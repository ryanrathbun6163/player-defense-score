"""Apply the prospective NBA candidate comparison, persist choices, then score.

Existing labels are read only by the scoring phase. The sequence function gets
model candidates, native timestamps and source width, never annotation fields.
All outputs are additive ignored research evidence. No model imports or fitting.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import time
import traceback

from .weak_response_capture import bind, bound, canonical, read, write_once, validate_context
from .weak_response_sequence import choose_sequence, observation_rows
from .weak_response_review import score_block

ROOT = Path(__file__).resolve().parents[2]
CONFIG = "configs/ball_tracking/proposals/weak_response_v0_1.json"
OUT = "data/outputs/ball_tracking/weak_response_v0_1"
FEASIBILITY = ("feasibility_saved_recovery_v0_2", "feasibility_hou_v0_1")
SELECTOR_FIELDS = ("candidate_index", "center_x", "center_y", "native_score", "in_source_bounds", "original_index")


def key(block_id):
    return hashlib.sha256(block_id.encode()).hexdigest()[:24]


def pool_rows(root, path, block, native):
    """Check the actual extraction producer against independent native records."""
    pools = []
    with Path(path).open(encoding="utf-8") as stream:
        for line, original in zip(stream, native, strict=True):
            record = json.loads(line)
            for field in ("source_frame_index", "source_pts_ticks", "time_base", "mean_heatmap_sha256"):
                if record[field] != original[field]:
                    raise ValueError("Extracted candidate/native provenance mismatch: " + field)
            if record["block_id"] != block["block_id"] or record["width_px"] != block["source_video"]["width_px"] or record["height_px"] != block["source_video"]["height_px"]:
                raise ValueError("Candidate source context differs")
            pool = record["candidates"]
            if [c["candidate_index"] for c in pool] != list(range(len(pool))):
                raise ValueError("Candidate index changed")
            for index, old in enumerate(original["candidates"]):
                if pool[index].get("original_index") != index or any(pool[index].get(k) != v for k, v in old.items()):
                    raise ValueError("Original strong candidate changed")
            if any(c.get("original_index") is not None for c in pool[len(original["candidates"]):]):
                raise ValueError("Weak candidate falsely marked native")
            # The complete evidence remains in the bound JSONL producer. Keep
            # only actual selector fields in RAM; do not duplicate provenance GB.
            pools.append([{k: c[k] for k in SELECTOR_FIELDS} for c in pool])
    return pools


def compact_choices(observations):
    return [{**{k: v for k, v in row.items() if k != "candidates"},
             "candidate_pool_count": len(row["candidates"])} for row in observations]


def materialize_choices(body, pools):
    if len(body["observations"]) != len(pools):
        raise ValueError("Choice/pool length mismatch")
    rows = []
    for row, pool in zip(body["observations"], pools, strict=True):
        if row["candidate_pool_count"] != len(pool):
            raise ValueError("Choice/pool candidate census differs")
        rows.append({**{k: v for k, v in row.items() if k != "candidate_pool_count"}, "candidates": pool})
    return rows


def extraction_sources(root, config_binding):
    sources = {}
    for name in FEASIBILITY:
        folder = root / OUT / name
        summary = read(folder / "summary.json")
        completed = read(bound(root, summary["extraction_completion"]))
        prepared = read(bound(root, completed["prepared"]))
        if prepared["config"] != config_binding:
            raise ValueError("Extraction and prospective method parameters differ")
        if prepared["input_package"] != bind(root, root / read(root / CONFIG)["input_package"]):
            raise ValueError("Extraction refers to a different source package")
        if completed["labels_used"] is not False:
            raise ValueError("Candidate extraction must precede label-assisted diagnosis")
        bound(root, prepared["config"]); bound(root, prepared["code"]); bound(root, prepared["source_roles"])
        for record in completed["blocks"]:
            if record["block_id"] in sources:
                raise ValueError("Duplicate extracted context")
            sources[record["block_id"]] = record["pools"]
    return sources


def differences(new, old):
    result = {}
    for name, outcome in (("correct", "matched"), ("wrong", "wrong"), ("missing", "missing")):
        a = {r["source_frame_index"] for r in new["frame_results"] if r["localization_eligible"] and r["outcome"] == outcome}
        b = {r["source_frame_index"] for r in old["frame_results"] if r["localization_eligible"] and r["outcome"] == outcome}
        result[name + "_added"] = sorted(a-b)
        result[name + "_removed"] = sorted(b-a)
    for category, field in (("certain_hidden", "certain_hidden_emissions"),):
        a = {r["source_frame_index"] for r in new["frame_results"] if r[field] > 0}
        b = {r["source_frame_index"] for r in old["frame_results"] if r[field] > 0}
        result[category + "_added"] = sorted(a-b); result[category + "_removed"] = sorted(b-a)
    return result


def execute(root=ROOT):
    root = Path(root).resolve()
    config = read(root / CONFIG)
    package = read(root / config["input_package"])
    inventory = read(root / OUT / "inventory.json")
    for name in FEASIBILITY:
        if not (root / OUT / name / "summary.json").is_file():
            raise ValueError("Completed feasibility required before comparison")
    if config["scope"]["protected_evaluation_authorized"] or package["protected_evaluation_authorized"]:
        raise ValueError("Protected access is closed")
    bound(root, config["research_control"])
    bound(root, inventory["source_roles"])
    if package["candidate"]["checkpoint"] != config["research_control"] or inventory["checkpoint"] != config["research_control"]:
        raise ValueError("Research control changed")
    bound(root, inventory["paired_inputs"])
    frozen = read(root / OUT / "prospective_freeze_v0_2.json")
    if frozen["config"] != bind(root, root / CONFIG):
        raise ValueError("Prospective config changed")
    for record in frozen["source"]:
        bound(root, record)
    sources = extraction_sources(root, frozen["config"])
    entries = package["blocks"]
    if len(entries) != 8 or sum(len(e["block"]["frames"]) for e in entries) != 3662:
        raise ValueError("Complete comparison scope differs")
    output = root / OUT / "comparison_v0_1"
    if output.exists():
        raise ValueError("Prior comparison exists; preserve its attempt")
    output.mkdir(parents=True)
    identity = {"schema_version": "weak_response_comparison/v0.1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": bind(root, root / CONFIG), "paired_inputs": bind(root, root / config["input_package"]),
        "checkpoint": config["research_control"], "inventory": bind(root, root / OUT / "inventory.json"),
        "source": [bind(root, root / f"src/ball_tracking/{name}.py") for name in
            ("weak_response_experiment", "weak_response_sequence", "weak_response_candidates", "weak_response_review", "completion_scoring")],
        "feasibility": [bind(root, root / OUT / name / "summary.json") for name in FEASIBILITY],
        "new_model_calls": 0, "new_training_updates": 0, "new_labels": 0, "protected_evaluation_authorized": False,
        "human_trajectory_acceptance": None, "model_adopted": False}
    write_once(output / "started.json", identity)
    began = time.perf_counter()
    try:
        records = []
        # Persist all automatic choices before calculating any scores.
        for entry in entries:
            validate_context(entry)
            block, native = entry["block"], entry["candidate_observations"]
            path = bound(root, sources[block["block_id"]])
            pools = pool_rows(root, path, block, native)
            times = [float(Fraction(row["source_pts_ticks"]) * Fraction(row["time_base"])) for row in native]
            folder = output / key(block["block_id"])
            folder.mkdir()
            linked = {"block_id": block["block_id"], "pool_source": bind(root, path), "variants": {}}
            write_once(folder / "native.json", {"block_id": block["block_id"], "observations": native})
            linked["variants"]["native"] = bind(root, folder / "native.json")
            for variant in ("sequence_strong", "sequence_weak"):
                used = [[deepcopy(c) for c in pool if c.get("original_index") is not None] for pool in pools] if variant == "sequence_strong" else pools
                chosen, details = choose_sequence(used, times, block["source_video"]["width_px"], config["sequence"])
                observations = observation_rows(native, used, chosen, details, variant, copy_pools=False)
                result_path = folder / (variant + ".json")
                write_once(result_path, {"block_id": block["block_id"], "variant": variant,
                    "pool_source": linked["pool_source"], "observations": compact_choices(observations),
                    "sequence_objective": details["objective"], "references_used_in_selection": False})
                linked["variants"][variant] = bind(root, result_path)
                print(json.dumps({"event": "choices_persisted", "block_id": block["block_id"], "variant": variant}), flush=True)
            records.append(linked)
            del pools, used, observations
        write_once(output / "choices_complete.json", {"identity": identity, "blocks": records,
                   "references_used_in_selection": False, "scores_computed": False})
        summaries = []
        for entry, record in zip(entries, records, strict=True):
            block, native = entry["block"], entry["candidate_observations"]
            pools = pool_rows(root, bound(root, record["pool_source"]), block, native)
            scores = {}
            for variant, link in record["variants"].items():
                body = read(bound(root, link))
                if body["block_id"] != block["block_id"]:
                    raise ValueError("Stored choice context differs")
                if variant == "native":
                    observations, expected = body["observations"], [r["candidates"] for r in native]
                else:
                    if body["variant"] != variant or body["pool_source"] != record["pool_source"]:
                        raise ValueError("Stored choice variant/pool differs")
                    expected = [[c for c in pool if c["original_index"] is not None] for pool in pools] if variant == "sequence_strong" else pools
                    observations = materialize_choices(body, expected)
                scores[variant] = score_block(block, observations, baseline=native, expected_pools=expected)
                write_once(output / key(block["block_id"]) / (variant + "_score.json"), scores[variant])
            # Actual native scoring must reproduce its original saved producer.
            original = read(bound(root, entry["provenance"]["candidate_records"]))
            if scores["native"] != original["score"]:
                raise ValueError("Native scoring differs from original producer")
            summaries.append({"block_id": block["block_id"], "role": block["role"],
                "variants": {name: score["summary"] for name, score in scores.items()},
                "changes_from_native": {name: differences(score, scores["native"]) for name, score in scores.items() if name != "native"},
                "changes_weak_vs_strong": differences(scores["sequence_weak"], scores["sequence_strong"])})
            print(json.dumps({"event": "scored", "block_id": block["block_id"], "counts": {
                name: {k: value["summary"][k] for k in ("matched", "wrong", "missing", "certain_hidden_emitted_points")}
                for name, value in scores.items()}}), flush=True)
        result = {**identity, "status": "completed", "elapsed_seconds": time.perf_counter()-began,
            "records": records, "blocks": summaries, "ball_phase_accepted": False,
            "interpretation": "Fixed inspected-development comparison; per-context gates and human review remain required. No independent test claim."}
        write_once(output / "completed.json", result)
        return result
    except BaseException as error:
        write_once(output / "failed.json", {"identity": identity, "error": str(error), "traceback": traceback.format_exc(),
                    "elapsed_seconds": time.perf_counter()-began})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", required=True)
    parser.parse_args()
    result = execute()
    print(json.dumps({"status": result["status"], "elapsed_seconds": result["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
