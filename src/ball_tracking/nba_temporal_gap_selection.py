"""One fixed saved-pool gap selector; labels enter only after decisions are saved."""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import statistics
import time
import uuid

import numpy as np

from . import nba_candidate_preservation as pool_producer
from . import nba_wasb_diagnostic as d
from .nba_adaptation_comparison import GATES as ADAPTATION_GATES
from .nba_adaptation_regression_diagnostic import read_bound
from .nba_annotations import FrameAnnotation

SCHEMA = "nba_temporal_gap_selection/v0.1"
POLICY = {
    "arm": "old", "time_base": "1/90000",
    "max_anchor_elapsed_seconds": .12,
    "max_anchor_speed_diagonals_per_second": 1.0,
    "max_candidate_distance_diagonals": .006,
    "max_plausible_diameter_diagonals": .006,
    "limits": "inclusive; no tolerance or threshold sweep",
    "original_points": "preserve every non-null original center exactly, including wrong or out-of-image points",
    "gap": "maximal original-missing run within one supplied consecutive window",
    "anchors": "both bounding original points must be in-image; no recursive anchors",
    "expectation": "linear native-PTS interpolation for ranking only; never emit interpolation",
    "pool": "in-image exact-coordinate groups from the old saved pool; retain all provenance members",
    "ambiguity": "abstain entire gap if any frame lacks plausible coordinates or their pairwise diameter exceeds limit",
    "choice": "minimum distance to expectation, then lowest original pool record index",
    "edge_gaps": "abstain", "whole_gap_or_none": True,
    "mass_filter": False, "contributor_voting": False, "labels_used_by_selector": False,
}
GATES = {"original_adaptation": copy.deepcopy(ADAPTATION_GATES), "sac_easy_control_matched": 60,
         "no_additional_wrong_or_hidden_alarms_all_groups": True}
INPUT_KEYS = {"window_id", "candidate_id", "source_frame_index", "source_pts_ticks",
              "width_px", "height_px", "baseline_center_xy_px", "pool_records"}
RECORD_KEYS = {"record_index", "center_xy_px", "provenance_id"}


def _center(value):
    d.require(value is None or isinstance(value, list) and len(value) == 2
              and all(isinstance(x, (float, int)) and not isinstance(x, bool) and math.isfinite(x) for x in value),
              "Nonfinite or malformed center")
    return copy.deepcopy(value)


def projection(row):
    """Explicit geometry whitelist; annotations, cohort and scores cannot enter."""
    source, frame, arm = row["source_video"], row["source_frame"], row["old"]
    return {"window_id": row["window_id"], "candidate_id": row["candidate_id"],
        "source_frame_index": row["source_frame_index"], "source_pts_ticks": frame["source_pts_ticks"],
        "width_px": source["width_px"], "height_px": source["height_px"],
        "baseline_center_xy_px": _center(arm["original_selected"]["center_xy_px"]),
        "pool_records": [{"record_index": i,
            "center_xy_px": _center([r["component"]["center_x"], r["component"]["center_y"]]),
            "provenance_id": copy.deepcopy(r["provenance_id"])} for i, r in enumerate(arm["pool"]["records"])]}


def _inside(point, row):
    return point is not None and 0 <= point[0] < row["width_px"] and 0 <= point[1] < row["height_px"]


def _validate_window(rows):
    d.require(bool(rows), "Empty selection window")
    first = rows[0]
    for offset, row in enumerate(rows):
        d.require(set(row) == INPUT_KEYS, "Selector input is not the geometry whitelist")
        d.require(all(row[k] == first[k] for k in ("window_id", "candidate_id", "width_px", "height_px")),
                  "Selector crossed source/window bounds")
        d.require(all(type(row[k]) is int for k in ("source_frame_index", "source_pts_ticks", "width_px", "height_px"))
                  and row["width_px"] > 0 and row["height_px"] > 0, "Invalid source dimensions or native PTS")
        d.require(row["source_frame_index"] == first["source_frame_index"] + offset
                  and (not offset or row["source_pts_ticks"] > rows[offset-1]["source_pts_ticks"]),
                  "Window is not consecutive with increasing native PTS")
        _center(row["baseline_center_xy_px"])
        for index, record in enumerate(row["pool_records"]):
            d.require(set(record) == RECORD_KEYS and record["record_index"] == index, "Pool record order changed")
            _center(record["center_xy_px"])
            d.require(record["center_xy_px"] is not None, "Null candidate coordinate")
            pid = record["provenance_id"]
            d.require(isinstance(pid, list) and len(pid) == 7 and pid[:3] == ["old", row["candidate_id"], row["source_frame_index"]],
                      "Pool candidate provenance changed")


def _groups(row):
    groups = {}
    for record in row["pool_records"]:
        if _inside(record["center_xy_px"], row):
            key = tuple(record["center_xy_px"])
            groups.setdefault(key, []).append(record)
    return [{"center_xy_px": list(key), "record_indices": [r["record_index"] for r in records],
             "provenance_ids": [copy.deepcopy(r["provenance_id"]) for r in records]} for key, records in groups.items()]


def select_window(rows):
    """Select from saved geometry only; all anchors come from the original rows."""
    _validate_window(rows)
    diagonal = math.hypot(rows[0]["width_px"], rows[0]["height_px"])
    radius = POLICY["max_candidate_distance_diagonals"] * diagonal
    diameter_limit = POLICY["max_plausible_diameter_diagonals"] * diagonal
    decisions = [{k: copy.deepcopy(row[k]) for k in ("window_id", "candidate_id", "source_frame_index", "source_pts_ticks",
                                                   "baseline_center_xy_px")} for row in rows]
    for row, decision in zip(rows, decisions):
        decision.update(selected_center_xy_px=copy.deepcopy(row["baseline_center_xy_px"]), selected_pool_record_index=None,
                        selected_provenance_id=None, selected_coordinate_group=None, gap_id=None,
                        decision="preserved_original" if row["baseline_center_xy_px"] is not None else "abstained",
                        reason="original_point_immutable" if row["baseline_center_xy_px"] is not None else None)
    gaps = []; offset = 0
    while offset < len(rows):
        if rows[offset]["baseline_center_xy_px"] is not None:
            offset += 1; continue
        start = offset
        while offset < len(rows) and rows[offset]["baseline_center_xy_px"] is None: offset += 1
        end = offset - 1
        gap_id = f"{rows[0]['window_id']}:{rows[start]['source_frame_index']}-{rows[end]['source_frame_index']}"
        gap = {"gap_id": gap_id, "window_id": rows[0]["window_id"], "candidate_id": rows[0]["candidate_id"],
               "source_frame_range_inclusive": [rows[start]["source_frame_index"], rows[end]["source_frame_index"]],
               "first_source_pts_ticks": rows[start]["source_pts_ticks"], "last_source_pts_ticks": rows[end]["source_pts_ticks"],
               "frames": end-start+1, "time_base": POLICY["time_base"], "image_diagonal_px": diagonal,
               "candidate_radius_px": radius, "plausible_diameter_limit_px": diameter_limit,
               "anchors": None, "anchor_elapsed_seconds": None, "anchor_speed_diagonals_per_second": None,
               "status": "abstained", "reason": None, "frame_diagnostics": []}
        gaps.append(gap)
        if start == 0 or end == len(rows)-1:
            gap["reason"] = "window_edge_gap"
        else:
            left, right = rows[start-1], rows[end+1]
            gap["anchors"] = [{k: copy.deepcopy(anchor[k]) for k in ("source_frame_index", "source_pts_ticks", "baseline_center_xy_px")}
                              for anchor in (left, right)]
            dt_ticks = right["source_pts_ticks"]-left["source_pts_ticks"]
            elapsed = Fraction(dt_ticks, 90000)
            speed = math.dist(left["baseline_center_xy_px"], right["baseline_center_xy_px"]) / (diagonal*float(elapsed))
            gap.update(anchor_elapsed_seconds=float(elapsed), anchor_speed_diagonals_per_second=speed)
            if not _inside(left["baseline_center_xy_px"], left) or not _inside(right["baseline_center_xy_px"], right):
                gap["reason"] = "anchor_out_of_image"
            elif elapsed > Fraction(str(POLICY["max_anchor_elapsed_seconds"])):
                gap["reason"] = "anchor_elapsed_exceeds_limit"
            elif speed > POLICY["max_anchor_speed_diagonals_per_second"]:
                gap["reason"] = "anchor_speed_exceeds_limit"
            else:
                for position in range(start, end+1):
                    row = rows[position]
                    fraction = (row["source_pts_ticks"]-left["source_pts_ticks"]) / dt_ticks
                    expected = [a+(b-a)*fraction for a, b in zip(left["baseline_center_xy_px"], right["baseline_center_xy_px"])]
                    groups = _groups(row)
                    for group in groups: group["distance_to_expectation_px"] = math.dist(group["center_xy_px"], expected)
                    plausible = [g for g in groups if g["distance_to_expectation_px"] <= radius]
                    diameter = max((math.dist(a["center_xy_px"], b["center_xy_px"])
                                    for i, a in enumerate(plausible) for b in plausible[i+1:]), default=0.0)
                    acceptable = bool(plausible) and diameter <= diameter_limit
                    selected = min(plausible, key=lambda g: (g["distance_to_expectation_px"], g["record_indices"][0])) if acceptable else None
                    gap["frame_diagnostics"].append({"source_frame_index": row["source_frame_index"],
                        "source_pts_ticks": row["source_pts_ticks"], "expected_center_xy_px": expected,
                        "in_image_coordinate_groups": groups, "plausible_record_indices": [g["record_indices"] for g in plausible],
                        "plausible_pairwise_diameter_px": diameter, "acceptable": acceptable,
                        "proposed_pool_record_index": selected["record_indices"][0] if selected else None})
                rejected = [r for r in gap["frame_diagnostics"] if not r["acceptable"]]
                if rejected:
                    gap["reason"] = "gap_has_empty_or_ambiguous_frame"
                else:
                    gap.update(status="filled", reason="all_frames_have_unambiguous_saved_candidates")
        for position in range(start, end+1):
            decision = decisions[position]
            decision.update(gap_id=gap_id, reason=gap["reason"])
            if gap["status"] == "filled":
                detail = gap["frame_diagnostics"][position-start]
                index = detail["proposed_pool_record_index"]; record = rows[position]["pool_records"][index]
                group = next(g for g in detail["in_image_coordinate_groups"] if index in g["record_indices"])
                decision.update(decision="filled_saved_candidate", selected_center_xy_px=copy.deepcopy(record["center_xy_px"]),
                    selected_pool_record_index=index, selected_provenance_id=copy.deepcopy(record["provenance_id"]),
                    selected_coordinate_group=copy.deepcopy(group))
    return {"window_id": rows[0]["window_id"], "candidate_id": rows[0]["candidate_id"], "frames": decisions, "gaps": gaps}


def select_all(projected_windows):
    d.require(len({rows[0]["window_id"] for rows in projected_windows if rows}) == len(projected_windows),
              "Duplicate selection windows")
    windows = [select_window(rows) for rows in projected_windows]
    return {"schema_version": SCHEMA, "policy": POLICY, "windows": windows,
            "frames": [row for window in windows for row in window["frames"]],
            "labels_used": False, "human_review": "pending", "accepted": False}


def attach_provenance(selection, report):
    """Attach original component metadata after geometry choice, without labels."""
    indexed = {(r["window_id"], r["source_frame_index"]): r for r in report["frames"]}
    for decision in selection["frames"]:
        original = indexed[decision["window_id"], decision["source_frame_index"]]["old"]
        decision["original_selected"] = copy.deepcopy(original["original_selected"])
        records = original["pool"]["records"]
        if decision["decision"] == "preserved_original":
            index = original["original_selected"]["selected_candidate_index"]
            d.require(type(index) is int and 0 <= index < original["pool"]["mean_record_count"],
                      "Original component is outside mean prefix")
            record = records[index]
            d.require(record["component"]["candidate_index"] == index
                      and decision["selected_center_xy_px"] == [record["component"]["center_x"], record["component"]["center_y"]]
                      and original["original_selected"]["native_score"] == record["component"]["native_score"],
                      "Original selected component metadata differs")
            decision.update(selected_pool_record_index=index, selected_provenance_id=copy.deepcopy(record["provenance_id"]))
        index = decision["selected_pool_record_index"]
        decision["selected_component"] = copy.deepcopy(records[index]["component"]) if index is not None else None
        decision["selected_native_score"] = records[index]["component"]["native_score"] if index is not None else None
    return selection


def load_context(root, scope_path):
    scope = d.read_json(scope_path)
    d.require(scope["schema_version"] == "nba_temporal_gap_selection_scope/v0.1" and scope["status"] == "approved"
              and scope["authorization"]["approved_by"] == "Ryan" and scope["authorization"]["user_statement"],
              "Approved selector scope is required")
    d.require(scope["policy"] == POLICY and scope["gates"] == GATES, "Frozen selector policy or gates differ")
    d.require(scope["pre_execution_implementation"] == d.binding(root, Path(__file__))
              and scope["pre_execution_tests"] == d.binding(root, root/"tests/test_nba_temporal_gap_selection.py"),
              "Pre-execution implementation/test binding differs")
    pool_scope = read_bound(root, scope["pool_scope"])
    report = read_bound(root, scope["input_report"])
    design_path = d.contained(root, scope["pre_execution_design"]["path"])
    d.require(d.binding(root, design_path) == scope["pre_execution_design"], "Pre-execution design changed")
    d.require(pool_scope["schema_version"] == "nba_candidate_preservation_scope/v0.1"
              and pool_scope["status"] == "approved" and pool_scope["policy"] == pool_producer.POLICY
              and report["schema_version"] == pool_producer.SCHEMA and report["status"] == "completed"
              and report["policy"] == pool_producer.POLICY and report["bindings"]["scope"] == scope["pool_scope"],
              "Saved pool producer authority differs")
    d.require(scope["windows"] == pool_scope["windows"], "Selector changed the original twelve windows")
    d.require(scope["totals"] == {"frames": pool_scope["totals"]["frames"], "eligible": pool_scope["totals"]["eligible"],
              "hidden": pool_scope["totals"]["hidden"], "unknown": pool_scope["totals"]["unknown"], "windows": len(pool_scope["windows"])},
              "Scope totals differ from pool authority")
    indexed = {(r["window_id"], r["source_frame_index"]): r for r in report["frames"]}
    d.require(len(indexed) == len(report["frames"]) == scope["totals"]["frames"], "Duplicate or missing producer rows")
    expected = {(w["window_id"], i) for w in scope["windows"] for i in w["source_frame_indices"]}
    d.require(set(indexed) == expected, "Producer rows differ from frozen windows")
    manifests = {source["candidate_id"]: read_bound(root, source["input_manifest"]) for source in pool_scope["sources"]}
    native_frames = {}
    for cid, manifest in manifests.items():
        d.require(manifest["time_base"] == POLICY["time_base"], "Bound native source time base differs")
        native_frames[cid] = {f["source_frame_index"]: f for f in manifest["frames"]}
    projected = []
    for window in scope["windows"]:
        rows = [indexed[window["window_id"], i] for i in window["source_frame_indices"]]
        for row in rows:
            d.require(all(row[k] == window[k] for k in ("window_id", "candidate_id", "analysis_group", "cohort", "is_control"))
                      and row["source_frame_index"] == row["source_frame"]["source_frame_index"], "Producer source/window join differs")
            d.require(row["source_frame"] == native_frames[row["candidate_id"]].get(row["source_frame_index"])
                      and row["source_video"] == manifests[row["candidate_id"]]["source_video"],
                      "Saved source PNG/PTS/identity differs from original manifest")
            arm = row["old"]; records = arm["pool"]["records"]; n = arm["pool"]["mean_record_count"]
            d.require(0 <= n <= len(records), "Invalid mean-prefix length")
            d.require(arm["original_selected"]["state"] == ("missing" if arm["original_selected"]["center_xy_px"] is None else "observed"),
                      "Original selection state/center differs")
            for i, record in enumerate(records):
                pid = record["provenance_id"]
                d.require(pid[:3] == ["old", row["candidate_id"], row["source_frame_index"]]
                          and pid[3] == ("mean" if i < n else "contributor"), "Pool prefix/provenance differs")
                d.require(record["in_source_bounds"] == _inside([record["component"]["center_x"], record["component"]["center_y"]],
                          {"width_px": row["source_video"]["width_px"], "height_px": row["source_video"]["height_px"]}),
                          "Pool in-image flag differs")
            d.require(pool_producer.coordinate_groups(records) == arm["pool"]["coordinate_groups"], "Exact coordinate groups differ")
        geometry = [projection(row) for row in rows]; _validate_window(geometry); projected.append(geometry)
    return scope, report, projected


def score_point(row, center, candidates):
    """Recreate the original scorer's frame contract without reading its outcome."""
    frame, label, source = row["source_frame"], row["annotation"], row["source_video"]
    bounds = type("Bounds", (), {k: source[k] for k in ("width_px", "height_px")})()
    annotation = FrameAnnotation.from_mapping(label, 0, bounds)
    d.require(label["frame_index"] == row["source_frame_index"], "Reference/source frame join differs")
    result = {"source_frame_index": row["source_frame_index"], "source_pts_ticks": frame["source_pts_ticks"],
        "temporal_contributions": len(row["old"]["pool"]["contributor_planes"]), "visibility": label["visibility"],
        "outcome": "unscored", "raw_center_error_px": None, "uncertainty_adjusted_error_px": None, "raw_candidate_available": False}
    geometry = {"width_px": source["width_px"], "height_px": source["height_px"]}
    if annotation.localization_eligible:
        target = annotation.geometry.center_xy_px
        matches = lambda p: _inside(p, geometry) and math.hypot(p[0]-target[0], p[1]-target[1]) <= 10
        result["raw_candidate_available"] = any(matches([c["center_x"], c["center_y"]]) for c in candidates)
        if center is None: result["outcome"] = "missing"
        else:
            error = math.hypot(center[0]-target[0], center[1]-target[1])
            result.update(outcome="matched" if matches(center) else "wrong", raw_center_error_px=error,
                uncertainty_adjusted_error_px=max(0, error-annotation.geometry.uncertainty_radius_px))
    elif annotation.visibility == "not_visible" and annotation.game_ball_identity_certainty in {"certain", "probable"}:
        result["outcome"] = "hidden_alarm" if center is not None else "hidden_quiet"
    return result


def score(report, selection):
    decisions = {(r["window_id"], r["source_frame_index"]): r for r in selection["frames"]}
    d.require(len(decisions) == len(selection["frames"]) == len(report["frames"]), "Selection coverage differs")
    rows = []
    for row in report["frames"]:
        decision = decisions[row["window_id"], row["source_frame_index"]]
        old = row["old"]; pool = old["pool"]
        before = score_point(row, old["original_selected"]["center_xy_px"],
                             [r["component"] for r in pool["records"][:pool["mean_record_count"]]])
        d.require(before == old["original_score"], "Recreated original outcomes/errors differ")
        selected = decision["selected_center_xy_px"]
        d.require(decision["source_pts_ticks"] == row["source_frame"]["source_pts_ticks"]
                  and decision["baseline_center_xy_px"] == old["original_selected"]["center_xy_px"], "Decision/source join differs")
        if decision["baseline_center_xy_px"] is not None:
            d.require(selected == decision["baseline_center_xy_px"] and decision["decision"] == "preserved_original", "Original point changed")
        elif selected is not None:
            index = decision["selected_pool_record_index"]; record = pool["records"][index]
            d.require(selected == [record["component"]["center_x"], record["component"]["center_y"]]
                      and decision["selected_provenance_id"] == record["provenance_id"], "Selected coordinate was not a saved candidate")
        after = score_point(row, selected, [r["component"] for r in pool["records"]])
        category = pool_producer.eligibility(row["annotation"])
        d.require(category == row["eligibility"], "Reference eligibility differs")
        rows.append({k: copy.deepcopy(row[k]) for k in ("window_id", "candidate_id", "source_frame_index", "source_frame",
                    "source_video", "analysis_group", "cohort", "is_control", "annotation", "eligibility")})
        rows[-1].update(baseline=before, selected=after, decision=copy.deepcopy(decision),
                       changed=selected != decision["baseline_center_xy_px"])
    return rows


def _stats(values):
    return {"count": len(values), "mean": statistics.fmean(values) if values else None,
            "median": statistics.median(values) if values else None,
            "p95": float(np.percentile(values, 95, method="linear")) if values else None,
            "max": max(values) if values else None}


def aggregate(rows):
    result = {"frames": len(rows), "eligibility": dict(Counter(r["eligibility"] for r in rows))}
    for arm in ("baseline", "selected"):
        counts = Counter(r[arm]["outcome"] for r in rows)
        result[arm] = {k: counts[k] for k in ("matched", "wrong", "missing", "hidden_alarm", "hidden_quiet", "unscored")}
        for name, outcomes in (("emitted_eligible", {"matched", "wrong"}), ("matched", {"matched"}), ("wrong", {"wrong"})):
            result[arm]["raw_error_" + name + "_px"] = _stats([r[arm]["raw_center_error_px"] for r in rows if r[arm]["outcome"] in outcomes])
    result.update(changed_frames=sum(r["changed"] for r in rows),
        outcome_transitions=dict(Counter(f"{r['baseline']['outcome']} -> {r['selected']['outcome']}" for r in rows)),
        new_wrong=sum(r["selected"]["outcome"] == "wrong" and r["baseline"]["outcome"] != "wrong" for r in rows),
        new_hidden_alarm=sum(r["selected"]["outcome"] == "hidden_alarm" and r["baseline"]["outcome"] != "hidden_alarm" for r in rows))
    return result


def missing_intervals(rows, arm, *, eligible_only=True):
    """Native endpoints, with right-censoring instead of an invented final duration."""
    def is_missing(row):
        if eligible_only: return row[arm]["outcome"] == "missing"
        return row["decision"]["baseline_center_xy_px" if arm == "baseline" else "selected_center_xy_px"] is None
    result = []; offset = 0
    while offset < len(rows):
        if not is_missing(rows[offset]): offset += 1; continue
        start = offset
        while offset < len(rows) and is_missing(rows[offset]): offset += 1
        end = offset-1; first, last = rows[start], rows[end]
        first_pts, last_pts = first["source_frame"]["source_pts_ticks"], last["source_frame"]["source_pts_ticks"]
        next_pts = rows[offset]["source_frame"]["source_pts_ticks"] if offset < len(rows) else None
        result.append({"window_id": first["window_id"], "candidate_id": first["candidate_id"],
            "source_frame_range_inclusive": [first["source_frame_index"], last["source_frame_index"]],
            "first_source_pts_ticks": first_pts, "last_source_pts_ticks": last_pts, "time_base": POLICY["time_base"],
            "frames": end-start+1, "first_to_last_seconds": (last_pts-first_pts)/90000,
            "end_exclusive_pts_ticks": next_pts, "duration_seconds": (next_pts-first_pts)/90000 if next_pts is not None else None,
            "right_censored_at_window_end": next_pts is None})
    return result


def summarize(rows, scope, selection):
    by_group = {group: aggregate([r for r in rows if r["analysis_group"] == group])
                for group in dict.fromkeys(r["analysis_group"] for r in rows)}
    controls = {group: aggregate([r for r in rows if r["analysis_group"] == group and r["is_control"]]) for group in by_group}
    checks = {}
    group_names = {"det": "det_development", "nfhs": "nfhs_development"}
    for name, group in group_names.items():
        values = by_group[group]["selected"]
        for metric, limit in scope["gates"]["original_adaptation"][name].items():
            actual = controls[group]["selected"]["matched"] if metric == "easy_control_matched" else values[metric.rsplit("_", 1)[0]]
            checks[name+"_"+metric] = actual == limit if metric == "easy_control_matched" else actual >= limit if metric.endswith("_min") else actual <= limit
    checks["sac_easy_control_matched"] = controls["sac_training_fit"]["selected"]["matched"] == scope["gates"]["sac_easy_control_matched"]
    for group, values in by_group.items():
        for metric in ("wrong", "hidden_alarm"):
            checks[group+"_no_additional_"+metric] = values["selected"][metric] <= values["baseline"][metric]
    by_window = {}
    for window in scope["windows"]:
        selected_rows = sorted([r for r in rows if r["window_id"] == window["window_id"]], key=lambda r: r["source_frame_index"])
        by_window[window["window_id"]] = {**aggregate(selected_rows),
            "eligible_missing_intervals": {arm: missing_intervals(selected_rows, arm) for arm in ("baseline", "selected")},
            "output_missing_intervals": {arm: missing_intervals(selected_rows, arm, eligible_only=False) for arm in ("baseline", "selected")}}
    return {"overall": aggregate(rows), "by_analysis_group": by_group, "by_window": by_window, "controls_included_subset": controls,
        "by_visibility": {name: aggregate([r for r in rows if r["annotation"]["visibility"] == name])
                          for name in sorted({r["annotation"]["visibility"] for r in rows})},
        "by_eligibility": {name: aggregate([r for r in rows if r["eligibility"] == name]) for name in ("eligible", "hidden", "unknown")},
        "gap_decisions": dict(Counter(g["reason"] for w in selection["windows"] for g in w["gaps"])),
        "changed_frames": [r for r in rows if r["changed"]],
        "gates": {"constants": scope["gates"], "checks": checks, "numerical_candidate_pass": all(checks.values()),
                  "human_review": "pending", "accepted": False}}


def run(root, scope_path):
    root = Path(root).resolve(); scope_path = (root / scope_path).resolve()
    scope = d.read_json(scope_path); output = d.contained(root, scope["output_root"])
    d.require(output.is_relative_to(root/"data/outputs"), "Output must remain in ignored data")
    output.mkdir(parents=True, exist_ok=True); lock = d.acquire_run_lock(output/".run.lock")
    attempt = output/"attempts"/uuid.uuid4().hex; began = time.monotonic()
    resources = {"model_calls": 0, "checkpoint_loads": 0, "heatmap_array_reads": 0, "source_png_decode_events": 0, "video_decode_events": 0}
    try:
        d.require(not (output/"completion.json").exists(), "Preserve completed selector trial")
        bindings = {"scope": d.binding(root, scope_path), **{k: scope[k] for k in ("input_report", "pool_scope", "pre_execution_design")},
            "implementation": [d.binding(root, Path(__file__).with_name(name)) for name in
                ("nba_temporal_gap_selection.py", "nba_candidate_preservation.py", "nba_wasb_diagnostic.py", "nba_annotations.py",
                 "nba_adaptation_regression_diagnostic.py", "nba_adaptation_comparison.py", "annotations.py")],
            "focused_tests": d.binding(root, root/"tests/test_nba_temporal_gap_selection.py")}
        d.write_once(attempt/"started.json", {"status": "started", "at_utc": d.stamp(), "bindings": bindings})
        scope, producer_report, projected = load_context(root, scope_path)
        geometry_bytes = json.dumps(projected, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        selection = attach_provenance(select_all(projected), producer_report)
        selection.update(bindings=bindings, geometry_projection_sha256=hashlib.sha256(geometry_bytes).hexdigest())
        # This immutable artifact exists before score() is permitted to consume labels.
        d.write_once(attempt/"selection.json", selection)
        selection_binding = d.binding(root, attempt/"selection.json")
        rows = score(producer_report, selection)
        d.require(Counter(r["eligibility"] for r in rows) == {k: scope["totals"][k] for k in ("eligible", "hidden", "unknown")},
                  "Scored reference inventory differs")
        summary = summarize(rows, scope, selection)
        report = {"schema_version": SCHEMA, "status": "completed", "bindings": bindings, "selection": selection_binding,
                  "frames": rows, "summary": summary, "resources": resources, "human_review": "pending", "accepted": False}
        d.write_once(attempt/"report.json", report); d.write_once(attempt/"summary.json", summary)
        completion = {"schema_version": SCHEMA, "status": "completed", "bindings": bindings, "selection": selection_binding,
                      "report": d.binding(root, attempt/"report.json"), "summary": d.binding(root, attempt/"summary.json"),
                      "elapsed_seconds": time.monotonic()-began, "human_review": "pending", "accepted": False}
        d.write_once(attempt/"completed.json", completion); d.write_once(output/"completion.json", completion)
        return completion
    except Exception as error:
        d.write_once(attempt/"failed.json", {"status": "failed_preserved", "error_type": type(error).__name__, "error": str(error),
                     "resources": resources, "elapsed_seconds": time.monotonic()-began})
        raise
    finally: d.release_run_lock(lock)


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--scope", required=True)
    parser.add_argument("--run", action="store_true"); parser.add_argument("--check-scope", action="store_true"); args = parser.parse_args()
    if args.run == args.check_scope: parser.error("Choose exactly one of --run or --check-scope")
    root = Path.cwd(); path = root/args.scope
    if args.check_scope:
        scope, _, _ = load_context(root, path)
        print(json.dumps({"status": "scope_and_producer_records_verified", "scope": d.binding(root, path), "totals": scope["totals"]}, indent=2))
    else: print(json.dumps(run(root, path), indent=2))


if __name__ == "__main__": main()
