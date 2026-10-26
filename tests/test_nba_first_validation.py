"""Synthetic CPU producer/consumer checks; no project pixels or model inference."""
from copy import deepcopy
from fractions import Fraction
import json
import unittest

import numpy as np

from src.ball_tracking import nba_first_validation as analysis
from src.ball_tracking import completion_training_runtime as runtime
from src.ball_tracking.nba_action_observation import select_observation, stream_means


def make_block(categories, points=None, durations=None, *, start=120, source_count=None, name="episode"):
    points = [(40, 40) if category == "eligible" else None for category in categories] if points is None else points
    durations = [40] * len(categories) if durations is None else durations
    frames, pts = [], 2000
    for offset, (category, duration) in enumerate(zip(categories, durations, strict=True)):
        index = start + offset
        label = None if category == "unlabeled" else {
            "frame_index": index, "annotation_status": "labeled",
            "visibility": "fully_visible" if category == "eligible" else "not_visible" if category in {"hidden", "probable_hidden"} else "indeterminate",
            "absence_reason": "occluded" if category in {"hidden", "probable_hidden"} else None,
            "game_ball_identity_certainty": "certain" if category in {"eligible", "hidden"} else "probable" if category == "probable_hidden" else "ambiguous",
            "geometry": {"center_xy_px": [40, 40], "source": "observed_complete_ball_center", "uncertainty_radius_px": 2} if category == "eligible" else None,
            "localization_eligible": category == "eligible", "difficulty_tags": [], "notes": "Synthetic fixture."}
        frames.append({"source_frame_index": index, "source_pts_ticks": pts, "duration_ticks": duration,
                       "png": {"path": f"synthetic/{name}/{index}.png", "sha256": "a" * 64}, "annotation": label})
        pts += duration
    block = {"block_id": name, "domain": "nba", "game_id": "synthetic", "role": "checkpoint_validation",
             "source_video": {"width_px": 512, "height_px": 288, "frame_count": source_count or start + len(frames) + 20},
             "time_base": "1/1000", "frames": frames}
    by_frame = {frame["source_frame_index"]: point for frame, point in zip(frames, points, strict=True)}
    def provide(rows):
        maps = np.zeros((3, 288, 512), np.float32)
        for channel, frame in enumerate(rows):
            point = by_frame[frame["source_frame_index"]]
            if point is not None:
                maps[channel, point[1], point[0]] = .75
        return maps
    segment = {"kind": "fixed_checkpoint_validation", "source_frame_range_inclusive": [start, frames[-1]["source_frame_index"]]}
    observations = [select_observation(frame, mean, count, block, segment) for frame, mean, count in stream_means(frames, provide)]
    return block, observations


class NbaFirstValidationTests(unittest.TestCase):
    def test_actual_observation_and_validation_score_producers_retain_counts_and_roles(self):
        block, observations = make_block(["eligible"] * 5 + ["hidden"],
            [(40, 40), (50, 40), (51, 40), None, (40, 40), (40, 40)])
        produced = runtime.scored_block(block, observations)
        record = {"name": "saved", "checkpoint": {"sha256": "synthetic"}, "report": {"blocks": [{**produced, "observations": observations}],
            "cohorts": {"nba_validation": {key: produced[key] for key in ("matched", "wrong", "certain_hidden_emissions")}}}}
        result = analysis.analyze_record([block], json.loads(json.dumps(record)))
        aggregate = result["aggregate"]
        self.assertEqual((aggregate["matched"], aggregate["wrong"], aggregate["missing"]), (3, 1, 1))
        self.assertEqual(aggregate["certain_hidden_emitted_points"], 1)
        self.assertFalse(result["historical_selection_changed"])
        self.assertEqual(result["episodes"][0]["frame_results"][1]["raw_center_error_px"], 10)
        self.assertEqual(result["episodes"][0]["frame_results"][2]["outcome"], "wrong")
        self.assertEqual(result["episodes"][0]["frame_results"][2]["uncertainty_adjusted_error_px"], 9)
        self.assertTrue(all(row["exposure_role"] == "checkpoint_validation" for row in result["episodes"][0]["frame_results"]))
        self.assertEqual(result["episodes"][0]["summary"]["wrong_objects"]["gate"]["status"], "inconclusive")

    def test_native_variable_intervals_and_omitted_outer_context_are_censored(self):
        block, observations = make_block(["eligible"] * 3, [None] * 3, [16, 17, 16])
        result = analysis.score_block(block, observations)
        gap = result["summary"]["missing_runs"]
        self.assertEqual(gap["worst_known_duration"]["exact_seconds"], "49/1000")
        self.assertEqual(gap["gate"]["status"], "inconclusive")
        self.assertEqual(len(gap["scope_censored_runs"]), 1)
        self.assertEqual(result["frame_results"][-1]["duration_ticks"], 16)
        self.assertEqual(result["scope_censoring"], {"left_unobserved": True, "right_unobserved": True,
            "source_frame_range_inclusive": [120, 122], "source_frame_count": 143, "outside_context_inferred": False})
        block, observations = make_block(["eligible"] * 3, [None] * 3, [16, 17, 16], start=0, source_count=3)
        complete = analysis.score_block(block, observations)["summary"]["missing_runs"]
        self.assertEqual(complete["gate"]["status"], "pass")
        self.assertEqual(complete["scope_censored_runs"], [])

    def test_known_excessive_missing_gap_fails_even_when_scope_censored(self):
        for final, expected in ((60, "inconclusive"), (61, "fail")):
            block, observations = make_block(["eligible"] * 3, [None] * 3, [70, 70, final])
            result = analysis.score_block(block, observations)
            self.assertEqual(result["summary"]["missing_runs"]["gate"]["status"], expected)
            self.assertEqual(Fraction(result["summary"]["missing_runs"]["worst_known_duration"]["exact_seconds"]), Fraction(140 + final, 1000))

    def test_recovery_is_inclusive120ms_and_requires_following_two_correct_frames(self):
        points = [None] * 4 + [(40, 40)] * 3
        block, observations = make_block(["hidden"] + ["eligible"] * 6, points)
        recovery = analysis.score_block(block, observations)["summary"]["recoveries"]
        self.assertEqual(recovery["gate"]["status"], "pass")
        self.assertEqual(recovery["events"][0]["latency"]["exact_seconds"], "3/25")
        self.assertEqual(recovery["events"][0]["stability_frame_indices"], [124, 125, 126])
        block, observations = make_block(["hidden"] + ["eligible"] * 5, points[:-1])
        recovery = analysis.score_block(block, observations)["summary"]["recoveries"]
        self.assertEqual(recovery["gate"]["status"], "inconclusive")
        self.assertTrue(recovery["events"][0]["censored"])
        block, observations = make_block(["hidden"] + ["eligible"] * 6,
            [None] * 4 + [(40, 40), (70, 70), (40, 40)])
        self.assertEqual(analysis.score_block(block, observations)["summary"]["recoveries"]["gate"]["status"], "fail")

    def test_sparse_references_and_uncertain_hidden_are_not_filled_or_certified(self):
        block, observations = make_block(["eligible", "unlabeled", "eligible", "probable_hidden", "eligible", "eligible"],
            [None, None, None, (40, 40), (40, 40), (40, 40)], [80, 80, 80, 17, 16, 17])
        block["role"] = "post_selection_evaluation_only"
        block["frames"][0]["reference_role"] = "historical_training"
        result = analysis.score_block(block, observations)
        self.assertEqual(result["summary"]["unscored"], 2)
        self.assertEqual(result["summary"]["certain_hidden_emitted_points"], 0)
        self.assertEqual(result["summary"]["uncertain_hidden_emitted_points"], 1)
        self.assertEqual(result["summary"]["missing_runs"]["gate"]["status"], "inconclusive")
        self.assertEqual(result["summary"]["recoveries"]["gate"]["status"], "inconclusive")
        self.assertEqual(result["frame_results"][1]["reference_category"], "reference_unlabeled")
        self.assertEqual(result["frame_results"][0]["exposure_role"], "historical_training")
        self.assertIsNone(result["human_visual_acceptance"])

    def test_pooling_cannot_conceal_episode_failure_or_join_episode_clocks(self):
        good, good_rows = make_block(["eligible"] * 100, name="good", start=0, source_count=100)
        bad, bad_rows = make_block(["eligible"] * 3, [None, None, (40, 40)], name="bad", start=0, source_count=3)
        result = analysis.aggregate_blocks([analysis.score_block(good, good_rows), analysis.score_block(bad, bad_rows)])
        self.assertGreater(result["fractions"]["matched"]["value"], .95)
        self.assertEqual(result["all_episode_automatic_gate_status"], "fail")
        self.assertEqual(result["episode_gates"]["bad"]["correct_fraction"], "fail")
        self.assertFalse(result["pooled_pass_claimed"])
        self.assertFalse(result["ball_phase_accepted"])
        self.assertEqual(result["worst_episode_known_missing_duration"]["exact_seconds"], "2/25")

    def test_stale_native_transport_components_and_protected_rows_rejected(self):
        block, observations = make_block(["eligible"] * 5)
        for field, value in (("source_frame_index", 999), ("source_pts_ticks", 999),
                             ("source_png", {"sha256": "stale"}), ("temporal_contributions", 1),
                             ("point_origin", "inferred"), ("center_xy_px", [1, 1])):
            changed = deepcopy(observations)
            changed[2][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                analysis.score_block(block, changed)
        altered = deepcopy(block)
        altered["frames"][2]["state"] = "withheld"
        with self.assertRaisesRegex(ValueError, "Protected"):
            analysis.score_block(altered, observations)
        altered = deepcopy(block)
        altered["protected_ranges"] = [[122, 122]]
        with self.assertRaisesRegex(ValueError, "Protected"):
            analysis.score_block(altered, observations)


if __name__ == "__main__":
    unittest.main()
