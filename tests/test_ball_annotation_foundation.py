import copy
import hashlib
import json
import math
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from src.ball_tracking.annotations import (
    AnnotationValidationError,
    BallAnnotationSet,
    load_annotations,
    verify_source_video,
)
from src.ball_tracking.detections import (
    BallDetectionRun,
    DetectionRunValidationError,
    load_detection_run,
)
from src.ball_tracking.evaluation import (
    DetectionEvaluationError,
    aggregate_evaluation_reports,
    evaluate_detections,
)


SOURCE_SHA256 = "a" * 64
REPO_ROOT = Path(__file__).resolve().parents[1]


def canonical_sha256(value):
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def observed_frame(
    frame_index,
    *,
    center=(100.0, 100.0),
    uncertainty=1.0,
    certainty="certain",
    eligible=True,
    notes=None,
):
    return {
        "frame_index": frame_index,
        "annotation_status": "labeled",
        "visibility": "fully_visible",
        "absence_reason": None,
        "geometry": {
            "center_xy_px": list(center),
            "source": "observed_complete_ball_center",
            "uncertainty_radius_px": uncertainty,
        },
        "game_ball_identity_certainty": certainty,
        "localization_eligible": eligible,
        "difficulty_tags": [],
        "notes": notes,
    }


def partial_frame(
    frame_index,
    *,
    center=(100.0, 100.0),
    uncertainty=4.0,
    with_geometry=True,
    certainty="certain",
    eligible=True,
):
    geometry = None
    notes = "human-estimated complete-ball center"

    if with_geometry:
        geometry = {
            "center_xy_px": list(center),
            "source": "human_amodal_estimate",
            "uncertainty_radius_px": uncertainty,
        }
    else:
        eligible = False
        notes = "complete-ball center is not defensible"

    return {
        "frame_index": frame_index,
        "annotation_status": "labeled",
        "visibility": "partially_visible",
        "absence_reason": None,
        "geometry": geometry,
        "game_ball_identity_certainty": certainty,
        "localization_eligible": eligible,
        "difficulty_tags": ["player_overlap"],
        "notes": notes,
    }


def not_visible_frame(
    frame_index,
    reason="occluded",
    *,
    certainty="certain",
):
    return {
        "frame_index": frame_index,
        "annotation_status": "labeled",
        "visibility": "not_visible",
        "absence_reason": reason,
        "geometry": None,
        "game_ball_identity_certainty": certainty,
        "localization_eligible": False,
        "difficulty_tags": [],
        "notes": "ball is not visible",
    }


def indeterminate_frame(frame_index):
    return {
        "frame_index": frame_index,
        "annotation_status": "labeled",
        "visibility": "indeterminate",
        "absence_reason": None,
        "geometry": None,
        "game_ball_identity_certainty": "ambiguous",
        "localization_eligible": False,
        "difficulty_tags": [],
        "notes": "visibility cannot be resolved",
    }


def unlabeled_frame(frame_index):
    return {
        "frame_index": frame_index,
        "annotation_status": "unlabeled",
        "visibility": None,
        "absence_reason": None,
        "geometry": None,
        "game_ball_identity_certainty": None,
        "localization_eligible": False,
        "difficulty_tags": [],
        "notes": None,
    }


def excluded_frame(frame_index):
    return {
        "frame_index": frame_index,
        "annotation_status": "excluded",
        "visibility": None,
        "absence_reason": None,
        "geometry": None,
        "game_ball_identity_certainty": None,
        "localization_eligible": False,
        "difficulty_tags": [],
        "notes": "broadcast cut excluded from evaluation",
    }


def ambiguous_visible_frame(frame_index):
    frame = observed_frame(
        frame_index,
        certainty="ambiguous",
        eligible=False,
        notes="game-ball identity is ambiguous",
    )
    return frame


def annotation_payload(
    annotations,
    *,
    annotation_set_id="possession_001_ball_pilot",
    possession_id="possession_001",
    start_frame_index=None,
    end_frame_index=None,
    frame_count=500,
    source_sha256=SOURCE_SHA256,
    source_path=None,
    width_px=1920,
    height_px=1080,
    fps=25.0,
):
    if start_frame_index is None:
        start_frame_index = annotations[0]["frame_index"]

    if end_frame_index is None:
        end_frame_index = annotations[-1]["frame_index"]

    return {
        "schema_version": "0.1",
        "annotation_set_id": annotation_set_id,
        "possession_id": possession_id,
        "source_video": {
            "path": (
                source_path
                if source_path is not None
                else f"data/clips/{possession_id}.mp4"
            ),
            "sha256": source_sha256,
            "width_px": width_px,
            "height_px": height_px,
            "fps": fps,
            "frame_count": frame_count,
        },
        "window": {
            "start_frame_index": start_frame_index,
            "end_frame_index": end_frame_index,
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
            "status": "draft",
            "annotator_id": "synthetic_test",
            "reviewer_id": None,
            "created_at_utc": "2026-08-23T12:00:00Z",
            "reviewed_at_utc": None,
        },
        "annotations": annotations,
    }


def parse_annotations(annotations, **kwargs):
    return BallAnnotationSet.from_mapping(
        annotation_payload(annotations, **kwargs)
    )


def parse_reviewed_annotations(annotations, **kwargs):
    payload = annotation_payload(annotations, **kwargs)
    payload["review"].update(
        {
            "status": "reviewed",
            "reviewer_id": "synthetic_reviewer",
            "reviewed_at_utc": "2026-08-23T13:00:00Z",
        }
    )
    return BallAnnotationSet.from_mapping(payload)


def detection(x, y, confidence=0.9, *, half_size=1.0):
    return {
        "candidate_index": 0,
        "class_id": 32,
        "class_name": "sports_ball",
        "bbox_xyxy_px": [
            x - half_size,
            y - half_size,
            x + half_size,
            y + half_size,
        ],
        "center_xy_px": [x, y],
        "confidence": confidence,
    }


def detection_run_payload(
    annotation_set,
    detections_by_frame=None,
    *,
    detection_run_id=None,
    model_overrides=None,
):
    if detections_by_frame is None:
        detections_by_frame = {}

    provenance = {
        "model_name": "synthetic_ball_detector",
        "package_name": "synthetic-package",
        "package_version": "1.0.0",
        "weights_identifier": "synthetic-weights",
        "weights_sha256": "b" * 64,
        "code_commit": "c" * 40,
        "device": "cpu",
        "precision": "fp32",
        "input_width_px": 1920,
        "input_height_px": 1080,
        "resize_mode": "source_resolution",
        "tiling_enabled": False,
        "target_class_id": 32,
        "target_class_name": "sports_ball",
        "export_confidence_floor": 0.0,
        "postprocessing_description": "synthetic raw detector output",
    }

    if model_overrides is not None:
        provenance.update(model_overrides)

    frames = []

    for frame_index in range(
        annotation_set.window.start_frame_index,
        annotation_set.window.end_frame_index + 1,
    ):
        raw_detections = copy.deepcopy(
            detections_by_frame.get(frame_index, [])
        )

        for candidate_index, candidate in enumerate(raw_detections):
            candidate["candidate_index"] = candidate_index

        frames.append(
            {
                "frame_index": frame_index,
                "inference_status": "completed",
                "failure_reason": None,
                "detections": raw_detections,
            }
        )

    return {
        "schema_version": "0.1",
        "detection_run_id": (
            detection_run_id
            if detection_run_id is not None
            else f"{annotation_set.annotation_set_id}_synthetic_run"
        ),
        "annotation_set_id": annotation_set.annotation_set_id,
        "possession_id": annotation_set.possession_id,
        "source_video": annotation_set.source_video.to_dict(),
        "window": {
            "start_frame_index": (
                annotation_set.window.start_frame_index
            ),
            "end_frame_index": annotation_set.window.end_frame_index,
        },
        "model_provenance": provenance,
        "frames": frames,
    }


def parse_detection_run(annotation_set, detections_by_frame=None, **kwargs):
    return BallDetectionRun.from_mapping(
        detection_run_payload(
            annotation_set,
            detections_by_frame,
            **kwargs,
        )
    )


def evaluate_predictions(
    annotation_set,
    detections_by_frame,
    *,
    confidence_threshold=0.5,
    localization_radius_px=5.0,
    detection_run_id=None,
    model_overrides=None,
):
    detection_run = parse_detection_run(
        annotation_set,
        detections_by_frame,
        detection_run_id=detection_run_id,
        model_overrides=model_overrides,
    )
    return evaluate_detections(
        annotation_set,
        detection_run,
        confidence_threshold=confidence_threshold,
        localization_radius_px=localization_radius_px,
    )


class BallAnnotationValidationTests(unittest.TestCase):
    def test_zero_based_inclusive_window_requires_exact_coverage(self):
        zero_based = parse_annotations(
            [observed_frame(0)],
            frame_count=1,
        )
        self.assertEqual(zero_based.window.start_frame_index, 0)

        records = [observed_frame(index) for index in range(375, 400)]
        annotation_set = parse_annotations(
            records,
            start_frame_index=375,
            end_frame_index=399,
        )
        self.assertEqual(len(annotation_set.annotations), 25)

        invalid_payloads = []

        missing = annotation_payload(copy.deepcopy(records))
        missing["annotations"].pop(5)
        invalid_payloads.append(missing)

        duplicate = annotation_payload(copy.deepcopy(records))
        duplicate["annotations"][5]["frame_index"] = 379
        invalid_payloads.append(duplicate)

        out_of_order = annotation_payload(copy.deepcopy(records))
        out_of_order["annotations"][5], out_of_order["annotations"][6] = (
            out_of_order["annotations"][6],
            out_of_order["annotations"][5],
        )
        invalid_payloads.append(out_of_order)

        outside = annotation_payload(copy.deepcopy(records))
        outside["annotations"][-1]["frame_index"] = 400
        invalid_payloads.append(outside)

        negative_start = annotation_payload(copy.deepcopy(records))
        negative_start["window"]["start_frame_index"] = -1
        invalid_payloads.append(negative_start)

        end_at_frame_count = annotation_payload(copy.deepcopy(records))
        end_at_frame_count["window"]["end_frame_index"] = 500
        invalid_payloads.append(end_at_frame_count)

        boolean_index = annotation_payload([observed_frame(True)])
        invalid_payloads.append(boolean_index)

        for payload in invalid_payloads:
            with self.subTest(payload=payload["window"]):
                with self.assertRaises(AnnotationValidationError):
                    BallAnnotationSet.from_mapping(payload)

    def test_coordinate_contract_is_fixed_to_original_complete_center(self):
        valid = annotation_payload([observed_frame(0)])

        for field, value in (
            ("frame_index_origin", 1),
            ("frame_index_origin", 0.0),
            ("pixel_origin", "bottom_left"),
            ("x_axis_direction", "left"),
            ("y_axis_direction", "up"),
            ("center_definition", "visible_fragment_centroid"),
            ("timestamp_rule", "one_based_frame_divided_by_fps"),
        ):
            payload = copy.deepcopy(valid)
            payload["coordinate_system"][field] = value

            with self.subTest(field=field):
                with self.assertRaises(AnnotationValidationError):
                    BallAnnotationSet.from_mapping(payload)

    def test_schema_version_and_unknown_fields_are_rejected(self):
        wrong_version = annotation_payload([observed_frame(0)])
        wrong_version["schema_version"] = "0.2"

        unknown_top_level = annotation_payload([observed_frame(0)])
        unknown_top_level["silent_default"] = True

        unknown_frame_field = annotation_payload([observed_frame(0)])
        unknown_frame_field["annotations"][0]["visible_center"] = [1, 2]

        for payload in (
            wrong_version,
            unknown_top_level,
            unknown_frame_field,
        ):
            with self.subTest(keys=sorted(payload)):
                with self.assertRaises(AnnotationValidationError):
                    BallAnnotationSet.from_mapping(payload)

    def test_loader_rejects_duplicate_json_object_keys(self):
        duplicate_json = (
            '{"schema_version":"0.1",'
            '"schema_version":"0.1"}'
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "duplicate_keys.json"
            path.write_text(duplicate_json, encoding="utf-8")

            with self.assertRaisesRegex(
                AnnotationValidationError,
                "Duplicate JSON object key",
            ):
                load_annotations(path)

    def test_source_hash_path_and_numeric_metadata_are_strict(self):
        valid = annotation_payload([observed_frame(0)])
        invalid_values = (
            ("sha256", "a" * 63),
            ("sha256", "g" * 64),
            ("sha256", "A" * 64),
            ("path", "../outside.mp4"),
            ("path", "C:/outside.mp4"),
            ("width_px", 0),
            ("width_px", True),
            ("height_px", -1),
            ("frame_count", 0),
            ("frame_count", True),
            ("fps", 0.0),
            ("fps", True),
            ("fps", math.nan),
            ("fps", math.inf),
        )

        for field, value in invalid_values:
            payload = copy.deepcopy(valid)
            payload["source_video"][field] = value

            with self.subTest(field=field, value=value):
                with self.assertRaises(AnnotationValidationError):
                    BallAnnotationSet.from_mapping(payload)

    def test_window_purpose_and_review_provenance_are_strict(self):
        allowed_purposes = (
            "challenge_evaluation",
            "protocol_adjudication",
            "representative_evaluation",
            "test_holdout",
            "training",
            "validation_calibration",
        )

        for purpose in allowed_purposes:
            payload = annotation_payload([observed_frame(0)])
            payload["window"]["selection_purpose"] = purpose

            with self.subTest(purpose=purpose):
                BallAnnotationSet.from_mapping(payload)

        invalid_purpose = annotation_payload([observed_frame(0)])
        invalid_purpose["window"]["selection_purpose"] = "convenient_clip"

        with self.assertRaises(AnnotationValidationError):
            BallAnnotationSet.from_mapping(invalid_purpose)

        reviewed_too_early = annotation_payload([observed_frame(0)])
        reviewed_too_early["review"].update(
            {
                "status": "reviewed",
                "reviewer_id": "reviewer",
                "reviewed_at_utc": "2026-08-23T11:59:59Z",
            }
        )

        with self.assertRaises(AnnotationValidationError):
            BallAnnotationSet.from_mapping(reviewed_too_early)

        draft_with_reviewer = annotation_payload([observed_frame(0)])
        draft_with_reviewer["review"]["reviewer_id"] = "reviewer"

        with self.assertRaises(AnnotationValidationError):
            BallAnnotationSet.from_mapping(draft_with_reviewer)

    def test_complete_set_allows_honest_self_review(self):
        payload = annotation_payload([observed_frame(0)])
        annotator_id = payload["review"]["annotator_id"]
        payload["review"].update(
            {
                "status": "reviewed",
                "reviewer_id": annotator_id,
                "reviewed_at_utc": "2026-08-23T13:00:00Z",
            }
        )

        annotation_set = BallAnnotationSet.from_mapping(payload)

        self.assertEqual(annotation_set.review.status, "reviewed")
        self.assertEqual(annotation_set.review.reviewer_id, annotator_id)

    def test_visible_geometry_source_and_uncertainty_rules(self):
        parse_annotations([observed_frame(0)])
        parse_annotations([partial_frame(0)])
        parse_annotations(
            [
                observed_frame(
                    0,
                    eligible=False,
                    notes="complete center is not defensible",
                )
            ]
        )

        no_geometry = observed_frame(
            0,
            eligible=False,
            notes="complete center is not defensible",
        )
        no_geometry["geometry"] = None
        parse_annotations([no_geometry])
        parse_annotations([partial_frame(0, with_geometry=False)])

        invalid_frames = []
        wrong_full_source = observed_frame(0)
        wrong_full_source["geometry"]["source"] = "human_amodal_estimate"
        invalid_frames.append(wrong_full_source)

        wrong_partial_source = partial_frame(0)
        wrong_partial_source["geometry"][
            "source"
        ] = "observed_complete_ball_center"
        invalid_frames.append(wrong_partial_source)

        for uncertainty in (
            0.0,
            -1.0,
            math.nan,
            math.inf,
            True,
            math.hypot(1920, 1080) + 0.001,
        ):
            invalid_frames.append(
                observed_frame(0, uncertainty=uncertainty)
            )
            invalid_frames.append(
                partial_frame(0, uncertainty=uncertainty)
            )

        no_geometry_but_eligible = partial_frame(0, with_geometry=False)
        no_geometry_but_eligible["localization_eligible"] = True
        invalid_frames.append(no_geometry_but_eligible)

        no_reason = partial_frame(0, with_geometry=False)
        no_reason["notes"] = ""
        invalid_frames.append(no_reason)

        for frame in invalid_frames:
            with self.subTest(frame=frame):
                with self.assertRaises(AnnotationValidationError):
                    parse_annotations([frame])

    def test_nonvisible_and_indeterminate_forbid_geometry(self):
        for reason in ("occluded", "out_of_frame", "unknown"):
            with self.subTest(reason=reason):
                parse_annotations([not_visible_frame(0, reason)])

        parse_annotations([indeterminate_frame(0)])

        invalid_frames = []
        no_absence = not_visible_frame(0)
        no_absence["absence_reason"] = None
        invalid_frames.append(no_absence)

        geometry = not_visible_frame(0)
        geometry["geometry"] = observed_frame(0)["geometry"]
        invalid_frames.append(geometry)

        absence_while_visible = observed_frame(0)
        absence_while_visible["absence_reason"] = "occluded"
        invalid_frames.append(absence_while_visible)

        known_indeterminate = indeterminate_frame(0)
        known_indeterminate["game_ball_identity_certainty"] = "certain"
        invalid_frames.append(known_indeterminate)

        eligible_indeterminate = indeterminate_frame(0)
        eligible_indeterminate["localization_eligible"] = True
        invalid_frames.append(eligible_indeterminate)

        unexplained_indeterminate = indeterminate_frame(0)
        unexplained_indeterminate["notes"] = None
        invalid_frames.append(unexplained_indeterminate)

        for frame in invalid_frames:
            with self.subTest(frame=frame):
                with self.assertRaises(AnnotationValidationError):
                    parse_annotations([frame])

    def test_unlabeled_and_excluded_clear_semantics(self):
        parse_annotations([unlabeled_frame(0)])
        parse_annotations([excluded_frame(0)])

        invalid_frames = []

        leaked = unlabeled_frame(0)
        leaked["visibility"] = "indeterminate"
        invalid_frames.append(leaked)

        tagged = excluded_frame(0)
        tagged["difficulty_tags"] = ["motion_blur"]
        invalid_frames.append(tagged)

        blank_reason = excluded_frame(0)
        blank_reason["notes"] = "  "
        invalid_frames.append(blank_reason)

        eligible = unlabeled_frame(0)
        eligible["localization_eligible"] = True
        invalid_frames.append(eligible)

        for frame in invalid_frames:
            with self.subTest(frame=frame):
                with self.assertRaises(AnnotationValidationError):
                    parse_annotations([frame])

        reviewed = annotation_payload([unlabeled_frame(0)])
        reviewed["review"].update(
            {
                "status": "reviewed",
                "reviewer_id": "reviewer",
                "reviewed_at_utc": "2026-08-23T13:00:00Z",
            }
        )

        with self.assertRaises(AnnotationValidationError):
            BallAnnotationSet.from_mapping(reviewed)

    def test_identity_certainty_controls_localization_eligibility(self):
        parse_annotations([ambiguous_visible_frame(0)])

        for certainty in ("certain", "probable"):
            with self.subTest(certainty=certainty):
                parse_annotations(
                    [observed_frame(0, certainty=certainty)]
                )

        invalid = ambiguous_visible_frame(0)
        invalid["localization_eligible"] = True

        with self.assertRaises(AnnotationValidationError):
            parse_annotations([invalid])

        unexplained = observed_frame(0, eligible=False)

        with self.assertRaises(AnnotationValidationError):
            parse_annotations([unexplained])

        missing_certainty = observed_frame(0)
        missing_certainty["game_ball_identity_certainty"] = None

        with self.assertRaises(AnnotationValidationError):
            parse_annotations([missing_certainty])

        unexplained_ambiguous = ambiguous_visible_frame(0)
        unexplained_ambiguous["notes"] = None

        with self.assertRaises(AnnotationValidationError):
            parse_annotations([unexplained_ambiguous])

    def test_centers_are_finite_and_inside_source_bounds(self):
        invalid_centers = (
            (-0.01, 100.0),
            (1920.0, 100.0),
            (100.0, -0.01),
            (100.0, 1080.0),
            (math.nan, 100.0),
            (math.inf, 100.0),
            (True, 100.0),
        )

        for center in invalid_centers:
            with self.subTest(center=center):
                with self.assertRaises(AnnotationValidationError):
                    parse_annotations([observed_frame(0, center=center)])

    def test_difficulty_tags_are_allowed_sorted_and_unique(self):
        valid = observed_frame(0)
        valid["difficulty_tags"] = ["motion_blur", "tiny_apparent_size"]
        parse_annotations([valid])

        invalid_tags = (
            ["tiny_apparent_size", "motion_blur"],
            ["motion_blur", "motion_blur"],
            ["unknown_tag"],
        )

        for tags in invalid_tags:
            frame = observed_frame(0)
            frame["difficulty_tags"] = tags

            with self.subTest(tags=tags):
                with self.assertRaises(AnnotationValidationError):
                    parse_annotations([frame])


class BallDetectionRunValidationTests(unittest.TestCase):
    def test_completed_run_preserves_provenance_and_empty_frames(self):
        annotation_set = parse_reviewed_annotations(
            [observed_frame(10), observed_frame(11)]
        )
        detection_run = parse_detection_run(
            annotation_set,
            {10: [detection(100, 100)], 11: []},
        )

        self.assertEqual(
            detection_run.annotation_set_id,
            annotation_set.annotation_set_id,
        )
        self.assertEqual(len(detection_run.frames), 2)
        self.assertEqual(detection_run.frames[0].inference_status, "completed")
        self.assertEqual(len(detection_run.frames[0].detections), 1)
        self.assertEqual(detection_run.frames[1].detections, ())
        self.assertEqual(
            detection_run.model_provenance.weights_sha256,
            "b" * 64,
        )

    def test_run_requires_exact_sorted_frame_coverage(self):
        annotation_set = parse_reviewed_annotations(
            [observed_frame(index) for index in range(10, 13)]
        )
        valid = detection_run_payload(annotation_set)
        BallDetectionRun.from_mapping(valid)

        missing = copy.deepcopy(valid)
        missing["frames"].pop()

        duplicate = copy.deepcopy(valid)
        duplicate["frames"][1]["frame_index"] = 10

        out_of_order = copy.deepcopy(valid)
        out_of_order["frames"][0], out_of_order["frames"][1] = (
            out_of_order["frames"][1],
            out_of_order["frames"][0],
        )

        for payload in (missing, duplicate, out_of_order):
            with self.subTest(frames=payload["frames"]):
                with self.assertRaises(DetectionRunValidationError):
                    BallDetectionRun.from_mapping(payload)

    def test_frame_status_distinguishes_empty_output_from_failure(self):
        annotation_set = parse_reviewed_annotations([observed_frame(0)])
        completed_empty = detection_run_payload(annotation_set)
        BallDetectionRun.from_mapping(completed_empty)

        failed = copy.deepcopy(completed_empty)
        failed["frames"][0].update(
            {
                "inference_status": "inference_failed",
                "failure_reason": "synthetic failure",
                "detections": None,
            }
        )
        parsed_failed = BallDetectionRun.from_mapping(failed)
        self.assertIsNone(parsed_failed.frames[0].detections)

        completed_without_array = copy.deepcopy(completed_empty)
        completed_without_array["frames"][0]["detections"] = None

        failed_with_array = copy.deepcopy(failed)
        failed_with_array["frames"][0]["detections"] = []

        failed_without_reason = copy.deepcopy(failed)
        failed_without_reason["frames"][0]["failure_reason"] = None

        for payload in (
            completed_without_array,
            failed_with_array,
            failed_without_reason,
        ):
            with self.subTest(frame=payload["frames"][0]):
                with self.assertRaises(DetectionRunValidationError):
                    BallDetectionRun.from_mapping(payload)

    def test_detection_geometry_class_order_and_floor_are_strict(self):
        annotation_set = parse_reviewed_annotations([observed_frame(0)])
        valid = detection_run_payload(
            annotation_set,
            {0: [detection(100, 100, 0.9)]},
            model_overrides={"export_confidence_floor": 0.5},
        )
        BallDetectionRun.from_mapping(valid)

        def changed(field, value):
            payload = copy.deepcopy(valid)
            payload["frames"][0]["detections"][0][field] = value
            return payload

        invalid_payloads = (
            changed("candidate_index", 1),
            changed("class_id", 31),
            changed("class_name", "person"),
            changed("confidence", 0.49),
            changed("bbox_xyxy_px", [101, 99, 99, 101]),
            changed("center_xy_px", [101, 100]),
        )

        unknown = copy.deepcopy(valid)
        unknown["frames"][0]["detections"][0]["tracker_hint"] = 7

        for payload in (*invalid_payloads, unknown):
            with self.subTest(detection=payload["frames"][0]["detections"]):
                with self.assertRaises(DetectionRunValidationError):
                    BallDetectionRun.from_mapping(payload)

    def test_model_provenance_and_loader_are_strict(self):
        annotation_set = parse_reviewed_annotations([observed_frame(0)])
        valid = detection_run_payload(annotation_set)
        invalid_values = (
            ("weights_sha256", "b" * 63),
            ("code_commit", "c" * 39),
            ("input_width_px", 0),
            ("tiling_enabled", 0),
            ("export_confidence_floor", 1.1),
        )

        for field, value in invalid_values:
            payload = copy.deepcopy(valid)
            payload["model_provenance"][field] = value

            with self.subTest(field=field):
                with self.assertRaises(DetectionRunValidationError):
                    BallDetectionRun.from_mapping(payload)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "duplicate_run.json"
            path.write_text(
                '{"schema_version":"0.1",'
                '"schema_version":"0.1"}',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                DetectionRunValidationError,
                "Duplicate JSON object key",
            ):
                load_detection_run(path)


class BallDetectionEvaluationTests(unittest.TestCase):
    def test_incomplete_run_binding_and_export_floor_are_guarded(self):
        annotation_set = parse_reviewed_annotations([observed_frame(0)])
        valid_payload = detection_run_payload(annotation_set)

        incomplete_payload = copy.deepcopy(valid_payload)
        incomplete_payload["frames"][0].update(
            {
                "inference_status": "not_run",
                "failure_reason": "not executed",
                "detections": None,
            }
        )
        incomplete_run = BallDetectionRun.from_mapping(incomplete_payload)

        with self.assertRaises(DetectionEvaluationError):
            evaluate_detections(
                annotation_set,
                incomplete_run,
                confidence_threshold=0.5,
                localization_radius_px=5.0,
            )

        mismatched_payloads = []

        wrong_annotation = copy.deepcopy(valid_payload)
        wrong_annotation["annotation_set_id"] = "different_annotations"
        mismatched_payloads.append(wrong_annotation)

        wrong_possession = copy.deepcopy(valid_payload)
        wrong_possession["possession_id"] = "possession_002"
        mismatched_payloads.append(wrong_possession)

        wrong_source = copy.deepcopy(valid_payload)
        wrong_source["source_video"]["sha256"] = "d" * 64
        mismatched_payloads.append(wrong_source)

        wrong_window = copy.deepcopy(valid_payload)
        wrong_window["window"] = {
            "start_frame_index": 1,
            "end_frame_index": 1,
        }
        wrong_window["frames"][0]["frame_index"] = 1
        mismatched_payloads.append(wrong_window)

        for payload in mismatched_payloads:
            detection_run = BallDetectionRun.from_mapping(payload)

            with self.subTest(run=payload["detection_run_id"]):
                with self.assertRaises(DetectionEvaluationError):
                    evaluate_detections(
                        annotation_set,
                        detection_run,
                        confidence_threshold=0.5,
                        localization_radius_px=5.0,
                    )

        floored_run = parse_detection_run(
            annotation_set,
            model_overrides={"export_confidence_floor": 0.5},
        )

        with self.assertRaises(DetectionEvaluationError):
            evaluate_detections(
                annotation_set,
                floored_run,
                confidence_threshold=0.499,
                localization_radius_px=5.0,
            )

    def test_localization_radius_is_inclusive(self):
        annotation_set = parse_reviewed_annotations(
            [observed_frame(0, center=(10.0, 10.0), uncertainty=1.0)]
        )
        predictions = {0: [detection(13.0, 14.0)]}

        matched = evaluate_predictions(
            annotation_set,
            predictions,
            confidence_threshold=0.5,
            localization_radius_px=5.0,
        )
        missed = evaluate_predictions(
            annotation_set,
            predictions,
            confidence_threshold=0.5,
            localization_radius_px=4.999,
        )

        self.assertEqual(matched["true_positive_count"], 1)
        self.assertEqual(matched["false_positive_count"], 0)
        self.assertEqual(matched["false_negative_count"], 0)
        self.assertEqual(missed["true_positive_count"], 0)
        self.assertEqual(missed["false_positive_count"], 1)
        self.assertEqual(missed["false_negative_count"], 1)

    def test_amodal_uncertainty_is_diagnostic_not_matching_tolerance(self):
        annotation_set = parse_reviewed_annotations(
            [
                partial_frame(
                    0,
                    center=(100.0, 100.0),
                    uncertainty=4.0,
                )
            ]
        )
        predictions = {0: [detection(107.0, 100.0)]}

        missed = evaluate_predictions(
            annotation_set,
            predictions,
            confidence_threshold=0.5,
            localization_radius_px=3.0,
        )

        self.assertEqual(missed["true_positive_count"], 0)
        self.assertEqual(missed["false_positive_count"], 1)
        self.assertEqual(missed["false_negative_count"], 1)

        matched = evaluate_predictions(
            annotation_set,
            predictions,
            confidence_threshold=0.5,
            localization_radius_px=7.0,
        )
        self.assertEqual(matched["true_positive_count"], 1)
        self.assertAlmostEqual(
            matched["matched_center_error_px"]["mean"],
            7.0,
        )
        self.assertAlmostEqual(
            matched["matched_effective_center_error_px"]["mean"],
            3.0,
        )

    def test_duplicate_and_unmatched_predictions_remain_false_positives(self):
        annotation_set = parse_reviewed_annotations(
            [observed_frame(0, uncertainty=1.0)]
        )
        predictions = {
            0: [
                detection(103.0, 104.0, 0.9),
                detection(100.0, 101.0, 0.8),
                detection(120.0, 100.0, 0.7),
            ]
        }

        report = evaluate_predictions(
            annotation_set,
            predictions,
            confidence_threshold=0.5,
            localization_radius_px=5.0,
        )

        self.assertEqual(report["true_positive_count"], 1)
        self.assertEqual(report["false_positive_count"], 2)
        self.assertEqual(report["false_negative_count"], 0)
        self.assertEqual(report["duplicate_false_positive_count"], 1)
        self.assertAlmostEqual(report["precision"], 1.0 / 3.0)
        self.assertEqual(report["recall"], 1.0)
        self.assertAlmostEqual(
            report["matched_center_error_px"]["mean"],
            5.0,
        )
        self.assertAlmostEqual(
            report["matched_effective_center_error_px"]["mean"],
            4.0,
        )

    def test_out_of_radius_prediction_is_fp_and_visible_truth_is_fn(self):
        annotation_set = parse_reviewed_annotations(
            [observed_frame(0, center=(100.0, 100.0), uncertainty=1.0)]
        )
        report = evaluate_predictions(
            annotation_set,
            {0: [detection(111.0, 100.0)]},
            confidence_threshold=0.5,
            localization_radius_px=5.0,
        )

        self.assertEqual(report["true_positive_count"], 0)
        self.assertEqual(report["false_positive_count"], 1)
        self.assertEqual(report["false_negative_count"], 1)
        self.assertEqual(report["matched_center_error_px"]["count"], 0)
        self.assertIsNone(report["matched_center_error_px"]["mean"])

    def test_nonvisible_predictions_are_false_alarms(self):
        annotation_set = parse_reviewed_annotations(
            [
                not_visible_frame(0, "occluded"),
                not_visible_frame(1, "out_of_frame"),
            ]
        )
        report = evaluate_predictions(
            annotation_set,
            {
                0: [detection(100, 100), detection(200, 200)],
                1: [detection(300, 300)],
            },
            confidence_threshold=0.5,
            localization_radius_px=5.0,
        )

        self.assertEqual(report["not_visible_frame_count"], 2)
        self.assertEqual(report["false_positive_count"], 3)
        self.assertEqual(report["false_negative_count"], 0)
        self.assertEqual(report["non_visible_false_alarm_count"], 3)
        self.assertEqual(
            report["non_visible_false_alarm_frame_count"],
            2,
        )

    def test_uncertain_and_uncovered_frames_are_unscored(self):
        annotation_set = parse_reviewed_annotations(
            [
                excluded_frame(0),
                indeterminate_frame(1),
                partial_frame(2, with_geometry=False),
                ambiguous_visible_frame(3),
                not_visible_frame(4, certainty="ambiguous"),
            ]
        )
        predictions = {
            frame_index: [detection(100, 100)]
            for frame_index in range(5)
        }
        report = evaluate_predictions(
            annotation_set,
            predictions,
            confidence_threshold=0.5,
            localization_radius_px=5.0,
        )

        self.assertEqual(report["unscored_frame_count"], 5)
        self.assertEqual(report["unscored_prediction_count"], 5)
        self.assertEqual(report["not_visible_frame_count"], 0)
        self.assertEqual(report["true_positive_count"], 0)
        self.assertEqual(report["false_positive_count"], 0)
        self.assertEqual(report["false_negative_count"], 0)
        self.assertIsNone(report["precision"])
        self.assertIsNone(report["recall"])

    def test_draft_annotation_set_cannot_be_evaluated(self):
        annotation_set = parse_annotations([observed_frame(0)])
        detection_run = parse_detection_run(
            annotation_set,
            {0: [detection(100, 100)]},
        )

        with self.assertRaises(DetectionEvaluationError):
            evaluate_detections(
                annotation_set,
                detection_run,
                confidence_threshold=0.5,
                localization_radius_px=5.0,
            )

    def test_confidence_threshold_is_inclusive(self):
        annotation_set = parse_reviewed_annotations([observed_frame(0)])
        report = evaluate_predictions(
            annotation_set,
            {
                0: [
                    detection(100, 100, 0.5),
                    detection(500, 500, 0.499),
                ]
            },
            confidence_threshold=0.5,
            localization_radius_px=5.0,
        )

        self.assertEqual(report["true_positive_count"], 1)
        self.assertEqual(report["false_positive_count"], 0)
        self.assertEqual(report["below_threshold_detection_count"], 1)

    def test_detection_run_content_digest_binds_candidate_predictions(self):
        annotation_set = parse_reviewed_annotations([observed_frame(0)])
        first_run = parse_detection_run(
            annotation_set,
            {0: [detection(100, 100)]},
            detection_run_id="stable_run_id",
        )
        changed_run = parse_detection_run(
            annotation_set,
            {0: [detection(101, 100)]},
            detection_run_id="stable_run_id",
        )
        first_report = evaluate_detections(
            annotation_set,
            first_run,
            confidence_threshold=0.5,
            localization_radius_px=5.0,
        )
        changed_report = evaluate_detections(
            annotation_set,
            changed_run,
            confidence_threshold=0.5,
            localization_radius_px=5.0,
        )

        self.assertEqual(
            first_report["detection_run_content_sha256"],
            canonical_sha256(first_run.to_dict()),
        )
        self.assertEqual(
            changed_report["detection_run_content_sha256"],
            canonical_sha256(changed_run.to_dict()),
        )
        self.assertEqual(
            first_report["detection_run_id"],
            changed_report["detection_run_id"],
        )
        self.assertEqual(
            first_report["model_run_signature"],
            changed_report["model_run_signature"],
        )
        self.assertNotEqual(
            first_report["detection_run_content_sha256"],
            changed_report["detection_run_content_sha256"],
        )

    def test_invalid_evaluation_settings_are_rejected(self):
        annotation_set = parse_reviewed_annotations([observed_frame(0)])
        detection_run = parse_detection_run(annotation_set)

        for threshold, radius in (
            (math.nan, 5.0),
            (1.1, 5.0),
            (0.5, -1.0),
            (0.5, math.inf),
        ):
            with self.subTest(threshold=threshold, radius=radius):
                with self.assertRaises(DetectionEvaluationError):
                    evaluate_detections(
                        annotation_set,
                        detection_run,
                        confidence_threshold=threshold,
                        localization_radius_px=radius,
                    )

    def test_macro_aggregation_groups_reports_by_possession(self):
        reports = []

        for frame_index, suffix in ((0, "a"), (1, "b")):
            annotation_set = parse_reviewed_annotations(
                [observed_frame(frame_index)],
                annotation_set_id=f"possession_001_{suffix}",
                possession_id="possession_001",
            )
            reports.append(
                evaluate_predictions(
                    annotation_set,
                    {frame_index: [detection(100, 100)]},
                    confidence_threshold=0.5,
                    localization_radius_px=5.0,
                )
            )

        possession_002 = parse_reviewed_annotations(
            [observed_frame(0), not_visible_frame(1)],
            annotation_set_id="possession_002_a",
            possession_id="possession_002",
            source_sha256="d" * 64,
        )
        reports.append(
            evaluate_predictions(
                possession_002,
                {0: [], 1: [detection(100, 100)]},
                confidence_threshold=0.5,
                localization_radius_px=5.0,
            )
        )

        aggregate = aggregate_evaluation_reports(reports)

        self.assertEqual(aggregate["report_count"], 3)
        self.assertEqual(aggregate["possession_count"], 2)
        self.assertEqual(aggregate["true_positive_count"], 2)
        self.assertEqual(aggregate["false_positive_count"], 1)
        self.assertEqual(aggregate["false_negative_count"], 1)
        self.assertAlmostEqual(aggregate["micro_precision"], 2.0 / 3.0)
        self.assertAlmostEqual(aggregate["micro_recall"], 2.0 / 3.0)
        self.assertAlmostEqual(aggregate["macro_precision"], 0.5)
        self.assertAlmostEqual(aggregate["macro_recall"], 0.5)
        self.assertEqual(
            aggregate["macro_precision_possession_count"],
            2,
        )
        self.assertEqual(
            aggregate["macro_recall_possession_count"],
            2,
        )
        self.assertEqual(
            aggregate["per_possession"]["possession_001"][
                "report_count"
            ],
            2,
        )

    def test_aggregate_rejects_incomparable_or_overlapping_reports(self):
        annotation_set = parse_reviewed_annotations([observed_frame(0)])
        report = evaluate_predictions(
            annotation_set,
            {0: [detection(100, 100)]},
            confidence_threshold=0.5,
            localization_radius_px=5.0,
        )
        def distinct_variant(**updates):
            variant = copy.deepcopy(report)
            variant.update(
                {
                    "annotation_set_id": "different_annotations",
                    "annotation_content_sha256": "e" * 64,
                    "detection_run_id": "different_run",
                    "window_start_frame_index": 1,
                    "window_end_frame_index": 1,
                }
            )
            variant.update(updates)
            return variant

        invalid_pairs = (
            distinct_variant(localization_radius_px=10.0),
            distinct_variant(model_run_signature="f" * 64),
            distinct_variant(selection_purpose="challenge_evaluation"),
            distinct_variant(
                window_start_frame_index=0,
                window_end_frame_index=0,
            ),
            distinct_variant(possession_id="possession_002"),
            distinct_variant(source_video_sha256="1" * 64),
            distinct_variant(annotation_set_id=report["annotation_set_id"]),
            distinct_variant(detection_run_id=report["detection_run_id"]),
        )

        for invalid in invalid_pairs:
            with self.subTest(report=invalid):
                with self.assertRaises(DetectionEvaluationError):
                    aggregate_evaluation_reports([report, invalid])

    def test_aggregate_requires_consistent_source_hash_per_possession(self):
        reports = []

        for suffix, source_sha256 in (("a", "a" * 64), ("b", "b" * 64)):
            annotation_set = parse_reviewed_annotations(
                [observed_frame(0 if suffix == "a" else 1)],
                annotation_set_id=f"possession_001_{suffix}",
                source_sha256=source_sha256,
            )
            frame_index = annotation_set.window.start_frame_index
            reports.append(
                evaluate_predictions(
                    annotation_set,
                    {frame_index: [detection(100, 100)]},
                    confidence_threshold=0.5,
                    localization_radius_px=5.0,
                )
            )

        with self.assertRaises(DetectionEvaluationError):
            aggregate_evaluation_reports(reports)

        missing_hash = copy.deepcopy(reports[0])
        missing_hash.pop("source_video_sha256")

        with self.assertRaises(DetectionEvaluationError):
            aggregate_evaluation_reports([missing_hash])

    def test_aggregate_rejects_model_signature_provenance_mismatch(self):
        annotation_set = parse_reviewed_annotations([observed_frame(0)])
        report = evaluate_predictions(
            annotation_set,
            {0: [detection(100, 100)]},
        )
        self.assertEqual(
            report["model_run_signature"],
            canonical_sha256(report["model_provenance"]),
        )
        tampered = copy.deepcopy(report)
        tampered["model_run_signature"] = "0" * 64

        with self.assertRaises(DetectionEvaluationError):
            aggregate_evaluation_reports([tampered])

    def test_aggregate_rejects_tampered_counts_and_frame_results(self):
        annotation_set = parse_reviewed_annotations([observed_frame(0)])
        report = evaluate_predictions(
            annotation_set,
            {
                0: [
                    detection(100, 100, 0.9),
                    detection(101, 100, 0.8),
                ]
            },
        )

        impossible_duplicates = copy.deepcopy(report)
        impossible_duplicates["duplicate_false_positive_count"] = (
            impossible_duplicates["false_positive_count"] + 1
        )

        inconsistent_total = copy.deepcopy(report)
        inconsistent_total["true_positive_count"] += 1

        inconsistent_frame = copy.deepcopy(report)
        inconsistent_frame["frame_results"][0][
            "false_positive_count"
        ] += 1

        for tampered in (
            impossible_duplicates,
            inconsistent_total,
            inconsistent_frame,
        ):
            with self.subTest(report=tampered):
                with self.assertRaises(DetectionEvaluationError):
                    aggregate_evaluation_reports([tampered])

    def test_aggregate_rejects_threshold_below_export_floor(self):
        annotation_set = parse_reviewed_annotations([observed_frame(0)])
        report = evaluate_predictions(
            annotation_set,
            {0: [detection(100, 100, 0.9)]},
            confidence_threshold=0.5,
            model_overrides={"export_confidence_floor": 0.5},
        )
        tampered = copy.deepcopy(report)
        tampered["confidence_threshold"] = 0.499

        with self.assertRaises(DetectionEvaluationError):
            aggregate_evaluation_reports([tampered])

    def test_aggregate_rejects_impossible_localization_match(self):
        annotation_set = parse_reviewed_annotations(
            [observed_frame(0, center=(100, 100))]
        )
        report = evaluate_predictions(
            annotation_set,
            {0: [detection(103, 104)]},
            localization_radius_px=5.0,
        )

        invalid_candidate_index = copy.deepcopy(report)
        invalid_candidate_index["frame_results"][0][
            "matched_candidate_index"
        ] = invalid_candidate_index["frame_results"][0][
            "input_detection_count"
        ]

        excessive_error = copy.deepcopy(report)
        excessive_error["frame_results"][0][
            "matched_center_error_px"
        ] = 5.001
        excessive_error["matched_center_error_px"] = {
            "count": 1,
            "mean": 5.001,
            "median": 5.001,
            "maximum": 5.001,
        }

        for tampered in (invalid_candidate_index, excessive_error):
            with self.subTest(report=tampered):
                with self.assertRaises(DetectionEvaluationError):
                    aggregate_evaluation_reports([tampered])


class BallSourceVerificationTests(unittest.TestCase):
    def test_missing_source_and_hash_mismatch_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            missing = parse_annotations(
                [observed_frame(0)],
                source_path="data/clips/missing.avi",
            )

            with self.assertRaisesRegex(
                AnnotationValidationError,
                "Source video does not exist",
            ):
                verify_source_video(missing, root)

            video_path = root / "data" / "clips" / "mismatch.avi"
            video_path.parent.mkdir(parents=True)
            video_path.write_bytes(b"synthetic non-video bytes")
            mismatched = parse_annotations(
                [observed_frame(0)],
                source_path="data/clips/mismatch.avi",
            )

            with self.assertRaisesRegex(
                AnnotationValidationError,
                "SHA-256 does not match",
            ):
                verify_source_video(mismatched, root)

    def test_tiny_mjpg_source_is_hashed_and_probed(self):
        import cv2
        import numpy as np

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video_path = root / "data" / "clips" / "tiny.avi"
            video_path.parent.mkdir(parents=True)
            writer = cv2.VideoWriter(
                str(video_path),
                cv2.VideoWriter_fourcc(*"MJPG"),
                10.0,
                (64, 48),
            )
            self.assertTrue(writer.isOpened())

            try:
                for value in (0, 64, 128):
                    writer.write(
                        np.full((48, 64, 3), value, dtype=np.uint8)
                    )
            finally:
                writer.release()

            source_sha256 = hashlib.sha256(
                video_path.read_bytes()
            ).hexdigest()
            annotation_set = parse_annotations(
                [observed_frame(0, center=(20, 20))],
                source_sha256=source_sha256,
                source_path="data/clips/tiny.avi",
                width_px=64,
                height_px=48,
                fps=10.0,
                frame_count=3,
            )
            verification = verify_source_video(annotation_set, root)

        self.assertEqual(verification["status"], "verified_source_video")
        self.assertEqual(verification["sha256"], source_sha256)
        self.assertEqual(verification["width_px"], 64)
        self.assertEqual(verification["height_px"], 48)
        self.assertEqual(verification["frame_count"], 3)

    def test_invalid_backend_metadata_is_rejected_as_annotation_error(self):
        class FakeCapture:
            def __init__(self, values):
                self.values = values

            def isOpened(self):
                return True

            def get(self, property_id):
                return self.values[property_id]

            def release(self):
                return None

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video_path = root / "data" / "clips" / "metadata.avi"
            video_path.parent.mkdir(parents=True)
            video_path.write_bytes(b"source bytes for metadata contract")
            source_sha256 = hashlib.sha256(video_path.read_bytes()).hexdigest()
            annotation_set = parse_annotations(
                [observed_frame(0)],
                source_sha256=source_sha256,
                source_path="data/clips/metadata.avi",
            )
            invalid_cases = (
                (float("nan"), 1080.0, 25.0, 499.0),
                (1920.5, 1080.0, 25.0, 499.0),
                (1920.0, 1080.0, 0.0, 499.0),
                (1920.0, 1080.0, 25.0, float("inf")),
            )

            for width, height, fps, frame_count in invalid_cases:
                with self.subTest(
                    width=width,
                    height=height,
                    fps=fps,
                    frame_count=frame_count,
                ):
                    fake_cv2 = types.SimpleNamespace(
                        CAP_PROP_FRAME_WIDTH=1,
                        CAP_PROP_FRAME_HEIGHT=2,
                        CAP_PROP_FPS=3,
                        CAP_PROP_FRAME_COUNT=4,
                        VideoCapture=lambda _path: FakeCapture(
                            {
                                1: width,
                                2: height,
                                3: fps,
                                4: frame_count,
                            }
                        ),
                    )
                    with patch.dict(sys.modules, {"cv2": fake_cv2}):
                        with self.assertRaisesRegex(
                            AnnotationValidationError,
                            "invalid positive",
                        ):
                            verify_source_video(annotation_set, root)


class BallAnnotationCliTests(unittest.TestCase):
    def test_help_is_available(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.ball_tracking.validate_annotations",
                "--help",
            ],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("--annotations", result.stdout)
        self.assertIn("--verify-source", result.stdout)
        self.assertIn("version 0.1", result.stdout)

    def test_reviewed_document_requires_source_verification(self):
        payload = annotation_payload([observed_frame(0)])
        payload["review"].update(
            {
                "status": "reviewed",
                "reviewer_id": "synthetic_reviewer",
                "reviewed_at_utc": "2026-08-23T13:00:00Z",
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "reviewed_annotations.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "src.ball_tracking.validate_annotations",
                    "--annotations",
                    str(path),
                    "--json",
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "Reviewed annotations require --verify-source",
            result.stderr,
        )

    def test_valid_document_prints_json_summary(self):
        payload = annotation_payload([observed_frame(0)])

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "annotations.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "src.ball_tracking.validate_annotations",
                    "--annotations",
                    str(path),
                    "--json",
                ],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

        summary = json.loads(result.stdout)
        self.assertEqual(
            summary["annotation_set_id"],
            "possession_001_ball_pilot",
        )
        self.assertEqual(summary["frame_count"], 1)
        self.assertEqual(summary["localization_eligible_count"], 1)
        self.assertEqual(summary["review_status"], "draft")


class BallAnnotationFinalizationReceiptTests(unittest.TestCase):
    def _assert_receipt_binds_metadata_only_self_review_transition(
        self,
        annotation_filename,
        approval_filename,
        finalization_filename,
    ):
        annotation_path = (
            REPO_ROOT
            / "configs"
            / "ball_tracking"
            / "annotations"
            / annotation_filename
        )
        approval_path = (
            REPO_ROOT
            / "configs"
            / "ball_tracking"
            / "reviews"
            / approval_filename
        )
        finalization_path = (
            REPO_ROOT
            / "configs"
            / "ball_tracking"
            / "reviews"
            / finalization_filename
        )

        annotation_bytes = annotation_path.read_bytes()
        approval_bytes = approval_path.read_bytes()
        annotation_payload = json.loads(annotation_bytes)
        approval = json.loads(approval_bytes)
        finalization = json.loads(finalization_path.read_bytes())
        annotation_set = load_annotations(annotation_path)

        self.assertEqual(annotation_set.review.status, "reviewed")
        self.assertEqual(annotation_set.review.reviewer_id, "ryan")
        self.assertFalse(
            finalization["review_policy"]["independent_reannotation_required"]
        )
        self.assertFalse(
            finalization["optional_reannotation"]["used_for_this_finalization"]
        )
        self.assertFalse(
            finalization["optional_reannotation"]["independent_draft_used"]
        )
        self.assertFalse(
            approval["limitations"][
                "requires_later_independent_submission_and_adjudication"
            ]
        )

        approved_review = finalization["approved_visual_review"]
        self.assertEqual(
            approved_review["approval_receipt_file_sha256"],
            hashlib.sha256(approval_bytes).hexdigest(),
        )
        self.assertEqual(
            approved_review["approval_receipt_canonical_sha256"],
            canonical_sha256(approval),
        )
        self.assertEqual(
            approved_review["visual_bundle_manifest_sha256"],
            approval["visual_review_bundle"]["manifest_sha256"],
        )

        final_annotation = finalization["final_annotation"]
        self.assertEqual(
            final_annotation["annotation_file_sha256"],
            hashlib.sha256(annotation_bytes).hexdigest(),
        )
        self.assertEqual(
            final_annotation["canonical_annotation_sha256"],
            canonical_sha256(annotation_payload),
        )

        transition = finalization["transition"]
        self.assertEqual(
            transition["allowed_changed_json_pointers"],
            [
                "/review/status",
                "/review/reviewer_id",
                "/review/reviewed_at_utc",
            ],
        )
        self.assertEqual(
            transition["actual_changed_json_pointers"],
            transition["allowed_changed_json_pointers"],
        )
        self.assertEqual(transition["after_review"], annotation_payload["review"])

        decision_payload = {
            key: value
            for key, value in annotation_payload.items()
            if key != "review"
        }
        self.assertEqual(
            transition["final_decision_payload_sha256"],
            canonical_sha256(decision_payload),
        )
        self.assertEqual(
            transition["approved_decision_payload_sha256"],
            transition["final_decision_payload_sha256"],
        )
        self.assertEqual(
            transition["annotation_rows_sha256"],
            canonical_sha256(annotation_payload["annotations"]),
        )

        approved_draft = copy.deepcopy(annotation_payload)
        approved_draft["review"] = transition["before_review"]
        self.assertEqual(
            transition["approved_draft_canonical_sha256"],
            canonical_sha256(approved_draft),
        )
        self.assertEqual(
            transition["approved_draft_annotation_file_sha256"],
            approval["bound_inputs"]["annotation_file_sha256"],
        )
        self.assertEqual(
            transition["approved_draft_canonical_sha256"],
            approval["bound_inputs"]["canonical_annotation_sha256"],
        )

    def test_p001_receipt_binds_metadata_only_self_review_transition(self):
        self._assert_receipt_binds_metadata_only_self_review_transition(
            "possession_001_frames_0375_0399_protocol_adjudication_v0_1.json",
            "possession_001_visual_review_approval_v0_1.json",
            "possession_001_single_annotator_finalization_v0_1.json",
        )

    def test_p002_receipt_binds_metadata_only_self_review_transition(self):
        self._assert_receipt_binds_metadata_only_self_review_transition(
            "possession_002_frames_0318_0342_protocol_adjudication_v0_1.json",
            "possession_002_visual_review_approval_v0_1.json",
            "possession_002_single_annotator_finalization_v0_1.json",
        )

    def test_p003_receipt_binds_metadata_only_self_review_transition(self):
        self._assert_receipt_binds_metadata_only_self_review_transition(
            "possession_003_frames_0416_0440_protocol_adjudication_v0_1.json",
            "possession_003_visual_review_approval_v0_1.json",
            "possession_003_single_annotator_finalization_v0_1.json",
        )


if __name__ == "__main__":
    unittest.main()
