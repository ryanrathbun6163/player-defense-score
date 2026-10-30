"""Independent exhaustive path oracle for the prospective sequence objective.

Synthetic inputs only. This enumerates complete paths, without calling the
implementation's support, transition, validation or dynamic-programming helpers.
It checks each alternative-state margin as well as the chosen objective.
"""
from copy import deepcopy
import itertools
import json
import math
from pathlib import Path
import random
import unittest

from src.ball_tracking.weak_response_sequence import choose_sequence


PARAMETERS = json.loads((Path(__file__).resolve().parents[1] /
    "configs/ball_tracking/proposals/weak_response_v0_1.json").read_text())["sequence"]


def point(index, x, *, mass=10, strong=True, inside=True):
    return {"candidate_index": index, "center_x": x, "center_y": 50,
            "native_score": mass, "in_source_bounds": inside,
            "original_index": index if strong else None}


def exhaustive_scores(pools, times, width, parameters):
    """Enumerate state tuples and calculate their costs directly from the spec."""
    def distance(a, b):
        return math.hypot(a["center_x"] - b["center_x"], a["center_y"] - b["center_y"])

    rewards = []
    for position, pool in enumerate(pools):
        largest = max((c["native_score"] for c in pool
                       if c["original_index"] is not None and c["in_source_bounds"]), default=1)
        scores = {None: parameters["missing_reward"]}
        for index, candidate in enumerate(pool):
            if not candidate["in_source_bounds"]:
                continue
            if candidate["original_index"] is not None:
                scores[index] = max(parameters["minimum_strong_reward"], parameters["strong_reward"] +
                    parameters["strong_relative_mass_weight"] * math.log(candidate["native_score"] / largest))
                continue
            reachable_times = []
            for other_position, other_pool in enumerate(pools):
                dt = times[other_position] - times[position]
                if 0 < abs(dt) <= parameters["weak_anchor_horizon_seconds"] + 1e-12:
                    if any(other["original_index"] is not None and other["in_source_bounds"]
                           and distance(candidate, other) <= width * parameters["maximum_speed_widths_per_second"] * abs(dt)
                           for other in other_pool):
                        reachable_times.append(dt)
            if any(dt < 0 for dt in reachable_times) and any(dt > 0 for dt in reachable_times):
                scores[index] = parameters["weak_reward"]
        rewards.append(scores)

    result = []
    for path in itertools.product(*(list(reward) for reward in rewards)):
        value = sum(rewards[i][state] for i, state in enumerate(path))
        for position, (left_index, right_index) in enumerate(zip(path, path[1:])):
            if left_index is None and right_index is None:
                continue
            if left_index is None or right_index is None:
                value -= parameters["switch_missing_cost"]
                continue
            delta = times[position + 1] - times[position]
            length = distance(pools[position][left_index], pools[position + 1][right_index])
            if length > width * delta * parameters["maximum_speed_widths_per_second"]:
                value = -math.inf
                break
            value -= parameters["motion_cost_weight"] * (
                length / (width * delta * parameters["motion_scale_widths_per_second"])) ** 2
        result.append((path, value))
    return result


class WeakResponseSequenceOracleTests(unittest.TestCase):
    def assert_matches_oracle(self, pools, times, width=1000, parameters=PARAMETERS):
        before = deepcopy((pools, times, parameters))
        chosen, details = choose_sequence(pools, times, width, parameters)
        values = exhaustive_scores(pools, times, width, parameters)
        optimum = max(value for _, value in values)
        self.assertAlmostEqual(dict(values)[tuple(chosen)], optimum, places=12)
        self.assertAlmostEqual(details["objective"], optimum, places=12)
        for position, state in enumerate(chosen):
            alternatives = [value for path, value in values
                            if path[position] != state and math.isfinite(value)]
            margin = details["frames"][position]["global_alternative_margin"]
            with self.subTest(position=position):
                if alternatives:
                    self.assertAlmostEqual(margin, optimum - max(alternatives), places=12)
                else:
                    self.assertIsNone(margin)
        self.assertEqual((pools, times, parameters), before)
        return chosen, details

    def test_sixty_deterministic_synthetic_contexts_and_every_alternative_margin(self):
        generator = random.Random(8812)
        for trial in range(60):
            pools = [[point(index, generator.choice((90, 100, 110, 200, 500)),
                            mass=generator.choice((1, 3, 10)), strong=generator.random() < .6,
                            inside=generator.random() > .1)
                      for index in range(generator.randrange(3))] for _ in range(4)]
            with self.subTest(trial=trial):
                self.assert_matches_oracle(pools, [0, .016, .033, .050])

    def test_two_ended_support_and_revisable_anchor_competition(self):
        pools = [[point(0, 100), point(1, 500)],
                 [point(0, 102, strong=False), point(1, 500, strong=False)],
                 [point(0, 104, strong=False), point(1, 500, strong=False)],
                 [point(0, 106), point(1, 500)]]
        self.assert_matches_oracle(pools, [0, .016, .033, .050])
        pools[-1] = []
        self.assert_matches_oracle(pools, [0, .016, .033, .050])

    def test_empty_context_and_exact_ties_have_explicit_deterministic_states(self):
        chosen, _ = self.assert_matches_oracle([[], [], []], [0, .02, .04])
        self.assertEqual(chosen, [None, None, None])
        parameters = {**PARAMETERS, "strong_reward": 0, "minimum_strong_reward": 0,
                      "strong_relative_mass_weight": 0, "weak_reward": 0,
                      "motion_cost_weight": 0, "switch_missing_cost": 0}
        pools = [[point(0, 100), point(1, 100)] for _ in range(3)]
        chosen, details = self.assert_matches_oracle(pools, [0, .02, .04], parameters=parameters)
        self.assertEqual(chosen, [0, 0, 0])
        self.assertEqual([r["global_alternative_margin"] for r in details["frames"]], [0, 0, 0])

    def test_sparse_neighbor_query_keeps_inclusive_speed_boundary(self):
        # A cheaper synthetic motion penalty makes losing a boundary edge alter
        # the optimal path. This changes no experimental recipe parameter.
        parameters = {**PARAMETERS, "motion_scale_widths_per_second": 3.0}
        for middle in (24.0, math.nextafter(24.0, math.inf), math.nextafter(24.0, -math.inf)):
            pools = [[point(0, 0)], [point(0, middle)], [point(0, 48)]]
            chosen, _ = self.assert_matches_oracle(pools, [0, .016, .032], parameters=parameters)
            if middle == 24:
                self.assertEqual(chosen, [0, 0, 0])
        diagonal = [[{**point(0, 3 * i), "center_y": 4 * i}] for i in range(3)]
        chosen, _ = self.assert_matches_oracle(diagonal, [0, 1 / 300, 2 / 300], parameters=parameters)
        self.assertEqual(chosen, [0, 0, 0])


if __name__ == "__main__":
    unittest.main()
