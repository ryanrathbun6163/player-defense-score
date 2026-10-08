"""Focused producer parity and tiny-model checks; never run the real fit."""
import ast
import copy
import importlib.util
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch
from torch import nn

from src.ball_tracking import wasb_training as training
from src.ball_tracking.wasb_adapter import affine_matrices
from src.ball_tracking.wasb_experiment import read_json, write_once
from test_ball_annotation_foundation import (
    ambiguous_visible_frame, not_visible_frame, observed_frame, parse_reviewed_annotations,
)

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "data/outputs/wasb_assets/WASB-SBDT-923462cacdeb3353b84ddebdedb3f4b7a8553b0f"


def upstream_module(relative, name):
    path = ASSET / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def upstream_function(relative, name, namespace):
    # Execute the exact pinned function AST without unrelated legacy imports.
    tree = ast.parse((ASSET / relative).read_text())
    node = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name][-1]
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(ASSET / relative), "exec"), namespace)
    return namespace[name]


class TinyModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(9, 3, 1)
        self.bn = nn.BatchNorm2d(3)

    def forward(self, inputs):
        return {0: self.bn(self.conv(inputs))}


def tiny_state():
    torch.manual_seed(1234)
    model = TinyModel()
    reference = training.freeze_batch_norm(model)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4, betas=(.9, .999), eps=1e-8, weight_decay=0)
    schedule = training.sample_schedule([{"triplet_id": "a"}, {"triplet_id": "b"}], sample_count=2)
    inputs = torch.randn(2, 9, 8, 8)
    targets = torch.zeros(2, 3, 8, 8)
    masks = torch.tensor([[True, False, True], [True, True, True]])
    loss, _ = training.training_step(model, optimizer, inputs, targets, masks)
    losses = [{"update": 1, "triplet_ids": schedule["batches"][0], "loss": loss}]
    identity = {"synthetic_test": True}
    state = training._training_state(model, optimizer, identity, schedule, 1, losses, reference, {"synthetic": True})
    return model, optimizer, state, identity, schedule


@unittest.skipUnless((ASSET / "src/utils/heatmap.py").exists(), "Pinned upstream target/loss sources unavailable")
class UpstreamTrainingParityTests(unittest.TestCase):
    def test_binary_disk_affine_integer_truncation_matches_actual_upstream_producer(self):
        binary = upstream_module("src/utils/heatmap.py", "_wasb_training_heatmap").gen_binary_map
        transform_point = upstream_function("src/utils/image.py", "affine_transform", {"np": np})
        for dimensions, point in (((1920, 1080), (376.7, 522.1)), ((512, 288), (100.99, 100.99)),
                                  ((100, 200), (20.1, .2)), ((1920, 1080), (0, 0))):
            labels = parse_reviewed_annotations([observed_frame(0, center=point)],
                                                width_px=dimensions[0], height_px=dimensions[1])
            annotation = labels.annotations[0]
            actual, valid, metadata = training.annotation_target(annotation, *dimensions)
            affine, _ = affine_matrices(*dimensions)
            integer = transform_point(np.array(point), affine).astype(np.int32)
            expected = binary((512, 288), integer, 2.5)
            np.testing.assert_array_equal(actual, expected)
            self.assertEqual(metadata["integer_heatmap_center"], integer.tolist())
            self.assertTrue(valid)
        self.assertEqual(training.annotation_target(
            parse_reviewed_annotations([observed_frame(0, center=(100.99, 100.99))],
                                       width_px=512, height_px=288).annotations[0], 512, 288)[2]["integer_heatmap_center"], [100, 100])

    def test_clamped_gamma_two_loss_matches_actual_upstream_loss(self):
        upstream_loss = upstream_module("src/losses/wbce.py", "_wasb_training_wbce").WBCELoss()
        sigmoid = upstream_function("src/utils/utils.py", "_sigmoid", {"torch": torch})
        logits = torch.linspace(-20, 20, 2 * 3 * 8 * 8, dtype=torch.float32).reshape(2, 3, 8, 8)
        targets = (torch.arange(logits.numel()).reshape(logits.shape) % 11 == 0).to(torch.float32)
        valid = torch.ones(2, 3, dtype=torch.bool)
        actual = training.masked_wbce(logits, targets, valid)
        expected = upstream_loss({0: sigmoid(logits.clone())}, {0: targets})
        torch.testing.assert_close(actual, expected, rtol=0, atol=0)


class TrainingBoundaryTests(unittest.TestCase):
    def test_ambiguity_retains_image_channel_but_removes_its_loss_and_denominator(self):
        labels = parse_reviewed_annotations([observed_frame(0), not_visible_frame(1), ambiguous_visible_frame(2)])
        values = [training.annotation_target(a, 1920, 1080) for a in labels.annotations]
        self.assertEqual([v[1] for v in values], [True, True, False])
        self.assertEqual([v[2]["kind"] for v in values], ["positive", "hidden", "masked"])
        self.assertGreater(values[0][0].sum(), 0)
        self.assertEqual(values[1][0].sum(), 0)
        self.assertEqual(values[2][0].sum(), 0)
        logits = torch.randn(2, 3, 8, 8, requires_grad=True)
        targets = torch.zeros_like(logits)
        valid = torch.tensor([[True, False, True], [True, False, True]])
        actual = training.masked_wbce(logits, targets, valid)
        expected = training.masked_wbce(logits[:, [0, 2]], targets[:, [0, 2]], torch.ones(2, 2, dtype=torch.bool))
        torch.testing.assert_close(actual, expected)
        actual.backward()
        self.assertTrue(torch.equal(logits.grad[:, 1], torch.zeros_like(logits.grad[:, 1])))
        self.assertGreater(float(logits.grad[:, 0].abs().sum()), 0)
        with self.assertRaisesRegex(ValueError, "supervised"):
            training.masked_wbce(logits, targets, torch.zeros_like(valid))

    def test_sampling_concatenates_cycles_to_exactly400_ids_and200_batches(self):
        triplets = [{"triplet_id": f"triplet_{i:02d}"} for i in range(69)]
        schedule = training.sample_schedule(triplets)
        self.assertEqual(len(schedule["sampled_ids"]), 400)
        self.assertEqual(len(schedule["batches"]), 200)
        self.assertEqual([len(c["consumed_ids"]) for c in schedule["cycles"]], [69] * 5 + [55])
        self.assertEqual([i for batch in schedule["batches"] for i in batch], schedule["sampled_ids"])
        for cycle in schedule["cycles"]:
            self.assertEqual(set(cycle["shuffled_ids"]), {t["triplet_id"] for t in triplets})
        self.assertEqual(training.sample_schedule(list(reversed(triplets))), schedule)
        self.assertNotEqual(training.sample_schedule(triplets, seed=1235)["sampled_ids"], schedule["sampled_ids"])

    def test_real_pilot_manifest_reads_only_three_training_annotation_bodies(self):
        config = training.load_config(ROOT, ROOT / training.DEFAULT_CONFIG)
        original_loader = training.load_annotations
        with patch.object(training, "load_annotations", wraps=original_loader) as loader:
            manifest, _ = training.build_training_manifest(ROOT, config)
        self.assertEqual(manifest["counts"], config["expected_split"])
        self.assertEqual(len(manifest["triplets"]), 69)
        self.assertEqual({call.args[0].resolve() for call in loader.call_args_list},
                         {(ROOT / p["annotation"]["path"]).resolve() for p in config["pilots"]})
        masked = [f for w in manifest["pilot_windows"] for f in w["frames"] if not f["valid_output_channel"]]
        self.assertEqual([f["frame_index"] for f in masked], [335])
        self.assertFalse(manifest["holdout_label_bodies_read"])
        changed = copy.deepcopy(config)
        changed["pilots"][0]["start_frame_index"] = 374
        with self.assertRaisesRegex(ValueError, "Pilot frame range"):
            training.build_training_manifest(ROOT, changed)

    def test_tiny_update_changes_parameters_but_keeps_all_batchnorm_buffers(self):
        model, optimizer, state, _, _ = tiny_state()
        self.assertTrue(all(p.requires_grad for p in model.parameters()))
        self.assertFalse(model.bn.training)
        self.assertTrue(model.training)
        self.assertFalse(torch.equal(model.bn.weight, torch.ones_like(model.bn.weight)))
        training.assert_batch_norm_unchanged(model, state["batch_norm_reference"])
        self.assertEqual(optimizer.defaults["lr"], 1e-4)
        model.bn.running_mean.add_(1)
        with self.assertRaisesRegex(ValueError, "buffers changed"):
            training.assert_batch_norm_unchanged(model, state["batch_norm_reference"])

    def test_safe_state_roundtrip_preserves_optimizer_rng_schedule_and_rejects_bn_mutation(self):
        model, optimizer, state, identity, schedule = tiny_state()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "state.pth"
            with patch.object(training.torch, "load", wraps=torch.load) as load:
                training.save_checkpoint_once(path, state)
                restored = training.load_training_state(path, identity, schedule)
            self.assertTrue(all(call.kwargs.get("weights_only") is True for call in load.call_args_list))
            clone = TinyModel()
            clone.load_state_dict(restored["model_state_dict"], strict=True)
            other = torch.optim.Adam(clone.parameters(), lr=1e-4)
            other.load_state_dict(restored["optimizer_state_dict"])
            self.assertEqual(len(other.state), len(optimizer.state))
            self.assertEqual(restored["schedule"], schedule)
            self.assertEqual(restored["losses"], state["losses"])
            training.restore_rng(restored["rng_state"])
            a = (random.random(), np.random.rand(), torch.rand(3))
            training.restore_rng(restored["rng_state"])
            b = (random.random(), np.random.rand(), torch.rand(3))
            self.assertEqual(a[:2], b[:2])
            torch.testing.assert_close(a[2], b[2])
            with self.assertRaises(FileExistsError):
                training.save_checkpoint_once(path, state)
            wrong = copy.deepcopy(restored)
            wrong["model_state_dict"]["bn.running_mean"].add_(1)
            bad = Path(folder) / "changed.pth"
            training.save_checkpoint_once(bad, wrong)
            with self.assertRaisesRegex(ValueError, "Saved BatchNorm"):
                training.load_training_state(bad, identity, schedule)
            with self.assertRaisesRegex(ValueError, "identity/schedule"):
                training.load_training_state(path, {"different": True}, schedule)
            misnamed = Path(folder) / "update_000200.pth"
            training.save_checkpoint_once(misnamed, restored)
            with self.assertRaisesRegex(ValueError, "filename and completed progress"):
                training.load_training_state(misnamed, identity, schedule)

    def test_final_publication_recovers_without_optimizer_or_model_execution(self):
        _, _, state, _, _ = tiny_state()
        state["completed_updates"] = 200
        state["losses"] = [{"update": i, "loss": .1, "triplet_ids": ["synthetic", "synthetic"]} for i in range(1, 201)]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for filename in ("training_manifest.json", "sampling_schedule.json", "config.json"):
                write_once(root / filename, {"synthetic": True})
            state_path = training.save_checkpoint_once(root / "final_state.pth", state)
            with patch.object(TinyModel, "forward", side_effect=AssertionError("No retraining for publication")):
                result = training.publish_final(root, root, training.binding(root, root / "config.json"), state_path, state, [])
                original = (root / "checkpoint.pth").read_bytes()
                second = training.publish_final(root, root, training.binding(root, root / "config.json"), state_path, state, [])
            self.assertEqual(result, second)
            self.assertEqual(original, (root / "checkpoint.pth").read_bytes())
            payload = torch.load(root / "checkpoint.pth", map_location="cpu", weights_only=True)
            self.assertEqual(set(payload), {"model_state_dict"})
            self.assertEqual(result["completed_updates"], 200)
            self.assertFalse(result["evaluation_used_for_training_or_selection"])

    def test_nonfinite_updates_and_state_are_rejected_and_lock_releases(self):
        model = TinyModel()
        training.freeze_batch_norm(model)
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            training.training_step(model, optimizer, torch.full((2, 9, 8, 8), float("nan")),
                                   torch.zeros(2, 3, 8, 8), torch.ones(2, 3, dtype=torch.bool))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(ValueError, "nonfinite"):
                training.save_checkpoint_once(root / "bad.pth", {"tensor": torch.tensor(float("nan"))})
            with training.training_lock(root / "training.lock"):
                with self.assertRaises(OSError):
                    with training.training_lock(root / "training.lock"):
                        self.fail("Concurrent lock acquired")
            with training.training_lock(root / "training.lock"):
                pass


if __name__ == "__main__":
    unittest.main()
