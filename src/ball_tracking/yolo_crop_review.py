"""Paired detector review from saved YOLO outputs and immutable RF-DETR PNGs."""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from .annotations import load_annotations
from .crop_motion_evaluation import selected_frame
from .crop_motion_factorial import experiment_grid as control_grid
from .development_experiments import (
    bound_file, canonical_sha256, closed, read_json, require_digest, safe_path, sha256_file,
)
from .temporal_experiment import file_binding, persist_once, spec_digest

THRESHOLDS = (.2, .35)
CONTROL_ARMS = ("crop_raw", "crop_top_one", "crop_top_twenty")
YOLO_ARMS = ("yolo_all_exported", "yolo_top_one", "yolo_top_twenty")
OUTPUT_ROOT = "data/outputs/ball_tracking/detector_challenger/yolo11x_crop_development_comparison_v0_1"
PRIOR_ROOT = "data/outputs/ball_tracking/crop_player_context"
SAVED_PIXEL_ROOT = "data/outputs/ball_tracking/crop_motion_factorial"
PNG_FOLDERS = ("comparison", "closeups", "yolo_view_0", "yolo_view_1", "yolo_view_2")
TILE_WIDTH, TILE_HEIGHT, TILE_HEADER, NATIVE_HEADER = 800, 522, 90, 90
LAYOUT = [["rfdetr_all_exported", "yolo_all_exported", "unmarked_source"],
          ["rfdetr_top_one", "yolo_top_one", "detector_policy"],
          ["rfdetr_top_twenty", "yolo_top_twenty", "legend"]]


@dataclass
class PreparedReview:
    header: dict
    windows: list[dict]
    verify: Callable[[], None]


def _verify_binding(root, item):
    require_digest(item["sha256"], "review input")
    target = safe_path(root, item["path"])
    if not target.is_file() or sha256_file(target) != item["sha256"]:
        raise ValueError("YOLO review input binding mismatch: " + item["path"])
    return target


def _read_png(root, item):
    """Decode exactly the bytes whose hash is checked, eliminating a hash/read race."""
    import cv2
    import numpy as np
    target = safe_path(root, item["path"], SAVED_PIXEL_ROOT)
    require_digest(item["sha256"], "saved PNG")
    if target.suffix != ".png":
        raise ValueError("Only saved development PNGs may supply review pixels")
    content = target.read_bytes()
    if hashlib.sha256(content).hexdigest() != item["sha256"]:
        raise ValueError("Saved PNG bytes changed before decode")
    pixels = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if pixels is None:
        raise ValueError("Could not decode saved development PNG")
    return pixels


def load_reused_assets(root, proposal):
    """Bind exact old native/source keys and the inference PNG inventory."""
    path = bound_file(root, proposal["reused_native_review_manifest"], PRIOR_ROOT)
    prior = closed(read_json(path), {"header", "assets", "final_frames", "frame_evidence", "human_visual_review"},
                   "prior player-context review")
    header = prior["header"]
    if (header["schema_version"] != "ball_crop_player_context_visual_review/v0.1"
            or header["windows"] != proposal["windows"]
            or header["confidence_views"] != list(THRESHOLDS) or header["radius_px"] != 10
            or header["reused_native_header_px"] != NATIVE_HEADER
            or header["native_reused_arms"] != list(dict.fromkeys(c.arm for c in control_grid()))
            or header["selected_operating_point"] is not None or header["quality_gate"] is not None):
        raise ValueError("Prior native review configuration/window provenance differs")
    if prior["final_frames"] != [{"window_id": w["window_id"], "frame_index": w["end_frame_index"]}
                                 for w in proposal["windows"]]:
        raise ValueError("Prior native final-frame declaration differs")
    inventory = {}
    for row in proposal["inference_source_frames"]:
        key = row["window_id"], row["frame_index"]
        if key in inventory:
            raise ValueError("Duplicate inference source frame")
        inventory[key] = row["source_png"]
    expected_frames = {(w["window_id"], f) for w in proposal["windows"]
                       for f in range(w["start_frame_index"], w["end_frame_index"] + 1)}
    if set(inventory) != expected_frames:
        raise ValueError("Inference source inventory differs from exact review windows")
    indexed = {}
    for row in header["reused_assets"]:
        closed(row, {"window_id", "confidence_threshold", "frame_index", "arm", "path", "sha256"}, "saved native reference")
        key = row["window_id"], row["confidence_threshold"], row["frame_index"], row["arm"]
        if key in indexed:
            raise ValueError("Duplicate saved native identity")
        safe_path(root, row["path"], SAVED_PIXEL_ROOT)
        require_digest(row["sha256"], "saved native reference")
        if row["arm"] not in (*header["native_reused_arms"], "unmarked_source"):
            raise ValueError("Unexpected saved native arm")
        folder = "unmarked_source" if row["arm"] == "unmarked_source" else f"view_{header['native_reused_arms'].index(row['arm'])}"
        suffix = f"/{row['window_id']}/confidence_{row['confidence_threshold']}/{folder}/frame_{row['frame_index']:06d}.png"
        if not row["path"].endswith(suffix):
            raise ValueError("Saved native path differs from exact frame/view identity")
        indexed[key] = row
    all_old_arms = (*header["native_reused_arms"], "unmarked_source")
    expected = {(wid, c, f, arm) for wid, f in expected_frames for c in THRESHOLDS for arm in all_old_arms}
    if set(indexed) != expected:
        raise ValueError("Prior native inventory has missing or extra frame/view keys")
    records = []
    for w in proposal["windows"]:
        for c in THRESHOLDS:
            for f in range(w["start_frame_index"], w["end_frame_index"] + 1):
                for arm in (*CONTROL_ARMS, "unmarked_source"):
                    row = indexed[w["window_id"], c, f, arm]
                    _verify_binding(root, row)
                    if arm == "unmarked_source":
                        source = inventory[w["window_id"], f]
                        safe_path(root, source["path"], SAVED_PIXEL_ROOT)
                        _verify_binding(root, source)
                        if row["sha256"] != source["sha256"]:
                            raise ValueError("Inference and review source pixels differ")
                    records.append(row)
    return records


def _report(pool, run, config, observations):
    matches = [r for r in pool["evaluation_reports"] if r["possession_id"] == run.possession_id
               and r["variant_id"] == config.variant_id and r["localization_radius_px"] == 10]
    if len(matches) != 1:
        raise ValueError("Missing/duplicate YOLO paired review scoring cell")
    report = matches[0]
    frames = [f.frame_index for f in run.frames]
    if (report["config"] != asdict(config) or report["source_video"] != run.source_video.to_dict()
            or report["window"] != run.window.to_dict()
            or report["observations_content_sha256"] != canonical_sha256(observations)
            or [r["frame_index"] for r in report["frame_results"]] != frames
            or [r["frame_index"] for r in observations["frames"]] != frames):
        raise ValueError("Scoring/observation provenance or frame synchronization differs")
    return report


def _prepare_review(root, path):
    from .yolo_crop_candidates import experiment_grid
    from .yolo_crop_evaluation import load_scoring_pools
    from .yolo_crop_experiment import (
        candidate_path, load_candidate_run, load_observations, load_saved_control,
        output_path, preflight, unchanged,
    )
    manifest_binding = file_binding(root, path)
    m, p, inputs, commit = preflight(root, path)
    pool_bindings = [file_binding(root, root / OUTPUT_ROOT / "evaluation" / (purpose + ".json"))
                     for purpose in p["pool_separation"]]
    pools = load_scoring_pools(root, m, p, commit, inputs=inputs)
    reused = load_reused_assets(root, p)
    bindings = [manifest_binding, m["proposal"], p["reused_native_review_manifest"],
                *p["saved_control_scoring_reports"], *pool_bindings]
    windows = []
    for w, label, item in zip(p["windows"], p["scoring_labels"], inputs, strict=True):
        if item["window"] != w:
            raise ValueError("Preflight input window order differs from review")
        bindings.append(file_binding(root, candidate_path(root, w)))
        run, payload, digest = load_candidate_run(root, m, p, w, commit, model=item["model"])
        if label["window_id"] != w["window_id"] or len(run.frames) != 25:
            raise ValueError("Review annotation/window mismatch")
        annotations = load_annotations(bound_file(root, label["annotation"], "configs/ball_tracking/annotations"))
        if (annotations.annotation_set_id != w["annotation_set_id"]
                or annotations.possession_id != run.possession_id or annotations.source_video != run.source_video
                or annotations.window.start_frame_index != run.window.start_frame_index
                or annotations.window.end_frame_index != run.window.end_frame_index
                or annotations.window.selection_purpose != w["purpose"]):
            raise ValueError("Frozen review annotation identity differs from candidate window")
        bindings.append(label["annotation"])
        observations, reports = {}, {}
        for c in (c for c in control_grid() if c.arm in CONTROL_ARMS and c.confidence_threshold in THRESHOLDS):
            obs = load_saved_control(root, p, w, c)
            observations[c.arm, c.confidence_threshold] = obs
            reports[c.arm, c.confidence_threshold] = _report(pools[w["purpose"]], run, c, obs)
            suffix = f"/{w['window_id']}/{c.variant_id}.json"
            matching = [b for b in p["saved_control_outputs"] if b["path"].endswith(suffix)]
            if len(matching) != 1:
                raise ValueError("Missing/duplicate saved control output binding")
            bindings.append(matching[0])
        for c in (c for c in experiment_grid() if c.confidence_threshold in THRESHOLDS):
            bindings.append(file_binding(root, output_path(root, w, c)))
            obs = load_observations(root, m, p, w, run, digest, c, commit, rederive=False)
            observations[c.arm, c.confidence_threshold] = obs
            reports[c.arm, c.confidence_threshold] = _report(pools[w["purpose"]], run, c, obs)
            if reports[c.arm, c.confidence_threshold]["input_candidate_content_sha256"] != canonical_sha256(run.to_dict()):
                raise ValueError("Saved score candidate digest differs from YOLO candidate file")
        annotation_digest = canonical_sha256(annotations.to_dict())
        if any(r["annotation_content_sha256"] != annotation_digest for r in reports.values()):
            raise ValueError("Saved scoring annotation digest differs from reviewed labels")
        windows.append({"window": w, "run": run, "truth": annotations.annotation_by_frame(),
                        "observations": observations, "reports": reports})
    header = {"schema_version": "ball_yolo_crop_visual_review/v0.1", "experiment_spec_sha256": spec_digest(m),
              "renderer_code_commit": commit, "windows": p["windows"], "confidence_views": list(THRESHOLDS),
              "radius_px": 10.0, "layout": LAYOUT,
              "view_configs": [asdict(c) for c in experiment_grid() if c.confidence_threshold in THRESHOLDS],
              "native_new_arms": list(YOLO_ARMS), "native_reused_arms": list(CONTROL_ARMS),
              "native_header_px": NATIVE_HEADER, "reused_assets": reused, "input_bindings": bindings,
              "source_inventory_sha256": canonical_sha256(p["inference_source_frames"]),
              "source_pixels": "exact original full-size development PNG references; no source-video decode",
              "old_controls": "unchanged native PNGs and saved observations/reports; no old execution",
              "detector_policies": {"rfdetr": "export floor .01; direct 576x576 resize; no NMS",
                                    "yolo": "postprocessed/exported; best class; NMS IoU .7; max_det300/crop; export floor .01"},
              "confidence_semantics": "original model scores; equal numerical thresholds are not calibrated probabilities",
              "hidden_closeup_focus": "highest accepted YOLO candidate, otherwise frame center; not ball truth",
              "selected_method": None, "selected_operating_point": None, "quality_gate": None}

    def verify():
        for item in bindings + reused:
            _verify_binding(root, item)
        unchanged(root, path, m, commit)

    verify()
    return PreparedReview(header, windows, verify)


def _tile(pixels, lines):
    import cv2
    import numpy as np
    panel = np.zeros((TILE_HEIGHT, TILE_WIDTH, 3), dtype=np.uint8)
    scale = min(TILE_WIDTH / pixels.shape[1], (TILE_HEIGHT - TILE_HEADER) / pixels.shape[0])
    width, height = max(1, round(pixels.shape[1]*scale)), max(1, round(pixels.shape[0]*scale))
    fitted = cv2.resize(pixels, (width, height), interpolation=cv2.INTER_AREA)
    x, y = (TILE_WIDTH-width)//2, TILE_HEADER+(TILE_HEIGHT-TILE_HEADER-height)//2
    panel[y:y+height, x:x+width] = fitted
    for i, line in enumerate(lines):
        cv2.putText(panel, line, (8, 20+i*22), cv2.FONT_HERSHEY_SIMPLEX, .48,
                    (235, 235, 235), 1, cv2.LINE_AA)
    return panel


def _native_header(body, lines):
    import cv2
    import numpy as np
    header = np.zeros((NATIVE_HEADER, body.shape[1], 3), dtype=np.uint8)
    for i, line in enumerate(lines):
        cv2.putText(header, line, (10, 24+i*27), cv2.FONT_HERSHEY_SIMPLEX,
                    .62 if i == 0 else .55, (235, 235, 235), 1, cv2.LINE_AA)
    return np.vstack((header, body))


def _text_panel(lines):
    import cv2
    import numpy as np
    panel = np.zeros((TILE_HEIGHT, TILE_WIDTH, 3), dtype=np.uint8)
    for i, line in enumerate(lines):
        cv2.putText(panel, line, (10, 30+i*39), cv2.FONT_HERSHEY_SIMPLEX,
                    .51 if i == 0 else .48, (235, 235, 235), 1, cv2.LINE_AA)
    return panel


def _summary(result):
    return (f"TP {int(result['matched_candidate_index'] is not None)} | FP {result['false_positive_count']}"
            f" | FN {result['false_negative_count']}")


def _label_exported_counts(overlay, source_width, frame, observation, threshold):
    """Replace the generic RAW count only on the newly rendered YOLO sidebar."""
    from .prepare_detection_visual_review import GRAY, _put_fitted_text
    sidebar_width = overlay.shape[1] - source_width
    scale = max(.42, min(.62, sidebar_width / 620.0 * .56))
    line_height = max(22, round(29 * scale / .56))
    overlay[6*line_height+line_height//3:8*line_height-line_height//3, source_width+1:] = 12
    qualified = sum(c.confidence >= threshold for c in frame.detections)
    _put_fitted_text(overlay,
        f"EXPORTED {len(frame.detections)} | >= CONF {qualified} | EMITTED {len(observation['emitted_candidate_indices'])}",
        (source_width+14, 7*line_height), sidebar_width-28, scale, GRAY)


def render_frame(source, annotation, frame, observations, reports, native_controls, threshold):
    import numpy as np
    from .prepare_detection_visual_review import DetectionReviewView, render_detection_overlay, render_truth_region_panel
    if threshold not in THRESHOLDS or annotation.frame_index != frame.frame_index:
        raise ValueError("Undeclared threshold or unsynchronized annotation")
    if set(native_controls) != set(CONTROL_ARMS) or set(observations) != set(CONTROL_ARMS + YOLO_ARMS):
        raise ValueError("All six detector/selector arms are required")
    if set(reports) != set(observations):
        raise ValueError("Scoring views differ from observation arms")
    for arm in observations:
        if observations[arm]["frame_index"] != frame.frame_index or reports[arm]["frame_index"] != frame.frame_index:
            raise ValueError("Unsynchronized detector review frame")
    height, width = source.shape[:2]
    for pixels in native_controls.values():
        if pixels.ndim != 3 or pixels.shape[0] != height + NATIVE_HEADER or pixels.shape[1] < width:
            raise ValueError("Saved native overlay dimensions differ from source")
    new, pairs, closeups, focuses = [], [], [], []
    names = ("all exported", "top one", "top twenty")
    for parent, arm, name in zip(CONTROL_ARMS, YOLO_ARMS, names, strict=True):
        observation, result = observations[arm], reports[arm]
        view = DetectionReviewView("YOLO " + name, threshold, 10.0, "descriptive_display_not_selected")
        overlay, _ = render_detection_overlay(source, annotation, selected_frame(frame, observation), result, view)
        _label_exported_counts(overlay, width, frame, observation, threshold)
        native = _native_header(overlay, (f"YOLO11x {name} | frame {frame.frame_index} | conf {threshold:.2f}",
            "Postprocessed: best class / NMS .7 / max_det300 per crop; exported >= .01",
            "Original model scores; cross-crop duplicates retained; no operating point selected"))
        new.append(native)
        old_tile = _tile(native_controls[parent][NATIVE_HEADER:, :width],
            (f"RF-DETR saved {name} | no NMS", f"Frame {frame.frame_index} | conf {threshold:.2f} | {_summary(reports[parent])}",
             "Direct 576x576 resize; original confidence", "Exact saved native pixels; controls unchanged"))
        new_tile = _tile(overlay[:, :width],
            (f"YOLO11x {name} | after NMS/cap", f"Frame {frame.frame_index} | conf {threshold:.2f} | {_summary(result)}",
             "640-square letterbox; original confidence", "Best class; NMS .7; max_det300/crop; duplicates retained"))
        pairs.append((old_tile, new_tile))
        region, focus = render_truth_region_panel(source, [native_controls[parent][NATIVE_HEADER:], overlay],
            annotation, frame, [DetectionReviewView("RF-DETR " + name, threshold, 10.0, "saved_control_pixels"), view])
        closeups.append(region)
        focuses.append({"control_arm": parent, "challenger_arm": arm,
                        "candidate_focus_source": "YOLO exported candidates only when truth is absent", **focus})
    right = [_tile(source, (f"Unmarked source | frame {frame.frame_index}", "Exact full-size source is linked in manifest")),
        _text_panel(("DETECTOR CONFIGURATIONS DIFFER", "RF-DETR: all exported direct detector candidates",
            "Direct 576x576 resize; no NMS", "YOLO: postprocessed/exported candidates",
            "640-square letterbox; best-class assignment", "Class-aware NMS .7; max_det300 per crop",
            "Both: original-score export floor >= .01", "Keep all cross-crop duplicates; no global NMS",
            "Top1/top20 follow the confidence filter", "Equal scores are not equal calibrated probability",
            "Complete configurations; no architecture-only claim", "Native views preserve candidate labels/confidence")),
        _text_panel(("PAIRED REVIEW | no method or gate selected", "Rows: all exported / top one / top twenty",
            "Left: saved RF-DETR | middle: new YOLO", "Green TP / red FP / magenta duplicate",
            "Orange hidden FP / cyan reviewed truth", "Yellow uncertainty; blue 10px scoring display",
            "Uncertainty is diagnostic, not matching tolerance", "Missing stays missing; no interpolation",
            "Closeups: raw source | RF-DETR | YOLO",
            "No truth: focus on YOLO proposal, not a ball label", "Use native views for candidates outside closeup",
            "Inspect every frame including final frame", "Human review pending; no holdout release"))]
    comparison = np.vstack([np.hstack((*pair, reference)) for pair, reference in zip(pairs, right, strict=True)])
    return comparison, new, np.vstack(closeups), focuses


def _expected_assets(header):
    paths, frames = set(), set()
    for w in header["windows"]:
        for c in THRESHOLDS:
            prefix = f"{w['window_id']}/confidence_{c}"
            paths.add(prefix + "/comparison_slow.mp4")
            for f in range(w["start_frame_index"], w["end_frame_index"]+1):
                frames.add((w["window_id"], c, f))
                paths.update(f"{prefix}/{folder}/frame_{f:06d}.png" for folder in PNG_FOLDERS)
    return paths, frames


def validate_review_bundle(root, bundle, header):
    value = closed(read_json(bundle / "manifest.json"),
        {"header", "assets", "final_frames", "frame_evidence", "human_visual_review"}, "YOLO review bundle")
    if value["header"] != header or value["human_visual_review"] != "pending":
        raise ValueError("YOLO review provenance mismatch")
    expected, frames = _expected_assets(header)
    paths = [a["path"] for a in value["assets"]]
    actual = {p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file() and p != bundle / "manifest.json"}
    evidence = [(r["window_id"], r["confidence_threshold"], r["frame_index"]) for r in value["frame_evidence"]]
    final = [{"window_id": w["window_id"], "frame_index": w["end_frame_index"]} for w in header["windows"]]
    if (len(paths) != len(expected) or set(paths) != expected or actual != expected
            or len(evidence) != len(frames) or set(evidence) != frames or value["final_frames"] != final):
        raise ValueError("Incomplete/duplicate YOLO review assets or final frames")
    sources = {(r["window_id"], r["confidence_threshold"], r["frame_index"]): r
               for r in header["reused_assets"] if r["arm"] == "unmarked_source"}
    for row in value["frame_evidence"]:
        key = row["window_id"], row["confidence_threshold"], row["frame_index"]
        if row["source_png"] != sources.get(key):
            raise ValueError("Frame evidence source provenance differs from reused pixels")
        if [(r["control_arm"], r["challenger_arm"]) for r in row["closeup_regions"]] != list(zip(CONTROL_ARMS, YOLO_ARMS)):
            raise ValueError("Closeup arm pairing differs")
    for item in value["assets"]:
        closed(item, {"path", "sha256"}, "new review asset")
        if sha256_file(safe_path(bundle, item["path"])) != item["sha256"]:
            raise ValueError("YOLO review asset hash mismatch")
    for item in header["input_bindings"] + header["reused_assets"]:
        _verify_binding(root, item)
    return value


def _verify_video(path):
    import cv2
    capture, count = cv2.VideoCapture(str(path)), 0
    try:
        if not capture.isOpened():
            raise ValueError("Could not decode new YOLO review clip")
        while True:
            ok, pixels = capture.read()
            if not ok:
                break
            if pixels.shape != (TILE_HEIGHT*3, TILE_WIDTH*3, 3):
                raise ValueError("Incorrect YOLO review video dimensions")
            count += 1
        if count != 25 or capture.get(cv2.CAP_PROP_FPS) != 5.0:
            raise ValueError("YOLO review video did not decode all 25 frames at 5fps")
    finally:
        capture.release()


def render_experiment(root, path):
    import cv2
    root, path = Path(root).resolve(), Path(path).resolve()
    prepared = _prepare_review(root, path)
    header = prepared.header
    bundle = safe_path(root, f"{OUTPUT_ROOT}/review/{canonical_sha256(header)[:32]}", OUTPUT_ROOT)
    if bundle.exists():
        validate_review_bundle(root, bundle, header)
        prepared.verify()
        return {"bundle": str(bundle), "reused": True}
    bundle.parent.mkdir(parents=True, exist_ok=True)
    indexed = {(r["window_id"], r["confidence_threshold"], r["frame_index"], r["arm"]): r for r in header["reused_assets"]}
    if len(indexed) != len(header["reused_assets"]):
        raise ValueError("Duplicate reused native identity")
    with tempfile.TemporaryDirectory(prefix=".pending_review_", dir=bundle.parent) as temporary:
        staging = Path(temporary).resolve()
        assets, evidence = [], []

        def add(target):
            assets.append({"path": target.relative_to(staging).as_posix(), "sha256": sha256_file(target)})

        for item in prepared.windows:
            w, run = item["window"], item["run"]
            writers = {}
            try:
                for offset, frame in enumerate(run.frames):
                    for c in THRESHOLDS:
                        records = {a: indexed[w["window_id"], c, frame.frame_index, a] for a in (*CONTROL_ARMS, "unmarked_source")}
                        source = _read_png(root, records["unmarked_source"])
                        if source.shape != (run.source_video.height_px, run.source_video.width_px, 3):
                            raise ValueError("Saved source PNG dimensions differ from source contract")
                        controls = {a: _read_png(root, records[a]) for a in CONTROL_ARMS}
                        observations = {a: item["observations"][a, c]["frames"][offset] for a in (*CONTROL_ARMS, *YOLO_ARMS)}
                        reports = {a: item["reports"][a, c]["frame_results"][offset] for a in observations}
                        comparison, native, closeups, focus = render_frame(source, item["truth"][frame.frame_index],
                            frame, observations, reports, controls, c)
                        folder = staging / w["window_id"] / f"confidence_{c}"
                        for name, pixels in [("comparison", comparison), ("closeups", closeups),
                                             *((f"yolo_view_{i}", v) for i, v in enumerate(native))]:
                            target = folder / name / f"frame_{frame.frame_index:06d}.png"
                            target.parent.mkdir(parents=True, exist_ok=True)
                            if not cv2.imwrite(str(target), pixels):
                                raise ValueError("Could not write new YOLO review PNG")
                            add(target)
                        evidence.append({"window_id": w["window_id"], "confidence_threshold": c,
                            "frame_index": frame.frame_index, "source_png": records["unmarked_source"], "closeup_regions": focus})
                        if c not in writers:
                            target = folder / "comparison_slow.mp4"
                            writer = cv2.VideoWriter(str(target), cv2.VideoWriter_fourcc(*"mp4v"), 5.0, (comparison.shape[1], comparison.shape[0]))
                            if not writer.isOpened():
                                writer.release()
                                raise ValueError("Could not open new YOLO review writer")
                            writers[c] = writer, target
                        writers[c][0].write(comparison)
            finally:
                for writer, _ in writers.values():
                    writer.release()
            if len(writers) != 2:
                raise ValueError("Incomplete YOLO confidence clips")
            for _, target in writers.values():
                _verify_video(target)
                add(target)
        persist_once(staging / "manifest.json", {"header": header, "assets": assets,
            "final_frames": [{"window_id": w["window_id"], "frame_index": w["end_frame_index"]} for w in header["windows"]],
            "frame_evidence": evidence, "human_visual_review": "pending"})
        validate_review_bundle(root, staging, header)
        prepared.verify()
        staging.rename(bundle)
    return {"bundle": str(bundle), "reused": False, "assets": len(assets),
            "reused_native_assets": len(header["reused_assets"]), "human_visual_review": "pending"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.repository_root.resolve()
    print(json.dumps(render_experiment(root, (root / args.manifest).resolve()), indent=2))


if __name__ == "__main__":
    main()
