"""CPU transport/diagnostic tests using previously captured producer records."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from src.ball_tracking import candidate_change_analysis as producer
from src.ball_tracking import candidate_quality_evaluation as quality


class QualityEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads((Path(__file__).parent / "fixtures/ball_tracking_candidate_change_transport_v0_1.json").read_text())["cases"]

    def captured_choice(self, index=0):
        captured = self.cases[index]
        return producer.transport_choice(**{k: captured[k] for k in
            ("block", "frame", "native", "observation", "query", "score", "descriptor", "pool")})

    def contrast(self, a, b):
        return {"row_id": "captured-pair", "contrast": "native__to__weak", "role": "primary",
                "block_id": self.cases[0]["query"]["block_id"], "frame": self.cases[0]["query"]["source_frame_index"],
                "tags": ["all842_native_correct"], "source_choice": a, "target_choice": b,
                **producer.compare_choices(a, b)}

    def test_actual_captured_observed_queries_roundtrip(self):
        for captured in self.cases:
            q = captured["query"]
            if q is not None and q["input_id"] is not None:
                got = quality.validate_logits([q], [{"query_id": q["query_id"], "quality_logit": 0.25}])
                self.assertEqual(got, {q["query_id"]: 0.25})

    def test_no_missing_extra_duplicate_or_nonfinite_predictions(self):
        q = self.cases[0]["query"]
        valid = {"query_id": q["query_id"], "quality_logit": 1.0}
        bad = [[], [valid, valid], [valid, {"query_id": "extra", "quality_logit": 1.0}]]
        for score in (float("nan"), float("inf"), -float("inf"), None, True, "1"):
            bad.append([dict(valid, quality_logit=score)])
        for rows in bad:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                quality.validate_logits([q], rows)

    def test_missing_query_has_no_image_prediction(self):
        q = deepcopy(self.cases[0]["query"])
        q["input_id"] = None
        self.assertEqual(quality.validate_logits([q], []), {})
        with self.assertRaises(ValueError):
            quality.validate_logits([q], [{"query_id": q["query_id"], "quality_logit": 0}])

    def test_shared_crop_never_collapses_distinct_point_queries(self):
        q = deepcopy(self.cases[0]["query"])
        other = deepcopy(q)
        other["query_id"] += ":distinct-point"
        scores = quality.validate_logits([q, other], [
            {"query_id": q["query_id"], "quality_logit": 1},
            {"query_id": other["query_id"], "quality_logit": -1}])
        self.assertEqual(len(scores), 2)
        self.assertNotEqual(scores[q["query_id"]], scores[other["query_id"]])

    def test_actual_choice_transport_keeps_old_scores_separate(self):
        a = self.captured_choice()
        scores = {a["query_id"]: -.2}
        row = quality.score_contrasts([self.contrast(a, a)], scores)[0]
        self.assertEqual(row["source_quality"]["image_quality_logit"], -.2)
        self.assertEqual(row["baseline_features"]["point"]["delta_target_minus_source"], 0)
        self.assertEqual(row["preference"], "tie")
        self.assertFalse(row["exactly_one_successful_old_choice"])

    def test_good_location_compares_to_fixed_reject_not_fake_image(self):
        a = self.captured_choice()
        missing = deepcopy(a)
        missing.update(state="missing", center_xy_px=None, outcome="missing", candidate_identity=None)
        row = quality.score_contrasts([self.contrast(missing, a)], {a["query_id"]: .5})[0]
        self.assertIsNone(row["source_quality"]["image_quality_logit"])
        self.assertEqual(row["source_quality"]["comparison_value"], 0)
        self.assertEqual(row["correct_side_status"], "correct_side")
        row = quality.score_contrasts([self.contrast(missing, a)], {a["query_id"]: -.5})[0]
        self.assertEqual(row["correct_side_status"], "wrong_side")

    def test_certain_hidden_rejection_and_unknown_are_different(self):
        a = self.captured_choice()
        a.update(reference_category="certain_hidden", outcome="unscored")
        missing = deepcopy(a)
        missing.update(state="missing", center_xy_px=None, candidate_identity=None)
        row = quality.score_contrasts([self.contrast(a, missing)], {a["query_id"]: -.5})[0]
        self.assertEqual(row["correct_side_status"], "correct_side")
        for category in ("indeterminate", "uncertain_hidden", "visible_unlocalizable"):
            a["reference_category"] = missing["reference_category"] = category
            row = quality.score_contrasts([self.contrast(a, missing)], {a["query_id"]: -.5})[0]
            self.assertFalse(row["exactly_one_successful_old_choice"])
            self.assertEqual(row["correct_side_status"], "not_discrimination_pair")

    def test_both_missing_remain_non_discriminating(self):
        a = self.captured_choice()
        a.update(state="missing", center_xy_px=None, outcome="missing", candidate_identity=None)
        row = quality.score_contrasts([self.contrast(a, a)], {})[0]
        self.assertEqual(row["choice_state"], "both_missing")
        self.assertEqual(row["preference"], "tie")
        self.assertFalse(row["exactly_one_successful_old_choice"])
        self.assertIsNone(row["target_quality"]["image_quality_logit"])

    def test_curve_ties_strict_zero_frame_rejection_and_unknowns(self):
        rows = []
        for identity, frame, category, target in [("native", 1, "eligible", 1), ("weak", 1, "eligible", 1),
                ("miss", 1, "eligible", 0), ("hidden1", 2, "certain_hidden", 0),
                ("hidden2", 2, "certain_hidden", 0), ("unknown", 3, "uncertain_hidden", None)]:
            rows.append({"query_id": identity, "block_id": "source", "frame": frame,
                         "reference_category": category, "quality_target": target, "missing": False,
                         "native": identity == "native", "is_native_selected": identity == "native"})
        logits = {"native": 1.0, "weak": 0.0, "miss": -1.0, "hidden1": -1.0, "hidden2": .5, "unknown": 1.0}
        curve = quality.diagnostic_curve(rows, logits)
        at_zero = next(row for row in curve if row["threshold"] == 0)
        self.assertEqual(at_zero["retained_candidates"]["matching"], 1)
        self.assertEqual(at_zero["retained_candidates"]["unknown"], 1)
        self.assertEqual(at_zero["retained_candidates"]["certain_hidden"], 1)
        self.assertEqual(at_zero["certain_hidden_frames_with_survivors"], 1)
        self.assertEqual(curve[0]["retained_candidates"]["certain_hidden"], 2)
        self.assertEqual(curve[0]["certain_hidden_frames_with_survivors"], 1)
        self.assertEqual(curve[-1]["retained_candidates"]["all_candidates"], 0)
        self.assertEqual(curve[-1]["certain_hidden_frames_with_survivors"], 0)
        self.assertEqual(len([r for r in curve if r["threshold"] == -1]), 1)

    def test_module_does_not_import_torch(self):
        # Other tests may legitimately import Torch; check this module's own
        # import behavior in an isolated interpreter instead of global suite state.
        result = subprocess.run([sys.executable, "-B", "-c",
            "import sys; from src.ball_tracking import candidate_quality_evaluation; assert 'torch' not in sys.modules"],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
