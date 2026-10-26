"""Disposable synthetic readiness check for the approved 768x432 experiment.

No source pixels or labels enter a forward pass; no model weights are saved.
The real fit initializes a separate fresh model and optimizer afterward.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import time
import traceback

import torch

from . import completion_training as frozen
from .completion_training_runtime import atomic_write_once, binding
from .wasb_experiment import read_json


def execute(root, parent_recipe, output):
    root = Path(root).resolve()
    folder = frozen.output_path(root, output)
    frozen.check(not folder.exists(), "Readiness must use a fresh attempt directory")
    parent, _, _, nfhs, parent_identity = frozen.preflight(root, parent_recipe)
    folder.mkdir(parents=True)
    identity = {"parent_identity": parent_identity,
        "code": binding(root, Path(__file__)), "shape": [2, 9, 432, 768],
        "user_authority": "ok move forward with the experiment chat",
        "synthetic_only": True, "source_pixels_read": 0, "protected_reads": 0}
    atomic_write_once(folder / "started.json", {"identity": identity,
        "at_utc": datetime.now(timezone.utc).isoformat()})
    start, steps = time.perf_counter(), []
    try:
        model, device, optimizer, bn = frozen.adaptation.initialize(root, parent, nfhs)
        checkpoint_before = binding(root, root / parent["initialization"]["checkpoint"]["path"])
        frozen.check(not optimizer.state, "Readiness optimizer must be fresh")
        mean = torch.tensor([.485, .456, .406] * 3, device=device).view(1, 9, 1, 1)
        std = torch.tensor([.229, .224, .225] * 3, device=device).view(1, 9, 1, 1)
        inputs = (torch.rand((2, 9, 432, 768), device=device) - mean) / std
        targets = torch.zeros((2, 3, 432, 768), device=device)
        yy, xx = torch.meshgrid(torch.arange(432, device=device), torch.arange(768, device=device), indexing="ij")
        targets[:, 0] = ((xx - 384).square() + (yy - 216).square() <= 3.75 ** 2).float()
        targets[1, 2] = ((xx - 390).square() + (yy - 216).square() <= 3.75 ** 2).float()
        masks = torch.tensor([[True, True, False], [True, True, True]], device=device)
        torch.cuda.reset_peak_memory_stats(device)
        for number in range(1, 4):
            torch.cuda.synchronize(device)
            began = time.perf_counter()
            loss, gradients = frozen.training.training_step(model, optimizer, inputs, targets, masks)
            torch.cuda.synchronize(device)
            frozen.training.assert_batch_norm_unchanged(model, bn)
            steps.append({"step": number, "loss": loss, "gradient_tensors": gradients,
                          "seconds": time.perf_counter() - began})
        free, total = torch.cuda.mem_get_info(device)
        frozen.check(checkpoint_before == binding(root, root / checkpoint_before["path"]),
                     "Original checkpoint changed during disposable check")
        result = {"schema_version": "wasb_resolution_readiness/v0.1", "status": "passed",
            "identity": identity, "steps": steps, "synthetic_optimizer_updates": 3,
            "scientific_optimizer_updates": 0, "weights_saved": False,
            "original_checkpoint_unchanged": True, "batch_norm_unchanged": True,
            "input_shape": list(inputs.shape), "target_and_output_shape": list(targets.shape),
            "peak_allocated_bytes": torch.cuda.max_memory_allocated(device),
            "peak_reserved_bytes": torch.cuda.max_memory_reserved(device),
            "free_device_bytes_after_step": free, "total_device_bytes": total,
            "elapsed_seconds": time.perf_counter() - start}
        atomic_write_once(folder / "completed.json", result)
        return result
    except BaseException as error:
        atomic_write_once(folder / "failed.json", {"identity": identity, "error": str(error),
            "traceback": traceback.format_exc(), "completed_steps": steps,
            "elapsed_seconds": time.perf_counter() - start})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-recipe", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.run:
        result = execute(root, args.parent_recipe, args.output)
        print({k: v for k, v in result.items() if k in {"status", "elapsed_seconds", "peak_allocated_bytes", "free_device_bytes_after_step"}}, flush=True)
    else:
        frozen.preflight(root, args.parent_recipe)
        print({"status": "preflight_passed", "model_loaded": False})


if __name__ == "__main__":
    main()
