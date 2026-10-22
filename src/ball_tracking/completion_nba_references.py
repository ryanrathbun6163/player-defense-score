"""Validate and render pending references against fixed NBA campaign episodes.

This module consumes source PNGs and manual AI proposals. It does not create
centers, accept labels, fit models, select checkpoints, or decode source video.
The assigned game role is retained, while both eligibility flags remain false.
Native rendering currently requires constant cadence; variable timing fails
explicitly before creating output rather than being silently resampled.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import subprocess

import cv2
import numpy as np

from .annotations import FrameAnnotation, SourceVideo
from .completion_references import binding, read_json, write_new


def _path(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Evidence path is outside repository")
    return path


def _check_binding(root, expected, label):
    if not isinstance(expected, dict) or not {"path", "sha256", "bytes"} <= expected.keys():
        raise ValueError(f"{label} requires path, sha256 and bytes")
    actual = binding(root, _path(root, expected["path"]))
    if any(actual[key] != expected[key] for key in actual):
        raise ValueError(f"{label} binding changed")
    return actual


def _fraction(value, label):
    try:
        result = Fraction(str(value))
    except (ValueError, ZeroDivisionError, TypeError) as exc:
        raise ValueError(f"Invalid {label}") from exc
    if result <= 0:
        raise ValueError(f"Invalid {label}")
    return result


def _same_seconds(value, expected):
    return (type(value) in (int, float) and math.isfinite(value)
            and abs(value - float(expected)) <= 1e-9)


def guard_episode(config, source_roles):
    """Resolve an unchanged episode/game assignment before image pixels are read."""
    if config.get("schema_version") != "completion_nba_reference_batch/v0.1":
        raise ValueError("Unexpected NBA batch config schema")
    if (source_roles.get("schema_version") != "ball_completion_source_roles/v0.1"
            or source_roles.get("status") != "source_roles_and_episode_windows_fixed_references_pending"):
        raise ValueError("Unexpected fixed source-role manifest")
    if (config.get("human_acceptance") != "pending"
            or config.get("annotation_origin") != "assistant_visual_proposal"
            or config.get("training_eligible") is not False
            or config.get("checkpoint_selection_eligible") is not False):
        raise ValueError("NBA references must remain pending and ineligible for fitting/selection")
    episodes = [e for e in source_roles["episodes"] if e["episode_id"] == config.get("episode_id")]
    if len(episodes) != 1:
        raise ValueError("Episode is absent or duplicated in the fixed source-role manifest")
    episode = episodes[0]
    games = [g for g in source_roles["game_roles"] if g["game_id"] == episode["game_id"]]
    if (len(games) != 1 or episode["role"] not in {"training", "checkpoint_validation"}
            or games[0]["role"] != episode["role"] or config.get("role") != episode["role"]):
        raise ValueError("Fixed episode/game role changed or is not permitted")
    if config.get("game_id", episode["game_id"]) != episode["game_id"]:
        raise ValueError("Configured game differs from fixed episode")
    if episode.get("source_selection_status") != "fixed_before_new_model_predictions":
        raise ValueError("Episode window was not fixed before predictions")
    native = _fraction(config["review"]["native_playback_fps"], "native playback rate")
    slow = _fraction(config["review"]["slow_playback_fps"], "slow playback rate")
    try:
        source_rate = Fraction(episode["source"]["average_rate"])
    except ValueError:
        source_rate = None  # Fixed SAC manifest explicitly names its variable cadence.
    if source_rate is not None and native != source_rate:
        raise ValueError("Configured native playback rate differs from fixed source")
    if slow > native:
        raise ValueError("Slow playback must not exceed native playback rate")
    if any(config["review"].get(key) is not True for key in
           ("source_pixels_only", "whole_batch_required", "uncertainty_and_actual_final_required")):
        raise ValueError("Required complete source-only visual review cannot be disabled")
    return episode


def _check_proposal(config, episode, proposal):
    if (proposal.get("status") != "assistant_proposal_pending_human_acceptance"
            or proposal.get("annotation_origin") != "assistant_visual_proposal"
            or proposal.get("human_acceptance") is not None
            or "human_acceptance" not in proposal
            or proposal.get("training_eligible") is not False
            or proposal.get("checkpoint_selection_eligible") is not False
            or not isinstance(proposal.get("annotator_id"), str)
            or not proposal["annotator_id"].strip()
            or proposal.get("batch_id") != config["batch_id"]
            or any(proposal.get(k) != episode[k] for k in ("episode_id", "game_id", "role"))):
        raise ValueError("Proposal identity, role, authorship or pending eligibility differs")


def join_native_frames(episode, fixed_frames, source_frames, source_timing, packet_timing):
    """Join the producer's actual PNG/timing records to the fixed episode census.

    This is metadata-only. Packet presentation order, rather than decode order,
    determines the source frame index. Both source-relative and review-relative
    times are retained without replacing the authoritative native PTS.
    """
    source = episode["source"]
    streams = packet_timing["streams"]
    if (len(streams) != 1 or streams[0]["width"] != source["width"]
            or streams[0]["height"] != source["height"]
            or streams[0]["time_base"] != source["time_base"]):
        raise ValueError("Actual source timing dimensions/time base differ from fixed source")
    packets = sorted(packet_timing["packets"], key=lambda row: row["pts"])
    if (len(packets) != source["decoded_frames"]
            or len({p["pts"] for p in packets}) != len(packets)):
        raise ValueError("Source packet presentation census differs from fixed source")
    if any(type(p["pts"]) is not int or type(p["duration"]) is not int or p["duration"] <= 0
           for p in packets):
        raise ValueError("Invalid actual native packet timing")
    start, end = episode["first_source_frame"], episode["last_source_frame"]
    if (type(start) is not int or type(end) is not int or not 0 <= start <= end < len(packets)
            or end - start + 1 != episode["new_frame_judgments"]):
        raise ValueError("Fixed episode frame range/count differs")
    indices = list(range(start, end + 1))
    for rows, key, label in ((fixed_frames, "source_frame", "fixed frame list"),
                             (source_frames, "frame_index", "source PNG"),
                             (source_timing, "source_frame_index", "source timing")):
        if ([row[key] for row in rows] != indices
                or any(type(row[key]) is not int for row in rows)):
            raise ValueError(f"{label} census differs from fixed episode")
    unit = _fraction(source["time_base"], "source time base")
    if episode["time_base"] != source["time_base"]:
        raise ValueError("Episode time base differs from fixed source")
    lo, hi = episode["window_pts_half_open"]
    result = []
    for index, fixed, png, decoded in zip(indices, fixed_frames, source_frames, source_timing):
        packet = packets[index]
        pts, duration = packet["pts"], packet["duration"]
        if (fixed["pts"] != pts or type(fixed["pts"]) is not int
                or fixed["time_base"] != source["time_base"] or not lo <= pts < hi
                or not _same_seconds(fixed["seconds"], pts * unit)):
            raise ValueError("Fixed frame-list PTS/window differs from actual source")
        for row in (png, decoded):
            if (type(row["native_pts_ticks"]) is not int or row["native_pts_ticks"] != pts
                    or type(row["native_duration_ticks"]) is not int
                    or row["native_duration_ticks"] != duration
                    or row["native_time_base"] != source["time_base"]):
                raise ValueError("PNG/source-timing native PTS or duration differs from fixed source")
        if (not _same_seconds(decoded["native_time_seconds"], pts * unit)
                or type(decoded["decoded_frame_duration_ticks"]) is not int
                or decoded["decoded_frame_duration_ticks"] not in (0, duration)
                or not decoded.get("duration_authority")):
            raise ValueError("Decoded source timing disagrees with packet duration/PTS")
        if index < end and pts + duration != packets[index + 1]["pts"]:
            raise ValueError("Selected native frame intervals are not contiguous")
        result.append({"source_frame_index": index, "native_pts_ticks": pts,
                       "native_duration_ticks": duration, "native_time_base": source["time_base"],
                       "native_pts_seconds": float(pts * unit),
                       "clip_relative_seconds": float((pts - packets[0]["pts"]) * unit),
                       "batch_relative_seconds": float((pts - packets[start]["pts"]) * unit),
                       "source_png": png})
    return result


def validate_preparation(root, folder, episode, frames):
    """Require the producer's completed audit, including every native RGB join.

    A retained failed attempt is evidence, never a substitute for the separate
    successful preparation/audit records. Optional recovery evidence is bound
    when present without requiring a prior failure for future clean batches.
    """
    preparation_path, audit_path = folder / "preparation.json", folder / "source_pixel_audit.json"
    if not preparation_path.is_file() or not audit_path.is_file():
        raise ValueError("Completed source preparation and successful source-pixel audit are required")
    preparation, audit = read_json(preparation_path), read_json(audit_path)
    count, source = len(frames), episode["source"]
    if (preparation.get("schema_version") != "completion_nba_source_preparation/v0.1"
            or preparation.get("status") != "passed"
            or any(preparation.get(k) != episode[k] for k in ("episode_id", "game_id", "role"))
            or preparation.get("human_acceptance") is not None
            or "human_acceptance" not in preparation
            or preparation.get("training_eligible") is not False
            or preparation.get("checkpoint_selection_eligible") is not False
            or preparation.get("fitting_authorized_by_this_artifact") is not False
            or preparation.get("selected_frame_count") != count
            or preparation.get("pixel_audit_exact_matches") != count
            or preparation.get("original_pngs_unchanged") is not True
            or preparation.get("source_dimensions_px") != [source["width"], source["height"]]
            or preparation.get("native_full_clip_frame_count") != source["decoded_frames"]
            or preparation.get("time_base") != source["time_base"]
            or preparation.get("range_inclusive") != [frames[0]["source_frame_index"], frames[-1]["source_frame_index"]]):
        raise ValueError("Source preparation is not a completed, unchanged pending reference preparation")
    if (audit.get("schema_version") != "completion_nba_source_pixel_audit/v0.1"
            or audit.get("status") != "passed" or audit.get("episode_id") != episode["episode_id"]
            or audit.get("selected_frames_checked") != count or audit.get("exact_matches") != count
            or audit.get("native_pts_matches") != count or audit.get("failures") != 0):
        raise ValueError("Successful source-pixel audit does not cover every selected frame")
    expected = {"source": binding(root, _path(root, source["path"])),
                "source_frames": binding(root, folder / "source_frames.json"),
                "source_timing": binding(root, folder / "source_timing.json"),
                "source_packet_timing": binding(root, folder / "source_packet_timing.json"),
                "source_pixel_audit": binding(root, audit_path)}
    for key, actual in expected.items():
        if preparation.get(key) != actual:
            raise ValueError(f"Completed preparation {key} binding differs from consumed record")
    for key in ("source", "source_frames", "source_timing"):
        if audit.get(key) != expected[key]:
            raise ValueError(f"Source-pixel audit {key} binding differs from consumed record")
    preserved = []
    for record in (preparation, audit):
        for key, value in record.items():
            if isinstance(value, dict) and {"path", "sha256", "bytes"} <= value.keys():
                checked = _check_binding(root, value, f"Source preparation/audit {key}")
                if checked not in preserved:
                    preserved.append(checked)
    rows = audit["rows"]
    if [row["frame_index"] for row in rows] != [frame["source_frame_index"] for frame in frames]:
        raise ValueError("Source-pixel audit frame census differs")
    for row, frame in zip(rows, frames):
        png = frame["source_png"]
        if (row["native_pts_ticks"] != frame["native_pts_ticks"] or row["png_sha256"] != png["sha256"]
                or any(row[key] != png["rgb_sha256"] for key in
                       ("pyav_rgb_sha256", "saved_png_rgb_sha256", "ffmpeg_rgb_sha256"))
                or row["exact_rgb_equal"] is not True or row["maximum_channel_difference"] != 0
                or row["mean_absolute_channel_difference"] != 0):
            raise ValueError("Source-pixel audit per-frame RGB/PTS evidence differs from consumed PNG")
    return {"source_preparation": binding(root, preparation_path),
            "source_pixel_audit": expected["source_pixel_audit"],
            "source_color_metadata": audit["source_color_metadata"],
            "source_preparation_evidence": preserved}


def validate_batch(root, config_path, proposal_path):
    root = Path(root).resolve()
    config_path, proposal_path = _path(root, config_path), _path(root, proposal_path)
    config, proposal = read_json(config_path), read_json(proposal_path)
    roles_binding = _check_binding(root, config["source_roles"], "Fixed source-role manifest")
    roles = read_json(_path(root, roles_binding["path"]))
    episode = guard_episode(config, roles)
    _check_proposal(config, episode, proposal)
    source_binding = _check_binding(root, episode["source"], "Fixed source video")
    fixed_binding = _check_binding(root, episode["frame_list"], "Fixed episode frame list")
    folder = _path(root, config["output_root"])
    frames_path, timing_path = folder / "source_frames.json", folder / "source_timing.json"
    packet_path = folder / "source_packet_timing.json"
    frames = join_native_frames(episode, read_json(_path(root, fixed_binding["path"])),
                               read_json(frames_path), read_json(timing_path), read_json(packet_path))
    preparation_evidence = validate_preparation(root, folder, episode, frames)
    rows = proposal["annotations"]
    if ([row["frame_index"] for row in rows] != [frame["source_frame_index"] for frame in frames]
            or any(type(row["frame_index"]) is not int for row in rows)):
        raise ValueError("Annotation census differs from fixed episode")
    source = episode["source"]
    # This object supplies pixel/frame bounds to the shared annotation parser;
    # authoritative timing comes from the native PTS join above, never fps math.
    bounds = SourceVideo.from_mapping({"path": source["path"], "sha256": source["sha256"],
                                       "width_px": source["width"], "height_px": source["height"],
                                       "fps": float(_fraction(config["review"]["native_playback_fps"], "native playback rate")),
                                       "frame_count": source["decoded_frames"]})
    if min(source["width"], source["height"]) < 120:
        raise ValueError("Source is too small for the review detail crop")
    for position, (frame, row) in enumerate(zip(frames, rows)):
        if FrameAnnotation.from_mapping(row, position, bounds).annotation_status != "labeled":
            raise ValueError("NBA reference batch contains incomplete labels")
        png = frame["source_png"]
        _check_binding(root, png, "Source PNG")
        image = cv2.imread(str(_path(root, png["path"])))
        if image is None or image.shape != (source["height"], source["width"], 3):
            raise ValueError("Source PNG native dimensions differ")
        rgb_hash = hashlib.sha256(cv2.cvtColor(image, cv2.COLOR_BGR2RGB).tobytes()).hexdigest()
        if rgb_hash != png["rgb_sha256"]:
            raise ValueError("Source PNG decoded RGB hash differs from producer record")
        frame["annotation"] = row
    return config, {"schema_version": "completion_nba_reference_review/v0.1",
                    "batch_id": config["batch_id"], "episode_id": episode["episode_id"],
                    "game_id": episode["game_id"], "role": episode["role"],
                    "status": proposal["status"], "config": binding(root, config_path),
                    "proposal": binding(root, proposal_path), "source_roles": roles_binding,
                    "fixed_episode": episode, "fixed_frame_list": fixed_binding,
                    "source_video": source_binding, "source_metadata": source,
                    "source_frames": binding(root, frames_path),
                    "source_timing": binding(root, timing_path),
                    "source_packet_timing": binding(root, packet_path),
                    **preparation_evidence,
                    "range_inclusive": [episode["first_source_frame"], episode["last_source_frame"]],
                    "annotation_origin": proposal["annotation_origin"],
                    "annotator_id": proposal["annotator_id"], "human_acceptance": None,
                    "training_eligible": False, "checkpoint_selection_eligible": False,
                    "counts": dict(Counter(row["visibility"] for row in rows)),
                    "eligible_centers": sum(row["localization_eligible"] for row in rows),
                    "null_centers": sum(row["geometry"] is None for row in rows), "frames": frames,
                    "validation": {"all_source_png_hashes_checked": True,
                                   "all_source_png_rgb_hashes_checked": True,
                                   "independent_source_rgb_exact_matches_checked": len(frames),
                                   "native_source_frame_and_pts_joins_checked": len(frames),
                                   "actual_emitted_video_frames_checked": 0,
                                   "human_visual_acceptance": "pending"}}


def render_frame(frame, item, count, episode_id, role, final_index, source_final_index):
    """Whole source plus current-frame detail, preserving null geometry as unknown."""
    canvas = np.zeros((720, 1280, 3), dtype=np.uint8)
    canvas[:540, :960] = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)
    row = item["annotation"]
    geometry = row["geometry"]
    if geometry is not None:
        x, y = geometry["center_xy_px"]
        cv2.drawMarker(canvas, (round(x * 960 / frame.shape[1]), round(y * 540 / frame.shape[0])),
                       (0, 255, 255), cv2.MARKER_CROSS, 15, 1)
        x0 = min(max(0, round(x) - 60), frame.shape[1] - 120)
        y0 = min(max(0, round(y) - 60), frame.shape[0] - 120)
        crop = cv2.resize(frame[y0:y0 + 120, x0:x0 + 120], (300, 300), interpolation=cv2.INTER_NEAREST)
        point = (round((x - x0) * 2.5), round((y - y0) * 2.5))
        cv2.drawMarker(crop, point, (0, 255, 255), cv2.MARKER_CROSS, 22, 1)
        cv2.circle(crop, point, round(geometry["uncertainty_radius_px"] * 2.5), (0, 255, 255), 1)
        canvas[40:340, 970:1270] = crop
    lines = [f"{episode_id} | assigned role: {role} | AI proposal; acceptance PENDING",
             f"Source frame {item['source_frame_index']} | native PTS {item['native_pts_ticks']} x {item['native_time_base']} sec",
             f"{row['visibility']} | complete-ball center {geometry['center_xy_px'] if geometry else 'UNKNOWN'}",
             f"Uncertainty: {geometry['uncertainty_radius_px'] if geometry else 'n/a'} source px | no fitting or checkpoint selection",
             f"Review all {count} frames | batch final {final_index}; source final {source_final_index}."]
    for index, line in enumerate(lines):
        cv2.putText(canvas, line, (20, 572 + index * 29), cv2.FONT_HERSHEY_SIMPLEX,
                    .60, (235, 235, 235), 1, cv2.LINE_AA)
    return canvas


def _canvas(root, item, context):
    image = cv2.imread(str(_path(root, item["source_png"]["path"])))
    if image is None:
        raise ValueError("Source PNG cannot be read")
    return render_frame(image, item, *context)


def review_color_filter(primaries, transfer):
    # Frame properties must be set after scale as well as on the output codec.
    # With raw RGB input, scale otherwise forwards unspecified primaries/transfer
    # and can override encoder options, silently dropping both emitted fields.
    return ("scale=in_range=full:out_color_matrix=bt601:out_range=tv,"
            f"setparams=range=limited:colorspace=smpte170m:color_primaries={primaries}:color_trc={transfer}")


def review_encoding_command(path, fps, primaries, transfer):
    """One production command shared with the actual one-frame encode regression."""
    return ["ffmpeg", "-hide_banner", "-loglevel", "error", "-n", "-f", "rawvideo",
            "-pix_fmt", "bgr24", "-s", "1280x720", "-r", str(fps), "-i", "-",
            "-an", "-vf", review_color_filter(primaries, transfer), "-c:v", "libx264",
            "-crf", "18", "-pix_fmt", "yuv420p", "-colorspace", "smpte170m",
            "-color_range", "tv", "-color_primaries", primaries, "-color_trc", transfer,
            "-movflags", "+faststart", str(path)]


def render(root, config_path, proposal_path, destination):
    root = Path(root).resolve()
    config, manifest = validate_batch(root, config_path, proposal_path)
    frames = manifest["frames"]
    native_fps = _fraction(config["review"]["native_playback_fps"], "native playback rate")
    if any(Fraction(item["native_duration_ticks"]) * Fraction(item["native_time_base"])
           != 1 / native_fps for item in frames):
        raise ValueError("Variable cadence requires a separately verified native-timing renderer")
    source_color = manifest["source_color_metadata"]
    primaries, transfer = source_color.get("color_primaries"), source_color.get("color_transfer")
    if not primaries or primaries == "unknown" or not transfer or transfer == "unknown":
        raise ValueError("Review encoding requires known source color primaries and transfer")
    color_filter = review_color_filter(primaries, transfer)
    manifest["review_color_conversion"] = {
        "source_pngs_changed": False, "input": "full-range native RGB pixels carried as bgr24",
        "ffmpeg_filter": color_filter, "output_color_space": "smpte170m",
        "output_color_range": "tv", "preserved_color_primaries": primaries,
        "preserved_color_transfer": transfer,
        "verification": "Every encoded frame is reconstructed to RGB by OpenCV using BT.601; emitted tags are separately checked with ffprobe."}
    destination = _path(root, destination)
    destination.mkdir(parents=True, exist_ok=False)
    context = (len(frames), manifest["episode_id"], manifest["role"], frames[-1]["source_frame_index"],
               manifest["source_metadata"]["decoded_frames"] - 1)
    videos = []
    for name, rate in (("review_native.mp4", config["review"]["native_playback_fps"]),
                       ("review_slow.mp4", config["review"]["slow_playback_fps"])):
        fps = _fraction(rate, "playback rate")
        path = destination / name
        command = review_encoding_command(path, fps, primaries, transfer)
        with (destination / (name + ".log")).open("xb") as log:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
            try:
                for item in frames:
                    process.stdin.write(_canvas(root, item, context).tobytes())
                process.stdin.close()
                if process.wait() != 0:
                    raise ValueError("NBA reference video encoding failed; partial output/log retained")
            finally:
                if process.stdin and not process.stdin.closed:
                    try:
                        process.stdin.close()
                    except BrokenPipeError:
                        pass
                if process.poll() is None:
                    process.kill()
                    process.wait()
        probe_command = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                         "stream=width,height,nb_frames,avg_frame_rate,color_range,color_space,color_transfer,color_primaries",
                         "-of", "json", str(path)]
        probe = json.loads(subprocess.run(probe_command, check=True, capture_output=True, text=True).stdout)
        probe_path = destination / name.replace(".mp4", "_encoded_probe.json")
        write_new(probe_path, probe)
        streams = probe.get("streams", [])
        if (len(streams) != 1 or streams[0].get("color_space") != "smpte170m"
                or streams[0].get("color_range") != "tv"
                or streams[0].get("color_primaries") != primaries
                or streams[0].get("color_transfer") != transfer
                or (streams[0].get("width"), streams[0].get("height")) != (1280, 720)
                or int(streams[0].get("nb_frames", -1)) != len(frames)
                or Fraction(streams[0].get("avg_frame_rate", "0")) != fps):
            raise ValueError("Encoded review metadata differs from declared color conversion/frame timing")
        capture = cv2.VideoCapture(str(path))
        errors, marker_errors, emitted = [], [], []
        try:
            for item in frames:
                ok, actual = capture.read()
                if not ok or actual.shape != (720, 1280, 3):
                    raise ValueError("NBA reference video frame census/dimensions differ")
                expected = _canvas(root, item, context)
                error = float(np.abs(actual.astype(np.int16) - expected.astype(np.int16)).mean())
                errors.append(error)
                if error > 8:
                    raise ValueError("Encoded NBA frame does not match source/label record")
                expected_crop, actual_crop = expected[40:340, 970:1270], actual[40:340, 970:1270]
                marker_error = None
                if item["annotation"]["geometry"] is not None:
                    marker = np.all(expected_crop == (0, 255, 255), axis=2)
                    if int(marker.sum()) < 20:
                        raise ValueError("Expected NBA label marker is absent")
                    marker_error = float(np.abs(actual_crop.astype(np.int16)[marker]
                                                - expected_crop.astype(np.int16)[marker]).mean())
                    marker_errors.append(marker_error)
                    if marker_error > 65:
                        raise ValueError("Encoded NBA label marker does not match its record")
                emitted.append({"source_frame_index": item["source_frame_index"],
                                "mean_absolute_pixel_error": error,
                                "label_marker_pixel_error": marker_error})
            if capture.read()[0]:
                raise ValueError("Unexpected additional NBA reference video frame")
            if abs(capture.get(cv2.CAP_PROP_FPS) - float(fps)) > .01:
                raise ValueError("NBA reference playback rate differs")
            final_path = destination / name.replace(".mp4", "_actual_final.png")
            if not cv2.imwrite(str(final_path), actual):
                raise ValueError("Could not save actual encoded final frame")
        finally:
            capture.release()
        videos.append({**binding(root, path), "frame_count": len(frames), "fps": float(fps),
                       "duration_seconds": float(len(frames) / fps),
                       "actual_final": binding(root, final_path),
                       "encoded_probe": binding(root, probe_path),
                       "encoding_command": command,
                       "all_frame_mean_absolute_pixel_errors": errors,
                       "all_frame_label_marker_pixel_errors": marker_errors,
                       "emitted_frame_checks": emitted})
    manifest["videos"] = videos
    manifest["validation"]["actual_emitted_video_frames_checked"] = len(frames) * len(videos)
    write_new(destination / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output:
        result = render(Path.cwd(), args.config, args.proposal, args.output)
    else:
        _, result = validate_batch(Path.cwd(), args.config, args.proposal)
    print(json.dumps({"status": result["status"], "episode_id": result["episode_id"],
                      "frame_count": len(result["frames"]), "counts": result["counts"]}))


if __name__ == "__main__":
    main()
