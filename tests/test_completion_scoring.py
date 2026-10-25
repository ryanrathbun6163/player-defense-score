"""CPU-only metric checks; actual observation producer supplies transport fixture.

No saved source images, candidate output, GPU, model, or protected data is read.
"""

import copy
from fractions import Fraction
import json
import unittest

import numpy as np

from src.ball_tracking.annotations import FrameAnnotation
from src.ball_tracking import completion_scoring as scoring
from src.ball_tracking.nba_action_observation import select_observation
from src.ball_tracking.nba_wasb_diagnostic import score_reference


def annotation(index, category="eligible", center=(40, 40), certainty="certain"):
    visible = category in {"eligible", "partial_null"}
    return {"frame_index": index, "annotation_status": "labeled",
            "visibility": "fully_visible" if category == "eligible" else
                          "partially_visible" if category == "partial_null" else
                          "not_visible" if category in {"hidden", "outside"} else "indeterminate",
            "absence_reason": "occluded" if category == "hidden" else "out_of_frame" if category == "outside" else None,
            "game_ball_identity_certainty": certainty if visible or category in {"hidden", "outside"} else "ambiguous",
            "geometry": {"center_xy_px": list(center), "source": "observed_complete_ball_center",
                         "uncertainty_radius_px": 2} if category == "eligible" else None,
            "localization_eligible": category == "eligible", "difficulty_tags": [], "notes": "Synthetic current-frame reference."}


def fixture(categories, points=None, durations=None, *, start=0, pts_origin=0):
    durations = [40] * len(categories) if durations is None else durations
    points = [(40, 40) if c == "eligible" else None for c in categories] if points is None else points
    frames, observations = [], []
    pts = pts_origin
    for offset, (category, point, duration) in enumerate(zip(categories, points, durations, strict=True)):
        index = start + offset
        png = {"path": f"synthetic_{index}.png", "sha256": "0" * 64}
        frame = {"source_frame_index": index, "source_pts_ticks": pts, "duration_ticks": duration,
                 "png": png, "annotation": None if category == "unlabeled" else annotation(index, category),
                 "block_id": "source_segment_a", "reference_role": "post_selection_development"}
        observations.append({"source_frame_index": index, "source_pts_ticks": pts, "source_png": png,
                             "inference_status": "completed", "center_xy_px": None if point is None else list(point)})
        frames.append(frame)
        pts += duration
    return {"block_id": "test", "source_video": {"width_px": 512, "height_px": 288},
            "time_base": "1/1000", "frames": frames}, observations


def review(observations, decision="not_wrong_object"):
    return [{"source_frame_index": row["source_frame_index"], "source_pts_ticks": row["source_pts_ticks"],
             "point_id": "selected", "center_xy_px": row["center_xy_px"], "decision": decision,
             "evidence": {"reviewer": "synthetic fixture", "basis": "Explicit test identity judgment; no images."}}
            for row in observations if row["center_xy_px"] is not None]


class CompletionScoringTests(unittest.TestCase):
    def test_actual_observation_producer_and_annotation_consumer_join(self):
        timeline, _ = fixture(["eligible"] * 3, start=120, pts_origin=2000)
        timeline["possession_id"] = "synthetic_possession"
        observations = []
        bounds = type("Bounds", (), timeline["source_video"])()
        for offset, (frame, coordinate) in enumerate(zip(timeline["frames"], [(50, 40), (51, 40), None])):
            # Use the production annotation parser/serializer and production
            # heatmap-component selector, not a copied observation schema.
            frame["annotation"] = FrameAnnotation.from_mapping(frame["annotation"], offset, bounds).to_dict()
            mean = np.zeros((288, 512), dtype=np.float32)
            if coordinate is not None:
                mean[coordinate[1], coordinate[0]] = .75
            observations.append(select_observation(frame, mean, 1, timeline, {"kind": "live_action"}))
        actual = scoring.score_timeline(timeline, observations)
        self.assertEqual(actual["possession_id"], "synthetic_possession")
        reference = {"frames": timeline["frames"], "annotations": [f["annotation"] for f in timeline["frames"]],
                     "source_video": timeline["source_video"], "candidate_id": "fixture", "game_id": "fixture",
                     "approved_role": "development"}
        original_reader = score_reference(reference, {"frames": observations})
        self.assertEqual([r["outcome"] for r in actual["frame_results"]], ["matched", "wrong", "missing"])
        self.assertEqual([r["outcome"] for r in original_reader["frame_results"]],
                         [r["outcome"] for r in actual["frame_results"]])
        self.assertEqual(actual["frame_results"][1]["raw_center_error_px"], 11)
        self.assertEqual(actual["frame_results"][1]["uncertainty_adjusted_error_px"], 9)
        self.assertEqual(actual["summary"]["wrong_objects"]["gate"]["status"], "inconclusive")
        self.assertFalse(actual["summary"]["wrong_objects"]["confirmed_runs"])
        json.dumps(actual, allow_nan=False)
        stale = copy.deepcopy(observations)
        stale[0]["source_png"]["sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "PNG join"):
            scoring.score_timeline(timeline, stale)

    def test_integer_fractions_cannot_round_into_passage(self):
        timeline, observations = fixture(["eligible"] * 19, [(40, 40)] * 18 + [None])
        report = scoring.score_timeline(timeline, observations)["summary"]
        self.assertEqual(report["gates"]["correct_fraction"]["status"], "fail")
        self.assertEqual(report["resolution_trigger_deficits"]["additional_matches_needed"], 1)
        timeline, observations = fixture(["eligible"] * 21, [(40, 40)] * 20 + [(80, 80)])
        report = scoring.score_timeline(timeline, observations)["summary"]
        self.assertEqual(report["gates"]["correct_fraction"]["status"], "pass")
        self.assertEqual(report["gates"]["wrong_fraction"]["status"], "fail")
        self.assertEqual(report["resolution_trigger_deficits"]["wrong_to_correct_needed"], 1)
        self.assertEqual(report["fractions"]["matched"]["denominator"], 21)
        self.assertEqual(report["resolution_trigger_deficits"]["trigger_status"], "not_assessed")

    def test_missing_run_uses_exact_display_durations_and_strict_limit(self):
        for last_duration, expected in [(100, "pass"), (101, "fail")]:
            timeline, observations = fixture(["eligible"] * 3, [None] * 3, [37, 63, last_duration])
            gaps = scoring.score_timeline(timeline, observations)["summary"]["missing_runs"]
            self.assertEqual(gaps["gate"]["status"], expected)
            self.assertEqual(Fraction(gaps["worst_known_duration"]["exact_seconds"]), Fraction(100 + last_duration, 1000))
            self.assertEqual(gaps["known_runs"][0]["end_exclusive_pts_ticks"], 100 + last_duration)

    def test_unknown_cannot_split_potential_excessive_gap(self):
        timeline, observations = fixture(["eligible", "unknown", "eligible"], [None] * 3, [80] * 3)
        report = scoring.score_timeline(timeline, observations)["summary"]
        self.assertEqual(report["missing_runs"]["gate"]["status"], "inconclusive")
        self.assertEqual(report["missing_runs"]["uncertain_possible_runs"][0]["duration"]["exact_seconds"], "6/25")
        self.assertEqual(report["missing"], 2)
        self.assertEqual(report["unscored"], 1)
        self.assertEqual(report["certain_hidden_emitted_points"], 0)
        timeline["frames"][1]["annotation"] = annotation(1, "hidden")
        report = scoring.score_timeline(timeline, observations)["summary"]
        self.assertEqual(report["missing_runs"]["gate"]["status"], "pass")
        timeline["frames"][1]["annotation"]["game_ball_identity_certainty"] = "probable"
        report = scoring.score_timeline(timeline, observations)["summary"]
        self.assertEqual(report["missing_runs"]["gate"]["status"], "inconclusive")

    def test_inferred_manual_points_are_absent_automatically_but_hidden_emissions(self):
        timeline, observations = fixture(["eligible", "hidden"], [(40, 40)] * 2)
        observations[0]["point_origin"] = "inferred"
        observations[1]["point_origin"] = "manual"
        report = scoring.score_timeline(timeline, observations)
        self.assertEqual(report["summary"]["missing"], 1)
        self.assertEqual(report["summary"]["matched"], 0)
        self.assertEqual(report["summary"]["certain_hidden_emitted_points"], 1)
        self.assertEqual(report["summary"]["gates"]["certain_hidden_emissions"]["status"], "fail")
        self.assertIsNone(report["frame_results"][0]["automatic_center_xy_px"])
        explicit = [{"source_frame_index": r["source_frame_index"], "source_pts_ticks": r["source_pts_ticks"],
                     "points": [{"point_id": "selected", "center_xy_px": r["center_xy_px"], "point_origin": r["point_origin"]}]}
                    for r in observations]
        explicit[1]["points"].append({"point_id": "fill", "center_xy_px": [50, 50], "point_origin": "inferred"})
        report = scoring.score_timeline(timeline, observations, published_observations=explicit)
        self.assertEqual(report["summary"]["certain_hidden_emitted_points"], 2)
        self.assertEqual(report["summary"]["certain_hidden_emitted_frames"], 1)
        explicit[0]["points"] = []
        with self.assertRaisesRegex(ValueError, "omitted the selected"):
            scoring.score_timeline(timeline, observations, published_observations=explicit)

    def test_recovery_deadline_inclusive_first_correct_and_three_native_frames(self):
        timeline, observations = fixture(["hidden"] + ["eligible"] * 6,
                                         [None] * 4 + [(40, 40)] * 3)
        recovery = scoring.score_timeline(timeline, observations)["summary"]["recoveries"]
        self.assertEqual(recovery["gate"]["status"], "pass")
        self.assertEqual(recovery["events"][0]["latency"]["exact_seconds"], "3/25")
        self.assertEqual(recovery["events"][0]["stability_frame_indices"], [4, 5, 6])
        observations[4]["center_xy_px"] = None
        recovery = scoring.score_timeline(timeline, observations)["summary"]["recoveries"]
        self.assertEqual(recovery["gate"]["status"], "fail")
        self.assertTrue(recovery["events"][0]["censored"])
        self.assertEqual(recovery["events"][0]["latency"]["exact_seconds"], "4/25")

    def test_recovery_does_not_substitute_a_later_stable_triple(self):
        timeline, observations = fixture(["hidden"] + ["eligible"] * 5,
                                         [None, (40, 40), (80, 80), (40, 40), (40, 40), (40, 40)])
        recovery = scoring.score_timeline(timeline, observations)["summary"]["recoveries"]
        self.assertEqual(recovery["gate"]["status"], "fail")
        self.assertEqual(recovery["events"][0]["first_correct_frame_index"], 1)

    def test_recovery_censoring_no_event_cut_and_uncertain_occlusion(self):
        timeline, observations = fixture(["hidden", "eligible", "eligible"])
        report = scoring.score_timeline(timeline, observations)["summary"]["recoveries"]
        self.assertEqual(report["gate"]["status"], "inconclusive")
        self.assertEqual(report["scored_event_count"], 0)
        self.assertEqual(report["censored_event_count"], 1)
        timeline, observations = fixture(["eligible"] * 3)
        self.assertEqual(scoring.score_timeline(timeline, observations)["summary"]["recoveries"]["gate"]["status"], "not_applicable")
        timeline, observations = fixture(["hidden"] + ["eligible"] * 3)
        timeline["frames"][0]["block_id"] = "before_camera_cut"
        recovery = scoring.score_timeline(timeline, observations)["summary"]["recoveries"]
        self.assertEqual(recovery["gate"]["status"], "inconclusive")
        self.assertIsNone(recovery["events"][0]["return_frame_index"])
        timeline["frames"][0]["block_id"] = "source_segment_a"
        timeline["frames"][0]["annotation"]["game_ball_identity_certainty"] = "probable"
        self.assertEqual(scoring.score_timeline(timeline, observations)["summary"]["recoveries"]["gate"]["status"], "inconclusive")

    def test_no_correct_before_observed_deadline_is_fail_short_window_is_censored(self):
        for length, status in [(3, "inconclusive"), (4, "fail")]:
            timeline, observations = fixture(["hidden"] + ["eligible"] * length, [None] * (length + 1))
            recovery = scoring.score_timeline(timeline, observations)["summary"]["recoveries"]
            self.assertEqual(recovery["gate"]["status"], status)

    def test_recovery_deadline_inside_last_display_interval_is_observed(self):
        for durations, status in [([200], "fail"), ([100, 100], "fail"),
                                  ([60, 60], "inconclusive"), ([60, 61], "fail")]:
            timeline, observations = fixture(["hidden"] + ["eligible"] * len(durations),
                                             [None] * (len(durations) + 1), [40] + durations)
            recovery = scoring.score_timeline(timeline, observations)["summary"]["recoveries"]
            self.assertEqual(recovery["gate"]["status"], status)
            self.assertEqual(Fraction(recovery["events"][0]["eligible_return_window"]["duration"]["exact_seconds"]),
                             Fraction(sum(durations), 1000))

    def test_wrong_object_requires_explicit_current_point_review_and_120ms_fails(self):
        for length, status in [(2, "pass"), (3, "fail")]:
            timeline, observations = fixture(["eligible"] * length, [(80, 80)] * length)
            unreviewed = scoring.score_timeline(timeline, observations)["summary"]["wrong_objects"]
            self.assertEqual(unreviewed["gate"]["status"], "inconclusive")
            self.assertEqual(unreviewed["confirmed_runs"], [])
            report = scoring.score_timeline(timeline, observations, wrong_object_judgments=review(observations, "confirmed_wrong_object"))
            self.assertEqual(report["summary"]["wrong_objects"]["gate"]["status"], status)
        stale = review(observations)
        stale[0]["center_xy_px"] = [40, 40]
        with self.assertRaisesRegex(ValueError, "point join"):
            scoring.score_timeline(timeline, observations, wrong_object_judgments=stale)

    def test_wrong_object_runs_are_censored_at_unscored_boundaries_not_camera_cuts(self):
        for side_length, expected in [(2, "inconclusive"), (3, "fail")]:
            size = side_length * 2 + 1
            timeline, observations = fixture(["eligible"] * size, [(80, 80)] * size)
            timeline["frames"][side_length].update(state="withheld", block_id=None, png=None, annotation=None)
            observations.pop(side_length)
            report = scoring.score_timeline(timeline, observations,
                wrong_object_judgments=review(observations, "confirmed_wrong_object"))["summary"]["wrong_objects"]
            self.assertEqual(report["gate"]["status"], expected)
            self.assertEqual(len(report["scope_censored_runs"]), 2)
            self.assertEqual([r["frames"] for r in report["confirmed_runs"]], [side_length] * 2)
        timeline, observations = fixture(["eligible"] * 4, [(80, 80)] * 4)
        for frame in timeline["frames"][2:]:
            frame["block_id"] = "after_camera_cut"
        report = scoring.score_timeline(timeline, observations,
            wrong_object_judgments=review(observations, "confirmed_wrong_object"))["summary"]["wrong_objects"]
        self.assertEqual(report["gate"]["status"], "pass")
        self.assertEqual(report["scope_censored_runs"], [])
        for i, frame in enumerate(timeline["frames"]):
            frame["block_id"] = "source_segment_a"
            frame["reference_role"] = "historical_training" if i in {0, 3} else "post_selection_development"
        report = scoring.score_timeline(timeline, observations,
            wrong_object_judgments=review(observations, "confirmed_wrong_object"))
        self.assertEqual(report["summary"]["wrong_objects"]["gate"]["status"], "fail")
        cohort = report["cohorts"]["historical_training"]["wrong_objects"]
        self.assertEqual(cohort["gate"]["status"], "inconclusive")
        self.assertEqual(len(cohort["scope_censored_runs"]), 2)

    def test_published_and_review_native_timing_are_strictly_joined(self):
        timeline, observations = fixture(["eligible"])
        published = [{"source_frame_index": 0, "source_pts_ticks": 0,
                      "points": [{"point_id": "selected", "center_xy_px": [40, 40], "point_origin": "automatic"}]}]
        for bad_pts in [False, 0.0]:
            changed = copy.deepcopy(published)
            changed[0]["source_pts_ticks"] = bad_pts
            with self.assertRaisesRegex(ValueError, "Published PTS must be an integer"):
                scoring.score_timeline(timeline, observations, published_observations=changed)
        changed = copy.deepcopy(published)
        changed[0]["time_base"] = "1/90000"
        with self.assertRaisesRegex(ValueError, "Published time base"):
            scoring.score_timeline(timeline, observations, published_observations=changed)
        for field, value, expected in [("source_frame_index", False, "frame index"),
                                       ("source_pts_ticks", 0.0, "PTS"),
                                       ("time_base", "1/90000", "time base")]:
            changed = review(observations)
            changed[0][field] = value
            with self.assertRaisesRegex(ValueError, expected):
                scoring.score_timeline(timeline, observations, wrong_object_judgments=changed)

    def test_protected_rows_remain_empty_and_censor_scope_without_creating_recovery(self):
        timeline, observations = fixture(["eligible"] * 3, [None] * 3)
        timeline["frames"][1].update(state="withheld", block_id=None, png=None, annotation=None)
        observations.pop(1)
        report = scoring.score_timeline(timeline, observations)
        self.assertEqual(report["summary"]["withheld"], 1)
        self.assertEqual(report["summary"]["eligible_frames"], 2)
        self.assertEqual(report["summary"]["missing_runs"]["gate"]["status"], "inconclusive")
        self.assertEqual(report["summary"]["recoveries"]["gate"]["status"], "not_applicable")
        self.assertEqual(report["frame_results"][1]["outcome"], "withheld")
        self.assertEqual(report["full_possession_acceptance"], "not_assessed")
        protected_observation = {"source_frame_index": 1, "source_pts_ticks": 40,
                                 "inference_status": "completed", "center_xy_px": None,
                                 "temporal_contributions": 0, "candidates": []}
        with self.assertRaisesRegex(ValueError, "withhold all inference"):
            scoring.score_timeline(timeline, observations + [protected_observation])
        protected_observation["inference_status"] = "withheld"
        scoring.score_timeline(timeline, observations + [protected_observation])
        protected_observation["temporal_contributions"] = 1
        with self.assertRaisesRegex(ValueError, "withhold all inference"):
            scoring.score_timeline(timeline, observations + [protected_observation])
        timeline["frames"][1]["baseline_observation"] = {"center_xy_px": [40, 40]}
        with self.assertRaisesRegex(ValueError, "Protected row"):
            scoring.score_timeline(timeline, observations)
        del timeline["frames"][1]["baseline_observation"]
        timeline["frames"][1]["annotation"] = annotation(1)
        with self.assertRaisesRegex(ValueError, "Protected row"):
            scoring.score_timeline(timeline, observations)

    def test_exposure_changes_do_not_split_source_gap_or_recovery(self):
        timeline, observations = fixture(["eligible"] * 6, [None] * 6)
        for frame in timeline["frames"][:3]:
            frame["reference_role"] = "historical_training"
        report = scoring.score_timeline(timeline, observations)["summary"]["missing_runs"]
        self.assertEqual(report["gate"]["status"], "fail")
        self.assertEqual(report["known_runs"][0]["duration"]["exact_seconds"], "6/25")
        self.assertEqual(report["known_runs"][0]["exposure_role"], "mixed")
        self.assertEqual(len(report["known_runs"][0]["exposure_roles"]), 2)
        for i, frame in enumerate(timeline["frames"]):
            frame["reference_role"] = "historical_training" if i in {0, 1, 4, 5} else "post_selection_development"
        report = scoring.score_timeline(timeline, observations)
        self.assertEqual(report["summary"]["missing_runs"]["gate"]["status"], "fail")
        subset = report["cohorts"]["historical_training"]["missing_runs"]
        self.assertEqual([r["frame_indices"] for r in subset["known_runs"]], [[0, 1], [4, 5]])
        self.assertEqual(subset["gate"]["status"], "inconclusive")
        self.assertEqual(len(subset["scope_censored_runs"]), 2)
        timeline, observations = fixture(["hidden"] + ["eligible"] * 3)
        timeline["frames"][0]["reference_role"] = "historical_training"
        self.assertEqual(scoring.score_timeline(timeline, observations)["summary"]["recoveries"]["gate"]["status"], "pass")

    def test_exposure_cohorts_are_separate_and_unlabeled_never_supplies_accuracy(self):
        timeline, observations = fixture(["eligible", "eligible", "unlabeled"], [None, (40, 40), (80, 80)])
        timeline["frames"][0]["reference_role"] = "historical_training"
        report = scoring.score_timeline(timeline, observations)
        self.assertEqual(report["cohorts"]["historical_training"]["matched"], 0)
        self.assertEqual(report["cohorts"]["post_selection_development"]["matched"], 1)
        self.assertEqual(report["summary"]["eligible_frames"], 2)
        self.assertEqual(report["summary"]["unscored"], 1)
        self.assertEqual(report["summary"]["reference_categories"]["reference_unlabeled"], 1)

    def test_strict_native_identity_explicit_scope_and_no_tool_failure_as_model_miss(self):
        timeline, observations = fixture(["eligible"] * 3)
        cases = []
        bad = copy.deepcopy(timeline); bad["frames"][0]["annotation"]["frame_index"] = 2
        cases.append((bad, observations, "Annotation/native"))
        bad = copy.deepcopy(timeline); del bad["frames"][0]["reference_role"]
        cases.append((bad, observations, "exposure role"))
        bad = copy.deepcopy(observations); bad[0]["source_pts_ticks"] += 1
        cases.append((timeline, bad, "PTS join"))
        for value in [False, 0.0]:
            bad = copy.deepcopy(observations); bad[0]["source_pts_ticks"] = value
            cases.append((timeline, bad, "Observation PTS must be an integer"))
        bad = copy.deepcopy(observations); bad[0]["time_base"] = "1/60000"
        cases.append((timeline, bad, "time base"))
        bad = copy.deepcopy(observations); bad[0].update(inference_status="failed", center_xy_px=None)
        cases.append((timeline, bad, "tooling failure"))
        bad = copy.deepcopy(observations); bad[0]["center_xy_px"] = [float("nan"), 2]
        cases.append((timeline, bad, "finite"))
        bad_native, bad = copy.deepcopy(timeline), copy.deepcopy(observations)
        bad_native["frames"][1]["source_pts_ticks"] = bad[1]["source_pts_ticks"] = 20
        cases.append((bad_native, bad, "must not overlap"))
        for native, emitted, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                scoring.score_timeline(native, emitted)


if __name__ == "__main__":
    unittest.main()
