"""Build immutable, annotation-bound visual-review evidence.

This module deliberately publishes into a namespace separate from the neutral
pre-annotation assets.  The annotation JSON is the authoritative record; every
PNG and video created here is a derived human-annotation visualization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

import cv2
import numpy as np

from src.ball_tracking.annotations import (
    AnnotationValidationError,
    BallAnnotationSet,
    FrameAnnotation,
    load_annotations,
    verify_source_video,
)
from src.ball_tracking.prepare_annotation_review import (
    MAX_PLAYBACK_FPS,
    ReviewAssetPreparationError,
    _decode_window_sequentially,
    _load_existing_manifest,
    _validate_existing_owned_bundle,
    _verify_playback,
    _write_lossless_png,
    _write_slow_playback,
)


SCHEMA_VERSION = "ball_annotation_visual_review/v0.1"
EXPECTED_FRAME_COUNT = 25
ZOOM_HALF_SIZE_PX = 60
ZOOM_SOURCE_SIZE_PX = 2 * ZOOM_HALF_SIZE_PX + 1
ZOOM_FACTOR = 4
ZOOM_SIZE_PX = ZOOM_SOURCE_SIZE_PX * ZOOM_FACTOR
ZOOM_HEADER_HEIGHT_PX = 135
ZOOM_PANEL_WIDTH_PX = 2 * ZOOM_SIZE_PX
ZOOM_PANEL_HEIGHT_PX = ZOOM_HEADER_HEIGHT_PX + ZOOM_SIZE_PX
CONTACT_COLUMNS = 5
CONTACT_ROWS = 5
CONTACT_TILE_WIDTH_PX = 320
CONTACT_TILE_HEIGHT_PX = 220
CONTACT_HEADER_HEIGHT_PX = 80
TRAJECTORY_WIDTH_PX = 1600
TRAJECTORY_HEIGHT_PX = 1000

TOP_LEVEL_FIELDS = {
    "schema_version",
    "asset_bundle_type",
    "bundle_input",
    "annotation",
    "source_video",
    "neutral_bundle",
    "window",
    "safeguards",
    "visual_conventions",
    "generator",
    "assets",
}
ANNOTATION_FIELDS = {
    "annotation_set_id",
    "possession_id",
    "annotation_schema_version",
    "canonical_content_sha256",
    "annotation_file_sha256",
    "review_status",
    "watermark",
    "authoritative_record",
    "review_status_statement",
    "snapshot",
}
NEUTRAL_FIELDS = {
    "path",
    "manifest_sha256",
    "asset_bundle_type",
    "source_frame_count",
    "pre_annotation_file_sha256",
    "snapshot",
}
BUNDLE_INPUT_FIELDS = {
    "bundle_input_sha256",
    "canonical_annotation_sha256",
    "annotation_file_sha256",
    "neutral_manifest_sha256",
    "source_video_sha256",
    "render_schema_version",
    "generator_fingerprint_sha256",
}
GENERATOR_FIELDS = {"module", "fingerprint_sha256", "fingerprint"}
GENERATOR_FINGERPRINT_FIELDS = {
    "generator_module_sha256",
    "annotation_review_module_sha256",
    "annotations_module_sha256",
    "python_implementation",
    "python_version",
    "platform_system",
    "platform_machine",
    "numpy_version",
    "opencv_version",
    "opencv_build_sha256",
}
ASSET_GROUP_FIELDS = {
    "overlay_frames",
    "zoom_panels",
    "zoom_contact_sheet",
    "overlay_playback",
    "trajectory_diagnostics",
}
BASE_ASSET_FIELDS = {"path", "sha256", "byte_size"}
SNAPSHOT_FIELDS = BASE_ASSET_FIELDS | {"content"}
OVERLAY_FIELDS = BASE_ASSET_FIELDS | {
    "frame_index",
    "width_px",
    "height_px",
    "source_frame_sha256",
    "visualization_only",
}
ZOOM_FIELDS = BASE_ASSET_FIELDS | {
    "frame_index",
    "panel_type",
    "requested_source_crop_xyxy_px",
    "source_center_xy_px",
    "annotated_panel_center_xy_px",
    "zoom_factor",
    "raw_view_included",
}
CONTACT_FIELDS = BASE_ASSET_FIELDS | {
    "layout",
    "frame_count",
    "chronological",
    "purpose",
    "pixel_geometry_review_allowed",
    "aspect_preserving_letterbox",
    "visualization_only",
}
PLAYBACK_FIELDS = BASE_ASSET_FIELDS | {
    "codec_fourcc",
    "frame_count",
    "fps",
    "source_fps",
    "contains_trajectory_trail",
    "purpose",
    "pixel_geometry_review_allowed",
    "semantic_validation",
    "deterministic_reference_validation",
    "max_allowed_mean_absolute_error",
    "last_frame_index",
    "visualization_only",
}
TRAJECTORY_FIELDS = BASE_ASSET_FIELDS | {
    "geometry_point_count",
    "missing_geometry_count",
    "has_any_missing_geometry",
    "all_geometry_missing",
    "leading_missing_geometry_count",
    "internal_missing_geometry_count",
    "trailing_missing_geometry_count",
    "has_internal_geometry_discontinuities",
    "consecutive_segment_count",
    "coordinate_space",
    "camera_motion_compensated",
    "interpolation_used",
    "smoothing_used",
    "court_projection_used",
    "visualization_only",
}

SAFEGUARDS = {
    "visualization_only": True,
    "json_is_authoritative": True,
    "independent_adjudication_evidence_included": False,
    "detector_outputs_included": False,
    "tracker_outputs_included": False,
    "interpolation_used": False,
    "smoothing_used": False,
    "court_projection_used": False,
    "annotation_json_modified": False,
    "neutral_bundle_modified": False,
    "source_video_modified": False,
}
VISUAL_CONVENTIONS = {
    "center": "cyan_crosshair",
    "uncertainty": "yellow_circle_exact_source_pixel_radius",
    "fully_visible": "circle_glyph_and_OBSERVED_text",
    "partially_visible": "diamond_glyph_and_AMODAL_ESTIMATE_text",
    "no_geometry": "status_text_without_point_marker",
    "zoom": "raw_and_4x_nearest_neighbor_annotated_views",
    "trajectory": (
        "image_space_consecutive_geometry_only_with_gaps_no_interpolation"
    ),
    "playback": "current_frame_annotation_only_no_trajectory_trail",
}

CYAN = (255, 255, 0)
YELLOW = (0, 255, 255)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
AMBER = (0, 170, 255)
GRAY = (150, 150, 150)
PLAYBACK_MAX_MEAN_ABS_ERROR = 12.0
PLAYBACK_MATCH_WIDTH_PX = 160


class AnnotationVisualReviewError(RuntimeError):
    """Raised when immutable visual-review evidence cannot be trusted."""


@dataclass(frozen=True)
class NeutralBundleSnapshot:
    """Exact neutral-manifest bytes and the object parsed from those bytes."""

    manifest: dict[str, Any]
    content: bytes
    sha256: str


def canonical_annotation_sha256(annotation_set: BallAnnotationSet) -> str:
    """Return the semantic annotation digest used in bundle identity."""

    encoded = json.dumps(
        annotation_set.to_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def generator_fingerprint() -> dict[str, str]:
    """Bind rendering code plus the native runtime that controls its output."""

    module_dir = Path(__file__).resolve().parent
    fingerprint = {
        "generator_module_sha256": _sha256_file(Path(__file__).resolve()),
        "annotation_review_module_sha256": _sha256_file(
            module_dir / "prepare_annotation_review.py"
        ),
        "annotations_module_sha256": _sha256_file(
            module_dir / "annotations.py"
        ),
        "python_implementation": platform.python_implementation(),
        "python_version": sys.version,
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "numpy_version": np.__version__,
        "opencv_version": cv2.__version__,
        "opencv_build_sha256": _sha256_bytes(
            cv2.getBuildInformation().encode("utf-8")
        ),
    }
    _exact_fields(
        fingerprint,
        GENERATOR_FINGERPRINT_FIELDS,
        "generator fingerprint",
    )
    return fingerprint


def generator_fingerprint_sha256(
    fingerprint: Mapping[str, str],
) -> str:
    """Return the canonical digest of the closed generator fingerprint."""

    _exact_fields(
        fingerprint,
        GENERATOR_FINGERPRINT_FIELDS,
        "generator fingerprint",
    )
    encoded = json.dumps(
        dict(fingerprint),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def bundle_input_components(
    annotation_set: BallAnnotationSet,
    annotation_bytes: bytes,
    neutral_manifest_bytes: bytes,
    fingerprint: Mapping[str, str],
) -> dict[str, str]:
    """Return every immutable input that controls rendered bundle identity."""

    return {
        "canonical_annotation_sha256": canonical_annotation_sha256(
            annotation_set
        ),
        "annotation_file_sha256": _sha256_bytes(annotation_bytes),
        "neutral_manifest_sha256": _sha256_bytes(neutral_manifest_bytes),
        "source_video_sha256": annotation_set.source_video.sha256,
        "render_schema_version": SCHEMA_VERSION,
        "generator_fingerprint_sha256": generator_fingerprint_sha256(
            fingerprint
        ),
    }


def bundle_input_sha256(components: Mapping[str, str]) -> str:
    """Hash the closed combined input record used as the directory name."""

    encoded = json.dumps(
        dict(components),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _exact_fields(value: Any, expected: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AnnotationVisualReviewError(f"{label} must be a JSON object")
    actual = set(value)
    if actual != expected:
        raise AnnotationVisualReviewError(
            f"{label} fields are not closed; "
            f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
        )
    return value


def _parse_json_bytes_closed(content: bytes, label: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise AnnotationVisualReviewError(
                    f"duplicate JSON key in {label}: {key!r}"
                )
            result[key] = value
        return result

    try:
        payload = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AnnotationVisualReviewError(
            f"could not parse JSON bytes for {label}: {error}"
        ) from error
    if not isinstance(payload, dict):
        raise AnnotationVisualReviewError(f"{label} must be a JSON object")
    return payload


def _load_json_closed(path: Path) -> dict[str, Any]:
    try:
        content = path.read_bytes()
    except OSError as error:
        raise AnnotationVisualReviewError(
            f"could not read visual-review manifest: {path}: {error}"
        ) from error
    return _parse_json_bytes_closed(content, str(path))


def _portable_asset_path(bundle_dir: Path, raw_path: Any, label: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path or "\\" in raw_path:
        raise AnnotationVisualReviewError(
            f"{label}.path must be a portable relative path"
        )
    relative = PurePosixPath(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise AnnotationVisualReviewError(f"{label}.path escapes the bundle")
    resolved = bundle_dir.joinpath(*relative.parts).resolve()
    try:
        resolved.relative_to(bundle_dir.resolve())
    except ValueError as error:
        raise AnnotationVisualReviewError(f"{label}.path escapes the bundle") from error
    return resolved


def _asset_record(path: Path, bundle_dir: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(bundle_dir).as_posix(),
        "sha256": _sha256_file(path),
        "byte_size": path.stat().st_size,
    }


def _write_bytes(path: Path, content: bytes) -> None:
    path.write_bytes(content)
    if path.read_bytes() != content:
        raise AnnotationVisualReviewError(f"written bytes did not verify: {path}")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _write_bytes(
        path,
        (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
    )


def _watermark(review_status: str) -> str:
    return (
        f"{review_status.upper()} JSON STATUS - "
        "HUMAN ANNOTATION VISUALIZATION"
    )


def _review_status_statement(review_status: str) -> str:
    return (
        f"JSON status is {review_status}; this visualization makes no "
        "inter-rater or repeatability claim"
    )


def frame_visual_semantics(annotation: FrameAnnotation) -> dict[str, Any]:
    """Return text/glyph semantics without inventing any new ball state."""

    if annotation.annotation_status == "excluded":
        state = "EXCLUDED"
        glyph = "none"
    elif annotation.visibility == "not_visible":
        state = f"NO POINT - NOT VISIBLE ({annotation.absence_reason})"
        glyph = "none"
    elif annotation.visibility == "indeterminate":
        state = "NO POINT - INDETERMINATE"
        glyph = "none"
    elif annotation.geometry is None:
        state = "VISIBLE - NO DEFENSIBLE POINT"
        glyph = "none"
    elif annotation.visibility == "fully_visible":
        state = "OBSERVED"
        glyph = "circle"
    elif annotation.visibility == "partially_visible":
        state = "AMODAL ESTIMATE"
        glyph = "diamond"
    else:  # Defensive fallback; the strict schema normally makes this unreachable.
        state = str(annotation.visibility).upper()
        glyph = "none"
    return {
        "state_text": state,
        "glyph": glyph,
        "identity_text": annotation.game_ball_identity_certainty or "none",
        "eligibility_text": (
            "SCORABLE" if annotation.localization_eligible else "UNSCORED"
        ),
    }


def trajectory_segments(
    annotation_set: BallAnnotationSet,
) -> tuple[tuple[int, int], ...]:
    """Return only adjacent-frame geometry links; gaps are never bridged."""

    segments = []
    for left, right in zip(
        annotation_set.annotations,
        annotation_set.annotations[1:],
    ):
        if (
            left.geometry is not None
            and right.geometry is not None
            and right.frame_index == left.frame_index + 1
        ):
            segments.append((left.frame_index, right.frame_index))
    return tuple(segments)


def trajectory_missingness(
    annotation_set: BallAnnotationSet,
) -> dict[str, int | bool]:
    """Classify missing rows; all-missing has no edge or internal anchors."""

    has_geometry = [
        annotation.geometry is not None
        for annotation in annotation_set.annotations
    ]
    missing_count = has_geometry.count(False)
    geometry_positions = [
        index for index, present in enumerate(has_geometry) if present
    ]
    if not geometry_positions:
        leading_count = 0
        internal_count = 0
        trailing_count = 0
    else:
        first = geometry_positions[0]
        last = geometry_positions[-1]
        leading_count = first
        trailing_count = len(has_geometry) - last - 1
        internal_count = sum(not present for present in has_geometry[first : last + 1])
    return {
        "missing_geometry_count": missing_count,
        "has_any_missing_geometry": missing_count > 0,
        "all_geometry_missing": not geometry_positions,
        "leading_missing_geometry_count": leading_count,
        "internal_missing_geometry_count": internal_count,
        "trailing_missing_geometry_count": trailing_count,
        "has_internal_geometry_discontinuities": internal_count > 0,
    }


def _draw_point_marker(
    image: Any,
    center_xy: tuple[float, float],
    uncertainty_radius: float,
    visibility: str,
    *,
    coordinate_scale: float = 1.0,
) -> None:
    center_x = center_xy[0] * coordinate_scale
    center_y = center_xy[1] * coordinate_scale
    fixed_scale = 256
    center = (
        round(center_x * fixed_scale),
        round(center_y * fixed_scale),
    )
    half = 11
    cv2.line(
        image,
        (round((center_x - half) * fixed_scale), center[1]),
        (round((center_x + half) * fixed_scale), center[1]),
        CYAN,
        2,
        cv2.LINE_AA,
        shift=8,
    )
    cv2.line(
        image,
        (center[0], round((center_y - half) * fixed_scale)),
        (center[0], round((center_y + half) * fixed_scale)),
        CYAN,
        2,
        cv2.LINE_AA,
        shift=8,
    )
    cv2.circle(
        image,
        center,
        max(1, round(uncertainty_radius * coordinate_scale * fixed_scale)),
        YELLOW,
        1,
        cv2.LINE_AA,
        shift=8,
    )
    if visibility == "fully_visible":
        cv2.circle(
            image,
            center,
            7 * fixed_scale,
            CYAN,
            1,
            cv2.LINE_AA,
            shift=8,
        )
    else:
        radius = 8
        diamond = np.array(
            [
                [center_x, center_y - radius],
                [center_x + radius, center_y],
                [center_x, center_y + radius],
                [center_x - radius, center_y],
            ],
            dtype=np.float64,
        )
        diamond = np.round(diamond * fixed_scale).astype(np.int32)
        cv2.polylines(
            image,
            [diamond],
            True,
            CYAN,
            1,
            cv2.LINE_AA,
            shift=8,
        )


def _ascii(value: str) -> str:
    return value.encode("ascii", "replace").decode("ascii")


def render_overlay_frame(
    source_frame: Any,
    annotation: FrameAnnotation,
    review_status: str,
) -> Any:
    """Render one source-resolution derivative without mutating its input."""

    overlay = source_frame.copy()
    height, width = overlay.shape[:2]
    scale = max(0.35, min(0.75, width / 1920.0 * 0.75))
    line_height = max(16, round(30 * scale / 0.75))
    header_height = min(height, 3 * line_height + 10)
    footer_height = min(height, 2 * line_height + 10)
    cv2.rectangle(overlay, (0, 0), (width, header_height), BLACK, -1)
    watermark = _watermark(review_status)
    cv2.putText(
        overlay,
        _ascii(watermark),
        (8, line_height),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        WHITE,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        overlay,
        "ONE AUTHORITATIVE ANNOTATION SET - NO INTER-RATER OR REPEATABILITY CLAIM",
        (8, 3 * line_height),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        GRAY,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        overlay,
        "JSON AUTHORITATIVE - NOT MODEL OUTPUT",
        (8, 2 * line_height),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        AMBER,
        1,
        cv2.LINE_AA,
    )
    semantics = frame_visual_semantics(annotation)
    cv2.rectangle(
        overlay,
        (0, max(0, height - footer_height)),
        (width, height),
        BLACK,
        -1,
    )
    cv2.putText(
        overlay,
        _ascii(
            f"FRAME {annotation.frame_index} | {semantics['state_text']} | "
            f"IDENTITY {semantics['identity_text']} | "
            f"{semantics['eligibility_text']}"
        ),
        (8, max(line_height, height - footer_height + line_height)),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        WHITE,
        1,
        cv2.LINE_AA,
    )
    tags = ", ".join(annotation.difficulty_tags) or "none"
    cv2.putText(
        overlay,
        _ascii(f"TAGS: {tags}"),
        (8, min(height - 3, height - footer_height + 2 * line_height)),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        GRAY,
        1,
        cv2.LINE_AA,
    )
    if annotation.geometry is not None:
        _draw_point_marker(
            overlay,
            annotation.geometry.center_xy_px,
            annotation.geometry.uncertainty_radius_px,
            annotation.visibility or "partially_visible",
        )
    return overlay


def _padded_crop(
    source_frame: Any,
    center_xy: tuple[float, float],
) -> tuple[Any, tuple[int, int, int, int], tuple[float, float]]:
    center_floor_x = math.floor(center_xy[0])
    center_floor_y = math.floor(center_xy[1])
    origin_x = center_floor_x - ZOOM_HALF_SIZE_PX
    origin_y = center_floor_y - ZOOM_HALF_SIZE_PX
    requested = (
        origin_x,
        origin_y,
        origin_x + ZOOM_SOURCE_SIZE_PX,
        origin_y + ZOOM_SOURCE_SIZE_PX,
    )
    crop = np.zeros(
        (ZOOM_SOURCE_SIZE_PX, ZOOM_SOURCE_SIZE_PX, 3),
        dtype=source_frame.dtype,
    )
    source_height, source_width = source_frame.shape[:2]
    source_left = max(0, requested[0])
    source_top = max(0, requested[1])
    source_right = min(source_width, requested[2])
    source_bottom = min(source_height, requested[3])
    if source_left < source_right and source_top < source_bottom:
        destination_left = source_left - origin_x
        destination_top = source_top - origin_y
        crop[
            destination_top : destination_top + source_bottom - source_top,
            destination_left : destination_left + source_right - source_left,
        ] = source_frame[source_top:source_bottom, source_left:source_right]
    local_center = (center_xy[0] - origin_x, center_xy[1] - origin_y)
    return crop, requested, local_center


def zoom_panel_mapping(
    annotation: FrameAnnotation,
) -> dict[str, Any]:
    """Return the source-crop and panel-center mapping used by zoom review."""

    if annotation.geometry is None:
        return {
            "panel_type": "status",
            "requested_source_crop_xyxy_px": None,
            "source_center_xy_px": None,
            "annotated_panel_center_xy_px": None,
        }
    center_x, center_y = annotation.geometry.center_xy_px
    origin_x = math.floor(center_x) - ZOOM_HALF_SIZE_PX
    origin_y = math.floor(center_y) - ZOOM_HALF_SIZE_PX
    local_x = (center_x - origin_x) * ZOOM_FACTOR
    local_y = (center_y - origin_y) * ZOOM_FACTOR
    return {
        "panel_type": "geometry_zoom",
        "requested_source_crop_xyxy_px": [
            origin_x,
            origin_y,
            origin_x + ZOOM_SOURCE_SIZE_PX,
            origin_y + ZOOM_SOURCE_SIZE_PX,
        ],
        "source_center_xy_px": [center_x, center_y],
        "annotated_panel_center_xy_px": [
            ZOOM_SIZE_PX + local_x,
            ZOOM_HEADER_HEIGHT_PX + local_y,
        ],
    }


def render_zoom_panel(
    source_frame: Any,
    annotation: FrameAnnotation,
    review_status: str,
) -> tuple[Any, dict[str, Any]]:
    """Render raw-versus-annotated 4x zoom, or an explicit no-point panel."""

    panel = np.full(
        (ZOOM_PANEL_HEIGHT_PX, ZOOM_PANEL_WIDTH_PX, 3),
        20,
        dtype=np.uint8,
    )
    semantics = frame_visual_semantics(annotation)
    cv2.putText(
        panel,
        _ascii(f"{_watermark(review_status)} - JSON AUTHORITATIVE"),
        (12, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        WHITE,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        panel,
        "ONE AUTHORITATIVE ANNOTATION SET - NO INTER-RATER OR REPEATABILITY CLAIM",
        (12, 49),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        GRAY,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        panel,
        _ascii(
            f"FRAME {annotation.frame_index} | {semantics['state_text']} | "
            f"{semantics['eligibility_text']}"
        ),
        (12, 74),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        AMBER,
        1,
        cv2.LINE_AA,
    )
    tags = ", ".join(annotation.difficulty_tags) or "none"
    note = annotation.notes or "none"
    cv2.putText(
        panel,
        _ascii(f"TAGS: {tags} | NOTE: {note[:95]}"),
        (12, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.46,
        GRAY,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        panel,
        "RAW 4x NEAREST",
        (12, 127),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.38,
        WHITE,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        panel,
        "DERIVED ANNOTATION 4x",
        (ZOOM_SIZE_PX + 12, 127),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.38,
        WHITE,
        1,
        cv2.LINE_AA,
    )
    mapping = zoom_panel_mapping(annotation)
    if annotation.geometry is None:
        source_height, source_width = source_frame.shape[:2]
        scale = min(
            ZOOM_SIZE_PX / source_width,
            ZOOM_SIZE_PX / source_height,
        )
        resized = cv2.resize(
            source_frame,
            (max(1, round(source_width * scale)), max(1, round(source_height * scale))),
            interpolation=cv2.INTER_AREA,
        )
        x = (ZOOM_PANEL_WIDTH_PX - resized.shape[1]) // 2
        y = ZOOM_HEADER_HEIGHT_PX + (ZOOM_SIZE_PX - resized.shape[0]) // 2
        panel[y : y + resized.shape[0], x : x + resized.shape[1]] = resized
        cv2.putText(
            panel,
            "NO GEOMETRY - NO CROP OR POINT INVENTED",
            (12, ZOOM_PANEL_HEIGHT_PX - 16),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            AMBER,
            1,
            cv2.LINE_AA,
        )
        return panel, mapping

    crop, _requested, local_center = _padded_crop(
        source_frame,
        annotation.geometry.center_xy_px,
    )
    raw_zoom = cv2.resize(
        crop,
        (ZOOM_SIZE_PX, ZOOM_SIZE_PX),
        interpolation=cv2.INTER_NEAREST,
    )
    annotated_zoom = raw_zoom.copy()
    for offset in range(-ZOOM_HALF_SIZE_PX, ZOOM_HALF_SIZE_PX + 1, 5):
        position = round((offset + ZOOM_HALF_SIZE_PX) * ZOOM_FACTOR)
        cv2.line(
            annotated_zoom,
            (position, 0),
            (position, ZOOM_SIZE_PX - 1),
            (90, 90, 90),
            1,
        )
        cv2.line(
            annotated_zoom,
            (0, position),
            (ZOOM_SIZE_PX - 1, position),
            (90, 90, 90),
            1,
        )
    _draw_point_marker(
        annotated_zoom,
        local_center,
        annotation.geometry.uncertainty_radius_px,
        annotation.visibility or "partially_visible",
        coordinate_scale=ZOOM_FACTOR,
    )
    panel[
        ZOOM_HEADER_HEIGHT_PX : ZOOM_PANEL_HEIGHT_PX,
        0:ZOOM_SIZE_PX,
    ] = raw_zoom
    panel[
        ZOOM_HEADER_HEIGHT_PX : ZOOM_PANEL_HEIGHT_PX,
        ZOOM_SIZE_PX:ZOOM_PANEL_WIDTH_PX,
    ] = annotated_zoom
    return panel, mapping


def aspect_preserving_letterbox(
    image: Any,
    target_width_px: int,
    target_height_px: int,
) -> Any:
    """Resize without distortion and center on a dark context-only tile."""

    if target_width_px <= 0 or target_height_px <= 0:
        raise AnnotationVisualReviewError(
            "letterbox dimensions must be positive"
        )
    source_height, source_width = image.shape[:2]
    scale = min(
        target_width_px / source_width,
        target_height_px / source_height,
    )
    resized_width = max(1, round(source_width * scale))
    resized_height = max(1, round(source_height * scale))
    resized = cv2.resize(
        image,
        (resized_width, resized_height),
        interpolation=cv2.INTER_AREA,
    )
    tile = np.full(
        (target_height_px, target_width_px, 3),
        18,
        dtype=image.dtype,
    )
    x = (target_width_px - resized_width) // 2
    y = (target_height_px - resized_height) // 2
    tile[y : y + resized_height, x : x + resized_width] = resized
    return tile


def _build_contact_sheet(
    panels: list[Any],
    frame_indices: list[int],
    review_status: str,
) -> Any:
    if len(panels) != EXPECTED_FRAME_COUNT:
        raise AnnotationVisualReviewError("contact sheet requires exactly 25 panels")
    width = CONTACT_COLUMNS * CONTACT_TILE_WIDTH_PX
    height = CONTACT_HEADER_HEIGHT_PX + CONTACT_ROWS * CONTACT_TILE_HEIGHT_PX
    sheet = np.full((height, width, 3), 18, dtype=np.uint8)
    cv2.putText(
        sheet,
        _ascii(
            f"{_watermark(review_status)} - ZOOM CONTEXT REVIEW"
        ),
        (24, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        WHITE,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        sheet,
        (
            "CONTEXT ONLY - NOT FOR PIXEL GEOMETRY | JSON AUTHORITATIVE | "
            "ONE AUTHORITATIVE ANNOTATION SET - NO INTER-RATER OR REPEATABILITY CLAIM"
        ),
        (24, 62),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.54,
        AMBER,
        1,
        cv2.LINE_AA,
    )
    for index, (panel, frame_index) in enumerate(
        zip(panels, frame_indices, strict=True)
    ):
        row, column = divmod(index, CONTACT_COLUMNS)
        x = column * CONTACT_TILE_WIDTH_PX
        y = CONTACT_HEADER_HEIGHT_PX + row * CONTACT_TILE_HEIGHT_PX
        tile = aspect_preserving_letterbox(
            panel,
            CONTACT_TILE_WIDTH_PX,
            CONTACT_TILE_HEIGHT_PX,
        )
        sheet[y : y + CONTACT_TILE_HEIGHT_PX, x : x + CONTACT_TILE_WIDTH_PX] = tile
        cv2.rectangle(sheet, (x, y), (x + 319, y + 219), WHITE, 1)
        cv2.rectangle(sheet, (x, y), (x + 112, y + 24), BLACK, -1)
        cv2.putText(
            sheet,
            f"FRAME {frame_index}",
            (x + 5, y + 18),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            WHITE,
            1,
            cv2.LINE_AA,
        )
    return sheet


def _build_trajectory_diagnostics(annotation_set: BallAnnotationSet) -> Any:
    canvas = np.full(
        (TRAJECTORY_HEIGHT_PX, TRAJECTORY_WIDTH_PX, 3),
        18,
        dtype=np.uint8,
    )
    cv2.putText(
        canvas,
        _ascii(_watermark(annotation_set.review.status)),
        (40, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        WHITE,
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        "JSON AUTHORITATIVE - IMAGE-SPACE DIAGNOSTIC - NOT MODEL OUTPUT",
        (40, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        WHITE,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        "ONE AUTHORITATIVE ANNOTATION SET - NO INTER-RATER OR REPEATABILITY CLAIM",
        (40, 102),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        GRAY,
        1,
        cv2.LINE_AA,
    )
    warning = (
        "CAMERA MOTION UNCOMPENSATED | NO SMOOTHING | NO INTERPOLATION | "
        "NOT A COURT/FLOOR TRAJECTORY"
    )
    cv2.putText(
        canvas,
        warning,
        (40, 129),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.57,
        AMBER,
        1,
        cv2.LINE_AA,
    )
    plot_left, plot_top, plot_right, plot_bottom = 70, 155, 1130, 720
    cv2.rectangle(
        canvas,
        (plot_left, plot_top),
        (plot_right, plot_bottom),
        GRAY,
        1,
    )
    source = annotation_set.source_video

    def map_point(center: tuple[float, float]) -> tuple[int, int]:
        return (
            round(plot_left + center[0] / source.width_px * (plot_right - plot_left)),
            round(plot_top + center[1] / source.height_px * (plot_bottom - plot_top)),
        )

    by_frame = annotation_set.annotation_by_frame()
    segments = trajectory_segments(annotation_set)
    for left_index, right_index in segments:
        left_geometry = by_frame[left_index].geometry
        right_geometry = by_frame[right_index].geometry
        assert left_geometry is not None and right_geometry is not None
        cv2.line(
            canvas,
            map_point(left_geometry.center_xy_px),
            map_point(right_geometry.center_xy_px),
            (255, 100, 255),
            2,
            cv2.LINE_AA,
        )

    geometry_annotations = [
        annotation
        for annotation in annotation_set.annotations
        if annotation.geometry is not None
    ]
    uncertainty_scale = min(
        (plot_right - plot_left) / source.width_px,
        (plot_bottom - plot_top) / source.height_px,
    )
    for annotation in geometry_annotations:
        geometry = annotation.geometry
        assert geometry is not None
        point = map_point(geometry.center_xy_px)
        radius = max(1, round(geometry.uncertainty_radius_px * uncertainty_scale))
        cv2.circle(canvas, point, radius, YELLOW, 1, cv2.LINE_AA)
        if annotation.visibility == "fully_visible":
            cv2.circle(canvas, point, 4, CYAN, 1, cv2.LINE_AA)
        else:
            diamond = np.array(
                [[point[0], point[1] - 5], [point[0] + 5, point[1]],
                 [point[0], point[1] + 5], [point[0] - 5, point[1]]],
                dtype=np.int32,
            )
            cv2.polylines(canvas, [diamond], True, CYAN, 1, cv2.LINE_AA)

    start = annotation_set.window.start_frame_index
    end = annotation_set.window.end_frame_index
    graph_left, graph_top, graph_right, graph_bottom = 70, 790, 1130, 945
    cv2.rectangle(
        canvas,
        (graph_left, graph_top),
        (graph_right, graph_bottom),
        GRAY,
        1,
    )
    step_values: dict[int, float] = {}
    uncertainty_values: dict[int, float] = {}
    for annotation in geometry_annotations:
        geometry = annotation.geometry
        assert geometry is not None
        uncertainty_values[annotation.frame_index] = geometry.uncertainty_radius_px
    for left_index, right_index in segments:
        left_geometry = by_frame[left_index].geometry
        right_geometry = by_frame[right_index].geometry
        assert left_geometry is not None and right_geometry is not None
        step_values[right_index] = math.dist(
            left_geometry.center_xy_px,
            right_geometry.center_xy_px,
        )
    maximum = max([1.0, *step_values.values(), *uncertainty_values.values()])

    def graph_x(frame_index: int) -> int:
        return round(
            graph_left
            + (frame_index - start) / max(1, end - start) * (graph_right - graph_left)
        )

    def graph_y(value: float) -> int:
        return round(graph_bottom - value / maximum * (graph_bottom - graph_top))

    for frame_index, value in uncertainty_values.items():
        cv2.circle(canvas, (graph_x(frame_index), graph_y(value)), 3, YELLOW, -1)
    for frame_index, value in step_values.items():
        cv2.circle(
            canvas,
            (graph_x(frame_index), graph_y(value)),
            3,
            (255, 100, 255),
            -1,
        )
    summary_x = 1170
    lines = [
        f"Frames: {start}-{end}",
        f"Geometry points: {len(geometry_annotations)}",
        f"Consecutive segments: {len(segments)}",
        "Cyan: annotated centers",
        "Yellow: uncertainty",
        "Magenta: step distance",
        "Gaps are left disconnected",
        "Coordinates: x right, y down",
    ]
    for index, line in enumerate(lines):
        cv2.putText(
            canvas,
            line,
            (summary_x, 140 + index * 34),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            WHITE if index < 3 else GRAY,
            1,
            cv2.LINE_AA,
        )
    return canvas


def _validate_complete_annotations(annotation_set: BallAnnotationSet) -> None:
    if annotation_set.window.frame_count != EXPECTED_FRAME_COUNT:
        raise AnnotationVisualReviewError(
            "visual review requires exactly 25 annotation rows"
        )
    unlabeled = [
        annotation.frame_index
        for annotation in annotation_set.annotations
        if annotation.annotation_status == "unlabeled"
    ]
    if unlabeled:
        raise AnnotationVisualReviewError(
            f"visual review requires a complete set; unlabeled frames={unlabeled}"
        )


def _validate_neutral_bundle(
    neutral_dir: Path,
    repository_root: Path,
    annotation_set: BallAnnotationSet,
) -> NeutralBundleSnapshot:
    allowed_root = (
        repository_root
        / "data"
        / "outputs"
        / "ball_tracking"
        / "annotation_review"
    ).resolve()
    try:
        relative = neutral_dir.relative_to(allowed_root)
    except ValueError as error:
        raise AnnotationVisualReviewError(
            f"neutral bundle must be below {allowed_root}"
        ) from error
    if relative == Path(".") or neutral_dir.is_symlink():
        raise AnnotationVisualReviewError(
            "neutral bundle must be a regular strict descendant bundle"
        )
    manifest_path = neutral_dir / "manifest.json"
    try:
        manifest_bytes = manifest_path.read_bytes()
        parsed_manifest = _parse_json_bytes_closed(
            manifest_bytes,
            str(manifest_path),
        )
        _validate_existing_owned_bundle(neutral_dir, annotation_set)
        validated_manifest = _load_existing_manifest(manifest_path)
        after_validation_bytes = manifest_path.read_bytes()
    except (OSError, ReviewAssetPreparationError) as error:
        raise AnnotationVisualReviewError(
            f"neutral bundle validation failed: {error}"
        ) from error
    if after_validation_bytes != manifest_bytes:
        raise AnnotationVisualReviewError(
            "neutral manifest changed while it was being validated"
        )
    if validated_manifest != parsed_manifest:
        raise AnnotationVisualReviewError(
            "neutral manifest parsed content changed during validation"
        )
    return NeutralBundleSnapshot(
        manifest=parsed_manifest,
        content=manifest_bytes,
        sha256=_sha256_bytes(manifest_bytes),
    )


def _decode_and_compare_neutral_frames(
    source_path: Path,
    annotation_set: BallAnnotationSet,
    neutral_dir: Path,
    neutral_snapshot: NeutralBundleSnapshot,
) -> tuple[Any, ...]:
    """Prove every neutral PNG is the verified sequential source decode."""

    decoded_frames = _decode_window_sequentially(source_path, annotation_set)
    neutral_records = neutral_snapshot.manifest["assets"]["source_frames"]
    if len(decoded_frames) != len(neutral_records):
        raise AnnotationVisualReviewError(
            "neutral/source frame counts differ after sequential decode"
        )
    for decoded, record, annotation in zip(
        decoded_frames,
        neutral_records,
        annotation_set.annotations,
        strict=True,
    ):
        neutral_path = neutral_dir.joinpath(
            *PurePosixPath(record["path"]).parts
        )
        neutral_frame = cv2.imread(str(neutral_path), cv2.IMREAD_COLOR)
        if neutral_frame is None or not np.array_equal(neutral_frame, decoded):
            raise AnnotationVisualReviewError(
                "neutral frame does not pixel-match verified sequential "
                f"source decode: frame {annotation.frame_index}"
            )
    return tuple(decoded_frames)


def _source_path(
    repository_root: Path,
    annotation_set: BallAnnotationSet,
) -> Path:
    path = repository_root.joinpath(*annotation_set.source_video.path.parts).resolve()
    try:
        path.relative_to(repository_root)
    except ValueError as error:
        raise AnnotationVisualReviewError(
            "source path escapes repository root"
        ) from error
    return path


def _output_path(
    repository_root: Path,
    annotation_set: BallAnnotationSet,
    digest: str,
) -> Path:
    window_name = (
        f"frames_{annotation_set.window.start_frame_index:04d}_"
        f"{annotation_set.window.end_frame_index:04d}"
    )
    output_path = (
        repository_root
        / "data"
        / "outputs"
        / "ball_tracking"
        / "annotation_visual_review"
        / annotation_set.possession_id
        / window_name
        / digest
    )
    validate_output_location(repository_root, output_path)
    return output_path


def _has_windows_reparse_point(path: Path) -> bool:
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & 0x400)


def validate_output_location(
    repository_root: Path,
    output_path: Path,
) -> None:
    """Enforce lexical/resolved containment without links or junctions."""

    root = repository_root.resolve()
    dedicated_root = (
        root
        / "data"
        / "outputs"
        / "ball_tracking"
        / "annotation_visual_review"
    )
    lexical_output = output_path.absolute()
    lexical_root = dedicated_root.absolute()
    try:
        lexical_relative = lexical_output.relative_to(lexical_root)
    except ValueError as error:
        raise AnnotationVisualReviewError(
            "output path is outside the dedicated annotation_visual_review root"
        ) from error
    if lexical_relative == Path("."):
        raise AnnotationVisualReviewError(
            "output path must be a strict descendant of the dedicated root"
        )

    try:
        root_relative = lexical_output.relative_to(root)
    except ValueError as error:
        raise AnnotationVisualReviewError(
            "output path is lexically outside the repository"
        ) from error
    current = root
    for part in root_relative.parts:
        current = current / part
        if current.is_symlink() or (
            current.exists() and _has_windows_reparse_point(current)
        ):
            raise AnnotationVisualReviewError(
                "output path contains a symlink or Windows reparse/junction "
                f"ancestor: {current}"
            )
        if current.exists() and not current.is_dir():
            raise AnnotationVisualReviewError(
                f"output path ancestor is not a directory: {current}"
            )

    resolved_root = dedicated_root.resolve()
    resolved_output = lexical_output.resolve()
    try:
        resolved_relative = resolved_output.relative_to(resolved_root)
    except ValueError as error:
        raise AnnotationVisualReviewError(
            "resolved output path escapes the dedicated output root"
        ) from error
    if resolved_relative == Path("."):
        raise AnnotationVisualReviewError(
            "resolved output path must be a strict descendant"
        )


def _expected_zoom_mapping(annotation: FrameAnnotation) -> dict[str, Any]:
    return zoom_panel_mapping(annotation)


def _validate_asset(
    bundle_dir: Path,
    record: Mapping[str, Any],
    expected_fields: set[str],
    expected_path: str,
    label: str,
) -> Path:
    _exact_fields(record, expected_fields, label)
    if record["path"] != expected_path:
        raise AnnotationVisualReviewError(
            f"{label}.path expected {expected_path!r}, received {record['path']!r}"
        )
    path = _portable_asset_path(bundle_dir, record["path"], label)
    if path.is_symlink() or not path.is_file():
        raise AnnotationVisualReviewError(f"{label} is not a regular file")
    if record["byte_size"] != path.stat().st_size:
        raise AnnotationVisualReviewError(f"{label} byte size does not match")
    if record["sha256"] != _sha256_file(path):
        raise AnnotationVisualReviewError(f"{label} SHA-256 does not match")
    return path


def _playback_match_view(frame: Any) -> Any:
    height, width = frame.shape[:2]
    if width <= PLAYBACK_MATCH_WIDTH_PX:
        return frame
    target_height = max(1, round(height * PLAYBACK_MATCH_WIDTH_PX / width))
    return cv2.resize(
        frame,
        (PLAYBACK_MATCH_WIDTH_PX, target_height),
        interpolation=cv2.INTER_AREA,
    )


def _mean_absolute_pixel_error(left: Any, right: Any) -> float:
    return float(
        np.mean(
            np.abs(
                left.astype(np.int16) - right.astype(np.int16)
            )
        )
    )


def _validate_playback_semantic_order(
    playback_path: Path,
    expected_overlays: Sequence[Any],
    expected_frame_indices: Sequence[int],
    width_px: int,
    height_px: int,
    expected_fps: float,
    expected_codec_fourcc: str,
) -> None:
    """Prove each lossy playback frame matches its ordered overlay source."""

    _verify_playback(
        playback_path,
        len(expected_overlays),
        width_px,
        height_px,
        expected_fps,
    )
    expected_match_views = [
        _playback_match_view(frame) for frame in expected_overlays
    ]
    capture = cv2.VideoCapture(str(playback_path))
    if not capture.isOpened():
        capture.release()
        raise AnnotationVisualReviewError(
            "could not decode overlay playback for semantic validation"
        )
    decoded_frames = []
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            decoded_frames.append(frame)
    finally:
        capture.release()
    if len(decoded_frames) != len(expected_overlays):
        raise AnnotationVisualReviewError(
            "playback semantic validation decoded an unexpected frame count"
        )

    final_position = len(expected_overlays) - 1
    for position, (decoded, expected) in enumerate(
        zip(decoded_frames, expected_overlays, strict=True)
    ):
        decoded_match = _playback_match_view(decoded)
        candidate_errors = [
            _mean_absolute_pixel_error(decoded_match, candidate)
            for candidate in expected_match_views
        ]
        closest_position = int(np.argmin(candidate_errors))
        expected_error = _mean_absolute_pixel_error(decoded, expected)
        if closest_position != position:
            if position == final_position:
                raise AnnotationVisualReviewError(
                    "final playback frame does not match the final ordered "
                    f"overlay frame {expected_frame_indices[position]}"
                )
            raise AnnotationVisualReviewError(
                "playback semantic frame order does not match overlays: "
                f"position {position} is closest to position {closest_position}"
            )
        if expected_error > PLAYBACK_MAX_MEAN_ABS_ERROR:
            label = (
                "final playback frame"
                if position == final_position
                else f"playback frame at position {position}"
            )
            raise AnnotationVisualReviewError(
                f"{label} exceeds codec tolerance: mean absolute error "
                f"{expected_error:.3f} > {PLAYBACK_MAX_MEAN_ABS_ERROR:.3f}"
            )

    with tempfile.TemporaryDirectory(
        prefix="ball-annotation-playback-reference-"
    ) as temporary_directory:
        reference_path = Path(temporary_directory) / "reference.mp4"
        reference_codec = _write_slow_playback(
            reference_path,
            list(expected_overlays),
            width_px,
            height_px,
            expected_fps,
        )
        if reference_codec != expected_codec_fourcc:
            raise AnnotationVisualReviewError(
                "playback codec does not match deterministic reference codec: "
                f"recorded {expected_codec_fourcc}, reference {reference_codec}"
            )
        if reference_path.read_bytes() != playback_path.read_bytes():
            raise AnnotationVisualReviewError(
                "playback does not match the deterministic reference encode "
                "under the fingerprinted runtime"
            )


def validate_visual_review_bundle(
    bundle_dir: Path,
    annotation_set: BallAnnotationSet,
    annotation_bytes: bytes,
    source_verification: dict[str, Any],
    neutral_dir: Path,
    repository_root: Path,
    neutral_snapshot: NeutralBundleSnapshot,
    verified_source_frames: Sequence[Any],
    bundle_components: dict[str, str],
    digest: str,
    expected_generator_fingerprint: Mapping[str, str],
) -> dict[str, Any]:
    """Validate a complete owned bundle before reuse or publication."""

    manifest_path = bundle_dir / "manifest.json"
    if bundle_dir.is_symlink() or not manifest_path.is_file():
        raise AnnotationVisualReviewError(
            "existing content-addressed output is not a complete owned bundle"
        )
    manifest = _load_json_closed(manifest_path)
    _exact_fields(manifest, TOP_LEVEL_FIELDS, "manifest")
    if (
        manifest["schema_version"] != SCHEMA_VERSION
        or manifest["asset_bundle_type"] != "ball_annotation_visual_review"
    ):
        raise AnnotationVisualReviewError("visual-review bundle schema is not owned")

    bundle_input = _exact_fields(
        manifest["bundle_input"],
        BUNDLE_INPUT_FIELDS,
        "bundle_input",
    )
    expected_bundle_input = {
        "bundle_input_sha256": digest,
        **bundle_components,
    }
    if bundle_input != expected_bundle_input:
        raise AnnotationVisualReviewError(
            "combined bundle-input binding does not match"
        )

    annotation_record = _exact_fields(
        manifest["annotation"], ANNOTATION_FIELDS, "annotation"
    )
    expected_watermark = _watermark(annotation_set.review.status)
    expected_annotation = {
        "annotation_set_id": annotation_set.annotation_set_id,
        "possession_id": annotation_set.possession_id,
        "annotation_schema_version": annotation_set.schema_version,
        "canonical_content_sha256": bundle_components[
            "canonical_annotation_sha256"
        ],
        "annotation_file_sha256": _sha256_bytes(annotation_bytes),
        "review_status": annotation_set.review.status,
        "watermark": expected_watermark,
        "authoritative_record": "annotation_snapshot.json",
        "review_status_statement": _review_status_statement(
            annotation_set.review.status
        ),
    }
    for field, expected in expected_annotation.items():
        if annotation_record[field] != expected:
            raise AnnotationVisualReviewError(
                f"annotation manifest binding does not match: {field}"
            )
    snapshot = annotation_record["snapshot"]
    snapshot_path = _validate_asset(
        bundle_dir,
        snapshot,
        SNAPSHOT_FIELDS,
        "annotation_snapshot.json",
        "annotation.snapshot",
    )
    if snapshot["content"] != "exact_input_annotation_bytes":
        raise AnnotationVisualReviewError("annotation snapshot content is not exact")
    if snapshot_path.read_bytes() != annotation_bytes:
        raise AnnotationVisualReviewError(
            "annotation snapshot bytes do not match input"
        )

    if manifest["source_video"] != source_verification:
        raise AnnotationVisualReviewError("source-video binding does not match")
    neutral_manifest = neutral_snapshot.manifest
    neutral = _exact_fields(manifest["neutral_bundle"], NEUTRAL_FIELDS, "neutral")
    neutral_expected = {
        "path": neutral_dir.relative_to(repository_root).as_posix(),
        "manifest_sha256": neutral_snapshot.sha256,
        "asset_bundle_type": "ball_annotation_review",
        "source_frame_count": EXPECTED_FRAME_COUNT,
        "pre_annotation_file_sha256": neutral_manifest["annotation_set"][
            "annotation_content_sha256"
        ],
    }
    for field, expected in neutral_expected.items():
        if neutral[field] != expected:
            raise AnnotationVisualReviewError(
                f"neutral bundle binding does not match: {field}"
            )
    neutral_snapshot_record = neutral["snapshot"]
    neutral_snapshot_path = _validate_asset(
        bundle_dir,
        neutral_snapshot_record,
        SNAPSHOT_FIELDS,
        "neutral_manifest_snapshot.json",
        "neutral.snapshot",
    )
    if neutral_snapshot_record["content"] != "exact_neutral_manifest_bytes":
        raise AnnotationVisualReviewError(
            "neutral manifest snapshot content is not exact"
        )
    if neutral_snapshot_path.read_bytes() != neutral_snapshot.content:
        raise AnnotationVisualReviewError(
            "neutral manifest snapshot bytes do not match input"
        )
    expected_window = {
        **annotation_set.window.to_dict(),
        "frame_count": EXPECTED_FRAME_COUNT,
    }
    if manifest["window"] != expected_window:
        raise AnnotationVisualReviewError("window binding does not match")
    if manifest["safeguards"] != SAFEGUARDS:
        raise AnnotationVisualReviewError("visual-review safeguards do not match")
    if manifest["visual_conventions"] != VISUAL_CONVENTIONS:
        raise AnnotationVisualReviewError("visual conventions do not match")
    generator = _exact_fields(manifest["generator"], GENERATOR_FIELDS, "generator")
    if generator["module"] != "src.ball_tracking.prepare_annotation_visual_review":
        raise AnnotationVisualReviewError("generator module is not recognized")
    recorded_fingerprint = _exact_fields(
        generator["fingerprint"],
        GENERATOR_FINGERPRINT_FIELDS,
        "generator.fingerprint",
    )
    if recorded_fingerprint != expected_generator_fingerprint:
        raise AnnotationVisualReviewError(
            "generator fingerprint does not match current code and runtime"
        )
    expected_fingerprint_sha256 = generator_fingerprint_sha256(
        expected_generator_fingerprint
    )
    if generator["fingerprint_sha256"] != expected_fingerprint_sha256:
        raise AnnotationVisualReviewError(
            "generator fingerprint SHA-256 does not match"
        )

    assets = _exact_fields(manifest["assets"], ASSET_GROUP_FIELDS, "assets")
    overlays = assets["overlay_frames"]
    zooms = assets["zoom_panels"]
    if not isinstance(overlays, list) or len(overlays) != EXPECTED_FRAME_COUNT:
        raise AnnotationVisualReviewError("overlay frame list is incomplete")
    if not isinstance(zooms, list) or len(zooms) != EXPECTED_FRAME_COUNT:
        raise AnnotationVisualReviewError("zoom panel list is incomplete")
    if len(verified_source_frames) != EXPECTED_FRAME_COUNT:
        raise AnnotationVisualReviewError(
            "verified source frame list is incomplete"
        )

    expected_entries = {
        "manifest.json",
        "annotation_snapshot.json",
        "neutral_manifest_snapshot.json",
        "overlay_frames",
        "zoom_panels",
        "annotation_zoom_contact_sheet.png",
        "annotation_overlay_slow.mp4",
        "trajectory_diagnostics.png",
    }
    neutral_frames = neutral_manifest["assets"]["source_frames"]
    expected_overlay_frames = []
    expected_zoom_panels = []
    for index, annotation in enumerate(annotation_set.annotations):
        frame_index = annotation.frame_index
        overlay_path = f"overlay_frames/frame_{frame_index:06d}.png"
        zoom_path = f"zoom_panels/frame_{frame_index:06d}.png"
        expected_entries.update({overlay_path, zoom_path})
        overlay = overlays[index]
        overlay_file = _validate_asset(
            bundle_dir,
            overlay,
            OVERLAY_FIELDS,
            overlay_path,
            f"overlay_frames[{index}]",
        )
        expected_overlay = {
            "frame_index": frame_index,
            "width_px": annotation_set.source_video.width_px,
            "height_px": annotation_set.source_video.height_px,
            "source_frame_sha256": neutral_frames[index]["sha256"],
            "visualization_only": True,
        }
        for field, expected in expected_overlay.items():
            if overlay[field] != expected:
                raise AnnotationVisualReviewError(
                    f"overlay_frames[{index}] metadata mismatch: {field}"
                )
        decoded_overlay = cv2.imread(str(overlay_file), cv2.IMREAD_COLOR)
        if decoded_overlay is None or decoded_overlay.shape[:2] != (
            annotation_set.source_video.height_px,
            annotation_set.source_video.width_px,
        ):
            raise AnnotationVisualReviewError("overlay dimensions do not match source")
        expected_overlay_pixels = render_overlay_frame(
            verified_source_frames[index],
            annotation,
            annotation_set.review.status,
        )
        if not np.array_equal(decoded_overlay, expected_overlay_pixels):
            raise AnnotationVisualReviewError(
                "overlay does not match the deterministic generator output: "
                f"frame {frame_index}"
            )
        expected_overlay_frames.append(expected_overlay_pixels)

        zoom = zooms[index]
        zoom_file = _validate_asset(
            bundle_dir,
            zoom,
            ZOOM_FIELDS,
            zoom_path,
            f"zoom_panels[{index}]",
        )
        expected_mapping = _expected_zoom_mapping(annotation)
        for field, expected in {
            "frame_index": frame_index,
            **expected_mapping,
            "zoom_factor": ZOOM_FACTOR,
            "raw_view_included": True,
        }.items():
            if zoom[field] != expected:
                raise AnnotationVisualReviewError(
                    f"zoom_panels[{index}] metadata mismatch: {field}"
                )
        decoded_zoom = cv2.imread(str(zoom_file), cv2.IMREAD_COLOR)
        if decoded_zoom is None or decoded_zoom.shape[:2] != (
            ZOOM_PANEL_HEIGHT_PX,
            ZOOM_PANEL_WIDTH_PX,
        ):
            raise AnnotationVisualReviewError("zoom panel dimensions are invalid")
        expected_zoom_pixels, rerendered_mapping = render_zoom_panel(
            verified_source_frames[index],
            annotation,
            annotation_set.review.status,
        )
        if rerendered_mapping != expected_mapping:
            raise AnnotationVisualReviewError(
                f"zoom mapping rerender mismatch: frame {frame_index}"
            )
        if not np.array_equal(decoded_zoom, expected_zoom_pixels):
            raise AnnotationVisualReviewError(
                "zoom panel does not match the deterministic generator output: "
                f"frame {frame_index}"
            )
        expected_zoom_panels.append(expected_zoom_pixels)

    contact = assets["zoom_contact_sheet"]
    contact_path = _validate_asset(
        bundle_dir,
        contact,
        CONTACT_FIELDS,
        "annotation_zoom_contact_sheet.png",
        "zoom_contact_sheet",
    )
    for field, expected in {
        "layout": "5x5",
        "frame_count": EXPECTED_FRAME_COUNT,
        "chronological": True,
        "purpose": "context_only_not_for_pixel_geometry",
        "pixel_geometry_review_allowed": False,
        "aspect_preserving_letterbox": True,
        "visualization_only": True,
    }.items():
        if contact[field] != expected:
            raise AnnotationVisualReviewError(f"contact metadata mismatch: {field}")
    decoded_contact = cv2.imread(str(contact_path), cv2.IMREAD_COLOR)
    if decoded_contact is None or decoded_contact.shape[:2] != (
        CONTACT_HEADER_HEIGHT_PX + CONTACT_ROWS * CONTACT_TILE_HEIGHT_PX,
        CONTACT_COLUMNS * CONTACT_TILE_WIDTH_PX,
    ):
        raise AnnotationVisualReviewError("contact sheet dimensions are invalid")
    expected_contact = _build_contact_sheet(
        expected_zoom_panels,
        [annotation.frame_index for annotation in annotation_set.annotations],
        annotation_set.review.status,
    )
    if not np.array_equal(decoded_contact, expected_contact):
        raise AnnotationVisualReviewError(
            "contact sheet does not match the deterministic generator output"
        )

    playback = assets["overlay_playback"]
    playback_path = _validate_asset(
        bundle_dir,
        playback,
        PLAYBACK_FIELDS,
        "annotation_overlay_slow.mp4",
        "overlay_playback",
    )
    playback_fps = min(MAX_PLAYBACK_FPS, annotation_set.source_video.fps)
    for field, expected in {
        "frame_count": EXPECTED_FRAME_COUNT,
        "fps": playback_fps,
        "source_fps": annotation_set.source_video.fps,
        "contains_trajectory_trail": False,
        "purpose": "context_only_ordered_annotation_playback",
        "pixel_geometry_review_allowed": False,
        "semantic_validation": (
            "decoded_frames_match_ordered_overlay_pngs_with_codec_tolerance"
        ),
        "deterministic_reference_validation": (
            "exact_mp4_bytes_regenerated_under_fingerprinted_runtime"
        ),
        "max_allowed_mean_absolute_error": PLAYBACK_MAX_MEAN_ABS_ERROR,
        "last_frame_index": annotation_set.window.end_frame_index,
        "visualization_only": True,
    }.items():
        if playback[field] != expected:
            raise AnnotationVisualReviewError(f"playback metadata mismatch: {field}")
    if not isinstance(playback["codec_fourcc"], str) or not playback["codec_fourcc"]:
        raise AnnotationVisualReviewError("playback codec is invalid")
    _validate_playback_semantic_order(
        playback_path,
        expected_overlay_frames,
        [annotation.frame_index for annotation in annotation_set.annotations],
        annotation_set.source_video.width_px,
        annotation_set.source_video.height_px,
        playback_fps,
        playback["codec_fourcc"],
    )

    trajectory = assets["trajectory_diagnostics"]
    trajectory_path = _validate_asset(
        bundle_dir,
        trajectory,
        TRAJECTORY_FIELDS,
        "trajectory_diagnostics.png",
        "trajectory_diagnostics",
    )
    geometry_count = sum(
        annotation.geometry is not None for annotation in annotation_set.annotations
    )
    segment_count = len(trajectory_segments(annotation_set))
    missingness = trajectory_missingness(annotation_set)
    for field, expected in {
        "geometry_point_count": geometry_count,
        **missingness,
        "consecutive_segment_count": segment_count,
        "coordinate_space": "original_image_pixels_x_right_y_down",
        "camera_motion_compensated": False,
        "interpolation_used": False,
        "smoothing_used": False,
        "court_projection_used": False,
        "visualization_only": True,
    }.items():
        if trajectory[field] != expected:
            raise AnnotationVisualReviewError(
                f"trajectory metadata mismatch: {field}"
            )
    decoded_trajectory = cv2.imread(str(trajectory_path), cv2.IMREAD_COLOR)
    if decoded_trajectory is None or decoded_trajectory.shape[:2] != (
        TRAJECTORY_HEIGHT_PX,
        TRAJECTORY_WIDTH_PX,
    ):
        raise AnnotationVisualReviewError("trajectory dimensions are invalid")
    expected_trajectory = _build_trajectory_diagnostics(annotation_set)
    if not np.array_equal(decoded_trajectory, expected_trajectory):
        raise AnnotationVisualReviewError(
            "trajectory diagnostic does not match the deterministic generator output"
        )

    actual_entries = set()
    for path in bundle_dir.rglob("*"):
        if path.is_symlink():
            raise AnnotationVisualReviewError("visual-review bundle contains a symlink")
        actual_entries.add(path.relative_to(bundle_dir).as_posix())
    if actual_entries != expected_entries:
        raise AnnotationVisualReviewError(
            "visual-review bundle structure is not closed; "
            f"missing={sorted(expected_entries - actual_entries)}, "
            f"extra={sorted(actual_entries - expected_entries)}"
        )
    return manifest


def _ensure_inputs_unchanged(
    annotation_path: Path,
    annotation_bytes: bytes,
    annotation_set: BallAnnotationSet,
    source_path: Path,
    neutral_dir: Path,
    repository_root: Path,
    neutral_snapshot: NeutralBundleSnapshot,
    expected_generator_fingerprint: Mapping[str, str],
) -> None:
    if annotation_path.read_bytes() != annotation_bytes:
        raise AnnotationVisualReviewError(
            "annotation JSON changed during generation; nothing was published"
        )
    if load_annotations(annotation_path).to_dict() != annotation_set.to_dict():
        raise AnnotationVisualReviewError(
            "annotation content changed during generation; nothing was published"
        )
    if _sha256_file(source_path) != annotation_set.source_video.sha256:
        raise AnnotationVisualReviewError(
            "source video changed during generation; nothing was published"
        )
    current_neutral = _validate_neutral_bundle(
        neutral_dir,
        repository_root,
        annotation_set,
    )
    if current_neutral.content != neutral_snapshot.content:
        raise AnnotationVisualReviewError(
            "neutral bundle changed during generation; nothing was published"
        )
    if generator_fingerprint() != expected_generator_fingerprint:
        raise AnnotationVisualReviewError(
            "visual-review generator code or runtime changed during generation; "
            "nothing was published"
        )


def _build_bundle(
    staging_dir: Path,
    annotation_bytes: bytes,
    annotation_set: BallAnnotationSet,
    source_verification: dict[str, Any],
    neutral_dir: Path,
    neutral_snapshot: NeutralBundleSnapshot,
    verified_source_frames: tuple[Any, ...],
    repository_root: Path,
    bundle_components: dict[str, str],
    digest: str,
    expected_generator_fingerprint: Mapping[str, str],
) -> dict[str, Any]:
    overlay_dir = staging_dir / "overlay_frames"
    zoom_dir = staging_dir / "zoom_panels"
    overlay_dir.mkdir()
    zoom_dir.mkdir()
    snapshot_path = staging_dir / "annotation_snapshot.json"
    neutral_snapshot_path = staging_dir / "neutral_manifest_snapshot.json"
    _write_bytes(snapshot_path, annotation_bytes)
    _write_bytes(neutral_snapshot_path, neutral_snapshot.content)

    overlay_records = []
    zoom_records = []
    overlay_frames = []
    zoom_panels = []
    frame_indices = []
    neutral_manifest = neutral_snapshot.manifest
    neutral_frames = neutral_manifest["assets"]["source_frames"]
    for index, (annotation, source_frame) in enumerate(
        zip(
            annotation_set.annotations,
            verified_source_frames,
            strict=True,
        )
    ):
        frame_index = annotation.frame_index
        frame_indices.append(frame_index)
        source_record = neutral_frames[index]
        overlay = render_overlay_frame(
            source_frame,
            annotation,
            annotation_set.review.status,
        )
        overlay_path = overlay_dir / f"frame_{frame_index:06d}.png"
        _write_lossless_png(overlay_path, overlay)
        overlay_record = _asset_record(overlay_path, staging_dir)
        overlay_record.update(
            {
                "frame_index": frame_index,
                "width_px": source_frame.shape[1],
                "height_px": source_frame.shape[0],
                "source_frame_sha256": source_record["sha256"],
                "visualization_only": True,
            }
        )
        overlay_records.append(overlay_record)
        overlay_frames.append(overlay)

        panel, mapping = render_zoom_panel(
            source_frame,
            annotation,
            annotation_set.review.status,
        )
        zoom_path = zoom_dir / f"frame_{frame_index:06d}.png"
        _write_lossless_png(zoom_path, panel)
        zoom_record = _asset_record(zoom_path, staging_dir)
        zoom_record.update(
            {
                "frame_index": frame_index,
                **mapping,
                "zoom_factor": ZOOM_FACTOR,
                "raw_view_included": True,
            }
        )
        zoom_records.append(zoom_record)
        zoom_panels.append(panel)

    contact_path = staging_dir / "annotation_zoom_contact_sheet.png"
    _write_lossless_png(
        contact_path,
        _build_contact_sheet(
            zoom_panels,
            frame_indices,
            annotation_set.review.status,
        ),
    )
    playback_path = staging_dir / "annotation_overlay_slow.mp4"
    playback_fps = min(MAX_PLAYBACK_FPS, annotation_set.source_video.fps)
    playback_codec = _write_slow_playback(
        playback_path,
        overlay_frames,
        annotation_set.source_video.width_px,
        annotation_set.source_video.height_px,
        playback_fps,
    )
    trajectory_path = staging_dir / "trajectory_diagnostics.png"
    _write_lossless_png(
        trajectory_path,
        _build_trajectory_diagnostics(annotation_set),
    )

    snapshot_record = _asset_record(snapshot_path, staging_dir)
    snapshot_record["content"] = "exact_input_annotation_bytes"
    neutral_snapshot_record = _asset_record(
        neutral_snapshot_path,
        staging_dir,
    )
    neutral_snapshot_record["content"] = "exact_neutral_manifest_bytes"
    contact_record = _asset_record(contact_path, staging_dir)
    contact_record.update(
        {
            "layout": "5x5",
            "frame_count": EXPECTED_FRAME_COUNT,
            "chronological": True,
            "purpose": "context_only_not_for_pixel_geometry",
            "pixel_geometry_review_allowed": False,
            "aspect_preserving_letterbox": True,
            "visualization_only": True,
        }
    )
    playback_record = _asset_record(playback_path, staging_dir)
    playback_record.update(
        {
            "codec_fourcc": playback_codec,
            "frame_count": EXPECTED_FRAME_COUNT,
            "fps": playback_fps,
            "source_fps": annotation_set.source_video.fps,
            "contains_trajectory_trail": False,
            "purpose": "context_only_ordered_annotation_playback",
            "pixel_geometry_review_allowed": False,
            "semantic_validation": (
                "decoded_frames_match_ordered_overlay_pngs_with_codec_tolerance"
            ),
            "deterministic_reference_validation": (
                "exact_mp4_bytes_regenerated_under_fingerprinted_runtime"
            ),
            "max_allowed_mean_absolute_error": PLAYBACK_MAX_MEAN_ABS_ERROR,
            "last_frame_index": annotation_set.window.end_frame_index,
            "visualization_only": True,
        }
    )
    geometry_count = sum(
        annotation.geometry is not None for annotation in annotation_set.annotations
    )
    segment_count = len(trajectory_segments(annotation_set))
    missingness = trajectory_missingness(annotation_set)
    trajectory_record = _asset_record(trajectory_path, staging_dir)
    trajectory_record.update(
        {
            "geometry_point_count": geometry_count,
            **missingness,
            "consecutive_segment_count": segment_count,
            "coordinate_space": "original_image_pixels_x_right_y_down",
            "camera_motion_compensated": False,
            "interpolation_used": False,
            "smoothing_used": False,
            "court_projection_used": False,
            "visualization_only": True,
        }
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "asset_bundle_type": "ball_annotation_visual_review",
        "bundle_input": {
            "bundle_input_sha256": digest,
            **bundle_components,
        },
        "annotation": {
            "annotation_set_id": annotation_set.annotation_set_id,
            "possession_id": annotation_set.possession_id,
            "annotation_schema_version": annotation_set.schema_version,
            "canonical_content_sha256": bundle_components[
                "canonical_annotation_sha256"
            ],
            "annotation_file_sha256": _sha256_bytes(annotation_bytes),
            "review_status": annotation_set.review.status,
            "watermark": _watermark(annotation_set.review.status),
            "authoritative_record": "annotation_snapshot.json",
            "review_status_statement": _review_status_statement(
                annotation_set.review.status
            ),
            "snapshot": snapshot_record,
        },
        "source_video": source_verification,
        "neutral_bundle": {
            "path": neutral_dir.relative_to(repository_root).as_posix(),
            "manifest_sha256": neutral_snapshot.sha256,
            "asset_bundle_type": "ball_annotation_review",
            "source_frame_count": EXPECTED_FRAME_COUNT,
            "pre_annotation_file_sha256": neutral_manifest["annotation_set"][
                "annotation_content_sha256"
            ],
            "snapshot": neutral_snapshot_record,
        },
        "window": {
            **annotation_set.window.to_dict(),
            "frame_count": EXPECTED_FRAME_COUNT,
        },
        "safeguards": SAFEGUARDS,
        "visual_conventions": VISUAL_CONVENTIONS,
        "generator": {
            "module": "src.ball_tracking.prepare_annotation_visual_review",
            "fingerprint_sha256": generator_fingerprint_sha256(
                expected_generator_fingerprint
            ),
            "fingerprint": dict(expected_generator_fingerprint),
        },
        "assets": {
            "overlay_frames": overlay_records,
            "zoom_panels": zoom_records,
            "zoom_contact_sheet": contact_record,
            "overlay_playback": playback_record,
            "trajectory_diagnostics": trajectory_record,
        },
    }
    _write_json(staging_dir / "manifest.json", manifest)
    return manifest


def _prepare_annotation_visual_review(
    annotation_path: Path,
    repository_root: Path,
    neutral_bundle_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    """Build or safely reuse one immutable content-addressed review bundle."""

    annotation_path = annotation_path.resolve()
    repository_root = repository_root.resolve()
    neutral_bundle_dir = neutral_bundle_dir.resolve()
    if not repository_root.is_dir():
        raise AnnotationVisualReviewError(
            f"repository root does not exist: {repository_root}"
        )
    annotation_bytes = annotation_path.read_bytes()
    annotation_set = load_annotations(annotation_path)
    if annotation_path.read_bytes() != annotation_bytes:
        raise AnnotationVisualReviewError("annotation JSON changed while loading")
    _validate_complete_annotations(annotation_set)
    source_verification = verify_source_video(annotation_set, repository_root)
    source_path = _source_path(repository_root, annotation_set)
    neutral_snapshot = _validate_neutral_bundle(
        neutral_bundle_dir,
        repository_root,
        annotation_set,
    )
    verified_source_frames = _decode_and_compare_neutral_frames(
        source_path,
        annotation_set,
        neutral_bundle_dir,
        neutral_snapshot,
    )
    expected_generator_fingerprint = generator_fingerprint()
    bundle_components = bundle_input_components(
        annotation_set,
        annotation_bytes,
        neutral_snapshot.content,
        expected_generator_fingerprint,
    )
    digest = bundle_input_sha256(bundle_components)
    output_dir = _output_path(repository_root, annotation_set, digest)

    if output_dir.exists():
        manifest = validate_visual_review_bundle(
            output_dir,
            annotation_set,
            annotation_bytes,
            source_verification,
            neutral_bundle_dir,
            repository_root,
            neutral_snapshot,
            verified_source_frames,
            bundle_components,
            digest,
            expected_generator_fingerprint,
        )
        _ensure_inputs_unchanged(
            annotation_path,
            annotation_bytes,
            annotation_set,
            source_path,
            neutral_bundle_dir,
            repository_root,
            neutral_snapshot,
            expected_generator_fingerprint,
        )
        return output_dir, manifest

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    validate_output_location(repository_root, output_dir)
    staging_dir = Path(
        tempfile.mkdtemp(
            prefix=f".{digest}.staging-",
            dir=output_dir.parent,
        )
    )
    try:
        _build_bundle(
            staging_dir,
            annotation_bytes,
            annotation_set,
            source_verification,
            neutral_bundle_dir,
            neutral_snapshot,
            verified_source_frames,
            repository_root,
            bundle_components,
            digest,
            expected_generator_fingerprint,
        )
        manifest = validate_visual_review_bundle(
            staging_dir,
            annotation_set,
            annotation_bytes,
            source_verification,
            neutral_bundle_dir,
            repository_root,
            neutral_snapshot,
            verified_source_frames,
            bundle_components,
            digest,
            expected_generator_fingerprint,
        )
        _ensure_inputs_unchanged(
            annotation_path,
            annotation_bytes,
            annotation_set,
            source_path,
            neutral_bundle_dir,
            repository_root,
            neutral_snapshot,
            expected_generator_fingerprint,
        )
        validate_output_location(repository_root, output_dir)
        if output_dir.exists():
            reused = validate_visual_review_bundle(
                output_dir,
                annotation_set,
                annotation_bytes,
                source_verification,
                neutral_bundle_dir,
                repository_root,
                neutral_snapshot,
                verified_source_frames,
                bundle_components,
                digest,
                expected_generator_fingerprint,
            )
            return output_dir, reused
        try:
            staging_dir.rename(output_dir)
        except OSError:
            if output_dir.exists():
                reused = validate_visual_review_bundle(
                    output_dir,
                    annotation_set,
                    annotation_bytes,
                    source_verification,
                    neutral_bundle_dir,
                    repository_root,
                    neutral_snapshot,
                    verified_source_frames,
                    bundle_components,
                    digest,
                    expected_generator_fingerprint,
                )
                return output_dir, reused
            raise
        return output_dir, manifest
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)


def prepare_annotation_visual_review(
    annotation_path: Path,
    repository_root: Path,
    neutral_bundle_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    """Build or safely reuse one immutable content-addressed review bundle."""

    try:
        return _prepare_annotation_visual_review(
            annotation_path,
            repository_root,
            neutral_bundle_dir,
        )
    except ReviewAssetPreparationError as error:
        raise AnnotationVisualReviewError(
            f"review asset operation failed: {error}"
        ) from error


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build an immutable post-annotation visual-review package from a "
            "complete strict annotation set and its neutral review bundle."
        )
    )
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--neutral-bundle", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    try:
        output_dir, manifest = prepare_annotation_visual_review(
            args.annotations,
            args.repository_root,
            args.neutral_bundle,
        )
    except (
        AnnotationValidationError,
        AnnotationVisualReviewError,
        FileNotFoundError,
        OSError,
    ) as error:
        raise SystemExit(f"Ball annotation visual-review error: {error}") from error
    print("Ball annotation visual-review package is ready.")
    print(f"Annotation: {manifest['annotation']['annotation_set_id']}")
    print(f"Review status: {manifest['annotation']['review_status']}")
    print(f"Output directory: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
