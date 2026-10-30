"""Focused CPU orchestration checks using actual PNG/observation producers."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from src.ball_tracking import completion_evaluation as original
from src.ball_tracking import tapnext_adapter as adapter_module
from src.ball_tracking import tapnext_pilot as pilot
from src.ball_tracking.completion_training_runtime import atomic_write_once, binding
from tests import test_completion_evaluation as fixtures


class ConsistentBackend:
    """Synthetic outputs pass the real transform/visibility consumer independently."""
    def __init__(self, fail_at=None):
        self.calls = 0
        self.fail_at = fail_at

    def infer(self, rgb, query, state):
        self.calls += 1
        if self.calls == self.fail_at:
            raise RuntimeError("synthetic model execution failure")
        h, w = rgb.shape[:2]
        yx = np.tile([64., 80.], (65, 1)).astype(np.float32)
        xy = yx[:, ::-1].copy() * np.array([w/256, h/256], np.float32)
        return adapter_module.TrackerFrame(xy, yx, np.zeros((65, 512), np.float32),
                                          np.ones(65, np.float32), {"step": self.calls})


class PilotOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.EvaluationTests("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root

    def test_actual_baseline_projection_removes_all_annotation_fields(self):
        block = self.fixture.block(domain="nba")
        baseline = original.baseline_observations(block)
        projected = pilot.prediction_input(block, block["frames"][0], baseline[0])
        self.assertEqual(set(projected), adapter_module.INPUT_KEYS)
        self.assertEqual(set(projected["wasb_observation"]), adapter_module.SEED_KEYS)
        self.assertNotIn("annotation", projected)
        self.assertNotIn("annotation", projected["source_png"])
        self.assertEqual(projected["wasb_observation"]["original_record_sha256"],
                         adapter_module.canonical(baseline[0]))
        self.assertIsNotNone(block["frames"][0]["annotation"])

    def test_protected_native_image_and_projection_fail_before_io(self):
        block = self.fixture.block()
        loader = pilot.NativeImages(self.root, block)
        protected = {"state": "withheld", "source_frame_index": 4}
        with patch.object(original, "bound_path", side_effect=AssertionError("No file access allowed")):
            with self.assertRaisesRegex(ValueError, "Protected image"):
                loader.get(protected)
            with self.assertRaisesRegex(ValueError, "Protected index"):
                loader.get(protected | {"state": "permitted"})
            with self.assertRaisesRegex(ValueError, "Protected frames"):
                pilot.prediction_input(block, protected, {})
        self.assertEqual(loader.decoded, 0)

    def test_infer_block_consumes_actual_producer_and_preserves_final_interval(self):
        block = self.fixture.block(domain="nba")
        ticks = 90000
        for frame, duration in zip(block["frames"], (1440, 1530, 1440, 1530), strict=True):
            frame["source_pts_ticks"], frame["duration_ticks"] = ticks, duration
            original_record = frame["baseline_observation"]["original_record"]
            original_record["source_pts_ticks"], original_record["time_base"] = ticks, "1/90000"
            ticks += duration
        block["time_base"] = "1/90000"
        work = self.root / "work"
        work.mkdir()
        adapter = adapter_module.SingleSeedAdapter(ConsistentBackend())
        result = pilot.infer_block(self.root, block, adapter, work)
        emitted = [json.loads(line) for line in (work / "frames.jsonl").read_text().splitlines()]
        self.assertEqual(emitted, result["observations"])
        self.assertEqual(result["resources"]["model_calls"], 4)
        self.assertEqual(result["resources"]["native_png_decodes"], 4)
        self.assertEqual(result["resources"]["maximum_cached_native_images"], 3)
        self.assertEqual(emitted[-1]["source_pts_ticks"] + emitted[-1]["duration_ticks"], ticks)
        self.assertEqual(emitted[0]["seed"]["source_frame_index"], 0)
        self.assertTrue(all(not row["seeded_this_frame"] for row in emitted[1:]))

    def test_partial_failure_preserves_jsonl_without_completion(self):
        block = self.fixture.block()
        work = self.root / "failed_work"
        work.mkdir()
        adapter = adapter_module.SingleSeedAdapter(ConsistentBackend(fail_at=3))
        with self.assertRaisesRegex(RuntimeError, "model execution failure"):
            pilot.infer_block(self.root, block, adapter, work)
        emitted = [json.loads(line) for line in (work / "frames.jsonl").read_text().splitlines()]
        self.assertEqual([row["source_frame_index"] for row in emitted], [0, 1])
        self.assertTrue(all(row["inference_status"] == "completed" for row in emitted))
        self.assertFalse((work / "completed.json").exists())
        self.assertFalse((work / "observations.json").exists())
        self.assertTrue(adapter.failed)

    def test_compatibility_joins_training_membership_by_source_and_index(self):
        block = self.fixture.block()
        train = {"training_blocks": [{"role": "training", "source_video": {"sha256": "wrong-source"},
                                     "frames": deepcopy(block["frames"])}]}
        train_path = self.root / "train.json"
        atomic_write_once(train_path, train)
        package = {"inference_blocks": [block]}
        identity = {"synthetic": True}
        def mocked_inputs(*args):
            return {}, package, {"package": binding(self.root, train_path)}, {}, {"synthetic_asset": True}
        with patch.object(pilot, "inputs", side_effect=mocked_inputs), \
             patch.object(pilot, "implementation", return_value=identity), \
             patch.object(pilot, "create_adapter", side_effect=AssertionError("No model without training membership")):
            with self.assertRaisesRegex(ValueError, "training probe"):
                pilot.compatibility(self.root, "unused", "data/outputs/wrong_source_probe")
        failed = json.loads((self.root / "data/outputs/wrong_source_probe/failed.json").read_text())
        self.assertIn("training probe", failed["error"])
        # New immutable source document and fresh attempt; preserve original failure.
        train["training_blocks"][0]["source_video"] = block["source_video"]
        train_path = self.root / "train_correct.json"
        atomic_write_once(train_path, train)
        with patch.object(pilot, "inputs", side_effect=mocked_inputs), \
             patch.object(pilot, "implementation", return_value=identity), \
             patch.object(pilot, "create_adapter", return_value=adapter_module.SingleSeedAdapter(ConsistentBackend())):
            result = pilot.compatibility(self.root, "unused", "data/outputs/correct_source_probe")
        self.assertEqual(result["model_calls"], 4)
        self.assertTrue(result["training_only"])
        self.assertFalse(result["scientific_pilot_outputs"])
        self.assertFalse((self.root / "data/outputs/wrong_source_probe/completed.json").exists())


if __name__ == "__main__":
    unittest.main()
