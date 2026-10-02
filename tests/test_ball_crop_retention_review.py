"""Synthetic saved-PNG review; no real candidates, footage or model calls."""
import copy
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import cv2
import numpy as np

from src.ball_tracking import crop_retention_review as review
from src.ball_tracking.annotations import BallAnnotationSet
from src.ball_tracking.development_experiments import canonical_sha256, read_json, sha256_file
from test_ball_annotation_foundation import (
    detection, not_visible_frame, observed_frame, parse_detection_run, parse_reviewed_annotations,
)

COMMIT = "c" * 40
ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def fixtures(frame_count=1, hidden=False):
    labels = parse_reviewed_annotations(
        [not_visible_frame(i) if hidden else observed_frame(i, center=(32, 30)) for i in range(frame_count)],
        width_px=160, height_px=90)
    payload = labels.to_dict()
    payload["window"]["selection_purpose"] = "representative_evaluation"
    labels = BallAnnotationSet.from_mapping(payload)
    run = parse_detection_run(labels, {i: [detection(32, 30, .35), detection(110, 55, .02)]
                                       for i in range(frame_count)})
    observations, reports = {}, {}
    for arm, policy in review.VIEW_KEYS:
        graph = arm in review.ARMS
        cap = None if policy == "all" or arm == "crop_raw" else 20
        steps = review.STEPS[review.ARMS.index(arm)] if graph else (None, None)
        config = {"arm": arm, "confidence_threshold": .01, "candidate_cap": cap,
                  "edge_step": steps[0], "cost_step": steps[1]}
        if policy == "all":
            config["retention_policy"] = "all_threshold_qualified_saved_candidates"
        frames, frame_results = [], []
        for frame in run.frames:
            index = frame.frame_index
            emitted = [1] if policy == "all" else [0] if graph else [0, 1]
            winner = {"endpoint": [index, emitted[0]], "score": .35 if policy != "all" else .4,
                      "path": [[index, emitted[0]]], "endpoint_confidence": .35 if policy != "all" else .02,
                      "trailing_skipped_frames": 0}
            ranking = {"winner": winner, "score_margin": .01, "current_alternatives": []} if graph else None
            frames.append({"frame_index": index, "emitted_candidate_indices": emitted,
                           "ranking": ranking, "decision_reason": "current_endpoint" if graph else "control_selection"})
            matched = 0 if 0 in emitted and not hidden else None
            count = len(emitted)
            frame_results.append({"frame_index": index, "annotation_status": "labeled",
                "visibility": "not_visible" if hidden else "fully_visible",
                "scoring_status": "not_visible_negative" if hidden else "localization_eligible",
                "input_detection_count": count, "accepted_detection_count": count,
                "matched_candidate_index": matched, "false_positive_count": count-int(matched is not None),
                "false_negative_count": int(not hidden and matched is None),
                "duplicate_false_positive_count": 0, "non_visible_false_alarm_count": count if hidden else 0,
                "unscored_prediction_count": 0, "matched_center_error_px": 0.0 if matched is not None else None,
                "matched_effective_center_error_px": 0.0 if matched is not None else None})
        observation = {"config": config, "frames": frames, "ranking_code_commit": COMMIT,
                       "detector_code_commit": run.model_provenance.code_commit}
        observations[arm, policy] = observation
        reports[arm, policy] = {"config": config, "localization_radius_px": 10.0,
            "source_video": run.source_video.to_dict(), "window": run.window.to_dict(),
            "possession_id": run.possession_id, "frame_results": frame_results,
            "observations_content_sha256": canonical_sha256(observation),
            "input_candidate_content_sha256": canonical_sha256(run.to_dict()),
            "annotation_content_sha256": canonical_sha256(labels.to_dict())}
    source = np.zeros((90, 160, 3), np.uint8)
    source[:, :, 0] = np.arange(160, dtype=np.uint8)
    source[:, :, 1] = np.arange(90, dtype=np.uint8)[:, None]
    cv2.circle(source, (32, 30), 5, (20, 100, 220), -1)
    return labels, run, observations, reports, source


def context_fixture(root):
    labels, run, observations, reports, source = fixtures(25)
    window_id = "synthetic_development_window"
    prior = root / "data/outputs/synthetic_review_inputs"
    annotation_path = root / "configs/ball_tracking/annotations/synthetic.json"
    write_json(annotation_path, labels.to_dict())
    candidate_path = prior / "candidates.json"
    write_json(candidate_path, {"synthetic": True})
    window = {"window_id": window_id, "purpose": "representative_evaluation", "possession_id": run.possession_id,
              "annotation_set_id": labels.annotation_set_id, "start_frame_index": 0, "end_frame_index": 24,
              "source_video": run.source_video.to_dict(), "crop_candidates": review._binding(root, candidate_path)}
    records, units = [], []
    saved_by_path, new_by_id = {}, {}
    for key, observation in observations.items():
        arm, policy = key
        if policy == "all":
            unit = {"window_id": window_id, "config": observation["config"], "comparison_unit_id": arm + "_all"}
            units.append(unit)
            new_by_id[unit["comparison_unit_id"]] = observation
        else:
            path = prior / f"{arm}.json"
            write_json(path, observation)
            record = {"window_id": window_id, "config": observation["config"], "file": review._binding(root, path)}
            records.append(record)
            saved_by_path[record["file"]["path"]] = observation
    assets, pngs = [], []
    for i in range(25):
        relative = f"source/frame_{i:06d}.png"
        target = prior / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(target), source)
        assets.append({"path": relative, "sha256": sha256_file(target)})
        pngs.append({"window_id": window_id, "frame_index": i,
                     "source_png": review._binding(root, target), "manifest_asset_relative_path": relative})
    manifest = prior / "manifest.json"
    write_json(manifest, {"assets": assets})
    for png in pngs:
        png["original_manifest"] = review._binding(root, manifest)
    scoring_path = root / review.OUTPUT_ROOT / "evaluation/windows" / f"{window_id}.json"
    score = {"evaluation_reports": list(reports.values())}
    write_json(scoring_path, score)
    context = {"proposal": {"windows": [window], "saved_control_outputs": records, "new_selection_units": units,
                 "scoring_labels": [{"window_id": window_id, "annotation": review._binding(root, annotation_path)}],
                 "saved_source_pngs": pngs}, "commit": COMMIT, "spec_sha256": "a"*64,
               "inputs": {window_id: (run, "b"*64)}}
    experiment_module = SimpleNamespace(
        load_saved_control=Mock(side_effect=lambda root, record, run=None: copy.deepcopy(saved_by_path[record["file"]["path"]])),
        load_new_observations=Mock(side_effect=lambda root, context, unit: copy.deepcopy(new_by_id[unit["comparison_unit_id"]])))
    evaluation_module = SimpleNamespace(load_window_score=Mock(return_value=score))
    return context, experiment_module, evaluation_module, labels, run, observations, reports, source


def fast_frame(source, annotation, frame, observations, reports):
    comparison = np.full((review.TILE_HEIGHT*4, review.TILE_WIDTH*3, 3), (frame.frame_index, 45, 120), np.uint8)
    native = {key: source.copy() for key in review.VIEW_KEYS}
    return comparison, native, source.copy(), [{"arm": arm, "raw_unmarked_view_included": True} for arm in review.ARMS]


class RetentionReviewFrameTests(unittest.TestCase):
    def test_pairs_references_and_source_faithful_closeups_preserve_source(self):
        labels, run, observations, reports, source = fixtures()
        before = source.copy()
        rendered = review.render_frame(source, labels.annotation_by_frame()[0], run.frames[0],
            {key: value["frames"][0] for key, value in observations.items()},
            {key: value["frame_results"][0] for key, value in reports.items()})
        comparison, native, closeups, focuses = rendered
        self.assertEqual(comparison.shape, (review.TILE_HEIGHT*4, review.TILE_WIDTH*3, 3))
        self.assertEqual(set(native), set(review.VIEW_KEYS))
        self.assertEqual(len(native), 10)
        self.assertTrue(np.array_equal(source, before))
        self.assertEqual(len(focuses), 4)
        self.assertTrue(all(f["raw_unmarked_view_included"] for f in focuses))
        self.assertTrue(all(f["focus_type"] == "reviewed_truth_center" for f in focuses))
        self.assertEqual(len({tuple(f["requested_source_crop_xyxy_px"]) for f in focuses}), 1)
        detail = review._details(run.frames[0], observations[review.ARMS[0], "all"]["frames"][0])[0]
        self.assertIn("conf 0.020000", detail)
        self.assertIn("path score 0.400000", detail)
        self.assertIn("margin 0.010000", detail)
        preview = ROOT / "data/outputs/ball_tracking/crop_retention_implementation_validation"
        preview.mkdir(parents=True, exist_ok=True)
        self.assertTrue(cv2.imwrite(str(preview / "synthetic_review_comparison.png"), comparison))
        self.assertTrue(cv2.imwrite(str(preview / "synthetic_review_closeups.png"), closeups))

    def test_hidden_focus_and_missing_observation_never_invent_truth(self):
        labels, run, observations, reports, source = fixtures(hidden=True)
        key = review.ARMS[0], "all"
        obs = observations[key]["frames"][0]
        obs["emitted_candidate_indices"] = []
        obs["decision_reason"] = "empty_hypothesis"
        obs["ranking"]["winner"] = {"endpoint": None, "score": 0.0, "path": []}
        result = reports[key]["frame_results"][0]
        for name in ("input_detection_count", "accepted_detection_count", "false_positive_count", "non_visible_false_alarm_count"):
            result[name] = 0
        rendered = review.render_frame(source, labels.annotation_by_frame()[0], run.frames[0],
            {key: value["frames"][0] for key, value in observations.items()},
            {key: value["frame_results"][0] for key, value in reports.items()})
        self.assertTrue(all(f["focus_type"] == "top_accepted_candidate_no_truth" for f in rendered[3]))
        self.assertIn("NULL", review._details(run.frames[0], obs)[0])
        self.assertIsNone(labels.annotation_by_frame()[0].geometry)

    def test_frame_sync_emission_original_indices_and_alternatives_fail_closed(self):
        labels, run, observations, reports, source = fixtures()
        rows = {key: value["frames"][0] for key, value in observations.items()}
        results = {key: value["frame_results"][0] for key, value in reports.items()}
        for change in ("frame", "unknown_candidate", "multiple_graph_emissions", "alternative"):
            changed = copy.deepcopy(rows)
            row = changed[review.ARMS[0], "all"]
            if change == "frame":
                row["frame_index"] = 8
            elif change == "unknown_candidate":
                row["emitted_candidate_indices"] = [99]
            elif change == "multiple_graph_emissions":
                row["emitted_candidate_indices"] = [0, 1]
            else:
                row["ranking"]["current_alternatives"] = [{"endpoint": [2, 1]}]
            with self.subTest(change=change), self.assertRaises(ValueError):
                review.render_frame(source, labels.annotation_by_frame()[0], run.frames[0], changed, results)
        noncontiguous = replace(run.frames[0], detections=tuple(replace(d, candidate_index=d.candidate_index+30)
                                                               for d in run.frames[0].detections))
        self.assertEqual(review._selected(noncontiguous, {"emitted_candidate_indices": [31]}).detections[0].candidate_index, 31)


class RetentionReviewPreparationTests(unittest.TestCase):
    def _modules(self, experiment, evaluation):
        return patch.dict(sys.modules, {"src.ball_tracking.crop_retention_experiment": experiment,
                                      "src.ball_tracking.crop_retention_evaluation": evaluation})

    def test_preparation_binds_saved_reports_sources_and_only_loads_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            context, experiment, evaluation, *_ = context_fixture(root)
            with self._modules(experiment, evaluation):
                prepared = review.prepare_window(root, context, "synthetic_development_window")
            self.assertEqual(len(prepared.sources), 25)
            self.assertEqual(len(prepared.observations), 10)
            self.assertEqual(prepared.header["renderer_code_commit"], COMMIT)
            self.assertEqual(len(prepared.header["observation_sources"]), 10)
            self.assertEqual(evaluation.load_window_score.call_count, 1)
            self.assertEqual(experiment.load_saved_control.call_count, 12)
            self.assertEqual(experiment.load_new_observations.call_count, 8)
            self.assertEqual(prepared.header["prior_motion_and_yolo_review"], "complete; no repeat requested")

    def test_missing_score_fails_without_loader_or_implicit_scoring(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            context, experiment, evaluation, *_ = context_fixture(root)
            path = root / review.OUTPUT_ROOT / "evaluation/windows/synthetic_development_window.json"
            path.unlink()
            with self._modules(experiment, evaluation), self.assertRaisesRegex(ValueError, "requires completed"):
                review.prepare_window(root, context, "synthetic_development_window")
            evaluation.load_window_score.assert_not_called()
            experiment.load_new_observations.assert_not_called()

    def test_mismatched_score_annotation_candidate_source_and_duplicate_png_fail(self):
        for mismatch in ("score", "annotation", "candidate", "source_manifest", "duplicate_png"):
            with self.subTest(mismatch=mismatch), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                context, experiment, evaluation, *_ = context_fixture(root)
                if mismatch == "score":
                    evaluation.load_window_score.return_value["evaluation_reports"][0]["observations_content_sha256"] = "f"*64
                elif mismatch == "annotation":
                    context["proposal"]["windows"][0]["annotation_set_id"] = "wrong"
                elif mismatch == "candidate":
                    evaluation.load_window_score.return_value["evaluation_reports"][0]["input_candidate_content_sha256"] = "f"*64
                elif mismatch == "source_manifest":
                    context["proposal"]["saved_source_pngs"][0]["manifest_asset_relative_path"] = "source/frame_000002.png"
                    context["proposal"]["saved_source_pngs"][0]["source_png"]["path"] = "data/outputs/synthetic_review_inputs/wrong.png"
                else:
                    context["proposal"]["saved_source_pngs"].append(context["proposal"]["saved_source_pngs"][0])
                with self._modules(experiment, evaluation), self.assertRaises(ValueError):
                    review.prepare_window(root, context, "synthetic_development_window")

    def test_png_same_buffer_digest_suffix_decode_and_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "source.png"
            pixels = np.full((8, 12, 3), 72, np.uint8)
            cv2.imwrite(str(path), pixels)
            binding = review._binding(root, path)
            self.assertTrue(np.array_equal(review._read_png(root, binding), pixels))
            path.write_bytes(b"broken")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                review._read_png(root, binding)
            with self.assertRaisesRegex(ValueError, "decode"):
                review._read_png(root, review._binding(root, path))
            with self.assertRaisesRegex(ValueError, "only bound PNG"):
                review._read_png(root, {"path": "source.mp4", "sha256": "a"*64})


class RetentionReviewBundleTests(unittest.TestCase):
    def test_six_complete_clips_final_pngs_resume_and_tamper_guard(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            context, experiment, evaluation, *_ = context_fixture(root)
            with patch.dict(sys.modules, {"src.ball_tracking.crop_retention_experiment": experiment,
                                          "src.ball_tracking.crop_retention_evaluation": evaluation}):
                prepared = review.prepare_window(root, context, "synthetic_development_window")
            windows = []
            with patch.object(review, "TILE_WIDTH", 96), patch.object(review, "TILE_HEIGHT", 64), \
                    patch.object(review, "render_frame", side_effect=fast_frame) as render:
                for i in range(6):
                    item = copy.copy(prepared)
                    item.header = copy.deepcopy(prepared.header)
                    item.window = {**prepared.window, "window_id": f"synthetic_window_{i}"}
                    item.header["window"] = item.window
                    windows.append(item.window)
                    target = root / review.OUTPUT_ROOT / "review/windows" / item.window["window_id"]
                    completed = review.render_prepared_window(root, item, target)
                    self.assertFalse(completed["reused"])
                    self.assertEqual(completed["assets"], 301)
                    manifest = read_json(target / "manifest.json")
                    self.assertEqual(manifest["video_verification"]["decoded_frames"], 25)
                    self.assertEqual(manifest["video_verification"]["fps"], 5.0)
                    self.assertEqual(manifest["final_frame"], 24)
                    self.assertEqual(len(manifest["final_png_verification"]), 12)
                    for folder in ("comparison", "closeups", *(f"view_{j}" for j in range(10))):
                        self.assertTrue((target / folder / "frame_000024.png").is_file())
                    calls = render.call_count
                    self.assertTrue(review.render_prepared_window(root, item, target)["reused"])
                    self.assertEqual(render.call_count, calls)
                self.assertEqual(render.call_count, 150)
                summary_context = {**context, "proposal": {"windows": windows}}
                final = review.finalize_review(root, summary_context)
                self.assertEqual(final["windows"], 6)
                self.assertEqual(review.finalize_review(root, summary_context), final)
                (target / "comparison/frame_000024.png").write_bytes(b"tamper")
                with self.assertRaisesRegex(ValueError, "binding mismatch"):
                    review.validate_review_bundle(root, target, item.header)

    def test_final_png_decoder_checks_dimensions_and_complete_panel_set(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = []
            for folder in ("comparison", "closeups", *(f"view_{i}" for i in range(10))):
                path = root / folder / "frame_000024.png"
                path.parent.mkdir()
                cv2.imwrite(str(path), np.zeros((8, 12, 3), np.uint8))
                assets.append({**review._binding(root, path), "width_px": 12, "height_px": 8})
            self.assertEqual(len(review._verify_final_pngs(root, assets, 24)), 12)
            with self.assertRaisesRegex(ValueError, "Missing final"):
                review._verify_final_pngs(root, assets[:-1], 24)
            assets[0]["height_px"] = 9
            with self.assertRaisesRegex(ValueError, "dimensions"):
                review._verify_final_pngs(root, assets, 24)

    def test_failure_retains_staging_receipt_without_publishing_completed_unit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            context, experiment, evaluation, *_ = context_fixture(root)
            with patch.dict(sys.modules, {"src.ball_tracking.crop_retention_experiment": experiment,
                                          "src.ball_tracking.crop_retention_evaluation": evaluation}):
                prepared = review.prepare_window(root, context, "synthetic_development_window")
            target = root / review.OUTPUT_ROOT / "review/windows" / "synthetic_development_window"
            with patch.object(review, "render_frame", side_effect=ValueError("synthetic abort")), \
                    self.assertRaisesRegex(ValueError, "synthetic abort"):
                review.render_prepared_window(root, prepared, target)
            self.assertFalse(target.exists())
            failures = list(target.parent.glob(".pending_*/failure.json"))
            self.assertEqual(len(failures), 1)
            self.assertEqual(read_json(failures[0])["status"], "incomplete")

    def test_source_change_on_resume_and_output_outside_scope_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            context, experiment, evaluation, *_ = context_fixture(root)
            with patch.dict(sys.modules, {"src.ball_tracking.crop_retention_experiment": experiment,
                                          "src.ball_tracking.crop_retention_evaluation": evaluation}):
                prepared = review.prepare_window(root, context, "synthetic_development_window")
            with self.assertRaises(ValueError):
                review.render_prepared_window(root, prepared, root / "unapproved_output")
            (root / prepared.sources[0]["path"]).write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "binding mismatch"):
                review.render_prepared_window(root, prepared, root / review.OUTPUT_ROOT / "review/windows/synthetic")

    def test_clip_validation_rejects_missing_frames_wrong_fps_and_dimensions(self):
        class Capture:
            def __init__(self, frames, fps, shape):
                self.remaining, self.fps, self.shape = frames, fps, shape
            def isOpened(self):
                return True
            def get(self, prop):
                return self.fps
            def read(self):
                self.remaining -= 1
                return (True, np.zeros(self.shape, np.uint8)) if self.remaining >= 0 else (False, None)
            def release(self):
                pass
        for frames, fps, shape in ((24, 5, (8, 12, 3)), (25, 6, (8, 12, 3)), (25, 5, (9, 12, 3))):
            with self.subTest(frames=frames, fps=fps, shape=shape), patch.object(review, "TILE_HEIGHT", 2), \
                    patch.object(review, "TILE_WIDTH", 4), patch.object(cv2, "VideoCapture", return_value=Capture(frames, fps, shape)), \
                    self.assertRaises(ValueError):
                review._verify_video(Path("synthetic-new-output.mp4"), 0, 24)


if __name__ == "__main__":
    unittest.main()
