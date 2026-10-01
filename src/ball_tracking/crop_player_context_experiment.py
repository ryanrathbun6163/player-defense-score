"""Guarded context comparison; old selectors and scores are immutable inputs."""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from . import crop_motion_experiment as prior_experiment
from . import crop_motion_factorial as controls
from .crop_player_context import experiment_grid, rank_candidates, validate_context_window, validate_observations
from .development_experiments import bound_file, canonical_sha256, closed, read_json, require_digest, safe_path, sha256_file
from .temporal_experiment import _tracked, clean_commit, git, persist_once, spec_digest

EXPERIMENT_ID = "rfdetr_medium_crop_player_context_v0_1"
OUTPUT_ROOT = f"data/outputs/ball_tracking/crop_player_context/{EXPERIMENT_ID}"
CONFIG_ROOT = "configs/ball_tracking/crop_player_context_experiments"
CONTEXT_ROOT = "data/outputs/ball_tracking/candidate_identity_diagnosis"
PRIOR_COMMIT = "2274ab6097cd841421e2b606f723b047cd7dc62b"
APPROVED_PROPOSAL_SHA256 = "b41dd0094755de726db6de196c28376cdfc2bceb40b645b1ce91fa56a6be80e7"
APPROVAL_SCOPE = "saved_six_development_crop_windows_36_new_context_variants_reusing_63_saved_variants"
FIELDS = prior_experiment.FIELDS
SNAPSHOT_FIELDS = {
    "schema_version", "source_experiment_commit", "purpose", "context_feasibility",
    "context_feasibility_generator", "input_bindings", "inherited_feasibility_bindings",
    "inherited_binding_semantics", "scope", "row_contract", "proposed_formula_metadata_only",
    "player_source_provenance", "provenance_limits", "windows", "all_window_rows_canonical_sha256",
    "selected_method", "selected_operating_point", "quality_gate",
}
ENVELOPE_FIELDS = {
    "experiment_spec_sha256", "input_crop_file", "crop_content_sha256",
    "input_player_context_file", "context_window_sha256", "observations_content_sha256", "observations",
}


def load_manifest(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    safe_path(root, path.relative_to(root).as_posix(), CONFIG_ROOT)
    m = closed(read_json(path), FIELDS, "player context manifest")
    if (m["schema_version"] != "ball_crop_player_context_experiment/v0.1"
            or m["experiment_id"] != EXPERIMENT_ID or m["output_root"] != OUTPUT_ROOT
            or m["selected_operating_point"] is not None or m["quality_gate"] is not None):
        raise ValueError("Unsupported player context manifest")
    proposal_path = bound_file(root, m["proposal"], "configs/ball_tracking/proposals")
    if m["proposal"]["sha256"] != APPROVED_PROPOSAL_SHA256:
        raise ValueError("Proposal differs from the exact approved player context specification")
    p = read_json(proposal_path)
    prior_path = bound_file(root, p["prior_motion_manifest"], "configs/ball_tracking/crop_motion_experiments")
    prior_loaded = prior_experiment.load_manifest(root, prior_path)
    prior_m, prior_p = prior_loaded[:2]
    if (p["schema_version"] != "ball_crop_player_context_proposal/v0.1"
            or p["proposal_id"] != EXPERIMENT_ID or p["prepared_at_commit"] != PRIOR_COMMIT
            or p["status"] != "proposal_not_authorized_not_executable"
            or p["authorization"] is not None or p["proposed_output_root"] != OUTPUT_ROOT
            or p["prior_motion_proposal"] != prior_m["proposal"]
            or any(p[k] != prior_p[k] for k in ("windows", "scoring_labels", "confidence_thresholds",
                                                "localization_radii_px", "pool_separation", "matching_rule"))):
        raise ValueError("Player context scope differs from the completed motion experiment")
    for key in ("design", "rationale"):
        if sha256_file(safe_path(root, p[key]["path"], "docs")) != p[key]["sha256"]:
            raise ValueError("Approved context design/rationale changed")
    # Read metadata only: no annotations, diagnostic outcomes, scoring pools or pixels.
    receipt = read_json(bound_file(root, p["motion_review_receipt"], "configs/ball_tracking/reviews"))
    evidence = receipt["bound_evidence"]
    if (receipt["human_visual_review"]["status"] != "completed"
            or receipt["human_visual_review"]["reviewer_id"] != "ryan"
            or evidence["execution_commit"] != PRIOR_COMMIT
            or evidence["experiment_manifest"] != p["prior_motion_manifest"]
            or evidence["execution_record"] != p["prior_motion_execution"]
            or evidence["scoring_reports"] != p["saved_control_scoring_reports"]):
        raise ValueError("Missing bound completed motion review")
    execution = read_json(bound_file(root, p["prior_motion_execution"], "data/outputs/ball_tracking/crop_motion_execution"))
    if (execution["commit"] != PRIOR_COMMIT or execution["manifest"] != p["prior_motion_manifest"]
            or execution["spec_sha256"] != spec_digest(prior_m)
            or execution["derived_outputs"] != p["saved_control_outputs"]
            or execution["scoring"]["reports"] != p["saved_control_scoring_reports"]
            or execution["review_manifest"] != p["prior_review_manifest"]):
        raise ValueError("Saved motion execution binding mismatch")
    expected = [f"{prior_m['output_root']}/{w['window_id']}/{c.variant_id}.json"
                for w in p["windows"] for c in controls.experiment_grid()]
    if len(expected) != 378 or [b["path"] for b in p["saved_control_outputs"]] != expected:
        raise ValueError("Expected exactly 378 ordered saved motion outputs")
    if [b["path"] for b in p["saved_control_scoring_reports"]] != [
            f"{prior_m['output_root']}/evaluation/{purpose}.json" for purpose in p["pool_separation"]]:
        raise ValueError("Expected two separate saved scoring pools")
    for b in [*p["saved_control_outputs"], *p["saved_control_scoring_reports"]]:
        closed(b, {"path", "sha256"}, "saved motion binding")
        require_digest(b["sha256"], "saved motion digest")
    if (len(p["original_embargo_paths"]) != 9
            or p["original_embargo_paths"] != execution["original_embargo_paths_absent"]
            or any(safe_path(root, name).exists() for name in p["original_embargo_paths"])):
        raise ValueError("Original prediction embargo paths must remain absent")
    if (p["sealed_holdouts"] != [["possession_001", 300, 324], ["possession_002", 200, 224], ["possession_003", 250, 274]]
            or p["holdout_release_authorized"] is not False):
        raise ValueError("Three holdouts must remain sealed")
    approval = closed(read_json(bound_file(root, m["authorization"], "configs/ball_tracking/reviews")),
                      {"schema_version", "experiment_spec_sha256", "proposal", "approved_by", "statement",
                       "recorded_at_utc", "timestamp_semantics", "scope", "git_mutations_authorized"}, "context approval")
    if (approval["schema_version"] != "ball_crop_player_context_approval/v0.1"
            or approval["experiment_spec_sha256"] != spec_digest(m) or approval["proposal"] != m["proposal"]
            or approval["approved_by"] != "ryan" or not isinstance(approval["statement"], str)
            or not approval["statement"].strip() or approval["scope"] != APPROVAL_SCOPE
            or approval["git_mutations_authorized"] is not False):
        raise ValueError("Missing exact player context authorization")
    return m, p, *prior_loaded


def load_context(root, p, runs):
    """Open the six-window snapshot, never the whole legacy player CSV files."""
    value = closed(read_json(bound_file(root, p["player_context"]["snapshot"], CONTEXT_ROOT)),
                   SNAPSHOT_FIELDS, "frozen player context snapshot")
    if (value["schema_version"] != "ball_observed_player_context_inputs/v0.1"
            or value["source_experiment_commit"] != PRIOR_COMMIT
            or any(value[k] is not None for k in ("selected_method", "selected_operating_point", "quality_gate"))
            or len(value["windows"]) != len(p["windows"]) or len(runs) != len(p["windows"])):
        raise ValueError("Frozen player context snapshot provenance mismatch")
    contexts, checked_csvs = [], set()
    for expected, context, run in zip(p["windows"], value["windows"], runs):
        for k in ("window_id", "possession_id", "purpose", "start_frame_index", "end_frame_index", "source_video"):
            if context[k] != expected[k]:
                raise ValueError("Frozen context window/source alignment mismatch")
        validate_context_window(context, run)
        binding = context["player_tracks"]
        if binding["path"] not in checked_csvs:
            source = safe_path(root, binding["path"], "data/outputs/identity")
            if sha256_file(source) != binding["sha256"]:
                raise ValueError("Frozen player CSV source binding changed")
            checked_csvs.add(binding["path"])
        contexts.append(context)
    rows = sum(len(c["rows"]) for c in contexts)
    if (rows != p["player_context"]["selected_rows"] or rows != value["scope"]["observed_row_count"]
            or value["scope"]["window_count"] != 6 or value["scope"]["source_frame_count"] != 150
            or canonical_sha256([{"window_id": c["window_id"], "rows": c["rows"]} for c in contexts])
            != value["all_window_rows_canonical_sha256"]):
        raise ValueError("Frozen context row count or digest mismatch")
    return contexts


def verify_source_files(root, p):
    """Hash each original source once; no media decoding or frame access."""
    checked_sources = set()
    for window in p["windows"]:
        source = window["source_video"]
        if source["path"] not in checked_sources:
            if sha256_file(safe_path(root, source["path"], "data/clips")) != source["sha256"]:
                raise ValueError("Frozen source-video byte binding changed")
            checked_sources.add(source["path"])


def load_inputs(root, loaded):
    prior = prior_experiment.load_inputs(root, loaded[2:])
    p = loaded[1]
    verify_source_files(root, p)
    contexts = load_context(root, p, [run for _, run, _ in prior])
    for window, (_, run, digest) in zip(p["windows"], prior):
        for config in controls.experiment_grid():
            load_saved_control(root, p, window, config, run=run, crop_digest=digest)
    return [(*item, context) for item, context in zip(prior, contexts)]


def load_saved_control(root, p, window, config, *, run=None, crop_digest=None):
    """Verify immutable saved bytes and identities without calling any selector."""
    config = controls.RankingConfig.from_mapping(asdict(config))
    expected = f"{prior_experiment.OUTPUT_ROOT}/{window['window_id']}/{config.variant_id}.json"
    matches = [b for b in p["saved_control_outputs"] if b["path"] == expected]
    if len(matches) != 1:
        raise ValueError("Missing or duplicate saved motion control")
    value = closed(read_json(bound_file(root, matches[0], prior_experiment.OUTPUT_ROOT)),
                   {"experiment_spec_sha256", "input_crop_file", "crop_content_sha256", "observations"}, "saved control")
    prior_m = read_json(bound_file(root, p["prior_motion_manifest"], "configs/ball_tracking/crop_motion_experiments"))
    if crop_digest is None:
        crop_digest = read_json(bound_file(root, window["crop_candidates"], "data/outputs/ball_tracking/tiled_development"))["content_sha256"]
    obs = value["observations"]
    if (value["experiment_spec_sha256"] != spec_digest(prior_m) or value["input_crop_file"] != window["crop_candidates"]
            or value["crop_content_sha256"] != crop_digest or obs["schema_version"] != controls.SCHEMA
            or obs["ranking_code_commit"] != PRIOR_COMMIT or obs["config"] != asdict(config)
            or obs["variant_id"] != config.variant_id or obs["possession_id"] != window["possession_id"]
            or obs["source_video"] != window["source_video"]
            or obs["window"] != {k: window[k] for k in ("start_frame_index", "end_frame_index")}
            or [f["frame_index"] for f in obs["frames"]] != list(range(window["start_frame_index"], window["end_frame_index"] + 1))):
        raise ValueError("Saved control provenance mismatch")
    if run is not None and (obs["input_candidate_content_sha256"] != canonical_sha256(run.to_dict())
                            or obs["detector_code_commit"] != run.model_provenance.code_commit):
        raise ValueError("Saved control candidate provenance mismatch")
    return obs


def output_path(root, window, config):
    return safe_path(root, f"{OUTPUT_ROOT}/{window['window_id']}/{config.variant_id}.json", OUTPUT_ROOT)


def preflight(root, path, *, require_clean=True):
    root, path = Path(root).resolve(), Path(path).resolve()
    loaded = load_manifest(root, path)
    m, p = loaded[:2]
    commit = clean_commit(root) if require_clean else git(root, "rev-parse", "HEAD")
    if require_clean:
        for name in [path, root/m["proposal"]["path"], root/m["authorization"]["path"],
                     *(root/p[k]["path"] for k in ("design", "rationale", "motion_review_receipt")),
                     *(root/r["annotation"]["path"] for r in p["scoring_labels"]),
                     *Path(__file__).parent.glob("crop_player_context*.py")]:
            _tracked(root, name)
    target = safe_path(root, f"{OUTPUT_ROOT}/ignore_check.json", OUTPUT_ROOT)
    if subprocess.run(["git", "check-ignore", "-q", "--", target.relative_to(root).as_posix()], cwd=root).returncode:
        raise ValueError("Context outputs must remain Git-ignored")
    return m, p, load_inputs(root, loaded), commit


def unchanged(root, path, m, commit):
    if clean_commit(root) != commit:
        raise ValueError("Git changed during player context stage")
    loaded = load_manifest(root, path)
    if loaded[0] != m:
        raise ValueError("Player context manifest changed during stage")
    load_inputs(root, loaded)


def envelope(root, m, window, run, digest, config, commit, context_window):
    p = read_json(bound_file(root, m["proposal"], "configs/ball_tracking/proposals"))
    observations = rank_candidates(run, config, commit, context_window)
    return {"experiment_spec_sha256": spec_digest(m), "input_crop_file": window["crop_candidates"],
            "crop_content_sha256": digest, "input_player_context_file": p["player_context"]["snapshot"],
            "context_window_sha256": canonical_sha256(context_window),
            "observations_content_sha256": canonical_sha256(observations), "observations": observations}


def load_observations(root, m, window, run, digest, config, commit, context_window, *, rederive=True):
    value = closed(read_json(output_path(root, window, config)), ENVELOPE_FIELDS, "context ranking envelope")
    p = read_json(bound_file(root, m["proposal"], "configs/ball_tracking/proposals"))
    obs = value["observations"]
    if (value["experiment_spec_sha256"] != spec_digest(m) or value["input_crop_file"] != window["crop_candidates"]
            or value["crop_content_sha256"] != digest or value["input_player_context_file"] != p["player_context"]["snapshot"]
            or value["context_window_sha256"] != canonical_sha256(context_window)
            or value["observations_content_sha256"] != canonical_sha256(obs)
            or obs["schema_version"] != "ball_crop_player_context_observations/v0.1"
            or obs["ranking_code_commit"] != commit or obs["config"] != asdict(config)
            or obs["detector_code_commit"] != run.model_provenance.code_commit
            or obs["selected_operating_point"] is not None or obs["quality_gate"] is not None
            or obs["variant_id"] != config.variant_id or obs["source_video"] != run.source_video.to_dict()
            or obs["window"] != run.window.to_dict() or obs["possession_id"] != run.possession_id
            or obs["input_candidate_content_sha256"] != canonical_sha256(run.to_dict())
            or obs["input_context_content_sha256"] != canonical_sha256(context_window)
            or obs["window_rows_sha256"] != context_window["selected_rows_sha256"]
            or [f["frame_index"] for f in obs["frames"]] != [f.frame_index for f in run.frames]):
        raise ValueError("Context ranking input/specification/commit binding mismatch")
    if rederive and validate_observations(obs, run, context_window) != config:
        raise ValueError("Context ranking configuration mismatch")
    return obs


def run_experiment(root, path, *, dry_run=False):
    m, p, inputs, commit = preflight(root, path, require_clean=not dry_run)
    if dry_run:
        return {"dry_run": True, "source_frames": sum(len(r.frames) for _, r, _, _ in inputs),
                "windows": len(inputs), "new_variants": 36, "reused_variants": 63,
                "new_outputs": 216, "reused_outputs": 378, "new_model_calls": 0,
                "execution_requires_clean_commit": True}
    # Validate every existing output before publishing any missing output.
    for w, (_, run, digest, context) in zip(p["windows"], inputs):
        for config in experiment_grid():
            if output_path(root, w, config).exists():
                load_observations(root, m, w, run, digest, config, commit, context)
    created = 0
    for w, (_, run, digest, context) in zip(p["windows"], inputs):
        for config in experiment_grid():
            target = output_path(root, w, config)
            if not target.exists():
                created += persist_once(target, envelope(root, m, w, run, digest, config, commit, context))
    unchanged(root, path, m, commit)
    return {"created_outputs": created, "new_outputs": 216, "reused_outputs": 378,
            "combined_outputs": 594, "new_model_calls": 0, "commit": commit}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = args.repository_root.resolve()
    print(json.dumps(run_experiment(root, (root/args.manifest).resolve(), dry_run=args.dry_run), indent=2))


if __name__ == "__main__":
    main()
