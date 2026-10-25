"""Synthetic runner transport/recovery checks; no real data, CUDA or WASB model."""
from contextlib import ExitStack
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch

from src.ball_tracking import completion_training as runner
from src.ball_tracking import completion_training_policy as policy
from src.ball_tracking import completion_training_runtime as runtime
from src.ball_tracking import wasb_training as training


class Store:
    calls = 0
    closed = 0

    def __init__(self, *args):
        pass

    def prepare(self):
        Store.calls += 1
        return {"blocks": [], "elapsed_seconds": Store.calls, "source_video_decodes": 0}

    def example(self, triplet):
        return torch.ones(1), torch.ones(1), torch.ones(1, dtype=torch.bool)

    def close(self):
        Store.closed += 1


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out = self.root / "data/outputs/fit"
        self.base = self.root / "initial.pth"
        model = torch.nn.Linear(1, 1, bias=False)
        with torch.no_grad():
            model.weight.fill_(0)
        training.save_checkpoint_once(self.base, {"model_state_dict": model.state_dict()})
        self.initial = runtime.binding(self.root, self.base)
        self.identity = {"recipe": {"sha256": "fixed"}, "package_sha256": "package", "schedule_sha256": "schedule"}
        self.recipe = {"output_root": "data/outputs/fit", "cache_root": "data/outputs/cache",
                       "initialization": {"checkpoint": self.initial}}
        self.package = {"training_triplets": [{"triplet_id": "a"}, {"triplet_id": "b"}, {"triplet_id": "c"}]}
        self.schedule = {"epochs": [{"epoch": e, "batches": [["a", "b"], ["c"]]} for e in range(1, 21)]}
        self.validated = []
        self.batch_sizes = []
        Store.calls = Store.closed = 0

    def initialize(self, *args):
        training.seed_runtime(1234)
        model = torch.nn.Linear(1, 1, bias=False)
        model.load_state_dict(torch.load(self.base, weights_only=True)["model_state_dict"])
        return model, "cpu", torch.optim.Adam(model.parameters(), lr=.0001), training.freeze_batch_norm(model)

    def step(self, model, optimizer, inputs, targets, masks):
        self.batch_sizes.append(len(inputs))
        optimizer.zero_grad()
        # Include all three RNGs in resume state through the production helper.
        loss = (model(inputs) - targets).square().mean()
        loss.backward()
        optimizer.step()
        return float(loss.detach()), 1

    def validate(self, model, device, store, package, epoch, checkpoint):
        self.validated.append(epoch)
        model.eval()
        metrics = {"matched": 10 if epoch == 0 else 11, "wrong": 0,
                   "certain_hidden_emissions": 0, "worst_missing_seconds": 0.0}
        # Epoch2 is worse than the retained baseline and must not win.
        if epoch == 2:
            metrics["wrong"] = 1
        return {"epoch": epoch, "checkpoint": checkpoint,
                "cohorts": {c: copy.deepcopy(metrics) for c in policy.COHORTS}}

    def stubs(self):
        stack = ExitStack()
        stack.enter_context(patch.object(runner, "preflight", return_value=(self.recipe, self.package, self.schedule, {}, self.identity)))
        stack.enter_context(patch.object(runner, "resources", return_value={"synthetic": True}))
        stack.enter_context(patch.object(runtime, "FrameStore", Store))
        stack.enter_context(patch.object(runner.adaptation, "initialize", side_effect=self.initialize))
        stack.enter_context(patch.object(training, "training_step", side_effect=self.step))
        stack.enter_context(patch.object(runtime, "validate_epoch", side_effect=self.validate))
        return stack

    def test_completed_validation_not_repeated_after_failure_and_selected_weights_are_adapter_ready(self):
        real_validation = runner.validation
        def interrupt_after_publish(*args):
            result = real_validation(*args)
            if args[-2] == 1:
                raise RuntimeError("Synthetic interruption after complete report")
            return result
        with self.stubs(), patch.object(runner, "validation", side_effect=interrupt_after_publish):
            with self.assertRaisesRegex(RuntimeError, "interruption"):
                runner.execute(self.root, "ignored")
        report = self.out / "validation/epoch_001.json"
        before = report.read_bytes()
        checkpoint = self.out / "checkpoints/epoch_001.pth"
        checkpoint_before = checkpoint.read_bytes()
        with self.stubs():
            result = runner.execute(self.root, "ignored", resume=True)
        self.assertEqual(self.validated, list(range(7)))
        self.assertEqual(result["selection"]["selected_epoch"], 1)
        self.assertEqual(result["completed_epochs"], 6)
        self.assertEqual(result["completed_updates"], 12)
        self.assertEqual(self.batch_sizes, [2, 1] * 6)
        self.assertEqual(report.read_bytes(), before)
        self.assertEqual(checkpoint.read_bytes(), checkpoint_before)
        self.assertEqual(set(torch.load(checkpoint, weights_only=True)), {"model_state_dict"})
        self.assertEqual(result["selected_checkpoint"], runtime.binding(self.root, checkpoint))
        self.assertIn(2, [r["epoch"] for r in result["selection"]["rejected"]])
        self.assertEqual(json.loads((self.out / "cache_preparation.json").read_text())["elapsed_seconds"], 1)
        with self.stubs(), patch.object(runner.adaptation, "initialize", side_effect=AssertionError("must not initialize")):
            self.assertEqual(runner.execute(self.root, "ignored", resume=True), result)
        with self.stubs():
            with self.assertRaisesRegex(ValueError, "already started"):
                runner.execute(self.root, "ignored")

    def test_epoch_zero_selection_uses_original_checkpoint_and_stops_at_five(self):
        def equal_validation(*args):
            r = self.validate(*args)
            for metrics in r["cohorts"].values():
                metrics.update(matched=10, wrong=0)
            return r
        with self.stubs(), patch.object(runtime, "validate_epoch", side_effect=equal_validation):
            result = runner.execute(self.root, "ignored")
        self.assertEqual(result["selected_checkpoint"], self.initial)
        self.assertEqual(result["completed_epochs"], 5)

    def test_unsaved_completed_updates_are_logged_and_resume_reports_replay(self):
        self.schedule = {"epochs": [{"epoch": e, "batches": [["a", "b"]] * 26} for e in range(1, 21)]}
        real_save = training.save_checkpoint_once
        def fail_end(path, value):
            if path.name == "update_000026.pth":
                raise RuntimeError("Synthetic save failure")
            return real_save(path, value)
        with self.stubs(), patch.object(training, "save_checkpoint_once", side_effect=fail_end):
            with self.assertRaisesRegex(RuntimeError, "save failure"):
                runner.execute(self.root, "ignored")
        failed = next((self.out / "attempts").glob("*/failed.json"))
        evidence = json.loads(failed.read_text())
        self.assertEqual(evidence["completed_updates_in_memory"], 26)
        self.assertTrue(evidence["resume_checkpoint"]["path"].endswith("update_000025.pth"))
        with self.stubs():
            result = runner.execute(self.root, "ignored", resume=True)
        restored = [json.loads(p.read_text()) for p in (self.out / "attempts").glob("*/restored.json")]
        self.assertTrue(any(r["restored_updates"] == 25 and r["previous_unsaved_completed_count"] == 1 for r in restored))
        self.assertTrue((self.out / "states/update_000025.pth").exists())
        self.assertEqual(len(self.batch_sizes), result["completed_updates"] + 1)

    def test_changed_resume_identity_is_rejected_before_cache_or_model(self):
        with self.stubs():
            runner.execute(self.root, "ignored")
        self.identity = {**self.identity, "schedule_sha256": "changed"}
        with self.stubs(), patch.object(runtime, "FrameStore", side_effect=AssertionError("must not prepare")):
            with self.assertRaisesRegex(ValueError, "identity changed"):
                runner.execute(self.root, "ignored", resume=True)

    def test_interrupted_retention_receipt_is_reused_with_newer_replacement(self):
        folder = self.out / "states"
        folder.mkdir(parents=True)
        old, middle, latest = [folder / f"update_{i:06d}.pth" for i in (0, 25, 50)]
        for p in (old, middle, latest):
            p.write_bytes(p.name.encode())
        receipt = self.out / "retention/update_000000.json"
        runner.write_once(receipt, {"status": "superseded_optimizer_state_removed", "removed_state": runtime.binding(self.root, old),
            "replacement": runtime.binding(self.root, middle), "epoch_model_checkpoints_retained": True})
        before = receipt.read_bytes()
        runner.retain_resume_states(self.root, self.out, latest)
        self.assertEqual(receipt.read_bytes(), before)
        self.assertFalse(old.exists())
        self.assertFalse(middle.exists())
        self.assertTrue(latest.exists())

    def test_load_state_rejects_loss_schedule_mismatch(self):
        model, _, optimizer, bn = self.initialize()
        losses = [{"epoch": 1, "batch_index": 1, "triplet_ids": ["wrong"], "update": 1, "loss": 1.0}]
        path = self.root / "update_000001.pth"
        training.save_checkpoint_once(path, runner.state_payload(model, optimizer, self.identity, 1, 1, losses, bn))
        with self.assertRaisesRegex(ValueError, "frozen schedule"):
            runner.load_state(path, self.identity, self.schedule)

    def test_preflight_requires_code_bindings_before_cache_or_model(self):
        recipe = {"schema_version": "ball_completion_primary_recipe/v0.1", "status": "frozen_before_model_execution",
                  "training": runner.TRAINING, "runtime": runner.runtime_versions(), "protected_evaluation_authorized": False,
                  "campaign_approval": {"path": "approval"}, "code_bindings": [], "inference": runner.INFERENCE}
        p = self.root / "recipe.json"
        p.write_text(json.dumps(recipe))
        with patch.object(runner, "bound_path", return_value=p):
            with self.assertRaisesRegex(ValueError, "implementation binding"):
                runner.preflight(Path(runner.__file__).resolve().parents[2], p)


if __name__ == "__main__":
    unittest.main()
