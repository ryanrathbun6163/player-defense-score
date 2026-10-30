"""CPU continuation/recovery checks using real producer reports and Adam states."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

from src.ball_tracking import wasb_continuation_training as runner
from src.ball_tracking import completion_training_runtime as runtime
from src.ball_tracking import wasb_training as training

REPO = Path(__file__).resolve().parents[1]


class Store:
    value = None
    resolution = runner.RESOLUTION
    def __init__(self, *args):
        pass
    def prepare(self):
        return {"blocks": [], "elapsed_seconds": 0., "source_video_decodes": 0}
    def example(self, triplet):
        return self.value
    def close(self):
        pass


class ContinuationRunnerTests(unittest.TestCase):
    def setUp(self):
        old_threads = torch.get_num_threads()
        torch.set_num_threads(1)
        self.addCleanup(torch.set_num_threads, old_threads)
        for name in ("is_available", "is_initialized"):
            guard = patch.object(torch.cuda, name, return_value=False)
            guard.start()
            self.addCleanup(guard.stop)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.output = self.root / "data/outputs/constant"
        self.initial = self.root / "initial.pth"
        self.package = {"training_triplets": [{"triplet_id": key} for key in "abc"]}
        self.schedule = {"epochs": [{"epoch": e, "batches": [["a", "b"], ["c"]]} for e in range(1, 21)]}
        image = runtime.normalized_tensor(np.full((432, 768, 3), 128, np.uint8))
        Store.value = (torch.cat([image] * 3), torch.zeros(3, 432, 768), torch.tensor([True, False, True]))
        self.source_identity = {"recipe": {"sha256": "parent-resolution"}, "resolution": runner.RESOLUTION}
        self.validated, self.steps = [], []
        self.producer = runner.resolution.validate_epoch
        training.seed_runtime(1234)
        model = torch.nn.Linear(1, 1, bias=False)
        with torch.no_grad():
            model.weight.zero_()
        training.save_checkpoint_once(self.initial, {"model_state_dict": model.state_dict()})
        self.parent = {"initialization": {"checkpoint": runtime.binding(self.root, self.initial)}}
        optimizer = torch.optim.Adam(model.parameters(), lr=.0001)
        losses = []
        for spec in self.schedule["epochs"][:5]:
            for batch_index, ids in enumerate(spec["batches"], 1):
                augmented = [runner.resolution.augment_example(Store.value, seed=1234, epoch=spec["epoch"],
                    batch_index=batch_index, sample_index=j, triplet_id=key) for j, key in enumerate(ids)]
                examples, audits = zip(*augmented)
                inputs, targets, masks = (torch.stack([x[j] for x in examples]) for j in range(3))
                loss, gradients = self.step(model, optimizer, inputs, targets, masks)
                losses.append({"update":len(losses) + 1, "epoch":spec["epoch"], "batch_index":batch_index,
                    "triplet_ids":ids, "loss":loss, "gradient_parameter_count":gradients, "augmentation":list(audits)})
        self.source_checkpoint = self.root / "source/checkpoints/epoch_005.pth"
        training.save_checkpoint_once(self.source_checkpoint, {"model_state_dict":model.state_dict()})
        self.checkpoint = runtime.binding(self.root, self.source_checkpoint)
        self.source_state = self.root / "source/states/update_000010.pth"
        training.save_checkpoint_once(self.source_state, runner.frozen.state_payload(model, optimizer, self.source_identity, 5, 2, losses, {}))
        self.source_report = self.root / "source/validation/epoch_005.json"
        report = self.producer(model, "cpu", Store(), {"validation_blocks": []}, 5, self.checkpoint)
        report["identity"] = self.source_identity
        runtime.atomic_write_once(self.source_report, report)
        self.cache_path = self.root / "source/cache_preparation.json"
        runtime.atomic_write_once(self.cache_path, Store().prepare())
        self.source_complete = self.root / "source/completed.json"
        runtime.atomic_write_once(self.source_complete, {"status":"synthetic_completed_parent"})
        self.recipe = {"arms":{name:{"output_root":f"data/outputs/{name}", "learning_rate":policy} for name, policy in runner.ARMS.items()},
            "source_state":runtime.binding(self.root, self.source_state),
            "source_completed":runtime.binding(self.root, self.source_complete),
            "source_cache_preparation":runtime.binding(self.root, self.cache_path),
            "cache_root":"data/outputs/cache", "initial_updates":10, "additional_updates":10,
            "total_updates":20, "start_epoch":5, "end_epoch":10}
        self.source = {"final_checkpoint":self.checkpoint}
        self.steps.clear()

    def identity(self, arm):
        return {"recipe":{"sha256":"continuation"}, "arm":arm, "source_identity":self.source_identity,
            "source_completed":self.recipe["source_completed"], "source_state":self.recipe["source_state"],
            "source_checkpoint":self.checkpoint, "source_validation_report":runtime.binding(self.root, self.source_report),
            "learning_rate_policy":runner.ARMS[arm], "resolution":runner.RESOLUTION}

    def preflight(self, root, path, arm):
        return self.recipe, self.parent, self.package, self.schedule, {}, self.identity(arm), self.source

    def initialize(self, root, parent, nfhs):
        training.seed_runtime(1234)
        model = torch.nn.Linear(1,1,bias=False)
        model.load_state_dict(torch.load(self.initial, weights_only=True)["model_state_dict"])
        optimizer = torch.optim.Adam(model.parameters(), lr=.0001)
        return model, "cpu", optimizer, {}

    def step(self, model, optimizer, inputs, targets, masks):
        self.steps.append({"lr":optimizer.param_groups[0]["lr"],
            "before_step":next(iter(optimizer.state.values()))["step"].item() if optimizer.state else 0})
        self.assertEqual(tuple(inputs.shape[1:]), (9,432,768))
        self.assertEqual(masks.tolist(), [[True,False,True]] * len(inputs))
        optimizer.zero_grad()
        loss = (model(inputs[:,0,:1,:1].reshape(-1,1)) - (1 + torch.rand(1))).square().mean()
        loss.backward()
        optimizer.step()
        return float(loss.detach()), 1

    def validate(self, model, device, store, package, epoch, checkpoint):
        self.validated.append(epoch)
        torch.rand(2)
        return self.producer(model, "cpu", store, {"validation_blocks":[]}, epoch, checkpoint)

    def stubs(self):
        stack = ExitStack()
        stack.enter_context(patch.object(runner, "preflight", side_effect=self.preflight))
        stack.enter_context(patch.object(runner.frozen, "resources", return_value={"synthetic":True}))
        stack.enter_context(patch.object(runner.resolution, "FrameStore", Store))
        stack.enter_context(patch.object(runner.frozen.adaptation, "initialize", side_effect=self.initialize))
        stack.enter_context(patch.object(training, "training_step", side_effect=self.step))
        stack.enter_context(patch.object(runner.resolution, "validate_epoch", side_effect=self.validate))
        stack.enter_context(patch.object(runner.frozen.policy, "choose_checkpoint", side_effect=AssertionError("No old selection veto")))
        return stack

    def test_actual_parent_state_handoff_absolute_schedule_and_completion_consumer(self):
        source_bytes = self.source_state.read_bytes()
        with self.stubs():
            result = runner.execute(self.root, "synthetic", "constant")
            actual, audit = runner.audit_completed_result(self.root, "synthetic", "constant")
        self.assertEqual(actual, result)
        self.assertEqual(self.validated, list(range(6,11)))
        self.assertEqual(self.steps[0], {"lr":.0001, "before_step":10})
        self.assertEqual((result["completed_updates"], result["optimizer_updates"], result["completed_epochs"]), (20,10,10))
        self.assertEqual(audit["validation_reports_checked"], 6)
        self.assertEqual(len(result["checkpoints"]), 5)
        self.assertFalse(result["model_adopted"])
        self.assertEqual(self.source_state.read_bytes(), source_bytes)
        first = runner.frozen.load_state(self.root / result["initial_continuation_state"]["path"], self.identity("constant"), self.schedule)
        parent = torch.load(self.source_state, map_location="cpu", weights_only=True)
        for key in ("model_state_dict", "optimizer_state_dict", "rng_state", "losses"):
            self.assertTrue(runner.trees_equal(first[key], parent[key]), key)
        final = runner.frozen.load_state(self.root / result["resume_checkpoint"]["path"], self.identity("constant"), self.schedule)
        self.assertEqual(final["losses"][:10], parent["losses"])
        self.assertEqual([r["epoch"] for r in final["losses"][10:]], [6,6,7,7,8,8,9,9,10,10])
        self.assertEqual([r["continuation_update"] for r in final["losses"][10:]], list(range(1,11)))
        reused = json.loads((self.output / "validation/epoch_005.json").read_text())
        self.assertEqual(reused, runner.source_report(self.root, self.identity("constant")))
        with self.stubs(), patch.object(runner.frozen.adaptation, "initialize", side_effect=AssertionError("No model")):
            self.assertEqual(runner.execute(self.root, "synthetic", "constant", resume=True), result)

    def test_two_arms_start_identically_then_only_learning_rate_policy_differs(self):
        results = {}
        with self.stubs():
            for arm in runner.ARMS:
                results[arm] = runner.execute(self.root, "synthetic", arm)
        states = {arm:torch.load(self.root / result["resume_checkpoint"]["path"], weights_only=True) for arm,result in results.items()}
        constant, cosine = (states[arm]["losses"][10:] for arm in runner.ARMS)
        self.assertEqual(constant[0], cosine[0])
        self.assertEqual([r["augmentation"] for r in constant], [r["augmentation"] for r in cosine])
        self.assertEqual([r["triplet_ids"] for r in constant], [r["triplet_ids"] for r in cosine])
        self.assertEqual(cosine[0]["learning_rate"], .0001)
        self.assertEqual(cosine[-1]["learning_rate"], .00001)
        self.assertTrue(all(a["learning_rate"] > b["learning_rate"] for a,b in zip(cosine, cosine[1:])))
        self.assertFalse(runner.trees_equal(states["constant"]["model_state_dict"], states["cosine"]["model_state_dict"]))

    def test_checkpoint_before_validation_interruption_resumes_without_duplicate_training(self):
        actual = runner.source_training.validation
        interrupted = False
        def fail(*args):
            nonlocal interrupted
            if args[-2] == 6 and not interrupted:
                interrupted = True
                raise RuntimeError("synthetic before validation")
            return actual(*args)
        with self.stubs(), patch.object(runner.source_training, "validation", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "before validation"):
                runner.execute(self.root, "synthetic", "cosine")
        saved = self.root / "data/outputs/cosine/checkpoints/epoch_006.pth"
        before = saved.read_bytes()
        with self.stubs():
            result = runner.execute(self.root, "synthetic", "cosine", resume=True)
        self.assertEqual(saved.read_bytes(), before)
        self.assertEqual(self.validated, list(range(6,11)))
        self.assertEqual(len(self.steps), 10)
        self.assertEqual(result["completed_updates"], 20)
        self.assertEqual(len(list((self.root / "data/outputs/cosine/attempts").glob("*/failed.json"))), 1)

    def test_unsaved_updates_replay_exact_loss_lr_augmentation_and_rng(self):
        actual = training.save_checkpoint_once
        def fail(path, value):
            if path.name == "update_000012.pth":
                raise RuntimeError("synthetic durability failure")
            return actual(path, value)
        with self.stubs(), patch.object(training, "save_checkpoint_once", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "durability"):
                runner.execute(self.root, "synthetic", "cosine")
        output = self.root / "data/outputs/cosine"
        old_log = next((output / "attempts").glob("*/updates.jsonl"))
        old_bytes = old_log.read_bytes()
        old = [json.loads(line) for line in old_log.read_text().splitlines() if json.loads(line)["event"] == "completed"]
        with self.stubs():
            runner.execute(self.root, "synthetic", "cosine", resume=True)
        new_log = next(path for path in (output / "attempts").glob("*/updates.jsonl") if path != old_log)
        new = [json.loads(line) for line in new_log.read_text().splitlines() if json.loads(line)["event"] == "completed"]
        self.assertEqual(old_log.read_bytes(), old_bytes)
        for a,b in zip(old, new[:2]):
            self.assertEqual({k:v for k,v in a.items() if k != "recorded_at_utc"}, {k:v for k,v in b.items() if k != "recorded_at_utc"})
        restored = [json.loads(path.read_text()) for path in (output / "attempts").glob("*/restored.json")]
        self.assertTrue(any(row["previous_unsaved_completed_count"] == 2 for row in restored))
        self.assertTrue((output / "states/update_000010.pth").is_file())

    def test_completed_validation_is_not_repeated_after_interruption(self):
        actual = runner.source_training.validation
        def fail(*args):
            report = actual(*args)
            if args[-2] == 6:
                raise RuntimeError("synthetic after validation")
            return report
        with self.stubs(), patch.object(runner.source_training, "validation", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "after validation"):
                runner.execute(self.root, "synthetic", "constant")
        path = self.output / "validation/epoch_006.json"
        before = path.read_bytes()
        with self.stubs():
            runner.execute(self.root, "synthetic", "constant", resume=True)
        self.assertEqual(self.validated, list(range(6,11)))
        self.assertEqual(path.read_bytes(), before)

    def test_missing_adam_history_and_tampered_lr_report_fail_closed(self):
        with self.stubs():
            result = runner.execute(self.root, "synthetic", "cosine")
        identity = self.identity("cosine")
        final = runner.frozen.load_state(self.root / result["resume_checkpoint"]["path"], identity, self.schedule)
        original = torch.load(self.source_state, weights_only=True)["losses"]
        final["losses"][-1]["learning_rate"] = .0001
        with self.assertRaisesRegex(ValueError, "learning-rate"):
            runner.validate_history(final["losses"], self.recipe, identity, original)
        model = torch.nn.Linear(1,1)
        with self.assertRaisesRegex(ValueError, "nonempty Adam"):
            runner.validate_optimizer(torch.optim.Adam(model.parameters(), lr=.0001), .0001, 10)
        reused = runner.source_report(self.root, identity)
        with self.assertRaisesRegex(ValueError, "Reused epoch-five"):
            runner.validate_report(reused, identity)
        reports = [json.loads((self.root / b["path"]).read_text()) for b in result["validation_reports"]]
        for field,value in (("initial_optimizer","fresh_Adam"),("optimizer_updates",20),("model_adopted",True)):
            with self.assertRaisesRegex(ValueError, "completion contract"):
                runner.validate_completion(self.root, self.recipe, identity, {**result,field:value}, reports)
        reports[0]["cohorts"]["nba_validation"]["matched"] = 999
        with self.assertRaisesRegex(ValueError, "source transport"):
            runner.validate_completion(self.root, self.recipe, identity, result, reports)

    def test_exact_learning_rate_endpoints_and_invalid_budget(self):
        for arm, policy in runner.ARMS.items():
            self.assertEqual(runner.learning_rate(policy,1,7760), .0001)
            self.assertEqual(runner.learning_rate(policy,7760,7760), policy["final"])
        for index in (0,7761,1.5):
            with self.assertRaises(ValueError):
                runner.learning_rate(runner.ARMS["cosine"], index, 7760)

    def test_real_metadata_preflight_consumes_parent_without_models_or_cache_arrays(self):
        source_path = REPO / "configs/ball_tracking/proposals/wasb_resolution_v0_1.json"
        source_recipe = json.loads(source_path.read_text())
        source_completion_path = REPO / source_recipe["output_root"] / "completed.json"
        source_completion = json.loads(source_completion_path.read_text())
        recipe = {"schema_version":runner.RECIPE_SCHEMA, "status":"frozen_before_model_execution",
            "source_recipe":runtime.binding(REPO, source_path),
            "source_completed":runtime.binding(REPO, source_completion_path),
            "source_state":source_completion["resume_checkpoint"],
            "source_cache_preparation":runtime.binding(REPO, source_completion_path.parent / "cache_preparation.json"),
            "runtime":source_recipe["runtime"], "training":runner.TRAINING,
            "resolution":runner.RESOLUTION, "augmentation":runner.source_training.augmentation.POLICY,
            "start_epoch":5, "end_epoch":10, "initial_updates":7760,
            "additional_updates":7760, "total_updates":15520, "cache_root":runner.CACHE_ROOT,
            "protected_evaluation_authorized":False, "new_labels":0,
            "execution_plan":source_recipe["execution_plan"],
            "user_authority":{"approval":"Synthetic metadata test; no training authority"},
            "code_bindings":[runtime.binding(REPO, REPO / path) for path in
                ("src/ball_tracking/wasb_continuation_training.py", "src/ball_tracking/gpu_supervision.py")],
            "arms":{name:{"learning_rate":policy, "output_root":f"{runner.OUTPUT_ROOT}/{name}/fit_v0_1"}
                    for name,policy in runner.ARMS.items()}}
        with tempfile.TemporaryDirectory(dir=REPO / "data/outputs/t", prefix="continuation_metadata_") as temporary:
            path = Path(temporary) / "recipe.json"
            runtime.atomic_write_once(path, recipe)
            # Existing runtime_versions calls cudnn.version. Stub only version
            # discovery here: this test concerns actual metadata transport.
            with patch.object(runner.source_training, "runtime_versions", return_value=source_recipe["runtime"]), \
                 patch.object(runner.frozen, "runtime_versions", return_value=source_recipe["runtime"]), \
                 patch.object(torch, "load", side_effect=AssertionError("No tensor loads")), \
                 patch.object(runner.resolution, "FrameStore", side_effect=AssertionError("No pixels/cache arrays")):
                contexts = [runner.preflight(REPO, path, arm) for arm in runner.ARMS]
                self.assertEqual([context[5]["arm"] for context in contexts], list(runner.ARMS))
                self.assertEqual(contexts[0][5]["source_state"], contexts[1][5]["source_state"])
                self.assertEqual(len(contexts[0][2]["training_triplets"]), 3103)
                self.assertEqual([len(e["batches"]) for e in contexts[0][3]["epochs"][5:10]], [1552] * 5)
                for field, value in (("additional_updates",15520),("end_epoch",11),("new_labels",1),
                                     ("source_state",source_recipe["readiness"])):
                    bad = Path(temporary) / (field + ".json")
                    runtime.atomic_write_once(bad, {**recipe,field:value})
                    with self.assertRaises(ValueError):
                        runner.preflight(REPO, bad, "constant")


if __name__ == "__main__":
    unittest.main()
