"""Appearance review consumes the actual preparation producer and draft schema."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import uuid

import numpy as np
from PIL import Image

from src.ball_tracking import nba_appearance_reference_review as render
from src.ball_tracking import nba_wasb_diagnostic as d
from tests.test_nba_appearance_reference import prepared_fixture
from tests.test_nba_wasb_diagnostic import FFBIN


class AppearanceReferenceReviewTests(unittest.TestCase):
    def setUp(self):
        repository = Path(__file__).resolve().parents[1]
        self.root = repository/"data/outputs/t/appearance_reference_review_tests"/uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.fixture = prepared_fixture(self.root)
        for name in ("nba_appearance_reference_review.py", "nba_action_review.py", "nba_gap_anchor_reference_review.py", "nba_annotations.py"):
            path = self.root/"src/ball_tracking"/name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((repository/"src/ball_tracking"/name).read_bytes())
        self.preparation = self.fixture["preparation_path"].relative_to(self.root).as_posix()
        self.proposal = self.fixture["proposal_path"].relative_to(self.root).as_posix()

    def inputs(self, with_proposal=True):
        prep, proposal = render.inputs(self.root, self.preparation, self.proposal if with_proposal else None)
        return prep, proposal, render.records(prep, proposal)

    def test_producer_transport_keeps_native_contexts_all_objects_and_target_only_classes(self):
        prep, proposal, rows = self.inputs()
        groups = len(prep["groups"])
        self.assertEqual(len(rows), 5*groups)
        self.assertEqual(sum(r["target"] for r in rows), groups)
        self.assertEqual(sum(r["context_final"] for r in rows), groups)
        self.assertEqual(sum(r["duration_ticks"] for r in rows), 288000*groups)
        labels = {r["candidate_key"]: r for r in proposal["rows"]}
        originals = {c["candidate_key"]: c for c in prep["candidates"]}
        seen = []
        for row, frame in zip(rows, prep["frames"], strict=True):
            self.assertEqual((row["continuous_source_id"], row["source_frame_index"], row["source_pts_ticks"], row["source_png"]),
                             (frame["continuous_source_id"], frame["source_frame_index"], frame["source_pts_ticks"], frame["raw_png"]))
            self.assertEqual(row["duration_ticks"], 126000 if row["target"] else 108000 if row["context_final"] else 18000)
            for candidate in row["candidates"]:
                original = originals[candidate["candidate_key"]]
                self.assertEqual(candidate["center_xy_px"], original["center_xy_px"])
                self.assertEqual(candidate["label"], labels[candidate["candidate_key"]] if row["target"] else None)
                self.assertNotIn("component", candidate)
                self.assertNotIn("confidence", candidate)
                if row["target"]: seen.append(candidate["candidate_key"])
        self.assertEqual(seen, [c["candidate_key"] for c in prep["candidates"]])
        for group in prep["groups"]:
            contexts = [r for r in rows if r["group_id"] == group["group_id"]]
            self.assertEqual(len({json.dumps([c["crop_xyxy"] for c in r["candidates"]]) for r in contexts}), 1)

    def test_source_sheets_are_unmarked_paired_pixels_resume_and_tamper_checked(self):
        prep, _, rows = self.inputs(False)
        args = (self.root, self.preparation, "data/outputs/source_sheets")
        result = render.build_source_sheets(*args)
        self.assertEqual(len(result["stills"]), len(prep["groups"]))
        manifest = d.read_json(self.root/result["artifacts"]["manifest"]["path"])
        self.assertFalse(manifest["object_classes_displayed"])
        self.assertFalse(manifest["markers_displayed"])
        self.assertTrue(all(c["label"] is None for r in manifest["frames"] for c in r["candidates"]))
        # Independently reproduce exact crop pixels at all five times, without overlay code.
        first = result["stills"][0]
        with Image.open(self.root/first["image"]["path"]) as sheet:
            self.assertEqual(sheet.size, (1280, 2100))
            for index, row in enumerate(rows[:5]):
                source = render.source_image(self.root, row)
                for j, candidate in enumerate(row["candidates"]):
                    expected = source.crop(candidate["crop_xyxy"]).resize((196, 196), Image.Resampling.NEAREST)
                    actual = sheet.crop((650+206*j, 166+404*index, 846+206*j, 362+404*index))
                    self.assertEqual(actual.tobytes(), expected.tobytes())
        with patch.object(render, "source_image", side_effect=AssertionError("resume must not rerender")):
            self.assertEqual(render.build_source_sheets(*args), result)
        path = self.root/first["image"]["path"]; path.write_bytes(path.read_bytes()+b"tampered")
        with self.assertRaisesRegex(ValueError, "Bound file changed"):
            render.build_source_sheets(*args)

    def test_classes_keys_and_local_candidate_markers_are_verified(self):
        prep, _, rows = self.inputs()
        target = next(r for r in rows if r["target"])
        image, markers = render.render_frame(render.source_image(self.root, target), target, len(prep["groups"]))
        self.assertEqual(len(markers), 2*len(target["candidates"]))
        pixels = np.asarray(image).copy(); render.verify_pixels(pixels, image, markers, target)
        altered = copy.deepcopy(target); altered["candidates"][0]["label"]["classification"] = "changed"
        self.assertNotEqual(render.key_bits(altered), render.key_bits(target))
        for row in (rows[0], rows[4]):
            _, context_markers = render.render_frame(render.source_image(self.root, row), row, len(prep["groups"]))
            self.assertEqual(context_markers, [])
        erased = pixels.copy()
        # Erase exact orange cross pixels only; global panel MAE remains tiny.
        orange = (erased[:,:,0]==255)&(erased[:,:,1]==179)&(erased[:,:,2]==71)
        erased[orange] = [15,20,29]
        with self.assertRaisesRegex(ValueError, "marker"):
            render.verify_pixels(erased, image, markers, target)
        pixels[808:816,:8] = 255-pixels[808:816,:8]
        with self.assertRaisesRegex(ValueError, "key"):
            render.verify_pixels(pixels, image, markers, target)

    def test_exact_native_display_timing_and_failure_preservation(self):
        _, _, rows = self.inputs()
        total = sum(r["duration_ticks"] for r in rows)
        probe = {"streams":[{"time_base":"1/90000", "duration_ts":total,"nb_frames":len(rows),"width":1280,"height":816}],
                 "frames":[{"best_effort_timestamp":r["review_pts_ticks"],"duration":r["duration_ticks"]} for r in rows]}
        self.assertEqual(render.timing.verify_probe(probe, rows), total)
        probe["frames"][-1]["duration"] = 18000
        with self.assertRaisesRegex(ValueError,"timing"):
            render.timing.verify_probe(probe, rows)
        with patch.object(render,"source_image",side_effect=RuntimeError("synthetic interruption")):
            with self.assertRaisesRegex(RuntimeError,"synthetic interruption"):
                render.build_source_sheets(self.root,self.preparation,"data/outputs/failed_sheets")
        attempts = list((self.root/"data/outputs/failed_sheets/attempts").iterdir())
        self.assertEqual(len(attempts),1)
        self.assertEqual(d.read_json(attempts[0]/"failed.json")["error"],"synthetic interruption")
        self.assertFalse((self.root/"data/outputs/failed_sheets/completion.json").exists())
        result = render.build_source_sheets(self.root,self.preparation,"data/outputs/failed_sheets")
        self.assertEqual(result["status"],"completed")
        self.assertEqual(len(list((self.root/"data/outputs/failed_sheets/attempts").iterdir())),2)

    @unittest.skipUnless((FFBIN/"ffmpeg.exe").is_file(),"FFmpeg required")
    def test_actual_emitted_records_encode_all_frames_holds_and_final_then_resume(self):
        prep, _, rows = self.inputs()
        args = (self.root,self.preparation,self.proposal,"data/outputs/media",str(FFBIN/"ffmpeg.exe"))
        result = render.render(*args)
        self.assertEqual((result["status"],result["human_review"]),("completed","pending"))
        self.assertEqual(len(result["stills"]),2*len(prep["groups"]))
        verification = d.read_json(self.root/result["artifacts"]["verification"]["path"])
        self.assertEqual(verification["decoded_frames"],len(rows))
        self.assertEqual(verification["duration_ticks"],288000*len(prep["groups"]))
        self.assertTrue(verification["all_keys_pixels_and_markers_verified"])
        guide = (self.root/result["artifacts"]["guide"]["path"]).read_text(encoding="utf-8")
        self.assertEqual(guide.count("<figure>"),2*len(prep["groups"]))
        self.assertIn("AI object proposals await human acceptance",guide)
        with Image.open(self.root/result["artifacts"]["actual_final"]["path"]) as final:
            expected, markers = render.render_frame(render.source_image(self.root,rows[-1]),rows[-1],len(prep["groups"]))
            render.verify_pixels(np.asarray(final),expected,markers,rows[-1])
        with patch.object(render,"source_image",side_effect=AssertionError("must not rerender")):
            self.assertEqual(render.render(*args),result)
        final_path = self.root/result["artifacts"]["actual_final"]["path"]
        final_path.write_bytes(final_path.read_bytes()+b"tampered")
        with self.assertRaisesRegex(ValueError,"Bound file changed"):
            render.render(*args)


if __name__ == "__main__":
    unittest.main()
