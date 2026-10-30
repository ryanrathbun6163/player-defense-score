"""Bounded candidate-point image model; importing this module never imports Torch.

Metadata and preprocessing are CPU-only. ``build_model`` is an execution entry
point, guarded before ML imports; its caller owns the frozen approval, resource
supervision and data-role checks. This module neither selects candidates nor
changes the original DINO/WASB producers.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import struct

import numpy as np
from PIL import Image


TOKEN_INDICES = (120, 121, 136, 137)
EXPECTED_BACKBONE_PARAMETERS = 22_056_576
EXPECTED_TRAINABLE_PARAMETERS = 3_600_641
SEED = 20261028
WEIGHTS = "data/outputs/ball_tracking/nba/appearance_feature_screen_v0_1/model/model.safetensors"
CONFIG = "data/outputs/ball_tracking/nba/appearance_reference_v0_1/design_sources/config.json"
LIBRARY = ".venv/Lib/site-packages/transformers/models/dinov2/modeling_dinov2.py"
PINS = {
    WEIGHTS: "ae1e99fcefd534ed978cdeb8326f08030c96e28b7a81ffcbc98a857c84d14be1",
    CONFIG: "1809f83e3bdb1609a501a610ad4a742f4fd8ae44d72ca4aa0df52d1f2ac8628d",
    LIBRARY: "9c7e028bdadef16e4fe6c59833ac916fe0a7987d1ac968a6f19aca40359ea9f8",
}
HEAD_SHAPES = {"head.0.weight": (128, 384), "head.0.bias": (128,),
               "head.2.weight": (1, 128), "head.2.bias": (1,)}


def check(value, message):
    if not value:
        raise ValueError(message)


def point_geometry(center_xy, width, height):
    """Exact earlier crop/token mapping, with explicit source/padding bounds."""
    check(type(width) is int and type(height) is int and width > 0 and height > 0,
          "Invalid source dimensions")
    center = np.asarray(center_xy, dtype=np.float64)
    check(center.shape == (2,) and np.isfinite(center).all(), "Invalid candidate center")
    x, y = (float(v) for v in center)
    check(0 <= x < width and 0 <= y < height, "Candidate center outside source")
    left, top = math.floor(x) - 32, math.floor(y) - 32
    u, v = 4 * (x - left + .5) - .5 - 16, 4 * (y - top + .5) - .5 - 16
    gx, gy = (u - 6.5) / 14, (v - 6.5) / 14
    col, row = math.floor(gx), math.floor(gy)
    check(0 <= col < 15 and 0 <= row < 15, "Point interpolation outside patch grid")
    indices = (1 + row * 16 + col, 2 + row * 16 + col,
               17 + row * 16 + col, 18 + row * 16 + col)
    check(indices == TOKEN_INDICES, "Candidate token identities differ")
    dx, dy = gx - col, gy - row
    weights = ((1-dx)*(1-dy), dx*(1-dy), (1-dx)*dy, dx*dy)
    check(all(math.isfinite(w) and 0 <= w <= 1 for w in weights)
          and abs(sum(weights)-1) < 1e-12, "Invalid interpolation weights")
    return {"crop_box": [left, top, left+64, top+64], "point_input_xy": [u, v],
            "token_indices": list(indices), "weights": list(weights),
            "complete_source_crop": left >= 0 and top >= 0
            and left+64 <= width and top+64 <= height}


def preprocess(image, center_xy):
    """Reuse original producer pixels; return CHW224 and four point weights."""
    check(isinstance(image, Image.Image), "Expected a PIL source image")
    geometry = point_geometry(center_xy, *image.size)
    from .nba_appearance_feature_screen import crop_and_preprocess
    _, _, chw = crop_and_preprocess(image, center_xy)
    check(chw.shape == (3, 224, 224) and chw.dtype == np.float32
          and np.isfinite(chw).all(), "Preprocessed input contract differs")
    return chw, np.asarray(geometry["weights"], dtype=np.float64)


def is_trainable_name(name):
    return (name.startswith(("backbone.encoder.layer.10.", "backbone.encoder.layer.11.",
                             "backbone.layernorm.")) or name in HEAD_SHAPES)


def read_weight_shapes(path):
    """Read safetensors metadata only; never deserialize through Torch."""
    with Path(path).open("rb") as handle:
        length_bytes = handle.read(8)
        check(len(length_bytes) == 8, "Missing safetensors header")
        length = struct.unpack("<Q", length_bytes)[0]
        check(0 < length < 1_000_000, "Unexpected safetensors header length")
        header = json.loads(handle.read(length))
    shapes = {}
    for name, value in header.items():
        if name == "__metadata__":
            continue
        check(value["dtype"] == "F32" and isinstance(value["shape"], list)
              and all(type(n) is int and n > 0 for n in value["shape"]),
              "Unexpected weight metadata")
        shapes[name] = tuple(value["shape"])
    return shapes


def parameter_contract(backbone_shapes):
    all_shapes = {"backbone."+name: tuple(shape) for name, shape in backbone_shapes.items()}
    check(sum(math.prod(s) for s in all_shapes.values()) == EXPECTED_BACKBONE_PARAMETERS,
          "Backbone parameter count differs")
    all_shapes.update(HEAD_SHAPES)
    trainable = {k: v for k, v in all_shapes.items() if is_trainable_name(k)}
    check(sum(math.prod(s) for s in trainable.values()) == EXPECTED_TRAINABLE_PARAMETERS,
          "Trainable parameter count differs")
    return {"all_shapes": all_shapes, "trainable_shapes": trainable,
            "trainable_parameters": EXPECTED_TRAINABLE_PARAMETERS}


def local_contract(root):
    """Validate local bindings without ML imports or model execution."""
    root = Path(root).resolve()
    for relative, expected in PINS.items():
        with (root / relative).open("rb") as handle:
            actual = hashlib.file_digest(handle, "sha256").hexdigest()
        check(actual == expected, "Pinned file differs: "+relative)
    config = json.loads((root / CONFIG).read_text(encoding="utf-8"))
    expected = {"num_hidden_layers": 12, "hidden_size": 384, "num_attention_heads": 6,
                "patch_size": 14, "num_channels": 3, "mlp_ratio": 4,
                "hidden_dropout_prob": 0.0, "attention_probs_dropout_prob": 0.0,
                "drop_path_rate": 0.0, "use_swiglu_ffn": False}
    check(all(config.get(k) == v for k, v in expected.items()), "DINO config differs")
    return parameter_contract(read_weight_shapes(root / WEIGHTS))


def trainable_manifest(model):
    rows = []
    for name, parameter in model.named_parameters():
        check(parameter.requires_grad == is_trainable_name(name), "Trainable predicate differs: "+name)
        if parameter.requires_grad:
            rows.append({"name": name, "shape": list(parameter.shape), "parameters": parameter.numel()})
    check(sum(row["parameters"] for row in rows) == EXPECTED_TRAINABLE_PARAMETERS,
          "Runtime trainable count differs")
    return rows


def frozen_fingerprint(model):
    """Hash exact names/shapes/dtypes/bytes of all frozen parameters."""
    trainable_manifest(model)
    digest = hashlib.sha256()
    for name, parameter in sorted(model.named_parameters()):
        if parameter.requires_grad:
            continue
        header = json.dumps([name, list(parameter.shape), str(parameter.dtype)],
                            separators=(",", ":")).encode()
        digest.update(struct.pack("<Q", len(header)))
        digest.update(header)
        digest.update(parameter.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def optimizer_parameter_groups(model, backbone_lr=1e-5, head_lr=1e-3, weight_decay=.01):
    check((backbone_lr, head_lr, weight_decay) == (1e-5, 1e-3, .01), "Frozen optimizer recipe differs")
    trainable_manifest(model)
    named = list(model.named_parameters())
    return [{"params": [p for n, p in named if p.requires_grad and n.startswith(prefix)],
             "lr": lr, "weight_decay": weight_decay}
            for prefix, lr in (("backbone.", backbone_lr), ("head.", head_lr))]


def build_model(root, device="cuda", *, execution_authorized=False, seed=SEED):
    """Construct only inside an approved supervised worker; no implicit download."""
    check(execution_authorized is True, "Model execution requires the worker's verified approval")
    check(seed == SEED, "Frozen initialization seed differs")
    check(str(device) in ("cpu", "cuda", "cuda:0"), "Unsupported model device")
    root = Path(root).resolve()
    expected = local_contract(root)
    import torch
    from transformers.models.dinov2 import modeling_dinov2
    from .nba_appearance_feature_screen import load_model
    check(Path(modeling_dinov2.__file__).resolve() == (root / LIBRARY).resolve(),
          "Loaded DINO library is not the pinned local library")
    torch.manual_seed(seed)
    backbone = load_model(root / CONFIG, root / WEIGHTS)

    class CandidateQualityModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.backbone = backbone
            self.head = torch.nn.Sequential(torch.nn.Linear(384, 128), torch.nn.GELU(), torch.nn.Linear(128, 1))
            for name, parameter in self.named_parameters():
                parameter.requires_grad_(is_trainable_name(name))
            actual = {name: tuple(p.shape) for name, p in self.named_parameters()}
            check(actual == expected["all_shapes"], "Runtime parameter names/shapes differ")
            trainable_manifest(self)
            self.train(False)

        def train(self, mode=True):
            super().train(mode)
            self.backbone.eval()
            for layer in self.backbone.encoder.layer[10:]:
                layer.train(mode)
            self.backbone.layernorm.train(mode)
            self.head.train(mode)
            return self

        def point_features(self, pixels, point_weights):
            check(pixels.ndim == 4 and tuple(pixels.shape[1:]) == (3, 224, 224)
                  and pixels.shape[0] > 0 and pixels.dtype == torch.float32,
                  "Expected nonempty float32 BCHW224 pixels")
            check(tuple(point_weights.shape) == (pixels.shape[0], 4)
                  and point_weights.dtype == torch.float64, "Expected float64 Bx4 weights")
            check(pixels.device == point_weights.device == next(self.parameters()).device,
                  "Input/model devices differ")
            check(bool(torch.isfinite(pixels).all()) and bool(torch.isfinite(point_weights).all())
                  and bool((point_weights >= 0).all())
                  and bool(((point_weights.sum(dim=1)-1).abs() < 1e-12).all()),
                  "Nonfinite input or invalid point weights")
            check(not self.backbone.embeddings.training
                  and all(not layer.training for layer in self.backbone.encoder.layer[:10]),
                  "Frozen prefix must stay in evaluation mode")
            with torch.no_grad():
                sequence = self.backbone.embeddings(pixels)
                for layer in self.backbone.encoder.layer[:10]:
                    sequence = layer(sequence)
            for layer in self.backbone.encoder.layer[10:]:
                sequence = layer(sequence)
            sequence = self.backbone.layernorm(sequence)
            check(tuple(sequence.shape) == (pixels.shape[0], 257, 384)
                  and sequence.dtype == torch.float32, "DINO sequence contract differs")
            raw = (sequence[:, list(TOKEN_INDICES), :].to(dtype=torch.float64)
                   * point_weights[:, :, None]).sum(dim=1)
            norms = torch.linalg.vector_norm(raw, dim=1, keepdim=True)
            check(bool(torch.isfinite(raw).all()) and bool(torch.isfinite(norms).all())
                  and bool((norms > 0).all()), "Invalid candidate-point feature")
            return raw / norms

        def forward_with_features(self, pixels, point_weights):
            features = self.point_features(pixels, point_weights)
            logits = self.head(features.to(dtype=torch.float32)).squeeze(-1)
            check(logits.dtype == torch.float32 and bool(torch.isfinite(logits).all()),
                  "Nonfinite or non-float32 quality logits")
            return logits, features

        def forward(self, pixels, point_weights):
            return self.forward_with_features(pixels, point_weights)[0]

    return CandidateQualityModel().to(device=device, dtype=torch.float32)
