"""Read-only inspection of frozen cached heatmaps; never changes predictions."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import io
import json
from pathlib import Path
import statistics
import time
import uuid

import cv2
import numpy as np

from . import nba_wasb_diagnostic as d
from . import nba_action_observation as action
from .nba_hard_example_diagnostic import validate_observations
from .wasb_adapter import affine_matrices
from .wasb_experiment import canonical

SCHEMA = "nba_saved_heatmap_inspection/v0.1"
RADIUS = 10


def load_saved_triplet(root, record, manifest, observations):
    """Read a bound archive once without creating or repairing any receipt."""
    path = d.contained(root, record["cache"]["path"])
    raw = path.read_bytes()
    binding = {"path": record["cache"]["path"], "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    d.require(all(binding[k] == value for k, value in record["cache"].items()), "Saved cache binding differs")
    receipt_path = path.with_suffix(".json")
    d.require(receipt_path.is_file(), "Missing original receipt; inspection will not repair it")
    receipt = d.read_json(receipt_path)
    with np.load(io.BytesIO(raw), allow_pickle=False) as archive:
        d.require(set(archive.files) == {"heatmaps", "metadata_json"}, "Unexpected cache archive inventory")
        values = archive["heatmaps"]
        metadata = json.loads(str(archive["metadata_json"].item()))
    d.validate_heatmaps(values)
    d.require(receipt == {**metadata, "cache": binding}, "Saved receipt/embedded metadata differs")
    identity = metadata["identity"]
    d.require(metadata["status"] == "completed" and canonical(identity) == record["original_identity_sha256"] and
              metadata["attempt_id"] == record["attempt_id"] and
              metadata["started_record"] == record["original_started_record"], "Original completed call identity differs")
    start = record["first_source_frame_index"]
    frame_map = {f["source_frame_index"]: f for f in manifest["frames"]}
    d.require(identity["frames"] == [frame_map[i] for i in range(start, start + 3)], "Cached native triple differs")
    for key in ("candidate_id", "game_id", "source_video", "time_base"):
        d.require(identity[key] == manifest[key], f"Cached {key} differs")
    d.require(identity["model_checkpoint"] == observations["checkpoint"] and identity["policy"] == d.POLICY,
              "Cached checkpoint/policy differs")
    if record["origin"] == "action_observation":
        d.require(identity["inference_code"] == observations["inference_code"] and
                  identity["proposal"] == observations["proposal"], "Action inference provenance differs")
    else:
        d.require(record["origin"] == "prior_pilot_import" and
                  identity["inference_code"] == observations["inference_code"]["diagnostic_producer"],
                  "Imported pilot inference provenance differs")
    started = d.read_json(d.bound(root, metadata["started_record"]))
    d.require(started["identity_sha256"] == canonical(identity) and started["attempt_id"] == metadata["attempt_id"],
              "Original call start differs")
    d.require(started["status"] == "started" and started["source_frame_indices"] == list(range(start, start + 3)),
              "Original started-call source frames differ")
    return values, {**binding, "receipt": d.binding(root, receipt_path), "origin": record["origin"],
                    "first_source_frame_index": start, "original_identity_sha256": record["original_identity_sha256"]}


def source_grid(width, height):
    """Map integer lattice locations using the same inverse as component centers."""
    _, inverse = affine_matrices(width, height)
    yy, xx = np.indices((288, 512), dtype=np.float32)
    grid = np.stack((xx, yy, np.ones_like(xx)), axis=-1).astype(np.float64) @ inverse.T
    return grid


def threshold_support(plane):
    # Explicitly retain OpenCV's float32 strict-threshold convention.
    return cv2.threshold(plane, .3, 1, cv2.THRESH_BINARY)[1].astype(np.uint8)


def plane_metrics(plane, grid, reference=None):
    """Raw response measurements; the reference disk never changes selection."""
    flat_index = int(np.argmax(plane))
    y, x = divmod(flat_index, plane.shape[1])
    support = threshold_support(plane)
    global_peak = float(plane[y, x])
    result = {"global_peak": global_peak, "global_peak_heatmap_xy": [x, y],
              "global_peak_source_xy_px": grid[y, x].tolist(), "global_peak_error_px": None,
              "global_peak_tie_pixels": int(np.count_nonzero(plane == plane[y, x])),
              "active_pixels_global": int(support.sum()), "local_peak": None, "local_peak_heatmap_xy": None,
              "local_peak_source_xy_px": None, "local_peak_error_px": None, "local_peak_tie_pixels": None,
              "local_to_global_peak_ratio": None, "local_disk_lattice_points": None,
              "active_pixels_in_reference_disk": None, "nearest_active_source_distance_px": None}
    if reference is None:
        return result
    distances = np.hypot(grid[:, :, 0] - reference[0], grid[:, :, 1] - reference[1])
    disk = distances <= RADIUS
    d.require(disk.any(), "Reference disk contains no mapped lattice locations")
    eligible = np.flatnonzero(disk)
    local_index = int(eligible[np.argmax(plane.ravel()[eligible])])
    ly, lx = divmod(local_index, plane.shape[1])
    local_peak = float(plane[ly, lx])
    active = support.astype(bool)
    result.update(global_peak_error_px=float(distances[y, x]), local_peak=local_peak,
                  local_peak_heatmap_xy=[lx, ly], local_peak_source_xy_px=grid[ly, lx].tolist(),
                  local_peak_error_px=float(distances[ly, lx]),
                  local_peak_tie_pixels=int(np.count_nonzero(disk & (plane == plane[ly, lx]))),
                  local_to_global_peak_ratio=local_peak / global_peak if global_peak else None,
                  local_disk_lattice_points=int(disk.sum()), active_pixels_in_reference_disk=int(np.count_nonzero(disk & active)),
                  nearest_active_source_distance_px=float(distances[active].min()) if active.any() else None)
    return result


def selected_component_metrics(mean, grid, observation, reference=None):
    selected = observation["selected_candidate_index"]
    if selected is None:
        return None
    _, labels = cv2.connectedComponents(threshold_support(mean), connectivity=8)
    mask = labels == selected + 1
    d.require(mask.any(), "Saved selected component has no reproduced support")
    ys, xs = np.where(mask)
    peak_offset = int(np.argmax(mean[ys, xs]))
    y, x = int(ys[peak_offset]), int(xs[peak_offset])
    candidate = observation["candidates"][selected]
    result = {"candidate_index": selected, "centroid_source_xy_px": observation["center_xy_px"],
              "native_mass": candidate["native_score"], "pixels": int(mask.sum()),
              "peak": float(mean[y, x]), "peak_heatmap_xy": [x, y], "peak_source_xy_px": grid[y, x].tolist(),
              "peak_tie_pixels": int(np.count_nonzero(mean[mask] == mean[y, x])),
              "bbox_heatmap_xyxy_inclusive": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
              "bbox_source_lattice_xyxy": [float(grid[mask, 0].min()), float(grid[mask, 1].min()),
                                           float(grid[mask, 0].max()), float(grid[mask, 1].max())],
              "centroid_error_px": None, "peak_error_px": None, "nearest_support_error_px": None,
              "active_pixels_in_reference_disk": None}
    if reference is not None:
        distances = np.hypot(grid[:, :, 0] - reference[0], grid[:, :, 1] - reference[1])
        result.update(centroid_error_px=float(np.hypot(candidate["center_x"] - reference[0], candidate["center_y"] - reference[1])),
                      peak_error_px=float(distances[y, x]), nearest_support_error_px=float(distances[mask].min()),
                      active_pixels_in_reference_disk=int(np.count_nonzero(mask & (distances <= RADIUS))))
    return result


def reconstruct_mean(contributions):
    """Exact original ascending float32 arithmetic, not a new aggregation rule."""
    d.require(contributions and [start for start, _ in contributions] == sorted({start for start, _ in contributions}),
              "Contributions must be unique and in original ascending-start order")
    mean = np.zeros((288, 512), np.float32)
    for _, plane in contributions:
        mean += plane
    return mean / np.float32(len(contributions))


def stats(values):
    values = [v for v in values if v is not None]
    return {"count": len(values), "min": min(values) if values else None,
            "median": statistics.median(values) if values else None,
            "mean": statistics.fmean(values) if values else None, "max": max(values) if values else None}


def summarize(rows):
    return {"frames": len(rows), "mean_global_peak": stats([r["mean"]["global_peak"] for r in rows]),
            "mean_local_peak": stats([r["mean"]["local_peak"] for r in rows]),
            "mean_local_to_global_ratio": stats([r["mean"]["local_to_global_peak_ratio"] for r in rows]),
            "mean_global_peak_error_px": stats([r["mean"]["global_peak_error_px"] for r in rows]),
            "local_active_support_frames": sum((r["mean"]["active_pixels_in_reference_disk"] or 0) > 0 for r in rows),
            "any_contributor_local_active_support_frames": sum(any((c["metrics"]["active_pixels_in_reference_disk"] or 0) > 0
                                                                   for c in r["contributors"]) for r in rows),
            "contributor_support_but_mean_no_local_support": sum(any((c["metrics"]["active_pixels_in_reference_disk"] or 0) > 0
                                                                   for c in r["contributors"]) and r["mean"]["active_pixels_in_reference_disk"] == 0 for r in rows),
            "global_peak_within_radius": sum(r["mean"]["global_peak_error_px"] is not None and r["mean"]["global_peak_error_px"] <= RADIUS for r in rows),
            "selected_component_peak_within_radius": sum(r["selected_component"] is not None and
                                                         r["selected_component"]["peak_error_px"] is not None and
                                                         r["selected_component"]["peak_error_px"] <= RADIUS for r in rows),
            "selected_component_support_within_radius": sum(r["selected_component"] is not None and
                                                            (r["selected_component"]["active_pixels_in_reference_disk"] or 0) > 0 for r in rows)}


def run(root, scope_path, output=None):
    root = Path(root).resolve()
    scope_path = (root / scope_path).resolve()
    scope = d.read_json(scope_path)
    d.require(scope["schema_version"] == "nba_saved_heatmap_inspection_scope/v0.1" and scope["status"] == "approved" and
              scope["authorization"]["approved_by"] == "Ryan", "Missing approved inspection scope")
    d.require(all(scope["authorization"][k] is False for k in ("new_model_inference", "training", "threshold_sweep", "new_prediction_policy", "label_changes")),
              "Unsupported inspection work")
    d.require(scope["measurements"]["localization_radius_source_px"] == RADIUS and
              scope["measurements"]["support_threshold_strict"] == .3, "Frozen measurement constants differ")
    output = d.contained(root, scope["output_root"]) if output is None else (root / output).resolve()
    d.require(output == d.contained(root, scope["output_root"]) and output.is_relative_to(root / "data/outputs") and
              not (output / "completion.json").exists(), "Preserve completed output or use approved output root")
    attempt = output / "attempts" / uuid.uuid4().hex
    code_files = [Path(__file__), Path(d.__file__), Path(action.__file__), root / "src/ball_tracking/wasb_adapter.py",
                  root / "src/ball_tracking/nba_hard_example_diagnostic.py", root / "src/ball_tracking/wasb_experiment.py"]
    bindings = {"scope": d.binding(root, scope_path), "authority": scope["authority"],
                "implementation": [d.binding(root, p) for p in code_files]}
    d.write_once(attempt / "started.json", {"status": "started", "at_utc": d.stamp(), "bindings": bindings})
    began = time.monotonic()
    cache_bindings, results, peak_cached_arrays = [], [], 0
    try:
        authority = {k: d.read_json(d.bound(root, v)) for k, v in scope["authority"].items()}
        report = authority["saved_score_report"]
        reference_map = {}
        for key in ("accepted_hard_reference", "accepted_pilot_reference"):
            accepted = authority[key]
            d.require(accepted["status"] == "human_accepted_assisted_reference", "References no longer accepted")
            for ref in accepted["references"]:
                d.require(ref["human_review"]["status"] == "accepted" and ref["origin"]["kind"] == "assistant_visual_proposal", "Reference origin differs")
                for frame, annotation in zip(ref["frames"], ref["annotations"]):
                    key2 = (ref["candidate_id"], frame["source_frame_index"])
                    d.require(key2 not in reference_map, "Repeated reference frame")
                    reference_map[key2] = (frame, annotation, ref)
        score_windows = {w["window_id"]: w for w in report["windows"]}
        targets = defaultdict(dict)
        for window in scope["windows"]:
            saved = score_windows[window["window_id"]]
            d.require(all(saved[k] == window[k] for k in ("window_id", "cohort", "candidate_id", "source_frame_range_inclusive")) and
                      len(saved["frame_results"]) == window["frames"], "Scope/score window inventory differs")
            for row in saved["frame_results"]:
                index = row["source_frame_index"]
                frame, annotation, ref = reference_map[(row["candidate_id"], index)]
                geometry = annotation["geometry"]
                d.require(row["source_pts_ticks"] == frame["source_pts_ticks"] and row["source_png"] == frame["png"] and
                          row["localization_eligible"] == annotation["localization_eligible"] and
                          row["reference_center_xy_px"] == (geometry["center_xy_px"] if geometry else None) and
                          row["annotation_uncertainty_radius_px"] == (geometry["uncertainty_radius_px"] if geometry else None),
                          "Saved score/reference mapping differs")
                d.require(index not in targets[row["candidate_id"]], "Repeated target frame")
                targets[row["candidate_id"]][index] = row
        d.require(sum(map(len, targets.values())) == scope["totals"]["frames"], "Target total differs")
        for source in scope["sources"]:
            candidate = source["candidate_id"]
            manifest = d.read_json(d.bound(root, source["input_manifest"]))
            observations = d.read_json(d.bound(root, source["observations"]))
            indexed = validate_observations(manifest, observations)
            d.require(observations["input_manifest"] == source["input_manifest"], "Frozen input authority differs")
            records = {r["first_source_frame_index"]: r for r in observations["triplet_caches"]}
            needed = {}
            for index in targets[candidate]:
                first, last = indexed[index]["segment_source_frame_range_inclusive"]
                needed[index] = [start for start in range(index - 2, index + 1) if first <= start <= last - 2]
                d.require(len(needed[index]) == indexed[index]["temporal_contributions"], "Original contribution count differs")
            starts = sorted({start for values in needed.values() for start in values})
            d.require(len(starts) == source["needed_unique_triplets"] and
                      sum(records[s]["cache"]["bytes"] for s in starts) == source["compressed_cache_bytes"], "Approved cache inventory differs")
            grid = source_grid(manifest["source_video"]["width_px"], manifest["source_video"]["height_px"])
            arrays = {}
            for offset, index in enumerate(sorted(targets[candidate])):
                row, observation = targets[candidate][index], indexed[index]
                for old in list(arrays):
                    if old < min(needed[index]):
                        del arrays[old]
                for start in needed[index]:
                    if start not in arrays:
                        arrays[start], bound = load_saved_triplet(root, records[start], manifest, observations)
                        cache_bindings.append({"candidate_id": candidate, **bound})
                peak_cached_arrays = max(peak_cached_arrays, len(arrays))
                contributions = [(s, arrays[s][index - s]) for s in needed[index]]
                mean = reconstruct_mean(contributions)
                mean_hash = hashlib.sha256(mean.tobytes()).hexdigest()
                d.require(mean_hash == observation["mean_heatmap_sha256"], "Original mean heatmap bytes differ")
                frame = reference_map[(candidate, index)][0]
                reconstructed = action.select_observation(frame, mean, len(contributions), manifest,
                    {"kind": observation["segment_kind"], "source_frame_range_inclusive": observation["segment_source_frame_range_inclusive"]})
                d.require(reconstructed == observation, "Frozen candidates or selected observation differ")
                reference = row["reference_center_xy_px"] if row["localization_eligible"] else None
                contributors = []
                for start, plane in contributions:
                    contributors.append({"triplet_first_source_frame_index": start, "channel": index - start,
                                         "target_source_pts_ticks": row["source_pts_ticks"],
                                         "origin": records[start]["origin"], "metrics": plane_metrics(plane, grid, reference)})
                result = {"window_id": row["window_id"], "cohort": row["cohort"], "candidate_id": candidate,
                          "game_id": row["game_id"], "approved_role": manifest["approved_role"],
                          "source_frame_index": index, "source_pts_ticks": row["source_pts_ticks"],
                          "time_base": row["time_base"], "source_png": row["source_png"], "outcome": row["outcome"],
                          "visibility": row["visibility"], "localization_eligible": row["localization_eligible"],
                          "reference_center_xy_px": reference, "annotation_uncertainty_radius_px": row["annotation_uncertainty_radius_px"],
                          "changed_pilot_context_edge": row["changed_pilot_context_edge"], "original_mean_sha256_verified": mean_hash,
                          "temporal_contributions": len(contributions), "mean": plane_metrics(mean, grid, reference),
                          "selected_component": selected_component_metrics(mean, grid, observation, reference), "contributors": contributors}
                results.append(result)
                if (offset + 1) % 100 == 0:
                    print(f"{candidate}: {offset + 1} exact means inspected", flush=True)
        d.require(len(cache_bindings) == scope["totals"]["needed_unique_triplets"] and
                  sum(c["bytes"] for c in cache_bindings) == scope["totals"]["compressed_cache_bytes"] and
                  len({c["path"] for c in cache_bindings}) == len(cache_bindings), "Executed cache inventory differs")
        grouped = defaultdict(list)
        for row in results:
            grouped[row["cohort"], row["outcome"]].append(row)
        payload = {"schema_version": SCHEMA, "status": "completed", "recorded_at_utc": d.stamp(), "bindings": bindings,
                   "scope_measurements": scope["measurements"], "limits": scope["limits"],
                   "accounting": {"frames": len(results), "unique_caches_read": len(cache_bindings),
                                  "compressed_cache_bytes": sum(c["bytes"] for c in cache_bindings),
                                  "peak_cached_triplet_arrays": peak_cached_arrays, "peak_triplet_array_bytes": peak_cached_arrays * 3 * 288 * 512 * 4,
                                  "original_means_and_candidate_inventories_verified": len(results),
                                  "model_calls": 0, "checkpoint_loads": 0, "training_runs": 0, "video_decodes": 0, "image_decodes": 0,
                                  "original_receipts_modified": False, "label_or_prediction_updates": False},
                   "cohorts": [{"cohort": c, "outcome": o, "summary": summarize(rows)} for (c, o), rows in sorted(grouped.items())],
                   "cache_bindings": cache_bindings, "frame_results": results}
        d.write_once(attempt / "report.json", payload)
        summary = {k: v for k, v in payload.items() if k not in ("frame_results", "cache_bindings")}
        d.write_once(attempt / "summary.json", summary)
        completion = {"schema_version": SCHEMA, "status": "completed", "elapsed_seconds": time.monotonic() - began,
                      "report": d.binding(root, attempt / "report.json"), "summary": d.binding(root, attempt / "summary.json"),
                      "accounting": payload["accounting"], "attempt": attempt.relative_to(root).as_posix()}
        d.write_once(attempt / "completed.json", completion)
        d.write_once(output / "completion.json", completion)
        return completion
    except Exception as error:
        d.write_once(attempt / "failed.json", {"status": "failed_preserved", "error_type": type(error).__name__, "error": str(error),
                                              "elapsed_seconds": time.monotonic() - began, "caches_read": len(cache_bindings),
                                              "frames_inspected": len(results)})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.root, args.scope, args.output), indent=2))


if __name__ == "__main__":
    main()
