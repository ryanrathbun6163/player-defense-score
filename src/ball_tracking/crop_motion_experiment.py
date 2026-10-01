"""Guarded independent motion-factor experiment on approved saved crops only."""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from . import crop_ranking_experiment as prior_experiment
from .crop_motion_factorial import ARMS, experiment_grid, legacy_config, rank_candidates, validate_observations, verify_control_trace
from .development_experiments import bound_file, canonical_sha256, closed, read_json, safe_path, sha256_file, require_digest
from .temporal_association import THRESHOLDS, RADII
from .temporal_experiment import _tracked, clean_commit, git, persist_once, spec_digest

EXPERIMENT_ID = "rfdetr_medium_crop_motion_factorial_v0_1"
OUTPUT_ROOT = f"data/outputs/ball_tracking/crop_motion_factorial/{EXPERIMENT_ID}"
EXECUTION_COMMIT = "3c4894656fd5da11708a54089444d41f0a6f7773"
FIELDS = prior_experiment.FIELDS
PROPOSAL_FIELDS = {
    "schema_version", "proposal_id", "status", "prepared_at_utc", "design", "rationale", "diagnostic", "generator",
    "prior_ranking_proposal", "prior_ranking_manifest", "prior_ranking_execution", "prior_ranking_execution_commit",
    "ranking_review_receipt", "crop_execution_commit", "crop_experiment_manifest", "crop_review_receipt",
    "saved_ranking_scoring_reports", "saved_ranking_control_outputs", "frozen_detector_contract_source",
    "windows", "scoring_labels", "confidence_thresholds", "localization_radii_px", "pool_separation", "selectors",
    "ranking_contract", "matching_rule", "comparisons", "required_metrics", "control_parity", "review",
    "expected_counts", "proposed_output_root", "selection_labels_access_allowed", "new_detector_inference_allowed",
    "training_allowed", "window_expansion_allowed", "deduplication_allowed",
    "candidate_center_or_confidence_modification_allowed", "smoothing_interpolation_extrapolation_allowed",
    "player_or_court_input_allowed", "holdout_release_authorized", "original_v0_1_embargoes_preserved",
    "selected_operating_point", "quality_gate", "authorization", "execution_preconditions",
}
RANKING_CONTRACT = {
    **prior_experiment.RANKING_CONTRACT,
    "edge_limit": "distance_px <= edge_step * source_diagonal_px * elapsed_frames; elapsed_frames in [1,3]",
    "normalized_step": "distance_px / (cost_step * source_diagonal_px * elapsed_frames)",
    "normalized_step_clipping_allowed": False,
    "existing_control_arithmetic_and_traversal_order_preserved": True,
}
EXPECTED_COUNTS = {"source_frames": 150, "new_model_calls": 0, "variants": 63,
                   "per_window_derived_outputs": 378, "total_per_window_scoring_reports": 1890,
                   "aggregate_cells_per_pool": 315, "mapped_control_output_traces": 270,
                   "mapped_control_scoring_cells": 1350, "new_graph_variants": 18, "new_graph_window_outputs": 108}
REVIEW = {
    "confidence_thresholds": [.2, .35], "radius_px": 10.0,
    "panels": [*ARMS, "unmarked_source", "legend"], "layout": {"rows": 3, "columns": 3},
    "clips": 12, "frames_per_clip": 25, "fps": 5.0, "all_frames_and_final_frame_required": True,
    "native_overlays_and_source_scale_closeups_required": True, "graph_panel_labels_require_both_parameters": True,
    "highlighted_context": {"possession_002_representative": [258, 262], "possession_002_challenge": [44, 45, 46, 48, 49],
                            "possession_003_representative": [300, 301, 302, 303],
                            "possession_003_hidden": [165, 166, 167, 168, 169],
                            "possession_003_boundaries": [164, 170, 171, 173, 174]},
}
CONTROL_PARITY = {
    "derived_outputs": 270, "scoring_cells": 1350, "full_observation_trace_parity_required": True,
    "compare": ["emitted_indices", "candidate_dispositions", "horizons", "edges", "best_paths", "component_scores",
                "endpoint_scores", "winner", "score_margin", "null_reason", "frame_outcomes", "metrics"],
    "permitted_metadata_mapping": ["explicit_legacy_to_new_arm_mapping", "legacy_step_limit_to_equal_edge_and_cost_steps",
                                   "schema_version", "new_experiment_specification", "new_code_commit", "derived_content_digest"],
    "behavioral_differences_allowed": False,
}


def load_manifest(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    safe_path(root, path.relative_to(root).as_posix(), "configs/ball_tracking/crop_motion_experiments")
    m = closed(read_json(path), FIELDS, "crop motion manifest")
    if (m["schema_version"] != "ball_crop_motion_experiment/v0.1" or m["experiment_id"] != EXPERIMENT_ID
            or m["output_root"] != OUTPUT_ROOT or m["selected_operating_point"] is not None or m["quality_gate"] is not None):
        raise ValueError("Unsupported crop motion manifest")
    p = closed(read_json(bound_file(root, m["proposal"], "configs/ball_tracking/proposals")), PROPOSAL_FIELDS, "motion proposal")
    prior_path = bound_file(root, p["prior_ranking_manifest"], "configs/ball_tracking/crop_ranking_experiments")
    prior_loaded = prior_experiment.load_manifest(root, prior_path)
    prior_m, prior_p = prior_loaded[:2]
    checks = {"schema_version": "ball_crop_motion_factorial_proposal/v0.1", "proposal_id": EXPERIMENT_ID,
              "status": "proposal_not_authorized_not_executable", "authorization": None,
              "prior_ranking_proposal": prior_m["proposal"], "prior_ranking_execution_commit": EXECUTION_COMMIT,
              "confidence_thresholds": list(THRESHOLDS), "localization_radii_px": list(RADII),
              "ranking_contract": RANKING_CONTRACT, "review": REVIEW, "expected_counts": EXPECTED_COUNTS,
              "control_parity": CONTROL_PARITY, "proposed_output_root": OUTPUT_ROOT + "/",
              "selected_operating_point": None, "quality_gate": None}
    for key in ("crop_execution_commit", "crop_experiment_manifest", "crop_review_receipt", "frozen_detector_contract_source",
                "windows", "scoring_labels", "pool_separation", "matching_rule", "selection_labels_access_allowed",
                "new_detector_inference_allowed", "training_allowed", "window_expansion_allowed", "deduplication_allowed",
                "candidate_center_or_confidence_modification_allowed", "smoothing_interpolation_extrapolation_allowed",
                "player_or_court_input_allowed", "holdout_release_authorized", "original_v0_1_embargoes_preserved"):
        checks[key] = prior_p[key]
    checks["selectors"] = [{**{k: v for k, v in asdict(c).items() if k != "confidence_threshold"},
                            "legacy_control_arm": legacy_config(c).arm if legacy_config(c) else None}
                           for c in experiment_grid()[:7]]
    if any(canonical_sha256(p.get(k)) != canonical_sha256(v) for k, v in checks.items()):
        raise ValueError("Proposal differs from the supported motion-factorial scope")
    for key in ("design", "rationale"):
        item = closed(p[key], {"path", "sha256"}, key)
        if sha256_file(safe_path(root, item["path"], "docs")) != item["sha256"]:
            raise ValueError("Approved motion design/rationale changed")
    # Only review/execution metadata is opened; scoring pools and annotations stay outside selection.
    receipt = read_json(bound_file(root, p["ranking_review_receipt"], "configs/ball_tracking/reviews"))
    evidence = receipt["bound_evidence"]
    if (receipt["human_visual_review"]["status"] != "completed" or receipt["human_visual_review"]["reviewer_id"] != "ryan"
            or evidence["execution_commit"] != EXECUTION_COMMIT
            or evidence["experiment_manifest"] != p["prior_ranking_manifest"]
            or evidence["execution_record"] != p["prior_ranking_execution"]
            or evidence["scoring_reports"] != p["saved_ranking_scoring_reports"]):
        raise ValueError("Missing bound ranking review response")
    execution = read_json(bound_file(root, p["prior_ranking_execution"], "data/outputs/ball_tracking/crop_ranking_execution"))
    if (execution["commit"] != EXECUTION_COMMIT or execution["manifest"] != p["prior_ranking_manifest"]
            or execution["spec_sha256"] != spec_digest(prior_m)
            or execution["derived_outputs"] != p["saved_ranking_control_outputs"]
            or execution["scoring"]["reports"] != p["saved_ranking_scoring_reports"]):
        raise ValueError("Saved ranking execution binding mismatch")
    expected = [f"{prior_m['output_root']}/{w['window_id']}/{c.variant_id}.json"
                for w in p["windows"] for c in prior_experiment.experiment_grid()]
    if [b["path"] for b in p["saved_ranking_control_outputs"]] != expected:
        raise ValueError("Expected exactly 270 ordered saved control outputs")
    if [r["path"] for r in p["saved_ranking_scoring_reports"]] != [
            f"{prior_m['output_root']}/evaluation/{purpose}.json" for purpose in p["pool_separation"]]:
        raise ValueError("Saved ranking scoring pool identity mismatch")
    for b in [*p["saved_ranking_control_outputs"], *p["saved_ranking_scoring_reports"]]:
        closed(b, {"path", "sha256"}, "saved ranking binding")
        require_digest(b["sha256"], "saved ranking digest")
    approval = closed(read_json(bound_file(root, m["authorization"], "configs/ball_tracking/reviews")),
                      {"schema_version", "experiment_spec_sha256", "proposal", "approved_by", "statement",
                       "recorded_at_utc", "timestamp_semantics", "scope", "git_mutations_authorized"}, "motion approval")
    if (approval["schema_version"] != "ball_crop_motion_approval/v0.1"
            or approval["experiment_spec_sha256"] != spec_digest(m) or approval["proposal"] != m["proposal"]
            or approval["approved_by"] != "ryan" or not isinstance(approval["statement"], str)
            or not approval["statement"].strip() or approval["git_mutations_authorized"] is not False
            or approval["scope"] != "saved_six_development_crop_windows_all_63_declared_variants"):
        raise ValueError("Missing exact motion-factorial authorization")
    return m, p, *prior_loaded


def load_inputs(root, loaded):
    # The inherited loader verifies complete saved crops without opening annotation content.
    inputs = prior_experiment.load_inputs(root, loaded[2:])
    for item in loaded[1]["saved_ranking_control_outputs"]:
        bound_file(root, item, prior_experiment.OUTPUT_ROOT)
    return inputs


def load_saved_control(root, p, window, config, *, crop_digest=None):
    prior = legacy_config(config)
    if prior is None:
        return None
    expected_path = f"{prior_experiment.OUTPUT_ROOT}/{window['window_id']}/{prior.variant_id}.json"
    item = next((b for b in p["saved_ranking_control_outputs"] if b["path"] == expected_path), None)
    if item is None:
        raise ValueError("Missing saved control binding")
    value = closed(read_json(bound_file(root, item, prior_experiment.OUTPUT_ROOT)),
                   {"experiment_spec_sha256", "input_crop_file", "crop_content_sha256", "observations"}, "saved control envelope")
    obs = value["observations"]
    if crop_digest is None:
        crop_digest = read_json(bound_file(root, window["crop_candidates"],
                                          "data/outputs/ball_tracking/tiled_development"))["content_sha256"]
    require_digest(crop_digest, "bound crop content digest")
    prior_m = read_json(bound_file(root, p["prior_ranking_manifest"], "configs/ball_tracking/crop_ranking_experiments"))
    if (value["experiment_spec_sha256"] != spec_digest(prior_m) or value["input_crop_file"] != window["crop_candidates"]
            or value["crop_content_sha256"] != crop_digest
            or obs["ranking_code_commit"] != EXECUTION_COMMIT or obs["config"] != asdict(prior)
            or obs["variant_id"] != prior.variant_id or obs["possession_id"] != window["possession_id"]
            or obs["source_video"] != window["source_video"]
            or obs["window"] != {"start_frame_index": window["start_frame_index"], "end_frame_index": window["end_frame_index"]}):
        raise ValueError("Saved control provenance mismatch")
    return obs


def output_path(root, window, config):
    return safe_path(root, f"{OUTPUT_ROOT}/{window['window_id']}/{config.variant_id}.json", OUTPUT_ROOT)


def preflight(root, path, *, require_clean=True):
    loaded = load_manifest(root, path)
    m, p = loaded[:2]
    commit = clean_commit(root) if require_clean else git(root, "rev-parse", "HEAD")
    if require_clean:
        for name in [path, root/m["proposal"]["path"], root/m["authorization"]["path"],
                     *(root/p[k]["path"] for k in ("design","rationale","ranking_review_receipt")),
                     *(root/r["annotation"]["path"] for r in p["scoring_labels"]),
                     *Path(__file__).parent.glob("crop_motion*.py")]:
            _tracked(root, name)
    target = safe_path(root, f"{OUTPUT_ROOT}/ignore_check.json", OUTPUT_ROOT)
    if subprocess.run(["git","check-ignore","-q","--",target.relative_to(root).as_posix()],cwd=root).returncode:
        raise ValueError("Motion outputs must remain Git-ignored")
    return m, p, load_inputs(root, loaded), commit


def unchanged(root, path, m, commit):
    if clean_commit(root) != commit or load_manifest(root, path)[0] != m:
        raise ValueError("Git or motion manifest changed during stage")
    load_inputs(root, load_manifest(root, path))


def envelope(root, m, window, run, digest, config, commit):
    return {"experiment_spec_sha256": spec_digest(m), "input_crop_file": window["crop_candidates"],
            "crop_content_sha256": digest, "observations": rank_candidates(run, config, commit)}


def load_observations(root, m, window, run, digest, config, commit):
    value = closed(read_json(output_path(root, window, config)),
                   {"experiment_spec_sha256","input_crop_file","crop_content_sha256","observations"}, "ranking envelope")
    if (value["experiment_spec_sha256"] != spec_digest(m) or value["input_crop_file"] != window["crop_candidates"]
            or value["crop_content_sha256"] != digest or value["observations"]["ranking_code_commit"] != commit
            or validate_observations(value["observations"], run) != config):
        raise ValueError("Ranking input/specification/commit binding mismatch")
    return value["observations"]


def run_experiment(root, path, *, dry_run=False):
    m, p, inputs, commit = preflight(root, path, require_clean=not dry_run)
    if dry_run:
        return {"dry_run":True,"source_frames":sum(len(c.frames) for _,c,_ in inputs),
                "windows":len(inputs),"variants":63,"new_model_calls":0,"execution_requires_clean_commit":True}
    # Reject all existing tampering before creating any missing outputs.
    for w, (_, run, digest) in zip(p["windows"], inputs):
        for config in experiment_grid():
            if output_path(root, w, config).exists():
                observations = load_observations(root, m, w, run, digest, config, commit)
                saved = load_saved_control(root, p, w, config, crop_digest=digest)
                if saved is not None:
                    verify_control_trace(observations, saved)
    created = 0
    for w, (_, run, digest) in zip(p["windows"], inputs):
        for config in experiment_grid():
            target = output_path(root, w, config)
            if not target.exists():
                payload = envelope(root,m,w,run,digest,config,commit)
                saved = load_saved_control(root, p, w, config, crop_digest=digest)
                if saved is not None:
                    verify_control_trace(payload["observations"], saved)
                created += persist_once(target, payload)
    unchanged(root,path,m,commit)
    return {"created_outputs":created,"total_outputs":378,"new_model_calls":0,"commit":commit}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--repository-root",type=Path,default=Path.cwd())
    parser.add_argument("--dry-run",action="store_true")
    args = parser.parse_args()
    root = args.repository_root.resolve()
    print(json.dumps(run_experiment(root,(root/args.manifest).resolve(),dry_run=args.dry_run),indent=2))


if __name__ == "__main__":
    main()
