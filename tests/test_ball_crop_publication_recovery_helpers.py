"""Synthetic contracts for separately bound, ignored publication helpers.

No scientific files, resource journal, model, saved images or video are read.
On checkouts without the ignored prepared helpers these tests skip explicitly.
"""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
HELPERS = ROOT / "data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1/audit"


def load(name):
    path = HELPERS / (name + ".py")
    if not path.is_file():
        raise unittest.SkipTest("Separately prepared ignored publication helper is absent")
    spec = importlib.util.spec_from_file_location("synthetic_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PublicationRecoveryHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load("independent_publication_recovery_audit")
        cls.guide = load("publication_recovery_review_guide")

    def fixture(self):
        windows = [{"window_id": "synthetic_" + str(i), "possession_id": "synthetic_possession_" + str(i // 2),
                    "purpose": "representative_evaluation" if i % 2 == 0 else "challenge_evaluation",
                    "start_frame_index": i * 25, "end_frame_index": i * 25 + 24} for i in range(6)]
        context = {"commit": "synthetic_commit", "spec_sha256": "synthetic_spec", "proposal": {"windows": windows}}
        cells = []
        keys = ("true_positive_count", "false_positive_count", "false_negative_count", "non_visible_false_alarm_count")
        for arm in self.guide.ARMS:
            for radius in (5, 10, 15, 20, 30):
                denominators = {"eligible_frame_count": 70, "not_visible_frame_count": 5, "unscored_frame_count": 0}
                cells.append({"arm": arm, "confidence_threshold": .01, "radius_px": radius,
                              "saved_cap20": {**dict(zip(keys, (40, 12, 30, 2))), **denominators},
                              "new_all": {**dict(zip(keys, (42, 10, 28, 1))), **denominators},
                              "metric_deltas": dict(zip(keys, (2, -2, -2, -1))),
                              "gained_match_frames": [{"possession_id": "synthetic_possession", "frame_index": 12}],
                              "lost_match_frames": []})
        value = {"schema_version": "ball_crop_retention_independent_publication_recovery_audit/v0.1", "status": "passed",
                 "execution_code_commit": context["commit"], "experiment_spec_sha256": context["spec_sha256"],
                 "new_comparison_clips_independently_decoded": 6, "human_visual_review": "pending_six_new_floor_clips_only",
                 "prior_reviews": "complete_no_repeat", "selected_method": None, "selected_operating_point": None, "quality_gate": None,
                 "pool_audits": [{"purpose": purpose, "fixed_floor_radius10_descriptive_cells": [c for c in cells if c["radius_px"] == 10],
                                 "all_radius_cap_deltas": cells,
                                 "fixed_floor_radius10_missingness_by_window": [{"window_id": window["window_id"], "purpose": purpose,
                                    "arm": arm, "confidence_threshold": .01, "radius_px": 10,
                                    "saved_cap20": {"frame_count": 25, "emitted_frame_count": 20, "missing_frame_count": 5, "emitted_frame_coverage": .8},
                                    "new_all": {"frame_count": 25, "emitted_frame_count": 22, "missing_frame_count": 3, "emitted_frame_coverage": .88}}
                                    for window in windows if window["purpose"] == purpose for arm in self.guide.ARMS]}
                                    for purpose in ("representative_evaluation", "challenge_evaluation")],
                 "review_audits": [{"window_id": w["window_id"], "final_source_frame": w["end_frame_index"], "human_visual_review": "pending",
                                    "independent_new_clip_decode": {"decoded_frames": 25}} for w in windows]}
        value["content_sha256"] = self.guide.canonical(value)
        return context, value

    def republish(self, value):
        value["content_sha256"] = self.guide.canonical({k: v for k, v in value.items() if k != "content_sha256"})

    def test_guide_copies_audited_cells_and_all_six_final_frames(self):
        context, value = self.fixture()
        before = copy.deepcopy(value)
        text = self.guide.format_guide(Path("/synthetic"), context, value, {"synthetic": True})
        self.assertEqual(value, before)
        self.assertIn("Representative pool", text)
        self.assertIn("Challenge pool", text)
        self.assertEqual(text.count("[Play clip]"), 6)
        self.assertIn("40 → 42", text)
        for window in context["proposal"]["windows"]:
            self.assertIn(f"frame_{window['end_frame_index']:06d}.png", text)
        self.assertIn("twelve earlier YOLO final-frame reviews are complete", text)
        self.assertIn("original failure remains a failure", text)
        self.assertIn("No confidence tuning", text)
        self.assertIn("Missing observations (NULL) differ", text)
        self.assertIn("5 → 3", text)
        self.assertIn("70 localization-eligible frames, 5 reviewed hidden frames", text)

    def test_tampered_audit_rejected(self):
        context, value = self.fixture()
        value["status"] = "failed"
        with self.assertRaisesRegex(ValueError, "exact passed"):
            self.guide.validate_audit(value, context)

    def test_wrong_commit_even_with_consistent_content_hash_rejected(self):
        context, value = self.fixture()
        value["execution_code_commit"] = "other"
        self.republish(value)
        with self.assertRaisesRegex(ValueError, "exact passed"):
            self.guide.validate_audit(value, context)

    def test_human_review_or_method_selection_cannot_be_fabricated(self):
        for field, replacement in (("human_visual_review", "complete"), ("selected_method", "winner")):
            with self.subTest(field=field):
                context, value = self.fixture()
                value[field] = replacement
                self.republish(value)
                with self.assertRaisesRegex(ValueError, "review/selection"):
                    self.guide.validate_audit(value, context)

    def test_pool_combination_and_missing_final_frame_rejected(self):
        context, value = self.fixture()
        value["pool_audits"][1]["purpose"] = "representative_evaluation"
        self.republish(value)
        with self.assertRaisesRegex(ValueError, "Pool separation"):
            self.guide.validate_audit(value, context)
        context, value = self.fixture()
        value["review_audits"][-1]["final_source_frame"] -= 1
        self.republish(value)
        with self.assertRaisesRegex(ValueError, "final-frame"):
            self.guide.validate_audit(value, context)

    def test_independent_source_is_hash_bound_before_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / self.audit.OUTPUT_NAME / "audit/independent_render_recovery_audit.py"
            target.parent.mkdir(parents=True)
            target.write_text("raise AssertionError('must not execute')", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source changed"):
                self.audit.load_independent(root)

    def test_inventory_rejects_inaccessible_walk(self):
        def incomplete(folder, *, onerror):
            onerror(PermissionError("synthetic unreadable subtree"))
            return iter(())
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(self.audit.os, "walk", incomplete):
                with self.assertRaises(PermissionError):
                    self.audit.file_set(Path(directory), Path(directory))

    def test_create_only_and_safe_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "receipt.json"
            self.audit.absent(target)
            target.write_text("synthetic", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Create-only"):
                self.audit.absent(target)
            for name in ("../outside", "/absolute", "C:/absolute", "x\\y", "x/../y"):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    self.guide.safe(root, name)

    def test_missingness_counts_checked_against_saved_emissions(self):
        arm = self.guide.ARMS[0]
        window = {"window_id": "synthetic", "purpose": "representative_evaluation", "possession_id": "synthetic_p",
                  "start_frame_index": 0, "end_frame_index": 24}
        def observation(count):
            return {"frames": [{"frame_index": i, "emitted_candidate_indices": [1] if i < count else []} for i in range(25)]}
        controls = {("synthetic", arm, .01): observation(20)}
        observations = {arm: observation(22)}
        reports = [{"config": {"arm": arm, "confidence_threshold": .01, "candidate_cap": cap}, "localization_radius_px": 10,
                    "temporal_metrics": {"frame_count": 25, "emitted_frame_count": emitted, "missing_frame_count": 25 - emitted,
                                         "emitted_frame_coverage": emitted / 25}} for cap, emitted in ((20, 20), (None, 22))]
        score = {"evaluation_reports": reports}
        rows = self.audit.paired_missingness(window, observations, controls, score)
        self.assertEqual(rows[0]["saved_cap20"]["missing_frame_count"], 5)
        self.assertEqual(rows[0]["new_all"]["missing_frame_count"], 3)
        reports[1]["temporal_metrics"]["missing_frame_count"] = 2
        with self.assertRaisesRegex(ValueError, "saved emissions"):
            self.audit.paired_missingness(window, observations, controls, score)

    def test_guide_rejects_missingness_and_denominator_tampering(self):
        context, value = self.fixture()
        value["pool_audits"][0]["fixed_floor_radius10_missingness_by_window"][0]["new_all"]["missing_frame_count"] = 0
        self.republish(value)
        with self.assertRaisesRegex(ValueError, "missingness arithmetic"):
            self.guide.validate_audit(value, context)
        context, value = self.fixture()
        value["pool_audits"][0]["fixed_floor_radius10_descriptive_cells"][0]["new_all"]["eligible_frame_count"] = 69
        self.republish(value)
        with self.assertRaisesRegex(ValueError, "denominators"):
            self.guide.validate_audit(value, context)

    def suffix_fixture(self):
        def start(aid, role, remaining):
            return {"kind": "started", "attempt_id": aid, "unit_key": "publication-recovery:" + role + ":",
                    "selection_unit": False, "reserved_seconds": remaining}
        def finish(aid, elapsed, budget):
            return {"kind": "finished", "attempt_id": aid, "elapsed_seconds": elapsed, "time_budget_seconds": budget, "success": True}
        return [start("accept", "accept", 90), finish("accept", 2, 90), start("final", "review-final", 88),
                finish("final", 3, 88), start("active", "completion-audit", 85)]

    def test_independent_suffix_exact_budgets_and_temporal_dependencies(self):
        limits = {"maximum_cumulative_seconds": 100}
        events = self.suffix_fixture()
        self.audit.validate_suffix(events, limits, 10, "active", "completion-audit")
        variants = []
        wrong = copy.deepcopy(events)
        wrong[0]["reserved_seconds"] = 91
        variants.append(wrong)
        variants.append([events[0], events[2], *events[1:]])
        variants.append([events[2], events[3], events[0], events[1], events[4]])
        wrong = copy.deepcopy(events)
        wrong[1]["time_budget_seconds"] = 89
        variants.append(wrong)
        wrong = copy.deepcopy(events)
        wrong[-1]["unit_key"] = "publication-recovery:verify:"
        variants.append(wrong)
        for index, wrong in enumerate(variants):
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.audit.validate_suffix(wrong, limits, 10, "active", "completion-audit")

    def test_historical_render_receipt_cannot_be_reassigned(self):
        snapshot = {"successful_render_attempt_id": "historical", "historical_success_binding_verified": True,
                    "window_id": "synthetic", "manifest": {"path": "synthetic/manifest.json", "sha256": "digest"}}
        start = {"unit_key": "render-recovery:render:synthetic"}
        worker = {"stage": "render", "key": "synthetic", "commit": self.audit.RENDER_COMMIT,
                  "spec_sha256": self.audit.RENDER_SPEC, "artifacts": [snapshot["manifest"]]}
        self.audit.historical_render_receipt(snapshot, "historical", start, worker)
        for field in ("stage", "key", "commit", "spec_sha256"):
            wrong = {**worker, field: "wrong"}
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "exact successful"):
                self.audit.historical_render_receipt(snapshot, "historical", start, wrong)

    def test_exact_presentation_worker_required(self):
        class Journal:
            def __init__(self, attempts):
                self.attempts = attempts
            def _attempts(self):
                return self.attempts
        row = {"finished": None, "start": {"selection_unit": False, "unit_key": "publication-recovery:presentation:"}}
        self.guide.current_presentation(Journal({"active": row}), "active")
        for attempts in ({}, {"other": row}, {"active": row, "other": row},
                         {"active": {"finished": None, "start": {"selection_unit": False, "unit_key": "publication-recovery:verify:"}}}):
            with self.subTest(attempts=attempts), self.assertRaisesRegex(ValueError, "current presentation"):
                self.guide.current_presentation(Journal(attempts), "active")


if __name__ == "__main__":
    unittest.main()
