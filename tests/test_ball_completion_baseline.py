"""Retained-output transport, native timing and protected-frame regressions."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from src.ball_tracking import completion_baseline as package
from src.ball_tracking import wasb_development_observation as producer
from src.ball_tracking.wasb_experiment import read_json


class CompletionBaselineTests(unittest.TestCase):
    def test_native_packet_pts_preserve_nonzero_origin_and_presentation_order(self):
        metadata = {"streams": [{"time_base": "1/12800"}],
                    "packets": [{"pts": 1536, "duration": 512}, {"pts": 512, "duration": 512},
                                {"pts": 1024, "duration": 512}]}
        times = package.packet_timeline(metadata, 3)
        self.assertEqual([t["native_timestamp_seconds"] for t in times], [.04, .08, .12])
        self.assertEqual([t["playback_timestamp_seconds"] for t in times], [0, .04, .08])
        for mutate in (lambda m: m["packets"].pop(), lambda m: m["packets"][0].update(pts=512),
                       lambda m: m["packets"][0].update(duration=0)):
            bad = copy.deepcopy(metadata)
            mutate(bad)
            with self.assertRaises(ValueError):
                package.packet_timeline(bad, 3)

    def fixture(self):
        source = {"path": "data/clips/artificial.mp4", "sha256": "a" * 64,
                  "width_px": 512, "height_px": 288, "fps": 25., "frame_count": 7}
        possession = {"possession_id": "artificial", "source_video": source,
                      "visible_segments": [[0, 2], [4, 6]], "protected_ranges": [[3, 3]]}
        means = np.zeros((3, 288, 512), np.float32)
        means[0, 40:42, 50:52] = .8
        # Critical fixture comes from the actual observation producer.
        segments = [{"segment": [start, start + 2],
                     "frames": producer.observed_frames(means, [1, 1, 1], start, source, .3),
                     "triplets": [{"input_frame_indices": [start, start + 1, start + 2]}]}
                    for start in (0, 4)]
        observations = {"possession_id": "artificial", "source_video": source,
                        "visible_segments": possession["visible_segments"], "protected_ranges": [[3, 3]],
                        "model_provenance": {"weights": {"sha256": "b" * 64}, "inference": producer.POLICY},
                        "segments": segments, "frames": producer.make_timeline(possession, segments, [])}
        times = package.packet_timeline({"streams": [{"time_base": "1/25"}],
            "packets": [{"pts": i, "duration": 1} for i in range(7)]}, 7)
        return possession, observations, times

    def test_actual_producer_output_keeps_points_mass_and_missing_states(self):
        possession, observations, times = self.fixture()
        package.validate_observations(possession, observations, "b" * 64)
        rows = package.frame_records(possession, observations, times, {})
        self.assertEqual(rows[0]["center_xy_px"], observations["frames"][0]["center_xy_px"])
        self.assertGreater(rows[0]["confidence"]["value"], 1)
        self.assertFalse(rows[0]["confidence"]["is_probability"])
        self.assertIsNone(rows[0]["confidence"]["calibrated_probability"])
        self.assertEqual(rows[1]["missing_reason"], "no_component_strictly_above_0.3")
        self.assertEqual(rows[3]["observation_type"], "withheld")
        self.assertEqual(rows[3]["reviewed_players_display_only"], [])
        intervals = package.missing_intervals(rows)
        self.assertEqual([(i["start_frame_index"], i["end_frame_index"]) for i in intervals], [(1, 2), (5, 6)])
        self.assertEqual([i["duration_seconds"] for i in intervals], [.08, .08])
        self.assertTrue(all(i["eligible_gap_gate"] == "inconclusive" for i in intervals))

    def test_source_alignment_and_protected_temporal_leak_are_rejected(self):
        possession, observations, times = self.fixture()
        mutations = [lambda o: o["segments"][0]["triplets"][0].update(input_frame_indices=[1, 2, 3]),
                     lambda o: o["frames"][3].update(center_xy_px=[1, 2]),
                     lambda o: o["frames"][0].update(center_xy_px=[1, 2]),
                     lambda o: o["frames"][0].update(contribution_count=2),
                     lambda o: o["frames"].pop()]
        for mutate in mutations:
            bad = copy.deepcopy(observations)
            mutate(bad)
            with self.assertRaises(ValueError):
                package.validate_observations(possession, bad, "b" * 64)
        with self.assertRaisesRegex(ValueError, "player time"):
            package.frame_records(possession, observations, times, {0: [{"original_timestamp_seconds": .04}]})

    @unittest.skipUnless((package.ROOT / "data/outputs/ball_tracking/wasb/wasb_expanded_development_observation_v0_1/summary.json").exists(),
                         "Saved local baseline is not available")
    def test_all_real_saved_producer_records_consumed_without_source_decoder(self):
        config = read_json(package.ROOT / package.DEFAULT_CONFIG)
        old = read_json(package.ROOT / config["observation_config"]["path"])
        summary = read_json(package.ROOT / config["observation_summary"]["path"])
        totals = {"observed": 0, "missing": 0, "withheld": 0}
        with patch("cv2.VideoCapture", side_effect=AssertionError("No source decoder")):
            for possession, saved in zip(old["possessions"], summary["possessions"], strict=True):
                observations = read_json(package.ROOT / saved["observations"]["path"])
                package.validate_observations(possession, observations, config["retained_checkpoint"]["sha256"])
                for row in observations["frames"]:
                    totals[row["state"]] += 1
        self.assertEqual(totals, {"observed": 979, "missing": 294, "withheld": 225})


if __name__ == "__main__":
    unittest.main()
