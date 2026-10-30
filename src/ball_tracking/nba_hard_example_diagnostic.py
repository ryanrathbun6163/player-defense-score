"""Score accepted difficult-scene references against immutable saved NBA outputs.

No images, heatmaps or model are loaded. Candidate availability is an oracle
diagnostic of the complete *saved strict >0.3 component inventory*, never a new
selector or a claim about evidence below that operating point.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import math
from pathlib import Path
import statistics
import time
import uuid

from . import nba_wasb_diagnostic as d
from .annotations import FrameAnnotation

SCHEMA = "nba_hard_example_saved_diagnostic/v0.1"
RADIUS = 10
OUTCOMES = ("matched", "wrong", "missing", "hidden_alarm", "hidden_quiet", "unscored")


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_observations(manifest, observations):
    """Check the actual action producer's inventory and selection relationships."""
    d.require(observations["schema_version"] == "nba_wasb_action_observation/v0.1",
              "Expected complete action producer record")
    for key in ("candidate_id", "game_id", "approved_role"):
        d.require(observations[key] == manifest[key], f"Observation {key} differs")
    d.require(observations["inference"] == d.POLICY, "Frozen operating point differs")
    d.require(observations["checkpoint"]["sha256"] == d.EXPANDED_SHA, "Frozen checkpoint differs")
    source = manifest["source_video"]
    frames, rows = manifest["frames"], observations["frames"]
    indices = [f["source_frame_index"] for f in frames]
    ticks = [f["source_pts_ticks"] for f in frames]
    d.require(indices == list(range(indices[0], indices[-1] + 1)) and
              all(b > a for a, b in zip(ticks, ticks[1:])) and
              manifest["source_end_exclusive_pts_ticks"] > ticks[-1], "Invalid native input timeline")
    d.require(len(rows) == len(frames), "Incomplete observation inventory")
    for frame, row in zip(frames, rows):
        d.require(row["source_frame_index"] == frame["source_frame_index"] and
                  row["source_pts_ticks"] == frame["source_pts_ticks"] and
                  row["source_png"] == frame["png"] and row["time_base"] == manifest["time_base"],
                  "Observation native frame/PTS/PNG mapping differs")
        # The approved action run has no withheld frames. Do not silently treat
        # unavailable inference as a completed empty candidate inventory.
        d.require(row["inference_status"] == "completed" and row["withheld_reason"] is None and
                  type(row["temporal_contributions"]) is int and 1 <= row["temporal_contributions"] <= 3 and
                  isinstance(row["mean_heatmap_sha256"], str) and len(row["mean_heatmap_sha256"]) == 64,
                  "Incomplete inference cannot support candidate oracle")
        candidates = row["candidates"]
        d.require(isinstance(candidates, list) and
                  [c["candidate_index"] for c in candidates] == list(range(len(candidates))),
                  "Candidate inventory indices differ")
        for candidate in candidates:
            d.require(all(_finite(candidate[k]) for k in
                          ("center_x", "center_y", "heatmap_x", "heatmap_y", "native_score")) and
                      candidate["native_score"] > 0 and type(candidate["component_pixels"]) is int and
                      candidate["component_pixels"] > 0, "Invalid saved component")
            in_bounds = 0 <= candidate["center_x"] < source["width_px"] and 0 <= candidate["center_y"] < source["height_px"]
            d.require(candidate["in_source_bounds"] is in_bounds, "Saved component bounds differ")
        chosen = min(candidates, key=lambda c: (-c["native_score"], c["candidate_index"])) if candidates else None
        d.require(row["state"] == ("observed" if chosen else "missing") and
                  row["selected_candidate_index"] == (chosen["candidate_index"] if chosen else None) and
                  row["center_xy_px"] == ([chosen["center_x"], chosen["center_y"]] if chosen else None) and
                  row["native_score"] == (chosen["native_score"] if chosen else None),
                  "Saved selected point/candidate/mass relationship differs")
    return {r["source_frame_index"]: r for r in rows}


def _stats(values):
    return {"count": len(values), "mean_px": statistics.fmean(values) if values else None,
            "median_px": statistics.median(values) if values else None,
            "max_px": max(values) if values else None}


def summarize(rows):
    counts = Counter(r["outcome"] for r in rows)
    eligible = sum(counts[k] for k in ("matched", "wrong", "missing"))
    hidden = counts["hidden_alarm"] + counts["hidden_quiet"]
    errors = [r["raw_center_error_px"] for r in rows if r["raw_center_error_px"] is not None]
    adjusted = [r["uncertainty_adjusted_error_px"] for r in rows if r["uncertainty_adjusted_error_px"] is not None]
    uncertainties = [r["annotation_uncertainty_radius_px"] for r in rows if r["localization_eligible"]]
    failure_rows = [r for r in rows if r["outcome"] in ("wrong", "missing")]
    return {"frames": len(rows), "eligible_frames": eligible, **{k: counts[k] for k in OUTCOMES},
            "match_fraction_of_eligible": counts["matched"] / eligible if eligible else None,
            "hidden_reference_frames": hidden,
            "hidden_alarm_fraction": counts["hidden_alarm"] / hidden if hidden else None,
            "raw_center_error_all_emitted_eligible": _stats(errors),
            "raw_center_error_matched": _stats([r["raw_center_error_px"] for r in rows if r["outcome"] == "matched"]),
            "raw_center_error_wrong": _stats([r["raw_center_error_px"] for r in rows if r["outcome"] == "wrong"]),
            "uncertainty_adjusted_error_all_emitted_eligible": _stats(adjusted),
            "annotation_uncertainty_radius_eligible": _stats(uncertainties),
            "candidate_available_eligible": sum(r["candidate_available_within_radius"] is True for r in rows),
            "failed_selection_with_alternative_candidate": sum(r["alternative_candidate_within_radius"] is True for r in failure_rows),
            "failed_selection_without_candidate": sum(r["candidate_available_within_radius"] is False for r in failure_rows),
            "wrong_with_alternative_candidate": sum(r["outcome"] == "wrong" and r["alternative_candidate_within_radius"] is True for r in rows),
            "missing_with_candidate": sum(r["outcome"] == "missing" and r["candidate_available_within_radius"] is True for r in rows),
            "saved_candidate_inventory_count": sum(r["saved_candidate_count"] for r in rows),
            "changed_pilot_context_edge_frames": sum(r["changed_pilot_context_edge"] for r in rows),
            "visibility": dict(sorted(Counter(r["visibility"] for r in rows).items()))}


def failure_intervals(rows):
    """Do not join across unknown labels, window boundaries or different errors."""
    intervals = []
    for offset, row in enumerate(rows):
        if row["outcome"] not in ("wrong", "missing"):
            continue
        if (intervals and intervals[-1]["outcome"] == row["outcome"] and
                intervals[-1]["source_frame_range_inclusive"][1] + 1 == row["source_frame_index"]):
            interval = intervals[-1]
        else:
            interval = {"outcome": row["outcome"], "source_frame_range_inclusive": [row["source_frame_index"]] * 2,
                        "first_source_pts_ticks": row["source_pts_ticks"], "time_base": row["time_base"], "frames": 0}
            intervals.append(interval)
        interval["source_frame_range_inclusive"][1] = row["source_frame_index"]
        interval["frames"] += 1
        interval["last_source_pts_ticks"] = row["source_pts_ticks"]
        interval["end_exclusive_pts_ticks"] = row["end_exclusive_pts_ticks"]
        interval["duration_seconds"] = float((interval["end_exclusive_pts_ticks"] - interval["first_source_pts_ticks"]) * Fraction(row["time_base"]))
        following = rows[offset + 1] if offset + 1 < len(rows) else None
        interval["following_frame_cue"] = None if following is None else {
            "source_frame_index": following["source_frame_index"], "source_pts_ticks": following["source_pts_ticks"],
            "outcome": following["outcome"], "visibility": following["visibility"],
            "interpretation": "matched at next labeled frame" if following["outcome"] == "matched" else "recovery not established at next frame"}
    return intervals


def score_window(reference, manifest, observations, window_id, cohort, selection_cue=None):
    indexed = validate_observations(manifest, observations)
    d.require(reference["human_review"]["status"] == "accepted" and
              reference["origin"]["kind"] == "assistant_visual_proposal", "Reference needs accepted AI provenance")
    for key in ("candidate_id", "game_id", "approved_role", "source_video", "time_base"):
        d.require(reference[key] == manifest[key], f"Reference {key} differs")
    frames, labels = reference["frames"], reference["annotations"]
    d.require(len(frames) == len(labels) and frames, "Incomplete accepted labels")
    indices = [f["source_frame_index"] for f in frames]
    d.require(indices == list(range(indices[0], indices[-1] + 1)), "Reference window must be contiguous")
    source_frames = {f["source_frame_index"]: f for f in manifest["frames"]}
    end_ticks = {f["source_frame_index"]: n["source_pts_ticks"] for f, n in zip(manifest["frames"], manifest["frames"][1:])}
    end_ticks[manifest["frames"][-1]["source_frame_index"]] = manifest["source_end_exclusive_pts_ticks"]
    changed = {r["source_frame_index"] for r in observations["pilot_context_comparison"]["changed_context_frames"]}
    bounds = type("Bounds", (), {k: reference["source_video"][k] for k in ("width_px", "height_px")})()
    rows = []
    for offset, (frame, label) in enumerate(zip(frames, labels)):
        index = frame["source_frame_index"]
        d.require(frame == source_frames.get(index) and label["frame_index"] == index, "Reference native frame/PTS/PNG mapping differs")
        annotation = FrameAnnotation.from_mapping(label, offset, bounds)
        d.require(annotation.annotation_status == "labeled", "Accepted reference contains incomplete label")
        observation = indexed[index]
        point = observation["center_xy_px"]
        result = {"window_id": window_id, "cohort": cohort, "candidate_id": reference["candidate_id"],
                  "game_id": reference["game_id"], "source_frame_index": index, "source_pts_ticks": frame["source_pts_ticks"],
                  "end_exclusive_pts_ticks": end_ticks[index], "time_base": reference["time_base"], "source_png": frame["png"],
                  "visibility": annotation.visibility, "identity_certainty": annotation.game_ball_identity_certainty,
                  "localization_eligible": annotation.localization_eligible,
                  "reference_center_xy_px": list(annotation.geometry.center_xy_px) if annotation.geometry else None,
                  "annotation_uncertainty_radius_px": annotation.geometry.uncertainty_radius_px if annotation.geometry else None,
                  "annotation_notes": annotation.notes, "observed_center_xy_px": point,
                  "selected_candidate_index": observation["selected_candidate_index"], "saved_candidate_count": len(observation["candidates"]),
                  "temporal_contributions": observation["temporal_contributions"],
                  "changed_pilot_context_edge": cohort == "pilot_control" and index in changed,
                  "outcome": "unscored", "raw_center_error_px": None, "uncertainty_adjusted_error_px": None,
                  "candidate_available_within_radius": None, "alternative_candidate_within_radius": None,
                  "candidate_indices_within_radius": [], "nearest_saved_candidate_error_px": None}
        if annotation.localization_eligible:
            target = annotation.geometry.center_xy_px
            candidates = observation["candidates"]
            distances = [(c["candidate_index"], math.hypot(c["center_x"] - target[0], c["center_y"] - target[1]))
                         for c in candidates if c["in_source_bounds"]]
            matching = [i for i, error in distances if error <= RADIUS]
            result.update(candidate_indices_within_radius=matching, candidate_available_within_radius=bool(matching),
                          alternative_candidate_within_radius=any(i != observation["selected_candidate_index"] for i in matching),
                          nearest_saved_candidate_error_px=min((error for _, error in distances), default=None))
            if point is None:
                result["outcome"] = "missing"
            else:
                error = math.hypot(point[0] - target[0], point[1] - target[1])
                result.update(outcome="matched" if observation["selected_candidate_index"] in matching else "wrong",
                              raw_center_error_px=error,
                              uncertainty_adjusted_error_px=max(0, error - annotation.geometry.uncertainty_radius_px))
        elif annotation.visibility == "not_visible" and annotation.game_ball_identity_certainty in {"certain", "probable"}:
            result["outcome"] = "hidden_alarm" if point is not None else "hidden_quiet"
        rows.append(result)
    return {"window_id": window_id, "cohort": cohort, "candidate_id": reference["candidate_id"], "game_id": reference["game_id"],
            "approved_role": reference["approved_role"], "source_frame_range_inclusive": [indices[0], indices[-1]],
            "summary": summarize(rows), "failure_intervals": failure_intervals(rows),
            "qualitative_window_selection_cue": selection_cue, "frame_results": rows}


def run(root, proposal_path, approval_path, reference_path, output):
    root = Path(root).resolve()
    proposal_path, approval_path, reference_path = [(root / p).resolve() for p in (proposal_path, approval_path, reference_path)]
    output = (root / output).resolve()
    d.require(output.is_relative_to(root / "data/outputs") and not (output / "completion.json").exists(),
              "Choose a new ignored output; completed diagnostic is preserved")
    attempt = output / "attempts" / uuid.uuid4().hex
    d.write_once(attempt / "started.json", {"at_utc": d.stamp(), "status": "started", "model_calls": 0})
    started = time.monotonic()
    try:
        proposal, approval, accepted = map(d.read_json, (proposal_path, approval_path, reference_path))
        proposal_binding = d.binding(root, proposal_path)
        d.require(proposal["schema_version"] == "nba_hard_example_reference_proposal/v0.1" and
                  approval["schema_version"] == "nba_hard_example_reference_approval/v0.1" and
                  approval["status"] == "approved" and approval["proposal"] == proposal_binding and
                  approval["approved_scope"] == proposal["approval_scope_requested"], "Approved saved-score scope differs")
        d.require(accepted["status"] == "human_accepted_assisted_reference", "New references not accepted")
        acceptance_path = d.bound(root, accepted["acceptance"])
        acceptance = d.read_json(acceptance_path)
        d.require(acceptance["scope_approval"] == d.binding(root, approval_path), "Accepted scoring scope differs")
        # Reconsume the publisher contract; a caller cannot relabel arbitrary
        # coordinates as accepted merely by editing the published wrapper.
        from .nba_hard_example_reference import load_accepted_references
        verified_references = load_accepted_references(acceptance_path, root, verify_images=False)
        d.require(accepted["references"] == verified_references, "Published accepted reference differs from review evidence")
        old_path = d.bound(root, proposal["authority"]["existing_pilot_reference"])
        old = d.read_json(old_path)
        d.require(old["status"] == "human_accepted_assisted_reference", "Control references not accepted")
        completed = d.read_json(d.bound(root, proposal["authority"]["completed_observation"]))
        d.require(completed["checkpoint_sha256"] == d.EXPANDED_SHA, "Completed checkpoint differs")
        completed_candidates = {c["candidate_id"]: c for c in completed["candidates"]}
        bindings = {"proposal": proposal_binding, "scope_approval": d.binding(root, approval_path),
                    "accepted_reference": d.binding(root, reference_path), "accepted_pilot_reference": d.binding(root, old_path),
                    "completed_observation": proposal["authority"]["completed_observation"],
                    "scoring_source": d.binding(root, Path(__file__)),
                    "scoring_dependencies": [d.binding(root, root / name) for name in
                                             ("src/ball_tracking/annotations.py", "src/ball_tracking/nba_wasb_diagnostic.py",
                                              "src/ball_tracking/nba_hard_example_reference.py")], "windows": []}
        windows = proposal["windows"]
        refs = {r["window_id"]: r for r in accepted["references"]}
        d.require(len(refs) == len(accepted["references"]) == len(windows) and
                  set(refs) == {w["window_id"] for w in windows}, "Accepted window inventory differs")
        sources, reports = {}, []
        for window in windows:
            candidate = window["candidate_id"]
            authority = completed_candidates[candidate]
            d.require(authority["input_manifest"] == window["input_manifest"] and
                      authority["observations"] == window["saved_observations"], "Complete audited candidate inventory binding differs")
            manifest = d.read_json(d.bound(root, window["input_manifest"]))
            observations = d.read_json(d.bound(root, window["saved_observations"]))
            d.require(observations["input_manifest"] == window["input_manifest"], "Observation input binding differs")
            sources[candidate] = (manifest, observations)
            reference = refs[window["window_id"]]
            for key in ("candidate_id", "game_id", "time_base"):
                d.require(reference[key] == window[key], f"Approved reference {key} differs")
            frames = reference["frames"]
            d.require(len(frames) == window["frames"] and
                      [frames[0]["source_frame_index"], frames[-1]["source_frame_index"]] == window["source_frame_range_inclusive"] and
                      [frames[0]["source_pts_ticks"], frames[-1]["source_pts_ticks"]] == window["source_pts_ticks_inclusive"],
                      "Approved reference range/timing differs")
            reports.append(score_window(reference, manifest, observations, window["window_id"], "hard_example", window["selection_rationale"]))
            bindings["windows"].append({"window_id": window["window_id"], "input_manifest": window["input_manifest"],
                                        "saved_observations": window["saved_observations"]})
        d.require(len(old["references"]) == len(sources) and {r["candidate_id"] for r in old["references"]} == set(sources),
                  "Control candidate inventory differs")
        for reference in old["references"]:
            manifest, observations = sources[reference["candidate_id"]]
            reports.append(score_window(reference, manifest, observations, reference["candidate_id"] + "_pilot_control", "pilot_control"))
        all_rows = [row for report in reports for row in report["frame_results"]]
        d.require(len({(r["candidate_id"], r["source_frame_index"]) for r in all_rows}) == len(all_rows),
                  "Hard examples and pilot controls overlap or repeat frames")
        hard = [r for r in all_rows if r["cohort"] == "hard_example"]
        controls = [r for r in all_rows if r["cohort"] == "pilot_control"]
        d.require(len(hard) == proposal["totals"]["new_proposed_label_frames"] and
                  len(controls) == proposal["totals"]["existing_accepted_pilot_control_frames"] and
                  len(all_rows) <= proposal["totals"]["maximum_saved_observations_scored_after_label_acceptance"], "Approved score counts differ")
        d.require(sum(r["changed_pilot_context_edge"] for r in controls) == 8, "Expected eight changed-context control edges")
        grouped = defaultdict(list)
        for row in all_rows:
            grouped[row["cohort"], row["game_id"]].append(row)
        report = {"schema_version": SCHEMA, "status": "completed", "recorded_at_utc": d.stamp(), "bindings": bindings,
                  "localization_radius_px": RADIUS, "matching": "inclusive raw source-pixel distance; in-image points only",
                  "uncertainty": "reported separately; diagnostic subtraction does not change matches",
                  "candidate_oracle": "complete saved strict >0.3 component inventory; no lower-threshold or heatmap reaggregation",
                  "complete_saved_inventory_verified": [
                      {"candidate_id": candidate, "frames": len(observations["frames"]),
                       "candidate_components": sum(len(r["candidates"]) for r in observations["frames"]),
                       "states": dict(Counter(r["state"] for r in observations["frames"]))}
                      for candidate, (_, observations) in sorted(sources.items())],
                  "cohorts": {"hard_example": summarize(hard), "pilot_control": summarize(controls)},
                  "by_game_and_cohort": [{"cohort": c, "game_id": g, "summary": summarize(rows)} for (c, g), rows in sorted(grouped.items())],
                  "windows": reports, "original_short_context_score_recomputed_or_overwritten": False,
                  "work": {"model_calls": 0, "training_runs": 0, "image_decodes": 0, "video_decodes": 0, "heatmap_reaggregations": 0},
                  "limits": ["Failure-selected development frames, not representative NBA accuracy or an independent test.",
                             "Adjacent frames are correlated; no independent-sample confidence claim.",
                             "Unsupported geometry stays localization-unscored. Hidden alarms use only certain/probable not_visible labels.",
                             "AI authorship and human acceptance are distinct; prior prediction exposure is preserved.",
                             "Oracle availability is not a deployed selector; absent components do not prove no subthreshold ball evidence.",
                             "Following-frame cues do not certify continuous recovery across unknown labels or beyond each window.",
                             "SAC eligibility, Detroit exclusion from fitting, holdouts and NFHS finish line are unchanged."]}
        report_path = attempt / "report.json"
        d.write_once(report_path, report)
        compact = {k: v for k, v in report.items() if k != "windows"}
        compact["windows"] = [{k: v for k, v in w.items() if k != "frame_results"} for w in reports]
        d.write_once(attempt / "summary.json", compact)
        completion = {"schema_version": SCHEMA, "status": "completed", "report": d.binding(root, report_path),
                      "summary": d.binding(root, attempt / "summary.json"), "elapsed_seconds": time.monotonic() - started,
                      "cohorts": report["cohorts"], "attempt": attempt.relative_to(root).as_posix()}
        d.write_once(attempt / "completed.json", completion)
        d.write_once(output / "completion.json", completion)
        return completion
    except Exception as error:
        d.write_once(attempt / "failed.json", {"status": "failed_preserved", "error_type": type(error).__name__,
                                              "error": str(error), "elapsed_seconds": time.monotonic() - started})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    import json
    print(json.dumps(run(args.root, args.proposal, args.approval, args.reference, args.output), indent=2))


if __name__ == "__main__":
    main()
