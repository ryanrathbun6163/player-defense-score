"""Six-panel review of original crop guesses and tentative history selections."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from .annotations import load_annotations, verify_source_video_contract
from .crop_ranking import ARMS, experiment_grid
from .crop_ranking_evaluation import score_experiment, selected_frame
from .crop_ranking_experiment import OUTPUT_ROOT, load_observations, preflight, unchanged
from .development_experiments import bound_file, canonical_sha256, closed, read_json, safe_path, sha256_file
from .temporal_experiment import file_binding, persist_once, spec_digest
from .tiled_candidates import select_run

TITLES = ("Crop: all candidates", "Crop: top one", "Crop: top twenty",
          "History: tight links", "History: wide links", "Whole frame: top one")


def render_frame(source, annotation, variants):
    import cv2
    import numpy as np
    from .prepare_detection_visual_review import DetectionReviewView, render_detection_overlay, render_truth_region_panel
    if len(variants) != 6:
        raise ValueError("All five ranking arms and whole-frame context required")
    overlays,views,panels = [],[],[]
    for title,(frame,observation,result,threshold) in zip(TITLES,variants):
        selected = selected_frame(frame,observation)
        view = DetectionReviewView(title,threshold,10.0,"descriptive_display_not_selected")
        overlay,_ = render_detection_overlay(source,annotation,selected,result,view)
        history = observation["ranking"]
        details = observation["decision_reason"]
        if history is not None:
            winner = history["winner"]
            details += f" | path score {winner['score']:.3f}"
            current = [e for e in history["competing_endpoints"] if e["endpoint"] is not None
                       and e["endpoint"][0] == frame.frame_index
                       and e["endpoint"][1] not in observation["emitted_candidate_indices"]]
            detections = {d.candidate_index:d for d in frame.detections}
            for alternative in current[:3]:
                index = alternative["endpoint"][1]
                x,y = map(round,detections[index].center_xy_px)
                cv2.circle(overlay,(x,y),12,(0,190,255),1)
                cv2.putText(overlay,f"alt #{index}",(x+14,y-14),cv2.FONT_HERSHEY_SIMPLEX,.45,(0,190,255),1)
        header = np.zeros((90,overlay.shape[1],3),dtype=np.uint8)
        cv2.putText(header,title,(10,25),cv2.FONT_HERSHEY_SIMPLEX,.75,(255,255,255),1)
        cv2.putText(header,details,(10,51),cv2.FONT_HERSHEY_SIMPLEX,.60,(230,230,230),1)
        cv2.putText(header,"Orange alt = context only; score is not confidence or probability",(10,77),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,190,255),1)
        overlays.append(np.vstack((header,overlay)))
        views.append(view)
        canvas = np.zeros((522,800,3),dtype=np.uint8)
        canvas[72:] = cv2.resize(overlay[:,:source.shape[1]],(800,450))
        cv2.putText(canvas,f"{title} | conf {threshold} | frame {frame.frame_index}",(8,20),cv2.FONT_HERSHEY_SIMPLEX,.55,(255,255,255),1)
        summary = f"TP {int(result['matched_candidate_index'] is not None)} | FP {result['false_positive_count']} | FN {result['false_negative_count']}"
        cv2.putText(canvas,summary,(8,42),cv2.FONT_HERSHEY_SIMPLEX,.55,(230,230,230),1)
        # The native images and JSON retain full reasons and every alternative.
        cv2.putText(canvas,details,(8,64),cv2.FONT_HERSHEY_SIMPLEX,.41,(230,230,230),1)
        panels.append(canvas)
    closeups = [render_truth_region_panel(source,[o[90:] for o in overlays[i:i+2]],annotation,variants[i][0],views[i:i+2])[0]
                for i in (0,2,4)]
    return np.vstack((np.hstack(panels[:3]),np.hstack(panels[3:]))),overlays,np.vstack(closeups)


def validate_review_bundle(bundle,header):
    value = closed(read_json(bundle/"manifest.json"),{"header","assets","final_frames","human_visual_review"},"crop ranking review")
    if value["header"] != header or value["human_visual_review"] != "pending":
        raise ValueError("Ranking review provenance mismatch")
    expected = set()
    for w in header["windows"]:
        for threshold in (.2,.35):
            prefix = f"{w['window_id']}/confidence_{threshold}"
            expected.add(f"{prefix}/comparison_slow.mp4")
            for frame in range(w["start_frame_index"],w["end_frame_index"]+1):
                expected.update(f"{prefix}/{folder}/frame_{frame:06d}.png" for folder in ("comparison","closeups",*(f"view_{i}" for i in range(6))))
    paths = [a["path"] for a in value["assets"]]
    if (len(paths) != len(expected) or set(paths) != expected
            or value["final_frames"] != [{"window_id":w["window_id"],"frame_index":w["end_frame_index"]} for w in header["windows"]]):
        raise ValueError("Incomplete/duplicate ranking review assets or missing final frame")
    for item in value["assets"]:
        if sha256_file(safe_path(bundle,item["path"])) != item["sha256"]:
            raise ValueError("Ranking review asset hash mismatch")
    return value


def render_experiment(root,path):
    import cv2
    scored = score_experiment(root,path)  # Immutable deterministic parity checked; never reruns a detector.
    m,p,inputs,commit = preflight(root,path)
    grids = {purpose:read_json(root/b["path"]) for purpose,b in zip(p["pool_separation"],scored["reports"])}
    saved = {purpose:read_json(bound_file(root,b,"data/outputs/ball_tracking/tiled_development"))
             for purpose,b in zip(p["pool_separation"],p["saved_crop_scoring_reports"])}
    header = {"schema_version":"ball_crop_ranking_visual_review/v0.1","experiment_spec_sha256":spec_digest(m),
              "renderer_code_commit":commit,"scoring_reports":scored["reports"],"windows":p["windows"],
              "confidence_views":[.2,.35],"radius_px":10.0,"panels":[*ARMS,"saved_whole_frame_top_one_context"],
              "original_control_reports":p["saved_crop_scoring_reports"],"selected_operating_point":None,"quality_gate":None}
    bundle = safe_path(root,f"{OUTPUT_ROOT}/review/{canonical_sha256(header)[:32]}",OUTPUT_ROOT)
    for (_,run,_),label in zip(inputs,p["scoring_labels"]):
        verify_source_video_contract(run.source_video,root)
        bound_file(root,label["annotation"],"configs/ball_tracking/annotations")
    if bundle.exists():
        validate_review_bundle(bundle,header)
        unchanged(root,path,m,commit)
        return {"bundle":str(bundle),"reused":True}
    bundle.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".pending_review_",dir=bundle.parent) as temporary:
        staging = Path(temporary).resolve()
        staging.relative_to(root.resolve())
        assets = []

        def add(target):
            assets.append({"path":target.relative_to(staging).as_posix(),"sha256":sha256_file(target)})

        for window,(whole,run,digest),label in zip(p["windows"],inputs,p["scoring_labels"]):
            labels = load_annotations(bound_file(root,label["annotation"],"configs/ball_tracking/annotations"))
            truth = labels.annotation_by_frame()
            observations,reports,context = {},{},{}
            for threshold in (.2,.35):
                for c in (c for c in experiment_grid() if c.confidence_threshold == threshold):
                    observations[c.variant_id] = load_observations(root,m,window,run,digest,c,commit)
                    reports[c.variant_id] = next(r for r in grids[window["purpose"]]["evaluation_reports"]
                                                 if r["possession_id"] == run.possession_id and r["variant_id"] == c.variant_id and r["localization_radius_px"] == 10.0)
                context[threshold] = (select_run(whole,"top_one",threshold), next(r for r in saved[window["purpose"]]["evaluation_reports"]
                      if r["possession_id"] == run.possession_id and r["config"] == {"image_arm":"saved_whole_frame","selector":"top_one","confidence_threshold":threshold,"localization_radius_px":10.0}))
            capture = cv2.VideoCapture(str(safe_path(root,whole.source_video.path.as_posix(),"data/clips")))
            writers = {}
            try:
                if not capture.isOpened() or not capture.set(cv2.CAP_PROP_POS_FRAMES,run.window.start_frame_index):
                    raise ValueError("Could not open/seek ranking review source")
                for offset,frame in enumerate(run.frames):
                    ok,source = capture.read()
                    if (not ok or source.shape != (run.source_video.height_px,run.source_video.width_px,3)
                            or round(capture.get(cv2.CAP_PROP_POS_FRAMES)) != frame.frame_index+1):
                        raise ValueError("Incomplete or incorrect review source decode")
                    for threshold in (.2,.35):
                        variants = [(frame,observations[c.variant_id]["frames"][offset],reports[c.variant_id]["frame_results"][offset],threshold)
                                    for c in experiment_grid() if c.confidence_threshold == threshold]
                        control,report = context[threshold]
                        cf = control.frames[offset]
                        variants.append((cf,{"emitted_candidate_indices":[d.candidate_index for d in cf.detections],"ranking":None,
                                             "decision_reason":"saved_whole_frame_context"},report["frame_results"][offset],threshold))
                        comparison,overlays,closeups = render_frame(source,truth[frame.frame_index],variants)
                        folder = staging/window["window_id"]/f"confidence_{threshold}"
                        for name,pixels in [("comparison",comparison),("closeups",closeups),*((f"view_{i}",v) for i,v in enumerate(overlays))]:
                            target = folder/name/f"frame_{frame.frame_index:06d}.png"
                            target.parent.mkdir(parents=True,exist_ok=True)
                            if not cv2.imwrite(str(target),pixels):
                                raise ValueError("Could not write ranking review PNG")
                            add(target)
                        if threshold not in writers:
                            target = folder/"comparison_slow.mp4"
                            writer = cv2.VideoWriter(str(target),cv2.VideoWriter_fourcc(*"mp4v"),5.0,(comparison.shape[1],comparison.shape[0]))
                            if not writer.isOpened():
                                raise ValueError("Could not open ranking review writer")
                            writers[threshold] = (writer,target)
                        writers[threshold][0].write(comparison)
            finally:
                capture.release()
                for writer,_ in writers.values():
                    writer.release()
            for _,target in writers.values():
                video,count = cv2.VideoCapture(str(target)),0
                try:
                    while video.read()[0]:
                        count += 1
                    if count != 25 or video.get(cv2.CAP_PROP_FPS) != 5.0:
                        raise ValueError("Ranking clip did not decode all 25 frames at 5 fps")
                finally:
                    video.release()
                add(target)
        persist_once(staging/"manifest.json",{"header":header,"assets":assets,
                     "final_frames":[{"window_id":w["window_id"],"frame_index":w["end_frame_index"]} for w in p["windows"]],"human_visual_review":"pending"})
        validate_review_bundle(staging,header)
        unchanged(root,path,m,commit)
        staging.rename(bundle)
    return {"bundle":str(bundle),"reused":False,"assets":len(assets),"human_visual_review":"pending"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("score","render"))
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--repository-root",type=Path,default=Path.cwd())
    args = parser.parse_args()
    root = args.repository_root.resolve()
    action = score_experiment if args.stage == "score" else render_experiment
    print(json.dumps(action(root,(root/args.manifest).resolve()),indent=2))


if __name__ == "__main__":
    main()
