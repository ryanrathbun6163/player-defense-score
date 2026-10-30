"""Paired player-context review using frozen native control/source PNGs."""
from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from .annotations import load_annotations
from .crop_motion_factorial import ARMS as CONTROL_ARMS, experiment_grid as control_grid
from .crop_motion_evaluation import selected_frame
from .development_experiments import (
    bound_file, canonical_sha256, closed, read_json, require_digest, safe_path, sha256_file,
)
from .temporal_experiment import file_binding, persist_once, spec_digest

THRESHOLDS = (.2, .35)
GRAPH_CONTROLS = CONTROL_ARMS[3:]
CONTEXT_ARMS = tuple(arm + "_player_context" for arm in GRAPH_CONTROLS)
OUTPUT_ROOT = "data/outputs/ball_tracking/crop_player_context/rfdetr_medium_crop_player_context_v0_1"
PRIOR_ROOT = "data/outputs/ball_tracking/crop_motion_factorial"
PNG_FOLDERS = ("comparison", "closeups", "player_context", *(f"context_view_{i}" for i in range(4)))
TILE_WIDTH, TILE_HEIGHT, TILE_HEADER = 800, 522, 90
NATIVE_HEADER = 90
LAYOUT = [["TT", "TT-context", "unmarked_source"],
          ["TW", "TW-context", "observed_player_context"],
          ["WT", "WT-context", "crop_top_one"], ["WW", "WW-context", "legend"]]


@dataclass
class PreparedReview:
    header: dict
    windows: list[dict]
    verify: Callable[[], None]


def _verify_binding(root, item):
    require_digest(item["sha256"], "review input")
    target = safe_path(root, item["path"])
    if not target.is_file() or sha256_file(target) != item["sha256"]:
        raise ValueError("Player-context review binding mismatch: " + item["path"])
    return target


def _read_png(root, item):
    import cv2
    target = _verify_binding(root, item)
    if target.suffix != ".png":
        raise ValueError("Saved review pixels must be PNG")
    pixels = cv2.imread(str(target), cv2.IMREAD_COLOR)
    if pixels is None:
        raise ValueError("Could not decode saved review PNG")
    return pixels


def load_reused_assets(root, proposal):
    """Resolve exact window/confidence/view/frame keys in the frozen old manifest."""
    path = bound_file(root, proposal["prior_review_manifest"], PRIOR_ROOT)
    prior = closed(read_json(path), {"header", "assets", "final_frames", "human_visual_review"},
                   "prior motion review")
    header = prior["header"]
    expected_configs = [asdict(c) for c in control_grid() if c.confidence_threshold in THRESHOLDS]
    if (header["schema_version"] != "ball_crop_motion_factorial_visual_review/v0.1"
            or header["windows"] != proposal["windows"]
            or header["confidence_views"] != list(THRESHOLDS) or header["radius_px"] != 10
            or header["view_configs"] != expected_configs
            or header["panels"] != [*CONTROL_ARMS, "unmarked_source", "legend"]
            or header["selected_operating_point"] is not None or header["quality_gate"] is not None
            or not header["native_unmarked_source_pngs"]):
        raise ValueError("Prior native review configuration/window provenance differs")
    expected_final = [{"window_id": w["window_id"], "frame_index": w["end_frame_index"]}
                      for w in proposal["windows"]]
    if prior["final_frames"] != expected_final:
        raise ValueError("Prior review final-frame declaration differs")
    indexed = {}
    for item in prior["assets"]:
        closed(item, {"path", "sha256"}, "prior review asset")
        if item["path"] in indexed:
            raise ValueError("Duplicate prior review asset key")
        safe_path(path.parent, item["path"])
        require_digest(item["sha256"], "prior review asset")
        indexed[item["path"]] = item
    records = []
    for w in proposal["windows"]:
        for threshold in THRESHOLDS:
            prefix = f"{w['window_id']}/confidence_{threshold}"
            for frame in range(w["start_frame_index"], w["end_frame_index"] + 1):
                for arm, folder in [(a, f"view_{i}") for i, a in enumerate(CONTROL_ARMS)] + [
                        ("unmarked_source", "unmarked_source")]:
                    key = f"{prefix}/{folder}/frame_{frame:06d}.png"
                    if key not in indexed:
                        raise ValueError("Missing exact prior native/source frame: " + key)
                    item = {"window_id": w["window_id"], "confidence_threshold": threshold,
                            "frame_index": frame, "arm": arm,
                            "path": (path.parent / key).relative_to(root).as_posix(),
                            "sha256": indexed[key]["sha256"]}
                    _verify_binding(root, item)
                    records.append(item)
    return records


def _report(pool, run, config, observations):
    matches = [r for r in pool["evaluation_reports"] if r["possession_id"] == run.possession_id
               and r["variant_id"] == config.variant_id and r["localization_radius_px"] == 10]
    if len(matches) != 1:
        raise ValueError("Missing/duplicate player-context review scoring cell")
    report = matches[0]
    indices = [frame.frame_index for frame in run.frames]
    if (report["config"] != asdict(config) or report["source_video"] != run.source_video.to_dict()
            or report["window"] != run.window.to_dict()
            or report["observations_content_sha256"] != canonical_sha256(observations)
            or [f["frame_index"] for f in report["frame_results"]] != indices
            or [f["frame_index"] for f in observations["frames"]] != indices):
        raise ValueError("Scoring/observation provenance or frame synchronization differs")
    return report


def _prepare_review(root, path):
    # Import the new stages here so helpers remain independently testable. Neither
    # a selector nor a scorer is called by this module.
    from .crop_player_context import experiment_grid, validate_context_window
    from .crop_player_context_evaluation import load_scoring_pools
    from .crop_player_context_experiment import (
        load_observations, load_saved_control, output_path, preflight, unchanged,
    )

    m, p, inputs, commit = preflight(root, path)
    pools = load_scoring_pools(root, m, p, commit)
    reused = load_reused_assets(root, p)
    bindings = [file_binding(root, path), m["proposal"], p["prior_review_manifest"],
                p["player_context"]["snapshot"], *p["saved_control_scoring_reports"]]
    bindings.extend(file_binding(root, root / OUTPUT_ROOT / "evaluation" / (purpose + ".json"))
                    for purpose in p["pool_separation"])
    windows = []
    for w, (_, run, digest, context), label in zip(p["windows"], inputs, p["scoring_labels"], strict=True):
        if label["window_id"] != w["window_id"] or len(run.frames) != 25:
            raise ValueError("Review annotation/window mismatch")
        annotations = load_annotations(bound_file(root, label["annotation"], "configs/ball_tracking/annotations"))
        if (annotations.annotation_set_id != w["annotation_set_id"]
                or annotations.possession_id != run.possession_id
                or annotations.source_video != run.source_video
                or annotations.window.start_frame_index != run.window.start_frame_index
                or annotations.window.end_frame_index != run.window.end_frame_index
                or annotations.window.selection_purpose != w["purpose"]):
            raise ValueError("Frozen review annotation identity differs from candidate window")
        bindings.append(label["annotation"])
        rows = validate_context_window(context, run)
        observations, reports = {}, {}
        for threshold in THRESHOLDS:
            for c in (c for c in control_grid() if c.confidence_threshold == threshold):
                obs = load_saved_control(root, p, w, c, run=run, crop_digest=digest)
                observations[c.arm, threshold] = obs
                reports[c.arm, threshold] = _report(pools[w["purpose"]], run, c, obs)
                suffix = f"/{w['window_id']}/{c.variant_id}.json"
                matching = [b for b in p["saved_control_outputs"] if b["path"].endswith(suffix)]
                if len(matching) != 1:
                    raise ValueError("Missing/duplicate saved control binding")
                bindings.append(matching[0])
            for c in (c for c in experiment_grid() if c.confidence_threshold == threshold):
                obs = load_observations(root, m, w, run, digest, c, commit, context, rederive=False)
                observations[c.arm, threshold] = obs
                reports[c.arm, threshold] = _report(pools[w["purpose"]], run, c, obs)
                bindings.append(file_binding(root, output_path(root, w, c)))
        annotation_digest = canonical_sha256(annotations.to_dict())
        if any(r["annotation_content_sha256"] != annotation_digest for r in reports.values()):
            raise ValueError("Saved scoring annotation digest differs from reviewed labels")
        windows.append({"window": w, "run": run, "truth": annotations.annotation_by_frame(),
                        "player_rows": rows, "observations": observations, "reports": reports})
    header = {"schema_version": "ball_crop_player_context_visual_review/v0.1",
              "experiment_spec_sha256": spec_digest(m), "renderer_code_commit": commit,
              "windows": p["windows"], "confidence_views": list(THRESHOLDS), "radius_px": 10.0,
              "layout": LAYOUT, "view_configs": [asdict(c) for c in experiment_grid()
                                                  if c.confidence_threshold in THRESHOLDS],
              "native_new_arms": list(CONTEXT_ARMS), "native_reused_arms": list(CONTROL_ARMS),
              "new_native_header_px": NATIVE_HEADER, "reused_native_header_px": NATIVE_HEADER,
              "reused_assets": reused, "input_bindings": bindings,
              "source_pixels": "exact frozen prior unmarked PNGs; no source video decode",
              "old_controls": "native PNGs and saved reports reused; no rerender/rescore/rerank",
              "player_context_causality": "offline reviewed inputs may use hindsight; ball history is causal",
              "selected_operating_point": None, "quality_gate": None}

    def verify():
        for binding in bindings + reused:
            _verify_binding(root, binding)
        unchanged(root, path, m, commit)

    verify()
    return PreparedReview(header, windows, verify)


def _title(arm):
    parent = arm.removesuffix("_player_context")
    c = next(c for c in control_grid() if c.arm == parent)
    if c.edge_step is None:
        return {"crop_raw": "Saved crop all candidates", "crop_top_one": "Saved crop top one",
                "crop_top_twenty": "Saved crop top twenty"}[parent]
    strength = ".25" if arm.endswith("_player_context") else "0 (saved)"
    return f"Edge {c.edge_step:.2f} / cost {c.cost_step:.2f} / context {strength}"


def _tile(pixels, lines):
    import cv2
    import numpy as np
    panel = np.zeros((TILE_HEIGHT, TILE_WIDTH, 3), dtype=np.uint8)
    scale = min(TILE_WIDTH / pixels.shape[1], (TILE_HEIGHT - TILE_HEADER) / pixels.shape[0])
    width, height = max(1, round(pixels.shape[1] * scale)), max(1, round(pixels.shape[0] * scale))
    fitted = cv2.resize(pixels, (width, height), interpolation=cv2.INTER_AREA)
    x, y = (TILE_WIDTH - width) // 2, TILE_HEADER + (TILE_HEIGHT - TILE_HEADER - height) // 2
    panel[y:y+height, x:x+width] = fitted
    for i, line in enumerate(lines):
        cv2.putText(panel, line, (8, 20 + i * 22), cv2.FONT_HERSHEY_SIMPLEX,
                    .48 if i != 3 else .42, (235, 235, 235), 1, cv2.LINE_AA)
    return panel


def _native_header(body, lines):
    import cv2
    import numpy as np
    header = np.zeros((NATIVE_HEADER, body.shape[1], 3), dtype=np.uint8)
    for i, line in enumerate(lines):
        cv2.putText(header, line, (10, 24 + i * 27), cv2.FONT_HERSHEY_SIMPLEX,
                    .65 if i == 0 else .56, (235, 235, 235), 1, cv2.LINE_AA)
    return np.vstack((header, body))


def player_context_overlay(source, frame_index, rows):
    """Draw only observed rectangles, independent of ball outputs and labels."""
    import cv2
    body = source.copy()
    for row in rows:
        if row["frame_index"] != frame_index:
            raise ValueError("Player box from another frame")
        x1, y1, x2, y2 = (round(row[key]) for key in ("x1", "y1", "x2", "y2"))
        cv2.rectangle(body, (x1, y1), (x2, y2), (210, 180, 70), 1)
        cv2.putText(body, str(row["player_id"]), (max(0, x1), max(16, y1-4)),
                    cv2.FONT_HERSHEY_SIMPLEX, .45, (210, 180, 70), 1)
    return _native_header(body, (f"Observed player context | frame {frame_index} | {len(rows)} boxes",
                                f"Context unavailable: {'yes' if not rows else 'no'} | completeness is not certified",
                                "Offline reviewed identities; rectangles are observations, not ball truth"))


def _details(frame, observation, result, context):
    history = observation["ranking"]
    winner = history["winner"] if history is not None else None
    emitted = observation["emitted_candidate_indices"]
    confidence = next((c.confidence for c in frame.detections if c.candidate_index in emitted), None)
    cost = None
    if context and emitted:
        matches = [n for n in history["node_context"] if n["reference"] == [frame.frame_index, emitted[0]]]
        if len(matches) != 1:
            raise ValueError("Missing/duplicate emitted node context")
        cost = matches[0]["context_cost"]
    conf_text = "none" if confidence is None else f"{confidence:.3f}"
    cost_text = "unapplied" if not context else "none" if cost is None else f"{cost:.3f}"
    score_text = "n/a" if winner is None else f"{winner['score']:.3f}"
    summary = f"TP {int(result['matched_candidate_index'] is not None)} | FP {result['false_positive_count']} | FN {result['false_negative_count']}"
    return summary, f"Original conf {conf_text} | context cost {cost_text} | path score {score_text}", observation["decision_reason"]


def render_frame(source, annotation, frame, observations, reports, native_controls, player_rows, threshold):
    """Composite saved control pixels with four new overlays; no old redraw."""
    import cv2
    import numpy as np
    from .prepare_detection_visual_review import DetectionReviewView, render_detection_overlay, render_truth_region_panel

    if threshold not in THRESHOLDS or annotation.frame_index != frame.frame_index:
        raise ValueError("Undeclared confidence or unsynchronized annotation")
    if set(native_controls) != set(CONTROL_ARMS) or set(observations) != set(CONTROL_ARMS + CONTEXT_ARMS):
        raise ValueError("All eleven native arms are required")
    if set(reports) != set(observations):
        raise ValueError("Scoring views differ from observation arms")
    height, width = source.shape[:2]
    for arm in observations:
        if observations[arm]["frame_index"] != frame.frame_index or reports[arm]["frame_index"] != frame.frame_index:
            raise ValueError("Unsynchronized review frame")
    for pixels in native_controls.values():
        if pixels.ndim != 3 or pixels.shape[0] != height + NATIVE_HEADER or pixels.shape[1] < width:
            raise ValueError("Saved native overlay dimensions differ from source")
    native_new, panels, closeups, focuses = [], {}, [], []
    for arm in CONTROL_ARMS:
        body = native_controls[arm][NATIVE_HEADER:, :width]
        summary, detail, reason = _details(frame, observations[arm], reports[arm], False)
        panels[arm] = _tile(body, (_title(arm), f"Frame {frame.frame_index} | conf {threshold:.2f} | {summary}", detail, reason))
    for parent, arm in zip(GRAPH_CONTROLS, CONTEXT_ARMS):
        observation, result = observations[arm], reports[arm]
        if (observation["context_available_box_count"] != len(player_rows)
                or observation["context_unavailable"] != (not player_rows)):
            raise ValueError("Saved context availability differs from frozen player rows")
        view = DetectionReviewView(_title(arm), threshold, 10.0, "descriptive_display_not_selected")
        overlay, _ = render_detection_overlay(source, annotation, selected_frame(frame, observation), result, view)
        summary, detail, reason = _details(frame, observation, result, True)
        native = _native_header(overlay, (_title(arm), detail + " | " + reason,
                                         "Original confidence, bounded context cost and path score are distinct; score is not probability"))
        native_new.append(native)
        panels[arm] = _tile(overlay[:, :width], (_title(arm), f"Frame {frame.frame_index} | conf {threshold:.2f} | {summary}", detail, reason))
        views = [DetectionReviewView(_title(parent), threshold, 10.0, "saved_control_pixels"), view]
        closeup, focus = render_truth_region_panel(source,
                        [native_controls[parent][NATIVE_HEADER:], overlay], annotation, frame, views)
        closeups.append(closeup)
        focuses.append({"control_arm": parent, "context_arm": arm, **focus})
    player = player_context_overlay(source, frame.frame_index, player_rows)
    reference_panels = [
        _tile(source, (f"Unmarked source | frame {frame.frame_index}", "Exact saved pixels; no new video decoding")),
        _tile(player[NATIVE_HEADER:], (f"Observed players | {len(player_rows)} boxes", f"Context unavailable: {'yes' if not player_rows else 'no'}",
                                           "Rectangles do not establish ball identity", "Offline reviewed inputs may use hindsight")),
        panels["crop_top_one"],
    ]
    legend = np.zeros((TILE_HEIGHT, TILE_WIDTH, 3), dtype=np.uint8)
    lines = ("PAIRED CONTEXT COMPARISON | no method selected", "Left: saved graph | middle: context coefficient .25",
             "Green TP / red FP / magenta duplicate / orange hidden FP", "Cyan truth / yellow uncertainty / blue 10px display radius",
             "Amber alt # = saved unselected hypothesis, not emitted",
             "Original confidence filters candidates; context changes score", "Signed utility is retained; negative paths can yield null",
             "Null means no current observation; no interpolation", "Inside player box gives zero cost, not proof of a ball",
             "Raw/top20 available as unchanged native-only references", "Exact native PNGs, score JSON and source-scale closeups",
             "Player input review may use hindsight; no online claim", "Review through final frame; quality gate remains unset")
    for i, line in enumerate(lines):
        cv2.putText(legend, line, (10, 30+i*40), cv2.FONT_HERSHEY_SIMPLEX,
                    .52 if i == 0 else .49, (230, 230, 230), 1, cv2.LINE_AA)
    reference_panels.append(legend)
    comparison = np.vstack([np.hstack((panels[parent], panels[arm], reference_panels[i]))
                            for i, (parent, arm) in enumerate(zip(GRAPH_CONTROLS, CONTEXT_ARMS))])
    return comparison, native_new, player, np.vstack(closeups), focuses


def _expected_assets(header):
    paths, frames = set(), set()
    for w in header["windows"]:
        for threshold in THRESHOLDS:
            prefix = f"{w['window_id']}/confidence_{threshold}"
            paths.add(prefix + "/comparison_slow.mp4")
            for frame in range(w["start_frame_index"], w["end_frame_index"]+1):
                frames.add((w["window_id"], threshold, frame))
                paths.update(f"{prefix}/{folder}/frame_{frame:06d}.png" for folder in PNG_FOLDERS)
    return paths, frames


def validate_review_bundle(root, bundle, header):
    value = closed(read_json(bundle / "manifest.json"),
                   {"header", "assets", "final_frames", "frame_evidence", "human_visual_review"},
                   "player-context review bundle")
    if value["header"] != header or value["human_visual_review"] != "pending":
        raise ValueError("Player-context review provenance mismatch")
    expected, frames = _expected_assets(header)
    paths = [a["path"] for a in value["assets"]]
    actual = {p.relative_to(bundle).as_posix() for p in bundle.rglob("*")
              if p.is_file() and p != bundle / "manifest.json"}
    evidence = [(r["window_id"], r["confidence_threshold"], r["frame_index"]) for r in value["frame_evidence"]]
    final = [{"window_id": w["window_id"], "frame_index": w["end_frame_index"]} for w in header["windows"]]
    if (len(paths) != len(expected) or set(paths) != expected or actual != expected
            or len(evidence) != len(frames) or set(evidence) != frames or value["final_frames"] != final
            or any(len(r["closeup_regions"]) != 4 for r in value["frame_evidence"])):
        raise ValueError("Incomplete/duplicate player-context assets or final frames")
    source_bindings = {(r["window_id"], r["confidence_threshold"], r["frame_index"]): r
                       for r in header["reused_assets"] if r["arm"] == "unmarked_source"}
    for row in value["frame_evidence"]:
        key = row["window_id"], row["confidence_threshold"], row["frame_index"]
        if row["source_png"] != source_bindings.get(key):
            raise ValueError("Frame evidence source provenance differs from exact reused pixels")
    for item in value["assets"]:
        closed(item, {"path", "sha256"}, "new review asset")
        target = safe_path(bundle, item["path"])
        if sha256_file(target) != item["sha256"]:
            raise ValueError("New player-context review asset hash mismatch")
    for binding in header["input_bindings"] + header["reused_assets"]:
        _verify_binding(root, binding)
    return value


def _verify_video(path):
    import cv2
    capture, count = cv2.VideoCapture(str(path)), 0
    try:
        if not capture.isOpened():
            raise ValueError("Could not decode new review clip")
        while True:
            ok, pixels = capture.read()
            if not ok:
                break
            if pixels.shape != (TILE_HEIGHT*4, TILE_WIDTH*3, 3):
                raise ValueError("Incorrect player-context review clip dimensions")
            count += 1
        if count != 25 or capture.get(cv2.CAP_PROP_FPS) != 5.0:
            raise ValueError("New review clip did not decode all 25 frames at 5 fps")
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
    indexed = {(a["window_id"], a["confidence_threshold"], a["frame_index"], a["arm"]): a
               for a in header["reused_assets"]}
    if len(indexed) != len(header["reused_assets"]):
        raise ValueError("Duplicate reused native-view identity")
    with tempfile.TemporaryDirectory(prefix=".pending_review_", dir=bundle.parent) as temporary:
        staging = Path(temporary).resolve()
        staging.relative_to(root)
        assets, evidence = [], []
        def add(target):
            assets.append({"path": target.relative_to(staging).as_posix(), "sha256": sha256_file(target)})

        for item in prepared.windows:
            w, run = item["window"], item["run"]
            writers = {}
            try:
                for offset, frame in enumerate(run.frames):
                    for threshold in THRESHOLDS:
                        records = {arm: indexed[w["window_id"], threshold, frame.frame_index, arm]
                                   for arm in (*CONTROL_ARMS, "unmarked_source")}
                        source = _read_png(root, records["unmarked_source"])
                        if source.shape != (run.source_video.height_px, run.source_video.width_px, 3):
                            raise ValueError("Saved unmarked PNG dimensions differ from source contract")
                        controls = {arm: _read_png(root, records[arm]) for arm in CONTROL_ARMS}
                        observations = {arm: item["observations"][arm, threshold]["frames"][offset]
                                        for arm in (*CONTROL_ARMS, *CONTEXT_ARMS)}
                        reports = {arm: item["reports"][arm, threshold]["frame_results"][offset]
                                   for arm in observations}
                        comparison, overlays, players, closeups, focuses = render_frame(
                            source, item["truth"][frame.frame_index], frame, observations, reports,
                            controls, item["player_rows"][frame.frame_index], threshold)
                        folder = staging / w["window_id"] / f"confidence_{threshold}"
                        for name, pixels in [("comparison", comparison), ("closeups", closeups),
                                             ("player_context", players),
                                             *((f"context_view_{i}", v) for i, v in enumerate(overlays))]:
                            target = folder / name / f"frame_{frame.frame_index:06d}.png"
                            target.parent.mkdir(parents=True, exist_ok=True)
                            if not cv2.imwrite(str(target), pixels):
                                raise ValueError("Could not write new player-context review PNG")
                            add(target)
                        evidence.append({"window_id": w["window_id"], "confidence_threshold": threshold,
                                         "frame_index": frame.frame_index, "source_png": records["unmarked_source"],
                                         "observed_player_boxes": len(item["player_rows"][frame.frame_index]),
                                         "closeup_regions": focuses})
                        if threshold not in writers:
                            target = folder / "comparison_slow.mp4"
                            writer = cv2.VideoWriter(str(target), cv2.VideoWriter_fourcc(*"mp4v"), 5.0,
                                                     (comparison.shape[1], comparison.shape[0]))
                            if not writer.isOpened():
                                writer.release()
                                raise ValueError("Could not open new player-context review writer")
                            writers[threshold] = writer, target
                        writers[threshold][0].write(comparison)
            finally:
                for writer, _ in writers.values():
                    writer.release()
            if len(writers) != 2:
                raise ValueError("Incomplete player-context confidence clips")
            for _, target in writers.values():
                _verify_video(target)
                add(target)
        persist_once(staging / "manifest.json", {"header": header, "assets": assets,
                     "final_frames": [{"window_id": w["window_id"], "frame_index": w["end_frame_index"]}
                                      for w in header["windows"]],
                     "frame_evidence": evidence, "human_visual_review": "pending"})
        validate_review_bundle(root, staging, header)
        prepared.verify()
        staging.rename(bundle)
    return {"bundle": str(bundle), "reused": False, "assets": len(assets),
            "reused_native_assets": len(header["reused_assets"]), "human_visual_review": "pending"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("render",), nargs="?", default="render")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.repository_root.resolve()
    print(json.dumps(render_experiment(root, (root / args.manifest).resolve()), indent=2))


if __name__ == "__main__":
    main()
