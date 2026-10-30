"""Auditable ball-tracking annotation and evaluation foundations."""

from .annotations import (
    AnnotationValidationError,
    BallAnnotationSet,
    BallGeometry,
    FrameAnnotation,
    SourceVideo,
    load_annotations,
    verify_source_video,
    verify_source_video_contract,
)
from .detections import (
    BallDetectionRun,
    DetectionRunValidationError,
    load_detection_run,
)
from .evaluation import (
    DetectionEvaluationError,
    aggregate_evaluation_reports,
    evaluate_detections,
)

__all__ = [
    "AnnotationValidationError",
    "BallAnnotationSet",
    "BallGeometry",
    "BallDetectionRun",
    "DetectionEvaluationError",
    "DetectionRunValidationError",
    "FrameAnnotation",
    "SourceVideo",
    "aggregate_evaluation_reports",
    "evaluate_detections",
    "load_annotations",
    "load_detection_run",
    "verify_source_video",
    "verify_source_video_contract",
]
