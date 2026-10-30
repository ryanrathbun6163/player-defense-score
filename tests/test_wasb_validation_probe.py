"""Synthetic CPU checks for the additive, read-only WASB validation probe."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import torch
from PIL import Image
from unittest.mock import patch

from src.ball_tracking import completion_training_runtime as runtime
from src.ball_tracking import wasb_validation_probe as probe


def synthetic_block(first=100, count=7):
    frames, pts = [], 9000
    for offset in range(count):
        index = first + offset
        duration = 16 if offset % 2 == 0 else 17
        frames.append({
            "source_frame_index": index, "source_pts_ticks": pts, "duration_ticks": duration,
            "png": {"path": f"synthetic/frame_{index}.png", "sha256": "a" * 64,
                    "rgb_sha256": "b" * 64},
            "annotation": {"frame_index": index, "annotation_status": "labeled",
                "visibility": "fully_visible", "absence_reason": None,
                "game_ball_identity_certainty": "certain", "localization_eligible": True,
                "geometry": {"center_xy_px": [40.0, 30.0],
                    "source": "observed_complete_ball_center", "uncertainty_radius_px": 2.0},
                "difficulty_tags": [], "notes": "Synthetic CPU test; no project footage."},
        })
        pts += duration
    return {"block_id": "synthetic_validation", "domain": "nfhs", "game_id": "possession_003",
            "role": "checkpoint_validation", "source_video": {"width_px": 512, "height_px": 288},
            "time_base": "1/1000", "frames": frames}


class SyntheticStore:
    """Encode the requested start only; the actual validator still owns transport."""
    def inputs(self, block_id, indices):
        if indices != list(range(indices[0], indices[0] + 3)):
            raise AssertionError("Synthetic producer received a nonnative triplet")
        return torch.tensor([indices[0]], dtype=torch.float32)


class SyntheticModel(torch.nn.Module):
    def __init__(self, block):
        super().__init__()
        self.first = block["frames"][0]["source_frame_index"]
        self.logits = {}
        self.calls = []
        for frame in block["frames"][:-2]:
            first = frame["source_frame_index"]
            values = torch.full((3, 288, 512), -9.0, dtype=torch.float32)
            for channel in range(3):
                target = first + channel
                # Spatially distinct channels make an off-by-one visible in hashes.
                values[channel, 30 + (target - self.first) % 3, 40 + target - self.first] = (
                    0.2 + (first - self.first) * 0.17 + channel * 0.11)
            self.logits[first] = values

    def forward(self, inputs):
        first = int(inputs[0, 0].item())
        self.calls.append(first)
        return {0: self.logits[first].unsqueeze(0).clone()}


def emitted_validation(block):
    model = SyntheticModel(block)
    report = runtime.validate_epoch(model, torch.device("cpu"), SyntheticStore(),
        {"validation_blocks": [block]}, 0, {"synthetic_checkpoint": True})
    maps = {first: logits.sigmoid().numpy().copy() for first, logits in model.logits.items()}
    return report["blocks"][0]["observations"], maps


class ValidationProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_threads = torch.get_num_threads()
        torch.set_num_threads(1)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.previous_threads)

    def assert_saved_binding(self, root, value):
        path = root / value["path"]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), value["sha256"])
        self.assertEqual(path.stat().st_size, value["bytes"])
        return path

    def test_actual_validation_producer_roundtrip_all_temporal_endpoints(self):
        block = synthetic_block()
        observations, maps = emitted_validation(block)
        expected = {r["source_frame_index"]: r for r in observations}
        spec = {"triplet_starts": [100, 101, 102, 103, 104], "target_frames": [100, 101, 103, 105, 106]}
        calls = []
        def provide(frames):
            calls.append([f["source_frame_index"] for f in frames])
            return maps[calls[-1][0]]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            targets = probe.collect_block(root, block, spec, provide, root / "probe", expected)
            self.assertEqual(calls, [list(range(i, i + 3)) for i in spec["triplet_starts"]])
            self.assertEqual([t["observation"]["temporal_contributions"] for t in targets], [1, 2, 3, 2, 1])
            self.assertEqual([[(c["triplet_start"], c["channel"]) for c in t["contributors"]] for t in targets],
                [[(100, 0)], [(100, 1), (101, 0)], [(101, 2), (102, 1), (103, 0)],
                 [(103, 2), (104, 1)], [(104, 2)]])
            persisted = json.loads((root / "probe/targets.json").read_text())
            self.assertEqual(persisted["targets"], targets)
            self.assertEqual(persisted["model_calls"], 5)
            for target in targets:
                index = target["source_frame_index"]
                self.assertEqual(target["observation"], expected[index])
                self.assertEqual(target["reproduction"],
                    {"mean_hash_equal": True, "observation_equal": True, "differing_fields": []})
                path = self.assert_saved_binding(root, target["mean_map"])
                with np.load(path, allow_pickle=False) as saved:
                    self.assertEqual(saved.files, ["mean"])
                    mean = saved["mean"]
                    self.assertEqual(hashlib.sha256(mean.tobytes()).hexdigest(), expected[index]["mean_heatmap_sha256"])
                for contributor in target["contributors"]:
                    path = self.assert_saved_binding(root, contributor["raw_maps"])
                    start, channel = contributor["triplet_start"], contributor["channel"]
                    with np.load(path, allow_pickle=False) as saved:
                        self.assertEqual(saved.files, ["heatmaps"])
                        np.testing.assert_array_equal(saved["heatmaps"], maps[start])
                    for field, peak_name in (("at_mean_global_peak", "global_peak"), ("at_mean_local_peak", "local_peak")):
                        x, y = target["mean_diagnostic"][peak_name]["heatmap_xy"]
                        self.assertEqual(contributor[field], float(maps[start][channel, y, x]))

    def test_sparse_declared_windows_reproduce_full_producer_interior_and_penultimate_frame(self):
        block = synthetic_block(300, 25)
        observations, maps = emitted_validation(block)
        expected = {r["source_frame_index"]: r for r in observations}
        spec = {"triplet_starts": [302, 303, 304, 321, 322], "target_frames": [304, 323]}
        calls = []
        def provide(frames):
            first = frames[0]["source_frame_index"]
            calls.append(first)
            return maps[first]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            targets = probe.collect_block(root, block, spec, provide, root / "sparse", expected)
            self.assertEqual(calls, spec["triplet_starts"])
            self.assertEqual([t["observation"] for t in targets], [expected[304], expected[323]])
            self.assertEqual([len(t["contributors"]) for t in targets], [3, 2])
            self.assertEqual(targets[1]["observation"]["segment_source_frame_range_inclusive"], [300, 324])

    def test_reproduction_mismatch_preserves_raw_maps_means_and_failure_record(self):
        block = synthetic_block()
        observations, maps = emitted_validation(block)
        for changed_field, changed_value in (("mean_heatmap_sha256", "0" * 64), ("native_score", -1.0)):
            with self.subTest(field=changed_field), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                expected = {r["source_frame_index"]: copy.deepcopy(r) for r in observations}
                expected[103][changed_field] = changed_value
                spec = {"triplet_starts": [101, 102, 103], "target_frames": [103]}
                with self.assertRaisesRegex(ValueError, "reproduction differs"):
                    probe.collect_block(root, block, spec, lambda rows: maps[rows[0]["source_frame_index"]],
                                        root / "failed", expected)
                persisted = json.loads((root / "failed/targets.json").read_text())
                target = persisted["targets"][0]
                self.assertFalse(target["reproduction"]["observation_equal"])
                self.assertIn(changed_field, target["reproduction"]["differing_fields"])
                self.assertEqual(target["reproduction"]["mean_hash_equal"], changed_field != "mean_heatmap_sha256")
                self.assert_saved_binding(root, target["mean_map"])
                for contributor in target["contributors"]:
                    self.assert_saved_binding(root, contributor["raw_maps"])
                original_bytes = {p.name: p.read_bytes() for p in (root / "failed").iterdir()}
                with self.assertRaises(FileExistsError):
                    probe.collect_block(root, block, spec, lambda rows: maps[rows[0]["source_frame_index"]],
                                        root / "failed", expected)
                self.assertEqual(original_bytes, {p.name: p.read_bytes() for p in (root / "failed").iterdir()})

    def test_diagnostics_distinguish_weak_off_target_and_averaging_dilution(self):
        block = synthetic_block()
        frame = block["frames"][0]
        weak = np.zeros((288, 512), np.float32)
        weak[30, 40] = .2
        weak_result = probe.diagnostic_map(weak, frame, block)
        self.assertEqual(weak_result["global_peak"]["heatmap_xy"], [40, 30])
        self.assertEqual(weak_result["global_peak"]["reference_distance_px"], 0)
        self.assertEqual(weak_result["strict_threshold_pixel_count"], 0)
        self.assertEqual(weak_result["components"], [])
        off_target = weak.copy()
        off_target[100, 200] = .8
        off_result = probe.diagnostic_map(off_target, frame, block)
        self.assertEqual(off_result["global_peak"]["heatmap_xy"], [200, 100])
        self.assertEqual(off_result["local_peak"]["heatmap_xy"], [40, 30])
        self.assertEqual(len(off_result["components"]), 1)
        self.assertGreater(off_result["components"][0]["reference_distance_px"], 10)
        contributors = np.zeros((3, 288, 512), np.float32)
        contributors[0, 30, 40] = .7
        self.assertEqual(len(probe.diagnostic_map(contributors[0], frame, block)["components"]), 1)
        averaged = contributors.sum(axis=0, dtype=np.float32) / np.float32(3)
        mean_result = probe.diagnostic_map(averaged, frame, block)
        self.assertEqual(mean_result["local_peak"]["reference_distance_px"], 0)
        self.assertEqual(mean_result["components"], [])
        self.assertLess(mean_result["local_peak"]["value"], .3)

    def test_diagnostic_uses_strict_threshold_and_inclusive_native_ten_pixel_radius(self):
        block = synthetic_block()
        heatmap = np.zeros((288, 512), np.float32)
        heatmap[30, 40] = np.float32(.3)
        heatmap[30, 50] = np.nextafter(np.float32(.3), np.float32(1))
        heatmap[30, 51] = np.float32(.9)
        result = probe.diagnostic_map(heatmap, block["frames"][0], block)
        self.assertEqual(result["strict_threshold_pixel_count"], 2)
        self.assertEqual(result["local_strict_threshold_pixel_count"], 1)
        self.assertEqual(result["local_peak"]["source_xy_px"], [50.0, 30.0])
        self.assertEqual(result["local_peak"]["reference_distance_px"], 10)
        self.assertEqual(result["integer_target_center_xy"], [40, 30])
        self.assertEqual(result["target_quantization_error_px"], 0)

    def test_frozen_inputs_consume_actual_cache_producer_without_preparing_or_modifying_it(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            block = synthetic_block(100, 5)
            block["source_video"] = {"width_px": 64, "height_px": 36}
            for offset, frame in enumerate(block["frames"]):
                rgb = np.empty((36, 64, 3), np.uint8)
                rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2] = offset * 31, 170 - offset * 17, 50 + offset
                path = root / f"frame_{offset}.png"
                Image.fromarray(rgb).save(path)
                frame["png"] = {**runtime.binding(root, path), "rgb_sha256": hashlib.sha256(rgb.tobytes()).hexdigest()}
            package = {"training_blocks": [], "validation_blocks": [block], "protected_ranges": {}}
            producing_store = runtime.FrameStore(root, package, root / "cache")
            try:
                prepared = producing_store.prepare()
                expected = producing_store.inputs(block["block_id"], [101, 102, 103])
            finally:
                producing_store.close()
            original = {p.relative_to(root): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}
            scope = {"block_id": block["block_id"], "triplet_starts": [101], "target_frames": [102],
                     "cache_receipt": prepared["blocks"][0]}
            with patch.object(runtime.FrameStore, "prepare", side_effect=AssertionError("Frozen inputs cannot rebuild cache")):
                store = probe.FrozenInputs(root, package, [scope])
                try:
                    verified = store.verify_sources()
                    self.assertEqual([r["source_frame_index"] for r in verified], [101, 102, 103])
                    self.assertTrue(all(r["exact_warp_and_normalization_match"] for r in verified))
                    self.assertTrue(torch.equal(store.inputs(block["block_id"], [101, 102, 103]), expected))
                    with self.assertRaisesRegex(ValueError, "Undeclared triplet"):
                        store.inputs(block["block_id"], [100, 101, 102])
                finally:
                    store.close()
            self.assertEqual(original, {p.relative_to(root): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in root.rglob("*") if p.is_file()})

    def test_state_digest_includes_batch_norm_float_and_integer_buffers(self):
        model = torch.nn.Sequential(torch.nn.Conv2d(1, 1, 1, bias=False), torch.nn.BatchNorm2d(1))
        with torch.no_grad():
            model[0].weight.fill_(0.25)
        original = probe.state_digest(model)
        self.assertEqual(original, probe.state_digest(copy.deepcopy(model)))
        with torch.no_grad():
            model[1].running_mean.add_(0.125)
        changed_float = probe.state_digest(model)
        self.assertNotEqual(original, changed_float)
        with torch.no_grad():
            model[1].num_batches_tracked.add_(1)
        self.assertNotEqual(changed_float, probe.state_digest(model))


if __name__ == "__main__":
    unittest.main()
