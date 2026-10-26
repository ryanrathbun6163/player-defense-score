"""Resolution-aware WASB primitives, separate from every frozen 512px producer.

The approved arm changes working sampling density and its coupled target radius.
Native frames, annotation masks, normalization, triplet averaging, component
selection and deterministic augmentation arithmetic retain their original rules.
The 512x288 parameterization exists for direct producer/consumer parity checks.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
from pathlib import Path
import time
import uuid

import cv2
import numpy as np
from PIL import Image
import torch

from . import completion_training_runtime as runtime
from . import wasb_adapter as adapter
from . import wasb_training as training
from . import wasb_augmentation as augmentation
from .annotations import FrameAnnotation
from .wasb_experiment import bound_path, canonical, digest_file

WIDTH, HEIGHT, TARGET_RADIUS = 768, 432, 3.75
check = runtime.check


def dimensions(width, height):
    check(type(width) is int and type(height) is int and width > 0 and height > 0
          and width % 8 == 0 and height % 8 == 0 and width * 9 == height * 16,
          "Working dimensions must be 16:9 positive multiples of eight")
    return width, height


def affine_matrices(source_width, source_height, *, width=WIDTH, height=HEIGHT):
    """Original float32 control points and OpenCV affine at explicit dimensions."""
    dimensions(width, height)
    source_width = adapter._dimension(source_width, "source_width")
    source_height = adapter._dimension(source_height, "source_height")
    center = np.array([source_width / 2.0, source_height / 2.0], dtype=np.float32)
    scale = np.float32(max(source_width, source_height))
    src, dst = np.zeros((3, 2), np.float32), np.zeros((3, 2), np.float32)
    src[0], src[1] = center, center + np.array([0, scale * -0.5])
    dst[0] = [width * 0.5, height * 0.5]
    dst[1] = dst[0] + np.array([0, width * -0.5], np.float32)
    for points in (src, dst):
        direct = points[0] - points[1]
        points[2] = points[1] + np.array([-direct[1], direct[0]], np.float32)
    return cv2.getAffineTransform(src, dst), cv2.getAffineTransform(dst, src)


def transform_metadata(source_width, source_height, *, width=WIDTH, height=HEIGHT):
    forward, inverse = affine_matrices(source_width, source_height, width=width, height=height)
    return {"source_width": int(source_width), "source_height": int(source_height),
            "heatmap_width": width, "heatmap_height": height,
            "source_to_heatmap": forward.tolist(), "heatmap_to_source": inverse.tolist(),
            "interpolation": "cv2.INTER_LINEAR", "border": "constant_zero", "color_order": "RGB"}


def preprocess_triplet(rgb_frames, *, width=WIDTH, height=HEIGHT):
    dimensions(width, height)
    check(len(rgb_frames) == 3, "WASB requires exactly three chronological RGB frames")
    check(all(isinstance(f, np.ndarray) and f.dtype == np.uint8 and f.ndim == 3
              and f.shape[2] == 3 and min(f.shape[:2]) > 0 for f in rgb_frames), "Invalid RGB frames")
    check(all(f.shape == rgb_frames[0].shape for f in rgb_frames), "Triplet source dimensions differ")
    sh, sw = rgb_frames[0].shape[:2]
    forward, _ = affine_matrices(sw, sh, width=width, height=height)
    inputs = torch.cat([runtime.normalized_tensor(cv2.warpAffine(
        f, forward, (width, height), flags=cv2.INTER_LINEAR)) for f in rgb_frames]).unsqueeze(0)
    return inputs, transform_metadata(sw, sh, width=width, height=height)


def annotation_target(annotation, source_width, source_height, *, width=WIDTH, height=HEIGHT, radius=None):
    dimensions(width, height)
    radius = 2.5 * width / 512 if radius is None else radius
    check(type(radius) in (int, float) and math.isfinite(radius) and radius == 2.5 * width / 512,
          "Target radius must preserve the original nominal source footprint")
    target = np.zeros((height, width), np.float32)
    kind, center = training.annotation_kind(annotation), None
    if kind == "positive":
        forward, _ = affine_matrices(source_width, source_height, width=width, height=height)
        x, y = annotation.geometry.center_xy_px
        center = (forward @ np.array([x, y, 1.0], np.float32)).astype(np.int32)
        if center[0] >= 0 and center[1] >= 0:
            yy, xx = np.indices(target.shape)
            target[(xx - center[0]) ** 2 + (yy - center[1]) ** 2 <= radius ** 2] = 1
    return target, kind != "masked", {"kind": kind, "integer_heatmap_center":
                                      None if center is None else center.tolist()}


class FrameStore:
    """Verified native-PNG cache; never resize an existing 512px working image."""
    def __init__(self, root, package, folder, *, width=WIDTH, height=HEIGHT, radius=None):
        self.width, self.height = dimensions(width, height)
        self.radius = 2.5 * width / 512 if radius is None else radius
        check(self.radius == 2.5 * width / 512, "Target radius/source footprint differs")
        self.root, self.folder = Path(root).resolve(), Path(folder).resolve()
        blocks = package["training_blocks"] + package["validation_blocks"]
        self.blocks = {b["block_id"]: b for b in blocks}
        check(len(self.blocks) == len(blocks), "Training/validation block IDs must be unique")
        self.arrays, self.positions, self.labels = {}, {}, {}
        self.identity = {"package_sha256": canonical(package),
                         "resolution_module_sha256": digest_file(Path(__file__)),
                         "normalization_module_sha256": digest_file(Path(runtime.__file__)),
                         "annotation_module_sha256": digest_file(Path(training.__file__)),
                         "representation": f"affine_RGB_uint8_{height}x{width}",
                         "target_radius": self.radius}
        self.folder.mkdir(parents=True, exist_ok=True)

    def prepare(self):
        began, receipts = time.perf_counter(), []
        for block_id, block in self.blocks.items():
            frames = block["frames"]
            indices = [f["source_frame_index"] for f in frames]
            check(indices and indices == list(range(indices[0], indices[-1] + 1)),
                  "Block native frames must be consecutive and unique")
            check(all(f["annotation"]["frame_index"] == f["source_frame_index"] for f in frames),
                  "Annotation/native-frame join differs")
            check(all(type(f["duration_ticks"]) is int and f["duration_ticks"] > 0 for f in frames)
                  and all(b["source_pts_ticks"] - a["source_pts_ticks"] == a["duration_ticks"]
                          for a, b in zip(frames, frames[1:])), "Native PTS/display-interval joins differ")
            bounds = type("Bounds", (), {k: block["source_video"][k] for k in ("width_px", "height_px")})()
            self.labels[block_id] = {f["source_frame_index"]: FrameAnnotation.from_mapping(f["annotation"], i, bounds)
                                     for i, f in enumerate(frames)}
            folder = self.folder / hashlib.sha256(block_id.encode()).hexdigest()[:24]
            folder.mkdir(exist_ok=True)
            receipt_path = folder / "receipt.json"
            expected = {"identity": self.identity, "block_sha256": canonical(block), "block_id": block_id}
            if receipt_path.exists():
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                check(all(receipt[k] == v for k, v in expected.items()), "Cached block identity changed")
                path = bound_path(self.root, receipt["warped_frames"])
            else:
                attempt = folder / "attempts" / uuid.uuid4().hex
                attempt.mkdir(parents=True, exist_ok=False)
                path = attempt / "frames.npy"
                runtime.atomic_write_once(attempt / "started.json", expected)
                source = block["source_video"]
                forward, _ = affine_matrices(source["width_px"], source["height_px"],
                                             width=self.width, height=self.height)
                array = np.lib.format.open_memmap(path, mode="w+", dtype=np.uint8,
                    shape=(len(frames), self.height, self.width, 3))
                verified = []
                try:
                    for offset, frame in enumerate(frames):
                        raw = bound_path(self.root, frame["png"]).read_bytes()
                        with Image.open(io.BytesIO(raw)) as image:
                            check(image.mode == "RGB", "Native PNG must be RGB")
                            rgb = np.asarray(image).copy()
                        check(rgb.shape == (source["height_px"], source["width_px"], 3), "Native PNG dimensions differ")
                        check(hashlib.sha256(rgb.tobytes()).hexdigest() == frame["png"]["rgb_sha256"],
                              "Native RGB digest differs")
                        warped = cv2.warpAffine(rgb, forward, (self.width, self.height), flags=cv2.INTER_LINEAR)
                        array[offset] = warped
                        verified.append({"source_frame_index": frame["source_frame_index"], "source_png": frame["png"],
                                         "warped_rgb_sha256": hashlib.sha256(warped.tobytes()).hexdigest()})
                    array.flush()
                finally:
                    array._mmap.close()
                receipt = {**expected, "warped_frames": runtime.binding(self.root, path), "verified_frames": verified,
                           "source_video_decodes": 0, "native_png_decodes": len(verified)}
                runtime.atomic_write_once(receipt_path, receipt)
            array = np.load(path, mmap_mode="r", allow_pickle=False)
            if array.shape != (len(frames), self.height, self.width, 3) or array.dtype != np.uint8:
                array._mmap.close()
                raise ValueError("Cached frame array shape or dtype differs")
            self.arrays[block_id] = array
            self.positions[block_id] = {f["source_frame_index"]: i for i, f in enumerate(frames)}
            receipts.append(runtime.binding(self.root, receipt_path))
            print(f"Verified resolution frame cache {block_id}: {len(frames)} frames", flush=True)
        return {"blocks": receipts, "unique_block_frames": sum(len(b["frames"]) for b in self.blocks.values()),
                "disk_cache_bytes": sum(a.nbytes for a in self.arrays.values()),
                "elapsed_seconds": time.perf_counter() - began, "float_triplets_retained": 0,
                "source_video_decodes": 0, "resolution": self.resolution}

    @property
    def resolution(self):
        return {"width": self.width, "height": self.height, "target_radius": self.radius}

    def inputs(self, block_id, indices):
        indices = [i["source_frame_index"] if isinstance(i, dict) else i for i in indices]
        check(len(indices) == 3 and indices == list(range(indices[0], indices[0] + 3)), "Non-native triplet")
        return torch.cat([runtime.normalized_tensor(self.arrays[block_id][self.positions[block_id][i]]) for i in indices])

    def close(self):
        for array in self.arrays.values():
            array._mmap.close()
        self.arrays.clear()

    def example(self, triplet):
        block_id, indices = triplet["block_id"], triplet["frame_indices"]
        block = self.blocks[block_id]
        check(block["role"] == "training", "Validation block cannot enter a gradient update")
        source = block["source_video"]
        targets = [annotation_target(self.labels[block_id][i], source["width_px"], source["height_px"],
                   width=self.width, height=self.height, radius=self.radius) for i in indices]
        valid = [t[1] for t in targets]
        check(valid == triplet["valid_output_channels"] and any(valid), "Supervision mask differs from frozen triplet")
        return self.inputs(block_id, indices), torch.from_numpy(np.stack([t[0] for t in targets])), torch.tensor(valid)


def recover_uint8_pixels(inputs):
    check(isinstance(inputs, torch.Tensor) and inputs.device.type == "cpu" and inputs.dtype == torch.float32
          and inputs.ndim == 3 and inputs.shape[0] == 9 and not inputs.requires_grad,
          "Expected untouched CPU FrameStore normalized triplet")
    dimensions(inputs.shape[2], inputs.shape[1])
    check(bool(torch.isfinite(inputs).all()), "Nonfinite normalized input")
    mean, std = augmentation._statistics()
    pixels = torch.round(inputs.mul(std).add(mean).mul(255))
    check(bool(((pixels >= 0) & (pixels <= 255)).all()), "Recovered pixels outside uint8 range")
    check(torch.equal(pixels.div(255).sub(mean).div(std), inputs), "Input is not the exact frozen uint8 normalization")
    return pixels


def apply_parameters(example, *, mirror, brightness_gain):
    check(isinstance(example, (tuple, list)) and len(example) == 3, "Expected image/target/mask example")
    inputs, targets, valid = example
    check(type(mirror) is bool, "Mirror must be Boolean")
    check(type(brightness_gain) in (int, float) and math.isfinite(brightness_gain)
          and .9 <= brightness_gain <= 1.1, "Brightness gain outside frozen bounds")
    pixels = recover_uint8_pixels(inputs)
    check(isinstance(targets, torch.Tensor) and targets.device.type == "cpu" and targets.dtype == torch.float32
          and tuple(targets.shape) == (3, *inputs.shape[1:]) and not targets.requires_grad
          and bool(((targets == 0) | (targets == 1)).all()), "Expected CPU rasterized binary targets")
    check(isinstance(valid, torch.Tensor) and valid.device.type == "cpu" and valid.dtype == torch.bool
          and tuple(valid.shape) == (3,), "Expected CPU channel mask")
    check(not bool(targets[~valid].any()), "Masked target must retain the frozen zero map")
    if brightness_gain == 1:
        augmented = inputs.flip(-1) if mirror else inputs.clone()
    else:
        if mirror:
            pixels = pixels.flip(-1)
        mean, std = augmentation._statistics()
        augmented = pixels.mul(float(brightness_gain)).clamp(0, 255).div(255).sub(mean).div(std)
    return augmented, targets.flip(-1) if mirror else targets.clone(), valid.clone()


def augment_example(example, *, seed=1234, epoch, batch_index, sample_index, triplet_id=None):
    check(triplet_id is None or isinstance(triplet_id, str) and bool(triplet_id), "Invalid triplet provenance")
    audit = augmentation.parameters(seed=seed, epoch=epoch, batch_index=batch_index, sample_index=sample_index)
    result = apply_parameters(example, mirror=audit["mirror"], brightness_gain=audit["brightness_gain"])
    audit.update(triplet_id=triplet_id, shared_frame_count=3, input_shape=list(example[0].shape),
                 targets_mirrored_with_images=True, channel_masks_unchanged=True,
                 source_uint8_recovery_verified=True, original_inputs_mutated=False)
    return result, audit


def stream_means(frames, triplet_provider, *, width=WIDTH, height=HEIGHT):
    dimensions(width, height)
    sums, counts = {}, {}
    if len(frames) < 3:
        for frame in frames:
            yield frame, None, 0
        return
    for offset in range(len(frames) - 2):
        values = triplet_provider(frames[offset:offset + 3])
        check(isinstance(values, np.ndarray) and values.dtype == np.float32 and values.shape == (3, height, width)
              and np.isfinite(values).all() and (values >= 0).all() and (values <= 1).all(),
              "Invalid completed triplet heatmaps")
        for channel, frame in enumerate(frames[offset:offset + 3]):
            index = frame["source_frame_index"]
            if index not in sums:
                sums[index], counts[index] = np.zeros((height, width), np.float32), 0
            sums[index] += values[channel]
            counts[index] += 1
        frame = frames[offset]
        count = counts.pop(frame["source_frame_index"])
        yield frame, sums.pop(frame["source_frame_index"]) / np.float32(count), count
    for frame in frames[-2:]:
        count = counts.pop(frame["source_frame_index"])
        yield frame, sums.pop(frame["source_frame_index"]) / np.float32(count), count


def components_from_heatmap(heatmap, source_width, source_height, threshold=.3, *, width=WIDTH, height=HEIGHT):
    dimensions(width, height)
    check(isinstance(heatmap, np.ndarray) and heatmap.shape == (height, width) and heatmap.dtype == np.float32
          and np.isfinite(heatmap).all() and (heatmap >= 0).all() and (heatmap <= 1).all(), "Invalid mean heatmap")
    check(np.isfinite(threshold) and 0 <= threshold <= 1, "Invalid component threshold")
    _, inverse = affine_matrices(source_width, source_height, width=width, height=height)
    if np.max(heatmap) <= threshold:
        return []
    _, binary = cv2.threshold(heatmap, float(threshold), 1, cv2.THRESH_BINARY)
    count, labels = cv2.connectedComponents(binary.astype(np.uint8), connectivity=8)
    candidates = []
    for label in range(1, count):
        ys, xs = np.where(labels == label)
        weights = heatmap[ys, xs]
        score = weights.sum()
        x, y = np.sum(np.array(xs) * weights) / score, np.sum(np.array(ys) * weights) / score
        source_xy = np.dot(inverse, np.array([x, y, 1.0], np.float32))
        candidates.append({"center_x": float(source_xy[0]), "center_y": float(source_xy[1]),
            "heatmap_x": float(x), "heatmap_y": float(y), "native_score": float(score),
            "component_pixels": int(weights.size),
            "in_source_bounds": bool(0 <= source_xy[0] < source_width and 0 <= source_xy[1] < source_height)})
    return candidates


def select_observation(frame, mean, count, manifest, segment, *, width=WIDTH, height=HEIGHT):
    candidates = [] if mean is None else components_from_heatmap(mean, manifest["source_video"]["width_px"],
        manifest["source_video"]["height_px"], threshold=.3, width=width, height=height)
    candidates = [{"candidate_index": i, **c} for i, c in enumerate(candidates)]
    chosen = min(candidates, key=lambda c: (-c["native_score"], c["candidate_index"])) if candidates else None
    return {"source_frame_index": frame["source_frame_index"], "source_pts_ticks": frame["source_pts_ticks"],
        "time_base": manifest["time_base"], "source_png": frame["png"],
        "inference_status": "withheld" if mean is None else "completed",
        "state": "withheld" if mean is None else "observed" if chosen else "missing",
        "withheld_reason": "segment_has_fewer_than_three_frames" if mean is None else None,
        "segment_kind": segment["kind"], "segment_source_frame_range_inclusive": segment.get("source_frame_range_inclusive"),
        "temporal_contributions": count, "mean_heatmap_sha256": None if mean is None else hashlib.sha256(mean.tobytes()).hexdigest(),
        "candidates": candidates, "selected_candidate_index": None if chosen is None else chosen["candidate_index"],
        "center_xy_px": None if chosen is None else [chosen["center_x"], chosen["center_y"]],
        "native_score": None if chosen is None else chosen["native_score"]}


def _model_values(model, device, inputs, width, height):
    with torch.inference_mode():
        logits = model(inputs.unsqueeze(0).to(device))[0]
        check(logits.shape == (1, 3, height, width) and bool(torch.isfinite(logits).all()), "Invalid inference logits")
        return logits.sigmoid()[0].cpu().numpy().astype(np.float32, copy=False)


def infer(block, model, device, cache, path, model_name, *, width=WIDTH, height=HEIGHT):
    from .nba_first_evaluation import validate_records
    dimensions(width, height)
    calls = 0
    def provide(frames):
        nonlocal calls
        values = _model_values(model, device, cache.inputs(block["block_id"], [f["source_frame_index"] for f in frames]), width, height)
        calls += 1
        if calls % 250 == 0:
            print(json.dumps({"event": "inference_progress", "model": model_name, "block": block["block_id"], "calls": calls}), flush=True)
        return values
    check(len(block["frames"]) >= 3, "Inference requires a complete native triplet")
    path = Path(path)
    check(not path.exists(), "Mean heatmap destination already exists")
    means = np.lib.format.open_memmap(path, mode="w+", dtype=np.float32, shape=(len(block["frames"]), height, width))
    records = []
    segment = {"kind": "nba_resolution_comparison", "source_frame_range_inclusive": block["range_inclusive"]}
    try:
        for offset, (frame, mean, count) in enumerate(stream_means(block["frames"], provide, width=width, height=height)):
            check(mean is not None, "Missing mean is not a model miss")
            means[offset] = mean
            records.append(select_observation(frame, mean, count, block, segment, width=width, height=height))
        means.flush()
    finally:
        means._mmap.close()
    validate_records(block, records)
    check(calls == len(block["frames"]) - 2, "Inference call census differs")
    return records, calls


def validate_epoch(model, device, store, package, epoch, checkpoint_binding):
    began = time.perf_counter()
    model.eval()
    block_results = []
    cohorts = {key: {"matched": 0, "wrong": 0, "certain_hidden_emissions": 0, "worst_missing_seconds": 0.0}
               for key in ("possession_001", "possession_002", "possession_003", "nba_validation")}
    for block in package["validation_blocks"]:
        check(block["role"] == "checkpoint_validation", "Nonselection block in validation")
        frames = [{"source_frame_index": f["source_frame_index"], "source_pts_ticks": f["source_pts_ticks"], "png": f["png"]}
                  for f in block["frames"]]
        manifest = {"source_video": block["source_video"], "time_base": block["time_base"]}
        segment = {"kind": "fixed_checkpoint_validation", "source_frame_range_inclusive":
                   [frames[0]["source_frame_index"], frames[-1]["source_frame_index"]]}
        def provide(selected):
            return _model_values(model, device, store.inputs(block["block_id"],
                [f["source_frame_index"] for f in selected]), store.width, store.height)
        observations = [select_observation(f, mean, count, manifest, segment, width=store.width, height=store.height)
                        for f, mean, count in stream_means(frames, provide, width=store.width, height=store.height)]
        scored = runtime.scored_block(block, observations)
        cohort = cohorts[block["game_id"] if block["domain"] == "nfhs" else "nba_validation"]
        for key in ("matched", "wrong", "certain_hidden_emissions"):
            cohort[key] += scored[key]
        cohort["worst_missing_seconds"] = max(cohort["worst_missing_seconds"], scored["worst_missing_seconds"])
        block_results.append({**scored, "observations": observations})
    return {"epoch": epoch, "checkpoint": checkpoint_binding, "cohorts": cohorts,
        "blocks": block_results, "elapsed_seconds": time.perf_counter() - began,
        "threshold": .3, "strict_threshold": True, "selection": "largest_component_mass_then_stable_index",
        "aggregation": "ascending_float32_aligned_contributor_mean", "protected_frames": 0,
        "post_selection_curated_labels_used": False, "det_or_tor_used": False, "resolution": store.resolution}
