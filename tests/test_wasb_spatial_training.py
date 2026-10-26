"""CPU spatial runner checks using accepted producer rows and real Adam state."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch

from src.ball_tracking import wasb_spatial_training as runner
from src.ball_tracking import completion_training_runtime as runtime
from src.ball_tracking import wasb_training as training
from src.ball_tracking.annotations import FrameAnnotation

REPO = Path(__file__).resolve().parents[1]


class Store:
    values = {}
    blocks = {}
    resolution = runner.RESOLUTION
    def __init__(self, *args):
        pass
    def prepare(self):
        return {"blocks":[], "elapsed_seconds":0., "source_video_decodes":0}
    def example(self, triplet):
        return self.values[triplet["triplet_id"]]
    def close(self):
        pass


class SpatialRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        primary = json.loads((REPO / "configs/ball_tracking/completion_campaign/primary_recipe_v0_1.json").read_text())
        cls.actual_package = json.loads((REPO / primary["package"]["path"]).read_text())

    def setUp(self):
        old_threads = torch.get_num_threads()
        torch.set_num_threads(1)
        self.addCleanup(torch.set_num_threads, old_threads)
        for name in ("is_available", "is_initialized"):
            guard = patch.object(torch.cuda, name, return_value=False)
            guard.start(); self.addCleanup(guard.stop)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / "data/outputs/spatial"
        block = deepcopy(self.actual_package["training_blocks"][0])
        rows = [deepcopy(t) for t in self.actual_package["training_triplets"] if t["block_id"] == block["block_id"]][:3]
        self.package = {"training_blocks":[block], "training_triplets":rows}
        Store.blocks = {block["block_id"]:block}
        keys = [t["triplet_id"] for t in rows]
        self.schedule = {"epochs":[{"epoch":e,"batches":[keys[:2],keys[2:]]} for e in range(1,21)]}
        # Synthetic pixels, actual accepted annotation/target producer contracts.
        pixels = np.full((432,768,3),128,np.uint8)
        image = runtime.normalized_tensor(pixels)
        frames = {f["source_frame_index"]:f for f in block["frames"]}
        bounds = SimpleNamespace(width_px=block["source_video"]["width_px"], height_px=block["source_video"]["height_px"])
        Store.values = {}
        for triplet in rows:
            targets = [runner.resolution.annotation_target(FrameAnnotation.from_mapping(frames[i]["annotation"],0,bounds),
                block["source_video"]["width_px"],block["source_video"]["height_px"]) for i in triplet["frame_indices"]]
            Store.values[triplet["triplet_id"]] = (torch.cat([image]*3), torch.from_numpy(np.stack([t[0] for t in targets])),
                torch.tensor([t[1] for t in targets]))
        self.source_identity = {"recipe":{"sha256":"synthetic_parent"}, "resolution":runner.RESOLUTION}
        self.validated, self.steps = [], []
        self.producer = runner.resolution.validate_epoch
        training.seed_runtime(1234)
        model = torch.nn.Linear(1,1,bias=False)
        with torch.no_grad(): model.weight.zero_()
        initial = self.root / "initial.pth"
        training.save_checkpoint_once(initial, {"model_state_dict":model.state_dict()})
        self.parent = {"initialization":{"checkpoint":runtime.binding(self.root,initial)}}
        optimizer = torch.optim.Adam(model.parameters(),lr=.0001)
        losses=[]
        for spec in self.schedule["epochs"][:5]:
            for index, ids in enumerate(spec["batches"],1):
                augmented = [runner.resolution.augment_example(Store.values[key],seed=1234,epoch=spec["epoch"],
                    batch_index=index,sample_index=j,triplet_id=key) for j,key in enumerate(ids)]
                examples,audits=zip(*augmented)
                inputs,targets,masks=(torch.stack([x[j] for x in examples]) for j in range(3))
                loss,gradients=self.step(model,optimizer,inputs,targets,masks)
                losses.append({"update":len(losses)+1,"epoch":spec["epoch"],"batch_index":index,"triplet_ids":ids,
                    "loss":loss,"gradient_parameter_count":gradients,"augmentation":list(audits)})
        checkpoint = self.root / "source/checkpoints/epoch_005.pth"
        training.save_checkpoint_once(checkpoint,{"model_state_dict":model.state_dict()})
        self.checkpoint = runtime.binding(self.root,checkpoint)
        self.source_state = self.root / "source/states/update_000010.pth"
        training.save_checkpoint_once(self.source_state,runner.frozen.state_payload(model,optimizer,self.source_identity,5,2,losses,{}))
        self.source_report = self.root / "source/validation/epoch_005.json"
        report = self.producer(model,"cpu",Store(),{"validation_blocks":[]},5,self.checkpoint)
        report["identity"] = self.source_identity
        runtime.atomic_write_once(self.source_report,report)
        cache = self.root / "source/cache_preparation.json"
        runtime.atomic_write_once(cache,Store().prepare())
        completed = self.root / "source/completed.json"
        runtime.atomic_write_once(completed,{"status":"synthetic_completed_parent"})
        self.recipe = {"output_root":"data/outputs/spatial","source_state":runtime.binding(self.root,self.source_state),
            "source_completed":runtime.binding(self.root,completed),"source_cache_preparation":runtime.binding(self.root,cache),
            "cache_root":"data/outputs/cache","initial_updates":10,"additional_updates":4,"total_updates":14,
            "start_epoch":5,"end_epoch":7}
        self.source = {"final_checkpoint":self.checkpoint}
        self.steps.clear()

    def identity(self):
        return {"recipe":{"sha256":"synthetic_spatial"},"arm":"spatial","source_identity":self.source_identity,
            "source_completed":self.recipe["source_completed"],"source_state":self.recipe["source_state"],
            "source_checkpoint":self.checkpoint,"source_validation_report":runtime.binding(self.root,self.source_report),
            "matched_control_completed":{"sha256":"synthetic_control"},
            "learning_rate_policy":runner.LEARNING_RATE_POLICY,"resolution":runner.RESOLUTION}

    def preflight(self, root, path):
        return self.recipe,self.parent,self.package,self.schedule,{},self.identity(),self.source

    def initialize(self, root, parent, nfhs):
        training.seed_runtime(1234)
        model=torch.nn.Linear(1,1,bias=False)
        model.load_state_dict(torch.load(self.root/"initial.pth",weights_only=True)["model_state_dict"])
        return model,"cpu",torch.optim.Adam(model.parameters(),lr=.0001),{}

    def step(self, model, optimizer, inputs, targets, masks):
        self.steps.append({"lr":optimizer.param_groups[0]["lr"],
            "before_step":next(iter(optimizer.state.values()))["step"].item() if optimizer.state else 0})
        self.assertEqual(tuple(inputs.shape[1:]),(9,432,768))
        self.assertTrue(bool(((targets==0)|(targets==1)).all()))
        self.assertTrue(bool(masks.all()))
        optimizer.zero_grad()
        loss=(model(inputs[:,0,:1,:1].reshape(-1,1))-(1+torch.rand(1))).square().mean()
        loss.backward(); optimizer.step()
        return float(loss.detach()),1

    def validate(self, model, device, store, package, epoch, checkpoint):
        self.validated.append(epoch)
        torch.rand(2)
        return self.producer(model,"cpu",store,{"validation_blocks":[]},epoch,checkpoint)

    def stubs(self):
        stack=ExitStack()
        stack.enter_context(patch.object(runner,"preflight",side_effect=self.preflight))
        stack.enter_context(patch.object(runner,"verify_owned_worker",return_value={"synthetic_cpu_owner":True}))
        stack.enter_context(patch.object(runner.frozen,"resources",return_value={"synthetic":True}))
        stack.enter_context(patch.object(runner.resolution,"FrameStore",Store))
        stack.enter_context(patch.object(runner.frozen.adaptation,"initialize",side_effect=self.initialize))
        stack.enter_context(patch.object(training,"training_step",side_effect=self.step))
        stack.enter_context(patch.object(runner.resolution,"validate_epoch",side_effect=self.validate))
        stack.enter_context(patch.object(runner.frozen.policy,"choose_checkpoint",side_effect=AssertionError("No selection")))
        return stack

    def run_fit(self, **kwargs):
        return runner.execute(self.root,"synthetic",monitor="data/outputs/monitor",**kwargs)

    def test_exact_parent_handoff_two_epoch_budget_and_actual_validation_consumer(self):
        source_bytes=self.source_state.read_bytes()
        with self.stubs():
            result=self.run_fit()
            actual,audit=runner.audit_completed_result(self.root,"synthetic")
        self.assertEqual(actual,result)
        self.assertEqual(self.validated,[6,7])
        self.assertEqual(self.steps[0],{"lr":.0001,"before_step":10})
        self.assertEqual((result["completed_updates"],result["optimizer_updates"],result["completed_epochs"]),(14,4,7))
        self.assertEqual(audit["validation_reports_checked"],3)
        self.assertEqual(len(result["checkpoints"]),2)
        self.assertEqual(self.source_state.read_bytes(),source_bytes)
        first=runner.frozen.load_state(self.root/result["initial_continuation_state"]["path"],self.identity(),self.schedule)
        parent=torch.load(self.source_state,map_location="cpu",weights_only=True)
        for key in ("model_state_dict","optimizer_state_dict","rng_state","losses"):
            self.assertTrue(runner.trees_equal(first[key],parent[key]),key)
        final=runner.frozen.load_state(self.root/result["resume_checkpoint"]["path"],self.identity(),self.schedule)
        self.assertEqual(final["losses"][:10],parent["losses"])
        self.assertEqual([r["epoch"] for r in final["losses"][10:]],[6,6,7,7])
        runner.validate_history(final["losses"],self.recipe,self.identity(),parent["losses"],self.package)
        for row in final["losses"][10:]:
            for sample,key in enumerate(row["triplet_ids"]):
                _,old_audit=runner.resolution.augment_example(Store.values[key],seed=1234,epoch=row["epoch"],
                    batch_index=row["batch_index"],sample_index=sample,triplet_id=key)
                self.assertEqual(row["augmentation"][sample],old_audit)
        with self.stubs(),patch.object(runner.frozen.adaptation,"initialize",side_effect=AssertionError("No new model")):
            self.assertEqual(self.run_fit(resume=True),result)

    def test_checkpoint_before_validation_resume_has_no_duplicate_steps(self):
        actual=runner.source_training.validation
        def fail(*args):
            if args[-2]==6: raise RuntimeError("before validation")
            return actual(*args)
        with self.stubs(),patch.object(runner.source_training,"validation",side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,"before validation"):self.run_fit()
        path=self.output/"checkpoints/epoch_006.pth"; old=path.read_bytes()
        with self.stubs():result=self.run_fit(resume=True)
        self.assertEqual(path.read_bytes(),old)
        self.assertEqual(self.validated,[6,7]); self.assertEqual(len(self.steps),4)
        self.assertEqual(result["completed_updates"],14)
        self.assertEqual(len(list((self.output/"attempts").glob("*/failed.json"))),1)

    def test_unsaved_replay_preserves_spatial_mirror_rng_and_old_failure(self):
        actual=training.save_checkpoint_once
        def fail(path,value):
            if path.name=="update_000012.pth":raise RuntimeError("durability failure")
            return actual(path,value)
        with self.stubs(),patch.object(training,"save_checkpoint_once",side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,"durability"):self.run_fit()
        old_log=next((self.output/"attempts").glob("*/updates.jsonl")); old_bytes=old_log.read_bytes()
        old=[json.loads(s) for s in old_log.read_text().splitlines() if json.loads(s)["event"]=="completed"]
        with self.stubs():self.run_fit(resume=True)
        new_log=next(p for p in (self.output/"attempts").glob("*/updates.jsonl") if p!=old_log)
        new=[json.loads(s) for s in new_log.read_text().splitlines() if json.loads(s)["event"]=="completed"]
        self.assertEqual(old_log.read_bytes(),old_bytes)
        for a,b in zip(old,new[:2],strict=True):
            self.assertEqual({k:v for k,v in a.items() if k!="recorded_at_utc"},{k:v for k,v in b.items() if k!="recorded_at_utc"})
        restored=[json.loads(p.read_text()) for p in (self.output/"attempts").glob("*/restored.json")]
        self.assertTrue(any(r["previous_unsaved_completed_count"]==2 for r in restored))
        self.assertTrue((self.output/"states/update_000010.pth").exists())

    def test_completed_validation_is_not_repeated_after_interruption(self):
        actual=runner.source_training.validation
        def fail(*args):
            result=actual(*args)
            if args[-2]==6:raise RuntimeError("after validation")
            return result
        with self.stubs(),patch.object(runner.source_training,"validation",side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,"after validation"):self.run_fit()
        path=self.output/"validation/epoch_006.json"; old=path.read_bytes()
        with self.stubs():self.run_fit(resume=True)
        self.assertEqual(self.validated,[6,7]); self.assertEqual(path.read_bytes(),old)

    def test_tampered_audit_budget_and_fresh_adam_rejected(self):
        with self.stubs():result=self.run_fit()
        state=runner.frozen.load_state(self.root/result["resume_checkpoint"]["path"],self.identity(),self.schedule)
        parent=torch.load(self.source_state,weights_only=True)
        state["losses"][-1]["spatial_augmentation"][0]["unexpected_tampering"]=True
        with self.assertRaises(ValueError):runner.validate_history(state["losses"],self.recipe,self.identity(),parent["losses"],self.package)
        reports=[json.loads((self.root/b["path"]).read_text()) for b in result["validation_reports"]]
        for key,value in (("optimizer_updates",14),("new_completed_epochs",5),("model_adopted",True)):
            with self.assertRaisesRegex(ValueError,"completion contract"):
                runner.validate_completion(self.root,self.recipe,self.identity(),{**result,key:value},reports)
        with self.assertRaisesRegex(ValueError,"nonempty Adam"):
            runner.validate_optimizer(torch.optim.Adam(torch.nn.Linear(1,1).parameters(),lr=.0001),.0001,10)
        with self.assertRaisesRegex(ValueError,"outside six and seven"):
            runner.validate_report({**reports[-1],"epoch":8},self.identity())

    def test_real_control_metadata_preflight_no_models_or_cache_pixels(self):
        control_path=REPO/"configs/ball_tracking/proposals/wasb_continuation_v0_1.json"
        control=json.loads(control_path.read_text())
        recipe={k:control[k] for k in ("source_recipe","source_completed","source_state","source_cache_preparation",
            "source_evaluation","cache_root","runtime","resolution","augmentation")}
        recipe.update(schema_version=runner.RECIPE_SCHEMA,status="frozen_before_model_execution",training=runner.TRAINING,
            spatial_augmentation=runner.spatial.POLICY,output_root=runner.OUTPUT_ROOT,
            matched_control_recipe=runtime.binding(REPO,control_path),
            matched_control_completed=runtime.binding(REPO,REPO/control["arms"]["constant"]["output_root"]/"completed.json"),
            start_epoch=5,end_epoch=7,initial_updates=7760,additional_updates=3104,total_updates=10864,
            protected_evaluation_authorized=False,new_labels=0,execution_plan=control["execution_plan"],
            user_authority={"approval":"Synthetic CPU metadata test, no model execution"},
            code_bindings=[runtime.binding(REPO,REPO/path) for path in ("src/ball_tracking/wasb_spatial_training.py",
                "src/ball_tracking/wasb_spatial_augmentation.py","src/ball_tracking/continuation_owned_guard.py","src/ball_tracking/gpu_supervision.py")])
        with tempfile.TemporaryDirectory(dir=REPO/"data/outputs/t",prefix="spatial_metadata_") as temporary:
            path=Path(temporary)/"recipe.json"; runtime.atomic_write_once(path,recipe)
            with patch.object(runner.source_training,"runtime_versions",return_value=control["runtime"]), \
                 patch.object(runner.frozen,"runtime_versions",return_value=control["runtime"]), \
                 patch.object(torch,"load",side_effect=AssertionError("No model/state tensors")), \
                 patch.object(runner.resolution,"FrameStore",side_effect=AssertionError("No pixel/cache arrays")):
                context=runner.preflight(REPO,path)
                self.assertEqual(context[5]["arm"],"spatial")
                self.assertEqual(context[5]["source_state"],control["source_state"])
                self.assertEqual([len(e["batches"]) for e in context[3]["epochs"][5:7]],[1552,1552])
                for key,value in (("additional_updates",7760),("end_epoch",10),("new_labels",1),
                                  ("source_state",control["source_completed"]),("matched_control_completed",control["source_completed"])):
                    bad=Path(temporary)/(key+".json"); runtime.atomic_write_once(bad,{**recipe,key:value})
                    with self.assertRaises(ValueError):runner.preflight(REPO,bad)


if __name__ == "__main__": unittest.main()
