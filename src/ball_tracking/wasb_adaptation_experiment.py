"""Evaluate the single approved final adapted checkpoint, preserving both controls.

Training is a separate command. This runner never chooses checkpoints, optimizes
thresholds, or accesses holdouts. Existing temporal inference and point scoring
are reused; calibration reads the resulting caches without another model pass.
"""
from __future__ import annotations

import argparse
import copy
import json
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

import cv2

from . import wasb_calibration as calibration
from .annotations import SourceVideo, verify_source_video_contract
from .wasb_experiment import (
    bound_path, canonical, digest_file, infer_window, inference_source_digest,
    load_config as load_transfer_config, load_point_cache, read_json,
    repository_path, runtime_versions, score_window, summarize, write_once,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = "configs/ball_tracking/wasb_experiments/wasb_basketball_adaptation_v0_1.json"


def load_completed_training(root, config_path):
    config = read_json(config_path)
    trial = repository_path(root, config["output_root"], "data/outputs")
    path = trial / "training/completion.json"
    completion = read_json(path)
    if (completion.get("schema_version") != "wasb_adaptation_training_completion/v0.1"
            or completion.get("status") != "completed" or completion.get("completed_updates") != 200
            or completion.get("config") != calibration.file_binding(root, config_path)
            or not completion.get("training_provenance")):
        raise ValueError("Evaluation requires the bound completed 200-update training record")
    checkpoint = bound_path(root, completion["checkpoint"])
    if checkpoint != trial / "training/checkpoint.pth":
        raise ValueError("Final checkpoint must be the recorded training output")
    return config, trial, completion, calibration.file_binding(root, path)


def evaluation_config(original, trial_relative, completion, completion_binding,
                      experiment_id="wasb_basketball_adaptation_v0_1", training_scope=None):
    result = copy.deepcopy(original)
    result.update(
        experiment_id=experiment_id + "_evaluation",
        output_root=trial_relative + "/evaluation",
        checkpoint=copy.deepcopy(completion["checkpoint"]),
        pretrained_checkpoint=copy.deepcopy(original["checkpoint"]),
        training_completion=completion_binding,
        training_provenance=copy.deepcopy(completion["training_provenance"]),
    )
    if training_scope is not None:
        result["training_scope"] = copy.deepcopy(training_scope)
    return result


def calibration_config(root, config, output, calibration_output):
    windows = copy.deepcopy(config["windows"])
    names = {"mean_heatmaps": "mean_heatmaps.npz", "heatmap_receipt": "points_receipt.json",
             "original_evaluation": "evaluation.json", "original_points": "points.json",
             "inference_identity": "inference_identity.json"}
    for window in windows:
        folder = output / window["window_id"]
        for key, filename in names.items():
            window[key] = calibration.file_binding(root, folder / filename)
    return {
        "schema_version": "wasb_cached_calibration_screen/v0.1",
        "experiment_id": config["experiment_id"].removesuffix("_evaluation") + "_calibration",
        "declaration_context": ("Eight thresholds and final checkpoint fixed in approved expanded-data adaptation plan before training"
                                if config.get("training_scope") else
                                "Eight thresholds and final checkpoint fixed in approved adaptation plan before training"),
        "source_experiment": calibration.file_binding(root, output / "experiment.json"),
        "output_root": calibration_output.relative_to(root).as_posix(),
        "component_thresholds": list(calibration.THRESHOLDS), "threshold_operator": ">",
        "localization_radius_px": 10, "rf_confidence_threshold": .01,
        "source_baseline_semantics": "original_points/evaluation mean this adapted checkpoint's fixed 0.5 output, not pretrained output",
        "rf_equal_output_count": {
            "scope": "separately within each development pool",
            "ranking": "RF top1 per frame, descending native confidence; ascending window_id, frame_index tie-break",
            "count": "adapted WASB emitted frames including hidden/unscored",
            "label_use": "none in selection; scoring only",
            "interpretation": "post-hoc ranking diagnostic, not a deployable threshold",
        },
        "windows": windows,
    }


def paired_frame_changes(adapted, pretrained):
    if [f["frame_index"] for f in adapted["frame_results"]] != [f["frame_index"] for f in pretrained["frame_results"]]:
        raise ValueError("Compared reports do not cover the same frames")
    for a, b in zip(adapted["frame_results"], pretrained["frame_results"], strict=True):
        if a["scoring_status"] != b["scoring_status"]:
            raise ValueError("Compared annotation eligibility differs")
    def matched(report):
        return {f["frame_index"] for f in report["frame_results"]
                if f["scoring_status"] == "localization_eligible" and f["matched_candidate_index"] is not None}
    new, old = matched(adapted), matched(pretrained)
    return {"recovered_frame_indices": sorted(new - old), "lost_frame_indices": sorted(old - new),
            "shared_frame_indices": sorted(new & old)}


def completed_calibration(root, config):
    """Require a receipt-bound completed summary, not just a leftover JSON file."""
    folder = repository_path(root, config["output_root"], "data/outputs")
    identity = read_json(folder / "execution_identity.json")
    if read_json(bound_path(root, identity["config"])) != config or not identity.get("source_bindings"):
        raise ValueError("Cached calibration execution identity differs")
    summary_binding = calibration.file_binding(root, folder / "summary.json")
    for path in (folder / "invocations").glob("*.result.json"):
        receipt = read_json(path)
        if (receipt.get("success") is True and receipt.get("summary") == summary_binding
                and all(receipt.get(key) == value for key, value in identity.items())):
            return read_json(folder / "summary.json")
    raise ValueError("Cached calibration has no successful receipt for its current summary")


def compare_calibrations(root, original_config, adapted_config, trial, completion_binding,
                         baseline_role="pretrained", training_scope=None):
    if baseline_role not in {"pretrained", "prior_adapted"}:
        raise ValueError("Unsupported completed comparison baseline")
    old_folder = repository_path(root, original_config["output_root"], "data/outputs")
    new_folder = repository_path(root, adapted_config["output_root"], "data/outputs")
    ids = {w["window_id"] for w in adapted_config["windows"]}
    if ids != {w["window_id"] for w in original_config["windows"]}:
        raise ValueError("Pretrained/adapted development windows differ")
    old_windows = {w["window_id"]: w for w in original_config["windows"]}
    for window in adapted_config["windows"]:
        if any(window[key] != old_windows[window["window_id"]][key] for key in (
                "purpose", "possession_id", "source_video", "start_frame_index", "end_frame_index",
                "annotation_set_id", "annotation", "rf_candidates")):
            raise ValueError("Compared calibration annotations, source frames or RF controls differ")
    old = completed_calibration(root, original_config)
    new = completed_calibration(root, adapted_config)
    if old["component_thresholds"] != new["component_thresholds"] or new["component_thresholds"] != list(calibration.THRESHOLDS):
        raise ValueError("Pretrained/adapted threshold grids differ")
    rows, report_bindings = [], []
    for old_row, new_row in zip(old["threshold_results"], new["threshold_results"], strict=True):
        threshold = old_row["component_threshold"]
        if threshold != new_row["component_threshold"]:
            raise ValueError("Threshold ordering differs")
        changes = []
        for window in adapted_config["windows"]:
            wid = window["window_id"]
            relative = Path(wid) / f"threshold_{threshold:g}/evaluation.json"
            old_report = read_json(old_folder / relative)["top_native_mass"]
            new_report = read_json(new_folder / relative)["top_native_mass"]
            for report, row in ((old_report, old_row), (new_report, new_row)):
                matches = [w for w in row["windows"] if w["window_id"] == wid]
                if len(matches) != 1 or calibration.summarize_reports([report]) != matches[0]["wasb_top_native_mass"]:
                    raise ValueError("Cached window report disagrees with completed summary")
            report_bindings.append({"threshold": threshold, "window_id": wid,
                baseline_role: calibration.file_binding(root, old_folder / relative),
                "adapted": calibration.file_binding(root, new_folder / relative)})
            changes.append({"window_id": wid, "purpose": window["purpose"],
                **paired_frame_changes(new_report, old_report)})
        pools = {}
        for pool in calibration.POOLS:
            members = [w for w in changes if w["purpose"] == pool]
            pools[pool] = {
                baseline_role: old_row["pools"][pool]["wasb_top_native_mass"],
                "adapted": new_row["pools"][pool]["wasb_top_native_mass"],
                baseline_role + "_raw": old_row["pools"][pool]["wasb_raw"],
                "adapted_raw": new_row["pools"][pool]["wasb_raw"],
                "rf_baseline": new_row["pools"][pool]["rf_baseline"],
                "rf_equal_adapted_output_count": new_row["pools"][pool]["rf_equal_output_count"],
                "adapted_vs_rf_baseline": new_row["pools"][pool]["wasb_vs_rf_baseline"],
                "adapted_vs_" + baseline_role: {key: sum(len(w[key + "_frame_indices"]) for w in members)
                                           for key in ("recovered", "lost", "shared")},
            }
        rows.append({"component_threshold": threshold, "pools": pools, "paired_windows": changes})
    result = {"schema_version": ("wasb_adaptation_comparison/v0.1" if baseline_role == "pretrained"
                                  else "wasb_adaptation_comparison/v0.2"),
        "training_completion": completion_binding,
        baseline_role + "_summary": calibration.file_binding(root, old_folder / "summary.json"),
        "adapted_summary": calibration.file_binding(root, new_folder / "summary.json"),
        "compared_report_bindings": report_bindings,
        "threshold_results": rows, "primary_threshold": .5, "localization_radius_px": 10,
        "selected_operating_point": None, "quality_gate": None, "human_visual_review": "pending",
        "limitations": ["Same-game, repeatedly inspected development windows; not independent generalization",
            (("Training uses " + training_scope + "; final checkpoint selected by update count, not evaluation")
             if training_scope else
             "Training uses only reviewed pilot windows; final checkpoint selected by update count, not evaluation"),
            "Pool-level equal-output-count RF ranking is a post-hoc diagnostic, not a deployable threshold",
            "One five-frame evaluation occlusion episode; geometric matches do not independently establish identity"]}
    if baseline_role != "pretrained":
        result["baseline_role"] = baseline_role
    filename = "comparison.json" if baseline_role == "pretrained" else "prior_adapted_comparison.json"
    write_once(trial / filename, result)
    return result


def execute(root, config_path, stage="all"):
    # Keep connected-component ordering consistent with the cached calibration.
    cv2.setNumThreads(1)
    config, trial, completion, completed_binding = load_completed_training(root, config_path)
    training_scope = None
    if config.get("schema_version") == "wasb_adaptation_experiment/v0.2":
        training_scope = (f"{len(config['training_blocks'])} training blocks / "
                          f"{config['expected_split']['reviewed_frames']} reviewed frames")
    original = load_transfer_config(root, bound_path(root, config["transfer_config"]))
    if len(original["windows"]) != 6 or len({w["window_id"] for w in original["windows"]}) != 6:
        raise ValueError("The approved comparison requires the six bound development windows")
    result_config = evaluation_config(original, trial.relative_to(root).as_posix(), completion, completed_binding,
                                     config["experiment_id"], training_scope)
    output = repository_path(root, result_config["output_root"], "data/outputs")
    output.mkdir(parents=True, exist_ok=True)
    invocation = output / "invocations" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + uuid.uuid4().hex + ".json")
    started = time.perf_counter()
    receipt = {"stage": stage, "training_completion": completed_binding,
               "source": calibration.file_binding(ROOT, Path(__file__)), "status": "started"}
    try:
        write_once(output / "experiment.json", result_config)
        identity = {"experiment_config_sha256": canonical(result_config), "weights": completion["checkpoint"],
            "training_completion": completed_binding, "upstream_commit": original["upstream_commit"],
            "inference": original["inference"],
            "adapter_sha256": digest_file(Path(__file__).with_name("wasb_adapter.py")),
            "derived_adapter_sha256": digest_file(Path(__file__).with_name("wasb_adapted_adapter.py")),
            "inference_source_sha256": inference_source_digest(), "runtime_versions": runtime_versions(),
            "native_score_definition": "sum of sigmoid values in an 8-connected component above 0.5",
            "input_modality": "three_RGB_images", "offline_future_context": True}
        saved_reports = {pool: read_json(bound_path(root, binding)) for pool, binding in original["rf_reports"].items()}
        payloads, adapter, verified_sources = [], None, set()
        for window in original["windows"]:
            folder = output / window["window_id"]
            if stage == "all":
                source = window["source_video"]
                if source["sha256"] not in verified_sources:
                    verify_source_video_contract(SourceVideo.from_mapping(source), root)
                    verified_sources.add(source["sha256"])
                if adapter is None and not (folder / "points_receipt.json").exists():
                    from .wasb_adapted_adapter import AdaptedWasbAdapter
                    adapter = AdaptedWasbAdapter(repository_path(root, original["upstream_source"]),
                        bound_path(root, original["checkpoint"]), bound_path(root, completion["checkpoint"]),
                        completion["checkpoint"]["sha256"], completion["training_provenance"], device="cuda")
                    write_once(output / "model_runtime.json", adapter.provenance)
                run = infer_window(root, result_config, window, adapter, output, identity)
            else:
                run = load_point_cache(folder, identity)
            payload, labels, methods = score_window(root, result_config, window, run, output, saved_reports)
            payloads.append(payload)
            if stage == "render":
                from .wasb_adaptation_review import render_window
                render_window(root, window, labels, methods, payload, folder)
            print(f"Adapted checkpoint: {window['window_id']} {stage} complete", flush=True)
        summary = summarize(result_config, payloads)
        summary["training_completion"] = completed_binding
        summary["limitations"] = [s for s in summary["limitations"] if "No tracker" not in s] + [
            ("Checkpoint trained on " + training_scope + "; no tracker, interpolation or player/court inference input"
             if training_scope else
             "Checkpoint trained on the three disjoint reviewed pilots; no tracker, interpolation or player/court inference input")]
        write_once(output / "summary.json", summary)
        calibration_output = trial / "calibration"
        calibration_output.mkdir(exist_ok=True)
        derived_calibration = calibration_config(root, result_config, output, calibration_output)
        calibration_path = trial / "calibration_config.json"
        write_once(calibration_path, derived_calibration)
        # A complete cached screen does not need to be recomputed for rendering.
        if not (calibration_output / "summary.json").exists():
            calibration.execute(root, calibration_path)
        old_config = calibration.load_config(root, bound_path(root, config["original_calibration_config"]))
        comparison = compare_calibrations(root, old_config, derived_calibration, trial, completed_binding,
                                          training_scope=training_scope)
        if config.get("prior_adapted_calibration_config"):
            prior = calibration.load_config(root, bound_path(root, config["prior_adapted_calibration_config"]))
            compare_calibrations(root, prior, derived_calibration, trial, completed_binding,
                                 baseline_role="prior_adapted", training_scope=training_scope)
            receipt["prior_adapted_comparison"] = calibration.file_binding(root, trial / "prior_adapted_comparison.json")
        receipt.update(status="completed", comparison=calibration.file_binding(root, trial / "comparison.json"))
        return comparison
    except BaseException as exc:
        receipt.update(status="failed", error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc())
        raise
    finally:
        receipt["elapsed_seconds"] = time.perf_counter() - started
        write_once(invocation, receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--stage", choices=("all", "score", "render"), default="all")
    args = parser.parse_args()
    result = execute(ROOT, repository_path(ROOT, args.config), args.stage)
    print(json.dumps({"status": "completed", "thresholds_compared": len(result["threshold_results"])}), flush=True)


if __name__ == "__main__":
    main()
