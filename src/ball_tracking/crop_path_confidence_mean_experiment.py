"""One phase-isolated mean-confidence comparison in an owned bounded worker.

The parent inspects source/admin bindings and filesystem metadata only. Existing
scientific bodies are opened only by the reserved worker's explicit access map.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

from . import crop_saved_decision_contrast as predecessor
from . import crop_retention_experiment as original
from . import crop_retention_monitor as monitor
from . import crop_retention_resources as resources
from .development_experiments import canonical_sha256, read_json, safe_path

legacy = predecessor.legacy
_require = legacy._require
verify_binding = legacy.verify_binding
file_binding = legacy.file_binding
_absent = legacy._absent
_stat_metadata = legacy._stat_metadata
BudgetJournal = resources.BudgetJournal
ID = "rfdetr_medium_crop_path_confidence_mean_v0_1"
MANIFEST_PATH = "configs/ball_tracking/crop_retention_experiments/" + ID + ".json"
APPROVAL_PATH = "configs/ball_tracking/reviews/rfdetr_medium_crop_path_confidence_mean_approval_v0_1.json"
PROPOSAL_PATH = "docs/ball_crop_path_confidence_mean_proposal.md"
PROPOSAL_SHA = "e93d9df6b22946820754b59f99117991c6afad1c40dc3a8543fda588e4d7e3f2"
SCOPE_PATH = "configs/ball_tracking/proposals/" + ID + ".json"
SCOPE_SHA = "48577fb837806b3bf96eb9bacc613167bfcde5807706571fa63cd0a76cb61737"
APPROVAL_SHA = "071e21ae651d28067e1ad5d8de3378d38bcf5615cf491f97c106af9914fc81e8"
IMPLEMENTATION_DIR = "data/outputs/t/mean_impl_10e5fcb90f51"
CERTIFICATE_PATH = IMPLEMENTATION_DIR + "/implementation_validation.json"
POST_COMMIT_PATH = IMPLEMENTATION_DIR + "/post_commit_execution_checkpoint.json"
FROZEN_HISTORY_PATH = IMPLEMENTATION_DIR + "/frozen_history.json"
FROZEN_HISTORY_SHA = "010f3c3f31df54becd664e3c30938eb82413cd703add939874c4f8ef63d9ad52"
PREDECESSOR_COMPLETION_PATH = predecessor.IMPLEMENTATION_DIR + "/saved_decision_contrast_completion_26242d13a5a9.json"
BASE_COMMIT = "10e5fcb90f51909891d5df08d0b84ea5932a4033"
OUTPUT_ROOT = predecessor.OUTPUT_ROOT
OUTPUT_DIR = "audit/path_confidence_mean_v0_1"
UNIT_KEY = "path-confidence-mean:study:"
PREFIX_COUNT = 3221
PREFIX_ATTEMPTS = 62
PREFIX_TIP = "237f3149eada122733f339fb6e3a283c71c8d0e4bd619c54b814c5f2053e451a"
PREDECESSOR_ATTEMPT = "9b7ad2e59c67420ea70e0a2be8b7767d"
PREDECESSOR_RESULT_SHA = "94773c4c4c22ae7bf99b5de088ef6299104678e84c10028efa3dffdd396c1fdb"
USED_SECONDS = 3448.804999999984
MAX_UNIT_SECONDS = 1200
MAX_RETURN_BYTES = 512 * 1024
MAX_NEW_BYTES = 4 * 1024 ** 3
KNOWN_FAILURES = predecessor.KNOWN_FAILURES
HUMAN_ROOT = predecessor.HUMAN_ROOT
AUTHORITY_PATHS = {"proposal": PROPOSAL_PATH, "scope": SCOPE_PATH, "authorization": APPROVAL_PATH,
                   "frozen_history": FROZEN_HISTORY_PATH, "predecessor_completion": PREDECESSOR_COMPLETION_PATH,
                   "human_ledger": HUMAN_ROOT + "/human_review_0008.json",
                   "human_review_completion": HUMAN_ROOT + "/human_review_completion_v0_1.json"}
AUTHORITY_FIELDS = tuple(AUTHORITY_PATHS)
MANIFEST_FIELDS = {"schema_version", "study_id", "output_root", "output_dir", "permitted_stages", "unit_key",
                   "maximum_unit_seconds", *AUTHORITY_FIELDS, "implementation_validation", "post_commit_checkpoint",
                   "selected_method", "selected_operating_point", "quality_gate"}
MONITOR_EVIDENCE = predecessor.MONITOR_EVIDENCE
SEMANTIC_SOURCES = (*predecessor.SEMANTIC_SOURCES, "src/ball_tracking/crop_retention_monitor.py",
                    "src/ball_tracking/crop_retention_resources.py", "src/ball_tracking/crop_retention_experiment.py")
CHECKS = {key: True for key in (
    "source_authority_unchanged", "preserved_metadata_and_receipts_unchanged", "output_integrity_verified",
    "owned_worker_phase_allowlist_enforced", "all_six_selections_frozen_before_scoring",
    "saved_controls_copied_without_selector_or_evaluator_rerun", "only_176_declared_existing_inputs_read",
    "source_video_pointers_inert", "existing_human_judgments_unchanged", "validated_monitor_used",
    "clean_post_commit_checkpoint_verified", "six_final_frame_reviews_pending")}
_scan_record = predecessor._scan_record
_successful_completion = predecessor._successful_completion


def _pair(value):
    return predecessor._pair(value)


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _read_bound(root, binding, limit=32 * 1024 * 1024):
    """Read a fixed administrative authority or bounded worker receipt only."""
    _pair(binding)
    receipt = re.fullmatch(re.escape(OUTPUT_ROOT) + r"/attempts/[0-9a-f]{32}\.result\.json", binding["path"])
    _require(binding["path"] in {*AUTHORITY_PATHS.values(), CERTIFICATE_PATH} or receipt is not None,
             "Administrative reader refuses scientific and undeclared pointers")
    path = safe_path(root, binding["path"])
    before = _stat_metadata(path)
    _require(before["size_bytes"] <= limit, "Administrative input exceeds byte bound")
    with path.open("rb") as stream:
        payload = stream.read(limit + 1)
    _require(len(payload) <= limit and _stat_metadata(path) == before
             and hashlib.sha256(payload).hexdigest() == binding["sha256"], "Administrative binding changed")
    return json.loads(payload)


def _spec_sha256(manifest):
    return canonical_sha256({key: value for key, value in manifest.items() if key != "implementation_validation"})


def _output_names(scope):
    return [OUTPUT_DIR + "/" + row["path"] for row in scope["outputs"]["files"]]


def _validate_scope(scope):
    _require(scope["schema_version"] == "ball_crop_path_confidence_mean_scope/v0.1"
             and scope["study_id"] == ID and scope["prepared_at_commit"] == BASE_COMMIT
             and scope["status"] == "proposed_not_authorized" and scope["executable"] is False,
             "Exact frozen proposal scope is required")
    _require(len(scope["windows"]) == 6 and len(scope["existing_scientific_files"]) == 176
             and len({row["path"] for row in scope["existing_scientific_files"]}) == 176
             and len(scope["outputs"]["files"]) == 636
             and len({row["path"] for row in scope["outputs"]["files"]}) == 636
             and scope["outputs"]["directory"] == OUTPUT_ROOT + "/" + OUTPUT_DIR
             and scope["proposed_unit"]["key"] == UNIT_KEY
             and scope["proposed_unit"]["maximum_attempts"] == 1
             and scope["proposed_unit"]["maximum_charged_seconds"] == MAX_UNIT_SECONDS,
             "Window/input/output/attempt allowance changed")
    return scope


def _validate_manifest(manifest):
    _require(type(manifest) is dict and set(manifest) == MANIFEST_FIELDS
             and manifest["schema_version"] == "ball_crop_path_confidence_mean_experiment/v0.1"
             and manifest["study_id"] == ID and manifest["output_root"] == OUTPUT_ROOT
             and manifest["output_dir"] == OUTPUT_DIR and manifest["permitted_stages"] == ["study"]
             and manifest["unit_key"] == UNIT_KEY and manifest["maximum_unit_seconds"] == MAX_UNIT_SECONDS
             and manifest["post_commit_checkpoint"] == POST_COMMIT_PATH,
             "Unsupported mean-confidence experiment scope")
    _require(all(manifest[k] is None for k in ("selected_method", "selected_operating_point", "quality_gate")),
             "No method or quality gate selection authorized")
    for key, path in AUTHORITY_PATHS.items():
        _require(_pair(manifest[key])["path"] == path, "Unexpected administrative authority: " + key)
    for key, digest in (("proposal", PROPOSAL_SHA), ("scope", SCOPE_SHA), ("authorization", APPROVAL_SHA), ("frozen_history", FROZEN_HISTORY_SHA)):
        _require(manifest[key]["sha256"] == digest, "Approved authority changed: " + key)
    _require(_pair(manifest["implementation_validation"])["path"] == CERTIFICATE_PATH,
             "Wrong implementation certificate")


def _validate_implementation(root, manifest):
    certificate = _read_bound(root, manifest["implementation_validation"])
    _require(certificate["schema_version"] == "ball_crop_path_confidence_mean_implementation_validation/v0.1",
             "Unsupported implementation certificate")
    for key in ("focused_tests_passed", "full_suite_passed", "independent_static_review_passed",
                "integrity_tests_passed", "monitor_design_check_passed"):
        _require(certificate.get(key) is True, "Incomplete implementation validation: " + key)
    _require(certificate["manifest_spec_sha256"] == _spec_sha256(manifest)
             and certificate["authority_sha256"] == {key: manifest[key]["sha256"] for key in AUTHORITY_FIELDS},
             "Certificate does not bind the exact specification")
    required = {path.relative_to(root).as_posix() for folder in ("src", "tests")
                for path in (root / folder).rglob("*.py")} | {"requirements.txt"}
    rows = certificate["source_bindings"]
    legacy._unique_bindings(rows)
    _require({row["path"] for row in rows} == required, "Certificate source inventory is incomplete")
    for row in rows:
        verify_binding(root, row)
        original._git(root, "ls-files", "--error-unmatch", "--", row["path"])
    _require(bool(certificate["evidence_bindings"]), "Validation evidence is absent")
    legacy._unique_bindings(certificate["evidence_bindings"])
    for row in certificate["evidence_bindings"]:
        _require(row["path"] in MONITOR_EVIDENCE or row["path"].startswith(IMPLEMENTATION_DIR + "/"),
                 "Undeclared validation evidence")
        verify_binding(root, row)
    return certificate


def _post_commit_checkpoint(root, manifest, commit):
    path = safe_path(root, POST_COMMIT_PATH)
    _require(path.is_file(), "Post-commit checkpoint absent; execution is blocked")
    checkpoint = monitor._read_record(path)
    _require(checkpoint["schema_version"] == "ball_crop_path_confidence_mean_execution_checkpoint/v0.1"
             and commit != BASE_COMMIT and checkpoint["head"] == commit
             and checkpoint["branch"] == "codex/ball-detector-baseline"
             and checkpoint["manifest"] == file_binding(root, root / MANIFEST_PATH)
             and checkpoint["implementation_validation"] == manifest["implementation_validation"]
             and checkpoint["manifest_spec_sha256"] == _spec_sha256(manifest)
             and checkpoint["preserved_prefix_tip_sha256"] == PREFIX_TIP,
             "Post-commit checkpoint differs from this exact study")
    for key in ("execution_authorized", "clean", "index_empty", "validated_sources_unchanged"):
        _require(checkpoint.get(key) is True, "Execution prerequisite absent: " + key)
    _require(subprocess.run(["git", "merge-base", "--is-ancestor", BASE_COMMIT, commit], cwd=root).returncode == 0,
             "Execution must descend from the completed contrast")
    return checkpoint


def _metadata(root, manifest_path, require_clean=True):
    root = Path(root).resolve()
    _require(Path(manifest_path).absolute() == root / MANIFEST_PATH, "Unexpected manifest path")
    commit = original._clean_checkpoint(root) if require_clean else original._git(root, "rev-parse", "HEAD")
    manifest = read_json(safe_path(root, MANIFEST_PATH))
    _validate_manifest(manifest)
    checkpoint = _post_commit_checkpoint(root, manifest, commit) if require_clean else None
    for key in AUTHORITY_FIELDS:
        verify_binding(root, manifest[key])
    scope = _validate_scope(_read_bound(root, manifest["scope"]))
    approval = _read_bound(root, manifest["authorization"])
    _require(approval["schema_version"] == "ball_crop_path_confidence_mean_approval/v0.1"
             and approval["approved_by"].lower() == "ryan" and approval["proposal"] == manifest["proposal"]
             and approval["scope"] == manifest["scope"] and approval["maximum_new_attempts"] == 1
             and approval["maximum_unit_seconds"] == MAX_UNIT_SECONDS, "Exact study approval missing")
    for key in ("implementation_authorized", "focused_validation_authorized", "full_regression_authorized",
                "conditional_execution_authorized", "clean_commit_required", "responsive_monitor_policy_adopted",
                "staging_authorized_if_validation_passes", "committing_authorized_if_validation_passes"):
        _require(approval.get(key) is True, "Missing authorization: " + key)
    for key in ("parent_scientific_body_access_authorized", "parent_pixel_inspection_authorized",
                "automatic_scientific_retry_authorized", "new_inference_authorized",
                "historical_selector_or_evaluator_rerun_authorized", "push_pr_merge_authorized"):
        _require(approval.get(key) is False, "Approval expands scope: " + key)
    history = _read_bound(root, manifest["frozen_history"])
    _require(history["schema_version"] == "ball_crop_path_confidence_mean_frozen_history/v0.1"
             and history["head"] == BASE_COMMIT and history["prefix_count"] == PREFIX_COUNT
             and history["prefix_tip_sha256"] == PREFIX_TIP and history["prefix_attempts"] == PREFIX_ATTEMPTS
             and history["prefix_successes"] == 58 and set(history["known_failures"]) == KNOWN_FAILURES
             and history["scientific_bodies_read_or_hashed"] is False
             and math.isclose(history["consumed_seconds"], USED_SECONDS, abs_tol=1e-7, rel_tol=0),
             "Wrong completed-history authority")
    limits = history["limits"]
    # The original journal hashes bind every approved resource-limit field.
    _require(limits["maximum_cumulative_seconds"] == 14400, "Cumulative budget changed")
    prior = _read_bound(root, manifest["predecessor_completion"])
    _require(prior["success"] is True and prior["attempt_id"] == PREDECESSOR_ATTEMPT
             and prior["completion_event_chain_sha256"] == PREFIX_TIP,
             "Completed contrast receipt changed")
    ledger = _read_bound(root, manifest["human_ledger"])
    human = _read_bound(root, manifest["human_review_completion"])
    _require(human["review_complete"] is True and human["pending_frames"] == []
             and human["reviewed_frames"] == list(predecessor.FRAMES)
             and human["latest_ledger"] == manifest["human_ledger"], "Completed human reviews changed")
    certificate = _validate_implementation(root, manifest) if require_clean else None
    if require_clean:
        for name in (MANIFEST_PATH, *AUTHORITY_PATHS.values()):
            if not name.startswith("data/"):
                original._git(root, "ls-files", "--error-unmatch", "--", name)
        for name in SEMANTIC_SOURCES:
            _require(original._git(root, "rev-parse", BASE_COMMIT + ":" + name)
                     == original._git(root, "rev-parse", commit + ":" + name),
                     "Historical scientific/monitor semantics changed: " + name)
    _require(subprocess.run(["git", "check-ignore", "-q", "--", OUTPUT_ROOT + "/" + OUTPUT_DIR + "/summary.json"], cwd=root).returncode == 0,
             "Study outputs must stay ignored")
    return {"root": root, "manifest_path": root / MANIFEST_PATH, "manifest": manifest, "commit": commit,
            "spec_sha256": _spec_sha256(manifest), "output_root": safe_path(root, OUTPUT_ROOT),
            "limits": limits, "history": history, "scope": scope, "certificate": certificate,
            "human_ledger": ledger, "human_review_completion": human, "checkpoint": checkpoint,
            "policy": monitor.monitoring_policy(limits, .25)}


def _remaining_seconds(journal):
    return min(MAX_UNIT_SECONDS - journal.consumed(UNIT_KEY),
               journal.limits["maximum_cumulative_seconds"] - journal.consumed())


def _closed_prefix(journal):
    _require(len(journal.events) >= PREFIX_COUNT and journal.events[PREFIX_COUNT - 1]["sha256"] == PREFIX_TIP,
             "Exact completed 3221-event prefix required")
    old_starts, _ = predecessor._closed_prefix(journal)
    frozen = journal.events[:PREFIX_COUNT]
    starts = {e["attempt_id"]: e for e in frozen if e["kind"] == "started"}
    ends = {e["attempt_id"]: e for e in frozen if e["kind"] == "finished"}
    _require(len(starts) == len(ends) == PREFIX_ATTEMPTS and set(starts) == set(ends)
             and set(starts) - set(old_starts) == {PREDECESSOR_ATTEMPT}
             and {aid for aid, e in ends.items() if not e["success"]} == KNOWN_FAILURES
             and sum(e["success"] is True for e in ends.values()) == 58
             and starts[PREDECESSOR_ATTEMPT]["unit_key"] == predecessor.UNIT_KEY
             and frozen[-1] == ends[PREDECESSOR_ATTEMPT]
             and math.isclose(sum(e["elapsed_seconds"] for e in ends.values()), USED_SECONDS, abs_tol=1e-7, rel_tol=0),
             "Completed history or consumed budgets changed")
    _successful_completion(ends[PREDECESSOR_ATTEMPT],
                           {"limits": journal.limits, "policy": monitor.monitoring_policy(journal.limits, .25)},
                           starts[PREDECESSOR_ATTEMPT]["reserved_seconds"])
    _require(ends[PREDECESSOR_ATTEMPT]["worker_result"] == {
        "path": "attempts/" + PREDECESSOR_ATTEMPT + ".result.json", "sha256": PREDECESSOR_RESULT_SHA},
        "Successful contrast receipt changed")
    return starts, ends


class MeanJournal(BudgetJournal):
    """One 1200-second study with a stricter additive four-GiB byte ceiling."""
    def __init__(self, output_root, limits, *, baseline_bytes=0):
        self.baseline_bytes = baseline_bytes
        super().__init__(output_root, limits)

    def append(self, kind, **details):
        measured = details.get("output_bytes") if kind == "sample" else details.get("final_accounting_output_bound_bytes")
        extra = monitor.FINAL_RESERVE if kind == "sample" else 0
        exceeds = measured is not None and measured - self.baseline_bytes + extra > MAX_NEW_BYTES
        if exceeds and kind == "sample":
            # Preserve the violating observation before stopping the owned worker.
            super().append(kind, **details)
            raise resources.ResourceLimitError("New study bytes exceeded four GiB including administrative files")
        if exceeds and kind == "finished":
            details.update(success=False, failure=details.get("failure") or "New study bytes exceeded four GiB")
        return super().append(kind, **details)

    def reserve(self, unit_key, selection_unit):
        _require(unit_key == UNIT_KEY and selection_unit is False, "Unknown study reservation")
        _require(len(self.events) == PREFIX_COUNT, "Consumed attempt cannot retry or adopt a suffix")
        _closed_prefix(self)
        _require(all(a["finished"] is not None for a in self._attempts().values()), "An attempt is active")
        remaining = _remaining_seconds(self)
        _require(remaining > 0, "Study allowance exhausted")
        aid = uuid.uuid4().hex
        self.append("started", attempt_id=aid, unit_key=UNIT_KEY, selection_unit=False, reserved_seconds=remaining)
        resources._write_new(self.root / "attempts" / (aid + ".reservation.json"), {"event_sha256": self.events[-1]["sha256"]})
        return aid, remaining


def verify_history(root, context, phase="before"):
    _require(phase in ("before", "worker", "completed"), "Unknown study history phase")
    root, output = Path(root).resolve(), context["output_root"]
    history = context["history"]
    journal = BudgetJournal(output, context["limits"])
    starts, ends = _closed_prefix(journal)
    _require(history["prior_saved_decision_contrast_completion"] == ends[PREDECESSOR_ATTEMPT], "Preserved completion changed")
    rows = history["raw_event_bindings"]
    legacy._unique_bindings(rows)
    _require(len(rows) == PREFIX_COUNT, "Incomplete frozen raw history")
    for index, b in enumerate(rows):
        _require(b["path"] == OUTPUT_ROOT + f"/resource_events/{index:08d}.json", "Noncontiguous prefix binding")
        verify_binding(root, b)
    seals = history["administrative_attempt_bindings"]
    legacy._unique_bindings(seals)
    expected = {OUTPUT_ROOT + "/attempts/" + aid + suffix for aid in starts
                for suffix in (".reservation.json", ".completion.json")}
    expected |= {OUTPUT_ROOT + "/attempts/" + aid + ".result.json" for aid in starts if ends[aid]["success"]}
    _require({b["path"] for b in seals} == expected, "Administrative receipt inventory changed")
    for b in seals:
        verify_binding(root, b)
    for aid in starts:
        for suffix, event in ((".reservation.json", starts[aid]), (".completion.json", ends[aid])):
            _require(read_json(safe_path(root, OUTPUT_ROOT + "/attempts/" + aid + suffix)) == {"event_sha256": event["sha256"]},
                     "Preserved attempt seal changed")
        if ends[aid]["success"]:
            receipt = next(b for b in seals if b["path"] == OUTPUT_ROOT + "/attempts/" + aid + ".result.json")
            _require(ends[aid]["worker_result"] == {"path": "attempts/" + aid + ".result.json", "sha256": receipt["sha256"]},
                     "Preserved successful receipt identity changed")
        else:
            _require(ends[aid]["worker_result"] is None, "Failed attempt acquired a result")
            _absent(output / "attempts" / (aid + ".result.json"))
    human = history["human_review_bindings"]
    legacy._unique_bindings(human)
    expected_human = {HUMAN_ROOT + f"/human_review_{i:04d}.json" for i in range(1, 9)}
    expected_human.add(HUMAN_ROOT + "/human_review_completion_v0_1.json")
    _require({row["path"] for row in human} == expected_human, "Completed human record inventory changed")
    for row in human:
        verify_binding(root, row)
    suffix = journal.events[PREFIX_COUNT:]
    attempts = journal._attempts()
    new = {aid: value for aid, value in attempts.items() if aid not in starts}
    if phase == "before":
        _require(not suffix and not new and all(row["finished"] is not None for row in attempts.values()),
                 "Path-confidence mean requires the untouched completed prefix; no retry or unknown suffix")
        return journal
    _require(len(new) == 1 and suffix and suffix[0]["kind"] == "started", "Exactly one owned path-confidence mean attempt is required")
    aid, attempt = next(iter(new.items()))
    start, end = attempt["start"], attempt["finished"]
    expected_seconds = min(MAX_UNIT_SECONDS, context["limits"]["maximum_cumulative_seconds"] - USED_SECONDS)
    _require(start["unit_key"] == UNIT_KEY and start["selection_unit"] is False
             and math.isclose(start["reserved_seconds"], expected_seconds, rel_tol=0, abs_tol=1e-7)
             and all(event["attempt_id"] == aid for event in suffix)
             and sum(event["kind"] == "started" for event in suffix) == 1,
             "Unknown path-confidence mean role or renewed reservation")
    _require(read_json(safe_path(root, OUTPUT_ROOT + "/attempts/" + aid + ".reservation.json")) == {"event_sha256": start["sha256"]},
             "Path-confidence mean reservation seal changed")
    policy_sha = resources._digest(context["policy"])
    policy_path = OUTPUT_ROOT + "/attempts/" + aid + ".monitoring_policy.json"
    _require(monitor._read_record(safe_path(root, policy_path)) == {"policy": context["policy"], "sha256": policy_sha},
             "Monitor policy differs from the adopted responsive policy")
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
                 "Path-confidence mean sample violated safety or policy bounds")
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
        _require(end is not None and suffix[-1] == end, "Incomplete or failed path-confidence mean attempt cannot release a review")
        _successful_completion(end, context, start["reserved_seconds"])
        counts = [sample["output_bytes"] for sample in samples if sample["output_bytes"] is not None]
        _require(samples and counts and end["monitor_samples"] == len(samples)
                 and end["peak_worker_memory_bytes"] >= max(sample["memory_bytes"] for sample in samples)
                 and end["maximum_output_bytes"] >= max(counts)
                 and end["minimum_free_disk_bytes"] <= min(sample["free_disk_bytes"] for sample in samples)
                 and end["worker_result"]["path"] == "attempts/" + aid + ".result.json"
                 and end["monitoring_policy_path"] == "attempts/" + aid + ".monitoring_policy.json",
                 "Completed path-confidence mean attempt understates its evidence or names another receipt")
        _require(read_json(safe_path(root, OUTPUT_ROOT + "/attempts/" + aid + ".completion.json")) == {"event_sha256": end["sha256"]},
                 "Path-confidence mean completion seal changed")
    return journal


def _input_metadata(root, inputs, rows):
    expected = {row["path"]: row for row in inputs}
    _require(len(expected) == len(inputs) and len(rows) == len(inputs)
             and {row["path"] for row in rows} == set(expected), "Incomplete scientific metadata inventory")
    result = {}
    for row in rows:
        _require(set(row) == {"path", "size_bytes", "mtime_ns", "device", "inode"}, "Invalid metadata row")
        actual = _stat_metadata(safe_path(root, row["path"]))
        _require(actual == {key: row[key] for key in row if key != "path"}
                 and actual["size_bytes"] == expected[row["path"]]["size_bytes"], "Scientific input metadata changed")
        result[row["path"]] = actual
    return result


def _preserved_metadata(root, context, phase="before", allow_outputs=False):
    """Only lstat/traversal of scientific paths; never open/hash their bodies."""
    _require(phase in ("before", "worker", "completed"), "Unknown preservation phase")
    root, output = Path(root).resolve(), context["output_root"]
    history = context["history"]
    _input_metadata(root, context["scope"]["existing_scientific_files"], history["scientific_input_metadata"])
    external = history["external_preserved_files"]
    _require(len(external) == 18 and len({row["path"] for row in external}) == 18,
             "The prior eighteen external metadata rows must remain preserved")
    for row in external:
        _require(_stat_metadata(safe_path(root, row["path"])) ==
                 {key: row[key] for key in ("size_bytes", "mtime_ns", "device", "inode")},
                 "Prior review image metadata changed")
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
    legacy._protected_metadata(root, context["history"]["protection"])
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
        _require(type(aid) is str and re.fullmatch(r"[0-9a-f]{32}", aid), "Invalid path-confidence mean attempt identity")
    if phase == "worker":
        owner = monitor._read_record(output / "supervisor.lock")
        _require(owner["pid"] == int(os.environ["BALL_RETENTION_PARENT_PID"]), "Worker supervisor ownership changed")
    elif phase == "completed":
        _absent(output / "supervisor.lock")
    destination = output / OUTPUT_DIR
    if not allow_outputs:
        _absent(destination)
    permitted_files = {OUTPUT_ROOT + "/" + path for path in _output_names(context["scope"])} if allow_outputs else set()
    permitted_dirs = set()
    if allow_outputs:
        for name in permitted_files:
            parent = Path(name).parent
            while parent.as_posix().startswith(OUTPUT_ROOT + "/" + OUTPUT_DIR):
                permitted_dirs.add(parent.as_posix())
                parent = parent.parent
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


class PhaseAccess:
    """Exact existing-file allowlist; no embedded pointer is a filesystem grant."""
    PHASES = {
        "selection": {"candidate_run"},
        "post_selection_comparison": {"candidate_run", "saved_control_observations", "reviewed_annotations", "saved_scoring_pool"},
        "rendering": {"candidate_run", "saved_control_observations", "reviewed_annotations", "source_png"},
    }

    def __init__(self, root, context):
        aid = os.environ.get("BALL_RETENTION_ATTEMPT_ID")
        _require(aid and context.get("current_attempt_id") == aid, "Scientific access requires owned reservation")
        self.root, self.context = Path(root).resolve(), context
        self.rows = {row["path"]: row for row in context["scope"]["existing_scientific_files"]}
        self.metadata = _input_metadata(root, list(self.rows.values()), context["history"]["scientific_input_metadata"])
        self.phase, self.opened, self.frozen = "selection", set(), None
        self.selection_content = {}

    def read(self, name):
        _require(os.environ.get("BALL_RETENTION_ATTEMPT_ID") == self.context["current_attempt_id"], "Worker ownership changed")
        _require(name in self.rows and self.rows[name]["role"] in self.PHASES[self.phase],
                 "Scientific path is undeclared or forbidden in this phase")
        row = self.rows[name]
        path = safe_path(self.root, name)
        before = _stat_metadata(path)
        _require(before == self.metadata[name], "Scientific input metadata changed before read")
        with path.open("rb") as stream:
            raw = stream.read(row["size_bytes"] + 1)
        _require(len(raw) == row["size_bytes"] and _stat_metadata(path) == before
                 and hashlib.sha256(raw).hexdigest() == row["sha256"], "Scientific bytes differ from approved binding")
        self.opened.add(name)
        return raw

    def json(self, name):
        _require(name in self.rows and self.rows[name]["role"] != "source_png", "Pixels cannot use JSON reader")
        return json.loads(self.read(name))

    def freeze(self, bindings, sink):
        expected = {f"selection/{w['window_id']}/observations.json" for w in self.context["scope"]["windows"]}
        _require(self.phase == "selection" and self.frozen is None and len(bindings) == 6,
                 "Selection freeze is single-use and needs all six outputs")
        actual = {row["path"].removeprefix(OUTPUT_ROOT + "/" + OUTPUT_DIR + "/") for row in bindings}
        _require(actual == expected, "Selection freeze omits or duplicates a window")
        sink.verify(bindings)
        self.frozen = deepcopy(bindings)
        sink.selection_frozen = True
        self.phase = "post_selection_comparison"

    def render(self, sink):
        _require(self.phase == "post_selection_comparison" and self.frozen is not None, "Rendering before selection freeze")
        sink.verify(self.frozen)
        self.phase = "rendering"


class OutputSink:
    """Create-only declared artifacts, verified publications and owned video temps."""
    def __init__(self, root, scope):
        self.root = Path(root).resolve()
        self.folder = safe_path(root, OUTPUT_ROOT + "/" + OUTPUT_DIR)
        _absent(self.folder)
        self.folder.mkdir()
        self.bounds = {row["path"]: row["maximum_bytes"] for row in scope["outputs"]["files"]}
        self.bindings, self.metadata, self.videos = {}, {}, {}
        self.selection_frozen = False
        self.total = 0

    def _target(self, relative):
        _require(relative in self.bounds and relative not in self.bindings, "Undeclared or existing artifact")
        _require(not (self.selection_frozen and relative.startswith("selection/")), "Frozen selections cannot be revised")
        target = safe_path(self.folder, relative)
        _absent(target)
        return target

    def write(self, relative, raw):
        target = self._target(relative)
        _require(type(raw) is bytes and 0 < len(raw) <= self.bounds[relative], "Artifact exceeds declared byte bound")
        _require(self.total + len(raw) + monitor.FINAL_RESERVE <= MAX_NEW_BYTES, "New artifact byte allowance exhausted")
        target.parent.mkdir(parents=True, exist_ok=True)
        legacy._write_new(target, raw)
        _require(target.read_bytes() == raw, "Create-only artifact serialization differs")
        binding = {"path": target.relative_to(self.root).as_posix(), "sha256": hashlib.sha256(raw).hexdigest()}
        self.bindings[relative] = binding
        self.metadata[relative] = {"path": binding["path"], **_stat_metadata(target)}
        self.total += len(raw)
        return deepcopy(binding)

    def json(self, relative, value):
        return self.write(relative, _json_bytes(value))

    def verify(self, bindings):
        for binding in bindings:
            relative = binding["path"].removeprefix(OUTPUT_ROOT + "/" + OUTPUT_DIR + "/")
            _require(relative in self.bindings and binding == self.bindings[relative], "Unknown new artifact binding")
            target = safe_path(self.folder, relative)
            _require(_stat_metadata(target) == {k: v for k, v in self.metadata[relative].items() if k != "path"},
                     "Published artifact metadata changed")
            verify_binding(self.root, binding)

    def open_video(self, relative, fps, size):
        import cv2
        self._target(relative)
        _require(relative.endswith("/comparison.mp4") and relative not in self.videos and fps == 5.0,
                 "Undeclared video or rate")
        temp = self.folder / "tmp" / (uuid.uuid4().hex + ".mp4")
        temp.parent.mkdir(exist_ok=True)
        _absent(temp)
        writer = cv2.VideoWriter(str(temp), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
        _require(writer.isOpened(), "Cannot open owned review video writer")
        self.videos[relative] = (temp, writer)
        return writer

    def verify_video(self, relative, count, fps, size):
        import cv2
        _require(relative in self.videos and count == 25 and fps == 5.0, "Unknown generated review video")
        path, writer = self.videos.pop(relative)
        writer.release()
        _require(0 < _stat_metadata(path)["size_bytes"] <= self.bounds[relative], "Generated video exceeds its bound")
        capture = cv2.VideoCapture(str(path))
        decoded = 0
        try:
            _require(capture.isOpened() and abs(capture.get(cv2.CAP_PROP_FPS) - fps) < .001, "Generated video FPS differs")
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                decoded += 1
                _require(decoded <= count and frame.shape[:2] == (size[1], size[0]), "Generated video geometry/count differs")
            _require(decoded == count, "Generated video has missing or extra frames")
        finally:
            capture.release()
        result = self.write(relative, path.read_bytes())
        path.unlink()  # Only this writer's UUID temporary is removed.
        if not self.videos:
            path.parent.rmdir()
        return result

    def complete(self):
        _require(not self.videos and set(self.bindings) == set(self.bounds), "Declared outputs incomplete or video still open")
        self.verify(list(self.bindings.values()))
        _require({p.relative_to(self.folder).as_posix() for p in self.folder.rglob("*") if p.is_file()} == set(self.bounds),
                 "Undeclared generated output or temporary remains")
        return list(self.bindings.values()), list(self.metadata.values())


def candidate_run(value, window):
    """Same validated candidate namespace as saved controls, with no file reads."""
    from .detections import BallDetectionRun
    from .tiled_candidates import combine_views
    _require(value["schema_version"] == "ball_tiled_candidates/v0.1"
             and value["content_sha256"] == canonical_sha256({"header": value["header"], "frames": value["frames"]}),
             "Candidate content contract mismatch")
    model = dict(value["header"]["per_view_model_provenance"])
    _require(model["code_commit"] == original.RF_COMMIT and model["export_confidence_floor"] == .01,
             "Original detector provenance changed")
    model.update(tiling_enabled=True, postprocessing_description=
                 "Four fixed overlapping crop union; global coordinate translation; all duplicates retained; no temporal filtering")
    declared = value["header"]["window"]
    _require(all(declared[key] == item for key, item in window.items() if key != "crop_candidates"),
             "Candidate window/source differs")
    payload = {"schema_version": "0.1", "detection_run_id": declared["detection_run_id"],
               "annotation_set_id": window["annotation_set_id"], "possession_id": window["possession_id"],
               "source_video": window["source_video"], "window": {k: window[k] for k in ("start_frame_index", "end_frame_index")},
               "model_provenance": model,
               "frames": [{"frame_index": f["frame_index"], "inference_status": "completed", "failure_reason": None,
                           "detections": [c["detection"] for c in f["candidates"]]} for f in value["frames"]]}
    run = BallDetectionRun.from_mapping(payload)
    _require(len(run.frames) == len(value["frames"]) == 25, "Expected full 25-frame candidate window")
    for stored, frame in zip(value["frames"], run.frames):
        _require(stored["model_calls"] == 4 and stored["frame_index"] == frame.frame_index
                 and combine_views(stored["views"], run.source_video, run.model_provenance) == stored["candidates"],
                 "Original crop-to-source candidate mapping changed")
    return run


def select_all(context, access, sink):
    """Six immutable outputs; no labels, saved reports or pixels in this phase."""
    from . import crop_path_confidence_mean as selector
    runs, observations, bindings = {}, {}, []
    config = selector.RankingConfig()
    for window in context["scope"]["windows"]:
        wid = window["window_id"]
        saved = access.json(window["crop_candidates"]["path"])
        run = candidate_run(saved, window)
        runs[wid] = run
        frames = []
        for full in selector.iter_ranked_frames(run):
            relative = f"selection/{wid}/audit/frame_{full['frame_index']:06d}.json"
            trace = sink.json(relative, full)
            compact = selector.summarize_frame(full)
            compact["trace_binding"] = trace
            frames.append(compact)
        _require([f["frame_index"] for f in frames] == [f.frame_index for f in run.frames], "Selection frame inventory differs")
        obs = {"schema_version": "ball_crop_path_confidence_mean_observations/v0.1", "variant_id": config.variant_id,
               "config": asdict(config), "ranking_code_commit": context["commit"], "detector_code_commit": original.RF_COMMIT,
               "input_candidate_content_sha256": canonical_sha256(run.to_dict()), "source_video": run.source_video.to_dict(),
               "window": run.window.to_dict(), "possession_id": run.possession_id, "frames": frames,
               "score_semantics": "Uncalibrated fixed-terminal-length binary64 mean confidence; no identity certainty",
               "selected_method": None, "selected_operating_point": None, "quality_gate": None}
        observations[wid] = obs
        access.selection_content[wid] = canonical_sha256(obs)
        bindings.append(sink.json(f"selection/{wid}/observations.json", {
            "schema_version": "ball_crop_path_confidence_mean_output/v0.1", "observations": obs,
            "observations_content_sha256": canonical_sha256(obs), "input_crop_file": window["crop_candidates"],
            "crop_content_sha256": saved["content_sha256"], "experiment_spec_sha256": context["spec_sha256"],
            "resource_attempt_id": context["current_attempt_id"]}))
    access.freeze(bindings, sink)
    sink.json("manifest.json", {"schema_version": "ball_crop_path_confidence_mean_selection_freeze/v0.1",
        "selection_bindings": bindings, "all_six_frozen_before_scoring": True,
        "attempt_id": context["current_attempt_id"], "commit": context["commit"], "spec_sha256": context["spec_sha256"]})
    return runs, observations


def compare_all(context, access, sink, runs, observations):
    from .annotations import BallAnnotationSet
    from . import crop_path_confidence_mean_evaluation as evaluation
    scope = context["scope"]
    reports, all_observations, all_labels, comparisons = {}, {}, {}, []
    # Whole pool bytes may be parsed only to extract these twelve fixed pointers.
    selected_saved = {}
    for item in (row for row in scope["existing_scientific_files"] if row["role"] == "saved_scoring_pool"):
        value = access.json(item["path"])
        for reference in (r for r in scope["saved_reports"] if r["source"]["path"] == item["path"]):
            pointer = reference["source"]["json_pointer"]
            _require(re.fullmatch(r"/evaluation_reports/\d+", pointer), "Only fixed saved report pointers may be extracted")
            selected_saved[(reference["window_id"], reference["config"]["arm"])] = deepcopy(value["evaluation_reports"][int(pointer.rsplit("/", 1)[1])])
        del value
    _require(len(selected_saved) == 12, "Incomplete saved report extraction")
    for window in scope["windows"]:
        wid, run = window["window_id"], runs[window["window_id"]]
        label_row = next(r for r in scope["existing_scientific_files"] if r["role"] == "reviewed_annotations" and r["window_id"] == wid)
        labels = BallAnnotationSet.from_mapping(access.json(label_row["path"]))
        by_arm = {evaluation.ARM: observations[wid]}
        for reference in (r for r in scope["saved_controls"] if r["window_id"] == wid):
            by_arm[reference["config"]["arm"]] = evaluation.verify_saved_observations(access.json(reference["file"]["path"]), reference, run)
        saved_reports = {}
        for reference in (r for r in scope["saved_reports"] if r["window_id"] == wid):
            arm = reference["config"]["arm"]
            saved_reports[arm] = evaluation.verify_saved_report(selected_saved[(wid, arm)], reference, by_arm[arm], run, labels)
        _require(canonical_sha256(observations[wid]) == access.selection_content[wid], "Frozen in-memory selection changed")
        new_report = evaluation.evaluate_unit(labels, run, observations[wid], context["commit"])
        comparisons.append(evaluation.compare_window(window, new_report, saved_reports, by_arm))
        reports[wid] = {evaluation.ARM: new_report, **saved_reports}
        all_observations[wid], all_labels[wid] = by_arm, labels
    pools = [evaluation.aggregate_pool([w for w in comparisons if w["purpose"] == purpose], purpose)
             for purpose in evaluation.POOLS]
    for pool in pools:
        purpose = pool["purpose"]
        sink.json(f"evaluation/{purpose}.json", {
            "schema_version": "ball_crop_path_confidence_mean_pool/v0.1", "comparison": pool,
            "new_evaluation_reports": [reports[w["window_id"]][evaluation.ARM] for w in scope["windows"] if w["purpose"] == purpose],
            "saved_report_references": [r for r in scope["saved_reports"] if r["purpose"] == purpose]})
    summary = {"schema_version": "ball_crop_path_confidence_mean_summary/v0.1", "windows": comparisons, "pools": pools,
               "interpretation": evaluation.development_interpretation(pools),
               "fixed_diagnostic": evaluation.diagnostic_rows(evaluation.DIAGNOSTIC_WINDOW,
                   all_observations[evaluation.DIAGNOSTIC_WINDOW], context["human_ledger"]["rows"]),
               "selected_method": None, "selected_operating_point": None, "quality_gate": None}
    return summary, reports, all_observations, all_labels


def render_all(context, access, sink, runs, reports, observations, labels):
    import cv2
    import numpy as np
    from . import crop_path_confidence_mean_review as review
    access.render(sink)
    indexes = []
    for window in context["scope"]["windows"]:
        wid = window["window_id"]
        sources = {row["frame_index"]: row for row in context["scope"]["existing_scientific_files"]
                   if row["role"] == "source_png" and row["window_id"] == wid}
        def read_source(index):
            _require(index in sources, "Undeclared source frame")
            pixels = cv2.imdecode(np.frombuffer(access.read(sources[index]["path"]), dtype=np.uint8), cv2.IMREAD_COLOR)
            _require(pixels is not None and pixels.shape == (window["source_video"]["height_px"], window["source_video"]["width_px"], 3),
                     "Bound source PNG geometry differs")
            return pixels
        from .crop_path_confidence_mean import ARM
        _require(canonical_sha256(observations[wid][ARM]) == access.selection_content[wid], "Selection changed after evaluation")
        result = review.render_window(window, runs[wid], labels[wid], observations[wid], reports[wid],
            read_source=read_source, write_bytes=sink.write, open_video=sink.open_video, verify_video=sink.verify_video)
        indexes.append({"window_id": wid, "index_binding": result["index_binding"],
                        "clip": OUTPUT_ROOT + "/" + OUTPUT_DIR + f"/review/{wid}/comparison.mp4",
                        "first_frame_index": window["start_frame_index"], "last_frame_index": window["end_frame_index"],
                        "frame_count": 25, "fps": 5, "human_review": "pending"})
    _require(access.opened == set(access.rows), "Scientific access inventory incomplete or expanded")
    return indexes


def _summary_text(summary):
    lines = ["Mean path confidence development comparison", "", summary["interpretation"]["label"] + ".",
             "All six new final-frame human reviews remain pending.", ""]
    for pool in summary["pools"]:
        lines.append(pool["purpose"] + ":")
        for arm, row in pool["totals"].items():
            lines.append("  " + arm + ": " + json.dumps(row["counts"], sort_keys=True))
        lines.append("  window regressions: " + json.dumps(pool["window_regressions"], sort_keys=True))
    lines += ["", "No method, operating point, production quality gate or holdout release is selected.",
              "Matched center distance does not certify object identity. Wrong-to-missing alone is not improvement."]
    return "\n".join(lines) + "\n"


def _run_bounded_supervised(context, command):
    baseline = sum(row["size_bytes"] for row in context["history"]["preserved_files"])
    def factory(output, limits):
        return MeanJournal(output, limits, baseline_bytes=baseline)
    return monitor.run_supervised(context["output_root"], UNIT_KEY, command, context["limits"],
                                  cwd=context["root"], selection_unit=False, poll_seconds=.25,
                                  require_result=True, journal_factory=factory)


def _worker(root, manifest_path):
    resources.wait_for_supervisor()
    root = Path(root).resolve()
    context = _metadata(root, manifest_path, True)
    journal = verify_history(root, context, "worker")
    aid = os.environ["BALL_RETENTION_ATTEMPT_ID"]
    context = {**context, "current_attempt_id": aid}
    result_path = safe_path(root, OUTPUT_ROOT + "/attempts/" + aid + ".result.json")
    _require(Path(os.environ["BALL_RETENTION_RESULT_PATH"]).resolve() == result_path, "Receipt outside owned reservation")
    _absent(result_path)
    _preserved_metadata(root, context, "worker")
    access = PhaseAccess(root, context)
    sink = OutputSink(root, context["scope"])
    runs, observations = select_all(context, access, sink)
    summary, reports, all_observations, labels = compare_all(context, access, sink, runs, observations)
    summary["reviews"] = render_all(context, access, sink, runs, reports, all_observations, labels)
    _require(len(_json_bytes(summary)) <= MAX_RETURN_BYTES, "Summary exceeds bounded interface; cannot truncate")
    sink.json("summary.json", summary)
    summary_text = _summary_text(summary)
    sink.write("summary.md", summary_text.encode("utf-8"))
    sink.json("provenance.json", {"schema_version": "ball_crop_path_confidence_mean_provenance/v0.1",
        "study_id": ID, "unit_key": UNIT_KEY, "attempt_id": aid, "commit": context["commit"],
        "spec_sha256": context["spec_sha256"], "authority_bindings": {k: context["manifest"][k] for k in AUTHORITY_FIELDS},
        "implementation_validation": context["manifest"]["implementation_validation"],
        "source_bindings": context["certificate"]["source_bindings"], "checks": CHECKS,
        "scientific_inputs": context["scope"]["existing_scientific_files"], "selection_freeze": access.frozen,
        "preserved_prefix_count": PREFIX_COUNT, "preserved_prefix_tip_sha256": PREFIX_TIP,
        "active_reservation_sha256": journal._attempts()[aid]["start"]["sha256"],
        "monitoring_policy_sha256": resources._digest(context["policy"]),
        "saved_control_provenance_retained": True, "artifacts_before_provenance": list(sink.bindings.values())})
    artifacts, metadata = sink.complete()
    end = _metadata(root, manifest_path, True)
    _require(end["commit"] == context["commit"] and end["spec_sha256"] == context["spec_sha256"], "Authority changed during study")
    verify_history(root, end, "worker")
    _preserved_metadata(root, end, "worker", allow_outputs=True)
    result = {"schema_version": "ball_crop_path_confidence_mean_worker_result/v0.1", "stage": "study",
        "unit_key": UNIT_KEY, "attempt_id": aid, "commit": context["commit"], "spec_sha256": context["spec_sha256"],
        "artifacts": artifacts, "artifact_metadata": metadata, "checks": CHECKS,
        "summary": summary, "summary_text": summary_text, "scientific_input_count": len(access.opened)}
    raw = _json_bytes(result)
    _require(len(raw) <= monitor.WORKER_RECEIPT_LIMIT, "Worker receipt exceeds one-MiB bound")
    legacy._write_new(result_path, raw)
    _require(result_path.read_bytes() == raw, "Worker receipt changed")
    return {"worker_result_written": True, "attempt_id": aid, "completion_pending": True}


def validate_bounded_summary(summary, context):
    """Reconcile returned accounting without scientific-file reads or scoring."""
    from . import crop_path_confidence_mean_evaluation as evaluation
    _require(type(summary) is dict and len(_json_bytes(summary)) <= MAX_RETURN_BYTES,
             "Bounded summary exceeds interface")
    windows = context["scope"]["windows"]
    _require([row["window_id"] for row in summary["windows"]] == [row["window_id"] for row in windows],
             "Summary windows changed or reordered")
    for declared, window in zip(windows, summary["windows"]):
        frames = list(range(declared["start_frame_index"], declared["end_frame_index"] + 1))
        hidden = set(range(165, 170)) if declared["possession_id"] == "possession_003" and declared["purpose"] == "challenge_evaluation" else set()
        _require(window["purpose"] == declared["purpose"] and window["possession_id"] == declared["possession_id"]
                 and window["first_frame"] == frames[0] and window["last_frame"] == frames[-1]
                 and window["startup_parity"] is True and set(window["summaries"]) == set(evaluation.ARMS),
                 "Window result identity differs")
        for arm in evaluation.ARMS:
            row = window["summaries"][arm]
            inventory = row["frame_indices"]
            keys = (*evaluation.STATES, *evaluation.HIDDEN_STATES, "ineligible")
            _require(set(inventory) == set(keys) and all(type(v) is list and v == sorted(set(v)) for v in inventory.values())
                     and sorted(f for values in inventory.values() for f in values) == frames,
                     "States do not form an exact source-frame partition")
            _require(row["counts"] == {k: len(inventory[k]) for k in keys}
                     and row["frame_denominator"] == 25
                     and row["eligible_denominator"] == 25 - len(hidden)
                     and row["hidden_denominator"] == len(hidden)
                     and not inventory["ineligible"]
                     and set(inventory["alarm"] + inventory["no_current_output"]) == hidden
                     and row["missed_eligible_count"] == len(inventory["wrong_present"]) + len(inventory["missing"]),
                     "State counts, missingness or denominators differ")
            states = {f: state for state, indices in inventory.items() for f in indices}
            fake = {"frame_results": [{"frame_index": f, "accepted_detection_count": int(states[f] in ("matched", "wrong_present", "alarm")),
                      "matched_candidate_index": 0 if states[f] == "matched" else None,
                      "scoring_status": "not_visible_negative" if f in hidden else "localization_eligible"} for f in frames]}
            _require(window["temporal_metrics"][arm] == evaluation.temporal_metrics(fake), "Run lengths differ from frame states")
            paths = window["path_metrics"][arm]
            choices = paths["endpoint_choice_frame_indices"]
            _require(set(choices) == {"current", "older", "empty"}
                     and sorted(f for v in choices.values() for f in v) == frames
                     and all(v == sorted(set(v)) for v in choices.values())
                     and paths["endpoint_choice_counts"] == {k: len(v) for k, v in choices.items()}
                     and set(choices["current"]) == set(inventory["matched"] + inventory["wrong_present"] + inventory["alarm"])
                     and all(k in {str(i) for i in range(6)} and type(v) is int and v >= 0 for k, v in paths["path_node_counts"].items())
                     and sum(paths["path_node_counts"].values()) == 25
                     and paths["singleton_emission_frame_indices"] == sorted(set(paths["singleton_emission_frame_indices"]))
                     and set(paths["singleton_emission_frame_indices"]) <= set(choices["current"])
                     and paths["singleton_emission_count"] == len(paths["singleton_emission_frame_indices"])
                     and paths["path_node_counts"].get("0", 0) == len(choices["empty"])
                     and paths["singleton_emission_count"] <= paths["path_node_counts"].get("1", 0)
                     and paths["top_one_path_is_descriptive_singleton"] is (arm == evaluation.TOP)
                     and (arm != evaluation.TOP or (not choices["older"] and paths["singleton_emission_frame_indices"] == choices["current"])),
                     "Path/endpoint accounting differs")
        for control in (evaluation.TT, evaluation.TOP):
            changed = window["changed_emission_frames"][control]
            _require(type(changed) is list and changed == sorted(set(changed))
                     and set(changed) <= set(frames[1:]), "Changed-emission list violates source scope or startup parity")
            left, right = (window["summaries"][a]["frame_indices"] for a in (control, evaluation.ARM))
            for kind, states in (("eligible", evaluation.STATES), ("hidden", evaluation.HIDDEN_STATES)):
                expected = {a: {b: {"count": len(set(left[a]) & set(right[b])),
                                   "frame_indices": sorted(set(left[a]) & set(right[b]))} for b in states} for a in states}
                _require(window["paired_transitions"][control][kind] == expected, "Paired transitions disagree with frame states")
            old, new = (window["summaries"][a]["counts"] for a in (control, evaluation.ARM))
            expected = {k: new[k] - old[k] for k in (*evaluation.STATES, "alarm")
                        if (new[k] < old[k] if k == "matched" else new[k] > old[k])}
            _require(window["window_regressions"][control] == expected, "Window regressions omitted or changed")
    pools = [evaluation.aggregate_pool([w for w in summary["windows"] if w["purpose"] == purpose], purpose)
             for purpose in evaluation.POOLS]
    _require(summary["pools"] == pools and summary["interpretation"] == evaluation.development_interpretation(pools),
             "Separate pool accounting or development interpretation differs")
    _require([r["frame_index"] for r in summary["fixed_diagnostic"]] == list(evaluation.DIAGNOSTIC_FRAMES),
             "Fixed diagnostic frames changed")
    diagnostic_window = next(w for w in summary["windows"] if w["window_id"] == evaluation.DIAGNOSTIC_WINDOW)
    for row, human in zip(summary["fixed_diagnostic"], context["human_ledger"]["rows"]):
        _require(row["saved_tt"]["original_human_record"] == human
                 and row["new_mean"]["semantic_identity"] is None
                 and row["saved_top_one"]["semantic_identity"] is None
                 and row["new_causal_verdict"] is None
                 and row["judgment_scope"] == "originally reviewed saved TT emission only"
                 and row["prior_contrast_context"] == ("confidence_only_startup" if row["frame_index"] == 300
                     else "motion_related_comparison" if row["frame_index"] == 304
                     else "one_of_six_history_dominated_saved_comparisons"),
                 "Old human judgments changed or leaked to new choices")
        selected = {}
        for field, arm in (("saved_tt", evaluation.TT), ("new_mean", evaluation.ARM), ("saved_top_one", evaluation.TOP)):
            observation = row[field]["observation"]
            _require(set(observation) == {"frame_index", "emitted_candidate_indices", "decision_reason", "winner", "score_margin"}
                     and observation["frame_index"] == row["frame_index"]
                     and type(observation["decision_reason"]) is str, "Incomplete compact diagnostic observation")
            indices = observation["emitted_candidate_indices"]
            _require(type(indices) is list and len(indices) <= 1 and all(type(i) is int and i >= 0 for i in indices),
                     "Invalid diagnostic candidate index")
            selected[arm] = indices
            frame_states = diagnostic_window["summaries"][arm]["frame_indices"]
            present = row["frame_index"] in frame_states["matched"] + frame_states["wrong_present"] + frame_states["alarm"]
            _require(bool(indices) == present, "Diagnostic output contradicts frame accounting")
            winner = observation["winner"]
            if arm == evaluation.TOP:
                _require(winner is None and observation["score_margin"] is None, "Top-one cannot inherit a history trace")
            else:
                _require(type(winner) is dict and type(winner["score"]) in (int, float) and math.isfinite(winner["score"])
                         and type(observation["score_margin"]) in (int, float) and math.isfinite(observation["score_margin"])
                         and observation["score_margin"] >= 0, "Diagnostic winner/margin invalid")
                endpoint = winner["endpoint"]
                if endpoint is None:
                    _require(not winner["path"] and not indices, "Empty diagnostic winner emits a candidate")
                else:
                    _require(type(endpoint) is list and len(endpoint) == 2
                             and all(type(i) is int and i >= 0 for i in endpoint)
                             and 300 <= endpoint[0] <= row["frame_index"]
                             and winner["path"] and winner["path"][-1] == endpoint
                             and indices == ([endpoint[1]] if endpoint[0] == row["frame_index"] else []),
                             "Diagnostic winner does not match emission")
        _require(len(selected[evaluation.TT]) == 1 and (human["emitted_candidate_index"] is None
                 or selected[evaluation.TT] == [human["emitted_candidate_index"]]), "Human index bound to another saved TT emission")
        if row["frame_index"] == 300:
            _require(all(indices == selected[evaluation.TT] for indices in selected.values()), "Frame 300 startup changed")
        for control in (evaluation.TT, evaluation.TOP):
            _require((selected[control] != selected[evaluation.ARM]) ==
                     (row["frame_index"] in diagnostic_window["changed_emission_frames"][control]),
                     "Diagnostic candidate changes differ from the review index")
    _require([r["window_id"] for r in summary["reviews"]] == [w["window_id"] for w in windows], "Review windows differ")
    for row, window in zip(summary["reviews"], windows):
        base = OUTPUT_ROOT + "/" + OUTPUT_DIR + "/review/" + window["window_id"]
        _require(row["clip"] == base + "/comparison.mp4" and _pair(row["index_binding"])["path"] == base + "/review_index.json"
                 and row["first_frame_index"] == window["start_frame_index"] and row["last_frame_index"] == window["end_frame_index"]
                 and row["frame_count"] == 25 and row["fps"] == 5 and row["human_review"] == "pending",
                 "Review endpoints or authorized presentation paths differ")
    _require(all(summary[k] is None for k in ("selected_method", "selected_operating_point", "quality_gate")),
             "Summary selected a method or quality gate")


def validate_return(result, root, context, aid):
    """Parent validates only bounded returned values and artifact metadata."""
    _require(set(result) == {"schema_version", "stage", "unit_key", "attempt_id", "commit", "spec_sha256", "artifacts",
                            "artifact_metadata", "checks", "summary", "summary_text", "scientific_input_count"}
             and result["schema_version"] == "ball_crop_path_confidence_mean_worker_result/v0.1"
             and result["stage"] == "study" and result["unit_key"] == UNIT_KEY and result["attempt_id"] == aid
             and result["commit"] == context["commit"] and result["spec_sha256"] == context["spec_sha256"]
             and result["checks"] == CHECKS and all(type(v) is bool for v in result["checks"].values())
             and result["scientific_input_count"] == 176, "Worker receipt does not bind this complete study")
    expected = {OUTPUT_ROOT + "/" + name for name in _output_names(context["scope"])}
    bounds = {OUTPUT_ROOT + "/" + OUTPUT_DIR + "/" + row["path"]: row["maximum_bytes"] for row in context["scope"]["outputs"]["files"]}
    legacy._unique_bindings(result["artifacts"])
    _require(len(result["artifacts"]) == 636 and {r["path"] for r in result["artifacts"]} == expected, "Output inventory differs")
    metadata = result["artifact_metadata"]
    _require(len(metadata) == 636 and {r["path"] for r in metadata} == expected, "Output metadata inventory differs")
    for row in metadata:
        _require(set(row) == {"path", "size_bytes", "mtime_ns", "device", "inode"}
                 and 0 < row["size_bytes"] <= bounds[row["path"]]
                 and _stat_metadata(safe_path(root, row["path"])) == {k: v for k, v in row.items() if k != "path"},
                 "Verified artifact metadata changed after worker completion")
    summary = result["summary"]
    validate_bounded_summary(summary, context)
    authored = {row["path"]: row for row in result["artifacts"]}
    _require(all(row["index_binding"] == authored[row["index_binding"]["path"]] for row in summary["reviews"]),
             "Review index binding differs from verified artifact")
    _require(len(summary["windows"]) == len(summary["reviews"]) == 6 and len(summary["pools"]) == 2
             and {r["window_id"] for r in summary["windows"]} == {w["window_id"] for w in context["scope"]["windows"]}
             and {r["window_id"] for r in summary["reviews"]} == {w["window_id"] for w in context["scope"]["windows"]}
             and all(r["human_review"] == "pending" for r in summary["reviews"])
             and len(summary["fixed_diagnostic"]) == 8
             and all(summary[k] is None for k in ("selected_method", "selected_operating_point", "quality_gate")),
             "Bounded summary scope differs")
    _require(result["summary_text"] == _summary_text(summary), "Summary text differs from bounded result")
    for name, raw in (("summary.json", _json_bytes(summary)), ("summary.md", result["summary_text"].encode("utf-8"))):
        path = OUTPUT_ROOT + "/" + OUTPUT_DIR + "/" + name
        _require(next(r["sha256"] for r in result["artifacts"] if r["path"] == path) == hashlib.sha256(raw).hexdigest()
                 and next(r["size_bytes"] for r in metadata if r["path"] == path) == len(raw), "Summary transport differs from verified artifact")
    _require(len(_json_bytes(summary)) <= MAX_RETURN_BYTES, "Summary transport exceeds its bound")
    return summary


def _completed_result(root, context, event):
    journal = verify_history(root, context, "completed")
    _require(journal.events[-1] == event, "Supervisor return differs from persisted event")
    aid = event["attempt_id"]
    context = {**context, "completed_attempt_id": aid}
    _preserved_metadata(root, context, "completed", allow_outputs=True)
    baseline = sum(row["size_bytes"] for row in context["history"]["preserved_files"])
    _require(event["final_accounting_output_bound_bytes"] - baseline <= MAX_NEW_BYTES, "Final new-byte bound exceeded")
    binding = {"path": OUTPUT_ROOT + "/" + event["worker_result"]["path"], "sha256": event["worker_result"]["sha256"]}
    result = _read_bound(root, binding, monitor.WORKER_RECEIPT_LIMIT)
    summary = validate_return(result, Path(root).resolve(), context, aid)
    returned = {"stage": "study", "successful_workers": 1, "commit": context["commit"], "worker_result": binding,
        "completion_event_sha256": event["sha256"], "summary": summary, "summary_text": result["summary_text"],
        "new_model_calls": 0, "saved_controls_reexecuted": False, "six_human_reviews_pending": True,
        "selected_method": None, "selected_operating_point": None, "quality_gate": None}
    _require(len(_json_bytes(returned)) <= MAX_RETURN_BYTES, "Bounded parent return exceeds 512KiB")
    return returned


def run_study(root, manifest_path, dry_run=False):
    context = _metadata(root, manifest_path, True)
    verify_history(root, context, "before")
    _preserved_metadata(root, context, "before")
    if dry_run:
        return {"dry_run": True, "metadata_only": True, "scientific_inputs_verified": False,
                "spec_sha256": context["spec_sha256"], "post_commit_checkpoint_verified": True}
    command = [sys.executable, "-B", "-m", "src.ball_tracking.crop_path_confidence_mean_experiment",
               "--manifest", str(context["manifest_path"]), "--repository-root", str(context["root"]), "--worker"]
    event = _run_bounded_supervised(context, command)
    end = _metadata(root, manifest_path, True)
    _require(end["commit"] == context["commit"] and end["spec_sha256"] == context["spec_sha256"], "Authority changed before parent release")
    return _completed_result(root, end, event)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--stage", choices=("study",), default="study")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    _require(not (args.worker and args.dry_run), "Owned worker cannot use dry-run authority")
    root = args.repository_root.resolve()
    manifest = root / args.manifest
    result = _worker(root, manifest) if args.worker else run_study(root, manifest, args.dry_run)
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":"), allow_nan=False))


if __name__ == "__main__":
    main()
