"""Small source/overlay/timing transport checks, without model or real source runs."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import ImageDraw

from src.ball_tracking import nba_temporal_gap_review as render
from src.ball_tracking import nba_wasb_diagnostic as d
from tests.test_nba_annotations import build_fixture, observed
from tests.test_nba_wasb_diagnostic import FFBIN


class TemporalGapReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="nba_temporal_review_")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        _, source = build_fixture(self.root)
        self.entries = []
        for i, frame in enumerate(source["frames"]):
            original = {"state": "missing" if i == 1 else "observed",
                        "center_xy_px": None if i == 1 else [3., 2.]}
            selected = {"state": "observed", "center_xy_px": [3., 2.]}
            self.entries.append({"window_id": "window_a" if i < 2 else "window_b",
                "candidate_id": source["candidate_id"], "analysis_group": "sac_training_fit",
                "source_frame": frame, "source_video": source["source_video"],
                "annotation": observed(frame["source_frame_index"]),
                "original": original, "selected": selected,
                "decision_kind": "gap_fill" if i == 1 else "unchanged"})

    def test_actual_selector_records_join_and_reject_mismatched_source(self):
        from src.ball_tracking import nba_temporal_gap_selection as producer
        rows = []
        for i, entry in enumerate(self.entries):
            frame = entry["source_frame"]
            component = {"candidate_index": 0, "center_x": 3., "center_y": 2.,
                         "native_score": 1., "component_pixels": 1}
            original = {**entry["original"], "selected_candidate_index": None if i == 1 else 0,
                        "native_score": None if i == 1 else 1.}
            row = {**{k: entry[k] for k in ("candidate_id", "analysis_group", "source_frame", "source_video", "annotation")},
                "window_id": "producer_window", "source_frame_index": frame["source_frame_index"],
                "cohort": "synthetic", "is_control": False, "eligibility": "eligible",
                "old": {"original_selected": original, "pool": {"mean_record_count": 0 if i == 1 else 1,
                    "records": [{"component": component, "in_source_bounds": True,
                        "provenance_id": ["old", entry["candidate_id"], frame["source_frame_index"],
                                          "contributor" if i == 1 else "mean", 660 if i == 1 else None,
                                          1 if i == 1 else None, 0]}],
                    "contributor_planes": [{}]}}}
            row["old"]["original_score"] = producer.score_point(row, original["center_xy_px"],
                [] if i == 1 else [component])
            rows.append(row)
        report = {"frames": rows}
        selection = producer.attach_provenance(producer.select_all([[producer.projection(r) for r in rows]]), report)
        scored = producer.score(report, selection)
        joined = render.join_entries(rows, selection["frames"], scored)
        self.assertEqual([r["decision_kind"] for r in joined], ["unchanged", "gap_fill", "unchanged"])
        self.assertEqual(joined[1]["selected"]["center_xy_px"], [3., 2.])
        bad = copy.deepcopy(selection["frames"])
        bad[1]["source_pts_ticks"] += 1
        with self.assertRaisesRegex(ValueError, "source join"):
            render.join_entries(rows, bad, scored)
        bad = copy.deepcopy(scored)
        bad[1]["annotation"]["geometry"]["center_xy_px"] = [4., 2.]
        with self.assertRaisesRegex(ValueError, "reference differs"):
            render.join_entries(rows, selection["frames"], bad)

    def test_timeline_preserves_native_frames_and_holds_each_window(self):
        for fps in (30, 6):
            records = render.timeline(self.entries, fps)
            tick = 90000//fps
            self.assertEqual([r["review_pts_ticks"] for r in records], [0, tick, tick*2+90000])
            self.assertEqual([r["duration_ticks"] for r in records], [tick, tick+90000, tick+90000])
            self.assertEqual([r["window_start_reset"] for r in records], [True, False, True])
            self.assertEqual([r["source_pts_ticks"] for r in records], [996362, 997802, 999332])
        bad = copy.deepcopy(self.entries)
        bad[1]["source_frame"]["source_frame_index"] += 1
        with self.assertRaisesRegex(ValueError, "discontinuity"):
            render.timeline(bad, 30)
        bad = copy.deepcopy(self.entries)
        bad[1]["window_id"], bad[2]["window_id"] = "window_b", "window_a"
        with self.assertRaisesRegex(ValueError, "contiguous"):
            render.timeline(bad, 30)

    def test_overlay_uses_gap_titles_verified_source_and_native_binary_key(self):
        records = render.timeline(self.entries, 30)
        texts = []
        original_text = ImageDraw.ImageDraw.text
        def capture(draw, xy, text, *args, **kwargs):
            texts.append(text)
            return original_text(draw, xy, text, *args, **kwargs)
        with patch.object(ImageDraw.ImageDraw, "text", capture):
            image = render.overlay(self.root, self.entries[1], records[1], 30)
        self.assertEqual(image.size, (1280, 816))
        self.assertTrue(all(title in texts for title in render.TITLES))
        self.assertIn("GAP FILL", texts)
        self.assertIn("MISSING", texts)
        nfhs = {**self.entries[1], "analysis_group": "nfhs_development",
            "window_id": "possession_001_frames_0200_0224_challenge_evaluation_development_v0_2"}
        header, _ = render.header_text(nfhs, records[1], 6)
        self.assertIn("P001 | challenge | frames 200-224", header)
        self.assertLess(render.review.font(16).getlength(header), 1256)
        pixels = np.asarray(image)
        bits = "".join("1" if pixels[812, i*8+4].mean() > 127 else "0" for i in range(112))
        self.assertEqual(bits, render.review.key_bits(1, self.entries[1]["source_frame"]))
        bad = copy.deepcopy(self.entries[1])
        bad["source_frame"]["png"]["rgb_sha256"] = "0"*64
        with self.assertRaisesRegex(ValueError, "RGB hash"):
            render.overlay(self.root, bad, records[1], 30)

    @unittest.skipUnless((FFBIN/"ffmpeg.exe").is_file(), "FFmpeg required")
    def test_encoded_windows_all_frames_keys_timing_finals_and_resume(self):
        for fps in (30, 6):
            output = self.root/"data/outputs"/str(fps)
            first = render.render_group(self.root, "synthetic", self.entries, fps,
                str(FFBIN/"ffmpeg.exe"), output, {"fixture": True})
            verified = d.read_json(self.root/first["verification"]["path"])
            self.assertEqual(verified["decoded_frames"], 3)
            self.assertEqual(verified["duration_ticks"], 3*90000//fps+180000)
            self.assertEqual([r["source_frame_index"] for r in first["window_final_frames"]], [661, 662])
            with patch("av.open", side_effect=AssertionError("completed video repeated")):
                self.assertEqual(first, render.render_group(self.root, "synthetic", self.entries,
                    fps, str(FFBIN/"ffmpeg.exe"), output, {"fixture": True}))

    def test_encoder_failure_is_preserved_without_completion(self):
        output = self.root/"data/outputs/failed"
        with patch("av.open", side_effect=RuntimeError("synthetic encoder failure")):
            with self.assertRaisesRegex(RuntimeError, "synthetic encoder"):
                render.render_group(self.root, "synthetic", self.entries, 30, "ffmpeg",
                    output, {"fixture": True})
        self.assertEqual(len(list(output.rglob("failed.json"))), 1)
        self.assertFalse(list(output.rglob("completion.json")))


if __name__ == "__main__":
    unittest.main()
