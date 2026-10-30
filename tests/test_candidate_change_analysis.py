"""Captured producer transport and synthetic comparison contracts; no model work."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from src.ball_tracking import candidate_change_analysis as analysis


def choice(point, correct="matched", *, category="eligible", native=True, values=None):
    emitted = point is not None
    features = dict.fromkeys(analysis.FEATURES, 0.5 if emitted else None)
    features.update(values or {})
    return {"state": "observed" if emitted else "missing", "center_xy_px": point,
            "candidate_identity": ["native", 0] if native and emitted else ["weak", 1] if emitted else None,
            "native_index": 0 if native and emitted else None,
            "features": features, "feature_unknown_reasons": {k: "missing_selection" for k, v in features.items() if v is None},
            "reference_category": category, "outcome": correct if category == "eligible" else "unscored",
            "extraction": "native_component" if native else "threshold_component", "geometry_status": "complete_source_crop"}


class CandidateChangeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads((Path(__file__).parent / "fixtures/ball_tracking_candidate_change_transport_v0_1.json").read_text())["cases"]

    def test_four_actual_producer_rows_match_saved_scorer(self):
        for captured in self.cases:
            with self.subTest(captured["label"]):
                row = analysis.transport_choice(**{k: captured[k] for k in
                    ("block", "frame", "native", "observation", "query", "score", "descriptor", "pool")})
                saved = captured["expected_saved_score"]
                self.assertEqual(row["outcome"], saved["outcome"])
                self.assertEqual(row["center_xy_px"], saved["automatic_center_xy_px"])
                self.assertEqual(row["reference_category"], saved["reference_category"])
                if row["localization_distance_px"] is not None:
                    self.assertAlmostEqual(row["localization_distance_px"], saved["raw_center_error_px"])

    def test_actual_query_clock_source_coordinate_and_candidate_tampering(self):
        original = self.cases[0]
        for kind in ("pts", "source", "png", "coordinate", "candidate"):
            c = deepcopy(original)
            if kind == "pts": c["query"]["source_pts_ticks"] += 1
            if kind == "source": c["query"]["source_video"]["sha256"] = "wrong"
            if kind == "png": c["observation"]["source_png"]["sha256"] = "wrong"
            if kind == "coordinate": c["query"]["center_xy_px"][0] += .001
            if kind == "candidate": c["query"]["candidate"]["candidate_index"] += 1
            with self.subTest(kind), self.assertRaises(ValueError):
                analysis.transport_choice(**{k: c[k] for k in
                    ("block", "frame", "native", "observation", "query", "score", "descriptor", "pool")})

    def test_inclusive_ten_pixels_and_out_of_bounds(self):
        self.assertEqual(analysis.outcome([10, 0], [0, 0], 20, 20)[0], "matched")
        self.assertEqual(analysis.outcome([10.0000001, 0], [0, 0], 20, 20)[0], "wrong")
        self.assertEqual(analysis.outcome([-1, 0], [0, 0], 20, 20)[0], "wrong")
        self.assertEqual(analysis.outcome(None, [0, 0], 20, 20), ("missing", None))
        self.assertEqual(analysis.outcome([1, 2], None, 20, 20), ("unscored", None))

    def test_all_missing_state_partitions_and_no_null_image_scores(self):
        present = choice([1, 2])
        missing = choice(None, "missing")
        combinations = [(present, present), (present, choice([2, 3])), (present, missing), (missing, present), (missing, missing)]
        for (a, b), expected in zip(combinations, analysis.STATES):
            row = analysis.compare_choices(a, b)
            self.assertEqual(row["choice_state"], expected)
            if not expected.startswith("both_observed"):
                self.assertTrue(all(x["delta_target_minus_source"] is None and x["preference"] == "unavailable" for x in row["features"].values()))

    def test_same_coordinate_distinct_identity_and_same_input_distinct_queries(self):
        a, b = choice([1, 2]), choice([1, 2], native=False)
        result = analysis.compare_choices(a, b)
        self.assertTrue(result["coordinate_agreement"])
        self.assertFalse(result["candidate_identity_agreement"])
        self.assertFalse(result["exactly_one_correct_observed_pair"])
        b["center_xy_px"] = [1.1, 2]
        a["input_id"] = b["input_id"] = "same_input_crop"
        a["query_id"], b["query_id"] = "a", "b"
        a["outcome"], b["outcome"] = "wrong", "matched"
        b["features"]["point"] = .7
        self.assertEqual(analysis.compare_choices(a, b)["features"]["point"]["correct_side_status"], "correct_side")

    def test_strict_preferences_ties_adverse_and_unknowns(self):
        a = choice([1, 2], "wrong", values={"point": .6, "cls": .5, "peak": .4})
        b = choice([3, 4], "matched", values={"point": .2, "cls": .5, "peak": None})
        b["feature_unknown_reasons"]["peak"] = "boundary_unknown"
        row = analysis.compare_choices(a, b)
        self.assertEqual(row["features"]["point"]["correct_side_status"], "wrong_side")
        self.assertEqual(row["features"]["cls"]["correct_side_status"], "tie")
        self.assertEqual(row["features"]["peak"]["correct_side_status"], "unavailable")
        b["features"]["cls"] = .5000000000000001
        self.assertEqual(analysis.compare_choices(a, b)["features"]["cls"]["preference"], "target")

    def test_hidden_and_unknown_never_count_as_correct_side(self):
        for category in ("certain_hidden", "uncertain_hidden", "indeterminate", "visible_unlocalizable"):
            a, b = choice([1, 2], category=category), choice([3, 4], category=category, values={"point": .9})
            row = analysis.compare_choices(a, b)
            self.assertFalse(row["exactly_one_correct_observed_pair"])
            self.assertEqual(row["features"]["point"]["correct_side_status"], "not_discrimination_pair")
            if category == "certain_hidden": self.assertEqual(row["visibility_interpretation"], "neither_emission_valid")

    def test_native_mass_does_not_compare_weak_extraction(self):
        captured = self.cases[1]
        row = analysis.transport_choice(**{k: captured[k] for k in
            ("block", "frame", "native", "observation", "query", "score", "descriptor", "pool")})
        self.assertIsNone(row["features"]["native_mass"])
        self.assertEqual(row["feature_unknown_reasons"]["native_mass"], "incomparable_nonnative_extraction")

    def test_summary_full_matrix_and_complete_pair_denominators(self):
        rows = []
        for a in analysis.OUTCOMES:
            for b in analysis.OUTCOMES:
                ca = choice(None if a == "missing" else [1, 2], a)
                cb = choice(None if b == "missing" else [3, 4], b, values={"point": .6 if b != "missing" else None})
                rows.append(analysis.compare_choices(ca, cb))
        result = analysis.summarize(rows)
        self.assertEqual(result["declared_rows"], 9)
        self.assertEqual(set(result["eligible_transition_matrix"].values()), {1})
        self.assertEqual(result["two_observed"], 4)
        self.assertEqual(result["exactly_one_correct_pairs"], 2)
        self.assertEqual(result["features"]["point"]["unavailable_rows_including_missing"], 5)
        self.assertEqual(result["features"]["point"]["exactly_one_correct"], {"correct_side": 1, "wrong_side": 1})

    def test_duplicate_rows_rejected_instead_of_silently_overwritten(self):
        with self.assertRaises(ValueError): analysis.indexed([{"i": 1}, {"i": 1}], ("i",))

    def test_reader_binding_tamper_and_repository_escape(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "record.json"; path.write_text('{"x":1}')
            reader = analysis.Reader(root)
            link = analysis.bind(path, root)
            self.assertEqual(reader.json(link), {"x": 1})
            link["sha256"] = "bad"
            with self.assertRaises(ValueError): reader.json(link)
            with self.assertRaises(ValueError): reader.data({"path": "../escape.json"})


if __name__ == "__main__":
    unittest.main()
