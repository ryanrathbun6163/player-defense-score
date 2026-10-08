"""Fixed development calibration screen over saved WASB mean heatmaps only.

No model, media decoding, inference, training or holdout access occurs. The RF
equal-output-count comparison ranks saved predictions without labels, separately
within each development pool. It is a post-hoc diagnostic, not a deployable gate.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from .annotations import load_annotations
from .point_evaluation import evaluate_points, validate_point_run
from .wasb_adapter import components_from_heatmap
from .wasb_experiment import (
    bound_path, digest_file, make_point_run, read_json, repository_path,
    rf_point_run, select_top_one, write_once,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = "configs/ball_tracking/wasb_experiments/wasb_basketball_calibration_v0_1.json"
THRESHOLDS = (0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5)
POOLS = ("representative_evaluation", "challenge_evaluation")


def file_binding(root, path):
    return {"path": path.resolve().relative_to(root.resolve()).as_posix(), "sha256": digest_file(path)}


def load_config(root, path):
    config = read_json(path)
    if (config["schema_version"] != "wasb_cached_calibration_screen/v0.1"
            or config["component_thresholds"] != list(THRESHOLDS)
            or config["threshold_operator"] != ">" or config["localization_radius_px"] != 10
            or config["rf_confidence_threshold"] != .01):
        raise ValueError("Calibration settings differ from the fixed declared screen")
    original = read_json(bound_path(root, config["source_experiment"]))
    declared = {w["window_id"]: w for w in original["windows"]}
    windows = config["windows"]
    if (len(windows) != 6 or len(declared) != 6
            or len({w["window_id"] for w in windows}) != 6
            or {w["window_id"] for w in windows} != set(declared)):
        raise ValueError("Calibration requires exactly the six original development windows")
    for window in windows:
        prior = declared[window["window_id"]]
        if any(window.get(key) != value for key, value in prior.items()):
            raise ValueError("Calibration window differs from the bound original experiment")
        if window["purpose"] not in POOLS:
            raise ValueError("Only the released development pools may be inspected")
        source_folder = repository_path(root, window["mean_heatmaps"]["path"]).parent
        expected_folder = (root / original["output_root"] / window["window_id"]).resolve()
        if source_folder != expected_folder:
            raise ValueError("Mean heatmap cache is outside its original window")
        for field, filename in (("heatmap_receipt", "points_receipt.json"),
                                ("original_evaluation", "evaluation.json"),
                                ("original_points", "points.json"),
                                ("inference_identity", "inference_identity.json")):
            if repository_path(root, window[field]["path"]) != source_folder / filename:
                raise ValueError("Saved cache administrative binding is outside its window")
    output = repository_path(root, config["output_root"], "data/outputs")
    original_output = repository_path(root, original["output_root"], "data/outputs")
    if output == original_output or output in original_output.parents or original_output in output.parents:
        raise ValueError("Calibration must preserve the original output tree")
    return config


def load_mean_heatmaps(root, window):
    path = bound_path(root, window["mean_heatmaps"])
    receipt = read_json(bound_path(root, window["heatmap_receipt"]))
    if (receipt["schema_version"] != "wasb_point_cache_receipt/v0.1"
            or receipt["files"]["mean_heatmaps.npz"] != window["mean_heatmaps"]["sha256"]
            or receipt["files"]["points.json"] != window["original_points"]["sha256"]
            or receipt["files"]["inference_identity.json"] != window["inference_identity"]["sha256"]):
        raise ValueError("Mean heatmaps do not match the original cache receipt")
    with np.load(path, allow_pickle=False) as saved:
        if set(saved.files) != {"heatmaps", "frame_indices"}:
            raise ValueError("Unexpected mean heatmap cache fields")
        values, frame_ids = saved["heatmaps"], saved["frame_indices"]
    expected = np.arange(window["start_frame_index"], window["end_frame_index"] + 1)
    if (values.dtype != np.float32 or values.shape != (len(expected), 288, 512)
            or frame_ids.dtype.kind not in "iu" or not np.array_equal(frame_ids, expected)
            or not np.isfinite(values).all() or (values < 0).any() or (values > 1).any()):
        raise ValueError("Saved mean heatmaps have invalid values, dimensions or frame identity")
    return values


def point_runs_from_heatmaps(window, heatmaps, threshold):
    """Use the actual official component producer and existing point run builder."""
    if threshold not in THRESHOLDS:
        raise ValueError("Undeclared component threshold")
    source = window["source_video"]
    components = [components_from_heatmap(h, source["width_px"], source["height_px"], threshold)
                  for h in heatmaps]
    run = make_point_run(window, {
        "model": "WASB saved basketball mean heatmaps", "mean_heatmaps": window["mean_heatmaps"],
        "inference_identity": window["inference_identity"], "heatmap_threshold": threshold,
        "threshold_operator": ">", "native_score_definition": "sum of sigmoid values in an 8-connected component",
        "new_inference": False, "calibration_scope": "already-inspected development windows",
    }, components)
    run["point_run_id"] += f"_calibration_{threshold:g}"
    return run, select_top_one(run), components


def rank_rf_equal_output_count(runs, count):
    """Select N RF top-one outputs by confidence, without any annotation input."""
    if type(count) is not int or count < 0:
        raise ValueError("Output count must be a nonnegative integer")
    ranked = []
    for window_id, run in runs.items():
        for frame in run["frames"]:
            candidates = frame["candidates"]
            if len(candidates) > 1:
                raise ValueError("Equal-count ranking requires RF top-one per frame")
            if candidates:
                candidate = candidates[0]
                score = candidate["native_score"]
                if isinstance(score, bool) or not isinstance(score, (float, int)) or not math.isfinite(score):
                    raise ValueError("Ranking requires finite native RF confidence")
                ranked.append({"window_id": window_id, "frame_index": frame["frame_index"],
                               "candidate_index": candidate["candidate_index"], "native_confidence": score})
    ranked.sort(key=lambda row: (-row["native_confidence"], row["window_id"], row["frame_index"]))
    if count > len(ranked):
        raise ValueError("RF has fewer emitted frames than the required equal output count")
    selected = ranked[:count]
    keep = {(r["window_id"], r["frame_index"]) for r in selected}
    views = copy.deepcopy(runs)
    for window_id, run in views.items():
        run["point_run_id"] += f"_post_hoc_equal_count_{count}"
        run["model_provenance"].update(
            selection="post_hoc_pool_confidence_rank_equal_output_count",
            retained_pool_output_count=count, ranking_uses_labels=False,
        )
        for frame in run["frames"]:
            if (window_id, frame["frame_index"]) not in keep:
                frame["candidates"] = []
    return views, selected


def summarize_reports(reports):
    frames = [frame for report in reports for frame in report["frame_results"]]
    eligible = [f for f in frames if f["scoring_status"] == "localization_eligible"]
    hidden = [f for f in frames if f["scoring_status"] == "not_visible_negative"]
    matched = sum(f["matched_candidate_index"] is not None for f in eligible)
    wrong = sum(f["matched_candidate_index"] is None and f["accepted_detection_count"] > 0 for f in eligible)
    missing = sum(f["accepted_detection_count"] == 0 for f in eligible)
    tp = sum(r["true_positive_count"] for r in reports)
    fp = sum(r["false_positive_count"] for r in reports)
    return {
        "frame_count": len(frames), "eligible": len(eligible), "hidden": len(hidden),
        "raw_available_or_matched": matched, "wrong_present": wrong, "missing": missing,
        "hidden_alarm_frames": sum(f["accepted_detection_count"] > 0 for f in hidden),
        "hidden_alarm_candidates": sum(f["accepted_detection_count"] for f in hidden),
        "emitted_frames_including_hidden_and_unscored": sum(f["accepted_detection_count"] > 0 for f in frames),
        "emitted_candidates": sum(f["accepted_detection_count"] for f in frames),
        "true_positive_count": tp, "false_positive_count": fp,
        "false_negative_count": sum(r["false_negative_count"] for r in reports),
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": matched / len(eligible) if eligible else None,
        "eligible_output_coverage": (matched + wrong) / len(eligible) if eligible else None,
    }


def assert_saved_parity(actual, original):
    """Compare genuine saved reports without rewriting their original provenance."""
    for key in ("frame_results", "eligible_frame_count", "not_visible_frame_count", "unscored_frame_count",
                "input_detection_count", "true_positive_count", "false_positive_count", "false_negative_count",
                "duplicate_false_positive_count", "non_visible_false_alarm_count",
                "non_visible_false_alarm_frame_count", "unscored_prediction_count", "precision", "recall",
                "matched_center_error_px", "matched_effective_center_error_px"):
        if actual[key] != original[key]:
            raise ValueError(f"Saved original report parity failed: {key}")


def paired_matches(actual, reference):
    if [f["frame_index"] for f in actual["frame_results"]] != [f["frame_index"] for f in reference["frame_results"]]:
        raise ValueError("Paired reports have different frame identities")
    matches = {f["frame_index"] for f in actual["frame_results"] if f["matched_candidate_index"] is not None}
    prior = {f["frame_index"] for f in reference["frame_results"] if f["matched_candidate_index"] is not None}
    return {"recovered": len(matches - prior), "lost": len(prior - matches), "shared": len(matches & prior),
            "recovered_frame_indices": sorted(matches - prior), "lost_frame_indices": sorted(prior - matches)}


def run_screen(root, config, output):
    labels_by_id, rf_runs, rf_reports, rf_raw_reports = {}, {}, {}, {}
    thresholds = {t: {} for t in THRESHOLDS}
    for window in config["windows"]:
        wid = window["window_id"]
        labels = load_annotations(bound_path(root, window["annotation"]))
        if labels.window.selection_purpose != window["purpose"]:
            raise ValueError("Reviewed annotation pool differs")
        labels_by_id[wid] = labels
        cache = load_mean_heatmaps(root, window)
        original_points = read_json(bound_path(root, window["original_points"]))
        validate_point_run(labels, original_points)
        original_evaluation = read_json(bound_path(root, window["original_evaluation"]))
        read_json(bound_path(root, window["inference_identity"]))
        candidate_record = read_json(bound_path(root, window["rf_candidates"]))
        header = candidate_record["header"]["window"]
        if any(header.get(key) != window[key] for key in (
                "window_id", "purpose", "possession_id", "source_video", "start_frame_index",
                "end_frame_index", "annotation_set_id")):
            raise ValueError("Saved RF candidate header differs from its declared window")
        rf_runs[wid] = select_top_one(rf_point_run(window, candidate_record, .01))
        rf_reports[wid] = evaluate_points(labels, rf_runs[wid], localization_radius_px=10)
        assert_saved_parity(rf_reports[wid], original_evaluation["reports"]["rf_top_one"]["10"])
        rf_raw_reports[wid] = original_evaluation["reports"]["rf_all"]["10"]
        write_once(output / wid / "rf_baseline.json", rf_reports[wid])
        for threshold in THRESHOLDS:
            raw, top, components = point_runs_from_heatmaps(window, cache, threshold)
            raw_score = evaluate_points(labels, raw, localization_radius_px=10)
            top_score = evaluate_points(labels, top, localization_radius_px=10)
            if threshold == .5:
                if raw["frames"] != original_points["frames"]:
                    raise ValueError("Default component output differs from original saved points")
                assert_saved_parity(raw_score, original_evaluation["reports"]["wasb_all"]["10"])
                assert_saved_parity(top_score, original_evaluation["reports"]["wasb_top_one"]["10"])
            folder = output / wid / f"threshold_{threshold:g}"
            write_once(folder / "components.json", components)
            write_once(folder / "points.json", raw)
            write_once(folder / "evaluation.json", {"raw": raw_score, "top_native_mass": top_score})
            thresholds[threshold][wid] = {"raw": raw_score, "top_native_mass": top_score,
                "output_count": sum(bool(f["candidates"]) for f in top["frames"])}
        print(f"Calibrated saved heatmaps: {wid}", flush=True)

    rows = []
    for threshold in THRESHOLDS:
        pools, windows = {}, []
        for pool in POOLS:
            ids = sorted(w["window_id"] for w in config["windows"] if w["purpose"] == pool)
            count = sum(thresholds[threshold][wid]["output_count"] for wid in ids)
            retained, ranking = rank_rf_equal_output_count({wid: rf_runs[wid] for wid in ids}, count)
            equal_scores = {wid: evaluate_points(labels_by_id[wid], retained[wid], localization_radius_px=10) for wid in ids}
            equal_payload = {"diagnostic": "post_hoc_pool_equal_output_count_not_deployable_threshold",
                "purpose": pool, "wasb_component_threshold": threshold, "retained_output_count": count,
                "ranking_uses_labels": False, "ranking": ranking, "evaluation_reports": equal_scores}
            write_once(output / "equal_output_count" / f"{pool}_{threshold:g}.json", equal_payload)
            pools[pool] = {
                "wasb_raw": summarize_reports([thresholds[threshold][wid]["raw"] for wid in ids]),
                "wasb_top_native_mass": summarize_reports([thresholds[threshold][wid]["top_native_mass"] for wid in ids]),
                "rf_baseline": summarize_reports([rf_reports[wid] for wid in ids]),
                "rf_saved_raw": summarize_reports([rf_raw_reports[wid] for wid in ids]),
                "rf_equal_output_count": summarize_reports(list(equal_scores.values())),
            }
            for name, references in (("wasb_vs_rf_baseline", rf_reports),
                                     ("wasb_vs_rf_equal_output_count", equal_scores)):
                paired = [paired_matches(thresholds[threshold][wid]["top_native_mass"], references[wid]) for wid in ids]
                pools[pool][name] = {key: sum(row[key] for row in paired) for key in ("recovered", "lost", "shared")}
            for wid in ids:
                windows.append({"window_id": wid, "purpose": pool,
                    "wasb_raw": summarize_reports([thresholds[threshold][wid]["raw"]]),
                    "wasb_top_native_mass": summarize_reports([thresholds[threshold][wid]["top_native_mass"]]),
                    "rf_baseline": summarize_reports([rf_reports[wid]]),
                    "rf_saved_raw": summarize_reports([rf_raw_reports[wid]]),
                    "rf_equal_pool_output_count": summarize_reports([equal_scores[wid]]),
                    "wasb_vs_rf_baseline": paired_matches(thresholds[threshold][wid]["top_native_mass"], rf_reports[wid]),
                    "wasb_vs_rf_equal_output_count": paired_matches(thresholds[threshold][wid]["top_native_mass"], equal_scores[wid])})
        rows.append({"component_threshold": threshold, "pools": pools, "windows": windows})
    summary = {"schema_version": "wasb_cached_calibration_summary/v0.1", "experiment_id": config["experiment_id"],
        "component_thresholds": list(THRESHOLDS), "localization_radius_px": 10, "threshold_operator": ">",
        "rf_confidence_threshold": .01, "default_0_5_original_points_and_report_parity": "passed_all_six_windows",
        "saved_rf_baseline_report_parity": "passed_all_six_windows", "threshold_results": rows,
        "new_inference": False, "holdout_access": False, "selected_operating_point": None, "quality_gate": None,
        "human_visual_review": "pending; this numeric screen does not replace synchronized visual review",
        "limitations": ["Repeatedly inspected development data; calibration is not independent generalization evidence",
            "RF equal-count ranking is label-free within each pool, but its N is derived post hoc from WASB output; not a deployable threshold",
            "Raw candidate availability uses truth for scoring and is not top-candidate performance",
            "Mean heatmaps and temporal boundary contributions are unchanged; native masses are not probabilities",
            "Five hidden frames represent one hidden episode; uncertainty and original failures remain preserved"]}
    write_once(output / "summary.json", summary)
    return summary


def execute(root, config_path):
    config = load_config(root, config_path)
    output = repository_path(root, config["output_root"], "data/outputs")
    output.mkdir(parents=True, exist_ok=True)
    invocation = output / "invocations" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + uuid.uuid4().hex)
    sources = [Path(__file__), Path(__file__).with_name("wasb_adapter.py"),
               Path(__file__).with_name("wasb_experiment.py"), Path(__file__).with_name("point_evaluation.py"),
               Path(__file__).with_name("annotations.py")]
    identity = {"config": file_binding(root, config_path),
                "source_bindings": [file_binding(ROOT, path) for path in sources],
                "python": sys.version, "numpy": np.__version__, "opencv": cv2.__version__,
                "new_inference": False, "model_loaded": False, "media_read": False, "holdout_access": False}
    write_once(invocation.with_suffix(".started.json"), identity)
    started = time.perf_counter()
    try:
        write_once(output / "experiment.json", config)
        write_once(output / "execution_identity.json", identity)
        cv2.setNumThreads(1)
        summary = run_screen(root, config, output)
    except BaseException as exc:
        write_once(invocation.with_suffix(".result.json"), {
            **identity, "success": False, "elapsed_seconds": time.perf_counter() - started,
            "failure": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc(),
        })
        raise
    write_once(invocation.with_suffix(".result.json"), {
        **identity, "success": True, "elapsed_seconds": time.perf_counter() - started,
        "summary": file_binding(root, output / "summary.json"),
    })
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    args = parser.parse_args()
    summary = execute(ROOT, repository_path(ROOT, args.config))
    print(json.dumps({"experiment_id": summary["experiment_id"], "status": "completed",
                      "default_parity": summary["default_0_5_original_points_and_report_parity"]}))


if __name__ == "__main__":
    main()
