"""Synthetic geometry, exhaustive paths, and frozen-input contracts only."""
import copy
import inspect
import math
import random
import unittest
from unittest.mock import patch

from src.ball_tracking import crop_motion_factorial as motion
from src.ball_tracking import crop_player_context as core
from src.ball_tracking.development_experiments import canonical_sha256
from test_ball_crop_ranking import run_fixture

COMMIT = "a" * 40


def config(arm=None, threshold=.2):
    return next(c for c in core.experiment_grid()
                if c.arm == (arm or core.ARMS[0]) and c.confidence_threshold == threshold)


def player_row(frame, box=(90., 90., 110., 110.), player="white_p1", track=0, fps=25.):
    x1, y1, x2, y2 = map(float, box)
    return {"frame_index": frame, "timestamp_sec": frame / fps, "track_id": track,
            "confidence": .8, "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "floor_x": (x1 + x2) / 2, "floor_y": y2, "team_label": "unknown",
            "segment_id": f"t{track}_s1", "baseline_player_id": f"unknown_p{track}",
            "player_id": player, "reconciled_team": "white", "identity_status": "active",
            "identity_review_reason": "", "duplicate_detection_count": 2,
            "source_track_ids": f"{track};{track + 100}", "source_segment_ids": f"t{track}_s1;t{track + 100}_s1"}


def refresh_window(window):
    """Refresh synthetic binding metadata after a deliberate fixture mutation."""
    lo, hi = window["start_frame_index"], window["end_frame_index"]
    rows = window["rows"]
    counts = {str(f): sum(r["frame_index"] == f for r in rows) for f in range(lo, hi + 1)}
    window.update({"per_frame_box_counts": counts, "box_rows": len(rows),
                   "frames_with_any_box": sum(n > 0 for n in counts.values()),
                   "frames_with_ten_boxes": sum(n == 10 for n in counts.values()),
                   "missing_box_slots_relative_to_ten": 10 * len(counts) - len(rows),
                   "rows_collapsing_duplicate_detections": sum(r["duplicate_detection_count"] > 1 for r in rows),
                   "raw_and_reconciled_team_disagreements": sum(r["team_label"] != r["reconciled_team"] for r in rows),
                   "selected_rows_sha256": canonical_sha256(rows),
                   "prior_feasibility_selected_rows_sha256": canonical_sha256(rows)})
    original = [{k: str(v) for k, v in r.items()} for r in rows]
    window["original_csv_records"] = original
    window["original_csv_records_sha256"] = canonical_sha256(original)
    return window


def context_window(run, context_by_frame=None):
    if context_by_frame is None:
        context_by_frame = {f.frame_index: [player_row(f.frame_index, fps=run.source_video.fps)] for f in run.frames}
    result = {"window_id": "synthetic_context", "possession_id": run.possession_id,
              "purpose": "representative_evaluation", "start_frame_index": run.window.start_frame_index,
              "end_frame_index": run.window.end_frame_index, "source_video": run.source_video.to_dict(),
              "source_video_binding_status": "Synthetic context only; no real media.",
              "player_tracks": {"path": "data/synthetic_players.csv", "sha256": "b" * 64},
              "columns": list(core.COLUMNS),
              "rows": [copy.deepcopy(r) for f in run.frames for r in context_by_frame[f.frame_index]]}
    return refresh_window(result)


def independent_cost(candidate, rows, coefficient):
    """Independent geometry via projection onto a rectangle, not core helpers."""
    x, y = candidate.center_xy_px
    ratios = []
    for r in rows:
        nearest_x = min(max(x, r["x1"]), r["x2"])
        nearest_y = min(max(y, r["y1"]), r["y2"])
        ratios.append(math.hypot(x - nearest_x, y - nearest_y) / (r["y2"] - r["y1"]))
    if not ratios:
        return 0.
    z = min(ratios)
    return coefficient * (z / (1. + z))


def exhaustive(frames, c, diagonal, context, coefficient=.25):
    """Enumerate every path independently; do not use endpoint DP pruning."""
    paths = []
    for frame in frames:
        accepted = [d for d in frame.detections if d.confidence >= c.confidence_threshold][:20]
        for candidate in accepted:
            ref = (frame.frame_index, candidate.candidate_index)
            penalty = independent_cost(candidate, context[frame.frame_index], coefficient)
            utility = candidate.confidence if penalty == 0 else candidate.confidence - penalty
            added = [(utility, (ref,), candidate, candidate.confidence, penalty, 0, 0.)]
            for score, path, prior, confidence_sum, context_sum, gaps, motion_sum in paths:
                dt = ref[0] - path[-1][0]
                distance = math.dist(prior.center_xy_px, candidate.center_xy_px)
                if 1 <= dt <= 3 and distance <= c.edge_step * diagonal * dt:
                    normalized = distance / (c.cost_step * diagonal * dt)
                    new_score = ((score + utility) - .25 * (dt - 1)) - .25 * normalized ** 2
                    added.append((new_score, (*path, ref), candidate, confidence_sum + candidate.confidence,
                                  context_sum + penalty, gaps + dt - 1, motion_sum + normalized ** 2))
            paths.extend(added)
    best = {}
    for value in paths:
        ref = value[1][-1]
        if ref not in best or (-value[0], value[1]) < (-best[ref][0], best[ref][1]):
            best[ref] = value
    now = frames[-1].frame_index
    endpoints = [{"endpoint": None, "score": 0., "path": [], "endpoint_confidence": None,
                  "trailing_skipped_frames": None, "context_cost_sum": 0.}]
    for ref, (score, path, candidate, _, cost, _, _) in best.items():
        if now - ref[0] <= 2:
            endpoints.append({"endpoint": list(ref), "score": score - .25 * (now - ref[0]),
                              "path": [list(x) for x in path], "endpoint_confidence": candidate.confidence,
                              "trailing_skipped_frames": now - ref[0], "context_cost_sum": cost})
    endpoints.sort(key=lambda e: (-e["score"], 0 if e["endpoint"] is None else 1,
                                 -e["endpoint"][0] if e["endpoint"] else 0,
                                 -e["endpoint_confidence"] if e["endpoint"] else 0,
                                 e["endpoint"][1] if e["endpoint"] else 0, tuple(map(tuple, e["path"]))))
    return best, endpoints


class ContextGeometryTests(unittest.TestCase):
    def candidate(self, x=100., y=100., confidence=.8):
        return run_fixture([[(x, y, confidence)]])[1].frames[0].detections[0]

    def test_grid_is_only_the_four_fixed_proposal_arms(self):
        grid = core.experiment_grid()
        self.assertEqual(len(grid), 36)
        self.assertEqual(len({c.variant_id for c in grid}), 36)
        self.assertEqual([c.arm for c in grid[:4]], list(core.ARMS))
        self.assertEqual([(c.edge_step, c.cost_step) for c in grid[:4]], [(.01, .01), (.01, .03), (.03, .01), (.03, .03)])
        for c in grid:
            self.assertEqual(core.RankingConfig.from_mapping(c.to_dict()), c)
            self.assertEqual(core.paired_control_config(c).arm + "_player_context", c.arm)
        invalid = [dict(arm="unknown"), dict(confidence_threshold=True), dict(confidence_threshold=.21),
                   dict(candidate_cap=True), dict(candidate_cap=19), dict(edge_step=.03),
                   dict(cost_step=.02), dict(context_coefficient=0.), dict(context_coefficient=.1),
                   dict(context_coefficient=True), dict(context_coefficient=float("nan")),
                   dict(context_coefficient=.25+0j), dict(edge_step=.01+0j)]
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(ValueError):
                core.RankingConfig(**{**config().to_dict(), **change})

    def test_geometry_uses_minimum_normalized_distance_not_nearest_pixels(self):
        # First box is 10 px away / 10 high; second is 20 px away / 100 high.
        rows = [player_row(0, (110, 95, 120, 105), "near", 1),
                player_row(0, (120, 50, 130, 150), "tall", 2)]
        actual = core.candidate_context(self.candidate(), rows)
        self.assertEqual(actual["normalized_distance"], .2)
        self.assertAlmostEqual(actual["context_cost"], 1 / 24)
        self.assertEqual([m["player_id"] for m in actual["minimizing_boxes"]], ["tall"])
        self.assertEqual(actual["minimizing_boxes"][0]["source_row"], rows[1])

    def test_inside_boundary_crossing_and_corners(self):
        box = player_row(0, (-10, -20, 110, 120))
        for x, y in ((100, 100), (110, 100), (110, 120)):
            actual = core.candidate_context(self.candidate(x, y), [box])
            self.assertEqual((actual["normalized_distance"], actual["context_cost"]), (0., 0.))
            self.assertEqual(actual["node_utility"], .8)
        actual = core.candidate_context(self.candidate(113, 124), [box])
        self.assertEqual(actual["normalized_distance"], 5 / 140)

    def test_monotonic_bounded_geometry_and_all_minimizers_are_order_invariant(self):
        candidate = self.candidate()
        costs = [core.candidate_context(candidate, [player_row(0, (100 + d, 95, 110 + d, 105))])["context_cost"]
                 for d in (0, 1, 10, 100, 10000)]
        self.assertEqual(costs, sorted(costs))
        self.assertEqual(costs[2], .125)
        self.assertTrue(all(0 <= p < .25 for p in costs))
        rows = [player_row(0, (110, 95, 120, 105), "z", 2),
                player_row(0, (80, 95, 90, 105), "a", 5)]
        actual = core.candidate_context(candidate, rows)
        self.assertEqual(actual, core.candidate_context(candidate, list(reversed(rows))))
        self.assertEqual([v["player_id"] for v in actual["minimizing_boxes"]], ["a", "z"])

    def test_empty_is_explicit_neutral_context_and_zero_parity_is_not_an_arm(self):
        actual = core.candidate_context(self.candidate(), [])
        self.assertTrue(actual["context_unavailable"])
        self.assertIsNone(actual["normalized_distance"])
        self.assertEqual((actual["context_cost"], actual["node_utility"], actual["minimizing_boxes"]), (0., .8, []))
        self.assertEqual(core.candidate_context(self.candidate(), [player_row(0, (1000, 90, 1010, 110))], 0.)["node_utility"], .8)
        for value in (None, True, .1, -.25, float("inf"), .25+0j):
            with self.subTest(value=value), self.assertRaises(ValueError):
                core.candidate_context(self.candidate(), [], value)

    def test_malformed_boxes_do_not_turn_into_missing_context(self):
        for key, value in (("x1", True), ("x2", float("nan")), ("y1", float("inf")),
                           ("x2", 90.), ("y2", 90.), ("frame_index", True),
                           ("track_id", False), ("timestamp_sec", -1.), ("player_id", ""),
                           ("identity_status", "excluded"), ("floor_x", float("nan"))):
            row = player_row(0); row[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                core.candidate_context(self.candidate(), [row])
        for rows in (None, [player_row(0), player_row(0)],
                     [player_row(0), player_row(1, player="other")]):
            with self.assertRaises(ValueError):
                core.candidate_context(self.candidate(), rows)
        row = player_row(0); row["x1"] = -1e308; row["x2"] = 1e308
        with self.assertRaises(ValueError):
            core.candidate_context(self.candidate(), [row])
        row = player_row(0, (1000, 0, 1010, 1e-308))
        with self.assertRaises(ValueError):
            core.candidate_context(self.candidate(), [row])
        row = player_row(0); row["x1"] = 10**1000
        with self.assertRaises(ValueError):
            core.candidate_context(self.candidate(), [row])


class ContextInputTests(unittest.TestCase):
    def setUp(self):
        _, self.run = run_fixture([[(100, 100, .8)], [], [(101, 101, .7)]])
        self.window = context_window(self.run, {0: [player_row(0)], 1: [], 2: [player_row(2)]})

    def test_frozen_window_preserves_every_field_and_empty_frame(self):
        before = copy.deepcopy(self.window)
        rows = core.validate_context_window(self.window, self.run)
        self.assertEqual(list(rows), [0, 1, 2])
        self.assertEqual(rows[1], ())
        self.assertEqual(rows[0][0], self.window["rows"][0])
        self.assertEqual(set(rows[0][0]), set(core.COLUMNS))
        rows[0][0]["x1"] = 999
        self.assertEqual(self.window, before)

    def test_invalid_window_source_timestamps_keys_digests_and_duplicates(self):
        mutations = []
        for key, value in (("possession_id", "wrong"), ("start_frame_index", True),
                           ("end_frame_index", 3), ("box_rows", True),
                           ("selected_rows_sha256", "f" * 64), ("prior_feasibility_selected_rows_sha256", "f" * 64)):
            v = copy.deepcopy(self.window); v[key] = value; mutations.append(v)
        v = copy.deepcopy(self.window); v["source_video"]["sha256"] = "f" * 64; mutations.append(v)
        v = copy.deepcopy(self.window); del v["per_frame_box_counts"]["1"]; mutations.append(v)
        v = copy.deepcopy(self.window); v["per_frame_box_counts"]["3"] = 0; mutations.append(v)
        v = copy.deepcopy(self.window); v["per_frame_box_counts"]["0"] = True; mutations.append(v)
        v = copy.deepcopy(self.window); v["rows"][0]["timestamp_sec"] = .5; refresh_window(v); mutations.append(v)
        v = copy.deepcopy(self.window); v["rows"].append(player_row(3)); refresh_window(v); mutations.append(v)
        v = copy.deepcopy(self.window); v["rows"].insert(0, player_row(0)); refresh_window(v); mutations.append(v)
        v = copy.deepcopy(self.window); v["rows"].reverse(); refresh_window(v); mutations.append(v)
        v = copy.deepcopy(self.window); v["original_csv_records"][0]["source_track_ids"] = "tampered"; mutations.append(v)
        for v in mutations:
            with self.subTest(window=v), self.assertRaises(ValueError):
                core.validate_context_window(v, self.run)

    def test_annotation_fields_cannot_enter_context_or_selector(self):
        for target in ("window", "row", "raw", "config"):
            v = copy.deepcopy(self.window)
            c = config().to_dict()
            if target == "window": v["annotations"] = []
            elif target == "row": v["rows"][0]["visibility"] = "not_visible"
            elif target == "raw": v["original_csv_records"][0]["ball_truth"] = "100,100"
            else: c["annotation_path"] = "forbidden.json"
            with self.subTest(target=target), self.assertRaises(ValueError):
                core.rank_candidates(self.run, core.RankingConfig.from_mapping(c), COMMIT, v)
        with patch("builtins.open", side_effect=AssertionError("Selector must not open files")):
            core.rank_candidates(self.run, config(), COMMIT, self.window)
        self.assertEqual(tuple(inspect.signature(core.rank_candidates).parameters),
                         ("run", "config", "code_commit", "context_window"))

    def test_floor_coordinates_and_identity_provenance_do_not_affect_geometry(self):
        before = core.rank_candidates(self.run, config(), COMMIT, self.window)
        changed = copy.deepcopy(self.window)
        for r in changed["rows"]:
            r["floor_x"] = -9999.; r["floor_y"] = 9999.
            r["source_track_ids"] = "original;provenance;retained"
        refresh_window(changed)
        after = core.rank_candidates(self.run, config(), COMMIT, changed)
        self.assertNotEqual(before["input_context_content_sha256"], after["input_context_content_sha256"])
        for a, b in zip(before["frames"], after["frames"]):
            self.assertEqual(a["ranking"]["winner"], b["ranking"]["winner"])
            self.assertEqual(a["ranking"]["best_path_per_endpoint"], b["ranking"]["best_path_per_endpoint"])


class ContextRankingTests(unittest.TestCase):
    def test_all_four_settings_match_independent_exhaustive_oracle(self):
        rng = random.Random(48301)
        for arm in core.ARMS:
            for _ in range(24):
                points = [[(100 + rng.randrange(65), 100 + rng.randrange(65), rng.choice([.03, .1, .2, .5, .8]))
                           for _ in range(rng.randrange(4))] for _ in range(5)]
                _, run = run_fixture(points)
                context = {f.frame_index: ([] if rng.randrange(4) == 0 else [
                    player_row(f.frame_index, (90 + rng.randrange(80), 80, 200, 100 + rng.randrange(80)))]) for f in run.frames}
                c = config(arm, .03)
                diagonal = math.hypot(run.source_video.width_px, run.source_video.height_px)
                expected, endpoints = exhaustive(run.frames, c, diagonal, context)
                actual = core.rank_history(run.frames, c, diagonal, context)
                self.assertEqual(actual["competing_endpoints"], endpoints)
                self.assertEqual(actual["winner"], endpoints[0])
                self.assertEqual(len(actual["best_path_per_endpoint"]), len(expected))
                for node in actual["best_path_per_endpoint"]:
                    score, path, _, confidence, cost, gaps, motion_sum = expected[tuple(node["endpoint"])]
                    self.assertEqual((node["score"], tuple(map(tuple, node["path"])), node["confidence_sum"],
                                      node["context_cost_sum"], node["internal_skipped_frames"], node["normalized_step_squared_sum"]),
                                     (score, path, confidence, cost, gaps, motion_sum))

    def test_zero_strength_exactly_projects_entire_motion_traces(self):
        _, run = run_fixture([[(100, 100, .8), (100, 100, .8)], [(130, 100, .8)], [],
                              [(140, 100, .35), (400, 400, .5)], [], [], [(170, 100, .5)]])
        diagonal = math.hypot(run.source_video.width_px, run.source_video.height_px)
        for c in core.experiment_grid():
            for offset in range(len(run.frames)):
                frames = run.frames[max(0, offset-4):offset+1]
                ctx = {f.frame_index: [player_row(f.frame_index, (800, 600, 850, 650))] for f in frames}
                actual = core.rank_history(frames, c, diagonal, ctx, context_coefficient=0.)
                old = motion.rank_history(frames, core.paired_control_config(c), diagonal)
                self.assertEqual(core.project_zero_context_trace(actual), old)
        actual = core.rank_history(run.frames[:1], config(), diagonal, {0: [player_row(0, (800, 600, 850, 650))]})
        with self.assertRaises(ValueError): core.project_zero_context_trace(actual)

    def test_positive_cost_changes_path_and_negative_utility_abstains(self):
        _, run = run_fixture([[(100, 100, .6), (400, 400, .5)]])
        ctx = {0: [player_row(0, (390, 390, 410, 410))]}
        actual = core.rank_history(run.frames, config(), 1000., ctx)
        self.assertEqual(motion.rank_history(run.frames, core.paired_control_config(config()), 1000.)["winner"]["endpoint"], [0, 0])
        self.assertEqual(actual["winner"]["endpoint"], [0, 1])
        _, low = run_fixture([[(100, 100, .03)]])
        negative = core.rank_history(low.frames, config(threshold=.03), 1000., ctx)
        self.assertLess(negative["node_context"][0]["node_utility"], 0.)
        self.assertIsNone(negative["winner"]["endpoint"])
        self.assertEqual(negative["node_context"][0]["original_confidence"], .03)

    def test_context_charged_once_per_node_in_own_frame(self):
        _, run = run_fixture([[(100, 100, .6)]] * 3)
        ctx = {0: [player_row(0)], 1: [player_row(1, (110, 95, 120, 105))], 2: []}
        result = core.rank_candidates(run, config(), COMMIT, context_window(run, ctx))
        last = result["frames"][-1]
        self.assertTrue(last["context_unavailable"])
        self.assertEqual(last["context_available_box_count"], 0)
        self.assertEqual([n["context_cost"] for n in last["ranking"]["node_context"]], [0., .125, 0.])
        self.assertEqual(last["ranking"]["winner"]["context_cost_sum"], .125)
        self.assertEqual(last["ranking"]["winner"]["score"], ((.6 + (.6-.125)) + .6))
        self.assertEqual(last["ranking"]["winner"]["path"], [[0, 0], [1, 0], [2, 0]])

    def test_empty_score_tie_and_original_confidence_endpoint_tie(self):
        _, run = run_fixture([[(100, 100, .125)]])
        ctx = {0: [player_row(0, (110, 95, 120, 105))]}
        r = core.rank_history(run.frames, config(threshold=.1), 1000., ctx)
        self.assertEqual(r["node_context"][0]["node_utility"], 0.)
        self.assertIsNone(r["winner"]["endpoint"])
        _, run = run_fixture([[(100, 100, .5), (115, 100, .375)]])
        r = core.rank_history(run.frames, config(), 1000., ctx)
        self.assertEqual(r["competing_endpoints"][0]["score"], r["competing_endpoints"][1]["score"])
        self.assertEqual(r["winner"]["endpoint"], [0, 0])
        self.assertEqual(r["winner"]["endpoint_confidence"], .5)

    def test_path_ties_missing_cost_trailing_expiry_and_inclusive_motion_edges(self):
        _, run = run_fixture([[(100, 100, .25)], [], [(100, 100, .5)]])
        ctx = {f.frame_index: [] for f in run.frames}
        self.assertEqual(core.rank_history(run.frames, config(), 1000., ctx)["winner"]["path"], [[0, 0], [2, 0]])
        _, run = run_fixture([[(100, 100, .8)], [], [], []])
        result = core.rank_candidates(run, config(), COMMIT, context_window(run, {f.frame_index: [] for f in run.frames}))
        self.assertEqual([f["emitted_candidate_indices"] for f in result["frames"]], [[0], [], [], []])
        self.assertEqual(result["frames"][2]["ranking"]["winner"]["score"], .8-.5)
        self.assertIsNone(result["frames"][3]["ranking"]["winner"]["endpoint"])
        _, run = run_fixture([[(100, 100, .9)], [(130, 100, .8)]])
        ctx = {0: [], 1: []}
        tight = core.rank_history(run.frames, config(core.ARMS[0]), 1000., ctx)
        wide = core.rank_history(run.frames, config(core.ARMS[2]), 1000., ctx)
        self.assertFalse(tight["eligible_edges"])
        self.assertEqual(wide["eligible_edges"][0]["normalized_step"], 3.)
        self.assertEqual(wide["eligible_edges"][0]["motion_penalty"], 2.25)

    def test_confidence_filter_and_cap_precede_context_cost(self):
        points = [(100+i, 100, .2) for i in range(21)] + [(400, 400, .19)]
        _, run = run_fixture([points])
        w = context_window(run, {0: [player_row(0, (119.5, 95, 120.5, 105))]})
        value = core.rank_candidates(run, config(), COMMIT, w)
        f = value["frames"][0]
        self.assertEqual(len(f["ranking"]["node_context"]), 20)
        self.assertEqual(f["candidate_decisions"][20]["disposition"], "outside_top_twenty")
        self.assertEqual(f["candidate_decisions"][21]["disposition"], "below_threshold")
        self.assertTrue(all(n["original_confidence"] == .2 for n in f["ranking"]["node_context"]))

    def test_no_future_influence_and_window_reset(self):
        points = [[(100+i, 100, .6)] for i in range(7)]
        _, run = run_fixture(points)
        base = core.rank_candidates(run, config(), COMMIT, context_window(run))
        changed_points = points[:4] + [[(450, 300, .9)]] * 3
        _, future = run_fixture(changed_points)
        future_context = {f.frame_index: [player_row(f.frame_index, (500, 400, 600, 500))]
                          if f.frame_index >= 4 else [player_row(f.frame_index)] for f in future.frames}
        changed = core.rank_candidates(future, config(), COMMIT, context_window(future, future_context))
        self.assertEqual(base["frames"][:4], changed["frames"][:4])
        # A fresh independent window cannot inherit any prior path.
        _, single = run_fixture([[(106, 100, .6)]])
        reset = core.rank_candidates(single, config(), COMMIT, context_window(single))
        self.assertEqual(reset["frames"][0]["ranking"]["winner"]["path"], [[0, 0]])
        self.assertEqual(base["frames"][-1]["horizon_start"], 2)
        for bad_context in ({0: []}, {0: [], 1: [], 2: []}, {True: [], 0: []}):
            with self.assertRaises(ValueError):
                core.rank_history(run.frames[:2], config(), 1000., bad_context)

    def test_observation_validation_binds_inputs_audits_and_provenance(self):
        _, run = run_fixture([[(100, 100, .7)], [(101, 100, .6)]])
        w = context_window(run)
        before_run, before_context = copy.deepcopy(run.to_dict()), copy.deepcopy(w)
        actual = core.rank_candidates(run, config(), COMMIT, w)
        self.assertEqual(core.validate_observations(actual, run, w), config())
        self.assertEqual(run.to_dict(), before_run)
        self.assertEqual(w, before_context)
        changes = []
        for key in ("input_context_content_sha256", "window_rows_sha256", "input_candidate_content_sha256"):
            v = copy.deepcopy(actual); v[key] = "f" * 64; changes.append(v)
        v = copy.deepcopy(actual); v["frames"][0]["ranking"]["node_context"][0]["context_cost"] = .1; changes.append(v)
        v = copy.deepcopy(actual); v["frames"][0]["ranking"]["winner"]["context_cost_sum"] = .1; changes.append(v)
        v = copy.deepcopy(actual); v["frames"][0]["context_unavailable"] = True; changes.append(v)
        v = copy.deepcopy(actual); v["selected_operating_point"] = {"confidence": .2}; changes.append(v)
        for value in changes:
            with self.assertRaises(ValueError): core.validate_observations(value, run, w)


if __name__ == "__main__":
    unittest.main()
