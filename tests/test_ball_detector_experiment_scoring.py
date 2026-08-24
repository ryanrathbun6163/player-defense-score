"""Focused tests for durable, embargo-safe detector pilot scoring."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path, PurePosixPath

from src.ball_tracking.annotations import load_annotations
from src.ball_tracking.detections import (
    SCHEMA_VERSION as DETECTION_SCHEMA_VERSION,
    load_detection_run,
)
from src.ball_tracking.detector_experiments import (
    build_model_provenance,
    load_detector_experiment,
)
from src.ball_tracking.evaluation import (
    aggregate_evaluation_reports,
    evaluate_detections,
)
from src.ball_tracking.run_detector_experiment import GitSnapshot
from src.ball_tracking.score_detector_experiment import (
    INTERPRETATION_CONSTRAINTS,
    REPORT_FILENAME,
    SCHEMA_VERSION,
    TOP_LEVEL_FIELDS,
    DetectorExperimentScoringError,
    ScoringDependencies,
    atomic_write_new_scoring_report,
    build_argument_parser,
    load_scoring_report,
    score_detector_experiment,
    validate_scoring_report,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REAL_MANIFEST = (
    REPOSITORY_ROOT
    / "configs"
    / "ball_tracking"
    / "experiments"
    / "rfdetr_medium_image_only_baseline_v0_1.json"
)
REAL_ANNOTATION_ROOT = (
    REPOSITORY_ROOT / "configs" / "ball_tracking" / "annotations"
)
MANIFEST_RELATIVE = PurePosixPath(
    "configs/ball_tracking/experiments/"
    "rfdetr_medium_image_only_baseline_v0_1.json"
)
SCORER_HEAD = "b" * 40
DETECTOR_HEAD = "a" * 40


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def synthetic_detection_payload(experiment, window, annotations) -> dict:
    provenance = build_model_provenance(
        experiment.detector,
        code_commit=DETECTOR_HEAD,
        runtime_device="cuda:0 | synthetic scoring fixture",
    )
    frames = []

    for annotation in annotations.annotations:
        detections = []

        if annotation.localization_eligible:
            center_x, center_y = annotation.geometry.center_xy_px
            detections.append(
                {
                    "candidate_index": 0,
                    "class_id": 37,
                    "class_name": "sports ball",
                    "confidence": 0.4,
                    "bbox_xyxy_px": [
                        center_x - 5.0,
                        center_y - 5.0,
                        center_x + 5.0,
                        center_y + 5.0,
                    ],
                    "center_xy_px": [center_x, center_y],
                }
            )

        frames.append(
            {
                "frame_index": annotation.frame_index,
                "inference_status": "completed",
                "failure_reason": None,
                "detections": detections,
            }
        )

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
        "model_provenance": provenance.to_dict(),
        "frames": frames,
    }


class SyntheticScoringContext:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.manifest_path = self.root.joinpath(*MANIFEST_RELATIVE.parts)
        self.manifest_path.parent.mkdir(parents=True)
        self.manifest_path.write_bytes(REAL_MANIFEST.read_bytes())
        self.experiment = load_detector_experiment(self.manifest_path)
        self.tracked_calls: list[PurePosixPath] = []
        self.source_calls = []
        self.annotation_load_calls: list[Path] = []
        self.detection_load_calls: list[Path] = []
        self.evaluation_calls: list[tuple[str, float, float]] = []
        self.write_calls: list[Path] = []
        self.ancestry_calls: list[tuple[str, str, PurePosixPath]] = []
        self.snapshots = [self.snapshot(), self.snapshot()]

        for window in self.experiment.windows_for_inference():
            source_annotation_path = (
                REAL_ANNOTATION_ROOT / f"{window.annotation_set_id}.json"
            )
            destination_annotation_path = (
                self.root
                / "configs"
                / "ball_tracking"
                / "annotations"
                / source_annotation_path.name
            )
            destination_annotation_path.parent.mkdir(parents=True, exist_ok=True)
            destination_annotation_path.write_bytes(
                source_annotation_path.read_bytes()
            )
            annotations = load_annotations(destination_annotation_path)
            detection_path = self.root.joinpath(*window.output_path.parts)
            write_json(
                detection_path,
                synthetic_detection_payload(
                    self.experiment,
                    window,
                    annotations,
                ),
            )

    def snapshot(self, *, head: str = SCORER_HEAD, clean: bool = True):
        return GitSnapshot(
            repository_root=self.root,
            head=head,
            clean=clean,
            manifest_tracked=True,
            manifest_matches_head=True,
            tracked_experiment_manifests=(MANIFEST_RELATIVE,),
            all_experiment_manifests_match_head=True,
        )

    @property
    def output_path(self) -> Path:
        return (
            self.root
            / "data"
            / "outputs"
            / "ball_tracking"
            / "evaluations"
            / self.experiment.experiment_id
            / REPORT_FILENAME
        )

    def inspect_git(self, root, manifest_relative):
        self.assert_root(root)
        if manifest_relative != MANIFEST_RELATIVE:
            raise AssertionError(manifest_relative)
        if not self.snapshots:
            return self.snapshot()
        return self.snapshots.pop(0)

    def assert_root(self, root):
        if root != self.root:
            raise AssertionError((root, self.root))

    def verify_tracked(self, root, relative):
        self.assert_root(root)
        self.tracked_calls.append(relative)

    def verify_source(self, source, root):
        self.assert_root(root)
        self.source_calls.append(source.sha256)
        return source.to_dict()

    def load_annotation(self, path):
        self.annotation_load_calls.append(path)
        return load_annotations(path)

    def load_detection(self, path):
        self.detection_load_calls.append(path)
        return load_detection_run(path)

    def evaluate(self, annotations, detections, **settings):
        self.evaluation_calls.append(
            (
                annotations.annotation_set_id,
                settings["confidence_threshold"],
                settings["localization_radius_px"],
            )
        )
        return evaluate_detections(annotations, detections, **settings)

    def write_report(self, report, path):
        self.write_calls.append(path)
        atomic_write_new_scoring_report(report, path)

    def verify_ancestor(self, root, ancestor, descendant, manifest_relative):
        self.assert_root(root)
        self.ancestry_calls.append(
            (ancestor, descendant, manifest_relative)
        )

    def dependencies(self) -> ScoringDependencies:
        return ScoringDependencies(
            load_experiment=load_detector_experiment,
            inspect_git=self.inspect_git,
            verify_tracked_file=self.verify_tracked,
            verify_commit_ancestor=self.verify_ancestor,
            verify_source=self.verify_source,
            is_git_ignored=lambda root, relative: True,
            load_annotation=self.load_annotation,
            load_detection=self.load_detection,
            evaluate=self.evaluate,
            aggregate=aggregate_evaluation_reports,
            write_report=self.write_report,
        )


class DetectorExperimentScoringTests(unittest.TestCase):
    def test_complete_grid_is_deterministic_embargo_safe_and_reusable(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            state = SyntheticScoringContext(Path(temporary_directory))
            summary = score_detector_experiment(
                state.manifest_path,
                state.root,
                dependencies=state.dependencies(),
            )

            self.assertFalse(summary.reused_existing)
            self.assertEqual(summary.head, SCORER_HEAD)
            self.assertEqual(summary.pilot_window_count, 3)
            self.assertEqual(summary.grid_cell_count, 45)
            self.assertEqual(summary.evaluation_report_count, 135)
            self.assertEqual(summary.output_path, state.output_path)
            self.assertEqual(state.write_calls, [state.output_path])
            report = load_scoring_report(state.output_path)
            self.assertEqual(set(report), set(TOP_LEVEL_FIELDS))
            self.assertEqual(report["schema_version"], SCHEMA_VERSION)
            self.assertEqual(report["evaluator_code_commit"], SCORER_HEAD)
            self.assertEqual(report["detector_code_commit"], DETECTOR_HEAD)
            self.assertEqual(
                report["interpretation_constraints"],
                INTERPRETATION_CONSTRAINTS,
            )
            self.assertIsNone(report["selected_operating_point"])
            self.assertIsNone(report["quality_gate"])
            self.assertEqual(len(report["evaluation_reports"]), 135)
            self.assertEqual(len(report["aggregate_results"]), 45)
            expected_annotation_ids = [
                window.annotation_set_id
                for window in state.experiment.windows_for_inference()
            ]
            self.assertEqual(
                [item["annotation_set_id"] for item in report["pilot_inputs"]],
                expected_annotation_ids,
            )
            self.assertNotIn(
                "representative_evaluation",
                state.output_path.read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                "challenge_evaluation",
                state.output_path.read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                "test_holdout",
                state.output_path.read_text(encoding="utf-8"),
            )
            self.assertEqual(len(state.annotation_load_calls), 3)
            self.assertEqual(len(state.detection_load_calls), 3)
            self.assertEqual(len(state.evaluation_calls), 135)
            expected_call_settings = [
                (threshold, radius)
                for threshold in state.experiment.scoring_grid.confidence_thresholds
                for radius in state.experiment.scoring_grid.localization_radii_px
                for _ in range(3)
            ]
            self.assertEqual(
                [(threshold, radius) for _, threshold, radius in state.evaluation_calls],
                expected_call_settings,
            )
            self.assertEqual(len(state.tracked_calls), 20)
            self.assertEqual(len(state.source_calls), 3)
            self.assertEqual(
                state.ancestry_calls,
                [(DETECTOR_HEAD, SCORER_HEAD, MANIFEST_RELATIVE)],
            )
            original_bytes = state.output_path.read_bytes()
            original_mtime = state.output_path.stat().st_mtime_ns
            state.snapshots = [state.snapshot(), state.snapshot()]
            state.evaluation_calls.clear()
            second = score_detector_experiment(
                state.manifest_path,
                state.root,
                dependencies=state.dependencies(),
            )
            self.assertTrue(second.reused_existing)
            self.assertEqual(state.output_path.read_bytes(), original_bytes)
            self.assertEqual(state.output_path.stat().st_mtime_ns, original_mtime)
            self.assertEqual(len(state.evaluation_calls), 135)
            self.assertEqual(state.write_calls, [state.output_path])
            self.assertEqual(
                state.ancestry_calls,
                [(DETECTOR_HEAD, SCORER_HEAD, MANIFEST_RELATIVE)] * 2,
            )

    def test_dirty_or_drifting_git_refuses_without_output(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            state = SyntheticScoringContext(Path(temporary_directory))
            state.snapshots = [state.snapshot(clean=False)]

            with self.assertRaisesRegex(
                DetectorExperimentScoringError,
                "clean",
            ):
                score_detector_experiment(
                    state.manifest_path,
                    state.root,
                    dependencies=state.dependencies(),
                )

            self.assertFalse(state.output_path.exists())
            self.assertEqual(state.annotation_load_calls, [])

        with tempfile.TemporaryDirectory() as temporary_directory:
            state = SyntheticScoringContext(Path(temporary_directory))
            state.snapshots = [
                state.snapshot(),
                state.snapshot(head="c" * 40),
            ]

            with self.assertRaisesRegex(
                DetectorExperimentScoringError,
                "HEAD changed",
            ):
                score_detector_experiment(
                    state.manifest_path,
                    state.root,
                    dependencies=state.dependencies(),
                )

            self.assertFalse(state.output_path.exists())

    def test_incomplete_detection_and_unignored_output_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            state = SyntheticScoringContext(Path(temporary_directory))
            first_window = state.experiment.windows_for_inference()[0]
            detection_path = state.root.joinpath(*first_window.output_path.parts)
            payload = json.loads(detection_path.read_text(encoding="utf-8"))
            payload["frames"][0].update(
                {
                    "inference_status": "not_run",
                    "failure_reason": "synthetic pending frame",
                    "detections": None,
                }
            )
            write_json(detection_path, payload)

            with self.assertRaisesRegex(
                DetectorExperimentScoringError,
                "incomplete",
            ):
                score_detector_experiment(
                    state.manifest_path,
                    state.root,
                    dependencies=state.dependencies(),
                )

            self.assertFalse(state.output_path.exists())

        with tempfile.TemporaryDirectory() as temporary_directory:
            state = SyntheticScoringContext(Path(temporary_directory))
            dependencies = replace(
                state.dependencies(),
                is_git_ignored=lambda root, relative: False,
            )

            with self.assertRaisesRegex(
                DetectorExperimentScoringError,
                "not Git-ignored",
            ):
                score_detector_experiment(
                    state.manifest_path,
                    state.root,
                    dependencies=dependencies,
                )

            self.assertFalse(state.output_path.exists())

    def test_existing_conflict_and_strict_schema_tamper_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            state = SyntheticScoringContext(Path(temporary_directory))
            score_detector_experiment(
                state.manifest_path,
                state.root,
                dependencies=state.dependencies(),
            )
            payload = json.loads(state.output_path.read_text(encoding="utf-8"))
            noncanonical_path = copy.deepcopy(payload)
            noncanonical_path["experiment_manifest"]["path"] = (
                "configs//ball_tracking/experiments/manifest.json"
            )

            with self.assertRaisesRegex(
                DetectorExperimentScoringError,
                "normalized repository-relative path",
            ):
                validate_scoring_report(noncanonical_path)

            windows_unsafe_path = copy.deepcopy(payload)
            windows_unsafe_path["experiment_manifest"]["path"] = (
                "configs/con/manifest.json"
            )

            with self.assertRaisesRegex(
                DetectorExperimentScoringError,
                "Windows-unsafe",
            ):
                validate_scoring_report(windows_unsafe_path)

            payload["aggregate_results"][0]["aggregate"][
                "true_positive_count"
            ] += 1
            write_json(state.output_path, payload)
            conflicting_bytes = state.output_path.read_bytes()
            state.snapshots = [state.snapshot(), state.snapshot()]

            with self.assertRaisesRegex(
                DetectorExperimentScoringError,
                "invalid|conflicts",
            ):
                score_detector_experiment(
                    state.manifest_path,
                    state.root,
                    dependencies=state.dependencies(),
                )

            self.assertEqual(state.output_path.read_bytes(), conflicting_bytes)

            payload = json.loads(conflicting_bytes)
            payload["unexpected"] = True

            with self.assertRaisesRegex(
                DetectorExperimentScoringError,
                "not closed",
            ):
                validate_scoring_report(payload)

    def test_cli_surface_has_no_scoring_or_path_override(self):
        parser = build_argument_parser()
        option_strings = {
            option
            for action in parser._actions
            for option in action.option_strings
        }
        self.assertEqual(
            option_strings,
            {"-h", "--help", "--experiment", "--repository-root"},
        )


if __name__ == "__main__":
    unittest.main()
