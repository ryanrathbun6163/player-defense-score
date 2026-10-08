"""Pinned WASB basketball image evidence, without its native tracker.

Input is three chronological RGB uint8 images of identical dimensions. Output
is three sigmoid heatmaps and all thresholded components, in input order.
``native_score`` is component heatmap mass, NOT a probability or box confidence.
The caller owns temporal overlap aggregation, candidate selection and missingness.

Affine/component arithmetic is adapted from NTT Communications' WASB-SBDT,
revision 923462cacdeb3353b84ddebdedb3f4b7a8553b0f (src/utils/image.py,
src/dataloaders/dataset_loader.py and src/detectors/postprocessor.py).
The affine implementation also carries Copyright (c) Microsoft; written by
Bin Xiao and modified by Xingyi Zhou. The unchanged external HRNet file retains
its own Microsoft notice. WASB's repository license follows:

MIT License
Copyright (c) 2023 NTT Communications Corporation

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np

SOURCE_REVISION = "923462cacdeb3353b84ddebdedb3f4b7a8553b0f"
CHECKPOINT_SHA256 = "8d1ba9870d0a6ab37b06ab82bed593c6c09133e713810bac475d0c000bb7e948"
SOURCE_SHA256 = {
    "src/models/hrnet.py": "862ce90279a44ad19dd0590e073a8089c1cf4bd79eca0930189dda9106fa83f5",
    "src/configs/model/wasb.yaml": "cab434199852e2c6b50aeb9881c0032931d3d2b16492afade6eb8b8866ab07f0",
}
INPUT_WIDTH, INPUT_HEIGHT = 512, 288
DEFAULT_THRESHOLD = 0.5


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _dimension(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def affine_matrices(source_width: int, source_height: int) -> tuple[np.ndarray, np.ndarray]:
    """Official zero-rotation center/max-side affine, including its float32 points."""
    width = _dimension(source_width, "source_width")
    height = _dimension(source_height, "source_height")
    center = np.array([width / 2.0, height / 2.0], dtype=np.float32)
    scale = np.float32(max(width, height))
    src = np.zeros((3, 2), dtype=np.float32)
    dst = np.zeros((3, 2), dtype=np.float32)
    src[0] = center
    src[1] = center + np.array([0, scale * -0.5])
    dst[0] = [INPUT_WIDTH * 0.5, INPUT_HEIGHT * 0.5]
    dst[1] = dst[0] + np.array([0, INPUT_WIDTH * -0.5], dtype=np.float32)
    for points in (src, dst):
        direct = points[0] - points[1]
        points[2] = points[1] + np.array([-direct[1], direct[0]], dtype=np.float32)
    return cv2.getAffineTransform(src, dst), cv2.getAffineTransform(dst, src)


def transform_metadata(source_width: int, source_height: int) -> dict:
    forward, inverse = affine_matrices(source_width, source_height)
    return {
        "source_width": int(source_width), "source_height": int(source_height),
        "heatmap_width": INPUT_WIDTH, "heatmap_height": INPUT_HEIGHT,
        "source_to_heatmap": forward.tolist(), "heatmap_to_source": inverse.tolist(),
        "interpolation": "cv2.INTER_LINEAR", "border": "constant_zero",
        "color_order": "RGB",
    }


def preprocess_triplet(rgb_frames: Sequence[np.ndarray]):
    """Produce the official normalized tensor [1,9,288,512] and affine metadata."""
    import torch

    if len(rgb_frames) != 3:
        raise ValueError("WASB requires exactly three chronological RGB frames")
    for frame in rgb_frames:
        if (not isinstance(frame, np.ndarray) or frame.dtype != np.uint8
                or frame.ndim != 3 or frame.shape[2] != 3
                or min(frame.shape[:2]) <= 0):
            raise ValueError("Each RGB frame must be a nonempty uint8 HWC array with three channels")
    if any(frame.shape != rgb_frames[0].shape for frame in rgb_frames[1:]):
        raise ValueError("All three frames must have identical dimensions")
    height, width = rgb_frames[0].shape[:2]
    forward, _ = affine_matrices(width, height)
    mean = torch.tensor([0.485, 0.456, 0.406], dtype=torch.float32)[:, None, None]
    std = torch.tensor([0.229, 0.224, 0.225], dtype=torch.float32)[:, None, None]
    tensors = []
    for frame in rgb_frames:
        warped = cv2.warpAffine(frame, forward, (INPUT_WIDTH, INPUT_HEIGHT), flags=cv2.INTER_LINEAR)
        tensor = torch.from_numpy(warped.transpose(2, 0, 1).copy()).to(torch.float32).div(255)
        tensors.append(tensor.sub(mean).div(std))
    return torch.cat(tensors, dim=0).unsqueeze(0), transform_metadata(width, height)


def components_from_heatmap(
    heatmap: np.ndarray, source_width: int, source_height: int,
    threshold: float = DEFAULT_THRESHOLD,
) -> list[dict]:
    """Official weighted 8-connected components, retaining even out-of-image centers.

    No sorting, top-one selection, radius filtering or temporal association occurs.
    Source coordinates follow upstream's float32-point/float64-matrix conversion.
    """
    if (not isinstance(heatmap, np.ndarray) or heatmap.shape != (INPUT_HEIGHT, INPUT_WIDTH)
            or heatmap.dtype != np.float32 or not np.isfinite(heatmap).all()
            or np.any(heatmap < 0) or np.any(heatmap > 1)):
        raise ValueError("heatmap must be finite float32 sigmoid values shaped (288,512)")
    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("threshold must be finite and between zero and one")
    _, inverse = affine_matrices(source_width, source_height)
    if np.max(heatmap) <= threshold:
        return []
    _, binary = cv2.threshold(heatmap, float(threshold), 1, cv2.THRESH_BINARY)
    count, labels = cv2.connectedComponents(binary.astype(np.uint8), connectivity=8)
    candidates = []
    for label in range(1, count):
        ys, xs = np.where(labels == label)
        weights = heatmap[ys, xs]
        score = weights.sum()
        x = np.sum(np.array(xs) * weights) / np.sum(weights)
        y = np.sum(np.array(ys) * weights) / np.sum(weights)
        source_xy = np.dot(inverse, np.array([x, y, 1.0], dtype=np.float32))
        candidates.append({
            "center_x": float(source_xy[0]), "center_y": float(source_xy[1]),
            "heatmap_x": float(x), "heatmap_y": float(y), "native_score": float(score),
            "component_pixels": int(weights.size),
            "in_source_bounds": bool(0 <= source_xy[0] < source_width and 0 <= source_xy[1] < source_height),
        })
    return candidates


class _Config(dict):
    """The HRNet constructor uses both dict and attribute access; no Hydra needed."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as error:
            raise AttributeError(name) from error


def _config(value):
    if isinstance(value, dict):
        return _Config({key: _config(item) for key, item in value.items()})
    if isinstance(value, list):
        return [_config(item) for item in value]
    return value


class WasbAdapter:
    """Load only the pinned HRNet module and strict official basketball state.

    No packages are installed and no upstream ``src``/``utils`` namespace is
    imported. Loading remains weights-only; a failure is never retried with pickle.
    """

    def __init__(self, source_root: str | Path, checkpoint_path: str | Path, device: str = "cuda"):
        import torch
        import yaml

        self.source_root = Path(source_root).resolve()
        self.checkpoint_path = Path(checkpoint_path).resolve()
        for relative, expected in SOURCE_SHA256.items():
            if _sha256(self.source_root / relative) != expected:
                raise ValueError(f"Pinned WASB source digest mismatch: {relative}")
        if _sha256(self.checkpoint_path) != CHECKPOINT_SHA256:
            raise ValueError("Pinned WASB basketball checkpoint digest mismatch")
        module_path = self.source_root / "src/models/hrnet.py"
        spec = importlib.util.spec_from_file_location(f"_pds_wasb_hrnet_{SOURCE_REVISION}", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cfg = yaml.safe_load((self.source_root / "src/configs/model/wasb.yaml").read_text(encoding="utf-8"))
        model = module.HRNet(_config(cfg))
        checkpoint = torch.load(self.checkpoint_path, map_location="cpu", weights_only=True)
        if not isinstance(checkpoint, dict) or set(checkpoint) != {"model_state_dict"}:
            raise ValueError("Unexpected WASB basketball checkpoint structure")
        state = checkpoint["model_state_dict"]
        if not isinstance(state, dict) or not all(isinstance(key, str) and isinstance(value, torch.Tensor) for key, value in state.items()):
            raise ValueError("WASB state must contain named tensors only")
        model.load_state_dict(state, strict=True)
        self.device = torch.device(device)
        self.model = model.to(self.device).eval()
        self.provenance = {
            "source_repository": "https://github.com/nttcom/WASB-SBDT",
            "source_revision": SOURCE_REVISION,
            "source_root": str(self.source_root), "source_sha256": dict(SOURCE_SHA256),
            "checkpoint_path": str(self.checkpoint_path), "checkpoint_sha256": CHECKPOINT_SHA256,
            "checkpoint_size_bytes": self.checkpoint_path.stat().st_size,
            "checkpoint_load": "torch.load(weights_only=True); load_state_dict(strict=True)",
            "torch_version": torch.__version__, "device": str(self.device),
            "native_score_semantics": "sum of sigmoid heatmap values within strict >0.5 component; not probability",
            "native_tracker_used": False,
        }

    def predict_triplet(self, rgb_frames: Sequence[np.ndarray]) -> dict:
        import torch

        inputs, metadata = preprocess_triplet(rgb_frames)
        with torch.inference_mode():
            output = self.model(inputs.to(self.device))
            if not isinstance(output, dict) or set(output) != {0} or tuple(output[0].shape) != (1, 3, INPUT_HEIGHT, INPUT_WIDTH):
                raise ValueError("Unexpected WASB output; expected scale 0 logits [1,3,288,512]")
            heatmaps = output[0].sigmoid().to(device="cpu", dtype=torch.float32).numpy()[0]
        frames = [{
            "candidates": components_from_heatmap(heatmap, metadata["source_width"], metadata["source_height"]),
            "transform": dict(metadata),
        } for heatmap in heatmaps]
        return {"heatmaps": heatmaps, "frames": frames}
