"""Small synthetic acceptance checks, independent of experiment populations."""
import copy
import math
import unittest

from src.ball_tracking import candidate_acceptance_evaluation as evaluate


def point(key, category, q, s=None, j=None, m=None, *, frame=None,
          context="nba_out_of_fold", cohort="package", policy=None, game="CHI", **extra):
    return {"row_key": key, "candidate_id": key, "query_id": None,
            "frame_key": frame or key + "_frame", "fit": "base", "game_id": game,
            "block_id": game + "_block", "source_frame_index": 3,
            "context": context, "cohort": cohort, "policy": policy,
            "evaluation_category": category, "target_group": category,
            "selected_native": False, "native_or_weak": "native", "difficulty_tags": [],
            "scores": {"Q": q, "S": q if s is None else s, "J": q if j is None else j,
                       "M": q if m is None else m}, **extra}


def frame(key):
    return {"frame_key": key, "context": "nba_out_of_fold", "fit": "base", "game_id": "CHI",
            "block_id": "block", "source_frame_index": 3}


def decision_fixture(improve=True):
    policies = []
    for game in ("CHI", "DEN", "SAC"):
        for policy in ("native", "quality_top"):
            prefix = game + "|" + policy
            policies.extend([
                point(prefix + "|right", "eligible_match", 1, policy=policy, game=game, cohort="fixed_policy"),
                point(prefix + "|wrong", "eligible_miss", 1, j=-1 if improve else 1,
                      policy=policy, game=game, cohort="fixed_policy"),
                point(prefix + "|hidden", "certain_hidden", 1, j=-1 if improve else 1,
                      policy=policy, game=game, cohort="fixed_policy"),
            ])
    for policy in ("native", "quality_top"):
        policies.append(point("HOU|" + policy, "eligible_match", 1, policy=policy, game="HOU",
                              context="HOU_development", cohort="fixed_policy", frame="protected"))
        policies.append(point("HOU|hidden|" + policy, "certain_hidden", -1, policy=policy, game="HOU",
                              context="HOU_development", cohort="fixed_policy", frame="hidden"))
    candidates = [point("stress_correct", "eligible_match", 1, context="HOU_development",
                        cohort="HOU_stress", frame="protected", game="HOU"),
                  point("unselected_alternative", "eligible_match", 1, j=-1,
                        context="HOU_development", cohort="HOU_main", frame="protected", game="HOU")]
    cases = {"named_groups": {"recovery": {"frame_keys": ["protected"]}, "other": {"frame_keys": []}}}
    return policies, candidates, cases


class CandidateAcceptanceEvaluationTests(unittest.TestCase):
    def test_strict_zero_distinct_hidden_frames_unknowns_and_missing_are_separate(self):
        rows = [point("m1", "eligible_match", 3, frame="match"),
                point("m2", "eligible_match", 1, frame="match"),
                point("m0", "eligible_match", 0), point("w", "eligible_miss", 2),
                point("h1", "certain_hidden", 2, frame="held|same_source_frame"),
                point("h2", "certain_hidden", 1, frame="held|same_source_frame"),
                point("h3", "certain_hidden", 1, frame="other_fit|same_source_frame"),
                point("u", "masked_unknown", 1), point("b", "boundary_unknown", -1),
                point("old", "historical", 1, frame=None, cohort="historical"),
                point("missing", "eligible_match", None)]
        result = evaluate.aggregate(rows, "J")
        self.assertEqual(result["denominator"], 11)
        self.assertEqual(result["counts"], {"accepted": 8, "correct_kept": 2,
            "wrong_eligible_kept": 1, "hidden_candidates": 3, "hidden_emission_frames": 2,
            "match_survival_frames": 1, "unknown_kept": 1, "historical_kept": 1})
        self.assertEqual(result["correct_rejected"], 2)
        self.assertEqual(result["score_states"], {"positive": 8, "negative": 1, "zero": 1, "missing": 1})
        self.assertTrue(result["unknown_not_counted_as_errors"])

    def test_exact_tie_curves_match_hand_counts_and_direct_aggregation(self):
        rows = [point("match", "eligible_match", 2, frame="m"),
                point("hidden1", "certain_hidden", 2, frame="h"),
                point("hidden2", "certain_hidden", 1, frame="h"),
                point("wrong", "eligible_miss", 1), point("unknown", "masked_unknown", 0),
                point("history", "historical", -1), point("missing", "eligible_match", None)]
        result = evaluate.curve(rows, "Q")
        expected = {
            2: [0, 0, 0, 0, 0, 0, 0, 0],
            1: [2, 1, 0, 1, 1, 1, 0, 0],
            0: [4, 1, 1, 2, 1, 1, 0, 0],
            -1: [5, 1, 1, 2, 1, 1, 1, 0],
        }
        thresholds = [p for p in result["points"] if p["kind"] == "threshold"]
        self.assertEqual([p["threshold"] for p in thresholds], [2, 1, 0, -1])
        self.assertEqual([p["tied_candidates"] for p in thresholds], [2, 2, 1, 1])
        for step in thresholds:
            self.assertEqual(step["counts"], expected[step["threshold"]])
            direct = evaluate.aggregate(rows, "Q", step["threshold"])["counts"]
            self.assertEqual(step["counts"], [direct[key] for key in evaluate.MEASURES])
        self.assertEqual(result["points"][-1]["counts"], [6, 1, 1, 2, 1, 1, 1, 1])
        self.assertEqual(result["observed_scores"], 6)
        self.assertEqual(result["missing_scores"], 1)
        self.assertIsNone(result["threshold_chosen"])
        self.assertTrue(result["descriptive_only"])
        self.assertEqual(evaluate.curve(list(reversed(rows)), "Q"), result)

    def test_all_missing_empty_and_constant_score_curves_do_not_invent_values(self):
        for rows in ([], [point("missing", "unknown", None)]):
            result = evaluate.curve(rows, "J")
            self.assertEqual(result["observed_scores"], 0)
            self.assertEqual(len(result["points"]), 2)
            self.assertTrue(all(p["counts"] == [0] * 8 for p in result["points"]))
        constant = evaluate.curve([point("a", "eligible_match", 0), point("b", "eligible_miss", 0)], "S")
        self.assertEqual(len(constant["points"]), 3)
        self.assertEqual(constant["points"][1]["tied_candidates"], 2)
        self.assertEqual(constant["points"][1]["counts"], [0] * 8)
        self.assertEqual(constant["points"][2]["counts"][0], 2)

    def test_policies_keep_original_choices_after_rejection_without_reranking(self):
        native = point("native", "eligible_miss", 1, j=-3, frame="f", selected_native=True)
        top = point("a_top", "eligible_match", 3, j=-1, frame="f", native_or_weak="weak")
        tied = point("b_top", "eligible_match", 3, j=99, frame="f", native_or_weak="weak")
        stress = point("stress", "eligible_match", 100, j=100, frame="f", cohort="HOU_stress")
        rows = evaluate.policy_rows([frame("f"), frame("empty")], [tied, stress, native, top])
        native_row, quality_row, missing_native, missing_top = rows
        self.assertEqual(native_row["chosen_row_key"], "native")
        self.assertEqual(quality_row["chosen_row_key"], "a_top")
        self.assertEqual(quality_row["quality_top_tied_row_keys"], ["a_top", "b_top"])
        self.assertEqual(quality_row["original_pool_count"], 3)
        self.assertEqual(evaluate.aggregate(rows, "J")["counts"]["accepted"], 0)
        for row in rows:
            self.assertFalse(row["fallback_allowed"])
            self.assertTrue(row["point_chosen_before_acceptance"])
        for row in (missing_native, missing_top):
            self.assertIsNone(row["chosen_row_key"])
            self.assertEqual(row["evaluation_category"], "missing_choice")
            self.assertEqual(row["scores"], dict.fromkeys(evaluate.ARMS))
        quality_row["scores"]["J"] = 77
        self.assertEqual(top["scores"]["J"], -1)
        with self.assertRaisesRegex(ValueError, "Multiple original native"):
            evaluate.policy_rows([frame("f")], [native, {**top, "selected_native": True}])

    def test_pair_diagnostics_are_exact_at_zero_and_preserve_missing(self):
        rows = [point("r", "eligible_match", 1, s=-1, j=0),
                point("a", "eligible_miss", -1, s=1, j=1), point("m", "unknown", None)]
        paired = list(evaluate.paired_policy_rows(rows))
        self.assertEqual([(p["J_vs_Q"], p["J_vs_S"]) for p in paired],
                         [("new_reject", "agreement"), ("new_accept", "agreement"), ("agreement", "agreement")])
        self.assertFalse(any(paired[-1]["accepted_at_zero"].values()))
        self.assertEqual(paired[-1]["scores"], dict.fromkeys(evaluate.ARMS))

    def test_numeric_radius_canonicalization_multitag_and_fallback_populations(self):
        a = point("a", "eligible_match", 1, recorded_uncertainty_radius_px=3,
                  difficulty_tags=["blur", "overlap", "blur"], M_no_rival_fallback=True)
        b = point("b", "eligible_miss", -1, recorded_uncertainty_radius_px=3.0,
                  difficulty_tags=["blur"], M_no_rival_fallback=False)
        c = point("c", "unknown", None, recorded_uncertainty_radius_px=None, M_no_rival_fallback=None)
        self.assertEqual(evaluate.token({"radius": 3}), evaluate.token({"radius": 3.0}))
        groups = list(evaluate.zero_tables([a, b, c]))
        radius = [r for r in groups if r["scope"] == "context" and r["family"] == "uncertainty_radius"
                  and r["value"] == 3 and r["arm"] == "Q"]
        self.assertEqual(len(radius), 1)
        self.assertEqual(radius[0]["denominator"], 2)
        blur = [r for r in groups if r["scope"] == "context" and r["family"] == "difficulty_tag"
                and r["value"] == "blur" and r["arm"] == "Q"]
        self.assertEqual(blur[0]["denominator"], 2)
        fallback = [r for r in evaluate.curves([a, b, c]) if r["scope"] == "M_fallback_inventory"]
        self.assertEqual({r["fallback"]: r["denominator"] for r in fallback}, {False: 1, True: 1, None: 1})

    def test_decision_requires_every_game_policy_and_both_comparators_plus_strict_gain(self):
        policies, candidates, cases = decision_fixture()
        result = evaluate.decide(policies, candidates, cases)
        self.assertTrue(result["fixed_reference_component_criterion_passed"])
        self.assertEqual(len(result["NBA_checks"]), 36)
        self.assertFalse(result["model_adopted"])
        self.assertFalse(result["tracker_complete"])
        self.assertIsNone(result["selected_threshold"])
        equal_policies, equal_candidates, equal_cases = decision_fixture(improve=False)
        self.assertFalse(evaluate.decide(equal_policies, equal_candidates, equal_cases)["fixed_reference_component_criterion_passed"])
        self.assertEqual(evaluate.decide(equal_policies, equal_candidates, equal_cases)["strict_improvements"], [])
        for changed_key, category, changes in (
            ("SAC|native|right", "eligible_match", {"J": 0}),
            ("DEN|quality_top|wrong", "eligible_miss", {"Q": -1, "S": -1, "J": 1}),
            ("CHI|native|hidden", "certain_hidden", {"Q": -1, "S": -1, "J": 1}),
            ("CHI|quality_top|wrong", "eligible_miss", {"Q": 1, "S": -1, "J": 1}),
        ):
            with self.subTest(key=changed_key, changes=changes):
                changed = copy.deepcopy(policies)
                next(r for r in changed if r["row_key"] == changed_key)["scores"].update(changes)
                outcome = evaluate.decide(changed, candidates, cases)
                self.assertFalse(outcome["fixed_reference_component_criterion_passed"])
                self.assertTrue(any(not r["passed"] for r in outcome["NBA_checks"]))

    def test_hou_protects_chosen_successes_and_exact_stress_but_not_unselected_alternatives(self):
        policies, candidates, cases = decision_fixture()
        result = evaluate.decide(policies, candidates, cases)
        self.assertEqual(result["HOU_protected_stress_count"], 1)
        self.assertTrue(result["fixed_reference_component_criterion_passed"])
        changed = copy.deepcopy(policies)
        next(r for r in changed if r["row_key"] == "HOU|native")["scores"]["J"] = 0
        outcome = evaluate.decide(changed, candidates, cases)
        self.assertFalse(outcome["fixed_reference_component_criterion_passed"])
        self.assertEqual(outcome["HOU_protected_policy_losses"], ["HOU|native"])
        changed_candidates = copy.deepcopy(candidates)
        changed_candidates[0]["scores"]["J"] = None
        outcome = evaluate.decide(policies, changed_candidates, cases)
        self.assertFalse(outcome["fixed_reference_component_criterion_passed"])
        self.assertEqual(outcome["HOU_protected_stress_losses"], ["stress_correct"])
        changed_candidates[0]["evaluation_category"] = "masked_unknown"
        self.assertTrue(evaluate.decide(policies, changed_candidates, cases)["fixed_reference_component_criterion_passed"])

    def test_hou_hidden_regression_is_per_policy_and_against_score_only_too(self):
        policies, candidates, cases = decision_fixture()
        hidden = next(r for r in policies if r["row_key"] == "HOU|hidden|quality_top")
        hidden["scores"].update(Q=1, S=-1, J=1)
        outcome = evaluate.decide(policies, candidates, cases)
        self.assertFalse(outcome["fixed_reference_component_criterion_passed"])
        failures = [r for r in outcome["HOU_hidden_checks"] if not r["passed"]]
        self.assertEqual(len(failures), 1)
        self.assertEqual((failures[0]["policy"], failures[0]["comparator"]), ("quality_top", "S"))

    def test_case_views_preserve_original_choices_missing_sides_and_raw_quality(self):
        candidate = point("r", "eligible_match", 2, j=-1, query_id="query")
        saved = {"source_choices": [
            {"query_id": "query", "state": "observed", "logit": 2},
            {"query_id": None, "state": "missing", "logit": None}],
            "contrasts": [{"row_id": "contrast", "source_comparison": {
                "source_choice": {"query_id": "query", "state": "observed", "outcome": "correct"},
                "target_choice": {"query_id": None, "state": "missing"}},
                "source_quality": {"image_quality_logit": 2},
                "target_quality": {"image_quality_logit": None}}]}
        choices, contrasts = evaluate.old_case_views(saved, [candidate])
        self.assertEqual(choices[0]["scores"]["J"], -1)
        self.assertEqual(choices[1]["scores"], dict.fromkeys(evaluate.ARMS))
        self.assertFalse(any(choices[1]["accepted_at_zero"].values()))
        self.assertEqual(contrasts[0]["target"]["scores"], dict.fromkeys(evaluate.ARMS))
        self.assertEqual(contrasts[0]["delta_target_minus_source"], dict.fromkeys(evaluate.ARMS))
        self.assertTrue(all(not r["new_choice_created"] for r in choices + contrasts))
        with self.assertRaisesRegex(ValueError, "query lost"):
            evaluate.old_case_views(saved, [])
        with self.assertRaisesRegex(ValueError, "Q changed"):
            evaluate.old_case_views(saved, [{**candidate, "scores": {**candidate["scores"], "Q": 5}}])

    def test_missingness_keeps_slots_and_field_absence_without_zero_substitution(self):
        observed = point("a", "eligible_match", 0, cohort="HOU_stress", context="HOU_development",
                         native_score=0, component_pixels=None, padding_pixels=0,
                         center_xy_px=[0, 0], out_of_fitting_schema=True)
        missing = point("b", "eligible_match", None, cohort="HOU_stress", context="HOU_development",
                        out_of_fitting_schema=True)
        result = evaluate.missingness([observed, missing], [{"row_key": "a"}, {"row_key": "b"}])[0]
        self.assertEqual(result["denominator"], 2)
        self.assertEqual(result["scores_missing"], dict.fromkeys(evaluate.ARMS, 1))
        self.assertEqual(result["source_fields_missing"], {"native_score": 1, "component_pixels": 2,
                                                         "padding_pixels": 1, "center_xy_px": 1})
        self.assertEqual(result["feature_records"], 2)
        self.assertEqual(result["out_of_fitting_schema"], 2)

    def test_malformed_score_values_are_rejected(self):
        for value in (True, "1", math.inf, -math.inf, math.nan):
            with self.subTest(value=value):
                row = point("a", "eligible_match", value)
                with self.assertRaisesRegex(ValueError, "Nonfinite/malformed"):
                    evaluate.aggregate([row], "Q")
                with self.assertRaisesRegex(ValueError, "Nonfinite/malformed"):
                    evaluate.curve([row], "Q")


if __name__ == "__main__":
    unittest.main()
