"""Synthetic path-oracle, exact legacy parity and streaming-retention tests."""
import copy
import json
import math
import random
from types import SimpleNamespace
import unittest

from src.ball_tracking import crop_motion_factorial as legacy
from src.ball_tracking.crop_retention import (
    ARMS, STEPS, RankingConfig, iter_ranked_frames, rank_history, summarize_frame,
)
from test_ball_crop_ranking import run_fixture


def config(arm=ARMS[0], threshold=.01, cap=None):
    return RankingConfig(arm, threshold, cap, *STEPS[arm])


def candidate(index, x=100., y=100., confidence=.8):
    return SimpleNamespace(candidate_index=index, confidence=confidence,
                           center_xy_px=(x, y), bbox_xyxy_px=(x-1, y-1, x+1, y+1))


def frame(index, candidates):
    return SimpleNamespace(frame_index=index, inference_status="completed", detections=tuple(candidates))


def run(frames):
    return SimpleNamespace(frames=tuple(frames),
                           source_video=SimpleNamespace(width_px=1920, height_px=1080),
                           model_provenance=SimpleNamespace(export_confidence_floor=.01))


def enumerate_paths(frames, settings, diagonal):
    """Independent exhaustive search: keep every path, with no endpoint DP."""
    paths = []
    for current_frame in frames:
        qualified = [c for c in current_frame.detections if c.confidence >= settings.confidence_threshold]
        if settings.candidate_cap is not None:
            qualified = qualified[:settings.candidate_cap]
        for current in qualified:
            ref = (current_frame.frame_index, current.candidate_index)
            additions = [(current.confidence, (ref,), current)]
            for score, path, old in paths:
                elapsed = ref[0] - path[-1][0]
                if not 1 <= elapsed <= 3:
                    continue
                distance = math.dist(current.center_xy_px, old.center_xy_px)
                if distance <= settings.edge_step * diagonal * elapsed:
                    cost = .25 * (distance / (settings.cost_step * diagonal * elapsed)) ** 2
                    score_after_gap = (score + current.confidence) - .25 * (elapsed - 1)
                    additions.append((score_after_gap - cost, (*path, ref), current))
            paths.extend(additions)
    best = {}
    for item in paths:
        key = item[1][-1]
        if key not in best or (-item[0], item[1]) < (-best[key][0], best[key][1]):
            best[key] = item
    now = frames[-1].frame_index
    endpoints = [{"endpoint": None, "score": 0., "path": [],
                  "endpoint_confidence": None, "trailing_skipped_frames": None}]
    for ref, (score, path, last) in best.items():
        gap = now-ref[0]
        if gap <= 2:
            endpoints.append({"endpoint": list(ref), "score": score - .25 * gap,
                              "path": list(map(list, path)), "endpoint_confidence": last.confidence,
                              "trailing_skipped_frames": gap})
    endpoints.sort(key=lambda e: (-e["score"], int(e["endpoint"] is not None),
                                 -e["endpoint"][0] if e["endpoint"] else 0,
                                 -e["endpoint_confidence"] if e["endpoint"] else 0,
                                 e["endpoint"][1] if e["endpoint"] else 0,
                                 tuple(map(tuple, e["path"]))))
    return best, endpoints


class RetentionConfigTests(unittest.TestCase):
    def test_strict_five_field_fixed_probe_contract_and_variant_identity(self):
        identities = set()
        for arm in ARMS:
            for threshold in (.01, .2, .35):
                for cap in (20, None):
                    c = config(arm, threshold, cap)
                    self.assertEqual(RankingConfig.from_mapping(c.to_dict()), c)
                    identities.add(c.variant_id)
        self.assertEqual(len(identities), 24)
        bad = [dict(config().to_dict(), arm="crop_top_one"),
               dict(config().to_dict(), confidence_threshold=.05),
               dict(config().to_dict(), confidence_threshold=True),
               dict(config().to_dict(), candidate_cap=400),
               dict(config().to_dict(), candidate_cap=20.),
               dict(config().to_dict(), candidate_cap=False),
               dict(config().to_dict(), edge_step=.03),
               dict(config().to_dict(), cost_step=float("nan")),
               dict(config().to_dict(), edge_step=True),
               dict(config().to_dict(), retention_policy="all")]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                RankingConfig.from_mapping(value)
        with self.assertRaises(ValueError):
            RankingConfig.from_mapping({"arm": ARMS[0]})

    def test_original_input_order_must_be_preserved_not_silently_sorted(self):
        invalid = [frame(0, [candidate(0, confidence=.2), candidate(1, confidence=.8)]),
                   frame(0, [candidate(2), candidate(2)]),
                   frame(0, [candidate(True)]),
                   frame(0, [candidate(0, confidence=float("nan"))]),
                   frame(0, [candidate(0, x=float("inf"))])]
        for f in invalid:
            with self.subTest(frame=f), self.assertRaises(ValueError):
                list(iter_ranked_frames(run([f]), config()))
        with self.assertRaises(ValueError):
            rank_history([frame(0, [])], config(), 0.)
        with self.assertRaises(ValueError):
            rank_history([frame(i, []) for i in range(6)], config(), 100.)
        with self.assertRaises(ValueError):
            rank_history([frame(0, []), frame(2, [])], config(), 100.)


class ExactPathTests(unittest.TestCase):
    def test_all_four_probes_match_independent_exhaustive_path_search(self):
        rng = random.Random(634021)
        diagonal = math.hypot(1920, 1080)
        for arm in ARMS:
            for case in range(28):
                frames = []
                for offset in range(5):
                    values = [candidate(21 + j*5, x=100 + rng.randrange(110),
                                        y=100 + rng.randrange(50),
                                        confidence=rng.choice([.01, .2, .35, .7, .9]))
                              for j in range(rng.randrange(4))]
                    values.sort(key=lambda c: -c.confidence)
                    frames.append(frame(offset + 50, values))
                settings = config(arm)
                expected, endpoints = enumerate_paths(frames, settings, diagonal)
                actual = rank_history(frames, settings, diagonal)
                with self.subTest(arm=arm, case=case):
                    self.assertEqual(actual["competing_endpoints"], endpoints)
                    self.assertEqual(actual["winner"], endpoints[0])
                    self.assertEqual(actual["score_margin"], endpoints[0]["score"] - endpoints[1]["score"]
                                     if len(endpoints) > 1 else None)
                    self.assertEqual(len(actual["best_path_per_endpoint"]), len(expected))
                    for record in actual["best_path_per_endpoint"]:
                        score, path, _ = expected[tuple(record["endpoint"])]
                        self.assertEqual(record["score"], score)
                        self.assertEqual(record["path"], list(map(list, path)))

    def test_cap20_full_trace_exactly_matches_existing_legacy_on_synthetic_inputs(self):
        rng = random.Random(383194)
        for arm in ARMS:
            for threshold in (.01, .2, .35):
                points = [[(100+rng.randrange(90), 200+rng.randrange(60),
                            rng.choice([.01, .1, .2, .35, .5, .9]))
                           for _ in range(24)] for _ in range(6)]
                _, typed = run_fixture(points)
                old = legacy.rank_candidates(typed, legacy.RankingConfig(arm, threshold, 20, *STEPS[arm]), "e"*40)
                actual = list(iter_ranked_frames(typed, config(arm, threshold, 20)))
                with self.subTest(arm=arm, threshold=threshold):
                    self.assertEqual(actual, old["frames"])

    def test_all_and_cap20_are_exactly_equal_when_each_frame_has_at_most_twenty_qualified(self):
        frames = [frame(i, [*[candidate(j, x=100+j, confidence=.8-j*.02) for j in range(20)],
                             *[candidate(20+j, x=120+j, confidence=.19-j*.01) for j in range(5)]])
                  for i in range(6)]
        for arm in ARMS:
            for threshold in (.2, .35):
                source = run(frames)
                capped = list(iter_ranked_frames(source, config(arm, threshold, 20)))
                all_saved = list(iter_ranked_frames(source, config(arm, threshold)))
                self.assertEqual(all_saved, capped)

    def test_current_and_history_candidates_beyond_twenty_are_admitted(self):
        # The low-confidence 99-to-99 stationary path beats each moving .8 path.
        # Capping each frame removes that path throughout the horizon.
        frames = []
        for i in range(5):
            clutter = [candidate(j, x=500+i*20, y=500+j*40, confidence=.8) for j in range(20)]
            frames.append(frame(i, [*clutter, candidate(99, confidence=.7)]))
        source = run(frames)
        all_frames = list(iter_ranked_frames(source, config()))
        capped = list(iter_ranked_frames(source, config(cap=20)))
        winner = all_frames[-1]["ranking"]["winner"]
        self.assertEqual(winner["path"], [[i, 99] for i in range(5)])
        self.assertEqual(all_frames[-1]["emitted_candidate_indices"], [99])
        self.assertNotEqual(capped[-1]["emitted_candidate_indices"], [99])
        self.assertTrue(all([i, 99] in [p["endpoint"] for p in all_frames[-1]["ranking"]["best_path_per_endpoint"]]
                            for i in range(5)))
        self.assertTrue(all(p["endpoint"][1] != 99 for p in capped[-1]["ranking"]["best_path_per_endpoint"]))
        cap_edges = capped[-1]["ranking"]["eligible_edges"]
        all_edges = all_frames[-1]["ranking"]["eligible_edges"]
        self.assertTrue(cap_edges)
        self.assertTrue(all(edge in all_edges for edge in cap_edges))
        self.assertGreaterEqual(winner["score"], capped[-1]["ranking"]["winner"]["score"])

    def test_every_capped_path_keeps_its_component_scores_in_all_candidate_graph(self):
        frames = [frame(i, [*[candidate(j, x=300+j*8+i*12, confidence=.8) for j in range(20)],
                             candidate(80, x=900, confidence=.7), candidate(99, x=920, confidence=.6)])
                  for i in range(4)]
        diagonal = math.hypot(1920, 1080)
        by_ref = {(f.frame_index, c.candidate_index): c for f in frames for c in f.detections}
        for arm in ARMS:
            capped = rank_history(frames, config(arm, cap=20), diagonal)
            complete = rank_history(frames, config(arm), diagonal)
            edges = {(tuple(e["from"]), tuple(e["to"])): e for e in complete["eligible_edges"]}
            self.assertTrue(capped["eligible_edges"])
            for edge in capped["eligible_edges"]:
                self.assertEqual(edges[(tuple(edge["from"]), tuple(edge["to"]))], edge)
            for record in capped["best_path_per_endpoint"]:
                path = list(map(tuple, record["path"]))
                score = by_ref[path[0]].confidence
                for before, after in zip(path, path[1:]):
                    edge = edges[(before, after)]
                    score = ((score + by_ref[after].confidence) - edge["skipped_frame_penalty"]) - edge["motion_penalty"]
                self.assertEqual(score, record["score"])
            self.assertGreaterEqual(complete["winner"]["score"], capped["winner"]["score"])

    def test_inclusive_threshold_and_source_values_are_unchanged(self):
        original = run([frame(0, [candidate(99, confidence=.2), candidate(120, confidence=.199999999)])])
        before = copy.deepcopy(original)
        result = list(iter_ranked_frames(original, config(threshold=.2)))[0]
        self.assertEqual(result["emitted_candidate_indices"], [99])
        self.assertEqual(result["candidate_decisions"], [{"candidate_index": 99, "disposition": "emitted"},
                                                       {"candidate_index": 120, "disposition": "below_threshold"}])
        self.assertEqual(original, before)
        self.assertEqual(result["ranking"]["winner"]["endpoint_confidence"], .2)

    def test_ties_empty_and_older_endpoint_missing_reasons(self):
        equal = rank_history([frame(50, [candidate(99), candidate(21)])], config(), 2202.)
        self.assertEqual(equal["winner"]["endpoint"], [50, 21])
        tied_paths = rank_history([frame(0, [candidate(99), candidate(21)]), frame(1, [candidate(88)])], config(), 2202.)
        self.assertEqual(tied_paths["winner"]["path"], [[0, 21], [1, 88]])
        zero_tie = list(iter_ranked_frames(run([frame(0, [candidate(0, confidence=.25)]), frame(1, [])]), config()))[-1]
        self.assertIsNone(zero_tie["ranking"]["winner"]["endpoint"])
        self.assertEqual(zero_tie["decision_reason"], "empty_hypothesis")
        older = list(iter_ranked_frames(run([frame(0, [candidate(0, confidence=.9)]), frame(1, [])]), config()))[-1]
        self.assertEqual(older["ranking"]["winner"]["endpoint"], [0, 0])
        self.assertEqual(older["emitted_candidate_indices"], [])
        self.assertEqual(older["decision_reason"], "earlier_endpoint_no_current_observation")
        empty = list(iter_ranked_frames(run([frame(0, [])]), config()))[0]
        self.assertIsNone(empty["ranking"]["score_margin"])
        self.assertEqual(empty["output_state"], "no_accepted_observation")

    def test_edge_limits_gaps_and_unclipped_cost_scale_remain_independent(self):
        diagonal = 1000.
        frames = [frame(0, [candidate(99, x=100, confidence=.9)]), frame(1, []), frame(2, []),
                  frame(3, [candidate(98, x=130, confidence=.9)])]
        at_limit = rank_history(frames, config(), diagonal)
        self.assertEqual(len(at_limit["eligible_edges"]), 1)
        self.assertEqual(at_limit["eligible_edges"][0]["elapsed_frames"], 3)
        self.assertEqual(at_limit["eligible_edges"][0]["skipped_frame_penalty"], .5)
        self.assertEqual(at_limit["eligible_edges"][0]["normalized_step"], 1.)
        frames[-1] = frame(3, [candidate(98, x=130.0001, confidence=.9)])
        self.assertEqual(rank_history(frames, config(), diagonal)["eligible_edges"], [])
        wide = rank_history([frame(0, [candidate(0)]), frame(1, [candidate(1, x=125)])], config(ARMS[2]), diagonal)
        self.assertEqual(wide["eligible_edges"][0]["normalized_step"], 2.5)
        self.assertEqual(wide["eligible_edges"][0]["motion_penalty"], .25*2.5**2)
        gap_four = rank_history([frame(0, [candidate(0)]), *[frame(i, []) for i in (1, 2, 3)],
                                 frame(4, [candidate(1)])], config(), diagonal)
        self.assertEqual(gap_four["eligible_edges"], [])


class StreamingAuditTests(unittest.TestCase):
    def test_stream_is_causal_without_prevalidating_future_and_resets_per_window(self):
        class FutureFrame:
            @property
            def frame_index(self):
                raise AssertionError("future candidate read")
        class CandidatesOnly:
            frames = (frame(0, [candidate(21)]), FutureFrame())
            source_video = SimpleNamespace(width_px=1920, height_px=1080)
            model_provenance = SimpleNamespace(export_confidence_floor=.01)
            @property
            def annotations(self):
                raise AssertionError("annotation read")
            @property
            def pixels(self):
                raise AssertionError("pixel read")
        stream = iter_ranked_frames(CandidatesOnly(), config())
        first = next(stream)
        self.assertEqual(first["frame_index"], 0)
        self.assertEqual(first["emitted_candidate_indices"], [21])
        stream.close()
        fresh = list(iter_ranked_frames(run([frame(50, [])]), config()))
        self.assertEqual(fresh[0]["horizon_start"], 50)
        self.assertEqual(fresh[0]["ranking"]["best_path_per_endpoint"], [])

    def test_five_frame_horizon_expires_old_nodes_and_does_not_revise_outputs(self):
        source = run([frame(i, [candidate(99)]) for i in range(7)])
        actual = list(iter_ranked_frames(source, config()))
        self.assertEqual([f["horizon_start"] for f in actual], [0, 0, 0, 0, 0, 1, 2])
        self.assertEqual(actual[-1]["ranking"]["winner"]["path"], [[i, 99] for i in range(2, 7)])
        self.assertEqual(actual[0]["ranking"]["winner"]["path"], [[0, 99]])
        with self.assertRaises(ValueError):
            list(iter_ranked_frames(run([frame(0, []), frame(2, [])]), config()))

    def test_compact_summary_keeps_original_decisions_and_binds_full_audit_content(self):
        full = list(iter_ranked_frames(run([frame(0, [candidate(j, confidence=.9-j*.1) for j in range(5)])]), config()))[0]
        before = copy.deepcopy(full)
        compact = summarize_frame(full)
        self.assertEqual(full, before)
        self.assertEqual(compact["candidate_decisions"], full["candidate_decisions"])
        self.assertEqual(compact["ranking"]["winner"], full["ranking"]["winner"])
        self.assertEqual(compact["ranking"]["best_path_for_winner"], full["ranking"]["best_path_per_endpoint"][0])
        self.assertEqual([r["endpoint"][1] for r in compact["ranking"]["current_alternatives"]], [1, 2, 3])
        self.assertEqual(compact["audit_counts"], {"node_count": 5, "edge_count": 0, "competing_endpoint_count": 6})
        self.assertEqual(json.loads(json.dumps(full)), full)
        compact["candidate_decisions"][0]["disposition"] = "modified_test_copy"
        self.assertEqual(full, before)

    def test_progress_callback_reports_every_pair_visit_and_can_abort_without_result(self):
        events = []
        source = run([frame(i, [candidate(j, confidence=.9) for j in range(50)]) for i in range(3)])
        frames = list(iter_ranked_frames(source, config(), events.append))
        completed = [e for e in events if e["phase"] == "horizon_complete"]
        self.assertEqual([e["pair_visits"] for e in completed], [50*49//2, 100*99//2, 150*149//2])
        self.assertTrue(any(e["phase"] == "ranking" for e in events))
        self.assertEqual(completed[-1]["edge_count"], len(frames[-1]["ranking"]["eligible_edges"]))
        class Abort(RuntimeError):
            pass
        def stop(event):
            if event["phase"] == "ranking":
                raise Abort("synthetic resource limit")
        stream = iter_ranked_frames(source, config(), stop)
        next(stream)
        with self.assertRaises(Abort):
            next(stream)

    def test_failed_detector_frame_and_export_floor_are_rejected(self):
        f = frame(0, [])
        f.inference_status = "failed"
        with self.assertRaises(ValueError):
            list(iter_ranked_frames(run([f]), config()))
        source = run([frame(0, [])])
        source.model_provenance.export_confidence_floor = .2
        with self.assertRaises(ValueError):
            list(iter_ranked_frames(source, config()))


if __name__ == "__main__":
    unittest.main()
