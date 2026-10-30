"""Separate scoring, full saved-control parity, and motion-factorial contrasts."""
from __future__ import annotations

from dataclasses import asdict, replace

from .annotations import load_annotations
from .crop_motion_factorial import (
    ARMS,
    RankingConfig,
    experiment_grid,
    legacy_config,
    validate_observations,
    verify_control_trace,
)
from .crop_motion_experiment import (
    OUTPUT_ROOT,
    load_observations,
    load_saved_control,
    preflight,
    unchanged,
)
from .crop_ranking_experiment import OUTPUT_ROOT as CONTROL_ROOT
from .development_experiments import (
    bound_file,
    canonical_sha256,
    read_json,
    require_digest,
    safe_path,
)
from .evaluation import evaluate_detections
from .temporal_association import RADII
from .temporal_evaluation import _runs
from .temporal_experiment import file_binding, persist_once, spec_digest
from .tiled_evaluation import COUNTS, METRICS


def selected_frame(frame, observation):
    emitted = set(observation["emitted_candidate_indices"])
    return replace(
        frame,
        detections=tuple(c for c in frame.detections if c.candidate_index in emitted),
    )


def _evaluate_validated(labels, run, observations, radius, commit):
    view = replace(
        run,
        frames=tuple(selected_frame(f, o) for f, o in zip(run.frames, observations["frames"])),
    )
    score = evaluate_detections(
        labels,
        view,
        confidence_threshold=observations["config"]["confidence_threshold"],
        localization_radius_px=radius,
    )
    missed = _runs([f["false_negative_count"] == 1 for f in score["frame_results"]])
    correct = _runs([f["matched_candidate_index"] is not None for f in score["frame_results"]])
    emitted = sum(bool(f["emitted_candidate_indices"]) for f in observations["frames"])
    return {
        "schema_version": "ball_crop_motion_evaluation/v0.1",
        "variant_id": observations["variant_id"],
        "config": observations["config"],
        "localization_radius_px": radius,
        "selection_purpose": labels.window.selection_purpose,
        "possession_id": run.possession_id,
        "source_video": run.source_video.to_dict(),
        "window": run.window.to_dict(),
        "input_model_provenance": run.model_provenance.to_dict(),
        "ranking_code_commit": observations["ranking_code_commit"],
        "evaluator_code_commit": commit,
        "observations_content_sha256": canonical_sha256(observations),
        "input_candidate_content_sha256": observations["input_candidate_content_sha256"],
        "annotation_content_sha256": score["annotation_content_sha256"],
        "matching_rule": "raw center distance; uncertainty diagnostic only",
        "metrics": {k: score[k] for k in METRICS},
        "frame_results": score["frame_results"],
        "temporal_metrics": {
            "emitted_frame_count": emitted,
            "missing_frame_count": len(run.frames) - emitted,
            "frame_count": len(run.frames),
            "emitted_frame_coverage": emitted / len(run.frames),
            "longest_consecutive_missed_eligible_run": max(missed, default=0),
            "correct_match_run_lengths": correct,
        },
        "selected_operating_point": None,
        "quality_gate": None,
    }


def evaluate_observations(labels, run, observations, radius, commit):
    require_digest(commit, "evaluator commit", 40)
    if radius not in RADII or isinstance(radius, bool):
        raise ValueError("Undeclared motion-factorial evaluation radius")
    validate_observations(observations, run)
    return _evaluate_validated(labels, run, observations, radius, commit)


def aggregate(reports):
    if not reports:
        raise ValueError("Empty motion-factorial scoring pool")
    first = reports[0]
    keys = (
        "variant_id", "config", "localization_radius_px", "selection_purpose",
        "input_model_provenance", "ranking_code_commit", "evaluator_code_commit",
    )
    if any(any(r[k] != first[k] for k in keys) for r in reports):
        raise ValueError("Mixed motion-factorial settings, pools, or provenance")
    if len({r["possession_id"] for r in reports}) != len(reports):
        raise ValueError("Duplicate possession in motion-factorial pool")
    metrics = {k: sum(r["metrics"][k] for r in reports) for k in COUNTS}
    tp, fp, fn = (metrics[k] for k in (
        "true_positive_count", "false_positive_count", "false_negative_count",
    ))
    metrics.update(
        precision=tp / (tp + fp) if tp + fp else None,
        recall=tp / (tp + fn) if tp + fn else None,
    )
    return {
        **{k: first[k] for k in keys},
        "metrics": metrics,
        "window_count": len(reports),
        "per_window": [
            {"possession_id": r["possession_id"], "window": r["window"],
             "metrics": r["metrics"], "temporal_metrics": r["temporal_metrics"]}
            for r in reports
        ],
        "selected_operating_point": None,
        "quality_gate": None,
    }


def verify_control_parity(report, saved):
    """Only explicit configuration/provenance metadata may differ from controls."""
    mapped = legacy_config(RankingConfig(**report["config"]))
    if (mapped is None or saved["config"] != asdict(mapped)
            or saved["variant_id"] != mapped.variant_id):
        raise ValueError("Saved ranking control configuration differs")
    identity = (
        "possession_id", "source_video", "window", "selection_purpose",
        "localization_radius_px", "input_model_provenance",
        "input_candidate_content_sha256", "annotation_content_sha256", "matching_rule",
    )
    if any(report[k] != saved[k] for k in identity):
        raise ValueError("Saved ranking control scoring identity differs")
    if any(report[k] != saved[k] for k in ("metrics", "frame_results", "temporal_metrics")):
        raise ValueError("Saved ranking control scoring outcomes differ")


def verify_aggregate_control_parity(report, saved):
    mapped = legacy_config(RankingConfig(**report["config"]))
    if (mapped is None or saved["config"] != asdict(mapped)
            or saved["variant_id"] != mapped.variant_id):
        raise ValueError("Saved ranking aggregate configuration differs")
    for key in ("localization_radius_px", "selection_purpose", "input_model_provenance",
                "metrics", "window_count", "per_window", "selected_operating_point", "quality_gate"):
        if report[key] != saved[key]:
            raise ValueError("Saved ranking aggregate outcomes or identity differ")


def _report_index(reports):
    index = {}
    for report in reports:
        config = report["config"]
        key = (report["possession_id"], config["arm"], config["confidence_threshold"],
               report["localization_radius_px"])
        if key in index:
            raise ValueError("Duplicate motion-factorial scoring cell")
        index[key] = report
    return index


def _cell(index, report, arm):
    key = (report["possession_id"], arm, report["config"]["confidence_threshold"],
           report["localization_radius_px"])
    if key not in index:
        raise ValueError("Incomplete motion-factorial comparison cell")
    other = index[key]
    identity = (
        "source_video", "window", "selection_purpose", "input_model_provenance",
        "ranking_code_commit", "evaluator_code_commit", "input_candidate_content_sha256",
        "annotation_content_sha256", "matching_rule",
    )
    if any(other[k] != report[k] for k in identity):
        raise ValueError("Motion-factorial comparison mixes inputs, pools, or provenance")
    return other


def _correct(report):
    return {f["frame_index"] for f in report["frame_results"]
            if f["matched_candidate_index"] is not None}


def _changes(before, after):
    old, new = _correct(before), _correct(after)
    return {
        "newly_recovered_frames": sorted(new - old),
        "newly_lost_frames": sorted(old - new),
        "true_positive_delta": after["metrics"]["true_positive_count"] - before["metrics"]["true_positive_count"],
        "false_positive_delta": after["metrics"]["false_positive_count"] - before["metrics"]["false_positive_count"],
        "false_negative_delta": after["metrics"]["false_negative_count"] - before["metrics"]["false_negative_count"],
        "hidden_false_alarm_delta": after["metrics"]["non_visible_false_alarm_count"] - before["metrics"]["non_visible_false_alarm_count"],
        "emitted_frame_delta": after["temporal_metrics"]["emitted_frame_count"] - before["temporal_metrics"]["emitted_frame_count"],
    }


def paired_differences(reports):
    """Compare every graph arm with three controls and partition its misses."""
    index = _report_index(reports)
    differences, decomposition = [], []
    for report in reports:
        config = report["config"]
        if config["arm"] not in ARMS[3:]:
            continue
        raw, top_one, capped = (_cell(index, report, arm) for arm in ARMS[:3])
        new, uncapped, limited = _correct(report), _correct(raw), _correct(capped)
        for baseline in (raw, top_one, capped):
            differences.append({
                "possession_id": report["possession_id"], "config": config,
                "radius_px": report["localization_radius_px"],
                "control": baseline["config"]["arm"], **_changes(baseline, report),
            })
        if not new <= limited <= uncapped:
            raise ValueError("Graph matches must reference qualifying capped raw candidates")
        raw_missing = {f["frame_index"] for f in raw["frame_results"]
                       if f["false_negative_count"]}
        cap_missing, ranking_missing = uncapped - limited, limited - new
        misses = {f["frame_index"] for f in report["frame_results"]
                  if f["false_negative_count"]}
        parts = (raw_missing, cap_missing, ranking_missing)
        if (set.union(*parts) != misses or sum(map(len, parts)) != len(misses)
                or len(misses) != report["metrics"]["false_negative_count"]):
            raise ValueError("Motion-factorial false-negative partition differs")
        decomposition.append({
            "possession_id": report["possession_id"], "config": config,
            "radius_px": report["localization_radius_px"],
            "raw_no_qualifying_candidate_frames": sorted(raw_missing),
            "cap_lost_frames": sorted(cap_missing),
            "additional_ranking_lost_frames": sorted(ranking_missing),
        })
    return differences, decomposition


def factorial_differences(reports):
    """Four same-cell contrasts, always changing the named parameter .01 -> .03."""
    index = _report_index(reports)
    comparisons = []
    anchors = {}
    for report in reports:
        if report["config"]["arm"] in ARMS[3:]:
            key = (report["possession_id"], report["config"]["confidence_threshold"],
                   report["localization_radius_px"])
            anchors[key] = _cell(index, report, ARMS[3])
    # ARMS follows the approved order: controls, TT, TW, WT, WW.
    pairs = (
        (ARMS[3], ARMS[5], "edge_step", "cost_step", .01),
        (ARMS[4], ARMS[6], "edge_step", "cost_step", .03),
        (ARMS[3], ARMS[4], "cost_step", "edge_step", .01),
        (ARMS[5], ARMS[6], "cost_step", "edge_step", .03),
    )
    for anchor in anchors.values():
        for before_arm, after_arm, varying, fixed, value in pairs:
            before, after = (_cell(index, anchor, arm) for arm in (before_arm, after_arm))
            if (before["config"][fixed] != value or after["config"][fixed] != value
                    or before["config"][varying] != .01 or after["config"][varying] != .03):
                raise ValueError("Motion-factorial pair changes an undeclared parameter")
            comparisons.append({
                "possession_id": anchor["possession_id"],
                "confidence_threshold": anchor["config"]["confidence_threshold"],
                "radius_px": anchor["localization_radius_px"],
                "varying_parameter": varying, "fixed_parameter": fixed, "fixed_value": value,
                "from_config": before["config"], "to_config": after["config"],
                **_changes(before, after),
            })
    return comparisons


def _saved_report_index(payload, purpose, commit):
    if (payload["schema_version"] != "ball_crop_ranking_pool/v0.1"
            or payload["purpose"] != purpose or payload["code_commit"] != commit
            or payload["selected_operating_point"] is not None or payload["quality_gate"] is not None):
        raise ValueError("Saved ranking scoring pool provenance differs")
    reports = payload["evaluation_reports"]
    if len(reports) != 675 or any(
            r["schema_version"] != "ball_crop_ranking_evaluation/v0.1"
            or r["ranking_code_commit"] != commit or r["evaluator_code_commit"] != commit
            or r["selection_purpose"] != purpose for r in reports):
        raise ValueError("Incomplete or mixed saved ranking scoring pool")
    return _report_index(reports)


def _saved_aggregate_index(payload, purpose, commit):
    index = {}
    for report in payload["aggregate_results"]:
        if (report["selection_purpose"] != purpose or report["ranking_code_commit"] != commit
                or report["evaluator_code_commit"] != commit):
            raise ValueError("Mixed saved ranking aggregate provenance")
        config = report["config"]
        key = (config["arm"], config["confidence_threshold"], report["localization_radius_px"])
        if key in index:
            raise ValueError("Duplicate saved ranking aggregate cell")
        index[key] = report
    if len(index) != 225:
        raise ValueError("Incomplete saved ranking aggregate pool")
    return index


def score_experiment(root, path):
    m, p, inputs, commit = preflight(root, path)
    if len(p["saved_ranking_scoring_reports"]) != 2 or len(p["saved_ranking_control_outputs"]) != 270:
        raise ValueError("Incomplete saved ranking control bindings")
    saved_payloads = {
        purpose: read_json(bound_file(root, item, CONTROL_ROOT))
        for purpose, item in zip(p["pool_separation"], p["saved_ranking_scoring_reports"])
    }
    saved = {purpose: _saved_report_index(payload, purpose, p["prior_ranking_execution_commit"])
             for purpose, payload in saved_payloads.items()}
    saved_aggregates = {
        purpose: _saved_aggregate_index(payload, purpose, p["prior_ranking_execution_commit"])
        for purpose, payload in saved_payloads.items()
    }
    pools = {purpose: [] for purpose in p["pool_separation"]}
    parity = trace_parity = 0
    for window, (_, run, digest), label in zip(p["windows"], inputs, p["scoring_labels"]):
        if label["window_id"] != window["window_id"]:
            raise ValueError("Motion-factorial scoring label window mismatch")
        labels = load_annotations(bound_file(root, label["annotation"], "configs/ball_tracking/annotations"))
        if (labels.window.selection_purpose != window["purpose"]
                or labels.annotation_set_id != window["annotation_set_id"]):
            raise ValueError("Motion-factorial scoring label identity mismatch")
        for config in experiment_grid():
            observations = load_observations(root, m, window, run, digest, config, commit)
            mapped = legacy_config(config)
            if mapped is not None:
                control = load_saved_control(root, p, window, config, crop_digest=digest)
                if control is None:
                    raise ValueError("Missing mapped saved ranking observation trace")
                verify_control_trace(observations, control)
                trace_parity += 1
            for radius in RADII:
                report = _evaluate_validated(labels, run, observations, radius, commit)
                if mapped is not None:
                    key = (run.possession_id, mapped.arm, config.confidence_threshold, radius)
                    if key not in saved[window["purpose"]]:
                        raise ValueError("Missing mapped saved ranking scoring cell")
                    verify_control_parity(report, saved[window["purpose"]][key])
                    parity += 1
                pools[window["purpose"]].append(report)
    if parity != 1350 or trace_parity != 270:
        raise ValueError("Incomplete saved ranking control trace/scoring parity audit")

    outputs, aggregate_parity = [], 0
    for purpose, reports in pools.items():
        aggregates = [
            aggregate([r for r in reports if r["variant_id"] == c.variant_id
                       and r["localization_radius_px"] == radius])
            for c in experiment_grid() for radius in RADII
        ]
        if (len(reports) != 945 or len(aggregates) != 315
                or any(a["window_count"] != 3 for a in aggregates)):
            raise ValueError("Incomplete motion-factorial scoring pool")
        for report in aggregates:
            mapped = legacy_config(RankingConfig(**report["config"]))
            if mapped is not None:
                key = (mapped.arm, mapped.confidence_threshold, report["localization_radius_px"])
                if key not in saved_aggregates[purpose]:
                    raise ValueError("Missing mapped saved ranking aggregate cell")
                verify_aggregate_control_parity(report, saved_aggregates[purpose][key])
                aggregate_parity += 1
        differences, decomposition = paired_differences(reports)
        factorial = factorial_differences(reports)
        if len(differences) != 1620 or len(decomposition) != 540 or len(factorial) != 540:
            raise ValueError("Incomplete motion-factorial comparisons or loss partitions")
        payload = {
            "schema_version": "ball_crop_motion_pool/v0.1", "purpose": purpose,
            "experiment_spec_sha256": spec_digest(m), "code_commit": commit,
            "annotation_bindings": p["scoring_labels"],
            "crop_input_bindings": [w["crop_candidates"] for w in p["windows"]],
            "saved_ranking_scoring_reports": p["saved_ranking_scoring_reports"],
            "saved_ranking_control_outputs": p["saved_ranking_control_outputs"],
            "prior_ranking_execution_commit": p["prior_ranking_execution_commit"],
            "evaluation_reports": reports, "aggregate_results": aggregates,
            "paired_differences": differences, "loss_decomposition": decomposition,
            "factorial_comparisons": factorial,
            "saved_control_parity_cells": parity,
            "saved_control_trace_parities": trace_parity,
            "parity_excluded_bookkeeping": [],
            "selected_operating_point": None, "quality_gate": None,
        }
        target = safe_path(root, f"{OUTPUT_ROOT}/evaluation/{purpose}.json", OUTPUT_ROOT)
        outputs.append((target, payload))
    if aggregate_parity != 450:
        raise ValueError("Incomplete saved ranking aggregate parity audit")
    for _, payload in outputs:
        payload["saved_control_aggregate_parities"] = aggregate_parity

    # Check every input again before publishing either pool.
    unchanged(root, path, m, commit)
    for item in p["scoring_labels"]:
        bound_file(root, item["annotation"], "configs/ball_tracking/annotations")
    for item in [*p["saved_ranking_scoring_reports"], *p["saved_ranking_control_outputs"]]:
        bound_file(root, item, CONTROL_ROOT)
    bindings = []
    for target, payload in outputs:
        persist_once(target, payload)
        bindings.append(file_binding(root, target))
    unchanged(root, path, m, commit)
    return {
        "reports": bindings, "per_window_reports": 1890, "aggregate_cells_per_pool": 315,
        "saved_control_parity_cells": parity, "saved_control_trace_parities": trace_parity,
        "saved_control_aggregate_parities": aggregate_parity,
    }
