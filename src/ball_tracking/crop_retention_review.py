"""Saved-PNG review of cap20 versus all exported floor candidates.

This module never selects or scores candidates. Saved reports are authoritative;
new presentation preserves their original detector/control provenance.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from .annotations import load_annotations
from .development_experiments import canonical_sha256, read_json, safe_path, sha256_file

OUTPUT_ROOT = "data/outputs/ball_tracking/crop_candidate_retention/rfdetr_medium_crop_candidate_retention_v0_1"
SCHEMA = "ball_crop_candidate_retention_window_review/v0.1"
ARMS = ("history_edge_tight_cost_tight", "history_edge_tight_cost_wide",
        "history_edge_wide_cost_tight", "history_edge_wide_cost_wide")
STEPS = ((.01, .01), (.01, .03), (.03, .01), (.03, .03))
PAIRS = tuple((arm, policy) for arm in ARMS for policy in ("cap20", "all"))
REFERENCE_KEYS = (("crop_raw", "saved"), ("crop_top_twenty", "saved"))
VIEW_KEYS = PAIRS + REFERENCE_KEYS
TILE_WIDTH, TILE_HEIGHT, TILE_HEADER, NATIVE_HEADER = 800, 552, 102, 116
FPS, FRAME_COUNT, THRESHOLD, RADIUS = 5.0, 25, .01, 10.0


@dataclass
class PreparedWindow:
    header: dict
    window: dict
    run: object
    truth: dict
    observations: dict
    reports: dict
    sources: dict
    verify: Callable[[], None]


def _binding(root, path):
    return {"path": Path(path).resolve().relative_to(Path(root).resolve()).as_posix(),
            "sha256": sha256_file(Path(path))}


def _verify_binding(root, binding):
    path = safe_path(Path(root), binding["path"])
    if not path.is_file() or sha256_file(path) != binding["sha256"]:
        raise ValueError("Retention review input binding mismatch: " + binding["path"])
    return path


def _read_png(root, binding):
    """Hash and decode the same bytes, never an unverified second file read."""
    import cv2
    import numpy as np
    path = safe_path(Path(root), binding["path"])
    if path.suffix.lower() != ".png":
        raise ValueError("Retention review accepts only bound PNG sources")
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != binding["sha256"]:
        raise ValueError("Retention review PNG hash mismatch")
    pixels = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
    if pixels is None:
        raise ValueError("Could not decode bound retention review PNG")
    return pixels


def _one(values, predicate, description):
    matches = [value for value in values if predicate(value)]
    if len(matches) != 1:
        raise ValueError("Missing/duplicate " + description)
    return matches[0]


def _validate_report(report, observation, run, labels, config):
    indices = [frame.frame_index for frame in run.frames]
    if (report["config"] != config or observation["config"] != config
            or report["localization_radius_px"] != RADIUS
            or report["source_video"] != run.source_video.to_dict()
            or report["window"] != run.window.to_dict()
            or report["possession_id"] != run.possession_id
            or report["observations_content_sha256"] != canonical_sha256(observation)
            or report["input_candidate_content_sha256"] != canonical_sha256(run.to_dict())
            or report["annotation_content_sha256"] != canonical_sha256(labels.to_dict())
            or [row["frame_index"] for row in report["frame_results"]] != indices
            or [row["frame_index"] for row in observation["frames"]] != indices):
        raise ValueError("Retention review report/config/provenance synchronization differs")


def prepare_window(root, context, window_id):
    """Load saved inputs only; a missing scoring artifact is a hard failure."""
    from .crop_retention_experiment import load_new_observations, load_saved_control
    from .crop_retention_evaluation import load_window_score

    root = Path(root).resolve()
    proposal = context["proposal"]
    window = _one(proposal["windows"], lambda w: w["window_id"] == window_id, "review window")
    score_path = safe_path(root, f"{OUTPUT_ROOT}/evaluation/windows/{window_id}.json", OUTPUT_ROOT)
    if not score_path.is_file():
        raise ValueError("Retention review requires completed saved window scoring")
    scored = load_window_score(root, context, window_id)
    run, _ = context["inputs"][window_id]
    indices = list(range(window["start_frame_index"], window["end_frame_index"] + 1))
    if len(indices) != FRAME_COUNT or [f.frame_index for f in run.frames] != indices:
        raise ValueError("Retention review requires the exact 25-frame source window")
    label = _one(proposal["scoring_labels"], lambda x: x["window_id"] == window_id, "review label")
    labels = load_annotations(_verify_binding(root, label["annotation"]))
    if (labels.annotation_set_id != window["annotation_set_id"]
            or labels.possession_id != run.possession_id or labels.source_video != run.source_video
            or labels.window.start_frame_index != indices[0] or labels.window.end_frame_index != indices[-1]
            or labels.window.selection_purpose != window["purpose"] or labels.review.status != "reviewed"):
        raise ValueError("Retention review label/source/window identity differs")
    bindings = [label["annotation"], window["crop_candidates"], _binding(root, score_path)]
    observations, reports, observation_sources, reloaders = {}, {}, [], []
    for key in VIEW_KEYS:
        arm, policy = key
        if policy == "all":
            unit = _one(proposal["new_selection_units"],
                        lambda u: u["window_id"] == window_id and u["config"]["arm"] == arm,
                        "new retention observation unit")
            observation = load_new_observations(root, context, unit)
            config = unit["config"]
            reloaders.append((key, lambda unit=unit: load_new_observations(root, context, unit)))
            origin = {"kind": "new_all", "comparison_unit_id": unit["comparison_unit_id"]}
        else:
            record = _one(proposal["saved_control_outputs"],
                          lambda c: c["window_id"] == window_id and c["config"]["arm"] == arm
                          and c["config"]["confidence_threshold"] == THRESHOLD,
                          "saved retention control")
            observation = load_saved_control(root, record, run=run)
            config = record["config"]
            bindings.append(record["file"])
            reloaders.append((key, lambda record=record: load_saved_control(root, record, run=run)))
            origin = {"kind": "saved_control", "record": record}
        cap = None if policy == "all" else config["candidate_cap"]
        if config["confidence_threshold"] != THRESHOLD or (policy == "all" and config["candidate_cap"] is not None):
            raise ValueError("Retention review only renders approved floor configurations")
        report = _one(scored["evaluation_reports"],
                      lambda r: r["config"]["arm"] == arm and r["config"]["candidate_cap"] == cap
                      and r["config"]["confidence_threshold"] == THRESHOLD
                      and r["localization_radius_px"] == RADIUS, "retention display report")
        _validate_report(report, observation, run, labels, config)
        observations[key], reports[key] = observation, report
        observation_sources.append({"arm": arm, "policy": policy,
                                    "observations_content_sha256": canonical_sha256(observation), **origin})
    sources = {}
    manifest_cache = {}
    for source in proposal["saved_source_pngs"]:
        if source["window_id"] != window_id:
            continue
        frame_index = source["frame_index"]
        if frame_index in sources or frame_index not in indices:
            raise ValueError("Duplicate/out-of-window retention source PNG")
        manifest_binding = source["original_manifest"]
        manifest_path = _verify_binding(root, manifest_binding)
        if manifest_binding["path"] not in manifest_cache:
            manifest_cache[manifest_binding["path"]] = read_json(manifest_path)
        manifest = manifest_cache[manifest_binding["path"]]
        asset = _one(manifest["assets"],
                     lambda a: a["path"] == source["manifest_asset_relative_path"], "bound source PNG asset")
        expected_path = safe_path(manifest_path.parent, asset["path"]).relative_to(root).as_posix()
        if source["source_png"] != {"path": expected_path, "sha256": asset["sha256"]}:
            raise ValueError("Retention source PNG differs from original manifest")
        sources[frame_index] = source["source_png"]
        bindings.extend((source["source_png"], manifest_binding))
    if set(sources) != set(indices):
        raise ValueError("Missing exact retention source frame PNG")
    bindings = list({(b["path"], b["sha256"]): b for b in bindings}.values())
    header = {"schema_version": SCHEMA, "experiment_spec_sha256": context["spec_sha256"],
              "renderer_code_commit": context["commit"], "window": window,
              "confidence_threshold": THRESHOLD, "radius_px": RADIUS,
              "layout": {"rows": 4, "columns": 3, "motion_rows": list(ARMS),
                         "columns_1_2": ["saved_cap20", "new_all"],
                         "third_column": ["unmarked_source", "saved_raw", "saved_top_twenty", "legend"]},
              "native_view_keys": [list(k) for k in VIEW_KEYS], "native_header_px": NATIVE_HEADER,
              "source_pngs": [{"frame_index": i, **sources[i]} for i in indices],
              "input_bindings": bindings, "observation_sources": observation_sources,
              "source_pixels": "bound saved unmarked PNGs; no source-video decode",
              "saved_controls": "new presentation only; original selection/scoring unchanged",
              "hidden_closeup_focus": "top exported candidate or frame center; never ball truth",
              "prior_motion_and_yolo_review": "complete; no repeat requested",
              "selected_method": None, "selected_operating_point": None, "quality_gate": None}

    def verify():
        for binding in bindings:
            _verify_binding(root, binding)
        for key, loader in reloaders:
            if canonical_sha256(loader()) != canonical_sha256(observations[key]):
                raise ValueError("Retention observations changed during review")

    verify()
    return PreparedWindow(header, window, run, labels.annotation_by_frame(), observations, reports, sources, verify)


def _selected(frame, observation):
    emitted = observation["emitted_candidate_indices"]
    available = {d.candidate_index for d in frame.detections}
    if len(set(emitted)) != len(emitted) or not set(emitted) <= available:
        raise ValueError("Invalid original candidate indices in retention review")
    return replace(frame, detections=tuple(d for d in frame.detections if d.candidate_index in emitted))


def _title(key):
    arm, policy = key
    if arm == "crop_raw":
        return "Saved raw: candidate availability, not trajectory"
    if arm == "crop_top_twenty":
        return "Saved top twenty: candidate availability"
    edge, cost = STEPS[ARMS.index(arm)]
    return f"Edge {edge:.2f} / cost {cost:.2f} | {'SAVED cap20' if policy == 'cap20' else 'NEW all'}"


def _details(frame, observation):
    emitted = observation["emitted_candidate_indices"]
    detections = {d.candidate_index: d for d in frame.detections}
    confidence = "; ".join(f"#{i} conf {detections[i].confidence:.6f}" for i in emitted[:1])
    first = confidence or "NULL: no current observation"
    history = observation["ranking"]
    if history is None:
        return f"{len(emitted)} saved candidates; availability reference", observation["decision_reason"]
    winner = history["winner"]
    margin = history["score_margin"] if "score_margin" in history else None
    detail = f"{first} | path score {winner['score']:.6f}"
    if margin is not None:
        detail += f" | margin {margin:.6f}"
    return detail, observation["decision_reason"]


def _text(image, text, position, width, size=.55, color=(235, 235, 235)):
    from .prepare_detection_visual_review import _put_fitted_text
    _put_fitted_text(image, text, position, width, size, color)


def _tile(body, lines):
    import cv2
    import numpy as np
    panel = np.zeros((TILE_HEIGHT, TILE_WIDTH, 3), np.uint8)
    scale = min(TILE_WIDTH/body.shape[1], (TILE_HEIGHT-TILE_HEADER)/body.shape[0])
    width, height = max(1, round(body.shape[1]*scale)), max(1, round(body.shape[0]*scale))
    x, y = (TILE_WIDTH-width)//2, TILE_HEADER+(TILE_HEIGHT-TILE_HEADER-height)//2
    panel[y:y+height, x:x+width] = cv2.resize(body, (width, height), interpolation=cv2.INTER_AREA)
    for i, line in enumerate(lines):
        _text(panel, line, (8, 21+24*i), TILE_WIDTH-16, .56 if i == 0 else .49)
    return panel


def render_frame(source, annotation, frame, observations, reports):
    """Render ten saved-result views; never infer an alternative winner."""
    import cv2
    import numpy as np
    from .prepare_detection_visual_review import DetectionReviewView, render_detection_overlay, render_truth_region_panel

    if set(observations) != set(VIEW_KEYS) or set(reports) != set(VIEW_KEYS):
        raise ValueError("All eight paired graphs and two availability references are required")
    if (annotation.frame_index != frame.frame_index
            or any(observations[k]["frame_index"] != frame.frame_index
                   or reports[k]["frame_index"] != frame.frame_index for k in VIEW_KEYS)):
        raise ValueError("Unsynchronized retention review frames")
    overlays, native, panels, views = {}, {}, {}, {}
    width = source.shape[1]
    for key in VIEW_KEYS:
        obs, result = observations[key], reports[key]
        selected = _selected(frame, obs)
        if key in PAIRS and len(selected.detections) > 1:
            raise ValueError("A graph review frame may emit at most one candidate")
        view = DetectionReviewView(_title(key), THRESHOLD, RADIUS, "descriptive_not_selected")
        overlay, _ = render_detection_overlay(source, annotation, selected, result, view)
        ranking = obs["ranking"]
        if ranking is not None:
            alternatives = ranking.get("current_alternatives")
            if alternatives is None:
                alternatives = [e for e in ranking.get("competing_endpoints", [])
                                if e["endpoint"] is not None and e["endpoint"][0] == frame.frame_index
                                and e["endpoint"][1] not in obs["emitted_candidate_indices"]][:3]
            available = {d.candidate_index: d for d in frame.detections}
            for alternative in alternatives[:3]:
                endpoint = alternative["endpoint"]
                if endpoint is None or endpoint[0] != frame.frame_index or endpoint[1] not in available:
                    raise ValueError("Saved current alternative is not an original current candidate")
                index = endpoint[1]
                x, y = map(round, available[index].center_xy_px)
                cv2.circle(overlay, (x, y), 12, (0, 190, 255), 1)
                cv2.putText(overlay, f"alt #{index}", (x+14, y-14), cv2.FONT_HERSHEY_SIMPLEX,
                            .42, (0, 190, 255), 1)
        detail, reason = _details(frame, obs)
        summary = f"MATCH {int(result['matched_candidate_index'] is not None)} | FP {result['false_positive_count']} | FN {result['false_negative_count']}"
        lines = (_title(key), f"Frame {frame.frame_index} | conf floor .01 | {summary}", detail, reason)
        header = np.zeros((NATIVE_HEADER, overlay.shape[1], 3), np.uint8)
        for i, line in enumerate((*lines[:3], "Amber alternatives are not emitted; path score/margin are not confidence")):
            _text(header, line, (10, 24+27*i), header.shape[1]-20, .64 if i == 0 else .54)
        native[key] = np.vstack((header, overlay))
        overlays[key], panels[key], views[key] = overlay, _tile(overlay[:, :width], lines), view
    legend = np.zeros((TILE_HEIGHT, TILE_WIDTH, 3), np.uint8)
    for i, line in enumerate(("CAP20 / ALL | one-factor comparison; no method selected",
            "Green MATCH / red FP / magenta duplicate / orange hidden FP",
            "Cyan reference / yellow uncertainty / blue raw 10px radius",
            "MATCH / FP are localization outcomes, not identity labels",
            "Original confidence qualifies and labels candidates",
            "Path score and margin are uncalibrated, not probabilities",
            "Amber alt # is context only, not an emitted observation",
            "NULL = no current observation; no invented coordinates",
            "Raw/top20 show availability and candidate burden",
            "Closeups include unmarked pixels at nearest-neighbor 4x",
            "Hidden closeup focus is NOT reviewed ball geometry",
            "Review these six new clips through their final frames",
            "Previous .20/.35 and YOLO reviews remain complete")):
        _text(legend, line, (10, 29+39*i), TILE_WIDTH-20, .54 if i == 0 else .48)
    reference_panels = [_tile(source, (f"Unmarked saved source | frame {frame.frame_index}",
                                      "Original PNG pixels; no source-video decode")),
                        panels[REFERENCE_KEYS[0]], panels[REFERENCE_KEYS[1]], legend]
    closeups, focuses = [], []
    for arm in ARMS:
        keys = ((arm, "cap20"), (arm, "all"))
        closeup, focus = render_truth_region_panel(source, [overlays[k] for k in keys], annotation,
                                                    frame, [views[k] for k in keys])
        closeups.append(closeup)
        focuses.append({"arm": arm, **focus})
    comparison = np.vstack([np.hstack((panels[arm, "cap20"], panels[arm, "all"], reference_panels[i]))
                            for i, arm in enumerate(ARMS)])
    return comparison, native, np.vstack(closeups), focuses


def _expected_assets(header):
    window = header["window"]
    paths = {"comparison_slow.mp4"}
    for index in range(window["start_frame_index"], window["end_frame_index"]+1):
        paths.update(f"{folder}/frame_{index:06d}.png"
                     for folder in ("comparison", "closeups", *(f"view_{i}" for i in range(len(VIEW_KEYS)))))
    return paths


def validate_review_bundle(root, bundle, header):
    """Validate immutable completed outputs and original sources, without decoding."""
    bundle = Path(bundle)
    value = read_json(bundle / "manifest.json")
    if (set(value) != {"header", "assets", "frame_evidence", "video_verification", "final_png_verification",
                       "final_frame", "human_visual_review"}
            or value["header"] != header or value["human_visual_review"] != "pending"):
        raise ValueError("Retention review manifest/provenance differs")
    expected = _expected_assets(header)
    paths = [a["path"] for a in value["assets"]]
    actual = {p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file() and p != bundle / "manifest.json"}
    window = header["window"]
    indices = list(range(window["start_frame_index"], window["end_frame_index"]+1))
    sources = {x["frame_index"]: {"path": x["path"], "sha256": x["sha256"]} for x in header["source_pngs"]}
    video = value["video_verification"]
    if (len(paths) != len(expected) or set(paths) != expected or actual != expected
            or [r["frame_index"] for r in value["frame_evidence"]] != indices
            or value["final_frame"] != indices[-1] or len(indices) != FRAME_COUNT
            or video["decoded_frames"] != FRAME_COUNT or video["fps"] != FPS
            or video["first_source_frame"] != indices[0] or video["last_source_frame"] != indices[-1]
            or video["dimensions_px"] != [TILE_WIDTH*3, TILE_HEIGHT*4]):
        raise ValueError("Incomplete retention review assets, frames or clip metadata")
    for row in value["frame_evidence"]:
        if row["source_png"] != sources[row["frame_index"]] or len(row["closeup_regions"]) != 4:
            raise ValueError("Retention review frame source/closeup provenance differs")
    final_suffix = f"/frame_{indices[-1]:06d}.png"
    expected_final = [{"path": a["path"], "width_px": a["width_px"], "height_px": a["height_px"]}
                      for a in value["assets"] if a["path"].endswith(final_suffix)]
    if len(expected_final) != 12 or value["final_png_verification"] != expected_final:
        raise ValueError("Retention review final PNG decode evidence differs")
    for binding in value["assets"]:
        _verify_binding(bundle, binding)
    for binding in header["input_bindings"]:
        _verify_binding(root, binding)
    return value


def _verify_video(path, first, last):
    import cv2
    capture, count = cv2.VideoCapture(str(path)), 0
    try:
        if not capture.isOpened():
            raise ValueError("Could not decode newly rendered retention clip")
        fps = capture.get(cv2.CAP_PROP_FPS)
        while True:
            ok, pixels = capture.read()
            if not ok:
                break
            if pixels.shape != (TILE_HEIGHT*4, TILE_WIDTH*3, 3):
                raise ValueError("Incorrect retention clip dimensions")
            count += 1
        if count != FRAME_COUNT or abs(fps-FPS) > 1e-6 or last-first+1 != count:
            raise ValueError("Retention clip must decode all 25 frames at 5 fps")
        return {"decoded_frames": count, "fps": fps, "dimensions_px": [TILE_WIDTH*3, TILE_HEIGHT*4],
                "first_source_frame": first, "last_source_frame": last}
    finally:
        capture.release()


def _verify_final_pngs(bundle, assets, last):
    records = []
    suffix = f"/frame_{last:06d}.png"
    for binding in assets:
        if not binding["path"].endswith(suffix):
            continue
        pixels = _read_png(bundle, binding)
        if pixels.shape != (binding["height_px"], binding["width_px"], 3):
            raise ValueError("Final retention PNG dimensions differ from written frame")
        records.append({"path": binding["path"], "width_px": pixels.shape[1], "height_px": pixels.shape[0]})
    if len(records) != 12:
        raise ValueError("Missing final retention comparison, closeup or native PNG")
    return records


def _write_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write("\n")


def render_prepared_window(root, prepared, target_dir):
    """Create one complete review unit atomically; retain incomplete staging."""
    import cv2
    root = Path(root).resolve()
    target = Path(target_dir)
    if not target.is_absolute():
        target = root / target
    target = safe_path(root, target.relative_to(root).as_posix(), OUTPUT_ROOT)
    prepared.verify()
    if target.exists():
        validate_review_bundle(root, target, prepared.header)
        return {"bundle": str(target), "reused": True, "human_visual_review": "pending"}
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.parent / (".pending_" + target.name + "_" + uuid.uuid4().hex)
    staging.mkdir()
    assets, evidence, writer = [], [], None
    try:
        for offset, frame in enumerate(prepared.run.frames):
            source = _read_png(root, prepared.sources[frame.frame_index])
            if source.shape != (prepared.run.source_video.height_px, prepared.run.source_video.width_px, 3):
                raise ValueError("Bound retention PNG dimensions differ from source metadata")
            observations = {key: prepared.observations[key]["frames"][offset] for key in VIEW_KEYS}
            reports = {key: prepared.reports[key]["frame_results"][offset] for key in VIEW_KEYS}
            comparison, native, closeups, focuses = render_frame(source, prepared.truth[frame.frame_index],
                                                                frame, observations, reports)
            images = [("comparison", comparison), ("closeups", closeups),
                      *((f"view_{i}", native[key]) for i, key in enumerate(VIEW_KEYS))]
            for folder, pixels in images:
                path = staging / folder / f"frame_{frame.frame_index:06d}.png"
                path.parent.mkdir(exist_ok=True)
                if not cv2.imwrite(str(path), pixels):
                    raise ValueError("Could not write retention review PNG")
                assets.append({**_binding(staging, path), "width_px": pixels.shape[1], "height_px": pixels.shape[0]})
            evidence.append({"frame_index": frame.frame_index, "source_png": prepared.sources[frame.frame_index],
                             "closeup_regions": focuses})
            if writer is None:
                writer = cv2.VideoWriter(str(staging / "comparison_slow.mp4"), cv2.VideoWriter_fourcc(*"mp4v"),
                                         FPS, (TILE_WIDTH*3, TILE_HEIGHT*4))
                if not writer.isOpened():
                    raise ValueError("Could not open retention review clip writer")
            if comparison.shape != (TILE_HEIGHT*4, TILE_WIDTH*3, 3):
                raise ValueError("Retention comparison image dimensions differ")
            writer.write(comparison)
        if writer is not None:
            writer.release()
            writer = None
        video_path = staging / "comparison_slow.mp4"
        video = _verify_video(video_path, prepared.window["start_frame_index"], prepared.window["end_frame_index"])
        assets.append(_binding(staging, video_path))
        final_pngs = _verify_final_pngs(staging, assets, prepared.window["end_frame_index"])
        _write_json(staging / "manifest.json", {"header": prepared.header, "assets": assets,
                    "frame_evidence": evidence, "video_verification": video,
                    "final_png_verification": final_pngs,
                    "final_frame": prepared.window["end_frame_index"], "human_visual_review": "pending"})
        validate_review_bundle(root, staging, prepared.header)
        prepared.verify()
        if target.exists():
            raise ValueError("Retention review destination appeared during rendering")
        staging.rename(target)
    except BaseException as error:
        if writer is not None:
            writer.release()
        _write_json(staging / "failure.json", {"status": "incomplete", "error_type": type(error).__name__,
                    "error": str(error), "completed_pngs": len(assets), "resume": "completed targets immutable; retained staging is not a completed unit"})
        raise
    return {"bundle": str(target), "reused": False, "assets": len(assets), "human_visual_review": "pending"}


def render_window(root, context, window_id, target_dir):
    return render_prepared_window(root, prepare_window(root, context, window_id), target_dir)


def finalize_review(root, context, target_dir=None):
    """Bind six completed window manifests without rendering or scoring."""
    root = Path(root).resolve()
    review_root = root / OUTPUT_ROOT / "review"
    if target_dir is not None:
        requested = Path(target_dir)
        if not requested.is_absolute():
            requested = root / requested
        review_root = safe_path(root, requested.relative_to(root).as_posix(), OUTPUT_ROOT)
    windows = []
    for window in context["proposal"]["windows"]:
        bundle = review_root / "windows" / window["window_id"]
        manifest = read_json(bundle / "manifest.json")
        header = manifest["header"]
        if (header["window"] != window or header["experiment_spec_sha256"] != context["spec_sha256"]
                or header["renderer_code_commit"] != context["commit"]):
            raise ValueError("Final retention review window provenance differs")
        validate_review_bundle(root, bundle, header)
        windows.append({"window_id": window["window_id"], "manifest": _binding(root, bundle / "manifest.json"),
                        "final_source_frame": window["end_frame_index"]})
    if len(windows) != 6 or len({w["window_id"] for w in windows}) != 6:
        raise ValueError("Retention review requires exactly six distinct completed windows")
    value = {"schema_version": "ball_crop_candidate_retention_review/v0.1",
             "experiment_spec_sha256": context["spec_sha256"], "renderer_code_commit": context["commit"],
             "windows": windows, "human_visual_review": "pending_six_new_floor_clips_only",
             "previous_motion_and_yolo_review": "complete_no_repeat", "selected_method": None,
             "selected_operating_point": None, "quality_gate": None}
    target = review_root / "manifest.json"
    if target.exists():
        if read_json(target) != value:
            raise ValueError("Existing retention review manifest differs")
    else:
        _write_json(target, value)
    return {"manifest": _binding(root, target), "windows": len(windows), "human_visual_review": value["human_visual_review"]}
