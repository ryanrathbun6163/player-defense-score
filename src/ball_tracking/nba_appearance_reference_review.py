"""Source-first candidate sheets and compact semantic-reference review media."""
from __future__ import annotations

import argparse
from fractions import Fraction
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import time
import uuid

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from . import nba_action_review as review
from . import nba_annotations as nba
from . import nba_gap_anchor_reference_review as timing
from . import nba_wasb_diagnostic as d

WIDTH, HEIGHT = 1280, 816
SCHEMA = "nba_appearance_reference_review/v0.1"


def inputs(root, preparation_path, proposal_path=None):
    from . import nba_appearance_reference as authority
    path = d.contained(root, str(preparation_path))
    if proposal_path is None:
        prepared, proposal = authority.load_ready_preparation(root, path), None
    else:
        prepared, proposal = authority.validate_proposal(root, d.contained(root, str(proposal_path)))
        d.require(proposal["preparation"] == d.binding(root, path), "Requested preparation/proposal differs")
    d.require(d.read_json(path) == prepared, "Preparation consumer transport differs")
    return prepared, proposal


def records(prepared, proposal=None):
    sources = {s["candidate_id"]: s for s in prepared["sources"]}
    labels = {} if proposal is None else {r["candidate_key"]: r for r in proposal["rows"]}
    result, tick = [], 0
    for group_index, group in enumerate(prepared["groups"]):
        frames = [f for f in prepared["frames"] if f["group_id"] == group["group_id"]]
        candidates = [c for c in prepared["candidates"] if c["group_id"] == group["group_id"]]
        lo, hi = group["context_range_inclusive"]
        d.require(hi-lo == 4 and [f["source_frame_index"] for f in frames] == list(range(lo, hi+1)), "Five-frame context differs")
        d.require(1 <= len(candidates) <= 3 and len(group["target_ids"]) == 1, "Candidate/context inventory differs")
        source = sources[group["continuous_source_id"]]
        d.require(all(c["source_frame_index"] == lo+2 and c["target_id"] == group["target_ids"][0] for c in candidates), "Candidate target join differs")
        for offset, frame in enumerate(frames):
            target, final = offset == 2, offset == 4
            d.require(frame["role"] == ("target" if target else "context_only") and frame["continuous_source_id"] == group["continuous_source_id"], "Source/target role differs")
            displayed = [{"candidate_key": c["candidate_key"], "candidate_offset": c["candidate_offset"],
                "center_xy_px": c["center_xy_px"], "crop_xyxy": [math.floor(c["center_xy_px"][0])-64,
                    math.floor(c["center_xy_px"][1])-64, math.floor(c["center_xy_px"][0])+64, math.floor(c["center_xy_px"][1])+64],
                "label": labels[c["candidate_key"]] if proposal is not None and target else None} for c in candidates]
            duration = 18000+(108000 if target else 0)+(90000 if final else 0)
            result.append({"review_index": len(result), "group_index": group_index, "group_id": group["group_id"],
                "block_id": group["block_id"], "split_role": group["role"], "continuous_source_id": frame["continuous_source_id"],
                "source_frame_index": frame["source_frame_index"], "source_pts_ticks": frame["source_pts_ticks"],
                "source_png": frame["raw_png"], "source_size_px": [source["source_video"]["width_px"], source["source_video"]["height_px"]],
                "target_frame_index": lo+2, "target": target, "context_final": final, "candidates": displayed,
                "review_pts_ticks": tick, "duration_ticks": duration})
            tick += duration
    d.require(len(result) == len(prepared["frames"]), "Context inventory omitted frames")
    return result


def source_image(root, record):
    width, height = record["source_size_px"]
    raw = nba.read_verified_png({"png": record["source_png"]}, {"width_px": width, "height_px": height}, root)
    with Image.open(io.BytesIO(raw)) as image:
        return image.convert("RGB")


def key_bits(record):
    identity = [record[k] for k in ("group_id", "continuous_source_id", "split_role", "target", "candidates")]
    return review.key_bits(record["review_index"], record)+f"{int(review.canonical(identity)[:12],16):048b}"


def draw_panels(canvas, image, record, top, *, marked=False):
    draw = ImageDraw.Draw(canvas); view = ImageOps.contain(image, (620, 349), Image.Resampling.LANCZOS)
    left, y = 10+(620-view.width)//2, top+(349-view.height)//2
    canvas.paste(view, (left, y)); markers = []
    for j, candidate in enumerate(record["candidates"]):
        x = 650+206*j; crop = image.crop(candidate["crop_xyxy"])
        canvas.paste(crop.resize((196, 196), Image.Resampling.NEAREST), (x, top+70))
        cx, cy = candidate["center_xy_px"]
        draw.text((x, top+12), f"#{j+1} candidate {candidate['candidate_offset']}", font=review.font(18), fill="white")
        draw.text((x, top+38), f"x={cx:.1f}, y={cy:.1f}", font=review.font(16), fill="white")
        if marked:
            markers.extend([(left+cx*view.width/image.width, y+cy*view.height/image.height),
                (x+(cx-candidate["crop_xyxy"][0])*196/128, top+70+(cy-candidate["crop_xyxy"][1])*196/128)])
            label = candidate["label"]
            draw.text((x, top+280), label["classification"].replace("_", " ").upper(), font=review.font(19), fill="#ffd380")
    for x, y in markers:
        draw.line((x-8, y, x+8, y), fill="#ffb347", width=3)
        draw.line((x, y-8, x, y+8), fill="#ffb347", width=3)
    return markers


def render_frame(image, record, groups):
    canvas = Image.new("RGB", (WIDTH, HEIGHT), "#0f141d"); draw = ImageDraw.Draw(canvas)
    draw.text((14, 10), f"{record['group_index']+1}/{groups}  {record['continuous_source_id']}  |  {record['split_role'].replace('_',' ').upper()}", font=review.font(24), fill="#ffd380")
    draw.text((14, 46), f"Native frame {record['source_frame_index']} | PTS {record['source_pts_ticks']} / 90000 | 5 fps slowed review", font=review.font(20), fill="white")
    draw.text((14, 82), "TARGET: AI OBJECT PROPOSALS — HUMAN REVIEW PENDING" if record["target"] else "CONTEXT ONLY — NO OBJECT CLASS ASSIGNED", font=review.font(23), fill="#ffd380")
    draw.text((14, 125), "ORIGINAL SOURCE", font=review.font(21), fill="white")
    draw.text((650, 125), "FIXED 128 × 128 SOURCE CROPS", font=review.font(21), fill="white")
    markers = draw_panels(canvas, image, record, 165, marked=record["target"])
    draw.text((14, 560), f"Candidate locations belong to target frame {record['target_frame_index']}; crop positions stay fixed through this context.", font=review.font(20), fill="white")
    if record["target"]:
        for j, candidate in enumerate(record["candidates"]):
            subtype = f" ({candidate['label']['subtype']})" if candidate["label"]["subtype"] else ""
            draw.text((14, 602+j*30), f"#{j+1}  {candidate['candidate_key']}  |  {candidate['label']['classification'].replace('_',' ')}{subtype}", font=review.font(20), fill="white")
    draw.text((14, 740), "Orange crosses: saved candidate points, not corrected ball centers. No confidence scores displayed.", font=review.font(19), fill="white")
    draw.text((14, 775), "Target holds 1.2 extra seconds; each context final holds 1 extra second. This is slowed review.", font=review.font(18), fill="#ffd380")
    for i, bit in enumerate(key_bits(record)):
        draw.rectangle((8*i, 808, 8*i+7, 815), fill="white" if bit == "1" else "black")
    return canvas, markers


def identity(root, preparation_path, proposal_path=None):
    value = {"schema_version": SCHEMA, "preparation": d.binding(root, d.contained(root, str(preparation_path))),
        "implementation": [d.binding(root, root/"src/ball_tracking"/name) for name in
            (Path(__file__).name, "nba_annotations.py", "nba_action_review.py", "nba_gap_anchor_reference_review.py")]}
    if proposal_path is not None:
        value["proposal"] = d.binding(root, d.contained(root, str(proposal_path)))
    return value


def destination(root, output, expected):
    output = d.contained(root, str(output)); d.require(output.is_relative_to(root/"data/outputs"), "Output must remain ignored")
    if (output/"completion.json").exists():
        prior = d.read_json(output/"completion.json"); d.require(prior["identity"] == expected, "Existing completion belongs to different inputs")
        for record in prior["artifacts"].values(): d.bound(root, record)
        for item in prior.get("stills", []): d.bound(root, item["image"])
        return output, None, prior
    folder = output/"attempts"/uuid.uuid4().hex; folder.mkdir(parents=True)
    d.write_once(folder/"started.json", {"identity": expected, "at_utc": d.stamp()})
    return output, folder, None


def build_source_sheets(root, preparation_path, output):
    root = Path(root).resolve(); prepared, _ = inputs(root, preparation_path); rows = records(prepared)
    expected = {**identity(root, preparation_path), "kind": "unmarked_source_sheets"}
    output, folder, prior = destination(root, output, expected)
    if prior is not None: return prior
    try:
        stills = []
        for group_index in range(len(prepared["groups"])):
            subset = [r for r in rows if r["group_index"] == group_index]
            canvas = Image.new("RGB", (WIDTH, 2100), "#0f141d"); draw = ImageDraw.Draw(canvas)
            draw.text((14, 10), f"UNMARKED SOURCE | {subset[0]['continuous_source_id']} | {subset[0]['split_role']}", font=review.font(24), fill="white")
            for index, row in enumerate(subset):
                y = 62+index*404
                draw.text((14, y), f"Native frame {row['source_frame_index']} | PTS {row['source_pts_ticks']} / 90000 | "+("TARGET" if row["target"] else "context only"), font=review.font(22), fill="#ffd380")
                draw_panels(canvas, source_image(root, row), row, y+34)
            path = folder/f"source_context_{group_index:02d}.png"; canvas.save(path)
            stills.append({"group_id": subset[0]["group_id"], "candidate_keys": [c["candidate_key"] for c in subset[0]["candidates"]], "image": d.binding(root, path)})
        d.write_once(folder/"manifest.json", {"identity": expected, "frames": rows, "object_classes_displayed": False, "markers_displayed": False})
        result = {"status": "completed", "identity": expected, "stills": stills, "artifacts": {"manifest": d.binding(root, folder/"manifest.json")}}
        d.write_once(output/"completion.json", result); return result
    except Exception as error:
        d.write_once(folder/"failed.json", {"error_type": type(error).__name__, "error": str(error)}); raise


def verify_pixels(pixels, expected, markers, row):
    bits = "".join("1" if pixels[812, i*8+4].mean() > 127 else "0" for i in range(160))
    d.require(bits == key_bits(row), "Encoded source/candidate/class key differs")
    delta = np.abs(pixels.astype(np.int16)-np.asarray(expected).astype(np.int16))
    errors = [float(delta[:, :640].mean()), float(delta[:, 640:].mean())]
    d.require(max(errors) < 8, "Encoded source/crop pixels differ")
    for x, y in markers:
        x0,x1,y0,y1 = max(0,int(x)-10), min(WIDTH,int(x)+11), max(0,int(y)-10), min(HEIGHT,int(y)+11)
        area = np.asarray(expected)[y0:y1,x0:x1]; orange = (area[:,:,0]==255)&(area[:,:,1]==179)&(area[:,:,2]==71)
        d.require(orange.any() and float(delta[y0:y1,x0:x1][orange].mean()) < 65, "Encoded candidate marker differs")
    return errors


def render(root, preparation_path, proposal_path, output, ffmpeg=None):
    import av
    root = Path(root).resolve(); prepared, proposal = inputs(root, preparation_path, proposal_path); rows = records(prepared, proposal)
    expected = {**identity(root, preparation_path, proposal_path), "kind": "human_semantic_review"}
    output, folder, prior = destination(root, output, expected)
    if prior is not None: return prior
    began = time.monotonic(); ffmpeg = Path(ffmpeg or shutil.which("ffmpeg") or "ffmpeg")
    try:
        video = folder/"appearance_review.mp4"; durations = {r["review_pts_ticks"]: r["duration_ticks"] for r in rows}
        with av.open(str(video), "w", options={"movflags": "+faststart"}) as container:
            stream = container.add_stream("libx264", rate=5, options={"crf": "18", "preset": "fast", "bf": "0"})
            stream.width, stream.height, stream.pix_fmt = WIDTH, HEIGHT, "yuv420p"
            stream.time_base = stream.codec_context.time_base = Fraction(1,90000); stream.codec_context.thread_count = 2
            def mux(packets):
                for packet in packets:
                    d.require(packet.time_base == Fraction(1,90000) and packet.pts in durations, "Encoder changed PTS")
                    packet.duration = durations[packet.pts]; container.mux(packet)
            for row in rows:
                image, _ = render_frame(source_image(root,row), row, len(prepared["groups"]))
                frame = av.VideoFrame.from_image(image); frame.pts = row["review_pts_ticks"]; frame.time_base = Fraction(1,90000); mux(stream.encode(frame))
            mux(stream.encode())
        probe_cmd = [str(ffmpeg.with_name("ffprobe.exe" if ffmpeg.suffix.lower()==".exe" else "ffprobe")), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=time_base,duration_ts,nb_frames,width,height:frame=best_effort_timestamp,duration", "-of", "json", str(video)]
        probe = subprocess.run(probe_cmd, capture_output=True, timeout=120); (folder/"probe.stderr.txt").write_bytes(probe.stderr)
        d.require(probe.returncode==0, "Video probe failed"); metadata = json.loads(probe.stdout); total = timing.verify_probe(metadata, rows); d.write_once(folder/"probe.json", metadata)
        decode = [str(ffmpeg), "-hide_banner", "-nostdin", "-loglevel", "error", "-xerror", "-threads", "2", "-i", str(video), "-map", "0:v:0", "-an", "-fps_mode", "passthrough", "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"]
        stills, errors = [], []
        with (folder/"decode.stderr.txt").open("xb") as stderr:
            process = subprocess.Popen(decode, stdout=subprocess.PIPE, stderr=stderr)
            try:
                for row in rows:
                    raw = bytearray()
                    while len(raw) < WIDTH*HEIGHT*3:
                        chunk = process.stdout.read(WIDTH*HEIGHT*3-len(raw)); d.require(bool(chunk), "Missing encoded frame"); raw.extend(chunk)
                    pixels = np.frombuffer(raw,np.uint8).reshape(HEIGHT,WIDTH,3)
                    image, markers = render_frame(source_image(root,row), row, len(prepared["groups"])); errors.append(verify_pixels(pixels,image,markers,row))
                    if row["target"] or row["context_final"]:
                        path = folder/f"{'target' if row['target'] else 'context_final'}_{row['group_index']:02d}.png"; Image.fromarray(pixels).save(path)
                        stills.append({"review_index":row["review_index"],"group_id":row["group_id"],"kind":"target" if row["target"] else "context_final","image":d.binding(root,path)})
                    if row is rows[-1]: Image.fromarray(pixels).save(folder/"final_frame.png")
                d.require(process.stdout.read(1)==b"" and process.wait(timeout=60)==0, "Extra frame/decode error")
            finally:
                if process.poll() is None: process.kill(); process.wait(timeout=10)
                process.stdout.close()
        d.write_once(folder/"manifest.json", {"identity":expected,"frames":rows,"classes_only_on_target":True,"native_motion_pacing":False,"source_frames_per_review_second":5})
        d.write_once(folder/"verification.json", {"status":"passed","decoded_frames":len(rows),"duration_ticks":total,"all_keys_pixels_and_markers_verified":True,"panel_mae_max":[max(e[i] for e in errors) for i in (0,1)],"probe_command":probe_cmd,"decode_command":decode})
        build_guide(folder,rows,stills,total)
        result = {"status":"completed","identity":expected,"human_review":"pending","stills":stills,"elapsed_seconds":time.monotonic()-began,
            "artifacts":{name:d.binding(root,folder/file) for name,file in {"video":"appearance_review.mp4","manifest":"manifest.json","verification":"verification.json","probe":"probe.json","guide":"review.html","actual_final":"final_frame.png"}.items()}}
        d.write_once(output/"completion.json",result); return result
    except Exception as error:
        d.write_once(folder/"failed.json", {"error_type":type(error).__name__,"error":str(error),"elapsed_seconds":time.monotonic()-began}); raise


def build_guide(folder, rows, stills, total):
    import html
    cards = []
    for still in stills:
        row = rows[still["review_index"]]; notes = ""
        if row["target"]:
            notes = "".join(f"<li>{html.escape(c['candidate_key'])}: <b>{html.escape(c['label']['classification'])}</b> ({html.escape(c['label']['subtype'] or 'no subtype')}) — {html.escape(c['label']['rationale'])}</li>" for c in row["candidates"])
        filename = Path(still["image"]["path"]).name
        cards.append(f"<figure><a href='{filename}'><img loading='lazy' src='{filename}'></a><figcaption>{html.escape(row['continuous_source_id'])} frame {row['source_frame_index']} — {still['kind']}</figcaption><ul>{notes}</ul></figure>")
    text = f"<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>Candidate appearance reference review</title><style>body{{max-width:1280px;margin:20px auto;padding:0 16px;background:#0f141d;color:white;font:18px system-ui}}video,img{{width:100%}}figure{{margin:24px 0}}a{{color:#8dd5ff}}</style><h1>Candidate appearance references</h1><p>AI object proposals await human acceptance. Orange marks saved candidate points, not corrected ball centers. Context frames carry no classes. No confidence scores appear.</p><p>{len(rows)} native frames; {total/90000:.1f} seconds of slowed review. On a phone, rotate to landscape or open any still to zoom.</p><video controls preload='metadata' src='appearance_review.mp4'></video><p><a href='final_frame.png'>Actual compilation final</a></p>{''.join(cards)}</html>\n"
    (folder/"review.html").write_text(text,encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--preparation",required=True); parser.add_argument("--proposal"); parser.add_argument("--output",required=True); parser.add_argument("--ffmpeg")
    args=parser.parse_args(); root=Path(__file__).resolve().parents[2]
    result=render(root,args.preparation,args.proposal,args.output,args.ffmpeg) if args.proposal else build_source_sheets(root,args.preparation,args.output)
    print(json.dumps(result,indent=2))


if __name__=="__main__": main()
