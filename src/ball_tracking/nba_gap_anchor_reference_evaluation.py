"""Publish accepted AI references and score immutable saved gap decisions.

Only JSON metadata is read. Source images, videos, model arrays and the original
790-frame report are never modified. Qualitative object judgments are separate.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path

from . import annotations
from . import nba_annotations as nba
from . import nba_candidate_preservation as pools
from . import nba_gap_anchor_reference as preparation
from . import nba_temporal_gap_selection as selector
from . import nba_wasb_diagnostic as d

ACCEPTANCE_SCHEMA = "nba_gap_anchor_reference_acceptance/v0.1"
REFERENCE_SCHEMA = "nba_gap_anchor_reference_accepted/v0.1"
SCHEMA = "nba_gap_anchor_reference_evaluation/v0.1"


def bound_json(root, binding):
    return d.read_json(d.bound(root, binding))


def output_path(root, output):
    path = (root / output).resolve()
    d.require(path.is_relative_to(root / "data/outputs"), "Generated references/reports must remain ignored")
    return path


def code_bindings(root):
    return [d.binding(root, root / "src/ball_tracking" / name) for name in
            ("nba_gap_anchor_reference_evaluation.py", "nba_temporal_gap_selection.py",
             "nba_candidate_preservation.py", "annotations.py", "nba_gap_anchor_reference.py",
             "nba_wasb_diagnostic.py")]


def load_acceptance(root, acceptance_path):
    """Verify accepted draft, original preparation and delivered media identity."""
    root = Path(root).resolve(); path = (root / acceptance_path).resolve()
    d.require(path.is_relative_to(root), "Acceptance must be inside repository")
    acceptance = d.read_json(path)
    d.require(acceptance["schema_version"] == ACCEPTANCE_SCHEMA and acceptance["status"] == "accepted"
              and acceptance["reviewer_id"] == "Ryan"
              and acceptance["annotation_origin"] == "assistant_visual_proposal"
              and acceptance["review_method"] == "human_visual_acceptance_of_assisted_proposals",
              "Human acceptance of the AI proposal is required")
    d.require(isinstance(acceptance["user_statement"], str) and acceptance["user_statement"].strip(),
              "Exact acceptance statement required")
    reviewed = datetime.fromisoformat(acceptance["reviewed_at_utc"].replace("Z", "+00:00"))
    d.require(reviewed.tzinfo is not None and reviewed.utcoffset() == timezone.utc.utcoffset(reviewed),
              "Acceptance timestamp must be explicit UTC")
    d.require(acceptance["accepted_new_references"] == 27 and acceptance["reused_controls_unchanged"] == 7
              and acceptance["evaluation_authorized"] is True and acceptance["evaluation_radius_px"] == 10,
              "Accepted scope or unchanged scoring radius differs")
    d.require(acceptance["semantic_object_adjudication"] == "not_separately_reported",
              "This acceptance does not independently adjudicate semantic object findings")
    prepared_result = bound_json(root, acceptance["preparation_result"])
    d.require(all(prepared_result[k] == acceptance[k] for k in ("preparation", "proposal", "proposal_seal"))
              and prepared_result["media"]["completion"] == acceptance["review_completion"],
              "Accepted preparation result/proposal/media binding differs")
    proposal = bound_json(root, acceptance["proposal"])
    seal = bound_json(root, acceptance["proposal_seal"])
    sealed_at = datetime.fromisoformat(seal["created_at_utc"].replace("Z", "+00:00"))
    d.require(sealed_at.tzinfo is not None and reviewed >= sealed_at, "Acceptance predates sealed reference proposal")
    d.require(seal["schema_version"] == "nba_gap_anchor_reference_proposal_seal/v0.1"
              and seal["proposal"] == acceptance["proposal"]
              and seal["preparation"] == acceptance["preparation"] == proposal["preparation"]
              and seal["new_targets"] == 27 and seal["reused_controls"] == 7,
              "Accepted proposal differs from its source-first seal")
    prepared = preparation.load_ready_preparation(root, d.bound(root, acceptance["preparation"]), verify_images=False)
    d.require(set(proposal) == {"schema_version", "preparation", "status", "authorship", "human_review",
                               "new_annotations", "existing_controls"}
              and proposal["schema_version"] == preparation.PROPOSAL_SCHEMA
              and proposal["status"] == "draft" and proposal["human_review"] == "pending",
              "Original pending proposal was changed")
    author = proposal["authorship"]
    d.require(set(author) == {"annotator_id", "method", "not_blind"}
              and isinstance(author["annotator_id"], str) and bool(author["annotator_id"].strip())
              and author["method"] == "source_first_ai" and author["not_blind"] is True,
              "AI authorship or non-blind source-first provenance changed")
    expected_new = [preparation.key(r) for r in prepared["frames"] if r["reference_origin"] == "new"]
    d.require([preparation.key(r) for r in proposal["new_annotations"]] == expected_new,
              "New reference census differs")
    sources = {s["candidate_id"]: s for s in prepared["sources"]}
    for index, row in enumerate(proposal["new_annotations"]):
        d.require(set(row) == {"continuous_source_id", "source_frame_index", "annotation"}, "Unknown new reference fields")
        source = sources[row["continuous_source_id"]]["source_video"]
        parsed = annotations.FrameAnnotation.from_mapping(row["annotation"], index,
            nba._PixelBounds(source["width_px"], source["height_px"]))
        d.require(parsed.frame_index == row["source_frame_index"] < source["frame_count"]
                  and parsed.annotation_status == "labeled", "Reference/source frame differs or lacks a judgment")
    controls = [{"continuous_source_id": r["continuous_source_id"], "source_frame_index": r["source_frame_index"],
                 "existing_reference": r["existing_reference"]} for r in prepared["frames"] if r["reference_origin"] == "existing"]
    d.require(proposal["existing_controls"] == controls, "Seven accepted control rows/provenance changed")
    media = bound_json(root, acceptance["review_completion"])
    d.require(media["status"] == "completed" and media["identity"]["proposal"] == acceptance["proposal"]
              and media["identity"]["preparation"] == acceptance["preparation"]
              and media["artifacts"]["video"] == acceptance["review_video"]
              and media["artifacts"]["guide"] == acceptance["review_guide"], "Accepted presented review differs")
    # The completed review's existing bindings are the media authority. Do not
    # re-read image/video bytes or repeat completed pixel/timing verification.
    for name in ("review_video", "review_guide"):
        item = acceptance[name]; media_path = d.contained(root, item["path"])
        d.require(media_path.stat().st_size == item["bytes"], "Presented media size changed")
    return acceptance, d.binding(root, path), prepared, proposal


def reference_document(root, acceptance_path):
    acceptance, binding, prepared, proposal = load_acceptance(root, acceptance_path)
    return {"schema_version": REFERENCE_SCHEMA, "status": "human_accepted_assisted_reference",
        "acceptance": binding, "human_review": {k: acceptance[k] for k in
            ("status", "reviewer_id", "reviewed_at_utc", "user_statement", "review_method", "semantic_object_adjudication")},
        "annotation_origin": acceptance["annotation_origin"], "authorship": copy.deepcopy(proposal["authorship"]),
        "bindings": {k: acceptance[k] for k in ("preparation_result", "preparation", "proposal", "proposal_seal",
                     "review_completion", "review_video", "review_guide")},
        "source_authorities": prepared["bindings"], "sources": prepared["sources"], "groups": prepared["groups"],
        "new_annotations": copy.deepcopy(proposal["new_annotations"]),
        "existing_controls": copy.deepcopy(proposal["existing_controls"]),
        "totals": {"new_references": 27, "reused_controls": 7,
                   "new_geometry": sum(r["annotation"]["geometry"] is not None for r in proposal["new_annotations"]),
                   "new_unknown": sum(r["annotation"]["visibility"] == "indeterminate" for r in proposal["new_annotations"])},
        "publication_implementation": code_bindings(root),
        "limits": {"independent_human_annotation": False, "independent_test_set": False,
            "source_first_not_blind": True, "selected_correlated_development_regression_set": True,
            "original_pending_draft_modified": False, "original_790_report_modified": False,
            "seven_controls_count_as_new": False, "qualitative_ai_object_findings_separately_human_adjudicated": False,
            "new_inference": False, "new_training": False}}


def publish_reference(root, acceptance_path, output):
    root = Path(root).resolve(); path = output_path(root, output)
    reference = reference_document(root, acceptance_path)
    d.write_once(path, reference)
    return reference


def score_reference_rows(reference, prepared, selection):
    """Use the existing scorer, preserving control outcomes and unknowns."""
    decisions = {(r["candidate_id"], r["source_frame_index"]): r for r in selection["frames"]}
    d.require(len(decisions) == len(selection["frames"]), "Duplicate saved source/frame decision")
    new_labels = {preparation.key(r): r["annotation"] for r in reference["new_annotations"]}
    old_labels = {preparation.key(r): r["existing_reference"] for r in reference["existing_controls"]}
    sources = {s["candidate_id"]: s for s in prepared["sources"]}
    new_rows = []; controls = []
    for frame in prepared["frames"]:
        if frame["role"] == "context_only":
            continue
        pair = preparation.key(frame); decision = decisions[pair]; source = sources[pair[0]]
        label = new_labels[pair] if frame["reference_origin"] == "new" else old_labels[pair]["row"]["annotation"]
        d.require(decision["source_video"] == source["source_video"]
                  and decision["source_frame"] == frame["source_frame"]
                  and decision["source_pts_ticks"] == frame["source_pts_ticks"]
                  and label["frame_index"] == pair[1], "Saved decision/reference source or native PTS differs")
        row = {"continuous_source_id": pair[0], "source_frame_index": pair[1], "source_frame": frame["source_frame"],
            "source_video": source["source_video"], "time_base": frame["time_base"], "time_origin": frame["time_origin"],
            "container_pts_ticks": frame["container_pts_ticks"], "group_id": frame["group_id"], "role": frame["role"],
            "reference_origin": frame["reference_origin"], "analysis_group": source["analysis_group"],
            "annotation": copy.deepcopy(label), "eligibility": pools.eligibility(label)}
        scoring_row = {**row, "old": {"pool": {"contributor_planes": [None] * decision["original_observation"]["temporal_contributions"]}}}
        before = selector.score_point(scoring_row, decision["baseline_center_xy_px"], decision["original_observation"]["candidates"])
        after = selector.score_point(scoring_row, decision["selected_center_xy_px"], [r["component"] for r in decision["candidate_pool"]["records"]])
        row.update(baseline=before, selected=after,
                   changed=decision["baseline_center_xy_px"] != decision["selected_center_xy_px"],
                   candidate_availability_scope=decision["candidate_pool_scope"],
                   exact_saved_decision=copy.deepcopy(decision))
        if frame["reference_origin"] == "new":
            new_rows.append(row)
        else:
            original = old_labels[pair]
            d.require(before == original["row"]["baseline"] and after == original["row"]["selected"],
                      "Reproduced accepted control outcomes/errors differ")
            row["existing_reference"] = copy.deepcopy(original)
            row["original_scores_reproduced_exactly"] = True
            controls.append(row)
    d.require(len(new_rows) == 27 and len(controls) == 7, "Evaluation target census differs")
    return new_rows, controls


def evaluate(root, reference_path, output):
    root = Path(root).resolve(); reference_path = (root / reference_path).resolve()
    reference = d.read_json(reference_path)
    expected = reference_document(root, reference["acceptance"]["path"])
    d.require(reference == expected, "Published accepted reference differs from accepted sealed proposal")
    accepted_binding = d.binding(root, reference_path)
    prepared = bound_json(root, reference["bindings"]["preparation"])
    selection_binding = prepared["bindings"]["selection"]
    selection = bound_json(root, selection_binding)
    new_rows, controls = score_reference_rows(reference, prepared, selection)
    summary = {"new_references_only": selector.aggregate(new_rows)}
    for field in ("role", "continuous_source_id", "analysis_group"):
        name = {"role": "by_role", "continuous_source_id": "by_source", "analysis_group": "by_analysis_group"}[field]
        summary[name] = {value: selector.aggregate([r for r in new_rows if r[field] == value])
                         for value in dict.fromkeys(r[field] for r in new_rows)}
    summary["unscored_new_frames"] = [{"continuous_source_id": r["continuous_source_id"], "source_frame_index": r["source_frame_index"],
        "role": r["role"], "visibility": r["annotation"]["visibility"], "emitted_point_present": r["exact_saved_decision"]["selected_center_xy_px"] is not None}
        for r in new_rows if r["selected"]["outcome"] == "unscored"]
    report = {"schema_version": SCHEMA, "status": "completed", "accepted_reference": accepted_binding,
        "selection": selection_binding, "original_790_report": prepared["bindings"]["report"],
        "implementation": code_bindings(root), "new_frames": new_rows, "reused_controls": controls, "summary": summary,
        "control_reproduction": {"rows": 7, "exact_original_scores_reproduced": True, "included_in_new_summary": False},
        "metric": {"raw_match_radius_px": 10, "boundary": "inclusive", "requires_in_image_point": True,
                   "uncertainty_adjusted_error": "diagnostic_only", "qualitative_object_identity_veto": False,
                   "candidate_availability": "Only the saved pool at each row's candidate_availability_scope; not an exhaustive search."},
        "interpretation": "Selected correlated development references. Unknowns remain unscored. Geometric matches do not establish object identity when a separate object judgment is unresolved. Qualitative AI head/other-object evidence is separate and is not converted to hidden-ball labels or geometric errors.",
        "resources": {"model_calls": 0, "candidate_array_reads": 0, "source_video_reads": 0,
                      "source_decodes": 0, "image_pixel_reads": 0, "original_artifacts_modified": False}}
    d.write_once(output_path(root, output), report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--publish", action="store_true"); mode.add_argument("--score", action="store_true")
    parser.add_argument("--acceptance"); parser.add_argument("--reference"); parser.add_argument("--output", required=True)
    args = parser.parse_args(); root = Path.cwd()
    if args.publish:
        result = publish_reference(root, args.acceptance, args.output)
        print(json.dumps({"status": result["status"], "totals": result["totals"]}, indent=2))
    else:
        result = evaluate(root, args.reference, args.output)
        print(json.dumps({"status": result["status"], "summary": result["summary"], "control_reproduction": result["control_reproduction"]}, indent=2))


if __name__ == "__main__":
    main()
