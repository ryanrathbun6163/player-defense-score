"""Separate scoring and synchronized review stages for temporal observations."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from .annotations import load_annotations, verify_source_video_contract
from .development_experiments import bound_file, canonical_sha256, closed, read_json, safe_path, sha256_file
from .temporal_association import RADII, experiment_grid, validate_observations
from .temporal_evaluation import aggregate_temporal_reports, evaluate_observations, selected_frame
from .temporal_experiment import (
    OUTPUT_ROOT, clean_commit, file_binding, load_inputs, load_manifest, output_path,
    persist_once, preflight, spec_digest,
)


def load_observations(root, manifest, window, run, config, commit):
    path = output_path(root, manifest, window, config)
    envelope = closed(read_json(path), {"experiment_spec_sha256", "input_detection_file", "observations"}, "observation envelope")
    value = envelope["observations"]
    if (envelope["experiment_spec_sha256"] != spec_digest(manifest)
            or envelope["input_detection_file"] != window["detection"]
            or value["association_code_commit"] != commit
            or validate_observations(value, run) != config):
        raise ValueError("Observation manifest/commit/variant binding mismatch")
    return value


def score_experiment(root, manifest_path):
    manifest, runs, commit = preflight(root, manifest_path)
    pools = {purpose: [] for purpose in ("representative_evaluation", "challenge_evaluation")}
    label_bindings = []
    for window, run, label_record in zip(manifest["windows"], runs, manifest["scoring_labels"]):
        path = bound_file(root, label_record["annotation"], "configs/ball_tracking/annotations")
        labels = load_annotations(path)
        if labels.window.selection_purpose != window["purpose"]:
            raise ValueError("Scoring pool differs from reviewed labels")
        label_bindings.append(label_record)
        for config in experiment_grid():
            observations = load_observations(root, manifest, window, run, config, commit)
            for radius in RADII:
                pools[window["purpose"]].append(evaluate_observations(labels, run, observations, radius, commit))
    outputs = []
    for purpose, reports in pools.items():
        aggregates = []
        for config in experiment_grid():
            for radius in RADII:
                group = [r for r in reports if r["variant_id"] == config.variant_id and r["localization_radius_px"] == radius]
                if len(group) != 3:
                    raise ValueError("Incomplete scoring pool")
                aggregates.append(aggregate_temporal_reports(group))
        report = {"schema_version": "ball_temporal_pool_grid/v0.1", "selection_purpose": purpose,
                  "experiment_spec_sha256": spec_digest(manifest), "code_commit": commit,
                  "annotation_bindings": label_bindings, "evaluation_reports": reports,
                  "aggregate_results": aggregates, "selected_operating_point": None, "quality_gate": None}
        path = safe_path(root, f"{manifest['output_root']}/evaluation/{purpose}.json", OUTPUT_ROOT)
        persist_once(path, report)
        outputs.append(file_binding(root, path))
    _unchanged(root, manifest_path, manifest, commit)
    for record in label_bindings:
        bound_file(root, record["annotation"], "configs/ball_tracking/annotations")
    return {"reports": outputs, "per_window_reports": sum(len(r) for r in pools.values()), "aggregate_cells_per_pool": 270}


def _unchanged(root, manifest_path, manifest, commit):
    if clean_commit(root) != commit or load_manifest(root, manifest_path) != manifest:
        raise ValueError("Git or manifest changed during stage")
    load_inputs(root, manifest)


def render_frame(source, annotation, raw_frame, variants):
    """Six views with full-size originals and paired native truth-region panels."""
    import cv2
    import numpy as np
    from .prepare_detection_visual_review import (
        DetectionReviewView, render_detection_overlay, render_truth_region_panel,
    )
    if len(variants) != 6:
        raise ValueError("Review requires both controls and all four tracklet variants")
    overlays, views = [], []
    for config, temporal_frame, result in variants:
        title = config.arm if config.arm != "tracklets" else f"tracklets step={config.step_limit} gap={config.max_missing_frames}"
        view = DetectionReviewView(title, config.confidence_threshold, 10.0, "descriptive_display_not_selected")
        selected = selected_frame(raw_frame, temporal_frame)
        overlay, _ = render_detection_overlay(source, annotation, selected, result, view)
        for decision in temporal_frame["candidate_decisions"]:
            if decision["disposition"] == "emitted" and decision["tracklet_id"] is not None:
                detection = raw_frame.detections[decision["candidate_index"]]
                xy = (round(detection.center_xy_px[0]) + 12,
                      round(detection.center_xy_px[1]) + 36)
                cv2.putText(overlay, f"T{decision['tracklet_id']}", xy, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        # A separate border leaves every source pixel intact and makes empty states explicit.
        header = np.zeros((48, overlay.shape[1], 3), dtype=np.uint8)
        cv2.putText(header, f"{title} | {temporal_frame['output_state']}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 1)
        overlays.append(np.vstack((header, overlay)))
        views.append(view)
    closeups = []
    for start in (0, 2, 4):
        panel, _ = render_truth_region_panel(source, [o[48:] for o in overlays[start:start + 2]],
                                             annotation, raw_frame, views[start:start + 2])
        closeups.append(panel)
    panels = []
    for index, overlay in enumerate(overlays):
        config, temporal_frame, result = variants[index]
        body = overlay[48:]
        scale = min(800 / body.shape[1], 370 / body.shape[0])
        resized = cv2.resize(body, (round(body.shape[1] * scale), round(body.shape[0] * scale)))
        canvas = np.zeros((420, 800, 3), dtype=np.uint8)
        canvas[50:50 + resized.shape[0], :resized.shape[1]] = resized
        title = config.arm if config.arm != "tracklets" else f"tracklets | step {config.step_limit} | gap {config.max_missing_frames}"
        title += f" | conf {config.confidence_threshold} | frame {raw_frame.frame_index}"
        details = (f"{temporal_frame['output_state']} | TP {int(result['matched_candidate_index'] is not None)}"
                   f" | FP {result['false_positive_count']} | FN {result['false_negative_count']}")
        cv2.putText(canvas, title, (10, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 1)
        cv2.putText(canvas, details, (10, 43), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (230, 230, 230), 1)
        panels.append(canvas)
    comparison = np.vstack((np.hstack(panels[:3]), np.hstack(panels[3:])))
    return comparison, overlays, np.vstack(closeups)


def _asset(path, bundle):
    return {"path": path.relative_to(bundle).as_posix(), "sha256": sha256_file(path)}


def validate_review_bundle(path, header):
    manifest = closed(read_json(path / "manifest.json"), {"header", "assets", "final_frames", "human_visual_review"}, "review bundle")
    if manifest["header"] != header or manifest["human_visual_review"] != "pending":
        raise ValueError("Review bundle input provenance mismatch")
    expected = set()
    for window in header["windows"]:
        for threshold in (0.2, 0.35):
            prefix = f"{window['window_id']}/confidence_{threshold}"
            expected.add(f"{prefix}/comparison_slow.mp4")
            for frame in range(window["start_frame_index"], window["end_frame_index"] + 1):
                expected.update(f"{prefix}/{folder}/frame_{frame:06d}.png" for folder in ("comparison", "closeups", *(f"view_{i}" for i in range(6))))
    actual = [a["path"] for a in manifest["assets"]]
    finals = [{"window_id": w["window_id"], "frame_index": w["end_frame_index"]} for w in header["windows"]]
    if set(actual) != expected or len(actual) != len(expected) or manifest["final_frames"] != finals:
        raise ValueError("Incomplete/duplicate review assets or missing final frame")
    for record in manifest["assets"]:
        asset = safe_path(path, record["path"])
        if sha256_file(asset) != record["sha256"]:
            raise ValueError("Review asset hash mismatch")
    return manifest


def render_experiment(root, manifest_path):
    import cv2
    manifest, runs, commit = preflight(root, manifest_path)
    grids = {}
    grid_bindings = []
    for purpose in ("representative_evaluation", "challenge_evaluation"):
        path = safe_path(root, f"{manifest['output_root']}/evaluation/{purpose}.json", OUTPUT_ROOT)
        grid = read_json(path)
        if grid["experiment_spec_sha256"] != spec_digest(manifest) or grid["code_commit"] != commit:
            raise ValueError("Scoring provenance mismatch")
        grids[purpose] = grid
        grid_bindings.append(file_binding(root, path))
    header = {"schema_version": "ball_temporal_visual_review/v0.1", "experiment_spec_sha256": spec_digest(manifest),
              "renderer_code_commit": commit, "scoring_reports": grid_bindings,
              "windows": manifest["windows"], "confidence_views": [0.2, 0.35], "radius_px": 10.0,
              "pixel_matching": "raw distance; uncertainty diagnostic only",
              "selected_operating_point": None, "quality_gate": None}
    bundle = safe_path(root, f"{manifest['output_root']}/review/{canonical_sha256(header)[:32]}", OUTPUT_ROOT)
    # Validate sources and labels even when reusing an existing bundle.
    for run, record in zip(runs, manifest["scoring_labels"]):
        verify_source_video_contract(run.source_video, root)
        bound_file(root, record["annotation"], "configs/ball_tracking/annotations")
    if bundle.exists():
        validate_review_bundle(bundle, header)
        return {"bundle": str(bundle), "reused": True}
    bundle.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".pending_review_", dir=bundle.parent) as temporary:
        staging = Path(temporary).resolve()
        staging.relative_to(root.resolve())
        assets, final_frames = [], []
        for window, run, label_record in zip(manifest["windows"], runs, manifest["scoring_labels"]):
            labels = load_annotations(bound_file(root, label_record["annotation"], "configs/ball_tracking/annotations"))
            annotations = labels.annotation_by_frame()
            configs = [c for c in experiment_grid() if c.confidence_threshold in (0.2, 0.35)]
            observations, evaluations = {}, {}
            for config in configs:
                obs = load_observations(root, manifest, window, run, config, commit)
                score = evaluate_observations(labels, run, obs, 10.0, commit)
                saved = [r for r in grids[window["purpose"]]["evaluation_reports"]
                         if r["variant_id"] == config.variant_id and r["possession_id"] == run.possession_id
                         and r["localization_radius_px"] == 10.0]
                if saved != [score]:
                    raise ValueError("Scoring report differs from recomputed review evidence")
                observations[config.variant_id], evaluations[config.variant_id] = obs, score
            capture = cv2.VideoCapture(str(root / run.source_video.path))
            writers = {}
            try:
                if not capture.isOpened():
                    raise ValueError("Source video cannot be opened")
                capture.set(cv2.CAP_PROP_POS_FRAMES, run.window.start_frame_index)
                for offset, raw_frame in enumerate(run.frames):
                    ok, source = capture.read()
                    if not ok or source.shape[:2] != (run.source_video.height_px, run.source_video.width_px):
                        raise ValueError("Incomplete source decode")
                    for threshold in (0.2, 0.35):
                        variants = [(c, observations[c.variant_id]["frames"][offset], evaluations[c.variant_id]["frame_results"][offset])
                                    for c in configs if c.confidence_threshold == threshold]
                        comparison, overlays, closeups = render_frame(source, annotations[raw_frame.frame_index], raw_frame, variants)
                        folder = staging / window["window_id"] / f"confidence_{threshold}"
                        for name, pixels in [("comparison", comparison), ("closeups", closeups),
                                             *((f"view_{i}", v) for i, v in enumerate(overlays))]:
                            path = folder / name / f"frame_{raw_frame.frame_index:06d}.png"
                            path.parent.mkdir(parents=True, exist_ok=True)
                            if not cv2.imwrite(str(path), pixels):
                                raise ValueError("Could not write review PNG")
                            assets.append(_asset(path, staging))
                        if threshold not in writers:
                            path = folder / "comparison_slow.mp4"
                            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 5.0, (comparison.shape[1], comparison.shape[0]))
                            if not writer.isOpened():
                                raise ValueError("Could not open review video writer")
                            writers[threshold] = (writer, path)
                        writers[threshold][0].write(comparison)
            finally:
                capture.release()
                for writer, _ in writers.values():
                    writer.release()
            for _, path in writers.values():
                video, count = cv2.VideoCapture(str(path)), 0
                try:
                    while video.read()[0]:
                        count += 1
                finally:
                    video.release()
                if count != len(run.frames):
                    raise ValueError("Review video failed complete-frame validation")
                assets.append(_asset(path, staging))
            final_frames.append({"window_id": window["window_id"], "frame_index": run.window.end_frame_index})
        persist_once(staging / "manifest.json", {"header": header, "assets": assets,
                                               "final_frames": final_frames, "human_visual_review": "pending"})
        validate_review_bundle(staging, header)
        _unchanged(root, manifest_path, manifest, commit)
        # Atomic directory rename, only to a new verified path below OUTPUT_ROOT.
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
