"""Source-first inspection and complete review of bounded appearance judgments.

The renderer reads only prepared PNGs. It never loads descriptor features,
detector scores, geometric labels, or an inference model into a display record.
"""
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
import textwrap
import time
import uuid

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from . import nba_action_review as drawing
from . import nba_annotations as nba
from . import nba_wasb_diagnostic as d

SCHEMA = "nba_ball_distractor_reference_review/v0.1"
WIDTH, HEIGHT = 1280, 960
CROP = 192
ORANGE = (255, 179, 71)


def local_path(root, value):
    path = Path(value)
    if path.is_absolute():
        path = path.resolve()
        d.require(path.is_relative_to(root), "Review path escapes repository")
        path = path.relative_to(root)
    return d.contained(root, path.as_posix())


def inputs(root, preparation_path, proposal_path=None):
    from . import nba_ball_distractor_reference as authority
    path = local_path(root, preparation_path)
    prepared = authority.load_ready_preparation(root, path, verify_images=True)
    d.require(prepared == d.read_json(path), "Preparation consumer transport differs")
    proposal = None
    if proposal_path is not None:
        proposal = d.read_json(local_path(root, proposal_path))
        d.require(proposal["schema_version"] == "nba_ball_distractor_reference_proposal/v0.1", "Proposal schema differs")
        d.require(proposal["preparation"] == d.binding(root, path), "Proposal preparation binding differs")
        expected = [r["row_id"] for r in prepared["new_review_rows"]]
        d.require([r["row_id"] for r in proposal["rows"]] == expected and len(set(expected)) == len(expected), "Proposal exact row census/order differs")
        candidates = {r["candidate_group_id"]: r for r in prepared["candidates"]}
        slots = {r["slot_id"]: r for r in prepared["contrast_slots"]}
        for row in proposal["rows"]:
            d.require(row["classification"] in {"ball", "other_object", "unresolved"}, "Unknown proposal class")
            d.require(isinstance(row["rationale"], str) and row["rationale"].strip(), "Missing source rationale")
            if row["row_id"] in candidates:
                d.require(row["center_xy_px"] == candidates[row["row_id"]]["center_xy_px"], "Saved candidate center changed")
            else:
                slot = slots[row["row_id"]]
                if row["center_xy_px"] is None:
                    d.require(row["classification"] == "unresolved", "Unavailable contrast must remain unresolved")
                else:
                    d.require(row["classification"] == "other_object" and row["subtype"] == slot["requested_subtype"], "Authored contrast class/subtype changed")
            if row["classification"] != "other_object":
                d.require(row.get("subtype") is None, "Non-other row has a subtype")
            if row["classification"] != "unresolved":
                d.require(bool(row.get("physical_object_instance_id")) and bool(row.get("episode_id")), "Resolved judgment lacks grouping")
        reused = proposal.get("reused_grouping", [])
        old_keys = [r["accepted_candidate"]["candidate_key"] for r in prepared["reused_controls"]]
        d.require([r["candidate_key"] for r in reused] == old_keys, "Reused grouping census/order differs")
    return prepared, proposal


def source_groups(prepared, proposal=None):
    """Make display-only records; intentionally drop scores and old outcomes."""
    sources = {s["candidate_id"]: s for s in prepared["sources"]}
    labels = {} if proposal is None else {r["row_id"]: r for r in proposal["rows"]}
    result = []
    for group_index, group in enumerate(prepared["groups"]):
        cid = group["continuous_source_id"]
        lo, hi = group["context_range_inclusive"]
        d.require(hi-lo == 4, "Context must contain exactly five native frames")
        frames = [r for r in prepared["frames"] if r["group_id"] == group["group_id"]]
        d.require([r["source_frame_index"] for r in frames] == list(range(lo, hi+1)), "Native context inventory/order differs")
        d.require(all(r["continuous_source_id"] == cid for r in frames), "Context source identity differs")
        source = sources[cid]
        rows = []
        for candidate in prepared["candidates"]:
            if (candidate["continuous_source_id"], candidate["source_frame_index"]) != (cid, lo+2):
                continue
            rid = candidate["candidate_group_id"]
            rows.append({"row_id": rid, "origin": "saved_detector_candidate", "center_xy_px": candidate["center_xy_px"],
                         "requested_subtype": None, "label": labels.get(rid)})
        for slot in prepared["contrast_slots"]:
            if (slot["continuous_source_id"], slot["source_frame_index"]) != (cid, lo+2):
                continue
            rid = slot["slot_id"]
            rows.append({"row_id": rid, "origin": "source_authored_contrast_slot",
                         "center_xy_px": labels[rid]["center_xy_px"] if proposal is not None else None,
                         "requested_subtype": slot["requested_subtype"], "anchor_kind": slot["anchor_kind"],
                         "distance_anchor_points_xy_px": slot["distance_anchor_points_xy_px"], "label": labels.get(rid)})
        d.require(1 <= len(rows) <= 4, "Display supports one to four rows per native target")
        size = [source["source_video"]["width_px"], source["source_video"]["height_px"]]
        for row in rows:
            center = row["center_xy_px"]
            if center is not None:
                d.require(len(center) == 2 and all(math.isfinite(v) for v in center) and 0 <= center[0] < size[0] and 0 <= center[1] < size[1], "Review point outside source")
        result.append({"group_index": group_index, "group_id": group["group_id"], "continuous_source_id": cid,
                       "block_id": group["block_id"], "role": group["role"], "target_frame_index": lo+2,
                       "source_size_px": size, "frames": frames, "rows": rows})
    actual = [r["row_id"] for g in result for r in g["rows"]]
    expected = [r["row_id"] for r in prepared["new_review_rows"]]
    d.require(len(actual) == len(expected) and set(actual) == set(expected), "Display omitted or duplicated a review row")
    d.require(sum(len(g["frames"]) for g in result) == len(prepared["frames"]), "Display omitted context frames")
    return result


def source_image(root, group, frame):
    raw = nba.read_verified_png({"png": frame["raw_png"]},
        {"width_px": group["source_size_px"][0], "height_px": group["source_size_px"][1]}, root)
    with Image.open(io.BytesIO(raw)) as image:
        return image.convert("RGB")


def crop_box(center):
    x, y = (math.floor(v) for v in center)
    return [x-CROP//2, y-CROP//2, x+CROP//2, y+CROP//2]


def fit_image(canvas, image, box):
    x, y, width, height = box
    view = ImageOps.contain(image, (width, height), Image.Resampling.LANCZOS)
    left, top = x+(width-view.width)//2, y+(height-view.height)//2
    canvas.paste(view, (left, top))
    return left, top, view.width/image.width, view.height/image.height


def lines(draw, xy, value, width, size=16, fill="white", limit=None):
    wrapped = textwrap.wrap(str(value), width=width, break_long_words=True, break_on_hyphens=False) or [""]
    if limit is not None and len(wrapped) > limit:
        wrapped = wrapped[:limit]; wrapped[-1] = wrapped[-1][:-1]+"…"
    for i, line in enumerate(wrapped):
        draw.text((xy[0], xy[1]+i*(size+4)), line, font=drawing.font(size), fill=fill)


def source_sheet(root, group):
    """No marks or object judgments; contrast crops show distance anchors only."""
    canvas = Image.new("RGB", (1280, 844+284*len(group["rows"])), "#0f141d")
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 10), f"SOURCE ONLY | {group['continuous_source_id']} | target {group['target_frame_index']} | {group['role']}", font=drawing.font(24), fill="white")
    draw.text((12, 42), "Unmarked original pixels. Rows refer to the middle frame; no model scores, geometry outcomes, or classes.", font=drawing.font(18), fill="#ffd380")
    images = [source_image(root, group, f) for f in group["frames"]]
    fit_image(canvas, images[2], (160, 76, 960, 540))
    draw.text((12, 620), "Full target above; all five consecutive native source frames below. Open original PNG links for native resolution.", font=drawing.font(18), fill="white")
    for j, (frame, image) in enumerate(zip(group["frames"], images, strict=True)):
        x = 10+j*254
        draw.text((x, 650), f"Frame {frame['source_frame_index']}"+(" TARGET" if j == 2 else ""), font=drawing.font(18), fill="#ffd380")
        fit_image(canvas, image, (x, 680, 244, 138))
    crop_records = []
    for row_index, row in enumerate(group["rows"]):
        y = 838+row_index*284
        center = row["center_xy_px"]
        if center is None:
            anchors = row["distance_anchor_points_xy_px"]
            d.require(len(anchors) == 1, "Source sheet needs exactly one frozen distance anchor per contrast slot")
            center = anchors[0]
            description = f"PLANNED {row['requested_subtype']} | distance anchor only, NOT authored object center"
        else:
            description = "SAVED DETECTOR POINT | fixed 192 × 192 source crop"
        draw.text((12, y), f"{row_index+1}. {row['row_id']}", font=drawing.font(19), fill="white")
        draw.text((12, y+27), f"{description} | x={center[0]:3.3f}, y={center[1]:3.3f}", font=drawing.font(17), fill="#ffd380")
        box = crop_box(center); placements = []
        for j, image in enumerate(images):
            x = 24+j*254
            canvas.paste(image.crop(box).resize((224,224), Image.Resampling.NEAREST), (x,y+56))
            placements.append([x,y+56,x+224,y+280])
        crop_records.append({"row_id": row["row_id"], "center_kind": "distance_anchor" if row["center_xy_px"] is None else "saved_candidate",
                             "center_xy_px": center, "crop_xyxy_px": box, "sheet_crop_boxes": placements})
    return canvas, crop_records


def identity(root, preparation_path, proposal_path=None):
    value = {"schema_version": SCHEMA, "preparation": d.binding(root, local_path(root, preparation_path)),
             "implementation": [d.binding(root, root/"src/ball_tracking"/name) for name in
                (Path(__file__).name, "nba_annotations.py", "nba_action_review.py", "nba_wasb_diagnostic.py")]}
    if proposal_path is not None:
        value["proposal"] = d.binding(root, local_path(root, proposal_path))
    return value


def destination(root, output, expected):
    output = local_path(root, output)
    d.require(output.is_relative_to(root/"data/outputs"), "Review output must remain ignored")
    if (output/"completion.json").exists():
        prior = d.read_json(output/"completion.json")
        d.require(prior["identity"] == expected, "Existing completion belongs to different inputs")
        for binding in prior["artifacts"].values():
            d.bound(root, binding)
        for still in prior.get("stills", []):
            d.bound(root, still["image"])
        return output, None, prior
    folder = output/"attempts"/uuid.uuid4().hex
    folder.mkdir(parents=True)
    d.write_once(folder/"started.json", {"identity": expected, "at_utc": d.stamp()})
    return output, folder, None


def _html_page(title, body):
    return ("<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
        f"<title>{html.escape(title)}</title><style>body{{max-width:1280px;margin:20px auto;padding:0 16px;background:#0f141d;color:white;font:18px system-ui}}"
        "video,img{max-width:100%;height:auto}figure{margin:24px 0}a{color:#8dd5ff}td,th{padding:8px;border:1px solid #555;vertical-align:top}table{border-collapse:collapse;width:100%}code{overflow-wrap:anywhere}</style>"
        f"<h1>{html.escape(title)}</h1>{body}</html>\n")


def build_source_sheets(root, preparation_path, output):
    root = Path(root).resolve(); prepared, _ = inputs(root, preparation_path)
    groups = source_groups(prepared)
    expected = {**identity(root, preparation_path), "kind": "source_only_sheets"}
    output, folder, prior = destination(root, output, expected)
    if prior is not None:
        return prior
    began = time.monotonic()
    try:
        stills = []
        # NFHS is prepared first so its independent annotator can begin promptly.
        order = sorted(groups, key=lambda g: (not g["continuous_source_id"].startswith("possession_"), g["group_index"]))
        for group in order:
            canvas, crops = source_sheet(root, group)
            path = folder/f"source_context_{group['group_index']:03d}.png"; canvas.save(path)
            record = {k: group[k] for k in ("group_index", "group_id", "continuous_source_id", "block_id", "role", "target_frame_index")}
            record.update({"row_ids": [r["row_id"] for r in group["rows"]], "frames": group["frames"],
                           "crop_records": crops, "image": d.binding(root, path)})
            stills.append(record)
            d.write_once(folder/f"source_context_{group['group_index']:03d}.json", record)
        stills.sort(key=lambda s: s["group_index"])
        batches = []
        for start in range(0, len(stills), 8):
            batch = stills[start:start+8]; name = f"batch_{start//8:02d}.html"
            body = "<p>Source-only inspection. No model outcomes or class judgments. Contrast crops identify only the frozen distance anchor.</p>"
            for still in batch:
                source_links = " · ".join(f"<a href='{html.escape(Path(root/f['raw_png']['path']).as_uri())}'>original {f['source_frame_index']}</a>" for f in still["frames"])
                body += f"<figure><a href='{Path(still['image']['path']).name}'><img loading='lazy' src='{Path(still['image']['path']).name}'></a><figcaption>{html.escape(still['group_id'])}</figcaption><p>{source_links}</p></figure>"
            (folder/name).write_text(_html_page(f"Source contexts {start+1}–{start+len(batch)}", body), encoding="utf-8")
            batches.append({"first_group_index": start, "group_ids": [s["group_id"] for s in batch], "html": d.binding(root, folder/name)})
        links = "".join(f"<li><a href='{Path(b['html']['path']).name}'>Contexts {b['first_group_index']+1}–{b['first_group_index']+len(b['group_ids'])}</a></li>" for b in batches)
        (folder/"source_review.html").write_text(_html_page("Bounded source inspection", f"<p>{len(groups)} targets; {len(prepared['new_review_rows'])} planned judgments; {len(prepared['frames'])} source frames. Classes and scores are absent. Each source point is fixed to its target frame.</p><ol>{links}</ol>"), encoding="utf-8")
        d.write_once(folder/"manifest.json", {"identity": expected, "groups": stills, "batches": batches,
            "object_classes_displayed": False, "markers_displayed": False, "model_scores_displayed": False, "geometric_outcomes_displayed": False})
        artifacts = {"manifest": d.binding(root, folder/"manifest.json"), "guide": d.binding(root, folder/"source_review.html")}
        artifacts.update({f"batch_{i:02d}": b["html"] for i,b in enumerate(batches)})
        result = {"status": "completed", "identity": expected, "stills": stills, "artifacts": artifacts, "elapsed_seconds": time.monotonic()-began}
        d.write_once(output/"completion.json", result)
        return result
    except Exception as error:
        d.write_once(folder/"failed.json", {"error_type": type(error).__name__, "error": str(error), "elapsed_seconds": time.monotonic()-began})
        raise


def records(groups):
    result, tick = [], 0
    for group in groups:
        for offset, frame in enumerate(group["frames"]):
            target, final = offset == 2, offset == 4
            duration = 18000+(108000 if target else 0)+(90000 if final else 0)
            row = {k: v for k,v in group.items() if k != "frames"}
            row.update({"review_index": len(result), "source_frame": frame, "source_frame_index": frame["source_frame_index"],
                        "source_pts_ticks": frame["source_pts_ticks"], "review_pts_ticks": tick, "duration_ticks": duration,
                        "target": target, "context_final": final})
            # Context carries geometry for the fixed crops, not a class assertion.
            row["rows"] = [{**r, "label": r["label"] if target else None} for r in group["rows"]]
            result.append(row); tick += duration
    return result


def key_bits(record):
    return f"{int(drawing.canonical(record)[:40],16):0160b}"


def cross(draw, point, index=None):
    x,y = point
    draw.line((x-7,y,x+7,y), fill=ORANGE, width=3)
    draw.line((x,y-7,x,y+7), fill=ORANGE, width=3)
    if index is not None:
        draw.text((x+8,y+5), str(index), font=drawing.font(16), fill=ORANGE)


def render_frame(image, record, group_count):
    canvas = Image.new("RGB", (WIDTH,HEIGHT), "#0f141d"); draw = ImageDraw.Draw(canvas)
    draw.text((12,8), f"{record['group_index']+1}/{group_count} | {record['continuous_source_id']} | {record['role']} | native frame {record['source_frame_index']}", font=drawing.font(23), fill="#ffd380")
    origin = record["source_frame"].get("time_origin", "native_source")
    clock = "clip-relative" if origin == "clip_first_frame" else "native source"
    draw.text((12,42), f"{clock} PTS {record['source_pts_ticks']} / 90000 | "+("TARGET — AI PROPOSALS; HUMAN REVIEW PENDING" if record["target"] else "CONTEXT ONLY — NO CLASS ASSIGNED"), font=drawing.font(19), fill="white")
    draw.text((12,78), "CLEAN SOURCE", font=drawing.font(19), fill="white")
    draw.text((650,78), "TARGET POINTS" if record["target"] else "CLEAN CONTEXT", font=drawing.font(19), fill="white")
    fit_image(canvas, image, (10,108,620,349))
    transform = fit_image(canvas, image, (650,108,620,349)); markers = []
    for j,row in enumerate(record["rows"]):
        center = row["center_xy_px"]; x = 10+j*318
        lines(draw, (x,484), f"{j+1}. {row['row_id']}", 33, 15, limit=2)
        draw.text((x,528), "DETECTOR POINT" if row["origin"] == "saved_detector_candidate" else "AUTHORED CONTRAST", font=drawing.font(16), fill="#ffd380")
        draw.text((x,552), "clean 192px" , font=drawing.font(15), fill="white")
        draw.text((x+156,552), "marked target" if record["target"] else "clean context", font=drawing.font(15), fill="white")
        if center is not None:
            box = crop_box(center); crop = image.crop(box).resize((144,144), Image.Resampling.NEAREST)
            canvas.paste(crop, (x,580)); canvas.paste(crop, (x+156,580))
            if record["target"]:
                point = (transform[0]+center[0]*transform[2],transform[1]+center[1]*transform[3])
                cross(draw,point,j+1); markers.append(point)
                point = (x+156+(center[0]-box[0])*144/CROP,580+(center[1]-box[1])*144/CROP)
                cross(draw,point); markers.append(point)
            draw.text((x,730), f"x={center[0]:.2f}, y={center[1]:.2f}", font=drawing.font(15), fill="white")
        else:
            draw.rectangle((x,580,x+300,724),fill="#252b35")
            lines(draw,(x+10,620),"Unavailable contrast: no authored point or crop",28,17)
        label = row["label"]
        if label is not None:
            text = label["classification"].replace("_"," ")+(f" / {label['subtype']}" if label.get("subtype") else "")
            lines(draw,(x,762),text,30,18,fill="#ffd380",limit=2)
            lines(draw,(x,810),"Object: "+str(label.get("physical_object_instance_id") or "unresolved"),38,13,limit=2)
            lines(draw,(x,848),"Episode: "+str(label.get("episode_id") or "unresolved"),38,13,limit=2)
    draw.text((12,899), f"Fixed crop positions belong to target {record['target_frame_index']}; context is slowed to 5 native frames/s.",font=drawing.font(18),fill="white")
    draw.text((12,926), "Orange crosses identify saved or separately authored points. Exact rationale and full group IDs are in the HTML.",font=drawing.font(17),fill="#ffd380")
    for i,bit in enumerate(key_bits(record)):
        draw.rectangle((i*8,952,i*8+7,959),fill="white" if bit == "1" else "black")
    return canvas, markers


def verify_pixels(pixels, expected, markers, record):
    bits = "".join("1" if pixels[956,i*8+4].mean() > 127 else "0" for i in range(160))
    d.require(bits == key_bits(record), "Encoded source/row/class identity differs")
    delta = np.abs(pixels.astype(np.int16)-np.asarray(expected).astype(np.int16))
    errors = [float(delta[:, :640].mean()), float(delta[:,640:].mean())]
    d.require(max(errors) < 8, "Encoded source/crop panel differs")
    for x,y in markers:
        x0,x1,y0,y1 = max(0,int(x)-9),min(WIDTH,int(x)+10),max(0,int(y)-9),min(HEIGHT,int(y)+10)
        area = np.asarray(expected)[y0:y1,x0:x1]
        mask = np.all(area == ORANGE,axis=2)
        d.require(mask.any() and float(delta[y0:y1,x0:x1][mask].mean()) < 65, "Encoded target marker differs")
    return errors


def verify_probe(probe, rows):
    d.require(len(probe["streams"]) == 1, "Expected one video stream")
    stream = probe["streams"][0]; total = sum(r["duration_ticks"] for r in rows)
    d.require((stream["width"],stream["height"],stream["time_base"]) == (WIDTH,HEIGHT,"1/90000"), "Video geometry/time base differs")
    d.require(int(stream["nb_frames"]) == len(rows) and int(stream["duration_ts"]) == total, "Encoded count or final hold differs")
    d.require(len(probe["frames"]) == len(rows), "Probed frame census differs")
    for actual,row in zip(probe["frames"],rows,strict=True):
        d.require(int(actual["best_effort_timestamp"]) == row["review_pts_ticks"] and int(actual["duration"]) == row["duration_ticks"], "Encoded frame timing differs")
    return total


def build_guide(folder, prepared, proposal, groups, stills, total):
    by_group = {}
    for still in stills:
        by_group.setdefault(still["group_id"],{})[still["kind"]] = Path(still["image"]["path"]).name
    body = (f"<p>AI proposals await human acceptance. {len(groups)} targets; {len(proposal['rows'])} new judgments; "
        f"{len(prepared['frames'])} context frames; {total/90000:.1f} seconds of slowed review. The old accepted26 classes remain separate.</p>"
        "<p>Orange crosses show detector points or separately authored contrast points. Crops stay at the target position through five native frames. Unresolved is not a negative label.</p>"
        "<video controls preload='metadata' src='reference_review.mp4'></video><p><a href='final_frame.png'>Actual video final</a></p>")
    for group in groups:
        images = by_group[group["group_id"]]
        body += f"<section><h2>{html.escape(group['group_id'])} — {html.escape(group['role'])}</h2><a href='{images['target']}'><img loading='lazy' src='{images['target']}'></a><p><a href='{images['context_final']}'>Actual final context frame</a></p><table><tr><th>Row / origin</th><th>Judgment</th><th>Grouping</th><th>Source rationale</th></tr>"
        for row in group["rows"]:
            label = row["label"]
            grouping = f"Object: {label.get('physical_object_instance_id')} | Episode: {label.get('episode_id')} | Duplicate: {label.get('duplicate_of_row_id')}"
            body += f"<tr><td><code>{html.escape(row['row_id'])}</code><br>{row['origin']}</td><td>{label['classification']}<br>{html.escape(str(label.get('subtype') or ''))}<br>{html.escape(str(row['center_xy_px']))}</td><td>{html.escape(grouping)}</td><td>{html.escape(label['rationale'])}</td></tr>"
        body += "</table></section>"
    body += "<h2>Existing accepted26: grouping supplement only</h2><p>These classes were already accepted. This proposal adds explicit object/episode grouping; it does not relabel them.</p><table><tr><th>Candidate</th><th>Accepted class</th><th>Proposed grouping / rationale</th></tr>"
    for control,grouping in zip(prepared["reused_controls"],proposal["reused_grouping"],strict=True):
        key = control["accepted_candidate"]["candidate_key"]
        body += f"<tr><td><code>{html.escape(key)}</code></td><td>{html.escape(control['accepted_row']['classification'])}</td><td>{html.escape(json.dumps(grouping,ensure_ascii=False))}</td></tr>"
    body += "</table>"
    (folder/"review.html").write_text(_html_page("Bounded ball/distractor reference proposals",body),encoding="utf-8")


def render(root, preparation_path, proposal_path, output, ffmpeg=None):
    import av
    root = Path(root).resolve(); prepared, proposal = inputs(root,preparation_path,proposal_path)
    groups = source_groups(prepared,proposal); rows = records(groups)
    expected = {**identity(root,preparation_path,proposal_path),"kind":"proposal_review"}
    output,folder,prior = destination(root,output,expected)
    if prior is not None:
        return prior
    began = time.monotonic(); ffmpeg = Path(ffmpeg or shutil.which("ffmpeg") or "ffmpeg")
    try:
        video = folder/"reference_review.mp4"; durations = {r["review_pts_ticks"]:r["duration_ticks"] for r in rows}
        with av.open(str(video),"w",options={"movflags":"+faststart"}) as container:
            stream = container.add_stream("libx264",rate=5,options={"crf":"18","preset":"fast","bf":"0"})
            stream.width,stream.height,stream.pix_fmt = WIDTH,HEIGHT,"yuv420p"
            stream.time_base = stream.codec_context.time_base = Fraction(1,90000); stream.codec_context.thread_count = 2
            def mux(packets):
                for packet in packets:
                    d.require(packet.time_base == Fraction(1,90000) and packet.pts in durations,"Encoder changed PTS")
                    packet.duration = durations[packet.pts]; container.mux(packet)
            for row in rows:
                canvas,_ = render_frame(source_image(root,row,row["source_frame"]),row,len(groups))
                frame = av.VideoFrame.from_image(canvas); frame.pts = row["review_pts_ticks"]; frame.time_base = Fraction(1,90000)
                mux(stream.encode(frame))
            mux(stream.encode())
        ffprobe = ffmpeg.with_name("ffprobe.exe" if ffmpeg.suffix.lower() == ".exe" else "ffprobe")
        probe_cmd = [str(ffprobe),"-v","error","-select_streams","v:0","-show_entries","stream=time_base,duration_ts,nb_frames,width,height:frame=best_effort_timestamp,duration","-of","json",str(video)]
        probe = subprocess.run(probe_cmd,capture_output=True,timeout=120); (folder/"probe.stderr.txt").write_bytes(probe.stderr)
        d.require(probe.returncode == 0,"Video probe failed"); metadata = json.loads(probe.stdout)
        total = verify_probe(metadata,rows); d.write_once(folder/"probe.json",metadata)
        command = [str(ffmpeg),"-hide_banner","-nostdin","-loglevel","error","-xerror","-threads","2","-i",str(video),"-map","0:v:0","-an","-fps_mode","passthrough","-pix_fmt","rgb24","-f","rawvideo","pipe:1"]
        stills,errors = [],[]
        with (folder/"decode.stderr.txt").open("xb") as stderr:
            process = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=stderr)
            try:
                for row in rows:
                    raw = bytearray()
                    while len(raw) < WIDTH*HEIGHT*3:
                        chunk = process.stdout.read(WIDTH*HEIGHT*3-len(raw)); d.require(bool(chunk),"Missing encoded frame"); raw.extend(chunk)
                    pixels = np.frombuffer(raw,np.uint8).reshape(HEIGHT,WIDTH,3)
                    canvas,markers = render_frame(source_image(root,row,row["source_frame"]),row,len(groups))
                    errors.append(verify_pixels(pixels,canvas,markers,row))
                    if row["target"] or row["context_final"]:
                        kind = "target" if row["target"] else "context_final"
                        path = folder/f"{kind}_{row['group_index']:03d}.png"; Image.fromarray(pixels).save(path)
                        stills.append({"review_index":row["review_index"],"group_id":row["group_id"],"kind":kind,"image":d.binding(root,path)})
                    if row is rows[-1]:
                        Image.fromarray(pixels).save(folder/"final_frame.png")
                d.require(process.stdout.read(1) == b"" and process.wait(timeout=60) == 0,"Extra encoded frame/decode failure")
            finally:
                if process.poll() is None:
                    process.kill(); process.wait(timeout=10)
                process.stdout.close()
        d.write_once(folder/"manifest.json",{"identity":expected,"frames":rows,"classes_only_on_targets":True,
            "new_judgments":proposal["rows"],"reused_grouping":proposal["reused_grouping"],"source_frames_per_review_second":5})
        d.write_once(folder/"verification.json",{"status":"passed","decoded_frames":len(rows),"target_frames":len(groups),
            "new_review_rows":len(proposal["rows"]),"context_finals":len(groups),"duration_ticks":total,
            "all_frame_keys_pixels_and_markers_verified":True,"panel_mae_max":[max(e[i] for e in errors) for i in (0,1)],
            "probe_command":probe_cmd,"decode_command":command})
        build_guide(folder,prepared,proposal,groups,stills,total)
        result = {"status":"completed","identity":expected,"human_review":"pending","stills":stills,"elapsed_seconds":time.monotonic()-began,
            "artifacts":{name:d.binding(root,folder/file) for name,file in {"video":"reference_review.mp4","manifest":"manifest.json",
                "verification":"verification.json","probe":"probe.json","guide":"review.html","actual_final":"final_frame.png"}.items()}}
        d.write_once(output/"completion.json",result)
        return result
    except Exception as error:
        d.write_once(folder/"failed.json",{"error_type":type(error).__name__,"error":str(error),"elapsed_seconds":time.monotonic()-began})
        raise


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--preparation",required=True); parser.add_argument("--proposal")
    parser.add_argument("--output",required=True); parser.add_argument("--ffmpeg"); args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    result = render(root,args.preparation,args.proposal,args.output,args.ffmpeg) if args.proposal else build_source_sheets(root,args.preparation,args.output)
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
