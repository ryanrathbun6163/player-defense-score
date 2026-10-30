"""A failed render must not replay completed synthetic selection or scoring."""
from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

from src.ball_tracking import wasb_development_observation as producer
from src.ball_tracking import wasb_motion_evaluation as evaluation
from src.ball_tracking import wasb_motion_review as review
from src.ball_tracking import wasb_motion_selection as motion


class MotionResumeTests(unittest.TestCase):
    def test_render_failure_reuses_completed_stages_and_preserves_failed_attempt(self):
        source = {"path": "data/clips/synthetic.mp4", "sha256": "a" * 64,
                  "width_px": 1920, "height_px": 1080, "fps": 25.0, "frame_count": 9}
        possession = {"possession_id": "synthetic", "source_video": source,
                      "visible_segments": [[0, 2], [6, 8]], "protected_ranges": [[3, 5]]}
        segments = []
        for start, x in ((0, 30), (6, 430)):
            maps = np.zeros((3, 288, 512), dtype=np.float32)
            maps[:, 40:43, x:x + 3] = .8
            segments.append({"segment": [start, start + 2], "frames": producer.observed_frames(
                maps, [1, 1, 1], start, source, .3)})
        observations = {"schema_version": "unlabeled_ball_development_observations/v0.1",
                        **possession, "reference_labels": None,
                        "threshold_status": "0.3_development_candidate",
                        "model_provenance": {"fixture": "actual_observation_producer"},
                        "frames": producer.make_timeline(possession, segments, [])}
        motion.validate_observations(observations, possession, [])

        with tempfile.TemporaryDirectory(prefix="pds_motion_resume_") as directory:
            root = Path(directory)
            config = {"output_root": "data/outputs/synthetic_motion", "selection": copy.deepcopy(motion.POLICY),
                      "evaluation_radius_px": 10.0}
            config_path = root / "configs/comparison.json"
            motion.write_once(config_path, config)
            input_path = root / "data/outputs/synthetic_observation/observations.json"
            motion.write_once(input_path, observations)
            saved = {"synthetic": {"observations": producer.binding(root, input_path)}}
            obs_config = {"output_root": "data/outputs/synthetic_observation", "possessions": [possession],
                          "split_metadata": {"path": "configs/synthetic_split.json", "sha256": "b" * 64}}
            loaded = (config, obs_config, {"fixture": "no_real_labels"}, {"synthetic": observations}, saved)
            real_binding = producer.binding

            def source_or_fixture_binding(binding_root, path):
                path = Path(path).resolve()
                # Bind the real implementation bytes while fixture outputs stay in TEMP.
                if path.is_relative_to(motion.ROOT / "src"):
                    return real_binding(motion.ROOT, path)
                return real_binding(binding_root, path)

            output = root / config["output_root"]
            with mock.patch.object(motion, "load_inputs", return_value=loaded), \
                    mock.patch.object(motion, "binding", side_effect=source_or_fixture_binding), \
                    mock.patch.object(motion.subprocess, "check_output", return_value="c" * 40 + "\n"), \
                    mock.patch.object(motion, "select_timeline", wraps=motion.select_timeline) as selected, \
                    mock.patch.object(evaluation, "evaluate_comparison", return_value={"windows": []}) as scored, \
                    mock.patch.object(review, "render_comparison", side_effect=RuntimeError("synthetic render failure")):
                with self.assertRaisesRegex(RuntimeError, "synthetic render failure"):
                    motion.execute(root, config_path)
                selected.assert_called_once()
                scored.assert_called_once()

            completed_stages = ("synthetic/selection.json", "selection_completion.json", "comparison.json",
                                "evaluation_identity.json", "evaluation_completion.json")
            preserved = {name: (output / name).read_bytes() for name in completed_stages}
            first_records = {path: path.read_bytes() for path in (output / "invocations").glob("*.json")}
            self.assertEqual(len(first_records), 2)
            failed = [path for path in first_records if not path.name.endswith(".started.json")]
            self.assertEqual(len(failed), 1)
            failure = motion.read_json(failed[0])
            self.assertEqual(failure["status"], "failed")
            self.assertIn("synthetic render failure", failure["error"])
            self.assertFalse(failure["selection_reused"])
            self.assertFalse(failure["evaluation_reused"])
            self.assertFalse((output / "summary.json").exists())

            with mock.patch.object(motion, "load_inputs", return_value=loaded), \
                    mock.patch.object(motion, "binding", side_effect=source_or_fixture_binding), \
                    mock.patch.object(motion.subprocess, "check_output", return_value="c" * 40 + "\n"), \
                    mock.patch.object(motion, "select_timeline", side_effect=AssertionError("Selection replayed")) as selected, \
                    mock.patch.object(evaluation, "evaluate_comparison", side_effect=AssertionError("Scoring replayed")) as scored, \
                    mock.patch.object(review, "render_comparison", return_value={"fixture": "completed_review"}) as rendered:
                summary = motion.execute(root, config_path)
                selected.assert_not_called()
                scored.assert_not_called()
                rendered.assert_called_once()

            self.assertEqual(summary["counts"]["synthetic"], {
                "baseline_observed": 6, "motion_observed": 6, "changed": 0, "withheld": 3})
            for name, raw in preserved.items():
                self.assertEqual((output / name).read_bytes(), raw, name)
            for path, raw in first_records.items():
                self.assertEqual(path.read_bytes(), raw, path.name)
            outcomes = [motion.read_json(path) for path in (output / "invocations").glob("*.json")
                        if not path.name.endswith(".started.json")]
            self.assertCountEqual([item["status"] for item in outcomes], ["failed", "completed"])
            success = next(item for item in outcomes if item["status"] == "completed")
            self.assertTrue(success["selection_reused"])
            self.assertTrue(success["evaluation_reused"])
            self.assertEqual(set(motion.read_json(output / "evaluation_identity.json")["sources"]), {
                "wasb_motion_evaluation.py", "point_evaluation.py", "annotations.py",
                "wasb_adaptation_experiment.py", "wasb_calibration.py"})


if __name__ == "__main__":
    unittest.main()
