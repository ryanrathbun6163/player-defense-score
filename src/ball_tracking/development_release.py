"""Prepare reviewed release evidence; verify its Git metadata before inference.

Only evidence preparation opens labels. Runtime authorization uses receipt
JSON and Git tree entries, never annotation content or review images.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .development_experiments import (
    EXPERIMENT_ID, EXPERIMENT_ROOT, PARENT_FILENAME, PARENT_SHA256, PROPOSAL_ROOT,
    REVIEW_ROOT, SCHEMA_VERSION, DevelopmentExperiment, binding, bound_file,
    canonical_sha256, closed, development_windows, execution_spec_sha256,
    planned_window, read_json, require_digest, safe_path, sha256_file,
    window_identity,
)
from .detector_experiments import (
    DetectorExperiment, DetectorExperimentValidationError, PREDICTION_EMBARGO,
    _require_utc_timestamp,
)

EVIDENCE_SCHEMA = "ball_detector_development_release_evidence/v0.1"
RECEIPT_SCHEMA = "ball_detector_development_release/v0.1"
APPROVAL_SCHEMA = "ball_detector_development_experiment_approval/v0.1"
EVIDENCE_ROOT = "data/outputs/ball_tracking/release_evidence"
EVIDENCE_FIELDS = {
    "schema_version", "evidence_commit", "parent_experiment", "proposal",
    "experiment_approval", "execution_spec_sha256", "development_windows",
    "protected_files", "validation", "prepared_at_utc",
}
RECEIPT_FIELDS = {
    "schema_version", "evidence_commit", "validation_report", "parent_experiment",
    "execution_spec_sha256", "development_windows", "approval",
}


def _fail(message: str):
    raise DetectorExperimentValidationError(message)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True,
                            text=True, encoding="utf-8", check=False)
    if result.returncode:
        _fail(f"Git release check failed: {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def _clean_head(root: Path) -> str:
    if Path(_git(root, "rev-parse", "--show-toplevel")).resolve() != root:
        _fail("Release requires the exact repository root")
    head = require_digest(_git(root, "rev-parse", "HEAD"), "HEAD", 40)
    if _git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        _fail("Release evidence requires an exactly clean committed worktree")
    return head


def _tree_blob(root: Path, commit: str, path: str) -> str:
    safe_path(root, path)
    raw = _git(root, "ls-tree", "-z", commit, "--", path)
    records = [item for item in raw.split("\0") if item]
    if len(records) != 1:
        _fail(f"Release input is not committed: {path}")
    metadata, recorded_path = records[0].split("\t", 1)
    mode, kind, digest = metadata.split()
    if recorded_path != path or mode not in {"100644", "100755"} or kind != "blob":
        _fail(f"Release input is not a regular committed file: {path}")
    return require_digest(digest, "Git blob", 40)


def _code_paths(root: Path, commit: str) -> set[str]:
    raw = _git(root, "ls-tree", "-r", "--name-only", "-z", commit, "--",
               "src/ball_tracking", "tests")
    return {p for p in raw.split("\0") if p.endswith(".py")}


def _label_paths(parent) -> set[str]:
    paths = set()
    for w in development_windows(parent):
        prefix = f"{w.possession_id}_frames_{w.start_frame_index:04d}_{w.end_frame_index:04d}"
        paths.add(f"configs/ball_tracking/annotations/{w.annotation_set_id}.json")
        paths.add(f"{REVIEW_ROOT}/{prefix}_visual_review_approval_v0_1.json")
        paths.add(f"{REVIEW_ROOT}/{prefix}_single_annotator_finalization_v0_1.json")
    return paths


def execution_spec(parent: DetectorExperiment) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "experiment_purpose": "image_only_ball_detector_development",
        "parent_experiment": {"path": f"{EXPERIMENT_ROOT}/{PARENT_FILENAME}",
                              "sha256": PARENT_SHA256},
        "detector": parent.detector.to_dict(),
        "scoring_grid": parent.scoring_grid.to_dict(),
        "leakage_controls": parent.leakage_controls.to_dict(),
        "windows": [planned_window(w) for w in development_windows(parent)],
        "sealed_holdouts": [window_identity(w) for w in parent.windows
                            if w.selection_purpose == "test_holdout"],
    }


def _validate_approval(value: dict) -> dict:
    value = closed(value, {"schema_version", "proposal", "approved_by",
                           "approved_at_utc", "statement", "scope",
                           "git_mutations_authorized"}, "experiment approval")
    if value["schema_version"] != APPROVAL_SCHEMA or value["approved_by"] != "ryan":
        _fail("Experiment approval must identify Ryan and the versioned schema")
    binding(value["proposal"], PROPOSAL_ROOT)
    _require_utc_timestamp(value["approved_at_utc"], "approval timestamp")
    if (not isinstance(value["statement"], str) or not value["statement"].strip()
        or value["scope"] != "six_development_windows_only"
        or value["git_mutations_authorized"] is not False):
        _fail("Invalid experiment approval scope")
    return value


def _check_sealed_outputs(root: Path, parent: DetectorExperiment, *, preparing=False):
    for w in parent.windows:
        if w.execution_status == PREDICTION_EMBARGO:
            if safe_path(root, w.output_path.as_posix()).exists():
                _fail(f"Historical embargo output unexpectedly exists: {w.output_path}")
    if preparing:
        for w in development_windows(parent):
            if safe_path(root, planned_window(w)["output_path"]).exists():
                _fail("Development predictions exist before release preparation")


def verify_annotation_evidence(root: Path, parent: DetectorExperiment, proposal: dict):
    """Label-aware, read-only check of every approved development reference."""
    from .annotations import load_annotations, verify_source_video

    rows = proposal.get("development_windows")
    expected = development_windows(parent)
    if not isinstance(rows, list) or len(rows) != len(expected):
        _fail("Proposal must bind all six development annotations")
    for record, w in zip(rows, expected, strict=True):
        for field in ("annotation_set_id", "possession_id", "selection_purpose",
                      "start_frame_index", "end_frame_index", "source_video"):
            if record.get(field) != window_identity(w)[field]:
                _fail(f"Proposal window mismatch: {field}")
        annotation_path = bound_file(root, record["annotation"],
                                     "configs/ball_tracking/annotations")
        approval_path = bound_file(root, record["approval_receipt"], REVIEW_ROOT)
        final_path = bound_file(root, record["finalization_receipt"], REVIEW_ROOT)
        expected_paths = _label_paths(parent)
        if any(p.relative_to(root).as_posix() not in expected_paths
               for p in (annotation_path, approval_path, final_path)):
            _fail("Proposal names an unexpected label or receipt")
        a = load_annotations(annotation_path)
        data = a.to_dict()
        if a.review.status != "reviewed" or a.review.reviewer_id != "ryan":
            _fail("Development labels must be reviewed by Ryan")
        if (a.annotation_set_id != w.annotation_set_id or a.possession_id != w.possession_id
            or a.source_video != w.source_video
            or a.window.to_dict() != {"start_frame_index": w.start_frame_index,
                "end_frame_index": w.end_frame_index, "selection_purpose": w.selection_purpose}):
            _fail("Reviewed annotation does not match selected source/window")
        verify_source_video(a, root)
        approval, final = read_json(approval_path), read_json(final_path)
        if (approval.get("schema_version") != "ball_annotation_visual_review_approval/v0.1"
            or final.get("schema_version") != "ball_annotation_finalization/v0.1"):
            _fail("Invalid annotation receipt schema")
        for value in (approval, final):
            if value["possession_id"] != w.possession_id or value["window"] != {
                "start_frame_index": w.start_frame_index,
                "end_frame_index": w.end_frame_index, "frame_count": w.frame_count,
            }:
                _fail("Annotation receipt window mismatch")
        stamp = approval["approval"]
        if (stamp["approved_by"] != "ryan" or not stamp["statement"].strip()
            or stamp["approved_at_utc"] != a.review.reviewed_at_utc):
            _fail("Annotation approval identity/time mismatch")
        final_binding = final["final_annotation"]
        if (final_binding["path"] != record["annotation"]["path"]
            or final_binding["annotation_file_sha256"] != sha256_file(annotation_path)
            or final_binding["canonical_annotation_sha256"] != canonical_sha256(data)):
            _fail("Final annotation receipt does not bind the reviewed file")
        ar = final["approved_visual_review"]
        if (ar["approval_receipt_path"] != record["approval_receipt"]["path"]
            or ar["approval_receipt_file_sha256"] != sha256_file(approval_path)
            or ar["approval_receipt_canonical_sha256"] != canonical_sha256(approval)):
            _fail("Finalization does not bind the approval receipt")
        bundle_manifest = bound_file(root, record["visual_review_manifest"],
                                     "data/outputs/ball_tracking/annotation_visual_review")
        bundle_dir, m = bundle_manifest.parent, read_json(bundle_manifest)
        if (approval["visual_review_bundle"]["path"] != bundle_dir.relative_to(root).as_posix()
            or approval["visual_review_bundle"]["manifest_sha256"] != sha256_file(bundle_manifest)
            or ar["visual_bundle_manifest_sha256"] != sha256_file(bundle_manifest)):
            _fail("Approved visual package mismatch")
        snapshot = read_json(bundle_dir / "annotation_snapshot.json")
        approved_inputs = approval["bound_inputs"]
        if (approved_inputs["annotation_file_sha256"] != sha256_file(bundle_dir / "annotation_snapshot.json")
            or approved_inputs["canonical_annotation_sha256"] != canonical_sha256(snapshot)
            or approved_inputs["source_video_sha256"] != w.source_video.sha256
            or approved_inputs["neutral_manifest_sha256"] != sha256_file(bundle_dir / "neutral_manifest_snapshot.json")):
            _fail("Approved snapshot/source hashes mismatch")
        transition = final["transition"]
        allowed = ["/review/status", "/review/reviewer_id", "/review/reviewed_at_utc"]
        reconstructed = copy.deepcopy(snapshot)
        reconstructed["review"].update(status="reviewed", reviewer_id="ryan",
                                        reviewed_at_utc=stamp["approved_at_utc"])
        if (reconstructed != data or transition["before_review"] != snapshot["review"]
            or transition["after_review"] != data["review"]
            or transition["allowed_changed_json_pointers"] != allowed
            or transition["actual_changed_json_pointers"] != allowed
            or transition["annotation_rows_sha256"] != canonical_sha256(data["annotations"])):
            _fail("Finalization changed frame decisions or review provenance")
        decisions = canonical_sha256({k: v for k, v in data.items() if k != "review"})
        if any(transition[k] != decisions for k in (
            "approved_decision_payload_sha256", "final_decision_payload_sha256")):
            _fail("Decision payload hash mismatch")
        assets = [m["annotation"]["snapshot"], m["neutral_bundle"]["snapshot"]]
        for value in m["assets"].values():
            assets.extend(value if isinstance(value, list) else [value])
        if len(assets) != 55:
            _fail("Annotation review package must contain all 55 assets")
        seen = set()
        for asset in assets:
            path = safe_path(bundle_dir, asset["path"])
            if asset["path"] in seen or path.stat().st_size != asset["byte_size"] or sha256_file(path) != asset["sha256"]:
                _fail("Annotation review asset missing, repeated, or changed")
            seen.add(asset["path"])


def _run_tests(root: Path) -> dict:
    python = root / ".venv/Scripts/python.exe"
    if not python.is_file():
        python = root / ".venv/bin/python"
    if not python.is_file():
        _fail("Release validation requires the repository .venv")
    args = [str(python), "-B", "-m", "unittest", "discover", "-s", "tests", "-v"]
    result = subprocess.run(args, cwd=root, capture_output=True, check=False)
    output = result.stdout + result.stderr
    match = re.search(rb"Ran (\d+) tests? in", output)
    if result.returncode != 0 or match is None or int(match[1]) == 0:
        _fail("Full release-validation test suite failed or discovered no tests")
    return {"returncode": 0, "tests_run": int(match[1]),
            "output_sha256": hashlib.sha256(output).hexdigest()}


def prepare_release_evidence(proposal_path: Path, approval_path: Path, root: Path,
                             *, test_runner=None) -> dict:
    root = root.resolve()
    head = _clean_head(root)
    proposal_binding = {"path": proposal_path.resolve().relative_to(root).as_posix(),
                        "sha256": sha256_file(proposal_path)}
    approval_binding = {"path": approval_path.resolve().relative_to(root).as_posix(),
                        "sha256": sha256_file(approval_path)}
    proposal = read_json(bound_file(root, proposal_binding, PROPOSAL_ROOT))
    approval = _validate_approval(read_json(bound_file(root, approval_binding, REVIEW_ROOT)))
    if approval["proposal"] != proposal_binding:
        _fail("Experiment approval binds a different proposal")
    if proposal.get("schema_version") != "ball_detector_development_release_proposal/v0.1":
        _fail("Expected a development release proposal")
    parent_binding = {"path": f"{EXPERIMENT_ROOT}/{PARENT_FILENAME}", "sha256": PARENT_SHA256}
    if proposal["parent_experiment"] != parent_binding:
        _fail("Proposal changed the frozen parent")
    parent = DetectorExperiment.from_mapping(read_json(bound_file(root, parent_binding, EXPERIMENT_ROOT)))
    _check_sealed_outputs(root, parent, preparing=True)
    verify_annotation_evidence(root, parent, proposal)
    paths = _label_paths(parent) | _code_paths(root, head) | {
        proposal_binding["path"], approval_binding["path"], parent_binding["path"],
    }
    protected = [{"path": p, "git_blob": _tree_blob(root, head, p),
                  "sha256": sha256_file(safe_path(root, p))} for p in sorted(paths)]
    validation = (test_runner or _run_tests)(root)
    if _clean_head(root) != head or any(
        sha256_file(safe_path(root, item["path"])) != item["sha256"] for item in protected
    ):
        _fail("Release inputs changed during validation")
    _check_sealed_outputs(root, parent, preparing=True)
    return {
        "schema_version": EVIDENCE_SCHEMA, "evidence_commit": head,
        "parent_experiment": parent_binding, "proposal": proposal_binding,
        "experiment_approval": approval_binding,
        "execution_spec_sha256": execution_spec_sha256(execution_spec(parent)),
        "development_windows": [window_identity(w) for w in development_windows(parent)],
        "protected_files": protected, "validation": validation,
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def _verify_evidence_metadata(root: Path, head: str, evidence: dict,
                              parent: DetectorExperiment, spec_digest: str):
    evidence = closed(evidence, EVIDENCE_FIELDS, "release evidence")
    if evidence["schema_version"] != EVIDENCE_SCHEMA:
        _fail("Invalid release evidence schema")
    evidence_commit = require_digest(evidence["evidence_commit"], "evidence commit", 40)
    _git(root, "merge-base", "--is-ancestor", evidence_commit, head)
    if evidence["execution_spec_sha256"] != spec_digest:
        _fail("Release execution specification changed")
    expected_parent = {"path": f"{EXPERIMENT_ROOT}/{PARENT_FILENAME}", "sha256": PARENT_SHA256}
    if (evidence["parent_experiment"] != expected_parent
        or evidence["development_windows"] != [window_identity(w) for w in development_windows(parent)]):
        _fail("Release evidence changed parent or development scope")
    approval_path = bound_file(root, evidence["experiment_approval"], REVIEW_ROOT)
    approval = _validate_approval(read_json(approval_path))
    proposal_binding = binding(evidence["proposal"], PROPOSAL_ROOT)
    if approval["proposal"] != proposal_binding:
        _fail("Release evidence lacks matching experiment approval")
    validation = closed(evidence["validation"], {"returncode", "tests_run", "output_sha256"}, "validation")
    if (type(validation["returncode"]) is not int or validation["returncode"] != 0
        or type(validation["tests_run"]) is not int or validation["tests_run"] <= 0):
        _fail("Release evidence has no passing test validation")
    require_digest(validation["output_sha256"], "test output")
    _require_utc_timestamp(evidence["prepared_at_utc"], "prepared_at_utc")
    expected_paths = _label_paths(parent) | _code_paths(root, head) | {
        proposal_binding["path"], evidence["experiment_approval"]["path"], expected_parent["path"],
    }
    records = evidence["protected_files"]
    if not isinstance(records, list) or len(records) != len(expected_paths):
        _fail("Release evidence omits protected files")
    if {r.get("path") for r in records} != expected_paths:
        _fail("Release evidence protected-file set changed")
    for record in records:
        record = closed(record, {"path", "git_blob", "sha256"}, "protected file")
        require_digest(record["sha256"], "protected file")
        if (_tree_blob(root, evidence_commit, record["path"]) != record["git_blob"]
            or _tree_blob(root, head, record["path"]) != record["git_blob"]):
            _fail(f"Protected Git blob changed since evidence validation: {record['path']}")
    return approval


def validate_development_release(experiment, root: Path, head: str) -> None:
    """Runtime check: metadata only. Call before constructing any adapter."""
    if not isinstance(experiment, DevelopmentExperiment):
        return
    if _clean_head(root) != head:
        _fail("Release HEAD changed after preflight")
    payload = experiment.to_dict()
    receipt_path = bound_file(root, payload["release_authorization"], REVIEW_ROOT)
    _tree_blob(root, head, payload["release_authorization"]["path"])
    receipt = closed(read_json(receipt_path), RECEIPT_FIELDS, "release authorization")
    if receipt["schema_version"] != RECEIPT_SCHEMA:
        _fail("Wrong release-authorization schema")
    report_path = bound_file(root, receipt["validation_report"], REVIEW_ROOT)
    _tree_blob(root, head, receipt["validation_report"]["path"])
    evidence = read_json(report_path)
    approval = _verify_evidence_metadata(root, head, evidence, experiment.parent,
                                         execution_spec_sha256(payload))
    for field in ("evidence_commit", "parent_experiment", "execution_spec_sha256", "development_windows"):
        if receipt[field] != evidence[field]:
            _fail(f"Release receipt conflicts with evidence: {field}")
    if receipt["approval"] != approval:
        _fail("Release receipt does not preserve the explicit experiment approval")
    _check_sealed_outputs(root, experiment.parent)


def publish_new_json(path: Path, value: dict):
    """Create only; existing reviewed/configured files are never overwritten."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def development_review_plan(purpose: str) -> dict:
    from .development_experiments import PURPOSES
    from .prepare_detection_visual_review import (
        DEVELOPMENT_PLAN_SCHEMA_VERSION, EXPECTED_RENDER_SCOPE,
    )
    if purpose not in PURPOSES:
        _fail("Review plan must name a development pool")
    scope = dict(EXPECTED_RENDER_SCOPE)
    scope["selection_purpose"] = purpose
    scope["all_authorized_pool_windows"] = scope.pop("all_authorized_pilots")
    return {
        "schema_version": DEVELOPMENT_PLAN_SCHEMA_VERSION,
        "review_id": f"{EXPERIMENT_ID}_{purpose}_comparison",
        "experiment_id": EXPERIMENT_ID,
        "scoring_report_path": (f"data/outputs/ball_tracking/evaluations/{EXPERIMENT_ID}/"
                                f"{purpose}_grid_v0_2.json"),
        "purpose": "descriptive_development_pool_candidate_comparison",
        "views": [{"view_id": f"confidence_{int(t * 100):03d}_radius_10",
                   "confidence_threshold": t, "localization_radius_px": 10.0,
                   "role": "descriptive_display_cell_not_selected"} for t in (0.35, 0.20)],
        "render_scope": scope,
        "interpretation": {
            "selected_operating_point": None, "quality_gate": None,
            "model_winner_claimed": False, "generalization_claimed": False,
            "holdout_evidence_included": False,
            "decision_statement": "Display the two predeclared cells; neither selects an operating point or quality gate.",
        },
    }


def prepare_activation(report_path: Path, root: Path) -> tuple[Path, ...]:
    root = root.resolve()
    head = _clean_head(root)
    report_path = safe_path(root, report_path.resolve().relative_to(root).as_posix(), EVIDENCE_ROOT)
    evidence = read_json(report_path)
    parent = DetectorExperiment.from_mapping(read_json(bound_file(root, evidence["parent_experiment"], EXPERIMENT_ROOT)))
    spec = execution_spec(parent)
    approval = _verify_evidence_metadata(root, head, evidence, parent, execution_spec_sha256(spec))
    _check_sealed_outputs(root, parent, preparing=True)
    stem = f"{EXPERIMENT_ID}_{evidence['evidence_commit'][:12]}"
    evidence_relative = f"{REVIEW_ROOT}/{stem}_evidence.json"
    receipt_relative = f"{REVIEW_ROOT}/{stem}_release.json"
    manifest_relative = f"{EXPERIMENT_ROOT}/{EXPERIMENT_ID}.json"
    from .development_experiments import PURPOSES
    plans = tuple(development_review_plan(purpose) for purpose in PURPOSES)
    paths = tuple(safe_path(root, p) for p in (
        evidence_relative, receipt_relative, manifest_relative,
        *(f"{REVIEW_ROOT}/{plan['review_id']}.json" for plan in plans),
    ))
    if any(p.exists() for p in paths):
        _fail("Activation artifacts already exist; refusing to overwrite")
    # Hash the exact future evidence bytes, avoiding a commit/receipt hash cycle.
    evidence_bytes = (json.dumps(evidence, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    receipt = {"schema_version": RECEIPT_SCHEMA,
               "validation_report": {"path": evidence_relative,
                   "sha256": hashlib.sha256(evidence_bytes).hexdigest()},
               "approval": approval,
               **{key: evidence[key] for key in (
                   "evidence_commit", "parent_experiment", "execution_spec_sha256", "development_windows")}}
    receipt_bytes = (json.dumps(receipt, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    manifest = {**spec, "release_authorization": {
        "path": receipt_relative, "sha256": hashlib.sha256(receipt_bytes).hexdigest()}}
    # No execution follows. These five files still require separate Git authorization.
    for path, value in zip(paths, (evidence, receipt, manifest, *plans), strict=True):
        publish_new_json(path, value)
    return paths


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare-evidence")
    prepare.add_argument("--proposal", type=Path, required=True)
    prepare.add_argument("--approval", type=Path, required=True)
    activate = commands.add_parser("prepare-activation")
    activate.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.repository_root.resolve()
    if args.command == "prepare-evidence":
        result = prepare_release_evidence(args.proposal, args.approval, root)
        output = safe_path(root, f"{EVIDENCE_ROOT}/{result['evidence_commit']}/validation.json")
        publish_new_json(output, result)
        print(output)
    else:
        for path in prepare_activation(args.evidence, root):
            print(path)


if __name__ == "__main__":
    main()
