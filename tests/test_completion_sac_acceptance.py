"""SAC acceptance transport and mixed-inventory regressions.

Actual completed NBA19 producer records are required for the integration class.
Missing local artifacts are explicit skips, never evidence of completed review.
Temporary test-only publications do not publish campaign acceptance or decode
pixels. Legacy routing fixtures come from actual accepted NBA01 records.
"""
import copy
from fractions import Fraction
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from src.ball_tracking.completion_references import binding, read_json, write_new
from src.ball_tracking import completion_sac_acceptance as sac


ROOT = Path(__file__).resolve().parents[1]
TEST_PARENT = ROOT / "data/outputs/t"


def legacy_entry():
    path = ROOT / "configs/ball_tracking/reviews/nba_completion_reference_batch_01_acceptance_v0_1.json"
    if not path.is_file():
        raise unittest.SkipTest("Actual legacy NBA01 acceptance unavailable")
    receipt = read_json(path)
    entry = {**receipt["accepted_reference"], "acceptance_receipt": binding(ROOT, path)}
    if not (ROOT / entry["path"]).is_file():
        raise unittest.SkipTest("Actual ignored legacy publication unavailable")
    return entry


class AcceptanceContractTests(unittest.TestCase):
    def test_explicit_human_statement_and_assisted_provenance_are_required(self):
        valid = {"status": "accepted", "reviewer_id": "test-only",
                 "review_method": "human_visual_acceptance_of_assisted_proposals",
                 "user_statement": "Test-only acceptance, never campaign publication",
                 "response_context": "Isolated contract test",
                 "exact_user_event_timestamp_utc": None,
                 "playback_telemetry_claimed": False,
                 "independent_human_annotation_claimed": False}
        sac._human_review(valid)
        for field in ("user_statement", "response_context", "exact_user_event_timestamp_utc"):
            changed = copy.deepcopy(valid)
            del changed[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                sac._human_review(changed)
        for field in ("playback_telemetry_claimed", "independent_human_annotation_claimed"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                sac._human_review({**valid, field: True})

    def test_accepted_label_flags_cannot_open_fitting_or_protected_access(self):
        for role in ("training", "checkpoint_validation"):
            doc = {"role": role, "training_eligible": role == "training",
                   "checkpoint_selection_eligible": role == "checkpoint_validation",
                   "eligibility_scope": "accepted_reference_labels_only",
                   **{key: False for key in sac._NOT_READY}}
            sac._accepted_flags(doc)
            for key in (*sac._NOT_READY, "training_eligible", "checkpoint_selection_eligible"):
                with self.subTest(role=role, field=key), self.assertRaisesRegex(ValueError, "eligibility"):
                    sac._accepted_flags({**doc, key: not doc[key]})

    def test_actual_legacy_publication_routes_to_unchanged_reader(self):
        entry = legacy_entry()
        actual, authorities = sac.accepted_nba_inventory(ROOT, [entry])
        publication = read_json(ROOT / entry["path"])
        self.assertEqual(len(actual), publication["accepted_references"])
        self.assertEqual(authorities, [binding(ROOT, ROOT / entry["path"]), entry["acceptance_receipt"]])
        key = (publication["game_id"], publication["source_metadata"]["sha256"],
               publication["annotations"][0]["frame_index"])
        self.assertEqual(actual[key]["annotation"], publication["annotations"][0])

    def test_unified_duplicate_guard_spans_both_schema_routes(self):
        # Routing-only test: both mocked validators return one actual legacy row.
        # This deliberately does not claim the stub SAC document is valid evidence.
        entry = legacy_entry()
        doc = read_json(ROOT / entry["path"])
        doc["annotations"] = doc["annotations"][:1]
        TEST_PARENT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="sac_route_", dir=TEST_PARENT) as name:
            folder = Path(name).resolve()
            self.assertTrue(folder.is_relative_to(TEST_PARENT.resolve()))
            stub = folder / "routing_only.json"
            write_new(stub, {"schema_version": "completion_sac_reference_accepted/v0.1"})
            with mock.patch.object(sac, "_legacy_accepted_reference", return_value=(doc, [])) as legacy, \
                    mock.patch.object(sac, "accepted_sac_reference", return_value=(doc, [])) as current:
                with self.assertRaisesRegex(ValueError, "Duplicate"):
                    sac.accepted_nba_inventory(ROOT, [entry, binding(ROOT, stub)])
                legacy.assert_called_once()
                current.assert_called_once()
            unknown = folder / "unknown.json"
            write_new(unknown, {"schema_version": "unsupported"})
            with self.assertRaisesRegex(ValueError, "Unknown accepted"):
                sac.accepted_nba_inventory(ROOT, [binding(ROOT, unknown)])


class ActualSACAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ROOT
        path = Path(os.environ.get("SAC_REFERENCE_RESULT", str(ROOT /
            "configs/ball_tracking/reviews/nba_completion_reference_batch_19_result_v0_1.json")))
        if not path.is_file():
            raise unittest.SkipTest("Actual completed SAC result unavailable; review evidence remains incomplete")
        result = read_json(path)
        if not (ROOT / result["review_manifest"]["path"]).is_file():
            raise unittest.SkipTest("Actual emitted SAC review manifest unavailable")
        cls.result_binding = binding(ROOT, path)
        cls.result = result
        cls.actual = sac.reviewed_sac_evidence(ROOT, cls.result_binding)
        cls.review = {"status": "accepted", "reviewer_id": "TEST_ONLY_DO_NOT_PUBLISH",
            "review_method": "human_visual_acceptance_of_assisted_proposals",
            "user_statement": "Synthetic test-only acceptance for isolated transport checks",
            "response_context": "Does not represent Ryan acceptance or a campaign publication",
            "exact_user_event_timestamp_utc": None, "playback_telemetry_claimed": False,
            "independent_human_annotation_claimed": False}
        # Reuse the already validated actual producer read for in-memory construction.
        with mock.patch.object(sac, "reviewed_sac_evidence", return_value=cls.actual):
            cls.doc = sac.build_accepted_reference(ROOT, cls.result_binding, cls.review,
                                                  "data/outputs/t/test-only-sac-receipt.json")

    def test_actual_native_presentation_timing_and_uncertainty_survive_transport(self):
        data = self.actual
        proposal = read_json(ROOT / data["evidence"]["proposal"]["path"])
        timing = read_json(ROOT / data["evidence"]["source_timing"]["path"])
        self.assertEqual(data["annotations"], proposal["annotations"])
        self.assertEqual([f["native_pts_ticks"] for f in data["frames"]],
                         [f["native_pts_ticks"] for f in timing])
        self.assertEqual({f["presentation_duration_ticks"] for f in data["frames"]}, {1440, 1530})
        self.assertTrue(any(f["presentation_duration_ticks"] != f["raw_packet_duration_ticks"]
                            for f in data["frames"]))
        native, slow = data["review_videos"]
        self.assertIsNone(native["fps"])
        self.assertEqual(native["timing_mode"], "native_vfr")
        duration = sum(f["presentation_duration_ticks"] for f in data["frames"]) * Fraction(data["source_metadata"]["time_base"])
        self.assertAlmostEqual(native["duration_seconds"], float(duration), places=9)
        self.assertEqual(slow["timing_mode"], "cfr")
        self.assertAlmostEqual(slow["duration_seconds"], len(data["annotations"]) / 10, places=9)
        self.assertEqual(data["accepted_null_centers"], sum(r["geometry"] is None for r in proposal["annotations"]))

    def test_rejects_changed_annotation_timing_identity_or_scope(self):
        # Actual evidence was independently validated in setUpClass; patching only
        # avoids repeatedly hashing full videos for each single-field corruption.
        for field in ("center", "uncertainty", "null", "pts", "duration", "raw_duration", "source", "role"):
            changed = copy.deepcopy(self.doc)
            first_center = next(r for r in changed["annotations"] if r["geometry"] is not None)
            if field == "center":
                first_center["geometry"]["center_xy_px"][0] += 1
            elif field == "uncertainty":
                first_center["geometry"]["uncertainty_radius_px"] += 1
            elif field == "null":
                first_center["geometry"] = None
            elif field in ("pts", "duration", "raw_duration"):
                key = {"pts": "native_pts_ticks", "duration": "presentation_duration_ticks",
                       "raw_duration": "raw_packet_duration_ticks"}[field]
                changed["frames"][0][key] = -1
            elif field == "source":
                changed["source_metadata"]["sha256"] = "0" * 64
            else:
                changed.update(role="checkpoint_validation", training_eligible=False, checkpoint_selection_eligible=True)
            with self.subTest(field=field), mock.patch.object(sac, "reviewed_sac_evidence", return_value=self.actual), \
                    self.assertRaisesRegex(ValueError, "Accepted annotations"):
                sac.validate_accepted_record(ROOT, changed)

    def test_result_binding_and_current_proposal_test_scope_are_strict(self):
        with self.assertRaisesRegex(ValueError, "binding changed"):
            sac.reviewed_sac_evidence(ROOT, {**self.result_binding, "sha256": "0" * 64})
        evidence = copy.deepcopy(self.actual["evidence"])
        evidence["proposal"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Current-proposal"):
            sac._validate_focused_test_scope(ROOT, {**self.result, "focused_tests_scope": "current_proposal"},
                                            evidence, len(self.actual["annotations"]), self.actual["accepted_eligible_centers"])

    def test_actual_serialized_sac_pair_and_legacy_inventory_coexist(self):
        TEST_PARENT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="sac_acceptance_test_only_", dir=TEST_PARENT) as name:
            folder = Path(name).resolve()
            self.assertTrue(folder.is_relative_to(TEST_PARENT.resolve()))
            publication, receipt_path = folder / "reference.json", folder / "receipt.json"
            doc = copy.deepcopy(self.doc)
            doc["acceptance_receipt_path"] = receipt_path.relative_to(ROOT).as_posix()
            write_new(publication, doc)
            pub = binding(ROOT, publication)
            receipt = sac.acceptance_receipt(doc, pub)
            write_new(receipt_path, receipt)
            entry = {**pub, "acceptance_receipt": binding(ROOT, receipt_path)}
            legacy = legacy_entry()
            actual, authorities = sac.accepted_nba_inventory(ROOT, [legacy, entry])
            legacy_count = read_json(ROOT / legacy["path"])["accepted_references"]
            self.assertEqual(len(actual), legacy_count + len(doc["annotations"]))
            self.assertEqual(len(authorities), 4)
            key = (doc["game_id"], doc["source_metadata"]["sha256"], doc["annotations"][0]["frame_index"])
            self.assertTrue(actual[key]["training_eligible"])
            self.assertFalse(actual[key]["checkpoint_selection_eligible"])
            wrong = copy.deepcopy(receipt)
            wrong["human_review"]["user_statement"] = "Different test statement"
            wrong_path = folder / "wrong_receipt.json"
            write_new(wrong_path, wrong)
            with self.assertRaisesRegex(ValueError, "receipt links/content"):
                sac.accepted_sac_reference(ROOT, {**entry, "acceptance_receipt": binding(ROOT, wrong_path)})


if __name__ == "__main__":
    unittest.main()
