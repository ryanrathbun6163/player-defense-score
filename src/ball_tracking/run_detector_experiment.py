"""Run a precommitted, label-blind RF-DETR experiment safely.

This module reads only the detector-experiment manifest and source video.  It
never reads annotation files or frame-level labels.  Heavy computer-vision and
model dependencies remain behind execution-time callables.  Dry-run verifies
the declared CUDA runtime but skips model construction and inference; unit tests
can substitute those callables and remain CPU-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from importlib.metadata import version as installed_package_version
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from .annotations import SourceVideo, verify_source_video_contract
from .detections import (
    SCHEMA_VERSION as DETECTION_SCHEMA_VERSION,
    BallDetection,
    BallDetectionRun,
    DetectionRunValidationError,
    ModelProvenance,
    load_detection_run,
)
from .detector_experiments import (
    DetectorExperiment,
    DetectorExperimentValidationError,
    ExperimentWindow,
    build_model_provenance,
    load_detector_experiment,
)
from .rfdetr_adapter import RFDETRBallAdapter


COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
EXPERIMENT_ROOT_PARTS = ("configs", "ball_tracking", "experiments")
OUTPUT_ROOT_PARTS = ("data", "outputs", "ball_tracking", "detections")
PENDING_REASON = "pending image-only inference"


class DetectorExperimentRunnerError(RuntimeError):
    """Raised when preflight or experiment execution cannot safely continue."""


class DetectorExperimentIncompleteError(DetectorExperimentRunnerError):
    """Raised after evidence is persisted but one or more frames are incomplete."""


@dataclass(frozen=True)
class GitSnapshot:
    repository_root: Path
    head: str
    clean: bool
    manifest_tracked: bool
    manifest_matches_head: bool = True
    tracked_experiment_manifests: tuple[PurePosixPath, ...] = ()
    all_experiment_manifests_match_head: bool = True


@dataclass
class OutputClaim:
    expected_run: BallDetectionRun | None


@dataclass(frozen=True)
class PreparedWindow:
    window: ExperimentWindow
    source_path: Path
    output_path: Path
    existing_run: BallDetectionRun | None
    output_claim: OutputClaim

    @property
    def pending_frame_indices(self) -> tuple[int, ...]:
        if self.existing_run is None:
            return tuple(
                range(
                    self.window.start_frame_index,
                    self.window.end_frame_index + 1,
                )
            )

        return tuple(
            frame.frame_index
            for frame in self.existing_run.frames
            if frame.inference_status == "not_run"
        )


@dataclass(frozen=True)
class PreflightResult:
    repository_root: Path
    experiment_path: Path
    experiment: DetectorExperiment
    head: str
    model_provenance: ModelProvenance
    weights_path: Path
    windows: tuple[PreparedWindow, ...]


@dataclass(frozen=True)
class ExperimentRunSummary:
    dry_run: bool
    head: str
    window_count: int
    completed_frame_count: int
    incomplete_frame_count: int
    output_paths: tuple[Path, ...]


ExperimentLoader = Callable[[Path], DetectorExperiment]
GitInspector = Callable[[Path, PurePosixPath], GitSnapshot]
PackageVersionReader = Callable[[str], str]
RuntimeDeviceInspector = Callable[[], str]
WeightsPathResolver = Callable[[Any], Path]
FileHasher = Callable[[Path], str]
SourceVerifier = Callable[[SourceVideo, Path], dict[str, Any]]
IgnoreChecker = Callable[[Path, PurePosixPath], bool]
DetectionRunLoader = Callable[[Path], BallDetectionRun]
ProvenanceBuilder = Callable[..., ModelProvenance]
AdapterFactory = Callable[[Path, float], Any]
CaptureFactory = Callable[[Path], Any]
ColorConverter = Callable[[Any], Any]
RunWriter = Callable[[BallDetectionRun, Path], None]


@dataclass(frozen=True)
class RunnerDependencies:
    load_experiment: ExperimentLoader
    inspect_git: GitInspector
    read_package_version: PackageVersionReader
    inspect_runtime_device: RuntimeDeviceInspector
    resolve_weights_path: WeightsPathResolver
    hash_file: FileHasher
    verify_source: SourceVerifier
    is_git_ignored: IgnoreChecker
    load_run: DetectionRunLoader
    build_provenance: ProvenanceBuilder
    create_adapter: AdapterFactory
    open_capture: CaptureFactory
    bgr_to_rgb: ColorConverter
    write_run: RunWriter


def _run_git(repository_root: Path, *arguments: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", *arguments],
            cwd=repository_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError as error:
        raise DetectorExperimentRunnerError(
            f"Could not execute Git: {error}"
        ) from error


def _require_git_success(
    result: subprocess.CompletedProcess,
    description: str,
) -> str:
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        suffix = f": {detail}" if detail else ""
        raise DetectorExperimentRunnerError(
            f"Git could not {description}{suffix}"
        )

    return result.stdout.strip()


def inspect_git_repository(
    repository_root: Path,
    manifest_path: PurePosixPath,
) -> GitSnapshot:
    """Read the exact Git root, HEAD, cleanliness, and manifest tracking state."""

    reported_root = _require_git_success(
        _run_git(repository_root, "rev-parse", "--show-toplevel"),
        "resolve the repository root",
    )
    head = _require_git_success(
        _run_git(repository_root, "rev-parse", "--verify", "HEAD"),
        "resolve HEAD",
    )
    status = _require_git_success(
        _run_git(
            repository_root,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ),
        "inspect worktree status",
    )
    tracked_result = _run_git(
        repository_root,
        "ls-files",
        "--error-unmatch",
        "--",
        manifest_path.as_posix(),
    )
    experiment_listing = _run_git(
        repository_root,
        "ls-files",
        "-z",
        "--",
        "/".join(EXPERIMENT_ROOT_PARTS),
    )
    _require_git_success(
        experiment_listing,
        "list committed detector-experiment manifests",
    )
    tracked_experiment_manifests = tuple(
        PurePosixPath(item)
        for item in experiment_listing.stdout.split("\0")
        if item and PurePosixPath(item).suffix == ".json"
    )
    manifest_matches_head = False

    if tracked_result.returncode == 0:
        worktree_blob = _require_git_success(
            _run_git(
                repository_root,
                "hash-object",
                "--",
                manifest_path.as_posix(),
            ),
            "hash the experiment manifest",
        )
        head_blob = _require_git_success(
            _run_git(
                repository_root,
                "rev-parse",
                f"HEAD:{manifest_path.as_posix()}",
            ),
            "resolve the committed experiment manifest",
        )
        manifest_matches_head = bool(worktree_blob) and worktree_blob == head_blob

    all_experiment_manifests_match_head = True

    for tracked_manifest in tracked_experiment_manifests:
        worktree_blob = _require_git_success(
            _run_git(
                repository_root,
                "hash-object",
                "--",
                tracked_manifest.as_posix(),
            ),
            f"hash detector-experiment manifest {tracked_manifest}",
        )
        head_blob = _require_git_success(
            _run_git(
                repository_root,
                "rev-parse",
                f"HEAD:{tracked_manifest.as_posix()}",
            ),
            f"resolve committed detector-experiment manifest "
            f"{tracked_manifest}",
        )
        all_experiment_manifests_match_head = (
            all_experiment_manifests_match_head
            and bool(worktree_blob)
            and worktree_blob == head_blob
        )

    return GitSnapshot(
        repository_root=Path(reported_root).resolve(),
        head=head,
        clean=not bool(status),
        manifest_tracked=tracked_result.returncode == 0,
        manifest_matches_head=manifest_matches_head,
        tracked_experiment_manifests=tracked_experiment_manifests,
        all_experiment_manifests_match_head=(
            all_experiment_manifests_match_head
        ),
    )


def resolve_weights_path(detector: Any) -> Path:
    """Mirror RF-DETR's cache-location rule without importing RF-DETR."""

    configured_root = os.environ.get("RF_HOME")

    if configured_root is None:
        cache_root = Path.home() / ".roboflow" / "models"
    else:
        cache_root = Path(configured_root).expanduser()

    return Path(
        os.path.abspath(cache_root / detector.weights_identifier)
    )


def inspect_cuda_runtime_device() -> str:
    """Observe the concrete CUDA device and runtime without constructing a model."""

    try:
        import torch
    except Exception as error:
        raise DetectorExperimentRunnerError(
            f"Could not import PyTorch for CUDA preflight: {error}"
        ) from error

    try:
        if not torch.cuda.is_available():
            raise DetectorExperimentRunnerError(
                "CUDA must be available for the frozen detector experiment"
            )

        device_index = torch.cuda.current_device()
        gpu_name = str(torch.cuda.get_device_name(device_index)).strip()
        torch_version = str(torch.__version__).strip()
        cuda_runtime = str(torch.version.cuda).strip()
        cudnn_version = torch.backends.cudnn.version()
    except DetectorExperimentRunnerError:
        raise
    except Exception as error:
        raise DetectorExperimentRunnerError(
            f"Could not inspect the CUDA runtime: {error}"
        ) from error

    if (
        isinstance(device_index, bool)
        or not isinstance(device_index, int)
        or device_index < 0
    ):
        raise DetectorExperimentRunnerError(
            f"CUDA returned an invalid current-device index: {device_index!r}"
        )

    observed_fields = {
        "gpu": gpu_name,
        "torch": torch_version,
        "cuda_runtime": cuda_runtime,
    }

    for label, value in observed_fields.items():
        if (
            not value
            or value.casefold() == "none"
            or not value.isprintable()
            or "\n" in value
            or "\r" in value
        ):
            raise DetectorExperimentRunnerError(
                f"CUDA preflight returned an invalid {label}: {value!r}"
            )

    if cudnn_version is not None and (
        isinstance(cudnn_version, bool)
        or not isinstance(cudnn_version, int)
        or cudnn_version < 0
    ):
        raise DetectorExperimentRunnerError(
            f"CUDA preflight returned an invalid cuDNN version: "
            f"{cudnn_version!r}"
        )

    cudnn_description = "none" if cudnn_version is None else str(cudnn_version)
    return (
        f"cuda:{device_index} | gpu={gpu_name}; torch={torch_version}; "
        f"cuda_runtime={cuda_runtime}; cudnn={cudnn_description}"
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def is_git_ignored(
    repository_root: Path,
    relative_path: PurePosixPath,
) -> bool:
    result = _run_git(
        repository_root,
        "check-ignore",
        "--quiet",
        "--",
        relative_path.as_posix(),
    )

    if result.returncode == 0:
        return True

    if result.returncode == 1:
        return False

    detail = result.stderr.strip() or result.stdout.strip()
    raise DetectorExperimentRunnerError(
        "Git could not evaluate output ignore status"
        + (f": {detail}" if detail else "")
    )


def create_adapter(
    weights_path: Path,
    export_confidence_floor: float,
) -> RFDETRBallAdapter:
    return RFDETRBallAdapter(
        weights_path=weights_path,
        export_confidence_floor=export_confidence_floor,
    )


def open_video_capture(source_path: Path) -> Any:
    import cv2

    return cv2.VideoCapture(str(source_path))


def convert_bgr_to_rgb(frame_bgr: Any) -> Any:
    import cv2

    return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)


def atomic_write_detection_run(run: BallDetectionRun, output_path: Path) -> None:
    """Atomically replace one schema-validated run JSON."""

    validated = BallDetectionRun.from_mapping(run.to_dict())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        dir=output_path.parent,
    )
    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output_file:
            json.dump(
                validated.to_dict(),
                output_file,
                indent=2,
                ensure_ascii=False,
            )
            output_file.write("\n")
            output_file.flush()
            os.fsync(output_file.fileno())

        os.replace(temporary_path, output_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def default_dependencies() -> RunnerDependencies:
    return RunnerDependencies(
        load_experiment=load_detector_experiment,
        inspect_git=inspect_git_repository,
        read_package_version=installed_package_version,
        inspect_runtime_device=inspect_cuda_runtime_device,
        resolve_weights_path=resolve_weights_path,
        hash_file=sha256_file,
        verify_source=verify_source_video_contract,
        is_git_ignored=is_git_ignored,
        load_run=load_detection_run,
        build_provenance=build_model_provenance,
        create_adapter=create_adapter,
        open_capture=open_video_capture,
        bgr_to_rgb=convert_bgr_to_rgb,
        write_run=atomic_write_detection_run,
    )


def _path_is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False

    return True


def _reject_symlink_components(
    repository_root: Path,
    relative_path: PurePosixPath,
    *,
    label: str,
) -> Path:
    if (
        relative_path.is_absolute()
        or not relative_path.parts
        or any(part in {"", ".", ".."} for part in relative_path.parts)
        or any(":" in part for part in relative_path.parts)
    ):
        raise DetectorExperimentRunnerError(
            f"{label} must be a normalized repository-relative path"
        )

    candidate = repository_root.joinpath(*relative_path.parts)
    current = repository_root

    for position, part in enumerate(relative_path.parts):
        current = current / part

        if current.is_symlink():
            raise DetectorExperimentRunnerError(
                f"{label} must not traverse a symlink: {current}"
            )

        if (
            position < len(relative_path.parts) - 1
            and current.exists()
            and not current.is_dir()
        ):
            raise DetectorExperimentRunnerError(
                f"{label} has a non-directory parent component: {current}"
            )

    resolved = candidate.resolve()

    if not _path_is_relative_to(resolved, repository_root):
        raise DetectorExperimentRunnerError(
            f"{label} escapes the repository root: {relative_path.as_posix()}"
        )

    return candidate


def _reject_absolute_symlink_components(path: Path, *, label: str) -> Path:
    absolute_path = Path(os.path.abspath(path))

    if not absolute_path.is_absolute():
        raise DetectorExperimentRunnerError(
            f"{label} must resolve from an absolute path"
        )

    current = Path(absolute_path.anchor)
    remaining_parts = absolute_path.parts[1:]

    for position, part in enumerate(remaining_parts):
        current = current / part

        if current.is_symlink():
            raise DetectorExperimentRunnerError(
                f"{label} must not traverse a symlink: {current}"
            )

        if (
            position < len(remaining_parts) - 1
            and current.exists()
            and not current.is_dir()
        ):
            raise DetectorExperimentRunnerError(
                f"{label} has a non-directory parent component: {current}"
            )

    return absolute_path


def _resolve_manifest_path(
    repository_root: Path,
    experiment_path: Path,
) -> tuple[Path, PurePosixPath]:
    if ".." in experiment_path.parts:
        raise DetectorExperimentRunnerError(
            "Experiment manifest path must not contain parent traversal"
        )

    candidate = (
        experiment_path
        if experiment_path.is_absolute()
        else repository_root / experiment_path
    )
    absolute_candidate = Path(os.path.abspath(candidate))

    if not _path_is_relative_to(absolute_candidate, repository_root):
        raise DetectorExperimentRunnerError(
            "Experiment manifest must stay within the repository root"
        )

    relative = PurePosixPath(
        absolute_candidate.relative_to(repository_root).as_posix()
    )

    if (
        tuple(relative.parts[: len(EXPERIMENT_ROOT_PARTS)])
        != EXPERIMENT_ROOT_PARTS
        or len(relative.parts) <= len(EXPERIMENT_ROOT_PARTS)
        or relative.suffix != ".json"
    ):
        raise DetectorExperimentRunnerError(
            "Experiment manifest must be a .json file beneath "
            "configs/ball_tracking/experiments"
        )

    checked = _reject_symlink_components(
        repository_root,
        relative,
        label="Experiment manifest path",
    )

    resolved = checked.resolve()

    if not _path_is_relative_to(resolved, repository_root):
        raise DetectorExperimentRunnerError(
            "Resolved experiment manifest escapes the repository root"
        )

    if not checked.is_file():
        raise DetectorExperimentRunnerError(
            f"Experiment manifest does not exist: {checked}"
        )

    return checked, relative


def _validate_git_snapshot(
    snapshot: GitSnapshot,
    repository_root: Path,
    manifest_path: PurePosixPath,
) -> str:
    if snapshot.repository_root.resolve() != repository_root:
        raise DetectorExperimentRunnerError(
            "--repository-root does not match Git's exact top-level root"
        )

    if not COMMIT_PATTERN.fullmatch(snapshot.head):
        raise DetectorExperimentRunnerError(
            "Git HEAD must be exactly 40 lowercase hexadecimal characters"
        )

    if not snapshot.clean:
        raise DetectorExperimentRunnerError(
            "Git worktree must be exactly clean before detector inference"
        )

    if not snapshot.manifest_tracked:
        raise DetectorExperimentRunnerError(
            "Experiment manifest must be committed at the clean Git HEAD"
        )

    if not snapshot.manifest_matches_head:
        raise DetectorExperimentRunnerError(
            "Experiment manifest bytes must exactly match the Git HEAD blob"
        )

    tracked_manifests = snapshot.tracked_experiment_manifests

    if not tracked_manifests or manifest_path not in tracked_manifests:
        raise DetectorExperimentRunnerError(
            "Experiment manifest must appear in the committed experiment "
            "registry at Git HEAD"
        )

    if len(set(tracked_manifests)) != len(tracked_manifests):
        raise DetectorExperimentRunnerError(
            "Committed experiment registry contains duplicate manifest paths"
        )

    for tracked_manifest in tracked_manifests:
        if (
            tuple(
                tracked_manifest.parts[: len(EXPERIMENT_ROOT_PARTS)]
            )
            != EXPERIMENT_ROOT_PARTS
            or len(tracked_manifest.parts) <= len(EXPERIMENT_ROOT_PARTS)
            or tracked_manifest.suffix != ".json"
        ):
            raise DetectorExperimentRunnerError(
                "Committed experiment registry contains an unsafe path: "
                f"{tracked_manifest}"
            )

    if not snapshot.all_experiment_manifests_match_head:
        raise DetectorExperimentRunnerError(
            "Every tracked detector-experiment manifest must exactly match "
            "its Git HEAD blob"
        )

    return snapshot.head


def _validate_global_manifest_claims(
    *,
    repository_root: Path,
    current_manifest_path: Path,
    current_experiment: DetectorExperiment,
    tracked_manifest_paths: tuple[PurePosixPath, ...],
    dependencies: RunnerDependencies,
) -> None:
    claims: dict[str, dict[Any, tuple[PurePosixPath, str]]] = {
        "detection_run_id": {},
        "output_path": {},
        "window_id": {},
    }

    for relative_path in tracked_manifest_paths:
        manifest_path = _reject_symlink_components(
            repository_root,
            relative_path,
            label=f"Tracked experiment manifest {relative_path}",
        )

        if not manifest_path.is_file():
            raise DetectorExperimentRunnerError(
                f"Tracked experiment manifest is missing: {manifest_path}"
            )

        if manifest_path == current_manifest_path:
            experiment = current_experiment
        else:
            try:
                experiment = dependencies.load_experiment(manifest_path)
            except Exception as error:
                raise DetectorExperimentRunnerError(
                    f"Could not load tracked detector-experiment manifest "
                    f"{manifest_path}: {error}"
                ) from error

        for window in experiment.windows:
            values = {
                "detection_run_id": window.detection_run_id,
                "output_path": window.output_path.as_posix().casefold(),
                "window_id": window.window_id,
            }

            for field, value in values.items():
                prior = claims[field].get(value)

                if prior is not None:
                    prior_manifest, prior_window = prior
                    raise DetectorExperimentRunnerError(
                        f"Tracked detector-experiment manifests must have "
                        f"globally unique {field}; {relative_path} window "
                        f"{window.window_id!r} conflicts with "
                        f"{prior_manifest} window {prior_window!r}"
                    )

                claims[field][value] = (
                    relative_path,
                    window.window_id,
                )


def _validate_package_and_weights(
    experiment: DetectorExperiment,
    dependencies: RunnerDependencies,
) -> Path:
    detector = experiment.detector

    try:
        actual_version = dependencies.read_package_version(
            detector.package_name
        )
    except Exception as error:
        raise DetectorExperimentRunnerError(
            f"Could not inspect package {detector.package_name!r}: {error}"
        ) from error

    if actual_version != detector.package_version:
        raise DetectorExperimentRunnerError(
            f"Installed {detector.package_name} version does not match the "
            f"manifest: expected {detector.package_version!r}, "
            f"received {actual_version!r}"
        )

    try:
        resolved_by_package_rule = dependencies.resolve_weights_path(detector)
    except Exception as error:
        raise DetectorExperimentRunnerError(
            f"Could not resolve frozen detector weights: {error}"
        ) from error

    unresolved_weights_path = _reject_absolute_symlink_components(
        resolved_by_package_rule,
        label="Frozen detector weights path",
    )
    weights_path = unresolved_weights_path.resolve()

    if not weights_path.is_file():
        raise DetectorExperimentRunnerError(
            f"Frozen detector weights are missing: {weights_path}"
        )

    try:
        actual_hash = dependencies.hash_file(weights_path)
    except Exception as error:
        raise DetectorExperimentRunnerError(
            f"Could not hash frozen detector weights {weights_path}: {error}"
        ) from error

    if actual_hash != detector.weights_sha256:
        raise DetectorExperimentRunnerError(
            "Frozen detector weights SHA-256 does not match the manifest: "
            f"expected {detector.weights_sha256}, received {actual_hash}"
        )

    return weights_path


def _validate_sources(
    windows: tuple[ExperimentWindow, ...],
    repository_root: Path,
    dependencies: RunnerDependencies,
) -> dict[tuple[Any, ...], Path]:
    verified_paths: dict[tuple[Any, ...], Path] = {}

    for window in windows:
        source = window.source_video
        key = (
            source.path.as_posix(),
            source.sha256,
            source.width_px,
            source.height_px,
            source.fps,
            source.frame_count,
        )

        if key in verified_paths:
            continue

        source_candidate = _reject_symlink_components(
            repository_root,
            source.path,
            label=f"Source-video path for {window.window_id}",
        )

        try:
            dependencies.verify_source(source, repository_root)
        except Exception as error:
            raise DetectorExperimentRunnerError(
                f"Source-video preflight failed for {source.path}: {error}"
            ) from error

        source_path = source_candidate.resolve()

        if not _path_is_relative_to(source_path, repository_root):
            raise DetectorExperimentRunnerError(
                f"Verified source path escapes repository root: {source.path}"
            )

        verified_paths[key] = source_path

    return verified_paths


def _expected_run_identity(
    window: ExperimentWindow,
    model_provenance: ModelProvenance,
) -> dict[str, Any]:
    return {
        "schema_version": DETECTION_SCHEMA_VERSION,
        "detection_run_id": window.detection_run_id,
        "annotation_set_id": window.annotation_set_id,
        "possession_id": window.possession_id,
        "source_video": window.source_video.to_dict(),
        "window": {
            "start_frame_index": window.start_frame_index,
            "end_frame_index": window.end_frame_index,
        },
        "model_provenance": model_provenance.to_dict(),
    }


def _validate_existing_run(
    run: BallDetectionRun,
    window: ExperimentWindow,
    model_provenance: ModelProvenance,
    output_path: Path,
) -> None:
    actual = run.to_dict()
    expected = _expected_run_identity(window, model_provenance)
    mismatches = [
        field for field, value in expected.items() if actual[field] != value
    ]

    if mismatches:
        raise DetectorExperimentRunnerError(
            f"Existing output conflicts with manifest/provenance at "
            f"{output_path}; mismatched fields: {sorted(mismatches)}"
        )


def _prepare_windows(
    windows: tuple[ExperimentWindow, ...],
    repository_root: Path,
    model_provenance: ModelProvenance,
    verified_sources: dict[tuple[Any, ...], Path],
    dependencies: RunnerDependencies,
) -> tuple[PreparedWindow, ...]:
    prepared = []

    for window in windows:
        if tuple(window.output_path.parts[: len(OUTPUT_ROOT_PARTS)]) != (
            OUTPUT_ROOT_PARTS
        ):
            raise DetectorExperimentRunnerError(
                f"Output path is outside the ignored detector root: "
                f"{window.output_path}"
            )

        output_path = _reject_symlink_components(
            repository_root,
            window.output_path,
            label=f"Output path for {window.window_id}",
        )

        try:
            output_is_ignored = dependencies.is_git_ignored(
                repository_root,
                window.output_path,
            )
        except Exception as error:
            if isinstance(error, DetectorExperimentRunnerError):
                raise

            raise DetectorExperimentRunnerError(
                f"Could not verify Git ignore status for "
                f"{window.output_path}: {error}"
            ) from error

        if not output_is_ignored:
            raise DetectorExperimentRunnerError(
                f"Output path is not ignored by Git: {window.output_path}"
            )

        if output_path.exists():
            if output_path.is_symlink() or not output_path.is_file():
                raise DetectorExperimentRunnerError(
                    f"Existing output is not a safe regular file: {output_path}"
                )

            try:
                existing_run = dependencies.load_run(output_path)
            except Exception as error:
                raise DetectorExperimentRunnerError(
                    f"Existing output is invalid at {output_path}: {error}"
                ) from error

            _validate_existing_run(
                existing_run,
                window,
                model_provenance,
                output_path,
            )
        else:
            existing_run = None

        source = window.source_video
        source_key = (
            source.path.as_posix(),
            source.sha256,
            source.width_px,
            source.height_px,
            source.fps,
            source.frame_count,
        )
        prepared.append(
            PreparedWindow(
                window=window,
                source_path=verified_sources[source_key],
                output_path=output_path,
                existing_run=existing_run,
                output_claim=OutputClaim(expected_run=existing_run),
            )
        )

    return tuple(prepared)


def preflight_detector_experiment(
    experiment_path: Path,
    repository_root: Path,
    *,
    dependencies: RunnerDependencies | None = None,
) -> PreflightResult:
    """Perform every read-only safety and provenance check."""

    deps = dependencies if dependencies is not None else default_dependencies()
    supplied_root = Path(os.path.abspath(repository_root))
    root = supplied_root.resolve()

    if supplied_root != root:
        raise DetectorExperimentRunnerError(
            "--repository-root must not traverse a symlink"
        )

    if not root.is_dir():
        raise DetectorExperimentRunnerError(
            f"Repository root does not exist: {root}"
        )

    manifest_path, manifest_relative = _resolve_manifest_path(
        root,
        experiment_path,
    )

    try:
        snapshot = deps.inspect_git(root, manifest_relative)
    except Exception as error:
        if isinstance(error, DetectorExperimentRunnerError):
            raise

        raise DetectorExperimentRunnerError(
            f"Git preflight failed: {error}"
        ) from error

    head = _validate_git_snapshot(snapshot, root, manifest_relative)

    try:
        experiment = deps.load_experiment(manifest_path)
    except Exception as error:
        raise DetectorExperimentRunnerError(
            f"Could not load detector experiment {manifest_path}: {error}"
        ) from error

    ready_windows = experiment.windows_for_inference()

    if not ready_windows:
        raise DetectorExperimentRunnerError(
            "Experiment contains no windows ready for inference"
        )

    _validate_global_manifest_claims(
        repository_root=root,
        current_manifest_path=manifest_path,
        current_experiment=experiment,
        tracked_manifest_paths=snapshot.tracked_experiment_manifests,
        dependencies=deps,
    )
    weights_path = _validate_package_and_weights(experiment, deps)
    verified_sources = _validate_sources(ready_windows, root, deps)

    try:
        runtime_device = deps.inspect_runtime_device()
    except Exception as error:
        if isinstance(error, DetectorExperimentRunnerError):
            raise

        raise DetectorExperimentRunnerError(
            f"CUDA runtime preflight failed: {error}"
        ) from error

    try:
        provenance = deps.build_provenance(
            experiment.detector,
            code_commit=head,
            runtime_device=runtime_device,
        )
    except Exception as error:
        raise DetectorExperimentRunnerError(
            f"Could not build frozen model provenance: {error}"
        ) from error

    windows = _prepare_windows(
        ready_windows,
        root,
        provenance,
        verified_sources,
        deps,
    )

    try:
        closing_snapshot = deps.inspect_git(root, manifest_relative)
    except Exception as error:
        if isinstance(error, DetectorExperimentRunnerError):
            raise

        raise DetectorExperimentRunnerError(
            f"Closing Git preflight failed: {error}"
        ) from error

    _validate_git_snapshot(closing_snapshot, root, manifest_relative)

    if closing_snapshot != snapshot:
        raise DetectorExperimentRunnerError(
            "Git HEAD, worktree, or committed experiment registry changed "
            "during preflight"
        )

    return PreflightResult(
        repository_root=root,
        experiment_path=manifest_path,
        experiment=experiment,
        head=head,
        model_provenance=provenance,
        weights_path=weights_path,
        windows=windows,
    )


def _initial_run(
    window: ExperimentWindow,
    model_provenance: ModelProvenance,
) -> BallDetectionRun:
    payload = {
        **_expected_run_identity(window, model_provenance),
        "frames": [
            {
                "frame_index": frame_index,
                "inference_status": "not_run",
                "failure_reason": PENDING_REASON,
                "detections": None,
            }
            for frame_index in range(
                window.start_frame_index,
                window.end_frame_index + 1,
            )
        ],
    }
    return BallDetectionRun.from_mapping(payload)


def _replace_frame(
    run: BallDetectionRun,
    frame_index: int,
    *,
    inference_status: str,
    failure_reason: str | None,
    detections: tuple[BallDetection, ...] | None,
) -> BallDetectionRun:
    position = frame_index - run.window.start_frame_index

    if position < 0 or position >= len(run.frames):
        raise DetectorExperimentRunnerError(
            f"Frame {frame_index} is outside output window"
        )

    if run.frames[position].inference_status != "not_run":
        raise DetectorExperimentRunnerError(
            f"Runner may update only not_run frame {frame_index}"
        )

    payload = run.to_dict()
    payload["frames"][position] = {
        "frame_index": frame_index,
        "inference_status": inference_status,
        "failure_reason": failure_reason,
        "detections": (
            None
            if detections is None
            else [detection.to_dict() for detection in detections]
        ),
    }

    try:
        return BallDetectionRun.from_mapping(payload)
    except DetectionRunValidationError as error:
        raise DetectorExperimentRunnerError(
            f"Could not construct valid output for frame {frame_index}: {error}"
        ) from error


def _failure_reason(prefix: str, error: BaseException) -> str:
    detail = " ".join(str(error).split())

    if not detail:
        detail = error.__class__.__name__

    return f"{prefix}: {error.__class__.__name__}: {detail}"[:1000]


def _write_checked(
    run: BallDetectionRun,
    prepared: PreparedWindow,
    preflight: PreflightResult,
    dependencies: RunnerDependencies,
) -> None:
    checked_path = _reject_symlink_components(
        preflight.repository_root,
        prepared.window.output_path,
        label=f"Output path for {prepared.window.window_id}",
    )

    if checked_path != prepared.output_path:
        raise DetectorExperimentRunnerError(
            "Output path changed after preflight"
        )

    expected_run = prepared.output_claim.expected_run

    if expected_run is None:
        if checked_path.exists():
            raise DetectorExperimentRunnerError(
                "Detector output appeared after preflight; refusing to "
                f"overwrite concurrent state at {checked_path}"
            )
    else:
        if checked_path.is_symlink() or not checked_path.is_file():
            raise DetectorExperimentRunnerError(
                "Detector output disappeared or became unsafe after "
                f"preflight: {checked_path}"
            )

        try:
            current_run = dependencies.load_run(checked_path)
        except Exception as error:
            raise DetectorExperimentRunnerError(
                "Could not revalidate detector output before writing "
                f"{checked_path}: {error}"
            ) from error

        if current_run != expected_run:
            raise DetectorExperimentRunnerError(
                "Detector output changed after preflight or the runner's "
                f"prior write; refusing to regress {checked_path}"
            )

    try:
        dependencies.write_run(run, checked_path)
    except Exception as error:
        if isinstance(error, DetectorExperimentRunnerError):
            raise

        raise DetectorExperimentRunnerError(
            f"Could not atomically persist detector output "
            f"{checked_path}: {error}"
        ) from error

    try:
        persisted_run = dependencies.load_run(checked_path)
    except Exception as error:
        raise DetectorExperimentRunnerError(
            f"Could not verify persisted detector output {checked_path}: "
            f"{error}"
        ) from error

    if persisted_run != run:
        raise DetectorExperimentRunnerError(
            f"Persisted detector output does not match the attempted state: "
            f"{checked_path}"
        )

    prepared.output_claim.expected_run = run


def _mark_decode_failure(
    run: BallDetectionRun,
    frame_index: int,
    reason: str,
    prepared: PreparedWindow,
    preflight: PreflightResult,
    dependencies: RunnerDependencies,
) -> BallDetectionRun:
    updated = _replace_frame(
        run,
        frame_index,
        inference_status="decode_failed",
        failure_reason=reason,
        detections=None,
    )
    _write_checked(updated, prepared, preflight, dependencies)
    return updated


def _execute_window(
    prepared: PreparedWindow,
    preflight: PreflightResult,
    adapter: Any,
    dependencies: RunnerDependencies,
) -> BallDetectionRun:
    run = (
        prepared.existing_run
        if prepared.existing_run is not None
        else _initial_run(prepared.window, preflight.model_provenance)
    )
    remaining = {
        frame.frame_index
        for frame in run.frames
        if frame.inference_status == "not_run"
    }

    if not remaining:
        return run

    if prepared.existing_run is None:
        _write_checked(run, prepared, preflight, dependencies)

    capture = None

    try:
        try:
            capture = dependencies.open_capture(prepared.source_path)
        except Exception as error:
            failing_frame = min(remaining)
            return _mark_decode_failure(
                run,
                failing_frame,
                _failure_reason("could not open source video", error),
                prepared,
                preflight,
                dependencies,
            )

        try:
            opened = bool(capture.isOpened())
        except Exception as error:
            failing_frame = min(remaining)
            return _mark_decode_failure(
                run,
                failing_frame,
                _failure_reason("could not inspect source video", error),
                prepared,
                preflight,
                dependencies,
            )

        if not opened:
            failing_frame = min(remaining)
            return _mark_decode_failure(
                run,
                failing_frame,
                "could not open source video for sequential decode",
                prepared,
                preflight,
                dependencies,
            )

        maximum_pending_frame = max(remaining)

        for source_frame_index in range(maximum_pending_frame + 1):
            try:
                decoded, frame_bgr = capture.read()
            except Exception as error:
                candidate_frames = sorted(
                    frame
                    for frame in remaining
                    if frame >= source_frame_index
                )

                if not candidate_frames:
                    break

                return _mark_decode_failure(
                    run,
                    candidate_frames[0],
                    _failure_reason(
                        f"sequential decode failed at source frame "
                        f"{source_frame_index}",
                        error,
                    ),
                    prepared,
                    preflight,
                    dependencies,
                )

            if not decoded:
                candidate_frames = sorted(
                    frame
                    for frame in remaining
                    if frame >= source_frame_index
                )

                if not candidate_frames:
                    break

                return _mark_decode_failure(
                    run,
                    candidate_frames[0],
                    "sequential decode returned no frame at source frame "
                    f"{source_frame_index}",
                    prepared,
                    preflight,
                    dependencies,
                )

            if source_frame_index not in remaining:
                continue

            try:
                frame_rgb = dependencies.bgr_to_rgb(frame_bgr)
                detections = tuple(adapter.predict_frame(frame_rgb))
                updated = _replace_frame(
                    run,
                    source_frame_index,
                    inference_status="completed",
                    failure_reason=None,
                    detections=detections,
                )
            except Exception as error:
                updated = _replace_frame(
                    run,
                    source_frame_index,
                    inference_status="inference_failed",
                    failure_reason=_failure_reason(
                        "image-only detector inference failed",
                        error,
                    ),
                    detections=None,
                )

            _write_checked(updated, prepared, preflight, dependencies)
            run = updated
            remaining.remove(source_frame_index)

            if not remaining:
                break

        return run
    finally:
        if capture is not None:
            try:
                capture.release()
            except Exception:
                pass


def _summarize_runs(
    preflight: PreflightResult,
    runs: tuple[BallDetectionRun, ...],
    *,
    dry_run: bool,
) -> ExperimentRunSummary:
    completed = sum(
        frame.inference_status == "completed"
        for run in runs
        for frame in run.frames
    )
    total = sum(len(run.frames) for run in runs)
    return ExperimentRunSummary(
        dry_run=dry_run,
        head=preflight.head,
        window_count=len(preflight.windows),
        completed_frame_count=completed,
        incomplete_frame_count=total - completed,
        output_paths=tuple(item.output_path for item in preflight.windows),
    )


def run_detector_experiment(
    experiment_path: Path,
    repository_root: Path,
    *,
    dry_run: bool = False,
    dependencies: RunnerDependencies | None = None,
) -> ExperimentRunSummary:
    """Preflight and optionally execute every manifest-authorized window."""

    deps = dependencies if dependencies is not None else default_dependencies()
    preflight = preflight_detector_experiment(
        experiment_path,
        repository_root,
        dependencies=deps,
    )

    if dry_run:
        dry_runs = tuple(
            item.existing_run
            if item.existing_run is not None
            else _initial_run(item.window, preflight.model_provenance)
            for item in preflight.windows
        )
        return _summarize_runs(preflight, dry_runs, dry_run=True)

    has_pending = any(item.pending_frame_indices for item in preflight.windows)

    if has_pending:
        try:
            adapter = deps.create_adapter(
                preflight.weights_path,
                preflight.experiment.detector.export_confidence_floor,
            )
        except Exception as error:
            raise DetectorExperimentRunnerError(
                f"Could not construct the frozen detector adapter: {error}"
            ) from error
    else:
        adapter = None

    runs = []

    for prepared in preflight.windows:
        if prepared.pending_frame_indices:
            run = _execute_window(prepared, preflight, adapter, deps)
        else:
            if prepared.existing_run is None:
                raise DetectorExperimentRunnerError(
                    "Internal error: missing output has no pending frames"
                )

            run = prepared.existing_run

        runs.append(run)

    summary = _summarize_runs(
        preflight,
        tuple(runs),
        dry_run=False,
    )

    if summary.incomplete_frame_count:
        incomplete = [
            f"{run.detection_run_id}:{frame.frame_index}="
            f"{frame.inference_status}"
            for run in runs
            for frame in run.frames
            if frame.inference_status != "completed"
        ]
        preview = ", ".join(incomplete[:12])
        suffix = " ..." if len(incomplete) > 12 else ""
        raise DetectorExperimentIncompleteError(
            f"Detector experiment remains incomplete after persisted "
            f"attempts ({summary.incomplete_frame_count} frames): "
            f"{preview}{suffix}"
        )

    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a strict, precommitted, image-only RF-DETR experiment."
        ),
        allow_abbrev=False,
    )
    parser.add_argument(
        "--experiment",
        type=Path,
        required=True,
        help="Committed detector-experiment manifest.",
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        required=True,
        help="Exact Git repository root.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform the complete read-only preflight without inference.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        summary = run_detector_experiment(
            args.experiment,
            args.repository_root,
            dry_run=args.dry_run,
        )
    except (
        DetectorExperimentRunnerError,
        DetectorExperimentValidationError,
        DetectionRunValidationError,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    mode = "Dry-run preflight" if summary.dry_run else "Detector experiment"
    print(
        f"{mode} complete: windows={summary.window_count}, "
        f"completed_frames={summary.completed_frame_count}, "
        f"incomplete_frames={summary.incomplete_frame_count}, "
        f"head={summary.head}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
