"""Actual synthetic producer cache transport and fixed-grid heatmap measurements."""
import copy
import hashlib
from pathlib import Path
import unittest

import numpy as np

from src.ball_tracking import nba_action_observation as action
from src.ball_tracking import nba_saved_heatmap_diagnostic as inspection
from src.ball_tracking import nba_wasb_diagnostic as d
from tests import test_nba_action_observation as action_fixture


class MeasurementTests(unittest.TestCase):
    def setUp(self):
        self.grid = inspection.source_grid(1920, 1080)

    def test_affine_grid_source_radius_and_float32_strict_threshold(self):
        self.assertEqual(self.grid[80, 80].tolist(), [300, 300])
        plane = np.zeros((288, 512), np.float32)
        plane[80, 80] = np.float32(.3)
        below = inspection.plane_metrics(plane, self.grid, [290, 300])
        self.assertEqual(below["local_peak_error_px"], 10)
        self.assertEqual(below["active_pixels_in_reference_disk"], 0)
        plane[80, 80] = np.nextafter(np.float32(.3), np.float32(1))
        above = inspection.plane_metrics(plane, self.grid, [290, 300])
        self.assertEqual(above["active_pixels_in_reference_disk"], 1)
        outside = inspection.plane_metrics(plane, self.grid, [289.9999, 300])
        self.assertEqual(outside["active_pixels_in_reference_disk"], 0)

    def test_hidden_reference_has_no_localization_metrics_and_ties_are_row_major(self):
        plane = np.zeros((288, 512), np.float32)
        plane[20, 40] = .7
        plane[40, 20] = .7
        metrics = inspection.plane_metrics(plane, self.grid, None)
        self.assertEqual(metrics["global_peak_heatmap_xy"], [40, 20])
        self.assertEqual(metrics["global_peak_tie_pixels"], 2)
        for key in ("local_peak", "global_peak_error_px", "local_peak_error_px", "active_pixels_in_reference_disk",
                    "nearest_active_source_distance_px", "local_to_global_peak_ratio"):
            self.assertIsNone(metrics[key])

    def test_component_can_have_near_peak_but_centroid_outside_fixed_radius(self):
        plane = np.zeros((288, 512), np.float32)
        plane[100, 100:109] = .31
        plane[100, 100] = .9
        manifest = {"source_video": {"width_px": 1920, "height_px": 1080}, "time_base": "1/90000"}
        frame = {"source_frame_index": 10, "source_pts_ticks": 90000, "png": {"path": "synthetic.png"}}
        observation = action.select_observation(frame, plane, 3, manifest, {"kind": "live_action"})
        metrics = inspection.selected_component_metrics(plane, self.grid, observation, [375, 375])
        self.assertGreater(metrics["centroid_error_px"], 10)
        self.assertEqual(metrics["peak_error_px"], 0)
        self.assertEqual(metrics["pixels"], 9)
        self.assertEqual(metrics["active_pixels_in_reference_disk"], 3)
        self.assertEqual(metrics["bbox_heatmap_xyxy_inclusive"], [100, 100, 108, 100])

    def test_sparse_reconstruction_is_exact_original_stream_arithmetic(self):
        frames = [{"source_frame_index": i} for i in range(10, 15)]
        generator = np.random.default_rng(43)
        triplets = {i: generator.random((3, 288, 512), dtype=np.float32) for i in range(10, 13)}
        original = list(action.stream_means(frames, lambda rows: triplets[rows[0]["source_frame_index"]]))
        for frame, mean, count in original:
            i = frame["source_frame_index"]
            values = [(start, triplets[start][i - start]) for start in sorted(triplets) if start <= i <= start + 2]
            self.assertEqual(count, len(values))
            self.assertEqual(inspection.reconstruct_mean(values).tobytes(), mean.tobytes())
        with self.assertRaises(ValueError):
            inspection.reconstruct_mean([(11, triplets[11][0]), (10, triplets[10][1])])


class CacheTransportTests(unittest.TestCase):
    def setUp(self):
        # This fixture executes the actual action producer using only synthetic
        # source PNGs and fake model output, including a real prior-cache import.
        self.fixture = action_fixture.ActionObservationTests(methodName="test_actual_producer_cache_import_extended_context_and_no_old_reinference")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.observations, _ = self.fixture.infer()
        self.root, self.manifest = self.fixture.root, self.fixture.manifest

    def test_actual_action_and_pilot_cache_records_are_read_without_receipt_mutation(self):
        seen = set()
        for record in self.observations["triplet_caches"]:
            path = self.root / record["cache"]["path"]
            receipt = path.with_suffix(".json")
            before = receipt.read_bytes()
            values, bound = inspection.load_saved_triplet(self.root, record, self.manifest, self.observations)
            self.assertEqual(values.dtype, np.float32)
            self.assertEqual(values.shape, (3, 288, 512))
            self.assertEqual(receipt.read_bytes(), before)
            self.assertEqual(bound["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            seen.add(record["origin"])
        self.assertEqual(seen, {"action_observation", "prior_pilot_import"})

    def test_missing_receipt_refuses_without_repair_and_corrupt_cache_refuses(self):
        record = self.observations["triplet_caches"][0]
        path = self.root / record["cache"]["path"]
        receipt = path.with_suffix(".json")
        original_receipt = receipt.read_bytes()
        receipt.unlink()
        with self.assertRaisesRegex(ValueError, "Missing original receipt"):
            inspection.load_saved_triplet(self.root, record, self.manifest, self.observations)
        self.assertFalse(receipt.exists())
        receipt.write_bytes(original_receipt)
        path.write_bytes(path.read_bytes() + b"synthetic corruption")
        with self.assertRaisesRegex(ValueError, "cache binding differs"):
            inspection.load_saved_triplet(self.root, record, self.manifest, self.observations)

    def test_native_identity_and_started_call_mismatches_refuse(self):
        record = self.observations["triplet_caches"][0]
        manifest = copy.deepcopy(self.manifest)
        manifest["frames"][0]["source_pts_ticks"] += 1
        with self.assertRaisesRegex(ValueError, "native triple differs"):
            inspection.load_saved_triplet(self.root, record, manifest, self.observations)
        bad = copy.deepcopy(record)
        bad["original_identity_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "call identity differs"):
            inspection.load_saved_triplet(self.root, bad, self.manifest, self.observations)


if __name__ == "__main__":
    unittest.main()
