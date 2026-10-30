"""One approved, cached native-PNG WASB diagnostic; no fitting or video input.

``--plan`` reads bound metadata/files only. ``--run`` requires a separate approval
of the exact config bytes. Completed triplets survive scoring/rendering failures;
unfinished attempts remain recorded when their missing triplet is retried.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time
import uuid

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from . import nba_annotations as nba
from .annotations import FrameAnnotation
from .wasb_adapter import CHECKPOINT_SHA256, SOURCE_REVISION, SOURCE_SHA256, components_from_heatmap
from .wasb_experiment import canonical, merge_heatmaps

SCHEMA = "nba_wasb_diagnostic/v0.1"
EXPANDED_SHA = "09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98"
POLICY = {"heatmap_threshold": .3, "triplet_stride": 1,
          "aggregation": "mean_aligned_complete_native_triplets", "padding": "none",
          "resampling": "none", "selection": "largest_component_mass", "device": "cuda"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError(f"Nonfinite JSON value: {value}")
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs,
                      parse_constant=invalid)


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def contained(root, relative):
    require(isinstance(relative, str) and relative and "\\" not in relative and ":" not in relative,
            "Expected portable repository-relative path")
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()), "Path leaves repository")
    return path


def binding(root, path):
    return {"path": Path(path).resolve().relative_to(root.resolve()).as_posix(),
            "sha256": digest(path), "bytes": Path(path).stat().st_size}


def bound(root, record):
    path = contained(root, record["path"])
    require(digest(path) == record["sha256"], f"Bound file changed: {record['path']}")
    if "bytes" in record:
        require(path.stat().st_size == record["bytes"], f"Bound size changed: {record['path']}")
    return path


def write_once(path, value):
    path = Path(path)
    if path.exists():
        require(read_json(path) == value, f"Existing evidence differs: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".partial")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    require(not path.exists(), f"Concurrent evidence creation: {path}")
    temporary.replace(path)


def inference_code_identity():
    # A presentation-only fix may reuse the exact completed inference evidence.
    names = {"input_identity", "validate_heatmaps", "infer_reference", "load_triplet"}
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    definitions = {node.name: ast.dump(node, include_attributes=False) for node in tree.body
                   if isinstance(node, ast.FunctionDef) and node.name in names}
    require(set(definitions) == names, "Inference code inventory incomplete")
    return {"runner_inference_ast_sha256": canonical(definitions),
            "adapter_sha256": digest(Path(__file__).with_name("wasb_adapter.py")),
            "adapted_adapter_sha256": digest(Path(__file__).with_name("wasb_adapted_adapter.py")),
            "aggregation_module_sha256": digest(Path(__file__).with_name("wasb_experiment.py")),
            "native_image_verifier_sha256": digest(Path(__file__).with_name("nba_annotations.py"))}


def load_plan(root, config_path):
    """No torch import, model construction, image decode or output writes."""
    from .nba_reviewed_reference import load_accepted_references

    root, config_path = Path(root).resolve(), Path(config_path).resolve()
    require(config_path.is_relative_to(root), "Config must be inside repository")
    config = read_json(config_path)
    expected = {"schema_version", "diagnostic_id", "accepted_references", "checkpoint_completion",
                "pretrained_checkpoint", "upstream_source", "output_root", "inference", "scoring", "rendering"}
    require(set(config) == expected and config["schema_version"] == SCHEMA, "Unsupported diagnostic config")
    require(re.fullmatch(r"[a-z0-9][a-z0-9_-]*", config["diagnostic_id"] or ""), "Invalid diagnostic ID")
    require(config["inference"] == POLICY and config["scoring"] == {"localization_radius_px": 10},
            "This diagnostic implements only the declared frozen recipe")
    render = config["rendering"]
    require(set(render) == {"fps", "final_hold_seconds", "ffmpeg"} and render["fps"] == 6
            and render["final_hold_seconds"] == 1 and Path(render["ffmpeg"]).is_file(), "Invalid rendering configuration")
    output = contained(root, config["output_root"])
    require(output.is_relative_to(root / "data/outputs"), "Output must be under data/outputs")
    acceptance_path = bound(root, config["accepted_references"])
    references = load_accepted_references(acceptance_path, root, verify_images=False)
    require(bool(references), "No accepted references")
    completion_path = bound(root, config["checkpoint_completion"])
    completion = read_json(completion_path)
    require(completion["status"] == "completed" and completion["completed_updates"] == 200
            and completion["checkpoint"]["sha256"] == EXPANDED_SHA, "Expected frozen expanded update-200 checkpoint")
    bound(root, completion["checkpoint"])
    bound(root, completion["config"])
    bound(root, completion["training_manifest"])
    require(config["pretrained_checkpoint"]["sha256"] == CHECKPOINT_SHA256, "Unexpected pretrained checkpoint")
    bound(root, config["pretrained_checkpoint"])
    require(config["upstream_source"]["revision"] == SOURCE_REVISION, "Unexpected upstream revision")
    upstream = contained(root, config["upstream_source"]["path"])
    for relative, expected_sha in SOURCE_SHA256.items():
        require(digest(upstream / relative) == expected_sha, f"Upstream file changed: {relative}")
    windows, ids = [], set()
    for reference in references:
        candidate = reference["candidate_id"]
        require(re.fullmatch(r"[a-z0-9][a-z0-9_-]*", candidate or "") and candidate not in ids,
                "Invalid or duplicate candidate ID")
        ids.add(candidate)
        frames = reference["frames"]
        indices = [f["source_frame_index"] for f in frames]
        ticks = [f["source_pts_ticks"] for f in frames]
        require(len(frames) >= 3 and indices == list(range(indices[0], indices[-1] + 1)),
                "Inference requires consecutive original frame indices")
        require(reference["time_base"] == "1/90000" and all(b > a for a, b in zip(ticks, ticks[1:])),
                "Native timestamps must increase")
        # These approved pilots have alternating millisecond-rounded 60-Hz PTS.
        require(set(b-a for a,b in zip(ticks,ticks[1:])) <= {1440,1530},
                "Unexpected native cadence: review context/gaps before execution")
        require([a["frame_index"] for a in reference["annotations"]] == indices,
                "Reference annotation inventory differs")
        require(reference["human_review"]["status"] == "accepted", "Reference acceptance is missing")
        windows.append({"candidate_id": candidate, "game_id": reference["game_id"],
                        "approved_role": reference["approved_role"], "scored_frames": len(frames),
                        "source_frame_range_inclusive": [indices[0], indices[-1]],
                        "source_pts_ticks_inclusive": [ticks[0], ticks[-1]],
                        "native_delta_ticks": sorted(set(b-a for a,b in zip(ticks,ticks[1:]))),
                        "source_span_seconds": (ticks[-1]-ticks[0])/90000,
                        "unique_triplets": len(frames)-2,
                        "temporal_contribution_counts": [min(i+1,3,len(frames)-i,len(frames)-2)
                                                         for i in range(len(frames))]})
    plan = {"schema_version": SCHEMA, "diagnostic_id": config["diagnostic_id"],
            "config": binding(root, config_path), "accepted_references": binding(root, acceptance_path),
            "checkpoint": completion["checkpoint"], "inference": POLICY, "scoring": config["scoring"],
            "windows": windows, "planned_unique_triplets": sum(w["unique_triplets"] for w in windows),
            "total_scored_frames": sum(w["scored_frames"] for w in windows),
            "output_root": config["output_root"], "inference_code": inference_code_identity(),
            "model_loaded": False, "images_decoded": 0, "original_video_decodes": 0,
            "training": False, "scientific_execution_requires_approval": True}
    return config, references, completion, plan


def authorize(root, approval_path, plan):
    require(approval_path is not None, "--run requires an explicit approval record")
    path = Path(approval_path).resolve()
    require(path.is_relative_to(root), "Approval must be inside repository")
    approval = read_json(path)
    require(approval.get("schema_version") == "nba_wasb_diagnostic_approval/v0.1"
            and approval.get("status") == "approved" and approval.get("approved_by") == "Ryan",
            "Scientific execution has not been approved")
    require(isinstance(approval.get("approved_at_utc"), str) and approval["approved_at_utc"].strip(),
            "Approval needs its recorded timestamp")
    approved_at = datetime.fromisoformat(approval["approved_at_utc"].replace("Z", "+00:00"))
    require(approved_at.tzinfo is not None and approved_at.utcoffset().total_seconds() == 0,
            "Approval timestamp must be UTC")
    expected = {"path": plan["config"]["path"], "sha256": plan["config"]["sha256"]}
    require(approval.get("config") == expected, "Approval does not bind this exact config")
    require(approval.get("scope") == {"diagnostic_id": plan["diagnostic_id"],
            "planned_unique_triplets": plan["planned_unique_triplets"], "training": False,
            "source_video_decode": False}, "Approval differs from the planned scientific scope")
    return binding(root, path)


def input_identity(reference, frames, config, plan):
    return {"candidate_id": reference["candidate_id"], "game_id": reference["game_id"],
            "source_video": reference["source_video"], "time_base": reference["time_base"],
            "frames": frames, "model_checkpoint": plan["checkpoint"],
            "pretrained_checkpoint": config["pretrained_checkpoint"], "policy": POLICY,
            "inference_code": plan["inference_code"]}


def validate_heatmaps(values):
    require(isinstance(values, np.ndarray) and values.dtype == np.float32
            and values.shape == (3,288,512) and np.isfinite(values).all()
            and (values >= 0).all() and (values <= 1).all(), "Invalid completed triplet heatmaps")


def load_triplet(root, cache, receipt, identity):
    with np.load(cache, allow_pickle=False) as saved:
        require(set(saved.files) == {"heatmaps", "metadata_json"}, "Incomplete triplet archive")
        heatmaps = saved["heatmaps"]
        metadata = json.loads(str(saved["metadata_json"].item()))
    validate_heatmaps(heatmaps)
    require(metadata["identity"] == identity and metadata["status"] == "completed", "Completed cache identity mismatch")
    require(math.isfinite(metadata["elapsed_seconds"]) and metadata["elapsed_seconds"] >= 0, "Invalid call duration")
    started = read_json(bound(root, metadata["started_record"]))
    require(started["identity_sha256"] == canonical(identity) and started["attempt_id"] == metadata["attempt_id"],
            "Completed cache lacks matching call history")
    record = {**metadata, "cache": binding(root, cache)}
    write_once(receipt, record)
    return heatmaps, record


def infer_reference(root, reference, config, plan, output, get_adapter):
    """Labels never enter the model or candidate selection."""
    folder = output / reference["candidate_id"] / "triplets"
    folder.mkdir(parents=True, exist_ok=True)
    frames = reference["frames"]
    values_by_start, records = {}, []
    # Three-image rolling buffer; every returned PNG byte stream is verified.
    images = {}
    for offset in range(len(frames)-2):
        triplet = frames[offset:offset+3]
        first = triplet[0]["source_frame_index"]
        identity = input_identity(reference, triplet, config, plan)
        cache, receipt = folder/f"triplet_{first:06d}.npz", folder/f"triplet_{first:06d}.json"
        if cache.exists():
            values, record = load_triplet(root, cache, receipt, identity)
        else:
            require(not receipt.exists(), "Completed receipt exists without its cache; preserve and investigate")
            for frame in triplet:
                idx = frame["source_frame_index"]
                if idx not in images:
                    raw = nba.read_verified_png(frame, reference["source_video"], root)
                    with Image.open(io.BytesIO(raw)) as image:
                        images[idx] = np.asarray(image).copy()
            images = {f["source_frame_index"]: images[f["source_frame_index"]] for f in triplet}
            adapter = get_adapter()
            attempt_id = uuid.uuid4().hex
            attempts = folder/"attempts"
            start_path = attempts/f"{first:06d}_{attempt_id}_started.json"
            write_once(start_path, {"attempt_id": attempt_id, "started_at_utc": stamp(),
                                   "source_frame_indices": [f["source_frame_index"] for f in triplet],
                                   "identity_sha256": canonical(identity), "status": "started"})
            began = time.monotonic()
            try:
                prediction = adapter.predict_triplet([images[f["source_frame_index"]] for f in triplet])
                values = prediction["heatmaps"]
                validate_heatmaps(values)
                metadata = {"status": "completed", "attempt_id": attempt_id, "identity": identity,
                            "started_record": binding(root,start_path), "elapsed_seconds": time.monotonic()-began}
                temporary = cache.with_name(cache.name+"."+attempt_id+".partial")
                with temporary.open("xb") as handle:
                    np.savez_compressed(handle, heatmaps=values,
                                        metadata_json=np.array(json.dumps(metadata,sort_keys=True,allow_nan=False)))
                    handle.flush(); os.fsync(handle.fileno())
                require(not cache.exists(), "Concurrent triplet completion")
                temporary.replace(cache)
                values, record = load_triplet(root,cache,receipt,identity)
            except Exception as error:
                write_once(attempts/f"{first:06d}_{attempt_id}_failed.json",
                           {"attempt_id":attempt_id,"status":"failed_preserved","elapsed_seconds":time.monotonic()-began,
                            "error_type":type(error).__name__,"error":str(error)})
                raise
        values_by_start[first] = values
        records.append(record)
    start,end = frames[0]["source_frame_index"],frames[-1]["source_frame_index"]
    means,counts = merge_heatmaps(values_by_start,start,end)
    observations=[]
    for frame,heatmap,count in zip(frames,means,counts):
        candidates=components_from_heatmap(heatmap,reference["source_video"]["width_px"],
                                           reference["source_video"]["height_px"],threshold=.3)
        candidates=[{"candidate_index":i,**c} for i,c in enumerate(candidates)]
        chosen=min(candidates,key=lambda c:(-c["native_score"],c["candidate_index"])) if candidates else None
        observations.append({"source_frame_index":frame["source_frame_index"],
            "source_pts_ticks":frame["source_pts_ticks"],"time_base":reference["time_base"],"source_png":frame["png"],
            "inference_status":"completed","state":"observed" if chosen else "missing",
            "temporal_contributions":count,"candidates":candidates,
            "selected_candidate_index":None if chosen is None else chosen["candidate_index"],
            "center_xy_px":None if chosen is None else [chosen["center_x"],chosen["center_y"]],
            "native_score":None if chosen is None else chosen["native_score"]})
    payload={"schema_version":"nba_wasb_observations/v0.1","candidate_id":reference["candidate_id"],
             "game_id":reference["game_id"],"approved_role":reference["approved_role"],
             "reference_bindings":reference["bindings"],"reference_origin":reference["origin"],
             "reference_human_review":reference["human_review"],
             "model_origin":{"kind":"wasb_model_inference","checkpoint":plan["checkpoint"]},
             "model_output_human_review":"pending","inference":POLICY,"checkpoint":plan["checkpoint"],
             "native_score_semantics":"sum of sigmoid heatmap values in strict >0.3 component; not probability",
             "frames":observations,"triplet_caches":[r["cache"] for r in records]}
    write_once(output/reference["candidate_id"]/"observations.json",payload)
    return payload


def score_reference(reference, observations):
    require(len(reference["frames"])==len(observations["frames"]),"Incomplete observation coverage")
    source=reference["source_video"]
    results=[]
    for i,(frame,label,observation) in enumerate(zip(reference["frames"],reference["annotations"],observations["frames"])):
        require(observation["source_frame_index"]==frame["source_frame_index"]==label["frame_index"]
                and observation["source_pts_ticks"]==frame["source_pts_ticks"]
                and observation["source_png"]==frame["png"] and observation["inference_status"]=="completed",
                "Observed/reference producer mapping differs")
        bounds=type("Bounds",(),{"width_px":source["width_px"],"height_px":source["height_px"]})()
        annotation=FrameAnnotation.from_mapping(label,i,bounds)
        point=observation["center_xy_px"]
        result={"source_frame_index":label["frame_index"],"source_pts_ticks":frame["source_pts_ticks"],
                "temporal_contributions":observation["temporal_contributions"],
                "visibility":label["visibility"],"outcome":"unscored","raw_center_error_px":None,
                "uncertainty_adjusted_error_px":None,"raw_candidate_available":False}
        if annotation.localization_eligible:
            target=annotation.geometry.center_xy_px
            def matches(x,y):
                return 0<=x<source["width_px"] and 0<=y<source["height_px"] and math.hypot(x-target[0],y-target[1])<=10
            result["raw_candidate_available"]=any(matches(c["center_x"],c["center_y"]) for c in observation["candidates"])
            if point is None:
                result["outcome"]="missing"
            else:
                error=math.hypot(point[0]-target[0],point[1]-target[1])
                result.update(outcome="matched" if matches(*point) else "wrong",raw_center_error_px=error,
                              uncertainty_adjusted_error_px=max(0,error-annotation.geometry.uncertainty_radius_px))
        elif annotation.visibility=="not_visible" and annotation.game_ball_identity_certainty in {"certain","probable"}:
            result["outcome"]="hidden_alarm" if point is not None else "hidden_quiet"
        results.append(result)
    def summary(rows):
        counts=Counter(r["outcome"] for r in rows)
        errors=[r["raw_center_error_px"] for r in rows if r["raw_center_error_px"] is not None]
        effective=[r["uncertainty_adjusted_error_px"] for r in rows if r["uncertainty_adjusted_error_px"] is not None]
        eligible=sum(counts[k] for k in ("matched","wrong","missing"))
        hidden=counts['hidden_alarm']+counts['hidden_quiet']
        return {"frames":len(rows),"eligible_frames":eligible,"matched":counts['matched'],"wrong":counts['wrong'],
                "missing":counts['missing'],"unscored":counts['unscored'],"true_positive_count":counts['matched'],
                "false_positive_count":counts['wrong']+counts['hidden_alarm'],
                "false_negative_count":counts['wrong']+counts['missing'],
                "raw_candidate_available":sum(r['raw_candidate_available'] for r in rows),
                "raw_center_error_all_emitted_eligible_mean_px":statistics.fmean(errors) if errors else None,
                "uncertainty_adjusted_error_all_emitted_eligible_mean_px":statistics.fmean(effective) if effective else None,
                "hidden_reference_frames":hidden,"hidden_alarm_rate":counts['hidden_alarm']/hidden if hidden else None}
    return {"schema_version":"nba_wasb_point_diagnostic/v0.1","candidate_id":reference["candidate_id"],
            "game_id":reference["game_id"],"approved_role":reference["approved_role"],
            "localization_radius_px":10,"matching":"inclusive raw source-pixel distance; in-image points only",
            "uncertainty":"diagnostic subtraction only; does not change matches and is not ball radius",
            "summary":summary(results),"endpoints_fewer_than_three_contributions":summary([r for r in results if r['temporal_contributions']<3]),
            "interior_three_contributions":summary([r for r in results if r['temporal_contributions']==3]),
            "frame_results":results,
            "limits":["Short development scenes, not holdouts or full-game performance.",
                      "Native 16/17 ms image spacing differs from the adapted NFHS 40 ms spacing.",
                      "Missing model observation does not establish invisible ball.",
                      "Raw candidate availability uses reference labels for scoring, not candidate selection.",
                      "No hidden reference frames means hidden-alarm behavior is unmeasured.",
                      "Long occlusions, recovery and gap behavior are not established."]}


def render_overlay(image, frame, label, observation):
    from .prepare_nba_assisted_review import draw_point, font
    canvas=Image.new("RGB",(1280,720),(15,20,29)); draw=ImageDraw.Draw(canvas)
    draw.text((16,8),"WASB diagnostic | AI reference labels accepted by human",fill="#ffd380",font=font(24))
    draw.text((16,42),f"Source {frame['source_frame_index']} | PTS {frame['source_pts_ticks']} x 1/90000",fill="white",font=font(20))
    view=ImageOps.contain(image,(960,540),Image.Resampling.LANCZOS);canvas.paste(view,(0,78))
    reference=None if label['geometry'] is None else label['geometry']['center_xy_px']
    model=observation['center_xy_px']; anchor=reference or model or [image.width/2,image.height/2]
    size=min(128,image.width,image.height)
    left=min(max(0,math.floor(anchor[0]-size/2)),image.width-size)
    top=min(max(0,math.floor(anchor[1]-size/2)),image.height-size)
    box=(left,top,left+size,top+size)
    canvas.paste(image.crop(box).resize((288,288),Image.Resampling.NEAREST),(976,108))
    for point,color,radius in ((reference,"#00ffff",0 if reference is None else label['geometry']['uncertainty_radius_px']),
                               (model,"#ff45c5",0)):
        if point is not None:
            x,y=point
            if 0<=x<image.width and 0<=y<image.height:
                draw_point(draw,(x*view.width/image.width,78+y*view.height/image.height),radius*view.width/image.width,color)
            if left<=x<left+size and top<=y<top+size:
                draw_point(draw,(976+(x-left)*288/size,108+(y-top)*288/size),radius*288/size,color,288/size)
    draw.text((976,82),"Reference-centered native crop",fill="white",font=font(16))
    draw.text((976,418),"Cyan: accepted AI reference",fill="#00ffff",font=font(16))
    draw.text((976,446),"Pink: selected WASB point",fill="#ff45c5",font=font(16))
    draw.text((16,632),f"Reference: {label['visibility']} | Model: {observation['state']} | contributions: {observation['temporal_contributions']}",fill="white",font=font(20))
    draw.text((16,666),"Development diagnostic; model output review pending. Slow playback is not native timing.",fill="#ffd380",font=font(18))
    return canvas


def render_reference(root, reference, observations, config, output):
    parent=output/reference['candidate_id']/"review_attempts";parent.mkdir(parents=True,exist_ok=True)
    for receipt_path in sorted(parent.glob("*/completion.json")):
        receipt=read_json(receipt_path)
        require(receipt['observations_sha256']==canonical(observations),"Existing render maps different observations")
        for item in receipt['artifacts']: bound(root,item)
        return binding(root,receipt_path)
    folder=parent/uuid.uuid4().hex;folder.mkdir();(folder/'frames').mkdir()
    write_once(folder/'started.json',{'status':'started','at_utc':stamp(),'observations_sha256':canonical(observations)})
    started=time.monotonic()
    try:
        records=[]
        for i,(frame,label,observation) in enumerate(zip(reference['frames'],reference['annotations'],observations['frames'])):
            raw=nba.read_verified_png(frame,reference['source_video'],root)
            with Image.open(io.BytesIO(raw)) as image: composite=render_overlay(image,frame,label,observation)
            path=folder/'frames'/f'review_{i:06d}.png';composite.save(path)
            records.append({'review_index':i,'source_frame_index':frame['source_frame_index'],
                            'source_pts_ticks':frame['source_pts_ticks'],'source_png':frame['png'],
                            'overlay':binding(root,path)})
        command=[config['rendering']['ffmpeg'],'-hide_banner','-nostdin','-loglevel','warning','-xerror','-n',
                 '-framerate','6','-start_number','0','-i',str(folder/'frames/review_%06d.png'),'-an',
                 '-vf','tpad=stop_mode=clone:stop_duration=1','-c:v','libx264','-threads','2','-preset','fast',
                 '-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(folder/'review.mp4')]
        with (folder/'ffmpeg.stdout.txt').open('xb') as stdout,(folder/'ffmpeg.stderr.txt').open('xb') as stderr:
            result=subprocess.run(command,stdout=stdout,stderr=stderr,timeout=120,check=False)
        require(result.returncode==0,f'Review encode failed: {result.returncode}')
        manifest={'candidate_id':reference['candidate_id'],'reference_origin':reference['origin'],
                  'reference_human_review':reference['human_review'],'model_output_human_review':'pending',
                  'frames':records,'command':command,'fps':6,'final_frame_hold_seconds':1,
                  'expected_encoded_frames':len(records)+6,'native_time_pacing':False,
                  'final_source_frame_index':records[-1]['source_frame_index']}
        write_once(folder/'review_manifest.json',manifest)
        receipt={'status':'complete','observations_sha256':canonical(observations),
                 'elapsed_seconds':time.monotonic()-started,
                 'artifacts':[binding(root,folder/name) for name in ('review_manifest.json','review.mp4','ffmpeg.stderr.txt')]
                 +[r['overlay'] for r in records]}
        write_once(folder/'completion.json',receipt)
        return binding(root,folder/'completion.json')
    except Exception as error:
        write_once(folder/'failed.json',{'status':'failed_preserved','error_type':type(error).__name__,
                                        'error':str(error),'elapsed_seconds':time.monotonic()-started})
        raise


def call_accounting(output):
    starts=list(output.glob('*/triplets/attempts/*_started.json'))
    failures=list(output.glob('*/triplets/attempts/*_failed.json'))
    completed=[read_json(p)['attempt_id'] for p in output.glob('*/triplets/triplet_*.json')]
    failed={read_json(p)['attempt_id'] for p in failures}
    uncertain=[read_json(p)['attempt_id'] for p in starts if read_json(p)['attempt_id'] not in set(completed)|failed]
    return {'model_call_starts':len(starts),'completed_unique_triplets':len(completed),
            'failed_attempts':len(failures),'started_without_completed_or_failed_record':uncertain,
            'all_attempt_evidence_retained':True}


def acquire_run_lock(path):
    """An OS-held lock expires on process exit; a stale filename cannot block resume."""
    handle=path.open('a+b')
    try:
        if path.stat().st_size==0:
            handle.write(b' ');handle.flush()
        handle.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return handle
    except OSError as error:
        handle.close()
        raise ValueError('Another diagnostic process currently holds the output lock') from error


def release_run_lock(handle):
    handle.seek(0)
    try:
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            fcntl.flock(handle,fcntl.LOCK_UN)
    finally:
        handle.close()


def run_diagnostic(root,config_path,approval_path,*,adapter_factory=None,render=True):
    """The injection hooks are for focused fake-adapter tests, never CLI options."""
    root=Path(root).resolve()
    config,references,completion,plan=load_plan(root,config_path)
    approval=authorize(root,approval_path,plan)  # Before output mutation or model construction.
    output=contained(root,config['output_root']);output.mkdir(parents=True,exist_ok=True)
    lock=acquire_run_lock(output/'.run.lock')
    adapter=None;run_id=uuid.uuid4().hex;began=time.monotonic()
    attempt=output/'run_attempts'/run_id
    try:
        write_once(output/'run_identity.json',{'config':plan['config'],'inference_code':plan['inference_code'],
                                              'checkpoint':plan['checkpoint'],'planned_unique_triplets':plan['planned_unique_triplets']})
        write_once(attempt/'started.json',{'status':'started','at_utc':stamp(),'approval':approval,'plan':plan,
                                         'pid':os.getpid(),'runner_code_sha256':digest(Path(__file__))})
        def get_adapter():
            nonlocal adapter
            if adapter is None:
                if adapter_factory is not None:adapter=adapter_factory()
                else:
                    from .wasb_adapted_adapter import AdaptedWasbAdapter
                    adapter=AdaptedWasbAdapter(contained(root,config['upstream_source']['path']),
                        bound(root,config['pretrained_checkpoint']),bound(root,completion['checkpoint']),
                        completion['checkpoint']['sha256'],completion['training_provenance'],device='cuda')
                write_once(attempt/'model_loaded.json',{
                    'provenance':getattr(adapter,'provenance',{'kind':'injected_test_adapter'}),
                    'python':sys.version,'numpy':np.__version__,'at_utc':stamp()})
            return adapter
        outputs=[]
        for reference in references:
            observations=infer_reference(root,reference,config,plan,output,get_adapter)
            score=score_reference(reference,observations)
            folder=output/reference['candidate_id'];write_once(folder/'diagnostic.json',score)
            review=render_reference(root,reference,observations,config,output) if render else None
            outputs.append({'candidate_id':reference['candidate_id'],'game_id':reference['game_id'],
                            'approved_role':reference['approved_role'],'summary':score['summary'],
                            'observations':binding(root,folder/'observations.json'),'diagnostic':binding(root,folder/'diagnostic.json'),
                            'review_completion':review})
        receipt={'status':'complete','diagnostic_id':plan['diagnostic_id'],'config':plan['config'],'approval':approval,
                 'candidates':outputs,'call_accounting':call_accounting(output),'original_video_decodes':0,
                 'training':False,'reference_labels_modified':False,'model_output_human_review':'pending'}
        write_once(output/'completion.json',receipt)
        write_once(attempt/'completed.json',{'status':'completed','elapsed_seconds':time.monotonic()-began,
                                            'completion':binding(root,output/'completion.json')})
        return receipt
    except Exception as error:
        write_once(attempt/'failed.json',{'status':'failed_preserved','error_type':type(error).__name__,
            'error':str(error),'elapsed_seconds':time.monotonic()-began,'call_accounting':call_accounting(output)})
        raise
    finally:
        release_run_lock(lock)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--repository-root',type=Path,default=Path.cwd())
    mode=parser.add_mutually_exclusive_group(required=True);mode.add_argument('--plan',action='store_true');mode.add_argument('--run',action='store_true')
    parser.add_argument('--approval',type=Path)
    args=parser.parse_args();root=args.repository_root.resolve()
    config=root/args.config
    if args.plan:result=load_plan(root,config)[3]
    else:result=run_diagnostic(root,config,None if args.approval is None else root/args.approval)
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':
    main()
