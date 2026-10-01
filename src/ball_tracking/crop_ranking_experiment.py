"""Guarded, resumable selection on approved saved crop candidates only."""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from .crop_ranking import ARMS, experiment_grid, rank_candidates, validate_observations
from .development_experiments import bound_file, canonical_sha256, closed, read_json, safe_path, sha256_file
from .temporal_association import THRESHOLDS, RADII
from .temporal_experiment import _tracked, clean_commit, git, load_inputs as load_whole_inputs, persist_once, spec_digest
from .tiled_candidates import candidate_run
from .tiled_evaluation import load_output
from .tiled_experiment import load_manifest as load_tiled_manifest

EXPERIMENT_ID = "rfdetr_medium_crop_candidate_ranking_v0_1"
OUTPUT_ROOT = f"data/outputs/ball_tracking/crop_candidate_ranking/{EXPERIMENT_ID}"
FIELDS = {"schema_version", "experiment_id", "proposal", "output_root", "authorization", "selected_operating_point", "quality_gate"}
EXECUTION_COMMIT = "1a9479f83a1766d8979fad07c604bc686d3c52c6"
PROPOSAL_FIELDS = {"schema_version","proposal_id","status","prepared_at_utc","design","rationale","diagnostic",
                   "crop_review_receipt","crop_execution_record","crop_execution_commit","crop_experiment_manifest",
                   "saved_crop_scoring_reports","frozen_detector_contract_source","windows","scoring_labels",
                   "confidence_thresholds","localization_radii_px","pool_separation","selectors","ranking_contract",
                   "matching_rule","review","expected_counts","proposed_output_root","selection_labels_access_allowed",
                   "new_detector_inference_allowed","training_allowed","window_expansion_allowed","deduplication_allowed",
                   "candidate_center_or_confidence_modification_allowed","smoothing_interpolation_extrapolation_allowed",
                   "player_or_court_input_allowed","holdout_release_authorized","original_v0_1_embargoes_preserved",
                   "selected_operating_point","quality_gate","authorization","execution_preconditions"}
RANKING_CONTRACT = {
    "input_order": "original_global_candidate_order_after_inclusive_confidence_filter",
    "history_frames": 5, "max_missing_frames_between_nodes": 2, "max_trailing_missing_frames": 2,
    "missing_frame_penalty": .25, "squared_normalized_step_penalty": .25,
    "edge_limit": "distance_px <= step_limit * source_diagonal_px * elapsed_frames; elapsed_frames in [1,3]",
    "score": "sum(original_confidences) - 0.25*(internal_skipped_frames + trailing_skipped_frames) - 0.25*sum(normalized_step**2)",
    "leading_missing_penalty": 0.0, "empty_hypothesis_score": 0.0,
    "solver": "exact_dynamic_programming_over_last_five_frame_acyclic_graph",
    "path_ties": "lexicographically_smallest_sequence_of_original_frame_candidate_pairs",
    "endpoint_ties": "latest_endpoint_frame_then_higher_endpoint_confidence_then_lower_global_candidate_index_then_lexicographic_path",
    "empty_tie_rule": "empty_wins_any_score_zero_tie",
    "output_rule": "emit_original_candidate_only_if_winning_endpoint_is_current_frame; otherwise_null",
    "probability_interpretation": False, "hypothesis_alternatives_and_score_margins_required": True,
    "ambiguity_margin_acceptance_threshold": None, "state_reset": "each_window",
    "future_access_allowed": False, "past_output_revisions_allowed": False, "singleton_start_allowed": True,
}
REVIEW = {"confidence_thresholds": [.2, .35], "radius_px": 10.0,
         "panels": [*ARMS, "saved_whole_frame_top_one_context"], "clips": 12,
         "frames_per_clip": 25, "fps": 5.0, "all_frames_and_final_frame_required": True,
         "highlighted_context": {"possession_002_challenge": [48, 49], "possession_002_representative": [258, 259],
                                 "possession_001_challenge": [219], "possession_003_hidden": [165,166,167,168,169],
                                 "possession_003_boundaries": [164,170,174]}}
EXPECTED_COUNTS = {"source_frames":150,"new_model_calls":0,"variants":45,"per_window_derived_outputs":270,
                   "total_per_window_scoring_reports":1350,"aggregate_cells_per_pool":225,"crop_raw_top_one_parity_cells":540}


def load_manifest(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    safe_path(root, path.relative_to(root).as_posix(), "configs/ball_tracking/crop_ranking_experiments")
    m = closed(read_json(path), FIELDS, "crop ranking manifest")
    if (m["schema_version"] != "ball_crop_candidate_ranking_experiment/v0.1"
            or m["experiment_id"] != EXPERIMENT_ID or m["output_root"] != OUTPUT_ROOT
            or m["selected_operating_point"] is not None or m["quality_gate"] is not None):
        raise ValueError("Unsupported crop ranking manifest")
    p = closed(read_json(bound_file(root, m["proposal"], "configs/ball_tracking/proposals")),PROPOSAL_FIELDS,"ranking proposal")
    tiled_path = bound_file(root, p["crop_experiment_manifest"], "configs/ball_tracking/tiled_experiments")
    tiled_m, tiled_p, temporal, baseline = load_tiled_manifest(root, tiled_path)
    # All inherited windows, labels, and model contracts remain bound to the prior permit.
    if not isinstance(p["windows"],list) or len(p["windows"]) != 6:
        raise ValueError("Expected exactly six saved crop windows")
    for window in p["windows"]:
        closed(window,set(tiled_p["windows"][0]) | {"crop_candidates"},"saved crop window")
        closed(window["crop_candidates"],{"path","sha256"},"crop candidate binding")
    expected_windows = [{**w, "crop_candidates": {"path": f"{tiled_m['output_root']}/{w['window_id']}/candidates.json",
                                                  "sha256": p["windows"][i]["crop_candidates"]["sha256"]}}
                        for i, w in enumerate(tiled_p["windows"])]
    checks = {"schema_version": "ball_crop_candidate_ranking_proposal/v0.1", "proposal_id": EXPERIMENT_ID,
              "status": "proposal_not_authorized_not_executable", "authorization": None,
              "crop_execution_commit": EXECUTION_COMMIT, "windows": expected_windows,
              "scoring_labels": tiled_p["scoring_labels"], "frozen_detector_contract_source": tiled_p["frozen_detector_contract_source"],
              "confidence_thresholds": list(THRESHOLDS), "localization_radii_px": list(RADII),
              "pool_separation": ["representative_evaluation", "challenge_evaluation"],
              "selectors": [{k:v for k,v in asdict(c).items() if k != "confidence_threshold" and v is not None}
                            for c in experiment_grid()[:5]],
              "ranking_contract": RANKING_CONTRACT, "review": REVIEW, "expected_counts": EXPECTED_COUNTS,
              "matching_rule": "raw center distance; uncertainty diagnostic only", "proposed_output_root": OUTPUT_ROOT,
              "selection_labels_access_allowed": False, "new_detector_inference_allowed": False,
              "training_allowed": False, "window_expansion_allowed": False, "deduplication_allowed": False,
              "candidate_center_or_confidence_modification_allowed": False,
              "smoothing_interpolation_extrapolation_allowed": False, "player_or_court_input_allowed": False,
              "holdout_release_authorized": False, "original_v0_1_embargoes_preserved": True,
              "selected_operating_point": None, "quality_gate": None}
    if any(canonical_sha256(p.get(k)) != canonical_sha256(v) for k,v in checks.items()):
        raise ValueError("Proposal differs from the supported saved crop ranking scope")
    for key in ("design", "rationale"):
        item = closed(p[key],{"path","sha256"},key)
        if sha256_file(safe_path(root,item["path"],"docs")) != item["sha256"]:
            raise ValueError("Approved ranking design/rationale changed")
    receipt = read_json(bound_file(root, p["crop_review_receipt"], "configs/ball_tracking/reviews"))
    evidence = receipt["bound_evidence"]
    # Runtime reads review metadata, never scoring pools, annotation content, or review pixels.
    if (receipt["human_visual_review"]["status"] != "completed"
            or receipt["human_visual_review"]["reviewer_id"] != "ryan"
            or evidence["experiment_manifest"] != p["crop_experiment_manifest"]
            or evidence["execution_commit"] != EXECUTION_COMMIT
            or evidence["execution_record"] != p["crop_execution_record"]
            or evidence["scoring_reports"] != p["saved_crop_scoring_reports"]):
        raise ValueError("Missing bound completed crop review")
    from .development_experiments import require_digest
    for item in [*(w["crop_candidates"] for w in expected_windows), *p["saved_crop_scoring_reports"]]:
        closed(item, {"path", "sha256"}, "saved crop binding")
        require_digest(item["sha256"], "saved crop input")
    if [r["path"] for r in p["saved_crop_scoring_reports"]] != [
            f"{tiled_m['output_root']}/evaluation/{purpose}.json" for purpose in p["pool_separation"]]:
        raise ValueError("Scoring pool identity mismatch")
    approval = closed(read_json(bound_file(root, m["authorization"], "configs/ball_tracking/reviews")),
                      {"schema_version","experiment_spec_sha256","proposal","approved_by","statement",
                       "recorded_at_utc","timestamp_semantics","scope","git_mutations_authorized"}, "ranking authorization")
    if (approval["schema_version"] != "ball_crop_candidate_ranking_approval/v0.1"
            or approval["experiment_spec_sha256"] != spec_digest(m) or approval["proposal"] != m["proposal"]
            or approval["approved_by"] != "ryan" or not isinstance(approval["statement"], str)
            or not approval["statement"].strip() or approval["git_mutations_authorized"] is not False
            or approval["scope"] != "saved_six_development_crop_windows_all_45_declared_variants"):
        raise ValueError("Missing exact ranking scope authorization")
    return m, p, tiled_m, tiled_p, temporal, baseline


def load_inputs(root, loaded):
    m, p, tiled_m, tiled_p, temporal, baseline = loaded
    wholes = load_whole_inputs(root, temporal)
    inputs = []
    for window, prior, raw in zip(p["windows"], tiled_p["windows"], wholes):
        bound_file(root, window["crop_candidates"], tiled_m["output_root"])
        output = load_output(root, tiled_m, prior, raw, baseline, p["crop_execution_commit"])
        inputs.append((raw, candidate_run(raw, output), output["content_sha256"]))
    return inputs


def output_path(root, window, config):
    return safe_path(root, f"{OUTPUT_ROOT}/{window['window_id']}/{config.variant_id}.json", OUTPUT_ROOT)


def preflight(root, path, *, require_clean=True):
    loaded = load_manifest(root, path)
    m, p = loaded[:2]
    commit = clean_commit(root) if require_clean else git(root, "rev-parse", "HEAD")
    if require_clean:
        for name in [path, root/m["proposal"]["path"], root/m["authorization"]["path"],
                     *(root/p[k]["path"] for k in ("design","rationale","crop_review_receipt")),
                     *(root/r["annotation"]["path"] for r in p["scoring_labels"]),
                     *Path(__file__).parent.glob("crop_ranking*.py")]:
            _tracked(root, name)
    target = safe_path(root, f"{OUTPUT_ROOT}/ignore_check.json", OUTPUT_ROOT)
    if subprocess.run(["git","check-ignore","-q","--",target.relative_to(root).as_posix()],cwd=root).returncode:
        raise ValueError("Ranking outputs must remain Git-ignored")
    return m, p, load_inputs(root, loaded), commit


def unchanged(root, path, m, commit):
    if clean_commit(root) != commit or load_manifest(root, path)[0] != m:
        raise ValueError("Git or ranking manifest changed during stage")
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
                "windows":len(inputs),"variants":45,"new_model_calls":0,"execution_requires_clean_commit":True}
    # Reject all existing tampering before creating any missing outputs.
    for w, (_, run, digest) in zip(p["windows"], inputs):
        for config in experiment_grid():
            if output_path(root, w, config).exists():
                load_observations(root, m, w, run, digest, config, commit)
    created = 0
    for w, (_, run, digest) in zip(p["windows"], inputs):
        for config in experiment_grid():
            target = output_path(root, w, config)
            if not target.exists():
                created += persist_once(target, envelope(root,m,w,run,digest,config,commit))
    unchanged(root,path,m,commit)
    return {"created_outputs":created,"total_outputs":270,"new_model_calls":0,"commit":commit}


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
