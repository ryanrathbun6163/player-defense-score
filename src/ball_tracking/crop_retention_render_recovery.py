"""Explicit render-only recovery of receipted selections and completed scores.

Earlier artifacts keep their actual source/specification identities. This module
never dispatches a selector, evaluator, or pool aggregation operation.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys

from . import crop_retention_experiment as original
from . import crop_retention_recovery as previous
from . import crop_retention_evaluation as scoring
from .crop_retention_resources import BudgetJournal, run_supervised, wait_for_supervisor
from .development_experiments import canonical_sha256, read_json, safe_path

ORIGINAL_COMMIT = previous.ORIGINAL_COMMIT
ORIGINAL_SPEC_SHA256 = previous.ORIGINAL_SPEC_SHA256
SCORING_COMMIT = "f36237247191e726ad7e81bdc6651f9340a9063d"
SCORING_SPEC_SHA256 = "4b1f9f3c75ee53eb1358bcb49981118269694ec39adb5a312ae325f8ee273bbf"
SCORING_MANIFEST_SHA256 = "2e1a57cfdacfa0359f328d467fd75b513b81fde192f69e4bd2a9919dbb7a6e1f"
RENDER_PROPOSAL_SHA256 = "2d9ea51ca4f93fbc77d902266dcbf1ef496edcb8c320c7a0dbbe6d86bf884b48"
APPROVAL_SHA256 = "133981a85b191e931e739ad0c3030659072282665db0dd5cb234716fb52f71f6"
INTERRUPTION_SHA256 = "f2bece32af228b0f525b07eb060b1671194812b26af7787283c8ecca2aabea8b"
CHECKPOINT_SHA256 = "8dce571305282e59dc61e3ceb610e2ea0e5dbd86ce1896beb9e035c8ee12dcac"
RECOVERY_ID = "rfdetr_medium_crop_candidate_retention_render_recovery_v0_1"
OUTPUT_ROOT = original.OUTPUT_ROOT
PERMITTED_STAGES = ["verify", "render"]
MANIFEST_FIELDS = {"schema_version", "recovery_id", "scoring_manifest", "render_proposal", "authorization",
                   "interruption_receipt", "resource_checkpoint", "implementation_validation", "output_root",
                   "permitted_stages", "selected_method", "selected_operating_point", "quality_gate"}
CHANGED_SCORING_PATHS = {"src/ball_tracking/crop_retention_resources.py",
                         "src/ball_tracking/crop_retention_review.py",
                         "tests/test_ball_crop_retention_recovery_resources.py"}
_require = original._require
verify_binding = original.verify_binding
file_binding = original.file_binding


def _pairs(rows):
    pairs = {(b["path"], b["sha256"]) for b in rows}
    _require(len(pairs) == len(rows) and len({b["path"] for b in rows}) == len(rows),
             "Duplicate preserved evidence binding")
    return pairs


def _validate_implementation(root, manifest):
    binding = manifest["implementation_validation"]
    _require(isinstance(binding, dict), "Render recovery implementation validation is missing")
    certificate = read_json(verify_binding(root, binding))
    flags = ("focused_tests_passed", "full_suite_passed", "resource_abort_and_resume_tests_passed",
             "independent_static_review_passed")
    _require(all(certificate.get(k) is True for k in flags), "Render recovery validation is incomplete")
    for field, authority in (("render_proposal_sha256", "render_proposal"),
                             ("resource_checkpoint_sha256", "resource_checkpoint"),
                             ("interruption_receipt_sha256", "interruption_receipt"),
                             ("scoring_manifest_sha256", "scoring_manifest")):
        _require(certificate[field] == manifest[authority]["sha256"], "Validation belongs to another render recovery scope")
    _require(certificate["render_proposal_sha256"] == RENDER_PROPOSAL_SHA256,
             "Validation does not bind the approved render proposal")
    required = {p.relative_to(root).as_posix() for folder in ("src", "tests")
                for p in (root / folder).rglob("*.py")}
    required.add("requirements.txt")
    bindings = certificate["source_bindings"]
    _pairs(bindings)
    _require(required <= {b["path"] for b in bindings}, "Validation omits source dependencies or tests")
    for b in bindings + certificate["evidence_bindings"]:
        verify_binding(root, b)
    for name in required:
        original._git(root, "ls-files", "--error-unmatch", "--", name)


def _metadata(root, manifest_path, require_clean):
    root, path = Path(root).resolve(), Path(manifest_path).resolve()
    # Fail before authority/input reads if execution is not at a clean checkpoint.
    commit = original._clean_checkpoint(root) if require_clean else original._git(root, "rev-parse", "HEAD")
    safe_path(root, path.relative_to(root).as_posix(), "configs/ball_tracking/crop_retention_experiments")
    manifest = read_json(path)
    _require(set(manifest) == MANIFEST_FIELDS
             and manifest["schema_version"] == "ball_crop_candidate_retention_render_recovery/v0.1"
             and manifest["recovery_id"] == RECOVERY_ID and manifest["output_root"] == OUTPUT_ROOT
             and manifest["permitted_stages"] == PERMITTED_STAGES,
             "Unsupported render recovery manifest or stage")
    _require(all(manifest[k] is None for k in ("selected_method", "selected_operating_point", "quality_gate")),
             "Render recovery does not choose a method, operating point or gate")
    for field, digest in (("scoring_manifest", SCORING_MANIFEST_SHA256), ("render_proposal", RENDER_PROPOSAL_SHA256),
                          ("authorization", APPROVAL_SHA256), ("interruption_receipt", INTERRUPTION_SHA256),
                          ("resource_checkpoint", CHECKPOINT_SHA256)):
        _require(manifest[field]["sha256"] == digest, "Render recovery authority differs from the approved scope")
    _require(manifest["scoring_manifest"]["content_sha256"] == SCORING_SPEC_SHA256,
             "Completed scoring specification differs")
    verify_binding(root, manifest["render_proposal"])
    approval = read_json(verify_binding(root, manifest["authorization"]))
    _require(approval["schema_version"] == "ball_crop_candidate_retention_render_recovery_approval/v0.1"
             and approval["proposal"] == manifest["render_proposal"] and approval["approved_by"] == "ryan"
             and approval["implementation_authorized"] is True and approval["execution_authorized"] is True
             and approval["training_authorized"] is False and approval["git_mutations_authorized"] is False,
             "Exact render recovery authorization is missing")
    if require_clean:
        _validate_implementation(root, manifest)
        _require(subprocess.run(["git", "merge-base", "--is-ancestor", SCORING_COMMIT, "HEAD"], cwd=root).returncode == 0,
                 "Render execution must descend from the completed scoring checkpoint")
        for name in (path.relative_to(root).as_posix(), manifest["render_proposal"]["path"], manifest["authorization"]["path"]):
            original._git(root, "ls-files", "--error-unmatch", "--", name)
    old = previous._metadata(root, verify_binding(root, manifest["scoring_manifest"]), False)
    _require(old["spec_sha256"] == SCORING_SPEC_SHA256, "Scoring canonical specification changed")
    old["commit"] = SCORING_COMMIT
    certificate = read_json(verify_binding(root, old["manifest"]["implementation_validation"]))
    for b in certificate["source_bindings"]:
        if b["path"] not in CHANGED_SCORING_PATHS:
            verify_binding(root, b)
    interruption = read_json(verify_binding(root, manifest["interruption_receipt"]))
    checkpoint = read_json(verify_binding(root, manifest["resource_checkpoint"]))
    _require(checkpoint["schema_version"] == "ball_crop_retention_render_interruption_checkpoint/v0.1"
             and checkpoint["commit"] == SCORING_COMMIT
             and checkpoint["forensic_receipt"] == manifest["interruption_receipt"]
             and len(checkpoint["journal_prefix"]["events"]) == 1170
             and checkpoint["completed_attempts"] == 41 and checkpoint["successful_attempts"] == 39
             and checkpoint["failed_attempts"] == 2 and checkpoint["comparison_audit_complete"] is False
             and checkpoint["human_visual_review_complete"] is False,
             "The complete post-diagnosis checkpoint is required")
    _require(interruption["experiment_commit"] == SCORING_COMMIT
             and interruption["spec_sha256"] == SCORING_SPEC_SHA256
             and interruption["manifest"] == {k: manifest["scoring_manifest"][k] for k in ("path", "sha256")}
             and interruption["implementation_validation"] == old["manifest"]["implementation_validation"]
             and interruption["preserved_inventory"] == old["manifest"]["preserved_inventory"],
             "Interruption proof is not bound to the preserved scoring authorities")
    return {"root": root, "manifest_path": path, "manifest": manifest, "approval": approval,
            "original_context": old["original_context"], "scoring_context": old, "inventory": old["inventory"],
            "interruption": interruption, "checkpoint": checkpoint, "proposal": old["proposal"],
            "commit": commit, "spec_sha256": canonical_sha256(manifest), "output_root": root / OUTPUT_ROOT}


def _expected_artifacts(context, stage, key):
    prefix = context["output_root"].relative_to(context["root"]).as_posix()
    windows = {w["window_id"] for w in context["proposal"]["windows"]}
    if stage in ("verify", "preflight"):
        _require(key in ("", *PERMITTED_STAGES), "Unknown render verification scope")
        return set()
    if stage == "render":
        _require(key in windows, "Unknown render recovery window")
        return {f"{prefix}/review/windows/{key}/manifest.json"}
    if stage == "review-final":
        _require(key == "", "Unknown review finalization key")
        return {f"{prefix}/review/manifest.json"}
    if stage == "completion-audit":
        # Receipt-only role for the separately reviewed independent helper.
        _require(key == "", "Unknown independent completion-audit key")
        return {f"{prefix}/audit/independent_render_recovery_audit.json"}
    raise ValueError("Selection, scoring, aggregation and unknown stages are forbidden")


def _score_paths(context):
    return (set().union(*(previous._expected_artifacts(context, "score", w["window_id"])
                          for w in context["proposal"]["windows"]))
            | previous._expected_artifacts(context, "score-final", ""))


def _verify_seal(root, output, binding, identifier, suffix, event):
    expected = output / "attempts" / (identifier + suffix)
    _require(binding["path"] == expected.relative_to(root).as_posix()
             and read_json(verify_binding(root, binding)) == {"event_sha256": event["sha256"]},
             "Resource reservation/completion seal changed")


def verify_history(root, context):
    """Bind both failures, every historical attempt, and only receipted new renders."""
    root, output = Path(root).resolve(), context["output_root"]
    checkpoint, interruption = context["checkpoint"], context["interruption"]
    prefix, old_prefix = checkpoint["journal_prefix"], context["inventory"]["journal_prefix"]
    journal = BudgetJournal(output, context["proposal"]["resource_limits"])
    bindings = prefix["events"]
    _require(bindings and len(journal.events) >= len(bindings)
             and bindings[:len(old_prefix["events"])] == old_prefix["events"], "Missing or altered preserved resource prefix")
    for i, binding in enumerate(bindings):
        _require(binding["path"] == (output / "resource_events" / f"{i:08d}.json").relative_to(root).as_posix(),
                 "Non-contiguous resource prefix")
        verify_binding(root, binding)
    events = journal.events[:len(bindings)]
    _require(events[-1]["sha256"] == prefix["chain_tip_sha256"], "Preserved resource chain tip changed")
    _require(journal.events[len(old_prefix["events"])-1]["sha256"] == old_prefix["chain_tip_sha256"],
             "Original resource prefix chain tip changed")
    starts = {e["attempt_id"]: e for e in events if e["kind"] == "started"}
    finishes = {e["attempt_id"]: e for e in events if e["kind"] == "finished"}
    rows = prefix["attempts"]
    _require(len(rows) == 41 and len(starts) == len(finishes) == len(rows)
             and len({r["attempt_id"] for r in rows}) == len(rows)
             and {r["attempt_id"] for r in rows} == set(starts) == set(finishes),
             "The complete 41-attempt post-diagnosis history is required")
    old_rows = {r["attempt_id"]: r for r in old_prefix["attempts"]}
    selection_rows = {r["attempt_id"]: r for r in context["inventory"]["selections"]}
    failed_score = context["inventory"]["failed_scoring"]
    failed_render = interruption["failed_render_completion_event"]
    _require(len(old_rows) == len(old_prefix["attempts"]) == 29
             and {r["attempt_id"] for r in old_prefix["attempts"] if r["role"] == "selection"} == set(selection_rows)
             and [r["attempt_id"] for r in old_prefix["attempts"] if r["role"] == "failed_score"]
             == [failed_score["attempt_id"]], "Original selection and failure role inventory changed")
    _require(failed_render in events and failed_render["success"] is False and failed_render["worker_result"] is None,
             "Known renderer failure differs from the preserved history")
    _require(set(old_rows) <= set(starts), "Original attempt inventory is missing")
    successes, scoring_artifacts, diagnosis = [], [], []
    suffix_roles = []
    for row in rows:
        identifier = row["attempt_id"]
        start, finish = starts[identifier], finishes[identifier]
        _require(row["unit_key"] == start["unit_key"] and row["success"] is finish["success"]
                 and row["completion_event_sha256"] == finish["sha256"], "Checkpoint attempt role or completion changed")
        _verify_seal(root, output, row["reservation"], identifier, ".reservation.json", start)
        _verify_seal(root, output, row["completion"], identifier, ".completion.json", finish)
        if identifier in old_rows:
            old_row = old_rows[identifier]
            _require(all(row[f] == old_row[f] for f in ("reservation", "completion", "worker_result")),
                     "Original attempt seal/result inventory changed")
        if finish["success"] is False:
            _require(row["worker_result"] is None and finish["worker_result"] is None,
                     "Failed worker cannot authorize an artifact")
            if identifier == failed_score["attempt_id"]:
                _require(finish["sha256"] == failed_score["completion_event_sha256"], "Original scoring failure changed")
            else:
                _require(identifier == failed_render["attempt_id"]
                         and start["unit_key"] == "recovery:render:" + context["proposal"]["windows"][0]["window_id"],
                         "Unknown preserved failure")
            continue
        _require(row["worker_result"] is not None and finish["worker_result"] is not None
                 and row["worker_result"] == previous._root_binding(root, output, finish["worker_result"]),
                 "Successful completion lacks its exact worker receipt")
        value = read_json(verify_binding(root, row["worker_result"]))
        successes.append(row["worker_result"])
        if identifier in old_rows:
            _require(value["commit"] == ORIGINAL_COMMIT and value["spec_sha256"] == ORIGINAL_SPEC_SHA256,
                     "Original selection-era worker provenance changed")
            role = old_rows[identifier]["role"]
            if role == "selection":
                entry = selection_rows.get(identifier)
                _require(entry is not None and value["stage"] == "select"
                         and value["key"] == entry["unit"]["comparison_unit_id"]
                         and start["unit_key"] == "select:" + value["key"]
                         and value["artifacts"] == [entry["manifest"]]
                         and row["worker_result"] == entry["worker_result"], "Unknown preserved selection receipt")
            else:
                _require(role in ("preflight", "diagnosis", "preparation")
                         and value["stage"] in ({"preflight"} if role == "preflight" else {role, "verify"}),
                         "Unknown original non-selection role")
                for b in value["artifacts"]:
                    relative = safe_path(root, b["path"]).relative_to(output).as_posix()
                    _require(relative.split("/")[0] not in ("observations", "evaluation", "review"),
                             "A diagnostic worker cannot authorize scientific output")
        else:
            _require(value["commit"] == SCORING_COMMIT and value["spec_sha256"] == SCORING_SPEC_SHA256
                     and start["unit_key"] == "recovery:" + value["stage"] + ":" + value["key"],
                     "Completed scoring-era worker provenance changed")
            stage, key = value["stage"], value["key"]
            suffix_roles.append((stage, key))
            if stage == "render-interruption-diagnosis":
                _require(key == "" and value["artifacts"] == [context["manifest"]["interruption_receipt"]]
                         and finish == events[-1], "Post-failure diagnosis is incomplete or differs")
                diagnosis.append(row["worker_result"])
            else:
                _require(stage in ("preflight", "score", "score-final"), "Unknown preserved scoring-era role")
                expected = previous._expected_artifacts(context, stage, key)
                _require(len(value["artifacts"]) == len(expected)
                         and {b["path"] for b in value["artifacts"]} == expected, "Incomplete scoring worker receipt")
                if stage != "preflight":
                    scoring_artifacts.extend(value["artifacts"])
        for b in value["artifacts"]:
            verify_binding(root, b)
    expected_roles = [("preflight", key) for key in ("verify", "score", "render")]
    expected_roles += [("score", w["window_id"]) for w in context["proposal"]["windows"]]
    expected_roles += [("score-final", ""), ("render-interruption-diagnosis", "")]
    _require(sorted(suffix_roles) == sorted(expected_roles), "Preserved completed scoring roles are not exact")
    _require(len(successes) == 39 and len(diagnosis) == 1
             and _pairs([b for b in successes if b not in diagnosis]) == _pairs(interruption["successful_worker_receipts"])
             and _pairs(scoring_artifacts) == _pairs(interruption["completed_scoring_artifacts"]),
             "Forensic successful-worker or scoring allowlist differs")
    last_binding = checkpoint["diagnosis_completion_event"]
    _require({k: last_binding[k] for k in ("path", "sha256")} == bindings[-1]
             and last_binding["canonical_sha256"] == events[-1]["sha256"], "Diagnosis completion proof changed")
    _require(checkpoint["completed_attempts"] == 41 and checkpoint["successful_attempts"] == 39
             and checkpoint["failed_attempts"] == 2, "Checkpoint attempt counts differ")
    elapsed = sum(e["elapsed_seconds"] for e in finishes.values())
    _require(math.isclose(elapsed, checkpoint["cumulative_seconds"], rel_tol=0, abs_tol=1e-6)
             and math.isclose(checkpoint["remaining_seconds"], 14400 - elapsed, rel_tol=0, abs_tol=1e-6),
             "Preserved cumulative budget differs")
    for identifier, attempt in journal._attempts().items():
        if identifier in starts:
            continue
        start, finish = attempt["start"], attempt["finished"]
        _require(start["unit_key"].startswith("render-recovery:"), "Unknown post-checkpoint worker")
        reservation = output / "attempts" / (identifier + ".reservation.json")
        _require(reservation.is_file() and read_json(reservation) == {"event_sha256": start["sha256"]},
                 "New reservation seal missing or changed")
        if finish is None:
            _require(identifier == os.environ.get("BALL_RETENTION_ATTEMPT_ID"), "Unfinished render recovery requires investigation")
        else:
            _require(finish["success"] is True, "A new render recovery failure requires investigation")
            completion = output / "attempts" / (identifier + ".completion.json")
            _require(completion.is_file() and read_json(completion) == {"event_sha256": finish["sha256"]},
                     "New completion seal missing or changed")
    return journal


def completed_bindings(root, context):
    journal = verify_history(root, context)
    start_keys = {e["attempt_id"]: e["unit_key"] for e in journal.events if e["kind"] == "started"}
    completed = {}
    for event in journal.events[len(context["checkpoint"]["journal_prefix"]["events"]):]:
        if event["kind"] != "finished":
            continue
        _require(event["success"] is True and event["worker_result"] is not None, "Unsuccessful render output cannot be reused")
        value = read_json(verify_binding(root, previous._root_binding(Path(root), context["output_root"], event["worker_result"])))
        _require(value["commit"] == context["commit"] and value["spec_sha256"] == context["spec_sha256"]
                 and start_keys[event["attempt_id"]] == "render-recovery:" + value["stage"] + ":" + value["key"],
                 "Render worker has wrong actual source/specification role")
        expected = _expected_artifacts(context, value["stage"], value["key"])
        _require(len(value["artifacts"]) == len(expected) and {b["path"] for b in value["artifacts"]} == expected,
                 "Unapproved or incomplete render artifact receipt")
        for b in value["artifacts"]:
            verify_binding(root, b)
            _require(completed.setdefault(b["path"], b["sha256"]) == b["sha256"], "Conflicting render receipts")
    return completed


def load_reused_observations(root, context, unit):
    return previous._load_reused_observations(root, context, unit, verify_history(root, context))


def load_reused_score(root, context, window_id):
    _require(window_id in {w["window_id"] for w in context["proposal"]["windows"]}, "Unknown preserved scoring window")
    verify_history(root, context)
    expected = next(iter(previous._expected_artifacts(context, "score", window_id)))
    matches = [b for b in context["interruption"]["completed_scoring_artifacts"] if b["path"] == expected]
    _require(len(matches) == 1, "Scoring window is not in the exact completed allowlist")
    verify_binding(root, matches[0])
    old = context["scoring_context"]
    _require(old["commit"] == SCORING_COMMIT and old["spec_sha256"] == SCORING_SPEC_SHA256,
             "Preserved scoring identity changed")
    return scoring.load_window_score(root, old, window_id)


def validate_preserved(root, context):
    """Read/hash exact old outputs; never rerank, rematch, aggregate or decode traces."""
    root, output = Path(root).resolve(), context["output_root"]
    inventory, receipt = context["inventory"], context["interruption"]
    _require(inventory["original_commit"] == ORIGINAL_COMMIT and inventory["original_spec_sha256"] == ORIGINAL_SPEC_SHA256
             and context["original_context"]["commit"] == ORIGINAL_COMMIT
             and context["original_context"]["spec_sha256"] == ORIGINAL_SPEC_SHA256
             and receipt["experiment_commit"] == SCORING_COMMIT and receipt["spec_sha256"] == SCORING_SPEC_SHA256,
             "Preserved selection/scoring provenance differs")
    entries = inventory["selections"]
    _require(len(entries) == 24 and len({e["unit"]["comparison_unit_id"] for e in entries}) == 24
             and sorted((e["unit"] for e in entries), key=lambda u: u["comparison_unit_id"])
             == sorted(context["proposal"]["new_selection_units"], key=lambda u: u["comparison_unit_id"])
             and sum(len(e["traces"]) for e in entries) == 600, "Exact 24-selection/600-trace allowlist is required")
    _require(_pairs(receipt["completed_selection_manifests"]) == _pairs([e["manifest"] for e in entries])
             and _pairs(receipt["completed_trace_bindings"]) == _pairs([b for e in entries for b in e["traces"]]),
             "Selection allowlist differs from forensic authority")
    journal = verify_history(root, context)
    expected = set()
    for entry in entries:
        previous._load_reused_observations(root, context, entry["unit"], journal)
        expected.add(entry["manifest"]["path"])
        expected.update(b["path"] for b in entry["traces"])
    actual = {p.relative_to(root).as_posix() for p in (output / "observations").rglob("*") if p.is_file()}
    _require(actual == expected and not any(p.is_file() for p in (output / ".pending_selection").rglob("*")),
             "Unbound or missing selection evidence")
    failed = inventory["failed_scoring"]
    _require(receipt["original_failed_scoring_preserved"] == failed, "Original failed scoring partial was changed")
    for b in (failed["partial"], failed["log"], receipt["failed_render_log"]):
        path = verify_binding(root, b)
        if "size_bytes" in b:
            _require(path.stat().st_size == b["size_bytes"], "Preserved partial size changed")
    score_bindings = receipt["completed_scoring_artifacts"]
    _require(len(score_bindings) == 8 and {b["path"] for b in score_bindings} == _score_paths(context),
             "Exact six windows and two completed score pools are required")
    for b in score_bindings:
        value = scoring._read_published(verify_binding(root, b))
        _require(value["experiment_spec_sha256"] == SCORING_SPEC_SHA256 and value["code_commit"] == SCORING_COMMIT,
                 "Completed score provenance changed")
    actual = {p.relative_to(root).as_posix() for p in (output / "evaluation").rglob("*") if p.is_file()}
    _require(actual == _score_paths(context) | {failed["partial"]["path"]}, "Unexpected or missing evaluation artifacts")
    for window in context["proposal"]["windows"]:
        load_reused_score(root, context, window["window_id"])
    partials = receipt["partial_review_files"]
    _pairs(partials)
    _require(len(partials) == 10, "The exact ten interrupted PNGs must be retained")
    parents = set()
    for b in partials:
        path = verify_binding(root, b)
        _require(path.suffix == ".png" and path.stat().st_size == b["size_bytes"], "Interrupted PNG bytes or size changed")
        relative = path.relative_to(output / "review/windows")
        _require(len(relative.parts) >= 2 and relative.parts[0].startswith(
                 ".pending_" + context["proposal"]["windows"][0]["window_id"] + "_"), "Interrupted PNG location changed")
        parents.add(output / "review/windows" / relative.parts[0])
    _require(len(parents) == 1 and {p.relative_to(root).as_posix() for p in next(iter(parents)).rglob("*") if p.is_file()}
             == {b["path"] for b in partials}, "Interrupted renderer directory contains unbound files")
    final_targets = {(output / "review/windows" / w["window_id"]).relative_to(root).as_posix()
                     for w in context["proposal"]["windows"]} | {(output / "review/manifest.json").relative_to(root).as_posix()}
    _require(set(receipt["absent_final_review_targets"]) == final_targets, "Historical unfinished review scope changed")
    for b in receipt["verified_bindings"]:
        if b["path"] not in CHANGED_SCORING_PATHS:
            verify_binding(root, b)
    return {"selection_units": 24, "trace_shards": 600, "scoring_artifacts": 8,
            "preserved_partial_pngs": 10, "selection_executed": False, "scoring_executed": False}


def _validate_published(root, context, completed):
    """A target published before resource completion is never adopted on resume."""
    from . import crop_retention_review as review
    review_root = context["output_root"] / "review"
    expected = {b["path"] for b in context["interruption"]["partial_review_files"]}
    for window in context["proposal"]["windows"]:
        name = window["window_id"]
        folder = review_root / "windows" / name
        if not folder.exists():
            continue
        path = folder / "manifest.json"
        _require(path.relative_to(root).as_posix() in completed, "Unreceipted review target cannot be adopted")
        prepared = review.prepare_window(root, context, name, observation_loader=load_reused_observations,
                                         score_loader=load_reused_score)
        value = review.validate_review_bundle(root, folder, prepared.header)
        expected.add(path.relative_to(root).as_posix())
        expected.update((folder / b["path"]).relative_to(root).as_posix() for b in value["assets"])
    final_path = review_root / "manifest.json"
    if final_path.exists():
        _require(final_path.relative_to(root).as_posix() in completed, "Unreceipted global review manifest")
        # Existing finalization is a strict read/compare when the target exists.
        review.finalize_review(root, context)
        expected.add(final_path.relative_to(root).as_posix())
    actual = {p.relative_to(root).as_posix() for p in review_root.rglob("*") if p.is_file()}
    _require(actual == expected, "Unexpected or incomplete review evidence requires investigation")


def load_context(root, manifest_path, *, require_clean=True):
    context = _metadata(root, manifest_path, require_clean)
    old = original.load_context(root, context["original_context"]["manifest_path"], require_clean=False,
                                verify_review_inputs=True, verify_scoring_inputs=True)
    old["commit"] = ORIGINAL_COMMIT
    context["original_context"], context["inputs"] = old, old["inputs"]
    context["scoring_context"].update(original_context=old, inputs=old["inputs"])
    p = context["proposal"]
    _require(len(p["windows"]) == 6 and len(p["saved_control_outputs"]) == 126
             and len(p["saved_report_references"]) == 630
             and len(p["higher_confidence_structural_equivalence"]) == 48, "Frozen comparison scope changed")
    context["recovery_provenance"] = {"original_selection_spec_sha256": ORIGINAL_SPEC_SHA256,
        "original_selection_commit": ORIGINAL_COMMIT,
        "preserved_inventory": context["scoring_context"]["manifest"]["preserved_inventory"],
        "original_evaluation_spec_sha256": SCORING_SPEC_SHA256, "original_evaluation_commit": SCORING_COMMIT,
        "scoring_manifest": context["manifest"]["scoring_manifest"],
        "interruption_receipt": context["manifest"]["interruption_receipt"],
        "resource_checkpoint": context["manifest"]["resource_checkpoint"]}
    validate_preserved(root, context)
    _validate_published(Path(root).resolve(), context, completed_bindings(root, context))
    return context


def _unchanged(context):
    root = context["root"]
    _require(original._clean_checkpoint(root) == context["commit"], "Render checkpoint changed during worker")
    _require(read_json(context["manifest_path"]) == context["manifest"], "Render manifest changed during worker")
    for field in ("scoring_manifest", "render_proposal", "authorization", "interruption_receipt", "resource_checkpoint",
                  "implementation_validation"):
        verify_binding(root, context["manifest"][field])
    _validate_implementation(root, context["manifest"])
    original._embargoes(root, context["proposal"])
    for window in context["proposal"]["windows"]:
        verify_binding(root, window["crop_candidates"])
    for control in context["proposal"]["saved_control_outputs"]:
        verify_binding(root, control["file"])
    validate_preserved(root, context)


def _worker(root, manifest_path, stage, key):
    _require(stage in ("verify", "preflight", "render", "review-final"), "Only rendering and verification are dispatchable")
    wait_for_supervisor()
    context = load_context(root, manifest_path)
    _expected_artifacts(context, stage, key)
    output, artifacts = context["output_root"], []
    if stage == "render":
        from .crop_retention_review import render_window
        render_window(root, context, key, output / "review/windows" / key,
                      observation_loader=load_reused_observations, score_loader=load_reused_score)
        artifacts.append(file_binding(root, output / "review/windows" / key / "manifest.json"))
    elif stage == "review-final":
        from .crop_retention_review import finalize_review
        completed = completed_bindings(root, context)
        _require(all(next(iter(_expected_artifacts(context, "render", w["window_id"]))) in completed
                     for w in context["proposal"]["windows"]), "All six rendered windows need successful resource receipts")
        finalize_review(root, context)
        artifacts.append(file_binding(root, output / "review/manifest.json"))
    _unchanged(context)
    result = {"stage": stage, "key": key, "spec_sha256": context["spec_sha256"],
              "commit": context["commit"], "artifacts": artifacts}
    target = safe_path(output, Path(os.environ["BALL_RETENTION_RESULT_PATH"]).relative_to(output).as_posix())
    original.persist_new(target, result)
    return result


def run_recovery(root, manifest_path, *, stage="verify", dry_run=False):
    _require(stage in PERMITTED_STAGES, "Render recovery permits verification and rendering only")
    root, manifest_path = Path(root).resolve(), Path(manifest_path).resolve()
    if dry_run:
        context = _metadata(root, manifest_path, False)
        return {"dry_run": True, "metadata_only": True, "saved_outputs_verified": False,
                "selection_executed": False, "scoring_executed": False, "execution_requires_clean_tested_commit": True,
                "saved_verification_requires_supervised_worker": True, "spec_sha256": context["spec_sha256"]}
    context = _metadata(root, manifest_path, True)
    def dispatch(action, key=""):
        command = [sys.executable, "-B", "-m", "src.ball_tracking.crop_retention_render_recovery", "--manifest",
                   str(manifest_path), "--repository-root", str(root), "--worker-stage", action, "--unit-key", key]
        return run_supervised(context["output_root"], "render-recovery:" + action + ":" + key, command,
                              context["proposal"]["resource_limits"], cwd=root, selection_unit=False, require_result=True)
    receipts = [dispatch("preflight", stage)]
    if stage == "render":
        for window in context["proposal"]["windows"]:
            receipts.append(dispatch("render", window["window_id"]))
        receipts.append(dispatch("review-final"))
    return {"stage": stage, "successful_workers": len(receipts), "commit": context["commit"],
            "selection_executed": False, "scoring_executed": False, "new_model_calls": 0, "training_executed": False,
            "output_root": str(context["output_root"])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--stage", choices=PERMITTED_STAGES, default="verify")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--worker-stage", choices=("preflight", "verify", "render", "review-final"), help=argparse.SUPPRESS)
    parser.add_argument("--unit-key", default="", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = args.repository_root.resolve()
    path = (root / args.manifest).resolve()
    value = (_worker(root, path, args.worker_stage, args.unit_key) if args.worker_stage
             else run_recovery(root, path, stage=args.stage, dry_run=args.dry_run))
    print(json.dumps(value, indent=2))


if __name__ == "__main__":
    main()
