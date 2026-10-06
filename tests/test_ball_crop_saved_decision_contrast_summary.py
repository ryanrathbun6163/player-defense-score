"""Invented JSON values only: no saved scientific artifact is opened."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest import mock

from src.ball_tracking import crop_saved_decision_contrast_summary as summary


def reseal(pool, wrapper, scope):
    """Pin artificial canonical values after an intentional fixture mutation."""
    digest = summary._canonical(wrapper["observations"])
    scope["frozen_control_reference"]["observations_content_sha256"] = digest
    scope["frozen_report_references"][summary.ARM]["observations_content_sha256"] = digest
    pool["evaluation_reports"][646]["observations_content_sha256"] = digest
    for arm, index in (("crop_top_twenty", 641), (summary.ARM, 646)):
        scope["frozen_report_references"][arm]["report_content_sha256"] = summary._canonical(pool["evaluation_reports"][index])


def make_inputs():
    """Return pool, wrapper, human ledger and scope entirely from invented data."""
    commit, detector, namespace = "1"*40, "2"*40, "3"*64
    pool_binding = {"path": "invented/pool.json", "sha256": "4"*64, "size_bytes": 100}
    obs_binding = {"path": "invented/observations.json", "sha256": "5"*64, "size_bytes": 100}
    prior_scope = {"path": "invented/identity_scope.json", "sha256": "6"*64, "size_bytes": 100}
    variant = summary.ARM + "_" + summary._canonical(summary.TT_CONFIG)[:16]
    scope = {
        "schema_version": "ball_crop_saved_decision_contrast_scope/v0.1",
        "window_id": summary.WINDOW, "possession_id": "possession_003", "purpose": "representative_evaluation",
        "frame_indices": list(summary.FRAMES), "setting": deepcopy(summary.SETTING),
        "scientific_inputs": {"representative_pool": pool_binding, "tt_observations_wrapper": obs_binding},
        "administrative_authorities": {"selection_scope": prior_scope},
        "arithmetic": {"gap_penalty": .25, "motion_penalty": .25, "relative_tolerance": 1e-9, "absolute_tolerance": 1e-9,
                       "current_endpoint_trailing_skips": 0, "tie_definition": "exact_stored_score_equality",
                       "frame300_has_no_prior_history": True, "saved_global_margin_is_not_pair_gap": True},
        "outputs": {"files": {"contrast.json": 131072, "summary.md": 65536, "provenance.json": 131072}},
        "comparison_rule": {"historical_path_bounds": {str(f): {"start": max(300, f-4), "end": f} for f in summary.FRAMES}},
        "frozen_report_references": {},
        "frozen_control_reference": {"window_id": summary.WINDOW, "purpose": "representative_evaluation", "possession_id": "possession_003",
                                     "file": summary._binding(obs_binding), "config": deepcopy(summary.TT_CONFIG), "variant_id": variant,
                                     "observations_content_sha256": "7"*64, "input_candidate_content_sha256": namespace,
                                     "original_selection_commit": commit, "original_detector_commit": detector, "frame_count": 25},
        "selected_method": None, "selected_operating_point": None, "quality_gate": None,
    }
    observations = {
        "schema_version": "ball_crop_motion_observations/v0.1", "variant_id": variant,
        "config": deepcopy(summary.TT_CONFIG), "ranking_code_commit": commit, "detector_code_commit": detector,
        "input_candidate_content_sha256": namespace, "source_video": {"path": "inert/never-open.mp4", "sha256": "8"*64},
        "window": {"start_frame_index": 300, "end_frame_index": 324}, "possession_id": "possession_003",
        "frames": [], "selected_operating_point": None, "quality_gate": None,
    }
    top_frames, tt_frames = [], []
    for frame in range(300, 325):
        top = {"frame_index": frame, "annotation_status": "labeled", "visibility": "fully_visible",
               "scoring_status": "localization_eligible", "accepted_detection_count": 2, "matched_candidate_index": 1,
               "false_positive_count": 1, "false_negative_count": 0, "matched_center_error_px": 4.125}
        tt = dict(top, accepted_detection_count=1, matched_candidate_index=None,
                  false_negative_count=1, matched_center_error_px=None)
        top_frames.append(top)
        tt_frames.append(tt)
        if frame not in summary.FRAMES:
            observations["frames"].append({"frame_index": frame})
            continue
        best, competing = [], []
        for candidate, c in ((0, .8), (1, .6)):
            path = [[frame, candidate]] if frame == 300 else [[frame-1, candidate], [frame, candidate]]
            total = c if frame == 300 else c+.5
            motion = 0.0 if frame == 300 else (.2 if candidate == 0 else .4)
            score = total-.25*motion
            best.append({"endpoint": [frame, candidate], "score": score, "path": path,
                         "confidence_sum": total, "internal_skipped_frames": 0, "normalized_step_squared_sum": motion})
            competing.append({"endpoint": [frame, candidate], "score": score, "path": deepcopy(path),
                              "endpoint_confidence": c, "trailing_skipped_frames": 0})
        competing.append({"endpoint": None, "score": 0.0, "path": [], "endpoint_confidence": None, "trailing_skipped_frames": None})
        observations["frames"].append({"frame_index": frame, "horizon_start": max(300, frame-4), "horizon_end": frame,
                                       "emitted_candidate_indices": [0], "candidate_decisions": [
                                           {"candidate_index": 0, "disposition": "emitted"},
                                           {"candidate_index": 1, "disposition": "eligible_not_emitted"}],
                                       "ranking": {"eligible_edges": {"opaque": "never interpreted"}, "best_path_per_endpoint": best,
                                                   "competing_endpoints": competing, "winner": deepcopy(competing[0]), "score_margin": .05},
                                       "decision_reason": "current_endpoint", "output_state": "tentative_observation"})
    pool = {"schema_version": "ball_crop_motion_pool/v0.1", "purpose": "representative_evaluation",
            "experiment_spec_sha256": "9"*64, "code_commit": commit,
            "evaluation_reports": [None]*647, "selected_operating_point": None, "quality_gate": None}
    for arm, index, config, frames in (("crop_top_twenty", 641, summary.TOP_CONFIG, top_frames),
                                       (summary.ARM, 646, summary.TT_CONFIG, tt_frames)):
        report = {"schema_version": "ball_crop_motion_evaluation/v0.1", "variant_id": arm + "_" + summary._canonical(config)[:16],
                  "config": deepcopy(config), "localization_radius_px": 10.0, "selection_purpose": "representative_evaluation",
                  "possession_id": "possession_003", "source_video": deepcopy(observations["source_video"]),
                  "window": deepcopy(observations["window"]), "input_model_provenance": {"invented": True},
                  "ranking_code_commit": commit, "evaluator_code_commit": commit,
                  "observations_content_sha256": "a"*64, "input_candidate_content_sha256": namespace,
                  "annotation_content_sha256": "b"*64, "matching_rule": "raw center distance; uncertainty diagnostic only",
                  "frame_results": frames, "selected_operating_point": None, "quality_gate": None}
        pool["evaluation_reports"][index] = report
        scope["frozen_report_references"][arm] = {
            "source": dict(summary._binding(pool_binding), json_pointer=f"/evaluation_reports/{index}"),
            "report_content_sha256": "c"*64, "window_id": summary.WINDOW, "purpose": "representative_evaluation",
            "config": deepcopy(config), "localization_radius_px": 10.0,
            "observations_file": summary._binding(obs_binding) if arm == summary.ARM else {"path": "inert/top.json", "sha256": "d"*64},
            "observations_content_sha256": "a"*64, "original_selection_commit": commit, "original_evaluation_commit": commit}
    wrapper = {"experiment_spec_sha256": pool["experiment_spec_sha256"], "input_crop_file": {"path": "inert/no-candidates.json", "sha256": "e"*64},
               "crop_content_sha256": "f"*64, "observations": observations}
    ledger = {"schema_version": "ball_crop_candidate_identity_review_ledger/v0.1", "scope": summary._binding(prior_scope),
              "window_id": summary.WINDOW, "required_reviewer": "Ryan",
              "setting": {"arm": summary.ARM, "policy": "cap20", "confidence_threshold": .01, "localization_radius_source_px": 10.0, "native_view": "view_0"},
              "selection_source": {"frame_indices": list(summary.FRAMES)}, "rows": [],
              "review_record": {"answered_frame_indices": list(summary.FRAMES), "pending_frame_indices": []},
              "selected_method": None, "selected_operating_point": None, "quality_gate": None}
    for frame in summary.FRAMES:
        ledger["rows"].append({"frame_index": frame, "status": "reviewed", "reviewer": "Ryan",
                               "actual_response": "Invented reviewer response.", "prior_localization_outcome": "present_nonmatching_current_output",
                               "emitted_candidate_index": 0 if frame == 300 else None,
                               "candidate_identity": "ball" if frame == 319 else "another_object",
                               "ball_center": "clearly_displaced" if frame == 319 else "not_applicable"})
    reseal(pool, wrapper, scope)
    return pool, wrapper, ledger, scope


class SavedDecisionContrastSummaryTests(unittest.TestCase):
    def setUp(self):
        self.pool, self.wrapper, self.ledger, self.scope = make_inputs()

    def build(self, seal=False):
        if seal:
            reseal(self.pool, self.wrapper, self.scope)
        return summary.build_contrast(self.pool, self.wrapper, self.ledger, self.scope)

    def ranking(self, frame=301):
        return self.wrapper["observations"]["frames"][frame-300]["ranking"]

    def change_score(self, frame, index, *, confidence=None, total=None, motion=None):
        rank = self.ranking(frame)
        best, endpoint = rank["best_path_per_endpoint"][index], rank["competing_endpoints"][index]
        if confidence is not None:
            endpoint["endpoint_confidence"] = confidence
        if total is not None:
            best["confidence_sum"] = total
        if motion is not None:
            best["normalized_step_squared_sum"] = motion
        best["score"] = best["confidence_sum"]-.25*best["internal_skipped_frames"]-.25*best["normalized_step_squared_sum"]
        endpoint["score"] = best["score"]
        rank["winner"] = deepcopy(rank["competing_endpoints"][0])

    def test_all_eight_rows_and_signed_arithmetic_without_mutation(self):
        before = deepcopy((self.pool, self.wrapper, self.ledger, self.scope))
        result = self.build()
        self.assertEqual(before, (self.pool, self.wrapper, self.ledger, self.scope))
        self.assertEqual([r["frame_index"] for r in result["rows"]], list(summary.FRAMES))
        row = result["rows"][1]
        self.assertAlmostEqual(row["pair_score_gap"], .25)
        self.assertEqual(row["contributions"]["winner"]["motion"], -.05)
        self.assertEqual(row["contributions"]["comparison"]["motion"], -.1)
        self.assertAlmostEqual(row["term_contrasts"]["motion"], .05)
        self.assertIs(summary.validate_returned_contrast(result, self.scope, self.ledger), result)

    def test_frame300_confidence_only_and_unchanged_null_human_indices(self):
        result = self.build()
        for name in ("winner", "comparison"):
            self.assertEqual(list(result["rows"][0]["contributions"][name].values())[1:], [0.0, 0.0, 0.0])
        self.assertEqual([r["human_review"]["emitted_candidate_index"] for r in result["rows"]], [0]+[None]*7)

    def test_global_margin_is_not_pair_gap(self):
        row = self.build()["rows"][1]
        self.assertEqual(row["saved_global_score_margin"], .05)
        self.assertNotEqual(row["saved_global_score_margin"], row["pair_score_gap"])

    def test_exact_tie_preserves_lower_original_index_rule(self):
        self.change_score(300, 1, confidence=.8, total=.8)
        self.ranking(300)["score_margin"] = 0.0
        row = self.build(seal=True)["rows"][0]
        self.assertTrue(row["exact_score_tie"])
        self.assertEqual(row["pair_score_gap"], 0)

    def test_near_tie_is_not_exact_tie(self):
        self.change_score(300, 1, confidence=.8-1e-12, total=.8-1e-12)
        self.ranking(300)["score_margin"] = 0.0
        row = self.build(seal=True)["rows"][0]
        self.assertFalse(row["exact_score_tie"])
        self.assertGreater(row["pair_score_gap"], 0)

    def test_tie_with_higher_comparison_confidence_is_rejected(self):
        self.change_score(301, 1, confidence=.9, total=1.3, motion=.2)
        self.ranking()["score_margin"] = 0.0
        with self.assertRaisesRegex(ValueError, "tie order"):
            self.build(seal=True)

    def test_unequal_saved_histories_and_gap_terms(self):
        rank = self.ranking(304)
        for index, path in ((0, [[301, 4], [304, 0]]), (1, [[302, 9], [303, 8], [304, 1]])):
            rank["best_path_per_endpoint"][index]["path"] = deepcopy(path)
            rank["competing_endpoints"][index]["path"] = deepcopy(path)
        rank["best_path_per_endpoint"][0]["internal_skipped_frames"] = 2
        self.change_score(304, 0, total=1.8, motion=.1)
        self.change_score(304, 1, total=1.2, motion=.4)
        row = self.build(seal=True)["rows"][3]
        self.assertEqual(row["term_contrasts"]["internal_gap"], -.5)
        self.assertNotEqual(row["winner"]["best_path"]["path"], row["comparison"]["best_path"]["path"])

    def test_digest_mismatch_is_rejected_before_extraction(self):
        self.pool["evaluation_reports"][641]["frame_results"][0]["matched_center_error_px"] = 3.0
        with self.assertRaisesRegex(ValueError, "digest"):
            self.build()

    def test_observation_digest_mismatch_is_rejected(self):
        self.ranking()["score_margin"] = .04
        with self.assertRaisesRegex(ValueError, "digest"):
            self.build()

    def test_candidate_namespace_mismatch_is_rejected(self):
        self.pool["evaluation_reports"][641]["input_candidate_content_sha256"] = "0"*64
        with self.assertRaisesRegex(ValueError, "provenance"):
            self.build(seal=True)
        self.setUp()
        self.pool["code_commit"] = "0"*40
        with self.assertRaisesRegex(ValueError, "provenance"):
            self.build(seal=True)

    def test_annotation_namespace_mismatch_is_rejected(self):
        self.pool["evaluation_reports"][641]["annotation_content_sha256"] = "0"*64
        with self.assertRaisesRegex(ValueError, "Annotation namespace"):
            self.build(seal=True)

    def test_wrong_config_and_report_pointer_are_rejected(self):
        for operation in (lambda: self.scope["frozen_report_references"][summary.ARM]["source"].update(json_pointer="/evaluation_reports/645"),
                          lambda: self.pool["evaluation_reports"][646]["config"].update(cost_step=.03)):
            self.setUp()
            operation()
            with self.assertRaises(ValueError):
                self.build(seal=True)

    def test_duplicate_or_missing_target_frame_is_rejected(self):
        self.wrapper["observations"]["frames"][1]["frame_index"] = 300
        with self.assertRaisesRegex(ValueError, "frame order"):
            self.build(seal=True)

    def test_duplicate_endpoint_and_disposition_records_are_rejected(self):
        for key in ("best_path_per_endpoint", "competing_endpoints"):
            self.setUp()
            self.ranking()[key].append(deepcopy(self.ranking()[key][0]))
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                self.build(seal=True)
        self.setUp()
        frame = self.wrapper["observations"]["frames"][1]
        frame["candidate_decisions"].append(deepcopy(frame["candidate_decisions"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.build(seal=True)

    def test_missing_comparison_endpoint_or_wrong_retention_is_rejected(self):
        self.ranking()["best_path_per_endpoint"].pop()
        with self.assertRaisesRegex(ValueError, "Missing"):
            self.build(seal=True)
        self.setUp()
        self.wrapper["observations"]["frames"][1]["candidate_decisions"][1]["disposition"] = "outside_top_twenty"
        with self.assertRaisesRegex(ValueError, "retention"):
            self.build(seal=True)

    def test_saved_output_must_be_current_single_nonmatch(self):
        for field, value in (("emitted_candidate_indices", []), ("emitted_candidate_indices", [0, 1]),
                             ("decision_reason", "earlier_endpoint_no_current_observation")):
            self.setUp()
            self.wrapper["observations"]["frames"][1][field] = value
            with self.assertRaises(ValueError):
                self.build(seal=True)
        self.setUp()
        self.pool["evaluation_reports"][646]["frame_results"][1]["matched_candidate_index"] = 0
        with self.assertRaisesRegex(ValueError, "nonmatch"):
            self.build(seal=True)

    def test_unsupported_labels_or_radius_error_are_rejected(self):
        for field, value in (("visibility", "not_visible"), ("annotation_status", "unlabeled"), ("matched_center_error_px", 10.1)):
            self.setUp()
            self.pool["evaluation_reports"][641]["frame_results"][1][field] = value
            with self.assertRaises(ValueError):
                self.build(seal=True)

    def test_bool_nan_infinity_and_negative_numeric_inputs_are_rejected(self):
        for value in (True, float("nan"), float("inf"), -.2):
            self.setUp()
            self.ranking()["competing_endpoints"][1]["endpoint_confidence"] = value
            with self.assertRaises(ValueError):
                self.build(seal=True)

    def test_paths_outside_horizon_or_wrong_endpoints_are_rejected(self):
        for path in ([[295, 0], [301, 0]], [[301, 0], [300, 0]], [[300, True], [301, 0]], [[300, 0], [301, 9]]):
            self.setUp()
            self.ranking()["best_path_per_endpoint"][0]["path"] = path
            self.ranking()["competing_endpoints"][0]["path"] = deepcopy(path)
            self.ranking()["winner"] = deepcopy(self.ranking()["competing_endpoints"][0])
            with self.assertRaises(ValueError):
                self.build(seal=True)

    def test_path_totals_and_scores_must_reconcile(self):
        self.ranking()["best_path_per_endpoint"][0]["confidence_sum"] = 1.5
        with self.assertRaisesRegex(ValueError, "reconcile"):
            self.build(seal=True)
        self.setUp()
        self.ranking()["best_path_per_endpoint"][0]["internal_skipped_frames"] = 1
        with self.assertRaisesRegex(ValueError, "gap count"):
            self.build(seal=True)

    def test_frame300_rejects_any_historical_contribution(self):
        self.change_score(300, 0, total=.9)
        with self.assertRaisesRegex(ValueError, "Singleton"):
            self.build(seal=True)

    def test_human_judgments_and_index_uncertainty_cannot_change(self):
        for key, value in (("emitted_candidate_index", 0), ("status", "pending"), ("candidate_identity", "unknown")):
            self.setUp()
            self.ledger["rows"][1][key] = value
            with self.assertRaises(ValueError):
                self.build()

    def test_source_map_covers_copies_and_derived_operands(self):
        result = self.build()
        mapping = result["source_map"]
        self.assertEqual(mapping["copies"]["/rows/0/winner/best_path"], ["tt_observations_wrapper", "/observations/frames/0/ranking/best_path_per_endpoint/0"])
        self.assertEqual(mapping["copies"]["/rows/0/comparison_report"], ["representative_pool", "/evaluation_reports/641/frame_results/0"])
        self.assertEqual(mapping["derived"]["/rows/0/contributions/winner/motion"]["operation"], "negative_product")
        self.assertIn("descendant leaf", mapping["copy_rule"])

    def test_forged_transport_arithmetic_provenance_or_human_row_fails(self):
        for mutate in (lambda r: r["rows"][0].update(pair_score_gap=10),
                       lambda r: r["source_map"]["copies"].update({"/rows/0/human_review": ["human_ledger", "/rows/1"]}),
                       lambda r: r["rows"][1]["human_review"].update(emitted_candidate_index=0),
                       lambda r: r["rows"][1]["source_locations"]["winner"].update(competing_endpoint=1)):
            result = self.build()
            mutate(result)
            with self.assertRaises(ValueError):
                summary.validate_returned_contrast(result, self.scope, self.ledger)

    def test_all_rows_in_summary_and_both_byte_bounds(self):
        result = self.build()
        rendered = summary.format_summary(result)
        for frame in summary.FRAMES:
            self.assertIn(f"## Frame {frame}\n", rendered)
        self.assertIn("Separate saved global margin", rendered)
        self.assertIn("visual identity remains unknown", rendered)
        self.assertLessEqual(len(summary._bytes(result)), summary.MAX_JSON_BYTES)
        self.assertLessEqual(len(rendered.encode("utf-8")), summary.MAX_TEXT_BYTES)
        with mock.patch.object(summary, "MAX_JSON_BYTES", 100):
            with self.assertRaises(ValueError):
                summary.validate_returned_contrast(result, self.scope, self.ledger)
        with mock.patch.object(summary, "MAX_TEXT_BYTES", 100):
            with self.assertRaises(ValueError):
                summary.format_summary(result)

    def test_no_file_access_or_pointer_following(self):
        with mock.patch("builtins.open", side_effect=AssertionError("No I/O")), mock.patch.object(Path, "open", side_effect=AssertionError("No I/O")):
            result = self.build()
            summary.format_summary(result)

    def test_json_preserves_full_precision(self):
        self.change_score(300, 1, confidence=.6000000000000001, total=.6000000000000001)
        result = self.build(seal=True)
        encoded = summary._bytes(result)
        self.assertEqual(json.loads(encoded)["rows"][0]["comparison"]["competing_endpoint"]["endpoint_confidence"], .6000000000000001)


if __name__ == "__main__":
    unittest.main()
