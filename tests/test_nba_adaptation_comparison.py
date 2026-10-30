"""Producer-derived comparison fixtures; no existing images/caches or model runs."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np
from PIL import Image

from src.ball_tracking import nba_adaptation_comparison as comparison
from src.ball_tracking import nba_wasb_diagnostic as d
from tests.test_nba_annotations import build_fixture
from tests import test_nba_wasb_diagnostic as producer
from tests import test_nba_hard_example_diagnostic as score_producer


class AdaptationComparisonTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix="nba_adaptation_comparison_")
        self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
        _,draft=build_fixture(self.root)
        self.manifest={k:copy.deepcopy(draft[k]) for k in
                       ("candidate_id","game_id","approved_role","source_video","time_base","frames")}
        self.manifest["source_end_exclusive_pts_ticks"]=1000862
        ref={**self.manifest,"bindings":{},"origin":{"kind":"synthetic"},"human_review":{"status":"synthetic"}}
        self.old=d.infer_reference(self.root,ref,{"pretrained_checkpoint":{"sha256":"0"*64}},
            {"checkpoint":{"sha256":"1"*64},"inference_code":{"fixture":True}},self.root/"old",producer.FakeAdapter)
        limits=[self.manifest["frames"][0]["source_frame_index"],self.manifest["frames"][-1]["source_frame_index"]]
        for r in self.old["frames"]:r.update(segment_kind="live_action",segment_source_frame_range_inclusive=limits)
        self.context={"output":self.root/"data/outputs/new","config_binding":{"fixture":"config"},
                      "training_binding":{"fixture":"completion"},"training":{"checkpoint":{"sha256":"2"*64}}}

    def test_new_checkpoint_producer_caches_resume_without_reinference_or_old_changes(self):
        before={p:p.read_bytes() for p in (self.root/"old").rglob("*") if p.is_file()}
        adapter=producer.FakeAdapter()
        first=comparison.infer_manifest(self.root,self.manifest,self.old,self.context,lambda:adapter)
        self.assertEqual(len(adapter.calls),1)
        second=comparison.infer_manifest(self.root,self.manifest,self.old,self.context,
            Mock(side_effect=AssertionError("completed call repeated")))
        self.assertEqual(first,second)
        for a,b in zip(first["frames"],self.old["frames"]):
            for key in ("candidates","center_xy_px","temporal_contributions"):self.assertEqual(a[key],b[key])
        self.assertEqual(before,{p:p.read_bytes() for p in before})
        changed=copy.deepcopy(self.context);changed["training"]["checkpoint"]["sha256"]="3"*64
        with self.assertRaisesRegex(ValueError,"identity"):
            comparison.infer_manifest(self.root,self.manifest,self.old,changed,Mock())

    def test_failed_call_is_retained_then_resumed_without_replacing_attempt(self):
        with self.assertRaisesRegex(RuntimeError,"interrupted"):
            comparison.infer_manifest(self.root,self.manifest,self.old,self.context,lambda:producer.FakeAdapter(fail=True))
        failed=list(self.context["output"].rglob("*_failed.json"));self.assertEqual(len(failed),1)
        before=failed[0].read_bytes()
        comparison.infer_manifest(self.root,self.manifest,self.old,self.context,producer.FakeAdapter)
        self.assertEqual(failed[0].read_bytes(),before)
        self.assertEqual(len(list(self.context["output"].rglob("*_started.json"))),2)

    def test_bad_segment_coverage_refuses_before_adapter(self):
        old=copy.deepcopy(self.old)
        for r in old["frames"]:r["segment_source_frame_range_inclusive"]=[660,661]
        adapter=Mock(side_effect=AssertionError("model must not load"))
        with self.assertRaisesRegex(ValueError,"coverage"):
            comparison.infer_manifest(self.root,self.manifest,old,self.context,adapter)
        adapter.assert_not_called()

    def test_score_transitions_preserve_labels_source_joins_and_hidden_unknowns(self):
        fixture=score_producer.SavedDiagnosticTests();fixture.setUp()
        old=fixture.observations;new=copy.deepcopy(old)
        new["frames"][0]=fixture.emitted(fixture.frames[0],{(100,100):.9})
        old["frames"][1]=fixture.emitted(fixture.frames[1],{})
        comp=comparison.compare_reference(fixture.reference,old,new,"fixture","hard_example")
        self.assertEqual(comp["gained_match_frames"],[11]);self.assertEqual(comp["lost_match_frames"],[10])
        self.assertEqual(comp["outcome_transitions"]["matched -> wrong"],1)
        for key in ("source_pts_ticks","source_png"):
            bad=copy.deepcopy(new);bad["frames"][0][key]=None
            with self.assertRaisesRegex(ValueError,"mapping"):
                comparison.compare_reference(fixture.reference,old,bad,"fixture","hard_example")

    def test_gates_require_each_bound_and_never_claim_human_acceptance(self):
        det={"matched":208,"missing":21,"wrong":8,"hidden_alarm":13}
        nfhs={"matched":130,"missing":14,"wrong":1,"hidden_alarm":0}
        value=comparison.gates(det,nfhs,60)
        self.assertTrue(value["numerical_candidate_pass"]);self.assertFalse(value["accepted"])
        for metric,value in (("matched",207),("missing",22),("wrong",9),("hidden_alarm",14)):
            self.assertFalse(comparison.gates({**det,metric:value},nfhs,60)["numerical_candidate_pass"])
        self.assertFalse(comparison.gates(det,nfhs,59)["numerical_candidate_pass"])

    def test_nfhs_actual_decoder_bgr_contract_converts_to_verified_rgb(self):
        source={**self.manifest["source_video"],"fps":25.0}
        window={"window_id":"synthetic_nfhs","possession_id":"synthetic","source_video":source,
                "start_frame_index":0,"end_frame_index":2}
        bgr=np.full((source["height_px"],source["width_px"],3),(10,20,200),np.uint8)
        with patch.object(comparison,"verify_source_video_contract"),patch.object(comparison.wasb,"decode_window",return_value={i:bgr for i in range(3)}):
            manifest=comparison.prepare_nfhs(self.root,window,self.context["output"])
        with Image.open(self.root/manifest["frames"][0]["png"]["path"]) as image:
            self.assertEqual(image.getpixel((0,0)),(200,20,10))
        self.assertEqual([f["source_pts_ticks"] for f in manifest["frames"]],[0,3600,7200])
        with patch.object(comparison.wasb,"decode_window",side_effect=AssertionError("repeat source decode")):
            self.assertEqual(manifest,comparison.prepare_nfhs(self.root,window,self.context["output"]))
        with patch.object(comparison,"verify_source_video_contract"),patch.object(comparison.wasb,"decode_window",side_effect=RuntimeError("decode failed")):
            with self.assertRaisesRegex(RuntimeError,"decode failed"):
                comparison.prepare_nfhs(self.root,{**window,"window_id":"failed_decode"},self.context["output"])
        self.assertEqual(len(list((self.context["output"]/"failed_decode").rglob("failed.json"))),1)

    def test_nfhs_baseline_consumes_actual_calibration_point_component_producer(self):
        from src.ball_tracking import wasb_calibration
        window={"window_id":"fixture_nfhs","possession_id":"fixture","source_video":self.manifest["source_video"],
                "start_frame_index":660,"end_frame_index":662,"annotation_set_id":"fixture",
                "mean_heatmaps":{"path":"synthetic.npz"},"inference_identity":{"path":"synthetic.json"}}
        means=np.zeros((3,288,512),np.float32);means[:,144,256]=.9
        raw,_,components=wasb_calibration.point_runs_from_heatmaps(window,means,.3)
        bindings={}
        for name,payload in (("points",raw),("components",components)):
            path=self.context["output"]/(name+".json");d.write_once(path,payload);bindings[name]=d.binding(self.root,path)
        actual=comparison.baseline_nfhs(self.root,window,self.manifest,bindings)
        self.assertEqual([r["temporal_contributions"] for r in actual["frames"]],[1,1,1])
        for a,b in zip(actual["frames"],self.old["frames"]):
            self.assertEqual(a["center_xy_px"],b["center_xy_px"])
            self.assertEqual(a["candidates"],b["candidates"])

    @unittest.skipUnless((producer.FFBIN/"ffmpeg.exe").is_file(),"FFmpeg required")
    def test_paired_real_media_all_frames_slowed_pts_hold_and_resume(self):
        for fps in (30,6):
            output=self.context["output"]/str(fps)
            result=comparison.render_pair(self.root,self.manifest,self.old,self.old,{},fps,
                                           str(producer.FFBIN/"ffmpeg.exe"),output)
            verification=d.read_json(self.root/result["verification"]["path"])
            self.assertEqual(verification["decoded_frames"],3)
            self.assertEqual(verification["duration_ticks"],3*90000//fps+90000)
            self.assertEqual(verification["actual_final_source_frame_index"],662)
            with patch("av.open",side_effect=AssertionError("encoded again")):
                self.assertEqual(result,comparison.render_pair(self.root,self.manifest,self.old,self.old,{},fps,
                    str(producer.FFBIN/"ffmpeg.exe"),output))

    def test_failed_render_is_preserved_and_mismatched_source_refused(self):
        output=self.context["output"]/"review"
        with patch("av.open",side_effect=RuntimeError("synthetic encoder")):
            with self.assertRaisesRegex(RuntimeError,"synthetic encoder"):
                comparison.render_pair(self.root,self.manifest,self.old,self.old,{},30,"ffmpeg",output)
        self.assertEqual(len(list(output.rglob("failed.json"))),1)
        self.assertFalse(list(output.rglob("completion.json")))
        new=copy.deepcopy(self.old);new["frames"][0]["source_pts_ticks"]+=1
        with self.assertRaisesRegex(ValueError,"source join"):
            comparison.render_pair(self.root,self.manifest,self.old,new,{},30,"ffmpeg",output)


if __name__=="__main__":unittest.main()
