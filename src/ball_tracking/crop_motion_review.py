"""Nine-panel review of crop controls and the independent motion factors."""
from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from .annotations import load_annotations, verify_source_video_contract
from .crop_motion_factorial import ARMS, experiment_grid
from .crop_motion_evaluation import score_experiment, selected_frame
from .crop_motion_experiment import OUTPUT_ROOT, load_observations, preflight, unchanged
from .development_experiments import bound_file, canonical_sha256, closed, read_json, safe_path, sha256_file
from .temporal_experiment import persist_once, spec_digest

THRESHOLDS = (.2, .35)
PANELS = (*ARMS, "unmarked_source", "legend")
PNG_FOLDERS = ("comparison", "closeups", "unmarked_source", *(f"view_{i}" for i in range(7)))
TILE_WIDTH, TILE_HEIGHT, TILE_HEADER = 800, 522, 72
NATIVE_HEADER = 90


def panel_title(config):
    """Both independently varied parameters remain visible on every graph view."""
    controls = {"crop_raw": "Crop: all candidates", "crop_top_one": "Crop: top one",
                "crop_top_twenty": "Crop: top twenty"}
    if config.arm in controls:
        return controls[config.arm]
    return f"History: edge {config.edge_step:.2f} / cost {config.cost_step:.2f}"


def _source_tile(source):
    import cv2
    import numpy as np
    body = np.zeros((TILE_HEIGHT-TILE_HEADER, TILE_WIDTH, 3), dtype=np.uint8)
    scale = min(body.shape[1]/source.shape[1], body.shape[0]/source.shape[0])
    width, height = max(1, round(source.shape[1]*scale)), max(1, round(source.shape[0]*scale))
    fitted = cv2.resize(source, (width, height), interpolation=cv2.INTER_AREA)
    x, y = (body.shape[1]-width)//2, (body.shape[0]-height)//2
    body[y:y+height, x:x+width] = fitted
    return body


def _legend(frame_index, threshold):
    import cv2
    import numpy as np
    panel = np.zeros((TILE_HEIGHT, TILE_WIDTH, 3), dtype=np.uint8)
    lines = (
        (f"Legend | frame {frame_index} | conf {threshold:.2f} | radius 10px", (255,255,255)),
        ("Edge: allowed displacement per source diagonal/frame", (230,230,230)),
        ("Cost: movement normalization; larger means lower cost", (230,230,230)),
        ("Green TP = matched; red FP = unmatched candidate", (0,220,0)),
        ("Magenta = duplicate FP; orange NV FP = hidden false alarm", (220,150,220)),
        ("Cyan cross = truth; yellow ring = annotation uncertainty", (255,255,0)),
        ("Blue ring = 10px raw-center matching radius", (255,100,0)),
        ("Orange alt = unselected hypothesis, context only", (0,190,255)),
        ("Missing = no current observation; nothing is filled", (230,230,230)),
        ("Path score / hypothesis margin are not probabilities", (230,230,230)),
        ("Native PNGs + JSON retain exact pixels and all hypotheses", (230,230,230)),
        ("Descriptive comparison; no operating point selected", (230,230,230)),
    )
    for index, (line, color) in enumerate(lines):
        cv2.putText(panel, line, (12, 30+index*40), cv2.FONT_HERSHEY_SIMPLEX,
                    .58 if index == 0 else .51, color, 1, cv2.LINE_AA)
    return panel


def render_frame(source, annotation, variants):
    """Render seven ordered arms, native overlays, and source-faithful closeups."""
    import cv2
    import numpy as np
    from .prepare_detection_visual_review import DetectionReviewView, render_detection_overlay, render_truth_region_panel

    if len(variants) != len(ARMS):
        raise ValueError("All seven motion-factorial arms are required")
    threshold = variants[0][3]
    configs = [c for c in experiment_grid() if c.confidence_threshold == threshold]
    if threshold not in THRESHOLDS or len(configs) != 7:
        raise ValueError("Undeclared motion-factorial review confidence")
    frame_index = variants[0][0].frame_index
    if (annotation.frame_index != frame_index
            or any(f.frame_index != frame_index or o["frame_index"] != frame_index
                   or r["frame_index"] != frame_index or t != threshold for f,o,r,t in variants)):
        raise ValueError("Motion-factorial panels are not synchronized")

    overlays, views, panels = [], [], []
    for config, (frame, observation, result, _) in zip(configs, variants):
        title = panel_title(config)
        selected = selected_frame(frame, observation)
        view = DetectionReviewView(title, threshold, 10.0, "descriptive_display_not_selected")
        overlay, _ = render_detection_overlay(source, annotation, selected, result, view)
        history = observation["ranking"]
        details = observation["decision_reason"]
        if history is not None:
            winner = history["winner"]
            details += f" | path score {winner['score']:.3f}"
            current = [e for e in history["competing_endpoints"] if e["endpoint"] is not None
                       and e["endpoint"][0] == frame_index
                       and e["endpoint"][1] not in observation["emitted_candidate_indices"]]
            detections = {d.candidate_index: d for d in frame.detections}
            for alternative in current[:3]:
                index = alternative["endpoint"][1]
                x, y = map(round, detections[index].center_xy_px)
                cv2.circle(overlay, (x,y), 12, (0,190,255), 1)
                cv2.putText(overlay, f"alt #{index}", (x+14,y-14), cv2.FONT_HERSHEY_SIMPLEX,
                            .45, (0,190,255), 1)
        native_header = np.zeros((NATIVE_HEADER, overlay.shape[1], 3), dtype=np.uint8)
        for text, y, size, color in (
                (title, 25, .75, (255,255,255)),
                (details, 51, .60, (230,230,230)),
                ("Orange alt = context only; path score is not detector confidence or probability",
                 77, .55, (0,190,255))):
            cv2.putText(native_header, text, (10,y), cv2.FONT_HERSHEY_SIMPLEX, size, color, 1)
        overlays.append(np.vstack((native_header, overlay)))
        views.append(view)

        panel = np.zeros((TILE_HEIGHT, TILE_WIDTH, 3), dtype=np.uint8)
        panel[TILE_HEADER:] = _source_tile(overlay[:, :source.shape[1]])
        summary = (f"TP {int(result['matched_candidate_index'] is not None)}"
                   f" | FP {result['false_positive_count']} | FN {result['false_negative_count']}")
        for text, y, size in ((f"{title} | conf {threshold:.2f} | frame {frame_index}", 20, .53),
                              (summary, 42, .55), (details, 64, .41)):
            cv2.putText(panel, text, (8,y), cv2.FONT_HERSHEY_SIMPLEX, size, (230,230,230), 1)
        panels.append(panel)

    source_panel = np.zeros((TILE_HEIGHT, TILE_WIDTH, 3), dtype=np.uint8)
    source_panel[TILE_HEADER:] = _source_tile(source)
    cv2.putText(source_panel, f"Unmarked source | frame {frame_index}", (8,25),
                cv2.FONT_HERSHEY_SIMPLEX, .65, (255,255,255), 1)
    cv2.putText(source_panel, "Native source PNG preserves the original pixels", (8,55),
                cv2.FONT_HERSHEY_SIMPLEX, .52, (230,230,230), 1)
    panels.extend((source_panel, _legend(frame_index, threshold)))

    # The existing source-faithful helper takes two views per row. The last
    # row contains wide/wide and another explicitly unmarked source column.
    closeup_overlays = [o[NATIVE_HEADER:] for o in overlays] + [source]
    closeup_views = [*views, DetectionReviewView("UNMARKED SOURCE", threshold, 10.0,
                                               "source_context_only")]
    closeups = [render_truth_region_panel(source, closeup_overlays[i:i+2], annotation,
                                         variants[0][0], closeup_views[i:i+2])[0]
                for i in (0,2,4,6)]
    comparison = np.vstack([np.hstack(panels[i:i+3]) for i in (0,3,6)])
    return comparison, overlays, np.vstack(closeups)


def validate_review_bundle(bundle, header):
    value = closed(read_json(bundle/"manifest.json"), {"header","assets","final_frames","human_visual_review"},
                   "crop motion-factorial review")
    if value["header"] != header or value["human_visual_review"] != "pending":
        raise ValueError("Motion-factorial review provenance mismatch")
    expected = set()
    for window in header["windows"]:
        for threshold in THRESHOLDS:
            prefix = f"{window['window_id']}/confidence_{threshold}"
            expected.add(f"{prefix}/comparison_slow.mp4")
            for frame in range(window["start_frame_index"], window["end_frame_index"]+1):
                expected.update(f"{prefix}/{folder}/frame_{frame:06d}.png" for folder in PNG_FOLDERS)
    paths = [a["path"] for a in value["assets"]]
    actual = {f.relative_to(bundle).as_posix() for f in bundle.rglob("*")
              if f.is_file() and f != bundle/"manifest.json"}
    if (len(paths) != len(expected) or set(paths) != expected or actual != expected
            or value["final_frames"] != [{"window_id":w["window_id"],"frame_index":w["end_frame_index"]}
                                         for w in header["windows"]]):
        raise ValueError("Incomplete/duplicate motion review assets or missing final frame")
    for item in value["assets"]:
        closed(item, {"path","sha256"}, "motion review asset")
        if sha256_file(safe_path(bundle, item["path"])) != item["sha256"]:
            raise ValueError("Motion-factorial review asset hash mismatch")
    return value


def render_experiment(root, path):
    import cv2
    scored = score_experiment(root, path)
    m, p, inputs, commit = preflight(root, path)
    grids = {purpose: read_json(root/b["path"])
             for purpose,b in zip(p["pool_separation"], scored["reports"])}
    header = {"schema_version":"ball_crop_motion_factorial_visual_review/v0.1",
              "experiment_spec_sha256":spec_digest(m), "renderer_code_commit":commit,
              "scoring_reports":scored["reports"], "windows":p["windows"],
              "confidence_views":list(THRESHOLDS), "radius_px":10.0, "panels":list(PANELS),
              "layout":{"rows":3,"columns":3},
              "view_configs":[asdict(c) for c in experiment_grid() if c.confidence_threshold in THRESHOLDS],
              "original_control_reports":p["saved_ranking_scoring_reports"],
              "native_unmarked_source_pngs":True, "selected_operating_point":None, "quality_gate":None}
    bundle = safe_path(root, f"{OUTPUT_ROOT}/review/{canonical_sha256(header)[:32]}", OUTPUT_ROOT)

    def verify_review_inputs():
        for (_,run,_),label in zip(inputs, p["scoring_labels"]):
            verify_source_video_contract(run.source_video, root)
            bound_file(root, label["annotation"], "configs/ball_tracking/annotations")

    verify_review_inputs()
    if bundle.exists():
        validate_review_bundle(bundle, header)
        unchanged(root, path, m, commit)
        return {"bundle":str(bundle), "reused":True}
    bundle.parent.mkdir(parents=True, exist_ok=True)
    configs = {threshold: tuple(c for c in experiment_grid() if c.confidence_threshold == threshold)
               for threshold in THRESHOLDS}
    with tempfile.TemporaryDirectory(prefix=".pending_review_", dir=bundle.parent) as temporary:
        staging = Path(temporary).resolve()
        staging.relative_to(root.resolve())
        assets = []

        def add(target):
            assets.append({"path":target.relative_to(staging).as_posix(), "sha256":sha256_file(target)})

        for window,(_,run,digest),label in zip(p["windows"], inputs, p["scoring_labels"]):
            labels = load_annotations(bound_file(root, label["annotation"], "configs/ball_tracking/annotations"))
            truth = labels.annotation_by_frame()
            observations, reports = {}, {}
            for threshold in THRESHOLDS:
                for config in configs[threshold]:
                    observations[config.variant_id] = load_observations(root,m,window,run,digest,config,commit)
                    matching = [r for r in grids[window["purpose"]]["evaluation_reports"]
                                if r["possession_id"] == run.possession_id
                                and r["variant_id"] == config.variant_id and r["localization_radius_px"] == 10.0]
                    if len(matching) != 1:
                        raise ValueError("Missing or duplicate motion review scoring report")
                    reports[config.variant_id] = matching[0]
            capture = cv2.VideoCapture(str(safe_path(root, run.source_video.path.as_posix(), "data/clips")))
            writers = {}
            try:
                if not capture.isOpened() or not capture.set(cv2.CAP_PROP_POS_FRAMES, run.window.start_frame_index):
                    raise ValueError("Could not open/seek motion review source")
                for offset,frame in enumerate(run.frames):
                    ok, source = capture.read()
                    if (not ok or source.shape != (run.source_video.height_px,run.source_video.width_px,3)
                            or round(capture.get(cv2.CAP_PROP_POS_FRAMES)) != frame.frame_index+1):
                        raise ValueError("Incomplete or incorrect motion review source decode")
                    for threshold in THRESHOLDS:
                        variants = [(frame, observations[c.variant_id]["frames"][offset],
                                     reports[c.variant_id]["frame_results"][offset], threshold)
                                    for c in configs[threshold]]
                        comparison, overlays, closeups = render_frame(source, truth[frame.frame_index], variants)
                        folder = staging/window["window_id"]/f"confidence_{threshold}"
                        for name,pixels in [("comparison",comparison), ("closeups",closeups),
                                            ("unmarked_source",source),
                                            *((f"view_{i}",v) for i,v in enumerate(overlays))]:
                            target = folder/name/f"frame_{frame.frame_index:06d}.png"
                            target.parent.mkdir(parents=True, exist_ok=True)
                            if not cv2.imwrite(str(target), pixels):
                                raise ValueError("Could not write motion review PNG")
                            add(target)
                        if threshold not in writers:
                            target = folder/"comparison_slow.mp4"
                            writer = cv2.VideoWriter(str(target), cv2.VideoWriter_fourcc(*"mp4v"),
                                                     5.0, (comparison.shape[1],comparison.shape[0]))
                            if not writer.isOpened():
                                raise ValueError("Could not open motion review writer")
                            writers[threshold] = (writer,target)
                        writers[threshold][0].write(comparison)
            finally:
                capture.release()
                for writer,_ in writers.values():
                    writer.release()
            if len(writers) != 2:
                raise ValueError("Incomplete motion review confidence clips")
            for _,target in writers.values():
                video, count = cv2.VideoCapture(str(target)), 0
                try:
                    if not video.isOpened():
                        raise ValueError("Could not decode motion review clip")
                    while True:
                        ok, pixels = video.read()
                        if not ok:
                            break
                        if pixels.shape != (TILE_HEIGHT*3, TILE_WIDTH*3, 3):
                            raise ValueError("Incorrect motion review clip dimensions")
                        count += 1
                    if count != 25 or video.get(cv2.CAP_PROP_FPS) != 5.0:
                        raise ValueError("Motion review clip did not decode all 25 frames at 5 fps")
                finally:
                    video.release()
                add(target)
        persist_once(staging/"manifest.json", {"header":header, "assets":assets,
                     "final_frames":[{"window_id":w["window_id"],"frame_index":w["end_frame_index"]}
                                     for w in p["windows"]], "human_visual_review":"pending"})
        validate_review_bundle(staging, header)
        verify_review_inputs()
        unchanged(root, path, m, commit)
        staging.rename(bundle)
    return {"bundle":str(bundle), "reused":False, "assets":len(assets), "human_visual_review":"pending"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("score","render"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.repository_root.resolve()
    action = score_experiment if args.stage == "score" else render_experiment
    print(json.dumps(action(root, (root/args.manifest).resolve()), indent=2))


if __name__ == "__main__":
    main()
