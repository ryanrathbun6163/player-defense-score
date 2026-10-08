"""Cached, development-only WASB transfer comparison; no training or tracking.

Model inputs stay inside the released windows. Labels and saved controls enter
only scoring/rendering. Native heatmap sums are never detector probabilities.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .annotations import SourceVideo, load_annotations, verify_source_video_contract

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = "configs/ball_tracking/wasb_experiments/wasb_basketball_transfer_v0_1.json"
POINT_SCHEMA = "ball_point_observations/v0.1"


def digest_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_once(path, value):
    path = Path(path)
    if path.exists():
        if read_json(path) != value:
            raise ValueError(f"Existing evidence differs; preserve it and use a new output path: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def inference_source_digest():
    """Bind inference behavior while allowing report-only source corrections."""
    names = {"decode_window", "triplet_starts", "merge_heatmaps", "make_point_run", "infer_window"}
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    definitions = {node.name: ast.dump(node, include_attributes=False)
                   for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names}
    if set(definitions) != names:
        raise ValueError("Inference source inventory is incomplete")
    return canonical(definitions)


def runtime_versions():
    import cv2
    import torch
    return {"python": sys.version, "numpy": np.__version__, "opencv": cv2.__version__,
            "torch": str(torch.__version__), "torch_cuda": torch.version.cuda,
            "cudnn": torch.backends.cudnn.version()}


def write_npz_once(path, **arrays):
    """Recover complete derived arrays without replacing contradictory evidence."""
    path = Path(path)
    if path.exists():
        with np.load(path, allow_pickle=False) as saved:
            if (set(saved.files) != set(arrays) or any(
                    saved[key].dtype != value.dtype or not np.array_equal(saved[key], value)
                    for key, value in arrays.items())):
                raise ValueError(f"Existing array evidence differs: {path}")
        return
    with path.open("xb") as stream:
        np.savez_compressed(stream, **arrays)


def read_triplet_cache(cache, receipt, frame_ids, identity):
    """The NPZ embeds enough metadata to recover a missing JSON receipt."""
    with np.load(cache, allow_pickle=False) as saved:
        if set(saved.files) != {"heatmaps", "metadata_json"}:
            raise ValueError("Triplet cache has no complete embedded receipt")
        heatmaps = saved["heatmaps"]
        metadata = json.loads(str(saved["metadata_json"].item()))
    elapsed = metadata["inference_seconds"]
    if (metadata["input_frame_indices"] != frame_ids
            or metadata["output_frame_indices"] != frame_ids
            or metadata["inference_identity_sha256"] != canonical(identity)
            or isinstance(elapsed, bool) or not isinstance(elapsed, (int, float))
            or not math.isfinite(elapsed) or elapsed < 0):
        raise ValueError("Triplet cache identity/frame/time metadata differs")
    write_once(receipt, {**metadata, "sha256": digest_file(cache)})
    return heatmaps, elapsed


def point_cache_receipt(folder):
    names = ("points.json", "components.json", "mean_heatmaps.npz", "inference_identity.json")
    return {"schema_version": "wasb_point_cache_receipt/v0.1",
            "files": {name: digest_file(folder / name) for name in names}}


def load_point_cache(folder, identity):
    if read_json(folder / "inference_identity.json") != identity:
        raise ValueError("Cached inference provenance differs")
    if read_json(folder / "points_receipt.json") != point_cache_receipt(folder):
        raise ValueError("Cached point/heatmap evidence digest differs")
    return read_json(folder / "points.json")


def repository_path(root, value, prefix=None):
    path = (root / value).resolve()
    path.relative_to(root.resolve())
    if prefix:
        path.relative_to((root / prefix).resolve())
    return path


def bound_path(root, binding):
    path = repository_path(root, binding["path"])
    if digest_file(path) != binding["sha256"]:
        raise ValueError(f"Input digest differs: {binding['path']}")
    return path


def triplet_starts(start, end):
    if type(start) is not int or type(end) is not int or start < 0 or end - start < 2:
        raise ValueError("A temporal window needs at least three valid consecutive frames")
    return list(range(start, end - 1))


def load_config(root, path):
    config = read_json(path)
    if config["schema_version"] != "wasb_development_comparison/v0.1":
        raise ValueError("Unsupported WASB experiment schema")
    dev = read_json(bound_path(root, config["development_manifest"]))
    declared = {w["window_id"]: w for w in dev["windows"]}
    seen = set()
    for window in config["windows"]:
        wid = window["window_id"]
        if wid in seen or wid not in declared:
            raise ValueError("Duplicate or unreleased window")
        seen.add(wid)
        parent = declared[wid]
        for key in ("possession_id", "source_video", "start_frame_index", "end_frame_index"):
            if window[key] != parent[key]:
                raise ValueError(f"Development window binding differs: {wid} {key}")
        if window["purpose"] != parent["selection_purpose"] or window["purpose"] not in {
                "representative_evaluation", "challenge_evaluation"}:
            raise ValueError("Only released development pools may run")
        start, end = window["start_frame_index"], window["end_frame_index"]
        triplet_starts(start, end)
        for held in dev["sealed_holdouts"]:
            if held["source_video"]["sha256"] == window["source_video"]["sha256"]:
                if max(start, held["start_frame_index"]) <= min(end, held["end_frame_index"]):
                    raise ValueError("Temporal input intersects a sealed holdout")
    if not seen:
        raise ValueError("No development windows")
    policy = config["inference"]
    if policy != {"device": "cuda", "precision": "float32", "batch_size": 1,
                  "temporal_policy": "mean_all_available_triplets_within_window",
                  "heatmap_threshold": 0.5, "threshold_operator": ">",
                  "padding": "none", "tracker": "none", "interpolation": "none"}:
        raise ValueError("This runner implements only the recorded untuned inference policy")
    repository_path(root, config["output_root"], "data/outputs")
    return config


def decode_window(root, window):
    import cv2
    source = window["source_video"]
    cap = cv2.VideoCapture(str(repository_path(root, source["path"], "data/clips")))
    frames = {}
    try:
        start, end = window["start_frame_index"], window["end_frame_index"]
        if not cap.isOpened() or not cap.set(cv2.CAP_PROP_POS_FRAMES, start):
            raise ValueError("Could not seek the declared source window")
        for index in range(start, end + 1):
            ok, frame = cap.read()
            if (not ok or frame.shape != (source["height_px"], source["width_px"], 3)
                    or abs(cap.get(cv2.CAP_PROP_POS_FRAMES) - (index + 1)) > 0.01):
                raise ValueError(f"Decode/frame-position mismatch at {index}")
            frames[index] = frame
    finally:
        cap.release()
    return frames


def merge_heatmaps(triplets, start, end):
    """Average only predictions whose output channel names the target frame."""
    sums = np.zeros((end - start + 1, 288, 512), dtype=np.float32)
    counts = np.zeros(end - start + 1, dtype=np.int32)
    if sorted(triplets) != triplet_starts(start, end):
        raise ValueError("Incomplete or extra temporal triplet outputs")
    for first in sorted(triplets):
        values = triplets[first]
        if (values.shape != (3, 288, 512) or values.dtype != np.float32
                or not np.isfinite(values).all() or (values < 0).any() or (values > 1).any()):
            raise ValueError("Invalid sigmoid heatmaps")
        for channel in range(3):
            offset = first + channel - start
            sums[offset] += values[channel]
            counts[offset] += 1
    if (counts == 0).any():
        raise ValueError("A scored frame has no model output")
    return sums / counts[:, None, None].astype(np.float32), counts.tolist()


def select_top_one(run):
    result = copy.deepcopy(run)
    result["point_run_id"] += "_top_native_mass"
    result["model_provenance"]["selection"] = "highest_native_score_then_candidate_index"
    for frame in result["frames"]:
        frame["candidates"] = sorted(frame["candidates"],
            key=lambda c: (-c["native_score"], c["candidate_index"]))[:1]
    return result


def make_point_run(window, provenance, components):
    start, end = window["start_frame_index"], window["end_frame_index"]
    if len(components) != end - start + 1:
        raise ValueError("Component output does not cover the declared window")
    return {"schema_version": POINT_SCHEMA,
            "point_run_id": window["window_id"] + "_wasb_all_components",
            "annotation_set_id": window["annotation_set_id"],
            "possession_id": window["possession_id"], "source_video": window["source_video"],
            "window": {"start_frame_index": start, "end_frame_index": end},
            "model_provenance": {**provenance, "selection": "all_components"},
            "frames": [{"frame_index": index, "inference_status": "completed", "failure_reason": None,
                        "candidates": [{"candidate_index": j,
                                        "center_xy_px": [c["center_x"], c["center_y"]],
                                        "native_score": c["native_score"]}
                                       for j, c in enumerate(rows)]}
                       for index, rows in zip(range(start, end + 1), components)]}


def infer_window(root, config, window, adapter, output, identity):
    from .wasb_adapter import components_from_heatmap
    import torch
    import cv2
    folder = output / window["window_id"]
    folder.mkdir(parents=True, exist_ok=True)
    write_once(folder / "inference_identity.json", identity)
    cached = folder / "points.json"
    if cached.exists() and (folder / "points_receipt.json").exists():
        return load_point_cache(folder, identity)
    source = window["source_video"]
    start, end = window["start_frame_index"], window["end_frame_index"]
    images = decode_window(root, window)
    triplets, timings = {}, []
    torch.cuda.reset_peak_memory_stats()
    for first in triplet_starts(start, end):
        cache = folder / f"triplet_{first:06d}.npz"
        receipt = folder / f"triplet_{first:06d}.json"
        if cache.exists():
            heatmaps, elapsed = read_triplet_cache(cache, receipt, [first, first + 1, first + 2], identity)
        else:
            if receipt.exists():
                raise ValueError("Triplet receipt exists without its cached arrays; preserve the evidence")
            if adapter is None:
                raise ValueError("Incomplete triplet cache requires a loaded WASB adapter")
            rgb = [cv2.cvtColor(images[i], cv2.COLOR_BGR2RGB) for i in range(first, first + 3)]
            torch.cuda.synchronize()
            began = time.perf_counter()
            prediction = adapter.predict_triplet(rgb)
            torch.cuda.synchronize()
            elapsed = time.perf_counter() - began
            heatmaps = prediction["heatmaps"]
            # Check actual producer output before persisting/reusing it.
            if (heatmaps.shape != (3, 288, 512) or heatmaps.dtype != np.float32
                    or not np.isfinite(heatmaps).all() or (heatmaps < 0).any() or (heatmaps > 1).any()):
                raise ValueError("Actual WASB output violates the heatmap contract")
            metadata = {"input_frame_indices": [first, first + 1, first + 2],
                        "output_frame_indices": [first, first + 1, first + 2],
                        "inference_seconds": elapsed, "inference_identity_sha256": canonical(identity),
                        "transform": prediction["frames"][0]["transform"],
                        "cuda_peak_allocated_bytes": torch.cuda.max_memory_allocated()}
            write_npz_once(cache, heatmaps=heatmaps,
                           metadata_json=np.array(json.dumps(metadata, sort_keys=True, allow_nan=False)))
            heatmaps, elapsed = read_triplet_cache(cache, receipt, [first, first + 1, first + 2], identity)
        triplets[first] = heatmaps
        timings.append(elapsed)
    means, counts = merge_heatmaps(triplets, start, end)
    components = [components_from_heatmap(h, source["width_px"], source["height_px"],
                                          threshold=config["inference"]["heatmap_threshold"]) for h in means]
    run = make_point_run(window, {**identity, "temporal_contributions_per_frame": counts}, components)
    write_npz_once(folder / "mean_heatmaps.npz", heatmaps=means, frame_indices=np.arange(start, end + 1))
    write_once(folder / "components.json", components)
    write_once(folder / "inference_timing.json", {"model_calls": len(triplets),
        "unique_scored_frames": end - start + 1, "inference_seconds": sum(timings),
        "cuda_peak_allocated_bytes": max(read_json(folder / f"triplet_{first:06d}.json")[
            "cuda_peak_allocated_bytes"] for first in triplets),
        "timing_scope": "Original triplet inference including adapter processing; excludes decoding, caching, scoring and rendering"})
    write_once(cached, run)
    write_once(folder / "points_receipt.json", point_cache_receipt(folder))
    return run


def rf_point_run(window, candidate_record, threshold):
    """Translate genuine saved RF centers/scores for parity, without inference."""
    frames = []
    for frame in candidate_record["frames"]:
        candidates = [c["detection"] for c in frame["candidates"]
                      if c["detection"]["confidence"] >= threshold]
        frames.append({"frame_index": frame["frame_index"], "inference_status": "completed",
                       "failure_reason": None, "candidates": [
                           {"candidate_index": c["candidate_index"], "center_xy_px": c["center_xy_px"],
                            "native_score": c["confidence"]} for c in candidates]})
    return {"schema_version": POINT_SCHEMA, "point_run_id": window["window_id"] + "_rf_saved",
            "annotation_set_id": window["annotation_set_id"], "possession_id": window["possession_id"],
            "source_video": window["source_video"],
            "window": {k: window[k] for k in ("start_frame_index", "end_frame_index")},
            "model_provenance": {"model_name": "saved RF-DETR crop union", "confidence_threshold": threshold,
                                 "selection": "all_components", "input": window["rf_candidates"]},
            "frames": frames}


def score_window(root, config, window, run, output, saved_reports):
    from .point_evaluation import evaluate_points
    labels = load_annotations(bound_path(root, window["annotation"]))
    if labels.window.selection_purpose != window["purpose"]:
        raise ValueError("Annotation pool differs")
    record = read_json(bound_path(root, window["rf_candidates"]))
    rf_all = rf_point_run(window, record, config["rf_confidence_threshold"])
    methods = {"wasb_all": run, "wasb_top_one": select_top_one(run),
               "rf_all": rf_all, "rf_top_one": select_top_one(rf_all)}
    reports = {}
    for name, point_run in methods.items():
        reports[name] = {}
        for radius in config["localization_radii_px"]:
            scored = evaluate_points(labels, point_run, localization_radius_px=radius)
            if name.startswith("rf_"):
                selector = "raw" if name == "rf_all" else "top_one"
                candidates = [r for r in saved_reports[window["purpose"]]["evaluation_reports"]
                    if r["possession_id"] == window["possession_id"]
                    and r["window"] == point_run["window"]
                    and r["config"] == {"image_arm": "four_crop_union", "selector": selector,
                        "confidence_threshold": config["rf_confidence_threshold"], "localization_radius_px": radius}]
                if len(candidates) != 1:
                    raise ValueError("Saved RF control selection is not unique")
                previous = candidates[0]
                for key, value in previous["metrics"].items():
                    if key not in {"input_detection_count", "below_threshold_detection_count"} and scored[key] != value:
                        raise ValueError(f"Point evaluator disagrees with saved RF metric: {key}")
                for actual, expected in zip(scored["frame_results"], previous["frame_results"]):
                    for key, value in expected.items():
                        if key not in {"input_detection_count", "below_threshold_detection_count"} and actual[key] != value:
                            raise ValueError(f"Point evaluator disagrees with saved RF frame field: {key}")
            reports[name][str(radius)] = scored
    payload = {"window_id": window["window_id"], "purpose": window["purpose"],
               "source_window": run["window"], "annotation": window["annotation"],
               "point_evaluator_sha256": digest_file(Path(__file__).with_name("point_evaluation.py")),
               "rf_saved_control_parity": "passed_all_declared_radii_raw_and_top_one",
               "reports": reports, "human_visual_review": "pending",
               "selected_operating_point": None, "quality_gate": None}
    write_once(output / window["window_id"] / "evaluation.json", payload)
    return payload, labels, methods


def outcome_table(scored):
    result = {"matched": [], "wrong_present": [], "missing": [], "hidden_alarm": []}
    for frame in scored["frame_results"]:
        i = frame["frame_index"]
        if frame["scoring_status"] == "localization_eligible":
            key = ("matched" if frame["matched_candidate_index"] is not None else
                   "wrong_present" if frame["accepted_detection_count"] else "missing")
            result[key].append(i)
        elif frame["non_visible_false_alarm_count"]:
            result["hidden_alarm"].append(i)
    return result


def summarize(config, payloads):
    radius = str(config["primary_radius_px"])
    rows = []
    for payload in payloads:
        reports = payload["reports"]
        rf = outcome_table(reports["rf_top_one"][radius])
        wasb = outcome_table(reports["wasb_top_one"][radius])
        rows.append({"window_id": payload["window_id"], "purpose": payload["purpose"],
                     "rf_top_one": rf, "wasb_top_one": wasb,
                     "rf_raw_available": reports["rf_all"][radius]["true_positive_count"],
                     "wasb_raw_available": reports["wasb_all"][radius]["true_positive_count"],
                     "eligible": reports["wasb_top_one"][radius]["eligible_frame_count"],
                     "hidden": reports["wasb_top_one"][radius]["not_visible_frame_count"],
                     "recovered": sorted(set(wasb["matched"]) - set(rf["matched"])),
                     "lost": sorted(set(rf["matched"]) - set(wasb["matched"]))})
    pools = {}
    for purpose in sorted({r["purpose"] for r in rows}):
        selected = [r for r in rows if r["purpose"] == purpose]
        pools[purpose] = {"window_count": len(selected),
            "eligible": sum(r["eligible"] for r in selected), "hidden": sum(r["hidden"] for r in selected),
            **{name: {key: sum(len(r[name][key]) for r in selected) for key in
                       ("matched", "wrong_present", "missing", "hidden_alarm")}
               for name in ("rf_top_one", "wasb_top_one")},
            **{key: sum(r[key] for r in selected) for key in ("rf_raw_available", "wasb_raw_available")},
            "recovered": sum(len(r["recovered"]) for r in selected),
            "lost": sum(len(r["lost"]) for r in selected)}
    return {"schema_version": "wasb_transfer_summary/v0.1", "experiment_id": config["experiment_id"],
            "primary_radius_px": config["primary_radius_px"], "pools": pools, "windows": rows,
            "human_visual_review": "pending", "selected_operating_point": None, "quality_gate": None,
            "limitations": ["Repeatedly inspected development data, not an independent test",
                "Geometric matching is not independently verified physical ball identity",
                "One hidden episode; five hidden frames are not five independent episodes",
                "Endpoint heatmaps have fewer temporal contributions; no external context or padding",
                "No tracker, interpolation, training, or player/court input to WASB"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--window", help="Run one declared window first; completed inference is reusable")
    parser.add_argument("--stage", choices=("infer", "score", "render", "all"), default="all")
    args = parser.parse_args()
    root = ROOT
    config_path = repository_path(root, args.config)
    output = repository_path(root, read_json(config_path)["output_root"], "data/outputs")
    output.mkdir(parents=True, exist_ok=True)
    invocation_id = str(time.time_ns())
    started = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()
    windows, failure = [], None
    try:
        config = load_config(root, config_path)
        windows = [w for w in config["windows"] if args.window is None or w["window_id"] == args.window]
        if not windows:
            raise ValueError("Requested window is not in the development configuration")
        write_once(output / "experiment.json", config)
        adapter = None
        model_path = bound_path(root, config["checkpoint"])
        identity = {"experiment_config_sha256": canonical(config), "weights": config["checkpoint"],
                    "upstream_commit": config["upstream_commit"], "inference": config["inference"],
                    "adapter_sha256": digest_file(Path(__file__).with_name("wasb_adapter.py")),
                    "inference_source_sha256": inference_source_digest(), "runtime_versions": runtime_versions(),
                    "native_score_definition": "sum of sigmoid values in an 8-connected component above 0.5",
                    "input_modality": "three_RGB_images", "offline_future_context": True}
        saved_reports = {p: read_json(bound_path(root, b)) for p, b in config["rf_reports"].items()}
        payloads = []
        for window in windows:
            verify_source_video_contract(SourceVideo.from_mapping(window["source_video"]), root)
            began = time.perf_counter()
            print(f"Processing {window['window_id']}", flush=True)
            folder = output / window["window_id"]
            if args.stage in {"all", "infer"}:
                if adapter is None and not (folder / "points.json").exists():
                    from .wasb_adapter import WasbAdapter
                    adapter = WasbAdapter(repository_path(root, config["upstream_source"]), model_path,
                                          device=config["inference"]["device"])
                    write_once(output / "model_runtime.json", adapter.provenance)
                run = infer_window(root, config, window, adapter, output, identity)
            else:
                run = load_point_cache(folder, identity)
            if args.stage != "infer":
                payload, labels, methods = score_window(root, config, window, run, output, saved_reports)
                payloads.append(payload)
                if args.stage in {"all", "render"}:
                    from .wasb_review import render_window
                    render_window(root, window, labels, methods, payload, folder)
            print(f"Completed {window['window_id']} in {time.perf_counter()-began:.2f}s", flush=True)
        if len(payloads) == len(config["windows"]):
            summary = summarize(config, payloads)
            write_once(output / "summary.json", summary)
            print(json.dumps(summary["pools"], indent=2), flush=True)
    except BaseException as error:
        failure = {"type": type(error).__name__, "message": str(error)[:2000]}
        raise
    finally:
        try:
            head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        except Exception:
            head = None
        receipt = {"started_at_utc": started_at, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                   "duration_seconds": time.perf_counter() - started, "stage": args.stage,
                   "requested_window": args.window, "windows": [w["window_id"] for w in windows],
                   "repository_head": head, "runner_sha256": digest_file(Path(__file__)),
                   "status": "failed" if failure else "completed", "error": failure}
        receipts = output / "invocations"
        try:
            receipts.mkdir(exist_ok=True)
            write_once(receipts / f"{invocation_id}.json", receipt)
        except Exception as receipt_error:
            if failure is None:
                raise
            print(f"Could not preserve invocation receipt: {receipt_error}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
