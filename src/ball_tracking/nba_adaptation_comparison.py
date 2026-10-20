"""One frozen-checkpoint comparison on approved NBA cores and released NFHS windows.

Labels enter scoring/display only. Existing predictions are immutable controls;
all new triplets, bounded NFHS PNGs, attempts and paired reviews are separate.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from fractions import Fraction
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from . import nba_action_observation as action
from . import nba_action_review as review
from . import nba_wasb_diagnostic as d
from . import wasb_experiment as wasb
from .annotations import SourceVideo, verify_source_video_contract, load_annotations

SCHEMA = "nba_adaptation_comparison/v0.1"
RENDERING = {"nba_fps": 30, "nfhs_fps": 6, "final_hold_seconds": 1, "paired_old_new": True}
GATES = {"det": {"matched_min": 208, "missing_max": 21, "wrong_max": 8,
                  "hidden_alarm_max": 13, "easy_control_matched": 60},
         "nfhs": {"matched_min": 130, "missing_max": 14, "wrong_max": 1, "hidden_alarm_max": 0}}


def bound(root, record):
    path = wasb.bound_path(root, record)
    d.require("bytes" not in record or path.stat().st_size == record["bytes"], "Bound size differs")
    return path


def code_identity():
    tree=ast.parse(Path(__file__).read_text(encoding="utf-8"))
    inference=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=="infer_manifest")
    return {"inference_ast": wasb.canonical(ast.dump(inference,include_attributes=False)), "action": action.inference_identity(),
            "adapter": d.digest(Path(__file__).with_name("wasb_adapted_adapter.py")),
            "source_reader": d.digest(Path(d.nba.__file__))}


def load_context(root, config_path, training_completion_path=None):
    root = Path(root).resolve()
    from .nba_wasb_adaptation import load_config
    config = load_config(root,config_path)
    evaluation = config["evaluation"]
    d.require(evaluation["policy"] == d.POLICY and evaluation["comparison_gates"] == GATES,
              "Comparison policy or gates differ")
    d.require(all(config["rendering"].get(k)==v for k,v in RENDERING.items()), "Review pacing/hold differs")
    d.require([evaluation[k] for k in ("nba_frames", "nba_triplets", "nfhs_frames", "nfhs_triplets")]
              == [2702, 2698, 150, 138], "Evaluation scope differs")
    training = None
    trial = d.contained(root, config["output_root"])
    d.require(trial.is_relative_to(root/"data/outputs"), "Trial outside ignored outputs")
    if training_completion_path is not None:
        training=d.read_json(training_completion_path)
        d.require(training["schema_version"] == "wasb_adaptation_training_completion/v0.1"
                  and training["status"] == "completed" and bound(root,training["config"]) == Path(config_path).resolve()
                  and training["completed_updates"] == config["training"]["updates"]
                  and training["training_provenance"], "Final completed training authority differs")
        d.require(bound(root,training["checkpoint"]) == trial/"training/checkpoint.pth",
                  "Only final training checkpoint may run")
    output = trial/"comparison"
    sources = []
    for item in evaluation["nba_sources"]:
        manifest = d.read_json(bound(root, item["input_manifest"]))
        old = d.read_json(bound(root, item["baseline_observations"]))
        from .nba_hard_example_diagnostic import validate_observations
        validate_observations(manifest, old)
        d.require(not output.is_relative_to(bound(root, item["baseline_observations"]).parent),
                  "Comparison output overlaps baseline")
        sources.append((manifest, old))
    d.require([(m["candidate_id"], len(m["frames"])) for m, _ in sources]
              == [("sac_mem_q1_c01",1471),("sas_det_q1_c02",1231)], "NBA core inventory differs")
    transfer = wasb.load_config(root, bound(root, evaluation["nfhs_transfer_config"]))
    d.require(len(transfer["windows"]) == 6 and all(w["end_frame_index"]-w["start_frame_index"] == 24
              for w in transfer["windows"]), "Only six original short NFHS windows may run")
    calibration = d.read_json(bound(root, evaluation["nfhs_baseline_calibration_config"]))
    d.require([w["window_id"] for w in calibration["windows"]]
              == [w["window_id"] for w in transfer["windows"]], "NFHS baseline windows differ")
    for window, prior in zip(transfer["windows"], calibration["windows"]):
        d.require(all(prior[k] == v for k,v in window.items()), "NFHS baseline context changed")
    baselines = evaluation["nfhs_baselines"]
    d.require([w["window_id"] for w in baselines] == [w["window_id"] for w in transfer["windows"]],
              "NFHS baseline inventory differs")
    for window in baselines:
        for field in ("components", "points", "evaluation"):
            expected = d.contained(root, calibration["output_root"])/window["window_id"]/"threshold_0.3"/(field+".json")
            d.require(bound(root,window[field]) == expected, "NFHS baseline outside original fixed threshold")
    references = []
    for key, cohort in (("nba_hard_reference","hard_example"),("nba_pilot_reference","pilot_control")):
        record = d.read_json(bound(root,evaluation[key]))
        d.require(record["status"] == "human_accepted_assisted_reference", "NBA references are not accepted")
        for ref in record["references"]:
            d.require(ref["human_review"]["status"] == "accepted", "Reference review differs")
            references.append((ref,cohort))
    d.require(sum(len(r["frames"]) for r,_ in references)==640, "Accepted reference scope differs")
    prior_score = d.read_json(bound(root,evaluation["nba_saved_score_report"]))
    prior_windows={w["window_id"]:w for w in prior_score["windows"]}
    for ref,cohort in references:
        manifest,old=next((m,o) for m,o in sources if m["candidate_id"]==ref["candidate_id"])
        d.require(all(ref[k]==manifest[k] for k in ("candidate_id","game_id","approved_role","source_video","time_base")),
                  "Accepted reference source authority differs")
        source_frames={f["source_frame_index"]:f for f in manifest["frames"]}
        d.require(all(f==source_frames.get(f["source_frame_index"]) for f in ref["frames"]),"Accepted reference native PNG/PTS differs")
        wid=ref.get("window_id",ref["candidate_id"]+"_pilot_control")
        old_subset={**old,"frames":[r for r in old["frames"] if r["source_frame_index"] in {f["source_frame_index"] for f in ref["frames"]}]}
        scored=d.score_reference(ref,old_subset)["frame_results"]
        d.require([(r["source_frame_index"],r["outcome"],r["raw_center_error_px"]) for r in scored]
                  ==[(r["source_frame_index"],r["outcome"],r["raw_center_error_px"]) for r in prior_windows[wid]["frame_results"]],
                  "Original accepted NBA score/producer parity differs")
    parent_config = d.read_json(bound(root,config["nfhs_training_config"]))
    return {"config":config,"config_binding":d.binding(root,config_path),"training":training,
            "training_binding":d.binding(root,training_completion_path) if training_completion_path is not None else None,"sources":sources,
            "references":references,"prior_score":prior_score,"transfer":transfer,
            "nfhs_baselines":baselines,"parent_config":parent_config,"output":output}


def infer_manifest(root, manifest, baseline, context, get_adapter):
    """Reuse the actual cache producer and exact ascending float32 averaging."""
    folder = context["output"]/manifest["candidate_id"]
    cache_folder = folder/"triplets"
    cache_folder.mkdir(parents=True,exist_ok=True)
    images, receipts, rows = {}, [], []
    identity_base = {"config":context["config_binding"],"training":context["training_binding"],
                     "model_checkpoint":context["training"]["checkpoint"],"inference_code":code_identity(),
                     "policy":d.POLICY,"source_video":manifest["source_video"],
                     "candidate_id":manifest["candidate_id"],"time_base":manifest["time_base"]}
    def provide(frames):
        values, receipt = action.new_triplet(root,manifest,frames,{**identity_base,"frames":frames},
                                            cache_folder,images,get_adapter)
        receipts.append({"first_source_frame_index":frames[0]["source_frame_index"],
                         "cache":receipt["cache"],"started_record":receipt["started_record"],
                         "attempt_id":receipt["attempt_id"]})
        if len(receipts)%100==0: print(f"{manifest['candidate_id']}: {len(receipts)} triplets",flush=True)
        return values
    segments=[]
    for row in baseline["frames"]:
        segment={"kind":row["segment_kind"],"source_frame_range_inclusive":row["segment_source_frame_range_inclusive"]}
        if not segments or segments[-1]!=segment: segments.append(segment)
    expected=[]; indexed={f["source_frame_index"]:f for f in manifest["frames"]}
    for segment in segments:
        first,last=segment["source_frame_range_inclusive"]
        expected.extend(range(first,last+1))
    d.require(expected == list(indexed), "Segments change coverage or cross boundaries")
    for segment in segments:
        first,last=segment["source_frame_range_inclusive"]
        for frame,mean,count in action.stream_means([indexed[i] for i in range(first,last+1)],provide):
            rows.append(action.select_observation(frame,mean,count,manifest,segment))
    d.require(expected == list(indexed), "Segments change coverage or cross boundaries")
    d.require([r["temporal_contributions"] for r in rows]
              == [r["temporal_contributions"] for r in baseline["frames"]], "Temporal context differs")
    result={"schema_version":SCHEMA,"candidate_id":manifest["candidate_id"],"game_id":manifest["game_id"],
            "approved_role":manifest["approved_role"],"inference":d.POLICY,
            "checkpoint":context["training"]["checkpoint"],"identity":identity_base,
            "frames":rows,"triplet_caches":receipts,"human_review":"pending"}
    d.write_once(folder/"observations.json",result)
    return result


def prepare_nfhs(root, window, output):
    """Only seek/decode one already released 25-frame context; persist verified PNGs."""
    folder=output/window["window_id"]/"inputs"
    identity={"window":window,"decoder":d.digest(Path(wasb.__file__))}
    path=folder/"manifest.json"
    if path.exists():
        saved=d.read_json(path)
        d.require(saved["preparation_identity"]==identity,"NFHS prepared authority changed")
        return saved
    source=window["source_video"]
    attempt=folder/"attempts"/uuid.uuid4().hex
    attempt.mkdir(parents=True,exist_ok=False)
    d.write_once(attempt/"started.json",identity)
    try:
        verify_source_video_contract(SourceVideo.from_mapping(source), root)
        pixels=wasb.decode_window(root,window)
        frames=[]
        for index,image in pixels.items():
            # The existing OpenCV decoder returns BGR; adapter/PNG inputs are RGB.
            image=image[:,:,::-1].copy()
            target=attempt/f"frame_{index:06d}.png"
            Image.fromarray(image).save(target)
            frames.append({"source_frame_index":index,"source_pts_ticks":int(index*90000/source["fps"]),
                           "png":{"path":target.relative_to(root).as_posix(),"sha256":d.digest(target),
                                  "rgb_sha256":hashlib.sha256(image.tobytes()).hexdigest()}})
        manifest={"candidate_id":window["window_id"],"game_id":window["possession_id"],
                  "approved_role":"nfhs_development","source_video":source,"time_base":"1/90000",
                  "frames":frames,"source_end_exclusive_pts_ticks":int((frames[-1]["source_frame_index"]+1)*90000/source["fps"]),
                  "preparation_identity":identity}
        for frame in frames: d.nba.read_verified_png(frame,source,root)
        d.write_once(path,manifest)
        d.write_once(attempt/"completed.json",{"manifest":d.binding(root,path),"decoded_frames":len(frames)})
        return manifest
    except Exception as error:
        d.write_once(attempt/"failed.json",{"status":"failed_preserved","error":str(error)})
        raise


def baseline_nfhs(root, window, manifest, records):
    components=d.read_json(bound(root,records["components"]))
    points=d.read_json(bound(root,records["points"]))
    d.require(points["model_provenance"]["heatmap_threshold"]==.3,"NFHS baseline threshold differs")
    d.require(points["frames"]==wasb.make_point_run(window,{},components)["frames"],"NFHS components/points disagree")
    rows=[]
    first,last=window["start_frame_index"],window["end_frame_index"]
    for offset,(frame,items) in enumerate(zip(manifest["frames"],components,strict=True)):
        candidates=[{"candidate_index":i,**c} for i,c in enumerate(items)]
        chosen=min(candidates,key=lambda c:(-c["native_score"],c["candidate_index"])) if candidates else None
        rows.append({**frame,"source_png":frame["png"],"time_base":"1/90000","inference_status":"completed",
                     "state":"observed" if chosen else "missing","withheld_reason":None,
                     "segment_kind":"development_window","segment_source_frame_range_inclusive":[first,last],
                     "temporal_contributions":min(offset+1,3,len(components)-offset,len(components)-2),"candidates":candidates,
                     "selected_candidate_index":chosen["candidate_index"] if chosen else None,
                     "center_xy_px":[chosen["center_x"],chosen["center_y"]] if chosen else None,
                     "native_score":chosen["native_score"] if chosen else None})
    return {"frames":rows,"candidate_id":manifest["candidate_id"],"checkpoint":{"sha256":d.EXPANDED_SHA}}


def counts(rows):
    c=Counter(r["outcome"] for r in rows)
    return {"frames":len(rows),"eligible_frames":sum(c[k] for k in ("matched","wrong","missing")),
            **{k:c[k] for k in ("matched","wrong","missing","hidden_alarm","hidden_quiet","unscored")}}


def compare_reference(reference, old, new, window_id, cohort):
    ids={f["source_frame_index"] for f in reference["frames"]}
    reports=[]
    for observations in (old,new):
        subset={**observations,"frames":[r for r in observations["frames"] if r["source_frame_index"] in ids]}
        reports.append(d.score_reference(reference,subset))
    rows=[{"source_frame_index":a["source_frame_index"],"old":a,"new":b}
          for a,b in zip(reports[0]["frame_results"],reports[1]["frame_results"],strict=True)]
    return {"window_id":window_id,"cohort":cohort,"candidate_id":reference["candidate_id"],
            "old":counts(reports[0]["frame_results"]),"new":counts(reports[1]["frame_results"]),"frames":rows,
            "gained_match_frames":[r["source_frame_index"] for r in rows if r["old"]["outcome"]!="matched" and r["new"]["outcome"]=="matched"],
            "lost_match_frames":[r["source_frame_index"] for r in rows if r["old"]["outcome"]=="matched" and r["new"]["outcome"]!="matched"],
            "outcome_transitions":dict(Counter(r["old"]["outcome"]+" -> "+r["new"]["outcome"] for r in rows))}


def paired_overlay(root, manifest, frame, old, new, index, labels, fps):
    raw=d.nba.read_verified_png(frame,manifest["source_video"],root)
    with Image.open(io.BytesIO(raw)) as original: source=original.convert("RGB")
    canvas=Image.new("RGB",(1280,816),(15,20,29)); draw=ImageDraw.Draw(canvas)
    label=labels.get(frame["source_frame_index"])
    anchor=(label["geometry"]["center_xy_px"] if label and label["geometry"] else
            old["center_xy_px"] or new["center_xy_px"] or [source.width/2,source.height/2])
    anchor_kind="accepted label" if label and label["geometry"] else "old point" if old["center_xy_px"] else "new point" if new["center_xy_px"] else "image center"
    crop_width,crop_height=min(320,source.width),min(180,source.height)
    cx=max(0,min(source.width-crop_width,round(anchor[0]-crop_width/2)))
    cy=max(0,min(source.height-crop_height,round(anchor[1]-crop_height/2)))
    crop=source.crop((cx,cy,cx+crop_width,cy+crop_height))
    draw.text((12,8),f"{manifest['candidate_id']} | source {frame['source_frame_index']} | "
              f"{frame['source_pts_ticks']/90000:.6f}s | playback {fps} fps",fill="white",font=review.font(19))
    for panel,(title,row) in enumerate((("OLD expanded checkpoint",old),("NEW NBA adaptation",new))):
        left=panel*640
        draw.text((left+12,44),f"{title} | {row['state'].upper()}",fill="#ffd380",font=review.font(20))
        view=ImageOps.contain(source,(636,360),Image.Resampling.LANCZOS)
        x=left+(640-view.width)//2; y=84+(360-view.height)//2
        canvas.paste(view,(x,y))
        def point(center,color,radius,rect,origin=(0,0),dimensions=None):
            if center is not None:
                width,height=dimensions or (source.width,source.height)
                if not (origin[0]<=center[0]<origin[0]+width and origin[1]<=center[1]<origin[1]+height):return
                px=rect[0]+(center[0]-origin[0])*rect[2]/width; py=rect[1]+(center[1]-origin[1])*rect[3]/height
                draw.ellipse((px-radius,py-radius,px+radius,py+radius),outline=color,width=2)
                draw.line((px-9,py,px+9,py),fill=color,width=1)
        point(row["center_xy_px"],"#ff45c5",6,(x,y,view.width,view.height))
        if label and label["geometry"]: point(label["geometry"]["center_xy_px"],"#41e4e0",10,(x,y,view.width,view.height))
        draw.text((left+12,450),f"Shared zoom anchor: {anchor_kind}",fill="#ffd380",font=review.font(16))
        zoom=ImageOps.contain(crop,(636,260),Image.Resampling.LANCZOS)
        zx=left+(640-zoom.width)//2;zy=480+(260-zoom.height)//2;canvas.paste(zoom,(zx,zy))
        point(row["center_xy_px"],"#ff45c5",6,(zx,zy,zoom.width,zoom.height),(cx,cy),(crop_width,crop_height))
        if label and label["geometry"]: point(label["geometry"]["center_xy_px"],"#41e4e0",10,(zx,zy,zoom.width,zoom.height),(cx,cy),(crop_width,crop_height))
        label_state=(label["visibility"]+" / "+("center" if label["geometry"] else "unknown center")) if label else "unlabeled"
        draw.text((left+12,746),label_state,fill="#41e4e0",font=review.font(17))
    draw.text((12,780),"Pink: model | Cyan: accepted label when available | No trails | Human review pending",
              fill="white",font=review.font(17))
    for i,bit in enumerate(review.key_bits(index,frame)):
        draw.rectangle((i*8,808,i*8+7,815),fill="white" if bit=="1" else "black")
    return canvas


def render_pair(root, manifest, old, new, labels, fps, ffmpeg, output):
    """Paired slowed delivery with native source keys and external every-frame verification."""
    import av
    frames=manifest["frames"]
    d.require(fps in (6,30) and len(frames)==len(old["frames"])==len(new["frames"]),"Invalid paired frame inventory")
    for frame,a,b in zip(frames,old["frames"],new["frames"]):
        d.require(all(r["source_frame_index"]==frame["source_frame_index"] and r["source_pts_ticks"]==frame["source_pts_ticks"]
                      and r["source_png"]==frame["png"] for r in (a,b)),"Paired source join differs")
    identity={"manifest":wasb.canonical(manifest),"old":wasb.canonical(old),"new":wasb.canonical(new),
              "labels":wasb.canonical(labels),"fps":fps,"hold_ticks":90000,"renderer":d.digest(Path(__file__))}
    parent=output/"review_attempts"
    for path in sorted(parent.glob("*/completion.json")) if parent.exists() else []:
        saved=d.read_json(path)
        if saved["identity"]==identity:
            for item in saved["artifacts"].values(): bound(root,item)
            return {**saved["artifacts"],"completion":d.binding(root,path)}
    folder=parent/uuid.uuid4().hex;folder.mkdir(parents=True)
    d.write_once(folder/"started.json",{"identity":identity,"at_utc":d.stamp()})
    began=time.monotonic(); tick=90000//fps
    records=[{"review_index":i,"source_frame_index":f["source_frame_index"],"source_pts_ticks":f["source_pts_ticks"],
              "source_png":f["png"],"review_pts_ticks":i*tick,"duration_ticks":tick+(90000 if i==len(frames)-1 else 0)}
             for i,f in enumerate(frames)]
    try:
        video=folder/"review.mp4"; durations={r["review_pts_ticks"]:r["duration_ticks"] for r in records}
        with av.open(str(video),"w",options={"movflags":"+faststart"}) as container:
            stream=container.add_stream("libx264",rate=fps,options={"crf":"18","preset":"fast","bf":"0"})
            stream.width,stream.height,stream.pix_fmt=1280,816,"yuv420p"
            stream.time_base=stream.codec_context.time_base=Fraction(1,90000);stream.codec_context.thread_count=2
            def mux(packets):
                for p in packets:
                    d.require(p.time_base==Fraction(1,90000) and p.pts in durations,"Encoder PTS changed")
                    p.duration=durations[p.pts];container.mux(p)
            for i,(frame,a,b) in enumerate(zip(frames,old["frames"],new["frames"])):
                image=paired_overlay(root,manifest,frame,a,b,i,labels,fps)
                packet=av.VideoFrame.from_image(image);packet.pts=i*tick;packet.time_base=Fraction(1,90000)
                mux(stream.encode(packet))
            mux(stream.encode())
        probe_path=Path(ffmpeg).with_name("ffprobe.exe" if Path(ffmpeg).suffix==".exe" else "ffprobe")
        result=subprocess.run([str(probe_path),"-v","error","-select_streams","v:0","-show_entries",
            "stream=time_base,duration_ts,nb_frames,width,height:frame=best_effort_timestamp,duration","-of","json",str(video)],
            capture_output=True,check=True,timeout=180)
        probe=json.loads(result.stdout);d.write_once(folder/"ffprobe.json",probe)
        stream=probe["streams"][0];total=records[-1]["review_pts_ticks"]+records[-1]["duration_ticks"]
        d.require(stream["time_base"]=="1/90000" and int(stream["duration_ts"])==total and
                  (stream["width"],stream["height"])==(1280,816) and int(stream["nb_frames"])==len(frames),"Encoded timeline differs")
        d.require([(int(r["best_effort_timestamp"]),int(r["duration"])) for r in probe["frames"]]
                  ==[(r["review_pts_ticks"],r["duration_ticks"]) for r in records],"Encoded frame timing differs")
        command=[str(ffmpeg),"-hide_banner","-nostdin","-loglevel","error","-xerror","-threads","2","-i",str(video),
                 "-map","0:v:0","-an","-fps_mode","passthrough","-pix_fmt","rgb24","-f","rawvideo","pipe:1"]
        errors=[]
        with (folder/"decode.stderr.txt").open("xb") as stderr:
            process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=stderr)
            try:
                for i,(frame,a,b) in enumerate(zip(frames,old["frames"],new["frames"])):
                    raw=bytearray()
                    while len(raw)<1280*816*3:
                        chunk=process.stdout.read(1280*816*3-len(raw));d.require(bool(chunk),"Missing decoded frame");raw.extend(chunk)
                    decoded=np.frombuffer(raw,np.uint8).reshape(816,1280,3)
                    bits="".join("1" if decoded[812,k*8+4].mean()>127 else "0" for k in range(112))
                    d.require(bits==review.key_bits(i,frame),"Decoded source frame key differs")
                    expected=np.asarray(paired_overlay(root,manifest,frame,a,b,i,labels,fps))
                    error=float(np.abs(decoded.astype(np.int16)-expected.astype(np.int16)).mean())
                    d.require(error<8,"Decoded paired pixels differ");errors.append(error)
                    if i==len(frames)-1:Image.fromarray(decoded).save(folder/"final_frame.png")
                d.require(process.stdout.read(1)==b"" and process.wait(timeout=60)==0,"Unexpected decoded frames or decoder failure")
            finally:
                if process.poll() is None:process.kill();process.wait(timeout=10)
                process.stdout.close()
        d.write_once(folder/"review_manifest.json",{"schema_version":SCHEMA,"identity":identity,"frames":records,
            "playback_fps":fps,"native_source_time_base":"1/90000","additional_final_hold_ticks":90000,
            "source_frames_each_once":True,"human_review":"pending"})
        d.write_once(folder/"verification.json",{"status":"passed","decoded_frames":len(errors),
            "all_source_keys_and_pts_verified":True,"all_paired_pixels_verified":True,"overlay_mae_max":max(errors),
            "actual_final_source_frame_index":frames[-1]["source_frame_index"],"actual_final_frame_mae":errors[-1],
            "duration_ticks":total,"decode_command":command})
        artifacts={k:d.binding(root,folder/v) for k,v in {"video":"review.mp4","manifest":"review_manifest.json",
            "verification":"verification.json","probe":"ffprobe.json","final_frame":"final_frame.png"}.items()}
        d.write_once(folder/"completion.json",{"status":"completed","identity":identity,"artifacts":artifacts,
            "elapsed_seconds":time.monotonic()-began,"human_review":"pending"})
        return {**artifacts,"completion":d.binding(root,folder/"completion.json")}
    except Exception as error:
        d.write_once(folder/"failed.json",{"status":"failed_preserved","error_type":type(error).__name__,"error":str(error)})
        raise


def gates(nba, nfhs, easy):
    checks={}
    for key,values in (("det",nba),("nfhs",nfhs)):
        for metric,limit in GATES[key].items():
            if metric=="easy_control_matched":checks[key+"_"+metric]=easy==limit
            elif metric.endswith("_min"):checks[key+"_"+metric]=values[metric[:-4]]>=limit
            else:checks[key+"_"+metric]=values[metric[:-4]]<=limit
    return {"checks":checks,"numerical_candidate_pass":all(checks.values()),"human_review":"pending","accepted":False}


def run(root,config_path,training_completion_path,*,adapter_factory=None,render=True):
    root=Path(root).resolve();context=load_context(root,config_path,training_completion_path)
    d.require(context["training"] is not None,"Actual evaluation requires completed final training")
    output=context["output"];output.mkdir(parents=True,exist_ok=True)
    lock=d.acquire_run_lock(output/".run.lock");attempt=output/"attempts"/uuid.uuid4().hex;began=time.monotonic()
    adapter=None
    try:
        identity={"config":context["config_binding"],"training":context["training_binding"],"code":code_identity()}
        d.write_once(output/"identity.json",identity)
        d.write_once(attempt/"started.json",{"identity":identity,"pid":os.getpid(),"at_utc":d.stamp(),
                                            "comparison_source":d.binding(root,Path(__file__))})
        def get_adapter():
            nonlocal adapter
            if adapter is None:
                if adapter_factory:adapter=adapter_factory()
                else:
                    from .wasb_adapted_adapter import AdaptedWasbAdapter
                    c=context["parent_config"];t=context["training"]
                    adapter=AdaptedWasbAdapter(d.contained(root,c["upstream_source"]),bound(root,c["pretrained_checkpoint"]),
                        bound(root,t["checkpoint"]),t["checkpoint"]["sha256"],t["training_provenance"],device="cuda")
                d.write_once(attempt/"model_loaded.json",{"provenance":getattr(adapter,"provenance",{"synthetic":True})})
            return adapter
        comparisons=[];packages=[];nba_rows={};nfhs_rows=[];render_jobs=[]
        for manifest,old in context["sources"]:
            new=infer_manifest(root,manifest,old,context,get_adapter);labels={};group=[]
            for ref,cohort in context["references"]:
                if ref["candidate_id"]!=manifest["candidate_id"]:continue
                labels.update({a["frame_index"]:a for a in ref["annotations"]})
                wid=ref.get("window_id",ref["candidate_id"]+"_pilot_control")
                comp=compare_reference(ref,old,new,wid,cohort);comparisons.append(comp);group.extend(comp["frames"])
            nba_rows[manifest["candidate_id"]]=group
            package={"candidate_id":manifest["candidate_id"],"observations":d.binding(root,output/manifest["candidate_id"]/"observations.json")}
            if render:render_jobs.append((package,manifest,old,new,labels,30))
            packages.append(package)
        prior_windows={w["window_id"]:w for w in context["prior_score"]["windows"]}
        for comp in comparisons:
            expected=prior_windows[comp["window_id"]]["frame_results"]
            d.require([(r["old"]["source_frame_index"],r["old"]["outcome"],r["old"]["raw_center_error_px"]) for r in comp["frames"]]
                      ==[(r["source_frame_index"],r["outcome"],r["raw_center_error_px"]) for r in expected],"Original NBA score parity failed")
        for window,baseline in zip(context["transfer"]["windows"],context["nfhs_baselines"]):
            manifest=prepare_nfhs(root,window,output);old=baseline_nfhs(root,window,manifest,baseline)
            labels_record=d.read_json(bound(root,window["annotation"]));load_annotations(bound(root,window["annotation"]))
            d.require(labels_record["source_video"]==window["source_video"] and
                      [a["frame_index"] for a in labels_record["annotations"]]
                      ==list(range(window["start_frame_index"],window["end_frame_index"]+1)),"NFHS label source/context differs")
            ref={**manifest,"annotations":labels_record["annotations"]}
            new=infer_manifest(root,manifest,old,context,get_adapter)
            comp=compare_reference(ref,old,new,window["window_id"],"nfhs_development");comparisons.append(comp);nfhs_rows.extend(comp["frames"])
            from .wasb_calibration import summarize_reports
            original=summarize_reports([d.read_json(bound(root,baseline["evaluation"]))["top_native_mass"]])
            d.require([comp["old"][k] for k in ("matched","wrong","missing","hidden_alarm")]
                      ==[original[k] for k in ("raw_available_or_matched","wrong_present","missing","hidden_alarm_frames")],"Original NFHS score parity failed")
            package={"candidate_id":manifest["candidate_id"],"observations":d.binding(root,output/manifest["candidate_id"]/"observations.json")}
            if render:render_jobs.append((package,manifest,old,new,{a["frame_index"]:a for a in ref["annotations"]},6))
            packages.append(package)
        nba={key:{arm:counts([r[arm] for r in rows]) for arm in ("old","new")} for key,rows in nba_rows.items()}
        nfhs={arm:counts([r[arm] for r in nfhs_rows]) for arm in ("old","new")}
        d.require([nfhs["old"][k] for k in ("matched","wrong","missing","hidden_alarm")]==[130,1,14,0],"NFHS baseline totals differ")
        easy=sum(c["new"]["matched"] for c in comparisons if c["cohort"]=="pilot_control" and c["candidate_id"]=="sas_det_q1_c02")
        report={"schema_version":SCHEMA,"identity":identity,"nba":nba,"nfhs":nfhs,"windows":comparisons,
                "gates":gates(nba["sas_det_q1_c02"]["new"],nfhs["new"],easy),"packages":packages,
                "limits":["SAC labels are training fit, DET is development only; neither is independent test accuracy.",
                          "No threshold/checkpoint selection; unchanged strict >0.3 original contexts.","All new videos require human review."]}
        d.write_once(output/"score_report.json",{k:v for k,v in report.items() if k!="packages"})
        for package,manifest,old,new,labels,fps in render_jobs:
            package["review"]=render_pair(root,manifest,old,new,labels,fps,context["config"]["evaluation"]["ffmpeg"],
                                           output/manifest["candidate_id"])
        d.write_once(output/"report.json",report)
        completion={"status":"completed","report":d.binding(root,output/"report.json"),"identity":identity,"human_review":"pending"}
        d.write_once(output/"completion.json",completion)
        d.write_once(attempt/"completed.json",{**completion,"elapsed_seconds":time.monotonic()-began})
        return completion
    except Exception as error:
        d.write_once(attempt/"failed.json",{"status":"failed_preserved","error_type":type(error).__name__,"error":str(error),
            "elapsed_seconds":time.monotonic()-began})
        raise
    finally:d.release_run_lock(lock)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--config",required=True)
    parser.add_argument("--training-completion",required=True);parser.add_argument("--run",action="store_true")
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    if not args.run:parser.error("Use --run only after the approved final training completes")
    print(json.dumps(run(root,d.contained(root,args.config),d.contained(root,args.training_completion)),indent=2))


if __name__=="__main__":main()
