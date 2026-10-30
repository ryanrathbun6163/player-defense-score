import copy
import json
import tempfile
import unittest
from pathlib import Path

from src.ball_tracking.detector_experiments import (
    EVALUATION_PURPOSES,
    EXPECTED_DETECTOR_SETTINGS,
    EXPECTED_LEAKAGE_CONTROLS,
    KNOWN_PRIOR_PREDICTION_EXCLUSION_BINDING,
    KNOWN_PROTOCOL_PILOT_BINDINGS,
    PREDICTION_EMBARGO,
    READY_FOR_INFERENCE,
    DetectorExperiment,
    DetectorExperimentValidationError,
    build_model_provenance,
    load_detector_experiment,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REAL_MANIFEST_PATH = (
    REPOSITORY_ROOT
    / "configs"
    / "ball_tracking"
    / "experiments"
    / "rfdetr_medium_image_only_baseline_v0_1.json"
)


SOURCES = {
    "possession_001": {
        "path": "data/clips/possession_001.mp4",
        "sha256": (
            "5c42dad097a27873852d1555a71de36b890eb7bf287cf53ee1cdc693c31fcae6"
        ),
        "width_px": 1920,
        "height_px": 1080,
        "fps": 25.0,
        "frame_count": 499,
    },
    "possession_002": {
        "path": "data/clips/possession_002.mp4",
        "sha256": (
            "e76e9805c390054d7fda9ca4413612d1f22cdb2f64bc58526a193bd8fdecb224"
        ),
        "width_px": 1920,
        "height_px": 1080,
        "fps": 25.0,
        "frame_count": 499,
    },
    "possession_003": {
        "path": "data/clips/possession_003.mp4",
        "sha256": (
            "6b0088df4434ebcd9de84997f871f26698544ebdd237f46d1f4a39937cf40531"
        ),
        "width_px": 1920,
        "height_px": 1080,
        "fps": 25.0,
        "frame_count": 500,
    },
}

PILOTS = (
    (
        "possession_001_frames_0375_0399_protocol_adjudication_v0_1",
        "possession_001",
        375,
        399,
    ),
    (
        "possession_002_frames_0318_0342_protocol_adjudication_v0_1",
        "possession_002",
        318,
        342,
    ),
    (
        "possession_003_frames_0416_0440_protocol_adjudication_v0_1",
        "possession_003",
        416,
        440,
    ),
)


def window_payload(
    possession_id,
    start,
    end,
    purpose,
    *,
    suffix,
    annotation_set_id=None,
):
    status = (
        READY_FOR_INFERENCE
        if purpose == "protocol_adjudication"
        else PREDICTION_EMBARGO
    )
    return {
        "window_id": f"{possession_id}_{suffix}",
        "annotation_set_id": (
            f"{possession_id}_{suffix}_annotations_v0_1"
            if annotation_set_id is None
            else annotation_set_id
        ),
        "detection_run_id": f"{possession_id}_{suffix}_rfdetr_v0_1",
        "possession_id": possession_id,
        "source_video": copy.deepcopy(SOURCES[possession_id]),
        "start_frame_index": start,
        "end_frame_index": end,
        "selection_purpose": purpose,
        "execution_status": status,
        "selection_rationale": (
            "Contiguous prediction-blind window selected before model output."
        ),
        "output_path": (
            "data/outputs/ball_tracking/detections/experiment_v0_1/"
            f"{possession_id}_{suffix}.json"
        ),
    }


def valid_payload():
    windows = [
        window_payload(
            possession_id,
            start,
            end,
            "protocol_adjudication",
            suffix=f"pilot_{start:04d}_{end:04d}",
            annotation_set_id=annotation_set_id,
        )
        for annotation_set_id, possession_id, start, end in PILOTS
    ]
    evaluation_windows = (
        ("representative_evaluation", 0, 24, "representative_0000_0024"),
        ("challenge_evaluation", 50, 74, "challenge_0050_0074"),
        ("test_holdout", 100, 124, "holdout_0100_0124"),
    )
    for possession_id in SOURCES:
        windows.extend(
            window_payload(
                possession_id,
                start,
                end,
                purpose,
                suffix=suffix,
            )
            for purpose, start, end, suffix in evaluation_windows
        )
    return {
        "schema_version": "ball_detector_experiment/v0.1",
        "experiment_id": "rfdetr_medium_coco_image_only_v0_1",
        "experiment_purpose": "image_only_ball_detector_baseline",
        "protocol_reference": "docs/ball_tracking_annotation_protocol.md",
        "precommit": {
            "recorded_at_utc": "2026-08-24T02:00:00Z",
            "decision_owner": "ryan",
            "window_selection_rule": (
                "Select fixed contiguous windows without detector predictions."
            ),
            "detector_selection_rule": (
                "Run one untuned official COCO baseline descriptively."
            ),
            "selected_window_predictions_viewed_before_precommit": False,
            "quality_gate_defined": False,
        },
        "window_selection": {
            "window_length_frames": 25,
            "required_evaluation_purposes": list(EVALUATION_PURPOSES),
            "same_source_overlap_policy": "forbid",
            "minimum_intervening_frames": 25,
            "pilot_exclusions": [
                {
                    "annotation_set_id": annotation_set_id,
                    "possession_id": possession_id,
                    "source_video_sha256": SOURCES[possession_id]["sha256"],
                    "start_frame_index": start,
                    "end_frame_index": end,
                }
                for annotation_set_id, possession_id, start, end in PILOTS
            ],
            "prior_prediction_exclusions": [
                {
                    "possession_id": "possession_001",
                    "source_video_sha256": SOURCES["possession_001"]["sha256"],
                    "known_prediction_frame_index": 150,
                    "excluded_start_frame_index": 125,
                    "excluded_end_frame_index": 199,
                    "reason_code": (
                        "historical_exploratory_prediction_viewed_before_precommit"
                    ),
                }
            ],
        },
        "leakage_controls": dict(EXPECTED_LEAKAGE_CONTROLS),
        "detector": dict(EXPECTED_DETECTOR_SETTINGS),
        "scoring_grid": {
            "confidence_thresholds": [
                0.01,
                0.03,
                0.05,
                0.10,
                0.15,
                0.20,
                0.25,
                0.35,
                0.50,
            ],
            "localization_radii_px": [5.0, 10.0, 15.0, 20.0, 30.0],
            "calibration_selection_purposes": [
                "representative_evaluation",
                "challenge_evaluation",
            ],
            "holdout_selection_purpose": "test_holdout",
            "holdout_release_rule": (
                "after_detector_and_operating_point_are_frozen"
            ),
            "quality_gate": None,
        },
        "windows": windows,
    }


class DetectorExperimentManifestTests(unittest.TestCase):
    def test_real_baseline_manifest_has_exact_approved_windows_and_round_trips(self):
        payload = json.loads(REAL_MANIFEST_PATH.read_text(encoding="utf-8"))
        experiment = load_detector_experiment(REAL_MANIFEST_PATH)
        expected_windows = {
            (
                "possession_001",
                "protocol_adjudication",
                375,
                399,
                READY_FOR_INFERENCE,
            ),
            (
                "possession_002",
                "protocol_adjudication",
                318,
                342,
                READY_FOR_INFERENCE,
            ),
            (
                "possession_003",
                "protocol_adjudication",
                416,
                440,
                READY_FOR_INFERENCE,
            ),
            (
                "possession_001",
                "representative_evaluation",
                50,
                74,
                PREDICTION_EMBARGO,
            ),
            (
                "possession_001",
                "challenge_evaluation",
                200,
                224,
                PREDICTION_EMBARGO,
            ),
            (
                "possession_001",
                "test_holdout",
                300,
                324,
                PREDICTION_EMBARGO,
            ),
            (
                "possession_002",
                "representative_evaluation",
                250,
                274,
                PREDICTION_EMBARGO,
            ),
            (
                "possession_002",
                "challenge_evaluation",
                25,
                49,
                PREDICTION_EMBARGO,
            ),
            (
                "possession_002",
                "test_holdout",
                200,
                224,
                PREDICTION_EMBARGO,
            ),
            (
                "possession_003",
                "representative_evaluation",
                300,
                324,
                PREDICTION_EMBARGO,
            ),
            (
                "possession_003",
                "challenge_evaluation",
                150,
                174,
                PREDICTION_EMBARGO,
            ),
            (
                "possession_003",
                "test_holdout",
                250,
                274,
                PREDICTION_EMBARGO,
            ),
        }
        actual_windows = {
            (
                window.possession_id,
                window.selection_purpose,
                window.start_frame_index,
                window.end_frame_index,
                window.execution_status,
            )
            for window in experiment.windows
        }

        self.assertEqual(experiment.experiment_id, REAL_MANIFEST_PATH.stem)
        self.assertEqual(len(experiment.windows), 12)
        self.assertEqual(actual_windows, expected_windows)
        self.assertEqual(
            {
                (
                    window.possession_id,
                    window.start_frame_index,
                    window.end_frame_index,
                )
                for window in experiment.windows_for_inference()
            },
            {
                ("possession_001", 375, 399),
                ("possession_002", 318, 342),
                ("possession_003", 416, 440),
            },
        )
        self.assertEqual(
            {
                window.possession_id: window.source_video.sha256
                for window in experiment.windows
            },
            {
                "possession_001": (
                    "5c42dad097a27873852d1555a71de36b890eb7bf287cf53ee1cdc693c31fcae6"
                ),
                "possession_002": (
                    "e76e9805c390054d7fda9ca4413612d1f22cdb2f64bc58526a193bd8fdecb224"
                ),
                "possession_003": (
                    "6b0088df4434ebcd9de84997f871f26698544ebdd237f46d1f4a39937cf40531"
                ),
            },
        )
        self.assertEqual(
            experiment.scoring_grid.confidence_thresholds,
            (0.01, 0.03, 0.05, 0.10, 0.15, 0.20, 0.25, 0.35, 0.50),
        )
        self.assertEqual(
            experiment.scoring_grid.localization_radii_px,
            (5.0, 10.0, 15.0, 20.0, 30.0),
        )
        self.assertFalse(
            experiment.precommit.selected_window_predictions_viewed_before_precommit
        )
        self.assertEqual(experiment.precommit.decision_owner, "ryan_codex_joint")
        self.assertEqual(experiment.window_selection.minimum_intervening_frames, 25)
        challenge_rationales = {
            window.selection_rationale
            for window in experiment.windows
            if window.selection_purpose == "challenge_evaluation"
        }
        self.assertTrue(
            all(
                (
                    "same-game frame-difference, optical-flow, sharpness, "
                    "brightness-variability, and histogram-change descriptors"
                )
                in item
                for item in challenge_rationales
            )
        )
        self.assertTrue(
            all(
                "player or hand congestion, which was not a ranking input" in item
                for item in challenge_rationales
            )
        )
        self.assertTrue(
            all(
                "does not claim exhaustive rim-interaction" in item
                for item in challenge_rationales
            )
        )
        self.assertEqual(experiment.to_dict(), payload)

    def test_valid_manifest_round_trips_and_exposes_only_ready_pilots(self):
        payload = valid_payload()
        experiment = DetectorExperiment.from_mapping(payload)

        self.assertEqual(experiment.to_dict(), payload)
        self.assertEqual(len(experiment.windows), 12)
        self.assertEqual(len(experiment.ready_windows), 3)
        self.assertEqual(experiment.windows_for_inference(), experiment.ready_windows)
        self.assertEqual(experiment.detector.model_query_count, 300)
        self.assertEqual(experiment.detector.model_logit_slot_count, 91)
        self.assertEqual(experiment.detector.num_select, 27300)
        self.assertEqual(experiment.detector.predict_threshold, 0.0)
        self.assertEqual(
            experiment.detector.predict_threshold_policy,
            "zero_then_adapter_inclusive_export_floor",
        )
        self.assertEqual(
            {window.selection_purpose for window in experiment.ready_windows},
            {"protocol_adjudication"},
        )
        self.assertEqual(
            {
                window.selection_purpose
                for window in experiment.windows
                if window.execution_status == PREDICTION_EMBARGO
            },
            set(EVALUATION_PURPOSES),
        )

    def test_loader_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "duplicate.json"
            path.write_text(
                '{"schema_version":"ball_detector_experiment/v0.1",'
                '"schema_version":"ball_detector_experiment/v0.1"}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                DetectorExperimentValidationError,
                "Duplicate JSON object key",
            ):
                load_detector_experiment(path)

    def test_loader_round_trips_valid_file_and_reports_missing_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "experiment.json"
            path.write_text(json.dumps(valid_payload()), encoding="utf-8")
            self.assertEqual(load_detector_experiment(path).to_dict(), valid_payload())
            with self.assertRaises(FileNotFoundError):
                load_detector_experiment(root / "missing.json")

    def test_closed_schema_and_forbidden_label_fields_are_rejected(self):
        unknown = valid_payload()
        unknown["unexpected"] = True
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "unknown fields",
        ):
            DetectorExperiment.from_mapping(unknown)

        annotation_path = valid_payload()
        annotation_path["windows"][0]["annotation_path"] = (
            "configs/ball_tracking/annotations/labels.json"
        )
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "forbidden inference field 'annotation_path'",
        ):
            DetectorExperiment.from_mapping(annotation_path)

        leaked_labels = valid_payload()
        leaked_labels["windows"][0]["labels"] = [{"center_xy_px": [1, 2]}]
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "forbidden inference field 'labels'",
        ):
            DetectorExperiment.from_mapping(leaked_labels)

    def test_schema_identity_and_protocol_are_frozen(self):
        mutations = (
            ("schema_version", "0.2"),
            ("experiment_purpose", "model_selection"),
            ("protocol_reference", "somewhere_else.md"),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                payload = valid_payload()
                payload[field] = value
                with self.assertRaises(DetectorExperimentValidationError):
                    DetectorExperiment.from_mapping(payload)

    def test_precommit_requires_prediction_blind_no_gate_state_and_utc(self):
        invalid_values = (
            (
                "selected_window_predictions_viewed_before_precommit",
                True,
            ),
            ("quality_gate_defined", True),
            ("recorded_at_utc", "2026-08-24T02:00:00"),
            ("recorded_at_utc", "2026-08-24T02:00:00-07:00"),
        )
        for field, value in invalid_values:
            with self.subTest(field=field, value=value):
                payload = valid_payload()
                payload["precommit"][field] = value
                with self.assertRaises(DetectorExperimentValidationError):
                    DetectorExperiment.from_mapping(payload)

    def test_window_selection_plan_is_fixed_and_has_three_unique_exclusions(self):
        mutations = (
            ("window_length_frames", 24),
            (
                "required_evaluation_purposes",
                ["challenge_evaluation", "representative_evaluation", "test_holdout"],
            ),
            ("same_source_overlap_policy", "warn"),
            ("minimum_intervening_frames", 24),
            ("minimum_intervening_frames", 26),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                payload = valid_payload()
                payload["window_selection"][field] = value
                with self.assertRaises(DetectorExperimentValidationError):
                    DetectorExperiment.from_mapping(payload)

        wrong_count = valid_payload()
        wrong_count["window_selection"]["pilot_exclusions"].pop()
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "exactly 3 entries",
        ):
            DetectorExperiment.from_mapping(wrong_count)

        duplicate = valid_payload()
        duplicate["window_selection"]["pilot_exclusions"][2] = copy.deepcopy(
            duplicate["window_selection"]["pilot_exclusions"][1]
        )
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "must be unique",
        ):
            DetectorExperiment.from_mapping(duplicate)

        missing_prior_guard = valid_payload()
        missing_prior_guard["window_selection"][
            "prior_prediction_exclusions"
        ].clear()
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "exactly the 1 known historical entry",
        ):
            DetectorExperiment.from_mapping(missing_prior_guard)

    def test_exactly_three_pilot_windows_must_match_exclusions(self):
        missing_pilot = valid_payload()
        missing_pilot["windows"][0]["selection_purpose"] = (
            "representative_evaluation"
        )
        missing_pilot["windows"][0]["execution_status"] = PREDICTION_EMBARGO
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "exactly 3 protocol_adjudication",
        ):
            DetectorExperiment.from_mapping(missing_pilot)

        mismatched_exclusion = valid_payload()
        exclusion = mismatched_exclusion["window_selection"]["pilot_exclusions"][0]
        exclusion["start_frame_index"] = 350
        exclusion["end_frame_index"] = 374
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "must exactly match",
        ):
            DetectorExperiment.from_mapping(mismatched_exclusion)

    def test_pilots_and_exclusions_cannot_be_mutated_together(self):
        payload = valid_payload()
        pilot = payload["windows"][0]
        exclusion = payload["window_selection"]["pilot_exclusions"][0]
        fake_annotation_set_id = "fake_p001_protocol_pilot"
        pilot["annotation_set_id"] = fake_annotation_set_id
        pilot["start_frame_index"] = 350
        pilot["end_frame_index"] = 374
        exclusion["annotation_set_id"] = fake_annotation_set_id
        exclusion["start_frame_index"] = 350
        exclusion["end_frame_index"] = 374

        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "known reviewed protocol pilot bindings",
        ):
            DetectorExperiment.from_mapping(payload)

    def test_known_prior_prediction_guard_is_exact_and_blocks_overlap(self):
        mutated_guard = valid_payload()
        mutated_guard["window_selection"]["prior_prediction_exclusions"][0][
            "known_prediction_frame_index"
        ] = 151
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "known P001 historical prediction guard",
        ):
            DetectorExperiment.from_mapping(mutated_guard)

        for start, end in ((101, 125), (175, 199), (199, 223)):
            with self.subTest(start=start, end=end):
                overlap = valid_payload()
                representative = next(
                    window
                    for window in overlap["windows"]
                    if window["possession_id"] == "possession_001"
                    and window["selection_purpose"]
                    == "representative_evaluation"
                )
                representative["start_frame_index"] = start
                representative["end_frame_index"] = end
                with self.assertRaisesRegex(
                    DetectorExperimentValidationError,
                    "prior-prediction exclusion",
                ):
                    DetectorExperiment.from_mapping(overlap)

        for start, end in ((100, 124), (200, 224)):
            with self.subTest(nonoverlap_start=start, nonoverlap_end=end):
                nonoverlap = valid_payload()
                if start == 100:
                    holdout = next(
                        window
                        for window in nonoverlap["windows"]
                        if window["possession_id"] == "possession_001"
                        and window["selection_purpose"] == "test_holdout"
                    )
                    holdout["start_frame_index"] = 250
                    holdout["end_frame_index"] = 274
                representative = next(
                    window
                    for window in nonoverlap["windows"]
                    if window["possession_id"] == "possession_001"
                    and window["selection_purpose"]
                    == "representative_evaluation"
                )
                representative["start_frame_index"] = start
                representative["end_frame_index"] = end
                DetectorExperiment.from_mapping(nonoverlap)

    def test_exactly_twelve_windows_are_required(self):
        missing = valid_payload()
        missing["windows"].pop()
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "exactly 12 entries",
        ):
            DetectorExperiment.from_mapping(missing)

        extra = valid_payload()
        extra_window = window_payload(
            "possession_001",
            75,
            99,
            "representative_evaluation",
            suffix="extra_representative_0075_0099",
        )
        extra["windows"].append(extra_window)
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "exactly 12 entries",
        ):
            DetectorExperiment.from_mapping(extra)

    def test_each_possession_requires_every_purpose_exactly_once(self):
        replacements = {
            "representative_evaluation": "challenge_evaluation",
            "challenge_evaluation": "test_holdout",
            "test_holdout": "representative_evaluation",
        }
        for purpose, replacement in replacements.items():
            with self.subTest(purpose=purpose):
                payload = valid_payload()
                target = next(
                    window
                    for window in payload["windows"]
                    if window["possession_id"] == "possession_001"
                    and window["selection_purpose"] == purpose
                )
                target["selection_purpose"] = replacement
                with self.assertRaisesRegex(
                    DetectorExperimentValidationError,
                    "must have every required purpose exactly once",
                ):
                    DetectorExperiment.from_mapping(payload)

    def test_evaluation_windows_must_use_the_same_three_pilot_possessions(self):
        extra_possession = valid_payload()
        extra_possession["windows"][3]["possession_id"] = "possession_004"
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "same 3 possessions as the protocol pilots",
        ):
            DetectorExperiment.from_mapping(extra_possession)

        duplicate_pilot_possession = valid_payload()
        duplicate_pilot_possession["windows"][2]["possession_id"] = (
            "possession_002"
        )
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "pilots must belong to 3 unique possessions",
        ):
            DetectorExperiment.from_mapping(duplicate_pilot_possession)

    def test_pilot_and_evaluation_execution_statuses_are_strict(self):
        pilot_pending = valid_payload()
        pilot_pending["windows"][0]["execution_status"] = PREDICTION_EMBARGO
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "requires execution_status",
        ):
            DetectorExperiment.from_mapping(pilot_pending)

        evaluation_ready = valid_payload()
        evaluation_ready["windows"][3]["execution_status"] = READY_FOR_INFERENCE
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "requires execution_status",
        ):
            DetectorExperiment.from_mapping(evaluation_ready)

    def test_windows_are_exactly_25_in_bounds_frames(self):
        wrong_length = valid_payload()
        wrong_length["windows"][3]["end_frame_index"] = 23
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "exactly 25 frames",
        ):
            DetectorExperiment.from_mapping(wrong_length)

        outside = valid_payload()
        outside["windows"][3]["start_frame_index"] = 475
        outside["windows"][3]["end_frame_index"] = 499
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "below source frame_count",
        ):
            DetectorExperiment.from_mapping(outside)

    def test_window_ids_and_output_paths_are_unique(self):
        fields = ("window_id", "annotation_set_id", "detection_run_id", "output_path")
        for field in fields:
            with self.subTest(field=field):
                payload = valid_payload()
                payload["windows"][4][field] = payload["windows"][3][field]
                with self.assertRaisesRegex(
                    DetectorExperimentValidationError,
                    f"unique {field}",
                ):
                    DetectorExperiment.from_mapping(payload)

        case_only_path = valid_payload()
        original_path = case_only_path["windows"][3]["output_path"]
        directory, filename = original_path.rsplit("/", 1)
        stem, suffix = filename.rsplit(".", 1)
        case_only_path["windows"][4]["output_path"] = (
            f"{directory}/{stem.upper()}.{suffix}"
        )
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "unique output_path",
        ):
            DetectorExperiment.from_mapping(case_only_path)

    def test_output_paths_are_portable_json_beneath_ignored_root(self):
        invalid_paths = (
            "C:/temp/run.json",
            "data/outputs/ball_tracking/../run.json",
            "configs/run.json",
            "data/outputs/ball_tracking/detections/run.csv",
            "data\\outputs\\ball_tracking\\detections\\run.json",
            (
                "data/outputs/ball_tracking/detections/experiment_v0_1/"
                "run.json:stream.json"
            ),
            "data/outputs/ball_tracking/detections/NUL.json",
            "data/outputs/ball_tracking/detections/unsafe./run.json",
            "data/outputs/ball_tracking/detections/unsafe /run.json",
        )
        for output_path in invalid_paths:
            with self.subTest(output_path=output_path):
                payload = valid_payload()
                payload["windows"][3]["output_path"] = output_path
                with self.assertRaises(DetectorExperimentValidationError):
                    DetectorExperiment.from_mapping(payload)

    def test_same_source_windows_cannot_overlap(self):
        payload = valid_payload()
        representative = payload["windows"][3]
        representative["start_frame_index"] = 375
        representative["end_frame_index"] = 399
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "must not overlap",
        ):
            DetectorExperiment.from_mapping(payload)

    def test_same_source_windows_require_25_intervening_unselected_frames(self):
        DetectorExperiment.from_mapping(valid_payload())

        evaluation_gap_24 = valid_payload()
        challenge = next(
            window
            for window in evaluation_gap_24["windows"]
            if window["possession_id"] == "possession_001"
            and window["selection_purpose"] == "challenge_evaluation"
        )
        challenge["start_frame_index"] = 49
        challenge["end_frame_index"] = 73
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "at least 25 completely unselected intervening frames",
        ):
            DetectorExperiment.from_mapping(evaluation_gap_24)

        evaluation_gap_25 = valid_payload()
        challenge = next(
            window
            for window in evaluation_gap_25["windows"]
            if window["possession_id"] == "possession_001"
            and window["selection_purpose"] == "challenge_evaluation"
        )
        challenge["start_frame_index"] = 50
        challenge["end_frame_index"] = 74
        DetectorExperiment.from_mapping(evaluation_gap_25)

        pilot_gap_24 = valid_payload()
        holdout = next(
            window
            for window in pilot_gap_24["windows"]
            if window["possession_id"] == "possession_002"
            and window["selection_purpose"] == "test_holdout"
        )
        holdout["start_frame_index"] = 269
        holdout["end_frame_index"] = 293
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "at least 25 completely unselected intervening frames",
        ):
            DetectorExperiment.from_mapping(pilot_gap_24)

        pilot_gap_25 = valid_payload()
        holdout = next(
            window
            for window in pilot_gap_25["windows"]
            if window["possession_id"] == "possession_002"
            and window["selection_purpose"] == "test_holdout"
        )
        holdout["start_frame_index"] = 268
        holdout["end_frame_index"] = 292
        DetectorExperiment.from_mapping(pilot_gap_25)

    def test_possession_source_contract_is_consistent_and_complete(self):
        inconsistent = valid_payload()
        inconsistent["windows"][3]["source_video"]["width_px"] = 1280
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "inconsistent source_video",
        ):
            DetectorExperiment.from_mapping(inconsistent)

        missing_source_field = valid_payload()
        del missing_source_field["windows"][3]["source_video"]["fps"]
        with self.assertRaisesRegex(
            DetectorExperimentValidationError,
            "source_video is invalid",
        ):
            DetectorExperiment.from_mapping(missing_source_field)

    def test_leakage_controls_are_fixed_and_closed(self):
        for field in EXPECTED_LEAKAGE_CONTROLS:
            with self.subTest(field=field):
                payload = valid_payload()
                current = payload["leakage_controls"][field]
                if isinstance(current, bool):
                    payload["leakage_controls"][field] = not current
                elif isinstance(current, int):
                    payload["leakage_controls"][field] = current + 1
                else:
                    payload["leakage_controls"][field] = "changed"
                with self.assertRaisesRegex(
                    DetectorExperimentValidationError,
                    "fixed image-only",
                ):
                    DetectorExperiment.from_mapping(payload)

    def test_detector_is_exact_frozen_fp32_uncompiled_rfdetr_baseline(self):
        changes = {
            "package_version": "1.9.2",
            "weights_sha256": "0" * 64,
            "device_type": "cpu",
            "precision": "float16",
            "compile_enabled": True,
            "input_width_px": 512,
            "tiling_enabled": True,
            "model_query_count": 299,
            "model_logit_slot_count": 90,
            "num_select": 100,
            "model_candidate_policy": "top_one_per_query",
            "predict_threshold": 0.01,
            "predict_threshold_policy": "nextafter_floor",
            "target_class_id": 32,
            "target_class_name": "ball",
            "export_confidence_floor": 0.02,
            "candidate_ordering": "model_order",
            "code_commit_policy": "allow_dirty",
        }
        for field, value in changes.items():
            with self.subTest(field=field):
                payload = valid_payload()
                payload["detector"][field] = value
                with self.assertRaisesRegex(
                    DetectorExperimentValidationError,
                    "frozen RF-DETR Medium baseline",
                ):
                    DetectorExperiment.from_mapping(payload)

    def test_frozen_detector_and_historical_bindings_match_known_literals(self):
        self.assertEqual(EXPECTED_DETECTOR_SETTINGS["package_version"], "1.9.1")
        self.assertEqual(
            EXPECTED_DETECTOR_SETTINGS["weights_sha256"],
            "749ff6071828aaffac63e204c4f4135ed3d6cdae4d702e086c360edc3b5768c8",
        )
        self.assertEqual(
            EXPECTED_DETECTOR_SETTINGS["resize_mode"],
            "direct RGB bilinear resize to 576x576 without letterboxing or "
            "padding; antialias disabled; ImageNet channel normalization",
        )
        self.assertEqual(
            EXPECTED_DETECTOR_SETTINGS["model_candidate_policy"],
            "all_query_class_pairs_before_target_class_filter",
        )
        self.assertEqual(
            EXPECTED_DETECTOR_SETTINGS["postprocessing_description"],
            "RF-DETR sigmoid scores with all 300 query x 91 logit pairs "
            "selected (num_select=27300); source-pixel box scaling and "
            "clipping; raw COCO class ID 37/name 'sports ball' filtering; "
            "adapter-side inclusive confidence-floor filtering; deterministic "
            "ordering; no NMS, ROI/court filter, tiling, temporal logic, "
            "deduplication, or top-one selection",
        )
        self.assertEqual(
            KNOWN_PROTOCOL_PILOT_BINDINGS,
            (
                (
                    "possession_001_frames_0375_0399_protocol_adjudication_v0_1",
                    "possession_001",
                    "5c42dad097a27873852d1555a71de36b890eb7bf287cf53ee1cdc693c31fcae6",
                    375,
                    399,
                ),
                (
                    "possession_002_frames_0318_0342_protocol_adjudication_v0_1",
                    "possession_002",
                    "e76e9805c390054d7fda9ca4413612d1f22cdb2f64bc58526a193bd8fdecb224",
                    318,
                    342,
                ),
                (
                    "possession_003_frames_0416_0440_protocol_adjudication_v0_1",
                    "possession_003",
                    "6b0088df4434ebcd9de84997f871f26698544ebdd237f46d1f4a39937cf40531",
                    416,
                    440,
                ),
            ),
        )
        self.assertEqual(
            KNOWN_PRIOR_PREDICTION_EXCLUSION_BINDING,
            (
                "possession_001",
                "5c42dad097a27873852d1555a71de36b890eb7bf287cf53ee1cdc693c31fcae6",
                150,
                125,
                199,
                "historical_exploratory_prediction_viewed_before_precommit",
            ),
        )

    def test_scoring_grid_is_strict_sorted_and_begins_at_export_floor(self):
        invalid_grids = (
            ("confidence_thresholds", [0.02, 0.10]),
            ("confidence_thresholds", [0.0100000000001, 0.10]),
            ("confidence_thresholds", [0.01, 0.10, 0.10]),
            ("confidence_thresholds", [0.01, 1.01]),
            ("localization_radii_px", [0.0, 5.0]),
            ("localization_radii_px", [5.0, 4.0]),
            ("localization_radii_px", []),
        )
        for field, values in invalid_grids:
            with self.subTest(field=field, values=values):
                payload = valid_payload()
                payload["scoring_grid"][field] = values
                with self.assertRaises(DetectorExperimentValidationError):
                    DetectorExperiment.from_mapping(payload)

    def test_scoring_roles_holdout_release_and_null_gate_are_fixed(self):
        changes = (
            (
                "calibration_selection_purposes",
                ["representative_evaluation"],
            ),
            ("holdout_selection_purpose", "challenge_evaluation"),
            ("holdout_release_rule", "immediate"),
            ("quality_gate", {"precision": 0.9}),
        )
        for field, value in changes:
            with self.subTest(field=field):
                payload = valid_payload()
                payload["scoring_grid"][field] = value
                with self.assertRaises(DetectorExperimentValidationError):
                    DetectorExperiment.from_mapping(payload)

    def test_build_model_provenance_uses_clean_commit_and_runtime_device(self):
        experiment = DetectorExperiment.from_mapping(valid_payload())
        provenance = build_model_provenance(
            experiment.detector,
            code_commit="a" * 40,
            runtime_device="cuda:0 | NVIDIA GeForce RTX 5070",
        )
        self.assertEqual(provenance.code_commit, "a" * 40)
        self.assertEqual(
            provenance.device,
            "cuda:0 | NVIDIA GeForce RTX 5070",
        )
        self.assertEqual(provenance.precision, "float32")
        self.assertEqual(provenance.input_width_px, 576)
        self.assertEqual(provenance.input_height_px, 576)
        self.assertEqual(provenance.target_class_id, 37)
        self.assertEqual(provenance.target_class_name, "sports ball")
        self.assertEqual(provenance.export_confidence_floor, 0.01)

        invalid_inputs = (
            ("A" * 40, "cuda:0"),
            ("a" * 40, "cpu"),
            ("a" * 40, ""),
            ("a" * 40, "cuda_fake"),
            ("a" * 40, "cuda:-1"),
            ("a" * 40, "cuda:01"),
            ("a" * 40, "cuda:0 NVIDIA GeForce RTX 5070"),
            ("a" * 40, "cuda:0 |  leading-space"),
            ("a" * 40, "cuda:0 | bad\tdescription"),
        )
        for commit, device in invalid_inputs:
            with self.subTest(commit=commit[:1], device=device):
                with self.assertRaises(DetectorExperimentValidationError):
                    build_model_provenance(
                        experiment.detector,
                        code_commit=commit,
                        runtime_device=device,
                    )

        for device in (
            "cuda",
            "cuda:0",
            "cuda:12 | GPU=NVIDIA; torch=2.10.0; cuda=13.0",
        ):
            with self.subTest(valid_device=device):
                self.assertEqual(
                    build_model_provenance(
                        experiment.detector,
                        code_commit="b" * 40,
                        runtime_device=device,
                    ).device,
                    device,
                )


if __name__ == "__main__":
    unittest.main()
