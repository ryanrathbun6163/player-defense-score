"""Read separately accepted NBA references without accepting an entire fit package.

Eligibility here is label-scoped: accepted training-game references may enter a
future frozen training package. It is neither permission to run a fit nor a
claim that the complete source/label/role package and executable recipe are
ready. This module reads metadata and hashes only; it never decodes or fits.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from .annotations import FrameAnnotation, SourceVideo
from .completion_references import read_json
from .completion_nba_references import (
    _check_binding, _check_proposal, _path, guard_episode,
    join_native_frames, validate_preparation,
)


_IDENTITY = ("batch_id", "episode_id", "game_id", "role")
_NOT_READY = ("package_ready_for_fitting", "executable_recipe_frozen",
              "fitting_authorized_by_this_artifact", "protected_evaluation_authorized",
              "model_output_acceptance", "ball_phase_accepted")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _human_review(review):
    _require(isinstance(review, dict), "Human acceptance record is required")
    _require(review.get("status") == "accepted"
             and review.get("review_method") == "human_visual_acceptance_of_assisted_proposals"
             and all(isinstance(review.get(k), str) and review[k].strip()
                     for k in ("reviewer_id", "user_statement", "response_context")),
             "Explicit human acceptance and response context are required")
    _require("exact_user_event_timestamp_utc" in review,
             "Unknown human event time must be explicitly null")
    _require(review.get("playback_telemetry_claimed") is False
             and review.get("independent_human_annotation_claimed") is False,
             "Acceptance must preserve honest assisted-review provenance")


def _validate_focused_test_scope(root, result, evidence, frame_count, centers):
    """Reuse unchanged code tests only beside the current batch's bound audit.

    The default retains the original strict proposal-specific contract. An
    explicit prior-implementation scope never substitutes prior batch media
    checks for current emitted-record evidence.
    """
    tests_binding = _check_binding(root, evidence["focused_tests"], "Focused tests")
    tests = read_json(_path(root, tests_binding["path"]))
    _require(type(tests.get("tests_run")) is int and tests["tests_run"] > 0
             and all(tests.get(k) == 0 for k in ("failures", "errors", "skipped", "exit_code"))
             and tests.get("implementation") == result.get("implementation")
             and tests.get("test_file") == result.get("tests"),
             "Successful focused-test receipt does not bind the unchanged producer/test source")
    for key in ("log", "implementation", "test_file", "actual_proposal"):
        _check_binding(root, tests.get(key), "Producer test " + key)
    scope = result.get("focused_tests_scope", "current_proposal")
    _require(scope in {"current_proposal", "prior_unchanged_implementation"},
             "Unknown focused-test scope")
    if scope == "current_proposal":
        _require(tests["actual_proposal"] == evidence["proposal"],
                 "Current-proposal focused tests do not bind this proposal")
        return
    _require(result.get("integration_audit") == evidence.get("integration_audit"),
             "Prior implementation tests require the current integration audit")
    audit_binding = _check_binding(root, evidence.get("integration_audit"), "Current integration audit")
    audit = read_json(_path(root, audit_binding["path"]))
    expected_counts = {"source_annotation_native_joins": frame_count,
                       "encoded_frames_checked": 2 * frame_count,
                       "encoded_markers_checked": 2 * centers}
    _require(audit.get("status") == "passed"
             and all(type(audit.get(k)) is int and audit[k] == value
                     for k, value in expected_counts.items())
             and all(audit.get(k) == evidence[k]
                     for k in ("proposal", "review_manifest", "source_frames", "source_timing")),
             "Current integration audit lacks this batch's exact records or complete counts")


def reviewed_nba_evidence(root, result_binding):
    """Validate actual producer records and completed review without opening pixels."""
    root = Path(root).resolve()
    result_binding = _check_binding(root, result_binding, "NBA preparation result")
    result = read_json(_path(root, result_binding["path"]))
    _require(result.get("schema_version") == "completion_nba_reference_batch_result/v0.1"
             and result.get("status") == "ready_for_human_reference_acceptance"
             and result.get("human_acceptance") is None
             and result.get("annotation_origin") == "assistant_visual_proposal"
             and result.get("training_eligible") is False
             and result.get("checkpoint_selection_eligible") is False
             and result.get("protected_evaluation_authorized") is False,
             "Original preparation result must remain pending and complete")
    evidence = {"preparation_result": result_binding}
    for key in ("config", "proposal", "review_manifest", "review_index", "exception_list",
                "focused_tests", "ai_visual_inspection", "integration_audit"):
        evidence[key] = _check_binding(root, result[key], key)
    config, proposal, manifest = [read_json(_path(root, evidence[k]["path"]))
                                  for k in ("config", "proposal", "review_manifest")]
    evidence["source_roles"] = _check_binding(root, config["source_roles"], "Fixed source roles")
    roles = read_json(_path(root, evidence["source_roles"]["path"]))
    episode = guard_episode(config, roles)
    _check_proposal(config, episode, proposal)
    _require(all(result[k] == proposal[k] == manifest[k] for k in _IDENTITY),
             "Prepared game/episode/role identity differs")
    _require(manifest.get("schema_version") == "completion_nba_reference_review/v0.1"
             and manifest.get("status") == proposal["status"]
             and manifest.get("human_acceptance") is None
             and manifest.get("training_eligible") is False
             and manifest.get("checkpoint_selection_eligible") is False
             and manifest.get("annotation_origin") == proposal["annotation_origin"]
             and manifest.get("annotator_id") == proposal["annotator_id"]
             and manifest["config"] == evidence["config"]
             and manifest["proposal"] == evidence["proposal"]
             and manifest["source_roles"] == evidence["source_roles"]
             and manifest["fixed_episode"] == episode,
             "Reviewed manifest differs from original pending proposal/config")
    source = episode["source"]
    evidence["source_video"] = _check_binding(root, source, "Fixed source video")
    evidence["fixed_frame_list"] = _check_binding(root, episode["frame_list"], "Fixed episode frames")
    for key in ("source_frames", "source_timing", "source_packet_timing"):
        evidence[key] = _check_binding(root, manifest[key], key)
    _require(manifest["source_video"] == evidence["source_video"]
             and manifest["source_metadata"] == source
             and manifest["fixed_frame_list"] == evidence["fixed_frame_list"],
             "Exact native source identity differs from fixed episode")
    frames = join_native_frames(
        episode, read_json(_path(root, evidence["fixed_frame_list"]["path"])),
        read_json(_path(root, evidence["source_frames"]["path"])),
        read_json(_path(root, evidence["source_timing"]["path"])),
        read_json(_path(root, evidence["source_packet_timing"]["path"])))
    preparation = validate_preparation(root, _path(root, config["output_root"]), episode, frames)
    for key in ("source_preparation", "source_pixel_audit"):
        _require(result[key] == manifest[key] == preparation[key],
                 "Source preparation evidence differs from completed result")
        evidence[key] = preparation[key]
    rows = proposal["annotations"]
    _require([row["frame_index"] for row in rows] == [f["source_frame_index"] for f in frames],
             "Accepted annotation census differs from native frames")
    _require(manifest["frames"] == [{**f, "annotation": row} for f, row in zip(frames, rows)],
             "Reviewed annotations/native frames differ from producer records")
    bounds = SourceVideo.from_mapping({"path": source["path"], "sha256": source["sha256"],
                                      "width_px": source["width"], "height_px": source["height"],
                                      "fps": config["review"]["native_playback_fps"],
                                      "frame_count": source["decoded_frames"]})
    for position, (row, frame) in enumerate(zip(rows, frames)):
        _require(FrameAnnotation.from_mapping(row, position, bounds).annotation_status == "labeled",
                 "Incomplete annotation cannot be accepted")
        _check_binding(root, frame["source_png"], "Native source PNG")
    counts = {"accepted_references": len(rows),
              "accepted_eligible_centers": sum(r["localization_eligible"] for r in rows),
              "accepted_null_centers": sum(r["geometry"] is None for r in rows),
              "accepted_visibility_counts": dict(Counter(r["visibility"] for r in rows))}
    _require(result["new_proposals"] == counts["accepted_references"]
             and result["proposed_centers"] == counts["accepted_eligible_centers"]
             and result["null_centers"] == counts["accepted_null_centers"]
             and result["visibility_counts"] == counts["accepted_visibility_counts"]
             and result["range_inclusive"] == [frames[0]["source_frame_index"], frames[-1]["source_frame_index"]],
             "Completed result census differs from reviewed labels")
    _require(len(manifest["videos"]) == 2, "Complete native and slow reviews are required")
    for video, fps in zip(manifest["videos"], (config["review"]["native_playback_fps"],
                                              config["review"]["slow_playback_fps"])):
        _check_binding(root, video, "Reviewed video")
        _check_binding(root, video["actual_final"], "Reviewed actual final")
        _check_binding(root, video["encoded_probe"], "Reviewed encoded metadata")
        _require(video["frame_count"] == len(rows) and video["fps"] == fps
                 and abs(video["duration_seconds"] - len(rows) / fps) < 1e-9,
                 "Reviewed video frame count or duration differs")
    _validate_focused_test_scope(root, result, evidence, len(rows), counts["accepted_eligible_centers"])
    visual = read_json(_path(root, evidence["ai_visual_inspection"]["path"]))
    _require(visual.get("status") == "ai_visual_inspection_complete_human_acceptance_pending"
             and visual["all_source_frames_inspected"] == [r["frame_index"] for r in rows]
             and visual["all_final_localized_encoded_crop_frames_inspected"] ==
                 [r["frame_index"] for r in rows if r["geometry"] is not None]
             and visual["all_null_center_source_context_crops_inspected"] ==
                 [r["frame_index"] for r in rows if r["geometry"] is None]
             and visual["slow_actual_final_inspected"] == manifest["videos"][1]["actual_final"],
             "Completed visual review does not cover the exact reviewed frame census")
    return {**{k: proposal[k] for k in _IDENTITY}, **counts,
            "range_inclusive": result["range_inclusive"], "source_metadata": source,
            "annotation_origin": proposal["annotation_origin"], "annotator_id": proposal["annotator_id"],
            "evidence": evidence,
            "review_videos": [{k: video[k] for k in
                               ("path", "sha256", "bytes", "frame_count", "fps", "duration_seconds",
                                "actual_final", "encoded_probe")} for video in manifest["videos"]],
            "annotations": rows, "frames": frames}


def _accepted_flags(doc):
    _require(doc.get("role") in {"training", "checkpoint_validation"}, "Unexpected accepted game role")
    _require(doc.get("training_eligible") is (doc["role"] == "training")
             and doc.get("checkpoint_selection_eligible") is (doc["role"] == "checkpoint_validation")
             and doc.get("eligibility_scope") == "accepted_reference_labels_only"
             and all(doc.get(k) is False for k in _NOT_READY),
             "Reference eligibility must not imply fit/package/recipe/protected readiness")


def build_accepted_reference(root, result_binding, human_review, acceptance_receipt_path):
    """Build, but do not write, an accepted copy of an explicitly reviewed batch."""
    _human_review(human_review)
    data = reviewed_nba_evidence(root, result_binding)
    return {"schema_version": "completion_nba_reference_accepted/v0.1",
            "status": "human_accepted_assisted_reference", **data,
            "human_review": human_review, "acceptance_receipt_path": acceptance_receipt_path,
            "training_eligible": data["role"] == "training",
            "checkpoint_selection_eligible": data["role"] == "checkpoint_validation",
            "eligibility_scope": "accepted_reference_labels_only",
            **{key: False for key in _NOT_READY}}


def validate_accepted_record(root, doc):
    """Validate accepted data against original producer records, without a receipt."""
    _require(doc.get("schema_version") == "completion_nba_reference_accepted/v0.1"
             and doc.get("status") == "human_accepted_assisted_reference",
             "Unexpected NBA accepted-reference schema/status")
    _human_review(doc.get("human_review"))
    _accepted_flags(doc)
    actual = reviewed_nba_evidence(root, doc["evidence"]["preparation_result"])
    _require(all(doc.get(k) == v for k, v in actual.items()),
             "Accepted annotations, source identity, role, timing or review evidence changed")
    return doc


def acceptance_receipt(doc, accepted_binding):
    """Construct the separate receipt from a validated accepted publication."""
    return {"schema_version": "completion_nba_reference_acceptance/v0.1", "status": "accepted",
            "accepted_reference": accepted_binding,
            **{k: v for k, v in doc.items()
               if k not in {"schema_version", "status", "acceptance_receipt_path", "annotations", "frames"}}}


def accepted_nba_reference(root, entry):
    """Read a bound publication and receipt. Eligibility is label-scoped only.

    Callers must separately freeze the complete accepted source/label/role
    package and executable recipe before fitting or checkpoint selection.
    A source key includes its SHA, so frame 0 of different clips cannot alias.
    """
    root = Path(root).resolve()
    publication = _check_binding(root, entry, "Accepted NBA publication")
    receipt_binding = _check_binding(root, entry.get("acceptance_receipt"), "NBA acceptance receipt")
    doc, receipt = [read_json(_path(root, b["path"])) for b in (publication, receipt_binding)]
    _require(doc.get("acceptance_receipt_path") == receipt_binding["path"]
             and receipt == acceptance_receipt(doc, publication),
             "Accepted NBA publication and receipt links/content disagree")
    validate_accepted_record(root, doc)
    return doc, [publication, receipt_binding]


def accepted_nba_inventory(root, entries):
    """Return unique accepted labels keyed by (game ID, native source SHA, frame)."""
    accepted, bindings = {}, []
    for entry in entries:
        doc, evidence = accepted_nba_reference(root, entry)
        bindings.extend(evidence)
        for row in doc["annotations"]:
            key = (doc["game_id"], doc["source_metadata"]["sha256"], row["frame_index"])
            _require(key not in accepted, "Duplicate accepted NBA native source frame")
            accepted[key] = {"episode_id": doc["episode_id"], "role": doc["role"], "annotation": row,
                             "training_eligible": doc["training_eligible"],
                             "checkpoint_selection_eligible": doc["checkpoint_selection_eligible"]}
    return accepted, bindings
