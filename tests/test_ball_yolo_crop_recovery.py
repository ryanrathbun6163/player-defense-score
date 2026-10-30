"""Synthetic partial-run recovery; real project evidence is never selected."""
import copy
import ast
import contextlib
import io
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np

from src.ball_tracking import yolo_crop_experiment as old
from src.ball_tracking import yolo_crop_recovery as recovery
from src.ball_tracking.development_experiments import canonical_sha256, read_json, sha256_file
from src.ball_tracking.temporal_experiment import file_binding, spec_digest
from test_ball_yolo_crop_experiment import fixture as original_fixture, FakeAdapter, write

NEW_COMMIT="b"*40


def bind_partial(root,old_path,old_m,p,inputs,commit=NEW_COMMIT):
    """Bind an already created synthetic175-unit partial run for sibling tests."""
    units=recovery._units(p);completed=[]
    for u in units[:175]:
        w=next(w for w in p["windows"] if w["window_id"]==u["window_id"])
        target=old.checkpoint_path(root,w,u["frame_index"],recovery.crop_views()[u["view_ordinal"]])
        cp=read_json(target)
        completed.append({**u,"checkpoint":file_binding(root,target),"actual_inference_commit":recovery.ORIGINAL_COMMIT,"attempt_id":cp["result"]["attempt_id"]})
    attempts=[]
    for target in sorted((root/old.OUTPUT_ROOT/"attempts").glob("*.start.json")):
        start=read_json(target);result_path=target.with_name(target.name.replace(".start.json",".result.json"));result=read_json(result_path)
        w=next(w for w in p["windows"] if w["window_id"]==start["window_id"])
        attempts.append({"attempt_id":start["attempt_id"],"preparation_id":start["preparation_id"],**recovery.unit(w,start["frame_index"],start["view"]),
                         "status":result["status"],"start":file_binding(root,target),"result":file_binding(root,result_path)})
    preps=[]
    for target in sorted((root/old.OUTPUT_ROOT/"preparations").glob("*.start.json")):
        start=read_json(target);result_path=target.with_name(target.name.replace(".start.json",".result.json"))
        preps.append({"preparation_id":start["preparation_id"],"start":file_binding(root,target),"result":file_binding(root,result_path)})
    assert len(attempts)==177 and len(preps)==2
    design=root/"docs/synthetic_recovery.md";design.write_text("Synthetic recovery design",encoding="utf-8")
    r={"schema_version":"ball_yolo_crop_recovery_proposal/v0.2","recovery_output_root":recovery.OUTPUT_ROOT,
       "original_experiment":file_binding(root,old_path),"original_runtime":old_m["runtime"],"original_execution_commit":recovery.ORIGINAL_COMMIT,
       "original_experiment_spec_sha256":spec_digest(old_m),"windows":p["windows"],"crop_views":p["crop_views"],
       "sealed_holdouts":p["sealed_holdouts"],"holdout_release_authorized":False,"design_document":file_binding(root,design),
       "completed_crop_units_reuse_without_inference":completed,"missing_crop_units_only_allowed_new_inference":units[175:],
       "preserved_attempt_receipts":attempts,"preserved_preparation_receipts":preps,
       "preserved_candidate_files":[file_binding(root,t) for t in sorted((root/old.OUTPUT_ROOT).glob("*/candidates.json"))],
       "preserved_selector_files":[file_binding(root,t) for t in sorted((root/old.OUTPUT_ROOT).glob("*/yolo_*.json"))]}
    rpath=root/"configs/ball_tracking/proposals/synthetic_recovery.json";write(rpath,r)
    approval={"schema_version":"ball_yolo11x_crop_recovery_approval/v0.2","proposal":file_binding(root,rpath),"approved_by":"Ryan",
              "user_statement":"Synthetic test approval","approved_at_utc":"synthetic","implementation_and_recovery_authorized":True,
              "git_authorization":{"stage":False,"commit":False,"push":False,"pull_request":False,"merge":False}}
    apath=root/"configs/ball_tracking/reviews/synthetic_recovery.json";write(apath,approval)
    m={"schema_version":"ball_yolo_crop_recovery_experiment/v0.2","experiment_id":"yolo11x_crop_recovery_v0_2",
       "recovery_proposal":file_binding(root,rpath),"original_experiment":file_binding(root,old_path),"authorization":file_binding(root,apath),
       "runtime":old_m["runtime"],"output_root":recovery.OUTPUT_ROOT,"selected_operating_point":None,"quality_gate":None}
    path=root/"configs/ball_tracking/yolo_crop_experiments/synthetic_recovery.json";write(path,m)
    revised=[{**item,"model":replace(item["model"],code_commit=commit),"recovery":r,"original_manifest":old_m} for item in inputs]
    return path,m,p,revised


def partial_fixture(root):
    path,m,p,inputs=original_fixture(root)
    inputs=[{**i,"model":replace(i["model"],code_commit=recovery.ORIGINAL_COMMIT)} for i in inputs]
    with patch.object(old,"preflight",return_value=(m,p,inputs,recovery.ORIGINAL_COMMIT)),patch.object(old,"unchanged"):
        for failure in (176,1):
            try:
                old.run_experiment(root,path,adapter_factory=lambda *args,failure=failure:FakeAdapter(fail_at=failure),
                                   png_reader=lambda *args:np.zeros((1080,1920,3),np.uint8))
            except RuntimeError:
                pass
            else:
                raise AssertionError("Synthetic original failure did not happen")
    return bind_partial(root,path,m,p,inputs)


class RecoveryTests(unittest.TestCase):
    def test_exact_recovery425_units_mixed_provenance_resume_and_original_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,m,p,inputs=partial_fixture(root)
            preserved={b["path"]:b["sha256"] for b in recovery.preserved_bindings(inputs[0]["recovery"])}
            factory=Mock(return_value=FakeAdapter());reader=Mock(return_value=np.zeros((1080,1920,3),np.uint8))
            with patch.object(recovery,"preflight",return_value=(m,p,inputs,NEW_COMMIT)),patch.object(recovery,"unchanged"),\
                    patch.object(old,"run_experiment",side_effect=AssertionError("old pipeline invoked")):
                result=recovery.run_experiment(root,path,adapter_factory=factory,png_reader=reader)
                self.assertEqual(result["new_crop_units"],425)
                self.assertEqual(result["known_total_project_attempts"],602)
                self.assertEqual(result["known_total_synthetic_forwards"],6)
                self.assertEqual(result["predictor_preparations"],3)
                self.assertEqual(result["recorded_attempt_starts"],602)
                self.assertEqual(factory.return_value.calls,425)
                files=list((root/recovery.OUTPUT_ROOT).rglob("*.json"));before={str(f):sha256_file(f) for f in files}
                again=recovery.run_experiment(root,path,adapter_factory=Mock(side_effect=AssertionError("resume model")),png_reader=Mock(side_effect=AssertionError("resume pixels")))
                self.assertEqual(again["created_new_checkpoints_this_invocation"],0)
                self.assertEqual(before,{str(f):sha256_file(f) for f in files})
                self.assertEqual(preserved,{s:sha256_file(root/s) for s in preserved})
                old_first=read_json(root/inputs[0]["recovery"]["preserved_candidate_files"][0]["path"])
                new_first=read_json(recovery.candidate_path(root,p["windows"][0]))
                self.assertEqual(new_first["frames"],old_first["frames"])
                for b in inputs[0]["recovery"]["preserved_selector_files"]:
                    old_obs=read_json(root/b["path"])["observations"]
                    new_obs=read_json(recovery.output_path(root,p["windows"][0],recovery.SelectorConfig.from_mapping(old_obs["config"])))["observations"]
                    self.assertEqual(new_obs["frames"],old_obs["frames"])
                run,payload,digest=recovery.load_candidate_run(root,m,p,p["windows"][1],NEW_COMMIT,model=inputs[1]["model"])
                self.assertEqual(payload["header"]["actual_inference_commits"],sorted([recovery.ORIGINAL_COMMIT,NEW_COMMIT]))
                self.assertEqual(len(payload["header"]["inference_units"]),100)
                c=recovery.experiment_grid()[0]
                obs=recovery.load_observations(root,m,p,p["windows"][1],run,digest,c,NEW_COMMIT)
                self.assertNotIn("detector_code_commit",obs)
                self.assertEqual(obs["model_code_commit_role"],recovery.ROLE)
                self.assertEqual(obs["assembly_code_commit"],NEW_COMMIT)
                singular=copy.deepcopy(obs);singular["detector_code_commit"]=NEW_COMMIT
                with self.assertRaisesRegex(ValueError,"actual-inference/assembly provenance"):
                    recovery.validate_saved_observations(singular,run,payload,recovery.file_binding(root,recovery.candidate_path(root,p["windows"][1])))
                # Tampered actual commits reject before any new model or pixels.
                crop=next((root/recovery.OUTPUT_ROOT).glob("*/views/*.json"));cp=read_json(crop)
                cp["header"]["actual_inference_commit"]="c"*40
                cp["content_sha256"]=canonical_sha256({k:v for k,v in cp.items() if k!="content_sha256"});write(crop,cp)
                with self.assertRaises(ValueError):recovery.run_experiment(root,path,adapter_factory=Mock(side_effect=AssertionError("model")),png_reader=reader)

    def test_publication_interruption_preserves_checkpoint_and_unknown_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,m,p,inputs=partial_fixture(root)
            persist=recovery.persist_once
            def interrupt(target,payload):
                if target.parent.name=="attempts" and target.name.endswith(".result.json"):
                    raise RuntimeError("synthetic interruption after checkpoint publication")
                return persist(target,payload)
            with patch.object(recovery,"preflight",return_value=(m,p,inputs,NEW_COMMIT)),patch.object(recovery,"unchanged"):
                first=FakeAdapter()
                with patch.object(recovery,"persist_once",side_effect=interrupt),self.assertRaisesRegex(RuntimeError,"after checkpoint"):
                    recovery.run_experiment(root,path,adapter_factory=lambda *args:first,png_reader=lambda *args:np.zeros((1080,1920,3),np.uint8))
                cp=next((root/recovery.OUTPUT_ROOT).glob("*/views/*.json"));before=sha256_file(cp)
                ledger=recovery._load_ledger(root,m,p,NEW_COMMIT,model=inputs[0]["model"])
                self.assertEqual(ledger["unfinished_attempt_records"],1)
                self.assertEqual(ledger["known_project_forwards"],1)
                second=FakeAdapter()
                result=recovery.run_experiment(root,path,adapter_factory=lambda *args:second,png_reader=lambda *args:np.zeros((1080,1920,3),np.uint8))
                self.assertEqual(second.calls,424)
                self.assertEqual(before,sha256_file(cp))
                self.assertTrue(result["unfinished_accounting_is_unknown"])
                self.assertEqual(result["known_total_project_forwards"],602)
                self.assertEqual(result["known_total_synthetic_forwards"],8)
                # A duplicate/gapped cumulative counter must fail before a model.
                start=next((root/recovery.OUTPUT_ROOT/"attempts").glob("*.start.json"));value=read_json(start)
                value["accounting_before"]["project_attempts"]+=1;write(start,value)
                with self.assertRaises(ValueError):recovery.run_experiment(root,path,adapter_factory=Mock(side_effect=AssertionError("model")))

    def test_contract_partition_authorization_and_dirty_gate_before_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,m,p,inputs=partial_fixture(root);r=inputs[0]["recovery"];old_m=inputs[0]["original_manifest"]
            with patch.object(recovery,"PROPOSAL_SHA",m["recovery_proposal"]["sha256"]),patch.object(old,"EXPECTED_PROPOSAL_SHA",old_m["proposal"]["sha256"]):
                loaded=recovery.load_manifest(root,path)
                self.assertEqual(loaded[0],m)
                with patch.object(recovery,"clean_commit",side_effect=ValueError("clean committed checkpoint")),\
                        patch.object(old,"preflight",side_effect=AssertionError("runtime before dirty guard")):
                    with self.assertRaisesRegex(ValueError,"clean committed"):recovery.preflight(root,path)
            changed=copy.deepcopy(r);changed["missing_crop_units_only_allowed_new_inference"][0]=changed["missing_crop_units_only_allowed_new_inference"][1]
            with self.assertRaisesRegex(ValueError,"partition"):recovery.validate_partition(root,changed,p)
            with patch.object(recovery,"preflight",return_value=(m,p,inputs,NEW_COMMIT)),patch.object(recovery.simple,"select_candidates",side_effect=lambda *args:{"frames":[]}):
                with self.assertRaises((KeyError,ValueError)):recovery.run_experiment(root,path,adapter_factory=Mock(side_effect=AssertionError("model before parity")))

    def test_failed_and_orphan_header_binding_and_unknown_tail(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,m,p,inputs=partial_fixture(root)
            with patch.object(recovery,"preflight",return_value=(m,p,inputs,NEW_COMMIT)),patch.object(recovery,"unchanged"):
                with self.assertRaisesRegex(RuntimeError,"failed project"):
                    recovery.run_experiment(root,path,adapter_factory=lambda *args:FakeAdapter(fail_at=1),png_reader=lambda *args:np.zeros((1080,1920,3),np.uint8))
                ledger=recovery._load_ledger(root,m,p,NEW_COMMIT,model=inputs[0]["model"])
                self.assertEqual(ledger["known_project_forwards"],1)
                start=next((root/recovery.OUTPUT_ROOT/"attempts").glob("*.start.json"));s=read_json(start)
                end=start.with_name(start.name.replace(".start.json",".result.json"));r=read_json(end)
                s["header_sha256"]="f"*64;write(start,s);r["start_sha256"]=sha256_file(start);write(end,r)
                with self.assertRaisesRegex(ValueError,"Attempt outside"):
                    recovery.run_experiment(root,path,adapter_factory=Mock(side_effect=AssertionError("model before bad failed header")))
                end.unlink()  # Synthetic process-death fixture, not project evidence.
                with self.assertRaisesRegex(ValueError,"Attempt outside"):
                    recovery._load_ledger(root,m,p,NEW_COMMIT,model=inputs[0]["model"])
                w=inputs[1]["window"]
                s["header_sha256"]=canonical_sha256(recovery._unit_header(m,w,inputs[1]["model"],inputs[1]["source_frames"]));write(start,s)
                ledger=recovery._load_ledger(root,m,p,NEW_COMMIT,model=inputs[0]["model"])
                self.assertEqual(ledger["unfinished_attempt_records"],1)
                self.assertEqual(ledger["known_project_forwards"],0)
                # Restore the genuine failed result in this synthetic fixture;
                # its observed forward remains counted when all425 units resume.
                r["start_sha256"]=sha256_file(start);write(end,r)
                resumed=FakeAdapter()
                result=recovery.run_experiment(root,path,adapter_factory=lambda *args:resumed,png_reader=lambda *args:np.zeros((1080,1920,3),np.uint8))
                self.assertEqual(resumed.calls,425)
                self.assertEqual(result["failed_recovery_attempts"],1)
                self.assertEqual(result["known_total_project_forwards"],603)
                self.assertEqual(result["recorded_attempt_starts"],603)
                self.assertEqual(result["known_total_synthetic_forwards"],8)
                # A process-death variant loses only that failed result. Its
                # unknowable tail remains explicit without rerunning completed units.
                end.unlink()
                result=recovery.run_experiment(root,path,adapter_factory=Mock(side_effect=AssertionError("orphan resume model")),png_reader=Mock(side_effect=AssertionError("orphan resume pixels")))
                self.assertEqual(result["unfinished_attempt_records"],1)
                self.assertEqual(result["known_total_project_forwards"],602)
                self.assertEqual(result["recorded_attempt_starts"],603)
                self.assertTrue(result["unfinished_accounting_is_unknown"])

    def test_cli_guard_runs_after_all_api_definitions(self):
        # Execute the actual module entry point with only its work function
        # replaced: this catches definitions accidentally placed after main().
        source=Path(recovery.__file__).read_text(encoding="utf-8")
        tree=ast.parse(source)
        for node in tree.body:
            if isinstance(node,ast.FunctionDef) and node.name=="run_experiment":
                node.body=ast.parse("assert callable(load_observations)\nassert callable(validate_saved_observations)\nreturn {'entry_point_definitions_available': True}").body
        ast.fix_missing_locations(tree)
        namespace={"__name__":"__main__","__package__":"src.ball_tracking"}
        with patch("sys.argv",["recovery","--manifest","synthetic.json"]),contextlib.redirect_stdout(io.StringIO()) as output:
            exec(compile(tree,recovery.__file__,"exec"),namespace)
        self.assertIn('entry_point_definitions_available',output.getvalue())


if __name__=="__main__":unittest.main()
