"""Stream native-paced, source-bound comparisons for continuous gap decisions.

This consumer never selects candidates or reads labels. NFHS protected positions
have no decoder request, source pixels, player display, or ball observation.
"""
from __future__ import annotations

from fractions import Fraction
import html
import io
import json
import math
import os
from pathlib import Path
import subprocess
import time
import uuid
from urllib.parse import quote

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from . import nba_action_review as review
from . import nba_annotations as nba
from . import nba_wasb_diagnostic as d
from . import wasb_development_observation as observation
from . import wasb_experiment as wasb
from .annotations import SourceVideo, verify_source_video_contract

SCHEMA = "nba_temporal_gap_continuous_review/v0.1"
WIDTH, HEIGHT = 1280, 816
HOLD_TICKS = 90000
TITLES = ("SAME-CONTEXT BASELINE", "UNCHANGED GAP RULE")


def validate_nfhs_timing(root, source):
    """Independently join saved container packet times to every playback slot."""
    timing = d.read_json(wasb.bound_path(root, source["native_timestamps"]))
    metadata = source["source_video"]
    d.require(timing["schema_version"] == "nfhs_container_native_timestamps/v0.1"
              and timing["status"] == "verified" and timing["candidate_id"] == source["candidate_id"]
              and timing["source_video"] == metadata and timing["time_base"] == "1/90000"
              and timing["time_origin"] == source["time_origin"] == "clip_first_frame", "NFHS timing authority differs")
    actual = timing["actual_source_binding"]
    d.require(all(actual[key] == metadata[key] for key in ("path", "sha256")), "Timing source binding differs")
    wasb.bound_path(root, actual)
    probe = d.read_json(wasb.bound_path(root, timing["packet_probe"]))
    d.require(len(probe["streams"]) == 1, "Unexpected native source packet streams")
    stream = probe["streams"][0]
    d.require((stream["width"], stream["height"]) == (metadata["width_px"], metadata["height_px"])
              and int(stream["nb_frames"]) == metadata["frame_count"]
              and stream["time_base"] == timing["original_time_base"], "Native packet source metadata differs")
    scale = Fraction(stream["time_base"])*90000
    packets = sorted((int(p["pts"])*scale, int(p["duration"])*scale) for p in probe["packets"])
    origin = timing["container_time_origin_ticks"]
    expected = [{"source_frame_index": i, "source_pts_ticks": i*3600,
                 "container_pts_ticks": origin+i*3600, "duration_ticks": 3600} for i in range(metadata["frame_count"])]
    d.require(timing["frames"] == expected and packets == [(f["container_pts_ticks"], 3600) for f in expected]
              and timing["source_end_exclusive_pts_ticks"] == metadata["frame_count"]*3600
              and timing["container_end_exclusive_pts_ticks"] == origin+metadata["frame_count"]*3600,
              "NFHS native packet timing differs from playback mapping")
    d.require(all(row["source_pts_ticks"] == frame["source_pts_ticks"]
                  and row["container_pts_ticks"] == frame["container_pts_ticks"]
                  and (row["decision"] == "withheld" or row["source_frame"] == frame)
                  for row, frame in zip(source["frames"], expected, strict=True)), "NFHS emitted native frame mapping differs")
    return timing


def validate_source(root, source):
    """Validate the producer's emitted timeline before opening source images."""
    rows, metadata, kind = source["frames"], source["source_video"], source["kind"]
    d.require(kind in ("nba", "nfhs") and rows, "Unknown or empty continuous source")
    indices = [r["source_frame_index"] for r in rows]
    ticks = [r["source_pts_ticks"] for r in rows]
    d.require(all(type(i) is int and 0 <= i < 2**32 for i in indices)
              and indices == list(range(indices[0], indices[0]+len(rows))), "Incomplete source frame timeline")
    d.require(all(type(t) is int and 0 <= t < 2**48 for t in ticks), "Invalid native source timestamps")
    d.require(all(type(metadata[k]) is int and metadata[k] > 0 for k in ("width_px", "height_px")),
              "Invalid source dimensions")
    if kind == "nba":
        manifest = d.read_json(wasb.bound_path(root, source["source_manifest"]))
        d.require(manifest["candidate_id"] == source["candidate_id"]
                  and manifest["source_video"] == metadata and manifest["time_base"] == "1/90000"
                  and manifest["frames"] == [r["source_frame"] for r in rows], "NBA source manifest join differs")
        end = manifest["source_end_exclusive_pts_ticks"]
        d.require(source["source_end_exclusive_pts_ticks"] == end and not source["protected_ranges"],
                  "NBA source boundary differs")
        durations = [b-a for a, b in zip(ticks, ticks[1:]+[end])]
        d.require(all(value in (1440, 1530) for value in durations), "NBA native cadence differs")
    else:
        possession = source["possession"]
        d.require(possession["source_video"] == metadata
                  and possession["possession_id"] == source["candidate_id"]
                  and source["protected_ranges"] == possession["protected_ranges"], "NFHS source/config join differs")
        d.require(metadata["fps"] == 25 and indices == list(range(metadata["frame_count"]))
                  and ticks == [i*3600 for i in indices], "NFHS native timeline must preserve every 25fps slot")
        d.require(possession["visible_segments"] == observation.complement_ranges(len(rows), source["protected_ranges"]),
                  "NFHS permitted segments differ from protected complement")
        for segment in possession["visible_segments"]:
            observation.guard_segment(possession, segment)
        validate_nfhs_timing(root, source)
        durations = [3600]*len(rows)
    for row in rows:
        index = row["source_frame_index"]
        protected = any(a <= index <= b for a, b in source["protected_ranges"])
        baseline, selected = row["baseline_center_xy_px"], row["selected_center_xy_px"]
        d.require((row["decision"] == "withheld") == protected, "Protected decision differs")
        if protected:
            d.require(baseline is None and selected is None and row["segment_id"] is None,
                      "Protected frame carries a prediction or segment")
        else:
            d.require(row["segment_id"] is not None, "Visible frame has no permitted segment")
            d.require(row["candidate_id"] == source["candidate_id"]
                      and row["original_observation"]["center_xy_px"] == baseline, "Baseline producer join differs")
            d.require(row["decision"] in ("preserved_original", "abstained", "filled_saved_candidate"),
                      "Unknown temporal decision")
            expected = "preserved_original" if baseline is not None else "abstained" if selected is None else "filled_saved_candidate"
            d.require(row["decision"] == expected and (baseline is None or baseline == selected),
                      "Original selection changed or decision disagrees")
            component = row["selected_component"]
            if selected is None:
                d.require(component is None and row["selected_pool_record_index"] is None
                          and row["selected_native_score"] is None and row["selected_provenance_id"] is None,
                          "Missing frame carries a selected component")
            else:
                pool, selected_index = row["candidate_pool"]["records"], row["selected_pool_record_index"]
                d.require(type(selected_index) is int and 0 <= selected_index < len(pool), "Selected pool record missing")
                record = pool[selected_index]
                d.require(record["component"] == component and record["provenance_id"] == row["selected_provenance_id"]
                          and [component["center_x"], component["center_y"]] == selected
                          and component["native_score"] == row["selected_native_score"], "Selected component/provenance join differs")
        for point in (baseline, selected):
            d.require(point is None or (isinstance(point, list) and len(point) == 2
                      and all(type(v) in (int, float) and math.isfinite(v) for v in point)), "Invalid displayed center")
        if kind == "nba":
            d.require(all(row[k] == row["source_frame"][k] for k in ("source_frame_index", "source_pts_ticks")),
                      "NBA native frame mapping differs")
    segments = source["segments"]
    permitted = [r for r in rows if r["decision"] != "withheld"]
    flattened = [r for segment in segments for r in segment["frames"]]
    d.require(flattened == permitted, "Segment and playback decision rows differ")
    expected_ranges = ([indices[0], indices[-1]],) if kind == "nba" else source["possession"]["visible_segments"]
    d.require([s["range_inclusive"] for s in segments] == list(expected_ranges), "Segment boundaries differ")
    for segment in segments:
        a, b = segment["range_inclusive"]
        d.require([r["source_frame_index"] for r in segment["frames"]] == list(range(a, b+1))
                  and all(r["segment_id"] == segment["segment_id"] for r in segment["frames"]),
                  "Segment identity or frame coverage differs")
    return [{"review_index": i, "source_frame_index": row["source_frame_index"],
             "source_pts_ticks": row["source_pts_ticks"], "review_pts_ticks": row["source_pts_ticks"]-ticks[0],
             "source_duration_ticks": duration, "duration_ticks": duration+(HOLD_TICKS if i == len(rows)-1 else 0),
             "segment_id": row["segment_id"], "decision": row["decision"],
             "container_pts_ticks": row.get("container_pts_ticks"),
             "source_png": row["source_frame"]["png"] if kind == "nba" else None,
             "source_pixels_withheld": row["decision"] == "withheld"}
            for i, (row, duration) in enumerate(zip(rows, durations, strict=True))]


def pair_bits(row):
    """A second visible key binds panel order and both displayed decisions."""
    identity = [TITLES, row["baseline_center_xy_px"], row["selected_center_xy_px"], row["decision"]]
    return f"{int(wasb.canonical(identity)[:8], 16):032b}"


def render_frame(image, source, row, index, players=()):
    """One shared source view and zoom, with independently marked selections."""
    withheld = row["decision"] == "withheld"
    d.require((image is None) == withheld, "Protected renderer must receive no source pixels")
    d.require(not withheld or not players, "Protected renderer must receive no player display")
    canvas = Image.new("RGB", (WIDTH, HEIGHT), "black" if withheld else (15, 20, 29))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 96, WIDTH-1, 775), fill="black")
    label = (f"{source['candidate_id']} | source frame {row['source_frame_index']} | "
             f"{'clip-relative PTS' if source['kind']=='nfhs' else 'native PTS'} {row['source_pts_ticks']} / 90000"
             f" | {'25fps' if source['kind']=='nfhs' else 'native timing'}")
    d.require(draw.textlength(label, font=review.font(17)) < WIDTH-24, "Review source header clipped")
    draw.text((12, 4), label, fill="white", font=review.font(17))
    draw.text((12, 28), "Protected source pixels omitted" if withheld else
              "Same source / same context | no reference labels displayed | human trajectory review pending",
              fill="#ffd380", font=review.font(15))
    baseline, selected = row["baseline_center_xy_px"], row["selected_center_xy_px"]
    if not withheld:
        d.require(image.size == (source["source_video"]["width_px"], source["source_video"]["height_px"]),
                  "Source image dimensions differ")
        anchor = baseline or selected or [image.width/2, image.height/2]
        cw, ch = min(320, image.width), min(180, image.height)
        cx, cy = max(0, min(image.width-cw, round(anchor[0]-cw/2))), max(0, min(image.height-ch, round(anchor[1]-ch/2)))
        crop = image.crop((cx, cy, cx+cw, cy+ch))
        view = ImageOps.contain(image, (636, 348), Image.Resampling.LANCZOS)
        zoom = ImageOps.contain(crop, (636, 260), Image.Resampling.LANCZOS)
    for panel, center in enumerate((baseline, selected)):
        left = panel*640
        state = "WITHHELD" if withheld else "GAP FILL" if panel and row["decision"] == "filled_saved_candidate" else "MISSING" if center is None else "OBSERVED"
        if center is not None and not (0 <= center[0] < image.width and 0 <= center[1] < image.height):
            state += " / OUTSIDE IMAGE"
        draw.text((left+12, 48), TITLES[panel], fill="#ffd380", font=review.font(20))
        draw.text((left+12, 70), state, fill="#ffd380", font=review.font(12))
        if withheld:
            continue
        vx, vy = left+(640-view.width)//2, 96+(348-view.height)//2
        zx, zy = left+(640-zoom.width)//2, 480+(260-zoom.height)//2
        canvas.paste(view, (vx, vy)); canvas.paste(zoom, (zx, zy))
        def location(point, rect, origin, dimensions):
            x, y = point
            if not (origin[0] <= x < origin[0]+dimensions[0] and origin[1] <= y < origin[1]+dimensions[1]):
                return None
            return rect[0]+(x-origin[0])*rect[2]/dimensions[0], rect[1]+(y-origin[1])*rect[3]/dimensions[1]
        for rect, origin, dimensions in (((vx, vy, view.width, view.height), (0, 0), image.size),
                                          ((zx, zy, zoom.width, zoom.height), (cx, cy), (cw, ch))):
            for player in players:
                xy = location((float(player["floor_x"]), float(player["floor_y"])), rect, origin, dimensions)
                if xy:
                    x, y = xy
                    draw.ellipse((x-2, y-2, x+2, y+2), fill="white")
                    draw.text((x+4, y), str(player["player_id"]), fill="white", font=review.font(11))
            xy = location(center, rect, origin, dimensions) if center is not None else None
            if xy:
                x, y = xy
                draw.ellipse((x-6, y-6, x+6, y+6), outline="#ff45c5", width=2)
                draw.line((x-10, y, x+10, y), fill="#ff45c5", width=2)
                draw.line((x, y-10, x, y+10), fill="#ff45c5", width=2)
        draw.text((left+12, 450), "Shared zoom: " + ("original point" if baseline else "new gap point" if selected else "image center"),
                  fill="#ffd380", font=review.font(16))
    footer = ("PROTECTED: black panels; no source image, players or predictions" if withheld else
              "Pink: ball point | White: reconciled NFHS player IDs (display only) | Unknown stays missing"
              if source["kind"] == "nfhs" else "Pink: ball point | NBA player identities unavailable | Unknown stays missing")
    draw.text((12, 784), footer, fill="white", font=review.font(15))
    bits = review.key_bits(index, row)+pair_bits(row)
    for i, bit in enumerate(bits):
        draw.rectangle((i*8, 808, i*8+7, 815), fill="white" if bit == "1" else "black")
    return canvas


def iter_images(root, source):
    """Decode only permitted sources, retaining at most one source frame."""
    if source["kind"] == "nba":
        for index, row in enumerate(source["frames"]):
            raw = nba.read_verified_png(row["source_frame"], source["source_video"], root)
            with Image.open(io.BytesIO(raw)) as image:
                yield render_frame(image.convert("RGB"), source, row, index)
        return
    possession = source["possession"]
    verify_source_video_contract(SourceVideo.from_mapping(source["source_video"]), root)
    players = observation.load_player_display(root, possession)
    starts = {a: [a, b] for a, b in possession["visible_segments"]}
    images = None
    try:
        for index, row in enumerate(source["frames"]):
            native = row["source_frame_index"]
            if native in starts:
                if images is not None:
                    images.close()
                images = iter(observation.decode_segment(root, possession, starts[native]))
            if row["decision"] == "withheld":
                if images is not None:
                    images.close(); images = None
                yield render_frame(None, source, row, index)
            else:
                d.require(images is not None, "Permitted frame has no source decoder")
                actual, pixels = next(images)
                d.require(actual == native, "Source/player/ball native frame join differs")
                yield render_frame(Image.fromarray(pixels[:, :, ::-1]), source, row, index, players.get(native, []))
    finally:
        if images is not None:
            images.close()


def verify_probe(probe, records):
    d.require(len(probe["streams"]) == 1, "Unexpected review streams")
    stream = probe["streams"][0]
    total = records[-1]["review_pts_ticks"]+records[-1]["duration_ticks"]
    d.require(stream["time_base"] == "1/90000" and int(stream["duration_ts"]) == total
              and (stream["width"], stream["height"]) == (WIDTH, HEIGHT)
              and int(stream["nb_frames"]) == len(records), "Encoded timeline differs")
    d.require([(int(f["best_effort_timestamp"]), int(f["duration"])) for f in probe["frames"]]
              == [(r["review_pts_ticks"], r["duration_ticks"]) for r in records], "Encoded frame timestamps differ")
    return total


def verify_pixels(decoded, expected, row, index):
    bits = "".join("1" if decoded[812, i*8+4].mean() > 127 else "0" for i in range(144))
    d.require(bits == review.key_bits(index, row)+pair_bits(row), "Decoded native frame or panel key differs")
    delta = np.abs(decoded.astype(np.int16)-np.asarray(expected).astype(np.int16))
    errors = [float(delta[:, panel*640:(panel+1)*640].mean()) for panel in (0, 1)]
    d.require(max(errors) < 8, "Decoded paired pixels differ")
    if row["decision"] == "withheld":
        d.require(int(decoded[96:776].max()) <= 3, "Protected panels are not black")
    return errors


def render_source(root, source, ffmpeg, output, bindings):
    """Stream and verify one complete comparison; preserve failed attempts."""
    import av
    root, output = Path(root).resolve(), Path(output).resolve()
    d.require(output.is_relative_to(root/"data/outputs"), "Review output must remain ignored")
    records = validate_source(root, source)
    identity = {"schema_version": SCHEMA, "source_sha256": wasb.canonical(source), "bindings": bindings,
                "renderer_sha256": d.digest(Path(__file__)), "source_reader_sha256": d.digest(Path(nba.__file__)),
                "nfhs_helpers_sha256": d.digest(Path(observation.__file__)),
                "display_helpers_sha256": d.digest(Path(review.__file__)), "final_hold_ticks": HOLD_TICKS}
    parent = output/"attempts"
    for path in sorted(parent.glob("*/completion.json")) if parent.exists() else []:
        saved = d.read_json(path)
        if saved["identity"] == identity:
            for record in saved["artifacts"].values():
                review.bound(root, record)
            for still in saved["changed_frames"]:
                review.bound(root, still["image"])
            for final in saved["segment_final_frames"]:
                review.bound(root, final["image"])
            return {**saved["artifacts"], "changed_frames": saved["changed_frames"],
                    "segment_final_frames": saved["segment_final_frames"], "completion": review.binding(root, path)}
    folder = parent/uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=False)
    review.write_json(folder/"started.json", {"identity": identity, "at_utc": d.stamp()})
    began = time.monotonic()
    try:
        video = folder/"comparison.mp4"
        durations = {r["review_pts_ticks"]: r["duration_ticks"] for r in records}
        with av.open(str(video), "w", options={"movflags": "+faststart"}) as container:
            stream = container.add_stream("libx264", rate=25 if source["kind"] == "nfhs" else Fraction(60000, 1001),
                                          options={"crf": "18", "preset": "fast", "bf": "0"})
            stream.width, stream.height, stream.pix_fmt = WIDTH, HEIGHT, "yuv420p"
            stream.time_base = stream.codec_context.time_base = Fraction(1, 90000)
            stream.codec_context.thread_count = 2
            def mux(packets):
                for packet in packets:
                    d.require(packet.time_base == Fraction(1, 90000) and packet.pts in durations, "Encoder PTS changed")
                    packet.duration = durations[packet.pts]
                    container.mux(packet)
            images = iter_images(root, source)
            try:
                for record, image in zip(records, images, strict=True):
                    frame = av.VideoFrame.from_image(image)
                    frame.pts, frame.time_base = record["review_pts_ticks"], Fraction(1, 90000)
                    mux(stream.encode(frame))
                mux(stream.encode())
            finally:
                images.close()
        ffprobe = Path(ffmpeg).with_name("ffprobe.exe" if Path(ffmpeg).suffix.lower() == ".exe" else "ffprobe")
        probe_command = [str(ffprobe), "-v", "error", "-select_streams", "v:0", "-show_entries",
                         "stream=time_base,duration_ts,nb_frames,width,height:frame=best_effort_timestamp,duration",
                         "-of", "json", str(video)]
        probed = subprocess.run(probe_command, capture_output=True, check=False, timeout=180)
        (folder/"ffprobe.stderr.txt").write_bytes(probed.stderr)
        d.require(probed.returncode == 0, "Review probe failed")
        probe = json.loads(probed.stdout)
        review.write_json(folder/"ffprobe.json", probe)
        total = verify_probe(probe, records)
        command = [str(ffmpeg), "-hide_banner", "-nostdin", "-loglevel", "error", "-xerror", "-threads", "2",
                   "-i", str(video), "-map", "0:v:0", "-an", "-fps_mode", "passthrough", "-pix_fmt", "rgb24",
                   "-f", "rawvideo", "pipe:1"]
        errors, stills, finals = [], [], []
        segment_ends = {s["range_inclusive"][1] for s in source["segments"]}
        with (folder/"decode.stderr.txt").open("xb") as stderr:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=stderr)
            images = iter_images(root, source)
            try:
                for record, row, expected in zip(records, source["frames"], images, strict=True):
                    raw = bytearray()
                    while len(raw) < WIDTH*HEIGHT*3:
                        chunk = process.stdout.read(WIDTH*HEIGHT*3-len(raw))
                        d.require(bool(chunk), "Missing decoded review frame")
                        raw.extend(chunk)
                    decoded = np.frombuffer(raw, np.uint8).reshape(HEIGHT, WIDTH, 3)
                    errors.append(verify_pixels(decoded, expected, row, record["review_index"]))
                    if row["decision"] == "filled_saved_candidate":
                        path = folder/f"changed_{row['source_frame_index']:06d}.png"
                        Image.fromarray(decoded).save(path)
                        stills.append({"source_frame_index": row["source_frame_index"], "source_pts_ticks": row["source_pts_ticks"],
                                       "image": review.binding(root, path)})
                    if row["source_frame_index"] in segment_ends:
                        path = folder/f"segment_final_{row['source_frame_index']:06d}.png"
                        Image.fromarray(decoded).save(path)
                        finals.append({"source_frame_index": row["source_frame_index"], "source_pts_ticks": row["source_pts_ticks"],
                                       "segment_id": row["segment_id"], "image": review.binding(root, path)})
                    if record["review_index"] == len(records)-1:
                        Image.fromarray(decoded).save(folder/"final_frame.png")
                d.require(process.stdout.read(1) == b"" and process.wait(timeout=60) == 0, "Unexpected frames or decode failure")
            finally:
                images.close()
                if process.poll() is None:
                    process.kill(); process.wait(timeout=10)
                process.stdout.close()
        review.write_json(folder/"review_manifest.json", {"schema_version": SCHEMA, "identity": identity,
            "candidate_id": source["candidate_id"], "source_video": source["source_video"], "frames": records,
            "time_base": "1/90000", "native_source_pacing": True, "final_hold_ticks": HOLD_TICKS,
            "source_pts_origin": "clip-relative frame zero" if source["kind"] == "nfhs" else "native NBA source",
            "native_timestamp_evidence": source.get("native_timestamps"),
            "protected_source_pixels_decoded": 0, "player_ids_display_only": source["kind"] == "nfhs",
            "retained_all_frame_composite_pngs": False, "human_review": "pending", "labels_read": 0})
        review.write_json(folder/"verification.json", {"status": "passed", "decoded_frames": len(errors),
            "all_native_pts_durations_and_pair_keys_verified": True, "all_paired_pixels_verified": True,
            "panel_overlay_mae_max": [max(e[p] for e in errors) for p in (0, 1)],
            "protected_frame_pairs_verified_black": sum(r["source_pixels_withheld"] for r in records),
            "changed_frames": stills, "segment_final_frames": finals,
            "actual_final_source_frame_index": records[-1]["source_frame_index"],
            "duration_ticks": total, "probe_command": probe_command, "decode_command": command})
        artifacts = {key: review.binding(root, folder/name) for key, name in {
            "video": "comparison.mp4", "manifest": "review_manifest.json", "verification": "verification.json",
            "probe": "ffprobe.json", "final_frame": "final_frame.png"}.items()}
        review.write_json(folder/"completion.json", {"status": "completed", "identity": identity,
            "artifacts": artifacts, "changed_frames": stills, "segment_final_frames": finals,
            "elapsed_seconds": time.monotonic()-began,
            "human_review": "pending"})
        return {**artifacts, "changed_frames": stills, "segment_final_frames": finals,
                "completion": review.binding(root, folder/"completion.json")}
    except Exception as error:
        review.write_json(folder/"failed.json", {"status": "failed_preserved", "error_type": type(error).__name__,
            "error": str(error), "elapsed_seconds": time.monotonic()-began})
        raise


def render_all(root, selection, ffmpeg, output, bindings):
    """Render the fixed two NBA and three NFHS sources, then a local guide."""
    root, output = Path(root).resolve(), Path(output).resolve()
    sources = selection["sources"]
    d.require(selection["schema_version"] == "nba_temporal_gap_continuous/v0.1"
              and len(sources) == 5 and len({s["candidate_id"] for s in sources}) == 5
              and sum(s["kind"] == "nba" for s in sources) == 2
              and sum(s["kind"] == "nfhs" for s in sources) == 3, "Expected five-source continuous selection")
    d.require(sum(len(s["frames"]) for s in sources) == 4200
              and sum(r["decision"] == "withheld" for s in sources for r in s["frames"]) == 225,
              "Continuous playback slot inventory differs")
    groups = {}
    for source in sources:
        name = source["candidate_id"]
        d.require(Path(name).name == name and "/" not in name and "\\" not in name and name not in (".", ".."),
                  "Unsafe source ID")
        print(f"Rendering {name}: {len(source['frames'])} native timeline slots", flush=True)
        groups[name] = render_source(root, source, ffmpeg, output/name, bindings)
    cards = []
    for name, package in groups.items():
        def url(record):
            return quote(Path(os.path.relpath(review.bound(root, record), output)).as_posix(), safe="/.")
        cards.append(f'<section><h2>{html.escape(name)}</h2><video controls preload="metadata" src="{url(package["video"])}"></video>'
                     f'<p><a href="{url(package["final_frame"])}">Actual final frame</a> | '
                     f'<a href="{url(package["manifest"])}">Native frame map</a></p>'
                     '<details><summary>All newly filled frames</summary><p>' +
                     ' | '.join(f'<a href="{url(item["image"])}">Frame {item["source_frame_index"]}</a>'
                                for item in package["changed_frames"]) + '</p></details>'
                     '<details><summary>Every permitted-segment final</summary><p>' +
                     ' | '.join(f'<a href="{url(item["image"])}">Frame {item["source_frame_index"]}</a>'
                                for item in package["segment_final_frames"]) + '</p></details>'
                     '<label>Playback speed <select><option value="1">1× native</option><option value="0.5">0.5×</option>'
                     '<option value="0.25">0.25×</option></select></label></section>')
    document = ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<title>Continuous gap-rule review</title><style>body{max-width:1280px;margin:24px auto;padding:0 20px;'
        'background:#0f141d;color:#edf2f7;font:17px system-ui}video{width:100%;background:black}section{margin:32px 0}'
        'a{color:#8dd5ff}select{font:inherit}</style><h1>Continuous gap-rule comparison</h1>'
        '<p>Watch all five complete comparisons through their actual final frames. Left: same-context original selection. '
        'Right: unchanged short-gap rule. Pink marks ball positions; NFHS white labels are reconciled player IDs for display only. '
        'Unknown intervals remain missing, and protected NFHS bands remain black.</p>'
        '<p>NBA uses native timestamps; NFHS uses 25 fps. Each final frame has one extra second. '
        'Unlabeled positions have no accuracy claim. Human trajectory review is pending.</p>' + ''.join(cards) +
        '<script>document.querySelectorAll("section").forEach(s=>s.querySelector("select").addEventListener("change",'
        'e=>s.querySelector("video").playbackRate=Number(e.target.value)));</script></html>\n')
    path = output/"review.html"
    if path.exists():
        d.require(path.read_text(encoding="utf-8") == document, "Existing review guide differs")
    else:
        path.write_text(document, encoding="utf-8", newline="\n")
    return {"schema_version": SCHEMA, "status": "completed", "groups": groups,
            "guide": review.binding(root, path), "timeline_slots": 4200, "protected_slots": 225,
            "human_review": "pending", "new_model_calls": 0}
