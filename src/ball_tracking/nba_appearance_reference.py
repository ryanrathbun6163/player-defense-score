"""Freeze saved mean candidates before source-only appearance judgments.

No inference, candidate-array reads, geometric scoring, or reference-center
creation. Pixels are extracted only after the metadata census is persisted.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
import uuid

from . import nba_gap_anchor_reference as source_reference
from . import nba_wasb_diagnostic as d

SCOPE_SCHEMA = "nba_appearance_reference_scope/v0.1"
FROZEN_SCHEMA = "nba_appearance_reference_metadata/v0.1"
SCHEMA = "nba_appearance_reference_preparation/v0.1"
PROPOSAL_SCHEMA = "nba_appearance_reference_proposal/v0.1"
ROLES = {"fit_eligible", "excluded_check"}


def _path(root, value):
    path = Path(value)
    path = path.resolve() if path.is_absolute() else d.contained(root, path.as_posix())
    d.require(path.is_relative_to(root), "Path leaves repository")
    return path


def _output(root, value):
    path = _path(root, value)
    d.require(path.is_relative_to(root / "data/outputs"), "Appearance artifacts must remain ignored")
    return path


def _read(root, binding):
    return d.read_json(d.bound(root, binding))


def _range(value):
    d.require(isinstance(value, list) and len(value) == 2
              and all(type(v) is int and v >= 0 for v in value) and value[0] <= value[1], "Invalid source range")
    return value


def _training_blocks(root, scope):
    config = _read(root, scope["fit_authority"])
    nfhs = _read(root, config["nfhs_training_config"])
    result = [(w["candidate_id"], w["source_frame_range_inclusive"], None)
              for w in config["nba_training_windows"]]
    result.extend((w["possession_id"], [w["start_frame_index"], w["end_frame_index"]], w["source_video"])
                  for w in nfhs["training_blocks"])
    return result


def _source_authority(root, source):
    """Join already-bound source authorities without rehashing entire videos."""
    rows, metadata = source["frames"], source["source_video"]
    indices = [r["source_frame_index"] for r in rows]
    d.require(len(indices) == len(set(indices)), "Duplicate source frame")
    if source["kind"] == "nba":
        native = _read(root, source["source_manifest"])
        d.require(native["candidate_id"] == source["candidate_id"] and native["source_video"] == metadata
                  and native["time_base"] == "1/90000" and source["time_origin"] == "native_container"
                  and native["frames"] == [r["source_frame"] for r in rows]
                  and native["source_end_exclusive_pts_ticks"] == source["source_end_exclusive_pts_ticks"]
                  and not source["protected_ranges"], "NBA source authority differs")
    else:
        d.require(source["kind"] == "nfhs", "Unknown source kind")
        native = _read(root, source["native_timestamps"])
        d.bound(root, native["packet_probe"])
        d.require(native["schema_version"] == "nfhs_container_native_timestamps/v0.1"
                  and native["status"] == "verified" and native["candidate_id"] == source["candidate_id"]
                  and native["source_video"] == metadata and native["time_base"] == "1/90000"
                  and native["time_origin"] == source["time_origin"] == "clip_first_frame"
                  and native["source_end_exclusive_pts_ticks"] == source["source_end_exclusive_pts_ticks"]
                  and source["possession"]["source_video"] == metadata
                  and source["possession"]["protected_ranges"] == source["protected_ranges"]
                  and source["possession"]["visible_segments"] == [s["range_inclusive"] for s in source["segments"]],
                  "NFHS source authority differs")
        expected = native["frames"]
        d.require(len(rows) == len(expected) and all(r["source_frame_index"] == f["source_frame_index"]
                  and r["source_pts_ticks"] == f["source_pts_ticks"]
                  and r["container_pts_ticks"] == f["container_pts_ticks"]
                  and (r["decision"] == "withheld" or r["source_frame"] == f)
                  for r, f in zip(rows, expected)), "NFHS native clock join differs")
    for row in rows:
        if row["decision"] != "withheld":
            d.require(row["source_frame"]["source_frame_index"] == row["source_frame_index"]
                      and row["source_frame"]["source_pts_ticks"] == row["source_pts_ticks"], "Source frame/clock join differs")


def census(root, scope):
    """Reconstruct the complete scoped candidate census using JSON only."""
    d.require(scope["schema_version"] == SCOPE_SCHEMA and scope["status"] == "approved"
              and scope["context_radius_frames"] == 2, "Approved two-frame context scope required")
    if "approval" in scope:
        d.require(_read(root, scope["approval"])["status"] == "approved", "Appearance scope approval differs")
    for name in ("plan", "inventory"):
        if name in scope:
            d.bound(root, scope[name])
    selection = _read(root, scope["selection"])
    d.require(selection["schema_version"] == "nba_temporal_gap_continuous/v0.1", "Unexpected saved selection")
    regression = _read(root, scope["regression_preparation"])
    d.require(regression["schema_version"] == source_reference.SCHEMA
              and regression["status"] == "source_preparation_complete", "Invalid regression source preparation")
    excluded = {(f["continuous_source_id"], f["source_frame_index"]) for f in regression["frames"]}
    training = _training_blocks(root, scope)
    sources = {s["candidate_id"]: s for s in selection["sources"]}
    d.require(len(sources) == len(selection["sources"]), "Duplicate source identity")
    specs = scope["targets"]
    d.require(isinstance(specs, list) and specs, "Empty target census")
    wanted = {t["continuous_source_id"] for t in specs}
    d.require(set(scope["source_roles"]) == wanted and all(r in ROLES for r in scope["source_roles"].values()),
              "Source roles must exactly cover target sources")
    for cid in wanted:
        d.require(cid in sources, "Unknown target source")
        _source_authority(root, sources[cid])
    groups, frames, targets, candidates = [], [], [], []
    seen, target_ids, blocks = set(), set(), {}
    for spec in specs:
        cid, index, tid, role = (spec[k] for k in ("continuous_source_id", "source_frame_index", "target_id", "role"))
        d.require(isinstance(tid, str) and tid and tid not in target_ids and type(index) is int,
                  "Duplicate or invalid target identity")
        target_ids.add(tid)
        d.require(role == scope["source_roles"][cid] and role in ROLES, "Source role crossing")
        source = sources[cid]; block = _range(spec["complete_block_range_inclusive"])
        bid = spec["block_id"]
        d.require(isinstance(bid, str) and bid, "Missing block identity")
        block_identity = (cid, role, tuple(block))
        d.require(bid not in blocks or blocks[bid] == block_identity, "Complete block ownership differs")
        blocks[bid] = block_identity
        lo, hi = index-2, index+2
        d.require(block[0] <= lo <= hi <= block[1], "Context escapes complete historical block")
        d.require(any(a <= block[0] <= block[1] <= b for a, b in (s["range_inclusive"] for s in source["segments"]))
                  and not any(max(lo, a) <= min(hi, b) for a, b in source["protected_ranges"]),
                  "Context escapes permitted segment or touches protected frames")
        if role == "fit_eligible":
            matches = [m for m in training if m[0] == cid and m[1] == block]
            d.require(matches and all(m[2] is None or m[2] == source["source_video"] for m in matches),
                      "Fit context is not a bound historical training block")
        timeline = {r["source_frame_index"]: r for r in source["frames"]}
        group = {"group_id": tid, "block_id": bid, "continuous_source_id": cid, "role": role,
                 "context_range_inclusive": [lo, hi], "target_ids": [tid]}
        groups.append(group)
        for n in range(lo, hi+1):
            pair = (cid, n)
            d.require(pair not in seen, "Appearance contexts overlap; choose targets at least five frames apart")
            d.require(pair not in excluded, "Appearance context overlaps diagnostic regression context")
            d.require(n in timeline and timeline[n]["decision"] != "withheld", "Missing or protected source frame")
            seen.add(pair); original = timeline[n]
            frames.append({"group_id": tid, "continuous_source_id": cid, "source_frame_index": n,
                "source_pts_ticks": original["source_pts_ticks"], "container_pts_ticks": original.get("container_pts_ticks"),
                "time_base": "1/90000", "time_origin": source["time_origin"], "source_frame": copy.deepcopy(original["source_frame"]),
                "role": "target" if n == index else "context_only", "target_id": tid if n == index else None})
        observation = timeline[index]["original_observation"]
        d.require(observation["source_frame_index"] == index and observation["source_pts_ticks"] == timeline[index]["source_pts_ticks"],
                  "Original observation/source clock differs")
        pool = observation["candidates"]
        d.require(isinstance(pool, list) and pool, "Target has no original mean candidates")
        indices = [c["candidate_index"] for c in pool]
        d.require(all(type(i) is int and i >= 0 for i in indices) and len(set(indices)) == len(indices), "Duplicate candidate identity")
        keys = []
        for offset, component in enumerate(pool):
            center = [component["center_x"], component["center_y"]]
            d.require(all(type(v) in (int, float) and math.isfinite(v) for v in center), "Invalid candidate center")
            inside = 0 <= center[0] < source["source_video"]["width_px"] and 0 <= center[1] < source["source_video"]["height_px"]
            d.require(component["in_source_bounds"] is inside and inside, "Candidate outside source bounds")
            key = f"{cid}:{index}:mean:{component['candidate_index']}"; keys.append(key)
            candidates.append({"candidate_key": key, "target_id": tid, "group_id": tid, "block_id": bid,
                "continuous_source_id": cid, "source_frame_index": index, "source_pts_ticks": timeline[index]["source_pts_ticks"],
                "role": role, "candidate_offset": offset, "component": copy.deepcopy(component), "center_xy_px": center,
                "provenance_id": ["old", cid, index, "mean", None, None, component["candidate_index"]]})
        targets.append({**copy.deepcopy(spec), "group_id": tid, "candidate_keys": keys})
    totals = {"targets": len(targets), "candidates": len(candidates), "context_frames": len(frames)}
    if "expected_totals" in scope:
        d.require(totals == scope["expected_totals"], "Frozen census totals differ from approved scope")
    return {"sources": [source_reference.source_metadata(sources[cid]) for cid in sources if cid in wanted],
            "groups": groups, "frames": frames, "targets": targets, "candidates": candidates, "totals": totals}, sources


def freeze(root, scope_path, output_dir):
    root = Path(root).resolve(); scope_path = _path(root, scope_path); output = _output(root, output_dir)
    scope = d.read_json(scope_path); records, _ = census(root, scope)
    bindings = {"scope": d.binding(root, scope_path), "implementation": d.binding(root, root / "src/ball_tracking/nba_appearance_reference.py")}
    document = {"schema_version": FROZEN_SCHEMA, "status": "metadata_frozen_before_pixels", "bindings": bindings,
                **records, "new_labels_created": False, "pixel_reads": 0}
    d.write_once(output / "metadata.json", document)
    return document


def load_frozen(root, path):
    root = Path(root).resolve(); document = d.read_json(_path(root, path))
    d.require(document["schema_version"] == FROZEN_SCHEMA and document["status"] == "metadata_frozen_before_pixels"
              and document["new_labels_created"] is False and document["pixel_reads"] == 0, "Invalid metadata freeze")
    d.bound(root, document["bindings"]["implementation"])
    records, sources = census(root, _read(root, document["bindings"]["scope"]))
    d.require({k: document[k] for k in records} == records, "Frozen candidate/source census differs")
    return document, sources


def prepare(root, frozen_path, output_dir=None):
    root = Path(root).resolve(); frozen_path = _path(root, frozen_path)
    output = _output(root, output_dir or frozen_path.parent)
    frozen, source_map = load_frozen(root, frozen_path)
    if (output / "preparation_ready.json").exists():
        prior = load_ready_preparation(root, output / "preparation.json")
        d.require(prior["metadata"] == d.binding(root, frozen_path), "Existing preparation belongs to different metadata")
        return prior
    attempt = output / "attempts" / uuid.uuid4().hex
    resources = {"model_calls": 0, "candidate_array_reads": 0, "new_labels_created": 0,
                 "existing_png_reads": 0, "nfhs_decoded_frames": 0, "nfhs_requested_segments": []}
    binding = d.binding(root, frozen_path)
    d.write_once(attempt / "started.json", {"metadata": binding, "created_at_utc": d.stamp()})
    try:
        for source in frozen["sources"]:
            if source["kind"] == "nfhs":
                d.require(d.digest(d.contained(root, source["source_video"]["path"])) == source["source_video"]["sha256"],
                          "NFHS source video bytes changed before extraction")
        frames = copy.deepcopy(frozen["frames"])
        source_reference.extract_frames(root, list(source_map.values()), frozen["groups"], frames, attempt / "frames", resources)
        preparation = {"schema_version": SCHEMA, "status": "source_preparation_complete", "metadata": binding,
            **{k: copy.deepcopy(frozen[k]) for k in ("sources", "groups", "targets", "candidates", "totals")},
            "frames": frames, "new_labels_created": False, "resources": resources}
        d.write_once(output / "preparation.json", preparation)
        d.write_once(output / "preparation_ready.json", {"metadata": binding,
            "preparation": d.binding(root, output / "preparation.json"), "new_labels_created": False})
        d.write_once(attempt / "completed.json", {"preparation": d.binding(root, output / "preparation.json"), "resources": resources})
        return preparation
    except Exception as error:
        d.write_once(attempt / "failed.json", {"status": "failed_preserved", "error_type": type(error).__name__,
            "error": str(error), "metadata": binding, "resources": resources})
        raise


def load_ready_preparation(root, path, *, verify_images=True):
    root = Path(root).resolve(); path = _path(root, path); preparation = d.read_json(path)
    ready = d.read_json(path.with_name("preparation_ready.json"))
    d.require(ready["preparation"] == d.binding(root, path) and ready["metadata"] == preparation["metadata"]
              and ready["new_labels_created"] is False and preparation["new_labels_created"] is False
              and preparation["schema_version"] == SCHEMA and preparation["status"] == "source_preparation_complete",
              "Source preparation changed after freeze")
    frozen, sources = load_frozen(root, d.bound(root, preparation["metadata"]))
    d.require(all(preparation[k] == frozen[k] for k in ("sources", "groups", "targets", "candidates", "totals"))
              and [{k: v for k, v in f.items() if k != "raw_png"} for f in preparation["frames"]] == frozen["frames"],
              "Prepared candidate/source transport differs")
    for frame in preparation["frames"]:
        _output(root, frame["raw_png"]["path"])
        if verify_images:
            source_reference.verify_raw_png(root, frame, sources[frame["continuous_source_id"]])
    return preparation


def validate_proposal(root, proposal_path):
    root = Path(root).resolve(); proposal = d.read_json(_path(root, proposal_path))
    d.require(set(proposal) == {"schema_version", "preparation", "authorship", "human_review", "rows"}
              and proposal["schema_version"] == PROPOSAL_SCHEMA and proposal["human_review"] == "pending", "Invalid appearance proposal fields/status")
    author = proposal["authorship"]
    d.require(set(author) == {"annotator_id", "method", "not_blind"} and isinstance(author["annotator_id"], str)
              and author["annotator_id"].strip() and author["method"] == "source_first_ai" and author["not_blind"] is True,
              "Honest source-first AI authorship required")
    preparation = load_ready_preparation(root, d.bound(root, proposal["preparation"]))
    rows = proposal["rows"]
    d.require(isinstance(rows, list) and [r["candidate_key"] for r in rows] == [r["candidate_key"] for r in preparation["candidates"]],
              "Proposal must cover the complete frozen candidate census in order")
    for row in rows:
        d.require(set(row) == {"candidate_key", "classification", "subtype", "rationale"}
                  and row["classification"] in {"ball", "other_object", "unresolved"}, "Invalid appearance row; geometry is not permitted")
        d.require(isinstance(row["rationale"], str) and row["rationale"].strip(), "Appearance rationale required")
        d.require((row["classification"] != "other_object" and row["subtype"] is None)
                  or (row["classification"] == "other_object" and isinstance(row["subtype"], str) and row["subtype"].strip()),
                  "Only confirmed other objects have a nonempty subtype")
    return preparation, proposal


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("action", choices=("freeze", "prepare"))
    parser.add_argument("--scope"); parser.add_argument("--metadata"); parser.add_argument("--output", required=True)
    args = parser.parse_args(); root = Path(__file__).resolve().parents[2]
    result = freeze(root, args.scope, args.output) if args.action == "freeze" else prepare(root, args.metadata, args.output)
    print(json.dumps({"status": result["status"], "totals": result["totals"]}))


if __name__ == "__main__":
    main()
