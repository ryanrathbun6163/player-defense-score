"""Unlabeled development observation with sealed bands omitted before decoding.

Each visible segment is independent. Cached raw triplets retain their original
identity; longer-context means are new observations, never replacement scores.
"""
from __future__ import annotations

import argparse
from collections import deque
import csv
import json
import shutil
import subprocess
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from .annotations import SourceVideo, verify_source_video_contract
from .wasb_adapter import components_from_heatmap, transform_metadata
from .wasb_experiment import (
    bound_path, canonical, digest_file, inference_source_digest, merge_heatmaps,
    read_json, read_triplet_cache, repository_path, runtime_versions,
    triplet_starts, write_npz_once, write_once,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = "configs/ball_tracking/wasb_experiments/wasb_expanded_development_observation_v0_1.json"
HEADER_HEIGHT = 160
POLICY = {"heatmap_threshold": .3, "triplet_stride": 1,
          "overlap_policy": "all_available_mean", "selection": "largest_component_mass", "device": "cuda"}
OLD_POLICY = {"device": "cuda", "precision": "float32", "batch_size": 1,
              "temporal_policy": "mean_all_available_triplets_within_window", "heatmap_threshold": .5,
              "threshold_operator": ">", "padding": "none", "tracker": "none", "interpolation": "none"}


def binding(root, path):
    return {"path": path.resolve().relative_to(root.resolve()).as_posix(),
            "sha256": digest_file(path), "size_bytes": path.stat().st_size}


def complement_ranges(count, protected):
    result, cursor = [], 0
    for start, end in protected:
        if type(start) is not int or type(end) is not int or not cursor <= start <= end < count:
            raise ValueError("Protected ranges must be sorted, disjoint, integer frame intervals")
        if cursor < start:
            result.append([cursor, start - 1])
        cursor = end + 1
    if cursor < count:
        result.append([cursor, count - 1])
    return result


def validate_scope(config, split):
    """Metadata only: complete exclusions are established before any source open."""
    if (config.get("schema_version") != "wasb_development_observation/v0.1"
            or config.get("inference") != POLICY or config.get("holdout_buffer_frames") != 25):
        raise ValueError("Unsupported observation schema, inference policy or holdout buffer")
    render = config["rendering"]
    if render != {"playback_fps": 25, "crf": 18}:
        raise ValueError("This observation uses source-rate 25fps H264 CRF18 rendering")
    declared = split["sealed_holdouts"]
    if not declared or len({p["possession_id"] for p in config["possessions"]}) != len(config["possessions"]):
        raise ValueError("Missing holdout metadata or repeated possession")
    if {p["possession_id"] for p in config["possessions"]} != {h["possession_id"] for h in declared}:
        raise ValueError("Observation possession inventory differs from sealed metadata")
    for possession in config["possessions"]:
        source = possession["source_video"]
        SourceVideo.from_mapping(source)
        protected = []
        for held in declared:
            if held["possession_id"] == possession["possession_id"]:
                if source != held["source_video"] or held["selection_purpose"] != "test_holdout":
                    raise ValueError("Holdout/source binding differs")
                protected.append([max(0, held["start_frame_index"] - 25),
                                  min(source["frame_count"] - 1, held["end_frame_index"] + 25)])
        protected.sort()
        expected_visible = complement_ranges(source["frame_count"], protected)
        if possession["protected_ranges"] != protected or possession["visible_segments"] != expected_visible:
            raise ValueError("Visible segments must be the exact complement of holdouts plus 25-frame buffers")
        for start, end in expected_visible:
            triplet_starts(start, end)
        if source["fps"] != 25:
            raise ValueError("Source-rate review requires a 25fps source")


def load_config(root, path):
    config = read_json(path)
    split = read_json(bound_path(root, config["split_metadata"]))
    validate_scope(config, split)
    old = read_json(bound_path(root, config["cached_experiment"]))
    completion = read_json(bound_path(root, config["training_completion"]))
    training = read_json(bound_path(root, config["training_config"]))
    if (completion.get("status") != "completed" or completion.get("completed_updates") != 200
            or completion.get("config") != config["training_config"]
            or old.get("training_completion") != config["training_completion"]
            or old.get("checkpoint") != completion.get("checkpoint")
            or old.get("training_provenance") != completion.get("training_provenance")
            or old.get("inference") != OLD_POLICY
            or old.get("development_manifest") != config["split_metadata"]):
        raise ValueError("Frozen training/comparison lineage differs")
    if not completion.get("training_provenance") or training.get("schema_version") != "wasb_adaptation_experiment/v0.2":
        raise ValueError("Observation requires the completed expanded training lineage")
    for possession in config["possessions"]:
        bound_path(root, possession["player_context"])
        repository_path(root, possession["source_video"]["path"], "data/clips")
    repository_path(root, config["output_root"], "data/outputs")
    return config, old, completion, training


def model_identity(old, versions):
    return {"weights": old["checkpoint"], "training_completion": old["training_completion"],
            "upstream_commit": old["upstream_commit"],
            "adapter_sha256": digest_file(Path(__file__).with_name("wasb_adapter.py")),
            "derived_adapter_sha256": digest_file(Path(__file__).with_name("wasb_adapted_adapter.py")),
            "inference_source_sha256": inference_source_digest(), "runtime_versions": versions,
            "input_modality": "three_RGB_images", "offline_future_context": True}


def validate_cache_identity(identity, old, model):
    if (any(identity.get(key) != value for key, value in model.items())
            or identity.get("experiment_config_sha256") != canonical(old)
            or identity.get("inference") != OLD_POLICY or old.get("inference") != OLD_POLICY):
        raise ValueError("Old raw-triplet producer/model/input identity is incompatible")
    # Threshold/native-score definitions are old postprocessing, not model input.
    # Pass the complete OLD identity to its reader; never rewrite it as the new one.


def cache_index(root, config, old, model):
    result = {}
    old_root = repository_path(root, old["output_root"], "data/outputs")
    possessions = {p["possession_id"]: p for p in config["possessions"]}
    for window in old["windows"]:
        possession = possessions[window["possession_id"]]
        start, end = window["start_frame_index"], window["end_frame_index"]
        if (window["source_video"] != possession["source_video"]
                or not any(a <= start <= end <= b for a, b in possession["visible_segments"])):
            raise ValueError("Saved cache window does not belong to an allowed source segment")
        folder = repository_path(root, (old_root / window["window_id"]).relative_to(root).as_posix(), old["output_root"])
        identity_path = folder / "inference_identity.json"
        identity = read_json(identity_path)
        validate_cache_identity(identity, old, model)
        for first in triplet_starts(start, end):
            key = (possession["possession_id"], first)
            if key in result:
                raise ValueError("Saved raw triplets have ambiguous origins")
            cache, receipt = folder / f"triplet_{first:06d}.npz", folder / f"triplet_{first:06d}.json"
            if not cache.is_file() or not receipt.is_file():
                raise ValueError("Previously completed triplet/receipt is missing; do not repeat its inference")
            result[key] = {"cache": cache, "receipt": receipt, "identity": identity,
                           "identity_binding": binding(root, identity_path), "window_id": window["window_id"]}
    return result


def guard_segment(possession, segment):
    start, end = segment
    if (list(segment) not in possession["visible_segments"]
            or any(max(start, low) <= min(end, high) for low, high in possession["protected_ranges"])):
        raise ValueError("Decode/inference segment intersects a protected band or is undeclared")
    triplet_starts(start, end)


def decode_segment(root, possession, segment):
    """Only yield requested visible pixels; never walk through a protected band."""
    guard_segment(possession, segment)
    source = possession["source_video"]
    capture = cv2.VideoCapture(str(repository_path(root, source["path"], "data/clips")))
    try:
        start, end = segment
        if not capture.isOpened() or not capture.set(cv2.CAP_PROP_POS_FRAMES, start):
            raise ValueError("Could not seek the allowed source segment")
        for index in range(start, end + 1):
            ok, frame = capture.read()
            if (not ok or frame.shape != (source["height_px"], source["width_px"], 3)
                    or abs(capture.get(cv2.CAP_PROP_POS_FRAMES) - (index + 1)) > .01):
                raise ValueError(f"Decode/frame-position mismatch at {index}")
            yield index, frame
    finally:
        capture.release()


def validate_heatmaps(values):
    if (not isinstance(values, np.ndarray) or values.shape != (3, 288, 512)
            or values.dtype != np.float32 or not np.isfinite(values).all()
            or (values < 0).any() or (values > 1).any()):
        raise ValueError("Invalid raw sigmoid heatmaps")


def read_bound_triplet(root, cache, receipt, first, identity, source):
    values, elapsed = read_triplet_cache(cache, receipt, [first, first + 1, first + 2], identity)
    validate_heatmaps(values)
    metadata = read_json(receipt)
    if metadata["transform"] != transform_metadata(source["width_px"], source["height_px"]):
        raise ValueError("Cached affine transform/source dimensions differ")
    return values, {"cache": binding(root, cache), "receipt": binding(root, receipt),
                    "original_inference_seconds": elapsed,
                    "cuda_peak_allocated_bytes": metadata["cuda_peak_allocated_bytes"]}


def observed_frames(means, counts, start, source, threshold):
    frames = []
    for offset, (heatmap, count) in enumerate(zip(means, counts, strict=True)):
        components = components_from_heatmap(heatmap, source["width_px"], source["height_px"], threshold)
        candidates = [{"candidate_index": j, **item} for j, item in enumerate(components)]
        selected = min(candidates, key=lambda c: (-c["native_score"], c["candidate_index"])) if candidates else None
        frames.append({"frame_index": start + offset, "state": "observed" if selected else "missing",
                       "contribution_count": count, "candidates": candidates,
                       "selected_candidate_index": None if selected is None else selected["candidate_index"],
                       "center_xy_px": None if selected is None else [selected["center_x"], selected["center_y"]],
                       "native_score": None if selected is None else selected["native_score"]})
    return frames


def infer_segment(root, config, possession, segment, output, identity, old_caches, predict):
    guard_segment(possession, segment)
    start, end = segment
    source = possession["source_video"]
    folder = output / possession["possession_id"] / f"segment_{start:06d}_{end:06d}"
    folder.mkdir(parents=True, exist_ok=True)
    segment_identity = {**identity, "source_video": source, "segment": [start, end]}
    write_once(folder / "inference_identity.json", segment_identity)
    plans = {}
    for first in triplet_starts(start, end):
        old = old_caches.get((possession["possession_id"], first))
        plans[first] = old or {"cache": folder / f"triplet_{first:06d}.npz",
                              "receipt": folder / f"triplet_{first:06d}.json", "identity": segment_identity}
    needs_pixels = any(not item["cache"].exists() for item in plans.values())
    images = iter(decode_segment(root, possession, segment)) if needs_pixels else None
    ring = deque(maxlen=3)
    triplets, records = {}, []
    try:
        for first, plan in plans.items():
            reused = "window_id" in plan
            fresh = not plan["cache"].exists()
            if fresh:
                if plan["receipt"].exists():
                    raise ValueError("Triplet receipt exists without arrays; preserve before recovery")
                while not ring or ring[-1][0] < first + 2:
                    ring.append(next(images))
                if [row[0] for row in ring] != [first, first + 1, first + 2]:
                    raise ValueError("Rolling source frames are not aligned with the triplet")
                rgb = [cv2.cvtColor(row[1], cv2.COLOR_BGR2RGB) for row in ring]
                prediction, elapsed, peak = predict(rgb)
                values = prediction["heatmaps"]
                validate_heatmaps(values)
                expected_transform = transform_metadata(source["width_px"], source["height_px"])
                if len(prediction["frames"]) != 3 or any(row["transform"] != expected_transform for row in prediction["frames"]):
                    raise ValueError("Actual model output affine transform differs")
                metadata = {"input_frame_indices": [first, first + 1, first + 2],
                            "output_frame_indices": [first, first + 1, first + 2], "inference_seconds": elapsed,
                            "inference_identity_sha256": canonical(segment_identity),
                            "transform": expected_transform, "cuda_peak_allocated_bytes": peak}
                write_npz_once(plan["cache"], heatmaps=values,
                               metadata_json=np.array(json.dumps(metadata, sort_keys=True, allow_nan=False)))
            values, record = read_bound_triplet(root, plan["cache"], plan["receipt"], first, plan["identity"], source)
            triplets[first] = values
            records.append({"input_frame_indices": [first, first + 1, first + 2], **record,
                            "origin": "prior_development_cache" if reused else "observation_cache",
                            "original_identity": plan.get("identity_binding", binding(root, folder / "inference_identity.json"))})
    finally:
        if images is not None:
            images.close()
    means, counts = merge_heatmaps(triplets, start, end)
    frames = observed_frames(means, counts, start, source, config["inference"]["heatmap_threshold"])
    write_npz_once(folder / "mean_heatmaps.npz", heatmaps=means, frame_indices=np.arange(start, end + 1))
    result = {"segment": [start, end], "identity": segment_identity, "frames": frames, "triplets": records,
              "mean_heatmaps": binding(root, folder / "mean_heatmaps.npz")}
    write_once(folder / "observations.json", result)
    return result


def make_timeline(possession, segments, training_blocks):
    lookup = {}
    for result in segments:
        guard_segment(possession, result["segment"])
        start, end = result["segment"]
        if [r["frame_index"] for r in result["frames"]] != list(range(start, end + 1)):
            raise ValueError("Segment observations are incomplete or misaligned")
        for row in result["frames"]:
            if row["frame_index"] in lookup:
                raise ValueError("Duplicate segment observation")
            lookup[row["frame_index"]] = {**row, "segment": result["segment"]}
    frames = []
    for index in range(possession["source_video"]["frame_count"]):
        protected = any(low <= index <= high for low, high in possession["protected_ranges"])
        if protected:
            if index in lookup:
                raise ValueError("Protected frame has a model observation")
            row = {"frame_index": index, "state": "withheld", "segment": None, "contribution_count": 0,
                   "candidates": [], "selected_candidate_index": None, "center_xy_px": None, "native_score": None}
        else:
            if index not in lookup:
                raise ValueError("Visible frame is missing its explicit observation state")
            row = lookup[index]
        row["training_frame"] = any(b["possession_id"] == possession["possession_id"]
            and b["start_frame_index"] <= index <= b["end_frame_index"] for b in training_blocks)
        frames.append(row)
    return frames


def load_player_display(root, possession):
    # Player positions are display-only and never supplied to predict/selection.
    path = bound_path(root, possession["player_context"])
    rows = {}
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            index = int(row["frame_index"])
            if any(low <= index <= high for low, high in possession["visible_segments"]):
                rows.setdefault(index, []).append(row)
    return rows


def render_frame(source, row, source_metadata, players):
    width, height = source_metadata["width_px"], source_metadata["height_px"]
    canvas = np.zeros((height + HEADER_HEIGHT, width, 3), dtype=np.uint8)
    withheld = row["state"] == "withheld"
    if withheld:
        if source is not None or row["center_xy_px"] is not None or row["contribution_count"] != 0:
            raise ValueError("Withheld render must receive no source pixels or ball state")
    else:
        if source is None or source.shape != (height, width, 3):
            raise ValueError("Visible render requires the synchronized source image")
        overlay = source.copy()
        for player in players:
            x, y = round(float(player["floor_x"])), round(float(player["floor_y"]))
            cv2.circle(overlay, (x, y), 4, (230, 230, 230), -1)
            cv2.putText(overlay, player["player_id"], (x + 5, y + 12), cv2.FONT_HERSHEY_SIMPLEX,
                        .44, (245, 245, 245), 1, cv2.LINE_AA)
        if row["center_xy_px"] is not None:
            x, y = map(round, row["center_xy_px"])
            if 0 <= x < width and 0 <= y < height:
                cv2.drawMarker(overlay, (x, y), (240, 80, 240), cv2.MARKER_CROSS, 23, 2, cv2.LINE_AA)
        canvas[HEADER_HEIGHT:] = overlay
    lines = [f"FRAME {row['frame_index']} | {row['state'].upper()} | 0.3 DEVELOPMENT CANDIDATE | source rate 25 fps",
             "UNLABELED / NO REFERENCE | human visual review pending | no interpolation or connecting trail",
             ("WITHHELD: sealed holdout plus 25-frame buffer; source pixels and inference omitted" if withheld else
              f"Magenta: model observation | White: reviewed player IDs (display only) | contributions {row['contribution_count']}"),
             "Includes training frames; not an accuracy test. Missing = no component above threshold, not proof of hidden ball."]
    for offset, text in enumerate(lines):
        cv2.putText(canvas, text, (18, 30 + 35 * offset), cv2.FONT_HERSHEY_SIMPLEX,
                    .65 if offset == 0 else .57, (235, 235, 235), 1, cv2.LINE_AA)
    return canvas


def verify_rendered_video(path, frames, shape, final_path):
    capture = cv2.VideoCapture(str(path))
    last = None
    try:
        for row in frames:
            ok, image = capture.read()
            if not ok or image.shape != shape:
                raise ValueError("Review video frame count or dimensions differ")
            if row["state"] == "withheld" and int(image[HEADER_HEIGHT:].max()) > 3:
                raise ValueError("Protected review source area is not black")
            last = image
        if capture.read()[0]:
            raise ValueError("Review video contains extra timeline frames")
    finally:
        capture.release()
    if last is None or not cv2.imwrite(str(final_path), last):
        raise ValueError("Decoded final-frame image could not be saved")
    return {"decoded_frames": len(frames), "final_frame_decoded": True,
            "protected_source_areas_verified_black": sum(r["state"] == "withheld" for r in frames)}


def render_possession(root, config, possession, observations, folder):
    receipt_path = folder / "review.json"
    identity = {"observations": binding(root, folder / "observations.json"),
                "player_context": possession["player_context"], "source_video": possession["source_video"],
                "renderer_sha256": digest_file(Path(__file__)), "rendering": config["rendering"]}
    if receipt_path.exists():
        saved = read_json(receipt_path)
        if saved["identity"] != identity:
            raise ValueError("Completed review identity differs")
        bound_path(root, saved["video"])
        bound_path(root, saved["decoded_final_frame"])
        return saved
    attempt = folder / "render_attempts" / uuid.uuid4().hex
    attempt.mkdir(parents=True)
    target, final = attempt / "review.mp4", attempt / "final_frame.png"
    write_once(attempt / "started.json", identity)
    source = possession["source_video"]
    width, height = source["width_px"], source["height_px"] + HEADER_HEIGHT
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise ValueError("ffmpeg is required for H264 review output")
    players = load_player_display(root, possession)
    decoders = {start: [start, end] for start, end in possession["visible_segments"]}
    images = None
    with (attempt / "ffmpeg.log").open("wb") as log:
        process = subprocess.Popen([ffmpeg, "-hide_banner", "-loglevel", "error", "-n", "-f", "rawvideo",
            "-pix_fmt", "bgr24", "-s", f"{width}x{height}", "-r", str(config["rendering"]["playback_fps"]),
            "-i", "pipe:0", "-an", "-c:v", "libx264", "-threads", "2", "-crf", str(config["rendering"]["crf"]),
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(target)], stdin=subprocess.PIPE, stderr=log)
        try:
            for row in observations["frames"]:
                index = row["frame_index"]
                if index in decoders:
                    if images is not None:
                        images.close()
                    images = iter(decode_segment(root, possession, decoders[index]))
                pixels = None
                if row["state"] != "withheld":
                    actual, pixels = next(images)
                    if actual != index:
                        raise ValueError("Source/player/ball review is not synchronized")
                elif images is not None:
                    images.close()
                    images = None
                canvas = render_frame(pixels, row, source, players.get(index, []))
                process.stdin.write(canvas.tobytes())
            process.stdin.close()
            if process.wait(timeout=120) != 0:
                raise ValueError("H264 encoding failed; attempt/log preserved")
        finally:
            if images is not None:
                images.close()
            if process.stdin and not process.stdin.closed:
                try:
                    process.stdin.close()
                except OSError:
                    pass  # Encoder exit may break the pipe; still reap our process.
            if process.poll() is None:
                process.kill()
                process.wait()
    verified = verify_rendered_video(target, observations["frames"], (height, width, 3), final)
    receipt = {"identity": identity, "video": binding(root, target), "decoded_final_frame": binding(root, final),
               "verification": verified, "human_visual_review": "pending", "selected_operating_point": None}
    write_once(receipt_path, receipt)
    return receipt


def execute(root, config_path, *, check_only=False):
    config, old, completion, training = load_config(root, config_path)
    cv2.setNumThreads(1)
    model = model_identity(old, runtime_versions())
    old_caches = cache_index(root, config, old, model)
    totals = {"visible_frames": sum(b - a + 1 for p in config["possessions"] for a, b in p["visible_segments"]),
              "withheld_frames": sum(b - a + 1 for p in config["possessions"] for a, b in p["protected_ranges"]),
              "triplets": sum(b - a - 1 for p in config["possessions"] for a, b in p["visible_segments"]),
              "prior_cached_triplets": len(old_caches)}
    totals["new_triplets"] = totals["triplets"] - totals["prior_cached_triplets"]
    if check_only:
        return {"status": "metadata_and_cache_identity_checked_no_decode_or_inference", **totals}
    import torch
    from .wasb_adapted_adapter import AdaptedWasbAdapter
    from .wasb_training import training_lock
    output = repository_path(root, config["output_root"], "data/outputs")
    output.mkdir(parents=True, exist_ok=True)
    with training_lock(output / "observation.lock"):
        attempt_path = output / "invocations" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + uuid.uuid4().hex + ".json")
        began = time.perf_counter()
        receipt = {"status": "started", "config": binding(root, config_path), "new_model_calls": 0,
                   "source": binding(ROOT, Path(__file__)), "scope": totals}
        write_once(attempt_path.with_suffix(".started.json"), receipt)
        identity = {**model, "observation_config_sha256": canonical(config),
                    "observation_source_sha256": digest_file(Path(__file__)),
                    "pretrained_checkpoint": old["pretrained_checkpoint"], "inference": POLICY}
        adapter = None
        try:
            write_once(output / "experiment.json", config)
            write_once(output / "inference_identity.json", identity)
            if shutil.disk_usage(output).free < 5 * 1024 ** 3:
                raise ValueError("At least 5GiB free disk is needed for caches and review output")
            bound_path(root, completion["checkpoint"])
            bound_path(root, old["pretrained_checkpoint"])

            def predict(rgb):
                nonlocal adapter
                if adapter is None:
                    adapter = AdaptedWasbAdapter(repository_path(root, old["upstream_source"]),
                        bound_path(root, old["pretrained_checkpoint"]), bound_path(root, completion["checkpoint"]),
                        completion["checkpoint"]["sha256"], completion["training_provenance"], device="cuda")
                    write_once(output / "model_runtime.json", adapter.provenance)
                    torch.cuda.reset_peak_memory_stats()
                torch.cuda.synchronize()
                start = time.perf_counter()
                receipt["new_model_calls"] += 1
                prediction = adapter.predict_triplet(rgb)
                torch.cuda.synchronize()
                elapsed = time.perf_counter() - start
                receipt["new_inference_seconds"] = receipt.get("new_inference_seconds", 0) + elapsed
                receipt["cuda_peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
                receipt["cuda_peak_reserved_bytes"] = torch.cuda.max_memory_reserved()
                return prediction, elapsed, receipt["cuda_peak_allocated_bytes"]

            results = []
            for possession in config["possessions"]:
                verify_source_video_contract(SourceVideo.from_mapping(possession["source_video"]), root)
                segments = []
                for segment in possession["visible_segments"]:
                    segments.append(infer_segment(root, config, possession, segment, output, identity, old_caches, predict))
                    print(f"{possession['possession_id']} frames {segment[0]}-{segment[1]} observations complete", flush=True)
                timeline = make_timeline(possession, segments, training["training_blocks"])
                observations = {"schema_version": "unlabeled_ball_development_observations/v0.1",
                    "possession_id": possession["possession_id"], "source_video": possession["source_video"],
                    "model_provenance": identity, "training_completion": config["training_completion"],
                    "visible_segments": possession["visible_segments"], "protected_ranges": possession["protected_ranges"],
                    "reference_labels": None, "selected_operating_point": None, "human_visual_review": "pending",
                    "threshold_status": "0.3_development_candidate", "frames": timeline,
                    "segments": [{key: value for key, value in item.items() if key != "frames"} for item in segments]}
                folder = output / possession["possession_id"]
                write_once(folder / "observations.json", observations)
                review = render_possession(root, config, possession, observations, folder)
                counts = {state: sum(r["state"] == state for r in timeline) for state in ("observed", "missing", "withheld")}
                results.append({"possession_id": possession["possession_id"], "counts": counts,
                    "observations": binding(root, folder / "observations.json"), "review": review})
            summary = {"schema_version": "wasb_development_observation_summary/v0.1", "scope": totals,
                       "possessions": results, "accuracy_metrics": None, "selected_operating_point": None,
                       "human_visual_review": "pending", "training_completion": config["training_completion"],
                       "limitations": ["Unlabeled, training-inclusive development inspection, not an accuracy test",
                           "Longer-context means do not replace the frozen six-window metrics",
                           "Withheld source bands are black; no temporal inputs or trajectories cross them",
                           "Observed means a model output, not confirmed ball identity; missing is not proof of occlusion"]}
            write_once(output / "summary.json", summary)
            receipt.update(status="completed", summary=binding(root, output / "summary.json"))
            return summary
        except BaseException as error:
            receipt.update(status="failed", error=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
            raise
        finally:
            receipt["elapsed_seconds"] = time.perf_counter() - began
            write_once(attempt_path, receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    result = execute(ROOT, repository_path(ROOT, args.config), check_only=args.check_only)
    print(json.dumps(result if args.check_only else {"status": "completed", "scope": result["scope"]}), flush=True)


if __name__ == "__main__":
    main()
