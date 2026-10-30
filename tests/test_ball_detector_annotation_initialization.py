"""Tests for prediction-blind detector-window annotation initialization."""

from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.ball_tracking.annotations import BallAnnotationSet
from src.ball_tracking.detector_experiments import load_detector_experiment
from src.ball_tracking.initialize_detector_annotation_windows import (
    AnnotationWindowInitializationError,
    build_argument_parser,
    build_draft_payload,
    development_windows,
    initialize_detector_annotation_windows,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    REPO_ROOT
    / "configs"
    / "ball_tracking"
    / "experiments"
    / "rfdetr_medium_image_only_baseline_v0_1.json"
)


class DetectorAnnotationInitializationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.experiment = load_detector_experiment(MANIFEST)

    def test_exact_six_development_windows_are_selected(self) -> None:
        windows = development_windows(self.experiment)
        self.assertEqual(len(windows), 6)
        self.assertEqual(
            {item.selection_purpose for item in windows},
            {"representative_evaluation", "challenge_evaluation"},
        )
        self.assertEqual({item.possession_id for item in windows}, {
            "possession_001",
            "possession_002",
            "possession_003",
        })

    def test_payload_is_strict_all_unlabeled_and_preserves_embargo(self) -> None:
        window = development_windows(self.experiment)[0]
        payload = build_draft_payload(
            window,
            annotator_id="ryan_codex_joint",
            created_at_utc="2026-08-24T05:10:00Z",
        )
        parsed = BallAnnotationSet.from_mapping(payload)
        self.assertEqual(parsed.annotation_set_id, window.annotation_set_id)
        self.assertEqual(len(parsed.annotations), 25)
        self.assertTrue(
            all(item.annotation_status == "unlabeled" for item in parsed.annotations)
        )
        self.assertEqual(parsed.review.status, "draft")
        self.assertIsNone(parsed.review.reviewer_id)
        self.assertIsNone(parsed.review.reviewed_at_utc)

    def test_ready_pilot_window_is_rejected(self) -> None:
        pilot = self.experiment.ready_windows[0]
        with self.assertRaises(AnnotationWindowInitializationError):
            build_draft_payload(
                pilot,
                annotator_id="ryan",
                created_at_utc="2026-08-24T05:10:00Z",
            )

    def test_cli_has_no_window_or_prediction_override(self) -> None:
        actions = {action.dest for action in build_argument_parser()._actions}
        self.assertNotIn("window", actions)
        self.assertNotIn("selection_purpose", actions)
        self.assertNotIn("allow_predictions", actions)

    def test_any_embargoed_prediction_blocks_all_publication(self) -> None:
        embargoed = next(
            item
            for item in self.experiment.windows
            if item.execution_status == "annotation_pending_prediction_embargo"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            prediction = root.joinpath(*embargoed.output_path.parts)
            prediction.parent.mkdir(parents=True)
            prediction.write_text("forbidden", encoding="utf-8")
            with self.assertRaises(AnnotationWindowInitializationError):
                initialize_detector_annotation_windows(
                    MANIFEST,
                    root,
                    annotator_id="ryan",
                    created_at_utc="2026-08-24T05:10:00Z",
                )
            annotation_root = root / "configs" / "ball_tracking" / "annotations"
            self.assertFalse(annotation_root.exists())

    def test_exact_reuse_and_conflict_never_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with patch(
                "src.ball_tracking.initialize_detector_annotation_windows."
                "verify_source_video",
                return_value={},
            ):
                first = initialize_detector_annotation_windows(
                    MANIFEST,
                    root,
                    annotator_id="ryan",
                    created_at_utc="2026-08-24T05:10:00Z",
                )
                second = initialize_detector_annotation_windows(
                    MANIFEST,
                    root,
                    annotator_id="ryan",
                    created_at_utc="2026-08-24T05:10:00Z",
                )
                self.assertEqual(len(first.created), 6)
                self.assertEqual(len(second.reused), 6)
                target = first.created[0]
                target.write_text("conflict", encoding="utf-8")
                with self.assertRaises(AnnotationWindowInitializationError):
                    initialize_detector_annotation_windows(
                        MANIFEST,
                        root,
                        annotator_id="ryan",
                        created_at_utc="2026-08-24T05:10:00Z",
                    )
                self.assertEqual(target.read_text(encoding="utf-8"), "conflict")


if __name__ == "__main__":
    unittest.main()
