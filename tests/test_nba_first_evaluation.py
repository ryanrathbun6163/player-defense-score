"""Saved validation producer transport and exact CPU cache checks; no GPU fit."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image
import torch

from src.ball_tracking import nba_first_evaluation as evaluate
from src.ball_tracking import completion_training_runtime as runtime
from src.ball_tracking.annotations import FrameAnnotation
from src.ball_tracking.wasb_adapter import preprocess_triplet


class _Store:
    def inputs(self, block_id, indices):
        tensor = torch.zeros((9, 288, 512), dtype=torch.float32)
        tensor[0, 0, 0] = indices[0]
        return tensor


class _Model(torch.nn.Module):
    """Deterministic CPU logits consumed by the actual frozen epoch validator."""
    def forward(self, inputs):
        logits = torch.full((1, 3, 288, 512), -20.0)
        start = int(inputs[0, 0, 0, 0])
        points = {100: (20, 12), 102: (30, 14)}
        for channel in range(3):
            point = points.get(start + channel)
            if point is not None:
                logits[0, channel, point[1] * 8, point[0] * 8] = 1.0986123
        return [logits]


class NbaFirstEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        parent = self.root / "data/outputs/t"
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="nba_first_cpu_test_", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.old_threads = torch.get_num_threads()
        torch.set_num_threads(2)
        self.addCleanup(torch.set_num_threads, self.old_threads)
        self.block = {"block_id": "synthetic_nba", "domain": "nba", "game_id": "synthetic",
            "role": "checkpoint_validation", "time_base": "1/90000", "range_inclusive": [100, 103],
            "source_video": {"width_px": 64, "height_px": 36,
                             "sha256": hashlib.sha256(b"synthetic source").hexdigest()}, "frames": []}
        self.rgb = []
        bounds = type("Bounds", (), self.block["source_video"])()
        pts = 900000
        for offset, duration in enumerate((1440, 1530, 1530, 1440)):
            index = 100 + offset
            rgb = np.zeros((36, 64, 3), np.uint8)
            rgb[:, :, 0] = np.arange(64, dtype=np.uint8)[None, :] + offset * 20
            rgb[:, :, 1] = np.arange(36, dtype=np.uint8)[:, None] * 3
            rgb[:, :, 2] = 100 + offset * 10
            self.rgb.append(rgb)
            path = self.folder / f"source_{index}.png"
            Image.fromarray(rgb).save(path)
            label = {"frame_index": index, "annotation_status": "labeled",
                "visibility": "fully_visible" if offset == 0 else "not_visible" if offset == 3 else "indeterminate",
                "absence_reason": "occluded" if offset == 3 else None,
                "game_ball_identity_certainty": "certain" if offset in {0, 3} else "ambiguous",
                "geometry": {"center_xy_px": [20, 12], "source": "observed_complete_ball_center",
                             "uncertainty_radius_px": 2} if offset == 0 else None,
                "localization_eligible": offset == 0, "difficulty_tags": [], "notes": "Synthetic reference"}
            self.block["frames"].append({"source_frame_index": index, "source_pts_ticks": pts,
                "duration_ticks": duration, "state": "permitted", "reference_role": "checkpoint_validation",
                "png": {**runtime.binding(self.root, path), "rgb_sha256": hashlib.sha256(rgb.tobytes()).hexdigest()},
                "annotation": FrameAnnotation.from_mapping(label, offset, bounds).to_dict()})
            pts += duration
        weight = self.folder / "model.pth"
        weight.write_bytes(b"CPU test checkpoint identity, never deserialized")
        self.checkpoint = runtime.binding(self.root, weight)
        self.report = runtime.validate_epoch(_Model(), "cpu", _Store(),
            {"validation_blocks": [self.block]}, 0, self.checkpoint)
        self.report_path = self.folder / "epoch_000.json"
        self.source = self.write_report(self.report)

    def write_report(self, report):
        self.report_path.write_text(json.dumps(report))
        return {"kind": "validation", "checkpoint": self.checkpoint,
                "report": runtime.binding(self.root, self.report_path)}

    def write_json(self, name, value):
        path = self.folder / name
        path.write_text(json.dumps(value))
        return runtime.binding(self.root, path)

    def test_actual_validation_producer_outputs_reuse_without_prediction_change(self):
        original = copy.deepcopy(self.report)
        records = evaluate.reused_observations(self.root, self.block, self.source)
        self.assertEqual(records, original["blocks"][0]["observations"])
        self.assertEqual([r["temporal_contributions"] for r in records], [1, 2, 2, 1])
        self.assertIsNone(records[1]["center_xy_px"])
        self.assertIsNone(records[3]["center_xy_px"])
        evaluate.validate_records(self.block, records)
        self.assertEqual(self.report, original)
        # Only the optional transport byte-size field may be supplied later.
        reduced = copy.deepcopy(self.report)
        del reduced["blocks"][0]["observations"][0]["source_png"]["bytes"]
        self.assertEqual(evaluate.reused_observations(self.root, self.block, self.write_report(reduced)), records)

    def test_reused_observations_reject_bad_native_join_failed_call_and_empty_png(self):
        changes = {"source_pts_ticks": 1, "inference_status": "failed", "source_png": {},
                   "point_origin": "manual", "temporal_contributions": 3, "center_xy_px": [1, 1]}
        for field, value in changes.items():
            report = copy.deepcopy(self.report)
            report["blocks"][0]["observations"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                evaluate.reused_observations(self.root, self.block, self.write_report(report))

    def test_validation_report_wrong_checkpoint_or_policy_is_rejected(self):
        for change in ({"checkpoint": {"sha256": "a" * 64}}, {"protected_frames": 1},
                       {"threshold": .25}, {"strict_threshold": False}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                evaluate.reused_observations(self.root, self.block, self.write_report({**self.report, **change}))

    def test_preflight_cannot_assign_one_models_saved_observations_to_another(self):
        models = []
        for index in range(12):
            path = self.folder / f"weights_{index}.pth"
            path.write_bytes(f"unique synthetic weights {index}".encode())
            checkpoint = self.checkpoint if index == 0 else runtime.binding(self.root, path)
            models.append({"name": f"model_{index}", "checkpoint": checkpoint,
                "provenance": self.source["report"], "reuse": {self.block["block_id"]: self.source}})
        package = self.write_json("training.json", {"reference_bindings": []})
        comparison = self.write_json("comparison.json", {"reference_bindings": []})
        parent = self.write_json("recipe.json", {"package": package, "code_bindings": []})
        config = {"schema_version": evaluate.SCHEMA, "status": "frozen_before_execution",
            "protected_evaluation_authorized": False, "training_authorized": False,
            "inference_policy": evaluate.evaluation.POLICY, "runtime": {"synthetic": True}, "code_bindings": [],
            "primary_recipe": parent, "training_package": package, "comparison_package": comparison,
            "block_ids": [self.block["block_id"]], "models": models,
            "new_model_calls": 0, "reused_observation_frames": 48}
        config_binding = self.write_json("config.json", config)
        with patch.object(evaluate, "runtime_versions", return_value={"synthetic": True}), \
             patch.object(evaluate, "blocks_from_packages", return_value=[self.block]):
            with self.assertRaisesRegex(ValueError, "checkpoint|model|weights"):
                evaluate.preflight(self.root, config_binding["path"])

    def prepare_cache(self):
        cache = evaluate.InputCache(self.root, [self.block], self.folder / "cache")
        self.addCleanup(cache.close)
        try:
            receipts = cache.prepare()
        except BaseException:
            cache.close()
            raise
        return cache, receipts

    def test_input_cache_matches_actual_preprocess_and_reuses_immutable_receipt(self):
        cache, receipts = self.prepare_cache()
        expected, _ = preprocess_triplet(self.rgb[:3])
        actual = cache.inputs(self.block["block_id"], self.block["frames"][:3])
        self.assertEqual(tuple(actual.shape), (9, 288, 512))
        self.assertTrue(torch.equal(actual.unsqueeze(0), expected))
        self.assertEqual(cache.arrays[self.block["block_id"]].dtype, np.uint8)
        self.assertEqual(cache.arrays[self.block["block_id"]].shape, (4, 288, 512, 3))
        self.assertEqual(receipts[0]["exact_preprocessing_triplets"], [[100, 101, 102], [101, 102, 103]])
        cache.close()
        reopened, second = self.prepare_cache()
        self.assertEqual(receipts, second)
        self.assertTrue(torch.equal(reopened.inputs(self.block["block_id"], self.block["frames"][:3]), actual))

    def test_cache_rejects_stale_receipt_and_wrong_array_representation(self):
        cache, receipts = self.prepare_cache()
        cache.close()
        receipt_path = self.root / receipts[0]["receipt"]["path"]
        original = json.loads(receipt_path.read_text())
        changed = copy.deepcopy(original)
        changed["identity"]["block_sha256"] = "f" * 64
        receipt_path.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, "identity changed"):
            self.prepare_cache()
        array_path = self.root / original["array"]["path"]
        correct = np.load(array_path, allow_pickle=False)
        for bad in (correct.astype(np.uint16), np.concatenate([correct, correct[:1]])):
            np.save(array_path, bad, allow_pickle=False)
            changed = copy.deepcopy(original)
            changed["array"] = runtime.binding(self.root, array_path)
            receipt_path.write_text(json.dumps(changed))
            with self.subTest(shape=bad.shape, dtype=str(bad.dtype)), self.assertRaisesRegex(ValueError, "shape or dtype"):
                self.prepare_cache()


if __name__ == "__main__":
    unittest.main()
