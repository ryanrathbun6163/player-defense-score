"""Synthetic checks for independent motion gates/costs and immutable controls."""
import copy
import math
import random
import shutil
import tempfile
import unittest
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np

from src.ball_tracking import crop_motion_experiment as experiment
from src.ball_tracking import crop_motion_evaluation as evaluation
from src.ball_tracking import crop_motion_review as review
from src.ball_tracking import crop_ranking as legacy
from src.ball_tracking import crop_ranking_experiment as legacy_experiment
from src.ball_tracking import crop_ranking_evaluation as legacy_evaluation
from src.ball_tracking.crop_motion_factorial import (
    ARMS, RankingConfig, experiment_grid, legacy_config, rank_candidates,
    rank_history, validate_observations, verify_control_trace,
)
from src.ball_tracking.development_experiments import canonical_sha256, read_json, sha256_file
from src.ball_tracking.temporal_experiment import file_binding, spec_digest
from test_ball_annotation_foundation import not_visible_frame, observed_frame, parse_reviewed_annotations
from test_ball_crop_ranking import ROOT, ranking_setup, run_fixture
from test_ball_detection_visual_review import write_json
from test_ball_temporal_association import fixture

COMMIT = "e" * 40
PRIOR_COMMIT = "3c4894656fd5da11708a54089444d41f0a6f7773"


def config(arm="history_edge_tight_cost_tight", threshold=.2):
    return next(c for c in experiment_grid() if c.arm == arm and c.confidence_threshold == threshold)


def exhaustive(frames, c, diagonal):
    """Enumerate all paths, rather than using endpoint dynamic programming."""
    paths = []
    for frame in frames:
        candidates = [d for d in frame.detections if d.confidence >= c.confidence_threshold][:20]
        for candidate in candidates:
            ref = (frame.frame_index, candidate.candidate_index)
            added = [(candidate.confidence, (ref,), candidate)]
            for score, path, prior in paths:
                elapsed = ref[0] - path[-1][0]
                distance = math.dist(prior.center_xy_px, candidate.center_xy_px)
                if 1 <= elapsed <= 3 and distance <= c.edge_step * diagonal * elapsed:
                    cost = distance / (c.cost_step * diagonal * elapsed)
                    added.append((score + candidate.confidence - .25 * (elapsed - 1) - .25 * cost ** 2,
                                  (*path, ref), candidate))
            paths.extend(added)
    best = {}
    for score, path, candidate in paths:
        ref = path[-1]
        if ref not in best or (-score, path) < (-best[ref][0], best[ref][1]):
            best[ref] = (score, path, candidate)
    now = frames[-1].frame_index
    endpoints = [(0.0, None, (), None)]
    for ref, (score, path, candidate) in best.items():
        if now - ref[0] <= 2:
            endpoints.append((score - .25 * (now - ref[0]), ref, path, candidate.confidence))
    endpoints.sort(key=lambda x: (-x[0], 0 if x[1] is None else 1,
                                 -x[1][0] if x[1] else 0, -x[3] if x[1] else 0,
                                 x[1][1] if x[1] else 0, x[2]))
    return best, endpoints[0]


def execution_patches(stack, module=experiment, commit=COMMIT):
    stack.enter_context(patch.object(module, "clean_commit", return_value=commit))
    stack.enter_context(patch.object(module, "git", return_value=commit))
    stack.enter_context(patch.object(module, "_tracked"))
    original_run = module.subprocess.run
    def git_ignore_only(args, *positional, **kwargs):
        if isinstance(args, (list, tuple)) and list(args[:2]) == ["git", "check-ignore"]:
            return type("Result", (), {"returncode": 0})()
        return original_run(args, *positional, **kwargs)
    stack.enter_context(patch.object(module.subprocess, "run", side_effect=git_ignore_only))


def bind_manifest(root, proposal):
    target = root / "configs/ball_tracking/proposals/synthetic_motion.json"
    write_json(target, proposal)
    manifest = {"schema_version": "ball_crop_motion_experiment/v0.1",
                "experiment_id": experiment.EXPERIMENT_ID, "proposal": file_binding(root, target),
                "output_root": experiment.OUTPUT_ROOT, "authorization": None,
                "selected_operating_point": None, "quality_gate": None}
    approval = {"schema_version": "ball_crop_motion_approval/v0.1",
                "experiment_spec_sha256": spec_digest(manifest), "proposal": manifest["proposal"],
                "approved_by": "ryan", "statement": "Synthetic approval only",
                "recorded_at_utc": "2026-10-01T00:00:00Z", "timestamp_semantics": "Synthetic test fixture",
                "scope": "saved_six_development_crop_windows_all_63_declared_variants",
                "git_mutations_authorized": False}
    auth_path = root / "configs/ball_tracking/reviews/synthetic_motion_approval.json"
    write_json(auth_path, approval)
    manifest["authorization"] = file_binding(root, auth_path)
    path = root / "configs/ball_tracking/crop_motion_experiments/synthetic.json"
    write_json(path, manifest)
    return path, manifest


def motion_setup(root):
    """Build every input in a temporary repository; never read user footage."""
    prior_path, prior_manifest, prior = ranking_setup(root)
    with ExitStack() as stack:
        execution_patches(stack, legacy_experiment, PRIOR_COMMIT)
        legacy_experiment.run_experiment(root, prior_path)
        scored = legacy_evaluation.score_experiment(root, prior_path)
    proposal = read_json(ROOT / "configs/ball_tracking/proposals/rfdetr_medium_crop_motion_factorial_v0_1.json")
    proposal["prior_ranking_proposal"] = prior_manifest["proposal"]
    proposal["prior_ranking_manifest"] = file_binding(root, prior_path)
    for key in ("windows", "scoring_labels", "crop_experiment_manifest", "crop_review_receipt", "frozen_detector_contract_source"):
        proposal[key] = prior[key]
    proposal["saved_ranking_scoring_reports"] = scored["reports"]
    proposal["saved_ranking_control_outputs"] = [
        file_binding(root, legacy_experiment.output_path(root, window, c))
        for window in prior["windows"] for c in legacy.experiment_grid()]
    for key in ("design", "rationale", "diagnostic", "generator"):
        target = root / proposal[key]["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("Synthetic motion fixture only.\n", encoding="utf-8")
        proposal[key] = file_binding(root, target)
    target = root / proposal["prior_ranking_execution"]["path"]
    write_json(target, {"commit": PRIOR_COMMIT, "manifest": proposal["prior_ranking_manifest"],
                        "spec_sha256": spec_digest(prior_manifest),
                        "derived_outputs": proposal["saved_ranking_control_outputs"],
                        "scoring": {"reports": proposal["saved_ranking_scoring_reports"]}})
    proposal["prior_ranking_execution"] = file_binding(root, target)
    receipt = {"schema_version": "ball_crop_ranking_visual_review_record/v0.1",
               "human_visual_review": {"status": "completed", "reviewer_id": "ryan"},
               "bound_evidence": {"execution_commit": PRIOR_COMMIT,
                                  "experiment_manifest": proposal["prior_ranking_manifest"],
                                  "experiment_approval": prior_manifest["authorization"],
                                  "execution_record": proposal["prior_ranking_execution"],
                                  "scoring_reports": proposal["saved_ranking_scoring_reports"]}}
    target = root / proposal["ranking_review_receipt"]["path"]
    write_json(target, receipt)
    proposal["ranking_review_receipt"] = file_binding(root, target)
    path, manifest = bind_manifest(root, proposal)
    return path, manifest, proposal


class FactorialRankingTests(unittest.TestCase):
    def test_grid_and_fixed_independent_parameter_contract(self):
        self.assertEqual(len(experiment_grid()), 63)
        self.assertEqual(len({c.variant_id for c in experiment_grid()}), 63)
        self.assertEqual([(c.edge_step, c.cost_step) for c in experiment_grid()[3:7]],
                         [(.01, .01), (.01, .03), (.03, .01), (.03, .03)])
        self.assertEqual(sum(legacy_config(c) is not None for c in experiment_grid()), 45)
        invalid = [("unknown", .2), ("crop_raw", True), ("crop_raw", .21),
                   ("crop_top_twenty", .2, 19), (ARMS[3], .2, 20, .03, .01),
                   (ARMS[4], .2, 20, .01, .01), (ARMS[5], .2, True, .03, .01),
                   ("crop_raw", .2, None, .01, .01)]
        for args in invalid:
            with self.subTest(args=args), self.assertRaises(ValueError):
                RankingConfig(*args)

    def test_all_four_dynamic_programs_match_independent_exhaustive_paths(self):
        rng = random.Random(94217)
        for arm in ARMS[3:]:
            for _ in range(24):
                points = [[(100 + rng.randrange(65), 100 + rng.randrange(65), rng.choice([.15, .2, .5, .8]))
                           for _ in range(rng.randrange(4))] for _ in range(5)]
                _, run = run_fixture(points)
                diagonal = math.hypot(run.source_video.width_px, run.source_video.height_px)
                expected, winner = exhaustive(run.frames, config(arm), diagonal)
                actual = rank_history(run.frames, config(arm), diagonal)
                chosen = actual["winner"]
                self.assertEqual((chosen["score"], tuple(chosen["endpoint"]) if chosen["endpoint"] else None,
                                  tuple(map(tuple, chosen["path"]))), winner[:3])
                self.assertEqual(len(actual["best_path_per_endpoint"]), len(expected))
                for node in actual["best_path_per_endpoint"]:
                    score, path, _ = expected[tuple(node["endpoint"])]
                    self.assertEqual((node["score"], tuple(map(tuple, node["path"]))), (score, path))

    def test_inclusive_gate_and_independent_unclipped_cost(self):
        _, run = run_fixture([[(100, 100, .9)], [(130, 100, .8)]])
        results = {a: rank_history(run.frames, config(a), 1000.0) for a in ARMS[3:]}
        self.assertFalse(results[ARMS[3]]["eligible_edges"])
        self.assertFalse(results[ARMS[4]]["eligible_edges"])
        tight_cost = results[ARMS[5]]["eligible_edges"][0]
        wide_cost = results[ARMS[6]]["eligible_edges"][0]
        self.assertEqual((tight_cost["normalized_step"], tight_cost["motion_penalty"]), (3.0, 2.25))
        self.assertEqual((wide_cost["normalized_step"], wide_cost["motion_penalty"]), (1.0, .25))
        _, just_outside = run_fixture([[(100, 100, .9)], [(130.000001, 100, .8)]])
        self.assertFalse(rank_history(just_outside.frames, config(ARMS[6]), 1000.0)["eligible_edges"])
        _, short = run_fixture([[(100, 100, .9)], [(110, 100, .8)]])
        a = rank_history(short.frames, config(ARMS[3]), 1000.0)["eligible_edges"][0]
        b = rank_history(short.frames, config(ARMS[4]), 1000.0)["eligible_edges"][0]
        self.assertEqual((a["from"], a["to"]), (b["from"], b["to"]))
        self.assertAlmostEqual(a["motion_penalty"], 9 * b["motion_penalty"])

    def test_all_45_controls_preserve_entire_legacy_frames(self):
        _, run = run_fixture([[(100, 100, .8), (100, 100, .8)], [(130, 100, .8)], [],
                              [(140, 100, .35), (400, 400, .5)], [], [], [(170, 100, .5)]])
        for c in experiment_grid():
            old_config = legacy_config(c)
            if old_config is not None:
                old = legacy.rank_candidates(run, old_config, PRIOR_COMMIT)
                new = rank_candidates(run, c, COMMIT)
                self.assertEqual(new["frames"], old["frames"])
                verify_control_trace(new, old)
                self.assertEqual(validate_observations(new, run), c)

    def test_trace_parity_rejects_behavior_and_identity_changes(self):
        _, run = run_fixture([[(100, 100, .8)], [(101, 100, .8)]])
        c = config()
        new = rank_candidates(run, c, COMMIT)
        old = legacy.rank_candidates(run, legacy_config(c), PRIOR_COMMIT)
        mutations = []
        v = copy.deepcopy(new); v["frames"][1]["ranking"]["eligible_edges"][0]["motion_penalty"] += .01; mutations.append(v)
        v = copy.deepcopy(new); v["frames"][1]["ranking"]["score_margin"] += .01; mutations.append(v)
        v = copy.deepcopy(new); v["frames"][1]["candidate_decisions"][0]["disposition"] = "eligible_not_emitted"; mutations.append(v)
        v = copy.deepcopy(new); v["input_candidate_content_sha256"] = "0" * 64; mutations.append(v)
        v = copy.deepcopy(new); v["selected_operating_point"] = {"confidence": .2}; mutations.append(v)
        for value in mutations:
            with self.subTest(value=value), self.assertRaises(ValueError):
                verify_control_trace(value, old)
        with self.assertRaises(ValueError):
            verify_control_trace(rank_candidates(run, config(ARMS[4]), COMMIT), old)

    def test_exact_path_endpoint_and_empty_ties(self):
        # A skipped-frame penalty cancels the first .25 confidence exactly.
        _, run = run_fixture([[(100, 100, .25)], [], [(100, 100, .5)]])
        path = rank_history(run.frames, config(), 1000.0)["winner"]["path"]
        self.assertEqual(path, [[0, 0], [2, 0]])
        _, run = run_fixture([[(100, 100, .75)], [(500, 400, .5)]])
        self.assertEqual(rank_history(run.frames, config(), 1000.0)["winner"]["endpoint"], [1, 0])
        _, run = run_fixture([[(100, 100, .25)], [(300, 100, .75), (100, 100, .5)]])
        self.assertEqual(rank_history(run.frames, config(), 1000.0)["winner"]["endpoint"], [1, 0])
        _, run = run_fixture([[(100, 100, .8), (100, 100, .8)]])
        self.assertEqual(rank_history(run.frames, config(), 1000.0)["winner"]["endpoint"], [0, 0])
        _, run = run_fixture([[(100, 100, .25)], []])
        result = rank_history(run.frames, config(), 1000.0)
        self.assertEqual([e["score"] for e in result["competing_endpoints"]], [0.0, 0.0])
        self.assertIsNone(result["winner"]["endpoint"])

    def test_gaps_expire_without_invented_observations(self):
        _, run = run_fixture([[(100, 100, .9)], [], [], [(105, 100, .8)], [], [], []])
        for arm in ARMS[3:]:
            value = rank_candidates(run, config(arm), COMMIT)
            self.assertEqual([f["emitted_candidate_indices"] for f in value["frames"]], [[0], [], [], [0], [], [], []])
            self.assertTrue(any(e["elapsed_frames"] == 3 for e in value["frames"][3]["ranking"]["eligible_edges"]))
            self.assertIsNone(value["frames"][-1]["ranking"]["winner"]["endpoint"])

    def test_threshold_cap_duplicates_and_order_remain_explicit(self):
        _, run = run_fixture([[(100, 100, .2), (100, 100, .2), (200, 200, .15)]])
        raw = rank_candidates(run, config("crop_raw"), COMMIT)["frames"][0]
        self.assertEqual(raw["emitted_candidate_indices"], [0, 1])
        self.assertEqual(raw["candidate_decisions"][2]["disposition"], "below_threshold")
        _, crowded = run_fixture([[(100 + i, 100, .9 - i * .001) for i in range(21)]])
        for arm in ARMS[2:]:
            frame = rank_candidates(crowded, config(arm), COMMIT)["frames"][0]
            self.assertEqual(frame["candidate_decisions"][20]["disposition"], "outside_top_twenty")
            self.assertNotIn(20, frame["emitted_candidate_indices"])

    def test_future_isolation_window_reset_and_five_frame_horizon(self):
        points = [[(100 + 15 * i, 100, .8)] for i in range(8)]
        _, run = run_fixture(points)
        _, prefix = run_fixture(points[:4])
        _, reset = run_fixture([[(700, 400, .5)]])
        for arm in ARMS[3:]:
            before = rank_candidates(reset, config(arm), COMMIT)
            full = rank_candidates(run, config(arm), COMMIT)
            self.assertEqual(full["frames"][:4], rank_candidates(prefix, config(arm), COMMIT)["frames"])
            self.assertEqual(before, rank_candidates(reset, config(arm), COMMIT))
            self.assertEqual(full["frames"][-1]["horizon_start"], 3)
            self.assertTrue(all(e["from"][0] >= 3 for e in full["frames"][-1]["ranking"]["eligible_edges"]))

    def test_no_file_access_no_input_mutation_and_rederivation_guard(self):
        _, run = run_fixture([[(100, 100, .8)], [(101, 100, .8)]])
        before = canonical_sha256(run.to_dict())
        with patch.object(Path, "open", side_effect=AssertionError("Selector opened external input")):
            value = rank_candidates(run, config(ARMS[4]), COMMIT)
        self.assertEqual(canonical_sha256(run.to_dict()), before)
        validate_observations(value, run)
        value["frames"][1]["ranking"]["winner"]["score"] += .01
        with self.assertRaises(ValueError):
            validate_observations(value, run)

    def test_bad_input_order_failure_and_history_shape_rejected(self):
        _, unsorted = fixture([[(100, 100, .2), (200, 200, .9)]])
        with self.assertRaises(ValueError):
            rank_candidates(unsorted, config(), COMMIT)
        _, run = run_fixture([[(100, 100, .8)], [(101, 100, .8)]])
        failed = replace(run, frames=(replace(run.frames[0], inference_status="inference_failed",
                                              failure_reason="synthetic", detections=None), run.frames[1]))
        with self.assertRaises(ValueError):
            rank_candidates(failed, config(), COMMIT)
        for frames in ((), (run.frames[1], run.frames[0]), (run.frames[0],) * 6):
            with self.assertRaises(ValueError):
                rank_history(frames, config(), 1000.0)

    def test_hidden_truth_only_scores_false_alarms_and_partitions_cap_loss(self):
        labels = parse_reviewed_annotations([observed_frame(0), not_visible_frame(1)])
        _, run = run_fixture([[(400 + i, 400, .9 - i * .001) for i in range(20)] + [(100, 100, .8)],
                              [(101, 100, .8)]], labels)
        reports = [evaluation.evaluate_observations(labels, run, rank_candidates(run, config(a), COMMIT), 10.0, COMMIT)
                   for a in ARMS]
        _, losses = evaluation.paired_differences(reports)
        self.assertEqual(len(losses), 4)
        for loss in losses:
            self.assertEqual(loss["cap_lost_frames"], [0])
            self.assertEqual(loss["raw_no_qualifying_candidate_frames"], [])
            self.assertEqual(loss["additional_ranking_lost_frames"], [])
        for report in reports:
            self.assertEqual(report["metrics"]["non_visible_false_alarm_count"], 1)


class FactorialEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.labels = parse_reviewed_annotations([observed_frame(0), observed_frame(1, center=(150, 100))])
        _, self.run = run_fixture([[(100, 100, .8)], [(400, 400, .8), (150, 100, .7)]], self.labels)
        self.reports = [evaluation.evaluate_observations(
            self.labels, self.run, rank_candidates(self.run, config(a), COMMIT), 10.0, COMMIT) for a in ARMS]

    def test_factorial_pairs_isolate_one_parameter_and_orient_deltas(self):
        pairs = evaluation.factorial_differences(self.reports)
        self.assertEqual(len(pairs), 4)
        self.assertEqual([(p["varying_parameter"], p["fixed_value"]) for p in pairs],
                         [("edge_step", .01), ("edge_step", .03), ("cost_step", .01), ("cost_step", .03)])
        self.assertEqual([p["newly_recovered_frames"] for p in pairs], [[], [1], [], [1]])
        self.assertEqual([p["newly_lost_frames"] for p in pairs], [[], [], [], []])
        self.assertEqual([p["true_positive_delta"] for p in pairs], [0, 1, 0, 1])
        self.assertEqual([p["false_positive_delta"] for p in pairs], [0, -1, 0, -1])
        self.assertEqual([p["false_negative_delta"] for p in pairs], [0, -1, 0, -1])

    def test_comparisons_reject_missing_duplicate_mixed_and_invalid_partition(self):
        for reports in (self.reports[:-1], self.reports + [self.reports[0]]):
            with self.assertRaises(ValueError):
                evaluation.factorial_differences(reports)
        with self.assertRaises(ValueError):
            evaluation.aggregate([self.reports[0], self.reports[0]])
        changed = copy.deepcopy(self.reports)
        changed[-1]["selection_purpose"] = "challenge_evaluation"
        with self.assertRaises(ValueError):
            evaluation.factorial_differences(changed)
        changed = copy.deepcopy(self.reports)
        changed[-1]["metrics"]["false_negative_count"] += 1
        with self.assertRaises(ValueError):
            evaluation.paired_differences(changed)

    def test_saved_report_and_aggregate_parity_include_all_metrics(self):
        c = config(ARMS[6])
        old = legacy_evaluation.evaluate_observations(
            self.labels, self.run, legacy.rank_candidates(self.run, legacy_config(c), PRIOR_COMMIT), 10.0, PRIOR_COMMIT)
        new = self.reports[-1]
        evaluation.verify_control_parity(new, old)
        for key, subkey in (("metrics", "input_detection_count"), ("metrics", "true_positive_count"),
                            ("temporal_metrics", "longest_consecutive_missed_eligible_run")):
            changed = copy.deepcopy(new)
            changed[key][subkey] += 1
            with self.subTest(key=key, subkey=subkey), self.assertRaises(ValueError):
                evaluation.verify_control_parity(changed, old)
        old_aggregate = legacy_evaluation.aggregate([old])
        new_aggregate = evaluation.aggregate([new])
        evaluation.verify_aggregate_control_parity(new_aggregate, old_aggregate)
        changed = copy.deepcopy(new_aggregate)
        changed["per_window"][0]["temporal_metrics"]["emitted_frame_count"] += 1
        with self.assertRaises(ValueError):
            evaluation.verify_aggregate_control_parity(changed, old_aggregate)


class FactorialContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.template.cleanup)
        motion_setup(Path(cls.template.name))

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        shutil.copytree(self.template.name, self.root, dirs_exist_ok=True)
        self.path = self.root / "configs/ball_tracking/crop_motion_experiments/synthetic.json"
        self.m = read_json(self.path)
        self.p = read_json(self.root / self.m["proposal"]["path"])

    def test_selection_loads_neither_labels_reports_nor_pixels(self):
        original = Path.open
        def guarded(path, *args, **kwargs):
            name = path.as_posix()
            if "/annotations/" in name or "/evaluation/" in name or name.endswith("diagnostic.json") or "/data/clips/" in name:
                raise AssertionError("Selector opened forbidden input " + name)
            return original(path, *args, **kwargs)
        with patch.object(Path, "open", guarded):
            loaded = experiment.load_manifest(self.root, self.path)
            self.assertEqual(len(experiment.load_inputs(self.root, loaded)), 6)

    def test_dirty_execution_stops_before_input_load(self):
        with patch.object(experiment, "clean_commit", side_effect=ValueError("dirty")), patch.object(experiment, "load_inputs") as inputs:
            with self.assertRaisesRegex(ValueError, "dirty"):
                experiment.run_experiment(self.root, self.path)
            inputs.assert_not_called()
        self.assertFalse((self.root / experiment.OUTPUT_ROOT).exists())

    def test_scope_tamper_rejected_even_with_rebound_approval(self):
        changes = []
        p = copy.deepcopy(self.p); p["windows"][0]["purpose"] = "test_holdout"; changes.append(p)
        p = copy.deepcopy(self.p); p["windows"][0]["start_frame_index"] += 1; changes.append(p)
        p = copy.deepcopy(self.p); p["ranking_contract"]["normalized_step_clipping_allowed"] = True; changes.append(p)
        p = copy.deepcopy(self.p); p["ranking_contract"]["history_frames"] = 6; changes.append(p)
        p = copy.deepcopy(self.p); p["selectors"][4]["cost_step"] = .02; changes.append(p)
        p = copy.deepcopy(self.p); p["confidence_thresholds"].pop(); changes.append(p)
        p = copy.deepcopy(self.p); p["selected_operating_point"] = {"confidence": .35}; changes.append(p)
        p = copy.deepcopy(self.p); p["saved_ranking_control_outputs"].pop(); changes.append(p)
        p = copy.deepcopy(self.p); p["force"] = True; changes.append(p)
        for proposal in changes:
            path, _ = bind_manifest(self.root, proposal)
            with self.subTest(proposal=proposal), self.assertRaises(ValueError):
                experiment.load_manifest(self.root, path)

    def test_each_original_prediction_embargo_remains_enforced(self):
        parent = read_json(self.root / "configs/ball_tracking/experiments/rfdetr_medium_image_only_baseline_v0_1.json")
        windows = [w for w in parent["windows"] if w["execution_status"] == "annotation_pending_prediction_embargo"]
        self.assertEqual(len(windows), 9)
        for window in windows:
            target = self.root / window["output_path"]
            write_json(target, {})
            try:
                with self.assertRaisesRegex(ValueError, "embargo"):
                    experiment.load_manifest(self.root, self.path)
            finally:
                target.unlink()

    def test_approval_crop_and_saved_control_tamper_rejected(self):
        approval = self.root / self.m["authorization"]["path"]
        original = approval.read_bytes()
        approval.write_bytes(original + b" ")
        with self.assertRaises(ValueError):
            experiment.load_manifest(self.root, self.path)
        approval.write_bytes(original)
        crop = self.root / self.p["windows"][0]["crop_candidates"]["path"]
        original = crop.read_bytes()
        crop.write_bytes(original + b" ")
        with self.assertRaises(ValueError):
            experiment.load_inputs(self.root, experiment.load_manifest(self.root, self.path))
        crop.write_bytes(original)
        control = self.root / self.p["saved_ranking_control_outputs"][0]["path"]
        control.write_bytes(control.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            experiment.load_saved_control(self.root, self.p, self.p["windows"][0], experiment_grid()[0])

    def test_dry_run_has_no_selection_or_outputs(self):
        with ExitStack() as stack:
            execution_patches(stack)
            rank = stack.enter_context(patch.object(experiment, "rank_candidates"))
            result = experiment.run_experiment(self.root, self.path, dry_run=True)
            rank.assert_not_called()
        self.assertEqual((result["source_frames"], result["variants"], result["new_model_calls"]), (150, 63, 0))
        self.assertFalse((self.root / experiment.OUTPUT_ROOT).exists())

    def test_rebound_saved_control_digest_cannot_mask_wrong_crop_identity(self):
        item = self.p["saved_ranking_control_outputs"][0]
        target = self.root / item["path"]
        value = read_json(target)
        value["crop_content_sha256"] = "0" * 64
        write_json(target, value)
        self.p["saved_ranking_control_outputs"][0] = file_binding(self.root, target)
        with self.assertRaisesRegex(ValueError, "provenance"):
            experiment.load_saved_control(self.root, self.p, self.p["windows"][0], experiment_grid()[0])

    def test_complete_partial_resume_all_control_parities_and_review(self):
        with ExitStack() as stack:
            execution_patches(stack)
            original = experiment.persist_once
            count = 0
            def interrupted(target, payload):
                nonlocal count
                count += 1
                if count == 8:
                    raise RuntimeError("synthetic interruption")
                return original(target, payload)
            with patch.object(experiment, "persist_once", side_effect=interrupted), self.assertRaisesRegex(RuntimeError, "interruption"):
                experiment.run_experiment(self.root, self.path)
            self.assertEqual(experiment.run_experiment(self.root, self.path)["created_outputs"], 371)
            before = {p: sha256_file(p) for p in (self.root / experiment.OUTPUT_ROOT).rglob("*.json")}
            self.assertEqual(len(before), 378)
            self.assertEqual(experiment.run_experiment(self.root, self.path)["created_outputs"], 0)
            self.assertEqual(before, {p: sha256_file(p) for p in before})
            scored = evaluation.score_experiment(self.root, self.path)
            self.assertEqual((scored["per_window_reports"], scored["aggregate_cells_per_pool"], scored["saved_control_parity_cells"],
                              scored["saved_control_trace_parities"]), (1890, 315, 1350, 270))
            self.assertEqual(scored["saved_control_aggregate_parities"], 450)
            for binding in scored["reports"]:
                pool = read_json(self.root / binding["path"])
                self.assertEqual(len(pool["evaluation_reports"]), 945)
                self.assertEqual(len(pool["aggregate_results"]), 315)
                self.assertEqual(len(pool["loss_decomposition"]), 540)
                self.assertEqual(len(pool["factorial_comparisons"]), 540)
                for item in pool["loss_decomposition"]:
                    matching = next(r for r in pool["evaluation_reports"] if r["possession_id"] == item["possession_id"]
                                    and r["config"] == item["config"] and r["localization_radius_px"] == item["radius_px"])
                    parts = [item[k] for k in ("raw_no_qualifying_candidate_frames", "cap_lost_frames", "additional_ranking_lost_frames")]
                    self.assertEqual(sum(map(len, parts)), matching["metrics"]["false_negative_count"])
                    self.assertEqual(len(set().union(*map(set, parts))), sum(map(len, parts)))
            self._check_review(stack)
            target = experiment.output_path(self.root, self.p["windows"][0], experiment_grid()[0])
            value = read_json(target)
            value["crop_content_sha256"] = "0" * 64
            write_json(target, value)
            with self.assertRaises(ValueError):
                experiment.run_experiment(self.root, self.path)

    def _check_review(self, stack):
        import cv2
        original_capture = cv2.VideoCapture
        source = np.zeros((1080, 1920, 3), dtype=np.uint8)
        cv2.putText(source, "SYNTHETIC MOTION FACTORIAL", (400, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, (90, 90, 90), 2)
        class Capture:
            def __init__(self): self.index = 0
            def isOpened(self): return True
            def set(self, prop, value): self.index = int(value); return True
            def get(self, prop): return self.index if prop == cv2.CAP_PROP_POS_FRAMES else 25.0
            def read(self): self.index += 1; return True, source.copy()
            def release(self): pass
        def capture(target):
            return Capture() if "/data/clips/" in str(target).replace("\\", "/") else original_capture(target)
        stack.enter_context(patch.object(review, "verify_source_video_contract"))
        stack.enter_context(patch.object(cv2, "VideoCapture", side_effect=capture))
        result = review.render_experiment(self.root, self.path)
        self.assertEqual(result["assets"], 3012)
        bundle = Path(result["bundle"])
        manifest = read_json(bundle / "manifest.json")
        videos = [a for a in manifest["assets"] if a["path"].endswith(".mp4")]
        self.assertEqual(len(videos), 12)
        for item in videos:
            video = original_capture(str(bundle / item["path"]))
            self.assertTrue(video.isOpened())
            self.assertAlmostEqual(video.get(cv2.CAP_PROP_FPS), 5.0)
            decoded = 0
            while video.read()[0]:
                decoded += 1
            video.release()
            self.assertEqual(decoded, 25)
        self.assertEqual(len(manifest["final_frames"]), 6)
        self.assertTrue(review.render_experiment(self.root, self.path)["reused"])
        previews = ROOT / "data/outputs/ball_tracking/crop_motion_implementation_validation"
        previews.mkdir(parents=True, exist_ok=True)
        first = bundle / self.p["windows"][0]["window_id"] / "confidence_0.2"
        for name in ("comparison", "closeups", "unmarked_source"):
            image = cv2.imread(str(first / name / "frame_000074.png"))
            self.assertIsNotNone(image)
            if name == "comparison":
                self.assertEqual(image.shape[:2], (1566, 2400))
            if name == "unmarked_source":
                self.assertTrue(np.array_equal(image, source))
            (previews / f"synthetic_{name}.png").write_bytes((first / name / "frame_000074.png").read_bytes())
        (bundle / manifest["assets"][0]["path"]).write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            review.validate_review_bundle(bundle, manifest["header"])


if __name__ == "__main__":
    unittest.main()
