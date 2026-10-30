"""Prepare the approved, immutable ball/distractor source census before labeling.

Reads saved JSON candidates and native source images only. No heatmap arrays,
features, model calls, training, or new semantic judgments are made here.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import json
import math
from pathlib import Path
import time
import uuid

from . import nba_appearance_reference as appearance
from . import nba_gap_anchor_reference as source_reference
from . import nba_wasb_diagnostic as d

SCHEMA = "nba_ball_distractor_reference_preparation/v0.1"
METADATA_SCHEMA = "nba_ball_distractor_reference_metadata/v0.1"
PROPOSAL_SCHEMA = "nba_ball_distractor_verifier_proposal/v0.1"
APPROVAL_SCHEMA = "nba_ball_distractor_verifier_approval/v0.1"
RECORD_KEYS = ("sources", "groups", "frames", "targets", "candidates", "contrast_slots",
               "new_review_rows", "reused_controls", "totals")
TARGET_KEYS = ("target_id", "continuous_source_id", "source_frame_index", "source_pts_ticks",
               "role", "block_id", "block_range_inclusive", "context_range_inclusive", "segment_id")
_read = appearance._read
_path = appearance._path
_output = appearance._output


def implementation_bindings(root):
    return [d.binding(root, root / "src/ball_tracking" / name) for name in (
        "nba_ball_distractor_reference.py", "nba_appearance_reference.py", "nba_gap_anchor_reference.py",
        "nba_annotations.py", "nba_wasb_diagnostic.py", "wasb_development_observation.py")]


def census(root, proposal, approval, proposal_binding):
    """Validate exact approved metadata and reconstruct source/blank-label rows."""
    d.require(proposal["schema_version"] == PROPOSAL_SCHEMA
              and approval["schema_version"] == APPROVAL_SCHEMA and approval["status"] == "approved"
              and approval["approved_by"] == "Ryan" and approval["label_preparation_authorized"] is True
              and approval["proposal"] == proposal_binding and approval["plan"] == proposal["plan"]
              and approval["design_evidence"] == proposal["design_evidence"], "Approval/proposal binding differs")
    d.bound(root, proposal["plan"])
    evidence, authorities = proposal["design_evidence"], proposal["authorities"]
    grid = _read(root, evidence["grid"])
    complete = _read(root, evidence["full_pool_reconstruction"])
    registry = _read(root, evidence["candidate_registry"])
    contrasts = _read(root, evidence["contrast_slots"])
    d.require(complete["grid"] == evidence["grid"] and registry["grid"] == evidence["grid"]
              and registry["full_pool_completion"] == evidence["full_pool_reconstruction"]
              and contrasts["candidate_registry"] == evidence["candidate_registry"], "Inventory bindings differ")
    selection = _read(root, authorities["selection"])
    accepted = _read(root, authorities["accepted_appearance"])
    regression = _read(root, authorities["old_34_regression_preparation"])
    d.require(accepted["status"] == "human_accepted_assisted_reference", "Accepted controls required")
    excluded = {(f["continuous_source_id"], f["source_frame_index"])
                for f in accepted["frames"] + regression["frames"]}
    fit_config = _read(root, authorities["nba_fit_authority"])
    d.require(fit_config["nfhs_training_config"] == authorities["nfhs_fit_authority"], "Fit authority join differs")
    training = appearance._training_blocks(root, {"fit_authority": authorities["nba_fit_authority"]})
    sources = {s["candidate_id"]: s for s in selection["sources"]}
    blocks = proposal["source_blocks"]
    source_roles = {}
    for block in blocks.values():
        cid, role, span = block["source"], block["role"], block["range_inclusive"]
        d.require(role in {"fit", "check"} and cid in sources, "Unknown source role")
        d.require(cid not in source_roles or source_roles[cid] == role, "Source crosses fit/check roles")
        source_roles[cid] = role
        source = sources[cid]
        d.require(any(a <= span[0] <= span[1] <= b for a, b in (s["range_inclusive"] for s in source["segments"]))
                  and not any(max(span[0], a) <= min(span[1], b) for a, b in source["protected_ranges"]),
                  "Historical block touches protected or unavailable frames")
        if role == "fit":
            matches = [t for t in training if t[0] == cid and t[1] == span]
            d.require(matches and all(t[2] is None or t[2] == source["source_video"] for t in matches),
                      "Fit block is not a bound historical training block")
    for cid in source_roles:
        appearance._source_authority(root, sources[cid])
    timelines = {cid: {f["source_frame_index"]: f for f in s["frames"]} for cid, s in sources.items()}
    grid_targets = {t["target_id"]: t for t in grid["targets"]}
    completed_targets = {b["path"]: b for b in complete["target_records"]}
    candidates = registry["candidate_records"]
    d.require(len({c["candidate_group_id"] for c in candidates}) == len(candidates), "Duplicate candidate identity")
    targets, target_records = {}, {}
    for candidate in candidates:
        cid, index, tid = (candidate[k] for k in ("continuous_source_id", "source_frame_index", "target_id"))
        target = {k: candidate[k] for k in TARGET_KEYS}
        d.require(target == grid_targets.get(tid), "Candidate is not the frozen grid target")
        block = blocks[candidate["block_id"]]
        d.require((cid, candidate["role"], candidate["block_range_inclusive"]) ==
                  (block["source"], block["role"], block["range_inclusive"]), "Candidate block/role differs")
        lo, hi = candidate["context_range_inclusive"]
        d.require([lo, hi] == [index-2, index+2] and block["range_inclusive"][0] <= lo <= hi <= block["range_inclusive"][1],
                  "Target context leaves its historical block")
        d.require(candidate["target_record"] == completed_targets.get(candidate["target_record"]["path"]),
                  "Candidate target was not in completed reconstruction")
        if tid not in target_records:
            target_records[tid] = _read(root, candidate["target_record"])
        record = target_records[tid]; original = timelines[cid][index]
        d.require(record["grid"] == evidence["grid"] and record["target"] == target
                  and record["original_mean_reproduced_exactly"] is True
                  and record["original_observation"] == original["original_observation"], "Saved original producer differs")
        d.require(candidate["source_video"] == record["source_video"] == sources[cid]["source_video"]
                  and candidate["source_frame"] == record["source_frame"] == original["source_frame"]
                  and candidate["source_pts_ticks"] == original["source_pts_ticks"], "Candidate source/clock differs")
        groups = {g["candidate_group_id"]: g for g in record["candidate_groups"]}
        group = groups[candidate["candidate_group_id"]]
        d.require(all(candidate[k] == group[k] for k in ("center_xy_px", "provenance_ids", "provenance_kinds", "emitted_in_saved_selection"))
                  and candidate["pool_record_indices"] == group["record_indices"]
                  and candidate["components"] == [record["pool"]["records"][i]["component"] for i in group["record_indices"]]
                  and candidate["provenance_ids"] == [record["pool"]["records"][i]["provenance_id"] for i in group["record_indices"]],
                  "Candidate coordinates or component provenance changed")
        x, y = candidate["center_xy_px"]
        d.require(all(type(v) in (int, float) and math.isfinite(v) for v in (x, y))
                  and 0 <= x < sources[cid]["source_video"]["width_px"] and 0 <= y < sources[cid]["source_video"]["height_px"]
                  and candidate["object_classification"] is None and candidate["physical_object_instance_id"] is None,
                  "New candidate is labeled or out of bounds")
        targets[tid] = target
    d.require(Counter(c["block_id"] for c in candidates) == Counter({k: b["candidate_quota"] for k, b in blocks.items()}),
              "Candidate block quotas differ")
    groups, frames, seen = [], [], set()
    for tid, target in targets.items():
        cid, index = target["continuous_source_id"], target["source_frame_index"]
        groups.append({"group_id": tid, "continuous_source_id": cid, "block_id": target["block_id"],
                       "role": target["role"], "context_range_inclusive": target["context_range_inclusive"], "target_ids": [tid]})
        for n in range(index-2, index+3):
            pair = (cid, n); original = timelines[cid][n]
            d.require(pair not in seen and pair not in excluded and original["decision"] != "withheld",
                      "New context overlaps another context, prior review, or protected frame")
            seen.add(pair)
            frames.append({"group_id": tid, "continuous_source_id": cid, "source_frame_index": n,
                "source_pts_ticks": original["source_pts_ticks"], "container_pts_ticks": original.get("container_pts_ticks"),
                "time_base": "1/90000", "time_origin": sources[cid]["time_origin"], "source_frame": copy.deepcopy(original["source_frame"]),
                "role": "target" if n == index else "context_only", "target_id": tid if n == index else None})
    slots = contrasts["slots"]; slot_frames = set()
    for slot in slots:
        pair = (slot["continuous_source_id"], slot["source_frame_index"])
        tid = f"{pair[0]}:{pair[1]}"
        d.require(pair not in slot_frames and tid in targets, "Contrast repeats or leaves selected targets")
        slot_frames.add(pair); target = targets[tid]; record = target_records[tid]
        d.require(slot["role"] == "fit_only_contrast" and target["role"] == "fit"
                  and slot["requested_subtype"] in {"head", "hand", "clothing"}
                  and slot["domain"] == sources[pair[0]]["kind"] and slot["replacement_allowed"] is False,
                  "Contrast role/domain/request differs")
        d.require(all(slot[k] == target[k] for k in ("continuous_source_id", "source_frame_index", "source_pts_ticks",
                  "block_id", "block_range_inclusive", "context_range_inclusive"))
                  and slot["source_video"] == record["source_video"] and slot["source_frame"] == record["source_frame"]
                  and slot["object_center_xy_px"] is None and slot["object_classification"] is None
                  and slot["physical_object_instance_id"] is None, "Contrast source/blank judgment differs")
    d.require(len({s["slot_id"] for s in slots}) == len(slots), "Duplicate contrast identity")
    controls = []
    d.require(len(accepted["rows"]) == len(accepted["candidates"]), "Accepted control census differs")
    for candidate, row in zip(accepted["candidates"], accepted["rows"]):
        cid, index = candidate["continuous_source_id"], candidate["source_frame_index"]
        matching = [(bid, b) for bid, b in blocks.items() if b["source"] == cid and b["range_inclusive"][0] <= index <= b["range_inclusive"][1]]
        d.require(candidate["candidate_key"] == row["candidate_key"] and len(matching) == 1, "Accepted control block/source join differs")
        bid, block = matching[0]
        d.require(candidate["role"] == {"fit": "fit_eligible", "check": "excluded_check"}[block["role"]], "Accepted control role crossing")
        controls.append({"accepted_candidate": copy.deepcopy(candidate), "accepted_row": copy.deepcopy(row),
                         "historical_block": {"block_id": bid, **copy.deepcopy(block)},
                         "physical_object_instance_id": None, "episode_id": None})
    rows = []
    for item in candidates + slots:
        contrast = "slot_id" in item
        rows.append({"row_id": item["slot_id"] if contrast else item["candidate_group_id"],
            "origin": "source_authored_contrast" if contrast else "saved_detector_candidate",
            "continuous_source_id": item["continuous_source_id"], "source_frame_index": item["source_frame_index"],
            "center_xy_px": None if contrast else copy.deepcopy(item["center_xy_px"]),
            "classification": None, "subtype": None, "physical_object_instance_id": None, "episode_id": None, "rationale": None})
    budget = proposal["new_label_budget"]
    totals = {"targets": len(targets), "candidates": len(candidates), "contrast_slots": len(slots),
              "new_review_rows": len(rows), "context_frames": len(frames), "reused_controls": len(controls),
              "prior_context_frames_excluded": len(excluded)}
    d.require(Counter(c["role"] for c in candidates) == Counter(fit=budget["candidate_fit"], check=budget["candidate_excluded_check"])
              and len(slots) == budget["source_authored_fit_contrast_slots"] and len(rows) == budget["total_attempted_maximum"]
              and len(targets) == budget["unique_target_frames"] and len(frames) == budget["unique_context_frames"]
              and budget["context_radius_frames"] == 2 and budget["replacements_allowed"] is False, "Approved census totals differ")
    return {"sources": [source_reference.source_metadata(sources[cid]) for cid in sources if cid in source_roles],
            "groups": groups, "frames": frames, "targets": list(targets.values()), "candidates": copy.deepcopy(candidates),
            "contrast_slots": copy.deepcopy(slots), "new_review_rows": rows, "reused_controls": controls, "totals": totals}, sources


def freeze(root, proposal_path, approval_path, output_dir):
    root = Path(root).resolve(); proposal_path = _path(root, proposal_path); approval_path = _path(root, approval_path)
    records, _ = census(root, d.read_json(proposal_path), d.read_json(approval_path), d.binding(root, proposal_path))
    document = {"schema_version": METADATA_SCHEMA, "status": "metadata_frozen_before_pixels",
        "bindings": {"proposal": d.binding(root, proposal_path), "approval": d.binding(root, approval_path),
                     "implementation": implementation_bindings(root)}, **records, "new_labels_created": False, "pixel_reads": 0}
    d.write_once(_output(root, output_dir) / "metadata.json", document)
    return document


def load_frozen(root, path):
    document = d.read_json(_path(root, path))
    d.require(document["schema_version"] == METADATA_SCHEMA and document["status"] == "metadata_frozen_before_pixels"
              and document["new_labels_created"] is False and document["pixel_reads"] == 0, "Invalid source metadata freeze")
    for binding in document["bindings"]["implementation"]:
        d.bound(root, binding)
    records, sources = census(root, _read(root, document["bindings"]["proposal"]), _read(root, document["bindings"]["approval"]),
                              document["bindings"]["proposal"])
    d.require(all(document[k] == records[k] for k in RECORD_KEYS), "Frozen census changed")
    return document, sources


def prepare(root, proposal_path, approval_path, output_dir):
    root = Path(root).resolve(); output = _output(root, output_dir); metadata_path = output / "metadata.json"
    if not metadata_path.exists():
        freeze(root, proposal_path, approval_path, output)
    frozen, sources = load_frozen(root, metadata_path)
    d.require(frozen["bindings"]["proposal"] == d.binding(root, _path(root, proposal_path))
              and frozen["bindings"]["approval"] == d.binding(root, _path(root, approval_path)), "Existing metadata has different authority")
    if (output / "preparation_ready.json").exists():
        return load_ready_preparation(root, output / "preparation.json")
    attempt = output / "attempts" / uuid.uuid4().hex; started = time.perf_counter()
    resources = {"model_calls": 0, "candidate_array_reads": 0, "new_labels_created": 0,
                 "existing_png_reads": 0, "nfhs_decoded_frames": 0, "nfhs_requested_segments": []}
    binding = d.binding(root, metadata_path)
    d.write_once(attempt / "started.json", {"metadata": binding, "created_at_utc": d.stamp()})
    try:
        for source in frozen["sources"]:
            if source["kind"] == "nfhs":
                d.require(d.digest(d.contained(root, source["source_video"]["path"])) == source["source_video"]["sha256"],
                          "NFHS source video bytes changed before extraction")
        frames = copy.deepcopy(frozen["frames"])
        source_reference.extract_frames(root, list(sources.values()), frozen["groups"], frames, attempt / "frames", resources)
        preparation = {"schema_version": SCHEMA, "status": "source_preparation_complete", "metadata": binding,
            **{k: copy.deepcopy(frozen[k]) for k in RECORD_KEYS if k != "frames"}, "frames": frames,
            "new_labels_created": False, "resources": resources, "human_new_label_review": "pending"}
        d.write_once(output / "preparation.json", preparation)
        d.write_once(output / "preparation_ready.json", {"metadata": binding, "preparation": d.binding(root, output / "preparation.json"),
                                                       "new_labels_created": False})
        d.write_once(attempt / "completed.json", {"preparation": d.binding(root, output / "preparation.json"),
            "resources": resources, "elapsed_seconds": time.perf_counter()-started})
        return preparation
    except Exception as error:
        d.write_once(attempt / "failed.json", {"status": "failed_preserved", "error_type": type(error).__name__, "error": str(error),
            "metadata": binding, "resources": resources, "elapsed_seconds": time.perf_counter()-started})
        raise


def load_ready_preparation(root, path, *, verify_images=True):
    root = Path(root).resolve(); path = _path(root, path); preparation = d.read_json(path)
    ready = d.read_json(path.with_name("preparation_ready.json"))
    d.require(ready["preparation"] == d.binding(root, path) and ready["metadata"] == preparation["metadata"]
              and ready["new_labels_created"] is False and preparation["new_labels_created"] is False
              and preparation["schema_version"] == SCHEMA and preparation["status"] == "source_preparation_complete",
              "Source preparation changed after freeze")
    frozen, sources = load_frozen(root, d.bound(root, preparation["metadata"]))
    d.require(all(preparation[k] == frozen[k] for k in RECORD_KEYS if k != "frames")
              and [{k: v for k, v in f.items() if k != "raw_png"} for f in preparation["frames"]] == frozen["frames"],
              "Prepared source/candidate transport differs")
    for frame in preparation["frames"]:
        _output(root, frame["raw_png"]["path"])
        if verify_images:
            source_reference.verify_raw_png(root, frame, sources[frame["continuous_source_id"]])
    return preparation


def validate_preparation(root, path, *, verify_images=False):
    return load_ready_preparation(root, path, verify_images=verify_images)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true", required=True)
    parser.add_argument("--proposal", required=True); parser.add_argument("--approval", required=True)
    parser.add_argument("--output", required=True); args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    result = prepare(root, args.proposal, args.approval, args.output)
    print(json.dumps({"status": result["status"], "totals": result["totals"], "resources": result["resources"]}))


if __name__ == "__main__":
    main()
