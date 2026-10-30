"""Merge assisted reference proposals and report provisional object-group adequacy.

Human review remains pending. This module never reads pixels, features, heatmaps,
or models, and never authorizes fitting from provisional counts.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import json
import math
from pathlib import Path

from . import nba_ball_distractor_reference as reference
from . import nba_wasb_diagnostic as d

SCHEMA = "nba_ball_distractor_reference_proposal/v0.1"
CLASSES = {"ball", "other_object", "unresolved"}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _point(value, size):
    return isinstance(value, list) and len(value) == 2 and all(type(v) in (int, float) and math.isfinite(v) for v in value) \
        and 0 <= value[0] < size[0] and 0 <= value[1] < size[1]


def _judgment(row):
    d.require(row["classification"] in CLASSES and _text(row["rationale"]), "Classification and source rationale required")
    resolved = row["classification"] != "unresolved"
    d.require((resolved and _text(row["physical_object_instance_id"]) and _text(row["episode_id"]))
              or (not resolved and row["physical_object_instance_id"] is None and row["episode_id"] is None),
              "Resolved objects need groups/episodes; unknowns must remain ungrouped")
    d.require((_text(row["subtype"]) if row["classification"] == "other_object" else row["subtype"] is None),
              "Only resolved other objects have subtypes")


def _derived(item, source, *, origin, role, block_id, classification, subtype, physical_id, episode_id,
             row_id, provenance_kinds=(), emitted=False):
    return {"row_id": row_id, "origin": origin, "role": role, "block_id": block_id,
        "continuous_source_id": item["continuous_source_id"], "source_frame_index": item["source_frame_index"],
        "domain": source["kind"], "classification": classification, "subtype": subtype,
        "physical_object_instance_id": physical_id, "episode_id": episode_id,
        "provenance_kinds": list(provenance_kinds), "emitted_in_saved_selection": emitted}


def physical_groups(rows, derived):
    """Resolve aliases within a frame, preserving every row and independent role."""
    groups = {}; by_row = {r["row_id"]: r for r in derived}
    for row in derived:
        if row["classification"] == "unresolved":
            continue
        key = (row["continuous_source_id"], row["source_frame_index"], row["physical_object_instance_id"])
        if key not in groups:
            groups[key] = {k: copy.deepcopy(row[k]) for k in ("continuous_source_id", "source_frame_index", "physical_object_instance_id",
                "episode_id", "classification", "subtype", "domain", "role", "block_id")}
            groups[key].update({"row_ids": [], "origins": [], "provenance_kinds": [], "new_detector_candidate": False,
                                "new_emitted_detector_candidate": False, "supplemental_duplicate_row_ids": []})
        group = groups[key]
        d.require(all(group[k] == row[k] for k in ("classification", "subtype", "role", "domain", "block_id", "episode_id")),
                  "Conflicting resolved classes, subtypes, roles or episodes within one physical object group")
        group["row_ids"].append(row["row_id"])
        group["origins"] = sorted(set(group["origins"]) | {row["origin"]})
        group["provenance_kinds"] = sorted(set(group["provenance_kinds"]) | set(row["provenance_kinds"]))
        if row["origin"] == "saved_detector_candidate":
            group["new_detector_candidate"] = True
            group["new_emitted_detector_candidate"] |= row["emitted_in_saved_selection"]
    for row in rows:
        resolved = row["classification"] != "unresolved"
        member = by_row[row["row_id"]]
        duplicate = row.get("duplicate_of_row_id")
        if member["origin"] != "source_authored_contrast":
            d.require(duplicate is None, "Detector candidate aliases use physical grouping, not supplemental duplicate fields")
            continue
        if not resolved:
            d.require(duplicate is None, "Unknown contrast cannot assert a duplicate identity")
            continue
        key = (member["continuous_source_id"], member["source_frame_index"], member["physical_object_instance_id"])
        group = groups[key]
        candidate_ids = [rid for rid in group["row_ids"] if by_row[rid]["origin"] == "saved_detector_candidate"]
        d.require(duplicate is None or duplicate in candidate_ids, "Contrast duplicate must join a same-frame resolved candidate object")
        if candidate_ids:
            row["duplicate_of_row_id"] = duplicate or candidate_ids[0]
            group["supplemental_duplicate_row_ids"].append(row["row_id"])
    return list(groups.values())


def adequacy(groups, limits, derived):
    """Count source/frame/object units; every scientific minimum comes from plan."""
    checks = []
    def minimum(name, value, required):
        checks.append({"name": name, "actual": value, "required_minimum": required, "passed": value >= required})
    def present(name, values, required):
        actual = sorted(set(values)); needed = sorted(set(required))
        checks.append({"name": name, "actual": actual, "required": needed, "passed": set(needed) <= set(actual)})
    def subset(role=None, classification=None, domain=None):
        return [g for g in groups if (role is None or g["role"] == role) and (classification is None or g["classification"] == classification)
                and (domain is None or g["domain"] == domain)]
    for role in ("fit", "check"):
        selected = subset(role)
        minimum(role+"_groups", len(selected), limits[role+"_groups_min"])
        minimum(role+"_ball_groups", len(subset(role, "ball")), limits[role+"_ball_groups_min"])
        minimum(role+"_other_groups", len(subset(role, "other_object")), limits[role+"_other_groups_min"])
        contributors = [g for g in selected if "contributor" in g["provenance_kinds"]]
        minimum(role+"_contributor_groups", len(contributors), limits["each_role_contributor_resolved_groups_min"])
        minimum(role+"_contributor_blocks", len({g["block_id"] for g in contributors}), limits["each_role_contributor_blocks_min"])
        present(role+"_contributor_classes", [g["classification"] for g in contributors], limits["each_role_contributor_classes_required"])
    for classification, short in (("ball", "ball"), ("other_object", "other")):
        selected = subset("fit", classification, "nfhs")
        minimum("nfhs_fit_"+short+"_groups", len(selected), limits["nfhs_fit_"+short+"_groups_min"])
        minimum("nfhs_fit_"+short+"_blocks", len({g["block_id"] for g in selected}), limits["nfhs_blocks_per_class_min"])
    new_negative = [g for g in subset("fit", "other_object") if g["new_detector_candidate"]]
    minimum("new_detector_fit_other_groups", len(new_negative), limits["new_detector_fit_other_groups_min"])
    minimum("new_detector_fit_other_blocks", len({g["block_id"] for g in new_negative}), limits["new_detector_fit_other_blocks_min"])
    minimum("new_nfhs_detector_fit_other_groups", sum(g["domain"] == "nfhs" for g in new_negative), limits["new_nfhs_detector_fit_other_groups_min"])
    for subtype in ("head", "clothing"):
        minimum("fit_"+subtype+"_blocks", len({g["block_id"] for g in subset("fit", "other_object") if g["subtype"] == subtype}),
                limits["fit_"+subtype+"_blocks_min"])
    for domain in ("nba", "nfhs"):
        present("check_"+domain+"_classes", [g["classification"] for g in subset("check", domain=domain)], limits["check_each_domain_classes_required"])
    present("check_other_subtypes", [g["subtype"] for g in subset("check", "other_object")], limits["check_other_subtypes_required"])
    emitted = [g for g in subset("check", "other_object") if g["new_emitted_detector_candidate"]]
    minimum("new_excluded_emitted_other_episodes", len({(g["block_id"], g["episode_id"]) for g in emitted}), limits["new_excluded_emitted_other_episodes_min"])
    minimum("new_excluded_emitted_other_blocks", len({g["block_id"] for g in emitted}), limits["new_excluded_emitted_other_distinct_blocks_min"])
    present("new_excluded_emitted_other_subtypes", ["head" if g["subtype"] == "head" else "one_non_head" for g in emitted],
            limits["new_excluded_emitted_other_subtypes"])
    counts = {role: {domain: dict(Counter(g["classification"] for g in subset(role, domain=domain))) for domain in ("nba", "nfhs")}
              for role in ("fit", "check")}
    return {"status": "provisional_human_review_pending", "count_unit": "resolved source/frame/physical-object group",
        "limits": copy.deepcopy(limits), "checks": checks, "all_numerical_gates_passed": all(c["passed"] for c in checks),
        "failed_gates": [c["name"] for c in checks if not c["passed"]], "resolved_group_counts": counts,
        "resolved_groups": len(groups), "unknown_rows_unscored": sum(r["classification"] == "unresolved" for r in derived),
        "supplemental_duplicate_rows_excluded": sum(len(g["supplemental_duplicate_row_ids"]) for g in groups),
        "feature_extraction_authorized": False, "fit_authorized": False,
        "human_acceptance_required": True, "failure_action": limits["failure_action"]}


def build(preparation, proposal, documents, reused):
    """Pure merge: annotation metadata never supplies authoritative roles/points."""
    sources = {s["candidate_id"]: s for s in preparation["sources"]}
    candidates = {c["candidate_group_id"]: c for c in preparation["candidates"]}
    slots = {s["slot_id"]: s for s in preparation["contrast_slots"]}
    supplied = {}
    for document in documents:
        author = document["authorship"]
        d.require(_text(author["annotator_id"]) and _text(author["method"]) and author["not_blind"] is True,
                  "Honest assisted-reference authorship required")
        d.require(document.get("human_review", "pending") == "pending", "New human reference acceptance is not established here")
        for row in document["rows"]:
            d.require(row["row_id"] not in supplied, "Duplicate annotation row")
            supplied[row["row_id"]] = copy.deepcopy(row)
    d.require(set(supplied) == {r["row_id"] for r in preparation["new_review_rows"]}, "Complete exact new annotation census required")
    rows, derived = [], []
    for blank in preparation["new_review_rows"]:
        row = supplied[blank["row_id"]]; _judgment(row)
        contrast = row["row_id"] in slots
        item = slots[row["row_id"]] if contrast else candidates[row["row_id"]]
        source = sources[item["continuous_source_id"]]
        if contrast:
            d.require((row["classification"] == "unresolved" and row["center_xy_px"] is None)
                      or (row["classification"] == "other_object" and row["subtype"] == item["requested_subtype"]
                          and _point(row["center_xy_px"], (source["source_video"]["width_px"], source["source_video"]["height_px"]))),
                      "Contrast must be a source-authored requested object or a null unknown")
            extent = row.get("object_extent_xyxy_px")
            if extent is not None:
                width, height = source["source_video"]["width_px"], source["source_video"]["height_px"]
                d.require(isinstance(extent, list) and len(extent) == 4 and all(type(v) in (int, float) and math.isfinite(v) for v in extent)
                          and 0 <= extent[0] < extent[2] <= width and 0 <= extent[1] < extent[3] <= height
                          and row["classification"] == "other_object", "Invalid authored contrast extent")
        else:
            d.require(row["center_xy_px"] == item["center_xy_px"], "Saved detector candidate coordinates must remain exact")
        metadata = _derived(item, source, origin=blank["origin"], role="fit" if contrast else item["role"], block_id=item["block_id"],
            classification=row["classification"], subtype=row["subtype"], physical_id=row["physical_object_instance_id"],
            episode_id=row["episode_id"], row_id=row["row_id"], provenance_kinds=() if contrast else item["provenance_kinds"],
            emitted=False if contrast else item["emitted_in_saved_selection"])
        for name in ("origin", "role", "block_id", "continuous_source_id", "source_frame_index", "domain"):
            d.require(name not in row or row[name] == metadata[name], "Annotation attempts to change source/role/origin")
        if "inspected_context_indices" in row:
            lo, hi = item["context_range_inclusive"]
            d.require(row["inspected_context_indices"] == list(range(lo, hi+1)), "Inspection context differs from approved five frames")
        row.update(metadata); row.setdefault("duplicate_of_row_id", None)
        rows.append(row); derived.append(metadata)
    d.require(reused["accepted_reference"] == proposal["authorities"]["accepted_appearance"]
              and reused["accepted_classes_changed"] is False, "Existing accepted labels cannot change")
    old = {r["candidate_key"]: r for r in reused["rows"]}
    expected_keys = [r["accepted_candidate"]["candidate_key"] for r in preparation["reused_controls"]]
    d.require(len(old) == len(reused["rows"]) and set(old) == set(expected_keys), "Exact existing grouping census required")
    grouping = []
    for control in preparation["reused_controls"]:
        candidate, label, block = (control[k] for k in ("accepted_candidate", "accepted_row", "historical_block"))
        row = copy.deepcopy(old[candidate["candidate_key"]])
        d.require(row["accepted_classification_unchanged"] == label["classification"] and row["block_id"] == block["block_id"]
                  and row["role"] == block["role"], "Accepted classification or historical role changed")
        judgment = {**row, "classification": label["classification"], "subtype": label["subtype"]}; _judgment(judgment)
        derived.append(_derived(candidate, sources[candidate["continuous_source_id"]], origin="existing_accepted_reference", role=block["role"],
            block_id=block["block_id"], classification=label["classification"], subtype=label["subtype"],
            physical_id=row["physical_object_instance_id"], episode_id=row["episode_id"], row_id=candidate["candidate_key"], provenance_kinds=("mean",)))
        grouping.append(row)
    groups = physical_groups(rows, derived)
    return {"rows": rows, "reused_grouping": grouping, "physical_groups": groups,
        "provisional_adequacy": adequacy(groups, proposal["pre_fit_adequacy"], derived),
        "counts": {"new_rows": len(rows), "new_classifications": dict(Counter(r["classification"] for r in rows)),
                   "reused_rows": len(grouping), "physical_groups": len(groups)}}


def merge(root, preparation_path, annotation_paths, reused_grouping_path, output_dir):
    root = Path(root).resolve(); prep_path = reference._path(root, preparation_path)
    prep = reference.load_ready_preparation(root, prep_path, verify_images=False)
    frozen = reference._read(root, prep["metadata"]); proposal = reference._read(root, frozen["bindings"]["proposal"])
    inputs = [d.binding(root, reference._path(root, p)) for p in annotation_paths]
    reused_binding = d.binding(root, reference._path(root, reused_grouping_path))
    documents = [reference._read(root, b) for b in inputs]; reused = reference._read(root, reused_binding)
    result = {"schema_version": SCHEMA, "status": "assisted_reference_proposal_human_review_pending", "human_review": "pending",
        "preparation": d.binding(root, prep_path), "authorship": {"method": "merged_source_first_ai_proposals", "not_blind": True,
            "contributors": [v["authorship"] for v in documents], "existing_grouping": reused["authorship"]},
        "bindings": {"annotation_inputs": inputs, "reused_grouping": reused_binding,
            "implementation": d.binding(root, root / "src/ball_tracking/nba_ball_distractor_reference_labels.py")},
        **build(prep, proposal, documents, reused), "feature_extraction_performed": False, "fitting_performed": False}
    output = reference._output(root, output_dir)
    d.write_once(output / "proposal.json", result)
    d.write_once(output / "proposal_seal.json", {"proposal": d.binding(root, output / "proposal.json"), "created_at_utc": d.stamp(),
                                                "human_review": "pending"})
    return result


def load_proposal(root, path):
    root = Path(root).resolve(); path = reference._path(root, path); result = d.read_json(path)
    seal = d.read_json(path.with_name("proposal_seal.json"))
    d.require(seal["proposal"] == d.binding(root, path) and result["schema_version"] == SCHEMA
              and result["human_review"] == "pending" and result["feature_extraction_performed"] is False
              and result["fitting_performed"] is False, "Proposed references changed or falsely accepted")
    d.bound(root, result["bindings"]["implementation"])
    prep = reference.load_ready_preparation(root, d.bound(root, result["preparation"]), verify_images=False)
    metadata = reference._read(root, prep["metadata"]); proposal = reference._read(root, metadata["bindings"]["proposal"])
    expected = build(prep, proposal, [reference._read(root, b) for b in result["bindings"]["annotation_inputs"]],
                     reference._read(root, result["bindings"]["reused_grouping"]))
    d.require(all(result[k] == value for k, value in expected.items()), "Merged annotation/grouping/adequacy transport differs")
    return prep, result


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--preparation", required=True)
    parser.add_argument("--annotations", nargs="+", required=True); parser.add_argument("--reused-grouping", required=True)
    parser.add_argument("--output", required=True); args = parser.parse_args()
    result = merge(Path(__file__).resolve().parents[2], args.preparation, args.annotations, args.reused_grouping, args.output)
    print(json.dumps({"counts": result["counts"], "provisional_adequacy": result["provisional_adequacy"]}))


if __name__ == "__main__":
    main()
