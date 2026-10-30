"""Invented-only release, one-attempt budget and worker transport boundaries.

Production scientific files, journals and media are never used as fixtures.
The full 3071-event prefix lives in memory; sealed file histories stay tiny.
"""
from __future__ import annotations

import copy
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.ball_tracking import crop_retention_error_breakdown as original
from src.ball_tracking import crop_retention_error_breakdown_recovery as recovery
from src.ball_tracking import crop_retention_error_breakdown_summary as old_summary
from src.ball_tracking import crop_retention_output_presence as presence
from src.ball_tracking import crop_retention_monitor as monitor
from src.ball_tracking import crop_retention_resources as resources
from test_ball_crop_retention_error_breakdown import binding, limits, write_json
import test_ball_crop_retention_error_breakdown_recovery as recovery_fixtures
from test_ball_crop_retention_error_breakdown_summary import fabricated_audit, fabricated_pool


def completion_event(seconds=52.547, reservation=292.73500000001513):
    policy = monitor.monitoring_policy(limits(), .25)
    digest = resources._digest(policy)
    return {"success": True, "exit_code": 0, "failure": None, "final_accounting_error": None,
            "worker_result": {"path": "attempts/" + presence.PREDECESSOR_ATTEMPT + ".result.json",
                              "sha256": presence.PREDECESSOR_RESULT_SHA},
            "owned_cleanup_verified": True, "cleanup_errors": [], "monitoring_policy_sha256": digest,
            "time_budget_seconds": reservation, "elapsed_seconds": seconds, "charged_elapsed_seconds": seconds,
            "total_wall_seconds_before_publication": seconds + 1, "time_overshoot_seconds": 0.,
            "memory_overshoot_bytes": 0, "output_overshoot_bytes": 0,
            "maximum_monitor_interval_seconds": .25, "monitor_samples": 59, "completed_scans": 2,
            "peak_worker_memory_bytes": 1024, "maximum_output_bytes": 2048,
            "final_accounting_output_bound_bytes": 2048 + 65536,
            "minimum_free_disk_bytes": 51 * 1024**3,
            "final_scan": {"schema_version": monitor.RESPONSE_VERSION, "request_id": "e" * 32,
                "requested_at": 10., "scan_started_at": 10.1, "completed_at": 10.2,
                "output_bytes": 2048, "success": True, "error": None, "policy_sha256": digest}}


def invented_prefix():
    """Construct the approved role/count/time boundaries without real payloads."""
    events = recovery_fixtures.invented_prefix()
    aid = presence.PREDECESSOR_ATTEMPT

    def append(kind, **details):
        events.append({"kind": kind, "attempt_id": aid,
                       "sha256": f"{len(events) + 1:064x}", **details})

    append("started", unit_key=recovery.UNIT_KEY, selection_unit=False,
           reserved_seconds=recovery.MAX_UNIT_SECONDS - recovery.FAILED_SECONDS)
    for index in range(59):
        append("sample", elapsed_seconds=index / 2)
    append("finished", **completion_event())
    events[-1]["sha256"] = presence.PREFIX_TIP
    return events


def invented_manifest():
    return {"schema_version": "ball_crop_retention_output_presence_experiment/v0.1",
            "study_id": presence.ID, "output_root": presence.OUTPUT_ROOT,
            "output_dir": presence.OUTPUT_DIR, "permitted_stages": ["summarize"],
            "unit_key": presence.UNIT_KEY, "maximum_unit_seconds": 120,
            "maximum_summary_bytes": 65536,
            "scientific_inputs": copy.deepcopy(presence.SCIENTIFIC_INPUTS),
            **{key: {"path": path, "sha256": "f" * 64}
               for key, path in presence.AUTHORITY_PATHS.items()},
            "proposal": {"path": presence.PROPOSAL_PATH, "sha256": presence.PROPOSAL_SHA},
            "frozen_history": {"path": presence.FROZEN_HISTORY_PATH, "sha256": presence.FROZEN_HISTORY_SHA},
            "implementation_validation": {"path": presence.CERTIFICATE_PATH, "sha256": "e" * 64},
            "post_commit_checkpoint": presence.POST_COMMIT_PATH,
            "selected_method": None, "selected_operating_point": None, "quality_gate": None}


class TemporaryRoot(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="opr_")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()


class PresenceBudgetTests(TemporaryRoot):
    def journal(self, events=None, approved=None):
        journal = presence.PresenceJournal.__new__(presence.PresenceJournal)
        journal.root = self.root
        journal.folder = self.root / "resource_events"
        journal.events = invented_prefix() if events is None else events
        journal.limits = limits() if approved is None else approved
        return journal

    def test_full_prefix_preserves_59_closed_attempts_55_successes_four_failures(self):
        journal = self.journal()
        self.assertEqual(len(journal.events), 3071)
        starts, ends = presence._closed_prefix(journal)
        self.assertEqual(len(starts), 59)
        self.assertEqual(sum(row["success"] is True for row in ends.values()), 55)
        self.assertEqual({aid for aid, row in ends.items() if not row["success"]}, recovery.KNOWN_FAILURES)
        self.assertAlmostEqual(journal.consumed(), presence.USED_SECONDS, places=7)
        self.assertAlmostEqual(journal.consumed(recovery.UNIT_KEY), 52.547, places=7)

    def test_new_120_second_allocation_does_not_renew_old_recovery_budget(self):
        journal = self.journal()
        before = copy.deepcopy(journal.events)
        aid, seconds = journal.reserve(presence.UNIT_KEY, False)
        self.assertEqual(seconds, 120)
        self.assertEqual(journal.events[:-1], before)
        self.assertEqual(journal.events[-1]["unit_key"], presence.UNIT_KEY)
        self.assertIs(journal.events[-1]["selection_unit"], False)
        self.assertAlmostEqual(journal.limits["maximum_cumulative_seconds"] - presence.USED_SECONDS,
                               11079.945000000014, places=7)
        seal = json.loads((self.root / "attempts" / (aid + ".reservation.json")).read_text())
        self.assertEqual(seal, {"event_sha256": journal.events[-1]["sha256"]})

    def test_smaller_cumulative_balance_controls_reservation(self):
        approved = limits()
        approved["maximum_cumulative_seconds"] = presence.USED_SECONDS + 2
        _, seconds = self.journal(approved=approved).reserve(presence.UNIT_KEY, False)
        self.assertAlmostEqual(seconds, 2, places=7)

    def test_prior_roles_selection_unknown_suffix_and_second_attempt_are_rejected(self):
        for key, selection in ((original.UNIT_KEY, False), (recovery.UNIT_KEY, False),
                               (presence.UNIT_KEY, True), ("unapproved", False)):
            with self.subTest(key=key, selection=selection):
                journal = self.journal()
                with self.assertRaises((ValueError, resources.ResourceLimitError)):
                    journal.reserve(key, selection)
                self.assertEqual(len(journal.events), 3071)
        journal = self.journal()
        journal.reserve(presence.UNIT_KEY, False)
        with self.assertRaises((ValueError, resources.ResourceLimitError)):
            journal.reserve(presence.UNIT_KEY, False)

    def test_prefix_tip_counts_success_role_and_charged_seconds_cannot_change(self):
        changes = (lambda e: e.pop(0),
                   lambda e: e[-1].__setitem__("sha256", "0" * 64),
                   lambda e: e[-1].__setitem__("success", False),
                   lambda e: e[-1].__setitem__("elapsed_seconds", 1),
                   lambda e: e[-61].__setitem__("unit_key", "unknown"))
        for change in changes:
            with self.subTest(change=change):
                events = invented_prefix()
                change(events)
                with self.assertRaises((ValueError, resources.ResourceLimitError)):
                    self.journal(events).reserve(presence.UNIT_KEY, False)

    def test_exhausted_budget_and_unknown_suffix_cannot_be_adopted(self):
        approved = limits()
        approved["maximum_cumulative_seconds"] = presence.USED_SECONDS
        with self.assertRaises((ValueError, resources.ResourceLimitError)):
            self.journal(approved=approved).reserve(presence.UNIT_KEY, False)
        events = invented_prefix() + [{"kind": "started", "attempt_id": "f" * 32,
            "unit_key": "unknown", "selection_unit": False, "reserved_seconds": 1., "sha256": "e" * 64}]
        with self.assertRaises((ValueError, resources.ResourceLimitError)):
            self.journal(events).reserve(presence.UNIT_KEY, False)


class ReleaseGateTests(TemporaryRoot):
    def test_manifest_allows_only_one_input_one_unit_and_no_decisions(self):
        manifest = invented_manifest()
        presence._validate_manifest(manifest)
        self.assertEqual(len(presence.SCIENTIFIC_INPUTS), 1)
        changes = ({"unit_key": recovery.UNIT_KEY}, {"maximum_unit_seconds": 121},
                   {"output_dir": recovery.OUTPUT_DIR}, {"permitted_stages": ["train"]},
                   {"selected_method": "invented-choice"},
                   {"scientific_inputs": {**manifest["scientific_inputs"], "extra": {}}})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                presence._validate_manifest({**manifest, **change})

    def test_dirty_tree_stops_before_manifest_history_or_scientific_reads(self):
        failure = ValueError("invented dirty tree")
        with patch.object(original.original, "_clean_checkpoint", side_effect=failure), \
             patch.object(presence, "read_json", side_effect=AssertionError("manifest read")), \
             patch.object(recovery, "_metadata", side_effect=AssertionError("historical read")), \
             patch.object(original, "_load_scientific_json", side_effect=AssertionError("scientific read")):
            with self.assertRaises(ValueError) as caught:
                presence._metadata(self.root, self.root / presence.MANIFEST_PATH)
        self.assertIs(caught.exception, failure)

    def test_missing_checkpoint_stops_before_authorities_history_or_dispatch(self):
        path = self.root / presence.MANIFEST_PATH
        write_json(path, invented_manifest())
        with patch.object(original.original, "_clean_checkpoint", return_value="b" * 40), \
             patch.object(presence, "verify_binding", side_effect=AssertionError("authority read")), \
             patch.object(recovery, "_metadata", side_effect=AssertionError("historical read")), \
             patch.object(presence, "_run_bounded_supervised", side_effect=AssertionError("dispatch")):
            for dry in (False, True):
                with self.subTest(dry_run=dry), self.assertRaisesRegex(ValueError, "checkpoint is absent"):
                    presence.run_output_presence(self.root, path, dry_run=dry)

    def test_administrative_reader_rejects_scientific_input_and_outputs_before_open(self):
        forbidden = [*presence.SCIENTIFIC_INPUTS.values(),
                     *[{"path": presence.OUTPUT_ROOT + "/" + path, "sha256": "a" * 64}
                       for path in presence.OUTPUTS]]
        with patch.object(Path, "open", side_effect=AssertionError("scientific body opened")):
            for row in forbidden:
                with self.subTest(path=row["path"]), self.assertRaises(ValueError):
                    presence._read_bound(self.root, {key: row[key] for key in ("path", "sha256")})

    def test_checkpoint_binds_new_commit_manifest_certificate_and_explicit_release(self):
        manifest, commit = invented_manifest(), "b" * 40
        manifest_path = self.root / presence.MANIFEST_PATH
        write_json(manifest_path, manifest)
        checkpoint = {"schema_version": "ball_crop_retention_output_presence_execution_checkpoint/v0.1",
            "head": commit, "branch": "codex/ball-detector-baseline", "manifest": binding(self.root, manifest_path),
            "implementation_validation": manifest["implementation_validation"],
            "manifest_spec_sha256": presence._spec_sha256(manifest), "preserved_prefix_tip_sha256": presence.PREFIX_TIP,
            **{key: True for key in ("execution_authorized", "clean", "index_empty", "validated_sources_unchanged")}}
        path = self.root / presence.POST_COMMIT_PATH
        write_json(path, checkpoint)
        with patch.object(presence.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as git:
            self.assertEqual(presence._post_commit_checkpoint(self.root, manifest, commit), checkpoint)
            git.assert_called_once_with(["git", "merge-base", "--is-ancestor", presence.BASE_COMMIT, commit], cwd=self.root)
            for key, value in (("head", presence.BASE_COMMIT), ("branch", "main"),
                               ("manifest_spec_sha256", "0" * 64), ("preserved_prefix_tip_sha256", "0" * 64),
                               ("execution_authorized", False), ("clean", False),
                               ("index_empty", False), ("validated_sources_unchanged", False)):
                write_json(path, {**checkpoint, key: value})
                with self.subTest(key=key), self.assertRaises(ValueError):
                    presence._post_commit_checkpoint(self.root, manifest, commit)
            write_json(path, checkpoint)
            with self.assertRaises(ValueError):
                presence._post_commit_checkpoint(self.root, manifest, presence.BASE_COMMIT)


class MonitorRoutingTests(TemporaryRoot):
    def test_validated_monitor_receives_exact_scoped_journal_without_global_override(self):
        context = {"root": self.root, "output_root": self.root / "invented_output", "limits": limits()}
        command = ["invented-python", "-B", "invented-worker"]
        completion = {"success": True, "attempt_id": "a" * 32}
        baseline = resources.BudgetJournal
        with patch.object(monitor, "run_supervised", return_value=completion) as launch, \
             patch.object(resources, "run_supervised", side_effect=AssertionError("legacy supervisor")):
            self.assertIs(presence._run_bounded_supervised(context, command), completion)
        launch.assert_called_once_with(context["output_root"], presence.UNIT_KEY, command, context["limits"],
            cwd=self.root, selection_unit=False, poll_seconds=.25, require_result=True,
            journal_factory=presence.PresenceJournal)
        self.assertIs(resources.BudgetJournal, baseline)

    def test_one_worker_command_and_no_retry_when_monitor_fails(self):
        path = self.root / presence.MANIFEST_PATH
        context = {"root": self.root, "manifest_path": path, "commit": "b" * 40,
                   "spec_sha256": "a" * 64}
        failure = resources.ResourceLimitError("invented monitor failure")
        with patch.object(presence, "_metadata", return_value=context) as metadata, \
             patch.object(presence, "verify_history"), patch.object(presence, "_preserved_metadata"), \
             patch.object(presence, "_run_bounded_supervised", side_effect=failure) as launch, \
             patch.object(presence, "_completed_result", side_effect=AssertionError("failed result release")):
            with self.assertRaises(resources.ResourceLimitError) as caught:
                presence.run_output_presence(self.root, path)
        self.assertIs(caught.exception, failure)
        metadata.assert_called_once_with(self.root, path, True)
        launch.assert_called_once_with(context, [sys.executable, "-B", "-m",
            "src.ball_tracking.crop_retention_output_presence", "--manifest", str(path),
            "--repository-root", str(self.root), "--worker"])


class CertificateTests(TemporaryRoot):
    def fixture(self):
        manifest = invented_manifest()
        paths = [self.root / name for name in ("src/invented.py", "tests/test_invented.py", "requirements.txt")]
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# invented current source\n", encoding="utf-8")
        evidence = self.root / presence.IMPLEMENTATION_DIR / "invented_validation.json"
        write_json(evidence, {"invented": True})
        value = {"schema_version": "ball_crop_retention_output_presence_implementation_validation/v0.1",
                 "manifest_spec_sha256": presence._spec_sha256(manifest),
                 "authority_sha256": {key: manifest[key]["sha256"] for key in presence.AUTHORITY_FIELDS},
                 **{key: True for key in ("focused_tests_passed", "full_suite_passed", "independent_static_review_passed",
                                         "integrity_tests_passed", "monitor_design_check_passed")},
                 "source_bindings": [binding(self.root, path) for path in paths],
                 "evidence_bindings": [binding(self.root, evidence)]}
        return manifest, value, paths

    def check(self, manifest, certificate):
        path = self.root / presence.CERTIFICATE_PATH
        write_json(path, certificate)
        manifest = {**manifest, "implementation_validation": binding(self.root, path)}
        with patch.object(original.original, "_git", return_value="tracked"):
            return presence._validate_implementation(self.root, manifest)

    def test_certificate_requires_complete_current_inventory_and_exact_sources(self):
        manifest, value, paths = self.fixture()
        self.assertEqual(self.check(manifest, value), value)
        with self.assertRaisesRegex(ValueError, "complete current source inventory"):
            self.check(manifest, {**value, "source_bindings": value["source_bindings"][:1]})
        paths[1].write_text("# drift after validation\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.check(manifest, value)

    def test_all_validation_gates_specification_and_authority_are_required(self):
        manifest, value, _ = self.fixture()
        for field in ("focused_tests_passed", "full_suite_passed", "independent_static_review_passed",
                      "integrity_tests_passed", "monitor_design_check_passed"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check(manifest, {**value, field: False})
        with self.assertRaises(ValueError):
            self.check(manifest, {**value, "manifest_spec_sha256": "0" * 64})
        with self.assertRaises(ValueError):
            self.check(manifest, {**value, "authority_sha256": {}})

    def test_scientific_pointer_cannot_be_smuggled_into_validation_evidence(self):
        manifest, value, _ = self.fixture()
        forbidden = next(iter(presence.SCIENTIFIC_INPUTS.values()))
        value["evidence_bindings"] = [{key: forbidden[key] for key in ("path", "sha256")}]
        real_verify = presence.verify_binding

        def guard(root, row):
            self.assertNotEqual(row["path"], forbidden["path"])
            return real_verify(root, row)

        with patch.object(presence, "verify_binding", side_effect=guard), self.assertRaisesRegex(ValueError, "outside"):
            self.check(manifest, value)

    def test_parent_metadata_uses_success_receipt_and_current_certificate_without_scientific_access(self):
        manifest = invented_manifest()
        path = self.root / presence.MANIFEST_PATH
        write_json(path, manifest)
        history = {"schema_version": "ball_crop_retention_output_presence_frozen_history/v0.1",
            "head": presence.BASE_COMMIT, "prefix_count": 3071, "prefix_tip_sha256": presence.PREFIX_TIP,
            "prefix_attempts": 59, "prefix_successes": 55, "known_failures": sorted(presence.KNOWN_FAILURES),
            "limits": limits(), "scientific_bodies_read_or_hashed": False, "consumed_seconds": presence.USED_SECONDS}
        approval = {"schema_version": "ball_crop_retention_output_presence_approval/v0.1",
            "approved_by": "Ryan", "proposal": manifest["proposal"], "maximum_new_attempts": 1,
            "maximum_unit_seconds": 120, "approved_operations": ["ordered_difference", "ordered_intersection", "list_length"],
            **{key: True for key in ("implementation_authorized", "focused_validation_authorized", "full_regression_authorized",
                                    "conditional_execution_authorized", "separate_clean_commit_required", "responsive_monitor_policy_adopted")},
            **{key: False for key in ("parent_scientific_body_access_authorized", "automatic_scientific_retry_authorized",
                                     "semantic_adjudication_authorized", "new_model_inference_authorized", "git_mutations_authorized")}}
        prior_binding = {"path": presence.OUTPUT_ROOT + "/attempts/" + presence.PREDECESSOR_ATTEMPT + ".result.json",
                         "sha256": presence.PREDECESSOR_RESULT_SHA}
        prior = {"success": True, "execution_commit": presence.BASE_COMMIT,
                 "attempt_id": presence.PREDECESSOR_ATTEMPT, "completion_event_chain_sha256": presence.PREFIX_TIP,
                 "authorized_recovery_attempts_remaining": 0, "worker_result_binding_from_verified_return": prior_binding}
        receipt = {"attempt_id": presence.PREDECESSOR_ATTEMPT, "commit": presence.BASE_COMMIT,
                   "artifacts": [{key: presence.SCIENTIFIC_INPUT[key] for key in ("path", "sha256")}],
                   "artifact_metadata": [{key: presence.SCIENTIFIC_INPUT[key] for key in ("path", "size_bytes")}]}
        records = {manifest["authorization"]["path"]: approval, manifest["frozen_history"]["path"]: history,
                   manifest["predecessor_completion"]["path"]: prior, prior_binding["path"]: receipt}
        current = {"invented_current_certificate": True}
        with patch.object(original.original, "_clean_checkpoint", return_value="b" * 40), \
             patch.object(original.original, "_git", return_value="tracked"), \
             patch.object(presence, "_post_commit_checkpoint", return_value={"invented_release": True}), \
             patch.object(presence, "verify_binding"), \
             patch.object(presence, "_read_bound", side_effect=lambda root, row, *args: records[row["path"]]), \
             patch.object(recovery, "_metadata", return_value={"limits": limits()}) as old_metadata, \
             patch.object(presence, "_validate_implementation", return_value=current) as validation, \
             patch.object(presence.subprocess, "run", return_value=SimpleNamespace(returncode=0)), \
             patch.object(presence, "_load_breakdown", side_effect=AssertionError("parent scientific read")), \
             patch.object(original, "_load_scientific_json", side_effect=AssertionError("parent old scientific read")):
            result = presence._metadata(self.root, path, True)
            approval["parent_scientific_body_access_authorized"] = True
            with self.assertRaisesRegex(ValueError, "expands scope"):
                presence._metadata(self.root, path, True)
        old_metadata.assert_called_once_with(self.root, self.root / recovery.MANIFEST_PATH, False)
        validation.assert_called_once_with(self.root, manifest)
        self.assertIs(result["certificate"], current)


class CompactHistory:
    """59 sealed invented attempts with the real attempt boundary and tiny files."""
    def __init__(self, root):
        self.old = recovery_fixtures.CompactHistory(root)
        self.root, self.output, self.journal = root, self.old.output, self.old.journal
        aid = presence.PREDECESSOR_ATTEMPT
        self.result_path = self.output / "attempts" / (aid + ".result.json")
        write_json(self.result_path, {"invented": True, "attempt_id": aid,
                                    "inert_scientific_pointer": "/must/not/open"})
        self.result_sha = binding(root, self.result_path)["sha256"]
        with patch.object(resources, "_write_new", side_effect=write_json):
            start = self.journal.append("started", attempt_id=aid, unit_key=recovery.UNIT_KEY,
                selection_unit=False, reserved_seconds=292.73500000001513)
            write_json(self.output / "attempts" / (aid + ".reservation.json"), {"event_sha256": start["sha256"]})
            completed = completion_event()
            completed["worker_result"]["sha256"] = self.result_sha
            end = self.journal.append("finished", attempt_id=aid, **completed)
        (self.output / "audit").mkdir(exist_ok=True)
        self.count, self.tip, self.used = len(self.journal.events), end["sha256"], self.journal.consumed()
        history = {"raw_event_bindings": [binding(root, path) for path in sorted(self.journal.folder.glob("*.json"))],
                   "administrative_attempt_bindings": [binding(root, path) for path in sorted((self.output / "attempts").glob("*.json"))],
                   "prior_recovery_completion": end,
                   "preserved_files": [{"path": path.relative_to(root).as_posix(), **original._stat_metadata(path)}
                                       for path in self.output.rglob("*") if path.is_file()],
                   "preserved_directories": [path.relative_to(root).as_posix() for path in self.output.rglob("*") if path.is_dir()],
                   "preserved_absent_paths": [presence.OUTPUT_ROOT + "/" + presence.OUTPUT_DIR,
                                              presence.OUTPUT_ROOT + "/supervisor.lock"],
                   "protection": {"sealed_holdouts_metadata_only": original.HOLDOUTS,
                       "preserved_absent_paths": ["data/outputs/ball_tracking/detections/invented_embargo_" + str(i) for i in range(9)]}}
        self.context = {"root": root, "output_root": self.output, "limits": self.old.context["limits"],
                        "history": history, "policy": monitor.monitoring_policy(limits(), .25),
                        "commit": "b" * 40, "spec_sha256": "a" * 64}

    def scope(self):
        stack = self.old.scope()
        for key, value in (("PREFIX_COUNT", self.count), ("PREFIX_TIP", self.tip),
                           ("USED_SECONDS", self.used), ("PREDECESSOR_RESULT_SHA", self.result_sha)):
            stack.enter_context(patch.object(presence, key, value))
        return stack

    def start(self):
        with self.scope():
            journal = presence.PresenceJournal(self.output, self.context["limits"])
            aid, _ = journal.reserve(presence.UNIT_KEY, False)
        self.journal = journal
        policy = self.context["policy"]
        write_json(self.output / "attempts" / (aid + ".monitoring_policy.json"),
                   {"policy": policy, "sha256": resources._digest(policy)})
        return aid


class HistoryIntegrationTests(TemporaryRoot):
    def test_closed_history_verifies_only_administrative_records_and_refuses_new_failure_receipt(self):
        fixture = CompactHistory(self.root)
        real_verify = presence.verify_binding

        def guard(root, row):
            self.assertTrue("/resource_events/" in row["path"] or "/attempts/" in row["path"])
            return real_verify(root, row)

        with fixture.scope(), patch.object(presence, "verify_binding", side_effect=guard):
            journal = presence.verify_history(self.root, fixture.context, "before")
        self.assertEqual(len(journal._attempts()), 59)
        write_json(fixture.output / "attempts" / (recovery.FAILED_ATTEMPT + ".result.json"), {"unreceipted": True})
        with fixture.scope(), self.assertRaises(ValueError):
            presence.verify_history(self.root, fixture.context, "before")

    def test_worker_requires_sole_new_reservation_correct_owner_and_monitor_policy(self):
        fixture = CompactHistory(self.root)
        aid = fixture.start()
        with fixture.scope(), patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": aid}):
            presence.verify_history(self.root, fixture.context, "worker")
            for phase in ("before", "completed"):
                with self.subTest(phase=phase), self.assertRaises(ValueError):
                    presence.verify_history(self.root, fixture.context, phase)
        with fixture.scope(), patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": "a" * 32}), self.assertRaises(ValueError):
            presence.verify_history(self.root, fixture.context, "worker")
        write_json(fixture.output / "attempts" / (aid + ".monitoring_policy.json"),
                   {"policy": fixture.context["policy"], "sha256": "0" * 64})
        with fixture.scope(), patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": aid}), self.assertRaisesRegex(ValueError, "Monitor policy"):
            presence.verify_history(self.root, fixture.context, "worker")

    def test_preservation_never_reads_bodies_and_rejects_unreceipted_files_or_metadata_drift(self):
        fixture = CompactHistory(self.root)
        with patch.object(Path, "open", side_effect=AssertionError("body opened")), \
             patch.object(Path, "read_bytes", side_effect=AssertionError("body read")):
            presence._preserved_metadata(self.root, fixture.context)
        extra = fixture.output / "unknown.bin"
        extra.write_bytes(b"preserve unknown evidence")
        with self.assertRaisesRegex(ValueError, "Unexpected evidence file"):
            presence._preserved_metadata(self.root, fixture.context)
        self.assertEqual(extra.read_bytes(), b"preserve unknown evidence")
        extra.unlink()  # This test owns the entire fabricated temporary tree.
        fixture.result_path.write_bytes(b"changed invented receipt body and size")
        with self.assertRaisesRegex(ValueError, "metadata changed"):
            presence._preserved_metadata(self.root, fixture.context)


class TinyWorker:
    def __init__(self, root):
        self.root, self.aid = root, "d" * 32
        self.output = root / presence.OUTPUT_ROOT
        (self.output / "audit").mkdir(parents=True)
        (self.output / "attempts").mkdir()
        self.result_path = self.output / "attempts" / (self.aid + ".result.json")
        self.input_path = self.output / "audit" / "invented_breakdown.json"
        self.input, _ = old_summary.build_summary([old_summary.extract_pool(fabricated_pool(p), fabricated_audit())
                                                  for p in old_summary.PURPOSES])
        write_json(self.input_path, self.input)
        self.scientific = {**binding(root, self.input_path), "size_bytes": self.input_path.stat().st_size}
        manifest = {**invented_manifest(), "scientific_inputs": {"breakdown": self.scientific}}
        write_json(root / presence.POST_COMMIT_PATH, {"invented_checkpoint": True})
        self.context = {"root": root, "manifest_path": root / presence.MANIFEST_PATH, "manifest": manifest,
                        "commit": "b" * 40, "spec_sha256": "a" * 64, "output_root": self.output,
                        "limits": limits(), "certificate": {"source_bindings": []},
                        "policy": monitor.monitoring_policy(limits(), .25)}
        self.journal = SimpleNamespace(_attempts=lambda: {self.aid: {"start": {"sha256": "c" * 64}}})

    def scope(self):
        stack = ExitStack()
        stack.enter_context(patch.object(resources, "wait_for_supervisor"))
        stack.enter_context(patch.object(presence, "_metadata", return_value=self.context))
        stack.enter_context(patch.object(presence, "verify_history", return_value=self.journal))
        self.preservation = stack.enter_context(patch.object(presence, "_preserved_metadata"))
        stack.enter_context(patch.object(presence, "SCIENTIFIC_INPUT", self.scientific))
        stack.enter_context(patch.object(presence, "SCIENTIFIC_INPUTS", {"breakdown": self.scientific}))
        self.loads = stack.enter_context(patch.object(presence, "_load_breakdown", wraps=presence._load_breakdown))
        stack.enter_context(patch.object(original, "_load_scientific_json", side_effect=AssertionError("old scientific loader")))
        stack.enter_context(patch.object(recovery, "_worker", side_effect=AssertionError("consumed recovery worker")))
        stack.enter_context(patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": self.aid,
                            "BALL_RETENTION_RESULT_PATH": str(self.result_path)}))
        return stack


class WorkerIntegrationTests(TemporaryRoot):
    def test_worker_reads_only_single_bound_input_and_keeps_all_original_rows(self):
        fixture = TinyWorker(self.root)
        opened, actual_open = [], Path.open

        def guard(path, *args, **kwargs):
            opened.append(path)
            return actual_open(path, *args, **kwargs)

        with fixture.scope(), patch.object(Path, "open", guard):
            result = presence._worker(self.root, fixture.context["manifest_path"])
        self.assertEqual(result, {"worker_result_written": True, "attempt_id": fixture.aid, "completion_pending": True})
        fixture.loads.assert_called_once_with(self.root)
        expected = {fixture.input_path, fixture.result_path, self.root / presence.POST_COMMIT_PATH,
                    *[fixture.output / name for name in presence.OUTPUTS]}
        self.assertLessEqual(set(opened), expected)
        self.assertGreaterEqual(opened.count(fixture.input_path), 2)
        destination = fixture.output / presence.OUTPUT_DIR
        result_body = json.loads((destination / "presence.json").read_text(encoding="utf-8"))
        text = (destination / "summary.md").read_text(encoding="utf-8")
        self.assertEqual(result_body["original_breakdown"], fixture.input)
        self.assertEqual(len(result_body["derived_by_row"]), 48)
        self.assertEqual(text.count("[saved row]"), 48)
        self.assertLessEqual(len(text.encode("utf-8")), 65536)
        receipt = json.loads(fixture.result_path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["summary_payload"]["text"], text)
        self.assertEqual(receipt["scientific_inputs"], {"breakdown": fixture.scientific})
        self.assertLessEqual(fixture.result_path.stat().st_size, monitor.WORKER_RECEIPT_LIMIT)
        self.assertEqual(fixture.preservation.call_args_list[-1].kwargs, {"allow_outputs": True})

    def test_wrong_result_destination_stops_before_scientific_load(self):
        fixture = TinyWorker(self.root)
        with fixture.scope(), patch.dict(os.environ, {"BALL_RETENTION_RESULT_PATH": str(self.root / "wrong.json")}):
            with self.assertRaisesRegex(ValueError, "outside its reservation"):
                presence._worker(self.root, fixture.context["manifest_path"])
        fixture.loads.assert_not_called()
        self.assertFalse(fixture.result_path.exists())

    def test_scientific_reader_requires_owner_exact_size_and_hash(self):
        fixture = TinyWorker(self.root)
        with patch.object(presence, "SCIENTIFIC_INPUT", fixture.scientific), patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "owned worker"):
                presence._load_breakdown(self.root)
        with fixture.scope():
            for changes in ({"sha256": "0" * 64}, {"size_bytes": fixture.scientific["size_bytes"] + 1}):
                with self.subTest(changes=changes), patch.object(presence, "SCIENTIFIC_INPUT", {**fixture.scientific, **changes}), \
                     self.assertRaises(ValueError):
                    presence._load_breakdown(self.root)

    def test_existing_destination_is_not_overwritten_or_receipted(self):
        fixture = TinyWorker(self.root)
        destination = fixture.output / presence.OUTPUT_DIR
        destination.mkdir()
        marker = destination / "summary.md"
        marker.write_bytes(b"preserve earlier partial")
        with fixture.scope(), self.assertRaises(ValueError):
            presence._worker(self.root, fixture.context["manifest_path"])
        self.assertEqual(marker.read_bytes(), b"preserve earlier partial")
        self.assertFalse(fixture.result_path.exists())

    def test_input_drift_after_derivation_keeps_partial_outputs_but_never_receipts(self):
        from src.ball_tracking import crop_retention_output_presence_summary as builder
        fixture = TinyWorker(self.root)
        real_build = builder.build_summary

        def build(value):
            result = real_build(value)
            fixture.input_path.write_bytes(b"changed invented source")
            return result

        with fixture.scope(), patch.object(builder, "build_summary", side_effect=build), self.assertRaises(ValueError):
            presence._worker(self.root, fixture.context["manifest_path"])
        self.assertTrue((fixture.output / presence.OUTPUT_DIR / "provenance.json").exists())
        self.assertFalse(fixture.result_path.exists())

    def test_final_preservation_failure_keeps_outputs_without_certifying_completion(self):
        fixture = TinyWorker(self.root)
        failure = ValueError("invented preserved metadata drift")
        with fixture.scope():
            fixture.preservation.side_effect = [None, failure]
            with self.assertRaises(ValueError) as caught:
                presence._worker(self.root, fixture.context["manifest_path"])
        self.assertIs(caught.exception, failure)
        self.assertEqual(len(list((fixture.output / presence.OUTPUT_DIR).iterdir())), 3)
        self.assertFalse(fixture.result_path.exists())

    def test_failed_receipt_publication_preserves_outputs_without_adoption(self):
        fixture = TinyWorker(self.root)
        actual_write = original._write_new

        def write(path, payload):
            if path == fixture.result_path:
                raise OSError("invented receipt publication failure")
            return actual_write(path, payload)

        with fixture.scope(), patch.object(original, "_write_new", side_effect=write), self.assertRaises(OSError):
            presence._worker(self.root, fixture.context["manifest_path"])
        self.assertEqual(len(list((fixture.output / presence.OUTPUT_DIR).iterdir())), 3)
        self.assertFalse(fixture.result_path.exists())


class ReceiptTransportTests(TemporaryRoot):
    def fixture(self, text="Invented bounded summary; no scientific body reads."):
        output = self.root / presence.OUTPUT_ROOT
        paths = [output / name for name in presence.OUTPUTS]
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode("utf-8") if path.name == "summary.md" else b'{"inert":"/must/not/open"}')
        aid = "d" * 32
        context = {"commit": "b" * 40, "spec_sha256": "a" * 64}
        payload = text.encode("utf-8")
        receipt = {"schema_version": "ball_crop_retention_output_presence_worker_result/v0.1",
                   "stage": "summarize", "unit_key": presence.UNIT_KEY, "attempt_id": aid,
                   **context, "artifacts": [binding(self.root, path) for path in paths],
                   "artifact_metadata": [{"path": path.relative_to(self.root).as_posix(), **original._stat_metadata(path)} for path in paths],
                   "scientific_inputs": presence.SCIENTIFIC_INPUTS, "checks": presence.CHECKS,
                   "summary_payload": {"text": text, "size_bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}}
        path = output / "attempts" / (aid + ".result.json")
        write_json(path, receipt)
        event = {"attempt_id": aid, "sha256": "c" * 64,
                 "worker_result": {"path": "attempts/" + aid + ".result.json", "sha256": binding(self.root, path)["sha256"]}}
        return context, receipt, path, event, paths

    def scope(self, event):
        stack = ExitStack()
        stack.enter_context(patch.object(presence, "verify_history", return_value=SimpleNamespace(events=[event])))
        stack.enter_context(patch.object(presence, "_preserved_metadata"))
        return stack

    def test_parent_opens_only_bounded_receipt_and_releases_same_summary(self):
        context, receipt, path, event, _ = self.fixture()
        opened, actual_open = [], Path.open

        def guard(candidate, *args, **kwargs):
            self.assertEqual(candidate, path)
            opened.append(candidate)
            return actual_open(candidate, *args, **kwargs)

        with self.scope(event), patch.object(Path, "open", guard):
            result = presence._completed_result(self.root, context, event)
        self.assertEqual(opened, [path])
        self.assertEqual(result["summary"], receipt["summary_payload"]["text"])
        self.assertEqual(result["new_model_calls"], 0)
        self.assertFalse(result["scoring_executed"])
        self.assertTrue(all(result[key] is None for key in old_summary.DECISIONS))

    def test_payload_tampering_and_artifact_metadata_drift_prevent_release(self):
        context, receipt, path, event, paths = self.fixture()
        for change in ({"text": "changed"}, {"size_bytes": True}, {"sha256": "0" * 64}):
            write_json(path, {**receipt, "summary_payload": {**receipt["summary_payload"], **change}})
            event["worker_result"]["sha256"] = binding(self.root, path)["sha256"]
            with self.subTest(change=change), self.scope(event), self.assertRaises(ValueError):
                presence._completed_result(self.root, context, event)
        write_json(path, receipt)
        event["worker_result"]["sha256"] = binding(self.root, path)["sha256"]
        paths[0].write_bytes(b"metadata drift after the worker receipt")
        with self.scope(event), self.assertRaisesRegex(ValueError, "metadata changed"):
            presence._completed_result(self.root, context, event)

    def test_wrong_receipt_scope_or_incomplete_artifacts_cannot_publish(self):
        context, receipt, path, event, _ = self.fixture()
        for change in ({"unit_key": recovery.UNIT_KEY}, {"commit": "c" * 40},
                       {"scientific_inputs": recovery.SCIENTIFIC_INPUTS}, {"artifacts": receipt["artifacts"][:2]},
                       {"checks": {**receipt["checks"], "unapproved_claim": True}}):
            write_json(path, {**receipt, **change})
            event["worker_result"]["sha256"] = binding(self.root, path)["sha256"]
            with self.subTest(change=change), self.scope(event), self.assertRaises(ValueError):
                presence._completed_result(self.root, context, event)

    def test_summary_and_receipt_bounds_reject_before_unbounded_body_read(self):
        context, _, path, event, _ = self.fixture("x" * (65536 + 1))
        with self.scope(event), self.assertRaisesRegex(ValueError, "bounded receipted"):
            presence._completed_result(self.root, context, event)
        path.write_bytes(b"x" * (monitor.WORKER_RECEIPT_LIMIT + 1))
        with self.scope(event), patch.object(Path, "open", side_effect=AssertionError("oversized body read")), \
             self.assertRaisesRegex(ValueError, "byte bound"):
            presence._completed_result(self.root, context, event)


class SupervisionIntegrationTests(TemporaryRoot):
    def test_one_actual_invented_child_has_120_seconds_owned_cleanup_and_bounded_transport(self):
        fixture = CompactHistory(self.root)
        seed = {"root": str(self.root), "output": str(fixture.output), "outputs": presence.OUTPUTS,
                "unit_key": presence.UNIT_KEY, "commit": fixture.context["commit"],
                "spec_sha256": fixture.context["spec_sha256"], "scientific_inputs": presence.SCIENTIFIC_INPUTS,
                "checks": presence.CHECKS}
        # This child creates three tiny invented files, never the scientific worker.
        program = "seed = " + repr(seed) + "\n" + '''
import hashlib, json, os, time
from pathlib import Path
gate = Path(os.environ['BALL_RETENTION_START_GATE'])
while not gate.is_file():
    time.sleep(.01)
root, output = Path(seed['root']), Path(seed['output'])
text = 'Bounded invented output-presence result; no scientific body read.'
artifacts, metadata = [], []
for name, payload in zip(seed['outputs'], (b'{}', text.encode(), b'{}')):
    path = output / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(payload)
    relative, info = path.relative_to(root).as_posix(), path.stat()
    artifacts.append({'path': relative, 'sha256': hashlib.sha256(payload).hexdigest()})
    metadata.append({'path': relative, 'size_bytes': info.st_size, 'mtime_ns': info.st_mtime_ns,
                     'device': info.st_dev, 'inode': info.st_ino})
result = {'schema_version': 'ball_crop_retention_output_presence_worker_result/v0.1',
          'stage': 'summarize', 'unit_key': seed['unit_key'], 'attempt_id': os.environ['BALL_RETENTION_ATTEMPT_ID'],
          'commit': seed['commit'], 'spec_sha256': seed['spec_sha256'], 'artifacts': artifacts,
          'artifact_metadata': metadata, 'scientific_inputs': seed['scientific_inputs'], 'checks': seed['checks'],
          'summary_payload': {'text': text, 'size_bytes': len(text.encode()), 'sha256': hashlib.sha256(text.encode()).hexdigest()}}
with Path(os.environ['BALL_RETENTION_RESULT_PATH']).open('x', encoding='utf-8') as stream:
    json.dump(result, stream)
'''
        baseline = resources.BudgetJournal
        with fixture.scope():
            event = presence._run_bounded_supervised(fixture.context, [sys.executable, "-B", "-c", program])
            journal = presence.verify_history(self.root, fixture.context, "completed")
            result = presence._completed_result(self.root, fixture.context, event)
            with self.assertRaises(ValueError):
                presence.PresenceJournal(fixture.output, fixture.context["limits"]).reserve(presence.UNIT_KEY, False)
        self.assertIs(resources.BudgetJournal, baseline)
        start = journal._attempts()[event["attempt_id"]]["start"]
        self.assertIs(start["selection_unit"], False)
        self.assertEqual(start["reserved_seconds"], 120)
        self.assertEqual(event["time_budget_seconds"], 120)
        self.assertEqual(start["limits_sha256"], resources._digest(fixture.context["limits"]))
        self.assertTrue(event["success"])
        self.assertTrue(event["owned_cleanup_verified"])
        self.assertGreaterEqual(event["completed_scans"], 2)
        self.assertLessEqual(event["maximum_monitor_interval_seconds"], 1)
        self.assertLess(journal.consumed(), fixture.used + 120)
        self.assertEqual(result["summary"], "Bounded invented output-presence result; no scientific body read.")
        self.assertEqual(result["successful_workers"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
