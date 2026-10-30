"""Artificial scoring evidence only; no real selection, images or model calls."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import src.ball_tracking as ball_package
from src.ball_tracking import crop_retention_evaluation as scoring
from src.ball_tracking.development_experiments import canonical_sha256, sha256_file
from src.ball_tracking.evaluation import evaluate_detections
from test_ball_annotation_foundation import (
    detection, not_visible_frame, observed_frame, parse_detection_run,
    parse_reviewed_annotations, partial_frame,
)


OLD_COMMIT = "a" * 40
NEW_COMMIT = "b" * 40


def bind(root, relative, document):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return {"path": relative, "sha256": sha256_file(path)}


def config(arm, threshold, *, new=False):
    motion = arm in scoring.MOTION_ARMS
    result = {"arm": arm, "confidence_threshold": threshold,
              "candidate_cap": None if new or arm in ("crop_raw", "crop_top_one") else 20,
              "edge_step": .01 if motion and "edge_tight" in arm else .03 if motion else None,
              "cost_step": .01 if motion and "cost_tight" in arm else .03 if motion else None}
    if new:
        result["retention_policy"] = scoring.RETENTION_POLICY
    return result


def observations(run, c, *, new=False, selected_index=None):
    frames = []
    for frame in run.frames:
        qualified = [d.candidate_index for d in frame.detections if d.confidence >= c["confidence_threshold"]]
        retained = qualified if c["candidate_cap"] is None else qualified[:20]
        if selected_index is not None:
            emitted = [selected_index] if selected_index in retained else []
        elif c["arm"] == "crop_raw":
            emitted = qualified
        elif c["arm"] == "crop_top_twenty":
            emitted = retained
        else:
            emitted = retained[:1]
        winner = {"endpoint": [frame.frame_index, emitted[0]] if emitted else None,
                  "path": [[frame.frame_index, emitted[0]]] if emitted else [], "score": 2.0 if new else 1.0}
        frames.append({"frame_index": frame.frame_index, "emitted_candidate_indices": emitted,
                       "candidate_decisions": [{"candidate_index": d.candidate_index,
                           "disposition": "below_threshold" if d.candidate_index not in qualified else
                           "outside_top_twenty" if d.candidate_index not in retained else
                           "emitted" if d.candidate_index in emitted else "eligible_not_emitted"} for d in frame.detections],
                       "ranking": {"winner": winner, "score_margin": .1,
                                   "best_path_for_winner": {"path": winner["path"]}, "current_alternatives": []},
                       "decision_reason": "synthetic_saved_decision", "horizon_start": max(0, frame.frame_index-4),
                       "horizon_end": frame.frame_index, "trace_binding": {"path": "synthetic_trace.json", "sha256": "e" * 64}})
    return {"schema_version": "ball_crop_retention_observations/v0.1" if new else "synthetic_saved_observations/v0.1",
            "variant_id": c["arm"] + "_" + canonical_sha256(c)[:16], "config": c,
            "ranking_code_commit": NEW_COMMIT if new else OLD_COMMIT,
            "input_candidate_content_sha256": canonical_sha256(run.to_dict()), "frames": frames}


def make_run(count=3, purpose="representative_evaluation", possession="possession_001"):
    labels = parse_reviewed_annotations([observed_frame(i) if i < count-1 else not_visible_frame(i) for i in range(count)])
    labels = replace(labels, possession_id=possession, annotation_set_id="synthetic_" + possession + "_" + purpose,
                     window=replace(labels.window, selection_purpose=purpose))
    raw = parse_detection_run(labels, {i: [detection(300, 300, .9),
        *[detection(310+j, 300, .1) for j in range(24)], detection(100, 100, .02)] for i in range(count)})
    return labels, raw


def saved_report(labels, run, obs, radius):
    frames = tuple(replace(f, detections=tuple(d for d in f.detections if d.candidate_index in o["emitted_candidate_indices"]))
                   for f, o in zip(run.frames, obs["frames"]))
    result = evaluate_detections(labels, replace(run, frames=frames), confidence_threshold=obs["config"]["confidence_threshold"], localization_radius_px=radius)
    emitted = sum(bool(o["emitted_candidate_indices"]) for o in obs["frames"])
    return {"schema_version": "ball_crop_motion_evaluation/v0.1", "variant_id": obs["variant_id"],
            "config": obs["config"], "selection_purpose": labels.window.selection_purpose,
            "possession_id": run.possession_id, "source_video": run.source_video.to_dict(), "window": run.window.to_dict(),
            "input_model_provenance": run.model_provenance.to_dict(), "ranking_code_commit": OLD_COMMIT,
            "evaluator_code_commit": OLD_COMMIT, "observations_content_sha256": canonical_sha256(obs),
            "input_candidate_content_sha256": obs["input_candidate_content_sha256"],
            "annotation_content_sha256": result["annotation_content_sha256"], "localization_radius_px": radius,
            "matching_rule": "raw center distance; uncertainty diagnostic only",
            "metrics": {k: result[k] for k in scoring.METRICS}, "frame_results": result["frame_results"],
            "temporal_metrics": {"emitted_frame_count": emitted, "missing_frame_count": len(frames)-emitted,
                                 "frame_count": len(frames), "emitted_frame_coverage": emitted/len(frames)},
            "selected_operating_point": None, "quality_gate": None}


def full_fixture(root):
    """Six invented windows with exactly630 saved and120 planned new reports."""
    p = {"windows": [], "scoring_labels": [], "saved_control_outputs": [], "saved_report_references": [],
         "saved_aggregate_references": [], "new_selection_units": [], "higher_confidence_structural_equivalence": [],
         "pool_separation": ["representative_evaluation", "challenge_evaluation"], "proposed_output_root": "data/outputs/synthetic_retention"}
    ctx = {"proposal": p, "manifest": {"output_root": p["proposed_output_root"]}, "commit": NEW_COMMIT,
           "spec_sha256": "f" * 64, "inputs": {}}
    all_obs, new_obs = {}, {}
    for purpose in p["pool_separation"]:
        reports, references, aggregates = [], [], []
        for possession_number in range(1, 4):
            labels, run = make_run(25, purpose, "possession_{:03d}".format(possession_number))
            wid = run.possession_id + "_" + purpose
            label_binding = bind(root, "labels/" + wid + ".json", labels.to_dict())
            crop_binding = bind(root, "candidates/" + wid + ".json", run.to_dict())
            p["windows"].append({"window_id": wid, "purpose": purpose, "possession_id": run.possession_id,
                                 "annotation_set_id": labels.annotation_set_id, "crop_candidates": crop_binding})
            p["scoring_labels"].append({"window_id": wid, "annotation": label_binding})
            ctx["inputs"][wid] = (run, crop_binding["sha256"])
            for threshold in scoring.THRESHOLDS:
                for arm in scoring.CONTROL_ARMS:
                    obs = observations(run, config(arm, threshold))
                    file = bind(root, "saved/{}_{}.json".format(wid, obs["variant_id"]), {"observations": obs})
                    record = {"window_id": wid, "purpose": purpose, "config": obs["config"], "file": file,
                              "observations_content_sha256": canonical_sha256(obs), "original_selection_commit": OLD_COMMIT}
                    p["saved_control_outputs"].append(record)
                    all_obs[file["path"]] = obs
                    for radius in scoring.RADII:
                        report = saved_report(labels, run, obs, radius)
                        references.append({"source": {"json_pointer": "/evaluation_reports/{}".format(len(reports))},
                            "report_content_sha256": canonical_sha256(report), "window_id": wid, "purpose": purpose,
                            "config": obs["config"], "localization_radius_px": radius, "observations_file": file,
                            "observations_content_sha256": canonical_sha256(obs), "original_selection_commit": OLD_COMMIT,
                            "original_evaluation_commit": OLD_COMMIT})
                        reports.append(report)
            for arm in scoring.MOTION_ARMS:
                obs = observations(run, config(arm, .01, new=True), new=True, selected_index=25)
                unit = {"window_id": wid, "purpose": purpose, "comparison_unit_id": wid + "__" + arm,
                        "config": obs["config"]}
                p["new_selection_units"].append(unit)
                new_obs[unit["comparison_unit_id"]] = obs
        for threshold in scoring.THRESHOLDS:
            for arm in scoring.CONTROL_ARMS:
                for radius in scoring.RADII:
                    subset = [r for r in reports if r["config"]["arm"] == arm and r["config"]["confidence_threshold"] == threshold and r["localization_radius_px"] == radius]
                    first = subset[0]
                    metrics = {k: sum(r["metrics"][k] for r in subset) for k in scoring.COUNTS}
                    aggregates.append({"config": first["config"], "selection_purpose": purpose, "localization_radius_px": radius,
                                       "ranking_code_commit": OLD_COMMIT, "evaluator_code_commit": OLD_COMMIT,
                                       "metrics": metrics, "window_count": 3})
        pool_binding = bind(root, "saved_pools/" + purpose + ".json", {"evaluation_reports": reports, "aggregate_results": aggregates})
        for reference in references:
            reference["source"].update(pool_binding)
        p["saved_report_references"].extend(references)
        for offset, aggregate in enumerate(aggregates):
            p["saved_aggregate_references"].append({"source": {**pool_binding, "json_pointer": "/aggregate_results/{}".format(offset)},
                "aggregate_content_sha256": canonical_sha256(aggregate), "purpose": purpose, "config": aggregate["config"],
                "localization_radius_px": aggregate["localization_radius_px"], "original_selection_commit": OLD_COMMIT, "original_evaluation_commit": OLD_COMMIT})
    for window in p["windows"]:
        wid, purpose = window["window_id"], window["purpose"]
        for arm in scoring.MOTION_ARMS:
            for threshold in (.20, .35):
                p["higher_confidence_structural_equivalence"].append({"window_id": wid, "purpose": purpose, "arm": arm,
                    "confidence_threshold": threshold, "status": "structural_equivalence_not_executed",
                    "per_frame_count_proof": [{"frame_index": f.frame_index, "qualified_candidate_count": 1} for f in ctx["inputs"][wid][0].frames],
                    "original_reports": [r for r in p["saved_report_references"] if r["window_id"] == wid and r["config"]["arm"] == arm and r["config"]["confidence_threshold"] == threshold],
                    "original_aggregates": [r for r in p["saved_aggregate_references"] if r["purpose"] == purpose and r["config"]["arm"] == arm and r["config"]["confidence_threshold"] == threshold]})
    fake_experiment = SimpleNamespace(load_saved_control=lambda root, record, run=None: copy.deepcopy(all_obs[record["file"]["path"]]),
                                      load_new_observations=lambda root, context, unit: copy.deepcopy(new_obs[unit["comparison_unit_id"]]))
    return ctx, fake_experiment


class RetentionEvaluationTests(unittest.TestCase):
    def test_original_index_beyond_twenty_hidden_null_and_input_provenance(self):
        labels, run = make_run()
        obs = observations(run, config(scoring.MOTION_ARMS[0], .01, new=True), new=True, selected_index=25)
        report = scoring.evaluate_unit(labels, run, obs, 10, NEW_COMMIT)
        self.assertEqual(report["frame_results"][0]["matched_candidate_index"], 25)
        self.assertEqual(report["metrics"]["true_positive_count"], 2)
        self.assertEqual(report["metrics"]["non_visible_false_alarm_count"], 1)
        self.assertIsNone(report["frame_results"][-1]["matched_center_error_px"])
        self.assertEqual(report["input_model_provenance"], run.model_provenance.to_dict())
        self.assertFalse(report["semantic_identity_labels_created"])

    def test_uncertainty_never_enlarges_radius(self):
        labels = parse_reviewed_annotations([partial_frame(0, center=(100, 100), uncertainty=30)])
        run = parse_detection_run(labels, {0: [detection(113, 100, .02)]})
        obs = observations(run, config(scoring.MOTION_ARMS[0], .01, new=True), new=True)
        report = scoring.evaluate_unit(labels, run, obs, 10, NEW_COMMIT)
        self.assertEqual(report["metrics"]["true_positive_count"], 0)
        self.assertEqual(report["metrics"]["false_negative_count"], 1)

    def test_old_and_higher_confidence_aliases_cannot_be_evaluated(self):
        labels, run = make_run()
        for c in (config(scoring.MOTION_ARMS[0], .01), config(scoring.MOTION_ARMS[0], .2, new=True)):
            with self.subTest(config=c), patch.object(scoring, "evaluate_detections", side_effect=AssertionError("Old scoring was called")):
                with self.assertRaises(ValueError):
                    scoring.evaluate_unit(labels, run, observations(run, c), 10, NEW_COMMIT)

    def test_changed_or_unknown_original_emission_rejected(self):
        labels, run = make_run()
        obs = observations(run, config(scoring.MOTION_ARMS[0], .01, new=True), new=True)
        for scenario in ("candidate", "input", "frame"):
            changed = copy.deepcopy(obs)
            if scenario == "candidate": changed["frames"][0]["emitted_candidate_indices"] = [999]
            elif scenario == "input": changed["input_candidate_content_sha256"] = "0" * 64
            else: changed["frames"].reverse()
            with self.subTest(scenario=scenario), self.assertRaises(ValueError):
                scoring.evaluate_unit(labels, run, changed, 10, NEW_COMMIT)

    def test_cap_loss_and_confidence_loss_are_ordered_not_double_counted(self):
        labels, run = make_run()
        get = lambda arm, threshold: saved_report(labels, run, observations(run, config(arm, threshold)), 10)
        floor = get("crop_raw", .01)
        low = scoring.loss_partition(floor, floor, get("crop_top_twenty", .01), get(scoring.MOTION_ARMS[0], .01))
        high = scoring.loss_partition(floor, get("crop_raw", .2), get("crop_top_twenty", .2), get(scoring.MOTION_ARMS[0], .2))
        self.assertEqual(low["parts"]["C_candidate_cap_loss"], [0, 1])
        self.assertEqual(high["parts"]["F_confidence_filter_loss"], [0, 1])
        self.assertEqual(high["parts"]["C_candidate_cap_loss"], [])
        self.assertEqual(low["hidden_alarm_frames"], [2])
        self.assertEqual(low["total_missed_eligible_frames"], 2)

    def test_larger_graph_score_can_accompany_a_lost_match(self):
        labels, run = make_run()
        c = config(scoring.MOTION_ARMS[0], .01, new=True)
        good = observations(run, c, new=True, selected_index=25)
        bad = observations(run, c, new=True, selected_index=0)
        for frame in bad["frames"]:
            frame["ranking"]["winner"]["score"] = 3.0
        before = scoring.evaluate_unit(labels, run, good, 10, NEW_COMMIT)
        after = scoring.evaluate_unit(labels, run, bad, 10, NEW_COMMIT)
        changed = scoring.match_changes(before, after)
        self.assertEqual(changed["newly_lost_frames"], [0, 1])
        self.assertEqual(changed["correct_to_wrong_frames"], [0, 1])
        self.assertEqual(changed["true_positive_count_delta"], -2)

    def test_new_history_and_new_current_candidate_attributions_remain_distinct(self):
        _, run = make_run()
        before = observations(run, config(scoring.MOTION_ARMS[0], .01))
        after = observations(run, config(scoring.MOTION_ARMS[0], .01, new=True), new=True, selected_index=25)
        # At frame1 the output changes to retained#1 through newly admitted#25
        # at frame0. This is distinct from frame0's new current#25 output.
        after["frames"][1]["emitted_candidate_indices"] = [1]
        after["frames"][1]["ranking"]["winner"].update(endpoint=[1, 1], path=[[0, 25], [1, 1]])
        rows = scoring.observation_changes(before, after)
        self.assertTrue(rows[0]["changed_to_new_current_candidate"])
        self.assertFalse(rows[0]["changed_to_previously_retained_candidate_via_new_history"])
        self.assertFalse(rows[1]["changed_to_new_current_candidate"])
        self.assertTrue(rows[1]["changed_to_previously_retained_candidate_via_new_history"])
        self.assertFalse(rows[1]["score_improvement_is_accuracy_improvement"])


class SavedScoringAndIntegrationTests(unittest.TestCase):
    def test_saved_pool_reuse_never_calls_evaluator_and_preserves_original_commits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ctx, _ = full_fixture(root)
            with patch.object(scoring, "evaluate_detections", side_effect=AssertionError("Rescoring saved evidence")):
                pool = scoring.load_saved_pool(root, ctx["proposal"], "representative_evaluation")
            self.assertEqual(len(pool["evaluation_reports"]), 315)
            self.assertEqual(len(pool["aggregate_results"]), 105)
            self.assertTrue(all(r["ranking_code_commit"] == OLD_COMMIT and r["evaluator_code_commit"] == OLD_COMMIT for r in pool["evaluation_reports"]))

    def test_aggregate_aliases_are_forty_not_one_hundred_twenty_per_pool(self):
        with tempfile.TemporaryDirectory() as temporary:
            ctx, _ = full_fixture(Path(temporary))
            aliases = scoring.deduplicate_aggregate_aliases(ctx["proposal"]["higher_confidence_structural_equivalence"], "representative_evaluation")
            self.assertEqual(len(aliases), 40)
            self.assertTrue(all(len(a["referencing_windows"]) == 3 for a in aliases))
            self.assertTrue(all(a["config"]["candidate_cap"] == 20 and not a["new_selection_or_scoring_executed"] for a in aliases))

    def test_pointer_digest_and_original_commit_tampering_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ctx, _ = full_fixture(root)
            for field, value in (("report_content_sha256", "0" * 64), ("original_evaluation_commit", NEW_COMMIT)):
                changed = copy.deepcopy(ctx["proposal"])
                changed["saved_report_references"][0][field] = value
                with self.subTest(field=field), self.assertRaises(ValueError):
                    scoring.load_saved_pool(root, changed, "representative_evaluation")
            source = ctx["proposal"]["saved_report_references"][0]["source"]
            path = root / source["path"]
            path.write_bytes(path.read_bytes() + b" ")
            with self.assertRaises(ValueError):
                scoring.load_saved_pool(root, ctx["proposal"], "representative_evaluation")

    def test_six_windows_only_score120_new_reports_and_preserve_all_alias_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ctx, fake = full_fixture(root)
            target = root / ctx["manifest"]["output_root"] / "evaluation"
            with patch.dict(sys.modules, {"src.ball_tracking.crop_retention_experiment": fake}), \
                    patch.object(ball_package, "crop_retention_experiment", fake, create=True), \
                    patch.object(scoring, "evaluate_detections", wraps=evaluate_detections) as evaluate:
                payloads = [scoring.score_window(root, ctx, w["window_id"], target / "windows") for w in ctx["proposal"]["windows"]]
            self.assertEqual(evaluate.call_count, 120)
            self.assertTrue(all(len(p["evaluation_reports"]) == 125 for p in payloads))
            self.assertTrue(all(len(p["paired_cap_differences"]) == 60 and len(p["confidence_differences"]) == 80 and len(p["loss_decomposition"]) == 120 for p in payloads))
            with patch.dict(sys.modules, {"src.ball_tracking.crop_retention_experiment": fake}), \
                    patch.object(ball_package, "crop_retention_experiment", fake, create=True), \
                    patch.object(scoring, "evaluate_detections", side_effect=AssertionError("Resume rescored completed unit")):
                resumed = scoring.score_window(root, ctx, ctx["proposal"]["windows"][0]["window_id"], target / "windows")
            self.assertEqual(resumed, payloads[0])
            with patch.object(scoring, "evaluate_detections", side_effect=AssertionError("Finalize rescored evidence")):
                result = scoring.finalize(root, ctx, payloads, target)
                loaded = scoring.load_window_score(root, ctx, ctx["proposal"]["windows"][0]["window_id"])
            self.assertEqual(result["distinct_reports"], 750)
            self.assertEqual(result["equivalence_report_references"], 240)
            self.assertEqual(len(loaded["equivalence_report_references"]), 40)
            for path in result["pool_paths"]:
                pool = json.loads(Path(path).read_text(encoding="utf-8"))
                self.assertEqual(len(pool["aggregate_results"]), 125)
                self.assertEqual(len(pool["equivalence_aggregate_references"]), 40)
                self.assertEqual(len(pool["aggregate_cap_differences"]), 20)
                self.assertFalse(pool["independent_trials_claimed"])
                self.assertIsNone(pool["selected_operating_point"])


if __name__ == "__main__":
    unittest.main()
