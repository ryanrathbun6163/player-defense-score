"""Artificial-only tests for fixed-terminal mean-confidence dynamic programming."""
import copy
import math
import random
import unittest
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

from src.ball_tracking import crop_motion_factorial as saved
from src.ball_tracking import crop_path_confidence_mean as mean
from test_ball_annotation_foundation import (
    detection, observed_frame, parse_detection_run, parse_reviewed_annotations,
)


def fixture(points, start=0, sort=True):
    labels = parse_reviewed_annotations([observed_frame(start + i) for i in range(len(points))])
    ordered = [sorted(frame, key=lambda item: (-item[2], item[0], item[1])) if sort else frame
               for frame in points]
    return parse_detection_run(labels, {start + i: [detection(*point) for point in frame]
                                       for i, frame in enumerate(ordered)})


def exhaustive(frames, diagonal):
    """Independent enumeration for ordinary graphs with separated float choices.

    This is not used as an oracle for the declared rounding/pruning corner case.
    It enumerates paths first and then evaluates each using its final denominator.
    """
    paths, nodes = [], {}
    for frame in frames:
        for candidate in [c for c in frame.detections if c.confidence >= .01][:20]:
            ref = (frame.frame_index, candidate.candidate_index)
            new = [(ref,)]
            for path in paths:
                delta = ref[0] - path[-1][0]
                if (1 <= delta <= 3 and math.dist(nodes[path[-1]].center_xy_px, candidate.center_xy_px)
                        <= .01 * diagonal * delta):
                    new.append((*path, ref))
            nodes[ref] = candidate
            paths.extend(new)
    best = {}
    for path in paths:
        n = len(path)
        score = nodes[path[0]].confidence / n
        for prior, ref in zip(path, path[1:]):
            delta = ref[0] - prior[0]
            normalized = math.dist(nodes[prior].center_xy_px, nodes[ref].center_xy_px) / (.01 * diagonal * delta)
            score = ((score + nodes[ref].confidence / n) - .25 * (delta - 1)) - .25 * normalized ** 2
        ref = path[-1]
        if ref not in best or (-score, path) < (-best[ref][0], best[ref][1]):
            best[ref] = (score, path)
    current = frames[-1].frame_index
    endpoints = [(0.0, None, (), None)]
    for ref, (score, path) in best.items():
        if current - ref[0] <= 2:
            endpoints.append((score - .25 * (current - ref[0]), ref, path, nodes[ref].confidence))
    endpoints.sort(key=lambda item: (-item[0], 0 if item[1] is None else 1,
                                    -item[1][0] if item[1] else 0,
                                    -item[3] if item[1] else 0,
                                    item[1][1] if item[1] else 0, item[2]))
    return best, endpoints


def state(trace, n, endpoint, actual):
    return next(value for value in trace["surviving_states"]
                if (value["terminal_n"], value["endpoint"], value["actual_node_count"])
                == (n, endpoint, actual))


class MeanConfidenceSelectorTests(unittest.TestCase):
    def test_only_one_frozen_arm_configuration(self):
        config = mean.RankingConfig()
        self.assertEqual(config, mean.RankingConfig.from_mapping(asdict(config)))
        self.assertTrue(config.variant_id.startswith(mean.ARM + "_"))
        for override in ({"arm": "history_edge_tight_cost_tight"}, {"confidence_threshold": .2},
                         {"candidate_cap": 21}, {"candidate_cap": 20.0}, {"edge_step": .03},
                         {"cost_step": .03}, {"confidence_threshold": True}, {"edge_step": True}):
            with self.subTest(override=override), self.assertRaises(ValueError):
                mean.RankingConfig(**override)
        with self.assertRaises(ValueError):
            mean.RankingConfig.from_mapping({**asdict(config), "force": True})

    def test_terminal_denominator_preserves_previously_losing_prefix(self):
        # At frame 1, singleton B (.8) beats A-B (.79). At frame 2, A-B-C
        # beats B-C and the older B endpoint. Keeping only frame 1's winner
        # would therefore incorrectly miss the current observation.
        step = math.sqrt(.06 / .25) * 10.0
        run = fixture([[(100, 100, .9)], [(100 + step, 100, .8)], [(100 + step, 100, .2)]])
        trace = mean.rank_history(run.frames, 1000.0)
        prefix = next(p for p in trace["best_path_per_endpoint"] if p["endpoint"] == [1, 0])
        self.assertEqual(prefix["path"], [[1, 0]])
        self.assertGreater(prefix["score"], state(trace, 2, [1, 0], 2)["score"])
        winner = trace["winner"]
        self.assertEqual(winner["path"], [[0, 0], [1, 0], [2, 0]])
        self.assertEqual(winner["node_count"], 3)
        self.assertGreater(winner["score"], .55)
        self.assertEqual(state(trace, 3, [2, 0], 3)["predecessor"],
                         {"terminal_n": 3, "endpoint": [1, 0], "actual_node_count": 2})

    def test_ordinary_small_graphs_agree_with_independent_enumeration(self):
        rng = random.Random(560137)
        for case in range(32):
            # Continuous artificial confidences and positions avoid deliberate
            # equal-prefix/rounding-collapse ambiguity in this oracle check.
            points = [[(100 + rng.uniform(-10, 10), 100 + rng.uniform(-10, 10),
                        rng.uniform(.021, .979)) for _ in range(rng.randrange(1, 4))]
                      for _ in range(5)]
            run = fixture(points)
            expected, endpoints = exhaustive(run.frames, 1000.0)
            actual = mean.rank_history(run.frames, 1000.0)
            with self.subTest(case=case):
                for record in actual["best_path_per_endpoint"]:
                    self.assertEqual((record["score"], tuple(map(tuple, record["path"]))),
                                     expected[tuple(record["endpoint"])])
                winner = actual["winner"]
                self.assertEqual((winner["score"], tuple(winner["endpoint"]),
                                  tuple(map(tuple, winner["path"]))), endpoints[0][:3])
                self.assertEqual(actual["score_margin"], endpoints[0][0] - endpoints[1][0])

    def test_binary64_extension_order_is_not_replaced_by_interpretive_formula(self):
        run = fixture([[(100, 100, .1)], [(100, 100, .2)], [(100, 100, .3)]])
        trace = mean.rank_history(run.frames, 1000.0)
        complete = state(trace, 3, [2, 0], 3)
        score = .1 / 3
        score = ((score + .2 / 3) - 0.0) - 0.0
        score = ((score + .3 / 3) - 0.0) - 0.0
        self.assertEqual(complete["score"], score)
        self.assertNotEqual(complete["score"], complete["confidence_sum"] / 3)
        self.assertTrue(math.isclose(complete["score"], complete["confidence_sum"] / 3,
                                     rel_tol=1e-9, abs_tol=1e-9))
        # Exact float equality, never a reconciliation tolerance, decides states.
        higher = {"score": math.nextafter(.5, 1.0), "path": [[1, 1]]}
        earlier = {"score": .5, "path": [[0, 0]]}
        self.assertLess(mean._state_key(higher), mean._state_key(earlier))

    def test_declared_pruning_keeps_prefix_winner_after_rounding_collapse(self):
        # A later addition can erase a one-ulp prefix difference. The DP keeps
        # the already chosen higher prefix; it does not resurrect a pruned path
        # for a new lexicographic tie. This documents the deliberate limitation.
        offset = math.sqrt(math.ulp(.125) / .25) * 10.0
        confidence = .1875 + 3 * math.ulp(.1875)
        run = fixture([[(100 + offset, 100, confidence), (100, 100, confidence)],
                       [(100, 100, .1875)], [(100, 100, .75)]], sort=False)
        trace = mean.rank_history(run.frames, 1000.0)
        chosen_prefix = state(trace, 3, [1, 0], 2)
        self.assertEqual(chosen_prefix["path"], [[0, 1], [1, 0]])
        displaced_edge = next(edge for edge in trace["eligible_edges"]
                              if edge["from"] == [0, 0] and edge["to"] == [1, 0])
        lower_prefix = ((confidence / 3 + .1875 / 3)
                        - displaced_edge["skipped_frame_penalty"]) - displaced_edge["motion_penalty"]
        self.assertLess(lower_prefix, chosen_prefix["score"])
        self.assertEqual(lower_prefix + .75 / 3, chosen_prefix["score"] + .75 / 3)
        self.assertEqual(state(trace, 3, [2, 0], 3)["path"], [[0, 1], [1, 0], [2, 0]])

    def test_exact_state_path_and_global_tie_orders(self):
        run = fixture([[(100, 100, .5), (100, 100, .5)], [(100, 100, .5), (100, 100, .5)]])
        trace = mean.rank_history(run.frames, 1000.0)
        self.assertEqual(state(trace, 2, [1, 0], 2)["path"], [[0, 0], [1, 0]])
        self.assertEqual(trace["winner"]["path"], [[0, 0], [1, 0]])
        self.assertEqual(trace["winner"]["endpoint"], [1, 0])
        self.assertEqual(trace["score_margin"], 0.0)
        # Current .5 ties an older .75 endpoint after its .25 trailing cost.
        distant = fixture([[(100, 100, .75)], [(700, 400, .5)]])
        self.assertEqual(mean.rank_history(distant.frames, 1000.0)["winner"]["endpoint"], [1, 0])
        unequal = fixture([[(100, 100, 1.0)], [(700, 400, .75), (100, 100, .5)]])
        self.assertEqual(mean.rank_history(unequal.frames, 1000.0)["winner"]["endpoint"], [1, 0])
        zero = fixture([[(100, 100, .25)], []])
        self.assertIsNone(mean.rank_history(zero.frames, 1000.0)["winner"]["endpoint"])

    def test_inclusive_floor_cap_gate_and_preserved_candidates(self):
        run = fixture([[(100 + i, 100, .9 - .01 * i) for i in range(21)]])
        frame = next(mean.iter_ranked_frames(run))
        self.assertEqual(len(frame["ranking"]["retained_candidates"]), 20)
        self.assertEqual(frame["candidate_decisions"][20]["disposition"], "outside_top_twenty")
        self.assertEqual(frame["ranking"]["retained_candidates"][0],
                         {"reference": [0, 0], **run.frames[0].detections[0].to_dict()})
        floor = fixture([[(100, 100, .01), (110, 100, .009)]])
        frame = next(mean.iter_ranked_frames(floor))
        self.assertEqual(frame["emitted_candidate_indices"], [0])
        self.assertEqual(frame["candidate_decisions"][1]["disposition"], "below_threshold")
        boundary = fixture([[(100, 100, .9)], [(110, 100, .8)]])
        edge = mean.rank_history(boundary.frames, 1000.0)["eligible_edges"][0]
        self.assertEqual((edge["normalized_step"], edge["motion_penalty"]), (1.0, .25))
        outside = fixture([[(100, 100, .9)], [(110.000001, 100, .8)]])
        self.assertEqual(mean.rank_history(outside.frames, 1000.0)["eligible_edges"], [])

    def test_internal_and_trailing_gaps_preserve_missingness(self):
        run = fixture([[(100, 100, .8)], [], [], [(100, 100, .2)], []])
        trace = mean.rank_history(run.frames, 1000.0)
        edge = trace["eligible_edges"][0]
        self.assertEqual((edge["elapsed_frames"], edge["skipped_frame_penalty"]), (3, .5))
        frames = list(mean.iter_ranked_frames(run))
        self.assertEqual(frames[1]["emitted_candidate_indices"], [])
        self.assertEqual(frames[1]["decision_reason"], "earlier_endpoint_no_current_observation")
        self.assertEqual(frames[2]["ranking"]["winner"]["trailing_skipped_frames"], 2)
        self.assertIsNone(frames[4]["ranking"]["winner"]["endpoint"])
        too_far = fixture([[(100, 100, .8)], [], [], [], [(100, 100, .8)]])
        self.assertEqual(mean.rank_history(too_far.frames, 1000.0)["eligible_edges"], [])
        empty = fixture([[], []])
        last = list(mean.iter_ranked_frames(empty))[-1]
        self.assertEqual(last["decision_reason"], "empty_hypothesis")
        self.assertIsNone(last["ranking"]["score_margin"])
        self.assertEqual(last["ranking"]["winner"]["node_count"], 0)

    def test_every_window_start_matches_saved_tt_and_top_one(self):
        tt = saved.RankingConfig("history_edge_tight_cost_tight", .01, 20, .01, .01)
        for start in (50, 200, 250, 25, 300, 150):
            run = fixture([[(100, 100, .8), (100, 100, .8), (300, 300, .7)]], start=start)
            current = next(mean.iter_ranked_frames(run))
            prior = saved.rank_history(run.frames, tt, math.hypot(run.source_video.width_px,
                                                                run.source_video.height_px))
            self.assertEqual(current["emitted_candidate_indices"], [0])
            self.assertEqual(current["ranking"]["winner"]["endpoint"], prior["winner"]["endpoint"])
            self.assertEqual(current["ranking"]["winner"]["score"], prior["winner"]["score"])
            self.assertEqual(current["ranking"]["winner"]["node_count"], 1)

    def test_horizon_causality_reset_no_file_access_or_input_mutation(self):
        points = [[(100 + i, 100, .7)] for i in range(8)]
        full, prefix = fixture(points), fixture(points[:4])
        before = copy.deepcopy(full.to_dict())
        calls = []
        with patch.object(Path, "open", side_effect=AssertionError("external read")), \
                patch("builtins.open", side_effect=AssertionError("external read")):
            frames = list(mean.iter_ranked_frames(full, lambda: calls.append(True)))
            shorter = list(mean.iter_ranked_frames(prefix))
        self.assertEqual(full.to_dict(), before)
        self.assertEqual(frames[:4], shorter)
        self.assertTrue(calls)
        self.assertEqual(frames[-1]["horizon_start"], 3)
        self.assertTrue(all(record["reference"][0] >= 3
                            for record in frames[-1]["ranking"]["retained_candidates"]))
        reset = fixture([[(700, 400, .6)]], start=100)
        self.assertEqual(next(mean.iter_ranked_frames(reset))["ranking"]["winner"]["path"], [[100, 0]])
        compact = mean.summarize_frame(frames[-1])
        self.assertEqual(set(compact["ranking"]), {"winner", "score_margin"})
        compact["ranking"]["winner"]["path"].append([999, 0])
        self.assertNotEqual(compact["ranking"]["winner"]["path"], frames[-1]["ranking"]["winner"]["path"])

    def test_all_states_have_valid_chosen_predecessors_and_component_accounting(self):
        run = fixture([[(100, 100, .91), (102, 100, .83)], [(103, 100, .79)], [], [(106, 100, .67)]])
        trace = mean.rank_history(run.frames, 1000.0)
        states = {(s["terminal_n"], tuple(s["endpoint"]), s["actual_node_count"]): s
                  for s in trace["surviving_states"]}
        for value in states.values():
            self.assertEqual(value["node_count"], len(value["path"]))
            self.assertLessEqual(value["actual_node_count"], value["terminal_n"])
            parent = value["predecessor"]
            if parent is not None:
                prior = states[(parent["terminal_n"], tuple(parent["endpoint"]), parent["actual_node_count"])]
                self.assertEqual(prior["path"], value["path"][:-1])
            else:
                self.assertEqual(value["node_count"], 1)
        self.assertTrue(all(s["node_count"] == s["terminal_n"] for s in trace["completed_states"]))
        changed = copy.deepcopy(trace["winner"])
        changed["score"] += .1
        with self.assertRaisesRegex(ValueError, "reconciliation"):
            mean._reconcile(changed, completed=True)

    def test_invalid_frames_order_confidence_and_export_floor_are_rejected(self):
        run = fixture([[(100, 100, .8)], [(101, 100, .7)]])
        for frames in ((), (run.frames[1], run.frames[0]), (run.frames[0],) * 6,
                       (run.frames[0], replace(run.frames[1], frame_index=3))):
            with self.subTest(frames=frames), self.assertRaises(ValueError):
                mean.rank_history(frames, 1000.0)
        for diagonal in (0, -1, math.inf, math.nan, True):
            with self.assertRaises(ValueError):
                mean.rank_history(run.frames, diagonal)
        failed = replace(run, frames=(replace(run.frames[0], inference_status="inference_failed",
                                              failure_reason="artificial", detections=None), run.frames[1]))
        unsorted = fixture([[(100, 100, .2), (200, 200, .8)]], sort=False)
        wrong_floor = replace(run, model_provenance=replace(run.model_provenance, export_confidence_floor=.02))
        reordered = replace(run, frames=tuple(reversed(run.frames)))
        invalid_detection = replace(run.frames[0].detections[0], confidence=math.nan)
        invalid = replace(run, frames=(replace(run.frames[0], detections=(invalid_detection,)), run.frames[1]))
        for invalid_run in (failed, unsorted, wrong_floor, reordered, invalid, {}, None):
            with self.subTest(run=invalid_run), self.assertRaises(ValueError):
                list(mean.iter_ranked_frames(invalid_run))


if __name__ == "__main__":
    unittest.main()
