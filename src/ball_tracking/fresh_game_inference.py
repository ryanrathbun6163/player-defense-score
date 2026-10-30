"""Supervised fresh-game detector + saved original Q/J inference, without fits.

Import/preflight are metadata-only. CPU preparation exports label-free source
identities and canonical warped RGB caches. The worker seals every detector
mean/pool and an exact Q workload before any Q forward. No labels are consumed
by capture, scoring, fixed-choice materialization, or feature construction.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone, timedelta
from fractions import Fraction
import hashlib
from importlib import metadata
import io as byteio
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import traceback

from . import candidate_acceptance_neural as io

ROOT = Path(__file__).resolve().parents[2]
BASE = "data/outputs/ball_tracking/fresh_game_diagnostic_v0_1"
ACCEPTED = BASE + "/accepted/reference.json"
ACCEPTED_SHA = "a0f37f0a6651ea18d3d09d0be0dd87d3a6f2f390033e1c4367355e6591fee645"
PROTOCOL = "docs/ball_tracking_fresh_game_diagnostic_protocol.md"
PREPARATION = BASE + "/inference_preparation/prepared.json"
INPUTS = BASE + "/inference_preparation/inputs.json"
LAUNCH_BASE = BASE + "/launch_v0_1"
INFERENCE_OUTPUT = BASE + "/attempt_001"
MONITOR = LAUNCH_BASE + "/monitoring/attempt_001"
RESTORATION = LAUNCH_BASE + "/debug_mode_restoration.json"
MODULE = "src.ball_tracking.fresh_game_inference"
OLD_PREP = "data/outputs/ball_tracking/candidate_proposal_coverage_v0_1/preparation/prepared.json"
DETECTOR = "data/outputs/ball_tracking/wasb_continuation_v0_1/cosine/fit_v0_1/checkpoints/epoch_009.pth"
DETECTOR_SHA = "f4b721662ec3d8b546563feffcf5ce0d6319ed8ddc83f398830a0aac5d29c7b9"
Q_BASE = "data/outputs/ball_tracking/candidate_quality_pilot_v0_1/attempt_005/all_nba"
Q_CHECKPOINT = Q_BASE + "/final_trainable.pth"
Q_SHA = "1bb7b3b5046652fbd7160d69bba5e3ab9e2fb3ebdd15b348ecf9db001bb98bb4"
J_MODEL = "data/outputs/ball_tracking/candidate_acceptance_gate_v0_1/attempt_001/analysis/fits/final_all_NBA_J.json"
J_SHA = "f98eaeb271d4960daf03bcdd09da65440e2fab43759b8e338677578f17330c77"
CLIPS, GAME, ROLE = ("122", "237", "365"), "0022400861", "diagnostic_development"
WIDTH, HEIGHT, BATCH_SIZE = 768, 432, 32
MAX_TOTAL_SECONDS, CLEANUP_RESERVE_SECONDS = 1800, 30
MAX_ARTIFACT_BYTES = 8 * 1024**3
GPU = io.GPU
RUNTIME = {**io.RUNTIME, "opencv-python": "5.0.0.93", "scipy": "1.17.1", "PyYAML": "6.0.3"}
COUNTS = {"blocks": 3, "frames": 360, "detector_forwards": 354, "Q_batch_size": 32,
          "Q_forwards": "ceil(K_in_bounds_retained_candidates/32)", "Q_budget_sealed_before_Q": True,
          "J_predictions": "K_in_bounds_retained_candidates", "parity_forwards": 0,
          "optimizer_updates": 0, "CPU_gate_fits": 0, "new_labels": 0}
REQUIRED_IMPLEMENTATION = {f"src/ball_tracking/{name}.py" for name in (
    "fresh_game_inference", "candidate_acceptance_neural", "candidate_acceptance_features",
    "candidate_quality_model", "candidate_quality_data", "candidate_quality_pilot", "candidate_quality_native_cable_resume",
    "candidate_producer_transfer_experiment", "candidate_proposal_coverage_capture",
    "training_response_capture", "wasb_resolution", "weak_response_followup", "weak_response_candidates",
    "wasb_adapter", "wasb_adapted_adapter", "wasb_training", "wasb_augmentation", "wasb_experiment",
    "annotations", "completion_training_runtime", "continuation_owned_guard",
    "gpu_supervision", "nba_appearance_feature_screen", "point_feature_inference")}
REQUIRED_IMPLEMENTATION.add("tests/test_fresh_game_inference.py")
FRAME_FIELDS = {"frame_key", "source_frame_index", "source_pts_ticks", "duration_ticks", "png"}
BLOCK_FIELDS = {"block_id", "clip_id", "game_id", "domain", "role", "source_video", "time_base", "range_inclusive", "frames"}
check, read, write_once, append, stamp, binding = io.check, io.read, io.write_once, io.append, io.stamp, io.binding


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def bound(root, link):
    minimal = {k: link[k] for k in ("path", "bytes", "sha256")}
    return io.bound(root, minimal)


def write_lines(path, rows):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def validate_block(block):
    check(set(block) == BLOCK_FIELDS and block["clip_id"] in CLIPS and block["game_id"] == GAME
          and block["domain"] == "nba" and block["role"] == ROLE
          and block["block_id"] == f"bkn_det_{GAME}_c{block['clip_id']}", "Unexpected source-only diagnostic block")
    frames = block["frames"]
    check(len(frames) >= 3 and all(set(f) == FRAME_FIELDS for f in frames), "Input frames contain unexpected fields or short context")
    indices = [f["source_frame_index"] for f in frames]
    check(all(type(i) is int for i in indices) and indices == list(range(indices[0], indices[-1] + 1))
          and block["range_inclusive"] == [indices[0], indices[-1]], "Native frame range/order differs")
    unit = Fraction(block["time_base"])
    check(unit > 0 and all(type(f["source_pts_ticks"]) is int and type(f["duration_ticks"]) is int
          and f["duration_ticks"] * unit == Fraction(1, 60)
          and f["frame_key"] == block["block_id"] + ":" + str(f["source_frame_index"]) for f in frames), "Native PTS/frame identity differs")
    check(all(b["source_pts_ticks"] - a["source_pts_ticks"] == a["duration_ticks"] for a, b in zip(frames, frames[1:])), "Native PTS are not contiguous")
    source = block["source_video"]
    check(set(source) == {"path", "bytes", "sha256", "width_px", "height_px"}
          and (source["width_px"], source["height_px"]) == (1280, 720), "Fixed native dimensions/source schema differ")
    for f in frames:
        check(set(f["png"]) == {"path", "bytes", "sha256", "rgb_sha256"}, "PNG identity schema differs")


def validate_inputs(inputs):
    check(set(inputs) == {"schema_version", "blocks"} and inputs["schema_version"] == "fresh_game_label_free_inputs/v0.1", "Input manifest schema differs")
    check([b["clip_id"] for b in inputs["blocks"]] == list(CLIPS), "Fixed clip order/scope differs")
    sources, frames = set(), set()
    for block in inputs["blocks"]:
        validate_block(block)
        check(len(block["frames"]) == 120 and block["range_inclusive"] == [0, 119]
              and block["frames"][0]["source_pts_ticks"] == 0
              and (block["frames"][-1]["source_pts_ticks"] + block["frames"][-1]["duration_ticks"]) * Fraction(block["time_base"]) == 2,
              "Selected native [0,2) window differs")
        check(block["source_video"]["sha256"] not in sources, "Repeated source clip")
        sources.add(block["source_video"]["sha256"])
        for frame in block["frames"]:
            check(frame["frame_key"] not in frames, "Repeated source frame")
            frames.add(frame["frame_key"])
    check(len(frames) == 360 and sum(len(b["frames"]) - 2 for b in inputs["blocks"]) == 354, "Exact source census differs")


def canonical_affine(source_width, source_height):
    """Exact float32 control points from wasb_resolution.affine_matrices, CPU-only."""
    import cv2
    import numpy as np
    center = np.array([source_width / 2., source_height / 2.], dtype=np.float32)
    scale = np.float32(max(source_width, source_height))
    src, dst = np.zeros((3, 2), np.float32), np.zeros((3, 2), np.float32)
    src[0], src[1] = center, center + np.array([0, scale * -.5])
    dst[0] = [WIDTH * .5, HEIGHT * .5]
    dst[1] = dst[0] + np.array([0, WIDTH * -.5], np.float32)
    for points in (src, dst):
        direct = points[0] - points[1]
        points[2] = points[1] + np.array([-direct[1], direct[0]], np.float32)
    return cv2.getAffineTransform(src, dst)


def prepare(root=ROOT, accepted_manifest_path=ACCEPTED):
    """One exclusive CPU PNG decode/cache preparation; no Torch or model calls."""
    root = Path(root).resolve()
    check("torch" not in sys.modules and str(accepted_manifest_path).replace("\\", "/") == ACCEPTED, "Only the fixed accepted publication may be prepared")
    accepted_binding = binding(root, root / ACCEPTED)
    check(accepted_binding["sha256"] == ACCEPTED_SHA, "Accepted reference publication changed")
    accepted = read(root / ACCEPTED)
    check(accepted["schema_version"] == "fresh_game_accepted_reference/v0.1" and accepted["status"] == "human_accepted_AI_reference"
          and accepted["game_id"] == GAME and accepted["role"] == ROLE
          and accepted["training_eligible"] is accepted["checkpoint_selection_eligible"] is False, "Accepted source role/eligibility differs")
    acceptance = read(bound(root, accepted["acceptance"]))
    check(acceptance["status"] == "human_accepted_AI_reference" and acceptance["accepted_frames"] == 360
          and acceptance["role"] == ROLE and isinstance(acceptance["user_statement"], str) and acceptance["user_statement"].strip(), "Human reference acceptance required")
    check([c["clip_id"] for c in accepted["clips"]] == list(CLIPS) and len(accepted["frames"]) == 360, "Accepted clip/frame census differs")
    blocks = []
    for clip in accepted["clips"]:
        meta, cid = clip["source_metadata"], clip["clip_id"]
        frames = [f for f in accepted["frames"] if f["clip_id"] == cid]
        check(Fraction(meta["average_rate"]) == 60 and all(f["native_time_base"] == meta["time_base"] for f in frames), "Accepted source cadence differs")
        blocks.append({"block_id": f"bkn_det_{GAME}_c{cid}", "clip_id": cid, "game_id": GAME, "domain": "nba", "role": ROLE,
            "source_video": {**clip["source_video"], "width_px": meta["width"], "height_px": meta["height"]},
            "time_base": meta["time_base"], "range_inclusive": [0, 119], "frames": [{
                "frame_key": f["frame_key"], "source_frame_index": f["source_frame_index"], "source_pts_ticks": f["native_pts_ticks"],
                "duration_ticks": f["native_duration_ticks"], "png": f["source_png"]} for f in frames]})
    inputs = {"schema_version": "fresh_game_label_free_inputs/v0.1", "blocks": blocks}
    validate_inputs(inputs)
    old = read(root / OLD_PREP)
    links = {}
    def add(link):
        actual = binding(root, bound(root, link))
        check(link["path"] not in links or links[link["path"]] == actual, "Conflicting input bindings")
        links[link["path"]] = actual
        return actual
    add(accepted_binding)
    for link in (accepted["acceptance"], accepted["selection"], accepted["source_pixel_audit"],
                 old["constructor_asset"], old["model_config"], *old["upstream_model_sources"]):
        add(link)
    from . import candidate_quality_model as model_api
    model_api.local_contract(root)
    for path in (*model_api.PINS, Q_BASE + "/final_tensor_fingerprints.json"):
        add(binding(root, root / path))
    models = {}
    for name, path, sha in (("detector", DETECTOR, DETECTOR_SHA), ("Q", Q_CHECKPOINT, Q_SHA), ("J", J_MODEL, J_SHA)):
        link = binding(root, root / path)
        check(link["sha256"] == sha, "Saved control checkpoint differs: " + name)
        models[name] = add(link)
    output = root / Path(PREPARATION).parent
    check(not output.exists(), "Preserve existing CPU preparation; no automatic retry")
    check(shutil.disk_usage(root).free > MAX_ARTIFACT_BYTES, "Insufficient preparation/output disk headroom")
    output.mkdir(parents=True, exist_ok=False)
    write_once(output / "started.json", {"accepted_reference": accepted_binding, "new_model_calls": 0})
    try:
        import cv2
        import numpy as np
        from PIL import Image
        caches = []
        for block in blocks:
            add(block["source_video"])
            folder = output / block["clip_id"]
            folder.mkdir()
            path = folder / "warped_frames.npy"
            array = np.lib.format.open_memmap(path, mode="w+", dtype=np.uint8, shape=(120, HEIGHT, WIDTH, 3))
            matrix = canonical_affine(1280, 720)
            verified = []
            try:
                for offset, frame in enumerate(block["frames"]):
                    add(frame["png"])
                    with Image.open(root / frame["png"]["path"]) as image:
                        check(image.mode == "RGB" and image.size == (1280, 720), "Canonical PNG mode/dimensions differ")
                        rgb = np.asarray(image).copy()
                    check(hashlib.sha256(rgb.tobytes()).hexdigest() == frame["png"]["rgb_sha256"], "Canonical native RGB hash differs")
                    warped = cv2.warpAffine(rgb, matrix, (WIDTH, HEIGHT), flags=cv2.INTER_LINEAR)
                    array[offset] = warped
                    verified.append({"frame_key": frame["frame_key"], "source_png": frame["png"],
                                     "warped_rgb_sha256": hashlib.sha256(warped.tobytes()).hexdigest()})
                array.flush()
            finally:
                array._mmap.close()
            cache = {"block_id": block["block_id"], "clip_id": block["clip_id"], "block_sha256": canonical(block),
                     "warped_frames": add(binding(root, path)), "source_to_heatmap": matrix.tolist(), "verified_frames": verified,
                     "source_png_decodes": 120, "source_video_decodes": 0, "model_calls": 0}
            write_once(folder / "receipt.json", cache)
            caches.append({"clip_id": block["clip_id"], "cache_receipt": add(binding(root, folder / "receipt.json")),
                           "warped_frames": cache["warped_frames"]})
        write_once(root / INPUTS, inputs)
        add(binding(root, root / INPUTS))
        result = {"status": "prepared_label_free_CPU_inputs_no_model_calls", "at_utc": stamp(), "counts": COUNTS,
            "protocol": binding(root, root / PROTOCOL), "accepted_reference": accepted_binding,
            "acceptance": accepted["acceptance"], "selection": accepted["selection"], "inputs": binding(root, root / INPUTS),
            "source_root": old["source_root"], "constructor_asset": old["constructor_asset"], "models": models,
            "Q_final_fingerprints": links[Q_BASE + "/final_tensor_fingerprints.json"], "blocks": caches,
            "input_bindings": list(links.values()), "source": [binding(root, root / p) for p in sorted(REQUIRED_IMPLEMENTATION)],
            "runtime": RUNTIME, "source_png_decodes": 360, "new_model_calls": 0, "training_updates": 0,
            "raw_mean_payload_bytes": 360 * WIDTH * HEIGHT * 4, "artifact_stop_bytes": MAX_ARTIFACT_BYTES,
            "label_free_runtime_inputs": True, "automatic_retry": False,
            "reduction_audit_scope": "Saved mean hashes, every contributor identity/count and per-channel digests; raw forward channels discarded, so no post-run numerical recomputation from raw channels."}
        check("torch" not in sys.modules, "CPU preparation imported Torch")
        write_once(root / PREPARATION, result)
        return result
    except BaseException as error:
        write_once(output / "failed.json", {"error": type(error).__name__, "message": str(error), "traceback": traceback.format_exc(), "automatic_retry": False})
        raise


def verify_prepared(root):
    prepared = read(root / PREPARATION)
    check(prepared["status"] == "prepared_label_free_CPU_inputs_no_model_calls" and prepared["counts"] == COUNTS
          and prepared["accepted_reference"]["sha256"] == ACCEPTED_SHA and prepared["label_free_runtime_inputs"] is True,
          "Prepared scope/accepted source differs")
    for link in [prepared["protocol"], *prepared["input_bindings"], *prepared["source"]]:
        bound(root, link)
    check({b["path"] for b in prepared["source"]} == REQUIRED_IMPLEMENTATION and prepared["runtime"] == RUNTIME, "Prepared implementation/runtime differs")
    for name, version in RUNTIME.items():
        check(metadata.version(name) == version, "Runtime version differs: " + name)
    inputs = read(bound(root, prepared["inputs"]))
    validate_inputs(inputs)
    from .candidate_proposal_coverage_capture import file_header
    for block, cache in zip(inputs["blocks"], prepared["blocks"], strict=True):
        check(cache["clip_id"] == block["clip_id"], "Cache order differs")
        receipt = read(bound(root, cache["cache_receipt"]))
        check(receipt["block_sha256"] == canonical(block) and receipt["warped_frames"] == cache["warped_frames"]
              and [r["source_png"] for r in receipt["verified_frames"]] == [f["png"] for f in block["frames"]], "Cache source identity differs")
        header = file_header(bound(root, cache["warped_frames"]))
        check(header["shape"] == (120, HEIGHT, WIDTH, 3) and header["descr"] == "|u1" and header["fortran_order"] is False
              and cache["warped_frames"]["bytes"] == 120 * HEIGHT * WIDTH * 3 + header["header_bytes"], "Warped cache array layout differs")
    return prepared, inputs


def validate_authorization(auth, freeze_binding, protocol):
    check(auth.get("execution_approved") is True and auth.get("execution_freeze") == freeze_binding
          and auth.get("protocol") == protocol and auth.get("scope") == COUNTS and auth.get("max_total_seconds") == MAX_TOTAL_SECONDS
          and isinstance(auth.get("user_statement"), str) and auth["user_statement"].strip(), "Exact inference authorization required")
    check(all(auth.get(k) is False for k in ("automatic_retry", "automatic_extension", "protected_access_approved", "new_labels_approved", "training_approved", "selector_approved")), "Authorization exceeds inference scope")


def validate_readiness(root, readiness, freeze_binding, authorization_binding, now=None):
    """Allow only the explicitly documented restoration of standing Debug ON."""
    link = readiness.get("debug_mode_restoration")
    check(isinstance(link, dict) and link.get("path") == RESTORATION and link in readiness.get("sources", []), "Bound Debug Mode restoration missing")
    restoration = read(bound(root, link))
    check(restoration.get("setting") == "NVIDIA Debug Mode"
          and restoration.get("before") == "Off, gray toggle left observed via NVIDIA App System Advanced screenshot"
          and restoration.get("after") == "On, green toggle right and accessibility Debug Mode Toggle switch On"
          and restoration.get("action") == "Restored Off to On with one toggle action"
          and restoration.get("settings_changed") is True and restoration.get("no_other_settings_changed") is True
          and restoration.get("authority") == "Standing project instruction to keep Debug Mode ON; ordinary restoration of successful prior setup",
          "Only the exact standing Debug OFF-to-ON restoration is permitted")
    ui_link = readiness.get("debug_mode_ui_observation")
    check(isinstance(ui_link, dict) and ui_link in readiness["sources"], "Current observed UI receipt missing")
    ui = read(bound(root, ui_link))
    times = [datetime.fromisoformat(v) for v in (restoration["at_utc"], ui["at_utc"], readiness["at_utc"])]
    check(all(t.tzinfo is not None and t.utcoffset() == timedelta(0) for t in times) and times[0] <= times[1] <= times[2]
          and (times[2] - times[1]).total_seconds() <= 120 and ui.get("debug_mode_enabled") is True
          and ui.get("restoration_receipt") == link and ui.get("settings_changed") is True, "Debug restoration/current UI timing or observed state differs")
    check(readiness.get("configuration_changes") == ["NVIDIA Debug Mode"] and readiness.get("settings_changed") is True
          and readiness.get("settings_changed_by_agent") is True and readiness.get("unexpected_setting_changes") == [], "Undeclared settings changes")
    normalized = dict(readiness, configuration_changes=[], settings_changed=False, settings_changed_by_agent=False)
    io.validate_readiness(normalized, freeze_binding, authorization_binding, now)


def preflight(root=ROOT, require_approval=False):
    root = Path(root).resolve()
    check("torch" not in sys.modules, "Preflight must precede Torch import")
    prepared, _ = verify_prepared(root)
    freeze_file = root / LAUNCH_BASE / "execution_freeze.json"
    freeze = read(freeze_file)
    check(freeze.get("status") == "frozen_for_authorized_execution" and freeze.get("scope") == COUNTS
          and freeze.get("prepared") == binding(root, root / PREPARATION)
          and freeze.get("protocol") == prepared["protocol"] == binding(root, root / PROTOCOL)
          and freeze.get("launch_base") == LAUNCH_BASE and freeze.get("inference_output") == INFERENCE_OUTPUT,
          "Frozen scope, protocol or destination differs")
    check(not (root / INFERENCE_OUTPUT).exists(), "Preserve existing attempt; retry/resume is not authorized")
    implementation, inputs = freeze.get("implementation", []), freeze.get("inputs", [])
    check(REQUIRED_IMPLEMENTATION <= {b["path"] for b in implementation}, "Implementation freeze coverage incomplete")
    index = {b["path"]: b for b in inputs}
    check(len(index) == len(inputs) and all(index.get(b["path"]) == b for b in prepared["input_bindings"])
          and index.get(PREPARATION) == freeze["prepared"] and index.get(RESTORATION) == binding(root, root / RESTORATION), "Input/restoration freeze coverage differs")
    check(isinstance(freeze.get("review"), list) and freeze["review"], "Independent review missing")
    for link in [*implementation, *inputs, freeze["focused_tests"], *freeze["review"]]:
        bound(root, link)
    options = {"cwd": root, "text": True, "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    check(subprocess.check_output(["git", "branch", "--show-current"], **options).strip() == "codex/ball-detector-baseline"
          and subprocess.check_output(["git", "rev-parse", "HEAD"], **options).strip() == "8c040fca385dd8fffa0d7a13c45c53e79950bae1"
          and not subprocess.check_output(["git", "diff", "--cached", "--name-only"], **options).strip(), "Git identity/index changed")
    check(shutil.disk_usage(root).free > MAX_ARTIFACT_BYTES, "Current output disk headroom insufficient")
    if require_approval:
        auth_file = root / LAUNCH_BASE / "execution_authorization.json"
        freeze_binding = binding(root, freeze_file)
        validate_authorization(read(auth_file), freeze_binding, freeze["protocol"])
        readiness = read(root / LAUNCH_BASE / "launch_readiness.json")
        validate_readiness(root, readiness, freeze_binding, binding(root, auth_file))
        for link in readiness["sources"]:
            bound(root, link)
    check("torch" not in sys.modules, "Preflight imported Torch")
    return prepared, freeze


def validate_policy(policy):
    check(policy.get("module") == MODULE and policy.get("arguments") == ["--run", "--monitor", MONITOR]
          and policy.get("sample_seconds") == 2 and policy.get("temperature_stop_C") == 80
          and policy.get("telemetry_timeout_seconds") == 5 and policy.get("grace_seconds") == 10
          and policy.get("automatic_retry") is False and policy.get("max_total_seconds") == MAX_TOTAL_SECONDS
          and policy.get("soft_stop_seconds") == MAX_TOTAL_SECONDS - CLEANUP_RESERVE_SECONDS
          and policy.get("gpu_uuid") == GPU, "Owned supervisor policy differs")


def remaining_seconds(policy, now=None):
    now = now or datetime.now(timezone.utc)
    created = datetime.fromisoformat(policy["created_at_utc"])
    check(created.tzinfo is not None and created.utcoffset() == timedelta(0), "UTC owned deadline required")
    elapsed = (now - created).total_seconds()
    check(math.isfinite(elapsed) and elapsed >= -2 and MAX_TOTAL_SECONDS - elapsed > CLEANUP_RESERVE_SECONDS, "Owned wall deadline reached or future dated")
    return MAX_TOTAL_SECONDS - elapsed


def capture_block(root, block, destination, provider):
    """Label-free reducer/extractor, independently synthetic-testable."""
    import numpy as np
    from . import wasb_resolution as resolution
    from . import weak_response_followup as extraction
    validate_block(block)
    destination.mkdir(parents=True, exist_ok=False)
    path, ledger = destination / "mean_heatmaps.npy", destination / "contributor_ledger.jsonl"
    frames, native, channels, calls = block["frames"], [], {}, 0
    means = np.lib.format.open_memmap(path, mode="w+", dtype=np.float32, shape=(len(frames), HEIGHT, WIDTH))
    def wrapped(selected):
        nonlocal calls
        start = selected[0]["source_frame_index"] - frames[0]["source_frame_index"]
        check(start == calls, "Triplet cadence/order differs")
        values = provider(selected)
        check(isinstance(values, np.ndarray) and values.dtype == np.float32 and values.shape == (3, HEIGHT, WIDTH)
              and np.isfinite(values).all() and (values >= 0).all() and (values <= 1).all(), "Invalid triplet response maps")
        for channel in range(3):
            channels[(start, channel)] = {"triplet_start_offset": start, "triplet_source_frame_indices": [f["source_frame_index"] for f in selected],
                "channel": channel, "channel_sha256": hashlib.sha256(values[channel].tobytes()).hexdigest()}
        calls += 1
        return values
    try:
        for offset, (frame, mean, count) in enumerate(resolution.stream_means(frames, wrapped)):
            starts = range(max(0, offset - 2), min(offset, len(frames) - 3) + 1)
            contributors = [channels.pop((s, offset - s)) for s in starts]
            check(mean is not None and count == len(contributors), "Mean/contributor accounting differs")
            row = resolution.select_observation(frame, mean, count, block,
                {"kind": ROLE, "source_frame_range_inclusive": block["range_inclusive"]})
            means[offset] = mean
            native.append(row)
            append(ledger, {"frame_key": frame["frame_key"], "offset": offset, "source_frame_index": frame["source_frame_index"],
                "source_pts_ticks": frame["source_pts_ticks"], "contributors": contributors, "count": count,
                "mean_heatmap_sha256": row["mean_heatmap_sha256"], "minimum": float(mean.min()), "maximum": float(mean.max())})
        check(not channels and calls == len(frames) - 2 and len(native) == len(frames), "Capture block accounting differs")
        means.flush()
    finally:
        means._mmap.close()
    extracted = extraction.extract_block(root, block, native, binding(root, path), destination / "pools.jsonl")
    record = {"block_id": block["block_id"], "clip_id": block["clip_id"], "game_id": GAME, "role": ROLE,
        "source_video": block["source_video"], "native_observations": native, "calls": calls, "extraction": extracted,
        "contributor_ledger": binding(root, ledger), "input_block_sha256": canonical(block), "labels_used": False,
        "raw_forward_channels_retained": False}
    write_once(destination / "completed.json", record)
    return record


def pool_rows(block, record, saved_pool_rows):
    from .candidate_quality_data import stable_id
    frames, candidates = [], []
    check(len(saved_pool_rows) == len(block["frames"]) == len(record["native_observations"]), "Pool/native frame census differs")
    for frame, observation, pool in zip(block["frames"], record["native_observations"], saved_pool_rows, strict=True):
        check(pool["block_id"] == block["block_id"] and pool["source_frame_index"] == observation["source_frame_index"] == frame["source_frame_index"]
              and pool["source_pts_ticks"] == observation["source_pts_ticks"] == frame["source_pts_ticks"]
              and pool["mean_heatmap_sha256"] == observation["mean_heatmap_sha256"] and observation["source_png"] == frame["png"]
              and pool["time_base"] == observation["time_base"] == block["time_base"], "Candidate source transport differs")
        native_count = len(observation["candidates"])
        check(pool["diagnostic"]["native_parity"] is True and pool["diagnostic"]["labels_used"] is False
              and pool["diagnostic"]["native_count"] == native_count and pool["diagnostic"]["pool_count"] == len(pool["candidates"]), "Extraction parity/census differs")
        source = block["source_video"]
        frame_id = stable_id("frame_", [source["sha256"], block["block_id"], frame["source_frame_index"], frame["source_pts_ticks"], block["time_base"]])
        common = {"frame_key": frame["frame_key"], "frame_id": frame_id, "clip_id": block["clip_id"], "block_id": block["block_id"],
            "game_id": GAME, "source_frame_index": frame["source_frame_index"], "source_pts_ticks": frame["source_pts_ticks"],
            "time_base": block["time_base"], "source_video_sha256": source["sha256"], "source_png": frame["png"]}
        own = []
        for index, candidate in enumerate(pool["candidates"]):
            check(candidate["candidate_index"] == index, "Candidate extraction order differs")
            native = index < native_count
            if native:
                check(all(candidate[k] == v for k, v in observation["candidates"][index].items()), "Native prefix changed")
            check(candidate["extraction"] == ("native_component" if native else "threshold_component")
                  and candidate["threshold"] == (.3 if native else .01), "Candidate origin/threshold differs")
            x, y = candidate["center_x"], candidate["center_y"]
            check(type(x) in (int, float) and type(y) in (int, float) and math.isfinite(x) and math.isfinite(y), "Invalid source point")
            inside = 0 <= x < source["width_px"] and 0 <= y < source["height_px"]
            check(candidate["in_source_bounds"] is inside, "Source bounds changed")
            left, top = math.floor(x) - 32, math.floor(y) - 32
            intersection = max(0, min(left + 64, source["width_px"]) - max(left, 0)) * max(0, min(top + 64, source["height_px"]) - max(top, 0))
            identity = stable_id("candidate_", [frame_id, record["extraction"]["pools"]["sha256"], index])
            row = {**common, "candidate_id": identity, "candidate_index": index, "center_xy_px": [x, y],
                "width_px": source["width_px"], "height_px": source["height_px"], "in_source_bounds": inside,
                "native_or_weak": "native" if native else "weak", "native_score": candidate["native_score"],
                "component_pixels": candidate["component_pixels"], "padding_pixels": 4096 - intersection,
                "selected_native": index == observation["selected_candidate_index"], "producer_candidate": candidate}
            own.append(row)
        selected = [r["candidate_id"] for r in own if r["selected_native"]]
        check(len(selected) <= 1, "Multiple native selections")
        frames.append({**common, "duration_ticks": frame["duration_ticks"], "pool_binding": record["extraction"]["pools"],
            "mean_heatmap_sha256": pool["mean_heatmap_sha256"], "candidate_ids": [r["candidate_id"] for r in own],
            "native_selected_candidate_id": selected[0] if selected else None,
            "native_state": observation["state"], "temporal_contributions": observation["temporal_contributions"]})
        candidates.extend(own)
    return frames, candidates


def q_budget(candidates):
    ids = [r["candidate_id"] for r in candidates if r["in_source_bounds"]]
    check(len({r["candidate_id"] for r in candidates}) == len(candidates), "Duplicate retained identity")
    return {"status": "sealed_complete_candidate_workload_before_Q", "ordered_candidate_ids": ids,
        "ordered_ids_sha256": canonical(ids), "K": len(ids), "batch_size": BATCH_SIZE,
        "Q_forwards": math.ceil(len(ids) / BATCH_SIZE), "J_predictions": len(ids),
        "all_retained_candidates": len(candidates), "out_of_source_bounds": len(candidates) - len(ids),
        "candidate_cap": None, "threshold_selection": None, "labels_used": False, "parity_forwards": 0}


def fixed_choices(frames, candidates, logits):
    by_id = {r["candidate_id"]: r for r in candidates}
    check(set(logits) == {r["candidate_id"] for r in candidates if r["in_source_bounds"]}, "Q coverage differs")
    check(all(type(v) in (int, float) and math.isfinite(v) for v in logits.values()), "Q logits must be finite scalars")
    output = []
    for frame in frames:
        check(all(k in by_id and by_id[k]["frame_key"] == frame["frame_key"] for k in frame["candidate_ids"]), "Fixed pool membership differs")
        ordered = sorted((k for k in frame["candidate_ids"] if k in logits), key=lambda k: (-logits[k], k))
        output.append({**frame, "quality_top_candidate_id": ordered[0] if ordered else None,
            "quality_top_tied_candidate_ids": [k for k in ordered if logits[k] == logits[ordered[0]]] if ordered else [],
            "point_chosen_before_acceptance": True, "fallback_allowed": False})
    return output


def start_call(counters, kind, limit, journal, details):
    check(kind in ("detector", "Q") and counters[kind + "_attempted"] < limit, "Exact forward budget exhausted")
    counters[kind + "_attempted"] += 1
    append(journal, {"event": kind + "_attempted", **details, "counters": dict(counters)})


def validate_counters(counters, budget):
    check(counters == {"detector_attempted": 354, "detector_returned": 354, "means": 360,
        "Q_attempted": budget["Q_forwards"], "Q_returned": budget["Q_forwards"], "Q_presentations": budget["K"],
        "J_predictions": budget["K"], "optimizer_updates": 0}, "Final exact workload accounting differs")


def run(root, monitor, arguments):
    root = Path(root).resolve()
    check(monitor == MONITOR and list(arguments) == ["--run", "--monitor", MONITOR], "Exact owned invocation required")
    prepared, freeze = preflight(root, require_approval=True)
    from .continuation_owned_guard import verify_owned_worker
    ownership = verify_owned_worker(root, root / monitor, MODULE, arguments)
    policy = read(root / monitor / "policy.json")
    validate_policy(policy)
    remaining = remaining_seconds(policy)
    from .candidate_quality_native_cable_resume import verify_runtime_driver
    driver = verify_runtime_driver(GPU)
    out = root / INFERENCE_OUTPUT
    out.mkdir(parents=True, exist_ok=False)
    began, done, array, crop_cache = time.monotonic(), threading.Event(), None, None
    counters = dict.fromkeys(("detector_attempted", "detector_returned", "means", "Q_attempted", "Q_returned", "Q_presentations", "J_predictions", "optimizer_updates"), 0)
    write_once(out / "started.json", {"at_utc": stamp(), "ownership": ownership, "driver": driver,
        "prepared": binding(root, root / PREPARATION), "accepted_reference": prepared["accepted_reference"],
        "execution_freeze": binding(root, root / LAUNCH_BASE / "execution_freeze.json"),
        "execution_authorization": binding(root, root / LAUNCH_BASE / "execution_authorization.json"),
        "launch_readiness": binding(root, root / LAUNCH_BASE / "launch_readiness.json"), "settings_changed_by_worker": False})
    def continuing():
        check(not (root / monitor / "STOP").exists(), "Owned supervisor requested STOP")
        remaining_seconds(policy)
    def watchdog():
        stop_at = time.monotonic() + max(0, remaining - CLEANUP_RESERVE_SECONDS)
        while not done.wait(2):
            try:
                reason = ("soft_wall_deadline" if time.monotonic() >= stop_at else
                    "artifact_byte_ceiling" if sum(p.stat().st_size for p in out.rglob("*") if p.is_file()) > MAX_ARTIFACT_BYTES else
                    "disk_free_below_512MiB" if shutil.disk_usage(out).free < 512 * 1024**2 else None)
            except Exception as error:
                reason = "storage_watchdog_failure:" + str(error)
            if reason:
                (root / monitor / "STOP").touch(exist_ok=True)
                write_once(out / "operational_stop.json", {"reason": reason, "automatic_retry": False})
                return
    threading.Thread(target=watchdog, daemon=True).start()
    try:
        continuing()
        check("torch" not in sys.modules, "Torch imported before approved runtime")
        os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
        import numpy as np
        import torch
        from types import SimpleNamespace
        from . import wasb_resolution as resolution
        from .wasb_adapted_adapter import AdaptedWasbAdapter
        torch.set_num_threads(4)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        # Match the current detector's saved response-capture runtime. Q has
        # its own stricter precision policy, applied only after this stage.
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = True
        torch.use_deterministic_algorithms(False)
        inputs = read(root / INPUTS)
        adapter = AdaptedWasbAdapter(root / prepared["source_root"], bound(root, prepared["constructor_asset"]),
            bound(root, prepared["models"]["detector"]), DETECTOR_SHA, {"fresh_game_preparation": binding(root, root / PREPARATION)}, device="cuda")
        adapter.model.eval().requires_grad_(False)
        before = {k: v.detach().cpu().clone() for k, v in adapter.model.state_dict().items()}
        records, frame_rows, candidates = [], [], []
        journal = out / "forward_journal.jsonl"
        for block, cache in zip(inputs["blocks"], prepared["blocks"], strict=True):
            continuing()
            array = np.load(root / cache["warped_frames"]["path"], mmap_mode="r", allow_pickle=False)
            check(not array.flags.writeable and array.dtype == np.uint8 and array.shape == (120, HEIGHT, WIDTH, 3), "Read-only warped cache differs")
            bid = block["block_id"]
            store = SimpleNamespace(arrays={bid: array}, positions={bid: {f["source_frame_index"]: i for i, f in enumerate(block["frames"])}})
            def provider(frames):
                continuing()
                indices = [f["source_frame_index"] for f in frames]
                details = {"clip_id": block["clip_id"], "source_frame_indices": indices}
                start_call(counters, "detector", 354, journal, details)
                values = resolution._model_values(adapter.model, adapter.device, resolution.FrameStore.inputs(store, bid, indices), WIDTH, HEIGHT)
                counters["detector_returned"] += 1
                append(journal, {"event": "detector_returned", **details, "triplet_sha256": hashlib.sha256(values.tobytes()).hexdigest(), "counters": dict(counters)})
                return values
            folder = out / "capture" / block["clip_id"]
            record = capture_block(root, block, folder, provider)
            array._mmap.close(); array = None
            counters["means"] += 120
            records.append(binding(root, folder / "completed.json"))
            own_frames, own_candidates = pool_rows(block, record, io.rows(root / record["extraction"]["pools"]["path"]))
            frame_rows.extend(own_frames); candidates.extend(own_candidates)
            append(out / "block_journal.jsonl", {"record": records[-1], "counters": dict(counters)})
            print(json.dumps({"event": "fresh_detector_block_complete", "clip_id": block["clip_id"], "candidates": len(own_candidates), "counters": counters}), flush=True)
        check(counters["detector_attempted"] == counters["detector_returned"] == 354 and counters["means"] == 360, "Detector stage incomplete")
        check(all(torch.equal(before[k], v.detach().cpu()) for k, v in adapter.model.state_dict().items()), "Detector inference changed tensors")
        del adapter, before, store
        torch.cuda.empty_cache()
        write_lines(out / "candidates.jsonl", candidates)
        capture_complete = {"status": "sealed_label_free_detector_capture", "records": records,
            "accepted_reference": prepared["accepted_reference"], "inputs": prepared["inputs"], "detector_checkpoint": prepared["models"]["detector"],
            "counters": dict(counters), "candidates": binding(root, out / "candidates.jsonl"), "labels_used": False,
            "model_tensors_unchanged": True, "reduction_audit_scope": prepared["reduction_audit_scope"],
            "precision": {"matmul_allow_tf32": False, "cudnn_allow_tf32": True,
                "cudnn_benchmark": False, "cudnn_deterministic": True, "deterministic_algorithms": False}}
        write_once(out / "capture_completed.json", capture_complete)
        budget = {**q_budget(candidates), "capture_completion": binding(root, out / "capture_completed.json"),
                  "candidates": binding(root, out / "candidates.jsonl"), "saved_Q_checkpoint": prepared["models"]["Q"]}
        write_once(out / "Q_budget.json", budget)
        print(json.dumps({"event": "complete_pool_Q_budget_sealed", "K": budget["K"], "Q_forwards": budget["Q_forwards"]}), flush=True)
        continuing()
        from . import candidate_quality_model as model_api
        from . import candidate_quality_pilot as pilot
        from .candidate_producer_transfer_experiment import restore_control
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.use_deterministic_algorithms(True)
        observed = [r for r in candidates if r["in_source_bounds"]]
        logits = {}
        q_health = {"checkpoint": prepared["models"]["Q"], "frozen_before": None, "groups_before": None, "model_constructed": False}
        if observed:
            crop_cache, weights, indices = pilot.make_crop_cache(root, observed, "candidate_id", out / "Q_crops.npy", model_api)
            with (out / "Q_point_weights.npy").open("xb") as stream:
                np.save(stream, weights, allow_pickle=False)
            write_lines(out / "Q_inputs.jsonl", ({"candidate_id": r["candidate_id"], "cache_index": i,
                "source_png": r["source_png"], "geometry": model_api.point_geometry(r["center_xy_px"], r["width_px"], r["height_px"])} for i, r in enumerate(observed)))
            continuing()
            model = model_api.build_model(root, device="cuda", execution_authorized=True)
            payload = bound(root, prepared["models"]["Q"]).read_bytes()
            check(hashlib.sha256(payload).hexdigest() == Q_SHA, "Saved Q bytes changed at load")
            checkpoint = torch.load(byteio.BytesIO(payload), map_location="cpu", weights_only=True)
            restore_control(model, checkpoint, "all_nba")
            del checkpoint, payload
            expected = read(bound(root, prepared["Q_final_fingerprints"]))
            frozen_before, groups_before = model_api.frozen_fingerprint(model), pilot.trainable_group_fingerprints(model)
            check(frozen_before == expected["frozen"] and groups_before == expected["trainable_groups"], "Restored original Q tensors differ")
            model.eval()
            q_health.update(frozen_before=frozen_before, groups_before=groups_before, model_constructed=True)
            with torch.inference_mode():
                for batch in pilot.batches(observed, BATCH_SIZE):
                    continuing()
                    ids = [r["candidate_id"] for r in batch]
                    pixels, points = pilot.input_batch(batch, crop_cache, weights, indices, "candidate_id")
                    start_call(counters, "Q", budget["Q_forwards"], journal, {"candidate_ids": ids})
                    values = model(pixels, points).detach().cpu().tolist()
                    check(len(values) == len(ids) and all(type(v) is float and math.isfinite(v) for v in values), "Invalid original Q scores")
                    counters["Q_returned"] += 1; counters["Q_presentations"] += len(ids)
                    for key, value in zip(ids, values, strict=True):
                        check(key not in logits, "Duplicate Q score identity")
                        logits[key] = value
                        append(out / "Q_scores.jsonl", {"candidate_id": key, "quality_logit": value})
                    append(journal, {"event": "Q_returned", "candidate_ids": ids, "counters": dict(counters)})
                    del pixels, points
            check(list(logits) == budget["ordered_candidate_ids"], "Complete Q order differs from sealed budget")
            q_health.update(frozen_after=model_api.frozen_fingerprint(model), groups_after=pilot.trainable_group_fingerprints(model))
            check(q_health["frozen_after"] == frozen_before and q_health["groups_after"] == groups_before, "Q inference changed tensors")
            crop_cache._mmap.close(); crop_cache = None
            del model
            torch.cuda.empty_cache()
        else:
            write_lines(out / "Q_scores.jsonl", [])
        write_once(out / "Q_model_health.json", {**q_health, "model_tensors_unchanged": True, "optimizer_updates": 0,
            "precision": {"matmul_allow_tf32": False, "cudnn_allow_tf32": False,
                "cudnn_benchmark": False, "cudnn_deterministic": True, "deterministic_algorithms": True}})
        continuing()
        fixed_frames = fixed_choices(frame_rows, candidates, logits)
        write_lines(out / "frames.jsonl", fixed_frames)
        from . import candidate_acceptance_features as feature_api
        gate = read(bound(root, prepared["models"]["J"]))
        check(gate["fit_id"] == "final_all_NBA" and gate["arm"] == "J", "Saved J head identity differs")
        by_frame = {}
        for row in observed:
            probe = {"row_key": "all_nba|" + row["candidate_id"], "frame_key": row["frame_key"], "fit": "all_nba", "cohort": "fresh_game",
                "logit": logits[row["candidate_id"]], **{k: row[k] for k in ("center_xy_px", "native_score", "component_pixels", "padding_pixels", "native_or_weak")}}
            by_frame.setdefault(row["frame_key"], []).append(probe)
        features = [feature_api.build_feature_row(probe, by_frame[probe["frame_key"]]) for pool in by_frame.values() for probe in pool]
        check([f["row_key"] for f in features] == ["all_nba|" + k for k in budget["ordered_candidate_ids"]], "J complete-pool feature order differs")
        jvalues = feature_api.score_gate(gate, features)
        jlogits = dict(zip(budget["ordered_candidate_ids"], jvalues, strict=True))
        counters["J_predictions"] = len(jvalues)
        write_lines(out / "features.jsonl", features)
        scores = [{"candidate_id": r["candidate_id"], "frame_key": r["frame_key"], "Q": logits.get(r["candidate_id"]),
            "J": jlogits.get(r["candidate_id"]), "status": "observed" if r["in_source_bounds"] else "out_of_source_bounds"} for r in candidates]
        write_lines(out / "scores.jsonl", scores)
        validate_counters(counters, budget)
        continuing()
        result = {"status": "completed_fresh_game_inference_no_fitting", "at_utc": stamp(), "elapsed_seconds": time.monotonic() - began,
            "accepted_reference": prepared["accepted_reference"], "prepared": binding(root, root / PREPARATION), "inputs": prepared["inputs"],
            "execution_freeze": binding(root, root / LAUNCH_BASE / "execution_freeze.json"), "models": prepared["models"],
            "scope": COUNTS, "counters": counters, "K": budget["K"], "retained_candidates": len(candidates),
            "frames": binding(root, out / "frames.jsonl"), "candidates": binding(root, out / "candidates.jsonl"),
            "scores": binding(root, out / "scores.jsonl"), "features": binding(root, out / "features.jsonl"),
            "capture_completion": binding(root, out / "capture_completed.json"), "Q_budget": binding(root, out / "Q_budget.json"),
            "labels_used": False, "Q_J_pool": "all in-bounds retained candidates, including every native and weak origin; OOB retained with null scores",
            "Qtop_tie_rule": "descending original Q then ascending candidate_id", "new_training_updates": 0, "CPU_gate_fits": 0,
            "new_labels": 0, "new_selector_runs": 0, "model_adopted": False, "automatic_retry": False,
            "outputs": [binding(root, p) for p in sorted(out.rglob("*")) if p.is_file()]}
        write_once(out / "completed.json", result)
        return result
    except BaseException as error:
        write_once(out / "failed.json", {"at_utc": stamp(), "elapsed_seconds": time.monotonic() - began, "error": type(error).__name__,
            "message": str(error), "traceback": traceback.format_exc(), "counters": counters, "automatic_retry": False})
        raise
    finally:
        done.set()
        for opened in (array, crop_cache):
            if opened is not None:
                opened._mmap.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--run", action="store_true")
    parser.add_argument("--monitor")
    args = parser.parse_args()
    if args.prepare:
        result = prepare()
    elif args.run:
        check(args.monitor is not None, "Owned monitor required")
        result = run(ROOT, args.monitor, sys.argv[1:])
    else:
        prepared, freeze = preflight()
        result = {"status": "metadata_preflight_passed", "counts": prepared["counts"]}
    print(json.dumps({k: result[k] for k in ("status", "counters", "K") if k in result}), flush=True)


if __name__ == "__main__":
    main()
