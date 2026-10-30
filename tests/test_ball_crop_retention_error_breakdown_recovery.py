"""Invented-only release, budget and transport checks for saved-error recovery.

No production journal, scientific body, media or old synthetic fixture is read.
The 3010-event accounting prefix is constructed in memory; filesystem fixtures
contain only the small new records or fabricated formatter inputs under TEMP.
"""
from __future__ import annotations

import copy
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from src.ball_tracking import crop_retention_error_breakdown as original
from src.ball_tracking import crop_retention_error_breakdown_recovery as recovery
from src.ball_tracking import crop_retention_error_breakdown_summary as summary
from src.ball_tracking import crop_retention_monitor as monitor
from src.ball_tracking import crop_retention_resources as resources
from test_ball_crop_retention_error_breakdown import SyntheticErrorBreakdown, binding, limits, write_json
from test_ball_crop_retention_error_breakdown_summary import fabricated_audit, fabricated_pool


ORIGINAL_SECONDS = 7.264999999984866


def invented_manifest():
    return {"schema_version": "ball_crop_candidate_retention_error_breakdown_recovery/v0.1",
            "recovery_id": recovery.ID, "output_root": recovery.OUTPUT_ROOT,
            "output_dir": recovery.OUTPUT_DIR, "permitted_stages": ["summarize"],
            "unit_key": recovery.UNIT_KEY, "shared_maximum_seconds": 300,
            "maximum_summary_bytes": 65536, "scientific_inputs": copy.deepcopy(recovery.SCIENTIFIC_INPUTS),
            **{key: {"path": path, "sha256": "f" * 64}
               for key, path in recovery.AUTHORITY_PATHS.items()},
            "frozen_history": {"path": recovery.FROZEN_HISTORY_PATH, "sha256": recovery.FROZEN_HISTORY_SHA},
            "implementation_validation": {"path": recovery.CERTIFICATE_PATH, "sha256": "e" * 64},
            "post_commit_checkpoint": recovery.POST_COMMIT_PATH,
            "selected_method": None, "selected_operating_point": None, "quality_gate": None}


def invented_prefix():
    """Same role/count/time boundaries as history, with no historical payloads."""
    events = []
    identifiers = sorted(original.KNOWN_FAILURES) + [f"{index:032x}" for index in range(3, 57)]

    def append(kind, aid, **details):
        value = {"kind": kind, "attempt_id": aid,
                 "sha256": f"{len(events) + 1:064x}", **details}
        events.append(value)
        return value

    for index, aid in enumerate(identifiers):
        append("started", aid, unit_key=f"invented:{index}",
               selection_unit=False, reserved_seconds=14400.0)
        if index == 56:
            for _ in range(2888):
                append("sample", aid, elapsed_seconds=0.0)
        append("finished", aid,
               elapsed_seconds=1.0 if index < 56 else original.USED_SECONDS - 56.0,
               success=index >= 3, worker_result=None if index < 3 else
               {"path": f"attempts/{aid}.result.json", "sha256": "a" * 64})
    events[-1]["sha256"] = original.PREFIX_TIP
    aid = recovery.FAILED_ATTEMPT
    append("started", aid, unit_key=original.UNIT_KEY,
           selection_unit=False, reserved_seconds=300.0)
    for elapsed in (0.0, .25, .5, .75, 1.0, 2.0):
        append("sample", aid, elapsed_seconds=elapsed)
    append("finished", aid, elapsed_seconds=ORIGINAL_SECONDS, success=False,
           worker_result=None, failure="ResourceLimitError: Output tree did not stabilize for complete byte accounting")
    events[-1]["sha256"] = recovery.PREFIX_TIP
    return events


class TemporaryRoot(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="ebr_")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()


class RecoveryBudgetTests(TemporaryRoot):
    def journal(self, events=None, approved=None):
        journal = recovery.RecoveryJournal.__new__(recovery.RecoveryJournal)
        journal.root = self.root
        journal.folder = self.root / "resource_events"
        journal.events = invented_prefix() if events is None else events
        journal.limits = limits() if approved is None else approved
        return journal

    def test_exact_prefix_is_58_closed_attempts_and_3010_events(self):
        journal = self.journal()
        self.assertEqual(len(journal.events), 3010)
        attempts = journal._attempts()
        self.assertEqual(len(attempts), 58)
        self.assertTrue(all(row["finished"] is not None for row in attempts.values()))
        self.assertEqual(sum(row["finished"]["success"] for row in attempts.values()), 54)
        self.assertEqual({aid for aid, row in attempts.items() if not row["finished"]["success"]},
                         original.KNOWN_FAILURES | {recovery.FAILED_ATTEMPT})
        self.assertAlmostEqual(journal.consumed(), recovery.USED_SECONDS, places=7)
        self.assertEqual(journal.consumed(original.UNIT_KEY), ORIGINAL_SECONDS)

    def test_reservation_reuses_original_300_seconds_and_preserves_global_balance(self):
        journal = self.journal()
        before = copy.deepcopy(journal.events)
        attempt, reserved = journal.reserve(recovery.UNIT_KEY, False)
        self.assertAlmostEqual(reserved, 292.73500000001513, places=7)
        self.assertAlmostEqual(journal.limits["maximum_cumulative_seconds"] - recovery.USED_SECONDS,
                               11132.492000000013, places=7)
        self.assertEqual(journal.events[:-1], before)
        self.assertEqual(journal.events[-1]["unit_key"], recovery.UNIT_KEY)
        self.assertIs(journal.events[-1]["selection_unit"], False)
        seal = json.loads((self.root / "attempts" / (attempt + ".reservation.json")).read_text())
        self.assertEqual(seal, {"event_sha256": journal.events[-1]["sha256"]})

    def test_smaller_cumulative_balance_controls_reservation(self):
        approved = limits()
        approved["maximum_cumulative_seconds"] = recovery.USED_SECONDS + 2.0
        journal = self.journal(approved=approved)
        _, reserved = journal.reserve(recovery.UNIT_KEY, False)
        self.assertAlmostEqual(reserved, 2.0, places=7)

    def test_other_role_selection_or_second_reservation_cannot_run(self):
        for key, selection in ((original.UNIT_KEY, False), (recovery.UNIT_KEY, True),
                               ("unapproved", False)):
            with self.subTest(key=key, selection=selection):
                journal = self.journal()
                with self.assertRaises((ValueError, resources.ResourceLimitError)):
                    journal.reserve(key, selection)
                self.assertEqual(len(journal.events), 3010)
        journal = self.journal()
        journal.reserve(recovery.UNIT_KEY, False)
        with self.assertRaises((ValueError, resources.ResourceLimitError)):
            journal.reserve(recovery.UNIT_KEY, False)

    def test_prefix_count_tip_and_original_failure_identity_are_required(self):
        changes = (lambda e: e.pop(0),
                   lambda e: e[-1].__setitem__("sha256", "0" * 64),
                   lambda e: e[-1].__setitem__("success", True),
                   lambda e: e[-8].__setitem__("unit_key", "unapproved-original"))
        for change in changes:
            with self.subTest(change=change):
                events = invented_prefix()
                change(events)
                journal = self.journal(events)
                with self.assertRaises((ValueError, resources.ResourceLimitError)):
                    journal.reserve(recovery.UNIT_KEY, False)

    def test_unknown_suffix_and_exhausted_budget_are_rejected(self):
        events = invented_prefix()
        events.append({"kind": "started", "attempt_id": "e" * 32,
                       "unit_key": "unknown", "selection_unit": False,
                       "reserved_seconds": 1.0, "sha256": "f" * 64})
        with self.assertRaises((ValueError, resources.ResourceLimitError)):
            self.journal(events).reserve(recovery.UNIT_KEY, False)
        approved = limits()
        approved["maximum_cumulative_seconds"] = recovery.USED_SECONDS - 1
        with self.assertRaises((ValueError, resources.ResourceLimitError)):
            self.journal(approved=approved).reserve(recovery.UNIT_KEY, False)


class MonitorRoutingTests(TemporaryRoot):
    def context(self):
        return {"root": self.root, "output_root": self.root / "invented_output",
                "limits": limits()}

    def test_new_monitor_receives_scoped_journal_and_exact_role(self):
        context, command = self.context(), ["invented-python", "-B", "invented-worker"]
        baseline = resources.BudgetJournal
        completion = {"success": True, "attempt_id": "a" * 32}
        with patch.object(monitor, "run_supervised", return_value=completion) as launch, \
             patch.object(resources, "run_supervised", side_effect=AssertionError("legacy supervisor")):
            self.assertIs(recovery._run_bounded_supervised(context, command), completion)
        launch.assert_called_once_with(context["output_root"], recovery.UNIT_KEY, command,
                                       context["limits"], cwd=self.root, selection_unit=False,
                                       poll_seconds=.25, require_result=True,
                                       journal_factory=recovery.RecoveryJournal)
        self.assertIs(resources.BudgetJournal, baseline)

    def test_monitor_failure_propagates_once_without_journal_replacement(self):
        baseline = resources.BudgetJournal
        failure = resources.ResourceLimitError("invented scanner failure")
        with patch.object(monitor, "run_supervised", side_effect=failure) as launch, \
             patch.object(resources, "run_supervised", side_effect=AssertionError("legacy supervisor")):
            with self.assertRaises(resources.ResourceLimitError) as caught:
                recovery._run_bounded_supervised(self.context(), ["invented-worker"])
        self.assertIs(caught.exception, failure)
        launch.assert_called_once()
        self.assertIs(resources.BudgetJournal, baseline)


class ReleaseGateTests(TemporaryRoot):
    def test_scope_keeps_three_inputs_one_role_and_no_selection(self):
        manifest = invented_manifest()
        recovery._validate_manifest(manifest)
        changes = ({"unit_key": original.UNIT_KEY}, {"shared_maximum_seconds": 301},
                   {"output_dir": original.OUTPUT_DIR}, {"permitted_stages": ["train"]},
                   {"selected_method": "invented-choice"},
                   {"scientific_inputs": {**manifest["scientific_inputs"], "extra": {}}})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                recovery._validate_manifest({**manifest, **change})

    def test_dirty_tree_stops_before_manifest_history_or_scientific_reads(self):
        failure = ValueError("invented dirty tree")
        with patch.object(original.original, "_clean_checkpoint", side_effect=failure), \
             patch.object(recovery, "read_json", side_effect=AssertionError("manifest read")), \
             patch.object(original, "_metadata", side_effect=AssertionError("historical read")), \
             patch.object(original, "_load_scientific_json", side_effect=AssertionError("scientific read")):
            with self.assertRaises(ValueError) as caught:
                recovery._metadata(self.root, self.root / recovery.MANIFEST_PATH)
        self.assertIs(caught.exception, failure)

    def test_missing_checkpoint_stops_before_authorities_history_and_dispatch(self):
        path = self.root / recovery.MANIFEST_PATH
        write_json(path, invented_manifest())
        with patch.object(original.original, "_clean_checkpoint", return_value="b" * 40), \
             patch.object(recovery, "verify_binding", side_effect=AssertionError("authority read")), \
             patch.object(original, "_metadata", side_effect=AssertionError("historical read")), \
             patch.object(recovery, "_run_bounded_supervised", side_effect=AssertionError("dispatch")):
            for dry in (False, True):
                with self.subTest(dry_run=dry), self.assertRaisesRegex(ValueError, "checkpoint is absent"):
                    recovery.run_error_breakdown_recovery(self.root, path, dry_run=dry)

    def test_checkpoint_binds_new_commit_manifest_certificate_and_explicit_release(self):
        manifest, commit = invented_manifest(), "b" * 40
        manifest_path = self.root / recovery.MANIFEST_PATH
        write_json(manifest_path, manifest)
        checkpoint = {
            "schema_version": "ball_crop_candidate_retention_error_breakdown_recovery_execution_checkpoint/v0.1",
            "head": commit, "branch": "codex/ball-detector-baseline",
            "manifest": binding(self.root, manifest_path),
            "implementation_validation": manifest["implementation_validation"],
            "manifest_spec_sha256": recovery._spec_sha256(manifest),
            "failed_prefix_tip_sha256": recovery.PREFIX_TIP,
            **{key: True for key in ("execution_authorized", "clean", "index_empty", "validated_sources_unchanged")}}
        path = self.root / recovery.POST_COMMIT_PATH
        write_json(path, checkpoint)
        with patch.object(recovery.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as git:
            self.assertEqual(recovery._post_commit_checkpoint(self.root, manifest, commit), checkpoint)
            git.assert_called_once_with(["git", "merge-base", "--is-ancestor", recovery.BASE_COMMIT, commit], cwd=self.root)
            for key, value in (("head", recovery.BASE_COMMIT), ("branch", "main"),
                               ("manifest_spec_sha256", "0" * 64), ("failed_prefix_tip_sha256", "0" * 64),
                               ("implementation_validation", {"path": "old-certificate.json", "sha256": "e" * 64}),
                               ("execution_authorized", False), ("clean", False),
                               ("index_empty", False), ("validated_sources_unchanged", False)):
                write_json(path, {**checkpoint, key: value})
                with self.subTest(key=key), self.assertRaises(ValueError):
                    recovery._post_commit_checkpoint(self.root, manifest, commit)
            write_json(path, checkpoint)
            with self.assertRaises(ValueError):
                recovery._post_commit_checkpoint(self.root, manifest, recovery.BASE_COMMIT)


class CertificateTests(TemporaryRoot):
    def fixture(self):
        manifest = invented_manifest()
        paths = [self.root / name for name in ("src/invented.py", "tests/test_invented.py", "requirements.txt")]
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# invented current source\n", encoding="utf-8")
        evidence = self.root / recovery.IMPLEMENTATION_DIR / "invented_validation.json"
        write_json(evidence, {"invented": True})
        value = {"schema_version": "ball_crop_candidate_retention_error_breakdown_recovery_implementation_validation/v0.1",
                 "manifest_spec_sha256": recovery._spec_sha256(manifest),
                 "authority_sha256": {key: manifest[key]["sha256"] for key in recovery.AUTHORITY_FIELDS},
                 **{key: True for key in ("focused_tests_passed", "full_suite_passed", "independent_static_review_passed",
                                         "integrity_tests_passed", "monitor_design_check_passed")},
                 "source_bindings": [binding(self.root, path) for path in paths],
                 "evidence_bindings": [binding(self.root, evidence)]}
        return manifest, value, paths

    def check(self, manifest, certificate):
        path = self.root / recovery.CERTIFICATE_PATH
        write_json(path, certificate)
        manifest = {**manifest, "implementation_validation": binding(self.root, path)}
        with patch.object(original.original, "_git", return_value="tracked"):
            return recovery._validate_implementation(self.root, manifest)

    def test_new_certificate_covers_current_inventory_without_adopting_old_inventory(self):
        manifest, value, paths = self.fixture()
        old_certificate = self.root / "old_administrative_certificate.json"
        write_json(old_certificate, {"source_bindings": [binding(self.root, paths[0])]})
        self.assertEqual(self.check(manifest, value), value)
        old = {**value, "source_bindings": value["source_bindings"][:1]}
        with self.assertRaisesRegex(ValueError, "complete current source inventory"):
            self.check(manifest, old)
        paths[1].write_text("# drift after validation\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.check(manifest, value)

    def test_all_new_validation_gates_and_specification_are_required(self):
        manifest, value, _ = self.fixture()
        for field in ("focused_tests_passed", "full_suite_passed", "independent_static_review_passed",
                      "integrity_tests_passed", "monitor_design_check_passed"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check(manifest, {**value, field: False})
        with self.assertRaises(ValueError):
            self.check(manifest, {**value, "manifest_spec_sha256": "0" * 64})
        with self.assertRaises(ValueError):
            self.check(manifest, {**value, "authority_sha256": {}})

    def test_unapproved_evidence_pointer_is_rejected_before_open(self):
        manifest, value, _ = self.fixture()
        forbidden = original.SCIENTIFIC_INPUTS["audit"]
        value["evidence_bindings"] = [{key: forbidden[key] for key in ("path", "sha256")}]
        real_verify = recovery.verify_binding
        def guard(root, row):
            self.assertNotEqual(row["path"], forbidden["path"])
            return real_verify(root, row)
        with patch.object(recovery, "verify_binding", side_effect=guard), self.assertRaisesRegex(ValueError, "outside"):
            self.check(manifest, value)

    def test_metadata_treats_old_authority_as_history_and_new_certificate_as_current(self):
        manifest = invented_manifest()
        path = self.root / recovery.MANIFEST_PATH
        write_json(path, manifest)
        history_binding = {"path": "invented_old_history.json", "sha256": "7" * 64}
        historical = {"manifest": {"frozen_history": history_binding}, "limits": limits()}
        preparation = {"schema_version": "error_breakdown_recovery_proposal_preparation/v0.1",
                       "head": recovery.BASE_COMMIT, "original_frozen_history": history_binding,
                       "sealed_holdouts_metadata_only": original.HOLDOUTS, "scientific_bodies_read_or_hashed": False}
        integration = {"schema_version": "ball_crop_candidate_retention_error_breakdown_recovery_integration_approval/v0.1",
                       "approved_by": "Ryan", "maximum_new_recovery_attempts": 1,
                       "design": manifest["integration_design"],
                       "recovery_authorization": manifest["recovery_authorization"],
                       "monitor_authorization": manifest["monitor_authorization"],
                       **{key: True for key in ("implementation_authorized", "focused_validation_authorized",
                           "full_regression_authorized", "operational_amendment_approved", "scientific_scope_unchanged", "clean_commit_required")},
                       **{key: False for key in ("scientific_execution_authorized_by_this_record", "git_mutations_authorized",
                                                "training_authorized", "automatic_retry_authorized")}}
        approval = {"conditional_execution_authorized": True, "maximum_new_recovery_attempts": 1,
                    "scientific_scope_unchanged": True, "proposal": manifest["recovery_proposal"],
                    "frozen_metadata": manifest["frozen_history"], "failed_attempt_id": recovery.FAILED_ATTEMPT,
                    "shared_original_and_recovery_maximum_seconds": 300}
        records = {manifest["integration_authorization"]["path"]: integration,
                   manifest["recovery_authorization"]["path"]: approval,
                   manifest["monitor_authorization"]["path"]: {"implementation_authorized": True,
                        "historical_limits_journal_and_consumed_budgets_preserved": True},
                   manifest["frozen_history"]["path"]: preparation}
        current = {"invented_current_certificate": True}
        with patch.object(original.original, "_clean_checkpoint", return_value="b" * 40), \
             patch.object(original.original, "_git", return_value="tracked"), \
             patch.object(recovery, "_post_commit_checkpoint", return_value={"invented_release": True}), \
             patch.object(recovery, "verify_binding"), \
             patch.object(recovery, "_read_bound", side_effect=lambda root, row: records[row["path"]]), \
             patch.object(original, "_metadata", return_value=historical) as old_metadata, \
             patch.object(recovery, "_validate_implementation", return_value=current) as current_validation, \
             patch.object(recovery.subprocess, "run", return_value=SimpleNamespace(returncode=0)), \
             patch.object(original, "_load_scientific_json", side_effect=AssertionError("parent scientific read")):
            result = recovery._metadata(self.root, path, True)
        old_metadata.assert_called_once_with(self.root, self.root / original.MANIFEST_PATH, False)
        current_validation.assert_called_once_with(self.root, manifest)
        self.assertIs(result["original_context"], historical)
        self.assertIs(result["certificate"], current)


class CompactHistory:
    """Real sealed invented57+1 history, using122 events rather than3010 files."""
    def __init__(self, root):
        self.old = SyntheticErrorBreakdown(root)
        self.root, self.output, self.journal = root, self.old.output, self.old.journal
        aid = recovery.FAILED_ATTEMPT
        with patch.object(resources, "_write_new", side_effect=write_json):
            started = self.journal.append("started", attempt_id=aid, unit_key=original.UNIT_KEY,
                                          selection_unit=False, reserved_seconds=300.0)
            write_json(self.output / "attempts" / (aid + ".reservation.json"), {"event_sha256": started["sha256"]})
            for elapsed in (0., .25, .5, .75, 1., 2.):
                self.journal.append("sample", attempt_id=aid, elapsed_seconds=elapsed)
            failed = self.journal.append("finished", attempt_id=aid, elapsed_seconds=ORIGINAL_SECONDS,
                success=False, worker_result=None, failure="ResourceLimitError: invented accounting deadline")
        history = {"journal_prefix": {"event_count": len(self.journal.events), "tip_sha256": failed["sha256"],
                     "raw_event_bindings": [binding(root, path) for path in sorted((self.output / "resource_events").glob("*.json"))]},
                   "failure_completion": failed}
        self.context = {"root": root, "output_root": self.output, "limits": self.old.limits,
                        "history": history, "original_context": self.old.context,
                        "policy": monitor.monitoring_policy(self.old.limits, .25)}

    def scope(self):
        stack = ExitStack()
        stack.enter_context(patch.object(recovery, "PREFIX_COUNT", len(self.context["history"]["journal_prefix"]["raw_event_bindings"])))
        stack.enter_context(patch.object(recovery, "PREFIX_TIP", self.context["history"]["journal_prefix"]["tip_sha256"]))
        stack.enter_context(patch.object(recovery, "USED_SECONDS", 57.0 + ORIGINAL_SECONDS))
        return stack


class HistoryIntegrationTests(TemporaryRoot):
    def test_closed_original_failure_is_preserved_and_no_body_pointer_followed(self):
        fixture = CompactHistory(self.root)
        real_verify = recovery.verify_binding
        def administrative_only(root, row):
            self.assertTrue("/resource_events/" in row["path"] or "/attempts/" in row["path"])
            return real_verify(root, row)
        with fixture.scope(), patch.object(recovery, "verify_binding", side_effect=administrative_only):
            journal = recovery.verify_history(self.root, fixture.context)
        self.assertEqual(len(journal._attempts()), 58)
        self.assertAlmostEqual(journal.consumed(original.UNIT_KEY), ORIGINAL_SECONDS)
        failed_result = fixture.output / "attempts" / (recovery.FAILED_ATTEMPT + ".result.json")
        write_json(failed_result, {"must_not_be_adopted": True})
        with fixture.scope(), self.assertRaises(ValueError):
            recovery.verify_history(self.root, fixture.context)

    def test_missing_old_seal_and_unknown_suffix_fail_without_repair(self):
        fixture = CompactHistory(self.root)
        path = self.root / fixture.old.history["journal_prefix"]["attempts"][0]["completion"]["path"]
        saved = path.read_bytes()
        path.unlink()
        with fixture.scope(), self.assertRaises((ValueError, FileNotFoundError)):
            recovery.verify_history(self.root, fixture.context)
        self.assertFalse(path.exists())
        path.write_bytes(saved)
        with patch.object(resources, "_write_new", side_effect=write_json):
            fixture.journal.append("started", attempt_id="e" * 32, unit_key="unknown-role",
                                   selection_unit=False, reserved_seconds=1.)
        with fixture.scope(), self.assertRaisesRegex(ValueError, "no retry or unknown suffix"):
            recovery.verify_history(self.root, fixture.context)

    def test_only_current_owned_recovery_reservation_can_reach_worker(self):
        fixture = CompactHistory(self.root)
        with fixture.scope():
            journal = recovery.RecoveryJournal(fixture.output, fixture.old.limits)
            aid, seconds = journal.reserve(recovery.UNIT_KEY, False)
            policy = fixture.context["policy"]
            policy_path = fixture.output / "attempts" / (aid + ".monitoring_policy.json")
            write_json(policy_path, {"policy": policy, "sha256": resources._digest(policy)})
            with patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": aid}):
                checked = recovery.verify_history(self.root, fixture.context, "worker")
                self.assertEqual(checked._attempts()[aid]["start"]["reserved_seconds"], seconds)
                with self.assertRaises(ValueError):
                    recovery.verify_history(self.root, fixture.context, "before")
                with self.assertRaises(ValueError):
                    recovery.verify_history(self.root, fixture.context, "completed")
            with patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": "a" * 32}), self.assertRaises(ValueError):
                recovery.verify_history(self.root, fixture.context, "worker")
            write_json(policy_path, {"policy": policy, "sha256": "0" * 64})
            with patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": aid}), self.assertRaisesRegex(ValueError, "Monitor policy"):
                recovery.verify_history(self.root, fixture.context, "worker")


class CompletionPolicyTests(unittest.TestCase):
    def fixture(self):
        approved = limits()
        policy = monitor.monitoring_policy(approved, .25)
        digest = resources._digest(policy)
        seconds = 300.0 - ORIGINAL_SECONDS
        scan = {"schema_version": monitor.RESPONSE_VERSION, "request_id": "e" * 32,
                "requested_at": 10., "scan_started_at": 10.1, "completed_at": 10.2,
                "output_bytes": 2048, "success": True, "error": None, "policy_sha256": digest}
        event = {"success": True, "exit_code": 0, "failure": None, "final_accounting_error": None,
                 "worker_result": {"path": "invented-result.json", "sha256": "a" * 64},
                 "owned_cleanup_verified": True, "cleanup_errors": [], "monitoring_policy_sha256": digest,
                 "time_budget_seconds": seconds, "elapsed_seconds": 2., "charged_elapsed_seconds": 2.,
                 "total_wall_seconds_before_publication": 3., "time_overshoot_seconds": 0.,
                 "memory_overshoot_bytes": 0, "output_overshoot_bytes": 0,
                 "maximum_monitor_interval_seconds": .25, "monitor_samples": 2, "completed_scans": 2,
                 "peak_worker_memory_bytes": 1024, "maximum_output_bytes": 2048,
                 "final_accounting_output_bound_bytes": 2048 + 65536,
                 "minimum_free_disk_bytes": 51 * 1024**3, "final_scan": scan}
        return event, {"limits": approved, "policy": policy}, seconds

    def test_success_requires_closed_ownership_two_scans_and_original_budget(self):
        event, context, seconds = self.fixture()
        recovery._successful_completion(event, context, seconds)
        changes = ({"owned_cleanup_verified": False}, {"cleanup_errors": ["descendant still live"]},
                   {"completed_scans": 1}, {"maximum_monitor_interval_seconds": 1.01},
                   {"time_budget_seconds": 300}, {"elapsed_seconds": seconds + .01},
                   {"minimum_free_disk_bytes": 50 * 1024**3 - 1},
                   {"peak_worker_memory_bytes": 8 * 1024**3 + 1},
                   {"final_accounting_error": "incomplete"}, {"worker_result": None})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                recovery._successful_completion({**event, **change}, context, seconds)

    def test_partial_malformed_or_understated_final_scan_never_passes(self):
        event, context, seconds = self.fixture()
        for change in ({"success": False}, {"output_bytes": True}, {"completed_at": 20.},
                       {"output_bytes": 2049}, {"requested_at": float("nan")},
                       {"policy_sha256": "0" * 64}):
            wrong = {**event, "final_scan": {**event["final_scan"], **change}}
            with self.subTest(change=change), self.assertRaises(ValueError):
                recovery._successful_completion(wrong, context, seconds)


class PreservationTests(TemporaryRoot):
    def fixture(self):
        output = self.root / recovery.OUTPUT_ROOT
        output.mkdir(parents=True)
        saved = output / "invented_evidence.bin"
        saved.write_bytes(b"invented prior evidence")
        history = {"preserved_files": [{"path": saved.relative_to(self.root).as_posix(), **original._stat_metadata(saved)}],
                   "preserved_directories": [recovery.OUTPUT_ROOT],
                   "preserved_absent_paths": [recovery.OUTPUT_ROOT + "/" + recovery.OUTPUT_DIR,
                                              recovery.OUTPUT_ROOT + "/supervisor.lock"]}
        protection = {"sealed_holdouts_metadata_only": original.HOLDOUTS,
                      "preserved_absent_paths": ["data/outputs/ball_tracking/detections/invented_embargo_" + str(i) for i in range(9)]}
        return saved, {"output_root": output, "history": history, "original_context": {"protection": protection}}

    def test_preservation_uses_only_metadata_and_rejects_change_without_repair(self):
        saved, context = self.fixture()
        with patch.object(Path, "read_bytes", side_effect=AssertionError("body read")), \
             patch.object(Path, "open", side_effect=AssertionError("body opened")):
            recovery._preserved_metadata(self.root, context)
        saved.write_bytes(b"changed invented evidence with a different size")
        changed = saved.read_bytes()
        with self.assertRaisesRegex(ValueError, "metadata changed"):
            recovery._preserved_metadata(self.root, context)
        self.assertEqual(saved.read_bytes(), changed)

    def test_unknown_file_and_existing_destination_are_preserved_on_rejection(self):
        _, context = self.fixture()
        extra = context["output_root"] / "unknown.bin"
        extra.write_bytes(b"keep failed evidence")
        with self.assertRaisesRegex(ValueError, "Unexpected evidence file"):
            recovery._preserved_metadata(self.root, context)
        self.assertEqual(extra.read_bytes(), b"keep failed evidence")
        extra.unlink()  # Explicit mutation of this test's invented fixture only.
        destination = context["output_root"] / recovery.OUTPUT_DIR
        destination.mkdir(parents=True)
        marker = destination / "partial.bin"
        marker.write_bytes(b"earlier partial")
        with self.assertRaises(ValueError):
            recovery._preserved_metadata(self.root, context)
        self.assertEqual(marker.read_bytes(), b"earlier partial")


class TinyWorker:
    def __init__(self, root):
        self.root = root
        self.aid = "d" * 32
        self.output = root / recovery.OUTPUT_ROOT
        (self.output / "audit").mkdir(parents=True)
        (self.output / "attempts").mkdir()
        self.result_path = self.output / "attempts" / (self.aid + ".result.json")
        inputs = {"audit": fabricated_audit(), "representative_pool": fabricated_pool("representative_evaluation"),
                  "challenge_pool": fabricated_pool("challenge_evaluation")}
        self.scientific = {}
        for key, value in inputs.items():
            path = root / "invented_inputs" / (key + ".json")
            write_json(path, value)
            self.scientific[key] = {**binding(root, path), "size_bytes": path.stat().st_size}
        manifest = {**invented_manifest(), "scientific_inputs": self.scientific}
        write_json(root / recovery.POST_COMMIT_PATH, {"invented_checkpoint": True})
        self.context = {"root": root, "manifest_path": root / recovery.MANIFEST_PATH,
                        "manifest": manifest, "commit": "b" * 40, "spec_sha256": "a" * 64,
                        "output_root": self.output, "limits": limits(),
                        "certificate": {"source_bindings": []},
                        "policy": monitor.monitoring_policy(limits(), .25)}
        self.journal = SimpleNamespace(_attempts=lambda: {self.aid: {"start": {"sha256": "c" * 64}}})

    def scope(self):
        stack = ExitStack()
        stack.enter_context(patch.object(resources, "wait_for_supervisor"))
        stack.enter_context(patch.object(recovery, "_metadata", return_value=self.context))
        stack.enter_context(patch.object(recovery, "verify_history", return_value=self.journal))
        self.preservation = stack.enter_context(patch.object(recovery, "_preserved_metadata"))
        stack.enter_context(patch.object(original, "SCIENTIFIC_INPUTS", self.scientific))
        stack.enter_context(patch.object(recovery, "SCIENTIFIC_INPUTS", self.scientific))
        self.loads = stack.enter_context(patch.object(original, "_load_scientific_json", wraps=original._load_scientific_json))
        stack.enter_context(patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": self.aid,
                            "BALL_RETENTION_RESULT_PATH": str(self.result_path)}))
        return stack


class WorkerIntegrationTests(TemporaryRoot):
    def test_owned_worker_reads_only_three_inputs_and_copies_48_rows_with_new_provenance(self):
        fixture = TinyWorker(self.root)
        with fixture.scope():
            result = recovery._worker(self.root, fixture.context["manifest_path"])
        self.assertEqual(result, {"worker_result_written": True, "attempt_id": fixture.aid, "completion_pending": True})
        self.assertEqual([call.args[2] for call in fixture.loads.call_args_list],
                         ["audit", "representative_pool", "challenge_pool"])
        destination = fixture.output / recovery.OUTPUT_DIR
        copied = json.loads((destination / "breakdown.json").read_text(encoding="utf-8"))
        text = (destination / "summary.md").read_text(encoding="utf-8")
        self.assertEqual([len(pool["rows"]) for pool in copied["pools"]], [24, 24])
        self.assertEqual(text.count("[saved row]"), 48)
        self.assertLessEqual(len(text.encode("utf-8")), 65536)
        self.assertTrue(all(copied[key] is None for key in summary.DECISIONS))
        provenance = json.loads((destination / "provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(provenance["preserved_failed_attempt_id"], recovery.FAILED_ATTEMPT)
        self.assertEqual(provenance["unit_key"], recovery.UNIT_KEY)
        self.assertEqual(provenance["implementation_validation"], fixture.context["manifest"]["implementation_validation"])
        self.assertEqual(provenance["post_commit_checkpoint"], binding(self.root, self.root / recovery.POST_COMMIT_PATH))
        self.assertFalse((fixture.output / original.OUTPUT_DIR).exists())
        receipt = json.loads(fixture.result_path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["summary_payload"]["text"], text)
        self.assertLessEqual(fixture.result_path.stat().st_size, monitor.WORKER_RECEIPT_LIMIT)
        self.assertEqual(fixture.preservation.call_args_list[-1].kwargs, {"allow_outputs": True})

    def test_wrong_result_destination_stops_before_any_scientific_load(self):
        fixture = TinyWorker(self.root)
        with fixture.scope(), patch.dict(os.environ, {"BALL_RETENTION_RESULT_PATH": str(self.root / "wrong.json")}):
            with self.assertRaisesRegex(ValueError, "another reservation"):
                recovery._worker(self.root, fixture.context["manifest_path"])
        fixture.loads.assert_not_called()
        self.assertFalse(fixture.result_path.exists())

    def test_scientific_reader_requires_owned_role_and_exact_bound_input(self):
        fixture = TinyWorker(self.root)
        with patch.object(original, "SCIENTIFIC_INPUTS", fixture.scientific), \
             patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "active supervised worker"):
                original._load_scientific_json(self.root, fixture.context, "audit")
        with fixture.scope():
            wrong = copy.deepcopy(fixture.context)
            wrong["manifest"]["scientific_inputs"]["audit"]["sha256"] = "0" * 64
            with self.assertRaises(ValueError):
                original._load_scientific_json(self.root, wrong, "audit")
            with self.assertRaises(ValueError):
                original._load_scientific_json(self.root, fixture.context, "unapproved")

    def test_existing_destination_is_not_overwritten_or_receipted(self):
        fixture = TinyWorker(self.root)
        destination = fixture.output / recovery.OUTPUT_DIR
        destination.mkdir()
        marker = destination / "summary.md"
        marker.write_bytes(b"preserve earlier partial")
        with fixture.scope(), self.assertRaises(ValueError):
            recovery._worker(self.root, fixture.context["manifest_path"])
        self.assertEqual(marker.read_bytes(), b"preserve earlier partial")
        self.assertFalse(fixture.result_path.exists())

    def test_final_preservation_failure_keeps_outputs_but_never_certifies_completion(self):
        fixture = TinyWorker(self.root)
        failure = ValueError("invented preserved metadata drift")
        with fixture.scope():
            fixture.preservation.side_effect = [None, failure]
            with self.assertRaises(ValueError) as caught:
                recovery._worker(self.root, fixture.context["manifest_path"])
        self.assertIs(caught.exception, failure)
        self.assertEqual(len(list((fixture.output / recovery.OUTPUT_DIR).iterdir())), 3)
        self.assertFalse(fixture.result_path.exists())
        self.assertEqual(fixture.loads.call_count, 3)


class ReceiptTransportTests(TemporaryRoot):
    def fixture(self, text="Invented bounded summary; no scientific body reads."):
        output = self.root / recovery.OUTPUT_ROOT
        paths = [output / name for name in recovery.OUTPUTS]
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode("utf-8") if path.name == "summary.md" else b'{"inert":"/must/not/open"}')
        aid = "d" * 32
        context = {"commit": "b" * 40, "spec_sha256": "a" * 64}
        payload = text.encode("utf-8")
        receipt = {"schema_version": "ball_crop_candidate_retention_error_breakdown_recovery_worker_result/v0.1",
                   "stage": "summarize", "unit_key": recovery.UNIT_KEY, "attempt_id": aid,
                   **context, "artifacts": [binding(self.root, path) for path in paths],
                   "artifact_metadata": [{"path": path.relative_to(self.root).as_posix(), **original._stat_metadata(path)} for path in paths],
                   "scientific_inputs": recovery.SCIENTIFIC_INPUTS, "checks": recovery.CHECKS,
                   "summary_payload": {"text": text, "size_bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}}
        path = output / "attempts" / (aid + ".result.json")
        write_json(path, receipt)
        event = {"attempt_id": aid, "sha256": "c" * 64,
                 "worker_result": {"path": "attempts/" + aid + ".result.json", "sha256": binding(self.root, path)["sha256"]}}
        return context, receipt, path, event, paths

    def scope(self, event):
        stack = ExitStack()
        stack.enter_context(patch.object(recovery, "verify_history", return_value=SimpleNamespace(events=[event])))
        stack.enter_context(patch.object(recovery, "_preserved_metadata"))
        return stack

    def test_parent_opens_only_bounded_receipt_and_releases_same_summary(self):
        context, receipt, path, event, paths = self.fixture()
        opened, actual_open = [], Path.open
        def guard(candidate, *args, **kwargs):
            self.assertEqual(candidate, path)
            opened.append(candidate)
            return actual_open(candidate, *args, **kwargs)
        with self.scope(event), patch.object(Path, "open", guard):
            result = recovery._completed_result(self.root, context, event)
        self.assertEqual(opened, [path])
        self.assertEqual(result["summary"], receipt["summary_payload"]["text"])
        self.assertEqual(result["new_model_calls"], 0)
        self.assertFalse(result["scoring_executed"])
        self.assertTrue(all(result[key] is None for key in summary.DECISIONS))

    def test_payload_tampering_and_artifact_metadata_drift_prevent_release(self):
        context, receipt, path, event, paths = self.fixture()
        for change in ({"text": "changed"}, {"size_bytes": True}, {"sha256": "0" * 64}):
            wrong = {**receipt, "summary_payload": {**receipt["summary_payload"], **change}}
            write_json(path, wrong)
            event["worker_result"]["sha256"] = binding(self.root, path)["sha256"]
            with self.subTest(change=change), self.scope(event), self.assertRaises(ValueError):
                recovery._completed_result(self.root, context, event)
        write_json(path, receipt)
        event["worker_result"]["sha256"] = binding(self.root, path)["sha256"]
        paths[0].write_bytes(b"metadata drift after the worker receipt")
        with self.scope(event), self.assertRaisesRegex(ValueError, "metadata changed"):
            recovery._completed_result(self.root, context, event)

    def test_summary_and_receipt_bounds_reject_before_unbounded_body_read(self):
        context, _, path, event, _ = self.fixture("x" * (65536 + 1))
        with self.scope(event), self.assertRaisesRegex(ValueError, "bounded receipted"):
            recovery._completed_result(self.root, context, event)
        path.write_bytes(b"x" * (monitor.WORKER_RECEIPT_LIMIT + 1))
        with self.scope(event), patch.object(Path, "open", side_effect=AssertionError("oversized body read")), \
             self.assertRaisesRegex(ValueError, "byte bound"):
            recovery._completed_result(self.root, context, event)


class PublicDispatchTests(TemporaryRoot):
    def test_one_new_worker_command_no_retry_when_monitor_fails(self):
        path = self.root / recovery.MANIFEST_PATH
        context = {"root": self.root, "manifest_path": path, "commit": "b" * 40,
                   "spec_sha256": "a" * 64}
        failure = resources.ResourceLimitError("invented monitor failure")
        with patch.object(recovery, "_metadata", return_value=context) as metadata, \
             patch.object(recovery, "verify_history"), patch.object(recovery, "_preserved_metadata"), \
             patch.object(recovery, "_run_bounded_supervised", side_effect=failure) as launch, \
             patch.object(recovery, "_completed_result", side_effect=AssertionError("failed result release")):
            with self.assertRaises(resources.ResourceLimitError) as caught:
                recovery.run_error_breakdown_recovery(self.root, path)
        self.assertIs(caught.exception, failure)
        metadata.assert_called_once_with(self.root, path, True)
        launch.assert_called_once_with(context, [recovery.sys.executable, "-B", "-m",
            "src.ball_tracking.crop_retention_error_breakdown_recovery", "--manifest", str(path),
            "--repository-root", str(self.root), "--worker"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
