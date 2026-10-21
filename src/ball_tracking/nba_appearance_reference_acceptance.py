"""Publish human acceptance of frozen AI appearance labels using metadata only."""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from . import nba_appearance_reference as preparation
from . import nba_wasb_diagnostic as d

ACCEPTANCE_SCHEMA = "nba_appearance_reference_acceptance/v0.1"
REFERENCE_SCHEMA = "nba_appearance_reference_accepted/v0.1"
SCHEMA = "nba_appearance_reference_publication/v0.1"
CLASSES = {"ball", "other_object", "unresolved"}


def _read(root, binding):
    return d.read_json(d.bound(root, binding))


def _utc(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    d.require(parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed),
              "Review and seal timestamps must be explicit UTC")
    return parsed


def _proposal(prepared, proposal):
    # The existing validator also verifies image pixels. Keep the same closed
    # label schema here while deliberately using the metadata-only loader.
    d.require(set(proposal) == {"schema_version", "preparation", "authorship", "human_review", "rows"}
              and proposal["schema_version"] == preparation.PROPOSAL_SCHEMA
              and proposal["human_review"] == "pending", "Original pending proposal changed")
    author = proposal["authorship"]
    d.require(set(author) == {"annotator_id", "method", "not_blind"}
              and isinstance(author["annotator_id"], str) and author["annotator_id"].strip()
              and author["method"] == "source_first_ai" and author["not_blind"] is True,
              "Source-first AI authorship must remain explicit")
    rows = proposal["rows"]
    d.require(isinstance(rows, list) and [r["candidate_key"] for r in rows]
              == [c["candidate_key"] for c in prepared["candidates"]], "Exact candidate label census required")
    for row in rows:
        d.require(set(row) == {"candidate_key", "classification", "subtype", "rationale"}
                  and row["classification"] in CLASSES, "Invalid label fields; geometry is not permitted")
        d.require(isinstance(row["rationale"], str) and row["rationale"].strip(), "Label rationale required")
        d.require((row["classification"] != "other_object" and row["subtype"] is None)
                  or (row["classification"] == "other_object" and isinstance(row["subtype"], str)
                      and row["subtype"].strip()), "Only confirmed other objects may have a subtype")
    return dict(Counter(row["classification"] for row in rows))


def _review(root, acceptance, result, prepared, proposal):
    media = _read(root, acceptance["review_completion"])
    d.require(media["status"] == "completed" and media["human_review"] == "pending"
              and media["identity"]["schema_version"] == "nba_appearance_reference_review/v0.1"
              and media["identity"]["kind"] == "human_semantic_review"
              and media["identity"]["preparation"] == acceptance["preparation"]
              and media["identity"]["proposal"] == acceptance["proposal"]
              and media["artifacts"] == result["media"]["artifacts"], "Completed review linkage differs")
    manifest = _read(root, media["artifacts"]["manifest"])
    verification = _read(root, media["artifacts"]["verification"])
    d.require(manifest["identity"] == media["identity"] and manifest["classes_only_on_target"] is True,
              "Review manifest identity differs")
    frames = manifest["frames"]
    d.require(len(frames) == len(prepared["frames"]) == prepared["totals"]["context_frames"],
              "Complete review context census required")
    groups = {g["group_id"]: g for g in prepared["groups"]}
    targets = {t["group_id"]: t for t in prepared["targets"]}
    labels = {r["candidate_key"]: r for r in proposal["rows"]}
    pts = 0
    expected_stills = []
    for index, (frame, source) in enumerate(zip(frames, prepared["frames"])):
        group = groups[source["group_id"]]; target = targets[source["group_id"]]
        is_target = source["role"] == "target"
        final = source["source_frame_index"] == group["context_range_inclusive"][1]
        d.require(frame["review_index"] == index and frame["group_id"] == source["group_id"]
                  and frame["block_id"] == group["block_id"] and frame["split_role"] == group["role"]
                  and all(frame[k] == source[k] for k in
                          ("continuous_source_id", "source_frame_index", "source_pts_ticks"))
                  and frame["source_png"] == source["raw_png"]
                  and frame["target_frame_index"] == target["source_frame_index"]
                  and frame["target"] is is_target and frame["context_final"] is final,
                  "Review source frame, role or target join differs")
        candidates = [c for c in prepared["candidates"] if c["group_id"] == source["group_id"]]
        d.require(len(frame["candidates"]) == len(candidates), "Review candidate census differs")
        for shown, candidate in zip(frame["candidates"], candidates):
            d.require(all(shown[k] == candidate[k] for k in
                          ("candidate_key", "candidate_offset", "center_xy_px"))
                      and shown["label"] == (labels[candidate["candidate_key"]] if is_target else None),
                      "Review candidate or label join differs")
        d.require(type(frame["duration_ticks"]) is int and frame["duration_ticks"] > 0
                  and frame["review_pts_ticks"] == pts, "Review timeline metadata differs")
        pts += frame["duration_ticks"]
        if is_target or final:
            expected_stills.append((index, group["group_id"], "target" if is_target else "context_final"))
    d.require([(s["review_index"], s["group_id"], s["kind"]) for s in media["stills"]] == expected_stills
              and verification["status"] == "passed" and verification["decoded_frames"] == len(frames)
              and verification["duration_ticks"] == pts
              and verification["all_keys_pixels_and_markers_verified"] is True
              and media["stills"][-1]["image"]["sha256"] == media["artifacts"]["actual_final"]["sha256"],
              "Completed verification or final-frame evidence differs")
    # Hash encoded review artifacts without decoding them. The original
    # completed verification remains the authority for their pixel content.
    artifacts = [media["artifacts"][k] for k in ("video", "guide", "actual_final")] + [s["image"] for s in media["stills"]]
    for item in artifacts:
        d.bound(root, item)
    return media, {"reviewed_artifact_files_hashed": len(artifacts),
                   "reviewed_artifact_bytes_hashed": sum(item["bytes"] for item in artifacts)}


def reference_document(root, acceptance_path):
    """Validate the frozen proposal/review joins without reading any pixels."""
    root = Path(root).resolve(); path = preparation._path(root, acceptance_path)
    accepted = d.read_json(path)
    d.require(accepted["schema_version"] == ACCEPTANCE_SCHEMA and accepted["status"] == "accepted"
              and accepted["reviewer_id"] == "Ryan"
              and isinstance(accepted["user_statement"], str) and accepted["user_statement"].strip()
              and accepted["annotation_origin"] == "assistant_visual_proposal"
              and accepted["review_method"] == "human_visual_acceptance_of_assisted_proposals",
              "Exact human acceptance of the AI appearance proposal required")
    reviewed = _utc(accepted["reviewed_at_utc"])
    d.require(set(accepted["accepted_counts"]) == CLASSES
              and all(type(n) is int and n >= 0 for n in accepted["accepted_counts"].values())
              and accepted["unresolved_used_as_negatives"] is False
              and all(accepted[k] is False for k in ("new_training_authorized", "new_inference_authorized",
                                                      "new_appearance_rule_trial_authorized")),
              "Acceptance scope or unresolved-label policy differs")
    result = _read(root, accepted["preparation_result"])
    d.require(result["schema_version"] == "nba_appearance_reference_result/v0.1"
              and result["status"] == "prepared_human_review_pending"
              and result["source_preparation"]["preparation"] == accepted["preparation"]
              and result["appearance_proposals"]["proposal"] == accepted["proposal"]
              and result["appearance_proposals"]["seal"] == accepted["proposal_seal"]
              and result["media"]["completion"] == accepted["review_completion"], "Preparation result bindings differ")
    proposal = _read(root, accepted["proposal"]); seal = _read(root, accepted["proposal_seal"])
    d.require(seal["schema_version"] == "nba_appearance_reference_proposal_seal/v0.1"
              and seal["human_review"] == "pending" and reviewed >= _utc(seal["created_at_utc"])
              and seal["proposal"] == accepted["proposal"]
              and seal["preparation"] == accepted["preparation"] == proposal["preparation"],
              "Accepted proposal differs from its seal or acceptance predates seal")
    prepared = preparation.load_ready_preparation(root, d.bound(root, accepted["preparation"]), verify_images=False)
    counts = _proposal(prepared, proposal)
    d.require(counts == accepted["accepted_counts"] == seal["counts"] == result["appearance_proposals"]["counts"],
              "Accepted class counts differ")
    roles = {}
    by_role = {}
    for candidate, label in zip(prepared["candidates"], proposal["rows"]):
        cid = candidate["continuous_source_id"]; role = candidate["role"]
        d.require(role in preparation.ROLES and roles.get(cid, role) == role, "Source role crosses fit/check boundary")
        roles[cid] = role
        by_role.setdefault(role, Counter())[label["classification"]] += 1
    by_role = {role: dict(counts) for role, counts in by_role.items()}
    d.require(roles == accepted["source_roles"] == result["census"]["source_roles"]
              and by_role == seal["by_role"] == result["appearance_proposals"]["by_role"]
              and proposal["authorship"] == result["appearance_proposals"]["authorship"],
              "Accepted source roles or AI provenance differs")
    media, byte_verification = _review(root, accepted, result, prepared, proposal)
    return {"schema_version": REFERENCE_SCHEMA, "status": "human_accepted_assisted_reference",
        "acceptance": d.binding(root, path),
        "human_review": {k: copy.deepcopy(accepted[k]) for k in
                         ("status", "reviewer_id", "reviewed_at_utc", "user_statement", "review_method")},
        "annotation_origin": accepted["annotation_origin"], "authorship": copy.deepcopy(proposal["authorship"]),
        "bindings": {k: accepted[k] for k in ("preparation_result", "preparation", "proposal", "proposal_seal", "review_completion")},
        "preparation_metadata": prepared["metadata"], "review_artifacts": media["artifacts"],
        "review_artifact_byte_verification": byte_verification,
        "proposal_seal_evidence": copy.deepcopy(seal),
        **{k: copy.deepcopy(prepared[k]) for k in ("sources", "groups", "frames", "targets", "candidates", "totals")},
        "rows": copy.deepcopy(proposal["rows"]), "counts": counts, "by_role": by_role, "source_roles": roles,
        "prior_evidence": copy.deepcopy(result["preserved"]),
        "limits": {"original_pending_proposal_modified": False, "original_pending_media_modified": False,
            "independent_human_annotation": False, "independent_test_set": False, "unresolved_used_as_negatives": False,
            "automatic_model_adoption": False, "new_training": False, "new_inference": False,
            "new_appearance_rule_trial": False, "geometric_scoring": False, "source_pixel_reads": 0}}


def publish(root, acceptance_path, output_dir):
    """Write a separate accepted artifact; preserve every attempt and exact resume."""
    root = Path(root).resolve(); output = preparation._output(root, output_dir)
    acceptance_path = preparation._path(root, acceptance_path)
    identity = {"schema_version": SCHEMA, "acceptance": d.binding(root, acceptance_path),
        "implementation": [d.binding(root, root / "src/ball_tracking" / name) for name in
                           ("nba_appearance_reference_acceptance.py", "nba_appearance_reference.py", "nba_wasb_diagnostic.py")]}
    completion_path = output / "completion.json"
    if completion_path.exists():
        completion = d.read_json(completion_path)
        d.require(completion["status"] == "completed" and completion["identity"] == identity,
                  "Existing publication identity differs")
        reference = _read(root, completion["accepted_reference"])
        d.require(reference == reference_document(root, acceptance_path), "Published accepted reference differs")
        return completion
    attempt = output / "attempts" / uuid.uuid4().hex
    d.write_once(attempt / "started.json", {"identity": identity, "created_at_utc": d.stamp()})
    try:
        reference = reference_document(root, acceptance_path)
        d.write_once(output / "accepted_reference.json", reference)
        completion = {"status": "completed", "identity": identity,
            "accepted_reference": d.binding(root, output / "accepted_reference.json"),
            "counts": reference["counts"], "by_role": reference["by_role"],
            "resources": {"source_pixel_reads": 0, "source_pixel_decodes": 0, "model_calls": 0,
                          "candidate_array_reads": 0, "geometric_scores_computed": 0,
                          **reference["review_artifact_byte_verification"]},
            "attempt": attempt.relative_to(root).as_posix(), "completed_at_utc": d.stamp()}
        d.write_once(attempt / "completed.json", completion)
        d.write_once(completion_path, completion)
        return completion
    except Exception as error:
        d.write_once(attempt / "failed.json", {"status": "failed_preserved", "identity": identity,
            "error_type": type(error).__name__, "error": str(error), "created_at_utc": d.stamp()})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acceptance", required=True); parser.add_argument("--output", required=True)
    args = parser.parse_args(); root = Path(__file__).resolve().parents[2]
    result = publish(root, args.acceptance, args.output)
    print(json.dumps({"status": result["status"], "accepted_reference": result["accepted_reference"], "counts": result["counts"]}))


if __name__ == "__main__":
    main()
