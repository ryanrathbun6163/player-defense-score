"""Acceptance transport checks using actual delivered NBA producer records.

No source pixels, models or fitting are used. Temporary publication/receipt
pairs exercise the reader without changing any reviewed original artifact.
"""
import copy
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from src.ball_tracking.completion_references import binding, read_json, write_new
from src.ball_tracking.completion_nba_acceptance import (
    _validate_focused_test_scope,
    acceptance_receipt, accepted_nba_inventory, accepted_nba_reference,
    build_accepted_reference, reviewed_nba_evidence, validate_accepted_record,
)


class ActualNBAAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        path = cls.root / "configs/ball_tracking/reviews/nba_completion_reference_batch_01_result_v0_1.json"
        if not path.is_file():
            raise unittest.SkipTest("Actual completed NBA batch01 result is unavailable")
        result = read_json(path)
        if not (cls.root / result["review_manifest"]["path"]).is_file():
            raise unittest.SkipTest("Actual ignored NBA reviewed records are unavailable")
        cls.result_binding = binding(cls.root, path)
        cls.review = {
            "status": "accepted", "reviewer_id": "Ryan",
            "review_method": "human_visual_acceptance_of_assisted_proposals",
            "user_statement": "Ok I approve chat. Please move forward",
            "response_context": "Direct reply to the complete NBA batch01 review: all 120 labels, 96 centers and 24 nulls.",
            "exact_user_event_timestamp_utc": None,
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "playback_telemetry_claimed": False, "independent_human_annotation_claimed": False,
        }
        cls.doc = build_accepted_reference(cls.root, cls.result_binding, cls.review,
                                          "data/outputs/t/test-only-nba-acceptance-receipt.json")

    def test_actual_review_census_native_timing_and_unknown_centers(self):
        d = reviewed_nba_evidence(self.root, self.result_binding)
        self.assertEqual((d["accepted_references"], d["accepted_eligible_centers"], d["accepted_null_centers"]),
                         (120, 96, 24))
        self.assertEqual([f["native_pts_ticks"] for f in d["frames"]], list(range(0, 120000, 1000)))
        self.assertEqual({f["native_time_base"] for f in d["frames"]}, {"1/60000"})
        self.assertEqual([r["frame_index"] for r in d["annotations"] if r["geometry"] is None],
                         list(range(96, 120)))
        self.assertEqual(d["source_metadata"]["decoded_frames"] - 1, 662)
        self.assertEqual(d["frames"][-1]["source_frame_index"], 119)

    def test_acceptance_preserves_ai_authorship_and_separates_label_from_fit_readiness(self):
        d = validate_accepted_record(self.root, self.doc)
        self.assertEqual(d["annotation_origin"], "assistant_visual_proposal")
        self.assertEqual(d["annotator_id"], "Codex assistant")
        self.assertTrue(d["training_eligible"])
        self.assertFalse(d["checkpoint_selection_eligible"])
        self.assertIsNone(d["human_review"]["exact_user_event_timestamp_utc"])
        for field in ("package_ready_for_fitting", "executable_recipe_frozen",
                      "fitting_authorized_by_this_artifact", "protected_evaluation_authorized"):
            self.assertIs(d[field], False)

    def test_rejects_rewritten_center_uncertainty_and_null(self):
        for change in ("center", "uncertainty", "null"):
            d = copy.deepcopy(self.doc)
            if change == "center":
                d["annotations"][0]["geometry"]["center_xy_px"][0] += 1
            elif change == "uncertainty":
                d["annotations"][0]["geometry"]["uncertainty_radius_px"] += 1
            else:
                d["annotations"][96]["geometry"] = copy.deepcopy(d["annotations"][0]["geometry"])
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "Accepted annotations"):
                validate_accepted_record(self.root, d)

    def test_rejects_source_game_role_and_native_pts_drift(self):
        for field in ("source", "game", "role", "pts"):
            d = copy.deepcopy(self.doc)
            if field == "source":
                d["source_metadata"]["sha256"] = "0" * 64
            elif field == "game":
                d["game_id"] = "different-game"
            elif field == "role":
                d.update(role="checkpoint_validation", training_eligible=False, checkpoint_selection_eligible=True)
            else:
                d["frames"][0]["native_pts_ticks"] = 512
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "Accepted annotations"):
                validate_accepted_record(self.root, d)

    def test_rejects_fit_readiness_or_protected_authorization_from_label_acceptance(self):
        for field in ("training_eligible", "checkpoint_selection_eligible", "package_ready_for_fitting",
                      "executable_recipe_frozen", "fitting_authorized_by_this_artifact",
                      "protected_evaluation_authorized", "model_output_acceptance", "ball_phase_accepted"):
            d = copy.deepcopy(self.doc)
            d[field] = not d[field]
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "eligibility"):
                validate_accepted_record(self.root, d)

    def test_explicit_human_statement_context_and_unknown_time_are_required(self):
        for field in ("user_statement", "response_context", "exact_user_event_timestamp_utc"):
            review = copy.deepcopy(self.review)
            del review[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                build_accepted_reference(self.root, self.result_binding, review, "unused.json")

    def test_bound_result_hash_must_match(self):
        altered = {**self.result_binding, "sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "binding changed"):
            reviewed_nba_evidence(self.root, altered)

    def test_actual_serialized_pair_reader_source_keys_and_duplicate_guard(self):
        temp_parent = self.root / "data/outputs/t"
        temp_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="nba_acceptance_reader_", dir=temp_parent) as name:
            folder = Path(name).resolve()
            self.assertTrue(folder.is_relative_to(temp_parent.resolve()))
            publication, receipt_path = folder / "reference.json", folder / "receipt.json"
            d = copy.deepcopy(self.doc)
            d["acceptance_receipt_path"] = receipt_path.relative_to(self.root).as_posix()
            write_new(publication, d)
            pub_binding = binding(self.root, publication)
            receipt = acceptance_receipt(d, pub_binding)
            write_new(receipt_path, receipt)
            entry = {**pub_binding, "acceptance_receipt": binding(self.root, receipt_path)}
            actual, _ = accepted_nba_reference(self.root, entry)
            self.assertEqual(actual["annotations"], self.doc["annotations"])
            inventory, _ = accepted_nba_inventory(self.root, [entry])
            key = (d["game_id"], d["source_metadata"]["sha256"], 0)
            self.assertIn(key, inventory)
            self.assertEqual(len(inventory), 120)
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                accepted_nba_inventory(self.root, [entry, entry])
            wrong = copy.deepcopy(receipt)
            wrong["human_review"]["user_statement"] = "Different statement"
            wrong_path = folder / "wrong_receipt.json"
            write_new(wrong_path, wrong)
            with self.assertRaisesRegex(ValueError, "receipt links/content"):
                accepted_nba_reference(self.root, {**entry, "acceptance_receipt": binding(self.root, wrong_path)})


class ReusedProducerTestScopeTests(unittest.TestCase):
    """Scope-only extensions derived from actual NBA01 producer records.

    A byte-identical proposal copied to a new temporary path represents a new
    current binding for these metadata tests. It is not a new visual review,
    independent batch, or accepted publication. All original source/code/test
    evidence remains actual and unchanged.
    """

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        path = cls.root / "configs/ball_tracking/reviews/nba_completion_reference_batch_01_result_v0_1.json"
        if not path.is_file():
            raise unittest.SkipTest("Actual NBA result is unavailable")
        cls.original_result = read_json(path)
        if not (cls.root / cls.original_result["review_manifest"]["path"]).is_file():
            raise unittest.SkipTest("Actual ignored NBA review records are unavailable")
        cls.original_evidence = reviewed_nba_evidence(cls.root, binding(cls.root, path))["evidence"]
        cls.original_audit = read_json(cls.root / cls.original_evidence["integration_audit"]["path"])

    def setUp(self):
        parent = self.root / "data/outputs/t"
        self.temp = tempfile.TemporaryDirectory(prefix="nba_test_scope_", dir=parent)
        self.folder = Path(self.temp.name).resolve()
        self.assertTrue(self.folder.is_relative_to(parent.resolve()))
        self.addCleanup(self.temp.cleanup)
        self.result = copy.deepcopy(self.original_result)
        self.evidence = copy.deepcopy(self.original_evidence)
        proposal = self.folder / "current_proposal_copy.json"
        with proposal.open("xb") as handle:
            handle.write((self.root / self.evidence["proposal"]["path"]).read_bytes())
        self.evidence["proposal"] = binding(self.root, proposal)
        self.result["proposal"] = self.evidence["proposal"]
        self.result["focused_tests_scope"] = "prior_unchanged_implementation"
        self.audit = {**copy.deepcopy(self.original_audit),
                      **{k: self.evidence[k] for k in
                         ("proposal", "review_manifest", "source_frames", "source_timing")}}

    def validate(self, audit=None):
        path = self.folder / f"audit_{len(list(self.folder.glob('audit_*.json')))}.json"
        write_new(path, self.audit if audit is None else audit)
        audit_binding = binding(self.root, path)
        self.result["integration_audit"] = self.evidence["integration_audit"] = audit_binding
        _validate_focused_test_scope(self.root, self.result, self.evidence, 120, 96)

    def test_explicit_unchanged_implementation_scope_uses_current_bound_audit(self):
        self.validate()
        self.assertNotEqual(self.evidence["proposal"],
                            read_json(self.root / self.evidence["focused_tests"]["path"])["actual_proposal"])

    def test_prior_scope_rejects_missing_incomplete_or_other_batch_audit(self):
        variants = [{}, {**self.audit, "status": "failed"}]
        for key in ("source_annotation_native_joins", "encoded_frames_checked", "encoded_markers_checked"):
            variants.append({**self.audit, key: self.audit[key] - 1})
        for key in ("proposal", "review_manifest", "source_frames", "source_timing"):
            changed = copy.deepcopy(self.audit)
            del changed[key]
            variants.append(changed)
        variants.append({**self.audit, "proposal": self.original_evidence["proposal"]})
        for number, audit in enumerate(variants):
            with self.subTest(case=number), self.assertRaisesRegex(ValueError, "Current integration audit"):
                self.validate(audit)
        self.result.pop("integration_audit", None)
        with self.assertRaisesRegex(ValueError, "current integration audit"):
            _validate_focused_test_scope(self.root, self.result, self.evidence, 120, 96)

    def test_prior_scope_rejects_changed_renderer_or_test_source(self):
        for key in ("implementation", "tests"):
            original = self.result[key]
            self.result[key] = {**original, "sha256": "0" * 64}
            with self.subTest(field=key), self.assertRaisesRegex(ValueError, "unchanged producer/test"):
                self.validate()
            self.result[key] = original

    def test_default_or_claimed_current_scope_still_requires_current_proposal(self):
        for scope in (None, "current_proposal", "unrecognized_scope"):
            if scope is None:
                self.result.pop("focused_tests_scope", None)
            else:
                self.result["focused_tests_scope"] = scope
            with self.subTest(scope=scope), self.assertRaises(ValueError):
                self.validate()


if __name__ == "__main__":
    unittest.main()
