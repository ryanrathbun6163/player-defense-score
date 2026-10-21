"""Compact source-first reference review; never show or score model coordinates."""
from __future__ import annotations

import argparse
from fractions import Fraction
import html
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import time
import uuid
from urllib.parse import quote

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from . import nba_action_review as review
from . import nba_annotations as nba
from . import nba_wasb_diagnostic as d

SCHEMA = "nba_gap_anchor_reference_review/v0.1"
WIDTH, HEIGHT = 1280, 816
FRAME_TICKS, HOLD_TICKS = 18000, 90000


def load_inputs(root, preparation_path, proposal_path):
    """Consume the actual producer contract and a separately persisted proposal."""
    from . import nba_gap_anchor_reference as authority
    root = Path(root).resolve()
    preparation_path = d.contained(root, str(preparation_path))
    proposal_path = d.contained(root, str(proposal_path))
    preparation, proposal = authority.validate_proposal(root, proposal_path)
    d.require(proposal["preparation"] == review.binding(root, preparation_path),
              "Requested preparation differs from proposed reference authority")
    d.require(d.read_json(preparation_path) == preparation, "Preparation consumer transport differs")
    sources = {s["candidate_id"]: s for s in preparation["sources"]}
    proposed = {(r["continuous_source_id"], r["source_frame_index"]): r["annotation"] for r in proposal["new_annotations"]}
    reused = {(r["continuous_source_id"], r["source_frame_index"]): r["existing_reference"] for r in proposal["existing_controls"]}
    d.require(not set(proposed).intersection(reused), "New and accepted reference inventories overlap")
    rows = []
    for frame in preparation["frames"]:
        key = frame["continuous_source_id"], frame["source_frame_index"]
        if frame["role"] == "context_only":
            d.require(key not in proposed and key not in reused, "Context-only frame received a reference judgment")
            annotation = None
        elif frame["reference_origin"] == "existing":
            d.require(reused[key] == frame["existing_reference"], "Accepted reference was modified")
            annotation = reused[key]["row"]["annotation"]
        else:
            d.require(frame["reference_origin"] == "new", "Unexpected target reference origin")
            annotation = proposed[key]
        if annotation is not None:
            d.require(annotation["frame_index"] == frame["source_frame_index"], "Annotation/source frame join differs")
        rows.append({"frame": frame, "source": sources[frame["continuous_source_id"]], "annotation": annotation})
    d.require(sum(r["annotation"] is not None for r in rows) == len(proposed)+len(reused), "Reference target coverage differs")
    return preparation, proposal, rows


def shared_crops(preparation, rows):
    """One reference-derived viewport per context; no predictions are consulted."""
    crops = {}
    for group in preparation["groups"]:
        selected = [r for r in rows if r["frame"]["group_id"] == group["group_id"]]
        d.require(selected, "Empty context")
        source = selected[0]["source"]["source_video"]
        width, height = source["width_px"], source["height_px"]
        geometries = [r["annotation"]["geometry"] for r in selected if r["annotation"] and r["annotation"]["geometry"]]
        if not geometries:
            crops[group["group_id"]] = [0, 0, width, height]
            continue
        xlo = min(g["center_xy_px"][0]-g["uncertainty_radius_px"] for g in geometries)
        xhi = max(g["center_xy_px"][0]+g["uncertainty_radius_px"] for g in geometries)
        ylo = min(g["center_xy_px"][1]-g["uncertainty_radius_px"] for g in geometries)
        yhi = max(g["center_xy_px"][1]+g["uncertainty_radius_px"] for g in geometries)
        crop_w = min(width, max(320, math.ceil(xhi-xlo+96), math.ceil((yhi-ylo+72)*16/9)))
        crop_h = min(height, max(180, math.ceil(crop_w*9/16)))
        left = max(0, min(width-crop_w, math.floor((xlo+xhi-crop_w)/2)))
        top = max(0, min(height-crop_h, math.floor((ylo+yhi-crop_h)/2)))
        crops[group["group_id"]] = [left, top, left+crop_w, top+crop_h]
    return crops


def timeline_records(preparation, rows):
    groups = preparation["groups"]
    d.require(len({g["group_id"] for g in groups}) == len(groups), "Duplicate context identity")
    crops = shared_crops(preparation, rows)
    records, tick = [], 0
    for group_index, group in enumerate(groups):
        selected = [r for r in rows if r["frame"]["group_id"] == group["group_id"]]
        a, b = group["context_range_inclusive"]
        d.require([r["frame"]["source_frame_index"] for r in selected] == list(range(a, b+1)), "Context frame inventory differs")
        d.require(all(r["frame"]["continuous_source_id"] == group["continuous_source_id"] for r in selected), "Context source differs")
        for i, row in enumerate(selected):
            frame = row["frame"]
            final = i == len(selected)-1
            duration = FRAME_TICKS+(HOLD_TICKS if final else 0)
            records.append({"review_index": len(records), "group_index": group_index, "group_id": group["group_id"],
                "continuous_source_id": frame["continuous_source_id"], "source_frame_index": frame["source_frame_index"],
                "source_pts_ticks": frame["source_pts_ticks"], "source_time_base": "1/90000",
                "review_pts_ticks": tick, "duration_ticks": duration, "context_final": final,
                "role": frame["role"], "reference_origin": frame["reference_origin"],
                "source_png": frame["raw_png"], "annotation": row["annotation"],
                "source_size_px": [row["source"]["source_video"]["width_px"], row["source"]["source_video"]["height_px"]],
                "crop_xyxy_source_px": crops[group["group_id"]]})
            tick += duration
    d.require(len(records) == len(rows), "Context ordering omitted or duplicated frames")
    return records


def frame_bits(record):
    authority = [record[k] for k in ("continuous_source_id", "group_id", "role", "reference_origin", "annotation", "crop_xyxy_source_px")]
    return review.key_bits(record["review_index"], record)+f"{int(review.canonical(authority)[:12],16):048b}"


def render_frame(image, row, record, context_count):
    """Source and same-context crop show only a target's actual reference row."""
    frame, source, annotation = row["frame"], row["source"]["source_video"], row["annotation"]
    d.require(image.size == (source["width_px"], source["height_px"]), "Source image dimensions differ")
    d.require(record["annotation"] == annotation and record["source_png"] == frame["raw_png"], "Render reference/source join differs")
    canvas = Image.new("RGB", (WIDTH, HEIGHT), (15, 20, 29)); draw = ImageDraw.Draw(canvas)
    origin = ("CONTEXT ONLY — NO REFERENCE JUDGMENT" if annotation is None else
              "AI PROPOSAL — HUMAN REVIEW PENDING" if record["reference_origin"] == "new" else "ACCEPTED REFERENCE — REUSED CONTROL")
    draw.text((14, 8), f"{record['group_index']+1}/{context_count}  {record['continuous_source_id']}  |  {origin}",
              fill="#ffd380", font=review.font(23))
    draw.text((14, 42), f"Source frame {record['source_frame_index']}  |  Native PTS {record['source_pts_ticks']} / 90000  |  5 fps slowed review",
              fill="white", font=review.font(20))
    draw.text((14, 79), "ORIGINAL SOURCE + REFERENCE", fill="white", font=review.font(21))
    draw.text((654, 79), "SAME CONTEXT CROP + REFERENCE", fill="white", font=review.font(21))
    crop_box = record["crop_xyxy_source_px"]
    crop = image.crop(crop_box)
    view = ImageOps.contain(image, (620, 440), Image.Resampling.LANCZOS)
    zoom = ImageOps.contain(crop, (620, 440), Image.Resampling.LANCZOS)
    vx, vy = 10+(620-view.width)//2, 115+(440-view.height)//2
    zx, zy = 650+(620-zoom.width)//2, 115+(440-zoom.height)//2
    canvas.paste(view, (vx, vy)); canvas.paste(zoom, (zx, zy))
    geometry = annotation["geometry"] if annotation else None
    if geometry:
        point = geometry["center_xy_px"]; radius = geometry["uncertainty_radius_px"]
        for left, top, rendered, original, origin_xy in ((vx, vy, view.size, image.size, (0, 0)),
                                                       (zx, zy, zoom.size, crop.size, crop_box[:2])):
            sx, sy = rendered[0]/original[0], rendered[1]/original[1]
            x, y = left+(point[0]-origin_xy[0])*sx, top+(point[1]-origin_xy[1])*sy
            draw.ellipse((x-radius*sx, y-radius*sy, x+radius*sx, y+radius*sy), outline="#00ffff", width=2)
            draw.line((x-9, y, x+9, y), fill="#00ffff", width=2)
            draw.line((x, y-9, x, y+9), fill="#00ffff", width=2)
        state = f"{annotation['visibility'].replace('_',' ').upper()}  |  Center [{point[0]:.2f}, {point[1]:.2f}]  |  Uncertainty {radius:.2f} px"
    elif annotation is not None:
        state = f"{(annotation['visibility'] or annotation['annotation_status']).replace('_',' ').upper()}  |  No defensible reference center"
    else:
        state = "Unmarked neighboring frame: context only; no ball position has been assigned"
    draw.text((14, 585), state, fill="#00ffff" if geometry else "#ffd380", font=review.font(24))
    if annotation is not None:
        certainty = annotation["game_ball_identity_certainty"] or "unknown"
        meaning = (("Geometry eligible after acceptance" if record["reference_origin"] == "new" else "Geometry eligible")
                   if annotation["localization_eligible"] else "Not eligible for geometric scoring")
        draw.text((14, 625), f"Identity: {certainty}  |  {record['role'].upper()}  |  {meaning}", fill="white", font=review.font(21))
        if record["reference_origin"] == "existing":
            draw.text((14, 661), "Previously accepted annotation and uncertainty retained unchanged", fill="white", font=review.font(19))
    draw.text((14, 740), "Cyan: reference center and uncertainty only. No model predictions are displayed.", fill="white", font=review.font(21))
    draw.text((14, 775), "New references are AI proposals. Context finals hold 1 extra second. Native motion is slowed.", fill="#ffd380", font=review.font(18))
    for i, bit in enumerate(frame_bits(record)):
        draw.rectangle((i*8, 808, i*8+7, 815), fill="white" if bit == "1" else "black")
    return canvas


def rendered_images(root, rows, records, context_count):
    indexed = {(r["frame"]["continuous_source_id"], r["frame"]["source_frame_index"]): r for r in rows}
    for record in records:
        row = indexed[record["continuous_source_id"], record["source_frame_index"]]
        raw = nba.read_verified_png({"png": row["frame"]["raw_png"]}, row["source"]["source_video"], root)
        with Image.open(io.BytesIO(raw)) as image:
            yield render_frame(image.convert("RGB"), row, record, context_count)


def verify_probe(probe, records):
    d.require(len(probe["streams"]) == 1, "Unexpected reference review streams")
    stream = probe["streams"][0]; total = records[-1]["review_pts_ticks"]+records[-1]["duration_ticks"]
    d.require(stream["time_base"] == "1/90000" and int(stream["duration_ts"]) == total
              and int(stream["nb_frames"]) == len(records) and (stream["width"], stream["height"]) == (WIDTH, HEIGHT),
              "Encoded reference frame inventory or final hold differs")
    d.require([(int(f["best_effort_timestamp"]), int(f["duration"])) for f in probe["frames"]]
              == [(r["review_pts_ticks"], r["duration_ticks"]) for r in records], "Encoded reference frame timing differs")
    return total


def verify_pixels(decoded, expected, record):
    bits = "".join("1" if decoded[812, i*8+4].mean() > 127 else "0" for i in range(160))
    d.require(bits == frame_bits(record), "Decoded source/reference/crop key differs")
    delta = np.abs(decoded.astype(np.int16)-np.asarray(expected).astype(np.int16))
    errors = [float(delta[:, i*640:(i+1)*640].mean()) for i in (0, 1)]
    d.require(max(errors) < 8, "Decoded source/reference panels differ")
    geometry = record["annotation"]["geometry"] if record["annotation"] else None
    if geometry:
        # A panel-wide average could miss an erased small marker. Check the
        # actual cyan pixels locally around each independently projected center.
        a, b, c, e = record["crop_xyxy_source_px"]
        for panel_left, size, origin in ((10, record["source_size_px"], (0, 0)), (650, (c-a, e-b), (a, b))):
            width, height = size
            rw, rh = (620, round(height/width*620)) if width/height > 620/440 else (round(width/height*440), 440)
            x = panel_left+(620-rw)//2+(geometry["center_xy_px"][0]-origin[0])*rw/width
            y = 115+(440-rh)//2+(geometry["center_xy_px"][1]-origin[1])*rh/height
            x0, x1 = max(0, int(x)-12), min(WIDTH, int(x)+13)
            y0, y1 = max(0, int(y)-12), min(HEIGHT, int(y)+13)
            expected_patch = np.asarray(expected)[y0:y1, x0:x1]
            cyan = (expected_patch[:, :, 0] < 10)&(expected_patch[:, :, 1] > 245)&(expected_patch[:, :, 2] > 245)
            # Two-pixel cyan strokes are chroma-subsampled by the phone-compatible
            # YUV420 stream; the transport fixture measures about 42 RGB levels.
            # This bound still rejects erased markers, independently of panel MAE.
            d.require(cyan.any() and float(delta[y0:y1, x0:x1][cyan].mean()) < 65, "Decoded reference marker differs")
    return errors


def render(root, preparation_path, proposal_path, output, ffmpeg=None):
    import av
    root = Path(root).resolve(); output = d.contained(root, str(output))
    d.require(output.is_relative_to(root/"data/outputs"), "Review output must remain ignored")
    preparation, proposal, rows = load_inputs(root, preparation_path, proposal_path)
    records = timeline_records(preparation, rows)
    ffmpeg = Path(ffmpeg or shutil.which("ffmpeg") or "ffmpeg")
    identity = {"schema_version": SCHEMA, "preparation": review.binding(root, d.contained(root, str(preparation_path))),
                "proposal": review.binding(root, d.contained(root, str(proposal_path))),
                "renderer": review.binding(root, root/"src/ball_tracking"/Path(__file__).name),
                "source_reader": review.binding(root, root/"src/ball_tracking"/Path(nba.__file__).name),
                "review_helper": review.binding(root, root/"src/ball_tracking"/Path(review.__file__).name),
                "source_frames_per_second": 5, "context_final_extra_hold_ticks": HOLD_TICKS}
    parent = output/"attempts"
    for path in sorted(parent.glob("*/completion.json")) if parent.exists() else []:
        prior = d.read_json(path)
        if prior["identity"] == identity:
            for item in prior["artifacts"].values(): review.bound(root, item)
            for item in prior["target_stills"]+prior["context_finals"]: review.bound(root, item["image"])
            return {**prior, "completion": review.binding(root, path)}
    folder = parent/uuid.uuid4().hex; folder.mkdir(parents=True, exist_ok=False)
    review.write_json(folder/"started.json", {"identity": identity, "at_utc": d.stamp()})
    began = time.monotonic()
    try:
        video = folder/"reference_compilation.mp4"
        durations = {r["review_pts_ticks"]: r["duration_ticks"] for r in records}
        with av.open(str(video), "w", options={"movflags": "+faststart"}) as container:
            stream = container.add_stream("libx264", rate=5, options={"crf": "18", "preset": "fast", "bf": "0"})
            stream.width, stream.height, stream.pix_fmt = WIDTH, HEIGHT, "yuv420p"
            stream.time_base = stream.codec_context.time_base = Fraction(1, 90000); stream.codec_context.thread_count = 2
            def mux(packets):
                for packet in packets:
                    d.require(packet.time_base == Fraction(1, 90000) and packet.pts in durations, "Encoder reference PTS changed")
                    packet.duration = durations[packet.pts]; container.mux(packet)
            for record, image in zip(records, rendered_images(root, rows, records, len(preparation["groups"])), strict=True):
                frame = av.VideoFrame.from_image(image); frame.pts = record["review_pts_ticks"]; frame.time_base = Fraction(1, 90000)
                mux(stream.encode(frame))
            mux(stream.encode())
        ffprobe = ffmpeg.with_name("ffprobe.exe" if ffmpeg.suffix.lower() == ".exe" else "ffprobe")
        command = [str(ffprobe), "-v", "error", "-select_streams", "v:0", "-show_entries",
                   "stream=time_base,duration_ts,nb_frames,width,height:frame=best_effort_timestamp,duration", "-of", "json", str(video)]
        probe = subprocess.run(command, capture_output=True, check=False, timeout=120)
        (folder/"ffprobe.stderr.txt").write_bytes(probe.stderr)
        d.require(probe.returncode == 0, "Reference review probe failed")
        probe_data = json.loads(probe.stdout); review.write_json(folder/"ffprobe.json", probe_data)
        total = verify_probe(probe_data, records)
        decode = [str(ffmpeg), "-hide_banner", "-nostdin", "-loglevel", "error", "-xerror", "-threads", "2", "-i", str(video),
                  "-map", "0:v:0", "-an", "-fps_mode", "passthrough", "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"]
        errors, targets, finals = [], [], []
        with (folder/"decode.stderr.txt").open("xb") as stderr:
            process = subprocess.Popen(decode, stdout=subprocess.PIPE, stderr=stderr)
            try:
                for record, expected in zip(records, rendered_images(root, rows, records, len(preparation["groups"])), strict=True):
                    raw = bytearray()
                    while len(raw) < WIDTH*HEIGHT*3:
                        chunk = process.stdout.read(WIDTH*HEIGHT*3-len(raw)); d.require(bool(chunk), "Missing reference review frame")
                        raw.extend(chunk)
                    pixels = np.frombuffer(raw, np.uint8).reshape(HEIGHT, WIDTH, 3)
                    errors.append(verify_pixels(pixels, expected, record))
                    item = {k: record[k] for k in ("review_index", "group_id", "continuous_source_id", "source_frame_index", "source_pts_ticks", "role", "reference_origin")}
                    if record["annotation"] is not None:
                        path = folder/f"target_{record['review_index']:03d}.png"; Image.fromarray(pixels).save(path)
                        targets.append({**item, "image": review.binding(root, path)})
                    if record["context_final"]:
                        path = folder/f"context_final_{record['group_index']:02d}.png"; Image.fromarray(pixels).save(path)
                        finals.append({**item, "image": review.binding(root, path)})
                    if record["review_index"] == len(records)-1: Image.fromarray(pixels).save(folder/"final_frame.png")
                d.require(process.stdout.read(1) == b"" and process.wait(timeout=60) == 0, "Extra reference frames or decode failure")
            finally:
                if process.poll() is None: process.kill(); process.wait(timeout=10)
                process.stdout.close()
        review.write_json(folder/"manifest.json", {"schema_version": SCHEMA, "identity": identity, "frames": records,
            "native_motion_pacing": False, "source_frames_per_second": 5, "context_final_hold_seconds": 1,
            "context_only_frames_unlabeled": True, "model_predictions_displayed": False, "human_review": "pending"})
        review.write_json(folder/"verification.json", {"status": "passed", "decoded_frames": len(errors), "duration_ticks": total,
            "all_source_reference_crop_keys_verified": True, "all_paired_pixels_verified": True,
            "all_reference_markers_verified": True,
            "panel_mae_max": [max(e[i] for e in errors) for i in (0, 1)], "target_stills": targets, "context_finals": finals,
            "actual_final_source": records[-1]["continuous_source_id"], "actual_final_frame": records[-1]["source_frame_index"],
            "probe_command": command, "decode_command": decode})
        guide = build_guide(folder, records, targets, finals, total)
        artifacts = {key: review.binding(root, folder/name) for key, name in {"video": "reference_compilation.mp4", "manifest": "manifest.json",
            "verification": "verification.json", "probe": "ffprobe.json", "final_frame": "final_frame.png", "guide": guide.name}.items()}
        completed = {"schema_version": SCHEMA, "status": "completed", "identity": identity, "artifacts": artifacts,
            "target_stills": targets, "context_finals": finals, "human_review": "pending", "elapsed_seconds": time.monotonic()-began}
        review.write_json(folder/"completion.json", completed)
        return {**completed, "completion": review.binding(root, folder/"completion.json")}
    except Exception as error:
        review.write_json(folder/"failed.json", {"status": "failed_preserved", "error_type": type(error).__name__,
            "error": str(error), "elapsed_seconds": time.monotonic()-began})
        raise


def build_guide(folder, records, targets, finals, total):
    cards = []
    for target in targets:
        record = records[target["review_index"]]; annotation = record["annotation"]
        caption = f"{record['continuous_source_id']} / {record['source_frame_index']} — {record['role']}; {record['reference_origin']} reference"
        if annotation["geometry"] is None: caption += " — NO REFERENCE CENTER"
        cards.append(f'<figure><a href="{quote(Path(target["image"]["path"]).name)}"><img loading="lazy" src="{quote(Path(target["image"]["path"]).name)}"></a><figcaption>{html.escape(caption)}</figcaption></figure>')
    unknown = [r for r in records if r["annotation"] is not None and (r["annotation"]["geometry"] is None or not r["annotation"]["localization_eligible"])]
    notes = ''.join(f'<li>{html.escape(r["continuous_source_id"])} frame {r["source_frame_index"]}: {html.escape(r["annotation"]["notes"] or "No eligible reference center")}</li>' for r in unknown)
    final_links = ''.join(f'<li>{html.escape(x["continuous_source_id"])} frame {x["source_frame_index"]}: <a href="{quote(Path(x["image"]["path"]).name)}">context final</a></li>' for x in finals)
    text = ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<title>Gap and anchor reference proposals</title><style>body{max-width:1280px;margin:20px auto;padding:0 16px;background:#0f141d;color:#edf2f7;font:18px system-ui}video,img{width:100%;background:black}figure{margin:20px 0}a{color:#8dd5ff}select{font:inherit}</style>'
        '<h1>Gap and anchor reference review</h1><p>New source-first AI proposals remain pending human acceptance. Existing accepted controls are reused unchanged. '
        f'{sum(r["annotation"] is None for r in records)} surrounding context frames receive no new judgment. Cyan shows only reference centers and uncertainty; no model predictions appear.</p>'
        f'<p>{len(records)} native source frames shown at 5 fps, plus one extra second on each context final: {total/90000:.1f} seconds. This is slowed review, not native motion.</p>'
        '<video id="clip" controls preload="metadata" src="reference_compilation.mp4"></video>'
        '<p>Speed <select id="speed"><option value="1">1× review speed</option><option value="0.5">0.5×</option><option value="0.25">0.25×</option></select> | <a href="final_frame.png">Actual compilation final</a></p>'
        '<h2>Unknown or unscored targets</h2><ul>'+notes+'</ul><h2>Every target frame</h2>'+''.join(cards)+'<h2>Every context final</h2><ul>'+final_links+'</ul>'
        '<script>document.getElementById("speed").addEventListener("change",e=>document.getElementById("clip").playbackRate=Number(e.target.value));</script></html>\n')
    path = folder/"review.html"; path.write_text(text, encoding="utf-8", newline="\n"); return path


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--preparation", required=True); parser.add_argument("--proposal", required=True)
    parser.add_argument("--output", required=True); parser.add_argument("--ffmpeg")
    args = parser.parse_args(); root = Path(__file__).resolve().parents[2]
    print(json.dumps(render(root, args.preparation, args.proposal, args.output, args.ffmpeg), indent=2))


if __name__ == "__main__":
    main()
