"""Fabricated render-only recovery evidence; never open real saved outputs."""
import copy
from contextlib import ExitStack
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from src.ball_tracking import crop_retention_experiment as original
from src.ball_tracking import crop_retention_evaluation as scoring
from src.ball_tracking import crop_retention_render_recovery as recovery
from src.ball_tracking import crop_retention_review as review
from src.ball_tracking import crop_retention_resources as resources
from src.ball_tracking.development_experiments import canonical_sha256, read_json, sha256_file
from test_ball_crop_retention_recovery import SyntheticRecovery, binding, write_json, empty_window
from test_ball_crop_retention_review import context_fixture, fast_frame


ROOT = Path(__file__).resolve().parents[1]
SELECTION_COMMIT = "0a7f5bc69be948b8c4e2c630c84c4ccdefb5dc41"
SELECTION_SPEC = "e481d645e946f285c655d721563172c4cb8c2f124214840b8c8d8ae5cfb752fd"
SCORING_COMMIT = "f36237247191e726ad7e81bdc6651f9340a9063d"
SCORING_SPEC = "4b1f9f3c75ee53eb1358bcb49981118269694ec39adb5a312ae325f8ee273bbf"
RENDER_COMMIT = "a" * 40
RENDER_SPEC = "b" * 64


class TemporaryRoot(unittest.TestCase):
    def setUp(self):
        parent = ROOT / "data/outputs/t/render_tests"
        parent.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="r_", dir=parent)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()


def forbid_scientific_work(stack):
    """Reading saved observations/reports is permitted; deriving them is not."""
    for module, name in ((original, "iter_ranked_frames"), (original, "write_selection"),
                         (scoring, "score_window"), (scoring, "evaluate_unit"),
                         (scoring, "evaluate_detections"), (scoring, "finalize")):
        stack.enter_context(patch.object(module, name,
                            side_effect=AssertionError("Scientific work forbidden: " + name)))


class SyntheticRenderRecovery(SyntheticRecovery):
    """Compact, real hash-chain with 41 attempts and two preserved failures."""

    def __init__(self, root):
        def short_window(root, number):
            window, run, output = empty_window(root, number)
            window["window_id"] = "w" + str(number)
            return window, run, output
        # Keep fabricated Windows trace paths below MAX_PATH without relaxing
        # any real output-root or 24-unit/600-trace check.
        with patch("test_ball_crop_retention_recovery.empty_window", side_effect=short_window):
            super().__init__(root)
        self.proposal["pool_separation"] = ["representative_evaluation", "challenge_evaluation"]
        self.proposal["proposed_output_root"] = original.OUTPUT_ROOT
        self.add_attempt("preparation:recovery", "preparation", stage="preparation", key="recovery")
        self.inventory["journal_prefix"]["events"] = self.event_bindings()
        self.inventory["journal_prefix"]["chain_tip_sha256"] = self.journal.events[-1]["sha256"]
        self.scoring_context = {**self.context, "commit": SCORING_COMMIT, "spec_sha256": SCORING_SPEC,
                                "manifest": {"output_root": original.OUTPUT_ROOT}}
        self.context.update(commit=RENDER_COMMIT, spec_sha256=RENDER_SPEC,
                            scoring_context=self.scoring_context)
        self.context["manifest"] = {"output_root": original.OUTPUT_ROOT}
        self.add_scoring_attempt("preflight", "verify")
        self.add_scoring_attempt("preflight", "score")
        self.score_bindings = []
        for window in self.proposal["windows"]:
            name = window["window_id"]
            path = self.output / "evaluation/windows" / (name + ".json")
            value = {"schema_version": scoring.WINDOW_SCHEMA, "experiment_spec_sha256": SCORING_SPEC,
                     "code_commit": SCORING_COMMIT, "window_id": name,
                     "synthetic_fixture": "Frozen artifact; no score operation was performed"}
            write_json(path, {**value, "content_sha256": canonical_sha256(value)})
            b = binding(root, path)
            self.score_bindings.append(b)
            self.add_scoring_attempt("score", name, [b])
        pools = []
        for purpose in self.proposal["pool_separation"]:
            path = self.output / "evaluation" / (purpose + ".json")
            value = {"schema_version": scoring.POOL_SCHEMA, "experiment_spec_sha256": SCORING_SPEC,
                     "code_commit": SCORING_COMMIT, "purpose": purpose}
            write_json(path, {**value, "content_sha256": canonical_sha256(value)})
            pools.append(binding(root, path))
        self.score_bindings.extend(pools)
        self.add_scoring_attempt("score-final", "", pools)
        self.add_scoring_attempt("preflight", "render")
        failed_id = "158f51be5ab34cdface57f4e0036b7d2"
        with patch.object(resources.uuid, "uuid4", return_value=SimpleNamespace(hex=failed_id)):
            attempt, _ = self.journal.reserve("recovery:render:" + self.proposal["windows"][0]["window_id"], False)
        pending = self.output / "review/windows" / (".pending_" + self.proposal["windows"][0]["window_id"] + "_original")
        pending.mkdir(parents=True)
        partials = []
        for i, folder in enumerate(("comparison", "closeups", *("view_" + str(j) for j in range(8)))):
            file = pending / folder / "frame_000000.png"
            file.parent.mkdir()
            file.write_bytes(b"Invented PNG-shaped partial, never decoded: " + str(i).encode())
            partials.append({**binding(root, file), "size_bytes": file.stat().st_size})
        log = self.output / "attempts" / (failed_id + ".log")
        log.write_bytes(b"")
        self.finish_attempt(attempt, "failed_render", [], success=False, elapsed=.5,
                            commit=SCORING_COMMIT, spec=SCORING_SPEC)
        failed_event = copy.deepcopy(self.journal.events[-1])
        self.interruption = {"experiment_commit": SCORING_COMMIT, "spec_sha256": SCORING_SPEC,
            "completed_selection_manifests": [e["manifest"] for e in self.selections],
            "completed_trace_bindings": [{k: v for k, v in b.items() if k != "frame_index"}
                for e in self.selections for b in e["traces"]],
            "completed_scoring_artifacts": self.score_bindings,
            "successful_worker_receipts": self.successful_worker_bindings(),
            "original_failed_scoring_preserved": copy.deepcopy(self.failure),
            "failed_render_completion_event": failed_event, "failed_render_log": binding(root, log),
            "partial_review_files": partials,
            "absent_final_review_targets": [(self.output / "review/windows" / w["window_id"]).relative_to(root).as_posix()
                for w in self.proposal["windows"]] + [(self.output / "review/manifest.json").relative_to(root).as_posix()],
            "verified_bindings": [w["crop_candidates"] for w in self.proposal["windows"]]}
        forensic = self.output / "audit/synthetic_render_interruption.json"
        write_json(forensic, self.interruption)
        self.add_scoring_attempt("render-interruption-diagnosis", "", [binding(root, forensic)])
        attempts = []
        for aid, item in self.journal._attempts().items():
            end = item["finished"]
            result = end["worker_result"]
            attempts.append({"attempt_id": aid, "unit_key": item["start"]["unit_key"], "success": end["success"],
                "reservation": binding(root, self.output / "attempts" / (aid + ".reservation.json")),
                "completion": binding(root, self.output / "attempts" / (aid + ".completion.json")),
                "completion_event_sha256": end["sha256"],
                "worker_result": binding(root, self.output / result["path"]) if result is not None else None})
        last = self.output / "resource_events" / f"{len(self.journal.events)-1:08d}.json"
        self.checkpoint = {"schema_version": "ball_crop_retention_render_interruption_checkpoint/v0.1",
            "commit": SCORING_COMMIT, "forensic_receipt": binding(root, forensic),
            "diagnosis_completion_event": {**binding(root, last), "canonical_sha256": self.journal.events[-1]["sha256"]},
            "journal_prefix": {"events": self.event_bindings(), "chain_tip_sha256": self.journal.events[-1]["sha256"],
                               "attempts": attempts},
            "completed_attempts": 41, "successful_attempts": 39, "failed_attempts": 2,
            "cumulative_seconds": self.journal.consumed(), "remaining_seconds": 14400-self.journal.consumed(),
            "comparison_audit_complete": False, "human_visual_review_complete": False}
        self.context.update(interruption=self.interruption, checkpoint=self.checkpoint)
        checkpoint_path = self.output / "audit/synthetic_checkpoint.json"
        write_json(checkpoint_path, self.checkpoint)
        self.context["manifest"].update(interruption_receipt=binding(root, forensic),
                                        resource_checkpoint=binding(root, checkpoint_path))

    def event_bindings(self):
        return [binding(self.root, p) for p in sorted((self.output / "resource_events").glob("*.json"))]

    def successful_worker_bindings(self):
        return [binding(self.root, self.output / e["worker_result"]["path"]) for e in self.journal.events
                if e["kind"] == "finished" and e["success"] is True]

    def add_scoring_attempt(self, stage, key, artifacts=None):
        attempt, _ = self.journal.reserve("recovery:" + stage + ":" + key, False)
        return self.finish_attempt(attempt, stage, artifacts or [], stage=stage, key=key,
                                   commit=SCORING_COMMIT, spec=SCORING_SPEC)

    def add_render_attempt(self, stage, key, artifacts=None, *, success=True, commit=RENDER_COMMIT, spec=RENDER_SPEC):
        attempt, _ = self.journal.reserve("render-recovery:" + stage + ":" + key, False)
        return self.finish_attempt(attempt, stage, artifacts or [], stage=stage, key=key,
                                   success=success, commit=commit, spec=spec)


class RenderRecoveryBoundaryTests(TemporaryRoot):
    def test_metadata_compares_file_binding_without_conflating_canonical_spec_digest(self):
        authority = self.root / "configs/ball_tracking/crop_retention_experiments"
        certificate = self.root / "saved_certificate.json"
        write_json(certificate, {"source_bindings": []})
        score_path = authority / "scoring.json"
        write_json(score_path, {"synthetic": "scoring authority metadata only"})
        score_binding = binding(self.root, score_path)
        prior = {"spec_sha256": SCORING_SPEC, "manifest": {
            "implementation_validation": binding(self.root, certificate),
            "preserved_inventory": {"path": "inventory.json", "sha256": "d" * 64}},
            "original_context": {}, "inventory": {}, "proposal": {}}
        forensic = self.root / "forensic.json"
        write_json(forensic, {"experiment_commit": SCORING_COMMIT, "spec_sha256": SCORING_SPEC,
            "manifest": score_binding, "implementation_validation": prior["manifest"]["implementation_validation"],
            "preserved_inventory": prior["manifest"]["preserved_inventory"]})
        checkpoint = self.root / "checkpoint.json"
        write_json(checkpoint, {"schema_version": "ball_crop_retention_render_interruption_checkpoint/v0.1",
            "commit": SCORING_COMMIT, "forensic_receipt": binding(self.root, forensic),
            "journal_prefix": {"events": [{} for _ in range(1170)]},
            "completed_attempts": 41, "successful_attempts": 39, "failed_attempts": 2,
            "comparison_audit_complete": False, "human_visual_review_complete": False})
        proposal = self.root / "proposal.md"
        proposal.write_text("Fabricated metadata authority", encoding="utf-8")
        approval = self.root / "approval.json"
        write_json(approval, {"schema_version": "ball_crop_candidate_retention_render_recovery_approval/v0.1",
            "proposal": binding(self.root, proposal), "approved_by": "ryan",
            "implementation_authorized": True, "execution_authorized": True,
            "training_authorized": False, "git_mutations_authorized": False})
        manifest = {"schema_version": "ball_crop_candidate_retention_render_recovery/v0.1",
            "recovery_id": recovery.RECOVERY_ID, "scoring_manifest": {**score_binding, "content_sha256": SCORING_SPEC},
            "render_proposal": binding(self.root, proposal), "authorization": binding(self.root, approval),
            "interruption_receipt": binding(self.root, forensic), "resource_checkpoint": binding(self.root, checkpoint),
            "implementation_validation": None, "output_root": original.OUTPUT_ROOT,
            "permitted_stages": ["verify", "render"], "selected_method": None,
            "selected_operating_point": None, "quality_gate": None}
        path = authority / "render.json"
        write_json(path, manifest)
        with ExitStack() as stack:
            for constant, field in (("SCORING_MANIFEST_SHA256", "scoring_manifest"),
                    ("RENDER_PROPOSAL_SHA256", "render_proposal"), ("APPROVAL_SHA256", "authorization"),
                    ("INTERRUPTION_SHA256", "interruption_receipt"), ("CHECKPOINT_SHA256", "resource_checkpoint")):
                stack.enter_context(patch.object(recovery, constant, manifest[field]["sha256"]))
            stack.enter_context(patch.object(original, "_git", return_value=RENDER_COMMIT))
            stack.enter_context(patch.object(recovery.previous, "_metadata", return_value=prior))
            stack.enter_context(patch.object(original, "load_context", side_effect=AssertionError("Scientific inputs opened by metadata loader")))
            loaded = recovery._metadata(self.root, path, False)
            self.assertEqual(loaded["commit"], RENDER_COMMIT)
            self.assertEqual(loaded["scoring_context"]["commit"], SCORING_COMMIT)
            self.assertEqual(loaded["spec_sha256"], canonical_sha256(manifest))
            manifest["scoring_manifest"]["content_sha256"] = "0" * 64
            write_json(path, manifest)
            with self.assertRaises(ValueError):
                recovery._metadata(self.root, path, False)

    def test_missing_certificate_fails_before_any_reuse_is_possible(self):
        with self.assertRaises(ValueError):
            recovery._validate_implementation(self.root, {"implementation_validation": None})

    def test_certificate_binds_scope_complete_validation_and_current_sources(self):
        files = [self.root / "src/module.py", self.root / "tests/test_module.py", self.root / "requirements.txt"]
        for file in files:
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("# fabricated certified source\n", encoding="utf-8")
        certificate = {"focused_tests_passed": True, "full_suite_passed": True,
            "resource_abort_and_resume_tests_passed": True, "independent_static_review_passed": True,
            "render_proposal_sha256": recovery.RENDER_PROPOSAL_SHA256,
            "resource_checkpoint_sha256": "1" * 64, "interruption_receipt_sha256": "2" * 64,
            "scoring_manifest_sha256": "3" * 64,
            "source_bindings": [binding(self.root, file) for file in files], "evidence_bindings": []}
        cert_path = self.root / "certificate.json"
        write_json(cert_path, certificate)
        manifest = {"implementation_validation": binding(self.root, cert_path),
            "resource_checkpoint": {"sha256": "1" * 64}, "interruption_receipt": {"sha256": "2" * 64},
            "scoring_manifest": {"sha256": "3" * 64}, "render_proposal": {"sha256": recovery.RENDER_PROPOSAL_SHA256}}
        with patch.object(original, "_git", return_value=""):
            recovery._validate_implementation(self.root, manifest)
            original_bytes = files[0].read_bytes()
            files[0].write_bytes(original_bytes + b"changed")
            with self.assertRaises(ValueError):
                recovery._validate_implementation(self.root, manifest)
            files[0].write_bytes(original_bytes)
            for field, value in (("full_suite_passed", False), ("render_proposal_sha256", "0" * 64),
                                 ("resource_checkpoint_sha256", "0" * 64),
                                 ("interruption_receipt_sha256", "0" * 64),
                                 ("scoring_manifest_sha256", "0" * 64),
                                 ("source_bindings", certificate["source_bindings"][:1])):
                changed = {**certificate, field: value}
                write_json(cert_path, changed)
                manifest["implementation_validation"] = binding(self.root, cert_path)
                with self.subTest(field=field), self.assertRaises(ValueError):
                    recovery._validate_implementation(self.root, manifest)

    def test_dirty_worktree_or_nonempty_index_fail_before_authority_reads(self):
        for dirty, index in ((" M source.py", ""), ("", "source.py")):
            def git(root, *args):
                return {("branch", "--show-current"): "codex/ball-detector-baseline",
                        ("status", "--porcelain=v1"): dirty,
                        ("diff", "--cached", "--name-only"): index}[args]
            with self.subTest(dirty=dirty, index=index), patch.object(original, "_git", side_effect=git), \
                    patch.object(recovery, "read_json", side_effect=AssertionError("Authority read before clean-checkpoint guard")):
                with self.assertRaises(ValueError):
                    recovery._metadata(self.root, self.root / "manifest.json", True)

    def test_selector_scoring_aggregation_and_unknown_stages_are_not_dispatchable(self):
        for stage in ("select", "score", "score-final", "completion-audit", "unknown"):
            with self.subTest(stage=stage), patch.object(recovery, "_metadata",
                    side_effect=AssertionError("Unapproved stage opened metadata")):
                with self.assertRaises(ValueError):
                    recovery.run_recovery(self.root, self.root / "unused.json", stage=stage)
            with self.subTest(worker=stage), patch.object(recovery, "wait_for_supervisor",
                    side_effect=AssertionError("Unapproved worker started")):
                with self.assertRaises(ValueError):
                    recovery._worker(self.root, self.root / "unused.json", stage, "")

    def test_metadata_only_dry_run_cannot_inspect_saved_data_or_start_worker(self):
        with patch.object(recovery, "_metadata", return_value={"spec_sha256": RENDER_SPEC}) as metadata, \
                patch.object(recovery, "load_context", side_effect=AssertionError("Unsupervised saved input read")), \
                patch.object(recovery, "run_supervised", side_effect=AssertionError("Dry run worker")):
            result = recovery.run_recovery(self.root, self.root / "unused.json", dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertFalse(result["selection_executed"])
        self.assertFalse(result["scoring_executed"])
        self.assertFalse(metadata.call_args.args[2])

    def test_render_dispatch_is_exactly_one_preflight_six_windows_and_finalization(self):
        context = {"commit": RENDER_COMMIT, "output_root": self.root / original.OUTPUT_ROOT,
                   "proposal": {"windows": [{"window_id": "window_" + str(i)} for i in range(6)],
                                "resource_limits": {"synthetic": True}}}
        with ExitStack() as stack:
            forbid_scientific_work(stack)
            stack.enter_context(patch.object(recovery, "_metadata", return_value=context))
            dispatch = stack.enter_context(patch.object(recovery, "run_supervised", return_value={"success": True}))
            recovery.run_recovery(self.root, self.root / "manifest.json", stage="render")
        keys = [call.args[1] for call in dispatch.call_args_list]
        self.assertEqual(keys, ["render-recovery:preflight:render",
            *("render-recovery:render:window_" + str(i) for i in range(6)), "render-recovery:review-final:"])
        self.assertTrue(all(call.args[0] == context["output_root"] for call in dispatch.call_args_list))
        self.assertTrue(all(call.kwargs["selection_unit"] is False for call in dispatch.call_args_list))

    def test_a_failed_worker_stops_dispatch_without_retry_or_new_window(self):
        context = {"commit": RENDER_COMMIT, "output_root": self.root / original.OUTPUT_ROOT,
                   "proposal": {"windows": [{"window_id": "window_" + str(i)} for i in range(6)],
                                "resource_limits": {"synthetic": True}}}
        with patch.object(recovery, "_metadata", return_value=context), \
                patch.object(recovery, "run_supervised", side_effect=[{}, RuntimeError("resource abort")]) as dispatch:
            with self.assertRaisesRegex(RuntimeError, "resource abort"):
                recovery.run_recovery(self.root, self.root / "manifest.json", stage="render")
        self.assertEqual(dispatch.call_count, 2)


class RenderRecoveryHistoryTests(TemporaryRoot):
    def setUp(self):
        super().setUp()
        self.data = SyntheticRenderRecovery(self.root)

    def test_complete_prefix_keeps_two_failures_and_same_cumulative_budget(self):
        d = self.data
        with ExitStack() as stack:
            forbid_scientific_work(stack)
            journal = recovery.verify_history(self.root, d.context)
        self.assertEqual(len(journal._attempts()), 41)
        self.assertEqual(sum(a["finished"]["success"] is False for a in journal._attempts().values()), 2)
        self.assertAlmostEqual(journal.consumed(), d.checkpoint["cumulative_seconds"])
        _, remaining = journal.reserve("render-recovery:preflight:render", False)
        self.assertAlmostEqual(remaining, d.checkpoint["remaining_seconds"])
        self.assertTrue(d.partial.exists())
        self.assertTrue(all((self.root / b["path"]).exists() for b in d.interruption["partial_review_files"]))

    def test_exact_old_selections_load_without_relabeling_source_or_executing_algorithm(self):
        d = self.data
        with ExitStack() as stack:
            forbid_scientific_work(stack)
            stack.enter_context(patch.object(scoring, "load_window_score", return_value={"synthetic": True}))
            validated = recovery.validate_preserved(self.root, d.context)
            self.assertEqual(validated["selection_units"], 24)
            self.assertEqual(validated["trace_shards"], 600)
            self.assertEqual(validated["scoring_artifacts"], 8)
            self.assertEqual(validated["preserved_partial_pngs"], 10)
            value = recovery.load_reused_observations(self.root, d.context, d.selections[-1]["unit"])
            self.assertEqual(value["ranking_code_commit"], SELECTION_COMMIT)
            self.assertEqual(len(value["frames"]), 25)
            self.assertTrue(all(f["emitted_candidate_indices"] == [] for f in value["frames"]))
        with self.assertRaises(ValueError):
            original.load_new_observations(self.root, d.context, d.selections[0]["unit"])
        unknown = copy.deepcopy(d.selections[0]["unit"])
        unknown["comparison_unit_id"] = "unapproved-unit"
        with self.assertRaises(ValueError):
            recovery.load_reused_observations(self.root, d.context, unknown)

    def test_selection_and_score_allowlists_cannot_omit_duplicate_or_add_items(self):
        d = self.data
        for field in ("completed_selection_manifests", "completed_trace_bindings", "completed_scoring_artifacts"):
            saved = d.interruption[field]
            for change in ("missing", "duplicate", "unknown"):
                altered = copy.deepcopy(saved)
                if change == "missing":
                    altered.pop()
                elif change == "duplicate":
                    altered[-1] = copy.deepcopy(altered[0])
                else:
                    altered[-1]["path"] = "unknown.json"
                d.interruption[field] = altered
                try:
                    with self.subTest(field=field, change=change), self.assertRaises((ValueError, RuntimeError)):
                        recovery.validate_preserved(self.root, d.context)
                finally:
                    d.interruption[field] = saved

    def test_changed_original_inputs_outputs_and_partials_are_rejected(self):
        d = self.data
        bindings = [d.selections[0]["manifest"], d.selections[0]["traces"][0],
                    d.proposal["windows"][0]["crop_candidates"], d.failure["partial"], d.failure["log"],
                    d.interruption["partial_review_files"][0], d.interruption["failed_render_log"]]
        with patch.object(scoring, "load_window_score", return_value={"synthetic": True}):
            for b in bindings:
                path = self.root / b["path"]
                before = path.read_bytes()
                path.write_bytes(before + b"altered")
                try:
                    with self.subTest(path=b["path"]), self.assertRaises((ValueError, RuntimeError)):
                        recovery.validate_preserved(self.root, d.context)
                finally:
                    path.write_bytes(before)
            staging = (self.root / d.interruption["partial_review_files"][0]["path"]).parent.parent
            extra = staging / "unbound.png"
            extra.write_bytes(b"extra fabricated partial")
            with self.assertRaises((ValueError, RuntimeError)):
                recovery.validate_preserved(self.root, d.context)

    def test_missing_event_changed_completion_and_reservation_seals_reject_resume(self):
        d = self.data
        targets = [self.root / d.checkpoint["journal_prefix"]["events"][3]["path"],
                   self.root / d.checkpoint["journal_prefix"]["attempts"][-1]["completion"]["path"],
                   self.root / d.checkpoint["journal_prefix"]["attempts"][-1]["reservation"]["path"]]
        for target in targets:
            before = target.read_bytes()
            with self.subTest(path=target.name):
                target.unlink()
                try:
                    with self.assertRaises((ValueError, RuntimeError, FileNotFoundError)):
                        recovery.verify_history(self.root, d.context)
                finally:
                    target.write_bytes(before)
                target.write_bytes(before + b" ")
                try:
                    with self.assertRaises((ValueError, RuntimeError)):
                        recovery.verify_history(self.root, d.context)
                finally:
                    target.write_bytes(before)

    def test_completed_score_without_exact_successful_resource_receipt_cannot_be_reused(self):
        d = self.data
        score_attempt = next(r for r in d.checkpoint["journal_prefix"]["attempts"]
                             if r["unit_key"] == "recovery:score:w0")
        receipt = self.root / score_attempt["worker_result"]["path"]
        receipt.unlink()
        self.assertTrue((self.root / d.score_bindings[0]["path"]).is_file())
        with patch.object(scoring, "load_window_score", side_effect=AssertionError("Unreceipted score loaded")):
            with self.assertRaises((ValueError, RuntimeError, FileNotFoundError)):
                recovery.load_reused_score(self.root, d.context, "w0")

    def test_reused_score_loader_is_allowlisted_and_uses_old_evaluation_identity(self):
        d = self.data
        with ExitStack() as stack:
            forbid_scientific_work(stack)
            loader = stack.enter_context(patch.object(scoring, "load_window_score", return_value={"synthetic": True}))
            value = recovery.load_reused_score(self.root, d.context, "w0")
        self.assertEqual(value, {"synthetic": True})
        old = loader.call_args.args[1]
        self.assertEqual(old["commit"], SCORING_COMMIT)
        self.assertEqual(old["spec_sha256"], SCORING_SPEC)
        self.assertEqual(d.context["commit"], RENDER_COMMIT)
        self.assertEqual(d.context["spec_sha256"], RENDER_SPEC)
        with patch.object(scoring, "load_window_score", side_effect=AssertionError("Unknown score loaded")):
            with self.assertRaises((ValueError, RuntimeError)):
                recovery.load_reused_score(self.root, d.context, "unknown-window")

    def test_changed_scoring_bytes_fail_before_saved_report_loader(self):
        d = self.data
        target = self.root / d.score_bindings[0]["path"]
        target.write_bytes(target.read_bytes() + b" ")
        with patch.object(scoring, "load_window_score", side_effect=AssertionError("Altered score body loaded")):
            with self.assertRaises((ValueError, RuntimeError)):
                recovery.load_reused_score(self.root, d.context, "w0")

    def test_prefix_before_forensic_completion_is_not_sufficient(self):
        d = self.data
        shortened = copy.deepcopy(d.checkpoint)
        shortened["journal_prefix"]["events"] = shortened["journal_prefix"]["events"][:-2]
        shortened["journal_prefix"]["attempts"] = shortened["journal_prefix"]["attempts"][:-1]
        d.context["checkpoint"] = shortened
        with self.assertRaises((ValueError, RuntimeError)):
            recovery.verify_history(self.root, d.context)

    def test_further_resource_failure_stops_instead_of_becoming_another_known_failure(self):
        d = self.data
        d.add_render_attempt("render", d.proposal["windows"][0]["window_id"], success=False)
        with self.assertRaises((ValueError, RuntimeError)):
            recovery.verify_history(self.root, d.context)
        self.assertTrue(d.partial.exists())

    def test_new_result_requires_actual_renderer_spec_commit_and_completion_seal(self):
        d = self.data
        record = d.add_render_attempt("preflight", "render")
        self.assertEqual(recovery.completed_bindings(self.root, d.context), {})
        seal = self.root / record["completion"]["path"]
        before = seal.read_bytes()
        seal.unlink()
        try:
            with self.assertRaises((ValueError, RuntimeError, FileNotFoundError)):
                recovery.completed_bindings(self.root, d.context)
        finally:
            seal.write_bytes(before)
        for field, value in (("commit", SCORING_COMMIT), ("spec_sha256", SCORING_SPEC)):
            changed = {**d.context, field: value}
            with self.subTest(field=field), self.assertRaises((ValueError, RuntimeError)):
                recovery.completed_bindings(self.root, changed)

    def test_successful_but_unapproved_scoring_receipt_is_rejected(self):
        d = self.data
        d.add_render_attempt("score", d.proposal["windows"][0]["window_id"], [d.score_bindings[0]])
        with self.assertRaises((ValueError, RuntimeError)):
            recovery.completed_bindings(self.root, d.context)

    def test_unknown_or_incomplete_review_receipt_cannot_bless_an_artifact(self):
        d = self.data
        target = d.output / "review/unapproved.json"
        write_json(target, {"synthetic": True})
        d.add_render_attempt("render", d.proposal["windows"][0]["window_id"], [binding(self.root, target)])
        with self.assertRaises((ValueError, RuntimeError)):
            recovery.completed_bindings(self.root, d.context)

    def test_completion_audit_receipt_accepts_only_the_exact_independent_receipt(self):
        d = self.data
        target = d.output / "audit/independent_render_recovery_audit.json"
        write_json(target, {"synthetic": "receipt only"})
        d.add_render_attempt("completion-audit", "", [binding(self.root, target)])
        self.assertEqual(recovery.completed_bindings(self.root, d.context),
                         {target.relative_to(self.root).as_posix(): sha256_file(target)})
        d.add_render_attempt("completion-audit", "", [d.score_bindings[0]])
        with self.assertRaises((ValueError, RuntimeError)):
            recovery.completed_bindings(self.root, d.context)

    def test_final_publication_without_successful_completion_is_never_adopted(self):
        d = self.data
        target = d.output / "review/windows" / d.proposal["windows"][0]["window_id"] / "manifest.json"
        write_json(target, {"looks_complete": True})
        with patch.object(review, "prepare_window", side_effect=AssertionError("Unreceipted review opened")):
            with self.assertRaises(ValueError):
                recovery._validate_published(self.root, d.context, {})
        self.assertTrue(target.exists())
        self.assertTrue(d.partial.exists())

    def test_unknown_final_window_and_new_unreceipted_pending_files_stop_resume(self):
        d = self.data
        for relative in ("review/windows/unknown_window/manifest.json", "review/windows/.pending_unbound/extra.png"):
            file = d.output / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b"unapproved")
            try:
                with self.subTest(path=relative), self.assertRaises(ValueError):
                    recovery._validate_published(self.root, d.context, {})
            finally:
                file.unlink()


class RenderRecoveryPresentationTests(TemporaryRoot):
    def prepared(self):
        context, experiment, evaluation, _, _, observations, reports, _ = context_fixture(self.root)
        context.update(commit=RENDER_COMMIT, spec_sha256=RENDER_SPEC)
        context["recovery_provenance"] = {"original_selection_commit": SELECTION_COMMIT,
            "original_selection_spec_sha256": SELECTION_SPEC, "original_evaluation_commit": SCORING_COMMIT,
            "original_evaluation_spec_sha256": SCORING_SPEC,
            "preserved_inventory": {"path": "synthetic_inventory.json", "sha256": "1" * 64},
            "scoring_manifest": {"path": "synthetic_scoring_manifest.json", "sha256": "2" * 64,
                                 "content_sha256": SCORING_SPEC},
            "interruption_receipt": {"path": "synthetic_interruption.json", "sha256": "3" * 64},
            "resource_checkpoint": {"path": "synthetic_checkpoint.json", "sha256": "4" * 64}}
        for key in review.VIEW_KEYS:
            obs, report = observations[key], reports[key]
            if key[1] == "all":
                obs["ranking_code_commit"] = SELECTION_COMMIT
                last = obs["frames"][-1]
                last["emitted_candidate_indices"] = []
                last["decision_reason"] = "empty_hypothesis"
                last["ranking"]["winner"] = {"endpoint": None, "score": 0.0, "path": []}
                row = report["frame_results"][-1]
                row.update(input_detection_count=0, accepted_detection_count=0, matched_candidate_index=None,
                           false_positive_count=0, false_negative_count=1, matched_center_error_px=None,
                           matched_effective_center_error_px=None)
                report["ranking_code_commit"] = SELECTION_COMMIT
                report["evaluator_code_commit"] = SCORING_COMMIT
            report["observations_content_sha256"] = canonical_sha256(obs)
        score_loader = lambda root, ctx, wid: evaluation.load_window_score(root, ctx, wid)
        observation_loader = lambda root, ctx, unit: experiment.load_new_observations(root, ctx, unit)
        with ExitStack() as stack:
            forbid_scientific_work(stack)
            stack.enter_context(patch.object(original, "load_saved_control", side_effect=experiment.load_saved_control))
            stack.enter_context(patch.object(original, "load_new_observations", side_effect=AssertionError("Default current-commit observation loader")))
            stack.enter_context(patch.object(scoring, "load_window_score", side_effect=AssertionError("Default current-commit score loader")))
            prepared = review.prepare_window(self.root, context, "synthetic_development_window",
                observation_loader=observation_loader, score_loader=score_loader)
        # Reload closures intentionally retain the fabricated loader objects.
        return context, prepared

    def test_distinct_selection_score_renderer_roles_nulls_and_complete_six_clip_contract(self):
        context, prepared = self.prepared()
        self.assertEqual(prepared.header["renderer_code_commit"], RENDER_COMMIT)
        self.assertEqual(prepared.header["experiment_spec_sha256"], RENDER_SPEC)
        self.assertEqual(prepared.header["recovery_provenance"], context["recovery_provenance"])
        for arm in review.ARMS:
            self.assertEqual(prepared.observations[arm, "all"]["ranking_code_commit"], SELECTION_COMMIT)
            self.assertEqual(prepared.reports[arm, "all"]["evaluator_code_commit"], SCORING_COMMIT)
            self.assertIn("NULL", review._details(prepared.run.frames[-1], prepared.observations[arm, "all"]["frames"][-1])[0])
        windows = []
        with ExitStack() as stack:
            forbid_scientific_work(stack)
            stack.enter_context(patch.object(review, "TILE_WIDTH", 48))
            stack.enter_context(patch.object(review, "TILE_HEIGHT", 32))
            render = stack.enter_context(patch.object(review, "render_frame", side_effect=fast_frame))
            for i in range(6):
                item = copy.copy(prepared)
                item.header = copy.deepcopy(prepared.header)
                item.window = {**prepared.window, "window_id": "synthetic_render_" + str(i),
                               "purpose": "representative_evaluation" if i < 3 else "challenge_evaluation"}
                item.header["window"] = item.window
                windows.append(item.window)
                target = self.root / original.OUTPUT_ROOT / "review/windows" / item.window["window_id"]
                value = review.render_prepared_window(self.root, item, target)
                self.assertFalse(value["reused"])
                manifest = read_json(target / "manifest.json")
                self.assertEqual(manifest["video_verification"]["decoded_frames"], 25)
                self.assertEqual(manifest["final_frame"], 24)
                self.assertEqual(len(manifest["final_png_verification"]), 12)
                self.assertEqual(manifest["human_visual_review"], "pending")
                self.assertTrue(all(manifest["header"][k] is None for k in
                                    ("selected_method", "selected_operating_point", "quality_gate")))
            self.assertEqual(render.call_count, 150)
            summary = review.finalize_review(self.root, {**context, "proposal": {"windows": windows}})
        self.assertEqual(summary["windows"], 6)
        self.assertEqual([w["purpose"] for w in windows].count("representative_evaluation"), 3)
        final = read_json(self.root / summary["manifest"]["path"])
        self.assertTrue(all(w["final_source_frame"] == 24 for w in final["windows"]))
        self.assertEqual(final["previous_motion_and_yolo_review"], "complete_no_repeat")

    def test_interrupted_attempt_uses_fresh_staging_and_preserves_prior_partial(self):
        _, prepared = self.prepared()
        target = self.root / original.OUTPUT_ROOT / "review/windows" / prepared.window["window_id"]
        previous = target.parent / (".pending_" + target.name + "_original")
        previous.mkdir(parents=True)
        protected = previous / "first.png"
        protected.write_bytes(b"preserved invented partial bytes")
        digest = sha256_file(protected)
        with patch.object(review, "render_frame", side_effect=RuntimeError("new simulated interruption")):
            with self.assertRaisesRegex(RuntimeError, "new simulated interruption"):
                review.render_prepared_window(self.root, prepared, target)
        self.assertFalse(target.exists())
        pending = list(target.parent.glob(".pending_*"))
        self.assertEqual(len(pending), 2)
        self.assertEqual(sha256_file(protected), digest)
        new = next(p for p in pending if p != previous)
        self.assertEqual(read_json(new / "failure.json")["status"], "incomplete")


if __name__ == "__main__":
    unittest.main()
