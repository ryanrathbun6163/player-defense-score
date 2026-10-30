"""Versioned development manifests; no annotations are opened by this loader."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .detector_experiments import (
    DetectorExperiment, DetectorExperimentValidationError, ExperimentWindow,
    SCHEMA_VERSION as PARENT_SCHEMA, _reject_duplicate_object_keys,
    _reject_forbidden_keys, _require_exact_fields, _require_identifier,
    _require_mapping,
)

SCHEMA_VERSION = "ball_detector_experiment/v0.2"
PURPOSES = ("representative_evaluation", "challenge_evaluation")
EXPERIMENT_ID = "rfdetr_medium_development_evaluation_v0_2"
EXPERIMENT_ROOT = "configs/ball_tracking/experiments"
REVIEW_ROOT = "configs/ball_tracking/reviews"
PROPOSAL_ROOT = "configs/ball_tracking/proposals"
PARENT_FILENAME = "rfdetr_medium_image_only_baseline_v0_1.json"
PARENT_SHA256 = "7d82faec9f4d0615a0e870372392a9a9d4f2576ada88e700bec2fd8b3b28d3e3"
TOP_FIELDS = frozenset({
    "schema_version", "experiment_id", "experiment_purpose",
    "parent_experiment", "release_authorization", "detector", "scoring_grid",
    "leakage_controls", "windows", "sealed_holdouts",
})


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def closed(value: Any, fields: set[str] | frozenset[str], label: str) -> dict:
    value = _require_mapping(value, label)
    _require_exact_fields(value, frozenset(fields), label)
    return dict(value)


def require_digest(value: Any, label: str, length: int = 64) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        rf"[0-9a-f]{{{length}}}", value,
    ):
        raise DetectorExperimentValidationError(f"Invalid {label} digest")
    return value


def portable_path(raw: Any, prefix: str | None = None) -> PurePosixPath:
    if not isinstance(raw, str) or not raw or any(c in raw for c in '\\:*?<>|"'):
        raise DetectorExperimentValidationError("Invalid portable path")
    path = PurePosixPath(raw)
    if path.is_absolute() or str(path) != raw or any(
        part in {"", ".", ".."} or part.endswith((".", " "))
        or any(ord(c) < 32 for c in part)
        or part.split(".")[0].casefold() in {
            "con", "prn", "aux", "nul",
            *(f"com{i}" for i in range(1, 10)),
            *(f"lpt{i}" for i in range(1, 10)),
        }
        for part in raw.split("/")
    ):
        raise DetectorExperimentValidationError("Unsafe portable path")
    if prefix and (
        path.parts[:len(PurePosixPath(prefix).parts)] != PurePosixPath(prefix).parts
        or len(path.parts) <= len(PurePosixPath(prefix).parts)
    ):
        raise DetectorExperimentValidationError(f"Path must be below {prefix}")
    return path


def safe_path(root: Path, raw: Any, prefix: str | None = None) -> Path:
    path = portable_path(raw, prefix)
    current = root.resolve()
    for part in path.parts:
        current = current / part
        if current.is_symlink() or (
            current.exists()
            and getattr(current.lstat(), "st_file_attributes", 0) & 0x400
        ):
            raise DetectorExperimentValidationError("Symlink/reparse path forbidden")
    current.resolve().relative_to(root.resolve())
    return current


def binding(value: Any, prefix: str) -> dict[str, str]:
    result = closed(value, {"path", "sha256"}, "file binding")
    path = portable_path(result["path"], prefix)
    if path.suffix != ".json":
        raise DetectorExperimentValidationError("Binding must name JSON")
    require_digest(result["sha256"], "file")
    return result


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream, object_pairs_hook=_reject_duplicate_object_keys)
    return dict(_require_mapping(value, str(path)))


def bound_file(root: Path, value: Any, prefix: str) -> Path:
    record = binding(value, prefix)
    path = safe_path(root, record["path"], prefix)
    if not path.is_file() or sha256_file(path) != record["sha256"]:
        raise DetectorExperimentValidationError(f"File binding mismatch: {path}")
    return path


def window_identity(window: ExperimentWindow) -> dict:
    return {
        "annotation_set_id": window.annotation_set_id,
        "possession_id": window.possession_id,
        "source_video": window.source_video.to_dict(),
        "start_frame_index": window.start_frame_index,
        "end_frame_index": window.end_frame_index,
        "selection_purpose": window.selection_purpose,
    }


def development_windows(parent: DetectorExperiment) -> tuple[ExperimentWindow, ...]:
    return tuple(w for w in parent.windows if w.selection_purpose in PURPOSES)


def planned_window(parent_window: ExperimentWindow) -> dict:
    result = parent_window.to_dict()
    stem = (
        f"{parent_window.possession_id}_frames_"
        f"{parent_window.start_frame_index:04d}_{parent_window.end_frame_index:04d}"
    )
    result.update(
        window_id=parent_window.window_id + "_development_v0_2",
        detection_run_id=stem + "_rfdetr_medium_development_v0_2",
        execution_status="ready_for_inference",
        output_path=(f"data/outputs/ball_tracking/detections/{EXPERIMENT_ID}/"
                     f"{stem}_rfdetr_medium_development_v0_2.json"),
    )
    return result


def execution_spec_sha256(payload: Mapping[str, Any]) -> str:
    return canonical_sha256({
        key: value for key, value in payload.items() if key != "release_authorization"
    })


@dataclass(frozen=True)
class DevelopmentExperiment:
    payload: Mapping[str, Any]
    parent: DetectorExperiment
    windows: tuple[ExperimentWindow, ...]

    @property
    def schema_version(self): return SCHEMA_VERSION

    @property
    def experiment_id(self): return self.payload["experiment_id"]

    @property
    def detector(self): return self.parent.detector

    @property
    def scoring_grid(self): return self.parent.scoring_grid

    @property
    def ready_windows(self): return self.windows

    def windows_for_inference(self): return self.windows

    def to_dict(self): return copy.deepcopy(dict(self.payload))


def load_development_experiment(payload: Any, manifest_path: Path) -> DevelopmentExperiment:
    payload = closed(payload, TOP_FIELDS, "development experiment")
    _reject_forbidden_keys(payload)
    if payload["schema_version"] != SCHEMA_VERSION or (
        payload["experiment_id"] != EXPERIMENT_ID
        or payload["experiment_purpose"] != "image_only_ball_detector_development"
    ):
        raise DetectorExperimentValidationError("Invalid development identity")
    _require_identifier(payload["experiment_id"], "experiment_id")
    root = manifest_path.parent.parent.parent.parent
    if safe_path(root, f"{EXPERIMENT_ROOT}/{manifest_path.name}") != manifest_path:
        raise DetectorExperimentValidationError("Manifest outside registry")
    parent_record = binding(payload["parent_experiment"], EXPERIMENT_ROOT)
    if parent_record != {"path": f"{EXPERIMENT_ROOT}/{PARENT_FILENAME}",
                         "sha256": PARENT_SHA256}:
        raise DetectorExperimentValidationError("Development parent is not the frozen precommit")
    parent_path = bound_file(root, parent_record, EXPERIMENT_ROOT)
    parent = DetectorExperiment.from_mapping(read_json(parent_path))
    if parent.schema_version != PARENT_SCHEMA:
        raise DetectorExperimentValidationError("Parent must use v0.1")
    binding(payload["release_authorization"], REVIEW_ROOT)
    for key in ("detector", "scoring_grid", "leakage_controls"):
        if canonical_sha256(payload[key]) != canonical_sha256(parent.to_dict()[key]):
            raise DetectorExperimentValidationError(f"Development changed frozen {key}")
    expected = [planned_window(w) for w in development_windows(parent)]
    if canonical_sha256(payload["windows"]) != canonical_sha256(expected):
        raise DetectorExperimentValidationError("Development windows must exactly match all six parent bindings")
    sealed = [window_identity(w) for w in parent.windows
              if w.selection_purpose == "test_holdout"]
    if canonical_sha256(payload["sealed_holdouts"]) != canonical_sha256(sealed):
        raise DetectorExperimentValidationError("Sealed holdouts differ from parent")
    windows = tuple(ExperimentWindow.from_mapping(w, i, development=True)
                    for i, w in enumerate(payload["windows"]))
    return DevelopmentExperiment(copy.deepcopy(payload), parent, windows)
