"""Regress the CPU ReID/identity stages against existing reviewed outputs."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from .commands import build_stage_command
from .possession import PipelinePaths, load_manifest
from .run_player_coordinates import discover_repo_root


MATCH_PROVENANCE_FIELDS = {
    "classified_tracks",
    "segments_report",
    "segment_prototypes",
    "review_config",
}
IDENTITY_PROVENANCE_FIELDS = {
    "classified_tracks",
    "segments_report",
    "match_report",
    "identity_review_config",
    "sequential_identity_review_config",
}


class RegressionMismatch(RuntimeError):
    """Raised when regenerated identity output differs from the baseline."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate segmentation, segment matching, and identity outputs "
            "in a temporary directory and compare them with reviewed outputs."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Possession pipeline JSON configuration.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="Repository root; normally discovered automatically.",
    )
    return parser.parse_args(argv)


def replace_option(command: list[str], option: str, value: Path) -> None:
    try:
        index = command.index(option)
    except ValueError as error:
        raise ValueError(f"Command does not define {option}") from error

    command[index + 1] = str(value)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def normalized_report(path: Path, provenance_fields: set[str]) -> Any:
    report = load_json(path)

    if not isinstance(report, dict):
        return report

    return {
        key: value
        for key, value in report.items()
        if key not in provenance_fields
    }


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as input_file:
        return list(csv.DictReader(input_file))


def assert_equal(label: str, baseline: Any, candidate: Any) -> None:
    if baseline != candidate:
        raise RegressionMismatch(f"{label} differs from the reviewed baseline")


def assert_npz_equal(label: str, baseline_path: Path, candidate_path: Path) -> None:
    with (
        np.load(baseline_path, allow_pickle=False) as baseline,
        np.load(candidate_path, allow_pickle=False) as candidate,
    ):
        assert_equal(f"{label} array names", baseline.files, candidate.files)

        for name in baseline.files:
            if not np.array_equal(baseline[name], candidate[name]):
                raise RegressionMismatch(
                    f"{label} array {name!r} differs from the reviewed baseline"
                )


def require_files(paths: PipelinePaths, keys: tuple[str, ...]) -> None:
    missing = [paths[key] for key in keys if not paths[key].is_file()]

    if missing:
        formatted = "\n".join(f"  - {path}" for path in missing)
        raise FileNotFoundError(
            "Reviewed baseline inputs/outputs are missing:\n" + formatted
        )


def run_command(command: list[str], repo_root: Path) -> None:
    actual = [sys.executable, *command[1:]]
    subprocess.run(actual, cwd=repo_root, check=True)


def verify(config_path: Path, explicit_root: Path | None) -> None:
    repo_root = discover_repo_root(config_path, explicit_root)
    manifest = load_manifest(config_path)
    paths = PipelinePaths.build(
        repo_root,
        manifest,
        config_path=config_path,
    )
    baseline_keys = (
        "osnet_embeddings",
        "reid_review_config",
        "classified_tracks",
        "reid_segments",
        "reid_segment_prototypes",
        "segment_match_candidates",
        "identity_review_config",
        "sequential_identity_review_config",
        "segment_player_mapping",
        "identity_annotated_tracks",
        "reconciled_tracks",
    )
    require_files(paths, baseline_keys)

    with tempfile.TemporaryDirectory(
        prefix=f"{manifest.possession_id}_identity_regression_"
    ) as temp_dir:
        temporary = Path(temp_dir)
        segments = temporary / "segments.json"
        prototypes = temporary / "prototypes.npz"
        matches = temporary / "matches.json"
        mapping = temporary / "mapping.json"
        annotated = temporary / "annotated.csv"
        reconciled = temporary / "reconciled.csv"

        segmentation = build_stage_command(
            "reid_segmentation",
            manifest,
            paths,
        )
        matching = build_stage_command("segment_matching", manifest, paths)
        identity = build_stage_command(
            "identity_review_cycle",
            manifest,
            paths,
        )

        if segmentation is None or matching is None or identity is None:
            raise RuntimeError("Required identity commands are not planned")

        replace_option(segmentation, "--output-segments", segments)
        replace_option(segmentation, "--output-prototypes", prototypes)
        run_command(segmentation, repo_root)

        replace_option(matching, "--segments", segments)
        replace_option(matching, "--prototypes", prototypes)
        replace_option(matching, "--output", matches)
        run_command(matching, repo_root)

        replace_option(identity, "--segments", segments)
        replace_option(identity, "--matches", matches)
        replace_option(identity, "--output-mapping", mapping)
        replace_option(identity, "--output-annotated-tracks", annotated)
        replace_option(identity, "--output-reconciled-tracks", reconciled)
        run_command(identity, repo_root)

        assert_equal(
            "segment report",
            load_json(paths["reid_segments"]),
            load_json(segments),
        )
        assert_npz_equal(
            "segment prototypes",
            paths["reid_segment_prototypes"],
            prototypes,
        )
        assert_equal(
            "segment-match report",
            normalized_report(
                paths["segment_match_candidates"],
                MATCH_PROVENANCE_FIELDS,
            ),
            normalized_report(matches, MATCH_PROVENANCE_FIELDS),
        )
        assert_equal(
            "identity mapping",
            normalized_report(
                paths["segment_player_mapping"],
                IDENTITY_PROVENANCE_FIELDS,
            ),
            normalized_report(mapping, IDENTITY_PROVENANCE_FIELDS),
        )
        assert_equal(
            "identity-annotated tracks",
            csv_rows(paths["identity_annotated_tracks"]),
            csv_rows(annotated),
        )
        assert_equal(
            "reconciled tracks",
            csv_rows(paths["reconciled_tracks"]),
            csv_rows(reconciled),
        )

    report = load_json(paths["segment_player_mapping"])
    summary = report["summary"]
    print("\nExisting player-identity regression passed.")
    print(f"Possession: {manifest.possession_id}")
    print(f"Segments: {summary['total_segment_count']}")
    print(f"Active identities: {summary['active_identity_cluster_count']}")
    print(f"Reconciled rows: {summary['reconciled_row_count']}")
    print("Temporary regression outputs were removed.")


def main() -> None:
    args = parse_args()

    try:
        verify(args.config.resolve(), args.repo_root)
    except (
        FileNotFoundError,
        RegressionMismatch,
        subprocess.CalledProcessError,
        ValueError,
    ) as error:
        raise SystemExit(f"Player-identity regression failed: {error}") from error


if __name__ == "__main__":
    main()
