"""One clean-commit-gated recovery of the saved, already reviewed error breakdown.

The parent verifies administrative receipts and filesystem metadata only. The
owned worker alone reads the three frozen scientific inputs and its own outputs.
Nothing in this module edits historical evidence or installs global overrides.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

from . import crop_retention_error_breakdown as legacy
from . import crop_retention_monitor as monitor
from . import crop_retention_resources as resources
from .development_experiments import canonical_sha256, read_json, safe_path

ID = "rfdetr_medium_crop_candidate_retention_error_breakdown_recovery_v0_1"
MANIFEST_PATH = "configs/ball_tracking/crop_retention_experiments/" + ID + ".json"
APPROVAL_PATH = "configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_error_breakdown_recovery_integration_approval_v0_1.json"
DESIGN_PATH = "docs/ball_crop_candidate_retention_error_breakdown_recovery_integration.md"
IMPLEMENTATION_DIR = "data/outputs/t/ebri_fa730bcb6d2e"
CERTIFICATE_PATH = IMPLEMENTATION_DIR + "/implementation_validation.json"
POST_COMMIT_PATH = IMPLEMENTATION_DIR + "/post_commit_execution_checkpoint.json"
BASE_COMMIT = "fa730bcb6d2e6d396391191c0fb3e36a3a338bf1"
OUTPUT_ROOT = legacy.OUTPUT_ROOT
OUTPUT_DIR = "audit/post_review_error_breakdown_recovery_v0_1"
OUTPUTS = [OUTPUT_DIR + "/" + name for name in ("breakdown.json", "summary.md", "provenance.json")]
UNIT_KEY = "post-review-error-breakdown-recovery:summary:"
PREFIX_COUNT = 3010
PREFIX_ATTEMPTS = 58
PREFIX_TIP = "e5f2a832dd961d2615daa30ca77b039ad8dbe68bcbcfa12c2437128fbc83a3b3"
FAILED_ATTEMPT = "4adfb390f1f74a1baaec7fb178092218"
FAILED_SECONDS = 7.264999999984866
USED_SECONDS = 3267.507999999987
MAX_UNIT_SECONDS = 300
MAX_SUMMARY_BYTES = 65536
KNOWN_FAILURES = legacy.KNOWN_FAILURES | {FAILED_ATTEMPT}
SCIENTIFIC_INPUTS = legacy.SCIENTIFIC_INPUTS
FROZEN_HISTORY_PATH = "data/outputs/ball_tracking/crop_candidate_retention_error_breakdown_recovery_proposal/fa730bcb6d2e_2026-10-04/preparation_before.json"
FROZEN_HISTORY_SHA = "3da326ad4768f8b3f8e991fb176d27cdbe9474305c8f264acfc1b392bfd0dc9b"
AUTHORITY_PATHS = {
    "original_manifest": legacy.MANIFEST_PATH,
    "recovery_proposal": "docs/ball_crop_candidate_retention_error_breakdown_recovery_proposal.md",
    "recovery_authorization": "configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_error_breakdown_recovery_approval_v0_1.json",
    "monitor_revision": "docs/ball_crop_candidate_retention_monitor_revision.md",
    "monitor_authorization": "configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_monitor_revision_approval_v0_1.json",
    "integration_design": DESIGN_PATH,
    "integration_authorization": APPROVAL_PATH,
    "frozen_history": FROZEN_HISTORY_PATH,
}
AUTHORITY_FIELDS = tuple(AUTHORITY_PATHS)
MANIFEST_FIELDS = {"schema_version", "recovery_id", "output_root", "output_dir", "permitted_stages",
                   "unit_key", "shared_maximum_seconds", "maximum_summary_bytes", "scientific_inputs",
                   *AUTHORITY_FIELDS, "implementation_validation", "post_commit_checkpoint",
                   "selected_method", "selected_operating_point", "quality_gate"}
MONITOR_EVIDENCE = {
    "data/outputs/t/ebdm_fa730bcb6d2e/design_01_check_result.json",
    "data/outputs/t/ebdm_fa730bcb6d2e/completion_checkpoint.json",
}
CHECKS = {**legacy.CHECKS, "shared_failed_attempt_budget_preserved": True,
          "validated_monitor_used": True, "clean_post_commit_checkpoint_verified": True}
_require = legacy._require
verify_binding = legacy.verify_binding
file_binding = legacy.file_binding
_absent = legacy._absent
_stat_metadata = legacy._stat_metadata
BudgetJournal = resources.BudgetJournal


def _pair(value):
    _require(type(value) is dict and set(value) == {"path", "sha256"}
             and type(value["path"]) is str and type(value["sha256"]) is str
             and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]), "Invalid exact metadata binding")
    return value


def _read_bound(root, binding, limit=32 * 1024 * 1024):
    """Only callers' fixed administrative paths may reach this bounded reader."""
    _pair(binding)
    _require(binding["path"] not in {row["path"] for row in SCIENTIFIC_INPUTS.values()}
             and binding["path"] not in {OUTPUT_ROOT + "/" + name for name in OUTPUTS},
             "Scientific bodies cannot be read by the administrative verifier")
    path = safe_path(root, binding["path"])
    before = _stat_metadata(path)
    _require(before["size_bytes"] <= limit, "Administrative receipt exceeds its byte bound")
    with path.open("rb") as stream:
        payload = stream.read(limit + 1)
    _require(len(payload) <= limit and _stat_metadata(path) == before
             and hashlib.sha256(payload).hexdigest() == binding["sha256"],
             "Administrative receipt changed or differs from its binding")
    return json.loads(payload)


def _spec_sha256(manifest):
    return canonical_sha256({key: value for key, value in manifest.items()
                             if key != "implementation_validation"})


def _validate_manifest(manifest):
    _require(type(manifest) is dict and set(manifest) == MANIFEST_FIELDS
             and manifest["schema_version"] == "ball_crop_candidate_retention_error_breakdown_recovery/v0.1"
             and manifest["recovery_id"] == ID and manifest["output_root"] == OUTPUT_ROOT
             and manifest["output_dir"] == OUTPUT_DIR and manifest["permitted_stages"] == ["summarize"]
             and manifest["unit_key"] == UNIT_KEY and manifest["shared_maximum_seconds"] == MAX_UNIT_SECONDS
             and manifest["maximum_summary_bytes"] == MAX_SUMMARY_BYTES
             and manifest["scientific_inputs"] == SCIENTIFIC_INPUTS
             and manifest["post_commit_checkpoint"] == POST_COMMIT_PATH,
             "Unsupported recovery scope")
    _require(all(manifest[key] is None for key in ("selected_method", "selected_operating_point", "quality_gate")),
             "Recovery cannot select a method, operating point or quality gate")
    for key, path in AUTHORITY_PATHS.items():
        _require(_pair(manifest[key])["path"] == path, "Recovery authority path changed: " + key)
    _require(manifest["frozen_history"] == {"path": FROZEN_HISTORY_PATH, "sha256": FROZEN_HISTORY_SHA},
             "The exact failed-prefix preservation authority is required")
    _require(_pair(manifest["implementation_validation"])["path"] == CERTIFICATE_PATH,
             "Unexpected recovery validation certificate")


def _validate_implementation(root, manifest):
    certificate = _read_bound(root, manifest["implementation_validation"])
    _require(certificate["schema_version"] == "ball_crop_candidate_retention_error_breakdown_recovery_implementation_validation/v0.1",
             "Unsupported recovery validation certificate")
    for key in ("focused_tests_passed", "full_suite_passed", "independent_static_review_passed",
                "integrity_tests_passed", "monitor_design_check_passed"):
        _require(certificate.get(key) is True, "Recovery implementation validation is incomplete: " + key)
    _require(certificate["manifest_spec_sha256"] == _spec_sha256(manifest)
             and certificate["authority_sha256"] == {key: manifest[key]["sha256"] for key in AUTHORITY_FIELDS},
             "Recovery validation is bound to different authority/specification")
    required = {path.relative_to(root).as_posix() for folder in ("src", "tests")
                for path in (root / folder).rglob("*.py")} | {"requirements.txt"}
    rows = certificate["source_bindings"]
    legacy._unique_bindings(rows)
    _require({row["path"] for row in rows} == required, "Current validation must cover the complete current source inventory")
    for row in rows:
        verify_binding(root, row)
        legacy.original._git(root, "ls-files", "--error-unmatch", "--", row["path"])
    evidence = certificate["evidence_bindings"]
    legacy._unique_bindings(evidence)
    _require(bool(evidence), "Validation evidence is missing")
    for row in evidence:
        _require(row["path"] in MONITOR_EVIDENCE or row["path"].startswith(IMPLEMENTATION_DIR + "/"),
                 "Validation evidence points outside the approved administrative directories")
        safe_path(root, row["path"])
        verify_binding(root, row)
    return certificate


def _post_commit_checkpoint(root, manifest, commit):
    """An absent release gate is a hard stop before history/root scans or dispatch."""
    path = safe_path(root, POST_COMMIT_PATH)
    _require(path.is_file(), "The post-commit execution checkpoint is absent; execution remains blocked")
    checkpoint = monitor._read_record(path)
    _require(checkpoint["schema_version"] == "ball_crop_candidate_retention_error_breakdown_recovery_execution_checkpoint/v0.1"
             and type(commit) is str and re.fullmatch(r"[0-9a-f]{40}", commit) and commit != BASE_COMMIT
             and checkpoint["head"] == commit and checkpoint["branch"] == "codex/ball-detector-baseline"
             and checkpoint["manifest"] == file_binding(root, root / MANIFEST_PATH)
             and checkpoint["implementation_validation"] == manifest["implementation_validation"]
             and checkpoint["manifest_spec_sha256"] == _spec_sha256(manifest)
             and checkpoint["failed_prefix_tip_sha256"] == PREFIX_TIP,
             "Post-commit checkpoint does not bind this exact execution")
    for key in ("execution_authorized", "clean", "index_empty", "validated_sources_unchanged"):
        _require(checkpoint.get(key) is True, "Post-commit execution prerequisite is missing: " + key)
    _require(subprocess.run(["git", "merge-base", "--is-ancestor", BASE_COMMIT, commit], cwd=root).returncode == 0,
             "Recovery must descend from the preserved failed execution commit")
    return checkpoint


def _metadata(root, manifest_path, require_clean=True):
    root = Path(root).resolve()
    path = Path(manifest_path).absolute()
    _require(path == root / MANIFEST_PATH, "Unexpected recovery manifest path")
    commit = legacy.original._clean_checkpoint(root) if require_clean else legacy.original._git(root, "rev-parse", "HEAD")
    manifest = read_json(safe_path(root, MANIFEST_PATH))
    _validate_manifest(manifest)
    checkpoint = _post_commit_checkpoint(root, manifest, commit) if require_clean else None
    for key in AUTHORITY_FIELDS:
        verify_binding(root, manifest[key])
    approval = _read_bound(root, manifest["integration_authorization"])
    _require(approval["schema_version"] == "ball_crop_candidate_retention_error_breakdown_recovery_integration_approval/v0.1"
             and approval["approved_by"].lower() == "ryan" and approval["maximum_new_recovery_attempts"] == 1
             and approval["design"] == manifest["integration_design"]
             and approval["recovery_authorization"] == manifest["recovery_authorization"]
             and approval["monitor_authorization"] == manifest["monitor_authorization"],
             "The exact operational integration approval is required")
    for key in ("implementation_authorized", "focused_validation_authorized", "full_regression_authorized",
                "operational_amendment_approved", "scientific_scope_unchanged", "clean_commit_required"):
        _require(approval.get(key) is True, "Missing integration approval prerequisite: " + key)
    for key in ("scientific_execution_authorized_by_this_record", "git_mutations_authorized",
                "training_authorized", "automatic_retry_authorized"):
        _require(approval.get(key) is False, "Integration approval expanded the authorized scope: " + key)
    recovery_approval = _read_bound(root, manifest["recovery_authorization"])
    _require(recovery_approval["conditional_execution_authorized"] is True
             and recovery_approval["maximum_new_recovery_attempts"] == 1
             and recovery_approval["scientific_scope_unchanged"] is True
             and recovery_approval["proposal"] == manifest["recovery_proposal"]
             and recovery_approval["frozen_metadata"] == manifest["frozen_history"]
             and recovery_approval["failed_attempt_id"] == FAILED_ATTEMPT
             and recovery_approval["shared_original_and_recovery_maximum_seconds"] == MAX_UNIT_SECONDS,
             "Original conditional recovery authority changed")
    monitor_approval = _read_bound(root, manifest["monitor_authorization"])
    _require(monitor_approval["implementation_authorized"] is True
             and monitor_approval["historical_limits_journal_and_consumed_budgets_preserved"] is True,
             "The separately reviewed monitor revision is required")
    # Validate the immutable historical foundation only. This false-mode helper
    # does not inspect the live journal or demand that an old source inventory
    # contain the newly added files. No legacy executable entry point is called.
    historical = legacy._metadata(root, root / legacy.MANIFEST_PATH, False)
    history = _read_bound(root, manifest["frozen_history"])
    _require(history["schema_version"] == "error_breakdown_recovery_proposal_preparation/v0.1"
             and history["head"] == BASE_COMMIT and history["original_frozen_history"] == historical["manifest"]["frozen_history"]
             and history["sealed_holdouts_metadata_only"] == legacy.HOLDOUTS
             and history["scientific_bodies_read_or_hashed"] is False,
             "Recovery preservation metadata belongs to another history")
    certificate = _validate_implementation(root, manifest) if require_clean else None
    if require_clean:
        for name in (MANIFEST_PATH, *AUTHORITY_PATHS.values()):
            if not name.startswith("data/"):
                legacy.original._git(root, "ls-files", "--error-unmatch", "--", name)
    _require(subprocess.run(["git", "check-ignore", "-q", "--", OUTPUT_ROOT + "/" + OUTPUTS[0]], cwd=root).returncode == 0,
             "Recovery outputs must remain ignored")
    return {"root": root, "manifest_path": path, "manifest": manifest, "commit": commit,
            "spec_sha256": _spec_sha256(manifest), "output_root": safe_path(root, OUTPUT_ROOT),
            "limits": historical["limits"], "history": history, "original_context": historical,
            "certificate": certificate, "policy": monitor.monitoring_policy(historical["limits"], .25),
            "checkpoint": checkpoint}


def _remaining_seconds(journal):
    roles = journal.consumed(legacy.UNIT_KEY) + journal.consumed(UNIT_KEY)
    return min(MAX_UNIT_SECONDS - roles, journal.limits["maximum_cumulative_seconds"] - journal.consumed())


def _closed_prefix(journal):
    _require(len(journal.events) >= PREFIX_COUNT and journal.events[PREFIX_COUNT - 1]["sha256"] == PREFIX_TIP,
             "The exact failed 3010-event prefix is required")
    frozen = journal.events[:PREFIX_COUNT]
    starts = {e["attempt_id"]: e for e in frozen if e["kind"] == "started"}
    ends = {e["attempt_id"]: e for e in frozen if e["kind"] == "finished"}
    _require(len(starts) == len(ends) == PREFIX_ATTEMPTS and set(starts) == set(ends)
             and {aid for aid, event in ends.items() if event["success"] is False} == KNOWN_FAILURES
             and sum(event["success"] is True for event in ends.values()) == 54,
             "The exact 58 closed attempts, 54 successes and 4 failures are required")
    _require(starts[FAILED_ATTEMPT]["unit_key"] == legacy.UNIT_KEY
             and ends[FAILED_ATTEMPT]["success"] is False and ends[FAILED_ATTEMPT]["worker_result"] is None
             and math.isclose(ends[FAILED_ATTEMPT]["elapsed_seconds"], FAILED_SECONDS, rel_tol=0, abs_tol=1e-7)
             and math.isclose(sum(event["elapsed_seconds"] for event in ends.values()), USED_SECONDS, rel_tol=0, abs_tol=1e-7),
             "Original failed attempt role, evidence or consumed allowance changed")
    return starts, ends


class RecoveryJournal(BudgetJournal):
    """One new reservation from the original shared 300-second allowance."""

    def reserve(self, unit_key, selection_unit):
        _require(unit_key == UNIT_KEY and selection_unit is False, "Unknown recovery reservation role")
        _require(len(self.events) == PREFIX_COUNT, "Recovery cannot retry or adopt an existing suffix")
        _closed_prefix(self)
        attempts = self._attempts()
        _require(len(attempts) == PREFIX_ATTEMPTS and all(a["finished"] is not None for a in attempts.values())
                 and not any(a["start"]["unit_key"] == UNIT_KEY for a in attempts.values()),
                 "Recovery requires exactly the untouched closed history")
        remaining = _remaining_seconds(self)
        _require(remaining > 0, "Shared recovery allowance is exhausted")
        aid = uuid.uuid4().hex
        self.append("started", attempt_id=aid, unit_key=UNIT_KEY, selection_unit=False, reserved_seconds=remaining)
        resources._write_new(self.root / "attempts" / (aid + ".reservation.json"),
                             {"event_sha256": self.events[-1]["sha256"]})
        return aid, remaining


def _scan_record(scan, policy_sha):
    _require(type(scan) is dict and set(scan) == {"schema_version", "request_id", "requested_at", "scan_started_at",
             "completed_at", "output_bytes", "success", "error", "policy_sha256"}
             and scan["schema_version"] == monitor.RESPONSE_VERSION and scan["policy_sha256"] == policy_sha
             and scan["success"] is True and scan["error"] is None
             and type(scan["output_bytes"]) is int and scan["output_bytes"] >= 0
             and type(scan["request_id"]) is str and re.fullmatch(r"[0-9a-f]{32}", scan["request_id"]),
             "Invalid completed monitor scan")
    times = [scan[key] for key in ("requested_at", "scan_started_at", "completed_at")]
    _require(all(type(value) in (int, float) and math.isfinite(value) for value in times)
             and 0 <= times[0] <= times[1] <= times[2] and times[2] - times[0] < 10,
             "Monitor scan timestamp/deadline changed")


def _successful_completion(event, context, reservation):
    limits, policy = context["limits"], context["policy"]
    policy_sha = resources._digest(policy)
    for key in ("exit_code", "monitor_samples", "peak_worker_memory_bytes", "maximum_output_bytes",
                "final_accounting_output_bound_bytes", "minimum_free_disk_bytes", "completed_scans",
                "memory_overshoot_bytes", "output_overshoot_bytes"):
        _require(type(event[key]) is int and event[key] >= 0, "Invalid completed resource counter: " + key)
    for key in ("elapsed_seconds", "charged_elapsed_seconds", "total_wall_seconds_before_publication",
                "time_budget_seconds", "time_overshoot_seconds", "maximum_monitor_interval_seconds"):
        _require(type(event[key]) in (int, float) and math.isfinite(event[key]) and event[key] >= 0,
                 "Invalid completed resource duration: " + key)
    _require(event["success"] is True and event["exit_code"] == 0 and event["failure"] is None
             and event["final_accounting_error"] is None and event["worker_result"] is not None
             and event["owned_cleanup_verified"] is True and event["cleanup_errors"] == []
             and event["monitoring_policy_sha256"] == policy_sha
             and event["time_budget_seconds"] == reservation
             and event["elapsed_seconds"] == event["charged_elapsed_seconds"] <= reservation
             and event["total_wall_seconds_before_publication"] >= event["charged_elapsed_seconds"]
             and all(event[key] == 0 for key in ("time_overshoot_seconds", "memory_overshoot_bytes", "output_overshoot_bytes"))
             and event["maximum_monitor_interval_seconds"] <= 1 and event["monitor_samples"] >= 1
             and event["completed_scans"] >= 2
             and event["peak_worker_memory_bytes"] <= policy["maximum_combined_rss_bytes"]
             and event["maximum_output_bytes"] <= event["final_accounting_output_bound_bytes"] <= limits["maximum_total_new_output_bytes"]
             and event["minimum_free_disk_bytes"] >= policy["effective_minimum_free_disk_bytes"],
             "Recovery completion failed the validated monitor/budget requirements; no retry")
    _scan_record(event["final_scan"], policy_sha)
    _require(event["final_scan"]["output_bytes"] <= event["maximum_output_bytes"], "Final accounting understated")


def verify_history(root, context, phase="before"):
    _require(phase in ("before", "worker", "completed"), "Unknown recovery history phase")
    root, output = Path(root).resolve(), context["output_root"]
    history = context["history"]
    journal = BudgetJournal(output, context["limits"])
    starts, ends = _closed_prefix(journal)
    prefix = history["journal_prefix"]
    rows = prefix["raw_event_bindings"]
    _require(prefix["event_count"] == PREFIX_COUNT and prefix["tip_sha256"] == PREFIX_TIP
             and len(rows) == PREFIX_COUNT and history["failure_completion"] == ends[FAILED_ATTEMPT],
             "Frozen recovery journal metadata differs")
    legacy._unique_bindings(rows)
    for index, binding in enumerate(rows):
        _require(binding["path"] == OUTPUT_ROOT + f"/resource_events/{index:08d}.json", "Noncontiguous frozen journal binding")
        verify_binding(root, binding)
    historical_rows = context["original_context"]["history"]["journal_prefix"]["attempts"]
    _require(len(historical_rows) == legacy.PREFIX_ATTEMPTS
             and {row["attempt_id"] for row in historical_rows} == set(starts) - {FAILED_ATTEMPT},
             "Historical receipt inventory changed")
    for row in historical_rows:
        aid = row["attempt_id"]
        _require(row["unit_key"] == starts[aid]["unit_key"] and row["success"] is ends[aid]["success"]
                 and row["completion_event_sha256"] == ends[aid]["sha256"], "Historical attempt role changed")
        legacy._seal(root, output, row["reservation"], aid, ".reservation.json", starts[aid])
        legacy._seal(root, output, row["completion"], aid, ".completion.json", ends[aid])
        if ends[aid]["success"]:
            expected = {"path": OUTPUT_ROOT + "/attempts/" + aid + ".result.json",
                        "sha256": ends[aid]["worker_result"]["sha256"]}
            _require(row["worker_result"] == expected and ends[aid]["worker_result"]["path"] == "attempts/" + aid + ".result.json",
                     "Historical success receipt role changed")
            verify_binding(root, expected)
        else:
            _require(row["worker_result"] is None and ends[aid]["worker_result"] is None, "Failed evidence gained a receipt")
            _absent(output / "attempts" / (aid + ".result.json"))
    for suffix, event in ((".reservation.json", starts[FAILED_ATTEMPT]), (".completion.json", ends[FAILED_ATTEMPT])):
        _require(read_json(safe_path(root, OUTPUT_ROOT + "/attempts/" + FAILED_ATTEMPT + suffix)) == {"event_sha256": event["sha256"]},
                 "Original failed attempt seal changed")
    _absent(output / "attempts" / (FAILED_ATTEMPT + ".result.json"))
    suffix = journal.events[PREFIX_COUNT:]
    attempts = journal._attempts()
    new = {aid: value for aid, value in attempts.items() if aid not in starts}
    if phase == "before":
        _require(not suffix and not new and all(row["finished"] is not None for row in attempts.values()),
                 "Recovery requires the untouched failed prefix; no retry or unknown suffix")
        return journal
    _require(len(new) == 1 and suffix and suffix[0]["kind"] == "started", "Exactly one owned recovery attempt is required")
    aid, attempt = next(iter(new.items()))
    start, end = attempt["start"], attempt["finished"]
    expected_seconds = min(MAX_UNIT_SECONDS - FAILED_SECONDS, context["limits"]["maximum_cumulative_seconds"] - USED_SECONDS)
    _require(start["unit_key"] == UNIT_KEY and start["selection_unit"] is False
             and math.isclose(start["reserved_seconds"], expected_seconds, rel_tol=0, abs_tol=1e-7)
             and all(event["attempt_id"] == aid for event in suffix)
             and sum(event["kind"] == "started" for event in suffix) == 1,
             "Unknown recovery role or renewed reservation")
    _require(read_json(safe_path(root, OUTPUT_ROOT + "/attempts/" + aid + ".reservation.json")) == {"event_sha256": start["sha256"]},
             "Recovery reservation seal changed")
    policy_sha = resources._digest(context["policy"])
    policy_path = OUTPUT_ROOT + "/attempts/" + aid + ".monitoring_policy.json"
    _require(monitor._read_record(safe_path(root, policy_path)) == {"policy": context["policy"], "sha256": policy_sha},
             "Monitor policy differs from the reviewed recovery")
    samples = [event for event in suffix if event["kind"] == "sample"]
    latest = None
    for sample in samples:
        _require(sample["monitoring_policy_sha256"] == policy_sha
                 and all(type(sample[key]) is int and sample[key] >= 0
                         for key in ("memory_bytes", "scanner_memory_bytes", "free_disk_bytes"))
                 and type(sample["elapsed_seconds"]) in (int, float) and math.isfinite(sample["elapsed_seconds"])
                 and 0 <= sample["elapsed_seconds"] <= start["reserved_seconds"]
                 and sample["scanner_memory_bytes"] <= sample["memory_bytes"] <= context["policy"]["maximum_combined_rss_bytes"]
                 and sample["free_disk_bytes"] >= context["policy"]["effective_minimum_free_disk_bytes"],
                 "Recovery sample violated safety or policy bounds")
        scan = sample["scan"]
        if scan is None:
            _require(latest is None and sample["output_bytes"] is None, "Missing scan cannot replace a completed measurement")
        else:
            _scan_record(scan, policy_sha)
            _require(sample["output_bytes"] == scan["output_bytes"] <= context["policy"]["maximum_output_bytes"],
                     "Resource sample differs from complete accounting")
            if latest is not None:
                _require(scan == latest or scan["requested_at"] >= latest["completed_at"], "Accounting results moved backwards or overlapped")
            latest = scan
    if phase == "worker":
        _require(aid == os.environ.get("BALL_RETENTION_ATTEMPT_ID") and end is None
                 and all(event["kind"] in ("started", "sample") for event in suffix), "Worker does not own the sole active reservation")
    else:
        _require(end is not None and suffix[-1] == end, "Incomplete or failed recovery cannot release a summary")
        _successful_completion(end, context, start["reserved_seconds"])
        counts = [sample["output_bytes"] for sample in samples if sample["output_bytes"] is not None]
        _require(samples and counts and end["monitor_samples"] == len(samples)
                 and end["peak_worker_memory_bytes"] >= max(sample["memory_bytes"] for sample in samples)
                 and end["maximum_output_bytes"] >= max(counts)
                 and end["minimum_free_disk_bytes"] <= min(sample["free_disk_bytes"] for sample in samples)
                 and end["worker_result"]["path"] == "attempts/" + aid + ".result.json"
                 and end["monitoring_policy_path"] == "attempts/" + aid + ".monitoring_policy.json",
                 "Completed recovery understates its evidence or names another receipt")
        _require(read_json(safe_path(root, OUTPUT_ROOT + "/attempts/" + aid + ".completion.json")) == {"event_sha256": end["sha256"]},
                 "Recovery completion seal changed")
    return journal


def _preserved_metadata(root, context, phase="before", allow_outputs=False):
    """Only lstat/traversal of scientific paths; never open/hash their bodies."""
    _require(phase in ("before", "worker", "completed"), "Unknown preservation phase")
    root, output = Path(root).resolve(), context["output_root"]
    history = context["history"]
    rows = history["preserved_files"]
    old_files = {row["path"] for row in rows}
    old_dirs = set(history["preserved_directories"])
    _require(len(old_files) == len(rows) and len(old_dirs) == len(history["preserved_directories"]), "Repeated preservation metadata")
    for row in rows:
        _require(_stat_metadata(safe_path(root, row["path"], OUTPUT_ROOT)) ==
                 {key: row[key] for key in ("size_bytes", "mtime_ns", "device", "inode")},
                 "Preserved evidence metadata changed: " + row["path"])
    for name in old_dirs:
        path = safe_path(root, name) if name == OUTPUT_ROOT else safe_path(root, name, OUTPUT_ROOT)
        _require(path.is_dir(), "Preserved directory disappeared")
    legacy._protected_metadata(root, context["original_context"]["protection"])
    aid = os.environ.get("BALL_RETENTION_ATTEMPT_ID") if phase == "worker" else context.get("completed_attempt_id")
    for name in history["preserved_absent_paths"]:
        if phase != "before" and name == OUTPUT_ROOT + "/supervisor.lock":
            continue
        if allow_outputs and name == OUTPUT_ROOT + "/" + OUTPUT_DIR:
            continue
        _absent(safe_path(root, name))
    if phase == "before":
        _require(aid is None, "Before phase cannot adopt an attempt")
    else:
        _require(type(aid) is str and re.fullmatch(r"[0-9a-f]{32}", aid), "Invalid recovery attempt identity")
    if phase == "worker":
        owner = monitor._read_record(output / "supervisor.lock")
        _require(owner["pid"] == int(os.environ["BALL_RETENTION_PARENT_PID"]), "Worker supervisor ownership changed")
    elif phase == "completed":
        _absent(output / "supervisor.lock")
    destination = output / OUTPUT_DIR
    if not allow_outputs:
        _absent(destination)
    permitted_files = {OUTPUT_ROOT + "/" + path for path in OUTPUTS} if allow_outputs else set()
    permitted_dirs = {OUTPUT_ROOT + "/" + OUTPUT_DIR} if allow_outputs else set()
    if aid:
        base = OUTPUT_ROOT + "/attempts/" + aid
        permitted_files |= {base + suffix for suffix in (".reservation.json", ".completion.json", ".log", ".start",
                                                            ".result.json", ".monitoring_policy.json")}
        permitted_dirs |= {base + ".temp", base + ".monitor"}
    if phase == "worker":
        permitted_files.add(OUTPUT_ROOT + "/supervisor.lock")

    def dynamic(name):
        if phase == "before":
            return False
        relative = name.removeprefix(OUTPUT_ROOT + "/resource_events/")
        event = re.fullmatch(r"(\d{8})\.json", relative)
        if event is None and phase == "worker":
            event = re.fullmatch(r"\.pending_(\d{8})\.json_[0-9a-f]{32}", relative)
        if name.startswith(OUTPUT_ROOT + "/resource_events/") and event:
            return int(event[1]) >= PREFIX_COUNT
        prefix = OUTPUT_ROOT + "/attempts/" + aid + ".monitor/"
        if name.startswith(prefix):
            leaf = name[len(prefix):]
            if leaf == "owned.start" or re.fullmatch(r"\d{6}\.(request|response)\.json", leaf):
                return True
            return phase == "worker" and re.fullmatch(r"\.pending_\d{6}\.(request|response)\.json_[0-9a-f]{32}", leaf) is not None
        return False

    def fail(error):
        raise error

    for folder, directories, files in os.walk(output, onerror=fail):
        for name in directories:
            relative = (Path(folder) / name).relative_to(root).as_posix()
            safe_path(root, relative)
            _require(relative in old_dirs | permitted_dirs, "Unexpected evidence directory: " + relative)
        for name in files:
            relative = (Path(folder) / name).relative_to(root).as_posix()
            safe_path(root, relative)
            _require(relative in old_files | permitted_files or dynamic(relative), "Unexpected evidence file: " + relative)


def _run_bounded_supervised(context, command):
    return monitor.run_supervised(context["output_root"], UNIT_KEY, command, context["limits"],
                                  cwd=context["root"], selection_unit=False, poll_seconds=.25,
                                  require_result=True, journal_factory=RecoveryJournal)


def _worker(root, manifest_path):
    resources.wait_for_supervisor()
    root = Path(root).resolve()
    context = _metadata(root, manifest_path, True)
    journal = verify_history(root, context, "worker")
    aid = os.environ["BALL_RETENTION_ATTEMPT_ID"]
    result_path = safe_path(root, OUTPUT_ROOT + "/attempts/" + aid + ".result.json")
    _require(Path(os.environ["BALL_RETENTION_RESULT_PATH"]).resolve() == result_path, "Worker receipt belongs to another reservation")
    _absent(result_path)
    _preserved_metadata(root, context, "worker")
    audit = legacy._load_scientific_json(root, context, "audit")
    _require(audit["schema_version"] == "ball_crop_retention_independent_publication_recovery_audit/v0.1"
             and audit["status"] == "passed" and audit["execution_code_commit"] == legacy.PUBLICATION_COMMIT,
             "The exact passed scientific audit is required")
    from .crop_retention_error_breakdown_summary import extract_pool, build_summary
    pools = []
    for key, purpose in (("representative_pool", "representative_evaluation"), ("challenge_pool", "challenge_evaluation")):
        pool = legacy._load_scientific_json(root, context, key)
        _require(pool.get("purpose") == purpose, "Scientific pool purpose changed")
        extracted = extract_pool(pool, audit)
        _require(extracted.get("purpose") == purpose and extracted.get("source_input") == key, "Copied pool provenance changed")
        pools.append(extracted)
        del pool
        gc.collect()
    summary, text = build_summary(pools)
    _require(type(summary) is dict and type(text) is str
             and summary.get("schema_version") == "ball_crop_retention_post_review_error_breakdown/v0.1"
             and type(summary.get("source_map")) is list and bool(summary["source_map"])
             and all(key in summary and summary[key] is None for key in ("selected_method", "selected_operating_point", "quality_gate")),
             "Recovery summary changed the unchanged formatter contract")
    text_bytes = text.encode("utf-8")
    _require(0 < len(text_bytes) <= MAX_SUMMARY_BYTES, "Summary transport exceeds its approved byte bound")
    destination = safe_path(root, OUTPUT_ROOT + "/" + OUTPUT_DIR)
    _absent(destination)
    destination.mkdir()
    summary_bytes = legacy._json_bytes(summary)
    legacy._write_new(destination / "breakdown.json", summary_bytes)
    legacy._write_new(destination / "summary.md", text_bytes)
    summary_bindings = [file_binding(root, destination / name) for name in ("breakdown.json", "summary.md")]
    provenance = {
        "schema_version": "ball_crop_candidate_retention_error_breakdown_recovery_provenance/v0.1",
        "recovery_id": ID, "unit_key": UNIT_KEY, "attempt_id": aid, "commit": context["commit"],
        "spec_sha256": context["spec_sha256"], "authority_bindings": {key: context["manifest"][key] for key in AUTHORITY_FIELDS},
        "implementation_validation": context["manifest"]["implementation_validation"],
        "post_commit_checkpoint": file_binding(root, root / POST_COMMIT_PATH),
        "source_bindings": context["certificate"]["source_bindings"], "scientific_inputs": SCIENTIFIC_INPUTS,
        "summary_bindings": summary_bindings, "source_map": summary["source_map"],
        "frozen_prefix_count": PREFIX_COUNT, "frozen_prefix_tip_sha256": PREFIX_TIP,
        "preserved_failed_attempt_id": FAILED_ATTEMPT,
        "active_reservation_sha256": journal._attempts()[aid]["start"]["sha256"],
        "monitoring_policy_sha256": resources._digest(context["policy"]), "checks": CHECKS,
        "acceptance": "Requires successful supervisor completion, unchanged preservation and verified bounded transport.",
    }
    provenance_bytes = legacy._json_bytes(provenance)
    legacy._write_new(destination / "provenance.json", provenance_bytes)
    authored = {"breakdown.json": summary_bytes, "summary.md": text_bytes, "provenance.json": provenance_bytes}
    _require(all((destination / name).read_bytes() == payload for name, payload in authored.items()), "Authored recovery output differs")
    end_context = _metadata(root, manifest_path, True)
    _require(end_context["commit"] == context["commit"] and end_context["spec_sha256"] == context["spec_sha256"],
             "Recovery execution authority changed during worker execution")
    for key in SCIENTIFIC_INPUTS:
        legacy._verify_scientific_input(root, end_context, key)
    verify_history(root, end_context, "worker")
    _preserved_metadata(root, end_context, "worker", allow_outputs=True)
    artifacts = [file_binding(root, destination / name) for name in authored]
    _require(all(row["sha256"] == hashlib.sha256(authored[Path(row["path"]).name]).hexdigest() for row in artifacts),
             "Recovery artifact changed during worker verification")
    result = {
        "schema_version": "ball_crop_candidate_retention_error_breakdown_recovery_worker_result/v0.1",
        "stage": "summarize", "unit_key": UNIT_KEY, "attempt_id": aid, "commit": context["commit"],
        "spec_sha256": context["spec_sha256"], "artifacts": artifacts,
        "artifact_metadata": [{"path": row["path"], **_stat_metadata(root / row["path"])} for row in artifacts],
        "scientific_inputs": SCIENTIFIC_INPUTS, "checks": CHECKS,
        "summary_payload": {"text": text, "size_bytes": len(text_bytes), "sha256": hashlib.sha256(text_bytes).hexdigest()},
    }
    payload = legacy._json_bytes(result)
    _require(len(payload) <= monitor.WORKER_RECEIPT_LIMIT, "Worker receipt exceeds the monitor interface bound")
    legacy._write_new(result_path, payload)
    _require(result_path.read_bytes() == payload, "Recovery worker receipt differs")
    return {"worker_result_written": True, "attempt_id": aid, "completion_pending": True}


def _completed_result(root, context, event):
    root = Path(root).resolve()
    journal = verify_history(root, context, "completed")
    _require(journal.events[-1] == event, "Supervisor completion differs from its persisted event")
    aid = event["attempt_id"]
    context = {**context, "completed_attempt_id": aid}
    _preserved_metadata(root, context, "completed", allow_outputs=True)
    binding = {"path": OUTPUT_ROOT + "/" + event["worker_result"]["path"], "sha256": event["worker_result"]["sha256"]}
    _require(binding["path"] == OUTPUT_ROOT + "/attempts/" + aid + ".result.json", "Wrong recovery receipt path")
    result = _read_bound(root, binding, monitor.WORKER_RECEIPT_LIMIT)
    _require(set(result) == {"schema_version", "stage", "unit_key", "attempt_id", "commit", "spec_sha256",
                             "artifacts", "artifact_metadata", "scientific_inputs", "checks", "summary_payload"}
             and result["schema_version"] == "ball_crop_candidate_retention_error_breakdown_recovery_worker_result/v0.1"
             and result["stage"] == "summarize" and result["unit_key"] == UNIT_KEY and result["attempt_id"] == aid
             and result["commit"] == context["commit"] and result["spec_sha256"] == context["spec_sha256"]
             and result["scientific_inputs"] == SCIENTIFIC_INPUTS and result["checks"] == CHECKS
             and all(type(value) is bool for value in result["checks"].values()),
             "Recovery worker receipt does not certify this exact execution")
    expected = {OUTPUT_ROOT + "/" + path for path in OUTPUTS}
    legacy._unique_bindings(result["artifacts"])
    _require(len(result["artifacts"]) == 3 and {row["path"] for row in result["artifacts"]} == expected,
             "Recovery artifact identities changed")
    rows = result["artifact_metadata"]
    _require(type(rows) is list and len(rows) == 3 and {row["path"] for row in rows} == expected, "Incomplete artifact metadata")
    for row in rows:
        _require(set(row) == {"path", "size_bytes", "mtime_ns", "device", "inode"}
                 and _stat_metadata(safe_path(root, row["path"])) == {key: row[key] for key in row if key != "path"},
                 "Recovery artifact metadata changed after worker verification")
    payload = result["summary_payload"]
    _require(type(payload) is dict and set(payload) == {"text", "size_bytes", "sha256"}
             and type(payload["text"]) is str and type(payload["size_bytes"]) is int,
             "Invalid bounded recovery summary transport")
    text_bytes = payload["text"].encode("utf-8")
    summary_path = OUTPUT_ROOT + "/" + OUTPUT_DIR + "/summary.md"
    _require(0 < len(text_bytes) <= MAX_SUMMARY_BYTES and len(text_bytes) == payload["size_bytes"]
             and hashlib.sha256(text_bytes).hexdigest() == payload["sha256"]
             and next(row["sha256"] for row in result["artifacts"] if row["path"] == summary_path) == payload["sha256"]
             and next(row["size_bytes"] for row in rows if row["path"] == summary_path) == len(text_bytes),
             "Returned summary is not the bounded receipted artifact")
    # Never follow artifact/source_map pointers or open scientific output bodies.
    return {"stage": "summarize", "successful_workers": 1, "commit": context["commit"],
            "worker_result": binding, "completion_event_sha256": event["sha256"], "artifacts": result["artifacts"],
            "summary": payload["text"], "new_model_calls": 0, "scoring_executed": False, "media_decoded": False,
            "selected_method": None, "selected_operating_point": None, "quality_gate": None}


def run_error_breakdown_recovery(root, manifest_path, dry_run=False):
    # Even a public dry-run requires the real post-commit gate. Development
    # tests call private clauses on fabricated metadata instead of real history.
    context = _metadata(root, manifest_path, True)
    verify_history(root, context, "before")
    _preserved_metadata(root, context, "before")
    if dry_run:
        return {"dry_run": True, "metadata_only": True, "scientific_inputs_verified": False,
                "spec_sha256": context["spec_sha256"], "post_commit_checkpoint_verified": True}
    command = [sys.executable, "-B", "-m", "src.ball_tracking.crop_retention_error_breakdown_recovery",
               "--manifest", str(context["manifest_path"]), "--repository-root", str(context["root"]), "--worker"]
    event = _run_bounded_supervised(context, command)
    end_context = _metadata(root, manifest_path, True)
    _require(end_context["commit"] == context["commit"] and end_context["spec_sha256"] == context["spec_sha256"],
             "Recovery authority changed before parent summary release")
    return _completed_result(root, end_context, event)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--stage", choices=("summarize",), default="summarize")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    _require(not (args.worker and args.dry_run), "An owned worker cannot use dry-run authority")
    root = args.repository_root.resolve()
    manifest = root / args.manifest
    result = _worker(root, manifest) if args.worker else run_error_breakdown_recovery(root, manifest, args.dry_run)
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
