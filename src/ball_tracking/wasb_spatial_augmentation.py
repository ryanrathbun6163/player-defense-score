"""Training-only scale/translation after the unchanged mirror/brightness producer.

Integer image indices are pixel centers. A forward transform maps p to
``scale * (p - (size - 1)/2) + (size - 1)/2 + translation``. Images use bilinear
inverse sampling; the *existing* binary target raster uses nearest sampling.
No disk is regenerated at a rounded transformed center. Geometry comes from the
same accepted block annotations as FrameStore, never inferred from target pixels.
"""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np
import torch
from torch.nn import functional as F

from . import wasb_augmentation as legacy
from . import wasb_resolution as resolution
from . import wasb_training as training
from .annotations import FrameAnnotation


WIDTH, HEIGHT = resolution.WIDTH, resolution.HEIGHT
POLICY = {
    "id": "wasb_synchronized_spatial_v0_1",
    "probability": 0.5,
    "scale": [0.9, 1.1],
    "translation_fraction": [-0.03, 0.03],
    "order": "frozen_mirror_brightness_then_spatial",
    "pixel_centers": "integer_indices",
    "scale_center_xy": [(WIDTH - 1) / 2, (HEIGHT - 1) / 2],
    "image_extent_xyxy": [-0.5, -0.5, WIDTH - 0.5, HEIGHT - 0.5],
    "image_interpolation": "torch_grid_sample_bilinear",
    "target_interpolation": "torch_grid_sample_nearest_original_binary_raster",
    "align_corners": False,
    "padding": "constant_normalized_zero_equals_ImageNet_RGB_mean",
    "target_padding": 0,
    "clip_check": "union_of_frozen_target_pixel_cells_and_continuous_annotation_uncertainty_circle",
    "clip_response": "whole_triplet_spatial_identity_preserving_mirror_brightness",
    "mask_policy": "unchanged",
    "hidden_target_policy": "zero_unchanged",
    "synchronization": "same_transform_for_all_three_frames_and_targets",
    "rng": {
        "algorithm": "sha256_canonical_key_four_big_endian_uint64_top53_div_2pow53",
        "key_fields": ["policy_id", "seed", "epoch", "batch_index", "sample_index"],
        "uniform_interval": "[0,1)", "global_rng_access": False,
        "independent_of": legacy.POLICY["id"],
    },
}
check = resolution.check


def parameters(*, seed=1234, epoch, batch_index, sample_index):
    """Independent keyed draws; never advance Python, NumPy or Torch RNG state."""
    for name, value, minimum in (("seed", seed, 0), ("epoch", epoch, 1),
                                 ("batch_index", batch_index, 1), ("sample_index", sample_index, 0)):
        check(type(value) is int and value >= minimum, "Invalid spatial key: " + name)
    key = {"policy_id": POLICY["id"], "seed": seed, "epoch": epoch,
           "batch_index": batch_index, "sample_index": sample_index}
    digest = hashlib.sha256(json.dumps(key, sort_keys=True, separators=(",", ":"),
                                      allow_nan=False).encode("utf-8")).digest()
    draws = [(int.from_bytes(digest[i:i + 8], "big") >> 11) / (1 << 53) for i in (0, 8, 16, 24)]
    return {"schema_version": "wasb_spatial_parameters/v0.1", **key, "key_sha256": digest.hex(),
            "apply_uniform": draws[0], "scale_uniform": draws[1],
            "translation_x_uniform": draws[2], "translation_y_uniform": draws[3],
            "requested": draws[0] < POLICY["probability"], "scale": .9 + .2 * draws[1],
            "translation_x_px": (-.03 + .06 * draws[2]) * WIDTH,
            "translation_y_px": (-.03 + .06 * draws[3]) * HEIGHT}


def matrices(*, scale, translation_x_px, translation_y_px):
    """Forward/inverse 2x3 matrices in pixel-center coordinates, not grid units."""
    check(type(scale) in (int, float) and math.isfinite(scale) and .9 <= scale <= 1.1,
          "Spatial scale outside policy")
    for value, size in ((translation_x_px, WIDTH), (translation_y_px, HEIGHT)):
        check(type(value) in (int, float) and math.isfinite(value) and abs(value) <= .03 * size,
              "Spatial translation outside policy")
    cx, cy = POLICY["scale_center_xy"]
    bx, by = (1 - scale) * cx + translation_x_px, (1 - scale) * cy + translation_y_px
    return [[float(scale), 0., float(bx)], [0., float(scale), float(by)]], [
        [1. / scale, 0., -bx / scale], [0., 1. / scale, -by / scale]]


def geometry(triplet, block, *, mirror, scale, translation_x_px, translation_y_px):
    """Metadata-only support check, sharing FrameStore's actual annotation parser.

    The finite target disk contains integer offsets -3..3 at radius 3.75. Its
    enclosing pixel-cell box includes the half-pixel nearest-sampling footprint.
    Annotation uncertainty is separately transformed about the *continuous*
    source center; it is not a larger loss target or a certainty upgrade.
    """
    check(type(mirror) is bool, "Mirror must be Boolean")
    check(block["role"] == "training" and triplet["block_id"] == block["block_id"],
          "Spatial input must join an actual training block")
    indices = triplet["frame_indices"]
    check(len(indices) == 3 and indices == list(range(indices[0], indices[0] + 3)),
          "Spatial geometry requires a native triplet")
    source = block["source_video"]
    sw, sh = source["width_px"], source["height_px"]
    bounds = type("Bounds", (), {"width_px": sw, "height_px": sh})()
    source_forward, _ = resolution.affine_matrices(sw, sh)
    forward, inverse = matrices(scale=scale, translation_x_px=translation_x_px,
                                translation_y_px=translation_y_px)
    factor = float(source_forward[0, 0])
    check(factor > 0 and np.allclose(source_forward[:2, :2], np.eye(2) * factor),
          "Unexpected source affine for uncertainty-circle transport")
    channels, clipped = [], []
    actual_valid = []
    extent = POLICY["image_extent_xyxy"]
    def mapped(point):
        return [forward[0][0] * point[0] + forward[0][2],
                forward[1][1] * point[1] + forward[1][2]]
    def box(cx, cy, radius):
        return [cx - radius, cy - radius, cx + radius, cy + radius]
    def contained(value):
        return value[0] >= extent[0] and value[1] >= extent[1] and value[2] <= extent[2] and value[3] <= extent[3]
    for channel, index in enumerate(indices):
        offset = index - block["frames"][0]["source_frame_index"]
        check(0 <= offset < len(block["frames"]), "Triplet frame outside block")
        frame = block["frames"][offset]
        check(frame["source_frame_index"] == index and frame["annotation"]["frame_index"] == index,
              "Spatial annotation/frame join differs")
        annotation = FrameAnnotation.from_mapping(frame["annotation"], offset, bounds)
        kind = training.annotation_kind(annotation)
        check(frame["kind"] == kind and frame["valid_output_channel"] == (kind != "masked"),
              "Frame metadata differs from annotation producer")
        actual_valid.append(kind != "masked")
        item = {"channel": channel, "source_frame_index": index, "kind": kind,
                "visibility": annotation.visibility, "difficulty_tags": list(annotation.difficulty_tags),
                "clipping_reasons": []}
        if kind == "positive":
            point = np.array([*annotation.geometry.center_xy_px, 1.], np.float32)
            continuous = source_forward @ point
            integer = continuous.astype(np.int32)
            original_integer = integer.tolist()
            unmirrored_continuous = continuous.tolist()
            continuous = continuous.tolist()
            integer = integer.tolist()
            if mirror:
                continuous[0], integer[0] = WIDTH - 1 - continuous[0], WIDTH - 1 - integer[0]
            transformed_center = mapped(integer)
            transformed_annotation = mapped(continuous)
            radius = float(annotation.geometry.uncertainty_radius_px) * factor
            target_before = box(*integer, math.floor(resolution.TARGET_RADIUS) + .5)
            target_after = box(*transformed_center, (math.floor(resolution.TARGET_RADIUS) + .5) * scale)
            uncertainty_before = box(*continuous, radius)
            uncertainty_after = box(*transformed_annotation, radius * scale)
            # An already clipped source raster cannot acquire missing support by augmentation.
            for name, value in (("source_target_support", target_before), ("source_uncertainty_support", uncertainty_before),
                                ("transformed_target_support", target_after), ("transformed_uncertainty_support", uncertainty_after)):
                if not contained(value):
                    item["clipping_reasons"].append(name)
            item.update(source_center_xy=list(annotation.geometry.center_xy_px),
                        source_uncertainty_radius_px=float(annotation.geometry.uncertainty_radius_px),
                        original_integer_heatmap_center=original_integer,
                        original_continuous_heatmap_center=unmirrored_continuous,
                        mirrored_integer_heatmap_center=integer, mirrored_continuous_heatmap_center=continuous,
                        proposed_integer_center_transport=transformed_center,
                        proposed_annotation_center_transport=transformed_annotation,
                        target_cell_bounds_before=target_before, target_cell_bounds_proposed=target_after,
                        uncertainty_bounds_before=uncertainty_before, uncertainty_bounds_proposed=uncertainty_after,
                        uncertainty_radius_working=radius, proposed_uncertainty_radius_working=radius * scale)
            if item["clipping_reasons"]:
                clipped.append(channel)
        channels.append(item)
    check(actual_valid == triplet["valid_output_channels"] and any(actual_valid),
          "Spatial supervision mask differs from triplet producer")
    return {"block_id": block["block_id"], "frame_indices": indices.copy(),
            "source_dimensions": [sw, sh], "source_to_heatmap": source_forward.tolist(),
            "mirror_already_applied": mirror, "proposed_forward": forward, "proposed_inverse": inverse,
            "channels": channels, "clipped_channels": clipped}


def plan(triplet, block, *, seed=1234, epoch, batch_index, sample_index, triplet_id=None):
    """Plan all decisions/geometry without images, tensor rasterization or RNG."""
    triplet_id = triplet["triplet_id"] if triplet_id is None else triplet_id
    check(triplet_id == triplet["triplet_id"], "Spatial triplet provenance differs")
    keys = dict(seed=seed, epoch=epoch, batch_index=batch_index, sample_index=sample_index)
    draw = parameters(**keys)
    geo = geometry(triplet, block, mirror=legacy.parameters(**keys)["mirror"],
                   **{k: draw[k] for k in ("scale", "translation_x_px", "translation_y_px")})
    applied = draw["requested"] and not geo["clipped_channels"]
    effective = {k: draw[k] for k in ("scale", "translation_x_px", "translation_y_px")} if applied else {
        "scale": 1., "translation_x_px": 0., "translation_y_px": 0.}
    forward, inverse = matrices(**effective)
    return {"schema_version": "wasb_spatial_augmentation/v0.1", "triplet_id": triplet_id,
            "parameters": draw, "geometry": geo, "applied": applied,
            "identity_reason": None if applied else "clipped_supervised_support" if draw["requested"] else "probability_not_selected",
            "effective_parameters": effective, "effective_forward": forward, "effective_inverse": inverse,
            "input_shape": [9, HEIGHT, WIDTH], "shared_frame_count": 3,
            "original_inputs_mutated": False, "channel_masks_unchanged": True,
            "target_raster_regenerated": False, "padding_normalized_value": 0.}


def validate_audit(audit, *, triplet, block, seed=1234, epoch, batch_index, sample_index, triplet_id=None):
    """Exact metadata-only replay for resumed history; no image/model operations."""
    check(audit == plan(triplet, block, seed=seed, epoch=epoch, batch_index=batch_index,
                        sample_index=sample_index, triplet_id=triplet_id), "Spatial audit differs from deterministic plan")
    return True


def apply_parameters(example, *, scale, translation_x_px, translation_y_px):
    """Low-level fixed transform for checks; production uses the clipping planner."""
    inputs, targets, valid = example
    _, inverse = matrices(scale=scale, translation_x_px=translation_x_px, translation_y_px=translation_y_px)
    check(isinstance(inputs, torch.Tensor) and inputs.device.type == "cpu" and inputs.dtype == torch.float32
          and tuple(inputs.shape) == (9, HEIGHT, WIDTH) and not inputs.requires_grad and bool(torch.isfinite(inputs).all()),
          "Expected finite CPU normalized 768 triplet")
    check(isinstance(targets, torch.Tensor) and targets.device.type == "cpu" and targets.dtype == torch.float32
          and tuple(targets.shape) == (3, HEIGHT, WIDTH) and not targets.requires_grad
          and bool(((targets == 0) | (targets == 1)).all()), "Expected original binary target raster")
    check(isinstance(valid, torch.Tensor) and valid.device.type == "cpu" and valid.dtype == torch.bool
          and tuple(valid.shape) == (3,) and not bool(targets[~valid].any()), "Invalid spatial channel masks")
    if scale == 1 and translation_x_px == 0 and translation_y_px == 0:
        return inputs.clone(), targets.clone(), valid.clone()
    # grid_sample align_corners=False maps grid g to ((g+1)*size-1)/2.
    # Compose its inverse with our pixel-coordinate inverse; no half-pixel shift.
    xs = torch.arange(WIDTH, dtype=torch.float32) * inverse[0][0] + inverse[0][2]
    ys = torch.arange(HEIGHT, dtype=torch.float32) * inverse[1][1] + inverse[1][2]
    gx, gy = 2 * (xs + .5) / WIDTH - 1, 2 * (ys + .5) / HEIGHT - 1
    grid = torch.stack((gx[None, :].expand(HEIGHT, WIDTH), gy[:, None].expand(HEIGHT, WIDTH)), -1)[None]
    transformed = F.grid_sample(inputs[None], grid, mode="bilinear", padding_mode="zeros", align_corners=False)[0]
    target = F.grid_sample(targets[None], grid, mode="nearest", padding_mode="zeros", align_corners=False)[0]
    check(bool(((target == 0) | (target == 1)).all()) and not bool(target[~valid].any()),
          "Spatial target interpolation changed binary/masked semantics")
    return transformed, target, valid.clone()


def augment_example(example, *, triplet, block, seed=1234, epoch, batch_index, sample_index, triplet_id=None):
    """Return transformed example and separate frozen/new audit records."""
    triplet_id = triplet["triplet_id"] if triplet_id is None else triplet_id
    keys = dict(seed=seed, epoch=epoch, batch_index=batch_index, sample_index=sample_index, triplet_id=triplet_id)
    spatial_audit = plan(triplet, block, **keys)
    check(example[2].tolist() == triplet["valid_output_channels"], "Example mask differs from accepted metadata")
    augmented, old_audit = resolution.augment_example(example, **keys)
    result = apply_parameters(augmented, **spatial_audit["effective_parameters"])
    return result, {"augmentation": old_audit, "spatial_augmentation": spatial_audit}
