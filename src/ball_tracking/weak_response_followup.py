"""One HOU-diagnosed CPU correction: motion/speed factorial and narrow weak pool.

All four arms are declared before execution. Existing v1 controls are reused.
No labels enter the sequence function; every point is an observed pool member.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import traceback

import cv2
import numpy as np

from .weak_response_capture import bind, bound, read, write_once, validate_context, HOU, CONTEXTS
from .weak_response_candidates import components, NATIVE_FIELDS
from .weak_response_sequence import choose_sequence, observation_rows
from .weak_response_experiment import compact_choices, materialize_choices, pool_rows, differences, SELECTOR_FIELDS, key
from .weak_response_review import score_block

ROOT = Path(__file__).resolve().parents[2]
CONFIG = "configs/ball_tracking/proposals/weak_response_followup_v0_1.json"
BASE = "data/outputs/ball_tracking/weak_response_v0_1"
OUTPUT = BASE + "/followup_v0_1"
ARM_NAMES = ("motion_only", "speed_only", "motion_and_speed", "motion_and_speed_narrow_weak")
SOURCE_NAMES = ("weak_response_followup", "weak_response_capture", "weak_response_candidates", "weak_response_sequence",
                "weak_response_experiment", "weak_response_review", "completion_scoring")


def check(value, message):
    if not value:
        raise ValueError(message)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def validate_parameters(config, original):
    check(config["research_control"] == original["research_control"] and config["quality"] == original["quality"],
          "Research control or quality criteria changed")
    check(config["base_sequence"] == original["sequence"], "Original sequence parameters changed")
    expected = {"motion_only": {"motion_cost_weight": .025, "maximum_speed_widths_per_second": 1.5},
                "speed_only": {"motion_cost_weight": .25, "maximum_speed_widths_per_second": 3.0},
                "motion_and_speed": {"motion_cost_weight": .025, "maximum_speed_widths_per_second": 3.0},
                "motion_and_speed_narrow_weak": {"motion_cost_weight": .025, "maximum_speed_widths_per_second": 3.0}}
    check(tuple(config["arms"]) == ARM_NAMES, "Fixed four-arm comparison changed")
    for name in ARM_NAMES:
        check(config["arms"][name]["changes"] == expected[name], "Unplanned parameter change")
        check(config["arms"][name]["pool"] == ("native_plus_0.01" if name.endswith("narrow_weak") else "native_only"),
              "Candidate pool factor changed")
    check(config["main_research_arm"] == "motion_and_speed" and config["main_research_arm_chosen_before_results"] is True,
          "Prospective main research arm changed")
    check(config["extraction"] == {"native_threshold": .3, "additional_threshold": .01, "strict_threshold": True,
          "connectivity": 8, "dedup_source_pixels": 2.0, "retain_native_candidates_exactly": True,
          "local_maxima": False, "candidate_cap": None}, "Narrow extraction recipe changed")
    check(config["protected_evaluation_authorized"] is False and config["new_training_updates"] == config["new_model_calls"] == config["new_labels"] == 0,
          "CPU-only comparison scope changed")


def parameters_for(config, arm):
    check(arm in ARM_NAMES, "Unknown arm")
    return {**deepcopy(config["base_sequence"]), **config["arms"][arm]["changes"]}


def validate_threshold_basis(report, selected_sources):
    """Validate disclosed HOU diagnosis, never an outcome-driven selector input."""
    check(tuple(b["block_id"] for b in report["blocks"]) == HOU, "Threshold choice must use the six HOU episodes only")
    e01 = report["blocks"][0]["methods"]
    check(e01["threshold_0.03"]["union_available"] == 118
          and e01["threshold_0.01"]["union_available"] == e01["threshold_0.01"]["eligible"] == 120,
          "Declared e01 threshold availability evidence changed")
    check(e01["threshold_0.01"]["gained_candidate_availability_frames"] == list(range(194, 204))
          and sorted(set(e01["threshold_0.01"]["gained_candidate_availability_frames"])
                     - set(e01["threshold_0.03"]["gained_candidate_availability_frames"])) == [200, 201],
          "Declared ten e01 recoveries or .03 limitation changed")
    check(all(b["methods"]["threshold_0.01"]["union_available"] * 100 >=
              95 * b["methods"]["threshold_0.01"]["eligible"] for b in report["blocks"]),
          "Narrow .01 native union misses the HOU availability floor")
    rows = selected_sources["rows"]
    check(all(row["block"] in HOU for row in rows), "Only HOU may inform threshold choice")
    hidden = [row for row in rows if row["block"] == HOU[4] and row["change"] == "certain_hidden_added"]
    adverse = [row for row in rows if row["block"] == HOU[4] and row["change"] == "correct_added"
               and row["selection"]["peak"] < .01]
    gains = [row["frame"] for row in rows if row["block"] == HOU[0] and row["change"] == "correct_added"]
    check(gains == list(range(194, 204)), "The demonstrated e01 gains changed")
    check(sorted(row["frame"] for row in hidden) == [4, 5, 22, 23, 24, 25, 26, 27, 214, 215, 216, 217]
          and all(row["selection"]["peak"] < .01 for row in hidden), "Twelve low-peak hidden choices changed")
    check(sorted(row["frame"] for row in adverse) == list(range(14, 20))
          and all(row["nearest_001_component_distance_to_v1_selection"] > 20 for row in adverse),
          "Known six useful low-peak e05 recoveries changed")
    return {"chosen_threshold": .01,
            "basis": "HOU label-assisted recovery preservation and rejection of exact low-peak false emissions; revised from the preserved .03 draft before freeze.",
            "superseded_draft_rule": "Highest nonnative threshold supplying >=95% every HOU episode gave .03; this was valid but does not preserve e01 frames200-201.",
            "counts": [{"block_id": b["block_id"], "eligible": b["methods"]["threshold_0.01"]["eligible"],
                        "native_plus_0.03_available": b["methods"]["threshold_0.03"]["union_available"],
                        "native_plus_0.01_available": b["methods"]["threshold_0.01"]["union_available"]} for b in report["blocks"]],
            "e01_demonstrated_gain_frames": gains,
            "exact_e05_hidden_choices_below_001": [row["frame"] for row in hidden],
            "adverse_e05_real_recoveries_below_001": [row["frame"] for row in adverse],
            "other_hidden_candidates_remain_possible": True,
            "labels_used_for_development_parameter_choice": True, "DET_used": False,
            "availability_is_not_automatic_accuracy": True}


def map_sources(root, inventory):
    captured = read(root / BASE / "capture_v0_1/completed.json")
    check(captured["status"] == "completed_exact_reproduction" and captured["new_model_calls"] == 948,
          "Completed bound HOU capture required")
    hou = {b["block_id"]: b["mean_heatmaps"] for b in captured["blocks"]}
    result = []
    for b in inventory["blocks"]:
        mean = b["saved_mean_maps"] if b["saved_mean_maps"] is not None else hou[b["block_id"]]
        bound(root, mean)
        bound(root, b["original_records"])
        result.append({"block_id": b["block_id"], "mean_heatmaps": mean, "native_records": b["original_records"]})
    check(tuple(b["block_id"] for b in result) == CONTEXTS, "Exact eight-map scope required")
    return result


def prepare(root=ROOT):
    root = Path(root).resolve()
    config = read(root / CONFIG)
    v1 = read(bound(root, config["original_config"]))
    validate_parameters(config, v1)
    for evidence in config["diagnostic_evidence"].values():
        bound(root, evidence)
    threshold_basis = validate_threshold_basis(
        read(root / config["diagnostic_evidence"]["hou_threshold_unions"]["path"]),
        read(root / config["diagnostic_evidence"]["hou_v1_weak_selected_sources"]["path"]))
    prior = read(bound(root, config["original_comparison"]))
    prior_freeze = read(bound(root, config["original_freeze"]))
    check(prior["status"] == "completed" and prior["source"] == prior_freeze["source"], "Original completed source differs")
    for link in prior_freeze["source"]:
        bound(root, link)
    inventory = read(root / BASE / "inventory.json")
    bound(root, inventory["source_roles"])
    package = read(bound(root, inventory["paired_inputs"]))
    check(package["candidate"]["checkpoint"] == config["research_control"], "Research-control binding differs")
    bound(root, config["research_control"])
    check(tuple(e["block"]["block_id"] for e in package["blocks"]) == CONTEXTS
          and sum(len(e["block"]["frames"]) for e in package["blocks"]) == 3662, "Full context scope differs")
    for entry in package["blocks"]:
        validate_context(entry)
    result = {"schema_version": "weak_response_followup_freeze/v0.1", "created_at_utc": stamp(),
        "status": "frozen_before_any_followup_choices_or_scores", "config": bind(root, root / CONFIG),
        "paired_inputs": inventory["paired_inputs"], "checkpoint": config["research_control"],
        "source_roles": inventory["source_roles"], "original_comparison": config["original_comparison"],
        "inventory": bind(root, root / BASE / "inventory.json"), "capture": bind(root, root / BASE / "capture_v0_1/completed.json"),
        "source": [bind(root, root / f"src/ball_tracking/{name}.py") for name in SOURCE_NAMES],
        "maps": map_sources(root, inventory), "threshold_selection": threshold_basis,
        "focused_validation": bind(root, root / BASE / "validation/followup_pre_freeze_tests.json"),
        "tests": bind(root, root / "tests/test_weak_response_followup.py"),
        "development_parameter_choice": "The declared changes use completed HOU development diagnosis. DET is locked application; SAC is training exposed.",
        "new_model_calls": 0, "new_training_updates": 0, "protected_evaluation_authorized": False,
        "new_arms": list(ARM_NAMES), "main_research_arm": config["main_research_arm"]}
    destination = root / OUTPUT / "prospective_freeze.json"
    write_once(destination, result)
    print(json.dumps({"event": "followup_frozen", "freeze": bind(root, destination)}), flush=True)
    return result


def narrow_pool(mean, native_candidates, width, height):
    """Native >.3 first, plus observed >.01 components; source-pixel dedup only."""
    native = components(mean, width, height, .3)
    check(len(native) == len(native_candidates), "Native candidate census differs")
    pool = []
    for index, (actual, saved) in enumerate(zip(native, native_candidates, strict=True)):
        check(saved["candidate_index"] == index and all(actual[k] == saved[k] for k in NATIVE_FIELDS),
              "Native component reconstruction differs")
        pool.append({**deepcopy(saved), "component_index": index, "original_index": index,
                     "extraction": "native_component", "threshold": .3, "extraction_index": index,
                     "extraction_original_index": index, "equivalent_extractions": []})
    weak = components(mean, width, height, .01)
    for index, candidate in enumerate(weak):
        row = {**candidate, "original_index": None, "extraction": "threshold_component", "threshold": .01,
               "extraction_index": index}
        duplicate = next((i for i, kept in enumerate(pool) if math.hypot(
            row["center_x"] - kept["center_x"], row["center_y"] - kept["center_y"]) <= 2.0), None)
        if duplicate is not None:
            pool[duplicate]["equivalent_extractions"].append(row)
        else:
            pool.append({**row, "candidate_index": len(pool), "component_index": len(pool),
                         "extraction_original_index": index, "equivalent_extractions": []})
    return pool, {"native_parity": True, "native_count": len(native), "raw_threshold_0.01_count": len(weak),
                  "retained_weak_count": len(pool) - len(native), "pool_count": len(pool), "labels_used": False}


def extract_block(root, block, native, map_link, destination):
    means = np.load(bound(root, map_link), mmap_mode="r", allow_pickle=False)
    check(means.shape == (len(native), 432, 768) and means.dtype == np.float32, "Saved map shape/dtype differs")
    totals = {"frames": 0, "native_candidates": 0, "raw_weak_candidates": 0, "retained_candidates": 0, "maximum_frame_pool": 0}
    try:
        with Path(destination).open("x", encoding="utf-8") as stream:
            for offset, original in enumerate(native):
                mean = means[offset]
                check(hashlib.sha256(mean.tobytes()).hexdigest() == original["mean_heatmap_sha256"], "Actual mean hash differs")
                pool, diagnostic = narrow_pool(mean, original["candidates"], block["source_video"]["width_px"], block["source_video"]["height_px"])
                emitted = {"block_id": block["block_id"], **{k: original[k] for k in
                    ("source_frame_index", "source_pts_ticks", "time_base", "mean_heatmap_sha256")},
                    "width_px": block["source_video"]["width_px"], "height_px": block["source_video"]["height_px"],
                    "candidates": pool, "diagnostic": diagnostic}
                stream.write(json.dumps(emitted, allow_nan=False) + "\n")
                totals["frames"] += 1
                totals["native_candidates"] += diagnostic["native_count"]
                totals["raw_weak_candidates"] += diagnostic["raw_threshold_0.01_count"]
                totals["retained_candidates"] += len(pool)
                totals["maximum_frame_pool"] = max(totals["maximum_frame_pool"], len(pool))
    finally:
        means._mmap.close()
    return {"block_id": block["block_id"], "mean_heatmaps": map_link, "pools": bind(root, destination), **totals,
            "all_native_candidates_exact": True, "all_mean_hashes_exact": True, "labels_used": False}


def select_arm(native, projected_pools, source_width, config, arm):
    """Candidate-only boundary; annotation records are not arguments."""
    use_weak = config["arms"][arm]["pool"] == "native_plus_0.01"
    used = projected_pools if use_weak else [[c for c in pool if c["original_index"] is not None] for pool in projected_pools]
    seconds = [float(Fraction(row["source_pts_ticks"]) * Fraction(row["time_base"])) for row in native]
    chosen, details = choose_sequence(used, seconds, source_width, parameters_for(config, arm))
    rows = observation_rows(native, used, chosen, details, arm, copy_pools=False)
    return compact_choices(rows), details["objective"]


def publish_review_view(root, result, prior_records, output):
    """Compatibility keys are explicit display aliases, never an adoption claim."""
    aliases = {"sequence_strong": "motion_and_speed", "sequence_weak": "motion_and_speed_narrow_weak"}
    labels = {"native": "Cosine-nine native control", "sequence_strong": "Corrected motion and speed; native candidates",
              "sequence_weak": "Corrected motion and speed; native plus >0.01 candidates"}
    records, blocks = [], []
    summaries = {b["block_id"]: b for b in result["blocks"]}
    for record in result["records"]:
        block_id = record["block_id"]
        folder = output / key(block_id)
        folder.mkdir(parents=True)
        views = {"native": prior_records[block_id]["variants"]["native"]}
        for alias, actual in aliases.items():
            body = read(bound(root, record["variants"][actual]))
            write_once(folder / (alias + ".json"), {**body, "variant": alias, "actual_arm_name": actual,
                       "display_label": labels[alias], "original_choice_record": record["variants"][actual]})
            views[alias] = bind(root, folder / (alias + ".json"))
        records.append({"block_id": block_id, "pool_source": record["pool_source"], "variants": views,
                        "actual_arm_names": {"native": "native", **aliases}})
        summary = summaries[block_id]
        blocks.append({"block_id": block_id, "role": summary["role"],
                       "variants": {"native": summary["controls"]["native"],
                                    **{alias: summary["variants"][actual] for alias, actual in aliases.items()}},
                       "changes_from_native": {alias: summary["changes_from_controls"][actual]["native"] for alias, actual in aliases.items()},
                       "changes_weak_vs_strong": summary["narrow_weak_changes_from_main_strong"]})
    review = {"schema_version": "weak_response_comparison/v0.1", "status": "completed", "records": records, "blocks": blocks,
              "paired_inputs": result["paired_inputs"], "checkpoint": result["checkpoint"], "config": result["config"],
              "source_comparison": bind(root, root / OUTPUT / "completed.json"), "variant_labels": labels,
              "actual_arm_names": {"native": "native", **aliases}, "display_aliases_only": True,
              "main_research_arm": "motion_and_speed", "human_trajectory_acceptance": None, "model_adopted": False,
              "ball_phase_accepted": False, "protected_evaluation_authorized": False}
    write_once(output / "completed.json", review)
    return bind(root, output / "completed.json")


def execute(root=ROOT):
    root = Path(root).resolve()
    output = root / OUTPUT
    frozen = read(output / "prospective_freeze.json")
    config = read(bound(root, frozen["config"]))
    for link in frozen["source"]:
        bound(root, link)
    validate_parameters(config, read(bound(root, config["original_config"])))
    bound(root, frozen["source_roles"]); bound(root, frozen["checkpoint"])
    package = read(bound(root, frozen["paired_inputs"]))
    prior = read(bound(root, frozen["original_comparison"]))
    check(not (output / "started.json").exists(), "Prior followup attempt exists; preserve it without automatic retry")
    check(package["protected_evaluation_authorized"] is False and tuple(e["block"]["block_id"] for e in package["blocks"]) == CONTEXTS,
          "Permitted full context scope differs")
    identity = {"schema_version": "weak_response_followup/v0.1", "created_at_utc": stamp(),
        "freeze": bind(root, output / "prospective_freeze.json"), "config": frozen["config"],
        "paired_inputs": frozen["paired_inputs"], "checkpoint": frozen["checkpoint"], "source": frozen["source"],
        "original_comparison": frozen["original_comparison"], "main_research_arm": config["main_research_arm"],
        "main_research_arm_chosen_before_results": True, "new_model_calls": 0, "new_training_updates": 0,
        "new_labels": 0, "protected_evaluation_authorized": False, "human_trajectory_acceptance": None,
        "model_adopted": False, "ball_phase_accepted": False}
    write_once(output / "started.json", identity)
    began = time.perf_counter()
    try:
        cv2.setNumThreads(1)
        map_links = {b["block_id"]: b["mean_heatmaps"] for b in frozen["maps"]}
        prior_records = {b["block_id"]: b for b in prior["records"]}
        records, extraction = [], []
        for entry in package["blocks"]:
            validate_context(entry)
            block, native = entry["block"], entry["candidate_observations"]
            block_id = block["block_id"]
            folder = output / key(block_id)
            folder.mkdir()
            pool_path = folder / "pools.jsonl"
            extracted = extract_block(root, block, native, map_links[block_id], pool_path)
            extraction.append(extracted)
            pools = pool_rows(root, pool_path, block, native)
            linked = {"block_id": block_id, "pool_source": extracted["pools"], "variants": {}, "scores": {},
                      "controls": prior_records[block_id]["variants"]}
            for arm in ARM_NAMES:
                rows, objective = select_arm(native, pools, block["source_video"]["width_px"], config, arm)
                path = folder / (arm + ".json")
                write_once(path, {"block_id": block_id, "variant": arm, "pool_source": extracted["pools"],
                    "pool_policy": config["arms"][arm]["pool"], "sequence_parameters": parameters_for(config, arm),
                    "observations": rows, "sequence_objective": objective, "references_used_in_selection": False})
                linked["variants"][arm] = bind(root, path)
            records.append(linked)
            print(json.dumps({"event": "followup_choices_persisted", "block_id": block_id,
                              "arms": list(ARM_NAMES), "pool_candidates": extracted["retained_candidates"]}), flush=True)
        check(sum(b["frames"] for b in extraction) == 3662, "Native parity census differs")
        write_once(output / "extraction_complete.json", {"identity": identity, "blocks": extraction,
            "frames": 3662, "all_native_candidates_exact": True, "all_mean_hashes_exact": True, "labels_used": False})
        # Every frame/arm choice exists before this statement and any scoring below.
        write_once(output / "choices_complete.json", {"identity": identity, "blocks": deepcopy(records),
                   "references_used_in_selection": False, "scores_computed": False})
        summaries = []
        for entry, record in zip(package["blocks"], records, strict=True):
            block, native = entry["block"], entry["candidate_observations"]
            folder = output / key(block["block_id"])
            pools = pool_rows(root, bound(root, record["pool_source"]), block, native)
            controls = {}
            for alias, link in record["controls"].items():
                path = bound(root, link)
                controls[alias] = read(path.with_name(alias + "_score.json"))
                # The original completed report is the hash-bound control summary.
                original_summary = next(b for b in prior["blocks"] if b["block_id"] == block["block_id"])["variants"][alias]
                check(controls[alias]["summary"] == original_summary, "Reused control score differs from completed v1")
                record.setdefault("control_scores", {})[alias] = bind(root, path.with_name(alias + "_score.json"))
            scores = {}
            for arm, link in record["variants"].items():
                body = read(bound(root, link))
                check(body["block_id"] == block["block_id"] and body["variant"] == arm
                      and body["pool_source"] == record["pool_source"] and body["sequence_parameters"] == parameters_for(config, arm),
                      "Actual choice transport differs")
                expected = pools if config["arms"][arm]["pool"] == "native_plus_0.01" else [[c for c in pool if c["original_index"] is not None] for pool in pools]
                observations = materialize_choices(body, expected)
                score = score_block(block, observations, baseline=native, expected_pools=expected)
                write_once(folder / (arm + "_score.json"), score)
                record["scores"][arm] = bind(root, folder / (arm + "_score.json"))
                scores[arm] = score
            summaries.append({"block_id": block["block_id"], "role": block["role"],
                "controls": {name: score["summary"] for name, score in controls.items()},
                "variants": {name: score["summary"] for name, score in scores.items()},
                "changes_from_controls": {name: {control: differences(score, baseline) for control, baseline in controls.items()}
                                          for name, score in scores.items()},
                "narrow_weak_changes_from_main_strong": differences(scores["motion_and_speed_narrow_weak"], scores["motion_and_speed"])})
            print(json.dumps({"event": "followup_scored", "block_id": block["block_id"], "counts": {
                name: {k: score["summary"][k] for k in ("matched", "wrong", "missing", "certain_hidden_emitted_points")}
                for name, score in scores.items()}}), flush=True)
        result = {**identity, "status": "completed", "finished_at_utc": stamp(), "elapsed_seconds": time.perf_counter() - began,
            "records": records, "blocks": summaries, "extraction": bind(root, output / "extraction_complete.json"),
            "interpretation": "HOU-informed development correction; DET locked application and SAC training-exposed. No independent test or adoption."}
        write_once(output / "completed.json", result)
        review = publish_review_view(root, result, prior_records, output / "review_comparison")
        write_once(output / "review_view.json", {"comparison": review, "display_aliases_only": True})
        return result
    except BaseException as error:
        write_once(output / "failed.json", {"identity": identity, "error": str(error), "traceback": traceback.format_exc(),
                   "elapsed_seconds": time.perf_counter() - began, "automatic_retry": False})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = parser.parse_args()
    result = prepare() if args.prepare else execute()
    check("torch" not in sys.modules, "CPU followup unexpectedly imported Torch")
    print(json.dumps({"status": result["status"], "new_model_calls": 0}), flush=True)


if __name__ == "__main__":
    main()
