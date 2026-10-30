"""Capture missing cosine-nine HOU mean maps without changing model behavior.

Metadata preparation imports no ML runtime. The only GPU entry requires the
existing owned-process supervisor. All source rows, means and candidates must
reproduce the completed research control exactly; this is not new training.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback
import uuid


ROOT = Path(__file__).resolve().parents[2]
MODULE = "src.ball_tracking.weak_response_capture"
OUTPUT = "data/outputs/ball_tracking/weak_response_v0_1"
INVENTORY = OUTPUT + "/inventory.json"
PAIRED = "data/outputs/ball_tracking/wasb_continuation_v0_1/paired_review_inputs_v0_1.json"
AUDIT = "data/outputs/t/full_history_review_20261026/current_candidate_audit.json"
CHECKPOINT = "data/outputs/ball_tracking/wasb_continuation_v0_1/cosine/fit_v0_1/checkpoints/epoch_009.pth"
CHECKPOINT_SHA = "f4b721662ec3d8b546563feffcf5ce0d6319ed8ddc83f398830a0aac5d29c7b9"
RECIPE = "configs/ball_tracking/proposals/wasb_continuation_v0_1.json"
PRIMARY = "configs/ball_tracking/completion_campaign/primary_recipe_v0_1.json"
HOU = tuple(f"hou-vs-okc-0022400879_e{i:02}" for i in range(1, 7))
CONTEXTS = ("sas_det_q1_c02:10668-11898", *HOU, "sac_mem_q1_c01:540-2010")
RESOLUTION = {"width": 768, "height": 432, "target_radius": 3.75}
SOURCE_MODULES = (
    "weak_response_capture", "wasb_resolution", "completion_training_runtime",
    "wasb_adapter", "wasb_adapted_adapter", "completion_evaluation",
    "nba_first_evaluation", "gpu_supervision", "continuation_owned_guard",
)


def check(value, message):
    if not value:
        raise ValueError(message)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def bind(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    return {"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size,
            "sha256": digest(path)}


def bound(root, link):
    root = Path(root).resolve()
    path = (root / link["path"]).resolve()
    check(path.is_relative_to(root), "Bound input escaped repository")
    check(bind(root, path) == link, "Bound input changed: " + link["path"])
    return path


def write_once(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def validate_context(entry):
    block, observations = entry["block"], entry["candidate_observations"]
    check(block["block_id"] in CONTEXTS and block["domain"] == "nba", "Unexpected context")
    check(block.get("protected_evaluation_authorized", False) is False, "Protected context prohibited")
    frames = block["frames"]
    check(len(frames) == len(observations) >= 3, "Context census differs")
    indices = [f["source_frame_index"] for f in frames]
    check(indices == list(range(indices[0], indices[-1] + 1)), "Non-native frame order")
    base = Fraction(block["time_base"])
    check(base > 0, "Invalid time base")
    for i, (frame, row) in enumerate(zip(frames, observations, strict=True)):
        index = frame["source_frame_index"]
        check(frame.get("state", "permitted") == "permitted" and not any(
            lo <= index <= hi for lo, hi in block.get("protected_ranges", [])), "Protected row prohibited")
        check(type(frame["duration_ticks"]) is int and frame["duration_ticks"] > 0, "Invalid native interval")
        if i:
            prior = frames[i - 1]
            check(prior["source_pts_ticks"] + prior["duration_ticks"] == frame["source_pts_ticks"],
                  "Native timing discontinuity")
        check(row["source_frame_index"] == index and row["source_pts_ticks"] == frame["source_pts_ticks"]
              and row["source_png"] == frame["png"] and Fraction(row["time_base"]) == base,
              "Original observation/source transport differs")
        check(row["inference_status"] == "completed" and row.get("point_origin", "automatic") == "automatic",
              "Only completed automatic source rows allowed")
    if block["block_id"] in HOU:
        check(block["role"] == "checkpoint_validation" and block["game_id"] == "0022400879"
              and len(frames) == (120 if block["block_id"] in HOU[:4] else 240), "HOU role/census differs")


def inventory(root=ROOT):
    """Read permitted cache metadata/arrays on CPU, never import Torch or models."""
    import numpy as np
    root = Path(root).resolve()
    paired, audit = read(root / PAIRED), read(root / AUDIT)
    check(paired["protected_evaluation_authorized"] is False, "Protected inputs prohibited")
    control = bind(root, root / CHECKPOINT)
    check(control == {"path": CHECKPOINT, "bytes": 6084071, "sha256": CHECKPOINT_SHA}
          and paired["candidate"]["checkpoint"] == control, "Cosine-nine research control changed")
    recipe, primary = read(root / RECIPE), read(root / PRIMARY)
    check(recipe["resolution"] == RESOLUTION, "Resolution differs")
    package_link = primary["package"]
    bound(root, package_link)
    entries = paired["blocks"]
    check(tuple(e["block"]["block_id"] for e in entries) == CONTEXTS, "Eight-context census/order differs")
    originals = {b["block_id"]: b["candidate_records"] for b in audit["models"]["cosine_epoch9"]["blocks"]}
    result = []
    for entry in entries:
        validate_context(entry)
        block, rows = entry["block"], entry["candidate_observations"]
        key = hashlib.sha256(block["block_id"].encode()).hexdigest()[:24]
        original_link = originals[block["block_id"]]
        original_path = bound(root, original_link)
        original = read(original_path)
        check(original["checkpoint"] == control and original["observations"] == rows,
              "Paired records differ from actual cosine-nine producer")
        hou = block["block_id"] in HOU
        cache_root = recipe["cache_root"] if hou else recipe["evaluation_cache_root"]
        receipt_path = root / cache_root / key / "receipt.json"
        receipt = read(receipt_path)
        array_link = receipt["warped_frames"] if hou else receipt["array"]
        array_path = bound(root, array_link)
        array = np.load(array_path, mmap_mode="r", allow_pickle=False)
        try:
            check(array.shape == (len(rows), 432, 768, 3) and array.dtype == np.uint8,
                  "Native input cache shape/dtype differs")
        finally:
            array._mmap.close()
        if hou:
            check(receipt["block_id"] == block["block_id"] and len(receipt["verified_frames"]) == len(rows),
                  "HOU input cache coverage differs")
            for cached, frame in zip(receipt["verified_frames"], block["frames"], strict=True):
                check(cached["source_frame_index"] == frame["source_frame_index"]
                      and cached["source_png"] == frame["png"], "Cached native source binding differs")
        mean_path = original_path.parent / "mean_heatmaps.npy"
        mean_link = None
        if mean_path.exists():
            mean_link = bind(root, mean_path)
            means = np.load(mean_path, mmap_mode="r", allow_pickle=False)
            try:
                check(means.shape == (len(rows), 432, 768) and means.dtype == np.float32,
                      "Saved mean-map shape/dtype differs")
                for offset, row in enumerate(rows):
                    check(hashlib.sha256(means[offset].tobytes()).hexdigest() == row["mean_heatmap_sha256"],
                          "Saved map/producer digest differs")
            finally:
                means._mmap.close()
        check(hou == (mean_link is None), "Saved mean coverage changed; revise capture scope before execution")
        result.append({"block_id": block["block_id"], "role": block["role"], "frames": len(rows),
            "source_frame_range_inclusive": [rows[0]["source_frame_index"], rows[-1]["source_frame_index"]],
            "time_base": block["time_base"], "source_video": block["source_video"],
            "native_png_bindings_sha256": canonical([f["png"] for f in block["frames"]]),
            "native_png_binding_source": {"path": PAIRED, "block_id": block["block_id"], "field": "block.frames[].png"},
            "native_input_receipt": bind(root, receipt_path), "native_input_array": array_link,
            "original_records": original_link, "saved_mean_maps": mean_link,
            "mean_hashes_checked": 0 if mean_link is None else len(rows),
            "new_forward_calls_required": len(rows) - 2 if hou else 0})
        print(json.dumps({"event": "inventory_context_verified", "block": block["block_id"],
                          "saved_means": mean_link is not None}), flush=True)
    return {"schema_version": "weak_response_inventory/v0.1", "created_at_utc": stamp(),
        "checkpoint": control, "paired_inputs": bind(root, root / PAIRED), "candidate_audit": bind(root, root / AUDIT),
        "continuation_recipe": bind(root, root / RECIPE), "primary_recipe": bind(root, root / PRIMARY),
        "training_package": package_link,
        "source_roles": bind(root, root / "configs/ball_tracking/completion_campaign/source_roles_v0_1.json"),
        "source_modules": [bind(root, root / f"src/ball_tracking/{name}.py") for name in SOURCE_MODULES],
        "runtime": recipe["runtime"], "resolution": RESOLUTION, "blocks": result,
        "new_forward_calls_required": sum(b["new_forward_calls_required"] for b in result),
        "new_mean_array_bytes": 960 * 432 * 768 * 4 + 6 * 128,
        "new_model_calls": 0, "new_optimizer_updates": 0, "protected_evaluation_authorized": False,
        "source_images_decoded": 0, "model_adopted": False,
        "cache_search_scope": "Current cosine fit/comparison directories and their bound upstream 768 caches; no HOU maps retained by validate_epoch."}


def capture_block(block, expected, path, provider):
    """Unchanged producer kernels plus exact row/hash comparison on actual output."""
    import numpy as np
    from . import wasb_resolution as resolution
    check(not Path(path).exists(), "Mean destination already exists")
    frames = block["frames"]
    check(len(frames) == len(expected) >= 3, "Capture frame census differs")
    calls = 0

    def provide(selected):
        nonlocal calls
        values = provider(selected)
        calls += 1
        return values

    segment = {"kind": "fixed_checkpoint_validation", "source_frame_range_inclusive":
               [frames[0]["source_frame_index"], frames[-1]["source_frame_index"]]}
    array = np.lib.format.open_memmap(path, mode="w+", dtype=np.float32, shape=(len(frames), 432, 768))
    observations = []
    try:
        for offset, (frame, mean, count) in enumerate(resolution.stream_means(frames, provide)):
            row = resolution.select_observation(frame, mean, count, block, segment)
            check(row == expected[offset], "Regenerated mean/native observation differs at "
                  + block["block_id"] + ":" + str(frame["source_frame_index"]))
            array[offset] = mean
            observations.append(row)
        check(calls == len(frames) - 2, "Capture call census differs")
        array.flush()
    finally:
        array._mmap.close()
    return observations, calls


def capture(root, inventory_path, monitor, arguments):
    root = Path(root).resolve()
    from .continuation_owned_guard import verify_owned_worker
    # Importing ML libraries and reading model weights happens only after this guard.
    ownership = verify_owned_worker(root, root / monitor, MODULE, arguments)
    inv = read(root / inventory_path)
    check(inv["schema_version"] == "weak_response_inventory/v0.1" and inv["new_forward_calls_required"] == 948
          and inv["protected_evaluation_authorized"] is False, "Unexpected capture inventory")
    for link in inv["source_modules"]:
        bound(root, link)
    for key in ("checkpoint", "paired_inputs", "candidate_audit", "continuation_recipe", "primary_recipe",
                "training_package", "source_roles"):
        bound(root, inv[key])
    check(inv["checkpoint"]["sha256"] == CHECKPOINT_SHA and inv["checkpoint"]["path"] == CHECKPOINT
          and inv["resolution"] == RESOLUTION, "Capture model/resolution differs")
    paired, recipe = read(root / PAIRED), read(root / RECIPE)
    entries = {entry["block"]["block_id"]: entry for entry in paired["blocks"]}
    check(tuple(entries) == CONTEXTS, "Context scope changed")
    hou_inventory = [b for b in inv["blocks"] if b["block_id"] in HOU]
    check(tuple(b["block_id"] for b in hou_inventory) == HOU, "HOU capture scope/order differs")
    output = root / OUTPUT / "capture_v0_1"
    check(not output.exists(), "Capture attempt already exists; no automatic repeat or overwrite")
    attempt = output / "attempts" / uuid.uuid4().hex
    attempt.mkdir(parents=True, exist_ok=False)
    write_once(attempt / "started.json", {"started_at_utc": stamp(), "inventory": bind(root, root / inventory_path),
               "owned_worker": ownership, "expected_forward_calls": 948, "expected_frames": 960,
               "new_optimizer_updates": 0, "protected_evaluation_authorized": False})
    started = time.perf_counter()
    counters = {b: {"attempted_calls": 0, "completed_calls": 0, "verified_frames": 0} for b in HOU}
    store, adapter = None, None
    try:
        import cv2
        import numpy as np
        import torch
        from . import completion_evaluation as evaluation
        from . import wasb_resolution as resolution
        from .wasb_experiment import runtime_versions
        check(runtime_versions() == inv["runtime"], "Pinned runtime differs")
        torch.set_num_threads(2)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        cv2.setNumThreads(1)
        package = read(root / inv["training_package"]["path"])
        store = resolution.FrameStore(root, package, root / recipe["cache_root"])
        store.blocks = {b: store.blocks[b] for b in HOU}
        for item in hou_inventory:
            validate_context(entries[item["block_id"]])
            bound(root, item["native_input_receipt"])
            bound(root, item["native_input_array"])
            bound(root, item["original_records"])
        write_once(attempt / "cache_verification.json", store.prepare())
        adapter = evaluation.make_adapter(root, {"selected_method": {"checkpoint": inv["checkpoint"],
                   "provenance": {"inventory": bind(root, root / inventory_path), "research_control_only": True}}})
        results = []
        with (attempt / "forward_journal.jsonl").open("x", encoding="utf-8", buffering=1) as journal:
            for item in hou_inventory:
                block_id = item["block_id"]
                entry = entries[block_id]
                block, expected = entry["block"], entry["candidate_observations"]
                folder = attempt / hashlib.sha256(block_id.encode()).hexdigest()[:24]
                folder.mkdir()
                counts = counters[block_id]

                def provide(frames):
                    indices = [f["source_frame_index"] for f in frames]
                    counts["attempted_calls"] += 1
                    journal.write(json.dumps({"at": stamp(), "block_id": block_id, "event": "forward_attempt",
                                              "indices": indices, "attempted_calls": counts["attempted_calls"]}) + "\n")
                    values = resolution._model_values(adapter.model, adapter.device, store.inputs(block_id, indices), 768, 432)
                    counts["completed_calls"] += 1
                    journal.write(json.dumps({"at": stamp(), "block_id": block_id, "event": "forward_completed",
                                              "completed_calls": counts["completed_calls"]}) + "\n")
                    return values

                observations, calls = capture_block(block, expected, folder / "mean_heatmaps.npy", provide)
                check(calls == counts["attempted_calls"] == counts["completed_calls"], "Actual call counters differ")
                counts["verified_frames"] = len(observations)
                write_once(folder / "records.json", {"block_id": block_id, "checkpoint": inv["checkpoint"],
                    "original_records": item["original_records"], "observations": observations,
                    "mean_hashes_and_native_rows_identical": True, **counts})
                result = {"block_id": block_id, "mean_heatmaps": bind(root, folder / "mean_heatmaps.npy"),
                          "records": bind(root, folder / "records.json"), **counts}
                write_once(folder / "completed.json", result)
                results.append(result)
                print(json.dumps({"event": "capture_block_complete", "block_id": block_id, **counts}), flush=True)
        check(sum(x["completed_calls"] for x in counters.values()) == 948
              and sum(x["verified_frames"] for x in counters.values()) == 960, "Final capture census differs")
        result = {"schema_version": "weak_response_capture/v0.1", "status": "completed_exact_reproduction",
            "finished_at_utc": stamp(), "elapsed_seconds": time.perf_counter() - started,
            "inventory": bind(root, root / inventory_path), "attempt": attempt.relative_to(root).as_posix(),
            "blocks": results, "new_model_calls": 948, "verified_frames": 960, "new_optimizer_updates": 0,
            "protected_evaluation_authorized": False, "model_adopted": False,
            "forward_journal": bind(root, attempt / "forward_journal.jsonl")}
        write_once(output / "completed.json", result)
        return result
    except BaseException as error:
        write_once(attempt / "failed.json", {"failed_at_utc": stamp(), "elapsed_seconds": time.perf_counter() - started,
            "exception": type(error).__name__, "message": str(error), "traceback": traceback.format_exc(),
            "blocks": counters, "new_optimizer_updates": 0, "automatic_retry": False})
        raise
    finally:
        if store is not None:
            store.close()
        if adapter is not None:
            del adapter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--prepare", action="store_true")
    choice.add_argument("--run", action="store_true")
    parser.add_argument("--inventory", default=INVENTORY)
    parser.add_argument("--monitor")
    args = parser.parse_args()
    if args.prepare:
        check(not args.monitor, "Preparation has no GPU monitor")
        result = inventory(ROOT)
        write_once(ROOT / args.inventory, result)
        print(json.dumps({"inventory": bind(ROOT, ROOT / args.inventory), "new_model_calls": 0}), flush=True)
    else:
        check(args.monitor is not None, "GPU capture requires active owned supervisor")
        result = capture(ROOT, args.inventory, args.monitor, sys.argv[1:])
        print(json.dumps({"status": result["status"], "new_model_calls": result["new_model_calls"]}), flush=True)


if __name__ == "__main__":
    main()
