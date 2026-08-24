"""Strict schema and invariants for reviewed ball-center annotations."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


SCHEMA_VERSION = "0.1"
IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

TOP_LEVEL_FIELDS = {
    "schema_version",
    "annotation_set_id",
    "possession_id",
    "source_video",
    "window",
    "coordinate_system",
    "review",
    "annotations",
}
SOURCE_VIDEO_FIELDS = {
    "path",
    "sha256",
    "width_px",
    "height_px",
    "fps",
    "frame_count",
}
WINDOW_FIELDS = {
    "start_frame_index",
    "end_frame_index",
    "selection_purpose",
}
COORDINATE_SYSTEM_FIELDS = {
    "frame_index_origin",
    "pixel_origin",
    "x_axis_direction",
    "y_axis_direction",
    "center_definition",
    "timestamp_rule",
}
REVIEW_FIELDS = {
    "status",
    "annotator_id",
    "reviewer_id",
    "created_at_utc",
    "reviewed_at_utc",
}
ANNOTATION_FIELDS = {
    "frame_index",
    "annotation_status",
    "visibility",
    "absence_reason",
    "game_ball_identity_certainty",
    "geometry",
    "localization_eligible",
    "difficulty_tags",
    "notes",
}
GEOMETRY_FIELDS = {
    "center_xy_px",
    "source",
    "uncertainty_radius_px",
}

ANNOTATION_STATUSES = {"labeled", "unlabeled", "excluded"}
VISIBILITY_STATES = {
    "fully_visible",
    "partially_visible",
    "not_visible",
    "indeterminate",
}
ABSENCE_REASONS = {"occluded", "out_of_frame", "unknown"}
IDENTITY_CERTAINTIES = {"certain", "probable", "ambiguous"}
GEOMETRY_SOURCES = {
    "observed_complete_ball_center",
    "human_amodal_estimate",
}
DIFFICULTY_TAGS = {
    "tiny_apparent_size",
    "motion_blur",
    "defocus",
    "hand_overlap",
    "player_overlap",
    "rim_net_backboard_overlap",
    "background_clutter",
    "camera_motion",
    "compression_artifact",
    "overlay_or_cut",
}
SELECTION_PURPOSES = {
    "protocol_adjudication",
    "representative_evaluation",
    "challenge_evaluation",
    "training",
    "validation_calibration",
    "test_holdout",
}


class AnnotationValidationError(ValueError):
    """Raised when ball annotations violate schema version 0.1."""


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AnnotationValidationError(f"{label} must be a JSON object")

    return value


def _reject_duplicate_json_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result = {}

    for key, value in pairs:
        if key in result:
            raise AnnotationValidationError(
                f"Duplicate JSON object key: {key!r}"
            )

        result[key] = value

    return result


def _validate_exact_fields(
    value: Mapping[str, Any],
    expected: set[str],
    label: str,
) -> None:
    keys = set(value)
    missing = sorted(expected - keys)
    unknown = sorted(keys - expected)

    if missing:
        raise AnnotationValidationError(f"{label} is missing fields: {missing}")

    if unknown:
        raise AnnotationValidationError(f"{label} has unknown fields: {unknown}")


def _require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AnnotationValidationError(f"{label} must be a non-empty string")

    return value.strip()


def _require_optional_nonempty_string(value: Any, label: str) -> str | None:
    if value is None:
        return None

    return _require_nonempty_string(value, label)


def _require_identifier(value: Any, label: str) -> str:
    identifier = _require_nonempty_string(value, label)

    if not IDENTIFIER_PATTERN.fullmatch(identifier):
        raise AnnotationValidationError(
            f"{label} must match {IDENTIFIER_PATTERN.pattern!r}: {identifier!r}"
        )

    return identifier


def _require_integer(
    value: Any,
    label: str,
    minimum: int,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AnnotationValidationError(f"{label} must be an integer")

    if value < minimum:
        raise AnnotationValidationError(f"{label} must be >= {minimum}")

    return value


def _require_number(
    value: Any,
    label: str,
    minimum: float,
    *,
    minimum_inclusive: bool = True,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AnnotationValidationError(f"{label} must be numeric")

    result = float(value)

    if not math.isfinite(result):
        raise AnnotationValidationError(f"{label} must be finite")

    valid = result >= minimum if minimum_inclusive else result > minimum

    if not valid:
        operator = ">=" if minimum_inclusive else ">"
        raise AnnotationValidationError(f"{label} must be {operator} {minimum}")

    return result


def _require_boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise AnnotationValidationError(f"{label} must be a boolean")

    return value


def _require_enum(value: Any, label: str, allowed: set[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise AnnotationValidationError(
            f"{label} must be one of {sorted(allowed)}"
        )

    return value


def _require_optional_enum(
    value: Any,
    label: str,
    allowed: set[str],
) -> str | None:
    if value is None:
        return None

    return _require_enum(value, label, allowed)


def _parse_utc_datetime(timestamp: str, label: str) -> datetime:
    parseable = timestamp[:-1] + "+00:00" if timestamp.endswith("Z") else timestamp

    try:
        parsed = datetime.fromisoformat(parseable)
    except ValueError as error:
        raise AnnotationValidationError(
            f"{label} must be an ISO-8601 UTC timestamp"
        ) from error

    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise AnnotationValidationError(
            f"{label} must include an explicit UTC offset"
        )

    return parsed


def _require_utc_timestamp(value: Any, label: str) -> str:
    timestamp = _require_nonempty_string(value, label)
    _parse_utc_datetime(timestamp, label)
    return timestamp


def _require_optional_utc_timestamp(value: Any, label: str) -> str | None:
    if value is None:
        return None

    return _require_utc_timestamp(value, label)


def _require_portable_relative_path(value: Any, label: str) -> PurePosixPath:
    raw_path = _require_nonempty_string(value, label)

    if "\\" in raw_path:
        raise AnnotationValidationError(
            f"{label} must use forward slashes for portability"
        )

    path = PurePosixPath(raw_path)

    if (
        path.is_absolute()
        or ".." in path.parts
        or path == PurePosixPath(".")
        or any(":" in part for part in path.parts)
    ):
        raise AnnotationValidationError(
            f"{label} must stay within the repository: {raw_path!r}"
        )

    return path


@dataclass(frozen=True)
class SourceVideo:
    path: PurePosixPath
    sha256: str
    width_px: int
    height_px: int
    fps: float
    frame_count: int

    @classmethod
    def from_mapping(cls, value: Any) -> "SourceVideo":
        source = _require_mapping(value, "source_video")
        _validate_exact_fields(source, SOURCE_VIDEO_FIELDS, "source_video")
        sha256 = _require_nonempty_string(
            source["sha256"],
            "source_video.sha256",
        )

        if not SHA256_PATTERN.fullmatch(sha256):
            raise AnnotationValidationError(
                "source_video.sha256 must contain exactly 64 lowercase "
                "hexadecimal characters"
            )

        return cls(
            path=_require_portable_relative_path(
                source["path"],
                "source_video.path",
            ),
            sha256=sha256,
            width_px=_require_integer(
                source["width_px"],
                "source_video.width_px",
                1,
            ),
            height_px=_require_integer(
                source["height_px"],
                "source_video.height_px",
                1,
            ),
            fps=_require_number(
                source["fps"],
                "source_video.fps",
                0.0,
                minimum_inclusive=False,
            ),
            frame_count=_require_integer(
                source["frame_count"],
                "source_video.frame_count",
                1,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path.as_posix(),
            "sha256": self.sha256,
            "width_px": self.width_px,
            "height_px": self.height_px,
            "fps": self.fps,
            "frame_count": self.frame_count,
        }


@dataclass(frozen=True)
class AnnotationWindow:
    start_frame_index: int
    end_frame_index: int
    selection_purpose: str

    @classmethod
    def from_mapping(
        cls,
        value: Any,
        source_video: SourceVideo,
    ) -> "AnnotationWindow":
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
            raise AnnotationValidationError(
                "window.end_frame_index must be >= window.start_frame_index"
            )

        if end >= source_video.frame_count:
            raise AnnotationValidationError(
                "window.end_frame_index must be below "
                "source_video.frame_count"
            )

        return cls(
            start_frame_index=start,
            end_frame_index=end,
            selection_purpose=_require_enum(
                window["selection_purpose"],
                "window.selection_purpose",
                SELECTION_PURPOSES,
            ),
        )

    @property
    def frame_count(self) -> int:
        return self.end_frame_index - self.start_frame_index + 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_frame_index": self.start_frame_index,
            "end_frame_index": self.end_frame_index,
            "selection_purpose": self.selection_purpose,
        }


@dataclass(frozen=True)
class CoordinateSystem:
    frame_index_origin: int
    pixel_origin: str
    x_axis_direction: str
    y_axis_direction: str
    center_definition: str
    timestamp_rule: str

    @classmethod
    def from_mapping(cls, value: Any) -> "CoordinateSystem":
        coordinate_system = _require_mapping(value, "coordinate_system")
        _validate_exact_fields(
            coordinate_system,
            COORDINATE_SYSTEM_FIELDS,
            "coordinate_system",
        )
        expected = {
            "frame_index_origin": 0,
            "pixel_origin": "top_left",
            "x_axis_direction": "right",
            "y_axis_direction": "down",
            "center_definition": "complete_ball_center",
            "timestamp_rule": "frame_index_divided_by_fps",
        }

        for field, expected_value in expected.items():
            actual = coordinate_system[field]

            if field == "frame_index_origin":
                actual_matches = (
                    isinstance(actual, int)
                    and not isinstance(actual, bool)
                    and actual == expected_value
                )
            else:
                actual_matches = actual == expected_value

            if not actual_matches:
                raise AnnotationValidationError(
                    f"coordinate_system.{field} must be {expected_value!r}"
                )

        return cls(**expected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_index_origin": self.frame_index_origin,
            "pixel_origin": self.pixel_origin,
            "x_axis_direction": self.x_axis_direction,
            "y_axis_direction": self.y_axis_direction,
            "center_definition": self.center_definition,
            "timestamp_rule": self.timestamp_rule,
        }


@dataclass(frozen=True)
class AnnotationReview:
    status: str
    annotator_id: str
    reviewer_id: str | None
    created_at_utc: str
    reviewed_at_utc: str | None

    @classmethod
    def from_mapping(cls, value: Any) -> "AnnotationReview":
        review = _require_mapping(value, "review")
        _validate_exact_fields(review, REVIEW_FIELDS, "review")
        status = _require_enum(
            review["status"],
            "review.status",
            {"draft", "reviewed"},
        )
        reviewer_id = _require_optional_nonempty_string(
            review["reviewer_id"],
            "review.reviewer_id",
        )
        reviewed_at_utc = _require_optional_utc_timestamp(
            review["reviewed_at_utc"],
            "review.reviewed_at_utc",
        )
        created_at_utc = _require_utc_timestamp(
            review["created_at_utc"],
            "review.created_at_utc",
        )

        if status == "draft" and (
            reviewer_id is not None or reviewed_at_utc is not None
        ):
            raise AnnotationValidationError(
                "draft review requires reviewer_id and reviewed_at_utc to be null"
            )

        if status == "reviewed" and (
            reviewer_id is None or reviewed_at_utc is None
        ):
            raise AnnotationValidationError(
                "reviewed review requires reviewer_id and reviewed_at_utc"
            )

        if (
            reviewed_at_utc is not None
            and _parse_utc_datetime(
                reviewed_at_utc,
                "review.reviewed_at_utc",
            )
            < _parse_utc_datetime(
                created_at_utc,
                "review.created_at_utc",
            )
        ):
            raise AnnotationValidationError(
                "review.reviewed_at_utc cannot precede review.created_at_utc"
            )

        return cls(
            status=status,
            annotator_id=_require_nonempty_string(
                review["annotator_id"],
                "review.annotator_id",
            ),
            reviewer_id=reviewer_id,
            created_at_utc=created_at_utc,
            reviewed_at_utc=reviewed_at_utc,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "annotator_id": self.annotator_id,
            "reviewer_id": self.reviewer_id,
            "created_at_utc": self.created_at_utc,
            "reviewed_at_utc": self.reviewed_at_utc,
        }


@dataclass(frozen=True)
class BallGeometry:
    center_xy_px: tuple[float, float]
    source: str
    uncertainty_radius_px: float

    @classmethod
    def from_mapping(
        cls,
        value: Any,
        label: str,
        source_video: SourceVideo,
    ) -> "BallGeometry":
        geometry = _require_mapping(value, label)
        _validate_exact_fields(geometry, GEOMETRY_FIELDS, label)
        raw_center = geometry["center_xy_px"]

        if not isinstance(raw_center, list) or len(raw_center) != 2:
            raise AnnotationValidationError(
                f"{label}.center_xy_px must be a two-value JSON array"
            )

        center_x = _require_number(
            raw_center[0],
            f"{label}.center_xy_px[0]",
            0.0,
        )
        center_y = _require_number(
            raw_center[1],
            f"{label}.center_xy_px[1]",
            0.0,
        )

        if center_x >= source_video.width_px:
            raise AnnotationValidationError(
                f"{label}.center_xy_px[0] must be below source_video.width_px"
            )

        if center_y >= source_video.height_px:
            raise AnnotationValidationError(
                f"{label}.center_xy_px[1] must be below source_video.height_px"
            )

        uncertainty_radius_px = _require_number(
            geometry["uncertainty_radius_px"],
            f"{label}.uncertainty_radius_px",
            0.0,
            minimum_inclusive=False,
        )
        maximum_uncertainty_radius_px = math.hypot(
            source_video.width_px,
            source_video.height_px,
        )

        if uncertainty_radius_px > maximum_uncertainty_radius_px:
            raise AnnotationValidationError(
                f"{label}.uncertainty_radius_px cannot exceed the source "
                "image diagonal"
            )

        return cls(
            center_xy_px=(center_x, center_y),
            source=_require_enum(
                geometry["source"],
                f"{label}.source",
                GEOMETRY_SOURCES,
            ),
            uncertainty_radius_px=uncertainty_radius_px,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "center_xy_px": list(self.center_xy_px),
            "source": self.source,
            "uncertainty_radius_px": self.uncertainty_radius_px,
        }


@dataclass(frozen=True)
class FrameAnnotation:
    frame_index: int
    annotation_status: str
    visibility: str | None
    absence_reason: str | None
    game_ball_identity_certainty: str | None
    geometry: BallGeometry | None
    localization_eligible: bool
    difficulty_tags: tuple[str, ...]
    notes: str | None

    @classmethod
    def from_mapping(
        cls,
        value: Any,
        annotation_index: int,
        source_video: SourceVideo,
    ) -> "FrameAnnotation":
        label = f"annotations[{annotation_index}]"
        annotation = _require_mapping(value, label)
        _validate_exact_fields(annotation, ANNOTATION_FIELDS, label)
        status = _require_enum(
            annotation["annotation_status"],
            f"{label}.annotation_status",
            ANNOTATION_STATUSES,
        )
        visibility = _require_optional_enum(
            annotation["visibility"],
            f"{label}.visibility",
            VISIBILITY_STATES,
        )
        absence_reason = _require_optional_enum(
            annotation["absence_reason"],
            f"{label}.absence_reason",
            ABSENCE_REASONS,
        )
        certainty = _require_optional_enum(
            annotation["game_ball_identity_certainty"],
            f"{label}.game_ball_identity_certainty",
            IDENTITY_CERTAINTIES,
        )
        geometry = (
            None
            if annotation["geometry"] is None
            else BallGeometry.from_mapping(
                annotation["geometry"],
                f"{label}.geometry",
                source_video,
            )
        )
        localization_eligible = _require_boolean(
            annotation["localization_eligible"],
            f"{label}.localization_eligible",
        )
        raw_tags = annotation["difficulty_tags"]

        if not isinstance(raw_tags, list):
            raise AnnotationValidationError(
                f"{label}.difficulty_tags must be a JSON array"
            )

        tags = []

        for tag_index, tag in enumerate(raw_tags):
            tags.append(
                _require_enum(
                    tag,
                    f"{label}.difficulty_tags[{tag_index}]",
                    DIFFICULTY_TAGS,
                )
            )

        if tags != sorted(set(tags)):
            raise AnnotationValidationError(
                f"{label}.difficulty_tags must be sorted and unique"
            )

        notes = _require_optional_nonempty_string(
            annotation["notes"],
            f"{label}.notes",
        )
        frame = cls(
            frame_index=_require_integer(
                annotation["frame_index"],
                f"{label}.frame_index",
                0,
            ),
            annotation_status=status,
            visibility=visibility,
            absence_reason=absence_reason,
            game_ball_identity_certainty=certainty,
            geometry=geometry,
            localization_eligible=localization_eligible,
            difficulty_tags=tuple(tags),
            notes=notes,
        )
        frame._validate_cross_field_contract(label)
        return frame

    def _validate_cross_field_contract(self, label: str) -> None:
        if self.annotation_status in {"unlabeled", "excluded"}:
            semantic_values = (
                self.visibility,
                self.absence_reason,
                self.game_ball_identity_certainty,
                self.geometry,
            )

            if any(value is not None for value in semantic_values):
                raise AnnotationValidationError(
                    f"{label} {self.annotation_status} semantic fields must be null"
                )

            if self.localization_eligible:
                raise AnnotationValidationError(
                    f"{label} {self.annotation_status} cannot be localization eligible"
                )

            if self.difficulty_tags:
                raise AnnotationValidationError(
                    f"{label} {self.annotation_status} difficulty_tags must be empty"
                )

            if self.annotation_status == "excluded" and self.notes is None:
                raise AnnotationValidationError(
                    f"{label} excluded annotation requires notes"
                )

            return

        if self.visibility is None:
            raise AnnotationValidationError(
                f"{label} labeled annotation requires visibility"
            )

        if self.game_ball_identity_certainty is None:
            raise AnnotationValidationError(
                f"{label} labeled annotation requires non-null game-ball "
                "identity certainty"
            )

        if self.visibility == "not_visible":
            if self.absence_reason is None:
                raise AnnotationValidationError(
                    f"{label} not_visible annotation requires absence_reason"
                )

            if self.geometry is not None or self.localization_eligible:
                raise AnnotationValidationError(
                    f"{label} not_visible annotation forbids geometry and "
                    "localization eligibility"
                )

        elif self.visibility == "indeterminate":
            if self.game_ball_identity_certainty != "ambiguous":
                raise AnnotationValidationError(
                    f"{label} indeterminate annotation requires ambiguous "
                    "game-ball identity certainty"
                )

            if self.absence_reason is not None or self.geometry is not None:
                raise AnnotationValidationError(
                    f"{label} indeterminate annotation forbids absence_reason "
                    "and geometry"
                )

            if self.localization_eligible:
                raise AnnotationValidationError(
                    f"{label} indeterminate annotation cannot be localization "
                    "eligible"
                )

            if self.notes is None:
                raise AnnotationValidationError(
                    f"{label} indeterminate annotation requires notes"
                )

        else:
            if self.absence_reason is not None:
                raise AnnotationValidationError(
                    f"{label} visible annotation forbids absence_reason"
                )

            if self.geometry is None or not self.localization_eligible:
                if self.notes is None:
                    raise AnnotationValidationError(
                        f"{label} visible annotation without eligible geometry "
                        "requires notes"
                    )

        if self.geometry is not None:
            if self.visibility == "fully_visible":
                if self.geometry.source != "observed_complete_ball_center":
                    raise AnnotationValidationError(
                        f"{label} fully_visible geometry must use "
                        "observed_complete_ball_center"
                    )
            elif self.visibility == "partially_visible":
                if self.geometry.source != "human_amodal_estimate":
                    raise AnnotationValidationError(
                        f"{label} partially_visible geometry must use "
                        "human_amodal_estimate"
                    )

                if self.geometry.uncertainty_radius_px <= 0.0:
                    raise AnnotationValidationError(
                        f"{label} partially_visible geometry requires a "
                        "positive uncertainty radius"
                    )

        if self.localization_eligible:
            if self.geometry is None:
                raise AnnotationValidationError(
                    f"{label} localization eligibility requires geometry"
                )

            if self.game_ball_identity_certainty not in {"certain", "probable"}:
                raise AnnotationValidationError(
                    f"{label} localization eligibility requires certain or "
                    "probable game-ball identity"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "annotation_status": self.annotation_status,
            "visibility": self.visibility,
            "absence_reason": self.absence_reason,
            "game_ball_identity_certainty": (
                self.game_ball_identity_certainty
            ),
            "geometry": None if self.geometry is None else self.geometry.to_dict(),
            "localization_eligible": self.localization_eligible,
            "difficulty_tags": list(self.difficulty_tags),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class BallAnnotationSet:
    schema_version: str
    annotation_set_id: str
    possession_id: str
    source_video: SourceVideo
    window: AnnotationWindow
    coordinate_system: CoordinateSystem
    review: AnnotationReview
    annotations: tuple[FrameAnnotation, ...]

    @classmethod
    def from_mapping(cls, value: Any) -> "BallAnnotationSet":
        payload = _require_mapping(value, "ball annotation set")
        _validate_exact_fields(payload, TOP_LEVEL_FIELDS, "ball annotation set")

        if payload["schema_version"] != SCHEMA_VERSION:
            raise AnnotationValidationError(
                f"Unsupported schema_version {payload['schema_version']!r}; "
                f"expected {SCHEMA_VERSION!r}"
            )

        source_video = SourceVideo.from_mapping(payload["source_video"])
        window = AnnotationWindow.from_mapping(payload["window"], source_video)
        raw_annotations = payload["annotations"]

        if not isinstance(raw_annotations, list):
            raise AnnotationValidationError("annotations must be a JSON array")

        annotations = tuple(
            FrameAnnotation.from_mapping(
                raw_annotation,
                annotation_index,
                source_video,
            )
            for annotation_index, raw_annotation in enumerate(raw_annotations)
        )
        expected_frames = list(
            range(window.start_frame_index, window.end_frame_index + 1)
        )
        actual_frames = [annotation.frame_index for annotation in annotations]

        if actual_frames != expected_frames:
            raise AnnotationValidationError(
                "annotations must contain exactly one sorted record for every "
                "inclusive window frame; expected "
                f"{expected_frames}, received {actual_frames}"
            )

        review = AnnotationReview.from_mapping(payload["review"])

        if review.status == "reviewed":
            unlabeled_frames = [
                annotation.frame_index
                for annotation in annotations
                if annotation.annotation_status == "unlabeled"
            ]

            if unlabeled_frames:
                raise AnnotationValidationError(
                    "reviewed annotation set cannot contain unlabeled frames: "
                    f"{unlabeled_frames}"
                )

        return cls(
            schema_version=SCHEMA_VERSION,
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
            coordinate_system=CoordinateSystem.from_mapping(
                payload["coordinate_system"]
            ),
            review=review,
            annotations=annotations,
        )

    def annotation_by_frame(self) -> dict[int, FrameAnnotation]:
        return {
            annotation.frame_index: annotation
            for annotation in self.annotations
        }

    def validation_summary(self) -> dict[str, Any]:
        status_counts = Counter(
            annotation.annotation_status for annotation in self.annotations
        )
        visibility_counts = Counter(
            annotation.visibility
            for annotation in self.annotations
            if annotation.visibility is not None
        )
        return {
            "status": "valid_ball_annotation_set",
            "schema_version": self.schema_version,
            "annotation_set_id": self.annotation_set_id,
            "possession_id": self.possession_id,
            "source_video_path": self.source_video.path.as_posix(),
            "start_frame_index": self.window.start_frame_index,
            "end_frame_index": self.window.end_frame_index,
            "frame_count": len(self.annotations),
            "annotation_status_counts": {
                key: status_counts.get(key, 0)
                for key in sorted(ANNOTATION_STATUSES)
            },
            "visibility_counts": {
                key: visibility_counts.get(key, 0)
                for key in sorted(VISIBILITY_STATES)
            },
            "localization_eligible_count": sum(
                annotation.localization_eligible
                for annotation in self.annotations
            ),
            "review_status": self.review.status,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "annotation_set_id": self.annotation_set_id,
            "possession_id": self.possession_id,
            "source_video": self.source_video.to_dict(),
            "window": self.window.to_dict(),
            "coordinate_system": self.coordinate_system.to_dict(),
            "review": self.review.to_dict(),
            "annotations": [
                annotation.to_dict() for annotation in self.annotations
            ],
        }


def load_annotations(path: Path) -> BallAnnotationSet:
    annotation_path = path.resolve()

    if not annotation_path.is_file():
        raise FileNotFoundError(
            f"Ball annotation JSON not found: {annotation_path}"
        )

    try:
        with annotation_path.open("r", encoding="utf-8") as input_file:
            payload = json.load(
                input_file,
                object_pairs_hook=_reject_duplicate_json_keys,
            )
    except json.JSONDecodeError as error:
        raise AnnotationValidationError(
            f"Invalid JSON in ball annotations {annotation_path}: {error}"
        ) from error

    return BallAnnotationSet.from_mapping(payload)


def verify_source_video_contract(
    source_video: SourceVideo,
    repository_root: Path,
) -> dict[str, Any]:
    """Verify one declared source-video contract against repository bytes."""

    root = repository_root.resolve()

    if not root.is_dir():
        raise AnnotationValidationError(
            f"Repository root does not exist: {root}"
        )

    source_path = root.joinpath(*source_video.path.parts).resolve()

    try:
        source_path.relative_to(root)
    except ValueError as error:
        raise AnnotationValidationError(
            "Resolved source video path escapes the repository root"
        ) from error

    if not source_path.is_file():
        raise AnnotationValidationError(
            f"Source video does not exist: {source_path}"
        )

    source_hash = hashlib.sha256()

    with source_path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            source_hash.update(chunk)

    actual_sha256 = source_hash.hexdigest()

    if actual_sha256 != source_video.sha256:
        raise AnnotationValidationError(
            "Source video SHA-256 does not match declared metadata: "
            f"expected {source_video.sha256}, "
            f"received {actual_sha256}"
        )

    try:
        import cv2
    except ImportError as error:
        raise AnnotationValidationError(
            "OpenCV is required to verify source-video metadata"
        ) from error

    capture = cv2.VideoCapture(str(source_path))

    if not capture.isOpened():
        raise AnnotationValidationError(
            f"Could not open source video for verification: {source_path}"
        )

    try:
        raw_width_px = float(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        raw_height_px = float(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = float(capture.get(cv2.CAP_PROP_FPS))
        raw_frame_count = float(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    finally:
        capture.release()

    integer_metadata = {
        "width_px": raw_width_px,
        "height_px": raw_height_px,
        "frame_count": raw_frame_count,
    }
    invalid_integer_metadata = [
        label
        for label, value in integer_metadata.items()
        if not math.isfinite(value) or value <= 0.0 or not value.is_integer()
    ]

    if invalid_integer_metadata:
        raise AnnotationValidationError(
            "Source video backend returned invalid positive-integer metadata: "
            + ", ".join(
                f"{label}={integer_metadata[label]!r}"
                for label in invalid_integer_metadata
            )
        )

    if not math.isfinite(actual_fps) or actual_fps <= 0.0:
        raise AnnotationValidationError(
            "Source video backend returned invalid positive fps: "
            f"{actual_fps!r}"
        )

    actual_width_px = int(raw_width_px)
    actual_height_px = int(raw_height_px)
    actual_frame_count = int(raw_frame_count)

    declared = source_video
    mismatches = []

    if actual_width_px != declared.width_px:
        mismatches.append(
            f"width_px expected {declared.width_px}, received {actual_width_px}"
        )

    if actual_height_px != declared.height_px:
        mismatches.append(
            "height_px expected "
            f"{declared.height_px}, received {actual_height_px}"
        )

    if not math.isclose(
        actual_fps,
        declared.fps,
        rel_tol=0.0,
        abs_tol=1e-6,
    ):
        mismatches.append(
            f"fps expected {declared.fps}, received {actual_fps}"
        )

    if actual_frame_count != declared.frame_count:
        mismatches.append(
            "frame_count expected "
            f"{declared.frame_count}, received {actual_frame_count}"
        )

    if mismatches:
        raise AnnotationValidationError(
            "Source video metadata does not match declared metadata: "
            + "; ".join(mismatches)
        )

    return {
        "status": "verified_source_video",
        "path": declared.path.as_posix(),
        "sha256": actual_sha256,
        "width_px": actual_width_px,
        "height_px": actual_height_px,
        "fps": actual_fps,
        "frame_count": actual_frame_count,
    }


def verify_source_video(
    annotation_set: BallAnnotationSet,
    repository_root: Path,
) -> dict[str, Any]:
    """Verify an annotation set's declared source bytes and metadata."""

    return verify_source_video_contract(
        annotation_set.source_video,
        repository_root,
    )
