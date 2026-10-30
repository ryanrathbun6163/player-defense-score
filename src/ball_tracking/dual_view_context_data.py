"""Source-bound CPU preparation for the frozen dual-view context experiment.

This module never imports torch or constructs a model. Original 64px caches are
read-only inputs. The new cache holds raw RGB 192px crops, not resized tensors.
Every query retains its own fractional point geometry and its original identity.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import traceback

import numpy as np
from PIL import Image

from .candidate_quality_model import point_geometry as local_geometry

BASE = "data/outputs/ball_tracking/dual_view_context_v0_1"
PREPARATION = BASE + "/preparation/attempt_001/prepared.json"
DESIGN = "data/outputs/ball_tracking/dual_view_context_design_v0_1"
Q = "data/outputs/ball_tracking/candidate_quality_pilot_v0_1"
FRESH = "data/outputs/ball_tracking/fresh_game_diagnostic_v0_1"
FIT_NAMES = ("leave_chi_out", "leave_den_out", "leave_sac_out", "all_nba")
TOKEN_INDICES = [120, 121, 136, 137]


def check(condition, message):
    if not condition:
        raise ValueError(message)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def owned_path(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    check(path.is_relative_to(root), f"Path escapes project: {relative}")
    return path


def read(path):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def read_rows(path):
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def binding(root, path):
    path = owned_path(root, path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for part in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(part)
    return {"path": path.relative_to(Path(root).resolve()).as_posix(),
            "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def verify_binding(root, expected):
    actual = binding(root, expected["path"])
    check(all(actual[key] == expected[key] for key in actual),
          f"Source binding changed: {expected['path']}")
    return actual


def write_once(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def write_rows_once(path, rows):
    with Path(path).open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")


def context_geometry(center_xy, width, height):
    """Pixel-center mapping for PIL 192->224 resize, with no center crop."""
    check(len(center_xy) == 2, "Expected a two-coordinate center")
    x, y = map(float, center_xy)
    check(math.isfinite(x) and math.isfinite(y), "Nonfinite center")
    check(0 <= x < width and 0 <= y < height, "Out-of-bounds center")
    left, top = math.floor(x) - 96, math.floor(y) - 96
    u, v = ((x - left + .5) * 224 / 192 - .5,
            (y - top + .5) * 224 / 192 - .5)
    gx, gy = (u - 6.5) / 14, (v - 6.5) / 14
    col, row = math.floor(gx), math.floor(gy)
    fx, fy = gx - col, gy - row
    tokens = [1 + row * 16 + col, 2 + row * 16 + col,
              17 + row * 16 + col, 18 + row * 16 + col]
    check(tokens == TOKEN_INDICES, "Unexpected context token neighborhood")
    weights = [(1-fx)*(1-fy), fx*(1-fy), (1-fx)*fy, fx*fy]
    check(abs(sum(weights) - 1) < 1e-14 and min(weights) >= 0, "Invalid point weights")
    return {"crop_box": [left, top, left + 192, top + 192],
            "point_input_xy": [u, v], "token_indices": tokens, "weights": weights,
            "complete_source_crop": left >= 0 and top >= 0 and left+192 <= width and top+192 <= height}


def partition_external(queries, targets):
    """Filter roles *after* assigning the indices of the existing local cache."""
    target_map = {r["query_id"]: r for r in targets}
    check(len(target_map) == len(targets), "Duplicate external target IDs")
    check(len({r['query_id'] for r in queries}) == len(queries), "Duplicate external query IDs")
    check(set(target_map) == {r['query_id'] for r in queries}, "External target/query mismatch")
    allowed, missing, omitted = [], [], []
    cache_index = 0
    for query in queries:
        target = target_map[query["query_id"]]
        index = cache_index if query["input_id"] is not None else None
        if index is not None:
            cache_index += 1
        excluded = target.get("source_id") == "sas_det_q1_c02" or query.get("source_id") == "sas_det_q1_c02"
        if excluded:
            omitted.append({"query_id": query["query_id"], "status": "omitted_DET_metadata_only",
                            "original_local_cache_index": index, "target_metadata": target})
        elif index is None:
            check(target.get("missing") is True, "Missing external query must retain missing status")
            missing.append({"query_id": query["query_id"], "status": "missing_no_score",
                            "target_metadata": target})
        else:
            check(target.get("missing") is False, "Observed query is marked missing")
            allowed.append((query, target, index))
    return allowed, missing, omitted, cache_index


def _row(record, original_id, kind, local_path, local_index, target_metadata=None):
    video = record.get("source_video", {})
    width = int(record.get("width_px", video.get("width_px", 0)))
    height = int(record.get("height_px", video.get("height_px", 0)))
    center = record["center_xy_px"]
    local = local_geometry(center, width, height)
    context = context_geometry(center, width, height)
    prefix = {"package": "p:", "external": "e:", "BKN": "b:"}[kind]
    frame = record["source_frame_index"]
    block = record.get("block_id", record.get("source_id"))
    result = {"row_key": prefix + original_id, "original_id": original_id, "kind": kind,
              "source_png": record["source_png"], "center_xy_px": center,
              "width_px": width, "height_px": height,
              "frame_key": record.get("frame_key", f"{block}:{frame}"),
              "frame_id": record.get("frame_id"), "game_id": record.get("game_id"),
              "block_id": block, "source_frame_index": frame,
              "domain": record.get("domain"), "cohort": record.get("cohort", "package" if kind == "package" else "BKN"),
              "native_or_weak": record.get("native_or_weak"),
              "target": record.get("target"), "target_group": record.get("target_group"),
              "reference_category": record.get("reference_category"),
              "local_cache": {"path": local_path, "index": local_index},
              "local_point_weights": local["weights"], "context_point_weights": context["weights"],
              "local_geometry": local, "context_geometry": context,
              "local_padding": not local["complete_source_crop"],
              "context_padding": not context["complete_source_crop"],
              "fit_eligible": kind == "package" and record.get("domain") == "nba" and record.get("target") in (0, 1)}
    if target_metadata is not None:
        result["target_metadata"] = target_metadata
        result["reference_category"] = target_metadata.get("reference_category")
        result["source_role"] = record.get("source_role")
        result["native_or_weak"] = "native" if target_metadata.get("native") is True else "weak" if target_metadata.get("native") is False else None
    return result


def inventory(root, verify=True):
    """Construct the finite query inventory from original, immutable manifests."""
    root = Path(root).resolve()
    sources = {}

    def bind(link):
        value = verify_binding(root, link) if verify else {k: link[k] for k in ("path", "bytes", "sha256")}
        prior = sources.setdefault(value["path"], value)
        check(prior == value, "Conflicting source binding")
        return owned_path(root, value["path"])

    def take(relative):
        return bind(binding(root, relative))

    freeze = read(take(DESIGN + "/design_freeze.json"))
    bind(freeze["protocol"])
    bind(freeze["proposal"])
    workload = read(take(DESIGN + "/population_review/population_workload.json"))
    budget = read(take(DESIGN + "/population_review/final_budget.json"))
    bind(budget["source_census"])
    ids = read(take(DESIGN + "/population_review/score_registry_ids.json"))
    for link in workload["inputs"]:
        bind(link)
    for fit in workload["fits"]:
        for key in ("weights", "manifest", "saved_Q_checkpoint", "saved_Q_scores"):
            bind(fit[key])
    local_caches = workload["reuse"]["crop_caches"][:3]
    for cache in workload["reuse"]["crop_caches"]:
        bind(cache)
    candidates = read_rows(root / Q / "preparation/candidates.jsonl")
    evaluation = read(root / Q / "evaluation/completed.json")
    queries = read_rows(bind(evaluation["queries_registry"]))
    targets = read_rows(bind(evaluation["query_targets"]))
    bind(evaluation["frame_registry"])
    allowed, missing, omitted, old_external_count = partition_external(queries, targets)
    check(old_external_count == 11787, "Original external cache cardinality changed")
    check([r[0]["query_id"] for r in allowed] == ids["allowed_external_query_ids"], "Allowed external order changed")
    check([r["query_id"] for r in missing] == ids["missing_external_query_ids"], "Missing external identities changed")
    check([r["query_id"] for r in omitted] == ids["omitted_DET_metadata_ids"], "Omitted DET identities changed")
    check([r["candidate_id"] for r in candidates] == ids["original_package_ids"], "Package order changed")
    bkn = read_rows(root / FRESH / "analysis/candidates.jsonl")
    check([r["candidate_id"] for r in bkn] == ids["BKN_candidate_ids"], "BKN order changed")
    bkn_inputs = read_rows(root / FRESH / "attempt_001/Q_inputs.jsonl")
    bkn_by_id = {r["candidate_id"]: r for r in bkn_inputs}
    check(len(bkn_by_id) == 3480 and set(bkn_by_id) == set(ids["BKN_candidate_ids"]), "BKN cache inventory mismatch")
    records = [_row(r, r["candidate_id"], "package", local_caches[0]["path"], i) for i, r in enumerate(candidates)]
    records.extend(_row(q, q["query_id"], "external", local_caches[1]["path"], i, t) for q, t, i in allowed)
    for r in bkn:
        original = bkn_by_id[r["candidate_id"]]
        check(original["source_png"] == r["source_png"], "BKN source binding mismatch")
        converted = _row(r, r["candidate_id"], "BKN", local_caches[2]["path"], original["cache_index"])
        check(converted["local_geometry"] == original["geometry"], "BKN saved point geometry mismatch")
        records.append(converted)
    rows = {}
    for i, record in enumerate(records):
        record["context_cache_index"] = i
        check(record["row_key"] not in rows, "Duplicate canonical row identity")
        rows[record["row_key"]] = record

    bkn_completed = read(take(FRESH + "/attempt_001/completed.json"))
    bkn_score_link = next(v for v in bkn_completed["outputs"] if v["path"].endswith("/Q_scores.jsonl"))
    bkn_scores = read_rows(bind(bkn_score_link))
    external_scores = read_rows(root / Q / "attempt_005/all_nba/development_scores.jsonl")
    external_control_map = {r["query_id"]: r["quality_logit"] for r in external_scores}
    for record in omitted:
        record["saved_Q_control_metadata_only"] = external_control_map[record["query_id"]]
    fits = {}
    for frozen in workload["fits"]:
        name = frozen["name"]
        manifest = read(root / frozen["manifest"]["path"])
        old_weights = read_rows(root / frozen["weights"]["path"])
        weights = [{"row_key": "p:" + w["candidate_id"], "target": rows["p:" + w["candidate_id"]]["target"],
                    "objective_weight": w["objective_weight"], "training_multiplier": w["training_multiplier"]} for w in old_weights]
        weight_keys = {w["row_key"] for w in weights}
        check(len(weight_keys) == len(weights) == frozen["fit_candidates"], "Fit membership count mismatch")
        check(abs(sum(w["objective_weight"] for w in weights) - 1) < 1e-10, "Original objective weights do not sum to one")
        for w in weights:
            row = rows[w["row_key"]]
            check(row["fit_eligible"] and row["game_id"] in manifest["fit_game_ids"], "Forbidden fitting row")
            check(w["training_multiplier"] == w["objective_weight"] * len(weights), "Original training multiplier changed")
        held = set(manifest["held_out_game_ids"])
        package_score = ["p:" + r["candidate_id"] for r in candidates if name == "all_nba" or r["game_id"] in held]
        union = weight_keys | set(package_score)
        capture = [{"name": "package", "row_keys": ["p:" + r["candidate_id"] for r in candidates if "p:" + r["candidate_id"] in union]}]
        scores = [{"name": "package_all" if name == "all_nba" else "package_held", "row_keys": package_score,
                   "role": "fit_and_secondary_diagnostic" if name == "all_nba" else "scorer_out_of_fold"}]
        saved = {"p:" + r["candidate_id"]: float(r["quality_logit"]) for r in read_rows(root / frozen["saved_Q_scores"]["path"])}
        if name == "all_nba":
            for group, keys, role in (("external", ["e:" + q["query_id"] for q, _, _ in allowed], "development_and_historical_no_selection"),
                                      ("BKN", ["b:" + r["candidate_id"] for r in bkn], "diagnostic_development_no_selection")):
                capture.append({"name": group, "row_keys": keys})
                scores.append({"name": group, "row_keys": keys, "role": role})
            saved.update({"e:" + r["query_id"]: float(r["quality_logit"]) for r in external_scores if "e:" + r["query_id"] in rows})
            saved.update({"b:" + r["candidate_id"]: float(r["quality_logit"]) for r in bkn_scores})
        else:
            scores.append({"name": "training_health", "row_keys": [w["row_key"] for w in weights], "role": "in_sample_training_health_only"})
        check(len(capture[0]["row_keys"]) == frozen["needed_local_frozen_feature_rows_fit_union_package_score"], "Capture union mismatch")
        check(len(package_score) == frozen["package_score_candidates"], "Package scoring membership mismatch")
        check(set(saved) <= set(k for g in capture for k in g["row_keys"]), "Control scores outside capture population")
        check(all(math.isfinite(v) for v in saved.values()), "Nonfinite saved control score")
        fits[name] = {"weights": weights, "capture_groups": capture, "score_groups": scores,
                      "saved_Q_checkpoint": frozen["saved_Q_checkpoint"], "saved_Q_scores": saved,
                      "fit_game_ids": manifest["fit_game_ids"], "held_out_game_ids": manifest["held_out_game_ids"],
                      "original_weights": frozen["weights"], "original_manifest": frozen["manifest"]}
    result = {"rows": rows, "fits": fits, "caches": {"local": local_caches},
              "source_bindings": list(sources.values()), "missing_external": missing, "omitted_DET": omitted}
    result["counts"] = validate_inventory(result)
    return result


def validate_inventory(data):
    rows, fits = data["rows"], data["fits"]
    check(Counter(r["kind"] for r in rows.values()) == {"package": 19632, "external": 11769, "BKN": 3480}, "Canonical row census changed")
    check(list(fits) == list(FIT_NAMES), "Unexpected fitting sequence")
    check(len(data["missing_external"]) == 11 and len(data["omitted_DET"]) == 18, "Missing/DET metadata census changed")
    forbidden = {"e:" + r["query_id"] for r in data["missing_external"] + data["omitted_DET"]}
    check(not forbidden.intersection(rows), "Missing or DET query leaked into scored rows")
    check([r["context_cache_index"] for r in rows.values()] == list(range(len(rows))), "Context cache row order changed")
    for key, row in rows.items():
        check(row["row_key"] == key, "Canonical identity mismatch")
        check(row["local_geometry"] == local_geometry(row["center_xy_px"], row["width_px"], row["height_px"]), "Local geometry changed")
        check(row["context_geometry"] == context_geometry(row["center_xy_px"], row["width_px"], row["height_px"]), "Context geometry changed")
        check(row["local_point_weights"] == row["local_geometry"]["weights"] and row["context_point_weights"] == row["context_geometry"]["weights"], "Fractional point weights changed")
    capture_rows = capture_batches = score_rows = score_batches = training_rows = updates = 0
    for fit in fits.values():
        weight_keys = [w["row_key"] for w in fit["weights"]]
        check(len(weight_keys) == len(set(weight_keys)), "Duplicate fitting identity")
        check(all(rows[k]["fit_eligible"] and rows[k]["game_id"] in fit["fit_game_ids"] for k in weight_keys), "Invalid fitting source role")
        for kind in ("capture_groups", "score_groups"):
            flat = []
            for group in fit[kind]:
                keys = group["row_keys"]
                check(keys and set(keys) <= set(rows), "Unknown or empty group")
                flat.extend(keys)
                if kind == "capture_groups":
                    capture_rows += len(keys)
                    capture_batches += math.ceil(len(keys) / 32)
                else:
                    score_rows += len(keys)
                    score_batches += math.ceil(len(keys) / 32)
            check(len(flat) == len(set(flat)), "Duplicate query presentation within a fit stream")
        check(set(weight_keys) <= {k for g in fit["capture_groups"] for k in g["row_keys"]}, "Missing fitting capture")
        check({k for g in fit["score_groups"] for k in g["row_keys"]} == {k for g in fit["capture_groups"] for k in g["row_keys"]}, "Scoring/capture identity mismatch")
        training_rows += len(weight_keys) * 6 * 2
        updates += math.ceil(len(weight_keys) / 32) * 6 * 2
    counts = {"canonical_rows": len(rows), "package": 19632, "external": 11769, "BKN": 3480,
              "missing_external": 11, "omitted_DET": 18, "capture_rows": capture_rows,
              "capture_batches": capture_batches, "final_scores_two_arms": score_rows * 2,
              "final_scoring_batches_two_arms": score_batches * 2,
              "training_presentations_two_arms": training_rows, "training_updates_two_arms": updates}
    check((capture_rows, capture_batches, score_rows*2, score_batches*2, training_rows, updates) ==
          (88742, 2776, 177484, 5554, 630864, 19740), f"Frozen workload mismatch: {counts}")
    return counts


def make_context_cache(root, destination, rows, local_caches, progress=print):
    """Decode only allowed sources; independently verify every reused local crop."""
    root, destination = Path(root).resolve(), Path(destination)
    check(not destination.exists(), "Context cache already exists")
    groups = defaultdict(list)
    for record in rows.values():
        groups[record["source_png"]["path"]].append(record)
    locals_by_path = {}
    for link in local_caches:
        verify_binding(root, link)
        cache = np.load(root / link["path"], mmap_mode="r", allow_pickle=False)
        check(list(cache.shape) == link["shape"] and str(cache.dtype) == "uint8", "Invalid original local cache header")
        locals_by_path[link["path"]] = cache
    context = np.lib.format.open_memmap(destination, mode="w+", dtype=np.uint8, shape=(len(rows), 192, 192, 3))
    sources, checked = [], 0
    try:
        for number, (relative, group) in enumerate(groups.items(), 1):
            source = group[0]["source_png"]
            check(all(r["source_png"] == source for r in group), "Conflicting PNG source bindings")
            source_binding = verify_binding(root, source)
            with Image.open(root / relative) as opened:
                image = opened.convert("RGB")
                if source.get("rgb_sha256"):
                    check(hashlib.sha256(image.tobytes()).hexdigest() == source["rgb_sha256"], "Source RGB checksum mismatch")
                for record in group:
                    check(image.size == (record["width_px"], record["height_px"]), "Source dimensions changed")
                    old = record["local_cache"]
                    reference = np.asarray(image.crop(tuple(record["local_geometry"]["crop_box"])), dtype=np.uint8)
                    check(np.array_equal(reference, locals_by_path[old["path"]][old["index"]]),
                          f"Original local cache disagrees with source: {record['row_key']}")
                    context[record["context_cache_index"]] = np.asarray(image.crop(tuple(record["context_geometry"]["crop_box"])), dtype=np.uint8)
                    checked += 1
            sources.append(source_binding)
            if number % 250 == 0 or number == len(groups):
                progress(json.dumps({"status": "preparing_CPU_crops", "source_pngs_done": number,
                                     "source_pngs_total": len(groups), "query_crops_done": checked}), flush=True)
        context.flush()
    finally:
        del context
        locals_by_path.clear()
    return {"source_pngs": sources, "images_decoded": len(groups), "local_crops_exactly_verified": checked,
            "context_crops_written": checked, "new_model_calls": 0, "torch_imported": False}


def prepare(root, destination=None):
    root = Path(root).resolve()
    destination = owned_path(root, destination or str(Path(PREPARATION).parent))
    check(destination.is_relative_to(root / BASE / "preparation"), "Preparation output outside its owned directory")
    destination.mkdir(parents=True, exist_ok=False)
    write_once(destination / "started.json", {"status": "started_CPU_preparation", "utc": stamp(), "new_model_calls": 0})
    try:
        data = inventory(root)
        data["caches"]["context"] = {"path": (destination / "context_crops.npy").relative_to(root).as_posix(),
                                         "shape": [len(data["rows"]), 192, 192, 3], "dtype": "uint8"}
        crop_receipt = make_context_cache(root, destination / "context_crops.npy", data["rows"], data["caches"]["local"])
        data["caches"]["context"].update(binding(root, destination / "context_crops.npy"))
        data["source_bindings"].extend(crop_receipt.pop("source_pngs"))
        # The independent BKN point-weight cache must agree at every original index.
        old_bkn_weights = np.load(root / FRESH / "attempt_001/Q_point_weights.npy", allow_pickle=False)
        for row in data["rows"].values():
            if row["kind"] == "BKN":
                check(np.array_equal(np.asarray(row["local_point_weights"]), old_bkn_weights[row["local_cache"]["index"]]), "BKN original point-weight cache mismatch")
        write_rows_once(destination / "rows.jsonl", data["rows"].values())
        write_once(destination / "fits.json", data["fits"])
        write_once(destination / "metadata_only.json", {"missing_external": data["missing_external"], "omitted_DET": data["omitted_DET"]})
        write_once(destination / "source_bindings.json", data["source_bindings"])
        write_once(destination / "crop_verification.json", crop_receipt)
        manifest = {"schema_version": "dual_view_context_preparation/v0.1", "status": "completed_CPU_preparation",
                    "utc": stamp(), "counts": data["counts"], "caches": data["caches"],
                    "rows": binding(root, destination / "rows.jsonl"), "fits": binding(root, destination / "fits.json"),
                    "metadata_only": binding(root, destination / "metadata_only.json"),
                    "source_bindings": binding(root, destination / "source_bindings.json"),
                    "crop_verification": binding(root, destination / "crop_verification.json"),
                    "implementation": binding(root, "src/ball_tracking/dual_view_context_data.py"),
                    "no_forward_deduplication": True, "new_model_calls": 0, "training_updates": 0,
                    "crop_cache_semantics": "Raw RGB uint8 192px; worker resizes directly to224; no center crop. Original64caches reused byte-for-byte."}
        write_once(destination / "prepared.json", manifest)
        return manifest
    except BaseException as exc:
        write_once(destination / "failed.json", {"status": "failed_CPU_preparation_preserved", "utc": stamp(),
                                                "error": str(exc), "traceback": traceback.format_exc(), "new_model_calls": 0})
        raise


def load_prepared(root, verify=True, path=PREPARATION):
    root = Path(root).resolve()
    manifest_path = owned_path(root, path)
    manifest = read(manifest_path)
    check(manifest["status"] == "completed_CPU_preparation", "Preparation incomplete")
    links = [manifest[k] for k in ("rows", "fits", "metadata_only", "source_bindings", "crop_verification", "implementation")]
    if verify:
        for link in links:
            verify_binding(root, link)
    records = read_rows(root / manifest["rows"]["path"])
    rows = {r["row_key"]: r for r in records}
    check(len(rows) == len(records), "Duplicate stored row identity")
    metadata = read(root / manifest["metadata_only"]["path"])
    sources = read(root / manifest["source_bindings"]["path"])
    if verify:
        for link in sources:
            verify_binding(root, link)
        for link in [manifest["caches"]["context"]] + manifest["caches"]["local"]:
            verify_binding(root, link)
            cache = np.load(root / link["path"], mmap_mode="r", allow_pickle=False)
            check(list(cache.shape) == link["shape"] and str(cache.dtype) == link["dtype"], "Cache header disagrees with manifest")
            del cache
    result = {"manifest": manifest, "prepared_binding": binding(root, manifest_path), "rows": rows,
              "fits": read(root / manifest["fits"]["path"]), "caches": manifest["caches"],
              "source_bindings": sources, **metadata}
    check(validate_inventory(result) == manifest["counts"], "Preparation workload changed")
    result["counts"] = manifest["counts"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "verify", "inventory"))
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--destination")
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.root, args.destination)
    elif args.command == "verify":
        result = load_prepared(args.root)["counts"]
    else:
        result = inventory(args.root)["counts"]
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
