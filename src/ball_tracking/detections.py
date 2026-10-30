"""Strict persisted contract for raw image-space ball detections."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .annotations import AnnotationValidationError, SourceVideo


SCHEMA_VERSION = "0.1"
IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")

TOP_LEVEL_FIELDS = {
    "schema_version",
    "detection_run_id",
    "annotation_set_id",
    "possession_id",
    "source_video",
    "window",
    "model_provenance",
    "frames",
}
WINDOW_FIELDS = {
    "start_frame_index",
    "end_frame_index",
}
MODEL_PROVENANCE_FIELDS = {
    "model_name",
    "package_name",
    "package_version",
    "weights_identifier",
    "weights_sha256",
    "code_commit",
    "device",
    "precision",
    "input_width_px",
    "input_height_px",
    "resize_mode",
    "tiling_enabled",
    "target_class_id",
    "target_class_name",
    "export_confidence_floor",
    "postprocessing_description",
}
FRAME_FIELDS = {
    "frame_index",
    "inference_status",
    "failure_reason",
    "detections",
}
DETECTION_FIELDS = {
    "candidate_index",
    "class_id",
    "class_name",
    "confidence",
    "bbox_xyxy_px",
    "center_xy_px",
}
INFERENCE_STATUSES = {
    "completed",
    "decode_failed",
    "inference_failed",
    "not_run",
}


class DetectionRunValidationError(ValueError):
    """Raised when a persisted detection run violates schema version 0.1."""


def _reject_duplicate_object_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    value: dict[str, Any] = {}

    for key, item in pairs:
        if key in value:
            raise DetectionRunValidationError(
                f"Duplicate JSON object key: {key!r}"
            )

        value[key] = item

    return value


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DetectionRunValidationError(f"{label} must be a JSON object")

    return value


def _validate_exact_fields(
    value: Mapping[str, Any],
    expected: set[str],
    label: str,
) -> None:
    keys = set(value)
    missing = sorted(expected - keys)
    unknown = sorted(keys - expected)

    if missing:
        raise DetectionRunValidationError(f"{label} is missing fields: {missing}")

    if unknown:
        raise DetectionRunValidationError(f"{label} has unknown fields: {unknown}")


def _require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DetectionRunValidationError(f"{label} must be a non-empty string")

    return value.strip()


def _require_identifier(value: Any, label: str) -> str:
    identifier = _require_nonempty_string(value, label)

    if not IDENTIFIER_PATTERN.fullmatch(identifier):
        raise DetectionRunValidationError(
            f"{label} must match {IDENTIFIER_PATTERN.pattern!r}: "
            f"{identifier!r}"
        )

    return identifier


def _require_integer(value: Any, label: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DetectionRunValidationError(f"{label} must be an integer")

    if value < minimum:
        raise DetectionRunValidationError(f"{label} must be >= {minimum}")

    return value


def _require_finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DetectionRunValidationError(f"{label} must be numeric")

    result = float(value)

    if not math.isfinite(result):
        raise DetectionRunValidationError(f"{label} must be finite")

    return result


def _require_unit_interval(value: Any, label: str) -> float:
    result = _require_finite_number(value, label)

    if not 0.0 <= result <= 1.0:
        raise DetectionRunValidationError(f"{label} must be in [0, 1]")

    return result


def _require_boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise DetectionRunValidationError(f"{label} must be a boolean")

    return value


def _require_enum(value: Any, label: str, allowed: set[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise DetectionRunValidationError(
            f"{label} must be one of {sorted(allowed)}"
        )

    return value


def _require_numeric_array(
    value: Any,
    label: str,
    length: int,
) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) != length:
        raise DetectionRunValidationError(
            f"{label} must be a {length}-value JSON array"
        )

    return tuple(
        _require_finite_number(item, f"{label}[{index}]")
        for index, item in enumerate(value)
    )


@dataclass(frozen=True)
class DetectionWindow:
    start_frame_index: int
    end_frame_index: int

    @classmethod
    def from_mapping(
        cls,
        value: Any,
        source_video: SourceVideo,
    ) -> "DetectionWindow":
        window = _require_mapping(value, "window")
        _validate_exact_fields(window, WINDOW_FIELDS, "window")
        start = _require_integer(
            window["start_frame_index"],
            "window.start_frame_index",
            0,
        )
        end = _require_integer(
            window["end_frame_index"],
            "window.end_frame_index",
            0,
        )

        if end < start:
            raise DetectionRunValidationError(
                "window.end_frame_index must be >= window.start_frame_index"
            )

        if end >= source_video.frame_count:
            raise DetectionRunValidationError(
                "window.end_frame_index must be below "
                "source_video.frame_count"
            )

        return cls(
            start_frame_index=start,
            end_frame_index=end,
        )

    @property
    def frame_count(self) -> int:
        return self.end_frame_index - self.start_frame_index + 1

    def to_dict(self) -> dict[str, int]:
        return {
            "start_frame_index": self.start_frame_index,
            "end_frame_index": self.end_frame_index,
        }


@dataclass(frozen=True)
class ModelProvenance:
    model_name: str
    package_name: str
    package_version: str
    weights_identifier: str
    weights_sha256: str
    code_commit: str
    device: str
    precision: str
    input_width_px: int
    input_height_px: int
    resize_mode: str
    tiling_enabled: bool
    target_class_id: int
    target_class_name: str
    export_confidence_floor: float
    postprocessing_description: str

    @classmethod
    def from_mapping(cls, value: Any) -> "ModelProvenance":
        provenance = _require_mapping(value, "model_provenance")
        _validate_exact_fields(
            provenance,
            MODEL_PROVENANCE_FIELDS,
            "model_provenance",
        )
        weights_sha256 = _require_nonempty_string(
            provenance["weights_sha256"],
            "model_provenance.weights_sha256",
        )
        code_commit = _require_nonempty_string(
            provenance["code_commit"],
            "model_provenance.code_commit",
        )

        if not SHA256_PATTERN.fullmatch(weights_sha256):
            raise DetectionRunValidationError(
                "model_provenance.weights_sha256 must contain exactly 64 "
                "lowercase hexadecimal characters"
            )

        if not COMMIT_PATTERN.fullmatch(code_commit):
            raise DetectionRunValidationError(
                "model_provenance.code_commit must contain exactly 40 "
                "lowercase hexadecimal characters"
            )

        return cls(
            model_name=_require_nonempty_string(
                provenance["model_name"],
                "model_provenance.model_name",
            ),
            package_name=_require_nonempty_string(
                provenance["package_name"],
                "model_provenance.package_name",
            ),
            package_version=_require_nonempty_string(
                provenance["package_version"],
                "model_provenance.package_version",
            ),
            weights_identifier=_require_nonempty_string(
                provenance["weights_identifier"],
                "model_provenance.weights_identifier",
            ),
            weights_sha256=weights_sha256,
            code_commit=code_commit,
            device=_require_nonempty_string(
                provenance["device"],
                "model_provenance.device",
            ),
            precision=_require_nonempty_string(
                provenance["precision"],
                "model_provenance.precision",
            ),
            input_width_px=_require_integer(
                provenance["input_width_px"],
                "model_provenance.input_width_px",
                1,
            ),
            input_height_px=_require_integer(
                provenance["input_height_px"],
                "model_provenance.input_height_px",
                1,
            ),
            resize_mode=_require_nonempty_string(
                provenance["resize_mode"],
                "model_provenance.resize_mode",
            ),
            tiling_enabled=_require_boolean(
                provenance["tiling_enabled"],
                "model_provenance.tiling_enabled",
            ),
            target_class_id=_require_integer(
                provenance["target_class_id"],
                "model_provenance.target_class_id",
                0,
            ),
            target_class_name=_require_nonempty_string(
                provenance["target_class_name"],
                "model_provenance.target_class_name",
            ),
            export_confidence_floor=_require_unit_interval(
                provenance["export_confidence_floor"],
                "model_provenance.export_confidence_floor",
            ),
            postprocessing_description=_require_nonempty_string(
                provenance["postprocessing_description"],
                "model_provenance.postprocessing_description",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "package_name": self.package_name,
            "package_version": self.package_version,
            "weights_identifier": self.weights_identifier,
            "weights_sha256": self.weights_sha256,
            "code_commit": self.code_commit,
            "device": self.device,
            "precision": self.precision,
            "input_width_px": self.input_width_px,
            "input_height_px": self.input_height_px,
            "resize_mode": self.resize_mode,
            "tiling_enabled": self.tiling_enabled,
            "target_class_id": self.target_class_id,
            "target_class_name": self.target_class_name,
            "export_confidence_floor": self.export_confidence_floor,
            "postprocessing_description": self.postprocessing_description,
        }


@dataclass(frozen=True)
class BallDetection:
    candidate_index: int
    class_id: int
    class_name: str
    confidence: float
    bbox_xyxy_px: tuple[float, float, float, float]
    center_xy_px: tuple[float, float]

    @classmethod
    def from_mapping(
        cls,
        value: Any,
        *,
        label: str,
        expected_candidate_index: int,
        source_video: SourceVideo,
        model_provenance: ModelProvenance,
    ) -> "BallDetection":
        detection = _require_mapping(value, label)
        _validate_exact_fields(detection, DETECTION_FIELDS, label)
        candidate_index = _require_integer(
            detection["candidate_index"],
            f"{label}.candidate_index",
            0,
        )

        if candidate_index != expected_candidate_index:
            raise DetectionRunValidationError(
                f"{label}.candidate_index must equal list position "
                f"{expected_candidate_index}"
            )

        class_id = _require_integer(
            detection["class_id"],
            f"{label}.class_id",
            0,
        )
        class_name = _require_nonempty_string(
            detection["class_name"],
            f"{label}.class_name",
        )

        if class_id != model_provenance.target_class_id:
            raise DetectionRunValidationError(
                f"{label}.class_id must equal "
                "model_provenance.target_class_id"
            )

        if class_name != model_provenance.target_class_name:
            raise DetectionRunValidationError(
                f"{label}.class_name must equal "
                "model_provenance.target_class_name"
            )

        confidence = _require_unit_interval(
            detection["confidence"],
            f"{label}.confidence",
        )

        if confidence < model_provenance.export_confidence_floor:
            raise DetectionRunValidationError(
                f"{label}.confidence must be >= "
                "model_provenance.export_confidence_floor"
            )

        bbox = _require_numeric_array(
            detection["bbox_xyxy_px"],
            f"{label}.bbox_xyxy_px",
            4,
        )
        x1, y1, x2, y2 = bbox

        if not 0.0 <= x1 < x2 <= source_video.width_px:
            raise DetectionRunValidationError(
                f"{label}.bbox_xyxy_px must satisfy "
                "0 <= x1 < x2 <= source width"
            )

        if not 0.0 <= y1 < y2 <= source_video.height_px:
            raise DetectionRunValidationError(
                f"{label}.bbox_xyxy_px must satisfy "
                "0 <= y1 < y2 <= source height"
            )

        center = _require_numeric_array(
            detection["center_xy_px"],
            f"{label}.center_xy_px",
            2,
        )
        center_x, center_y = center

        if not 0.0 <= center_x < source_video.width_px:
            raise DetectionRunValidationError(
                f"{label}.center_xy_px[0] must be within source width"
            )

        if not 0.0 <= center_y < source_video.height_px:
            raise DetectionRunValidationError(
                f"{label}.center_xy_px[1] must be within source height"
            )

        expected_center_x = (x1 + x2) / 2.0
        expected_center_y = (y1 + y2) / 2.0

        if not math.isclose(
            center_x,
            expected_center_x,
            rel_tol=0.0,
            abs_tol=1e-6,
        ) or not math.isclose(
            center_y,
            expected_center_y,
            rel_tol=0.0,
            abs_tol=1e-6,
        ):
            raise DetectionRunValidationError(
                f"{label}.center_xy_px must equal the bbox midpoint"
            )

        return cls(
            candidate_index=candidate_index,
            class_id=class_id,
            class_name=class_name,
            confidence=confidence,
            bbox_xyxy_px=(x1, y1, x2, y2),
            center_xy_px=(center_x, center_y),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_index": self.candidate_index,
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "bbox_xyxy_px": list(self.bbox_xyxy_px),
            "center_xy_px": list(self.center_xy_px),
        }


@dataclass(frozen=True)
class DetectionFrame:
    frame_index: int
    inference_status: str
    failure_reason: str | None
    detections: tuple[BallDetection, ...] | None

    @classmethod
    def from_mapping(
        cls,
        value: Any,
        *,
        frame_position: int,
        source_video: SourceVideo,
        model_provenance: ModelProvenance,
    ) -> "DetectionFrame":
        label = f"frames[{frame_position}]"
        frame = _require_mapping(value, label)
        _validate_exact_fields(frame, FRAME_FIELDS, label)
        frame_index = _require_integer(
            frame["frame_index"],
            f"{label}.frame_index",
            0,
        )
        inference_status = _require_enum(
            frame["inference_status"],
            f"{label}.inference_status",
            INFERENCE_STATUSES,
        )
        raw_failure_reason = frame["failure_reason"]
        raw_detections = frame["detections"]

        if inference_status == "completed":
            if raw_failure_reason is not None:
                raise DetectionRunValidationError(
                    f"{label} completed inference requires null failure_reason"
                )

            if not isinstance(raw_detections, list):
                raise DetectionRunValidationError(
                    f"{label} completed inference requires a detections array"
                )

            detections = tuple(
                BallDetection.from_mapping(
                    raw_detection,
                    label=f"{label}.detections[{candidate_index}]",
                    expected_candidate_index=candidate_index,
                    source_video=source_video,
                    model_provenance=model_provenance,
                )
                for candidate_index, raw_detection in enumerate(raw_detections)
            )
            failure_reason = None
        else:
            failure_reason = _require_nonempty_string(
                raw_failure_reason,
                f"{label}.failure_reason",
            )

            if raw_detections is not None:
                raise DetectionRunValidationError(
                    f"{label} failed or unrun inference requires null detections"
                )

            detections = None

        return cls(
            frame_index=frame_index,
            inference_status=inference_status,
            failure_reason=failure_reason,
            detections=detections,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "inference_status": self.inference_status,
            "failure_reason": self.failure_reason,
            "detections": (
                None
                if self.detections is None
                else [detection.to_dict() for detection in self.detections]
            ),
        }


@dataclass(frozen=True)
class BallDetectionRun:
    schema_version: str
    detection_run_id: str
    annotation_set_id: str
    possession_id: str
    source_video: SourceVideo
    window: DetectionWindow
    model_provenance: ModelProvenance
    frames: tuple[DetectionFrame, ...]

    @classmethod
    def from_mapping(cls, value: Any) -> "BallDetectionRun":
        payload = _require_mapping(value, "ball detection run")
        _validate_exact_fields(payload, TOP_LEVEL_FIELDS, "ball detection run")

        if payload["schema_version"] != SCHEMA_VERSION:
            raise DetectionRunValidationError(
                f"Unsupported schema_version {payload['schema_version']!r}; "
                f"expected {SCHEMA_VERSION!r}"
            )

        try:
            source_video = SourceVideo.from_mapping(payload["source_video"])
        except AnnotationValidationError as error:
            raise DetectionRunValidationError(str(error)) from error

        window = DetectionWindow.from_mapping(payload["window"], source_video)
        model_provenance = ModelProvenance.from_mapping(
            payload["model_provenance"]
        )
        raw_frames = payload["frames"]

        if not isinstance(raw_frames, list):
            raise DetectionRunValidationError("frames must be a JSON array")

        frames = tuple(
            DetectionFrame.from_mapping(
                raw_frame,
                frame_position=frame_position,
                source_video=source_video,
                model_provenance=model_provenance,
            )
            for frame_position, raw_frame in enumerate(raw_frames)
        )
        expected_indices = list(
            range(window.start_frame_index, window.end_frame_index + 1)
        )
        actual_indices = [frame.frame_index for frame in frames]

        if actual_indices != expected_indices:
            raise DetectionRunValidationError(
                "frames must contain exactly one sorted record for every "
                "inclusive window frame; expected "
                f"{expected_indices}, received {actual_indices}"
            )

        return cls(
            schema_version=SCHEMA_VERSION,
            detection_run_id=_require_identifier(
                payload["detection_run_id"],
                "detection_run_id",
            ),
            annotation_set_id=_require_identifier(
                payload["annotation_set_id"],
                "annotation_set_id",
            ),
            possession_id=_require_identifier(
                payload["possession_id"],
                "possession_id",
            ),
            source_video=source_video,
            window=window,
            model_provenance=model_provenance,
            frames=frames,
        )

    def frame_by_index(self) -> dict[int, DetectionFrame]:
        return {frame.frame_index: frame for frame in self.frames}

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "detection_run_id": self.detection_run_id,
            "annotation_set_id": self.annotation_set_id,
            "possession_id": self.possession_id,
            "source_video": self.source_video.to_dict(),
            "window": self.window.to_dict(),
            "model_provenance": self.model_provenance.to_dict(),
            "frames": [frame.to_dict() for frame in self.frames],
        }


def load_detection_run(path: Path) -> BallDetectionRun:
    run_path = path.resolve()

    if not run_path.is_file():
        raise FileNotFoundError(f"Ball detection run JSON not found: {run_path}")

    try:
        with run_path.open("r", encoding="utf-8") as input_file:
            payload = json.load(
                input_file,
                object_pairs_hook=_reject_duplicate_object_keys,
            )
    except json.JSONDecodeError as error:
        raise DetectionRunValidationError(
            f"Invalid JSON in ball detection run {run_path}: {error}"
        ) from error

    return BallDetectionRun.from_mapping(payload)
