"""Boundaries and native timing for the campaign's pending source references."""
import tempfile
from pathlib import Path
import unittest
import numpy as np

from src.ball_tracking.completion_references import binding, guard_range, presentation_timeline, render_frame


class CompletionReferenceTests(unittest.TestCase):
    def setUp(self):
        self.config = {"possession_id": "possession_003", "range_inclusive": [0, 119],
                       "training_eligible": False, "checkpoint_selection_eligible": False,
                       "human_acceptance": "pending", "role": "post_selection_evaluation_only"}
        self.possession = {"source_video": {"frame_count": 500},
                           "protected_ranges": [[225, 299]], "visible_segments": [[0, 224], [300, 499]]}

    def test_reject_protected_and_existing_reference_before_decode(self):
        self.assertEqual(guard_range(self.config, self.possession, {}), list(range(120)))
        with self.assertRaisesRegex(ValueError, "accepted"):
            guard_range(self.config, self.possession, {("possession_003", 19): {}})
        self.config["range_inclusive"] = [224, 300]
        with self.assertRaisesRegex(ValueError, "protected"):
            guard_range(self.config, self.possession, {})

    def test_role_and_acceptance_cannot_change_in_renderer(self):
        for key, value in (("training_eligible", True), ("checkpoint_selection_eligible", True),
                           ("human_acceptance", "accepted")):
            changed = {**self.config, key: value}
            with self.assertRaisesRegex(ValueError, "pending evaluation-only"):
                guard_range(changed, self.possession, {})

    def test_native_pts_sorted_and_origin_preserved(self):
        # Actual H.264 packets can arrive in decode order, with a nonzero PTS origin.
        probe = {"streams": [{"time_base": "1/12800"}],
                 "packets": [{"pts": 1536, "duration": 512}, {"pts": 512, "duration": 512},
                             {"pts": 1024, "duration": 512}]}
        rows = presentation_timeline(probe, 3)
        self.assertEqual([r["native_pts_ticks"] for r in rows], [512, 1024, 1536])
        self.assertEqual([r["clip_relative_seconds"] for r in rows], [0, .04, .08])
        self.assertEqual(rows[0]["native_pts_seconds"], .04)
        probe["packets"][0]["pts"] = 2048
        with self.assertRaisesRegex(ValueError, "Non-contiguous"):
            presentation_timeline(probe, 3)

    def test_binding_accepts_relative_paths(self):
        # Regression: the CLI initially rendered a video then failed to bind a relative path.
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            path = Path(directory) / "sample.txt"
            path.write_text("source", encoding="utf-8")
            relative = path.relative_to(Path.cwd())
            self.assertEqual(binding(Path.cwd(), relative), binding(Path.cwd(), path))

    def test_overlay_uses_actual_source_dimensions(self):
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        item = {"source_frame_index": 10, "native_pts_ticks": 5120, "native_time_base": "1/12800",
                "annotation": {"visibility": "partially_visible",
                               "geometry": {"center_xy_px": [500, 300], "uncertainty_radius_px": 8}}}
        result = render_frame(frame, item, 120, "new_source", 119)
        self.assertEqual(result[225, 375].tolist(), [0, 255, 255])
        self.assertEqual(result[150, 250].tolist(), [0, 0, 0])


if __name__ == "__main__":
    unittest.main()
