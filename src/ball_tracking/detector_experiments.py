"""Strict precommitted contract for image-only ball-detector experiments.

The manifest deliberately contains only source/window bindings, model settings,
and a scoring plan.  Annotation paths and frame-level labels are forbidden so a
future inference runner can consume the contract without gaining access to
ground truth.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from .annotations import AnnotationValidationError, SourceVideo
from .detections import (
    DetectionRunValidationError,
    ModelProvenance,
)
from .rfdetr_adapter import (
    DEVICE,
    INPUT_HEIGHT_PX,
    INPUT_WIDTH_PX,
    MIN_EXPORT_CONFIDENCE_FLOOR,
    MODEL_LOGIT_SLOT_COUNT,
    MODEL_NAME,
    MODEL_QUERY_COUNT,
    NUM_SELECT,
    PACKAGE_NAME,
    PACKAGE_VERSION,
    POSTPROCESSING_DESCRIPTION,
    PRECISION,
    PREDICT_THRESHOLD,
    RESIZE_MODE,
    TARGET_CLASS_ID,
    TARGET_CLASS_NAME,
    TILING_ENABLED,
    WEIGHTS_IDENTIFIER,
    WEIGHTS_SHA256,
)


SCHEMA_VERSION = "ball_detector_experiment/v0.1"
EXPERIMENT_PURPOSE = "image_only_ball_detector_baseline"
PROTOCOL_REFERENCE = "docs/ball_tracking_annotation_protocol.md"
WINDOW_LENGTH_FRAMES = 25
MINIMUM_INTERVENING_FRAMES = 25

PROTOCOL_PURPOSE = "protocol_adjudication"
EVALUATION_PURPOSES = (
    "representative_evaluation",
    "challenge_evaluation",
    "test_holdout",
)
ALL_SELECTION_PURPOSES = frozenset((PROTOCOL_PURPOSE, *EVALUATION_PURPOSES))

READY_FOR_INFERENCE = "ready_for_inference"
PREDICTION_EMBARGO = "annotation_pending_prediction_embargo"
EXECUTION_STATUSES = frozenset((READY_FOR_INFERENCE, PREDICTION_EMBARGO))

IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
RUNTIME_DEVICE_PATTERN = re.compile(r"^cuda(?::(?:0|[1-9][0-9]*))?$")

KNOWN_PROTOCOL_PILOT_BINDINGS = (
    (
        "possession_001_frames_0375_0399_protocol_adjudication_v0_1",
        "possession_001",
        "5c42dad097a27873852d1555a71de36b890eb7bf287cf53ee1cdc693c31fcae6",
        375,
        399,
    ),
    (
        "possession_002_frames_0318_0342_protocol_adjudication_v0_1",
        "possession_002",
        "e76e9805c390054d7fda9ca4413612d1f22cdb2f64bc58526a193bd8fdecb224",
        318,
        342,
    ),
    (
        "possession_003_frames_0416_0440_protocol_adjudication_v0_1",
        "possession_003",
        "6b0088df4434ebcd9de84997f871f26698544ebdd237f46d1f4a39937cf40531",
        416,
        440,
    ),
)

KNOWN_PRIOR_PREDICTION_EXCLUSION_BINDING = (
    "possession_001",
    "5c42dad097a27873852d1555a71de36b890eb7bf287cf53ee1cdc693c31fcae6",
    150,
    125,
    199,
    "historical_exploratory_prediction_viewed_before_precommit",
)

EXPECTED_LEAKAGE_CONTROLS: Mapping[str, Any] = {
    "input_modality": "single_rgb_frame",
    "temporal_context_frames": 0,
    "annotation_content_access": False,
    "annotation_paths_present": False,
    "player_track_access": False,
    "court_geometry_access": False,
    "candidate_postselection": "none",
    "holdout_prediction_review_before_operating_point_freeze": False,
}

EXPECTED_DETECTOR_SETTINGS: Mapping[str, Any] = {
    "adapter_id": "rfdetr_medium_coco_v0_1",
    "model_name": MODEL_NAME,
    "package_name": PACKAGE_NAME,
    "package_version": PACKAGE_VERSION,
    "weights_identifier": WEIGHTS_IDENTIFIER,
    "weights_sha256": WEIGHTS_SHA256,
    "device_type": DEVICE,
    "precision": PRECISION,
    "compile_enabled": False,
    "batch_size": 1,
    "input_width_px": INPUT_WIDTH_PX,
    "input_height_px": INPUT_HEIGHT_PX,
    "resize_mode": RESIZE_MODE,
    "tiling_enabled": TILING_ENABLED,
    "model_query_count": MODEL_QUERY_COUNT,
    "model_logit_slot_count": MODEL_LOGIT_SLOT_COUNT,
    "num_select": NUM_SELECT,
    "model_candidate_policy": (
        "all_query_class_pairs_before_target_class_filter"
    ),
    "predict_threshold": PREDICT_THRESHOLD,
    "predict_threshold_policy": "zero_then_adapter_inclusive_export_floor",
    "target_class_id": TARGET_CLASS_ID,
    "target_class_name": TARGET_CLASS_NAME,
    "export_confidence_floor": MIN_EXPORT_CONFIDENCE_FLOOR,
    "candidate_ordering": (
        "confidence_desc_then_bbox_xyxy_lexicographic_then_raw_index"
    ),
    "postprocessing_description": POSTPROCESSING_DESCRIPTION,
    "code_commit_policy": "require_clean_git_head",
}

TOP_LEVEL_FIELDS = frozenset(
    {
        "schema_version",
        "experiment_id",
        "experiment_purpose",
        "protocol_reference",
        "precommit",
        "window_selection",
        "leakage_controls",
        "detector",
        "scoring_grid",
        "windows",
    }
)
PRECOMMIT_FIELDS = frozenset(
    {
        "recorded_at_utc",
        "decision_owner",
        "window_selection_rule",
        "detector_selection_rule",
        "selected_window_predictions_viewed_before_precommit",
        "quality_gate_defined",
    }
)
WINDOW_SELECTION_FIELDS = frozenset(
    {
        "window_length_frames",
        "required_evaluation_purposes",
        "same_source_overlap_policy",
        "minimum_intervening_frames",
        "pilot_exclusions",
        "prior_prediction_exclusions",
    }
)
PILOT_EXCLUSION_FIELDS = frozenset(
    {
        "annotation_set_id",
        "possession_id",
        "source_video_sha256",
        "start_frame_index",
        "end_frame_index",
    }
)
PRIOR_PREDICTION_EXCLUSION_FIELDS = frozenset(
    {
        "possession_id",
        "source_video_sha256",
        "known_prediction_frame_index",
        "excluded_start_frame_index",
        "excluded_end_frame_index",
        "reason_code",
    }
)
LEAKAGE_CONTROL_FIELDS = frozenset(EXPECTED_LEAKAGE_CONTROLS)
DETECTOR_FIELDS = frozenset(EXPECTED_DETECTOR_SETTINGS)
SCORING_GRID_FIELDS = frozenset(
    {
        "confidence_thresholds",
        "localization_radii_px",
        "calibration_selection_purposes",
        "holdout_selection_purpose",
        "holdout_release_rule",
        "quality_gate",
    }
)
WINDOW_FIELDS = frozenset(
    {
        "window_id",
        "annotation_set_id",
        "detection_run_id",
        "possession_id",
        "source_video",
        "start_frame_index",
        "end_frame_index",
        "selection_purpose",
        "execution_status",
        "selection_rationale",
        "output_path",
    }
)

FORBIDDEN_MANIFEST_KEYS = frozenset(
    {
        "annotation_path",
        "annotations_path",
        "annotation_file",
        "annotation_file_path",
        "ground_truth",
        "labels",
        "ball_center",
        "center_xy_px",
        "geometry",
        "difficulty_tags",
        "visibility",
    }
)

OUTPUT_PATH_PREFIX = PurePosixPath(
    "data/outputs/ball_tracking/detections"
).parts


class DetectorExperimentValidationError(ValueError):
    """Raised when a detector-experiment manifest violates schema v0.1."""


def _reject_duplicate_object_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise DetectorExperimentValidationError(
                f"Duplicate JSON object key: {key!r}"
            )
        result[key] = value

    return result


def _reject_forbidden_keys(value: Any, label: str = "manifest") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in FORBIDDEN_MANIFEST_KEYS:
                raise DetectorExperimentValidationError(
                    f"{label} contains forbidden inference field {key!r}"
                )
            _reject_forbidden_keys(child, f"{label}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_keys(child, f"{label}[{index}]")


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DetectorExperimentValidationError(f"{label} must be a JSON object")
    return value


def _require_exact_fields(
    value: Mapping[str, Any],
    expected: frozenset[str],
    label: str,
) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)

    if missing:
        raise DetectorExperimentValidationError(
            f"{label} is missing fields: {missing}"
        )
    if unknown:
        raise DetectorExperimentValidationError(
            f"{label} has unknown fields: {unknown}"
        )


def _require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DetectorExperimentValidationError(
            f"{label} must be a non-empty string"
        )
    if value != value.strip():
        raise DetectorExperimentValidationError(
            f"{label} must not contain surrounding whitespace"
        )
    return value


def _require_identifier(value: Any, label: str) -> str:
    identifier = _require_nonempty_string(value, label)
    if not IDENTIFIER_PATTERN.fullmatch(identifier):
        raise DetectorExperimentValidationError(
            f"{label} must match {IDENTIFIER_PATTERN.pattern!r}"
        )
    return identifier


def _require_integer(value: Any, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DetectorExperimentValidationError(f"{label} must be an integer")
    if value < minimum:
        raise DetectorExperimentValidationError(f"{label} must be >= {minimum}")
    return value


def _require_finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DetectorExperimentValidationError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise DetectorExperimentValidationError(f"{label} must be finite")
    return result


def _require_boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise DetectorExperimentValidationError(f"{label} must be a boolean")
    return value


def _require_utc_timestamp(value: Any, label: str) -> str:
    timestamp = _require_nonempty_string(value, label)
    normalized = timestamp[:-1] + "+00:00" if timestamp.endswith("Z") else timestamp
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise DetectorExperimentValidationError(
            f"{label} must be an ISO-8601 timestamp"
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise DetectorExperimentValidationError(
            f"{label} must have an explicit UTC offset"
        )
    return timestamp


def _require_sha256(value: Any, label: str) -> str:
    digest = _require_nonempty_string(value, label)
    if not SHA256_PATTERN.fullmatch(digest):
        raise DetectorExperimentValidationError(
            f"{label} must contain exactly 64 lowercase hexadecimal characters"
        )
    return digest


def _require_output_path(value: Any, label: str) -> PurePosixPath:
    raw = _require_nonempty_string(value, label)
    if "\\" in raw:
        raise DetectorExperimentValidationError(
            f"{label} must use portable forward slashes"
        )
    path = PurePosixPath(raw)
    if (
        path.is_absolute()
        or not path.parts
        or "." in path.parts
        or ".." in path.parts
        or path.as_posix() != raw
    ):
        raise DetectorExperimentValidationError(
            f"{label} must be a normalized repository-relative path"
        )
    windows_reserved_names = {
        "aux",
        "con",
        "nul",
        "prn",
        *(f"com{index}" for index in range(1, 10)),
        *(f"lpt{index}" for index in range(1, 10)),
    }
    for component in path.parts:
        device_basename = component.split(".", 1)[0].rstrip(" .").casefold()
        if (
            ":" in component
            or component.endswith((".", " "))
            or device_basename in windows_reserved_names
        ):
            raise DetectorExperimentValidationError(
                f"{label} contains a Windows-unsafe path component "
                f"{component!r}"
            )
    if path.parts[: len(OUTPUT_PATH_PREFIX)] != OUTPUT_PATH_PREFIX:
        raise DetectorExperimentValidationError(
            f"{label} must be beneath "
            "data/outputs/ball_tracking/detections"
        )
    if path.suffix != ".json":
        raise DetectorExperimentValidationError(
            f"{label} must name a .json file"
        )
    return path


def _require_string_sequence(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise DetectorExperimentValidationError(f"{label} must be a JSON array")
    return tuple(
        _require_nonempty_string(item, f"{label}[{index}]")
        for index, item in enumerate(value)
    )


def _require_strict_numeric_grid(
    value: Any,
    label: str,
    *,
    minimum: float,
    maximum: float | None,
) -> tuple[float, ...]:
    if not isinstance(value, list) or not value:
        raise DetectorExperimentValidationError(
            f"{label} must be a non-empty JSON array"
        )
    result = tuple(
        _require_finite_number(item, f"{label}[{index}]")
        for index, item in enumerate(value)
    )
    if any(item < minimum for item in result):
        raise DetectorExperimentValidationError(
            f"{label} values must be >= {minimum}"
        )
    if maximum is not None and any(item > maximum for item in result):
        raise DetectorExperimentValidationError(
            f"{label} values must be <= {maximum}"
        )
    if any(right <= left for left, right in zip(result, result[1:])):
        raise DetectorExperimentValidationError(
            f"{label} must be strictly increasing and duplicate-free"
        )
    return result


@dataclass(frozen=True)
class ExperimentPrecommit:
    recorded_at_utc: str
    decision_owner: str
    window_selection_rule: str
    detector_selection_rule: str
    selected_window_predictions_viewed_before_precommit: bool
    quality_gate_defined: bool

    @classmethod
    def from_mapping(cls, value: Any) -> "ExperimentPrecommit":
        precommit = _require_mapping(value, "precommit")
        _require_exact_fields(precommit, PRECOMMIT_FIELDS, "precommit")
        predictions_viewed = _require_boolean(
            precommit["selected_window_predictions_viewed_before_precommit"],
            "precommit.selected_window_predictions_viewed_before_precommit",
        )
        quality_gate_defined = _require_boolean(
            precommit["quality_gate_defined"],
            "precommit.quality_gate_defined",
        )
        if predictions_viewed:
            raise DetectorExperimentValidationError(
                "precommit.selected_window_predictions_viewed_before_precommit "
                "must be false"
            )
        if quality_gate_defined:
            raise DetectorExperimentValidationError(
                "precommit.quality_gate_defined must be false for the first baseline"
            )
        return cls(
            recorded_at_utc=_require_utc_timestamp(
                precommit["recorded_at_utc"],
                "precommit.recorded_at_utc",
            ),
            decision_owner=_require_nonempty_string(
                precommit["decision_owner"],
                "precommit.decision_owner",
            ),
            window_selection_rule=_require_nonempty_string(
                precommit["window_selection_rule"],
                "precommit.window_selection_rule",
            ),
            detector_selection_rule=_require_nonempty_string(
                precommit["detector_selection_rule"],
                "precommit.detector_selection_rule",
            ),
            selected_window_predictions_viewed_before_precommit=(
                predictions_viewed
            ),
            quality_gate_defined=quality_gate_defined,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "recorded_at_utc": self.recorded_at_utc,
            "decision_owner": self.decision_owner,
            "window_selection_rule": self.window_selection_rule,
            "detector_selection_rule": self.detector_selection_rule,
            "selected_window_predictions_viewed_before_precommit": (
                self.selected_window_predictions_viewed_before_precommit
            ),
            "quality_gate_defined": self.quality_gate_defined,
        }


@dataclass(frozen=True)
class PilotExclusion:
    annotation_set_id: str
    possession_id: str
    source_video_sha256: str
    start_frame_index: int
    end_frame_index: int

    @classmethod
    def from_mapping(cls, value: Any, index: int) -> "PilotExclusion":
        label = f"window_selection.pilot_exclusions[{index}]"
        exclusion = _require_mapping(value, label)
        _require_exact_fields(exclusion, PILOT_EXCLUSION_FIELDS, label)
        start = _require_integer(
            exclusion["start_frame_index"],
            f"{label}.start_frame_index",
        )
        end = _require_integer(
            exclusion["end_frame_index"],
            f"{label}.end_frame_index",
        )
        if end < start:
            raise DetectorExperimentValidationError(
                f"{label}.end_frame_index must be >= start_frame_index"
            )
        if end - start + 1 != WINDOW_LENGTH_FRAMES:
            raise DetectorExperimentValidationError(
                f"{label} must contain exactly {WINDOW_LENGTH_FRAMES} frames"
            )
        return cls(
            annotation_set_id=_require_identifier(
                exclusion["annotation_set_id"],
                f"{label}.annotation_set_id",
            ),
            possession_id=_require_identifier(
                exclusion["possession_id"],
                f"{label}.possession_id",
            ),
            source_video_sha256=_require_sha256(
                exclusion["source_video_sha256"],
                f"{label}.source_video_sha256",
            ),
            start_frame_index=start,
            end_frame_index=end,
        )

    @property
    def binding_key(self) -> tuple[str, str, str, int, int]:
        return (
            self.annotation_set_id,
            self.possession_id,
            self.source_video_sha256,
            self.start_frame_index,
            self.end_frame_index,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "annotation_set_id": self.annotation_set_id,
            "possession_id": self.possession_id,
            "source_video_sha256": self.source_video_sha256,
            "start_frame_index": self.start_frame_index,
            "end_frame_index": self.end_frame_index,
        }


@dataclass(frozen=True)
class PriorPredictionExclusion:
    possession_id: str
    source_video_sha256: str
    known_prediction_frame_index: int
    excluded_start_frame_index: int
    excluded_end_frame_index: int
    reason_code: str

    @classmethod
    def from_mapping(cls, value: Any, index: int) -> "PriorPredictionExclusion":
        label = f"window_selection.prior_prediction_exclusions[{index}]"
        exclusion = _require_mapping(value, label)
        _require_exact_fields(
            exclusion,
            PRIOR_PREDICTION_EXCLUSION_FIELDS,
            label,
        )
        known_frame = _require_integer(
            exclusion["known_prediction_frame_index"],
            f"{label}.known_prediction_frame_index",
        )
        start = _require_integer(
            exclusion["excluded_start_frame_index"],
            f"{label}.excluded_start_frame_index",
        )
        end = _require_integer(
            exclusion["excluded_end_frame_index"],
            f"{label}.excluded_end_frame_index",
        )
        if end < start:
            raise DetectorExperimentValidationError(
                f"{label}.excluded_end_frame_index must be >= "
                "excluded_start_frame_index"
            )
        if not start <= known_frame <= end:
            raise DetectorExperimentValidationError(
                f"{label}.known_prediction_frame_index must fall within the "
                "excluded frame range"
            )
        return cls(
            possession_id=_require_identifier(
                exclusion["possession_id"],
                f"{label}.possession_id",
            ),
            source_video_sha256=_require_sha256(
                exclusion["source_video_sha256"],
                f"{label}.source_video_sha256",
            ),
            known_prediction_frame_index=known_frame,
            excluded_start_frame_index=start,
            excluded_end_frame_index=end,
            reason_code=_require_identifier(
                exclusion["reason_code"],
                f"{label}.reason_code",
            ),
        )

    @property
    def binding_key(self) -> tuple[str, str, int, int, int, str]:
        return (
            self.possession_id,
            self.source_video_sha256,
            self.known_prediction_frame_index,
            self.excluded_start_frame_index,
            self.excluded_end_frame_index,
            self.reason_code,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "possession_id": self.possession_id,
            "source_video_sha256": self.source_video_sha256,
            "known_prediction_frame_index": self.known_prediction_frame_index,
            "excluded_start_frame_index": self.excluded_start_frame_index,
            "excluded_end_frame_index": self.excluded_end_frame_index,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True)
class WindowSelectionPlan:
    window_length_frames: int
    required_evaluation_purposes: tuple[str, ...]
    same_source_overlap_policy: str
    minimum_intervening_frames: int
    pilot_exclusions: tuple[PilotExclusion, ...]
    prior_prediction_exclusions: tuple[PriorPredictionExclusion, ...]

    @classmethod
    def from_mapping(cls, value: Any) -> "WindowSelectionPlan":
        plan = _require_mapping(value, "window_selection")
        _require_exact_fields(plan, WINDOW_SELECTION_FIELDS, "window_selection")
        window_length = _require_integer(
            plan["window_length_frames"],
            "window_selection.window_length_frames",
            1,
        )
        if window_length != WINDOW_LENGTH_FRAMES:
            raise DetectorExperimentValidationError(
                f"window_selection.window_length_frames must be {WINDOW_LENGTH_FRAMES}"
            )
        purposes = _require_string_sequence(
            plan["required_evaluation_purposes"],
            "window_selection.required_evaluation_purposes",
        )
        if purposes != EVALUATION_PURPOSES:
            raise DetectorExperimentValidationError(
                "window_selection.required_evaluation_purposes must exactly equal "
                f"{list(EVALUATION_PURPOSES)}"
            )
        overlap_policy = _require_nonempty_string(
            plan["same_source_overlap_policy"],
            "window_selection.same_source_overlap_policy",
        )
        if overlap_policy != "forbid":
            raise DetectorExperimentValidationError(
                "window_selection.same_source_overlap_policy must be 'forbid'"
            )
        minimum_intervening = _require_integer(
            plan["minimum_intervening_frames"],
            "window_selection.minimum_intervening_frames",
        )
        if minimum_intervening != MINIMUM_INTERVENING_FRAMES:
            raise DetectorExperimentValidationError(
                "window_selection.minimum_intervening_frames must be "
                f"{MINIMUM_INTERVENING_FRAMES}"
            )
        raw_exclusions = plan["pilot_exclusions"]
        if not isinstance(raw_exclusions, list) or len(raw_exclusions) != 3:
            raise DetectorExperimentValidationError(
                "window_selection.pilot_exclusions must contain exactly 3 entries"
            )
        exclusions = tuple(
            PilotExclusion.from_mapping(item, index)
            for index, item in enumerate(raw_exclusions)
        )
        if len({item.binding_key for item in exclusions}) != len(exclusions):
            raise DetectorExperimentValidationError(
                "window_selection.pilot_exclusions must be unique"
            )
        if {item.binding_key for item in exclusions} != set(
            KNOWN_PROTOCOL_PILOT_BINDINGS
        ):
            raise DetectorExperimentValidationError(
                "window_selection.pilot_exclusions must exactly match the "
                "3 known reviewed protocol pilot bindings"
            )
        raw_prior_exclusions = plan["prior_prediction_exclusions"]
        if (
            not isinstance(raw_prior_exclusions, list)
            or len(raw_prior_exclusions) != 1
        ):
            raise DetectorExperimentValidationError(
                "window_selection.prior_prediction_exclusions must contain "
                "exactly the 1 known historical entry"
            )
        prior_exclusions = tuple(
            PriorPredictionExclusion.from_mapping(item, index)
            for index, item in enumerate(raw_prior_exclusions)
        )
        if prior_exclusions[0].binding_key != (
            KNOWN_PRIOR_PREDICTION_EXCLUSION_BINDING
        ):
            raise DetectorExperimentValidationError(
                "window_selection.prior_prediction_exclusions must exactly "
                "match the known P001 historical prediction guard"
            )
        return cls(
            window_length_frames=window_length,
            required_evaluation_purposes=purposes,
            same_source_overlap_policy=overlap_policy,
            minimum_intervening_frames=minimum_intervening,
            pilot_exclusions=exclusions,
            prior_prediction_exclusions=prior_exclusions,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_length_frames": self.window_length_frames,
            "required_evaluation_purposes": list(
                self.required_evaluation_purposes
            ),
            "same_source_overlap_policy": self.same_source_overlap_policy,
            "minimum_intervening_frames": self.minimum_intervening_frames,
            "pilot_exclusions": [item.to_dict() for item in self.pilot_exclusions],
            "prior_prediction_exclusions": [
                item.to_dict() for item in self.prior_prediction_exclusions
            ],
        }


@dataclass(frozen=True)
class LeakageControls:
    input_modality: str
    temporal_context_frames: int
    annotation_content_access: bool
    annotation_paths_present: bool
    player_track_access: bool
    court_geometry_access: bool
    candidate_postselection: str
    holdout_prediction_review_before_operating_point_freeze: bool

    @classmethod
    def from_mapping(cls, value: Any) -> "LeakageControls":
        controls = _require_mapping(value, "leakage_controls")
        _require_exact_fields(
            controls,
            LEAKAGE_CONTROL_FIELDS,
            "leakage_controls",
        )
        normalized = {
            "input_modality": _require_nonempty_string(
                controls["input_modality"],
                "leakage_controls.input_modality",
            ),
            "temporal_context_frames": _require_integer(
                controls["temporal_context_frames"],
                "leakage_controls.temporal_context_frames",
            ),
            "annotation_content_access": _require_boolean(
                controls["annotation_content_access"],
                "leakage_controls.annotation_content_access",
            ),
            "annotation_paths_present": _require_boolean(
                controls["annotation_paths_present"],
                "leakage_controls.annotation_paths_present",
            ),
            "player_track_access": _require_boolean(
                controls["player_track_access"],
                "leakage_controls.player_track_access",
            ),
            "court_geometry_access": _require_boolean(
                controls["court_geometry_access"],
                "leakage_controls.court_geometry_access",
            ),
            "candidate_postselection": _require_nonempty_string(
                controls["candidate_postselection"],
                "leakage_controls.candidate_postselection",
            ),
            "holdout_prediction_review_before_operating_point_freeze": (
                _require_boolean(
                    controls[
                        "holdout_prediction_review_before_operating_point_freeze"
                    ],
                    "leakage_controls."
                    "holdout_prediction_review_before_operating_point_freeze",
                )
            ),
        }
        if normalized != dict(EXPECTED_LEAKAGE_CONTROLS):
            raise DetectorExperimentValidationError(
                "leakage_controls must exactly match the fixed image-only, "
                "prediction-embargo contract"
            )
        return cls(**normalized)

    def to_dict(self) -> dict[str, Any]:
        return {
            field: getattr(self, field) for field in EXPECTED_LEAKAGE_CONTROLS
        }


@dataclass(frozen=True)
class DetectorSpecification:
    adapter_id: str
    model_name: str
    package_name: str
    package_version: str
    weights_identifier: str
    weights_sha256: str
    device_type: str
    precision: str
    compile_enabled: bool
    batch_size: int
    input_width_px: int
    input_height_px: int
    resize_mode: str
    tiling_enabled: bool
    model_query_count: int
    model_logit_slot_count: int
    num_select: int
    model_candidate_policy: str
    predict_threshold: float
    predict_threshold_policy: str
    target_class_id: int
    target_class_name: str
    export_confidence_floor: float
    candidate_ordering: str
    postprocessing_description: str
    code_commit_policy: str

    @classmethod
    def from_mapping(cls, value: Any) -> "DetectorSpecification":
        detector = _require_mapping(value, "detector")
        _require_exact_fields(detector, DETECTOR_FIELDS, "detector")
        normalized: dict[str, Any] = {
            "adapter_id": _require_identifier(
                detector["adapter_id"], "detector.adapter_id"
            ),
            "model_name": _require_nonempty_string(
                detector["model_name"], "detector.model_name"
            ),
            "package_name": _require_nonempty_string(
                detector["package_name"], "detector.package_name"
            ),
            "package_version": _require_nonempty_string(
                detector["package_version"], "detector.package_version"
            ),
            "weights_identifier": _require_nonempty_string(
                detector["weights_identifier"], "detector.weights_identifier"
            ),
            "weights_sha256": _require_sha256(
                detector["weights_sha256"], "detector.weights_sha256"
            ),
            "device_type": _require_nonempty_string(
                detector["device_type"], "detector.device_type"
            ),
            "precision": _require_nonempty_string(
                detector["precision"], "detector.precision"
            ),
            "compile_enabled": _require_boolean(
                detector["compile_enabled"], "detector.compile_enabled"
            ),
            "batch_size": _require_integer(
                detector["batch_size"], "detector.batch_size", 1
            ),
            "input_width_px": _require_integer(
                detector["input_width_px"], "detector.input_width_px", 1
            ),
            "input_height_px": _require_integer(
                detector["input_height_px"], "detector.input_height_px", 1
            ),
            "resize_mode": _require_nonempty_string(
                detector["resize_mode"], "detector.resize_mode"
            ),
            "tiling_enabled": _require_boolean(
                detector["tiling_enabled"], "detector.tiling_enabled"
            ),
            "model_query_count": _require_integer(
                detector["model_query_count"],
                "detector.model_query_count",
                1,
            ),
            "model_logit_slot_count": _require_integer(
                detector["model_logit_slot_count"],
                "detector.model_logit_slot_count",
                1,
            ),
            "num_select": _require_integer(
                detector["num_select"], "detector.num_select", 1
            ),
            "model_candidate_policy": _require_nonempty_string(
                detector["model_candidate_policy"],
                "detector.model_candidate_policy",
            ),
            "predict_threshold": _require_finite_number(
                detector["predict_threshold"],
                "detector.predict_threshold",
            ),
            "predict_threshold_policy": _require_nonempty_string(
                detector["predict_threshold_policy"],
                "detector.predict_threshold_policy",
            ),
            "target_class_id": _require_integer(
                detector["target_class_id"], "detector.target_class_id"
            ),
            "target_class_name": _require_nonempty_string(
                detector["target_class_name"], "detector.target_class_name"
            ),
            "export_confidence_floor": _require_finite_number(
                detector["export_confidence_floor"],
                "detector.export_confidence_floor",
            ),
            "candidate_ordering": _require_nonempty_string(
                detector["candidate_ordering"], "detector.candidate_ordering"
            ),
            "postprocessing_description": _require_nonempty_string(
                detector["postprocessing_description"],
                "detector.postprocessing_description",
            ),
            "code_commit_policy": _require_nonempty_string(
                detector["code_commit_policy"], "detector.code_commit_policy"
            ),
        }
        if not 0.0 <= normalized["export_confidence_floor"] <= 1.0:
            raise DetectorExperimentValidationError(
                "detector.export_confidence_floor must be in [0, 1]"
            )
        if normalized != dict(EXPECTED_DETECTOR_SETTINGS):
            mismatches = sorted(
                field
                for field, expected in EXPECTED_DETECTOR_SETTINGS.items()
                if normalized[field] != expected
            )
            raise DetectorExperimentValidationError(
                "detector does not match the frozen RF-DETR Medium baseline; "
                f"mismatched fields: {mismatches}"
            )
        return cls(**normalized)

    def to_dict(self) -> dict[str, Any]:
        return {field: getattr(self, field) for field in EXPECTED_DETECTOR_SETTINGS}


@dataclass(frozen=True)
class ScoringGrid:
    confidence_thresholds: tuple[float, ...]
    localization_radii_px: tuple[float, ...]
    calibration_selection_purposes: tuple[str, ...]
    holdout_selection_purpose: str
    holdout_release_rule: str
    quality_gate: None

    @classmethod
    def from_mapping(
        cls,
        value: Any,
        detector: DetectorSpecification,
    ) -> "ScoringGrid":
        grid = _require_mapping(value, "scoring_grid")
        _require_exact_fields(grid, SCORING_GRID_FIELDS, "scoring_grid")
        thresholds = _require_strict_numeric_grid(
            grid["confidence_thresholds"],
            "scoring_grid.confidence_thresholds",
            minimum=detector.export_confidence_floor,
            maximum=1.0,
        )
        if thresholds[0] != detector.export_confidence_floor:
            raise DetectorExperimentValidationError(
                "scoring_grid.confidence_thresholds must begin at the export floor"
            )
        radii = _require_strict_numeric_grid(
            grid["localization_radii_px"],
            "scoring_grid.localization_radii_px",
            minimum=0.0,
            maximum=None,
        )
        if radii[0] <= 0.0:
            raise DetectorExperimentValidationError(
                "scoring_grid.localization_radii_px values must be positive"
            )
        calibration_purposes = _require_string_sequence(
            grid["calibration_selection_purposes"],
            "scoring_grid.calibration_selection_purposes",
        )
        expected_calibration = EVALUATION_PURPOSES[:2]
        if calibration_purposes != expected_calibration:
            raise DetectorExperimentValidationError(
                "scoring_grid.calibration_selection_purposes must exactly equal "
                f"{list(expected_calibration)}"
            )
        holdout_purpose = _require_nonempty_string(
            grid["holdout_selection_purpose"],
            "scoring_grid.holdout_selection_purpose",
        )
        if holdout_purpose != "test_holdout":
            raise DetectorExperimentValidationError(
                "scoring_grid.holdout_selection_purpose must be 'test_holdout'"
            )
        release_rule = _require_nonempty_string(
            grid["holdout_release_rule"],
            "scoring_grid.holdout_release_rule",
        )
        if release_rule != "after_detector_and_operating_point_are_frozen":
            raise DetectorExperimentValidationError(
                "scoring_grid.holdout_release_rule must freeze detector and "
                "operating point before holdout release"
            )
        if grid["quality_gate"] is not None:
            raise DetectorExperimentValidationError(
                "scoring_grid.quality_gate must be null for the first baseline"
            )
        return cls(
            confidence_thresholds=thresholds,
            localization_radii_px=radii,
            calibration_selection_purposes=calibration_purposes,
            holdout_selection_purpose=holdout_purpose,
            holdout_release_rule=release_rule,
            quality_gate=None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "confidence_thresholds": list(self.confidence_thresholds),
            "localization_radii_px": list(self.localization_radii_px),
            "calibration_selection_purposes": list(
                self.calibration_selection_purposes
            ),
            "holdout_selection_purpose": self.holdout_selection_purpose,
            "holdout_release_rule": self.holdout_release_rule,
            "quality_gate": self.quality_gate,
        }


@dataclass(frozen=True)
class ExperimentWindow:
    window_id: str
    annotation_set_id: str
    detection_run_id: str
    possession_id: str
    source_video: SourceVideo
    start_frame_index: int
    end_frame_index: int
    selection_purpose: str
    execution_status: str
    selection_rationale: str
    output_path: PurePosixPath

    @classmethod
    def from_mapping(cls, value: Any, index: int) -> "ExperimentWindow":
        label = f"windows[{index}]"
        window = _require_mapping(value, label)
        _require_exact_fields(window, WINDOW_FIELDS, label)
        try:
            source_video = SourceVideo.from_mapping(window["source_video"])
        except AnnotationValidationError as error:
            raise DetectorExperimentValidationError(
                f"{label}.source_video is invalid: {error}"
            ) from error
        start = _require_integer(
            window["start_frame_index"], f"{label}.start_frame_index"
        )
        end = _require_integer(
            window["end_frame_index"], f"{label}.end_frame_index"
        )
        if end < start:
            raise DetectorExperimentValidationError(
                f"{label}.end_frame_index must be >= start_frame_index"
            )
        if end >= source_video.frame_count:
            raise DetectorExperimentValidationError(
                f"{label}.end_frame_index must be below source frame_count"
            )
        if end - start + 1 != WINDOW_LENGTH_FRAMES:
            raise DetectorExperimentValidationError(
                f"{label} must contain exactly {WINDOW_LENGTH_FRAMES} frames"
            )
        purpose = _require_nonempty_string(
            window["selection_purpose"], f"{label}.selection_purpose"
        )
        if purpose not in ALL_SELECTION_PURPOSES:
            raise DetectorExperimentValidationError(
                f"{label}.selection_purpose must be one of "
                f"{sorted(ALL_SELECTION_PURPOSES)}"
            )
        status = _require_nonempty_string(
            window["execution_status"], f"{label}.execution_status"
        )
        if status not in EXECUTION_STATUSES:
            raise DetectorExperimentValidationError(
                f"{label}.execution_status must be one of "
                f"{sorted(EXECUTION_STATUSES)}"
            )
        expected_status = (
            READY_FOR_INFERENCE if purpose == PROTOCOL_PURPOSE else PREDICTION_EMBARGO
        )
        if status != expected_status:
            raise DetectorExperimentValidationError(
                f"{label} purpose {purpose!r} requires execution_status "
                f"{expected_status!r}"
            )
        return cls(
            window_id=_require_identifier(
                window["window_id"], f"{label}.window_id"
            ),
            annotation_set_id=_require_identifier(
                window["annotation_set_id"], f"{label}.annotation_set_id"
            ),
            detection_run_id=_require_identifier(
                window["detection_run_id"], f"{label}.detection_run_id"
            ),
            possession_id=_require_identifier(
                window["possession_id"], f"{label}.possession_id"
            ),
            source_video=source_video,
            start_frame_index=start,
            end_frame_index=end,
            selection_purpose=purpose,
            execution_status=status,
            selection_rationale=_require_nonempty_string(
                window["selection_rationale"], f"{label}.selection_rationale"
            ),
            output_path=_require_output_path(
                window["output_path"], f"{label}.output_path"
            ),
        )

    @property
    def frame_count(self) -> int:
        return self.end_frame_index - self.start_frame_index + 1

    @property
    def pilot_binding_key(self) -> tuple[str, str, str, int, int]:
        return (
            self.annotation_set_id,
            self.possession_id,
            self.source_video.sha256,
            self.start_frame_index,
            self.end_frame_index,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "annotation_set_id": self.annotation_set_id,
            "detection_run_id": self.detection_run_id,
            "possession_id": self.possession_id,
            "source_video": self.source_video.to_dict(),
            "start_frame_index": self.start_frame_index,
            "end_frame_index": self.end_frame_index,
            "selection_purpose": self.selection_purpose,
            "execution_status": self.execution_status,
            "selection_rationale": self.selection_rationale,
            "output_path": self.output_path.as_posix(),
        }


@dataclass(frozen=True)
class DetectorExperiment:
    schema_version: str
    experiment_id: str
    experiment_purpose: str
    protocol_reference: str
    precommit: ExperimentPrecommit
    window_selection: WindowSelectionPlan
    leakage_controls: LeakageControls
    detector: DetectorSpecification
    scoring_grid: ScoringGrid
    windows: tuple[ExperimentWindow, ...]

    @classmethod
    def from_mapping(cls, value: Any) -> "DetectorExperiment":
        payload = _require_mapping(value, "detector experiment")
        _reject_forbidden_keys(payload)
        _require_exact_fields(payload, TOP_LEVEL_FIELDS, "detector experiment")
        if payload["schema_version"] != SCHEMA_VERSION:
            raise DetectorExperimentValidationError(
                f"schema_version must be {SCHEMA_VERSION!r}"
            )
        if payload["experiment_purpose"] != EXPERIMENT_PURPOSE:
            raise DetectorExperimentValidationError(
                f"experiment_purpose must be {EXPERIMENT_PURPOSE!r}"
            )
        if payload["protocol_reference"] != PROTOCOL_REFERENCE:
            raise DetectorExperimentValidationError(
                f"protocol_reference must be {PROTOCOL_REFERENCE!r}"
            )
        precommit = ExperimentPrecommit.from_mapping(payload["precommit"])
        selection = WindowSelectionPlan.from_mapping(payload["window_selection"])
        leakage = LeakageControls.from_mapping(payload["leakage_controls"])
        detector = DetectorSpecification.from_mapping(payload["detector"])
        scoring_grid = ScoringGrid.from_mapping(payload["scoring_grid"], detector)
        raw_windows = payload["windows"]
        if not isinstance(raw_windows, list):
            raise DetectorExperimentValidationError("windows must be a JSON array")
        windows = tuple(
            ExperimentWindow.from_mapping(item, index)
            for index, item in enumerate(raw_windows)
        )
        cls._validate_windows(windows, selection)
        return cls(
            schema_version=SCHEMA_VERSION,
            experiment_id=_require_identifier(
                payload["experiment_id"], "experiment_id"
            ),
            experiment_purpose=EXPERIMENT_PURPOSE,
            protocol_reference=PROTOCOL_REFERENCE,
            precommit=precommit,
            window_selection=selection,
            leakage_controls=leakage,
            detector=detector,
            scoring_grid=scoring_grid,
            windows=windows,
        )

    @staticmethod
    def _validate_windows(
        windows: tuple[ExperimentWindow, ...],
        selection: WindowSelectionPlan,
    ) -> None:
        if len(windows) != 12:
            raise DetectorExperimentValidationError(
                "windows must contain exactly 12 entries: one protocol pilot, "
                "one representative, one challenge, and one holdout window for "
                "each of 3 possessions"
            )
        unique_fields: Sequence[tuple[str, Sequence[str]]] = (
            ("window_id", [item.window_id for item in windows]),
            ("annotation_set_id", [item.annotation_set_id for item in windows]),
            ("detection_run_id", [item.detection_run_id for item in windows]),
            (
                "output_path",
                [item.output_path.as_posix().casefold() for item in windows],
            ),
        )
        for label, values in unique_fields:
            if len(set(values)) != len(values):
                raise DetectorExperimentValidationError(
                    f"windows must have unique {label} values"
                )

        pilot_windows = tuple(
            item for item in windows if item.selection_purpose == PROTOCOL_PURPOSE
        )
        if len(pilot_windows) != 3:
            raise DetectorExperimentValidationError(
                "windows must contain exactly 3 protocol_adjudication pilots"
            )
        pilot_possessions = {
            item.possession_id for item in pilot_windows
        }
        if len(pilot_possessions) != 3:
            raise DetectorExperimentValidationError(
                "the 3 protocol_adjudication pilots must belong to 3 unique "
                "possessions"
            )
        pilot_keys = {item.pilot_binding_key for item in pilot_windows}
        exclusion_keys = {
            item.binding_key for item in selection.pilot_exclusions
        }
        if pilot_keys != exclusion_keys:
            raise DetectorExperimentValidationError(
                "protocol_adjudication windows must exactly match the 3 "
                "declared pilot exclusions"
            )
        if pilot_keys != set(KNOWN_PROTOCOL_PILOT_BINDINGS):
            raise DetectorExperimentValidationError(
                "protocol_adjudication windows must exactly match the 3 known "
                "reviewed protocol pilot bindings"
            )

        for exclusion in selection.prior_prediction_exclusions:
            for item in windows:
                same_source = (
                    item.possession_id == exclusion.possession_id
                    and item.source_video.sha256 == exclusion.source_video_sha256
                )
                overlaps = (
                    item.start_frame_index <= exclusion.excluded_end_frame_index
                    and exclusion.excluded_start_frame_index
                    <= item.end_frame_index
                )
                if same_source and overlaps:
                    raise DetectorExperimentValidationError(
                        f"window {item.window_id!r} overlaps the known prior-"
                        "prediction exclusion for P001 frames "
                        f"{exclusion.excluded_start_frame_index}-"
                        f"{exclusion.excluded_end_frame_index}"
                    )

        all_possessions = {item.possession_id for item in windows}
        if all_possessions != pilot_possessions:
            raise DetectorExperimentValidationError(
                "all windows must belong to the same 3 possessions as the "
                "protocol pilots"
            )
        required_purposes = {PROTOCOL_PURPOSE, *EVALUATION_PURPOSES}
        for possession_id in sorted(pilot_possessions):
            purposes = [
                item.selection_purpose
                for item in windows
                if item.possession_id == possession_id
            ]
            purpose_counts = {
                purpose: purposes.count(purpose)
                for purpose in required_purposes
            }
            if set(purposes) != required_purposes or any(
                count != 1 for count in purpose_counts.values()
            ):
                raise DetectorExperimentValidationError(
                    f"possession {possession_id!r} must have every required "
                    "purpose exactly once; received counts "
                    f"{dict(sorted(purpose_counts.items()))}"
                )

        possession_sources: dict[str, Mapping[str, Any]] = {}
        source_possessions: dict[str, str] = {}
        by_source: dict[str, list[ExperimentWindow]] = {}
        for item in windows:
            source_dict = item.source_video.to_dict()
            prior_source = possession_sources.setdefault(
                item.possession_id, source_dict
            )
            if prior_source != source_dict:
                raise DetectorExperimentValidationError(
                    f"possession {item.possession_id!r} has inconsistent "
                    "source_video contracts"
                )
            prior_possession = source_possessions.setdefault(
                item.source_video.sha256, item.possession_id
            )
            if prior_possession != item.possession_id:
                raise DetectorExperimentValidationError(
                    "one source_video SHA-256 cannot belong to multiple possessions"
                )
            by_source.setdefault(item.source_video.sha256, []).append(item)

        for source_sha256, source_windows in by_source.items():
            ordered = sorted(
                source_windows,
                key=lambda item: (item.start_frame_index, item.end_frame_index),
            )
            for left, right in zip(ordered, ordered[1:]):
                if right.start_frame_index <= left.end_frame_index:
                    raise DetectorExperimentValidationError(
                        "same-source windows must not overlap: "
                        f"{left.window_id!r} and {right.window_id!r} on "
                        f"{source_sha256}"
                    )
                intervening_frames = (
                    right.start_frame_index - left.end_frame_index - 1
                )
                if intervening_frames < selection.minimum_intervening_frames:
                    raise DetectorExperimentValidationError(
                        "same-source windows must have at least "
                        f"{selection.minimum_intervening_frames} completely "
                        "unselected intervening frames: "
                        f"{left.window_id!r} and {right.window_id!r} on "
                        f"{source_sha256} have {intervening_frames}"
                    )

    @property
    def ready_windows(self) -> tuple[ExperimentWindow, ...]:
        """Return the only windows a label-blind inference runner may consume."""

        return tuple(
            item
            for item in self.windows
            if item.execution_status == READY_FOR_INFERENCE
        )

    def windows_for_inference(self) -> tuple[ExperimentWindow, ...]:
        """Runner-facing alias that excludes prediction-embargoed windows."""

        return self.ready_windows

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "experiment_id": self.experiment_id,
            "experiment_purpose": self.experiment_purpose,
            "protocol_reference": self.protocol_reference,
            "precommit": self.precommit.to_dict(),
            "window_selection": self.window_selection.to_dict(),
            "leakage_controls": self.leakage_controls.to_dict(),
            "detector": self.detector.to_dict(),
            "scoring_grid": self.scoring_grid.to_dict(),
            "windows": [item.to_dict() for item in self.windows],
        }


def build_model_provenance(
    detector: DetectorSpecification,
    *,
    code_commit: str,
    runtime_device: str,
) -> ModelProvenance:
    """Build the persisted provenance after a runner verifies a clean HEAD.

    ``code_commit`` is intentionally supplied at execution time to avoid a
    self-referential commit hash in the committed experiment manifest.
    """

    device = _require_nonempty_string(runtime_device, "runtime_device")
    device_base, delimiter, observed_description = device.partition(" | ")
    valid_description = (
        not delimiter
        or (
            bool(observed_description)
            and len(observed_description) <= 256
            and observed_description.isprintable()
            and observed_description == observed_description.strip()
        )
    )
    if (
        not RUNTIME_DEVICE_PATTERN.fullmatch(device_base)
        or not valid_description
    ):
        raise DetectorExperimentValidationError(
            "runtime_device must be 'cuda' or 'cuda:<nonnegative index>', "
            "optionally followed by ' | <printable observed description>'"
        )
    try:
        return ModelProvenance.from_mapping(
            {
                "model_name": detector.model_name,
                "package_name": detector.package_name,
                "package_version": detector.package_version,
                "weights_identifier": detector.weights_identifier,
                "weights_sha256": detector.weights_sha256,
                "code_commit": code_commit,
                "device": device,
                "precision": detector.precision,
                "input_width_px": detector.input_width_px,
                "input_height_px": detector.input_height_px,
                "resize_mode": detector.resize_mode,
                "tiling_enabled": detector.tiling_enabled,
                "target_class_id": detector.target_class_id,
                "target_class_name": detector.target_class_name,
                "export_confidence_floor": detector.export_confidence_floor,
                "postprocessing_description": (
                    detector.postprocessing_description
                ),
            }
        )
    except DetectionRunValidationError as error:
        raise DetectorExperimentValidationError(
            f"Could not build model provenance: {error}"
        ) from error


def load_detector_experiment(path: Path) -> DetectorExperiment:
    manifest_path = path.resolve()
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Detector experiment manifest not found: {manifest_path}"
        )
    try:
        with manifest_path.open("r", encoding="utf-8") as input_file:
            payload = json.load(
                input_file,
                object_pairs_hook=_reject_duplicate_object_keys,
            )
    except json.JSONDecodeError as error:
        raise DetectorExperimentValidationError(
            f"Invalid JSON in detector experiment {manifest_path}: {error}"
        ) from error
    return DetectorExperiment.from_mapping(payload)
