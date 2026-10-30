"""Resolution arm checked against actual frozen 512px producers and raw PNGs."""
import hashlib
from pathlib import Path
import random
import tempfile
import unittest

import cv2
import numpy as np
from PIL import Image
import torch

from src.ball_tracking import completion_training_runtime as runtime
from src.ball_tracking import nba_action_observation as observation
from src.ball_tracking import wasb_adapter as adapter
from src.ball_tracking import wasb_augmentation as augmentation
from src.ball_tracking import wasb_resolution as resolution
from src.ball_tracking import wasb_training as training
from src.ball_tracking.annotations import FrameAnnotation
from tests.test_completion_training_runtime import label
from tests.test_wasb_augmentation import producer_example


class ResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads = torch.get_num_threads()
        torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.old_threads)

    def test_affine_actual_producer_parity_and_native_inverse_at_both_sizes(self):
        for sw, sh in ((1280, 720), (1920, 1080)):
            expected = adapter.affine_matrices(sw, sh)
            actual = resolution.affine_matrices(sw, sh, width=512, height=288)
            for a, b in zip(actual, expected, strict=True):
                np.testing.assert_array_equal(a, b)
            self.assertEqual(resolution.transform_metadata(sw, sh, width=512, height=288),
                             adapter.transform_metadata(sw, sh))
            forward, inverse = resolution.affine_matrices(sw, sh)
            for point in ([0., 0.], [sw / 2, sh / 2], [sw - 1., sh - 1.], [101.25, 230.75]):
                mapped = forward @ np.array([*point, 1], np.float32)
                np.testing.assert_allclose(mapped, np.array(point) * 768 / sw, atol=1e-10)
                np.testing.assert_allclose(inverse @ [*mapped, 1], point, atol=1e-10)
            self.assertAlmostEqual(3.75 * inverse[0, 0], 2.5 * expected[1][0, 0])

    def test_preprocessing_matches_actual512_and_direct_native768_not_double_resize(self):
        rng = np.random.default_rng(45)
        for sw, sh in ((1280, 720), (1920, 1080)):
            frames = [rng.integers(0, 256, (sh, sw, 3), dtype=np.uint8) for _ in range(3)]
            expected, metadata = adapter.preprocess_triplet(frames)
            actual, got_metadata = resolution.preprocess_triplet(frames, width=512, height=288)
            self.assertTrue(torch.equal(actual, expected))
            self.assertEqual(got_metadata, metadata)
            actual768, metadata768 = resolution.preprocess_triplet(frames)
            analytic = np.array([[768 / sw, 0, 0], [0, 768 / sw, 0]], np.float64)
            direct = torch.cat([runtime.normalized_tensor(cv2.warpAffine(f, analytic, (768, 432),
                              flags=cv2.INTER_LINEAR)) for f in frames]).unsqueeze(0)
            self.assertTrue(torch.equal(actual768, direct))
            forward512, _ = adapter.affine_matrices(sw, sh)
            wrong = cv2.resize(cv2.warpAffine(frames[0], forward512, (512, 288)), (768, 432))
            self.assertFalse(torch.equal(actual768[0, :3], runtime.normalized_tensor(wrong)))
            self.assertEqual((metadata768["heatmap_width"], metadata768["heatmap_height"]), (768, 432))

    def test_targets_preserve_actual512_masks_and_source_radius(self):
        for sw, sh in ((1280, 720), (1920, 1080)):
            bounds = type("Bounds", (), {"width_px": sw, "height_px": sh})()
            raws = [label(0, [sw / 2 + 1.25, sh / 2 + .75], "fully_visible"),
                    label(1), label(2, None, "not_visible", "probable"),
                    label(3, None, "indeterminate", "ambiguous")]
            for i, raw in enumerate(raws):
                annotation = FrameAnnotation.from_mapping(raw, i, bounds)
                expected = training.annotation_target(annotation, sw, sh)
                actual = resolution.annotation_target(annotation, sw, sh, width=512, height=288)
                np.testing.assert_array_equal(actual[0], expected[0])
                self.assertEqual(actual[1:], expected[1:])
                result, valid, details = resolution.annotation_target(annotation, sw, sh)
                self.assertEqual(valid, expected[1])
                self.assertEqual(result.shape, (432, 768))
                self.assertEqual(details["kind"], expected[2]["kind"])
                if i == 0:
                    cx, cy = np.array(raw["geometry"]["center_xy_px"]) * 768 / sw
                    expected_center = [int(cx), int(cy)]
                    self.assertEqual(details["integer_heatmap_center"], expected_center)
                    ys, xs = np.nonzero(result)
                    self.assertTrue(((xs - int(cx)) ** 2 + (ys - int(cy)) ** 2 <= 3.75 ** 2).all())
                    self.assertEqual(len(xs), 45)
                else:
                    self.assertFalse(result.any())
            with self.assertRaisesRegex(ValueError, "source footprint"):
                resolution.annotation_target(annotation, sw, sh, radius=2.5)

    def test_stateless_augmentation_is_identical_at512_and_preserves768_masks(self):
        _, example = producer_example()
        arguments = dict(seed=1234, epoch=3, batch_index=88, sample_index=1, triplet_id="real-schedule-position")
        expected, expected_audit = augmentation.augment_example(example, **arguments)
        actual, audit = resolution.augment_example(example, **arguments)
        self.assertEqual(audit, expected_audit)
        for a, b in zip(actual, expected, strict=True):
            self.assertTrue(torch.equal(a, b))
        image = np.tile(np.arange(256, dtype=np.uint8), (432, 3))
        rgb = np.stack((image, 255 - image, np.roll(image, 1, axis=1)), axis=-1)
        inputs = torch.cat([runtime.normalized_tensor(rgb)] * 3)
        targets = torch.zeros((3, 432, 768), dtype=torch.float32)
        targets[0, 13:17, 81:85] = 1
        mask = torch.tensor([True, True, False])
        original = tuple(t.clone() for t in (inputs, targets, mask))
        python_rng, numpy_rng, torch_rng = random.getstate(), np.random.get_state(), torch.random.get_rng_state()
        result, audit768 = resolution.augment_example((inputs, targets, mask), **arguments)
        self.assertEqual(audit768["input_shape"], [9, 432, 768])
        self.assertEqual(audit768["brightness_gain"], audit["brightness_gain"])
        self.assertEqual(audit768["mirror"], audit["mirror"])
        self.assertTrue(torch.equal(result[1], targets.flip(-1) if audit["mirror"] else targets))
        self.assertFalse(result[1][1:].any())
        self.assertTrue(torch.equal(result[2], mask))
        for a, b in zip((inputs, targets, mask), original, strict=True):
            self.assertTrue(torch.equal(a, b))
        self.assertEqual(random.getstate(), python_rng)
        np.testing.assert_equal(np.random.get_state(), numpy_rng)
        self.assertTrue(torch.equal(torch.random.get_rng_state(), torch_rng))
        identity = resolution.apply_parameters((inputs, targets, mask), mirror=False, brightness_gain=1)
        for a, b in zip(identity, original, strict=True):
            self.assertTrue(torch.equal(a, b))
            self.assertNotEqual(a.data_ptr(), b.data_ptr())

    def test_mean_and_component_consumers_match_actual512_producers(self):
        frames = [{"source_frame_index": i, "source_pts_ticks": i * 17, "png": {"path": str(i)}} for i in range(5)]
        rng = np.random.default_rng(19)
        values = [rng.random((3, 288, 512), dtype=np.float32) * np.float32(.2) for _ in range(3)]
        for value in values:
            value[:, 140:143, 251:255] = .8
            value[:, 34:36, 41:43] = .9
        def provider(selected):
            return values[selected[0]["source_frame_index"]]
        expected = list(observation.stream_means(frames, provider))
        actual = list(resolution.stream_means(frames, provider, width=512, height=288))
        self.assertEqual([x[2] for x in actual], [1, 2, 3, 2, 1])
        for (f, mean, n), (ef, emean, en) in zip(actual, expected, strict=True):
            np.testing.assert_array_equal(mean, emean)
            self.assertEqual((f, n), (ef, en))
            for sw, sh in ((1280, 720), (1920, 1080)):
                manifest = {"source_video": {"width_px": sw, "height_px": sh}, "time_base": "1/1000"}
                segment = {"kind": "synthetic", "source_frame_range_inclusive": [0, 4]}
                self.assertEqual(resolution.select_observation(f, mean, n, manifest, segment, width=512, height=288),
                                 observation.select_observation(f, mean, n, manifest, segment))
        empty = np.full((432, 768), .3, np.float32)
        self.assertEqual(resolution.components_from_heatmap(empty, 1920, 1080), [])
        empty.fill(0)
        empty[216, 384] = .8
        candidate = resolution.components_from_heatmap(empty, 1920, 1080)[0]
        self.assertEqual((candidate["center_x"], candidate["center_y"]), (960, 540))
        short = list(resolution.stream_means(frames[:2], lambda _: self.fail("Must not infer padded triplet")))
        self.assertEqual([(m, n) for _, m, n in short], [(None, 0), (None, 0)])

    def _package(self, root, role="training"):
        frames = []
        for i in range(3):
            rgb = np.full((720, 1280, 3), 37 + i * 74, np.uint8)
            rgb[358:363, 638:643] = (244, 89, 18)
            path = root / f"frame{i}.png"
            Image.fromarray(rgb).save(path)
            annotation = [label(i, [640, 360], "fully_visible"), label(i),
                          label(i, None, "indeterminate", "ambiguous")][i]
            frames.append({"source_frame_index": i, "source_pts_ticks": i * 1500, "duration_ticks": 1500,
                "png": {**runtime.binding(root, path), "rgb_sha256": hashlib.sha256(rgb.tobytes()).hexdigest()},
                "annotation": annotation})
        block = {"block_id": "native-test", "game_id": "g", "domain": "nba", "role": role,
                 "source_video": {"width_px": 1280, "height_px": 720}, "time_base": "1/90000",
                 "range_inclusive": [0, 2], "frames": frames}
        return {"training_blocks": [block] if role == "training" else [],
                "validation_blocks": [block] if role != "training" else []}, block

    def test_native_cache_examples_role_guard_and_corruption_detection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package, block = self._package(root)
            store = resolution.FrameStore(root, package, root / "cache")
            try:
                receipt = store.prepare()
                self.assertEqual(receipt["resolution"], {"width": 768, "height": 432, "target_radius": 3.75})
                triplet = {"block_id": block["block_id"], "frame_indices": [0, 1, 2], "valid_output_channels": [True, True, False]}
                inputs, targets, masks = store.example(triplet)
                self.assertEqual(tuple(inputs.shape), (9, 432, 768))
                self.assertEqual(masks.tolist(), [True, True, False])
                self.assertEqual(targets[0].sum().item(), 45)
                self.assertFalse(targets[1:].any())
                source = []
                for f in block["frames"]:
                    with Image.open(root / f["png"]["path"]) as image:
                        source.append(np.asarray(image).copy())
                expected, _ = resolution.preprocess_triplet(source)
                self.assertTrue(torch.equal(inputs.unsqueeze(0), expected))
                with self.assertRaisesRegex(ValueError, "Supervision mask"):
                    store.example({**triplet, "valid_output_channels": [True, True, True]})
                store.blocks[block["block_id"]]["role"] = "checkpoint_validation"
                with self.assertRaisesRegex(ValueError, "Validation block"):
                    store.example(triplet)
                store.blocks[block["block_id"]]["role"] = "training"
            finally:
                store.close()
            cached = next((root / "cache").rglob("frames.npy"))
            with cached.open("r+b") as stream:
                stream.seek(-1, 2)
                stream.write(b"\x00")
            bad = resolution.FrameStore(root, package, root / "cache")
            try:
                with self.assertRaises(ValueError):
                    bad.prepare()
            finally:
                bad.close()

    def test_emitted768_observations_pass_actual_scorer_and_native_join(self):
        class SyntheticModel(torch.nn.Module):
            def forward(self, inputs):
                logits = torch.full((len(inputs), 3, 432, 768), -20., dtype=torch.float32)
                logits[:, 0, 216, 384] = 20.
                return {0: logits}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package, block = self._package(root, "checkpoint_validation")
            store = resolution.FrameStore(root, package, root / "cache")
            try:
                store.prepare()
                model = SyntheticModel()
                records, calls = resolution.infer(block, model, torch.device("cpu"), store, root / "means.npy", "synthetic")
                self.assertEqual(calls, 1)
                self.assertEqual([r["source_frame_index"] for r in records], [0, 1, 2])
                self.assertEqual([r["center_xy_px"] for r in records], [[640., 360.], None, None])
                scored = runtime.scored_block(block, records)
                self.assertEqual((scored["matched"], scored["wrong"], scored["certain_hidden_emissions"]), (1, 0, 0))
                emitted = resolution.validate_epoch(model, torch.device("cpu"), store, package, 0, {"synthetic": True})
                self.assertEqual(emitted["resolution"], {"width": 768, "height": 432, "target_radius": 3.75})
                self.assertEqual(emitted["cohorts"]["nba_validation"]["matched"], 1)
                self.assertEqual([r["outcome"] for r in emitted["blocks"][0]["frame_results"]], ["matched", "hidden_quiet", "unscored"])
                means = np.load(root / "means.npy", mmap_mode="r")
                self.assertEqual(means.shape, (3, 432, 768))
                means._mmap.close()
                with self.assertRaisesRegex(ValueError, "already exists"):
                    resolution.infer(block, model, torch.device("cpu"), store, root / "means.npy", "synthetic")
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
