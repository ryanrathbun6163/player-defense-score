"""Freeze approved source frames and validate a mixed-source reference proposal.

Preparation reads saved metadata and source pixels only. It neither selects nor
scores predictions, creates annotations, loads model arrays, or accepts labels.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import time
import uuid

from PIL import Image

from . import annotations
from . import nba_annotations as nba
from . import nba_temporal_gap_continuous_review as continuous_review
from . import nba_wasb_diagnostic as d
from . import wasb_development_observation as nfhs

SCOPE_SCHEMA = "nba_gap_anchor_reference_scope/v0.1"
SCHEMA = "nba_gap_anchor_reference_preparation/v0.1"
PROPOSAL_SCHEMA = "nba_gap_anchor_reference_proposal/v0.1"
TOTALS = {"groups": 10, "target_frames": 34, "context_frames": 74,
          "new_references": 27, "reused_references": 7}


def key(row):
    return row["continuous_source_id"], row["source_frame_index"]


def read_bound(root, binding):
    return d.read_json(d.bound(root, binding))


def implementation_bindings(root):
    return [d.binding(root, root / "src/ball_tracking" / Path(module.__file__).name) for module in
            (__import__(__name__, fromlist=[""]), annotations, nba,
             continuous_review, d, nfhs)]


def derive_groups(selection):
    """Census every saved filled gap, without using its scores or labels."""
    result = []
    for source in selection["sources"]:
        for segment in source["segments"]:
            for gap in segment["gaps"]:
                if gap["reason"] != "all_frames_have_unambiguous_saved_candidates":
                    continue
                lo, hi = gap["source_frame_range_inclusive"]
                d.require([a["source_frame_index"] for a in gap["anchors"]] == [lo-1, hi+1],
                          "Saved gap endpoints differ")
                result.append({"group_id": gap["gap_id"], "continuous_source_id": source["candidate_id"],
                    "target_range_inclusive": [lo-1, hi+1], "context_range_inclusive": [lo-3, hi+3]})
    return result


def source_metadata(source):
    fields = ("candidate_id", "kind", "analysis_group", "source_video", "time_origin",
              "source_manifest", "native_timestamps", "source_end_exclusive_pts_ticks",
              "protected_ranges", "possession")
    result = {k: copy.deepcopy(source[k]) for k in fields if k in source}
    result["time_base"] = "1/90000"
    result["permitted_segments"] = [s["range_inclusive"] for s in source["segments"]]
    return result


def validate_source_authority(root, source):
    """Check source/clock joins without reading any candidate arrays or pixels."""
    metadata = source["source_video"]
    d.require(d.digest(d.contained(root, metadata["path"])) == metadata["sha256"],
              "Source video bytes changed")
    rows = source["frames"]
    indices = [r["source_frame_index"] for r in rows]
    d.require(len(set(indices)) == len(indices), "Duplicate source frame")
    if source["kind"] == "nba":
        manifest = read_bound(root, source["source_manifest"])
        d.require(manifest["candidate_id"] == source["candidate_id"]
                  and manifest["source_video"] == metadata and manifest["time_base"] == "1/90000"
                  and manifest["frames"] == [r["source_frame"] for r in rows]
                  and manifest["source_end_exclusive_pts_ticks"] == source["source_end_exclusive_pts_ticks"]
                  and source["time_origin"] == "native_container" and not source["protected_ranges"],
                  "NBA native source authority differs")
    else:
        d.require(source["kind"] == "nfhs" and source["possession"]["source_video"] == metadata
                  and source["possession"]["protected_ranges"] == source["protected_ranges"]
                  and source["possession"]["visible_segments"] == [s["range_inclusive"] for s in source["segments"]],
                  "NFHS permitted source authority differs")
        continuous_review.validate_nfhs_timing(root, source)


def census(selection, report, groups):
    """Join by the continuous source ID; historical NFHS window IDs differ."""
    d.require(groups == derive_groups(selection), "Batch is not the complete saved filled-gap census")
    sources = {s["candidate_id"]: s for s in selection["sources"]}
    d.require(len(sources) == len(selection["sources"]), "Duplicate continuous source ID")
    references = {key(r): (i, r) for i, r in enumerate(report["frames"])}
    d.require(len(references) == len(report["frames"]), "Duplicate accepted reference key")
    frames = []; seen = set()
    for group in groups:
        cid = group["continuous_source_id"]; source = sources[cid]
        lo, hi = group["target_range_inclusive"]; first, last = group["context_range_inclusive"]
        d.require(first == lo-2 and last == hi+2
                  and any(a <= first <= last <= b for a, b in (s["range_inclusive"] for s in source["segments"]))
                  and not any(max(first, a) <= min(last, b) for a, b in source["protected_ranges"]),
                  "Context escapes an approved segment or touches protected frames")
        timeline = {r["source_frame_index"]: r for r in source["frames"]}
        for index in range(first, last+1):
            pair = (cid, index); d.require(pair not in seen, "Overlapping reference contexts")
            seen.add(pair); original = timeline[index]
            d.require(original["decision"] != "withheld" and original["source_frame"]["source_frame_index"] == index
                      and original["source_frame"]["source_pts_ticks"] == original["source_pts_ticks"], "Source frame/clock join differs")
            role = "context_only" if index < lo or index > hi else "anchor" if index in (lo, hi) else "fill"
            if role == "anchor":
                d.require(original["baseline_center_xy_px"] is not None, "Original anchor missing")
            elif role == "fill":
                d.require(original["decision"] == "filled_saved_candidate" and original["baseline_center_xy_px"] is None,
                          "Target gap does not contain a saved fill")
            existing = None
            if role != "context_only" and pair in references:
                position, reference = references[pair]
                d.require(reference["source_video"] == source["source_video"]
                          and reference["source_frame"]["source_pts_ticks"] == original["source_pts_ticks"]
                          and reference["annotation"]["frame_index"] == index, "Accepted reference source join differs")
                existing = {"report_frame_index": position, "row": copy.deepcopy(reference)}
            frames.append({"continuous_source_id": cid, "source_frame_index": index,
                "source_pts_ticks": original["source_pts_ticks"], "container_pts_ticks": original.get("container_pts_ticks"),
                "time_base": "1/90000", "time_origin": source["time_origin"],
                "source_frame": copy.deepcopy(original["source_frame"]), "group_id": group["group_id"], "role": role,
                "reference_origin": None if role == "context_only" else "existing" if existing else "new",
                "existing_reference": existing})
    totals = {"groups": len(groups), "target_frames": sum(r["role"] != "context_only" for r in frames),
              "context_frames": len(frames), "new_references": sum(r["reference_origin"] == "new" for r in frames),
              "reused_references": sum(r["reference_origin"] == "existing" for r in frames)}
    d.require(totals == TOTALS, "Reference census totals differ")
    return frames


def validate_scope(root, scope, *, verify_sources=True):
    d.require(scope["schema_version"] == SCOPE_SCHEMA and scope["status"] == "approved"
              and scope["totals"] == TOTALS, "Approved reference scope required")
    approval = read_bound(root, scope["approval"])
    d.require(approval["status"] == "approved" and approval["approved_by"] == "Ryan"
              and approval["plan"] == scope["plan"] and approval["totals"] == TOTALS,
              "Reference approval or approved plan differs")
    d.bound(root, scope["plan"])
    d.require(scope["implementation"] == implementation_bindings(root)
              and scope["focused_tests"] == d.binding(root, root / "tests/test_nba_gap_anchor_reference.py"),
              "Preparation implementation/test bindings changed")
    selection = read_bound(root, scope["selection"]); report = read_bound(root, scope["report"])
    d.require(selection["schema_version"] == "nba_temporal_gap_continuous/v0.1"
              and report["status"] == "completed" and report["selection"] == scope["selection"],
              "Saved continuous selection/report join differs")
    frames = census(selection, report, scope["groups"])
    wanted = {r["continuous_source_id"] for r in frames}
    sources = [s for s in selection["sources"] if s["candidate_id"] in wanted]
    if verify_sources:
        for source in sources:
            validate_source_authority(root, source)
    output = d.contained(root, scope["output_root"])
    d.require(output.is_relative_to(root / "data/outputs"), "Reference artifacts must remain ignored")
    return sources, frames


def verify_raw_png(root, frame, source):
    """Validate encoded bytes, native dimensions and decoded RGB identity."""
    raw = nba.read_verified_png({"png": frame["raw_png"]}, source["source_video"], root)
    d.require(len(raw) == frame["raw_png"]["bytes"], "Raw PNG byte count differs")
    if source["kind"] == "nba":
        d.require(all(frame["raw_png"][k] == frame["source_frame"]["png"][k] for k in ("sha256", "rgb_sha256")),
                  "Prepared NBA image differs from the original source PNG")
    return raw


def extract_frames(root, sources, groups, frames, folder, resources):
    """Read saved NBA PNGs; request only approved NFHS subsegments."""
    by_source = {s["candidate_id"]: s for s in sources}
    by_group = {g["group_id"]: g for g in groups}
    decoders = {}
    try:
        for frame in frames:
            cid = frame["continuous_source_id"]; source = by_source[cid]
            if source["kind"] == "nba":
                raw = nba.read_verified_png(frame["source_frame"], source["source_video"], root)
                resources["existing_png_reads"] += 1
            else:
                gid = frame["group_id"]; group = by_group[gid]
                if gid not in decoders:
                    possession = copy.deepcopy(source["possession"])
                    possession["visible_segments"] = [g["context_range_inclusive"] for g in groups if g["continuous_source_id"] == cid]
                    # census validated each requested span against the original authority.
                    decoders[gid] = iter(nfhs.decode_segment(root, possession, group["context_range_inclusive"]))
                    resources["nfhs_requested_segments"].append({"continuous_source_id": cid,
                                                               "range_inclusive": group["context_range_inclusive"]})
                native, pixels = next(decoders[gid])
                d.require(native == frame["source_frame_index"], "Decoded source frame differs")
                image = Image.fromarray(pixels[:, :, ::-1]); buffer = io.BytesIO(); image.save(buffer, format="PNG")
                raw = buffer.getvalue(); resources["nfhs_decoded_frames"] += 1
                if native == group["context_range_inclusive"][1]:
                    d.require(next(decoders[gid], None) is None, "Decoder yielded outside approved span")
                    del decoders[gid]
            path = folder / cid / f"source_{frame['source_frame_index']:06d}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as handle:
                handle.write(raw)
            with Image.open(io.BytesIO(raw)) as image:
                rgb_sha = hashlib.sha256(image.convert("RGB").tobytes()).hexdigest()
            frame["raw_png"] = {**d.binding(root, path), "rgb_sha256": rgb_sha}
            verify_raw_png(root, frame, source)
    finally:
        for decoder in decoders.values():
            decoder.close()


def validate_preparation(root, preparation, scope=None, *, verify_images=True):
    root = Path(root).resolve()
    d.require(preparation["schema_version"] == SCHEMA and preparation["status"] == "source_preparation_complete"
              and preparation["new_labels_created"] is False and preparation["totals"] == TOTALS,
              "Invalid reference source preparation")
    bound_scope = read_bound(root, preparation["bindings"]["scope"])
    d.require(scope is None or scope == bound_scope, "Preparation scope differs")
    sources, expected = validate_scope(root, bound_scope, verify_sources=False)
    d.require(preparation["groups"] == bound_scope["groups"]
              and preparation["sources"] == [source_metadata(s) for s in sources], "Prepared source metadata differs")
    d.require(preparation["bindings"] == {"scope": preparation["bindings"]["scope"],
        **{k: bound_scope[k] for k in ("approval", "plan", "selection", "report", "implementation")}},
        "Preparation authority binding differs")
    d.require([{k: v for k, v in f.items() if k != "raw_png"} for f in preparation["frames"]] == expected,
              "Prepared frame census, controls or native source records differ")
    source_map = {s["candidate_id"]: s for s in sources}
    for frame in preparation["frames"]:
        d.require(d.contained(root, frame["raw_png"]["path"]).is_relative_to(root / "data/outputs"), "Raw image outside ignored outputs")
        if verify_images:
            verify_raw_png(root, frame, source_map[frame["continuous_source_id"]])
    return preparation


def load_ready_preparation(root, path, *, verify_images=True):
    path = Path(path); preparation = d.read_json(path)
    ready = d.read_json(path.with_name("preparation_ready.json"))
    d.require(ready["preparation"] == d.binding(root, path) and ready["new_labels_created"] is False
              and ready["scope"] == preparation["bindings"]["scope"], "Preparation changed after source freeze")
    return validate_preparation(root, preparation, verify_images=verify_images)


def prepare(root, scope_path):
    root = Path(root).resolve(); scope_path = (root / scope_path).resolve()
    scope = d.read_json(scope_path); sources, frames = validate_scope(root, scope)
    output = d.contained(root, scope["output_root"]); output.mkdir(parents=True, exist_ok=True)
    path = output / "preparation.json"
    if (output / "preparation_ready.json").exists():
        preparation = load_ready_preparation(root, path)
        d.require(preparation["bindings"]["scope"] == d.binding(root, scope_path), "Completed preparation belongs to another scope")
        return d.read_json(output / "preparation_ready.json")
    lock = d.acquire_run_lock(output / ".prepare.lock")
    attempt = output / "attempts" / uuid.uuid4().hex; began = time.monotonic()
    resources = {"model_calls": 0, "candidate_array_reads": 0, "new_labels_created": 0,
                 "existing_png_reads": 0, "nfhs_decoded_frames": 0, "nfhs_requested_segments": []}
    bindings = {"scope": d.binding(root, scope_path),
                **{k: scope[k] for k in ("approval", "plan", "selection", "report", "implementation")}}
    try:
        d.write_once(attempt / "started.json", {"bindings": bindings, "at_utc": d.stamp()})
        if path.exists():
            preparation = validate_preparation(root, d.read_json(path), scope)
        else:
            extract_frames(root, sources, scope["groups"], frames, attempt / "frames", resources)
            preparation = {"schema_version": SCHEMA, "status": "source_preparation_complete", "bindings": bindings,
                "groups": scope["groups"], "sources": [source_metadata(s) for s in sources], "frames": frames,
                "totals": TOTALS, "new_labels_created": False, "resources": resources, "created_at_utc": d.stamp()}
            validate_preparation(root, preparation, scope)
            d.write_once(path, preparation)
        ready = {"schema_version": SCHEMA, "status": "source_preparation_complete", "preparation": d.binding(root, path),
                 "scope": bindings["scope"], "new_labels_created": False, "created_at_utc": d.stamp()}
        d.write_once(output / "preparation_ready.json", ready)
        d.write_once(attempt / "completed.json", {"ready": d.binding(root, output / "preparation_ready.json"),
                                                 "elapsed_seconds": time.monotonic()-began, "resources": resources})
        return ready
    except Exception as error:
        d.write_once(attempt / "failed.json", {"status": "failed_preserved", "error_type": type(error).__name__,
            "error": str(error), "bindings": bindings, "resources": resources, "elapsed_seconds": time.monotonic()-began})
        raise
    finally:
        d.release_run_lock(lock)


def validate_proposal(root, proposal_path):
    """Validate an AI draft without accepting it or treating unknowns as labels."""
    root = Path(root).resolve(); proposal = d.read_json(proposal_path)
    d.require(set(proposal) == {"schema_version", "preparation", "status", "authorship", "human_review",
                               "new_annotations", "existing_controls"}, "Unexpected proposal fields")
    d.require(proposal["schema_version"] == PROPOSAL_SCHEMA and proposal["status"] == "draft"
              and proposal["human_review"] == "pending", "Only a pending reference draft is supported")
    author = proposal["authorship"]
    d.require(set(author) == {"annotator_id", "method", "not_blind"}
              and isinstance(author["annotator_id"], str) and bool(author["annotator_id"].strip())
              and author["method"] == "source_first_ai" and author["not_blind"] is True, "Honest AI authorship required")
    preparation = load_ready_preparation(root, d.bound(root, proposal["preparation"]))
    sources = {s["candidate_id"]: s for s in preparation["sources"]}
    expected_new = [key(r) for r in preparation["frames"] if r["reference_origin"] == "new"]
    d.require([key(r) for r in proposal["new_annotations"]] == expected_new, "New reference census differs")
    for index, row in enumerate(proposal["new_annotations"]):
        d.require(set(row) == {"continuous_source_id", "source_frame_index", "annotation"}, "Unexpected annotation entry fields")
        metadata = sources[row["continuous_source_id"]]["source_video"]
        # Existing NBA validation uses these same dimension-only bounds: no invented fps.
        bounds = nba._PixelBounds(metadata["width_px"], metadata["height_px"])
        parsed = annotations.FrameAnnotation.from_mapping(row["annotation"], index, bounds)
        d.require(parsed.frame_index == row["source_frame_index"] < metadata["frame_count"]
                  and parsed.annotation_status == "labeled", "Every proposed judgment requires an explicit supported or indeterminate assessment")
    controls = [{"continuous_source_id": r["continuous_source_id"], "source_frame_index": r["source_frame_index"],
                 "existing_reference": r["existing_reference"]} for r in preparation["frames"] if r["reference_origin"] == "existing"]
    d.require(proposal["existing_controls"] == controls, "Accepted controls or their original provenance changed")
    return preparation, proposal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope"); parser.add_argument("--proposal")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare", action="store_true"); modes.add_argument("--check-scope", action="store_true")
    modes.add_argument("--validate-proposal", action="store_true")
    args = parser.parse_args(); root = Path.cwd()
    if args.validate_proposal:
        validate_proposal(root, root / args.proposal); result = {"status": "valid_pending_reference_proposal"}
    elif args.check_scope:
        validate_scope(root, d.read_json(root / args.scope)); result = {"status": "approved_source_metadata_verified", "totals": TOTALS}
    else:
        result = prepare(root, args.scope)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
