"""Score recovery-derived views with explicit per-unit inference provenance."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import yolo_crop_evaluation as original
from . import yolo_crop_recovery as backend
from .annotations import load_annotations
from .detections import load_detection_run
from .development_experiments import bound_file, canonical_sha256, read_json, safe_path
from .temporal_association import RADII
from .temporal_experiment import file_binding, persist_once, spec_digest
from .tiled_candidates import candidate_run as saved_crop_run
from .yolo_crop_candidates import experiment_grid

REPORT_SCHEMA = "ball_yolo_crop_evaluation/v0.2"
POOL_SCHEMA = "ball_yolo_crop_pool/v0.2"
MODEL_COMMIT_ROLE = "assembly_view_only_not_actual_inference_commit_for_all_units"
PROVENANCE_FIELDS = ("input_candidate_file", "inference_inventory_sha256", "actual_inference_commits",
                     "assembly_code_commit", "model_code_commit_role")
AGGREGATE_FIELDS = ("inference_inventory_bindings", "actual_inference_commits", "assembly_code_commit",
                    "model_code_commit_role")


def provenance_binding(observations):
    return {key: observations[key] for key in PROVENANCE_FIELDS}


def _check_provenance(root, window, payload, observations, commit):
    header = payload["header"]
    units = header["inference_units"]
    expected = [(frame, view) for frame in range(window["start_frame_index"], window["end_frame_index"]+1)
                for view in range(4)]
    if (len(units) != 100 or [(u["frame_index"], u["view_ordinal"]) for u in units] != expected
            or any(u["window_id"] != window["window_id"] or u["possession_id"] != window["possession_id"] for u in units)
            or header["inference_inventory_sha256"] != canonical_sha256(units)
            or header["actual_inference_commits"] != sorted({u["actual_inference_commit"] for u in units})
            or header["model_code_commit_role"] != MODEL_COMMIT_ROLE or header["assembly_code_commit"] != commit
            or header["per_view_model_provenance"]["code_commit"] != commit):
        raise ValueError("Recovery inference inventory or assembly role differs")
    expected_provenance = {"input_candidate_file": file_binding(root, backend.candidate_path(root, window)),
                          **{key: header[key] for key in PROVENANCE_FIELDS if key != "input_candidate_file"}}
    if (provenance_binding(observations) != expected_provenance or "detector_code_commit" in observations
            or observations["ranking_code_commit"] != commit):
        raise ValueError("Recovery observation lost actual inference provenance")
    return expected_provenance


def aggregate(reports):
    base = original.aggregate(reports)
    first = reports[0]
    if any(r["model_code_commit_role"] != MODEL_COMMIT_ROLE or r["assembly_code_commit"] != first["assembly_code_commit"] for r in reports):
        raise ValueError("Mixed recovery assembly roles or commits")
    base.update(inference_inventory_bindings=[{"possession_id": r["possession_id"], "window": r["window"],
                                              **provenance_binding(r)} for r in reports],
                actual_inference_commits=sorted({commit for r in reports for commit in r["actual_inference_commits"]}),
                assembly_code_commit=first["assembly_code_commit"], model_code_commit_role=MODEL_COMMIT_ROLE)
    return base


def _load_evidence(root, m, p, commit, saved, inputs):
    if len(p["windows"]) != 6 or len(p["scoring_labels"]) != 6:
        raise ValueError("Recovery requires the six frozen windows and labels")
    models = {item["window"]["window_id"]: item["model"] for item in inputs or []}
    indices = {purpose: original._report_index(pool["evaluation_reports"]) for purpose, pool in saved.items()}
    evidence = {}
    for window, label in zip(p["windows"], p["scoring_labels"]):
        if label["window_id"] != window["window_id"]:
            raise ValueError("Recovery scoring label window differs")
        labels = load_annotations(bound_file(root, label["annotation"], "configs/ball_tracking/annotations"))
        if (labels.annotation_set_id != window["annotation_set_id"] or labels.possession_id != window["possession_id"]
                or labels.window.selection_purpose != window["purpose"] or labels.source_video.to_dict() != window["source_video"]
                or [a.frame_index for a in labels.annotations] != list(range(window["start_frame_index"], window["end_frame_index"]+1))):
            raise ValueError("Recovery annotations do not align with the frozen source")
        raw = load_detection_run(bound_file(root, window["detection"], "data/outputs/ball_tracking"))
        old = saved_crop_run(raw, read_json(bound_file(root, window["crop_candidates"], "data/outputs/ball_tracking")))
        run, payload, digest = backend.load_candidate_run(root, m, p, window, commit, model=models.get(window["window_id"]))
        if (run.annotation_set_id != labels.annotation_set_id or run.possession_id != labels.possession_id
                or run.source_video != labels.source_video or run.window != old.window
                or old.annotation_set_id != labels.annotation_set_id or old.possession_id != labels.possession_id
                or old.source_video != labels.source_video):
            raise ValueError("Recovery detector/source/label identities differ")
        observations = {}
        for config in original.control_grid():
            obs = backend.load_saved_control(root, p, window, config)
            for radius in RADII:
                key = (window["purpose"], window["possession_id"], window["start_frame_index"], window["end_frame_index"],
                       config.arm, config.confidence_threshold, radius)
                original._bind_report(indices[window["purpose"]][key], labels, old, obs)
        for config in experiment_grid():
            obs = backend.load_observations(root, m, p, window, run, digest, config, commit, rederive=False)
            _check_provenance(root, window, payload, obs, commit)
            observations[config.variant_id] = obs
        evidence[window["window_id"]] = (labels, run, observations, payload)
    return evidence


def _validate_grid(reports, aggregates, p, purpose, commit):
    bases = [{key: value for key, value in a.items() if key not in AGGREGATE_FIELDS} for a in aggregates]
    original._validate_grid(reports, bases, p, purpose, experiment_grid(), commit, REPORT_SCHEMA)
    expected = [aggregate([r for r in reports if r["variant_id"] == c.variant_id and r["localization_radius_px"] == radius])
                for c in experiment_grid() for radius in RADII]
    if aggregates != expected:
        raise ValueError("Recovery aggregate inference inventory differs")


def _pool_path(root, purpose):
    return safe_path(root, f"{backend.OUTPUT_ROOT}/evaluation/{purpose}.json", backend.OUTPUT_ROOT)


def _metadata(m, p, purpose, commit, evidence):
    inventories = []
    for window in p["windows"]:
        if window["purpose"] == purpose:
            observations = evidence[window["window_id"]][2]
            inventories.append({"window_id": window["window_id"], **provenance_binding(next(iter(observations.values())))})
    return {"schema_version": POOL_SCHEMA, "purpose": purpose, "experiment_spec_sha256": spec_digest(m),
            "code_commit": commit, "assembly_code_commit": commit, "evaluation_code_commit": commit,
            "model_code_commit_role": MODEL_COMMIT_ROLE, "inference_inventory_bindings": inventories,
            "actual_inference_commits": sorted({c for row in inventories for c in row["actual_inference_commits"]}),
            "recovery_proposal": m["recovery_proposal"], "original_experiment": m["original_experiment"],
            "prior_motion_execution_commit": original.PRIOR_COMMIT,
            "provenance_semantics": "Typed model commit is the assembly view only. Bound per-unit inventories retain actual inference commits. Reused RF-DETR reports retain original provenance.",
            "saved_control_scoring_reports": p["saved_control_scoring_reports"], "saved_control_outputs": p["saved_control_outputs"],
            "annotation_bindings": p["scoring_labels"], "crop_input_bindings": [w["crop_candidates"] for w in p["windows"]],
            "reused_report_count": 405, "new_report_count": 405, "reused_aggregate_count": 135, "new_aggregate_count": 135,
            "selected_method": None, "selected_operating_point": None, "quality_gate": None}


def _validate_pool(value, m, p, purpose, commit, saved, evidence):
    metadata = _metadata(m, p, purpose, commit, evidence)
    extras = {"evaluation_reports", "aggregate_results", "paired_differences", "loss_decomposition",
              "aggregate_paired_differences", "content_sha256"}
    if (set(value) != set(metadata)|extras or any(value.get(key) != expected for key, expected in metadata.items())
            or value["content_sha256"] != original._pool_digest(value)
            or value["evaluation_reports"][:405] != saved["evaluation_reports"]
            or value["aggregate_results"][:135] != saved["aggregate_results"]):
        raise ValueError("Recovery pool changed original controls or inference provenance")
    reports, aggregates = value["evaluation_reports"][405:], value["aggregate_results"][135:]
    _validate_grid(reports, aggregates, p, purpose, commit)
    index = original._report_index(reports)
    for window in (w for w in p["windows"] if w["purpose"] == purpose):
        labels, run, observations, _ = evidence[window["window_id"]]
        for config in experiment_grid():
            obs = observations[config.variant_id]
            for radius in RADII:
                report = index[(purpose, window["possession_id"], window["start_frame_index"], window["end_frame_index"],
                                config.arm, config.confidence_threshold, radius)]
                original._bind_report(report, labels, run, obs)
                if "detector_code_commit" in report or provenance_binding(report) != provenance_binding(obs):
                    raise ValueError("Recovery score lost per-unit inference provenance")
    differences, losses = original.paired_differences(value["evaluation_reports"])
    if (len(differences) != 405 or len(losses) != 810 or value["paired_differences"] != differences
            or value["loss_decomposition"] != losses
            or value["aggregate_paired_differences"] != original.aggregate_paired_differences(value["aggregate_results"])):
        raise ValueError("Recovery contrasts or loss accounting differ")


def load_scoring_pools(root, m, p, commit, *, inputs=None):
    """Read and verify saved recovery scores; never select or score a candidate."""
    saved = original._saved_pools(root, p)
    evidence = _load_evidence(root, m, p, commit, saved, inputs)
    pools = {}
    for purpose in p["pool_separation"]:
        value = read_json(_pool_path(root, purpose))
        _validate_pool(value, m, p, purpose, commit, saved[purpose], evidence)
        pools[purpose] = value
    return pools


def score_experiment(root, path):
    m, p, inputs, commit = backend.preflight(root, path)
    saved = original._saved_pools(root, p)
    evidence = _load_evidence(root, m, p, commit, saved, inputs)
    pools = {}
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
        for window in (w for w in p["windows"] if w["purpose"] == purpose):
            labels, run, observations, _ = evidence[window["window_id"]]
            for config in experiment_grid():
                obs = observations[config.variant_id]
                for radius in RADII:
                    report = original._evaluate_validated(labels, run, obs, radius, commit)
                    report.update(schema_version=REPORT_SCHEMA, **provenance_binding(obs))
                    reports.append(report)
        aggregates = [aggregate([r for r in reports if r["variant_id"] == c.variant_id and r["localization_radius_px"] == radius])
                      for c in experiment_grid() for radius in RADII]
        reports = [*saved[purpose]["evaluation_reports"], *reports]
        aggregates = [*saved[purpose]["aggregate_results"], *aggregates]
        differences, losses = original.paired_differences(reports)
        value = {**_metadata(m, p, purpose, commit, evidence), "evaluation_reports": reports, "aggregate_results": aggregates,
                 "paired_differences": differences, "loss_decomposition": losses,
                 "aggregate_paired_differences": original.aggregate_paired_differences(aggregates)}
        value["content_sha256"] = original._pool_digest(value)
        _validate_pool(value, m, p, purpose, commit, saved[purpose], evidence)
        pools[purpose] = value
    backend.unchanged(root, path, m, commit)
    if _load_evidence(root, m, p, commit, original._saved_pools(root, p), inputs) != evidence:
        raise ValueError("Recovery score inputs changed during evaluation")
    bindings = []
    for purpose in p["pool_separation"]:
        target = _pool_path(root, purpose)
        persist_once(target, pools[purpose])
        bindings.append(file_binding(root, target))
    backend.unchanged(root, path, m, commit)
    return {"reports": bindings, "new_per_window_reports": 810, "reused_per_window_reports": 810,
            "per_window_reports": 1620, "new_aggregate_cells_per_pool": 135,
            "reused_aggregate_cells_per_pool": 135, "aggregate_cells_per_pool": 270,
            "saved_controls_reranked": 0, "saved_controls_rescored": 0,
            "model_code_commit_role": MODEL_COMMIT_ROLE, "assembly_code_commit": commit,
            "evaluation_code_commit": commit}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.repository_root.resolve()
    print(json.dumps(score_experiment(root, (root/args.manifest).resolve()), indent=2))


if __name__ == "__main__":
    main()
