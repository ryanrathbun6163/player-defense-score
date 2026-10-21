"""Reference media consumes actual preparation output, never model predictions."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import uuid

import numpy as np
from PIL import Image

from src.ball_tracking import nba_gap_anchor_reference_review as render
from src.ball_tracking import nba_wasb_diagnostic as d
from tests.test_nba_gap_anchor_reference import prepared_fixture, write_json
from tests.test_nba_wasb_diagnostic import FFBIN


class GapAnchorReferenceReviewTests(unittest.TestCase):
    def setUp(self):
        repository = Path(__file__).resolve().parents[1]
        self.root = repository/"data/outputs/t/gap_anchor_reference_review_tests"/uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.fixture = prepared_fixture(self.root)
        for name in ("nba_gap_anchor_reference_review.py", "nba_action_review.py"):
            (self.root/"src/ball_tracking"/name).write_bytes((repository/"src/ball_tracking"/name).read_bytes())
        self.preparation = self.fixture["preparation_path"].relative_to(self.root).as_posix()
        self.proposal = self.fixture["proposal_path"].relative_to(self.root).as_posix()

    def inputs(self):
        prep, proposal, rows = render.load_inputs(self.root, self.preparation, self.proposal)
        return prep, proposal, rows, render.timeline_records(prep, rows)

    def test_actual_preparation_census_and_native_joins(self):
        prep, _, rows, records = self.inputs()
        self.assertEqual(len(records), 74)
        self.assertEqual(sum(r["annotation"] is not None for r in records), 34)
        self.assertEqual(sum(r["reference_origin"] == "new" for r in records), 27)
        self.assertEqual(sum(r["reference_origin"] == "existing" for r in records), 7)
        self.assertEqual(sum(r["context_final"] for r in records), 10)
        self.assertEqual(sum(r["duration_ticks"] for r in records), 2232000)
        for record, row in zip(records, rows, strict=True):
            self.assertEqual(record["source_pts_ticks"], row["frame"]["source_pts_ticks"])
            self.assertEqual(record["source_png"], row["frame"]["raw_png"])
            if row["frame"]["role"] == "context_only":
                self.assertIsNone(record["annotation"])
            elif row["frame"]["reference_origin"] == "existing":
                self.assertEqual(record["annotation"], row["frame"]["existing_reference"]["row"]["annotation"])
        self.assertTrue(all(":" in g["group_id"] for g in prep["groups"]))
        for group in prep["groups"]:
            self.assertEqual(len({tuple(r["crop_xyxy_source_px"]) for r in records if r["group_id"] == group["group_id"]}), 1)

    def test_reference_points_both_panels_unknown_and_context_unmarked(self):
        prep, _, rows, records = self.inputs()
        selected = [next(i for i, r in enumerate(records) if r["reference_origin"] == origin)
                    for origin in (None, "new", "existing")]
        images = list(render.rendered_images(self.root, [rows[i] for i in selected], [records[i] for i in selected], len(prep["groups"])))
        # Synthetic source colors contain no cyan. Inspect image regions, excluding text and keys.
        for image in images[:2]:
            pixels = np.asarray(image)[115:555]
            self.assertEqual(int(((pixels[:, :, 0] < 30)&(pixels[:, :, 1] > 225)&(pixels[:, :, 2] > 225)).sum()), 0)
        # Accepted fixture center [20,20] on 64x40 source scales to both 620x387 panes.
        pixels = np.asarray(images[-1])
        for x in (10+20*620/64, 650+20*620/64):
            y = 115+(440-387)//2+20*387/40
            patch_pixels = pixels[round(y)-3:round(y)+4, round(x)-3:round(x)+4]
            self.assertGreater(int(((patch_pixels[:, :, 0] < 30)&(patch_pixels[:, :, 1] > 225)&(patch_pixels[:, :, 2] > 225)).sum()), 5)
        altered = copy.deepcopy(records[selected[-1]]); altered["annotation"]["geometry"]["center_xy_px"][0] += 1
        self.assertNotEqual(render.frame_bits(altered), render.frame_bits(records[selected[-1]]))
        erased = pixels.copy()
        region = erased[115:555]
        region[(region[:, :, 0] < 30)&(region[:, :, 1] > 225)&(region[:, :, 2] > 225)] = [54, 30, 70]
        with self.assertRaisesRegex(ValueError, "marker"):
            render.verify_pixels(erased, images[-1], records[selected[-1]])

    def test_consumer_rejects_changed_reference_and_wrong_preparation(self):
        changed = copy.deepcopy(self.fixture["proposal"])
        changed["existing_controls"][0]["existing_reference"]["row"]["annotation"]["notes"] = "changed"
        write_json(self.root, "data/outputs/changed.json", changed)
        with self.assertRaises(ValueError):
            render.load_inputs(self.root, self.preparation, "data/outputs/changed.json")
        write_json(self.root, "data/outputs/other.json", self.fixture["preparation"])
        with self.assertRaisesRegex(ValueError, "Requested preparation"):
            render.load_inputs(self.root, "data/outputs/other.json", self.proposal)

    def test_final_hold_and_encoded_source_key_are_checked(self):
        prep, _, rows, records = self.inputs()
        probe = {"streams": [{"time_base": "1/90000", "duration_ts": 2232000, "nb_frames": 74,
                              "width": render.WIDTH, "height": render.HEIGHT}],
                 "frames": [{"best_effort_timestamp": r["review_pts_ticks"], "duration": r["duration_ticks"]} for r in records]}
        self.assertEqual(render.verify_probe(probe, records), 2232000)
        probe["frames"][-1]["duration"] = 18000
        with self.assertRaisesRegex(ValueError, "timing"):
            render.verify_probe(probe, records)
        image = next(render.rendered_images(self.root, rows[:1], records[:1], len(prep["groups"])))
        pixels = np.asarray(image).copy(); render.verify_pixels(pixels, image, records[0])
        pixels[808:816, :8] = 255-pixels[808:816, :8]
        with self.assertRaisesRegex(ValueError, "key"):
            render.verify_pixels(pixels, image, records[0])

    @unittest.skipUnless((FFBIN/"ffmpeg.exe").is_file(), "FFmpeg required")
    def test_full_emitted_preparation_encode_verify_resume_and_tamper(self):
        args = (self.root, self.preparation, self.proposal, "data/outputs/media", str(FFBIN/"ffmpeg.exe"))
        result = render.render(*args)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["human_review"], "pending")
        self.assertEqual(len(result["target_stills"]), 34)
        self.assertEqual(len(result["context_finals"]), 10)
        verification = d.read_json(self.root/result["artifacts"]["verification"]["path"])
        self.assertEqual(verification["decoded_frames"], 74)
        self.assertEqual(verification["duration_ticks"], 2232000)
        self.assertTrue(verification["all_paired_pixels_verified"])
        self.assertEqual(verification["actual_final_frame"], self.fixture["preparation"]["frames"][-1]["source_frame_index"])
        guide = (self.root/result["artifacts"]["guide"]["path"]).read_text(encoding="utf-8")
        self.assertEqual(guide.count("<figure>"), 34)
        self.assertIn("40 surrounding context frames", guide)
        with patch.object(render, "rendered_images", side_effect=AssertionError("no repeated encode")):
            self.assertEqual(render.render(*args), result)
        final = self.root/result["artifacts"]["final_frame"]["path"]
        final.write_bytes(final.read_bytes()+b"tampered")
        with self.assertRaisesRegex(ValueError, "binding"):
            render.render(*args)


if __name__ == "__main__":
    unittest.main()
