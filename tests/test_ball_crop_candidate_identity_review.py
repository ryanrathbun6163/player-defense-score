"""Artificial-only boundaries for the sixteen-file candidate identity review.

No production image, scientific manifest, annotation, report or journal is read.
Tiny byte fixtures deliberately are not decodable PNGs; pixels are never needed.
"""
from __future__ import annotations

import builtins
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

from src.ball_tracking import crop_candidate_identity_review as identity
from src.ball_tracking import crop_retention_error_breakdown as original
from src.ball_tracking import crop_retention_error_breakdown_recovery as recovery
from src.ball_tracking import crop_retention_output_presence as presence
from src.ball_tracking import crop_retention_monitor as monitor
from src.ball_tracking import crop_retention_resources as resources
from test_ball_crop_retention_error_breakdown import binding, limits, write_json
import test_ball_crop_retention_output_presence as presence_fixtures


def completion_event():
    value = presence_fixtures.completion_event(seconds=42.734, reservation=120)
    value["worker_result"] = {"path": "attempts/" + identity.PREDECESSOR_ATTEMPT + ".result.json",
                              "sha256": identity.PREDECESSOR_RESULT_SHA}
    value["monitor_samples"] = 48
    return value


def invented_prefix():
    events = presence_fixtures.invented_prefix()
    aid = identity.PREDECESSOR_ATTEMPT

    def append(kind, **details):
        events.append({"kind": kind, "attempt_id": aid,
                       "sha256": f"{len(events) + 1:064x}", **details})

    append("started", unit_key=presence.UNIT_KEY, selection_unit=False, reserved_seconds=120)
    for index in range(48):
        append("sample", elapsed_seconds=index / 2)
    append("finished", **completion_event())
    events[-1]["sha256"] = identity.PREFIX_TIP
    return events


def invented_manifest():
    return {"schema_version": "ball_crop_candidate_identity_review_experiment/v0.1",
            "study_id": identity.ID, "output_root": identity.OUTPUT_ROOT, "output_dir": identity.OUTPUT_DIR,
            "permitted_stages": ["verify"], "unit_key": identity.UNIT_KEY, "maximum_unit_seconds": 120,
            "maximum_guide_bytes": 65536, "scientific_inputs": copy.deepcopy(identity.SCIENTIFIC_INPUTS),
            **{key: {"path": path, "sha256": "f" * 64} for key, path in identity.AUTHORITY_PATHS.items()},
            "proposal": {"path": identity.PROPOSAL_PATH, "sha256": identity.PROPOSAL_SHA},
            "scope": {"path": identity.SCOPE_PATH, "sha256": identity.SCOPE_SHA},
            "frozen_history": {"path": identity.FROZEN_HISTORY_PATH, "sha256": identity.FROZEN_HISTORY_SHA},
            "implementation_validation": {"path": identity.CERTIFICATE_PATH, "sha256": "e" * 64},
            "post_commit_checkpoint": identity.POST_COMMIT_PATH,
            "selected_method": None, "selected_operating_point": None, "quality_gate": None}


def invented_scope():
    return {"schema_version": "ball_crop_candidate_identity_review_scope/v0.1",
            "status": "proposed_not_authorized", "prepared_at_commit": identity.BASE_COMMIT,
            "proposal_path": identity.PROPOSAL_PATH, "window_id": identity.WINDOW_ID,
            "setting": copy.deepcopy(identity.SETTING), "scientific_inputs": copy.deepcopy(identity.SCIENTIFIC_INPUTS),
            "selection_source": {"frame_indices": list(identity.FRAMES), "source_row_pointer": "/pools/0/rows/16",
                                 "field": "present_nonmatching_current_output"},
            "proposed_worker": {"unit": identity.UNIT_KEY, "maximum_attempts": 1, "maximum_charged_seconds": 120,
                                "output_root": identity.OUTPUT_ROOT + "/" + identity.OUTPUT_DIR},
            "human_review": {"reviewer": "Ryan", "sequence": list(identity.ROLES),
                "identity_choices": ["ball", "another_object", "uncertain"],
                "ball_center_choices": ["plausible", "clearly_displaced", "cannot_judge"],
                "other_identity_center_value": "not_applicable", "initial_row_status": "pending",
                "source_first_not_blind": True, "parent_pixel_inspection_authorized": False,
                "preserve_localization_outcome": True},
            "selected_method": None, "selected_operating_point": None, "quality_gate": None}


class TemporaryRoot(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="cir_")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()


class IdentityBudgetTests(TemporaryRoot):
    def journal(self, events=None, approved=None):
        value = identity.IdentityJournal.__new__(identity.IdentityJournal)
        value.root, value.folder = self.root, self.root / "resource_events"
        value.events = invented_prefix() if events is None else events
        value.limits = limits() if approved is None else approved
        return value

    def test_exact_prefix_keeps_60_closed_attempts_56_successes_and_four_failures(self):
        journal = self.journal()
        self.assertEqual(len(journal.events), 3121)
        starts, ends = identity._closed_prefix(journal)
        self.assertEqual(len(starts), 60)
        self.assertEqual(sum(event["success"] is True for event in ends.values()), 56)
        self.assertEqual({aid for aid, event in ends.items() if not event["success"]}, recovery.KNOWN_FAILURES)
        self.assertAlmostEqual(journal.consumed(), identity.USED_SECONDS, places=7)
        self.assertAlmostEqual(journal.consumed(presence.UNIT_KEY), 42.734, places=7)

    def test_one_new_120_second_reservation_preserves_completed_history_and_old_allowances(self):
        journal = self.journal()
        before = copy.deepcopy(journal.events)
        aid, seconds = journal.reserve(identity.UNIT_KEY, False)
        self.assertEqual(seconds, 120)
        self.assertEqual(journal.events[:-1], before)
        self.assertEqual(journal.events[-1]["unit_key"], identity.UNIT_KEY)
        self.assertIs(journal.events[-1]["selection_unit"], False)
        self.assertAlmostEqual(journal.limits["maximum_cumulative_seconds"] - identity.USED_SECONDS,
                               11037.211000000018, places=7)
        seal = json.loads((self.root / "attempts" / (aid + ".reservation.json")).read_text())
        self.assertEqual(seal, {"event_sha256": journal.events[-1]["sha256"]})

    def test_smaller_cumulative_balance_and_exhausted_budget_are_respected(self):
        approved = limits()
        approved["maximum_cumulative_seconds"] = identity.USED_SECONDS + 2
        _, seconds = self.journal(approved=approved).reserve(identity.UNIT_KEY, False)
        self.assertAlmostEqual(seconds, 2, places=7)
        approved["maximum_cumulative_seconds"] = identity.USED_SECONDS
        with self.assertRaises((ValueError, resources.ResourceLimitError)):
            self.journal(approved=approved).reserve(identity.UNIT_KEY, False)

    def test_other_roles_selection_or_prior_attempt_cannot_receive_another_reservation(self):
        for key, selection in ((original.UNIT_KEY, False), (recovery.UNIT_KEY, False),
                               (presence.UNIT_KEY, False), (identity.UNIT_KEY, True), ("unknown", False)):
            with self.subTest(key=key, selection=selection), self.assertRaises(ValueError):
                self.journal().reserve(key, selection)
        journal = self.journal()
        journal.reserve(identity.UNIT_KEY, False)
        with self.assertRaises(ValueError):
            journal.reserve(identity.UNIT_KEY, False)

    def test_prefix_tip_success_role_budget_and_unknown_suffix_are_rejected(self):
        changes = (lambda e: e.pop(0), lambda e: e[-1].__setitem__("sha256", "0" * 64),
                   lambda e: e[-1].__setitem__("success", False),
                   lambda e: e[-1].__setitem__("elapsed_seconds", 1),
                   lambda e: e[-50].__setitem__("unit_key", "unapproved"),
                   lambda e: e.append({"kind": "started", "attempt_id": "e" * 32, "unit_key": "unknown",
                                       "selection_unit": False, "reserved_seconds": 1., "sha256": "f" * 64}))
        for change in changes:
            events = invented_prefix()
            change(events)
            with self.subTest(change=change), self.assertRaises((ValueError, resources.ResourceLimitError)):
                self.journal(events).reserve(identity.UNIT_KEY, False)


class CompactHistory:
    """60 sealed invented attempts, retaining exact role counts with tiny files."""
    def __init__(self, root):
        self.old = presence_fixtures.CompactHistory(root)
        self.root, self.output, self.journal = root, self.old.output, self.old.journal
        aid = identity.PREDECESSOR_ATTEMPT
        self.result_path = self.output / "attempts" / (aid + ".result.json")
        write_json(self.result_path, {"invented": True, "attempt_id": aid,
                                    "inert_scientific_pointer": "/must/not/open"})
        self.result_sha = binding(root, self.result_path)["sha256"]
        with patch.object(resources, "_write_new", side_effect=write_json):
            start = self.journal.append("started", attempt_id=aid, unit_key=presence.UNIT_KEY,
                                       selection_unit=False, reserved_seconds=120)
            write_json(self.output / "attempts" / (aid + ".reservation.json"), {"event_sha256": start["sha256"]})
            completed = completion_event()
            completed["worker_result"]["sha256"] = self.result_sha
            end = self.journal.append("finished", attempt_id=aid, **completed)
        self.count, self.tip, self.used = len(self.journal.events), end["sha256"], self.journal.consumed()
        self.images = TinyImages(root)
        history = {"raw_event_bindings": [binding(root, path) for path in sorted(self.journal.folder.glob("*.json"))],
                   "administrative_attempt_bindings": [binding(root, path) for path in sorted((self.output / "attempts").glob("*.json"))],
                   "prior_output_presence_completion": end,
                   "scientific_input_metadata": self.images.metadata,
                   "preserved_files": [{"path": path.relative_to(root).as_posix(), **original._stat_metadata(path)}
                                       for path in self.output.rglob("*") if path.is_file()],
                   "preserved_directories": [path.relative_to(root).as_posix() for path in self.output.rglob("*") if path.is_dir()],
                   "preserved_absent_paths": [identity.OUTPUT_ROOT + "/" + identity.OUTPUT_DIR,
                                              identity.OUTPUT_ROOT + "/supervisor.lock"],
                   "protection": self.old.context["history"]["protection"]}
        self.context = {"root": root, "output_root": self.output, "limits": self.old.context["limits"],
                        "history": history, "policy": monitor.monitoring_policy(limits(), .25),
                        "commit": "b" * 40, "spec_sha256": "a" * 64}

    def scope(self):
        stack = self.old.scope()
        stack.enter_context(patch.object(identity, "SCIENTIFIC_INPUTS", self.images.inputs))
        for key, value in (("PREFIX_COUNT", self.count), ("PREFIX_TIP", self.tip),
                           ("USED_SECONDS", self.used), ("PREDECESSOR_RESULT_SHA", self.result_sha)):
            stack.enter_context(patch.object(identity, key, value))
        return stack

    def start(self):
        with self.scope():
            journal = identity.IdentityJournal(self.output, self.context["limits"])
            aid, _ = journal.reserve(identity.UNIT_KEY, False)
        self.journal = journal
        policy = self.context["policy"]
        write_json(self.output / "attempts" / (aid + ".monitoring_policy.json"),
                   {"policy": policy, "sha256": resources._digest(policy)})
        return aid


class HistoryIntegrationTests(TemporaryRoot):
    def test_closed_history_reads_only_administrative_records_and_refuses_failed_result_adoption(self):
        fixture = CompactHistory(self.root)
        real_verify = identity.verify_binding

        def guard(root, row):
            self.assertTrue("/resource_events/" in row["path"] or "/attempts/" in row["path"])
            return real_verify(root, row)

        with fixture.scope(), patch.object(identity, "verify_binding", side_effect=guard):
            journal = identity.verify_history(self.root, fixture.context, "before")
        self.assertEqual(len(journal._attempts()), 60)
        write_json(fixture.output / "attempts" / (recovery.FAILED_ATTEMPT + ".result.json"), {"unreceipted": True})
        with fixture.scope(), self.assertRaises(ValueError):
            identity.verify_history(self.root, fixture.context, "before")

    def test_worker_requires_sole_owned_attempt_and_reviewed_monitor_policy(self):
        fixture = CompactHistory(self.root)
        aid = fixture.start()
        with fixture.scope(), patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": aid}):
            identity.verify_history(self.root, fixture.context, "worker")
            for phase in ("before", "completed"):
                with self.subTest(phase=phase), self.assertRaises(ValueError):
                    identity.verify_history(self.root, fixture.context, phase)
        with fixture.scope(), patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": "a" * 32}), self.assertRaises(ValueError):
            identity.verify_history(self.root, fixture.context, "worker")
        write_json(fixture.output / "attempts" / (aid + ".monitoring_policy.json"),
                   {"policy": fixture.context["policy"], "sha256": "0" * 64})
        with fixture.scope(), patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": aid}), self.assertRaises(ValueError):
            identity.verify_history(self.root, fixture.context, "worker")

    def test_preservation_uses_only_metadata_and_refuses_unreceipted_file_or_image_drift(self):
        fixture = CompactHistory(self.root)
        with fixture.scope(), patch.object(Path, "open", side_effect=AssertionError("preserved body opened")):
            identity._preserved_metadata(self.root, fixture.context)
        extra = fixture.output / "unreceipted.json"
        extra.write_bytes(b"preserve unknown evidence")
        with fixture.scope(), self.assertRaisesRegex(ValueError, "Unexpected evidence file"):
            identity._preserved_metadata(self.root, fixture.context)
        self.assertEqual(extra.read_bytes(), b"preserve unknown evidence")
        extra.unlink()  # This test owns the complete fabricated temporary root.
        fixture.images.paths[0].write_bytes(b"changed invented image size")
        with fixture.scope(), self.assertRaisesRegex(ValueError, "metadata changed"):
            identity._preserved_metadata(self.root, fixture.context)


class ReleaseGateTests(TemporaryRoot):
    def test_manifest_cannot_expand_images_units_stages_outputs_or_choose_method(self):
        manifest = invented_manifest()
        identity._validate_manifest(manifest)
        for change in ({"unit_key": presence.UNIT_KEY}, {"maximum_unit_seconds": 121},
                       {"output_dir": presence.OUTPUT_DIR}, {"permitted_stages": ["render"]},
                       {"selected_method": "invented-choice"}, {"scientific_inputs": manifest["scientific_inputs"][:-1]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                identity._validate_manifest({**manifest, **change})

    def test_dirty_tree_stops_before_manifest_history_or_image_access(self):
        failure = ValueError("invented dirty tree")
        with patch.object(original.original, "_clean_checkpoint", side_effect=failure), \
             patch.object(identity, "read_json", side_effect=AssertionError("manifest read")), \
             patch.object(presence, "_metadata", side_effect=AssertionError("historical read")), \
             patch.object(identity, "_verify_image_bytes", side_effect=AssertionError("image read")):
            with self.assertRaises(ValueError) as caught:
                identity._metadata(self.root, self.root / identity.MANIFEST_PATH)
        self.assertIs(caught.exception, failure)

    def test_missing_release_checkpoint_stops_before_audit_reads_or_dispatch(self):
        path = self.root / identity.MANIFEST_PATH
        write_json(path, {})
        with patch.object(original.original, "_clean_checkpoint", return_value="b" * 40), \
             patch.object(identity, "_validate_manifest"), \
             patch.object(identity, "verify_binding", side_effect=AssertionError("authority read")), \
             patch.object(identity, "_run_bounded_supervised", side_effect=AssertionError("dispatch")):
            for dry in (False, True):
                with self.subTest(dry_run=dry), self.assertRaisesRegex(ValueError, "checkpoint is absent"):
                    identity.run_identity_review(self.root, path, dry_run=dry)

    def test_parent_administrative_reader_rejects_images_outputs_and_undeclared_pointers(self):
        forbidden = [row[role]["path"] for row in identity.SCIENTIFIC_INPUTS for role in identity.ROLES]
        forbidden += [identity.OUTPUT_ROOT + "/" + name for name in identity.OUTPUTS]
        forbidden += ["data/outputs/unapproved_scientific_manifest.json"]
        with patch.object(Path, "open", side_effect=AssertionError("scientific body opened")):
            for name in forbidden:
                with self.subTest(path=name), self.assertRaises(ValueError):
                    identity._read_bound(self.root, {"path": name, "sha256": "a" * 64})

    def test_checkpoint_requires_exact_new_commit_bound_sources_and_authorized_clean_release(self):
        manifest, commit = invented_manifest(), "b" * 40
        manifest_path = self.root / identity.MANIFEST_PATH
        write_json(manifest_path, manifest)
        checkpoint = {"schema_version": "ball_crop_candidate_identity_review_execution_checkpoint/v0.1",
            "head": commit, "branch": "codex/ball-detector-baseline", "manifest": binding(self.root, manifest_path),
            "implementation_validation": manifest["implementation_validation"],
            "manifest_spec_sha256": identity._spec_sha256(manifest), "preserved_prefix_tip_sha256": identity.PREFIX_TIP,
            **{key: True for key in ("execution_authorized", "clean", "index_empty", "validated_sources_unchanged")}}
        path = self.root / identity.POST_COMMIT_PATH
        write_json(path, checkpoint)
        with patch.object(identity.subprocess, "run", return_value=SimpleNamespace(returncode=0)):
            self.assertEqual(identity._post_commit_checkpoint(self.root, manifest, commit), checkpoint)
            for key, value in (("head", identity.BASE_COMMIT), ("branch", "main"),
                               ("manifest_spec_sha256", "0" * 64), ("preserved_prefix_tip_sha256", "0" * 64),
                               ("execution_authorized", False), ("clean", False),
                               ("index_empty", False), ("validated_sources_unchanged", False)):
                write_json(path, {**checkpoint, key: value})
                with self.subTest(key=key), self.assertRaises(ValueError):
                    identity._post_commit_checkpoint(self.root, manifest, commit)


class ScopeTests(unittest.TestCase):
    def test_scope_requires_exact_eight_frames_source_first_and_unchanged_setting(self):
        scope = invented_scope()
        self.assertEqual(identity._validate_scope(scope), scope)
        expected = [(frame, role) for frame in (300, 301, 302, 304, 308, 319, 320, 324) for role in identity.ROLES]
        rows = identity._input_rows(scope["scientific_inputs"])
        self.assertEqual([(row["frame_index"], row["role"]) for row in rows], expected)
        for field, value in (("window_id", "another-window"), ("status", "approved"),
                             ("setting", {**scope["setting"], "policy": "all"}),
                             ("selected_method", "chosen")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                identity._validate_scope({**scope, field: value})
        for field, value in (("sequence", list(reversed(identity.ROLES))),
                             ("source_first_not_blind", False), ("initial_row_status", "reviewed"),
                             ("parent_pixel_inspection_authorized", True), ("preserve_localization_outcome", False)):
            wrong = copy.deepcopy(scope)
            wrong["human_review"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                identity._validate_scope(wrong)

    def test_missing_extra_reordered_or_substituted_image_binding_is_not_an_input(self):
        correct = copy.deepcopy(identity.SCIENTIFIC_INPUTS)
        alternatives = [correct[:-1], correct + [correct[0]], list(reversed(correct))]
        changed = copy.deepcopy(correct)
        changed[0][identity.ROLES[0]]["sha256"] = "0" * 64
        alternatives.append(changed)
        changed = copy.deepcopy(correct)
        changed[0]["frame_index"] = 310  # Missing-output row expressly excluded from this study.
        alternatives.append(changed)
        for inputs in alternatives:
            with self.subTest(inputs=inputs), self.assertRaises(ValueError):
                identity._input_rows(inputs)

    def test_pending_ledger_and_source_first_guide_have_no_automatic_human_judgments(self):
        scope = invented_scope()
        before = copy.deepcopy(scope)
        with patch.object(Path, "open", side_effect=AssertionError("pure helper body access")):
            ledger = identity._pending_ledger(scope)
            guide = identity._review_guide(Path("C:/invented/root"), scope)
        self.assertEqual(scope, before)
        self.assertEqual([row["frame_index"] for row in ledger["rows"]], list(identity.FRAMES))
        self.assertEqual(ledger["required_reviewer"], "Ryan")
        for row, expected in zip(ledger["rows"], scope["scientific_inputs"]):
            self.assertEqual(row["image_bindings"], {role: expected[role] for role in identity.ROLES})
            self.assertEqual(row["prior_localization_outcome"], "present_nonmatching_current_output")
            self.assertEqual(row["status"], "pending")
            self.assertTrue(all(row[key] is None for key in ("reviewer", "actual_response", "recorded_at_utc",
                "emitted_candidate_index", "candidate_identity", "ball_center", "note")))
        self.assertIn("not blind or independent", guide)
        self.assertIn("amber alt # markers are not emissions", guide)
        pointers = [guide.index(row[role]["path"]) for row in scope["scientific_inputs"] for role in identity.ROLES]
        self.assertEqual(pointers, sorted(pointers))
        self.assertLessEqual(len(guide.encode("utf-8")), 65536)


class CertificateTests(TemporaryRoot):
    def fixture(self):
        manifest = invented_manifest()
        paths = [self.root / name for name in ("src/invented.py", "tests/test_invented.py", "requirements.txt")]
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# invented validation source\n", encoding="utf-8")
        evidence = self.root / identity.IMPLEMENTATION_DIR / "invented_validation.json"
        write_json(evidence, {"invented": True})
        certificate = {"schema_version": "ball_crop_candidate_identity_review_implementation_validation/v0.1",
            "manifest_spec_sha256": identity._spec_sha256(manifest),
            "authority_sha256": {key: manifest[key]["sha256"] for key in identity.AUTHORITY_FIELDS},
            **{key: True for key in ("focused_tests_passed", "full_suite_passed", "independent_static_review_passed",
                                    "integrity_tests_passed", "monitor_design_check_passed")},
            "source_bindings": [binding(self.root, path) for path in paths],
            "evidence_bindings": [binding(self.root, evidence)]}
        return manifest, certificate, paths

    def check(self, manifest, certificate):
        path = self.root / identity.CERTIFICATE_PATH
        write_json(path, certificate)
        manifest = {**manifest, "implementation_validation": binding(self.root, path)}
        with patch.object(original.original, "_git", return_value="tracked"):
            return identity._validate_implementation(self.root, manifest)

    def test_current_certificate_requires_complete_unchanged_source_inventory(self):
        manifest, certificate, paths = self.fixture()
        self.assertEqual(self.check(manifest, certificate), certificate)
        with self.assertRaisesRegex(ValueError, "complete current source inventory"):
            self.check(manifest, {**certificate, "source_bindings": certificate["source_bindings"][:1]})
        paths[1].write_text("# changed after validation\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.check(manifest, certificate)

    def test_validation_flags_and_unapproved_scientific_evidence_cannot_be_adopted(self):
        manifest, certificate, _ = self.fixture()
        for field in ("focused_tests_passed", "full_suite_passed", "independent_static_review_passed",
                      "integrity_tests_passed", "monitor_design_check_passed"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check(manifest, {**certificate, field: False})
        forbidden = identity.SCIENTIFIC_INPUTS[0][identity.ROLES[0]]
        wrong = {**certificate, "evidence_bindings": [{key: forbidden[key] for key in ("path", "sha256")}]}
        real_verify = identity.verify_binding

        def guard(root, row):
            self.assertNotEqual(row["path"], forbidden["path"])
            return real_verify(root, row)

        with patch.object(identity, "verify_binding", side_effect=guard), self.assertRaisesRegex(ValueError, "outside"):
            self.check(manifest, wrong)


class TinyImages:
    def __init__(self, root):
        self.root, self.inputs, self.metadata, self.paths = root, [], [], []
        for frame in identity.FRAMES:
            row = {"frame_index": frame}
            for role in identity.ROLES:
                path = root / "data/outputs/invented_identity_images" / str(frame) / (role + ".png")
                path.parent.mkdir(parents=True, exist_ok=True)
                # Deliberately not an image: any accidental decoder cannot succeed.
                path.write_bytes(("invented opaque bytes " + str(frame) + " " + role).encode("ascii"))
                row[role] = {**binding(root, path), "size_bytes": path.stat().st_size}
                self.metadata.append({"path": path.relative_to(root).as_posix(), **original._stat_metadata(path)})
                self.paths.append(path)
            self.inputs.append(row)

    def scope(self):
        stack = ExitStack()
        stack.enter_context(patch.object(identity, "SCIENTIFIC_INPUTS", self.inputs))
        stack.enter_context(patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": "d" * 32}))
        return stack


class ImageByteTests(TemporaryRoot):
    def test_exact_sixteen_opaque_files_are_hashed_without_pixel_decoding_or_other_file_access(self):
        fixture = TinyImages(self.root)
        opened, actual_open, actual_import = [], Path.open, builtins.__import__

        def guard(path, *args, **kwargs):
            self.assertIn(path, fixture.paths)
            self.assertEqual(args[0] if args else kwargs.get("mode", "r"), "rb")
            opened.append(path)
            return actual_open(path, *args, **kwargs)

        def imports(name, *args, **kwargs):
            self.assertNotIn(name.split(".")[0], {"cv2", "PIL", "imageio", "skimage", "matplotlib"})
            return actual_import(name, *args, **kwargs)

        with fixture.scope(), patch.object(Path, "open", guard), patch.object(builtins, "__import__", imports):
            result = identity._verify_image_bytes(self.root, fixture.inputs, fixture.metadata)
        self.assertIs(result["success"], True)
        self.assertIs(result["pixels_decoded"], False)
        self.assertEqual(len(result["images"]), 16)
        self.assertEqual(set(opened), set(fixture.paths))
        self.assertEqual([(row["frame_index"], row["role"]) for row in result["images"]],
                         [(frame, role) for frame in identity.FRAMES for role in identity.ROLES])
        for checked, expected in zip(result["images"], fixture.metadata):
            self.assertEqual(checked["expected"]["path"], expected["path"])
            self.assertEqual(checked["actual"]["sha256"], binding(self.root, self.root / expected["path"])["sha256"])

    def test_parent_without_worker_ownership_cannot_open_any_image(self):
        fixture = TinyImages(self.root)
        with patch.object(identity, "SCIENTIFIC_INPUTS", fixture.inputs), patch.dict(os.environ, {}, clear=True), \
             patch.object(Path, "open", side_effect=AssertionError("parent image opened")), self.assertRaises(ValueError):
            identity._verify_image_bytes(self.root, fixture.inputs, fixture.metadata)

    def test_hash_mismatch_records_actual_bytes_stops_later_reads_and_cannot_validate(self):
        fixture = TinyImages(self.root)
        fixture.inputs[0][identity.ROLES[0]]["sha256"] = "0" * 64
        opened, actual_open = [], Path.open

        def guard(path, *args, **kwargs):
            opened.append(path)
            return actual_open(path, *args, **kwargs)

        with fixture.scope(), patch.object(Path, "open", guard):
            result = identity._verify_image_bytes(self.root, fixture.inputs, fixture.metadata)
            with self.assertRaises(ValueError):
                identity._validate_verification(result, fixture.inputs, fixture.metadata)
        self.assertFalse(result["success"])
        self.assertEqual(opened, [fixture.paths[0]])
        self.assertEqual(result["images"][0]["expected"]["sha256"], "0" * 64)
        self.assertEqual(result["images"][0]["actual"]["sha256"], binding(self.root, fixture.paths[0])["sha256"])
        self.assertTrue(all(row["error"] == "not_attempted_after_prior_failure" for row in result["images"][1:]))

    def test_metadata_drift_symlink_and_escape_paths_stop_before_any_body_open(self):
        fixture = TinyImages(self.root)
        metadata = copy.deepcopy(fixture.metadata)
        metadata[0]["mtime_ns"] += 1
        with fixture.scope(), patch.object(Path, "open", side_effect=AssertionError("preflight image read")), self.assertRaises(ValueError):
            identity._verify_image_bytes(self.root, fixture.inputs, metadata)
        real_symlink = Path.is_symlink

        def symlink(path):
            return path == fixture.paths[0] or real_symlink(path)

        with fixture.scope(), patch.object(Path, "is_symlink", symlink), \
             patch.object(Path, "open", side_effect=AssertionError("symlink image read")), self.assertRaises(ValueError):
            identity._verify_image_bytes(self.root, fixture.inputs, fixture.metadata)
        fixture.inputs[0][identity.ROLES[0]]["path"] = "../forbidden.png"
        fixture.metadata[0]["path"] = "../forbidden.png"
        with fixture.scope(), patch.object(Path, "open", side_effect=AssertionError("escaped image read")), self.assertRaises(ValueError):
            identity._verify_image_bytes(self.root, fixture.inputs, fixture.metadata)

    def test_success_receipt_rejects_missing_rows_changed_binding_or_claimed_pixel_decode(self):
        fixture = TinyImages(self.root)
        with fixture.scope():
            result = identity._verify_image_bytes(self.root, fixture.inputs, fixture.metadata)
            identity._validate_verification(result, fixture.inputs, fixture.metadata)
            wrong = copy.deepcopy(result)
            wrong["images"][0]["actual"]["sha256"] = "0" * 64
            for changed in (wrong, {**result, "images": result["images"][:-1]}, {**result, "pixels_decoded": True}):
                with self.subTest(changed=changed), self.assertRaises(ValueError):
                    identity._validate_verification(changed, fixture.inputs, fixture.metadata)

    def test_same_size_change_during_streaming_invalidates_verification(self):
        fixture = TinyImages(self.root)
        actual_open = Path.open
        target = fixture.paths[0]
        original_bytes = target.read_bytes()
        stamp = target.stat()

        class ChangingStream:
            def __init__(self, stream):
                self.stream, self.changed = stream, False

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.stream.close()

            def read(self, size):
                value = self.stream.read(size)
                if not self.changed:
                    self.changed = True
                    with actual_open(target, "wb") as stream:
                        stream.write(b"x" * len(original_bytes))
                    os.utime(target, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 1000000000))
                return value

        def open_changed(path, *args, **kwargs):
            stream = actual_open(path, *args, **kwargs)
            return ChangingStream(stream) if path == target else stream

        with fixture.scope(), patch.object(Path, "open", open_changed):
            result = identity._verify_image_bytes(self.root, fixture.inputs, fixture.metadata)
        self.assertFalse(result["success"])
        self.assertFalse(result["images"][0]["success"])
        self.assertNotEqual(result["images"][0]["metadata_before"], result["images"][0]["metadata_after"])
        self.assertTrue(all(row["actual"] is None for row in result["images"][1:]))


class TinyWorker(TinyImages):
    def __init__(self, root):
        super().__init__(root)
        self.aid = "d" * 32
        self.output = root / identity.OUTPUT_ROOT
        (self.output / "review").mkdir(parents=True)
        (self.output / "attempts").mkdir()
        self.result_path = self.output / "attempts" / (self.aid + ".result.json")
        with patch.object(identity, "SCIENTIFIC_INPUTS", self.inputs):
            self.scope_metadata = invented_scope()
            manifest = invented_manifest()
        write_json(root / identity.POST_COMMIT_PATH, {"invented_checkpoint": True})
        self.context = {"root": root, "manifest_path": root / identity.MANIFEST_PATH,
            "manifest": manifest, "scope": self.scope_metadata,
            "commit": "b" * 40, "spec_sha256": "a" * 64, "output_root": self.output, "limits": limits(),
            "history": {"scientific_input_metadata": self.metadata, "preserved_files": [],
                "preserved_directories": [identity.OUTPUT_ROOT + "/review", identity.OUTPUT_ROOT + "/attempts"],
                "preserved_absent_paths": [identity.OUTPUT_ROOT + "/" + identity.OUTPUT_DIR,
                                           identity.OUTPUT_ROOT + "/supervisor.lock"],
                "protection": {"sealed_holdouts_metadata_only": original.HOLDOUTS,
                    "preserved_absent_paths": ["data/outputs/ball_tracking/detections/invented_embargo_" + str(i) for i in range(9)]}},
            "certificate": {"source_bindings": []},
            "policy": monitor.monitoring_policy(limits(), .25)}
        self.journal = SimpleNamespace(_attempts=lambda: {self.aid: {"start": {"sha256": "c" * 64}}})

    def scope(self):
        stack = super().scope()
        stack.enter_context(patch.object(resources, "wait_for_supervisor"))
        stack.enter_context(patch.object(identity, "_metadata", return_value=self.context))
        stack.enter_context(patch.object(identity, "verify_history", return_value=self.journal))
        self.preservation = stack.enter_context(patch.object(identity, "_preserved_metadata"))
        stack.enter_context(patch.dict(os.environ, {"BALL_RETENTION_RESULT_PATH": str(self.result_path)}))
        stack.enter_context(patch.object(presence, "_worker", side_effect=AssertionError("old scientific worker")))
        stack.enter_context(patch.object(presence, "_load_breakdown", side_effect=AssertionError("old scientific input")))
        return stack


class WorkerTests(TemporaryRoot):
    def test_worker_opens_only_sixteen_images_and_exact_new_administrative_files(self):
        fixture = TinyWorker(self.root)
        opened, actual_open = [], Path.open
        expected = set(fixture.paths) | {fixture.result_path, self.root / identity.POST_COMMIT_PATH,
                                        *[fixture.output / name for name in identity.OUTPUTS]}

        def guard(path, *args, **kwargs):
            self.assertIn(path, expected)
            opened.append(path)
            return actual_open(path, *args, **kwargs)

        with fixture.scope(), patch.object(Path, "open", guard):
            result = identity._worker(self.root, fixture.context["manifest_path"])
        self.assertEqual(result, {"worker_result_written": True, "attempt_id": fixture.aid, "completion_pending": True})
        self.assertEqual([path for path in opened if path in fixture.paths], fixture.paths)
        destination = fixture.output / identity.OUTPUT_DIR
        self.assertEqual({path.name for path in destination.iterdir()}, set(identity.OUTPUT_NAMES))
        ledger = json.loads((destination / "pending_review.json").read_text(encoding="utf-8"))
        self.assertEqual(len(ledger["rows"]), 8)
        self.assertTrue(all(row["status"] == "pending" and row["actual_response"] is None for row in ledger["rows"]))
        receipt = json.loads(fixture.result_path.read_text(encoding="utf-8"))
        self.assertTrue(receipt["verification"]["success"])
        self.assertEqual(receipt["pending_review"], ledger)
        self.assertLessEqual(fixture.result_path.stat().st_size, monitor.WORKER_RECEIPT_LIMIT)

    def test_wrong_receipt_location_and_existing_output_directory_never_overwrite_evidence(self):
        fixture = TinyWorker(self.root)
        with fixture.scope(), patch.dict(os.environ, {"BALL_RETENTION_RESULT_PATH": str(self.root / "wrong.json")}), \
             patch.object(identity, "_verify_image_bytes", side_effect=AssertionError("premature image access")), \
             self.assertRaises(ValueError):
            identity._worker(self.root, fixture.context["manifest_path"])
        destination = fixture.output / identity.OUTPUT_DIR
        destination.mkdir()
        marker = destination / "verification.json"
        marker.write_bytes(b"preserve previous partial")
        with fixture.scope(), self.assertRaises(ValueError):
            identity._worker(self.root, fixture.context["manifest_path"])
        self.assertEqual(marker.read_bytes(), b"preserve previous partial")
        self.assertFalse(fixture.result_path.exists())

    def test_failed_hash_leaves_verification_evidence_only_and_never_releases_human_review(self):
        fixture = TinyWorker(self.root)
        fixture.inputs[0][identity.ROLES[0]]["sha256"] = "0" * 64
        with fixture.scope(), self.assertRaises(ValueError):
            identity._worker(self.root, fixture.context["manifest_path"])
        destination = fixture.output / identity.OUTPUT_DIR
        self.assertEqual([path.name for path in destination.iterdir()], ["verification.json"])
        result = json.loads((destination / "verification.json").read_text())
        self.assertFalse(result["success"])
        self.assertEqual(result["images"][0]["expected"]["sha256"], "0" * 64)
        self.assertIsNotNone(result["images"][0]["actual"])
        self.assertFalse(fixture.result_path.exists())

    def test_preservation_or_receipt_publication_failure_keeps_partial_outputs_without_adoption(self):
        actual_write = original._write_new
        for failure in ("preservation", "publication"):
            with self.subTest(failure=failure):
                fixture = TinyWorker(self.root / failure)

                def write(path, payload):
                    if path == fixture.result_path:
                        raise OSError("invented receipt publication failure")
                    return actual_write(path, payload)

                with fixture.scope(), ExitStack() as stack:
                    if failure == "preservation":
                        fixture.preservation.side_effect = [None, ValueError("invented final metadata drift")]
                    else:
                        stack.enter_context(patch.object(original, "_write_new", side_effect=write))
                    with self.assertRaises((ValueError, OSError)):
                        identity._worker(fixture.root, fixture.context["manifest_path"])
                self.assertEqual({path.name for path in (fixture.output / identity.OUTPUT_DIR).iterdir()}, set(identity.OUTPUT_NAMES))
                self.assertFalse(fixture.result_path.exists())


class ReceiptTests(TemporaryRoot):
    def fixture(self):
        fixture = TinyWorker(self.root)
        with fixture.scope():
            identity._worker(self.root, fixture.context["manifest_path"])
        receipt = json.loads(fixture.result_path.read_text(encoding="utf-8"))
        event = {"attempt_id": fixture.aid, "sha256": "c" * 64,
                 "worker_result": {"path": "attempts/" + fixture.aid + ".result.json",
                                   "sha256": binding(self.root, fixture.result_path)["sha256"]}}
        return fixture, receipt, event

    def scope(self, fixture, event):
        stack = ExitStack()
        stack.enter_context(patch.object(identity, "SCIENTIFIC_INPUTS", fixture.inputs))
        stack.enter_context(patch.object(identity, "verify_history", return_value=SimpleNamespace(events=[event])))
        return stack

    def test_parent_opens_only_bounded_receipt_and_releases_pending_review_without_pixel_inspection(self):
        fixture, receipt, event = self.fixture()
        opened, actual_open = [], Path.open

        def guard(path, *args, **kwargs):
            self.assertEqual(path, fixture.result_path)
            opened.append(path)
            return actual_open(path, *args, **kwargs)

        with self.scope(fixture, event), patch.object(Path, "open", guard):
            result = identity._completed_result(self.root, fixture.context, event)
        self.assertEqual(opened, [fixture.result_path])
        self.assertEqual(result["pending_review"], receipt["pending_review"])
        self.assertTrue(result["human_review_pending"])
        self.assertFalse(result["parent_pixel_inspection_authorized"])
        self.assertFalse(result["media_decoded"])
        self.assertEqual(result["new_model_calls"], 0)

    def test_invented_judgment_altered_verification_or_guide_cannot_be_returned(self):
        fixture, receipt, event = self.fixture()
        changes = []
        wrong = copy.deepcopy(receipt)
        wrong["pending_review"]["rows"][0].update(status="reviewed", reviewer="Ryan", candidate_identity="ball")
        changes.append(wrong)
        wrong = copy.deepcopy(receipt)
        wrong["verification"]["images"][0]["actual"]["sha256"] = "0" * 64
        changes.append(wrong)
        wrong = copy.deepcopy(receipt)
        wrong["guide_payload"]["text"] = "Invented changed instructions."
        changes.append(wrong)
        for wrong in changes:
            write_json(fixture.result_path, wrong)
            event["worker_result"]["sha256"] = binding(self.root, fixture.result_path)["sha256"]
            with self.subTest(wrong=wrong), self.scope(fixture, event), self.assertRaises(ValueError):
                identity._completed_result(self.root, fixture.context, event)

    def test_oversized_receipt_and_changed_image_metadata_reject_without_body_access(self):
        fixture, receipt, event = self.fixture()
        fixture.result_path.write_bytes(b"x" * (monitor.WORKER_RECEIPT_LIMIT + 1))
        with self.scope(fixture, event), patch.object(Path, "open", side_effect=AssertionError("oversized receipt read")), \
             self.assertRaisesRegex(ValueError, "byte bound"):
            identity._completed_result(self.root, fixture.context, event)
        write_json(fixture.result_path, receipt)
        event["worker_result"]["sha256"] = binding(self.root, fixture.result_path)["sha256"]
        fixture.paths[0].write_bytes(b"changed image metadata after verification")
        with self.scope(fixture, event), patch.object(Path, "open", side_effect=AssertionError("changed image body read")), \
             self.assertRaisesRegex(ValueError, "metadata changed"):
            identity._completed_result(self.root, fixture.context, event)


class DispatchTests(TemporaryRoot):
    def test_exact_role_uses_existing_monitor_without_global_journal_override(self):
        context = {"root": self.root, "output_root": self.root / "invented_output", "limits": limits()}
        command = ["invented-python", "-B", "invented-worker"]
        completion = {"success": True, "attempt_id": "a" * 32}
        baseline = resources.BudgetJournal
        with patch.object(monitor, "run_supervised", return_value=completion) as launch, \
             patch.object(resources, "run_supervised", side_effect=AssertionError("legacy supervisor")):
            self.assertIs(identity._run_bounded_supervised(context, command), completion)
        launch.assert_called_once_with(context["output_root"], identity.UNIT_KEY, command, context["limits"],
            cwd=self.root, selection_unit=False, poll_seconds=.25, require_result=True,
            journal_factory=identity.IdentityJournal)
        self.assertIs(resources.BudgetJournal, baseline)

    def test_monitor_failure_has_one_dispatch_no_retry_and_no_publication(self):
        path = self.root / identity.MANIFEST_PATH
        context = {"root": self.root, "manifest_path": path, "commit": "b" * 40,
                   "spec_sha256": "a" * 64}
        failure = resources.ResourceLimitError("invented monitor failure")
        with patch.object(identity, "_metadata", return_value=context) as metadata, \
             patch.object(identity, "verify_history"), patch.object(identity, "_preserved_metadata"), \
             patch.object(identity, "_run_bounded_supervised", side_effect=failure) as launch, \
             patch.object(identity, "_completed_result", side_effect=AssertionError("failed result release")):
            with self.assertRaises(resources.ResourceLimitError) as caught:
                identity.run_identity_review(self.root, path)
        self.assertIs(caught.exception, failure)
        metadata.assert_called_once_with(self.root, path, True)
        launch.assert_called_once_with(context, [sys.executable, "-B", "-m",
            "src.ball_tracking.crop_candidate_identity_review", "--manifest", str(path),
            "--repository-root", str(self.root), "--worker"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
