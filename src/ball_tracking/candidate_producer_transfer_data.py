"""Bound producer-transfer inputs; CPU crops only, never Torch/model execution.

Existing quality caches retain their original row order. New candidates share
pixels only for identical source/frame/PNG/floor-crop identities; fractional
point weights remain query-specific. Labels never enter the image batch API.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import traceback

import numpy as np
from PIL import Image

from . import candidate_quality_data as original
from .candidate_quality_model import point_geometry

ROOT = Path(__file__).resolve().parents[2]
BASE = Path("data/outputs/ball_tracking/candidate_producer_transfer_v0_1")
OUTPUT = BASE / "preparation/attempt_001"
CONFIG = Path("configs/ball_tracking/proposals/candidate_producer_transfer_v0_1.json")
DESIGN = Path("data/outputs/ball_tracking/candidate_producer_transfer_design_v0_1")
OLD = Path("data/outputs/ball_tracking/candidate_quality_pilot_v0_1")
SEED, BATCH_SIZE, CYCLES = 20261028, 32, 6
check = original.require
binding, verify_binding = original.binding, original.verify_binding
read, write = original.read_json, original.write_json


def rows(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def dimensions(row):
    if "width_px" in row:
        return row["width_px"], row["height_px"]
    return row["source_video"]["width_px"], row["source_video"]["height_px"]


def crop_identity(row, geometry):
    """Source identity plus exact pixel window; never just a matching PNG name."""
    png = row["source_png"]
    return (row.get("source_video_sha256", row.get("source_video", {}).get("sha256")),
            row["source_frame_index"], png["path"], png["sha256"], png["rgb_sha256"],
            *dimensions(row), *geometry["crop_box"])


def make_routes(old_candidates, queries, additions):
    """Produce observable-only routes, preserving every raw candidate/query ID."""
    routes, route_ids, known_crops, new_crops, new_rows = [], set(), {}, {}, []

    def add(item, key, cache, index, geometry):
        check(key not in route_ids, "Duplicate raw input identity")
        route_ids.add(key)
        routes.append({"input_key": key, "cache": cache, "index": index,
                       "source_png": item.get("source_png"),
                       "center_xy_px": item.get("center_xy_px"),
                       "dimensions": list(dimensions(item)),
                       "crop_box": geometry["crop_box"] if geometry else None,
                       "point_weights": geometry["weights"] if geometry else None,
                       "missing": geometry is None})

    for index, item in enumerate(old_candidates):
        geometry = point_geometry(item["center_xy_px"], *dimensions(item))
        add(item, item["candidate_id"], "old_training", index, geometry)
        known_crops.setdefault(crop_identity(item, geometry), index)
    emitted = 0
    for item in queries:
        if item["input_id"] is None:
            add(item, item["query_id"], None, None, None)
        else:
            geometry = point_geometry(item["center_xy_px"], *dimensions(item))
            add(item, item["query_id"], "old_evaluation", emitted, geometry)
            emitted += 1
    reused_old = reused_new = 0
    for item in additions:
        geometry = point_geometry(item["center_xy_px"], *dimensions(item))
        key = crop_identity(item, geometry)
        if key in known_crops:
            cache, index = "old_training", known_crops[key]
            reused_old += 1
        elif key in new_crops:
            cache, index = "added", new_crops[key]
            reused_new += 1
        else:
            cache, index = "added", len(new_rows)
            new_crops[key] = index
            new_rows.append(item)
        add(item, item["candidate_id"], cache, index, geometry)
    return routes, new_rows, {"reused_old_crops": reused_old,
                             "reused_within_added_crops": reused_new,
                             "new_unique_crops": len(new_rows),
                             "missing_queries": len(queries) - emitted}


def validate_population(old_candidates, union, additions, novelty):
    old_nba = [r for r in old_candidates if r["domain"] == "nba"]
    check(len({r["candidate_id"] for r in old_candidates + additions}) == len(old_candidates) + len(additions),
          "Candidate IDs collide")
    check(len(union) == len(old_nba) + len(additions), "Union size differs")
    check(len({r["training_row_key"] for r in union}) == len(union), "Training IDs collide")
    for index, (row, source) in enumerate(zip(union, old_nba + additions, strict=True)):
        pop = "cosine_current" if index < len(old_nba) else "alternate_added"
        check(row["producer_population"] == pop and row["training_row_key"] == pop + "|" + source["candidate_id"],
              "Training namespace differs")
        check({k: v for k, v in row.items() if k not in ("producer_population", "training_row_key")} == source,
              "Original row/target/order changed")
        check(row["domain"] == "nba" and row["game_id"] in original.NBA_GAMES,
              "External source entered union")
    check([r["candidate_id"] for r in additions] == [r["candidate_id"] for r in novelty],
          "Novelty order/identity differs")
    for item, evidence in zip(additions, novelty, strict=True):
        check(item["target"] in (0, 1) and evidence["role_screen_eligible"] is True
              and evidence["new_exact_point_vs_current_and_history"] is True,
              "Unpermitted added target/role/novelty")


def validate_fit(union, plan, weights, schedules):
    """Exact fitting games/order, inherited objective and fixed sampled cycles."""
    fit = plan["fit"]
    check(fit in original.FIT_GAMES and tuple(plan["fit_games"]) == original.FIT_GAMES[fit],
          "Fit source membership differs")
    eligible = [r for r in union if r["game_id"] in plan["fit_games"] and r["target"] is not None]
    expected, _ = original.fit_weights(union, tuple(plan["fit_games"]))
    check(len(eligible) == plan["augmented_known_candidates"], "Known fit size differs")
    check(len(weights) == len(eligible), "Weight membership differs")
    for item, expected_item, source in zip(weights, expected, eligible, strict=True):
        check(all(item[key] == value for key, value in expected_item.items()), "Weight formula/scale differs")
        check(item["training_row_key"] == source["training_row_key"]
              and item["candidate_id"] == source["candidate_id"], "Weight row order differs")
    quota = sum(r["producer_population"] == "cosine_current" for r in eligible)
    check(quota == plan["original_known_candidates"] == plan["draws_per_round"], "Original draw quota differs")
    keys = [r["training_row_key"] for r in eligible]
    batch_sizes = [min(BATCH_SIZE, quota - start) for start in range(0, quota, BATCH_SIZE)]
    check(plan["batch_sizes_per_round"] == batch_sizes and len(schedules) == CYCLES, "Batch/cycle contract differs")
    visits = Counter()
    for cycle, schedule in enumerate(schedules, 1):
        order = keys.copy()
        random.Random(SEED + cycle).shuffle(order)
        check(schedule["fit"] == fit and schedule["round"] == cycle
              and schedule["seed"] == SEED + cycle and schedule["population"] == len(keys)
              and schedule["quota"] == quota and schedule["batch_sizes"] == batch_sizes
              and schedule["training_row_keys"] == order[:quota], "Frozen schedule/source exclusion differs")
        visits.update(schedule["training_row_keys"])
    check(set(visits) == set(keys) and min(visits.values()) >= 1, "Some eligible inputs are never seen")
    check(plan["optimizer_updates"] == CYCLES * len(batch_sizes)
          and plan["training_presentations"] == CYCLES * quota, "Fit budget differs")
    return {"known": len(keys), "updates": CYCLES * len(batch_sizes),
            "presentations": CYCLES * quota, "minimum_visits": min(visits.values())}


def validate_scoring_plan(old_candidates, queries, additions, scoring):
    expected = []
    for fit, game in zip(tuple(original.FIT_GAMES)[:3], original.NBA_GAMES, strict=True):
        for owner, population, source in (("new_treatment", "original_held_NBA", old_candidates),
                                          ("new_treatment", "added_held_challenge", additions),
                                          ("saved_Q_control", "added_held_challenge", additions)):
            ids = [r["candidate_id"] for r in source if r["game_id"] == game]
            expected.append((fit, owner, population, game, "candidate_id", ids))
    expected += [("all_nba", "new_treatment", "NFHS_secondary", None, "candidate_id",
                  [r["candidate_id"] for r in old_candidates if r["domain"] == "nfhs"]),
                 ("all_nba", "new_treatment", "original_external_registry", None, "query_id",
                  [r["query_id"] for r in queries if r["input_id"] is not None])]
    check(len(expected) == len(scoring), "Scoring groups differ")
    for actual, item in zip(scoring, expected, strict=True):
        fit, owner, population, game, field, ids = item
        check((actual["fit"], actual["owner"], actual["population"], actual.get("game_id"), actual["id_field"], actual["ids"])
              == item and actual["forwards"] == math.ceil(len(ids) / BATCH_SIZE),
              "Scoring ownership/order/source exclusion/missing contract differs")
    return {"forwards": sum(r["forwards"] for r in scoring), "presentations": sum(len(r["ids"]) for r in scoring)}


def materialize_added_crops(root, items, destination):
    """Decode only new source crops; check exact original CPU preprocessing parity."""
    from .nba_appearance_feature_screen import crop_and_preprocess
    check(not destination.exists(), "Refuse to replace a crop cache")
    groups = defaultdict(list)
    for index, item in enumerate(items):
        groups[item["source_png"]["path"]].append((index, item))
    array = np.empty((len(items), 64, 64, 3), dtype=np.uint8)
    receipts = []
    for members in groups.values():
        link = members[0][1]["source_png"]
        check(all(row["source_png"] == link and dimensions(row) == dimensions(members[0][1]) for _, row in members),
              "Conflicting source image binding")
        path = verify_binding(root, link)
        with Image.open(path) as source:
            image = source.convert("RGB")
            check(image.size == dimensions(members[0][1]), "Source image dimensions differ")
            check(hashlib.sha256(image.tobytes()).hexdigest() == link["rgb_sha256"], "Decoded source RGB differs")
            for index, item in members:
                geometry = point_geometry(item["center_xy_px"], *image.size)
                crop = image.crop(tuple(geometry["crop_box"]))
                array[index] = np.asarray(crop, dtype=np.uint8)
                direct = crop_and_preprocess(image, item["center_xy_px"])[2]
                cached = crop_and_preprocess(crop, [32., 32.])[2]
                check(np.array_equal(direct, cached), "Original/cache CPU preprocessing differs")
                receipts.append({"candidate_id": item["candidate_id"], "cache_index": index,
                                 "crop_rgb_sha256": hashlib.sha256(array[index].tobytes()).hexdigest(),
                                 "preprocessed_sha256": hashlib.sha256(cached.tobytes()).hexdigest(),
                                 "exact_original_preprocess_equal": True})
    with destination.open("xb") as stream:
        np.save(stream, array, allow_pickle=False)
    return {"decoded_source_pngs": len(groups), "new_crops": len(items),
            "parity_checked_crops": len(receipts), "max_absolute_preprocess_difference": 0.0,
            "rows": sorted(receipts, key=lambda r: r["cache_index"])}


def _read_design(root):
    links = {}

    def bound(link):
        if link["path"] in links:
            check(links[link["path"]] == {k: link[k] for k in ("path", "bytes", "sha256")}, "Conflicting bindings")
            return root / link["path"]
        path = verify_binding(root, link)
        links[link["path"]] = {k: link[k] for k in ("path", "bytes", "sha256")}
        return path

    config = read(root / CONFIG)
    bound(binding(root, root / CONFIG))
    bound(config["protocol"])
    for link in config["input_bindings"]:
        bound(link)
    population = read(bound(config["population"]["manifest"]))
    for link in population["files"].values():
        bound(link)
    workload = read(root / DESIGN / "feasibility/workload.json")
    for link in workload["bindings"]:
        bound(link)
    check(config["counts"] == workload["counts"], "Declared workload differs")
    old_link = links[(OLD / "preparation/candidates.jsonl").as_posix()]
    union_link = population["files"]["union_candidates.jsonl"]
    added_link = population["files"]["added_candidates.jsonl"]
    novelty_link = population["files"]["added_novelty.jsonl"]
    query_link = next(link for path, link in links.items() if path.endswith("point_preparation_v0_1/attempt_003/queries.jsonl"))
    score_link = workload["scoring_plan"]
    old, union, added, novelty, queries, scoring = [rows(bound(link)) if name != "scoring" else read(bound(link))
        for name, link in (("old", old_link), ("union", union_link), ("added", added_link),
                          ("novelty", novelty_link), ("queries", query_link), ("scoring", score_link))]
    validate_population(old, union, added, novelty)
    check((len(old), len(union), len(added), len(queries)) == (19632, 19274, 461, 11798), "Finite registry counts differ")
    fit_records, fit_inputs = {}, {}
    for plan in workload["plans"]:
        weight_rows = rows(bound(plan["weights"]))
        schedule_links = [r["schedule"] for r in plan["round_details"]]
        schedules = [read(bound(link)) for link in schedule_links]
        bound(plan["exposure_rows"])
        validate_fit(union, plan, weight_rows, schedules)
        fit_records[plan["fit"]] = {"plan": plan, "weights": plan["weights"], "schedules": schedule_links,
                                     "exposure": plan["exposure_rows"]}
        fit_inputs[plan["fit"]] = {"plan": plan, "weights": weight_rows, "schedules": schedules}
    check(tuple(fit_records) == tuple(original.FIT_GAMES), "Four-fit order differs")
    check(validate_scoring_plan(old, queries, added, scoring) == {"forwards": 1014, "presentations": 32341},
          "Scoring budget differs")
    cache_links = {name: links[(OLD / "attempt_005" / filename).as_posix()] for name, filename in
                   (("old_training", "training_crops.npy"), ("old_evaluation", "evaluation_crops.npy"))}
    sources = {"original_candidates": old_link, "union_candidates": union_link, "added_candidates": added_link,
               "queries": query_link, "scoring_plan": score_link}
    return old, union, added, queries, scoring, fit_records, fit_inputs, cache_links, sources, list(links.values())


def prepare(root=ROOT, output_dir=None):
    root = Path(root).resolve()
    destination = Path(output_dir).resolve() if output_dir is not None else root / OUTPUT
    check(destination.is_relative_to(root), "Preparation must stay inside project")
    destination.mkdir(parents=True, exist_ok=False)
    write(destination / "started.json", {"status": "CPU_preparation_started", "at_utc": datetime.now(timezone.utc).isoformat()})
    caches = {}
    try:
        old, union, added, queries, scoring, fits, _, cache_links, sources, inputs = _read_design(root)
        routes, new_items, crop_counts = make_routes(old, queries, added)
        check(crop_counts["reused_old_crops"] == 9 and crop_counts["missing_queries"] == 11,
              "Frozen crop overlap/missing census differs")
        for name, link in cache_links.items():
            caches[name] = np.load(root / link["path"], mmap_mode="r", allow_pickle=False)
            expected = 19632 if name == "old_training" else 11787
            check(caches[name].shape == (expected, 64, 64, 3) and caches[name].dtype == np.uint8
                  and not caches[name].flags.writeable, "Original read-only cache header differs")
        pixel_receipt = materialize_added_crops(root, new_items, destination / "added_crops.npy")
        cache_links["added"] = binding(root, destination / "added_crops.npy")
        original.write_jsonl(destination / "input_routes.jsonl", routes)
        write(destination / "pixel_validation.json", pixel_receipt)
        original.write_jsonl(destination / "new_crop_rows.jsonl", new_items)
        prepared = {"schema_version": "candidate_producer_transfer_preparation/v0.1",
            "status": "prepared_CPU_inputs_no_model_calls", "at_utc": datetime.now(timezone.utc).isoformat(),
            "sources": sources, "fits": fits, "caches": cache_links,
            "cache_shapes": {"old_training": [19632, 64, 64, 3], "old_evaluation": [11787, 64, 64, 3],
                             "added": [len(new_items), 64, 64, 3]},
            "routes": binding(root, destination / "input_routes.jsonl"),
            "pixel_validation": binding(root, destination / "pixel_validation.json"),
            "new_crop_rows": binding(root, destination / "new_crop_rows.jsonl"),
            "input_bindings": inputs,
            "counts": {"original_candidate_rows": len(old), "union_NBA_rows": len(union), "additions": len(added),
                       "query_rows": len(queries), "routes": len(routes), **crop_counts,
                       "source_png_decodes": pixel_receipt["decoded_source_pngs"],
                       "model_calls": 0, "optimizer_updates": 0, "old_crops_regenerated": 0},
            "point_contract": "Exact original floor crop; separate float64 point weights per raw input ID.",
            "source": binding(root, Path(__file__))}
        write(destination / "prepared.json", prepared)
        return prepared
    except BaseException as error:
        write(destination / "failed.json", {"status": "failed_CPU_preparation_preserved", "error": repr(error),
                                            "traceback": traceback.format_exc(), "model_calls": 0})
        raise
    finally:
        close_caches(caches)


def load_prepared(root=ROOT, verify=True, prepared_path=None):
    root = Path(root).resolve()
    path = Path(prepared_path) if prepared_path is not None else root / OUTPUT / "prepared.json"
    manifest = read(path)
    check(manifest["status"] == "prepared_CPU_inputs_no_model_calls", "Preparation is not complete")
    seen = set()

    def bound(link):
        if verify and link["path"] not in seen:
            verify_binding(root, link)
            seen.add(link["path"])
        return root / link["path"]

    if verify:
        for link in manifest["input_bindings"] + list(manifest["caches"].values()) + [manifest["source"], manifest["pixel_validation"], manifest["new_crop_rows"]]:
            bound(link)
    source_rows = {name: (read(bound(link)) if name == "scoring_plan" else rows(bound(link)))
                   for name, link in manifest["sources"].items()}
    result = {"manifest": manifest, "routes": {r["input_key"]: r for r in rows(bound(manifest["routes"]))},
              "scoring_plan": source_rows["scoring_plan"], "fits": {}}
    for name in ("original_candidates", "union_candidates", "added_candidates"):
        result[name] = {r["candidate_id"]: r for r in source_rows[name]}
    result["training_rows"] = {r["training_row_key"]: r for r in source_rows["union_candidates"]}
    result["queries"] = {r["query_id"]: r for r in source_rows["queries"]}
    for fit, record in manifest["fits"].items():
        result["fits"][fit] = {"plan": record["plan"], "weights": rows(bound(record["weights"])),
                                "schedules": [read(bound(link)) for link in record["schedules"]],
                                "bindings": {"weights": record["weights"], "schedules": record["schedules"],
                                             "exposure": record["exposure"]}}
        bound(record["exposure"])
    return result


def open_caches(root, loaded):
    caches = {}
    try:
        for name, link in loaded["manifest"]["caches"].items():
            array = np.load(Path(root) / link["path"], mmap_mode="r", allow_pickle=False)
            caches[name] = array
            check(array.dtype == np.uint8 and list(array.shape) == loaded["manifest"]["cache_shapes"][name]
                  and not array.flags.writeable, "Read-only cache contract differs")
        return caches
    except BaseException:
        close_caches(caches)
        raise


def close_caches(caches):
    for cache in caches.values():
        if getattr(cache, "_mmap", None) is not None:
            cache._mmap.close()


def batch_arrays(ids, loaded, caches):
    """CPU arrays only, in exact requested order; missing queries cannot score."""
    from .nba_appearance_feature_screen import crop_and_preprocess
    check(0 < len(ids) <= BATCH_SIZE, "Invalid inference batch size")
    pixels, points = [], []
    for key in ids:
        check(key in loaded["routes"], "Unknown input ID")
        route = loaded["routes"][key]
        check(route["input_key"] == key and route["missing"] is False, "Missing query cannot produce an image score")
        check(route["cache"] in caches and type(route["index"]) is int
              and 0 <= route["index"] < len(caches[route["cache"]]), "Invalid cache route")
        crop = np.asarray(caches[route["cache"]][route["index"]])
        check(crop.dtype == np.uint8 and crop.shape == (64, 64, 3), "Crop dtype/shape differs")
        weight = np.asarray(route["point_weights"], dtype=np.float64)
        check(weight.shape == (4,) and np.isfinite(weight).all() and (weight >= 0).all()
              and abs(float(weight.sum()) - 1.) < 1e-12, "Invalid point weights")
        pixels.append(crop_and_preprocess(Image.fromarray(crop), [32., 32.])[2])
        points.append(weight)
    pixel_array, point_array = np.stack(pixels), np.stack(points)
    check(pixel_array.dtype == np.float32 and pixel_array.shape == (len(ids), 3, 224, 224)
          and np.isfinite(pixel_array).all(), "Preprocessed input contract differs")
    return pixel_array, point_array


if __name__ == "__main__":
    result = prepare()
    print(json.dumps({"status": result["status"], "counts": result["counts"]}, indent=2))
