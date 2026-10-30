"""Bounded synthetic checks for the origin ablation runner and protections."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.ball_tracking import candidate_acceptance_origin_ablation as runner
from src.ball_tracking import candidate_acceptance_origin_model as model_api


def point(key, category="eligible_match", *, q=1, s=1, j=1, a=1, game="CHI", policy="native",
          context="nba_out_of_fold", cohort="fixed_policy", frame=None, **extra):
    return {"row_key": key, "frame_key": frame or key, "context": context, "game_id": game,
            "policy": policy, "cohort": cohort, "evaluation_category": category,
            "scores": {"Q": q, "S": s, "J": j, "M": q, "A": a}, **extra}


def fixture(improve=True):
    policies = []
    for game in ("CHI", "DEN", "SAC"):
        for policy in ("native", "quality_top"):
            prefix = game + "|" + policy
            policies.extend([point(prefix + "|correct", game=game, policy=policy),
                             point(prefix + "|wrong", "eligible_miss", a=-1 if improve else 1,
                                   game=game, policy=policy),
                             point(prefix + "|hidden", "certain_hidden", a=-1 if improve else 1,
                                   game=game, policy=policy)])
    for policy in ("native", "quality_top"):
        policies.append(point("HOU|" + policy, game="HOU", policy=policy, context="HOU_development", frame="protected"))
        policies.append(point("HOU|hidden|" + policy, "certain_hidden", q=-1, s=-1, j=1,
                              a=-1, game="HOU", policy=policy, context="HOU_development"))
    candidates = [point("stress", game="HOU", context="HOU_development", cohort="HOU_stress", frame="protected")]
    cases = {"named_groups": {"kept": {"frame_keys": ["protected"]}}}
    protection = runner.protection_lists(policies, candidates, cases)
    return policies, candidates, cases, protection


class CandidateAcceptanceOriginAblationTests(unittest.TestCase):
    def test_frozen_protection_depends_only_on_original_q_j_and_named_roles(self):
        policies = [point("nba_j", q=-1, j=1), point("nba_q", q=1, j=-1),
                    point("nba_wrong", "eligible_miss"),
                    point("hou_q", q=1, j=-1, context="HOU_development", frame="named"),
                    point("hou_j", q=-1, j=1, context="HOU_development", frame="named"),
                    point("hou_neither", q=-1, j=-1, context="HOU_development", frame="named"),
                    point("hou_outside", context="HOU_development", frame="outside")]
        candidates = [point("stress_q", q=1, j=-1, cohort="HOU_stress", frame="named"),
                      point("stress_j", q=-1, j=1, cohort="HOU_stress", frame="named"),
                      point("alternative", cohort="HOU_main", frame="named"),
                      point("unknown", "masked_unknown", cohort="HOU_stress", frame="named"),
                      point("stress_outside", cohort="HOU_stress", frame="outside")]
        cases = {"named_groups": {"test": {"frame_keys": ["named", "named"]}}}
        expected = runner.protection_lists(policies, candidates, cases)
        self.assertEqual(expected["NBA_J_kept_correct_policy_ids"], ["nba_j"])
        self.assertEqual(expected["HOU_Q_or_J_kept_correct_named_policy_ids"], ["hou_j", "hou_q"])
        self.assertEqual(expected["HOU_Q_or_J_kept_correct_named_stress_ids"], ["stress_j", "stress_q"])
        for value in (-100, 0, 100, None):
            changed_policies, changed_candidates = copy.deepcopy((policies, candidates))
            for row in changed_policies + changed_candidates:
                row["scores"]["A"] = value
            self.assertEqual(runner.protection_lists(changed_policies, changed_candidates, cases), expected)
        self.assertTrue(expected["candidate_alternatives_are_not_extra_vetoes"])

    def test_exact_j_kept_correct_losses_veto_even_when_totals_are_equal(self):
        policies, candidates, cases, protection = fixture()
        original = copy.deepcopy((policies, candidates))
        result = runner.evaluate_decisions(policies, candidates, cases, protection)
        self.assertTrue(result["A_nonregression_vs_J_passed"])
        self.assertTrue(result["original_component_criterion"]["fixed_reference_component_criterion_passed"])
        self.assertEqual((policies, candidates), original)
        target = next(r for r in policies if r["row_key"] == "CHI|native|correct")
        target["scores"]["A"] = -1
        policies.append(point("replacement_correct", q=-1, s=-1, j=-1, a=1))
        result = runner.evaluate_decisions(policies, candidates, cases, protection)
        self.assertTrue(all(r["passed"] for r in result["A_vs_J_checks"]))
        self.assertFalse(result["A_nonregression_vs_J_passed"])
        self.assertEqual(result["protected_losses"]["NBA_J_kept_correct_policy_ids"], ["CHI|native|correct"])
        self.assertTrue(result["original_component_criterion"]["fixed_reference_component_criterion_passed"])
        self.assertIsNone(result["selected_threshold"])
        self.assertFalse(result["model_adopted"])

    def test_nonregression_requires_a_strict_nba_gain_and_hou_protections(self):
        policies, candidates, cases, protection = fixture(improve=False)
        result = runner.evaluate_decisions(policies, candidates, cases, protection)
        self.assertTrue(all(r["passed"] for r in result["A_vs_J_checks"]))
        self.assertFalse(result["strict_NBA_improvement"])
        self.assertFalse(result["A_nonregression_vs_J_passed"])
        for kind in ("policy", "stress"):
            policies, candidates, cases, protection = fixture()
            target = next(r for r in policies if r["row_key"] == "HOU|native") if kind == "policy" else candidates[0]
            target["scores"]["A"] = 0
            result = runner.evaluate_decisions(policies, candidates, cases, protection)
            self.assertFalse(result["A_nonregression_vs_J_passed"])
            name = "HOU_Q_or_J_kept_correct_named_" + ("policy_ids" if kind == "policy" else "stress_ids")
            self.assertEqual(result["protected_losses"][name], [target["row_key"]])
        policies, candidates, cases, protection = fixture()
        protection["NBA_J_kept_correct_policy_ids"].append("missing_identity")
        with self.assertRaisesRegex(ValueError, "Protected identity lost"):
            runner.evaluate_decisions(policies, candidates, cases, protection)

    def test_original_q_s_criterion_is_separate_and_substitution_never_changes_j(self):
        policies, candidates, cases, protection = fixture()
        hidden = next(r for r in policies if r["row_key"] == "CHI|native|hidden")
        hidden["scores"].update(Q=-1, S=-1, J=1, A=1)
        original = copy.deepcopy((policies, candidates))
        result = runner.evaluate_decisions(policies, candidates, cases, protection)
        self.assertTrue(result["A_nonregression_vs_J_passed"])
        self.assertFalse(result["original_component_criterion"]["fixed_reference_component_criterion_passed"])
        self.assertEqual(result["original_component_criterion_evaluated_arm"], "A")
        self.assertEqual((policies, candidates), original)
        for check in result["original_component_criterion"]["NBA_checks"]:
            self.assertIn("A", check)
            self.assertNotIn("J", check)
        self.assertEqual(hidden["scores"]["J"], 1)

    def test_predictions_use_saved_gate_and_fixed_choice_without_fallback_and_preserve_old_scores(self):
        candidates = []
        for key, gate, quality in (("native", "outer_CHI", 1), ("alternate", "outer_CHI", 2),
                                   ("den", "outer_DEN", 3), ("sac", "outer_SAC", 4),
                                   ("hou", "final_all_NBA", 5), ("missing", "final_all_NBA", None)):
            candidate = point(key, q=quality, s=quality, j=quality, a=None, cohort="package",
                              gate_fit=gate, logit=quality)
            candidate["scores"].pop("A")
            candidates.append(candidate)
        policies = [point("policy_native", chosen_row_key="native"),
                    point("policy_top", policy="quality_top", chosen_row_key="alternate"),
                    point("policy_empty", chosen_row_key=None)]
        for policy in policies:
            policy["scores"].pop("A")
        loaded = {"candidates": candidates, "fixed_policies": policies,
                  "feature_indices": {"evaluation": {r["row_key"]: {"row_key": r["row_key"], "Q": r["logit"]}
                                                       for r in candidates}}}
        before = copy.deepcopy(loaded)
        calls = []
        def predict(model, features):
            calls.append((model, [r["row_key"] for r in features]))
            return [None if r["Q"] is None else -1 if r["row_key"] == "native" else 10 for r in features]
        scored, chosen = runner.add_predictions(loaded, {gate: gate for gate in runner.data.GATES}, predict)
        self.assertEqual(loaded, before)
        self.assertEqual(calls, [("outer_CHI", ["native", "alternate"]), ("outer_DEN", ["den"]),
                                ("outer_SAC", ["sac"]), ("final_all_NBA", ["hou", "missing"])])
        self.assertEqual([r["scores"]["A"] for r in chosen], [-1, 10, None])
        self.assertEqual([r["chosen_row_key"] for r in chosen], ["native", "alternate", None])
        self.assertIsNone(scored[-1]["scores"]["A"])
        for old, new in zip(candidates + policies, scored + chosen):
            self.assertEqual({k: v for k, v in new["scores"].items() if k != "A"}, old["scores"])
        for predictions, reason in (([], "lost rows"), ([None, 10], "missingness"),
                                     ([float("nan"), 10], "Nonfinite/malformed")):
            with self.assertRaisesRegex(ValueError, reason):
                runner.add_predictions(loaded, {gate: gate for gate in runner.data.GATES},
                                       lambda model, features: predictions)
        broken = copy.deepcopy(loaded)
        broken["fixed_policies"][0]["chosen_row_key"] = "not_a_candidate"
        with self.assertRaisesRegex(ValueError, "fixed choice lost"):
            runner.add_predictions(broken, {gate: gate for gate in runner.data.GATES}, predict)

    def test_extending_choices_contrasts_preserves_every_old_field_and_missing_side(self):
        scores = {"Q": 1, "S": 2, "J": 3, "M": 4}
        flags = dict.fromkeys(scores, True)
        old_choices = [{"query_id": "q1", "state": "observed", "scores": dict(scores),
                        "accepted_at_zero": dict(flags), "extra": {"original": [1, 2]}},
                       {"query_id": None, "state": "missing", "scores": dict.fromkeys(scores),
                        "accepted_at_zero": dict.fromkeys(scores, False)}]
        old_contrasts = [{"row_key": "contrast", "source": copy.deepcopy(old_choices[0]),
                          "target": {**copy.deepcopy(old_choices[0]), "query_id": "q2"},
                          "delta_target_minus_source": dict.fromkeys(scores, 0), "original_label": "kept"},
                         {"row_key": "missing", "source": copy.deepcopy(old_choices[0]),
                          "target": copy.deepcopy(old_choices[1]), "delta_target_minus_source": dict.fromkeys(scores)}]
        candidates = [point("first", query_id="q1", a=-2), point("second", query_id="q2", a=5)]
        before = copy.deepcopy((old_choices, old_contrasts, candidates))
        choices, contrasts = runner.extend_old_choices(old_choices, old_contrasts, candidates)
        self.assertEqual((old_choices, old_contrasts, candidates), before)
        self.assertEqual(choices[0]["scores"]["A"], -2)
        self.assertFalse(choices[0]["accepted_at_zero"]["A"])
        self.assertIsNone(choices[1]["scores"]["A"])
        self.assertEqual(contrasts[0]["delta_target_minus_source"]["A"], 7)
        self.assertIsNone(contrasts[1]["delta_target_minus_source"]["A"])
        def without_a(value):
            if isinstance(value, dict): return {k: without_a(v) for k, v in value.items() if k != "A"}
            if isinstance(value, list): return [without_a(v) for v in value]
            return value
        self.assertEqual(without_a(choices), old_choices)
        self.assertEqual(without_a(contrasts), old_contrasts)
        with self.assertRaisesRegex(ValueError, "Source choice identity"):
            runner.extend_old_choices(old_choices, old_contrasts, [])

    def test_exclusive_outputs_and_prefreeze_failure_do_not_run_fit_or_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / runner.OUTPUT
            with patch.object(runner, "check_freeze", side_effect=ValueError("synthetic freeze failure")), \
                 patch.object(runner.data, "load_inputs") as loader:
                with self.assertRaisesRegex(ValueError, "freeze failure"):
                    runner.run(root)
                loader.assert_not_called()
            self.assertFalse(output.exists())
            output.mkdir(parents=True)
            sentinel = output / "completed.json"
            sentinel.write_bytes(b"old completed output")
            with patch.object(runner, "check_freeze") as check:
                with self.assertRaisesRegex(ValueError, "no silent retry"):
                    runner.run(root)
                check.assert_not_called()
            self.assertEqual(sentinel.read_bytes(), b"old completed output")
            path = root / "rows.jsonl"
            self.assertEqual(runner.write_rows(path, [{"score": None}, {"score": 0}]), 2)
            before = path.read_bytes()
            self.assertEqual(list(runner.rows(path)), [{"score": None}, {"score": 0}])
            with self.assertRaises(FileExistsError):
                runner.write_rows(path, [{"replacement": True}])
            self.assertEqual(path.read_bytes(), before)

    def test_failed_fit_record_and_runner_receipt_persist_without_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            loaded = {"fixed_policies": [], "candidates": []}
            controls = {"case_views": {"named_groups": {}}}
            protection = runner.protection_lists([], [], controls["case_views"])
            failure = {"status": "failed", "arm": "A", "fit_id": "outer_CHI", "diagnostic": "synthetic"}
            def read(path):
                if Path(path) == root / runner.PROTECTION: return protection
                if Path(path).name == "preserved_controls_and_cases.json": return controls
                raise AssertionError("unexpected file read: " + str(path))
            with patch.object(runner, "check_freeze", return_value=({}, {})), \
                 patch.object(runner.data, "load_inputs", return_value=loaded), \
                 patch.object(runner.data, "fit_inputs", return_value=([], [], [])), \
                 patch.object(runner.io, "read", side_effect=read), \
                 patch.object(runner.io, "binding", return_value={"path": "synthetic", "sha256": "test"}), \
                 patch.object(model_api, "fit_origin_gate", side_effect=model_api.GateFitError("synthetic solver failure", failure)) as fit:
                with self.assertRaisesRegex(model_api.GateFitError, "synthetic solver failure"):
                    runner.run(root)
                output = root / runner.OUTPUT
                self.assertEqual(json.loads((output / "fits/outer_CHI_A_failed.json").read_text()), failure)
                failed = json.loads((output / "failed.json").read_text())
                self.assertEqual(failed["error"], "GateFitError")
                self.assertFalse(failed["automatic_retry"])
                self.assertFalse((output / "completed.json").exists())
                before = (output / "failed.json").read_bytes()
                with self.assertRaisesRegex(ValueError, "no silent retry"):
                    runner.run(root)
                self.assertEqual(fit.call_count, 1)
                self.assertEqual((output / "failed.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
