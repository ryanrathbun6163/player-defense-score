"""Score only new context arms and compose unchanged saved control reports."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

from .annotations import load_annotations
from . import crop_motion_factorial as controls
from .crop_motion_evaluation import aggregate, selected_frame
from .crop_player_context import ARMS, experiment_grid, validate_observations
from .crop_player_context_experiment import (
    OUTPUT_ROOT, PRIOR_COMMIT, load_observations, load_saved_control, preflight, unchanged,
)
from .development_experiments import bound_file, canonical_sha256, read_json, require_digest, safe_path
from .evaluation import evaluate_detections
from .temporal_association import RADII, THRESHOLDS
from .temporal_evaluation import _runs
from .temporal_experiment import file_binding, persist_once, spec_digest
from .tiled_evaluation import METRICS

CONTROL_PAIRS = dict(zip(ARMS, controls.ARMS[3:]))
POOL_SCHEMA = "ball_crop_player_context_pool/v0.1"


def _evaluate_validated(labels, run, observations, radius, commit):
    view = replace(run, frames=tuple(selected_frame(f, o) for f, o in zip(run.frames, observations["frames"])))
    score = evaluate_detections(labels, view, confidence_threshold=observations["config"]["confidence_threshold"],
                                localization_radius_px=radius)
    emitted = sum(bool(f["emitted_candidate_indices"]) for f in observations["frames"])
    return {
        "schema_version": "ball_crop_player_context_evaluation/v0.1",
        "variant_id": observations["variant_id"], "config": observations["config"],
        "localization_radius_px": radius, "selection_purpose": labels.window.selection_purpose,
        "possession_id": run.possession_id, "source_video": run.source_video.to_dict(), "window": run.window.to_dict(),
        "input_model_provenance": run.model_provenance.to_dict(),
        "ranking_code_commit": observations["ranking_code_commit"], "evaluator_code_commit": commit,
        "observations_content_sha256": canonical_sha256(observations),
        "input_candidate_content_sha256": observations["input_candidate_content_sha256"],
        "input_context_content_sha256": observations["input_context_content_sha256"],
        "window_rows_sha256": observations["window_rows_sha256"],
        "annotation_content_sha256": score["annotation_content_sha256"],
        "matching_rule": "raw center distance; uncertainty diagnostic only",
        "metrics": {k: score[k] for k in METRICS}, "frame_results": score["frame_results"],
        "temporal_metrics": {
            "emitted_frame_count": emitted, "missing_frame_count": len(run.frames)-emitted,
            "frame_count": len(run.frames), "emitted_frame_coverage": emitted/len(run.frames),
            "longest_consecutive_missed_eligible_run": max(_runs([f["false_negative_count"] == 1 for f in score["frame_results"]]), default=0),
            "correct_match_run_lengths": _runs([f["matched_candidate_index"] is not None for f in score["frame_results"]]),
        },
        "context_metrics": {
            "frames_without_observed_boxes": [f["frame_index"] for f in observations["frames"] if f["context_unavailable"]],
            "observed_box_counts": [{"frame_index": f["frame_index"], "box_count": f["context_available_box_count"]}
                                    for f in observations["frames"]],
        },
        "selected_operating_point": None, "quality_gate": None,
    }


def evaluate_observations(labels, run, observations, radius, commit, context_window):
    require_digest(commit, "context evaluator commit", 40)
    if radius not in RADII or isinstance(radius, bool):
        raise ValueError("Undeclared context evaluation radius")
    validate_observations(observations, run, context_window)
    return _evaluate_validated(labels, run, observations, radius, commit)


def _key(report):
    return (report["possession_id"], report["config"]["arm"], report["config"]["confidence_threshold"],
            report["localization_radius_px"])


def _report_index(reports):
    result = {}
    for report in reports:
        key = _key(report)
        if key in result:
            raise ValueError("Duplicate player context scoring cell")
        result[key] = report
    return result


def _cell(index, report, arm, threshold=None):
    key = (report["possession_id"], arm,
           report["config"]["confidence_threshold"] if threshold is None else threshold,
           report["localization_radius_px"])
    if key not in index:
        raise ValueError("Incomplete player context comparison cell")
    other = index[key]
    identity = ("source_video", "window", "selection_purpose", "input_model_provenance",
                "input_candidate_content_sha256", "annotation_content_sha256", "matching_rule")
    if any(other[k] != report[k] for k in identity):
        raise ValueError("Context comparison mixes sources, labels or pools")
    # Old and new ranking/evaluation commits intentionally differ; never relabel controls.
    return other


def _correct(report):
    return {f["frame_index"] for f in report["frame_results"] if f["matched_candidate_index"] is not None}


def _changes(before, after):
    old, new = _correct(before), _correct(after)
    return {
        "newly_recovered_frames": sorted(new-old), "newly_lost_frames": sorted(old-new),
        **{name: after["metrics"][key]-before["metrics"][key] for name, key in (
            ("true_positive_delta", "true_positive_count"), ("false_positive_delta", "false_positive_count"),
            ("false_negative_delta", "false_negative_count"), ("hidden_false_alarm_delta", "non_visible_false_alarm_count"))},
        "emitted_frame_delta": after["temporal_metrics"]["emitted_frame_count"]-before["temporal_metrics"]["emitted_frame_count"],
    }


def observation_changes(before, after):
    """Describe changed observed endpoints/support separately from localization gains."""
    if [f["frame_index"] for f in before["frames"]] != [f["frame_index"] for f in after["frames"]]:
        raise ValueError("Paired observation frame alignment differs")
    changed, abstained, resumed, support = [], [], [], []
    for old, new in zip(before["frames"], after["frames"]):
        frame = old["frame_index"]
        if old["emitted_candidate_indices"] != new["emitted_candidate_indices"]:
            changed.append(frame)
        if old["emitted_candidate_indices"] and not new["emitted_candidate_indices"]:
            abstained.append(frame)
        if new["emitted_candidate_indices"] and not old["emitted_candidate_indices"]:
            resumed.append(frame)
        a, b = old["ranking"]["winner"], new["ranking"]["winner"]
        if a["path"] != b["path"] or a["endpoint"] != b["endpoint"]:
            support.append({"frame_index": frame, "control_endpoint": a["endpoint"], "context_endpoint": b["endpoint"],
                            "control_path": a["path"], "context_path": b["path"],
                            "control_support_nodes": len(a["path"]), "context_support_nodes": len(b["path"]),
                            "support_node_delta": len(b["path"])-len(a["path"])})
    return {"changed_emission_frames": changed, "newly_abstained_frames": abstained,
            "newly_emitted_frames": resumed, "changed_path_support": support}


def paired_differences(reports, observations):
    index = _report_index(reports)
    differences, decomposition = [], []
    for report in reports:
        config = report["config"]
        if config["arm"] not in CONTROL_PAIRS:
            continue
        baseline = _cell(index, report, CONTROL_PAIRS[config["arm"]])
        for k in ("candidate_cap", "edge_step", "cost_step", "confidence_threshold"):
            if config[k] != baseline["config"][k]:
                raise ValueError("Context pair changes motion settings")
        key = (report["selection_purpose"], report["possession_id"], config["arm"], config["confidence_threshold"])
        control_key = (report["selection_purpose"], report["possession_id"], baseline["config"]["arm"], config["confidence_threshold"])
        if key not in observations or control_key not in observations:
            raise ValueError("Missing paired observation trace")
        for observation_key, bound_report in ((key, report), (control_key, baseline)):
            obs = observations[observation_key]
            if ([f["frame_index"] for f in obs["frames"]] != [f["frame_index"] for f in bound_report["frame_results"]]
                    or canonical_sha256(obs) != bound_report["observations_content_sha256"]):
                raise ValueError("Paired observation/report window or content differs")
        differences.append({"possession_id": report["possession_id"], "config": config,
                            "control_config": baseline["config"], "radius_px": report["localization_radius_px"],
                            "control_ranking_commit": baseline["ranking_code_commit"],
                            "context_ranking_commit": report["ranking_code_commit"],
                            **_changes(baseline, report),
                            **observation_changes(observations[control_key], observations[key])})
        raw = _cell(index, report, controls.ARMS[0])
        floor = _cell(index, report, controls.ARMS[0], THRESHOLDS[0])
        cap = _cell(index, report, controls.ARMS[2])
        new, capped, qualified, available = map(_correct, (report, cap, raw, floor))
        if not new <= capped <= qualified <= available:
            raise ValueError("Context matched candidate is outside saved raw/capped availability")
        unavailable = {f["frame_index"] for f in floor["frame_results"] if f["false_negative_count"]}
        filtered, cap_lost, ranking_lost = available-qualified, qualified-capped, capped-new
        misses = {f["frame_index"] for f in report["frame_results"] if f["false_negative_count"]}
        parts = (unavailable, filtered, cap_lost, ranking_lost)
        if set.union(*parts) != misses or sum(map(len, parts)) != len(misses) or len(misses) != report["metrics"]["false_negative_count"]:
            raise ValueError("Context false-negative loss partition differs")
        decomposition.append({"possession_id": report["possession_id"], "config": config,
                              "radius_px": report["localization_radius_px"],
                              "no_candidate_at_export_floor_frames": sorted(unavailable),
                              "confidence_filter_lost_frames": sorted(filtered),
                              "raw_no_qualifying_candidate_frames": sorted(unavailable|filtered),
                              "cap_lost_frames": sorted(cap_lost), "additional_ranking_lost_frames": sorted(ranking_lost)})
    return differences, decomposition


def aggregate_paired_differences(aggregates):
    index = {}
    for r in aggregates:
        key = (r["config"]["arm"], r["config"]["confidence_threshold"], r["localization_radius_px"])
        if key in index:
            raise ValueError("Duplicate context aggregate cell")
        index[key] = r
    pairs = []
    for r in aggregates:
        c = r["config"]
        if c["arm"] not in CONTROL_PAIRS:
            continue
        old = index.get((CONTROL_PAIRS[c["arm"]], c["confidence_threshold"], r["localization_radius_px"]))
        if old is None or any(old[k] != r[k] for k in ("selection_purpose", "input_model_provenance", "window_count")):
            raise ValueError("Incomplete or mixed aggregate comparison")
        pairs.append({"config": c, "control_config": old["config"], "radius_px": r["localization_radius_px"],
                      "selection_purpose": r["selection_purpose"],
                      **{k+"_delta": r["metrics"][k]-old["metrics"][k] for k in (
                          "true_positive_count", "false_positive_count", "false_negative_count", "non_visible_false_alarm_count")}})
    return pairs


def _saved_pools(root, p):
    pools = {}
    for purpose, binding in zip(p["pool_separation"], p["saved_control_scoring_reports"]):
        payload = read_json(bound_file(root, binding, "data/outputs/ball_tracking/crop_motion_factorial"))
        if (payload["schema_version"] != "ball_crop_motion_pool/v0.1" or payload["purpose"] != purpose
                or payload["code_commit"] != PRIOR_COMMIT or payload["selected_operating_point"] is not None
                or payload["quality_gate"] is not None or len(payload["evaluation_reports"]) != 945
                or len(payload["aggregate_results"]) != 315):
            raise ValueError("Incomplete or mixed saved motion scoring pool")
        _validate_grid(payload["evaluation_reports"], payload["aggregate_results"], p, purpose,
                       controls.experiment_grid(), PRIOR_COMMIT, "ball_crop_motion_evaluation/v0.1")
        pools[purpose] = payload
    if len(pools) != 2:
        raise ValueError("Expected two saved scoring pools")
    return pools


def _validate_grid(reports, aggregates, p, purpose, configs, commit, schema):
    windows = {w["possession_id"]: w for w in p["windows"] if w["purpose"] == purpose}
    index = _report_index(reports)
    expected = {(pid, c.arm, c.confidence_threshold, radius) for pid in windows for c in configs for radius in RADII}
    if set(index) != expected:
        raise ValueError("Incomplete scoring grid")
    config_map = {c.variant_id: asdict(c) for c in configs}
    for r in reports:
        w = windows[r["possession_id"]]
        if (r["schema_version"] != schema or r["config"] != config_map.get(r["variant_id"])
                or r["ranking_code_commit"] != commit or r["evaluator_code_commit"] != commit
                or r["selection_purpose"] != purpose or r["source_video"] != w["source_video"]
                or r["window"] != {k: w[k] for k in ("start_frame_index", "end_frame_index")}
                or [f["frame_index"] for f in r["frame_results"]] != list(range(w["start_frame_index"], w["end_frame_index"]+1))):
            raise ValueError("Scoring report identity/provenance mismatch")
    keys = set()
    for a in aggregates:
        key = (a["config"]["arm"], a["config"]["confidence_threshold"], a["localization_radius_px"])
        if (key in keys or a["config"] != config_map.get(a["variant_id"]) or a["selection_purpose"] != purpose
                or a["ranking_code_commit"] != commit or a["evaluator_code_commit"] != commit
                or a["window_count"] != 3 or len(a["per_window"]) != 3
                or {w["possession_id"] for w in a["per_window"]} != set(windows)):
            raise ValueError("Aggregate identity/provenance mismatch")
        keys.add(key)
    if keys != {(c.arm, c.confidence_threshold, r) for c in configs for r in RADII}:
        raise ValueError("Incomplete aggregate grid")


def _pool_digest(payload):
    return canonical_sha256({k: v for k, v in payload.items() if k != "content_sha256"})


def load_scoring_pools(root, m, p, commit):
    """Validate composed saved reports for review without evaluating any candidate."""
    saved = _saved_pools(root, p)
    snapshot = read_json(bound_file(root, p["player_context"]["snapshot"],
                                    "data/outputs/ball_tracking/candidate_identity_diagnosis"))
    contexts = {(w["purpose"], w["possession_id"]): w for w in snapshot["windows"]}
    pools = {}
    for purpose in p["pool_separation"]:
        target = safe_path(root, f"{OUTPUT_ROOT}/evaluation/{purpose}.json", OUTPUT_ROOT)
        value = read_json(target)
        if (value["schema_version"] != POOL_SCHEMA or value["purpose"] != purpose
                or value["experiment_spec_sha256"] != spec_digest(m) or value["assembly_code_commit"] != commit
                or value["content_sha256"] != _pool_digest(value)
                or value["saved_control_scoring_reports"] != p["saved_control_scoring_reports"]
                or value["saved_control_outputs"] != p["saved_control_outputs"]
                or value["input_player_context_file"] != p["player_context"]["snapshot"]
                or value["annotation_bindings"] != p["scoring_labels"]
                or value["crop_input_bindings"] != [w["crop_candidates"] for w in p["windows"]]
                or value["prior_motion_execution_commit"] != PRIOR_COMMIT or value["code_commit"] != commit
                or value["selected_operating_point"] is not None or value["quality_gate"] is not None
                or [value[k] for k in ("reused_report_count", "new_report_count", "reused_aggregate_count", "new_aggregate_count")]
                != [945, 540, 315, 180]
                or value["evaluation_reports"][:945] != saved[purpose]["evaluation_reports"]
                or value["aggregate_results"][:315] != saved[purpose]["aggregate_results"]):
            raise ValueError("Composed context pool changed saved controls or provenance")
        _validate_grid(value["evaluation_reports"][945:], value["aggregate_results"][315:], p, purpose,
                       experiment_grid(), commit, "ball_crop_player_context_evaluation/v0.1")
        saved_index = _report_index(saved[purpose]["evaluation_reports"])
        for report in value["evaluation_reports"][945:]:
            _cell(saved_index, report, CONTROL_PAIRS[report["config"]["arm"]])
            context = contexts[purpose, report["possession_id"]]
            counts = context["per_frame_box_counts"]
            expected_metrics = {
                "frames_without_observed_boxes": [int(f) for f, n in counts.items() if n == 0],
                "observed_box_counts": [{"frame_index": int(f), "box_count": n} for f, n in counts.items()],
            }
            if (report["input_context_content_sha256"] != canonical_sha256(context)
                    or report["window_rows_sha256"] != context["selected_rows_sha256"]
                    or report["context_metrics"] != expected_metrics):
                raise ValueError("Context report differs from frozen context provenance or availability")
        if len(value["paired_differences"]) != 540 or len(value["loss_decomposition"]) != 540 or len(value["aggregate_paired_differences"]) != 180:
            raise ValueError("Incomplete paired context report")
        pools[purpose] = value
    return pools


def score_experiment(root, path):
    m, p, inputs, commit = preflight(root, path)
    saved = _saved_pools(root, p)
    new_pools = {purpose: [] for purpose in p["pool_separation"]}
    observations = {}
    for window, (_, run, digest, context), label in zip(p["windows"], inputs, p["scoring_labels"]):
        if label["window_id"] != window["window_id"]:
            raise ValueError("Context scoring label window mismatch")
        labels = load_annotations(bound_file(root, label["annotation"], "configs/ball_tracking/annotations"))
        if labels.window.selection_purpose != window["purpose"] or labels.annotation_set_id != window["annotation_set_id"]:
            raise ValueError("Context scoring label identity mismatch")
        saved_index = _report_index(saved[window["purpose"]]["evaluation_reports"])
        for config in controls.experiment_grid():
            obs = load_saved_control(root, p, window, config, run=run, crop_digest=digest)
            observations[(window["purpose"], run.possession_id, config.arm, config.confidence_threshold)] = obs
            for radius in RADII:
                report = saved_index[(run.possession_id, config.arm, config.confidence_threshold, radius)]
                if (report["observations_content_sha256"] != canonical_sha256(obs)
                        or report["input_candidate_content_sha256"] != canonical_sha256(run.to_dict())
                        or report["annotation_content_sha256"] != canonical_sha256(labels.to_dict())):
                    raise ValueError("Saved report observation/candidate/label provenance mismatch")
        for config in experiment_grid():
            obs = load_observations(root, m, window, run, digest, config, commit, context)
            observations[(window["purpose"], run.possession_id, config.arm, config.confidence_threshold)] = obs
            for radius in RADII:
                new_pools[window["purpose"]].append(_evaluate_validated(labels, run, obs, radius, commit))
    outputs = []
    for purpose, new in new_pools.items():
        new_aggregates = [aggregate([r for r in new if r["variant_id"] == c.variant_id and r["localization_radius_px"] == radius])
                          for c in experiment_grid() for radius in RADII]
        _validate_grid(new, new_aggregates, p, purpose, experiment_grid(), commit, "ball_crop_player_context_evaluation/v0.1")
        reports = [*saved[purpose]["evaluation_reports"], *new]
        aggregates = [*saved[purpose]["aggregate_results"], *new_aggregates]
        differences, losses = paired_differences(reports, observations)
        aggregate_differences = aggregate_paired_differences(aggregates)
        if len(differences) != 540 or len(losses) != 540 or len(aggregate_differences) != 180:
            raise ValueError("Incomplete context comparison")
        payload = {"schema_version": POOL_SCHEMA, "purpose": purpose, "experiment_spec_sha256": spec_digest(m),
                   "assembly_code_commit": commit, "code_commit": commit,
                   "provenance_semantics": "Assembly commit describes this comparison; each reused report/aggregate retains its original ranking and evaluator commits unchanged.",
                   "saved_control_scoring_reports": p["saved_control_scoring_reports"],
                   "saved_control_outputs": p["saved_control_outputs"], "prior_motion_execution_commit": PRIOR_COMMIT,
                   "input_player_context_file": p["player_context"]["snapshot"], "annotation_bindings": p["scoring_labels"],
                   "crop_input_bindings": [w["crop_candidates"] for w in p["windows"]],
                   "reused_report_count": 945, "new_report_count": 540,
                   "reused_aggregate_count": 315, "new_aggregate_count": 180,
                   "evaluation_reports": reports, "aggregate_results": aggregates,
                   "paired_differences": differences, "loss_decomposition": losses,
                   "aggregate_paired_differences": aggregate_differences,
                   "selected_operating_point": None, "quality_gate": None}
        payload["content_sha256"] = _pool_digest(payload)
        outputs.append((safe_path(root, f"{OUTPUT_ROOT}/evaluation/{purpose}.json", OUTPUT_ROOT), payload))
    unchanged(root, path, m, commit)
    for item in p["scoring_labels"]:
        bound_file(root, item["annotation"], "configs/ball_tracking/annotations")
    _saved_pools(root, p)
    # Refuse changed existing pools before publishing either one.
    for target, payload in outputs:
        if target.exists() and read_json(target) != payload:
            raise ValueError("Refusing changed existing context pool")
    bindings = []
    for target, payload in outputs:
        persist_once(target, payload)
        bindings.append(file_binding(root, target))
    unchanged(root, path, m, commit)
    return {"reports": bindings, "new_per_window_reports": 1080, "reused_per_window_reports": 1890,
            "per_window_reports": 2970, "new_aggregate_cells_per_pool": 180,
            "reused_aggregate_cells_per_pool": 315, "aggregate_cells_per_pool": 495,
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
