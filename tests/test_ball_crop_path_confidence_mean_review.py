"""Artificial pixels and injectable I/O verify the new six-clip renderer."""
import copy
import json
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from src.ball_tracking import crop_path_confidence_mean_review as review
from src.ball_tracking.crop_path_confidence_mean_evaluation import ARM, ARMS, TT, TOP
from test_ball_crop_path_confidence_mean_evaluation import fixture


class MemoryWriter:
    def __init__(self):
        self.shapes = []
        self.released = False

    def write(self, pixels):
        self.shapes.append(pixels.shape)

    def release(self):
        self.released = True


def source_pixels():
    pixels = np.zeros((90, 160, 3), dtype=np.uint8)
    pixels[:, :, 0] = np.arange(160, dtype=np.uint8)
    pixels[:, :, 1] = np.arange(90, dtype=np.uint8)[:, None]
    return pixels


def fast_frame(source, annotation, frame, observations, reports):
    composite = np.full((review.TILE_HEIGHT * 2, review.TILE_WIDTH * 2, 3), frame.frame_index % 255, dtype=np.uint8)
    native = {review.VIEW_NAMES[a]: np.vstack((np.zeros((review.NATIVE_HEADER, source.shape[1], 3), dtype=np.uint8), source)) for a in ARMS}
    details = {review.VIEW_NAMES[a]: {"frame_index": frame.frame_index, "emitted_candidate_indices": observations[a]["emitted_candidate_indices"]} for a in ARMS}
    return composite, native, details


class MeanReviewTests(unittest.TestCase):
    def test_native_scale_four_panels_source_unchanged_and_missingness(self):
        labels, run, observations, reports, _ = fixture()
        source = source_pixels()
        before = source.copy()
        index = 2
        composite, native, details = review.render_frame(source, labels.annotation_by_frame()[index], run.frames[index],
            {a: observations[a]["frames"][index] for a in ARMS}, {a: reports[a]["frame_results"][index] for a in ARMS})
        self.assertEqual(composite.shape, (review.TILE_HEIGHT * 2, review.TILE_WIDTH * 2, 3))
        self.assertEqual(set(native), {"saved_tt", "new_mean", "saved_top_one"})
        self.assertTrue(all(p.shape == (90 + review.NATIVE_HEADER, 160, 3) for p in native.values()))
        self.assertTrue(np.array_equal(before, source))
        self.assertTrue(all("MISSING" in d["selection_text"] for d in details.values()))
        self.assertTrue(all(d["state"] == "missing" for d in details.values()))

    def test_hidden_frame_has_no_reference_geometry_and_candidate_index_visible(self):
        labels, run, observations, reports, _ = fixture()
        index = 3
        self.assertIsNone(labels.annotation_by_frame()[index].geometry)
        _, _, details = review.render_frame(source_pixels(), labels.annotation_by_frame()[index], run.frames[index],
            {a: observations[a]["frames"][index] for a in ARMS}, {a: reports[a]["frame_results"][index] for a in ARMS})
        self.assertTrue(all(d["state"] == "alarm" and "#0" in d["selection_text"] for d in details.values()))

    def test_unsynchronized_or_unknown_candidates_rejected(self):
        labels, run, observations, reports, _ = fixture()
        obs = {a: copy.deepcopy(observations[a]["frames"][0]) for a in ARMS}
        results = {a: reports[a]["frame_results"][0] for a in ARMS}
        obs[ARM]["frame_index"] = 1
        with self.assertRaisesRegex(ValueError, "synchronized"):
            review.render_frame(source_pixels(), labels.annotation_by_frame()[0], run.frames[0], obs, results)
        obs[ARM]["frame_index"] = 0
        obs[ARM]["emitted_candidate_indices"] = [99]
        with self.assertRaisesRegex(ValueError, "Unknown"):
            review.render_frame(source_pixels(), labels.annotation_by_frame()[0], run.frames[0], obs, results)

    def test_all_25_frames_native_outputs_first_last_and_changed_index(self):
        labels, run, observations, reports, window = fixture(25, start=150, hidden=(15, 16, 17, 18, 19))
        observations[ARM]["frames"][5]["emitted_candidate_indices"] = []
        reads, written, writer, verified = [], {}, MemoryWriter(), []

        def read_source(index):
            reads.append(index)
            return source_pixels()

        def write(relative, payload):
            self.assertNotIn(relative, written)
            written[relative] = payload
            return {"path": relative, "sha256": "a" * 64, "size_bytes": len(payload)}

        def open_video(relative, fps, size):
            self.assertTrue(relative.endswith("/comparison.mp4"))
            self.assertEqual(fps, 5.0)
            self.assertEqual(size, (review.TILE_WIDTH * 2, review.TILE_HEIGHT * 2))
            return writer

        def verify_video(relative, count, fps, size):
            self.assertTrue(writer.released)
            self.assertEqual(count, len(writer.shapes))
            self.assertEqual(count, 25)
            self.assertEqual(fps, 5.0)
            verified.append(relative)
            return {"path": relative, "sha256": "b" * 64, "size_bytes": 1}

        with patch.object(review, "render_frame", side_effect=fast_frame), patch.object(cv2, "VideoCapture", side_effect=AssertionError("No video source decode")):
            result = review.render_window(window, run, labels, observations, reports, read_source=read_source,
                                          write_bytes=write, open_video=open_video, verify_video=verify_video)
        index = result["index"]
        self.assertEqual(reads, list(range(150, 175)))
        self.assertEqual(len(written), 78)  # 75 native + first + last + index
        self.assertEqual(len(index["assets"]), 78)  # video replaces index in assets
        self.assertEqual(index["native_overlay_count"], 75)
        self.assertEqual(index["first_frame_index"], 150)
        self.assertEqual(index["final_frame_index"], 174)
        self.assertEqual(index["changed_emission_frame_indices"], dict(saved_tt=[155], saved_top_one=[155]))
        self.assertEqual(len(verified), 1)
        self.assertEqual(index["human_final_frame_review"], "pending")
        self.assertEqual(index["source_video_decodes"], 0)
        self.assertEqual([row["frame_index"] for row in index["frames"] if not row["reference_geometry_present"]], [165, 166, 167, 168, 169])
        decoded = json.loads(written[result["index_binding"]["path"]])
        self.assertEqual(decoded, index)

    def test_worker_read_denial_propagates_and_writer_released_after_failure(self):
        labels, run, observations, reports, window = fixture(25)
        writer, calls = MemoryWriter(), []

        def read(index):
            calls.append(index)
            if index == 1:
                raise PermissionError("pixel phase refused")
            return source_pixels()

        with patch.object(review, "render_frame", side_effect=fast_frame), self.assertRaisesRegex(PermissionError, "phase refused"):
            review.render_window(window, run, labels, observations, reports, read_source=read,
                write_bytes=lambda name, payload: {"path": name}, open_video=lambda *args: writer,
                verify_video=lambda *args: self.fail("Failed clip cannot be adopted"))
        self.assertEqual(calls, [0, 1])
        self.assertTrue(writer.released)

    def test_incomplete_window_rejected_before_any_read(self):
        labels, run, observations, reports, window = fixture(24)
        with self.assertRaisesRegex(ValueError, "complete 25"):
            review.render_window(window, run, labels, observations, reports,
                read_source=lambda *args: self.fail("No source access before structural validation"),
                write_bytes=lambda *args: None, open_video=lambda *args: None, verify_video=lambda *args: None)


if __name__ == "__main__":
    unittest.main()
