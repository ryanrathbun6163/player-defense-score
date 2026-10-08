"""Temporal alignment and the actual heatmap-to-point evaluator boundary."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.ball_tracking.point_evaluation import evaluate_points
from src.ball_tracking.wasb_adapter import components_from_heatmap
from src.ball_tracking.wasb_experiment import (
    canonical, make_point_run, merge_heatmaps, read_triplet_cache, select_top_one,
    triplet_starts, write_npz_once, write_once,
)
from test_ball_annotation_foundation import observed_frame, parse_reviewed_annotations


class WasbExperimentTests(unittest.TestCase):
    def test_every_output_channel_is_bound_to_its_source_frame(self):
        triplets = {}
        for first in range(10, 13):
            triplets[first] = np.stack([np.full((288, 512), (first + channel) / 100,
                                               dtype=np.float32) for channel in range(3)])
        result, counts = merge_heatmaps(triplets, 10, 14)
        self.assertEqual(counts, [1, 2, 3, 2, 1])
        self.assertEqual(result.dtype, np.float32)
        np.testing.assert_allclose(result[:, 100, 100], [.10, .11, .12, .13, .14], atol=1e-7)

    def test_25_frame_window_never_reads_external_context_or_drops_tail(self):
        starts = triplet_starts(50, 74)
        self.assertEqual(len(starts), 23)
        self.assertEqual(starts[0], 50)
        self.assertEqual(starts[-1] + 2, 74)
        covered = {first + channel for first in starts for channel in range(3)}
        self.assertEqual(covered, set(range(50, 75)))

    def test_partial_or_nonfinite_model_outputs_cannot_be_scored_as_missing(self):
        valid = np.zeros((3, 288, 512), dtype=np.float32)
        with self.assertRaises(ValueError):
            merge_heatmaps({}, 0, 2)
        with self.assertRaises(ValueError):
            merge_heatmaps({0: valid, 1: valid}, 0, 2)
        bad = valid.copy()
        bad[0, 0, 0] = np.nan
        with self.assertRaises(ValueError):
            merge_heatmaps({0: bad}, 0, 2)

    def test_actual_component_producer_flows_through_run_builder_and_evaluator(self):
        # Analytic source coordinates for a 2x2 block centered at 100.5 heatmap pixels.
        center = (376.875, 376.875)
        labels = parse_reviewed_annotations([observed_frame(i, center=center) for i in range(3)])
        window = {"window_id": "synthetic_wasb", "annotation_set_id": labels.annotation_set_id,
                  "possession_id": labels.possession_id, "source_video": labels.source_video.to_dict(),
                  "start_frame_index": 0, "end_frame_index": 2}
        heatmap = np.zeros((288, 512), dtype=np.float32)
        heatmap[100:102, 100:102] = .75
        components = components_from_heatmap(heatmap, 1920, 1080)
        run = make_point_run(window, {"model": "synthetic_heatmap"}, [components, [], components])
        self.assertEqual(run["frames"][0]["candidates"][0]["native_score"], 3)
        score = evaluate_points(labels, select_top_one(run), localization_radius_px=0)
        self.assertEqual(score["true_positive_count"], 2)
        self.assertEqual(score["false_negative_count"], 1)
        self.assertEqual(score["frame_results"][1]["accepted_detection_count"], 0)
        self.assertEqual(score["frame_results"][-1]["frame_index"], 2)

    def test_top_one_keeps_original_candidate_identity_and_deterministic_ties(self):
        run = {"point_run_id": "test", "model_provenance": {}, "frames": [
            {"candidates": [{"candidate_index": 8, "native_score": 5},
                            {"candidate_index": 3, "native_score": 5},
                            {"candidate_index": 0, "native_score": 2}]}]}
        original = copy.deepcopy(run)
        selected = select_top_one(run)
        self.assertEqual(selected["frames"][0]["candidates"][0]["candidate_index"], 3)
        self.assertEqual(run, original)

    def test_saved_evidence_reused_only_when_identical(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "record.json"
            write_once(path, {"a": 1})
            write_once(path, {"a": 1})
            with self.assertRaises(ValueError):
                write_once(path, {"a": 2})
            self.assertIn('"a": 1', path.read_text())

    def test_interrupted_triplet_publication_recovers_receipt_without_inference(self):
        with tempfile.TemporaryDirectory() as folder:
            cache, receipt = Path(folder) / "triplet.npz", Path(folder) / "triplet.json"
            identity = {"adapter": "fixed", "inference_source": "fixed"}
            metadata = {"input_frame_indices": [50, 51, 52], "output_frame_indices": [50, 51, 52],
                        "inference_seconds": .25, "inference_identity_sha256": canonical(identity),
                        "cuda_peak_allocated_bytes": 123, "transform": {"color_order": "RGB"}}
            values = np.full((3, 288, 512), .25, dtype=np.float32)
            write_npz_once(cache, heatmaps=values, metadata_json=np.array(json.dumps(metadata)))
            self.assertFalse(receipt.exists())
            recovered, elapsed = read_triplet_cache(cache, receipt, [50, 51, 52], identity)
            np.testing.assert_array_equal(values, recovered)
            self.assertEqual(elapsed, .25)
            self.assertTrue(receipt.exists())
            with self.assertRaises(ValueError):
                read_triplet_cache(cache, receipt, [51, 52, 53], identity)
            with self.assertRaises(ValueError):
                read_triplet_cache(cache, receipt, [50, 51, 52], {"adapter": "changed"})

    def test_completed_mean_arrays_reused_and_conflicting_arrays_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mean.npz"
            value = np.array([1, 2, 3], dtype=np.float32)
            write_npz_once(path, heatmaps=value)
            original = path.read_bytes()
            write_npz_once(path, heatmaps=value.copy())
            with self.assertRaises(ValueError):
                write_npz_once(path, heatmaps=value + 1)
            self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
