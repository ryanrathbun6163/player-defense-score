"""Publish human-accepted difficult-scene AI labels without changing proposals."""
from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from src.ball_tracking import nba_annotations as nba
from src.ball_tracking.nba_reviewed_reference import _read_bound, _same_binding
from src.ball_tracking.prepare_nba_assisted_review import (
    contained, digest, exceptions, read_json, require, text, validate_proposal, write_new,
)

SCHEMA_VERSION = "nba_reviewed_reference/v0.1"


def _inventory(rows: list, label: str) -> dict:
    require(isinstance(rows, list) and bool(rows), f"{label} needs window packages")
    result = {}
    for row in rows:
        require(isinstance(row, dict), f"{label} package must be an object")
        key = row.get("window_id")
        text(key, "window_id")
        require(key not in result, f"Duplicate {label} window_id")
        result[key] = row
    return result


def load_accepted_references(acceptance_path: Path, repo_root: Path,
                             verify_images: bool = False) -> list[dict]:
    """Verify exact accepted windows, source records and presented review geometry.

    Window IDs, not candidate IDs, identify these packages: several difficult
    windows can come from the same candidate. Parent recordings are stat-checked
    against the completed source audit, never read or decoded here.
    """
    root = Path(repo_root).resolve()
    path = (root / acceptance_path).resolve()
    require(path.is_relative_to(root), "Acceptance must be inside repository")
    raw = path.read_bytes()
    acceptance = read_json(raw)
    require(acceptance.get("schema_version") == "nba_hard_example_label_acceptance/v0.1"
            and acceptance.get("status") == "accepted", "Human label acceptance is not accepted")
    require(acceptance.get("annotation_origin") == "assistant_visual_proposal"
            and acceptance.get("review_method") == "human_visual_acceptance_of_assisted_proposals",
            "Acceptance must retain assisted origin and review method")
    for key in ("reviewer_id", "reviewed_at_utc", "user_statement", "scope"):
        text(acceptance.get(key), key)
    require(acceptance["reviewer_id"] == "Ryan", "Hard-example labels require Ryan's acceptance")
    stamp = datetime.fromisoformat(acceptance["reviewed_at_utc"].replace("Z", "+00:00"))
    require(stamp.tzinfo is not None and stamp.utcoffset().total_seconds() == 0,
            "Acceptance timestamp must be UTC")
    limits = acceptance.get("limits", {})
    for key in ("independent_human_annotation", "training_authorized", "new_inference_authorized",
                "independent_test_set", "full_possession_or_phase_acceptance"):
        require(limits.get(key) is False, f"Unsupported acceptance scope: {key}")
    require(limits.get("saved_output_scoring_authorized") is True,
            "Acceptance must retain approved saved-output scoring scope")
    acceptance_binding = {"path": path.relative_to(root).as_posix(), "sha256": digest(raw), "bytes": len(raw)}
    prepared_raw, prepared_binding = _read_bound(root, acceptance["preparation_record"])
    prepared = read_json(prepared_raw)
    require(prepared.get("schema_version") == "nba_hard_example_reference_preparation/v0.1"
            and prepared.get("status") == "prepared_pending_human_label_acceptance",
            "Invalid hard-example preparation record")
    approval_raw, approval_binding = _read_bound(root, acceptance["scope_approval"])
    approval = read_json(approval_raw)
    require(_same_binding(approval_binding, prepared["scope_approval"]),
            "Preparation/acceptance scope approval differs")
    proposal_raw, scope_proposal_binding = _read_bound(root, approval["proposal"])
    scope_proposal = read_json(proposal_raw)
    require(_same_binding(scope_proposal_binding, prepared["scope_proposal"]),
            "Preparation/approval scope proposal differs")
    packages = _inventory(acceptance.get("packages"), "acceptance")
    preparations = _inventory(prepared.get("packages"), "preparation")
    windows = _inventory(scope_proposal.get("windows"), "proposal")
    require(set(packages) == set(preparations) == set(windows),
            "Acceptance/preparation/approved window inventory differs")
    results, frame_keys = [], set()
    for window_id, package in packages.items():
        prep, window = preparations[window_id], windows[window_id]
        bound, documents = {}, {}
        aliases = {"proposal": "proposal", "original_annotations": "source_draft",
                   "review_manifest": "review_manifest", "review_video": "review_video",
                   "review_receipt": "preparation_receipt"}
        for key, prep_key in aliases.items():
            data, bound[key] = _read_bound(root, package[key], ".mp4" if key == "review_video" else ".json")
            require(all(bound[key].get(field) == prep[prep_key].get(field)
                        for field in ("path", "sha256", "bytes")),
                    f"Preparation/acceptance binding differs: {key}")
            if key != "review_video":
                documents[key] = read_json(data)
        original = documents["original_annotations"]
        nba.validate_annotations(original)
        asset_check = nba.verify_annotation_assets(original, root, verify_images=verify_images)
        require(asset_check.get("window_id") == window_id
                and _same_binding(original["approval"], approval_binding), "Original approved window differs")
        require(original["revision"] == 0 and original["review"]["status"] == "draft"
                and all(row["annotation_status"] == "unlabeled" for row in original["annotations"]),
                "Original blank draft was changed")
        proposal, manifest = documents["proposal"], documents["review_manifest"]
        validated = validate_proposal(proposal, original, contained(root, bound["original_annotations"]["path"]),
                                      bound["original_annotations"]["sha256"], root)
        for key in ("candidate_id", "game_id", "approved_role"):
            require(package[key] == prep[key] == original[key], f"Accepted window differs in {key}")
        frames, rows = original["frames"], proposal["annotations"]
        indices = [frame["source_frame_index"] for frame in frames]
        require(package["frame_count"] == len(frames)
                and package["source_frame_range_inclusive"] == prep["source_frame_range_inclusive"]
                == [indices[0], indices[-1]]
                and package["actual_final_frame_in_presented_review"] == prep["actual_final_frame_inspected"]
                == indices[-1], "Accepted frame inventory/final frame differs")
        priorities = [item["frame_index"] for item in proposal["review_priority"]]
        require(package["priority_frame_indices"] == prep["review_priority_frames"] == priorities,
                "Accepted priority frames differ")
        require(manifest.get("schema_version") == "nba_assisted_review_manifest/v0.1"
                and manifest.get("candidate_id") == original["candidate_id"]
                and manifest.get("origin") == proposal["origin"]
                and manifest.get("human_review") == proposal["human_review"]
                and manifest.get("source_annotation_binding") == proposal["source_annotation_binding"]
                and manifest.get("source_evidence") == validated["evidence"],
                "Review manifest provenance differs")
        review_frames = manifest["frames"]
        require(len(review_frames) == len(frames), "Review frame count differs")
        for i, (frame, row, review) in enumerate(zip(frames, rows, review_frames)):
            key = (original["candidate_id"], frame["source_frame_index"])
            require(key not in frame_keys, "Accepted windows overlap or duplicate source frames")
            frame_keys.add(key)
            require(review["review_index"] == i and review["source_frame_index"] == frame["source_frame_index"]
                    and review["source_pts_ticks"] == frame["source_pts_ticks"]
                    and review["time_base"] == original["time_base"] and review["source_png"] == frame["png"],
                    "Review native frame/PTS/PNG mapping differs")
            geometry = row["geometry"]
            require(review["render_geometry"]["point_source_pixels"] == (geometry["center_xy_px"] if geometry else None)
                    and review["render_geometry"]["uncertainty_radius_source_pixels"]
                    == (geometry["uncertainty_radius_px"] if geometry else None), "Review proposed geometry differs")
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
        receipt = documents["review_receipt"]
        require(receipt.get("status") == "prepared_pending_human_review"
                and receipt.get("candidate_id") == original["candidate_id"]
                and receipt.get("counts") == counts and receipt.get("final_source_frame_included") == indices[-1]
                and receipt.get("original_annotations_modified") is False and receipt.get("human_labels_created") == 0
                and receipt.get("proposal_origin") == "assistant_visual_proposal", "Review receipt differs")
        for key in ("proposal", "review_manifest", "review_video"):
            matches = [item for item in receipt["artifacts"] if _same_binding(item, bound[key])]
            require(len(matches) == 1 and matches[0].get("bytes") == bound[key]["bytes"],
                    "Review receipt artifact differs")
        input_raw, input_binding = _read_bound(root, window["input_manifest"])
        source_verification = read_json(input_raw)["preparation"]["identity"]["window"]["source_verification"]
        human_review = {key: acceptance[key] for key in
                        ("status", "reviewer_id", "reviewed_at_utc", "review_method", "user_statement", "scope")}
        human_review["independent_human_annotation"] = False
        result = {key: original[key] for key in
                  ("candidate_id", "game_id", "approved_role", "source_video", "time_base", "frames")}
        result.update(window_id=window_id, source_window=window, annotations=rows, origin=proposal["origin"],
                      human_review=human_review, limits=limits,
                      bindings={"acceptance": acceptance_binding, "preparation_record": prepared_binding,
                                "scope_approval": approval_binding, "scope_proposal": scope_proposal_binding,
                                "input_manifest": input_binding, "source_verification": source_verification, **bound})
        results.append(copy.deepcopy(result))
    totals = prepared["totals"]
    all_rows = [row for record in results for row in record["annotations"]]
    require(totals["frames"] == len(all_rows)
            and totals["eligible_proposed_centers"] == sum(row["localization_eligible"] for row in all_rows)
            and totals["null_geometry"] == sum(row["geometry"] is None for row in all_rows)
            and totals["visibility"] == dict(Counter(row["visibility"] or row["annotation_status"] for row in all_rows)),
            "Preparation totals differ from accepted rows")
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
                                 "original_drafts_modified": False, "proposals_modified": False,
                                 "model_calls": 0, "training_runs": 0, "scoring_runs": 0}}
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
    print(json.dumps({"status": document["status"], "windows": len(document["references"]),
                      **document["verification"]}))


if __name__ == "__main__":
    main()
