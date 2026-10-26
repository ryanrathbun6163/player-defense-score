"""Actual observation producer and native encoded transport for NBA-first review."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from src.ball_tracking import nba_first_review as review
from src.ball_tracking.annotations import FrameAnnotation
from src.ball_tracking.completion_training_runtime import atomic_write_once, binding
from src.ball_tracking.nba_action_observation import select_observation, stream_means


class NbaFirstReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.block = {"block_id": "nba_episode_1", "domain": "nba", "game_id": "nba_game",
            "role": "checkpoint_validation", "time_base": "1/90000", "source_video": {
                "width_px": 64, "height_px": 36, "sha256": hashlib.sha256(b"source metadata").hexdigest()},
            "frames": []}
        bounds = type("Bounds", (), self.block["source_video"])()
        pts = 900000
        for offset, duration in enumerate((1440, 1530, 1530, 1440)):
            index = 100 + offset
            rgb = np.full((36, 64, 3), [20 + 30 * offset, 80, 160], np.uint8)
            image = self.root / f"source_{index}.png"
            Image.fromarray(rgb).save(image)
            label = {"frame_index": index, "annotation_status": "labeled",
                "visibility": "fully_visible" if offset == 0 else "not_visible" if offset == 3 else "indeterminate",
                "absence_reason": "occluded" if offset == 3 else None,
                "game_ball_identity_certainty": "certain" if offset in {0, 3} else "ambiguous",
                "geometry": {"center_xy_px": [20, 12], "source": "observed_complete_ball_center",
                             "uncertainty_radius_px": 2} if offset == 0 else None,
                "localization_eligible": offset == 0, "difficulty_tags": [], "notes": "Synthetic reference"}
            self.block["frames"].append({"source_frame_index": index, "source_pts_ticks": pts,
                "duration_ticks": duration,
                "png": {**binding(self.root, image), "rgb_sha256": hashlib.sha256(rgb.tobytes()).hexdigest()},
                "annotation": None if offset == 2 else FrameAnnotation.from_mapping(label, offset, bounds).to_dict()})
            pts += duration
        self.baseline = self.produce([(20, 12), None, (30, 14), None])
        self.candidate = self.produce([(32, 12), None, (34, 14), None])
        self.entry = {"block": self.block, "baseline_observations": self.baseline,
                      "candidate_observations": self.candidate, "provenance": {"synthetic": True}}
        models = {}
        for name in ("baseline", "candidate"):
            path = self.root / f"{name}.pth"
            path.write_bytes(name.encode())
            models[name] = {"name": name, "checkpoint": binding(self.root, path)}
        self.inputs = {"schema_version": review.SCHEMA, "status": "completed_evaluation",
            "protected_evaluation_authorized": False, "human_visual_acceptance": None,
            **models, "blocks": [self.entry]}
        self.input_path = self.root / "inputs.json"
        atomic_write_once(self.input_path, self.inputs)
        # render_review binds implementation files but does not execute these
        # fixtures; all renderer/scorer functions above are the real producers.
        code = self.root / "src/ball_tracking"
        code.mkdir(parents=True)
        for name in ("nba_first_review", "completion_nba_comparison_render", "completion_evaluation",
                     "completion_evaluation_package", "completion_sac_references"):
            (code / f"{name}.py").write_text("synthetic local implementation binding\n")

    def produce(self, points):
        def provider(frames):
            values = []
            for frame in frames:
                mean = np.zeros((288, 512), np.float32)
                point = points[frame["source_frame_index"] - 100]
                if point is not None:
                    mean[point[1] * 8, point[0] * 8] = .75
                values.append(mean)
            return np.stack(values)
        return [select_observation(frame, mean, count, self.block, {"kind": "synthetic"})
                for frame, mean, count in stream_means(self.block["frames"], provider)]

    def test_native_conversion_preserves_roles_originals_and_missingness(self):
        original = copy.deepcopy(self.entry)
        block, new = review.prepared_block(self.entry)
        self.assertEqual(self.entry, original)
        self.assertEqual(block["original_role"], "checkpoint_validation")
        self.assertEqual(block["role"], "post_selection_evaluation_only")
        self.assertEqual([f["reference_role"] for f in block["frames"]], ["checkpoint_validation"] * 4)
        self.assertEqual([f["baseline_observation"]["original_record"] for f in block["frames"]], self.baseline)
        self.assertEqual(new, self.candidate)
        self.assertIsNone(new[1]["center_xy_px"])
        self.assertIsNone(block["frames"][3]["annotation"]["geometry"])

    def test_protected_and_failed_records_rejected_before_pixels(self):
        for kind in ("protected_state", "protected_index", "failed", "wrong_pts", "wrong_point"):
            changed = copy.deepcopy(self.entry)
            if kind == "protected_state":
                changed["block"]["frames"][0]["state"] = "withheld"
            elif kind == "protected_index":
                changed["block"]["protected_ranges"] = [[100, 100]]
            elif kind == "failed":
                changed["candidate_observations"][0]["inference_status"] = "failed"
            elif kind == "wrong_pts":
                changed["candidate_observations"][0]["source_pts_ticks"] += 1
            else:
                changed["candidate_observations"][0]["center_xy_px"] = [20, 12]
            with self.subTest(kind=kind), patch.object(review.renderer, "source_rgb", side_effect=AssertionError("No pixels")):
                with self.assertRaises(ValueError):
                    review.prepared_block(changed)

    def test_input_binding_checks_checkpoint_and_duplicate_context(self):
        inputs, prepared = review.load_inputs(self.root, binding(self.root, self.input_path))
        self.assertEqual(inputs, self.inputs)
        self.assertEqual(len(prepared), 1)
        self.input_path.write_text(json.dumps({**self.inputs, "blocks": [self.entry, self.entry]}))
        with self.assertRaisesRegex(ValueError, "Duplicate review block"):
            review.load_inputs(self.root, binding(self.root, self.input_path))
        self.input_path.write_text(json.dumps(self.inputs))
        (self.root / "candidate.pth").write_bytes(b"different weights")
        with self.assertRaises(ValueError):
            review.load_inputs(self.root, binding(self.root, self.input_path))

    @unittest.skipUnless(shutil.which("ffprobe"), "ffprobe required for actual encoded native transport")
    def test_actual_review_vfr_final_frame_and_resume_integrity(self):
        result = review.render_review(self.root, binding(self.root, self.input_path), "data/outputs/review")
        summary = json.loads((self.root / result["summary"]["path"]).read_text())
        block = summary["blocks"][0]
        self.assertEqual(summary["native_frames"], 4)
        self.assertEqual(block["actual_final_native_frame"], 103)
        self.assertEqual(block["actual_final_source_pts_ticks"], 904500)
        self.assertEqual(block["actual_final_duration_ticks"], 1440)
        self.assertEqual(block["total_duration_ticks"], 5940)
        self.assertEqual(block["added_final_hold_ticks"], 0)
        self.assertTrue(block["all_decoded_native_keys_verified"])
        records = json.loads((self.root / block["frame_records"]["path"]).read_text())["frames"]
        self.assertEqual([f["encoded_pts_ticks"] for f in records], [0, 1440, 2970, 4500])
        self.assertEqual([f["selected_observation"] for f in records], self.candidate)
        self.assertEqual([f["baseline_observation"]["original_baseline_record"] for f in records], self.baseline)
        self.assertEqual(review.render_review(self.root, binding(self.root, self.input_path),
                                             "data/outputs/review", resume=True), result)
        (self.root / block["video"]["path"]).write_bytes(b"damaged video")
        with self.assertRaises(ValueError):
            review.render_review(self.root, binding(self.root, self.input_path), "data/outputs/review", resume=True)


if __name__ == "__main__":
    unittest.main()
