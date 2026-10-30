import json
from pathlib import Path
import unittest

from src.ball_tracking.weak_response_sequence import choose_sequence, observation_rows

PARAMS = json.loads((Path(__file__).resolve().parents[1] / "configs/ball_tracking/proposals/weak_response_v0_1.json").read_text())["sequence"]


def point(x, index=0, mass=10, strong=True):
    return {"candidate_index": index, "center_x": x, "center_y": 50.0, "native_score": mass,
            "in_source_bounds": True, "original_index": index if strong else None}


class WeakSequenceTests(unittest.TestCase):
    def test_original_wrong_choice_can_change(self):
        pools = [[point(100)], [point(800, mass=11), point(101, 1)], [point(102)]]
        chosen, detail = choose_sequence(pools, [0, 1/60, 2/60], 1000, PARAMS)
        self.assertEqual(chosen, [0, 1, 0])
        self.assertFalse(detail["reference_inputs_used"])

    def test_observed_weak_path_with_two_ended_support(self):
        pools = [[point(100)]] + [[point(100+i, strong=False)] for i in range(1, 20)] + [[point(120)]]
        chosen, _ = choose_sequence(pools, [i/60 for i in range(21)], 1000, PARAMS)
        self.assertEqual(chosen, [0]*21)

    def test_unbracketed_weak_and_empty_remain_missing(self):
        pools = [[point(100, strong=False)], [], [point(102, strong=False)]]
        self.assertEqual(choose_sequence(pools, [0, .02, .04], 1000, PARAMS)[0], [None]*3)

    def test_strong_conflict_can_abstain_with_nonempty_pool(self):
        pools = [[point(100)], [point(101)], [point(900)], [point(102)], [point(103)]]
        self.assertIsNone(choose_sequence(pools, [i/60 for i in range(5)], 1000, PARAMS)[0][2])

    def test_time_not_frame_count_controls_motion(self):
        pools = [[point(100)], [point(200)], [point(300)]]
        fast = choose_sequence(pools, [0, .01, .02], 1000, PARAMS)[0]
        slow = choose_sequence(pools, [0, .2, .4], 1000, PARAMS)[0]
        self.assertIn(None, fast)
        self.assertEqual(slow, [0, 0, 0])

    def test_out_of_bounds_and_invalid_timing(self):
        p = point(100); p["in_source_bounds"] = False
        self.assertEqual(choose_sequence([[p]], [0], 1000, PARAMS)[0], [None])
        with self.assertRaises(ValueError):
            choose_sequence([[point(0)], [point(1)]], [1, 1], 1000, PARAMS)

    def test_transport_preserves_observed_coordinates_and_source(self):
        native = [{"source_frame_index": 20, "source_pts_ticks": 1000, "center_xy_px": [500, 50],
                   "selected_candidate_index": 0, "mean_heatmap_sha256": "unchanged"}]
        pool = [[point(501)]]
        chosen, d = choose_sequence(pool, [0], 1000, PARAMS)
        result = observation_rows(native, pool, chosen, d, "sequence_strong")
        self.assertEqual(result[0]["center_xy_px"], [501, 50])
        self.assertEqual(result[0]["original_center_xy_px"], [500, 50])
        self.assertEqual(result[0]["mean_heatmap_sha256"], "unchanged")
        self.assertEqual(native[0]["center_xy_px"], [500, 50])


if __name__ == "__main__":
    unittest.main()
