"""Native producer contracts and tiny training mechanics; never run a real fit."""
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
from torch import nn

from src.ball_tracking import nba_wasb_adaptation as adaptation
from src.ball_tracking import wasb_training as training
from src.ball_tracking.wasb_experiment import write_once

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/ball_tracking/wasb_experiments/nba_wasb_adaptation_v0_1.json"
REAL_REFERENCE = ROOT / "data/outputs/ball_tracking/nba/hard_example_reference_v0_1/accepted/reference.json"


def native_fixture():
    # Native frame/PTS pairs captured from the approved SAC action-input producer.
    captured = [(940, 1416752), (941, 1418282), (942, 1419722), (943, 1421252), (944, 1422782)]
    frames = [{"source_frame_index": index, "source_pts_ticks": pts,
               "png": {"path": f"source_{index}.png", "sha256": "0" * 64, "rgb_sha256": "1" * 64}}
              for index, pts in captured]
    rows = [{"frame_index": index, "annotation_status": "labeled", "visibility": "fully_visible",
             "absence_reason": None, "game_ball_identity_certainty": "certain", "geometry": None,
             "localization_eligible": False, "difficulty_tags": [], "notes": "Synthetic accepted AI source fixture"}
            for index, _ in captured]
    rows[0].update(geometry={"center_xy_px": [3.0, 2.0], "uncertainty_radius_px": 1.0,
                            "source": "observed_complete_ball_center"}, localization_eligible=True)
    rows[-1].update(visibility="not_visible", absence_reason="occluded")
    reference = {"game_id": "0022500829", "candidate_id": "sac_mem_q1_c01",
                 "approved_role": "future_training_candidate_pool", "time_base": "1/90000",
                 "frames": frames, "annotations": rows,
                 "source_video": {"path": "parent_source.mp4", "sha256": "2" * 64,
                                  "width_px": 8, "height_px": 6, "frame_count": 1000},
                 "human_review": {"status": "accepted", "independent_human_annotation": False},
                 "origin": {"kind": "assistant_visual_proposal"}, "bindings": {"source_verification": {"fixture": True}}}
    specification = {"window_id": "sac_test", "game_id": "0022500829", "candidate_id": "sac_mem_q1_c01",
                     "reference_kind": "hard_example", "source_frame_range_inclusive": [940, 944]}
    return reference, specification


class NativeTrainingContracts(unittest.TestCase):
    def test_native_block_uses_captured_pts_and_keeps_unknowns_masked(self):
        reference, specification = native_fixture()
        block, labels = adaptation.native_block(reference, specification)
        self.assertEqual([f["source_pts_ticks"] for f in block["frames"]], [1416752, 1418282, 1419722, 1421252, 1422782])
        self.assertEqual([f["kind"] for f in block["frames"]], ["positive", "masked", "masked", "masked", "hidden"])
        triplets, excluded, counts = adaptation.compose_triplets([block])
        self.assertEqual([t["frame_indices"] for t in triplets], [[940, 941, 942], [942, 943, 944]])
        self.assertEqual([t["frame_indices"] for t in excluded], [[941, 942, 943]])
        self.assertEqual(counts["masked_frames"], 3)
        self.assertEqual(counts["hidden_frames"], 1)
        self.assertEqual(block["annotation_origin"], reference["origin"])
        for index, kind in ((940, "positive"), (941, "masked"), (944, "hidden")):
            target, valid, metadata = training.annotation_target(labels[index], 8, 6)
            self.assertEqual(metadata["kind"], kind)
            self.assertEqual(valid, kind != "masked")
            self.assertEqual(bool(np.any(target)), kind == "positive")

    def test_excluded_games_pending_review_gaps_timing_and_role_are_rejected(self):
        original, specification = native_fixture()
        mutations = [lambda r: r.update(game_id="0022500828"),
                     lambda r: r.update(approved_role="target_case_development"),
                     lambda r: r["human_review"].update(status="pending"),
                     lambda r: r["human_review"].update(independent_human_annotation=True),
                     lambda r: r["frames"][1].update(source_frame_index=999),
                     lambda r: r["frames"][1].update(source_pts_ticks=1416751),
                     lambda r: r["frames"][1].update(source_pts_ticks=1418283),
                     lambda r: r.update(time_base="1/25"),
                     lambda r: r["annotations"][1].update(frame_index=999)]
        for mutate in mutations:
            value = copy.deepcopy(original)
            mutate(value)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                adaptation.native_block(value, specification)

    def test_mixed_schedule_has_exact_sample_frame_exposure_without_cross_domain_context(self):
        reference, specification = native_fixture()
        nba_block, _ = adaptation.native_block(reference, specification)
        nfhs_block = copy.deepcopy(nba_block)
        nfhs_block.update(domain="nfhs", window_id="nfhs_test")
        nfhs_block["source_video"]["sha256"] = "3" * 64
        triplets, excluded, counts = adaptation.compose_triplets([nba_block, nfhs_block])
        schedule = training.sample_schedule(triplets)
        exposure = adaptation.exposure_report([nba_block, nfhs_block], triplets, schedule)
        self.assertEqual(counts["reviewed_frames"], 10)
        self.assertEqual(len(schedule["batches"]), 200)
        self.assertEqual(exposure["sample_count"], 400)
        self.assertEqual(exposure["samples_by_domain"], {"nba": 200, "nfhs": 200})
        self.assertEqual(sum(r["input_count"] for r in exposure["frame_exposure"]), 1200)
        self.assertEqual(sum(r["supervised_output_count"] for r in exposure["frame_exposure"]), 400)
        self.assertTrue(all(r["supervised_output_count"] == 0 for r in exposure["frame_exposure"] if r["kind"] == "masked"))
        self.assertTrue(all(sample["window_id"] in {"sac_test", "nfhs_test"} for sample in exposure["samples"]))
        self.assertEqual(training.sample_schedule(list(reversed(triplets))), schedule)
        with self.assertRaisesRegex(ValueError, "duplicate or overlap"):
            adaptation.compose_triplets([nba_block, copy.deepcopy(nba_block)])

    def test_native_png_examples_use_verified_source_pixels_and_never_open_recording(self):
        reference, specification = native_fixture()
        with tempfile.TemporaryDirectory(prefix="nba_native_training_") as folder:
            root = Path(folder)
            for offset, frame in enumerate(reference["frames"]):
                image = Image.new("RGB", (8, 6), (20 * offset, 50, 70))
                image.save(root / frame["png"]["path"])
                frame["png"].update(sha256=hashlib.sha256((root / frame["png"]["path"]).read_bytes()).hexdigest(),
                                    rgb_sha256=hashlib.sha256(image.tobytes()).hexdigest())
            block, labels = adaptation.native_block(reference, specification)
            triplets, _, _ = adaptation.compose_triplets([block])
            manifest = {"nfhs_manifest": {}, "triplets": triplets}
            with patch.object(training, "prepare_examples", return_value=({}, [])), \
                    patch.object(adaptation.cv2, "VideoCapture", side_effect=AssertionError("Do not decode NBA source")), \
                    patch.object(adaptation, "preprocess_triplet", wraps=adaptation.preprocess_triplet) as producer:
                examples, checks = adaptation.prepare_examples(root, manifest, {}, {}, {"sac_test": reference}, {"sac_test": labels})
            self.assertEqual(len(examples), 2)
            self.assertEqual([[int(frame[0, 0, 0]) for frame in call.args[0]] for call in producer.call_args_list],
                             [[0, 20, 40], [40, 60, 80]])
            self.assertEqual([example[2].tolist() for example in examples.values()], [[True, False, False], [False, False, True]])
            self.assertEqual(checks[0]["native_pngs_verified"], 5)
            self.assertEqual(checks[0]["source_video_decodes"], 0)
            frame = reference["frames"][0]
            (root / frame["png"]["path"]).write_bytes(b"changed PNG")
            with patch.object(training, "prepare_examples", return_value=({}, [])):
                with self.assertRaisesRegex(ValueError, "PNG hash mismatch"):
                    adaptation.prepare_examples(root, manifest, {}, {}, {"sac_test": reference}, {"sac_test": labels})


class TinyModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Conv2d(9, 3, 1)
        self.bn = nn.BatchNorm2d(3)

    def forward(self, inputs):
        return {0: self.bn(self.conv(inputs))}


class ContinuationMechanics(unittest.TestCase):
    def test_initialized_checkpoint_is_explicit_and_optimizer_is_fresh(self):
        model = TinyModel()
        with torch.no_grad():
            model.conv.weight.fill_(.2)
            model.bn.running_mean.fill_(.4)
        adapter = type("SyntheticAdapter", (), {"model": model, "device": torch.device("cpu")})()
        config = {"initialization": {"training_completion": {"path": "prior.json"}, "checkpoint": {"path": "expanded.pth"}}}
        nfhs = {"upstream_source": "source", "pretrained_checkpoint": {"path": "pretrained.pth"}}
        with tempfile.TemporaryDirectory(prefix="nba_initialization_") as folder:
            root = Path(folder)
            with patch.object(adaptation.torch.cuda, "is_available", return_value=True), \
                    patch.object(training, "seed_runtime"), \
                    patch.object(adaptation, "read_json", return_value={"training_provenance": {"prior": "reviewed"}}), \
                    patch.object(adaptation, "bound", side_effect=lambda root, value: root / value["path"]), \
                    patch.object(adaptation, "AdaptedWasbAdapter", return_value=adapter) as loader:
                actual, device, optimizer, buffers = adaptation.initialize(root, config, nfhs)
            self.assertEqual(loader.call_args.args[2], root / "expanded.pth")
            self.assertEqual(loader.call_args.args[3], adaptation.INITIAL_SHA)
            self.assertIs(actual, model)
            self.assertFalse(optimizer.state)
            self.assertEqual(optimizer.defaults["lr"], .0001)
            self.assertTrue(all(p.requires_grad for p in actual.parameters()))
            self.assertFalse(model.bn.training)
            before = model.conv.weight.detach().clone()
            training.training_step(model, optimizer, torch.ones(2, 9, 4, 4), torch.zeros(2, 3, 4, 4),
                                   torch.tensor([[True, False, True], [True, True, True]]))
            self.assertFalse(torch.equal(before, model.conv.weight))
            training.assert_batch_norm_unchanged(model, buffers)

    def test_final_checkpoint_publication_is_recoverable_without_training(self):
        model = TinyModel()
        buffers = training.freeze_batch_norm(model)
        optimizer = torch.optim.Adam(model.parameters(), lr=.0001)
        schedule = training.sample_schedule([{"triplet_id": "synthetic"}])
        losses = [{"update": i + 1, "loss": .1, "triplet_ids": ids} for i, ids in enumerate(schedule["batches"])]
        state = training._training_state(model, optimizer, {"synthetic": True}, schedule, 200, losses, buffers, {"synthetic": True})
        with tempfile.TemporaryDirectory(prefix="nba_publish_training_") as folder:
            root = Path(folder)
            for name in ("training_manifest.json", "sampling_schedule.json", "sample_exposure.json", "config.json"):
                write_once(root / name, {"synthetic": True})
            state_path = training.save_checkpoint_once(root / "update_000200.pth", state)
            config_binding = adaptation.binding(root, root / "config.json")
            with patch.object(TinyModel, "forward", side_effect=AssertionError("No training during publication")):
                first = adaptation.publish_final(root, root, config_binding, state_path, state, [])
                checkpoint = (root / "checkpoint.pth").read_bytes()
                second = adaptation.publish_final(root, root, config_binding, state_path, state, [])
            self.assertEqual(first, second)
            self.assertEqual(checkpoint, (root / "checkpoint.pth").read_bytes())
            self.assertEqual(first["checkpoint"]["bytes"], len(checkpoint))
            self.assertEqual(set(torch.load(root / "checkpoint.pth", map_location="cpu", weights_only=True)), {"model_state_dict"})
            self.assertEqual(first["initial_optimizer"], "fresh_Adam_no_parent_optimizer_state")
            changed = copy.deepcopy(state)
            changed["model_state_dict"]["conv.bias"].add_(1)
            with self.assertRaisesRegex(ValueError, "Existing final weights differ"):
                adaptation.publish_final(root, root, config_binding, state_path, changed, [])


@unittest.skipUnless(CONFIG.exists() and REAL_REFERENCE.exists(), "Approved local native-reference records unavailable")
class ActualApprovedMetadata(unittest.TestCase):
    def test_bound_real_preflight_uses_only_training_rows_without_loading_weights_or_images(self):
        original = Path.read_bytes
        reads = []
        def no_media_or_weights(path):
            self.assertNotIn(path.suffix.lower(), {".pth", ".pt", ".png", ".jpg", ".mp4"})
            reads.append(path.resolve())
            return original(path)
        with patch.object(Path, "read_bytes", no_media_or_weights), \
                patch.object(adaptation.torch, "load", side_effect=AssertionError("No checkpoint load during preflight")), \
                patch.object(adaptation.Image, "open", side_effect=AssertionError("No image decode during preflight")):
            result = adaptation.prepare(ROOT, CONFIG)
        self.assertEqual(result["manifest"]["counts"], {
            "positive_frames": 400, "hidden_frames": 36, "masked_frames": 14,
            "nba_frames": 300, "nfhs_frames": 150, "reviewed_frames": 450,
            "all_triplets": 434, "excluded_all_masked_triplets": 10, "usable_triplets": 424})
        self.assertEqual(result["exposure"]["samples_by_domain"], {"nba": 269, "nfhs": 131})
        self.assertEqual(len(result["exposure"]["unused_usable_triplets"]), 24)
        self.assertEqual(result["manifest"]["excluded_nba_annotation_rows_used"], 0)
        self.assertTrue(result["manifest"]["nba_mixed_reference_containers_parsed"])
        self.assertFalse(result["manifest"]["holdout_label_bodies_read"])
        for path in reads:
            self.assertNotIn("det_distractor_long_gap", path.as_posix())
            self.assertNotIn("det_drive_rim_overlap", path.as_posix())
        excluded = result["manifest"]["excluded_all_masked_triplets"]
        self.assertEqual([r["frame_indices"][0] for r in excluded], list(range(968, 978)))

    def test_config_approval_recipe_initialization_and_exclusion_changes_fail(self):
        config = adaptation.read_json(CONFIG)
        actual_read = adaptation.read_json
        mutations = [lambda c: c["training"].update(updates=201),
                     lambda c: c["initialization"]["checkpoint"].update(sha256="0" * 64),
                     lambda c: c["excluded_nba_game_ids"].remove("0022500828"),
                     lambda c: c["nba_training_windows"][0].update(game_id="0022500828"),
                     lambda c: c["nba_training_windows"][0].update(source_frame_range_inclusive=[661, 720])]
        for mutate in mutations:
            changed = copy.deepcopy(config)
            mutate(changed)
            def changed_read(path):
                return changed if Path(path).resolve() == CONFIG.resolve() else actual_read(path)
            with self.subTest(mutate=mutate), patch.object(adaptation, "read_json", side_effect=changed_read):
                with self.assertRaises(ValueError):
                    adaptation.load_config(ROOT, CONFIG)


if __name__ == "__main__":
    unittest.main()
