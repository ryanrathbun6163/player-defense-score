"""Seal CPU response descriptors before a separate reference-assisted analysis.

Only saved observed pools, compact choices, native provenance and mean maps enter
feature extraction. This module does not choose tracks or fit a classifier.
"""
from __future__ import annotations

from copy import deepcopy
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

import numpy as np

from .candidate_response_features import describe_response, FEATURE_NAMES
from .weak_response_capture import read, bind, bound, write_once, validate_context, HOU


ROOT = Path(__file__).resolve().parents[2]
CONFIG = "configs/ball_tracking/proposals/candidate_response_feasibility_v0_1.json"
OUTPUT = "data/outputs/ball_tracking/candidate_identity_feasibility_v0_1/study_v0_1"
INPUT_KEYS = ("paired_inputs", "original_comparison", "followup_comparison", "inventory",
              "captured_HOU_means", "original_comparison_audit", "followup_audit", "source_roles",
              "research_control")
SOURCE_NAMES = ("candidate_response_features", "candidate_response_study", "weak_response_candidates",
                "weak_response_capture")


PROVENANCE_FIELDS = ("source_frame_index", "source_pts_ticks", "time_base", "mean_heatmap_sha256")
CANDIDATE_FIELDS = ("candidate_index", "original_index", "center_x", "center_y", "heatmap_x", "heatmap_y",
                    "native_score", "component_pixels", "in_source_bounds", "component_index", "extraction",
                    "threshold", "extraction_index", "extraction_original_index", "equivalent_extractions")


def check(condition, message):
    if not condition:
        raise ValueError(message)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def validate_config(config):
    check(config["schema_version"] == "candidate_response_feasibility/v0.1"
          and config["status"] == "prospective_CPU_diagnostic_no_tracking_or_fitting", "Unexpected study protocol")
    check(config["output_root"] + "/" + config["study_subdirectory"] == OUTPUT,
          "Declared output scope changed")
    check(tuple(config["feature_block_ids"]) == HOU, "Only all six complete HOU contexts allowed for features")
    check(all(config[key] == 0 for key in
              ("new_model_calls", "new_training_updates", "new_labels", "new_tracking_outputs"))
          and config["protected_evaluation_authorized"] is False, "Diagnostic-only scope changed")
    d = config["descriptors"]
    check(d["source_disk_radius_px"] == 10 and d["source_core_radius_px"] == 5
          and d["source_grid_spacing_px"] == 1 and tuple(d["features"]) == FEATURE_NAMES,
          "Fixed feature specification changed")
    check(config["analysis"]["all_feature_rows_sealed_before_reference_analysis"] is True,
          "Features must precede reference analysis")


def prepare(root=ROOT):
    """Bind inputs/source and verify scope; do not call the feature kernel."""
    root = Path(root).resolve()
    config = read(root / CONFIG)
    validate_config(config)
    for key in INPUT_KEYS:
        bound(root, config[key])
    package = read(root / config["paired_inputs"]["path"])
    original = read(root / config["original_comparison"]["path"])
    followup = read(root / config["followup_comparison"]["path"])
    capture = read(root / config["captured_HOU_means"]["path"])
    original_audit = read(root / config["original_comparison_audit"]["path"])
    followup_audit = read(root / config["followup_audit"]["path"])
    check(package["candidate"]["checkpoint"] == original["checkpoint"] == followup["checkpoint"]
          == config["research_control"] and package["protected_evaluation_authorized"] is False,
          "Model/source scope differs")
    check(original["status"] == followup["status"] == "completed"
          and capture["status"] == "completed_exact_reproduction", "Completed producer evidence required")
    check(original_audit["status"] == "pass" and original_audit["discrepancies"] == []
          and original_audit["inputs"]["comparison"] == config["original_comparison"]
          and followup_audit["status"] == "passed"
          and followup_audit["completed"] == config["followup_comparison"], "Independent membership audit differs")
    original_config = read(bound(root, original["config"]))
    check(config["quality_criteria_unchanged"] == original_config["quality"], "Original quality contract changed")
    for report in (original, followup):
        for link in report["source"]:
            bound(root, link)
    maps = {entry["block_id"]: entry["mean_heatmaps"] for entry in capture["blocks"]}
    prior_records = {entry["block_id"]: entry for entry in original["records"]}
    new_records = {entry["block_id"]: entry for entry in followup["records"]}
    entries = [entry for entry in package["blocks"] if entry["block"]["block_id"] in HOU]
    check(tuple(entry["block"]["block_id"] for entry in entries) == HOU
          and sum(len(entry["block"]["frames"]) for entry in entries) == 960, "Complete HOU census differs")
    blocks = []
    for entry in entries:
        validate_context(entry)
        bid = entry["block"]["block_id"]
        prior, new = prior_records[bid], new_records[bid]
        original_native = read(bound(root, prior["variants"]["native"]))
        check(original_native["observations"] == entry["candidate_observations"], "Native control changed")
        stress_link = prior["variants"]["sequence_weak"]
        stress = read(bound(root, stress_link))
        check(stress["block_id"] == bid and stress["variant"] == "sequence_weak"
              and stress["pool_source"] == prior["pool_source"]
              and stress["references_used_in_selection"] is False
              and len(stress["observations"]) == len(entry["candidate_observations"]), "Stress cohort transport differs")
        for link in (maps[bid], new["pool_source"], prior["pool_source"]):
            bound(root, link)
        blocks.append({"block_id": bid, "frames": len(entry["block"]["frames"]),
            "mean_heatmaps": maps[bid], "main_pool": new["pool_source"], "expanded_pool": prior["pool_source"],
            "expanded_choices": stress_link, "native_record": prior["variants"]["native"]})
    result = {"schema_version": "candidate_response_prepared/v0.1", "created_at_utc": stamp(),
        "status": "prepared_no_descriptor_rows_computed", "config": bind(root, root / CONFIG),
        "inputs": {key: config[key] for key in INPUT_KEYS}, "blocks": blocks,
        "source": [bind(root, root / f"src/ball_tracking/{name}.py") for name in SOURCE_NAMES],
        "expected_frames": 960, "expected_main_candidates": 10778, "expected_stress_rows": 960,
        "new_model_calls": 0, "new_features_extracted": 0, "new_selector_runs": 0,
        "reference_analysis_performed": False, "protected_evaluation_access": False,
        "stress_membership_evidence": "Original compact choices and full pool bindings are unchanged; prior independent audit checked every actual selected candidate against its full producer pool."}
    destination = root / OUTPUT / "prepared.json"
    write_once(destination, result)
    print(json.dumps({"event": "response_features_prepared", "prepared": bind(root, destination)}), flush=True)
    return result


def describe_frame(mean, native, pool_record, expanded_choice):
    """Consume actual saved producer records; preserve every observed candidate.

    The caller binds the original full broad pool and independent membership
    audit. Compact stress choices preserve their actual coordinates/missingness;
    this routine does not silently replace them with a nearby .01 candidate.
    """
    check(isinstance(mean, np.ndarray) and mean.dtype == np.float32 and mean.ndim == 2,
          "Saved float32 mean required")
    check(hashlib.sha256(mean.tobytes()).hexdigest() == native["mean_heatmap_sha256"], "Saved mean hash differs")
    check(all(pool_record[field] == native[field] == expanded_choice[field] for field in PROVENANCE_FIELDS),
          "Feature producer native provenance differs")
    check(expanded_choice["source_png"] == native["source_png"], "Stress choice source differs")
    width, height = pool_record["width_px"], pool_record["height_px"]
    pool = pool_record["candidates"]
    check([candidate["candidate_index"] for candidate in pool] == list(range(len(pool))), "Pool order differs")
    for index, original in enumerate(native["candidates"]):
        check(pool[index]["original_index"] == index and all(pool[index].get(key) == value for key, value in original.items()),
              "Native candidate metadata changed")
    check(all(candidate["original_index"] is None for candidate in pool[len(native["candidates"]):]),
          "Nonnative candidate falsely marked native")
    rows = []
    for candidate in pool:
        metadata = {field: deepcopy(candidate[field]) for field in CANDIDATE_FIELDS if field in candidate}
        rows.append({"candidate": metadata,
                     "descriptor": describe_response(mean, [candidate["center_x"], candidate["center_y"]], width, height)})
    selected = expanded_choice["selected_candidate_index"]
    if selected is None:
        check(expanded_choice["state"] == "missing" and expanded_choice["center_xy_px"] is None
              and expanded_choice["native_score"] is None, "Stress missingness differs")
    else:
        check(type(selected) is int and 0 <= selected < expanded_choice["candidate_pool_count"]
              and expanded_choice["state"] == "observed" and expanded_choice["center_xy_px"] is not None,
              "Stress compact selection differs")
    return {"block_id": pool_record["block_id"], **{field: native[field] for field in PROVENANCE_FIELDS},
            "source_png": deepcopy(native["source_png"]), "width_px": width, "height_px": height,
            "temporal_contributions": native["temporal_contributions"],
            "native_selected_candidate_index": native["selected_candidate_index"],
            "main_candidates": rows,
            "expanded_weak_selection": {"observation": deepcopy(expanded_choice),
                "descriptor": describe_response(mean, expanded_choice["center_xy_px"], width, height)},
            "reference_inputs_used": False, "tracking_outputs_changed": False}


def extract(root=ROOT):
    """Require the root's frozen protocol; emit every feature before analysis."""
    root = Path(root).resolve()
    output = root / OUTPUT
    prepared_path = output / "prepared.json"
    frozen_path = output / "prospective_freeze.json"
    frozen = read(frozen_path)
    check(frozen["prepared"] == bind(root, prepared_path), "Root freeze does not bind actual preparation")
    for link in frozen["source"]:
        bound(root, link)
    prepared = read(prepared_path)
    config = read(bound(root, prepared["config"]))
    validate_config(config)
    for link in prepared["source"]:
        bound(root, link)
    for link in prepared["inputs"].values():
        bound(root, link)
    check(not (output / "started.json").exists(), "Prior extraction attempt exists; preserve it without automatic retry")
    package = read(root / prepared["inputs"]["paired_inputs"]["path"])
    entries = {entry["block"]["block_id"]: entry for entry in package["blocks"]}
    identity = {"schema_version": "candidate_response_extraction/v0.1", "started_at_utc": stamp(),
        "prepared": bind(root, prepared_path), "freeze": bind(root, frozen_path), "config": prepared["config"],
        "paired_inputs": prepared["inputs"]["paired_inputs"], "source": prepared["source"],
        "original_comparison_audit": prepared["inputs"]["original_comparison_audit"],
        "followup_audit": prepared["inputs"]["followup_audit"],
        "reference_analysis_performed": False, "new_model_calls": 0, "new_selector_runs": 0,
        "new_training_updates": 0, "new_labels": 0, "new_tracking_outputs": 0, "protected_evaluation_access": False}
    write_once(output / "started.json", identity)
    began = time.perf_counter()
    blocks, frames, candidate_count = [], 0, 0
    try:
        for spec in prepared["blocks"]:
            entry = entries[spec["block_id"]]
            validate_context(entry)
            native = entry["candidate_observations"]
            means = np.load(bound(root, spec["mean_heatmaps"]), mmap_mode="r", allow_pickle=False)
            check(means.shape == (len(native), 432, 768) and means.dtype == np.float32, "Mean map census differs")
            choices = read(bound(root, spec["expanded_choices"]))["observations"]
            pool_path = bound(root, spec["main_pool"])
            # Source bytes remain part of the freeze, even though metadata for
            # selected broad points is reused from their prior membership audit.
            bound(root, spec["expanded_pool"])
            path = output / (hashlib.sha256(spec["block_id"].encode()).hexdigest()[:24] + ".features.jsonl")
            block_candidates, block_frames, statuses = 0, 0, {}
            try:
                with pool_path.open(encoding="utf-8") as source, path.open("x", encoding="utf-8") as target:
                    for index, (line, original, stress) in enumerate(zip(source, native, choices, strict=True)):
                        producer = json.loads(line)
                        check(producer["block_id"] == spec["block_id"]
                              and producer["width_px"] == entry["block"]["source_video"]["width_px"]
                              and producer["height_px"] == entry["block"]["source_video"]["height_px"],
                              "Full producer source context differs")
                        row = describe_frame(means[index], original, producer, stress)
                        target.write(json.dumps(row, allow_nan=False, separators=(",", ":")) + "\n")
                        block_frames += 1
                        block_candidates += len(row["main_candidates"])
                        for value in row["main_candidates"] + [row["expanded_weak_selection"]]:
                            status = value["descriptor"]["status"]
                            statuses[status] = statuses.get(status, 0) + 1
            finally:
                means._mmap.close()
            check(block_frames == spec["frames"], "Feature frame census differs")
            blocks.append({**spec, "features": bind(root, path), "main_candidates": block_candidates,
                           "stress_rows": block_frames, "descriptor_statuses_main_plus_stress": statuses})
            frames += block_frames
            candidate_count += block_candidates
            print(json.dumps({"event": "response_feature_block_saved", "block_id": spec["block_id"],
                              "frames": block_frames, "main_candidates": block_candidates}), flush=True)
        check(frames == 960 and candidate_count == 10778 and len(blocks) == 6,
              "Complete feature census differs")
        result = {**identity, "status": "completed", "completed_at_utc": stamp(),
            "elapsed_seconds": time.perf_counter() - began, "blocks": blocks, "frames": frames,
            "main_candidates": candidate_count, "stress_rows": frames,
            "all_feature_rows_sealed_before_reference_analysis": True}
        write_once(output / "extraction_complete.json", result)
        return result
    except BaseException as error:
        write_once(output / "failed.json", {"identity": identity, "error": str(error),
            "traceback": traceback.format_exc(), "frames_completed": frames,
            "main_candidates_completed": candidate_count, "elapsed_seconds": time.perf_counter() - began,
            "automatic_retry": False})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--extract", action="store_true")
    args = parser.parse_args()
    result = prepare() if args.prepare else extract()
    check("torch" not in sys.modules, "CPU response study unexpectedly imported Torch")
    print(json.dumps({"status": result["status"], "new_model_calls": 0}), flush=True)


if __name__ == "__main__":
    main()
