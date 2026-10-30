"""CPU runner checks with actual resolution producers; no real weights or PNGs."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

from src.ball_tracking import completion_resolution_training as runner
from src.ball_tracking import completion_training_runtime as runtime
from src.ball_tracking import wasb_training as training

REPO = Path(__file__).resolve().parents[1]


class Store:
    resolution = runner.RESOLUTION
    value = None
    closed = 0
    def __init__(self, *args): pass
    def prepare(self): return {"blocks": [], "elapsed_seconds": 0., "source_video_decodes": 0}
    def example(self, triplet): return self.value
    def close(self): Store.closed += 1


class ResolutionRunnerTests(unittest.TestCase):
    def setUp(self):
        self.old_threads = torch.get_num_threads()
        torch.set_num_threads(1)
        self.addCleanup(torch.set_num_threads, self.old_threads)
        self.cuda_guard = patch.object(torch.cuda, "is_available", return_value=False)
        self.cuda_guard.start()
        self.addCleanup(self.cuda_guard.stop)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.output = self.root / "data/outputs/fit"
        self.base = self.root / "initial.pth"
        self.model = torch.nn.Linear(1, 1, bias=False)
        with torch.no_grad(): self.model.weight.zero_()
        training.save_checkpoint_once(self.base, {"model_state_dict": self.model.state_dict()})
        self.initial = runtime.binding(self.root, self.base)
        self.identity = {"recipe": {"sha256": "resolution"}, "resolution": runner.RESOLUTION}
        self.parent = {"initialization": {"checkpoint": self.initial}}
        self.recipe = {"output_root": "data/outputs/fit", "cache_root": "data/outputs/cache", "total_updates": 10,
            "parent_recipe": {"sha256": "parent"}, "control_completed": {"sha256": "control"}}
        self.package = {"training_triplets": [{"triplet_id": key} for key in "abc"]}
        self.schedule = {"epochs": [{"epoch": e, "batches": [["a", "b"], ["c"]]} for e in range(1, 21)]}
        image = runtime.normalized_tensor(np.full((432, 768, 3), 128, np.uint8))
        Store.value = (torch.cat([image] * 3), torch.zeros(3,432,768), torch.tensor([True,False,True]))
        Store.closed = 0
        self.validated, self.steps, self.parents = [], [], []
        self.producer = runner.resolution.validate_epoch

    def report(self, epoch, checkpoint):
        # Real new-resolution validation producer emits the complete schema;
        # an empty synthetic block list prevents pixels/model forward calls.
        report = self.producer(self.model, "cpu", Store(), {"validation_blocks": []}, epoch, checkpoint)
        for metrics in report["cohorts"].values():
            metrics.update(matched=10-epoch, wrong=epoch)
        return report

    def initialize(self, root, parent, nfhs):
        self.parents.append(parent)
        training.seed_runtime(1234)
        model = torch.nn.Linear(1,1,bias=False)
        model.load_state_dict(torch.load(self.base, weights_only=True)["model_state_dict"])
        optimizer = torch.optim.Adam(model.parameters(), lr=.0001, betas=(.9,.999), eps=1e-8, weight_decay=0)
        return model,"cpu",optimizer,training.freeze_batch_norm(model)

    def step(self, model, optimizer, inputs, targets, masks):
        self.steps.append(len(inputs))
        self.assertEqual(tuple(inputs.shape[1:]),(9,432,768))
        self.assertEqual(masks.tolist(),[[True,False,True]]*len(inputs))
        optimizer.zero_grad()
        loss=(model(inputs[:,0,:1,:1].reshape(-1,1))-1).square().mean()
        loss.backward()
        optimizer.step()
        return float(loss.detach()),1

    def validate(self, model, device, store, package, epoch, checkpoint):
        self.validated.append(epoch)
        torch.rand(2)  # Wrapper must restore training RNG even for this producer.
        return self.report(epoch,checkpoint)

    def stubs(self):
        stack=ExitStack()
        stack.enter_context(patch.object(runner,"preflight",return_value=(self.recipe,self.parent,self.package,self.schedule,{},self.identity)))
        stack.enter_context(patch.object(runner.frozen,"resources",return_value={"synthetic":True}))
        stack.enter_context(patch.object(runner.resolution,"FrameStore",Store))
        stack.enter_context(patch.object(runner.frozen.adaptation,"initialize",side_effect=self.initialize))
        stack.enter_context(patch.object(training,"training_step",side_effect=self.step))
        stack.enter_context(patch.object(runner.resolution,"validate_epoch",side_effect=self.validate))
        stack.enter_context(patch.object(runner.frozen.policy,"choose_checkpoint",side_effect=AssertionError("No historical NFHS selection")))
        stack.enter_context(patch.object(runner.frozen.policy,"should_stop",side_effect=AssertionError("No adaptive stop")))
        return stack

    def test_actual_producer_fresh_epoch_zero_fixed_budget_and_completed_consumer(self):
        with self.stubs():
            result=runner.execute(self.root,"synthetic")
            actual,audit=runner.audit_completed_result(self.root,"synthetic")
        self.assertEqual(self.validated,list(range(6)))
        self.assertEqual(self.steps,[2,1]*5)
        self.assertEqual(self.parents,[self.parent])
        self.assertEqual((result["completed_epochs"],result["completed_updates"]),(5,10))
        self.assertEqual(result["stop_reason"],"five_epoch_budget")
        self.assertFalse(result["selection_applied"])
        self.assertIsNone(result["selected_checkpoint"])
        self.assertEqual(actual,result)
        self.assertEqual(audit["validation_reports_checked"],6)
        self.assertEqual(len(result["checkpoints"]),5)
        baseline=json.loads((self.output/"validation/epoch_000.json").read_text())
        self.assertEqual(baseline["checkpoint"],self.initial)
        self.assertEqual(baseline["resolution"],runner.RESOLUTION)
        self.assertNotIn("reused_validation",baseline)
        durable=runner.frozen.load_state(self.output/"states/update_000010.pth",self.identity,self.schedule)
        runner.validate_augmentation_history(durable["losses"])
        self.assertEqual(len(durable["losses"][-1]["augmentation"]),1)
        self.assertEqual(durable["losses"][0]["augmentation"][0]["input_shape"],[9,432,768])
        self.assertEqual(set(torch.load(self.output/"checkpoints/epoch_005.pth",weights_only=True)),{"model_state_dict"})
        with self.stubs(),patch.object(runner.frozen.adaptation,"initialize",side_effect=AssertionError("No model")):
            self.assertEqual(runner.execute(self.root,"synthetic",resume=True),result)
            with self.assertRaisesRegex(ValueError,"unchanged --resume"):
                runner.execute(self.root,"synthetic")

    def test_completed_validation_not_repeated_after_interruption(self):
        real=runner.validation
        def interrupt(*args):
            report=real(*args)
            if args[-2]==1:raise RuntimeError("synthetic after-validation interruption")
            return report
        with self.stubs(),patch.object(runner,"validation",side_effect=interrupt):
            with self.assertRaisesRegex(RuntimeError,"after-validation"):
                runner.execute(self.root,"synthetic")
        before=(self.output/"validation/epoch_001.json").read_bytes()
        with self.stubs():result=runner.execute(self.root,"synthetic",resume=True)
        self.assertEqual(self.validated,list(range(6)))
        self.assertEqual((self.output/"validation/epoch_001.json").read_bytes(),before)
        self.assertEqual(result["completed_updates"],10)
        self.assertTrue((self.output/"states/update_000002.pth").is_file())
        self.assertEqual(len(list((self.output/"attempts").glob("*/failed.json"))),1)

    def test_unsaved_updates_replay_exact_draws_and_preserve_failure_history(self):
        actual_save=training.save_checkpoint_once
        def fail(path,value):
            if path.name=="update_000002.pth":raise RuntimeError("synthetic durability failure")
            return actual_save(path,value)
        with self.stubs(),patch.object(training,"save_checkpoint_once",side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,"durability"):
                runner.execute(self.root,"synthetic")
        first=next((self.output/"attempts").glob("*/updates.jsonl"))
        old=first.read_bytes()
        old_rows=[json.loads(line) for line in old.decode().splitlines() if json.loads(line)["event"]=="completed"]
        with self.stubs():runner.execute(self.root,"synthetic",resume=True)
        self.assertEqual(first.read_bytes(),old)
        new=next(p for p in (self.output/"attempts").glob("*/updates.jsonl") if p!=first)
        new_rows=[json.loads(line) for line in new.read_text().splitlines() if json.loads(line)["event"]=="completed"]
        for a,b in zip(old_rows,new_rows[:2]):
            self.assertEqual(a["augmentation"],b["augmentation"])
            self.assertEqual(a["loss"],b["loss"])
        self.assertEqual(self.validated,list(range(6)))
        restored=[json.loads(p.read_text()) for p in (self.output/"attempts").glob("*/restored.json")]
        self.assertTrue(any(r["restored_updates"]==0 and r["previous_unsaved_completed_count"]==2 for r in restored))
        self.assertTrue((self.output/"states/update_000000.pth").is_file())

    def test_validation_rng_preserved_and_512_or_reuse_cannot_be_published(self):
        before=torch.get_rng_state().clone()
        with patch.object(runner.resolution,"validate_epoch",side_effect=self.validate):
            report=runner.validation(self.root,self.output,self.identity,self.model,"cpu",None,{},0,self.initial)
        self.assertTrue(torch.equal(before,torch.get_rng_state()))
        for changed in ({**report,"resolution":{"width":512,"height":288,"target_radius":2.5}},
                        {**report,"reused_validation":{"source_report":"old"}}):
            with self.assertRaisesRegex(ValueError,"Fresh resolution"):
                runner.validate_report(changed,self.identity)

    def test_optimizer_restored_settings_are_checked(self):
        optimizer=torch.optim.Adam(self.model.parameters(),lr=.0001)
        runner.validate_optimizer(optimizer,require_fresh=True)
        saved=deepcopy(optimizer.state_dict())
        saved["param_groups"][0]["lr"] = .001
        optimizer.load_state_dict(saved)
        with self.assertRaisesRegex(ValueError,"Adam settings differ"):
            runner.validate_optimizer(optimizer)

    def test_tampered_draw_completion_and_identity_fail_closed(self):
        with self.stubs():result=runner.execute(self.root,"synthetic")
        state=runner.frozen.load_state(self.output/"states/update_000010.pth",self.identity,self.schedule)
        state["losses"][0]["augmentation"][0]["brightness_gain"]=1.1
        with self.assertRaisesRegex(ValueError,"draw differs"):runner.validate_augmentation_history(state["losses"])
        reports=[json.loads((self.root/b["path"]).read_text()) for b in result["validation_reports"]]
        for changed in ({**result,"epoch_zero_reused":True},{**result,"selected_checkpoint":result["final_checkpoint"]},
                        {**result,"stop_reason":"five_epochs_without_rank_improvement"}):
            with self.assertRaisesRegex(ValueError,"completion contract"):
                runner.validate_completion(self.root,self.recipe,self.identity,changed,reports)
        self.identity={**self.identity,"changed":True}
        with self.stubs(),patch.object(runner.resolution,"FrameStore",side_effect=AssertionError("No pixels")):
            with self.assertRaisesRegex(ValueError,"unchanged --resume"):runner.execute(self.root,"synthetic",resume=True)

    def test_real_parent_schedule_and_control_metadata_preflight(self):
        parent_path=REPO/"configs/ball_tracking/completion_campaign/primary_recipe_v0_1.json"
        parent=json.loads(parent_path.read_text())
        recipe={"schema_version":"wasb_resolution_recipe/v0.1","status":"frozen_before_model_execution",
            "parent_recipe":runtime.binding(REPO,parent_path),
            "control_completed":runtime.binding(REPO,REPO/"data/outputs/ball_tracking/wasb_augmentation_v0_1/fit_v0_1/completed.json"),
            "runtime":parent["runtime"],"max_epochs":5,"total_updates":7760,"resolution":runner.RESOLUTION,
            "training":runner.TRAINING,"augmentation":runner.augmentation.POLICY,"protected_evaluation_authorized":False,
            "output_root":runner.OUTPUT_ROOT,"cache_root":runner.CACHE_ROOT,
            "execution_plan":runtime.binding(REPO,REPO/"docs/ball_tracking_nba_resolution_experiment.md"),
            "user_authority":{"approval":"Synthetic metadata test; does not authorize execution"},
            "code_bindings":[runtime.binding(REPO,REPO/"src/ball_tracking"/name) for name in
                ["completion_resolution_training.py","wasb_resolution.py","wasb_augmentation.py","gpu_supervision.py"]]}
        folder=REPO/"data/outputs/t"
        with tempfile.TemporaryDirectory(dir=folder,prefix="resolution_preflight_test_") as temp:
            path=Path(temp)/"recipe.json"
            runtime.atomic_write_once(path,recipe)
            with patch.object(torch,"load",side_effect=AssertionError("No tensors")),patch.object(runner.resolution,"FrameStore",side_effect=AssertionError("No pixels")):
                _,_,package,schedule,_,identity=runner.preflight(REPO,path)
            self.assertEqual(len(package["training_triplets"]),3103)
            self.assertEqual([len(e["batches"]) for e in schedule["epochs"][:5]],[1552]*5)
            self.assertEqual(identity["resolution"],runner.RESOLUTION)
            for field,value in [("max_epochs",6),("cache_root",parent["cache_root"]),("training",{**runner.TRAINING,"learning_rate":.001})]:
                changed={**recipe,field:value};bad=Path(temp)/(field+".json")
                runtime.atomic_write_once(bad,changed)
                with self.assertRaises(ValueError):runner.preflight(REPO,bad)


if __name__=="__main__":unittest.main()
