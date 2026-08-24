"""Prepare neutral, source-bound media for ball annotation review."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

import numpy as np

from .annotations import (
    AnnotationValidationError,
    BallAnnotationSet,
    load_annotations,
    verify_source_video,
)

try:
    import cv2
except ImportError:  # pragma: no cover - exercised by the explicit guard
    cv2 = None


REVIEW_ASSET_SCHEMA_VERSION = "0.1"
EXPECTED_WINDOW_FRAME_COUNT = 25
OVERVIEW_COLUMNS = 5
OVERVIEW_ROWS = 5
OVERVIEW_TILE_WIDTH_PX = 320
OVERVIEW_TILE_HEIGHT_PX = 180
OVERVIEW_HEADER_HEIGHT_PX = 96
MAX_PLAYBACK_FPS = 5.0
MP4_CODEC_CANDIDATES = ("mp4v", "avc1", "H264")
MANIFEST_FIELDS = {
    "schema_version",
    "asset_bundle_type",
    "annotation_set",
    "source_video",
    "window",
    "review_safeguards",
    "assets",
}
ANNOTATION_IDENTITY_FIELDS = {
    "annotation_set_id",
    "possession_id",
    "annotation_schema_version",
    "annotation_content_sha256",
}
SOURCE_MANIFEST_FIELDS = {
    "status",
    "path",
    "sha256",
    "width_px",
    "height_px",
    "fps",
    "frame_count",
}
WINDOW_MANIFEST_FIELDS = {
    "start_frame_index",
    "end_frame_index",
    "selection_purpose",
    "frame_count",
    "decode_method",
}
REVIEW_SAFEGUARD_FIELDS = {
    "native_source_frames_unmarked",
    "detector_outputs_included",
    "crops_included",
    "trajectory_hints_included",
    "annotation_json_modified",
}
ASSET_GROUP_FIELDS = {
    "source_frames",
    "context_overview",
    "slow_playback",
}
SOURCE_FRAME_ASSET_FIELDS = {
    "path",
    "sha256",
    "byte_size",
    "frame_index",
    "width_px",
    "height_px",
    "encoding",
}
OVERVIEW_ASSET_FIELDS = {
    "path",
    "sha256",
    "byte_size",
    "purpose",
    "pixel_annotation_allowed",
    "layout",
    "contains_full_frames_only",
    "contains_detector_hints",
}
PLAYBACK_ASSET_FIELDS = {
    "path",
    "sha256",
    "byte_size",
    "purpose",
    "codec_fourcc",
    "frame_count",
    "fps",
    "source_fps",
    "slowdown_factor",
    "contains_overlays",
    "contains_detector_hints",
}


class ReviewAssetPreparationError(RuntimeError):
    """Raised when a complete, trustworthy review bundle cannot be built."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare neutral 25-frame media for ball-center annotation review. "
            "The source is verified before any review assets are published."
        )
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        required=True,
        help="Strict ball annotation JSON defining the source and window.",
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        required=True,
        help="Repository root used to resolve the declared source-video path.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help=(
            "Bundle directory beneath data/outputs/ball_tracking/ that will "
            "receive the complete review assets."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing nonempty output directory after success.",
    )
    return parser.parse_args(argv)


def _require_cv2() -> None:
    if cv2 is None:
        raise ReviewAssetPreparationError(
            "OpenCV is required to prepare ball annotation review assets"
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _require_input_unchanged(
    path: Path,
    expected_sha256: str,
    label: str,
) -> None:
    try:
        actual_sha256 = _sha256_file(path)
    except OSError as error:
        raise ReviewAssetPreparationError(
            f"{label} changed or became unreadable during review-bundle "
            "preparation; refusing to publish"
        ) from error

    if actual_sha256 != expected_sha256:
        raise ReviewAssetPreparationError(
            f"{label} changed during review-bundle preparation; refusing "
            "to publish"
        )


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    temporary_path = path.with_name(
        f".{path.name}.{uuid.uuid4().hex}.tmp"
    )

    try:
        with temporary_path.open("xb") as output_file:
            output_file.write(content)
            output_file.flush()
            os.fsync(output_file.fileno())

        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, indent=2) + "\n"
    _atomic_write_bytes(path, serialized.encode("utf-8"))


def _is_nonempty_directory(path: Path) -> bool:
    return path.is_dir() and next(path.iterdir(), None) is not None


def _require_manifest_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReviewAssetPreparationError(
            f"Existing bundle {label} must be a JSON object"
        )

    return value


def _require_exact_manifest_fields(
    value: dict[str, Any],
    expected: set[str],
    label: str,
) -> None:
    actual = set(value)

    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ReviewAssetPreparationError(
            f"Existing bundle {label} fields are not recognized; "
            f"missing={missing}, extra={extra}"
        )


def _load_existing_manifest(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ReviewAssetPreparationError(
            "Existing nonempty output is not an owned ball annotation review "
            "bundle: manifest.json must be a regular file"
        )

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}

        for key, value in pairs:
            if key in result:
                raise ReviewAssetPreparationError(
                    f"Existing bundle manifest has duplicate key: {key!r}"
                )

            result[key] = value

        return result

    try:
        with path.open("r", encoding="utf-8") as input_file:
            payload = json.load(
                input_file,
                object_pairs_hook=reject_duplicate_keys,
            )
    except (
        json.JSONDecodeError,
        OSError,
        UnicodeDecodeError,
    ) as error:
        raise ReviewAssetPreparationError(
            "Existing nonempty output is not an owned ball annotation review "
            f"bundle: manifest.json is unreadable: {error}"
        ) from error

    return _require_manifest_mapping(payload, "manifest")


def _validate_recorded_asset(
    record: dict[str, Any],
    expected_fields: set[str],
    expected_path: str,
    output_dir: Path,
    label: str,
) -> None:
    _require_exact_manifest_fields(record, expected_fields, label)

    if record["path"] != expected_path:
        raise ReviewAssetPreparationError(
            f"Existing bundle {label} path does not match: {record['path']!r}"
        )

    asset_path = output_dir.joinpath(*Path(expected_path).parts)

    if asset_path.is_symlink() or not asset_path.is_file():
        raise ReviewAssetPreparationError(
            f"Existing bundle {label} is not a regular file: {asset_path}"
        )

    if (
        isinstance(record["byte_size"], bool)
        or not isinstance(record["byte_size"], int)
        or record["byte_size"] != asset_path.stat().st_size
    ):
        raise ReviewAssetPreparationError(
            f"Existing bundle {label} byte size does not match its manifest"
        )

    recorded_hash = record["sha256"]

    if (
        not isinstance(recorded_hash, str)
        or len(recorded_hash) != 64
        or any(character not in "0123456789abcdef" for character in recorded_hash)
        or _sha256_file(asset_path) != recorded_hash
    ):
        raise ReviewAssetPreparationError(
            f"Existing bundle {label} SHA-256 does not match its manifest"
        )


def _validate_existing_owned_bundle(
    output_dir: Path,
    annotation_set: BallAnnotationSet,
) -> None:
    manifest = _load_existing_manifest(output_dir / "manifest.json")
    _require_exact_manifest_fields(manifest, MANIFEST_FIELDS, "manifest")

    if (
        manifest["schema_version"] != REVIEW_ASSET_SCHEMA_VERSION
        or manifest["asset_bundle_type"] != "ball_annotation_review"
    ):
        raise ReviewAssetPreparationError(
            "Existing nonempty output is not an owned ball annotation review "
            "bundle with the supported schema"
        )

    annotation_identity = _require_manifest_mapping(
        manifest["annotation_set"],
        "annotation_set",
    )
    _require_exact_manifest_fields(
        annotation_identity,
        ANNOTATION_IDENTITY_FIELDS,
        "annotation_set",
    )
    expected_annotation_identity = {
        "annotation_set_id": annotation_set.annotation_set_id,
        "possession_id": annotation_set.possession_id,
        "annotation_schema_version": annotation_set.schema_version,
    }

    for field, expected in expected_annotation_identity.items():
        if annotation_identity[field] != expected:
            raise ReviewAssetPreparationError(
                "Existing bundle annotation identity does not match the "
                f"requested annotation set: field={field}"
            )

    annotation_hash = annotation_identity["annotation_content_sha256"]

    if (
        not isinstance(annotation_hash, str)
        or len(annotation_hash) != 64
        or any(character not in "0123456789abcdef" for character in annotation_hash)
    ):
        raise ReviewAssetPreparationError(
            "Existing bundle annotation content SHA-256 is invalid"
        )

    source = _require_manifest_mapping(manifest["source_video"], "source_video")
    _require_exact_manifest_fields(
        source,
        SOURCE_MANIFEST_FIELDS,
        "source_video",
    )
    expected_source = annotation_set.source_video
    exact_source_identity = {
        "status": "verified_source_video",
        "path": expected_source.path.as_posix(),
        "sha256": expected_source.sha256,
        "width_px": expected_source.width_px,
        "height_px": expected_source.height_px,
        "frame_count": expected_source.frame_count,
    }

    for field, expected in exact_source_identity.items():
        if source[field] != expected:
            raise ReviewAssetPreparationError(
                "Existing bundle source identity does not match the requested "
                f"annotation set: field={field}"
            )

    if (
        isinstance(source["fps"], bool)
        or not isinstance(source["fps"], (int, float))
        or not math.isclose(
            float(source["fps"]),
            expected_source.fps,
            rel_tol=0.0,
            abs_tol=1e-6,
        )
    ):
        raise ReviewAssetPreparationError(
            "Existing bundle source FPS does not match the requested "
            "annotation set"
        )

    window = _require_manifest_mapping(manifest["window"], "window")
    _require_exact_manifest_fields(window, WINDOW_MANIFEST_FIELDS, "window")
    expected_window = {
        **annotation_set.window.to_dict(),
        "frame_count": annotation_set.window.frame_count,
        "decode_method": "sequential_from_frame_zero_no_random_seek",
    }

    if window != expected_window:
        raise ReviewAssetPreparationError(
            "Existing bundle window identity does not match the requested "
            "annotation set"
        )

    safeguards = _require_manifest_mapping(
        manifest["review_safeguards"],
        "review_safeguards",
    )
    _require_exact_manifest_fields(
        safeguards,
        REVIEW_SAFEGUARD_FIELDS,
        "review_safeguards",
    )
    expected_safeguards = {
        "native_source_frames_unmarked": True,
        "detector_outputs_included": False,
        "crops_included": False,
        "trajectory_hints_included": False,
        "annotation_json_modified": False,
    }

    if safeguards != expected_safeguards:
        raise ReviewAssetPreparationError(
            "Existing bundle review safeguards are not recognized"
        )

    assets = _require_manifest_mapping(manifest["assets"], "assets")
    _require_exact_manifest_fields(assets, ASSET_GROUP_FIELDS, "assets")
    frame_records = assets["source_frames"]

    if not isinstance(frame_records, list):
        raise ReviewAssetPreparationError(
            "Existing bundle assets.source_frames must be a JSON array"
        )

    frame_indices = list(
        range(
            annotation_set.window.start_frame_index,
            annotation_set.window.end_frame_index + 1,
        )
    )

    if len(frame_records) != len(frame_indices):
        raise ReviewAssetPreparationError(
            "Existing bundle source-frame count does not match the window"
        )

    expected_entries = {
        "manifest.json",
        "source_frames",
        "context_only_overview.png",
        "slow_playback.mp4",
    }

    for record_index, frame_index in enumerate(frame_indices):
        record = _require_manifest_mapping(
            frame_records[record_index],
            f"assets.source_frames[{record_index}]",
        )
        expected_path = f"source_frames/frame_{frame_index:06d}.png"
        expected_entries.add(expected_path)
        _validate_recorded_asset(
            record,
            SOURCE_FRAME_ASSET_FIELDS,
            expected_path,
            output_dir,
            f"assets.source_frames[{record_index}]",
        )
        expected_frame_identity = {
            "frame_index": frame_index,
            "width_px": expected_source.width_px,
            "height_px": expected_source.height_px,
            "encoding": "lossless_png",
        }

        for field, expected in expected_frame_identity.items():
            if record[field] != expected:
                raise ReviewAssetPreparationError(
                    "Existing bundle source-frame identity does not match: "
                    f"record={record_index}, field={field}"
                )

    overview = _require_manifest_mapping(
        assets["context_overview"],
        "assets.context_overview",
    )
    _validate_recorded_asset(
        overview,
        OVERVIEW_ASSET_FIELDS,
        "context_only_overview.png",
        output_dir,
        "assets.context_overview",
    )
    expected_overview = {
        "purpose": "context_only",
        "pixel_annotation_allowed": False,
        "layout": "5x5",
        "contains_full_frames_only": True,
        "contains_detector_hints": False,
    }

    for field, expected in expected_overview.items():
        if overview[field] != expected:
            raise ReviewAssetPreparationError(
                f"Existing bundle context-overview field is invalid: {field}"
            )

    playback = _require_manifest_mapping(
        assets["slow_playback"],
        "assets.slow_playback",
    )
    _validate_recorded_asset(
        playback,
        PLAYBACK_ASSET_FIELDS,
        "slow_playback.mp4",
        output_dir,
        "assets.slow_playback",
    )
    playback_fps = min(MAX_PLAYBACK_FPS, expected_source.fps)
    expected_playback = {
        "purpose": "clean_slow_playback",
        "frame_count": annotation_set.window.frame_count,
        "fps": playback_fps,
        "source_fps": expected_source.fps,
        "slowdown_factor": expected_source.fps / playback_fps,
        "contains_overlays": False,
        "contains_detector_hints": False,
    }

    for field, expected in expected_playback.items():
        if playback[field] != expected:
            raise ReviewAssetPreparationError(
                f"Existing bundle slow-playback field is invalid: {field}"
            )

    if playback["codec_fourcc"] not in MP4_CODEC_CANDIDATES:
        raise ReviewAssetPreparationError(
            "Existing bundle slow-playback codec is not recognized"
        )

    try:
        actual_entries = {
            path.relative_to(output_dir).as_posix()
            for path in output_dir.rglob("*")
        }
    except OSError as error:
        raise ReviewAssetPreparationError(
            f"Could not inspect existing bundle structure: {error}"
        ) from error

    if actual_entries != expected_entries:
        missing = sorted(expected_entries - actual_entries)
        extra = sorted(actual_entries - expected_entries)
        raise ReviewAssetPreparationError(
            "Existing bundle structure contains missing or unrecognized "
            f"artifacts; missing={missing}, extra={extra}"
        )


def _validate_output_target(
    output_dir: Path,
    repository_root: Path,
    annotation_path: Path,
    source_path: Path,
    annotation_set: BallAnnotationSet,
    overwrite: bool,
) -> None:
    allowed_output_root = (
        repository_root / "data" / "outputs" / "ball_tracking"
    ).resolve()

    try:
        relative_output = output_dir.relative_to(allowed_output_root)
    except ValueError as error:
        raise ReviewAssetPreparationError(
            "Output directory must be a strict descendant of "
            f"{allowed_output_root}: {output_dir}"
        ) from error

    if relative_output == Path("."):
        raise ReviewAssetPreparationError(
            "Output directory must be a strict descendant of "
            f"{allowed_output_root}; the ball_tracking output root itself "
            "is not a bundle target"
        )

    if output_dir.parent == output_dir:
        raise ReviewAssetPreparationError(
            "The filesystem root cannot be used as the output directory"
        )

    if output_dir.exists() and not output_dir.is_dir():
        raise ReviewAssetPreparationError(
            f"Output path exists but is not a directory: {output_dir}"
        )

    if _is_nonempty_directory(output_dir) and not overwrite:
        raise ReviewAssetPreparationError(
            "Output directory is nonempty; pass --overwrite to replace it: "
            f"{output_dir}"
        )

    if _is_nonempty_directory(output_dir) and overwrite:
        _validate_existing_owned_bundle(output_dir, annotation_set)

    protected_paths = {
        "repository root": repository_root,
        "annotation JSON": annotation_path,
        "source video": source_path,
    }

    for label, protected_path in protected_paths.items():
        try:
            protected_path.relative_to(output_dir)
        except ValueError:
            continue

        raise ReviewAssetPreparationError(
            f"Output directory cannot contain the protected {label}: "
            f"{output_dir}"
        )


def _decode_window_sequentially(
    source_path: Path,
    annotation_set: BallAnnotationSet,
) -> list[Any]:
    """Decode from frame zero through the window without random seeking."""

    capture = cv2.VideoCapture(str(source_path))

    if not capture.isOpened():
        raise ReviewAssetPreparationError(
            f"Could not open verified source video: {source_path}"
        )

    start = annotation_set.window.start_frame_index
    end = annotation_set.window.end_frame_index
    frames = []

    try:
        for frame_index in range(end + 1):
            success, frame = capture.read()

            if not success or frame is None:
                raise ReviewAssetPreparationError(
                    "Sequential source decode failed at frame "
                    f"{frame_index}; required window is {start}-{end}"
                )

            height_px, width_px = frame.shape[:2]

            if (
                width_px != annotation_set.source_video.width_px
                or height_px != annotation_set.source_video.height_px
            ):
                raise ReviewAssetPreparationError(
                    "Decoded frame dimensions changed at frame "
                    f"{frame_index}: expected "
                    f"{annotation_set.source_video.width_px}x"
                    f"{annotation_set.source_video.height_px}, received "
                    f"{width_px}x{height_px}"
                )

            if frame_index >= start:
                frames.append(frame)
    finally:
        capture.release()

    if len(frames) != annotation_set.window.frame_count:
        raise ReviewAssetPreparationError(
            "Sequential decode produced an incomplete annotation window: "
            f"expected {annotation_set.window.frame_count}, "
            f"received {len(frames)}"
        )

    return frames


def _write_lossless_png(path: Path, frame: Any) -> None:
    success, encoded = cv2.imencode(
        ".png",
        frame,
        [cv2.IMWRITE_PNG_COMPRESSION, 3],
    )

    if not success:
        raise ReviewAssetPreparationError(
            f"Could not encode lossless PNG: {path}"
        )

    _atomic_write_bytes(path, encoded.tobytes())
    decoded = cv2.imread(str(path), cv2.IMREAD_COLOR)

    if decoded is None or decoded.shape != frame.shape:
        raise ReviewAssetPreparationError(
            f"Lossless PNG verification failed: {path}"
        )

    if not (decoded == frame).all():
        raise ReviewAssetPreparationError(
            f"Lossless PNG pixel verification failed: {path}"
        )


def _build_context_overview(frames: list[Any], frame_indices: list[int]) -> Any:
    if len(frames) != EXPECTED_WINDOW_FRAME_COUNT:
        raise ReviewAssetPreparationError(
            "The context overview requires exactly 25 frames"
        )

    sheet_width = OVERVIEW_COLUMNS * OVERVIEW_TILE_WIDTH_PX
    sheet_height = (
        OVERVIEW_HEADER_HEIGHT_PX
        + OVERVIEW_ROWS * OVERVIEW_TILE_HEIGHT_PX
    )
    sheet = np.full((sheet_height, sheet_width, 3), 18, dtype=np.uint8)
    heading = "CONTEXT ONLY - NOT FOR PIXEL ANNOTATION"
    subheading = "Downscaled full frames; use source_frames PNGs for labels"
    cv2.putText(
        sheet,
        heading,
        (32, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        sheet,
        subheading,
        (32, 76),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (205, 205, 205),
        1,
        cv2.LINE_AA,
    )

    for index, (frame, frame_index) in enumerate(
        zip(frames, frame_indices, strict=True)
    ):
        row, column = divmod(index, OVERVIEW_COLUMNS)
        x_start = column * OVERVIEW_TILE_WIDTH_PX
        y_start = (
            OVERVIEW_HEADER_HEIGHT_PX + row * OVERVIEW_TILE_HEIGHT_PX
        )
        tile = cv2.resize(
            frame,
            (OVERVIEW_TILE_WIDTH_PX, OVERVIEW_TILE_HEIGHT_PX),
            interpolation=cv2.INTER_AREA,
        )
        cv2.rectangle(tile, (0, 0), (156, 30), (0, 0, 0), -1)
        cv2.putText(
            tile,
            f"FRAME {frame_index}",
            (8, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        sheet[
            y_start : y_start + OVERVIEW_TILE_HEIGHT_PX,
            x_start : x_start + OVERVIEW_TILE_WIDTH_PX,
        ] = tile
        cv2.rectangle(
            sheet,
            (x_start, y_start),
            (
                x_start + OVERVIEW_TILE_WIDTH_PX - 1,
                y_start + OVERVIEW_TILE_HEIGHT_PX - 1,
            ),
            (230, 230, 230),
            1,
        )

    return sheet


def _verify_playback(
    path: Path,
    expected_frame_count: int,
    expected_width_px: int,
    expected_height_px: int,
    expected_fps: float,
) -> None:
    capture = cv2.VideoCapture(str(path))

    if not capture.isOpened():
        raise ReviewAssetPreparationError(
            f"Could not reopen generated playback: {path}"
        )

    actual_fps = float(capture.get(cv2.CAP_PROP_FPS))
    decoded_count = 0

    try:
        while True:
            success, frame = capture.read()

            if not success:
                break

            if frame is None:
                raise ReviewAssetPreparationError(
                    f"Generated playback returned an empty frame: {path}"
                )

            height_px, width_px = frame.shape[:2]

            if (
                width_px != expected_width_px
                or height_px != expected_height_px
            ):
                raise ReviewAssetPreparationError(
                    "Generated playback dimensions do not match the source: "
                    f"{width_px}x{height_px}"
                )

            decoded_count += 1
    finally:
        capture.release()

    if decoded_count != expected_frame_count:
        raise ReviewAssetPreparationError(
            "Generated playback frame count is incomplete: expected "
            f"{expected_frame_count}, received {decoded_count}"
        )

    if not math.isclose(
        actual_fps,
        expected_fps,
        rel_tol=0.0,
        abs_tol=0.05,
    ):
        raise ReviewAssetPreparationError(
            "Generated playback FPS does not match the requested slow rate: "
            f"expected {expected_fps}, received {actual_fps}"
        )


def _write_slow_playback(
    path: Path,
    frames: list[Any],
    width_px: int,
    height_px: int,
    playback_fps: float,
) -> str:
    codec_errors = []

    for codec in MP4_CODEC_CANDIDATES:
        partial_path = path.with_name(f".{path.stem}.{codec}.part.mp4")
        writer = cv2.VideoWriter(
            str(partial_path),
            cv2.VideoWriter_fourcc(*codec),
            playback_fps,
            (width_px, height_px),
        )

        if not writer.isOpened():
            writer.release()
            codec_errors.append(f"{codec}: writer did not open")

            if partial_path.exists():
                partial_path.unlink()

            continue

        try:
            for frame in frames:
                writer.write(frame)
        finally:
            writer.release()

        try:
            if not partial_path.is_file() or partial_path.stat().st_size == 0:
                raise ReviewAssetPreparationError("writer produced no bytes")

            _verify_playback(
                partial_path,
                len(frames),
                width_px,
                height_px,
                playback_fps,
            )
            partial_path.replace(path)
            return codec
        except (OSError, ReviewAssetPreparationError) as error:
            codec_errors.append(f"{codec}: {error}")

            if partial_path.exists():
                partial_path.unlink()

    raise ReviewAssetPreparationError(
        "No tested MP4 codec produced a complete slow playback; "
        + "; ".join(codec_errors)
    )


def _asset_record(path: Path, bundle_root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(bundle_root).as_posix(),
        "sha256": _sha256_file(path),
        "byte_size": path.stat().st_size,
    }


def _commit_staging_directory(
    staging_dir: Path,
    output_dir: Path,
    overwrite: bool,
) -> None:
    if output_dir.exists() and not output_dir.is_dir():
        raise ReviewAssetPreparationError(
            f"Output path became a non-directory: {output_dir}"
        )

    if _is_nonempty_directory(output_dir) and not overwrite:
        raise ReviewAssetPreparationError(
            f"Output directory became nonempty during generation: {output_dir}"
        )

    if not output_dir.exists():
        staging_dir.replace(output_dir)
        return

    backup_dir = output_dir.with_name(
        f".{output_dir.name}.backup-{uuid.uuid4().hex}"
    )
    output_dir.replace(backup_dir)

    try:
        staging_dir.replace(output_dir)
    except OSError:
        backup_dir.replace(output_dir)
        raise

    shutil.rmtree(backup_dir)


def _build_bundle(
    staging_dir: Path,
    annotation_set: BallAnnotationSet,
    annotation_content_sha256: str,
    source_verification: dict[str, Any],
    frames: list[Any],
) -> dict[str, Any]:
    source_frames_dir = staging_dir / "source_frames"
    source_frames_dir.mkdir()
    frame_indices = list(
        range(
            annotation_set.window.start_frame_index,
            annotation_set.window.end_frame_index + 1,
        )
    )
    frame_assets = []

    for frame_index, frame in zip(frame_indices, frames, strict=True):
        frame_path = source_frames_dir / f"frame_{frame_index:06d}.png"
        _write_lossless_png(frame_path, frame)
        record = _asset_record(frame_path, staging_dir)
        record.update(
            {
                "frame_index": frame_index,
                "width_px": annotation_set.source_video.width_px,
                "height_px": annotation_set.source_video.height_px,
                "encoding": "lossless_png",
            }
        )
        frame_assets.append(record)

    overview_path = staging_dir / "context_only_overview.png"
    overview = _build_context_overview(frames, frame_indices)
    _write_lossless_png(overview_path, overview)
    playback_fps = min(MAX_PLAYBACK_FPS, annotation_set.source_video.fps)
    playback_path = staging_dir / "slow_playback.mp4"
    playback_codec = _write_slow_playback(
        playback_path,
        frames,
        annotation_set.source_video.width_px,
        annotation_set.source_video.height_px,
        playback_fps,
    )
    overview_record = _asset_record(overview_path, staging_dir)
    overview_record.update(
        {
            "purpose": "context_only",
            "pixel_annotation_allowed": False,
            "layout": "5x5",
            "contains_full_frames_only": True,
            "contains_detector_hints": False,
        }
    )
    playback_record = _asset_record(playback_path, staging_dir)
    playback_record.update(
        {
            "purpose": "clean_slow_playback",
            "codec_fourcc": playback_codec,
            "frame_count": len(frames),
            "fps": playback_fps,
            "source_fps": annotation_set.source_video.fps,
            "slowdown_factor": (
                annotation_set.source_video.fps / playback_fps
            ),
            "contains_overlays": False,
            "contains_detector_hints": False,
        }
    )
    manifest = {
        "schema_version": REVIEW_ASSET_SCHEMA_VERSION,
        "asset_bundle_type": "ball_annotation_review",
        "annotation_set": {
            "annotation_set_id": annotation_set.annotation_set_id,
            "possession_id": annotation_set.possession_id,
            "annotation_schema_version": annotation_set.schema_version,
            "annotation_content_sha256": annotation_content_sha256,
        },
        "source_video": source_verification,
        "window": {
            **annotation_set.window.to_dict(),
            "frame_count": annotation_set.window.frame_count,
            "decode_method": "sequential_from_frame_zero_no_random_seek",
        },
        "review_safeguards": {
            "native_source_frames_unmarked": True,
            "detector_outputs_included": False,
            "crops_included": False,
            "trajectory_hints_included": False,
            "annotation_json_modified": False,
        },
        "assets": {
            "source_frames": frame_assets,
            "context_overview": overview_record,
            "slow_playback": playback_record,
        },
    }
    _atomic_write_json(staging_dir / "manifest.json", manifest)
    return manifest


def prepare_annotation_review(
    annotation_path: Path,
    repository_root: Path,
    output_dir: Path,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Build and publish one complete neutral annotation-review bundle."""

    _require_cv2()
    annotation_path = annotation_path.resolve()
    repository_root = repository_root.resolve()
    output_dir = output_dir.resolve()
    annotation_content_sha256 = _sha256_file(annotation_path)
    annotation_set = load_annotations(annotation_path)
    _require_input_unchanged(
        annotation_path,
        annotation_content_sha256,
        "Annotation JSON",
    )

    if annotation_set.window.frame_count != EXPECTED_WINDOW_FRAME_COUNT:
        raise ReviewAssetPreparationError(
            "Ball annotation review windows must contain exactly 25 frames; "
            f"received {annotation_set.window.frame_count}"
        )

    source_path = repository_root.joinpath(
        *annotation_set.source_video.path.parts
    ).resolve()
    _validate_output_target(
        output_dir,
        repository_root,
        annotation_path,
        source_path,
        annotation_set,
        overwrite,
    )
    source_verification = verify_source_video(
        annotation_set,
        repository_root,
    )
    source_content_sha256 = source_verification["sha256"]
    _require_input_unchanged(
        source_path,
        source_content_sha256,
        "Source video",
    )
    frames = _decode_window_sequentially(source_path, annotation_set)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(
        tempfile.mkdtemp(
            prefix=f".{output_dir.name}.staging-",
            dir=output_dir.parent,
        )
    )

    try:
        manifest = _build_bundle(
            staging_dir,
            annotation_set,
            annotation_content_sha256,
            source_verification,
            frames,
        )
        _validate_output_target(
            output_dir,
            repository_root,
            annotation_path,
            source_path,
            annotation_set,
            overwrite,
        )
        _require_input_unchanged(
            annotation_path,
            annotation_content_sha256,
            "Annotation JSON",
        )
        _require_input_unchanged(
            source_path,
            source_content_sha256,
            "Source video",
        )
        _commit_staging_directory(staging_dir, output_dir, overwrite)
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)

    return manifest


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    try:
        manifest = prepare_annotation_review(
            args.annotations,
            args.repository_root,
            args.output_dir,
            overwrite=args.overwrite,
        )
    except (
        AnnotationValidationError,
        FileNotFoundError,
        OSError,
        ReviewAssetPreparationError,
    ) as error:
        raise SystemExit(
            f"Ball annotation review preparation error: {error}"
        ) from error

    print("Ball annotation review assets prepared.")
    print(
        "Annotation set: "
        f"{manifest['annotation_set']['annotation_set_id']}"
    )
    print(
        "Window: "
        f"{manifest['window']['start_frame_index']}-"
        f"{manifest['window']['end_frame_index']}"
    )
    print(f"Output directory: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
