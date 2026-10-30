"""Apply the frozen gap selector to bound, complete development contexts.

Only geometrically admissible original gaps consume saved contributor arrays.
No model, decoder or repairing cache loader is called. Labels enter after an
immutable selection is published. Protected NFHS slots have no observations.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import time
import uuid

from . import nba_action_observation as action
from . import nba_adaptation_regression_diagnostic as saved
from . import nba_candidate_preservation as pools
from . import nba_saved_heatmap_diagnostic as metrics
from . import nba_temporal_gap_selection as selector
from . import nba_wasb_diagnostic as d
from . import wasb_development_observation as nfhs

SCHEMA = "nba_temporal_gap_continuous/v0.1"
SCOPE_SCHEMA = "nba_temporal_gap_continuous_scope/v0.1"
TOTALS = {"processed_frames": 3975, "segments": 8, "protected_frames": 225,
          "timeline_frames": 4200, "available_triplets": 3959, "scored_frames": 790}
ADDITIONAL_CONDITIONS = {"det_matched_min": 209, "same_context_nfhs_matched_min": 131,
    "no_new_wrong_frames": True, "no_new_hidden_alarm_frames": True, "no_lost_correct_positions": True,
    "all_original_points_immutable": True,
    "accepted_additions_retained": [["sas_det_q1_c02", 11437], ["sas_det_q1_c02", 11438], ["possession_001", 208]],
    "same_context_nfhs_baseline_matched_wrong_missing_hidden_alarm": [131, 1, 13, 0],
    "new_human_trajectory_review_required": True}
NBA_CONFIG = "configs/ball_tracking/selections/nba_wasb_action_observation_proposal_v0_1.json"
NFHS_CONFIG = "configs/ball_tracking/wasb_experiments/wasb_expanded_development_observation_v0_1.json"


def build_scope_sources(root, native_timestamps=None):
    """Bind existing producer JSON, never arrays, pixels, labels or model files."""
    root = Path(root).resolve()
    nba = d.read_json(root / NBA_CONFIG); school = d.read_json(root / NFHS_CONFIG)
    result = []
    for window in nba["windows"]:
        cid = window["candidate_id"]; folder = root / nba["outputs"]["root"]
        limits = window["source_frame_range_inclusive"]
        result.append({"candidate_id": cid, "kind": "nba",
            "analysis_group": "sac_training_fit" if window["approved_role"] == "future_training_candidate_pool" else "det_development",
            "source_video": window["source_video"],
            "source_manifest": d.binding(root, folder / "inputs" / cid / "manifest.json"),
            "source_end_exclusive_pts_ticks": window["source_end_exclusive_pts_ticks"],
            "protected_ranges": [], "segments": [{"segment_id": f"{cid}:{limits[0]}-{limits[1]}",
                "range_inclusive": limits, "observations": d.binding(root, folder / cid / "observations.json")} ]})
    for possession in school["possessions"]:
        cid = possession["possession_id"]; folder = root / school["output_root"] / cid
        result.append({"candidate_id": cid, "kind": "nfhs", "analysis_group": "nfhs_development",
            "source_video": possession["source_video"], "possession": possession,
            "source_end_exclusive_pts_ticks": possession["source_video"]["frame_count"] * 3600,
            "protected_ranges": possession["protected_ranges"],
            "timeline_observations": d.binding(root, folder / "observations.json"),
            "segments": [{"segment_id": f"{cid}:{lo}-{hi}", "range_inclusive": [lo, hi],
                "observations": d.binding(root, folder / f"segment_{lo:06d}_{hi:06d}" / "observations.json")}
                for lo, hi in possession["visible_segments"]]})
        if native_timestamps is not None: result[-1]["native_timestamps"] = native_timestamps[cid]
    return result


def validate_scope(root, scope):
    d.require(scope["schema_version"] == SCOPE_SCHEMA and scope["status"] == "approved", "Approved continuous scope required")
    approval = saved.read_bound(root, scope["approval"])
    d.require(approval.get("schema_version") == "nba_temporal_gap_continuous_validation_approval/v0.1"
              and approval.get("status") == "approved" and approval.get("approved_by") == "Ryan"
              and approval.get("user_statement"), "Ryan approval required")
    d.require(d.binding(root, d.contained(root, approval["proposal"]["path"])) == approval["proposal"], "Approved plan changed")
    d.require(scope["policy"] == selector.POLICY and scope["gates"] == selector.GATES, "Frozen rule or gates changed")
    d.require(scope["additional_conditions"] == ADDITIONAL_CONDITIONS, "Continuous retention/control gates changed")
    d.require(scope["totals"] == TOTALS, "Continuous scope totals changed")
    d.require(all(approval["scope"][key] == scope["totals"][value] for key, value in
        {"processed_frames": "processed_frames", "continuous_segments": "segments",
         "protected_timeline_positions": "protected_frames", "existing_label_frames": "scored_frames"}.items()), "Approval totals differ")
    d.require(scope["source_authority"] == {"nba_action_proposal": d.binding(root, root / NBA_CONFIG),
        "nfhs_observation_config": d.binding(root, root / NFHS_CONFIG)}, "Source authority bytes changed")
    timing = {s["candidate_id"]: s["native_timestamps"] for s in scope["sources"] if s["kind"] == "nfhs"}
    d.require(scope["sources"] == build_scope_sources(root, timing), "Full-context source authorities or producer bindings changed")
    modules = [Path(__file__), Path(selector.__file__), Path(pools.__file__), Path(saved.__file__),
               Path(action.__file__), Path(nfhs.__file__), Path(metrics.__file__), Path(d.__file__)]
    d.require(scope["implementation"] == [d.binding(root, p) for p in modules]
              and scope["focused_tests"] == d.binding(root, root / "tests/test_nba_temporal_gap_continuous.py"), "Implementation/test bindings changed")
    # Hashing the prior label-bearing report does not parse or expose its labels.
    for name in ("accepted_gap_report", "accepted_gap_scope", "accepted_gap_visual_review"):
        d.require(d.binding(root, d.contained(root, scope[name]["path"])) == scope[name], f"Changed {name}")
    accepted_scope = saved.read_bound(root, scope["accepted_gap_scope"])
    d.require(accepted_scope["policy"] == selector.POLICY and accepted_scope["gates"] == selector.GATES,
              "Accepted bounded rule differs")
    output = d.contained(root, scope["output_root"])
    d.require(output.is_relative_to(root / "data/outputs"), "Outputs must remain ignored")
    return accepted_scope


def normalize_observation(observation, frame, limits, kind):
    """Independently validate the actual producer's selected-component contract."""
    row = copy.deepcopy(observation)
    if kind == "nfhs":
        d.require(row["frame_index"] == frame["source_frame_index"], "NFHS frame join differs")
        row["source_frame_index"] = row["frame_index"]
        row["source_pts_ticks"] = frame["source_pts_ticks"]
        row["temporal_contributions"] = row["contribution_count"]
    d.require(row["source_frame_index"] == frame["source_frame_index"]
              and row["source_pts_ticks"] == frame["source_pts_ticks"], "Original native frame/PTS differs")
    d.require(row["temporal_contributions"] == len(saved.needed_starts([row["source_frame_index"]], limits)),
              "Original complete contributor context differs")
    candidates = row["candidates"]
    d.require([r["candidate_index"] for r in candidates] == list(range(len(candidates))), "Candidate order changed")
    selected = min(candidates, key=lambda c: (-c["native_score"], c["candidate_index"])) if candidates else None
    d.require(row["selected_candidate_index"] == (selected["candidate_index"] if selected else None)
              and row["center_xy_px"] == ([selected["center_x"], selected["center_y"]] if selected else None)
              and row["native_score"] == (selected["native_score"] if selected else None)
              and row["state"] == ("observed" if selected else "missing"), "Original selected-component transport differs")
    selector._center(row["center_xy_px"])
    return row


def load_segment(root, source, segment):
    data = saved.read_bound(root, segment["observations"])
    limits = segment["range_inclusive"]; cid = source["candidate_id"]
    lo, hi = limits
    if source["kind"] == "nba":
        manifest = saved.read_bound(root, source["source_manifest"])
        d.require(data["candidate_id"] == manifest["candidate_id"] == cid
                  and manifest["source_video"] == source["source_video"]
                  and data["input_manifest"] == source["source_manifest"]
                  and data["checkpoint"]["sha256"] == d.EXPANDED_SHA
                  and manifest["time_base"] == selector.POLICY["time_base"]
                  and data["inference"] == d.POLICY, "NBA producer/source/model contract differs")
        frames = manifest["frames"]
        originals = data["frames"]
        records = {r["first_source_frame_index"]: r for r in data["triplet_caches"]}
        d.require(len(records) == len(data["triplet_caches"]), "Duplicate NBA cache start")
        d.require(all(r["segment_source_frame_range_inclusive"] == limits for r in originals), "NBA context boundary changed")
    else:
        d.require(data["segment"] == limits and data["identity"]["source_video"] == source["source_video"]
                  and data["identity"]["weights"]["sha256"] == d.EXPANDED_SHA, "NFHS producer/source/model contract differs")
        originals = data["frames"]
        timing = saved.read_bound(root, source["native_timestamps"])
        d.require(timing["time_base"] == "1/90000" and timing["time_origin"] == "clip_first_frame"
                  and timing["source_video"] == source["source_video"], "NFHS native timing source/origin differs")
        timed = timing["frames"]
        d.require([f["source_frame_index"] for f in timed] == list(range(source["source_video"]["frame_count"]))
                  and all(f["source_pts_ticks"] == f["source_frame_index"] * 3600 and f["duration_ticks"] == 3600
                          and f["container_pts_ticks"] == timing["container_time_origin_ticks"] + f["source_pts_ticks"] for f in timed),
                  "NFHS packet timing does not establish the original 25fps relative timeline")
        frames = [copy.deepcopy(timed[i]) for i in range(lo, hi + 1)]
        manifest = {"candidate_id": cid, "source_video": source["source_video"], "time_base": "1/90000", "frames": frames}
        records = {r["input_frame_indices"][0]: r for r in data["triplets"]}
        d.require(len(records) == len(data["triplets"]), "Duplicate NFHS cache start")
    d.require([f["source_frame_index"] for f in frames] == list(range(lo, hi + 1))
              and len(originals) == len(frames) and sorted(records) == list(range(lo, hi - 1)), "Incomplete continuous segment inventory")
    observations = [normalize_observation(r, f, limits, source["kind"]) for r, f in zip(originals, frames, strict=True)]
    return {"source": source, "segment": segment, "producer": data, "manifest": manifest,
            "frames": frames, "observations": observations, "cache_records": records}


def projected_row(context, frame, observation, pool):
    source = context["source"]
    return {"window_id": context["segment"]["segment_id"], "candidate_id": source["candidate_id"],
        "source_frame_index": frame["source_frame_index"], "source_pts_ticks": frame["source_pts_ticks"],
        "width_px": source["source_video"]["width_px"], "height_px": source["source_video"]["height_px"],
        "baseline_center_xy_px": observation["center_xy_px"],
        "pool_records": [{"record_index": n, "center_xy_px": [r["component"]["center_x"], r["component"]["center_y"]],
                          "provenance_id": r["provenance_id"]} for n, r in enumerate(pool["records"])]}


def potentially_fillable_indices(projected):
    """Reuse the selector itself to prune only its pre-candidate rejection paths."""
    probe = selector.select_window(projected)
    return {r["source_frame_index"] for gap in probe["gaps"] for r in gap["frame_diagnostics"]}


def nfhs_cache_origin(root, context, record, start, identity):
    """Reproduce the producer's source join without inventing identity fields.

    Imported evaluation identities describe the model/config, not a source.
    Their bound experiment window and original on-disk location bind the source.
    Fresh longer-observation identities instead carry source_video and segment.
    """
    source = context["source"]
    d.require(identity["weights"]["sha256"] == d.EXPANDED_SHA
              and record["input_frame_indices"] == [start, start + 1, start + 2], "NFHS original identity/frame list differs")
    cache_path = d.contained(root, record["cache"]["path"])
    identity_path = d.contained(root, record["original_identity"]["path"])
    d.require(cache_path.name == f"triplet_{start:06d}.npz" and identity_path == cache_path.with_name("inference_identity.json")
              and d.contained(root, record["receipt"]["path"]) == cache_path.with_suffix(".json"), "NFHS cache/identity locations differ")
    if record["origin"] == "observation_cache":
        d.require(identity == context["producer"]["identity"] and identity["source_video"] == source["source_video"]
                  and identity["segment"] == context["segment"]["range_inclusive"], "NFHS observation identity differs")
        return {"kind": "observation_segment", "range_inclusive": identity["segment"]}
    d.require(record["origin"] == "prior_development_cache", "Unknown NFHS cache origin")
    config = d.read_json(root / NFHS_CONFIG)
    old = saved.read_bound(root, config["cached_experiment"])
    d.require(identity["experiment_config_sha256"] == nfhs.canonical(old)
              and identity["inference"] == old["inference"] == nfhs.OLD_POLICY, "Imported NFHS experiment/model contract differs")
    for key in ("weights", "training_completion", "upstream_commit", "adapter_sha256", "derived_adapter_sha256",
                "inference_source_sha256", "runtime_versions", "input_modality", "offline_future_context"):
        d.require(identity[key] == context["producer"]["identity"][key], "Imported NFHS model lineage differs")
    windows = [window for window in old["windows"]
               if d.contained(root, old["output_root"]) / window["window_id"] == cache_path.parent]
    d.require(len(windows) == 1, "Imported NFHS cache has no unique original source window")
    window = windows[0]; lo, hi = window["start_frame_index"], window["end_frame_index"]
    d.require(window["possession_id"] == source["candidate_id"] and window["source_video"] == source["source_video"]
              and lo <= start < start + 2 <= hi
              and any(a <= lo <= hi <= b for a, b in source["possession"]["visible_segments"])
              and context["segment"]["range_inclusive"][0] <= start < start + 2 <= context["segment"]["range_inclusive"][1],
              "Imported NFHS source/window/protected-boundary join differs")
    return {"kind": "prior_development_window", "experiment": config["cached_experiment"],
            "window_id": window["window_id"], "range_inclusive": [lo, hi], "source_video": window["source_video"]}


def read_contributor(root, context, start):
    record = context["cache_records"][start]
    if context["source"]["kind"] == "nba":
        descriptor = {"start": start, "format": "native_action", "cache": record["cache"],
            "receipt": d.binding(root, d.contained(root, record["cache"]["path"]).with_suffix(".json")), "producer_record": record}
        return saved.load_cache(root, descriptor, context["manifest"], context["producer"])
    identity = saved.read_bound(root, record["original_identity"])
    origin = nfhs_cache_origin(root, context, record, start, identity)
    cache = {"path": record["cache"]["path"], "sha256": record["cache"]["sha256"], "bytes": record["cache"]["size_bytes"]}
    descriptor = {"start": start, "format": "nfhs_original", "cache": cache, "receipt": record["receipt"]}
    values, binding = saved.load_cache(root, descriptor, context["manifest"], nfhs_identity=identity)
    return values, {**binding, "original_identity": record["original_identity"], "original_producer_record": record,
                    "original_source_authority": origin}


def select_segment(root, context, resources, *, cache_reader=read_contributor, prune=True):
    source = context["source"]; cid = source["candidate_id"]; limits = context["segment"]["range_inclusive"]
    size = source["source_video"]["width_px"], source["source_video"]["height_px"]
    all_pools = {f["source_frame_index"]: pools.build_pool("old", cid, f["source_frame_index"], obs, [], size)
                 for f, obs in zip(context["frames"], context["observations"], strict=True)}
    projected = [projected_row(context, f, obs, all_pools[f["source_frame_index"]])
                 for f, obs in zip(context["frames"], context["observations"], strict=True)]
    eligible = potentially_fillable_indices(projected) if prune else {r["source_frame_index"] for r in projected}
    arrays = {}
    for frame, observation in zip(context["frames"], context["observations"], strict=True):
        index = frame["source_frame_index"]
        if index not in eligible: continue
        needed = saved.needed_starts([index], limits)
        for expired in list(arrays):
            if expired not in needed: del arrays[expired]
        for start in needed:
            if start not in arrays:
                arrays[start], binding = cache_reader(root, context, start)
                resources["cache_reads"].append({"candidate_id": cid, "segment_id": context["segment"]["segment_id"], **binding})
        resources["peak_triplet_arrays"] = max(resources["peak_triplet_arrays"], len(arrays))
        contributions = [(s, index - s, arrays[s][index - s]) for s in needed]
        mean = metrics.reconstruct_mean([(s, plane) for s, _, plane in contributions])
        if source["kind"] == "nba":
            reproduced = action.select_observation(frame, mean, len(needed), context["manifest"],
                {"kind": observation["segment_kind"], "source_frame_range_inclusive": limits})
            d.require(reproduced == observation, "Consumed original NBA mean/candidates/selection differ")
        else:
            reproduced = nfhs.observed_frames([mean], [len(needed)], index, source["source_video"], .3)[0]
            d.require(all(reproduced[k] == observation[k] for k in reproduced), "Consumed original NFHS mean/candidates/selection differ")
        all_pools[index] = pools.build_pool("old", cid, index, observation, contributions, size)
    projected = [projected_row(context, f, obs, all_pools[f["source_frame_index"]])
                 for f, obs in zip(context["frames"], context["observations"], strict=True)]
    result = selector.select_window(projected)
    for decision, frame, observation in zip(result["frames"], context["frames"], context["observations"], strict=True):
        index = decision["source_frame_index"]; pool = all_pools[index]
        selected_index = decision["selected_pool_record_index"]
        if decision["decision"] == "preserved_original": selected_index = observation["selected_candidate_index"]
        selected_record = pool["records"][selected_index] if selected_index is not None else None
        decision.update(segment_id=context["segment"]["segment_id"], source_frame=frame,
            source_video=source["source_video"], original_observation=observation,
            selected_pool_record_index=selected_index,
            selected_provenance_id=selected_record["provenance_id"] if selected_record else None,
            selected_component=selected_record["component"] if selected_record else None,
            selected_native_score=selected_record["component"]["native_score"] if selected_record else None,
            candidate_pool=pool, candidate_pool_scope="complete_contributors" if index in eligible else "mean_only_not_consulted")
        if source["kind"] == "nfhs": decision["container_pts_ticks"] = frame["container_pts_ticks"]
    result.update(segment_id=context["segment"]["segment_id"], range_inclusive=limits,
                  candidate_frames_consulted=sorted(eligible))
    return result


def select_sources(root, scope, resources):
    sources = []; windows = []; frames = []
    for source in scope["sources"]:
        segments = [select_segment(root, load_segment(root, source, segment), resources) for segment in source["segments"]]
        processed = [r for segment in segments for r in segment["frames"]]
        by_index = {r["source_frame_index"]: r for r in processed}
        if source["kind"] == "nfhs":
            timeline = saved.read_bound(root, source["timeline_observations"])
            timing = saved.read_bound(root, source["native_timestamps"])
            d.require(timeline["source_video"] == source["source_video"] and timeline["protected_ranges"] == source["protected_ranges"], "NFHS timeline authority differs")
            expected = {r["frame_index"]: r for r in timeline["frames"]}
            full = []
            for index in range(source["source_video"]["frame_count"]):
                withheld = any(a <= index <= b for a, b in source["protected_ranges"])
                d.require(withheld == (expected[index]["state"] == "withheld") == (index not in by_index), "Protected NFHS position entered processing")
                if withheld:
                    full.append({"candidate_id": source["candidate_id"], "source_frame_index": index, "source_pts_ticks": index * 3600,
                        "baseline_center_xy_px": None, "selected_center_xy_px": None, "decision": "withheld", "segment_id": None,
                        "reason": "protected_band", "selected_native_score": None, "selected_component": None,
                        "container_pts_ticks": timing["frames"][index]["container_pts_ticks"]})
                else:
                    d.require(all(expected[index][k] == by_index[index]["original_observation"][k] for k in
                        ("state", "center_xy_px", "candidates", "selected_candidate_index", "native_score", "contribution_count")), "NFHS timeline and segment records differ")
                    full.append(by_index[index])
        else: full = processed
        sources.append({**source, "time_origin": "clip_first_frame" if source["kind"] == "nfhs" else "native_container",
                        "segments": segments, "frames": full})
        windows.extend(segments); frames.extend(processed)
    d.require(len(frames) == scope["totals"]["processed_frames"] and len(windows) == scope["totals"]["segments"]
              and sum(len(s["frames"]) for s in sources) == scope["totals"]["timeline_frames"], "Selected scope totals differ")
    return {"schema_version": SCHEMA, "policy": selector.POLICY, "sources": sources, "windows": windows,
            "frames": frames, "labels_used": False, "human_review": "pending", "accepted": False}


def score_saved_selection(root, scope, selection, selection_binding):
    d.require(d.binding(root, d.contained(root, selection_binding["path"])) == selection_binding,
              "Selection must be persisted unchanged before loading labels")
    prior = saved.read_bound(root, scope["accepted_gap_report"])
    d.require(prior["status"] == "completed" and len(prior["frames"]) == scope["totals"]["scored_frames"], "Accepted reference inventory differs")
    indexed = {(r["source_video"]["sha256"], r["source_frame_index"]): r for r in selection["frames"]}
    rows = []; retention = []; context_changes = []
    for old in prior["frames"]:
        decision = indexed[old["source_video"]["sha256"], old["source_frame_index"]]
        d.require(old["source_frame"]["source_pts_ticks"] == decision["source_pts_ticks"]
                  and old["source_video"] == decision["source_video"], "Label/source identity or PTS join differs")
        scoring_row = {**old, "source_frame": decision["source_frame"],
                       "old": {"pool": {"contributor_planes": [None] * decision["original_observation"]["temporal_contributions"]}}}
        components = [r["component"] for r in decision["candidate_pool"]["records"]]
        before = selector.score_point(scoring_row, decision["baseline_center_xy_px"], decision["original_observation"]["candidates"])
        after = selector.score_point(scoring_row, decision["selected_center_xy_px"], components)
        row = {k: copy.deepcopy(old[k]) for k in ("window_id", "candidate_id", "source_frame_index", "source_frame",
            "source_video", "analysis_group", "cohort", "is_control", "annotation", "eligibility")}
        d.require(pools.eligibility(row["annotation"]) == row["eligibility"], "Reference eligibility changed")
        row.update(continuous_source_id=decision["candidate_id"], segment_id=decision["segment_id"], baseline=before, selected=after,
                   decision=decision, changed=decision["baseline_center_xy_px"] != decision["selected_center_xy_px"],
                   short_context_baseline=old["baseline"], accepted_short_context_selected=old["selected"],
                   candidate_availability_scope=decision["candidate_pool_scope"])
        rows.append(row)
        if before != old["baseline"]:
            context_changes.append({"candidate_id": decision["candidate_id"], "source_frame_index": old["source_frame_index"],
                "short_context_baseline": old["baseline"], "same_context_baseline": before,
                "point_changed": old["decision"]["baseline_center_xy_px"] != decision["baseline_center_xy_px"]})
        if old["changed"]:
            retention.append({"candidate_id": decision["candidate_id"], "source_frame_index": old["source_frame_index"],
                "accepted_center_xy_px": old["decision"]["selected_center_xy_px"], "continuous_center_xy_px": decision["selected_center_xy_px"],
                "retained_exact_coordinate": old["decision"]["selected_center_xy_px"] == decision["selected_center_xy_px"],
                "matched": after["outcome"] == "matched", "same_context_original_outcome": before["outcome"]})
    d.require(len({(r["continuous_source_id"], r["source_frame_index"]) for r in rows}) == len(rows), "Duplicate scored source frame")
    return rows, retention, context_changes


def summarize(rows, scope, accepted_scope, selection, retention, context_changes):
    summary = selector.summarize(rows, accepted_scope, selection)
    checks = summary["gates"]["checks"]
    checks.update(no_new_wrong_frames=not any(r["selected"]["outcome"] == "wrong" and r["baseline"]["outcome"] != "wrong" for r in rows),
        no_new_hidden_alarm_frames=not any(r["selected"]["outcome"] == "hidden_alarm" and r["baseline"]["outcome"] != "hidden_alarm" for r in rows),
        no_lost_correct_positions=not any(r["baseline"]["outcome"] == "matched" and r["selected"]["outcome"] != "matched" for r in rows),
        retained_all_original_points=all(r["baseline_center_xy_px"] is None or r["baseline_center_xy_px"] == r["selected_center_xy_px"] for r in selection["frames"]),
        det_retains_209_matches=summary["by_analysis_group"]["det_development"]["selected"]["matched"] >= 209,
        accepted_three_additions_retained=sorted([r["candidate_id"], r["source_frame_index"]] for r in retention)
            == sorted(ADDITIONAL_CONDITIONS["accepted_additions_retained"])
            and all(r["retained_exact_coordinate"] and r["matched"] for r in retention))
    nfhs_baseline = summary["by_analysis_group"]["nfhs_development"]["baseline"]
    checks["same_context_nfhs_control"] = [nfhs_baseline[k] for k in ("matched", "wrong", "missing", "hidden_alarm")] == [131, 1, 13, 0]
    checks["same_context_nfhs_not_regressed"] = summary["by_analysis_group"]["nfhs_development"]["selected"]["matched"] >= 131
    summary["gates"]["numerical_candidate_pass"] = all(checks.values())
    intervals = []
    for segment in selection["windows"]:
        adapted = [{"window_id": r["window_id"], "candidate_id": r["candidate_id"], "source_frame_index": r["source_frame_index"],
                    "source_frame": r["source_frame"], "decision": r} for r in segment["frames"]]
        intervals.append({"segment_id": segment["segment_id"], **{arm: selector.missing_intervals(adapted, arm, eligible_only=False)
                          for arm in ("baseline", "selected")}})
    summary.update(accepted_addition_retention=retention, model_context_changes=context_changes,
        all_changed_frames=[r for r in selection["frames"] if r["baseline_center_xy_px"] != r["selected_center_xy_px"]],
        remaining_labeled_errors=[r for r in rows if r["selected"]["outcome"] in {"wrong", "missing", "hidden_alarm"}],
        full_output_missing_intervals=intervals, totals=scope["totals"],
        unlabeled_positions="Unscored; visual plausibility is not an accuracy count.",
        candidate_availability="Full contributor pools are materialized only for geometrically admissible gaps; other rows show original mean candidates only.")
    return summary


def load_resumable_selection(root, output, path, bindings):
    selection_path = d.contained(root, str(path))
    d.require(selection_path.is_relative_to(output / "attempts") and selection_path.name == "selection.json",
              "Resume only a preserved selection from this output root")
    ready = d.read_json(selection_path.with_name("selection_ready.json"))
    selection_binding = ready["selection"]
    d.require(selection_binding == d.binding(root, selection_path) and ready["labels_loaded"] is False,
              "Resumed selection differs from its pre-scoring receipt")
    selection = d.read_json(selection_path)
    d.require(selection["schema_version"] == SCHEMA and selection["policy"] == selector.POLICY
              and selection["bindings"] == ready["bindings"]
              and selection["bindings"]["scope"] == bindings["scope"]
              and selection["bindings"]["selector"] == bindings["selector"] and selection["labels_used"] is False,
              "Resumed selection scope/frozen selector differs")
    return selection, selection_binding


def run(root, scope_path, *, resume_selection=None):
    root = Path(root).resolve(); scope_path = (root / scope_path).resolve()
    scope = d.read_json(scope_path); accepted_scope = validate_scope(root, scope)
    output = d.contained(root, scope["output_root"]); output.mkdir(parents=True, exist_ok=True)
    lock = d.acquire_run_lock(output / ".run.lock"); attempt = output / "attempts" / uuid.uuid4().hex
    began = time.monotonic(); resources = {"model_calls": 0, "checkpoint_loads": 0, "source_decodes": 0,
                                         "cache_reads": [], "peak_triplet_arrays": 0}
    bindings = {"scope": d.binding(root, scope_path), "approval": scope["approval"],
        "implementation": d.binding(root, Path(__file__)), "selector": d.binding(root, Path(selector.__file__)),
        "focused_tests": d.binding(root, root / "tests/test_nba_temporal_gap_continuous.py")}
    try:
        d.require(not (output / "completion.json").exists(), "Preserve completed continuous validation")
        d.write_once(attempt / "started.json", {"status": "started", "bindings": bindings, "at_utc": d.stamp()})
        if resume_selection is None:
            selection = select_sources(root, scope, resources)
            selection.update(bindings=bindings, resources=resources)
            d.write_once(attempt / "selection.json", selection)
            selection_binding = d.binding(root, attempt / "selection.json")
            d.write_once(attempt / "selection_ready.json", {"selection": selection_binding, "bindings": bindings,
                                                           "labels_loaded": False, "at_utc": d.stamp()})
        else:
            selection, selection_binding = load_resumable_selection(root, output, resume_selection, bindings)
            resources["resumed_selection"] = selection_binding
            resources["original_selection_resources"] = selection["resources"]
        rows, retention, context_changes = score_saved_selection(root, scope, selection, selection_binding)
        summary = summarize(rows, scope, accepted_scope, selection, retention, context_changes)
        report = {"schema_version": SCHEMA, "status": "completed", "bindings": bindings, "selection": selection_binding,
                  "frames": rows, "summary": summary, "resources": resources, "human_review": "pending", "accepted": False}
        d.write_once(attempt / "report.json", report); d.write_once(attempt / "summary.json", summary)
        completion = {"schema_version": SCHEMA, "status": "completed", "bindings": bindings, "selection": selection_binding,
            "report": d.binding(root, attempt / "report.json"), "summary": d.binding(root, attempt / "summary.json"),
            "elapsed_seconds": time.monotonic() - began, "human_review": "pending", "accepted": False}
        d.write_once(attempt / "completed.json", completion); d.write_once(output / "completion.json", completion)
        return completion
    except Exception as error:
        d.write_once(attempt / "failed.json", {"status": "failed_preserved", "error_type": type(error).__name__,
            "error": str(error), "resources": resources, "elapsed_seconds": time.monotonic() - began})
        raise
    finally:
        d.release_run_lock(lock)


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--scope", required=True)
    parser.add_argument("--resume-selection", help="Use an existing immutable selection after a downstream delivery failure")
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument("--run", action="store_true"); action_group.add_argument("--check-scope", action="store_true")
    args = parser.parse_args(); root = Path.cwd(); path = root / args.scope
    if args.check_scope:
        scope = d.read_json(path); validate_scope(root, scope)
        print(json.dumps({"status": "bound_metadata_verified_no_arrays_or_labels_read", "totals": scope["totals"]}, indent=2))
    else: print(json.dumps(run(root, path, resume_selection=args.resume_selection), indent=2))


if __name__ == "__main__": main()
