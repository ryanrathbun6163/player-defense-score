"""CPU-only tests of the frozen population and actual image/cache contract."""
from copy import deepcopy
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

from src.ball_tracking import dual_view_context_data as data


class GeometryTests(unittest.TestCase):
    def test_fractional_centers_keep_distinct_weights_on_identical_crop(self):
        a = data.context_geometry([10.1, 20.2], 1280, 720)
        b = data.context_geometry([10.9, 20.8], 1280, 720)
        self.assertEqual(a["crop_box"], b["crop_box"])
        self.assertNotEqual(a["weights"], b["weights"])
        self.assertEqual(a["token_indices"], [120, 121, 136, 137])
        self.assertAlmostEqual(sum(a["weights"]), 1.0)
        self.assertFalse(a["complete_source_crop"])
        # Independent affine coordinate calculation and bilinear interpolation.
        x_input = (96.1 + .5) * (7 / 6) - .5
        y_input = (96.2 + .5) * (7 / 6) - .5
        self.assertAlmostEqual(a["point_input_xy"][0], x_input)
        self.assertAlmostEqual(a["point_input_xy"][1], y_input)
        fx = (x_input - 6.5) / 14 - 7
        fy = (y_input - 6.5) / 14 - 7
        np.testing.assert_allclose(a["weights"], [(1-fx)*(1-fy), fx*(1-fy), (1-fx)*fy, fx*fy], rtol=0, atol=4e-15)
        self.assertNotEqual(a["weights"], data.local_geometry([10.1, 20.2], 1280, 720)["weights"])

    def test_invalid_centers_fail_without_clamping(self):
        for point in ([float("nan"), 1], [-.1, 1], [1280, 1], [1, 720]):
            with self.assertRaises(ValueError):
                data.context_geometry(point, 1280, 720)

    def test_external_cache_indices_precede_role_filter(self):
        queries = [{"query_id": name, "input_id": None if name == "missing" else name,
                    "source_id": "sas_det_q1_c02" if name == "DET" else "allowed"}
                   for name in ["first", "DET", "missing", "last"]]
        targets = [{"query_id": r["query_id"], "missing": r["input_id"] is None} for r in queries]
        allowed, missing, omitted, old_count = data.partition_external(queries, targets)
        self.assertEqual([(q["query_id"], index) for q, _, index in allowed], [("first", 0), ("last", 2)])
        self.assertEqual(old_count, 3)
        self.assertEqual(missing[0]["status"], "missing_no_score")
        self.assertNotIn("quality_logit", missing[0])
        self.assertEqual(omitted[0]["original_local_cache_index"], 1)

    def test_cache_producer_and_consumer_preserve_raw_pixels_and_padding(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pixels = np.zeros((80, 100, 3), np.uint8)
            pixels[:, :, 0] = np.arange(100, dtype=np.uint8)[None, :]
            pixels[:, :, 1] = np.arange(80, dtype=np.uint8)[:, None]
            pixels[:, :, 2] = 91
            Image.fromarray(pixels).save(root / "source.png")
            source = data.binding(root, "source.png")
            records = {}
            with Image.open(root / "source.png") as image:
                crops = []
                for i, center in enumerate(([0.25, .75], [.75, .25])):
                    original = {"source_png": source, "center_xy_px": center, "width_px": 100,
                                "height_px": 80, "source_frame_index": 0, "block_id": "fixture"}
                    row = data._row(original, str(i), "package", "local.npy", i)
                    row["context_cache_index"] = i
                    records[row["row_key"]] = row
                    crops.append(np.asarray(image.crop(tuple(row["local_geometry"]["crop_box"]))))
            np.save(root / "local.npy", np.stack(crops), allow_pickle=False)
            local = {**data.binding(root, "local.npy"), "shape": [2, 64, 64, 3], "dtype": "uint8"}
            before = data.binding(root, "local.npy")
            receipt = data.make_context_cache(root, root / "context.npy", records, [local], progress=lambda *a, **k: None)
            actual = np.load(root / "context.npy", allow_pickle=False)
            self.assertEqual(actual.shape, (2, 192, 192, 3))
            self.assertEqual(actual.dtype, np.uint8)
            self.assertTrue(np.array_equal(actual[0], actual[1]))
            np.testing.assert_array_equal(actual[0, 96:176, 96:192], pixels[:, :96])
            self.assertFalse(actual[:, :96].any())
            self.assertEqual(receipt["local_crops_exactly_verified"], 2)
            self.assertEqual(data.binding(root, "local.npy"), before)
            # A wrong cache with a self-consistent file hash still fails pixel parity.
            bad = np.stack(crops)
            bad[1, 32, 32, 0] ^= 1
            np.save(root / "bad.npy", bad, allow_pickle=False)
            bad_link = {**data.binding(root, "bad.npy"), "shape": [2, 64, 64, 3], "dtype": "uint8"}
            bad_rows = deepcopy(records)
            for row in bad_rows.values():
                row["local_cache"]["path"] = "bad.npy"
            with self.assertRaisesRegex(ValueError, "disagrees with source"):
                data.make_context_cache(root, root / "failed_context.npy", bad_rows, [bad_link], progress=lambda *a, **k: None)
            self.assertTrue((root / "failed_context.npy").exists())

    def test_module_import_has_no_torch(self):
        result = subprocess.run([sys.executable, "-B", "-c", "import sys; from src.ball_tracking import dual_view_context_data; assert 'torch' not in sys.modules"],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class OriginalPopulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        if not (cls.root / data.DESIGN / "design_freeze.json").exists():
            raise unittest.SkipTest("Saved source manifests not present")
        cls.inventory = data.inventory(cls.root)

    def test_finite_populations_and_physical_batch_boundaries(self):
        self.assertEqual(self.inventory["counts"]["capture_rows"], 88742)
        self.assertEqual(self.inventory["counts"]["capture_batches"], 2776)
        self.assertEqual(self.inventory["counts"]["final_scoring_batches_two_arms"], 5554)
        self.assertEqual(self.inventory["counts"]["training_updates_two_arms"], 19740)
        self.assertEqual([len(f["weights"]) for f in self.inventory["fits"].values()], [11954, 11912, 11182, 17524])
        for fit_name, fit in self.inventory["fits"].items():
            captured = set(k for g in fit["capture_groups"] for k in g["row_keys"])
            scores = set(k for g in fit["score_groups"] for k in g["row_keys"])
            self.assertEqual(captured, scores)
            if fit_name != "all_nba":
                self.assertTrue(all(key.startswith("p:") for key in captured))
                self.assertEqual(set(fit["held_out_game_ids"]) & set(fit["fit_game_ids"]), set())
            original_weights = data.read_rows(self.root / fit["original_weights"]["path"])
            self.assertEqual([w["row_key"] for w in fit["weights"]], ["p:" + w["candidate_id"] for w in original_weights])
            self.assertEqual([w["objective_weight"] for w in fit["weights"]], [w["objective_weight"] for w in original_weights])

    def test_external_and_BKN_roles_and_original_cache_indices(self):
        rows = self.inventory["rows"]
        targets = data.read_rows(self.root / data.Q / "evaluation/query_targets.jsonl")
        completion = data.read(self.root / data.Q / "evaluation/completed.json")
        original = data.read_rows(self.root / completion["queries_registry"]["path"])
        queries_by_id = {q["query_id"]: q for q in original}
        index = {q["query_id"]: i for i, q in enumerate(q for q in original if q["input_id"] is not None)}
        for row in rows.values():
            if row["kind"] == "external":
                self.assertEqual(row["local_cache"]["index"], index[row["original_id"]])
                self.assertEqual(row["local_point_weights"], [t["weight"] for t in queries_by_id[row["original_id"]]["geometry"]["tokens"]])
                self.assertFalse(row["fit_eligible"])
            elif row["kind"] == "BKN":
                self.assertFalse(row["fit_eligible"])
        for metadata in self.inventory["missing_external"] + self.inventory["omitted_DET"]:
            self.assertNotIn("e:" + metadata["query_id"], rows)
        self.assertTrue(all("saved_Q_control_metadata_only" in r for r in self.inventory["omitted_DET"]))

    def test_mutated_fractional_mapping_fails_validation(self):
        mutated = dict(self.inventory)
        mutated["rows"] = dict(self.inventory["rows"])
        key = next(iter(mutated["rows"]))
        mutated["rows"][key] = deepcopy(mutated["rows"][key])
        mutated["rows"][key]["context_point_weights"] = [w + (.001 if i == 0 else 0) for i, w in enumerate(mutated["rows"][key]["context_point_weights"])]
        with self.assertRaisesRegex(ValueError, "Fractional point weights"):
            data.validate_inventory(mutated)


if __name__ == "__main__":
    unittest.main()
