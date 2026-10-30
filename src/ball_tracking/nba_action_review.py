"""Stream source-paced NBA observation reviews with independently checked transport.

No annotations are manufactured or scored here. Native frame timestamps remain
integer 90 kHz ticks; the actual final frame receives a declared one-second hold.
"""
from __future__ import annotations

import hashlib
import html
import io
import json
import math
import os
from pathlib import Path
import subprocess
import time
import uuid
from fractions import Fraction
from urllib.parse import quote

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from . import nba_annotations as nba
from .prepare_nba_assisted_review import font

TIME_BASE = Fraction(1, 90000)
WIDTH, HEIGHT, SOURCE_TOP, SOURCE_HEIGHT = 1280, 816, 64, 720
KEY_TOP, KEY_CELL = 808, 8
HOLD_TICKS = 90000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def binding(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    require(path.is_relative_to(root), "Review artifact escapes repository")
    return {"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def bound(root, record):
    path = (Path(root) / record["path"]).resolve()
    require(binding(root, path) == record, "Review artifact binding mismatch")
    return path


def write_json(path, value):
    path = Path(path)
    require(not path.exists(), "Review evidence already exists")
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".partial")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    require(not path.exists(), "Concurrent review evidence creation")
    temporary.replace(path)


def validate_inputs(manifest, observations):
    require("annotations" not in manifest, "Action review expects an unlabeled input manifest")
    require(manifest["time_base"] == "1/90000", "Unsupported source time base")
    require(observations["candidate_id"] == manifest["candidate_id"], "Candidate join mismatch")
    require(observations["game_id"] == manifest["game_id"], "Game join mismatch")
    frames, rows = manifest["frames"], observations["frames"]
    require(bool(frames) and len(frames) == len(rows), "Incomplete action observation inventory")
    indices = [frame["source_frame_index"] for frame in frames]
    ticks = [frame["source_pts_ticks"] for frame in frames]
    require(all(type(i) is int and 0 <= i < 2**32 for i in indices), "Invalid source frame index")
    require(indices == list(range(indices[0], indices[0] + len(indices))), "Nonconsecutive source frames")
    require(all(type(t) is int and 0 <= t < 2**48 for t in ticks), "Invalid native PTS")
    end = manifest["source_end_exclusive_pts_ticks"]
    require(type(end) is int and all(b-a in (1440, 1530) for a, b in zip(ticks, ticks[1:] + [end])),
            "Action review cadence or final source duration changed")
    source = manifest["source_video"]
    require(all(type(source[key]) is int and source[key] > 0 for key in ("width_px", "height_px")),
            "Invalid source dimensions")
    for frame, row in zip(frames, rows):
        require(all(frame[key] == row[key] for key in ("source_frame_index", "source_pts_ticks")),
                "Observation frame/PTS join mismatch")
        require(row.get("time_base", "1/90000") == "1/90000", "Observation time base changed")
        require(row.get("source_png", frame["png"]) == frame["png"], "Observation source PNG changed")
        require(row["state"] in {"observed", "missing", "withheld"}, "Unknown observation state")
        point = row["center_xy_px"]
        require((point is not None) == (row["state"] == "observed"), "Observation point/state mismatch")
        if point is not None:
            require(len(point) == 2 and all(math.isfinite(float(x)) for x in point), "Invalid model point")
            require(0 <= point[0] < source["width_px"] and 0 <= point[1] < source["height_px"],
                    "Model point outside original source")
        require(type(row["temporal_contributions"]) is int and 0 <= row["temporal_contributions"] <= 3,
                "Invalid temporal contribution count")
        require(isinstance(row["candidates"], list), "Missing candidate inventory")
        for candidate in row["candidates"]:
            require(all(math.isfinite(float(candidate[key])) for key in ("center_x", "center_y")),
                    "Invalid candidate point")
            require(0 <= candidate["center_x"] < source["width_px"]
                    and 0 <= candidate["center_y"] < source["height_px"],
                    "Candidate point outside original source")
    return [b-a for a, b in zip(ticks, ticks[1:] + [end])]


def key_bits(review_index, frame):
    """A small visible binary frame key makes lossy video-frame joins testable."""
    return f"{review_index:032b}{frame['source_frame_index']:032b}{frame['source_pts_ticks']:048b}"


def render_overlay(image, frame, observation, review_index, candidate_id):
    canvas = Image.new("RGB", (WIDTH, HEIGHT), (15, 20, 29))
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 3), f"{candidate_id} | Frozen WASB observations | review pending",
              fill="white", font=font(22))
    draw.text((12, 33), f"Source frame {frame['source_frame_index']} | "
              f"PTS {frame['source_pts_ticks']} / 90000 | "
              f"{frame['source_pts_ticks']/90000:.6f} s | {observation['state'].upper()} | "
              f"{observation['temporal_contributions']} contributions", fill="#ffd380", font=font(17))
    view = ImageOps.contain(image, (WIDTH, SOURCE_HEIGHT), Image.Resampling.LANCZOS)
    left, top = (WIDTH-view.width)//2, SOURCE_TOP+(SOURCE_HEIGHT-view.height)//2
    canvas.paste(view, (left, top))
    def location(x, y):
        return left+x*view.width/image.width, top+y*view.height/image.height
    for candidate in observation["candidates"]:
        x, y = location(candidate["center_x"], candidate["center_y"])
        draw.ellipse((x-4, y-4, x+4, y+4), outline="#ffd380", width=1)
    point = observation["center_xy_px"]
    if point is not None:
        x, y = location(*point)
        draw.ellipse((x-7, y-7, x+7, y+7), outline="#ff45c5", width=2)
        draw.line((x-11, y, x+11, y), fill="#ff45c5", width=1)
        draw.line((x, y-11, x, y+11), fill="#ff45c5", width=1)
    reason = observation.get("withheld_reason")
    footer = "Pink: selected point | Gold: candidate | Missing means unknown | Native source pacing"
    if reason:
        footer = "WITHHELD: " + str(reason)[:120]
    draw.text((12, 786), footer, fill="white", font=font(16))
    for index, bit in enumerate(key_bits(review_index, frame)):
        x = index*KEY_CELL
        draw.rectangle((x, KEY_TOP, x+KEY_CELL-1, HEIGHT-1), fill="white" if bit == "1" else "black")
    return canvas, {"source_view_rect": [left, top, view.width, view.height],
                    "point_source_pixels": point}


def source_overlay(root, manifest, frame, observation, index):
    raw = nba.read_verified_png(frame, manifest["source_video"], Path(root))
    with Image.open(io.BytesIO(raw)) as source:
        return render_overlay(source.convert("RGB"), frame, observation, index, manifest["candidate_id"])


def verify_video(root, manifest, observations, records, video, ffmpeg, folder):
    """External ffprobe verifies native PTS; external FFmpeg decodes every frame."""
    ffprobe = Path(ffmpeg).with_name("ffprobe.exe" if Path(ffmpeg).suffix.lower() == ".exe" else "ffprobe")
    probe_command = [str(ffprobe), "-v", "error", "-select_streams", "v:0", "-show_entries",
                     "stream=time_base,duration_ts,nb_frames,width,height:frame=best_effort_timestamp,duration",
                     "-of", "json", str(video)]
    probe = subprocess.run(probe_command, capture_output=True, check=False, timeout=180)
    (folder/"ffprobe.stderr.txt").write_bytes(probe.stderr)
    require(probe.returncode == 0, "Review probe failed")
    metadata = json.loads(probe.stdout)
    write_json(folder/"ffprobe.json", metadata)
    require(len(metadata["streams"]) == 1, "Unexpected review stream count")
    stream = metadata["streams"][0]
    require(stream["time_base"] == "1/90000" and (stream["width"], stream["height"]) == (WIDTH, HEIGHT),
            "Encoded dimensions or time base changed")
    encoded_frames = metadata["frames"]
    require(len(encoded_frames) == len(records) == int(stream["nb_frames"]), "Encoded frame count mismatch")
    for record, encoded in zip(records, encoded_frames):
        require(int(encoded["best_effort_timestamp"]) == record["review_pts_ticks"], "Encoded native PTS mismatch")
        require(int(encoded["duration"]) == record["encoded_duration_ticks"], "Encoded frame duration mismatch")
    expected_duration = records[-1]["review_pts_ticks"] + records[-1]["encoded_duration_ticks"]
    require(int(stream["duration_ts"]) == expected_duration, "Final hold or timeline duration mismatch")
    command = [str(ffmpeg), "-hide_banner", "-nostdin", "-loglevel", "error", "-xerror", "-threads", "2",
               "-i", str(video), "-map", "0:v:0", "-an", "-fps_mode", "passthrough", "-pix_fmt", "rgb24",
               "-f", "rawvideo", "pipe:1"]
    errors = []
    with (folder/"decode.stderr.txt").open("xb") as stderr:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=stderr)
        try:
            for index, (frame, observation) in enumerate(zip(manifest["frames"], observations["frames"])):
                raw = bytearray()
                while len(raw) < WIDTH*HEIGHT*3:
                    chunk = process.stdout.read(WIDTH*HEIGHT*3-len(raw))
                    require(bool(chunk), "Review decode ended before actual final frame")
                    raw.extend(chunk)
                decoded = np.frombuffer(raw, dtype=np.uint8).reshape(HEIGHT, WIDTH, 3)
                bits = "".join("1" if float(decoded[KEY_TOP+4, i*KEY_CELL+4].mean()) > 127 else "0"
                               for i in range(112))
                require(bits == key_bits(index, frame), "Decoded frame key differs from source mapping")
                expected, _ = source_overlay(root, manifest, frame, observation, index)
                error = float(np.abs(decoded.astype(np.int16)-np.asarray(expected).astype(np.int16)).mean())
                require(error < 8.0, "Decoded overlay differs materially from expected source frame")
                errors.append(error)
                if index == len(records)-1:
                    Image.fromarray(decoded).save(folder/"final_frame.png")
            require(process.stdout.read(1) == b"", "Review contains unexpected decoded frames")
            require(process.wait(timeout=60) == 0, "Full review decode failed")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
            process.stdout.close()
    result = {"status": "passed", "decoded_frames": len(errors), "native_pts_all_frames_verified": True,
              "decoded_source_frame_keys_all_verified": True, "overlay_mae_max": max(errors),
              "overlay_mae_mean": sum(errors)/len(errors), "actual_final_frame_mae": errors[-1],
              "actual_final_source_frame_index": manifest["frames"][-1]["source_frame_index"],
              "timeline_duration_ticks": expected_duration, "time_base": "1/90000",
              "additional_final_hold_ticks": HOLD_TICKS, "probe_command": probe_command,
              "full_decode_command": command, "final_frame": binding(root, folder/"final_frame.png")}
    write_json(folder/"verification.json", result)
    return result


def render_action(root, manifest, observations, ffmpeg, output):
    """Return bound complete review artifacts; preserve failed attempts and resume."""
    import av
    root, output = Path(root).resolve(), Path(output).resolve()
    require(output.is_relative_to(root), "Review output escapes repository")
    durations = validate_inputs(manifest, observations)
    identity = {"manifest_sha256": canonical(manifest), "observations_sha256": canonical(observations),
                "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "source_reader_sha256": hashlib.sha256(Path(nba.__file__).read_bytes()).hexdigest(),
                "font_helper_sha256": hashlib.sha256(Path(font.__code__.co_filename).read_bytes()).hexdigest(),
                "final_hold_ticks": HOLD_TICKS}
    parent = output/"review_attempts"
    if parent.exists():
        for path in sorted(parent.glob("*/completion.json")):
            completed = json.loads(path.read_text(encoding="utf-8"))
            if completed["identity"] == identity:
                for item in completed["artifacts"].values():
                    bound(root, item)
                return {**completed["artifacts"], "completion": binding(root, path), "reused": True}
    folder = parent/uuid.uuid4().hex
    folder.mkdir(parents=True)
    write_json(folder/"started.json", {"status": "started", "identity": identity})
    began = time.monotonic()
    try:
        video = folder/"review.mp4"
        frames, rows = manifest["frames"], observations["frames"]
        relative_pts = [f["source_pts_ticks"]-frames[0]["source_pts_ticks"] for f in frames]
        encoded_durations = durations.copy()
        encoded_durations[-1] += HOLD_TICKS
        duration_by_pts = dict(zip(relative_pts, encoded_durations))
        records = []
        with av.open(str(video), "w", options={"movflags": "+faststart"}) as container:
            stream = container.add_stream("libx264", rate=Fraction(60000, 1001),
                                          options={"crf": "18", "preset": "fast", "bf": "0"})
            stream.width, stream.height, stream.pix_fmt = WIDTH, HEIGHT, "yuv420p"
            stream.time_base = stream.codec_context.time_base = TIME_BASE
            stream.codec_context.thread_count = 2
            def mux(packets):
                for packet in packets:
                    require(packet.time_base == TIME_BASE and packet.pts in duration_by_pts,
                            "Encoder changed native presentation timestamps")
                    packet.duration = duration_by_pts[packet.pts]
                    container.mux(packet)
            for index, (frame, observation) in enumerate(zip(frames, rows)):
                image, geometry = source_overlay(root, manifest, frame, observation, index)
                encoded = av.VideoFrame.from_image(image)
                encoded.pts, encoded.time_base = relative_pts[index], TIME_BASE
                mux(stream.encode(encoded))
                records.append({"review_index": index, "source_frame_index": frame["source_frame_index"],
                    "source_pts_ticks": frame["source_pts_ticks"], "review_pts_ticks": relative_pts[index],
                    "source_duration_ticks": durations[index], "encoded_duration_ticks": encoded_durations[index],
                    "source_png": frame["png"], "state": observation["state"], **geometry})
            mux(stream.encode())
        review_manifest = {"schema_version": "nba_action_review/v0.1", "candidate_id": manifest["candidate_id"],
            "game_id": manifest["game_id"], "model_output_human_review": "pending", "identity": identity,
            "time_base": "1/90000", "native_source_pts_pacing": True, "frames": records,
            "final_hold_ticks": HOLD_TICKS, "final_hold_method": "extend_actual_final_frame_duration",
            "frame_key_layout": "32bit review index + 32bit source frame index + 48bit source PTS; visible bottom strip",
            "encoder": {"library": "PyAV", "version": av.__version__, "codec": "libx264", "crf": 18,
                        "preset": "fast", "b_frames": 0, "threads": 2}, "annotations_created": False,
            "accuracy_scoring": False, "retained_composite_source_pngs": 0}
        write_json(folder/"review_manifest.json", review_manifest)
        verify_video(root, manifest, observations, records, video, ffmpeg, folder)
        artifacts = {key: binding(root, folder/name) for key, name in (
            ("review_video", "review.mp4"), ("review_manifest", "review_manifest.json"),
            ("verification", "verification.json"), ("final_frame", "final_frame.png"),
            ("ffprobe", "ffprobe.json"), ("probe_log", "ffprobe.stderr.txt"), ("decode_log", "decode.stderr.txt"))}
        write_json(folder/"completion.json", {"status": "complete", "identity": identity,
                   "elapsed_seconds": time.monotonic()-began, "artifacts": artifacts,
                   "model_output_human_review": "pending"})
        return {**artifacts, "completion": binding(root, folder/"completion.json"), "reused": False}
    except Exception as error:
        write_json(folder/"failed.json", {"status": "failed_preserved", "error_type": type(error).__name__,
                   "error": str(error), "elapsed_seconds": time.monotonic()-began})
        raise


def build_review_page(root, packages, output):
    """Make a local page for the complete timelines; playback speed changes only UI."""
    root, output = Path(root).resolve(), Path(output).resolve()
    require(output.is_relative_to(root), "Review page escapes repository")
    cards = []
    for package in packages:
        video = bound(root, package["review"]["review_video"])
        relative = quote(Path(os.path.relpath(video, output)).as_posix(), safe="/.")
        title = html.escape(package["candidate_id"])
        cards.append(f'<section><h2>{title}</h2><video controls preload="metadata" src="{relative}"></video>'
                     '<p>Playback speed: <select aria-label="Playback speed">'
                     '<option value="1">1× native</option><option value="0.5">0.5×</option>'
                     '<option value="0.25">0.25×</option><option value="0.1">0.1×</option></select></p></section>')
    document = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">' \
        '<title>NBA action observation review</title><style>body{margin:24px auto;padding:0 20px;max-width:1280px;' \
        'font:17px system-ui;background:#0f141d;color:#edf2f7}video{width:100%;background:black}section{margin:32px 0}' \
        'select{font:inherit;padding:5px}p{line-height:1.5}</style><h1>NBA action observation review</h1>' \
        '<p>Watch both complete timelines, including their final frames. Pink marks the selected model point; ' \
        'gold marks other candidates. Missing and withheld frames remain explicit. These observations have no new ' \
        'reference labels or accuracy score. Human review is pending.</p><p>Native source timing is preserved. ' \
        'Each actual final frame has one additional second of display. Slower playback changes only presentation speed.</p>' \
        + ''.join(cards) + '<script>document.querySelectorAll("section").forEach(s=>s.querySelector("select")' \
        '.addEventListener("change",e=>{s.querySelector("video").playbackRate=Number(e.target.value)}));</script></html>\n'
    output.mkdir(parents=True, exist_ok=True)
    path = output/"review.html"
    if path.exists():
        require(path.read_text(encoding="utf-8") == document, "Existing review page differs; preserve it")
    else:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(document)
    return binding(root, path)
