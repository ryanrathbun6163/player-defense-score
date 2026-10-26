"""CPU-only review of one NBA-first candidate against preserved baseline outputs.

The input is an immutable, bound comparison record. This wrapper adapts native
blocks to the existing renderer without changing labels, point selections or
source roles. "Selected model" in the reused canvas means selected for this
review; it does not mean adopted or accepted.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import html
from pathlib import Path
import time
import traceback
import uuid

from . import completion_evaluation as evaluation
from . import completion_nba_comparison_render as renderer
from .completion_evaluation_package import ROLE, normalize_block
from .completion_training_runtime import atomic_write_once as write_once, binding
from .wasb_experiment import bound_path, canonical, read_json


SCHEMA = "nba_first_review_inputs/v0.1"
OUTPUT_SCHEMA = "nba_first_review/v0.1"


def check(condition, message):
    if not condition:
        raise ValueError(message)


def prepared_block(entry):
    """Derive a render view while retaining the source block and every output."""
    original = entry["block"]
    check(original["domain"] == "nba", "Only NBA review blocks are permitted")
    block = deepcopy(original)
    block["original_role"] = original["role"]
    block["role"] = ROLE
    block.setdefault("candidate_id", block["block_id"])
    old, new = entry["baseline_observations"], entry["candidate_observations"]
    check(len(old) == len(new) == len(block["frames"]), "Review observation census differs")
    for frame, baseline in zip(block["frames"], old, strict=True):
        check(frame.get("state", "permitted") == "permitted", "Protected review frame prohibited")
        index = frame["source_frame_index"]
        check(not any(a <= index <= b for a, b in block.get("protected_ranges", [])),
              "Protected review index prohibited")
        frame["state"] = "permitted"
        frame.setdefault("block_id", block["block_id"])
        frame.setdefault("reference_role", frame.get("exposure_role", original["role"]))
        frame["baseline_observation"] = {k: deepcopy(baseline[k]) for k in
            ("source_frame_index", "center_xy_px", "native_score", "temporal_contributions", "state")}
        frame["baseline_observation"]["original_record"] = deepcopy(baseline)
    normalize_block(block)
    # Both series must already have the native transport fields emitted by the
    # actual observation producer. A failed call can never become a missing ball.
    evaluation.validate_observations(block, old)
    evaluation.validate_observations(block, new)
    transported = evaluation.baseline_observations(block)
    check([r["original_baseline_record"] for r in transported] == old,
          "Baseline render transport changed an original output")
    return block, deepcopy(new)


def load_inputs(root, input_binding):
    root = Path(root).resolve()
    inputs = read_json(bound_path(root, input_binding))
    check(inputs.get("schema_version") == SCHEMA
          and inputs.get("status") == "completed_evaluation"
          and inputs.get("protected_evaluation_authorized") is False,
          "Completed permitted NBA evaluation required")
    check(inputs.get("human_visual_acceptance") is None,
          "New review must not claim earlier human acceptance")
    for name in ("baseline", "candidate"):
        check(isinstance(inputs[name]["name"], str) and inputs[name]["name"], "Model display name required")
        bound_path(root, inputs[name]["checkpoint"])
    for evidence in inputs.get("evidence_bindings", []):
        bound_path(root, evidence)
    check(bool(inputs["blocks"]), "Review must contain complete supplied blocks")
    prepared = [prepared_block(entry) for entry in inputs["blocks"]]
    ids = [block["block_id"] for block, _ in prepared]
    check(len(ids) == len(set(ids)), "Duplicate review block")
    return inputs, prepared


def validate_completed(root, result, identity, prepared):
    check(result["status"] == "completed" and result["identity"] == identity,
          "Completed NBA review identity changed")
    summary = read_json(bound_path(root, result["summary"]))
    bound_path(root, result["index"])
    check(summary["schema_version"] == OUTPUT_SCHEMA and summary["identity"] == identity
          and summary["human_visual_acceptance"] is None
          and summary["protected_evaluation_authorized"] is False,
          "NBA review summary changed")
    check(len(summary["blocks"]) == len(prepared)
          and summary["native_frames"] == sum(len(b["frames"]) for b, _ in prepared),
          "Completed review census differs")
    for saved, (block, _) in zip(summary["blocks"], prepared, strict=True):
        final = block["frames"][-1]
        check(saved["block_id"] == block["block_id"] and saved["block_sha256"] == canonical(block)
              and saved["decoded_frames"] == saved["native_pts_packet_frame_duration_checks"] == len(block["frames"])
              and saved["actual_final_native_frame"] == final["source_frame_index"]
              and saved["actual_final_source_pts_ticks"] == final["source_pts_ticks"]
              and saved["actual_final_duration_ticks"] == final["duration_ticks"]
              and saved["added_final_hold_ticks"] == 0 and saved["all_decoded_native_keys_verified"],
              "Completed native/final-frame evidence differs")
        for key in ("video", "actual_final_frame", "frame_records", "encoded_probe"):
            bound_path(root, saved[key])
    return result


def render_review(root, input_binding, output_folder, *, resume=False):
    root = Path(root).resolve()
    inputs, prepared = load_inputs(root, input_binding)
    output = (root / output_folder).resolve()
    check(output.is_relative_to(root / "data/outputs") and output != root / "data/outputs",
          "Review output escaped data/outputs")
    check(not output.exists() or resume, "Existing review requires explicit resume; old attempts stay preserved")
    identity = {"inputs": input_binding, "baseline": inputs["baseline"], "candidate": inputs["candidate"],
        "implementations": [binding(root, root / f"src/ball_tracking/{name}.py") for name in
            ("nba_first_review", "completion_nba_comparison_render", "completion_evaluation",
             "completion_evaluation_package", "completion_sac_references")],
        "protected_evaluation_authorized": False, "human_visual_acceptance": None}
    output.mkdir(parents=True, exist_ok=True)
    from .wasb_training import training_lock
    with training_lock(output / "review.lock"):
        write_once(output / "identity.json", identity)
        if (output / "completed.json").exists():
            return validate_completed(root, read_json(output / "completed.json"), identity, prepared)
        attempt = output / "attempts" / uuid.uuid4().hex
        attempt.mkdir(parents=True)
        began = time.perf_counter()
        write_once(attempt / "started.json", {"identity": identity, "started_at_utc": evaluation.stamp()})
        try:
            results, sections = [], []
            for offset, ((block, selected), entry) in enumerate(zip(prepared, inputs["blocks"], strict=True), 1):
                folder_name = f"block_{offset:02d}"
                provenance = {"input": input_binding, "input_block_sha256": canonical(entry["block"]),
                    "baseline": inputs["baseline"], "candidate": inputs["candidate"],
                    "source_block_role": entry["block"]["role"], "comparison": entry.get("provenance", {}),
                    "selection_meaning": "candidate chosen for review only; not adopted"}
                result = renderer.render_block(root, block, selected, attempt / folder_name, provenance)
                results.append(result)
                title = html.escape(block["candidate_id"])
                role = html.escape(str(entry["block"]["role"]))
                sections.append(f'<section><h2>{title}</h2><p>Original role: {role}.</p>'
                    f'<video controls preload="metadata" src="{folder_name}/comparison.mp4"></video>'
                    f'<p>Final native frame {result["actual_final_native_frame"]} · '
                    f'<a href="{folder_name}/actual_final_frame.png">Actual final frame</a> · '
                    f'<a href="{folder_name}/frame_records.json">Every source frame and timestamp</a></p></section>')
                print(f"Verified NBA-first review {block['block_id']}: {len(block['frames'])} frames", flush=True)
            summary = {"schema_version": OUTPUT_SCHEMA, "status": "completed", "identity": identity,
                "blocks": results, "native_frames": sum(r["decoded_frames"] for r in results),
                "human_visual_acceptance": None, "protected_evaluation_authorized": False}
            write_once(attempt / "summary.json", summary)
            old_name, new_name = (html.escape(inputs[k]["name"]) for k in ("baseline", "candidate"))
            (attempt / "index.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8">'
                '<title>NBA-first candidate review</title><style>body{font:17px/1.5 system-ui;max-width:1400px;'
                'margin:32px auto;padding:0 20px}video{width:100%;background:black}section{margin:32px 0}</style>'
                f'<h1>NBA-first candidate review</h1><p>Orange, left: {old_name}. Cyan, right: {new_name}. '
                'Green: accepted reference where available.</p><p>The video label “selected model” means selected '
                'for this comparison only. No model adoption, ball-phase pass or human trajectory acceptance is claimed. '
                'These are complete supplied contexts at native presentation timing, including each actual final interval. '
                'Unlabeled context is not accuracy evidence. Missing outputs and unknown reference positions stay explicit. '
                'Human review is pending.</p>' + ''.join(sections) + '</html>', encoding="utf-8")
            result = {"status": "completed", "identity": identity, "summary": binding(root, attempt / "summary.json"),
                "index": binding(root, attempt / "index.html"), "elapsed_seconds": time.perf_counter() - began,
                "human_visual_acceptance": None}
            validate_completed(root, result, identity, prepared)
            write_once(output / "completed.json", result)
            write_once(attempt / "completed.json", {"completion": binding(root, output / "completed.json")})
            return result
        except BaseException as error:
            write_once(attempt / "failed.json", {"identity": identity, "error_type": type(error).__name__,
                "error": str(error), "traceback": traceback.format_exc(),
                "elapsed_seconds": time.perf_counter() - began, "retry_requires_resume": True})
            raise


def main():
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    bound = binding(root, root / args.input)
    if args.run:
        result = render_review(root, bound, args.output_root, resume=args.resume)
    else:
        _, prepared = load_inputs(root, bound)
        result = {"status": "preflight_only_no_pixels", "input": bound,
                  "blocks": [b["block_id"] for b, _ in prepared],
                  "native_frames": sum(len(b["frames"]) for b, _ in prepared)}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
