"""CPU-only NBA episode scoring from existing, bound validation observations.

No image, heatmap, model or optimizer is loaded. Each source episode retains its
own clock and missing-context boundaries. Pooled counts are descriptive only;
historical checkpoint rejection and pending human review remain unchanged.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import time
import traceback

from . import completion_scoring as scoring
from .completion_evaluation_package import PRIMARY_RECIPE, validate_component_selection
from .wasb_experiment import bound_path, canonical, digest_file, read_json, write_once

SCHEMA = "nba_first_saved_validation/v0.1"
AUGMENTATION_RECIPE = "configs/ball_tracking/proposals/wasb_augmentation_v0_1.json"
AUTOMATIC_GATES = ("correct_fraction", "wrong_fraction", "certain_hidden_emissions", "missing_continuity", "recovery")


def check(value, message):
    if not value:
        raise ValueError(message)


def binding(root, path):
    path = Path(path).resolve()
    return {"path": path.relative_to(Path(root).resolve()).as_posix(),
            "sha256": digest_file(path), "bytes": path.stat().st_size}


def combine(statuses):
    values = set(statuses)
    return "fail" if "fail" in values else "inconclusive" if "inconclusive" in values else "pass" if "pass" in values else "not_applicable"


def score_block(block, observations):
    """Score one complete supplied context; censor omitted outer source intervals.

The input may be a checkpoint-validation episode or a permitted hard-context
evaluation block. Sparse annotations stay unknown, and per-frame segment and
reference-role fields are retained. Source pixels are never opened.
"""
    check(block["domain"] == "nba", "NBA-only scoring required")
    check(block.get("protected_evaluation_authorized", False) is False, "Protected evaluation prohibited")
    frames = block["frames"]
    indices = [f["source_frame_index"] for f in frames]
    check(len(frames) >= 3 and indices == list(range(indices[0], indices[-1] + 1)), "Complete consecutive native context required")
    check(len(observations) == len(frames), "Observation census differs")
    base = Fraction(block["time_base"])
    check(base > 0, "Invalid native time base")
    source = block["source_video"]
    check(0 <= indices[0] <= indices[-1] < source["frame_count"], "Context outside source frame count")
    for position, (frame, row) in enumerate(zip(frames, observations, strict=True)):
        index = indices[position]
        check(frame.get("state", "permitted") == "permitted"
              and not any(lo <= index <= hi for lo, hi in block.get("protected_ranges", [])), "Protected row prohibited")
        check(type(frame["duration_ticks"]) is int and frame["duration_ticks"] > 0, "Invalid native duration")
        if position:
            previous = frames[position - 1]
            check(previous["source_pts_ticks"] + previous["duration_ticks"] == frame["source_pts_ticks"], "Native interval discontinuity")
        check(row["source_frame_index"] == index and row["source_pts_ticks"] == frame["source_pts_ticks"]
              and row["source_png"] == frame["png"] and Fraction(row["time_base"]) == base,
              "Observation/native source transport differs")
        check(row["inference_status"] == "completed" and row.get("point_origin", "automatic") == "automatic",
              "Only completed automatic observations are eligible")
        expected_count = sum(start <= position <= start + 2 for start in range(max(0, position - 2), min(position, len(frames) - 3) + 1))
        check(row["temporal_contributions"] == expected_count, "Saved temporal context differs")
        validate_component_selection(row)
    timeline = {**block, "exposure_role": block.get("exposure_role", block.get("reference_role", block.get("role")))}
    report = scoring.score_timeline(timeline, observations)
    rows = report["frame_results"]
    left, right = indices[0] > 0, indices[-1] < source["frame_count"] - 1
    if left:
        rows[0]["boundary_before"] = "exposure_subset_boundary"
    if right:
        rows[-1]["boundary_after"] = "exposure_subset_boundary"
    # The unchanged public scorer has no outer-window-boundary parameter. Its
    # existing pure kernels already implement this precise censoring contract.
    report["summary"] = scoring._metrics(rows)
    report["cohorts"] = {role: {"scope": "descriptive exposure subset; omitted intervals censored",
        **scoring._metrics(scoring._cohort_rows(rows, role))} for role in sorted({r["exposure_role"] for r in rows})}
    report.update(scope_censoring={"left_unobserved": left, "right_unobserved": right,
        "source_frame_range_inclusive": [indices[0], indices[-1]], "source_frame_count": source["frame_count"],
        "outside_context_inferred": False}, source_video=source,
        automatic_gate_status=combine(report["summary"]["gates"][key]["status"] for key in AUTOMATIC_GATES),
        human_visual_acceptance=None, full_possession_acceptance="not_assessed")
    return report


def aggregate_blocks(reports):
    """Descriptive counts plus conjunction of episode gates, never a pooled pass."""
    check(reports and len({r["block_id"] for r in reports}) == len(reports), "Duplicate/empty episode reports")
    keys = ("frames", "eligible_frames", "matched", "wrong", "missing", "unscored", "withheld",
            "certain_hidden_emitted_points", "certain_hidden_emitted_frames", "uncertain_hidden_emitted_points")
    counts = {key: sum(r["summary"][key] for r in reports) for key in keys}
    denominator = counts["eligible_frames"]
    statuses = {r["block_id"]: {key: value["status"] for key, value in r["summary"]["gates"].items()} for r in reports}
    worst = max(Fraction(r["summary"]["missing_runs"]["worst_known_duration"]["exact_seconds"]) for r in reports)
    return {"scope": "descriptive totals across separate episodes; no pooled acceptance gate", **counts,
        "fractions": {key: {"numerator": counts[key], "denominator": denominator,
                             "value": counts[key] / denominator if denominator else None} for key in ("matched", "wrong", "missing")},
        "worst_episode_known_missing_duration": {"exact_seconds": str(worst), "seconds": float(worst)},
        "episode_gates": statuses,
        "episode_quantitative_status": {r["block_id"]: r["summary"]["quantitative_status"] for r in reports},
        "episode_automatic_gate_status": {r["block_id"]: r["automatic_gate_status"] for r in reports},
        "all_episode_quantitative_status": combine(r["summary"]["quantitative_status"] for r in reports),
        "all_episode_automatic_gate_status": combine(r["automatic_gate_status"] for r in reports),
        "recovery_event_status_counts": dict(Counter(e["status"] for r in reports for e in r["summary"]["recoveries"]["events"])),
        "wrong_object_review_pending_points": sum(r["summary"]["wrong_objects"]["pending_points"] for r in reports),
        "pooled_pass_claimed": False, "human_visual_acceptance": None, "ball_phase_accepted": False}


def inventory(root):
    """Read immutable producer envelopes; verify eleven distinct saved checkpoints."""
    root = Path(root).resolve()
    parent_path, augmentation_path = root / PRIMARY_RECIPE, root / AUGMENTATION_RECIPE
    parent, augmentation = read_json(parent_path), read_json(augmentation_path)
    check(augmentation["parent_recipe"] == binding(root, parent_path), "Augmentation parent recipe differs")
    package = read_json(bound_path(root, parent["package"]))
    check(package["protected_evaluation_authorized"] is False, "Protected package prohibited")
    blocks = [b for b in package["validation_blocks"] if b["domain"] == "nba"]
    check(len(blocks) == 6 and sum(len(b["frames"]) for b in blocks) == 960
          and {b["game_id"] for b in blocks} == {"0022400879"}
          and all(b["role"] == "checkpoint_validation" for b in blocks), "Saved NBA validation census/role differs")
    training_games = {b["game_id"] for b in package["training_blocks"] if b["domain"] == "nba"}
    check(not training_games.intersection(b["game_id"] for b in blocks), "NBA validation game overlaps fitting games")
    for item in parent["code_bindings"] + augmentation["code_bindings"]:
        bound_path(root, item)
    for block in blocks:
        for entry in block["reference_bindings"]:
            bound_path(root, entry)
    completions, records, identities = {}, [], {}
    for label, recipe, recipe_path in (("primary", parent, parent_path), ("augmentation", augmentation, augmentation_path)):
        completion_path = root / recipe["output_root"] / "completed.json"
        if label == "primary":
            check(binding(root, completion_path) == augmentation["control_completed"], "Original completed-control binding differs")
        completion = read_json(completion_path)
        check(completion["status"] == "completed" and completion["completed_epochs"] == 5
              and completion["identity"]["recipe"] == binding(root, recipe_path)
              and completion["identity"]["package_sha256"] == canonical(package)
              and completion["protected_evaluation_authorized"] is False, "Historical completion identity differs")
        saved_reports = [read_json(bound_path(root, item)) for item in completion["validation_reports"]]
        check([report["epoch"] for report in saved_reports] == list(range(6)), "Historical validation epoch census differs")
        for report in saved_reports:
            check(report["identity"] == completion["identity"] and report["threshold"] == .3
                  and report["strict_threshold"] is True and report["selection"] == "largest_component_mass_then_stable_index"
                  and report["aggregation"] == "ascending_float32_aligned_contributor_mean"
                  and report["protected_frames"] == 0, "Historical report identity/policy differs")
            bound_path(root, report["checkpoint"])
        completions[label] = {"binding": binding(root, completion_path), "historical_selection": completion["selection"],
                              "historical_stop_reason": completion["stop_reason"]}
        identities[label] = completion["identity"]
        if label == "primary":
            original_zero = saved_reports[0]
        else:
            reused = deepcopy(saved_reports[0])
            reuse = reused.pop("reused_validation")
            check(reuse["source_report"] == records[0]["validation_report"] and reuse["new_model_calls"] == 0,
                  "Epoch-zero reuse provenance differs")
            reused["identity"] = identities["primary"]
            check(reused == original_zero, "Reused epoch-zero body differs")
        for report, report_binding in zip(saved_reports, completion["validation_reports"], strict=True):
            if label == "augmentation" and report["epoch"] == 0:
                continue
            records.append({"name": label + f"_epoch{report['epoch']}", "epoch": report["epoch"], "campaign": label,
                "checkpoint": report["checkpoint"], "validation_report": report_binding, "report": report})
    check(len(records) == len({r["checkpoint"]["sha256"] for r in records}) == 11, "Unique checkpoint census differs")
    return package, blocks, records, {"package": parent["package"], "completions": completions,
        "validation_game_id": "0022400879", "training_game_ids": sorted(training_games),
        "model_calls": 0, "source_pixels_read": False, "protected_evaluation_authorized": False}


def analyze_record(blocks, record):
    saved = {b["block_id"]: b for b in record["report"]["blocks"] if b["domain"] == "nba"}
    check(set(saved) == {b["block_id"] for b in blocks}, "Saved validation episode census differs")
    episodes = []
    for block in blocks:
        source = saved[block["block_id"]]
        check(source["game_id"] == block["game_id"], "Saved validation game differs")
        report = score_block(block, source["observations"])
        summary = report["summary"]
        for key in ("matched", "wrong", "missing", "eligible_frames"):
            check(summary[key] == source[key], "New reader changed original geometric counts")
        check(summary["certain_hidden_emitted_points"] == source["certain_hidden_emissions"]
              and summary["certain_hidden_emitted_points"] + summary["uncertain_hidden_emitted_points"] == source["all_hidden_emissions"],
              "New reader changed original hidden-emission counts")
        check(Fraction(summary["missing_runs"]["worst_known_duration"]["exact_seconds"]) == Fraction(source["worst_missing_duration_exact"]),
              "New reader changed known missing duration")
        check(len(source["frame_results"]) == len(report["frame_results"]), "Original score-frame census differs")
        for original, actual in zip(source["frame_results"], report["frame_results"], strict=True):
            check(original["source_frame_index"] == actual["source_frame_index"]
                  and original["source_pts_ticks"] == actual["source_pts_ticks"], "Original geometric score transport differs")
            if actual["localization_eligible"]:
                check(original["outcome"] == actual["outcome"]
                      and abs((original["raw_center_error_px"] or 0) - (actual["raw_center_error_px"] or 0)) < 1e-9,
                      "Original per-frame geometric outcome differs")
        report["observations"] = source["observations"]
        episodes.append(report)
    aggregate = aggregate_blocks(episodes)
    historical = record["report"]["cohorts"]["nba_validation"]
    check(all(aggregate[k] == historical[k] for k in ("matched", "wrong"))
          and aggregate["certain_hidden_emitted_points"] == historical["certain_hidden_emissions"], "Original NBA cohort totals differ")
    return {**{k: v for k, v in record.items() if k != "report"}, "episodes": episodes, "aggregate": aggregate,
            "historical_selection_changed": False, "model_adopted": False}


def execute(root, output_folder, *, authority=None):
    root = Path(root).resolve()
    package, blocks, records, identity = inventory(root)
    output = (root / output_folder).resolve()
    check(output.is_relative_to(root / "data/outputs") and output != root / "data/outputs" and not output.exists(),
          "Preserve existing evidence; use a fresh output under data/outputs")
    if authority is not None:
        bound_path(root, authority)
    identity.update(authority=authority, implementation=binding(root, Path(__file__)),
                    scoring_implementation=binding(root, Path(scoring.__file__)))
    output.mkdir(parents=True)
    write_once(output / "started.json", identity)
    began = time.perf_counter()
    try:
        analyses = []
        for record in records:
            analysis = analyze_record(blocks, record)
            path = output / (record["name"] + ".json")
            write_once(path, analysis)
            check(read_json(bound_path(root, binding(root, path))) == analysis, "Emitted checkpoint analysis changed in transport")
            analyses.append({"name": record["name"], "checkpoint": record["checkpoint"], "analysis": binding(root, path),
                             "aggregate": analysis["aggregate"]})
        result = {"schema_version": SCHEMA, "status": "completed", "identity": identity,
            "checkpoints": analyses, "unique_checkpoints": 11, "episodes_per_checkpoint": 6,
            "frames_per_checkpoint": 960, "eligible_frames_per_checkpoint": 882,
            "historical_selection_changed": False, "model_adopted": False,
            "protected_evaluation_authorized": False, "human_visual_acceptance": None,
            "elapsed_seconds": time.perf_counter() - began,
            "limits": ["Checkpoint validation is development evidence, not untouched holdout evidence.",
                       "Episode boundaries censor omitted context; no cross-episode trajectory is invented.",
                       "Pooled fractions do not override any episode failure or unresolved human review."]}
        write_once(output / "completed.json", result)
        return result
    except BaseException as error:
        write_once(output / "failed.json", {"identity": identity, "error": str(error), "traceback": traceback.format_exc()})
        raise


def main():
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output-root")
    args = parser.parse_args()
    if args.output_root:
        result = execute(args.root, args.output_root)
        print(json.dumps({k: result[k] for k in ("status", "unique_checkpoints", "frames_per_checkpoint")}))
    else:
        _, blocks, records, identity = inventory(args.root)
        print(json.dumps({"status": "saved_metadata_inventory", "blocks": [b["block_id"] for b in blocks],
                          "reports": [{k: v for k, v in r.items() if k != "report"} for r in records], "identity": identity}))


if __name__ == "__main__":
    main()
