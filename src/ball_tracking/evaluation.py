"""Pure evaluation for reviewed ball annotations and persisted detections."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from src.ball_tracking.annotations import BallAnnotationSet
from src.ball_tracking.detections import BallDetectionRun, ModelProvenance


EVALUATION_SCHEMA_VERSION = "ball_detection_evaluation/v0.1"

FRAME_RESULT_FIELDS = frozenset(
    {
        "frame_index",
        "annotation_status",
        "visibility",
        "scoring_status",
        "input_detection_count",
        "accepted_detection_count",
        "matched_candidate_index",
        "false_positive_count",
        "false_negative_count",
        "duplicate_false_positive_count",
        "non_visible_false_alarm_count",
        "unscored_prediction_count",
        "matched_center_error_px",
        "matched_effective_center_error_px",
    }
)

ERROR_SUMMARY_FIELDS = frozenset({"count", "mean", "median", "maximum"})

EVALUATION_REPORT_FIELDS = frozenset(
    {
        "evaluation_schema_version",
        "annotation_set_id",
        "annotation_content_sha256",
        "detection_run_id",
        "detection_run_content_sha256",
        "model_run_signature",
        "model_provenance",
        "possession_id",
        "source_video_path",
        "source_video_sha256",
        "window_start_frame_index",
        "window_end_frame_index",
        "selection_purpose",
        "confidence_threshold",
        "localization_radius_px",
        "eligible_frame_count",
        "not_visible_frame_count",
        "unscored_frame_count",
        "input_detection_count",
        "below_threshold_detection_count",
        "true_positive_count",
        "false_positive_count",
        "false_negative_count",
        "duplicate_false_positive_count",
        "non_visible_false_alarm_count",
        "non_visible_false_alarm_frame_count",
        "non_visible_false_alarm_rate",
        "non_visible_false_alarms_per_100_frames",
        "unscored_prediction_count",
        "precision",
        "recall",
        "matched_center_error_px",
        "matched_effective_center_error_px",
        "frame_results",
    }
)


class DetectionEvaluationError(ValueError):
    """Raised when annotations, detections, or reports cannot be compared."""


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DetectionEvaluationError(f"{label} must be a finite number")

    result = float(value)

    if not math.isfinite(result):
        raise DetectionEvaluationError(f"{label} must be a finite number")

    return result


def _require_unit_interval(value: Any, label: str) -> float:
    result = _require_finite_number(value, label)

    if not 0.0 <= result <= 1.0:
        raise DetectionEvaluationError(
            f"{label} must be between 0 and 1 inclusive"
        )

    return result


def _require_nonnegative_number(value: Any, label: str) -> float:
    result = _require_finite_number(value, label)

    if result < 0.0:
        raise DetectionEvaluationError(f"{label} must be non-negative")

    return result


def _require_nonnegative_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DetectionEvaluationError(
            f"{label} must be a non-negative integer"
        )

    return value


def _require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DetectionEvaluationError(f"{label} must be a non-empty string")

    return value


def _require_sha256(value: Any, label: str) -> str:
    result = _require_nonempty_string(value, label)

    if len(result) != 64 or any(
        character not in "0123456789abcdef" for character in result
    ):
        raise DetectionEvaluationError(
            f"{label} must contain exactly 64 lowercase hexadecimal characters"
        )

    return result


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DetectionEvaluationError(f"{label} must be a mapping")

    return value


def _require_exact_fields(
    value: Mapping[str, Any],
    expected_fields: frozenset[str],
    label: str,
) -> None:
    actual_fields = set(value)
    missing_fields = sorted(expected_fields - actual_fields)
    unknown_fields = sorted(actual_fields - expected_fields)

    if missing_fields or unknown_fields:
        raise DetectionEvaluationError(
            f"{label} fields do not match schema; "
            f"missing={missing_fields}, unknown={unknown_fields}"
        )


def _require_optional_nonnegative_number(
    value: Any,
    label: str,
) -> float | None:
    if value is None:
        return None

    return _require_nonnegative_number(value, label)


def _require_report_value(
    actual: Any,
    expected: Any,
    label: str,
) -> None:
    if actual != expected:
        raise DetectionEvaluationError(
            f"{label} does not match frame_results; "
            f"expected {expected!r}, received {actual!r}"
        )


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None

    return numerator / denominator


def _error_summary(values: Sequence[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "maximum": None,
        }

    return {
        "count": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "maximum": max(values),
    }


def _validate_error_summary(
    value: Any,
    expected: Mapping[str, Any],
    label: str,
) -> None:
    summary = _require_mapping(value, label)
    _require_exact_fields(summary, ERROR_SUMMARY_FIELDS, label)
    count = _require_nonnegative_integer(summary["count"], f"{label}.count")
    normalized: dict[str, Any] = {"count": count}

    for field in ("mean", "median", "maximum"):
        normalized[field] = _require_optional_nonnegative_number(
            summary[field],
            f"{label}.{field}",
        )

    if count == 0 and any(
        normalized[field] is not None
        for field in ("mean", "median", "maximum")
    ):
        raise DetectionEvaluationError(
            f"{label} statistics must be null when count is zero"
        )

    if count > 0 and any(
        normalized[field] is None
        for field in ("mean", "median", "maximum")
    ):
        raise DetectionEvaluationError(
            f"{label} statistics are required when count is positive"
        )

    _require_report_value(normalized, dict(expected), label)


def _validate_evaluation_report(
    report: Mapping[str, Any],
    report_index: int,
) -> dict[str, Any]:
    label = f"reports[{report_index}]"
    _require_exact_fields(report, EVALUATION_REPORT_FIELDS, label)

    if report["evaluation_schema_version"] != EVALUATION_SCHEMA_VERSION:
        raise DetectionEvaluationError(
            f"{label}.evaluation_schema_version must be "
            f"{EVALUATION_SCHEMA_VERSION!r}"
        )

    annotation_set_id = _require_nonempty_string(
        report["annotation_set_id"],
        f"{label}.annotation_set_id",
    )
    annotation_content_sha256 = _require_sha256(
        report["annotation_content_sha256"],
        f"{label}.annotation_content_sha256",
    )
    detection_run_id = _require_nonempty_string(
        report["detection_run_id"],
        f"{label}.detection_run_id",
    )
    detection_run_content_sha256 = _require_sha256(
        report["detection_run_content_sha256"],
        f"{label}.detection_run_content_sha256",
    )
    declared_model_signature = _require_sha256(
        report["model_run_signature"],
        f"{label}.model_run_signature",
    )

    try:
        model_provenance = ModelProvenance.from_mapping(
            report["model_provenance"]
        )
    except ValueError as error:
        raise DetectionEvaluationError(
            f"{label}.model_provenance is invalid: {error}"
        ) from error

    expected_model_signature = _canonical_sha256(
        model_provenance.to_dict()
    )

    if declared_model_signature != expected_model_signature:
        raise DetectionEvaluationError(
            f"{label}.model_run_signature does not match model_provenance"
        )

    possession_id = _require_nonempty_string(
        report["possession_id"],
        f"{label}.possession_id",
    )
    _require_nonempty_string(
        report["source_video_path"],
        f"{label}.source_video_path",
    )
    source_video_sha256 = _require_sha256(
        report["source_video_sha256"],
        f"{label}.source_video_sha256",
    )
    window_start = _require_nonnegative_integer(
        report["window_start_frame_index"],
        f"{label}.window_start_frame_index",
    )
    window_end = _require_nonnegative_integer(
        report["window_end_frame_index"],
        f"{label}.window_end_frame_index",
    )

    if window_end < window_start:
        raise DetectionEvaluationError(
            f"{label} window end cannot precede start"
        )

    selection_purpose = _require_nonempty_string(
        report["selection_purpose"],
        f"{label}.selection_purpose",
    )
    threshold = _require_unit_interval(
        report["confidence_threshold"],
        f"{label}.confidence_threshold",
    )
    radius = _require_nonnegative_number(
        report["localization_radius_px"],
        f"{label}.localization_radius_px",
    )

    if threshold < model_provenance.export_confidence_floor:
        raise DetectionEvaluationError(
            f"{label}.confidence_threshold cannot be below "
            "model_provenance.export_confidence_floor"
        )

    frame_results = report["frame_results"]

    if isinstance(frame_results, (str, bytes)) or not isinstance(
        frame_results,
        Sequence,
    ):
        raise DetectionEvaluationError(f"{label}.frame_results must be a sequence")

    expected_frame_count = window_end - window_start + 1

    if len(frame_results) != expected_frame_count:
        raise DetectionEvaluationError(
            f"{label}.frame_results must cover every frame in the window"
        )

    derived_counts = {
        "eligible_frame_count": 0,
        "not_visible_frame_count": 0,
        "unscored_frame_count": 0,
        "input_detection_count": 0,
        "below_threshold_detection_count": 0,
        "true_positive_count": 0,
        "false_positive_count": 0,
        "false_negative_count": 0,
        "duplicate_false_positive_count": 0,
        "non_visible_false_alarm_count": 0,
        "non_visible_false_alarm_frame_count": 0,
        "unscored_prediction_count": 0,
    }
    matched_center_errors = []
    matched_effective_center_errors = []

    for frame_position, frame_value in enumerate(frame_results):
        frame_label = f"{label}.frame_results[{frame_position}]"
        frame = _require_mapping(frame_value, frame_label)
        _require_exact_fields(frame, FRAME_RESULT_FIELDS, frame_label)
        expected_frame_index = window_start + frame_position
        frame_index = _require_nonnegative_integer(
            frame["frame_index"],
            f"{frame_label}.frame_index",
        )

        if frame_index != expected_frame_index:
            raise DetectionEvaluationError(
                f"{frame_label}.frame_index must be {expected_frame_index}"
            )

        annotation_status = frame["annotation_status"]

        if annotation_status not in {"labeled", "unlabeled", "excluded"}:
            raise DetectionEvaluationError(
                f"{frame_label}.annotation_status is invalid"
            )

        visibility = frame["visibility"]

        if visibility not in {
            None,
            "fully_visible",
            "partially_visible",
            "not_visible",
            "indeterminate",
        }:
            raise DetectionEvaluationError(
                f"{frame_label}.visibility is invalid"
            )

        scoring_status = frame["scoring_status"]

        if scoring_status not in {
            "localization_eligible",
            "not_visible_negative",
            "unscored",
        }:
            raise DetectionEvaluationError(
                f"{frame_label}.scoring_status is invalid"
            )

        input_count = _require_nonnegative_integer(
            frame["input_detection_count"],
            f"{frame_label}.input_detection_count",
        )
        accepted_count = _require_nonnegative_integer(
            frame["accepted_detection_count"],
            f"{frame_label}.accepted_detection_count",
        )

        if accepted_count > input_count:
            raise DetectionEvaluationError(
                f"{frame_label}.accepted_detection_count cannot exceed input"
            )

        frame_counts = {}

        for field in (
            "false_positive_count",
            "false_negative_count",
            "duplicate_false_positive_count",
            "non_visible_false_alarm_count",
            "unscored_prediction_count",
        ):
            frame_counts[field] = _require_nonnegative_integer(
                frame[field],
                f"{frame_label}.{field}",
            )

        matched_candidate_index = frame["matched_candidate_index"]

        if matched_candidate_index is not None:
            matched_candidate_index = _require_nonnegative_integer(
                matched_candidate_index,
                f"{frame_label}.matched_candidate_index",
            )

        center_error = _require_optional_nonnegative_number(
            frame["matched_center_error_px"],
            f"{frame_label}.matched_center_error_px",
        )
        effective_error = _require_optional_nonnegative_number(
            frame["matched_effective_center_error_px"],
            f"{frame_label}.matched_effective_center_error_px",
        )
        matched = matched_candidate_index is not None

        if matched != (center_error is not None) or matched != (
            effective_error is not None
        ):
            raise DetectionEvaluationError(
                f"{frame_label} match index and error fields must agree"
            )

        if matched and effective_error > center_error:
            raise DetectionEvaluationError(
                f"{frame_label} effective error cannot exceed raw error"
            )

        if matched and matched_candidate_index >= input_count:
            raise DetectionEvaluationError(
                f"{frame_label}.matched_candidate_index is outside the "
                "input detection range"
            )

        if matched and center_error > radius:
            raise DetectionEvaluationError(
                f"{frame_label}.matched_center_error_px exceeds the "
                "localization radius"
            )

        if scoring_status == "localization_eligible":
            if annotation_status != "labeled" or visibility not in {
                "fully_visible",
                "partially_visible",
            }:
                raise DetectionEvaluationError(
                    f"{frame_label} localization eligibility conflicts with "
                    "annotation semantics"
                )

            derived_counts["eligible_frame_count"] += 1
            expected_false_negative_count = 0 if matched else 1
            expected_false_positive_count = accepted_count - int(matched)

            if expected_false_positive_count < 0:
                raise DetectionEvaluationError(
                    f"{frame_label} matched frame has no accepted detection"
                )

            _require_report_value(
                frame_counts["false_negative_count"],
                expected_false_negative_count,
                f"{frame_label}.false_negative_count",
            )
            _require_report_value(
                frame_counts["false_positive_count"],
                expected_false_positive_count,
                f"{frame_label}.false_positive_count",
            )

            if not matched and frame_counts["duplicate_false_positive_count"]:
                raise DetectionEvaluationError(
                    f"{frame_label} unmatched frame cannot contain duplicates"
                )

            if (
                frame_counts["duplicate_false_positive_count"]
                > frame_counts["false_positive_count"]
            ):
                raise DetectionEvaluationError(
                    f"{frame_label} duplicate false positives exceed all "
                    "false positives"
                )

            if (
                frame_counts["non_visible_false_alarm_count"]
                or frame_counts["unscored_prediction_count"]
            ):
                raise DetectionEvaluationError(
                    f"{frame_label} localization frame has incompatible counts"
                )

            if matched:
                derived_counts["true_positive_count"] += 1
                matched_center_errors.append(center_error)
                matched_effective_center_errors.append(effective_error)
        elif scoring_status == "not_visible_negative":
            if annotation_status != "labeled" or visibility != "not_visible":
                raise DetectionEvaluationError(
                    f"{frame_label} negative scoring conflicts with annotation"
                )

            derived_counts["not_visible_frame_count"] += 1
            expected_zero_fields = (
                "false_negative_count",
                "duplicate_false_positive_count",
                "unscored_prediction_count",
            )

            if matched or any(frame_counts[field] for field in expected_zero_fields):
                raise DetectionEvaluationError(
                    f"{frame_label} negative frame has incompatible match/counts"
                )

            _require_report_value(
                frame_counts["false_positive_count"],
                accepted_count,
                f"{frame_label}.false_positive_count",
            )
            _require_report_value(
                frame_counts["non_visible_false_alarm_count"],
                accepted_count,
                f"{frame_label}.non_visible_false_alarm_count",
            )

            if accepted_count:
                derived_counts["non_visible_false_alarm_frame_count"] += 1
        else:
            derived_counts["unscored_frame_count"] += 1

            if matched or any(
                frame_counts[field]
                for field in (
                    "false_positive_count",
                    "false_negative_count",
                    "duplicate_false_positive_count",
                    "non_visible_false_alarm_count",
                )
            ):
                raise DetectionEvaluationError(
                    f"{frame_label} unscored frame has incompatible match/counts"
                )

            _require_report_value(
                frame_counts["unscored_prediction_count"],
                accepted_count,
                f"{frame_label}.unscored_prediction_count",
            )

        derived_counts["input_detection_count"] += input_count
        derived_counts["below_threshold_detection_count"] += (
            input_count - accepted_count
        )

        for field in (
            "false_positive_count",
            "false_negative_count",
            "duplicate_false_positive_count",
            "non_visible_false_alarm_count",
            "unscored_prediction_count",
        ):
            derived_counts[field] += frame_counts[field]

    for field, expected_value in derived_counts.items():
        actual_value = _require_nonnegative_integer(
            report[field],
            f"{label}.{field}",
        )
        _require_report_value(actual_value, expected_value, f"{label}.{field}")

    expected_precision = _safe_ratio(
        derived_counts["true_positive_count"],
        derived_counts["true_positive_count"]
        + derived_counts["false_positive_count"],
    )
    expected_recall = _safe_ratio(
        derived_counts["true_positive_count"],
        derived_counts["true_positive_count"]
        + derived_counts["false_negative_count"],
    )
    expected_false_alarm_rate = _safe_ratio(
        derived_counts["non_visible_false_alarm_frame_count"],
        derived_counts["not_visible_frame_count"],
    )
    expected_false_alarms_per_100_frames = (
        None
        if derived_counts["not_visible_frame_count"] == 0
        else 100.0
        * derived_counts["non_visible_false_alarm_count"]
        / derived_counts["not_visible_frame_count"]
    )

    for field, expected_value in (
        ("precision", expected_precision),
        ("recall", expected_recall),
        ("non_visible_false_alarm_rate", expected_false_alarm_rate),
        (
            "non_visible_false_alarms_per_100_frames",
            expected_false_alarms_per_100_frames,
        ),
    ):
        actual_value = _require_optional_nonnegative_number(
            report[field],
            f"{label}.{field}",
        )
        _require_report_value(actual_value, expected_value, f"{label}.{field}")

    _validate_error_summary(
        report["matched_center_error_px"],
        _error_summary(matched_center_errors),
        f"{label}.matched_center_error_px",
    )
    _validate_error_summary(
        report["matched_effective_center_error_px"],
        _error_summary(matched_effective_center_errors),
        f"{label}.matched_effective_center_error_px",
    )

    return {
        "annotation_set_id": annotation_set_id,
        "annotation_content_sha256": annotation_content_sha256,
        "detection_run_id": detection_run_id,
        "detection_run_content_sha256": detection_run_content_sha256,
        "model_run_signature": declared_model_signature,
        "possession_id": possession_id,
        "source_video_sha256": source_video_sha256,
        "window_start_frame_index": window_start,
        "window_end_frame_index": window_end,
        "selection_purpose": selection_purpose,
        "confidence_threshold": threshold,
        "localization_radius_px": radius,
        "counts": {
            field: derived_counts[field]
            for field in (
                "true_positive_count",
                "false_positive_count",
                "false_negative_count",
                "duplicate_false_positive_count",
                "non_visible_false_alarm_count",
            )
        },
    }


def _validate_run_binding(
    annotation_set: BallAnnotationSet,
    detection_run: BallDetectionRun,
) -> None:
    mismatches = []

    if detection_run.annotation_set_id != annotation_set.annotation_set_id:
        mismatches.append("annotation_set_id")

    if detection_run.possession_id != annotation_set.possession_id:
        mismatches.append("possession_id")

    if detection_run.source_video != annotation_set.source_video:
        mismatches.append("source_video")

    if (
        detection_run.window.start_frame_index
        != annotation_set.window.start_frame_index
        or detection_run.window.end_frame_index
        != annotation_set.window.end_frame_index
    ):
        mismatches.append("window")

    if mismatches:
        raise DetectionEvaluationError(
            "Detection run does not match annotation contract: "
            f"{sorted(mismatches)}"
        )

    incomplete_frames = [
        frame.frame_index
        for frame in detection_run.frames
        if frame.inference_status != "completed"
    ]

    if incomplete_frames:
        raise DetectionEvaluationError(
            "Detection run has incomplete inference frames: "
            f"{incomplete_frames}"
        )


def evaluate_detections(
    annotation_set: BallAnnotationSet,
    detection_run: BallDetectionRun,
    *,
    confidence_threshold: float,
    localization_radius_px: float,
) -> dict[str, Any]:
    """Evaluate one complete, provenance-bound raw detection run.

    Primary matching uses raw source-pixel center distance. Annotation
    uncertainty remains visible in a diagnostic effective-error field, but it
    cannot turn an otherwise out-of-radius prediction into a true positive.
    """

    if not isinstance(annotation_set, BallAnnotationSet):
        raise DetectionEvaluationError(
            "annotation_set must be a BallAnnotationSet"
        )

    if not isinstance(detection_run, BallDetectionRun):
        raise DetectionEvaluationError(
            "detection_run must be a BallDetectionRun"
        )

    if annotation_set.review.status != "reviewed":
        raise DetectionEvaluationError(
            "Detection evaluation requires a reviewed annotation set"
        )

    _validate_run_binding(annotation_set, detection_run)
    threshold = _require_unit_interval(
        confidence_threshold,
        "confidence_threshold",
    )
    radius = _require_nonnegative_number(
        localization_radius_px,
        "localization_radius_px",
    )
    export_floor = detection_run.model_provenance.export_confidence_floor

    if threshold < export_floor:
        raise DetectionEvaluationError(
            "confidence_threshold cannot be below the detection run's "
            "export_confidence_floor"
        )

    annotations_by_frame = annotation_set.annotation_by_frame()
    detections_by_frame = detection_run.frame_by_index()

    eligible_frame_count = 0
    not_visible_frame_count = 0
    unscored_frame_count = 0
    true_positive_count = 0
    false_positive_count = 0
    false_negative_count = 0
    duplicate_false_positive_count = 0
    non_visible_false_alarm_count = 0
    non_visible_false_alarm_frame_count = 0
    unscored_prediction_count = 0
    input_detection_count = 0
    below_threshold_detection_count = 0
    matched_center_errors = []
    matched_effective_center_errors = []
    frame_results = []

    for frame_index, annotation in annotations_by_frame.items():
        detection_frame = detections_by_frame[frame_index]
        detections = detection_frame.detections

        if detections is None:
            raise DetectionEvaluationError(
                "Completed detection frame unexpectedly lacks detections: "
                f"{frame_index}"
            )

        input_detection_count += len(detections)
        accepted = [
            detection
            for detection in detections
            if detection.confidence >= threshold
        ]
        below_threshold_detection_count += len(detections) - len(accepted)
        accepted.sort(
            key=lambda detection: (
                -detection.confidence,
                detection.candidate_index,
            )
        )
        frame_result = {
            "frame_index": frame_index,
            "annotation_status": annotation.annotation_status,
            "visibility": annotation.visibility,
            "scoring_status": None,
            "input_detection_count": len(detections),
            "accepted_detection_count": len(accepted),
            "matched_candidate_index": None,
            "false_positive_count": 0,
            "false_negative_count": 0,
            "duplicate_false_positive_count": 0,
            "non_visible_false_alarm_count": 0,
            "unscored_prediction_count": 0,
            "matched_center_error_px": None,
            "matched_effective_center_error_px": None,
        }

        if annotation.localization_eligible:
            eligible_frame_count += 1
            frame_result["scoring_status"] = "localization_eligible"
            geometry = annotation.geometry

            if geometry is None:
                raise DetectionEvaluationError(
                    "Validated annotation unexpectedly lacks geometry: "
                    f"frame {frame_index}"
                )

            qualifying = []

            for detection in accepted:
                delta_x = detection.center_xy_px[0] - geometry.center_xy_px[0]
                delta_y = detection.center_xy_px[1] - geometry.center_xy_px[1]
                center_error = math.hypot(delta_x, delta_y)
                effective_error = max(
                    0.0,
                    center_error - geometry.uncertainty_radius_px,
                )

                if center_error <= radius:
                    qualifying.append(
                        (detection, center_error, effective_error)
                    )

            if qualifying:
                matched, center_error, effective_error = qualifying[0]
                true_positive_count += 1
                frame_result["matched_candidate_index"] = (
                    matched.candidate_index
                )
                frame_result["matched_center_error_px"] = center_error
                frame_result[
                    "matched_effective_center_error_px"
                ] = effective_error
                matched_center_errors.append(center_error)
                matched_effective_center_errors.append(effective_error)
                frame_false_positives = len(accepted) - 1
                frame_duplicates = len(qualifying) - 1
            else:
                false_negative_count += 1
                frame_result["false_negative_count"] = 1
                frame_false_positives = len(accepted)
                frame_duplicates = 0

            false_positive_count += frame_false_positives
            duplicate_false_positive_count += frame_duplicates
            frame_result["false_positive_count"] = frame_false_positives
            frame_result[
                "duplicate_false_positive_count"
            ] = frame_duplicates
        elif (
            annotation.annotation_status == "labeled"
            and annotation.visibility == "not_visible"
            and annotation.game_ball_identity_certainty
            in {"certain", "probable"}
        ):
            not_visible_frame_count += 1
            frame_result["scoring_status"] = "not_visible_negative"
            frame_false_alarms = len(accepted)
            false_positive_count += frame_false_alarms
            non_visible_false_alarm_count += frame_false_alarms
            frame_result["false_positive_count"] = frame_false_alarms
            frame_result[
                "non_visible_false_alarm_count"
            ] = frame_false_alarms

            if frame_false_alarms:
                non_visible_false_alarm_frame_count += 1
        else:
            unscored_frame_count += 1
            frame_result["scoring_status"] = "unscored"
            frame_unscored_predictions = len(accepted)
            unscored_prediction_count += frame_unscored_predictions
            frame_result[
                "unscored_prediction_count"
            ] = frame_unscored_predictions

        frame_results.append(frame_result)

    precision = _safe_ratio(
        true_positive_count,
        true_positive_count + false_positive_count,
    )
    recall = _safe_ratio(
        true_positive_count,
        true_positive_count + false_negative_count,
    )
    annotation_content_sha256 = _canonical_sha256(annotation_set.to_dict())
    detection_run_content_sha256 = _canonical_sha256(
        detection_run.to_dict()
    )
    model_run_signature = _canonical_sha256(
        detection_run.model_provenance.to_dict()
    )

    return {
        "evaluation_schema_version": EVALUATION_SCHEMA_VERSION,
        "annotation_set_id": annotation_set.annotation_set_id,
        "annotation_content_sha256": annotation_content_sha256,
        "detection_run_id": detection_run.detection_run_id,
        "detection_run_content_sha256": detection_run_content_sha256,
        "model_run_signature": model_run_signature,
        "model_provenance": detection_run.model_provenance.to_dict(),
        "possession_id": annotation_set.possession_id,
        "source_video_path": annotation_set.source_video.path.as_posix(),
        "source_video_sha256": annotation_set.source_video.sha256,
        "window_start_frame_index": annotation_set.window.start_frame_index,
        "window_end_frame_index": annotation_set.window.end_frame_index,
        "selection_purpose": annotation_set.window.selection_purpose,
        "confidence_threshold": threshold,
        "localization_radius_px": radius,
        "eligible_frame_count": eligible_frame_count,
        "not_visible_frame_count": not_visible_frame_count,
        "unscored_frame_count": unscored_frame_count,
        "input_detection_count": input_detection_count,
        "below_threshold_detection_count": below_threshold_detection_count,
        "true_positive_count": true_positive_count,
        "false_positive_count": false_positive_count,
        "false_negative_count": false_negative_count,
        "duplicate_false_positive_count": duplicate_false_positive_count,
        "non_visible_false_alarm_count": non_visible_false_alarm_count,
        "non_visible_false_alarm_frame_count": (
            non_visible_false_alarm_frame_count
        ),
        "non_visible_false_alarm_rate": _safe_ratio(
            non_visible_false_alarm_frame_count,
            not_visible_frame_count,
        ),
        "non_visible_false_alarms_per_100_frames": (
            None
            if not_visible_frame_count == 0
            else 100.0
            * non_visible_false_alarm_count
            / not_visible_frame_count
        ),
        "unscored_prediction_count": unscored_prediction_count,
        "precision": precision,
        "recall": recall,
        "matched_center_error_px": _error_summary(matched_center_errors),
        "matched_effective_center_error_px": _error_summary(
            matched_effective_center_errors
        ),
        "frame_results": frame_results,
    }


def aggregate_evaluation_reports(
    reports: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Aggregate comparable, non-overlapping reports by possession."""

    if isinstance(reports, (str, bytes)) or not isinstance(reports, Sequence):
        raise DetectionEvaluationError("reports must be a sequence")

    if not reports:
        return {
            "report_count": 0,
            "possession_count": 0,
            "model_run_signature": None,
            "selection_purpose": None,
            "confidence_threshold": None,
            "localization_radius_px": None,
            "true_positive_count": 0,
            "false_positive_count": 0,
            "false_negative_count": 0,
            "duplicate_false_positive_count": 0,
            "non_visible_false_alarm_count": 0,
            "micro_precision": None,
            "micro_recall": None,
            "macro_precision": None,
            "macro_recall": None,
            "macro_precision_possession_count": 0,
            "macro_recall_possession_count": 0,
            "per_possession": {},
        }

    seen_annotation_sets = set()
    seen_annotation_contents = set()
    seen_detection_runs = set()
    seen_detection_run_contents = set()
    source_hash_by_possession: dict[str, str] = {}
    possession_by_source_hash: dict[str, str] = {}
    windows_by_source_hash: dict[str, list[tuple[int, int, str]]] = defaultdict(
        list
    )
    first_threshold = None
    first_radius = None
    first_model_signature = None
    first_selection_purpose = None
    per_possession_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "report_count": 0,
            "true_positive_count": 0,
            "false_positive_count": 0,
            "false_negative_count": 0,
            "duplicate_false_positive_count": 0,
            "non_visible_false_alarm_count": 0,
        }
    )

    for report_index, report_value in enumerate(reports):
        report = _require_mapping(
            report_value,
            f"reports[{report_index}]",
        )
        validated = _validate_evaluation_report(report, report_index)
        annotation_set_id = validated["annotation_set_id"]
        annotation_content_sha256 = validated[
            "annotation_content_sha256"
        ]
        detection_run_id = validated["detection_run_id"]
        detection_run_content_sha256 = validated[
            "detection_run_content_sha256"
        ]
        possession_id = validated["possession_id"]
        model_run_signature = validated["model_run_signature"]
        source_video_sha256 = validated["source_video_sha256"]
        selection_purpose = validated["selection_purpose"]
        window_start = validated["window_start_frame_index"]
        window_end = validated["window_end_frame_index"]

        if annotation_set_id in seen_annotation_sets:
            raise DetectionEvaluationError(
                "Duplicate annotation_set_id in aggregate reports: "
                f"{annotation_set_id!r}"
            )

        if detection_run_id in seen_detection_runs:
            raise DetectionEvaluationError(
                "Duplicate detection_run_id in aggregate reports: "
                f"{detection_run_id!r}"
            )

        if annotation_content_sha256 in seen_annotation_contents:
            raise DetectionEvaluationError(
                "Duplicate annotation_content_sha256 in aggregate reports: "
                f"{annotation_content_sha256!r}"
            )

        if detection_run_content_sha256 in seen_detection_run_contents:
            raise DetectionEvaluationError(
                "Duplicate detection_run_content_sha256 in aggregate "
                f"reports: {detection_run_content_sha256!r}"
            )

        seen_annotation_sets.add(annotation_set_id)
        seen_annotation_contents.add(annotation_content_sha256)
        seen_detection_runs.add(detection_run_id)
        seen_detection_run_contents.add(detection_run_content_sha256)
        known_source_hash = source_hash_by_possession.get(possession_id)

        if known_source_hash not in {None, source_video_sha256}:
            raise DetectionEvaluationError(
                "Reports for one possession must share source_video_sha256: "
                f"{possession_id!r}"
            )

        known_possession = possession_by_source_hash.get(source_video_sha256)

        if known_possession not in {None, possession_id}:
            raise DetectionEvaluationError(
                "One source_video_sha256 cannot represent multiple "
                "possessions"
            )

        source_hash_by_possession[possession_id] = source_video_sha256
        possession_by_source_hash[source_video_sha256] = possession_id
        windows_by_source_hash[source_video_sha256].append(
            (window_start, window_end, annotation_set_id)
        )
        threshold = validated["confidence_threshold"]
        radius = validated["localization_radius_px"]

        if report_index == 0:
            first_threshold = threshold
            first_radius = radius
            first_model_signature = model_run_signature
            first_selection_purpose = selection_purpose
        elif (
            threshold != first_threshold
            or radius != first_radius
            or model_run_signature != first_model_signature
            or selection_purpose != first_selection_purpose
        ):
            raise DetectionEvaluationError(
                "All reports must use the same threshold, radius, model "
                "configuration, and selection purpose"
            )

        counts = per_possession_counts[possession_id]
        counts["report_count"] += 1

        for field, value in validated["counts"].items():
            counts[field] += value

    for source_hash, windows in windows_by_source_hash.items():
        ordered_windows = sorted(windows)

        for previous, current in zip(ordered_windows, ordered_windows[1:]):
            if current[0] <= previous[1]:
                raise DetectionEvaluationError(
                    "Aggregate reports contain overlapping source windows: "
                    f"{source_hash} {previous[2]!r} and {current[2]!r}"
                )

    per_possession = {}

    for possession_id in sorted(per_possession_counts):
        counts: dict[str, Any] = dict(per_possession_counts[possession_id])
        counts["precision"] = _safe_ratio(
            counts["true_positive_count"],
            counts["true_positive_count"]
            + counts["false_positive_count"],
        )
        counts["recall"] = _safe_ratio(
            counts["true_positive_count"],
            counts["true_positive_count"]
            + counts["false_negative_count"],
        )
        counts["source_video_sha256"] = source_hash_by_possession[
            possession_id
        ]
        per_possession[possession_id] = counts

    total_true_positives = sum(
        counts["true_positive_count"] for counts in per_possession.values()
    )
    total_false_positives = sum(
        counts["false_positive_count"] for counts in per_possession.values()
    )
    total_false_negatives = sum(
        counts["false_negative_count"] for counts in per_possession.values()
    )
    precision_values = [
        counts["precision"]
        for counts in per_possession.values()
        if counts["precision"] is not None
    ]
    recall_values = [
        counts["recall"]
        for counts in per_possession.values()
        if counts["recall"] is not None
    ]

    return {
        "report_count": len(reports),
        "possession_count": len(per_possession),
        "model_run_signature": first_model_signature,
        "selection_purpose": first_selection_purpose,
        "confidence_threshold": first_threshold,
        "localization_radius_px": first_radius,
        "true_positive_count": total_true_positives,
        "false_positive_count": total_false_positives,
        "false_negative_count": total_false_negatives,
        "duplicate_false_positive_count": sum(
            counts["duplicate_false_positive_count"]
            for counts in per_possession.values()
        ),
        "non_visible_false_alarm_count": sum(
            counts["non_visible_false_alarm_count"]
            for counts in per_possession.values()
        ),
        "micro_precision": _safe_ratio(
            total_true_positives,
            total_true_positives + total_false_positives,
        ),
        "micro_recall": _safe_ratio(
            total_true_positives,
            total_true_positives + total_false_negatives,
        ),
        "macro_precision": (
            None
            if not precision_values
            else statistics.fmean(precision_values)
        ),
        "macro_recall": (
            None if not recall_values else statistics.fmean(recall_values)
        ),
        "macro_precision_possession_count": len(precision_values),
        "macro_recall_possession_count": len(recall_values),
        "per_possession": per_possession,
    }
