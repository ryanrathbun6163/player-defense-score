"""CPU producer/consumer alignment and deterministic augmentation checks."""
import copy
import hashlib
import json
from pathlib import Path
import random
import tempfile
import unittest

import numpy as np
from PIL import Image
import torch

from src.ball_tracking import completion_training_runtime as runtime
from src.ball_tracking import wasb_augmentation as aug
from tests.test_completion_training_runtime import label


def producer_example():
    values = np.tile(np.arange(256, dtype=np.uint8), (288, 2))
    images = [np.stack((values, np.roll(values, index+1, axis=1), 255-values), axis=-1)
              for index in range(3)]
    inputs = torch.cat([runtime.normalized_tensor(image) for image in images])
    targets = torch.zeros((3, 288, 512), dtype=torch.float32)
    targets[0, 100:103, 40:43] = 1
    return images, (inputs, targets, torch.tensor([True, True, False]))


class AugmentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_threads = torch.get_num_threads()
        torch.set_num_threads(2)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.old_threads)

    def test_all_uint8_values_exactly_recovered_from_actual_normalization(self):
        images, example = producer_example()
        actual = aug.recover_uint8_pixels(example[0])
        expected = torch.cat([torch.from_numpy(image.transpose(2, 0, 1).copy()).float() for image in images])
        self.assertTrue(torch.equal(actual, expected))
        self.assertEqual(set(actual.flatten().tolist()), set(range(256)))

    def test_identity_is_bit_exact_and_allocates_independent_outputs(self):
        _, example = producer_example()
        copied = tuple(t.clone() for t in example)
        result = aug.apply_parameters(example, mirror=False, brightness_gain=1)
        for before, after, expected in zip(example, result, copied, strict=True):
            self.assertTrue(torch.equal(before, after))
            self.assertTrue(torch.equal(before, expected))
            self.assertNotEqual(before.data_ptr(), after.data_ptr())
        result[0].zero_()
        result[1].zero_()
        result[2].zero_()
        self.assertTrue(all(torch.equal(before, expected) for before, expected in zip(example, copied, strict=True)))

    def test_exact_horizontal_reflection_preserves_binary_support_and_masks(self):
        _, example = producer_example()
        result = aug.apply_parameters(example, mirror=True, brightness_gain=1)
        self.assertTrue(torch.equal(result[0], example[0].flip(-1)))
        self.assertTrue(torch.equal(result[1], example[1].flip(-1)))
        self.assertEqual(result[1][0].nonzero()[:, 1].unique().tolist(), [469, 470, 471])
        self.assertEqual(result[1].sum().item(), example[1].sum().item())
        self.assertTrue(torch.equal(result[2], example[2]))
        self.assertEqual(result[1][1:].count_nonzero().item(), 0)

    def test_brightness_endpoints_use_source_pixel_space_no_postgain_rounding(self):
        images, example = producer_example()
        mean = torch.tensor([.485, .456, .406])[:, None, None]
        std = torch.tensor([.229, .224, .225])[:, None, None]
        for gain in (.9, 1.1):
            for mirror in (False, True):
                with self.subTest(gain=gain, mirror=mirror):
                    result = aug.apply_parameters(example, mirror=mirror, brightness_gain=gain)
                    expected = []
                    for image in images:
                        source = torch.from_numpy(image.transpose(2, 0, 1).copy()).float()
                        source = source.flip(-1) if mirror else source
                        changed = source.mul(gain).clamp(0, 255)
                        expected.append(changed.div(255).sub(mean).div(std))
                    self.assertTrue(torch.equal(result[0], torch.cat(expected)))
                    self.assertTrue(torch.equal(result[1], example[1].flip(-1) if mirror else example[1]))
                    self.assertTrue(torch.equal(result[2], example[2]))
        # Pixel1 becomes0.9, not an implicitly rounded1, in every RGB/time channel.
        source = np.ones((288, 512, 3), dtype=np.uint8)
        one = (torch.cat([runtime.normalized_tensor(source)]*3), example[1], example[2])
        result = aug.apply_parameters(one, mirror=False, brightness_gain=.9)[0]
        self.assertFalse(torch.equal(result, one[0]))

    def test_stateless_key_matches_independent_sha256_and_is_order_independent(self):
        key = {"policy_id": aug.POLICY["id"], "seed": 1234, "epoch": 1, "batch_index": 2, "sample_index": 0}
        digest = hashlib.sha256(json.dumps(key, sort_keys=True, separators=(",", ":")).encode()).digest()
        expected = [(int.from_bytes(digest[s:s+8], "big") >> 11)/(2**53) for s in (0, 8)]
        first = aug.parameters(seed=1234, epoch=1, batch_index=2, sample_index=0)
        self.assertEqual([first["mirror_uniform"], first["brightness_uniform"]], expected)
        self.assertEqual(first["mirror"], expected[0] < .5)
        self.assertEqual(first["brightness_gain"], .9+.2*expected[1])
        other = aug.parameters(seed=1234, epoch=2, batch_index=2, sample_index=0)
        self.assertNotEqual(first["key_sha256"], other["key_sha256"])
        self.assertEqual(first, aug.parameters(seed=1234, epoch=1, batch_index=2, sample_index=0))

    def test_does_not_access_or_mutate_global_rng_or_input_tensors(self):
        _, example = producer_example()
        before = tuple(t.clone() for t in example)
        python_state, numpy_state, torch_state = random.getstate(), np.random.get_state(), torch.get_rng_state().clone()
        first, record = aug.augment_example(example, epoch=3, batch_index=4, sample_index=1, triplet_id="triplet-a")
        second, changed_record = aug.augment_example(example, epoch=3, batch_index=4, sample_index=1, triplet_id="triplet-b")
        self.assertEqual(random.getstate(), python_state)
        numpy_after = np.random.get_state()
        self.assertEqual(numpy_after[0], numpy_state[0])
        self.assertTrue(np.array_equal(numpy_after[1], numpy_state[1]))
        self.assertEqual(numpy_after[2:], numpy_state[2:])
        self.assertTrue(torch.equal(torch.get_rng_state(), torch_state))
        self.assertTrue(all(torch.equal(a, b) for a, b in zip(example, before, strict=True)))
        self.assertTrue(all(torch.equal(a, b) for a, b in zip(first, second, strict=True)))
        self.assertEqual(record["key_sha256"], changed_record["key_sha256"])
        self.assertEqual(json.loads(json.dumps(record, allow_nan=False)), record)

    def test_actual_framestore_example_alignment_positive_hidden_and_masked(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = {"width_px": 1920, "height_px": 1080}
            frames = []
            for index in range(3):
                rgb = np.zeros((1080, 1920, 3), np.uint8)
                rgb[:, :, :] = [30+index, 90+index, 200-index]
                rgb[360:390, 600:630] = 255
                path = root / f"frame{index}.png"
                Image.fromarray(rgb).save(path)
                annotation = (label(index, [615., 375.], "fully_visible") if index == 0 else
                              label(index) if index == 1 else label(index, None, "indeterminate", "ambiguous"))
                frames.append({"source_frame_index": index, "source_pts_ticks": 512*(index+1), "duration_ticks": 512,
                               "png": {**runtime.binding(root, path), "rgb_sha256": hashlib.sha256(rgb.tobytes()).hexdigest()},
                               "annotation": annotation})
            block = {"block_id": "actual_fixture", "game_id": "fixture", "domain": "nfhs", "role": "training",
                     "source_video": source, "time_base": "1/12800", "frames": frames}
            store = runtime.FrameStore(root, {"training_blocks": [block], "validation_blocks": []}, root / "cache")
            try:
                store.prepare()
                original = store.example({"block_id": block["block_id"], "frame_indices": [0, 1, 2],
                                          "valid_output_channels": [True, True, False]})
                saved = tuple(t.clone() for t in original)
                result = aug.apply_parameters(original, mirror=True, brightness_gain=1.1)
                self.assertEqual(result[2].tolist(), [True, True, False])
                self.assertEqual(result[1][1:].count_nonzero().item(), 0)
                yy, xx = original[1][0].nonzero(as_tuple=True)
                self.assertTrue(torch.equal(result[1][0, yy, 511-xx], torch.ones_like(xx).float()))
                self.assertEqual(result[1][0].sum().item(), original[1][0].sum().item())
                # The actual frozen target center and reflected bright object occupy
                # the same model-grid region after exactly one index reversal.
                target_y, target_x = round(yy.float().mean().item()), round(xx.float().mean().item())
                mean, std = torch.tensor([.485, .456, .406]), torch.tensor([.229, .224, .225])
                color = (result[0][:3, target_y, 511-target_x]*std+mean)*255
                self.assertTrue(torch.allclose(color, torch.full((3,), 255.), atol=3e-5))
                self.assertTrue(all(torch.equal(a, b) for a, b in zip(original, saved, strict=True)))
            finally:
                store.close()

    def test_bad_keys_shapes_nonfinite_nonbinary_and_nonproducer_inputs_rejected(self):
        _, example = producer_example()
        for key in ({"epoch": 0, "batch_index": 1, "sample_index": 0},
                    {"epoch": 1, "batch_index": 0, "sample_index": 0},
                    {"epoch": 1, "batch_index": 1, "sample_index": -1},
                    {"epoch": True, "batch_index": 1, "sample_index": 0}):
            with self.assertRaises(ValueError):
                aug.parameters(**key)
        for gain in (.89, 1.11, float("nan"), True):
            with self.assertRaises(ValueError):
                aug.apply_parameters(example, mirror=False, brightness_gain=gain)
        for which, value in ((0, float("nan")), (0, .12345), (1, .5)):
            changed = tuple(t.clone() for t in example)
            changed[which].flatten()[0] = value
            with self.assertRaises(ValueError):
                aug.apply_parameters(changed, mirror=False, brightness_gain=1)
        with self.assertRaises(ValueError):
            aug.apply_parameters((example[0].half(), *example[1:]), mirror=False, brightness_gain=1)


if __name__ == "__main__":
    unittest.main()
