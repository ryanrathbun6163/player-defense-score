"""Publish accepted AI proposals separately from their unchanged pending inputs."""
from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from src.ball_tracking import nba_annotations as nba
from src.ball_tracking.prepare_nba_assisted_review import (
    contained, digest, exceptions, read_json, require, text, validate_proposal, write_new,
)

SCHEMA_VERSION = "nba_reviewed_reference/v0.1"


def _read_bound(root: Path, value: dict, suffix: str = ".json") -> tuple[bytes, dict]:
    require(isinstance(value, dict) and {"path", "sha256"} <= set(value), "Invalid file binding")
    path = contained(root, value["path"])
    require(path.suffix.lower() == suffix, "Unexpected bound file type")
    # Review derivatives and records only; never accidentally hash an original recording.
    require(path.stat().st_size <= 64 * 1024 * 1024, "Bound review file exceeds 64 MiB")
    raw = path.read_bytes()
    require(digest(raw) == value["sha256"], f"Hash mismatch: {value['path']}")
    require("bytes" not in value or value["bytes"] == len(raw), "Bound file size mismatch")
    return raw, {"path": value["path"], "sha256": digest(raw), "bytes": len(raw)}


def _same_binding(left: dict, right: dict) -> bool:
    return all(left.get(key) == right.get(key) for key in ("path", "sha256"))


def _one(rows: list, candidate: str) -> dict:
    matches = [row for row in rows if row.get("candidate_id") == candidate]
    require(len(matches) == 1, "Expected exactly one matching package")
    return matches[0]


def load_accepted_references(acceptance_path: Path, repo_root: Path,
                             verify_images: bool = False) -> list[dict]:
    """Validate acceptance and source authorities without decoding/hashing MP4 sources.

    Returned frames and annotation rows retain their original values. Human
    acceptance does not convert the assistant's proposal into human reannotation.
    """
    root = Path(repo_root).resolve()
    path = (root / acceptance_path).resolve()
    require(path.is_relative_to(root), "Acceptance must be inside repository")
    raw = path.read_bytes()
    acceptance = read_json(raw)
    require(acceptance.get("schema_version") == "nba_assisted_label_acceptance/v0.1"
            and acceptance.get("status") == "accepted", "Human acceptance is not accepted")
    require(acceptance.get("annotation_origin") == "assistant_visual_proposal"
            and acceptance.get("review_method") == "human_visual_acceptance_of_assisted_proposals",
            "Acceptance must retain assisted origin and review method")
    for key in ("reviewer_id", "reviewed_at_utc", "user_statement", "scope"):
        text(acceptance.get(key), key)
    stamp = datetime.fromisoformat(acceptance["reviewed_at_utc"].replace("Z", "+00:00"))
    require(stamp.tzinfo is not None and stamp.utcoffset().total_seconds() == 0,
            "Acceptance timestamp must be UTC")
    limits = acceptance.get("limits", {})
    for key in ("independent_human_annotation", "training_authorized", "new_diagnostic_recipe_approved",
                "independent_test_set", "full_possession_or_phase_acceptance"):
        require(limits.get(key) is False, f"Unsupported acceptance scope: {key}")
    acceptance_binding = {"path": path.relative_to(root).as_posix(), "sha256": digest(raw), "bytes": len(raw)}
    prepared_raw, prepared_binding = _read_bound(root, acceptance["preparation_record"])
    prepared = read_json(prepared_raw)
    require(prepared.get("schema_version") == "nba_assisted_annotation_pilot_preparation/v0.1"
            and prepared.get("status") == "prepared_pending_human_review", "Invalid preparation record")
    packages = acceptance.get("packages")
    require(isinstance(packages, list) and bool(packages), "Acceptance needs packages")
    ids = [item["candidate_id"] for item in packages]
    require(len(ids) == len(set(ids)) and set(ids) == {p["candidate_id"] for p in prepared["packages"]},
            "Acceptance/preparation package inventory differs")
    results = []
    for package in packages:
        candidate = package["candidate_id"]
        prep = _one(prepared["packages"], candidate)
        bound, documents = {}, {}
        for key in ("proposal", "original_annotations", "review_manifest", "review_video"):
            data, bound[key] = _read_bound(root, package[key], ".mp4" if key == "review_video" else ".json")
            if key != "review_video":
                documents[key] = read_json(data)
        original = documents["original_annotations"]
        nba.validate_annotations(original)
        nba.verify_annotation_assets(original, root, verify_images=verify_images)
        proposal, manifest = documents["proposal"], documents["review_manifest"]
        validated = validate_proposal(proposal, original, contained(root, bound["original_annotations"]["path"]),
                                      bound["original_annotations"]["sha256"], root)
        for key in ("candidate_id", "game_id", "approved_role"):
            require(package[key] == original[key], f"Acceptance differs from original {key}")
        for key, old_key in (("proposal", "proposal"), ("original_annotations", "original_draft"),
                             ("review_video", "review_video")):
            require(_same_binding(bound[key], prep[old_key]), "Preparation/acceptance binding differs")
        frames, rows = original["frames"], proposal["annotations"]
        indices = [frame["source_frame_index"] for frame in frames]
        priorities = [item["frame_index"] for item in proposal["review_priority"]]
        require(package["frame_count"] == len(frames)
                and package["source_frame_range_inclusive"] == [indices[0], indices[-1]]
                and package["actual_final_frame_in_presented_review"] == indices[-1], "Accepted frame inventory differs")
        require(package["priority_frame_indices"] == prep["priority_frame_indices"] == priorities,
                "Accepted priority frames differ")
        require(prep["origin"] == proposal["origin"] and prep["original_draft_revision"] == original["revision"]
                and prep["original_draft_all_rows_unlabeled"] is True
                and all(row["annotation_status"] == "unlabeled" for row in original["annotations"]),
                "Preparation original draft/origin differs")
        require(manifest.get("schema_version") == "nba_assisted_review_manifest/v0.1"
                and manifest.get("candidate_id") == candidate and manifest.get("origin") == proposal["origin"]
                and manifest.get("human_review") == proposal["human_review"]
                and manifest.get("source_annotation_binding") == proposal["source_annotation_binding"]
                and manifest.get("source_evidence") == validated["evidence"], "Review manifest provenance differs")
        review_frames = manifest["frames"]
        require(len(review_frames) == len(frames), "Review frame count differs")
        for i, (frame, row, review) in enumerate(zip(frames, rows, review_frames)):
            require(review["review_index"] == i and review["source_frame_index"] == frame["source_frame_index"]
                    and review["source_pts_ticks"] == frame["source_pts_ticks"]
                    and review["time_base"] == original["time_base"] and review["source_png"] == frame["png"],
                    "Review native frame/PTS/PNG mapping differs")
            geometry = row["geometry"]
            require(review["render_geometry"]["point_source_pixels"] == (geometry["center_xy_px"] if geometry else None)
                    and review["render_geometry"]["uncertainty_radius_source_pixels"] == (geometry["uncertainty_radius_px"] if geometry else None),
                    "Review proposed geometry differs")
            require(review["exceptions"] == exceptions(row, validated["priority_by_frame"].get(row["frame_index"])),
                    "Review exception flags differ")
        counts = {"frames": len(frames), "with_point": sum(row["geometry"] is not None for row in rows),
                  "eligible": sum(row["localization_eligible"] for row in rows),
                  "exception_frames": sum(bool(row["exceptions"]) for row in review_frames),
                  "visibility": dict(Counter(row["visibility"] or row["annotation_status"] for row in rows))}
        require(manifest["counts"] == prep["counts"] == counts, "Review counts differ")
        video = manifest["video"]
        require(contained(root, (Path(bound["review_manifest"]["path"]).parent / video["path"]).as_posix())
                == contained(root, bound["review_video"]["path"]), "Review video path differs")
        require(video["final_frame_hold_seconds"] == 1 and video["native_time_pacing"] is False
                and video["interpolated_source_frames"] == 0
                and video["expected_encoded_frames"] == len(frames) + video["review_source_frames_per_second"],
                "Review video inventory/final-frame convention differs")
        receipt_raw, bound["review_receipt"] = _read_bound(root, prep["review_receipt"])
        receipt = read_json(receipt_raw)
        require(receipt.get("status") == "prepared_pending_human_review" and receipt.get("candidate_id") == candidate
                and receipt.get("counts") == counts and receipt.get("final_source_frame_included") == indices[-1]
                and receipt.get("original_annotations_modified") is False and receipt.get("human_labels_created") == 0
                and receipt.get("proposal_origin") == "assistant_visual_proposal", "Review receipt differs")
        for key in ("proposal", "review_manifest", "review_video"):
            matches = [item for item in receipt["artifacts"] if _same_binding(item, bound[key])]
            require(len(matches) == 1 and matches[0].get("bytes") == bound[key]["bytes"], "Review receipt artifact differs")
        allocation_raw, allocation_binding = _read_bound(root, original["approval"])
        allocation = read_json(allocation_raw)
        pilot = _one(allocation["annotation_pilots"], candidate)
        human_review = {key: acceptance[key] for key in
                        ("status", "reviewer_id", "reviewed_at_utc", "review_method", "user_statement", "scope")}
        human_review["independent_human_annotation"] = False
        result = {key: original[key] for key in
                  ("candidate_id", "game_id", "approved_role", "source_video", "time_base", "frames")}
        result.update(annotations=rows, origin=proposal["origin"], human_review=human_review,
                      limits=limits, bindings={"acceptance": acceptance_binding, "preparation_record": prepared_binding,
                      **bound, "allocation_approval": allocation_binding, "source_verification": pilot["source_verification"]})
        results.append(copy.deepcopy(result))
    require(prepared["totals"]["source_frames"] == sum(len(item["frames"]) for item in results),
            "Preparation total frame count differs")
    return results


def publish_reference(acceptance_path: Path, output: Path, repo_root: Path) -> dict:
    root = Path(repo_root).resolve()
    output = (root / output).resolve()
    require(output.is_relative_to(root / "data/outputs"), "Reference output must be under data/outputs")
    require(not output.exists(), "Existing reference preserved; choose a new output")
    records = load_accepted_references(acceptance_path, root, verify_images=True)
    document = {"schema_version": SCHEMA_VERSION, "status": "human_accepted_assisted_reference",
                "acceptance": records[0]["bindings"]["acceptance"], "references": records,
                "verification": {"native_pngs_verified": sum(len(row["frames"]) for row in records),
                                 "original_video_bytes_read": 0, "original_video_decodes": 0,
                                 "original_drafts_modified": False, "proposals_modified": False}}
    output.parent.mkdir(parents=True, exist_ok=True)
    write_new(output, document)
    return document


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acceptance", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repository-root", default=Path.cwd(), type=Path)
    args = parser.parse_args()
    document = publish_reference(args.acceptance, args.output, args.repository_root)
    print(json.dumps({"status": document["status"], "candidates": len(document["references"]),
                      **document["verification"]}))


if __name__ == "__main__":
    main()
