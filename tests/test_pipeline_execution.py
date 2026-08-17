import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.pipeline.execution import ensure_review_templates, execute_plan
from src.pipeline.possession import PipelineManifest, PipelinePaths


REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_CONFIG = REPO_ROOT / "configs" / "possession_001_pipeline.json"


def candidate_manifest():
    payload = json.loads(BASELINE_CONFIG.read_text(encoding="utf-8"))
    payload = copy.deepcopy(payload)
    payload["possession_id"] = "possession_002"
    payload["video_path"] = "data/clips/possession_002.mp4"
    payload["reference_frame_index"] = "middle"
    payload["overrides"]["identity"]["review_boundaries"] = []
    payload["overrides"]["camera_motion"][
        "extra_checkpoint_frames"
    ] = []
    return PipelineManifest.from_mapping(payload)


def synthetic_plan(stages):
    return {
        "generalization_gate": {"structural": {"passed": True}},
        "stages": stages,
    }


class PipelineExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temporary.name)
        (self.repo_root / "src").mkdir()
        (self.repo_root / "configs").mkdir()
        self.manifest = candidate_manifest()
        self.config_path = (
            self.repo_root / "configs" / "possession_002_pipeline.json"
        )
        self.config_path.write_text(
            json.dumps(self.manifest.to_dict()),
            encoding="utf-8",
        )
        self.paths = PipelinePaths.build(
            self.repo_root,
            self.manifest,
            config_path=self.config_path,
        )
        self.paths["video"].parent.mkdir(parents=True)
        self.paths["video"].write_bytes(b"video")

    def tearDown(self):
        self.temporary.cleanup()

    def automatic_stage(self):
        return {
            "index": 1,
            "name": "tracking",
            "command": ["python", "-m", "fake.tracking"],
            "review_commands": [],
            "inputs": [{"key": "video"}],
            "outputs": [{"key": "tracking_tracks"}],
        }

    def test_completed_stage_is_skipped_on_resume(self):
        calls = []

        def runner(command, repo_root):
            calls.append((command, repo_root))
            self.paths["tracking_tracks"].parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            self.paths["tracking_tracks"].write_text(
                "frame_index,track_id\n",
                encoding="utf-8",
            )
            return 0

        plan = synthetic_plan([self.automatic_stage()])
        first = execute_plan(
            plan,
            self.manifest,
            self.paths,
            command_runner=runner,
        )
        second = execute_plan(
            plan,
            self.manifest,
            self.paths,
            command_runner=runner,
        )

        self.assertEqual(first.status, "completed")
        self.assertEqual(second.skipped_stages, ["tracking"])
        self.assertEqual(len(calls), 1)

    def test_failed_stage_can_resume(self):
        attempts = 0

        def runner(command, repo_root):
            nonlocal attempts
            attempts += 1

            if attempts == 1:
                return 7

            self.paths["tracking_tracks"].parent.mkdir(parents=True)
            self.paths["tracking_tracks"].write_text(
                "frame_index,track_id\n",
                encoding="utf-8",
            )
            return 0

        plan = synthetic_plan([self.automatic_stage()])
        failed = execute_plan(
            plan,
            self.manifest,
            self.paths,
            command_runner=runner,
        )
        resumed = execute_plan(
            plan,
            self.manifest,
            self.paths,
            command_runner=runner,
        )

        self.assertEqual(failed.status, "failed")
        self.assertEqual(failed.stage_name, "tracking")
        self.assertEqual(resumed.status, "completed")
        self.assertEqual(attempts, 2)

    def test_rerun_from_invalidates_completed_stage(self):
        calls = 0

        def runner(command, repo_root):
            nonlocal calls
            calls += 1
            self.paths["tracking_tracks"].parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            self.paths["tracking_tracks"].write_text(
                str(calls),
                encoding="utf-8",
            )
            return 0

        plan = synthetic_plan([self.automatic_stage()])
        execute_plan(
            plan,
            self.manifest,
            self.paths,
            command_runner=runner,
        )
        execute_plan(
            plan,
            self.manifest,
            self.paths,
            rerun_from="tracking",
            command_runner=runner,
        )

        self.assertEqual(calls, 2)

    def test_calibration_gate_pauses_then_resumes(self):
        self.paths["court_calibration_pending"].write_text(
            "{}",
            encoding="utf-8",
        )
        self.paths["landmark_review_dir"].mkdir(parents=True)
        stage = {
            "index": 1,
            "name": "calibration_review_gate",
            "command": None,
            "review_commands": [],
            "inputs": [
                {"key": "court_calibration_pending"},
                {"key": "landmark_review_dir"},
            ],
            "outputs": [{"key": "court_calibration_review"}],
        }
        plan = synthetic_plan([stage])
        paused = execute_plan(plan, self.manifest, self.paths)
        self.assertEqual(paused.status, "paused_for_review")

        self.paths["court_calibration_review"].write_text(
            json.dumps({"review_status": "approved"}),
            encoding="utf-8",
        )
        resumed = execute_plan(plan, self.manifest, self.paths)
        self.assertEqual(resumed.status, "completed")

    def test_identity_gate_pauses_for_unresolved_reid_decisions(self):
        self.paths["reid_segments"].parent.mkdir(parents=True)
        self.paths["reid_segments"].write_text(
            json.dumps({"unresolved_appearance_candidate_count": 2}),
            encoding="utf-8",
        )
        self.paths["segment_match_candidates"].write_text(
            json.dumps({"unresolved_review_candidate_count": 0}),
            encoding="utf-8",
        )
        ensure_review_templates(self.manifest, self.paths)
        stage = {
            "index": 1,
            "name": "identity_review_cycle",
            "command": ["python", "-m", "fake.identity"],
            "review_commands": [["python", "-m", "fake.review"]],
            "inputs": [],
            "outputs": [
                {"key": "segment_player_mapping"},
                {"key": "identity_annotated_tracks"},
                {"key": "reconciled_tracks"},
            ],
        }
        result = execute_plan(
            synthetic_plan([stage]),
            self.manifest,
            self.paths,
        )

        self.assertEqual(result.status, "paused_for_review")
        self.assertIn("appearance boundary", " ".join(result.reasons))
        self.assertEqual(len(result.review_commands), 1)

    def test_missing_review_templates_are_created_once(self):
        created = ensure_review_templates(self.manifest, self.paths)
        created_again = ensure_review_templates(self.manifest, self.paths)

        self.assertEqual(len(created), 3)
        self.assertEqual(created_again, [])
        identity = json.loads(
            self.paths["identity_review_config"].read_text(encoding="utf-8")
        )
        self.assertEqual(identity["expected_active_player_count"], 10)


class RunnerExecutionProtectionTests(unittest.TestCase):
    def test_reviewed_baseline_cannot_run_without_explicit_override(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.pipeline.run_player_coordinates",
                "--config",
                str(BASELINE_CONFIG),
                "--run",
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reviewed baseline", result.stderr)


if __name__ == "__main__":
    unittest.main()
