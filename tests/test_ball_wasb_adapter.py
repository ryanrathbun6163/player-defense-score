"""Synthetic WASB boundary checks; optional pinned-asset checks never download data."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock

import cv2
import numpy as np
import torch

from src.ball_tracking import wasb_adapter as wasb

ASSETS = Path(__file__).resolve().parents[1] / "data/outputs/wasb_assets"
SOURCE = ASSETS / f"WASB-SBDT-{wasb.SOURCE_REVISION}"
CHECKPOINT = ASSETS / "wasb_basketball.pth"


class WasbPreprocessingTests(unittest.TestCase):
    def test_rgb_order_temporal_order_and_official_normalization(self):
        colors = ([255, 0, 0], [0, 255, 0], [0, 0, 255])
        frames = [np.full((288, 512, 3), color, dtype=np.uint8) for color in colors]
        tensor, metadata = wasb.preprocess_triplet(frames)
        self.assertEqual(tuple(tensor.shape), (1, 9, 288, 512))
        self.assertEqual(tensor.dtype, torch.float32)
        for index, color in enumerate(colors):
            expected = (torch.tensor(color, dtype=torch.float32) / 255 - torch.tensor([.485, .456, .406])) / torch.tensor([.229, .224, .225])
            torch.testing.assert_close(tensor[0, index * 3:index * 3 + 3, 140, 250], expected, rtol=0, atol=0)
        self.assertEqual(metadata["color_order"], "RGB")
        np.testing.assert_array_equal(metadata["source_to_heatmap"], [[1, 0, 0], [0, 1, 0]])

    def test_affine_non_widescreen_geometry_and_no_coordinate_clamping(self):
        forward, inverse = wasb.affine_matrices(100, 100)
        np.testing.assert_allclose(forward @ [50, 50, 1], [256, 144])
        np.testing.assert_allclose(inverse @ [256, 144, 1], [50, 50])
        # A wide source receives vertical padding. Its candidate is retained and flagged.
        heatmap = np.zeros((288, 512), dtype=np.float32)
        heatmap[0, 256] = .9
        candidate, = wasb.components_from_heatmap(heatmap, 2000, 500)
        self.assertLess(candidate["center_y"], 0)
        self.assertFalse(candidate["in_source_bounds"])

    def test_invalid_frame_count_dtype_channels_and_mixed_dimensions_rejected(self):
        valid = np.zeros((20, 30, 3), dtype=np.uint8)
        cases = ([valid] * 2, [valid.astype(np.float32)] * 3,
                 [valid[:, :, :1]] * 3, [valid, valid, valid[:10]],
                 [np.zeros((0, 30, 3), dtype=np.uint8)] * 3)
        for frames in cases:
            with self.subTest(shapes=[frame.shape for frame in frames]), self.assertRaises(ValueError):
                wasb.preprocess_triplet(frames)

    def test_components_strict_threshold_connectivity_weighted_centers_and_native_mass(self):
        heatmap = np.zeros((288, 512), dtype=np.float32)
        heatmap[10, 10] = .6
        heatmap[11, 11] = .9  # diagonal joins the first pixel (8-connectivity).
        heatmap[100, 100] = .5  # exactly threshold is absent.
        heatmap[200, 400] = .75
        candidates = wasb.components_from_heatmap(heatmap, 512, 288)
        self.assertEqual(len(candidates), 2)
        first = candidates[0]
        self.assertEqual(first["component_pixels"], 2)
        self.assertEqual(first["native_score"], float(np.float32(.6) + np.float32(.9)))
        self.assertGreater(first["native_score"], 1)
        self.assertAlmostEqual(first["center_x"], 10.6, places=5)
        self.assertAlmostEqual(first["center_y"], 10.6, places=5)
        self.assertTrue(first["in_source_bounds"])
        self.assertEqual(candidates[1]["center_x"], 400)

    def test_empty_and_malformed_heatmaps_are_distinguished(self):
        heatmap = np.zeros((288, 512), dtype=np.float32)
        self.assertEqual(wasb.components_from_heatmap(heatmap, 1920, 1080), [])
        for bad in (heatmap.astype(np.float64), heatmap[:10], heatmap + np.nan, heatmap - 1, heatmap + 2):
            with self.subTest(dtype=bad.dtype, shape=bad.shape), self.assertRaises(ValueError):
                wasb.components_from_heatmap(bad, 1920, 1080)
        for threshold in (float("nan"), -1, 2):
            with self.subTest(threshold=threshold), self.assertRaises(ValueError):
                wasb.components_from_heatmap(heatmap, 1920, 1080, threshold)
        for dimensions in ((0, 1080), (1920, -1), (True, 10), (10.5, 20)):
            with self.subTest(dimensions=dimensions), self.assertRaises(ValueError):
                wasb.components_from_heatmap(heatmap, *dimensions)


@unittest.skipUnless((SOURCE / "src/models/hrnet.py").exists() and CHECKPOINT.exists(), "Pinned external WASB assets are not installed")
class WasbPinnedAssetTests(unittest.TestCase):
    """Checks actual external producer functions and safely loaded basketball weights."""

    @classmethod
    def setUpClass(cls):
        cls.namespace_before = {name: sys.modules.get(name) for name in ("src", "src.models", "utils", "utils.image")}
        cls.adapter = wasb.WasbAdapter(SOURCE, CHECKPOINT, device="cuda" if torch.cuda.is_available() else "cpu")

    def test_affines_match_actual_upstream_transform_for_multiple_aspect_ratios(self):
        module_path = SOURCE / "src/utils/image.py"
        spec = importlib.util.spec_from_file_location("_test_wasb_official_image", module_path)
        image = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(image)
        for width, height in ((1920, 1080), (100, 100), (641, 479), (300, 900)):
            with self.subTest(width=width, height=height):
                forward, inverse = wasb.affine_matrices(width, height)
                center = np.array([width / 2., height / 2.], dtype=np.float32)
                for actual, inv in ((forward, 0), (inverse, 1)):
                    expected = image.get_affine_transform(center, max(width, height) * 1., 0, [512, 288], inv=inv)
                    np.testing.assert_array_equal(actual, expected)

    def test_components_match_actual_upstream_producer_method(self):
        # Compile the unmodified producer method, avoiding unrelated package imports.
        source = ast.parse((SOURCE / "src/detectors/postprocessor.py").read_text(encoding="utf-8"))
        cls = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == "TracknetV2Postprocessor")
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "_detect_blob_concomp")
        namespace = {"np": np, "cv2": cv2}
        exec(compile(ast.Module(body=[method], type_ignores=[]), "actual_upstream_postprocessor", "exec"), namespace)
        producer = type("Producer", (), {"_score_threshold": .5, "_use_hm_weight": True})()
        heatmap = np.zeros((288, 512), dtype=np.float32)
        heatmap[5:8, 9:12] = np.arange(9, dtype=np.float32).reshape(3, 3) / 30 + .6
        heatmap[17, 23] = .99
        heatmap[18, 24] = .51
        heatmap[40, 40] = .5
        xys, scores = namespace["_detect_blob_concomp"](producer, heatmap)
        candidates = wasb.components_from_heatmap(heatmap, 641, 479)
        self.assertEqual(len(candidates), len(xys))
        _, inverse = wasb.affine_matrices(641, 479)
        for candidate, xy, score in zip(candidates, xys, scores):
            self.assertEqual(candidate["native_score"], float(score))
            np.testing.assert_array_equal([candidate["heatmap_x"], candidate["heatmap_y"]], xy)
            mapped = inverse @ np.array([xy[0], xy[1], 1.], dtype=np.float32)
            np.testing.assert_array_equal([candidate["center_x"], candidate["center_y"]], mapped)

    def test_real_checkpoint_and_synthetic_triplet_reach_actual_output_consumer(self):
        # Artificial color ramps exercise real model/runtime, never project footage.
        y, x = np.indices((72, 128))
        frames = [np.stack(((x + offset) % 256, (y * 3) % 256, (x + y) % 256), axis=-1).astype(np.uint8) for offset in (0, 20, 40)]
        result = self.adapter.predict_triplet(frames)
        self.assertEqual(result["heatmaps"].shape, (3, 288, 512))
        self.assertEqual(result["heatmaps"].dtype, np.float32)
        self.assertTrue(np.isfinite(result["heatmaps"]).all())
        self.assertEqual(len(result["frames"]), 3)
        for heatmap, record in zip(result["heatmaps"], result["frames"]):
            self.assertEqual(record["candidates"], wasb.components_from_heatmap(heatmap, 128, 72))
            self.assertEqual(record["transform"]["source_width"], 128)
        self.assertFalse(self.adapter.model.training)
        self.assertEqual(len(self.adapter.model.state_dict()), 428)
        self.assertFalse(self.adapter.provenance["native_tracker_used"])
        for name, original in self.namespace_before.items():
            self.assertIs(sys.modules.get(name), original, name)

    def test_checkpoint_loading_is_weights_only_strict_and_has_no_unsafe_retry(self):
        # Actual checkpoint bytes satisfy the pin; only the deserialized state is
        # mutated to verify the boundary refuses missing trained parameters.
        real = torch.load(CHECKPOINT, map_location="cpu", weights_only=True)
        altered = dict(real["model_state_dict"])
        altered.pop("conv1.weight")
        with mock.patch("torch.load", return_value={"model_state_dict": altered}) as load:
            with self.assertRaisesRegex(RuntimeError, "Missing key"):
                wasb.WasbAdapter(SOURCE, CHECKPOINT, device="cpu")
            load.assert_called_once_with(CHECKPOINT.resolve(), map_location="cpu", weights_only=True)
        with mock.patch("torch.load", side_effect=RuntimeError("safe loader rejected object")) as load:
            with self.assertRaisesRegex(RuntimeError, "safe loader rejected"):
                wasb.WasbAdapter(SOURCE, CHECKPOINT, device="cpu")
            self.assertEqual(load.call_count, 1)

    def test_changed_checkpoint_or_source_is_rejected_before_import_or_deserialization(self):
        with mock.patch.object(wasb, "_sha256", return_value="0" * 64), mock.patch("torch.load") as load:
            with self.assertRaisesRegex(ValueError, "source digest mismatch"):
                wasb.WasbAdapter(SOURCE, CHECKPOINT, device="cpu")
            load.assert_not_called()
        digests = list(wasb.SOURCE_SHA256.values()) + ["0" * 64]
        with mock.patch.object(wasb, "_sha256", side_effect=digests), mock.patch("torch.load") as load:
            with self.assertRaisesRegex(ValueError, "checkpoint digest mismatch"):
                wasb.WasbAdapter(SOURCE, CHECKPOINT, device="cpu")
            load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
