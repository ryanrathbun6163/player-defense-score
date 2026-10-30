"""Synthetic runner/real producer transport checks; no real model, CUDA or pixels."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

from src.ball_tracking import completion_augmentation_training as runner
from src.ball_tracking import completion_training_runtime as runtime
from src.ball_tracking import wasb_training as training

REPO = Path(__file__).resolve().parents[1]


class Store:
    example_value = None
    closed = 0

    def __init__(self, *args):
        pass

    def prepare(self):
        return {"blocks": [], "elapsed_seconds": 0., "source_video_decodes": 0}

    def example(self, triplet):
        return self.example_value

    def close(self):
        Store.closed += 1


class AugmentationRunnerTests(unittest.TestCase):
    def setUp(self):
        self.old_threads = torch.get_num_threads()
        torch.set_num_threads(1)
        self.addCleanup(torch.set_num_threads, self.old_threads)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.out = self.root / "data/outputs/fit"
        self.base = self.root / "initial.pth"
        self.model = torch.nn.Linear(1, 1, bias=False)
        with torch.no_grad():
            self.model.weight.zero_()
        training.save_checkpoint_once(self.base, {"model_state_dict": self.model.state_dict()})
        self.initial = runtime.binding(self.root, self.base)
        self.parent_identity = {"recipe": {"sha256": "original"}, "package_sha256": "package", "schedule_sha256": "schedule"}
        self.identity = {"parent_identity": self.parent_identity, "recipe": {"sha256": "augmentation"}}
        self.parent = {"initialization": {"checkpoint": self.initial}}
        self.recipe = {"output_root": "data/outputs/fit", "cache_root": "data/outputs/cache", "total_updates": 10,
            "parent_recipe": {"sha256": "parent"}, "control_completed": {"sha256": "control"}}
        self.package = {"training_triplets": [{"triplet_id": key} for key in "abc"]}
        self.schedule = {"epochs": [{"epoch": e, "batches": [["a", "b"], ["c"]]} for e in range(1, 21)]}
        # Use actual frozen normalization. Synthetic RGB only, no repository PNGs.
        image = runtime.normalized_tensor(np.full((288, 512, 3), 128, np.uint8))
        Store.example_value = (torch.cat([image] * 3), torch.zeros(3, 288, 512), torch.tensor([True, False, True]))
        Store.closed = 0
        self.validated, self.steps, self.initialized_parents = [], [], []
        self.producer = runtime.validate_epoch
        self.original = self.report(0, self.initial)
        self.original["identity"] = self.parent_identity
        self.original_path = self.root / "control_epoch000.json"
        runtime.atomic_write_once(self.original_path, self.original)

    def report(self, epoch, checkpoint):
        # Actual validation producer supplies its full schema and policy fields;
        # the empty synthetic package prevents any image access or forward call.
        report = self.producer(self.model, "cpu", None, {"validation_blocks": []}, epoch, checkpoint)
        for metrics in report["cohorts"].values():
            metrics.update(matched=10 + epoch, wrong=0)
        return report

    def initialize(self, root, parent, nfhs):
        self.initialized_parents.append(parent)
        training.seed_runtime(1234)
        model = torch.nn.Linear(1, 1, bias=False)
        model.load_state_dict(torch.load(self.base, weights_only=True)["model_state_dict"])
        optimizer = torch.optim.Adam(model.parameters(), lr=.0001)
        self.assertFalse(optimizer.state)
        return model, "cpu", optimizer, training.freeze_batch_norm(model)

    def step(self, model, optimizer, inputs, targets, masks):
        self.steps.append(len(inputs))
        self.assertEqual(masks.tolist(), [[True, False, True]] * len(inputs))
        optimizer.zero_grad()
        loss = (model(inputs[:, 0, :1, :1].reshape(-1, 1)) - 1).square().mean()
        loss.backward()
        optimizer.step()
        return float(loss.detach()), 1

    def validate(self, model, device, store, package, epoch, checkpoint):
        self.validated.append(epoch)
        return self.report(epoch, checkpoint)

    def stubs(self):
        stack = ExitStack()
        stack.enter_context(patch.object(runner, "preflight", return_value=(self.recipe, self.parent, self.package, self.schedule, {}, self.identity)))
        stack.enter_context(patch.object(runner, "read_control", return_value=(
            {"validation_reports": [runtime.binding(self.root, self.original_path)]}, [self.original])))
        stack.enter_context(patch.object(runner.frozen, "resources", return_value={"synthetic": True}))
        stack.enter_context(patch.object(runtime, "FrameStore", Store))
        stack.enter_context(patch.object(runner.frozen.adaptation, "initialize", side_effect=self.initialize))
        stack.enter_context(patch.object(training, "training_step", side_effect=self.step))
        stack.enter_context(patch.object(runtime, "validate_epoch", side_effect=self.validate))
        return stack

    def test_real_producer_reports_new_schema_fixed_budget_and_consumer_accept_late_winner(self):
        before = self.original_path.read_bytes()
        with self.stubs():
            result = runner.execute(self.root, "synthetic")
            selected, audit = runner.audit_completed_result(self.root, "synthetic")
        self.assertEqual(self.validated, [1, 2, 3, 4, 5])
        self.assertEqual(self.steps, [2, 1] * 5)
        self.assertEqual(self.initialized_parents, [self.parent])
        self.assertEqual((result["completed_epochs"], result["completed_updates"]), (5, 10))
        self.assertEqual(result["stop_reason"], "five_epoch_budget")
        self.assertEqual(result["selection"]["selected_epoch"], 5)
        self.assertFalse(runner.frozen.policy.should_stop(5, 5))
        self.assertEqual(selected["checkpoint"], result["final_checkpoint"])
        self.assertEqual(audit["status"], "passed")
        self.assertEqual(self.original_path.read_bytes(), before)
        baseline = json.loads((self.out / "validation/epoch_000.json").read_text())
        self.assertEqual(baseline["identity"], self.identity)
        self.assertEqual(baseline["reused_validation"]["source_identity"], self.parent_identity)
        self.assertEqual(baseline["reused_validation"]["new_model_calls"], 0)
        restored = deepcopy(baseline)
        restored["identity"] = restored.pop("reused_validation")["source_identity"]
        self.assertEqual(restored, self.original)
        durable = runner.frozen.load_state(self.out / "states/update_000010.pth", self.identity, self.schedule)
        runner.validate_augmentation_history(durable["losses"])
        self.assertEqual(len(durable["losses"][-1]["augmentation"]), 1)
        self.assertEqual(set(torch.load(self.out / "checkpoints/epoch_005.pth", weights_only=True)), {"model_state_dict"})
        with self.stubs(), patch.object(runner.frozen.adaptation, "initialize", side_effect=AssertionError("No model")):
            self.assertEqual(runner.execute(self.root, "synthetic", resume=True), result)
            with self.assertRaisesRegex(ValueError, "unchanged --resume"):
                runner.execute(self.root, "synthetic")

    def test_completed_validation_is_not_repeated_after_interruption(self):
        real = runner.frozen.validation

        def interrupt(*args):
            report = real(*args)
            if args[-2] == 1:
                raise RuntimeError("synthetic after-validation interruption")
            return report

        with self.stubs(), patch.object(runner.frozen, "validation", side_effect=interrupt):
            with self.assertRaisesRegex(RuntimeError, "after-validation"):
                runner.execute(self.root, "synthetic")
        saved = (self.out / "validation/epoch_001.json").read_bytes()
        with self.stubs():
            result = runner.execute(self.root, "synthetic", resume=True)
        self.assertEqual(self.validated, [1, 2, 3, 4, 5])
        self.assertEqual(result["selection"]["selected_epoch"], 5)
        self.assertEqual((self.out / "validation/epoch_001.json").read_bytes(), saved)
        self.assertTrue((self.out / "states/update_000002.pth").exists())
        self.assertEqual(len(list((self.out / "attempts").glob("*/failed.json"))), 1)

    def test_unsaved_replay_keeps_exact_augmentation_draw_and_failed_attempt(self):
        actual_save = training.save_checkpoint_once

        def fail(path, value):
            if path.name == "update_000002.pth":
                raise RuntimeError("synthetic durability failure")
            return actual_save(path, value)

        with self.stubs(), patch.object(training, "save_checkpoint_once", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "durability"):
                runner.execute(self.root, "synthetic")
        first = next((self.out / "attempts").glob("*/updates.jsonl"))
        before = first.read_bytes()
        old_rows = [json.loads(line) for line in before.decode().splitlines() if json.loads(line)["event"] == "completed"]
        with self.stubs():
            runner.execute(self.root, "synthetic", resume=True)
        self.assertEqual(first.read_bytes(), before)
        new = next(p for p in (self.out / "attempts").glob("*/updates.jsonl") if p != first)
        new_rows = [json.loads(line) for line in new.read_text().splitlines() if json.loads(line)["event"] == "completed"]
        self.assertEqual([r["augmentation"] for r in old_rows], [r["augmentation"] for r in new_rows[:2]])
        restored = [json.loads(p.read_text()) for p in (self.out / "attempts").glob("*/restored.json")]
        self.assertTrue(any(r["restored_updates"] == 0 and r["previous_unsaved_completed_count"] == 2 for r in restored))
        self.assertTrue((self.out / "states/update_000000.pth").is_file())

    def test_tampered_draw_and_identity_are_rejected_before_model(self):
        with self.stubs():
            runner.execute(self.root, "synthetic")
        path = self.out / "states/update_000010.pth"
        state = runner.frozen.load_state(path, self.identity, self.schedule)
        state["losses"][0]["augmentation"][0]["brightness_gain"] = 1.1
        with self.assertRaisesRegex(ValueError, "draw differs"):
            runner.validate_augmentation_history(state["losses"])
        self.identity = {**self.identity, "changed": True}
        with self.stubs(), patch.object(runtime, "FrameStore", side_effect=AssertionError("No cache")):
            with self.assertRaisesRegex(ValueError, "unchanged --resume"):
                runner.execute(self.root, "synthetic", resume=True)

    def test_new_schema_rejects_old_stopping_semantics_and_fake_reused_trained_epoch(self):
        with self.stubs():
            result = runner.execute(self.root, "synthetic")
        reports = [json.loads((self.root / b["path"]).read_text()) for b in result["validation_reports"]]
        changed = {**result, "stop_reason": "five_epochs_without_rank_improvement"}
        with self.assertRaisesRegex(ValueError, "completion contract"):
            runner.validate_completion(self.root, self.recipe, self.identity, changed, reports)
        reports[1]["reused_validation"] = reports[0]["reused_validation"]
        with self.assertRaisesRegex(ValueError, "newly produced"):
            runner.validate_completion(self.root, self.recipe, self.identity, result, reports)

    def test_actual_control_package_schedule_and_bindings_metadata_preflight(self):
        # Real saved producer records are read as JSON/hash bytes only. No model
        # tensors, source pixels, protected labels or inference are loaded.
        parent_path = REPO / "configs/ball_tracking/completion_campaign/primary_recipe_v0_1.json"
        parent = json.loads(parent_path.read_text())
        recipe = {"schema_version": "wasb_augmentation_recipe/v0.1", "status": "frozen_before_model_execution",
            "parent_recipe": runtime.binding(REPO, parent_path),
            "control_completed": runtime.binding(REPO, REPO / "data/outputs/ball_tracking/completion_campaign_v0_1/primary_fit_v0_1/completed.json"),
            "runtime": parent["runtime"], "max_epochs": 5, "total_updates": 7760,
            "augmentation": runner.augmentation.POLICY, "protected_evaluation_authorized": False,
            "output_root": runner.OUTPUT_ROOT, "cache_root": parent["cache_root"],
            "execution_plan": runtime.binding(REPO, REPO / "docs/ball_tracking_wasb_augmentation_experiment.md"),
            "user_authority": {"approval": "Synthetic metadata test; does not authorize execution"},
            "code_bindings": [runtime.binding(REPO, REPO / "src/ball_tracking" / name) for name in
                              ["completion_augmentation_training.py", "wasb_augmentation.py", "gpu_supervision.py"]]}
        folder = REPO / "data/outputs/t"
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=folder, prefix="augmentation_preflight_test_") as temp:
            path = Path(temp) / "recipe.json"
            runtime.atomic_write_once(path, recipe)
            with patch.object(torch, "load", side_effect=AssertionError("No model load")), \
                 patch.object(runtime, "FrameStore", side_effect=AssertionError("No pixels")):
                _, _, package, schedule, _, identity = runner.preflight(REPO, path)
            self.assertEqual(len(package["training_triplets"]), 3103)
            self.assertEqual([len(e["batches"]) for e in schedule["epochs"][:5]], [1552] * 5)
            self.assertEqual(identity["executed_epochs_sha256"], runner.canonical(schedule["epochs"][:5]))
            changed = {**recipe, "max_epochs": 6}
            bad = Path(temp) / "changed.json"
            runtime.atomic_write_once(bad, changed)
            with self.assertRaisesRegex(ValueError, "budget differs"):
                runner.preflight(REPO, bad)


if __name__ == "__main__":
    unittest.main()
