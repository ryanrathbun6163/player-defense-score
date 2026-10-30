"""Focused tests for candidate-versus-truth detector review evidence."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path, PurePosixPath

import numpy as np

from src.ball_tracking.annotations import (
    BallGeometry,
    BallAnnotationSet,
    FrameAnnotation,
    SourceVideo,
    load_annotations,
)
from src.ball_tracking.detections import (
    SCHEMA_VERSION as DETECTION_SCHEMA_VERSION,
    BallDetection,
    BallDetectionRun,
    DetectionFrame,
    load_detection_run,
)
from src.ball_tracking.detector_experiments import (
    build_model_provenance,
    load_detector_experiment,
)
from src.ball_tracking.prepare_detection_visual_review import (
    COMPARISON_HEIGHT_PX,
    COMPARISON_WIDTH_PX,
    BLUE,
    EXPECTED_FRAME_COUNT,
    HEATMAP_HEIGHT_PX,
    HEATMAP_WIDTH_PX,
    ORANGE,
    PLAN_SCHEMA_VERSION,
    SCHEMA_VERSION,
    ZOOM_FACTOR,
    ZOOM_PANEL_HEADER_PX,
    ZOOM_SOURCE_SIZE_PX,
    DetectionReviewView,
    DetectionVisualReviewError,
    PreparedVisualPilot,
    VisualReviewDependencies,
    build_metric_heatmaps,
    candidate_display_roles,
    load_detection_review_plan,
    prepare_detection_visual_review,
    render_detection_overlay,
    render_truth_region_panel,
    validate_detection_visual_review_bundle_integrity,
)
from src.ball_tracking.run_detector_experiment import GitSnapshot
from src.ball_tracking.score_detector_experiment import (
    PreparedPilot,
    atomic_write_new_scoring_report,
    build_scoring_report,
    load_scoring_report,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REAL_MANIFEST = (
    REPOSITORY_ROOT
    / "configs"
    / "ball_tracking"
    / "experiments"
    / "rfdetr_medium_image_only_baseline_v0_1.json"
)
SCORER_HEAD = "b" * 40
DETECTOR_HEAD = "a" * 40
RENDERER_HEAD = "c" * 40


def write_json(path: Path, payload: dict) -> bytes:
    content = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return content


def reviewed_annotation_payload(window, source: SourceVideo) -> dict:
    rows = []

    for position, frame_index in enumerate(
        range(window.start_frame_index, window.end_frame_index + 1)
    ):
        if position == 2:
            row = {
                "frame_index": frame_index,
                "annotation_status": "labeled",
                "visibility": "not_visible",
                "absence_reason": "occluded",
                "game_ball_identity_certainty": "probable",
                "geometry": None,
                "localization_eligible": False,
                "difficulty_tags": ["player_overlap"],
                "notes": None,
            }
        elif position == 3:
            row = {
                "frame_index": frame_index,
                "annotation_status": "labeled",
                "visibility": "indeterminate",
                "absence_reason": None,
                "game_ball_identity_certainty": "ambiguous",
                "geometry": None,
                "localization_eligible": False,
                "difficulty_tags": ["background_clutter"],
                "notes": "Synthetic ambiguity for unscored coverage.",
            }
        else:
            row = {
                "frame_index": frame_index,
                "annotation_status": "labeled",
                "visibility": "fully_visible",
                "absence_reason": None,
                "game_ball_identity_certainty": "certain",
                "geometry": {
                    "center_xy_px": [
                        82.25 + position * 2.0,
                        72.5 + position,
                    ],
                    "source": "observed_complete_ball_center",
                    "uncertainty_radius_px": 3.0,
                },
                "localization_eligible": True,
                "difficulty_tags": [],
                "notes": None,
            }
        rows.append(row)

    return {
        "schema_version": "0.1",
        "annotation_set_id": window.annotation_set_id,
        "possession_id": window.possession_id,
        "source_video": source.to_dict(),
        "window": {
            "start_frame_index": window.start_frame_index,
            "end_frame_index": window.end_frame_index,
            "selection_purpose": "protocol_adjudication",
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
            "status": "reviewed",
            "annotator_id": "synthetic_annotator",
            "reviewer_id": "synthetic_reviewer",
            "created_at_utc": "2026-08-23T12:00:00Z",
            "reviewed_at_utc": "2026-08-23T13:00:00Z",
        },
        "annotations": rows,
    }


def candidate(
    index: int,
    confidence: float,
    center_x: float,
    center_y: float,
) -> dict:
    return {
        "candidate_index": index,
        "class_id": 37,
        "class_name": "sports ball",
        "confidence": confidence,
        "bbox_xyxy_px": [
            center_x - 5.0,
            center_y - 5.0,
            center_x + 5.0,
            center_y + 5.0,
        ],
        "center_xy_px": [center_x, center_y],
    }


def detection_payload(experiment, window, source, annotations) -> dict:
    provenance = build_model_provenance(
        experiment.detector,
        code_commit=DETECTOR_HEAD,
        runtime_device="cuda:0 | synthetic visual fixture",
    )
    frames = []

    for position, annotation in enumerate(annotations.annotations):
        detections = []

        if position == 0:
            center_x, center_y = annotation.geometry.center_xy_px
            detections = [
                candidate(0, 0.45, 24.0, 20.0),
                candidate(1, 0.40, center_x, center_y),
                candidate(2, 0.30, center_x + 2.0, center_y),
            ]
        elif position == 1:
            detections = [candidate(0, 0.25, 22.0, 18.0)]
        elif position in {2, 3}:
            detections = [candidate(0, 0.25, 24.0, 20.0)]
        elif position == EXPECTED_FRAME_COUNT - 1:
            detections = []
        elif annotation.localization_eligible:
            center_x, center_y = annotation.geometry.center_xy_px
            detections = [candidate(0, 0.40, center_x, center_y)]

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
        "source_video": source.to_dict(),
        "window": {
            "start_frame_index": window.start_frame_index,
            "end_frame_index": window.end_frame_index,
        },
        "model_provenance": provenance.to_dict(),
        "frames": frames,
    }


class SyntheticVisualContext:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        base_experiment = load_detector_experiment(REAL_MANIFEST)
        source_by_possession = {}

        for possession_index, possession_id in enumerate(
            sorted({window.possession_id for window in base_experiment.windows})
        ):
            source_path = (
                self.root / "data" / "clips" / f"{possession_id}.synthetic"
            )
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_content = (
                f"synthetic-source-{possession_id}\n".encode("utf-8")
            )
            source_path.write_bytes(source_content)
            source_by_possession[possession_id] = SourceVideo.from_mapping(
                {
                    "path": source_path.relative_to(self.root).as_posix(),
                    "sha256": hashlib.sha256(source_content).hexdigest(),
                    "width_px": 320,
                    "height_px": 180,
                    "fps": 10.0,
                    "frame_count": 500,
                }
            )

        windows = tuple(
            replace(
                window,
                source_video=source_by_possession[window.possession_id],
                output_path=PurePosixPath(
                    "data",
                    "outputs",
                    "ball_tracking",
                    "detections",
                    "synthetic_visual_experiment_v0_1",
                    window.output_path.name,
                ),
            )
            for window in base_experiment.windows
        )
        self.experiment = replace(
            base_experiment,
            experiment_id="synthetic_visual_experiment_v0_1",
            windows=windows,
        )
        self.experiment_relative = PurePosixPath(
            "configs/ball_tracking/experiments/synthetic_visual_experiment_v0_1.json"
        )
        self.experiment_path = self.root.joinpath(*self.experiment_relative.parts)
        self.experiment_bytes = write_json(
            self.experiment_path,
            self.experiment.to_dict(),
        )
        prepared_pilots = []
        self.annotations_by_id = {}
        self.detections_by_id = {}

        for window in self.experiment.windows_for_inference():
            source = source_by_possession[window.possession_id]
            annotation_path = (
                self.root
                / "configs"
                / "ball_tracking"
                / "annotations"
                / f"{window.annotation_set_id}.json"
            )
            annotation_bytes = write_json(
                annotation_path,
                reviewed_annotation_payload(window, source),
            )
            annotations = load_annotations(annotation_path)
            detection_path = self.root.joinpath(*window.output_path.parts)
            detection_bytes = write_json(
                detection_path,
                detection_payload(
                    self.experiment,
                    window,
                    source,
                    annotations,
                ),
            )
            detections = load_detection_run(detection_path)
            self.annotations_by_id[annotations.annotation_set_id] = annotations
            self.detections_by_id[detections.detection_run_id] = detections
            prepared_pilots.append(
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

        report = build_scoring_report(
            self.experiment,
            self.experiment_relative,
            self.experiment_bytes,
            SCORER_HEAD,
            prepared_pilots,
        )
        self.report_relative = PurePosixPath(
            "data/outputs/ball_tracking/evaluations/"
            "synthetic_visual_experiment_v0_1/"
            "protocol_adjudication_grid_v0_1.json"
        )
        self.report_path = self.root.joinpath(*self.report_relative.parts)
        atomic_write_new_scoring_report(report, self.report_path)
        self.plan_relative = PurePosixPath(
            "configs/ball_tracking/reviews/synthetic_visual_review_v0_1.json"
        )
        self.plan_path = self.root.joinpath(*self.plan_relative.parts)
        self.plan_bytes = write_json(
            self.plan_path,
            {
                "schema_version": PLAN_SCHEMA_VERSION,
                "review_id": "synthetic_visual_review_v0_1",
                "experiment_id": self.experiment.experiment_id,
                "scoring_report_path": self.report_relative.as_posix(),
                "purpose": "descriptive_protocol_pilot_candidate_comparison",
                "views": [
                    {
                        "view_id": "diagnostic_035_r10",
                        "confidence_threshold": 0.35,
                        "localization_radius_px": 10.0,
                        "role": "higher_precision_descriptive_view_not_selected",
                    },
                    {
                        "view_id": "tracker_020_r10",
                        "confidence_threshold": 0.20,
                        "localization_radius_px": 10.0,
                        "role": "higher_recall_candidate_view_not_selected",
                    },
                ],
                "render_scope": {
                    "selection_purpose": "protocol_adjudication",
                    "all_authorized_pilots": True,
                    "all_frames_including_final": True,
                    "full_resolution_overlays": True,
                    "synchronized_comparison": True,
                    "truth_region_zoom": True,
                    "category_contact_sheets": True,
                    "metric_heatmaps": True,
                },
                "interpretation": {
                    "selected_operating_point": None,
                    "quality_gate": None,
                    "model_winner_claimed": False,
                    "generalization_claimed": False,
                    "holdout_evidence_included": False,
                    "decision_statement": (
                        "Synthetic descriptive comparison; neither view is selected."
                    ),
                },
            },
        )
        self.snapshots = [self.snapshot(), self.snapshot()]
        self.decode_calls = []
        self.playback_calls = []

    def snapshot(self):
        return GitSnapshot(
            repository_root=self.root,
            head=RENDERER_HEAD,
            clean=True,
            manifest_tracked=True,
            manifest_matches_head=True,
            tracked_experiment_manifests=(self.experiment_relative,),
            all_experiment_manifests_match_head=True,
        )

    def inspect_git(self, root, manifest_relative):
        self.assert_root(root)
        self.assertEqualPath(manifest_relative, self.experiment_relative)
        return self.snapshots.pop(0) if self.snapshots else self.snapshot()

    def assert_root(self, root):
        if root != self.root:
            raise AssertionError((root, self.root))

    def assertEqualPath(self, actual, expected):
        if actual != expected:
            raise AssertionError((actual, expected))

    def verify_tracked(self, root, relative):
        self.assert_root(root)
        if relative != self.plan_relative and relative.parts[:3] != (
            "configs",
            "ball_tracking",
            "annotations",
        ):
            raise AssertionError(relative)

    def verify_source(self, source, root):
        self.assert_root(root)
        return source.to_dict()

    def decode_window(self, source_path, annotations):
        self.decode_calls.append(annotations.annotation_set_id)
        height = annotations.source_video.height_px
        width = annotations.source_video.width_px
        frames = []

        for position in range(EXPECTED_FRAME_COUNT):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:, :, 0] = position * 9 % 256
            frame[:, :, 1] = np.arange(width, dtype=np.uint16) % 256
            frame[:, :, 2] = np.arange(height, dtype=np.uint8)[:, None]
            frames.append(frame)

        return frames

    def write_playback(self, path, frames, width, height, fps):
        self.playback_calls.append((len(frames), width, height, fps))
        payload = (
            f"synthetic-playback:{len(frames)}:{width}:{height}:{fps}\n"
        ).encode("utf-8")
        path.write_bytes(payload)
        return "FAKE"

    def dependencies(self):
        return VisualReviewDependencies(
            load_plan=load_detection_review_plan,
            load_experiment=lambda path: self.experiment,
            load_scoring_report=load_scoring_report,
            inspect_git=self.inspect_git,
            verify_tracked_file=self.verify_tracked,
            is_git_ignored=lambda root, relative: True,
            load_annotation=load_annotations,
            load_detection=load_detection_run,
            verify_source=self.verify_source,
            decode_window=self.decode_window,
            write_playback=self.write_playback,
        )


class PureDetectionVisualReviewTests(unittest.TestCase):
    def test_review_plan_is_strict_and_descriptive(self):
        real_plan = (
            REPOSITORY_ROOT
            / "configs"
            / "ball_tracking"
            / "reviews"
            / "rfdetr_medium_pilot_candidate_comparison_v0_1.json"
        )
        plan = load_detection_review_plan(real_plan)
        self.assertEqual(plan.schema_version, PLAN_SCHEMA_VERSION)
        self.assertEqual(
            [
                (view.confidence_threshold, view.localization_radius_px)
                for view in plan.views
            ],
            [(0.35, 10.0), (0.20, 10.0)],
        )
        self.assertIsNone(plan.interpretation["selected_operating_point"])
        self.assertFalse(plan.interpretation["generalization_claimed"])

        payload = json.loads(real_plan.read_text(encoding="utf-8"))
        payload["views"][0]["view_id"] = "../../outside"

        with tempfile.TemporaryDirectory() as temporary_directory:
            malicious_plan = Path(temporary_directory) / "plan.json"
            write_json(malicious_plan, payload)

            with self.assertRaisesRegex(
                DetectionVisualReviewError,
                "portable lowercase underscore identifier",
            ):
                load_detection_review_plan(malicious_plan)

    def test_ambiguous_geometry_is_unscored_context_not_truth(self):
        annotation = FrameAnnotation(
            frame_index=335,
            annotation_status="labeled",
            visibility="partially_visible",
            absence_reason=None,
            game_ball_identity_certainty="ambiguous",
            geometry=BallGeometry(
                center_xy_px=(160.25, 90.5),
                source="human_amodal_estimate",
                uncertainty_radius_px=5.0,
            ),
            localization_eligible=False,
            difficulty_tags=("player_overlap",),
            notes="Ambiguous synthetic annotation.",
        )
        detection = BallDetection(
            candidate_index=0,
            class_id=37,
            class_name="sports ball",
            confidence=0.4,
            bbox_xyxy_px=(150.0, 80.0, 160.0, 90.0),
            center_xy_px=(155.0, 85.0),
        )
        detection_frame = DetectionFrame(
            frame_index=335,
            inference_status="completed",
            failure_reason=None,
            detections=(detection,),
        )
        frame_result = {
            "frame_index": 335,
            "scoring_status": "unscored",
            "input_detection_count": 1,
            "accepted_detection_count": 1,
            "matched_candidate_index": None,
            "false_positive_count": 0,
            "false_negative_count": 0,
            "duplicate_false_positive_count": 0,
            "non_visible_false_alarm_count": 0,
            "unscored_prediction_count": 1,
        }
        view = DetectionReviewView(
            "tracker_020_r10",
            0.20,
            10.0,
            "higher_recall_not_selected",
        )
        source = np.zeros((180, 320, 3), dtype=np.uint8)
        overlay, roles = render_detection_overlay(
            source,
            annotation,
            detection_frame,
            frame_result,
            view,
        )
        source_view = overlay[:, : source.shape[1]]

        self.assertEqual(roles[0]["role"], "unscored_prediction")
        self.assertIsNone(roles[0]["center_error_px"])
        self.assertTrue(np.any(np.all(source_view == ORANGE, axis=2)))
        self.assertFalse(np.any(np.all(source_view == BLUE, axis=2)))

        _, metadata = render_truth_region_panel(
            source,
            (overlay, overlay.copy()),
            annotation,
            detection_frame,
            (view, replace(view, view_id="diagnostic_035_r10")),
        )
        self.assertEqual(
            metadata["focus_type"],
            "ambiguous_unscored_annotation_center_not_truth",
        )

    def test_right_edge_zoom_zero_pads_instead_of_cropping_sidebar(self):
        source = np.zeros((180, 320, 3), dtype=np.uint8)
        overlay = np.full((180, 840, 3), 199, dtype=np.uint8)
        overlay[:, : source.shape[1]] = source
        annotation = FrameAnnotation(
            frame_index=10,
            annotation_status="labeled",
            visibility="fully_visible",
            absence_reason=None,
            game_ball_identity_certainty="certain",
            geometry=BallGeometry(
                center_xy_px=(318.5, 90.0),
                source="observed_complete_ball_center",
                uncertainty_radius_px=3.0,
            ),
            localization_eligible=True,
            difficulty_tags=(),
            notes=None,
        )
        detection_frame = DetectionFrame(
            frame_index=10,
            inference_status="completed",
            failure_reason=None,
            detections=(),
        )
        views = (
            DetectionReviewView("diagnostic_035_r10", 0.35, 10.0, "a"),
            DetectionReviewView("tracker_020_r10", 0.20, 10.0, "b"),
        )
        panel, metadata = render_truth_region_panel(
            source,
            (overlay, overlay.copy()),
            annotation,
            detection_frame,
            views,
        )
        column_width = ZOOM_SOURCE_SIZE_PX * ZOOM_FACTOR

        self.assertGreater(
            metadata["requested_source_crop_xyxy_px"][2],
            source.shape[1] - 1,
        )

        for column_index in (1, 2):
            column_end = (column_index + 1) * column_width
            padded_interior = panel[
                ZOOM_PANEL_HEADER_PX + 4 : -4,
                column_end - 180 : column_end - 4,
            ]
            self.assertTrue(np.all(padded_interior == 0))

    def test_candidate_roles_cover_tp_fp_duplicate_negative_and_unscored(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            state = SyntheticVisualContext(Path(temporary_directory))
            pilot_input = load_scoring_report(state.report_path)["pilot_inputs"][0]
            annotations = state.annotations_by_id[pilot_input["annotation_set_id"]]
            detections = state.detections_by_id[pilot_input["detection_run_id"]]
            report = next(
                report
                for report in load_scoring_report(state.report_path)[
                    "evaluation_reports"
                ]
                if report["annotation_set_id"] == annotations.annotation_set_id
                and report["confidence_threshold"] == 0.20
                and report["localization_radius_px"] == 10.0
            )
            annotation_by_frame = annotations.annotation_by_frame()
            detection_by_frame = detections.frame_by_index()
            result_by_frame = {
                result["frame_index"]: result for result in report["frame_results"]
            }
            start = annotations.window.start_frame_index
            roles = candidate_display_roles(
                annotation_by_frame[start],
                detection_by_frame[start],
                result_by_frame[start],
                confidence_threshold=0.20,
                localization_radius_px=10.0,
            )
            self.assertEqual(
                [item["role"] for item in roles],
                [
                    "ordinary_false_positive",
                    "true_positive",
                    "duplicate_false_positive",
                ],
            )
            self.assertEqual(
                candidate_display_roles(
                    annotation_by_frame[start + 2],
                    detection_by_frame[start + 2],
                    result_by_frame[start + 2],
                    confidence_threshold=0.20,
                    localization_radius_px=10.0,
                )[0]["role"],
                "not_visible_false_alarm",
            )
            self.assertEqual(
                candidate_display_roles(
                    annotation_by_frame[start + 3],
                    detection_by_frame[start + 3],
                    result_by_frame[start + 3],
                    confidence_threshold=0.20,
                    localization_radius_px=10.0,
                )[0]["role"],
                "unscored_prediction",
            )

    def test_overlay_preserves_source_and_appends_unobscuring_sidebar(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            state = SyntheticVisualContext(Path(temporary_directory))
            scoring = load_scoring_report(state.report_path)
            pilot_input = scoring["pilot_inputs"][0]
            annotations = state.annotations_by_id[pilot_input["annotation_set_id"]]
            detections = state.detections_by_id[pilot_input["detection_run_id"]]
            report = next(
                report
                for report in scoring["evaluation_reports"]
                if report["annotation_set_id"] == annotations.annotation_set_id
                and report["confidence_threshold"] == 0.20
                and report["localization_radius_px"] == 10.0
            )
            frame_index = annotations.window.start_frame_index
            source = state.decode_window(
                state.root / annotations.source_video.path,
                annotations,
            )[0]
            source_before = source.copy()
            overlay, _ = render_detection_overlay(
                source,
                annotations.annotation_by_frame()[frame_index],
                detections.frame_by_index()[frame_index],
                report["frame_results"][0],
                DetectionReviewView(
                    "tracker_020_r10",
                    0.20,
                    10.0,
                    "higher_recall_not_selected",
                ),
            )
            self.assertTrue(np.array_equal(source, source_before))
            self.assertEqual(overlay.shape[0], source.shape[0])
            self.assertGreater(overlay.shape[1], source.shape[1])
            self.assertTrue(
                np.array_equal(
                    overlay[:, : source.shape[1]][:, -1],
                    source_before[:, -1],
                )
            )

    def test_heatmap_is_fixed_size_and_contains_no_selection_mutation(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            state = SyntheticVisualContext(Path(temporary_directory))
            scoring = load_scoring_report(state.report_path)
            before = copy.deepcopy(scoring)
            heatmap = build_metric_heatmaps(
                scoring,
                (
                    DetectionReviewView("a", 0.35, 10.0, "not_selected"),
                    DetectionReviewView("b", 0.20, 10.0, "not_selected"),
                ),
            )
            self.assertEqual(
                heatmap.shape,
                (HEATMAP_HEIGHT_PX, HEATMAP_WIDTH_PX, 3),
            )
            self.assertEqual(scoring, before)


class DetectionVisualReviewBundleTests(unittest.TestCase):
    def test_scoring_report_is_bound_to_exact_experiment_manifest(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            state = SyntheticVisualContext(Path(temporary_directory))
            state.experiment = replace(
                state.experiment,
                scoring_grid=replace(
                    state.experiment.scoring_grid,
                    confidence_thresholds=(0.15, 0.20, 0.35),
                ),
            )

            with self.assertRaisesRegex(
                DetectionVisualReviewError,
                "canonical experiment content",
            ):
                prepare_detection_visual_review(
                    state.plan_path,
                    state.root,
                    dependencies=state.dependencies(),
                )

    def test_complete_bundle_covers_all_pilots_views_frames_and_final_frame(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            state = SyntheticVisualContext(Path(temporary_directory))
            summary = prepare_detection_visual_review(
                state.plan_path,
                state.root,
                dependencies=state.dependencies(),
            )
            self.assertFalse(summary.reused_existing)
            self.assertEqual(summary.head, RENDERER_HEAD)
            self.assertEqual(summary.pilot_count, 3)
            self.assertEqual(summary.view_count, 2)
            self.assertEqual(summary.rendered_frame_count, 75)
            manifest = validate_detection_visual_review_bundle_integrity(
                summary.output_dir
            )
            self.assertEqual(manifest["schema_version"], SCHEMA_VERSION)
            self.assertIsNone(
                manifest["safeguards"]["selected_operating_point"]
            )
            self.assertEqual(len(manifest["pilots"]), 3)
            self.assertEqual(state.decode_calls.__len__(), 3)
            self.assertEqual(
                state.playback_calls,
                [(25, COMPARISON_WIDTH_PX, COMPARISON_HEIGHT_PX, 5.0)] * 3,
            )

            for pilot in manifest["pilots"]:
                self.assertTrue(pilot["final_frame_included"])
                self.assertEqual(len(pilot["views"]), 2)
                self.assertEqual(len(pilot["comparison_frames"]), 25)
                self.assertEqual(len(pilot["truth_region_panels"]), 25)
                self.assertEqual(
                    pilot["comparison_frames"][-1]["frame_index"],
                    pilot["window"]["end_frame_index"],
                )

                for view in pilot["views"]:
                    self.assertEqual(len(view["overlay_frames"]), 25)
                    self.assertEqual(
                        set(view["category_contact_sheets"]),
                        {
                            "true_positive",
                            "false_negative",
                            "ordinary_false_positive",
                            "duplicate_false_positive",
                            "not_visible_clean_negative",
                            "not_visible_false_alarm",
                            "unscored",
                        },
                    )

            first_overlay = manifest["pilots"][0]["views"][0][
                "overlay_frames"
            ][0]
            self.assertFalse(
                first_overlay[
                    "source_viewport_obscured_by_header_or_sidebar"
                ]
            )
            self.assertGreater(first_overlay["accepted_detection_count"], 0)

    def test_bundle_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            state = SyntheticVisualContext(Path(temporary_directory))
            summary = prepare_detection_visual_review(
                state.plan_path,
                state.root,
                dependencies=state.dependencies(),
            )
            manifest = json.loads(
                (summary.output_dir / "manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            overlay_relative = manifest["pilots"][0]["views"][0][
                "overlay_frames"
            ][0]["path"]
            overlay_path = summary.output_dir.joinpath(
                *PurePosixPath(overlay_relative).parts
            )
            overlay_path.write_bytes(overlay_path.read_bytes() + b"tamper")

            with self.assertRaisesRegex(
                DetectionVisualReviewError,
                "modified",
            ):
                validate_detection_visual_review_bundle_integrity(
                    summary.output_dir
                )

    def test_coherently_rehashed_frame_swap_fails_exact_reuse(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            state = SyntheticVisualContext(Path(temporary_directory))
            summary = prepare_detection_visual_review(
                state.plan_path,
                state.root,
                dependencies=state.dependencies(),
            )
            manifest_path = summary.output_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            overlays = manifest["pilots"][0]["views"][0]["overlay_frames"]
            first_path = summary.output_dir.joinpath(
                *PurePosixPath(overlays[0]["path"]).parts
            )
            final_path = summary.output_dir.joinpath(
                *PurePosixPath(overlays[-1]["path"]).parts
            )
            final_path.write_bytes(first_path.read_bytes())
            overlays[-1]["sha256"] = hashlib.sha256(
                final_path.read_bytes()
            ).hexdigest()
            overlays[-1]["byte_size"] = final_path.stat().st_size
            write_json(manifest_path, manifest)

            validate_detection_visual_review_bundle_integrity(
                summary.output_dir
            )

            with self.assertRaisesRegex(
                DetectionVisualReviewError,
                "conflicts with exact regenerated assets",
            ):
                prepare_detection_visual_review(
                    state.plan_path,
                    state.root,
                    dependencies=state.dependencies(),
                )


if __name__ == "__main__":
    unittest.main()
