"""Score the three reviewed detector pilots on the frozen manifest grid.

The detector runner is intentionally label blind.  This module is the separate
post-inference boundary that may read reviewed annotations.  It scores only the
manifest's ``ready_for_inference`` windows, preserves every full evaluator
report, and publishes one deterministic, content-bound JSON bundle.

The bundle is descriptive pilot evidence.  It never selects an operating point,
defines a quality gate, or opens prediction-embargoed evaluation windows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

from .annotations import (
    BallAnnotationSet,
    SourceVideo,
    load_annotations,
    verify_source_video_contract,
)
from .detections import BallDetectionRun, load_detection_run
from .detector_experiments import (
    PROTOCOL_PURPOSE,
    DetectorExperiment,
    ExperimentWindow,
    build_model_provenance,
    load_detector_experiment,
)
from .evaluation import aggregate_evaluation_reports, evaluate_detections
from .run_detector_experiment import (
    GitSnapshot,
    _reject_symlink_components,
    _resolve_manifest_path,
    _run_git,
    _validate_git_snapshot,
    inspect_git_repository,
    is_git_ignored,
)


SCHEMA_VERSION = "ball_detector_scoring_grid/v0.1"
REPORT_FILENAME = "protocol_adjudication_grid_v0_1.json"
ANNOTATION_ROOT_PARTS = ("configs", "ball_tracking", "annotations")
OUTPUT_ROOT_PARTS = ("data", "outputs", "ball_tracking", "evaluations")
WINDOWS_RESERVED_NAMES = {
    "aux",
    "con",
    "nul",
    "prn",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}
EVALUATOR_SOURCE_PATHS = tuple(
    PurePosixPath("src", "ball_tracking", filename)
    for filename in (
        "score_detector_experiment.py",
        "evaluation.py",
        "annotations.py",
        "detections.py",
        "detector_experiments.py",
        "rfdetr_adapter.py",
        "run_detector_experiment.py",
    )
)

TOP_LEVEL_FIELDS = frozenset(
    {
        "schema_version",
        "report_id",
        "experiment_id",
        "experiment_manifest",
        "evaluator_code_commit",
        "detector_code_commit",
        "selection_purpose",
        "confidence_thresholds",
        "localization_radii_px",
        "pilot_window_count",
        "grid_cell_count",
        "evaluation_report_count",
        "model_run_signature",
        "pilot_inputs",
        "evaluation_reports",
        "aggregate_results",
        "selected_operating_point",
        "quality_gate",
        "interpretation_constraints",
    }
)
MANIFEST_BINDING_FIELDS = frozenset(
    {"path", "byte_sha256", "canonical_content_sha256"}
)
PILOT_INPUT_FIELDS = frozenset(
    {
        "window_id",
        "annotation_set_id",
        "annotation_path",
        "annotation_file_sha256",
        "annotation_content_sha256",
        "detection_run_id",
        "detection_path",
        "detection_file_sha256",
        "detection_run_content_sha256",
        "possession_id",
        "source_video_path",
        "source_video_sha256",
        "window_start_frame_index",
        "window_end_frame_index",
    }
)
AGGREGATE_RESULT_FIELDS = frozenset(
    {"confidence_threshold", "localization_radius_px", "aggregate"}
)
INTERPRETATION_CONSTRAINTS = {
    "status": "descriptive_protocol_pilot_grid",
    "operating_point_selection_allowed": False,
    "quality_gate_claim_allowed": False,
    "generalization_claim_allowed": False,
    "embargoed_window_predictions_accessed": False,
}


class DetectorExperimentScoringError(RuntimeError):
    """Raised when a pilot-grid score bundle cannot be trusted."""


@dataclass(frozen=True)
class PreparedPilot:
    window: ExperimentWindow
    annotation_path: Path
    annotation_bytes: bytes
    annotations: BallAnnotationSet
    detection_path: Path
    detection_bytes: bytes
    detections: BallDetectionRun


@dataclass(frozen=True)
class ScoringSummary:
    head: str
    output_path: Path
    reused_existing: bool
    pilot_window_count: int
    grid_cell_count: int
    evaluation_report_count: int


ExperimentLoader = Callable[[Path], DetectorExperiment]
GitInspector = Callable[[Path, PurePosixPath], GitSnapshot]
TrackedFileVerifier = Callable[[Path, PurePosixPath], None]
CommitAncestorVerifier = Callable[[Path, str, str, PurePosixPath], None]
SourceVerifier = Callable[[SourceVideo, Path], dict[str, Any]]
IgnoreChecker = Callable[[Path, PurePosixPath], bool]
AnnotationLoader = Callable[[Path], BallAnnotationSet]
DetectionLoader = Callable[[Path], BallDetectionRun]
Evaluator = Callable[..., dict[str, Any]]
Aggregator = Callable[[Sequence[Mapping[str, Any]]], dict[str, Any]]
ReportWriter = Callable[[Mapping[str, Any], Path], None]


@dataclass(frozen=True)
class ScoringDependencies:
    load_experiment: ExperimentLoader
    inspect_git: GitInspector
    verify_tracked_file: TrackedFileVerifier
    verify_commit_ancestor: CommitAncestorVerifier
    verify_source: SourceVerifier
    is_git_ignored: IgnoreChecker
    load_annotation: AnnotationLoader
    load_detection: DetectionLoader
    evaluate: Evaluator
    aggregate: Aggregator
    write_report: ReportWriter


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _serialized_report(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise DetectorExperimentScoringError(
                f"duplicate JSON key in scoring report: {key!r}"
            )

        result[key] = value

    return result


def _exact_fields(
    value: Any,
    expected: frozenset[str],
    label: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DetectorExperimentScoringError(f"{label} must be a JSON object")

    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)

    if missing or extra:
        raise DetectorExperimentScoringError(
            f"{label} fields are not closed; missing={missing}, extra={extra}"
        )

    return value


def _require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DetectorExperimentScoringError(
            f"{label} must be a non-empty string"
        )

    return value


def _require_sha256(value: Any, label: str) -> str:
    result = _require_nonempty_string(value, label)

    if len(result) != 64 or any(
        character not in "0123456789abcdef" for character in result
    ):
        raise DetectorExperimentScoringError(
            f"{label} must be 64 lowercase hexadecimal characters"
        )

    return result


def _require_commit(value: Any, label: str) -> str:
    result = _require_nonempty_string(value, label)

    if len(result) != 40 or any(
        character not in "0123456789abcdef" for character in result
    ):
        raise DetectorExperimentScoringError(
            f"{label} must be 40 lowercase hexadecimal characters"
        )

    return result


def _require_nonnegative_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DetectorExperimentScoringError(
            f"{label} must be a non-negative integer"
        )

    return value


def _require_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DetectorExperimentScoringError(f"{label} must be numeric")

    result = float(value)

    if not (result == result and abs(result) != float("inf")):
        raise DetectorExperimentScoringError(f"{label} must be finite")

    return result


def _require_grid(value: Any, label: str) -> tuple[float, ...]:
    if not isinstance(value, list) or not value:
        raise DetectorExperimentScoringError(
            f"{label} must be a non-empty JSON array"
        )

    grid = tuple(
        _require_number(item, f"{label}[{index}]")
        for index, item in enumerate(value)
    )

    if any(left >= right for left, right in zip(grid, grid[1:])):
        raise DetectorExperimentScoringError(
            f"{label} must be strictly increasing"
        )

    return grid


def _require_portable_path(value: Any, label: str) -> PurePosixPath:
    raw = _require_nonempty_string(value, label)

    if "\\" in raw:
        raise DetectorExperimentScoringError(
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
        raise DetectorExperimentScoringError(
            f"{label} must be a normalized repository-relative path"
        )

    for component in path.parts:
        device_basename = component.split(".", 1)[0].rstrip(" .").casefold()

        if (
            ":" in component
            or component.endswith((".", " "))
            or device_basename in WINDOWS_RESERVED_NAMES
        ):
            raise DetectorExperimentScoringError(
                f"{label} contains a Windows-unsafe path component "
                f"{component!r}"
            )

    return path


def _require_portable_json_path(value: Any, label: str) -> PurePosixPath:
    path = _require_portable_path(value, label)

    if path.suffix != ".json":
        raise DetectorExperimentScoringError(f"{label} must be a JSON path")

    return path


def load_scoring_report(path: Path) -> dict[str, Any]:
    """Load and strictly validate one durable grid report."""

    report_path = path.resolve()

    if not report_path.is_file():
        raise FileNotFoundError(
            f"Detector scoring report not found: {report_path}"
        )

    try:
        with report_path.open("r", encoding="utf-8") as input_file:
            payload = json.load(
                input_file,
                object_pairs_hook=_reject_duplicate_keys,
            )
    except json.JSONDecodeError as error:
        raise DetectorExperimentScoringError(
            f"Invalid JSON in detector scoring report {report_path}: {error}"
        ) from error

    return validate_scoring_report(payload)


def validate_scoring_report(value: Any) -> dict[str, Any]:
    """Validate the closed bundle schema and every aggregate relationship."""

    report = dict(_exact_fields(value, TOP_LEVEL_FIELDS, "scoring report"))

    if report["schema_version"] != SCHEMA_VERSION:
        raise DetectorExperimentScoringError(
            f"schema_version must be {SCHEMA_VERSION!r}"
        )

    report_id = _require_nonempty_string(report["report_id"], "report_id")
    experiment_id = _require_nonempty_string(
        report["experiment_id"],
        "experiment_id",
    )

    if report_id != f"{experiment_id}_protocol_adjudication_grid_v0_1":
        raise DetectorExperimentScoringError(
            "report_id does not match experiment_id and report version"
        )
    manifest = _exact_fields(
        report["experiment_manifest"],
        MANIFEST_BINDING_FIELDS,
        "experiment_manifest",
    )
    manifest_path = _require_portable_json_path(
        manifest["path"],
        "experiment_manifest.path",
    )

    if (
        tuple(manifest_path.parts[:3])
        != ("configs", "ball_tracking", "experiments")
        or len(manifest_path.parts) != 4
    ):
        raise DetectorExperimentScoringError(
            "experiment_manifest.path must name one experiment registry JSON"
        )
    _require_sha256(manifest["byte_sha256"], "experiment_manifest.byte_sha256")
    _require_sha256(
        manifest["canonical_content_sha256"],
        "experiment_manifest.canonical_content_sha256",
    )
    _require_commit(report["evaluator_code_commit"], "evaluator_code_commit")
    detector_commit = _require_commit(
        report["detector_code_commit"],
        "detector_code_commit",
    )

    if report["selection_purpose"] != PROTOCOL_PURPOSE:
        raise DetectorExperimentScoringError(
            f"selection_purpose must be {PROTOCOL_PURPOSE!r}"
        )

    thresholds = _require_grid(
        report["confidence_thresholds"],
        "confidence_thresholds",
    )
    radii = _require_grid(
        report["localization_radii_px"],
        "localization_radii_px",
    )

    if thresholds[0] < 0.0 or thresholds[-1] > 1.0:
        raise DetectorExperimentScoringError(
            "confidence_thresholds must stay within [0, 1]"
        )

    if radii[0] <= 0.0:
        raise DetectorExperimentScoringError(
            "localization_radii_px values must be positive"
        )

    pilot_count = _require_nonnegative_integer(
        report["pilot_window_count"],
        "pilot_window_count",
    )
    grid_cell_count = _require_nonnegative_integer(
        report["grid_cell_count"],
        "grid_cell_count",
    )
    evaluation_report_count = _require_nonnegative_integer(
        report["evaluation_report_count"],
        "evaluation_report_count",
    )

    if pilot_count != 3:
        raise DetectorExperimentScoringError(
            "pilot_window_count must be exactly 3"
        )

    expected_cell_count = len(thresholds) * len(radii)

    if grid_cell_count != expected_cell_count:
        raise DetectorExperimentScoringError(
            "grid_cell_count does not match the declared grids"
        )

    if evaluation_report_count != pilot_count * grid_cell_count:
        raise DetectorExperimentScoringError(
            "evaluation_report_count does not match pilots x grid cells"
        )

    model_signature = _require_sha256(
        report["model_run_signature"],
        "model_run_signature",
    )
    pilot_inputs = report["pilot_inputs"]

    if not isinstance(pilot_inputs, list) or len(pilot_inputs) != pilot_count:
        raise DetectorExperimentScoringError(
            "pilot_inputs must contain exactly 3 entries"
        )

    normalized_inputs = []

    for index, raw_input in enumerate(pilot_inputs):
        label = f"pilot_inputs[{index}]"
        item = dict(_exact_fields(raw_input, PILOT_INPUT_FIELDS, label))

        for field in (
            "window_id",
            "annotation_set_id",
            "detection_run_id",
            "possession_id",
        ):
            _require_nonempty_string(item[field], f"{label}.{field}")

        annotation_path = _require_portable_json_path(
            item["annotation_path"],
            f"{label}.annotation_path",
        )
        expected_annotation_path = PurePosixPath(
            *ANNOTATION_ROOT_PARTS,
            f"{item['annotation_set_id']}.json",
        )

        if annotation_path != expected_annotation_path:
            raise DetectorExperimentScoringError(
                f"{label}.annotation_path must be derived from annotation_set_id"
            )

        detection_path = _require_portable_json_path(
            item["detection_path"],
            f"{label}.detection_path",
        )

        if (
            tuple(detection_path.parts[:5])
            != (
                "data",
                "outputs",
                "ball_tracking",
                "detections",
                experiment_id,
            )
            or len(detection_path.parts) != 6
        ):
            raise DetectorExperimentScoringError(
                f"{label}.detection_path must stay in the experiment detector root"
            )

        _require_portable_path(
            item["source_video_path"],
            f"{label}.source_video_path",
        )

        for field in (
            "annotation_file_sha256",
            "annotation_content_sha256",
            "detection_file_sha256",
            "detection_run_content_sha256",
            "source_video_sha256",
        ):
            _require_sha256(item[field], f"{label}.{field}")

        start = _require_nonnegative_integer(
            item["window_start_frame_index"],
            f"{label}.window_start_frame_index",
        )
        end = _require_nonnegative_integer(
            item["window_end_frame_index"],
            f"{label}.window_end_frame_index",
        )

        if end < start:
            raise DetectorExperimentScoringError(
                f"{label} window end precedes start"
            )

        normalized_inputs.append(item)

    for field in (
        "window_id",
        "annotation_set_id",
        "annotation_content_sha256",
        "detection_run_id",
        "detection_run_content_sha256",
        "possession_id",
        "source_video_path",
        "source_video_sha256",
    ):
        values = [item[field] for item in normalized_inputs]

        if len(set(values)) != len(values):
            raise DetectorExperimentScoringError(
                f"pilot_inputs must have unique {field} values"
            )

    evaluation_reports = report["evaluation_reports"]
    aggregate_results = report["aggregate_results"]

    if (
        not isinstance(evaluation_reports, list)
        or len(evaluation_reports) != evaluation_report_count
    ):
        raise DetectorExperimentScoringError(
            "evaluation_reports length does not match its declared count"
        )

    if (
        not isinstance(aggregate_results, list)
        or len(aggregate_results) != grid_cell_count
    ):
        raise DetectorExperimentScoringError(
            "aggregate_results length does not match its declared count"
        )

    input_annotation_ids = [
        item["annotation_set_id"] for item in normalized_inputs
    ]
    report_position = 0
    aggregate_position = 0

    for threshold in thresholds:
        for radius in radii:
            cell_reports = evaluation_reports[
                report_position : report_position + pilot_count
            ]
            report_position += pilot_count
            cell_annotation_ids = [
                candidate.get("annotation_set_id")
                if isinstance(candidate, Mapping)
                else None
                for candidate in cell_reports
            ]

            if cell_annotation_ids != input_annotation_ids:
                raise DetectorExperimentScoringError(
                    "evaluation_reports are not in deterministic cell/pilot order"
                )

            for pilot_index, candidate in enumerate(cell_reports):
                if not isinstance(candidate, Mapping):
                    raise DetectorExperimentScoringError(
                        "evaluation_reports entries must be JSON objects"
                    )

                input_record = normalized_inputs[pilot_index]
                expected_fields = {
                    "annotation_content_sha256": input_record[
                        "annotation_content_sha256"
                    ],
                    "detection_run_id": input_record["detection_run_id"],
                    "detection_run_content_sha256": input_record[
                        "detection_run_content_sha256"
                    ],
                    "possession_id": input_record["possession_id"],
                    "source_video_sha256": input_record[
                        "source_video_sha256"
                    ],
                    "source_video_path": input_record["source_video_path"],
                    "window_start_frame_index": input_record[
                        "window_start_frame_index"
                    ],
                    "window_end_frame_index": input_record[
                        "window_end_frame_index"
                    ],
                    "selection_purpose": PROTOCOL_PURPOSE,
                    "confidence_threshold": threshold,
                    "localization_radius_px": radius,
                    "model_run_signature": model_signature,
                }

                for field, expected in expected_fields.items():
                    if candidate.get(field) != expected:
                        raise DetectorExperimentScoringError(
                            "evaluation report binding mismatch at "
                            f"threshold={threshold}, radius={radius}, "
                            f"pilot={pilot_index}, field={field}"
                        )

                provenance = candidate.get("model_provenance")

                if (
                    not isinstance(provenance, Mapping)
                    or provenance.get("code_commit") != detector_commit
                ):
                    raise DetectorExperimentScoringError(
                        "evaluation report detector_code_commit mismatch"
                    )

            try:
                recomputed_aggregate = aggregate_evaluation_reports(cell_reports)
            except Exception as error:
                raise DetectorExperimentScoringError(
                    "evaluation_reports failed strict aggregate validation: "
                    f"{error}"
                ) from error

            aggregate_record = _exact_fields(
                aggregate_results[aggregate_position],
                AGGREGATE_RESULT_FIELDS,
                f"aggregate_results[{aggregate_position}]",
            )
            aggregate_position += 1

            if (
                aggregate_record["confidence_threshold"] != threshold
                or aggregate_record["localization_radius_px"] != radius
                or aggregate_record["aggregate"] != recomputed_aggregate
            ):
                raise DetectorExperimentScoringError(
                    "aggregate_results do not exactly match evaluation_reports"
                )

    if report["selected_operating_point"] is not None:
        raise DetectorExperimentScoringError(
            "selected_operating_point must remain null for pilot scoring"
        )

    if report["quality_gate"] is not None:
        raise DetectorExperimentScoringError(
            "quality_gate must remain null for the first baseline"
        )

    if report["interpretation_constraints"] != INTERPRETATION_CONSTRAINTS:
        raise DetectorExperimentScoringError(
            "interpretation_constraints do not match the frozen pilot semantics"
        )

    return report


def verify_tracked_file_at_head(
    repository_root: Path,
    relative_path: PurePosixPath,
) -> None:
    """Require one repository-relative file to match its exact HEAD blob."""

    path = reject_unsafe_repository_path(
        repository_root,
        relative_path,
        label=f"Tracked scoring input {relative_path}",
    )

    if not path.is_file():
        raise DetectorExperimentScoringError(
            f"Tracked scoring input does not exist: {path}"
        )

    tracked = _run_git(
        repository_root,
        "ls-files",
        "--error-unmatch",
        "--",
        relative_path.as_posix(),
    )

    if tracked.returncode != 0:
        raise DetectorExperimentScoringError(
            f"Scoring input must be tracked at Git HEAD: {relative_path}"
        )

    worktree_blob = _run_git(
        repository_root,
        "hash-object",
        "--",
        relative_path.as_posix(),
    )
    head_blob = _run_git(
        repository_root,
        "rev-parse",
        f"HEAD:{relative_path.as_posix()}",
    )

    if worktree_blob.returncode != 0 or head_blob.returncode != 0:
        raise DetectorExperimentScoringError(
            f"Could not bind scoring input to Git HEAD: {relative_path}"
        )

    if worktree_blob.stdout.strip() != head_blob.stdout.strip():
        raise DetectorExperimentScoringError(
            f"Scoring input bytes do not match Git HEAD: {relative_path}"
        )


def _has_windows_reparse_point(path: Path) -> bool:
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False

    return bool(attributes & 0x400)


def reject_unsafe_repository_path(
    repository_root: Path,
    relative_path: PurePosixPath,
    *,
    label: str,
) -> Path:
    """Reject lexical escapes, symlinks, and Windows junction/reparse paths."""

    path = _reject_symlink_components(
        repository_root,
        relative_path,
        label=label,
    )
    current = repository_root

    for part in relative_path.parts:
        current = current / part

        if current.exists() and _has_windows_reparse_point(current):
            raise DetectorExperimentScoringError(
                f"{label} must not traverse a Windows reparse/junction: {current}"
            )

    return path


def verify_git_commit_ancestor(
    repository_root: Path,
    ancestor_commit: str,
    descendant_commit: str,
    manifest_relative_path: PurePosixPath,
) -> None:
    """Require a reachable detector commit with the exact experiment manifest."""

    result = _run_git(
        repository_root,
        "merge-base",
        "--is-ancestor",
        ancestor_commit,
        descendant_commit,
    )

    if result.returncode == 0:
        worktree_blob = _run_git(
            repository_root,
            "hash-object",
            "--",
            manifest_relative_path.as_posix(),
        )
        detector_blob = _run_git(
            repository_root,
            "rev-parse",
            f"{ancestor_commit}:{manifest_relative_path.as_posix()}",
        )

        if worktree_blob.returncode != 0 or detector_blob.returncode != 0:
            detail = (
                detector_blob.stderr.strip()
                or detector_blob.stdout.strip()
                or worktree_blob.stderr.strip()
                or worktree_blob.stdout.strip()
            )
            raise DetectorExperimentScoringError(
                "Detector commit does not contain the scored experiment manifest"
                + (f": {detail}" if detail else "")
            )

        if worktree_blob.stdout.strip() != detector_blob.stdout.strip():
            raise DetectorExperimentScoringError(
                "Detector commit experiment manifest differs from the exact "
                "manifest being scored"
            )

        return

    detail = result.stderr.strip() or result.stdout.strip()

    if result.returncode == 1:
        raise DetectorExperimentScoringError(
            "Detector code commit is not an ancestor of evaluator HEAD: "
            f"detector={ancestor_commit}, evaluator={descendant_commit}"
        )

    raise DetectorExperimentScoringError(
        "Git could not verify detector/evaluator commit ancestry"
        + (f": {detail}" if detail else "")
    )


def _annotation_relative_path(window: ExperimentWindow) -> PurePosixPath:
    return PurePosixPath(
        *ANNOTATION_ROOT_PARTS,
        f"{window.annotation_set_id}.json",
    )


def _verify_evaluator_sources(
    repository_root: Path,
    dependencies: ScoringDependencies,
) -> None:
    for relative_path in EVALUATOR_SOURCE_PATHS:
        dependencies.verify_tracked_file(repository_root, relative_path)


def _output_relative_path(experiment: DetectorExperiment) -> PurePosixPath:
    return PurePosixPath(
        *OUTPUT_ROOT_PARTS,
        experiment.experiment_id,
        REPORT_FILENAME,
    )


def _validate_window_binding(
    experiment: DetectorExperiment,
    window: ExperimentWindow,
    annotations: BallAnnotationSet,
    detections: BallDetectionRun,
) -> None:
    annotation_expected = {
        "annotation_set_id": window.annotation_set_id,
        "possession_id": window.possession_id,
        "source_video": window.source_video.to_dict(),
        "window_start": window.start_frame_index,
        "window_end": window.end_frame_index,
        "selection_purpose": window.selection_purpose,
    }
    annotation_actual = {
        "annotation_set_id": annotations.annotation_set_id,
        "possession_id": annotations.possession_id,
        "source_video": annotations.source_video.to_dict(),
        "window_start": annotations.window.start_frame_index,
        "window_end": annotations.window.end_frame_index,
        "selection_purpose": annotations.window.selection_purpose,
    }

    if annotation_actual != annotation_expected:
        raise DetectorExperimentScoringError(
            f"Annotation binding conflicts with manifest window {window.window_id!r}"
        )

    if annotations.review.status != "reviewed":
        raise DetectorExperimentScoringError(
            f"Annotation set {annotations.annotation_set_id!r} is not reviewed"
        )

    detection_expected = {
        "detection_run_id": window.detection_run_id,
        "annotation_set_id": window.annotation_set_id,
        "possession_id": window.possession_id,
        "source_video": window.source_video.to_dict(),
        "window_start": window.start_frame_index,
        "window_end": window.end_frame_index,
    }
    detection_actual = {
        "detection_run_id": detections.detection_run_id,
        "annotation_set_id": detections.annotation_set_id,
        "possession_id": detections.possession_id,
        "source_video": detections.source_video.to_dict(),
        "window_start": detections.window.start_frame_index,
        "window_end": detections.window.end_frame_index,
    }

    if detection_actual != detection_expected:
        raise DetectorExperimentScoringError(
            f"Detection binding conflicts with manifest window {window.window_id!r}"
        )

    incomplete = [
        frame.frame_index
        for frame in detections.frames
        if frame.inference_status != "completed"
    ]

    if incomplete:
        raise DetectorExperimentScoringError(
            f"Detection run {detections.detection_run_id!r} is incomplete at "
            f"frames {incomplete}"
        )

    provenance = detections.model_provenance
    expected_provenance = build_model_provenance(
        experiment.detector,
        code_commit=provenance.code_commit,
        runtime_device=provenance.device,
    )

    if provenance != expected_provenance:
        raise DetectorExperimentScoringError(
            f"Detection provenance conflicts with frozen detector for "
            f"{detections.detection_run_id!r}"
        )


def _prepare_pilots(
    experiment: DetectorExperiment,
    repository_root: Path,
    dependencies: ScoringDependencies,
) -> tuple[PreparedPilot, ...]:
    windows = experiment.windows_for_inference()

    if (
        len(windows) != 3
        or any(window.selection_purpose != PROTOCOL_PURPOSE for window in windows)
    ):
        raise DetectorExperimentScoringError(
            "Scoring requires exactly the 3 manifest-authorized protocol pilots"
        )

    prepared = []
    verified_sources: set[str] = set()
    model_provenance = None

    for window in windows:
        annotation_relative = _annotation_relative_path(window)
        dependencies.verify_tracked_file(repository_root, annotation_relative)
        annotation_path = reject_unsafe_repository_path(
            repository_root,
            annotation_relative,
            label=f"Annotation path for {window.window_id}",
        )
        annotation_bytes = annotation_path.read_bytes()
        annotations = dependencies.load_annotation(annotation_path)

        if annotation_path.read_bytes() != annotation_bytes:
            raise DetectorExperimentScoringError(
                f"Annotation input changed while loading: {annotation_relative}"
            )

        detection_path = reject_unsafe_repository_path(
            repository_root,
            window.output_path,
            label=f"Detection path for {window.window_id}",
        )

        if not dependencies.is_git_ignored(
            repository_root,
            window.output_path,
        ):
            raise DetectorExperimentScoringError(
                f"Detection output is not Git-ignored: {window.output_path}"
            )

        detection_bytes = detection_path.read_bytes()
        detections = dependencies.load_detection(detection_path)

        if detection_path.read_bytes() != detection_bytes:
            raise DetectorExperimentScoringError(
                f"Detection input changed while loading: {window.output_path}"
            )

        _validate_window_binding(
            experiment,
            window,
            annotations,
            detections,
        )

        if window.source_video.sha256 not in verified_sources:
            dependencies.verify_source(window.source_video, repository_root)
            verified_sources.add(window.source_video.sha256)

        if model_provenance is None:
            model_provenance = detections.model_provenance
        elif detections.model_provenance != model_provenance:
            raise DetectorExperimentScoringError(
                "All three pilot detections must share identical model provenance"
            )

        prepared.append(
            PreparedPilot(
                window=window,
                annotation_path=annotation_path,
                annotation_bytes=annotation_bytes,
                annotations=annotations,
                detection_path=detection_path,
                detection_bytes=detection_bytes,
                detections=detections,
            )
        )

    return tuple(prepared)


def build_scoring_report(
    experiment: DetectorExperiment,
    manifest_relative_path: PurePosixPath,
    manifest_bytes: bytes,
    evaluator_code_commit: str,
    pilots: Sequence[PreparedPilot],
    *,
    evaluate: Evaluator = evaluate_detections,
    aggregate: Aggregator = aggregate_evaluation_reports,
) -> dict[str, Any]:
    """Build and internally validate the deterministic full-grid report."""

    if len(pilots) != 3:
        raise DetectorExperimentScoringError(
            "Exactly 3 prepared pilots are required"
        )

    thresholds = experiment.scoring_grid.confidence_thresholds
    radii = experiment.scoring_grid.localization_radii_px
    evaluation_reports = []
    aggregate_results = []

    for threshold in thresholds:
        for radius in radii:
            cell_reports = [
                evaluate(
                    pilot.annotations,
                    pilot.detections,
                    confidence_threshold=threshold,
                    localization_radius_px=radius,
                )
                for pilot in pilots
            ]
            cell_aggregate = aggregate(cell_reports)
            evaluation_reports.extend(cell_reports)
            aggregate_results.append(
                {
                    "confidence_threshold": threshold,
                    "localization_radius_px": radius,
                    "aggregate": cell_aggregate,
                }
            )

    first_reports = evaluation_reports[: len(pilots)]
    model_signature = first_reports[0]["model_run_signature"]
    detector_code_commit = first_reports[0]["model_provenance"]["code_commit"]
    pilot_inputs = []

    for pilot, evaluation_report in zip(pilots, first_reports, strict=True):
        pilot_inputs.append(
            {
                "window_id": pilot.window.window_id,
                "annotation_set_id": pilot.window.annotation_set_id,
                "annotation_path": _annotation_relative_path(
                    pilot.window
                ).as_posix(),
                "annotation_file_sha256": hashlib.sha256(
                    pilot.annotation_bytes
                ).hexdigest(),
                "annotation_content_sha256": evaluation_report[
                    "annotation_content_sha256"
                ],
                "detection_run_id": pilot.window.detection_run_id,
                "detection_path": pilot.window.output_path.as_posix(),
                "detection_file_sha256": hashlib.sha256(
                    pilot.detection_bytes
                ).hexdigest(),
                "detection_run_content_sha256": evaluation_report[
                    "detection_run_content_sha256"
                ],
                "possession_id": pilot.window.possession_id,
                "source_video_path": pilot.window.source_video.path.as_posix(),
                "source_video_sha256": pilot.window.source_video.sha256,
                "window_start_frame_index": pilot.window.start_frame_index,
                "window_end_frame_index": pilot.window.end_frame_index,
            }
        )

    report = {
        "schema_version": SCHEMA_VERSION,
        "report_id": (
            f"{experiment.experiment_id}_protocol_adjudication_grid_v0_1"
        ),
        "experiment_id": experiment.experiment_id,
        "experiment_manifest": {
            "path": manifest_relative_path.as_posix(),
            "byte_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "canonical_content_sha256": _canonical_sha256(
                experiment.to_dict()
            ),
        },
        "evaluator_code_commit": evaluator_code_commit,
        "detector_code_commit": detector_code_commit,
        "selection_purpose": PROTOCOL_PURPOSE,
        "confidence_thresholds": list(thresholds),
        "localization_radii_px": list(radii),
        "pilot_window_count": len(pilots),
        "grid_cell_count": len(thresholds) * len(radii),
        "evaluation_report_count": len(evaluation_reports),
        "model_run_signature": model_signature,
        "pilot_inputs": pilot_inputs,
        "evaluation_reports": evaluation_reports,
        "aggregate_results": aggregate_results,
        "selected_operating_point": None,
        "quality_gate": experiment.scoring_grid.quality_gate,
        "interpretation_constraints": dict(INTERPRETATION_CONSTRAINTS),
    }
    return validate_scoring_report(report)


def atomic_write_new_scoring_report(
    report: Mapping[str, Any],
    output_path: Path,
) -> None:
    """Publish one complete report without ever overwriting a prior artifact."""

    validated = validate_scoring_report(report)
    content = _serialized_report(validated)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        dir=output_path.parent,
    )
    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(descriptor, "wb") as output_file:
            output_file.write(content)
            output_file.flush()
            os.fsync(output_file.fileno())

        try:
            os.link(temporary_path, output_path)
        except FileExistsError as error:
            raise DetectorExperimentScoringError(
                f"Scoring report appeared during publication: {output_path}"
            ) from error

        if output_path.read_bytes() != content:
            raise DetectorExperimentScoringError(
                f"Published scoring report bytes did not verify: {output_path}"
            )
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def default_dependencies() -> ScoringDependencies:
    return ScoringDependencies(
        load_experiment=load_detector_experiment,
        inspect_git=inspect_git_repository,
        verify_tracked_file=verify_tracked_file_at_head,
        verify_commit_ancestor=verify_git_commit_ancestor,
        verify_source=verify_source_video_contract,
        is_git_ignored=is_git_ignored,
        load_annotation=load_annotations,
        load_detection=load_detection_run,
        evaluate=evaluate_detections,
        aggregate=aggregate_evaluation_reports,
        write_report=atomic_write_new_scoring_report,
    )


def score_detector_experiment(
    experiment_path: Path,
    repository_root: Path,
    *,
    dependencies: ScoringDependencies | None = None,
) -> ScoringSummary:
    """Score all frozen cells and safely publish or reuse one report."""

    deps = default_dependencies() if dependencies is None else dependencies
    root = repository_root.resolve()

    if not root.is_dir():
        raise DetectorExperimentScoringError(
            f"Repository root does not exist: {root}"
        )

    try:
        manifest_path, manifest_relative = _resolve_manifest_path(
            root,
            experiment_path,
        )
        reject_unsafe_repository_path(
            root,
            manifest_relative,
            label="Experiment manifest path",
        )
        opening_snapshot = deps.inspect_git(root, manifest_relative)
        head = _validate_git_snapshot(
            opening_snapshot,
            root,
            manifest_relative,
        )
    except Exception as error:
        if isinstance(error, DetectorExperimentScoringError):
            raise
        raise DetectorExperimentScoringError(
            f"Scoring Git/manifest preflight failed: {error}"
        ) from error

    manifest_bytes = manifest_path.read_bytes()
    experiment = deps.load_experiment(manifest_path)
    _verify_evaluator_sources(root, deps)

    if manifest_path.read_bytes() != manifest_bytes:
        raise DetectorExperimentScoringError(
            "Experiment manifest changed while loading"
        )

    output_relative = _output_relative_path(experiment)
    output_path = reject_unsafe_repository_path(
        root,
        output_relative,
        label="Detector scoring report path",
    )

    if not deps.is_git_ignored(root, output_relative):
        raise DetectorExperimentScoringError(
            f"Detector scoring report path is not Git-ignored: {output_relative}"
        )

    if output_path.exists() and not output_path.is_file():
        raise DetectorExperimentScoringError(
            f"Detector scoring report path is not a file: {output_path}"
        )

    pilots = _prepare_pilots(experiment, root, deps)
    detector_code_commit = pilots[0].detections.model_provenance.code_commit
    deps.verify_commit_ancestor(
        root,
        detector_code_commit,
        head,
        manifest_relative,
    )
    report = build_scoring_report(
        experiment,
        manifest_relative,
        manifest_bytes,
        head,
        pilots,
        evaluate=deps.evaluate,
        aggregate=deps.aggregate,
    )
    expected_bytes = _serialized_report(report)

    for pilot in pilots:
        if pilot.annotation_path.read_bytes() != pilot.annotation_bytes:
            raise DetectorExperimentScoringError(
                f"Annotation changed during scoring: {pilot.annotation_path}"
            )

        if pilot.detection_path.read_bytes() != pilot.detection_bytes:
            raise DetectorExperimentScoringError(
                f"Detection changed during scoring: {pilot.detection_path}"
            )

        deps.verify_tracked_file(
            root,
            _annotation_relative_path(pilot.window),
        )

    if manifest_path.read_bytes() != manifest_bytes:
        raise DetectorExperimentScoringError(
            "Experiment manifest changed during scoring"
        )

    _verify_evaluator_sources(root, deps)

    closing_snapshot = deps.inspect_git(root, manifest_relative)

    try:
        closing_head = _validate_git_snapshot(
            closing_snapshot,
            root,
            manifest_relative,
        )
    except Exception as error:
        raise DetectorExperimentScoringError(
            f"Closing Git validation failed: {error}"
        ) from error

    if closing_head != head:
        raise DetectorExperimentScoringError(
            "Git HEAD changed during scoring; no report was published"
        )

    reject_unsafe_repository_path(
        root,
        output_relative,
        label="Detector scoring report path",
    )

    if output_path.exists():
        existing_bytes = output_path.read_bytes()

        try:
            existing_report = load_scoring_report(output_path)
        except Exception as error:
            raise DetectorExperimentScoringError(
                f"Existing scoring report is invalid and will not be overwritten: "
                f"{error}"
            ) from error

        if existing_report != report or existing_bytes != expected_bytes:
            raise DetectorExperimentScoringError(
                "Existing scoring report conflicts with the exact recomputed "
                f"bundle and will not be overwritten: {output_path}"
            )

        reused = True
    else:
        deps.write_report(report, output_path)
        reused = False

    return ScoringSummary(
        head=head,
        output_path=output_path,
        reused_existing=reused,
        pilot_window_count=report["pilot_window_count"],
        grid_cell_count=report["grid_cell_count"],
        evaluation_report_count=report["evaluation_report_count"],
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Score only the three reviewed protocol pilots on the exact "
            "detector-experiment grid and publish one immutable report."
        )
    )
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)

    try:
        summary = score_detector_experiment(
            args.experiment,
            args.repository_root,
        )
    except (
        DetectorExperimentScoringError,
        FileNotFoundError,
        OSError,
        ValueError,
    ) as error:
        raise SystemExit(
            f"Ball detector experiment scoring error: {error}"
        ) from error

    action = "reused" if summary.reused_existing else "created"
    print(
        "Ball detector pilot grid scoring complete: "
        f"pilots={summary.pilot_window_count}, "
        f"cells={summary.grid_cell_count}, "
        f"reports={summary.evaluation_report_count}, "
        f"artifact={action}, head={summary.head}"
    )
    print(f"Output: {summary.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
