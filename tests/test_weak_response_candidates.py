"""CPU extraction parity, provenance, missingness and local-structure checks."""
from __future__ import annotations

import ast
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import sys
import unittest

import cv2
import numpy as np

from src.ball_tracking import wasb_adapter
from src.ball_tracking import weak_response_candidates as candidate


ROOT = Path(__file__).resolve().parents[1]


def frozen_producer():
    """Execute actual frozen CPU functions without importing its GPU runtime."""
    source = ROOT / "src/ball_tracking/wasb_resolution.py"
    parsed = ast.parse(source.read_text(encoding="utf-8"))
    names = {"dimensions", "affine_matrices", "components_from_heatmap"}
    nodes = [n for n in parsed.body if isinstance(n, ast.FunctionDef) and n.name in names]
    def check(condition, message):
        if not condition:
            raise ValueError(message)
    namespace = {"np": np, "cv2": cv2, "adapter": wasb_adapter,
                 "WIDTH": 768, "HEIGHT": 432, "check": check}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)
    return namespace["components_from_heatmap"]


class CandidateTests(unittest.TestCase):
    def test_exact_frozen_producer_fields_at_both_resolutions(self):
        producer = frozen_producer()
        rng = np.random.default_rng(61026)
        for width, height in ((512, 288), (768, 432)):
            heatmap = np.zeros((height, width), np.float32)
            heatmap[5:29, 9:40] = rng.random((24, 31), dtype=np.float32)
            heatmap[80, 70], heatmap[81, 71] = .6, .9
            heatmap[0, width//2] = .7
            heatmap[100, 120] = .3
            for threshold in (.3, .01, .00001):
                with self.subTest(width=width, threshold=threshold):
                    expected = producer(heatmap, 2000, 500, threshold, width=width, height=height)
                    self.assertEqual(candidate.components(heatmap, 2000, 500, threshold), expected)

    def test_pool_native_fields_indices_and_saved_record_validation(self):
        heatmap = np.zeros((432, 768), np.float32)
        heatmap[20:23, 30:33] = .9
        heatmap[70, 90] = .02
        producer = frozen_producer()
        native = [{"candidate_index": i, **c}
                  for i, c in enumerate(producer(heatmap, 1920, 1080))]
        pool, diagnostic = candidate.extract_pool(heatmap, native, 1920, 1080)
        self.assertEqual({k: pool[0][k] for k in native[0]}, native[0])
        self.assertEqual(pool[0]["original_index"], 0)
        self.assertTrue(all(row["candidate_index"] == i for i, row in enumerate(pool)))
        self.assertTrue(all(row["original_index"] is None for row in pool[1:]))
        self.assertTrue(diagnostic["native_parity"])
        self.assertFalse(diagnostic["labels_used"])
        modified = deepcopy(native)
        modified[0]["center_x"] += .01
        with self.assertRaisesRegex(ValueError, "differs"):
            candidate.extract_pool(heatmap, modified, 1920, 1080)

    def test_strict_threshold_diagonal_connectivity_and_empty_map(self):
        heatmap = np.zeros((18, 32), np.float32)
        heatmap[4, 4], heatmap[5, 5], heatmap[10, 10] = .5, .75, .3
        rows = candidate.components(heatmap, 32, 18)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["component_pixels"], 2)
        empty = np.zeros_like(heatmap)
        pool, diagnostic = candidate.extract_pool(empty, [], 32, 18)
        self.assertEqual(pool, [])
        self.assertEqual(diagnostic["pool_count"], 0)
        self.assertTrue(all(not rows for rows in diagnostic["components_by_threshold"].values()))

    def test_plateau_consolidation_clipped_patch_and_local_centroid(self):
        heatmap = np.zeros((18, 32), np.float32)
        heatmap[0:2, 0:2] = .1
        heatmap[1, 2] = .06
        heatmap[2, 2] = .05  # Strict > half-peak excludes this float32 half.
        rows = candidate.local_maxima(heatmap, 32, 18)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["plateau_pixels"], 4)
        self.assertEqual(row["peak_heatmap_xy"], [0, 0])
        self.assertEqual(row["patch_bounds_xyxy"], [0, 0, 3, 3])
        self.assertEqual(row["component_pixels"], 5)
        self.assertGreater(row["heatmap_x"], .5)

    def test_weak_local_maxima_retain_separate_lobes_of_merged_component(self):
        heatmap = np.zeros((18, 32), np.float32)
        heatmap[8, 5:17] = .00002
        heatmap[8, 5], heatmap[8, 16] = .001, .002
        components = candidate.components(heatmap, 32, 18, .00001)
        maxima = candidate.local_maxima(heatmap, 32, 18)
        self.assertEqual(len(components), 1)
        # A flat bridge also has a locally maximal plateau beyond each 5x5
        # neighborhood. Preserve that clutter rather than invent prominence.
        self.assertEqual(len(maxima), 3)
        self.assertEqual([r["center_x"] for r in maxima if r["peak"] > .0001], [5., 16.])

    def test_dedup_keeps_native_and_preserves_all_raw_extractions(self):
        heatmap = np.zeros((18, 32), np.float32)
        heatmap[8, 10], heatmap[8, 12], heatmap[8, 20] = .9, .002, .001
        native = [{"candidate_index": i, **r}
                  for i, r in enumerate(candidate.components(heatmap, 32, 18))]
        pool, diagnostic = candidate.extract_pool(heatmap, native, 32, 18)
        self.assertEqual(pool[0]["center_x"], 10.)
        self.assertTrue(any(r["center_x"] == 12. for r in pool[0]["equivalent_extractions"]))
        self.assertTrue(any(r["center_x"] == 12.
                            for r in diagnostic["components_by_threshold"]["0.0001"]))
        self.assertEqual(diagnostic["raw_weak_count"], sum(len(p["equivalent_extractions"]) for p in pool)
                         + len(pool)-len(native))

    def test_no_candidate_cap_and_out_of_image_points_retained(self):
        heatmap = np.zeros((288, 512), np.float32)
        heatmap[::8, ::8] = .001
        pool, diagnostic = candidate.extract_pool(heatmap, [], 2000, 500)
        self.assertGreater(len(pool), 1000)
        self.assertIsNone(diagnostic["candidate_count_cap"])
        self.assertTrue(any(not p["in_source_bounds"] for p in pool))

    def test_bad_inputs_and_changed_parameters_are_rejected(self):
        heatmap = np.zeros((18, 32), np.float32)
        for bad in (heatmap.astype(np.float64), heatmap+np.nan, heatmap-1, heatmap+2):
            with self.assertRaises(ValueError):
                candidate.components(bad, 32, 18)
        parameters = deepcopy(candidate.DEFAULT_PARAMETERS)
        parameters["dedup_source_pixels"] = 3
        with self.assertRaisesRegex(ValueError, "frozen"):
            candidate.extract_pool(heatmap, [], 32, 18, parameters)
        with self.assertRaises(ValueError):
            candidate.local_maxima(heatmap, 32, 18, relative_cutoff=1)

    def test_module_import_does_not_load_torch(self):
        result = subprocess.run([sys.executable, "-c", "import sys; from src.ball_tracking import weak_response_candidates; assert 'torch' not in sys.modules"],
                                cwd=ROOT, text=True, capture_output=True,
                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
