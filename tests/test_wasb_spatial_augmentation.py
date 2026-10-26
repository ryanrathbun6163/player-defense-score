"""Spatial alignment checked against frozen producers and analytic pixel geometry."""
import copy
import hashlib
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest import mock

import numpy as np
import torch

from src.ball_tracking import wasb_augmentation as legacy
from src.ball_tracking import wasb_resolution as resolution
from src.ball_tracking import wasb_spatial_augmentation as spatial
from src.ball_tracking import wasb_training as training
from src.ball_tracking.annotations import FrameAnnotation
from tests import test_wasb_resolution as resolution_tests


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "data/outputs/ball_tracking/completion_campaign_v0_1/frozen_primary_package_v0_1/package.json"


class SpatialAugmentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads = torch.get_num_threads()
        torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.old_threads)

    def package(self, root):
        # Actual preceding test producer writes native PNGs + joins; use real
        # FrameStore normalization/targets instead of fabricating consumer tensors.
        package, block = resolution_tests.ResolutionTests()._package(root)
        source = block["source_video"]
        bounds = type("Bounds", (), source | {"width_px": source["width_px"], "height_px": source["height_px"]})()
        for i, frame in enumerate(block["frames"]):
            annotation = FrameAnnotation.from_mapping(frame["annotation"], i, bounds)
            kind = training.annotation_kind(annotation)
            frame.update(kind=kind, valid_output_channel=kind != "masked")
        triplet = {"triplet_id": block["block_id"] + "/frame_000000", "block_id": block["block_id"],
                   "frame_indices": [0, 1, 2], "valid_output_channels": [True, True, False]}
        return package, block, triplet

    def test_actual_framestore_legacy_identity_replay_masks_and_rng(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package, block, triplet = self.package(root)
            store = resolution.FrameStore(root, package, root / "cache")
            try:
                store.prepare()
                example = store.example(triplet)
                saved = tuple(t.clone() for t in example)
                rngs = random.getstate(), np.random.get_state(), torch.random.get_rng_state()
                seen = set()
                for batch_index in range(1, 15):
                    keys = dict(seed=1234, epoch=6, batch_index=batch_index, sample_index=0,
                                triplet_id=triplet["triplet_id"])
                    expected, old_audit = resolution.augment_example(example, **keys)
                    actual, audit = spatial.augment_example(example, triplet=triplet, block=block, **keys)
                    self.assertEqual(audit["augmentation"], old_audit)
                    self.assertNotEqual(audit["spatial_augmentation"]["parameters"]["key_sha256"], old_audit["key_sha256"])
                    self.assertTrue(spatial.validate_audit(audit["spatial_augmentation"], triplet=triplet, block=block, **keys))
                    applied = audit["spatial_augmentation"]["applied"]
                    seen.add(applied)
                    if not applied:
                        for a, e in zip(actual, expected, strict=True):
                            self.assertTrue(torch.equal(a, e))
                            self.assertNotEqual(a.data_ptr(), e.data_ptr())
                    self.assertTrue(torch.equal(actual[2], example[2]))
                    self.assertFalse(actual[1][1:].any())  # certain hidden and masked
                    self.assertTrue(bool(((actual[1] == 0) | (actual[1] == 1)).all()))
                    self.assertTrue(actual[1][0].any())
                self.assertEqual(seen, {False, True})
                for a, e in zip(example, saved, strict=True):
                    self.assertTrue(torch.equal(a, e))
                self.assertEqual(random.getstate(), rngs[0])
                np.testing.assert_equal(np.random.get_state(), rngs[1])
                self.assertTrue(torch.equal(torch.random.get_rng_state(), rngs[2]))
            finally:
                store.close()

    def test_stateless_draw_formula_and_call_order(self):
        keys = dict(seed=1234, epoch=7, batch_index=1552, sample_index=0)
        raw = {"policy_id": spatial.POLICY["id"], **keys}
        digest = hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()).digest()
        expected_uniforms = [int.from_bytes(digest[i:i + 8], "big") // 2048 / 9007199254740992 for i in (0, 8, 16, 24)]
        first = spatial.parameters(**keys)
        for i in range(10):
            spatial.parameters(**(keys | {"batch_index": i + 1}))
        self.assertEqual(first, spatial.parameters(**keys))
        self.assertEqual([first[k] for k in ("apply_uniform", "scale_uniform", "translation_x_uniform", "translation_y_uniform")], expected_uniforms)
        self.assertNotEqual(first["key_sha256"], legacy.parameters(**keys)["key_sha256"])

    def test_integer_translation_alignment_and_constant_padding_without_duplicates(self):
        h, w = resolution.HEIGHT, resolution.WIDTH
        yy, xx = np.indices((h, w), dtype=np.float32)
        channels = torch.from_numpy(np.stack([xx / w, yy / h, (xx + yy) / (w + h)]))
        inputs = channels.repeat(3, 1, 1)
        target = torch.zeros((3, h, w), dtype=torch.float32)
        target[:, 100:104, 300:305] = 1
        result, raster, valid = spatial.apply_parameters((inputs, target, torch.ones(3, dtype=torch.bool)),
                                                         scale=1., translation_x_px=7., translation_y_px=-4.)
        expected = torch.zeros_like(target)
        expected[:, 96:100, 307:312] = 1
        self.assertTrue(torch.equal(raster, expected))
        torch.testing.assert_close(result[:, 20:200, 20:400], inputs[:, 24:204, 13:393], rtol=0, atol=2e-6)
        self.assertEqual(float(result[:, :, :6].abs().max()), 0.)
        self.assertEqual(float(result[:, -3:].abs().max()), 0.)
        for channel in range(3):
            self.assertTrue(torch.equal(result[channel], result[channel + 3]))
            self.assertTrue(torch.equal(result[channel], result[channel + 6]))
        self.assertTrue(valid.all())

    def test_scale_inverse_pixel_centers_and_nearest_original_raster(self):
        h, w = resolution.HEIGHT, resolution.WIDTH
        scale, tx, ty = 1.073, 2.31, -3.17
        forward, inverse = spatial.matrices(scale=scale, translation_x_px=tx, translation_y_px=ty)
        fh, ih = np.vstack((forward, [0, 0, 1])), np.vstack((inverse, [0, 0, 1]))
        np.testing.assert_allclose(fh @ ih, np.eye(3), atol=1e-12)
        cx, cy = (w - 1) / 2, (h - 1) / 2
        np.testing.assert_allclose(fh @ [cx, cy, 1], [cx + tx, cy + ty, 1], atol=1e-12)
        yy, xx = np.indices((h, w), dtype=np.float64)
        original = ((xx - 301) ** 2 + (yy - 199) ** 2 <= 3.75 ** 2).astype(np.float32)
        targets = torch.from_numpy(np.stack([original] * 3))
        inputs = torch.from_numpy(np.stack([xx / w, yy / h, np.ones_like(xx)] * 3).astype(np.float32))
        result, raster, _ = spatial.apply_parameters((inputs, targets, torch.ones(3, dtype=torch.bool)),
                                                     scale=scale, translation_x_px=tx, translation_y_px=ty)
        # Independent analytic inverse in pixel space. Sampling is deliberately
        # compared to the old raster, not a newly rounded center/radius disk.
        sx, sy = (xx - cx - tx) / scale + cx, (yy - cy - ty) / scale + cy
        nx, ny = np.floor(sx + .5).astype(int), np.floor(sy + .5).astype(int)
        expected = np.zeros((h, w), np.float32)
        inside = (nx >= 0) & (nx < w) & (ny >= 0) & (ny < h)
        expected[inside] = original[ny[inside], nx[inside]]
        np.testing.assert_array_equal(raster[0].numpy(), expected)
        np.testing.assert_allclose(result[0, 30:400, 40:700].numpy(), sx[30:400, 40:700] / w, atol=3e-7)
        np.testing.assert_allclose(result[1, 30:400, 40:700].numpy(), sy[30:400, 40:700] / h, atol=3e-7)

    def test_target_and_uncertainty_clipping_are_distinct_and_preserve_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package, block, triplet = self.package(root)
            # At working x=12, the radius3.75 raster fits after shifting left7px;
            # a 12px uncertainty circle does not. That uncertainty is metadata,
            # not a widened supervised disk.
            block["frames"][0]["annotation"]["geometry"].update(center_xy_px=[20., 360.], uncertainty_radius_px=20.)
            geo = spatial.geometry(triplet, block, mirror=False, scale=1., translation_x_px=-7., translation_y_px=0.)
            reasons = geo["channels"][0]["clipping_reasons"]
            self.assertIn("transformed_uncertainty_support", reasons)
            self.assertNotIn("transformed_target_support", reasons)
            geo = spatial.geometry(triplet, block, mirror=False, scale=1., translation_x_px=-12., translation_y_px=0.)
            self.assertIn("transformed_target_support", geo["channels"][0]["clipping_reasons"])
            store = resolution.FrameStore(root, package, root / "cache")
            try:
                store.prepare()
                example = store.example(triplet)
                selected = next(i for i in range(1, 500) if spatial.plan(triplet, block, epoch=6, batch_index=i, sample_index=0)["identity_reason"] == "clipped_supervised_support")
                keys = dict(epoch=6, batch_index=selected, sample_index=0, triplet_id=triplet["triplet_id"])
                actual, audit = spatial.augment_example(example, triplet=triplet, block=block, **keys)
                expected, old = resolution.augment_example(example, **keys)
                self.assertEqual(audit["augmentation"], old)
                for a, b in zip(actual, expected, strict=True):
                    self.assertTrue(torch.equal(a, b))
                self.assertFalse(audit["spatial_augmentation"]["applied"])
            finally:
                store.close()

    @unittest.skipUnless(PACKAGE.is_file(), "Requires accepted local frozen package")
    def test_actual_accepted_records_match_frozen_target_geometry_and_masks(self):
        package = json.loads(PACKAGE.read_text(encoding="utf-8"))
        blocks = {b["block_id"]: b for b in package["training_blocks"]}
        chosen = []
        seen = set()
        for triplet in package["training_triplets"]:
            block = blocks[triplet["block_id"]]
            offset = triplet["frame_indices"][0] - block["frames"][0]["source_frame_index"]
            frames = block["frames"][offset:offset + 3]
            categories = {block["domain"]} | {f["kind"] for f in frames} | {f["annotation"]["visibility"] for f in frames}
            if categories - seen:
                chosen.append((triplet, block))
                seen |= categories
        self.assertTrue({"nba", "nfhs", "positive", "hidden", "masked", "partially_visible", "fully_visible"} <= seen)
        for triplet, block in chosen:
            source = block["source_video"]
            bounds = type("Bounds", (), {k: source[k] for k in ("width_px", "height_px")})()
            for mirror in (False, True):
                geo = spatial.geometry(triplet, block, mirror=mirror, scale=1.1,
                                       translation_x_px=.03 * resolution.WIDTH,
                                       translation_y_px=-.03 * resolution.HEIGHT)
                for channel, index in enumerate(triplet["frame_indices"]):
                    offset = index - block["frames"][0]["source_frame_index"]
                    annotation = FrameAnnotation.from_mapping(block["frames"][offset]["annotation"], offset, bounds)
                    raster, valid, old = resolution.annotation_target(annotation, source["width_px"], source["height_px"])
                    got = geo["channels"][channel]
                    self.assertEqual(got["kind"], old["kind"])
                    self.assertEqual(valid, triplet["valid_output_channels"][channel])
                    if old["kind"] == "positive":
                        self.assertEqual(got["original_integer_heatmap_center"], old["integer_heatmap_center"])
                        xs = np.nonzero(raster[:, ::-1] if mirror else raster)[1]
                        ys = np.nonzero(raster)[0]
                        self.assertEqual(got["target_cell_bounds_before"], [float(xs.min()) - .5, float(ys.min()) - .5,
                                                                               float(xs.max()) + .5, float(ys.max()) + .5])
                    else:
                        self.assertFalse(raster.any())

    def test_metadata_only_plans_reject_wrong_joins_and_mutated_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            _, block, triplet = self.package(Path(temp))
            keys = dict(epoch=6, batch_index=2, sample_index=1)
            with mock.patch.object(resolution, "annotation_target", side_effect=AssertionError("No raster planning")), \
                 mock.patch.object(torch, "arange", side_effect=AssertionError("No grid planning")), \
                 mock.patch.object(torch, "load", side_effect=AssertionError("No model loading")):
                audit = spatial.plan(triplet, block, **keys)
                self.assertTrue(spatial.validate_audit(audit, triplet=triplet, block=block, **keys))
            wrong = copy.deepcopy(audit)
            wrong["effective_parameters"]["scale"] = .99
            with self.assertRaisesRegex(ValueError, "audit differs"):
                spatial.validate_audit(wrong, triplet=triplet, block=block, **keys)
            bad = copy.deepcopy(block)
            bad["frames"][1]["annotation"]["frame_index"] = 7
            with self.assertRaisesRegex(ValueError, "join differs"):
                spatial.plan(triplet, bad, **keys)
            bad = copy.deepcopy(block)
            bad["frames"][0]["kind"] = "hidden"
            with self.assertRaisesRegex(ValueError, "metadata differs"):
                spatial.plan(triplet, bad, **keys)


if __name__ == "__main__":
    unittest.main()
