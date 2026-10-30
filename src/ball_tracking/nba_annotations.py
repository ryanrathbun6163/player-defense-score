"""Draft NBA annotations with native PTS, immutable provenance and safe saves.

This contract is separate from the frozen NFHS annotation-set schema. Only the
existing per-frame ball semantics are reused; no nominal fps is invented.
Version 0.1 deliberately cannot record human review acceptance.
"""

from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import re
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .annotations import AnnotationValidationError, FrameAnnotation


SCHEMA_VERSION = "nba_ball_annotations/v0.1"
TIME_BASE = "1/90000"
APPROVED_ROLES = {
    "future_training_candidate_pool",
    "target_case_development",
    "additional_development_no_current_label_selection",
}
COORDINATE_SYSTEM = {
    "pixel_origin": "top_left",
    "x_axis_direction": "right",
    "y_axis_direction": "down",
    "center_definition": "complete_ball_center",
}
TOP_FIELDS = {
    "schema_version", "annotation_set_id", "game_id", "candidate_id",
    "approved_role", "approval", "source_video", "time_base",
    "coordinate_system", "frames", "annotations", "revision",
    "created_at_utc", "updated_at_utc", "review",
}
SOURCE_FIELDS = {"path", "sha256", "width_px", "height_px", "frame_count"}
FRAME_FIELDS = {"source_frame_index", "source_pts_ticks", "png"}
PNG_FIELDS = {"path", "sha256", "rgb_sha256"}
MAX_PNG_BYTES = 64 * 1024 * 1024


class AnnotationConflictError(ValueError):
    """Another writer, revision or annotator conflicts with this save."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AnnotationValidationError(message)


def _fields(value: Any, fields: set[str], label: str) -> None:
    _require(isinstance(value, Mapping), f"{label} must be an object")
    _require(set(value) == fields, f"{label} fields must be exactly {sorted(fields)}")


def _integer(value: Any, label: str, minimum: int = 0) -> None:
    _require(type(value) is int and value >= minimum, f"{label} must be an integer >= {minimum}")


def _text(value: Any, label: str) -> None:
    _require(isinstance(value, str) and bool(value.strip()), f"{label} must be nonempty text")


def _identifier(value: Any, label: str) -> None:
    _require(isinstance(value, str) and re.fullmatch(r"[a-z0-9][a-z0-9_-]*", value) is not None,
             f"{label} must be a lowercase identifier")


def _sha(value: Any, label: str) -> None:
    _require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
             f"{label} must be a lowercase SHA-256")


def _relative(value: Any, label: str) -> None:
    _text(value, label)
    _require("\\" not in value and ":" not in value and "\x00" not in value,
             f"{label} must be a portable relative path")
    path = PurePosixPath(value)
    _require(not path.is_absolute() and value == path.as_posix()
             and all(part not in {".", ".."} for part in path.parts),
             f"{label} must be a normalized contained relative path")


def _bound_path(root: Path, value: str) -> Path:
    _relative(value, "bound path")
    root = root.resolve()
    result = (root / value).resolve()
    _require(result.is_relative_to(root), "Bound path escapes repository")
    return result


def _utc(value: Any, label: str) -> datetime:
    _text(value, label)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AnnotationValidationError(f"{label} must be an ISO UTC timestamp") from exc
    _require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0,
             f"{label} must include UTC timezone")
    return parsed


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        _require(key not in result, f"Duplicate JSON object key: {key}")
        result[key] = value
    return result


def _parse(raw: bytes | str) -> Any:
    try:
        return json.loads(raw, object_pairs_hook=_unique_pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(
                              AnnotationValidationError(f"Nonfinite JSON value: {value}")))
    except (ValueError, UnicodeError) as exc:
        if isinstance(exc, AnnotationValidationError):
            raise
        raise AnnotationValidationError(f"Invalid JSON: {exc}") from exc


@dataclass(frozen=True)
class _PixelBounds:
    """Only dimensions used by FrameAnnotation; no fabricated fps context."""

    width_px: int
    height_px: int


def validate_annotations(data: Any) -> dict[str, Any]:
    """Validate and return an independent, normalized plain JSON document."""
    _fields(data, TOP_FIELDS, "NBA annotations")
    doc = copy.deepcopy(dict(data))
    _require(doc["schema_version"] == SCHEMA_VERSION, "Unsupported NBA schema_version")
    for field in ("annotation_set_id", "candidate_id"):
        _identifier(doc[field], field)
    _require(isinstance(doc["game_id"], str) and re.fullmatch(r"\d{10}", doc["game_id"]) is not None,
             "game_id must be the 10-digit NBA game ID")
    _require(isinstance(doc["approved_role"], str) and doc["approved_role"] in APPROVED_ROLES, "Unknown approved_role")
    _fields(doc["approval"], {"path", "sha256"}, "approval")
    _relative(doc["approval"]["path"], "approval.path")
    _sha(doc["approval"]["sha256"], "approval.sha256")
    source = doc["source_video"]
    _fields(source, SOURCE_FIELDS, "source_video")
    _relative(source["path"], "source_video.path")
    _sha(source["sha256"], "source_video.sha256")
    for field in ("width_px", "height_px", "frame_count"):
        _integer(source[field], f"source_video.{field}", 1)
    _require(doc["time_base"] == TIME_BASE, "time_base must be 1/90000")
    _require(doc["coordinate_system"] == COORDINATE_SYSTEM, "Unsupported coordinate_system")
    _integer(doc["revision"], "revision")
    created = _utc(doc["created_at_utc"], "created_at_utc")
    updated = _utc(doc["updated_at_utc"], "updated_at_utc")
    _require(updated >= created, "updated_at_utc precedes creation")
    review = doc["review"]
    _fields(review, {"status", "annotator_id", "reviewer_id", "reviewed_at_utc"}, "review")
    _require(review["status"] == "draft" and review["reviewer_id"] is None
             and review["reviewed_at_utc"] is None,
             "v0.1 is draft-only; actual human signoff requires a separate review record")
    if review["annotator_id"] is not None:
        _text(review["annotator_id"], "review.annotator_id")
    frames = doc["frames"]
    _require(isinstance(frames, list) and bool(frames), "frames must be a nonempty array")
    indices, ticks, paths = [], [], []
    for frame in frames:
        _fields(frame, FRAME_FIELDS, "frame")
        _integer(frame["source_frame_index"], "source_frame_index")
        _require(frame["source_frame_index"] < source["frame_count"], "Source frame exceeds source_video.frame_count")
        _integer(frame["source_pts_ticks"], "source_pts_ticks")
        png = frame["png"]
        _fields(png, PNG_FIELDS, "frame.png")
        _relative(png["path"], "png.path")
        _require(PurePosixPath(png["path"]).suffix.lower() == ".png", "Frame authority must be PNG")
        _sha(png["sha256"], "png.sha256")
        _sha(png["rgb_sha256"], "png.rgb_sha256")
        indices.append(frame["source_frame_index"])
        ticks.append(frame["source_pts_ticks"])
        paths.append(png["path"])
    _require(indices == list(range(indices[0], indices[0] + len(indices))), "Source frame indices must be ordered and contiguous")
    _require(all(a < b for a, b in zip(ticks, ticks[1:])), "Source PTS must be strictly increasing")
    _require(len(set(paths)) == len(paths), "Each frame needs a distinct PNG path")
    annotations = doc["annotations"]
    _require(isinstance(annotations, list) and len(annotations) == len(frames), "One annotation row is required per frame")
    bounds = _PixelBounds(source["width_px"], source["height_px"])
    normalized = [FrameAnnotation.from_mapping(row, i, bounds).to_dict()
                  for i, row in enumerate(annotations)]
    _require([row["frame_index"] for row in normalized] == indices,
             "Annotation frame_index must equal its original source frame index")
    if review["annotator_id"] is None:
        _require(all(row["annotation_status"] == "unlabeled" and row["notes"] is None
                     for row in normalized), "Nonempty annotations require a real annotator_id")
    doc["annotations"] = normalized
    return doc


def document_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_annotation_snapshot(path: Path, *, repo_root: Path | None = None,
                             verify_images: bool = False) -> tuple[dict[str, Any], str]:
    """Return document and revision hash from the same bytes."""
    raw = Path(path).read_bytes()
    doc = validate_annotations(_parse(raw))
    if verify_images:
        _require(repo_root is not None, "repo_root is required to verify assets")
        verify_annotation_assets(doc, repo_root)
    return doc, hashlib.sha256(raw).hexdigest()


def load_annotations(path: Path, *, repo_root: Path | None = None,
                     verify_images: bool = False) -> dict[str, Any]:
    return load_annotation_snapshot(path, repo_root=repo_root, verify_images=verify_images)[0]


def _read_binding(binding: Mapping[str, Any], repo_root: Path) -> bytes:
    _require(isinstance(binding, Mapping), "File binding must be an object")
    _relative(binding.get("path"), "binding.path")
    _sha(binding.get("sha256"), "binding.sha256")
    raw = _bound_path(repo_root, binding["path"]).read_bytes()
    _require(hashlib.sha256(raw).hexdigest() == binding["sha256"], f"Hash mismatch: {binding['path']}")
    if "bytes" in binding:
        _integer(binding["bytes"], "binding.bytes")
        _require(len(raw) == binding["bytes"], f"Size mismatch: {binding['path']}")
    return raw


def read_verified_png(frame: Mapping[str, Any], source_video: Mapping[str, Any],
                      repo_root: Path) -> bytes:
    """Check file and RGB hashes on exactly the bytes returned to the editor."""
    from PIL import Image

    png = frame["png"]
    path = _bound_path(repo_root, png["path"])
    with path.open("rb") as handle:
        raw = handle.read(MAX_PNG_BYTES + 1)
    _require(len(raw) <= MAX_PNG_BYTES, "PNG exceeds bounded 64 MiB read")
    _require(hashlib.sha256(raw).hexdigest() == png["sha256"], f"PNG hash mismatch: {png['path']}")
    try:
        with Image.open(io.BytesIO(raw)) as image:
            _require(image.format == "PNG" and image.mode == "RGB", "Frame authority must be RGB PNG")
            _require(image.size == (source_video["width_px"], source_video["height_px"]), "PNG dimensions differ from source")
            rgb_sha = hashlib.sha256(image.tobytes()).hexdigest()
    except (OSError, ValueError) as exc:
        if isinstance(exc, AnnotationValidationError):
            raise
        raise AnnotationValidationError(f"Invalid PNG: {png['path']}") from exc
    _require(rgb_sha == png["rgb_sha256"], f"PNG RGB hash mismatch: {png['path']}")
    return raw


def verify_annotation_assets(data: Any, repo_root: Path, *,
                             verify_images: bool = True) -> dict[str, Any]:
    """Bind approval, producer frame map and PNGs; never read full video bytes."""
    doc = validate_annotations(data)
    root = Path(repo_root)
    approval = _parse(_read_binding(doc["approval"], root))
    _require(isinstance(approval, dict), "Approval must be an object")
    if approval.get("schema_version") == "nba_hard_example_reference_approval/v0.1":
        return _verify_hard_example_assets(doc, approval, root, verify_images=verify_images)
    _require(approval.get("schema_version") == "nba_development_selection_approval/v0.1"
             and approval.get("status") == "approved", "Allocation/pilot approval is not approved")
    _text(approval.get("approved_by"), "approval.approved_by")
    _text(approval.get("approval_statement"), "approval.approval_statement")
    proposal = _parse(_read_binding(approval["proposal"], root))
    _require(isinstance(proposal, dict), "Proposal must be an object")
    _require(proposal.get("schema_version") == "nba_development_selection_proposal/v0.1", "Approval must bind the selection proposal")
    pilots = [p for p in approval.get("annotation_pilots", [])
              if p.get("annotation_set_id") == doc["annotation_set_id"]]
    _require(len(pilots) == 1, "Approval must identify exactly one annotation pilot")
    pilot = pilots[0]
    for field in ("candidate_id", "game_id", "approved_role", "source_video", "time_base"):
        _require(pilot.get(field) == doc[field], f"Approved pilot differs in {field}")
    roles = [role for role in approval.get("game_roles", []) if role.get("game_id") == doc["game_id"]]
    _require(len(roles) == 1 and roles[0].get("approved_role") == doc["approved_role"], "Approved game role mismatch")
    first, last = doc["frames"][0], doc["frames"][-1]
    _require(pilot.get("source_frame_range_inclusive") == [first["source_frame_index"], last["source_frame_index"]], "Approved pilot source frame range mismatch")
    _require(pilot.get("source_pts_ticks_inclusive") == [first["source_pts_ticks"], last["source_pts_ticks"]], "Approved pilot PTS endpoints mismatch")
    proposed_pilots = [row for row in proposal.get("proposed_annotation_pilot", [])
                       if row.get("candidate_id") == doc["candidate_id"]]
    _require(len(proposed_pilots) == 1, "Proposal must identify exactly one candidate pilot")
    proposed_pilot = proposed_pilots[0]
    for field in ("source_frame_range_inclusive", "source_pts_ticks_inclusive", "time_base"):
        _require(proposed_pilot.get(field) == pilot.get(field), f"Approval differs from proposed pilot {field}")
    _require(proposed_pilot.get("frame_count") == len(doc["frames"]), "Proposed pilot frame count mismatch")
    candidates = [row for row in proposal.get("candidates", []) if row.get("candidate_id") == doc["candidate_id"]]
    _require(len(candidates) == 1, "Proposal must identify exactly one source candidate")
    candidate = candidates[0]
    _require(candidate.get("game_id") == doc["game_id"]
             and candidate.get("parent_source_sha256") == doc["source_video"]["sha256"],
             "Proposed candidate game/source identity mismatch")
    _require(candidate.get("frame_map") == pilot.get("frame_map"), "Approval must use the proposal's bound frame map")
    proposed_roles = [row for row in proposal.get("game_roles", []) if row.get("game_id") == doc["game_id"]]
    _require(len(proposed_roles) == 1 and proposed_roles[0].get("proposed_role") == doc["approved_role"],
             "Approval differs from proposed game role")
    rows = [_parse(line) for line in _read_binding(pilot["frame_map"], root).splitlines() if line.strip()]
    _require(bool(rows), "Approved frame map is empty")
    for i, row in enumerate(rows):
        _fields(row, {"clip_frame_index", "source_frame_index", "source_pts_ticks", "clip_pts_ticks", "time_base"}, "producer frame map row")
        for field in ("clip_frame_index", "source_frame_index", "source_pts_ticks", "clip_pts_ticks"):
            _integer(row[field], f"frame map {field}")
        _require(row["time_base"] == TIME_BASE and row["clip_frame_index"] == rows[0]["clip_frame_index"] + i, "Producer frame map order/time base mismatch")
        _require(row["source_frame_index"] == rows[0]["source_frame_index"] + i, "Producer source indices are not contiguous")
        origin_ticks = rows[0]["source_pts_ticks"] - rows[0]["clip_pts_ticks"]
        _require(row["clip_pts_ticks"] == row["source_pts_ticks"] - origin_ticks, "Producer relative PTS mismatch")
        if i:
            _require(row["source_pts_ticks"] > rows[i - 1]["source_pts_ticks"], "Producer PTS are not increasing")
    selected = [row for row in rows if first["source_frame_index"] <= row["source_frame_index"] <= last["source_frame_index"]]
    expected = [(f["source_frame_index"], f["source_pts_ticks"]) for f in doc["frames"]]
    _require([(r["source_frame_index"], r["source_pts_ticks"]) for r in selected] == expected,
             "Annotation source mapping differs from approved producer frame map")
    source_path = _bound_path(root, doc["source_video"]["path"])
    _require(source_path.is_file(), "Parent source video is missing")
    verification = pilot.get("source_verification")
    _fields(verification, {"audit", "hash_field", "stat_field", "source_stat"}, "source_verification")
    audit = _parse(_read_binding(verification["audit"], root))
    _require(isinstance(audit, dict), "Source audit must be an object")
    _require(audit.get(verification["hash_field"]) == doc["source_video"]["sha256"], "Source audit digest mismatch")
    _require(audit.get(verification["stat_field"]) == verification["source_stat"], "Source audit stat mismatch")
    actual_stat = source_path.stat()
    _require({"bytes": actual_stat.st_size, "mtime_ns": actual_stat.st_mtime_ns} == verification["source_stat"],
             "Parent source stat changed since completed hash audit")
    if verify_images:
        for frame in doc["frames"]:
            read_verified_png(frame, doc["source_video"], root)
    return {"status": "verified", "frames_verified": len(doc["frames"]) if verify_images else 0,
            "frame_map_rows_verified": len(doc["frames"]), "png_verification_skipped": not verify_images,
            "approval_sha256": doc["approval"]["sha256"], "full_source_bytes_read": 0,
            "human_label_review": "pending"}


def _sized_json_binding(binding: Any, root: Path, label: str) -> dict[str, Any]:
    """The new contract requires both exact bytes and digest for its authorities."""
    _fields(binding, {"path", "bytes", "sha256"}, label)
    value = _parse(_read_binding(binding, root))
    _require(isinstance(value, dict), f"{label} must bind an object")
    return value


def _verify_hard_example_assets(doc: dict[str, Any], approval: dict[str, Any],
                                root: Path, *, verify_images: bool) -> dict[str, Any]:
    """Verify only the approved difficult-scene draft, without accepting labels.

    The action-input producer already froze original PNG/RGB and native PTS
    records. This consumer compares those actual records, not nominal fps or
    an independently reconstructed image inventory.
    """
    _fields(approval, {
        "schema_version", "status", "reviewer_id", "user_statement", "recorded_at_utc",
        "source_commit", "proposal", "approved_scope", "windows", "totals",
        "human_label_acceptance_required_before_publication_or_scoring",
        "new_model_inference_or_training_authorized", "preserved_boundaries",
    }, "hard-example approval")
    _require(approval["status"] == "approved" and approval["reviewer_id"] == "Ryan",
             "Hard-example scope requires Ryan's approval")
    _text(approval["user_statement"], "approval.user_statement")
    _utc(approval["recorded_at_utc"], "approval.recorded_at_utc")
    _require(isinstance(approval["source_commit"], str)
             and re.fullmatch(r"[0-9a-f]{40}", approval["source_commit"]) is not None,
             "Approval source_commit must be a full Git commit")
    _require(approval["human_label_acceptance_required_before_publication_or_scoring"] is True
             and approval["new_model_inference_or_training_authorized"] is False,
             "Hard-example approval cannot authorize scoring acceptance or new inference/training")
    proposal = _sized_json_binding(approval["proposal"], root, "hard-example proposal binding")
    _require(proposal.get("schema_version") == "nba_hard_example_reference_proposal/v0.1"
             and proposal.get("proposal_id") == "nba_hard_example_reference_v0_1"
             and proposal.get("status") == "design_only_awaiting_scope_approval"
             and proposal.get("runnable") is False,
             "Approval must bind the immutable hard-example proposal")
    _require(approval["approved_scope"] == proposal.get("approval_scope_requested")
             and isinstance(approval["approved_scope"], str) and bool(approval["approved_scope"].strip()),
             "Approval scope differs from bound proposal")
    _require(approval["totals"] == proposal.get("totals"), "Approval totals differ from bound proposal")
    totals = approval["totals"]
    _require(isinstance(totals, dict) and all(totals.get(key) == 0 and type(totals.get(key)) is int
             for key in ("new_model_calls", "training_runs", "raw_game_video_decodes")),
             "Hard-example scope must reuse existing inputs and predictions")
    boundaries = proposal.get("boundaries")
    _require(isinstance(boundaries, dict) and approval["preserved_boundaries"] == boundaries,
             "Approval boundaries differ from bound proposal")
    _require(all(boundaries.get(key) is True for key in (
        "protected_holdouts_unchanged", "original_nfhs_finish_line_unchanged",
        "no_new_training_threshold_search_motion_selector_interpolation_or_model_inference")),
        "Hard-example scope must preserve scientific boundaries")
    label_contract = proposal.get("label_contract")
    _require(isinstance(label_contract, dict) and label_contract.get(
        "human_acceptance_required_before_reference_publication_or_scoring") is True,
        "Proposal must retain explicit human label acceptance")
    windows = proposal.get("windows")
    _require(isinstance(windows, list) and bool(windows) and all(isinstance(w, dict) for w in windows),
             "Proposal windows must be objects")
    window_ids = [w.get("window_id") for w in windows]
    for window_id in window_ids:
        _identifier(window_id, "proposed window_id")
    for proposed_window in windows:
        _integer(proposed_window.get("frames"), "proposed window frames", 1)
    _require(len(set(window_ids)) == len(window_ids), "Duplicate proposed window_id")
    approval_fields = ("window_id", "candidate_id", "game_id", "source_frame_range_inclusive", "frames")
    _require(approval["windows"] == [{key: w.get(key) for key in approval_fields} for w in windows],
             "Approved windows differ from bound proposal")
    _require(sum(w.get("frames", 0) for w in windows) == totals.get("new_proposed_label_frames"),
             "Proposed window counts differ from approved total")
    selected = [w for w in windows if doc["annotation_set_id"] == w["window_id"] + "_hard_example_v0_1"]
    _require(len(selected) == 1, "Annotation set must identify exactly one approved hard-example window")
    window = selected[0]
    for field in ("candidate_id", "game_id", "time_base"):
        _require(window.get(field) == doc[field], f"Proposed window differs in {field}")
    _require(window.get("approved_game_role") == doc["approved_role"], "Proposed window role differs")
    _require(doc["approved_role"] in {"future_training_candidate_pool", "target_case_development"},
             "Hard-example role is outside approved development scope")
    manifest = _sized_json_binding(window.get("input_manifest"), root, "action-input manifest binding")
    _require(manifest.get("schema_version") == "nba_action_inputs/v0.1", "Wrong action-input producer schema")
    for field in ("candidate_id", "game_id", "approved_role", "source_video", "time_base"):
        _require(manifest.get(field) == doc[field], f"Action-input manifest differs in {field}")
    producer_frames = manifest.get("frames")
    _require(isinstance(producer_frames, list) and bool(producer_frames), "Action-input frame inventory is empty")
    for frame in producer_frames:
        _fields(frame, FRAME_FIELDS, "action-input frame")
        _integer(frame["source_frame_index"], "action-input source_frame_index")
        _integer(frame["source_pts_ticks"], "action-input source_pts_ticks")
        _fields(frame["png"], PNG_FIELDS, "action-input PNG")
        _relative(frame["png"]["path"], "action-input PNG path")
        for key in ("sha256", "rgb_sha256"):
            _sha(frame["png"][key], f"action-input PNG {key}")
    indices = [f["source_frame_index"] for f in producer_frames]
    ticks = [f["source_pts_ticks"] for f in producer_frames]
    _require(indices == list(range(indices[0], indices[-1] + 1)), "Action-input source frames are not contiguous")
    _require(indices[-1] < doc["source_video"]["frame_count"], "Action-input frame exceeds original source")
    _require(len({f["png"]["path"] for f in producer_frames}) == len(producer_frames),
             "Action-input PNG paths must be distinct")
    _require(all(a < b for a, b in zip(ticks, ticks[1:])), "Action-input native PTS are not increasing")
    _require(manifest.get("source_frame_range_inclusive") == [indices[0], indices[-1]]
             and manifest.get("source_pts_ticks_inclusive") == [ticks[0], ticks[-1]],
             "Action-input manifest endpoints differ from its frame records")
    end_pts = manifest.get("source_end_exclusive_pts_ticks")
    _integer(end_pts, "action-input end-exclusive PTS")
    _require(end_pts > ticks[-1], "Action-input end-exclusive PTS must follow final frame")
    first, last = doc["frames"][0], doc["frames"][-1]
    _require(window.get("source_frame_range_inclusive") == [first["source_frame_index"], last["source_frame_index"]]
             and window.get("frames") == len(doc["frames"]), "Proposed frame range/count differs from annotation")
    _require(window.get("source_pts_ticks_inclusive") == [first["source_pts_ticks"], last["source_pts_ticks"]],
             "Proposed native PTS endpoints differ from annotation")
    actual = [f for f in producer_frames if first["source_frame_index"] <= f["source_frame_index"] <= last["source_frame_index"]]
    _require(actual == doc["frames"], "Annotation records differ from bound action-input frame/PTS/PNG/RGB records")
    next_frame = last["source_frame_index"] + 1
    lookup = {f["source_frame_index"]: f for f in producer_frames}
    boundary = lookup[next_frame]["source_pts_ticks"] if next_frame in lookup else end_pts
    _require(window.get("source_end_exclusive_pts_ticks") == boundary,
             "Proposed end-exclusive PTS differs from action-input boundary")
    _require(window.get("native_duration_seconds") == (boundary - first["source_pts_ticks"]) / 90000,
             "Proposed native duration differs from producer PTS")
    preparation = manifest.get("preparation")
    _require(isinstance(preparation, dict) and isinstance(preparation.get("identity"), dict),
             "Action-input preparation identity is missing")
    original = preparation["identity"].get("window")
    _require(isinstance(original, dict), "Action-input original window is missing")
    for field in ("candidate_id", "game_id", "approved_role", "source_video", "time_base",
                  "source_frame_range_inclusive", "source_pts_ticks_inclusive", "source_end_exclusive_pts_ticks"):
        _require(original.get(field) == manifest.get(field), f"Producer identity differs in {field}")
    verification = original.get("source_verification")
    _fields(verification, {"audit", "hash_field", "stat_field", "source_stat"}, "source_verification")
    _text(verification["hash_field"], "source_verification.hash_field")
    _text(verification["stat_field"], "source_verification.stat_field")
    audit = _parse(_read_binding(verification["audit"], root))
    _require(isinstance(audit, dict) and audit.get(verification["hash_field"]) == doc["source_video"]["sha256"]
             and audit.get(verification["stat_field"]) == verification["source_stat"],
             "Original action-input source audit differs")
    source_path = _bound_path(root, doc["source_video"]["path"])
    _require(source_path.is_file(), "Parent source video is missing")
    stat = source_path.stat()
    _require({"bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns} == verification["source_stat"],
             "Parent source stat changed since completed action-input audit")
    if verify_images:
        for frame in doc["frames"]:
            read_verified_png(frame, doc["source_video"], root)
    return {"status": "verified", "frames_verified": len(doc["frames"]) if verify_images else 0,
            "frame_map_rows_verified": len(doc["frames"]), "png_verification_skipped": not verify_images,
            "approval_sha256": doc["approval"]["sha256"], "full_source_bytes_read": 0,
            "human_label_review": "pending", "window_id": window["window_id"],
            "action_input_manifest_sha256": window["input_manifest"]["sha256"]}


def _encoded(doc: dict[str, Any]) -> bytes:
    return (json.dumps(doc, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


@contextmanager
def _exclusive_lock(path: Path):
    lock = path.with_name(path.name + ".lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise AnnotationConflictError("Annotation file is busy; retry after the other save") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        yield
    finally:
        lock.unlink()


def _atomic_replace(path: Path, raw: bytes) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent,
                                         prefix=path.name + ".", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def initialize_annotations(path: Path, data: Any) -> dict[str, Any]:
    """Create only a genuinely unlabeled draft; never overwrite any artifact."""
    doc = validate_annotations(data)
    _require(doc["revision"] == 0 and doc["review"]["annotator_id"] is None,
             "Initialization requires revision 0 and a null annotator")
    _require(doc["created_at_utc"] == doc["updated_at_utc"], "Initialization timestamps must agree")
    path = Path(path)
    with _exclusive_lock(path):
        if path.exists():
            raise AnnotationConflictError("Annotation file already exists")
        _atomic_replace(path, _encoded(doc))
    return doc


def save_annotations(path: Path, annotations: list[dict[str, Any]], *,
                     expected_revision: int, expected_sha256: str,
                     annotator_id: str) -> dict[str, Any]:
    """Save label rows only, preserving immutable metadata and the prior bytes.

The server verifies bound assets before calling this function. The exclusive
lock coordinates writers; both revision and exact-byte digest detect stale
clients or external edits. Human review acceptance is never set here.
"""
    _integer(expected_revision, "expected_revision")
    _sha(expected_sha256, "expected_sha256")
    _text(annotator_id, "annotator_id")
    annotator_id = annotator_id.strip()
    path = Path(path)
    with _exclusive_lock(path):
        old_bytes = path.read_bytes()
        old_sha = hashlib.sha256(old_bytes).hexdigest()
        current = validate_annotations(_parse(old_bytes))
        if current["revision"] != expected_revision or old_sha != expected_sha256:
            raise AnnotationConflictError("Stale annotation revision; reload before saving")
        if current["review"]["annotator_id"] not in (None, annotator_id):
            raise AnnotationConflictError("Changing the recorded annotator requires a separate provenance decision")
        updated = copy.deepcopy(current)
        updated["annotations"] = copy.deepcopy(annotations)
        updated["review"]["annotator_id"] = annotator_id
        updated["revision"] += 1
        updated["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        updated = validate_annotations(updated)
        history = path.with_name(path.stem + ".history")
        history.mkdir(exist_ok=True)
        snapshot = history / f"revision_{current['revision']:06d}_{old_sha}.json"
        try:
            with snapshot.open("xb") as handle:
                handle.write(old_bytes)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            if snapshot.read_bytes() != old_bytes:
                raise AnnotationConflictError("Existing prior snapshot does not match current bytes")
        if path.read_bytes() != old_bytes:
            raise AnnotationConflictError("Annotation changed externally during save")
        _atomic_replace(path, _encoded(updated))
    return updated
