"""Initialize prediction-blind annotation drafts from a detector precommit.

Only representative and challenge windows are eligible.  Predictions for every
embargoed window must still be absent before any draft is published.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from .annotations import BallAnnotationSet, verify_source_video
from .detector_experiments import (
    PREDICTION_EMBARGO,
    DetectorExperiment,
    ExperimentWindow,
    load_detector_experiment,
)


DEVELOPMENT_PURPOSES = {
    "representative_evaluation",
    "challenge_evaluation",
}
EXPECTED_DRAFT_COUNT = 6


class AnnotationWindowInitializationError(RuntimeError):
    """Raised when prediction-blind drafts cannot be initialized safely."""


@dataclass(frozen=True)
class InitializationSummary:
    created: tuple[Path, ...]
    reused: tuple[Path, ...]


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


def build_draft_payload(
    window: ExperimentWindow,
    *,
    annotator_id: str,
    created_at_utc: str,
) -> dict[str, Any]:
    """Build and schema-validate one all-unlabeled draft."""

    if window.selection_purpose not in DEVELOPMENT_PURPOSES:
        raise AnnotationWindowInitializationError(
            "only representative and challenge windows may be initialized"
        )
    if window.execution_status != PREDICTION_EMBARGO:
        raise AnnotationWindowInitializationError(
            "development annotation windows must remain prediction embargoed"
        )

    payload = {
        "schema_version": "0.1",
        "annotation_set_id": window.annotation_set_id,
        "possession_id": window.possession_id,
        "source_video": window.source_video.to_dict(),
        "window": {
            "start_frame_index": window.start_frame_index,
            "end_frame_index": window.end_frame_index,
            "selection_purpose": window.selection_purpose,
        },
        "coordinate_system": {
            "frame_index_origin": 0,
            "pixel_origin": "top_left",
            "x_axis_direction": "right",
            "y_axis_direction": "down",
            "center_definition": "complete_ball_center",
            "timestamp_rule": "frame_index_divided_by_fps",
        },
        "review": {
            "status": "draft",
            "annotator_id": annotator_id,
            "reviewer_id": None,
            "created_at_utc": created_at_utc,
            "reviewed_at_utc": None,
        },
        "annotations": _blank_rows(
            window.start_frame_index,
            window.end_frame_index,
        ),
    }
    return BallAnnotationSet.from_mapping(payload).to_dict()


def development_windows(
    experiment: DetectorExperiment,
) -> tuple[ExperimentWindow, ...]:
    windows = tuple(
        item
        for item in experiment.windows
        if item.selection_purpose in DEVELOPMENT_PURPOSES
    )
    if len(windows) != EXPECTED_DRAFT_COUNT:
        raise AnnotationWindowInitializationError(
            f"expected {EXPECTED_DRAFT_COUNT} development windows, "
            f"received {len(windows)}"
        )
    if any(item.execution_status != PREDICTION_EMBARGO for item in windows):
        raise AnnotationWindowInitializationError(
            "every development window must remain prediction embargoed"
        )
    return windows


def _serialized(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2) + "\n").encode("utf-8")


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output_file:
            output_file.write(content)
            output_file.flush()
            os.fsync(output_file.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def initialize_detector_annotation_windows(
    experiment_path: Path,
    repository_root: Path,
    *,
    annotator_id: str,
    created_at_utc: str,
) -> InitializationSummary:
    root = repository_root.resolve()
    experiment = load_detector_experiment(experiment_path)
    windows = development_windows(experiment)

    # Check every embargoed path, including all three holdouts, before writing.
    for item in experiment.windows:
        if item.execution_status != PREDICTION_EMBARGO:
            continue
        prediction_path = root.joinpath(*item.output_path.parts)
        if prediction_path.exists():
            raise AnnotationWindowInitializationError(
                "prediction embargo was already breached; refusing to initialize "
                f"annotations: {item.output_path.as_posix()}"
            )

    prepared: list[tuple[Path, bytes]] = []
    for item in windows:
        payload = build_draft_payload(
            item,
            annotator_id=annotator_id,
            created_at_utc=created_at_utc,
        )
        annotation_set = BallAnnotationSet.from_mapping(payload)
        verify_source_video(annotation_set, root)
        output_path = (
            root
            / "configs"
            / "ball_tracking"
            / "annotations"
            / f"{item.annotation_set_id}.json"
        )
        prepared.append((output_path, _serialized(payload)))

    created: list[Path] = []
    reused: list[Path] = []
    for output_path, content in prepared:
        if output_path.exists():
            if output_path.read_bytes() != content:
                raise AnnotationWindowInitializationError(
                    "existing annotation draft conflicts and will not be "
                    f"overwritten: {output_path}"
                )
            reused.append(output_path)
            continue
        _atomic_write(output_path, content)
        created.append(output_path)

    return InitializationSummary(tuple(created), tuple(reused))


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Initialize the six prediction-blind representative/challenge "
            "annotation drafts from a frozen detector experiment."
        )
    )
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--annotator-id", required=True)
    parser.add_argument("--created-at-utc", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    try:
        summary = initialize_detector_annotation_windows(
            args.experiment,
            args.repository_root,
            annotator_id=args.annotator_id,
            created_at_utc=args.created_at_utc,
        )
    except (OSError, ValueError, AnnotationWindowInitializationError) as error:
        raise SystemExit(f"Ball annotation initialization error: {error}") from error

    print(
        "Prediction-blind annotation drafts ready: "
        f"created={len(summary.created)}, reused={len(summary.reused)}"
    )
    for path in (*summary.created, *summary.reused):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
