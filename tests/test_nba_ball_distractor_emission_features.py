"""Focused transport/resume checks; no real encoder or source-video decode."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from src.ball_tracking import nba_ball_distractor_emission_features as e
from src.ball_tracking import nba_appearance_feature_screen as screen

REPO = Path(__file__).resolve().parents[1]
SELECTION = "data/outputs/ball_tracking/nba/temporal_gap_continuous_v0_1/attempts/c4c9e3e80c5b4beaaa49147f0e0ad3b5/selection.json"
CACHE = "data/outputs/ball_tracking/nba/ball_distractor_training_v0_1/feature_manifest.json"


def fixture(root):
    """Real PNG and feature producers; tiny model is injected only at encode."""
    video = {"path": "source.mp4", "sha256": "a"*64, "width_px": 16, "height_px": 12}
    source = {"candidate_id": "tiny", "kind": "nba", "source_video": video, "protected_ranges": []}
    rows = []
    for index in range(2):
        png = screen._png(root, root/f"source_{index}.png", Image.new("RGB", (16, 12), (40+index, 80, 120)))
        rows.append({"candidate_id": "tiny", "source_frame_index": index, "source_pts_ticks": index*1500,
            "selected_center_xy_px": [1.25, 2.75], "source_frame": {"png": png},
            "selected_provenance_id": ["old", "tiny", index, "mean", None, None, 0],
            "decision": "preserved_original"})
    return [source], rows, {"fixture": "actual_verified_png_producer"}


class EmissionFeaturesTest(unittest.TestCase):
    def test_interrupted_feature_resume_and_bound_artifact_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); prepared = fixture(root)
            calls = []
            def fail_second(_model, chw):
                calls.append(chw.copy())
                if len(calls) == 2:
                    raise RuntimeError("synthetic interruption")
                return np.arange(1, 385, dtype=np.float32)
            with patch.object(e, "prepare_selection", return_value=prepared), patch.object(screen, "encode", side_effect=fail_second):
                with self.assertRaisesRegex(RuntimeError, "synthetic interruption"):
                    e.extract(root, {}, object(), {}, "out")
            failures = list((root/"out/attempts").glob("*/failure.json"))
            self.assertEqual(len(failures), 1)
            failed = json.loads(failures[0].read_text())
            self.assertEqual((failed["resources"]["encoder_attempts"], failed["resources"]["encoder_calls"]), (2, 1))
            with patch.object(e, "prepare_selection", return_value=prepared), patch.object(screen, "encode", return_value=np.arange(1,385,dtype=np.float32)) as encoder:
                result = e.extract(root, {}, object(), {}, "out")
                self.assertEqual(encoder.call_count, 1)
                self.assertEqual(result["resources"]["resumed_features"], 1)
                self.assertEqual(set(result["features_by_emission_id"]), {"tiny:0", "tiny:1"})
                crop = Image.open(root/next(iter(result["cache"].values()))["crop64"]["path"])
                self.assertEqual(crop.size, (64,64))
                self.assertEqual(crop.getpixel((0,0)), (0,0,0))
            with patch.object(e, "prepare_selection", return_value=prepared), patch.object(screen, "encode", side_effect=AssertionError("no model on resume")):
                resumed = e.extract(root, {}, None, {}, "out")
                self.assertEqual(resumed["manifest"], result["manifest"])
                self.assertEqual(resumed["resources"]["nba_png_reads"], 0)
                entry = next(iter(resumed["cache"].values()))
                path = root/entry["crop64"]["path"]; path.write_bytes(path.read_bytes()+b"tampered")
                with self.assertRaises(ValueError):
                    e.extract(root, {}, None, {}, "out")

    def test_source_pts_and_same_floor_cache_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); sources, rows, binding=fixture(root)
            with patch.object(e,"prepare_selection",return_value=(sources,rows,binding)), patch.object(screen,"encode",return_value=np.arange(1,385,dtype=np.float32)):
                result=e.extract(root,{},object(),{},"out")
            row=copy.deepcopy(rows[0]); row["selected_center_xy_px"]=[1.99,2.01]
            key=e.crop_key(row);entry=result["cache"][key]
            e._cached(root,entry,key,row,sources[0])
            wrong=copy.deepcopy(entry);wrong["source_pts_ticks"]+=1
            with self.assertRaisesRegex(ValueError,"source/PTS"):
                e._cached(root,wrong,key,row,sources[0])
            wrong=copy.deepcopy(entry);wrong["raw_cls_float32"][0]+=1
            with self.assertRaisesRegex(ValueError,"feature differs"):
                e._cached(root,wrong,key,row,sources[0])

    def test_nfhs_stream_skips_protected_span_and_rejects_bad_yield(self):
        source={"candidate_id":"nfhs","kind":"nfhs","protected_ranges":[[3,5]],
                "possession":{"visible_segments":[[0,2],[6,8]]}}
        rows=[{"source_frame_index":1},{"source_frame_index":7}]
        resources={"nfhs_requested_segments":[],"nfhs_decoded_frames":0}
        seen=[]
        def decode(_root,_possession,span):
            seen.append(span)
            for i in range(span[0],span[1]+1):
                yield i,np.zeros((2,3,3),dtype=np.uint8)
        with patch.object(e.nfhs,"decode_segment",side_effect=decode):
            frames=list(e._images(Path.cwd(),source,rows,resources))
        self.assertEqual([x[0] for x in frames],[1,7]);self.assertEqual(seen,[[0,2],[6,8]])
        self.assertEqual(resources["nfhs_decoded_frames"],6)
        with patch.object(e.nfhs,"decode_segment",side_effect=AssertionError("protected decode")):
            with self.assertRaisesRegex(ValueError,"protected"):
                list(e._images(Path.cwd(),source,[{"source_frame_index":4}],resources))
        def bad_decode(*_args):
            yield 3,np.zeros((2,3,3),dtype=np.uint8)
        with patch.object(e.nfhs,"decode_segment",side_effect=bad_decode):
            with self.assertRaisesRegex(ValueError,"outside permitted"):
                list(e._images(Path.cwd(),source,rows,resources))

    @unittest.skipUnless((REPO/SELECTION).is_file() and (REPO/CACHE).is_file(), "Authorized captured local records unavailable")
    def test_actual_captured_selection_and_training_cache_transport(self):
        sources,rows,_=e.prepare_selection(REPO,SELECTION)
        self.assertEqual(len(rows),3373)
        self.assertEqual(sum(r["decision"]=="filled_saved_candidate" for r in rows),14)
        cache={tuple(r["crop_key"]):r for r in json.loads((REPO/CACHE).read_text())["cache"]}
        source_map={s["candidate_id"]:s for s in sources};count=0
        for row in rows:
            key=e.crop_key(row)
            if key in cache:
                e._cached(REPO,cache[key],key,row,source_map[row["candidate_id"]]);count+=1
        self.assertEqual(count,148)


if __name__ == "__main__":
    unittest.main()
