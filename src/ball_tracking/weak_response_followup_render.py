"""Render the two predeclared corrected NBA arms without rerunning selection.

This additive CPU wrapper preserves the initial comparison and its review files.
It consumes original arm records directly, with no compatibility display aliases.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import html
from pathlib import Path
import json
import sys
import time
import traceback
import uuid

from . import weak_response_render as original
from . import weak_response_review as review
from . import weak_response_experiment as experiment
from .weak_response_capture import bind, bound, canonical, read, write_once, validate_context, CONTEXTS

ROOT = Path(__file__).resolve().parents[2]
OUT = "data/outputs/ball_tracking/weak_response_v0_1/followup_v0_1"
COMPARISON = OUT + "/completed.json"
ARMS = {"motion_and_speed": "native_only", "motion_and_speed_narrow_weak": "native_plus_0.01"}
SCHEMA = "weak_response_followup_complete_render/v0.1"
check = original.check


def validate_choice(body, record, entry, arm, config):
    """Validate the actual producer envelope before materializing bound pools."""
    check(arm in ARMS and config["arms"][arm]["pool"] == ARMS[arm], "Unexpected fixed render arm/pool")
    check(body["block_id"] == record["block_id"] == entry["block"]["block_id"]
          and body["variant"] == arm and body["pool_source"] == record["pool_source"]
          and body["pool_policy"] == ARMS[arm]
          and body["sequence_parameters"] == {**config["base_sequence"], **config["arms"][arm]["changes"]}
          and body["references_used_in_selection"] is False, "Actual fixed-arm choice transport differs")
    native = entry["candidate_observations"]
    check(len(body["observations"]) == len(native), "Choice frame count differs")
    for chosen, baseline in zip(body["observations"], native, strict=True):
        check(all(chosen[key] == baseline[key] for key in
            ("source_frame_index", "source_pts_ticks", "time_base", "mean_heatmap_sha256")),
            "Choice native timestamp/map provenance differs")


def preflight(root, comparison_path, arm):
    root = Path(root).resolve()
    check(arm in ARMS, "Only the two predeclared review arms are allowed")
    comparison_link = bind(root, root / comparison_path)
    comparison = read(bound(root, comparison_link))
    check(comparison["status"] == "completed" and comparison["protected_evaluation_authorized"] is False
          and comparison["model_adopted"] is False and comparison["ball_phase_accepted"] is False
          and comparison["human_trajectory_acceptance"] is None
          and comparison["new_training_updates"] == comparison["new_model_calls"] == comparison["new_labels"] == 0
          and comparison["main_research_arm"] == "motion_and_speed"
          and comparison["main_research_arm_chosen_before_results"] is True,
          "Completed permitted fixed follow-up required")
    frozen = read(bound(root, comparison["freeze"]))
    check(frozen["status"] == "frozen_before_any_followup_choices_or_scores"
          and all(frozen[key] == comparison[key] for key in
              ("source", "config", "paired_inputs", "checkpoint", "original_comparison", "main_research_arm")),
          "Completed follow-up differs from prospective freeze")
    clarification_link = bind(root, (root / comparison_path).parent / "prospective_freeze_clarification.json")
    clarification = read(bound(root, clarification_link))
    check(clarification["original_freeze"] == comparison["freeze"]
          and clarification["kind"] == "explicit_prospective_history_clarification",
          "Prospective history clarification differs")
    bound(root, clarification["frozen_test_source"])
    for source in comparison["source"]:
        bound(root, source)
    config = read(bound(root, comparison["config"]))
    check(config["extraction"]["additional_threshold"] == .01
          and config["extraction"]["native_threshold"] == .3, "Actual narrow-pool threshold differs")
    prior = read(bound(root, comparison["original_comparison"]))
    check(prior["status"] == "completed" and prior["checkpoint"] == comparison["checkpoint"],
          "Original completed cosine-nine control differs")
    for source in prior["source"]:
        bound(root, source)
    bound(root, comparison["checkpoint"])
    package = read(bound(root, comparison["paired_inputs"]))
    check(package["protected_evaluation_authorized"] is False
          and package["candidate"]["checkpoint"] == comparison["checkpoint"], "Paired source/control differs")
    entries, source_records = package["blocks"], comparison["records"]
    check(tuple(entry["block"]["block_id"] for entry in entries) == CONTEXTS
          and len(entries) == len(source_records) == 8
          and sum(len(entry["block"]["frames"]) for entry in entries) == 3662
          and [entry["block"]["block_id"] for entry in entries] == [r["block_id"] for r in source_records],
          "Complete eight-context follow-up required")
    prior_records = {r["block_id"]: r for r in prior["records"]}
    records = []
    for entry, record in zip(entries, source_records, strict=True):
        validate_context(entry)
        check(record["controls"] == prior_records[record["block_id"]]["variants"], "Reused controls changed")
        body = read(bound(root, record["variants"][arm]))
        validate_choice(body, record, entry, arm, config)
        native = read(bound(root, record["controls"]["native"]))
        check(native["block_id"] == record["block_id"]
              and native["observations"] == entry["candidate_observations"], "Native observations changed")
        # This in-memory mapping only adapts the frozen receipt helper; all file
        # bindings still name the original actual arm and native record.
        records.append({"block_id": record["block_id"], "pool_source": record["pool_source"],
            "variants": {"native": record["controls"]["native"], arm: record["variants"][arm]}})
    identity = {"schema_version": SCHEMA, "comparison": comparison_link, "freeze": comparison["freeze"],
        "prospective_history_clarification": clarification_link,
        "variant": arm, "actual_arm_name": arm, "pool_recipe": ARMS[arm], "display_aliases_used": False,
        "paired_inputs": comparison["paired_inputs"], "checkpoint": comparison["checkpoint"],
        "original_comparison": comparison["original_comparison"], "comparison_source": comparison["source"],
        "render_source": [bind(root, root / f"src/ball_tracking/{name}.py") for name in
            ("weak_response_followup_render", "weak_response_render", "weak_response_review",
             "weak_response_experiment", "weak_response_capture", "completion_sac_references")],
        "candidate_pool_policy": "native_only" if ARMS[arm] == "native_only" else "all",
        "candidate_pool_projection": list(experiment.SELECTOR_FIELDS), "human_visual_acceptance": None,
        "model_adopted": False, "protected_evaluation_authorized": False, "model_calls": 0}
    return entries, records, identity


def execute(root=ROOT, *, comparison_path=COMPARISON, arm, resume=False):
    root = Path(root).resolve()
    entries, records, identity = preflight(root, comparison_path, arm)
    output = root / OUT / f"review_{arm}_v0_1"
    check(not output.exists() or resume, "Existing review requires --resume; preserve all attempts")
    output.mkdir(parents=True, exist_ok=True)
    original.publish(output / "identity.json", identity)
    if (output / "completed.json").exists():
        return original.verify_completed(root, read(output / "completed.json"), identity, entries, records)
    run = output / "attempts" / uuid.uuid4().hex
    run.mkdir(parents=True)
    began = time.perf_counter()
    write_once(run / "started.json", {"identity": identity, "created_at_utc": datetime.now(timezone.utc).isoformat()})
    rendered, reused, published = 0, 0, []
    try:
        for entry, record in zip(entries, records, strict=True):
            block, native = entry["block"], entry["candidate_observations"]
            expected = original.block_identity(identity, entry, record)
            folder = output / "blocks" / experiment.key(block["block_id"])
            folder.mkdir(parents=True, exist_ok=True)
            complete_path = folder / "completed.json"
            if complete_path.exists():
                result = original.verify_block_receipt(root, read(complete_path), expected, block)
                reused += 1
                event = "reused_verified_render"
            else:
                body = read(bound(root, record["variants"][arm]))
                pools = experiment.pool_rows(root, bound(root, record["pool_source"]), block, native)
                if identity["candidate_pool_policy"] == "native_only":
                    pools = [[c for c in pool if c["original_index"] is not None] for pool in pools]
                observations = experiment.materialize_choices(body, pools)
                render_entry = {"block": block, "baseline_observations": native, "candidate_observations": observations,
                    "candidate_pool_source": record["pool_source"], "candidate_pool_policy": identity["candidate_pool_policy"],
                    "candidate_pool_projection": identity["candidate_pool_projection"]}
                attempt = folder / "attempts" / uuid.uuid4().hex
                result = review.render_block(root, render_entry, attempt, provenance=expected)
                receipt = {"status": "completed", "identity": expected,
                    "render_started": bind(root, attempt / "started.json"),
                    "render_receipt": bind(root, attempt / "render_receipt.json")}
                original.verify_block_receipt(root, receipt, expected, block)
                write_once(complete_path, receipt)
                rendered += 1
                event = "rendered_verified"
                del pools, observations, render_entry, body
                gc.collect()
            published.append({"block_id": block["block_id"], "completion": bind(root, complete_path), "render": result})
            print(json.dumps({"event": event, "actual_arm_name": arm, "block_id": block["block_id"],
                "native_frames": len(block["frames"]), "elapsed_seconds": time.perf_counter() - began}), flush=True)
        check(sum(item["render"]["decoded_frames"] for item in published) == 3662, "Incomplete final review")
        sections = []
        for item in published:
            result = item["render"]
            links = {name: (root / result[name]["path"]).relative_to(output).as_posix()
                for name in ("video", "actual_final_frame", "frame_records")}
            sections.append(f'<section><h2>{html.escape(item["block_id"])}: {html.escape(arm)}</h2>'
                f'<video controls preload="metadata" src="{html.escape(links["video"], quote=True)}"></video>'
                f'<p>Actual final native frame: {result["actual_final_native_frame"]}. '
                f'<a href="{html.escape(links["actual_final_frame"], quote=True)}">Final frame</a> | '
                f'<a href="{html.escape(links["frame_records"], quote=True)}">Every frame and timestamp</a></p></section>')
        page = ('<!doctype html><html lang="en"><meta charset="utf-8"><title>NBA corrected sequence review</title>'
            '<style>body{font:17px/1.5 system-ui;max-width:1400px;margin:32px auto;padding:0 20px}video{width:100%}</style>'
            f'<h1>NBA corrected sequence review: {html.escape(arm)}</h1>'
            f'<p>Actual candidate pool recipe: {html.escape(ARMS[arm])}. Orange/left: cosine-nine native research control. '
            f'Cyan/right: {html.escape(arm)}, a predeclared follow-up research arm. Green: accepted reference where '
            'available. All eight supplied contexts, 3,662 native frames and final intervals are included. '
            'Missing choices and uncertain references remain explicit. HOU informed this development correction; '
            'DET is locked application and SAC is training-exposed. Human trajectory and object-identity review '
            'remains pending. Focused HOU e01 transport tests exercised the selector and scorer before the full-study '
            'freeze; that disclosed chronology limitation remains bound in the review identity. '
            'No model adoption or ball-phase pass is claimed.</p>' + ''.join(sections) + '</html>')
        index = output / "index.html"
        if index.exists():
            check(index.read_text(encoding="utf-8") == page, "Existing master index differs")
        else:
            index.write_text(page, encoding="utf-8")
        summary = {"schema_version": SCHEMA, "identity": identity, "blocks": published, "native_frames": 3662,
            "human_visual_acceptance": None, "protected_evaluation_authorized": False, "model_adopted": False}
        original.publish(output / "summary.json", summary)
        result = {**summary, "status": "completed", "summary": bind(root, output / "summary.json"),
            "index": bind(root, index), "completion_attempt": run.relative_to(root).as_posix(),
            "rendered_blocks_this_attempt": rendered, "reused_completed_blocks": reused,
            "elapsed_seconds_this_attempt": time.perf_counter() - began}
        original.verify_completed(root, result, identity, entries, records)
        write_once(output / "completed.json", result)
        write_once(run / "completed.json", {"completion": bind(root, output / "completed.json"),
            "rendered_blocks": rendered, "reused_blocks": reused, "elapsed_seconds": time.perf_counter() - began})
        return result
    except BaseException as error:
        write_once(run / "failed.json", {"identity": identity, "error": str(error), "traceback": traceback.format_exc(),
            "rendered_blocks": rendered, "reused_blocks": reused, "elapsed_seconds": time.perf_counter() - began})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=tuple(ARMS), required=True)
    parser.add_argument("--comparison", default=COMPARISON)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.run:
        result = execute(comparison_path=args.comparison, arm=args.arm, resume=args.resume)
        print(json.dumps({key: result[key] for key in ("status", "native_frames", "index",
            "rendered_blocks_this_attempt", "reused_completed_blocks", "elapsed_seconds_this_attempt")}))
    else:
        entries, _, identity = preflight(ROOT, args.comparison, args.arm)
        print(json.dumps({"status": "render_preflight_only_no_pixels", "contexts": len(entries),
            "native_frames": 3662, "identity": identity}))
    check("torch" not in sys.modules, "CPU render unexpectedly imported Torch")


if __name__ == "__main__":
    main()
