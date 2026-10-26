"""Thirty fixed, read-only WASB calls to explain five saved P003 outputs.

The default CLI is metadata-only. --run is for the owned GPU supervisor. No
optimizer, fitting, threshold search, label change, or phase acceptance exists.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import time
import traceback

import cv2
import numpy as np
from PIL import Image
import torch

from . import completion_evaluation as evaluation
from . import completion_training_runtime as runtime
from .nba_action_observation import select_observation, stream_means
from .wasb_adapter import affine_matrices, components_from_heatmap, preprocess_triplet
from .wasb_experiment import bound_path, canonical, read_json, runtime_versions
from .wasb_training import training_lock

SCHEMA = "wasb_validation_probe/v0.1"
CHALLENGE = "possession_003_frames_0150_0174_challenge_evaluation_development_v0_2"
REPRESENTATIVE = "possession_003_frames_0300_0324_representative_evaluation_development_v0_2"
SCOPE = {CHALLENGE: {"triplet_starts": [168, 169, 170, 171, 172], "target_frames": [170, 171, 172]},
         REPRESENTATIVE: {"triplet_starts": [302, 303, 304, 321, 322], "target_frames": [304, 323]}}
MODELS = {"baseline": 0, "control_epoch3": 3, "augmentation_epoch3": 3}
write_once, binding = runtime.atomic_write_once, runtime.binding


def check(value, message):
    if not value:
        raise ValueError(message)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def needed_frames(spec):
    return sorted({i for start in spec["triplet_starts"] for i in range(start, start + 3)})


def groups(starts):
    result = []
    for start in starts:
        if result and start == result[-1][-1] + 1:
            result[-1].append(start)
        else:
            result.append([start])
    return result


def preflight(root, config_path):
    """Verify metadata and code/checkpoint hashes without decoding images/tensors."""
    root = Path(root).resolve()
    path = (root / config_path).resolve()
    config = read_json(path)
    check(config["schema_version"] == SCHEMA and config["status"] == "frozen_before_model_execution"
          and config["protected_evaluation_authorized"] is False, "Frozen permitted diagnostic required")
    parent = read_json(bound_path(root, config["parent_recipe"]))
    augmented = read_json(bound_path(root, config["augmentation_recipe"]))
    check(config["parent_recipe"]["path"] == evaluation.PRIMARY_RECIPE
          and augmented["parent_recipe"] == config["parent_recipe"]
          and config["package"] == parent["package"], "Diagnostic parent/package differs")
    check(config["runtime"] == parent["runtime"] == augmented["runtime"] == runtime_versions(),
          "Diagnostic runtime differs from validation")
    check(len(parent["code_bindings"]) == 25, "Original dependency census differs")
    for entry in parent["code_bindings"] + augmented["code_bindings"] + config["code_bindings"]:
        bound_path(root, entry)
    required = {"src/ball_tracking/wasb_validation_probe.py", "src/ball_tracking/completion_evaluation.py",
                "src/ball_tracking/gpu_supervision.py"}
    check(required.issubset({b["path"] for b in config["code_bindings"]}), "Diagnostic code bindings incomplete")
    package = read_json(bound_path(root, config["package"]))
    check(package["protected_evaluation_authorized"] is False, "Protected package prohibited")
    available = {b["block_id"]: b for b in package["validation_blocks"]}
    specs = {b["block_id"]: b for b in config["blocks"]}
    check(len(specs) == len(config["blocks"]) == 2 and set(specs) == set(SCOPE), "Fixed block scope differs")
    cache_identity = {"package_sha256": canonical(package),
        "adapter_sha256": next(b["sha256"] for b in parent["code_bindings"] if b["path"].endswith("/wasb_adapter.py")),
        "runtime_sha256": next(b["sha256"] for b in parent["code_bindings"] if b["path"].endswith("/completion_training_runtime.py")),
        "representation": "affine_RGB_uint8_288x512"}
    for block_id, spec in specs.items():
        check(all(spec[k] == v for k, v in SCOPE[block_id].items()), "Fixed triplets/targets differ")
        block = available[block_id]
        check(block["role"] == "checkpoint_validation" and block["game_id"] == "possession_003"
              and block["source_video"]["width_px"] == 1920 and block["source_video"]["height_px"] == 1080,
              "Diagnostic source role/geometry differs")
        frames = {f["source_frame_index"]: f for f in block["frames"]}
        for index in needed_frames(spec):
            check(index in frames and frames[index]["annotation"]["frame_index"] == index
                  and not any(lo <= index <= hi for lo, hi in package["protected_ranges"].get("possession_003", [])),
                  "Diagnostic index outside permitted validation block")
        receipt = read_json(bound_path(root, spec["cache_receipt"]))
        check(receipt["identity"] == cache_identity and receipt["block_id"] == block_id
              and receipt["block_sha256"] == canonical(block), "Frozen cache receipt identity differs")
        verified = {r["source_frame_index"]: r for r in receipt["verified_frames"]}
        check(len(verified) == len(block["frames"]) and all(verified[i]["source_png"] == frames[i]["png"]
              for i in needed_frames(spec)), "Frozen cache/source transport differs")
    models = {m["name"]: m for m in config["models"]}
    check(len(models) == len(config["models"]) == 3 and set(models) == set(MODELS), "Fixed checkpoint scope differs")
    reports = {}
    for name, model in models.items():
        expected_folder = augmented["output_root"] if name == "augmentation_epoch3" else parent["output_root"]
        check(model["validation_report"]["path"] == expected_folder + f"/validation/epoch_{MODELS[name]:03d}.json",
              "Diagnostic validation source differs")
        report = read_json(bound_path(root, model["validation_report"]))
        check(report["epoch"] == MODELS[name] and report["checkpoint"] == model["checkpoint"]
              and report["identity"]["recipe"] == (config["augmentation_recipe"] if name == "augmentation_epoch3" else config["parent_recipe"])
              and report["protected_frames"] == 0 and report["strict_threshold"] is True and report["threshold"] == .3,
              "Saved validation checkpoint/policy identity differs")
        bound_path(root, model["checkpoint"])
        reports[name] = report
    check(models["baseline"]["checkpoint"] == parent["initialization"]["checkpoint"], "Retained baseline differs")
    output = (root / config["output_root"]).resolve()
    check(output.is_relative_to(root / "data/outputs") and output != root / "data/outputs", "Output escaped data/outputs")
    identity = {"scope": binding(root, path), "protected_evaluation_authorized": False,
                "model_calls": 30, "unique_native_frames": 16, "target_outputs": 15,
                "inference_policy": evaluation.POLICY, "reproduction": "exact mean SHA256 and complete observation equality"}
    return config, package, reports, identity


class FrozenInputs:
    """Read only the declared rows of existing caches; never call prepare or write cache."""
    def __init__(self, root, package, scopes):
        self.root = Path(root).resolve()
        blocks = {b["block_id"]: b for b in package["validation_blocks"]}
        self.blocks, self.specs = {s["block_id"]: blocks[s["block_id"]] for s in scopes}, {s["block_id"]: s for s in scopes}
        self.arrays, self.receipts, self.positions, self.verified = {}, {}, {}, []
        try:
            for block_id, block in self.blocks.items():
                check(block["role"] == "checkpoint_validation", "Only declared validation cache allowed")
                for index in needed_frames(self.specs[block_id]):
                    check(not any(lo <= index <= hi for lo, hi in package.get("protected_ranges", {}).get(block["game_id"], [])),
                          "Protected cache access prohibited")
                receipt = read_json(bound_path(self.root, self.specs[block_id]["cache_receipt"]))
                check(receipt["block_sha256"] == canonical(block) and receipt["block_id"] == block_id, "Stale cache block")
                array = np.load(bound_path(self.root, receipt["warped_frames"]), mmap_mode="r", allow_pickle=False)
                self.arrays[block_id] = array
                check(array.shape == (len(block["frames"]), 288, 512, 3) and array.dtype == np.uint8, "Cache shape differs")
                self.receipts[block_id] = receipt
                self.positions[block_id] = {f["source_frame_index"]: j for j, f in enumerate(block["frames"])}
        except BaseException:
            self.close()
            raise

    def verify_sources(self):
        for block_id, block in self.blocks.items():
            source = block["source_video"]
            forward, _ = affine_matrices(source["width_px"], source["height_px"])
            receipts = {r["source_frame_index"]: r for r in self.receipts[block_id]["verified_frames"]}
            for index in needed_frames(self.specs[block_id]):
                position = self.positions[block_id][index]
                frame = block["frames"][position]
                raw = bound_path(self.root, frame["png"]).read_bytes()
                with Image.open(io.BytesIO(raw)) as image:
                    check(image.mode == "RGB", "Source PNG must be RGB")
                    rgb = np.asarray(image).copy()
                check(rgb.shape == (source["height_px"], source["width_px"], 3)
                      and hashlib.sha256(rgb.tobytes()).hexdigest() == frame["png"]["rgb_sha256"], "Source RGB identity differs")
                warped = cv2.warpAffine(rgb, forward, (512, 288), flags=cv2.INTER_LINEAR)
                cached = self.arrays[block_id][position]
                check(receipts[index]["source_png"] == frame["png"]
                      and hashlib.sha256(cached.tobytes()).hexdigest() == receipts[index]["warped_rgb_sha256"]
                      and np.array_equal(cached, warped), "Cached warp differs from actual source PNG")
                expected, _ = preprocess_triplet([rgb, rgb, rgb])
                check(torch.equal(runtime.normalized_tensor(cached), expected[0, :3]), "Cached normalization differs from adapter")
                self.verified.append({"block_id": block_id, "source_frame_index": index, "source_png": frame["png"],
                    "warped_rgb_sha256": receipts[index]["warped_rgb_sha256"], "exact_warp_and_normalization_match": True})
        return self.verified

    def inputs(self, block_id, indices):
        check(indices == list(range(indices[0], indices[0] + 3))
              and indices[0] in self.specs[block_id]["triplet_starts"], "Undeclared triplet prohibited")
        return torch.cat([runtime.normalized_tensor(self.arrays[block_id][self.positions[block_id][i]]) for i in indices])

    def close(self):
        for array in self.arrays.values():
            array._mmap.close()
        self.arrays.clear()


def state_digest(model):
    """Hash every named tensor, including BatchNorm buffers, without optimizer state."""
    hashes = []
    for name, tensor in sorted(model.state_dict().items()):
        value = tensor.detach().cpu().contiguous()
        hashes.append({"name": name, "dtype": str(value.dtype), "shape": list(value.shape),
                       "sha256": hashlib.sha256(value.numpy().tobytes()).hexdigest()})
    return {"sha256": canonical(hashes), "tensor_count": len(hashes), "tensors": hashes}


def diagnostic_map(heatmap, frame, block):
    source = block["source_video"]
    forward, inverse = affine_matrices(source["width_px"], source["height_px"])
    check(heatmap.dtype == np.float32 and heatmap.shape == (288, 512) and np.isfinite(heatmap).all(), "Invalid diagnostic map")
    center = frame["annotation"]["geometry"]["center_xy_px"]
    yy, xx = np.indices(heatmap.shape)
    native_x = inverse[0, 0] * xx + inverse[0, 1] * yy + inverse[0, 2]
    native_y = inverse[1, 0] * xx + inverse[1, 1] * yy + inverse[1, 2]
    distances = np.hypot(native_x - center[0], native_y - center[1])
    local = (distances <= 10) & (native_x >= 0) & (native_x < source["width_px"]) & (native_y >= 0) & (native_y < source["height_px"])
    def peak(mask=None):
        if mask is not None and not mask.any():
            return None
        offset = int(np.argmax(heatmap if mask is None else np.where(mask, heatmap, -np.inf)))
        y, x = np.unravel_index(offset, heatmap.shape)
        return {"heatmap_xy": [int(x), int(y)], "value": float(heatmap[y, x]),
                "source_xy_px": [float(native_x[y, x]), float(native_y[y, x])],
                "reference_distance_px": float(distances[y, x])}
    components = components_from_heatmap(heatmap, source["width_px"], source["height_px"], threshold=.3)
    for index, item in enumerate(components):
        item.update(candidate_index=index, reference_distance_px=float(np.hypot(item["center_x"] - center[0], item["center_y"] - center[1])))
    mapped = forward @ np.array([*center, 1.0], dtype=np.float32)
    quantized = mapped.astype(np.int32)
    quantized_native = inverse @ np.array([*quantized, 1.0], dtype=np.float32)
    return {"heatmap_sha256": hashlib.sha256(heatmap.tobytes()).hexdigest(), "global_peak": peak(), "local_peak": peak(local),
            "strict_threshold_pixel_count": int(np.count_nonzero(heatmap > np.float32(.3))),
            "local_strict_threshold_pixel_count": int(np.count_nonzero(local & (heatmap > np.float32(.3)))),
            "local_radius_source_px": 10, "components": components,
            "reference_center_xy_px": center, "reference_heatmap_xy": mapped.tolist(),
            "integer_target_center_xy": quantized.tolist(), "integer_target_center_source_xy": quantized_native.tolist(),
            "target_quantization_error_px": float(np.linalg.norm(quantized_native - center)),
            "target_radius_heatmap_px": 2.5,
            "target_nonzero_pixels": int(np.count_nonzero((xx - quantized[0]) ** 2 + (yy - quantized[1]) ** 2 <= 2.5 ** 2))}


def collect_block(root, block, spec, provider, folder, expected_observations):
    """Produce original observations from exact contributor windows, retaining raw maps."""
    root, folder = Path(root).resolve(), Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    frames = {f["source_frame_index"]: f for f in block["frames"]}
    raw, raw_bindings, means = {}, {}, {}
    segment = {"kind": "fixed_checkpoint_validation", "source_frame_range_inclusive":
               [block["frames"][0]["source_frame_index"], block["frames"][-1]["source_frame_index"]]}
    def provide(rows):
        start = rows[0]["source_frame_index"]
        check(start in spec["triplet_starts"] and start not in raw, "Undeclared/repeated model call")
        values = provider(rows)
        check(values.shape == (3, 288, 512) and values.dtype == np.float32 and np.isfinite(values).all()
              and (values >= 0).all() and (values <= 1).all(), "Invalid model probabilities")
        raw[start] = values.copy()
        path = folder / f"triplet_{start:06d}.npz"
        with path.open("xb") as stream:
            np.savez_compressed(stream, heatmaps=values)
        with np.load(path, allow_pickle=False) as transported:
            check(transported.files == ["heatmaps"] and np.array_equal(transported["heatmaps"], values), "Saved triplet maps differ")
        raw_bindings[start] = binding(root, path)
        return values
    for group in groups(spec["triplet_starts"]):
        rows = [frames[i] for i in range(group[0], group[-1] + 3)]
        for frame, mean, count in stream_means(rows, provide):
            if frame["source_frame_index"] in spec["target_frames"]:
                means[frame["source_frame_index"]] = (mean, count)
    check(set(means) == set(spec["target_frames"]), "Target output census differs")
    targets = []
    for index in spec["target_frames"]:
        frame, (mean, count) = frames[index], means[index]
        observation = select_observation(frame, mean, count, block, segment)
        expected = expected_observations[index]
        mean_diag = diagnostic_map(mean, frame, block)
        contributors = []
        for start in spec["triplet_starts"]:
            if start <= index <= start + 2:
                plane = raw[start][index - start]
                probes = {name: float(plane[p["heatmap_xy"][1], p["heatmap_xy"][0]]) if p else None
                          for name, p in (("at_mean_global_peak", mean_diag["global_peak"]), ("at_mean_local_peak", mean_diag["local_peak"]))}
                contributors.append({"triplet_start": start, "channel": index - start, "raw_maps": raw_bindings[start],
                                     "diagnostic": diagnostic_map(plane, frame, block), **probes})
        check(len(contributors) == count, "Contributor count differs")
        mean_path = folder / f"mean_{index:06d}.npz"
        with mean_path.open("xb") as stream:
            np.savez_compressed(stream, mean=mean)
        with np.load(mean_path, allow_pickle=False) as transported:
            check(transported.files == ["mean"] and np.array_equal(transported["mean"], mean), "Saved mean map differs")
        targets.append({"source_frame_index": index, "source_png": frame["png"], "observation": observation,
            "expected_observation": expected, "mean_map": binding(root, mean_path), "mean_diagnostic": mean_diag,
            "contributors": contributors, "reproduction": {"mean_hash_equal": observation["mean_heatmap_sha256"] == expected["mean_heatmap_sha256"],
                "observation_equal": observation == expected,
                "differing_fields": [k for k in sorted(set(observation) | set(expected)) if observation.get(k) != expected.get(k)]}})
    write_once(folder / "targets.json", {"block_id": block["block_id"], "targets": targets, "model_calls": len(raw)})
    check(all(t["reproduction"]["mean_hash_equal"] and t["reproduction"]["observation_equal"] for t in targets),
          "Saved validation reproduction differs; raw evidence retained, no diagnostic completion")
    return targets


def execute(root, config_path):
    root = Path(root).resolve()
    config, package, reports, identity = preflight(root, config_path)
    output = root / config["output_root"]
    check(not output.exists(), "Preserve existing diagnostic attempt; no automatic retry")
    output.mkdir(parents=True)
    write_once(output / "started.json", {"identity": identity, "started_at_utc": stamp()})
    began, store, adapter, calls = time.perf_counter(), None, None, 0
    before, current_name = None, None
    old_backend = (torch.backends.cudnn.benchmark, torch.backends.cudnn.deterministic)
    try:
        with training_lock(output / "diagnostic.lock"):
            store = FrozenInputs(root, package, config["blocks"])
            verified = store.verify_sources()
            check(len(verified) == 16, "Verified source census differs")
            write_once(output / "input_verification.json", {"frames": verified, "native_png_decodes": 16, "source_video_decodes": 0,
                "protected_png_reads": 0, "cache_modified": False})
            torch.backends.cudnn.benchmark, torch.backends.cudnn.deterministic = False, True
            results = []
            for model in config["models"]:
                current_name = model["name"]
                adapter = evaluation.make_adapter(root, {"selected_method": {"checkpoint": model["checkpoint"],
                    "validation_report": model["validation_report"], "diagnostic_scope": identity["scope"],
                    "method_kind": "read_only_checkpoint_probe_not_selection"}})
                check(all(not module.training for module in adapter.model.modules()), "Probe requires evaluation mode")
                before = state_digest(adapter.model)
                write_once(output / current_name / "state_before.json", before)
                targets = []
                for spec in config["blocks"]:
                    block = store.blocks[spec["block_id"]]
                    saved = next(b for b in reports[current_name]["blocks"] if b["block_id"] == block["block_id"])
                    expected = {r["source_frame_index"]: r for r in saved["observations"]}
                    def provider(frames):
                        nonlocal calls
                        indices = [f["source_frame_index"] for f in frames]
                        with (output / "calls.jsonl").open("a", encoding="utf-8") as stream:
                            stream.write(json.dumps({"event": "started", "model": current_name, "frames": indices, "at": stamp()}) + "\n")
                        inputs = store.inputs(block["block_id"], indices)
                        with torch.inference_mode():
                            logits = adapter.model(inputs.unsqueeze(0).to(adapter.device))[0]
                            check(logits.shape == (1, 3, 288, 512) and bool(torch.isfinite(logits).all()), "Invalid validation logits")
                            values = logits.sigmoid()[0].cpu().numpy().astype(np.float32, copy=False)
                        calls += 1
                        with (output / "calls.jsonl").open("a", encoding="utf-8") as stream:
                            stream.write(json.dumps({"event": "completed", "model": current_name, "frames": indices, "calls": calls, "at": stamp()}) + "\n")
                        return values
                    key = hashlib.sha256(block["block_id"].encode()).hexdigest()[:24]
                    targets.extend(collect_block(root, block, spec, provider, output / current_name / key, expected))
                after = state_digest(adapter.model)
                write_once(output / current_name / "state_after.json", after)
                check(after == before, "Loaded model parameters/BatchNorm buffers changed")
                results.append({"model": model, "targets": targets, "model_state_unchanged": True,
                    "state_before": binding(root, output / current_name / "state_before.json"),
                    "state_after": binding(root, output / current_name / "state_after.json")})
                del adapter
                adapter, before = None, None
                print(f"Verified diagnostic {current_name}: 5 saved outputs, 10 calls", flush=True)
            check(calls == 30, "Fixed model-call census differs")
            result = {"schema_version": SCHEMA, "status": "completed", "identity": identity, "models": results,
                "model_calls": calls, "elapsed_seconds": time.perf_counter() - began, "threshold_sweep": False,
                "optimizer_created": False, "labels_modified": False, "protected_evaluation_authorized": False,
                "ball_phase_accepted": False, "human_visual_acceptance": None}
            write_once(output / "completed.json", result)
            return result
    except BaseException as error:
        mutation = None
        if adapter is not None and before is not None:
            try:
                after = state_digest(adapter.model)
                write_once(output / current_name / "state_after_failure.json", after)
                mutation = after != before
            except BaseException as audit_error:
                mutation = {"verification_error": str(audit_error)}
        write_once(output / "failed.json", {"identity": identity, "error": str(error), "traceback": traceback.format_exc(),
            "completed_model_calls": calls, "model_state_changed": mutation, "elapsed_seconds": time.perf_counter() - began,
            "automatic_retry": False, "protected_evaluation_authorized": False})
        raise
    finally:
        if store is not None:
            store.close()
        del adapter
        torch.backends.cudnn.benchmark, torch.backends.cudnn.deterministic = old_backend


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--config", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.run:
        result = execute(args.root, args.config)
        print(json.dumps({k: result[k] for k in ("status", "model_calls", "elapsed_seconds")}))
    else:
        _, _, _, identity = preflight(args.root, args.config)
        print(json.dumps({"status": "metadata_preflight_passed_no_model_or_pixel_decode", "identity": identity}))


if __name__ == "__main__":
    main()
