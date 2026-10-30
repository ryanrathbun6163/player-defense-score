"""Artificial-only, independently assembled scoring/control fixtures."""
import copy
import math
import unittest
from unittest.mock import patch

from src.ball_tracking import crop_cross_detector_corroboration as selector
from src.ball_tracking import crop_cross_detector_corroboration_evaluation as scoring
from src.ball_tracking.annotations import BallAnnotationSet
from src.ball_tracking.detections import BallDetectionRun
from src.ball_tracking.development_experiments import canonical_sha256
from src.ball_tracking.evaluation import evaluate_detections
from test_ball_annotation_foundation import (
    detection, detection_run_payload, not_visible_frame, observed_frame,
    parse_reviewed_annotations,
)

COMMIT, OLD_COMMIT = "d" * 40, "c" * 40


def artificial_run(labels, points, detector):
    model = {"model_name": "RF-DETR Medium COCO" if detector == "rfdetr" else "Ultralytics YOLO11x Detect COCO",
             "package_name": "rfdetr" if detector == "rfdetr" else "ultralytics",
             "target_class_id": 37, "target_class_name": "sports ball", "tiling_enabled": True}
    payload = detection_run_payload(labels, {index: [dict(detection(*point), class_id=37, class_name="sports ball") for point in row]
                                             for index, row in points.items()},
                                    model_overrides=model, detection_run_id="artificial_" + detector)
    return BallDetectionRun.from_mapping(payload)


def manual_observations(run, arm, choices):
    """Saved fixture inputs: no old selector or old observation validator runs."""
    config = dict(arm=arm, confidence_threshold=.01, candidate_cap=None if arm == scoring.TOP else 20,
                  edge_step=None if arm == scoring.TOP else .01, cost_step=None if arm == scoring.TOP else .01)
    if arm == scoring.ARM:
        config = dict(scoring.CONFIG)
    return {"config": config, "variant_id": arm + "_artificial",
            "ranking_code_commit": COMMIT if arm == scoring.ARM else OLD_COMMIT,
            "detector_code_commit": run.model_provenance.code_commit,
            "input_candidate_content_sha256": canonical_sha256(run.to_dict()),
            "source_video": run.source_video.to_dict(), "window": run.window.to_dict(), "possession_id": run.possession_id,
            "frames": [{"frame_index": frame.frame_index, "emitted_candidate_indices": [] if choice is None else [choice],
                        **({"supported_candidate_indices": [candidate.candidate_index for candidate in frame.detections]} if arm == scoring.ARM else {})}
                       for frame, choice in zip(run.frames, choices)]}


def manual_report(labels, run, observations):
    """Make a saved artificial report by direct arithmetic, never old scoring."""
    rows = []
    for label, frame, observation in zip(labels.annotations, run.frames, observations["frames"]):
        emitted = observation["emitted_candidate_indices"]
        error = math.dist(frame.detections[emitted[0]].center_xy_px, label.geometry.center_xy_px) if emitted and label.localization_eligible else None
        matched = bool(error is not None and error <= 10)
        rows.append({"frame_index": frame.frame_index,
                     "scoring_status": "localization_eligible" if label.localization_eligible else "not_visible_negative",
                     "accepted_detection_count": len(emitted),
                     "matched_candidate_index": emitted[0] if matched else None,
                     "matched_center_error_px": error if matched else None})
    report = {"variant_id": observations["variant_id"], "config": copy.deepcopy(observations["config"]),
              "localization_radius_px": 10.0, "selection_purpose": labels.window.selection_purpose,
              "possession_id": run.possession_id, "source_video": run.source_video.to_dict(), "window": run.window.to_dict(),
              "input_model_provenance": run.model_provenance.to_dict(),
              "ranking_code_commit": observations["ranking_code_commit"], "evaluator_code_commit": OLD_COMMIT,
              "observations_content_sha256": canonical_sha256(observations),
              "input_candidate_content_sha256": observations["input_candidate_content_sha256"],
              "annotation_content_sha256": canonical_sha256(labels.to_dict()),
              "matching_rule": "raw center distance; uncertainty diagnostic only", "frame_results": rows}
    if observations["config"]["arm"] == scoring.ARM:
        availability = []
        for label, frame in zip(labels.annotations, run.frames):
            indices = [candidate.candidate_index for candidate in frame.detections
                       if label.localization_eligible and math.dist(candidate.center_xy_px, label.geometry.center_xy_px) <= 10]
            availability.append({"frame_index": frame.frame_index, "localization_eligible": label.localization_eligible,
                                 "original_rf_raw10_candidate_indices": indices if label.localization_eligible else None,
                                 "corroborated_raw10_candidate_indices": indices if label.localization_eligible else None,
                                 "original_rf_raw10_available": bool(indices) if label.localization_eligible else None,
                                 "corroborated_raw10_available": bool(indices) if label.localization_eligible else None})
        frames = [row["frame_index"] for row in availability if row["original_rf_raw10_available"]]
        report["candidate_availability"] = {"postselection_only": True, "eligible_denominator": sum(label.localization_eligible for label in labels.annotations),
                                            "frame_results": availability, "original_rf": {"count": len(frames), "frame_indices": frames},
                                            "corroborated": {"count": len(frames), "frame_indices": frames}}
    return report


def fixture(*, count=6, start=0, purpose="representative_evaluation", possession="possession_001", hidden=(3,)):
    labels = parse_reviewed_annotations([not_visible_frame(start + offset) if offset in hidden else observed_frame(start + offset, center=(32, 30))
                                        for offset in range(count)], possession_id=possession, width_px=160, height_px=90)
    value = labels.to_dict()
    value["window"]["selection_purpose"] = purpose
    labels = BallAnnotationSet.from_mapping(value)
    # Candidate 0 is centered, 1 is a distractor, and 2 is slightly offset but raw10.
    points = {index: [(32, 30, .8), (110, 55, .6), (37, 30, .4)] for index in range(start, start + count)}
    rf = artificial_run(labels, points, "rfdetr")
    yolo = artificial_run(labels, points, "yolo")
    choices = [0] * count
    observations = {arm: manual_observations(rf, arm, choices) for arm in scoring.ARMS}
    reports = {arm: manual_report(labels, rf, observation) for arm, observation in observations.items()}
    window = {"window_id": f"artificial_{purpose}_{possession}_{start}", "purpose": purpose, "possession_id": possession,
              "source_video": rf.source_video.to_dict(), "start_frame_index": start, "end_frame_index": start + count - 1}
    return labels, rf, yolo, observations, reports, window


def set_choices(data, arm, choices):
    labels, rf, _, observations, reports, _ = data
    observations[arm] = manual_observations(rf, arm, choices)
    reports[arm] = manual_report(labels, rf, observations[arm])


def comparison(data):
    _, _, _, observations, reports, window = data
    return scoring.compare_window(window, reports[scoring.ARM], {arm: reports[arm] for arm in scoring.CONTROLS}, observations)


def control_reference(observations, report):
    return {"config": observations["config"], "variant_id": observations["variant_id"],
            "observations_content_sha256": canonical_sha256(observations),
            "input_candidate_content_sha256": observations["input_candidate_content_sha256"],
            "original_selection_commit": observations["ranking_code_commit"],
            "original_detector_commit": observations["detector_code_commit"],
            "frame_count": len(observations["frames"]), "report_content_sha256": canonical_sha256(report),
            "localization_radius_px": 10.0, "original_evaluation_commit": report["evaluator_code_commit"],
            "purpose": report["selection_purpose"]}


def interpreted(first, second=None):
    second = second or fixture(purpose="challenge_evaluation")
    return scoring.development_interpretation([scoring.aggregate_pool([comparison(data)], data[-1]["purpose"])
                                              for data in (first, second)])


class CorroborationEvaluationTests(unittest.TestCase):
    def test_new_arm_scored_once_without_selection_or_pair_replay(self):
        labels, rf, yolo, *_ = fixture()
        observations = selector.select_candidates(rf, yolo, COMMIT)
        with patch.object(selector, "select_candidates", side_effect=AssertionError("reselection forbidden")), \
                patch.object(selector, "box_iou", side_effect=AssertionError("pair replay forbidden")), \
                patch.object(scoring, "evaluate_detections", wraps=evaluate_detections) as evaluator:
            report = scoring.evaluate_selection(labels, rf, observations, COMMIT, yolo_run=yolo)
        self.assertEqual(evaluator.call_count, 1)
        self.assertEqual(evaluator.call_args.kwargs, {"confidence_threshold": .01, "localization_radius_px": 10.0})
        self.assertEqual(report["state_summary"]["counts"]["matched"], 5)
        self.assertEqual(report["state_summary"]["counts"]["alarm"], 1)
        self.assertFalse(report["semantic_identity_labels_created"])
        self.assertFalse(report["absence_is_hidden_label"])
        self.assertEqual(report["input_bindings"], observations["input_bindings"])

    def test_saved_arms_and_unbound_yolo_cannot_be_evaluated(self):
        labels, rf, yolo, observations, *_ = fixture()
        for arm in scoring.CONTROLS:
            with self.subTest(arm=arm), self.assertRaisesRegex(ValueError, "fixed new corroboration"):
                scoring.evaluate_selection(labels, rf, observations[arm], COMMIT, yolo_run=yolo)
        fresh = selector.select_candidates(rf, yolo, COMMIT)
        with self.assertRaises(TypeError):
            scoring.evaluate_selection(labels, rf, fresh, COMMIT)
        altered = copy.deepcopy(fresh)
        altered["input_bindings"]["yolo"]["content_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            scoring.evaluate_selection(labels, rf, altered, COMMIT, yolo_run=yolo)

    def test_postselection_availability_keeps_original_and_supported_separate(self):
        labels, rf, _, *_ = fixture()
        # Both detectors agree on candidate 1, a known artificial non-ball distractor.
        yolo = artificial_run(labels, {index: [(110, 55, .9)] for index in range(6)}, "yolo")
        observations = selector.select_candidates(rf, yolo, COMMIT)
        frozen = copy.deepcopy(observations)
        report = scoring.evaluate_selection(labels, rf, observations, COMMIT, yolo_run=yolo)
        self.assertEqual(observations, frozen)
        availability = report["candidate_availability"]
        self.assertEqual(availability["original_rf"]["count"], 5)
        self.assertEqual(availability["corroborated"]["count"], 0)
        self.assertIsNone(availability["frame_results"][3]["original_rf_raw10_available"])
        self.assertEqual(report["state_summary"]["counts"]["wrong_present"], 5)
        self.assertFalse(availability["semantic_identity_established"])

    def test_copy_saved_controls_preserves_original_bytes_in_memory_and_no_replay(self):
        labels, rf, _, observations, reports, _ = fixture()
        before = copy.deepcopy((observations, reports))
        with patch.object(scoring, "evaluate_detections", side_effect=AssertionError("old scoring forbidden")), \
                patch.object(selector, "select_candidates", side_effect=AssertionError("old selecting forbidden")):
            for arm in scoring.CONTROLS:
                obs, report = observations[arm], reports[arm]
                reference = {"config": obs["config"], "variant_id": obs["variant_id"], "observations_content_sha256": canonical_sha256(obs),
                             "input_candidate_content_sha256": obs["input_candidate_content_sha256"], "original_selection_commit": OLD_COMMIT,
                             "original_detector_commit": rf.model_provenance.code_commit, "frame_count": 6,
                             "report_content_sha256": canonical_sha256(report), "localization_radius_px": 10,
                             "original_evaluation_commit": OLD_COMMIT, "purpose": labels.window.selection_purpose}
                copied_obs = scoring.verify_saved_observations({"observations": obs, "inert_path": "never/read/me"}, reference, rf)
                copied_report = scoring.verify_saved_report(report, reference, copied_obs, rf, labels)
                self.assertEqual(copied_report, report)
                self.assertIsNot(copied_report, report)
                self.assertEqual(copied_report["evaluator_code_commit"], OLD_COMMIT)
                modified = copy.deepcopy(report)
                modified["evaluator_code_commit"] = COMMIT
                with self.assertRaises(ValueError):
                    scoring.verify_saved_report(modified, reference, copied_obs, rf, labels)
        self.assertEqual((observations, reports), before)

    def test_first_frame_can_be_withheld_and_choices_errors_are_explicit(self):
        data = fixture()
        set_choices(data, scoring.ARM, [None, 0, 2, None, 1, 0])
        result = comparison(data)
        self.assertEqual(result["startup"][scoring.ARM]["state"], "missing")
        self.assertFalse(result["startup_parity_required"])
        self.assertEqual(result["candidate_choices_against_top_one"]["counts"], dict(retained=2, suppressed=2, replaced=2, both_missing=0))
        self.assertEqual(result["primary_effects"]["correct_choices_lost"]["frame_indices"], [0, 4])
        self.assertEqual(result["primary_effects"]["wrong_replacements"]["frame_indices"], [4])
        errors = result["paired_original_center_errors"][scoring.TOP]
        replaced = next(row for row in errors if row["frame_index"] == 2)
        self.assertEqual((replaced["old_error_px"], replaced["new_error_px"], replaced["difference_px"], replaced["candidate_choice"]), (0, 5, 5, "replaced"))
        self.assertEqual(result["temporal_metrics"][scoring.ARM]["correct_run_lengths"], [2, 1])

    def test_wrong_suppression_is_favorable_but_not_recovered_localization(self):
        data = fixture()
        set_choices(data, scoring.TOP, [1, 0, 0, 0, 0, 0])
        set_choices(data, scoring.ARM, [None, 0, 0, 0, 0, 0])
        result = interpreted(data)
        self.assertEqual(result["label"], "favorable_development")
        self.assertFalse(result["raw10_matched_coverage_improved_somewhere"])
        self.assertTrue(result["wrong_present_reduced_somewhere"])
        self.assertFalse(result["suppression_alone_is_recovered_localization"])
        self.assertEqual(comparison(data)["primary_effects"]["matches_recovered"]["count"], 0)

    def test_lost_match_excludes_favorable_even_with_offsetting_gain(self):
        data = fixture()
        set_choices(data, scoring.TOP, [0, 1, 1, 0, 0, 0])
        set_choices(data, scoring.ARM, [None, 0, 0, 0, 0, 0])
        result = interpreted(data)
        self.assertEqual(result["label"], "not_favorable")
        self.assertTrue(result["tradeoff"])
        self.assertTrue(result["raw10_matched_coverage_improved_somewhere"])

    def test_lost_match_to_wrong_and_pure_regression(self):
        data = fixture()
        set_choices(data, scoring.ARM, [1, 0, 0, 0, 0, 0])
        result = interpreted(data)
        self.assertEqual(result["label"], "not_favorable")
        self.assertTrue(result["pure_regression"])
        self.assertFalse(result["tradeoff"])

    def test_new_hidden_alarm_excludes_favorable_even_if_hidden_count_drops(self):
        data = fixture(hidden=(2, 3, 4))
        set_choices(data, scoring.TOP, [0, 0, None, 0, 0, 0])
        set_choices(data, scoring.ARM, [0, 0, 1, None, None, 0])
        # This case deliberately describes report transitions directly: the
        # missing baseline output would be impossible under valid top-one
        # selection, but the interpretation predicate must independently refuse it.
        old = scoring.state_summary(data[4][scoring.TOP])
        new = scoring.state_summary(data[4][scoring.ARM])
        unchanged = comparison(fixture())
        unchanged["summaries"][scoring.TOP] = old
        unchanged["summaries"][scoring.ARM] = new
        unchanged["paired_transitions"][scoring.TOP] = scoring.transitions(data[4][scoring.TOP], data[4][scoring.ARM])
        other = comparison(fixture(purpose="challenge_evaluation"))
        result = scoring.development_interpretation([{"purpose": scoring.POOLS[0], "windows": [unchanged]},
                                                     {"purpose": scoring.POOLS[1], "windows": [other]}])
        self.assertEqual(result["label"], "not_favorable")
        self.assertTrue(result["hidden_alarms_reduced_somewhere"])

    def test_unchanged_means_framewise_states_not_counts_or_candidate_equality(self):
        data = fixture()
        set_choices(data, scoring.ARM, [2, 2, 2, 1, 2, 2])
        self.assertEqual(interpreted(data)["label"], "unchanged_measured_outcomes")
        self.assertEqual(len(comparison(data)["changed_emission_frames"][scoring.TOP]), 6)
        set_choices(data, scoring.TOP, [0, 1, 0, 0, 0, 0])
        set_choices(data, scoring.ARM, [1, 0, 0, 0, 0, 0])
        self.assertEqual(interpreted(data)["label"], "not_favorable")

    def test_per_window_regression_cannot_be_hidden_in_pool_gain(self):
        loss = fixture()
        gain = fixture(start=20)
        other = fixture(purpose="challenge_evaluation")
        set_choices(loss, scoring.ARM, [None, 0, 0, 0, 0, 0])
        set_choices(gain, scoring.TOP, [1, 1, 0, 0, 0, 0])
        result = scoring.development_interpretation([scoring.aggregate_pool([comparison(loss), comparison(gain)], scoring.POOLS[0]),
                                                     scoring.aggregate_pool([comparison(other)], scoring.POOLS[1])])
        self.assertEqual(result["label"], "not_favorable")

    def test_complete_transitions_pools_and_control_regressions_are_preserved(self):
        data = fixture()
        set_choices(data, scoring.TOP, [1, 1, 0, 0, None, 0])
        set_choices(data, scoring.ARM, [0, None, 1, None, None, 2])
        result = comparison(data)
        for arm in scoring.CONTROLS:
            table = result["paired_transitions"][arm]
            self.assertEqual(sum(cell["count"] for row in table["eligible"].values() for cell in row.values()), 5)
            self.assertEqual(sum(cell["count"] for row in table["hidden"].values() for cell in row.values()), 1)
        self.assertEqual(result["window_regressions"][scoring.TT]["matched"], -3)
        pool = scoring.aggregate_pool([result], scoring.POOLS[0])
        self.assertTrue(pool["runs_not_concatenated"])
        self.assertEqual(pool["totals"][scoring.ARM]["frames"]["matched"][0], {"window_id": data[-1]["window_id"], "frame_index": 0})
        self.assertEqual(pool["totals"][scoring.ARM]["missed_eligible_count"], 3)
        with self.assertRaisesRegex(ValueError, "separate"):
            scoring.aggregate_pool([result], scoring.POOLS[1])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            scoring.aggregate_pool([result, result], scoring.POOLS[0])

    def test_selected_recovery_episode_has_all_frames_and_nullable_delay(self):
        data = fixture(count=25, start=150, possession="possession_003", purpose="challenge_evaluation", hidden=(15, 16, 17, 18, 19))
        new = [0] * 25
        new[15:22] = [None] * 7
        set_choices(data, scoring.ARM, new)
        set_choices(data, scoring.MEAN, [None] * 25)
        result = comparison(data)["recovery"]
        self.assertEqual([row["frame_index"] for row in result["boundary_frame_results"]], list(range(163, 175)))
        self.assertEqual(result["arms"][scoring.ARM], {"first_subsequent_raw10_match": 172, "delay_frames_from_170": 2, "delay_seconds_from_170": .08})
        self.assertIsNone(result["arms"][scoring.MEAN]["first_subsequent_raw10_match"])
        self.assertTrue(result["frame_170_candidate_availability"]["original_rf_raw10_available"])
        self.assertFalse(result["general_reacquisition_guarantee"])

    def test_mixed_source_or_changed_control_is_refused_without_replay(self):
        data = fixture()
        data[3][scoring.TT]["frames"][0]["emitted_candidate_indices"] = []
        with self.assertRaisesRegex(ValueError, "content/provenance"):
            comparison(data)
        data = fixture()
        data[4][scoring.TOP]["annotation_content_sha256"] = "e" * 64
        with self.assertRaisesRegex(ValueError, "mixes"):
            comparison(data)

    def test_boolean_matched_candidate_cannot_alias_original_index_zero(self):
        data = fixture()
        data[4][scoring.TOP]["frame_results"][0]["matched_candidate_index"] = False
        with self.assertRaisesRegex(ValueError, "emitted candidate"):
            comparison(data)

    def test_availability_totals_lists_flags_and_eligibility_must_reconcile(self):
        changes = [
            lambda value: value["original_rf"].update(count=999),
            lambda value: value["original_rf"].update(frame_indices=[0, 1, 2, 3, 4]),
            lambda value: value["corroborated"].update(count=True),
            lambda value: value["frame_results"][0].update(original_rf_raw10_available=False),
            lambda value: value["frame_results"][0].update(original_rf_raw10_available=1),
            lambda value: value["frame_results"][0].update(corroborated_raw10_candidate_indices=[0, 1, 2]),
            lambda value: value["frame_results"][0].update(original_rf_raw10_candidate_indices=[False, 2]),
            lambda value: value["frame_results"][0].update(original_rf_raw10_candidate_indices=[2, 0]),
            lambda value: value["frame_results"][0].update(localization_eligible=False),
            lambda value: value["frame_results"][3].update(original_rf_raw10_candidate_indices=[]),
        ]
        for change in changes:
            data = fixture()
            change(data[4][scoring.ARM]["candidate_availability"])
            with self.subTest(change=change), self.assertRaises(ValueError):
                comparison(data)

    def test_availability_cannot_claim_unsupported_original_candidate(self):
        data = fixture()
        observation = data[3][scoring.ARM]
        observation["frames"][0]["supported_candidate_indices"] = [0, 1]
        data[4][scoring.ARM]["observations_content_sha256"] = canonical_sha256(observation)
        with self.assertRaisesRegex(ValueError, "supported original"):
            comparison(data)


if __name__ == "__main__":
    unittest.main()
