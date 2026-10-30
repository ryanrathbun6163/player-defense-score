"""Cached calibration uses real component/point producers and label-free ranking."""
import copy
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np

from src.ball_tracking import wasb_calibration as calibration
from src.ball_tracking.point_evaluation import evaluate_points
from src.ball_tracking.wasb_adapter import components_from_heatmap
from src.ball_tracking.wasb_experiment import make_point_run, rf_point_run, select_top_one, write_once
from test_ball_annotation_foundation import detection, not_visible_frame, observed_frame, parse_reviewed_annotations


def labels_and_window(window_id="synthetic", pool="representative_evaluation"):
    labels = parse_reviewed_annotations([
        observed_frame(0, center=(376.875, 376.875)),
        observed_frame(1, center=(376.875, 376.875)), not_visible_frame(2),
    ], annotation_set_id=window_id + "_labels")
    labels = replace(labels, window=replace(labels.window, selection_purpose=pool))
    window = {"window_id": window_id, "purpose": pool, "annotation_set_id": labels.annotation_set_id,
              "possession_id": labels.possession_id, "source_video": labels.source_video.to_dict(),
              "start_frame_index": 0, "end_frame_index": 2,
              "mean_heatmaps": {"path": "synthetic.npz", "sha256": "a" * 64},
              "inference_identity": {"path": "synthetic_identity.json", "sha256": "b" * 64}}
    return labels, window


def fixture(root):
    original_output = root / "data/outputs/original"
    declarations, windows = [], []
    for i in range(6):
        labels, window = labels_and_window(f"window_{i}", calibration.POOLS[i // 3])
        folder = original_output / window["window_id"]
        folder.mkdir(parents=True)
        annotation = root / f"labels_{i}.json"
        write_once(annotation, labels.to_dict())
        window["annotation"] = calibration.file_binding(root, annotation)
        record = {"schema_version": "ball_tiled_candidates/v0.1",
                  "header": {"window": {key: window[key] for key in (
                      "window_id", "purpose", "annotation_set_id", "possession_id", "source_video",
                      "start_frame_index", "end_frame_index")}},
                  "frames": [{"frame_index": frame, "candidates": [{
                      "detection": detection(376.875, 376.875, .9 - frame * .1)}]} for frame in range(3)]}
        candidates = root / f"rf_{i}.json"
        write_once(candidates, record)
        window["rf_candidates"] = calibration.file_binding(root, candidates)
        declared = {k: v for k, v in window.items() if k not in {"mean_heatmaps", "inference_identity"}}
        declarations.append(declared)
        heatmaps = np.zeros((3, 288, 512), dtype=np.float32)
        heatmaps[0, 100:102, 100:102] = .75
        heatmaps[1, 100:102, 100:102] = .15
        # A hidden-frame distractor crosses only part of the declared grid.
        heatmaps[2, 200, 400] = .075
        with (folder / "mean_heatmaps.npz").open("xb") as stream:
            np.savez_compressed(stream, heatmaps=heatmaps, frame_indices=np.arange(3))
        components = [components_from_heatmap(h, 1920, 1080, .5) for h in heatmaps]
        original = make_point_run(window, {"synthetic_model": True}, components)
        write_once(folder / "points.json", original)
        write_once(folder / "inference_identity.json", {"synthetic": True, "no_model_loaded": True})
        for field, filename in (("mean_heatmaps", "mean_heatmaps.npz"), ("original_points", "points.json"),
                                ("inference_identity", "inference_identity.json")):
            window[field] = calibration.file_binding(root, folder / filename)
        write_once(folder / "points_receipt.json", {"schema_version": "wasb_point_cache_receipt/v0.1",
            "files": {name: window[field]["sha256"] for name, field in (
                ("mean_heatmaps.npz", "mean_heatmaps"), ("points.json", "original_points"),
                ("inference_identity.json", "inference_identity"))}})
        window["heatmap_receipt"] = calibration.file_binding(root, folder / "points_receipt.json")
        rf = rf_point_run(window, record, .01)
        runs = {"wasb_all": original, "wasb_top_one": select_top_one(original),
                "rf_all": rf, "rf_top_one": select_top_one(rf)}
        write_once(folder / "evaluation.json", {"reports": {
            name: {"10": evaluate_points(labels, run, localization_radius_px=10)} for name, run in runs.items()}})
        window["original_evaluation"] = calibration.file_binding(root, folder / "evaluation.json")
        windows.append(window)
    source = root / "original_experiment.json"
    write_once(source, {"windows": declarations, "output_root": "data/outputs/original"})
    config = {"schema_version": "wasb_cached_calibration_screen/v0.1", "experiment_id": "synthetic_calibration",
              "component_thresholds": list(calibration.THRESHOLDS), "threshold_operator": ">",
              "localization_radius_px": 10, "rf_confidence_threshold": .01,
              "source_experiment": calibration.file_binding(root, source),
              "output_root": "data/outputs/calibration", "windows": windows}
    path = root / "calibration.json"
    write_once(path, config)
    return path, config


class CachedCalibrationTests(unittest.TestCase):
    def test_real_component_producer_point_consumer_and_native_mass_ranking(self):
        labels, window = labels_and_window()
        maps = np.zeros((3, 288, 512), dtype=np.float32)
        maps[0, 100:102, 100:102] = .3  # mass1.2, fractional source centroid.
        maps[0, 200, 400] = .75
        raw, top, components = calibration.point_runs_from_heatmaps(window, maps, .2)
        self.assertEqual(components[0], components_from_heatmap(maps[0], 1920, 1080, .2))
        self.assertGreater(top["frames"][0]["candidates"][0]["native_score"], 1)
        self.assertEqual(top["frames"][0]["candidates"][0]["center_xy_px"], [376.875, 376.875])
        score = evaluate_points(labels, top, localization_radius_px=0)
        self.assertEqual((score["true_positive_count"], score["false_negative_count"]), (1, 1))
        _, default, _ = calibration.point_runs_from_heatmaps(window, maps, .5)
        default_score = evaluate_points(labels, default, localization_radius_px=10)
        self.assertEqual(default_score["true_positive_count"], 0)
        self.assertEqual(default_score["false_positive_count"], 1)
        self.assertNotIn("confidence", raw["frames"][0]["candidates"][0])

    def test_threshold_is_strict_and_only_declared_values_are_permitted(self):
        labels, window = labels_and_window()
        maps = np.zeros((3, 288, 512), dtype=np.float32)
        maps[0, 100, 100] = .5
        raw, _, _ = calibration.point_runs_from_heatmaps(window, maps, .5)
        self.assertEqual(raw["frames"][0]["candidates"], [])
        with self.assertRaisesRegex(ValueError, "Undeclared"):
            calibration.point_runs_from_heatmaps(window, maps, .123)

    def test_equal_output_count_is_label_free_and_ties_are_stable(self):
        labels, window = labels_and_window()
        source = make_point_run(window, {"test": True}, [[{"center_x": 0, "center_y": 0, "native_score": .5}]] * 3)
        runs = {"z_window": source, "a_window": copy.deepcopy(source)}
        original = copy.deepcopy(runs)
        selected, ranking = calibration.rank_rf_equal_output_count(runs, 4)
        self.assertEqual([(r["window_id"], r["frame_index"]) for r in ranking],
                         [("a_window", 0), ("a_window", 1), ("a_window", 2), ("z_window", 0)])
        self.assertEqual(sum(bool(f["candidates"]) for run in selected.values() for f in run["frames"]), 4)
        self.assertEqual(runs, original)
        self.assertFalse(selected["a_window"]["model_provenance"]["ranking_uses_labels"])
        # The selected frame2 is hidden in labels: ranking did not remove it.
        self.assertTrue(selected["a_window"]["frames"][2]["candidates"])
        summary = calibration.summarize_reports([evaluate_points(labels, selected["a_window"], localization_radius_px=10)])
        self.assertEqual(summary["emitted_frames_including_hidden_and_unscored"], 3)
        self.assertEqual(summary["hidden_alarm_frames"], 1)

    def test_equal_count_zero_and_impossible_counts_or_non_top_one_fail(self):
        _, window = labels_and_window()
        run = make_point_run(window, {"test": True}, [[{"center_x": 0, "center_y": 0, "native_score": .5}]] * 3)
        views, rank = calibration.rank_rf_equal_output_count({"a": run}, 0)
        self.assertEqual(rank, [])
        self.assertFalse(any(f["candidates"] for f in views["a"]["frames"]))
        for count in (True, -1, 4):
            with self.assertRaises(ValueError):
                calibration.rank_rf_equal_output_count({"a": run}, count)
        run["frames"][0]["candidates"] *= 2
        with self.assertRaisesRegex(ValueError, "top-one"):
            calibration.rank_rf_equal_output_count({"a": run}, 1)

    def test_complete_cached_screen_reproduces_default_and_never_loads_model_or_media(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, config = fixture(root)
            before = {p: p.read_bytes() for p in (root / "data/outputs/original").rglob("*") if p.is_file()}
            with patch("src.ball_tracking.wasb_adapter.WasbAdapter", side_effect=AssertionError("model forbidden")), \
                    patch("cv2.VideoCapture", side_effect=AssertionError("media forbidden")):
                result = calibration.execute(root, path)
            self.assertEqual(result["default_0_5_original_points_and_report_parity"], "passed_all_six_windows")
            self.assertEqual(result["component_thresholds"], list(calibration.THRESHOLDS))
            for row in result["threshold_results"]:
                for pool in calibration.POOLS:
                    counts = row["pools"][pool]
                    field = "emitted_frames_including_hidden_and_unscored"
                    self.assertEqual(counts["wasb_top_native_mass"][field], counts["rf_equal_output_count"][field])
            self.assertTrue(all(p.read_bytes() == content for p, content in before.items()))
            self.assertIsNone(result["selected_operating_point"])

    def test_changed_grid_scope_or_original_output_location_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, config = fixture(root)
            variants = []
            for key, value in (("component_thresholds", [.5]), ("localization_radius_px", 20),
                               ("output_root", "data/outputs/original")):
                variants.append({**config, key: value})
            changed = copy.deepcopy(config)
            changed["windows"][0]["purpose"] = "sealed_holdout"
            variants.append(changed)
            changed = copy.deepcopy(config)
            changed["windows"] = changed["windows"][:-1]
            variants.append(changed)
            for index, changed in enumerate(variants):
                other = root / f"changed_{index}.json"
                write_once(other, changed)
                with self.subTest(index=index), self.assertRaises(ValueError):
                    calibration.load_config(root, other)

    def test_bad_cache_digest_shape_frame_identity_and_receipt_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, config = fixture(root)
            window = config["windows"][0]
            wrong_digest = copy.deepcopy(window)
            wrong_digest["mean_heatmaps"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "digest"):
                calibration.load_mean_heatmaps(root, wrong_digest)
            for index, (maps, ids) in enumerate((
                    (np.zeros((3, 288, 512), dtype=np.float64), np.arange(3)),
                    (np.zeros((3, 288, 512), dtype=np.float32), np.array([0, 0, 2])),
                    (np.full((3, 288, 512), np.nan, dtype=np.float32), np.arange(3)))):
                path = root / f"bad_{index}.npz"
                with path.open("xb") as stream:
                    np.savez_compressed(stream, heatmaps=maps, frame_indices=ids)
                bad = copy.deepcopy(window)
                bad["mean_heatmaps"] = calibration.file_binding(root, path)
                receipt = calibration.read_json(root / window["heatmap_receipt"]["path"])
                receipt["files"]["mean_heatmaps.npz"] = bad["mean_heatmaps"]["sha256"]
                receipt_path = root / f"bad_receipt_{index}.json"
                write_once(receipt_path, receipt)
                bad["heatmap_receipt"] = calibration.file_binding(root, receipt_path)
                with self.assertRaisesRegex(ValueError, "values, dimensions or frame identity"):
                    calibration.load_mean_heatmaps(root, bad)

    def test_conflicting_evidence_is_preserved_and_failure_is_recorded(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, config = fixture(root)
            output = root / config["output_root"]
            write_once(output / "experiment.json", {"old": "preserved"})
            before = (output / "experiment.json").read_bytes()
            with self.assertRaisesRegex(ValueError, "Existing evidence differs"):
                calibration.execute(root, path)
            self.assertEqual((output / "experiment.json").read_bytes(), before)
            receipts = list((output / "invocations").glob("*.result.json"))
            self.assertEqual(len(receipts), 1)
            result = json.loads(receipts[0].read_text())
            self.assertFalse(result["success"])
            self.assertIn("ValueError", result["failure"])
            self.assertGreaterEqual(result["elapsed_seconds"], 0)

    def test_saved_parity_rejects_changed_metrics_and_frame_identity(self):
        labels, window = labels_and_window()
        run = make_point_run(window, {"test": True}, [[], [], []])
        original = evaluate_points(labels, run, localization_radius_px=10)
        for field in ("false_negative_count", "frame_results"):
            changed = copy.deepcopy(original)
            if field == "frame_results":
                changed[field][0]["frame_index"] = 4
            else:
                changed[field] += 1
            with self.assertRaisesRegex(ValueError, "parity failed"):
                calibration.assert_saved_parity(changed, original)


if __name__ == "__main__":
    unittest.main()
