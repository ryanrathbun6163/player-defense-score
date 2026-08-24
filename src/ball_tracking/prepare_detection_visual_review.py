"""Build immutable candidate-versus-truth detector review evidence.

The package renders two explicitly configured descriptive grid points.  It
never chooses a winner or changes evaluator semantics.  Every accepted
candidate is shown, and all candidate roles are reconciled against the exact
``evaluate_detections`` frame result that supplied the scoring report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

import cv2
import numpy as np

from .annotations import (
    BallAnnotationSet,
    FrameAnnotation,
    SourceVideo,
    load_annotations,
    verify_source_video_contract,
)
from .detections import (
    BallDetection,
    BallDetectionRun,
    DetectionFrame,
    load_detection_run,
)
from .evaluation import evaluate_detections
from .detector_experiments import DetectorExperiment, load_detector_experiment
from .prepare_annotation_review import (
    MAX_PLAYBACK_FPS,
    ReviewAssetPreparationError,
    _decode_window_sequentially,
    _write_lossless_png,
    _write_slow_playback,
)
from .prepare_annotation_visual_review import (
    AnnotationVisualReviewError,
    _draw_point_marker,
    aspect_preserving_letterbox,
)
from .run_detector_experiment import (
    DetectorExperimentRunnerError,
    GitSnapshot,
    _validate_git_snapshot,
    inspect_git_repository,
    is_git_ignored,
)
from .score_detector_experiment import (
    DetectorExperimentScoringError,
    load_scoring_report,
    reject_unsafe_repository_path,
    verify_tracked_file_at_head,
)


SCHEMA_VERSION = "ball_detection_visual_review/v0.1"
PLAN_SCHEMA_VERSION = "ball_detection_visual_review_plan/v0.1"
PLAN_ROOT_PARTS = ("configs", "ball_tracking", "reviews")
OUTPUT_ROOT_PARTS = (
    "data",
    "outputs",
    "ball_tracking",
    "detection_review",
)
EXPECTED_PILOT_COUNT = 3
EXPECTED_FRAME_COUNT = 25
EXPECTED_VIEW_COUNT = 2
ZOOM_HALF_SIZE_PX = 60
ZOOM_SOURCE_SIZE_PX = 2 * ZOOM_HALF_SIZE_PX + 1
ZOOM_FACTOR = 4
ZOOM_PANEL_HEADER_PX = 130
ZOOM_PANEL_WIDTH_PX = 3 * ZOOM_SOURCE_SIZE_PX * ZOOM_FACTOR
ZOOM_PANEL_HEIGHT_PX = (
    ZOOM_PANEL_HEADER_PX + ZOOM_SOURCE_SIZE_PX * ZOOM_FACTOR
)
COMPARISON_PANEL_WIDTH_PX = 960
COMPARISON_PANEL_HEIGHT_PX = 540
COMPARISON_HEADER_PX = 110
COMPARISON_WIDTH_PX = 2 * COMPARISON_PANEL_WIDTH_PX
COMPARISON_HEIGHT_PX = COMPARISON_HEADER_PX + COMPARISON_PANEL_HEIGHT_PX
CONTACT_COLUMNS = 5
CONTACT_ROWS = 5
CONTACT_TILE_WIDTH_PX = 384
CONTACT_TILE_HEIGHT_PX = 230
CONTACT_HEADER_PX = 110
HEATMAP_WIDTH_PX = 1800
HEATMAP_HEIGHT_PX = 760

PLAN_TOP_LEVEL_FIELDS = frozenset(
    {
        "schema_version",
        "review_id",
        "experiment_id",
        "scoring_report_path",
        "purpose",
        "views",
        "render_scope",
        "interpretation",
    }
)
PLAN_VIEW_FIELDS = frozenset(
    {
        "view_id",
        "confidence_threshold",
        "localization_radius_px",
        "role",
    }
)
RENDER_SCOPE_FIELDS = frozenset(
    {
        "selection_purpose",
        "all_authorized_pilots",
        "all_frames_including_final",
        "full_resolution_overlays",
        "synchronized_comparison",
        "truth_region_zoom",
        "category_contact_sheets",
        "metric_heatmaps",
    }
)
INTERPRETATION_FIELDS = frozenset(
    {
        "selected_operating_point",
        "quality_gate",
        "model_winner_claimed",
        "generalization_claimed",
        "holdout_evidence_included",
        "decision_statement",
    }
)
BUNDLE_TOP_LEVEL_FIELDS = frozenset(
    {
        "schema_version",
        "asset_bundle_type",
        "bundle_input",
        "review_plan",
        "scoring_report",
        "safeguards",
        "visual_conventions",
        "generator",
        "aggregate_grid",
        "pilots",
        "assets",
    }
)
ASSET_BASE_FIELDS = frozenset({"path", "sha256", "byte_size"})

EXPECTED_RENDER_SCOPE = {
    "selection_purpose": "protocol_adjudication",
    "all_authorized_pilots": True,
    "all_frames_including_final": True,
    "full_resolution_overlays": True,
    "synchronized_comparison": True,
    "truth_region_zoom": True,
    "category_contact_sheets": True,
    "metric_heatmaps": True,
}
SAFEGUARDS = {
    "visualization_only": True,
    "scoring_report_is_authoritative": True,
    "annotation_json_is_authoritative": True,
    "all_threshold_accepted_candidates_rendered": True,
    "below_threshold_candidates_rendered": False,
    "nms_used": False,
    "top_one_selection_used": False,
    "deduplication_used": False,
    "interpolation_used": False,
    "smoothing_used": False,
    "court_filter_used": False,
    "selected_operating_point": None,
    "quality_gate": None,
    "holdout_evidence_included": False,
    "standalone_validation_scope": (
        "closed_structure_and_recorded_hashes_not_semantic_regeneration"
    ),
    "exact_reuse_validation": (
        "full_deterministic_regeneration_and_tree_hash_comparison"
    ),
}
VISUAL_CONVENTIONS = {
    "truth_center": "cyan_crosshair",
    "annotation_uncertainty": "yellow_circle_exact_source_pixel_radius",
    "localization_radius": "blue_circle_raw_source_pixel_radius",
    "true_positive": "green_box_circle_and_TP_text",
    "ordinary_false_positive": "red_box_x_and_FP_text",
    "duplicate_false_positive": "magenta_box_double_circle_and_DUP_FP_text",
    "not_visible_false_alarm": "orange_box_triangle_and_NV_FP_text",
    "unscored_prediction": "gray_box_question_mark_and_UNSCORED_text",
    "ambiguous_unscored_annotation": (
        "orange_diamond_and_AMBIGUOUS_UNSCORED_text_no_localization_radius"
    ),
    "draw_order": "nonmatches_then_match_then_truth",
    "full_resolution_pngs": "authoritative_visual_evidence",
    "comparison_contact_sheets_and_mp4": "context_only",
}

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (150, 150, 150)
CYAN = (255, 255, 0)
YELLOW = (0, 255, 255)
BLUE = (255, 100, 0)
GREEN = (0, 220, 0)
RED = (0, 0, 255)
MAGENTA = (255, 0, 255)
ORANGE = (0, 165, 255)

IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
WINDOWS_RESERVED_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}

CANDIDATE_ROLE_COLORS = {
    "true_positive": GREEN,
    "ordinary_false_positive": RED,
    "duplicate_false_positive": MAGENTA,
    "not_visible_false_alarm": ORANGE,
    "unscored_prediction": GRAY,
}
CANDIDATE_ROLE_LABELS = {
    "true_positive": "TP",
    "ordinary_false_positive": "FP",
    "duplicate_false_positive": "DUP FP",
    "not_visible_false_alarm": "NV FP",
    "unscored_prediction": "UNSCORED",
}


class DetectionVisualReviewError(RuntimeError):
    """Raised when candidate-versus-truth evidence cannot be trusted."""


@dataclass(frozen=True)
class DetectionReviewView:
    view_id: str
    confidence_threshold: float
    localization_radius_px: float
    role: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "view_id": self.view_id,
            "confidence_threshold": self.confidence_threshold,
            "localization_radius_px": self.localization_radius_px,
            "role": self.role,
        }


@dataclass(frozen=True)
class DetectionReviewPlan:
    schema_version: str
    review_id: str
    experiment_id: str
    scoring_report_path: PurePosixPath
    purpose: str
    views: tuple[DetectionReviewView, ...]
    render_scope: Mapping[str, Any]
    interpretation: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "review_id": self.review_id,
            "experiment_id": self.experiment_id,
            "scoring_report_path": self.scoring_report_path.as_posix(),
            "purpose": self.purpose,
            "views": [view.to_dict() for view in self.views],
            "render_scope": dict(self.render_scope),
            "interpretation": dict(self.interpretation),
        }


@dataclass(frozen=True)
class PreparedVisualPilot:
    pilot_input: Mapping[str, Any]
    annotation_path: Path
    annotation_bytes: bytes
    annotations: BallAnnotationSet
    detection_path: Path
    detection_bytes: bytes
    detections: BallDetectionRun
    reports_by_view_id: Mapping[str, Mapping[str, Any]]
    source_path: Path
    source_bytes_sha256: str


@dataclass(frozen=True)
class DetectionVisualReviewSummary:
    head: str
    output_dir: Path
    reused_existing: bool
    pilot_count: int
    view_count: int
    rendered_frame_count: int


PlanLoader = Callable[[Path], DetectionReviewPlan]
ExperimentLoader = Callable[[Path], DetectorExperiment]
ScoringReportLoader = Callable[[Path], dict[str, Any]]
GitInspector = Callable[[Path, PurePosixPath], GitSnapshot]
TrackedFileVerifier = Callable[[Path, PurePosixPath], None]
IgnoreChecker = Callable[[Path, PurePosixPath], bool]
AnnotationLoader = Callable[[Path], BallAnnotationSet]
DetectionLoader = Callable[[Path], BallDetectionRun]
SourceVerifier = Callable[[SourceVideo, Path], dict[str, Any]]
WindowDecoder = Callable[[Path, BallAnnotationSet], Sequence[Any]]
PlaybackWriter = Callable[[Path, list[Any], int, int, float], str]


@dataclass(frozen=True)
class VisualReviewDependencies:
    load_plan: PlanLoader
    load_experiment: ExperimentLoader
    load_scoring_report: ScoringReportLoader
    inspect_git: GitInspector
    verify_tracked_file: TrackedFileVerifier
    is_git_ignored: IgnoreChecker
    load_annotation: AnnotationLoader
    load_detection: DetectionLoader
    verify_source: SourceVerifier
    decode_window: WindowDecoder
    write_playback: PlaybackWriter


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise DetectionVisualReviewError(
                f"duplicate JSON key in detection review input: {key!r}"
            )

        result[key] = value

    return result


def _exact_fields(
    value: Any,
    expected: frozenset[str],
    label: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DetectionVisualReviewError(f"{label} must be a JSON object")

    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)

    if missing or extra:
        raise DetectionVisualReviewError(
            f"{label} fields are not closed; missing={missing}, extra={extra}"
        )

    return value


def _require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DetectionVisualReviewError(f"{label} must be a non-empty string")

    return value


def _require_identifier(value: Any, label: str) -> str:
    result = _require_string(value, label)

    if (
        len(result) > 96
        or not IDENTIFIER_PATTERN.fullmatch(result)
        or result.casefold() in WINDOWS_RESERVED_NAMES
    ):
        raise DetectionVisualReviewError(
            f"{label} must be a portable lowercase underscore identifier"
        )

    return result


def _require_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DetectionVisualReviewError(f"{label} must be numeric")

    result = float(value)

    if not math.isfinite(result):
        raise DetectionVisualReviewError(f"{label} must be finite")

    return result


def _portable_json_path(value: Any, label: str) -> PurePosixPath:
    raw = _require_string(value, label)

    if "\\" in raw:
        raise DetectionVisualReviewError(
            f"{label} must use portable forward slashes"
        )

    path = PurePosixPath(raw)

    if (
        path.is_absolute()
        or not path.parts
        or "." in path.parts
        or ".." in path.parts
        or path.as_posix() != raw
        or path.suffix != ".json"
    ):
        raise DetectionVisualReviewError(
            f"{label} must be a normalized repository-relative JSON path"
        )

    for component in path.parts:
        device_basename = component.split(".", 1)[0].rstrip(" .").casefold()

        if (
            ":" in component
            or component.endswith((".", " "))
            or device_basename in WINDOWS_RESERVED_NAMES
        ):
            raise DetectionVisualReviewError(
                f"{label} contains a Windows-unsafe path component "
                f"{component!r}"
            )

    return path


def load_detection_review_plan(path: Path) -> DetectionReviewPlan:
    plan_path = path.resolve()

    if not plan_path.is_file():
        raise FileNotFoundError(
            f"Detection visual-review plan not found: {plan_path}"
        )

    try:
        with plan_path.open("r", encoding="utf-8") as input_file:
            payload = json.load(
                input_file,
                object_pairs_hook=_reject_duplicate_keys,
            )
    except json.JSONDecodeError as error:
        raise DetectionVisualReviewError(
            f"Invalid JSON in detection visual-review plan {plan_path}: {error}"
        ) from error

    plan = _exact_fields(payload, PLAN_TOP_LEVEL_FIELDS, "review plan")

    if plan["schema_version"] != PLAN_SCHEMA_VERSION:
        raise DetectionVisualReviewError(
            f"review plan schema_version must be {PLAN_SCHEMA_VERSION!r}"
        )

    if plan["purpose"] != "descriptive_protocol_pilot_candidate_comparison":
        raise DetectionVisualReviewError(
            "review plan purpose is not the descriptive pilot comparison"
        )

    raw_views = plan["views"]

    if not isinstance(raw_views, list) or len(raw_views) != EXPECTED_VIEW_COUNT:
        raise DetectionVisualReviewError(
            "review plan must contain exactly 2 synchronized views"
        )

    views = []

    for index, raw_view in enumerate(raw_views):
        label = f"views[{index}]"
        view = _exact_fields(raw_view, PLAN_VIEW_FIELDS, label)
        threshold = _require_number(
            view["confidence_threshold"],
            f"{label}.confidence_threshold",
        )
        radius = _require_number(
            view["localization_radius_px"],
            f"{label}.localization_radius_px",
        )

        if not 0.0 <= threshold <= 1.0 or radius <= 0.0:
            raise DetectionVisualReviewError(
                f"{label} threshold/radius are outside valid ranges"
            )

        views.append(
            DetectionReviewView(
                view_id=_require_identifier(
                    view["view_id"],
                    f"{label}.view_id",
                ),
                confidence_threshold=threshold,
                localization_radius_px=radius,
                role=_require_string(view["role"], f"{label}.role"),
            )
        )

    if len({view.view_id for view in views}) != len(views):
        raise DetectionVisualReviewError("review plan view_id values must be unique")

    if len(
        {
            (view.confidence_threshold, view.localization_radius_px)
            for view in views
        }
    ) != len(views):
        raise DetectionVisualReviewError(
            "review plan views must use distinct threshold/radius cells"
        )

    render_scope = dict(
        _exact_fields(
            plan["render_scope"],
            RENDER_SCOPE_FIELDS,
            "render_scope",
        )
    )

    if render_scope != EXPECTED_RENDER_SCOPE:
        raise DetectionVisualReviewError(
            "render_scope must request every required pilot-review asset"
        )

    interpretation = dict(
        _exact_fields(
            plan["interpretation"],
            INTERPRETATION_FIELDS,
            "interpretation",
        )
    )

    if (
        interpretation["selected_operating_point"] is not None
        or interpretation["quality_gate"] is not None
        or interpretation["model_winner_claimed"] is not False
        or interpretation["generalization_claimed"] is not False
        or interpretation["holdout_evidence_included"] is not False
    ):
        raise DetectionVisualReviewError(
            "review plan interpretation must preserve descriptive-only status"
        )

    _require_string(
        interpretation["decision_statement"],
        "interpretation.decision_statement",
    )
    return DetectionReviewPlan(
        schema_version=PLAN_SCHEMA_VERSION,
        review_id=_require_identifier(plan["review_id"], "review_id"),
        experiment_id=_require_identifier(
            plan["experiment_id"],
            "experiment_id",
        ),
        scoring_report_path=_portable_json_path(
            plan["scoring_report_path"],
            "scoring_report_path",
        ),
        purpose=plan["purpose"],
        views=tuple(views),
        render_scope=render_scope,
        interpretation=interpretation,
    )


def generator_fingerprint() -> dict[str, str]:
    """Bind exact renderer/evaluator helpers and native image runtime."""

    module_root = Path(__file__).resolve().parent
    files = {
        "generator_module_sha256": Path(__file__).resolve(),
        "scoring_module_sha256": module_root / "score_detector_experiment.py",
        "evaluation_module_sha256": module_root / "evaluation.py",
        "annotations_module_sha256": module_root / "annotations.py",
        "detections_module_sha256": module_root / "detections.py",
        "annotation_review_module_sha256": (
            module_root / "prepare_annotation_review.py"
        ),
        "annotation_visual_module_sha256": (
            module_root / "prepare_annotation_visual_review.py"
        ),
    }
    fingerprint = {key: _sha256_file(path) for key, path in files.items()}
    fingerprint.update(
        {
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
    )
    return fingerprint


def candidate_display_roles(
    annotation: FrameAnnotation,
    detection_frame: DetectionFrame,
    frame_result: Mapping[str, Any],
    *,
    confidence_threshold: float,
    localization_radius_px: float,
) -> tuple[dict[str, Any], ...]:
    """Join accepted raw candidates to evaluator-authoritative frame roles."""

    if detection_frame.detections is None:
        raise DetectionVisualReviewError(
            f"Frame {detection_frame.frame_index} has no completed detections"
        )

    accepted = [
        detection
        for detection in detection_frame.detections
        if detection.confidence >= confidence_threshold
    ]
    accepted.sort(key=lambda item: (-item.confidence, item.candidate_index))

    if len(accepted) != frame_result["accepted_detection_count"]:
        raise DetectionVisualReviewError(
            f"Frame {detection_frame.frame_index} accepted-candidate count "
            "does not match evaluator report"
        )

    matched_index = frame_result["matched_candidate_index"]
    roles = []

    for detection in accepted:
        center_error = None

        if annotation.localization_eligible:
            if annotation.geometry is None:
                raise DetectionVisualReviewError(
                    "Localization-eligible annotation has no geometry"
                )

            center_error = math.hypot(
                detection.center_xy_px[0] - annotation.geometry.center_xy_px[0],
                detection.center_xy_px[1] - annotation.geometry.center_xy_px[1],
            )

        if detection.candidate_index == matched_index:
            role = "true_positive"
        elif frame_result["scoring_status"] == "not_visible_negative":
            role = "not_visible_false_alarm"
        elif frame_result["scoring_status"] == "unscored":
            role = "unscored_prediction"
        elif (
            matched_index is not None
            and center_error is not None
            and center_error <= localization_radius_px
        ):
            role = "duplicate_false_positive"
        else:
            role = "ordinary_false_positive"

        roles.append(
            {
                "candidate_index": detection.candidate_index,
                "confidence": detection.confidence,
                "role": role,
                "center_error_px": center_error,
            }
        )

    true_positive_count = sum(
        item["role"] == "true_positive" for item in roles
    )
    false_positive_count = sum(
        item["role"]
        in {
            "ordinary_false_positive",
            "duplicate_false_positive",
            "not_visible_false_alarm",
        }
        for item in roles
    )
    duplicate_count = sum(
        item["role"] == "duplicate_false_positive" for item in roles
    )
    not_visible_count = sum(
        item["role"] == "not_visible_false_alarm" for item in roles
    )
    unscored_count = sum(
        item["role"] == "unscored_prediction" for item in roles
    )
    expected_true_positive_count = int(matched_index is not None)

    if (
        true_positive_count != expected_true_positive_count
        or false_positive_count != frame_result["false_positive_count"]
        or duplicate_count != frame_result["duplicate_false_positive_count"]
        or not_visible_count != frame_result["non_visible_false_alarm_count"]
        or unscored_count != frame_result["unscored_prediction_count"]
    ):
        raise DetectionVisualReviewError(
            f"Frame {detection_frame.frame_index} candidate roles do not "
            "reconcile with evaluator counts"
        )

    return tuple(roles)


def _ascii(value: str) -> str:
    return value.encode("ascii", "replace").decode("ascii")


def _put_fitted_text(
    image: Any,
    text: str,
    origin: tuple[int, int],
    max_width_px: int,
    base_scale: float,
    color: tuple[int, int, int],
    *,
    thickness: int = 1,
) -> None:
    """Draw one complete line, shrinking it when needed to avoid clipping."""

    rendered = _ascii(text)
    (text_width, _), _ = cv2.getTextSize(
        rendered,
        cv2.FONT_HERSHEY_SIMPLEX,
        base_scale,
        thickness,
    )
    scale = base_scale

    if text_width > max_width_px:
        scale *= max_width_px / text_width

    cv2.putText(
        image,
        rendered,
        origin,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        thickness,
        cv2.LINE_AA,
    )


def _draw_unscored_annotation_marker(
    image: Any,
    annotation: FrameAnnotation,
) -> None:
    """Mark geometry that is context only and explicitly not scoring truth."""

    if annotation.geometry is None:
        return

    height, width = image.shape[:2]
    center = (
        max(0, min(width - 1, round(annotation.geometry.center_xy_px[0]))),
        max(0, min(height - 1, round(annotation.geometry.center_xy_px[1]))),
    )
    diamond = np.array(
        [
            [center[0], center[1] - 10],
            [center[0] + 10, center[1]],
            [center[0], center[1] + 10],
            [center[0] - 10, center[1]],
        ],
        dtype=np.int32,
    )
    cv2.polylines(image, [diamond], True, ORANGE, 2, cv2.LINE_AA)
    cv2.putText(
        image,
        "AMBIGUOUS / UNSCORED ANNOTATION",
        (max(0, center[0] + 14), max(28, center[1] - 14)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        ORANGE,
        2,
        cv2.LINE_AA,
    )


def _candidate_by_index(
    detection_frame: DetectionFrame,
) -> dict[int, BallDetection]:
    if detection_frame.detections is None:
        return {}

    return {
        detection.candidate_index: detection
        for detection in detection_frame.detections
    }


def _draw_candidate(
    image: Any,
    detection: BallDetection,
    role: str,
) -> None:
    color = CANDIDATE_ROLE_COLORS[role]
    label = CANDIDATE_ROLE_LABELS[role]
    height, width = image.shape[:2]
    x1, y1, x2, y2 = detection.bbox_xyxy_px
    left_float = max(0.0, min(width - 1.0, x1))
    top_float = max(0.0, min(height - 1.0, y1))
    right_float = max(0.0, min(width - 1.0, x2))
    bottom_float = max(0.0, min(height - 1.0, y2))
    left = round(left_float)
    top = round(top_float)
    center = (
        max(0, min(width - 1, round(detection.center_xy_px[0]))),
        max(0, min(height - 1, round(detection.center_xy_px[1]))),
    )
    fixed_shift = 8
    fixed_scale = 1 << fixed_shift
    fixed_center = tuple(
        round(
            max(0.0, min(limit - 1.0, coordinate)) * fixed_scale
        )
        for coordinate, limit in zip(
            detection.center_xy_px,
            (width, height),
            strict=True,
        )
    )
    thickness = 3 if role == "true_positive" else 2
    cv2.rectangle(
        image,
        (
            round(left_float * fixed_scale),
            round(top_float * fixed_scale),
        ),
        (
            round(right_float * fixed_scale),
            round(bottom_float * fixed_scale),
        ),
        color,
        thickness,
        cv2.LINE_8,
        fixed_shift,
    )

    if role == "true_positive":
        cv2.circle(
            image,
            fixed_center,
            7 * fixed_scale,
            color,
            2,
            cv2.LINE_AA,
            fixed_shift,
        )
    elif role == "duplicate_false_positive":
        cv2.circle(
            image,
            fixed_center,
            7 * fixed_scale,
            color,
            2,
            cv2.LINE_AA,
            fixed_shift,
        )
        cv2.circle(
            image,
            fixed_center,
            11 * fixed_scale,
            color,
            1,
            cv2.LINE_AA,
            fixed_shift,
        )
    elif role == "not_visible_false_alarm":
        triangle = np.array(
            [
                [center[0], center[1] - 9],
                [center[0] + 8, center[1] + 7],
                [center[0] - 8, center[1] + 7],
            ],
            dtype=np.int32,
        )
        cv2.polylines(image, [triangle], True, color, 2, cv2.LINE_AA)
    elif role == "unscored_prediction":
        cv2.putText(
            image,
            "?",
            (center[0] - 5, center[1] + 7),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2,
            cv2.LINE_AA,
        )
    else:
        cv2.line(
            image,
            (center[0] - 7, center[1] - 7),
            (center[0] + 7, center[1] + 7),
            color,
            2,
            cv2.LINE_AA,
        )
        cv2.line(
            image,
            (center[0] + 7, center[1] - 7),
            (center[0] - 7, center[1] + 7),
            color,
            2,
            cv2.LINE_AA,
        )

    text = f"#{detection.candidate_index} {label}"
    text_y = max(18, top - 6)
    cv2.putText(
        image,
        _ascii(text),
        (left, text_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        color,
        2,
        cv2.LINE_AA,
    )


def render_detection_overlay(
    source_frame: Any,
    annotation: FrameAnnotation,
    detection_frame: DetectionFrame,
    frame_result: Mapping[str, Any],
    view: DetectionReviewView,
) -> tuple[Any, tuple[dict[str, Any], ...]]:
    """Render every accepted candidate and authoritative truth at native size."""

    source_height, source_width = source_frame.shape[:2]
    sidebar_width = max(520, min(720, round(source_width * 0.34)))
    overlay = np.full(
        (source_height, source_width + sidebar_width, 3),
        12,
        dtype=np.uint8,
    )
    overlay[:, :source_width] = source_frame
    source_view = overlay[:, :source_width]
    roles = candidate_display_roles(
        annotation,
        detection_frame,
        frame_result,
        confidence_threshold=view.confidence_threshold,
        localization_radius_px=view.localization_radius_px,
    )
    detections_by_index = _candidate_by_index(detection_frame)
    matched_index = frame_result["matched_candidate_index"]

    for role_record in roles:
        if role_record["candidate_index"] == matched_index:
            continue
        _draw_candidate(
            source_view,
            detections_by_index[role_record["candidate_index"]],
            role_record["role"],
        )

    if matched_index is not None:
        matched_role = next(
            item for item in roles if item["candidate_index"] == matched_index
        )
        _draw_candidate(
            source_view,
            detections_by_index[matched_index],
            matched_role["role"],
        )

    if annotation.localization_eligible:
        if annotation.geometry is None:
            raise DetectionVisualReviewError(
                "Localization-eligible annotation has no geometry"
            )

        center = (
            round(annotation.geometry.center_xy_px[0]),
            round(annotation.geometry.center_xy_px[1]),
        )
        fixed_shift = 8
        fixed_scale = 1 << fixed_shift
        cv2.circle(
            source_view,
            tuple(
                round(coordinate * fixed_scale)
                for coordinate in annotation.geometry.center_xy_px
            ),
            round(view.localization_radius_px * fixed_scale),
            BLUE,
            1,
            cv2.LINE_AA,
            fixed_shift,
        )
        _draw_point_marker(
            source_view,
            annotation.geometry.center_xy_px,
            annotation.geometry.uncertainty_radius_px,
            annotation.visibility,
        )

        if frame_result["false_negative_count"]:
            cv2.putText(
                source_view,
                "FN - REVIEWED BALL MISSED",
                (max(0, center[0] + 14), max(28, center[1] - 14)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                RED,
                2,
                cv2.LINE_AA,
            )
    elif annotation.geometry is not None:
        _draw_unscored_annotation_marker(source_view, annotation)

    scale = max(0.42, min(0.62, sidebar_width / 620.0 * 0.56))
    line_height = max(22, round(29 * scale / 0.56))
    sidebar_x = source_width + 14
    sidebar_text_width = sidebar_width - 28
    header_lines = (
        ("DESCRIPTIVE VIEW - NOT SELECTED", WHITE),
        (f"VIEW {view.view_id}", WHITE),
        (
            f"CONF >= {view.confidence_threshold:.2f} | "
            f"RAW RADIUS <= {view.localization_radius_px:.1f} PX",
            WHITE,
        ),
        (f"ROLE {view.role}", GRAY),
    )

    for line_number, (text, color) in enumerate(header_lines, start=1):
        _put_fitted_text(
            overlay,
            text,
            (sidebar_x, line_number * line_height),
            sidebar_text_width,
            scale,
            color,
        )
    status_line = (
        f"FRAME {annotation.frame_index} | {frame_result['scoring_status']} | "
        f"TP {int(matched_index is not None)} FP "
        f"{frame_result['false_positive_count']} FN "
        f"{frame_result['false_negative_count']} DUP "
        f"{frame_result['duplicate_false_positive_count']} NV "
        f"{frame_result['non_visible_false_alarm_count']} UNSCORED "
        f"{frame_result['unscored_prediction_count']}"
    )
    count_line = (
        f"RAW {frame_result['input_detection_count']} | ACCEPTED "
        f"{frame_result['accepted_detection_count']} | BELOW THRESHOLD "
        f"{frame_result['input_detection_count'] - frame_result['accepted_detection_count']}"
    )
    _put_fitted_text(
        overlay,
        status_line,
        (sidebar_x, 6 * line_height),
        sidebar_text_width,
        scale,
        WHITE,
    )
    _put_fitted_text(
        overlay,
        count_line,
        (sidebar_x, 7 * line_height),
        sidebar_text_width,
        scale,
        GRAY,
    )
    _put_fitted_text(
        overlay,
        "CANDIDATES (FP = vs reviewed game ball)",
        (sidebar_x, 9 * line_height),
        sidebar_text_width,
        scale,
        WHITE,
    )

    for position, role_record in enumerate(roles):
        candidate = detections_by_index[role_record["candidate_index"]]
        error = role_record["center_error_px"]
        error_text = "n/a" if error is None else f"{error:.2f}px"
        candidate_text = (
            f"#{candidate.candidate_index:03d} "
            f"{CANDIDATE_ROLE_LABELS[role_record['role']]:8s} "
            f"conf {candidate.confidence:.3f} err {error_text}"
        )
        y = (10 + position) * line_height

        if y >= source_height - line_height:
            cv2.putText(
                overlay,
                f"... {len(roles) - position} more accepted candidates",
                (sidebar_x, source_height - line_height),
                cv2.FONT_HERSHEY_SIMPLEX,
                scale,
                ORANGE,
                1,
                cv2.LINE_AA,
            )
            break

        _put_fitted_text(
            overlay,
            candidate_text,
            (sidebar_x, y),
            sidebar_text_width,
            scale,
            CANDIDATE_ROLE_COLORS[role_record["role"]],
        )

    cv2.line(
        overlay,
        (source_width + 2, 0),
        (source_width + 2, source_height - 1),
        WHITE,
        2,
        cv2.LINE_8,
    )
    return overlay, roles


def _fit_context_panel(image: Any, width: int, height: int) -> Any:
    return aspect_preserving_letterbox(image, width, height)


def build_synchronized_comparison_frame(
    overlays: Sequence[Any],
    views: Sequence[DetectionReviewView],
    frame_index: int,
) -> Any:
    """Place both descriptive views on one chronological context canvas."""

    if len(overlays) != EXPECTED_VIEW_COUNT or len(views) != EXPECTED_VIEW_COUNT:
        raise DetectionVisualReviewError(
            "Synchronized comparison requires exactly 2 views"
        )

    canvas = np.full(
        (COMPARISON_HEIGHT_PX, COMPARISON_WIDTH_PX, 3),
        12,
        dtype=np.uint8,
    )
    heading = (
        f"FRAME {frame_index} | SYNCHRONIZED DESCRIPTIVE COMPARISON | "
        "CONTEXT ONLY - NO OPERATING POINT SELECTED"
    )
    cv2.putText(
        canvas,
        _ascii(heading),
        (24, 38),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.82,
        WHITE,
        2,
        cv2.LINE_AA,
    )

    for index, (overlay, view) in enumerate(zip(overlays, views, strict=True)):
        x = index * COMPARISON_PANEL_WIDTH_PX
        panel = _fit_context_panel(
            overlay,
            COMPARISON_PANEL_WIDTH_PX,
            COMPARISON_PANEL_HEIGHT_PX,
        )
        canvas[
            COMPARISON_HEADER_PX : COMPARISON_HEIGHT_PX,
            x : x + COMPARISON_PANEL_WIDTH_PX,
        ] = panel
        label = (
            f"{view.view_id} | conf >= {view.confidence_threshold:.2f} | "
            f"radius {view.localization_radius_px:.1f}px"
        )
        cv2.putText(
            canvas,
            _ascii(label),
            (x + 18, 82),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            GRAY,
            1,
            cv2.LINE_AA,
        )

    cv2.line(
        canvas,
        (COMPARISON_PANEL_WIDTH_PX, COMPARISON_HEADER_PX),
        (COMPARISON_PANEL_WIDTH_PX, COMPARISON_HEIGHT_PX - 1),
        WHITE,
        2,
    )
    return canvas


def _padded_crop(
    image: Any,
    center_xy: tuple[float, float],
) -> tuple[Any, tuple[int, int, int, int]]:
    center_x = round(center_xy[0])
    center_y = round(center_xy[1])
    requested_x1 = center_x - ZOOM_HALF_SIZE_PX
    requested_y1 = center_y - ZOOM_HALF_SIZE_PX
    requested_x2 = center_x + ZOOM_HALF_SIZE_PX + 1
    requested_y2 = center_y + ZOOM_HALF_SIZE_PX + 1
    crop = np.zeros(
        (ZOOM_SOURCE_SIZE_PX, ZOOM_SOURCE_SIZE_PX, 3),
        dtype=np.uint8,
    )
    height, width = image.shape[:2]
    source_x1 = max(0, requested_x1)
    source_y1 = max(0, requested_y1)
    source_x2 = min(width, requested_x2)
    source_y2 = min(height, requested_y2)
    destination_x1 = source_x1 - requested_x1
    destination_y1 = source_y1 - requested_y1
    destination_x2 = destination_x1 + source_x2 - source_x1
    destination_y2 = destination_y1 + source_y2 - source_y1

    if source_x2 > source_x1 and source_y2 > source_y1:
        crop[
            destination_y1:destination_y2,
            destination_x1:destination_x2,
        ] = image[source_y1:source_y2, source_x1:source_x2]

    return crop, (
        requested_x1,
        requested_y1,
        requested_x2,
        requested_y2,
    )


def _focus_point(
    annotation: FrameAnnotation,
    detection_frame: DetectionFrame,
    views: Sequence[DetectionReviewView],
    source_width: int,
    source_height: int,
) -> tuple[tuple[float, float], str]:
    if annotation.localization_eligible:
        if annotation.geometry is None:
            raise DetectionVisualReviewError(
                "Localization-eligible annotation has no geometry"
            )

        return annotation.geometry.center_xy_px, "reviewed_truth_center"

    if annotation.geometry is not None:
        return (
            annotation.geometry.center_xy_px,
            "ambiguous_unscored_annotation_center_not_truth",
        )

    if detection_frame.detections is not None:
        minimum_threshold = min(view.confidence_threshold for view in views)
        accepted = [
            detection
            for detection in detection_frame.detections
            if detection.confidence >= minimum_threshold
        ]

        if accepted:
            accepted.sort(
                key=lambda item: (-item.confidence, item.candidate_index)
            )
            return accepted[0].center_xy_px, "top_accepted_candidate_no_truth"

    return (
        (source_width - 1) / 2.0,
        (source_height - 1) / 2.0,
    ), "frame_center_no_truth_or_accepted_candidate"


def render_truth_region_panel(
    source_frame: Any,
    overlays: Sequence[Any],
    annotation: FrameAnnotation,
    detection_frame: DetectionFrame,
    views: Sequence[DetectionReviewView],
) -> tuple[Any, dict[str, Any]]:
    """Render RAW | view 1 | view 2 without inventing missing truth geometry."""

    if len(overlays) != EXPECTED_VIEW_COUNT or len(views) != EXPECTED_VIEW_COUNT:
        raise DetectionVisualReviewError(
            "Truth-region panel requires exactly 2 views"
        )

    source_height, source_width = source_frame.shape[:2]
    focus_xy, focus_type = _focus_point(
        annotation,
        detection_frame,
        views,
        source_width,
        source_height,
    )
    source_images = [
        source_frame,
        *(overlay[:, :source_width] for overlay in overlays),
    ]
    crops = []
    requested_crop = None

    for image in source_images:
        crop, requested = _padded_crop(image, focus_xy)
        crops.append(
            cv2.resize(
                crop,
                (ZOOM_SOURCE_SIZE_PX * ZOOM_FACTOR,) * 2,
                interpolation=cv2.INTER_NEAREST,
            )
        )

        if requested_crop is None:
            requested_crop = requested
        elif requested != requested_crop:
            raise DetectionVisualReviewError(
                "Truth-region crops do not share exact source coordinates"
            )

    panel = np.full(
        (ZOOM_PANEL_HEIGHT_PX, ZOOM_PANEL_WIDTH_PX, 3),
        12,
        dtype=np.uint8,
    )
    heading = (
        f"FRAME {annotation.frame_index} | FOCUS {focus_type} | "
        "NEAREST-NEIGHBOR 4X | RAW COLUMN IS UNMARKED"
    )
    cv2.putText(
        panel,
        _ascii(heading),
        (18, 36),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.68,
        WHITE,
        2,
        cv2.LINE_AA,
    )
    if annotation.geometry is None:
        cv2.putText(
            panel,
            "NO REVIEWED TRUTH GEOMETRY - FOCUS IS NOT A BALL LABEL",
            (18, 72),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.63,
            ORANGE,
            2,
            cv2.LINE_AA,
        )
    elif not annotation.localization_eligible:
        cv2.putText(
            panel,
            "AMBIGUOUS / UNSCORED ANNOTATION - NOT LOCALIZATION TRUTH",
            (18, 72),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.63,
            ORANGE,
            2,
            cv2.LINE_AA,
        )
    labels = (
        "RAW UNMARKED",
        f"{views[0].view_id}",
        f"{views[1].view_id}",
    )
    column_width = ZOOM_SOURCE_SIZE_PX * ZOOM_FACTOR

    for index, (crop, label) in enumerate(zip(crops, labels, strict=True)):
        x = index * column_width
        panel[ZOOM_PANEL_HEADER_PX:, x : x + column_width] = crop
        cv2.putText(
            panel,
            _ascii(label),
            (x + 12, 108),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            GRAY,
            1,
            cv2.LINE_AA,
        )
        cv2.rectangle(
            panel,
            (x, ZOOM_PANEL_HEADER_PX),
            (x + column_width - 1, ZOOM_PANEL_HEIGHT_PX - 1),
            WHITE,
            1,
        )

    return panel, {
        "focus_type": focus_type,
        "focus_xy_px": [focus_xy[0], focus_xy[1]],
        "requested_source_crop_xyxy_px": list(requested_crop),
        "zoom_factor": ZOOM_FACTOR,
        "raw_unmarked_view_included": True,
    }


def build_contact_sheet(
    images: Sequence[Any],
    frame_indices: Sequence[int],
    title: str,
    *,
    empty_statement: str | None = None,
) -> Any:
    """Build a fixed 5x5 chronological context-only contact sheet."""

    if len(images) != len(frame_indices) or len(images) > 25:
        raise DetectionVisualReviewError(
            "Contact-sheet images and frame indices must agree and fit 5x5"
        )

    sheet = np.full(
        (
            CONTACT_HEADER_PX + CONTACT_ROWS * CONTACT_TILE_HEIGHT_PX,
            CONTACT_COLUMNS * CONTACT_TILE_WIDTH_PX,
            3,
        ),
        14,
        dtype=np.uint8,
    )
    cv2.putText(
        sheet,
        _ascii(title),
        (24, 42),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.78,
        WHITE,
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        sheet,
        "CONTEXT ONLY - USE FULL-RESOLUTION OVERLAYS FOR PIXEL REVIEW",
        (24, 78),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        GRAY,
        1,
        cv2.LINE_AA,
    )

    if not images:
        statement = empty_statement or "ZERO FRAMES IN THIS CATEGORY"
        cv2.putText(
            sheet,
            _ascii(statement),
            (90, CONTACT_HEADER_PX + 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            ORANGE,
            2,
            cv2.LINE_AA,
        )
        return sheet

    for index, (image, frame_index) in enumerate(
        zip(images, frame_indices, strict=True)
    ):
        row, column = divmod(index, CONTACT_COLUMNS)
        x = column * CONTACT_TILE_WIDTH_PX
        y = CONTACT_HEADER_PX + row * CONTACT_TILE_HEIGHT_PX
        tile = _fit_context_panel(
            image,
            CONTACT_TILE_WIDTH_PX,
            CONTACT_TILE_HEIGHT_PX,
        )
        sheet[y : y + CONTACT_TILE_HEIGHT_PX, x : x + CONTACT_TILE_WIDTH_PX] = tile
        cv2.rectangle(sheet, (x, y), (x + 160, y + 28), BLACK, -1)
        cv2.putText(
            sheet,
            f"FRAME {frame_index}",
            (x + 8, y + 21),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            WHITE,
            1,
            cv2.LINE_AA,
        )
        cv2.rectangle(
            sheet,
            (x, y),
            (x + CONTACT_TILE_WIDTH_PX - 1, y + CONTACT_TILE_HEIGHT_PX - 1),
            WHITE,
            1,
        )

    return sheet


def _metric_value(aggregate: Mapping[str, Any], metric: str) -> float | None:
    if metric == "micro_f1_visualization_derived":
        true_positive = aggregate["true_positive_count"]
        false_positive = aggregate["false_positive_count"]
        false_negative = aggregate["false_negative_count"]
        denominator = 2 * true_positive + false_positive + false_negative
        return None if denominator == 0 else 2 * true_positive / denominator

    return aggregate[metric]


def build_metric_heatmaps(
    scoring_report: Mapping[str, Any],
    views: Sequence[DetectionReviewView],
) -> Any:
    """Render fixed-scale precision, recall, and derived-F1 grid panels."""

    thresholds = scoring_report["confidence_thresholds"]
    radii = scoring_report["localization_radii_px"]
    aggregate_by_cell = {
        (
            item["confidence_threshold"],
            item["localization_radius_px"],
        ): item["aggregate"]
        for item in scoring_report["aggregate_results"]
    }
    canvas = np.full(
        (HEATMAP_HEIGHT_PX, HEATMAP_WIDTH_PX, 3),
        16,
        dtype=np.uint8,
    )
    cv2.putText(
        canvas,
        "DESCRIPTIVE PROTOCOL-PILOT GRID - REQUESTED CELLS OUTLINED - NO WINNER OR OPERATING POINT",
        (24, 42),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        WHITE,
        2,
        cv2.LINE_AA,
    )
    panel_width = HEATMAP_WIDTH_PX // 3
    grid_left = 88
    grid_top = 122
    cell_width = 88
    cell_height = 58
    metrics = (
        ("micro_precision", "MICRO PRECISION"),
        ("micro_recall", "MICRO RECALL"),
        ("micro_f1_visualization_derived", "MICRO F1 (VISUALIZATION-DERIVED)"),
    )
    requested_cells = {
        (view.confidence_threshold, view.localization_radius_px)
        for view in views
    }

    for panel_index, (metric, title) in enumerate(metrics):
        offset_x = panel_index * panel_width
        cv2.putText(
            canvas,
            title,
            (offset_x + 100, 86),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            WHITE,
            2,
            cv2.LINE_AA,
        )

        for column, radius in enumerate(radii):
            cv2.putText(
                canvas,
                f"{radius:g}px",
                (offset_x + grid_left + column * cell_width + 18, grid_top - 14),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                GRAY,
                1,
                cv2.LINE_AA,
            )

        for row, threshold in enumerate(thresholds):
            cv2.putText(
                canvas,
                f"{threshold:.2f}",
                (offset_x + 18, grid_top + row * cell_height + 36),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.46,
                GRAY,
                1,
                cv2.LINE_AA,
            )

            for column, radius in enumerate(radii):
                aggregate = aggregate_by_cell[(threshold, radius)]
                value = _metric_value(aggregate, metric)
                x1 = offset_x + grid_left + column * cell_width
                y1 = grid_top + row * cell_height
                x2 = x1 + cell_width - 4
                y2 = y1 + cell_height - 4

                if value is None:
                    color = (80, 80, 80)
                    text = "NA"
                else:
                    bounded = max(0.0, min(1.0, value))
                    color = (
                        32,
                        round(45 + 170 * bounded),
                        round(215 - 170 * bounded),
                    )
                    text = f"{value:.3f}"

                cv2.rectangle(canvas, (x1, y1), (x2, y2), color, -1)
                outline = (
                    CYAN if (threshold, radius) in requested_cells else WHITE
                )
                thickness = 3 if (threshold, radius) in requested_cells else 1
                cv2.rectangle(canvas, (x1, y1), (x2, y2), outline, thickness)
                cv2.putText(
                    canvas,
                    text,
                    (x1 + 9, y1 + 34),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.47,
                    BLACK,
                    1,
                    cv2.LINE_AA,
                )

    return canvas


def _asset_record(path: Path, bundle_dir: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(bundle_dir).as_posix(),
        "sha256": _sha256_file(path),
        "byte_size": path.stat().st_size,
    }


def _write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)

    if path.read_bytes() != content:
        raise DetectionVisualReviewError(
            f"Written bytes did not verify: {path}"
        )


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    _write_bytes(
        path,
        (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode(
            "utf-8"
        ),
    )


def _resolve_review_plan_path(
    repository_root: Path,
    review_plan_path: Path,
) -> tuple[Path, PurePosixPath]:
    if ".." in review_plan_path.parts:
        raise DetectionVisualReviewError(
            "Review-plan path must not contain parent traversal"
        )

    candidate = (
        review_plan_path
        if review_plan_path.is_absolute()
        else repository_root / review_plan_path
    )
    absolute = Path(os.path.abspath(candidate))

    try:
        relative = PurePosixPath(
            absolute.relative_to(repository_root).as_posix()
        )
    except ValueError as error:
        raise DetectionVisualReviewError(
            "Review plan must stay within the repository root"
        ) from error

    if (
        tuple(relative.parts[: len(PLAN_ROOT_PARTS)]) != PLAN_ROOT_PARTS
        or len(relative.parts) <= len(PLAN_ROOT_PARTS)
        or relative.suffix != ".json"
    ):
        raise DetectionVisualReviewError(
            "Review plan must be a JSON file beneath configs/ball_tracking/reviews"
        )

    checked = reject_unsafe_repository_path(
        repository_root,
        relative,
        label="Detection visual-review plan path",
    )

    if not checked.is_file():
        raise DetectionVisualReviewError(
            f"Detection visual-review plan does not exist: {checked}"
        )

    return checked, relative


def _find_report_for_view(
    scoring_report: Mapping[str, Any],
    annotation_set_id: str,
    view: DetectionReviewView,
) -> Mapping[str, Any]:
    matches = [
        report
        for report in scoring_report["evaluation_reports"]
        if report["annotation_set_id"] == annotation_set_id
        and report["confidence_threshold"] == view.confidence_threshold
        and report["localization_radius_px"] == view.localization_radius_px
    ]

    if len(matches) != 1:
        raise DetectionVisualReviewError(
            f"Scoring report must contain exactly one report for "
            f"{annotation_set_id!r} at confidence "
            f"{view.confidence_threshold} / radius "
            f"{view.localization_radius_px}; received {len(matches)}"
        )

    return matches[0]


def _validate_scoring_report_against_experiment(
    scoring_report: Mapping[str, Any],
    experiment: DetectorExperiment,
    experiment_manifest_relative: PurePosixPath,
) -> None:
    """Bind the ignored report back to the exact committed manifest contract."""

    if scoring_report["experiment_id"] != experiment.experiment_id:
        raise DetectionVisualReviewError(
            "Scoring report experiment_id conflicts with experiment manifest"
        )

    if scoring_report["experiment_manifest"]["path"] != (
        experiment_manifest_relative.as_posix()
    ):
        raise DetectionVisualReviewError(
            "Scoring report experiment manifest path is not exact"
        )

    if scoring_report["experiment_manifest"][
        "canonical_content_sha256"
    ] != _canonical_sha256(experiment.to_dict()):
        raise DetectionVisualReviewError(
            "Scoring report canonical experiment content does not match manifest"
        )

    if scoring_report["confidence_thresholds"] != list(
        experiment.scoring_grid.confidence_thresholds
    ) or scoring_report["localization_radii_px"] != list(
        experiment.scoring_grid.localization_radii_px
    ):
        raise DetectionVisualReviewError(
            "Scoring report grid conflicts with the frozen experiment grid"
        )

    windows = experiment.windows_for_inference()
    pilot_inputs = scoring_report["pilot_inputs"]

    if len(windows) != len(pilot_inputs):
        raise DetectionVisualReviewError(
            "Scoring report pilot count conflicts with experiment manifest"
        )

    for index, (window, pilot_input) in enumerate(
        zip(windows, pilot_inputs, strict=True)
    ):
        expected = {
            "window_id": window.window_id,
            "annotation_set_id": window.annotation_set_id,
            "annotation_path": (
                "configs/ball_tracking/annotations/"
                f"{window.annotation_set_id}.json"
            ),
            "detection_run_id": window.detection_run_id,
            "detection_path": window.output_path.as_posix(),
            "possession_id": window.possession_id,
            "source_video_path": window.source_video.path.as_posix(),
            "source_video_sha256": window.source_video.sha256,
            "window_start_frame_index": window.start_frame_index,
            "window_end_frame_index": window.end_frame_index,
        }

        for field, expected_value in expected.items():
            if pilot_input[field] != expected_value:
                raise DetectionVisualReviewError(
                    f"Scoring report pilot_inputs[{index}].{field} "
                    "conflicts with experiment manifest"
                )


def _prepare_visual_pilots(
    plan: DetectionReviewPlan,
    scoring_report: Mapping[str, Any],
    repository_root: Path,
    dependencies: VisualReviewDependencies,
) -> tuple[PreparedVisualPilot, ...]:
    if scoring_report["experiment_id"] != plan.experiment_id:
        raise DetectionVisualReviewError(
            "Review plan experiment_id does not match scoring report"
        )

    if scoring_report["selection_purpose"] != "protocol_adjudication":
        raise DetectionVisualReviewError(
            "Detection visual review may consume only protocol pilots"
        )

    grid_cells = {
        (item["confidence_threshold"], item["localization_radius_px"])
        for item in scoring_report["aggregate_results"]
    }

    for view in plan.views:
        if (
            view.confidence_threshold,
            view.localization_radius_px,
        ) not in grid_cells:
            raise DetectionVisualReviewError(
                f"Review view {view.view_id!r} is not a scored grid cell"
            )

    pilot_inputs = scoring_report["pilot_inputs"]

    if len(pilot_inputs) != EXPECTED_PILOT_COUNT:
        raise DetectionVisualReviewError(
            "Visual review requires exactly the 3 scored pilots"
        )

    prepared = []
    seen_model_provenance = None

    for pilot_input in pilot_inputs:
        annotation_relative = _portable_json_path(
            pilot_input["annotation_path"],
            "pilot annotation path",
        )
        dependencies.verify_tracked_file(
            repository_root,
            annotation_relative,
        )
        annotation_path = reject_unsafe_repository_path(
            repository_root,
            annotation_relative,
            label=f"Annotation path for {pilot_input['window_id']}",
        )
        annotation_bytes = annotation_path.read_bytes()

        if _sha256_bytes(annotation_bytes) != pilot_input[
            "annotation_file_sha256"
        ]:
            raise DetectionVisualReviewError(
                f"Annotation file hash no longer matches scoring report: "
                f"{annotation_relative}"
            )

        annotations = dependencies.load_annotation(annotation_path)
        detection_relative = _portable_json_path(
            pilot_input["detection_path"],
            "pilot detection path",
        )
        detection_path = reject_unsafe_repository_path(
            repository_root,
            detection_relative,
            label=f"Detection path for {pilot_input['window_id']}",
        )

        if not dependencies.is_git_ignored(
            repository_root,
            detection_relative,
        ):
            raise DetectionVisualReviewError(
                f"Detection input is not Git-ignored: {detection_relative}"
            )

        detection_bytes = detection_path.read_bytes()

        if _sha256_bytes(detection_bytes) != pilot_input[
            "detection_file_sha256"
        ]:
            raise DetectionVisualReviewError(
                f"Detection file hash no longer matches scoring report: "
                f"{detection_relative}"
            )

        detections = dependencies.load_detection(detection_path)

        if annotations.annotation_set_id != pilot_input["annotation_set_id"]:
            raise DetectionVisualReviewError(
                "Loaded annotation_set_id conflicts with scoring report"
            )

        if detections.detection_run_id != pilot_input["detection_run_id"]:
            raise DetectionVisualReviewError(
                "Loaded detection_run_id conflicts with scoring report"
            )

        reports_by_view_id = {}

        for view in plan.views:
            expected_report = _find_report_for_view(
                scoring_report,
                annotations.annotation_set_id,
                view,
            )
            recomputed = evaluate_detections(
                annotations,
                detections,
                confidence_threshold=view.confidence_threshold,
                localization_radius_px=view.localization_radius_px,
            )

            if recomputed != expected_report:
                raise DetectionVisualReviewError(
                    f"Recomputed evaluation does not exactly match scoring "
                    f"report for {annotations.annotation_set_id!r} / "
                    f"{view.view_id!r}"
                )

            reports_by_view_id[view.view_id] = expected_report

        if seen_model_provenance is None:
            seen_model_provenance = detections.model_provenance
        elif detections.model_provenance != seen_model_provenance:
            raise DetectionVisualReviewError(
                "Visual-review detections do not share one model provenance"
            )

        source_relative = annotations.source_video.path
        source_path = reject_unsafe_repository_path(
            repository_root,
            source_relative,
            label=f"Source video for {pilot_input['window_id']}",
        )
        source_verification = dependencies.verify_source(
            annotations.source_video,
            repository_root,
        )

        if source_verification["sha256"] != annotations.source_video.sha256:
            raise DetectionVisualReviewError(
                "Source verifier returned a conflicting SHA-256"
            )

        prepared.append(
            PreparedVisualPilot(
                pilot_input=pilot_input,
                annotation_path=annotation_path,
                annotation_bytes=annotation_bytes,
                annotations=annotations,
                detection_path=detection_path,
                detection_bytes=detection_bytes,
                detections=detections,
                reports_by_view_id=reports_by_view_id,
                source_path=source_path,
                source_bytes_sha256=annotations.source_video.sha256,
            )
        )

    return tuple(prepared)


def _view_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    precision = report["precision"]
    recall = report["recall"]
    f1 = (
        None
        if precision is None or recall is None or precision + recall == 0
        else 2 * precision * recall / (precision + recall)
    )
    return {
        "true_positive_count": report["true_positive_count"],
        "false_positive_count": report["false_positive_count"],
        "false_negative_count": report["false_negative_count"],
        "duplicate_false_positive_count": report[
            "duplicate_false_positive_count"
        ],
        "non_visible_false_alarm_count": report[
            "non_visible_false_alarm_count"
        ],
        "unscored_prediction_count": report["unscored_prediction_count"],
        "precision": precision,
        "recall": recall,
        "f1_visualization_derived": f1,
    }


def _frame_category_membership(
    frame_result: Mapping[str, Any],
    roles: Sequence[Mapping[str, Any]],
) -> dict[str, bool]:
    return {
        "true_positive": frame_result["matched_candidate_index"] is not None,
        "false_negative": frame_result["false_negative_count"] > 0,
        "ordinary_false_positive": any(
            item["role"] == "ordinary_false_positive" for item in roles
        ),
        "duplicate_false_positive": any(
            item["role"] == "duplicate_false_positive" for item in roles
        ),
        "not_visible_clean_negative": (
            frame_result["scoring_status"] == "not_visible_negative"
            and frame_result["non_visible_false_alarm_count"] == 0
        ),
        "not_visible_false_alarm": (
            frame_result["scoring_status"] == "not_visible_negative"
            and frame_result["non_visible_false_alarm_count"] > 0
        ),
        "unscored": frame_result["scoring_status"] == "unscored",
    }


def _write_bundle_assets(
    staging_dir: Path,
    plan: DetectionReviewPlan,
    scoring_report: Mapping[str, Any],
    plan_relative: PurePosixPath,
    plan_bytes: bytes,
    report_bytes: bytes,
    manifest_bytes: bytes,
    pilots: Sequence[PreparedVisualPilot],
    fingerprint: Mapping[str, str],
    bundle_components: Mapping[str, Any],
    digest: str,
    window_decoder: WindowDecoder,
    playback_writer: PlaybackWriter,
) -> dict[str, Any]:
    snapshots_dir = staging_dir / "input_snapshots"
    snapshots_dir.mkdir()
    plan_snapshot_path = snapshots_dir / "review_plan.json"
    scoring_snapshot_path = snapshots_dir / "scoring_report.json"
    experiment_snapshot_path = snapshots_dir / "experiment_manifest.json"
    _write_bytes(plan_snapshot_path, plan_bytes)
    _write_bytes(scoring_snapshot_path, report_bytes)
    _write_bytes(experiment_snapshot_path, manifest_bytes)
    heatmap_path = staging_dir / "pilot_metric_heatmaps.png"
    _write_lossless_png(
        heatmap_path,
        build_metric_heatmaps(scoring_report, plan.views),
    )
    pilot_records = []

    for pilot in pilots:
        frames = tuple(
            window_decoder(pilot.source_path, pilot.annotations)
        )

        if len(frames) != EXPECTED_FRAME_COUNT:
            raise DetectionVisualReviewError(
                f"Decoded pilot {pilot.pilot_input['window_id']!r} must contain "
                f"exactly {EXPECTED_FRAME_COUNT} frames"
            )

        for frame_position, frame in enumerate(frames):
            if not isinstance(frame, np.ndarray) or frame.dtype != np.uint8:
                raise DetectionVisualReviewError(
                    "Decoded source frames must be uint8 NumPy arrays"
                )

            if frame.shape != (
                pilot.annotations.source_video.height_px,
                pilot.annotations.source_video.width_px,
                3,
            ):
                raise DetectionVisualReviewError(
                    f"Decoded source frame {frame_position} dimensions conflict "
                    "with source contract"
                )

        possession_id = pilot.annotations.possession_id
        pilot_dir = staging_dir / possession_id
        pilot_dir.mkdir()
        pilot_snapshot_dir = snapshots_dir / possession_id
        pilot_snapshot_dir.mkdir()
        annotation_snapshot_path = pilot_snapshot_dir / "annotations.json"
        detection_snapshot_path = pilot_snapshot_dir / "detections.json"
        _write_bytes(annotation_snapshot_path, pilot.annotation_bytes)
        _write_bytes(detection_snapshot_path, pilot.detection_bytes)
        overlay_directories = {}
        view_roots = {}
        overlay_records_by_view: dict[str, list[dict[str, Any]]] = {}
        overlay_images_by_view: dict[str, list[Any]] = {}
        roles_by_view: dict[str, list[tuple[dict[str, Any], ...]]] = {}

        for view_index, view in enumerate(plan.views):
            view_root = pilot_dir / f"v{view_index + 1}"
            view_dir = view_root / "overlays"
            view_dir.mkdir(parents=True)
            view_roots[view.view_id] = view_root
            overlay_directories[view.view_id] = view_dir
            overlay_records_by_view[view.view_id] = []
            overlay_images_by_view[view.view_id] = []
            roles_by_view[view.view_id] = []

        comparison_dir = pilot_dir / "comparison_frames"
        zoom_dir = pilot_dir / "truth_region_panels"
        comparison_dir.mkdir()
        zoom_dir.mkdir()
        annotations_by_frame = pilot.annotations.annotation_by_frame()
        detections_by_frame = pilot.detections.frame_by_index()
        results_by_view = {
            view.view_id: {
                item["frame_index"]: item
                for item in pilot.reports_by_view_id[view.view_id]["frame_results"]
            }
            for view in plan.views
        }
        comparison_images = []
        comparison_records = []
        zoom_images = []
        zoom_records = []
        frame_indices = list(
            range(
                pilot.annotations.window.start_frame_index,
                pilot.annotations.window.end_frame_index + 1,
            )
        )

        for frame_index, source_frame in zip(
            frame_indices,
            frames,
            strict=True,
        ):
            annotation = annotations_by_frame[frame_index]
            detection_frame = detections_by_frame[frame_index]
            source_frame_hash = _sha256_bytes(source_frame.tobytes())
            frame_overlays = []

            for view in plan.views:
                frame_result = results_by_view[view.view_id][frame_index]
                overlay, roles = render_detection_overlay(
                    source_frame,
                    annotation,
                    detection_frame,
                    frame_result,
                    view,
                )
                overlay_path = overlay_directories[view.view_id] / (
                    f"frame_{frame_index:06d}.png"
                )
                _write_lossless_png(overlay_path, overlay)
                record = _asset_record(overlay_path, staging_dir)
                record.update(
                    {
                        "frame_index": frame_index,
                        "view_id": view.view_id,
                        "source_viewport_width_px": source_frame.shape[1],
                        "source_viewport_height_px": source_frame.shape[0],
                        "rendered_width_px": overlay.shape[1],
                        "rendered_height_px": overlay.shape[0],
                        "decoded_source_frame_sha256": source_frame_hash,
                        "scoring_status": frame_result["scoring_status"],
                        "input_detection_count": frame_result[
                            "input_detection_count"
                        ],
                        "accepted_detection_count": frame_result[
                            "accepted_detection_count"
                        ],
                        "matched_candidate_index": frame_result[
                            "matched_candidate_index"
                        ],
                        "false_positive_count": frame_result[
                            "false_positive_count"
                        ],
                        "false_negative_count": frame_result[
                            "false_negative_count"
                        ],
                        "duplicate_false_positive_count": frame_result[
                            "duplicate_false_positive_count"
                        ],
                        "non_visible_false_alarm_count": frame_result[
                            "non_visible_false_alarm_count"
                        ],
                        "unscored_prediction_count": frame_result[
                            "unscored_prediction_count"
                        ],
                        "candidate_roles": [dict(item) for item in roles],
                        "source_viewport_unscaled": True,
                        "source_viewport_obscured_by_header_or_sidebar": False,
                        "visualization_only": True,
                    }
                )
                overlay_records_by_view[view.view_id].append(record)
                overlay_images_by_view[view.view_id].append(
                    _fit_context_panel(
                        overlay,
                        CONTACT_TILE_WIDTH_PX,
                        CONTACT_TILE_HEIGHT_PX,
                    )
                )
                roles_by_view[view.view_id].append(roles)
                frame_overlays.append(overlay)

            comparison = build_synchronized_comparison_frame(
                frame_overlays,
                plan.views,
                frame_index,
            )
            comparison_path = comparison_dir / f"frame_{frame_index:06d}.png"
            _write_lossless_png(comparison_path, comparison)
            comparison_record = _asset_record(comparison_path, staging_dir)
            comparison_record.update(
                {
                    "frame_index": frame_index,
                    "width_px": comparison.shape[1],
                    "height_px": comparison.shape[0],
                    "chronologically_synchronized": True,
                    "pixel_geometry_review_allowed": False,
                    "visualization_only": True,
                }
            )
            comparison_records.append(comparison_record)
            comparison_images.append(comparison)
            zoom_panel, zoom_mapping = render_truth_region_panel(
                source_frame,
                frame_overlays,
                annotation,
                detection_frame,
                plan.views,
            )
            zoom_path = zoom_dir / f"frame_{frame_index:06d}.png"
            _write_lossless_png(zoom_path, zoom_panel)
            zoom_record = _asset_record(zoom_path, staging_dir)
            zoom_record.update(
                {
                    "frame_index": frame_index,
                    **zoom_mapping,
                    "visualization_only": True,
                }
            )
            zoom_records.append(zoom_record)
            zoom_images.append(
                _fit_context_panel(
                    zoom_panel,
                    CONTACT_TILE_WIDTH_PX,
                    CONTACT_TILE_HEIGHT_PX,
                )
            )

        # Native source frames and native overlays are no longer needed.  Drop
        # the final loop references before contact-sheet and playback work so
        # one 1080p pilot does not remain resident longer than necessary.
        del frames, source_frame, frame_overlays, overlay, zoom_panel

        all_frame_contact_records = {}
        category_contact_records = {}
        category_names = (
            "true_positive",
            "false_negative",
            "ordinary_false_positive",
            "duplicate_false_positive",
            "not_visible_clean_negative",
            "not_visible_false_alarm",
            "unscored",
        )

        for view in plan.views:
            view_root = view_roots[view.view_id]
            all_contact_path = view_root / "all_25_frames_contact_sheet.png"
            _write_lossless_png(
                all_contact_path,
                build_contact_sheet(
                    overlay_images_by_view[view.view_id],
                    frame_indices,
                    f"{possession_id} | {view.view_id} | ALL 25 FRAMES",
                ),
            )
            all_contact_record = _asset_record(all_contact_path, staging_dir)
            all_contact_record.update(
                {
                    "view_id": view.view_id,
                    "frame_count": EXPECTED_FRAME_COUNT,
                    "first_frame_index": frame_indices[0],
                    "last_frame_index": frame_indices[-1],
                    "chronological": True,
                    "pixel_geometry_review_allowed": False,
                    "visualization_only": True,
                }
            )
            all_frame_contact_records[view.view_id] = all_contact_record
            category_contact_records[view.view_id] = {}

            for category in category_names:
                selected_images = []
                selected_indices = []

                for position, frame_index in enumerate(frame_indices):
                    frame_result = results_by_view[view.view_id][frame_index]
                    membership = _frame_category_membership(
                        frame_result,
                        roles_by_view[view.view_id][position],
                    )

                    if membership[category]:
                        selected_images.append(
                            overlay_images_by_view[view.view_id][position]
                        )
                        selected_indices.append(frame_index)

                category_path = view_root / f"category_{category}.png"
                _write_lossless_png(
                    category_path,
                    build_contact_sheet(
                        selected_images,
                        selected_indices,
                        f"{possession_id} | {view.view_id} | {category}",
                        empty_statement=f"ZERO {category.upper()} FRAMES",
                    ),
                )
                category_record = _asset_record(category_path, staging_dir)
                category_record.update(
                    {
                        "view_id": view.view_id,
                        "category": category,
                        "frame_count": len(selected_indices),
                        "frame_indices": selected_indices,
                        "categories_are_non_partitioning": True,
                        "zero_count_placeholder": not selected_indices,
                        "pixel_geometry_review_allowed": False,
                        "visualization_only": True,
                    }
                )
                category_contact_records[view.view_id][category] = (
                    category_record
                )

        comparison_contact_path = pilot_dir / "comparison_all_25_contact_sheet.png"
        _write_lossless_png(
            comparison_contact_path,
            build_contact_sheet(
                comparison_images,
                frame_indices,
                f"{possession_id} | SYNCHRONIZED COMPARISON | ALL 25 FRAMES",
            ),
        )
        comparison_contact_record = _asset_record(
            comparison_contact_path,
            staging_dir,
        )
        comparison_contact_record.update(
            {
                "frame_count": EXPECTED_FRAME_COUNT,
                "first_frame_index": frame_indices[0],
                "last_frame_index": frame_indices[-1],
                "chronological": True,
                "pixel_geometry_review_allowed": False,
                "visualization_only": True,
            }
        )
        zoom_contact_path = pilot_dir / "truth_region_all_25_contact_sheet.png"
        _write_lossless_png(
            zoom_contact_path,
            build_contact_sheet(
                zoom_images,
                frame_indices,
                f"{possession_id} | TRUTH-REGION PANELS | ALL 25 FRAMES",
            ),
        )
        zoom_contact_record = _asset_record(zoom_contact_path, staging_dir)
        zoom_contact_record.update(
            {
                "frame_count": EXPECTED_FRAME_COUNT,
                "first_frame_index": frame_indices[0],
                "last_frame_index": frame_indices[-1],
                "chronological": True,
                "raw_unmarked_view_included": True,
                "pixel_geometry_review_allowed": False,
                "visualization_only": True,
            }
        )
        playback_path = pilot_dir / "synchronized_comparison_slow.mp4"
        playback_fps = min(MAX_PLAYBACK_FPS, pilot.annotations.source_video.fps)
        playback_codec = playback_writer(
            playback_path,
            comparison_images,
            COMPARISON_WIDTH_PX,
            COMPARISON_HEIGHT_PX,
            playback_fps,
        )
        playback_record = _asset_record(playback_path, staging_dir)
        playback_record.update(
            {
                "codec_fourcc": playback_codec,
                "frame_count": EXPECTED_FRAME_COUNT,
                "fps": playback_fps,
                "source_fps": pilot.annotations.source_video.fps,
                "first_frame_index": frame_indices[0],
                "last_frame_index": frame_indices[-1],
                "chronologically_synchronized": True,
                "pixel_geometry_review_allowed": False,
                "visualization_only": True,
            }
        )
        view_records = []

        for view in plan.views:
            view_records.append(
                {
                    **view.to_dict(),
                    "evaluation_summary": _view_summary(
                        pilot.reports_by_view_id[view.view_id]
                    ),
                    "overlay_frames": overlay_records_by_view[view.view_id],
                    "all_frame_contact_sheet": all_frame_contact_records[
                        view.view_id
                    ],
                    "category_contact_sheets": category_contact_records[
                        view.view_id
                    ],
                }
            )

        pilot_records.append(
            {
                "window_id": pilot.pilot_input["window_id"],
                "annotation_set_id": pilot.annotations.annotation_set_id,
                "detection_run_id": pilot.detections.detection_run_id,
                "possession_id": possession_id,
                "source_video": pilot.annotations.source_video.to_dict(),
                "window": {
                    **pilot.annotations.window.to_dict(),
                    "frame_count": EXPECTED_FRAME_COUNT,
                },
                "annotation_snapshot": _asset_record(
                    annotation_snapshot_path,
                    staging_dir,
                ),
                "detection_snapshot": _asset_record(
                    detection_snapshot_path,
                    staging_dir,
                ),
                "views": view_records,
                "comparison_frames": comparison_records,
                "truth_region_panels": zoom_records,
                "comparison_contact_sheet": comparison_contact_record,
                "truth_region_contact_sheet": zoom_contact_record,
                "comparison_playback": playback_record,
                "final_frame_included": (
                    comparison_records[-1]["frame_index"]
                    == pilot.annotations.window.end_frame_index
                ),
            }
        )

    plan_snapshot_record = _asset_record(plan_snapshot_path, staging_dir)
    report_snapshot_record = _asset_record(scoring_snapshot_path, staging_dir)
    experiment_snapshot_record = _asset_record(
        experiment_snapshot_path,
        staging_dir,
    )
    heatmap_record = _asset_record(heatmap_path, staging_dir)
    heatmap_record.update(
        {
            "metrics": [
                "micro_precision",
                "micro_recall",
                "micro_f1_visualization_derived",
            ],
            "fixed_scale_minimum": 0.0,
            "fixed_scale_maximum": 1.0,
            "requested_cells_outlined": [
                {
                    "confidence_threshold": view.confidence_threshold,
                    "localization_radius_px": view.localization_radius_px,
                }
                for view in plan.views
            ],
            "winner_or_ranking_encoded": False,
            "visualization_only": True,
        }
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "asset_bundle_type": "ball_detection_candidate_visual_review",
        "bundle_input": {
            "bundle_input_sha256": digest,
            **bundle_components,
        },
        "review_plan": {
            "review_id": plan.review_id,
            "schema_version": plan.schema_version,
            "path": plan_relative.as_posix(),
            "purpose": plan.purpose,
            "views": [view.to_dict() for view in plan.views],
            "interpretation": dict(plan.interpretation),
            "snapshot": plan_snapshot_record,
        },
        "scoring_report": {
            "report_id": scoring_report["report_id"],
            "schema_version": scoring_report["schema_version"],
            "path": plan.scoring_report_path.as_posix(),
            "evaluator_code_commit": scoring_report["evaluator_code_commit"],
            "detector_code_commit": scoring_report["detector_code_commit"],
            "model_run_signature": scoring_report["model_run_signature"],
            "selected_operating_point": scoring_report[
                "selected_operating_point"
            ],
            "quality_gate": scoring_report["quality_gate"],
            "snapshot": report_snapshot_record,
            "experiment_manifest_snapshot": experiment_snapshot_record,
        },
        "safeguards": dict(SAFEGUARDS),
        "visual_conventions": dict(VISUAL_CONVENTIONS),
        "generator": {
            "module": "src.ball_tracking.prepare_detection_visual_review",
            "code_commit": bundle_components["renderer_code_commit"],
            "fingerprint_sha256": bundle_components[
                "generator_fingerprint_sha256"
            ],
            "fingerprint": dict(fingerprint),
        },
        "aggregate_grid": {
            "confidence_thresholds": scoring_report[
                "confidence_thresholds"
            ],
            "localization_radii_px": scoring_report[
                "localization_radii_px"
            ],
            "grid_cell_count": scoring_report["grid_cell_count"],
            "pilot_window_count": scoring_report["pilot_window_count"],
            "evaluation_report_count": scoring_report[
                "evaluation_report_count"
            ],
        },
        "pilots": pilot_records,
        "assets": {"pilot_metric_heatmaps": heatmap_record},
    }
    _write_json(staging_dir / "manifest.json", manifest)
    return manifest


def _load_json_closed(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as input_file:
            payload = json.load(
                input_file,
                object_pairs_hook=_reject_duplicate_keys,
            )
    except json.JSONDecodeError as error:
        raise DetectionVisualReviewError(
            f"Invalid JSON in visual-review manifest {path}: {error}"
        ) from error

    if not isinstance(payload, dict):
        raise DetectionVisualReviewError(
            "Detection visual-review manifest must be a JSON object"
        )

    return payload


def _portable_asset_path(
    bundle_dir: Path,
    value: Any,
    label: str,
) -> Path:
    raw = _require_string(value, f"{label}.path")

    if "\\" in raw:
        raise DetectionVisualReviewError(
            f"{label}.path must use portable forward slashes"
        )

    relative = PurePosixPath(raw)

    if (
        relative.is_absolute()
        or not relative.parts
        or "." in relative.parts
        or ".." in relative.parts
        or relative.as_posix() != raw
    ):
        raise DetectionVisualReviewError(f"{label}.path escapes the bundle")

    for component in relative.parts:
        device_basename = component.split(".", 1)[0].rstrip(" .").casefold()

        if (
            ":" in component
            or component.endswith((".", " "))
            or device_basename in WINDOWS_RESERVED_NAMES
        ):
            raise DetectionVisualReviewError(
                f"{label}.path contains a Windows-unsafe component "
                f"{component!r}"
            )

    path = bundle_dir.joinpath(*relative.parts)

    try:
        path.resolve().relative_to(bundle_dir.resolve())
    except ValueError as error:
        raise DetectionVisualReviewError(
            f"{label}.path escapes the bundle"
        ) from error

    return path


def _collect_asset_records(
    value: Any,
    *,
    label: str = "manifest",
) -> list[tuple[str, Mapping[str, Any]]]:
    records = []

    if isinstance(value, Mapping):
        if ASSET_BASE_FIELDS.issubset(value):
            records.append((label, value))

        for key, child in value.items():
            records.extend(
                _collect_asset_records(child, label=f"{label}.{key}")
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            records.extend(
                _collect_asset_records(child, label=f"{label}[{index}]")
            )

    return records


def validate_detection_visual_review_bundle_integrity(
    bundle_dir: Path,
    *,
    expected_digest: str | None = None,
) -> dict[str, Any]:
    """Validate closed structure and recorded hashes, not visual semantics.

    Semantic reuse validation is deliberately stronger: the preparation path
    regenerates every artifact under the fingerprinted runtime and compares
    complete tree signatures.  A caller needing proof of ordered visual
    content must rerun ``prepare_detection_visual_review`` with the exact
    bound inputs, rather than treating self-recorded hashes as an external
    trust anchor.
    """

    bundle_dir = bundle_dir.resolve()

    if not bundle_dir.is_dir():
        raise DetectionVisualReviewError(
            f"Detection visual-review bundle is not a directory: {bundle_dir}"
        )

    manifest_path = bundle_dir / "manifest.json"
    manifest = dict(
        _exact_fields(
            _load_json_closed(manifest_path),
            BUNDLE_TOP_LEVEL_FIELDS,
            "visual-review manifest",
        )
    )

    if manifest["schema_version"] != SCHEMA_VERSION:
        raise DetectionVisualReviewError(
            f"Visual-review schema_version must be {SCHEMA_VERSION!r}"
        )

    if manifest["asset_bundle_type"] != (
        "ball_detection_candidate_visual_review"
    ):
        raise DetectionVisualReviewError(
            "Visual-review asset_bundle_type is invalid"
        )

    bundle_input = manifest["bundle_input"]

    if not isinstance(bundle_input, Mapping):
        raise DetectionVisualReviewError("bundle_input must be a JSON object")

    digest = bundle_input.get("bundle_input_sha256")

    if not isinstance(digest, str) or len(digest) != 64:
        raise DetectionVisualReviewError(
            "bundle_input_sha256 must be a SHA-256 string"
        )

    recomputed_digest = _canonical_sha256(
        {
            key: value
            for key, value in bundle_input.items()
            if key != "bundle_input_sha256"
        }
    )

    if digest != recomputed_digest:
        raise DetectionVisualReviewError(
            "bundle_input_sha256 does not match bundle components"
        )

    if expected_digest is not None and digest != expected_digest:
        raise DetectionVisualReviewError(
            "Visual-review bundle digest does not match expected inputs"
        )

    if manifest["safeguards"] != SAFEGUARDS:
        raise DetectionVisualReviewError(
            "Visual-review safeguards do not match frozen semantics"
        )

    if manifest["visual_conventions"] != VISUAL_CONVENTIONS:
        raise DetectionVisualReviewError(
            "Visual-review conventions do not match frozen semantics"
        )

    pilots = manifest["pilots"]

    if not isinstance(pilots, list) or len(pilots) != EXPECTED_PILOT_COUNT:
        raise DetectionVisualReviewError(
            "Visual-review manifest must contain exactly 3 pilots"
        )

    possession_ids = []

    for pilot_index, pilot in enumerate(pilots):
        label = f"pilots[{pilot_index}]"

        if not isinstance(pilot, Mapping):
            raise DetectionVisualReviewError(f"{label} must be a JSON object")

        possession_ids.append(pilot.get("possession_id"))

        if pilot.get("final_frame_included") is not True:
            raise DetectionVisualReviewError(
                f"{label} does not prove final-frame inclusion"
            )

        window = pilot.get("window")
        comparison_frames = pilot.get("comparison_frames")
        truth_panels = pilot.get("truth_region_panels")
        views = pilot.get("views")

        if not isinstance(window, Mapping):
            raise DetectionVisualReviewError(f"{label}.window is invalid")

        start = window.get("start_frame_index")
        end = window.get("end_frame_index")
        expected_indices = list(range(start, end + 1))

        if len(expected_indices) != EXPECTED_FRAME_COUNT:
            raise DetectionVisualReviewError(
                f"{label}.window must contain exactly 25 frames"
            )

        for records, records_label in (
            (comparison_frames, "comparison_frames"),
            (truth_panels, "truth_region_panels"),
        ):
            if (
                not isinstance(records, list)
                or [record.get("frame_index") for record in records]
                != expected_indices
            ):
                raise DetectionVisualReviewError(
                    f"{label}.{records_label} must cover all 25 frames in order"
                )

        if not isinstance(views, list) or len(views) != EXPECTED_VIEW_COUNT:
            raise DetectionVisualReviewError(
                f"{label}.views must contain exactly 2 views"
            )

        for view_index, view in enumerate(views):
            overlays = view.get("overlay_frames")

            if (
                not isinstance(overlays, list)
                or [record.get("frame_index") for record in overlays]
                != expected_indices
            ):
                raise DetectionVisualReviewError(
                    f"{label}.views[{view_index}].overlay_frames must cover "
                    "all 25 frames in order"
                )

            if any(
                record.get("source_viewport_obscured_by_header_or_sidebar")
                is not False
                for record in overlays
            ):
                raise DetectionVisualReviewError(
                    f"{label}.views[{view_index}] obscures the source viewport"
                )

    if len(set(possession_ids)) != EXPECTED_PILOT_COUNT:
        raise DetectionVisualReviewError(
            "Visual-review pilots must have unique possession IDs"
        )

    asset_records = _collect_asset_records(manifest)
    recorded_paths = set()

    for label, record in asset_records:
        path = _portable_asset_path(bundle_dir, record["path"], label)
        relative = path.relative_to(bundle_dir).as_posix()

        if relative in recorded_paths:
            raise DetectionVisualReviewError(
                f"Asset path is recorded more than once: {relative}"
            )

        recorded_paths.add(relative)

        if path.is_symlink() or not path.is_file():
            raise DetectionVisualReviewError(
                f"Recorded visual-review asset is missing or unsafe: {relative}"
            )

        expected_sha = record["sha256"]
        expected_size = record["byte_size"]

        if (
            not isinstance(expected_sha, str)
            or len(expected_sha) != 64
            or isinstance(expected_size, bool)
            or not isinstance(expected_size, int)
            or expected_size < 0
        ):
            raise DetectionVisualReviewError(
                f"Recorded asset digest/size is invalid: {relative}"
            )

        if path.stat().st_size != expected_size or _sha256_file(path) != expected_sha:
            raise DetectionVisualReviewError(
                f"Recorded visual-review asset was modified: {relative}"
            )

    actual_files = set()

    for path in bundle_dir.rglob("*"):
        if path.is_symlink():
            raise DetectionVisualReviewError(
                "Visual-review bundle contains a symlink"
            )

        if path.is_file():
            actual_files.add(path.relative_to(bundle_dir).as_posix())

    expected_files = {"manifest.json", *recorded_paths}

    if actual_files != expected_files:
        raise DetectionVisualReviewError(
            "Visual-review bundle structure is not closed; "
            f"missing={sorted(expected_files - actual_files)}, "
            f"extra={sorted(actual_files - expected_files)}"
        )

    return manifest


def _tree_signature(root: Path) -> dict[str, tuple[int, str]]:
    """Describe a complete tree without retaining artifact bytes in memory."""

    result: dict[str, tuple[int, str]] = {}

    for path in root.rglob("*"):
        if path.is_symlink():
            raise DetectionVisualReviewError(
                f"Visual-review tree contains a symlink: {path}"
            )

        if path.is_file():
            result[path.relative_to(root).as_posix()] = (
                path.stat().st_size,
                _sha256_file(path),
            )

    return result


def _ensure_inputs_unchanged(
    plan_path: Path,
    plan_bytes: bytes,
    report_path: Path,
    report_bytes: bytes,
    experiment_manifest_path: Path,
    experiment_manifest_bytes: bytes,
    pilots: Sequence[PreparedVisualPilot],
    fingerprint: Mapping[str, str],
) -> None:
    if plan_path.read_bytes() != plan_bytes:
        raise DetectionVisualReviewError(
            "Review plan changed during rendering; nothing was published"
        )

    if report_path.read_bytes() != report_bytes:
        raise DetectionVisualReviewError(
            "Scoring report changed during rendering; nothing was published"
        )

    if experiment_manifest_path.read_bytes() != experiment_manifest_bytes:
        raise DetectionVisualReviewError(
            "Experiment manifest changed during rendering; nothing was published"
        )

    for pilot in pilots:
        if pilot.annotation_path.read_bytes() != pilot.annotation_bytes:
            raise DetectionVisualReviewError(
                "Annotation input changed during rendering; nothing was published"
            )

        if pilot.detection_path.read_bytes() != pilot.detection_bytes:
            raise DetectionVisualReviewError(
                "Detection input changed during rendering; nothing was published"
            )

        if _sha256_file(pilot.source_path) != pilot.source_bytes_sha256:
            raise DetectionVisualReviewError(
                "Source video changed during rendering; nothing was published"
            )

    if generator_fingerprint() != dict(fingerprint):
        raise DetectionVisualReviewError(
            "Renderer code or runtime changed during generation; nothing was published"
        )


def default_dependencies() -> VisualReviewDependencies:
    return VisualReviewDependencies(
        load_plan=load_detection_review_plan,
        load_experiment=load_detector_experiment,
        load_scoring_report=load_scoring_report,
        inspect_git=inspect_git_repository,
        verify_tracked_file=verify_tracked_file_at_head,
        is_git_ignored=is_git_ignored,
        load_annotation=load_annotations,
        load_detection=load_detection_run,
        verify_source=verify_source_video_contract,
        decode_window=_decode_window_sequentially,
        write_playback=_write_slow_playback,
    )


def prepare_detection_visual_review(
    review_plan_path: Path,
    repository_root: Path,
    *,
    dependencies: VisualReviewDependencies | None = None,
) -> DetectionVisualReviewSummary:
    """Build or exactly reuse one content-addressed comparison package."""

    deps = default_dependencies() if dependencies is None else dependencies
    root = repository_root.resolve()

    if not root.is_dir():
        raise DetectionVisualReviewError(
            f"Repository root does not exist: {root}"
        )

    plan_path, plan_relative = _resolve_review_plan_path(
        root,
        review_plan_path,
    )
    plan_bytes = plan_path.read_bytes()
    plan = deps.load_plan(plan_path)

    if plan_path.read_bytes() != plan_bytes:
        raise DetectionVisualReviewError("Review plan changed while loading")

    report_path = reject_unsafe_repository_path(
        root,
        plan.scoring_report_path,
        label="Detection scoring report path",
    )

    if (
        tuple(plan.scoring_report_path.parts[:5])
        != ("data", "outputs", "ball_tracking", "evaluations", plan.experiment_id)
        or plan.scoring_report_path.suffix != ".json"
    ):
        raise DetectionVisualReviewError(
            "Review plan scoring report is outside the experiment evaluation root"
        )

    if not deps.is_git_ignored(root, plan.scoring_report_path):
        raise DetectionVisualReviewError(
            "Detection scoring report must stay Git-ignored"
        )

    report_bytes = report_path.read_bytes()
    scoring_report = deps.load_scoring_report(report_path)

    if report_path.read_bytes() != report_bytes:
        raise DetectionVisualReviewError("Scoring report changed while loading")

    experiment_manifest_relative = _portable_json_path(
        scoring_report["experiment_manifest"]["path"],
        "scoring report experiment manifest path",
    )
    experiment_manifest_path = reject_unsafe_repository_path(
        root,
        experiment_manifest_relative,
        label="Scoring report experiment manifest path",
    )
    experiment_manifest_bytes = experiment_manifest_path.read_bytes()

    if _sha256_bytes(experiment_manifest_bytes) != scoring_report[
        "experiment_manifest"
    ]["byte_sha256"]:
        raise DetectionVisualReviewError(
            "Experiment manifest bytes no longer match scoring report"
        )

    experiment = deps.load_experiment(experiment_manifest_path)
    _validate_scoring_report_against_experiment(
        scoring_report,
        experiment,
        experiment_manifest_relative,
    )

    opening_snapshot = deps.inspect_git(root, experiment_manifest_relative)

    try:
        head = _validate_git_snapshot(
            opening_snapshot,
            root,
            experiment_manifest_relative,
        )
    except Exception as error:
        raise DetectionVisualReviewError(
            f"Visual-review Git preflight failed: {error}"
        ) from error

    deps.verify_tracked_file(root, plan_relative)
    pilots = _prepare_visual_pilots(plan, scoring_report, root, deps)
    fingerprint = generator_fingerprint()
    bundle_components = {
        "render_schema_version": SCHEMA_VERSION,
        "review_plan_path": plan_relative.as_posix(),
        "review_plan_sha256": _sha256_bytes(plan_bytes),
        "scoring_report_sha256": _sha256_bytes(report_bytes),
        "experiment_manifest_sha256": _sha256_bytes(
            experiment_manifest_bytes
        ),
        "generator_fingerprint_sha256": _canonical_sha256(fingerprint),
        "renderer_code_commit": head,
    }
    digest = _canonical_sha256(bundle_components)
    output_relative = PurePosixPath(
        *OUTPUT_ROOT_PARTS,
        plan.review_id,
        digest[:32],
    )
    output_dir = reject_unsafe_repository_path(
        root,
        output_relative,
        label="Detection visual-review output path",
    )

    if not deps.is_git_ignored(root, output_relative):
        raise DetectionVisualReviewError(
            "Detection visual-review output path must stay Git-ignored"
        )

    if output_dir.exists() and not output_dir.is_dir():
        raise DetectionVisualReviewError(
            f"Detection visual-review output is not a directory: {output_dir}"
        )

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(
        tempfile.mkdtemp(
            prefix=f".{digest[:12]}.staging-",
            dir=output_dir.parent,
        )
    )

    try:
        _write_bundle_assets(
            staging_dir,
            plan,
            scoring_report,
            plan_relative,
            plan_bytes,
            report_bytes,
            experiment_manifest_bytes,
            pilots,
            fingerprint,
            bundle_components,
            digest,
            deps.decode_window,
            deps.write_playback,
        )
        validate_detection_visual_review_bundle_integrity(
            staging_dir,
            expected_digest=digest,
        )
        _ensure_inputs_unchanged(
            plan_path,
            plan_bytes,
            report_path,
            report_bytes,
            experiment_manifest_path,
            experiment_manifest_bytes,
            pilots,
            fingerprint,
        )
        closing_snapshot = deps.inspect_git(
            root,
            experiment_manifest_relative,
        )

        try:
            closing_head = _validate_git_snapshot(
                closing_snapshot,
                root,
                experiment_manifest_relative,
            )
        except Exception as error:
            raise DetectionVisualReviewError(
                f"Closing Git validation failed: {error}"
            ) from error

        if closing_head != head:
            raise DetectionVisualReviewError(
                "Git HEAD changed during rendering; nothing was published"
            )

        reject_unsafe_repository_path(
            root,
            output_relative,
            label="Detection visual-review output path",
        )

        if output_dir.exists():
            validate_detection_visual_review_bundle_integrity(
                output_dir,
                expected_digest=digest,
            )

            if _tree_signature(output_dir) != _tree_signature(staging_dir):
                raise DetectionVisualReviewError(
                    "Existing content-addressed visual-review bundle conflicts "
                    "with exact regenerated assets"
                )

            reused = True
        else:
            try:
                staging_dir.rename(output_dir)
            except OSError:
                if not output_dir.exists():
                    raise

                validate_detection_visual_review_bundle_integrity(
                    output_dir,
                    expected_digest=digest,
                )

                if _tree_signature(output_dir) != _tree_signature(staging_dir):
                    raise DetectionVisualReviewError(
                        "Concurrent visual-review publication conflicts with "
                        "exact regenerated assets"
                    )

                reused = True
            else:
                reused = False

        return DetectionVisualReviewSummary(
            head=head,
            output_dir=output_dir,
            reused_existing=reused,
            pilot_count=len(pilots),
            view_count=len(plan.views),
            rendered_frame_count=len(pilots) * EXPECTED_FRAME_COUNT,
        )
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build an immutable, synchronized candidate-versus-truth review "
            "for the descriptive detector settings in a committed review plan."
        )
    )
    parser.add_argument("--review-plan", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)

    try:
        summary = prepare_detection_visual_review(
            args.review_plan,
            args.repository_root,
        )
    except (
        DetectionVisualReviewError,
        DetectorExperimentScoringError,
        DetectorExperimentRunnerError,
        AnnotationVisualReviewError,
        ReviewAssetPreparationError,
        FileNotFoundError,
        OSError,
        ValueError,
    ) as error:
        raise SystemExit(
            f"Ball detection visual-review error: {error}"
        ) from error

    action = "reused" if summary.reused_existing else "created"
    print(
        "Ball detection visual-review package is ready: "
        f"pilots={summary.pilot_count}, views={summary.view_count}, "
        f"source_frames={summary.rendered_frame_count}, "
        f"artifact={action}, head={summary.head}"
    )
    print(f"Output directory: {summary.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
