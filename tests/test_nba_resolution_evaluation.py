"""Actual CPU validation/inference producers and immutable comparison transport."""
from copy import deepcopy
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

from src.ball_tracking import nba_resolution_evaluation as evaluate
from src.ball_tracking import wasb_resolution as resolution
from src.ball_tracking import completion_training_runtime as runtime
from src.ball_tracking.nba_first_validation import score_block


class Store:
    width, height, radius = 768, 432, 3.75
    resolution = {"width": 768, "height": 432, "target_radius": 3.75}

    def inputs(self, block_id, indices):
        result = torch.zeros((9, 432, 768), dtype=torch.float32)
        result[0, 0, 0] = indices[0]
        return result


class Model(torch.nn.Module):
    """Finite CPU logits; no real checkpoint or model is loaded."""
    def forward(self, inputs):
        logits = torch.full((1, 3, 432, 768), -20.0)
        start = int(inputs[0, 0, 0, 0])
        for channel in range(3):
            if start + channel in {100, 102}:
                logits[0, channel, 144, 240] = 1.0986123
        return {0: logits}


class ResolutionEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        temp_root = self.root / "data/outputs/t"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="resolution_evaluation_cpu_", dir=temp_root)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        old = torch.get_num_threads()
        torch.set_num_threads(2)
        self.addCleanup(torch.set_num_threads, old)
        self.block = {"block_id": "synthetic_hou", "domain": "nba", "game_id": "synthetic",
            "role": "checkpoint_validation", "time_base": "1/90000", "range_inclusive": [100, 103],
            "source_video": {"width_px": 64, "height_px": 36, "frame_count": 200,
                             "sha256": hashlib.sha256(b"synthetic video never opened").hexdigest()}, "frames": []}
        self.rgb = []
        pts = 900000
        for offset, duration in enumerate((1440, 1530, 1530, 1440)):
            index = 100 + offset
            rgb = np.zeros((36, 64, 3), dtype=np.uint8)
            rgb[:, :, 0] = np.arange(64, dtype=np.uint8)[None, :] + 20 * offset
            rgb[:, :, 1] = np.arange(36, dtype=np.uint8)[:, None] * 3
            rgb[:, :, 2] = 100 + offset * 10
            self.rgb.append(rgb)
            path = self.folder / f"native_{index}.png"
            Image.fromarray(rgb).save(path)
            annotation = {"frame_index": index, "annotation_status": "labeled",
                "visibility": "fully_visible" if offset == 0 else "not_visible" if offset == 3 else "indeterminate",
                "absence_reason": "occluded" if offset == 3 else None,
                "game_ball_identity_certainty": "certain" if offset in {0, 3} else "ambiguous",
                "geometry": {"center_xy_px": [20, 12], "source": "observed_complete_ball_center", "uncertainty_radius_px": 2} if offset == 0 else None,
                "localization_eligible": offset == 0, "difficulty_tags": [], "notes": "Synthetic accepted producer fixture"}
            self.block["frames"].append({"source_frame_index": index, "source_pts_ticks": pts,
                "duration_ticks": duration, "state": "permitted", "block_id": self.block["block_id"],
                "reference_role": "checkpoint_validation", "annotation": annotation,
                "png": {**runtime.binding(self.root, path), "rgb_sha256": hashlib.sha256(rgb.tobytes()).hexdigest()}})
            pts += duration
        self.checkpoint = self.weight("checkpoint")
        self.identity = {"synthetic": "actual producer transport"}
        self.report = resolution.validate_epoch(Model(), "cpu", Store(), {"validation_blocks": [self.block]}, 1, self.checkpoint)
        self.report["identity"] = self.identity

    def weight(self, name):
        path = self.folder / (name + ".pth")
        path.write_bytes(("Never deserialize: " + name).encode())
        return runtime.binding(self.root, path)

    def json_file(self, name, body):
        path = self.folder / name
        path.write_text(json.dumps(body), encoding="utf-8")
        return runtime.binding(self.root, path)

    def observations(self):
        return evaluate.reuse_validation(self.root, self.block, self.report, self.identity, self.checkpoint)

    def test_actual_768_validation_producer_reuses_native_outputs_unchanged(self):
        original = deepcopy(self.report)
        rows = self.observations()
        self.assertEqual(rows, self.report["blocks"][0]["observations"])
        self.assertEqual([r["temporal_contributions"] for r in rows], [1, 2, 2, 1])
        self.assertEqual(rows[0]["center_xy_px"], [20, 12])
        self.assertIsNone(rows[1]["center_xy_px"])
        self.assertEqual(self.report, original)

    def test_reuse_rejects_512_resolution_foreign_checkpoint_failed_or_manual_output(self):
        for alteration in ({"resolution": {"width": 512, "height": 288, "target_radius": 2.5}},
                           {"reused_validation": {}}, {"protected_frames": 1}, {"threshold": .25},
                           {"checkpoint": self.weight("wrong")}):
            with self.subTest(alteration=alteration), self.assertRaises(ValueError):
                evaluate.reuse_validation(self.root, self.block, {**self.report, **alteration}, self.identity, self.checkpoint)
        for field, value in (("source_pts_ticks", 0), ("temporal_contributions", 3), ("source_png", {}),
                             ("inference_status", "failed"), ("point_origin", "manual")):
            report = deepcopy(self.report)
            report["blocks"][0]["observations"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                evaluate.reuse_validation(self.root, self.block, report, self.identity, self.checkpoint)

    def prepare_cache(self, block=None):
        cache = evaluate.InputCache(self.root, [block or self.block], self.folder / "cache")
        self.addCleanup(cache.close)
        try:
            return cache, cache.prepare()
        except BaseException:
            cache.close()
            raise

    def test_native_image_only_cache_matches_actual_resolution_preprocessor_and_resumes(self):
        block = deepcopy(self.block)
        for frame in block["frames"]:
            frame["annotation"] = None
        cache, receipts = self.prepare_cache(block)
        actual = cache.inputs(block["block_id"], [100, 101, 102])
        expected, _ = resolution.preprocess_triplet(self.rgb[:3])
        self.assertTrue(torch.equal(actual.unsqueeze(0), expected))
        self.assertEqual(tuple(actual.shape), (9, 432, 768))
        record = json.loads((self.root / receipts[0]["receipt"]["path"]).read_text())
        self.assertEqual(record["annotation_targets_created"], 0)
        self.assertEqual(record["source_video_decodes"], 0)
        cache.close()
        resumed, second = self.prepare_cache(block)
        self.assertEqual(second, receipts)
        self.assertTrue(torch.equal(resumed.inputs(block["block_id"], [100, 101, 102]), actual))

    def test_cache_rejects_stale_identity_malformed_array_and_protected_scope(self):
        cache, receipts = self.prepare_cache()
        cache.close()
        path = self.root / receipts[0]["receipt"]["path"]
        original = json.loads(path.read_text())
        bad = deepcopy(original)
        bad["identity"]["resolution"]["width"] = 512
        path.write_text(json.dumps(bad))
        with self.assertRaisesRegex(ValueError, "identity changed"):
            self.prepare_cache()
        array_path = self.root / original["array"]["path"]
        np.save(array_path, np.zeros((4, 288, 512, 3), np.uint8), allow_pickle=False)
        original["array"] = runtime.binding(self.root, array_path)
        path.write_text(json.dumps(original))
        with self.assertRaisesRegex(ValueError, "shape or dtype"):
            self.prepare_cache()
        block = deepcopy(self.block)
        block["frames"][0]["state"] = "withheld"
        with self.assertRaisesRegex(ValueError, "permitted NBA"):
            self.prepare_cache(block)

    def test_gains_losses_use_actual_scored_producer_and_reject_different_reference_join(self):
        original = score_block(self.block, self.observations())
        observations = deepcopy(self.observations())
        # Actual component producer emits an empty observation from a zero mean.
        segment = {"kind": "synthetic", "source_frame_range_inclusive": [100, 103]}
        observations[0] = resolution.select_observation(self.block["frames"][0], np.zeros((432, 768), np.float32), 1, self.block, segment)
        candidate = score_block(self.block, observations)
        delta = evaluate.gains_losses(candidate, original)
        self.assertEqual(delta["frame_indices"]["lost_matches"], [100])
        self.assertEqual(delta["counts"]["gained_matches"], 0)
        self.assertFalse(delta["semantic_wrong_object_inferred"])
        altered = deepcopy(original)
        altered["frame_results"][0]["reference_category"] = "reference_unlabeled"
        with self.assertRaisesRegex(ValueError, "reference/native"):
            evaluate.gains_losses(candidate, altered)

    def test_earliest_review_candidate_requires_explicit_gates_and_all_contexts(self):
        score = score_block(self.block, self.observations())
        episodes = [{"summary": deepcopy(score["summary"])} for _ in range(8)]
        for episode in episodes:
            for gate in evaluate.AUTOMATIC_GATES:
                episode["summary"]["gates"][gate]["status"] = "pass"
        models = [{"epoch": 2, "episodes": deepcopy(episodes)}, {"epoch": 1, "episodes": deepcopy(episodes)}]
        self.assertEqual(evaluate.qualifying_epoch(models), 1)
        for status in ("fail", "inconclusive", None):
            bad = deepcopy(models)
            for model in bad:
                model["episodes"][0]["summary"]["gates"]["recovery"]["status"] = status
            self.assertIsNone(evaluate.qualifying_epoch(bad))
        bad = deepcopy(models[:1])
        del bad[0]["episodes"][0]["summary"]["gates"]["recovery"]
        self.assertIsNone(evaluate.qualifying_epoch(bad))
        with self.assertRaisesRegex(ValueError, "eight"):
            evaluate.qualifying_epoch([{"epoch": 1, "episodes": episodes[:7]}])

    def execution_fixture(self):
        blocks = []
        for index in range(8):
            block = deepcopy(self.block)
            block["block_id"] = f"synthetic_context_{index}"
            for frame in block["frames"]:
                frame["block_id"] = block["block_id"]
                frame["reference_role"] = "checkpoint_validation" if index < 6 else "historical_training" if index == 6 else "excluded_development"
            blocks.append(block)
        reports, bindings = [], []
        for epoch in range(6):
            checkpoint = self.weight(f"epoch{epoch}")
            report = resolution.validate_epoch(Model(), "cpu", Store(), {"validation_blocks": blocks[:6]}, epoch, checkpoint)
            report["identity"] = self.identity
            reports.append(report)
            bindings.append(self.json_file(f"validation{epoch}.json", report))
        controls = {}
        for name in evaluate.CONTROLS:
            controls[name] = {"checkpoint": self.checkpoint, "training_exposure": {"synthetic": True}, "blocks": {}}
            for block in blocks:
                rows = deepcopy(self.observations())
                controls[name]["blocks"][block["block_id"]] = {"score": score_block(block, rows), "records": bindings[0]}
        completed_binding = self.json_file("training_completed.json", {"identity": self.identity})
        result = {"identity": self.identity, "validation_reports": bindings}
        audit = {"training_transport": {"training_result": completed_binding}, "new_model_calls": 20,
                 "reused_HOU_observation_frames": 120, "models": 5}
        recipe_binding = self.json_file("recipe.json", {"synthetic": True})
        recipe = {"nba_control_evaluation": bindings[0]}
        return recipe_binding["path"], (recipe, blocks, result, reports[1:], controls, audit)

    def test_actual_cpu_inference_receipts_resume_after_failure_without_repeating_completed_blocks(self):
        recipe_path, fixture = self.execution_fixture()
        destination = (self.folder / "comparison").relative_to(self.root).as_posix()
        original_infer = resolution.infer
        invoked = []
        def interrupt_second(*args, **kwargs):
            invoked.append((args[5], args[0]["block_id"]))
            if len(invoked) == 2:
                raise RuntimeError("synthetic interruption before second block")
            return original_infer(*args, **kwargs)
        with patch.object(evaluate, "preflight", return_value=fixture), patch.object(evaluate, "OUTPUT_ROOT", destination), \
             patch.object(evaluate.nba.evaluation, "make_adapter", side_effect=lambda *a, **k: SimpleNamespace(model=Model(), device="cpu")) as loader, \
             patch.object(evaluate.torch.cuda, "empty_cache"), patch.object(resolution, "infer", side_effect=interrupt_second):
            with self.assertRaisesRegex(RuntimeError, "synthetic interruption"):
                evaluate.execute(self.root, recipe_path)
        failed = list((self.root / destination / "attempts").glob("*/failed.json"))
        self.assertEqual(len(failed), 1)
        resumed_calls = []
        def resume_infer(*args, **kwargs):
            resumed_calls.append((args[5], args[0]["block_id"]))
            return original_infer(*args, **kwargs)
        with patch.object(evaluate, "preflight", return_value=fixture), patch.object(evaluate, "OUTPUT_ROOT", destination), \
             patch.object(evaluate.nba.evaluation, "make_adapter", side_effect=lambda *a, **k: SimpleNamespace(model=Model(), device="cpu")), \
             patch.object(evaluate.torch.cuda, "empty_cache"), patch.object(resolution, "infer", side_effect=resume_infer):
            completed = evaluate.execute(self.root, recipe_path)
        self.assertNotIn(invoked[0], resumed_calls)
        self.assertEqual(len(resumed_calls), 9)
        self.assertEqual(completed["completed_block_calls_this_attempt"], 18)
        self.assertEqual(completed["total_receipted_model_calls"], 20)
        publication = json.loads((self.root / completed["evaluation"]["path"]).read_text())
        self.assertEqual(len(publication["models"]), 5)
        self.assertEqual(publication["reused_validation_frames"], 120)
        self.assertFalse(publication["model_adopted"])
        self.assertIsNone(publication["earliest_epoch_for_human_review"])
        self.assertTrue(failed[0].exists())
        with patch.object(evaluate, "preflight", return_value=fixture), patch.object(evaluate, "OUTPUT_ROOT", destination), \
             patch.object(evaluate.nba.evaluation, "make_adapter", side_effect=AssertionError("Completed run must not load a model")):
            self.assertEqual(evaluate.execute(self.root, recipe_path), completed)


if __name__ == "__main__":
    unittest.main()
