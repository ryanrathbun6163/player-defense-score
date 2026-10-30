"""Synthetic-only response descriptors; no real-study preparation probes."""
from copy import deepcopy
import inspect
import hashlib
import json
import math
import tempfile
from pathlib import Path
import unittest

import numpy as np

from src.ball_tracking import candidate_response_features as features
from src.ball_tracking import candidate_response_study as study
from src.ball_tracking.weak_response_candidates import components
from src.ball_tracking.weak_response_followup import narrow_pool


def gaussian(*, center=(64., 64.), sigma=(2., 2.), amplitude=.8):
    yy, xx = np.mgrid[:128, :128]
    return (amplitude * np.exp(-.5 * (((xx - center[0]) / sigma[0]) ** 2
                                      + ((yy - center[1]) / sigma[1]) ** 2))).astype(np.float32)


class CandidateResponseFeatureTests(unittest.TestCase):
    def test_analytic_affine_ramp_bilinear_sampling(self):
        yy, xx = np.mgrid[:60, :80]
        mean = (.05 + .002 * xx + .001 * yy).astype(np.float32)
        xy = np.asarray([[61.25, 40.5], [64., 52.], [80.5, 60.25]])
        samples, reason = features.sample_source_points(mean, xy, 160, 120)
        self.assertIsNone(reason)
        self.assertEqual(samples.dtype, np.float64)
        np.testing.assert_allclose(samples, .05 + .001 * xy[:, 0] + .0005 * xy[:, 1], rtol=0, atol=2e-8)

    def test_symmetric_offset_and_elongated_responses(self):
        symmetric = features.describe_response(gaussian(), [64., 64.], 128, 128)
        shifted = features.describe_response(gaussian(center=(68., 64.)), [64., 64.], 128, 128)
        elongated = features.describe_response(gaussian(sigma=(4., 1.)), [64., 64.], 128, 128)
        self.assertEqual(symmetric["status"], "observed")
        self.assertEqual((symmetric["sample_count"], symmetric["core_count"], symmetric["ring_count"]), (317, 81, 236))
        self.assertAlmostEqual(symmetric["features"]["isotropy"], 1., places=12)
        self.assertAlmostEqual(symmetric["features"]["negative_centroid_distance"], 0., places=12)
        self.assertLess(shifted["features"]["negative_centroid_distance"], -3.9)
        self.assertLess(elongated["features"]["isotropy"], .1)
        self.assertGreater(symmetric["features"]["negative_spread"], elongated["features"]["negative_spread"])

    def test_shape_scale_invariance_and_explicit_contrast_epsilon(self):
        mean = gaussian()
        a = features.describe_response(mean, [64., 64.], 128, 128)["features"]
        b = features.describe_response(mean * np.float32(.125), [64., 64.], 128, 128)["features"]
        self.assertEqual(b["peak"], a["peak"] * .125)
        for name in ("entropy_concentration", "isotropy", "negative_centroid_distance", "negative_spread"):
            self.assertAlmostEqual(a[name], b[name], places=12)
        # The fixed additive epsilon means contrast is approximately, not
        # mathematically exactly, scale invariant. This is part of the recipe.
        self.assertAlmostEqual(a["core_ring_contrast"], b["core_ring_contrast"], places=9)

    def test_uniform_zero_boundary_and_degenerate_support(self):
        uniform = features.describe_response(np.full((128, 128), .2, np.float32), [64., 64.], 128, 128)
        self.assertAlmostEqual(uniform["features"]["entropy_concentration"], 0., places=12)
        self.assertAlmostEqual(uniform["features"]["core_ring_contrast"], 0., places=12)
        self.assertAlmostEqual(uniform["features"]["isotropy"], 1., places=12)
        zeros = np.zeros((128, 128), np.float32)
        self.assertEqual(features.describe_response(zeros, [64., 64.], 128, 128)["reason"], "all_zero_response")
        self.assertEqual(features.describe_response(zeros, None, 128, 128)["reason"], "missing_selection")
        boundary = features.describe_response(gaussian(), [5., 64.], 128, 128)
        self.assertEqual(boundary["reason"], "incomplete_source_patch")
        self.assertTrue(all(value is None for value in boundary["features"].values()))
        # Source128 -> map64: a valid source pixel beyond map's final center
        # cannot be padded into extra response evidence.
        map_boundary = features.describe_response(np.ones((64, 64), np.float32), [117., 64.], 128, 128)
        self.assertEqual(map_boundary["reason"], "incomplete_heatmap_patch")
        zeros[64, 64] = .5
        point = features.describe_response(zeros, [64., 64.], 128, 128)
        self.assertEqual(point["status"], "partial")
        self.assertIsNone(point["features"]["isotropy"])
        self.assertEqual(point["feature_unknown_reasons"], {"isotropy": "zero_spatial_variance"})
        self.assertEqual(point["features"]["entropy_concentration"], 1.)

    def test_input_preservation_and_label_free_api(self):
        mean = gaussian()
        before = mean.copy()
        center = [64., 64.]
        saved_center = deepcopy(center)
        a = features.describe_response(mean, center, 128, 128)
        b = features.describe_response(mean, center, 128, 128)
        self.assertEqual(a, b)
        np.testing.assert_array_equal(mean, before)
        self.assertEqual(center, saved_center)
        self.assertEqual(tuple(inspect.signature(features.describe_response).parameters),
                         ("mean", "center_xy_px", "source_width", "source_height"))
        with self.assertRaises(TypeError):
            features.describe_response(mean, center, 128, 128, reference=[1, 1])
        with self.assertRaises(ValueError):
            features.describe_response(mean.astype(np.float64), center, 128, 128)

    def test_zero_weight_invalid_neighbors_and_nonfinite_evidence(self):
        mean = np.zeros((128, 128), np.float32)
        mean[64, 64] = .5
        mean[64, 65] = np.nan
        mean[65, 64] = np.inf
        mean[65, 65] = -1
        exact, reason = features.sample_source_points(mean, [[64., 64.]], 128, 128)
        self.assertIsNone(reason)
        np.testing.assert_array_equal(exact, [.5])
        values, reason = features.sample_source_points(mean, [[64.5, 64.]], 128, 128)
        self.assertIsNone(values)
        self.assertEqual(reason, "invalid_sampled_response")
        self.assertEqual(features.describe_response(mean, [64., 64.], 128, 128)["reason"],
                         "invalid_sampled_response")
        self.assertEqual(features.describe_response(mean, [np.nan, 64.], 128, 128)["reason"],
                         "nonfinite_candidate_center")

    def test_actual_synthetic_pool_producer_serialization_transport(self):
        mean = gaussian()
        mean[30:32, 30:32] = .025
        native = [{"candidate_index": i, **c} for i, c in enumerate(components(mean, 128, 128, .3))]
        pool, diagnostic = narrow_pool(mean, native, 128, 128)
        self.assertGreater(len(pool), len(native))
        self.assertEqual(diagnostic["native_count"], len(native))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "producer.jsonl"
            path.write_text(json.dumps({"candidates": pool}) + "\n")
            emitted = json.loads(path.read_text())["candidates"]
        self.assertEqual(emitted, pool)
        original = deepcopy(emitted)
        descriptors = [features.describe_response(mean, [c["center_x"], c["center_y"]], 128, 128)
                       for c in emitted]
        self.assertEqual(emitted, original)
        self.assertEqual(len(descriptors), len(emitted))
        self.assertTrue(all(row["status"] == "observed" for row in descriptors))
        self.assertTrue(all(c["native_score"] == source["native_score"] for c, source in zip(emitted, pool)))
        native_row = {"source_frame_index": 7, "source_pts_ticks": 7000, "time_base": "1/60000",
                      "mean_heatmap_sha256": hashlib.sha256(mean.tobytes()).hexdigest(),
                      "source_png": {"path": "synthetic.png"}, "temporal_contributions": 3,
                      "selected_candidate_index": 0, "candidates": native}
        producer_row = {"block_id": "synthetic", **{key: native_row[key] for key in study.PROVENANCE_FIELDS},
                        "width_px": 128, "height_px": 128, "candidates": emitted}
        weak = next(c for c in emitted if c["original_index"] is None)
        choice = {**{key: native_row[key] for key in study.PROVENANCE_FIELDS},
                  "source_png": native_row["source_png"], "state": "observed",
                  "center_xy_px": [weak["center_x"], weak["center_y"]], "native_score": weak["native_score"],
                  "selected_candidate_index": weak["candidate_index"], "candidate_pool_count": len(pool)}
        actual = study.describe_frame(mean, native_row, producer_row, choice)
        self.assertEqual(actual["expanded_weak_selection"]["observation"], choice)
        self.assertEqual([row["candidate"] for row in actual["main_candidates"]], emitted)
        self.assertEqual([row["descriptor"] for row in actual["main_candidates"]], descriptors)
        changed = deepcopy(producer_row)
        changed["candidates"][0]["native_score"] += .1
        with self.assertRaises(ValueError):
            study.describe_frame(mean, native_row, changed, choice)
        missing = {**choice, "state": "missing", "center_xy_px": None, "native_score": None,
                   "selected_candidate_index": None}
        self.assertEqual(study.describe_frame(mean, native_row, producer_row, missing)
                         ["expanded_weak_selection"]["descriptor"]["reason"], "missing_selection")


if __name__ == "__main__":
    unittest.main()
