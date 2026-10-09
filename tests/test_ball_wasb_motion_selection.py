"""Behavioral and real producer/consumer checks for the fixed candidate selector."""
from __future__ import annotations

import copy
import unittest
from unittest import mock

import numpy as np

from src.ball_tracking import wasb_development_observation as producer
from src.ball_tracking import wasb_motion_selection as motion


def candidate(index, x, y=100.0, mass=10.0):
    return {"candidate_index": index, "center_x": float(x), "center_y": float(y), "native_score": mass}


def select(rows):
    return motion.select_segment([{"frame_index": i, "candidates": row} for i, row in enumerate(rows)],
                                 1920, 1080, motion.POLICY)


class MotionSelectionTests(unittest.TestCase):
    def test_distractor_rejected_and_real_alternate_keeps_original_identity(self):
        rows = [[candidate(0, 100)], [candidate(0, 110)],
                [candidate(0, 120, mass=8), candidate(1, 700, mass=10)]]
        original = copy.deepcopy(rows)
        result = select(rows)
        self.assertEqual([d["selected_candidate_index"] for d in result], [0, 0, 0])
        self.assertEqual(result[-1]["prediction_xy_px"], [120.0, 100.0])
        self.assertEqual(rows, original)

    def test_mass_guard_does_not_accept_tiny_nearby_component(self):
        result = select([[candidate(0, 100)], [candidate(0, 100, mass=4.9), candidate(1, 800, mass=10)]])
        self.assertIsNone(result[-1]["selected_candidate_index"])
        self.assertEqual(result[-1]["reason"], "motion_abstention")

    def test_fast_dribble_reversal_and_deterministic_distance_tie(self):
        result = select([[candidate(0, 100)], [candidate(0, 158)], [candidate(0, 100)]])
        self.assertTrue(all(d["selected_candidate_index"] == 0 for d in result))
        result = select([[candidate(0, 100)], [candidate(0, 90), candidate(1, 110)]])
        self.assertEqual(result[-1]["selected_candidate_index"], 0)

    def test_three_missing_outputs_expire_history_and_allow_singleton_reacquisition(self):
        result = select([[candidate(0, 100)], [], [], [candidate(0, 1500)], [candidate(0, 1500)]])
        self.assertEqual([d["selected_candidate_index"] for d in result], [0, None, None, None, 0])
        self.assertEqual(result[-1]["reason"], "native_mass_start_or_restart")
        self.assertEqual(result[-1]["history"], [])

    def test_persistent_nearby_false_path_can_lock_selector_honestly(self):
        result = select([[candidate(0, 100)], [candidate(0, 110, mass=6), candidate(1, 1000)],
                         [candidate(0, 120, mass=6), candidate(1, 1010)]])
        self.assertEqual([d["selected_candidate_index"] for d in result], [0, 0, 0])

    def fixture(self):
        source = {"path": "data/clips/synthetic.mp4", "sha256": "a" * 64,
                  "width_px": 1920, "height_px": 1080, "fps": 25.0, "frame_count": 9}
        possession = {"possession_id": "synthetic", "source_video": source,
                      "visible_segments": [[0, 2], [6, 8]], "protected_ranges": [[3, 5]]}
        training = [{"possession_id": "synthetic", "start_frame_index": 0, "end_frame_index": 0}]
        segments = []
        for start, x in ((0, 30), (6, 430)):
            maps = np.zeros((3, 288, 512), dtype=np.float32)
            maps[:, 40:43, x:x + 3] = .8
            frames = producer.observed_frames(maps, [1, 1, 1], start, source, .3)
            segments.append({"segment": [start, start + 2], "frames": frames})
        observations = {"schema_version": "unlabeled_ball_development_observations/v0.1", **possession,
                        "reference_labels": None, "threshold_status": "0.3_development_candidate",
                        "model_provenance": {"test": "actual_producer"},
                        "frames": producer.make_timeline(possession, segments, training)}
        return observations, possession, training

    def test_actual_observation_producer_transport_and_protected_segment_reset(self):
        observations, possession, training = self.fixture()
        original = copy.deepcopy(observations)
        motion.validate_observations(observations, possession, training)
        result = motion.select_timeline(observations, possession, motion.POLICY)
        self.assertEqual(observations, original)
        self.assertEqual(result["frames"][6]["selection_audit"]["reason"], "native_mass_start_or_restart")
        for before, after in zip(observations["frames"], result["frames"]):
            self.assertEqual(after["candidates"], before["candidates"])
            self.assertEqual(after["center_xy_px"], before["center_xy_px"])
        self.assertTrue(all(result["frames"][i]["state"] == "withheld" for i in (3, 4, 5)))

    def test_bad_control_training_and_withheld_records_are_rejected(self):
        observations, possession, training = self.fixture()
        for change in (lambda d: d["frames"][0].__setitem__("training_frame", False),
                       lambda d: d["frames"][0].__setitem__("selected_candidate_index", 8),
                       lambda d: d["frames"][3].__setitem__("center_xy_px", [1, 2])):
            bad = copy.deepcopy(observations)
            change(bad)
            with self.assertRaises(ValueError):
                motion.validate_observations(bad, possession, training)

    @unittest.skipUnless((motion.ROOT / "data/outputs/ball_tracking/wasb/wasb_expanded_development_observation_v0_1/summary.json").exists(),
                         "Requires existing ignored development observations")
    def test_actual_captured_observations_load_without_model_source_or_labels(self):
        with mock.patch("cv2.VideoCapture", side_effect=AssertionError("No source decode")), \
                mock.patch("src.ball_tracking.annotations.load_annotations", side_effect=AssertionError("No labels")):
            result = motion.execute(motion.ROOT, motion.ROOT / motion.DEFAULT_CONFIG, check_only=True)
        self.assertEqual(result["frames"], 1498)
        self.assertFalse(result["labels_read"])
        self.assertEqual(result["model_calls"], 0)


if __name__ == "__main__":
    unittest.main()
