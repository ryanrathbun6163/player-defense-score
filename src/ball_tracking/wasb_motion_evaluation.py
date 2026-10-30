"""Paired development scoring of saved longer-context WASB selections.

Only the six released annotation windows are opened. Both arms are projected
from the same supplied timeline and scored by the existing point evaluator;
this module never selects candidates, loads a model, or reads holdout labels.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from .annotations import BallAnnotationSet, SourceVideo
from .point_evaluation import POINT_RUN_SCHEMA_VERSION, evaluate_points
from .wasb_adaptation_experiment import paired_frame_changes
from .wasb_calibration import POOLS, summarize_reports


SCHEMA_VERSION = "wasb_motion_comparison/v0.1"
RADIUS_PX = 10


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _finite(value):
    return (type(value) in (int, float) and math.isfinite(value))


def _selection(row, prefix):
    index_key = "baseline_candidate_index" if prefix else "selected_candidate_index"
    center_key = "baseline_center_xy_px" if prefix else "center_xy_px"
    score_key = "baseline_native_score" if prefix else "native_score"
    if any(key not in row for key in (index_key, center_key, score_key)):
        raise ValueError("Timeline selection is missing candidate index, center or native mass")
    index, center, score = row[index_key], row[center_key], row[score_key]
    if index is None:
        if center is not None or score is not None:
            raise ValueError("Missing selection must preserve null center and native mass")
        return []
    if (type(index) is not int or index < 0 or not isinstance(center, list)
            or len(center) != 2 or not all(_finite(v) for v in center)
            or not _finite(score) or score < 0):
        raise ValueError("Selection requires an original index, finite center and nonnegative native mass")
    if "candidates" in row:
        candidates = row["candidates"]
        if not isinstance(candidates, list):
            raise ValueError("Original candidate inventory must be a list")
        ids = [candidate["candidate_index"] for candidate in candidates]
        if len(set(ids)) != len(ids) or index not in ids:
            raise ValueError("Selected candidate is absent or candidate indices repeat")
        original = candidates[ids.index(index)]
        if ([original["center_x"], original["center_y"]] != center
                or original["native_score"] != score):
            raise ValueError("Selection changed the original candidate center or native mass")
    return [{"candidate_index": index, "center_xy_px": center, "native_score": score}]


def _scope(split, timelines):
    if split.get("schema_version") != "ball_detector_experiment/v0.2":
        raise ValueError("Comparison requires the released development split")
    windows = split["windows"]
    if len(windows) != 6 or len({w["window_id"] for w in windows}) != 6:
        raise ValueError("Comparison requires exactly six unique development windows")
    if len({w["annotation_set_id"] for w in windows}) != 6:
        raise ValueError("Development annotation identities must be unique")
    possessions = {w["possession_id"] for w in windows}
    if len(possessions) != 3 or set(timelines) != possessions:
        raise ValueError("Comparison requires the same three development possessions")
    held = split["sealed_holdouts"]
    if len(held) != 3 or {h["possession_id"] for h in held} != possessions:
        raise ValueError("Missing or duplicate protected holdout metadata")
    seen = set()
    for pid in sorted(possessions):
        timeline = timelines[pid]
        source = SourceVideo.from_mapping(timeline["source_video"])
        members = [w for w in windows if w["possession_id"] == pid]
        if len(members) != 2 or {w["selection_purpose"] for w in members} != set(POOLS):
            raise ValueError("Each possession requires one window in each development pool")
        holdout = next(h for h in held if h["possession_id"] == pid)
        if (SourceVideo.from_mapping(holdout["source_video"]) != source
                or holdout["selection_purpose"] != "test_holdout"):
            raise ValueError("Protected source identity differs")
        low, high = holdout["start_frame_index"], holdout["end_frame_index"]
        if type(low) is not int or type(high) is not int or not 0 <= low <= high < source.frame_count:
            raise ValueError("Invalid protected frame range")
        low, high = max(0, low - 25), min(source.frame_count - 1, high + 25)
        rows = timeline["frames"]
        if (not isinstance(rows, list) or any(type(r.get("frame_index")) is not int for r in rows)
                or [r["frame_index"] for r in rows] != list(range(source.frame_count))):
            raise ValueError("Timeline must cover every source frame exactly once in order")
        for row in rows:
            if type(row.get("is_training_frame")) is not bool:
                raise ValueError("Every timeline frame requires explicit training membership")
            if row.get("state") not in {"observed", "missing", "withheld"}:
                raise ValueError("Unsupported timeline state")
            baseline, motion = _selection(row, True), _selection(row, False)
            if low <= row["frame_index"] <= high:
                if row["state"] != "withheld" or baseline or motion or row["is_training_frame"]:
                    raise ValueError("Protected frames must remain withheld with no selections or training")
            elif row["state"] == "withheld":
                raise ValueError("Unprotected frame cannot be withheld")
            elif (row["state"] == "observed") != bool(motion):
                raise ValueError("Motion state and selected candidate disagree")
        for window in members:
            start, end = window["start_frame_index"], window["end_frame_index"]
            if (type(start) is not int or type(end) is not int or not 0 <= start <= end < source.frame_count
                    or end - start != 24 or window["execution_status"] != "ready_for_inference"
                    or SourceVideo.from_mapping(window["source_video"]) != source):
                raise ValueError("Released window bounds, status or source differ")
            if max(start, low) <= min(end, high):
                raise ValueError("Development scoring intersects withheld frames")
            for index in range(start, end + 1):
                if (pid, index) in seen:
                    raise ValueError("Development windows overlap")
                seen.add((pid, index))
                if rows[index]["is_training_frame"] or rows[index]["state"] == "withheld":
                    raise ValueError("Development scoring cannot include training or withheld frames")
    if len(seen) != 150:
        raise ValueError("Comparison requires exactly 150 distinct development frames")


def _point_run(labels, window, rows, arm, timeline_digest):
    return {
        "schema_version": POINT_RUN_SCHEMA_VERSION,
        "point_run_id": window["window_id"] + "_longer_context_" + arm,
        "annotation_set_id": labels.annotation_set_id, "possession_id": labels.possession_id,
        "source_video": labels.source_video.to_dict(),
        "window": {"start_frame_index": labels.window.start_frame_index,
                   "end_frame_index": labels.window.end_frame_index},
        "model_provenance": {"arm": arm, "timeline_content_sha256": timeline_digest,
                             "native_score_definition": "unchanged saved component mass",
                             "context": "same longer-context observations for both arms"},
        "frames": [{"frame_index": row["frame_index"], "inference_status": "completed",
                    "failure_reason": None, "candidates": _selection(row, arm == "baseline")}
                   for row in rows],
    }


def _outcome(frame):
    if frame["scoring_status"] == "not_visible_negative":
        return "hidden_alarm" if frame["accepted_detection_count"] else "hidden_absent"
    if frame["matched_candidate_index"] is not None:
        return "matched"
    return "wrong_present" if frame["accepted_detection_count"] else "missing"


def _changes(baseline, motion):
    result = paired_frame_changes(motion, baseline)
    result.update(hidden_alarm_added_frame_indices=[], hidden_alarm_removed_frame_indices=[],
                  shared_hidden_alarm_frame_indices=[], frame_changes=[])
    for old, new in zip(baseline["frame_results"], motion["frame_results"], strict=True):
        index = old["frame_index"]
        old_alarm, new_alarm = old["non_visible_false_alarm_count"] > 0, new["non_visible_false_alarm_count"] > 0
        if old_alarm or new_alarm:
            key = ("shared_hidden_alarm" if old_alarm and new_alarm else
                   "hidden_alarm_added" if new_alarm else "hidden_alarm_removed")
            result[key + "_frame_indices"].append(index)
        result["frame_changes"].append({"frame_index": index, "scoring_status": old["scoring_status"],
            "baseline_outcome": _outcome(old), "motion_outcome": _outcome(new),
            "baseline_matched_error_px": old["matched_center_error_px"],
            "motion_matched_error_px": new["matched_center_error_px"],
            "match_gained": old["matched_candidate_index"] is None and new["matched_candidate_index"] is not None,
            "match_lost": old["matched_candidate_index"] is not None and new["matched_candidate_index"] is None})
    return result


def _summary(windows):
    change_names = ("recovered", "lost", "shared", "hidden_alarm_added", "hidden_alarm_removed", "shared_hidden_alarm")
    return {"baseline": summarize_reports([w["baseline_report"] for w in windows]),
            "motion": summarize_reports([w["motion_report"] for w in windows]),
            "changes": {name: sum(len(w["changes"][name + "_frame_indices"]) for w in windows)
                        for name in change_names}}


def evaluate_comparison(root: Path, split: dict, timelines: dict) -> dict:
    """Score exactly 150 released non-training frames, returning JSON data only.

    The caller verifies the split file binding and independently derives training
    membership from the bound training configuration. Full timelines must carry
    both arms' unchanged native masses, plus null withheld placeholders.
    """
    _scope(split, timelines)  # Reject invalid/holdout scope before opening labels.
    root = root.resolve()
    digests = {pid: _digest(timeline) for pid, timeline in timelines.items()}
    windows = []
    for window in split["windows"]:
        annotation_id = window["annotation_set_id"]
        if not isinstance(annotation_id, str) or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in annotation_id):
            raise ValueError("Unsafe annotation identity")
        path = (root / "configs/ball_tracking/annotations" / (annotation_id + ".json")).resolve()
        path.relative_to((root / "configs/ball_tracking/annotations").resolve())
        path.relative_to(root)
        raw = path.read_bytes()
        labels = BallAnnotationSet.from_mapping(json.loads(raw))
        if (labels.annotation_set_id != annotation_id or labels.possession_id != window["possession_id"]
                or labels.source_video != SourceVideo.from_mapping(window["source_video"])
                or labels.window.start_frame_index != window["start_frame_index"]
                or labels.window.end_frame_index != window["end_frame_index"]
                or labels.window.selection_purpose != window["selection_purpose"]):
            raise ValueError("Development annotation identity, window or source differs")
        pid = window["possession_id"]
        rows = timelines[pid]["frames"][window["start_frame_index"]:window["end_frame_index"] + 1]
        reports = {arm: evaluate_points(labels, _point_run(labels, window, rows, arm, digests[pid]),
                                       localization_radius_px=RADIUS_PX) for arm in ("baseline", "motion")}
        windows.append({"window_id": window["window_id"], "possession_id": pid,
            "purpose": window["selection_purpose"], "source_video": labels.source_video.to_dict(),
            "annotation": {"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(raw).hexdigest()},
            "baseline_report": reports["baseline"], "motion_report": reports["motion"],
            "changes": _changes(reports["baseline"], reports["motion"])})
    summary = _summary(windows)
    for arm in ("baseline", "motion"):
        if (summary[arm]["frame_count"], summary[arm]["eligible"], summary[arm]["hidden"]) != (150, 145, 5):
            raise ValueError("Released labels must retain 150 frames, 145 eligible and five hidden")
    return {"schema_version": SCHEMA_VERSION, "split_content_sha256": _digest(split),
        "timeline_content_sha256": digests, "localization_radius_px": RADIUS_PX,
        "comparison_context": "paired selections from identical longer-context frames; short-window scores are not the control",
        "windows": windows, "pools": {pool: _summary([w for w in windows if w["purpose"] == pool]) for pool in POOLS},
        "summary": summary, "training_frames_scored": 0, "withheld_frames_scored": 0,
        "selected_operating_point": None, "quality_gate": None, "human_visual_review": "pending",
        "limitations": ["Repeatedly inspected same-game development frames are not independent generalization evidence",
                        "Geometric matches do not independently establish ball identity",
                        "Longer observation includes training frames, but these six scoring windows exclude them"]}
