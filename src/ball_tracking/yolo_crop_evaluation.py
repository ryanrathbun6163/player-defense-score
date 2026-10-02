"""Score new YOLO observations and compare immutable RF-DETR crop evidence."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from dataclasses import asdict, replace
from pathlib import Path

from .annotations import load_annotations
from . import crop_motion_factorial as controls
from .detections import ModelProvenance, load_detection_run
from .development_experiments import bound_file, canonical_sha256, read_json, require_digest, safe_path
from .evaluation import evaluate_detections
from .temporal_association import RADII, THRESHOLDS
from .temporal_evaluation import _runs
from .temporal_experiment import file_binding, persist_once, spec_digest
from .tiled_candidates import candidate_run as saved_crop_run
from .tiled_evaluation import COUNTS, METRICS
from .yolo_crop_candidates import ARMS, experiment_grid, validate_observations
from .yolo_crop_experiment import (
    OUTPUT_ROOT, PRIOR_COMMIT, load_candidate_run, load_observations,
    load_saved_control, preflight, unchanged,
)

POOL_SCHEMA = "ball_yolo_crop_pool/v0.1"
REPORT_SCHEMA = "ball_yolo_crop_evaluation/v0.1"
CONTROL_PAIRS = dict(zip(ARMS, controls.ARMS[:3]))
CONTROL_ARMS = tuple(CONTROL_PAIRS.values())
MATCHING_RULE = "raw center distance; uncertainty diagnostic only"


def control_grid():
    return tuple(c for c in controls.experiment_grid() if c.arm in CONTROL_ARMS)


def _temporal(frames):
    emitted = [f["accepted_detection_count"] > 0 for f in frames]
    return {
        "emitted_frame_count": sum(emitted), "missing_frame_count": len(frames)-sum(emitted),
        "frame_count": len(frames), "emitted_frame_coverage": sum(emitted)/len(frames),
        "longest_consecutive_missed_eligible_run": max(_runs([f["false_negative_count"] == 1 for f in frames]), default=0),
        "correct_match_run_lengths": _runs([f["matched_candidate_index"] is not None for f in frames]),
    }


def _evaluate_validated(labels, run, observations, radius, commit):
    selected = replace(run, frames=tuple(replace(frame, detections=tuple(
        c for c in frame.detections if c.candidate_index in obs["emitted_candidate_indices"]))
        for frame, obs in zip(run.frames, observations["frames"])))
    score = evaluate_detections(labels, selected,
                                confidence_threshold=observations["config"]["confidence_threshold"],
                                localization_radius_px=radius)
    return {
        "schema_version": REPORT_SCHEMA, "variant_id": observations["variant_id"],
        "config": observations["config"], "localization_radius_px": radius,
        "selection_purpose": labels.window.selection_purpose, "possession_id": run.possession_id,
        "source_video": run.source_video.to_dict(), "window": run.window.to_dict(),
        "input_model_provenance": run.model_provenance.to_dict(),
        "ranking_code_commit": observations["ranking_code_commit"], "evaluator_code_commit": commit,
        "observations_content_sha256": canonical_sha256(observations),
        "input_candidate_content_sha256": canonical_sha256(run.to_dict()),
        "annotation_content_sha256": score["annotation_content_sha256"], "matching_rule": MATCHING_RULE,
        "metrics": {k: score[k] for k in METRICS}, "frame_results": score["frame_results"],
        "temporal_metrics": _temporal(score["frame_results"]),
        "selected_operating_point": None, "quality_gate": None,
    }


def evaluate_observations(labels, run, observations, radius, commit):
    """Evaluate a new selected view; annotations enter only this scoring stage."""
    require_digest(commit, "YOLO evaluator commit", 40)
    if isinstance(radius, bool) or radius not in RADII:
        raise ValueError("Undeclared YOLO localization radius")
    validate_observations(observations, run)
    return _evaluate_validated(labels, run, observations, radius, commit)


def aggregate(reports):
    """Pool arithmetic only; preserve the historical aggregate representation."""
    if not reports:
        raise ValueError("Empty detector comparison aggregate")
    keys = ("variant_id", "config", "localization_radius_px", "selection_purpose",
            "input_model_provenance", "ranking_code_commit", "evaluator_code_commit")
    first = reports[0]
    if any(any(r[k] != first[k] for k in keys) for r in reports):
        raise ValueError("Mixed detector aggregate settings or provenance")
    if len({r["possession_id"] for r in reports}) != len(reports):
        raise ValueError("Duplicate possession in detector aggregate")
    metrics = {k: sum(r["metrics"][k] for r in reports) for k in COUNTS}
    tp, fp, fn = (metrics[k] for k in ("true_positive_count", "false_positive_count", "false_negative_count"))
    metrics.update(precision=tp/(tp+fp) if tp+fp else None, recall=tp/(tp+fn) if tp+fn else None)
    return {**{k: first[k] for k in keys}, "metrics": metrics, "window_count": len(reports),
            "per_window": [{"possession_id": r["possession_id"], "window": r["window"],
                            "metrics": r["metrics"], "temporal_metrics": r["temporal_metrics"]} for r in reports],
            "selected_operating_point": None, "quality_gate": None}


def _key(report):
    return (report["selection_purpose"], report["possession_id"],
            report["window"]["start_frame_index"], report["window"]["end_frame_index"],
            report["config"]["arm"], report["config"]["confidence_threshold"], report["localization_radius_px"])


def _report_index(reports):
    index = {}
    for r in reports:
        key = _key(r)
        if key in index:
            raise ValueError("Duplicate detector scoring cell")
        index[key] = r
    return index


def _cell(index, report, arm, threshold=None):
    key = (*_key(report)[:4], arm,
           report["config"]["confidence_threshold"] if threshold is None else threshold,
           report["localization_radius_px"])
    other = index.get(key)
    if other is None:
        raise ValueError("Incomplete detector comparison cell")
    # Detector/candidate identities and code commits deliberately differ between models.
    if any(other[k] != report[k] for k in ("source_video", "window", "selection_purpose",
                                           "annotation_content_sha256", "matching_rule")):
        raise ValueError("Detector comparison mixes sources, annotations or pools")
    if [f["frame_index"] for f in other["frame_results"]] != [f["frame_index"] for f in report["frame_results"]]:
        raise ValueError("Paired detector frames differ")
    return other


def _correct(report):
    return {f["frame_index"] for f in report["frame_results"] if f["matched_candidate_index"] is not None}


def _identity(report):
    return {k: report[k] for k in ("possession_id", "selection_purpose", "window", "config")}


def paired_differences(reports):
    """Compare outcomes, never treating indices from different models as identities."""
    index = _report_index(reports)
    identities = {key[:4] for key in index}
    if not identities or set(index) != {(*identity, arm, threshold, radius) for identity in identities
            for arm in (*ARMS, *CONTROL_ARMS) for threshold in THRESHOLDS for radius in RADII}:
        raise ValueError("Incomplete paired detector grid")
    pairs, losses = [], []
    for report in reports:
        arm = report["config"]["arm"]
        if arm not in (*ARMS, *CONTROL_ARMS):
            raise ValueError("Undeclared detector comparison arm")
        floor_arm = ARMS[0] if arm in ARMS else CONTROL_ARMS[0]
        qualified = _cell(index, report, floor_arm)
        floor = _cell(index, report, floor_arm, THRESHOLDS[0])
        if any(qualified[k] != report[k] or floor[k] != report[k] for k in
               ("input_model_provenance", "input_candidate_content_sha256")):
            raise ValueError("Availability decomposition mixes detector exports")
        selected, accepted, available = map(_correct, (report, qualified, floor))
        if not selected <= accepted <= available:
            raise ValueError("Selected matches exceed exported availability")
        unavailable = {f["frame_index"] for f in floor["frame_results"] if f["false_negative_count"]}
        filtered, selector_lost = available-accepted, accepted-selected
        missed = {f["frame_index"] for f in report["frame_results"] if f["false_negative_count"]}
        parts = (unavailable, filtered, selector_lost)
        if set.union(*parts) != missed or sum(map(len, parts)) != len(missed):
            raise ValueError("False-negative partition does not reconcile")
        losses.append({**_identity(report), "radius_px": report["localization_radius_px"],
            "no_exported_candidate_at_floor_frames": sorted(unavailable),
            "confidence_filter_lost_frames": sorted(filtered), "selector_lost_frames": sorted(selector_lost),
            "false_negative_frames": sorted(missed),
            "unavailability_semantics": (
                "Postprocessed exports only: score, best-class assignment, NMS and cap cannot be separated."
                if arm in ARMS else "Saved RF-DETR crop exports at the fixed confidence floor."),
            "hidden_false_alarm_frames": [f["frame_index"] for f in report["frame_results"] if f["non_visible_false_alarm_count"]],
            "missing_observation_run_lengths": _runs([f["accepted_detection_count"] == 0 for f in report["frame_results"]])})
        if arm not in ARMS:
            continue
        baseline = _cell(index, report, CONTROL_PAIRS[arm])
        before, after = _correct(baseline), _correct(report)
        shared = []
        frames = []
        for old, new in zip(baseline["frame_results"], report["frame_results"]):
            if old["scoring_status"] != new["scoring_status"]:
                raise ValueError("Paired annotation eligibility differs")
            frames.append({"frame_index": new["frame_index"], "scoring_status": new["scoring_status"],
                           "control": old, "challenger": new})
            if old["matched_candidate_index"] is not None and new["matched_candidate_index"] is not None:
                shared.append({"frame_index": new["frame_index"],
                    "center_error_delta_px": new["matched_center_error_px"]-old["matched_center_error_px"],
                    "effective_center_error_delta_px": new["matched_effective_center_error_px"]-old["matched_effective_center_error_px"]})
        pairs.append({**_identity(report), "control_config": baseline["config"],
            "radius_px": report["localization_radius_px"],
            "control_ranking_commit": baseline["ranking_code_commit"], "challenger_ranking_commit": report["ranking_code_commit"],
            "control_model_provenance": baseline["input_model_provenance"], "challenger_model_provenance": report["input_model_provenance"],
            "newly_recovered_frames": sorted(after-before), "newly_lost_frames": sorted(before-after),
            **{name: report["metrics"][key]-baseline["metrics"][key] for name, key in (
                ("true_positive_delta", "true_positive_count"), ("false_positive_delta", "false_positive_count"),
                ("false_negative_delta", "false_negative_count"), ("hidden_false_alarm_delta", "non_visible_false_alarm_count"),
                ("duplicate_false_positive_delta", "duplicate_false_positive_count"))},
            "emitted_frame_delta": report["temporal_metrics"]["emitted_frame_count"]-baseline["temporal_metrics"]["emitted_frame_count"],
            "shared_match_localization_changes": shared, "frame_comparisons": frames})
    return pairs, losses


def aggregate_paired_differences(aggregates):
    index = {}
    for r in aggregates:
        key = (r["selection_purpose"], r["config"]["arm"], r["config"]["confidence_threshold"], r["localization_radius_px"])
        if key in index:
            raise ValueError("Duplicate detector aggregate cell")
        index[key] = r
    result = []
    for new in aggregates:
        c = new["config"]
        if c["arm"] not in ARMS:
            continue
        old = index.get((new["selection_purpose"], CONTROL_PAIRS[c["arm"]], c["confidence_threshold"], new["localization_radius_px"]))
        if (old is None or old["window_count"] != new["window_count"]
                or [(w["possession_id"], w["window"]) for w in old["per_window"]]
                != [(w["possession_id"], w["window"]) for w in new["per_window"]]):
            raise ValueError("Incomplete detector aggregate pair")
        result.append({"config": c, "control_config": old["config"], "radius_px": new["localization_radius_px"],
                       "selection_purpose": new["selection_purpose"],
                       **{k+"_delta": new["metrics"][k]-old["metrics"][k] for k in COUNTS}})
    return result


def _error_summary(values):
    return {"count": len(values), "mean": statistics.fmean(values) if values else None,
            "median": statistics.median(values) if values else None, "maximum": max(values) if values else None}


def _validate_metrics(report):
    """Reconcile saved arithmetic without rerunning geometric matching or selection."""
    frames = report["frame_results"]
    metrics = report["metrics"]
    if not frames or set(metrics) != set(METRICS):
        raise ValueError("Incomplete detector report metrics")
    computed = {k: sum(f[k] for f in frames) for k in (
        "input_detection_count", "false_positive_count", "false_negative_count", "duplicate_false_positive_count",
        "non_visible_false_alarm_count", "unscored_prediction_count")}
    computed.update(eligible_frame_count=sum(f["scoring_status"] == "localization_eligible" for f in frames),
                    not_visible_frame_count=sum(f["scoring_status"] == "not_visible_negative" for f in frames),
                    unscored_frame_count=sum(f["scoring_status"] == "unscored" for f in frames),
                    true_positive_count=sum(f["matched_candidate_index"] is not None for f in frames),
                    below_threshold_detection_count=sum(f["input_detection_count"]-f["accepted_detection_count"] for f in frames),
                    non_visible_false_alarm_frame_count=sum(f["non_visible_false_alarm_count"] > 0 for f in frames))
    tp, fp, fn, hidden = (computed[k] for k in ("true_positive_count", "false_positive_count", "false_negative_count", "not_visible_frame_count"))
    computed.update(precision=tp/(tp+fp) if tp+fp else None, recall=tp/(tp+fn) if tp+fn else None,
                    non_visible_false_alarm_rate=computed["non_visible_false_alarm_frame_count"]/hidden if hidden else None,
                    non_visible_false_alarms_per_100_frames=100.0*computed["non_visible_false_alarm_count"]/hidden if hidden else None)
    for key in ("matched_center_error_px", "matched_effective_center_error_px"):
        values = [f[key] for f in frames if f["matched_candidate_index"] is not None]
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x < 0 for x in values):
            raise ValueError("Invalid saved localization errors")
        computed[key] = _error_summary(values)
    for f in frames:
        count = f["accepted_detection_count"]
        match = int(f["matched_candidate_index"] is not None)
        if (any(type(f[k]) is not int or f[k] < 0 for k in ("input_detection_count", "accepted_detection_count",
                 "false_positive_count", "false_negative_count", "duplicate_false_positive_count",
                 "non_visible_false_alarm_count", "unscored_prediction_count"))
                or (match and (type(f["matched_candidate_index"]) is not int or f["matched_candidate_index"] < 0))
                or count > f["input_detection_count"]
                or f["scoring_status"] not in {"localization_eligible", "not_visible_negative", "unscored"}
                or f["false_positive_count"] < 0 or not 0 <= f["duplicate_false_positive_count"] <= f["false_positive_count"]):
            raise ValueError("Invalid saved frame counts")
        if f["scoring_status"] == "localization_eligible":
            if f["false_negative_count"] != 1-match or f["false_positive_count"] != count-match or f["non_visible_false_alarm_count"]:
                raise ValueError("Saved eligible outcome arithmetic differs")
        elif f["scoring_status"] == "not_visible_negative":
            if match or f["false_negative_count"] or f["non_visible_false_alarm_count"] != count or f["false_positive_count"] != count:
                raise ValueError("Saved hidden outcome arithmetic differs")
        elif match or f["false_positive_count"] or f["false_negative_count"] or f["unscored_prediction_count"] != count:
            raise ValueError("Saved unscored outcome arithmetic differs")
        if not match and (f["matched_center_error_px"] is not None or f["matched_effective_center_error_px"] is not None):
            raise ValueError("Unmatched frame has localization error")
        if match and not 0 <= f["matched_effective_center_error_px"] <= f["matched_center_error_px"] <= report["localization_radius_px"]:
            raise ValueError("Saved localization errors exceed raw matching radius")
    if computed != metrics or report["temporal_metrics"] != _temporal(frames):
        raise ValueError("Saved report metrics or missing runs do not reconcile")


def _validate_grid(reports, aggregates, p, purpose, configs, commit, schema):
    windows = [w for w in p["windows"] if w["purpose"] == purpose]
    index = _report_index(reports)
    expected = {(purpose, w["possession_id"], w["start_frame_index"], w["end_frame_index"], c.arm, c.confidence_threshold, r)
                for w in windows for c in configs for r in RADII}
    if len(windows) != 3 or set(index) != expected:
        raise ValueError("Incomplete detector scoring grid")
    identities = {(w["possession_id"], w["start_frame_index"], w["end_frame_index"]): w for w in windows}
    config_map = {c.variant_id: asdict(c) for c in configs}
    for r in reports:
        w = identities[r["possession_id"], r["window"]["start_frame_index"], r["window"]["end_frame_index"]]
        if (r["schema_version"] != schema or r["config"] != config_map.get(r["variant_id"])
                or r["ranking_code_commit"] != commit or r["evaluator_code_commit"] != commit
                or r["source_video"] != w["source_video"] or r["matching_rule"] != MATCHING_RULE
                or r["selected_operating_point"] is not None or r["quality_gate"] is not None
                or [f["frame_index"] for f in r["frame_results"]] != list(range(w["start_frame_index"], w["end_frame_index"]+1))):
            raise ValueError("Detector report identity/provenance mismatch")
        _validate_metrics(r)
    expected_aggregates = [aggregate([r for r in reports if r["variant_id"] == c.variant_id and r["localization_radius_px"] == radius])
                           for c in configs for radius in RADII]
    if aggregates != expected_aggregates:
        raise ValueError("Incomplete or changed detector aggregate grid")


def _saved_pools(root, p):
    result = {}
    for purpose, binding in zip(p["pool_separation"], p["saved_control_scoring_reports"]):
        value = read_json(bound_file(root, binding, "data/outputs/ball_tracking/crop_motion_factorial"))
        if (value["schema_version"] != "ball_crop_motion_pool/v0.1" or value["purpose"] != purpose
                or value["code_commit"] != PRIOR_COMMIT or value["selected_operating_point"] is not None
                or value["quality_gate"] is not None or len(value["evaluation_reports"]) != 945
                or len(value["aggregate_results"]) != 315):
            raise ValueError("Incomplete or changed saved control pool")
        reports = [r for r in value["evaluation_reports"] if r["config"]["arm"] in CONTROL_ARMS]
        aggregates = [r for r in value["aggregate_results"] if r["config"]["arm"] in CONTROL_ARMS]
        _validate_grid(reports, aggregates, p, purpose, control_grid(), PRIOR_COMMIT, "ball_crop_motion_evaluation/v0.1")
        result[purpose] = {"evaluation_reports": reports, "aggregate_results": aggregates}
    if len(result) != 2 or len(p["saved_control_scoring_reports"]) != 2:
        raise ValueError("Expected exactly two saved control pools")
    return result


def _load_evidence(root, m, p, commit, saved, inputs=None):
    """Load bound saved inputs only. No selector, detector or scorer is invoked."""
    evidence = {}
    if len(p["windows"]) != 6 or len(p["scoring_labels"]) != 6:
        raise ValueError("Expected six development windows and labels")
    saved_indices = {purpose: _report_index(pool["evaluation_reports"]) for purpose, pool in saved.items()}
    models = {item["window"]["window_id"]: item["model"] for item in inputs or []}
    verified_model = None
    for w, binding in zip(p["windows"], p["scoring_labels"]):
        if binding["window_id"] != w["window_id"]:
            raise ValueError("Detector scoring label window differs")
        labels = load_annotations(bound_file(root, binding["annotation"], "configs/ball_tracking/annotations"))
        if (labels.annotation_set_id != w["annotation_set_id"] or labels.possession_id != w["possession_id"]
                or labels.window.selection_purpose != w["purpose"] or labels.source_video.to_dict() != w["source_video"]
                or [a.frame_index for a in labels.annotations] != list(range(w["start_frame_index"], w["end_frame_index"]+1))):
            raise ValueError("Detector scoring labels do not align with source window")
        old_raw = load_detection_run(bound_file(root, w["detection"], "data/outputs/ball_tracking"))
        old = saved_crop_run(old_raw, read_json(bound_file(root, w["crop_candidates"], "data/outputs/ball_tracking")))
        model = models.get(w["window_id"], verified_model)
        if model is None:
            run, payload, digest = load_candidate_run(root, m, p, w, commit)
        else:
            run, payload, digest = load_candidate_run(root, m, p, w, commit, model=model)
        verified_model = ModelProvenance.from_mapping(payload["header"]["per_view_model_provenance"])
        if (run.annotation_set_id != labels.annotation_set_id or run.possession_id != labels.possession_id
                or run.source_video != labels.source_video or run.window != old.window
                or old.annotation_set_id != labels.annotation_set_id or old.possession_id != labels.possession_id
                or old.source_video != labels.source_video):
            raise ValueError("Detector runs do not align with scoring source/labels")
        observations = {}
        for c in control_grid():
            obs = load_saved_control(root, p, w, c)
            observations[c.variant_id] = obs
            for radius in RADII:
                r = saved_indices[w["purpose"]][(w["purpose"], w["possession_id"], w["start_frame_index"], w["end_frame_index"], c.arm, c.confidence_threshold, radius)]
                _bind_report(r, labels, old, obs)
        for c in experiment_grid():
            observations[c.variant_id] = load_observations(root, m, p, w, run, digest, c, commit, rederive=False)
        evidence[w["window_id"]] = (labels, run, observations, payload)
    return evidence


def _bind_report(report, labels, run, observations):
    if (report["observations_content_sha256"] != canonical_sha256(observations)
            or report["input_candidate_content_sha256"] != canonical_sha256(run.to_dict())
            or observations["input_candidate_content_sha256"] != report["input_candidate_content_sha256"]
            or report["annotation_content_sha256"] != canonical_sha256(labels.to_dict())
            or report["input_model_provenance"] != run.model_provenance.to_dict()
            or report["config"] != observations["config"]
            or [f["frame_index"] for f in report["frame_results"]] != [f["frame_index"] for f in observations["frames"]]):
        raise ValueError("Saved report observation/candidate/annotation provenance differs")
    for frame, observation, annotation in zip(report["frame_results"], observations["frames"], labels.annotations):
        emitted = observation["emitted_candidate_indices"]
        if frame["accepted_detection_count"] != len(emitted) or (frame["matched_candidate_index"] is not None and frame["matched_candidate_index"] not in emitted):
            raise ValueError("Saved frame does not describe the bound selected observations")
        status = ("localization_eligible" if annotation.localization_eligible else
                  "not_visible_negative" if annotation.annotation_status == "labeled" and annotation.visibility == "not_visible"
                  and annotation.game_ball_identity_certainty in {"certain", "probable"} else "unscored")
        if (frame["annotation_status"] != annotation.annotation_status or frame["visibility"] != annotation.visibility
                or frame["scoring_status"] != status):
            raise ValueError("Saved frame annotation eligibility differs from bound labels")


def _pool_digest(value):
    return canonical_sha256({k: v for k, v in value.items() if k != "content_sha256"})


def _pool_path(root, purpose):
    return safe_path(root, f"{OUTPUT_ROOT}/evaluation/{purpose}.json", OUTPUT_ROOT)


def _pool_metadata(m, p, purpose, commit):
    return {"schema_version": POOL_SCHEMA, "purpose": purpose, "experiment_spec_sha256": spec_digest(m),
            "code_commit": commit, "assembly_code_commit": commit, "prior_motion_execution_commit": PRIOR_COMMIT,
            "provenance_semantics": "Reused reports retain their original model, ranking and evaluator provenance; assembly commit describes this comparison only.",
            "saved_control_scoring_reports": p["saved_control_scoring_reports"], "saved_control_outputs": p["saved_control_outputs"],
            "annotation_bindings": p["scoring_labels"], "crop_input_bindings": [w["crop_candidates"] for w in p["windows"]],
            "reused_report_count": 405, "new_report_count": 405, "reused_aggregate_count": 135, "new_aggregate_count": 135,
            "selected_operating_point": None, "quality_gate": None}


def _validate_pool(value, m, p, purpose, commit, saved, evidence):
    metadata = _pool_metadata(m, p, purpose, commit)
    if (set(value) != set(metadata) | {"evaluation_reports", "aggregate_results", "paired_differences",
                                      "loss_decomposition", "aggregate_paired_differences", "content_sha256"}
            or any(value.get(k) != v for k, v in metadata.items())
            or value.get("content_sha256") != _pool_digest(value)
            or value["evaluation_reports"][:405] != saved["evaluation_reports"]
            or value["aggregate_results"][:135] != saved["aggregate_results"]):
        raise ValueError("Composed detector pool changed controls or provenance")
    reports, aggregates = value["evaluation_reports"][405:], value["aggregate_results"][135:]
    _validate_grid(reports, aggregates, p, purpose, experiment_grid(), commit, REPORT_SCHEMA)
    report_index = _report_index(reports)
    for w in (w for w in p["windows"] if w["purpose"] == purpose):
        labels, run, observations, _ = evidence[w["window_id"]]
        for c in experiment_grid():
            for radius in RADII:
                report = report_index[(purpose, w["possession_id"], w["start_frame_index"], w["end_frame_index"], c.arm, c.confidence_threshold, radius)]
                _bind_report(report, labels, run, observations[c.variant_id])
    pairs, losses = paired_differences(value["evaluation_reports"])
    if (len(pairs) != 405 or len(losses) != 810 or value["paired_differences"] != pairs
            or value["loss_decomposition"] != losses
            or value["aggregate_paired_differences"] != aggregate_paired_differences(value["aggregate_results"])):
        raise ValueError("Saved detector contrasts or loss partitions differ")


def load_scoring_pools(root, m, p, commit, *, inputs=None):
    """Validate persisted comparison pools without selecting or scoring candidates."""
    saved = _saved_pools(root, p)
    evidence = _load_evidence(root, m, p, commit, saved, inputs)
    pools = {}
    for purpose in p["pool_separation"]:
        value = read_json(_pool_path(root, purpose))
        _validate_pool(value, m, p, purpose, commit, saved[purpose], evidence)
        pools[purpose] = value
    return pools


def score_experiment(root, path):
    m, p, inputs, commit = preflight(root, path)
    saved = _saved_pools(root, p)
    evidence = _load_evidence(root, m, p, commit, saved, inputs)
    pools = {}
    # Verify every existing pool before generating or publishing any missing pool.
    for purpose in p["pool_separation"]:
        target = _pool_path(root, purpose)
        if target.exists():
            value = read_json(target)
            _validate_pool(value, m, p, purpose, commit, saved[purpose], evidence)
            pools[purpose] = value
    for purpose in p["pool_separation"]:
        if purpose in pools:
            continue
        reports = []
        for w in (w for w in p["windows"] if w["purpose"] == purpose):
            labels, run, observations, _ = evidence[w["window_id"]]
            for c in experiment_grid():
                for radius in RADII:
                    reports.append(_evaluate_validated(labels, run, observations[c.variant_id], radius, commit))
        aggregates = [aggregate([r for r in reports if r["variant_id"] == c.variant_id and r["localization_radius_px"] == radius])
                      for c in experiment_grid() for radius in RADII]
        _validate_grid(reports, aggregates, p, purpose, experiment_grid(), commit, REPORT_SCHEMA)
        reports = [*saved[purpose]["evaluation_reports"], *reports]
        aggregates = [*saved[purpose]["aggregate_results"], *aggregates]
        pairs, losses = paired_differences(reports)
        value = {**_pool_metadata(m, p, purpose, commit), "evaluation_reports": reports, "aggregate_results": aggregates,
                 "paired_differences": pairs, "loss_decomposition": losses,
                 "aggregate_paired_differences": aggregate_paired_differences(aggregates)}
        value["content_sha256"] = _pool_digest(value)
        _validate_pool(value, m, p, purpose, commit, saved[purpose], evidence)
        pools[purpose] = value
    unchanged(root, path, m, commit)
    # Re-read all bindings before publication, including controls and selected inputs.
    if _load_evidence(root, m, p, commit, _saved_pools(root, p), inputs) != evidence:
        raise ValueError("Detector scoring inputs changed during scoring")
    bindings = []
    for purpose in p["pool_separation"]:
        target = _pool_path(root, purpose)
        persist_once(target, pools[purpose])
        bindings.append(file_binding(root, target))
    unchanged(root, path, m, commit)
    return {"reports": bindings, "new_per_window_reports": 810, "reused_per_window_reports": 810,
            "per_window_reports": 1620, "new_aggregate_cells_per_pool": 135,
            "reused_aggregate_cells_per_pool": 135, "aggregate_cells_per_pool": 270,
            "saved_controls_reranked": 0, "saved_controls_rescored": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.repository_root.resolve()
    print(json.dumps(score_experiment(root, (root/args.manifest).resolve()), indent=2))


if __name__ == "__main__":
    main()
