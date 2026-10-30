"""Focused tests for prediction-blind independent annotation preparation."""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from src.ball_tracking import prepare_independent_review as module
from src.ball_tracking.annotations import BallAnnotationSet
from src.ball_tracking.prepare_annotation_review import prepare_annotation_review
from src.ball_tracking.prepare_independent_review import (
    EXPECTED_FRAME_COUNT,
    FULL_CENSUS_POLICY,
    GENERATOR_PROCESS_DECLARATION,
    GENERATOR_FINGERPRINT_FIELDS,
    IndependentReviewError,
    LIFECYCLE,
    NEXT_STEP_GUIDANCE,
    binding_components,
    binding_sha256,
    build_argument_parser,
    generator_fingerprint,
    launch_independent_editor,
    prepare_independent_review,
    validate_independent_editor_target,
    validate_neutral_bundle,
    validate_reviewer_id,
)


REVIEWER_ID = "alex_independent_2026"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict) -> bytes:
    content = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
    path.write_bytes(content)
    return content


def write_video(root: Path) -> Path:
    path = root / "data" / "clips" / "possession_001.avi"
    path.parent.mkdir(parents=True)
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        10.0,
        (96, 54),
    )
    if not writer.isOpened():
        raise RuntimeError("synthetic MJPG writer unavailable")
    try:
        for frame_index in range(405):
            frame = np.zeros((54, 96, 3), dtype=np.uint8)
            frame[:, :, 0] = frame_index * 7 % 256
            frame[:, :, 1] = np.arange(96, dtype=np.uint8)
            frame[:, :, 2] = np.arange(54, dtype=np.uint8)[:, None]
            writer.write(frame)
    finally:
        writer.release()
    return path


def source_metadata(video_path: Path, root: Path) -> dict:
    capture = cv2.VideoCapture(str(video_path))
    try:
        return {
            "path": video_path.relative_to(root).as_posix(),
            "sha256": sha256_file(video_path),
            "width_px": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height_px": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": float(capture.get(cv2.CAP_PROP_FPS)),
            "frame_count": int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
        }
    finally:
        capture.release()


def blank_payload(video_path: Path, root: Path) -> dict:
    return {
        "schema_version": "0.1",
        "annotation_set_id": "possession_001_neutral_seed_v0_1",
        "possession_id": "possession_001",
        "source_video": source_metadata(video_path, root),
        "window": {
            "start_frame_index": 375,
            "end_frame_index": 399,
            "selection_purpose": "protocol_adjudication",
        },
        "coordinate_system": {
            "frame_index_origin": 0,
            "pixel_origin": "top_left",
            "x_axis_direction": "right",
            "y_axis_direction": "down",
            "center_definition": "complete_ball_center",
            "timestamp_rule": "frame_index_divided_by_fps",
        },
        "review": {
            "status": "draft",
            "annotator_id": "neutral_seed_builder",
            "reviewer_id": None,
            "created_at_utc": "2026-08-23T12:00:00Z",
            "reviewed_at_utc": None,
        },
        "annotations": [
            {
                "frame_index": frame_index,
                "annotation_status": "unlabeled",
                "visibility": None,
                "absence_reason": None,
                "game_ball_identity_certainty": None,
                "geometry": None,
                "localization_eligible": False,
                "difficulty_tags": [],
                "notes": None,
            }
            for frame_index in range(375, 400)
        ],
    }


def complete_payload(payload: dict, *, reviewed: bool = False) -> dict:
    result = json.loads(json.dumps(payload))
    for offset, row in enumerate(result["annotations"]):
        row.update(
            {
                "annotation_status": "labeled",
                "visibility": "fully_visible",
                "absence_reason": None,
                "game_ball_identity_certainty": "certain",
                "geometry": {
                    "center_xy_px": [20.0 + offset, 25.0],
                    "source": "observed_complete_ball_center",
                    "uncertainty_radius_px": 2.0,
                },
                "localization_eligible": True,
                "difficulty_tags": [],
                "notes": None,
            }
        )
    if reviewed:
        result["review"]["status"] = "reviewed"
        result["review"]["reviewer_id"] = "later_adjudicator"
        # A generated workspace uses today's creation time; keep this fixture
        # chronologically valid so it reaches the reviewed-workspace guard.
        created = datetime.fromisoformat(
            result["review"]["created_at_utc"].replace("Z", "+00:00")
        )
        result["review"]["reviewed_at_utc"] = (created + timedelta(seconds=1)).isoformat()
    return result


def prepare_inputs(root: Path) -> tuple[Path, Path, Path, bytes]:
    protocol_path = root / "docs" / "ball_tracking_annotation_protocol.md"
    protocol_path.parent.mkdir(parents=True)
    protocol_bytes = (
        b"# Ball-tracking annotation protocol v0.1\n\n"
        b"Synthetic strict protocol snapshot for focused tests.\n"
    )
    protocol_path.write_bytes(protocol_bytes)
    video_path = write_video(root)
    seed_path = root / "neutral_seed.json"
    write_json(seed_path, blank_payload(video_path, root))
    neutral_dir = (
        root
        / "data"
        / "outputs"
        / "ball_tracking"
        / "annotation_review"
        / "possession_001"
        / "frames_0375_0399"
    )
    prepare_annotation_review(seed_path, root, neutral_dir)
    primary = complete_payload(blank_payload(video_path, root))
    primary["annotation_set_id"] = (
        "possession_001_frames_0375_0399_protocol_adjudication_v0_1"
    )
    primary["review"]["annotator_id"] = "ryan_codex_joint"
    primary["annotations"][0]["notes"] = "PRIMARY_LABEL_LEAK_CANARY"
    write_json(seed_path, primary)
    return neutral_dir, seed_path, video_path, protocol_bytes


def read_working(path: Path) -> dict:
    return json.loads(path.read_bytes())


class IndependentReviewCreationTests(unittest.TestCase):
    def test_api_is_neutral_only_and_blank_375_through_399(self) -> None:
        parameters = inspect.signature(prepare_independent_review).parameters
        self.assertEqual(
            list(parameters),
            ["neutral_bundle", "repository_root", "reviewer_id"],
        )
        parser_options = {
            option
            for action in build_argument_parser()._actions
            for option in action.option_strings
        }
        self.assertNotIn("--annotations", parser_options)
        self.assertNotIn("--output-dir", parser_options)
        self.assertNotIn("--overwrite", parser_options)

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, primary_path, video_path, protocol_bytes = prepare_inputs(root)
            primary_bytes = primary_path.read_bytes()
            source_bytes = video_path.read_bytes()
            neutral_manifest_bytes = (neutral_dir / "manifest.json").read_bytes()
            result = prepare_independent_review(neutral_dir, root, REVIEWER_ID)

            self.assertEqual(result.state, "created_pristine_draft")
            self.assertEqual(result.unlabeled_frame_count, 25)
            self.assertEqual(
                result.review_root.relative_to(root).as_posix(),
                "data/outputs/ball_tracking/independent_review/"
                "possession_001/frames_0375_0399/alex_independent_2026",
            )
            working = read_working(result.workspace_annotation_path)
            self.assertEqual(
                [row["frame_index"] for row in working["annotations"]],
                list(range(375, 400)),
            )
            for row in working["annotations"]:
                self.assertEqual(
                    row,
                    {
                        "frame_index": row["frame_index"],
                        "annotation_status": "unlabeled",
                        "visibility": None,
                        "absence_reason": None,
                        "game_ball_identity_certainty": None,
                        "geometry": None,
                        "localization_eligible": False,
                        "difficulty_tags": [],
                        "notes": None,
                    },
                )
            self.assertEqual(working["review"]["status"], "draft")
            self.assertEqual(working["review"]["annotator_id"], REVIEWER_ID)
            self.assertIsNone(working["review"]["reviewer_id"])
            self.assertIsNone(working["review"]["reviewed_at_utc"])
            self.assertNotEqual(
                working["annotation_set_id"],
                "possession_001_neutral_seed_v0_1",
            )
            template_path = result.kit_dir / "blank_annotation_template.json"
            self.assertEqual(
                template_path.read_bytes(),
                result.workspace_annotation_path.read_bytes(),
            )
            self.assertFalse(
                os.path.samestat(
                    template_path.stat(),
                    result.workspace_annotation_path.stat(),
                )
            )
            self.assertEqual(
                (result.kit_dir / "neutral_manifest_snapshot.json").read_bytes(),
                neutral_manifest_bytes,
            )
            self.assertEqual(
                (result.kit_dir / "protocol_snapshot.md").read_bytes(),
                protocol_bytes,
            )
            manifest = json.loads((result.kit_dir / "manifest.json").read_bytes())
            self.assertEqual(len(manifest["assets"]["source_frames"]), 25)
            self.assertEqual(
                manifest["assets"]["source_frames"][-1]["frame_index"],
                399,
            )
            self.assertEqual(manifest["window"]["census_policy"], FULL_CENSUS_POLICY)
            self.assertNotIn("blindness_attestation", manifest)
            self.assertEqual(
                manifest["generator_process_declaration"],
                GENERATOR_PROCESS_DECLARATION,
            )
            self.assertFalse(
                manifest["generator_process_declaration"][
                    "reviewer_exposure_attestation_included"
                ]
            )
            self.assertEqual(manifest["lifecycle"], LIFECYCLE)
            self.assertEqual(result.lifecycle_status, "draft")
            self.assertEqual(result.next_step, NEXT_STEP_GUIDANCE)
            start_here_path = result.kit_dir / "START_HERE.md"
            start_here = start_here_path.read_text(encoding="utf-8")
            self.assertIn("repository-local, not a portable", start_here)
            self.assertIn("requires the original source clip", start_here)
            self.assertIn("repository's `.venv`", start_here)
            self.assertIn(
                ".\\.venv\\Scripts\\python.exe -m "
                "src.ball_tracking.prepare_independent_review",
                start_here,
            )
            self.assertIn("--launch-editor", start_here)
            self.assertIn("The current native frame", start_here)
            self.assertIn("context-only", start_here)
            self.assertIn("25/25 completed frames", start_here)
            self.assertIn("remains `draft`", start_here)
            self.assertIn("freeze/submission step is not implemented", start_here)
            self.assertIn("captured only during that later submission", start_here)
            self.assertEqual(
                manifest["assets"]["start_here"]["sha256"],
                sha256_file(start_here_path),
            )
            self.assertEqual(
                manifest["binding"]["start_here_sha256"],
                sha256_file(start_here_path),
            )
            self.assertFalse(manifest["safeguards"]["primary_annotation_json_read"])
            self.assertNotIn(
                b"PRIMARY_LABEL_LEAK_CANARY",
                b"".join(path.read_bytes() for path in result.kit_dir.rglob("*") if path.is_file()),
            )
            self.assertEqual(primary_path.read_bytes(), primary_bytes)
            self.assertEqual(video_path.read_bytes(), source_bytes)

    def test_reviewer_identity_rejections(self) -> None:
        rejected = (
            "ryan_codex_joint",
            "reviewer",
            "placeholder",
            "test_reviewer_1",
            "unknown",
            "UpperCase",
            "bad/path",
            "",
        )
        for value in rejected:
            with self.subTest(reviewer_id=value):
                with self.assertRaises(IndependentReviewError):
                    validate_reviewer_id(value)
        self.assertEqual(validate_reviewer_id(REVIEWER_ID), REVIEWER_ID)

    def test_primary_annotator_alias_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            IndependentReviewError,
            "independent reviewer ID must differ from the primary annotator",
        ):
            validate_reviewer_id("ryan")

    def test_fingerprint_is_closed_and_output_reparse_is_rejected(self) -> None:
        fingerprint = generator_fingerprint()
        self.assertEqual(set(fingerprint), GENERATOR_FINGERPRINT_FIELDS)
        baseline_digest = module.generator_fingerprint_sha256(fingerprint)
        for field in sorted(GENERATOR_FINGERPRINT_FIELDS):
            with self.subTest(field=field):
                changed = dict(fingerprint)
                changed[field] = f"{changed[field]}-changed"
                self.assertNotEqual(
                    module.generator_fingerprint_sha256(changed),
                    baseline_digest,
                )

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, _primary, _video, _protocol = prepare_inputs(root)
            with patch.object(
                module,
                "_has_windows_reparse_point",
                side_effect=lambda path: path.name == "independent_review",
            ):
                with self.assertRaisesRegex(
                    IndependentReviewError,
                    "output contains a symlink or Windows reparse/junction",
                ):
                    prepare_independent_review(neutral_dir, root, REVIEWER_ID)

    def test_guarded_launcher_refuses_primary_and_invokes_only_fixed_target(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, primary_path, _video, _protocol = prepare_inputs(root)
            result = prepare_independent_review(neutral_dir, root, REVIEWER_ID)

            with self.assertRaisesRegex(
                IndependentReviewError,
                "primary or arbitrary annotation paths are forbidden",
            ):
                validate_independent_editor_target(
                    result.review_root,
                    primary_path,
                    root,
                    REVIEWER_ID,
                )

            with patch.object(
                module,
                "_invoke_annotation_editor",
                return_value=23,
            ) as invoke:
                exit_code = launch_independent_editor(
                    neutral_dir,
                    root,
                    REVIEWER_ID,
                )
            self.assertEqual(exit_code, 23)
            invoke.assert_called_once()
            invoked_argv, guarded_target = invoke.call_args.args
            self.assertEqual(
                invoked_argv,
                [
                    "--annotations",
                    str(result.workspace_annotation_path),
                    "--repository-root",
                    str(root.resolve()),
                ],
            )
            self.assertEqual(
                guarded_target.annotation_path,
                result.workspace_annotation_path,
            )

            primary_payload = json.loads(primary_path.read_bytes())
            primary_bytes = write_json(
                result.workspace_annotation_path,
                primary_payload,
            )
            with patch.object(module, "_invoke_annotation_editor") as invoke:
                with self.assertRaises(IndependentReviewError):
                    launch_independent_editor(neutral_dir, root, REVIEWER_ID)
            invoke.assert_not_called()
            self.assertEqual(
                result.workspace_annotation_path.read_bytes(),
                primary_bytes,
            )

    def test_start_here_powershell_command_quotes_odd_bound_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, _primary, _video, _protocol = prepare_inputs(root)
            odd_neutral_dir = neutral_dir.parent / "odd_$(do_not_run)_`tick_o'hare"
            neutral_dir.rename(odd_neutral_dir)
            result = prepare_independent_review(
                odd_neutral_dir,
                root,
                REVIEWER_ID,
            )
            start_here = (result.kit_dir / "START_HERE.md").read_text(
                encoding="utf-8"
            )
            command = next(
                line
                for line in start_here.splitlines()
                if line.startswith(".\\.venv\\Scripts\\python.exe")
            )
            neutral_argument = (
                odd_neutral_dir.relative_to(root)
                .as_posix()
                .replace("/", "\\")
                .replace("'", "''")
            )
            self.assertEqual(
                command,
                ".\\.venv\\Scripts\\python.exe -m "
                "src.ball_tracking.prepare_independent_review "
                f"--neutral-bundle '{neutral_argument}' "
                "--repository-root '.' "
                f"--reviewer-id '{REVIEWER_ID}' --launch-editor",
            )
            self.assertIn("$(do_not_run)", command)
            self.assertIn("`tick", command)
            self.assertIn("o''hare", command)
            self.assertNotIn('--neutral-bundle "', command)


class IndependentReviewLifecycleTests(unittest.TestCase):
    def test_pristine_rerun_reuses_exact_bytes_and_created_time(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, _primary, _video, _protocol = prepare_inputs(root)
            first = prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            working_bytes = first.workspace_annotation_path.read_bytes()
            origin_bytes = (first.review_root / "workspace" / "origin.json").read_bytes()
            created_at = read_working(first.workspace_annotation_path)["review"][
                "created_at_utc"
            ]

            second = prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            self.assertEqual(second.state, "reused_pristine_draft")
            self.assertEqual(second.workspace_annotation_path.read_bytes(), working_bytes)
            self.assertEqual(
                (second.review_root / "workspace" / "origin.json").read_bytes(),
                origin_bytes,
            )
            self.assertEqual(
                read_working(second.workspace_annotation_path)["review"][
                    "created_at_utc"
                ],
                created_at,
            )

    def test_partial_and_completed_drafts_are_preserved_and_stay_draft(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, _primary, _video, _protocol = prepare_inputs(root)
            result = prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            payload = read_working(result.workspace_annotation_path)
            created_at = payload["review"]["created_at_utc"]
            payload["annotations"][0].update(
                {
                    "annotation_status": "labeled",
                    "visibility": "fully_visible",
                    "game_ball_identity_certainty": "certain",
                    "geometry": {
                        "center_xy_px": [20.0, 25.0],
                        "source": "observed_complete_ball_center",
                        "uncertainty_radius_px": 2.0,
                    },
                    "localization_eligible": True,
                }
            )
            partial_bytes = write_json(result.workspace_annotation_path, payload)
            partial = prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            self.assertEqual(partial.state, "resumable_partial_draft")
            self.assertEqual(partial.unlabeled_frame_count, 24)
            self.assertEqual(partial.workspace_annotation_path.read_bytes(), partial_bytes)

            completed_payload = complete_payload(payload)
            completed_bytes = write_json(
                result.workspace_annotation_path,
                completed_payload,
            )
            completed = prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            self.assertEqual(completed.state, "resumable_completed_draft")
            self.assertEqual(completed.unlabeled_frame_count, 0)
            self.assertEqual(
                completed.workspace_annotation_path.read_bytes(),
                completed_bytes,
            )
            completed_on_disk = read_working(completed.workspace_annotation_path)
            self.assertEqual(completed_on_disk["review"]["status"], "draft")
            self.assertIsNone(completed_on_disk["review"]["reviewer_id"])
            self.assertEqual(
                completed_on_disk["review"]["created_at_utc"],
                created_at,
            )

    def test_reviewed_workspace_is_refused_without_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, _primary, _video, _protocol = prepare_inputs(root)
            result = prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            reviewed = complete_payload(read_working(result.workspace_annotation_path), reviewed=True)
            reviewed_bytes = write_json(result.workspace_annotation_path, reviewed)
            with self.assertRaisesRegex(
                IndependentReviewError,
                "must remain draft",
            ):
                prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            self.assertEqual(result.workspace_annotation_path.read_bytes(), reviewed_bytes)

    def test_invalid_or_mismatched_workspace_is_never_reset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, _primary, _video, _protocol = prepare_inputs(root)
            result = prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            original = read_working(result.workspace_annotation_path)
            cases = []
            mismatched_id = json.loads(json.dumps(original))
            mismatched_id["annotation_set_id"] = "foreign_independent_set"
            cases.append((b"{invalid json", "could not parse"))
            cases.append(
                (
                    (json.dumps(mismatched_id, indent=2) + "\n").encode("utf-8"),
                    "identity mismatch: annotation_set_id",
                )
            )
            mismatched_source = json.loads(json.dumps(original))
            mismatched_source["source_video"]["sha256"] = "0" * 64
            cases.append(
                (
                    (json.dumps(mismatched_source, indent=2) + "\n").encode("utf-8"),
                    "identity mismatch: source_video",
                )
            )
            for content, expected_error in cases:
                with self.subTest(expected_error=expected_error):
                    result.workspace_annotation_path.write_bytes(content)
                    with self.assertRaisesRegex(
                        IndependentReviewError,
                        expected_error,
                    ):
                        prepare_independent_review(neutral_dir, root, REVIEWER_ID)
                    self.assertEqual(
                        result.workspace_annotation_path.read_bytes(),
                        content,
                    )

    def test_origin_mismatch_and_extra_workspace_artifact_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, _primary, _video, _protocol = prepare_inputs(root)
            result = prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            origin_path = result.review_root / "workspace" / "origin.json"
            original_origin_bytes = origin_path.read_bytes()
            origin = json.loads(origin_path.read_bytes())
            origin["annotation_set_id"] = "foreign_independent_set"
            tampered_origin = write_json(origin_path, origin)
            with self.assertRaisesRegex(
                IndependentReviewError,
                "workspace origin does not match",
            ):
                prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            self.assertEqual(origin_path.read_bytes(), tampered_origin)

            # Restore only for the independent extra-tree assertion.
            origin_path.write_bytes(original_origin_bytes)
            extra_path = result.review_root / "workspace" / "notes.txt"
            extra_path.write_text("preserve me", encoding="utf-8")
            with self.assertRaisesRegex(
                IndependentReviewError,
                "workspace contains extras",
            ):
                prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            self.assertEqual(extra_path.read_text(encoding="utf-8"), "preserve me")


class IndependentReviewEditorGuardTests(unittest.TestCase):
    def test_coherent_primary_copy_forgery_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, primary_path, _video, _protocol = prepare_inputs(root)
            result = prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            primary_bytes = primary_path.read_bytes()
            primary = json.loads(primary_bytes)

            template_path = result.kit_dir / "blank_annotation_template.json"
            template_path.write_bytes(primary_bytes)
            result.workspace_annotation_path.write_bytes(primary_bytes)
            manifest_path = result.kit_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_bytes())
            forged_binding = "f" * 64
            manifest["binding"]["kit_binding_sha256"] = forged_binding
            manifest["binding"]["workspace_created_at_utc"] = primary["review"][
                "created_at_utc"
            ]
            template_record = manifest["assets"]["blank_annotation_template"]
            template_record.update(
                {
                    "sha256": sha256_file(template_path),
                    "byte_size": template_path.stat().st_size,
                    "annotation_set_id": primary["annotation_set_id"],
                    "annotator_id": primary["review"]["annotator_id"],
                    "created_at_utc": primary["review"]["created_at_utc"],
                }
            )
            write_json(manifest_path, manifest)

            origin_path = result.review_root / "workspace" / "origin.json"
            origin = json.loads(origin_path.read_bytes())
            origin.update(
                {
                    "kit_binding_sha256": forged_binding,
                    "kit_manifest_sha256": sha256_file(manifest_path),
                    "template_sha256": sha256_file(template_path),
                    "annotation_set_id": primary["annotation_set_id"],
                    "created_at_utc": primary["review"]["created_at_utc"],
                }
            )
            forged_origin_bytes = write_json(origin_path, origin)

            with self.assertRaises(IndependentReviewError):
                validate_independent_editor_target(
                    result.review_root,
                    result.workspace_annotation_path,
                    root,
                    REVIEWER_ID,
                )
            self.assertEqual(result.workspace_annotation_path.read_bytes(), primary_bytes)
            self.assertEqual(template_path.read_bytes(), primary_bytes)
            self.assertEqual(origin_path.read_bytes(), forged_origin_bytes)

    def test_swap_after_guard_is_rejected_before_editor_main(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, primary_path, _video, _protocol = prepare_inputs(root)
            result = prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            primary_bytes = primary_path.read_bytes()
            original_guard = module.validate_independent_editor_target

            def guard_then_swap(*args, **kwargs):
                guarded = original_guard(*args, **kwargs)
                guarded.annotation_path.write_bytes(primary_bytes)
                return guarded

            with patch.object(
                module,
                "validate_independent_editor_target",
                side_effect=guard_then_swap,
            ), patch("src.ball_tracking.annotate_frames.main") as editor_main:
                with self.assertRaisesRegex(
                    IndependentReviewError,
                    "changed after the editor guard",
                ):
                    launch_independent_editor(neutral_dir, root, REVIEWER_ID)
            editor_main.assert_not_called()
            self.assertEqual(
                result.workspace_annotation_path.read_bytes(),
                primary_bytes,
            )

    def test_swap_after_final_recheck_uses_verified_in_memory_session(self) -> None:
        from src.ball_tracking import annotate_frames as editor

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, primary_path, _video, _protocol = prepare_inputs(root)
            result = prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            primary_bytes = primary_path.read_bytes()
            original_recheck = module._recheck_guarded_editor_snapshot
            captured = {}

            def recheck_then_swap(target):
                original_recheck(target)
                target.annotation_path.write_bytes(primary_bytes)

            def inspect_initial_session(argv):
                args = editor.build_argument_parser().parse_args(argv)
                captured["session"] = editor.prepare_annotation_session(
                    args.annotations,
                    args.repository_root,
                )
                return 0

            with patch.object(
                module,
                "_recheck_guarded_editor_snapshot",
                side_effect=recheck_then_swap,
            ), patch.object(editor, "main", side_effect=inspect_initial_session):
                self.assertEqual(
                    launch_independent_editor(neutral_dir, root, REVIEWER_ID),
                    0,
                )

            session = captured["session"]
            self.assertEqual(session.annotation_set.review.annotator_id, REVIEWER_ID)
            self.assertNotEqual(
                session.annotation_set.annotation_set_id,
                "possession_001_frames_0375_0399_protocol_adjudication_v0_1",
            )
            self.assertTrue(
                all(
                    row.annotation_status == "unlabeled"
                    for row in session.annotation_set.annotations
                )
            )
            self.assertNotIn(
                "PRIMARY_LABEL_LEAK_CANARY",
                json.dumps(session.annotation_set.to_dict()),
            )
            self.assertEqual(
                result.workspace_annotation_path.read_bytes(),
                primary_bytes,
            )
            with self.assertRaisesRegex(
                editor.AnnotationEditorError,
                "changed on disk since this editor loaded it",
            ):
                editor.atomic_save_frame(
                    session.annotation_path,
                    session.annotation_set,
                    session.annotation_set.annotations[0].to_dict(),
                )
            self.assertEqual(
                result.workspace_annotation_path.read_bytes(),
                primary_bytes,
            )


class IndependentReviewNeutralTrustTests(unittest.TestCase):
    def test_source_byte_change_fails_before_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, _primary, video_path, _protocol = prepare_inputs(root)
            video_path.write_bytes(video_path.read_bytes() + b"source-tamper")
            tampered_bytes = video_path.read_bytes()
            with self.assertRaisesRegex(
                IndependentReviewError,
                "source verification failed",
            ):
                prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            self.assertEqual(video_path.read_bytes(), tampered_bytes)
            self.assertFalse(
                (
                    root
                    / "data"
                    / "outputs"
                    / "ball_tracking"
                    / "independent_review"
                ).exists()
            )

    def test_coherently_rehashed_final_neutral_frame_tamper_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, _primary, _video, _protocol = prepare_inputs(root)
            manifest_path = neutral_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_bytes())
            record = manifest["assets"]["source_frames"][-1]
            self.assertEqual(record["frame_index"], 399)
            frame_path = neutral_dir / Path(record["path"])
            frame = cv2.imread(str(frame_path), cv2.IMREAD_COLOR)
            frame[0, 0, 0] ^= 255
            self.assertTrue(cv2.imwrite(str(frame_path), frame))
            record["sha256"] = sha256_file(frame_path)
            record["byte_size"] = frame_path.stat().st_size
            tampered_manifest = write_json(manifest_path, manifest)
            tampered_frame = frame_path.read_bytes()
            with self.assertRaisesRegex(
                IndependentReviewError,
                "pixel-match sequential source decode: frame 399",
            ):
                prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            self.assertEqual(frame_path.read_bytes(), tampered_frame)
            self.assertEqual(manifest_path.read_bytes(), tampered_manifest)

    def test_wrong_type_safeguard_order_final_and_extra_tree_are_rejected(
        self,
    ) -> None:
        mutations = (
            (
                "wrong_type",
                lambda manifest: manifest.update(
                    {"asset_bundle_type": "ball_annotation_visual_review"}
                ),
            ),
            (
                "safeguard",
                lambda manifest: manifest["review_safeguards"].update(
                    {"detector_outputs_included": True}
                ),
            ),
            (
                "order",
                lambda manifest: manifest["assets"]["source_frames"].__setitem__(
                    slice(0, 2),
                    list(reversed(manifest["assets"]["source_frames"][:2])),
                ),
            ),
            (
                "final",
                lambda manifest: manifest["assets"]["source_frames"][-1].update(
                    {"frame_index": 398}
                ),
            ),
            (
                "window",
                lambda manifest: manifest["window"].update(
                    {"frame_count": 24}
                ),
            ),
        )
        for name, mutate in mutations:
            with self.subTest(case=name), tempfile.TemporaryDirectory() as temporary_directory:
                root = Path(temporary_directory)
                neutral_dir, _primary, _video, _protocol = prepare_inputs(root)
                manifest_path = neutral_dir / "manifest.json"
                manifest = json.loads(manifest_path.read_bytes())
                mutate(manifest)
                tampered = write_json(manifest_path, manifest)
                with self.assertRaises(IndependentReviewError):
                    prepare_independent_review(neutral_dir, root, REVIEWER_ID)
                self.assertEqual(manifest_path.read_bytes(), tampered)

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, _primary, _video, _protocol = prepare_inputs(root)
            extra_path = neutral_dir / "foreign_detector_hint.txt"
            extra_path.write_text("do not delete", encoding="utf-8")
            with self.assertRaisesRegex(
                IndependentReviewError,
                "unrecognized artifacts",
            ):
                prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            self.assertEqual(extra_path.read_text(encoding="utf-8"), "do not delete")

    def test_neutral_reparse_ancestor_and_outside_type_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, _primary, _video, _protocol = prepare_inputs(root)
            with patch.object(
                module,
                "_has_windows_reparse_point",
                side_effect=lambda path: path.name == "source_frames",
            ):
                with self.assertRaisesRegex(
                    IndependentReviewError,
                    "reparse/junction",
                ):
                    validate_neutral_bundle(neutral_dir, root)

            with patch.object(
                module,
                "_has_windows_reparse_point",
                side_effect=lambda path: path.name == "docs",
            ):
                with self.assertRaisesRegex(
                    IndependentReviewError,
                    "protocol path contains a symlink or Windows "
                    "reparse/junction ancestor",
                ):
                    prepare_independent_review(neutral_dir, root, REVIEWER_ID)

            visual_dir = (
                root
                / "data"
                / "outputs"
                / "ball_tracking"
                / "annotation_visual_review"
                / "foreign"
            )
            visual_dir.mkdir(parents=True)
            (visual_dir / "manifest.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(
                IndependentReviewError,
                "dedicated root",
            ):
                validate_neutral_bundle(visual_dir, root)


class IndependentReviewTamperAndFailureTests(unittest.TestCase):
    def test_neutral_manifest_toctou_prevents_publication_and_cleans_staging(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, _primary, _video, _protocol = prepare_inputs(root)
            manifest_path = neutral_dir / "manifest.json"
            original_build = module._build_kit_and_workspace

            def build_then_change(*args, **kwargs):
                result = original_build(*args, **kwargs)
                manifest_path.write_bytes(manifest_path.read_bytes() + b"\n")
                return result

            with patch.object(
                module,
                "_build_kit_and_workspace",
                side_effect=build_then_change,
            ):
                with self.assertRaisesRegex(
                    IndependentReviewError,
                    "neutral manifest changed during preparation",
                ):
                    prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            self.assertEqual(list(root.rglob(f".{REVIEWER_ID}.staging-*")), [])
            self.assertFalse(
                (
                    root
                    / "data"
                    / "outputs"
                    / "ball_tracking"
                    / "independent_review"
                    / "possession_001"
                    / "frames_0375_0399"
                    / REVIEWER_ID
                ).exists()
            )

    def test_protocol_toctou_prevents_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, _primary, _video, _protocol = prepare_inputs(root)
            protocol_path = root / "docs" / "ball_tracking_annotation_protocol.md"
            original_build = module._build_kit_and_workspace

            def build_then_change(*args, **kwargs):
                result = original_build(*args, **kwargs)
                protocol_path.write_bytes(protocol_path.read_bytes() + b"changed")
                return result

            with patch.object(
                module,
                "_build_kit_and_workspace",
                side_effect=build_then_change,
            ):
                with self.assertRaisesRegex(
                    IndependentReviewError,
                    "protocol changed during preparation",
                ):
                    prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            self.assertEqual(list(root.rglob(f".{REVIEWER_ID}.staging-*")), [])

    def test_coherently_rehashed_immutable_frame_tamper_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, _primary, _video, _protocol = prepare_inputs(root)
            result = prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            manifest_path = result.kit_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_bytes())
            record = manifest["assets"]["source_frames"][-1]
            frame_path = result.kit_dir / Path(record["path"])
            frame = cv2.imread(str(frame_path), cv2.IMREAD_COLOR)
            frame[-1, -1, 1] ^= 255
            self.assertTrue(cv2.imwrite(str(frame_path), frame))
            record["sha256"] = sha256_file(frame_path)
            record["byte_size"] = frame_path.stat().st_size
            tampered_manifest = write_json(manifest_path, manifest)
            tampered_frame = frame_path.read_bytes()
            with self.assertRaisesRegex(
                IndependentReviewError,
                "does not match verified source pixels: frame 399",
            ):
                prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            self.assertEqual(frame_path.read_bytes(), tampered_frame)
            self.assertEqual(manifest_path.read_bytes(), tampered_manifest)

    def test_coherently_rehashed_start_here_tamper_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, _primary, _video, _protocol = prepare_inputs(root)
            result = prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            start_here_path = result.kit_dir / "START_HERE.md"
            start_here_path.write_bytes(
                start_here_path.read_bytes() + b"\nUse a foreign file instead.\n"
            )
            tampered_start_here = start_here_path.read_bytes()
            manifest_path = result.kit_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_bytes())
            record = manifest["assets"]["start_here"]
            record["sha256"] = sha256_file(start_here_path)
            record["byte_size"] = start_here_path.stat().st_size
            tampered_manifest = write_json(manifest_path, manifest)
            origin_path = result.review_root / "workspace" / "origin.json"
            origin = json.loads(origin_path.read_bytes())
            origin["kit_manifest_sha256"] = sha256_file(manifest_path)
            tampered_origin = write_json(origin_path, origin)

            with self.assertRaisesRegex(
                IndependentReviewError,
                "START_HERE instructions do not match deterministic content",
            ):
                prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            self.assertEqual(start_here_path.read_bytes(), tampered_start_here)
            self.assertEqual(manifest_path.read_bytes(), tampered_manifest)
            self.assertEqual(origin_path.read_bytes(), tampered_origin)

    def test_immutable_extra_artifact_is_never_removed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, _primary, _video, _protocol = prepare_inputs(root)
            result = prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            extra = result.kit_dir / "foreign.txt"
            extra.write_text("preserve", encoding="utf-8")
            with self.assertRaisesRegex(
                IndependentReviewError,
                "immutable kit tree is not closed",
            ):
                prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            self.assertEqual(extra.read_text(encoding="utf-8"), "preserve")

    def test_fsync_and_publication_failures_leave_no_partial_or_staging(self) -> None:
        for failure_kind in ("fsync", "publish"):
            with self.subTest(failure=failure_kind), tempfile.TemporaryDirectory() as temporary_directory:
                root = Path(temporary_directory)
                neutral_dir, _primary, _video, _protocol = prepare_inputs(root)
                if failure_kind == "fsync":
                    context = patch.object(
                        module.os,
                        "fsync",
                        side_effect=OSError("synthetic fsync failure"),
                    )
                else:
                    context = patch.object(
                        module,
                        "_publish_no_replace",
                        side_effect=IndependentReviewError(
                            "synthetic publication failure"
                        ),
                    )
                with context, self.assertRaises((OSError, IndependentReviewError)):
                    prepare_independent_review(neutral_dir, root, REVIEWER_ID)
                self.assertEqual(list(root.rglob(f".{REVIEWER_ID}.staging-*")), [])
                review_root = (
                    root
                    / "data"
                    / "outputs"
                    / "ball_tracking"
                    / "independent_review"
                    / "possession_001"
                    / "frames_0375_0399"
                    / REVIEWER_ID
                )
                self.assertFalse(review_root.exists())

    def test_target_appears_race_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, _primary, _video, _protocol = prepare_inputs(root)
            created_target = None
            original_atomic_publish = module._atomic_rename_no_replace

            def race_at_atomic_publish(_staging: Path, target: Path) -> None:
                nonlocal created_target
                target.mkdir()
                created_target = target
                original_atomic_publish(_staging, target)

            with patch.object(
                module,
                "_atomic_rename_no_replace",
                side_effect=race_at_atomic_publish,
            ):
                with self.assertRaisesRegex(
                    IndependentReviewError,
                    "appeared during publication",
                ):
                    prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            self.assertIsNotNone(created_target)
            self.assertEqual(list(created_target.iterdir()), [])
            self.assertEqual(list(root.rglob(f".{REVIEWER_ID}.staging-*")), [])

    def test_working_file_race_is_detected_without_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, _primary, _video, _protocol = prepare_inputs(root)
            result = prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            working_path = result.workspace_annotation_path
            original_read_bytes = Path.read_bytes
            raced = {"done": False}

            def racing_read(path: Path) -> bytes:
                content = original_read_bytes(path)
                if path == working_path and not raced["done"]:
                    raced["done"] = True
                    path.write_bytes(content + b"\n")
                return content

            with patch.object(Path, "read_bytes", racing_read):
                with self.assertRaisesRegex(
                    IndependentReviewError,
                    "changed during late rerun validation",
                ):
                    prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            self.assertTrue(raced["done"])
            self.assertTrue(original_read_bytes(working_path).endswith(b"\n\n"))

    def test_late_working_file_race_is_detected_without_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            neutral_dir, _primary, _video, _protocol = prepare_inputs(root)
            result = prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            original_ensure = module._ensure_external_inputs_unchanged
            original_bytes = result.workspace_annotation_path.read_bytes()

            def ensure_then_change(*args, **kwargs):
                original_ensure(*args, **kwargs)
                result.workspace_annotation_path.write_bytes(
                    original_bytes + b"\n"
                )

            with patch.object(
                module,
                "_ensure_external_inputs_unchanged",
                side_effect=ensure_then_change,
            ):
                with self.assertRaisesRegex(
                    IndependentReviewError,
                    "changed during late rerun validation",
                ):
                    prepare_independent_review(neutral_dir, root, REVIEWER_ID)
            self.assertEqual(
                result.workspace_annotation_path.read_bytes(),
                original_bytes + b"\n",
            )
