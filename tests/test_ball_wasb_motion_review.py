"""Actual source/video checks for candidate-only comparison evidence."""
from __future__ import annotations

import copy
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import cv2
import numpy as np

from src.ball_tracking import wasb_development_observation as observation
from src.ball_tracking import wasb_motion_review as review
from src.ball_tracking.wasb_experiment import digest_file, read_json


@unittest.skipUnless(shutil.which("ffmpeg"), "Requires ffmpeg for actual H264 evidence")
class MotionReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.config = {"rendering": {"playback_fps": 25, "crf": 18}}
        self.output = self.root / "data/outputs/comparison/possession_002"

    def fixture(self, count=9):
        path = self.root / "data/clips/artificial.mp4"
        path.parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 25, (512, 288))
        self.assertTrue(writer.isOpened())
        for index in range(count):
            image = np.full((288, 512, 3), 30 + index * 15, dtype=np.uint8)
            # A different permanent patch makes accidental panel swaps visible.
            image[200:250, 400:450] = (20 + index * 10, 70, 150)
            writer.write(image)
        writer.release()
        player_path = self.root / "data/outputs/identity/artificial.csv"
        player_path.parent.mkdir(parents=True)
        player_path.write_text("frame_index,player_id,floor_x,floor_y\n0,P0,300,150\n1,P1,300,170\n",
                               encoding="utf-8")
        source = {"path": path.relative_to(self.root).as_posix(), "sha256": digest_file(path),
                  "width_px": 512, "height_px": 288, "fps": 25.0, "frame_count": count}
        pos = {"possession_id": "possession_002", "source_video": source,
               "protected_ranges": [[3, 5]], "visible_segments": [[0, 2]] + ([[6, 8]] if count == 9 else []),
               "player_context": observation.binding(self.root, player_path)}
        segments = []
        for a, b in pos["visible_segments"]:
            means = np.zeros((b - a + 1, 288, 512), dtype=np.float32)
            for offset in range(b - a + 1):
                means[offset, 70:73, 100 + offset:103 + offset] = .8
                means[offset, 110:112, 200 + offset:202 + offset] = .5
            segments.append({"segment": [a, b], "frames": observation.observed_frames(
                means, [1] * (b - a + 1), a, source, .3)})
        frames = observation.make_timeline(pos, segments, [])
        for row in frames:
            row["baseline_center_xy_px"] = copy.deepcopy(row["center_xy_px"])
            row["baseline_candidate_index"] = row["selected_candidate_index"]
        alternate = frames[1]["candidates"][1]
        frames[1].update(center_xy_px=[alternate["center_x"], alternate["center_y"]],
                         selected_candidate_index=alternate["candidate_index"], is_training_frame=True)
        for index in [2] + ([8] if count == 9 else []):
            frames[index].update(state="missing", center_xy_px=None, selected_candidate_index=None)
        return pos, {"source_video": source, "frames": frames}

    def test_actual_source_synced_panels_all_changed_stills_final_frame_and_resume(self):
        pos, timeline = self.fixture()
        requested = []
        original = observation.decode_segment

        def record(root, declared, segment):
            for index, image in original(root, declared, segment):
                requested.append(index)
                yield index, image

        with mock.patch.object(observation, "decode_segment", side_effect=record):
            result = review.render_comparison(self.root, self.config, pos, timeline, self.output)
        self.assertEqual(requested, [0, 1, 2, 6, 7, 8])
        self.assertEqual(result["changed_frame_indices"], [1, 2, 8])
        self.assertEqual(result["known_cue_frame_indices"], [2])
        self.assertEqual([s["frame_index"] for s in result["stills"]], [1, 2, 8])
        self.assertEqual(result["verification"], {"decoded_frames": 9, "final_frame_index": 8,
            "final_frame_decoded": True, "playback_fps": 25., "protected_frame_pairs_verified_black": 3})
        capture = cv2.VideoCapture(str(self.root / result["video"]["path"]))
        for index in range(9):
            ok, image = capture.read()
            self.assertTrue(ok)
            self.assertEqual(image.shape, (448, 1024, 3))
            if 3 <= index <= 5:
                self.assertLessEqual(int(image[review.HEADER_HEIGHT:].max()), 3)
            else:
                # Read the independent source video to compare frame identity.
                source = cv2.VideoCapture(str(self.root / pos["source_video"]["path"]))
                source.set(cv2.CAP_PROP_POS_FRAMES, index)
                ok, expected = source.read()
                source.release()
                self.assertTrue(ok)
                for offset in (0, 512):
                    actual_patch = image[review.HEADER_HEIGHT + 200:review.HEADER_HEIGHT + 250,
                                         offset + 400:offset + 450].astype(float)
                    self.assertLess(float(np.abs(actual_patch - expected[200:250, 400:450]).mean()), 5)
        self.assertFalse(capture.read()[0])
        capture.release()
        final = cv2.imread(str(self.root / result["decoded_final_frame"]["path"]))
        self.assertEqual(final.shape, (448, 1024, 3))
        self.assertGreater(float(final[200:250, 20:50].mean()), 130)
        # A still has each source panel at its original resolution and two different selections.
        still = cv2.imread(str(self.root / result["stills"][0]["image"]["path"]))
        row = timeline["frames"][1]
        for offset, center in ((0, row["baseline_center_xy_px"]), (512, row["center_xy_px"])):
            x, y = map(round, center)
            np.testing.assert_array_equal(still[review.HEADER_HEIGHT + y, offset + x], [240, 80, 240])
        self.assertIsNone(result["selected_operating_point"])
        self.assertEqual(result["human_visual_review"], "pending")
        with mock.patch.object(observation, "decode_segment", side_effect=AssertionError("No render on resume")):
            self.assertEqual(review.render_comparison(self.root, self.config, pos, timeline, self.output), result)
        still_path = self.root / result["stills"][0]["image"]["path"]
        still_path.write_bytes(still_path.read_bytes() + b"tampered")
        with self.assertRaisesRegex(ValueError, "digest differs"):
            review.render_comparison(self.root, self.config, pos, timeline, self.output)

    def test_invalid_frame_selection_and_protected_scope_rejected_before_decoder(self):
        pos, timeline = self.fixture()
        mutations = [lambda rows: rows[3].update(state="missing"),
                     lambda rows: rows[0].update(center_xy_px=[1, 2]),
                     lambda rows: rows[1].update(frame_index=0),
                     lambda rows: rows[3].update(candidates=[{"candidate_index": 0}]),
                     lambda rows: rows[2].update(state="observed")]
        for mutate in mutations:
            changed = copy.deepcopy(timeline)
            mutate(changed["frames"])
            with mock.patch.object(cv2, "VideoCapture") as capture, self.assertRaises(ValueError):
                review.render_comparison(self.root, self.config, pos, changed, self.output)
            capture.assert_not_called()
        with self.assertRaisesRegex(ValueError, "no source pixels"):
            review.render_frame(np.zeros((288, 512, 3), np.uint8), timeline["frames"][3], pos["source_video"], [])
        # Finite off-image candidates stay observations and are never clamped onto a border.
        outside = copy.deepcopy(timeline)
        row = outside["frames"][0]
        chosen = next(c for c in row["candidates"] if c["candidate_index"] == row["selected_candidate_index"])
        chosen["center_x"] = -50
        row["center_xy_px"] = row["baseline_center_xy_px"] = [-50, chosen["center_y"]]
        review.validate_timeline(pos, outside)
        canvas = review.render_frame(np.zeros((288, 512, 3), np.uint8), row, pos["source_video"], [])
        self.assertFalse(canvas[review.HEADER_HEIGHT:].any())

    def test_failed_attempt_is_preserved_owned_encoder_reaped_and_retry_is_separate(self):
        pos, timeline = self.fixture()
        children = []
        original_popen = review.subprocess.Popen

        def launch(*args, **kwargs):
            child = original_popen(*args, **kwargs)
            children.append(child)
            return child

        def out_of_sync(root, declared, segment):
            yield 999, np.zeros((288, 512, 3), np.uint8)

        with mock.patch.object(review.subprocess, "Popen", side_effect=launch), \
                mock.patch.object(observation, "decode_segment", side_effect=out_of_sync), \
                self.assertRaisesRegex(ValueError, "not synchronized"):
            review.render_comparison(self.root, self.config, pos, timeline, self.output)
        self.assertTrue(children and all(child.poll() is not None for child in children))
        self.assertFalse((self.output / "review.json").exists())
        attempts = list((self.output / "render_attempts").iterdir())
        self.assertEqual(len(attempts), 1)
        failed = read_json(attempts[0] / "completed.json")
        self.assertEqual(failed["status"], "failed")
        self.assertGreater(failed["wall_seconds"], 0)
        review.render_comparison(self.root, self.config, pos, timeline, self.output)
        self.assertEqual(read_json(attempts[0] / "completed.json"), failed)
        self.assertEqual(len(list((self.output / "render_attempts").iterdir())), 2)

    def test_protected_final_frame_decodes_black_in_both_panels(self):
        pos, timeline = self.fixture(count=6)
        result = review.render_comparison(self.root, self.config, pos, timeline, self.output)
        final = cv2.imread(str(self.root / result["decoded_final_frame"]["path"]))
        self.assertLessEqual(int(final[review.HEADER_HEIGHT:].max()), 3)
        self.assertEqual(result["verification"]["decoded_frames"], 6)
        self.assertEqual(result["verification"]["final_frame_index"], 5)


if __name__ == "__main__":
    unittest.main()
