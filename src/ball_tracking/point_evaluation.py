"""Score temporal point observations without inventing boxes or probabilities.

The matching and visibility rules mirror ``evaluation.evaluate_detections``.
Native scores only order candidates; every supplied candidate is evaluated.
Coordinates outside the source image are retained as errors, never clamped.
This module deliberately does not change the reviewed raw-detector schema.
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections.abc import Mapping
from typing import Any

from .annotations import BallAnnotationSet, SourceVideo


POINT_RUN_SCHEMA_VERSION = "ball_point_observations/v0.1"
POINT_EVALUATION_SCHEMA_VERSION = "ball_point_evaluation/v0.1"
RUN_FIELDS = frozenset({
    "schema_version", "point_run_id", "annotation_set_id", "possession_id",
    "source_video", "window", "model_provenance", "frames",
})
FRAME_FIELDS = frozenset({
    "frame_index", "inference_status", "failure_reason", "candidates",
})
CANDIDATE_FIELDS = frozenset({"candidate_index", "center_xy_px", "native_score"})


class PointEvaluationError(ValueError):
    """Point observations cannot be compared with the reviewed annotations."""


def _fields(value: Any, expected: frozenset[str], label: str) -> Mapping:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise PointEvaluationError(f"{label} must contain exactly {sorted(expected)}")
    return value


def _number(value: Any, label: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PointEvaluationError(f"{label} must be a finite number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise PointEvaluationError(f"{label} must be finite") from exc
    if not math.isfinite(result) or (nonnegative and result < 0):
        raise PointEvaluationError(f"{label} must be finite" + (" and nonnegative" if nonnegative else ""))
    return result


def _json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PointEvaluationError("Point observations must contain finite JSON data") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def validate_point_run(annotation_set: BallAnnotationSet, point_run: Mapping) -> dict:
    """Return a JSON copy after checking identity, complete coverage and points.

    An empty candidate list means completed inference with no output. Missing,
    failed or unrun frames cannot be silently scored as model abstention.
    Candidate indices remain in the original per-frame namespace after a
    selector, so indices must be unique but need not be consecutive.
    """
    if not isinstance(annotation_set, BallAnnotationSet):
        raise PointEvaluationError("annotation_set must be a BallAnnotationSet")
    # Recheck dataclasses supplied directly as well as those loaded from JSON.
    annotation_set = BallAnnotationSet.from_mapping(annotation_set.to_dict())
    if annotation_set.review.status != "reviewed":
        raise PointEvaluationError("Point evaluation requires reviewed annotations")
    run = _fields(point_run, RUN_FIELDS, "point_run")
    if run["schema_version"] != POINT_RUN_SCHEMA_VERSION:
        raise PointEvaluationError("Unsupported point observation schema")
    if not isinstance(run["point_run_id"], str) or not run["point_run_id"].strip():
        raise PointEvaluationError("point_run_id must be a nonempty string")
    for field in ("annotation_set_id", "possession_id"):
        if run[field] != getattr(annotation_set, field):
            raise PointEvaluationError(f"Point run does not match {field}")
    if SourceVideo.from_mapping(run["source_video"]) != annotation_set.source_video:
        raise PointEvaluationError("Point run does not match source_video")
    window = _fields(run["window"], frozenset({"start_frame_index", "end_frame_index"}), "window")
    for field in window:
        if type(window[field]) is not int or window[field] != getattr(annotation_set.window, field):
            raise PointEvaluationError("Point run does not match annotation window")
    if not isinstance(run["model_provenance"], Mapping) or not run["model_provenance"]:
        raise PointEvaluationError("model_provenance must be a nonempty JSON object")
    if not all(isinstance(key, str) for key in run["model_provenance"]):
        raise PointEvaluationError("model_provenance keys must be strings")
    frames = run["frames"]
    if not isinstance(frames, list):
        raise PointEvaluationError("frames must be a JSON array")
    expected_ids = list(range(window["start_frame_index"], window["end_frame_index"] + 1))
    actual_ids = []
    for frame in frames:
        _fields(frame, FRAME_FIELDS, "frame")
        frame_id = frame["frame_index"]
        if type(frame_id) is not int:
            raise PointEvaluationError("frame_index must be an integer")
        actual_ids.append(frame_id)
        if frame["inference_status"] != "completed" or frame["failure_reason"] is not None:
            raise PointEvaluationError(f"Incomplete point inference at frame {frame_id}")
        candidates = frame["candidates"]
        if not isinstance(candidates, list):
            raise PointEvaluationError("Completed frames require a candidate array")
        indices = set()
        for candidate in candidates:
            _fields(candidate, CANDIDATE_FIELDS, "candidate")
            index = candidate["candidate_index"]
            if type(index) is not int or index < 0 or index in indices:
                raise PointEvaluationError("Candidate indices must be unique nonnegative integers")
            indices.add(index)
            center = candidate["center_xy_px"]
            if not isinstance(center, list) or len(center) != 2:
                raise PointEvaluationError("center_xy_px must be a two-number JSON array")
            for coordinate in center:
                _number(coordinate, "center coordinate")
            _number(candidate["native_score"], "native_score", nonnegative=True)
    if actual_ids != expected_ids:
        raise PointEvaluationError("Point frames must cover every inclusive window frame exactly once in order")
    return json.loads(_json_bytes(run))


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _errors(values: list[float]) -> dict:
    return {
        "count": len(values), "mean": statistics.fmean(values) if values else None,
        "median": statistics.median(values) if values else None,
        "maximum": max(values) if values else None,
    }


def evaluate_points(
    annotation_set: BallAnnotationSet,
    point_run: Mapping,
    *,
    localization_radius_px: float,
) -> dict[str, Any]:
    """Apply the reviewed raw-distance rules to all supplied point candidates.

    ``native_score`` is finite, nonnegative and unbounded. It is never treated
    as a probability or thresholded here. Among candidates within the inclusive
    radius, highest native score wins, with candidate index breaking ties.
    Other candidates are false positives; a wrong visible prediction also
    leaves a false negative. Annotation uncertainty is diagnostic only.
    """
    run = validate_point_run(annotation_set, point_run)
    radius = _number(localization_radius_px, "localization_radius_px", nonnegative=True)
    width, height = annotation_set.source_video.width_px, annotation_set.source_video.height_px
    results = []
    for annotation, frame in zip(annotation_set.annotations, run["frames"], strict=True):
        candidates = sorted(frame["candidates"], key=lambda c: (-c["native_score"], c["candidate_index"]))
        result = {
            "frame_index": frame["frame_index"], "annotation_status": annotation.annotation_status,
            "visibility": annotation.visibility, "scoring_status": "unscored",
            "input_detection_count": len(candidates), "accepted_detection_count": len(candidates),
            "matched_candidate_index": None, "false_positive_count": 0, "false_negative_count": 0,
            "duplicate_false_positive_count": 0, "non_visible_false_alarm_count": 0,
            "unscored_prediction_count": 0, "matched_center_error_px": None,
            "matched_effective_center_error_px": None,
        }
        if annotation.localization_eligible:
            result["scoring_status"] = "localization_eligible"
            geometry = annotation.geometry
            qualifying = []
            for candidate in candidates:
                x, y = candidate["center_xy_px"]
                error = math.hypot(x - geometry.center_xy_px[0], y - geometry.center_xy_px[1])
                if 0 <= x < width and 0 <= y < height and error <= radius:
                    qualifying.append((candidate, error))
            if qualifying:
                matched, error = qualifying[0]
                result["matched_candidate_index"] = matched["candidate_index"]
                result["matched_center_error_px"] = error
                result["matched_effective_center_error_px"] = max(0.0, error - geometry.uncertainty_radius_px)
                result["false_positive_count"] = len(candidates) - 1
                result["duplicate_false_positive_count"] = len(qualifying) - 1
            else:
                result["false_negative_count"] = 1
                result["false_positive_count"] = len(candidates)
        elif (annotation.annotation_status == "labeled" and annotation.visibility == "not_visible"
              and annotation.game_ball_identity_certainty in {"certain", "probable"}):
            result["scoring_status"] = "not_visible_negative"
            result["false_positive_count"] = len(candidates)
            result["non_visible_false_alarm_count"] = len(candidates)
        else:
            result["unscored_prediction_count"] = len(candidates)
        results.append(result)

    summed = (
        "input_detection_count", "false_positive_count", "false_negative_count",
        "duplicate_false_positive_count", "non_visible_false_alarm_count", "unscored_prediction_count",
    )
    metrics = {key: sum(frame[key] for frame in results) for key in summed}
    metrics.update(
        eligible_frame_count=sum(f["scoring_status"] == "localization_eligible" for f in results),
        not_visible_frame_count=sum(f["scoring_status"] == "not_visible_negative" for f in results),
        unscored_frame_count=sum(f["scoring_status"] == "unscored" for f in results),
        true_positive_count=sum(f["matched_candidate_index"] is not None for f in results),
        below_threshold_detection_count=0,
        non_visible_false_alarm_frame_count=sum(f["non_visible_false_alarm_count"] > 0 for f in results),
    )
    tp, fp, fn = (metrics[key] for key in ("true_positive_count", "false_positive_count", "false_negative_count"))
    negative_count = metrics["not_visible_frame_count"]
    metrics.update(
        precision=_ratio(tp, tp + fp), recall=_ratio(tp, tp + fn),
        non_visible_false_alarm_rate=_ratio(metrics["non_visible_false_alarm_frame_count"], negative_count),
        non_visible_false_alarms_per_100_frames=_ratio(100 * metrics["non_visible_false_alarm_count"], negative_count),
        matched_center_error_px=_errors([f["matched_center_error_px"] for f in results
                                        if f["matched_center_error_px"] is not None]),
        matched_effective_center_error_px=_errors([f["matched_effective_center_error_px"] for f in results
                                                  if f["matched_effective_center_error_px"] is not None]),
    )
    return {
        "evaluation_schema_version": POINT_EVALUATION_SCHEMA_VERSION,
        "annotation_set_id": annotation_set.annotation_set_id,
        "annotation_content_sha256": _digest(annotation_set.to_dict()),
        "point_run_id": run["point_run_id"], "point_run_content_sha256": _digest(run),
        "model_run_signature": _digest(run["model_provenance"]), "model_provenance": run["model_provenance"],
        "possession_id": annotation_set.possession_id,
        "source_video_path": annotation_set.source_video.path.as_posix(),
        "source_video_sha256": annotation_set.source_video.sha256,
        "window_start_frame_index": annotation_set.window.start_frame_index,
        "window_end_frame_index": annotation_set.window.end_frame_index,
        "selection_purpose": annotation_set.window.selection_purpose,
        "localization_radius_px": radius,
        "matching_rule": "inclusive raw source-pixel distance; uncertainty diagnostic only; out-of-image points cannot match",
        "candidate_order": "descending native_score, ascending candidate_index; all supplied candidates evaluated",
        **metrics, "frame_results": results,
    }
