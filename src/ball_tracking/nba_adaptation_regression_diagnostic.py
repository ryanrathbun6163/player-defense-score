"""Inspect a frozen old/new saved-heatmap scope without changing predictions."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
import math
from pathlib import Path
import time
import uuid

import numpy as np

from . import nba_action_observation as action
from . import nba_adaptation_comparison as comparison
from . import nba_saved_heatmap_diagnostic as metrics
from . import nba_wasb_diagnostic as d
from . import wasb_calibration
from .wasb_experiment import canonical

SCHEMA = "nba_adaptation_regression_diagnostic/v0.1"
SCOPE_SCHEMA = "nba_adaptation_regression_scope/v0.1"


def needed_starts(indices, limits):
    return sorted({s for i in indices for s in range(i - 2, i + 1) if limits[0] <= s <= limits[1] - 2})


def validate_scope(scope):
    d.require(scope["schema_version"] == SCOPE_SCHEMA and scope["status"] == "approved"
              and scope["authorization"]["approved_by"] == "Ryan", "Missing approved scope")
    d.require(all(scope["authorization"][key] is False for key in
                  ("new_model_inference", "training", "threshold_sweep", "label_changes", "prediction_changes", "video_or_source_png_decode")),
              "Unsupported scientific action")
    d.require(scope["policy"]["support_threshold_strict"] == .3 and
              scope["policy"]["localization_radius_source_px_inclusive"] == 10, "Changed fixed measurement rule")
    radius = scope["context_radius_native_frames"]
    d.require(type(radius) is int and radius >= 0, "Invalid context radius")
    d.require(len({s["candidate_id"] for s in scope["sources"]}) == len(scope["sources"]), "Repeated source")
    for source in scope["sources"]:
        anchors, limits = source["anchors"], source["original_context_inclusive"]
        d.require(source["kind"] in {"nba", "nfhs"} and len(set(anchors)) == len(anchors)
                  and all(type(a) is int and limits[0] <= a <= limits[1] for a in anchors), "Invalid anchor scope")
        indices = sorted({i for a in anchors for i in range(max(limits[0], a - radius), min(limits[1], a + radius) + 1)})
        d.require(source["source_frame_indices"] == indices, "Changed fixed frame scope")
        for arm in ("old", "new"):
            d.require([r["start"] for r in source["triplets"][arm]] == needed_starts(indices, limits),
                      "Missing or extra original contributors")
    totals = scope["totals"]
    d.require(totals["frames"] == sum(len(s["source_frame_indices"]) for s in scope["sources"])
              and totals["means"] == 2 * totals["frames"]
              and totals["anchors"] == sum(len(s["anchors"]) for s in scope["sources"])
              and totals["anchor_planes"] == 2 * totals["anchors"]
              and totals["triplet_bodies"] == sum(len(s["triplets"][a]) for s in scope["sources"] for a in ("old", "new")),
              "Changed fixed totals")


def read_bound(root, record):
    return d.read_json(comparison.bound(root, record))


def load_cache(root, descriptor, manifest, observations=None, nfhs_identity=None):
    """Read each producer format directly; never invoke a repairing cache loader."""
    path = d.contained(root, descriptor["cache"]["path"])
    raw = path.read_bytes()
    actual = {"path": descriptor["cache"]["path"], "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    d.require(actual == descriptor["cache"], "Cache binding differs")
    receipt = read_bound(root, descriptor["receipt"])
    d.require(Path(descriptor["receipt"]["path"]) == Path(descriptor["cache"]["path"]).with_suffix(".json"),
              "Cache sidecar path differs")
    with np.load(io.BytesIO(raw), allow_pickle=False) as saved:
        d.require(set(saved.files) == {"heatmaps", "metadata_json"}, "Unexpected triplet fields")
        values = saved["heatmaps"]
        metadata = json.loads(str(saved["metadata_json"].item()))
    d.validate_heatmaps(values)
    start = descriptor["start"]
    ids = list(range(start, start + 3))
    if descriptor["format"] == "nfhs_original":
        d.require(receipt == {**metadata, "sha256": actual["sha256"]}, "Original NFHS receipt differs")
        elapsed = metadata["inference_seconds"]
        d.require(metadata["input_frame_indices"] == ids and metadata["output_frame_indices"] == ids
                  and metadata["inference_identity_sha256"] == canonical(nfhs_identity), "Original NFHS identity differs")
        d.require(type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= 0, "Invalid original elapsed time")
        lineage = {"format": "nfhs_original", "identity_sha256": canonical(nfhs_identity),
                   "captured_png_and_pts_identity": False,
                   "historical_producer_threshold": nfhs_identity["inference"]["heatmap_threshold"],
                   "diagnostic_selection_threshold": .3}
    else:
        d.require(receipt == {**metadata, "cache": actual} and metadata["status"] == "completed", "Native receipt differs")
        record = descriptor["producer_record"]
        d.require(record["cache"] == actual and record["first_source_frame_index"] == start
                  and record["attempt_id"] == metadata["attempt_id"], "Native inventory differs")
        identity = metadata["identity"]
        frame_map = {f["source_frame_index"]: f for f in manifest["frames"]}
        d.require(identity["frames"] == [frame_map[i] for i in ids], "Native frame PNG/PTS identity differs")
        for key in ("candidate_id", "source_video", "time_base"):
            d.require(identity[key] == manifest[key], "Native source identity differs")
        d.require(identity["model_checkpoint"] == observations["checkpoint"] and identity["policy"] == d.POLICY,
                  "Native model/policy differs")
        if descriptor["format"] == "native_adaptation":
            d.require(identity == {**observations["identity"], "frames": [frame_map[i] for i in ids]}
                      and record["started_record"] == metadata["started_record"], "Adaptation inference identity differs")
        else:
            d.require(descriptor["format"] == "native_action" and canonical(identity) == record["original_identity_sha256"]
                      and record["original_started_record"] == metadata["started_record"], "Action origin identity differs")
            expected_code = observations["inference_code"] if record["origin"] == "action_observation" else observations["inference_code"]["diagnostic_producer"]
            d.require(identity["inference_code"] == expected_code, "Action inference provenance differs")
        begun = read_bound(root, metadata["started_record"])
        d.require(begun["identity_sha256"] == canonical(identity) and begun["attempt_id"] == metadata["attempt_id"]
                  and begun["status"] == "started" and begun["source_frame_indices"] == ids, "Original started-call record differs")
        lineage = {"format": descriptor["format"], "identity_sha256": canonical(identity),
                   "started_record": metadata["started_record"], "attempt_id": metadata["attempt_id"],
                   "captured_png_and_pts_identity": True}
    return values, {"start": start, "cache": actual, "receipt": descriptor["receipt"], **lineage}


def component_metrics(mean, grid, observation, reference, source_size):
    """Describe every original strict-threshold component without reranking output."""
    ordered = sorted(observation["candidates"], key=lambda c: (-c["native_score"], c["candidate_index"]))
    ranks = {c["candidate_index"]: rank + 1 for rank, c in enumerate(ordered)}
    result = []
    for candidate in observation["candidates"]:
        index = candidate["candidate_index"]
        view = {**observation, "selected_candidate_index": index,
                "center_xy_px": [candidate["center_x"], candidate["center_y"]]}
        value = metrics.selected_component_metrics(mean, grid, view, reference)
        value.update(mass_rank=ranks[index], selected=index == observation["selected_candidate_index"],
                     in_source_bounds=0 <= candidate["center_x"] < source_size[0] and 0 <= candidate["center_y"] < source_size[1],
                     centroid_within_reference_radius=value["centroid_error_px"] <= 10 if reference is not None else None,
                     peak_within_reference_radius=value["peak_error_px"] <= 10 if reference is not None else None)
        result.append(value)
    return result


def describe_plane(mean, contributions, grid, observation, annotation, fixed_locations, source_size):
    reference = annotation["geometry"]["center_xy_px"] if annotation["localization_eligible"] else None
    components = component_metrics(mean, grid, observation, reference, source_size)
    contributors = [{"triplet_first_source_frame_index": start, "channel": channel,
                     "metrics": metrics.plane_metrics(plane, grid, reference)} for start, channel, plane in contributions]
    mean_metrics = metrics.plane_metrics(mean, grid, reference)
    any_support = any((c["metrics"]["active_pixels_in_reference_disk"] or 0) > 0 for c in contributors)
    return {"mean_heatmap_sha256": hashlib.sha256(mean.tobytes()).hexdigest(), "mean_metrics": mean_metrics,
            "contributors": contributors, "components": components,
            "selected_component": next((c for c in components if c["selected"]), None),
            "matching_alternative_indices": [c["candidate_index"] for c in components if not c["selected"] and c["in_source_bounds"] and c["centroid_within_reference_radius"]],
            "averaging": {"any_contributor_local_support": any_support if reference is not None else None,
                          "support_lost_in_mean": (any_support and mean_metrics["active_pixels_in_reference_disk"] == 0) if reference is not None else None,
                          "local_peak_mean_minus_max_contributor": mean_metrics["local_peak"] - max(c["metrics"]["local_peak"] for c in contributors) if reference is not None else None},
            "fixed_selection_locations": {name: {"center_xy_px": center, "meaning": "diagnostic location, not a reference label",
                                                 "metrics": metrics.plane_metrics(mean, grid, center)}
                                          for name, center in fixed_locations.items() if center is not None},
            "original_observation": observation}


def source_records(root, source, authority):
    manifest = read_bound(root, source["input_manifest"])
    new = read_bound(root, source["new_observations"])
    if source["kind"] == "nba":
        old = read_bound(root, source["old_observations"])
        refs = authority["accepted_nba_hard_reference"]
        d.require(refs["status"] == "human_accepted_assisted_reference", "Reference is not accepted")
        annotations = {}; reference_frames = {}
        for ref in refs["references"]:
            if ref["candidate_id"] == source["candidate_id"]:
                d.require(ref["human_review"]["status"] == "accepted" and ref["source_video"] == manifest["source_video"], "Reference source/review differs")
                annotations.update({a["frame_index"]: a for a in ref["annotations"]})
                reference_frames.update({f["source_frame_index"]: f for f in ref["frames"]})
        bundle = identity = None
    else:
        window = source["window"]
        d.require(manifest["preparation_identity"]["window"]["source_video"] == window["source_video"]
                  and manifest["source_video"] == window["source_video"], "NFHS original source contract differs")
        for key in ("mean_heatmaps", "heatmap_receipt", "original_points", "inference_identity"):
            comparison.bound(root, window[key])
        for key in ("components", "points", "evaluation"):
            comparison.bound(root, source["baseline"][key])
        old = comparison.baseline_nfhs(root, window, manifest, source["baseline"])
        labels = read_bound(root, source["annotation"])
        d.require(labels["source_video"] == manifest["source_video"], "NFHS accepted reference source differs")
        annotations = {a["frame_index"]: a for a in labels["annotations"]}
        reference_frames = {f["source_frame_index"]: f for f in manifest["frames"]}
        identity = read_bound(root, source["original_identity"])
        d.require(identity["weights"]["sha256"] == d.EXPANDED_SHA, "Original NFHS checkpoint differs")
        d.require(identity["inference"]["heatmap_threshold"] == .5, "Original NFHS lineage differs")
        bundle = wasb_calibration.load_mean_heatmaps(root, window)
    d.require(new["candidate_id"] == old["candidate_id"] == manifest["candidate_id"] == source["candidate_id"], "Candidate mapping differs")
    d.require(new["checkpoint"] == authority["training_completion"]["checkpoint"], "Adapted checkpoint identity differs")
    frame_map = {f["source_frame_index"]: f for f in manifest["frames"]}
    for index in source["source_frame_indices"]:
        d.require(frame_map[index] == reference_frames[index], "Accepted frame PNG/PTS mapping differs")
    return manifest, old, new, annotations, bundle, identity


def analyze_source(root, source, authority, accounting, exported):
    manifest, old, new, annotations, bundle, identity = source_records(root, source, authority)
    maps = {arm: {r["source_frame_index"]: r for r in data["frames"]} for arm, data in (("old", old), ("new", new))}
    frames = {f["source_frame_index"]: f for f in manifest["frames"]}
    score_map = {r["source_frame_index"]: r for w in authority["comparison_score_report"]["windows"]
                 if w["candidate_id"] == source["candidate_id"] for r in w["frames"]}
    grid = metrics.source_grid(manifest["source_video"]["width_px"], manifest["source_video"]["height_px"])
    result = {i: {"candidate_id": source["candidate_id"], "source_frame_index": i, "source_frame": frames[i],
                  "source_video": manifest["source_video"], "annotation": annotations[i], "is_anchor": i in source["anchors"],
                  "anchor_contexts": [a for a in source["anchors"] if i in source["anchor_context_frames"][str(a)]], "old": None, "new": None}
              for i in source["source_frame_indices"]}
    for arm, data in (("old", old), ("new", new)):
        descriptors = {r["start"]: r for r in source["triplets"][arm]}
        arrays = {}
        for index in source["source_frame_indices"]:
            observation = maps[arm][index]
            limits = observation["segment_source_frame_range_inclusive"]
            d.require(limits == source["original_context_inclusive"], "Original context was shortened or changed")
            needed = needed_starts([index], limits)
            d.require(len(needed) == observation["temporal_contributions"], "Original contribution count differs")
            for expired in list(arrays):
                if expired not in needed: del arrays[expired]
            for start in needed:
                if start not in arrays:
                    arrays[start], binding = load_cache(root, descriptors[start], manifest, data, identity)
                    accounting["triplet_cache_reads"].append({"candidate_id": source["candidate_id"], "arm": arm, **binding})
            accounting["peak_rolling_triplet_arrays"] = max(accounting["peak_rolling_triplet_arrays"], len(arrays))
            contributions = [(s, arrays[s][index - s]) for s in needed]
            mean = metrics.reconstruct_mean(contributions)
            reproduced = action.select_observation(frames[index], mean, len(needed), manifest,
                {"kind": observation["segment_kind"], "source_frame_range_inclusive": limits})
            if arm == "old" and source["kind"] == "nfhs":
                d.require(np.array_equal(mean, bundle[index - limits[0]]), "Original NFHS saved mean bytes differ")
                d.require(all(reproduced[k] == observation[k] for k in reproduced if k != "mean_heatmap_sha256"),
                          "Original NFHS 0.3 components/selection differ")
            else:
                d.require(reproduced == observation, "Original native mean/candidates/selection differ")
            ref = {**manifest, "frames": [frames[index]], "annotations": [annotations[index]]}
            score = d.score_reference(ref, {"frames": [observation]})["frame_results"][0]
            d.require(score == score_map[index][arm], "Original score parity differs")
            locations = {name + "_selected_center": maps[name][index]["center_xy_px"] for name in ("old", "new")}
            description = describe_plane(mean, [(s, index - s, p) for s, p in contributions], grid, observation, annotations[index], locations,
                                         (manifest["source_video"]["width_px"], manifest["source_video"]["height_px"]))
            description["original_score"] = score
            result[index][arm] = description
            if index in source["anchors"]:
                exported.append(({"candidate_id": source["candidate_id"], "source_frame_index": index,
                                  "arm": arm, "mean_heatmap_sha256": description["mean_heatmap_sha256"]}, mean.copy()))
    if bundle is not None:
        accounting["old_nfhs_mean_bundles"].append({**source["original_mean_bundle"], "stored_planes_loaded": len(bundle),
                                                    "selected_planes_measured": len(result), "decoded_array_bytes": bundle.nbytes})
    return list(result.values())


def anchor_summary(rows):
    anchors = []
    for row in rows:
        if not row["is_anchor"]: continue
        item = {"candidate_id": row["candidate_id"], "source_frame_index": row["source_frame_index"]}
        for arm in ("old", "new"):
            value = row[arm]
            item[arm] = {"score": value["original_score"], "mean": value["mean_metrics"],
                         "selected_component": value["selected_component"], "matching_alternative_indices": value["matching_alternative_indices"],
                         "averaging": value["averaging"], "fixed_selection_locations": value["fixed_selection_locations"]}
        item["local_peak_delta_new_minus_old"] = row["new"]["mean_metrics"]["local_peak"] - row["old"]["mean_metrics"]["local_peak"] if row["old"]["mean_metrics"]["local_peak"] is not None else None
        anchors.append(item)
    return anchors


def run(root, scope_path):
    root = Path(root).resolve(); scope_path = (root / scope_path).resolve()
    scope = d.read_json(scope_path); validate_scope(scope)
    output = d.contained(root, scope["output_root"])
    d.require(output.is_relative_to(root / "data/outputs") and not (output / "completion.json").exists(), "Preserve completed diagnostic")
    attempt = output / "attempts" / uuid.uuid4().hex
    bindings = {"scope": d.binding(root, scope_path), "authority": scope["authority"],
                "implementation": [d.binding(root, Path(module.__file__)) for module in
                                   (metrics, d, action, comparison, wasb_calibration)] + [d.binding(root, Path(__file__))]}
    began = time.monotonic()
    accounting = {"triplet_cache_reads": [], "old_nfhs_mean_bundles": [], "peak_rolling_triplet_arrays": 0,
                  "model_calls": 0, "checkpoint_loads": 0, "source_png_decode_events": 0, "video_decode_events": 0}
    d.write_once(attempt / "started.json", {"status": "started", "at_utc": d.stamp(), "bindings": bindings})
    try:
        authority = {k: read_bound(root, v) for k, v in scope["authority"].items()}
        rows, exported = [], []
        for source in scope["sources"]:
            radius = scope["context_radius_native_frames"]; limits = source["original_context_inclusive"]
            contexts = {str(a): list(range(max(limits[0], a-radius), min(limits[1], a+radius)+1)) for a in source["anchors"]}
            rows.extend(analyze_source(root, {**source, "anchor_context_frames": contexts}, authority, accounting, exported))
        expected = scope["totals"]
        d.require(len(rows) == expected["frames"] and len(exported) == expected["anchor_planes"]
                  and len(accounting["triplet_cache_reads"]) == expected["triplet_bodies"], "Final inventory differs")
        totals = Counter(f"{r['old']['original_score']['outcome']} -> {r['new']['original_score']['outcome']}" for r in rows)
        anchors = anchor_summary(rows)
        losses = sum(a["old"]["score"]["outcome"] == "matched" and a["new"]["score"]["outcome"] != "matched" for a in anchors)
        recoveries = sum(a["old"]["score"]["outcome"] != "matched" and a["new"]["score"]["outcome"] == "matched" for a in anchors)
        d.require(losses == expected["anchor_losses"] and recoveries == expected["anchor_recoveries"], "Original anchor losses/recoveries differ")
        plane_path = attempt / "anchor_mean_heatmaps.npz"
        with plane_path.open("xb") as stream: np.savez_compressed(stream, heatmaps=np.stack([p for _, p in exported]))
        accounting.update(triplet_compressed_bytes_read=sum(c["cache"]["bytes"] for c in accounting["triplet_cache_reads"]),
                          peak_rolling_triplet_array_bytes=accounting["peak_rolling_triplet_arrays"] * 3 * 288 * 512 * 4,
                          retained_anchor_plane_bytes=sum(p.nbytes for _, p in exported),
                          memory_note="Array inventories are not total process RAM; one NFHS 25-plane bundle is loaded at a time.")
        summary = {"frames": len(rows), "old_new_means": 2 * len(rows), "original_parity_checks_passed": 2 * len(rows),
                   "transitions": dict(totals), "anchor_count": len(anchors), "anchor_losses": losses, "anchor_recoveries": recoveries, "anchors": anchors,
                   "limitations": scope["limitations"]}
        report = {"schema_version": SCHEMA, "status": "completed", "bindings": bindings, "frames": rows,
                  "summary": summary, "resources": accounting, "anchor_mean_heatmaps": d.binding(root, plane_path),
                  "anchor_planes": [{"index": i, **info} for i, (info, _) in enumerate(exported)],
                  "elapsed_seconds": time.monotonic() - began, "prediction_or_label_changes": False}
        d.write_once(attempt / "report.json", report); d.write_once(attempt / "summary.json", summary)
        completion = {"schema_version": SCHEMA, "status": "completed", "report": d.binding(root, attempt / "report.json"),
                      "summary": d.binding(root, attempt / "summary.json"), "anchor_mean_heatmaps": report["anchor_mean_heatmaps"],
                      "bindings": bindings, "elapsed_seconds": time.monotonic() - began}
        d.write_once(attempt / "completed.json", completion); d.write_once(output / "completion.json", completion)
        return completion
    except Exception as error:
        d.write_once(attempt / "failed.json", {"status": "failed_preserved", "error_type": type(error).__name__,
                      "error": str(error), "elapsed_seconds": time.monotonic() - began, "resources": accounting})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", required=True); parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run: parser.error("Explicit --run required")
    print(json.dumps(run(Path.cwd(), args.scope), indent=2))


if __name__ == "__main__": main()
