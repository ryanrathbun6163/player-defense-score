"""Approved recovery of exact saved retention selections; never runs selection."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from . import crop_retention_experiment as original
from .crop_retention_resources import BudgetJournal, run_supervised, wait_for_supervisor
from .development_experiments import canonical_sha256, read_json, safe_path, sha256_file

ORIGINAL_COMMIT = "0a7f5bc69be948b8c4e2c630c84c4ccdefb5dc41"
ORIGINAL_SPEC_SHA256 = "e481d645e946f285c655d721563172c4cb8c2f124214840b8c8d8ae5cfb752fd"
ORIGINAL_MANIFEST_SHA256 = "f2b8834722ddf9f1ce4dcfdf1441a12cc0d52591b57bb66ca726c3aef2ca15ff"
RECOVERY_PROPOSAL_SHA256 = "c066bc43b204a09a05e2912589cbc173614cecbe563431ebbeed75c42db3de48"
APPROVAL_SHA256 = "29ba7f01ff0a2bd149d341d064673460f8be87bedd024442015a7a222a6090ae"
INTERRUPTION_SHA256 = "0f90a59c07dd2436ef8618ffd8d3637695b99ab3e56e08f879866d9d702e40df"
RECOVERY_ID = "rfdetr_medium_crop_candidate_retention_recovery_v0_1"
OUTPUT_ROOT = original.OUTPUT_ROOT
PERMITTED_STAGES = ["verify", "score", "render"]
MANIFEST_FIELDS = {"schema_version", "recovery_id", "original_manifest", "recovery_proposal",
                   "authorization", "preserved_inventory", "implementation_validation", "output_root",
                   "permitted_stages", "selected_method", "selected_operating_point", "quality_gate"}
INVENTORY_FIELDS = {"schema_version", "original_commit", "original_spec_sha256", "original_source_bindings",
                    "interruption_receipt", "selections", "journal_prefix", "failed_scoring"}
CHANGED_ORIGINAL_PATHS = {
    "src/ball_tracking/crop_retention_resources.py",
    "src/ball_tracking/crop_retention_evaluation.py",
    "src/ball_tracking/crop_retention_review.py",
    "tests/test_ball_crop_retention_resources.py",
}
_require = original._require
verify_binding = original.verify_binding
file_binding = original.file_binding


def _validate_implementation(root, manifest):
    binding = manifest["implementation_validation"]
    _require(isinstance(binding, dict), "Recovery implementation validation is missing")
    certificate = read_json(verify_binding(root, binding))
    flags = ("focused_tests_passed", "full_suite_passed", "resource_abort_and_resume_tests_passed",
             "independent_static_review_passed")
    _require(all(certificate.get(k) is True for k in flags), "Recovery validation is incomplete")
    _require(certificate["recovery_proposal_sha256"] == RECOVERY_PROPOSAL_SHA256
             and certificate["preserved_inventory_sha256"] == manifest["preserved_inventory"]["sha256"],
             "Recovery validation belongs to another approved scope or inventory")
    required = {p.relative_to(root).as_posix() for folder in ("src", "tests")
                for p in (root / folder).rglob("*.py")}
    required.add("requirements.txt")
    bindings = certificate["source_bindings"]
    _require(len({b["path"] for b in bindings}) == len(bindings)
             and required <= {b["path"] for b in bindings}, "Recovery validation omits dependencies or tests")
    for b in bindings + certificate["evidence_bindings"]:
        verify_binding(root, b)
    for name in required:
        original._git(root, "ls-files", "--error-unmatch", "--", name)


def _metadata(root, manifest_path, require_clean):
    root, path = Path(root).resolve(), Path(manifest_path).resolve()
    safe_path(root, path.relative_to(root).as_posix(), "configs/ball_tracking/crop_retention_experiments")
    commit = original._clean_checkpoint(root) if require_clean else original._git(root, "rev-parse", "HEAD")
    manifest = read_json(path)
    _require(set(manifest) == MANIFEST_FIELDS
             and manifest["schema_version"] == "ball_crop_candidate_retention_recovery/v0.1"
             and manifest["recovery_id"] == RECOVERY_ID and manifest["output_root"] == OUTPUT_ROOT
             and manifest["permitted_stages"] == PERMITTED_STAGES,
             "Unsupported recovery manifest or permitted stage")
    _require(all(manifest[k] is None for k in ("selected_method", "selected_operating_point", "quality_gate")),
             "Recovery does not select a method or quality gate")
    _require(manifest["original_manifest"]["sha256"] == ORIGINAL_MANIFEST_SHA256
             and manifest["original_manifest"]["content_sha256"] == ORIGINAL_SPEC_SHA256
             and manifest["recovery_proposal"]["sha256"] == RECOVERY_PROPOSAL_SHA256
             and manifest["authorization"]["sha256"] == APPROVAL_SHA256,
             "Recovery is not bound to the exact approved authorities")
    verify_binding(root, manifest["recovery_proposal"])
    approval = read_json(verify_binding(root, manifest["authorization"]))
    _require(approval["schema_version"] == "ball_crop_candidate_retention_recovery_approval/v0.1"
             and approval["proposal"] == manifest["recovery_proposal"] and approval["approved_by"] == "ryan"
             and approval["implementation_authorized"] is True and approval["execution_authorized"] is True
             and approval["training_authorized"] is False and approval["git_mutations_authorized"] is False,
             "Missing exact recovery authorization")
    if require_clean:
        _validate_implementation(root, manifest)
        _require(subprocess.run(["git", "merge-base", "--is-ancestor", ORIGINAL_COMMIT, "HEAD"], cwd=root).returncode == 0,
                 "Recovery execution is not descended from the preserved selection checkpoint")
        for b in (manifest["recovery_proposal"], manifest["authorization"]):
            original._git(root, "ls-files", "--error-unmatch", "--", b["path"])
        original._git(root, "ls-files", "--error-unmatch", "--", path.relative_to(root).as_posix())
    old_path = verify_binding(root, manifest["original_manifest"])
    old = original._metadata(root, old_path, False)
    _require(old["spec_sha256"] == ORIGINAL_SPEC_SHA256, "Original canonical specification changed")
    old["commit"] = ORIGINAL_COMMIT
    inventory = read_json(verify_binding(root, manifest["preserved_inventory"]))
    _require(set(inventory) == INVENTORY_FIELDS
             and inventory["schema_version"] == "ball_crop_candidate_retention_recovery_inventory/v0.1"
             and inventory["original_commit"] == ORIGINAL_COMMIT
             and inventory["original_spec_sha256"] == ORIGINAL_SPEC_SHA256
             and inventory["interruption_receipt"]["sha256"] == INTERRUPTION_SHA256,
             "Preserved recovery inventory has changed scope")
    certificate = read_json(verify_binding(root, old["manifest"]["implementation_validation"]))
    _require(inventory["original_source_bindings"] == certificate["source_bindings"],
             "Original implementation/source inventory changed")
    # These are the four explicitly reviewed changes. Everything else from the
    # original certificate, including selection and its dependencies, stays exact.
    for b in inventory["original_source_bindings"]:
        if b["path"] not in CHANGED_ORIGINAL_PATHS:
            verify_binding(root, b)
    return {"root": root, "manifest_path": path, "manifest": manifest, "approval": approval,
            "inventory": inventory, "original_context": old, "proposal": old["proposal"],
            "commit": commit, "spec_sha256": canonical_sha256(manifest), "output_root": root / OUTPUT_ROOT}


def _root_binding(root, output, binding):
    return {"path": safe_path(output, binding["path"]).relative_to(root).as_posix(), "sha256": binding["sha256"]}


def _expected_artifacts(context, stage, key):
    windows = {w["window_id"] for w in context["proposal"]["windows"]}
    prefix = context["output_root"].relative_to(context["root"]).as_posix()
    if stage in ("verify", "preflight"):
        _require(key in ("", *PERMITTED_STAGES), "Unknown recovery verification scope")
        return set()
    if stage == "score":
        _require(key in windows, "Unknown recovery scoring window")
        return {f"{prefix}/evaluation/windows/{key}.json"}
    if stage == "score-final":
        _require(key == "", "Unknown recovery scoring finalization key")
        return {f"{prefix}/evaluation/{purpose}.json" for purpose in context["proposal"]["pool_separation"]}
    if stage == "render":
        _require(key in windows, "Unknown recovery rendering window")
        return {f"{prefix}/review/windows/{key}/manifest.json"}
    if stage == "review-final":
        _require(key == "", "Unknown recovery review finalization key")
        return {f"{prefix}/review/manifest.json"}
    if stage == "completion-audit":
        # Receipt role for the separately reviewed independent helper only.
        # Neither the CLI nor _worker dispatches this role.
        _require(key == "", "Unknown independent completion-audit key")
        return {f"{prefix}/audit/independent_recovery_audit.json"}
    raise ValueError("Selection and unknown stages are forbidden during recovery")


def verify_history(root, context):
    """Verify the exact old prefix and role-bound new receipts without rewriting either."""
    root, output = Path(root).resolve(), context["output_root"]
    inventory, prefix = context["inventory"], context["inventory"]["journal_prefix"]
    journal = BudgetJournal(output, context["proposal"]["resource_limits"])
    bindings = prefix["events"]
    _require(bindings and len(journal.events) >= len(bindings), "Missing preserved resource history")
    for index, binding in enumerate(bindings):
        expected = output / "resource_events" / f"{index:08d}.json"
        _require(binding["path"] == expected.relative_to(root).as_posix(), "Non-contiguous preserved event inventory")
        verify_binding(root, binding)
    _require(journal.events[len(bindings)-1]["sha256"] == prefix["chain_tip_sha256"],
             "Preserved resource chain tip changed")
    old_events = journal.events[:len(bindings)]
    starts = {e["attempt_id"]: e for e in old_events if e["kind"] == "started"}
    finishes = {e["attempt_id"]: e for e in old_events if e["kind"] == "finished"}
    rows = prefix["attempts"]
    _require(len(rows) == len(starts) and len({r["attempt_id"] for r in rows}) == len(rows)
             and {r["attempt_id"] for r in rows} == set(starts) == set(finishes),
             "Preserved attempts are missing, additional or unfinished")
    selected = {r["attempt_id"]: r for r in inventory["selections"]}
    failed = inventory["failed_scoring"]
    for row in rows:
        identifier, role = row["attempt_id"], row["role"]
        start, finish = starts[identifier], finishes[identifier]
        _require(role in {"selection", "preflight", "diagnosis", "preparation", "failed_score"},
                 "Unknown preserved attempt role")
        for field, event in (("reservation", start), ("completion", finish)):
            expected = output / "attempts" / (identifier + (".reservation.json" if field == "reservation" else ".completion.json"))
            _require(row[field]["path"] == expected.relative_to(root).as_posix(), "Preserved attempt seal path changed")
            _require(read_json(verify_binding(root, row[field])) == {"event_sha256": event["sha256"]},
                     "Preserved attempt seal changed")
        if role == "failed_score":
            _require(identifier == failed["attempt_id"] and finish["success"] is False
                     and finish["sha256"] == failed["completion_event_sha256"]
                     and row["worker_result"] is None and finish["worker_result"] is None,
                     "Known scoring failure was changed or adopted")
            if "log_path" in finish:
                _require(failed["log"]["path"] == safe_path(output, finish["log_path"]).relative_to(root).as_posix(),
                         "Failed scoring log differs from its completion event")
            continue
        _require(finish["success"] is True and row["worker_result"] is not None
                 and finish["worker_result"] is not None, "Preserved output lacks successful worker completion")
        _require(row["worker_result"] == _root_binding(root, output, finish["worker_result"]),
                 "Preserved worker-result binding differs from its completion")
        result = read_json(verify_binding(root, row["worker_result"]))
        _require(result["commit"] == ORIGINAL_COMMIT and result["spec_sha256"] == ORIGINAL_SPEC_SHA256,
                 "Preserved worker has wrong original source/specification role")
        if role == "selection":
            entry = selected.get(identifier)
            _require(entry is not None and result["stage"] == "select"
                     and result["key"] == entry["unit"]["comparison_unit_id"]
                     and start["unit_key"] == "select:" + result["key"]
                     and result["artifacts"] == [entry["manifest"]]
                     and row["worker_result"] == entry["worker_result"], "Unallowlisted original selection receipt")
        else:
            _require(result["stage"] in ({"preflight"} if role == "preflight" else {role, "verify"}),
                     "Preserved non-selection worker role differs")
            for b in result["artifacts"]:
                relative = safe_path(root, b["path"]).relative_to(output).as_posix()
                _require(relative.split("/")[0] not in ("observations", "evaluation", "review"),
                         "A diagnostic receipt cannot authorize a scientific output")
        for b in result["artifacts"]:
            verify_binding(root, b)
    _require(sum(r["role"] == "failed_score" for r in rows) == 1
             and {r["attempt_id"] for r in rows if r["role"] == "selection"} == set(selected),
             "Preserved selection/failure role inventory changed")
    # The only unfinished suffix may be this supervised recovery worker itself.
    for identifier, attempt in journal._attempts().items():
        if identifier in starts:
            continue
        start, finish = attempt["start"], attempt["finished"]
        _require(start["unit_key"].startswith("recovery:"), "Unknown post-prefix worker")
        reservation = output / "attempts" / (identifier + ".reservation.json")
        _require(reservation.is_file() and read_json(reservation) == {"event_sha256": start["sha256"]},
                 "Recovery reservation seal is missing or changed")
        if finish is None:
            _require(identifier == os.environ.get("BALL_RETENTION_ATTEMPT_ID"),
                     "Unfinished recovery history requires investigation")
        else:
            _require(finish["success"] is True, "A subsequent recovery failure requires investigation")
            completion = output / "attempts" / (identifier + ".completion.json")
            _require(completion.is_file() and read_json(completion) == {"event_sha256": finish["sha256"]},
                     "Recovery completion seal is missing or changed")
    return journal


def completed_bindings(root, context):
    """Accept only receipted new score/review artifacts under this recovery identity."""
    root, output = Path(root).resolve(), context["output_root"]
    journal = verify_history(root, context)
    result = {}
    start_keys = {e["attempt_id"]: e["unit_key"] for e in journal.events if e["kind"] == "started"}
    for event in journal.events[len(context["inventory"]["journal_prefix"]["events"]):]:
        if event["kind"] != "finished":
            continue
        _require(event["success"] is True and event["worker_result"] is not None,
                 "New output lacks successful resource completion")
        value = read_json(verify_binding(root, _root_binding(root, output, event["worker_result"])))
        _require(value["spec_sha256"] == context["spec_sha256"] and value["commit"] == context["commit"]
                 and start_keys[event["attempt_id"]] == "recovery:" + value["stage"] + ":" + value["key"],
                 "Recovery worker has incorrect source/specification/stage provenance")
        expected = _expected_artifacts(context, value["stage"], value["key"])
        _require(len(value["artifacts"]) == len(expected) and {b["path"] for b in value["artifacts"]} == expected,
                 "Recovery receipt binds unknown or incomplete artifacts")
        for b in value["artifacts"]:
            verify_binding(root, b)
            _require(result.setdefault(b["path"], b["sha256"]) == b["sha256"], "Conflicting recovery receipts")
    return result


def load_reused_observations(root, context, unit):
    """Load one explicitly allowlisted old selection with its actual old provenance."""
    return _load_reused_observations(root, context, unit, verify_history(root, context))


def _load_reused_observations(root, context, unit, journal):
    root = Path(root).resolve()
    entries = [r for r in context["inventory"]["selections"] if r["unit"] == unit]
    _require(len(entries) == 1, "Selection is not in the exact preserved allowlist")
    entry = entries[0]
    finished = [e for e in journal.events[:len(context["inventory"]["journal_prefix"]["events"])]
                if e["kind"] == "finished" and e["attempt_id"] == entry["attempt_id"]]
    _require(len(finished) == 1 and finished[0]["success"] is True, "Original selection was not completed")
    event_path = verify_binding(root, entry["completion"])
    _require(read_json(event_path) == finished[0], "Selection completion event differs from preserved history")
    expected = original.unit_directory(context["original_context"], unit) / "manifest.json"
    _require(entry["manifest"]["path"] == expected.relative_to(root).as_posix(), "Original selection path differs")
    value = read_json(verify_binding(root, entry["manifest"]))
    _require(value["resource_attempt_id"] == entry["attempt_id"]
             and value["observations_content_sha256"] == entry["observations_content_sha256"]
             and value["input_crop_file"] == entry["input_crop_file"]
             and value["crop_content_sha256"] == entry["crop_content_sha256"]
             and value["observations"]["input_candidate_content_sha256"] == entry["input_candidate_content_sha256"],
             "Original selection content/input/attempt binding differs")
    traces = [{"frame_index": f["frame_index"], **f["trace_binding"]} for f in value["observations"]["frames"]]
    _require(traces == entry["traces"] and len(traces) == 25, "Original trace inventory changed")
    # All completion proofs were verified above. Reuse the strict existing
    # structural validator with the explicitly bound OLD identity, not a relaxed
    # ordinary loader or fabricated new commit. It hashes but never ranks/decodes.
    return original._validate_new_observations(root, context["original_context"], unit, require_completion=False)


def validate_preserved(root, context):
    """Verify all 24 old selections, 600 traces, exact failed partial and full history."""
    root = Path(root).resolve()
    inventory, proposal = context["inventory"], context["proposal"]
    _require(inventory["original_commit"] == ORIGINAL_COMMIT
             and inventory["original_spec_sha256"] == ORIGINAL_SPEC_SHA256
             and context["original_context"]["commit"] == ORIGINAL_COMMIT
             and context["original_context"]["spec_sha256"] == ORIGINAL_SPEC_SHA256,
             "Preserved source/specification roles differ")
    entries = inventory["selections"]
    _require(len(entries) == 24 and len({r["unit"]["comparison_unit_id"] for r in entries}) == 24
             and sorted((r["unit"] for r in entries), key=lambda x: x["comparison_unit_id"])
             == sorted(proposal["new_selection_units"], key=lambda x: x["comparison_unit_id"])
             and sum(len(r["traces"]) for r in entries) == 600,
             "Recovery requires the exact 24 selections and 600 traces")
    _require(len(inventory["journal_prefix"]["attempts"]) >= 28, "Diagnosis history is missing")
    receipt = read_json(verify_binding(root, inventory["interruption_receipt"]))
    def pairs(rows):
        result = {(b["path"], b["sha256"]) for b in rows}
        _require(len(result) == len(rows), "Duplicate preserved evidence binding")
        return result
    _require(receipt["experiment_commit"] == ORIGINAL_COMMIT
             and receipt["original_spec_sha256"] == ORIGINAL_SPEC_SHA256
             and pairs(receipt["completed_selection_manifests"]) == pairs([e["manifest"] for e in entries])
             and pairs(receipt["completed_trace_bindings"]) == pairs([b for e in entries for b in e["traces"]]),
             "Selection allowlist differs from the bound interruption evidence")
    previous_workers = [r["worker_result"] for r in inventory["journal_prefix"]["attempts"]
                        if r["role"] in ("selection", "preflight")]
    _require(len(previous_workers) == 26
             and pairs(receipt["successful_worker_receipts"]) == pairs(previous_workers),
             "Original successful worker scope differs from interruption evidence")
    failed = inventory["failed_scoring"]
    event = receipt["failed_completion_event"]
    _require(failed["attempt_id"] == event["attempt_id"]
             and failed["completion_event_sha256"] == event["sha256"]
             and event["success"] is False and event["worker_result"] is None
             and failed["partial"] == {"path": receipt["partial_scoring_file"]["path"],
                                       "sha256": receipt["partial_scoring_file"]["sha256"],
                                       "size_bytes": receipt["partial_scoring_file"]["bytes"]}
             and failed["log"] == receipt["failed_worker_log"], "Known failure differs from interruption evidence")
    partial = verify_binding(root, failed["partial"])
    _require(partial.stat().st_size == failed["partial"]["size_bytes"], "Failed partial size changed")
    _require(partial.parent == context["output_root"] / "evaluation/windows"
             and ".json.incomplete-" in partial.name, "Known partial is outside its original scoring location")
    verify_binding(root, failed["log"])
    journal = verify_history(root, context)
    _require(event in journal.events[:len(inventory["journal_prefix"]["events"])] ,
             "Interruption failure is not in the preserved resource prefix")
    expected = set()
    for entry in entries:
        _load_reused_observations(root, context, entry["unit"], journal)
        expected.add(entry["manifest"]["path"])
        expected.update(b["path"] for b in entry["traces"])
    actual = {p.relative_to(root).as_posix() for p in (context["output_root"] / "observations").rglob("*") if p.is_file()}
    _require(actual == expected, "Additional, missing or unbound original selection files")
    _require(not any(p.is_file() for p in (context["output_root"] / ".pending_selection").rglob("*")),
             "Unbound pending selection evidence requires investigation")
    return {"selection_units": 24, "trace_shards": 600, "selection_executed": False}


def _validate_published(root, context, completed):
    """A final filename alone never authorizes recovery reuse."""
    from . import crop_retention_evaluation as evaluation
    from . import crop_retention_review as review
    output = context["output_root"]
    partial = context["inventory"]["failed_scoring"]["partial"]["path"]
    expected_scores = set().union(*(_expected_artifacts(context, "score", w["window_id"])
                                   for w in context["proposal"]["windows"]))
    expected_scores |= _expected_artifacts(context, "score-final", "")
    for path in (output / "evaluation").rglob("*"):
        if not path.is_file():
            continue
        name = path.relative_to(root).as_posix()
        if name == partial:
            continue
        _require(name in expected_scores and name in completed, "Unreceipted or unexpected published scoring target")
        value = evaluation._read_published(path)
        _require(value["experiment_spec_sha256"] == context["spec_sha256"]
                 and value["code_commit"] == context["commit"], "Wrong recovered score provenance")
    for window in context["proposal"]["windows"]:
        name = window["window_id"]
        path = output / "evaluation/windows" / (name + ".json")
        if path.exists():
            evaluation.load_window_score(root, context, name)
    review_root = output / "review"
    if review_root.exists():
        expected = set()
        final_path = review_root / "manifest.json"
        for window in context["proposal"]["windows"]:
            folder = review_root / "windows" / window["window_id"]
            if not folder.exists():
                continue
            path = folder / "manifest.json"
            _require(path.relative_to(root).as_posix() in completed, "Unreceipted review target cannot be adopted")
            prepared = review.prepare_window(root, context, window["window_id"], observation_loader=load_reused_observations)
            value = review.validate_review_bundle(root, folder, prepared.header)
            expected.add(path.relative_to(review_root).as_posix())
            expected.update((folder / b["path"]).relative_to(review_root).as_posix() for b in value["assets"])
        if final_path.exists():
            _require(final_path.relative_to(root).as_posix() in completed, "Unreceipted final review manifest")
            expected.add("manifest.json")
        actual = {p.relative_to(review_root).as_posix() for p in review_root.rglob("*") if p.is_file()}
        _require(actual == expected, "Unexpected or incomplete review assets require investigation")


def load_context(root, manifest_path, *, require_clean=True, verify_review_inputs=False, verify_scoring_inputs=False):
    context = _metadata(root, manifest_path, require_clean)
    old = original.load_context(root, context["original_context"]["manifest_path"], require_clean=False,
                                verify_review_inputs=verify_review_inputs, verify_scoring_inputs=verify_scoring_inputs)
    old["commit"] = ORIGINAL_COMMIT
    context["original_context"], context["inputs"] = old, old["inputs"]
    p = context["proposal"]
    _require(len(p["windows"]) == 6 and len(p["saved_control_outputs"]) == 126
             and len(p["saved_report_references"]) == 630
             and len(p["higher_confidence_structural_equivalence"]) == 48, "Frozen comparison scope changed")
    context["recovery_provenance"] = {"original_selection_spec_sha256": ORIGINAL_SPEC_SHA256,
                                      "original_selection_commit": ORIGINAL_COMMIT,
                                      "preserved_inventory": context["manifest"]["preserved_inventory"]}
    validate_preserved(root, context)
    _validate_published(Path(root).resolve(), context, completed_bindings(root, context))
    return context


def _unchanged(context):
    root = context["root"]
    _require(original._clean_checkpoint(root) == context["commit"], "Recovery checkpoint changed during worker")
    _require(read_json(context["manifest_path"]) == context["manifest"], "Recovery manifest changed during worker")
    for field in ("original_manifest", "recovery_proposal", "authorization", "preserved_inventory", "implementation_validation"):
        verify_binding(root, context["manifest"][field])
    _validate_implementation(root, context["manifest"])
    original._embargoes(root, context["proposal"])
    for w in context["proposal"]["windows"]:
        verify_binding(root, w["crop_candidates"])
    for r in context["proposal"]["saved_control_outputs"]:
        verify_binding(root, r["file"])
    validate_preserved(root, context)


def _worker(root, manifest_path, stage, key):
    _require(stage in ("verify", "preflight", "score", "score-final", "render", "review-final"),
             "Recovery cannot dispatch selection")
    wait_for_supervisor()
    context = load_context(root, manifest_path, verify_scoring_inputs=True,
                           verify_review_inputs=stage in ("verify", "render", "review-final") or key in ("verify", "render"))
    _expected_artifacts(context, stage, key)
    output, artifacts = context["output_root"], []
    if stage == "score":
        from .crop_retention_evaluation import score_window
        score_window(root, context, key, output / "evaluation/windows", observation_loader=load_reused_observations)
        artifacts.append(file_binding(root, output / "evaluation/windows" / (key + ".json")))
    elif stage == "score-final":
        from .crop_retention_evaluation import finalize
        expected = sorted(_expected_artifacts(context, stage, key))
        completed = completed_bindings(root, context)
        if not all(name in completed for name in expected):
            _require(not any((Path(root) / name).exists() for name in expected), "Partially published score pools require investigation")
            windows = [output / "evaluation/windows" / (w["window_id"] + ".json") for w in context["proposal"]["windows"]]
            _require(all(p.relative_to(Path(root)).as_posix() in completed for p in windows), "Scoring windows are not all receipted")
            finalize(root, context, windows, output / "evaluation")
        artifacts.extend(file_binding(root, Path(root) / name) for name in expected)
    elif stage == "render":
        from .crop_retention_review import render_window
        _require(all(name in completed_bindings(root, context) for name in _expected_artifacts(context, "score-final", "")),
                 "Rendering requires completed separated score pools")
        render_window(root, context, key, output / "review/windows" / key, observation_loader=load_reused_observations)
        artifacts.append(file_binding(root, output / "review/windows" / key / "manifest.json"))
    elif stage == "review-final":
        from .crop_retention_review import finalize_review
        completed = completed_bindings(root, context)
        _require(all(next(iter(_expected_artifacts(context, "render", w["window_id"]))) in completed
                     for w in context["proposal"]["windows"]), "Review windows are not all receipted")
        finalize_review(root, context)
        artifacts.append(file_binding(root, output / "review/manifest.json"))
    _unchanged(context)
    result = {"stage": stage, "key": key, "spec_sha256": context["spec_sha256"],
              "commit": context["commit"], "artifacts": artifacts}
    target = safe_path(output, Path(os.environ["BALL_RETENTION_RESULT_PATH"]).relative_to(output).as_posix())
    original.persist_new(target, result)
    return result


def run_recovery(root, manifest_path, *, stage="verify", dry_run=False):
    _require(stage in PERMITTED_STAGES, "Recovery permits verification, scoring and rendering only")
    root, manifest_path = Path(root).resolve(), Path(manifest_path).resolve()
    if dry_run:
        context = _metadata(root, manifest_path, False)
        return {"dry_run": True, "metadata_only": True, "saved_outputs_verified": False,
                "selection_executed": False, "execution_requires_clean_tested_commit": True,
                "saved_verification_requires_supervised_worker": True, "spec_sha256": context["spec_sha256"]}
    # Parent does only authority/source validation. All saved-output inspection
    # and continuation runs in supervised workers, consuming the existing budget.
    context = _metadata(root, manifest_path, True)
    def dispatch(action, key=""):
        command = [sys.executable, "-B", "-m", "src.ball_tracking.crop_retention_recovery", "--manifest",
                   str(manifest_path), "--repository-root", str(root), "--worker-stage", action, "--unit-key", key]
        return run_supervised(context["output_root"], "recovery:" + action + ":" + key, command,
                              context["proposal"]["resource_limits"], cwd=root, selection_unit=False, require_result=True)
    receipts = [dispatch("preflight", stage)]
    if stage in ("score", "render"):
        for window in context["proposal"]["windows"]:
            receipts.append(dispatch(stage, window["window_id"]))
        receipts.append(dispatch("score-final" if stage == "score" else "review-final"))
    return {"stage": stage, "successful_workers": len(receipts), "commit": context["commit"],
            "selection_executed": False, "new_model_calls": 0, "training_executed": False,
            "output_root": str(context["output_root"])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--stage", choices=PERMITTED_STAGES, default="verify")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--worker-stage", choices=("preflight", "verify", "score", "score-final", "render", "review-final"), help=argparse.SUPPRESS)
    parser.add_argument("--unit-key", default="", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = args.repository_root.resolve()
    path = (root / args.manifest).resolve()
    value = (_worker(root, path, args.worker_stage, args.unit_key) if args.worker_stage
             else run_recovery(root, path, stage=args.stage, dry_run=args.dry_run))
    print(json.dumps(value, indent=2))


if __name__ == "__main__":
    main()
