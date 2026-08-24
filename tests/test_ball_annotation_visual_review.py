"""Focused tests for immutable post-annotation visual-review evidence."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from src.ball_tracking import prepare_annotation_visual_review as visual_review_module
from src.ball_tracking.annotations import BallAnnotationSet
from src.ball_tracking.prepare_annotation_review import (
    ReviewAssetPreparationError,
    prepare_annotation_review,
)
from src.ball_tracking.prepare_annotation_visual_review import (
    AnnotationVisualReviewError,
    CONTACT_HEADER_HEIGHT_PX,
    CONTACT_ROWS,
    CONTACT_TILE_HEIGHT_PX,
    EXPECTED_FRAME_COUNT,
    TRAJECTORY_HEIGHT_PX,
    TRAJECTORY_WIDTH_PX,
    ZOOM_FACTOR,
    ZOOM_HEADER_HEIGHT_PX,
    ZOOM_PANEL_HEIGHT_PX,
    ZOOM_PANEL_WIDTH_PX,
    ZOOM_SIZE_PX,
    aspect_preserving_letterbox,
    bundle_input_components,
    bundle_input_sha256,
    canonical_annotation_sha256,
    frame_visual_semantics,
    generator_fingerprint,
    generator_fingerprint_sha256,
    prepare_annotation_visual_review,
    render_overlay_frame,
    render_zoom_panel,
    trajectory_segments,
    trajectory_missingness,
    validate_output_location,
    zoom_panel_mapping,
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_video(root: Path) -> Path:
    path = root / "data" / "clips" / "visual_review.avi"
    path.parent.mkdir(parents=True)
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        10.0,
        (320, 180),
    )
    if not writer.isOpened():
        raise RuntimeError("synthetic MJPG writer unavailable")
    try:
        for frame_index in range(30):
            frame = np.zeros((180, 320, 3), dtype=np.uint8)
            frame[:, :, 0] = frame_index * 7 % 256
            frame[:, :, 1] = np.arange(320, dtype=np.uint16) % 256
            frame[:, :, 2] = np.arange(180, dtype=np.uint8)[:, None]
            writer.write(frame)
    finally:
        writer.release()
    return path


def source_metadata(video_path: Path, root: Path) -> dict:
    capture = cv2.VideoCapture(str(video_path))
    try:
        return {
            "path": video_path.relative_to(root).as_posix(),
            "sha256": sha256_file(video_path),
            "width_px": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height_px": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": float(capture.get(cv2.CAP_PROP_FPS)),
            "frame_count": int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
        }
    finally:
        capture.release()


def base_payload(video_path: Path, root: Path) -> dict:
    return {
        "schema_version": "0.1",
        "annotation_set_id": "visual_review_test",
        "possession_id": "possession_999",
        "source_video": source_metadata(video_path, root),
        "window": {
            "start_frame_index": 2,
            "end_frame_index": 26,
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
            "annotator_id": "synthetic_annotator",
            "reviewer_id": None,
            "created_at_utc": "2026-08-23T12:00:00Z",
            "reviewed_at_utc": None,
        },
        "annotations": [
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
            for frame_index in range(2, 27)
        ],
    }


def complete_payload(payload: dict, *, reviewed: bool = False) -> dict:
    result = json.loads(json.dumps(payload))
    annotations = []
    for frame_index in range(2, 27):
        if frame_index == 4:
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
        elif frame_index == 5:
            row = {
                "frame_index": frame_index,
                "annotation_status": "labeled",
                "visibility": "indeterminate",
                "absence_reason": None,
                "game_ball_identity_certainty": "ambiguous",
                "geometry": None,
                "localization_eligible": False,
                "difficulty_tags": ["background_clutter"],
                "notes": "Two plausible orange objects.",
            }
        elif frame_index == 6:
            row = {
                "frame_index": frame_index,
                "annotation_status": "excluded",
                "visibility": None,
                "absence_reason": None,
                "game_ball_identity_certainty": None,
                "geometry": None,
                "localization_eligible": False,
                "difficulty_tags": [],
                "notes": "Synthetic source fault for coverage.",
            }
        else:
            partial = frame_index % 3 == 0
            row = {
                "frame_index": frame_index,
                "annotation_status": "labeled",
                "visibility": "partially_visible" if partial else "fully_visible",
                "absence_reason": None,
                "game_ball_identity_certainty": "probable" if partial else "certain",
                "geometry": {
                    "center_xy_px": [
                        30.25 + (frame_index - 2) * 8.0,
                        60.5 + (frame_index - 2) * 2.0,
                    ],
                    "source": (
                        "human_amodal_estimate"
                        if partial
                        else "observed_complete_ball_center"
                    ),
                    "uncertainty_radius_px": 4.0 if partial else 2.0,
                },
                "localization_eligible": True,
                "difficulty_tags": ["motion_blur"] if partial else [],
                "notes": None,
            }
        annotations.append(row)
    result["annotations"] = annotations
    if reviewed:
        result["review"] = {
            "status": "reviewed",
            "annotator_id": "synthetic_annotator",
            "reviewer_id": "synthetic_reviewer",
            "created_at_utc": "2026-08-23T12:00:00Z",
            "reviewed_at_utc": "2026-08-23T13:00:00Z",
        }
    return result


def write_json(path: Path, payload: dict) -> bytes:
    content = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
    path.write_bytes(content)
    return content


def prepare_inputs(root: Path) -> tuple[Path, Path, Path, dict]:
    video_path = write_video(root)
    draft = base_payload(video_path, root)
    annotation_path = root / "annotations.json"
    write_json(annotation_path, draft)
    neutral_dir = (
        root
        / "data"
        / "outputs"
        / "ball_tracking"
        / "annotation_review"
        / "possession_999"
        / "frames_0002_0026"
    )
    prepare_annotation_review(annotation_path, root, neutral_dir)
    complete = complete_payload(draft)
    write_json(annotation_path, complete)
    return annotation_path, neutral_dir, video_path, complete


def expected_bundle_identity(
    annotation_path: Path,
    neutral_dir: Path,
    payload: dict,
) -> tuple[dict[str, str], str]:
    components = bundle_input_components(
        BallAnnotationSet.from_mapping(payload),
        annotation_path.read_bytes(),
        (neutral_dir / "manifest.json").read_bytes(),
        generator_fingerprint(),
    )
    return components, bundle_input_sha256(components)


def output_window(root: Path) -> Path:
    return (
        root
        / "data"
        / "outputs"
        / "ball_tracking"
        / "annotation_visual_review"
        / "possession_999"
        / "frames_0002_0026"
    )


class PureVisualConventionTests(unittest.TestCase):
    def test_semantics_and_zoom_mapping_do_not_invent_geometry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            annotation_path, _neutral, _video, payload = prepare_inputs(root)
            annotation_set = BallAnnotationSet.from_mapping(payload)
            observed = annotation_set.annotations[0]
            no_point = annotation_set.annotations[2]
            self.assertEqual(frame_visual_semantics(observed)["glyph"], "circle")
            self.assertEqual(frame_visual_semantics(no_point)["glyph"], "none")
            self.assertIsNone(
                zoom_panel_mapping(no_point)["requested_source_crop_xyxy_px"]
            )
            mapping = zoom_panel_mapping(observed)
            self.assertEqual(mapping["panel_type"], "geometry_zoom")
            self.assertAlmostEqual(
                mapping["annotated_panel_center_xy_px"][0],
                ZOOM_SIZE_PX + (60.25 * ZOOM_FACTOR),
            )
            self.assertTrue(annotation_path.is_file())

    def test_visible_without_geometry_is_never_drawn_as_observed_or_amodal(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _path, _neutral, _video, payload = prepare_inputs(root)
            row = payload["annotations"][0]
            row["geometry"] = None
            row["localization_eligible"] = False
            row["notes"] = "Visible, but no defensible center can be placed."
            annotation = BallAnnotationSet.from_mapping(payload).annotations[0]
            semantics = frame_visual_semantics(annotation)
            self.assertEqual(
                semantics["state_text"],
                "VISIBLE - NO DEFENSIBLE POINT",
            )
            self.assertEqual(semantics["glyph"], "none")
            self.assertEqual(
                zoom_panel_mapping(annotation)["panel_type"],
                "status",
            )

    def test_trajectory_segments_break_at_every_geometry_gap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _path, _neutral, _video, payload = prepare_inputs(root)
            annotation_set = BallAnnotationSet.from_mapping(payload)
            segments = trajectory_segments(annotation_set)
            self.assertIn((2, 3), segments)
            self.assertNotIn((3, 7), segments)
            self.assertNotIn((3, 4), segments)
            self.assertIn((7, 8), segments)

    def test_trajectory_missingness_distinguishes_edges_internal_and_all(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _path, _neutral, _video, payload = prepare_inputs(root)
            for offset, row in enumerate(payload["annotations"]):
                row.update(
                    {
                        "annotation_status": "labeled",
                        "visibility": "fully_visible",
                        "absence_reason": None,
                        "game_ball_identity_certainty": "certain",
                        "geometry": {
                            "center_xy_px": [40.0 + offset, 70.0],
                            "source": "observed_complete_ball_center",
                            "uncertainty_radius_px": 2.0,
                        },
                        "localization_eligible": True,
                        "difficulty_tags": [],
                        "notes": None,
                    }
                )

            dense = BallAnnotationSet.from_mapping(payload)
            self.assertEqual(
                trajectory_missingness(dense),
                {
                    "missing_geometry_count": 0,
                    "has_any_missing_geometry": False,
                    "all_geometry_missing": False,
                    "leading_missing_geometry_count": 0,
                    "internal_missing_geometry_count": 0,
                    "trailing_missing_geometry_count": 0,
                    "has_internal_geometry_discontinuities": False,
                },
            )

            edge_only = json.loads(json.dumps(payload))
            for position in (0, 1, 23, 24):
                row = edge_only["annotations"][position]
                row["geometry"] = None
                row["localization_eligible"] = False
                row["notes"] = "No defensible point."
            summary = trajectory_missingness(
                BallAnnotationSet.from_mapping(edge_only)
            )
            self.assertEqual(summary["missing_geometry_count"], 4)
            self.assertEqual(summary["leading_missing_geometry_count"], 2)
            self.assertEqual(summary["internal_missing_geometry_count"], 0)
            self.assertEqual(summary["trailing_missing_geometry_count"], 2)
            self.assertTrue(summary["has_any_missing_geometry"])
            self.assertFalse(summary["has_internal_geometry_discontinuities"])
            self.assertFalse(summary["all_geometry_missing"])

            edge_and_internal = json.loads(json.dumps(edge_only))
            row = edge_and_internal["annotations"][8]
            row["geometry"] = None
            row["localization_eligible"] = False
            row["notes"] = "No defensible point."
            summary = trajectory_missingness(
                BallAnnotationSet.from_mapping(edge_and_internal)
            )
            self.assertEqual(summary["missing_geometry_count"], 5)
            self.assertEqual(summary["internal_missing_geometry_count"], 1)
            self.assertTrue(summary["has_internal_geometry_discontinuities"])

            all_missing = json.loads(json.dumps(payload))
            for row in all_missing["annotations"]:
                row["geometry"] = None
                row["localization_eligible"] = False
                row["notes"] = "No defensible point."
            summary = trajectory_missingness(
                BallAnnotationSet.from_mapping(all_missing)
            )
            self.assertEqual(summary["missing_geometry_count"], 25)
            self.assertEqual(summary["leading_missing_geometry_count"], 0)
            self.assertEqual(summary["internal_missing_geometry_count"], 0)
            self.assertEqual(summary["trailing_missing_geometry_count"], 0)
            self.assertTrue(summary["has_any_missing_geometry"])
            self.assertTrue(summary["all_geometry_missing"])
            self.assertFalse(summary["has_internal_geometry_discontinuities"])

    def test_overlay_renderer_does_not_mutate_native_source_array(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _path, _neutral, _video, payload = prepare_inputs(root)
            annotation = BallAnnotationSet.from_mapping(payload).annotations[0]
            source = np.full((180, 320, 3), 77, dtype=np.uint8)
            original = source.copy()
            overlay = render_overlay_frame(source, annotation, "draft")
            self.assertTrue(np.array_equal(source, original))
            self.assertFalse(np.array_equal(overlay, original))

    def test_zoom_panel_preserves_an_unmarked_raw_nearest_neighbor_view(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _path, _neutral, _video, payload = prepare_inputs(root)
            annotation = BallAnnotationSet.from_mapping(payload).annotations[5]
            source = np.arange(180 * 320 * 3, dtype=np.uint32)
            source = (source.reshape(180, 320, 3) % 256).astype(np.uint8)
            panel, mapping = render_zoom_panel(source, annotation, "draft")
            left, top, right, bottom = mapping[
                "requested_source_crop_xyxy_px"
            ]
            expected_raw = cv2.resize(
                source[top:bottom, left:right],
                (ZOOM_SIZE_PX, ZOOM_SIZE_PX),
                interpolation=cv2.INTER_NEAREST,
            )
            raw_view = panel[
                ZOOM_HEADER_HEIGHT_PX:,
                :ZOOM_SIZE_PX,
            ]
            self.assertTrue(np.array_equal(raw_view, expected_raw))

    def test_contact_letterbox_preserves_aspect_ratio_with_explicit_bars(
        self,
    ) -> None:
        source = np.full((50, 100, 3), 255, dtype=np.uint8)
        tile = aspect_preserving_letterbox(source, 100, 100)
        self.assertEqual(tile.shape, (100, 100, 3))
        self.assertTrue(np.all(tile[:25] == 18))
        self.assertTrue(np.all(tile[25:75] == 255))
        self.assertTrue(np.all(tile[75:] == 18))

    def test_bundle_identity_binds_exact_bytes_code_helpers_and_runtime(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            annotation_path, neutral_dir, _video, payload = prepare_inputs(root)
            annotation_set = BallAnnotationSet.from_mapping(payload)
            exact_bytes = annotation_path.read_bytes()
            reformatted_bytes = json.dumps(
                payload,
                separators=(",", ":"),
            ).encode("utf-8")
            neutral_bytes = (neutral_dir / "manifest.json").read_bytes()
            fingerprint = generator_fingerprint()
            exact = bundle_input_components(
                annotation_set,
                exact_bytes,
                neutral_bytes,
                fingerprint,
            )
            reformatted = bundle_input_components(
                annotation_set,
                reformatted_bytes,
                neutral_bytes,
                fingerprint,
            )
            helper_changed_fingerprint = dict(fingerprint)
            helper_changed_fingerprint[
                "annotation_review_module_sha256"
            ] = "0" * 64
            helper_changed = bundle_input_components(
                annotation_set,
                exact_bytes,
                neutral_bytes,
                helper_changed_fingerprint,
            )
            runtime_changed_fingerprint = dict(fingerprint)
            runtime_changed_fingerprint["opencv_version"] += "-changed"
            runtime_changed = bundle_input_components(
                annotation_set,
                exact_bytes,
                neutral_bytes,
                runtime_changed_fingerprint,
            )
            self.assertEqual(
                exact["canonical_annotation_sha256"],
                reformatted["canonical_annotation_sha256"],
            )
            self.assertNotEqual(
                bundle_input_sha256(exact),
                bundle_input_sha256(reformatted),
            )
            self.assertNotEqual(
                bundle_input_sha256(exact),
                bundle_input_sha256(helper_changed),
            )
            self.assertNotEqual(
                bundle_input_sha256(exact),
                bundle_input_sha256(runtime_changed),
            )


class OutputLocationTests(unittest.TestCase):
    def test_output_must_be_below_dedicated_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            dedicated = (
                root
                / "data"
                / "outputs"
                / "ball_tracking"
                / "annotation_visual_review"
            )
            dedicated.mkdir(parents=True)
            valid = dedicated / "possession" / "window" / ("a" * 64)
            validate_output_location(root, valid)
            with self.assertRaisesRegex(
                AnnotationVisualReviewError,
                "outside the dedicated",
            ):
                validate_output_location(
                    root,
                    root / "data" / "outputs" / "wrong" / ("a" * 64),
                )
            with self.assertRaisesRegex(
                AnnotationVisualReviewError,
                "strict descendant",
            ):
                validate_output_location(root, dedicated)

    def test_output_rejects_symlink_and_windows_reparse_ancestors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            dedicated = (
                root
                / "data"
                / "outputs"
                / "ball_tracking"
                / "annotation_visual_review"
            )
            dedicated.mkdir(parents=True)
            target = dedicated / "possession" / "window" / ("b" * 64)

            def marks_dedicated_as_link(path: Path) -> bool:
                return path.name == "annotation_visual_review"

            with patch.object(Path, "is_symlink", marks_dedicated_as_link):
                with self.assertRaisesRegex(
                    AnnotationVisualReviewError,
                    "symlink or Windows reparse/junction",
                ):
                    validate_output_location(root, target)

            with patch.object(
                visual_review_module,
                "_has_windows_reparse_point",
                side_effect=lambda path: path.name == "annotation_visual_review",
            ):
                with self.assertRaisesRegex(
                    AnnotationVisualReviewError,
                    "symlink or Windows reparse/junction",
                ):
                    validate_output_location(root, target)


class VisualReviewBundleTests(unittest.TestCase):
    def test_complete_bundle_is_content_addressed_and_preserving(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            annotation_path, neutral_dir, video_path, payload = prepare_inputs(root)
            annotation_bytes = annotation_path.read_bytes()
            source_bytes = video_path.read_bytes()
            neutral_manifest_bytes = (neutral_dir / "manifest.json").read_bytes()
            neutral_hashes = {
                path.relative_to(neutral_dir).as_posix(): sha256_file(path)
                for path in neutral_dir.rglob("*")
                if path.is_file()
            }
            output_dir, manifest = prepare_annotation_visual_review(
                annotation_path,
                root,
                neutral_dir,
            )
            annotation_set = BallAnnotationSet.from_mapping(payload)
            components, digest = expected_bundle_identity(
                annotation_path,
                neutral_dir,
                payload,
            )
            self.assertEqual(output_dir.name, digest)
            self.assertEqual(
                manifest["bundle_input"],
                {"bundle_input_sha256": digest, **components},
            )
            self.assertEqual(
                manifest["generator"]["fingerprint"],
                generator_fingerprint(),
            )
            self.assertEqual(
                manifest["generator"]["fingerprint_sha256"],
                generator_fingerprint_sha256(generator_fingerprint()),
            )
            self.assertEqual(
                manifest["annotation"]["canonical_content_sha256"],
                canonical_annotation_sha256(annotation_set),
            )
            self.assertEqual(
                output_dir.relative_to(root).parts[:5],
                (
                    "data",
                    "outputs",
                    "ball_tracking",
                    "annotation_visual_review",
                    "possession_999",
                ),
            )
            self.assertEqual(
                (output_dir / "annotation_snapshot.json").read_bytes(),
                annotation_bytes,
            )
            self.assertEqual(
                (output_dir / "neutral_manifest_snapshot.json").read_bytes(),
                neutral_manifest_bytes,
            )
            self.assertEqual(
                manifest["neutral_bundle"]["snapshot"]["sha256"],
                hashlib.sha256(neutral_manifest_bytes).hexdigest(),
            )
            self.assertEqual(len(manifest["assets"]["overlay_frames"]), 25)
            self.assertEqual(len(manifest["assets"]["zoom_panels"]), 25)
            self.assertEqual(
                manifest["annotation"]["watermark"],
                "DRAFT JSON STATUS - HUMAN ANNOTATION VISUALIZATION",
            )
            self.assertEqual(
                manifest["annotation"]["review_status_statement"],
                "JSON status is draft; this visualization makes no "
                "inter-rater or repeatability claim",
            )
            self.assertTrue(manifest["safeguards"]["json_is_authoritative"])
            self.assertFalse(
                manifest["safeguards"][
                    "independent_adjudication_evidence_included"
                ]
            )
            self.assertFalse(
                manifest["safeguards"]["detector_outputs_included"]
            )
            self.assertEqual(
                manifest["assets"]["zoom_contact_sheet"]["purpose"],
                "context_only_not_for_pixel_geometry",
            )
            self.assertFalse(
                manifest["assets"]["zoom_contact_sheet"][
                    "pixel_geometry_review_allowed"
                ]
            )
            self.assertTrue(
                manifest["assets"]["zoom_contact_sheet"][
                    "aspect_preserving_letterbox"
                ]
            )
            playback_record = manifest["assets"]["overlay_playback"]
            self.assertEqual(
                playback_record["purpose"],
                "context_only_ordered_annotation_playback",
            )
            self.assertFalse(playback_record["pixel_geometry_review_allowed"])
            self.assertEqual(playback_record["last_frame_index"], 26)
            self.assertEqual(
                playback_record["deterministic_reference_validation"],
                "exact_mp4_bytes_regenerated_under_fingerprinted_runtime",
            )
            trajectory_record = manifest["assets"]["trajectory_diagnostics"]
            self.assertEqual(trajectory_record["missing_geometry_count"], 3)
            self.assertTrue(trajectory_record["has_any_missing_geometry"])
            self.assertTrue(
                trajectory_record["has_internal_geometry_discontinuities"]
            )
            self.assertFalse(trajectory_record["all_geometry_missing"])
            self.assertEqual(
                [
                    record["frame_index"]
                    for record in manifest["assets"]["overlay_frames"]
                ],
                list(range(2, 27)),
            )
            self.assertEqual(
                [
                    record["frame_index"]
                    for record in manifest["assets"]["zoom_panels"]
                ],
                list(range(2, 27)),
            )
            final_overlay = manifest["assets"]["overlay_frames"][-1]
            final_neutral = json.loads(neutral_manifest_bytes)["assets"][
                "source_frames"
            ][-1]
            self.assertEqual(final_overlay["frame_index"], 26)
            self.assertEqual(
                final_overlay["path"],
                "overlay_frames/frame_000026.png",
            )
            self.assertEqual(
                final_overlay["source_frame_sha256"],
                final_neutral["sha256"],
            )
            self.assertEqual(
                json.loads(
                    (output_dir / "annotation_snapshot.json").read_bytes()
                )["annotations"][-1]["frame_index"],
                26,
            )
            overlay_paths = sorted((output_dir / "overlay_frames").glob("*.png"))
            zoom_paths = sorted((output_dir / "zoom_panels").glob("*.png"))
            self.assertEqual(len(overlay_paths), EXPECTED_FRAME_COUNT)
            self.assertEqual(len(zoom_paths), EXPECTED_FRAME_COUNT)
            self.assertEqual(cv2.imread(str(overlay_paths[0])).shape[:2], (180, 320))
            self.assertEqual(
                cv2.imread(str(zoom_paths[0])).shape[:2],
                (ZOOM_PANEL_HEIGHT_PX, ZOOM_PANEL_WIDTH_PX),
            )
            contact = cv2.imread(
                str(output_dir / "annotation_zoom_contact_sheet.png")
            )
            self.assertEqual(
                contact.shape[0],
                CONTACT_HEADER_HEIGHT_PX + CONTACT_ROWS * CONTACT_TILE_HEIGHT_PX,
            )
            trajectory = cv2.imread(str(output_dir / "trajectory_diagnostics.png"))
            self.assertEqual(
                trajectory.shape[:2],
                (TRAJECTORY_HEIGHT_PX, TRAJECTORY_WIDTH_PX),
            )
            playback = cv2.VideoCapture(
                str(output_dir / "annotation_overlay_slow.mp4")
            )
            try:
                count = 0
                while playback.read()[0]:
                    count += 1
                fps = playback.get(cv2.CAP_PROP_FPS)
            finally:
                playback.release()
            self.assertEqual(count, 25)
            self.assertAlmostEqual(fps, 5.0, places=1)
            self.assertEqual(annotation_path.read_bytes(), annotation_bytes)
            self.assertEqual(video_path.read_bytes(), source_bytes)
            self.assertEqual(
                {
                    path.relative_to(neutral_dir).as_posix(): sha256_file(path)
                    for path in neutral_dir.rglob("*")
                    if path.is_file()
                },
                neutral_hashes,
            )

    def test_unlabeled_input_fails_before_visual_output_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            annotation_path, neutral_dir, _video, payload = prepare_inputs(root)
            payload["annotations"][10] = base_payload(
                root / "data" / "clips" / "visual_review.avi", root
            )["annotations"][10]
            write_json(annotation_path, payload)
            with self.assertRaisesRegex(AnnotationVisualReviewError, "unlabeled"):
                prepare_annotation_visual_review(annotation_path, root, neutral_dir)
            output_root = (
                root
                / "data"
                / "outputs"
                / "ball_tracking"
                / "annotation_visual_review"
            )
            self.assertFalse(output_root.exists())

    def test_annotation_change_during_render_prevents_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            annotation_path, neutral_dir, _video, payload = prepare_inputs(root)
            _components, digest = expected_bundle_identity(
                annotation_path,
                neutral_dir,
                payload,
            )
            expected_output = output_window(root) / digest

            original_build = visual_review_module._build_bundle

            def build_then_change(*args, **kwargs):
                manifest = original_build(*args, **kwargs)
                annotation_path.write_bytes(annotation_path.read_bytes() + b"\n")
                return manifest

            with patch.object(
                visual_review_module,
                "_build_bundle",
                side_effect=build_then_change,
            ):
                with self.assertRaisesRegex(
                    AnnotationVisualReviewError,
                    "annotation JSON changed",
                ):
                    prepare_annotation_visual_review(
                        annotation_path,
                        root,
                        neutral_dir,
                    )
            self.assertFalse(expected_output.exists())
            self.assertEqual(list(output_window(root).glob(".*.staging-*")), [])

    def test_source_change_during_render_prevents_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            annotation_path, neutral_dir, video_path, payload = prepare_inputs(root)
            _components, digest = expected_bundle_identity(
                annotation_path,
                neutral_dir,
                payload,
            )
            expected_output = output_window(root) / digest

            original_build = visual_review_module._build_bundle

            def build_then_change(*args, **kwargs):
                manifest = original_build(*args, **kwargs)
                video_path.write_bytes(video_path.read_bytes() + b"changed")
                return manifest

            with patch.object(
                visual_review_module,
                "_build_bundle",
                side_effect=build_then_change,
            ):
                with self.assertRaisesRegex(
                    AnnotationVisualReviewError,
                    "source video changed",
                ):
                    prepare_annotation_visual_review(
                        annotation_path,
                        root,
                        neutral_dir,
                    )
            self.assertFalse(expected_output.exists())
            self.assertEqual(list(output_window(root).glob(".*.staging-*")), [])

    def test_exact_neutral_manifest_change_during_render_prevents_publication(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            annotation_path, neutral_dir, _video, payload = prepare_inputs(root)
            neutral_manifest_path = neutral_dir / "manifest.json"
            original_neutral_bytes = neutral_manifest_path.read_bytes()
            _components, digest = expected_bundle_identity(
                annotation_path,
                neutral_dir,
                payload,
            )
            expected_output = output_window(root) / digest
            original_build = visual_review_module._build_bundle

            def build_then_reformat_neutral(*args, **kwargs):
                manifest = original_build(*args, **kwargs)
                neutral_manifest_path.write_bytes(original_neutral_bytes + b"\n")
                return manifest

            with patch.object(
                visual_review_module,
                "_build_bundle",
                side_effect=build_then_reformat_neutral,
            ):
                with self.assertRaisesRegex(
                    AnnotationVisualReviewError,
                    "neutral bundle changed during generation",
                ):
                    prepare_annotation_visual_review(
                        annotation_path,
                        root,
                        neutral_dir,
                    )
            self.assertFalse(expected_output.exists())
            self.assertEqual(
                neutral_manifest_path.read_bytes(),
                original_neutral_bytes + b"\n",
            )
            self.assertEqual(list(output_window(root).glob(".*.staging-*")), [])

    def test_codec_failure_is_wrapped_and_staging_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            annotation_path, neutral_dir, video_path, payload = prepare_inputs(root)
            annotation_bytes = annotation_path.read_bytes()
            source_bytes = video_path.read_bytes()
            _components, digest = expected_bundle_identity(
                annotation_path,
                neutral_dir,
                payload,
            )
            with patch.object(
                visual_review_module,
                "_write_slow_playback",
                side_effect=ReviewAssetPreparationError("synthetic codec failure"),
            ):
                with self.assertRaisesRegex(
                    AnnotationVisualReviewError,
                    "review asset operation failed: synthetic codec failure",
                ):
                    prepare_annotation_visual_review(
                        annotation_path,
                        root,
                        neutral_dir,
                    )
            self.assertFalse((output_window(root) / digest).exists())
            self.assertEqual(list(output_window(root).glob(".*.staging-*")), [])
            self.assertEqual(annotation_path.read_bytes(), annotation_bytes)
            self.assertEqual(video_path.read_bytes(), source_bytes)

    def test_tampered_neutral_bundle_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            annotation_path, neutral_dir, _video, _payload = prepare_inputs(root)
            neutral_frame = next((neutral_dir / "source_frames").glob("*.png"))
            neutral_frame.write_bytes(neutral_frame.read_bytes() + b"tamper")
            with self.assertRaisesRegex(
                AnnotationVisualReviewError,
                "neutral bundle validation failed",
            ):
                prepare_annotation_visual_review(annotation_path, root, neutral_dir)

    def test_coherently_rehashed_neutral_pixel_tamper_fails_source_proof(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            annotation_path, neutral_dir, video_path, _payload = prepare_inputs(root)
            annotation_bytes = annotation_path.read_bytes()
            source_bytes = video_path.read_bytes()
            manifest_path = neutral_dir / "manifest.json"
            neutral_manifest = json.loads(manifest_path.read_bytes())
            record = neutral_manifest["assets"]["source_frames"][0]
            neutral_frame_path = neutral_dir / Path(record["path"])
            frame = cv2.imread(str(neutral_frame_path), cv2.IMREAD_COLOR)
            self.assertIsNotNone(frame)
            frame[0, 0, 0] ^= 255
            self.assertTrue(
                cv2.imwrite(
                    str(neutral_frame_path),
                    frame,
                    [cv2.IMWRITE_PNG_COMPRESSION, 3],
                )
            )
            record["sha256"] = sha256_file(neutral_frame_path)
            record["byte_size"] = neutral_frame_path.stat().st_size
            write_json(manifest_path, neutral_manifest)
            tampered_frame_bytes = neutral_frame_path.read_bytes()
            tampered_manifest_bytes = manifest_path.read_bytes()

            with self.assertRaisesRegex(
                AnnotationVisualReviewError,
                "does not pixel-match verified sequential source",
            ):
                prepare_annotation_visual_review(annotation_path, root, neutral_dir)

            self.assertEqual(annotation_path.read_bytes(), annotation_bytes)
            self.assertEqual(video_path.read_bytes(), source_bytes)
            self.assertEqual(neutral_frame_path.read_bytes(), tampered_frame_bytes)
            self.assertEqual(manifest_path.read_bytes(), tampered_manifest_bytes)
            self.assertFalse(output_window(root).exists())

    def test_reuse_succeeds_but_tampering_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            annotation_path, neutral_dir, _video, _payload = prepare_inputs(root)
            output_dir, first_manifest = prepare_annotation_visual_review(
                annotation_path, root, neutral_dir
            )
            original_manifest_bytes = (output_dir / "manifest.json").read_bytes()
            reused_dir, reused_manifest = prepare_annotation_visual_review(
                annotation_path, root, neutral_dir
            )
            self.assertEqual(reused_dir, output_dir)
            self.assertEqual(reused_manifest, first_manifest)
            self.assertEqual(
                (output_dir / "manifest.json").read_bytes(),
                original_manifest_bytes,
            )

            overlay_path = next((output_dir / "overlay_frames").glob("*.png"))
            tampered_content = bytearray(overlay_path.read_bytes())
            tampered_content[-1] ^= 1
            tampered_overlay_bytes = bytes(tampered_content)
            overlay_path.write_bytes(tampered_overlay_bytes)
            with self.assertRaisesRegex(AnnotationVisualReviewError, "SHA-256"):
                prepare_annotation_visual_review(annotation_path, root, neutral_dir)
            self.assertEqual(overlay_path.read_bytes(), tampered_overlay_bytes)
            self.assertEqual(
                (output_dir / "manifest.json").read_bytes(),
                original_manifest_bytes,
            )

    def test_reuse_rejects_foreign_overlay_with_coherently_rehashed_manifest(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            annotation_path, neutral_dir, _video, _payload = prepare_inputs(root)
            output_dir, _manifest = prepare_annotation_visual_review(
                annotation_path,
                root,
                neutral_dir,
            )
            manifest_path = output_dir / "manifest.json"
            tampered = json.loads(manifest_path.read_bytes())
            overlay_records = tampered["assets"]["overlay_frames"]
            target_path = output_dir / Path(overlay_records[0]["path"])
            foreign_path = output_dir / Path(overlay_records[1]["path"])
            target_path.write_bytes(foreign_path.read_bytes())
            overlay_records[0]["sha256"] = sha256_file(target_path)
            overlay_records[0]["byte_size"] = target_path.stat().st_size
            tampered_bytes = write_json(manifest_path, tampered)
            foreign_bytes = target_path.read_bytes()

            with self.assertRaisesRegex(
                AnnotationVisualReviewError,
                "does not match the deterministic generator output",
            ):
                prepare_annotation_visual_review(annotation_path, root, neutral_dir)
            self.assertEqual(manifest_path.read_bytes(), tampered_bytes)
            self.assertEqual(target_path.read_bytes(), foreign_bytes)

    def test_reuse_rerenders_every_derived_png_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            annotation_path, neutral_dir, _video, _payload = prepare_inputs(root)
            output_dir, original_manifest = prepare_annotation_visual_review(
                annotation_path,
                root,
                neutral_dir,
            )
            manifest_path = output_dir / "manifest.json"
            original_manifest_bytes = manifest_path.read_bytes()
            cases = (
                (
                    "zoom panel",
                    original_manifest["assets"]["zoom_panels"][0],
                ),
                (
                    "contact sheet",
                    original_manifest["assets"]["zoom_contact_sheet"],
                ),
                (
                    "trajectory diagnostic",
                    original_manifest["assets"]["trajectory_diagnostics"],
                ),
            )
            for expected_error, original_record in cases:
                with self.subTest(asset=expected_error):
                    asset_path = output_dir / Path(original_record["path"])
                    original_asset_bytes = asset_path.read_bytes()
                    image = cv2.imread(str(asset_path), cv2.IMREAD_COLOR)
                    self.assertIsNotNone(image)
                    image[image.shape[0] // 2, image.shape[1] // 2, 0] ^= 255
                    self.assertTrue(cv2.imwrite(str(asset_path), image))
                    tampered = json.loads(original_manifest_bytes)
                    if expected_error == "zoom panel":
                        record = tampered["assets"]["zoom_panels"][0]
                    elif expected_error == "contact sheet":
                        record = tampered["assets"]["zoom_contact_sheet"]
                    else:
                        record = tampered["assets"]["trajectory_diagnostics"]
                    record["sha256"] = sha256_file(asset_path)
                    record["byte_size"] = asset_path.stat().st_size
                    tampered_manifest_bytes = write_json(manifest_path, tampered)

                    with self.assertRaisesRegex(
                        AnnotationVisualReviewError,
                        expected_error,
                    ):
                        prepare_annotation_visual_review(
                            annotation_path,
                            root,
                            neutral_dir,
                        )
                    self.assertEqual(
                        manifest_path.read_bytes(),
                        tampered_manifest_bytes,
                    )
                    asset_path.write_bytes(original_asset_bytes)
                    manifest_path.write_bytes(original_manifest_bytes)

    def test_reuse_requires_exact_current_generator_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            annotation_path, neutral_dir, _video, _payload = prepare_inputs(root)
            output_dir, _manifest = prepare_annotation_visual_review(
                annotation_path,
                root,
                neutral_dir,
            )
            manifest_path = output_dir / "manifest.json"
            tampered = json.loads(manifest_path.read_bytes())
            tampered["generator"]["fingerprint"][
                "annotation_review_module_sha256"
            ] = "0" * 64
            tampered_bytes = write_json(manifest_path, tampered)

            with self.assertRaisesRegex(
                AnnotationVisualReviewError,
                "generator fingerprint",
            ):
                prepare_annotation_visual_review(annotation_path, root, neutral_dir)
            self.assertEqual(manifest_path.read_bytes(), tampered_bytes)

    def test_reuse_rejects_reordered_replaced_and_local_playback_tamper(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            annotation_path, neutral_dir, _video, _payload = prepare_inputs(root)
            output_dir, original_manifest = prepare_annotation_visual_review(
                annotation_path,
                root,
                neutral_dir,
            )
            manifest_path = output_dir / "manifest.json"
            original_manifest_bytes = manifest_path.read_bytes()
            playback_record = original_manifest["assets"]["overlay_playback"]
            playback_path = output_dir / Path(playback_record["path"])
            original_playback_bytes = playback_path.read_bytes()
            overlays = [
                cv2.imread(
                    str(output_dir / Path(record["path"])),
                    cv2.IMREAD_COLOR,
                )
                for record in original_manifest["assets"]["overlay_frames"]
            ]
            self.assertTrue(all(frame is not None for frame in overlays))

            def write_tampered_playback(frames: list[np.ndarray]) -> bytes:
                codec = visual_review_module._write_slow_playback(
                    playback_path,
                    frames,
                    320,
                    180,
                    5.0,
                )
                tampered = json.loads(original_manifest_bytes)
                record = tampered["assets"]["overlay_playback"]
                record["codec_fourcc"] = codec
                record["sha256"] = sha256_file(playback_path)
                record["byte_size"] = playback_path.stat().st_size
                return write_json(manifest_path, tampered)

            reversed_manifest_bytes = write_tampered_playback(
                list(reversed(overlays))
            )
            reversed_playback_bytes = playback_path.read_bytes()
            with self.assertRaisesRegex(
                AnnotationVisualReviewError,
                "playback semantic frame order",
            ):
                prepare_annotation_visual_review(annotation_path, root, neutral_dir)
            self.assertEqual(manifest_path.read_bytes(), reversed_manifest_bytes)
            self.assertEqual(playback_path.read_bytes(), reversed_playback_bytes)

            playback_path.write_bytes(original_playback_bytes)
            manifest_path.write_bytes(original_manifest_bytes)
            replaced_frames = list(overlays)
            replaced_frames[-1] = overlays[0]
            replaced_manifest_bytes = write_tampered_playback(replaced_frames)
            replaced_playback_bytes = playback_path.read_bytes()
            with self.assertRaisesRegex(
                AnnotationVisualReviewError,
                "final playback frame",
            ):
                prepare_annotation_visual_review(annotation_path, root, neutral_dir)
            self.assertEqual(manifest_path.read_bytes(), replaced_manifest_bytes)
            self.assertEqual(playback_path.read_bytes(), replaced_playback_bytes)

            playback_path.write_bytes(original_playback_bytes)
            manifest_path.write_bytes(original_manifest_bytes)
            localized_frames = list(overlays)
            localized_final = overlays[-1].copy()
            cv2.rectangle(
                localized_final,
                (150, 80),
                (152, 82),
                (255, 0, 255),
                -1,
            )
            localized_frames[-1] = localized_final
            localized_manifest_bytes = write_tampered_playback(localized_frames)
            localized_playback_bytes = playback_path.read_bytes()
            with self.assertRaisesRegex(
                AnnotationVisualReviewError,
                "deterministic reference encode",
            ):
                prepare_annotation_visual_review(annotation_path, root, neutral_dir)
            self.assertEqual(manifest_path.read_bytes(), localized_manifest_bytes)
            self.assertEqual(playback_path.read_bytes(), localized_playback_bytes)

    def test_reviewed_input_uses_distinct_digest_and_reviewed_watermark(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            annotation_path, neutral_dir, _video, payload = prepare_inputs(root)
            reviewed = complete_payload(payload, reviewed=True)
            write_json(annotation_path, reviewed)
            output_dir, manifest = prepare_annotation_visual_review(
                annotation_path, root, neutral_dir
            )
            self.assertEqual(
                manifest["annotation"]["watermark"],
                "REVIEWED JSON STATUS - HUMAN ANNOTATION VISUALIZATION",
            )
            self.assertEqual(
                manifest["annotation"]["review_status_statement"],
                "JSON status is reviewed; this visualization makes no "
                "inter-rater or repeatability claim",
            )
            self.assertFalse(
                manifest["safeguards"][
                    "independent_adjudication_evidence_included"
                ]
            )
            _components, expected_digest = expected_bundle_identity(
                annotation_path,
                neutral_dir,
                reviewed,
            )
            self.assertEqual(
                output_dir.name,
                expected_digest,
            )


if __name__ == "__main__":
    unittest.main()
