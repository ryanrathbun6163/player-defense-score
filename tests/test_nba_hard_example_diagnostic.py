"""Consume actual action-producer rows; no real model, source image or media."""
import copy
import unittest

import numpy as np

from src.ball_tracking import nba_action_observation as producer
from src.ball_tracking import nba_hard_example_diagnostic as diagnostic
from src.ball_tracking import nba_wasb_diagnostic as original


def label(index, center=(50, 50), uncertainty=2):
    return {"frame_index": index, "annotation_status": "labeled", "visibility": "fully_visible",
            "absence_reason": None, "game_ball_identity_certainty": "certain",
            "geometry": {"center_xy_px": list(center), "uncertainty_radius_px": uncertainty,
                         "source": "observed_complete_ball_center"},
            "localization_eligible": True, "difficulty_tags": [], "notes": "Synthetic source evidence"}


class SavedDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.frames = [{"source_frame_index": index, "source_pts_ticks": pts,
                        "png": {"path": f"synthetic_{index}.png", "sha256": "0" * 64, "rgb_sha256": "1" * 64}}
                       for index, pts in zip(range(10, 14), (90000, 91440, 92970, 94410))]
        self.manifest = {"candidate_id": "synthetic", "game_id": "test", "approved_role": "target_case_development",
                         "source_video": {"width_px": 512, "height_px": 288}, "time_base": "1/90000",
                         "frames": self.frames, "source_end_exclusive_pts_ticks": 95940}
        self.reference = {**self.manifest, "annotations": [label(i) for i in range(10, 14)],
                          "origin": {"kind": "assistant_visual_proposal"}, "human_review": {"status": "accepted"}}
        self.observations = {"schema_version": producer.SCHEMA,
                             **{k: self.manifest[k] for k in ("candidate_id", "game_id", "approved_role")},
                             "inference": dict(original.POLICY), "checkpoint": {"sha256": original.EXPANDED_SHA},
                             "frames": [self.emitted(frame, {(50, 50): .9}) for frame in self.frames],
                             "pilot_context_comparison": {"changed_context_frames": [{"source_frame_index": 10}]}}

    def emitted(self, frame, pixels):
        heatmap = np.zeros((288, 512), np.float32)
        for (x, y), mass in pixels.items():
            heatmap[y, x] = mass
        return producer.select_observation(frame, heatmap, 3, self.manifest,
                                           {"kind": "live_action", "source_frame_range_inclusive": [10, 13]})

    def score(self, cohort="hard_example"):
        return diagnostic.score_window(self.reference, self.manifest, self.observations, "test", cohort)

    def test_actual_producer_rows_match_existing_scoring_contract(self):
        expected = original.score_reference(self.reference, self.observations)
        actual = self.score()
        self.assertEqual(actual["summary"]["matched"], expected["summary"]["matched"])
        for row, old in zip(actual["frame_results"], expected["frame_results"]):
            self.assertEqual(row["outcome"], old["outcome"])
            self.assertEqual(row["raw_center_error_px"], old["raw_center_error_px"])
            self.assertEqual(row["candidate_available_within_radius"], old["raw_candidate_available"])

    def test_inclusive_raw_boundary_and_uncertainty_does_not_relax_matching(self):
        self.reference["annotations"][0] = label(10, center=(40, 50), uncertainty=20)
        self.reference["annotations"][1] = label(11, center=(39.9999, 50), uncertainty=20)
        rows = self.score()["frame_results"]
        self.assertEqual(rows[0]["outcome"], "matched")
        self.assertEqual(rows[0]["raw_center_error_px"], 10)
        self.assertEqual(rows[1]["outcome"], "wrong")
        self.assertEqual(rows[1]["uncertainty_adjusted_error_px"], 0)

    def test_oracle_retains_weaker_candidate_when_largest_mass_is_distractor(self):
        self.observations["frames"][0] = self.emitted(self.frames[0], {(50, 50): .5, (100, 100): .9})
        report = self.score()
        row = report["frame_results"][0]
        self.assertEqual(row["outcome"], "wrong")
        self.assertEqual(row["selected_candidate_index"], 1)
        self.assertEqual(row["candidate_indices_within_radius"], [0])
        self.assertTrue(row["alternative_candidate_within_radius"])
        self.assertEqual(report["summary"]["wrong_with_alternative_candidate"], 1)

    def test_missing_means_empty_completed_inventory_and_unknowns_stay_unscored(self):
        self.observations["frames"][0] = self.emitted(self.frames[0], {})
        self.reference["annotations"][1].update(geometry=None, localization_eligible=False)
        self.reference["annotations"][2].update(visibility="indeterminate", geometry=None, localization_eligible=False,
                                                game_ball_identity_certainty="ambiguous")
        report = self.score()
        self.assertEqual(report["frame_results"][0]["outcome"], "missing")
        self.assertFalse(report["frame_results"][0]["candidate_available_within_radius"])
        self.assertEqual(report["summary"]["unscored"], 2)
        self.assertIsNone(report["frame_results"][1]["candidate_available_within_radius"])
        self.assertEqual(report["summary"]["missing_with_candidate"], 0)

    def test_hidden_alarms_only_for_certain_or_probable_hidden_references(self):
        for i in range(3):
            self.reference["annotations"][i].update(visibility="not_visible", absence_reason="occluded",
                                                    geometry=None, localization_eligible=False)
        self.observations["frames"][1] = self.emitted(self.frames[1], {})
        self.reference["annotations"][2]["game_ball_identity_certainty"] = "ambiguous"
        report = self.score()
        self.assertEqual([r["outcome"] for r in report["frame_results"]], ["hidden_alarm", "hidden_quiet", "unscored", "matched"])
        self.assertEqual(report["summary"]["hidden_reference_frames"], 2)
        self.assertEqual(report["summary"]["hidden_alarm_fraction"], .5)

    def test_native_intervals_stop_at_unknown_labels_and_use_next_pts(self):
        for i in range(4):
            self.observations["frames"][i] = self.emitted(self.frames[i], {})
        self.reference["annotations"][2].update(geometry=None, localization_eligible=False)
        intervals = self.score()["failure_intervals"]
        self.assertEqual([r["source_frame_range_inclusive"] for r in intervals], [[10, 11], [13, 13]])
        self.assertEqual(intervals[0]["duration_seconds"], .033)
        self.assertEqual(intervals[1]["duration_seconds"], .017)
        self.assertEqual(intervals[0]["following_frame_cue"]["outcome"], "unscored")
        self.assertIsNone(intervals[1]["following_frame_cue"])

    def test_reference_pts_png_and_acceptance_mismatches_fail(self):
        original_reference = copy.deepcopy(self.reference)
        mutations = [lambda r: r["frames"][0].update(source_pts_ticks=123),
                     lambda r: r["frames"][0]["png"].update(sha256="f" * 64),
                     lambda r: r["human_review"].update(status="pending"),
                     lambda r: r.update(game_id="other")]
        for mutation in mutations:
            self.reference = copy.deepcopy(original_reference)
            mutation(self.reference)
            with self.assertRaises(ValueError):
                self.score()

    def test_candidate_inventory_and_selected_point_inconsistencies_fail(self):
        saved = copy.deepcopy(self.observations)
        mutations = [lambda r: r["frames"][0].update(center_xy_px=[60, 60]),
                     lambda r: r["frames"][0]["candidates"][0].update(candidate_index=2),
                     lambda r: r["frames"][0].update(candidates=[]),
                     lambda r: r["frames"][0].update(inference_status="withheld"),
                     lambda r: r["frames"].pop(),
                     lambda r: r["frames"][0]["candidates"][0].update(in_source_bounds=False)]
        for mutation in mutations:
            self.observations = copy.deepcopy(saved)
            mutation(self.observations)
            with self.assertRaises(ValueError):
                self.score()

    def test_context_edges_flag_only_control_cohort(self):
        self.assertEqual(self.score()["summary"]["changed_pilot_context_edge_frames"], 0)
        self.assertEqual(self.score("pilot_control")["summary"]["changed_pilot_context_edge_frames"], 1)


if __name__ == "__main__":
    unittest.main()
