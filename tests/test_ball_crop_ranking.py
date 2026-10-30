"""Synthetic ranking, provenance, resume, parity, and complete-review tests."""
import copy
import hashlib
import json
import math
import random
import tempfile
import unittest
from contextlib import ExitStack
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

import numpy as np

from src.ball_tracking import crop_ranking_experiment as experiment
from src.ball_tracking import crop_ranking_evaluation as evaluation
from src.ball_tracking import crop_ranking_review as review
from src.ball_tracking import tiled_experiment
from src.ball_tracking.annotations import load_annotations
from src.ball_tracking.crop_ranking import ARMS, RankingConfig, experiment_grid, rank_candidates, rank_history, validate_observations
from src.ball_tracking.development_experiments import canonical_sha256, read_json, sha256_file
from src.ball_tracking.temporal_experiment import file_binding, load_inputs, spec_digest
from src.ball_tracking.tiled_candidates import candidate_run, crop_views, make_frame, make_output
from src.ball_tracking.tiled_evaluation import score_one
from test_ball_annotation_foundation import not_visible_frame, observed_frame, parse_reviewed_annotations
from test_ball_detection_visual_review import write_json
from test_ball_temporal_association import fixture
from test_ball_tiled_comparison import ROOT, crop_result, setup_manifest

COMMIT = "f" * 40


def config(arm="recent_history_tight", threshold=.2):
    return next(c for c in experiment_grid() if c.arm == arm and c.confidence_threshold == threshold)


def run_fixture(points,labels=None):
    ordered = [sorted(frame,key=lambda p:(-p[2],p[0],p[1])) for frame in points]
    return fixture(ordered,labels)


def exhaustive(frames, c, diagonal):
    """Enumerate every small-graph path independently of the production DP."""
    paths = []
    for frame in frames:
        for candidate in frame.detections[:20]:
            if candidate.confidence < c.confidence_threshold:
                continue
            ref = (frame.frame_index,candidate.candidate_index)
            added = [(candidate.confidence,(ref,),candidate)]
            for score,path,old in paths:
                delta = frame.frame_index-path[-1][0]
                distance = math.dist(old.center_xy_px,candidate.center_xy_px)
                limit = c.step_limit*diagonal*delta
                if 1 <= delta <= 3 and distance <= limit:
                    added.append((score+candidate.confidence-.25*(delta-1)-.25*(distance/limit)**2,(*path,ref),candidate))
            paths.extend(added)
    t = frames[-1].frame_index
    per_endpoint = {}
    for score,path,candidate in paths:
        ref = path[-1]
        old = per_endpoint.get(ref)
        if old is None or (-score,path) < (-old[0],old[1]):
            per_endpoint[ref] = (score,path,candidate)
    competing = [(0.0,None,(),None)]
    for ref,(score,path,candidate) in per_endpoint.items():
        if t-ref[0] <= 2:
            competing.append((score-.25*(t-ref[0]),ref,path,candidate.confidence))
    competing.sort(key=lambda v:(-v[0],0 if v[1] is None else 1,-v[1][0] if v[1] else 0,
                                  -v[3] if v[1] else 0,v[1][1] if v[1] else 0,v[2]))
    return per_endpoint,competing[0]


def bind_manifest(root,payload):
    proposal_path = root/"configs/ball_tracking/proposals/synthetic_ranking.json"
    write_json(proposal_path,payload)
    manifest = {"schema_version":"ball_crop_candidate_ranking_experiment/v0.1","experiment_id":experiment.EXPERIMENT_ID,
                "proposal":file_binding(root,proposal_path),"output_root":experiment.OUTPUT_ROOT,"authorization":None,
                "selected_operating_point":None,"quality_gate":None}
    auth = {"schema_version":"ball_crop_candidate_ranking_approval/v0.1","experiment_spec_sha256":spec_digest(manifest),
            "proposal":manifest["proposal"],"approved_by":"ryan","statement":"Synthetic approval only",
            "recorded_at_utc":"2026-10-01T00:00:00Z","timestamp_semantics":"Synthetic test fixture",
            "scope":"saved_six_development_crop_windows_all_45_declared_variants","git_mutations_authorized":False}
    auth_path = root/"configs/ball_tracking/reviews/synthetic_ranking_approval.json"
    write_json(auth_path,auth)
    manifest["authorization"] = file_binding(root,auth_path)
    path = root/"configs/ball_tracking/crop_ranking_experiments/synthetic.json"
    write_json(path,manifest)
    return path,manifest


def ranking_setup(root):
    tiled_path,tiled_m,tiled_p = setup_manifest(root)
    _,_,temporal,baseline = tiled_experiment.load_manifest(root,tiled_path)
    raws = load_inputs(root,temporal)
    model = tiled_experiment.build_model_provenance(baseline.detector,code_commit=experiment.EXECUTION_COMMIT,runtime_device="cuda:0 | synthetic")
    pools = {purpose:[] for purpose in ("representative_evaluation","challenge_evaluation")}
    candidate_bindings = []
    for w,raw,label in zip(tiled_p["windows"],raws,tiled_p["scoring_labels"]):
        frames = []
        for offset,f in enumerate(raw.frames):
            views = [crop_result(v) for v in crop_views()]
            # Saved synthetic predictions are independent of label reads.
            points = [(82.25+2*offset,72.5+offset,.8),(300+offset,300,.7)]
            if offset == 4:
                points = [(500,400,.95),*points]
            views[0] = crop_result(crop_views()[0],points)
            frames.append(make_frame(f.frame_index,views,raw.source_video,model))
        value = make_output(tiled_experiment.make_header(tiled_m,w,model),frames)
        output = root/tiled_experiment.OUTPUT_ROOT/w["window_id"]/"candidates.json"
        write_json(output,value)
        candidate_bindings.append(file_binding(root,output))
        labels = load_annotations(root/label["annotation"]["path"])
        run = candidate_run(raw,value)
        for arm,selector,threshold,radius in __import__("src.ball_tracking.tiled_evaluation",fromlist=["configurations"]).configurations():
            chosen = raw if arm == "saved_whole_frame" else run
            pools[w["purpose"]].append(score_one(labels,chosen,arm,selector,threshold,radius,value["content_sha256"] if arm == "four_crop_union" else None,experiment.EXECUTION_COMMIT))
    saved_bindings = []
    for purpose,reports in pools.items():
        path = root/tiled_experiment.OUTPUT_ROOT/"evaluation"/f"{purpose}.json"
        write_json(path,{"evaluation_reports":reports})
        saved_bindings.append(file_binding(root,path))
    proposal = read_json(ROOT/"configs/ball_tracking/proposals/rfdetr_medium_crop_candidate_ranking_v0_1.json")
    proposal["crop_experiment_manifest"] = file_binding(root,tiled_path)
    proposal["windows"] = [{**w,"crop_candidates":b} for w,b in zip(tiled_p["windows"],candidate_bindings)]
    proposal["scoring_labels"] = tiled_p["scoring_labels"]
    proposal["frozen_detector_contract_source"] = tiled_p["frozen_detector_contract_source"]
    proposal["saved_crop_scoring_reports"] = saved_bindings
    for key in ("design","rationale"):
        doc = root/proposal[key]["path"]
        doc.parent.mkdir(parents=True,exist_ok=True)
        doc.write_text("Synthetic ranking document only.\n")
        proposal[key] = file_binding(root,doc)
    record_path = root/"data/outputs/ball_tracking/tiled_execution/synthetic/execution_record.json"
    write_json(record_path,{"synthetic":True})
    proposal["crop_execution_record"] = file_binding(root,record_path)
    receipt_path = root/proposal["crop_review_receipt"]["path"]
    write_json(receipt_path,{"human_visual_review":{"status":"completed","reviewer_id":"ryan"},
                            "bound_evidence":{"experiment_manifest":proposal["crop_experiment_manifest"],
                                              "execution_commit":experiment.EXECUTION_COMMIT,
                                              "execution_record":proposal["crop_execution_record"],"scoring_reports":saved_bindings}})
    proposal["crop_review_receipt"] = file_binding(root,receipt_path)
    path,m = bind_manifest(root,proposal)
    return path,m,proposal


def execution_patches(stack):
    stack.enter_context(patch.object(experiment,"clean_commit",return_value=COMMIT))
    stack.enter_context(patch.object(experiment,"git",return_value=COMMIT))
    stack.enter_context(patch.object(experiment,"_tracked"))
    stack.enter_context(patch.object(experiment.subprocess,"run",return_value=type("Result",(),{"returncode":0})()))


class RankingTests(unittest.TestCase):
    def test_grid_and_invalid_settings(self):
        self.assertEqual(len(experiment_grid()),45)
        self.assertEqual(len({c.variant_id for c in experiment_grid()}),45)
        for args in [("unknown",.2),("crop_raw",True),("crop_raw",.21),("crop_top_twenty",.2,19),("recent_history_tight",.2,20,.03)]:
            with self.subTest(args=args),self.assertRaises(ValueError):
                RankingConfig(*args)

    def test_exact_dp_matches_exhaustive_graphs(self):
        rng = random.Random(318)
        for arm in ARMS[3:]:
            for _ in range(20):
                points = [[(100+rng.randrange(0,45),100+rng.randrange(0,45),rng.choice([.2,.5,.8])) for _ in range(rng.randrange(0,4))] for _ in range(5)]
                _,run = run_fixture(points)
                diagonal = math.hypot(run.source_video.width_px,run.source_video.height_px)
                expected,winner = exhaustive(run.frames,config(arm),diagonal)
                value = rank_history(run.frames,config(arm),diagonal)
                self.assertEqual((value["winner"]["score"],tuple(value["winner"]["endpoint"]) if value["winner"]["endpoint"] else None,
                                  tuple(tuple(x) for x in value["winner"]["path"])),winner[:3])
                for node in value["best_path_per_endpoint"]:
                    score,path,_ = expected[tuple(node["endpoint"])]
                    self.assertEqual((node["score"],tuple(tuple(x) for x in node["path"])),(score,path))

    def test_history_recovers_lower_confidence_candidate(self):
        _,run = run_fixture([[(100,100,.8)],[(101,100,.8)],[(500,400,.95),(102,100,.8)]])
        top = rank_candidates(run,config("crop_top_one"),COMMIT)
        value = rank_candidates(run,config(),COMMIT)
        self.assertEqual(top["frames"][-1]["emitted_candidate_indices"],[0])
        self.assertEqual(value["frames"][-1]["emitted_candidate_indices"],[1])

    def test_stable_clutter_remains_an_explicit_failure(self):
        _,run = run_fixture([[(400,400,.9),(100+i,100,.8)] for i in range(5)])
        value = rank_candidates(run,config(),COMMIT)
        self.assertEqual(value["frames"][-1]["emitted_candidate_indices"],[0])

    def test_gap_has_no_extrapolated_coordinate_and_expires(self):
        _,run = run_fixture([[(100,100,.9)],[(101,100,.9)],[],[],[],[(104,100,.8)]])
        value = rank_candidates(run,config(),COMMIT)
        self.assertEqual([f["emitted_candidate_indices"] for f in value["frames"]],[ [0],[0],[],[],[],[0] ])
        self.assertEqual(value["frames"][2]["decision_reason"],"earlier_endpoint_no_current_observation")
        self.assertIsNone(value["frames"][4]["ranking"]["winner"]["endpoint"])

    def test_gap_edge_and_wide_link_are_distinct(self):
        _,run = run_fixture([[(100,100,.9)],[],[],[(105,100,.8)]])
        value = rank_candidates(run,config(),COMMIT)
        self.assertTrue(any(e["elapsed_frames"]==3 for e in value["frames"][-1]["ranking"]["eligible_edges"]))
        _,fast = run_fixture([[(100,100,.9)],[(150,100,.8)]])
        tight = rank_candidates(fast,config(),COMMIT)["frames"][-1]["ranking"]
        wide = rank_candidates(fast,config("recent_history_wide"),COMMIT)["frames"][-1]["ranking"]
        self.assertFalse(tight["eligible_edges"])
        self.assertTrue(wide["eligible_edges"])

    def test_cap_and_duplicates_preserve_original_indices(self):
        points = [(400+i,400,.9-i*.001) for i in range(21)]
        _,run = run_fixture([points])
        value = rank_candidates(run,config("crop_top_twenty"),COMMIT)
        self.assertEqual(value["frames"][0]["emitted_candidate_indices"],list(range(20)))
        self.assertEqual(value["frames"][0]["candidate_decisions"][-1]["disposition"],"outside_top_twenty")
        _,duplicates = run_fixture([[(100,100,.8),(100,100,.8)]])
        self.assertEqual(rank_candidates(duplicates,config("crop_raw"),COMMIT)["frames"][0]["emitted_candidate_indices"],[0,1])
        self.assertEqual(rank_candidates(duplicates,config(),COMMIT)["frames"][0]["emitted_candidate_indices"],[0])

    def test_threshold_inclusive_and_explicit_empty(self):
        _,run = run_fixture([[(100,100,.2),(200,200,.15)],[]])
        value = rank_candidates(run,config(),COMMIT)
        self.assertEqual(value["frames"][0]["emitted_candidate_indices"],[0])
        self.assertEqual(value["frames"][0]["candidate_decisions"][1]["disposition"],"below_threshold")
        self.assertEqual(value["frames"][1]["output_state"],"no_accepted_observation")

    def test_empty_wins_zero_score_tie(self):
        _,run = run_fixture([[(100,100,.25)],[]])
        value = rank_candidates(run,config(),COMMIT)
        endpoints = value["frames"][-1]["ranking"]["competing_endpoints"]
        self.assertEqual([e["score"] for e in endpoints],[0.0,0.0])
        self.assertIsNone(value["frames"][-1]["ranking"]["winner"]["endpoint"])

    def test_cap_loss_is_separate_from_ranking_loss(self):
        points = [(400+i,400,.9-i*.001) for i in range(20)] + [(100,100,.8)]
        labels,run = run_fixture([points])
        reports = [evaluation.evaluate_observations(labels,run,rank_candidates(run,config(arm),COMMIT),10.0,COMMIT)
                   for arm in ARMS]
        _,losses = evaluation.paired_differences(reports)
        self.assertEqual(len(losses),2)
        for loss in losses:
            self.assertEqual(loss["cap_lost_frames"],[0])
            self.assertEqual(loss["additional_ranking_lost_frames"],[])
            self.assertEqual(loss["raw_no_qualifying_candidate_frames"],[])

    def test_causal_prefix_window_reset_and_horizon_expiry(self):
        points = [[(100+i,100,.8)] for i in range(7)]
        _,full = run_fixture(points)
        _,prefix = run_fixture(points[:4])
        a = rank_candidates(full,config(),COMMIT)
        b = rank_candidates(prefix,config(),COMMIT)
        self.assertEqual(a["frames"][:4],b["frames"])
        self.assertEqual(a,rank_candidates(full,config(),COMMIT))
        self.assertEqual(a["frames"][-1]["horizon_start"],2)
        self.assertTrue(all(e["from"][0]>=2 for e in a["frames"][-1]["ranking"]["eligible_edges"]))

    def test_no_file_access_input_immutability_and_tamper_rejection(self):
        _,run = run_fixture([[(100,100,.8)],[(101,100,.8)]])
        before = canonical_sha256(run.to_dict())
        with patch.object(Path,"open",side_effect=AssertionError("ranking opened external file")):
            value = rank_candidates(run,config(),COMMIT)
        self.assertEqual(before,canonical_sha256(run.to_dict()))
        validate_observations(value,run)
        value["frames"][-1]["ranking"]["winner"]["score"] += .01
        with self.assertRaises(ValueError):
            validate_observations(value,run)

    def test_hidden_truth_is_not_used_to_suppress_predictions(self):
        labels = parse_reviewed_annotations([observed_frame(0),not_visible_frame(1)])
        labels,run = run_fixture([[(100,100,.8)],[(101,100,.8)]],labels)
        value = rank_candidates(run,config(),COMMIT)
        report = evaluation.evaluate_observations(labels,run,value,10.0,COMMIT)
        self.assertEqual(report["metrics"]["non_visible_false_alarm_count"],1)

    def test_bad_order_and_failed_input_are_rejected(self):
        _,run = fixture([[(100,100,.2),(200,200,.9)]])
        with self.assertRaises(ValueError):
            rank_candidates(run,config(),COMMIT)
        _,run = run_fixture([[(100,100,.8)]])
        failed = replace(run,frames=(replace(run.frames[0],inference_status="inference_failed",failure_reason="synthetic",detections=None),))
        with self.assertRaises(ValueError):
            rank_candidates(failed,config(),COMMIT)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.path,self.m,self.p = ranking_setup(self.root)

    def test_manifest_and_inputs_are_label_blind(self):
        original = Path.open
        def guarded(path,*args,**kwargs):
            name = path.as_posix()
            if "/annotations/" in name or "/evaluation/" in name or name.endswith("diagnostic.json") or "/data/clips/" in name:
                raise AssertionError("selector opened forbidden input "+name)
            return original(path,*args,**kwargs)
        with patch.object(Path,"open",guarded):
            loaded = experiment.load_manifest(self.root,self.path)
            self.assertEqual(len(experiment.load_inputs(self.root,loaded)),6)

    def test_dirty_state_stops_before_saved_input_load(self):
        with patch.object(experiment,"clean_commit",side_effect=ValueError("dirty")),patch.object(experiment,"load_inputs") as inputs:
            with self.assertRaisesRegex(ValueError,"dirty"):
                experiment.run_experiment(self.root,self.path)
            inputs.assert_not_called()
        self.assertFalse((self.root/experiment.OUTPUT_ROOT).exists())

    def test_changed_scope_rejected_even_with_rebound_receipt(self):
        changes = []
        p=copy.deepcopy(self.p);p["windows"][0]["purpose"]="test_holdout";changes.append(p)
        p=copy.deepcopy(self.p);p["windows"][0]["start_frame_index"]+=1;changes.append(p)
        p=copy.deepcopy(self.p);p["ranking_contract"]["history_frames"]=6;changes.append(p)
        p=copy.deepcopy(self.p);p["ranking_contract"]["missing_frame_penalty"]=.1;changes.append(p)
        p=copy.deepcopy(self.p);p["confidence_thresholds"].pop();changes.append(p)
        p=copy.deepcopy(self.p);p["selected_operating_point"]={"confidence":.35};changes.append(p)
        p=copy.deepcopy(self.p);p["force"]=True;changes.append(p)
        p=copy.deepcopy(self.p);p["windows"].pop();changes.append(p)
        for p in changes:
            path,_=bind_manifest(self.root,p)
            with self.subTest(p=p),self.assertRaises(ValueError):
                experiment.load_manifest(self.root,path)

    def test_all_nine_embargo_paths_enforced(self):
        parent=read_json(self.root/"configs/ball_tracking/experiments/rfdetr_medium_image_only_baseline_v0_1.json")
        for w in [w for w in parent["windows"] if w["execution_status"]=="annotation_pending_prediction_embargo"]:
            target=self.root/w["output_path"]
            write_json(target,{})
            try:
                with self.assertRaisesRegex(ValueError,"embargo"):
                    experiment.load_manifest(self.root,self.path)
            finally:
                target.unlink()

    def test_approval_and_crop_tampering_rejected(self):
        target=self.root/self.m["authorization"]["path"]
        original=target.read_bytes();target.write_bytes(original+b" ")
        with self.assertRaises(ValueError):
            experiment.load_manifest(self.root,self.path)
        target.write_bytes(original)
        target=self.root/self.p["windows"][0]["crop_candidates"]["path"]
        target.write_text(target.read_text()+" ")
        with self.assertRaises(ValueError):
            experiment.load_inputs(self.root,experiment.load_manifest(self.root,self.path))

    def test_dry_run_has_no_selection_or_output(self):
        with ExitStack() as stack:
            execution_patches(stack)
            rank=stack.enter_context(patch.object(experiment,"rank_candidates"))
            result=experiment.run_experiment(self.root,self.path,dry_run=True)
            rank.assert_not_called()
        self.assertEqual((result["source_frames"],result["new_model_calls"]),(150,0))
        self.assertFalse((self.root/experiment.OUTPUT_ROOT).exists())


class IntegrationTests(unittest.TestCase):
    def test_complete_partial_resume_control_parity_and_review(self):
        with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
            root=Path(directory)
            path,m,p=ranking_setup(root)
            execution_patches(stack)
            original=experiment.persist_once
            count=0
            def interrupted(target,payload):
                nonlocal count
                count+=1
                if count==8:
                    raise RuntimeError("synthetic interruption")
                return original(target,payload)
            with patch.object(experiment,"persist_once",side_effect=interrupted),self.assertRaisesRegex(RuntimeError,"interruption"):
                experiment.run_experiment(root,path)
            self.assertEqual(experiment.run_experiment(root,path)["created_outputs"],263)
            before={f:sha256_file(f) for f in (root/experiment.OUTPUT_ROOT).rglob("*.json")}
            self.assertEqual(experiment.run_experiment(root,path)["created_outputs"],0)
            self.assertEqual(before,{f:sha256_file(f) for f in before})
            scored=evaluation.score_experiment(root,path)
            self.assertEqual((scored["per_window_reports"],scored["aggregate_cells_per_pool"],scored["saved_control_parity_cells"]),(1350,225,540))
            grid=read_json(root/scored["reports"][0]["path"])
            self.assertEqual(len(grid["evaluation_reports"]),675)
            self.assertEqual(len(grid["aggregate_results"]),225)
            self.assertTrue(grid["loss_decomposition"])
            with self.assertRaises(ValueError):
                evaluation.aggregate([grid["evaluation_reports"][0]]*2)
            changed=copy.deepcopy(grid["evaluation_reports"][0]);changed["frame_results"][0]["false_negative_count"]+=1
            with self.assertRaises(ValueError):
                evaluation.verify_control_parity(changed,grid["evaluation_reports"][0])
            import cv2
            original_capture=cv2.VideoCapture
            source=np.zeros((1080,1920,3),dtype=np.uint8)
            cv2.putText(source,"SYNTHETIC RANKING REVIEW",(400,300),cv2.FONT_HERSHEY_SIMPLEX,1,(90,90,90),2)
            class Capture:
                def __init__(self): self.index=0
                def isOpened(self): return True
                def set(self,property,value): self.index=int(value);return True
                def get(self,property): return self.index if property==cv2.CAP_PROP_POS_FRAMES else 25.0
                def read(self): self.index+=1;return True,source.copy()
                def release(self): pass
            def capture(target):
                return Capture() if "/data/clips/" in str(target).replace("\\","/") else original_capture(target)
            stack.enter_context(patch.object(review,"verify_source_video_contract"))
            stack.enter_context(patch.object(cv2,"VideoCapture",side_effect=capture))
            result=review.render_experiment(root,path)
            self.assertEqual(result["assets"],2412)
            bundle=Path(result["bundle"])
            record=read_json(bundle/"manifest.json")
            self.assertEqual(sum(a["path"].endswith(".mp4") for a in record["assets"]),12)
            self.assertEqual(len(record["final_frames"]),6)
            self.assertTrue(review.render_experiment(root,path)["reused"])
            previews=ROOT/"data/outputs/ball_tracking/crop_ranking_implementation_validation"
            previews.mkdir(parents=True,exist_ok=True)
            for name in ("comparison","closeups"):
                src=bundle/p["windows"][0]["window_id"]/"confidence_0.2"/name/"frame_000074.png"
                (previews/f"synthetic_{name}.png").write_bytes(src.read_bytes())
            (bundle/record["assets"][0]["path"]).write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                review.validate_review_bundle(bundle,record["header"])
            target=experiment.output_path(root,p["windows"][0],experiment_grid()[0])
            value=read_json(target);value["crop_content_sha256"]="0"*64;write_json(target,value)
            with self.assertRaises(ValueError):
                experiment.run_experiment(root,path)


if __name__ == "__main__":
    unittest.main()
