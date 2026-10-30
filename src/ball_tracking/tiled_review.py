"""Score and render the approved four-panel whole-frame/crop comparison."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from .annotations import load_annotations
from .development_experiments import bound_file, canonical_sha256, closed, read_json, safe_path, sha256_file
from .temporal_experiment import persist_once, spec_digest
from .tiled_candidates import candidate_run, crop_views, select_run
from .tiled_evaluation import ARMS, SELECTORS, load_output, score_one, score_experiment
from .tiled_experiment import OUTPUT_ROOT, preflight, unchanged


def crop_context(source):
    import cv2
    pixels = source.copy()
    for view, color in zip(crop_views(), ((255, 180, 80), (180, 255, 80), (80, 180, 255), (240, 120, 220))):
        x0, y0, x1, y1 = view["xyxy_half_open_px"]
        cv2.rectangle(pixels, (x0, y0), (x1-1, y1-1), color, 2)
        cv2.putText(pixels, view["view_id"], (x0+8, y0+28), cv2.FONT_HERSHEY_SIMPLEX, .8, color, 2)
    return pixels


def render_frame(source, annotation, raw_frame, variants):
    import cv2
    import numpy as np
    from .prepare_detection_visual_review import DetectionReviewView, render_detection_overlay, render_truth_region_panel
    if [(a, s) for a, s, _, _, _ in variants] != [(a, s) for a in ARMS for s in SELECTORS]:
        raise ValueError("All four comparison panels required in declared order")
    overlays, views, panels = [], [], []
    for arm, selector, threshold, frame, result in variants:
        title = ("Whole frame" if arm == "saved_whole_frame" else "Crop union") + (": all candidates" if selector == "raw" else ": top one")
        view = DetectionReviewView(title, threshold, 10.0, "descriptive_display_not_selected")
        overlay, _ = render_detection_overlay(source, annotation, frame, result, view)
        header = np.zeros((48, overlay.shape[1], 3), dtype=np.uint8)
        cv2.putText(header, title, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, .75, (255, 255, 255), 1)
        overlays.append(np.vstack((header, overlay)))
        views.append(view)
        panel = np.zeros((590, 960, 3), dtype=np.uint8)
        panel[50:] = cv2.resize(overlay[:, :source.shape[1]], (960, 540))
        cv2.putText(panel, f"{title} | conf {threshold} | frame {frame.frame_index}", (10, 21), cv2.FONT_HERSHEY_SIMPLEX, .68, (255, 255, 255), 1)
        details = f"TP {int(result['matched_candidate_index'] is not None)} | FP {result['false_positive_count']} | FN {result['false_negative_count']}"
        if not result["accepted_detection_count"]:
            details += " | no accepted observation"
        cv2.putText(panel, details, (10, 43), cv2.FONT_HERSHEY_SIMPLEX, .65, (230, 230, 230), 1)
        panels.append(panel)
    closeups = []
    for start in (0, 2):
        image, _ = render_truth_region_panel(source, [o[48:] for o in overlays[start:start+2]], annotation, raw_frame, views[start:start+2])
        closeups.append(image)
    return np.vstack((np.hstack(panels[:2]), np.hstack(panels[2:]))), overlays, np.vstack(closeups)


def validate_review_bundle(bundle, header):
    value = closed(read_json(bundle / "manifest.json"), {"header", "assets", "final_frames", "human_visual_review"}, "tiled review")
    if value["header"] != header or value["human_visual_review"] != "pending":
        raise ValueError("Review provenance mismatch")
    expected = set()
    for w in header["windows"]:
        for frame in range(w["start_frame_index"], w["end_frame_index"]+1):
            expected.add(f"{w['window_id']}/crop_context/frame_{frame:06d}.png")
            for threshold in (.2, .35):
                prefix = f"{w['window_id']}/confidence_{threshold}"
                expected.update(f"{prefix}/{folder}/frame_{frame:06d}.png" for folder in ("comparison", "closeups", "view_0", "view_1", "view_2", "view_3"))
        expected.update(f"{w['window_id']}/confidence_{threshold}/comparison_slow.mp4" for threshold in (.2, .35))
    paths = [a["path"] for a in value["assets"]]
    if len(paths) != len(expected) or set(paths) != expected or value["final_frames"] != [
            {"window_id": w["window_id"], "frame_index": w["end_frame_index"]} for w in header["windows"]]:
        raise ValueError("Incomplete/duplicate review assets or missing final frame")
    for record in value["assets"]:
        if sha256_file(safe_path(bundle, record["path"])) != record["sha256"]:
            raise ValueError("Tiled review asset hash mismatch")
    return value


def render_experiment(root, manifest_path):
    import cv2
    # Reconstruct all saved scoring cells; persist_once refuses any changed report.
    scored = score_experiment(root, manifest_path)
    m, p, raws, baseline, commit = preflight(root, manifest_path)
    header = {"schema_version": "ball_tiled_visual_review/v0.1", "experiment_spec_sha256": spec_digest(m),
              "renderer_code_commit": commit, "scoring_reports": scored["reports"], "windows": p["windows"],
              "confidence_views": [.2, .35], "radius_px": 10.0, "crop_views": crop_views(),
              "matching_rule": "raw center distance; uncertainty diagnostic only", "selected_operating_point": None, "quality_gate": None}
    bundle = safe_path(root, f"{OUTPUT_ROOT}/review/{canonical_sha256(header)[:32]}", OUTPUT_ROOT)
    if bundle.exists():
        validate_review_bundle(bundle, header)
        return {"bundle": str(bundle), "reused": True}
    bundle.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".pending_review_", dir=bundle.parent) as temporary:
        staging = Path(temporary).resolve()
        staging.relative_to(root.resolve())
        assets = []

        def add_asset(path):
            assets.append({"path": path.relative_to(staging).as_posix(), "sha256": sha256_file(path)})

        def png(path, pixels):
            path.parent.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(path), pixels):
                raise ValueError("Could not write review image")
            add_asset(path)

        for w, raw, label in zip(p["windows"], raws, p["scoring_labels"]):
            output = load_output(root, m, w, raw, baseline, commit)
            tiled = candidate_run(raw, output)
            labels = load_annotations(bound_file(root, label["annotation"], "configs/ball_tracking/annotations"))
            annotations = labels.annotation_by_frame()
            selections, evaluations = {}, {}
            for threshold in (.2, .35):
                for arm in ARMS:
                    run = raw if arm == "saved_whole_frame" else tiled
                    for selector in SELECTORS:
                        key = (arm, selector, threshold)
                        selections[key] = select_run(run, selector, threshold)
                        evaluations[key] = score_one(labels, run, arm, selector, threshold, 10.,
                                                    output["content_sha256"] if arm == "four_crop_union" else None, commit)
            capture = cv2.VideoCapture(str(root / raw.source_video.path))
            writers = {}
            try:
                if not capture.isOpened() or not capture.set(cv2.CAP_PROP_POS_FRAMES, raw.window.start_frame_index):
                    raise ValueError("Source video cannot be opened/positioned")
                for offset, raw_frame in enumerate(raw.frames):
                    ok, source = capture.read()
                    if (not ok or source.shape != (1080, 1920, 3)
                            or round(capture.get(cv2.CAP_PROP_POS_FRAMES)) != raw_frame.frame_index+1):
                        raise ValueError("Source decode/frame-index mismatch")
                    png(staging / w["window_id"] / "crop_context" / f"frame_{raw_frame.frame_index:06d}.png", crop_context(source))
                    for threshold in (.2, .35):
                        variants = [(a, s, threshold, selections[(a, s, threshold)].frames[offset],
                                     evaluations[(a, s, threshold)]["frame_results"][offset]) for a in ARMS for s in SELECTORS]
                        comparison, overlays, closeups = render_frame(source, annotations[raw_frame.frame_index], raw_frame, variants)
                        folder = staging / w["window_id"] / f"confidence_{threshold}"
                        for name, pixels in [("comparison", comparison), ("closeups", closeups), *((f"view_{i}", overlay) for i, overlay in enumerate(overlays))]:
                            png(folder / name / f"frame_{raw_frame.frame_index:06d}.png", pixels)
                        if threshold not in writers:
                            path = folder / "comparison_slow.mp4"
                            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 5., (1920, 1180))
                            if not writer.isOpened():
                                raise ValueError("Could not open review video writer")
                            writers[threshold] = (writer, path)
                        writers[threshold][0].write(comparison)
            finally:
                capture.release()
                for writer, _ in writers.values():
                    writer.release()
            for _, path in writers.values():
                capture, count = cv2.VideoCapture(str(path)), 0
                try:
                    while capture.read()[0]:
                        count += 1
                finally:
                    capture.release()
                if count != len(raw.frames):
                    raise ValueError("Review video failed final-frame validation")
                add_asset(path)
        persist_once(staging / "manifest.json", {"header": header, "assets": assets,
                     "final_frames": [{"window_id": w["window_id"], "frame_index": w["end_frame_index"]} for w in p["windows"]],
                     "human_visual_review": "pending"})
        validate_review_bundle(staging, header)
        unchanged(root, manifest_path, m, commit)
        preflight(root, manifest_path)
        staging.rename(bundle)
    return {"bundle": str(bundle), "reused": False, "human_visual_review": "pending"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("score", "render"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.repository_root.resolve()
    action = score_experiment if args.stage == "score" else render_experiment
    print(json.dumps(action(root, (root / args.manifest).resolve()), indent=2))


if __name__ == "__main__":
    main()
