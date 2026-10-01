"""Synthetic saved-PNG reuse, paired rendering, provenance and atomic resume."""
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

from src.ball_tracking import crop_player_context_review as review
from src.ball_tracking import crop_motion_evaluation, crop_motion_factorial, crop_motion_review
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
    result = {"frame_index": 0, "annotation_status": "labeled",
              "visibility": "not_visible" if hidden else "fully_visible",
              "scoring_status": "not_visible_negative" if hidden else "localization_eligible",
              "input_detection_count": 1, "accepted_detection_count": 1,
              "matched_candidate_index": None if hidden else 0,
              "false_positive_count": int(hidden), "false_negative_count": 0,
              "duplicate_false_positive_count": 0, "non_visible_false_alarm_count": int(hidden),
              "unscored_prediction_count": 0, "matched_center_error_px": None if hidden else 0.0,
              "matched_effective_center_error_px": None if hidden else 0.0}
    observations, reports = {}, {}
    for arm in (*review.CONTROL_ARMS, *review.CONTEXT_ARMS):
        context = arm in review.CONTEXT_ARMS
        history = {"winner": {"endpoint": [0, 0], "score": .73 if context else .8,
                              "path": [[0, 0]], "endpoint_confidence": .8,
                              "trailing_skipped_frames": 0},
                   "node_context": [{"reference": [0, 0], "context_cost": .07}]}
        observations[arm] = {"frame_index": 0, "emitted_candidate_indices": [0],
                             "decision_reason": "current_endpoint", "ranking": history,
                             "context_available_box_count": 1, "context_unavailable": False}
        if arm in review.CONTROL_ARMS[:3]:
            observations[arm]["ranking"] = None
        reports[arm] = copy.deepcopy(result)
    source = np.zeros((1080, 1920, 3), dtype=np.uint8)
    source[:, :, 0] = np.arange(1920, dtype=np.uint16)[None, :] % 211
    source[:, :, 1] = np.arange(1080, dtype=np.uint16)[:, None] % 197
    cv2.circle(source, (100, 100), 9, (20, 100, 220), -1)
    cv2.putText(source, "SYNTHETIC: SAVED SOURCE PIXELS", (500, 300),
                cv2.FONT_HERSHEY_SIMPLEX, 1.1, (160, 180, 220), 2)
    natives = {}
    for i, arm in enumerate(review.CONTROL_ARMS):
        body = source.copy()
        body[20:30, 20:30] = (20*i, 20, 240)
        natives[arm] = np.vstack((np.full((90, 1920, 3), i, np.uint8), body))
    rows = [{"frame_index": 0, "player_id": "synthetic_player", "track_id": 1,
             "x1": 135.0, "y1": 100.0, "x2": 235.0, "y2": 190.0}]
    return labels.annotation_by_frame()[0], run.frames[0], source, observations, reports, natives, rows


def saved_fixture(root, *, window_count=6, frame_count=25):
    windows = [{"window_id": f"synthetic_window_{i}", "start_frame_index": 0,
                "end_frame_index": frame_count-1} for i in range(window_count)]
    old = root / review.PRIOR_ROOT / "synthetic_review"
    assets = []
    for w in windows:
        for threshold in review.THRESHOLDS:
            for frame in range(frame_count):
                source = np.full((64, 96, 3), (frame, 37, 90), np.uint8)
                for folder in ["unmarked_source", *(f"view_{i}" for i in range(7))]:
                    pixels = source if folder == "unmarked_source" else np.vstack((np.zeros((90, 96, 3), np.uint8), source))
                    key = f"{w['window_id']}/confidence_{threshold}/{folder}/frame_{frame:06d}.png"
                    target = old / key
                    target.parent.mkdir(parents=True, exist_ok=True)
                    assert cv2.imwrite(str(target), pixels)
                    assets.append({"path": key, "sha256": sha256_file(target)})
    header = {"schema_version": "ball_crop_motion_factorial_visual_review/v0.1", "windows": windows,
              "confidence_views": list(review.THRESHOLDS), "radius_px": 10.0,
              "view_configs": [asdict(c) for c in review.control_grid() if c.confidence_threshold in review.THRESHOLDS],
              "panels": [*review.CONTROL_ARMS, "unmarked_source", "legend"],
              "selected_operating_point": None, "quality_gate": None, "native_unmarked_source_pngs": True}
    manifest = {"header": header, "assets": assets,
                "final_frames": [{"window_id": w["window_id"], "frame_index": w["end_frame_index"]} for w in windows],
                "human_visual_review": "pending"}
    path = old / "manifest.json"
    write_json(path, manifest)
    return {"windows": windows, "prior_review_manifest": file_binding(root, path)}, manifest


def prepared_fixture(root, proposal):
    reused = review.load_reused_assets(root, proposal)
    header = {"windows": proposal["windows"], "reused_assets": reused, "input_bindings": [],
              "schema_version": "synthetic_review", "layout": review.LAYOUT}
    windows = []
    for w in proposal["windows"]:
        frames = [SimpleNamespace(frame_index=i) for i in range(w["start_frame_index"], w["end_frame_index"]+1)]
        run = SimpleNamespace(frames=frames, source_video=SimpleNamespace(width_px=96, height_px=64))
        observations, reports = {}, {}
        for threshold in review.THRESHOLDS:
            for arm in (*review.CONTROL_ARMS, *review.CONTEXT_ARMS):
                observations[arm, threshold] = {"frames": [{"frame_index": f.frame_index} for f in frames]}
                reports[arm, threshold] = {"frame_results": [{"frame_index": f.frame_index} for f in frames]}
        windows.append({"window": w, "run": run, "truth": {f.frame_index: None for f in frames},
                        "player_rows": {f.frame_index: [] for f in frames},
                        "observations": observations, "reports": reports})
    return review.PreparedReview(header, windows, Mock())


def fast_frame(source, annotation, frame, observations, reports, native_controls, player_rows, threshold):
    comparison = np.full((128, 96, 3), (frame.frame_index, 40, 90), np.uint8)
    native = np.vstack((np.zeros((90, 96, 3), np.uint8), source))
    return comparison, [native.copy() for _ in range(4)], native, source.copy(), [{"synthetic": True} for _ in range(4)]


class ContextReviewFrameTests(unittest.TestCase):
    def test_four_new_overlays_reuse_seven_saved_views_and_source_scale_pairs(self):
        from src.ball_tracking import prepare_detection_visual_review as helper
        annotation, frame, source, observations, reports, natives, rows = one_frame()
        originals = {k: v.copy() for k, v in natives.items()}
        original_source = source.copy()
        with patch.object(helper, "render_detection_overlay", wraps=helper.render_detection_overlay) as overlay:
            result = review.render_frame(source, annotation, frame, observations, reports, natives, rows, .2)
        comparison, new, players, closeups, focuses = result
        self.assertEqual(overlay.call_count, 4)
        self.assertEqual(comparison.shape, (review.TILE_HEIGHT*4, review.TILE_WIDTH*3, 3))
        self.assertEqual(len(new), 4)
        self.assertEqual(players.shape, (1170, 1920, 3))
        self.assertTrue(np.array_equal(source, original_source))
        self.assertTrue(all(np.array_equal(natives[k], v) for k, v in originals.items()))
        self.assertEqual(len(focuses), 4)
        self.assertTrue(all(f["raw_unmarked_view_included"] for f in focuses))
        self.assertEqual(len({tuple(f["requested_source_crop_xyxy_px"]) for f in focuses}), 1)
        detail = review._details(frame, observations[review.CONTEXT_ARMS[0]], reports[review.CONTEXT_ARMS[0]], True)[1]
        self.assertIn("Original conf 0.800", detail)
        self.assertIn("context cost 0.070", detail)
        self.assertIn("path score 0.730", detail)
        # This ignored synthetic preview is the only artifact outside temporary
        # fixtures; it is not a real experiment or source-media frame.
        target = ROOT / "data/outputs/ball_tracking/crop_player_context_implementation_validation"
        target.mkdir(parents=True, exist_ok=True)
        for name, pixels in (("comparison", comparison), ("closeups", closeups), ("player_context", players)):
            self.assertTrue(cv2.imwrite(str(target / f"synthetic_final_v3_{name}.png"), pixels))

    def test_missing_context_panel_and_hidden_closeup_do_not_invent_truth(self):
        annotation, frame, source, observations, reports, natives, rows = one_frame(True)
        result = review.render_frame(source, annotation, frame, observations, reports, natives, rows, .35)
        self.assertEqual(len(result[4]), 4)
        self.assertTrue(all(f["focus_type"] == "top_accepted_candidate_no_truth" for f in result[4]))
        a = review.player_context_overlay(source, frame.frame_index, [])
        self.assertTrue(np.array_equal(a[review.NATIVE_HEADER:], source))
        with self.assertRaisesRegex(ValueError, "another frame"):
            review.player_context_overlay(source, 1, rows)

    def test_frame_sync_context_availability_and_native_dimensions_fail_closed(self):
        annotation, frame, source, observations, reports, natives, rows = one_frame()
        changed = copy.deepcopy(observations)
        changed[review.CONTEXT_ARMS[0]]["frame_index"] = 1
        with self.assertRaisesRegex(ValueError, "Unsynchronized"):
            review.render_frame(source, annotation, frame, changed, reports, natives, rows, .2)
        changed = copy.deepcopy(observations)
        changed[review.CONTEXT_ARMS[0]]["context_available_box_count"] = 2
        with self.assertRaisesRegex(ValueError, "availability"):
            review.render_frame(source, annotation, frame, changed, reports, natives, rows, .2)
        natives[review.CONTROL_ARMS[0]] = source
        with self.assertRaisesRegex(ValueError, "dimensions"):
            review.render_frame(source, annotation, frame, observations, reports, natives, rows, .2)


class ContextReviewAssetTests(unittest.TestCase):
    def test_reused_keys_configuration_final_frame_and_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            p, manifest = saved_fixture(root, window_count=1, frame_count=2)
            self.assertEqual(len(review.load_reused_assets(root, p)), 32)
            path = root / p["prior_review_manifest"]["path"]
            for field in ("config", "missing_final", "duplicate"):
                changed = copy.deepcopy(manifest)
                if field == "config":
                    changed["header"]["view_configs"][3]["edge_step"] = .7
                elif field == "missing_final":
                    changed["assets"] = [a for a in changed["assets"] if not a["path"].endswith("frame_000001.png")]
                else:
                    changed["assets"].append(changed["assets"][0])
                write_json(path, changed)
                p["prior_review_manifest"] = file_binding(root, path)
                with self.subTest(field=field), self.assertRaises(ValueError):
                    review.load_reused_assets(root, p)
            write_json(path, manifest)
            p["prior_review_manifest"] = file_binding(root, path)
            (path.parent / manifest["assets"][0]["path"]).write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "binding mismatch"):
                review.load_reused_assets(root, p)

    def test_report_must_bind_config_frames_and_complete_observation_digest(self):
        labels, run = fixture([[(100, 100, .8)]])
        config = review.control_grid()[0]
        observation = {"frames": [{"frame_index": 0}], "audit": "original"}
        report = {"possession_id": run.possession_id, "variant_id": config.variant_id,
                  "localization_radius_px": 10.0, "config": asdict(config),
                  "source_video": run.source_video.to_dict(), "window": run.window.to_dict(),
                  "observations_content_sha256": canonical_sha256(observation), "frame_results": [{"frame_index": 0}]}
        pool = {"evaluation_reports": [report]}
        self.assertEqual(review._report(pool, run, config, observation), report)
        with self.assertRaisesRegex(ValueError, "provenance"):
            review._report(pool, run, config, {**observation, "audit": "tampered"})
        with self.assertRaisesRegex(ValueError, "duplicate"):
            review._report({"evaluation_reports": [report, report]}, run, config, observation)

    def test_complete_atomic_resume_native_reuse_no_pipeline_or_source_video_decode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            p, _ = saved_fixture(root)
            prepared = prepared_fixture(root, p)
            before = {r["path"]: sha256_file(root / r["path"]) for r in prepared.header["reused_assets"]}
            original_capture = cv2.VideoCapture
            decoded = []
            def capture(path):
                self.assertEqual(Path(path).name, "comparison_slow.mp4", "Only newly generated clips may be decoded")
                self.assertIn(".pending_review_", str(path))
                decoded.append(path)
                return original_capture(path)
            original_write = cv2.imwrite
            writes = 0
            def interrupted(path, pixels):
                nonlocal writes
                writes += 1
                if writes == 9:
                    raise RuntimeError("synthetic interruption")
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
                self.assertEqual(result["assets"], 2112)
                self.assertEqual(result["reused_native_assets"], 2400)
                self.assertEqual(len(decoded), 12)
                bundle = Path(result["bundle"])
                manifest = read_json(bundle / "manifest.json")
                self.assertEqual(len(manifest["frame_evidence"]), 300)
                self.assertEqual(len(manifest["final_frames"]), 6)
                self.assertTrue(review.render_experiment(root, root / "synthetic_manifest.json")["reused"])
                self.assertEqual(len(decoded), 12, "Resume must not decode or rerender videos")
                self.assertEqual(before, {name: sha256_file(root / name) for name in before})
                changed = copy.deepcopy(manifest)
                changed["frame_evidence"][0]["source_png"] = changed["frame_evidence"][1]["source_png"]
                write_json(bundle / "manifest.json", changed)
                with self.assertRaisesRegex(ValueError, "source provenance"):
                    review.render_experiment(root, root / "synthetic_manifest.json")
                write_json(bundle / "manifest.json", manifest)
                last = bundle / "synthetic_window_5/confidence_0.35/context_view_3/frame_000024.png"
                original = last.read_bytes()
                last.unlink()
                with self.assertRaisesRegex(ValueError, "final frames"):
                    review.validate_review_bundle(root, bundle, prepared.header)
                last.write_bytes(original)
                last.write_bytes(b"corrupt new PNG")
                with self.assertRaisesRegex(ValueError, "asset hash"):
                    review.render_experiment(root, root / "synthetic_manifest.json")
                last.write_bytes(original)
                old_path = root / prepared.header["reused_assets"][0]["path"]
                old_path.write_bytes(b"changed old native bytes")
                with self.assertRaisesRegex(ValueError, "binding mismatch"):
                    review.render_experiment(root, root / "synthetic_manifest.json")


if __name__ == "__main__":
    unittest.main()
