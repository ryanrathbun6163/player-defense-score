"""Native-paced comparison of saved emissions and a separate provisional veto.

The original continuous renderer owns source validation and guarded decoding.
This consumer changes only the displayed pair and its visible transport key.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import html
import json
import math
import os
from pathlib import Path
import subprocess
import time
import uuid
from urllib.parse import quote

import numpy as np
from PIL import Image, ImageDraw

from . import nba_temporal_gap_continuous_review as original
from . import nba_action_review as review
from . import nba_wasb_diagnostic as d
from . import wasb_experiment as wasb
from . import nba_ball_distractor_policy as policy_authority

SCHEMA = "nba_ball_distractor_review/v0.1"
TITLES = ("ORIGINAL SAVED OUTPUT", "PROVISIONAL APPEARANCE VETO")
WIDTH, HEIGHT = original.WIDTH, original.HEIGHT


def map_source(source, policy_rows):
    """Join every permitted decision; no added or relocated point is allowed."""
    index = {}
    for row in policy_rows:
        key = (row["candidate_id"], row["source_frame_index"])
        d.require(key not in index, "Duplicate policy frame")
        index[key] = row
    expected = {(source["candidate_id"], r["source_frame_index"]) for r in source["frames"]
                if r["decision"] != "withheld"}
    d.require(set(index) == expected, "Policy/source permitted census differs")
    rows = []
    for old in source["frames"]:
        saved = old["selected_center_xy_px"]
        if old["decision"] == "withheld":
            rows.append({**old, "baseline_center_xy_px": None, "selected_center_xy_px": None,
                         "policy_decision": "withheld", "logit": None})
            continue
        policy = index[(source["candidate_id"], old["source_frame_index"])]
        d.require(policy["source_pts_ticks"] == old["source_pts_ticks"], "Policy native PTS differs")
        emission = policy["saved_emission"]
        d.require(emission == policy_authority.emission(old),
                  "Policy saved emission differs from original")
        selected = policy["selected_center_xy_px"]
        d.require(selected is None or selected == saved, "Veto added or relocated an original point")
        d.require(all(policy[field] == (emission[field] if selected is not None else None)
                      for field in policy_authority.EMISSION_FIELDS), "Policy changed retained component provenance")
        logit = policy["logit"]
        if saved is None:
            d.require(selected is None and logit is None, "Missing original gained a score or point")
            d.require(policy["policy_decision"] == "original_missing", "Missing original decision differs")
            decision = "missing"
        else:
            d.require(type(logit) in (int, float) and math.isfinite(logit), "Emission has no finite policy logit")
            if old["decision"] == "preserved_original":
                d.require((selected is not None) == (logit >= 0)
                          and policy["policy_decision"] == ("retained_original" if selected is not None else "vetoed_original"),
                          "Original veto differs from frozen negative-logit boundary")
            else:
                d.require(policy["policy_decision"] == ("retained_gap_fill" if selected is not None else "revoked_gap_fill")
                          and (selected is None or logit > 0), "Saved gap policy differs")
            decision = "kept" if selected is not None else "suppressed"
        d.require(policy["removed"] == (saved is not None and selected is None), "Policy removal flag differs")
        rows.append({**old, "baseline_center_xy_px": saved, "selected_center_xy_px": selected,
                     "decision": decision, "policy_decision": policy["policy_decision"], "logit": logit})
    return {**source, "frames": rows}


def pair_bits(row):
    identity = [TITLES, row["baseline_center_xy_px"], row["selected_center_xy_px"], row["decision"]]
    return f"{int(wasb.canonical(identity)[:8], 16):032b}"


def iter_images(root, mapped_source):
    """Reuse protected-aware readers, then replace all policy-specific labels."""
    images = original.iter_images(root, mapped_source)
    try:
        for index, (row, image) in enumerate(zip(mapped_source["frames"], images, strict=True)):
            draw = ImageDraw.Draw(image)
            background = "black" if row["decision"] == "withheld" else (15, 20, 29)
            draw.rectangle((0, 26, WIDTH-1, 95), fill=background)
            draw.text((12, 28), "Experimental veto failed checks | human labels and trajectory review pending",
                      fill="#ffd380", font=review.font(15))
            states = ("WITHHELD", "WITHHELD") if row["decision"] == "withheld" else (
                "SAVED POINT" if row["baseline_center_xy_px"] is not None else "MISSING",
                "KEPT" if row["decision"] == "kept" else "SUPPRESSED" if row["decision"] == "suppressed" else "MISSING")
            for panel in (0, 1):
                d.require(draw.textlength(TITLES[panel],font=review.font(20)) < 616,"Review panel title clipped")
                draw.text((panel*640+12, 48), TITLES[panel], fill="#ffd380", font=review.font(20))
                draw.text((panel*640+12, 73), states[panel], fill="#ffd380", font=review.font(12))
            bits = review.key_bits(index, row)+pair_bits(row)
            for i, bit in enumerate(bits):
                draw.rectangle((i*8, 808, i*8+7, 815), fill="white" if bit == "1" else "black")
            yield image
    finally:
        images.close()


def pixel_signature(image):
    """Compact paired pixel evidence saved at the only source-rendering pass."""
    if not isinstance(image, Image.Image):
        image = Image.fromarray(image)
    return np.stack([np.asarray(image.crop((p*640, 0, (p+1)*640, HEIGHT)).resize((32,32), Image.Resampling.BOX))
                     for p in (0,1)])


def verify_pixels(decoded, expected_signature, row, index):
    bits = "".join("1" if decoded[812, i*8+4].mean() > 127 else "0" for i in range(144))
    d.require(bits == review.key_bits(index, row)+pair_bits(row), "Decoded native frame or veto pair key differs")
    delta = np.abs(pixel_signature(decoded).astype(np.int16)-expected_signature.astype(np.int16))
    errors = [float(delta[p].mean()) for p in (0, 1)]
    d.require(max(errors) < 8, "Decoded original/veto paired pixels differ")
    if row["decision"] == "withheld":
        d.require(int(decoded[96:776].max()) <= 3, "Protected panels are not black")
    return errors


def changed_episodes(rows):
    """Consecutive suppressed runs, split at missing/protected/segment boundaries."""
    runs = []
    for i, row in enumerate(rows):
        if row["decision"] != "suppressed":
            continue
        if not runs or i != runs[-1][-1]+1 or row["segment_id"] != rows[runs[-1][-1]]["segment_id"]:
            runs.append([])
        runs[-1].append(i)
    return [{"episode_index": n, "segment_id": rows[run[0]]["segment_id"],
             "source_range_inclusive": [rows[run[0]]["source_frame_index"], rows[run[-1]]["source_frame_index"]],
             "suppressed_frames": len(run), "review_indices": [run[0], run[-1]],
             "representative_review_index": run[len(run)//2],
             "source_pts_ticks": [rows[run[0]]["source_pts_ticks"], rows[run[-1]]["source_pts_ticks"]]}
            for n, run in enumerate(runs)]


def render_source(root, source, policy_rows, ffmpeg, output, bindings):
    import av
    root, output = Path(root).resolve(), Path(output).resolve()
    d.require(output.is_relative_to(root/"data/outputs"), "Review output must remain ignored")
    records = original.validate_source(root, source)
    mapped = map_source(source, policy_rows)
    rows = mapped["frames"]
    for record, row in zip(records, rows, strict=True):
        record.update(decision=row["decision"], policy_decision=row["policy_decision"],
                      original_center_xy_px=row["baseline_center_xy_px"], selected_center_xy_px=row["selected_center_xy_px"],
                      logit=row["logit"], original_provenance_id=row.get("selected_provenance_id"))
    episodes = changed_episodes(rows)
    identity = {"schema_version": SCHEMA, "original_source_sha256": wasb.canonical(source),
                "policy_rows_sha256": wasb.canonical(policy_rows), "bindings": bindings,
                "renderer_sha256": d.digest(Path(__file__)), "source_renderer_sha256": d.digest(Path(original.__file__)),
                "source_reader_sha256": d.digest(Path(original.nba.__file__)),
                "nfhs_helpers_sha256": d.digest(Path(original.observation.__file__)),
                "display_helpers_sha256": d.digest(Path(review.__file__)),
                "policy_transport_sha256": d.digest(Path(policy_authority.__file__)),
                "panel_titles": TITLES, "final_hold_ticks": original.HOLD_TICKS}
    # JSON roundtrip makes tuple/list identity equality stable on resume.
    identity = json.loads(json.dumps(identity))
    parent = output/"attempts"
    for path in sorted(parent.glob("*/completion.json")) if parent.exists() else []:
        saved = d.read_json(path)
        if saved["identity"] == identity:
            for item in saved["artifacts"].values(): d.bound(root, item)
            for item in saved["changed_episodes"]+saved["segment_final_frames"]: d.bound(root, item["image"])
            for episode in saved["changed_episodes"]:
                for item in episode["boundary_images"]: d.bound(root, item["image"])
            return {**saved["artifacts"], "changed_episodes": saved["changed_episodes"],
                    "segment_final_frames": saved["segment_final_frames"], "completion": d.binding(root, path)}
    folder = parent/uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=False)
    d.write_once(folder/"started.json", {"identity": identity, "at_utc": d.stamp()})
    began = time.monotonic()
    try:
        video = folder/"comparison.mp4"
        durations = {r["review_pts_ticks"]: r["duration_ticks"] for r in records}
        signatures = []
        with av.open(str(video), "w", options={"movflags": "+faststart"}) as container:
            stream = container.add_stream("libx264", rate=25 if source["kind"] == "nfhs" else Fraction(60000,1001),
                                          options={"crf":"18", "preset":"fast", "bf":"0"})
            stream.width, stream.height, stream.pix_fmt = WIDTH, HEIGHT, "yuv420p"
            stream.time_base = stream.codec_context.time_base = Fraction(1,90000)
            stream.codec_context.thread_count = 2
            def mux(packets):
                for packet in packets:
                    d.require(packet.time_base == Fraction(1,90000) and packet.pts in durations, "Encoder PTS changed")
                    packet.duration = durations[packet.pts]; container.mux(packet)
            images = iter_images(root, mapped)
            try:
                for record, image in zip(records, images, strict=True):
                    signatures.append(pixel_signature(image))
                    frame = av.VideoFrame.from_image(image); frame.pts = record["review_pts_ticks"]
                    frame.time_base = Fraction(1,90000); mux(stream.encode(frame))
                mux(stream.encode())
            finally: images.close()
        signatures=np.stack(signatures)
        np.savez_compressed(folder/"pixel_signatures.npz", panels=signatures)
        ffprobe = Path(ffmpeg).with_name("ffprobe.exe" if Path(ffmpeg).suffix.lower()==".exe" else "ffprobe")
        probe_command = [str(ffprobe),"-v","error","-select_streams","v:0","-show_entries",
                         "stream=time_base,duration_ts,nb_frames,width,height:frame=best_effort_timestamp,duration",
                         "-of","json",str(video)]
        probed = subprocess.run(probe_command,capture_output=True,check=False,timeout=180)
        (folder/"ffprobe.stderr.txt").write_bytes(probed.stderr)
        d.require(probed.returncode==0,"Review probe failed")
        probe=json.loads(probed.stdout); d.write_once(folder/"ffprobe.json",probe)
        total=original.verify_probe(probe,records)
        command=[str(ffmpeg),"-hide_banner","-nostdin","-loglevel","error","-xerror","-threads","2",
                 "-i",str(video),"-map","0:v:0","-an","-fps_mode","passthrough","-pix_fmt","rgb24","-f","rawvideo","pipe:1"]
        errors, finals = [], []
        representative = {e["representative_review_index"]: e for e in episodes}
        boundaries = {}
        for episode in episodes:
            episode["boundary_images"]=[]
            for i in sorted(set(episode["review_indices"])):
                boundaries[i]=episode
        segment_ends = {s["range_inclusive"][1] for s in source["segments"]}
        with (folder/"decode.stderr.txt").open("xb") as stderr:
            process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=stderr)
            try:
                for record,row,expected in zip(records,rows,signatures,strict=True):
                    raw=bytearray()
                    while len(raw)<WIDTH*HEIGHT*3:
                        chunk=process.stdout.read(WIDTH*HEIGHT*3-len(raw));d.require(bool(chunk),"Missing decoded review frame");raw.extend(chunk)
                    decoded=np.frombuffer(raw,np.uint8).reshape(HEIGHT,WIDTH,3)
                    i=record["review_index"]; errors.append(verify_pixels(decoded,expected,row,i))
                    if i in representative:
                        path=folder/f"changed_episode_{representative[i]['episode_index']:04d}.png";Image.fromarray(decoded).save(path)
                        representative[i].update(image=d.binding(root,path),representative_source_frame_index=row["source_frame_index"],
                                                  review_seconds=record["review_pts_ticks"]/90000)
                    if i in boundaries:
                        path=folder/f"changed_boundary_{row['source_frame_index']:06d}.png";Image.fromarray(decoded).save(path)
                        boundaries[i]["boundary_images"].append({"source_frame_index":row["source_frame_index"],"image":d.binding(root,path)})
                    if row["source_frame_index"] in segment_ends:
                        path=folder/f"segment_final_{row['source_frame_index']:06d}.png";Image.fromarray(decoded).save(path)
                        finals.append({"source_frame_index":row["source_frame_index"],"segment_id":row["segment_id"],"image":d.binding(root,path)})
                    if i==len(records)-1: Image.fromarray(decoded).save(folder/"final_frame.png")
                d.require(process.stdout.read(1)==b"" and process.wait(timeout=60)==0,"Unexpected frames or decode failure")
            finally:
                if process.poll() is None: process.kill();process.wait(timeout=10)
                process.stdout.close()
        d.write_once(folder/"review_manifest.json",{"schema_version":SCHEMA,"identity":identity,"candidate_id":source["candidate_id"],
            "source_video":source["source_video"],"frames":records,"time_base":"1/90000","native_source_pacing":True,
            "final_hold_ticks":original.HOLD_TICKS,"native_timestamp_evidence":source.get("native_timestamps"),
            "protected_source_pixels_decoded":0,"player_ids_display_only":source["kind"]=="nfhs",
            "pixel_signatures":d.binding(root,folder/"pixel_signatures.npz"),"pixel_signature_shape":[2,32,32,3],
            "changed_episodes":episodes,"human_review":"pending","model_adoption":"failed_checks_not_accepted"})
        d.write_once(folder/"verification.json",{"status":"passed","decoded_frames":len(errors),
            "all_native_pts_durations_and_pair_keys_verified":True,"all_paired_pixel_signatures_verified":True,
            "source_render_passes":1,"signature_panel_mae_max":[max(e[p] for e in errors) for p in (0,1)],
            "protected_frame_pairs_verified_black":sum(r["source_pixels_withheld"] for r in records),
            "changed_episode_count":len(episodes),"suppressed_frames":sum(e["suppressed_frames"] for e in episodes),
            "actual_final_source_frame_index":records[-1]["source_frame_index"],"duration_ticks":total,
            "probe_command":probe_command,"decode_command":command})
        artifacts={key:d.binding(root,folder/name) for key,name in {"video":"comparison.mp4","manifest":"review_manifest.json",
            "verification":"verification.json","probe":"ffprobe.json","pixel_signatures":"pixel_signatures.npz","final_frame":"final_frame.png"}.items()}
        d.write_once(folder/"completion.json",{"status":"completed","identity":identity,"artifacts":artifacts,
            "changed_episodes":episodes,"segment_final_frames":finals,"elapsed_seconds":time.monotonic()-began,"human_review":"pending"})
        return {**artifacts,"changed_episodes":episodes,"segment_final_frames":finals,"completion":d.binding(root,folder/"completion.json")}
    except Exception as error:
        d.write_once(folder/"failed.json",{"status":"failed_preserved","error_type":type(error).__name__,"error":str(error),
                                        "elapsed_seconds":time.monotonic()-began})
        raise


def render_all(root, original_selection_path, policy_path, ffmpeg, output):
    root,output=Path(root).resolve(),Path(output).resolve()
    d.require(output.is_relative_to(root/"data/outputs"),"Review output must remain ignored")
    selection_path=root/Path(original_selection_path)
    policy_path=root/Path(policy_path)
    selection,policy=d.read_json(selection_path),d.read_json(policy_path)
    sources=selection["sources"]; policy_rows=policy["frames"]
    d.require(len(sources)==5 and len({s["candidate_id"] for s in sources})==5
              and sum(len(s["frames"]) for s in sources)==4200 and len(policy_rows)==3975
              and sum(r["decision"]=="withheld" for s in sources for r in s["frames"])==225,"Five-source playback census differs")
    d.require({r["candidate_id"] for r in policy_rows}=={s["candidate_id"] for s in sources},"Policy source census differs")
    bindings={"original_selection":d.binding(root,selection_path),"policy":d.binding(root,policy_path)}
    output.mkdir(parents=True,exist_ok=True); groups={}
    for source in sources:
        cid=source["candidate_id"]
        d.require(Path(cid).name==cid and "/" not in cid and "\\" not in cid and cid not in (".",".."),"Unsafe source ID")
        print(f"Rendering {cid}: {len(source['frames'])} native timeline slots",flush=True)
        groups[cid]=render_source(root,source,[r for r in policy_rows if r["candidate_id"]==cid],ffmpeg,output/cid,bindings)
    cards=[]
    for cid,package in groups.items():
        def url(binding): return quote(Path(os.path.relpath(d.bound(root,binding),output)).as_posix(),safe="/.")
        links=' | '.join(f'<a href="{url(e["image"])}">{e["source_range_inclusive"][0]}–{e["source_range_inclusive"][1]} ({e["suppressed_frames"]})</a>' for e in package["changed_episodes"])
        finals=' | '.join(f'<a href="{url(e["image"])}">{e["source_frame_index"]}</a>' for e in package["segment_final_frames"])
        cards.append(f'<section><h2>{html.escape(cid)}</h2><video controls preload="metadata" src="{url(package["video"])}"></video>'
            f'<p><a href="{url(package["final_frame"])}">Actual final frame</a> | <a href="{url(package["manifest"])}">Every native decision</a></p>'
            f'<details><summary>Suppressed episodes: {len(package["changed_episodes"])}</summary><p>{links}</p></details>'
            f'<details><summary>Every permitted-segment final</summary><p>{finals}</p></details>'
            '<label>Playback speed <select><option value="1">1× native</option><option value="0.5">0.5×</option><option value="0.25">0.25×</option></select></label></section>')
    document='<!doctype html><meta charset="utf-8"><title>Provisional appearance veto comparison</title><style>body{max-width:1280px;margin:24px auto;padding:20px;background:#0f141d;color:#edf2f7;font:17px system-ui}video{width:100%}a{color:#8dd5ff}section{margin:32px 0}</style><h1>Original output and provisional appearance veto</h1><p>The model failed scientific checks. Left: original saved emissions, including the existing gap repairs. Right: original points are vetoed only for negative logits. Existing gap fills require the entire saved gap and both anchors to be positive. No point is relocated or added. This is a failed experimental comparison, not an accepted replacement.</p><p>Native timestamps and all 4,200 slots are retained. The 225 protected NFHS slots have black panels and no decoded source pixels. White NFHS player IDs are display only. Each actual final frame holds for one extra second. Human label and trajectory review remain pending.</p>'+''.join(cards)+'<script>document.querySelectorAll("section").forEach(s=>s.querySelector("select").addEventListener("change",e=>s.querySelector("video").playbackRate=Number(e.target.value)));</script>\n'
    guide=output/"review.html"
    if guide.exists():d.require(guide.read_text(encoding="utf-8")==document,"Existing guide differs")
    else:guide.write_text(document,encoding="utf-8",newline="\n")
    result={"schema_version":SCHEMA,"status":"completed","bindings":bindings,"groups":groups,"guide":d.binding(root,guide),
            "timeline_slots":4200,"protected_slots":225,"human_review":"pending","new_model_calls":0,"model_adoption":"failed_checks_not_accepted"}
    d.write_once(output/"completion.json",result)
    return result


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("selection","policy","ffmpeg","output"):parser.add_argument("--"+name,required=True)
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    render_all(root,args.selection,args.policy,args.ffmpeg,root/args.output)
