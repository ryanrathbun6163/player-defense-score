import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.court.prepare_calibration_review import (
    parse_args as parse_calibration_preparation_args,
)
from src.court.propagate_court_calibration import (
    parse_args as parse_camera_motion_args,
)
from src.identity.build_player_identities import (
    parse_args as parse_identity_build_args,
)
from src.identity.review_cross_track_switches import (
    parse_args as parse_cross_track_review_args,
)
from src.identity.review_residual_identities import (
    parse_args as parse_residual_review_args,
)
from src.identity.review_sequential_identities import (
    parse_args as parse_sequential_review_args,
)
from src.identity.review_team_balance import (
    parse_args as parse_team_balance_review_args,
)
from src.pipeline.generalization_gate import evaluate_empirical_gate
from src.pipeline.verify_existing_player_identity import (
    IDENTITY_PROVENANCE_FIELDS,
    MATCH_PROVENANCE_FIELDS,
    normalized_report,
    replace_option,
)
from src.pipeline.planner import build_plan
from src.pipeline.possession import (
    ConfigurationError,
    PipelineManifest,
    PipelinePaths,
    load_manifest,
)
from src.reid.extract_track_embeddings import (
    parse_args as parse_embedding_args,
)
from src.reid.review_identity_boundaries import (
    parse_args as parse_boundary_review_args,
)
from src.reid.segment_track_embeddings import (
    parse_args as parse_segmentation_args,
)
from src.tracking.reconcile_track_ids import (
    parse_args as parse_matching_args,
)
from src.visualization.render_identity_tracks import (
    parse_args as parse_identity_visualization_args,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "configs" / "possession_001_pipeline.json"

GENERALIZED_MODULES = (
    "src.reid.extract_track_embeddings",
    "src.reid.segment_track_embeddings",
    "src.tracking.reconcile_track_ids",
    "src.identity.build_player_identities",
    "src.visualization.render_identity_tracks",
    "src.court.prepare_calibration_review",
    "src.court.propagate_court_calibration",
    "src.reid.review_identity_boundaries",
    "src.identity.review_residual_identities",
    "src.identity.review_sequential_identities",
    "src.identity.review_cross_track_switches",
    "src.identity.review_team_balance",
)

GENERALIZED_FILES = (
    REPO_ROOT / "src" / "reid" / "extract_track_embeddings.py",
    REPO_ROOT / "src" / "reid" / "segment_track_embeddings.py",
    REPO_ROOT / "src" / "tracking" / "reconcile_track_ids.py",
    REPO_ROOT / "src" / "identity" / "build_player_identities.py",
    REPO_ROOT / "src" / "reid" / "review_identity_boundaries.py",
    REPO_ROOT / "src" / "identity" / "review_residual_identities.py",
    REPO_ROOT / "src" / "identity" / "review_sequential_identities.py",
    REPO_ROOT / "src" / "identity" / "review_cross_track_switches.py",
    REPO_ROOT / "src" / "identity" / "review_team_balance.py",
)

STAGE_PARSERS = {
    "reid_embeddings": parse_embedding_args,
    "reid_segmentation": parse_segmentation_args,
    "segment_matching": parse_matching_args,
    "identity_review_cycle": parse_identity_build_args,
    "identity_visualization": parse_identity_visualization_args,
    "calibration_preparation": parse_calibration_preparation_args,
    "camera_motion": parse_camera_motion_args,
}

REVIEW_PARSERS = {
    "src.reid.review_identity_boundaries": parse_boundary_review_args,
    "src.identity.review_residual_identities": parse_residual_review_args,
    "src.identity.review_sequential_identities": (
        parse_sequential_review_args
    ),
    "src.identity.review_cross_track_switches": (
        parse_cross_track_review_args
    ),
    "src.identity.review_team_balance": parse_team_balance_review_args,
}


def baseline_payload():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


class ReIDInterfaceTests(unittest.TestCase):
    def test_generalized_modules_have_lightweight_help(self):
        for module in GENERALIZED_MODULES:
            with self.subTest(module=module):
                result = subprocess.run(
                    [sys.executable, "-m", module, "--help"],
                    cwd=REPO_ROOT,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout.lower())

    def test_automatic_reid_source_has_no_possession_literal(self):
        for path in GENERALIZED_FILES:
            with self.subTest(path=path):
                self.assertNotIn(
                    "possession_001",
                    path.read_text(encoding="utf-8"),
                )

    def test_manifest_commands_are_accepted_by_refactored_parsers(self):
        manifest = load_manifest(CONFIG_PATH)
        paths = PipelinePaths.build(
            REPO_ROOT,
            manifest,
            config_path=CONFIG_PATH,
        )
        stages = {
            stage["name"]: stage
            for stage in build_plan(manifest, paths)["stages"]
        }

        for stage_name, parser in STAGE_PARSERS.items():
            with self.subTest(stage_name=stage_name):
                command = stages[stage_name]["command"]
                self.assertIsNotNone(command)
                self.assertIsNotNone(parser(command[3:]))

    def test_every_cli_ready_stage_has_a_manifest_command(self):
        manifest = load_manifest(CONFIG_PATH)
        paths = PipelinePaths.build(REPO_ROOT, manifest)
        plan = build_plan(manifest, paths)
        missing = [
            stage["name"]
            for stage in plan["stages"]
            if (
                stage["generalization_status"] == "cli_ready"
                and stage["command"] is None
            )
        ]
        self.assertEqual(missing, [])
        self.assertTrue(plan["generalization_gate"]["structural"]["passed"])

    def test_identity_review_commands_are_accepted_by_their_parsers(self):
        manifest = load_manifest(CONFIG_PATH)
        paths = PipelinePaths.build(REPO_ROOT, manifest)
        plan = build_plan(manifest, paths)
        stage = next(
            stage
            for stage in plan["stages"]
            if stage["name"] == "identity_review_cycle"
        )
        self.assertEqual(len(stage["review_commands"]), 5)

        for command in stage["review_commands"]:
            module = command[2]

            with self.subTest(module=module):
                self.assertIsNotNone(REVIEW_PARSERS[module](command[3:]))

    def test_second_possession_commands_are_fully_isolated(self):
        payload = copy.deepcopy(baseline_payload())
        payload["possession_id"] = "possession_002"
        payload["video_path"] = "data/clips/possession_002.mp4"
        payload["reference_frame_index"] = "middle"
        payload["overrides"]["identity"]["review_boundaries"] = []
        payload["overrides"]["camera_motion"][
            "extra_checkpoint_frames"
        ] = []
        manifest = PipelineManifest.from_mapping(payload)
        paths = PipelinePaths.build(REPO_ROOT, manifest)
        plan = build_plan(manifest, paths)

        for stage in plan["stages"]:
            commands = [
                command
                for command in (
                    stage["command"],
                    *stage.get("review_commands", []),
                )
                if command is not None
            ]

            for command in commands:
                with self.subTest(stage=stage["name"], module=command[2]):
                    self.assertNotIn("possession_001", " ".join(command))


class ReIDBehaviorTests(unittest.TestCase):
    def test_reviewed_manual_boundary_splits_synthetic_embeddings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            embeddings_path = root / "embeddings.npz"
            review_path = root / "review.json"
            segments_path = root / "segments.json"
            prototypes_path = root / "prototypes.npz"

            np.savez_compressed(
                embeddings_path,
                embeddings=np.asarray(
                    [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, 1.0]],
                    dtype=np.float32,
                ),
                frame_indices=np.asarray([0, 5, 10, 15], dtype=np.int32),
                track_ids=np.asarray([1, 1, 1, 1], dtype=np.int32),
                confidences=np.asarray([0.9] * 4, dtype=np.float32),
                team_labels=np.asarray(["white"] * 4, dtype=np.str_),
                bounding_boxes=np.asarray(
                    [[0, 0, 20, 60]] * 4,
                    dtype=np.int32,
                ),
            )
            review_path.write_text(
                json.dumps(
                    {
                        "manual_split_after_frames": {"1": [7]},
                        "manual_segment_team_overrides": {},
                    }
                ),
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "src.reid.segment_track_embeddings",
                    "--embeddings",
                    str(embeddings_path),
                    "--review-config",
                    str(review_path),
                    "--output-segments",
                    str(segments_path),
                    "--output-prototypes",
                    str(prototypes_path),
                ],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            report = json.loads(segments_path.read_text(encoding="utf-8"))
            self.assertEqual(report["temporal_segment_count"], 2)
            self.assertEqual(report["manual_break_count"], 1)
            self.assertEqual(
                report["unresolved_appearance_candidate_count"],
                0,
            )
            self.assertTrue(prototypes_path.is_file())


class GeneralizationGateTests(unittest.TestCase):
    def test_empirical_gate_passes_complete_second_possession_evidence(self):
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
        gate = evaluate_empirical_gate("possession_001", evidence)
        self.assertTrue(gate["passed"])

    def test_empirical_gate_rejects_insufficient_coordinate_coverage(self):
        evidence = {
            "possession_id": "possession_002",
            "source_edits_required": False,
            "all_stages_completed": True,
            "review_gates_completed": True,
            "homography_coverage_ratio": 1.0,
            "coordinate_coverage_ratio": 0.94,
            "complete_player_frame_ratio": 0.90,
            "unresolved_review_count": 0,
            "coordinate_key_violation_count": 0,
            "outside_court_positions_audited": True,
            "visual_review_through_final_frame": True,
            "generated_outputs_uncommitted": True,
        }
        gate = evaluate_empirical_gate("possession_001", evidence)
        self.assertFalse(gate["passed"])
        failed = {
            check["name"]
            for check in gate["checks"]
            if not check["passed"]
        }
        self.assertEqual(failed, {"coordinate_coverage"})

    def test_empirical_gate_rejects_malformed_ratio_without_crashing(self):
        evidence = {
            "possession_id": "possession_002",
            "source_edits_required": False,
            "all_stages_completed": True,
            "review_gates_completed": True,
            "homography_coverage_ratio": 1.0,
            "coordinate_coverage_ratio": "high",
            "complete_player_frame_ratio": 0.90,
            "unresolved_review_count": 0,
            "coordinate_key_violation_count": 0,
            "outside_court_positions_audited": True,
            "visual_review_through_final_frame": True,
            "generated_outputs_uncommitted": True,
        }
        gate = evaluate_empirical_gate("possession_001", evidence)
        self.assertFalse(gate["passed"])
        self.assertIn(
            "coordinate_coverage",
            {
                check["name"]
                for check in gate["checks"]
                if not check["passed"]
            },
        )

    def test_manifest_rejects_inverted_strict_reid_threshold(self):
        payload = baseline_payload()
        payload["overrides"]["reid"][
            "strict_max_appearance_distance"
        ] = 0.5

        with self.assertRaisesRegex(
            ConfigurationError,
            "strict_max_appearance_distance",
        ):
            PipelineManifest.from_mapping(payload)


class IdentityRegressionHelperTests(unittest.TestCase):
    def test_command_option_replacement_is_explicit(self):
        command = ["python", "-m", "example", "--output", "old.json"]
        replace_option(command, "--output", Path("new.json"))
        self.assertEqual(command[-1], "new.json")

    def test_report_normalization_removes_only_provenance(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "report.json"
            payload = {
                "classified_tracks": "one.csv",
                "segments_report": "two.json",
                "segment_prototypes": "three.npz",
                "review_config": "four.json",
                "strict_candidate_count": 12,
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            normalized = normalized_report(path, MATCH_PROVENANCE_FIELDS)

        self.assertEqual(normalized, {"strict_candidate_count": 12})
        self.assertIn("match_report", IDENTITY_PROVENANCE_FIELDS)


if __name__ == "__main__":
    unittest.main()
