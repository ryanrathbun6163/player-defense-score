"""Measure a label-blind saved-component pool; never select new predictions."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
import uuid

import numpy as np

from . import nba_adaptation_regression_diagnostic as saved
from . import nba_action_observation as action
from . import nba_saved_heatmap_diagnostic as metrics
from . import nba_wasb_diagnostic as d
from .wasb_adapter import components_from_heatmap

SCHEMA = "nba_candidate_preservation/v0.1"
POLICY = {
    "threshold_strict": .3, "localization_radius_source_px_inclusive": 10, "connectivity": 8,
    "mean_policy": "unchanged original ascending float32 complete contributor context",
    "pool": "all original mean records plus every in-image component from each original contributor plane",
    "coordinate_groups": "exact Python float (center_x, center_y) equality; preserve every provenance member; not unique balls",
    "approximate_deduplication": False, "nms": False, "selection_changes": False,
    "in_image": "0 <= x < source width and 0 <= y < source height",
    "burden_quantile": "numpy.percentile with method=linear",
    "ambiguity": "eligible frame with at least one matching and at least one nonmatching in-image coordinate; diagnostic only",
    "hidden": "not_visible with certain/probable game-ball identity; other ineligible rows remain unknown",
}


def in_image(center, size):
    return 0 <= center[0] < size[0] and 0 <= center[1] < size[1]


def coordinate_groups(records):
    groups, positions = [], {}
    for index, record in enumerate(records):
        center = tuple(float(record["component"][k]) for k in ("center_x", "center_y"))
        if center not in positions:
            positions[center] = len(groups)
            groups.append({"center_xy_px": list(center), "record_indices": []})
        groups[positions[center]]["record_indices"].append(index)
    return groups


def build_pool(arm, source_id, frame_index, observation, contributions, source_size):
    """No labels enter this function; original mean records form the exact prefix."""
    records = []
    def add(kind, start, channel, component):
        center = [component["center_x"], component["center_y"]]
        records.append({"provenance_id": [arm, source_id, frame_index, kind, start, channel, component["candidate_index"]],
                        "component": dict(component), "in_source_bounds": in_image(center, source_size)})
    for component in observation["candidates"]: add("mean", None, None, component)
    mean_count = len(records); planes = []
    for start, channel, plane in contributions:
        components = components_from_heatmap(plane, *source_size, threshold=.3)
        retained = []
        for index, component in enumerate(components):
            if in_image([component["center_x"], component["center_y"]], source_size):
                retained.append(index); add("contributor", start, channel, {"candidate_index": index, **component})
        planes.append({"triplet_first_source_frame_index": start, "channel": channel,
                       "heatmap_sha256": hashlib.sha256(plane.tobytes()).hexdigest(),
                       "original_component_count": len(components), "retained_component_indices": retained})
    return {"mean_record_count": mean_count, "records": records, "coordinate_groups": coordinate_groups(records),
            "contributor_planes": planes}


def eligibility(annotation):
    if annotation["localization_eligible"]: return "eligible"
    if annotation["visibility"] == "not_visible" and annotation["game_ball_identity_certainty"] in {"certain", "probable"}: return "hidden"
    return "unknown"


def measure_pool(records, annotation):
    groups = coordinate_groups(records)
    inside = [r for r in records if r["in_source_bounds"]]
    inside_groups = [g for g in groups if records[g["record_indices"][0]]["in_source_bounds"]]
    category = eligibility(annotation)
    result = {"raw_records": len(records), "exact_coordinates": len(groups), "in_image_records": len(inside),
              "in_image_exact_coordinates": len(inside_groups), "out_of_image_records": len(records)-len(inside),
              "available": None, "matching_records": None, "nonmatching_in_image_records": None,
              "matching_coordinates": None, "nonmatching_in_image_coordinates": None,
              "ambiguous": None, "wrong_only": None, "empty": not inside,
              "hidden_nonempty": bool(inside) if category == "hidden" else None}
    if category == "eligible":
        target = annotation["geometry"]["center_xy_px"]
        matches = lambda xy: bool(np.hypot(xy[0]-target[0], xy[1]-target[1]) <= 10)
        matching = sum(matches([r["component"]["center_x"], r["component"]["center_y"]]) for r in inside)
        matching_groups = sum(matches(g["center_xy_px"]) for g in inside_groups)
        result.update(available=bool(matching), matching_records=matching,
                      nonmatching_in_image_records=len(inside)-matching, matching_coordinates=matching_groups,
                      nonmatching_in_image_coordinates=len(inside_groups)-matching_groups,
                      ambiguous=bool(matching_groups and len(inside_groups)>matching_groups),
                      wrong_only=bool(inside and not matching))
    return result


def evaluate_pool(pool, annotation):
    mean = measure_pool(pool["records"][:pool["mean_record_count"]], annotation)
    union = measure_pool(pool["records"], annotation)
    eligible = eligibility(annotation) == "eligible"; hidden = eligibility(annotation) == "hidden"
    result = {"mean": mean, "union": union,
              "newly_available": bool(union["available"] and not mean["available"]) if eligible else None,
              "lost_availability": bool(mean["available"] and not union["available"]) if eligible else None,
              "newly_ambiguous": bool(union["ambiguous"] and not mean["ambiguous"]) if eligible else None,
              "newly_nonempty_hidden": bool(union["hidden_nonempty"] and not mean["hidden_nonempty"]) if hidden else None,
              "incremental_raw_records": union["raw_records"]-mean["raw_records"],
              "incremental_exact_coordinates": union["exact_coordinates"]-mean["exact_coordinates"],
              **{"incremental_" + k: union[k]-mean[k] if eligible else None
                 for k in ("nonmatching_in_image_records", "nonmatching_in_image_coordinates")}}
    d.require(not result["lost_availability"], "Mean-pool subset invariant failed")
    return result


def load_plan(root, scope_path):
    scope = d.read_json(scope_path)
    d.require(scope["schema_version"] == "nba_candidate_preservation_scope/v0.1" and scope["status"] == "approved"
              and scope["authorization"]["approved_by"] == "Ryan", "Missing approved scope")
    d.require(scope["policy"] == POLICY, "Declared pool policy differs from implementation")
    d.require(all(scope["authorization"][k] is False for k in ("new_model_inference", "training", "threshold_sweep",
              "label_changes", "prediction_changes", "source_png_or_video_decode")), "Unsupported scientific work")
    authority = {k: saved.read_bound(root, v) for k, v in scope["authority"].items()}
    inventory = saved.read_bound(root, scope["cache_inventory"])
    d.require(inventory["schema_version"] == "nba_candidate_preservation_cache_inventory/v0.1", "Cache inventory schema differs")
    contract = scope["reference_container_contract"]; references = []
    for key in ("accepted_nba_hard_reference", "accepted_nba_pilot_reference"):
        record = authority[key]
        d.require(all(record.get(k) == v for k, v in contract.items()), "Actual accepted reference container differs")
        references.extend(record["references"])
    keys = [(r["candidate_id"], f["source_frame_index"]) for r in references for f in r["frames"]]
    d.require(len(keys) == len(set(keys)), "Accepted reference sets overlap")
    # A validated in-memory view for the existing source loader; both originals remain independently bound.
    authority["accepted_nba_hard_reference"] = {**authority["accepted_nba_hard_reference"], "references": references}
    sources = {s["candidate_id"]: s for s in scope["sources"]}
    caches = {s["candidate_id"]: s["triplets"] for s in inventory["sources"]}
    d.require(len(sources) == len(scope["sources"]) and set(caches) == set(sources), "Source inventory differs")
    window_map = {}
    for window in scope["windows"]:
        for index in window["source_frame_indices"]:
            key = window["candidate_id"], index
            d.require(key not in window_map, "Duplicate scored frame")
            window_map[key] = window
    total = scope["totals"]
    d.require(len(window_map) == total["frames"] and total["frame_arm_rows"] == 2 * total["frames"], "Scope total differs")
    for cid, source in sources.items():
        d.require(source["source_frame_indices"] == sorted(i for c, i in window_map if c == cid), "Window/source frames differ")
        needed = saved.needed_starts(source["source_frame_indices"], source["original_context_inclusive"])
        for arm in ("old", "new"):
            d.require([r["start"] for r in caches[cid][arm]] == needed and len(needed) == source["expected_triplets_per_arm"], "Original cache contributor inventory differs")
    descriptors = [r for data in caches.values() for arm in ("old", "new") for r in data[arm]]
    d.require(len(descriptors) == total["unique_triplet_bodies"] and sum(r["cache"]["bytes"] for r in descriptors) == total["triplet_compressed_bytes"], "Bound cache resource inventory differs")
    screen = scope["usefulness_screen"]
    d.require(screen["primary_arm"] == "old" and type(screen["minimum_newly_available_non_anchor_per_group"]) is int
              and screen["minimum_newly_available_non_anchor_per_group"] >= 1
              and set(screen["groups"]) <= {s["analysis_group"] for s in sources.values()}, "Invalid configured usefulness screen")
    return scope, authority, caches, window_map


def analyze_source(root, source, authority, descriptors, windows, prior, resources):
    manifest, old, new, annotations, bundle, identity = saved.source_records(root, source, authority)
    frames = {f["source_frame_index"]: f for f in manifest["frames"]}
    indexed = {a: {r["source_frame_index"]: r for r in obs["frames"]} for a, obs in (("old", old), ("new", new))}
    scores = {r["source_frame_index"]: r for w in authority["comparison_score_report"]["windows"] if w["candidate_id"] == source["candidate_id"] for r in w["frames"]}
    size = manifest["source_video"]["width_px"], manifest["source_video"]["height_px"]
    rows = {}
    for index in source["source_frame_indices"]:
        window = windows[source["candidate_id"], index]; key = source["candidate_id"], index
        rows[index] = {"candidate_id": source["candidate_id"], "source_frame_index": index, "source_frame": frames[index],
            "source_video": manifest["source_video"], "window_id": window["window_id"], "cohort": window["cohort"],
            "analysis_group": window["analysis_group"], "is_control": window["is_control"], "annotation": annotations[index],
            "eligibility": eligibility(annotations[index]), "is_prior_anchor": key in prior["anchors"],
            "inside_prior_context": key in prior["context"]}
    for arm, observations in (("old", old), ("new", new)):
        records = {r["start"]: r for r in descriptors[arm]}; arrays = {}
        for index in source["source_frame_indices"]:
            observation = indexed[arm][index]; limits = observation["segment_source_frame_range_inclusive"]
            d.require(limits == source["original_context_inclusive"], "Original context changed")
            starts = saved.needed_starts([index], limits)
            d.require(len(starts) == observation["temporal_contributions"], "Original temporal contribution count differs")
            for expired in list(arrays):
                if expired not in starts: del arrays[expired]
            for start in starts:
                if start not in arrays:
                    resources["attempted_cache_reads"] += 1
                    arrays[start], binding = saved.load_cache(root, records[start], manifest, observations, identity)
                    resources["triplet_cache_reads"].append({"candidate_id": source["candidate_id"], "arm": arm, **binding})
            resources["peak_rolling_triplet_arrays"] = max(resources["peak_rolling_triplet_arrays"], len(arrays))
            means_input = [(s, arrays[s][index-s]) for s in starts]
            mean = metrics.reconstruct_mean(means_input)
            reproduced = action.select_observation(frames[index], mean, len(starts), manifest,
                {"kind": observation["segment_kind"], "source_frame_range_inclusive": limits})
            if arm == "old" and source["kind"] == "nfhs":
                d.require(mean.tobytes() == bundle[index-limits[0]].tobytes(), "Original NFHS mean bytes differ")
                d.require(all(reproduced[k] == observation[k] for k in reproduced if k != "mean_heatmap_sha256"), "Original NFHS 0.3 selection differs")
            else: d.require(reproduced == observation, "Original native mean/candidates/selection differ")
            reference = {**manifest, "frames": [frames[index]], "annotations": [annotations[index]]}
            score = d.score_reference(reference, {"frames": [observation]})["frame_results"][0]
            d.require(score == scores[index][arm], "Original selected score changed")
            pool = build_pool(arm, source["candidate_id"], index, observation, [(s, index-s, p) for s, p in means_input], size)
            measured = evaluate_pool(pool, annotations[index])
            d.require(not annotations[index]["localization_eligible"] or measured["mean"]["available"] == score["raw_candidate_available"], "Original mean-pool availability differs")
            d.require([r["component"] for r in pool["records"][:pool["mean_record_count"]]] == observation["candidates"], "Original mean records changed")
            rows[index][arm] = {"mean_heatmap_sha256": reproduced["mean_heatmap_sha256"], "pool": pool,
                "evaluation": measured, "original_score": score,
                "original_selected": {k: observation[k] for k in ("state", "selected_candidate_index", "center_xy_px", "native_score")}}
            resources["contributor_planes_measured"] += len(starts)
    if bundle is not None:
        resources["old_nfhs_mean_bundles"].append({**source["original_mean_bundle"], "stored_planes_loaded": len(bundle), "selected_planes_verified": len(rows), "array_bytes": bundle.nbytes})
    return list(rows.values())


def distribution(values):
    return {"count": len(values), "median": float(np.median(values)) if values else None,
            "p95": float(np.percentile(values, 95, method="linear")) if values else None, "max": max(values) if values else None}


def aggregate(rows):
    result = {"frames": len(rows), "eligibility": dict(Counter(r["eligibility"] for r in rows)), "arms": {}}
    for arm in ("old", "new"):
        values = [r[arm]["evaluation"] for r in rows]; eligible = [r for r in rows if r["eligibility"] == "eligible"]
        value = {"mean_available": sum(bool(v["mean"]["available"]) for v in values),
                 "union_available": sum(bool(v["union"]["available"]) for v in values),
                 **{k: sum(bool(v[k]) for v in values) for k in ("newly_available", "lost_availability", "newly_ambiguous", "newly_nonempty_hidden")},
                 "newly_available_non_anchor": sum(bool(r[arm]["evaluation"]["newly_available"]) and not r["is_prior_anchor"] for r in rows),
                 "newly_available_outside_prior_context": sum(bool(r[arm]["evaluation"]["newly_available"]) and not r["inside_prior_context"] for r in rows),
                 "residual_unavailable": sum(not r[arm]["evaluation"]["union"]["available"] for r in eligible),
                 "newly_available_frames": [{"candidate_id": r["candidate_id"], "source_frame_index": r["source_frame_index"]} for r in rows if r[arm]["evaluation"]["newly_available"]]}
        for name in ("mean", "union"):
            for metric in ("hidden_nonempty", "ambiguous", "wrong_only"):
                value[name + "_" + metric] = sum(bool(v[name][metric]) for v in values)
            value[name + "_empty_eligible"] = sum(r[arm]["evaluation"][name]["empty"] for r in eligible)
        value["candidate_burden"] = {name + "_" + metric: distribution([v[name][metric] for v in values])
            for name in ("mean", "union") for metric in ("raw_records", "exact_coordinates", "in_image_records", "in_image_exact_coordinates")}
        value["candidate_burden"].update({k: distribution([v[k] for v in values]) for k in ("incremental_raw_records", "incremental_exact_coordinates")})
        value["eligible_candidate_composition"] = {name + "_" + metric: distribution([r[arm]["evaluation"][name][metric] for r in eligible])
            for name in ("mean", "union") for metric in ("matching_records", "nonmatching_in_image_records", "matching_coordinates", "nonmatching_in_image_coordinates")}
        value["eligible_candidate_composition"].update({k: distribution([r[arm]["evaluation"][k] for r in eligible])
            for k in ("incremental_nonmatching_in_image_records", "incremental_nonmatching_in_image_coordinates")})
        already_hidden = [v for v in values if v["mean"]["hidden_nonempty"]]
        value["hidden_already_nonempty_burden"] = {"frames": len(already_hidden),
            **{k: distribution([v[k] for v in already_hidden]) for k in ("incremental_raw_records", "incremental_exact_coordinates")}}
        value["mean_to_union_availability_transitions"] = dict(Counter(f"{r[arm]['evaluation']['mean']['available']} -> {r[arm]['evaluation']['union']['available']}" for r in eligible))
        result["arms"][arm] = value
    for pool in ("mean", "union"):
        result["old_to_new_" + pool + "_availability_transitions"] = dict(Counter(f"{r['old']['evaluation'][pool]['available']} -> {r['new']['evaluation'][pool]['available']}" for r in rows if r["eligibility"] == "eligible"))
    result["original_selected_outcome_transitions"] = dict(Counter(f"{r['old']['original_score']['outcome']} -> {r['new']['original_score']['outcome']}" for r in rows))
    return result


def summarize(rows, scope):
    groups = {name: aggregate([r for r in rows if r["analysis_group"] == name]) for name in dict.fromkeys(r["analysis_group"] for r in rows)}
    for name, group in groups.items():
        for arm in ("old", "new"):
            d.require(group["arms"][arm]["mean_available"] == scope["expected_mean_pool_available"][name][arm], "Original mean-pool baseline total differs")
    controls = aggregate([r for r in rows if r["is_control"]])
    d.require(all(controls["arms"][a]["lost_availability"] == 0 for a in ("old", "new")), "Control mean-subset invariant failed")
    screen = scope["usefulness_screen"]; arm = screen["primary_arm"]
    conditions = {group: groups[group]["arms"][arm]["newly_available_non_anchor"] >= screen["minimum_newly_available_non_anchor_per_group"] for group in screen["groups"]}
    passed = all(conditions.values())
    return {"overall": aggregate(rows), "by_analysis_group": groups,
            "by_window": {name: aggregate([r for r in rows if r["window_id"] == name]) for name in dict.fromkeys(r["window_id"] for r in rows)},
            "controls_included_subset": controls,
            "by_visibility": {name: aggregate([r for r in rows if r["annotation"]["visibility"] == name]) for name in sorted({r["annotation"]["visibility"] for r in rows})},
            "by_eligibility": {name: aggregate([r for r in rows if r["eligibility"] == name]) for name in ("eligible", "hidden", "unknown")},
            "usefulness_screen": {"passed": passed, "conditions": conditions, "primary_arm": arm,
                "meaning": screen["pass_meaning"] if passed else screen["fail_meaning"], "candidate_or_model_promoted": False,
                "costs": screen["costs"]}, "limits": scope["limits"]}


def run(root, scope_path):
    root = Path(root).resolve(); scope_path = (root / scope_path).resolve()
    scope, authority, caches, windows = load_plan(root, scope_path)
    output = d.contained(root, scope["output_root"]); d.require(output.is_relative_to(root / "data/outputs"), "Output outside ignored data")
    output.mkdir(parents=True, exist_ok=True); lock = d.acquire_run_lock(output / '.run.lock')
    attempt = output / 'attempts' / uuid.uuid4().hex; began = time.monotonic()
    resources = {"triplet_cache_reads": [], "attempted_cache_reads": 0, "old_nfhs_mean_bundles": [],
                 "peak_rolling_triplet_arrays": 0, "contributor_planes_measured": 0,
                 "model_calls": 0, "checkpoint_loads": 0, "source_png_decode_events": 0, "video_decode_events": 0}
    try:
        d.require(not (output / 'completion.json').exists(), "Preserve completed experiment")
        files = ['nba_candidate_preservation.py', 'nba_adaptation_regression_diagnostic.py', 'nba_saved_heatmap_diagnostic.py',
                 'nba_action_observation.py', 'nba_adaptation_comparison.py', 'nba_wasb_diagnostic.py', 'wasb_calibration.py', 'wasb_adapter.py', 'wasb_experiment.py', 'nba_annotations.py']
        bindings = {"scope": d.binding(root, scope_path), "cache_inventory": scope["cache_inventory"], "authority": scope["authority"],
                    "implementation": [d.binding(root, Path(__file__).with_name(name)) for name in files],
                    "focused_tests": d.binding(root, root / 'tests/test_nba_candidate_preservation.py')}
        d.write_once(attempt / 'started.json', {"status": "started", "at_utc": d.stamp(), "bindings": bindings})
        previous = authority["previous_diagnostic_scope"]
        prior = {"anchors": {(s["candidate_id"], i) for s in previous["sources"] for i in s["anchors"]},
                 "context": {(s["candidate_id"], i) for s in previous["sources"] for i in s["source_frame_indices"]}}
        rows = []
        for source in scope["sources"]:
            rows.extend(analyze_source(root, source, authority, caches[source["candidate_id"]], windows, prior, resources))
        total = scope["totals"]
        d.require(len(rows) == total["frames"] and len(resources["triplet_cache_reads"]) == total["unique_triplet_bodies"]
                  and resources["contributor_planes_measured"] == total["contributor_planes_both_arms"], "Executed inventory differs")
        d.require(Counter(r["eligibility"] for r in rows) == {k: total[k] for k in ("eligible", "hidden", "unknown")}, "Reference eligibility inventory differs")
        summary = summarize(rows, scope)
        resources.update(triplet_compressed_bytes_read=sum(r["cache"]["bytes"] for r in resources["triplet_cache_reads"]),
                         rolling_triplet_array_inventory_bytes=resources["peak_rolling_triplet_arrays"] * 3 * 288 * 512 * 4,
                         memory_note="Rolling array inventory is not total process RAM; one 25-plane old NFHS mean bundle at a time.")
        report = {"schema_version": SCHEMA, "status": "completed", "bindings": bindings, "policy": POLICY, "frames": rows,
                  "summary": summary, "resources": resources, "original_predictions_and_scores_unchanged": True}
        d.write_once(attempt / 'report.json', report); d.write_once(attempt / 'summary.json', summary)
        completion = {"schema_version": SCHEMA, "status": "completed", "report": d.binding(root, attempt / 'report.json'),
                      "summary": d.binding(root, attempt / 'summary.json'), "bindings": bindings, "elapsed_seconds": time.monotonic()-began}
        d.write_once(attempt / 'completed.json', completion); d.write_once(output / 'completion.json', completion)
        return completion
    except Exception as error:
        d.write_once(attempt / 'failed.json', {"status": "failed_preserved", "error_type": type(error).__name__, "error": str(error),
                     "resources": resources, "elapsed_seconds": time.monotonic()-began})
        raise
    finally: d.release_run_lock(lock)


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--scope', required=True)
    parser.add_argument('--run', action='store_true'); parser.add_argument('--check-scope', action='store_true'); args = parser.parse_args()
    if args.run == args.check_scope: parser.error('Choose exactly one of --run or --check-scope')
    root = Path.cwd(); path = root / args.scope
    if args.check_scope:
        scope, _, _, _ = load_plan(root, path); print(json.dumps({"status": "scope_metadata_verified", "scope": d.binding(root, path), "totals": scope['totals']}, indent=2))
    else: print(json.dumps(run(root, path), indent=2))


if __name__ == '__main__': main()
