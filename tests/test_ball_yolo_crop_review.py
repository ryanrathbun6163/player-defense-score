"""Synthetic paired-detector review, immutable PNG reuse and complete videos."""
import copy
import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import cv2
import numpy as np

from src.ball_tracking import yolo_crop_review as review
from src.ball_tracking import crop_motion_review, crop_motion_evaluation, crop_motion_factorial
from src.ball_tracking.development_experiments import canonical_sha256, read_json, sha256_file
from src.ball_tracking.temporal_experiment import file_binding
from test_ball_annotation_foundation import not_visible_frame, observed_frame, parse_reviewed_annotations
from test_ball_temporal_association import fixture

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def one_frame(hidden=False):
    labels = parse_reviewed_annotations([not_visible_frame(0) if hidden else observed_frame(0)])
    _, run = fixture([[(100, 100, .8)]], labels)
    result = {"frame_index": 0, "annotation_status": "labeled", "visibility": "not_visible" if hidden else "fully_visible",
        "scoring_status": "not_visible_negative" if hidden else "localization_eligible", "input_detection_count": 1,
        "accepted_detection_count": 1, "matched_candidate_index": None if hidden else 0,
        "false_positive_count": int(hidden), "false_negative_count": 0, "duplicate_false_positive_count": 0,
        "non_visible_false_alarm_count": int(hidden), "unscored_prediction_count": 0,
        "matched_center_error_px": None if hidden else 0.0, "matched_effective_center_error_px": None if hidden else 0.0}
    observations, reports = {}, {}
    for arm in (*review.CONTROL_ARMS, *review.YOLO_ARMS):
        # Old IDs deliberately differ from the YOLO ID; old native pixels/report
        # must not be interpreted through the new detector's candidate objects.
        old = arm in review.CONTROL_ARMS
        observations[arm] = {"frame_index": 0, "emitted_candidate_indices": [7 if old else 0],
                             "decision_reason": "control_selection", "ranking": None}
        reports[arm] = {**result, "matched_candidate_index": None if hidden else 7 if old else 0}
    source = np.zeros((1080, 1920, 3), np.uint8)
    source[:, :, 0] = np.arange(1920, dtype=np.uint16)[None, :] % 211
    source[:, :, 1] = np.arange(1080, dtype=np.uint16)[:, None] % 197
    cv2.circle(source, (100, 100), 9, (20, 100, 220), -1)
    cv2.putText(source, "SYNTHETIC DETECTOR COMPARISON", (470, 300), cv2.FONT_HERSHEY_SIMPLEX,
                1.1, (180, 200, 220), 2)
    natives = {}
    for i, arm in enumerate(review.CONTROL_ARMS):
        body = source.copy()
        cv2.rectangle(body, (89, 89), (111, 111), (0, 255, 0), 2)
        cv2.putText(body, "#7 SAVED TP", (120, 100), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 255, 0), 1)
        natives[arm] = np.vstack((np.full((90, 1920, 3), i, np.uint8), body))
    return labels.annotation_by_frame()[0], run.frames[0], source, observations, reports, natives


def saved_fixture(root, *, window_count=6, frame_count=25):
    windows = [{"window_id": f"synthetic_window_{i}", "start_frame_index": 0, "end_frame_index": frame_count-1}
               for i in range(window_count)]
    all_old_arms = list(dict.fromkeys(c.arm for c in review.control_grid()))
    old = root / review.SAVED_PIXEL_ROOT / "synthetic_review"
    records, source_inventory = [], []
    for w in windows:
        for c in review.THRESHOLDS:
            for frame in range(frame_count):
                source = np.full((64, 96, 3), (frame, 37, 90), np.uint8)
                for arm, folder in [(a, f"view_{i}") for i, a in enumerate(all_old_arms)] + [("unmarked_source", "unmarked_source")]:
                    pixels = source if arm == "unmarked_source" else np.vstack((np.zeros((90, 96, 3), np.uint8), source))
                    path = old / w["window_id"] / f"confidence_{c}" / folder / f"frame_{frame:06d}.png"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    assert cv2.imwrite(str(path), pixels)
                    b = file_binding(root, path)
                    records.append({"window_id": w["window_id"], "confidence_threshold": c,
                                    "frame_index": frame, "arm": arm, **b})
                    if c == .2 and arm == "unmarked_source":
                        source_inventory.append({"window_id": w["window_id"], "frame_index": frame, "source_png": b})
    header = {"schema_version": "ball_crop_player_context_visual_review/v0.1", "windows": windows,
        "confidence_views": list(review.THRESHOLDS), "radius_px": 10.0, "reused_native_header_px": 90,
        "native_reused_arms": all_old_arms, "reused_assets": records,
        "selected_operating_point": None, "quality_gate": None}
    manifest = {"header": header, "assets": [], "frame_evidence": [], "human_visual_review": "pending",
                "final_frames": [{"window_id": w["window_id"], "frame_index": w["end_frame_index"]} for w in windows]}
    path = root / review.PRIOR_ROOT / "synthetic_review/manifest.json"
    write_json(path, manifest)
    return {"windows": windows, "reused_native_review_manifest": file_binding(root, path),
            "inference_source_frames": source_inventory}, manifest


def prepared_fixture(root, proposal):
    reused = review.load_reused_assets(root, proposal)
    header = {"windows": proposal["windows"], "reused_assets": reused, "input_bindings": [],
              "schema_version": "synthetic_review", "layout": review.LAYOUT}
    windows = []
    for w in proposal["windows"]:
        frames = [SimpleNamespace(frame_index=i) for i in range(w["start_frame_index"], w["end_frame_index"]+1)]
        run = SimpleNamespace(frames=frames, source_video=SimpleNamespace(width_px=96, height_px=64))
        observations, reports = {}, {}
        for c in review.THRESHOLDS:
            for arm in (*review.CONTROL_ARMS, *review.YOLO_ARMS):
                observations[arm, c] = {"frames": [{"frame_index": f.frame_index} for f in frames]}
                reports[arm, c] = {"frame_results": [{"frame_index": f.frame_index} for f in frames]}
        windows.append({"window": w, "run": run, "truth": {f.frame_index: None for f in frames},
                        "observations": observations, "reports": reports})
    return review.PreparedReview(header, windows, Mock())


def fast_frame(source, annotation, frame, observations, reports, native_controls, threshold):
    assert all(o["frame_index"] == frame.frame_index for o in observations.values())
    assert all(r["frame_index"] == frame.frame_index for r in reports.values())
    assert np.all(source[:, :, 0] == frame.frame_index)
    comparison = np.full((96, 96, 3), (frame.frame_index, 40, 90), np.uint8)
    native = np.vstack((np.zeros((90, 96, 3), np.uint8), source))
    return comparison, [native.copy() for _ in range(3)], source.copy(), [
        {"control_arm": a, "challenger_arm": b} for a, b in zip(review.CONTROL_ARMS, review.YOLO_ARMS)]


class YoloReviewFrameTests(unittest.TestCase):
    def test_independent_detector_ids_three_new_overlays_and_unmodified_old_pixels(self):
        from src.ball_tracking import prepare_detection_visual_review as helper
        annotation, frame, source, observations, reports, natives = one_frame()
        before, original = {k: v.copy() for k, v in natives.items()}, source.copy()
        with patch.object(helper, "render_detection_overlay", wraps=helper.render_detection_overlay) as overlay, \
                patch.object(helper, "_put_fitted_text", wraps=helper._put_fitted_text) as text:
            comparison, new, closeups, focuses = review.render_frame(source, annotation, frame, observations, reports, natives, .2)
        self.assertEqual(overlay.call_count, 3)
        self.assertEqual(sum(c.args[1] == "EXPORTED 1 | >= CONF 1 | EMITTED 1" for c in text.call_args_list), 3)
        self.assertEqual(comparison.shape, (1566, 2400, 3))
        self.assertEqual(len(new), 3)
        self.assertTrue(all(p.shape[0] == 1170 and p.shape[1] >= 1920 for p in new))
        self.assertTrue(np.array_equal(source, original))
        self.assertTrue(all(np.array_equal(natives[k], v) for k, v in before.items()))
        self.assertEqual(len(focuses), 3)
        self.assertTrue(all(f["raw_unmarked_view_included"] for f in focuses))
        self.assertEqual(len({tuple(f["requested_source_crop_xyxy_px"]) for f in focuses}), 1)
        # Independent crop pixel check: no overlay may touch the raw column.
        x1, y1, x2, y2 = focuses[0]["requested_source_crop_xyxy_px"]
        expected = np.repeat(np.repeat(original[y1:y2, x1:x2], 4, axis=0), 4, axis=1)
        actual = closeups[helper.ZOOM_PANEL_HEADER_PX:helper.ZOOM_PANEL_HEIGHT_PX, :expected.shape[1]]
        self.assertTrue(np.array_equal(actual[1:-1, 1:-1], expected[1:-1, 1:-1]))
        target = ROOT / "data/outputs/ball_tracking/yolo_crop_implementation_validation"
        target.mkdir(parents=True, exist_ok=True)
        for name, pixels in (("comparison", comparison), ("closeups", closeups), ("native", new[0])):
            self.assertTrue(cv2.imwrite(str(target / f"synthetic_v2_{name}.png"), pixels))

    def test_hidden_focus_is_not_truth_and_frame_misalignment_rejected(self):
        annotation, frame, source, observations, reports, natives = one_frame(True)
        args = (source, annotation, frame, observations, reports, natives)
        result = review.render_frame(*args, .35)
        self.assertTrue(all(f["focus_type"] == "top_accepted_candidate_no_truth" for f in result[3]))
        self.assertTrue(all("YOLO" in f["candidate_focus_source"] for f in result[3]))
        for target in (3, 4):
            changed = list(copy.deepcopy(args))
            changed[target][review.YOLO_ARMS[0]]["frame_index"] = 1
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "Unsynchronized"):
                review.render_frame(*changed, .2)
        changed = list(args)
        changed[5] = {**args[5], review.CONTROL_ARMS[0]: args[0]}
        with self.assertRaisesRegex(ValueError, "dimensions"):
            review.render_frame(*changed, .2)


class YoloReviewAssetTests(unittest.TestCase):
    def test_saved_inventory_exact_keys_final_frames_source_identity_and_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proposal, original = saved_fixture(root, window_count=1, frame_count=2)
            self.assertEqual(len(review.load_reused_assets(root, proposal)), 16)
            path = root / proposal["reused_native_review_manifest"]["path"]
            for scenario in ("config", "final", "duplicate", "missing", "misbound_path"):
                changed = copy.deepcopy(original)
                if scenario == "config": changed["header"]["native_reused_arms"].reverse()
                elif scenario == "final": changed["final_frames"][0]["frame_index"] = 0
                elif scenario == "duplicate": changed["header"]["reused_assets"].append(changed["header"]["reused_assets"][0])
                elif scenario == "missing": changed["header"]["reused_assets"].pop()
                else: changed["header"]["reused_assets"][0]["path"] = changed["header"]["reused_assets"][8]["path"]
                write_json(path, changed)
                proposal["reused_native_review_manifest"] = file_binding(root, path)
                with self.subTest(scenario=scenario), self.assertRaises(ValueError): review.load_reused_assets(root, proposal)
            write_json(path, original)
            proposal["reused_native_review_manifest"] = file_binding(root, path)
            altered = copy.deepcopy(proposal)
            altered["inference_source_frames"][0]["source_png"] = altered["inference_source_frames"][1]["source_png"]
            with self.assertRaisesRegex(ValueError, "pixels differ"): review.load_reused_assets(root, altered)
            (root / original["header"]["reused_assets"][0]["path"]).write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "binding mismatch"): review.load_reused_assets(root, proposal)

    def test_read_png_hashes_the_actual_decoded_bytes_and_never_uses_imread(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proposal, _ = saved_fixture(root, window_count=1, frame_count=1)
            record = proposal["inference_source_frames"][0]["source_png"]
            with patch.object(cv2, "imread", side_effect=AssertionError("two-read race")):
                self.assertEqual(review._read_png(root, record).shape, (64, 96, 3))
            path = root / record["path"]
            path.write_bytes(b"changed after earlier validation")
            with patch.object(cv2, "imdecode", side_effect=AssertionError("must hash before decode")):
                with self.assertRaisesRegex(ValueError, "bytes changed"): review._read_png(root, record)

    def test_report_binds_independent_config_complete_observation_digest_and_frames(self):
        _, run = fixture([[(100, 100, .8)]])
        config = review.control_grid()[0]
        obs = {"frames": [{"frame_index": 0}], "audit": "original"}
        report = {"possession_id": run.possession_id, "variant_id": config.variant_id,
            "localization_radius_px": 10.0, "config": asdict(config), "source_video": run.source_video.to_dict(),
            "window": run.window.to_dict(), "observations_content_sha256": canonical_sha256(obs), "frame_results": [{"frame_index": 0}]}
        self.assertEqual(review._report({"evaluation_reports": [report]}, run, config, obs), report)
        for scenario in ("digest", "frame", "config"):
            changed = copy.deepcopy(report)
            if scenario == "digest": changed["observations_content_sha256"] = "0"*64
            elif scenario == "frame": changed["frame_results"][0]["frame_index"] = 1
            else: changed["config"]["confidence_threshold"] = .7
            with self.subTest(scenario=scenario), self.assertRaisesRegex(ValueError, "provenance"):
                review._report({"evaluation_reports": [changed]}, run, config, obs)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            review._report({"evaluation_reports": [report, report]}, run, config, obs)

    def test_complete_atomic_bundle_resume_corruption_and_no_old_pipeline_or_source_video(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proposal, _ = saved_fixture(root)
            prepared = prepared_fixture(root, proposal)
            before = {r["path"]: sha256_file(root / r["path"]) for r in prepared.header["reused_assets"]}
            original_capture, original_write = cv2.VideoCapture, cv2.imwrite
            decoded, writes = [], 0
            def capture(path):
                self.assertEqual(Path(path).name, "comparison_slow.mp4")
                self.assertIn(".pending_review_", str(path))
                self.assertTrue(Path(path).is_relative_to(root / review.OUTPUT_ROOT))
                decoded.append(path)
                return original_capture(path)
            def interrupted(path, pixels):
                nonlocal writes
                writes += 1
                if writes == 9: raise RuntimeError("synthetic interruption")
                return original_write(path, pixels)
            with patch.object(review, "_prepare_review", return_value=prepared), \
                    patch.object(review, "render_frame", side_effect=fast_frame), \
                    patch.object(review, "TILE_WIDTH", 32), patch.object(review, "TILE_HEIGHT", 32), \
                    patch.object(cv2, "VideoCapture", side_effect=capture), \
                    patch.object(crop_motion_review, "render_experiment", side_effect=AssertionError("old renderer")), \
                    patch.object(crop_motion_evaluation, "score_experiment", side_effect=AssertionError("old scorer")), \
                    patch.object(crop_motion_factorial, "rank_candidates", side_effect=AssertionError("old selector")):
                with patch.object(cv2, "imwrite", side_effect=interrupted), self.assertRaisesRegex(RuntimeError, "interruption"):
                    review.render_experiment(root, root / "synthetic_manifest.json")
                parent = root / review.OUTPUT_ROOT / "review"
                self.assertFalse(list(parent.iterdir()))
                result = review.render_experiment(root, root / "synthetic_manifest.json")
                self.assertEqual(result["assets"], 1512)
                self.assertEqual(result["reused_native_assets"], 1200)
                self.assertEqual(len(decoded), 12)
                bundle = Path(result["bundle"])
                manifest = read_json(bundle / "manifest.json")
                self.assertEqual(len(manifest["frame_evidence"]), 300)
                self.assertEqual(len(manifest["final_frames"]), 6)
                self.assertTrue(review.render_experiment(root, root / "synthetic_manifest.json")["reused"])
                self.assertEqual(len(decoded), 12, "Resume must not rerender or decode clips")
                self.assertEqual(before, {p: sha256_file(root/p) for p in before})
                for scenario in ("source", "pair"):
                    changed = copy.deepcopy(manifest)
                    if scenario == "source": changed["frame_evidence"][0]["source_png"] = changed["frame_evidence"][1]["source_png"]
                    else: changed["frame_evidence"][0]["closeup_regions"][0]["challenger_arm"] = review.YOLO_ARMS[1]
                    write_json(bundle/"manifest.json", changed)
                    with self.subTest(scenario=scenario), self.assertRaises(ValueError): review.render_experiment(root, root/"synthetic_manifest.json")
                write_json(bundle/"manifest.json", manifest)
                last = bundle/"synthetic_window_5/confidence_0.35/yolo_view_2/frame_000024.png"
                data = last.read_bytes()
                last.unlink()
                with self.assertRaisesRegex(ValueError, "final frames"): review.validate_review_bundle(root, bundle, prepared.header)
                last.write_bytes(b"corrupt new native")
                with self.assertRaisesRegex(ValueError, "asset hash"): review.validate_review_bundle(root, bundle, prepared.header)
                last.write_bytes(data)
                (root/prepared.header["reused_assets"][0]["path"]).write_bytes(b"changed reused native")
                with self.assertRaisesRegex(ValueError, "binding mismatch"): review.render_experiment(root, root/"synthetic_manifest.json")

    def test_input_change_before_publish_leaves_no_completed_bundle(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proposal, _ = saved_fixture(root, window_count=1)
            prepared = prepared_fixture(root, proposal)
            prepared.verify.side_effect = ValueError("input changed during rendering")
            with patch.object(review, "_prepare_review", return_value=prepared), \
                    patch.object(review, "render_frame", side_effect=fast_frame), \
                    patch.object(review, "TILE_WIDTH", 32), patch.object(review, "TILE_HEIGHT", 32):
                with self.assertRaisesRegex(ValueError, "input changed"):
                    review.render_experiment(root, root/"synthetic_manifest.json")
            self.assertFalse(list((root/review.OUTPUT_ROOT/"review").iterdir()))


if __name__ == "__main__":
    unittest.main()
