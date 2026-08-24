"""Prepare a prediction-blind independent ball-annotation workspace.

Only an already-neutral ``ball_annotation_review`` bundle is accepted as
input.  Primary/labeled annotation JSON and annotation-visualization bundles
are deliberately outside this module's API and trust boundary.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import math
import os
import platform
import shutil
import sys
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

import cv2
import numpy as np

from src.ball_tracking.annotations import (
    IDENTIFIER_PATTERN,
    AnnotationValidationError,
    BallAnnotationSet,
    verify_source_video,
)
from src.ball_tracking.prepare_annotation_review import (
    ANNOTATION_IDENTITY_FIELDS,
    ASSET_GROUP_FIELDS,
    MANIFEST_FIELDS as NEUTRAL_MANIFEST_FIELDS,
    MAX_PLAYBACK_FPS,
    REVIEW_ASSET_SCHEMA_VERSION,
    REVIEW_SAFEGUARD_FIELDS,
    SOURCE_MANIFEST_FIELDS,
    WINDOW_MANIFEST_FIELDS,
    ReviewAssetPreparationError,
    _build_context_overview,
    _decode_window_sequentially,
    _validate_existing_owned_bundle,
    _write_lossless_png,
    _write_slow_playback,
)


KIT_SCHEMA_VERSION = "ball_independent_review_kit/v0.1"
ORIGIN_SCHEMA_VERSION = "ball_independent_review_workspace_origin/v0.1"
ASSET_BUNDLE_TYPE = "ball_independent_review_kit"
EXPECTED_FRAME_COUNT = 25
FULL_CENSUS_POLICY = "all_25_frames_prediction_blind_independent_labeling"
PROTOCOL_RELATIVE_PATH = PurePosixPath(
    "docs/ball_tracking_annotation_protocol.md"
)
WORKING_FILENAME = "independent_annotations.json"

PRIMARY_ANNOTATOR_IDS = frozenset({"ryan", "ryan_codex_joint"})
GENERIC_REVIEWER_IDS = frozenset(
    {
        "annotator",
        "anonymous",
        "default",
        "dummy",
        "example",
        "generic",
        "human",
        "independent_reviewer",
        "none",
        "placeholder",
        "reviewer",
        "reviewer_id",
        "test",
        "tbd",
        "todo",
        "unknown",
        "user",
    }
)
GENERIC_REVIEWER_PREFIXES = (
    "dummy_",
    "example_",
    "generic_",
    "placeholder_",
    "test_",
)

KIT_TOP_LEVEL_FIELDS = {
    "schema_version",
    "asset_bundle_type",
    "binding",
    "neutral_bundle",
    "source_video",
    "window",
    "independent_labeler",
    "generator_process_declaration",
    "lifecycle",
    "safeguards",
    "generator",
    "assets",
}
BINDING_FIELDS = {
    "kit_binding_sha256",
    "neutral_manifest_sha256",
    "source_video_sha256",
    "window_start_frame_index",
    "window_end_frame_index",
    "window_selection_purpose",
    "protocol_sha256",
    "full_census_policy",
    "reviewer_id",
    "workspace_created_at_utc",
    "generator_fingerprint_sha256",
    "start_here_sha256",
}
NEUTRAL_BINDING_FIELDS = {
    "path",
    "asset_bundle_type",
    "manifest_sha256",
    "snapshot",
}
KIT_WINDOW_FIELDS = {
    "start_frame_index",
    "end_frame_index",
    "selection_purpose",
    "frame_count",
    "decode_method",
    "census_policy",
}
LABELER_FIELDS = {
    "annotator_id",
    "schema_role",
    "primary_annotator_ids_excluded",
}
PROCESS_DECLARATION_FIELDS = {
    "scope",
    "statement",
    "reviewer_exposure_attestation_included",
    "reviewer_exposure_attestation_stage",
}
LIFECYCLE_FIELDS = {
    "working_annotation_status",
    "completion_behavior",
    "submission_freeze_available",
    "next_step",
}
GENERATOR_FIELDS = {"fingerprint_sha256", "fingerprint"}
GENERATOR_FINGERPRINT_FIELDS = {
    "generator_module_sha256",
    "annotations_module_sha256",
    "neutral_review_helper_module_sha256",
    "annotation_editor_module_sha256",
    "python_implementation",
    "python_version",
    "platform_system",
    "platform_machine",
    "numpy_version",
    "opencv_version",
    "opencv_build_sha256",
}
KIT_ASSET_GROUP_FIELDS = {
    "source_frames",
    "context_overview",
    "slow_playback",
    "neutral_manifest_snapshot",
    "protocol_snapshot",
    "blank_annotation_template",
    "start_here",
}
BASE_ASSET_FIELDS = {"path", "sha256", "byte_size"}
SOURCE_FRAME_FIELDS = BASE_ASSET_FIELDS | {
    "frame_index",
    "width_px",
    "height_px",
    "encoding",
    "content",
}
OVERVIEW_FIELDS = BASE_ASSET_FIELDS | {
    "purpose",
    "pixel_annotation_allowed",
    "contains_detector_hints",
    "visualization_only",
}
PLAYBACK_FIELDS = BASE_ASSET_FIELDS | {
    "purpose",
    "codec_fourcc",
    "frame_count",
    "fps",
    "source_fps",
    "contains_overlays",
    "contains_detector_hints",
    "visualization_only",
}
SNAPSHOT_FIELDS = BASE_ASSET_FIELDS | {"content"}
PROTOCOL_FIELDS = SNAPSHOT_FIELDS | {
    "source_path",
    "declared_version",
}
TEMPLATE_FIELDS = SNAPSHOT_FIELDS | {
    "annotation_set_id",
    "annotator_id",
    "created_at_utc",
    "mutable",
}
START_HERE_FIELDS = SNAPSHOT_FIELDS | {"purpose"}
ORIGIN_FIELDS = {
    "schema_version",
    "kit_binding_sha256",
    "kit_relative_path",
    "kit_manifest_sha256",
    "template_relative_path",
    "template_sha256",
    "working_annotation_relative_path",
    "annotation_set_id",
    "reviewer_id",
    "created_at_utc",
    "source_video_sha256",
    "window_start_frame_index",
    "window_end_frame_index",
}

GENERATOR_PROCESS_DECLARATION = {
    "scope": "generator_input_boundary_only",
    "statement": (
        "This generator prepared the kit only from verified neutral source "
        "evidence. This process declaration does not attest to the reviewer's "
        "prior exposure and is not proof of reviewer blindness."
    ),
    "reviewer_exposure_attestation_included": False,
    "reviewer_exposure_attestation_stage": (
        "captured_only_during_later_submission"
    ),
}
NEXT_STEP_GUIDANCE = (
    "After all 25 frames are complete, close the editor and return the "
    "workspace annotation for separate validation and freezing. Leave it "
    "draft; submission freezing and reviewer-exposure attestation are later "
    "steps and are not implemented by this generator."
)
LIFECYCLE = {
    "working_annotation_status": "draft",
    "completion_behavior": "all_25_completed_rows_still_remain_draft",
    "submission_freeze_available": False,
    "next_step": NEXT_STEP_GUIDANCE,
}
SAFEGUARDS = {
    "prediction_blind_workflow": True,
    "all_window_frames_included": True,
    "native_source_frames_unmarked": True,
    "primary_annotation_json_read": False,
    "labeled_annotation_payload_read": False,
    "annotation_visual_review_assets_read": False,
    "primary_annotation_values_included": False,
    "detector_outputs_included": False,
    "tracker_outputs_included": False,
    "interpolation_used": False,
    "template_rows_all_unlabeled": True,
    "completed_independent_labels_remain_draft": True,
    "immutable_kit_separate_from_mutable_workspace": True,
}


class IndependentReviewError(RuntimeError):
    """Raised when independent-review provenance cannot be trusted."""


@dataclass(frozen=True)
class NeutralEvidence:
    directory: Path
    manifest: dict[str, Any]
    manifest_bytes: bytes
    manifest_sha256: str
    descriptor: BallAnnotationSet
    source_path: Path
    source_verification: dict[str, Any]
    frames: tuple[Any, ...]


@dataclass(frozen=True)
class IndependentReviewResult:
    review_root: Path
    kit_dir: Path
    workspace_annotation_path: Path
    state: str
    unlabeled_frame_count: int
    completed_frame_count: int
    lifecycle_status: str
    next_step: str


@dataclass(frozen=True)
class GuardedEditorTarget:
    annotation_path: Path
    annotation_bytes: bytes
    origin_path: Path
    origin_bytes: bytes
    repository_root: Path
    source_path: Path
    annotation_set: BallAnnotationSet


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
        raise IndependentReviewError(f"{label} must be a JSON object")
    actual = set(value)
    if actual != expected:
        raise IndependentReviewError(
            f"{label} fields are not closed; "
            f"missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )
    return value


def _parse_json_bytes(content: bytes, label: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise IndependentReviewError(
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
        raise IndependentReviewError(
            f"could not parse {label}: {error}"
        ) from error
    if not isinstance(payload, dict):
        raise IndependentReviewError(f"{label} must be a JSON object")
    return payload


def _serialize_json(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary_path.open("xb") as output_file:
            output_file.write(content)
            output_file.flush()
            os.fsync(output_file.fileno())
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _write_json(path: Path, payload: Mapping[str, Any]) -> bytes:
    content = _serialize_json(payload)
    _atomic_write_bytes(path, content)
    return content


def _asset_record(path: Path, root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": _sha256_file(path),
        "byte_size": path.stat().st_size,
    }


def _has_windows_reparse_point(path: Path) -> bool:
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & 0x400)


def _validate_strict_descendant(
    repository_root: Path,
    candidate: Path,
    dedicated_root: Path,
    label: str,
) -> Path:
    root = repository_root.resolve()
    lexical_candidate = candidate.absolute()
    lexical_dedicated = dedicated_root.absolute()
    try:
        relative = lexical_candidate.relative_to(lexical_dedicated)
    except ValueError as error:
        raise IndependentReviewError(
            f"{label} must be below the dedicated root {lexical_dedicated}"
        ) from error
    if relative == Path("."):
        raise IndependentReviewError(
            f"{label} must be a strict descendant of {lexical_dedicated}"
        )
    try:
        root_relative = lexical_candidate.relative_to(root)
    except ValueError as error:
        raise IndependentReviewError(
            f"{label} is lexically outside the repository"
        ) from error
    current = root
    for part in root_relative.parts:
        current = current / part
        if current.is_symlink() or (
            current.exists() and _has_windows_reparse_point(current)
        ):
            raise IndependentReviewError(
                f"{label} contains a symlink or Windows reparse/junction "
                f"ancestor: {current}"
            )
        if current.exists() and not current.is_dir():
            raise IndependentReviewError(
                f"{label} ancestor is not a directory: {current}"
            )
    resolved_dedicated = lexical_dedicated.resolve()
    resolved_candidate = lexical_candidate.resolve()
    try:
        resolved_relative = resolved_candidate.relative_to(resolved_dedicated)
    except ValueError as error:
        raise IndependentReviewError(
            f"resolved {label} escapes its dedicated root"
        ) from error
    if resolved_relative == Path("."):
        raise IndependentReviewError(
            f"resolved {label} must be a strict descendant"
        )
    return resolved_candidate


def validate_reviewer_id(reviewer_id: str) -> str:
    if not isinstance(reviewer_id, str):
        raise IndependentReviewError("reviewer ID must be a string")
    identifier = reviewer_id.strip()
    if not IDENTIFIER_PATTERN.fullmatch(identifier) or len(identifier) > 64:
        raise IndependentReviewError(
            "reviewer ID must be a project identifier of at most 64 "
            "lowercase letters, digits, underscores, or hyphens"
        )
    if identifier in PRIMARY_ANNOTATOR_IDS:
        raise IndependentReviewError(
            "independent reviewer ID must differ from the primary annotator"
        )
    if identifier in GENERIC_REVIEWER_IDS or identifier.startswith(
        GENERIC_REVIEWER_PREFIXES
    ):
        raise IndependentReviewError(
            "reviewer ID must identify a real independent labeler, not a "
            "generic or placeholder identity"
        )
    return identifier


def generator_fingerprint() -> dict[str, str]:
    module_dir = Path(__file__).resolve().parent
    fingerprint = {
        "generator_module_sha256": _sha256_file(Path(__file__).resolve()),
        "annotations_module_sha256": _sha256_file(module_dir / "annotations.py"),
        "neutral_review_helper_module_sha256": _sha256_file(
            module_dir / "prepare_annotation_review.py"
        ),
        "annotation_editor_module_sha256": _sha256_file(
            module_dir / "annotate_frames.py"
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


def generator_fingerprint_sha256(fingerprint: Mapping[str, str]) -> str:
    _exact_fields(
        fingerprint,
        GENERATOR_FINGERPRINT_FIELDS,
        "generator fingerprint",
    )
    canonical = json.dumps(
        dict(fingerprint),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(canonical)


def _blank_rows(start: int, end: int) -> list[dict[str, Any]]:
    return [
        {
            "frame_index": frame_index,
            "annotation_status": "unlabeled",
            "visibility": None,
            "absence_reason": None,
            "game_ball_identity_certainty": None,
            "geometry": None,
            "localization_eligible": False,
            "difficulty_tags": [],
            "notes": None,
        }
        for frame_index in range(start, end + 1)
    ]


def _coordinate_system() -> dict[str, Any]:
    return {
        "frame_index_origin": 0,
        "pixel_origin": "top_left",
        "x_axis_direction": "right",
        "y_axis_direction": "down",
        "center_definition": "complete_ball_center",
        "timestamp_rule": "frame_index_divided_by_fps",
    }


def _descriptor_from_neutral_manifest(
    manifest: Mapping[str, Any],
) -> BallAnnotationSet:
    annotation_identity = _exact_fields(
        manifest["annotation_set"],
        ANNOTATION_IDENTITY_FIELDS,
        "neutral manifest.annotation_set",
    )
    source = _exact_fields(
        manifest["source_video"],
        SOURCE_MANIFEST_FIELDS,
        "neutral manifest.source_video",
    )
    window = _exact_fields(
        manifest["window"],
        WINDOW_MANIFEST_FIELDS,
        "neutral manifest.window",
    )
    if annotation_identity["annotation_schema_version"] != "0.1":
        raise IndependentReviewError(
            "neutral annotation schema version must be 0.1"
        )
    for field in ("frame_count", "start_frame_index", "end_frame_index"):
        if isinstance(window[field], bool) or not isinstance(window[field], int):
            raise IndependentReviewError(
                f"neutral manifest.window.{field} must be an integer"
            )
    if window["frame_count"] != EXPECTED_FRAME_COUNT or (
        window["end_frame_index"] - window["start_frame_index"] + 1
        != EXPECTED_FRAME_COUNT
    ):
        raise IndependentReviewError(
            "independent review requires one exact 25-frame window"
        )
    if window["selection_purpose"] != "protocol_adjudication":
        raise IndependentReviewError(
            "neutral window must use the fixed protocol_adjudication census"
        )
    if window["decode_method"] != "sequential_from_frame_zero_no_random_seek":
        raise IndependentReviewError(
            "neutral window decode method is not the required sequential method"
        )
    payload = {
        "schema_version": "0.1",
        "annotation_set_id": annotation_identity["annotation_set_id"],
        "possession_id": annotation_identity["possession_id"],
        "source_video": {
            field: source[field]
            for field in (
                "path",
                "sha256",
                "width_px",
                "height_px",
                "fps",
                "frame_count",
            )
        },
        "window": {
            "start_frame_index": window["start_frame_index"],
            "end_frame_index": window["end_frame_index"],
            "selection_purpose": window["selection_purpose"],
        },
        "coordinate_system": _coordinate_system(),
        "review": {
            "status": "draft",
            "annotator_id": "neutral_bundle_descriptor",
            "reviewer_id": None,
            "created_at_utc": "1970-01-01T00:00:00Z",
            "reviewed_at_utc": None,
        },
        "annotations": _blank_rows(
            window["start_frame_index"],
            window["end_frame_index"],
        ),
    }
    try:
        return BallAnnotationSet.from_mapping(payload)
    except AnnotationValidationError as error:
        raise IndependentReviewError(
            f"neutral manifest identity is not valid schema v0.1: {error}"
        ) from error


def _reject_tree_links(root: Path, label: str) -> None:
    if root.is_symlink() or _has_windows_reparse_point(root):
        raise IndependentReviewError(
            f"{label} root is a symlink or Windows reparse/junction"
        )
    try:
        paths = list(root.rglob("*"))
    except OSError as error:
        raise IndependentReviewError(f"could not inspect {label}: {error}") from error
    for path in paths:
        if path.is_symlink() or _has_windows_reparse_point(path):
            raise IndependentReviewError(
                f"{label} contains a symlink or Windows reparse/junction: {path}"
            )


def _portable_asset_path(root: Path, raw_path: Any, label: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path or "\\" in raw_path:
        raise IndependentReviewError(f"{label}.path is not portable")
    relative = PurePosixPath(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise IndependentReviewError(f"{label}.path escapes its bundle")
    path = root.joinpath(*relative.parts)
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise IndependentReviewError(f"{label}.path escapes its bundle") from error
    return path


def _validate_source_path_links(
    repository_root: Path,
    descriptor: BallAnnotationSet,
) -> Path:
    lexical = repository_root.joinpath(*descriptor.source_video.path.parts)
    try:
        relative = lexical.absolute().relative_to(repository_root.resolve())
    except ValueError as error:
        raise IndependentReviewError("source path escapes repository root") from error
    current = repository_root.resolve()
    for part in relative.parts:
        current = current / part
        if current.is_symlink() or (
            current.exists() and _has_windows_reparse_point(current)
        ):
            raise IndependentReviewError(
                "source path contains a symlink or Windows reparse/junction: "
                f"{current}"
            )
    resolved = lexical.resolve()
    try:
        resolved.relative_to(repository_root.resolve())
    except ValueError as error:
        raise IndependentReviewError("resolved source path escapes repository") from error
    return resolved


def validate_neutral_bundle(
    neutral_bundle: Path,
    repository_root: Path,
) -> NeutralEvidence:
    """Validate neutral evidence without opening any annotation JSON."""

    repository_root = repository_root.resolve()
    dedicated_root = (
        repository_root
        / "data"
        / "outputs"
        / "ball_tracking"
        / "annotation_review"
    )
    neutral_dir = _validate_strict_descendant(
        repository_root,
        neutral_bundle,
        dedicated_root,
        "neutral bundle",
    )
    if not neutral_dir.is_dir():
        raise IndependentReviewError(
            f"neutral bundle directory does not exist: {neutral_dir}"
        )
    _reject_tree_links(neutral_dir, "neutral bundle")
    manifest_path = neutral_dir / "manifest.json"
    try:
        manifest_bytes = manifest_path.read_bytes()
    except OSError as error:
        raise IndependentReviewError(
            f"could not read neutral manifest: {error}"
        ) from error
    manifest = _parse_json_bytes(manifest_bytes, "neutral manifest")
    _exact_fields(manifest, NEUTRAL_MANIFEST_FIELDS, "neutral manifest")
    if (
        manifest["schema_version"] != REVIEW_ASSET_SCHEMA_VERSION
        or manifest["asset_bundle_type"] != "ball_annotation_review"
    ):
        raise IndependentReviewError(
            "input must be a neutral ball_annotation_review bundle"
        )
    _exact_fields(
        manifest["review_safeguards"],
        REVIEW_SAFEGUARD_FIELDS,
        "neutral manifest.review_safeguards",
    )
    expected_safeguards = {
        "native_source_frames_unmarked": True,
        "detector_outputs_included": False,
        "crops_included": False,
        "trajectory_hints_included": False,
        "annotation_json_modified": False,
    }
    if manifest["review_safeguards"] != expected_safeguards:
        raise IndependentReviewError("neutral review safeguards do not match")
    _exact_fields(
        manifest["assets"],
        ASSET_GROUP_FIELDS,
        "neutral manifest.assets",
    )
    descriptor = _descriptor_from_neutral_manifest(manifest)
    try:
        _validate_existing_owned_bundle(neutral_dir, descriptor)
    except ReviewAssetPreparationError as error:
        raise IndependentReviewError(
            f"neutral bundle validation failed: {error}"
        ) from error
    if manifest_path.read_bytes() != manifest_bytes:
        raise IndependentReviewError(
            "neutral manifest changed while it was being validated"
        )
    source_path = _validate_source_path_links(repository_root, descriptor)
    try:
        source_verification = verify_source_video(descriptor, repository_root)
        frames = _decode_window_sequentially(source_path, descriptor)
    except (AnnotationValidationError, ReviewAssetPreparationError) as error:
        raise IndependentReviewError(
            f"neutral source verification failed: {error}"
        ) from error
    frame_records = manifest["assets"]["source_frames"]
    if not isinstance(frame_records, list) or len(frame_records) != len(frames):
        raise IndependentReviewError("neutral source-frame list is incomplete")
    expected_indices = list(
        range(
            descriptor.window.start_frame_index,
            descriptor.window.end_frame_index + 1,
        )
    )
    for position, (record, decoded, frame_index) in enumerate(
        zip(frame_records, frames, expected_indices, strict=True)
    ):
        if not isinstance(record, Mapping) or record.get("frame_index") != frame_index:
            raise IndependentReviewError(
                f"neutral frame order mismatch at position {position}"
            )
        neutral_path = _portable_asset_path(
            neutral_dir,
            record.get("path"),
            f"neutral source_frames[{position}]",
        )
        neutral_frame = cv2.imread(str(neutral_path), cv2.IMREAD_COLOR)
        if neutral_frame is None or not np.array_equal(neutral_frame, decoded):
            raise IndependentReviewError(
                "neutral frame does not pixel-match sequential source decode: "
                f"frame {frame_index}"
            )
    if frame_records[-1]["frame_index"] != descriptor.window.end_frame_index:
        raise IndependentReviewError("neutral final frame identity is incorrect")
    if manifest_path.read_bytes() != manifest_bytes:
        raise IndependentReviewError(
            "neutral manifest changed during source verification"
        )
    return NeutralEvidence(
        directory=neutral_dir,
        manifest=manifest,
        manifest_bytes=manifest_bytes,
        manifest_sha256=_sha256_bytes(manifest_bytes),
        descriptor=descriptor,
        source_path=source_path,
        source_verification=source_verification,
        frames=tuple(frames),
    )


def independent_annotation_set_id(
    descriptor: BallAnnotationSet,
    reviewer_id: str,
) -> str:
    return (
        f"{descriptor.possession_id}_frames_"
        f"{descriptor.window.start_frame_index:04d}_"
        f"{descriptor.window.end_frame_index:04d}_"
        f"independent_{reviewer_id}_v0_1"
    )


def _template_payload(
    descriptor: BallAnnotationSet,
    reviewer_id: str,
    created_at_utc: str,
) -> dict[str, Any]:
    annotation_set_id = independent_annotation_set_id(descriptor, reviewer_id)
    if annotation_set_id == descriptor.annotation_set_id:
        raise IndependentReviewError(
            "independent annotation_set_id must differ from neutral provenance"
        )
    payload = {
        "schema_version": "0.1",
        "annotation_set_id": annotation_set_id,
        "possession_id": descriptor.possession_id,
        "source_video": descriptor.source_video.to_dict(),
        "window": descriptor.window.to_dict(),
        "coordinate_system": _coordinate_system(),
        "review": {
            "status": "draft",
            "annotator_id": reviewer_id,
            "reviewer_id": None,
            "created_at_utc": created_at_utc,
            "reviewed_at_utc": None,
        },
        "annotations": _blank_rows(
            descriptor.window.start_frame_index,
            descriptor.window.end_frame_index,
        ),
    }
    try:
        parsed = BallAnnotationSet.from_mapping(payload)
    except AnnotationValidationError as error:
        raise IndependentReviewError(
            f"generated blank independent template is invalid: {error}"
        ) from error
    if any(row.annotation_status != "unlabeled" for row in parsed.annotations):
        raise IndependentReviewError("blank template unexpectedly contains labels")
    return parsed.to_dict()


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _protocol_snapshot(repository_root: Path) -> tuple[Path, bytes, str]:
    protocol_path = repository_root.joinpath(*PROTOCOL_RELATIVE_PATH.parts)
    current = repository_root.resolve()
    for part in PROTOCOL_RELATIVE_PATH.parts:
        current = current / part
        if current.is_symlink() or (
            current.exists() and _has_windows_reparse_point(current)
        ):
            raise IndependentReviewError(
                "annotation protocol path contains a symlink or Windows "
                f"reparse/junction ancestor: {current}"
            )
    resolved = protocol_path.resolve()
    try:
        resolved.relative_to(repository_root.resolve())
    except ValueError as error:
        raise IndependentReviewError("annotation protocol escapes repository") from error
    try:
        content = resolved.read_bytes()
    except OSError as error:
        raise IndependentReviewError(
            f"could not read annotation protocol: {error}"
        ) from error
    if b"Ball-tracking annotation protocol v0.1" not in content:
        raise IndependentReviewError(
            "annotation protocol snapshot is not declared v0.1"
        )
    return resolved, content, _sha256_bytes(content)


def _powershell_single_quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _start_here_bytes(
    repository_root: Path,
    evidence: NeutralEvidence,
    reviewer_id: str,
) -> bytes:
    neutral_relative = evidence.directory.relative_to(repository_root).as_posix()
    working_relative = (
        review_root_path(repository_root, evidence.descriptor, reviewer_id)
        .relative_to(repository_root)
        .joinpath("workspace", WORKING_FILENAME)
        .as_posix()
    )
    neutral_windows = neutral_relative.replace("/", "\\")
    source_relative = evidence.descriptor.source_video.path.as_posix()
    content = f"""# START HERE - independent ball annotation

This kit is repository-local, not a portable standalone package. Run it from
the full Player Defense Score repository. It requires the original source clip
at `{source_relative}` and the repository's `.venv` environment.

Use exactly this one PowerShell command from the repository root:

```powershell
.\\.venv\\Scripts\\python.exe -m src.ball_tracking.prepare_independent_review --neutral-bundle {_powershell_single_quoted(neutral_windows)} --repository-root {_powershell_single_quoted('.')} --reviewer-id {_powershell_single_quoted(reviewer_id)} --launch-editor
```

## Which files may change

- Mutable: `{working_relative}` is the only annotation file the guarded editor
  may update.
- Immutable: everything under this `kit/` directory, including
  `blank_annotation_template.json`, `source_frames/`, the manifest, and the
  snapshots. `workspace/origin.json` is also provenance and must not be edited.

## Annotation rules

- Label all 25 frames. The current native frame displayed by the editor governs
  pixel geometry.
- `context_only_overview.png` and `slow_playback.mp4` are context-only. Do not
  use either asset to read or click pixel geometry.
- Even at 25/25 completed frames, the working annotation remains `draft`. Never
  promote it to `reviewed` in this phase.

## Return and next step

After all 25 frames are complete, close the editor and return
`{working_relative}` to the project owner without editing the immutable kit or
`workspace/origin.json`. The next phase is separate validation and freezing of
that exact draft. The freeze/submission step is not implemented here, and the
reviewer's exposure attestation is captured only during that later submission.
"""
    return content.encode("utf-8")


def binding_components(
    evidence: NeutralEvidence,
    protocol_sha256: str,
    reviewer_id: str,
    created_at_utc: str,
    fingerprint: Mapping[str, str],
    repository_root: Path,
) -> dict[str, Any]:
    start_here_bytes = _start_here_bytes(
        repository_root,
        evidence,
        reviewer_id,
    )
    return {
        "neutral_manifest_sha256": evidence.manifest_sha256,
        "source_video_sha256": evidence.descriptor.source_video.sha256,
        "window_start_frame_index": (
            evidence.descriptor.window.start_frame_index
        ),
        "window_end_frame_index": evidence.descriptor.window.end_frame_index,
        "window_selection_purpose": (
            evidence.descriptor.window.selection_purpose
        ),
        "protocol_sha256": protocol_sha256,
        "full_census_policy": FULL_CENSUS_POLICY,
        "reviewer_id": reviewer_id,
        "workspace_created_at_utc": created_at_utc,
        "generator_fingerprint_sha256": generator_fingerprint_sha256(
            fingerprint
        ),
        "start_here_sha256": _sha256_bytes(start_here_bytes),
    }


def binding_sha256(components: Mapping[str, Any]) -> str:
    if set(components) != BINDING_FIELDS - {"kit_binding_sha256"}:
        raise IndependentReviewError("kit binding components are not closed")
    canonical = json.dumps(
        dict(components),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(canonical)


def review_root_path(
    repository_root: Path,
    descriptor: BallAnnotationSet,
    reviewer_id: str,
) -> Path:
    window_name = (
        f"frames_{descriptor.window.start_frame_index:04d}_"
        f"{descriptor.window.end_frame_index:04d}"
    )
    candidate = (
        repository_root.resolve()
        / "data"
        / "outputs"
        / "ball_tracking"
        / "independent_review"
        / descriptor.possession_id
        / window_name
        / reviewer_id
    )
    dedicated = (
        repository_root.resolve()
        / "data"
        / "outputs"
        / "ball_tracking"
        / "independent_review"
    )
    return _validate_strict_descendant(
        repository_root.resolve(),
        candidate,
        dedicated,
        "independent review output",
    )


def _origin_payload(
    review_root: Path,
    kit_dir: Path,
    kit_manifest_path: Path,
    template_path: Path,
    template_payload: Mapping[str, Any],
    reviewer_id: str,
    components: Mapping[str, Any],
    digest: str,
) -> dict[str, Any]:
    return {
        "schema_version": ORIGIN_SCHEMA_VERSION,
        "kit_binding_sha256": digest,
        "kit_relative_path": kit_dir.relative_to(review_root).as_posix(),
        "kit_manifest_sha256": _sha256_file(kit_manifest_path),
        "template_relative_path": template_path.relative_to(review_root).as_posix(),
        "template_sha256": _sha256_file(template_path),
        "working_annotation_relative_path": (
            f"workspace/{WORKING_FILENAME}"
        ),
        "annotation_set_id": template_payload["annotation_set_id"],
        "reviewer_id": reviewer_id,
        "created_at_utc": components["workspace_created_at_utc"],
        "source_video_sha256": components["source_video_sha256"],
        "window_start_frame_index": components["window_start_frame_index"],
        "window_end_frame_index": components["window_end_frame_index"],
    }


def _build_kit_and_workspace(
    staging_root: Path,
    repository_root: Path,
    evidence: NeutralEvidence,
    protocol_bytes: bytes,
    reviewer_id: str,
    template_payload: Mapping[str, Any],
    template_bytes: bytes,
    components: Mapping[str, Any],
    digest: str,
    fingerprint: Mapping[str, str],
) -> tuple[Path, Path]:
    kit_dir = staging_root / "kit" / digest
    workspace_dir = staging_root / "workspace"
    source_frames_dir = kit_dir / "source_frames"
    source_frames_dir.mkdir(parents=True)
    workspace_dir.mkdir()

    frame_indices = list(
        range(
            evidence.descriptor.window.start_frame_index,
            evidence.descriptor.window.end_frame_index + 1,
        )
    )
    source_records = []
    for frame_index, frame in zip(
        frame_indices,
        evidence.frames,
        strict=True,
    ):
        frame_path = source_frames_dir / f"frame_{frame_index:06d}.png"
        try:
            _write_lossless_png(frame_path, frame)
        except ReviewAssetPreparationError as error:
            raise IndependentReviewError(
                f"could not write independent source frame: {error}"
            ) from error
        record = _asset_record(frame_path, kit_dir)
        record.update(
            {
                "frame_index": frame_index,
                "width_px": evidence.descriptor.source_video.width_px,
                "height_px": evidence.descriptor.source_video.height_px,
                "encoding": "lossless_png",
                "content": "verified_native_source_pixels_unmarked",
            }
        )
        source_records.append(record)

    overview_path = kit_dir / "context_only_overview.png"
    overview = _build_context_overview(list(evidence.frames), frame_indices)
    try:
        _write_lossless_png(overview_path, overview)
    except ReviewAssetPreparationError as error:
        raise IndependentReviewError(
            f"could not write independent context overview: {error}"
        ) from error

    playback_path = kit_dir / "slow_playback.mp4"
    playback_fps = min(MAX_PLAYBACK_FPS, evidence.descriptor.source_video.fps)
    try:
        playback_codec = _write_slow_playback(
            playback_path,
            list(evidence.frames),
            evidence.descriptor.source_video.width_px,
            evidence.descriptor.source_video.height_px,
            playback_fps,
        )
    except ReviewAssetPreparationError as error:
        raise IndependentReviewError(
            f"could not write independent clean playback: {error}"
        ) from error

    neutral_snapshot_path = kit_dir / "neutral_manifest_snapshot.json"
    protocol_path = kit_dir / "protocol_snapshot.md"
    template_path = kit_dir / "blank_annotation_template.json"
    start_here_path = kit_dir / "START_HERE.md"
    start_here_bytes = _start_here_bytes(
        repository_root,
        evidence,
        reviewer_id,
    )
    _atomic_write_bytes(neutral_snapshot_path, evidence.manifest_bytes)
    _atomic_write_bytes(protocol_path, protocol_bytes)
    _atomic_write_bytes(template_path, template_bytes)
    _atomic_write_bytes(start_here_path, start_here_bytes)

    overview_record = _asset_record(overview_path, kit_dir)
    overview_record.update(
        {
            "purpose": "context_only_not_for_pixel_annotation",
            "pixel_annotation_allowed": False,
            "contains_detector_hints": False,
            "visualization_only": True,
        }
    )
    playback_record = _asset_record(playback_path, kit_dir)
    playback_record.update(
        {
            "purpose": "clean_context_only_playback",
            "codec_fourcc": playback_codec,
            "frame_count": EXPECTED_FRAME_COUNT,
            "fps": playback_fps,
            "source_fps": evidence.descriptor.source_video.fps,
            "contains_overlays": False,
            "contains_detector_hints": False,
            "visualization_only": True,
        }
    )
    neutral_snapshot_record = _asset_record(neutral_snapshot_path, kit_dir)
    neutral_snapshot_record["content"] = "exact_neutral_manifest_bytes"
    protocol_record = _asset_record(protocol_path, kit_dir)
    protocol_record.update(
        {
            "content": "exact_protocol_bytes",
            "source_path": PROTOCOL_RELATIVE_PATH.as_posix(),
            "declared_version": "v0.1",
        }
    )
    template_record = _asset_record(template_path, kit_dir)
    template_record.update(
        {
            "content": "pristine_all_unlabeled_independent_template",
            "annotation_set_id": template_payload["annotation_set_id"],
            "annotator_id": reviewer_id,
            "created_at_utc": components["workspace_created_at_utc"],
            "mutable": False,
        }
    )
    start_here_record = _asset_record(start_here_path, kit_dir)
    start_here_record.update(
        {
            "content": "deterministic_repo_local_operator_instructions",
            "purpose": "guarded_independent_annotation_entry_and_handoff",
        }
    )
    manifest = {
        "schema_version": KIT_SCHEMA_VERSION,
        "asset_bundle_type": ASSET_BUNDLE_TYPE,
        "binding": {"kit_binding_sha256": digest, **dict(components)},
        "neutral_bundle": {
            "path": evidence.directory.relative_to(repository_root).as_posix(),
            "asset_bundle_type": "ball_annotation_review",
            "manifest_sha256": evidence.manifest_sha256,
            "snapshot": neutral_snapshot_record,
        },
        "source_video": evidence.source_verification,
        "window": {
            **evidence.descriptor.window.to_dict(),
            "frame_count": EXPECTED_FRAME_COUNT,
            "decode_method": "sequential_from_frame_zero_no_random_seek",
            "census_policy": FULL_CENSUS_POLICY,
        },
        "independent_labeler": {
            "annotator_id": reviewer_id,
            "schema_role": "independent_labeler_stored_as_review.annotator_id",
            "primary_annotator_ids_excluded": sorted(PRIMARY_ANNOTATOR_IDS),
        },
        "generator_process_declaration": GENERATOR_PROCESS_DECLARATION,
        "lifecycle": LIFECYCLE,
        "safeguards": SAFEGUARDS,
        "generator": {
            "fingerprint_sha256": generator_fingerprint_sha256(fingerprint),
            "fingerprint": dict(fingerprint),
        },
        "assets": {
            "source_frames": source_records,
            "context_overview": overview_record,
            "slow_playback": playback_record,
            "neutral_manifest_snapshot": neutral_snapshot_record,
            "protocol_snapshot": protocol_record,
            "blank_annotation_template": template_record,
            "start_here": start_here_record,
        },
    }
    kit_manifest_path = kit_dir / "manifest.json"
    _write_json(kit_manifest_path, manifest)

    working_path = workspace_dir / WORKING_FILENAME
    _atomic_write_bytes(working_path, template_bytes)
    origin = _origin_payload(
        staging_root,
        kit_dir,
        kit_manifest_path,
        template_path,
        template_payload,
        reviewer_id,
        components,
        digest,
    )
    _write_json(workspace_dir / "origin.json", origin)
    if os.path.samestat(template_path.stat(), working_path.stat()):
        raise IndependentReviewError(
            "working annotation must be a separate file, not a hardlink"
        )
    return kit_dir, working_path


def _validate_asset_record(
    kit_dir: Path,
    record: Any,
    expected_fields: set[str],
    expected_path: str,
    label: str,
) -> Path:
    mapping = _exact_fields(record, expected_fields, label)
    if mapping["path"] != expected_path:
        raise IndependentReviewError(
            f"{label}.path expected {expected_path!r}"
        )
    path = _portable_asset_path(kit_dir, mapping["path"], label)
    if path.is_symlink() or not path.is_file():
        raise IndependentReviewError(f"{label} is not a regular file")
    if (
        isinstance(mapping["byte_size"], bool)
        or not isinstance(mapping["byte_size"], int)
        or mapping["byte_size"] != path.stat().st_size
    ):
        raise IndependentReviewError(f"{label} byte size does not match")
    if mapping["sha256"] != _sha256_file(path):
        raise IndependentReviewError(f"{label} SHA-256 does not match")
    return path


def _validate_kit(
    review_root: Path,
    kit_dir: Path,
    repository_root: Path,
    evidence: NeutralEvidence,
    protocol_bytes: bytes,
    reviewer_id: str,
    template_payload: Mapping[str, Any],
    template_bytes: bytes,
    components: Mapping[str, Any],
    digest: str,
    fingerprint: Mapping[str, str],
) -> dict[str, Any]:
    _reject_tree_links(kit_dir, "independent immutable kit")
    manifest_path = kit_dir / "manifest.json"
    try:
        manifest_bytes = manifest_path.read_bytes()
    except OSError as error:
        raise IndependentReviewError(f"could not read kit manifest: {error}") from error
    manifest = _parse_json_bytes(manifest_bytes, "independent kit manifest")
    _exact_fields(manifest, KIT_TOP_LEVEL_FIELDS, "independent kit manifest")
    if (
        manifest["schema_version"] != KIT_SCHEMA_VERSION
        or manifest["asset_bundle_type"] != ASSET_BUNDLE_TYPE
    ):
        raise IndependentReviewError("independent kit type/schema is not owned")
    binding = _exact_fields(manifest["binding"], BINDING_FIELDS, "kit binding")
    if binding != {"kit_binding_sha256": digest, **dict(components)}:
        raise IndependentReviewError("kit provenance binding does not match")
    neutral = _exact_fields(
        manifest["neutral_bundle"],
        NEUTRAL_BINDING_FIELDS,
        "kit neutral_bundle",
    )
    expected_neutral = {
        "path": evidence.directory.relative_to(repository_root).as_posix(),
        "asset_bundle_type": "ball_annotation_review",
        "manifest_sha256": evidence.manifest_sha256,
    }
    for field, expected in expected_neutral.items():
        if neutral[field] != expected:
            raise IndependentReviewError(
                f"kit neutral binding mismatch: {field}"
            )
    if manifest["source_video"] != evidence.source_verification:
        raise IndependentReviewError("kit source-video binding does not match")
    expected_window = {
        **evidence.descriptor.window.to_dict(),
        "frame_count": EXPECTED_FRAME_COUNT,
        "decode_method": "sequential_from_frame_zero_no_random_seek",
        "census_policy": FULL_CENSUS_POLICY,
    }
    if _exact_fields(
        manifest["window"], KIT_WINDOW_FIELDS, "kit window"
    ) != expected_window:
        raise IndependentReviewError("kit window/full-census policy does not match")
    expected_labeler = {
        "annotator_id": reviewer_id,
        "schema_role": "independent_labeler_stored_as_review.annotator_id",
        "primary_annotator_ids_excluded": sorted(PRIMARY_ANNOTATOR_IDS),
    }
    if _exact_fields(
        manifest["independent_labeler"],
        LABELER_FIELDS,
        "independent labeler",
    ) != expected_labeler:
        raise IndependentReviewError("independent labeler identity does not match")
    if _exact_fields(
        manifest["generator_process_declaration"],
        PROCESS_DECLARATION_FIELDS,
        "generator process declaration",
    ) != GENERATOR_PROCESS_DECLARATION:
        raise IndependentReviewError(
            "generator process declaration does not match"
        )
    if _exact_fields(
        manifest["lifecycle"],
        LIFECYCLE_FIELDS,
        "independent kit lifecycle",
    ) != LIFECYCLE:
        raise IndependentReviewError("independent kit lifecycle does not match")
    if manifest["safeguards"] != SAFEGUARDS:
        raise IndependentReviewError("independent kit safeguards do not match")
    generator = _exact_fields(
        manifest["generator"], GENERATOR_FIELDS, "kit generator"
    )
    recorded_fingerprint = _exact_fields(
        generator["fingerprint"],
        GENERATOR_FINGERPRINT_FIELDS,
        "kit generator fingerprint",
    )
    if recorded_fingerprint != fingerprint:
        raise IndependentReviewError(
            "kit generator fingerprint does not match current code/runtime"
        )
    if generator["fingerprint_sha256"] != generator_fingerprint_sha256(
        fingerprint
    ):
        raise IndependentReviewError("kit generator fingerprint hash is invalid")
    assets = _exact_fields(
        manifest["assets"], KIT_ASSET_GROUP_FIELDS, "kit assets"
    )
    frame_records = assets["source_frames"]
    if not isinstance(frame_records, list) or len(frame_records) != EXPECTED_FRAME_COUNT:
        raise IndependentReviewError("kit source frame list is incomplete")

    expected_entries = {
        "manifest.json",
        "source_frames",
        "context_only_overview.png",
        "slow_playback.mp4",
        "neutral_manifest_snapshot.json",
        "protocol_snapshot.md",
        "blank_annotation_template.json",
        "START_HERE.md",
    }
    expected_indices = list(
        range(
            evidence.descriptor.window.start_frame_index,
            evidence.descriptor.window.end_frame_index + 1,
        )
    )
    for position, (record, frame_index, expected_pixels) in enumerate(
        zip(frame_records, expected_indices, evidence.frames, strict=True)
    ):
        relative_path = f"source_frames/frame_{frame_index:06d}.png"
        expected_entries.add(relative_path)
        frame_path = _validate_asset_record(
            kit_dir,
            record,
            SOURCE_FRAME_FIELDS,
            relative_path,
            f"kit source_frames[{position}]",
        )
        expected_metadata = {
            "frame_index": frame_index,
            "width_px": evidence.descriptor.source_video.width_px,
            "height_px": evidence.descriptor.source_video.height_px,
            "encoding": "lossless_png",
            "content": "verified_native_source_pixels_unmarked",
        }
        for field, expected in expected_metadata.items():
            if record[field] != expected:
                raise IndependentReviewError(
                    f"kit source frame metadata mismatch: {field}"
                )
        decoded = cv2.imread(str(frame_path), cv2.IMREAD_COLOR)
        if decoded is None or not np.array_equal(decoded, expected_pixels):
            raise IndependentReviewError(
                "kit source frame does not match verified source pixels: "
                f"frame {frame_index}"
            )
    if frame_records[-1]["frame_index"] != expected_indices[-1]:
        raise IndependentReviewError("kit final frame identity does not match")

    overview_record = assets["context_overview"]
    overview_path = _validate_asset_record(
        kit_dir,
        overview_record,
        OVERVIEW_FIELDS,
        "context_only_overview.png",
        "kit context overview",
    )
    expected_overview_metadata = {
        "purpose": "context_only_not_for_pixel_annotation",
        "pixel_annotation_allowed": False,
        "contains_detector_hints": False,
        "visualization_only": True,
    }
    for field, expected in expected_overview_metadata.items():
        if overview_record[field] != expected:
            raise IndependentReviewError(
                f"kit context overview metadata mismatch: {field}"
            )
    decoded_overview = cv2.imread(str(overview_path), cv2.IMREAD_COLOR)
    expected_overview = _build_context_overview(
        list(evidence.frames), expected_indices
    )
    if decoded_overview is None or not np.array_equal(
        decoded_overview, expected_overview
    ):
        raise IndependentReviewError(
            "kit context overview does not match deterministic neutral render"
        )

    playback_record = assets["slow_playback"]
    playback_path = _validate_asset_record(
        kit_dir,
        playback_record,
        PLAYBACK_FIELDS,
        "slow_playback.mp4",
        "kit slow playback",
    )
    playback_fps = min(MAX_PLAYBACK_FPS, evidence.descriptor.source_video.fps)
    expected_playback_metadata = {
        "purpose": "clean_context_only_playback",
        "frame_count": EXPECTED_FRAME_COUNT,
        "fps": playback_fps,
        "source_fps": evidence.descriptor.source_video.fps,
        "contains_overlays": False,
        "contains_detector_hints": False,
        "visualization_only": True,
    }
    for field, expected in expected_playback_metadata.items():
        if playback_record[field] != expected:
            raise IndependentReviewError(
                f"kit clean playback metadata mismatch: {field}"
            )
    with tempfile.TemporaryDirectory(
        prefix="independent-review-playback-reference-"
    ) as temporary_directory:
        reference_path = Path(temporary_directory) / "reference.mp4"
        try:
            reference_codec = _write_slow_playback(
                reference_path,
                list(evidence.frames),
                evidence.descriptor.source_video.width_px,
                evidence.descriptor.source_video.height_px,
                playback_fps,
            )
        except ReviewAssetPreparationError as error:
            raise IndependentReviewError(
                f"could not regenerate clean playback reference: {error}"
            ) from error
        if reference_codec != playback_record["codec_fourcc"]:
            raise IndependentReviewError("kit playback codec does not match")
        if reference_path.read_bytes() != playback_path.read_bytes():
            raise IndependentReviewError(
                "kit playback does not match deterministic clean reference"
            )

    neutral_snapshot_path = _validate_asset_record(
        kit_dir,
        neutral["snapshot"],
        SNAPSHOT_FIELDS,
        "neutral_manifest_snapshot.json",
        "kit neutral manifest snapshot",
    )
    if (
        neutral["snapshot"]["content"] != "exact_neutral_manifest_bytes"
        or neutral_snapshot_path.read_bytes() != evidence.manifest_bytes
    ):
        raise IndependentReviewError("kit neutral snapshot bytes do not match")
    if assets["neutral_manifest_snapshot"] != neutral["snapshot"]:
        raise IndependentReviewError("neutral snapshot asset records diverge")

    protocol_path = _validate_asset_record(
        kit_dir,
        assets["protocol_snapshot"],
        PROTOCOL_FIELDS,
        "protocol_snapshot.md",
        "kit protocol snapshot",
    )
    expected_protocol_metadata = {
        "content": "exact_protocol_bytes",
        "source_path": PROTOCOL_RELATIVE_PATH.as_posix(),
        "declared_version": "v0.1",
    }
    for field, expected in expected_protocol_metadata.items():
        if assets["protocol_snapshot"][field] != expected:
            raise IndependentReviewError(
                f"kit protocol metadata mismatch: {field}"
            )
    if protocol_path.read_bytes() != protocol_bytes:
        raise IndependentReviewError("kit protocol snapshot bytes do not match")

    template_path = _validate_asset_record(
        kit_dir,
        assets["blank_annotation_template"],
        TEMPLATE_FIELDS,
        "blank_annotation_template.json",
        "kit blank template",
    )
    expected_template_metadata = {
        "content": "pristine_all_unlabeled_independent_template",
        "annotation_set_id": template_payload["annotation_set_id"],
        "annotator_id": reviewer_id,
        "created_at_utc": components["workspace_created_at_utc"],
        "mutable": False,
    }
    for field, expected in expected_template_metadata.items():
        if assets["blank_annotation_template"][field] != expected:
            raise IndependentReviewError(
                f"kit blank template metadata mismatch: {field}"
            )
    if template_path.read_bytes() != template_bytes:
        raise IndependentReviewError("kit blank template bytes do not match")

    start_here_path = _validate_asset_record(
        kit_dir,
        assets["start_here"],
        START_HERE_FIELDS,
        "START_HERE.md",
        "kit START_HERE instructions",
    )
    expected_start_here = _start_here_bytes(
        repository_root,
        evidence,
        reviewer_id,
    )
    expected_start_here_metadata = {
        "content": "deterministic_repo_local_operator_instructions",
        "purpose": "guarded_independent_annotation_entry_and_handoff",
    }
    for field, expected in expected_start_here_metadata.items():
        if assets["start_here"][field] != expected:
            raise IndependentReviewError(
                f"kit START_HERE metadata mismatch: {field}"
            )
    if (
        components["start_here_sha256"] != _sha256_bytes(expected_start_here)
        or start_here_path.read_bytes() != expected_start_here
    ):
        raise IndependentReviewError(
            "kit START_HERE instructions do not match deterministic content"
        )

    actual_entries = {
        path.relative_to(kit_dir).as_posix()
        for path in kit_dir.rglob("*")
    }
    if actual_entries != expected_entries:
        raise IndependentReviewError(
            "immutable kit tree is not closed; "
            f"missing={sorted(expected_entries - actual_entries)}, "
            f"extra={sorted(actual_entries - expected_entries)}"
        )
    if manifest_path.read_bytes() != manifest_bytes:
        raise IndependentReviewError("kit manifest changed during validation")
    expected_relative = f"kit/{digest}"
    if kit_dir.relative_to(review_root).as_posix() != expected_relative:
        raise IndependentReviewError("kit is not at its content-bound path")
    return manifest


def _read_origin(review_root: Path) -> tuple[dict[str, Any], bytes]:
    origin_path = review_root / "workspace" / "origin.json"
    try:
        content = origin_path.read_bytes()
    except OSError as error:
        raise IndependentReviewError(
            f"could not read independent workspace origin: {error}"
        ) from error
    origin = _parse_json_bytes(content, "independent workspace origin")
    _exact_fields(origin, ORIGIN_FIELDS, "independent workspace origin")
    if origin["schema_version"] != ORIGIN_SCHEMA_VERSION:
        raise IndependentReviewError("workspace origin schema is not recognized")
    return origin, content


def _validate_working_annotation(
    working_path: Path,
    expected_template: Mapping[str, Any],
    origin: Mapping[str, Any],
) -> tuple[BallAnnotationSet, bytes]:
    if working_path.is_symlink() or _has_windows_reparse_point(working_path):
        raise IndependentReviewError(
            "working annotation cannot be a symlink or reparse point"
        )
    try:
        working_bytes = working_path.read_bytes()
    except OSError as error:
        raise IndependentReviewError(
            f"could not read working independent annotation: {error}"
        ) from error
    payload = _parse_json_bytes(working_bytes, "working independent annotation")
    try:
        annotation_set = BallAnnotationSet.from_mapping(payload)
    except AnnotationValidationError as error:
        raise IndependentReviewError(
            f"working independent annotation is invalid: {error}"
        ) from error
    if annotation_set.review.status != "draft":
        raise IndependentReviewError(
            "completed independent annotations must remain draft pending "
            "separate adjudication"
        )
    expected_fields = {
        "schema_version": expected_template["schema_version"],
        "annotation_set_id": expected_template["annotation_set_id"],
        "possession_id": expected_template["possession_id"],
        "source_video": expected_template["source_video"],
        "window": expected_template["window"],
        "coordinate_system": expected_template["coordinate_system"],
    }
    actual = annotation_set.to_dict()
    for field, expected in expected_fields.items():
        if actual[field] != expected:
            raise IndependentReviewError(
                f"working independent annotation identity mismatch: {field}"
            )
    expected_review = expected_template["review"]
    if (
        actual["review"]["annotator_id"] in PRIMARY_ANNOTATOR_IDS
        or actual["review"]["annotator_id"] != origin["reviewer_id"]
        or actual["review"]["annotator_id"] != expected_review["annotator_id"]
        or actual["review"]["created_at_utc"]
        != origin["created_at_utc"]
        or actual["review"]["reviewer_id"] is not None
        or actual["review"]["reviewed_at_utc"] is not None
    ):
        raise IndependentReviewError(
            "working independent annotation review identity/time mismatch"
        )
    if working_path.read_bytes() != working_bytes:
        raise IndependentReviewError(
            "working independent annotation changed during validation"
        )
    return annotation_set, working_bytes


def _validate_existing_review(
    review_root: Path,
    repository_root: Path,
    evidence: NeutralEvidence,
    protocol_bytes: bytes,
    reviewer_id: str,
    created_at_utc: str,
    fingerprint: Mapping[str, str],
) -> IndependentReviewResult:
    if not review_root.is_dir():
        raise IndependentReviewError(
            "independent review output exists but is not a directory"
        )
    _reject_tree_links(review_root, "independent review workspace")
    components = binding_components(
        evidence,
        _sha256_bytes(protocol_bytes),
        reviewer_id,
        created_at_utc,
        fingerprint,
        repository_root,
    )
    digest = binding_sha256(components)
    kit_dir = review_root / "kit" / digest
    template_payload = _template_payload(
        evidence.descriptor,
        reviewer_id,
        created_at_utc,
    )
    template_bytes = _serialize_json(template_payload)
    _validate_kit(
        review_root,
        kit_dir,
        repository_root,
        evidence,
        protocol_bytes,
        reviewer_id,
        template_payload,
        template_bytes,
        components,
        digest,
        fingerprint,
    )
    origin, origin_bytes = _read_origin(review_root)
    expected_origin = _origin_payload(
        review_root,
        kit_dir,
        kit_dir / "manifest.json",
        kit_dir / "blank_annotation_template.json",
        template_payload,
        reviewer_id,
        components,
        digest,
    )
    if origin != expected_origin:
        raise IndependentReviewError(
            "workspace origin does not match the immutable kit/identity"
        )
    workspace_dir = review_root / "workspace"
    working_path = workspace_dir / WORKING_FILENAME
    annotation_set, working_bytes = _validate_working_annotation(
        working_path,
        template_payload,
        origin,
    )
    template_path = kit_dir / "blank_annotation_template.json"
    if os.path.samestat(template_path.stat(), working_path.stat()):
        raise IndependentReviewError(
            "working annotation aliases the immutable template"
        )
    if set(path.name for path in review_root.iterdir()) != {"kit", "workspace"}:
        raise IndependentReviewError("independent review root contains extras")
    if set(path.name for path in (review_root / "kit").iterdir()) != {digest}:
        raise IndependentReviewError("independent kit root contains extras")
    if set(path.name for path in workspace_dir.iterdir()) != {
        "origin.json",
        WORKING_FILENAME,
    }:
        raise IndependentReviewError("independent workspace contains extras")
    if (workspace_dir / "origin.json").read_bytes() != origin_bytes:
        raise IndependentReviewError("workspace origin changed during validation")
    if working_path.read_bytes() != working_bytes:
        raise IndependentReviewError(
            "working independent annotation changed during final recheck"
        )
    unlabeled = sum(
        row.annotation_status == "unlabeled"
        for row in annotation_set.annotations
    )
    if unlabeled == EXPECTED_FRAME_COUNT and working_bytes == template_bytes:
        state = "reused_pristine_draft"
    elif unlabeled:
        state = "resumable_partial_draft"
    else:
        state = "resumable_completed_draft"
    return IndependentReviewResult(
        review_root=review_root,
        kit_dir=kit_dir,
        workspace_annotation_path=working_path,
        state=state,
        unlabeled_frame_count=unlabeled,
        completed_frame_count=EXPECTED_FRAME_COUNT - unlabeled,
        lifecycle_status=LIFECYCLE["working_annotation_status"],
        next_step=NEXT_STEP_GUIDANCE,
    )


def _ensure_external_inputs_unchanged(
    repository_root: Path,
    evidence: NeutralEvidence,
    protocol_path: Path,
    protocol_bytes: bytes,
    fingerprint: Mapping[str, str],
) -> None:
    manifest_path = evidence.directory / "manifest.json"
    if manifest_path.read_bytes() != evidence.manifest_bytes:
        raise IndependentReviewError(
            "neutral manifest changed during preparation; nothing was published"
        )
    _reject_tree_links(evidence.directory, "neutral bundle")
    try:
        _validate_existing_owned_bundle(
            evidence.directory,
            evidence.descriptor,
        )
    except ReviewAssetPreparationError as error:
        raise IndependentReviewError(
            "neutral bundle changed during preparation; nothing was published: "
            f"{error}"
        ) from error
    frame_records = evidence.manifest["assets"]["source_frames"]
    for position, (record, expected_pixels) in enumerate(
        zip(frame_records, evidence.frames, strict=True)
    ):
        path = _portable_asset_path(
            evidence.directory,
            record["path"],
            f"neutral source_frames[{position}]",
        )
        decoded = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if decoded is None or not np.array_equal(decoded, expected_pixels):
            raise IndependentReviewError(
                "neutral source frame changed during preparation; "
                "nothing was published"
            )
    if _sha256_file(evidence.source_path) != evidence.descriptor.source_video.sha256:
        raise IndependentReviewError(
            "source video changed during preparation; nothing was published"
        )
    if protocol_path.read_bytes() != protocol_bytes:
        raise IndependentReviewError(
            "annotation protocol changed during preparation; nothing was published"
        )
    if generator_fingerprint() != fingerprint:
        raise IndependentReviewError(
            "independent-review generator/runtime changed during preparation; "
            "nothing was published"
        )
    if not repository_root.is_dir():
        raise IndependentReviewError("repository root disappeared during preparation")


def _atomic_rename_no_replace(source: Path, target: Path) -> None:
    """Atomically rename a directory while refusing any existing target."""

    source_text = str(source.absolute())
    target_text = str(target.absolute())
    if os.name == "nt":
        move_file = ctypes.WinDLL("kernel32", use_last_error=True).MoveFileExW
        move_file.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
        move_file.restype = ctypes.c_int
        movefile_write_through = 0x00000008
        if move_file(source_text, target_text, movefile_write_through):
            return
        error_code = ctypes.get_last_error()
        if error_code in {80, 183}:
            raise IndependentReviewError(
                "independent review target appeared during publication; "
                "nothing was replaced"
            )
        raise IndependentReviewError(
            "could not atomically publish independent review without "
            f"replacement (Windows error {error_code})"
        )

    source_bytes = os.fsencode(source_text)
    target_bytes = os.fsencode(target_text)
    library = ctypes.CDLL(None, use_errno=True)
    if sys.platform.startswith("linux"):
        rename_no_replace = getattr(library, "renameat2", None)
        if rename_no_replace is None:
            raise IndependentReviewError(
                "atomic no-replace directory publication is unavailable on "
                "this Linux runtime"
            )
        rename_no_replace.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        rename_no_replace.restype = ctypes.c_int
        result = rename_no_replace(
            -100,
            source_bytes,
            -100,
            target_bytes,
            1,
        )
    elif sys.platform == "darwin":
        rename_no_replace = getattr(library, "renamex_np", None)
        if rename_no_replace is None:
            raise IndependentReviewError(
                "atomic no-replace directory publication is unavailable on "
                "this macOS runtime"
            )
        rename_no_replace.argtypes = [
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        rename_no_replace.restype = ctypes.c_int
        result = rename_no_replace(source_bytes, target_bytes, 0x00000004)
    else:
        raise IndependentReviewError(
            "atomic no-replace directory publication is unsupported on this "
            f"platform: {sys.platform}"
        )
    if result == 0:
        return
    error_code = ctypes.get_errno()
    if error_code in {errno.EEXIST, errno.ENOTEMPTY}:
        raise IndependentReviewError(
            "independent review target appeared during publication; "
            "nothing was replaced"
        )
    raise IndependentReviewError(
        "could not atomically publish independent review without replacement: "
        f"[errno {error_code}] {os.strerror(error_code)}"
    )


def _publish_no_replace(staging_root: Path, review_root: Path) -> None:
    _atomic_rename_no_replace(staging_root, review_root)


def prepare_independent_review(
    neutral_bundle: Path,
    repository_root: Path,
    reviewer_id: str,
) -> IndependentReviewResult:
    """Create or safely resume one prediction-blind independent workspace."""

    reviewer_id = validate_reviewer_id(reviewer_id)
    repository_root = repository_root.resolve()
    if not repository_root.is_dir():
        raise IndependentReviewError(
            f"repository root does not exist: {repository_root}"
        )
    evidence = validate_neutral_bundle(neutral_bundle, repository_root)
    protocol_path, protocol_bytes, protocol_sha256 = _protocol_snapshot(
        repository_root
    )
    fingerprint = generator_fingerprint()
    review_root = review_root_path(
        repository_root,
        evidence.descriptor,
        reviewer_id,
    )

    if review_root.exists():
        origin, origin_bytes = _read_origin(review_root)
        if origin["reviewer_id"] != reviewer_id:
            raise IndependentReviewError(
                "existing workspace reviewer identity does not match"
            )
        created_at_utc = origin["created_at_utc"]
        working_path = review_root / "workspace" / WORKING_FILENAME
        working_bytes = working_path.read_bytes()
        prevalidated_kit_dir = _portable_asset_path(
            review_root,
            origin["kit_relative_path"],
            "existing workspace kit",
        )
        kit_manifest_path = prevalidated_kit_dir / "manifest.json"
        kit_manifest_bytes = kit_manifest_path.read_bytes()
        result = _validate_existing_review(
            review_root,
            repository_root,
            evidence,
            protocol_bytes,
            reviewer_id,
            created_at_utc,
            fingerprint,
        )
        if result.workspace_annotation_path != working_path:
            raise IndependentReviewError(
                "validated workspace path changed during rerun"
            )
        if result.kit_dir != prevalidated_kit_dir:
            raise IndependentReviewError(
                "validated immutable kit path changed during rerun"
            )
        _ensure_external_inputs_unchanged(
            repository_root,
            evidence,
            protocol_path,
            protocol_bytes,
            fingerprint,
        )
        if (review_root / "workspace" / "origin.json").read_bytes() != origin_bytes:
            raise IndependentReviewError(
                "workspace origin changed during rerun validation"
            )
        if result.workspace_annotation_path.read_bytes() != working_bytes:
            raise IndependentReviewError(
                "working independent annotation changed during late rerun "
                "validation"
            )
        if kit_manifest_path.read_bytes() != kit_manifest_bytes:
            raise IndependentReviewError(
                "immutable kit manifest changed during late rerun validation"
            )
        return result

    created_at_utc = _utc_now()
    components = binding_components(
        evidence,
        protocol_sha256,
        reviewer_id,
        created_at_utc,
        fingerprint,
        repository_root,
    )
    digest = binding_sha256(components)
    template_payload = _template_payload(
        evidence.descriptor,
        reviewer_id,
        created_at_utc,
    )
    template_bytes = _serialize_json(template_payload)
    review_root.parent.mkdir(parents=True, exist_ok=True)
    review_root = review_root_path(
        repository_root,
        evidence.descriptor,
        reviewer_id,
    )
    staging_root = Path(
        tempfile.mkdtemp(
            prefix=f".{reviewer_id}.staging-",
            dir=review_root.parent,
        )
    )
    try:
        kit_dir, working_path = _build_kit_and_workspace(
            staging_root,
            repository_root,
            evidence,
            protocol_bytes,
            reviewer_id,
            template_payload,
            template_bytes,
            components,
            digest,
            fingerprint,
        )
        validation = _validate_existing_review(
            staging_root,
            repository_root,
            evidence,
            protocol_bytes,
            reviewer_id,
            created_at_utc,
            fingerprint,
        )
        if validation.state != "reused_pristine_draft":
            raise IndependentReviewError(
                "new independent workspace is not pristine"
            )
        _ensure_external_inputs_unchanged(
            repository_root,
            evidence,
            protocol_path,
            protocol_bytes,
            fingerprint,
        )
        review_root_path(
            repository_root,
            evidence.descriptor,
            reviewer_id,
        )
        _publish_no_replace(staging_root, review_root)
        return IndependentReviewResult(
            review_root=review_root,
            kit_dir=review_root / kit_dir.relative_to(staging_root),
            workspace_annotation_path=(
                review_root / working_path.relative_to(staging_root)
            ),
            state="created_pristine_draft",
            unlabeled_frame_count=EXPECTED_FRAME_COUNT,
            completed_frame_count=0,
            lifecycle_status=LIFECYCLE["working_annotation_status"],
            next_step=NEXT_STEP_GUIDANCE,
        )
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root)


def validate_independent_editor_target(
    review_root: Path,
    annotation_path: Path,
    repository_root: Path,
    reviewer_id: str,
) -> GuardedEditorTarget:
    """Guard the editor against opening a primary or unrelated draft."""

    reviewer_id = validate_reviewer_id(reviewer_id)
    repository_root = repository_root.resolve()
    dedicated_root = (
        repository_root
        / "data"
        / "outputs"
        / "ball_tracking"
        / "independent_review"
    )
    review_root = _validate_strict_descendant(
        repository_root,
        review_root,
        dedicated_root,
        "independent editor review root",
    )
    if not review_root.is_dir():
        raise IndependentReviewError(
            "independent editor review root is not a directory"
        )
    _reject_tree_links(review_root, "independent editor review root")
    fixed_target = review_root / "workspace" / WORKING_FILENAME
    if annotation_path.absolute() != fixed_target.absolute():
        raise IndependentReviewError(
            "editor target is not the fixed independent workspace annotation; "
            "primary or arbitrary annotation paths are forbidden"
        )
    origin, origin_bytes = _read_origin(review_root)
    if origin["reviewer_id"] != reviewer_id:
        raise IndependentReviewError("editor target reviewer identity mismatch")
    if origin["working_annotation_relative_path"] != (
        f"workspace/{WORKING_FILENAME}"
    ):
        raise IndependentReviewError("workspace origin working path is invalid")
    kit_dir = _portable_asset_path(
        review_root,
        origin["kit_relative_path"],
        "workspace origin kit",
    )
    kit_manifest = kit_dir / "manifest.json"
    if not kit_manifest.is_file() or _sha256_file(kit_manifest) != origin[
        "kit_manifest_sha256"
    ]:
        raise IndependentReviewError("editor target kit binding is invalid")
    manifest = _parse_json_bytes(
        kit_manifest.read_bytes(),
        "independent kit manifest",
    )
    _exact_fields(manifest, KIT_TOP_LEVEL_FIELDS, "independent kit manifest")
    neutral = _exact_fields(
        manifest["neutral_bundle"],
        NEUTRAL_BINDING_FIELDS,
        "kit neutral_bundle",
    )
    neutral_path = _portable_asset_path(
        repository_root,
        neutral["path"],
        "kit neutral bundle",
    )
    evidence = validate_neutral_bundle(neutral_path, repository_root)
    protocol_path, protocol_bytes, _protocol_sha256 = _protocol_snapshot(
        repository_root
    )
    fingerprint = generator_fingerprint()
    expected_review_root = review_root_path(
        repository_root,
        evidence.descriptor,
        reviewer_id,
    )
    if review_root != expected_review_root:
        raise IndependentReviewError(
            "editor review root does not match the neutral evidence and "
            "reviewer identity"
        )
    validation = _validate_existing_review(
        review_root,
        repository_root,
        evidence,
        protocol_bytes,
        reviewer_id,
        origin["created_at_utc"],
        fingerprint,
    )
    if validation.workspace_annotation_path != fixed_target:
        raise IndependentReviewError(
            "editor target differs from the fully validated workspace"
        )
    template_path = _portable_asset_path(
        review_root,
        origin["template_relative_path"],
        "workspace origin template",
    )
    if not template_path.is_file() or _sha256_file(template_path) != origin[
        "template_sha256"
    ]:
        raise IndependentReviewError("editor target pristine template is invalid")
    template = _parse_json_bytes(
        template_path.read_bytes(),
        "independent blank template",
    )
    annotation_set, working_bytes = _validate_working_annotation(
        fixed_target,
        template,
        origin,
    )
    if annotation_set.annotation_set_id != origin["annotation_set_id"]:
        raise IndependentReviewError(
            "editor target annotation_set_id does not match workspace origin"
        )
    if annotation_set.review.annotator_id != reviewer_id or (
        annotation_set.review.annotator_id in PRIMARY_ANNOTATOR_IDS
    ):
        raise IndependentReviewError(
            "editor target annotator identity is not the independent reviewer"
        )
    _ensure_external_inputs_unchanged(
        repository_root,
        evidence,
        protocol_path,
        protocol_bytes,
        fingerprint,
    )
    if (review_root / "workspace" / "origin.json").read_bytes() != origin_bytes:
        raise IndependentReviewError("editor target origin changed during guard")
    if fixed_target.read_bytes() != working_bytes:
        raise IndependentReviewError("editor target changed during guard")
    return GuardedEditorTarget(
        annotation_path=fixed_target,
        annotation_bytes=working_bytes,
        origin_path=review_root / "workspace" / "origin.json",
        origin_bytes=origin_bytes,
        repository_root=repository_root,
        source_path=evidence.source_path,
        annotation_set=annotation_set,
    )


def _recheck_guarded_editor_snapshot(target: GuardedEditorTarget) -> None:
    if target.annotation_path.read_bytes() != target.annotation_bytes:
        raise IndependentReviewError(
            "independent annotation changed after the editor guard; editor "
            "was not opened"
        )
    if target.origin_path.read_bytes() != target.origin_bytes:
        raise IndependentReviewError(
            "independent workspace origin changed after the editor guard; "
            "editor was not opened"
        )


def _invoke_annotation_editor(
    argv: Sequence[str],
    target: GuardedEditorTarget,
) -> int:
    _recheck_guarded_editor_snapshot(target)
    from src.ball_tracking import annotate_frames as editor

    original_prepare = editor.prepare_annotation_session

    def prepare_verified_session(
        annotation_path: Path,
        repository_root: Path,
    ) -> Any:
        if annotation_path.absolute() != target.annotation_path.absolute():
            raise IndependentReviewError(
                "editor requested an annotation path other than the guarded "
                "independent target"
            )
        if repository_root.resolve() != target.repository_root:
            raise IndependentReviewError(
                "editor requested a repository root other than the guarded "
                "repository"
            )
        return editor.AnnotationSession(
            annotation_path=target.annotation_path,
            repository_root=target.repository_root,
            source_path=target.source_path,
            annotation_set=target.annotation_set,
        )

    editor.prepare_annotation_session = prepare_verified_session
    try:
        return editor.main(argv)
    finally:
        editor.prepare_annotation_session = original_prepare


def launch_independent_editor(
    neutral_bundle: Path,
    repository_root: Path,
    reviewer_id: str,
) -> int:
    result = prepare_independent_review(
        neutral_bundle,
        repository_root,
        reviewer_id,
    )
    target = validate_independent_editor_target(
        result.review_root,
        result.workspace_annotation_path,
        repository_root,
        reviewer_id,
    )
    return _invoke_annotation_editor(
        [
            "--annotations",
            str(target.annotation_path),
            "--repository-root",
            str(repository_root.resolve()),
        ],
        target,
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare or resume a prediction-blind independent ball review "
            "from a verified neutral bundle."
        )
    )
    parser.add_argument("--neutral-bundle", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--reviewer-id", required=True)
    parser.add_argument(
        "--launch-editor",
        action="store_true",
        help="Open only the guarded independent workspace after validation.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    try:
        if args.launch_editor:
            exit_code = launch_independent_editor(
                args.neutral_bundle,
                args.repository_root,
                args.reviewer_id,
            )
            if exit_code == 0:
                print("Independent editor closed; the workspace remains draft.")
                print(f"Next step: {NEXT_STEP_GUIDANCE}")
            return exit_code
        result = prepare_independent_review(
            args.neutral_bundle,
            args.repository_root,
            args.reviewer_id,
        )
    except (IndependentReviewError, OSError) as error:
        raise SystemExit(f"Independent review preparation error: {error}") from error
    print("Independent review workspace is ready.")
    print(f"State: {result.state}")
    print(f"Immutable kit: {result.kit_dir}")
    print(f"Working annotation: {result.workspace_annotation_path}")
    print(f"Unlabeled frames: {result.unlabeled_frame_count}")
    print(f"Lifecycle status: {result.lifecycle_status}")
    print(f"Next step: {result.next_step}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
