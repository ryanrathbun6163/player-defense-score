"""Native review transport using existing PNG/observation producers and real H.264."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from src.ball_tracking import nba_action_review as review
from src.ball_tracking import nba_wasb_diagnostic as diagnostic
from tests.test_nba_annotations import build_fixture
from tests.test_nba_wasb_diagnostic import FakeAdapter

FFBIN = Path("C:/Users/Ryan/AppData/Local/Microsoft/WinGet/Packages/"
             "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0-full_build/bin")
FFMPEG = shutil.which("ffmpeg") or str(FFBIN/"ffmpeg.exe")


class NBAActionReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="nba_action_review_synthetic_")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        _, draft = build_fixture(self.root)
        self.manifest = {key: copy.deepcopy(draft[key]) for key in
                         ("candidate_id", "game_id", "approved_role", "source_video", "time_base", "frames")}
        self.manifest["source_end_exclusive_pts_ticks"] = 1000862
        # The actual observation producer emits all candidate/selection/source fields.
        # Synthetic weights are never loaded; no real NBA pixels or models are read.
        reference = {**self.manifest, "bindings": {}, "origin": {"kind": "synthetic_fixture"},
                     "human_review": {"status": "fixture_only"}}
        config = {"pretrained_checkpoint": {"path": "synthetic", "sha256": "0"*64}}
        plan = {"checkpoint": {"path": "synthetic", "sha256": "1"*64}, "inference_code": {"fixture": True}}
        self.observations = diagnostic.infer_reference(self.root, reference, config, plan,
                                                       self.root/"synthetic_observation", lambda: FakeAdapter())
        self.output = self.root/"data/outputs/action_review"

    def test_producer_frame_pts_and_state_joins_fail_before_outputs(self):
        cases = []
        for field, value in (("source_frame_index", 999), ("source_pts_ticks", 123),
                             ("state", "missing"), ("center_xy_px", [999.0, 2.0])):
            changed = copy.deepcopy(self.observations)
            changed["frames"][0][field] = value
            cases.append(changed)
        for changed in cases:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                review.render_action(self.root, self.manifest, changed, FFMPEG, self.output)
        self.assertFalse(self.output.exists())
        changed = copy.deepcopy(self.manifest)
        changed["source_end_exclusive_pts_ticks"] += 1
        with self.assertRaisesRegex(ValueError, "cadence"):
            review.validate_inputs(changed, self.observations)
        changed = copy.deepcopy(self.manifest)
        changed["annotations"] = []
        with self.assertRaisesRegex(ValueError, "unlabeled"):
            review.validate_inputs(changed, self.observations)

    def test_overlay_geometry_missing_withheld_and_frame_key(self):
        frame = self.manifest["frames"][0]
        source = Image.new("RGB", (8, 6), (20, 30, 40))
        observed = self.observations["frames"][0]
        image, geometry = review.render_overlay(source, frame, observed, 0, "fixture")
        left, top, width, height = geometry["source_view_rect"]
        x, y = observed["center_xy_px"]
        self.assertEqual(image.getpixel((round(left+x*width/8), round(top+y*height/6))), (255, 69, 197))
        for state in ("missing", "withheld"):
            row = {**observed, "state": state, "center_xy_px": None, "candidates": [], "temporal_contributions": 0}
            missing, geometry = review.render_overlay(source, frame, row, 0, "fixture")
            self.assertIsNone(geometry["point_source_pixels"])
            self.assertEqual(missing.getpixel((round(left+x*width/8), round(top+y*height/6))), (20, 30, 40))
        pixels = np.asarray(image)
        bits = "".join("1" if pixels[review.KEY_TOP+4, i*review.KEY_CELL+4].mean() > 127 else "0" for i in range(112))
        self.assertEqual(bits, review.key_bits(0, frame))

    @unittest.skipUnless(Path(FFMPEG).is_file(), "Installed FFmpeg required")
    def test_real_native_pts_full_decode_final_hold_and_resume(self):
        self.observations["frames"][1].update(state="missing", center_xy_px=None, candidates=[])
        self.observations["frames"][2].update(state="withheld", center_xy_px=None, candidates=[],
                                                 temporal_contributions=0, withheld_reason="synthetic short segment")
        result = review.render_action(self.root, self.manifest, self.observations, FFMPEG, self.output)
        verification = json.loads((self.root/result["verification"]["path"]).read_text())
        self.assertEqual(verification["decoded_frames"], 3)
        self.assertEqual(verification["actual_final_source_frame_index"], 662)
        self.assertEqual(verification["timeline_duration_ticks"], 94500)
        self.assertEqual(verification["additional_final_hold_ticks"], 90000)
        self.assertTrue(verification["native_pts_all_frames_verified"])
        self.assertTrue(verification["decoded_source_frame_keys_all_verified"])
        probe = json.loads((self.root/result["ffprobe"]["path"]).read_text())
        self.assertEqual([f["best_effort_timestamp"] for f in probe["frames"]], [0, 1440, 2970])
        self.assertEqual([f["duration"] for f in probe["frames"]], [1440, 1530, 91530])
        self.assertEqual([p.name for p in self.output.rglob("*.png")], ["final_frame.png"])
        with patch("av.open", side_effect=AssertionError("completed review was encoded again")):
            resumed = review.render_action(self.root, self.manifest, self.observations, FFMPEG, self.output)
        self.assertTrue(resumed["reused"])
        self.assertEqual(resumed["completion"], result["completion"])
        packages = [{"candidate_id": "fixture_one", "review": result},
                    {"candidate_id": "fixture_two", "review": result}]
        page = review.build_review_page(self.root, packages, self.output)
        text = (self.root/page["path"]).read_text()
        self.assertEqual(text.count("<video "), 2)
        self.assertEqual(text.count('aria-label="Playback speed"'), 2)
        self.assertIn("Human review is pending", text)
        self.assertEqual(review.build_review_page(self.root, packages, self.output), page)

    def test_failed_encoding_is_retained_without_completion(self):
        with patch("av.open", side_effect=RuntimeError("synthetic encoder failure")):
            with self.assertRaisesRegex(RuntimeError, "synthetic encoder failure"):
                review.render_action(self.root, self.manifest, self.observations, FFMPEG, self.output)
        failures = list(self.output.rglob("failed.json"))
        self.assertEqual(len(failures), 1)
        self.assertEqual(json.loads(failures[0].read_text())["status"], "failed_preserved")
        self.assertEqual(list(self.output.rglob("completion.json")), [])


if __name__ == "__main__":
    unittest.main()
