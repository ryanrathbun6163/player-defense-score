"""Synthetic authority and supervision boundaries for the one-shot interpretation.

All files and child-process inputs are invented in temporary output trees. No
production guide, audit, resource journal, media or scientific record is opened.
"""
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

from src.ball_tracking import crop_retention_interpretation as interpretation
from src.ball_tracking import crop_retention_resources as resources


ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def binding(root, path):
    return {"path": path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def limits():
    return {"maximum_worker_memory_bytes": 8 * 1024**3,
            "maximum_total_new_output_bytes": 32 * 1024**3,
            "minimum_free_disk_bytes": 0,
            "maximum_seconds_per_unit": 1800,
            "maximum_cumulative_seconds": 14400,
            "maximum_concurrent_workers": 1}


class TemporaryRoot(unittest.TestCase):
    def setUp(self):
        parent = ROOT / "data/outputs/t/interpretation_tests"
        parent.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="i_", dir=parent)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()


class SyntheticInterpretation:
    """56 sealed historical attempts, including the three immutable failures.

The fixture deliberately has only start/finish events, not thousands of sample
events. Tests patch only its event count/tip/time, never the 56-attempt boundary.
"""
    def __init__(self, root):
        self.root = root
        self.output = root / interpretation.OUTPUT_ROOT
        self.output.mkdir(parents=True)
        self.limits = limits()
        self.journal = resources.BudgetJournal(self.output, self.limits)
        failed = sorted(interpretation.KNOWN_FAILURES)
        rows = []
        for index in range(56):
            identifier = failed[index] if index < 3 else f"{index:032x}"
            # Durability/atomic-publication behavior has its own resource tests.
            # Build immutable invented history cheaply; supervision below uses
            # the unchanged real writer and process monitor.
            with patch.object(resources.uuid, "uuid4", return_value=SimpleNamespace(hex=identifier)), \
                 patch.object(resources, "_write_new", side_effect=write_json):
                attempt, budget = self.journal.reserve("synthetic-old:" + str(index), False)
            success = index >= 3
            result = None
            if success:
                target = self.output / "attempts" / (attempt + ".result.json")
                write_json(target, {"synthetic": True, "attempt_id": attempt,
                                    "inert_scientific_pointer": {"path": "/must/not/open/deeper-report.json"}})
                result = {"path": target.relative_to(self.output).as_posix(),
                          "sha256": binding(root, target)["sha256"]}
            with patch.object(resources, "_write_new", side_effect=write_json):
                finish = self.journal.append("finished", attempt_id=attempt, elapsed_seconds=1.,
                                             success=success, worker_result=result, time_budget_seconds=budget)
            rows.append({"attempt_id": attempt, "unit_key": "synthetic-old:" + str(index),
                         "success": success, "completion_event_sha256": finish["sha256"],
                         "reservation": binding(root, self.output / "attempts" / (attempt + ".reservation.json")),
                         "completion": binding(root, self.output / "attempts" / (attempt + ".completion.json")),
                         "worker_result": binding(root, target) if success else None})
        self.history = {"schema_version": "ball_crop_candidate_retention_interpretation_frozen_history/v0.1",
                        "resource_limits": self.limits,
                        "journal_prefix": {"events": [binding(root, path) for path in sorted(self.journal.folder.glob("*.json"))],
                                           "attempts": rows, "chain_tip_sha256": self.journal.events[-1]["sha256"]},
                        "preserved_files": [], "preserved_directories": [],
                        "preserved_absent_paths": [], "sealed_holdouts_metadata_only": interpretation.HOLDOUTS}
        self.context = {"root": root, "output_root": self.output, "limits": self.limits,
                        "history": self.history, "commit": "f" * 40, "spec_sha256": "e" * 64,
                        "manifest": {}, "manifest_path": root / interpretation.MANIFEST_PATH,
                        "checkpoint": {"resource_event_count": len(self.journal.events),
                                       "cumulative_active_seconds": self.journal.consumed(),
                                       "remaining_cumulative_seconds": 14400 - self.journal.consumed()}}
        self.history["preserved_files"] = [{"path": p.relative_to(root).as_posix(), **interpretation._stat_metadata(p)}
                                            for p in self.output.rglob("*") if p.is_file()]
        self.history["preserved_directories"] = [p.relative_to(root).as_posix()
                                                  for p in self.output.rglob("*") if p.is_dir()]
        absent = ["data/outputs/ball_tracking/detections/synthetic_embargo_" + str(i) for i in range(9)]
        self.history["preserved_absent_paths"] = absent
        self.context["checkpoint"].update(preserved_absent_paths=absent,
                                           sealed_holdouts_metadata_only=interpretation.HOLDOUTS)

    def patch_scope(self):
        stack = ExitStack()
        stack.enter_context(patch.object(interpretation, "PREFIX_COUNT", len(self.history["journal_prefix"]["events"])))
        stack.enter_context(patch.object(interpretation, "PREFIX_TIP", self.history["journal_prefix"]["chain_tip_sha256"]))
        stack.enter_context(patch.object(interpretation, "USED_SECONDS", 56.))
        return stack

    def metadata_authority(self):
        """Complete fabricated authority/certificate chain; inputs stay absent."""
        source = self.root / "src/synthetic.py"
        source.parent.mkdir()
        source.write_text("# synthetic source\n", encoding="utf-8")
        requirements = self.root / "requirements.txt"
        requirements.write_text("# synthetic\n", encoding="utf-8")
        old_certificate = self.output / "audit/synthetic_old_certificate.json"
        write_json(old_certificate, {"source_bindings": [binding(self.root, source)], "helper_bindings": []})
        proposal = self.root / interpretation.PROPOSAL_PATH
        proposal.parent.mkdir(parents=True)
        proposal.write_text("Synthetic exact proposal.\n", encoding="utf-8")
        proposal_pair = binding(self.root, proposal)
        approval = self.root / interpretation.APPROVAL_PATH
        write_json(approval, {"schema_version": "ball_crop_candidate_retention_interpretation_approval/v0.1",
                              "proposal": proposal_pair, "approved_by": "ryan", "implementation_authorized": True,
                              "execution_authorized": True, "clean_commit_required": True,
                              "training_authorized": False, "git_mutations_authorized": False})
        checkpoint = {**self.context["checkpoint"], "schema_version": "publication_recovery_completion_checkpoint/v0.1",
                      "head": interpretation.PUBLICATION_COMMIT, "resource_chain_tip_sha256": self.history["journal_prefix"]["chain_tip_sha256"],
                      "completed_attempts": 56, "successful_attempts": 53,
                      "preserved_failed_attempts": sorted(interpretation.KNOWN_FAILURES), "active_workers": 0,
                      "independent_completion_audit_passed": True, "supervised_review_guide_completed": True,
                      "resource_limits": self.limits, "implementation_validation": binding(self.root, old_certificate)}
        completion_path = self.root / interpretation.COMPLETION_PATH
        write_json(completion_path, checkpoint)
        checkpoint_pair = binding(self.root, completion_path)
        human_path = self.root / interpretation.HUMAN_REVIEW_PATH
        write_json(human_path, {"schema_version": "ball_crop_candidate_retention_visual_review_record/v0.1",
                               "human_visual_review": {"status": "completed_and_approved", "requested_scope_completed": True},
                               "bound_evidence": {"completion_checkpoint": checkpoint_pair}})
        self.history["completion_checkpoint"] = checkpoint_pair
        self.history["preserved_absent_paths"] = [*checkpoint["preserved_absent_paths"],
            interpretation.OUTPUT_ROOT + "/supervisor.lock", interpretation.OUTPUT_ROOT + "/" + interpretation.OUTPUT_DIR]
        history_path = self.root / interpretation.FROZEN_HISTORY_PATH
        write_json(history_path, self.history)
        authority = {"proposal": proposal_pair, "authorization": binding(self.root, approval),
                     "completion_checkpoint": checkpoint_pair, "human_review_record": binding(self.root, human_path),
                     "frozen_history": binding(self.root, history_path)}
        certificate = self.root / "data/outputs/ball_tracking/crop_candidate_retention_interpretation_implementation/synthetic/certificate.json"
        write_json(certificate, {"schema_version": "ball_crop_candidate_retention_interpretation_implementation_validation/v0.1",
                                 **{k: True for k in ("focused_tests_passed", "full_suite_passed", "independent_static_review_passed", "integrity_tests_passed")},
                                 "authority_sha256": {k: v["sha256"] for k, v in authority.items()},
                                 "source_bindings": [binding(self.root, source), binding(self.root, requirements)], "evidence_bindings": []})
        manifest = {"schema_version": "ball_crop_candidate_retention_interpretation/v0.1", "interpretation_id": interpretation.ID,
                    **authority, "scientific_inputs": interpretation.SCIENTIFIC_INPUTS,
                    "implementation_validation": binding(self.root, certificate), "output_root": interpretation.OUTPUT_ROOT,
                    "permitted_stages": ["interpret"], "unit_key": interpretation.UNIT_KEY,
                    "maximum_unit_seconds": 1800, "maximum_summary_bytes": 65536,
                    "selected_method": None, "selected_operating_point": None, "quality_gate": None}
        write_json(self.context["manifest_path"], manifest)
        stack = self.patch_scope()
        for constant, key in (("PROPOSAL_SHA", "proposal"), ("APPROVAL_SHA", "authorization"),
                              ("COMPLETION_SHA", "completion_checkpoint"), ("HUMAN_REVIEW_SHA", "human_review_record"),
                              ("FROZEN_HISTORY_SHA", "frozen_history")):
            stack.enter_context(patch.object(interpretation, constant, authority[key]["sha256"]))
        stack.enter_context(patch.object(interpretation.original, "_clean_checkpoint", return_value=self.context["commit"]))
        stack.enter_context(patch.object(interpretation.original, "_git", return_value="tracked"))
        stack.enter_context(patch.object(interpretation.subprocess, "run", return_value=SimpleNamespace(returncode=0)))
        return manifest, stack

    def start(self, *, key=None, selection=False, seconds=1800):
        aid = "d" * 32
        event = self.journal.append("started", attempt_id=aid, unit_key=key or interpretation.UNIT_KEY,
                                    selection_unit=selection, reserved_seconds=seconds)
        resources._write_new(self.output / "attempts" / (aid + ".reservation.json"), {"event_sha256": event["sha256"]})
        return aid

    def finish(self, aid, **changes):
        target = self.output / "attempts" / (aid + ".result.json")
        if not target.exists():
            write_json(target, {"synthetic": True})
        self.journal.append("sample", attempt_id=aid, elapsed_seconds=1., memory_bytes=1024,
                            output_bytes=2048, free_disk_bytes=1024**3)
        fields = {"attempt_id": aid, "elapsed_seconds": 2., "success": True, "exit_code": 0,
                  "failure": None, "final_accounting_error": None,
                  "worker_result": {"path": "attempts/" + aid + ".result.json", "sha256": binding(self.root, target)["sha256"]},
                  "time_budget_seconds": 1800, "time_overshoot_seconds": 0, "memory_overshoot_bytes": 0,
                  "output_overshoot_bytes": 0, "maximum_monitor_interval_seconds": .3, "monitor_samples": 1,
                  "peak_worker_memory_bytes": 1024, "maximum_output_bytes": 2048,
                  "final_accounting_output_bound_bytes": 4096, "minimum_free_disk_bytes": 1024**3}
        fields.update(changes)
        return self.journal.append("finished", **fields)


class PrimitiveBoundaryTests(TemporaryRoot):
    def test_create_only_writer_does_not_replace_existing_bytes(self):
        target = self.root / "summary.md"
        target.write_bytes(b"earlier partial must remain")
        with self.assertRaises(FileExistsError):
            interpretation._write_new(target, b"replacement")
        self.assertEqual(target.read_bytes(), b"earlier partial must remain")

    def test_source_certificate_requires_every_source_and_all_validation_gates(self):
        source = self.root / "src/example.py"
        source.parent.mkdir()
        source.write_text("# invented source\n", encoding="utf-8")
        requirements = self.root / "requirements.txt"
        requirements.write_text("# invented dependencies\n", encoding="utf-8")
        certificate_path = self.root / "data/outputs/ball_tracking/crop_candidate_retention_interpretation_implementation/synthetic/certificate.json"
        authority = {key: {"sha256": str(index) * 64} for index, key in enumerate(interpretation.AUTHORITY_FIELDS)}
        certificate = {"schema_version": "ball_crop_candidate_retention_interpretation_implementation_validation/v0.1",
                       **{key: True for key in ("focused_tests_passed", "full_suite_passed", "independent_static_review_passed", "integrity_tests_passed")},
                       "authority_sha256": {key: value["sha256"] for key, value in authority.items()},
                       "source_bindings": [binding(self.root, source), binding(self.root, requirements)],
                       "evidence_bindings": []}
        def check(value):
            write_json(certificate_path, value)
            manifest = {**authority, "implementation_validation": binding(self.root, certificate_path)}
            with patch.object(interpretation.original, "_git", return_value="tracked"):
                return interpretation._validate_implementation(self.root, manifest)
        self.assertEqual(check(certificate), certificate)
        for flag in ("focused_tests_passed", "full_suite_passed", "independent_static_review_passed", "integrity_tests_passed"):
            wrong = {**certificate, flag: False}
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                check(wrong)
        wrong = {**certificate, "source_bindings": certificate["source_bindings"][:1]}
        with self.assertRaisesRegex(ValueError, "dependencies"):
            check(wrong)
        source.write_text("# changed after validation\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            check(certificate)

    def test_sealed_holdouts_and_all_nine_embargoes_remain_absent(self):
        paths = ["data/outputs/ball_tracking/detections/embargo_" + str(i) for i in range(9)]
        checkpoint = {"sealed_holdouts_metadata_only": copy.deepcopy(interpretation.HOLDOUTS),
                      "preserved_absent_paths": paths}
        interpretation._protected_metadata(self.root, checkpoint)
        wrong = copy.deepcopy(checkpoint)
        wrong["sealed_holdouts_metadata_only"][0][1] += 1
        with self.assertRaises(ValueError):
            interpretation._protected_metadata(self.root, wrong)
        target = self.root / paths[-1]
        target.parent.mkdir(parents=True)
        target.write_bytes(b"forbidden")
        with self.assertRaises(ValueError):
            interpretation._protected_metadata(self.root, checkpoint)


class HistoryBoundaryTests(TemporaryRoot):
    def test_frozen_fifty_six_attempts_are_verified_without_following_science_pointers(self):
        fixture = SyntheticInterpretation(self.root)
        # An inert pointer in historical result metadata must never be followed.
        with fixture.patch_scope():
            journal = interpretation.verify_history(self.root, fixture.context)
        self.assertEqual(len(journal._attempts()), 56)
        self.assertEqual(journal.consumed(), 56.)

    def test_missing_old_seal_and_new_failed_result_are_rejected(self):
        fixture = SyntheticInterpretation(self.root)
        failed = fixture.history["journal_prefix"]["attempts"][0]
        seal = self.root / failed["completion"]["path"]
        saved = seal.read_bytes()
        seal.unlink()
        with fixture.patch_scope(), self.assertRaises((ValueError, FileNotFoundError)):
            interpretation.verify_history(self.root, fixture.context)
        seal.write_bytes(saved)
        write_json(fixture.output / "attempts" / (failed["attempt_id"] + ".result.json"), {"adopted": True})
        with fixture.patch_scope(), self.assertRaisesRegex(ValueError, "already exists"):
            interpretation.verify_history(self.root, fixture.context)

    def test_changed_frozen_result_and_event_binding_are_rejected(self):
        fixture = SyntheticInterpretation(self.root)
        row = fixture.history["journal_prefix"]["attempts"][-1]
        path = self.root / row["worker_result"]["path"]
        saved = path.read_bytes()
        path.write_bytes(b"changed receipt")
        with fixture.patch_scope(), self.assertRaises(ValueError):
            interpretation.verify_history(self.root, fixture.context)
        path.write_bytes(saved)
        fixture.history["journal_prefix"]["events"][0]["sha256"] = "0" * 64
        with fixture.patch_scope(), self.assertRaises(ValueError):
            interpretation.verify_history(self.root, fixture.context)

    def test_only_the_current_owned_active_reservation_is_allowed(self):
        fixture = SyntheticInterpretation(self.root)
        aid = fixture.start()
        with fixture.patch_scope(), patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": aid}):
            interpretation.verify_history(self.root, fixture.context, "worker")
            with self.assertRaisesRegex(ValueError, "no retry"):
                interpretation.verify_history(self.root, fixture.context, "before")
            with patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": "a" * 32}), self.assertRaises(ValueError):
                interpretation.verify_history(self.root, fixture.context, "worker")

    def test_other_role_selection_label_and_overlarge_reservation_are_rejected(self):
        for index, changes in enumerate(({"key": "publication-recovery:preflight:"}, {"selection": True}, {"seconds": 1801})):
            with self.subTest(changes=changes):
                fixture = SyntheticInterpretation(self.root / str(index))
                aid = fixture.start(**changes)
                with fixture.patch_scope(), patch.dict(os.environ, {"BALL_RETENTION_ATTEMPT_ID": aid}), self.assertRaises(ValueError):
                    interpretation.verify_history(fixture.root, fixture.context, "worker")

    def test_success_is_closed_once_and_cannot_be_reused(self):
        fixture = SyntheticInterpretation(self.root)
        aid = fixture.start()
        fixture.finish(aid)
        with fixture.patch_scope():
            interpretation.verify_history(self.root, fixture.context, "completed")
            for phase in ("before", "worker"):
                with self.subTest(phase=phase), self.assertRaises(ValueError):
                    interpretation.verify_history(self.root, fixture.context, phase)

    def test_failed_or_incomplete_suffix_never_counts_as_completion(self):
        fixture = SyntheticInterpretation(self.root)
        aid = fixture.start()
        with fixture.patch_scope(), self.assertRaisesRegex(ValueError, "Incomplete"):
            interpretation.verify_history(self.root, fixture.context, "completed")
        fixture.finish(aid, success=False, failure="synthetic failure")
        with fixture.patch_scope(), self.assertRaisesRegex(ValueError, "no retry"):
            interpretation.verify_history(self.root, fixture.context, "completed")

    def test_completion_resource_and_receipt_boundaries(self):
        variants = ({"time_budget_seconds": 1801}, {"elapsed_seconds": 1800.01},
                    {"maximum_monitor_interval_seconds": 1.01}, {"monitor_samples": 0},
                    {"memory_overshoot_bytes": 1}, {"final_accounting_error": "incomplete"},
                    {"maximum_output_bytes": 4097},
                    {"worker_result": {"path": "attempts/someone-else.result.json", "sha256": "0" * 64}})
        for index, changes in enumerate(variants):
            with self.subTest(changes=changes):
                fixture = SyntheticInterpretation(self.root / str(index))
                aid = fixture.start()
                fixture.finish(aid, **changes)
                with fixture.patch_scope(), self.assertRaises(ValueError):
                    interpretation.verify_history(fixture.root, fixture.context, "completed")

    def test_recorded_samples_cannot_exceed_limits_or_be_hidden_by_final_counters(self):
        variants = ({"memory_bytes": 8 * 1024**3 + 1}, {"output_bytes": 32 * 1024**3 + 1},
                    {"free_disk_bytes": -1}, {"memory_bytes": float("inf")},
                    {"memory_bytes": 2048}, {"output_bytes": 3000}, {"free_disk_bytes": 1})
        for index, changes in enumerate(variants):
            with self.subTest(changes=changes):
                fixture = SyntheticInterpretation(self.root / str(index))
                aid = fixture.start()
                if changes.get("memory_bytes") == float("inf"):
                    # The journal itself rejects nonfinite JSON at publication.
                    with self.assertRaises(ValueError):
                        fixture.journal.append("sample", attempt_id=aid, elapsed_seconds=.5,
                            memory_bytes=float("inf"), output_bytes=1, free_disk_bytes=1024**3)
                    continue
                fields = {"memory_bytes": 1024, "output_bytes": 2048, "free_disk_bytes": 1024**3, **changes}
                fixture.journal.append("sample", attempt_id=aid, elapsed_seconds=.5, **fields)
                fixture.finish(aid, monitor_samples=2)
                with fixture.patch_scope(), self.assertRaises(ValueError):
                    interpretation.verify_history(fixture.root, fixture.context, "completed")

    def test_completed_inventory_rejects_unpublished_resource_event_leftover(self):
        fixture = SyntheticInterpretation(self.root)
        aid = fixture.start()
        fixture.finish(aid)
        fixture.context["completed_attempt_id"] = aid
        target = fixture.output / "resource_events" / (f".pending_{len(fixture.journal.events):08d}.json_" + "c" * 32)
        target.write_text("{}", encoding="utf-8")
        with fixture.patch_scope(), self.assertRaisesRegex(ValueError, "Unexpected new evidence file"):
            interpretation._preserved_metadata(self.root, fixture.context, "completed", allow_outputs=True)

    def test_preservation_uses_metadata_and_rejects_unknown_output_or_existing_destination(self):
        fixture = SyntheticInterpretation(self.root)
        with fixture.patch_scope(), patch.object(Path, "read_bytes", side_effect=AssertionError("scientific read")):
            interpretation._preserved_metadata(self.root, fixture.context)
        extra = fixture.output / "unexpected.txt"
        extra.write_bytes(b"invented")
        with fixture.patch_scope(), self.assertRaisesRegex(ValueError, "Unexpected new evidence file"):
            interpretation._preserved_metadata(self.root, fixture.context)
        extra.unlink()
        target = fixture.output / interpretation.OUTPUT_DIR
        target.mkdir(parents=True)
        with fixture.patch_scope(), self.assertRaisesRegex(ValueError, "already exists"):
            interpretation._preserved_metadata(self.root, fixture.context)


class SupervisionBoundaryTests(TemporaryRoot):
    def test_actual_child_uses_1800_false_selection_reservation_and_restores_original_journal(self):
        fixture = SyntheticInterpretation(self.root)
        (fixture.output / "audit").mkdir()
        fixture.history["preserved_directories"].append(interpretation.OUTPUT_ROOT + "/audit")
        seed = {"root": str(self.root), "output": str(fixture.output), "outputs": interpretation.OUTPUTS,
                "unit_key": interpretation.UNIT_KEY, "commit": fixture.context["commit"],
                "spec_sha256": fixture.context["spec_sha256"], "scientific_inputs": interpretation.SCIENTIFIC_INPUTS,
                "checks": interpretation.CHECKS}
        # This child generates only three invented tiny files and a result
        # envelope. It never imports or invokes the scientific worker.
        program = "seed = " + repr(seed) + "\n" + '''
import hashlib, json, os, time
from pathlib import Path
gate = Path(os.environ['BALL_RETENTION_START_GATE'])
while not gate.is_file():
    time.sleep(.01)
root, output = Path(seed['root']), Path(seed['output'])
text = 'Bounded synthetic interpretation; no scientific inputs were read.'
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
result = {'schema_version': 'ball_crop_candidate_retention_interpretation_worker_result/v0.1',
          'stage': 'interpret', 'unit_key': seed['unit_key'], 'attempt_id': os.environ['BALL_RETENTION_ATTEMPT_ID'],
          'commit': seed['commit'], 'spec_sha256': seed['spec_sha256'], 'artifacts': artifacts,
          'artifact_metadata': metadata, 'scientific_inputs': seed['scientific_inputs'], 'checks': seed['checks'],
          'summary_payload': {'text': text, 'size_bytes': len(text.encode()), 'sha256': hashlib.sha256(text.encode()).hexdigest()}}
with Path(os.environ['BALL_RETENTION_RESULT_PATH']).open('x', encoding='utf-8') as stream:
    json.dump(result, stream)
'''
        original_class = resources.BudgetJournal
        with fixture.patch_scope():
            event = interpretation._run_bounded_supervised(fixture.context, [sys.executable, "-B", "-c", program])
            journal = interpretation.verify_history(self.root, fixture.context, "completed")
            result = interpretation._completed_result(self.root, fixture.context, event)
        self.assertIs(resources.BudgetJournal, original_class)
        start = journal._attempts()[event["attempt_id"]]["start"]
        self.assertIs(start["selection_unit"], False)
        self.assertEqual(start["reserved_seconds"], 1800)
        self.assertEqual(event["time_budget_seconds"], 1800)
        self.assertEqual(start["limits_sha256"], resources._digest(fixture.limits))
        self.assertTrue(event["success"])
        self.assertGreater(event["monitor_samples"], 0)
        self.assertLessEqual(event["maximum_monitor_interval_seconds"], 1)
        self.assertLess(journal.consumed(), 56 + 1800)
        self.assertEqual(result["summary"], "Bounded synthetic interpretation; no scientific inputs were read.")
        self.assertEqual(result["successful_workers"], 1)

    def test_actual_failed_child_stops_without_retry_and_restores_journal(self):
        fixture = SyntheticInterpretation(self.root)
        original_class = resources.BudgetJournal
        with fixture.patch_scope():
            with self.assertRaises(resources.ResourceLimitError):
                interpretation._run_bounded_supervised(fixture.context, [sys.executable, "-B", "-c", "raise SystemExit(7)"])
            self.assertIs(resources.BudgetJournal, original_class)
            journal = resources.BudgetJournal(fixture.output, fixture.limits)
            self.assertEqual(len(journal._attempts()), 57)
            self.assertFalse(journal.events[-1]["success"])
            with self.assertRaises(ValueError):
                interpretation._run_bounded_supervised(fixture.context, [sys.executable, "-B", "-c", "raise AssertionError('must not launch')"])
        self.assertIs(resources.BudgetJournal, original_class)
        self.assertEqual(len(resources.BudgetJournal(fixture.output, fixture.limits)._attempts()), 57)

    def test_scoped_adapter_refuses_other_roles_selection_or_repeated_reservation(self):
        fixture = SyntheticInterpretation(self.root)
        with fixture.patch_scope():
            journal = interpretation._InterpretationJournal(fixture.output, fixture.limits)
            for role, selection in (("select:forbidden", False), (interpretation.UNIT_KEY, True)):
                with self.subTest(role=role, selection=selection), self.assertRaises(ValueError):
                    journal.reserve(role, selection)
            aid, seconds = journal.reserve(interpretation.UNIT_KEY, False)
            self.assertEqual(seconds, 1800)
            self.assertEqual(journal.consumed(), 56 + 1800)
            with self.assertRaises(ValueError):
                journal.reserve(interpretation.UNIT_KEY, False)
            self.assertTrue((fixture.output / "attempts" / (aid + ".reservation.json")).exists())

    def test_adapter_uses_smaller_remaining_original_budget(self):
        # A separate small invented experiment has only 900 seconds left. The
        # real unchanged monitor/limit digest still governs the reservation.
        output = self.root / interpretation.OUTPUT_ROOT
        contract = {**limits(), "maximum_cumulative_seconds": 1000}
        journal = resources.BudgetJournal(output, contract)
        aid, _ = journal.reserve("synthetic-old", False)
        journal.append("finished", attempt_id=aid, elapsed_seconds=100., success=True, worker_result=None)
        with patch.object(interpretation, "PREFIX_COUNT", 2), patch.object(interpretation, "PREFIX_ATTEMPTS", 1), \
             patch.object(interpretation, "PREFIX_TIP", journal.events[-1]["sha256"]), patch.object(interpretation, "USED_SECONDS", 100.):
            scoped = interpretation._InterpretationJournal(output, contract)
            _, seconds = scoped.reserve(interpretation.UNIT_KEY, False)
        self.assertEqual(seconds, 900)


class DispatchBoundaryTests(TemporaryRoot):
    def test_complete_metadata_chain_checks_source_authority_and_exact_two_inputs_without_science(self):
        fixture = SyntheticInterpretation(self.root)
        manifest, authority_scope = fixture.metadata_authority()
        with authority_scope, patch.object(interpretation, "_read_scientific_inputs", side_effect=AssertionError("metadata scientific read")):
            context = interpretation._metadata(self.root, fixture.context["manifest_path"], True)
            self.assertEqual(context["manifest"], manifest)
            for row in manifest["scientific_inputs"].values():
                self.assertFalse((self.root / row["path"]).exists())
            for change in ({"scientific_inputs": {**manifest["scientific_inputs"], "deeper_report": {"path": "forbidden"}}},
                           {"selected_method": "winner"}, {"maximum_unit_seconds": 1801},
                           {"permitted_stages": ["interpret", "preflight"]},
                           {"proposal": {**manifest["proposal"], "sha256": "0" * 64}}):
                write_json(fixture.context["manifest_path"], {**manifest, **change})
                with self.subTest(change=change), self.assertRaises(ValueError):
                    interpretation._metadata(self.root, fixture.context["manifest_path"], True)
            write_json(fixture.context["manifest_path"], manifest)
            (self.root / "src/synthetic.py").write_text("# changed certified bytes\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                interpretation._metadata(self.root, fixture.context["manifest_path"], True)

    def test_dirty_checkout_stops_before_manifest_or_scientific_input_read(self):
        with patch.object(interpretation.original, "_clean_checkpoint", side_effect=ValueError("dirty checkout")), \
             patch.object(interpretation, "read_json", side_effect=AssertionError("must stop before reads")), \
             self.assertRaisesRegex(ValueError, "dirty checkout"):
            interpretation._metadata(self.root, self.root / interpretation.MANIFEST_PATH, True)

    def test_dry_run_and_parent_guards_never_read_science_or_launch_extra_preflight(self):
        context = {"spec_sha256": "synthetic", "commit": "synthetic", "root": self.root,
                   "manifest_path": self.root / interpretation.MANIFEST_PATH}
        with patch.object(interpretation, "_metadata", return_value=context), \
             patch.object(interpretation, "verify_history") as history, \
             patch.object(interpretation, "_preserved_metadata"), \
             patch.object(interpretation, "_read_scientific_inputs", side_effect=AssertionError("parent science read")), \
             patch.object(interpretation, "_run_bounded_supervised", side_effect=AssertionError("dry run worker")):
            self.assertTrue(interpretation.run_interpretation(self.root, context["manifest_path"], dry_run=True)["metadata_only"])
            self.assertEqual(history.call_args.args[-1], "before")

    def test_failure_prevents_summary_transport_and_parent_dispatches_exactly_one_unit(self):
        context = {"spec_sha256": "synthetic", "commit": "synthetic", "root": self.root,
                   "manifest_path": self.root / interpretation.MANIFEST_PATH}
        with patch.object(interpretation, "_metadata", return_value=context), \
             patch.object(interpretation, "verify_history"), patch.object(interpretation, "_preserved_metadata"), \
             patch.object(interpretation, "_run_bounded_supervised", side_effect=resources.ResourceLimitError("stop")) as run, \
             patch.object(interpretation, "_completed_result", side_effect=AssertionError("released failed summary")):
            with self.assertRaises(resources.ResourceLimitError):
                interpretation.run_interpretation(self.root, context["manifest_path"])
            self.assertEqual(run.call_count, 1)
            command = run.call_args.args[1]
            self.assertIn("src.ball_tracking.crop_retention_interpretation", command)
            self.assertIn("--worker", command)
            self.assertNotIn("--stage", command)

    def test_old_roles_are_not_cli_dispatchable(self):
        for stage in ("preflight", "select", "score", "render", "verify", "accept", "completion-audit", "presentation"):
            with self.subTest(stage=stage), patch.object(interpretation, "_metadata", side_effect=AssertionError("old role read")), \
                 patch("sys.stderr"), self.assertRaises(SystemExit):
                interpretation.main(["--manifest", "unused", "--stage", stage])


class WorkerAndTransportTests(TemporaryRoot):
    def fixture(self):
        from test_ball_crop_retention_interpretation_summary import fabricated_audit, fabricated_guide, seal
        fixture = SyntheticInterpretation(self.root)
        aid = fixture.start()
        audit = fabricated_audit()
        audit["execution_code_commit"] = interpretation.PUBLICATION_COMMIT
        seal(audit)
        inputs = {"guide": fabricated_guide(audit).encode(), "audit": json.dumps(audit).encode()}
        scientific = {}
        for key, payload in inputs.items():
            path = fixture.output / "audit" / ("synthetic_guide.md" if key == "guide" else "synthetic_audit.json")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            scientific[key] = {**binding(self.root, path), "size_bytes": len(payload)}
        certificate = self.root / "synthetic_certificate.json"
        write_json(certificate, {"source_bindings": []})
        fixture.context["manifest"] = {
            **{key: {"path": "synthetic_authority/" + key, "sha256": "a" * 64} for key in interpretation.AUTHORITY_FIELDS},
            "scientific_inputs": scientific, "implementation_validation": binding(self.root, certificate)}
        environment = {"BALL_RETENTION_ATTEMPT_ID": aid,
                       "BALL_RETENTION_RESULT_PATH": str(fixture.output / "attempts" / (aid + ".result.json"))}
        return fixture, aid, scientific, environment

    def worker_scope(self, fixture, scientific, environment):
        stack = fixture.patch_scope()
        stack.enter_context(patch.dict(os.environ, environment))
        stack.enter_context(patch.object(interpretation, "SCIENTIFIC_INPUTS", scientific))
        stack.enter_context(patch.object(interpretation, "wait_for_supervisor"))
        stack.enter_context(patch.object(interpretation, "_metadata", return_value=fixture.context))
        stack.enter_context(patch.object(interpretation, "_preserved_metadata"))
        return stack

    def test_worker_creates_exact_three_outputs_and_provenance_without_claiming_completion(self):
        fixture, aid, scientific, environment = self.fixture()
        original_open = Path.open
        reads = []
        allowed = {self.root / row["path"] for row in scientific.values()}
        def observe(path, *args, **kwargs):
            if path in allowed and args and args[0] == "rb":
                reads.append(path)
            return original_open(path, *args, **kwargs)
        with self.worker_scope(fixture, scientific, environment), patch.object(Path, "open", observe):
            result = interpretation._worker(self.root, fixture.context["manifest_path"])
        self.assertTrue(result["completion_pending"])
        self.assertEqual(len(reads), 4)
        self.assertEqual(set(reads), allowed)
        destination = fixture.output / interpretation.OUTPUT_DIR
        self.assertEqual({p.name for p in destination.iterdir()}, {"summary.json", "summary.md", "provenance.json"})
        provenance = json.loads((destination / "provenance.json").read_text())
        self.assertEqual(provenance["attempt_id"], aid)
        self.assertEqual(provenance["scientific_inputs"], scientific)
        self.assertEqual(provenance["authority_bindings"], {k: fixture.context["manifest"][k] for k in interpretation.AUTHORITY_FIELDS})
        self.assertNotIn("content_sha256", provenance)
        self.assertNotIn("successful_completion", provenance)
        self.assertIn("subsequent successful supervisor", provenance["acceptance"])
        receipt = json.loads(Path(environment["BALL_RETENTION_RESULT_PATH"]).read_text())
        self.assertEqual(len(receipt["artifacts"]), 3)
        self.assertEqual(receipt["summary_payload"]["text"].encode(), (destination / "summary.md").read_bytes())

    def test_wrong_active_owner_or_existing_output_stops_before_scientific_read(self):
        fixture, aid, scientific, environment = self.fixture()
        with self.worker_scope(fixture, scientific, {**environment, "BALL_RETENTION_ATTEMPT_ID": "b" * 32}), \
             patch.object(interpretation, "_read_scientific_inputs", side_effect=AssertionError("premature science read")), \
             self.assertRaisesRegex(ValueError, "does not own"):
            interpretation._worker(self.root, fixture.context["manifest_path"])
        destination = fixture.output / interpretation.OUTPUT_DIR
        destination.mkdir()
        (destination / "summary.md").write_text("earlier partial", encoding="utf-8")
        with self.worker_scope(fixture, scientific, environment), \
             patch.object(interpretation, "_preserved_metadata", side_effect=ValueError("existing output")), \
             patch.object(interpretation, "_read_scientific_inputs", side_effect=AssertionError("premature science read")), \
             self.assertRaisesRegex(ValueError, "existing output"):
            interpretation._worker(self.root, fixture.context["manifest_path"])
        self.assertEqual((destination / "summary.md").read_text(), "earlier partial")

    def test_bad_input_digest_and_changed_end_authority_prevent_receipt(self):
        fixture, aid, scientific, environment = self.fixture()
        guide = self.root / scientific["guide"]["path"]
        original = guide.read_bytes()
        guide.write_bytes(original.replace(b"Synthetic", b"Tampered!", 1))
        with self.worker_scope(fixture, scientific, environment), self.assertRaises(ValueError):
            interpretation._worker(self.root, fixture.context["manifest_path"])
        self.assertFalse(Path(environment["BALL_RETENTION_RESULT_PATH"]).exists())
        self.assertFalse((fixture.output / interpretation.OUTPUT_DIR).exists())
        guide.write_bytes(original)
        changed = {**fixture.context, "commit": "changed"}
        with self.worker_scope(fixture, scientific, environment), \
             patch.object(interpretation, "_metadata", side_effect=[fixture.context, changed]), \
             self.assertRaisesRegex(ValueError, "changed during"):
            interpretation._worker(self.root, fixture.context["manifest_path"])
        self.assertFalse(Path(environment["BALL_RETENTION_RESULT_PATH"]).exists())
        self.assertEqual(len(list((fixture.output / interpretation.OUTPUT_DIR).iterdir())), 3)

    def test_changed_input_at_end_prevents_receipt_and_preserves_partial_outputs(self):
        fixture, aid, scientific, environment = self.fixture()
        from src.ball_tracking import crop_retention_interpretation_summary as builder
        real_build = builder.build_summary
        def change_input(guide, audit):
            result = real_build(guide, audit)
            target = self.root / scientific["guide"]["path"]
            target.write_bytes(target.read_bytes() + b"changed after summary")
            return result
        with self.worker_scope(fixture, scientific, environment), patch.object(builder, "build_summary", side_effect=change_input), \
             self.assertRaises(ValueError):
            interpretation._worker(self.root, fixture.context["manifest_path"])
        self.assertFalse(Path(environment["BALL_RETENTION_RESULT_PATH"]).exists())
        self.assertTrue((fixture.output / interpretation.OUTPUT_DIR / "provenance.json").exists())

    def final_output_mutation(self, name):
        fixture, aid, scientific, environment = self.fixture()
        count = 0
        def end_metadata(*args):
            nonlocal count
            count += 1
            if count == 2:
                target = fixture.output / interpretation.OUTPUT_DIR / name
                target.write_bytes(b'{"tampered_after_initial_integrity_check":true}')
            return fixture.context
        with self.worker_scope(fixture, scientific, environment), \
             patch.object(interpretation, "_metadata", side_effect=end_metadata), self.assertRaises(ValueError):
            interpretation._worker(self.root, fixture.context["manifest_path"])
        self.assertFalse(Path(environment["BALL_RETENTION_RESULT_PATH"]).exists())

    def test_final_summary_json_mutation_cannot_gain_receipt(self):
        self.final_output_mutation("summary.json")

    def test_final_provenance_mutation_cannot_gain_receipt(self):
        self.final_output_mutation("provenance.json")

    def test_summary_over_limit_or_selected_method_fails_without_output(self):
        fixture, aid, scientific, environment = self.fixture()
        from src.ball_tracking import crop_retention_interpretation_summary as builder
        value = {"schema_version": "ball_crop_retention_post_review_interpretation_summary/v0.1",
                 "source_map": [{"synthetic": True}], "selected_method": None,
                 "selected_operating_point": None, "quality_gate": None}
        for candidate, text in (({**value, "selected_method": "winner"}, "synthetic"), (value, "é" * 32769)):
            with self.subTest(selected=candidate["selected_method"]), self.worker_scope(fixture, scientific, environment), \
                 patch.object(builder, "build_summary", return_value=(candidate, text)), self.assertRaises(ValueError):
                interpretation._worker(self.root, fixture.context["manifest_path"])
            self.assertFalse((fixture.output / interpretation.OUTPUT_DIR).exists())
            self.assertFalse(Path(environment["BALL_RETENTION_RESULT_PATH"]).exists())

    def test_parent_releases_only_bound_success_text_without_opening_scientific_outputs(self):
        fixture, aid, scientific, environment = self.fixture()
        with self.worker_scope(fixture, scientific, environment):
            interpretation._worker(self.root, fixture.context["manifest_path"])
        event = fixture.finish(aid)
        protected = {self.root / row["path"] for row in scientific.values()} | {
            fixture.output / name for name in interpretation.OUTPUTS}
        original_open = Path.open
        def forbid(path, *args, **kwargs):
            if path in protected:
                raise AssertionError("parent opened scientific input/output")
            return original_open(path, *args, **kwargs)
        with fixture.patch_scope(), patch.object(interpretation, "SCIENTIFIC_INPUTS", scientific), \
             patch.object(interpretation, "_preserved_metadata"), patch.object(Path, "open", forbid):
            result = interpretation._completed_result(self.root, fixture.context, event)
        self.assertIn("Representative pool", result["summary"])
        self.assertEqual(result["successful_workers"], 1)
        self.assertIsNone(result["selected_method"])
        self.assertFalse(result["scoring_executed"])
        self.assertFalse(result["media_decoded"])

    def test_output_tamper_after_worker_success_prevents_parent_release(self):
        fixture, aid, scientific, environment = self.fixture()
        with self.worker_scope(fixture, scientific, environment):
            interpretation._worker(self.root, fixture.context["manifest_path"])
        event = fixture.finish(aid)
        (fixture.output / interpretation.OUTPUT_DIR / "summary.md").write_bytes(b"changed after success")
        with fixture.patch_scope(), patch.object(interpretation, "SCIENTIFIC_INPUTS", scientific), \
             patch.object(interpretation, "_preserved_metadata"), self.assertRaisesRegex(ValueError, "metadata changed"):
            interpretation._completed_result(self.root, fixture.context, event)

    def test_even_successful_result_cannot_transport_text_unbound_to_readable_artifact(self):
        fixture, aid, scientific, environment = self.fixture()
        with self.worker_scope(fixture, scientific, environment):
            interpretation._worker(self.root, fixture.context["manifest_path"])
        receipt_path = Path(environment["BALL_RETENTION_RESULT_PATH"])
        receipt = json.loads(receipt_path.read_text())
        text = "Unreceipted replacement summary"
        receipt["summary_payload"] = {"text": text, "size_bytes": len(text.encode()), "sha256": hashlib.sha256(text.encode()).hexdigest()}
        write_json(receipt_path, receipt)
        event = fixture.finish(aid)
        with fixture.patch_scope(), patch.object(interpretation, "SCIENTIFIC_INPUTS", scientific), \
             patch.object(interpretation, "_preserved_metadata"), self.assertRaisesRegex(ValueError, "not the receipted"):
            interpretation._completed_result(self.root, fixture.context, event)


if __name__ == "__main__":
    unittest.main()
