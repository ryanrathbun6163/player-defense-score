"""Synthetic invariants for the frozen study's descriptive endpoint consumers."""
from copy import deepcopy
import unittest

from src.ball_tracking import saved_score_failure_analysis as analysis


def candidate(cid, context, fid, game, logit, category="eligible_match", target_group="positive",
              origin="native", selected=False, cohort="package", fit="all_nba", tags=None):
    target = 1 if target_group == "positive" else 0 if target_group in ("eligible_distant_miss", "certain_hidden") else None
    return {
        "row_key": context + "|" + cid, "candidate_id": cid if cohort == "package" else None,
        "query_id": cid if cohort != "package" else None,
        "frame_key": context + "|" + fid if fid else None, "frame_id": fid,
        "context": context, "fit": fit, "game_id": game, "block_id": game + "_e01" if game else None,
        "source_frame_index": int(fid[-1]) if fid else None, "cohort": cohort,
        "native_or_weak": origin, "selected_native": selected,
        "evaluation_category": category, "target_group": target_group, "target": target,
        "logit": logit, "zero_state": analysis.sign(logit),
        "native_score": .25 if logit is not None else None, "component_pixels": 3 if logit is not None else None,
        "extraction": "component" if origin == "native" else "weak_peak", "threshold": .1,
        "padding_pixels": 0 if logit is not None else None,
        "padding_state": "complete" if logit is not None else "inapplicable_missing",
        "visibility": "visible", "game_ball_identity_certainty": "certain",
        "difficulty_tags": [] if tags is None else tags, "recorded_uncertainty_radius_px": 2,
        "geometry_source": "accepted", "selection_category": None, "annotation": {},
    }


def frame(context, fid, game, pool, rank, margin, *, eligible=True, reference="positive", native_outcome="correct"):
    selected = next((c for c in pool if c["selected_native"]), None)
    native_correct = bool(selected and selected["evaluation_category"] == "eligible_match")
    native_logit = selected["logit"] if selected else None
    matches = [c for c in pool if c["evaluation_category"] == "eligible_match"]
    cross = {"eligible": eligible, "reference_category": reference, "candidate_count": len(pool),
             "matching_candidates": len(matches), "positive_matching_candidates": sum(c["logit"] > 0 for c in matches),
             "native_correct": native_correct, "native_correct_logit": native_logit if native_correct else None,
             "native_outcome": native_outcome}
    return {
        "frame_key": context + "|" + fid, "frame_id": fid, "context": context,
        "game_id": game, "block_id": game + "_e01", "source_frame_index": int(fid[-1]),
        "ranking_normalized": rank, "rank_margin": margin,
        "rank_margin_null_reason": None if margin is not None else "not_localization_eligible" if not eligible else "no_matching_candidate" if not matches else "no_eligible_miss",
        "cross_tab": cross, "native_outcome": native_outcome, "native_correct": native_correct,
        "native_selected_logit": native_logit, "candidate_count": len(pool), "matching_candidate_count": len(matches),
        "visibility": "visible" if eligible else "not_visible", "game_ball_identity_certainty": "certain",
        "difficulty_tags": [], "recorded_uncertainty_radius_px": 2 if eligible else None,
        "geometry_source": "accepted" if eligible else None, "selection_category": None,
        "annotation": {},
    }


def fixture():
    frames, candidates = [], []
    for context, is_held in (("nba_in_sample", False), ("nba_out_of_fold", True)):
        fit = "leave_A_out" if is_held else "all_nba"
        pool = [candidate("match", context, "f1", "A", -1 if is_held else 1, selected=True, fit=fit, tags=["occluded", "occluded"]),
                candidate("miss", context, "f1", "A", -1 if is_held else 0, "eligible_miss", "eligible_distant_miss", "weak", fit=fit),
                candidate("boundary", context, "f1", "A", -2, "eligible_miss", "boundary_unknown", fit=fit)]
        candidates.extend(pool)
        frames.append(frame(context, "f1", "A", pool, "top_tie" if is_held else "match_first", 0 if is_held else 1))
        fit = "leave_B_out" if is_held else "all_nba"
        pool = [candidate("no_match", context, "f2", "B", -3 if is_held else -2,
                          "eligible_miss", "eligible_distant_miss", selected=True, fit=fit)]
        candidates.extend(pool)
        frames.append(frame(context, "f2", "B", pool, "no_pool_match", None, native_outcome="wrong"))
        pool = [candidate("hidden", context, "f3", "B", -1 if is_held else 1,
                          "certain_hidden", "certain_hidden", selected=True, fit=fit)]
        candidates.extend(pool)
        frames.append(frame(context, "f3", "B", pool, "not_eligible", None, eligible=False, reference="hidden", native_outcome="emitted"))
    pool = [candidate("nfhs", "nfhs_secondary", "f4", "N", 0, selected=True)]
    candidates.extend(pool)
    frames.append(frame("nfhs_secondary", "f4", "N", pool, "match_first", None))
    pool = [candidate("houhidden", "HOU_development", "f5", "H", -1, "certain_hidden", "certain_hidden", selected=True, cohort="HOU_main")]
    candidates.extend(pool)
    frames.append(frame("HOU_development", "f5", "H", pool, "not_eligible", None, eligible=False, reference="certain_hidden", native_outcome="unscored"))
    candidates.append(candidate("stresspositive", "HOU_development", "f5", "H", 10, "certain_hidden", "certain_hidden", "unknown_stress_origin", cohort="HOU_stress"))
    pool = [candidate("houwrong", "HOU_development", "f6", "H", 2, "eligible_miss", "eligible_distant_miss", selected=True, cohort="HOU_main"),
            candidate("houmatch", "HOU_development", "f6", "H", 0, origin="weak", cohort="HOU_main")]
    candidates.extend(pool)
    frames.append(frame("HOU_development", "f6", "H", pool, "miss_first", -2, native_outcome="wrong"))
    candidates.append(candidate("stressmissing", "HOU_development", "f6", "H", None, "missing", "missing_selection", "unknown_stress_origin", cohort="HOU_stress"))
    candidates.append(candidate("history", "historical", None, None, 3, "historical", "historical", "inapplicable_historical", cohort="historical"))
    manifests = {"all_nba": {"fit_game_ids": ["A", "B"]},
                 "leave_A_out": {"fit_game_ids": ["B"]}, "leave_B_out": {"fit_game_ids": ["A"]}}
    weights = {}
    for fit, manifest in manifests.items():
        fitting = [r for r in candidates if r["context"] == "nba_in_sample" and r["game_id"] in manifest["fit_game_ids"] and r["target"] is not None]
        weights[fit] = {r["candidate_id"]: {"objective_weight": 1 / len(fitting), "training_multiplier": 1} for r in fitting}
    contrast = {"row_id": "retained_unknown", "frame_key": "HOU_development|f6", "contrast": "old_to_old",
                "block_id": "H_e01", "frame": 6, "tags": ["old_case", "old_case"], "choice_state": "both_missing",
                "outcome_transition": "unknown->unknown", "correct_side_status": "not_discrimination_pair",
                "coordinate_agreement": False, "source_quality": {"image_quality_logit": None, "comparison_value": 0}}
    return {"frames": frames, "candidates": candidates, "weights": weights, "manifests": manifests,
            "historical": [{"screen_role": "unresolved", "quality_target": None}],
            "contrasts": [contrast], "controls": {"prior": {"no_threshold_selected": True}}}


class SavedScoreFailureAnalysisTests(unittest.TestCase):
    def test_numeric_summaries_preserve_zero_missing_ties_and_quartile_rule(self):
        result = analysis.numeric_summary([None, 0, 0, 2, 6])
        self.assertEqual(result, {"observed_count": 4, "missing_count": 1, "min": 0.0, "median": 1.0,
                                  "max": 6.0, "q25": 0.0, "q75": 3.0, "quartiles_reason": None})
        self.assertIsNone(analysis.numeric_summary([0, 1, 2])["q25"])
        self.assertIsNone(analysis.numeric_summary([None])["median"])
        self.assertEqual([analysis.sign(v) for v in [None, -1, 0, 1]], ["missing", "negative", "zero", "positive"])
        for bad in [float("nan"), float("inf"), True, "0"]:
            with self.assertRaises(ValueError):
                analysis.numeric_summary([bad])

    def test_fullpool_states_keep_native_wrong_sign_and_exclude_stress_survivors(self):
        study = fixture()
        states = analysis.frame_states(study["frames"], study["candidates"])
        self.assertFalse(states["HOU_development|f5"]["hidden_survivor"])
        self.assertEqual(states["HOU_development|f6"]["native_zero_state"], "positive")
        self.assertFalse(states["HOU_development|f6"]["native_correct_positive"])
        self.assertEqual(states["nba_out_of_fold|f1"]["ranking"], "top_tie")
        self.assertTrue(states["nfhs_secondary|f4"]["native_correct_rejected"])
        self.assertFalse(states["nfhs_secondary|f4"]["any_match_positive"])

    def test_candidate_units_do_not_duplicate_frame_units_or_rerank_origin(self):
        study = fixture()
        states = analysis.frame_states(study["frames"], study["candidates"])
        rows = [r for r in study["candidates"] if r["frame_key"] == "nba_in_sample|f1"]
        result = analysis.candidate_counts(rows, states)
        self.assertEqual((result["denominator"], result["distinct_context_frames"]), (3, 1))
        self.assertEqual(result["parent_full_pool_states"][0]["candidate_count"], 3)
        self.assertEqual(result["parent_full_pool_states"][0]["distinct_context_frames"], 1)
        weak_only = analysis.candidate_counts([r for r in rows if r["native_or_weak"] == "weak"], states)
        self.assertEqual(weak_only["parent_full_pool_states"][0]["state"]["ranking"], "match_first")

    def test_frame_retention_counts_partition_native_correct_frames_once(self):
        study = fixture()
        states = analysis.frame_states(study["frames"], study["candidates"])
        result = analysis.frame_counts(study["frames"], states)
        counts = result["counts"]
        # One native-correct point is positive, one negative, one exactly zero.
        # The selected wrong/hidden positives must not enter this denominator.
        self.assertEqual(counts["native_correct"], 3)
        self.assertEqual(counts["native_correct_positive"], 1)
        self.assertEqual(counts["native_correct_negative"], 1)
        self.assertEqual(counts["native_correct_zero"], 1)
        self.assertEqual(counts["native_correct_rejected"], 2)
        self.assertEqual(counts["native_correct_positive"] + counts["native_correct_rejected"], counts["native_correct"])
        self.assertEqual(sum(r["count"] for r in result["joint_states"]), result["denominator"])

    def test_paired_deltas_use_exact_candidates_and_keep_margin_nulls(self):
        study = fixture()
        states = analysis.frame_states(study["frames"], study["candidates"])
        candidates, frames, tables = analysis.paired_rows(study["frames"], study["candidates"], states)
        self.assertEqual((len(candidates), len(frames)), (5, 3))
        match = next(r for r in candidates if r["candidate_id"] == "match")
        self.assertEqual(match["held_minus_fitted"], -2)
        self.assertEqual(match["sign_transition"], "positive->negative")
        self.assertEqual(match["parent_rank_transition"], "match_first->top_tie")
        self.assertEqual(match["parent_rank_margin_difference"], -1)
        no_match = next(r for r in candidates if r["candidate_id"] == "no_match")
        self.assertIsNone(no_match["parent_fitted_rank_margin"])
        self.assertEqual(no_match["parent_fitted_margin_null_reason"], "no_matching_candidate")
        table = next(r for r in tables["candidates"] if r["scope"] == "game" and r["game_id"] == "A" and r["target_group"] == "positive")
        self.assertEqual(table["statistics"]["parent_held_rank_margin"]["median"], 0)
        self.assertEqual(table["distinct_frames"], 1)
        mutated = deepcopy(study["candidates"])
        next(r for r in mutated if r["context"] == "nba_out_of_fold")["candidate_id"] = "lost_pair"
        with self.assertRaisesRegex(ValueError, "populations differ"):
            analysis.paired_rows(study["frames"], mutated, states)

    def test_support_uses_actual_fit_games_and_preserves_excluded_and_absent_groups(self):
        study = fixture()
        states = analysis.frame_states(study["frames"], study["candidates"])
        tables, associations = analysis.support_correspondence(study["candidates"], study["weights"], study["manifests"], states)

        def cell(fit, group, origin="native", family="all", value="all"):
            return next(r for r in tables if r["fit"] == fit and r["target_group"] == group
                        and r["native_or_weak"] == origin and r["family"] == family and r["value"] == value)

        positive = cell("all_nba", "positive")
        self.assertEqual((positive["fitting_candidates"], positive["unique_fitting_frames"], positive["objective_mass"]), (1, 1, .25))
        self.assertEqual(positive["fitting_game_ids"], ["A"])
        absent = cell("leave_A_out", "positive")
        self.assertEqual((absent["status"], absent["fitting_candidates"], absent["objective_mass"]), ("zero_fitting_support", 0, 0.0))
        self.assertEqual(absent["included_fit_games"], ["B"])
        excluded = cell("all_nba", "boundary_unknown")
        self.assertEqual((excluded["excluded_candidates"], excluded["fitting_candidates"]), (1, 0))
        self.assertIsNone(excluded["objective_mass"])
        self.assertEqual(cell("all_nba", "positive", family="difficulty_tag", value="occluded")["objective_mass"], .25)
        self.assertNotIn("N", {g for t in tables for g in t["fitting_game_ids"]})
        held_match = next(r for r in associations if r["context"] == "nba_out_of_fold" and r["scope"] == "game" and r["game_id"] == "A" and r["support_key"] == absent["support_key"])
        self.assertEqual(held_match["zero_states"], {"negative": 1})
        self.assertEqual(held_match["fitting_candidates"], 0)
        self.assertEqual(held_match["parent_full_pool_states"][0]["state"]["ranking"], "top_tie")

    def test_metadata_marginals_keep_no_tag_null_and_exact_radius_separate(self):
        self.assertEqual(analysis.metadata({"difficulty_tags": []}, "difficulty_tag"), ["no_tag"])
        self.assertEqual(analysis.metadata({}, "difficulty_tag"), [None])
        self.assertEqual(analysis.metadata({"recorded_uncertainty_radius_px": 2.25}, "uncertainty_radius"), [2.25])
        self.assertNotEqual(analysis.token(None), analysis.token("null"))
        study = fixture()
        states = analysis.frame_states(study["frames"], study["candidates"])
        tables, numeric = analysis.grouped_candidates(study["candidates"], states)
        tagged = [r for r in tables if r["context"] == "nba_in_sample" and r["scope"] == "context" and r["family"] == "difficulty_tag" and r["value"] == "occluded"]
        self.assertEqual(tagged[0]["denominator"], 1)
        self.assertTrue(all("extraction" in r and "threshold" in r and "cohort" in r for r in numeric))

    def test_equivalent_numeric_radius_support_is_shared_without_rounding(self):
        self.assertEqual(analysis.token({"value": 4}), analysis.token({"value": 4.0}))
        self.assertNotEqual(analysis.token({"value": 4.0}), analysis.token({"value": 4.0001}))
        self.assertNotEqual(analysis.token({"value": 4}), analysis.token({"value": "4"}))
        study = fixture()
        source = next(r for r in study["candidates"] if r["row_key"] == "nba_in_sample|match")
        diagnostic = next(r for r in study["candidates"] if r["row_key"] == "HOU_development|houwrong")
        source["recorded_uncertainty_radius_px"] = 4
        diagnostic.update(target=1, target_group="positive", recorded_uncertainty_radius_px=4.0)
        states = analysis.frame_states(study["frames"], study["candidates"])
        tables, associations = analysis.support_correspondence(study["candidates"], study["weights"], study["manifests"], states)
        cells = [r for r in tables if r["fit"] == "all_nba" and r["target_group"] == "positive" and r["native_or_weak"] == "native" and r["family"] == "uncertainty_radius" and r["value"] == 4]
        self.assertEqual(len(cells), 1)
        self.assertEqual(cells[0]["status"], "available")
        self.assertEqual(cells[0]["fitting_candidates"], 1)
        self.assertEqual(cells[0]["objective_mass"], .25)
        self.assertIsInstance(source["recorded_uncertainty_radius_px"], int)
        self.assertIsInstance(diagnostic["recorded_uncertainty_radius_px"], float)
        assoc = next(r for r in associations if r["context"] == "HOU_development" and r["scope"] == "context" and r["support_key"] == cells[0]["support_key"])
        self.assertEqual(assoc["fitting_candidates"], 1)

    def test_missing_extraction_threshold_is_unavailable_not_zero_training_support(self):
        study = fixture()
        stress = next(r for r in study["candidates"] if r["row_key"] == "HOU_development|stresspositive")
        stress.update(native_or_weak="native", extraction="component", threshold=None)
        states = analysis.frame_states(study["frames"], study["candidates"])
        tables, associations = analysis.support_correspondence(study["candidates"], study["weights"], study["manifests"], states)
        cell = next(r for r in tables if r["fit"] == "all_nba" and r["target_group"] == "certain_hidden" and r["native_or_weak"] == "native" and r["family"] == "extraction_threshold" and r["value"] == ["component", None])
        self.assertEqual(cell["status"], "metadata_unavailable")
        self.assertIsNone(cell["objective_mass"])
        diagnostic = next(r for r in associations if r["context"] == "HOU_development" and r["cohort"] == "HOU_stress" and r["scope"] == "context" and r["support_key"] == cell["support_key"])
        self.assertEqual(diagnostic["support_status"], "metadata_unavailable")
        self.assertIsNone(diagnostic["objective_mass"])
        self.assertEqual(diagnostic["denominator"], 1)

    def test_end_to_end_retains_unknown_contrasts_historical_and_missing_slots(self):
        study = fixture()
        snapshot = deepcopy(study)
        output = analysis.analyze(study)
        self.assertEqual(study, snapshot)
        self.assertEqual(output["summary"]["paired_NBA_candidates"], 5)
        self.assertEqual(output["summary"]["missing_scores"], 1)
        self.assertEqual(output["summary"]["contrasts"], 1)
        self.assertEqual(output["contrast_views"][0]["source_quality"], {"image_quality_logit": None, "comparison_value": 0})
        self.assertEqual(output["historical_appendix"], snapshot["historical"])
        self.assertIsNone(output["historical_appendix"][0]["quality_target"])
        self.assertEqual(output["controls"], snapshot["controls"])
        self.assertEqual(output["case_views"]["all_existing_contrast_tags"]["old_case"], ["retained_unknown"])
        self.assertEqual(output["case_views"]["named_groups"]["all_HOU_native_wrong_eligible"]["frame_count"], 1)
        self.assertEqual(output["summary"]["new_choices"], 0)

    def test_input_sign_and_duplicate_integrity_are_fatal(self):
        study = fixture()
        study["candidates"][0]["zero_state"] = "zero"
        with self.assertRaisesRegex(ValueError, "sign transport"):
            analysis.analyze(study)
        study = fixture()
        study["candidates"].append(deepcopy(study["candidates"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            analysis.analyze(study)


if __name__ == "__main__":
    unittest.main()
