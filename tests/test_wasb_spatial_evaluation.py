"""Actual CPU producers verify spatial and saved matched-control transport."""
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

from src.ball_tracking import wasb_spatial_evaluation as evaluate
from src.ball_tracking import nba_resolution_evaluation as source_evaluation
from src.ball_tracking import wasb_resolution as resolution
from src.ball_tracking import completion_training_runtime as runtime
from src.ball_tracking.nba_first_validation import score_block


class Store:
    width, height, radius = 768, 432, 3.75
    resolution = {"width": 768, "height": 432, "target_radius": 3.75}

    def inputs(self, block_id, indices):
        return torch.zeros((9, 432, 768), dtype=torch.float32)


class Model(torch.nn.Module):
    def forward(self, inputs):
        logits = torch.full((1, 3, 432, 768), -20.0)
        logits[:, :, 144, 240] = 1.0986123
        return {0: logits}


class SpatialEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.temp = tempfile.TemporaryDirectory(prefix="spatial_evaluation_cpu_", dir=self.root / "data/outputs/t")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.cuda_guard = patch.object(torch.cuda, "_lazy_init", side_effect=AssertionError("No CUDA initialization in CPU tests"))
        self.cuda_guard.start()
        self.addCleanup(self.cuda_guard.stop)
        old_threads = torch.get_num_threads()
        torch.set_num_threads(2)
        self.addCleanup(torch.set_num_threads, old_threads)
        self.block = {"block_id": "synthetic_hou", "domain": "nba", "game_id": "synthetic",
            "role": "checkpoint_validation", "time_base": "1/90000", "range_inclusive": [100, 103],
            "source_video": {"width_px": 64, "height_px": 36, "frame_count": 200,
                             "sha256": hashlib.sha256(b"synthetic unopened source").hexdigest()}, "frames": []}
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
                "game_ball_identity_certainty": "certain" if offset in (0, 3) else "ambiguous",
                "geometry": {"center_xy_px": [20, 12], "source": "observed_complete_ball_center",
                             "uncertainty_radius_px": 2} if offset == 0 else None,
                "localization_eligible": offset == 0, "difficulty_tags": [], "notes": "Synthetic accepted producer fixture"}
            self.block["frames"].append({"source_frame_index": index, "source_pts_ticks": pts,
                "duration_ticks": duration, "state": "permitted", "block_id": self.block["block_id"],
                "reference_role": "checkpoint_validation", "annotation": annotation,
                "png": {**runtime.binding(self.root, path), "rgb_sha256": hashlib.sha256(rgb.tobytes()).hexdigest()}})
            pts += duration
        self.identity = {"arm": "spatial", "synthetic": "actual spatial report transport"}
        self.checkpoint = self.weight("checkpoint")
        self.report = self.make_report(6, self.checkpoint, [self.block])

    def weight(self, name):
        path = self.folder / (name + ".pth")
        path.write_bytes(("Never deserialize synthetic checkpoint " + name).encode())
        return runtime.binding(self.root, path)

    def json_file(self, name, value):
        path = self.folder / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return runtime.binding(self.root, path)

    def make_report(self, epoch, checkpoint, blocks):
        report = resolution.validate_epoch(Model(), "cpu", Store(), {"validation_blocks": blocks}, epoch, checkpoint)
        report["identity"] = self.identity
        return report

    def test_actual_fresh_absolute_epoch_producer_reuse_is_exact(self):
        original = deepcopy(self.report)
        rows = evaluate.reuse_validation(self.root, self.block, self.report, self.identity, self.checkpoint)
        self.assertEqual(rows, self.report["blocks"][0]["observations"])
        self.assertEqual(rows[0]["center_xy_px"], [20, 12])
        self.assertEqual([row["temporal_contributions"] for row in rows], [1, 2, 2, 1])
        self.assertEqual(self.report, original)

    def test_reuse_rejects_anchor_foreign_arm_checkpoint_and_failed_transport(self):
        for changes in ({"epoch": 5}, {"epoch": 11}, {"reused_validation": {"source_report": "old"}},
                        {"identity": {**self.identity, "arm": "constant"}},
                        {"checkpoint": self.weight("foreign")}, {"threshold": .25},
                        {"resolution": {"width": 512, "height": 288, "target_radius": 2.5}}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                evaluate.reuse_validation(self.root, self.block, {**self.report, **changes}, self.identity, self.checkpoint)
        for field, value in (("source_pts_ticks", 1), ("source_png", {}), ("inference_status", "failed"), ("point_origin", "manual")):
            report = deepcopy(self.report)
            report["blocks"][0]["observations"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                evaluate.reuse_validation(self.root, self.block, report, self.identity, self.checkpoint)

    def test_existing_cache_cannot_be_created_and_reuses_exact_original_bytes(self):
        folder = self.folder / "cache"
        cache = evaluate.ExistingInputCache(self.root, [self.block], folder)
        with patch.object(evaluate.nba.evaluation, "NativeImages", side_effect=AssertionError("No source pixels for absent cache")):
            with self.assertRaisesRegex(ValueError, "Existing resolution input cache required"):
                cache.prepare()
        self.assertFalse(folder.exists())
        original = source_evaluation.InputCache(self.root, [self.block], folder)
        receipts = original.prepare()
        original.close()
        before = {p: p.read_bytes() for p in folder.rglob("*") if p.is_file()}
        try:
            actual = cache.prepare()
            expected, _ = resolution.preprocess_triplet(self.rgb[:3])
            self.assertEqual(actual, receipts)
            self.assertTrue(torch.equal(cache.inputs(self.block["block_id"], [100, 101, 102]).unsqueeze(0), expected))
        finally:
            cache.close()
        self.assertEqual({p: p.read_bytes() for p in folder.rglob("*") if p.is_file()}, before)

    def test_actual_saved_control_producers_bind_without_model_or_pixel_access(self):
        source_recipe_path = self.root / "configs/ball_tracking/proposals/wasb_resolution_v0_1.json"
        source_recipe = evaluate.read_json(source_recipe_path)
        config = evaluate.read_json(evaluate.bound_path(self.root, source_recipe["nba_first_config"]))
        package = evaluate.read_json(evaluate.bound_path(self.root, config["training_package"]))
        comparison = evaluate.read_json(evaluate.bound_path(self.root, config["comparison_package"]))
        blocks = evaluate.nba.blocks_from_packages(package, comparison)
        recipe = {"source_recipe": runtime.binding(self.root, source_recipe_path),
                  "source_completed": runtime.binding(self.root, self.root / source_recipe["output_root"] / "completed.json"),
                  "source_evaluation": runtime.binding(self.root, self.root / source_recipe["evaluation_output_root"] / "evaluation.json")}
        source_fit = evaluate.read_json(evaluate.bound_path(self.root, recipe["source_completed"]))
        recipe["source_state"] = source_fit["resume_checkpoint"]
        recipe["matched_control_recipe"] = runtime.binding(self.root, self.root / "configs/ball_tracking/proposals/wasb_continuation_v0_1.json")
        control_root = self.root / "data/outputs/ball_tracking/wasb_continuation_v0_1/constant"
        recipe["matched_control_completed"] = runtime.binding(self.root, control_root / "fit_v0_1/completed.json")
        recipe["matched_control_evaluation"] = runtime.binding(self.root, control_root / "nba_comparison_v0_1/evaluation.json")
        recipe["matched_control_comparison_completed"] = runtime.binding(self.root, control_root / "nba_comparison_v0_1/completed.json")
        with patch.object(torch, "load", side_effect=AssertionError("No tensor loads")), \
             patch.object(np, "load", side_effect=AssertionError("No mean/cache arrays for saved controls")), \
             patch.object(evaluate.nba.evaluation, "NativeImages", side_effect=AssertionError("No pixels")):
            controls = evaluate.read_controls(self.root, blocks, recipe, source_recipe)
        self.assertEqual(set(controls), set(evaluate.CONTROLS))
        det = next(block for block in blocks if block["block_id"].startswith("sas_det"))
        self.assertEqual(controls["resolution_epoch5"]["blocks"][det["block_id"]]["score"]["summary"]["matched"], 219)
        self.assertEqual(controls["augmentation_epoch5"]["blocks"][det["block_id"]]["score"]["summary"]["matched"], 212)
        self.assertEqual(controls["constant_epoch6"]["blocks"][det["block_id"]]["score"]["summary"]["matched"], 219)
        self.assertEqual(controls["constant_epoch7"]["blocks"][det["block_id"]]["score"]["summary"]["matched"], 218)
        for epoch in (6, 7):
            self.assertEqual(controls[f"constant_epoch{epoch}"]["absolute_epoch"], epoch)
            self.assertEqual(len(controls[f"constant_epoch{epoch}"]["secondary_NFHS_validation"]), 6)
        emitted_path = evaluate.bound_path(self.root, controls["constant_epoch6"]["blocks"][blocks[0]["block_id"]]["records"])
        emitted = evaluate.read_json(emitted_path)
        original_read = evaluate.read_json
        for field, value in (("arm", "cosine"), ("epoch", 7), ("model", "continuation_constant_epoch7"), ("score", {})):
            def corrupted_read(path):
                return {**emitted, field: value} if Path(path) == emitted_path else original_read(path)
            with self.subTest(saved_control_field=field), patch.object(evaluate, "read_json", side_effect=corrupted_read), self.assertRaises(ValueError):
                evaluate.read_matched_controls(self.root, blocks, recipe)
        cosine_fit = runtime.binding(self.root, control_root.parent / "cosine/fit_v0_1/completed.json")
        with self.assertRaisesRegex(ValueError, "Matched constant fit"):
            evaluate.read_matched_controls(self.root, blocks, {**recipe, "matched_control_completed": cosine_fit})
        with self.assertRaisesRegex(ValueError, "Source resolution comparison identity"):
            evaluate.read_controls(self.root, blocks, {**recipe, "source_completed": self.json_file("wrong_source.json", {})}, source_recipe)

    def execution_fixture(self):
        blocks = []
        for index in range(8):
            block = deepcopy(self.block)
            block["block_id"] = f"synthetic_context_{index}"
            for frame in block["frames"]:
                frame["block_id"] = block["block_id"]
                frame["reference_role"] = "checkpoint_validation" if index < 6 else "historical_training" if index == 6 else "excluded_development"
            blocks.append(block)
        nfhs = deepcopy(self.block)
        nfhs.update(block_id="synthetic_nfhs", domain="nfhs", game_id="possession_001")
        for frame in nfhs["frames"]:
            frame["block_id"] = nfhs["block_id"]
        reports = [self.make_report(epoch, self.weight(f"epoch{epoch}"), [*blocks[:6], nfhs]) for epoch in range(5, 8)]
        reports[0]["reused_validation"] = {"synthetic_anchor": True}
        links = {report["epoch"]: self.json_file(f"validation{report['epoch']}.json", report) for report in reports}
        controls = {}
        for name in evaluate.CONTROLS:
            controls[name] = {"checkpoint": self.checkpoint, "training_exposure": {"synthetic": True}, "secondary_NFHS_validation": [], "blocks": {}}
            for block in blocks:
                rows = self.make_report(6, self.checkpoint, [block])["blocks"][0]["observations"]
                controls[name]["blocks"][block["block_id"]] = {"score": score_block(block, rows), "records": links[5]}
        result = {"identity": self.identity, "arm": "spatial", "validation_reports": list(links.values()),
                  "checkpoints": [report["checkpoint"] for report in reports[1:]]}
        audit = {"training_transport": {"training_result": self.json_file("training_completed.json", result)},
                 "new_model_calls": 8, "reused_HOU_observation_frames": 48, "models": 2}
        cache_folder = self.folder / "cache"
        cache = source_evaluation.InputCache(self.root, blocks[6:], cache_folder)
        cache.prepare()
        cache.close()
        recipe = {"evaluation_output_root": (self.folder / "comparison").relative_to(self.root).as_posix(),
                  "evaluation_cache_root": cache_folder.relative_to(self.root).as_posix(), "source_evaluation": links[5], "matched_control_evaluation": links[5], "matched_control_comparison_completed": links[5]}
        recipe_path = self.json_file("recipe.json", recipe)["path"]
        return recipe_path, (recipe, blocks, result, reports[1:], links, controls, audit)

    def run_fixture(self, recipe_path, fixture, infer=None):
        with patch.object(evaluate, "preflight", return_value=fixture), \
             patch.object(evaluate.nba.evaluation, "make_adapter", side_effect=lambda *a, **k: SimpleNamespace(model=Model(), device="cpu")), \
             patch.object(evaluate.torch.cuda, "empty_cache"), \
             patch.object(resolution, "infer", side_effect=infer or resolution.infer):
            return evaluate.execute(self.root, recipe_path)

    def test_actual_cpu_inference_resume_and_completed_consumer_preserve_arm_epochs(self):
        recipe_path, fixture = self.execution_fixture()
        original_infer, invoked = resolution.infer, []
        def interrupt_second(*args, **kwargs):
            invoked.append((args[5], args[0]["block_id"]))
            if len(invoked) == 2:
                raise RuntimeError("synthetic interruption")
            return original_infer(*args, **kwargs)
        with self.assertRaisesRegex(RuntimeError, "synthetic interruption"):
            self.run_fixture(recipe_path, fixture, interrupt_second)
        destination = self.root / fixture[0]["evaluation_output_root"]
        failed = list((destination / "attempts").glob("*/failed.json"))
        self.assertEqual(len(failed), 1)
        resumed = []
        def resume_infer(*args, **kwargs):
            resumed.append((args[5], args[0]["block_id"]))
            return original_infer(*args, **kwargs)
        completed = self.run_fixture(recipe_path, fixture, resume_infer)
        self.assertNotIn(invoked[0], resumed)
        self.assertEqual(len(resumed), 3)
        self.assertEqual((completed["completed_block_calls_this_attempt"], completed["total_receipted_model_calls"]), (6, 8))
        published = evaluate.read_json(self.root / completed["evaluation"]["path"])
        self.assertEqual([model["epoch"] for model in published["models"]], [6, 7])
        self.assertEqual([model["name"] for model in published["models"]], [f"spatial_epoch{e}" for e in range(6, 8)])
        self.assertEqual(published["reused_validation_frames"], 48)
        self.assertEqual([m["matched_control"] for m in published["models"]], ["constant_epoch6", "constant_epoch7"])
        self.assertTrue(all(set(m["comparisons"]) == set(evaluate.CONTROLS) for m in published["models"]))
        self.assertEqual(published["models"][0]["secondary_NFHS_validation"][0]["block_id"], "synthetic_nfhs")
        self.assertEqual(published["models"][0]["secondary_NFHS_validation"][0]["matched"], 1)
        self.assertNotIn("observations", published["models"][0]["secondary_NFHS_validation"][0])
        self.assertIsNone(published["earliest_epoch_for_human_review"])
        self.assertFalse(published["model_adopted"])
        with patch.object(evaluate, "preflight", return_value=fixture), \
             patch.object(evaluate.nba.evaluation, "make_adapter", side_effect=AssertionError("No completed-run model load")), \
             patch.object(evaluate, "ExistingInputCache", side_effect=AssertionError("No completed-run cache access")):
            self.assertEqual(evaluate.execute(self.root, recipe_path), completed)
        self.assertTrue(failed[0].exists())

    def test_completed_consumer_rejects_forged_arm_epoch_and_score_even_with_rebound_hash(self):
        recipe_path, fixture = self.execution_fixture()
        completed = self.run_fixture(recipe_path, fixture)
        published = evaluate.read_json(self.root / completed["evaluation"]["path"])
        receipt_link = published["models"][0]["records"][0]["receipt"]
        receipt = evaluate.read_json(self.root / receipt_link["path"])
        original = evaluate.read_json(self.root / receipt["records"]["path"])
        report, block = fixture[3][0], fixture[1][0]
        for field, value in (("arm", "cosine"), ("epoch", 5), ("model", "spatial_epoch7"),
                             ("checkpoint", self.weight("foreign_completed")), ("score", {})):
            changed = self.json_file(f"bad_{field}.json", {**original, field: value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                evaluate.validate_block(self.root, block, report, completed["identity"],
                    {**receipt, "records": changed}, "spatial_epoch6", fixture[4][6])
        for field, value in (("matched_control", "constant_epoch7"), ("secondary_NFHS_validation", [{"forged": True}])):
            forged = deepcopy(published)
            forged["models"][0][field] = value
            altered = {**completed, "evaluation": self.json_file(f"forged_{field}.json", forged)}
            with self.subTest(publication_field=field), self.assertRaisesRegex(ValueError, "matched epoch or secondary NFHS"):
                evaluate.validate_publication(self.root, altered, completed["identity"], fixture[3], fixture[4], fixture[1], fixture[5], fixture[6])

    def test_metadata_preflight_consumes_actual_report_epochs_without_model_or_pixels(self):
        recipe_path, fixture = self.execution_fixture()
        recipe, blocks, result, reports, links, controls, audit = fixture
        source_recipe = {"nba_first_config": {"path": "synthetic_config"}}
        recipe.update(source_recipe=self.json_file("source_recipe.json", source_recipe),
                      evaluation_cache_root=evaluate.CACHE_ROOT,
                      code_bindings=[runtime.binding(self.root, Path(evaluate.__file__))])
        recipe["evaluation_output_root"] = evaluate.output_root()
        (self.root / recipe_path).write_text(json.dumps(recipe))
        with patch.object(evaluate.training, "audit_completed_result", return_value=(result, audit["training_transport"])), \
             patch.object(evaluate.nba, "preflight", return_value=({}, blocks, {})), \
             patch.object(evaluate, "read_controls", return_value=controls), \
             patch.object(torch, "load", side_effect=AssertionError("No tensors")), \
             patch.object(evaluate.nba.evaluation, "NativeImages", side_effect=AssertionError("No pixels")):
            actual = evaluate.preflight(self.root, recipe_path)
        self.assertEqual([r["epoch"] for r in actual[3]], [6, 7])
        self.assertEqual(actual[-1]["absolute_epochs"], [6, 7])
        with patch.object(evaluate.training, "audit_completed_result", return_value=({**result, "arm": "constant"}, audit["training_transport"])):
            with self.assertRaisesRegex(ValueError, "different spatial pilot"):
                evaluate.preflight(self.root, recipe_path)


if __name__ == "__main__":
    unittest.main()
