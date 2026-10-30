"""Focused training-assessment transport/partition checks; synthetic CPU only."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image
import torch

from src.ball_tracking import completion_training_assessment as assessment
from src.ball_tracking import completion_training_runtime as runtime
from src.ball_tracking import wasb_training as training
from src.ball_tracking.wasb_experiment import read_json

ROOT = Path(__file__).resolve().parents[1]


def annotation(index, kind):
    positive = kind == "positive"
    return {"frame_index": index, "annotation_status": "labeled",
        "visibility": "fully_visible" if positive else "not_visible" if kind == "hidden" else "indeterminate",
        "absence_reason": "occluded" if kind == "hidden" else None,
        "game_ball_identity_certainty": "ambiguous" if kind == "masked" else "certain",
        "geometry": {"center_xy_px": [32, 18], "source": "observed_complete_ball_center",
                     "uncertainty_radius_px": 2} if positive else None,
        "localization_eligible": positive, "difficulty_tags": [], "notes": "Synthetic CPU fixture."}


def package_fixture(root):
    kinds = ["positive", "hidden", "masked", "masked", "masked", "positive"]
    frames = []
    for index, kind in enumerate(kinds):
        rgb = np.full((36, 64, 3), index * 20, dtype=np.uint8)
        path = root / f"input_{index}.png"
        Image.fromarray(rgb).save(path)
        frames.append({"source_frame_index": index, "source_pts_ticks": index * 512,
            "duration_ticks": 512, "png": {**runtime.binding(root, path),
                "rgb_sha256": hashlib.sha256(rgb.tobytes()).hexdigest()},
            "annotation": annotation(index, kind), "kind": kind, "valid_output_channel": kind != "masked"})
    block = {"block_id": "training_block", "game_id": "possession_001", "domain": "nfhs",
        "role": "training", "time_base": "1/12800",
        "source_video": {"width_px": 64, "height_px": 36, "sha256": "synthetic-source"}, "frames": frames}
    triplets = [{"block_id": block["block_id"], "frame_indices": list(range(i, i + 3)),
                 "valid_output_channels": [k != "masked" for k in kinds[i:i + 3]]}
                for i in range(4) if any(k != "masked" for k in kinds[i:i + 3])]
    return {"training_blocks": [block], "validation_blocks": [{"block_id": "unreadable_validation"}],
            "training_triplets": triplets, "protected_ranges": {"possession_001": [[10, 20]]}}


class SyntheticModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.register_buffer("constant", torch.tensor(1.0))
        self.calls = 0

    def forward(self, inputs):
        if self.training or torch.is_grad_enabled():
            raise AssertionError("Assessment must use eval/inference mode")
        self.calls += 1
        logits = torch.full((1, 3, 288, 512), -12., dtype=torch.float32)
        logits[:, :, 144, 256] = 4.
        return {0: logits}


class LossTests(unittest.TestCase):
    def test_decomposition_matches_actual_frozen_loss_and_excludes_masked_channels(self):
        logits = torch.linspace(-8, 8, 3 * 4 * 5).reshape(1, 3, 4, 5)
        targets = torch.zeros_like(logits)
        targets[0, 0, 1, 2] = 1
        mask = torch.tensor([[True, True, False]])
        part = assessment.loss_breakdown(logits, targets, mask, ["positive", "hidden", "masked"])
        result = assessment.summarize_loss(part)
        self.assertEqual(result["valid_pixel_denominator"], 40)
        self.assertEqual([result["categories"][k]["pixels"] for k in assessment.CATEGORIES], [1, 19, 20])
        self.assertAlmostEqual(result["global_valid_pixel_mean"], float(training.masked_wbce(logits, targets, mask)), places=6)
        changed = logits.clone()
        changed[:, 2] = 100
        self.assertEqual(part, assessment.loss_breakdown(changed, targets, mask, ["positive", "hidden", "masked"]))
        self.assertEqual(part["masked_channel_occurrences"], 1)

    def test_all_masked_context_has_no_loss_or_denominator(self):
        result = assessment.summarize_loss(assessment.loss_breakdown(torch.zeros(1, 3, 2, 2),
            torch.zeros(1, 3, 2, 2), torch.zeros(1, 3, dtype=torch.bool), ["masked"] * 3))
        self.assertEqual(result["all_masked_triplets"], 1)
        self.assertEqual(result["valid_pixel_denominator"], 0)
        self.assertIsNone(result["global_valid_pixel_mean"])

    def test_soft_targets_hidden_positive_and_nonfinite_logits_are_rejected(self):
        targets = torch.zeros(1, 3, 2, 2)
        targets[0, 0, 0, 0] = 1
        logits = torch.zeros_like(targets)
        mask = torch.tensor([[True, True, False]])
        targets[0, 0, 1, 1] = .7
        with self.assertRaisesRegex(ValueError, "binary"):
            assessment.loss_breakdown(logits, targets, mask, ["positive", "hidden", "masked"])
        targets[0, 0, 1, 1] = 0
        targets[0, 1, 0, 0] = 1
        with self.assertRaisesRegex(ValueError, "zero"):
            assessment.loss_breakdown(logits, targets, mask, ["positive", "hidden", "masked"])
        logits[0, 0, 0, 0] = float("nan")
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            assessment.loss_breakdown(logits, targets, mask, ["positive", "hidden", "masked"])


class ProducerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = package_fixture(self.root)

    def test_actual_native_cache_stream_and_scorer_one_pass_without_validation_pixels(self):
        view = assessment.training_view(self.package)
        store = runtime.FrameStore(self.root, self.package, self.root / "cache")
        store.blocks = {b["block_id"]: b for b in view["training_blocks"]}
        self.addCleanup(store.close)
        cache = store.prepare()
        self.assertEqual(cache["unique_block_frames"], 6)
        self.assertEqual(set(store.labels), {"training_block"})
        model = SyntheticModel()
        before = assessment.model_digest(model)
        events = []
        block = view["training_blocks"][0]
        record = assessment.assess_block(model, "cpu", store, block, events.append)
        self.assertEqual(model.calls, 4)
        self.assertEqual(assessment.model_digest(model), before)
        self.assertEqual([record[k] for k in ("matched", "wrong", "missing", "certain_hidden_emissions")], [2, 0, 0, 1])
        self.assertEqual([o["temporal_contributions"] for o in record["observations"]], [1, 2, 3, 3, 2, 1])
        self.assertEqual(record["loss"]["supervised_triplets"], 3)
        self.assertEqual(record["loss"]["all_masked_triplets"], 1)
        # Serialize actual producer output, then consume it through the production aggregator/scorer.
        path = self.root / "record.json"
        runtime.atomic_write_once(path, record)
        transported = read_json(path)
        self.assertEqual(runtime.scored_block(block, transported["observations"])["frame_results"], record["frame_results"])
        summary = assessment.aggregate([transported])
        self.assertEqual(summary["supervision_accounting"]["unique_frames"], {"positive": 2, "hidden": 1, "masked": 3})
        self.assertEqual(summary["supervision_accounting"]["supervised_channel_occurrences"], 4)
        self.assertEqual(summary["supervision_accounting"]["repeated_supervised_channel_occurrences"], 1)
        self.assertEqual(len(events), 8)

    def test_roles_protected_frames_and_wrong_triplet_join_reject_before_inputs(self):
        changed = copy.deepcopy(self.package)
        changed["training_blocks"][0]["role"] = "checkpoint_validation"
        with self.assertRaisesRegex(ValueError, "training roles"):
            assessment.training_view(changed)
        changed = copy.deepcopy(self.package)
        changed["protected_ranges"]["possession_001"] = [[2, 3]]
        with self.assertRaisesRegex(ValueError, "Protected"):
            assessment.training_view(changed)
        changed = copy.deepcopy(self.package)
        changed["training_triplets"][0]["valid_output_channels"] = [False] * 3
        with self.assertRaisesRegex(ValueError, "triplets differ"):
            assessment.training_view(changed)

    def test_inference_failure_propagates_instead_of_missing_observations(self):
        store = runtime.FrameStore(self.root, self.package, self.root / "cache")
        store.blocks = {b["block_id"]: b for b in self.package["training_blocks"]}
        self.addCleanup(store.close)
        store.prepare()
        model = SyntheticModel()
        with patch.object(model, "forward", side_effect=RuntimeError("synthetic model failure")):
            with self.assertRaisesRegex(RuntimeError, "synthetic model failure"):
                assessment.assess_block(model, "cpu", store, self.package["training_blocks"][0])

    def test_adapter_consumes_actual_string_upstream_source_and_final_checkpoint_binding(self):
        identity = {"checkpoint": {"path": "epoch5.pth", "sha256": "final-sha"}}
        config = {"upstream_source": "upstream", "pretrained_checkpoint": {"path": "original.pth"}}
        with patch("src.ball_tracking.wasb_adapted_adapter.AdaptedWasbAdapter") as constructor, \
             patch.object(assessment, "bound_path", side_effect=lambda root, entry: root / entry["path"]):
            assessment.make_adapter(self.root, config, identity)
        args, kwargs = constructor.call_args
        self.assertEqual(args[:4], (self.root / "upstream", self.root / "original.pth", self.root / "epoch5.pth", "final-sha"))
        self.assertEqual(kwargs, {"device": "cuda"})

    def test_immutable_block_recovery_avoids_repeat_model_calls_and_checks_saved_bytes(self):
        counts = {"training_frames": 6, "training_blocks": 1, "supervised_triplets": 3,
                  "inference_triplets": 4, "all_masked_triplets_excluded_from_loss": 1}
        identity = {"synthetic_execution": True}
        setup = ({"cache_root": "cache"}, self.package, {}, identity, counts)
        model = SyntheticModel()
        out = self.root / "data/outputs/assessment"
        with patch.object(assessment, "preflight", return_value=setup), \
             patch.object(torch.cuda, "is_available", return_value=True), \
             patch.object(assessment, "make_adapter", return_value=SimpleNamespace(model=model, device="cpu")), \
             patch.object(assessment, "aggregate", side_effect=RuntimeError("after immutable block publication")):
            with self.assertRaisesRegex(RuntimeError, "after immutable"):
                assessment.execute(self.root, output_folder="data/outputs/assessment")
        self.assertEqual(model.calls, 4)
        failures = list((out / "attempts").glob("*/failed.json"))
        self.assertEqual(len(failures), 1)
        original_failure = failures[0].read_bytes()
        with patch.object(assessment, "preflight", return_value=setup), \
             patch.object(assessment, "make_adapter", side_effect=AssertionError("Completed block must be reused")), \
             patch.object(runtime.FrameStore, "prepare", side_effect=AssertionError("No new pixels on recovery")):
            completed = assessment.execute(self.root, output_folder="data/outputs/assessment", resume=True)
            self.assertEqual(assessment.execute(self.root, output_folder="data/outputs/assessment", resume=True), completed)
            with self.assertRaisesRegex(ValueError, "requires --resume"):
                assessment.execute(self.root, output_folder="data/outputs/assessment")
        self.assertEqual(failures[0].read_bytes(), original_failure)
        report = read_json(self.root / completed["assessment"]["path"])
        receipt = read_json(self.root / report["block_receipts"][0]["path"])
        (self.root / receipt["record"]["path"]).write_text("{}", encoding="utf-8")
        with patch.object(assessment, "preflight", return_value=setup):
            with self.assertRaises(ValueError):
                assessment.execute(self.root, output_folder="data/outputs/assessment", resume=True)

    def test_execution_records_model_failure_without_publishing_missing_or_completed(self):
        counts = {"training_frames": 6, "training_blocks": 1, "supervised_triplets": 3,
                  "inference_triplets": 4, "all_masked_triplets_excluded_from_loss": 1}
        setup = ({"cache_root": "cache"}, self.package, {}, {"synthetic": True}, counts)
        model = SyntheticModel()
        out = self.root / "data/outputs/failure"
        with patch.object(assessment, "preflight", return_value=setup), \
             patch.object(torch.cuda, "is_available", return_value=True), \
             patch.object(assessment, "make_adapter", return_value=SimpleNamespace(model=model, device="cpu")), \
             patch.object(model, "forward", side_effect=RuntimeError("model failure")):
            with self.assertRaisesRegex(RuntimeError, "model failure"):
                assessment.execute(self.root, output_folder="data/outputs/failure")
        self.assertFalse((out / "completed.json").exists())
        self.assertFalse((out / "assessment.json").exists())
        self.assertFalse(list((out / "blocks").glob("*/receipt.json")))
        failure = read_json(next((out / "attempts").glob("*/failed.json")))
        self.assertTrue(failure["failed_inference_is_not_missing"])


class ActualMetadataTests(unittest.TestCase):
    @unittest.skipUnless((ROOT / assessment.RESULT).exists(), "Actual local producer record unavailable")
    def test_actual_completed_producer_binds_final_not_selected_without_model_or_pixels(self):
        with patch.object(torch, "load", side_effect=AssertionError("No tensors in preflight")), \
             patch.object(runtime.FrameStore, "prepare", side_effect=AssertionError("No pixels in preflight")):
            _, _, _, identity, counts = assessment.preflight(ROOT)
        result = read_json(ROOT / assessment.RESULT)
        self.assertEqual(identity["checkpoint"], result["final_checkpoint"])
        self.assertNotEqual(identity["checkpoint"], result["selected_checkpoint"])
        self.assertEqual(counts, {"training_frames": 3329, "training_blocks": 26,
            "supervised_triplets": 3103, "inference_triplets": 3277,
            "all_masked_triplets_excluded_from_loss": 174})


if __name__ == "__main__":
    unittest.main()
