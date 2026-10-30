"""Actual accepted-record transport with fake model calls; no real inference."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np
from PIL import Image

from src.ball_tracking import nba_wasb_diagnostic as diagnostic
from src.ball_tracking.nba_reviewed_reference import load_accepted_references
from tests.test_nba_reviewed_reference import build_accepted_fixture

FFBIN = Path("C:/Users/Ryan/AppData/Local/Microsoft/WinGet/Packages/"
             "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0-full_build/bin")


class FakeAdapter:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail
        self.provenance = {"checkpoint_role":"adapted_basketball",
                           "checkpoint_path":"synthetic-adapted-weights",
                           "pretrained_checkpoint":{"path":"synthetic-original-weights"},
                           "fixture_only":True}

    def predict_triplet(self, images):
        self.calls.append([image.copy() for image in images])
        if self.fail:
            raise RuntimeError("synthetic interrupted model call")
        heatmaps = np.zeros((3, 288, 512), dtype=np.float32)
        heatmaps[:, 144, 256] = .9
        return {"heatmaps": heatmaps}


class NBADiagnosticTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="nba_wasb_fake_")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.acceptance, _, self.original, self.proposal = build_accepted_fixture(self.root)
        self.reference = load_accepted_references(self.acceptance, self.root)[0]
        for name, payload in (("checkpoint.pth", b"fake expanded checkpoint: never tensor-loaded"),
                              ("pretrained.pth", b"fake pretrained checkpoint: never tensor-loaded"),
                              ("training_config.json", b"{}"), ("training_manifest.json", b"{}"),
                              ("upstream/model.py", b"# synthetic upstream binding\n")):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        def bind(name):
            return {key: value for key, value in diagnostic.binding(self.root, self.root / name).items() if key != "bytes"}
        self.bind = bind
        completion = {"status": "completed", "completed_updates": 200,
                      "checkpoint": bind("checkpoint.pth"), "config": bind("training_config.json"),
                      "training_manifest": bind("training_manifest.json"),
                      "training_provenance": {"fixture": True}}
        (self.root / "completion.json").write_text(json.dumps(completion), encoding="utf-8")
        self.config = {
            "schema_version": diagnostic.SCHEMA, "diagnostic_id": "nba_synthetic_diagnostic",
            "accepted_references": bind("acceptance.json"), "checkpoint_completion": bind("completion.json"),
            "pretrained_checkpoint": bind("pretrained.pth"),
            "upstream_source": {"path": "upstream", "revision": diagnostic.SOURCE_REVISION},
            "output_root": "data/outputs/diagnostic", "inference": dict(diagnostic.POLICY),
            "scoring": {"localization_radius_px": 10},
            "rendering": {"fps": 6, "final_hold_seconds": 1, "ffmpeg": str(FFBIN / "ffmpeg.exe")
                          if (FFBIN / "ffmpeg.exe").is_file() else sys.executable},
        }
        self.config_path = self.root / "config.json"
        self.config_path.write_text(json.dumps(self.config), encoding="utf-8")
        for name, value in (("EXPANDED_SHA", bind("checkpoint.pth")["sha256"]),
                            ("CHECKPOINT_SHA256", bind("pretrained.pth")["sha256"]),
                            ("SOURCE_SHA256", {"model.py": bind("upstream/model.py")["sha256"]})):
            patcher = patch.object(diagnostic, name, value)
            patcher.start(); self.addCleanup(patcher.stop)
        self.approval = {
            "schema_version": "nba_wasb_diagnostic_approval/v0.1", "status": "approved", "approved_by": "Ryan",
            "approved_at_utc": "2026-10-18T00:00:00+00:00", "config": bind("config.json"),
            "scope": {"diagnostic_id": self.config["diagnostic_id"], "planned_unique_triplets": 1,
                      "training": False, "source_video_decode": False},
        }
        self.approval_path = self.root / "diagnostic_approval.json"
        self.approval_path.write_text(json.dumps(self.approval), encoding="utf-8")
        self.output = self.root / self.config["output_root"]

    def run_fake(self, adapter=None, render=False):
        adapter = adapter or FakeAdapter()
        result = diagnostic.run_diagnostic(self.root, self.config_path, self.approval_path,
                                           adapter_factory=lambda: adapter, render=render)
        return result, adapter

    def test_plan_reads_actual_producer_metadata_without_images_model_or_output(self):
        with patch.object(diagnostic.nba, "read_verified_png", side_effect=AssertionError("image read in plan")):
            config, references, completion, plan = diagnostic.load_plan(self.root, self.config_path)
        self.assertFalse(self.output.exists())
        self.assertFalse(plan["model_loaded"])
        self.assertEqual(plan["planned_unique_triplets"], 1)
        self.assertEqual(plan["windows"][0]["native_delta_ticks"], [1440, 1530])
        self.assertEqual([f["source_pts_ticks"] for f in references[0]["frames"]], [996362,997802,999332])
        self.assertEqual(references[0]["origin"], self.proposal["origin"])
        self.assertEqual(references[0]["human_review"]["status"], "accepted")
        self.assertEqual(plan['windows'][0]['temporal_contribution_counts'],[1,1,1])
        self.assertIn('aggregation_module_sha256',plan['inference_code'])

    def test_missing_or_changed_approval_refuses_before_model_or_output(self):
        factory = Mock(side_effect=AssertionError("Model construction before authorization"))
        for mode in ("absent", "changed_hash", "different_scope"):
            bad = copy.deepcopy(self.approval)
            path = self.approval_path
            if mode == "absent": path = None
            elif mode == "changed_hash": bad["config"]["sha256"] = "0" * 64
            else: bad["scope"]["planned_unique_triplets"] = 2
            self.approval_path.write_text(json.dumps(bad), encoding="utf-8")
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                diagnostic.run_diagnostic(self.root,self.config_path,path,adapter_factory=factory,render=False)
            self.assertFalse(self.output.exists())
        factory.assert_not_called()

    def test_actual_emitted_records_scoring_and_cached_resume_do_not_reinfer(self):
        original_bytes = (self.root / "draft.json").read_bytes()
        result, adapter = self.run_fake()
        self.assertEqual(len(adapter.calls), 1)
        self.assertEqual([int(image[0,0,0]) for image in adapter.calls[0]], [0,40,80])
        self.assertEqual(result["call_accounting"]["completed_unique_triplets"], 1)
        emitted = diagnostic.read_json(self.output/self.reference["candidate_id"]/"observations.json")
        self.assertEqual(emitted['reference_origin'],self.proposal['origin'])
        self.assertEqual(emitted['reference_human_review']['status'],'accepted')
        self.assertEqual(emitted['model_origin']['kind'],'wasb_model_inference')
        self.assertEqual(emitted['model_output_human_review'],'pending')
        self.assertNotIn('human_review',emitted)
        self.assertNotIn('origin',emitted)
        runtime=diagnostic.read_json(next(self.output.glob('run_attempts/*/model_loaded.json')))
        self.assertEqual(runtime['provenance'],adapter.provenance)
        self.assertEqual(runtime['provenance']['checkpoint_role'],'adapted_basketball')
        self.assertNotEqual(runtime['provenance']['checkpoint_path'],runtime['provenance']['pretrained_checkpoint']['path'])
        self.assertEqual([f["source_frame_index"] for f in emitted["frames"]], [660,661,662])
        self.assertEqual([f["source_pts_ticks"] for f in emitted["frames"]], [996362,997802,999332])
        self.assertEqual([f["temporal_contributions"] for f in emitted["frames"]], [1,1,1])
        for source, frame in zip(self.original["frames"], emitted["frames"]):
            self.assertEqual(source["png"], frame["source_png"])
        scored = diagnostic.score_reference(self.reference, emitted)
        self.assertEqual(scored["summary"]["matched"], 3)
        self.assertIsNone(scored["summary"]["hidden_alarm_rate"])
        self.assertEqual(scored["interior_three_contributions"]["frames"], 0)
        factory = Mock(side_effect=AssertionError("Completed cache was reinferred"))
        resumed = diagnostic.run_diagnostic(self.root,self.config_path,self.approval_path,adapter_factory=factory,render=False)
        self.assertEqual(resumed,result); factory.assert_not_called()
        self.assertEqual((self.root/"draft.json").read_bytes(),original_bytes)
        bad=copy.deepcopy(emitted);bad["frames"][1]["source_pts_ticks"]+=1
        with self.assertRaisesRegex(ValueError,"producer mapping"):
            diagnostic.score_reference(self.reference,bad)

    def test_unfinished_call_retry_preserves_consumption_and_completed_cache_corruption_refuses(self):
        with self.assertRaisesRegex(RuntimeError,"synthetic interrupted"):
            self.run_fake(FakeAdapter(fail=True))
        result, adapter=self.run_fake()
        self.assertEqual(result["call_accounting"]["model_call_starts"],2)
        self.assertEqual(result["call_accounting"]["failed_attempts"],1)
        self.assertEqual(result["call_accounting"]["completed_unique_triplets"],1)
        self.assertEqual(len(list(self.output.glob('*/triplets/attempts/*_started.json'))),2)
        cache=next(self.output.glob('*/triplets/triplet_*.npz'))
        with cache.open('ab') as handle:handle.write(b'corrupt binding, NPZ still readable')
        factory=Mock(side_effect=AssertionError('Corrupted completed cache reinferred'))
        with self.assertRaisesRegex(ValueError,'Existing evidence differs'):
            diagnostic.run_diagnostic(self.root,self.config_path,self.approval_path,adapter_factory=factory,render=False)
        factory.assert_not_called()

    def test_process_lock_refuses_parallel_work_and_releases_without_deleting_file(self):
        path=self.root/'process.lock'
        first=diagnostic.acquire_run_lock(path)
        try:
            with self.assertRaisesRegex(ValueError,'currently holds'):
                diagnostic.acquire_run_lock(path)
        finally:
            diagnostic.release_run_lock(first)
        self.assertTrue(path.is_file())
        # This is the same OS release performed when a process closes/exits.
        second=diagnostic.acquire_run_lock(path)
        diagnostic.release_run_lock(second)

    def test_five_captured_native_frames_overlap_and_cache_in_original_order(self):
        # Additional captured SAC producer PTS, continuing the fixture's 660-662.
        # Only synthetic pixels are added; this directly tests the inference helper.
        reference=copy.deepcopy(self.reference)
        for index,ticks,color in ((663,1000862,120),(664,1002302,160)):
            image=Image.new('RGB',(8,6),(color,30,60));path=self.root/f'source_{index:06d}.png';image.save(path)
            reference['frames'].append({'source_frame_index':index,'source_pts_ticks':ticks,
                'png':{'path':path.name,'sha256':diagnostic.digest(path),
                       'rgb_sha256':hashlib.sha256(image.tobytes()).hexdigest()}})
        class OverlapAdapter(FakeAdapter):
            def predict_triplet(self,images):
                self.calls.append([int(image[0,0,0]) for image in images])
                heatmaps=np.zeros((3,288,512),np.float32)
                heatmaps[:,144,256]=.6+.05*len(self.calls)
                return {'heatmaps':heatmaps}
        adapter=OverlapAdapter()
        config,_,_,plan=diagnostic.load_plan(self.root,self.config_path)
        observed=diagnostic.infer_reference(self.root,reference,config,plan,self.output,lambda:adapter)
        self.assertEqual(adapter.calls,[[0,40,80],[40,80,120],[80,120,160]])
        self.assertEqual([r['temporal_contributions'] for r in observed['frames']],[1,2,3,2,1])
        for frame,mass in zip(observed['frames'],(.65,.675,.7,.725,.75)):
            self.assertAlmostEqual(frame['native_score'],mass,places=5)
        factory=Mock(side_effect=AssertionError('Completed overlapping triplet reinferred'))
        replay=diagnostic.infer_reference(self.root,reference,config,plan,self.output,factory)
        self.assertEqual(replay,observed);factory.assert_not_called()

    def test_strict_threshold_and_largest_mass_selection_ignore_reference(self):
        class CompetingAdapter(FakeAdapter):
            def predict_triplet(self,images):
                heatmaps=np.zeros((3,288,512),np.float32)
                heatmaps[:,144,256]=.9
                heatmaps[:,100,100:102]=.8
                heatmaps[:,50,50]=.3  # Exactly threshold: must be excluded.
                return {'heatmaps':heatmaps}
        self.run_fake(CompetingAdapter())
        observed=diagnostic.read_json(self.output/self.reference['candidate_id']/'observations.json')
        for frame in observed['frames']:
            self.assertEqual(len(frame['candidates']),2)
            selected=next(c for c in frame['candidates'] if c['candidate_index']==frame['selected_candidate_index'])
            self.assertAlmostEqual(selected['native_score'],1.6,places=5)
            self.assertEqual(selected['component_pixels'],2)

    def test_raw_distance_scoring_uncertainty_does_not_change_match(self):
        self.run_fake()
        observations=diagnostic.read_json(self.output/self.reference['candidate_id']/'observations.json')
        reference=copy.deepcopy(self.reference)
        reference['source_video']['width_px']=1920;reference['source_video']['height_px']=1080
        for label in reference['annotations']:
            label['geometry']['center_xy_px']=[100.,100.]
            label['geometry']['uncertainty_radius_px']=9
        for frame,x in zip(observations['frames'],(110.,110.01,None)):
            frame['center_xy_px']=None if x is None else [x,100.]
            frame['candidates']=[] if x is None else [{'candidate_index':0,'center_x':x,'center_y':100.,'native_score':1.}]
        score=diagnostic.score_reference(reference,observations)
        self.assertEqual([r['outcome'] for r in score['frame_results']],['matched','wrong','missing'])
        self.assertEqual(score['summary']['false_positive_count'],1)
        self.assertEqual(score['summary']['false_negative_count'],2)
        self.assertAlmostEqual(score['frame_results'][1]['uncertainty_adjusted_error_px'],1.01)

    @unittest.skipUnless((FFBIN/'ffmpeg.exe').is_file(),'Local FFmpeg unavailable')
    def test_real_new_synthetic_render_final_hold_and_render_failure_resume(self):
        original_run=diagnostic.subprocess.run
        with patch.object(diagnostic.subprocess,'run',side_effect=RuntimeError('synthetic render interruption')):
            with self.assertRaisesRegex(RuntimeError,'synthetic render interruption'):
                self.run_fake(render=True)
        self.assertEqual(diagnostic.call_accounting(self.output)['model_call_starts'],1)
        factory=Mock(side_effect=AssertionError('Render retry reran model'))
        result=diagnostic.run_diagnostic(self.root,self.config_path,self.approval_path,adapter_factory=factory)
        factory.assert_not_called()
        receipt=diagnostic.read_json(self.root/result['candidates'][0]['review_completion']['path'])
        video=next(self.root/b['path'] for b in receipt['artifacts'] if b['path'].endswith('review.mp4'))
        metadata=json.loads(original_run([str(FFBIN/'ffprobe.exe'),'-v','error','-show_streams','-of','json',str(video)],capture_output=True,check=True).stdout)
        self.assertEqual(int(metadata['streams'][0]['nb_frames']),9)
        self.assertEqual(metadata['streams'][0]['avg_frame_rate'],'6/1')
        tail=self.root/'tail.png'
        original_run([str(FFBIN/'ffmpeg.exe'),'-hide_banner','-nostdin','-loglevel','error','-ss','1.333330','-i',str(video),'-frames:v','1',str(tail)],capture_output=True,check=True)
        final=next(self.root/b['path'] for b in receipt['artifacts'] if b['path'].endswith('review_000002.png'))
        with Image.open(tail) as image:actual=np.asarray(image.convert('RGB')).astype(np.int16)
        with Image.open(final) as image:expected=np.asarray(image).astype(np.int16)
        self.assertLess(np.abs(actual-expected).mean(),4)
        self.assertEqual(len(list(video.parents[1].glob('*/failed.json'))),1)
        self.assertEqual(result['call_accounting']['model_call_starts'],1)


if __name__=='__main__':
    unittest.main()
