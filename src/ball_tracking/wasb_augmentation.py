"""Training-only synchronized mirror/brightness, additive to the frozen producer.

Inputs must be the untouched CPU float32 uint8-derived FrameStore.example output.
The exact normalization roundtrip is verified before augmentation. No global RNG
is read or changed, and no input tensor is modified or returned by reference.
"""
from __future__ import annotations

import hashlib
import json
import math

import torch


POLICY = {
    "id": "wasb_synchronized_mirror_brightness_v0_1",
    "mirror": {"axis": "last_image_and_rasterized_target_x_index", "probability": 0.5},
    "brightness": {"gain_min": 0.9, "gain_max": 1.1, "space": "recovered_uint8_RGB_as_float32",
                   "clamp": [0.0, 255.0], "post_gain_quantization": False},
    "synchronization": "one_mirror_and_gain_shared_by_all_three_frames",
    "rng": {"algorithm": "sha256_canonical_key_first_two_big_endian_uint64_top53_div_2pow53",
            "key_fields": ["policy_id", "seed", "epoch", "batch_index", "sample_index"],
            "epoch_base": 1, "batch_index_base": 1, "sample_index_base": 0,
            "uniform_interval": "[0,1)", "global_rng_access": False},
    "normalization": {"mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225],
                      "original_pixel_recovery": "round_inverse_then_verify_exact_normalized_roundtrip"},
    "mask_policy": "unchanged", "hidden_target_policy": "zero_unchanged",
    "resize": False, "crop": False, "rotation": False, "blur": False,
    "new_visibility_labels": False,
}


def check(value, message):
    if not value:
        raise ValueError(message)


def parameters(*, seed=1234, epoch, batch_index, sample_index):
    """One stateless draw per immutable schedule position, independent of call order."""
    for name, value, minimum in (("seed", seed, 0), ("epoch", epoch, 1),
                                 ("batch_index", batch_index, 1), ("sample_index", sample_index, 0)):
        check(type(value) is int and value >= minimum, "Invalid augmentation key: " + name)
    key = {"policy_id": POLICY["id"], "seed": seed, "epoch": epoch,
           "batch_index": batch_index, "sample_index": sample_index}
    key_bytes = json.dumps(key, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    digest = hashlib.sha256(key_bytes).digest()
    mirror_u, gain_u = [(int.from_bytes(digest[start:start+8], "big") >> 11) / (1 << 53)
                        for start in (0, 8)]
    return {"schema_version": "wasb_augmentation_parameters/v0.1", **key,
            "key_sha256": digest.hex(), "mirror_uniform": mirror_u, "brightness_uniform": gain_u,
            "mirror": mirror_u < 0.5, "brightness_gain": 0.9 + 0.2 * gain_u}


def _statistics():
    mean = torch.tensor(POLICY["normalization"]["mean"], dtype=torch.float32).repeat(3)[:, None, None]
    std = torch.tensor(POLICY["normalization"]["std"], dtype=torch.float32).repeat(3)[:, None, None]
    return mean, std


def recover_uint8_pixels(inputs):
    """Recover integer-valued float32 pixels; reject inputs from another producer."""
    check(isinstance(inputs, torch.Tensor) and inputs.device.type == "cpu"
          and inputs.dtype == torch.float32 and tuple(inputs.shape) == (9, 288, 512)
          and not inputs.requires_grad, "Expected untouched CPU FrameStore normalized triplet")
    check(bool(torch.isfinite(inputs).all()), "Nonfinite normalized input")
    mean, std = _statistics()
    pixels = torch.round(inputs.mul(std).add(mean).mul(255))
    check(bool(((pixels >= 0) & (pixels <= 255)).all()), "Recovered pixels outside uint8 range")
    reconstructed = pixels.div(255).sub(mean).div(std)
    check(torch.equal(reconstructed, inputs), "Input is not the exact frozen uint8 normalization")
    return pixels


def apply_parameters(example, *, mirror, brightness_gain):
    """Apply a fixed parameter pair; public for focused endpoint/alignment checks.

    Production uses augment_example, which fixes parameters from schedule keys.
    The helper permits only the same frozen gain bounds; identity is allowed.
    """
    check(isinstance(example, (tuple, list)) and len(example) == 3, "Expected image/target/mask example")
    inputs, targets, valid = example
    check(type(mirror) is bool, "Mirror must be Boolean")
    check(type(brightness_gain) in (int, float) and math.isfinite(brightness_gain)
          and 0.9 <= brightness_gain <= 1.1, "Brightness gain outside frozen bounds")
    pixels = recover_uint8_pixels(inputs)
    check(isinstance(targets, torch.Tensor) and targets.device.type == "cpu"
          and targets.dtype == torch.float32 and tuple(targets.shape) == (3, 288, 512)
          and not targets.requires_grad and bool(((targets == 0) | (targets == 1)).all()),
          "Expected CPU rasterized binary targets")
    check(isinstance(valid, torch.Tensor) and valid.device.type == "cpu"
          and valid.dtype == torch.bool and tuple(valid.shape) == (3,), "Expected CPU channel mask")
    check(not bool(targets[~valid].any()), "Masked target must retain the frozen zero map")
    if brightness_gain == 1:
        augmented = inputs.flip(-1) if mirror else inputs.clone()
    else:
        if mirror:
            pixels = pixels.flip(-1)
        mean, std = _statistics()
        augmented = pixels.mul(float(brightness_gain)).clamp(0, 255).div(255).sub(mean).div(std)
    return (augmented, targets.flip(-1) if mirror else targets.clone(), valid.clone())


def augment_example(example, *, seed=1234, epoch, batch_index, sample_index, triplet_id=None):
    """Return ((inputs, targets, masks), audit); triplet_id is provenance, not RNG."""
    check(triplet_id is None or isinstance(triplet_id, str) and bool(triplet_id), "Invalid triplet provenance")
    audit = parameters(seed=seed, epoch=epoch, batch_index=batch_index, sample_index=sample_index)
    result = apply_parameters(example, mirror=audit["mirror"], brightness_gain=audit["brightness_gain"])
    audit.update(triplet_id=triplet_id, shared_frame_count=3, input_shape=list(example[0].shape),
                 targets_mirrored_with_images=True, channel_masks_unchanged=True,
                 source_uint8_recovery_verified=True, original_inputs_mutated=False)
    return result, audit
