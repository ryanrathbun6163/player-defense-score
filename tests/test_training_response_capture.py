"""Synthetic saved-map capture and real metadata transport; no neural inference."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from src.ball_tracking import training_response_capture as capture
from src.ball_tracking import wasb_resolution as producer


def synthetic(n=7):
    frames = [{"source_frame_index": i, "source_pts_ticks": i*1000,
               "png": {"path": f"frame{i}.png", "bytes": 1, "sha256": str(i)*64, "rgb_sha256": str(i)*64}}
              for i in range(n)]
    block = {"block_id": "synthetic_training", "frames": frames, "range_inclusive": [0, n-1],
             "source_video": {"width_px": 1280, "height_px": 720, "sha256": "a"*64}, "time_base": "1/60000"}
    maps = []
    expected = []
    segment = {"kind": "training_only_assessment", "source_frame_range_inclusive": block["range_inclusive"]}
    for i in range(n):
        # Independent explicit contributor sum, in ascending start/channel order.
        planes = [np.full((432, 768), (s*3+(i-s)+1)/100, np.float32) for s in range(max(0, i-2), min(i, n-3)+1)]
        total = np.zeros((432, 768), np.float32)
        for plane in planes: total += plane
        mean = total / np.float32(len(planes))
        maps.append(mean)
        expected.append(producer.select_observation(frames[i], mean, len(planes), block, segment))
    def provide(selected):
        s = selected[0]["source_frame_index"]
        return np.stack([np.full((432, 768), (s*3+c+1)/100, np.float32) for c in range(3)])
    return block, expected, maps, provide


class TrainingResponseCaptureTests(unittest.TestCase):
    def test_required_starts_full_partial_and_all_imported(self):
        self.assertEqual(capture.required_starts(7, set()), [0, 1, 2, 3, 4])
        self.assertEqual(capture.required_starts(7, {2, 3, 4}), [0, 1, 3, 4])
        self.assertEqual(capture.required_starts(7, set(range(7))), [])
        for n, offsets in [(2, set()), (7, {-1}), (7, {7})]:
            with self.assertRaises(ValueError): capture.required_starts(n, offsets)

    def test_actual_producer_capture_means_and_original_boundary_counts(self):
        block, expected, means, provide = synthetic()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"means.npy"
            observed, calls = capture.capture_means(block, expected, path, provide)
            self.assertEqual(calls, 5)
            self.assertEqual(observed, expected)
            np.testing.assert_array_equal(np.load(path, allow_pickle=False), np.stack(means))
            self.assertEqual([r["temporal_contributions"] for r in observed], [1, 2, 3, 3, 3, 2, 1])

    def test_partial_reuse_reduces_calls_with_exact_output_parity(self):
        block, expected, means, provide = synthetic()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"means.npy"
            observed, calls = capture.capture_means(block, expected, path, provide, {i: means[i] for i in (2, 3, 4)})
            self.assertEqual(calls, 4)
            self.assertEqual(observed, expected)
            np.testing.assert_array_equal(np.load(path, allow_pickle=False), np.stack(means))

    def test_emitted_means_transport_to_existing_weak_pool_producer(self):
        from src.ball_tracking import weak_response_followup as extraction
        block, expected, _, provide = synthetic()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            maps_path, pools_path = root/"means.npy", root/"pools.jsonl"
            observed, _ = capture.capture_means(block, expected, maps_path, provide)
            receipt = extraction.extract_block(root, block, observed, capture.binding(root, maps_path), pools_path)
            rows = [json.loads(line) for line in pools_path.read_text().splitlines()]
            self.assertEqual(len(rows), 7)
            self.assertEqual([r["source_frame_index"] for r in rows], list(range(7)))
            self.assertTrue(receipt["all_mean_hashes_exact"] and receipt["all_native_candidates_exact"])
            self.assertTrue(all(r["mean_heatmap_sha256"] == obs["mean_heatmap_sha256"] for r, obs in zip(rows, observed)))

    def test_all_imported_runs_no_provider(self):
        block, expected, means, _ = synthetic()
        def forbidden(_): raise AssertionError("Unexpected neural request")
        with tempfile.TemporaryDirectory() as directory:
            _, calls = capture.capture_means(block, expected, Path(directory)/"means.npy", forbidden, dict(enumerate(means)))
            self.assertEqual(calls, 0)

    def test_hash_mismatch_and_existing_output_are_not_overwritten(self):
        block, expected, means, provide = synthetic()
        wrong = deepcopy(expected); wrong[0]["mean_heatmap_sha256"] = "0"*64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"means.npy"
            with self.assertRaises(ValueError): capture.capture_means(block, wrong, path, provide)
            self.assertTrue(path.exists())
            before = path.read_bytes()
            with self.assertRaises(ValueError): capture.capture_means(block, expected, path, provide)
            self.assertEqual(path.read_bytes(), before)

    def test_donor_requires_exact_video_clock_png_rgb_map_and_candidates(self):
        block, rows, _, _ = synthetic()
        frame, observation = block["frames"][0], rows[0]
        self.assertTrue(capture.donor_matches(block, frame, observation, block["source_video"], observation))
        for field in ("time_base", "source_pts_ticks", "source_frame_index", "mean_heatmap_sha256", "source_png", "candidates"):
            wrong = deepcopy(observation)
            wrong[field] = [] if field == "candidates" else {"sha256": "bad", "rgb_sha256": "bad"} if field == "source_png" else "bad"
            # Empty synthetic candidate lists need an actual mismatch.
            if field == "candidates": wrong[field] = [{"candidate_index": 999}]
            self.assertFalse(capture.donor_matches(block, frame, observation, block["source_video"], wrong), field)
        self.assertFalse(capture.donor_matches(block, frame, observation, {**block["source_video"], "sha256": "bad"}, observation))

    def test_actual_saved_training_observation_donor_contract(self):
        path = capture.ROOT/capture.PREVIOUS_PREP
        if not path.exists(): self.skipTest("Ignored historical producer records unavailable")
        prep = json.loads(path.read_text())
        package = json.loads((capture.ROOT/prep["package"]["path"]).read_text())
        assessment = json.loads((capture.ROOT/capture.FIT).read_text())
        receipt = json.loads((capture.ROOT/assessment["block_receipts"][0]["path"]).read_text())
        record = json.loads((capture.ROOT/receipt["record"]["path"]).read_text())
        block = next(b for b in package["training_blocks"] if b["block_id"] == record["block_id"])
        observation = record["observations"][0]
        self.assertTrue(capture.donor_matches(block, block["frames"][0], observation, record["source_video"], observation))
        wrong = deepcopy(observation); wrong["source_png"]["rgb_sha256"] = "bad"
        self.assertFalse(capture.donor_matches(block, block["frames"][0], observation, record["source_video"], wrong))

    def test_real_execution_requires_separate_approval_record_first(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out = root/capture.OUTPUT
            out.mkdir(parents=True)
            (out/"prepared.json").write_text('{}')
            with self.assertRaises(FileNotFoundError):
                capture.run(root, "unused_monitor", ["--run"])
            self.assertFalse((out/"capture_attempt_001").exists())


if __name__ == "__main__":
    unittest.main()
