"""Producer emission transport and synthetic five-clip display primitives."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from src.ball_tracking import nba_ball_distractor_review as render
from src.ball_tracking import nba_ball_distractor_policy as policy
from tests.test_nba_temporal_gap_continuous_review import nba_fixture, nfhs_fixture
from tests.test_nba_wasb_diagnostic import FFBIN


def policy_rows(source):
    result=[]
    for row in source["frames"]:
        if row["decision"]=="withheld":continue
        emission=policy.emission(row)
        gap=row["decision"]=="filled_saved_candidate"
        selected={field:None for field in policy.EMISSION_FIELDS} if gap else emission
        result.append({"candidate_id":source["candidate_id"],"source_frame_index":row["source_frame_index"],
            "source_pts_ticks":row["source_pts_ticks"],"saved_emission":emission,**selected,
            "logit":1. if gap else 0.,"policy_decision":"revoked_gap_fill" if gap else "retained_original",
            "removed":gap})
    return result


class BallDistractorReviewTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory(prefix="ball_veto_review_")
        self.addCleanup(folder.cleanup);self.root=Path(folder.name)
        self.source=nba_fixture(self.root);self.policy=policy_rows(self.source)

    def test_exact_producer_emission_transport_original_left_and_gap_dependency(self):
        with self.assertRaisesRegex(ValueError,"remain ignored"):
            render.render_all(self.root,"unused-selection","unused-policy","unused-ffmpeg",self.root/"outside")
        before=copy.deepcopy(self.source)
        mapped=render.map_source(self.source,self.policy)
        self.assertEqual(self.source,before)
        self.assertIsNone(self.source["frames"][1]["baseline_center_xy_px"])
        self.assertEqual(mapped["frames"][1]["baseline_center_xy_px"],[3.,2.])
        self.assertIsNone(mapped["frames"][1]["selected_center_xy_px"])
        self.assertEqual(mapped["frames"][0]["selected_center_xy_px"],[3.,2.])  # original zero survives
        episodes=render.changed_episodes(mapped["frames"])
        self.assertEqual(episodes[0]["source_range_inclusive"],[661,661])
        for field,value in (("source_pts_ticks",999),("selected_center_xy_px",[4.,2.])):
            bad=copy.deepcopy(self.policy);bad[0][field]=value
            with self.assertRaises(ValueError):render.map_source(self.source,bad)
        bad=copy.deepcopy(self.policy);bad[0]["saved_emission"]["selected_provenance_id"]=["wrong"]
        with self.assertRaisesRegex(ValueError,"saved emission"):render.map_source(self.source,bad)
        with self.assertRaisesRegex(ValueError,"Duplicate"):render.map_source(self.source,self.policy+[self.policy[0]])

    def test_protected_source_guard_custom_keys_and_swapped_pixels(self):
        source=nfhs_fixture(self.root);mapped=render.map_source(source,policy_rows(source))
        seen=[];decode=render.original.observation.decode_segment
        def guarded(root,poss,segment):
            seen.append(segment);return decode(root,poss,segment)
        with patch.object(render.original.observation,"decode_segment",side_effect=guarded):
            images=list(render.iter_images(self.root,mapped))
        self.assertEqual(seen,[[0,2],[6,8]])
        for i,(row,image) in enumerate(zip(mapped["frames"],images,strict=True)):
            pixels=np.asarray(image);signature=render.pixel_signature(image)
            self.assertEqual(render.verify_pixels(pixels,signature,row,i),[0.,0.])
            if row["decision"]=="withheld":self.assertEqual(int(pixels[96:776].max()),0)
        row=mapped["frames"][1];pixels=np.asarray(images[1]).copy();signature=render.pixel_signature(images[1])
        pixels[808:816,112*8:113*8]=255-pixels[808:816,112*8:113*8]
        with self.assertRaisesRegex(ValueError,"pair key"):render.verify_pixels(pixels,signature,row,1)
        with self.assertRaisesRegex(ValueError,"frame or veto"):render.verify_pixels(np.asarray(images[0]),signature,row,1)
        artificial=np.zeros((816,1280,3),np.uint8);artificial[:,:640]=250
        expected=render.pixel_signature(artificial);swapped=np.concatenate((artificial[:,640:],artificial[:,:640]),axis=1)
        self.assertGreater(float(np.abs(render.pixel_signature(swapped).astype(int)-expected).mean()),200)

    @unittest.skipUnless((FFBIN/"ffmpeg.exe").is_file(),"ffmpeg fixture unavailable")
    def test_encode_all_frames_native_pts_signatures_final_stills_and_resume(self):
        output=self.root/"data/outputs/veto_review"
        package=render.render_source(self.root,self.source,self.policy,FFBIN/"ffmpeg.exe",output,{"synthetic":True})
        manifest=json.loads((self.root/package["manifest"]["path"]).read_text())
        self.assertEqual([r["review_pts_ticks"] for r in manifest["frames"]],[0,1440,2970])
        self.assertEqual([r["duration_ticks"] for r in manifest["frames"]],[1440,1530,91530])
        verify=json.loads((self.root/package["verification"]["path"]).read_text())
        self.assertEqual(verify["decoded_frames"],3)
        self.assertEqual(verify["source_render_passes"],1)
        self.assertEqual(verify["suppressed_frames"],1)
        self.assertEqual(len(package["changed_episodes"]),1)
        self.assertEqual(len(package["changed_episodes"][0]["boundary_images"]),1)
        self.assertEqual(package["segment_final_frames"][0]["source_frame_index"],662)
        with patch.object(render,"iter_images",side_effect=AssertionError("must reuse completed review")):
            again=render.render_source(self.root,self.source,self.policy,FFBIN/"ffmpeg.exe",output,{"synthetic":True})
        self.assertEqual(again,package)


if __name__=="__main__":unittest.main()
