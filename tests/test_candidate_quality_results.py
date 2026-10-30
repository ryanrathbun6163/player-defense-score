"""CPU score-consumer checks using actual prepared producer records.

All logits below are declared synthetic test values, never experiment results.
No model, image, map or protected evaluation is opened.
"""
from copy import deepcopy
import unittest

from src.ball_tracking import candidate_quality_results as results


class CandidateQualityResultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = results.ROOT / results.PREPARATION
        if not (base / "prepared.json").exists():
            raise unittest.SkipTest("Ignored metadata preparation unavailable")
        cls.frames = results.read_rows(base / "frames.jsonl")
        cls.candidates = results.read_rows(base / "candidates.jsonl")
        cls.by_id = {c["candidate_id"]: c for c in cls.candidates}

    def select(self, predicate):
        frame = next(f for f in self.frames if predicate(f))
        return deepcopy(frame), [deepcopy(self.by_id[i]) for i in frame["candidate_ids"]]

    def score_maps(self, candidates, value=0.0):
        return {name: [{"candidate_id": c["candidate_id"], "quality_logit": value}
                       for c in candidates if name == "all_nba"
                       or (c["domain"] == "nba" and c["game_id"] not in games)]
                for name, games in results.FIT_GAMES.items()}

    def test_actual_boundary_mask_is_still_an_evaluation_miss(self):
        frame, candidates = self.select(lambda f: any(self.by_id[i]["target_group"] == "boundary_unknown"
                                                     for i in f["candidate_ids"]))
        unknown = next(c for c in candidates if c["target_group"] == "boundary_unknown")
        self.assertIsNone(unknown["target"])
        self.assertEqual(results.evaluation_category(frame, unknown), "eligible_miss")
        rows, summary = results.analyze_scores([frame], candidates, self.score_maps(candidates))
        emitted = next(c for c in rows[0]["candidate_scores"] if c["candidate_id"] == unknown["candidate_id"])
        self.assertIsNone(emitted["fitting_target"])
        self.assertEqual(emitted["evaluation_category"], "eligible_miss")
        counts = summary["contexts"]["nba_in_sample"]["counts"]
        self.assertEqual(counts["candidates:eligible_miss:retained_zero"], 0)
        self.assertGreaterEqual(counts["candidates:eligible_miss:tie_zero"], 1)

    def test_empty_hidden_frames_remain_denominator_at_fixed_strict_zero(self):
        selected = [self.select(lambda f: f["domain"] == "nba" and f["kind"] == "hidden" and not f["candidate_ids"]),
                    self.select(lambda f: f["domain"] == "nba" and f["kind"] == "hidden" and bool(f["candidate_ids"]))]
        frames = [f for f, _ in selected]
        candidates = [c for _, members in selected for c in members]
        rows, summary = results.analyze_scores(frames, candidates, self.score_maps(candidates, 0.0))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["candidate_scores"], [])
        for context in ("nba_in_sample", "nba_out_of_fold"):
            stats = summary["contexts"][context]
            self.assertEqual(stats["counts"]["frames:hidden"], 2)
            self.assertEqual(stats["counts"]["frames:empty_pool"], 1)
            self.assertEqual(stats["counts"]["frames:hidden:any_survivor_zero"], 0)
            self.assertEqual(stats["counts"]["frames:hidden:any_tie_zero"], 1)
            self.assertEqual(stats["frontier"]["hidden_empty_pool_frames"], 1)
            self.assertEqual(stats["groups"]["origin"]["weak"]["frames:hidden"], 2)
            self.assertEqual(stats["groups"]["origin"]["weak"]["frames:hidden:survivor_zero"], 0)

    def test_masked_frames_have_scores_without_correctness_labels(self):
        frame, candidates = self.select(lambda f: f["kind"] == "masked" and bool(f["candidate_ids"]))
        rows, summary = results.analyze_scores([frame], candidates, self.score_maps(candidates, 10.0))
        self.assertTrue(all(c["evaluation_category"] == "masked_unknown" for c in rows[0]["candidate_scores"]))
        counts = summary["contexts"]["nba_in_sample"]["counts"]
        self.assertEqual(counts["frames:masked"], 1)
        self.assertEqual(counts["candidates:masked_unknown:retained_zero"], len(candidates))
        self.assertNotIn("frames:native_correct", counts)

    def test_native_missing_weak_positive_and_strict_ranking_are_reported(self):
        frame, candidates = self.select(lambda f: f["block_id"] == "chi-vs-ind-0022400868_e02"
                                       and f["source_frame_index"] == 83)
        scores = self.score_maps(candidates, -1.0)
        match_ids = {c["candidate_id"] for c in candidates if results.evaluation_category(frame, c) == "eligible_match"}
        self.assertEqual(len(match_ids), 1)
        for fit_scores in scores.values():
            for row in fit_scores:
                if row["candidate_id"] in match_ids:
                    row["quality_logit"] = 2.0
        _, summary = results.analyze_scores([frame], candidates, scores)
        counts = summary["contexts"]["nba_out_of_fold"]["counts"]
        self.assertEqual(counts["frames:native_missing"], 1)
        self.assertEqual(counts["frames:weak_match_retained_zero:native_missing"], 1)
        self.assertEqual(counts["frames:ranking:match_strictly_first"], 1)

    def test_match_miss_ties_are_not_strict_ranking_successes(self):
        frame, candidates = self.select(lambda f: f["block_id"] == "chi-vs-ind-0022400868_e01"
                                       and f["source_frame_index"] == 0)
        _, summary = results.analyze_scores([frame], candidates, self.score_maps(candidates, 1.0))
        counts = summary["contexts"]["nba_in_sample"]["counts"]
        self.assertEqual(counts["frames:ranking:match_miss_top_tie"], 1)
        self.assertNotIn("frames:ranking:match_strictly_first", counts)
        self.assertEqual(counts["frames:native_correct:retained_zero"], 1)

    def test_positive_zero_negative_logits_partition_without_tie_survival(self):
        frame, candidates = self.select(lambda f: f["block_id"] == "chi-vs-ind-0022400868_e01"
                                       and f["source_frame_index"] == 0)
        scores = self.score_maps(candidates)
        values = [0.0, -1.0, 1.0, -0.0, 2.0]
        for fit_scores in scores.values():
            for row, value in zip(fit_scores, values):
                row["quality_logit"] = value
        _, summary = results.analyze_scores([frame], candidates, scores)
        counts = summary["contexts"]["nba_in_sample"]["counts"]
        self.assertEqual(counts["candidates:retained_zero"], 2)
        self.assertEqual(counts["candidates:below_zero"], 1)
        self.assertEqual(counts["candidates:tie_zero"], 2)
        self.assertEqual(counts["frames:native_correct:retained_zero"], 0)
        self.assertEqual(counts["frames:native_correct:rejected_zero"], 0)
        self.assertEqual(counts["frames:native_correct:tie_zero"], 1)
        zero = next(r for r in summary["contexts"]["nba_in_sample"]["frontier"]["rows"] if r["cutoff"] == 0)
        self.assertEqual(zero["native_correct_retained"], 0)

    def test_held_fit_routing_and_secondary_nfhs_scope(self):
        selected = [self.select(lambda f: f["block_id"] == "chi-vs-ind-0022400868_e01"
                                and f["source_frame_index"] == 0),
                    self.select(lambda f: f["domain"] == "nfhs" and bool(f["candidate_ids"]))]
        frames = [f for f, _ in selected]
        candidates = [c for _, members in selected for c in members]
        scores = self.score_maps(candidates, 1.0)
        for row in scores["leave_chi_out"]:
            row["quality_logit"] = -1.0
        rows, summary = results.analyze_scores(frames, candidates, scores)
        self.assertEqual(rows[0]["scoring_contexts"]["nba_out_of_fold"]["fit"], "leave_chi_out")
        self.assertTrue(all(c["held_out_logit"] is None for c in rows[1]["candidate_scores"]))
        self.assertEqual(summary["contexts"]["nfhs_secondary"]["counts"]["frames"], 1)
        gap = summary["paired_game_comparisons"]["0022400868"]["out_of_fold_minus_in_sample"]
        self.assertEqual(gap["frames:native_correct:retained_zero"], -1)
        self.assertEqual(gap["frames"], 0)

    def test_score_population_duplicate_nonfinite_and_missing_errors(self):
        _, candidates = self.select(lambda f: f["block_id"] == "chi-vs-ind-0022400868_e01"
                                    and f["source_frame_index"] == 0)
        for fault in ("duplicate", "missing", "wrong_game", "nonfinite"):
            scores = self.score_maps(candidates)
            if fault == "duplicate":
                scores["all_nba"].append(deepcopy(scores["all_nba"][0]))
            elif fault == "missing":
                scores["leave_chi_out"].pop()
            elif fault == "wrong_game":
                scores["leave_den_out"].append(deepcopy(scores["all_nba"][0]))
            else:
                scores["all_nba"][0]["quality_logit"] = float("nan")
            with self.assertRaises(ValueError, msg=fault):
                results.validate_scores(candidates, scores)

    def test_frontier_counts_hidden_frames_not_candidate_density(self):
        def point(native=None, hidden=None, weak=None, match=None):
            return {"native_correct_logit": native, "hidden_max_logit": hidden,
                    "weak_match_max_logit": weak, "any_match_max_logit": match}
        curve = results.diagnostic_frontier([point(native=1, weak=1, match=1),
                                             point(native=3, match=3), point(hidden=2), point()], 2)
        self.assertEqual(curve["hidden_empty_pool_frames"], 1)
        after_two = next(r for r in curve["rows"] if r["cutoff"] == 2)
        self.assertEqual(after_two["native_correct_retained"], 1)
        self.assertEqual(after_two["hidden_frames_with_survivor"], 0)
        self.assertEqual(after_two["weak_match_frames_retained"], 0)
        self.assertTrue(curve["diagnostic_only_no_selected_threshold"])

    def test_full_actual_population_transport_with_declared_zero_test_scores(self):
        rows, summary = results.analyze_scores(self.frames, self.candidates, self.score_maps(self.candidates, 0.0))
        self.assertEqual(len(rows), 3329)
        self.assertEqual(sum(not r["candidate_scores"] for r in rows), 21)
        self.assertEqual(sum(r["frame"]["kind"] == "masked" for r in rows), 241)
        self.assertEqual(sum(len(r["candidate_scores"]) for r in rows), 19632)
        for context in ("nba_in_sample", "nba_out_of_fold"):
            counts = summary["contexts"][context]["counts"]
            self.assertEqual(counts["frames"], 3179)
            self.assertEqual(counts["frames:native_correct"], 2807)
            self.assertEqual(counts["frames:weak_match"], 610)
            self.assertEqual(counts["frames:hidden"], 128)
            self.assertEqual(counts["frames:hidden:any_survivor_zero"], 0)
            self.assertEqual(counts["frames:hidden:any_tie_zero"], 113)
            self.assertEqual(counts["candidates:tie_zero"], counts["candidates"])
            self.assertEqual(counts["frames:native_correct:retained_zero"], 0)
            self.assertEqual(counts["frames:native_correct:tie_zero"], 2807)
        self.assertEqual(summary["contexts"]["nfhs_secondary"]["counts"]["frames"], 150)


if __name__ == "__main__":
    unittest.main()
