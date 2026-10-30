"""Prepare native RGB inputs for an approved, unlabeled NBA observation.

Existing pilot images retain their exact records. Only missing contiguous ranges
are decoded, into unique attempt directories. A failed range never overwrites
its evidence; completed ranges can be resumed without another source decode.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import re
import subprocess
import time
import uuid

from PIL import Image

from . import nba_annotations as nba
from . import nba_wasb_diagnostic as evidence
from .prepare_nba_annotation_pilot import extraction_command, parse_framehash, source_stat

SCHEMA = "nba_action_inputs/v0.1"


def _source_rows(root, window):
    """Validate bounded source authority without hashing the original recording."""
    source = evidence.contained(root, window["source_video"]["path"])
    verification = window["source_verification"]
    audit = evidence.read_json(evidence.bound(root, verification["audit"]))
    evidence.require(source.is_file() and source_stat(source) == verification["source_stat"],
                     "Original source size/mtime changed")
    evidence.require(audit[verification["hash_field"]] == window["source_video"]["sha256"]
                     and audit[verification["stat_field"]] == verification["source_stat"],
                     "Completed source audit differs from approved source")
    path = evidence.bound(root, window["frame_map"])
    # Reuse the duplicate-key/nonfinite checks of the evidence reader without
    # materializing a temporary JSON document.
    import json
    def pairs(items):
        result = {}
        for key, value in items:
            evidence.require(key not in result, "Duplicate frame-map JSON key")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError(f"Nonfinite frame-map value: {value}")
    rows = [json.loads(line, object_pairs_hook=pairs, parse_constant=invalid)
            for line in path.read_text(encoding="utf-8").splitlines()]
    first, last = window["source_frame_range_inclusive"]
    evidence.require(type(first) is int and type(last) is int and 0 <= first <= last
                     < window["source_video"]["frame_count"], "Invalid source range")
    selected = [row for row in rows if first <= row["source_frame_index"] <= last + 1]
    evidence.require([row["source_frame_index"] for row in selected] == list(range(first, last + 2)),
                     "Frame map does not supply exact ordered source range plus end boundary")
    evidence.require(window["time_base"] == "1/90000"
                     and all(row["time_base"] == "1/90000" for row in selected), "Invalid native time base")
    pts = [row["source_pts_ticks"] for row in selected]
    evidence.require(all(type(tick) is int for tick in pts)
                     and all(b - a in (1440, 1530) for a, b in zip(pts, pts[1:])),
                     "Unexpected native cadence; inspect source gaps before preparation")
    evidence.require([pts[0], pts[-2]] == window["source_pts_ticks_inclusive"]
                     and pts[-1] == window["source_end_exclusive_pts_ticks"]
                     and len(selected) - 1 == window["frames"], "Approved source range/PTS/count differs")
    return source, selected[:-1], pts[-1]


def _missing_ranges(indices, reused):
    ranges = []
    for index in indices:
        if index in reused:
            continue
        if ranges and index == ranges[-1][-1] + 1:
            ranges[-1].append(index)
        else:
            ranges.append([index])
    return ranges


def _verify_frames(root, frames, source, rows):
    evidence.require(len(frames) == len(rows), "Input frame count differs")
    for frame, row in zip(frames, rows, strict=True):
        evidence.require(set(frame) == {"source_frame_index", "source_pts_ticks", "png"}
                         and frame["source_frame_index"] == row["source_frame_index"]
                         and frame["source_pts_ticks"] == row["source_pts_ticks"],
                         "Input frames differ from source frame map")
        nba.read_verified_png(frame, source, root)


def _extract_range(root, window, rows, end_pts, directory, identity, ffmpeg):
    completion = directory / "completion.json"
    def read_complete(path):
        saved = evidence.read_json(path)
        evidence.require(saved["status"] == "complete" and saved["identity"] == identity,
                         "Completed extraction range identity differs")
        for item in saved["evidence"]:
            evidence.bound(root, item)
        _verify_frames(root, saved["frames"], window["source_video"], rows)
        return saved
    if completion.exists():
        saved = read_complete(completion)
        return saved["frames"]
    # The attempt completion is durable before the shared pointer is published.
    # Recover that evidence after a receipt-delivery failure without decoding
    # the successfully completed range again.
    completed_attempts = sorted(directory.glob("attempts/*/completed.json"))
    evidence.require(len(completed_attempts) <= 1, "Ambiguous completed extraction attempts")
    if completed_attempts:
        saved = read_complete(completed_attempts[0])
        evidence.write_once(completion, saved)
        return saved["frames"]
    attempt = directory / "attempts" / uuid.uuid4().hex
    (attempt / "frames").mkdir(parents=True)
    source = evidence.contained(root, window["source_video"]["path"])
    before = source_stat(source)
    evidence.require(before == window["source_verification"]["source_stat"],
                     "Original source changed before bounded decode")
    command = extraction_command(str(ffmpeg), source, attempt, rows[0]["source_frame_index"],
                                 rows[0]["source_pts_ticks"], end_pts)
    started = time.monotonic()
    evidence.write_once(attempt / "started.json", {
        "status": "started", "at_utc": evidence.stamp(), "identity": identity,
        "command": command, "source_stat_before": before, "source_hash_recomputed": False,
        "code": evidence.binding(root, Path(__file__)) if Path(__file__).is_relative_to(root)
        else {"sha256": evidence.digest(Path(__file__))},
        "extraction_helper_sha256": evidence.digest(Path(__file__).with_name("prepare_nba_annotation_pilot.py")),
    })
    try:
        with (attempt / "ffmpeg.stdout.txt").open("xb") as stdout, (attempt / "ffmpeg.stderr.txt").open("xb") as stderr:
            result = subprocess.run(command, stdout=stdout, stderr=stderr, check=False)
        evidence.require(result.returncode == 0, f"Native extraction failed: exit {result.returncode}")
        hashes = parse_framehash(attempt / "source_rgb_framehash.txt")
        evidence.require([row["pts"] for row in hashes] == [row["source_pts_ticks"] for row in rows],
                         "Actual decoded PTS differ from approved original frame inventory")
        files = sorted((attempt / "frames").iterdir())
        evidence.require([path.name for path in files] == [f"source_{row['source_frame_index']:06d}.png" for row in rows],
                         "Decoded PNG inventory differs")
        frames = []
        width, height = window["source_video"]["width_px"], window["source_video"]["height_px"]
        for row, rgb, path in zip(rows, hashes, files, strict=True):
            with Image.open(path) as image:
                evidence.require(image.mode == "RGB" and image.size == (width, height), "Native PNG shape/mode differs")
                rgb_sha = hashlib.sha256(image.tobytes()).hexdigest()
            evidence.require(rgb["bytes"] == width * height * 3 and rgb["rgb_sha256"] == rgb_sha,
                             "Native PNG pixels differ from emitted decoded RGB hash")
            frames.append({"source_frame_index": row["source_frame_index"], "source_pts_ticks": row["source_pts_ticks"],
                           "png": {"path": path.relative_to(root).as_posix(), "sha256": evidence.digest(path),
                                   "rgb_sha256": rgb_sha}})
        evidence.require(source_stat(source) == before == window["source_verification"]["source_stat"],
                         "Original source changed during bounded decode")
        receipt = {"status": "complete", "identity": identity, "frames": frames,
                   "elapsed_seconds": time.monotonic() - started, "completed_at_utc": evidence.stamp(),
                   "source_stat_after": source_stat(source), "source_hash_recomputed": False,
                   "evidence": [evidence.binding(root, attempt / name) for name in
                                ("started.json", "source_rgb_framehash.txt", "ffmpeg.stdout.txt", "ffmpeg.stderr.txt")]}
        evidence.write_once(attempt / "completed.json", receipt)
        evidence.write_once(completion, receipt)
        return frames
    except Exception as error:
        evidence.write_once(attempt / "failed.json", {"status": "failed_preserved", "at_utc": evidence.stamp(),
                            "elapsed_seconds": time.monotonic() - started, "error_type": type(error).__name__,
                            "error": str(error)})
        raise


def prepare_inputs(root, proposal, approval_binding, old_references, output, ffmpeg):
    """Return bound unlabeled manifests; ``output`` is a dedicated input directory.

    The caller owns scientific scope authorization before this entry point. This
    helper also checks the bound approval/proposal before any output mutation.
    Original full-game file hashes are never recomputed here.
    """
    root, output = Path(root).resolve(), Path(output).resolve()
    evidence.require(output.is_relative_to(root / "data/outputs"), "Input output must remain under data/outputs")
    approval = evidence.read_json(evidence.bound(root, approval_binding))
    evidence.require(approval.get("schema_version") == "nba_wasb_action_observation_approval/v0.1"
                     and approval.get("status") == "approved" and approval.get("approved_by") == "Ryan",
                     "Native action preparation requires approved scope")
    evidence.require(evidence.read_json(evidence.bound(root, approval["proposal"])) == proposal,
                     "Approval binds a different proposal")
    references = {reference["candidate_id"]: reference for reference in old_references}
    evidence.require(len(references) == len(old_references), "Duplicate prior reference candidate")
    windows = proposal["windows"]
    evidence.require(len({w["candidate_id"] for w in windows}) == len(windows), "Duplicate source window")
    prepared = []
    for window in windows:
        candidate = window["candidate_id"]
        evidence.require(isinstance(candidate, str) and re.fullmatch(r"[a-z0-9][a-z0-9_-]*", candidate),
                         "Invalid candidate identifier")
        source, rows, end_pts = _source_rows(root, window)
        reference = references[candidate]
        evidence.require(all(reference[key] == window[key] for key in
                             ("candidate_id", "game_id", "approved_role", "source_video", "time_base")),
                         "Prior reference source/game/role differs")
        old = {frame["source_frame_index"]: copy.deepcopy(frame) for frame in reference["frames"]}
        mapping = {row["source_frame_index"]: row for row in rows}
        evidence.require(len(old) == len(reference["frames"]) == window["reused_native_png_frames"]
                         and set(old) <= set(mapping), "Prior PNG inventory differs from approved input reuse")
        evidence.require(len(rows) - len(old) == window["new_native_png_frames"], "New PNG count differs")
        _verify_frames(root, list(old.values()), window["source_video"], [mapping[index] for index in old])
        prepared.append((window, rows, end_pts, old))
    output.mkdir(parents=True, exist_ok=True)
    lock = evidence.acquire_run_lock(output / ".prepare.lock")
    try:
        results = []
        for window, rows, end_pts, old in prepared:
            directory = output / window["candidate_id"]
            identity = {"schema_version": SCHEMA, "proposal": approval["proposal"], "approval": approval_binding,
                        "window": window, "reused_frames": list(old.values())}
            directory.mkdir(parents=True, exist_ok=True)
            evidence.write_once(directory / "input_identity.json", identity)
            manifest_path = directory / "manifest.json"
            if manifest_path.exists():
                existing = evidence.read_json(manifest_path)
                evidence.require(existing["preparation"]["identity"] == identity, "Completed input manifest identity differs")
                for item in existing["preparation"]["range_completions"]:
                    evidence.bound(root, item)
            lookup = {row["source_frame_index"]: row for row in rows}
            all_frames = dict(old)
            ranges = _missing_ranges(list(lookup), old)
            receipts = []
            for indices in ranges:
                selected = [lookup[index] for index in indices]
                boundary = lookup[indices[-1] + 1]["source_pts_ticks"] if indices[-1] + 1 in lookup else end_pts
                range_dir = directory / f"range_{indices[0]:06d}_{indices[-1]:06d}"
                evidence.require(not manifest_path.exists() or (range_dir / "completion.json").is_file(),
                                 "Completed input range receipt is missing; preserve and investigate")
                range_identity = {"input_identity_sha256": evidence.canonical(identity),
                                  "source_frame_range_inclusive": [indices[0], indices[-1]],
                                  "source_pts_ticks_inclusive": [selected[0]["source_pts_ticks"], selected[-1]["source_pts_ticks"]],
                                  "source_end_exclusive_pts_ticks": boundary}
                extracted = _extract_range(root, window, selected, boundary, range_dir, range_identity, ffmpeg)
                all_frames.update({frame["source_frame_index"]: frame for frame in extracted})
                receipts.append(evidence.binding(root, range_dir / "completion.json"))
            manifest = {"schema_version": SCHEMA, **{key: copy.deepcopy(window[key]) for key in
                        ("candidate_id", "game_id", "approved_role", "source_video", "time_base",
                         "source_frame_range_inclusive", "source_pts_ticks_inclusive", "source_end_exclusive_pts_ticks")},
                        "frames": [all_frames[row["source_frame_index"]] for row in rows],
                        "preparation": {"identity": identity, "range_completions": receipts,
                                        "source_hash_recomputed": False, "annotations_created": 0,
                                        "new_native_png_frames": window["new_native_png_frames"],
                                        "reused_native_png_frames": window["reused_native_png_frames"]}}
            evidence.write_once(manifest_path, manifest)
            results.append(manifest)
        return results
    finally:
        evidence.release_run_lock(lock)
