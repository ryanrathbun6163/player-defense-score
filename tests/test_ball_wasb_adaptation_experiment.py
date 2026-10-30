"""Derived checkpoint and genuine cached-output boundaries for adaptation scoring."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch

from src.ball_tracking import wasb_adaptation_experiment as experiment
from src.ball_tracking import wasb_calibration as calibration
from src.ball_tracking.wasb_experiment import read_json, write_once
from test_ball_wasb_calibration import fixture


class AdaptationExperimentTests(unittest.TestCase):
    def test_only_bound_completed_final_training_checkpoint_can_be_evaluated(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            trial = root / "data/outputs/adaptation"
            training = trial / "training"
            training.mkdir(parents=True)
            config_path = root / "config.json"
            write_once(config_path, {"output_root": "data/outputs/adaptation"})
            checkpoint = training / "checkpoint.pth"
            torch.save({"model_state_dict": {"weight": torch.ones(1)}}, checkpoint)
            completion = {"schema_version": "wasb_adaptation_training_completion/v0.1",
                "status": "completed", "completed_updates": 200,
                "config": calibration.file_binding(root, config_path),
                "checkpoint": calibration.file_binding(root, checkpoint),
                "training_provenance": {"pilot_frames": 75}}
            completion_path = training / "completion.json"
            write_once(completion_path, completion)
            self.assertEqual(experiment.load_completed_training(root, config_path)[2], completion)
            for key, value in (("completed_updates", 199), ("status", "failed"),
                               ("config", {"path": "config.json", "sha256": "0" * 64})):
                changed = {**completion, key: value}
                completion_path.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaises(ValueError):
                    experiment.load_completed_training(root, config_path)
            completion_path.write_text(json.dumps(completion), encoding="utf-8")
            checkpoint.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                experiment.load_completed_training(root, config_path)

    def test_derived_config_keeps_original_controls_and_does_not_mutate_them(self):
        original = {"checkpoint": {"path": "original.pth", "sha256": "a" * 64},
                    "windows": [{"window_id": "declared"}], "inference": {"heatmap_threshold": .5}}
        before = copy.deepcopy(original)
        completion = {"checkpoint": {"path": "adapted.pth", "sha256": "b" * 64},
                      "training_provenance": {"updates": 200}}
        result = experiment.evaluation_config(original, "data/outputs/trial", completion, {"sha256": "c" * 64})
        self.assertEqual(original, before)
        self.assertEqual(result["windows"], original["windows"])
        self.assertEqual(result["checkpoint"], completion["checkpoint"])
        self.assertEqual(result["pretrained_checkpoint"], original["checkpoint"])
        self.assertEqual(result["output_root"], "data/outputs/trial/evaluation")
        self.assertEqual(result["experiment_id"], "wasb_basketball_adaptation_v0_1_evaluation")
        self.assertNotIn("training_scope", result)
        expanded = experiment.evaluation_config(
            original, "data/outputs/expanded", completion, {"sha256": "c" * 64},
            "wasb_basketball_expanded_adaptation_v0_1", "5 training blocks / 150 reviewed frames")
        self.assertEqual(expanded["experiment_id"], "wasb_basketball_expanded_adaptation_v0_1_evaluation")
        self.assertEqual(expanded["training_scope"], "5 training blocks / 150 reviewed frames")
        self.assertEqual(expanded["windows"], original["windows"])
        self.assertEqual(original, before)

    def test_generated_calibration_uses_genuine_source_cache_and_compares_same_frames(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path, source_config = fixture(root)
            inference = read_json(root / "original_experiment.json")
            inference["experiment_id"] = "wasb_basketball_expanded_adaptation_v0_1_evaluation"
            inference["training_scope"] = "5 training blocks / 150 reviewed frames"
            source_folder = root / inference["output_root"]
            write_once(source_folder / "experiment.json", inference)
            derived_folder = root / "data/outputs/derived_calibration"
            derived = experiment.calibration_config(root, inference, source_folder, derived_folder)
            derived_path = root / "derived.json"
            write_once(derived_path, derived)
            self.assertEqual(calibration.load_config(root, derived_path), derived)
            self.assertEqual(derived["experiment_id"], "wasb_basketball_expanded_adaptation_v0_1_calibration")
            # Both score the real fixture component->point->evaluator records;
            # one uses the original config and one the generated adapted config.
            old_summary = calibration.execute(root, source_path)
            new_summary = calibration.execute(root, derived_path)
            trial = root / "data/outputs/trial"
            compared = experiment.compare_calibrations(root, source_config, derived, trial, {"sha256": "d" * 64})
            self.assertEqual(old_summary["component_thresholds"], new_summary["component_thresholds"])
            for row in compared["threshold_results"]:
                for pool in row["pools"].values():
                    self.assertEqual(pool["adapted_vs_pretrained"]["recovered"], 0)
                    self.assertEqual(pool["adapted_vs_pretrained"]["lost"], 0)
                    self.assertEqual(pool["adapted"], pool["pretrained"])
            self.assertEqual(derived["source_experiment"]["path"], "data/outputs/original/experiment.json")
            # The same completed producer evidence can be compared as a historical
            # adapted baseline, without rerunning its screen or changing its bytes.
            preserved = {path: path.read_bytes() for path in (root / source_config["output_root"]).rglob("*")
                         if path.is_file()}
            with patch.object(calibration, "execute", side_effect=AssertionError("cached baseline rerun")), \
                    patch("cv2.VideoCapture", side_effect=AssertionError("media forbidden")), \
                    patch("src.ball_tracking.wasb_adapted_adapter.AdaptedWasbAdapter",
                          side_effect=AssertionError("model forbidden")):
                prior = experiment.compare_calibrations(
                    root, source_config, derived, trial, {"sha256": "d" * 64},
                    baseline_role="prior_adapted", training_scope=inference["training_scope"])
            self.assertEqual(prior["baseline_role"], "prior_adapted")
            self.assertNotIn("pretrained_summary", prior)
            self.assertEqual(prior["prior_adapted_summary"], compared["pretrained_summary"])
            self.assertEqual(read_json(trial / "comparison.json"), compared)
            self.assertEqual(read_json(trial / "prior_adapted_comparison.json"), prior)
            self.assertTrue(all(path.read_bytes() == payload for path, payload in preserved.items()))
            for row in prior["threshold_results"]:
                for pool in row["pools"].values():
                    self.assertEqual(pool["adapted_vs_prior_adapted"], {"recovered": 0, "lost": 0, "shared":
                        pool["adapted"]["raw_available_or_matched"]})
                    self.assertEqual(pool["prior_adapted"], pool["adapted"])
                    self.assertNotIn("pretrained", pool)
            self.assertIn("150 reviewed frames", prior["limitations"][1])
            changed_scope = copy.deepcopy(derived)
            changed_scope["windows"][0]["annotation"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "annotations, source frames or RF controls differ"):
                experiment.compare_calibrations(root, source_config, changed_scope, trial, {"sha256": "d" * 64})
            # A leftover or modified summary cannot masquerade as completed.
            summary_path = derived_folder / "summary.json"
            summary_path.write_text(json.dumps({**new_summary, "experiment_id": "modified"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "successful receipt"):
                experiment.completed_calibration(root, derived)

    def test_paired_changes_have_correct_direction_and_reject_frame_mismatch(self):
        def report(matched):
            return {"frame_results": [{"frame_index": i, "scoring_status": "localization_eligible",
                "matched_candidate_index": 0 if i in matched else None} for i in range(3)]}
        self.assertEqual(experiment.paired_frame_changes(report({1, 2}), report({0, 1})),
                         {"recovered_frame_indices": [2], "lost_frame_indices": [0], "shared_frame_indices": [1]})
        changed = report({1})
        changed["frame_results"][2]["frame_index"] = 4
        with self.assertRaises(ValueError):
            experiment.paired_frame_changes(changed, report({1}))


if __name__ == "__main__":
    unittest.main()
