"""CPU metadata preparation for the proposed candidate-point quality pilot.

No image decoding, Torch import, model call, fitting or new labels occurs here.
Targets describe accepted-coordinate quality, not semantic ball identity. The
negative uncertainty band is a conservative fitting choice, not a confidence
interval; original inclusive-ten-pixel evaluation remains unchanged.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CAPTURE_BASE = Path("data/outputs/ball_tracking/training_response_preparation_v0_1")
OUTPUT = Path("data/outputs/ball_tracking/candidate_quality_pilot_v0_1/preparation")
PACKAGE_SHA256 = "5615933dfbb43728a4c67a6c94665157f349f2562ad50bd2c9be02dc86181c9f"
NBA_GAMES = ("0022400868", "0022400866", "0022500829")
NFHS_GAMES = ("possession_001", "possession_002", "possession_003")
FIT_GAMES = {
    "leave_chi_out": ("0022400866", "0022500829"),
    "leave_den_out": ("0022400868", "0022500829"),
    "leave_sac_out": ("0022400868", "0022400866"),
    "all_nba": NBA_GAMES,
}
STRATUM_MASS = {"positive": 0.5, "eligible_distant_miss": 0.25, "certain_hidden": 0.25}
BATCH_SIZE = 32
EPOCHS = 6


def require(condition, message):
    if not condition:
        raise ValueError(message)


def binding(root: Path, path: Path) -> dict:
    path = path.resolve()
    require(path.is_relative_to(root.resolve()), "Binding outside project")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": path.relative_to(root.resolve()).as_posix(),
            "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def verify_binding(root: Path, link: dict) -> Path:
    path = root / link["path"]
    actual = binding(root, path)
    require(all(actual[k] == link[k] for k in ("path", "bytes", "sha256")),
            "Changed binding: " + link["path"])
    return path


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def write_jsonl(path: Path, rows):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, allow_nan=False) + "\n")


def stable_id(prefix: str, values) -> str:
    encoded = json.dumps(values, separators=(",", ":"), ensure_ascii=True).encode()
    return prefix + hashlib.sha256(encoded).hexdigest()


def validate_source_block(block: dict):
    """Reject source-role expansion before consuming any candidate rows."""
    require(block["role"] == "training", "Original source role is not training")
    domain, game = block["domain"], block["game_id"]
    require((domain == "nba" and game in NBA_GAMES)
            or (domain == "nfhs" and game in NFHS_GAMES),
            "Source is outside the fixed training capture; HOU/DET/protected forbidden")


def candidate_target(frame: dict, candidate: dict, width: int, height: int) -> dict:
    """Retain unknowns, inclusive-ten positives and conservative distant negatives."""
    x, y = candidate["center_x"], candidate["center_y"]
    require(all(isinstance(v, (int, float)) and math.isfinite(v) for v in (x, y)),
            "Non-finite candidate coordinate")
    inside = 0 <= x < width and 0 <= y < height
    require(candidate["in_source_bounds"] is inside, "Producer bounds flag differs")
    annotation = frame["annotation"]
    kind = frame["kind"]
    result = {"target": None, "target_group": "masked_unknown", "distance_px": None,
              "recorded_uncertainty_radius_px": None, "in_source_bounds": inside}
    if kind == "masked":
        geometry = annotation.get("geometry")
        if geometry:
            result["recorded_uncertainty_radius_px"] = geometry.get("uncertainty_radius_px")
        return result
    require(annotation["game_ball_identity_certainty"] == "certain", "Scored identity is uncertain")
    if kind == "hidden":
        require(annotation["visibility"] == "not_visible"
                and annotation["localization_eligible"] is False
                and annotation["geometry"] is None, "Invalid certain-hidden reference")
        result.update(target=0, target_group="certain_hidden")
        return result
    require(kind == "positive" and annotation["localization_eligible"] is True,
            "Unknown kind or ineligible positive")
    center = annotation["geometry"]["center_xy_px"]
    uncertainty = annotation["geometry"]["uncertainty_radius_px"]
    require(isinstance(uncertainty, (int, float)) and math.isfinite(uncertainty)
            and uncertainty >= 0, "Invalid placement uncertainty")
    distance = math.hypot(x - center[0], y - center[1])
    require(math.isfinite(distance), "Non-finite reference geometry")
    result.update(distance_px=distance, recorded_uncertainty_radius_px=uncertainty)
    if inside and distance <= 10:
        result.update(target=1, target_group="positive")
    elif not inside or distance > 10 + uncertainty:
        result.update(target=0, target_group="eligible_distant_miss")
    else:
        result["target_group"] = "boundary_unknown"
    return result


def make_frame_rows(block: dict, frame: dict, observation: dict, pool: dict,
                    pool_binding: dict) -> tuple[dict, list[dict]]:
    """Consume the actual emitted extraction schema with exact native transport."""
    validate_source_block(block)
    source, png = block["source_video"], frame["png"]
    require(pool["block_id"] == block["block_id"], "Wrong pool block")
    require(frame["annotation"]["frame_index"] == frame["source_frame_index"], "Reference frame mismatch")
    for field in ("source_frame_index", "source_pts_ticks"):
        require(pool[field] == observation[field] == frame[field], "Frame/clock transport mismatch: " + field)
    require(pool["time_base"] == observation["time_base"] == block["time_base"], "Time base mismatch")
    require(pool["mean_heatmap_sha256"] == observation["mean_heatmap_sha256"], "Mean identity mismatch")
    require(observation["source_png"] == png, "PNG binding mismatch")
    require(pool["width_px"] == source["width_px"] and pool["height_px"] == source["height_px"],
            "Source dimensions mismatch")
    diagnostic = pool["diagnostic"]
    require(diagnostic["labels_used"] is False and diagnostic["native_parity"] is True,
            "Pool extraction contract changed")
    native = observation["candidates"]
    require(diagnostic["native_count"] == len(native), "Native prefix length mismatch")
    require(diagnostic["pool_count"] == len(pool["candidates"]), "Pool length mismatch")
    require(diagnostic["retained_weak_count"] == len(pool["candidates"]) - len(native), "Weak count mismatch")
    frame_id = stable_id("frame_", [source["sha256"], block["block_id"], frame["source_frame_index"],
                                    frame["source_pts_ticks"], block["time_base"]])
    common = {"frame_id": frame_id, "block_id": block["block_id"], "game_id": block["game_id"],
              "domain": block["domain"], "source_frame_index": frame["source_frame_index"],
              "source_pts_ticks": frame["source_pts_ticks"], "time_base": block["time_base"],
              "source_video_sha256": source["sha256"], "source_png": png}
    rows = []
    for index, candidate in enumerate(pool["candidates"]):
        require(candidate["candidate_index"] == index, "Candidate index/order mismatch")
        origin = "native" if index < len(native) else "weak"
        if origin == "native":
            require(candidate["extraction"] == "native_component", "Native extraction mismatch")
            require(all(candidate[key] == value for key, value in native[index].items()),
                    "Native candidate transport mismatch")
        else:
            require(candidate["extraction"] == "threshold_component" and candidate["threshold"] == 0.01,
                    "Weak extraction changed")
        candidate_id = stable_id("candidate_", [frame_id, pool_binding["sha256"], index])
        rows.append({**common, "candidate_id": candidate_id, "candidate_index": index,
                     "native_or_weak": origin,
                     "center_xy_px": [candidate["center_x"], candidate["center_y"]],
                     "width_px": source["width_px"], "height_px": source["height_px"],
                     "producer_candidate": candidate,
                     **candidate_target(frame, candidate, source["width_px"], source["height_px"])})
    frame_row = {**common, "duration_ticks": frame["duration_ticks"], "source_video": source,
                 "annotation": frame["annotation"], "kind": frame["kind"],
                 "valid_output_channel": frame["valid_output_channel"],
                 "pool_binding": pool_binding, "mean_heatmap_sha256": pool["mean_heatmap_sha256"],
                 "native_selected_candidate_index": observation["selected_candidate_index"],
                 "native_center_xy_px": observation["center_xy_px"],
                 "candidate_ids": [row["candidate_id"] for row in rows],
                 "candidate_count": len(rows), "original_source_role": block["role"],
                 "pilot_role": "nba_fit_or_scorer_validation" if block["domain"] == "nba"
                 else "nfhs_secondary_evaluation_only"}
    return frame_row, rows


def fit_weights(candidates: list[dict], games: tuple[str, ...]) -> tuple[list[dict], dict]:
    """Weights total one: stratum, game, block, frame, origin, candidate.

    Unknowns, held games and NFHS have no fit row. An absent origin/block/game
    within a stratum has no denominator contribution; available siblings share
    that parent's mass equally. A globally empty required stratum is an error,
    never silently reallocated to another target. The frozen four fits all have
    every stratum in every fitting NBA game.
    """
    require(games and len(set(games)) == len(games) and set(games) <= set(NBA_GAMES),
            "Fit games outside fixed NBA sources")
    selected = []
    tree = {}
    seen = set()
    for row in candidates:
        require(row["candidate_id"] not in seen, "Duplicate candidate identity")
        seen.add(row["candidate_id"])
        if row["domain"] != "nba" or row["game_id"] not in games or row["target"] is None:
            continue
        group = row["target_group"]
        require(group in STRATUM_MASS and row["target"] == (1 if group == "positive" else 0),
                "Target/group mismatch")
        require(row["native_or_weak"] in ("native", "weak"), "Unknown candidate origin")
        cursor = tree.setdefault(group, {}).setdefault(row["game_id"], {}).setdefault(row["block_id"], {})
        cursor.setdefault(row["frame_id"], {}).setdefault(row["native_or_weak"], []).append(row["candidate_id"])
        selected.append(row)
    require(set(tree) == set(STRATUM_MASS), "A required fitting stratum is empty")
    weights = {}
    stratum_support = {}
    for group, game_tree in tree.items():
        stratum_support[group] = {}
        for game, blocks in game_tree.items():
            stratum_support[group][game] = {"blocks": len(blocks), "frames": sum(map(len, blocks.values())),
                                           "candidates": 0}
            for frames in blocks.values():
                for origins in frames.values():
                    for ids in origins.values():
                        weight = STRATUM_MASS[group] / len(game_tree) / len(blocks) / len(frames) / len(origins) / len(ids)
                        for candidate_id in ids:
                            weights[candidate_id] = weight
                        stratum_support[group][game]["candidates"] += len(ids)
    require(math.isclose(math.fsum(weights.values()), 1.0, abs_tol=1e-12), "Weights do not sum to one")
    n = len(selected)
    output = [{"candidate_id": row["candidate_id"], "objective_weight": weights[row["candidate_id"]],
               "training_multiplier": n * weights[row["candidate_id"]]} for row in selected]
    return output, {"fitting_candidates": n, "target_counts": dict(Counter(str(r["target"]) for r in selected)),
                    "stratum_counts": dict(Counter(r["target_group"] for r in selected)),
                    "stratum_support": stratum_support, "weight_sum": math.fsum(weights.values()),
                    "minimum_objective_weight": min(weights.values()), "maximum_objective_weight": max(weights.values()),
                    "batch_size": BATCH_SIZE, "epochs": EPOCHS,
                    "steps_per_epoch": math.ceil(n / BATCH_SIZE),
                    "total_training_steps": EPOCHS * math.ceil(n / BATCH_SIZE)}


def prepare(root: Path = ROOT, output: Path | None = None) -> dict:
    root = root.resolve()
    output = (output or root / OUTPUT).resolve()
    require(output.is_relative_to(root), "Output outside workspace")
    require(not output.exists(), "Preparation output already exists; preserve it")
    base = root / CAPTURE_BASE
    prepared_path, completed_path = base / "prepared.json", base / "capture_attempt_001/completed.json"
    prepared, complete = read_json(prepared_path), read_json(completed_path)
    require(complete["status"] == "completed_capture_no_fitting"
            and complete["model_tensors_unchanged"] is True
            and complete["extraction_sealed_before_label_assisted_coverage"] is True,
            "Capture not the completed frozen input")
    require(complete["new_training_updates"] == complete["new_selector_runs"] == complete["new_labels"] == 0
            and complete["protected_access"] is False, "Capture scope mismatch")
    verify_binding(root, complete["prepared"])
    require(prepared["package"]["sha256"] == PACKAGE_SHA256, "Package is not the accepted frozen training package")
    package = read_json(verify_binding(root, prepared["package"]))
    require(prepared["source_roles"] == package["source_roles"], "Source role binding mismatch")
    roles = read_json(verify_binding(root, package["source_roles"]))
    role_map = {r["game_id"]: r["role"] for r in roles["game_roles"]}
    require(all(role_map[g] == "training" for g in NBA_GAMES), "NBA role mismatch")
    reference_bindings = package["reference_bindings"] + [package["accepted_nba_inventory"]]
    for link in reference_bindings:
        verify_binding(root, link)
    blocks = package["training_blocks"]
    require(len(blocks) == len(prepared["blocks"]) == len(complete["records"]) == 26, "Block census mismatch")
    require([b["block_id"] for b in blocks] == [b["block_id"] for b in prepared["blocks"]], "Prepared block order mismatch")
    frames, candidates, source_bindings = [], [], []
    for block, item, link in zip(blocks, prepared["blocks"], complete["records"], strict=True):
        validate_source_block(block)
        record = read_json(verify_binding(root, link))
        require(record["block_id"] == block["block_id"] and record["original_record"] == item["native_record"],
                "Capture record mismatch")
        original = read_json(verify_binding(root, item["native_record"]))
        require(record["native_observations"] == original["observations"], "Original native observations changed")
        extraction = record["extraction"]
        require(extraction["all_native_candidates_exact"] is True and extraction["all_mean_hashes_exact"] is True
                and extraction["labels_used"] is False, "Extraction receipt mismatch")
        pool_path = verify_binding(root, extraction["pools"])
        pools = [json.loads(line) for line in pool_path.read_text(encoding="utf-8").splitlines()]
        require(len(pools) == len(block["frames"]) == len(record["native_observations"]) == item["frames"],
                "Frame population mismatch")
        for frame, observation, pool in zip(block["frames"], record["native_observations"], pools, strict=True):
            frame_row, candidate_rows = make_frame_rows(block, frame, observation, pool, extraction["pools"])
            frames.append(frame_row)
            candidates.extend(candidate_rows)
        source_bindings.append({"block_id": block["block_id"], "capture_record": link,
                                "original_record": item["native_record"], "pools": extraction["pools"],
                                "mean_heatmaps": extraction["mean_heatmaps"]})
    require(len(frames) == 3329 and len(candidates) == 19632, "Frozen frame/candidate census changed")
    require(len({f["frame_id"] for f in frames}) == len(frames), "Repeated frame identity")
    require(len({(f["source_video_sha256"], f["source_frame_index"]) for f in frames}) == len(frames),
            "Overlapping source-frame contexts; grouping requires review")
    require(len({c["candidate_id"] for c in candidates}) == len(candidates), "Repeated candidate identity")
    targets = Counter(c["target_group"] for c in candidates)
    require(targets == Counter(positive=3627, eligible_distant_miss=14332, certain_hidden=375,
                               boundary_unknown=70, masked_unknown=1228), "Target census mismatch")
    weighted = {name: fit_weights(candidates, games) for name, games in FIT_GAMES.items()}
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "started.json", {"at_utc": datetime.now(timezone.utc).isoformat(),
                                        "scope": "CPU metadata preparation; training not authorized"})
    write_jsonl(output / "frames.jsonl", frames)
    write_jsonl(output / "candidates.jsonl", candidates)
    common_bindings = {"frames": binding(root, output / "frames.jsonl"),
                       "candidates": binding(root, output / "candidates.jsonl")}
    fit_manifests = {}
    for name, games in FIT_GAMES.items():
        directory = output / "fits" / name
        directory.mkdir(parents=True)
        weights, stats = weighted[name]
        write_jsonl(directory / "weights.jsonl", weights)
        held = [g for g in NBA_GAMES if g not in games]
        fit_frames = [f for f in frames if f["domain"] == "nba" and f["game_id"] in games]
        held_frames = [f for f in frames if f["domain"] == "nba" and f["game_id"] in held]
        manifest = {"schema_version": "candidate_quality_fit/v0.1", "fit_id": name,
                    "fit_game_ids": list(games), "held_out_game_ids": held,
                    "fit_frame_ids": [f["frame_id"] for f in fit_frames],
                    "held_out_frame_ids": [f["frame_id"] for f in held_frames],
                    "secondary_nfhs_frame_ids": [f["frame_id"] for f in frames if f["domain"] == "nfhs"],
                    "fit_frame_kind_counts": dict(Counter(f["kind"] for f in fit_frames)),
                    "held_out_frame_kind_counts": dict(Counter(f["kind"] for f in held_frames)),
                    "common": common_bindings, "weights": binding(root, directory / "weights.jsonl"),
                    **stats, "training_authorized": False,
                    "base_exposure": "cosine nine already trained on all three NBA sources"}
        write_json(directory / "manifest.json", manifest)
        fit_manifests[name] = binding(root, directory / "manifest.json")
    result = {"schema_version": "candidate_quality_preparation/v0.1", "status": "prepared_no_training",
              "created_at_utc": datetime.now(timezone.utc).isoformat(), "common": common_bindings,
              "fit_manifests": fit_manifests, "frames": len(frames), "candidates": len(candidates),
              "unique_source_frames": len(frames), "empty_frames": sum(not f["candidate_ids"] for f in frames),
              "frame_kind_counts": dict(Counter(f["kind"] for f in frames)), "target_counts": dict(targets),
              "domain_counts": dict(Counter(f["domain"] for f in frames)),
              "all_four_fits_steps": sum(stats["total_training_steps"] for _, stats in weighted.values()),
              "all_four_fits_candidate_exposures": EPOCHS * sum(stats["fitting_candidates"] for _, stats in weighted.values()),
              "stratum_mass": STRATUM_MASS,
              "weight_hierarchy": ["stratum", "game", "block", "frame", "nonempty_native_or_weak", "candidate"],
              "missing_strata": "Missing child groups omitted and available siblings share their parent's mass; any globally absent required stratum errors. No empty-frame or unknown-label crop is fabricated.",
              "target_policy": "positive:inbounds d<=10; negative:certain_hidden or eligible out-of-bounds/d>10+u; other/masked unknown. Asymmetric fitting mask, not uncertainty probability; original evaluation unchanged.",
              "inputs": {"prepared_capture": binding(root, prepared_path), "completed_capture": binding(root, completed_path),
                         "package": prepared["package"], "source_roles": package["source_roles"],
                         "references": reference_bindings, "blocks": source_bindings},
              "implementation": binding(root, Path(__file__)),
              "pixel_reads": 0, "model_calls": 0, "training_updates": 0, "new_labels": 0,
              "protected_access": False, "training_authorized": False,
              "verification_limit": "Metadata bindings/native transport checked; prior map/component audit reused. No maps or images read. Source PNG hashes remain bound for execution-time verification."}
    write_json(output / "prepared.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true", required=True)
    args = parser.parse_args()
    if args.prepare:
        result = prepare()
        print(json.dumps({k: result[k] for k in ("status", "frames", "candidates", "empty_frames",
                                               "target_counts", "all_four_fits_steps")}, indent=2))


if __name__ == "__main__":
    main()
