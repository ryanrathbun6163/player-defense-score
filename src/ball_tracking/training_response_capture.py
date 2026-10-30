"""Prepare/capture missing training-only responses; no fit, selector or new labels."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = "data/outputs/ball_tracking/training_response_preparation_v0_1"
MODULE = "src.ball_tracking.training_response_capture"
FIT = "data/outputs/ball_tracking/wasb_continuation_v0_1/current_training_fit_v0_1/assessment.json"
PREVIOUS_PREP = "data/outputs/t/wasb_continuation_20261026/current768_training_fit_preparation_20261026T194234636167Z.json"


def check(value, message):
    if not value:
        raise ValueError(message)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_bytes())


def binding(root, path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return {"path": path.relative_to(Path(root).resolve()).as_posix(), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def bound(root, link):
    path = (Path(root) / link["path"]).resolve()
    check(path.is_relative_to(Path(root).resolve()) and binding(root, path) == {k: link[k] for k in ("path", "bytes", "sha256")}, "Binding mismatch: " + link["path"])
    return path


def write_once(path, data):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")


def required_starts(frame_count, imported_offsets):
    check(type(frame_count) is int and frame_count >= 3, "Need at least three frames")
    check(all(type(i) is int and 0 <= i < frame_count for i in imported_offsets), "Import offset invalid")
    needed = set()
    for i in range(frame_count):
        if i not in imported_offsets:
            needed.update(range(max(0, i - 2), min(i, frame_count - 3) + 1))
    return sorted(needed)


def donor_matches(block, frame, observation, donor_source, donor_observation):
    return (block["source_video"] == donor_source
            and donor_observation["source_frame_index"] == observation["source_frame_index"] == frame["source_frame_index"]
            and donor_observation["source_pts_ticks"] == observation["source_pts_ticks"] == frame["source_pts_ticks"]
            and donor_observation["time_base"] == observation["time_base"] == block["time_base"]
            and donor_observation["source_png"]["sha256"] == frame["png"]["sha256"]
            and donor_observation["source_png"]["rgb_sha256"] == frame["png"]["rgb_sha256"]
            and donor_observation["mean_heatmap_sha256"] == observation["mean_heatmap_sha256"]
            and donor_observation["candidates"] == observation["candidates"])


def capture_means(block, expected, path, provider, imports=None):
    """Exact original ascending float32 arithmetic; provider may be synthetic."""
    import numpy as np
    from . import wasb_resolution as resolution
    imports = imports or {}
    frames = block["frames"]
    check(len(frames) == len(expected), "Native frame census mismatch")
    starts = required_starts(len(frames), imports)
    start_set = set(starts)
    sums, counts, emitted, calls = {}, {}, [], 0
    check(not Path(path).exists(), "Preserve existing map output")
    array = np.lib.format.open_memmap(path, mode="w+", dtype=np.float32, shape=(len(frames), 432, 768))
    segment = {"kind": "training_only_assessment", "source_frame_range_inclusive": block["range_inclusive"]}

    def emit(i):
        if i in imports:
            mean = imports[i]
            count = expected[i]["temporal_contributions"]
        else:
            count = counts.pop(i)
            mean = sums.pop(i) / np.float32(count)
        row = resolution.select_observation(frames[i], mean, count, block, segment)
        check(row == expected[i], "Original training observation/hash mismatch: " + block["block_id"] + ":" + str(frames[i]["source_frame_index"]))
        array[i] = mean
        emitted.append(row)

    try:
        for start in range(len(frames) - 2):
            if start in start_set:
                values = provider(frames[start:start + 3])
                calls += 1
                check(isinstance(values, np.ndarray) and values.dtype == np.float32 and values.shape == (3, 432, 768)
                      and np.isfinite(values).all() and (values >= 0).all() and (values <= 1).all(), "Invalid forward maps")
                for channel in range(3):
                    i = start + channel
                    if i not in imports:
                        if i not in sums:
                            sums[i], counts[i] = np.zeros((432, 768), np.float32), 0
                        sums[i] += values[channel]
                        counts[i] += 1
            emit(start)
        emit(len(frames) - 2)
        emit(len(frames) - 1)
        check(not sums and not counts and calls == len(starts), "Capture contributor/call accounting differs")
        array.flush()
    finally:
        array._mmap.close()
    return emitted, calls


def prepare(root=ROOT):
    """Metadata/byte verification only; imports no Torch or model constructor."""
    root = Path(root).resolve()
    out = root / OUTPUT
    out.mkdir(exist_ok=True)
    check(not (out / "prepared.json").exists(), "Preserve completed preparation")
    old_link = binding(root, root / PREVIOUS_PREP)
    previous, assessment = read(root / PREVIOUS_PREP), read(root / FIT)
    package = read(bound(root, previous["package"]))
    recipe = read(bound(root, previous["recipe"]))
    checkpoint = assessment["identity"]["checkpoint"]
    bound(root, checkpoint)
    for link in package["reference_bindings"]:
        bound(root, link)
    check(package["protected_evaluation_authorized"] is False and len(package["training_blocks"]) == 26, "Original package scope differs")
    caches = {read(bound(root, b))["block_id"]: b for b in previous["training_cache_receipts"]}
    records = {}
    for link in assessment["block_receipts"]:
        receipt = read(bound(root, link))
        record = read(bound(root, receipt["record"]))
        check(receipt["identity"]["checkpoint"] == checkpoint, "Mixed model source")
        records[record["block_id"]] = (receipt["record"], record)
    # Donor inventory is existing, already permitted SAC only. No HOU/DET map access.
    donor_inventory = read(root / "data/outputs/ball_tracking/weak_response_v0_1/inventory.json")
    donor = next(b for b in donor_inventory["blocks"] if b["block_id"] == "sac_mem_q1_c01:540-2010")
    donor_rows = read(bound(root, donor["original_records"]))["observations"]
    donor_by_frame = {r["source_frame_index"]: (i, r) for i, r in enumerate(donor_rows)}
    donor_map_path = bound(root, donor["saved_mean_maps"])
    import numpy as np
    donor_maps = np.load(donor_map_path, mmap_mode="r", allow_pickle=False)
    blocks, counters, by_game = [], Counter(), defaultdict(Counter)
    try:
        for block in package["training_blocks"]:
            bid = block["block_id"]
            check(block["role"] == "training" and all(f.get("state", "permitted") == "permitted" for f in block["frames"]), "Non-training/protected frame")
            cache_link = caches[bid]
            cache = read(bound(root, cache_link))
            image_path = bound(root, cache["warped_frames"])
            images = np.load(image_path, mmap_mode="r", allow_pickle=False)
            try:
                check(images.shape == (len(block["frames"]), 432, 768, 3) and images.dtype == np.uint8, "Input cache shape/dtype")
            finally:
                images._mmap.close()
            record_link, record = records[bid]
            check(record["source_video"] == block["source_video"] and len(record["observations"]) == len(block["frames"]), "Training producer source/census")
            imports = {}
            pool_stats = Counter()
            for i, (frame, obs, verified) in enumerate(zip(block["frames"], record["observations"], cache["verified_frames"], strict=True)):
                check(frame["source_frame_index"] == obs["source_frame_index"] == verified["source_frame_index"]
                      and frame["source_pts_ticks"] == obs["source_pts_ticks"] and obs["time_base"] == block["time_base"]
                      and frame["png"] == obs["source_png"] == verified["source_png"], "Actual producer/cache/PTS join differs")
                kind = frame["kind"]
                pool_stats["frames:" + kind] += 1
                pool_stats["candidates:" + kind] += len(obs["candidates"])
                if kind == "positive":
                    import math
                    for c in obs["candidates"]:
                        d = math.dist([c["center_x"], c["center_y"]], frame["annotation"]["geometry"]["center_xy_px"])
                        pool_stats["eligible:within10" if d <= 10 else "eligible:outside10"] += 1
                        pool_stats["eligible:farther_than10_plus_recorded_uncertainty"] += d > 10 + frame["annotation"]["geometry"]["uncertainty_radius_px"]
                if block["source_video"] == donor["source_video"] and frame["source_frame_index"] in donor_by_frame:
                    j, saved = donor_by_frame[frame["source_frame_index"]]
                    if donor_matches(block, frame, obs, donor["source_video"], saved):
                        check(hashlib.sha256(donor_maps[j].tobytes()).hexdigest() == obs["mean_heatmap_sha256"], "Actual donor mean differs")
                        imports[str(i)] = j
            starts = required_starts(len(block["frames"]), {int(i) for i in imports})
            blocks.append({"block_id": bid, "source_role": block["role"], "domain": block["domain"], "frames": len(block["frames"]),
                           "native_record": record_link, "cache_receipt": cache_link, "warped_frames": cache["warped_frames"],
                           "import_offsets": imports, "required_triplet_start_offsets": starts,
                           "new_forward_calls": len(starts), "saved_strong_pool": dict(pool_stats)})
            counters.update(pool_stats)
            by_game[block["game_id"] or bid].update(pool_stats)
            print(json.dumps({"event": "training_capture_prepared_block", "block": bid, "imports": len(imports), "new_calls": len(starts)}), flush=True)
    finally:
        donor_maps._mmap.close()
    raw_bytes = sum(b["frames"] * 432 * 768 * 4 + 128 for b in blocks)
    check(shutil.disk_usage(out).free >= raw_bytes * 2, "Insufficient practical disk headroom")
    check(sum(b["frames"] for b in blocks) == 3329 and sum(counters["frames:" + k] for k in ("positive", "hidden", "masked")) == 3329, "Training census differs")
    source_names = ["training_response_capture", "wasb_resolution", "weak_response_followup", "weak_response_candidates",
                    "wasb_adapter", "wasb_adapted_adapter", "completion_evaluation", "completion_training_runtime",
                    "continuation_owned_guard", "gpu_supervision"]
    result = {"status": "prepared_no_inference_no_fit", "created_at_utc": stamp(), "prior_preparation": old_link,
              "package": previous["package"], "recipe": previous["recipe"], "checkpoint": checkpoint,
              "assessment": binding(root, root / FIT), "model_config": previous["model_config"],
              "source_roles": package["source_roles"], "cache_root": recipe["cache_root"], "blocks": blocks,
              "strong_pool_census": dict(counters), "strong_pool_by_game": {k: dict(v) for k, v in by_game.items()},
              "donor": {"source_video": donor["source_video"], "record": donor["original_records"], "maps": donor["saved_mean_maps"],
                        "import_policy": "Only actual byte-identical canonical training means/native components; donor/canonical contexts remain separately recorded."},
              "frames": 3329, "maximum_full_pass_calls": 3277, "planned_new_calls": sum(b["new_forward_calls"] for b in blocks),
              "imported_frames": sum(len(b["import_offsets"]) for b in blocks), "raw_map_bytes": raw_bytes,
              "free_disk_bytes_at_preparation": shutil.disk_usage(out).free,
              "source": [binding(root, root / f"src/ball_tracking/{n}.py") for n in source_names],
              "upstream_model_sources": previous["upstream_model_sources"], "constructor_asset": previous["pretrained_constructor_asset"],
              "new_model_calls": 0, "new_training_updates": 0, "new_selector_runs": 0, "new_labels": 0,
              "protected_access": False, "GPU_execution_authorized": False, "training_authorized": False,
              "weak_pool_parameters": {"native": ">.3", "additional": ">.01", "duplicate_radius_source_px": 2, "candidate_cap": None},
              "limits": ["Pool opportunity/correctness is not semantic identity or training success.",
                         "No training images/frames from HOU, DET, TOR or curated evaluation; NFHS replay roles unchanged.",
                         "Exact SAC imports authenticate canonical training values, not a claim of identical donor temporal context.",
                         "No model architecture or training recipe adopted; capture requires separate explicit GPU authorization."]}
    write_once(out / "prepared.json", result)
    return result


def run(root, monitor, arguments):
    root = Path(root).resolve()
    out = root / OUTPUT
    # Authorization and real process ownership precede any ML/runtime import.
    prepared = read(out / "prepared.json")
    approval = read(out / "gpu_approval.json")
    freeze = read(out / "execution_freeze.json")
    check(approval["explicit_GPU_capture_approved"] is True and approval["prepared"] == binding(root, out / "prepared.json")
          and bool(approval["user_statement"].strip()) and approval["training_approved"] is False, "Specific capture authorization required")
    check(freeze["prepared"] == binding(root, out / "prepared.json"), "Prepared inputs differ from freeze")
    for link in freeze["source_and_tests"] + prepared["source"] + prepared["upstream_model_sources"]:
        bound(root, link)
    from .continuation_owned_guard import verify_owned_worker
    ownership = verify_owned_worker(root, root / monitor, MODULE, arguments)
    import numpy as np
    import torch
    from . import completion_evaluation as evaluation
    from . import wasb_resolution as resolution
    from . import weak_response_followup as extraction
    package = read(bound(root, prepared["package"]))
    bound(root, prepared["checkpoint"])
    destination = out / "capture_attempt_001"
    destination.mkdir(exist_ok=False)
    start = time.perf_counter()
    write_once(destination / "started.json", {"at_utc": stamp(), "ownership": ownership, "approval": binding(root, out / "gpu_approval.json"),
                                              "prepared": binding(root, out / "prepared.json")})
    store, donor_maps, adapter = None, None, None
    attempted = returned = 0
    try:
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        store = resolution.FrameStore(root, package, root / prepared["cache_root"])
        store.blocks = {b["block_id"]: b for b in package["training_blocks"]}
        # Existing immutable caches only; never allow implicit cache regeneration.
        for b in prepared["blocks"]:
            bound(root, b["cache_receipt"])
            bound(root, b["warped_frames"])
        store.prepare()
        donor_maps = np.load(bound(root, prepared["donor"]["maps"]), mmap_mode="r", allow_pickle=False)
        adapter = evaluation.make_adapter(root, {"selected_method": {"checkpoint": prepared["checkpoint"],
                   "provenance": {"prepared": binding(root, out / "prepared.json"), "research_control_only": True}}})
        adapter.model.eval().requires_grad_(False)
        before = {k: v.detach().cpu().clone() for k, v in adapter.model.state_dict().items()}
        blocks = {b["block_id"]: b for b in package["training_blocks"]}
        records = []
        with (destination / "forward_journal.jsonl").open("x", encoding="utf-8", buffering=1) as log:
            for item in prepared["blocks"]:
                block = blocks[item["block_id"]]
                expected = read(bound(root, item["native_record"]))["observations"]
                folder = destination / hashlib.sha256(block["block_id"].encode()).hexdigest()[:24]
                folder.mkdir()
                imports = {int(i): donor_maps[j] for i, j in item["import_offsets"].items()}

                def provider(frames):
                    nonlocal attempted, returned
                    check(attempted < prepared["planned_new_calls"], "Frozen call budget exhausted")
                    indices = [f["source_frame_index"] for f in frames]
                    attempted += 1
                    log.write(json.dumps({"event": "attempted", "at_utc": stamp(), "block_id": block["block_id"], "indices": indices, "count": attempted}) + "\n")
                    values = resolution._model_values(adapter.model, adapter.device, store.inputs(block["block_id"], indices), 768, 432)
                    returned += 1
                    log.write(json.dumps({"event": "returned", "at_utc": stamp(), "count": returned}) + "\n")
                    return values

                observations, calls = capture_means(block, expected, folder / "mean_heatmaps.npy", provider, imports)
                check(calls == item["new_forward_calls"], "Per-block call count differs")
                pool_stats = extraction.extract_block(root, block, observations, binding(root, folder / "mean_heatmaps.npy"), folder / "pools.jsonl")
                record = {"block_id": block["block_id"], "original_record": item["native_record"], "native_observations": observations,
                          "calls": calls, "imports": item["import_offsets"], "extraction": pool_stats}
                write_once(folder / "completed.json", record)
                records.append(binding(root, folder / "completed.json"))
                print(json.dumps({"event": "training_response_block_complete", "block": block["block_id"], "calls_returned": returned, "retained_candidates": pool_stats["retained_candidates"]}), flush=True)
        check(attempted == returned == prepared["planned_new_calls"], "Final call count differs")
        check(all(torch.equal(before[k], v.detach().cpu()) for k, v in adapter.model.state_dict().items()), "Model tensors changed")
        result = {"status": "completed_capture_no_fitting", "completed_at_utc": stamp(), "elapsed_seconds": time.perf_counter() - start,
                  "prepared": binding(root, out / "prepared.json"), "records": records, "new_forward_calls_attempted": attempted,
                  "new_forward_calls_returned": returned, "frames": 3329, "model_tensors_unchanged": True,
                  "new_training_updates": 0, "new_selector_runs": 0, "new_labels": 0, "protected_access": False,
                  "extraction_sealed_before_label_assisted_coverage": True, "model_adopted": False}
        write_once(destination / "completed.json", result)
        return result
    except BaseException as error:
        write_once(destination / "failed.json", {"at_utc": stamp(), "elapsed_seconds": time.perf_counter() - start,
             "exception": type(error).__name__, "message": str(error), "traceback": traceback.format_exc(),
             "attempted_calls": attempted, "returned_calls": returned, "automatic_retry": False})
        raise
    finally:
        if donor_maps is not None:
            donor_maps._mmap.close()
        if store is not None:
            store.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--run", action="store_true")
    parser.add_argument("--monitor")
    args = parser.parse_args()
    result = prepare() if args.prepare else run(ROOT, args.monitor, sys.argv[1:])
    print(json.dumps({k: result[k] for k in ("status", "frames", "new_model_calls", "planned_new_calls", "imported_frames") if k in result}), flush=True)


if __name__ == "__main__":
    main()
