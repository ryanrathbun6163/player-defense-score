"""Bounded schema fixtures and integrity edge cases; no full study execution."""

import copy
import json
from pathlib import Path
import unittest

from src.ball_tracking.saved_score_failure_data import (
    IntegrityError, RANKING_NORMALIZATION, _check_transport, _enrich_frame,
    crop_padding, finite_score, index_unique, rank_margin, reporting_target,
    same_keys, zero_state,
)


FIXTURE = json.loads((Path(__file__).parent / "fixtures/saved_score_failure_data.json").read_text(encoding="utf-8"))


class TestSavedScoreFailureData(unittest.TestCase):
    def test_actual_captured_target_rules_reproduce_frozen_support(self):
        frames = {o["frame"]["frame_id"]: o["frame"] for o in FIXTURE["package_outcomes"]}
        self.assertEqual({f["kind"] for f in frames.values()}, {"positive", "hidden", "masked"})
        for candidate in FIXTURE["package_candidates"]:
            target = reporting_target(frames[candidate["frame_id"]], candidate["center_xy_px"],
                                      candidate["width_px"], candidate["height_px"])
            for field in ("target", "target_group", "distance_px", "recorded_uncertainty_radius_px"):
                self.assertEqual(target[field], candidate[field])
            self.assertEqual(target["in_bounds"], candidate["in_source_bounds"])

    def test_inclusive_radius_band_and_outside_source(self):
        frame = {"kind": "positive", "annotation": {"game_ball_identity_certainty": "certain",
                 "localization_eligible": True, "geometry": {"center_xy_px": [50, 50], "uncertainty_radius_px": 5}}}
        for center, group, target in (([60, 50], "positive", 1), ([65, 50], "boundary_unknown", None),
                                      ([65.001, 50], "eligible_distant_miss", 0), ([-1, 50], "eligible_distant_miss", 0)):
            actual = reporting_target(frame, center, 100, 100)
            self.assertEqual((actual["target_group"], actual["target"]), (group, target))
        frame["annotation"]["geometry"]["uncertainty_radius_px"] = -1
        with self.assertRaises(IntegrityError):
            reporting_target(frame, [60, 50], 100, 100)

    def test_mask_precedes_identity_and_bounds(self):
        frame = {"kind": "masked", "annotation": {"game_ball_identity_certainty": "uncertain", "geometry": None}}
        result = reporting_target(frame, [-100, 2], 100, 100)
        self.assertIsNone(result["target"])
        self.assertEqual(result["target_group"], "masked_unknown")
        self.assertFalse(result["in_bounds"])

    def test_missing_selection_is_not_zero_or_negative(self):
        frame = {"kind": "hidden", "annotation": {"geometry": None}}
        result = reporting_target(frame, None, 1280, 720)
        self.assertEqual(result["target_group"], "missing_selection")
        self.assertIsNone(result["target"])
        self.assertEqual([zero_state(x) for x in (None, -1, 0, 1)], ["missing", "negative", "zero", "positive"])

    def test_padding_uses_saved_floor_centered_rectangle(self):
        result = crop_padding([31.99, 32.01], 1280, 720)
        self.assertEqual(result["crop_box"], [-1, 0, 63, 64])
        self.assertEqual(result["padding_pixels"], 64)
        self.assertEqual(result["padding_state"], "padded")
        self.assertEqual(crop_padding([32, 32], 1280, 720)["padding_state"], "complete")
        self.assertEqual(crop_padding([-100, -100], 1280, 720)["padding_pixels"], 4096)

    def test_margin_null_reasons_empty_pool_match_only_and_tie(self):
        match = {"evaluation_category": "eligible_match", "logit": -1}
        miss = {"evaluation_category": "eligible_miss", "logit": -1}
        self.assertEqual(rank_margin([], True), (None, "no_matching_candidate"))
        self.assertEqual(rank_margin([match], True), (None, "no_eligible_miss"))
        self.assertEqual(rank_margin([match, miss], False), (None, "not_localization_eligible"))
        self.assertEqual(rank_margin([match, miss], True), (0, None))
        self.assertEqual(RANKING_NORMALIZATION["match_miss_top_tie"], "top_tie")

    def test_actual_saved_frame_transport_and_selected_native_identity(self):
        outcome = next(o for o in FIXTURE["package_outcomes"] if o["frame"]["kind"] == "positive")
        frame = outcome["frame"]
        score = outcome["scoring_contexts"]["nba_in_sample"]
        pool = [{"logit": c["all_nba_logit"], "evaluation_category": c["evaluation_category"],
                 "native_or_weak": c["native_or_weak"],
                 "selected_native": c["native_or_weak"] == "native" and c["candidate_index"] == frame["native_selected_candidate_index"]}
                for c in outcome["candidate_scores"]]
        matches = [c for c in pool if c["evaluation_category"] == "eligible_match"]
        cross = {"candidate_count": len(pool), "matching_candidates": len(matches),
                 "positive_matching_candidates": sum(c["logit"] > 0 for c in matches),
                 "native_correct": True, "native_correct_logit": score["native_correct_logit"]}
        row = {"frame_key": "fixture", "native_correct": True, "eligible": True, "cross_tab": cross}
        _enrich_frame(row, pool)
        self.assertEqual(row["native_selected_logit"], score["native_selected_logit"])
        self.assertEqual(row["any_match_max_logit"], score["any_match_max_logit"])
        self.assertEqual(row["weak_match_max_logit"], score["weak_match_max_logit"])
        broken = copy.deepcopy(row)
        broken["cross_tab"]["matching_candidates"] += 1
        with self.assertRaises(IntegrityError):
            _enrich_frame(broken, pool)

    def test_duplicate_lost_keys_nonfinite_and_missing_observed_scores_fail(self):
        with self.assertRaises(IntegrityError):
            index_unique([{"id": "same"}, {"id": "same"}], "id", "fixture")
        with self.assertRaises(IntegrityError):
            same_keys({"a", "b"}, {"a"}, "fixture")
        for value in (None, float("nan"), float("inf"), True):
            with self.assertRaises(IntegrityError):
                finite_score(value, "fixture")
        self.assertIsNone(finite_score(None, "optional", missing=True))

    def test_source_identity_conflict_rejected_without_pixel_reads(self):
        frame = copy.deepcopy(FIXTURE["package_outcomes"][0]["frame"])
        block = {"block_id": frame["block_id"], "source_video": frame["source_video"], "time_base": frame["time_base"],
                 "game_id": frame["game_id"], "domain": frame["domain"], "role": "training"}
        source = {k: frame[k] for k in ("source_frame_index", "source_pts_ticks", "duration_ticks", "annotation", "kind", "valid_output_channel")}
        source["png"] = frame["source_png"]
        _check_transport(frame, block, source, package=True)
        source["source_pts_ticks"] += 1
        with self.assertRaises(IntegrityError):
            _check_transport(frame, block, source, package=True)


if __name__ == "__main__":
    unittest.main()
