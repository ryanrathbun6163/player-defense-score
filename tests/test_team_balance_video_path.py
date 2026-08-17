import unittest
from pathlib import Path
from unittest.mock import patch

from src.identity import review_cross_track_switches as cross
from src.identity import review_team_balance as team_balance


class FakeCapture:
    def __init__(self, path):
        self.path = path
        self.requested_frames = []
        self.released = False

    def isOpened(self):
        return True

    def set(self, property_id, frame_index):
        self.requested_frames.append(
            (property_id, frame_index)
        )

    def read(self):
        return True, "decoded-frame"

    def release(self):
        self.released = True


class FakeCv2:
    CAP_PROP_POS_FRAMES = 1

    def __init__(self):
        self.capture = None

    def VideoCapture(self, path):
        self.capture = FakeCapture(path)
        return self.capture


class CrossTrackFrameReaderTests(unittest.TestCase):
    def test_explicit_video_path_overrides_module_global(self):
        fake_cv2 = FakeCv2()

        with patch.object(
            cross,
            "VIDEO_PATH",
            Path("wrong-video.mp4"),
            create=True,
        ), patch.object(cross.residual, "cv2", fake_cv2):
            frames = cross.read_frames(
                {12},
                Path("configured-video.mp4"),
            )

        self.assertEqual(fake_cv2.capture.path, "configured-video.mp4")
        self.assertEqual(
            fake_cv2.capture.requested_frames,
            [(FakeCv2.CAP_PROP_POS_FRAMES, 12)],
        )
        self.assertTrue(fake_cv2.capture.released)
        self.assertEqual(frames, {12: "decoded-frame"})

    def test_cross_track_call_can_still_use_module_video_path(self):
        fake_cv2 = FakeCv2()

        with patch.object(
            cross,
            "VIDEO_PATH",
            Path("cross-track-video.mp4"),
            create=True,
        ), patch.object(cross.residual, "cv2", fake_cv2):
            frames = cross.read_frames({21})

        self.assertEqual(fake_cv2.capture.path, "cross-track-video.mp4")
        self.assertEqual(frames, {21: "decoded-frame"})


class TeamBalanceFrameReaderTests(unittest.TestCase):
    def test_montage_generation_passes_configured_video_path(self):
        configured_path = Path("data/clips/possession_002.mp4")
        captured = {}

        def read_frames(frame_indices, video_path=None):
            captured["frame_indices"] = frame_indices
            captured["video_path"] = video_path
            return {}

        report = {
            "context_frames": [],
            "review_identities": [],
        }

        with patch.object(
            team_balance,
            "VIDEO_PATH",
            configured_path,
            create=True,
        ), patch.object(
            team_balance,
            "CONTEXT_PATH",
            Path("context.jpg"),
            create=True,
        ), patch.object(
            team_balance,
            "IDENTITY_GRID_PATH",
            Path("identities.jpg"),
            create=True,
        ), patch.object(
            team_balance.cross,
            "read_frames",
            side_effect=read_frames,
        ), patch.object(
            team_balance,
            "context_montage",
            return_value="context-montage",
        ), patch.object(
            team_balance,
            "identity_grid",
            return_value="identity-grid",
        ), patch.object(team_balance.cross, "write_montage"):
            team_balance.generate_montages(report, {})

        self.assertEqual(captured["frame_indices"], set())
        self.assertEqual(captured["video_path"], configured_path)


if __name__ == "__main__":
    unittest.main()
