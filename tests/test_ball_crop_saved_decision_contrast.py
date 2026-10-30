"""Artificial-only runner boundaries for the saved eight-frame contrast.

All scientific-looking paths belong to temporary fixtures. No production data,
annotation, review image, journal or saved report is opened by these tests.
"""
from __future__ import annotations

import copy
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.ball_tracking import crop_saved_decision_contrast as contrast
from src.ball_tracking import crop_candidate_identity_review as identity
from src.ball_tracking import crop_retention_error_breakdown as original
from src.ball_tracking import crop_retention_error_breakdown_recovery as recovery
from src.ball_tracking import crop_retention_monitor as monitor
from src.ball_tracking import crop_retention_resources as resources
from test_ball_crop_retention_error_breakdown import binding, limits, write_json
import test_ball_crop_candidate_identity_review as identity_fixtures
import test_ball_crop_retention_output_presence as presence_fixtures


def completion_event():
    value = presence_fixtures.completion_event(seconds=43.938, reservation=120)
    value["worker_result"] = {"path": "attempts/" + contrast.PREDECESSOR_ATTEMPT + ".result.json",
                              "sha256": contrast.PREDECESSOR_RESULT_SHA}
    value["monitor_samples"] = 49
    return value


def invented_prefix():
    events = identity_fixtures.invented_prefix()
    aid = contrast.PREDECESSOR_ATTEMPT

    def append(kind, **details):
        events.append({"kind": kind, "attempt_id": aid,
                       "sha256": f"{len(events) + 1:064x}", **details})

    append("started", unit_key=identity.UNIT_KEY, selection_unit=False, reserved_seconds=120)
    for index in range(49):
        append("sample", elapsed_seconds=index / 2)
    append("finished", **completion_event())
    events[-1]["sha256"] = contrast.PREFIX_TIP
    return events


def invented_manifest():
    return {"schema_version": "ball_crop_saved_decision_contrast_experiment/v0.1",
            "study_id": contrast.ID, "output_root": contrast.OUTPUT_ROOT,
            "output_dir": contrast.OUTPUT_DIR, "permitted_stages": ["summarize"],
            "unit_key": contrast.UNIT_KEY, "maximum_unit_seconds": 120,
            "maximum_summary_bytes": 65536, "maximum_contrast_bytes": 131072,
            "maximum_provenance_bytes": 131072, "scientific_inputs": copy.deepcopy(contrast.SCIENTIFIC_INPUTS),
            **{key: {"path": path, "sha256": "f" * 64} for key, path in contrast.AUTHORITY_PATHS.items()},
            "proposal": {"path": contrast.PROPOSAL_PATH, "sha256": contrast.PROPOSAL_SHA},
            "scope": {"path": contrast.SCOPE_PATH, "sha256": contrast.SCOPE_SHA},
            "frozen_history": {"path": contrast.FROZEN_HISTORY_PATH, "sha256": contrast.FROZEN_HISTORY_SHA},
            "implementation_validation": {"path": contrast.CERTIFICATE_PATH, "sha256": "e" * 64},
            "post_commit_checkpoint": contrast.POST_COMMIT_PATH,
            "selected_method": None, "selected_operating_point": None, "quality_gate": None}


class TemporaryRoot(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="sdc_")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()


class ContrastBudgetTests(TemporaryRoot):
    def journal(self, events=None, approved=None):
        value = contrast.ContrastJournal.__new__(contrast.ContrastJournal)
        value.root, value.folder = self.root, self.root / "resource_events"
        value.events = invented_prefix() if events is None else events
        value.limits = limits() if approved is None else approved
        return value

    def test_exact_prefix_preserves_61_closed_attempts_57_successes_and_four_failures(self):
        journal = self.journal()
        self.assertEqual(len(journal.events), 3172)
        starts, ends = contrast._closed_prefix(journal)
        self.assertEqual(len(starts), 61)
        self.assertEqual(sum(event["success"] is True for event in ends.values()), 57)
        self.assertEqual({aid for aid, event in ends.items() if not event["success"]}, recovery.KNOWN_FAILURES)
        self.assertAlmostEqual(journal.consumed(), contrast.USED_SECONDS, places=7)
        self.assertAlmostEqual(journal.limits["maximum_cumulative_seconds"] - journal.consumed(),
                               10993.273000000017, places=7)

    def test_one_120_second_reservation_keeps_prefix_and_seals_exact_new_role(self):
        journal = self.journal()
        before = copy.deepcopy(journal.events)
        aid, seconds = journal.reserve(contrast.UNIT_KEY, False)
        self.assertEqual(seconds, 120)
        self.assertEqual(journal.events[:-1], before)
        self.assertEqual(journal.events[-1]["unit_key"], contrast.UNIT_KEY)
        self.assertIs(journal.events[-1]["selection_unit"], False)
        seal = json.loads((self.root / "attempts" / (aid + ".reservation.json")).read_text())
        self.assertEqual(seal, {"event_sha256": journal.events[-1]["sha256"]})

    def test_cumulative_balance_limits_reservation_and_exhaustion_blocks_it(self):
        approved = limits()
        approved["maximum_cumulative_seconds"] = contrast.USED_SECONDS + 2
        _, seconds = self.journal(approved=approved).reserve(contrast.UNIT_KEY, False)
        self.assertAlmostEqual(seconds, 2, places=7)
        approved["maximum_cumulative_seconds"] = contrast.USED_SECONDS
        with self.assertRaises((ValueError, resources.ResourceLimitError)):
            self.journal(approved=approved).reserve(contrast.UNIT_KEY, False)

    def test_consumed_attempt_unknown_role_and_selection_cannot_be_reserved(self):
        for key, selection in ((original.UNIT_KEY, False), (recovery.UNIT_KEY, False),
                               (identity.UNIT_KEY, False), (contrast.UNIT_KEY, True), ("unknown", False)):
            with self.subTest(key=key, selection=selection), self.assertRaises(ValueError):
                self.journal().reserve(key, selection)
        journal = self.journal()
        journal.reserve(contrast.UNIT_KEY, False)
        with self.assertRaises(ValueError):
            journal.reserve(contrast.UNIT_KEY, False)

    def test_changed_prefix_tip_prior_result_budget_or_unknown_suffix_is_rejected(self):
        changes = (lambda e: e.pop(0), lambda e: e[-1].__setitem__("sha256", "0" * 64),
                   lambda e: e[-1].__setitem__("success", False),
                   lambda e: e[-1].__setitem__("elapsed_seconds", 1),
                   lambda e: e[-1]["worker_result"].__setitem__("sha256", "0" * 64),
                   lambda e: e[-1].__setitem__("owned_cleanup_verified", False),
                   lambda e: e[-51].__setitem__("unit_key", "unapproved"),
                   lambda e: e.append({"kind": "started", "attempt_id": "e" * 32, "unit_key": "unknown",
                                       "selection_unit": False, "reserved_seconds": 1., "sha256": "f" * 64}))
        for change in changes:
            events = invented_prefix()
            change(events)
            with self.subTest(change=change), self.assertRaises((ValueError, resources.ResourceLimitError)):
                self.journal(events).reserve(contrast.UNIT_KEY, False)


class ReleaseGateTests(TemporaryRoot):
    def test_manifest_cannot_expand_inputs_units_stages_outputs_or_choose_method(self):
        manifest = invented_manifest()
        contrast._validate_manifest(manifest)
        for change in ({"unit_key": identity.UNIT_KEY}, {"maximum_unit_seconds": 121},
                       {"maximum_summary_bytes": 65537}, {"maximum_contrast_bytes": 131073},
                       {"maximum_provenance_bytes": 131073},
                       {"output_dir": identity.OUTPUT_DIR}, {"permitted_stages": ["rerank"]},
                       {"selected_method": "invented-choice"}, {"scientific_inputs": {}}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                contrast._validate_manifest({**manifest, **change})

    def test_dirty_tree_stops_before_manifest_history_or_scientific_access(self):
        failure = ValueError("invented dirty tree")
        with patch.object(original.original, "_clean_checkpoint", side_effect=failure), \
             patch.object(contrast, "read_json", side_effect=AssertionError("manifest read")), \
             patch.object(identity, "_metadata", side_effect=AssertionError("historical read")), \
             patch.object(contrast, "_load_scientific_inputs", side_effect=AssertionError("scientific read")):
            with self.assertRaises(ValueError) as caught:
                contrast._metadata(self.root, self.root / contrast.MANIFEST_PATH)
        self.assertIs(caught.exception, failure)

    def test_missing_release_checkpoint_stops_before_authority_reads_or_dispatch(self):
        path = self.root / contrast.MANIFEST_PATH
        write_json(path, {})
        with patch.object(original.original, "_clean_checkpoint", return_value="b" * 40), \
             patch.object(contrast, "_validate_manifest"), \
             patch.object(contrast, "verify_binding", side_effect=AssertionError("authority read")), \
             patch.object(contrast, "_run_bounded_supervised", side_effect=AssertionError("dispatch")):
            for dry in (False, True):
                with self.subTest(dry_run=dry), self.assertRaisesRegex(ValueError, "checkpoint is absent"):
                    contrast.run_saved_decision_contrast(self.root, path, dry_run=dry)

    def test_parent_reader_rejects_both_inputs_new_outputs_and_undeclared_pointers(self):
        forbidden = [row["path"] for row in contrast.SCIENTIFIC_INPUTS.values()]
        forbidden += [contrast.OUTPUT_ROOT + "/" + name for name in contrast.OUTPUTS]
        forbidden += ["data/outputs/unapproved_scientific_manifest.json"]
        with patch.object(Path, "open", side_effect=AssertionError("scientific body opened")):
            for name in forbidden:
                with self.subTest(path=name), self.assertRaises(ValueError):
                    contrast._read_bound(self.root, {"path": name, "sha256": "a" * 64})

    def test_checkpoint_requires_exact_commit_bindings_and_all_release_conditions(self):
        manifest, commit = invented_manifest(), "b" * 40
        manifest_path = self.root / contrast.MANIFEST_PATH
        write_json(manifest_path, manifest)
        checkpoint = {"schema_version": "ball_crop_saved_decision_contrast_execution_checkpoint/v0.1",
            "head": commit, "branch": "codex/ball-detector-baseline", "manifest": binding(self.root, manifest_path),
            "implementation_validation": manifest["implementation_validation"],
            "manifest_spec_sha256": contrast._spec_sha256(manifest), "preserved_prefix_tip_sha256": contrast.PREFIX_TIP,
            **{key: True for key in ("execution_authorized", "clean", "index_empty", "validated_sources_unchanged")}}
        path = self.root / contrast.POST_COMMIT_PATH
        write_json(path, checkpoint)
        with patch.object(contrast.subprocess, "run", return_value=SimpleNamespace(returncode=0)):
            self.assertEqual(contrast._post_commit_checkpoint(self.root, manifest, commit), checkpoint)
            for key, value in (("head", contrast.BASE_COMMIT), ("branch", "main"),
                               ("manifest_spec_sha256", "0" * 64), ("preserved_prefix_tip_sha256", "0" * 64),
                               ("execution_authorized", False), ("clean", False),
                               ("index_empty", False), ("validated_sources_unchanged", False)):
                write_json(path, {**checkpoint, key: value})
                with self.subTest(key=key), self.assertRaises(ValueError):
                    contrast._post_commit_checkpoint(self.root, manifest, commit)


class CertificateTests(TemporaryRoot):
    def fixture(self):
        manifest = invented_manifest()
        paths = [self.root / name for name in ("src/invented.py", "tests/test_invented.py", "requirements.txt")]
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# invented validation source\n", encoding="utf-8")
        evidence = self.root / contrast.IMPLEMENTATION_DIR / "invented_validation.json"
        write_json(evidence, {"invented": True})
        certificate = {"schema_version": "ball_crop_saved_decision_contrast_implementation_validation/v0.1",
            "manifest_spec_sha256": contrast._spec_sha256(manifest),
            "authority_sha256": {key: manifest[key]["sha256"] for key in contrast.AUTHORITY_FIELDS},
            **{key: True for key in ("focused_tests_passed", "full_suite_passed", "independent_static_review_passed",
                                    "integrity_tests_passed", "monitor_design_check_passed")},
            "source_bindings": [binding(self.root, path) for path in paths],
            "evidence_bindings": [binding(self.root, evidence)]}
        return manifest, certificate, paths

    def check(self, manifest, certificate):
        path = self.root / contrast.CERTIFICATE_PATH
        write_json(path, certificate)
        manifest = {**manifest, "implementation_validation": binding(self.root, path)}
        with patch.object(original.original, "_git", return_value="tracked"):
            return contrast._validate_implementation(self.root, manifest)

    def test_certificate_requires_complete_unchanged_source_inventory(self):
        manifest, certificate, paths = self.fixture()
        self.assertEqual(self.check(manifest, certificate), certificate)
        with self.assertRaisesRegex(ValueError, "complete current source inventory"):
            self.check(manifest, {**certificate, "source_bindings": certificate["source_bindings"][:1]})
        paths[1].write_text("# changed after validation\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.check(manifest, certificate)

    def test_incomplete_flags_and_scientific_validation_evidence_cannot_be_adopted(self):
        manifest, certificate, _ = self.fixture()
        for field in ("focused_tests_passed", "full_suite_passed", "independent_static_review_passed",
                      "integrity_tests_passed", "monitor_design_check_passed"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check(manifest, {**certificate, field: False})
        forbidden = next(iter(contrast.SCIENTIFIC_INPUTS.values()))
        wrong = {**certificate, "evidence_bindings": [{key: forbidden[key] for key in ("path", "sha256")}]}
        real_verify = contrast.verify_binding

        def guard(root, row):
            self.assertNotEqual(row["path"], forbidden["path"])
            return real_verify(root, row)

        with patch.object(contrast, "verify_binding", side_effect=guard), self.assertRaisesRegex(ValueError, "outside"):
            self.check(manifest, wrong)


class TinyInputs:
    def __init__(self, root, payloads=None):
        self.root, self.inputs, self.metadata, self.paths = root, {}, [], []
        self.payloads = payloads or {
            "representative_pool": {"invented": True, "inert_scientific_pointer": "../do-not-follow.json"},
            "tt_observations_wrapper": {"invented": True, "input_crop_file": "../do-not-follow.json"}}
        for role, payload in self.payloads.items():
            path = root / "data/outputs/invented_contrast_inputs" / (role + ".json")
            write_json(path, payload)
            self.inputs[role] = {**binding(root, path), "size_bytes": path.stat().st_size}
            self.metadata.append({"path": path.relative_to(root).as_posix(), **original._stat_metadata(path)})
            self.paths.append(path)
        self.context = {"current_attempt_id": "d" * 32, "manifest": {"scientific_inputs": self.inputs},
                        "history": {"scientific_input_metadata": self.metadata}}

    def scope(self):
        stack = ExitStack()
        stack.enter_context(patch.object(contrast, "SCIENTIFIC_INPUTS", self.inputs))
        stack.enter_context(patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": "d" * 32,
                                                   "BALL_RETENTION_PARENT_PID": str(os.getpid())}))
        return stack


class CompactHistory:
    """61 sealed invented attempts with tiny administrative bodies."""
    def __init__(self, root):
        self.old = identity_fixtures.CompactHistory(root)
        self.root, self.output, self.journal = root, self.old.output, self.old.journal
        aid = contrast.PREDECESSOR_ATTEMPT
        self.result_path = self.output / "attempts" / (aid + ".result.json")
        write_json(self.result_path, {"invented": True, "attempt_id": aid,
                                    "inert_scientific_pointer": "/must/not/open"})
        self.result_sha = binding(root, self.result_path)["sha256"]
        with patch.object(resources, "_write_new", side_effect=write_json):
            start = self.journal.append("started", attempt_id=aid, unit_key=identity.UNIT_KEY,
                                       selection_unit=False, reserved_seconds=120)
            write_json(self.output / "attempts" / (aid + ".reservation.json"), {"event_sha256": start["sha256"]})
            completed = completion_event()
            completed["worker_result"]["sha256"] = self.result_sha
            end = self.journal.append("finished", attempt_id=aid, **completed)
        self.count, self.tip, self.used = len(self.journal.events), end["sha256"], self.journal.consumed()
        self.scientific = TinyInputs(root)
        human_paths = [root / contrast.HUMAN_ROOT / f"human_review_{index:04d}.json" for index in range(1, 9)]
        human_paths.append(root / contrast.HUMAN_ROOT / "human_review_completion_v0_1.json")
        for path in human_paths:
            write_json(path, {"invented_administrative_record": path.name})
        history = {"raw_event_bindings": [binding(root, path) for path in sorted(self.journal.folder.glob("*.json"))],
                   "administrative_attempt_bindings": [binding(root, path) for path in sorted((self.output / "attempts").glob("*.json"))],
                   "prior_candidate_identity_completion": end,
                   "human_review_bindings": [binding(root, path) for path in human_paths],
                   "scientific_input_metadata": self.scientific.metadata,
                   "external_preserved_files": self.old.images.metadata,
                   "preserved_files": [{"path": path.relative_to(root).as_posix(), **original._stat_metadata(path)}
                                       for path in self.output.rglob("*") if path.is_file()],
                   "preserved_directories": [path.relative_to(root).as_posix() for path in self.output.rglob("*") if path.is_dir()],
                   "preserved_absent_paths": [contrast.OUTPUT_ROOT + "/" + contrast.OUTPUT_DIR,
                                              contrast.OUTPUT_ROOT + "/supervisor.lock"],
                   "protection": self.old.context["history"]["protection"]}
        self.context = {"root": root, "output_root": self.output, "limits": self.old.context["limits"],
                        "history": history, "policy": monitor.monitoring_policy(limits(), .25),
                        "commit": "b" * 40, "spec_sha256": "a" * 64}

    def scope(self):
        stack = self.old.scope()
        stack.enter_context(patch.object(contrast, "SCIENTIFIC_INPUTS", self.scientific.inputs))
        for key, value in (("PREFIX_COUNT", self.count), ("PREFIX_TIP", self.tip),
                           ("USED_SECONDS", self.used), ("PREDECESSOR_RESULT_SHA", self.result_sha)):
            stack.enter_context(patch.object(contrast, key, value))
        return stack

    def start(self):
        with self.scope():
            journal = contrast.ContrastJournal(self.output, self.context["limits"])
            aid, _ = journal.reserve(contrast.UNIT_KEY, False)
        self.journal = journal
        policy = self.context["policy"]
        write_json(self.output / "attempts" / (aid + ".monitoring_policy.json"),
                   {"policy": policy, "sha256": resources._digest(policy)})
        return aid


class HistoryIntegrationTests(TemporaryRoot):
    def test_closed_history_reads_administrative_records_only_and_refuses_failed_result_adoption(self):
        fixture = CompactHistory(self.root)
        real_verify = contrast.verify_binding

        def guard(root, row):
            self.assertTrue("/resource_events/" in row["path"] or "/attempts/" in row["path"]
                            or row["path"].startswith(contrast.HUMAN_ROOT + "/"))
            return real_verify(root, row)

        with fixture.scope(), patch.object(contrast, "verify_binding", side_effect=guard):
            journal = contrast.verify_history(self.root, fixture.context, "before")
        self.assertEqual(len(journal._attempts()), 61)
        write_json(fixture.output / "attempts" / (recovery.FAILED_ATTEMPT + ".result.json"), {"unreceipted": True})
        with fixture.scope(), self.assertRaises(ValueError):
            contrast.verify_history(self.root, fixture.context, "before")

    def test_worker_requires_sole_owned_attempt_and_exact_responsive_monitor_policy(self):
        fixture = CompactHistory(self.root)
        aid = fixture.start()
        with fixture.scope(), patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": aid}):
            contrast.verify_history(self.root, fixture.context, "worker")
            for phase in ("before", "completed"):
                with self.subTest(phase=phase), self.assertRaises(ValueError):
                    contrast.verify_history(self.root, fixture.context, phase)
        with fixture.scope(), patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": "a" * 32}), self.assertRaises(ValueError):
            contrast.verify_history(self.root, fixture.context, "worker")
        write_json(fixture.output / "attempts" / (aid + ".monitoring_policy.json"),
                   {"policy": fixture.context["policy"], "sha256": "0" * 64})
        with fixture.scope(), patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": aid}), self.assertRaises(ValueError):
            contrast.verify_history(self.root, fixture.context, "worker")

    def test_preservation_is_metadata_only_and_refuses_unreceipted_file_or_scientific_drift(self):
        fixture = CompactHistory(self.root)
        with fixture.scope(), patch.object(Path, "open", side_effect=AssertionError("preserved body opened")):
            contrast._preserved_metadata(self.root, fixture.context)
        extra = fixture.output / "unreceipted.json"
        extra.write_bytes(b"preserve unknown evidence")
        with fixture.scope(), self.assertRaisesRegex(ValueError, "Unexpected evidence file"):
            contrast._preserved_metadata(self.root, fixture.context)
        self.assertEqual(extra.read_bytes(), b"preserve unknown evidence")
        extra.unlink()  # This fixture owns its complete fabricated temporary root.
        fixture.scientific.paths[0].write_bytes(b"changed invented scientific input size")
        with fixture.scope(), self.assertRaisesRegex(ValueError, "metadata changed"):
            contrast._preserved_metadata(self.root, fixture.context)


class ScientificInputTests(TemporaryRoot):
    def test_exact_two_bound_json_bodies_are_read_without_following_embedded_pointers(self):
        fixture = TinyInputs(self.root)
        opened, actual_open = [], Path.open

        def guard(path, *args, **kwargs):
            self.assertIn(path, fixture.paths)
            self.assertEqual(args[0] if args else kwargs.get("mode", "r"), "rb")
            opened.append(path)
            return actual_open(path, *args, **kwargs)

        with fixture.scope(), patch.object(Path, "open", guard):
            result = contrast._load_scientific_inputs(self.root, fixture.context)
        self.assertEqual(result, fixture.payloads)
        self.assertEqual(opened, fixture.paths)

    def test_parent_without_worker_ownership_cannot_open_either_input(self):
        fixture = TinyInputs(self.root)
        with patch.object(contrast, "SCIENTIFIC_INPUTS", fixture.inputs), patch.dict(os.environ, {}, clear=True), \
             patch.object(Path, "open", side_effect=AssertionError("parent scientific read")), self.assertRaises(ValueError):
            contrast._load_scientific_inputs(self.root, fixture.context)

    def test_binding_mismatch_stops_before_reading_second_input(self):
        fixture = TinyInputs(self.root)
        fixture.inputs["representative_pool"]["sha256"] = "0" * 64
        opened, actual_open = [], Path.open

        def guard(path, *args, **kwargs):
            opened.append(path)
            return actual_open(path, *args, **kwargs)

        with fixture.scope(), patch.object(Path, "open", guard), self.assertRaises(ValueError):
            contrast._load_scientific_inputs(self.root, fixture.context)
        self.assertEqual(opened, [fixture.paths[0]])

    def test_metadata_drift_symlink_and_escape_paths_stop_before_body_access(self):
        fixture = TinyInputs(self.root)
        fixture.metadata[0]["mtime_ns"] += 1
        with fixture.scope(), patch.object(Path, "open", side_effect=AssertionError("preflight body read")), self.assertRaises(ValueError):
            contrast._load_scientific_inputs(self.root, fixture.context)
        fixture.metadata[0]["mtime_ns"] -= 1
        real_symlink = Path.is_symlink

        def symlink(path):
            return path == fixture.paths[0] or real_symlink(path)

        with fixture.scope(), patch.object(Path, "is_symlink", symlink), \
             patch.object(Path, "open", side_effect=AssertionError("symlink body read")), self.assertRaises(ValueError):
            contrast._load_scientific_inputs(self.root, fixture.context)
        fixture.inputs["representative_pool"]["path"] = "../forbidden.json"
        fixture.metadata[0]["path"] = "../forbidden.json"
        with fixture.scope(), patch.object(Path, "open", side_effect=AssertionError("escaped body read")), self.assertRaises(ValueError):
            contrast._load_scientific_inputs(self.root, fixture.context)


class TinyWorker(TinyInputs):
    def __init__(self, root):
        from test_ball_crop_saved_decision_contrast_summary import make_inputs

        pool, wrapper, ledger, scope = make_inputs()
        super().__init__(root, {"representative_pool": pool, "tt_observations_wrapper": wrapper})
        scope["scientific_inputs"] = self.inputs
        for row in scope["frozen_report_references"].values():
            row["source"].update({key: self.inputs["representative_pool"][key] for key in ("path", "sha256")})
        scope["frozen_report_references"]["history_edge_tight_cost_tight"]["observations_file"] = {
            key: self.inputs["tt_observations_wrapper"][key] for key in ("path", "sha256")}
        scope["frozen_control_reference"]["file"] = {
            key: self.inputs["tt_observations_wrapper"][key] for key in ("path", "sha256")}
        self.aid, self.output = "d" * 32, root / contrast.OUTPUT_ROOT
        (self.output / "audit").mkdir(parents=True)
        (self.output / "attempts").mkdir()
        self.result_path = self.output / "attempts" / (self.aid + ".result.json")
        write_json(root / contrast.POST_COMMIT_PATH, {"invented_release_checkpoint": True})
        manifest = invented_manifest()
        manifest["scientific_inputs"] = self.inputs
        self.prior_images = identity_fixtures.TinyImages(root)
        self.context = {"root": root, "manifest_path": root / contrast.MANIFEST_PATH, "manifest": manifest,
            "output_root": self.output, "current_attempt_id": self.aid,
            "commit": "b" * 40, "spec_sha256": "a" * 64, "scope": scope, "human_ledger": ledger,
            "limits": limits(), "history": {"scientific_input_metadata": self.metadata,
                "external_preserved_files": self.prior_images.metadata, "preserved_files": [],
                "preserved_directories": [contrast.OUTPUT_ROOT + "/audit", contrast.OUTPUT_ROOT + "/attempts"],
                "preserved_absent_paths": [contrast.OUTPUT_ROOT + "/" + contrast.OUTPUT_DIR,
                                           contrast.OUTPUT_ROOT + "/supervisor.lock"],
                "protection": {"sealed_holdouts_metadata_only": original.HOLDOUTS,
                    "preserved_absent_paths": ["data/outputs/ball_tracking/detections/invented_embargo_" + str(i) for i in range(9)]}},
            "certificate": {"source_bindings": []}, "policy": monitor.monitoring_policy(limits(), .25)}
        self.journal = SimpleNamespace(_attempts=lambda: {self.aid: {"start": {"sha256": "c" * 64}}})

    def scope(self):
        stack = super().scope()
        stack.enter_context(patch.object(resources, "wait_for_supervisor"))
        stack.enter_context(patch.object(contrast, "_metadata", return_value=self.context))
        stack.enter_context(patch.object(contrast, "verify_history", return_value=self.journal))
        self.preservation = stack.enter_context(patch.object(contrast, "_preserved_metadata"))
        stack.enter_context(patch.dict(os.environ, {"BALL_RETENTION_RESULT_PATH": str(self.result_path)}))
        stack.enter_context(patch.object(identity, "_worker", side_effect=AssertionError("consumed scientific worker")))
        stack.enter_context(patch.object(identity, "_verify_image_bytes", side_effect=AssertionError("image access")))
        return stack


class WorkerTests(TemporaryRoot):
    def test_worker_reads_only_bound_pair_and_creates_three_outputs_with_bounded_receipt(self):
        fixture = TinyWorker(self.root)
        opened, actual_open = [], Path.open
        expected = set(fixture.paths) | {fixture.result_path, self.root / contrast.POST_COMMIT_PATH,
                                        *[fixture.output / name for name in contrast.OUTPUTS]}

        def guard(path, *args, **kwargs):
            self.assertIn(path, expected)
            opened.append(path)
            return actual_open(path, *args, **kwargs)

        with fixture.scope(), patch.object(Path, "open", guard):
            result = contrast._worker(self.root, fixture.context["manifest_path"])
        self.assertEqual(result, {"worker_result_written": True, "attempt_id": fixture.aid, "completion_pending": True})
        self.assertEqual([path for path in opened if path in fixture.paths], fixture.paths)
        destination = fixture.output / contrast.OUTPUT_DIR
        self.assertEqual({path.name for path in destination.iterdir()}, set(contrast.OUTPUT_NAMES))
        receipt = json.loads(fixture.result_path.read_text(encoding="utf-8"))
        self.assertEqual(len(receipt["contrast"]["rows"]), 8)
        self.assertEqual(receipt["contrast"], json.loads((destination / "contrast.json").read_text(encoding="utf-8")))
        self.assertEqual(receipt["summary_payload"]["text"], (destination / "summary.md").read_text(encoding="utf-8"))
        self.assertLessEqual(fixture.result_path.stat().st_size, monitor.WORKER_RECEIPT_LIMIT)

    def test_wrong_receipt_location_and_existing_output_never_overwrite_evidence(self):
        fixture = TinyWorker(self.root)
        with fixture.scope(), patch.dict(os.environ, {"BALL_RETENTION_RESULT_PATH": str(self.root / "wrong.json")}), \
             patch.object(contrast, "_load_scientific_inputs", side_effect=AssertionError("premature scientific access")), \
             self.assertRaises(ValueError):
            contrast._worker(self.root, fixture.context["manifest_path"])
        destination = fixture.output / contrast.OUTPUT_DIR
        destination.mkdir()
        marker = destination / "contrast.json"
        marker.write_bytes(b"preserve previous partial")
        with fixture.scope(), self.assertRaises(ValueError):
            contrast._worker(self.root, fixture.context["manifest_path"])
        self.assertEqual(marker.read_bytes(), b"preserve previous partial")
        self.assertFalse(fixture.result_path.exists())

    def test_input_or_formatter_failure_never_publishes_success_receipt_or_retries(self):
        for failure in ("hash", "formatter"):
            with self.subTest(failure=failure):
                fixture = TinyWorker(self.root / failure)
                with fixture.scope(), ExitStack() as stack:
                    if failure == "hash":
                        fixture.inputs["representative_pool"]["sha256"] = "0" * 64
                        build = stack.enter_context(patch.object(contrast.formatter, "build_contrast",
                            side_effect=AssertionError("formatter after unverified input")))
                    else:
                        build = stack.enter_context(patch.object(contrast.formatter, "build_contrast",
                            side_effect=ValueError("invented incompatible endpoint")))
                    with self.assertRaises(ValueError):
                        contrast._worker(fixture.root, fixture.context["manifest_path"])
                self.assertEqual(build.call_count, 0 if failure == "hash" else 1)
                self.assertFalse(fixture.result_path.exists())

    def test_size_and_late_publication_failures_preserve_partial_evidence_without_adoption(self):
        actual_write = original._write_new
        for failure in ("summary_bound", "preservation", "publication"):
            with self.subTest(failure=failure):
                fixture = TinyWorker(self.root / failure)

                def write(path, payload):
                    if path == fixture.result_path:
                        raise OSError("invented receipt publication failure")
                    return actual_write(path, payload)

                with fixture.scope(), ExitStack() as stack:
                    if failure == "summary_bound":
                        stack.enter_context(patch.object(contrast.formatter, "format_summary", return_value="x" * 65537))
                    elif failure == "preservation":
                        fixture.preservation.side_effect = [None, ValueError("invented final metadata drift")]
                    else:
                        stack.enter_context(patch.object(original, "_write_new", side_effect=write))
                    with self.assertRaises((ValueError, OSError)):
                        contrast._worker(fixture.root, fixture.context["manifest_path"])
                self.assertFalse(fixture.result_path.exists())
                destination = fixture.output / contrast.OUTPUT_DIR
                if failure == "summary_bound":
                    self.assertFalse((destination / "summary.md").exists())
                else:
                    self.assertEqual({path.name for path in destination.iterdir()}, set(contrast.OUTPUT_NAMES))


class ReceiptTests(TemporaryRoot):
    def fixture(self):
        fixture = TinyWorker(self.root)
        with fixture.scope():
            contrast._worker(self.root, fixture.context["manifest_path"])
        receipt = json.loads(fixture.result_path.read_text(encoding="utf-8"))
        event = {"attempt_id": fixture.aid, "sha256": "c" * 64,
                 "worker_result": {"path": "attempts/" + fixture.aid + ".result.json",
                                   "sha256": binding(self.root, fixture.result_path)["sha256"]}}
        return fixture, receipt, event

    def scope(self, fixture, event):
        stack = ExitStack()
        stack.enter_context(patch.object(contrast, "SCIENTIFIC_INPUTS", fixture.inputs))
        stack.enter_context(patch.object(contrast, "verify_history", return_value=SimpleNamespace(events=[event])))
        return stack

    def test_parent_opens_only_receipt_and_returns_eight_verified_rows_with_human_nulls_preserved(self):
        fixture, receipt, event = self.fixture()
        human_before = copy.deepcopy(fixture.context["human_ledger"])
        opened, actual_open = [], Path.open

        def guard(path, *args, **kwargs):
            self.assertEqual(path, fixture.result_path)
            opened.append(path)
            return actual_open(path, *args, **kwargs)

        with self.scope(fixture, event), patch.object(Path, "open", guard):
            result = contrast._completed_result(self.root, fixture.context, event)
        self.assertEqual(opened, [fixture.result_path])
        self.assertEqual(result["contrast"], receipt["contrast"])
        self.assertEqual([row["human_review"]["emitted_candidate_index"] for row in result["contrast"]["rows"]],
                         [0] + [None] * 7)
        self.assertEqual(fixture.context["human_ledger"], human_before)
        self.assertEqual(result["new_model_calls"], 0)
        self.assertFalse(result["scoring_executed"])
        self.assertFalse(result["media_decoded"])

    def test_forged_scope_summary_or_artifact_binding_cannot_be_returned(self):
        fixture, receipt, event = self.fixture()
        changes = []
        wrong = copy.deepcopy(receipt)
        wrong["scientific_inputs"]["representative_pool"]["sha256"] = "0" * 64
        changes.append(wrong)
        wrong = copy.deepcopy(receipt)
        wrong["summary_payload"]["text"] = "Invented changed conclusions."
        changes.append(wrong)
        wrong = copy.deepcopy(receipt)
        wrong["artifacts"][0]["sha256"] = "0" * 64
        changes.append(wrong)
        wrong = copy.deepcopy(receipt)
        wrong["contrast"]["rows"][1]["human_review"]["emitted_candidate_index"] = 0
        changes.append(wrong)
        for wrong in changes:
            write_json(fixture.result_path, wrong)
            event["worker_result"]["sha256"] = binding(self.root, fixture.result_path)["sha256"]
            with self.subTest(wrong=wrong), self.scope(fixture, event), self.assertRaises(ValueError):
                contrast._completed_result(self.root, fixture.context, event)

    def test_oversized_receipt_input_drift_and_output_drift_reject_without_scientific_reads(self):
        fixture, receipt, event = self.fixture()
        fixture.result_path.write_bytes(b"x" * (monitor.WORKER_RECEIPT_LIMIT + 1))
        with self.scope(fixture, event), patch.object(Path, "open", side_effect=AssertionError("oversized receipt read")), \
             self.assertRaisesRegex(ValueError, "byte bound"):
            contrast._completed_result(self.root, fixture.context, event)
        write_json(fixture.result_path, receipt)
        event["worker_result"]["sha256"] = binding(self.root, fixture.result_path)["sha256"]
        (fixture.output / contrast.OUTPUT_DIR / "summary.md").write_bytes(b"changed scientific output metadata")
        actual_open = Path.open

        def only_receipt(path, *args, **kwargs):
            self.assertEqual(path, fixture.result_path)
            return actual_open(path, *args, **kwargs)

        with self.scope(fixture, event), patch.object(Path, "open", only_receipt), self.assertRaisesRegex(ValueError, "metadata changed"):
            contrast._completed_result(self.root, fixture.context, event)
        fixture.paths[0].write_bytes(b"changed scientific input metadata")
        with self.scope(fixture, event), patch.object(Path, "open", side_effect=AssertionError("changed scientific body read")), \
             self.assertRaisesRegex(ValueError, "metadata changed"):
            contrast._completed_result(self.root, fixture.context, event)


class DispatchTests(TemporaryRoot):
    def test_exact_role_reuses_responsive_monitor_without_global_journal_override(self):
        context = {"root": self.root, "output_root": self.root / "invented_output", "limits": limits()}
        command = ["invented-python", "-B", "invented-worker"]
        completion = {"success": True, "attempt_id": "a" * 32}
        baseline = resources.BudgetJournal
        with patch.object(monitor, "run_supervised", return_value=completion) as launch, \
             patch.object(resources, "run_supervised", side_effect=AssertionError("legacy supervisor")):
            self.assertIs(contrast._run_bounded_supervised(context, command), completion)
        launch.assert_called_once_with(context["output_root"], contrast.UNIT_KEY, command, context["limits"],
            cwd=self.root, selection_unit=False, poll_seconds=.25, require_result=True,
            journal_factory=contrast.ContrastJournal)
        self.assertIs(resources.BudgetJournal, baseline)

    def test_monitor_failure_has_one_dispatch_no_retry_and_no_parent_publication(self):
        path = self.root / contrast.MANIFEST_PATH
        context = {"root": self.root, "manifest_path": path, "commit": "b" * 40, "spec_sha256": "a" * 64}
        failure = resources.ResourceLimitError("invented monitor failure")
        with patch.object(contrast, "_metadata", return_value=context) as metadata, \
             patch.object(contrast, "verify_history"), patch.object(contrast, "_preserved_metadata"), \
             patch.object(contrast, "_run_bounded_supervised", side_effect=failure) as launch, \
             patch.object(contrast, "_completed_result", side_effect=AssertionError("failed result release")):
            with self.assertRaises(resources.ResourceLimitError) as caught:
                contrast.run_saved_decision_contrast(self.root, path)
        self.assertIs(caught.exception, failure)
        metadata.assert_called_once_with(self.root, path, True)
        launch.assert_called_once_with(context, [sys.executable, "-B", "-m",
            "src.ball_tracking.crop_saved_decision_contrast", "--manifest", str(path),
            "--repository-root", str(self.root), "--worker"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
