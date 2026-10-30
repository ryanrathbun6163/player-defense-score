"""One bounded, worker-only derivation from the completed recovery breakdown.

Historical scientific bodies remain opaque to the parent. Completed authority,
monitor and formatter modules are reused without overrides or mutation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

from . import crop_retention_error_breakdown_recovery as predecessor
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
ID = "rfdetr_medium_crop_candidate_retention_output_presence_v0_1"
MANIFEST_PATH = "configs/ball_tracking/crop_retention_experiments/" + ID + ".json"
APPROVAL_PATH = "configs/ball_tracking/reviews/rfdetr_medium_crop_candidate_retention_output_presence_approval_v0_1.json"
PROPOSAL_PATH = "docs/ball_crop_candidate_retention_output_presence_proposal.md"
PROPOSAL_SHA = "355bfcd29d8059737ca4b8449cd1fe0a03b72ba32aefc57b2ed5e71ba2dbdfcb"
IMPLEMENTATION_DIR = "data/outputs/t/op_impl_de134d942767"
CERTIFICATE_PATH = IMPLEMENTATION_DIR + "/implementation_validation.json"
POST_COMMIT_PATH = IMPLEMENTATION_DIR + "/post_commit_execution_checkpoint.json"
FROZEN_HISTORY_PATH = IMPLEMENTATION_DIR + "/frozen_history.json"
FROZEN_HISTORY_SHA = "def7a7fc4e82466ef057427fa2beb0e017af2a48a809884506f9297a5bd7e106"
PREDECESSOR_COMPLETION_PATH = predecessor.IMPLEMENTATION_DIR + "/recovery_completion_de134d942767.json"
BASE_COMMIT = "de134d942767b70dfc6da360745f50405a8b3f8d"
OUTPUT_ROOT = predecessor.OUTPUT_ROOT
OUTPUT_DIR = "audit/post_review_output_presence_v0_1"
OUTPUTS = [OUTPUT_DIR + "/" + name for name in ("presence.json", "summary.md", "provenance.json")]
UNIT_KEY = "post-review-output-presence:summary:"
PREFIX_COUNT = 3071
PREFIX_ATTEMPTS = 59
PREFIX_TIP = "d800b77b4db2128d1baa09db59538ab6f16d4aad6d96aaa7a9fd84f96c11bf92"
PREDECESSOR_ATTEMPT = "05fe00c14f224c5abfc2cc6008e90f96"
PREDECESSOR_RESULT_SHA = "c058335ee3d8a1301c6db55bedd83311cb07031d8fcdc1a8d5b9520fb0caa6d5"
USED_SECONDS = 3320.0549999999857
MAX_UNIT_SECONDS = 120
MAX_SUMMARY_BYTES = 65536
KNOWN_FAILURES = predecessor.KNOWN_FAILURES
SCIENTIFIC_INPUT = {"path": OUTPUT_ROOT + "/audit/post_review_error_breakdown_recovery_v0_1/breakdown.json",
                    "size_bytes": 744235, "sha256": "05b6ea6091ebeada1857b85016c2510f9d65349596f61cd208514c2a31252b32"}
SCIENTIFIC_INPUTS = {"breakdown": SCIENTIFIC_INPUT}
AUTHORITY_PATHS = {"proposal": PROPOSAL_PATH, "authorization": APPROVAL_PATH,
                   "frozen_history": FROZEN_HISTORY_PATH, "predecessor_manifest": predecessor.MANIFEST_PATH,
                   "predecessor_completion": PREDECESSOR_COMPLETION_PATH}
AUTHORITY_FIELDS = tuple(AUTHORITY_PATHS)
MANIFEST_FIELDS = {"schema_version", "study_id", "output_root", "output_dir", "permitted_stages", "unit_key",
                   "maximum_unit_seconds", "maximum_summary_bytes", "scientific_inputs", *AUTHORITY_FIELDS,
                   "implementation_validation", "post_commit_checkpoint", "selected_method", "selected_operating_point", "quality_gate"}
MONITOR_EVIDENCE = predecessor.MONITOR_EVIDENCE
SEMANTIC_SOURCES = ("src/ball_tracking/crop_retention_evaluation.py", "src/ball_tracking/evaluation.py",
                    "src/ball_tracking/crop_motion_factorial.py", "src/ball_tracking/crop_motion_evaluation.py")
SCORING_COMMIT = "f36237247191e726ad7e81bdc6651f9340a9063d"
CHECKS = {"input_hash_unchanged": True, "source_authority_unchanged": True,
          "preserved_metadata_and_receipts_unchanged": True, "output_integrity_verified": True,
          "only_one_scientific_input_read": True, "within_row_derivation_only": True,
          "no_inference_scoring_selection_media_or_semantic_labels": True,
          "new_budget_distinct_from_consumed_recovery": True, "validated_monitor_used": True,
          "clean_post_commit_checkpoint_verified": True}
_scan_record = predecessor._scan_record
_successful_completion = predecessor._successful_completion

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
             and manifest["schema_version"] == "ball_crop_retention_output_presence_experiment/v0.1"
             and manifest["study_id"] == ID and manifest["output_root"] == OUTPUT_ROOT
             and manifest["output_dir"] == OUTPUT_DIR and manifest["permitted_stages"] == ["summarize"]
             and manifest["unit_key"] == UNIT_KEY and manifest["maximum_unit_seconds"] == MAX_UNIT_SECONDS
             and manifest["maximum_summary_bytes"] == MAX_SUMMARY_BYTES
             and manifest["scientific_inputs"] == SCIENTIFIC_INPUTS
             and manifest["post_commit_checkpoint"] == POST_COMMIT_PATH, "Unsupported output-presence scope")
    _require(all(manifest[k] is None for k in ("selected_method", "selected_operating_point", "quality_gate")),
             "Output-presence cannot choose a method or quality gate")
    for key, path in AUTHORITY_PATHS.items():
        _require(_pair(manifest[key])["path"] == path, "Unexpected authority path: " + key)
    _require(manifest["proposal"] == {"path": PROPOSAL_PATH, "sha256": PROPOSAL_SHA}
             and manifest["frozen_history"] == {"path": FROZEN_HISTORY_PATH, "sha256": FROZEN_HISTORY_SHA},
             "Exact approved proposal and completed prefix are required")
    _require(_pair(manifest["implementation_validation"])["path"] == CERTIFICATE_PATH,
             "Unexpected current validation certificate")


def _validate_implementation(root, manifest):
    certificate = _read_bound(root, manifest["implementation_validation"])
    _require(certificate["schema_version"] == "ball_crop_retention_output_presence_implementation_validation/v0.1",
             "Unsupported output-presence validation certificate")
    for key in ("focused_tests_passed", "full_suite_passed", "independent_static_review_passed",
                "integrity_tests_passed", "monitor_design_check_passed"):
        _require(certificate.get(key) is True, "Output-presence implementation validation is incomplete: " + key)
    _require(certificate["manifest_spec_sha256"] == _spec_sha256(manifest)
             and certificate["authority_sha256"] == {key: manifest[key]["sha256"] for key in AUTHORITY_FIELDS},
             "Output-presence validation is bound to different authority/specification")
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
    _require(checkpoint["schema_version"] == "ball_crop_retention_output_presence_execution_checkpoint/v0.1"
             and type(commit) is str and re.fullmatch(r"[0-9a-f]{40}", commit) and commit != BASE_COMMIT
             and checkpoint["head"] == commit and checkpoint["branch"] == "codex/ball-detector-baseline"
             and checkpoint["manifest"] == file_binding(root, root / MANIFEST_PATH)
             and checkpoint["implementation_validation"] == manifest["implementation_validation"]
             and checkpoint["manifest_spec_sha256"] == _spec_sha256(manifest)
             and checkpoint["preserved_prefix_tip_sha256"] == PREFIX_TIP,
             "Post-commit checkpoint does not bind this exact execution")
    for key in ("execution_authorized", "clean", "index_empty", "validated_sources_unchanged"):
        _require(checkpoint.get(key) is True, "Post-commit execution prerequisite is missing: " + key)
    _require(subprocess.run(["git", "merge-base", "--is-ancestor", BASE_COMMIT, commit], cwd=root).returncode == 0,
             "Output-presence must descend from the completed recovery commit")
    return checkpoint


def _metadata(root, manifest_path, require_clean=True):
    root = Path(root).resolve()
    path = Path(manifest_path).absolute()
    _require(path == root / MANIFEST_PATH, "Unexpected output-presence manifest path")
    commit = legacy.original._clean_checkpoint(root) if require_clean else legacy.original._git(root, "rev-parse", "HEAD")
    manifest = read_json(safe_path(root, MANIFEST_PATH))
    _validate_manifest(manifest)
    checkpoint = _post_commit_checkpoint(root, manifest, commit) if require_clean else None
    for key in AUTHORITY_FIELDS:
        verify_binding(root, manifest[key])
    approval = _read_bound(root, manifest["authorization"])
    _require(approval["schema_version"] == "ball_crop_retention_output_presence_approval/v0.1"
             and approval["approved_by"].lower() == "ryan" and approval["proposal"] == manifest["proposal"]
             and approval["maximum_new_attempts"] == 1 and approval["maximum_unit_seconds"] == MAX_UNIT_SECONDS
             and approval["approved_operations"] == ["ordered_difference", "ordered_intersection", "list_length"],
             "Exact output-presence approval is required")
    for key in ("implementation_authorized", "focused_validation_authorized", "full_regression_authorized",
                "conditional_execution_authorized", "separate_clean_commit_required", "responsive_monitor_policy_adopted"):
        _require(approval.get(key) is True, "Missing authorization: " + key)
    for key in ("parent_scientific_body_access_authorized", "automatic_scientific_retry_authorized",
                "semantic_adjudication_authorized", "new_model_inference_authorized", "git_mutations_authorized"):
        _require(approval.get(key) is False, "Approval expands scope: " + key)
    # Historical metadata only; never invoke the consumed recovery's public runner.
    historical = predecessor._metadata(root, root / predecessor.MANIFEST_PATH, False)
    history = _read_bound(root, manifest["frozen_history"])
    _require(history["schema_version"] == "ball_crop_retention_output_presence_frozen_history/v0.1"
             and history["head"] == BASE_COMMIT and history["prefix_count"] == PREFIX_COUNT
             and history["prefix_tip_sha256"] == PREFIX_TIP and history["prefix_attempts"] == PREFIX_ATTEMPTS
             and history["prefix_successes"] == 55 and set(history["known_failures"]) == KNOWN_FAILURES
             and history["limits"] == historical["limits"] and history["scientific_bodies_read_or_hashed"] is False
             and math.isclose(history["consumed_seconds"], USED_SECONDS, abs_tol=1e-7, rel_tol=0),
             "Wrong completed-history preservation authority")
    prior = _read_bound(root, manifest["predecessor_completion"])
    _require(prior["success"] is True and prior["execution_commit"] == BASE_COMMIT
             and prior["attempt_id"] == PREDECESSOR_ATTEMPT and prior["completion_event_chain_sha256"] == PREFIX_TIP
             and prior["authorized_recovery_attempts_remaining"] == 0
             and prior["worker_result_binding_from_verified_return"] == {
                 "path": OUTPUT_ROOT + "/attempts/" + PREDECESSOR_ATTEMPT + ".result.json", "sha256": PREDECESSOR_RESULT_SHA},
             "The consumed successful recovery is required")
    source_receipt = _read_bound(root, prior["worker_result_binding_from_verified_return"], monitor.WORKER_RECEIPT_LIMIT)
    _require(source_receipt["attempt_id"] == PREDECESSOR_ATTEMPT and source_receipt["commit"] == BASE_COMMIT
             and {"path": SCIENTIFIC_INPUT["path"], "sha256": SCIENTIFIC_INPUT["sha256"]} in source_receipt["artifacts"]
             and next(row["size_bytes"] for row in source_receipt["artifact_metadata"] if row["path"] == SCIENTIFIC_INPUT["path"])
                 == SCIENTIFIC_INPUT["size_bytes"], "Scientific input lacks its successful producer binding")
    certificate = _validate_implementation(root, manifest) if require_clean else None
    if require_clean:
        for name in (MANIFEST_PATH, *AUTHORITY_PATHS.values()):
            if not name.startswith("data/"):
                legacy.original._git(root, "ls-files", "--error-unmatch", "--", name)
        for name in SEMANTIC_SOURCES:
            _require(legacy.original._git(root, "rev-parse", SCORING_COMMIT + ":" + name)
                     == legacy.original._git(root, "rev-parse", commit + ":" + name),
                     "Historical output-presence semantics changed: " + name)
    _require(subprocess.run(["git", "check-ignore", "-q", "--", OUTPUT_ROOT + "/" + OUTPUTS[0]], cwd=root).returncode == 0,
             "Study outputs must remain ignored")
    return {"root": root, "manifest_path": path, "manifest": manifest, "commit": commit,
            "spec_sha256": _spec_sha256(manifest), "output_root": safe_path(root, OUTPUT_ROOT),
            "limits": historical["limits"], "history": history, "certificate": certificate,
            "policy": monitor.monitoring_policy(historical["limits"], .25), "checkpoint": checkpoint}


def _remaining_seconds(journal):
    return min(MAX_UNIT_SECONDS - journal.consumed(UNIT_KEY),
               journal.limits["maximum_cumulative_seconds"] - journal.consumed())


def _closed_prefix(journal):
    _require(len(journal.events) >= PREFIX_COUNT and journal.events[PREFIX_COUNT - 1]["sha256"] == PREFIX_TIP,
             "Exact completed 3071-event prefix is required")
    old_starts, _ = predecessor._closed_prefix(journal)
    frozen = journal.events[:PREFIX_COUNT]
    starts = {e["attempt_id"]: e for e in frozen if e["kind"] == "started"}
    ends = {e["attempt_id"]: e for e in frozen if e["kind"] == "finished"}
    _require(len(starts) == len(ends) == PREFIX_ATTEMPTS and set(starts) == set(ends)
             and set(starts) - set(old_starts) == {PREDECESSOR_ATTEMPT}
             and {aid for aid, e in ends.items() if not e["success"]} == KNOWN_FAILURES
             and sum(e["success"] is True for e in ends.values()) == 55
             and starts[PREDECESSOR_ATTEMPT]["unit_key"] == predecessor.UNIT_KEY
             and frozen[-1] == ends[PREDECESSOR_ATTEMPT]
             and math.isclose(sum(e["elapsed_seconds"] for e in ends.values()), USED_SECONDS, abs_tol=1e-7, rel_tol=0),
             "Completed recovery history or budgets changed")
    policy = monitor.monitoring_policy(journal.limits, .25)
    _successful_completion(ends[PREDECESSOR_ATTEMPT], {"limits": journal.limits, "policy": policy},
                           starts[PREDECESSOR_ATTEMPT]["reserved_seconds"])
    _require(ends[PREDECESSOR_ATTEMPT]["worker_result"] == {
        "path": "attempts/" + PREDECESSOR_ATTEMPT + ".result.json", "sha256": PREDECESSOR_RESULT_SHA},
        "Successful precursor receipt changed")
    return starts, ends


class PresenceJournal(BudgetJournal):
    """One new 120-second role, never a renewal of the consumed recovery."""
    def reserve(self, unit_key, selection_unit):
        _require(unit_key == UNIT_KEY and selection_unit is False, "Unknown output-presence reservation")
        _require(len(self.events) == PREFIX_COUNT, "Study cannot retry or adopt a suffix")
        _closed_prefix(self)
        _require(all(a["finished"] is not None for a in self._attempts().values()), "An attempt is still active")
        remaining = _remaining_seconds(self)
        _require(remaining > 0, "Output-presence budget is exhausted")
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
    _require(history["prior_recovery_completion"] == ends[PREDECESSOR_ATTEMPT], "Preserved completion changed")
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
    suffix = journal.events[PREFIX_COUNT:]
    attempts = journal._attempts()
    new = {aid: value for aid, value in attempts.items() if aid not in starts}
    if phase == "before":
        _require(not suffix and not new and all(row["finished"] is not None for row in attempts.values()),
                 "Output-presence requires the untouched completed prefix; no retry or unknown suffix")
        return journal
    _require(len(new) == 1 and suffix and suffix[0]["kind"] == "started", "Exactly one owned output-presence attempt is required")
    aid, attempt = next(iter(new.items()))
    start, end = attempt["start"], attempt["finished"]
    expected_seconds = min(MAX_UNIT_SECONDS, context["limits"]["maximum_cumulative_seconds"] - USED_SECONDS)
    _require(start["unit_key"] == UNIT_KEY and start["selection_unit"] is False
             and math.isclose(start["reserved_seconds"], expected_seconds, rel_tol=0, abs_tol=1e-7)
             and all(event["attempt_id"] == aid for event in suffix)
             and sum(event["kind"] == "started" for event in suffix) == 1,
             "Unknown output-presence role or renewed reservation")
    _require(read_json(safe_path(root, OUTPUT_ROOT + "/attempts/" + aid + ".reservation.json")) == {"event_sha256": start["sha256"]},
             "Output-presence reservation seal changed")
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
                 "Output-presence sample violated safety or policy bounds")
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
        _require(end is not None and suffix[-1] == end, "Incomplete or failed output-presence attempt cannot release a summary")
        _successful_completion(end, context, start["reserved_seconds"])
        counts = [sample["output_bytes"] for sample in samples if sample["output_bytes"] is not None]
        _require(samples and counts and end["monitor_samples"] == len(samples)
                 and end["peak_worker_memory_bytes"] >= max(sample["memory_bytes"] for sample in samples)
                 and end["maximum_output_bytes"] >= max(counts)
                 and end["minimum_free_disk_bytes"] <= min(sample["free_disk_bytes"] for sample in samples)
                 and end["worker_result"]["path"] == "attempts/" + aid + ".result.json"
                 and end["monitoring_policy_path"] == "attempts/" + aid + ".monitoring_policy.json",
                 "Completed output-presence attempt understates its evidence or names another receipt")
        _require(read_json(safe_path(root, OUTPUT_ROOT + "/attempts/" + aid + ".completion.json")) == {"event_sha256": end["sha256"]},
                 "Output-presence completion seal changed")
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
        _require(type(aid) is str and re.fullmatch(r"[0-9a-f]{32}", aid), "Invalid output-presence attempt identity")
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
                                  require_result=True, journal_factory=PresenceJournal)


def _load_breakdown(root):
    _require(bool(os.environ.get("BALL_RETENTION_ATTEMPT_ID")), "Scientific access requires an owned worker")
    path = safe_path(root, SCIENTIFIC_INPUT["path"], OUTPUT_ROOT)
    before = _stat_metadata(path)
    _require(before["size_bytes"] == SCIENTIFIC_INPUT["size_bytes"], "Scientific input size changed")
    with path.open("rb") as stream:
        payload = stream.read(SCIENTIFIC_INPUT["size_bytes"] + 1)
    _require(len(payload) == SCIENTIFIC_INPUT["size_bytes"] and _stat_metadata(path) == before
             and hashlib.sha256(payload).hexdigest() == SCIENTIFIC_INPUT["sha256"], "Scientific input bytes changed")
    return json.loads(payload)


def _worker(root, manifest_path):
    resources.wait_for_supervisor()
    root = Path(root).resolve()
    context = _metadata(root, manifest_path, True)
    journal = verify_history(root, context, "worker")
    aid = os.environ["BALL_RETENTION_ATTEMPT_ID"]
    result_path = safe_path(root, OUTPUT_ROOT + "/attempts/" + aid + ".result.json")
    _require(Path(os.environ["BALL_RETENTION_RESULT_PATH"]).resolve() == result_path, "Worker receipt is outside its reservation")
    _absent(result_path)
    _preserved_metadata(root, context, "worker")
    from .crop_retention_output_presence_summary import build_summary, SUMMARY_SCHEMA
    summary, text = build_summary(_load_breakdown(root))
    _require(summary["schema_version"] == SUMMARY_SCHEMA and type(text) is str
             and all(summary.get(k) is None for k in ("selected_method", "selected_operating_point", "quality_gate")),
             "Output-presence formatter contract changed")
    text_bytes = text.encode("utf-8")
    _require(0 < len(text_bytes) <= MAX_SUMMARY_BYTES, "Summary exceeds approved transport bound")
    destination = safe_path(root, OUTPUT_ROOT + "/" + OUTPUT_DIR)
    _absent(destination)
    destination.mkdir()
    summary_bytes = legacy._json_bytes(summary)
    legacy._write_new(destination / "presence.json", summary_bytes)
    legacy._write_new(destination / "summary.md", text_bytes)
    provenance = {"schema_version": "ball_crop_retention_output_presence_provenance/v0.1",
                  "study_id": ID, "unit_key": UNIT_KEY, "attempt_id": aid, "commit": context["commit"],
                  "spec_sha256": context["spec_sha256"], "authority_bindings": {k: context["manifest"][k] for k in AUTHORITY_FIELDS},
                  "implementation_validation": context["manifest"]["implementation_validation"],
                  "post_commit_checkpoint": file_binding(root, root / POST_COMMIT_PATH),
                  "source_bindings": context["certificate"]["source_bindings"], "scientific_inputs": SCIENTIFIC_INPUTS,
                  "source_map": summary["source_map"], "preserved_prefix_count": PREFIX_COUNT,
                  "preserved_prefix_tip_sha256": PREFIX_TIP,
                  "active_reservation_sha256": journal._attempts()[aid]["start"]["sha256"],
                  "monitoring_policy_sha256": resources._digest(context["policy"]), "checks": CHECKS,
                  "summary_bindings": [file_binding(root, destination / n) for n in ("presence.json", "summary.md")],
                  "acceptance": "Requires successful sealed completion, preservation and verified bounded transport."}
    provenance_bytes = legacy._json_bytes(provenance)
    legacy._write_new(destination / "provenance.json", provenance_bytes)
    authored = {"presence.json": summary_bytes, "summary.md": text_bytes, "provenance.json": provenance_bytes}
    _require(all((destination / n).read_bytes() == raw for n, raw in authored.items()), "Authored output differs")
    end = _metadata(root, manifest_path, True)
    _require(end["commit"] == context["commit"] and end["spec_sha256"] == context["spec_sha256"], "Authority changed during worker execution")
    # Recheck only the exact permitted scientific input; never follow its pointers.
    verify_binding(root, SCIENTIFIC_INPUT)
    verify_history(root, end, "worker")
    _preserved_metadata(root, end, "worker", allow_outputs=True)
    artifacts = [file_binding(root, destination / name) for name in authored]
    _require(all(b["sha256"] == hashlib.sha256(authored[Path(b["path"]).name]).hexdigest() for b in artifacts), "Authored artifact changed")
    result = {"schema_version": "ball_crop_retention_output_presence_worker_result/v0.1",
              "stage": "summarize", "unit_key": UNIT_KEY, "attempt_id": aid, "commit": context["commit"],
              "spec_sha256": context["spec_sha256"], "artifacts": artifacts,
              "artifact_metadata": [{"path": b["path"], **_stat_metadata(root / b["path"])} for b in artifacts],
              "scientific_inputs": SCIENTIFIC_INPUTS, "checks": CHECKS,
              "summary_payload": {"text": text, "size_bytes": len(text_bytes), "sha256": hashlib.sha256(text_bytes).hexdigest()}}
    payload = legacy._json_bytes(result)
    _require(len(payload) <= monitor.WORKER_RECEIPT_LIMIT, "Worker receipt exceeds interface bound")
    legacy._write_new(result_path, payload)
    _require(result_path.read_bytes() == payload, "Worker receipt differs")
    return {"worker_result_written": True, "attempt_id": aid, "completion_pending": True}


def _completed_result(root, context, event):
    root = Path(root).resolve()
    journal = verify_history(root, context, "completed")
    _require(journal.events[-1] == event, "Supervisor completion differs from its persisted event")
    aid = event["attempt_id"]
    context = {**context, "completed_attempt_id": aid}
    _preserved_metadata(root, context, "completed", allow_outputs=True)
    binding = {"path": OUTPUT_ROOT + "/" + event["worker_result"]["path"], "sha256": event["worker_result"]["sha256"]}
    _require(binding["path"] == OUTPUT_ROOT + "/attempts/" + aid + ".result.json", "Wrong output-presence receipt path")
    result = _read_bound(root, binding, monitor.WORKER_RECEIPT_LIMIT)
    _require(set(result) == {"schema_version", "stage", "unit_key", "attempt_id", "commit", "spec_sha256",
                             "artifacts", "artifact_metadata", "scientific_inputs", "checks", "summary_payload"}
             and result["schema_version"] == "ball_crop_retention_output_presence_worker_result/v0.1"
             and result["stage"] == "summarize" and result["unit_key"] == UNIT_KEY and result["attempt_id"] == aid
             and result["commit"] == context["commit"] and result["spec_sha256"] == context["spec_sha256"]
             and result["scientific_inputs"] == SCIENTIFIC_INPUTS and result["checks"] == CHECKS
             and all(type(value) is bool for value in result["checks"].values()),
             "Output-presence worker receipt does not certify this exact execution")
    expected = {OUTPUT_ROOT + "/" + path for path in OUTPUTS}
    legacy._unique_bindings(result["artifacts"])
    _require(len(result["artifacts"]) == 3 and {row["path"] for row in result["artifacts"]} == expected,
             "Output-presence artifact identities changed")
    rows = result["artifact_metadata"]
    _require(type(rows) is list and len(rows) == 3 and {row["path"] for row in rows} == expected, "Incomplete artifact metadata")
    for row in rows:
        _require(set(row) == {"path", "size_bytes", "mtime_ns", "device", "inode"}
                 and _stat_metadata(safe_path(root, row["path"])) == {key: row[key] for key in row if key != "path"},
                 "Output-presence artifact metadata changed after worker verification")
    payload = result["summary_payload"]
    _require(type(payload) is dict and set(payload) == {"text", "size_bytes", "sha256"}
             and type(payload["text"]) is str and type(payload["size_bytes"]) is int,
             "Invalid bounded output-presence summary transport")
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


def run_output_presence(root, manifest_path, dry_run=False):
    # Even a public dry-run requires the real post-commit gate. Development
    # tests call private clauses on fabricated metadata instead of real history.
    context = _metadata(root, manifest_path, True)
    verify_history(root, context, "before")
    _preserved_metadata(root, context, "before")
    if dry_run:
        return {"dry_run": True, "metadata_only": True, "scientific_inputs_verified": False,
                "spec_sha256": context["spec_sha256"], "post_commit_checkpoint_verified": True}
    command = [sys.executable, "-B", "-m", "src.ball_tracking.crop_retention_output_presence",
               "--manifest", str(context["manifest_path"]), "--repository-root", str(context["root"]), "--worker"]
    event = _run_bounded_supervised(context, command)
    end_context = _metadata(root, manifest_path, True)
    _require(end_context["commit"] == context["commit"] and end_context["spec_sha256"] == context["spec_sha256"],
             "Output-presence authority changed before parent summary release")
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
    result = _worker(root, manifest) if args.worker else run_output_presence(root, manifest, args.dry_run)
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
