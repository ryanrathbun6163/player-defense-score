"""Tests for the prediction-blind ball-annotation desktop editor helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.ball_tracking.annotate_frames import (
    AnnotationEditorError,
    DisplayTransform,
    FormValidationError,
    FrameFormValues,
    atomic_save_frame,
    build_updated_payload,
    form_to_annotation_row,
    map_canvas_to_source,
    map_source_to_canvas,
    normalize_form_values,
    prepare_annotation_session,
    uncertainty_radius_from_boundary,
)
from src.ball_tracking.annotations import (
    AnnotationValidationError,
    BallAnnotationSet,
)


def make_payload(*, reviewed: bool = False, frame_count: int = 2) -> dict:
    annotations = []
    for frame_index in range(frame_count):
        if reviewed:
            annotations.append(
                {
                    "frame_index": frame_index,
                    "annotation_status": "labeled",
                    "visibility": "not_visible",
                    "absence_reason": "unknown",
                    "game_ball_identity_certainty": "probable",
                    "geometry": None,
                    "localization_eligible": False,
                    "difficulty_tags": [],
                    "notes": None,
                }
            )
        else:
            annotations.append(
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
            )
    return {
        "schema_version": "0.1",
        "annotation_set_id": "editor_test_set",
        "possession_id": "possession_test",
        "source_video": {
            "path": "data/clips/test.mp4",
            "sha256": "a" * 64,
            "width_px": 1920,
            "height_px": 1080,
            "fps": 25.0,
            "frame_count": frame_count,
        },
        "window": {
            "start_frame_index": 0,
            "end_frame_index": frame_count - 1,
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
            "status": "reviewed" if reviewed else "draft",
            "annotator_id": "ryan",
            "reviewer_id": "reviewer" if reviewed else None,
            "created_at_utc": "2026-08-23T00:00:00Z",
            "reviewed_at_utc": "2026-08-23T01:00:00Z" if reviewed else None,
        },
        "annotations": annotations,
    }


class CoordinateMappingTests(unittest.TestCase):
    def test_canvas_center_maps_to_original_source_center(self) -> None:
        transform = DisplayTransform(100.0, 50.0, 960.0, 540.0, 1920, 1080)
        self.assertEqual(
            map_canvas_to_source(580.0, 320.0, transform),
            (960.0, 540.0),
        )
        self.assertEqual(
            map_source_to_canvas(960.0, 540.0, transform),
            (580.0, 320.0),
        )

    def test_letterbox_and_exclusive_edges_are_rejected(self) -> None:
        transform = DisplayTransform(100.0, 50.0, 960.0, 540.0, 1920, 1080)
        for point in ((99.9, 50.0), (100.0, 49.9), (1060.0, 100.0), (500, 590)):
            with self.subTest(point=point):
                with self.assertRaises(FormValidationError):
                    map_canvas_to_source(*point, transform)

    def test_uncertainty_radius_is_measured_from_visual_boundary(self) -> None:
        self.assertEqual(
            uncertainty_radius_from_boundary(100.0, 100.0, 103.0, 104.0),
            5.0,
        )
        with self.assertRaises(FormValidationError):
            uncertainty_radius_from_boundary(100.0, 100.0, 100.0, 100.0)


class FormStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.annotation_set = BallAnnotationSet.from_mapping(make_payload())
        self.source = self.annotation_set.source_video

    def test_not_visible_clears_stale_geometry_and_eligibility(self) -> None:
        normalized = normalize_form_values(
            FrameFormValues(
                annotation_status="labeled",
                visibility="not_visible",
                absence_reason="occluded",
                identity_certainty="certain",
                has_geometry=True,
                center_x="500",
                center_y="400",
                uncertainty_radius_px="2",
                localization_eligible=True,
                difficulty_tags=("player_overlap",),
            )
        )
        self.assertFalse(normalized.has_geometry)
        self.assertIsNone(normalized.center_x)
        self.assertFalse(normalized.localization_eligible)
        self.assertEqual(normalized.absence_reason, "occluded")
        self.assertEqual(normalized.difficulty_tags, ("player_overlap",))

    def test_indeterminate_forces_ambiguous_and_clears_incompatible_state(self) -> None:
        normalized = normalize_form_values(
            FrameFormValues(
                annotation_status="labeled",
                visibility="indeterminate",
                absence_reason="unknown",
                identity_certainty="certain",
                has_geometry=True,
                center_x="100",
                center_y="100",
                uncertainty_radius_px="2",
                localization_eligible=True,
                notes="Cannot resolve competing orange objects.",
            )
        )
        self.assertEqual(normalized.identity_certainty, "ambiguous")
        self.assertIsNone(normalized.absence_reason)
        self.assertFalse(normalized.has_geometry)
        self.assertFalse(normalized.localization_eligible)

    def test_excluded_clears_semantic_fields_but_retains_required_note(self) -> None:
        row = form_to_annotation_row(
            0,
            FrameFormValues(
                annotation_status="excluded",
                visibility="fully_visible",
                identity_certainty="certain",
                has_geometry=True,
                center_x="100",
                center_y="100",
                uncertainty_radius_px="2",
                localization_eligible=True,
                difficulty_tags=("motion_blur",),
                notes="Source frame is corrupted.",
            ),
            self.source,
        )
        self.assertEqual(row["annotation_status"], "excluded")
        self.assertIsNone(row["visibility"])
        self.assertIsNone(row["geometry"])
        self.assertEqual(row["difficulty_tags"], [])
        self.assertEqual(row["notes"], "Source frame is corrupted.")

    def test_visibility_derives_the_approved_geometry_source(self) -> None:
        complete = form_to_annotation_row(
            0,
            FrameFormValues(
                annotation_status="labeled",
                visibility="fully_visible",
                identity_certainty="certain",
                has_geometry=True,
                center_x="960.5",
                center_y="540.25",
                uncertainty_radius_px="1.5",
                localization_eligible=True,
            ),
            self.source,
        )
        partial = form_to_annotation_row(
            0,
            FrameFormValues(
                annotation_status="labeled",
                visibility="partially_visible",
                identity_certainty="probable",
                has_geometry=True,
                center_x="960.5",
                center_y="540.25",
                uncertainty_radius_px="4",
                localization_eligible=True,
            ),
            self.source,
        )
        self.assertEqual(
            complete["geometry"]["source"], "observed_complete_ball_center"
        )
        self.assertEqual(partial["geometry"]["source"], "human_amodal_estimate")

    def test_invalid_point_is_rejected(self) -> None:
        with self.assertRaises(AnnotationValidationError):
            form_to_annotation_row(
                0,
                FrameFormValues(
                    annotation_status="labeled",
                    visibility="fully_visible",
                    identity_certainty="certain",
                    has_geometry=True,
                    center_x="1920",
                    center_y="100",
                    uncertainty_radius_px="2",
                    localization_eligible=True,
                ),
                self.source,
            )

    def test_invalid_uncertainty_is_rejected(self) -> None:
        for uncertainty in ("", "0", "nan", "not-a-number"):
            with self.subTest(uncertainty=uncertainty):
                with self.assertRaises(
                    (FormValidationError, AnnotationValidationError)
                ):
                    form_to_annotation_row(
                        0,
                        FrameFormValues(
                            annotation_status="labeled",
                            visibility="fully_visible",
                            identity_certainty="certain",
                            has_geometry=True,
                            center_x="100",
                            center_y="100",
                            uncertainty_radius_px=uncertainty,
                            localization_eligible=True,
                        ),
                        self.source,
                    )

    def test_required_notes_are_not_satisfied_by_whitespace(self) -> None:
        forms = (
            FrameFormValues(annotation_status="excluded", notes="   "),
            FrameFormValues(
                annotation_status="labeled",
                visibility="indeterminate",
                identity_certainty="ambiguous",
                notes="\t",
            ),
            FrameFormValues(
                annotation_status="labeled",
                visibility="fully_visible",
                identity_certainty="probable",
                has_geometry=False,
                notes="\n",
            ),
        )
        for form in forms:
            with self.subTest(form=form):
                with self.assertRaises(AnnotationValidationError):
                    form_to_annotation_row(0, form, self.source)


class SessionAndAtomicSaveTests(unittest.TestCase):
    def test_reviewed_set_is_refused_before_source_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            annotation_path = root / "reviewed.json"
            annotation_path.write_text(
                json.dumps(make_payload(reviewed=True)), encoding="utf-8"
            )
            with mock.patch(
                "src.ball_tracking.annotate_frames.verify_source_video"
            ) as verify_mock:
                with self.assertRaisesRegex(AnnotationEditorError, "read-only"):
                    prepare_annotation_session(annotation_path, root)
                verify_mock.assert_not_called()

    def test_build_and_atomic_save_validate_the_complete_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            annotation_path = Path(temporary_directory) / "draft.json"
            original_payload = make_payload()
            annotation_path.write_text(
                json.dumps(original_payload, indent=2) + "\n", encoding="utf-8"
            )
            annotation_set = BallAnnotationSet.from_mapping(original_payload)
            row = form_to_annotation_row(
                0,
                FrameFormValues(
                    annotation_status="labeled",
                    visibility="fully_visible",
                    identity_certainty="certain",
                    has_geometry=True,
                    center_x="123.25",
                    center_y="456.5",
                    uncertainty_radius_px="2",
                    localization_eligible=True,
                    difficulty_tags=("tiny_apparent_size",),
                ),
                annotation_set.source_video,
            )

            built = build_updated_payload(annotation_set, row)
            self.assertEqual(
                original_payload["annotations"][0]["annotation_status"],
                "unlabeled",
            )
            self.assertEqual(built["annotations"][0]["annotation_status"], "labeled")
            self.assertEqual(built["review"]["status"], "draft")

            updated = atomic_save_frame(annotation_path, annotation_set, row)
            loaded = json.loads(annotation_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, updated.to_dict())
            self.assertEqual(updated.review.status, "draft")
            self.assertEqual(updated.annotations[1].annotation_status, "unlabeled")
            self.assertEqual(list(annotation_path.parent.glob(".*.tmp")), [])

    def test_invalid_complete_update_does_not_touch_original_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            annotation_path = Path(temporary_directory) / "draft.json"
            payload = make_payload()
            original_bytes = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
            annotation_path.write_bytes(original_bytes)
            annotation_set = BallAnnotationSet.from_mapping(payload)
            invalid_row = annotation_set.annotations[0].to_dict()
            invalid_row["frame_index"] = 99

            with self.assertRaises(FormValidationError):
                atomic_save_frame(annotation_path, annotation_set, invalid_row)
            self.assertEqual(annotation_path.read_bytes(), original_bytes)

    def test_replace_failure_keeps_original_and_cleans_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            annotation_path = Path(temporary_directory) / "draft.json"
            payload = make_payload()
            original_bytes = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
            annotation_path.write_bytes(original_bytes)
            annotation_set = BallAnnotationSet.from_mapping(payload)
            row = form_to_annotation_row(
                0,
                FrameFormValues(
                    annotation_status="labeled",
                    visibility="not_visible",
                    absence_reason="occluded",
                    identity_certainty="probable",
                ),
                annotation_set.source_video,
            )
            with mock.patch(
                "src.ball_tracking.annotate_frames.os.replace",
                side_effect=OSError("simulated replace failure"),
            ):
                with self.assertRaises(OSError):
                    atomic_save_frame(annotation_path, annotation_set, row)
            self.assertEqual(annotation_path.read_bytes(), original_bytes)
            self.assertEqual(list(annotation_path.parent.glob(".*.tmp")), [])

    def test_stale_second_editor_cannot_overwrite_newer_saved_frame(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            annotation_path = Path(temporary_directory) / "draft.json"
            payload = make_payload()
            annotation_path.write_text(
                json.dumps(payload, indent=2) + "\n", encoding="utf-8"
            )
            first_editor = BallAnnotationSet.from_mapping(payload)
            stale_second_editor = BallAnnotationSet.from_mapping(payload)
            first_row = form_to_annotation_row(
                0,
                FrameFormValues(
                    annotation_status="labeled",
                    visibility="not_visible",
                    absence_reason="occluded",
                    identity_certainty="probable",
                ),
                first_editor.source_video,
            )
            atomic_save_frame(annotation_path, first_editor, first_row)
            newer_bytes = annotation_path.read_bytes()

            stale_row = form_to_annotation_row(
                1,
                FrameFormValues(
                    annotation_status="labeled",
                    visibility="not_visible",
                    absence_reason="unknown",
                    identity_certainty="probable",
                ),
                stale_second_editor.source_video,
            )
            with self.assertRaisesRegex(
                AnnotationEditorError,
                "changed on disk.*nothing was written",
            ):
                atomic_save_frame(
                    annotation_path,
                    stale_second_editor,
                    stale_row,
                )
            self.assertEqual(annotation_path.read_bytes(), newer_bytes)
            self.assertEqual(list(annotation_path.parent.glob(".*.tmp")), [])

    def test_session_cannot_overwrite_file_promoted_to_reviewed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            annotation_path = Path(temporary_directory) / "annotations.json"
            draft_payload = make_payload()
            draft_set = BallAnnotationSet.from_mapping(draft_payload)
            annotation_path.write_text(
                json.dumps(draft_payload, indent=2) + "\n", encoding="utf-8"
            )

            reviewed_payload = make_payload(reviewed=True)
            reviewed_bytes = (
                json.dumps(reviewed_payload, indent=2) + "\n"
            ).encode("utf-8")
            annotation_path.write_bytes(reviewed_bytes)
            stale_row = form_to_annotation_row(
                0,
                FrameFormValues(
                    annotation_status="labeled",
                    visibility="not_visible",
                    absence_reason="occluded",
                    identity_certainty="certain",
                ),
                draft_set.source_video,
            )

            with self.assertRaisesRegex(
                AnnotationEditorError,
                "changed on disk.*nothing was written",
            ):
                atomic_save_frame(annotation_path, draft_set, stale_row)
            self.assertEqual(annotation_path.read_bytes(), reviewed_bytes)
            self.assertEqual(list(annotation_path.parent.glob(".*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
