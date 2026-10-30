import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

import src.ball_tracking.prepare_annotation_review as review_module
from src.ball_tracking.annotations import AnnotationValidationError
from src.ball_tracking.prepare_annotation_review import (
    OVERVIEW_COLUMNS,
    OVERVIEW_HEADER_HEIGHT_PX,
    OVERVIEW_ROWS,
    OVERVIEW_TILE_HEIGHT_PX,
    OVERVIEW_TILE_WIDTH_PX,
    ReviewAssetPreparationError,
    prepare_annotation_review,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_synthetic_video(
    root,
    *,
    frame_count=30,
    width_px=64,
    height_px=48,
    fps=10.0,
):
    video_path = root / "data" / "clips" / "synthetic.avi"
    video_path.parent.mkdir(parents=True)
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        fps,
        (width_px, height_px),
    )

    if not writer.isOpened():
        raise RuntimeError("Synthetic MJPG writer is unavailable")

    try:
        for frame_index in range(frame_count):
            frame = np.zeros((height_px, width_px, 3), dtype=np.uint8)
            frame[:, :, 0] = frame_index * 7 % 256
            frame[:, :, 1] = np.arange(width_px, dtype=np.uint8)
            frame[:, :, 2] = np.arange(height_px, dtype=np.uint8)[:, None]
            writer.write(frame)
    finally:
        writer.release()

    return video_path


def annotation_payload(
    video_path,
    root,
    *,
    start_frame_index=2,
    end_frame_index=26,
    sha256=None,
):
    capture = cv2.VideoCapture(str(video_path))

    if not capture.isOpened():
        raise RuntimeError("Could not probe synthetic video")

    try:
        width_px = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height_px = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    finally:
        capture.release()

    return {
        "schema_version": "0.1",
        "annotation_set_id": "synthetic_ball_review",
        "possession_id": "possession_999",
        "source_video": {
            "path": video_path.relative_to(root).as_posix(),
            "sha256": sha256 or sha256_file(video_path),
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
            for frame_index in range(
                start_frame_index,
                end_frame_index + 1,
            )
        ],
    }


def write_annotations(root, payload):
    annotation_path = root / "annotations.json"
    annotation_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    return annotation_path


def decode_frame(video_path, target_index):
    capture = cv2.VideoCapture(str(video_path))

    try:
        for frame_index in range(target_index + 1):
            success, frame = capture.read()

            if not success:
                raise RuntimeError(f"Decode failed at frame {frame_index}")
    finally:
        capture.release()

    return frame


def review_output(root, name="review_bundle"):
    return root / "data" / "outputs" / "ball_tracking" / name


class BallAnnotationReviewAssetTests(unittest.TestCase):
    def test_complete_bundle_is_native_neutral_and_source_bound(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video_path = write_synthetic_video(root)
            annotation_path = write_annotations(
                root,
                annotation_payload(video_path, root),
            )
            original_annotation_bytes = annotation_path.read_bytes()
            output_dir = review_output(root)
            manifest = prepare_annotation_review(
                annotation_path,
                root,
                output_dir,
            )

            self.assertEqual(
                annotation_path.read_bytes(),
                original_annotation_bytes,
            )
            source_frame_paths = sorted(
                (output_dir / "source_frames").glob("*.png")
            )
            self.assertEqual(len(source_frame_paths), 25)
            self.assertEqual(
                source_frame_paths[0].name,
                "frame_000002.png",
            )
            self.assertEqual(
                source_frame_paths[-1].name,
                "frame_000026.png",
            )
            expected_frame = decode_frame(video_path, 2)
            written_frame = cv2.imread(str(source_frame_paths[0]))
            self.assertTrue(np.array_equal(written_frame, expected_frame))
            overview = cv2.imread(
                str(output_dir / "context_only_overview.png")
            )
            self.assertEqual(
                overview.shape[:2],
                (
                    OVERVIEW_HEADER_HEIGHT_PX
                    + OVERVIEW_ROWS * OVERVIEW_TILE_HEIGHT_PX,
                    OVERVIEW_COLUMNS * OVERVIEW_TILE_WIDTH_PX,
                ),
            )
            playback = cv2.VideoCapture(
                str(output_dir / "slow_playback.mp4")
            )

            try:
                playback_count = 0

                while playback.read()[0]:
                    playback_count += 1

                playback_fps = playback.get(cv2.CAP_PROP_FPS)
            finally:
                playback.release()

            self.assertEqual(playback_count, 25)
            self.assertAlmostEqual(playback_fps, 5.0, places=1)
            manifest_on_disk = json.loads(
                (output_dir / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest_on_disk, manifest)
            self.assertEqual(
                manifest["annotation_set"]["annotation_content_sha256"],
                hashlib.sha256(original_annotation_bytes).hexdigest(),
            )
            self.assertEqual(
                manifest["source_video"]["sha256"],
                sha256_file(video_path),
            )
            self.assertEqual(manifest["window"]["frame_count"], 25)
            self.assertEqual(
                manifest["window"]["decode_method"],
                "sequential_from_frame_zero_no_random_seek",
            )
            self.assertFalse(
                manifest["assets"]["context_overview"][
                    "pixel_annotation_allowed"
                ]
            )
            self.assertFalse(
                manifest["assets"]["slow_playback"][
                    "contains_detector_hints"
                ]
            )

            for asset in manifest["assets"]["source_frames"]:
                asset_path = output_dir / asset["path"]
                self.assertEqual(asset["sha256"], sha256_file(asset_path))
                self.assertEqual(asset["encoding"], "lossless_png")

    def test_late_annotation_mutation_refuses_publication(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video_path = write_synthetic_video(root)
            annotation_path = write_annotations(
                root,
                annotation_payload(video_path, root),
            )
            output_dir = review_output(root)
            original_build_bundle = review_module._build_bundle

            def mutate_annotation_then_build(*args, **kwargs):
                annotation_path.write_bytes(annotation_path.read_bytes() + b" ")
                return original_build_bundle(*args, **kwargs)

            with patch(
                "src.ball_tracking.prepare_annotation_review._build_bundle",
                side_effect=mutate_annotation_then_build,
            ), self.assertRaisesRegex(
                ReviewAssetPreparationError,
                "Annotation JSON changed",
            ):
                prepare_annotation_review(
                    annotation_path,
                    root,
                    output_dir,
                )

            self.assertFalse(output_dir.exists())
            self.assertEqual(
                list(output_dir.parent.glob(".review_bundle.staging-*")),
                [],
            )

    def test_late_source_mutation_refuses_publication(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video_path = write_synthetic_video(root)
            annotation_path = write_annotations(
                root,
                annotation_payload(video_path, root),
            )
            output_dir = review_output(root)
            original_build_bundle = review_module._build_bundle

            def mutate_source_then_build(*args, **kwargs):
                video_path.write_bytes(video_path.read_bytes() + b"changed")
                return original_build_bundle(*args, **kwargs)

            with patch(
                "src.ball_tracking.prepare_annotation_review._build_bundle",
                side_effect=mutate_source_then_build,
            ), self.assertRaisesRegex(
                ReviewAssetPreparationError,
                "Source video changed",
            ):
                prepare_annotation_review(
                    annotation_path,
                    root,
                    output_dir,
                )

            self.assertFalse(output_dir.exists())
            self.assertEqual(
                list(output_dir.parent.glob(".review_bundle.staging-*")),
                [],
            )

    def test_nonempty_output_requires_overwrite_and_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video_path = write_synthetic_video(root)
            annotation_path = write_annotations(
                root,
                annotation_payload(video_path, root),
            )
            output_dir = review_output(root)
            output_dir.parent.mkdir(parents=True)
            output_dir.mkdir()
            sentinel = output_dir / "keep.txt"
            sentinel.write_text("keep", encoding="utf-8")

            with self.assertRaisesRegex(
                ReviewAssetPreparationError,
                "nonempty",
            ):
                prepare_annotation_review(
                    annotation_path,
                    root,
                    output_dir,
                )

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_overwrite_replaces_existing_directory_after_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video_path = write_synthetic_video(root)
            annotation_path = write_annotations(
                root,
                annotation_payload(video_path, root),
            )
            output_dir = review_output(root)
            prepare_annotation_review(
                annotation_path,
                root,
                output_dir,
            )
            prepare_annotation_review(
                annotation_path,
                root,
                output_dir,
                overwrite=True,
            )

            self.assertTrue((output_dir / "manifest.json").is_file())
            self.assertEqual(
                len(list((output_dir / "source_frames").glob("*.png"))),
                25,
            )

    def test_source_mismatch_and_non_25_frame_window_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video_path = write_synthetic_video(root)
            mismatched_path = write_annotations(
                root,
                annotation_payload(video_path, root, sha256="0" * 64),
            )

            with self.assertRaisesRegex(
                AnnotationValidationError,
                "SHA-256 does not match",
            ):
                prepare_annotation_review(
                    mismatched_path,
                    root,
                    review_output(root, "mismatched_output"),
                )

            short_payload = annotation_payload(
                video_path,
                root,
                start_frame_index=2,
                end_frame_index=25,
            )
            short_path = write_annotations(root, short_payload)

            with self.assertRaisesRegex(
                ReviewAssetPreparationError,
                "exactly 25 frames",
            ):
                prepare_annotation_review(
                    short_path,
                    root,
                    review_output(root, "short_output"),
                )

            self.assertFalse(review_output(root, "mismatched_output").exists())
            self.assertFalse(review_output(root, "short_output").exists())

    def test_codec_failure_is_explicit_and_keeps_old_output(self):
        class ClosedWriter:
            def isOpened(self):
                return False

            def release(self):
                pass

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video_path = write_synthetic_video(root)
            annotation_path = write_annotations(
                root,
                annotation_payload(video_path, root),
            )
            output_dir = review_output(root)
            prepare_annotation_review(
                annotation_path,
                root,
                output_dir,
            )
            original_manifest = (output_dir / "manifest.json").read_bytes()

            with patch(
                "src.ball_tracking.prepare_annotation_review.cv2.VideoWriter",
                return_value=ClosedWriter(),
            ), self.assertRaisesRegex(
                ReviewAssetPreparationError,
                "No tested MP4 codec",
            ):
                prepare_annotation_review(
                    annotation_path,
                    root,
                    output_dir,
                    overwrite=True,
                )

            self.assertEqual(
                (output_dir / "manifest.json").read_bytes(),
                original_manifest,
            )
            self.assertEqual(
                list(output_dir.parent.glob(".review_bundle.staging-*")),
                [],
            )

    def test_overwrite_refuses_sentinel_only_broad_descendant(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video_path = write_synthetic_video(root)
            annotation_path = write_annotations(
                root,
                annotation_payload(video_path, root),
            )
            output_dir = review_output(root, "broad/descendant")
            output_dir.mkdir(parents=True)
            sentinel = output_dir / "keep.txt"
            sentinel.write_text("keep", encoding="utf-8")

            with self.assertRaisesRegex(
                ReviewAssetPreparationError,
                "owned ball annotation review bundle",
            ):
                prepare_annotation_review(
                    annotation_path,
                    root,
                    output_dir,
                    overwrite=True,
                )

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_overwrite_refuses_mismatched_valid_bundle_identity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video_path = write_synthetic_video(root)
            annotation_path = write_annotations(
                root,
                annotation_payload(video_path, root),
            )
            output_dir = review_output(root)
            prepare_annotation_review(annotation_path, root, output_dir)
            original_manifest = (output_dir / "manifest.json").read_bytes()
            changed_payload = annotation_payload(video_path, root)
            changed_payload["annotation_set_id"] = "different_ball_review"
            write_annotations(root, changed_payload)

            with self.assertRaisesRegex(
                ReviewAssetPreparationError,
                "annotation identity does not match",
            ):
                prepare_annotation_review(
                    annotation_path,
                    root,
                    output_dir,
                    overwrite=True,
                )

            self.assertEqual(
                (output_dir / "manifest.json").read_bytes(),
                original_manifest,
            )

    def test_overwrite_refuses_bundle_with_extra_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video_path = write_synthetic_video(root)
            annotation_path = write_annotations(
                root,
                annotation_payload(video_path, root),
            )
            output_dir = review_output(root)
            prepare_annotation_review(annotation_path, root, output_dir)
            extra_path = output_dir / "notes" / "do_not_delete.txt"
            extra_path.parent.mkdir()
            extra_path.write_text("user artifact", encoding="utf-8")

            with self.assertRaisesRegex(
                ReviewAssetPreparationError,
                "unrecognized artifacts",
            ):
                prepare_annotation_review(
                    annotation_path,
                    root,
                    output_dir,
                    overwrite=True,
                )

            self.assertEqual(
                extra_path.read_text(encoding="utf-8"),
                "user artifact",
            )

    def test_output_must_be_below_ball_tracking_generated_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video_path = write_synthetic_video(root)
            annotation_path = write_annotations(
                root,
                annotation_payload(video_path, root),
            )
            allowed_root = root / "data" / "outputs" / "ball_tracking"
            rejected_paths = (
                allowed_root,
                root,
                root / "unrelated" / "review_bundle",
                root / "data" / "outputs" / "other" / "review_bundle",
            )

            for rejected_path in rejected_paths:
                with self.subTest(output_dir=rejected_path):
                    with self.assertRaisesRegex(
                        ReviewAssetPreparationError,
                        "strict descendant",
                    ):
                        prepare_annotation_review(
                            annotation_path,
                            root,
                            rejected_path,
                            overwrite=True,
                        )

    def test_cli_help_lists_required_contract(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.ball_tracking.prepare_annotation_review",
                "--help",
            ],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertIn("--annotations", result.stdout)
        self.assertIn("--repository-root", result.stdout)
        self.assertIn("--output-dir", result.stdout)
        self.assertIn("--overwrite", result.stdout)


if __name__ == "__main__":
    unittest.main()
