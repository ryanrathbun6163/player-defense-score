import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.classification.classify_teams import (
    classify_feature_row,
    parse_args as parse_classification_args,
)
from src.classification.extract_uniform_features import (
    parse_args as parse_uniform_feature_args,
)
from src.court.select_court_polygon import (
    parse_args as parse_court_polygon_args,
)
from src.pipeline.planner import build_plan
from src.pipeline.possession import (
    ConfigurationError,
    PipelineManifest,
    PipelinePaths,
    load_manifest,
)
from src.tracking.audit_tracks import parse_args as parse_tracking_audit_args
from src.tracking.track_video import parse_args as parse_tracking_args


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "configs" / "possession_001_pipeline.json"

FRONT_STAGE_MODULES = (
    "src.court.select_court_polygon",
    "src.tracking.track_video",
    "src.tracking.audit_tracks",
    "src.classification.extract_uniform_features",
    "src.classification.classify_teams",
)

FRONT_STAGE_FILES = (
    REPO_ROOT / "src" / "court" / "select_court_polygon.py",
    REPO_ROOT / "src" / "tracking" / "track_video.py",
    REPO_ROOT / "src" / "tracking" / "audit_tracks.py",
    REPO_ROOT / "src" / "classification" / "extract_uniform_features.py",
    REPO_ROOT / "src" / "classification" / "classify_teams.py",
)

FRONT_STAGE_PARSERS = {
    "court_polygon": parse_court_polygon_args,
    "tracking": parse_tracking_args,
    "tracking_audit": parse_tracking_audit_args,
    "uniform_features": parse_uniform_feature_args,
    "team_classification": parse_classification_args,
}


class FrontStageInterfaceTests(unittest.TestCase):
    def test_each_front_stage_has_lightweight_cli_help(self):
        for module in FRONT_STAGE_MODULES:
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

    def test_front_stage_source_has_no_possession_001_literal(self):
        for path in FRONT_STAGE_FILES:
            with self.subTest(path=path):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("possession_001", source)

    def test_dry_run_builds_config_driven_commands(self):
        manifest = load_manifest(CONFIG_PATH)
        paths = PipelinePaths.build(
            REPO_ROOT,
            manifest,
            config_path=CONFIG_PATH,
        )
        plan = build_plan(manifest, paths)
        stages = {stage["name"]: stage for stage in plan["stages"]}

        for name in (
            "court_polygon",
            "tracking",
            "tracking_audit",
            "uniform_features",
            "team_classification",
        ):
            with self.subTest(name=name):
                self.assertEqual(
                    stages[name]["generalization_status"],
                    "cli_ready",
                )
                self.assertIsNotNone(stages[name]["command"])

        tracking_command = stages["tracking"]["command"]
        self.assertIn("data/clips/possession_001.mp4", tracking_command)
        self.assertIn("--detector-threshold", tracking_command)
        self.assertEqual(
            tracking_command[
                tracking_command.index("--detector-threshold") + 1
            ],
            "0.15",
        )
        self.assertEqual(
            plan["summary"]["generalization_status_counts"],
            {
                "cli_ready": 19,
                "review_gate": 2,
            },
        )

    def test_each_planned_command_is_accepted_by_its_cli_parser(self):
        manifest = load_manifest(CONFIG_PATH)
        paths = PipelinePaths.build(
            REPO_ROOT,
            manifest,
            config_path=CONFIG_PATH,
        )
        plan = build_plan(manifest, paths)
        stages = {stage["name"]: stage for stage in plan["stages"]}

        for stage_name, parser in FRONT_STAGE_PARSERS.items():
            with self.subTest(stage_name=stage_name):
                command = stages[stage_name]["command"]
                self.assertEqual(command[:3], ["python", "-m", command[2]])
                parsed = parser(command[3:])
                self.assertIsNotNone(parsed)


class FrontStageBehaviorTests(unittest.TestCase):
    def test_tracking_audit_uses_dynamic_frame_count(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tracks_path = temp_path / "tracks.csv"
            report_path = temp_path / "audit.json"

            with tracks_path.open(
                "w",
                newline="",
                encoding="utf-8",
            ) as output_file:
                writer = csv.DictWriter(
                    output_file,
                    fieldnames=(
                        "frame_index",
                        "track_id",
                        "confidence",
                        "floor_x",
                        "floor_y",
                    ),
                )
                writer.writeheader()

                for frame_index in range(4):
                    writer.writerow(
                        {
                            "frame_index": frame_index,
                            "track_id": 1,
                            "confidence": 0.9,
                            "floor_x": 100 + frame_index,
                            "floor_y": 200,
                        }
                    )

                for frame_index in range(3):
                    writer.writerow(
                        {
                            "frame_index": frame_index,
                            "track_id": 2,
                            "confidence": 0.8,
                            "floor_x": 300 + frame_index,
                            "floor_y": 200,
                        }
                    )

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "src.tracking.audit_tracks",
                    "--tracks",
                    str(tracks_path),
                    "--output",
                    str(report_path),
                    "--frame-count",
                    "4",
                    "--expected-player-count",
                    "2",
                    "--track-count-tolerance",
                    "0",
                    "--min-handoff-track-length",
                    "5",
                ],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["expected_frame_count"], 4)
            self.assertEqual(report["total_tracked_detections"], 7)
            self.assertEqual(report["unique_track_ids"], 2)
            self.assertEqual(
                report["per_frame_summary"]["frames_with_exactly_10"],
                3,
            )

    def test_classification_thresholds_preserve_white_dark_unknown(self):
        args = parse_classification_args(
            [
                "--video",
                "video.mp4",
                "--tracks",
                "tracks.csv",
                "--features",
                "features.csv",
                "--output-tracks",
                "classified.csv",
                "--output-video",
                "classified.mp4",
            ]
        )
        white = {
            "track_detections": 100,
            "feature_samples": 20,
            "texture_std": 50.0,
            "bright_fraction": 0.70,
            "dark_fraction": 0.10,
            "median_value": 200.0,
        }
        dark = {
            "track_detections": 100,
            "feature_samples": 20,
            "texture_std": 50.0,
            "bright_fraction": 0.20,
            "dark_fraction": 0.40,
            "median_value": 100.0,
        }
        unknown = dict(white, track_detections=2)

        self.assertEqual(classify_feature_row(white, args), "white")
        self.assertEqual(classify_feature_row(dark, args), "dark")
        self.assertEqual(classify_feature_row(unknown, args), "unknown")


class FrontStageManifestValidationTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def test_rejects_out_of_range_tracking_threshold(self):
        self.payload["overrides"]["tracking"]["detector_threshold"] = 1.1

        with self.assertRaisesRegex(ConfigurationError, "detector_threshold"):
            PipelineManifest.from_mapping(self.payload)

    def test_rejects_unknown_classification_setting(self):
        self.payload["overrides"]["classification"]["typo_threshold"] = 1

        with self.assertRaisesRegex(ConfigurationError, "unknown fields"):
            PipelineManifest.from_mapping(self.payload)


if __name__ == "__main__":
    unittest.main()
