"""Frozen-local / trainable-auxiliary fusion model; importing never loads Torch.

The only pretrained model construction entry point is guarded by its worker.
Readout helpers also support small synthetic CPU tests without loading weights.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np
from PIL import Image

from . import candidate_quality_model as original

check = original.check
SEED = 20261030
TOKEN_INDICES = original.TOKEN_INDICES
EXPECTED_AUXILIARY_PARAMETERS = 3_551_232
EXPECTED_HEAD_PARAMETERS = 147_713
EXPECTED_TRAINABLE_PARAMETERS = 3_698_945
HEAD_SHAPES = {"head.0.weight": (128, 1152), "head.0.bias": (128,),
               "head.2.weight": (1, 128), "head.2.bias": (1,)}


def preprocess_raw(raw, arm):
    """Use original local preprocessing or direct 192-to-224 context resize."""
    check(arm in ("LL", "LC"), "Unknown auxiliary arm")
    side = 64 if arm == "LL" else 192
    check(isinstance(raw, np.ndarray) and raw.shape == (side, side, 3)
          and raw.dtype == np.uint8, "Raw crop shape/dtype differs")
    image = Image.fromarray(raw)
    if arm == "LL":
        from .nba_appearance_feature_screen import crop_and_preprocess
        result = crop_and_preprocess(image, [32., 32.])[2]
    else:
        resized = np.asarray(image.resize((224, 224), Image.Resampling.BICUBIC), dtype=np.float32)
        result = ((resized / np.float32(255.) - np.array([.485, .456, .406], dtype=np.float32))
                  / np.array([.229, .224, .225], dtype=np.float32)).transpose(2, 0, 1)
    check(result.shape == (3, 224, 224) and result.dtype == np.float32
          and np.isfinite(result).all(), "Preprocessed crop differs")
    return np.ascontiguousarray(result)


def is_trainable_name(name):
    return (name.startswith(("backbone.encoder.layer.10.", "backbone.encoder.layer.11.",
                             "backbone.layernorm.")) or name in HEAD_SHAPES)


def local_contract(root):
    contract = original.local_contract(root)
    shapes = {name: shape for name, shape in contract["all_shapes"].items()
              if name.startswith("backbone.")}
    shapes.update(HEAD_SHAPES)
    trainable = {name: shape for name, shape in shapes.items() if is_trainable_name(name)}
    check(sum(math.prod(s) for n, s in trainable.items() if n.startswith("backbone."))
          == EXPECTED_AUXILIARY_PARAMETERS, "Auxiliary parameter count differs")
    check(sum(math.prod(s) for s in HEAD_SHAPES.values()) == EXPECTED_HEAD_PARAMETERS,
          "Fusion head parameter count differs")
    check(sum(math.prod(s) for s in trainable.values()) == EXPECTED_TRAINABLE_PARAMETERS,
          "Total trainable parameter count differs")
    return {"all_shapes": shapes, "trainable_shapes": trainable,
            "trainable_parameters": EXPECTED_TRAINABLE_PARAMETERS}


def normalized_readouts(sequence, point_weights):
    """Interpolate final-normalized patch tokens before one float64 L2 norm."""
    import torch
    check(sequence.ndim == 3 and tuple(sequence.shape[1:]) == (257, 384)
          and sequence.shape[0] > 0 and sequence.dtype == torch.float32,
          "Expected nonempty final-normalized Bx257x384 sequence")
    check(tuple(point_weights.shape) == (sequence.shape[0], 4)
          and point_weights.dtype == torch.float64 and point_weights.device == sequence.device
          and bool(torch.isfinite(point_weights).all()) and bool((point_weights >= 0).all())
          and bool(((point_weights.sum(1)-1).abs() < 1e-12).all()), "Invalid point weights")
    point = (sequence[:, list(TOKEN_INDICES), :].to(dtype=torch.float64)
             * point_weights[:, :, None]).sum(1)
    cls = sequence[:, 0, :].to(dtype=torch.float64)
    result = []
    for value in (point, cls):
        norm = torch.linalg.vector_norm(value, dim=1, keepdim=True)
        check(bool(torch.isfinite(value).all()) and bool(torch.isfinite(norm).all())
              and bool((norm > 0).all()), "Invalid auxiliary readout")
        result.append(value / norm)
    return tuple(result)


def fuse_features(local, point, cls):
    """The independent normalized vectors retain their declared order and scale."""
    import torch
    check(local.ndim == 2 and local.shape[1] == 384 and not local.requires_grad,
          "Local point features must be frozen Bx384 tensors")
    check(all(v.shape == local.shape and v.device == local.device and v.dtype == torch.float64
              and bool(torch.isfinite(v).all()) for v in (local, point, cls)),
          "Fusion readout shape/dtype/device differs")
    check(all(bool((torch.linalg.vector_norm(v, dim=1)-1).abs().lt(1e-10).all())
              for v in (local, point, cls)), "Fusion inputs must be independently unit-normalized")
    return torch.cat([v.to(dtype=torch.float32) for v in (local, point, cls)], dim=1)


def trainable_manifest(model):
    rows = []
    for name, parameter in model.named_parameters():
        check(parameter.requires_grad == is_trainable_name(name), "Trainable predicate differs: " + name)
        if parameter.requires_grad:
            rows.append({"name": name, "shape": list(parameter.shape), "parameters": parameter.numel()})
    check(sum(row["parameters"] for row in rows) == EXPECTED_TRAINABLE_PARAMETERS,
          "Runtime trainable parameter count differs")
    return rows


def frozen_fingerprint(model):
    trainable_manifest(model)
    digest = hashlib.sha256()
    for name, parameter in sorted(model.named_parameters()):
        if parameter.requires_grad:
            continue
        header = json.dumps([name, list(parameter.shape), str(parameter.dtype)], separators=(",", ":")).encode()
        digest.update(struct.pack("<Q", len(header)))
        digest.update(header)
        digest.update(parameter.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def optimizer_parameter_groups(model):
    trainable_manifest(model)
    named = list(model.named_parameters())
    return [{"params": [p for n, p in named if p.requires_grad and n.startswith(prefix)],
             "lr": lr, "weight_decay": .01} for prefix, lr in (("backbone.", 1e-5), ("head.", 1e-3))]


def _make_model(backbone, expected_shapes):
    """Assemble an already loaded encoder; seed reset is deliberately here."""
    import torch

    class DualViewContextModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.backbone = backbone
            torch.manual_seed(SEED)
            self.head = torch.nn.Sequential(torch.nn.Linear(1152, 128), torch.nn.GELU(), torch.nn.Linear(128, 1))
            for name, parameter in self.named_parameters():
                parameter.requires_grad_(is_trainable_name(name))
            if expected_shapes is not None:
                check({n: tuple(p.shape) for n, p in self.named_parameters()} == expected_shapes,
                      "Runtime parameter names/shapes differ")
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

        def auxiliary_features(self, pixels, point_weights):
            check(pixels.ndim == 4 and tuple(pixels.shape[1:]) == (3, 224, 224)
                  and pixels.shape[0] > 0 and pixels.dtype == torch.float32
                  and pixels.device == next(self.parameters()).device
                  and bool(torch.isfinite(pixels).all()), "Invalid auxiliary pixels")
            check(not self.backbone.embeddings.training
                  and all(not layer.training for layer in self.backbone.encoder.layer[:10]),
                  "Frozen prefix must remain in eval mode")
            with torch.no_grad():
                sequence = self.backbone.embeddings(pixels)
                for layer in self.backbone.encoder.layer[:10]:
                    sequence = layer(sequence)
            for layer in self.backbone.encoder.layer[10:]:
                sequence = layer(sequence)
            return normalized_readouts(self.backbone.layernorm(sequence), point_weights)

        def forward_with_features(self, local, pixels, point_weights):
            point, cls = self.auxiliary_features(pixels, point_weights)
            logits = self.head(fuse_features(local, point, cls)).squeeze(-1)
            check(logits.dtype == torch.float32 and bool(torch.isfinite(logits).all()), "Invalid fusion logit")
            return logits, point, cls

        def forward(self, local, pixels, point_weights):
            return self.forward_with_features(local, pixels, point_weights)[0]

    return DualViewContextModel()


def build_model(root, device="cuda", *, execution_authorized=False, seed=SEED):
    check(execution_authorized is True, "Model execution requires verified worker authorization")
    check(seed == SEED and str(device) in ("cpu", "cuda", "cuda:0"), "Frozen seed/device differs")
    root = Path(root).resolve()
    expected = local_contract(root)
    import torch
    from transformers.models.dinov2 import modeling_dinov2
    from .nba_appearance_feature_screen import load_model
    check(Path(modeling_dinov2.__file__).resolve() == (root / original.LIBRARY).resolve(),
          "Loaded DINO library differs from pinned source")
    backbone = load_model(root / original.CONFIG, root / original.WEIGHTS)
    return _make_model(backbone, expected["all_shapes"]).to(device=device, dtype=torch.float32)


def first_batch_parity(model, pixels, weights, actual_point, actual_cls):
    """One extra standard encoder call; point checked by the original CPU consumer."""
    import torch
    from .point_feature_inference import point_readout
    with torch.no_grad():
        output = model.backbone(pixel_values=pixels, return_dict=True)
        sequence = output.last_hidden_state
        check(tuple(sequence.shape) == (pixels.shape[0], 257, 384)
              and sequence.dtype == torch.float32 and bool(torch.isfinite(sequence).all())
              and torch.equal(sequence[:, 0, :], output.pooler_output), "Standard producer output differs")
        tokens = sequence[:, list(TOKEN_INDICES), :].detach().cpu().numpy()
        cls = sequence[:, 0, :].detach().cpu().numpy().astype(np.float64)
    expected = []
    for sample, row_weights in zip(tokens, weights.detach().cpu().numpy(), strict=True):
        geometry = {"tokens": [{"sequence_index": index, "weight": float(weight)}
                                for index, weight in zip(TOKEN_INDICES, row_weights, strict=True)]}
        _, unit, reason = point_readout(sample, geometry)
        check(reason is None, "Original point readout rejected standard producer")
        expected.append(unit)
    expected_point = np.stack(expected)
    expected_cls = cls / np.linalg.norm(cls, axis=1, keepdims=True)
    result = {"samples": len(expected), "atol": 1e-10, "rtol": 1e-10,
              "producer": "pinned standard DINO forward; original CPU point consumer; independent CPU CLS"}
    for name, actual, reference in (("point", actual_point, expected_point), ("CLS", actual_cls, expected_cls)):
        value = actual.detach().cpu().numpy()
        check(value.dtype == np.float64 and np.allclose(value, reference, atol=1e-10, rtol=1e-10),
              "Auxiliary producer/readout parity failed: " + name)
        result[name + "_max_absolute_difference"] = float(np.max(np.abs(value-reference)))
    return result
