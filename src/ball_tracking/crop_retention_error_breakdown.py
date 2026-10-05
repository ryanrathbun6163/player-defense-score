"""One supervised reading of the saved error breakdown in two completed pools."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import uuid

from . import crop_retention_resources as resources
from . import crop_retention_experiment as original
from .crop_retention_resources import BudgetJournal, wait_for_supervisor
from .development_experiments import canonical_sha256, read_json, safe_path

ID = "rfdetr_medium_crop_candidate_retention_error_breakdown_v0_1"
MANIFEST_PATH = "configs/ball_tracking/crop_retention_experiments/" + ID + ".json"
APPROVAL_PATH = "configs/ball_tracking/reviews/" + ID.replace("_v0_1", "_approval_v0_1") + ".json"
OUTPUT_ROOT = original.OUTPUT_ROOT
OUTPUT_DIR = "audit/post_review_error_breakdown_v0_1"
OUTPUTS = [OUTPUT_DIR + "/" + name for name in ("breakdown.json", "summary.md", "provenance.json")]
UNIT_KEY = "post-review-error-breakdown:summary:"
PREFIX_COUNT = 3002
PREFIX_ATTEMPTS = 57
PREFIX_TIP = "6c0924cc29f4bdf6b7d6e9311b3fc8205baf8ad0ab251a31ae2bb056a45e1f6c"
USED_SECONDS = 3260.243000000002
MAX_UNIT_SECONDS = 300
MAX_SUMMARY_BYTES = 65536
PUBLICATION_COMMIT = "a89cd40838b066c1d2fe3cb1f257dda10e80a3bb"
PREVIOUS_COMMIT = "e71a4d2165623208d624c4839e9321bd9bf779ba"
PROPOSAL_PATH = "docs/ball_crop_candidate_retention_error_breakdown_proposal.md"
PROPOSAL_SHA = "f8525927fa5589b7c5a70aef6fee9bcc813365e267503eaa4f6610438802deee"
COMPLETION_PATH = ("data/outputs/ball_tracking/crop_candidate_retention_interpretation_implementation/"
                   "a89cd40838b0_2026-10-02/interpretation_completion_checkpoint.json")
COMPLETION_SHA = "c6e55a921c44bd6dfa29b291dd753fb80b72637ecc86ba035802210f5bb80bf5"
PUBLICATION_CHECKPOINT = {
    "path": "data/outputs/ball_tracking/crop_candidate_retention_publication_recovery_implementation/cd51bfc1336b_2026-10-02/recovery_completion_checkpoint.json",
    "sha256": "03ddbd6151b3827afaf98070a5c8ed745f9ccd05b582b84d0c23ab8f0417e7d0",
}
WINDOW_AUTHORITY_PATH = "configs/ball_tracking/proposals/rfdetr_medium_crop_candidate_retention_v0_1.json"
WINDOW_AUTHORITY_SHA = "7640784e2a64e81a2064ebb40cd4d1c77366076e5e78a2c19f8f5fc28e29fe1b"
HUMAN_REVIEW_PATH = "configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_visual_review_record_v0_1.json"
HUMAN_REVIEW_SHA = "9a3089a14747dce7b95670838dd116b2ddaf6cd426837f93435ff6ad6706d46b"
APPROVAL_SHA = "f0eb74cde6077a5741c46ebe1aa1f8633ed2ac031f8b3a5f493d417ca9a2a0cf"
FROZEN_HISTORY_SHA = "b765b13e8e76daa9d6108d5a82b5d3e589c93b76415fc97a75054ba8fb0238cf"
FROZEN_HISTORY_PATH = ("data/outputs/ball_tracking/crop_candidate_retention_error_breakdown_implementation/"
                       "e71a4d216562_2026-10-02/frozen_history.json")
SCIENTIFIC_INPUTS = {
    "representative_pool": {"path": OUTPUT_ROOT + "/evaluation/representative_evaluation.json",
              "sha256": "82ce2d01b9f61a5d66b358f5aa42654db2413f7a9d5e45867ddffc9fb1e5acfb", "size_bytes": 134447507},
    "challenge_pool": {"path": OUTPUT_ROOT + "/evaluation/challenge_evaluation.json",
              "sha256": "01afe5ad0391336c5619e93dea585f79a665dccd02d9201c3dbe9349d1e60f60", "size_bytes": 126628338},
    "audit": {"path": OUTPUT_ROOT + "/audit/independent_publication_recovery_audit.json",
              "sha256": "a1c944c3e1a5184ff08986adacbb2e623d515a67b33a67a55075dcc3f5fc5da2", "size_bytes": 1770176},
}
KNOWN_FAILURES = {"158f51be5ab34cdface57f4e0036b7d2", "e1ba648def3f4e1f887332e850396e4c",
                  "e3ea5536e59d4cdc8fea72d45bc53241"}
HOLDOUTS = [["possession_001", 300, 324], ["possession_002", 200, 224], ["possession_003", 250, 274]]
WINDOWS = [{"window_id": f"possession_{p:03d}_frames_{first:04d}_{last:04d}_{purpose}_development_v0_2",
            "possession_id": f"possession_{p:03d}", "purpose": purpose,
            "start_frame_index": first, "end_frame_index": last}
           for p, first, last, purpose in ((1, 50, 74, "representative_evaluation"), (1, 200, 224, "challenge_evaluation"),
               (2, 250, 274, "representative_evaluation"), (2, 25, 49, "challenge_evaluation"),
               (3, 300, 324, "representative_evaluation"), (3, 150, 174, "challenge_evaluation"))]
PREDECESSOR_RECEIPTS = {
    "score-final": {"path": OUTPUT_ROOT + "/attempts/98a92bcb9d384f1c9b684d92403c7bc6.result.json",
                    "sha256": "a03e3ac99a3cbaad8f0fe48d206f75663fb8fc00a601b60d2cdc7b72163b0873"},
    "completion-audit": {"path": OUTPUT_ROOT + "/attempts/b5b46e5fac4f442ab960984758cfd469.result.json",
                         "sha256": "e45897d7545aa6b2bce15d68af9d8b54077cb32ab88e98bdc67c9103549da87e"},
    "interpret": {"path": OUTPUT_ROOT + "/attempts/7bd613d71cef48d38c15a72e9647fc10.result.json",
                  "sha256": "07d810dcfe98bf2937d2e6bfdfbb1985cdbd05b974c3d974f6919bcb7a19fa62"},
}
_require = original._require
verify_binding = original.verify_binding
file_binding = original.file_binding


def _pair(binding):
    return {key: binding[key] for key in ("path", "sha256")}


def _absent(path):
    _require(not os.path.lexists(path), "Create-only error_breakdown destination already exists: " + str(path))


def _unique_bindings(rows):
    _require(isinstance(rows, list) and len({row["path"] for row in rows}) == len(rows),
             "Repeated or invalid bindings")
    for row in rows:
        _require(isinstance(row["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]),
                 "Invalid bound digest")


def _json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _write_new(path, payload):
    with Path(path).open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _stat_metadata(path):
    info = path.lstat()
    _require(stat.S_ISREG(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
             "Preserved evidence is not a regular file")
    return {"size_bytes": info.st_size, "mtime_ns": info.st_mtime_ns,
            "device": info.st_dev, "inode": info.st_ino}


AUTHORITY_FIELDS = ("proposal", "authorization", "completion_checkpoint", "human_review_record", "frozen_history", "window_authority")
MANIFEST_FIELDS = {"schema_version", "error_breakdown_id", *AUTHORITY_FIELDS, "scientific_inputs",
                   "implementation_validation", "output_root", "permitted_stages", "unit_key",
                   "maximum_unit_seconds", "maximum_summary_bytes", "selected_method",
                   "selected_operating_point", "quality_gate"}


def _validate_implementation(root, manifest):
    binding = manifest["implementation_validation"]
    _require(isinstance(binding, dict), "ErrorBreakdown implementation validation is missing")
    certificate = read_json(verify_binding(root, binding))
    _require(certificate["schema_version"] == "ball_crop_candidate_retention_error_breakdown_implementation_validation/v0.1",
             "Unsupported error_breakdown certificate")
    for flag in ("focused_tests_passed", "full_suite_passed", "independent_static_review_passed", "integrity_tests_passed"):
        _require(certificate.get(flag) is True, "ErrorBreakdown validation is incomplete")
    _require(certificate["authority_sha256"] == {key: manifest[key]["sha256"] for key in AUTHORITY_FIELDS},
             "Validation belongs to another exact authority")
    required = {p.relative_to(root).as_posix() for folder in ("src", "tests") for p in (root / folder).rglob("*.py")}
    required.add("requirements.txt")
    bindings = certificate["source_bindings"]
    _unique_bindings(bindings)
    _require({b["path"] for b in bindings} == required, "Validation omits or adds source dependencies")
    for row in bindings:
        verify_binding(root, row)
        original._git(root, "ls-files", "--error-unmatch", "--", row["path"])
    evidence = certificate["evidence_bindings"]
    _unique_bindings(evidence)
    certificate_parent = Path(binding["path"]).parent.as_posix()
    _require(certificate_parent.startswith("data/outputs/ball_tracking/crop_candidate_retention_error_breakdown_implementation/"),
             "Unexpected error_breakdown validation directory")
    for row in evidence:
        safe_path(root, row["path"], certificate_parent)
        verify_binding(root, row)
    return certificate


def _protected_metadata(root, checkpoint):
    _require(checkpoint["sealed_holdouts_metadata_only"] == HOLDOUTS, "Sealed holdout scope changed")
    paths = checkpoint["preserved_absent_paths"]
    _require(len(paths) == len(set(paths)), "Repeated protected path")
    _require(sum(p.startswith("data/outputs/ball_tracking/detections/") for p in paths) == 9,
             "Nine original prediction embargoes must remain present in authority")
    for name in paths:
        _absent(safe_path(root, name))


def _metadata(root, manifest_path, require_clean):
    """Read source, authority, certificate and resource metadata; never science."""
    root = Path(root).resolve()
    path = Path(manifest_path).absolute()
    _require(path == root / MANIFEST_PATH, "Unexpected error_breakdown manifest path")
    safe_path(root, MANIFEST_PATH)
    commit = original._clean_checkpoint(root) if require_clean else original._git(root, "rev-parse", "HEAD")
    manifest = read_json(path)
    _require(set(manifest) == MANIFEST_FIELDS
             and manifest["schema_version"] == "ball_crop_candidate_retention_error_breakdown/v0.1"
             and manifest["error_breakdown_id"] == ID and manifest["output_root"] == OUTPUT_ROOT
             and manifest["permitted_stages"] == ["summarize"] and manifest["unit_key"] == UNIT_KEY
             and manifest["maximum_unit_seconds"] == MAX_UNIT_SECONDS
             and manifest["maximum_summary_bytes"] == MAX_SUMMARY_BYTES,
             "Unsupported error_breakdown scope")
    _require(all(manifest[k] is None for k in ("selected_method", "selected_operating_point", "quality_gate")),
             "ErrorBreakdown cannot choose a method or quality gate")
    _require(manifest["scientific_inputs"] == SCIENTIFIC_INPUTS, "Only the three exact scientific inputs are permitted")
    expected = {"proposal": (PROPOSAL_PATH, PROPOSAL_SHA), "authorization": (APPROVAL_PATH, APPROVAL_SHA),
                "completion_checkpoint": (COMPLETION_PATH, COMPLETION_SHA),
                "human_review_record": (HUMAN_REVIEW_PATH, HUMAN_REVIEW_SHA),
                "window_authority": (WINDOW_AUTHORITY_PATH, WINDOW_AUTHORITY_SHA)}
    for key, (name, digest) in expected.items():
        _require(digest is not None and manifest[key] == {"path": name, "sha256": digest}, "Exact error_breakdown authority changed")
        verify_binding(root, manifest[key])
    _require(manifest["frozen_history"] == {"path": FROZEN_HISTORY_PATH, "sha256": FROZEN_HISTORY_SHA},
             "Frozen error_breakdown history changed")
    history = read_json(verify_binding(root, manifest["frozen_history"]))
    approval = read_json(root / APPROVAL_PATH)
    _require(approval["schema_version"] == "ball_crop_candidate_retention_error_breakdown_approval/v0.1"
             and approval["proposal"] == manifest["proposal"] and approval["approved_by"] == "ryan"
             and approval["implementation_authorized"] is True and approval["execution_authorized"] is True
             and approval["clean_commit_required"] is True and approval["training_authorized"] is False
             and approval["git_mutations_authorized"] is False,
             "Exact error_breakdown approval is missing")
    checkpoint = read_json(root / COMPLETION_PATH)
    _require(checkpoint["schema_version"] == "interpretation_completion_checkpoint/v0.1"
             and checkpoint["head"] == PREVIOUS_COMMIT and checkpoint["resource_event_count"] == PREFIX_COUNT
             and checkpoint["completion_event_sha256"] == PREFIX_TIP
             and checkpoint["completed_attempts"] == PREFIX_ATTEMPTS and checkpoint["successful_attempts"] == 54
             and set(checkpoint["preserved_failed_attempts"]) == KNOWN_FAILURES and checkpoint["active_workers"] == 0
             and checkpoint["cumulative_active_seconds"] == USED_SECONDS
             and math.isclose(checkpoint["remaining_cumulative_seconds"], 14400 - USED_SECONDS, rel_tol=0, abs_tol=1e-7)
             and checkpoint["interpretation_completed"] is True and checkpoint["bounded_summary_successfully_returned"] is True
             and checkpoint["worker_result"] == PREDECESSOR_RECEIPTS["interpret"],
             "The exact completed interpretation checkpoint is required")
    publication = read_json(verify_binding(root, PUBLICATION_CHECKPOINT))
    window_authority = read_json(root / WINDOW_AUTHORITY_PATH)
    _require([{key: row[key] for key in WINDOWS[0]} for row in window_authority["windows"]] == WINDOWS,
             "Approved window identity/order/bounds changed")
    _require(window_authority["sealed_holdouts_metadata_only"] == HOLDOUTS
             and set(window_authority["original_embargo_paths"]) <= set(publication["preserved_absent_paths"]),
             "Window authority protected scope changed")
    human = read_json(root / HUMAN_REVIEW_PATH)
    _require(human["schema_version"] == "ball_crop_candidate_retention_visual_review_record/v0.1"
             and human["human_visual_review"]["status"] == "completed_and_approved"
             and human["human_visual_review"]["requested_scope_completed"] is True
             and human["bound_evidence"]["completion_checkpoint"] == PUBLICATION_CHECKPOINT,
             "The six new human reviews must be complete")
    _require(history["schema_version"] == "ball_crop_candidate_retention_error_breakdown_frozen_history/v0.1"
             and history["completion_checkpoint"] == manifest["completion_checkpoint"]
             and history["resource_limits"] == checkpoint["resource_limits"]
             and set(history["preserved_absent_paths"]) == set(publication["preserved_absent_paths"]) |
                 {OUTPUT_ROOT + "/supervisor.lock", OUTPUT_ROOT + "/" + OUTPUT_DIR}
             and history["sealed_holdouts_metadata_only"] == HOLDOUTS,
             "Frozen metadata belongs to another completed comparison")
    _protected_metadata(root, publication)
    # This older certificate contains only source/test/helper bindings. Never
    # traverse its scientific evidence or artifact pointers here.
    for prior in (publication, checkpoint):
        old_certificate = read_json(verify_binding(root, prior["implementation_validation"]))
        for row in old_certificate["source_bindings"] + old_certificate.get("helper_bindings", []):
            name = row["path"]
            _require(name == "requirements.txt" or name.endswith(".py") and
                     (name.startswith("src/") or name.startswith("tests/") or name.startswith(OUTPUT_ROOT + "/audit/")),
                     "Old certificate contains a non-source binding")
            verify_binding(root, row)
    for stage, binding in PREDECESSOR_RECEIPTS.items():
        receipt = read_json(verify_binding(root, binding))
        _require(receipt["stage"] == stage, "Predecessor receipt role changed")
        artifacts = {_pair(b)["path"]: b["sha256"] for b in receipt["artifacts"]}
        needed = ("representative_pool", "challenge_pool") if stage == "score-final" else ("audit",) if stage == "completion-audit" else ()
        _require(all(artifacts.get(SCIENTIFIC_INPUTS[k]["path"]) == SCIENTIFIC_INPUTS[k]["sha256"] for k in needed),
                 "Scientific input lost its completed receipt binding")
    if require_clean:
        _validate_implementation(root, manifest)
        _require(subprocess.run(["git", "merge-base", "--is-ancestor", PREVIOUS_COMMIT, "HEAD"], cwd=root).returncode == 0,
                 "Error breakdown must descend from the completed interpretation")
        for name in (MANIFEST_PATH, PROPOSAL_PATH, APPROVAL_PATH, HUMAN_REVIEW_PATH, WINDOW_AUTHORITY_PATH):
            original._git(root, "ls-files", "--error-unmatch", "--", name)
    output = safe_path(root, OUTPUT_ROOT)
    _require(subprocess.run(["git", "check-ignore", "-q", "--", OUTPUT_ROOT + "/" + OUTPUTS[0]], cwd=root).returncode == 0,
             "ErrorBreakdown outputs must remain ignored")
    return {"root": root, "manifest_path": path, "manifest": manifest, "approval": approval,
            "checkpoint": checkpoint, "protection": publication, "history": history, "limits": checkpoint["resource_limits"],
            "commit": commit, "spec_sha256": canonical_sha256(manifest), "output_root": output}


def _seal(root, output, binding, aid, suffix, event):
    _require(binding["path"] == (output / "attempts" / (aid + suffix)).relative_to(root).as_posix(),
             "Attempt seal names another file")
    _require(read_json(verify_binding(root, binding)) == {"event_sha256": event["sha256"]},
             "Completed attempt seal changed")


def _successful_completion(event, limits):
    integer_fields = ("exit_code", "monitor_samples", "peak_worker_memory_bytes", "maximum_output_bytes",
                      "final_accounting_output_bound_bytes", "minimum_free_disk_bytes",
                      "memory_overshoot_bytes", "output_overshoot_bytes")
    duration_fields = ("elapsed_seconds", "time_budget_seconds", "time_overshoot_seconds", "maximum_monitor_interval_seconds")
    _require(all(type(event[k]) is int and event[k] >= 0 for k in integer_fields)
             and all(type(event[k]) in (int, float) and math.isfinite(event[k]) and event[k] >= 0 for k in duration_fields),
             "Invalid error_breakdown completion resource counters")
    _require(event["success"] is True and event["exit_code"] == 0 and event["failure"] is None
             and event["final_accounting_error"] is None and event["worker_result"] is not None
             and 0 <= event["elapsed_seconds"] <= MAX_UNIT_SECONDS
             and event["time_budget_seconds"] == min(MAX_UNIT_SECONDS, limits["maximum_cumulative_seconds"] - USED_SECONDS)
             and all(event[key] == 0 for key in ("time_overshoot_seconds", "memory_overshoot_bytes", "output_overshoot_bytes"))
             and event["maximum_monitor_interval_seconds"] <= 1 and event["monitor_samples"] >= 1
             and event["peak_worker_memory_bytes"] <= limits["maximum_worker_memory_bytes"]
             and event["maximum_output_bytes"] <= event["final_accounting_output_bound_bytes"]
             and event["final_accounting_output_bound_bytes"] <= limits["maximum_total_new_output_bytes"]
             and event["minimum_free_disk_bytes"] >= limits["minimum_free_disk_bytes"],
             "ErrorBreakdown completion failed resource or success requirements; no retry")


def verify_history(root, context, phase="before"):
    """Verify only journal/seal/result metadata, never bound scientific bodies."""
    _require(phase in ("before", "worker", "completed"), "Unknown error_breakdown history phase")
    root, output = Path(root).resolve(), context["output_root"]
    prefix = context["history"]["journal_prefix"]
    journal = BudgetJournal(output, context["limits"])
    _require(len(prefix["events"]) == PREFIX_COUNT and len(journal.events) >= PREFIX_COUNT
             and prefix["chain_tip_sha256"] == PREFIX_TIP and journal.events[PREFIX_COUNT - 1]["sha256"] == PREFIX_TIP,
             "Frozen completed resource prefix changed")
    _unique_bindings(prefix["events"])
    for index, binding in enumerate(prefix["events"]):
        _require(binding["path"] == (output / "resource_events" / f"{index:08d}.json").relative_to(root).as_posix(),
                 "Noncontiguous frozen resource bindings")
        verify_binding(root, binding)
    frozen = journal.events[:PREFIX_COUNT]
    starts = {e["attempt_id"]: e for e in frozen if e["kind"] == "started"}
    ends = {e["attempt_id"]: e for e in frozen if e["kind"] == "finished"}
    rows = prefix["attempts"]
    _require(len(rows) == len(starts) == len(ends) == PREFIX_ATTEMPTS
             and {r["attempt_id"] for r in rows} == set(starts) == set(ends)
             and {aid for aid, end in ends.items() if not end["success"]} == KNOWN_FAILURES,
             "The exact completed fifty-seven-attempt history is required")
    for row in rows:
        aid = row["attempt_id"]
        start, end = starts[aid], ends[aid]
        _require(row["unit_key"] == start["unit_key"] and row["success"] is end["success"]
                 and row["completion_event_sha256"] == end["sha256"], "Historical attempt identity changed")
        _seal(root, output, row["reservation"], aid, ".reservation.json", start)
        _seal(root, output, row["completion"], aid, ".completion.json", end)
        if not end["success"]:
            _require(row["worker_result"] is None and end["worker_result"] is None, "Failed attempt gained a receipt")
            _absent(output / "attempts" / (aid + ".result.json"))
        else:
            expected = {"path": OUTPUT_ROOT + "/attempts/" + aid + ".result.json",
                        "sha256": end["worker_result"]["sha256"]}
            _require(end["worker_result"]["path"] == "attempts/" + aid + ".result.json"
                     and row["worker_result"] == expected, "Historical success receipt changed")
            verify_binding(root, row["worker_result"])
    _require(math.isclose(sum(e["elapsed_seconds"] for e in ends.values()), USED_SECONDS, rel_tol=0, abs_tol=1e-7),
             "Consumed resource allowance changed")
    suffix = journal.events[PREFIX_COUNT:]
    attempts = journal._attempts()
    new = {aid: row for aid, row in attempts.items() if aid not in starts}
    if phase == "before":
        _require(not suffix and not new and all(a["finished"] is not None for a in attempts.values()),
                 "ErrorBreakdown requires the untouched completed prefix; no retry or reuse")
        return journal
    _require(len(new) == 1 and suffix and suffix[0]["kind"] == "started", "Exactly one new error_breakdown attempt is required")
    aid, attempt = next(iter(new.items()))
    start, end = attempt["start"], attempt["finished"]
    _require(start["unit_key"] == UNIT_KEY and start["selection_unit"] is False
             and start["reserved_seconds"] == min(MAX_UNIT_SECONDS, context["limits"]["maximum_cumulative_seconds"] - USED_SECONDS)
             and all(e["attempt_id"] == aid for e in suffix)
             and sum(e["kind"] == "started" for e in suffix) == 1,
             "Unknown role or changed error_breakdown reservation")
    reservation = output / "attempts" / (aid + ".reservation.json")
    _require(read_json(safe_path(root, reservation.relative_to(root).as_posix())) == {"event_sha256": start["sha256"]},
             "ErrorBreakdown reservation seal changed")
    samples = [event for event in suffix if event["kind"] == "sample"]
    limits = context["limits"]
    for sample in samples:
        _require(all(type(sample[k]) is int and sample[k] >= 0
                     for k in ("memory_bytes", "output_bytes", "free_disk_bytes"))
                 and type(sample["elapsed_seconds"]) in (int, float)
                 and math.isfinite(sample["elapsed_seconds"])
                 and 0 <= sample["elapsed_seconds"] <= start["reserved_seconds"]
                 and sample["memory_bytes"] <= limits["maximum_worker_memory_bytes"]
                 and sample["output_bytes"] <= limits["maximum_total_new_output_bytes"]
                 and sample["free_disk_bytes"] >= limits["minimum_free_disk_bytes"],
                 "ErrorBreakdown sample violated the approved resource bounds")
    if phase == "worker":
        _require(aid == os.environ.get("BALL_RETENTION_ATTEMPT_ID") and end is None
                 and all(e["kind"] in ("started", "sample") for e in suffix),
                 "Worker does not own the sole active error_breakdown reservation")
    else:
        _require(end is not None and suffix[-1] == end, "Incomplete error_breakdown requires investigation")
        _successful_completion(end, context["limits"])
        # The supervisor measures between persisted samples too. Its final
        # extrema may be more conservative, but cannot understate a sample.
        _require(bool(samples) and end["monitor_samples"] == len(samples)
                 and end["peak_worker_memory_bytes"] >= max(s["memory_bytes"] for s in samples)
                 and end["maximum_output_bytes"] >= max(s["output_bytes"] for s in samples)
                 and end["minimum_free_disk_bytes"] <= min(s["free_disk_bytes"] for s in samples)
                 and end["final_accounting_output_bound_bytes"] >= max(s["output_bytes"] for s in samples),
                 "Completion understates persisted samples or their count")
        _require(end["worker_result"]["path"] == "attempts/" + aid + ".result.json",
                 "ErrorBreakdown completion names another receipt")
        _require(read_json(safe_path(root, (output / "attempts" / (aid + ".completion.json")).relative_to(root).as_posix()))
                 == {"event_sha256": end["sha256"]}, "ErrorBreakdown completion seal changed")
    return journal


def _preserved_metadata(root, context, phase="before", allow_outputs=False):
    """lstat-only preservation; no media, report, candidate or trace hashing."""
    root, output = Path(root).resolve(), context["output_root"]
    history = context["history"]
    rows = history["preserved_files"]
    _require(len(rows) == len({r["path"] for r in rows}), "Repeated preserved file metadata")
    old_files = {row["path"] for row in rows}
    old_dirs = set(history["preserved_directories"])
    _require(len(old_dirs) == len(history["preserved_directories"]), "Repeated preserved directory")
    for row in rows:
        path = safe_path(root, row["path"], OUTPUT_ROOT)
        _require(_stat_metadata(path) == {key: row[key] for key in ("size_bytes", "mtime_ns", "device", "inode")},
                 "Preserved scientific/resource file metadata changed: " + row["path"])
    for name in old_dirs:
        path = safe_path(root, name)
        _require(path.is_dir() and (name == OUTPUT_ROOT or name.startswith(OUTPUT_ROOT + "/")),
                 "Preserved directory changed")
    _protected_metadata(root, context.get("protection", context["checkpoint"]))
    aid = os.environ.get("BALL_RETENTION_ATTEMPT_ID") if phase == "worker" else context.get("completed_attempt_id")
    if phase == "before":
        for name in history["preserved_absent_paths"]:
            _absent(safe_path(root, name))
    elif phase == "worker":
        _require(aid is not None and re.fullmatch(r"[0-9a-f]{32}", aid), "Invalid owned attempt identity")
        owner = read_json(safe_path(root, OUTPUT_ROOT + "/supervisor.lock"))
        _require(owner["pid"] == int(os.environ["BALL_RETENTION_PARENT_PID"]), "Unowned error_breakdown supervisor lock")
    else:
        _require(phase == "completed" and aid is not None, "Unknown preserved metadata phase")
        _absent(output / "supervisor.lock")
    destination = safe_path(root, OUTPUT_ROOT + "/" + OUTPUT_DIR)
    if not allow_outputs:
        _absent(destination)
    permitted_files = {OUTPUT_ROOT + "/" + p for p in OUTPUTS} if allow_outputs else set()
    permitted_dirs = {OUTPUT_ROOT + "/" + OUTPUT_DIR} if allow_outputs else set()
    if aid:
        permitted_files |= {OUTPUT_ROOT + "/attempts/" + aid + ending
                            for ending in (".reservation.json", ".completion.json", ".log", ".start", ".result.json")}
        permitted_dirs.add(OUTPUT_ROOT + "/attempts/" + aid + ".temp")
    if phase == "worker":
        permitted_files.add(OUTPUT_ROOT + "/supervisor.lock")
    def dynamic_event(name):
        relative = name.removeprefix(OUTPUT_ROOT + "/resource_events/")
        match = re.fullmatch(r"(\d{8})\.json", relative)
        if match is None and phase == "worker":
            match = re.fullmatch(r"\.pending_(\d{8})\.json_[0-9a-f]{32}", relative)
        return phase != "before" and name.startswith(OUTPUT_ROOT + "/resource_events/") and match is not None and int(match[1]) >= PREFIX_COUNT
    def fail(error):
        raise error
    for folder, directories, files in os.walk(output, onerror=fail):
        for name in directories:
            relative = (Path(folder) / name).relative_to(root).as_posix()
            safe_path(root, relative)
            _require(relative in old_dirs | permitted_dirs, "Unexpected new evidence directory: " + relative)
        for name in files:
            relative = (Path(folder) / name).relative_to(root).as_posix()
            safe_path(root, relative)
            _require(relative in old_files | permitted_files or dynamic_event(relative), "Unexpected new evidence file: " + relative)


class _ErrorBreakdownJournal(BudgetJournal):
    """Tighten only this new role's reservation; retain every original limit."""

    def reserve(self, unit_key, selection_unit):
        _require(unit_key == UNIT_KEY and selection_unit is False, "Reservation adapter is limited to error_breakdown")
        _require(len(self.events) == PREFIX_COUNT and self.events[-1]["sha256"] == PREFIX_TIP,
                 "ErrorBreakdown cannot retry or reuse an existing attempt")
        attempts = self._attempts()
        _require(len(attempts) == PREFIX_ATTEMPTS and all(a["finished"] is not None for a in attempts.values())
                 and math.isclose(self.consumed(), USED_SECONDS, rel_tol=0, abs_tol=1e-7),
                 "ErrorBreakdown requires the completed original budget")
        remaining = min(MAX_UNIT_SECONDS, self.limits["maximum_cumulative_seconds"] - self.consumed())
        _require(remaining > 0, "ErrorBreakdown allowance is exhausted")
        aid = uuid.uuid4().hex
        self.append("started", attempt_id=aid, unit_key=unit_key, selection_unit=False, reserved_seconds=remaining)
        resources._write_new(self.root / "attempts" / (aid + ".reservation.json"),
                             {"event_sha256": self.events[-1]["sha256"]})
        return aid, remaining


def _run_bounded_supervised(context, command):
    # The unchanged supervisor takes its monitored deadline from reserve(). Its
    # default non-selection reservation is the entire remaining allowance; this
    # new role alone instead reserves the approved tighter 300-second bound.
    _require(resources.BudgetJournal is BudgetJournal, "Unexpected resource journal implementation")
    resources.BudgetJournal = _ErrorBreakdownJournal
    try:
        return resources.run_supervised(context["output_root"], UNIT_KEY, command, context["limits"],
                                        cwd=context["root"], selection_unit=False, require_result=True)
    finally:
        resources.BudgetJournal = BudgetJournal


def _verify_scientific_input(root, context, key):
    _require(os.environ.get("BALL_RETENTION_ATTEMPT_ID"), "Scientific inputs require an active supervised worker")
    _require(key in SCIENTIFIC_INPUTS and set(context["manifest"]["scientific_inputs"]) == set(SCIENTIFIC_INPUTS),
             "Unapproved scientific input name")
    binding = context["manifest"]["scientific_inputs"][key]
    _require(binding == SCIENTIFIC_INPUTS[key], "Unapproved scientific input")
    path = safe_path(root, binding["path"])
    _require(_stat_metadata(path)["size_bytes"] == binding["size_bytes"], "Scientific input size changed")
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(block)
            _require(size <= binding["size_bytes"], "Scientific input grew while hashing")
            digest.update(block)
    _require(size == binding["size_bytes"] and digest.hexdigest() == binding["sha256"], "Scientific input bytes changed")
    return path


def _load_scientific_json(root, context, key):
    path = _verify_scientific_input(root, context, key)
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    _require(isinstance(value, dict), "Scientific input must be a published JSON object")
    return value


CHECKS = {"input_hashes_unchanged": True, "source_authority_unchanged": True,
          "preserved_metadata_and_receipts_unchanged": True, "output_integrity_verified": True,
          "only_three_scientific_inputs_read": True, "pools_loaded_sequentially": True,
          "no_new_scoring_aggregation_inference_or_media": True}


def _worker(root, manifest_path):
    wait_for_supervisor()
    root = Path(root).resolve()
    context = _metadata(root, manifest_path, True)
    journal = verify_history(root, context, "worker")
    aid = os.environ["BALL_RETENTION_ATTEMPT_ID"]
    result_path = safe_path(root, OUTPUT_ROOT + "/attempts/" + aid + ".result.json")
    _require(Path(os.environ["BALL_RETENTION_RESULT_PATH"]).resolve() == result_path,
             "Worker result destination differs from its reservation")
    _absent(result_path)
    _preserved_metadata(root, context, "worker")
    audit = _load_scientific_json(root, context, "audit")
    _require(audit["schema_version"] == "ball_crop_retention_independent_publication_recovery_audit/v0.1"
             and audit["status"] == "passed" and audit["execution_code_commit"] == PUBLICATION_COMMIT,
             "The exact passed publication audit is required")
    from .crop_retention_error_breakdown_summary import extract_pool, build_summary
    pool_results = []
    for key, purpose in (("representative_pool", "representative_evaluation"), ("challenge_pool", "challenge_evaluation")):
        pool = _load_scientific_json(root, context, key)
        _require(pool.get("purpose") == purpose, "Scientific pool identity differs from its bound input")
        extracted = extract_pool(pool, audit)
        _require(extracted.get("purpose") == purpose and extracted.get("source_input") == key,
                 "Copied breakdown belongs to another pool")
        pool_results.append(extracted)
        del pool
        gc.collect()
    summary, text = build_summary(pool_results)
    _require(isinstance(summary, dict) and isinstance(text, str)
             and summary.get("schema_version") == "ball_crop_retention_post_review_error_breakdown/v0.1"
             and isinstance(summary.get("source_map"), list) and bool(summary["source_map"])
             and all(k in summary and summary[k] is None for k in ("selected_method", "selected_operating_point", "quality_gate")),
             "Summary cannot select a method or quality gate")
    text_bytes = text.encode("utf-8")
    _require(0 < len(text_bytes) <= MAX_SUMMARY_BYTES, "Readable summary is empty or exceeds its byte limit")
    summary_bytes = _json_bytes(summary)
    destination = safe_path(root, OUTPUT_ROOT + "/" + OUTPUT_DIR)
    _absent(destination)
    destination.mkdir()
    _write_new(destination / "breakdown.json", summary_bytes)
    _write_new(destination / "summary.md", text_bytes)
    summary_bindings = [file_binding(root, destination / name) for name in ("breakdown.json", "summary.md")]
    certificate = read_json(verify_binding(root, context["manifest"]["implementation_validation"]))
    provenance = {
        "schema_version": "ball_crop_candidate_retention_error_breakdown_provenance/v0.1",
        "error_breakdown_id": ID, "unit_key": UNIT_KEY, "attempt_id": aid,
        "commit": context["commit"], "spec_sha256": context["spec_sha256"],
        "authority_bindings": {k: context["manifest"][k] for k in AUTHORITY_FIELDS},
        "implementation_validation": context["manifest"]["implementation_validation"],
        "source_bindings": certificate["source_bindings"],
        "scientific_inputs": context["manifest"]["scientific_inputs"],
        "summary_bindings": summary_bindings,
        "source_map": summary.get("source_map", {}),
        "frozen_prefix_count": PREFIX_COUNT, "frozen_prefix_tip_sha256": PREFIX_TIP,
        "active_reservation_sha256": journal._attempts()[aid]["start"]["sha256"],
        "preservation_basis": "Frozen file/directory metadata and complete receipt chain; only the two approved pools and audit were read/stream-hashed.",
        "checks": CHECKS,
        "acceptance": "Requires a subsequent successful supervisor completion and bound worker result.",
    }
    provenance_bytes = _json_bytes(provenance)
    _write_new(destination / "provenance.json", provenance_bytes)
    # Verify the newly authored outputs while still inside the worker. The
    # parent will inspect receipt metadata and the bounded returned text only.
    _require((destination / "breakdown.json").read_bytes() == summary_bytes
             and (destination / "summary.md").read_bytes() == text_bytes
             and read_json(destination / "provenance.json") == provenance, "ErrorBreakdown output integrity differs")
    end_context = _metadata(root, manifest_path, True)
    _require(end_context["spec_sha256"] == context["spec_sha256"] and end_context["commit"] == context["commit"],
             "Execution authority or commit changed during error_breakdown")
    for key in SCIENTIFIC_INPUTS:
        _verify_scientific_input(root, end_context, key)
    verify_history(root, end_context, "worker")
    _preserved_metadata(root, end_context, "worker", allow_outputs=True)
    artifacts = [file_binding(root, context["output_root"] / name) for name in OUTPUTS]
    authored = {"breakdown.json": summary_bytes, "summary.md": text_bytes, "provenance.json": provenance_bytes}
    _require(all(row["sha256"] == hashlib.sha256(authored[Path(row["path"]).name]).hexdigest() for row in artifacts),
             "Authored error_breakdown output changed during final verification")
    artifact_metadata = [{"path": row["path"], **_stat_metadata(root / row["path"])} for row in artifacts]
    result = {"schema_version": "ball_crop_candidate_retention_error_breakdown_worker_result/v0.1",
              "stage": "summarize", "unit_key": UNIT_KEY, "attempt_id": aid,
              "commit": context["commit"], "spec_sha256": context["spec_sha256"],
              "artifacts": artifacts, "artifact_metadata": artifact_metadata,
              "scientific_inputs": context["manifest"]["scientific_inputs"],
              "checks": CHECKS, "summary_payload": {"text": text, "size_bytes": len(text_bytes),
                                                       "sha256": hashlib.sha256(text_bytes).hexdigest()}}
    _write_new(result_path, _json_bytes(result))
    _require(read_json(result_path) == result, "ErrorBreakdown worker receipt differs")
    return {"worker_result_written": True, "attempt_id": aid, "completion_pending": True}


def _completed_result(root, context, event):
    root = Path(root).resolve()
    journal = verify_history(root, context, "completed")
    _require(journal.events[-1] == event, "Supervisor completion does not match the persisted resource event")
    aid = event["attempt_id"]
    context = {**context, "completed_attempt_id": aid}
    _preserved_metadata(root, context, "completed", allow_outputs=True)
    binding = {"path": OUTPUT_ROOT + "/" + event["worker_result"]["path"], "sha256": event["worker_result"]["sha256"]}
    result = read_json(verify_binding(root, binding))
    _require(set(result) == {"schema_version", "stage", "unit_key", "attempt_id", "commit", "spec_sha256",
                            "artifacts", "artifact_metadata", "scientific_inputs", "checks", "summary_payload"}
             and result["schema_version"] == "ball_crop_candidate_retention_error_breakdown_worker_result/v0.1"
             and result["stage"] == "summarize" and result["unit_key"] == UNIT_KEY and result["attempt_id"] == aid
             and result["commit"] == context["commit"] and result["spec_sha256"] == context["spec_sha256"]
             and result["checks"] == CHECKS and result["scientific_inputs"] == SCIENTIFIC_INPUTS,
             "Successful error_breakdown receipt differs from the approved unit")
    _unique_bindings(result["artifacts"])
    expected = {OUTPUT_ROOT + "/" + name for name in OUTPUTS}
    _require(len(result["artifacts"]) == 3 and {b["path"] for b in result["artifacts"]} == expected,
             "ErrorBreakdown receipt has missing or unauthorized outputs")
    rows = result["artifact_metadata"]
    _require(isinstance(rows, list) and len(rows) == 3 and {r["path"] for r in rows} == expected,
             "Output metadata is incomplete")
    for row in rows:
        _require(set(row) == {"path", "size_bytes", "mtime_ns", "device", "inode"}
                 and _stat_metadata(safe_path(root, row["path"])) == {k: row[k] for k in row if k != "path"},
                 "Output metadata changed after supervised verification")
    payload = result["summary_payload"]
    _require(set(payload) == {"text", "size_bytes", "sha256"} and isinstance(payload["text"], str),
             "Invalid bounded summary transport")
    text_bytes = payload["text"].encode("utf-8")
    _require(0 < len(text_bytes) <= MAX_SUMMARY_BYTES and len(text_bytes) == payload["size_bytes"]
             and hashlib.sha256(text_bytes).hexdigest() == payload["sha256"], "Returned summary payload is invalid")
    summary_path = OUTPUT_ROOT + "/" + OUTPUT_DIR + "/summary.md"
    _require(next(b["sha256"] for b in result["artifacts"] if b["path"] == summary_path) == payload["sha256"],
             "Returned summary is not the receipted readable artifact")
    for artifact in result["artifacts"]:
        metadata = _stat_metadata(safe_path(root, artifact["path"]))
        if artifact["path"] == summary_path:
            _require(metadata["size_bytes"] == len(text_bytes), "Readable summary metadata changed")
    # Do not hash or open the three scientific outputs from the parent.
    return {"stage": "summarize", "successful_workers": 1, "commit": context["commit"],
            "worker_result": binding, "completion_event_sha256": event["sha256"], "artifacts": result["artifacts"],
            "summary": payload["text"], "new_model_calls": 0, "scoring_executed": False,
            "media_decoded": False, "selected_method": None, "selected_operating_point": None, "quality_gate": None}


def run_error_breakdown(root, manifest_path, dry_run=False):
    context = _metadata(root, manifest_path, not dry_run)
    verify_history(root, context, "before")
    _preserved_metadata(root, context, "before")
    if dry_run:
        return {"dry_run": True, "metadata_only": True, "scientific_inputs_verified": False,
                "execution_requires_clean_tested_commit": True, "spec_sha256": context["spec_sha256"]}
    command = [sys.executable, "-B", "-m", "src.ball_tracking.crop_retention_error_breakdown",
               "--manifest", str(context["manifest_path"]), "--repository-root", str(context["root"]), "--worker"]
    event = _run_bounded_supervised(context, command)
    end_context = _metadata(root, manifest_path, True)
    _require(end_context["commit"] == context["commit"] and end_context["spec_sha256"] == context["spec_sha256"],
             "Parent execution authority changed before summary release")
    return _completed_result(root, end_context, event)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--stage", choices=("summarize",), default="summarize")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    _require(not (args.worker and args.dry_run), "A worker cannot use dry-run metadata authority")
    root = args.repository_root.resolve()
    manifest_path = root / args.manifest
    result = _worker(root, manifest_path) if args.worker else run_error_breakdown(root, manifest_path, args.dry_run)
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
