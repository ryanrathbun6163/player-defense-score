"""Read-only NBA diagnostic control using the pinned original basketball weights.

Reuse the verified native NBA contexts, preprocessing, inference and scorer from
the completed comparison. No fitting, label change, threshold tuning or adoption.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
import traceback

import cv2
import torch

from . import nba_first_evaluation as nba
from .nba_first_validation import score_block, aggregate_blocks
from .completion_training_runtime import atomic_write_once as write_once, binding
from .wasb_experiment import read_json, bound_path, runtime_versions
from .wasb_adapter import CHECKPOINT_SHA256
from .wasb_training import training_lock

SCHEMA = "nba_original_weight_control/v0.1"
check = nba.check


def validate_config(config):
    check(config["schema_version"] == SCHEMA and config["status"] == "frozen_before_execution"
          and config["training_authorized"] is False and config["protected_evaluation_authorized"] is False,
          "Read-only frozen control required")
    check(config["checkpoint"]["sha256"] == CHECKPOINT_SHA256, "Original pinned basketball weight required")
    check(config["policy"] == nba.evaluation.POLICY, "Control inference policy differs")
    check(config["new_model_calls"] == 3646, "Control call census differs")


def preflight(root, config_path):
    root = Path(root).resolve()
    config = read_json(root / config_path)
    validate_config(config)
    bound_path(root, config["parent_config"])
    parent, blocks, _ = nba.preflight(root, config["parent_config"]["path"])
    for entry in config["code_bindings"] + [config["checkpoint"], config["comparison"]]:
        bound_path(root, entry)
    check(config["runtime"] == runtime_versions(), "Runtime differs")
    check(config["block_ids"] == [b["block_id"] for b in blocks]
          and sum(len(b["frames"]) - 2 for b in blocks) == config["new_model_calls"], "Fixed NBA context differs")
    return config, parent, blocks


def execute(root, config_path):
    root = Path(root).resolve()
    config, parent, blocks = preflight(root, config_path)
    folder = (root / config["output_root"]).resolve()
    check(folder.is_relative_to(root / "data/outputs") and not folder.exists(), "Use a fresh ignored control output")
    folder.mkdir(parents=True)
    identity = {"config": binding(root, root / config_path), "original_comparison": config["comparison"]}
    began = time.perf_counter()
    write_once(folder / "started.json", {"identity": identity, "started_at_utc": nba.stamp()})
    cache = nba.InputCache(root, blocks, root / parent["output_root"] / "input_cache")
    calls = 0
    try:
        with training_lock(folder / "control.lock"):
            torch.set_num_threads(2)
            torch.backends.cudnn.benchmark = False
            torch.backends.cudnn.deterministic = True
            cv2.setNumThreads(1)
            write_once(folder / "cache_verification.json", cache.prepare())
            adapter = nba.evaluation.make_adapter(root, {"selected_method": {
                "checkpoint": config["checkpoint"], "provenance": "Pinned original basketball weights; no local adaptation"}})
            reports, records = [], []
            for block in blocks:
                output = folder / nba.key(block)
                output.mkdir()
                observations, count = nba.infer(block, adapter.model, adapter.device, cache,
                    output / "mean_heatmaps.npy", "original_basketball")
                calls += count
                report = score_block(block, observations)
                write_once(output / "records.json", {"block_id": block["block_id"], "checkpoint": config["checkpoint"],
                    "observations": observations, "score": report})
                reports.append(report)
                records.append({"block_id": block["block_id"], "records": binding(root, output / "records.json"),
                    "mean_heatmaps": binding(root, output / "mean_heatmaps.npy"), "new_model_calls": count})
                s = report["summary"]
                print(json.dumps({"event": "block_complete", "block": block["block_id"], "correct": s["matched"],
                    "wrong": s["wrong"], "missing": s["missing"], "hidden": s["certain_hidden_emitted_points"]}), flush=True)
            check(calls == config["new_model_calls"], "Actual call census differs")
            result = {"schema_version": SCHEMA, "status": "completed", "identity": identity,
                "checkpoint": config["checkpoint"], "records": records,
                "validation_summary": aggregate_blocks(reports[:6]),
                "episodes": [{"block_id": r["block_id"], "summary": r["summary"]} for r in reports],
                "new_model_calls": calls, "optimizer_updates": 0, "new_labels": 0, "protected_reads": 0,
                "model_adopted": False, "human_review": None, "elapsed_seconds": time.perf_counter() - began}
            write_once(folder / "completed.json", result)
            return result
    except BaseException as error:
        write_once(folder / "failed.json", {"identity": identity, "error": str(error), "traceback": traceback.format_exc(),
            "completed_model_calls": calls, "elapsed_seconds": time.perf_counter() - began})
        raise
    finally:
        cache.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--config", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    result = execute(args.root, args.config) if args.run else {
        "status": "preflight_passed", "new_model_calls": preflight(args.root, args.config)[0]["new_model_calls"]}
    print(json.dumps({k: v for k, v in result.items() if k in {"status", "new_model_calls", "elapsed_seconds"}}, indent=2))


if __name__ == "__main__":
    main()
