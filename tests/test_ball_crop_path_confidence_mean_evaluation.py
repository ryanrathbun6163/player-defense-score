"""Artificial-only checks of fixed mean evaluation and preserved controls."""
import copy
from dataclasses import replace
import unittest
from unittest.mock import patch

from src.ball_tracking import crop_path_confidence_mean_evaluation as scoring
from src.ball_tracking.annotations import BallAnnotationSet
from src.ball_tracking.development_experiments import canonical_sha256
from src.ball_tracking.evaluation import evaluate_detections
from test_ball_annotation_foundation import detection, not_visible_frame, observed_frame, parse_detection_run, parse_reviewed_annotations

COMMIT, OLD_COMMIT = "d" * 40, "c" * 40


def fixture(count=6, start=0, purpose="representative_evaluation", hidden=(3,)):
    labels = parse_reviewed_annotations([not_visible_frame(i) if i - start in hidden else observed_frame(i, center=(32, 30))
                                        for i in range(start, start + count)], width_px=160, height_px=90)
    payload = labels.to_dict()
    payload["window"]["selection_purpose"] = purpose
    labels = BallAnnotationSet.from_mapping(payload)
    run = parse_detection_run(labels, {i: [detection(32, 30, .8), detection(110, 55, .6)] for i in range(start, start + count)})
    observations, reports = {}, {}
    for arm in scoring.ARMS:
        config = dict(scoring.CONFIG, arm=arm) if arm != scoring.TOP else dict(arm=arm, confidence_threshold=.01, candidate_cap=None, edge_step=None, cost_step=None)
        rows = []
        for offset, frame in enumerate(run.frames):
            emitted = [] if offset == 2 else [1] if offset == 1 else [0]
            winner = {"endpoint": [frame.frame_index, emitted[0]] if emitted else None,
                      "path": [[frame.frame_index, emitted[0]]] if emitted else [],
                      "node_count": len(emitted), "score": .8 if emitted else 0.0,
                      "endpoint_confidence": .8 if emitted else None}
            rows.append({"frame_index": frame.frame_index, "emitted_candidate_indices": emitted,
                         "ranking": {"winner": winner, "score_margin": .1} if arm != scoring.TOP else None,
                         "decision_reason": "current_endpoint" if emitted else "empty_hypothesis"})
        obs = {"config": config, "variant_id": arm + "_synthetic", "frames": rows,
               "ranking_code_commit": COMMIT if arm == scoring.ARM else OLD_COMMIT,
               "detector_code_commit": run.model_provenance.code_commit,
               "input_candidate_content_sha256": canonical_sha256(run.to_dict()),
               "source_video": run.source_video.to_dict(), "window": run.window.to_dict(), "possession_id": run.possession_id}
        observations[arm] = obs
        selected = replace(run, frames=tuple(replace(f, detections=tuple(c for c in f.detections if c.candidate_index in o["emitted_candidate_indices"]))
                                             for f, o in zip(run.frames, rows)))
        raw = evaluate_detections(labels, selected, confidence_threshold=.01, localization_radius_px=10.0)
        reports[arm] = {"variant_id": obs["variant_id"], "config": config, "localization_radius_px": 10.0,
                       "selection_purpose": purpose, "possession_id": run.possession_id,
                       "source_video": run.source_video.to_dict(), "window": run.window.to_dict(),
                       "input_model_provenance": run.model_provenance.to_dict(),
                       "ranking_code_commit": obs["ranking_code_commit"], "evaluator_code_commit": OLD_COMMIT,
                       "observations_content_sha256": canonical_sha256(obs), "input_candidate_content_sha256": obs["input_candidate_content_sha256"],
                       "annotation_content_sha256": canonical_sha256(labels.to_dict()), "matching_rule": "raw center distance; uncertainty diagnostic only",
                       "metrics": {k: raw[k] for k in scoring.METRICS}, "frame_results": raw["frame_results"]}
    window = {"window_id": "synthetic_" + purpose + "_" + str(start), "purpose": purpose, "possession_id": run.possession_id,
              "source_video": run.source_video.to_dict(), "start_frame_index": start, "end_frame_index": start + count - 1}
    return labels, run, observations, reports, window


def report_reference(report):
    return {"config": report["config"], "localization_radius_px": 10.0,
            "report_content_sha256": canonical_sha256(report), "observations_content_sha256": report["observations_content_sha256"],
            "original_selection_commit": OLD_COMMIT, "original_evaluation_commit": OLD_COMMIT,
            "purpose": report["selection_purpose"]}


class MeanEvaluationTests(unittest.TestCase):
    def test_only_new_fixed_arm_is_evaluated_once(self):
        labels, run, observations, _, _ = fixture()
        with patch.object(scoring, "evaluate_detections", wraps=evaluate_detections) as call:
            report = scoring.evaluate_unit(labels, run, observations[scoring.ARM], COMMIT)
        self.assertEqual(call.call_count, 1)
        self.assertEqual(call.call_args.kwargs, dict(confidence_threshold=.01, localization_radius_px=10.0))
        self.assertEqual(report["state_summary"]["counts"], dict(matched=3, wrong_present=1, missing=1, alarm=1, no_current_output=0, ineligible=0))
        self.assertEqual(report["state_summary"]["missed_eligible_count"], 2)
        for arm in (scoring.TT, scoring.TOP):
            with self.assertRaisesRegex(ValueError, "fixed new mean"):
                scoring.evaluate_unit(labels, run, observations[arm], COMMIT)

    def test_unknown_index_candidate_namespace_and_wrong_config_refused(self):
        labels, run, observations, _, _ = fixture()
        for mutate in (lambda o: o["frames"][0].update(emitted_candidate_indices=[99]),
                       lambda o: o.update(input_candidate_content_sha256="0" * 64),
                       lambda o: o["config"].update(confidence_threshold=.2)):
            obs = copy.deepcopy(observations[scoring.ARM])
            mutate(obs)
            with self.assertRaises(ValueError):
                scoring.evaluate_unit(labels, run, obs, COMMIT)

    def test_old_report_copy_never_calls_evaluator_or_changes_commit(self):
        labels, run, observations, reports, _ = fixture()
        report = reports[scoring.TT]
        before = copy.deepcopy(report)
        with patch.object(scoring, "evaluate_detections", side_effect=AssertionError("old evaluator forbidden")):
            copied = scoring.verify_saved_report(report, report_reference(report), observations[scoring.TT], run, labels)
        self.assertEqual(report, before)
        self.assertEqual(copied, before)
        self.assertIsNot(copied, report)
        self.assertEqual(copied["evaluator_code_commit"], OLD_COMMIT)
        tampered = copy.deepcopy(report)
        tampered["evaluator_code_commit"] = COMMIT
        with self.assertRaises(ValueError):
            scoring.verify_saved_report(tampered, report_reference(report), observations[scoring.TT], run, labels)

    def test_old_observation_copy_no_selection_and_null_top_cap_preserved(self):
        _, run, observations, _, _ = fixture()
        for arm in (scoring.TT, scoring.TOP):
            obs = observations[arm]
            ref = {"config": obs["config"], "variant_id": obs["variant_id"],
                   "observations_content_sha256": canonical_sha256(obs), "input_candidate_content_sha256": obs["input_candidate_content_sha256"],
                   "original_selection_commit": OLD_COMMIT, "original_detector_commit": run.model_provenance.code_commit, "frame_count": 6}
            copied = scoring.verify_saved_observations({"observations": obs, "inert": "do/not/follow"}, ref, run)
            self.assertEqual(copied, obs)
            self.assertIsNot(copied, obs)

    def test_hidden_breaks_correct_and_missed_runs_and_discontinuity_breaks(self):
        _, _, _, reports, _ = fixture()
        metrics = scoring.temporal_metrics(reports[scoring.ARM])
        self.assertEqual(metrics["correct_run_lengths"], [1, 2])
        self.assertEqual(metrics["missed_eligible_run_lengths"], [2])
        altered = copy.deepcopy(reports[scoring.ARM])
        altered["frame_results"][5]["frame_index"] = 8
        self.assertEqual(scoring.temporal_metrics(altered)["correct_run_lengths"], [1, 1, 1])
        self.assertEqual(scoring.temporal_metrics({"frame_results": []})["longest_missed_eligible_run"], 0)

    def test_exact_three_by_three_and_hidden_two_by_two(self):
        _, _, _, reports, _ = fixture()
        old, new = reports[scoring.TT], copy.deepcopy(reports[scoring.ARM])
        new["frame_results"][1]["matched_candidate_index"] = 1
        new["frame_results"][2]["accepted_detection_count"] = 1
        new["frame_results"][3]["accepted_detection_count"] = 0
        table = scoring.transitions(old, new)
        self.assertEqual(table["eligible"]["wrong_present"]["matched"], {"count": 1, "frame_indices": [1]})
        self.assertEqual(table["eligible"]["missing"]["wrong_present"]["frame_indices"], [2])
        self.assertEqual(table["hidden"]["alarm"]["no_current_output"]["frame_indices"], [3])
        self.assertEqual(sum(c["count"] for row in table["eligible"].values() for c in row.values()), 5)

    def test_hidden_center_and_duplicate_result_frames_refused(self):
        _, _, _, reports, _ = fixture()
        hidden = copy.deepcopy(reports[scoring.ARM]["frame_results"][3])
        hidden["matched_candidate_index"] = 0
        with self.assertRaisesRegex(ValueError, "Hidden"):
            scoring.frame_state(hidden)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            scoring.state_summary({"frame_results": [hidden, hidden]})

    def test_every_transition_cell_has_exactly_one_frame_without_double_counting(self):
        _, _, _, reports, _ = fixture()
        old, new = copy.deepcopy(reports[scoring.TT]), copy.deepcopy(reports[scoring.ARM])
        old["frame_results"], new["frame_results"] = [], []
        index = 0
        for states, status in ((scoring.STATES, "localization_eligible"), (scoring.HIDDEN_STATES, "not_visible_negative")):
            for before in states:
                for after in states:
                    for target, state in ((old, before), (new, after)):
                        target["frame_results"].append({"frame_index": index, "scoring_status": status,
                            "accepted_detection_count": int(state in ("matched", "wrong_present", "alarm")),
                            "matched_candidate_index": 0 if state == "matched" else None})
                    index += 1
        transitions = scoring.transitions(old, new)
        cells = [cell for kind in transitions.values() for row in kind.values() for cell in row.values()]
        self.assertEqual(len(cells), 13)
        self.assertTrue(all(cell["count"] == 1 for cell in cells))
        self.assertEqual(sorted(f for cell in cells for f in cell["frame_indices"]), list(range(13)))

    def test_startup_parity_and_separate_pool_keyed_frames(self):
        _, _, observations, reports, window = fixture()
        comparison = scoring.compare_window(window, reports[scoring.ARM], {a: reports[a] for a in (scoring.TT, scoring.TOP)}, observations)
        pool = scoring.aggregate_pool([comparison], window["purpose"])
        cell = pool["paired_transitions"][scoring.TT]["eligible"]["matched"]["matched"]
        self.assertEqual(cell["frames"][0], {"window_id": window["window_id"], "frame_index": 0})
        self.assertTrue(pool["runs_not_concatenated"])
        with self.assertRaisesRegex(ValueError, "separate"):
            scoring.aggregate_pool([comparison], "challenge_evaluation")
        observations[scoring.ARM]["frames"][0]["emitted_candidate_indices"] = []
        with self.assertRaisesRegex(ValueError, "startup"):
            scoring.compare_window(window, reports[scoring.ARM], {a: reports[a] for a in (scoring.TT, scoring.TOP)}, observations)

    def test_older_empty_singleton_path_counts(self):
        _, _, observations, _, _ = fixture()
        obs = observations[scoring.ARM]
        obs["frames"][2]["ranking"]["winner"] = dict(endpoint=[1, 1], path=[[0, 1], [1, 1]], node_count=2)
        result = scoring.path_metrics(obs)
        self.assertEqual(result["endpoint_choice_counts"], dict(current=5, older=1, empty=0))
        self.assertEqual(result["singleton_emission_count"], 5)
        self.assertEqual(result["path_node_counts"], {"1": 5, "2": 1})

    def test_wrong_to_missing_is_not_favorable(self):
        pools = []
        for purpose in scoring.POOLS:
            _, _, observations, reports, window = fixture(purpose=purpose)
            comparison = scoring.compare_window(window, reports[scoring.ARM], {a: reports[a] for a in (scoring.TT, scoring.TOP)}, observations)
            pools.append(scoring.aggregate_pool([comparison], purpose))
        self.assertEqual(scoring.development_interpretation(pools)["label"], "unchanged")
        pools[0]["totals"][scoring.ARM]["counts"]["wrong_present"] -= 1
        pools[0]["totals"][scoring.ARM]["counts"]["missing"] += 1
        self.assertFalse(scoring.development_interpretation(pools)["favorable_development_signal"])
        self.assertEqual(scoring.development_interpretation(pools)["label"], "mixed")

    def test_favorable_pool_totals_disclose_window_regressions(self):
        pools = []
        for purpose in scoring.POOLS:
            _, _, observations, reports, window = fixture(purpose=purpose)
            comparison = scoring.compare_window(window, reports[scoring.ARM], {a: reports[a] for a in (scoring.TT, scoring.TOP)}, observations)
            pools.append(scoring.aggregate_pool([comparison], purpose))
        pools[0]["totals"][scoring.ARM]["counts"]["matched"] += 1
        pools[0]["totals"][scoring.ARM]["counts"]["wrong_present"] -= 1
        pools[0]["window_regressions"] = [{"against": scoring.TT, "window_id": "other", "deltas": {"matched": -1}}]
        self.assertEqual(scoring.development_interpretation(pools)["label"], "favorable pool totals with window regressions")

    def test_diagnostic_keeps_null_human_indices_and_new_identity_unknown(self):
        _, _, observations, _, _ = fixture(25, start=300, hidden=())
        human = [{"frame_index": i, "status": "reviewed", "reviewer": "Ryan", "emitted_candidate_index": 0 if i == 300 else None,
                  "candidate_identity": "another_object", "actual_response": "synthetic human record"} for i in scoring.DIAGNOSTIC_FRAMES]
        # The diagnostic requires eight emitted old choices; this artificial
        # fixture's generic missing row is replaced without running a selector.
        observations[scoring.TT]["frames"][2]["emitted_candidate_indices"] = [0]
        result = scoring.diagnostic_rows(scoring.DIAGNOSTIC_WINDOW, observations, human)
        self.assertEqual(len(result), 8)
        self.assertIsNone(result[1]["saved_tt"]["original_human_record"]["emitted_candidate_index"])
        self.assertTrue(all(row["new_mean"]["semantic_identity"] is None for row in result))
        self.assertEqual(sum(row["prior_contrast_context"] == "one_of_six_history_dominated_saved_comparisons" for row in result), 6)


if __name__ == "__main__":
    unittest.main()
