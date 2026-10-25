"""Bounded, exact-preprocessing inputs and streaming campaign validation.

Only already accepted, role-checked package blocks enter this module. Native PNGs
are verified once and affine-warped into an immutable uint8 disk cache. Triplets
are assembled on demand; no all-triplet float tensor or epoch heatmap cache exists.
"""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
import hashlib
import io
import json
import os
from pathlib import Path
import time
import uuid

import cv2
import numpy as np
from PIL import Image
import torch

from . import wasb_training as training
from . import wasb_adapter as adapter
from .annotations import FrameAnnotation
from .nba_action_observation import stream_means, select_observation
from .nba_wasb_diagnostic import score_reference
from .wasb_experiment import bound_path, canonical, digest_file


def binding(root, path):
    path = Path(path).resolve()
    return {"path": path.relative_to(Path(root).resolve()).as_posix(),
            "sha256": digest_file(path), "bytes": path.stat().st_size}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def atomic_write_once(path, value):
    """Publish complete immutable JSON; retain any interrupted temporary file.

    An exclusive hard link exposes the already flushed file atomically without
    replacing another writer's destination. Both names are in the same folder.
    The run's OS lock provides process ownership; the exclusive link also guards
    a mistaken second publisher. Original bytes survive equal-value resumes.
    """
    path = Path(path)
    if path.exists():
        check(json.loads(path.read_text(encoding="utf-8")) == value, "Existing JSON evidence differs")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temporary.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.link(temporary, path)
    temporary.unlink()


def normalized_tensor(warped):
    """Exactly the original adapter's float32 arithmetic, after its affine warp."""
    mean = torch.tensor([.485, .456, .406], dtype=torch.float32)[:, None, None]
    std = torch.tensor([.229, .224, .225], dtype=torch.float32)[:, None, None]
    tensor = torch.from_numpy(np.array(warped.transpose(2, 0, 1), copy=True))
    return tensor.to(torch.float32).div(255).sub(mean).div(std)


class FrameStore:
    """Memory-mapped unique warped frames, with one bounded batch in float32 RAM."""

    def __init__(self, root, package, folder):
        self.root, self.folder = Path(root).resolve(), Path(folder).resolve()
        self.blocks = {b["block_id"]: b for b in package["training_blocks"] + package["validation_blocks"]}
        check(len(self.blocks) == len(package["training_blocks"]) + len(package["validation_blocks"]),
              "Training/validation block IDs must be unique")
        self.arrays, self.positions, self.labels = {}, {}, {}
        self.identity = {"package_sha256": canonical(package),
                         "adapter_sha256": digest_file(Path(adapter.__file__)),
                         "runtime_sha256": digest_file(Path(__file__)), "representation": "affine_RGB_uint8_288x512"}
        self.folder.mkdir(parents=True, exist_ok=True)

    def prepare(self):
        began = time.perf_counter()
        receipts = []
        for block_id, block in self.blocks.items():
            frames = block["frames"]
            indices = [f["source_frame_index"] for f in frames]
            check(indices and indices == list(range(indices[0], indices[-1] + 1)), "Block native frames must be consecutive and unique")
            check(all(f["annotation"]["frame_index"] == f["source_frame_index"] for f in frames),
                  "Annotation/native-frame join differs")
            check(all(type(f["duration_ticks"]) is int and f["duration_ticks"] > 0 for f in frames)
                  and all(b["source_pts_ticks"] - a["source_pts_ticks"] == a["duration_ticks"]
                          for a, b in zip(frames, frames[1:])), "Native PTS/display-interval joins differ")
            bounds = type("Bounds", (), {k: block["source_video"][k] for k in ("width_px", "height_px")})()
            self.labels[block_id] = {f["source_frame_index"]: FrameAnnotation.from_mapping(f["annotation"], i, bounds)
                                     for i, f in enumerate(block["frames"])}
            # The ID is metadata, never an unchecked filesystem path.
            key = hashlib.sha256(block_id.encode()).hexdigest()[:24]
            folder = self.folder / key
            folder.mkdir(exist_ok=True)
            receipt_path = folder / "receipt.json"
            expected = {"identity": self.identity, "block_sha256": canonical(block), "block_id": block_id}
            if receipt_path.exists():
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                check(all(receipt[k] == v for k, v in expected.items()), "Cached block identity changed")
                path = bound_path(self.root, receipt["warped_frames"])
            else:
                # A crash leaves this attempt intact; only this unfinished block is retried.
                attempt = folder / "attempts" / uuid.uuid4().hex
                attempt.mkdir(parents=True, exist_ok=False)
                path = attempt / "frames.npy"
                atomic_write_once(attempt / "started.json", expected)
                source = block["source_video"]
                forward, _ = adapter.affine_matrices(source["width_px"], source["height_px"])
                array = np.lib.format.open_memmap(path, mode="w+", dtype=np.uint8,
                                                 shape=(len(block["frames"]), 288, 512, 3))
                verified = []
                for offset, frame in enumerate(block["frames"]):
                    raw = bound_path(self.root, frame["png"]).read_bytes()
                    with Image.open(io.BytesIO(raw)) as image:
                        check(image.mode == "RGB", "Native PNG must be RGB")
                        rgb = np.asarray(image).copy()
                    check(rgb.shape == (source["height_px"], source["width_px"], 3), "Native PNG dimensions differ")
                    check(hashlib.sha256(rgb.tobytes()).hexdigest() == frame["png"]["rgb_sha256"],
                          "Native RGB digest differs")
                    warped = cv2.warpAffine(rgb, forward, (512, 288), flags=cv2.INTER_LINEAR)
                    array[offset] = warped
                    verified.append({"source_frame_index": frame["source_frame_index"],
                                     "source_png": frame["png"], "warped_rgb_sha256": hashlib.sha256(warped.tobytes()).hexdigest()})
                array.flush()
                del array
                receipt = {**expected, "warped_frames": binding(self.root, path), "verified_frames": verified,
                           "source_video_decodes": 0, "native_png_decodes": len(verified)}
                atomic_write_once(receipt_path, receipt)
            array = np.load(path, mmap_mode="r", allow_pickle=False)
            check(array.shape == (len(block["frames"]), 288, 512, 3) and array.dtype == np.uint8,
                  "Cached frame array shape or dtype differs")
            self.arrays[block_id] = array
            self.positions[block_id] = {f["source_frame_index"]: i for i, f in enumerate(block["frames"])}
            check(len(self.positions[block_id]) == len(block["frames"]), "Duplicate block frame")
            receipts.append(binding(self.root, receipt_path))
            print(f"Verified frame cache {block_id}: {len(block['frames'])} frames", flush=True)
        return {"blocks": receipts, "unique_block_frames": sum(len(b["frames"]) for b in self.blocks.values()),
                "disk_cache_bytes": sum(a.nbytes for a in self.arrays.values()),
                "elapsed_seconds": time.perf_counter() - began,
                "float_triplets_retained": 0, "source_video_decodes": 0}

    def inputs(self, block_id, indices):
        check(len(indices) == 3 and indices == list(range(indices[0], indices[0] + 3)), "Non-native triplet")
        return torch.cat([normalized_tensor(self.arrays[block_id][self.positions[block_id][i]]) for i in indices])

    def close(self):
        for array in self.arrays.values():
            array._mmap.close()
        self.arrays.clear()

    def example(self, triplet):
        block_id, indices = triplet["block_id"], triplet["frame_indices"]
        block = self.blocks[block_id]
        check(block["role"] == "training", "Validation block cannot enter a gradient update")
        source = block["source_video"]
        targets = [training.annotation_target(self.labels[block_id][i], source["width_px"], source["height_px"])
                   for i in indices]
        valid = [t[1] for t in targets]
        check(valid == triplet["valid_output_channels"] and any(valid), "Supervision mask differs from frozen triplet")
        return self.inputs(block_id, indices), torch.from_numpy(np.stack([t[0] for t in targets])), torch.tensor(valid)


def scored_block(block, observations):
    frames = [{"source_frame_index": f["source_frame_index"], "source_pts_ticks": f["source_pts_ticks"],
               "png": f["png"]} for f in block["frames"]]
    reference = {"frames": frames, "annotations": [f["annotation"] for f in block["frames"]],
                 "source_video": block["source_video"], "candidate_id": block["block_id"],
                 "game_id": block["game_id"], "approved_role": block["role"]}
    result = score_reference(reference, {"frames": observations})
    count = Counter(r["outcome"] for r in result["frame_results"])
    worst, current = Fraction(0), Fraction(0)
    for frame, row in zip(block["frames"], result["frame_results"], strict=True):
        current = current + Fraction(frame["duration_ticks"]) * Fraction(block["time_base"]) if row["outcome"] == "missing" else Fraction(0)
        worst = max(worst, current)
    certain = sum(row["outcome"] == "hidden_alarm" and frame["annotation"]["game_ball_identity_certainty"] == "certain"
                  for frame, row in zip(block["frames"], result["frame_results"], strict=True))
    return {"block_id": block["block_id"], "domain": block["domain"], "game_id": block["game_id"],
            "matched": count["matched"], "wrong": count["wrong"], "missing": count["missing"],
            "eligible_frames": count["matched"] + count["wrong"] + count["missing"],
            "certain_hidden_emissions": certain, "all_hidden_emissions": count["hidden_alarm"],
            "worst_missing_seconds": float(worst), "worst_missing_duration_exact": str(worst),
            "frame_results": result["frame_results"]}


def validate_epoch(model, device, store, package, epoch, checkpoint_binding):
    """Same fixed native contexts at epoch zero and each trained epoch; no tuning."""
    began = time.perf_counter()
    model.eval()
    block_results = []
    cohorts = {key: {"matched": 0, "wrong": 0, "certain_hidden_emissions": 0, "worst_missing_seconds": 0.0}
               for key in ("possession_001", "possession_002", "possession_003", "nba_validation")}
    for block in package["validation_blocks"]:
        check(block["role"] == "checkpoint_validation", "Nonselection block in validation")
        frames = [{"source_frame_index": f["source_frame_index"], "source_pts_ticks": f["source_pts_ticks"],
                   "png": f["png"]} for f in block["frames"]]
        manifest = {"source_video": block["source_video"], "time_base": block["time_base"]}
        segment = {"kind": "fixed_checkpoint_validation", "source_frame_range_inclusive":
                   [frames[0]["source_frame_index"], frames[-1]["source_frame_index"]]}
        def provide(selected):
            inputs = store.inputs(block["block_id"], [f["source_frame_index"] for f in selected])
            with torch.inference_mode():
                logits = model(inputs.unsqueeze(0).to(device))[0]
                check(logits.shape == (1, 3, 288, 512) and bool(torch.isfinite(logits).all()), "Invalid validation logits")
                return logits.sigmoid()[0].cpu().numpy().astype(np.float32, copy=False)
        observations = [select_observation(f, mean, count, manifest, segment)
                        for f, mean, count in stream_means(frames, provide)]
        scored = scored_block(block, observations)
        cohort = cohorts[block["game_id"] if block["domain"] == "nfhs" else "nba_validation"]
        for key in ("matched", "wrong", "certain_hidden_emissions"):
            cohort[key] += scored[key]
        cohort["worst_missing_seconds"] = max(cohort["worst_missing_seconds"], scored["worst_missing_seconds"])
        block_results.append({**scored, "observations": observations})
    return {"epoch": epoch, "checkpoint": checkpoint_binding, "cohorts": cohorts,
            "blocks": block_results, "elapsed_seconds": time.perf_counter() - began,
            "threshold": .3, "strict_threshold": True, "selection": "largest_component_mass_then_stable_index",
            "aggregation": "ascending_float32_aligned_contributor_mean", "protected_frames": 0,
            "post_selection_curated_labels_used": False, "det_or_tor_used": False}
