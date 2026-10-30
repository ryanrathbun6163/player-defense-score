"""Pending SAC references with native presentation timing and explicit seek context.

The original NBA producer remains unchanged. Raw packet/decoded durations are
evidence; presentation duration is independently joined to the next global PTS.
This module reads prepared PNGs, never the source video or a model.
"""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess

import av
import cv2
import numpy as np

from .annotations import FrameAnnotation, SourceVideo
from .completion_references import binding, read_json, write_new
from .completion_nba_references import (
    _path, _check_binding, _check_proposal, _fraction, _same_seconds,
    guard_episode as _legacy_guard, validate_preparation as _legacy_preparation,
    render_frame, _canvas, review_color_filter,
)


DURATION_AUTHORITY = "next_global_presentation_pts"


def guard_episode(config, source_roles):
    episode = _legacy_guard(config, source_roles)
    if (episode["game_id"] != "0022500829" or episode["source_clip_id"] != "existing_full_game"
            or episode["source"]["average_rate"] != "native variable16/17ms cadence"
            or config["review"].get("timing_mode") != "native_vfr"
            or _fraction(config["review"]["slow_playback_fps"], "slow rate") != 10):
        raise ValueError("SAC review requires its fixed source and explicit native presentation timing")
    return episode


def _packet_census(episode, packet_timing):
    source, streams = episode["source"], packet_timing["streams"]
    if (len(streams) != 1 or any(streams[0][k] != source[k] for k in ("width", "height", "time_base"))):
        raise ValueError("Actual SAC stream dimensions/time base differ from fixed source")
    packets = sorted(packet_timing["packets"], key=lambda row: row["pts"])
    if (len(packets) != source["decoded_frames"] or len({p["pts"] for p in packets}) != len(packets)
            or any(type(p["pts"]) is not int or "duration" not in p for p in packets)
            or any(p.get("duration") is not None and (type(p["duration"]) is not int or p["duration"] <= 0)
                   for p in packets)):
        raise ValueError("Full SAC packet presentation census or raw duration differs")
    return packets


def join_native_frames(episode, fixed_frames, source_frames, source_timing, packet_timing):
    """Join global native identity without treating packet duration as exposure."""
    packets = _packet_census(episode, packet_timing)
    source = episode["source"]
    start, end = episode["first_source_frame"], episode["last_source_frame"]
    if (type(start) is not int or type(end) is not int or not 0 <= start <= end < len(packets) - 1
            or end - start + 1 != episode["new_frame_judgments"]):
        raise ValueError("Fixed SAC range requires a following global PTS for its final interval")
    indices = list(range(start, end + 1))
    for rows, key in ((fixed_frames, "source_frame"), (source_frames, "frame_index"),
                      (source_timing, "source_frame_index")):
        if [r[key] for r in rows] != indices or any(type(r[key]) is not int for r in rows):
            raise ValueError("Selected SAC frame census differs from fixed episode")
    unit = _fraction(source["time_base"], "source time base")
    if episode["time_base"] != source["time_base"]:
        raise ValueError("Fixed SAC time base differs")
    lo, hi = episode["window_pts_half_open"]
    result = []
    for index, fixed, png, decoded in zip(indices, fixed_frames, source_frames, source_timing):
        pts = packets[index]["pts"]
        duration = packets[index + 1]["pts"] - pts
        raw_duration = packets[index].get("duration")
        if (type(fixed["pts"]) is not int or fixed["pts"] != pts or not lo <= pts < hi
                or fixed["time_base"] != source["time_base"] or not _same_seconds(fixed["seconds"], pts * unit)):
            raise ValueError("Fixed SAC frame-list PTS/window differs from full packet census")
        for row in (png, decoded):
            if (type(row["native_pts_ticks"]) is not int or row["native_pts_ticks"] != pts
                    or row["native_time_base"] != source["time_base"]
                    or type(row["presentation_duration_ticks"]) is not int
                    or row["presentation_duration_ticks"] != duration or row["native_duration_ticks"] != duration
                    or row["raw_packet_duration_ticks"] != raw_duration):
                raise ValueError("SAC PNG/timing raw packet duration, presentation interval or PTS differs")
        if (not _same_seconds(decoded["native_time_seconds"], pts * unit)
                or type(decoded["decoded_frame_duration_ticks"]) is not int
                or decoded["decoded_frame_duration_ticks"] < 0
                or decoded["duration_authority"] != DURATION_AUTHORITY):
            raise ValueError("SAC decoded timing lacks its explicit presentation-duration authority")
        result.append({"source_frame_index": index, "native_pts_ticks": pts,
                       "native_time_base": source["time_base"], "native_duration_ticks": duration,
                       "presentation_duration_ticks": duration, "raw_packet_duration_ticks": raw_duration,
                       "decoded_frame_duration_ticks": decoded["decoded_frame_duration_ticks"],
                       "duration_authority": DURATION_AUTHORITY,
                       "native_pts_seconds": float(pts * unit),
                       "clip_relative_seconds": float((pts - packets[0]["pts"]) * unit),
                       "batch_relative_seconds": float((pts - packets[start]["pts"]) * unit),
                       "source_png": png})
    return result


def validate_seek_context(episode, frames, packet_timing, decode, audit, preparation):
    """Require global native identity for every decoded, filtered and RGB row."""
    packets = _packet_census(episode, packet_timing)
    by_pts = {p["pts"]: i for i, p in enumerate(packets)}
    selected = [f["source_frame_index"] for f in frames]

    def indices(rows, label, local=False):
        result = [r["source_frame_index"] for r in rows]
        if (not result or result != sorted(set(result))
                or any(type(i) is not int or not 0 <= i < len(packets) for i in result)
                or any(r["native_pts_ticks"] != packets[i]["pts"] for r, i in zip(rows, result))
                or any(b != a + 1 for a, b in zip(result, result[1:]))
                or (local and [r["output_index"] for r in rows] != list(range(len(rows))))):
            raise ValueError(f"SAC {label} context census or native PTS differs")
        return result

    returned = indices(decode["returned_frames"], "primary")
    context = [i for i in returned if i not in selected]
    if (not set(selected) <= set(returned) or returned[-1] != selected[-1]
            or decode["decoded_outside_selected_frames"] != context or decode["selected_count"] != len(selected)
            or decode["stopped_after_last_selected_native_frame"] != selected[-1]
            or decode["all_source_frames_inherit_role"] != episode["role"] or decode["no_model_calls"] is not True):
        raise ValueError("SAC primary seek context is not complete and explicitly disclosed")
    submitted = decode["submitted_packets"]
    if (not submitted or any(type(p.get("pts")) is not int or p["pts"] not in by_pts for p in submitted)
            or len({p["pts"] for p in submitted}) != len(submitted)):
        raise ValueError("SAC submitted packets differ from full native source census")
    filtered = indices(audit["ffmpeg_filter_frames"], "secondary", local=True)
    rgb_count = audit["secondary_rgb_output_frames"]
    if (type(rgb_count) is not int or not 0 < rgb_count <= len(filtered)
            or not set(selected) <= set(filtered[:rgb_count]) or filtered[rgb_count - 1] != selected[-1]
            or audit["secondary_filter_frames_outside_selected"] !=
               [r for r in audit["ffmpeg_filter_frames"] if r["source_frame_index"] not in selected]):
        raise ValueError("SAC secondary selected/RGB/context census differs")
    counts = {"primary_returned": len(returned), "primary_submitted_packets": len(submitted),
              "saved_pngs": len(selected), "secondary_rgb_output_frames": rgb_count,
              "secondary_filter_reported_frames": len(filtered)}
    if preparation["decode_counts"] != counts:
        raise ValueError("SAC preparation decode accounting differs from actual context")
    return {"selected_native_source_frames": selected, "primary_returned_source_frames": returned,
            "primary_returned_frames_outside_selected": context,
            "primary_submitted_packet_source_indices": [by_pts[p["pts"]] for p in submitted],
            "secondary_rgb_source_frames": filtered[:rgb_count],
            "secondary_filter_source_frames": filtered,
            "all_context_inherits_fixed_game_role": episode["role"], "source_video_decoded_by_consumer": False}


def validate_preparation(root, folder, episode, frames):
    # These established fields/hashes/RGB checks are independent of packet versus
    # presentation duration. The additional SAC audit validates seek context.
    root, folder = Path(root).resolve(), Path(folder).resolve()
    evidence = _legacy_preparation(root, folder, episode, frames)
    preparation, audit, decode, packets = (read_json(folder / name) for name in
        ("preparation.json", "source_pixel_audit.json", "decode_audit.json", "source_packet_timing.json"))
    if preparation.get("decode_audit") != binding(root, folder / "decode_audit.json"):
        raise ValueError("SAC preparation does not bind its actual decode audit")
    evidence["source_decode_audit"] = binding(root, folder / "decode_audit.json")
    evidence["source_seek_context"] = validate_seek_context(episode, frames, packets, decode, audit, preparation)
    return evidence


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
    frames_path, timing_path, packet_path = (folder / name for name in
                                             ("source_frames.json", "source_timing.json", "source_packet_timing.json"))
    frames = join_native_frames(episode, read_json(_path(root, fixed_binding["path"])),
                               read_json(frames_path), read_json(timing_path), read_json(packet_path))
    preparation_evidence = validate_preparation(root, folder, episode, frames)
    rows, source = proposal["annotations"], episode["source"]
    if ([row["frame_index"] for row in rows] != [f["source_frame_index"] for f in frames]
            or any(type(row["frame_index"]) is not int for row in rows)):
        raise ValueError("SAC annotation census differs from fixed episode")
    bounds = SourceVideo.from_mapping({"path": source["path"], "sha256": source["sha256"],
        "width_px": source["width"], "height_px": source["height"],
        "fps": float(_fraction(config["review"]["native_playback_fps"], "nominal bounds rate")),
        "frame_count": source["decoded_frames"]})
    for position, (frame, row) in enumerate(zip(frames, rows)):
        if FrameAnnotation.from_mapping(row, position, bounds).annotation_status != "labeled":
            raise ValueError("SAC batch contains incomplete labels")
        png = frame["source_png"]
        _check_binding(root, png, "Source PNG")
        image = cv2.imread(str(_path(root, png["path"])))
        if image is None or image.shape != (source["height"], source["width"], 3):
            raise ValueError("SAC PNG native dimensions differ")
        if hashlib.sha256(cv2.cvtColor(image, cv2.COLOR_BGR2RGB).tobytes()).hexdigest() != png["rgb_sha256"]:
            raise ValueError("SAC PNG decoded RGB hash differs")
        frame["annotation"] = row
    return config, {"schema_version": "completion_sac_reference_review/v0.1",
        "batch_id": config["batch_id"], "episode_id": episode["episode_id"], "game_id": episode["game_id"],
        "role": episode["role"], "status": proposal["status"], "config": binding(root, config_path),
        "proposal": binding(root, proposal_path), "source_roles": roles_binding, "fixed_episode": episode,
        "fixed_frame_list": fixed_binding, "source_video": source_binding, "source_metadata": source,
        "source_frames": binding(root, frames_path), "source_timing": binding(root, timing_path),
        "source_packet_timing": binding(root, packet_path), **preparation_evidence,
        "range_inclusive": [episode["first_source_frame"], episode["last_source_frame"]],
        "annotation_origin": proposal["annotation_origin"], "annotator_id": proposal["annotator_id"],
        "human_acceptance": None, "training_eligible": False, "checkpoint_selection_eligible": False,
        "counts": dict(Counter(r["visibility"] for r in rows)),
        "eligible_centers": sum(r["localization_eligible"] for r in rows),
        "null_centers": sum(r["geometry"] is None for r in rows), "frames": frames,
        "timing_mode": "native_vfr", "duration_authority": DURATION_AUTHORITY,
        "native_duration_ticks_semantics": "alias of presentation_duration_ticks; raw packet duration is separate",
        "validation": {"all_source_png_hashes_checked": True, "all_source_png_rgb_hashes_checked": True,
            "independent_source_rgb_exact_matches_checked": len(frames),
            "native_source_frame_and_pts_joins_checked": len(frames),
            "actual_emitted_video_frames_checked": 0, "human_visual_acceptance": "pending"}}


def timing_schedule(frames, slow_fps=None):
    """Exact output timestamps, including the final frame's exposure interval."""
    if not frames:
        raise ValueError("An encoded timing schedule cannot be empty")
    if slow_fps is not None:
        rate = _fraction(slow_fps, "slow rate")
        # Using the source clock also makes the two transports easy to compare.
        unit = _fraction(frames[0]["native_time_base"], "native time base")
        duration = (1 / rate) / unit
        if duration.denominator != 1:
            raise ValueError("Slow cadence is not exactly representable on the source clock")
        rows = [(i * int(duration), int(duration)) for i in range(len(frames))]
    else:
        unit = _fraction(frames[0]["native_time_base"], "native time base")
        origin = frames[0]["native_pts_ticks"]
        rows = [(f["native_pts_ticks"] - origin, f["presentation_duration_ticks"]) for f in frames]
    if (rows[0][0] != 0 or any(type(p) is not int or type(d) is not int or d <= 0 for p, d in rows)
            or any(p + d != nxt[0] for (p, d), nxt in zip(rows, rows[1:]))):
        raise ValueError("Encoded timing schedule is not contiguous and positive")
    return unit, rows


def encode_review_video(path, canvases, schedule, time_base, primaries, transfer):
    """Encode one frame per supplied canvas, then mux explicit packet durations.

    Disabling B frames makes encoded packet PTS identity unambiguous. Codec
    frame-rate metadata never supplies native timestamps or the final duration.
    Color conversion is the same explicit RGB-to-BT.601 limited-range conversion
    used by the unchanged NBA reviewer; source primaries/transfer are preserved.
    """
    path, unit = Path(path), Fraction(time_base)
    if path.exists():
        raise FileExistsError(path)
    if primaries != "bt709" or transfer != "bt709":
        raise ValueError("This SAC encoder requires verified BT.709 primaries and transfer")
    if not schedule or schedule[0][0] != 0:
        raise ValueError("Review timing must start at zero")
    expected = {pts: duration for pts, duration in schedule}
    if (len(expected) != len(schedule) or any(type(p) is not int or type(d) is not int or d <= 0
                                            for p, d in schedule)
            or any(p + d != nxt[0] for (p, d), nxt in zip(schedule, schedule[1:]))):
        raise ValueError("Review timing must be unique, positive and contiguous")
    emitted = set()
    with path.open("xb") as handle, av.open(handle, "w", format="mp4",
            options={"movflags": "+faststart", "video_track_timescale": str(unit.denominator)}) as output:
        stream = output.add_stream("libx264", rate=60)
        stream.width, stream.height, stream.pix_fmt = 1280, 720, "yuv420p"
        stream.time_base = unit
        codec = stream.codec_context
        codec.time_base = unit
        codec.max_b_frames = 0
        codec.options = {"crf": "18", "preset": "medium", "bf": "0"}
        codec.colorspace, codec.color_range = 6, 1  # SMPTE170M, MPEG limited.
        codec.color_primaries, codec.color_trc = 1, 1  # Preserve source BT.709.
        graph = None

        def mux(packets):
            for packet in packets:
                if packet.time_base != unit or packet.pts not in expected or packet.pts in emitted:
                    raise ValueError("Encoder changed or duplicated a requested presentation timestamp")
                packet.duration = expected[packet.pts]
                emitted.add(packet.pts)
                output.mux(packet)

        count = 0
        for count, canvas in enumerate(canvases, 1):
            if count > len(schedule) or canvas.shape != (720, 1280, 3) or canvas.dtype != np.uint8:
                raise ValueError("Canvas count, native review dimensions or type differs")
            pts, duration = schedule[count - 1]
            frame = av.VideoFrame.from_ndarray(canvas, format="bgr24")
            frame.time_base, frame.pts, frame.duration = unit, pts, duration
            if graph is None:
                graph = av.filter.Graph()
                src = graph.add_buffer(template=frame)
                scale = graph.add("scale", "in_range=full:out_color_matrix=bt601:out_range=tv")
                props = graph.add("setparams", "range=limited:colorspace=smpte170m:color_primaries=bt709:color_trc=bt709")
                fmt, sink = graph.add("format", "pix_fmts=yuv420p"), graph.add("buffersink")
                src.link_to(scale); scale.link_to(props); props.link_to(fmt); fmt.link_to(sink)
                graph.configure()
            graph.push(frame)
            converted = graph.pull()
            converted.time_base, converted.pts, converted.duration = unit, pts, duration
            mux(stream.encode(converted))
        if count != len(schedule):
            raise ValueError("Canvas count differs from timing schedule")
        mux(stream.encode(None))
        if emitted != set(expected):
            raise ValueError("Encoder did not emit every requested timestamp")
    return {"encoder": "PyAV/libx264", "pyav_version": av.__version__, "time_base": str(unit),
            "codec_options": {"crf": "18", "preset": "medium", "bf": "0"},
            "packet_duration_authority": "explicit requested presentation interval after encoding",
            "filter": review_color_filter(primaries, transfer), "source_video_decoded": False}


def probe_encoded_video(path):
    command = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams",
               "-show_packets", "-show_frames", "-of", "json", str(path)]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def validate_encoded_timing(probe, schedule, time_base, primaries, transfer):
    """Read independent ffprobe output: verify each packet AND decoded frame."""
    unit = Fraction(time_base)
    streams = probe.get("streams", [])
    if len(streams) != 1:
        raise ValueError("Encoded review requires exactly one video stream")
    stream = streams[0]
    if ((stream.get("width"), stream.get("height")) != (1280, 720)
            or stream.get("color_space") != "smpte170m" or stream.get("color_range") != "tv"
            or stream.get("color_primaries") != primaries or stream.get("color_transfer") != transfer
            or Fraction(stream["time_base"]) != unit or int(stream["nb_frames"]) != len(schedule)
            or int(stream.get("start_pts", -1)) != 0
            or int(stream.get("duration_ts", -1)) != schedule[-1][0] + schedule[-1][1]):
        raise ValueError("Encoded color, dimensions, time base or total interval differs")
    # ffprobe combines its two requested censuses in packets_and_frames.
    combined = probe.get("packets_and_frames", [])
    packets = probe.get("packets", [r for r in combined if r.get("type") == "packet"])
    frames = probe.get("frames", [r for r in combined if r.get("type") == "frame"])
    if len(packets) != len(schedule) or len(frames) != len(schedule):
        raise ValueError("Encoded packet/frame census differs")
    checked = []
    for index, ((pts, duration), packet, frame) in enumerate(zip(schedule, packets, frames)):
        decoded_duration = frame.get("duration", frame.get("pkt_duration"))
        if (int(packet.get("pts", -1)) != pts or int(packet.get("duration", -1)) != duration
                or int(frame.get("pts", -1)) != pts or int(frame.get("best_effort_timestamp", -1)) != pts
                or decoded_duration is None or int(decoded_duration) != duration):
            raise ValueError(f"Encoded native PTS/duration differs at output frame {index}")
        checked.append({"output_index": index, "encoded_pts_ticks": pts,
                        "encoded_duration_ticks": duration, "encoded_time_base": str(unit),
                        "packet_and_decoded_frame_exact": True})
    return checked


def validate_video_timing(root, video, frames, slow_fps=10, native=True):
    """Validate bound emitted evidence for acceptance/finalization consumers."""
    root = Path(root).resolve()
    for key, entry in (("video", video), ("encoded probe", video["encoded_probe"]),
                       ("encoded timing", video["encoded_timing"])):
        _check_binding(root, entry, key)
    unit, schedule = timing_schedule(frames, None if native else slow_fps)
    probe = read_json(_path(root, video["encoded_probe"]["path"]))
    checked = validate_encoded_timing(probe, schedule, unit,
                                     video["color_primaries"], video["color_transfer"])
    timing = read_json(_path(root, video["encoded_timing"]["path"]))
    if (timing.get("schema_version") != "completion_sac_encoded_timing/v0.1"
            or timing.get("status") != "passed" or timing.get("video") != binding(root, _path(root, video["path"]))
            or timing.get("encoded_probe") != video["encoded_probe"] or timing.get("rows") != checked
            or timing.get("source_frame_indices") != [f["source_frame_index"] for f in frames]
            or video.get("time_base") != str(unit) or video.get("frame_count") != len(frames)
            or video.get("timing_mode") != ("native_vfr" if native else "cfr")
            or video.get("fps") != (None if native else float(_fraction(slow_fps, "slow rate")))
            or not _same_seconds(video.get("duration_seconds"), (schedule[-1][0] + schedule[-1][1]) * unit)):
        raise ValueError("Bound video timing evidence differs from current native frame schedule")
    return checked


def render(root, config_path, proposal_path, destination):
    root = Path(root).resolve()
    config, manifest = validate_batch(root, config_path, proposal_path)
    frames, color = manifest["frames"], manifest["source_color_metadata"]
    primaries, transfer = color.get("color_primaries"), color.get("color_transfer")
    if primaries != "bt709" or transfer != "bt709":
        raise ValueError("SAC review requires verified source BT.709 primaries/transfer")
    destination = _path(root, destination)
    destination.mkdir(parents=True, exist_ok=False)
    context = (len(frames), manifest["episode_id"], manifest["role"], frames[-1]["source_frame_index"],
               manifest["source_metadata"]["decoded_frames"] - 1)
    manifest["review_color_conversion"] = {
        "source_pngs_changed": False, "input": "full-range native RGB pixels carried as bgr24",
        "ffmpeg_filter": review_color_filter(primaries, transfer), "output_color_space": "smpte170m",
        "output_color_range": "tv", "preserved_color_primaries": primaries,
        "preserved_color_transfer": transfer,
        "verification": "Every encoded frame reconstructed by OpenCV; CLI ffprobe checks every packet/frame PTS, duration and emitted tags."}
    videos = []
    for name, native in (("review_native.mp4", True), ("review_slow.mp4", False)):
        slow = config["review"]["slow_playback_fps"]
        unit, schedule = timing_schedule(frames, None if native else slow)
        path = destination / name
        encoding = encode_review_video(path, (_canvas(root, item, context) for item in frames),
                                       schedule, unit, primaries, transfer)
        probe = probe_encoded_video(path)
        probe_path = destination / name.replace(".mp4", "_encoded_probe.json")
        write_new(probe_path, probe)
        checked = validate_encoded_timing(probe, schedule, unit, primaries, transfer)
        timing_path = destination / name.replace(".mp4", "_encoded_timing.json")
        write_new(timing_path, {"schema_version": "completion_sac_encoded_timing/v0.1", "status": "passed",
            "video": binding(root, path), "encoded_probe": binding(root, probe_path),
            "source_frame_indices": [f["source_frame_index"] for f in frames], "rows": checked})
        capture = cv2.VideoCapture(str(path))
        errors, marker_errors, emitted = [], [], []
        try:
            for item, timed in zip(frames, checked):
                ok, actual = capture.read()
                if not ok or actual.shape != (720, 1280, 3):
                    raise ValueError("SAC encoded frame census/dimensions differ")
                expected = _canvas(root, item, context)
                error = float(np.abs(actual.astype(np.int16) - expected.astype(np.int16)).mean())
                errors.append(error)
                if error > 8:
                    raise ValueError("Encoded SAC frame differs from source/label record")
                marker_error = None
                if item["annotation"]["geometry"] is not None:
                    target, observed = expected[40:340, 970:1270], actual[40:340, 970:1270]
                    mask = np.all(target == (0, 255, 255), axis=2)
                    if int(mask.sum()) < 20:
                        raise ValueError("Expected SAC label marker is absent")
                    marker_error = float(np.abs(observed.astype(np.int16)[mask] - target.astype(np.int16)[mask]).mean())
                    marker_errors.append(marker_error)
                    if marker_error > 65:
                        raise ValueError("Encoded SAC label marker differs")
                emitted.append({"source_frame_index": item["source_frame_index"], **timed,
                                "mean_absolute_pixel_error": error, "label_marker_pixel_error": marker_error})
            if capture.read()[0]:
                raise ValueError("Unexpected extra SAC encoded frame")
            final_path = destination / name.replace(".mp4", "_actual_final.png")
            if not cv2.imwrite(str(final_path), actual):
                raise ValueError("Could not save actual SAC encoded final")
        finally:
            capture.release()
        video = {**binding(root, path), "frame_count": len(frames), "fps": None if native else float(slow),
            "timing_mode": "native_vfr" if native else "cfr", "time_base": str(unit),
            "duration_seconds": float((schedule[-1][0] + schedule[-1][1]) * unit),
            "color_primaries": primaries, "color_transfer": transfer,
            "actual_final": binding(root, final_path), "encoded_probe": binding(root, probe_path),
            "encoded_timing": binding(root, timing_path), "encoding": encoding,
            "all_frame_mean_absolute_pixel_errors": errors,
            "all_frame_label_marker_pixel_errors": marker_errors, "emitted_frame_checks": emitted}
        validate_video_timing(root, video, frames, slow, native)
        videos.append(video)
    manifest["videos"] = videos
    manifest["validation"]["actual_emitted_video_frames_checked"] = 2 * len(frames)
    manifest["validation"]["actual_emitted_packet_and_frame_timestamps_checked"] = 2 * len(frames)
    write_new(destination / "manifest.json", manifest)
    return manifest
