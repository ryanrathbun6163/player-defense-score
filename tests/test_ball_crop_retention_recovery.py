"""Fabricated recovery evidence only; no real outputs, models or video access."""
import copy
from dataclasses import replace
import gzip
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.ball_tracking import crop_retention_experiment as original
from src.ball_tracking import crop_retention_recovery as recovery
from src.ball_tracking import crop_retention_evaluation as scoring
from src.ball_tracking import crop_retention_review as review
from src.ball_tracking.crop_retention import ARMS, STEPS, RankingConfig
from src.ball_tracking.crop_retention_resources import BudgetJournal
from src.ball_tracking.development_experiments import canonical_sha256, sha256_file
from src.ball_tracking.tiled_candidates import candidate_run, crop_views, make_frame, make_output
from test_ball_temporal_association import fixture
from test_ball_tiled_comparison import crop_result
from test_ball_crop_retention_evaluation import full_fixture


OLD_COMMIT = "0a7f5bc69be948b8c4e2c630c84c4ccdefb5dc41"
NEW_COMMIT = "b" * 40
OLD_SPEC = "e481d645e946f285c655d721563172c4cb8c2f124214840b8c8d8ae5cfb752fd"
NEW_SPEC = "c" * 64


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def binding(root, path):
    return {"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)}


def empty_window(root, number):
    """A valid saved crop input generated from invented empty detector records."""
    _, base = fixture([[] for _ in range(25)])
    model = replace(base.model_provenance, code_commit=original.RF_COMMIT,
                    target_class_id=37, target_class_name="sports ball", export_confidence_floor=.01)
    base = replace(base, model_provenance=model)
    window = {"window_id": f"synthetic_window_{number}", "purpose": "representative_evaluation" if number < 3 else "challenge_evaluation",
              "possession_id": base.possession_id, "source_video": base.source_video.to_dict(),
              "start_frame_index": 0, "end_frame_index": 24, "annotation_set_id": base.annotation_set_id}
    frames = [make_frame(i, [crop_result(v) for v in crop_views()], base.source_video, model) for i in range(25)]
    output = make_output({"window": {**window, "detection_run_id": base.detection_run_id},
                          "per_view_model_provenance": model.to_dict(), "crop_views": crop_views()}, frames)
    path = root/f"data/outputs/synthetic_candidates/window_{number}.json"
    write_json(path, output)
    window["crop_candidates"] = binding(root,path)
    return window, candidate_run(base,output), output


def empty_saved_frame(index):
    winner = {"endpoint":None,"score":0.0,"path":[],"endpoint_confidence":None,"trailing_skipped_frames":None}
    return {"frame_index":index,"horizon_start":max(0,index-4),"horizon_end":index,
            "emitted_candidate_indices":[],"candidate_decisions":[],
            "ranking":{"eligible_edges":[],"best_path_per_endpoint":[],
                       "competing_endpoints":[winner],"winner":winner,"score_margin":None},
            "decision_reason":"empty_hypothesis","output_state":"no_accepted_observation"}


class SyntheticRecovery:
    """Exact24/600 immutable evidence, one failed write, and later diagnosis."""

    def __init__(self, root):
        self.root = root
        self.output = root/original.OUTPUT_ROOT
        self.output.mkdir(parents=True)
        self.limits = {"workers":1,"maximum_cumulative_seconds":14400,"maximum_seconds_per_unit":1800,
                       "maximum_worker_memory_bytes":8*1024**3,"maximum_total_new_output_bytes":32*1024**3,
                       "minimum_free_disk_bytes":10*1024**3}
        self.proposal = {"windows":[],"new_selection_units":[],"resource_limits":self.limits,
                         "original_embargo_paths":[f"data/outputs/embargo_{i}.json" for i in range(9)],
                         "sealed_holdouts_metadata_only":[["p1",100,124],["p2",200,224],["p3",300,324]]}
        self.original_context = {"root":root,"output_root":self.output,"commit":OLD_COMMIT,"spec_sha256":OLD_SPEC,
                                 "manifest":{},"proposal":self.proposal,"inputs":{}}
        self.context = {"root":root,"output_root":self.output,"commit":NEW_COMMIT,"spec_sha256":NEW_SPEC,
                        "manifest":{},"proposal":self.proposal,"inputs":self.original_context["inputs"],
                        "original_context":self.original_context}
        self.selections, self.attempts = [], []
        self.journal = BudgetJournal(self.output,self.limits)
        self.add_attempt("preflight:select","preflight",stage="preflight",key="select")
        for number in range(6):
            window, run, crop = empty_window(root,number)
            self.proposal["windows"].append(window)
            self.original_context["inputs"][window["window_id"]] = (run,crop["content_sha256"])
            for arm in ARMS:
                config = RankingConfig(arm,.01,None,*STEPS[arm])
                unit = {"comparison_unit_id":window["window_id"]+"__"+arm,"window_id":window["window_id"],
                        "config":{**config.to_dict(),"retention_policy":"all_threshold_qualified_saved_candidates"}}
                self.proposal["new_selection_units"].append(unit)
                attempt,_ = self.journal.reserve("select:"+unit["comparison_unit_id"],True)
                folder = original.unit_directory(self.original_context,unit)
                folder.mkdir(parents=True)
                compact, traces = [], []
                for i in range(25):
                    full = empty_saved_frame(i)
                    trace = folder/f"frame_{i:06d}.json.gz"
                    trace.write_bytes(gzip.compress(json.dumps(full).encode(),mtime=0))
                    b = binding(root,trace)
                    traces.append({"frame_index":i,**b})
                    compact.append({**{k:copy.deepcopy(v) for k,v in full.items() if k != "ranking"},
                                    "ranking":{"winner":copy.deepcopy(full["ranking"]["winner"]),"score_margin":None,
                                               "best_path_for_winner":None,"current_alternatives":[]},
                                    "audit_counts":{"node_count":0,"edge_count":0,"competing_endpoint_count":1},
                                    "trace_binding":b})
                obs = {"schema_version":"ball_crop_retention_observations/v0.1","variant_id":config.variant_id,
                       "config":unit["config"],"ranking_code_commit":OLD_COMMIT,"detector_code_commit":original.RF_COMMIT,
                       "input_candidate_content_sha256":canonical_sha256(run.to_dict()),"source_video":run.source_video.to_dict(),
                       "window":run.window.to_dict(),"possession_id":run.possession_id,"frames":compact,
                       "selected_method":None,"selected_operating_point":None,"quality_gate":None,
                       "score_semantics":"Synthetic frozen empty hypothesis; never executed selection"}
                manifest = {"schema_version":"ball_crop_retention_output/v0.1","experiment_spec_sha256":OLD_SPEC,
                            "input_crop_file":window["crop_candidates"],"crop_content_sha256":crop["content_sha256"],
                            "observations":obs,"observations_content_sha256":canonical_sha256(obs),"resource_attempt_id":attempt}
                path = folder/"manifest.json"
                write_json(path,manifest)
                record = self.finish_attempt(attempt,"selection",[binding(root,path)],stage="select",key=unit["comparison_unit_id"])
                self.selections.append({"unit":unit,"manifest":binding(root,path),"observations_content_sha256":canonical_sha256(obs),
                                        "input_crop_file":window["crop_candidates"],"crop_content_sha256":crop["content_sha256"],
                                        "input_candidate_content_sha256":obs["input_candidate_content_sha256"],"traces":traces,
                                        "attempt_id":attempt,"worker_result":record["worker_result"],
                                        "completion":binding(root,self.output/"resource_events"/f"{len(self.journal.events)-1:08d}.json")})
        self.add_attempt("preflight:score","preflight",stage="preflight",key="score")
        failed,_ = self.journal.reserve("score:"+self.proposal["windows"][0]["window_id"],False)
        self.partial = self.output/"evaluation/windows/synthetic_window_0.json.incomplete-failed"
        self.partial.parent.mkdir(parents=True)
        self.partial.write_bytes(b'{"synthetic_incomplete":')
        log = self.output/"attempts"/(failed+".log")
        log.write_text("Synthetic monitor measurement failure\n",encoding="utf-8")
        failed_record = self.finish_attempt(failed,"failed_score",[],success=False,elapsed=.5)
        self.failure = {"attempt_id":failed,"completion_event_sha256":self.journal.events[-1]["sha256"],
                        "partial":{**binding(root,self.partial),"size_bytes":self.partial.stat().st_size},"log":binding(root,log)}
        failed_event = copy.deepcopy(self.journal.events[-1])
        successful = [r["worker_result"] for r in self.attempts if r["worker_result"] is not None]
        self.add_attempt("diagnosis:interruption","diagnosis",stage="diagnosis",key="interruption",elapsed=2.0)
        interruption = self.output/"audit/interruption_receipt.json"
        write_json(interruption,{"experiment_commit":OLD_COMMIT,"original_spec_sha256":OLD_SPEC,
                                 "completed_selection_manifests":[e["manifest"] for e in self.selections],
                                 "completed_trace_bindings":[{k:v for k,v in b.items() if k != "frame_index"}
                                                             for e in self.selections for b in e["traces"]],
                                 "successful_worker_receipts":successful,"failed_completion_event":failed_event,
                                 "partial_scoring_file":{**binding(root,self.partial),"bytes":self.partial.stat().st_size},
                                 "failed_worker_log":binding(root,log)})
        self.inventory = {"schema_version":"ball_crop_candidate_retention_recovery_inventory/v0.1",
                          "original_commit":OLD_COMMIT,"original_spec_sha256":OLD_SPEC,"original_source_bindings":[],
                          "interruption_receipt":binding(root,interruption),"selections":self.selections,
                          "journal_prefix":{"events":[binding(root,p) for p in sorted((self.output/"resource_events").glob("*.json"))],
                                            "chain_tip_sha256":self.journal.events[-1]["sha256"],"attempts":self.attempts},
                          "failed_scoring":self.failure}
        self.context["inventory"] = self.inventory

    def add_attempt(self, unit_key, role, *, stage, key, elapsed=.01):
        attempt,_ = self.journal.reserve(unit_key,False)
        return self.finish_attempt(attempt,role,[],stage=stage,key=key,elapsed=elapsed)

    def finish_attempt(self, attempt, role, artifacts, *, stage="score",key="",success=True,elapsed=.01,
                       commit=OLD_COMMIT,spec=OLD_SPEC):
        worker_binding = None
        if success:
            path = self.output/"attempts"/(attempt+".result.json")
            write_json(path,{"stage":stage,"key":key,"commit":commit,"spec_sha256":spec,"artifacts":artifacts})
            worker_binding = binding(self.root,path)
        relative = {"path":str((self.root/worker_binding["path"]).relative_to(self.output)).replace("\\","/"),
                    "sha256":worker_binding["sha256"]} if worker_binding else None
        self.journal.append("finished",attempt_id=attempt,elapsed_seconds=elapsed,success=success,exit_code=0 if success else 1,
                            failure=None if success else "ResourceLimitError: synthetic incomplete byte measurement",
                            worker_result=relative,peak_worker_memory_bytes=1024,maximum_output_bytes=4096,
                            final_accounting_output_bound_bytes=20480,final_accounting_error=None,
                            maximum_monitor_interval_seconds=.25,minimum_free_disk_bytes=100*1024**3,
                            time_overshoot_seconds=0,memory_overshoot_bytes=0,output_overshoot_bytes=0)
        record = {"attempt_id":attempt,"role":role,
                  "reservation":binding(self.root,self.output/"attempts"/(attempt+".reservation.json")),
                  "completion":binding(self.root,self.output/"attempts"/(attempt+".completion.json")),"worker_result":worker_binding}
        if commit == OLD_COMMIT:
            self.attempts.append(record)
        return record


class PreservedSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.data = SyntheticRecovery(self.root)

    def test_full_24_by_25_inventory_preserves_original_selection_roles_without_algorithm_calls(self):
        d = self.data
        with patch.object(original,"iter_ranked_frames",side_effect=AssertionError("selection rerun")), \
                patch.object(original,"write_selection",side_effect=AssertionError("selection rewritten")):
            recovery.validate_preserved(self.root,d.context)
            for entry in d.selections:
                obs = recovery.load_reused_observations(self.root,d.context,entry["unit"])
                self.assertEqual(obs["ranking_code_commit"],OLD_COMMIT)
                self.assertEqual(len(obs["frames"]),25)
                self.assertTrue(all(f["emitted_candidate_indices"] == [] for f in obs["frames"]))
        self.assertEqual(len(d.selections),24)
        self.assertEqual(sum(len(e["traces"]) for e in d.selections),600)

    def test_manifest_trace_partial_and_failed_log_changes_are_rejected(self):
        d = self.data
        cases = [d.selections[0]["manifest"],d.selections[-1]["traces"][-1],
                 d.inventory["failed_scoring"]["partial"],d.inventory["failed_scoring"]["log"]]
        for b in cases:
            file = self.root/b["path"]
            before = file.read_bytes()
            with self.subTest(path=b["path"]):
                file.write_bytes(before+b"altered")
                try:
                    with self.assertRaises((ValueError,RuntimeError)):
                        recovery.validate_preserved(self.root,d.context)
                finally:
                    file.write_bytes(before)

    def test_missing_duplicate_unknown_and_wrong_config_selection_allowlist_are_rejected(self):
        d = self.data
        original_inventory = copy.deepcopy(d.inventory)
        def missing(x): x["selections"].pop()
        def duplicate(x): x["selections"][-1] = copy.deepcopy(x["selections"][0])
        def unknown(x): x["selections"][0]["unit"]["comparison_unit_id"] = "not_an_approved_unit"
        def wrong_config(x): x["selections"][0]["unit"]["config"]["confidence_threshold"] = .2
        for mutate in (missing,duplicate,unknown,wrong_config):
            d.context["inventory"] = copy.deepcopy(original_inventory)
            mutate(d.context["inventory"])
            with self.subTest(change=mutate.__name__),self.assertRaises((ValueError,RuntimeError)):
                recovery.validate_preserved(self.root,d.context)
        d.context["inventory"] = d.inventory

    def test_changed_original_spec_or_commit_is_not_a_generic_ancestor_exception(self):
        d = self.data
        for field,value in (("original_spec_sha256","d"*64),("original_commit","e"*40)):
            altered = copy.deepcopy(d.inventory)
            altered[field] = value
            d.context["inventory"] = altered
            with self.subTest(field=field),self.assertRaises((ValueError,RuntimeError)):
                recovery.validate_preserved(self.root,d.context)
        d.context["inventory"] = d.inventory

    def test_selection_requires_its_exact_successful_worker_receipt(self):
        d = self.data
        first = d.selections[0]
        for field,value in (("attempt_id",d.failure["attempt_id"]),
                            ("worker_result",d.selections[1]["worker_result"]),
                            ("completion",d.selections[1]["completion"])):
            altered = copy.deepcopy(d.inventory)
            altered["selections"][0][field] = value
            d.context["inventory"] = altered
            with self.subTest(field=field),self.assertRaises((ValueError,RuntimeError)):
                recovery.validate_preserved(self.root,d.context)
        d.context["inventory"] = d.inventory

    def test_unlisted_unit_and_unlisted_selection_file_are_not_accepted(self):
        d = self.data
        unit = copy.deepcopy(d.selections[0]["unit"])
        unit["comparison_unit_id"] = "extra_unit"
        with self.assertRaises((ValueError,RuntimeError)):
            recovery.load_reused_observations(self.root,d.context,unit)
        file = self.root/d.selections[0]["manifest"]["path"]
        (file.parent/"unreceipted.json").write_text("{}",encoding="utf-8")
        with self.assertRaises((ValueError,RuntimeError)):
            recovery.load_reused_observations(self.root,d.context,d.selections[0]["unit"])

    def test_default_original_runner_rejects_mixed_spec_and_commit(self):
        d = self.data
        with self.assertRaisesRegex(ValueError,"another source checkpoint"):
            original.load_new_observations(self.root,d.context,d.selections[0]["unit"])
        # Loading through recovery must not mutate source context or receipts to
        # make the default runner's same-specification guard pass afterward.
        recovery.load_reused_observations(self.root,d.context,d.selections[0]["unit"])
        with self.assertRaisesRegex(ValueError,"another source checkpoint"):
            original.load_new_observations(self.root,d.context,d.selections[0]["unit"])

    def test_failed_scoring_and_diagnosis_remain_in_consumed_budget(self):
        d = self.data
        history = recovery.verify_history(self.root,d.context)
        self.assertAlmostEqual(history.consumed(),2.76,places=8)
        self.assertAlmostEqual(history.consumed("score:synthetic_window_0"),.5,places=8)
        _,remaining = history.reserve("recovery:score:synthetic_window_0",False)
        self.assertAlmostEqual(remaining,14400-2.76,places=8)
        self.assertTrue(d.partial.exists())

    def test_new_evaluation_preserves_old_ranking_commit_without_mutating_observations(self):
        d = self.data
        entry = d.selections[0]
        obs = recovery.load_reused_observations(self.root,d.context,entry["unit"])
        before = canonical_sha256(obs)
        labels,_ = fixture([[] for _ in range(25)])
        run,_ = d.context["inputs"][entry["unit"]["window_id"]]
        report = scoring.evaluate_unit(labels,run,obs,10.0,NEW_COMMIT)
        self.assertEqual(report["ranking_code_commit"],OLD_COMMIT)
        self.assertEqual(report["evaluator_code_commit"],NEW_COMMIT)
        self.assertEqual(report["observations_content_sha256"],before)
        self.assertEqual(canonical_sha256(obs),before)
        self.assertEqual(report["metrics"]["false_negative_count"],25)
        self.assertEqual(report["metrics"]["true_positive_count"],0)

    def test_missing_event_and_changed_completion_seal_cannot_reset_history(self):
        d = self.data
        event = self.root/d.inventory["journal_prefix"]["events"][3]["path"]
        before = event.read_bytes()
        event.unlink()
        try:
            with self.assertRaises((ValueError,RuntimeError,FileNotFoundError)):
                recovery.verify_history(self.root,d.context)
        finally:
            event.write_bytes(before)
        seal = self.root/d.attempts[-1]["completion"]["path"]
        seal.write_text('{"event_sha256":"'+'0'*64+'"}',encoding="utf-8")
        with self.assertRaises((ValueError,RuntimeError)):
            recovery.verify_history(self.root,d.context)

    def test_final_score_without_completion_receipt_is_never_adopted(self):
        d = self.data
        d.proposal["pool_separation"] = ["representative_evaluation","challenge_evaluation"]
        target = d.output/"evaluation/windows/synthetic_window_0.json"
        write_json(target,{"looks_complete":True})
        with patch.object(scoring,"load_window_score",side_effect=AssertionError("Unreceipted score loaded")):
            with self.assertRaisesRegex(ValueError,"Unreceipted"):
                recovery._validate_published(self.root,d.context,recovery.completed_bindings(self.root,d.context))
        self.assertTrue(target.exists())
        self.assertTrue(d.partial.exists())

    def test_receipt_only_completion_audit_cannot_bless_scientific_artifacts(self):
        d = self.data
        target = d.output/"audit/independent_recovery_audit.json"
        write_json(target,{"synthetic":True})
        attempt,_ = d.journal.reserve("recovery:completion-audit:",False)
        record = d.finish_attempt(attempt,"completion-audit",[binding(self.root,target)],stage="completion-audit",
                                  commit=NEW_COMMIT,spec=NEW_SPEC)
        completed = recovery.completed_bindings(self.root,d.context)
        self.assertEqual(completed,{target.relative_to(self.root).as_posix():sha256_file(target)})
        seal = self.root/record["completion"]["path"]
        before = seal.read_bytes()
        seal.unlink()
        try:
            with self.assertRaises((ValueError,RuntimeError)):
                recovery.completed_bindings(self.root,d.context)
        finally:
            seal.write_bytes(before)
        scientific = d.output/"evaluation/windows/synthetic_window_0.json"
        write_json(scientific,{"unapproved_scientific_output":True})
        attempt,_ = d.journal.reserve("recovery:completion-audit:",False)
        d.finish_attempt(attempt,"completion-audit",[binding(self.root,scientific)],stage="completion-audit",
                         commit=NEW_COMMIT,spec=NEW_SPEC)
        with self.assertRaisesRegex(ValueError,"unknown or incomplete artifacts"):
            recovery.completed_bindings(self.root,d.context)

    def test_new_receipts_must_use_recovery_spec_and_current_evaluation_commit(self):
        d = self.data
        target = d.output/"evaluation/windows/synthetic_window_0.json"
        write_json(target,{"synthetic":True})
        attempt,_ = d.journal.reserve("recovery:score:synthetic_window_0",False)
        d.finish_attempt(attempt,"score",[binding(self.root,target)],stage="score",key="synthetic_window_0",
                         commit=NEW_COMMIT,spec=OLD_SPEC)
        with self.assertRaisesRegex(ValueError,"incorrect source/specification/stage"):
            recovery.completed_bindings(self.root,d.context)


class RecoveryIntegrationTests(unittest.TestCase):
    def test_actual_worker_scoring_reuse_and_review_preparation_keep_distinct_source_roles(self):
        """Exercise the real callback chain and report schema, not just evaluate_unit."""
        import cv2
        import numpy as np
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            context, saved = full_fixture(root)
            output = root/original.OUTPUT_ROOT
            context.update(root=root,output_root=output,commit=NEW_COMMIT,spec_sha256=NEW_SPEC)
            context["manifest"]["output_root"] = original.OUTPUT_ROOT
            context["recovery_provenance"] = {"original_selection_commit":OLD_COMMIT,
                                              "original_selection_spec_sha256":OLD_SPEC,
                                              "preserved_inventory":{"path":"synthetic_inventory.json","sha256":"e"*64}}
            window = context["proposal"]["windows"][0]
            wid = window["window_id"]
            run,_ = context["inputs"][wid]
            window.update(start_frame_index=0,end_frame_index=24,source_video=run.source_video.to_dict())
            def reused(root,ctx,unit):
                observation = saved.load_new_observations(root,ctx,unit)
                observation["ranking_code_commit"] = OLD_COMMIT
                return observation
            def execute_score(receipt_path):
                with patch.object(recovery,"wait_for_supervisor"), \
                        patch.object(recovery,"load_context",return_value=context), \
                        patch.object(recovery,"_unchanged"), \
                        patch.object(recovery,"load_reused_observations",side_effect=reused), \
                        patch.dict(os.environ,{"BALL_RETENTION_RESULT_PATH":str(receipt_path)}):
                    return recovery._worker(root,root/"synthetic_manifest.json","score",wid)
            with patch.object(original,"load_saved_control",side_effect=saved.load_saved_control), \
                    patch.object(original,"load_new_observations",side_effect=AssertionError("Default mixed-commit loader used")), \
                    patch.object(original,"iter_ranked_frames",side_effect=AssertionError("Selection executed")):
                first = execute_score(output/"synthetic_score_receipt.json")
                score_path = output/"evaluation/windows"/(wid+".json")
                before = score_path.read_bytes()
                score = scoring.load_window_score(root,context,wid)
                new = [r for r in score["evaluation_reports"] if r["schema_version"] == scoring.REPORT_SCHEMA]
                self.assertEqual(len(new),20)
                self.assertTrue(all(r["ranking_code_commit"] == OLD_COMMIT and r["evaluator_code_commit"] == NEW_COMMIT for r in new))
                self.assertEqual(first["commit"],NEW_COMMIT)
                self.assertEqual(first["spec_sha256"],NEW_SPEC)
                self.assertEqual(first["artifacts"],[binding(root,score_path)])
                with patch.object(scoring,"evaluate_unit",side_effect=AssertionError("Completed score rerun")):
                    second = execute_score(output/"synthetic_reuse_receipt.json")
                self.assertEqual(first,second)
                self.assertEqual(score_path.read_bytes(),before)
                # Saved PNGs are fabricated source images. Preparation binds them;
                # existing renderer tests cover encoded clips and all final frames.
                prior = root/"saved_pngs"
                prior.mkdir()
                pixels = np.zeros((run.source_video.height_px,run.source_video.width_px,3),np.uint8)
                ok,encoded = cv2.imencode(".png",pixels)
                self.assertTrue(ok)
                assets,records = [],[]
                for index in range(25):
                    target = prior/f"frame_{index:06d}.png"
                    target.write_bytes(encoded.tobytes())
                    assets.append({"path":target.name,"sha256":sha256_file(target)})
                    records.append({"window_id":wid,"frame_index":index,"source_png":binding(root,target),
                                    "manifest_asset_relative_path":target.name})
                manifest = prior/"manifest.json"
                write_json(manifest,{"assets":assets})
                for record in records:
                    record["original_manifest"] = binding(root,manifest)
                context["proposal"]["saved_source_pngs"] = records
                captured = []
                def capture(root,prepared,target):
                    prepared.verify()
                    captured.append(prepared)
                    return {"synthetic_preparation_verified":True}
                with patch.object(review,"render_prepared_window",side_effect=capture):
                    result = review.render_window(root,context,wid,output/"review/windows"/wid,
                                                  observation_loader=reused)
                self.assertTrue(result["synthetic_preparation_verified"])
                prepared = captured[0]
                self.assertEqual(prepared.header["renderer_code_commit"],NEW_COMMIT)
                self.assertEqual(prepared.header["experiment_spec_sha256"],NEW_SPEC)
                self.assertEqual(prepared.header["recovery_provenance"],context["recovery_provenance"])
                self.assertEqual(len(prepared.sources),25)
                self.assertTrue(all(prepared.observations[arm,"all"]["ranking_code_commit"] == OLD_COMMIT for arm in ARMS))
                self.assertFalse((output/"review").exists())


class RecoveryBoundaryTests(unittest.TestCase):
    def test_select_and_audit_cannot_be_dispatched_through_recovery_runner(self):
        for stage in ("select","completion-audit","unknown"):
            with self.subTest(stage=stage),patch.object(recovery,"_metadata",side_effect=AssertionError("Metadata opened")):
                with self.assertRaisesRegex(ValueError,"verification, scoring and rendering only"):
                    recovery.run_recovery(Path.cwd(),Path.cwd()/"unused.json",stage=stage)
            with self.subTest(worker=stage),patch.object(recovery,"wait_for_supervisor",side_effect=AssertionError("Worker started")):
                with self.assertRaisesRegex(ValueError,"cannot dispatch selection"):
                    recovery._worker(Path.cwd(),Path.cwd()/"unused.json",stage,"")

    def test_dirty_checkpoint_and_nonempty_index_fail_before_authority_or_saved_reads(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            manifest = root/"configs/ball_tracking/crop_retention_experiments/synthetic.json"
            for dirty,index in ((" M source.py",""),("","source.py")):
                def git(root,*args):
                    return {("branch","--show-current"):"codex/ball-detector-baseline",
                            ("status","--porcelain=v1"):dirty,("diff","--cached","--name-only"):index}[args]
                with self.subTest(dirty=dirty,index=index),patch.object(original,"_git",side_effect=git), \
                        patch.object(recovery,"read_json",side_effect=AssertionError("Authority read before checkpoint guard")):
                    with self.assertRaisesRegex(ValueError,"clean committed checkpoint|Index must be empty"):
                        recovery._metadata(root,manifest,True)

    def test_missing_or_incomplete_recovery_certificate_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            with self.assertRaisesRegex(ValueError,"validation is missing"):
                recovery._validate_implementation(root,{"implementation_validation":None})
            path = root/"certificate.json"
            write_json(path,{"focused_tests_passed":True,"full_suite_passed":False})
            with self.assertRaisesRegex(ValueError,"validation is incomplete"):
                recovery._validate_implementation(root,{"implementation_validation":binding(root,path)})

    def test_recovery_certificate_requires_all_sources_tests_and_unchanged_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            files = [root/"src/module.py",root/"tests/test_module.py",root/"requirements.txt"]
            for path in files:
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text("# synthetic certified input\n",encoding="utf-8")
            certificate = {"focused_tests_passed":True,"full_suite_passed":True,
                           "resource_abort_and_resume_tests_passed":True,"independent_static_review_passed":True,
                           "recovery_proposal_sha256":recovery.RECOVERY_PROPOSAL_SHA256,
                           "preserved_inventory_sha256":"f"*64,
                           "source_bindings":[binding(root,p) for p in files],"evidence_bindings":[]}
            path = root/"certificate.json"
            write_json(path,certificate)
            manifest = {"implementation_validation":binding(root,path),"preserved_inventory":{"sha256":"f"*64}}
            with patch.object(original,"_git",return_value=""):
                recovery._validate_implementation(root,manifest)
                files[0].write_text("# changed after tests\n",encoding="utf-8")
                with self.assertRaisesRegex(ValueError,"Changed bound file"):
                    recovery._validate_implementation(root,manifest)
                certificate["source_bindings"].pop(1)
                write_json(path,certificate)
                manifest["implementation_validation"] = binding(root,path)
                with self.assertRaisesRegex(ValueError,"omits dependencies or tests"):
                    recovery._validate_implementation(root,manifest)

    def test_verify_preflight_requests_scoring_and_source_png_checks_after_supervisor_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            output = root/original.OUTPUT_ROOT
            context = {"root":root,"output_root":output,"proposal":{"windows":[]},
                       "commit":NEW_COMMIT,"spec_sha256":NEW_SPEC}
            order = []
            with patch.object(recovery,"wait_for_supervisor",side_effect=lambda:order.append("supervised")), \
                    patch.object(recovery,"load_context",side_effect=lambda *a,**k:(order.append("loaded"),context)[1]) as loader, \
                    patch.object(recovery,"_unchanged"), \
                    patch.dict(os.environ,{"BALL_RETENTION_RESULT_PATH":str(output/"preflight.result.json")}):
                result = recovery._worker(root,root/"manifest.json","preflight","verify")
            self.assertEqual(order,["supervised","loaded"])
            self.assertTrue(loader.call_args.kwargs["verify_scoring_inputs"])
            self.assertTrue(loader.call_args.kwargs["verify_review_inputs"])
            self.assertEqual(result["artifacts"],[])

    def test_dry_run_is_metadata_only_and_keeps_full_verification_supervised(self):
        with patch.object(recovery,"_metadata",return_value={"spec_sha256":NEW_SPEC}) as metadata, \
                patch.object(recovery,"load_context",side_effect=AssertionError("Unsupervised output inspection")), \
                patch.object(recovery,"run_supervised",side_effect=AssertionError("Dry run started worker")):
            result = recovery.run_recovery(Path.cwd(),Path.cwd()/"synthetic.json",dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertFalse(result["selection_executed"])
        self.assertFalse(metadata.call_args.args[2])


if __name__ == "__main__":
    unittest.main()
