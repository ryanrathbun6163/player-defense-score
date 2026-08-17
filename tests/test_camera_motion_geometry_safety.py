import unittest

import numpy as np

from src.court.export_player_court_coordinates import validate_contract
from src.court.propagate_court_calibration import (
    build_geometry_safe_fallback_trajectory,
    stabilize_terminal_trajectory,
    summarize_tracking,
    validate_smoothed_camera_geometry,
)


WIDTH = 1920
HEIGHT = 1080
REFERENCE_FRAME = 2
CONTROL_POINTS = np.asarray(
    [
        [500.0, 300.0],
        [1400.0, 300.0],
        [500.0, 750.0],
        [1400.0, 750.0],
        [950.0, 525.0],
    ],
    dtype=float,
)


class CameraGeometryValidationTests(unittest.TestCase):
    def test_smooth_translation_sequence_passes(self):
        transforms = []

        for frame_index in range(5):
            offset = (frame_index - REFERENCE_FRAME) * 4.0
            transforms.append(
                np.asarray(
                    [
                        [1.0, 0.0, -offset],
                        [0.0, 1.0, 0.0],
                        [0.0, 0.0, 1.0],
                    ]
                )
            )

        validation = validate_smoothed_camera_geometry(
            transforms,
            WIDTH,
            HEIGHT,
            CONTROL_POINTS,
            REFERENCE_FRAME,
        )

        self.assertEqual(validation["status"], "passed")
        self.assertEqual(validation["issues"], [])

    def test_projective_singularity_is_rejected(self):
        transforms = [np.eye(3) for _ in range(5)]
        transforms[3] = np.asarray(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0015, 0.0, 1.0],
            ]
        )

        validation = validate_smoothed_camera_geometry(
            transforms,
            WIDTH,
            HEIGHT,
            CONTROL_POINTS,
            REFERENCE_FRAME,
        )
        issue_codes = {
            issue["code"] for issue in validation["issues"]
        }

        self.assertEqual(validation["status"], "failed")
        self.assertIn(
            "vanishing_line_crosses_control_region",
            issue_codes,
        )

    def test_local_median_fallback_replaces_extreme_outlier(self):
        trajectories = []

        for frame_index in range(41):
            translated = CONTROL_POINTS + [frame_index * 2.0, 0.0]
            trajectories.append(translated)

        trajectories = np.asarray(trajectories, dtype=float)
        trajectories[20] += 5000.0
        valid_mask = np.ones(41, dtype=bool)

        (
            smoothed,
            accepted_mask,
            median_residuals,
            maximum_residuals,
            summary,
        ) = build_geometry_safe_fallback_trajectory(
            trajectories,
            valid_mask,
            11,
            10,
        )

        self.assertFalse(accepted_mask[20])
        self.assertGreater(median_residuals[20], 12.0)
        self.assertGreater(maximum_residuals[20], 50.0)
        self.assertTrue(np.all(np.isfinite(smoothed)))
        self.assertEqual(summary["median_window_length"], 21)
        self.assertEqual(summary["smoothing_window_length"], 31)


class TerminalTrajectoryStabilizationTests(unittest.TestCase):
    def _moving_trajectory(self):
        trajectory = np.repeat(
            CONTROL_POINTS[None, :, :],
            100,
            axis=0,
        )

        for frame_index in range(70, 100):
            trajectory[frame_index, :, 0] += (
                frame_index - 69
            ) * 2.0

        return trajectory

    def test_sparse_unreliable_tail_is_held_at_last_anchor(self):
        smoothed = self._moving_trajectory()
        observed = smoothed.copy()
        accepted_mask = np.ones(100, dtype=bool)
        accepted_mask[70:] = False
        accepted_mask[[80, 90, 99]] = True

        stabilized, summary = stabilize_terminal_trajectory(
            smoothed,
            accepted_mask,
            20,
            observed=observed,
        )

        self.assertTrue(summary["applied"])
        self.assertEqual(summary["start_frame"], 70)
        self.assertEqual(summary["anchor_frame"], 69)
        self.assertEqual(summary["decision"], "applied_anchor_hold")
        self.assertFalse(summary["motion_evidence"]["passed"])
        expected_hold = np.repeat(
            smoothed[69][None, :, :],
            30,
            axis=0,
        )
        np.testing.assert_allclose(stabilized[70:], expected_hold)

    def test_distributed_coherent_motion_bypasses_anchor_hold(self):
        smoothed = self._moving_trajectory()
        observed = smoothed.copy()
        accepted_mask = np.ones(100, dtype=bool)
        accepted_mask[70:] = False
        accepted_mask[
            [75, 76, 80, 82, 88, 90, 94, 97, 99]
        ] = True

        stabilized, summary = stabilize_terminal_trajectory(
            smoothed,
            accepted_mask,
            20,
            observed=observed,
        )

        self.assertFalse(summary["applied"])
        self.assertEqual(
            summary["decision"],
            "preserved_coherent_terminal_motion",
        )
        evidence = summary["motion_evidence"]
        self.assertTrue(evidence["passed"])
        self.assertEqual(evidence["accepted_frame_count"], 9)
        self.assertEqual(evidence["covered_temporal_bin_count"], 3)
        self.assertEqual(evidence["last_accepted_frame"], 99)
        np.testing.assert_allclose(stabilized, smoothed)

    def test_incoherent_observations_do_not_bypass_anchor_hold(self):
        smoothed = self._moving_trajectory()
        observed = smoothed.copy()
        accepted_frames = [75, 76, 80, 82, 88, 90, 94, 97, 99]
        accepted_mask = np.ones(100, dtype=bool)
        accepted_mask[70:] = False
        accepted_mask[accepted_frames] = True

        for sequence_index, frame_index in enumerate(accepted_frames):
            observed[frame_index, :, 0] += (
                80.0 if sequence_index % 2 else -80.0
            )

        stabilized, summary = stabilize_terminal_trajectory(
            smoothed,
            accepted_mask,
            20,
            observed=observed,
        )

        self.assertTrue(summary["applied"])
        self.assertFalse(summary["motion_evidence"]["passed"])
        self.assertFalse(
            summary["motion_evidence"]["criteria"][
                "maximum_median_support_error"
            ]
        )
        expected_hold = np.repeat(
            smoothed[69][None, :, :],
            30,
            axis=0,
        )
        np.testing.assert_allclose(stabilized[70:], expected_hold)


class CameraGeometryContractTests(unittest.TestCase):
    def test_tracking_summary_discloses_geometry_fallback(self):
        frame_records = [
            {
                "method": "reference_identity",
                "direct_match": None,
            }
        ]

        for _ in range(9):
            frame_records.append(
                {
                    "method": "direct_to_reference",
                    "direct_match": {
                        "inlier_count": 60,
                        "inlier_ratio": 0.6,
                        "median_reprojection_error_px": 1.0,
                    },
                }
            )

        summary = summarize_tracking(
            frame_records,
            {
                "geometry_validation": {"status": "passed"},
                "geometry_fallback": {"applied": True},
            },
        )

        self.assertEqual(
            summary["quality_classification"],
            "usable_with_geometry_safe_fallback_review",
        )

    def test_coordinate_export_rejects_unvalidated_motion_report(self):
        calibration = {
            "video_metadata": {"frame_count": 3},
            "reference_frame_index": 1,
        }
        motion_report = {
            "video_metadata": {"frame_count": 3},
            "reference_frame_index": 1,
        }

        with self.assertRaisesRegex(
            ValueError,
            "passed smoothed-camera geometry validation",
        ):
            validate_contract(
                calibration,
                motion_report,
                np.stack([np.eye(3)] * 3),
                1,
                [],
                0,
                0,
            )


if __name__ == "__main__":
    unittest.main()
