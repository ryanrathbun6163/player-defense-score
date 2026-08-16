import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.pipeline.planner import STAGE_SPECS, build_plan
from src.pipeline.possession import (
    ConfigurationError,
    PipelineManifest,
    PipelinePaths,
    load_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "configs" / "possession_001_pipeline.json"


def baseline_payload():
    with CONFIG_PATH.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


class PipelineManifestTests(unittest.TestCase):
    def test_possession_001_manifest_round_trips(self):
        manifest = load_manifest(CONFIG_PATH)

        self.assertEqual(manifest.schema_version, 1)
        self.assertEqual(manifest.possession_id, "possession_001")
        self.assertEqual(manifest.reference_frame_index, 249)
        self.assertEqual(manifest.expected_player_count, 10)
        self.assertEqual(
            dict(manifest.expected_team_counts),
            {"white": 5, "dark": 5},
        )
        self.assertEqual(manifest.to_dict(), baseline_payload())

    def test_rejects_unsafe_possession_id(self):
        payload = baseline_payload()
        payload["possession_id"] = "../possession_002"

        with self.assertRaisesRegex(ConfigurationError, "possession_id"):
            PipelineManifest.from_mapping(payload)

    def test_rejects_video_path_outside_repository(self):
        payload = baseline_payload()
        payload["video_path"] = "../possession_002.mp4"

        with self.assertRaisesRegex(ConfigurationError, "within the repository"):
            PipelineManifest.from_mapping(payload)

    def test_rejects_inconsistent_team_counts(self):
        payload = baseline_payload()
        payload["expected_team_counts"]["dark"] = 4

        with self.assertRaisesRegex(ConfigurationError, "must sum"):
            PipelineManifest.from_mapping(payload)

    def test_rejects_unsorted_or_duplicate_checkpoints(self):
        payload = baseline_payload()
        payload["overrides"]["camera_motion"][
            "extra_checkpoint_frames"
        ] = [10, 3, 10]

        with self.assertRaisesRegex(ConfigurationError, "sorted and unique"):
            PipelineManifest.from_mapping(payload)

    def test_middle_reference_frame_is_supported(self):
        payload = baseline_payload()
        payload["possession_id"] = "possession_002"
        payload["video_path"] = "data/clips/possession_002.mp4"
        payload["reference_frame_index"] = "middle"
        payload["overrides"] = {}
        manifest = PipelineManifest.from_mapping(payload)

        self.assertIsNone(manifest.reference_frame_index)
        self.assertEqual(manifest.reference_frame_value, "middle")


class PipelinePathTests(unittest.TestCase):
    def setUp(self):
        self.manifest = load_manifest(CONFIG_PATH)
        self.paths = PipelinePaths.build(
            REPO_ROOT,
            self.manifest,
            config_path=CONFIG_PATH,
        )

    def test_existing_possession_001_path_contract_is_preserved(self):
        expected = {
            "tracking_tracks": (
                "data/outputs/tracking/"
                "possession_001_court_filtered_tracks.csv"
            ),
            "classified_tracks": (
                "data/outputs/classification/"
                "possession_001_team_classified_tracks.csv"
            ),
            "reconciled_tracks": (
                "data/outputs/identity/"
                "possession_001_reconciled_tracks.csv"
            ),
            "camera_homographies": (
                "data/outputs/court/possession_001_motion_review/"
                "possession_001_camera_homographies.npz"
            ),
            "player_coordinates": (
                "data/outputs/court/"
                "possession_001_player_court_coordinates.csv"
            ),
            "refined_coordinates": (
                "data/outputs/court/"
                "possession_001_player_court_coordinates_refined.csv"
            ),
            "gap_filled_coordinates": (
                "data/outputs/court/"
                "possession_001_player_court_coordinates_gap_filled.csv"
            ),
        }

        for key, relative_path in expected.items():
            with self.subTest(key=key):
                self.assertEqual(self.paths.relative(key), relative_path)

    def test_possession_002_paths_are_isolated_without_source_edits(self):
        payload = copy.deepcopy(baseline_payload())
        payload["possession_id"] = "possession_002"
        payload["video_path"] = "data/clips/possession_002.mp4"
        payload["reference_frame_index"] = "middle"
        payload["overrides"] = {}
        manifest = PipelineManifest.from_mapping(payload)
        paths = PipelinePaths.build(REPO_ROOT, manifest)

        self.assertEqual(
            paths.relative("tracking_tracks"),
            "data/outputs/tracking/possession_002_court_filtered_tracks.csv",
        )
        self.assertEqual(
            paths.relative("gap_filled_coordinates"),
            (
                "data/outputs/court/"
                "possession_002_player_court_coordinates_gap_filled.csv"
            ),
        )
        self.assertNotIn(
            "possession_001",
            paths.relative("gap_filled_coordinates"),
        )
        self.assertEqual(
            paths.relative("pipeline_state"),
            (
                "data/outputs/pipeline/"
                "possession_002_player_coordinate_pipeline_state.json"
            ),
        )

    def test_stage_plan_has_unique_names_and_known_paths(self):
        plan = build_plan(self.manifest, self.paths)
        names = [stage["name"] for stage in plan["stages"]]

        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(names), len(STAGE_SPECS))
        self.assertTrue(plan["execution_enabled"])
        self.assertTrue(
            plan["execution_guardrails"]["reviewed_baseline_protected"]
        )
        self.assertNotIn(
            "needs_cli_refactor",
            plan["summary"]["generalization_status_counts"],
        )
        self.assertTrue(plan["generalization_gate"]["structural"]["passed"])
        self.assertFalse(
            plan["generalization_gate"]["ball_tracking_unlocked"]
        )


class RunnerTests(unittest.TestCase):
    def test_json_dry_run_is_non_executing(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.pipeline.run_player_coordinates",
                "--config",
                str(CONFIG_PATH),
                "--dry-run",
                "--json",
            ],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        plan = json.loads(result.stdout)

        self.assertEqual(
            plan["status"],
            "pipeline_generalization_ready",
        )
        self.assertTrue(plan["execution_enabled"])
        self.assertEqual(
            plan["manifest"]["possession_id"],
            "possession_001",
        )

    def test_reviewed_second_possession_evidence_unlocks_gate_only(self):
        evidence = {
            "possession_id": "possession_002",
            "source_edits_required": False,
            "all_stages_completed": True,
            "review_gates_completed": True,
            "homography_coverage_ratio": 1.0,
            "coordinate_coverage_ratio": 0.97,
            "complete_player_frame_ratio": 0.90,
            "unresolved_review_count": 0,
            "coordinate_key_violation_count": 0,
            "outside_court_positions_audited": True,
            "visual_review_through_final_frame": True,
            "generated_outputs_uncommitted": True,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            evidence_path = Path(temp_dir) / "evidence.json"
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "src.pipeline.run_player_coordinates",
                    "--config",
                    str(CONFIG_PATH),
                    "--dry-run",
                    "--gate-evidence",
                    str(evidence_path),
                    "--json",
                ],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

        plan = json.loads(result.stdout)
        gate = plan["generalization_gate"]
        self.assertTrue(gate["empirical"]["passed"])
        self.assertTrue(gate["ball_tracking_unlocked"])
        self.assertTrue(plan["execution_enabled"])


if __name__ == "__main__":
    unittest.main()
