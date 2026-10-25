import hashlib
import copy
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import numpy as np
from PIL import Image
import torch

from src.ball_tracking import completion_training_runtime as runtime
from src.ball_tracking.wasb_adapter import affine_matrices, preprocess_triplet


def label(index, center=None, visibility="not_visible", certainty="certain"):
    return {"frame_index": index, "annotation_status": "labeled", "visibility": visibility,
            "absence_reason": "occluded" if visibility == "not_visible" else None,
            "game_ball_identity_certainty": certainty,
            "geometry": None if center is None else {"center_xy_px": center, "source": "observed_complete_ball_center",
                                                      "uncertainty_radius_px": 2},
            "localization_eligible": center is not None, "difficulty_tags": [], "notes": "Synthetic test."}


class RuntimeTests(unittest.TestCase):
    def test_atomic_receipt_survives_interrupted_publication_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "receipt.json"
            with patch.object(runtime.os, "link", side_effect=OSError("simulated interruption")):
                with self.assertRaises(OSError):
                    runtime.atomic_write_once(path, {"status": "passed"})
            self.assertFalse(path.exists())
            abandoned = list(Path(temp).glob("*.tmp"))
            self.assertEqual(len(abandoned), 1)
            runtime.atomic_write_once(path, {"status": "passed"})
            original = path.read_bytes()
            runtime.atomic_write_once(path, {"status": "passed"})
            self.assertEqual(path.read_bytes(), original)
            self.assertTrue(abandoned[0].exists())
            with self.assertRaisesRegex(ValueError, "evidence differs"):
                runtime.atomic_write_once(path, {"status": "failed"})

    def test_normalization_exactly_matches_producing_adapter_at_two_source_sizes(self):
        import cv2
        rng = np.random.default_rng(91)
        for width, height in [(1280, 720), (1920, 1080)]:
            frames = [rng.integers(0, 256, (height, width, 3), dtype=np.uint8) for _ in range(3)]
            expected, _ = preprocess_triplet(frames)
            forward, _ = affine_matrices(width, height)
            actual = torch.cat([runtime.normalized_tensor(cv2.warpAffine(f, forward, (512, 288), flags=cv2.INTER_LINEAR))
                                for f in frames]).unsqueeze(0)
            self.assertTrue(torch.equal(expected, actual))

    def test_unknown_is_masked_and_validation_cannot_supply_gradient_samples(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            frames = []
            for index in range(3):
                rgb = np.full((36, 64, 3), index * 70, np.uint8)
                path = root / f"frame{index}.png"
                Image.fromarray(rgb).save(path)
                annotation = label(index, [32, 18], "fully_visible") if index != 1 else label(index, None, "indeterminate", "ambiguous")
                frames.append({"source_frame_index": index, "source_pts_ticks": index * 512, "duration_ticks": 512,
                               "png": {**runtime.binding(root, path), "rgb_sha256": hashlib.sha256(rgb.tobytes()).hexdigest()},
                               "annotation": annotation})
            block = {"block_id": "synthetic", "game_id": "test", "domain": "nba", "role": "checkpoint_validation",
                     "source_video": {"width_px": 64, "height_px": 36}, "time_base": "1/12800", "frames": frames}
            store = runtime.FrameStore(root, {"training_blocks": [], "validation_blocks": [block]}, root / "cache")
            report = store.prepare()
            self.assertEqual(report["unique_block_frames"], 3)
            self.assertEqual(report["source_video_decodes"], 0)
            self.assertEqual(store.inputs("synthetic", [0, 1, 2]).shape, (9, 288, 512))
            class SyntheticModel(torch.nn.Module):
                def forward(self, inputs):
                    logits = torch.full((len(inputs), 3, 288, 512), -20., dtype=torch.float32)
                    logits[:, :, 144, 256] = 20.
                    return {0: logits}
            emitted = runtime.validate_epoch(SyntheticModel(), torch.device("cpu"), store,
                                             {"validation_blocks": [block]}, 0, {"synthetic": True})
            self.assertEqual(emitted["cohorts"]["nba_validation"]["matched"], 2)
            self.assertEqual(emitted["cohorts"]["nba_validation"]["wrong"], 0)
            self.assertEqual([r["outcome"] for r in emitted["blocks"][0]["frame_results"]],
                             ["matched", "unscored", "matched"])
            self.assertEqual([r["source_pts_ticks"] for r in emitted["blocks"][0]["observations"]], [0, 512, 1024])
            with self.assertRaisesRegex(ValueError, "Validation block"):
                store.example({"block_id": "synthetic", "frame_indices": [0, 1, 2], "valid_output_channels": [True, False, True]})
            train_block = {**block, "role": "training"}
            train_store = runtime.FrameStore(root, {"training_blocks": [train_block], "validation_blocks": []}, root / "train_cache")
            train_store.prepare()
            triplet = {"block_id": "synthetic", "frame_indices": [0, 1, 2], "valid_output_channels": [True, False, True]}
            inputs, targets, masks = train_store.example(triplet)
            self.assertEqual(masks.tolist(), [True, False, True])
            self.assertGreater(int(targets[0].sum()), 0)
            self.assertEqual(int(targets[1].sum()), 0)
            with self.assertRaisesRegex(ValueError, "Supervision mask"):
                train_store.example({**triplet, "valid_output_channels": [True, True, True]})
            train_store.close()
            misjoined = copy.deepcopy(train_block)
            misjoined["frames"][0]["annotation"]["frame_index"] = 2
            with self.assertRaisesRegex(ValueError, "Annotation/native-frame join"):
                runtime.FrameStore(root, {"training_blocks": [misjoined], "validation_blocks": []}, root / "bad_cache").prepare()
            # A verified cache must reject silent content changes on a new reader.
            cache_path = next((root / "cache").rglob("frames.npy"))
            store.close()
            with cache_path.open("r+b") as f:
                f.seek(-1, 2)
                f.write(b"\xff")
            with self.assertRaises(ValueError):
                runtime.FrameStore(root, {"training_blocks": [], "validation_blocks": [block]}, root / "cache").prepare()

    def test_missing_duration_uses_actual_display_intervals_and_hidden_certainty(self):
        rows, observations = [], []
        for i, (duration, center, certainty) in enumerate([(1440, [20, 20], "certain"), (1530, [20, 20], "certain"),
                                                        (1440, None, "certain"), (1530, None, "probable")]):
            annotation = label(i, center, "fully_visible" if center else "not_visible", certainty)
            png = {"path": str(i), "sha256": "0" * 64}
            rows.append({"source_frame_index": i, "source_pts_ticks": i * 1500, "duration_ticks": duration,
                         "png": png, "annotation": annotation})
            observations.append({"source_frame_index": i, "source_pts_ticks": i * 1500, "source_png": png,
                                 "inference_status": "completed", "temporal_contributions": 1,
                                 "candidates": [], "center_xy_px": None if center else [20, 20]})
        block = {"block_id": "x", "game_id": "g", "domain": "nba", "role": "checkpoint_validation",
                 "source_video": {"width_px": 64, "height_px": 36}, "time_base": "1/90000", "frames": rows}
        scored = runtime.scored_block(block, observations)
        self.assertEqual(scored["missing"], 2)
        self.assertEqual(scored["worst_missing_duration_exact"], "33/1000")
        self.assertEqual(scored["certain_hidden_emissions"], 1)
        self.assertEqual(scored["all_hidden_emissions"], 2)


if __name__ == "__main__":
    unittest.main()
