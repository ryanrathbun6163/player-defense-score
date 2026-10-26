"""NBA-first comparison of existing WASB weights; no optimizer or fitting.

Reuse hash-bound observations, infer only missing model/context pairs, and apply
the unchanged completion scorer separately to each existing NBA episode/context.
All outputs are additive and resumable by immutable per-model/block receipts.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import traceback
import uuid

import cv2
import numpy as np
import torch

from . import completion_evaluation as evaluation
from . import completion_training_runtime as runtime
from .nba_action_observation import select_observation, stream_means
from .wasb_adapter import affine_matrices, preprocess_triplet
from .wasb_experiment import bound_path, canonical, read_json, runtime_versions
from .wasb_training import training_lock

SCHEMA = "nba_first_saved_models/v0.1"
write_once, binding, check = runtime.atomic_write_once, runtime.binding, runtime.check


def stamp():
    return datetime.now(timezone.utc).isoformat()


def key(block):
    return hashlib.sha256(block["block_id"].encode()).hexdigest()[:24]


def blocks_from_packages(training, comparison):
    """Only permitted NBA validation and already open historical NBA contexts."""
    check(training["protected_evaluation_authorized"] is False
          and comparison["protected_evaluation_authorized"] is False, "Protected package prohibited")
    result = []
    for original in training["validation_blocks"]:
        if original["domain"] != "nba":
            continue
        check(original["role"] == "checkpoint_validation", "Validation exposure differs")
        block = deepcopy(original)
        for frame in block["frames"]:
            frame.update(state="permitted", block_id=block["block_id"], reference_role="checkpoint_validation")
        result.append(block)
    for original in comparison["inference_blocks"]:
        if original["domain"] == "nba":
            evaluation.normalize_block(original)
            result.append(deepcopy(original))
    check(len(result) == 8 and len({b["block_id"] for b in result}) == 8,
          "Expected six validation episodes and two historical contexts")
    check(sum(len(b["frames"]) for b in result) == 3662, "NBA context census differs")
    for block in result:
        indices = [f["source_frame_index"] for f in block["frames"]]
        check(indices == list(range(indices[0], indices[-1] + 1)), "Non-native NBA context")
        check(all(f["state"] == "permitted" for f in block["frames"]), "Protected NBA row prohibited")
        check(not block.get("protected_ranges"), "Protected context prohibited")
    return result


def validate_records(block, observations):
    frames = block["frames"]
    check(len(frames) == len(observations), "Observation census differs")
    for offset, (frame, row) in enumerate(zip(frames, observations, strict=True)):
        check(row["source_frame_index"] == frame["source_frame_index"]
              and row["source_pts_ticks"] == frame["source_pts_ticks"]
              and row["time_base"] == block["time_base"], "Native observation join differs")
        check({"path", "sha256", "rgb_sha256"} <= row["source_png"].keys(), "Observation PNG identity incomplete")
        check(all(frame["png"].get(k) == v for k, v in row["source_png"].items()), "Observation PNG differs")
        check(row["inference_status"] == "completed", "Tool failure is not a missing model output")
        check(row.get("point_origin", "automatic") == "automatic", "Nonautomatic point in model comparison")
        expected = sum(start <= offset <= start + 2 for start in
                       range(max(0, offset - 2), min(offset + 1, len(frames) - 2)))
        check(row["temporal_contributions"] == expected, "Temporal contributors differ")
        evaluation.validate_component_selection(row)


def reused_observations(root, block, source):
    if source["kind"] == "retained_historical":
        return evaluation.baseline_observations(block)
    report = read_json(bound_path(root, source["report"]))
    if source["kind"] == "validation":
        check(report["checkpoint"] == source["checkpoint"] and report["protected_frames"] == 0
              and report["threshold"] == .3 and report["strict_threshold"] is True,
              "Saved validation identity differs")
        matches = [b for b in report["blocks"] if b["block_id"] == block["block_id"]]
        check(len(matches) == 1, "Saved validation block is not unique")
        observations = matches[0]["observations"]
    elif source["kind"] == "historical_adaptation":
        check(report["checkpoint"] == source["checkpoint"]
              and report["identity"]["model_checkpoint"] == source["checkpoint"]
              and report["identity"]["policy"] == {"heatmap_threshold": .3, "triplet_stride": 1,
                  "aggregation": "mean_aligned_complete_native_triplets", "padding": "none", "resampling": "none",
                  "selection": "largest_component_mass", "device": "cuda"}
              and report["identity"]["source_video"] == block["source_video"],
              "Saved historical model/policy/source differs")
        observations = report["frames"]
    else:
        raise ValueError("Unknown saved-observation producer")
    result = deepcopy(observations)
    for frame, row in zip(block["frames"], result, strict=True):
        # Producer PNG bindings may omit byte size, but may not disagree.
        check({"path", "sha256", "rgb_sha256"} <= row["source_png"].keys(), "Saved PNG identity incomplete")
        check(all(frame["png"].get(k) == v for k, v in row["source_png"].items()), "Saved PNG differs")
        row["source_png"] = deepcopy(frame["png"])
    validate_records(block, result)
    return result


def preflight(root, config_path):
    root = Path(root).resolve()
    config = read_json(root / config_path)
    check(config["schema_version"] == SCHEMA and config["status"] == "frozen_before_execution"
          and config["protected_evaluation_authorized"] is False and config["training_authorized"] is False,
          "Frozen evaluation-only scope required")
    check(config["inference_policy"] == evaluation.POLICY, "Inference policy changed")
    check(config["runtime"] == runtime_versions(), "Runtime changed")
    for item in config["code_bindings"]:
        bound_path(root, item)
    parent = read_json(bound_path(root, config["primary_recipe"]))
    for item in parent["code_bindings"]:
        bound_path(root, item)
    training = read_json(bound_path(root, config["training_package"]))
    comparison = read_json(bound_path(root, config["comparison_package"]))
    check(config["training_package"] == parent["package"], "Original accepted package changed")
    for item in training["reference_bindings"] + comparison["reference_bindings"]:
        bound_path(root, item)
    blocks = blocks_from_packages(training, comparison)
    check(config["block_ids"] == [b["block_id"] for b in blocks], "Frozen block scope changed")
    check(len(config["models"]) == 12 and len({m["checkpoint"]["sha256"] for m in config["models"]}) == 12,
          "Expected twelve unique saved weights")
    calls, reused = 0, 0
    for model in config["models"]:
        bound_path(root, model["checkpoint"])
        bound_path(root, model["provenance"])
        check(set(model["reuse"]) <= set(config["block_ids"]), "Unexpected reuse block")
        for block in blocks:
            source = model["reuse"].get(block["block_id"])
            if source:
                check(source["checkpoint"] == model["checkpoint"], "Reused prediction belongs to another model")
                if source["kind"] == "retained_historical":
                    check(model["checkpoint"]["sha256"] == comparison["baseline_checkpoint_sha256"],
                          "Retained outputs cannot represent different weights")
                if source["kind"] == "historical_adaptation":
                    report = read_json(bound_path(root, source["report"]))
                    provenance = read_json(bound_path(root, model["provenance"]))
                    check(report["identity"]["training"] == model["provenance"]
                          and report["identity"]["config"] == provenance["config"],
                          "Historical observation/training provenance differs")
                records = reused_observations(root, block, source)
                validate_records(block, records)
                reused += len(records)
            else:
                calls += len(block["frames"]) - 2
    check(calls == config["new_model_calls"] and reused == config["reused_observation_frames"],
          "Frozen work census changed")
    return config, blocks, {"status": "passed", "models": 12, "contexts": 8,
        "new_model_calls": calls, "reused_observation_frames": reused,
        "protected_pixel_reads": 0, "optimizer_updates": 0}


class InputCache:
    """Exact existing affine preprocessing, once per source frame, disk mapped."""
    def __init__(self, root, blocks, folder):
        self.root, self.blocks, self.folder = Path(root), blocks, Path(folder)
        self.arrays, self.positions = {}, {}

    def prepare(self):
        receipts = []
        for block in self.blocks:
            folder = self.folder / key(block)
            folder.mkdir(parents=True, exist_ok=True)
            expected = {"block_sha256": canonical(block), "representation": "affine_RGB_uint8_288x512",
                "adapter": binding(self.root, Path(preprocess_triplet.__code__.co_filename)),
                "runtime": binding(self.root, Path(runtime.__file__))}
            receipt_path = folder / "receipt.json"
            if receipt_path.exists():
                receipt = read_json(receipt_path)
                check(receipt["identity"] == expected, "Input-cache identity changed")
                path = bound_path(self.root, receipt["array"])
            else:
                attempt = folder / "attempts" / uuid.uuid4().hex
                attempt.mkdir(parents=True, exist_ok=False)
                write_once(attempt / "started.json", expected)
                path = attempt / "frames.npy"
                array = np.lib.format.open_memmap(path, mode="w+", dtype=np.uint8,
                    shape=(len(block["frames"]), 288, 512, 3))
                images = evaluation.NativeImages(self.root, block)
                source = block["source_video"]
                forward, _ = affine_matrices(source["width_px"], source["height_px"])
                try:
                    for offset, frame in enumerate(block["frames"]):
                        array[offset] = cv2.warpAffine(images.get(frame), forward, (512, 288), flags=cv2.INTER_LINEAR)
                    array.flush()
                finally:
                    array._mmap.close()
                receipt = {"identity": expected, "array": binding(self.root, path),
                    "native_png_decodes": images.decoded, "source_video_decodes": 0, "protected_reads": 0}
                write_once(receipt_path, receipt)
            self.arrays[block["block_id"]] = np.load(path, mmap_mode="r", allow_pickle=False)
            check(self.arrays[block["block_id"]].dtype == np.uint8
                  and self.arrays[block["block_id"]].shape == (len(block["frames"]), 288, 512, 3),
                  "Input-cache shape or dtype differs")
            self.positions[block["block_id"]] = {f["source_frame_index"]: i for i, f in enumerate(block["frames"])}
            # Actual producer comparison on first/middle/final native triplets.
            verified = []
            images = evaluation.NativeImages(self.root, block)
            for offset in sorted({0, (len(block["frames"]) - 3) // 2, len(block["frames"]) - 3}):
                frames = block["frames"][offset:offset + 3]
                expected_tensor, _ = preprocess_triplet([images.get(f) for f in frames])
                actual = self.inputs(block["block_id"], frames)
                check(torch.equal(actual.unsqueeze(0), expected_tensor), "Cached/original preprocessing differs")
                verified.append([f["source_frame_index"] for f in frames])
            receipts.append({"receipt": binding(self.root, receipt_path), "exact_preprocessing_triplets": verified})
            print(json.dumps({"event": "cache_verified", "block": block["block_id"], "frames": len(block["frames"])}), flush=True)
        return receipts

    def inputs(self, block_id, frames):
        return torch.cat([runtime.normalized_tensor(self.arrays[block_id][self.positions[block_id][f["source_frame_index"]]])
                          for f in frames])

    def close(self):
        for array in self.arrays.values():
            array._mmap.close()
        self.arrays.clear()


def infer(block, model, device, cache, path, model_name):
    calls = 0
    def provide(frames):
        nonlocal calls
        with torch.inference_mode():
            logits = model(cache.inputs(block["block_id"], frames).unsqueeze(0).to(device))[0]
            check(logits.shape == (1, 3, 288, 512) and bool(torch.isfinite(logits).all()), "Invalid inference logits")
            values = logits.sigmoid()[0].cpu().numpy().astype(np.float32, copy=False)
        calls += 1
        if calls % 250 == 0:
            print(json.dumps({"event": "inference_progress", "model": model_name, "block": block["block_id"],
                              "calls": calls}), flush=True)
        return values
    means = np.lib.format.open_memmap(path, mode="w+", dtype=np.float32, shape=(len(block["frames"]), 288, 512))
    records = []
    segment = {"kind": "nba_first_saved_model_comparison", "source_frame_range_inclusive": block["range_inclusive"]}
    try:
        for offset, (frame, mean, count) in enumerate(stream_means(block["frames"], provide)):
            check(mean is not None and np.isfinite(mean).all(), "Missing/invalid mean is not a model miss")
            means[offset] = mean
            records.append(select_observation(frame, mean, count, block, segment))
        means.flush()
    finally:
        means._mmap.close()
    validate_records(block, records)
    check(calls == len(block["frames"]) - 2, "Inference call census differs")
    return records, calls


def execute(root, config_path):
    from .nba_first_validation import score_block, aggregate_blocks
    root = Path(root).resolve()
    config, blocks, audit = preflight(root, config_path)
    output = root / config["output_root"]
    check(output.resolve().is_relative_to(root / "data/outputs") and output.resolve() != root / "data/outputs",
          "Evaluation output escaped data/outputs")
    output.mkdir(parents=True, exist_ok=True)
    identity = {"config": binding(root, root / config_path), "preflight": audit}
    completed_path = output / "completed.json"
    with training_lock(output / "evaluation.lock"):
        if completed_path.exists():
            completed = read_json(completed_path)
            check(completed["identity"] == identity, "Completed comparison identity differs")
            bound_path(root, completed["evaluation"])
            return completed
        attempt = output / "attempts" / uuid.uuid4().hex
        attempt.mkdir(parents=True, exist_ok=False)
        write_once(attempt / "started.json", {"identity": identity, "started_at_utc": stamp()})
        began = time.perf_counter()
        cache = InputCache(root, blocks, output / "input_cache")
        try:
            torch.set_num_threads(2)
            torch.backends.cudnn.benchmark = False
            torch.backends.cudnn.deterministic = True
            cv2.setNumThreads(1)
            cache_receipts = cache.prepare()
            write_once(attempt / "cache_preparation.json", cache_receipts)
            models = []
            total_calls = 0
            for model_spec in config["models"]:
                model_began = time.perf_counter()
                adapter = None
                reports, receipts = [], []
                for block in blocks:
                    folder = output / "models" / model_spec["name"] / key(block)
                    folder.mkdir(parents=True, exist_ok=True)
                    receipt_path = folder / "receipt.json"
                    block_identity = {"config": identity["config"], "checkpoint": model_spec["checkpoint"],
                                      "block_sha256": canonical(block)}
                    if receipt_path.exists():
                        receipt = read_json(receipt_path)
                        check(receipt["identity"] == block_identity, "Resumed block identity differs")
                        body = read_json(bound_path(root, receipt["records"]))
                        if receipt.get("mean_heatmaps"):
                            bound_path(root, receipt["mean_heatmaps"])
                        observations = body["observations"]
                        validate_records(block, observations)
                        report = score_block(block, observations)
                        check(report == body["score"], "Resumed emitted score differs")
                    else:
                        block_attempt = folder / "attempts" / uuid.uuid4().hex
                        block_attempt.mkdir(parents=True, exist_ok=False)
                        write_once(block_attempt / "started.json", {"identity": block_identity, "started_at_utc": stamp()})
                        source = model_spec["reuse"].get(block["block_id"])
                        calls, heatmaps = 0, None
                        if source:
                            observations = reused_observations(root, block, source)
                        else:
                            if adapter is None:
                                adapter = evaluation.make_adapter(root, {"selected_method": {
                                    "checkpoint": model_spec["checkpoint"], "provenance": model_spec["provenance"]}})
                            path = block_attempt / "mean_heatmaps.npy"
                            observations, calls = infer(block, adapter.model, adapter.device, cache, path, model_spec["name"])
                            heatmaps = binding(root, path)
                        report = score_block(block, observations)
                        body_path = block_attempt / "records.json"
                        write_once(body_path, {"block_id": block["block_id"], "checkpoint": model_spec["checkpoint"],
                            "observations": observations, "score": report, "reused_source": source})
                        receipt = {"identity": block_identity, "records": binding(root, body_path),
                            "mean_heatmaps": heatmaps, "new_model_calls": calls, "reused": source is not None}
                        write_once(receipt_path, receipt)
                        total_calls += calls
                    reports.append(report)
                    receipts.append({"block_id": block["block_id"], "receipt": binding(root, receipt_path)})
                    summary = report["summary"]
                    print(json.dumps({"event": "block_completed", "model": model_spec["name"], "block": block["block_id"],
                        "correct": summary["matched"], "eligible": summary["eligible_frames"], "wrong": summary["wrong"],
                        "certain_hidden": summary["certain_hidden_emitted_frames"], "reused": receipt["reused"]}), flush=True)
                models.append({"name": model_spec["name"], "checkpoint": model_spec["checkpoint"],
                    "training_exposure": model_spec["training_exposure"], "records": receipts,
                    "episodes": [{"block_id": r["block_id"], "summary": r["summary"]} for r in reports],
                    "validation_summary": aggregate_blocks(reports[:6]),
                    "elapsed_seconds_this_attempt": time.perf_counter() - model_began})
                if adapter is not None:
                    del adapter
                    torch.cuda.empty_cache()
            report_path = output / "evaluation.json"
            write_once(report_path, {"schema_version": SCHEMA, "status": "completed_evaluation", "identity": identity,
                "models": models, "blocks": [{k: v for k, v in b.items() if k != "frames"} for b in blocks],
                "model_calls_this_attempt": total_calls, "protected_evaluation_authorized": False,
                "training_updates": 0, "new_labels": 0, "human_trajectory_acceptance": None,
                "model_adopted": False, "phase_pass_claimed": False,
                "scope": "NBA-first development comparison. Historical failures and high-school results remain unchanged.",
                "limits": ["HOU-OKC is repeatedly used validation, not a fresh test game.",
                           "SAC is training-exposed for fitted NBA models; report separately.",
                           "Sparse historical reference coverage cannot establish complete-context acceptance.",
                           "No automatic wrong-object identity or human visual acceptance is inferred."]})
            result = {"status": "completed", "identity": identity, "evaluation": binding(root, report_path),
                "attempt": binding(root, attempt / "started.json"), "elapsed_seconds_this_attempt": time.perf_counter() - began,
                "model_calls_this_attempt": total_calls, "optimizer_updates": 0, "protected_reads": 0,
                "finished_at_utc": stamp()}
            write_once(completed_path, result)
            return result
        except BaseException as error:
            write_once(attempt / "failed.json", {"status": "failed_preserved", "error_type": type(error).__name__,
                "error": str(error), "traceback": traceback.format_exc(), "elapsed_seconds": time.perf_counter() - began})
            raise
        finally:
            cache.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--config", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    result = execute(args.root, args.config) if args.run else preflight(args.root, args.config)[2]
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
