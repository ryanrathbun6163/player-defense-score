"""Synchronized corroboration review from explicitly supplied bound images.

This module performs no selection, scoring, source-file reads or video decoding.
The caller owns phase authorization, verified image reads, and create-only
publication. Stage-one use is restricted to artificial fixtures.
"""
from __future__ import annotations

import json
import re

from .crop_cross_detector_corroboration_evaluation import ARM, TOP, frame_state
from .development_experiments import canonical_sha256, require_digest

ARMS = (TOP, ARM)
PANELS = ("unmarked_source", "saved_top_one", "new_corroborated")
VIEW_NAMES = {TOP: "saved_top_one", ARM: "new_corroborated"}
TITLES = {TOP: "SAVED RF TOP ONE", ARM: "NEW RF/YOLO CORROBORATED"}
TILE_WIDTH, TILE_HEIGHT, HEADER = 960, 680, 140
NATIVE_HEADER = 140
FPS = 5.0


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _line(image, text, y, *, size=.60):
    import cv2
    cv2.putText(image, text, (12, y), cv2.FONT_HERSHEY_SIMPLEX, size,
                (235, 235, 235), 1, cv2.LINE_AA)


def _fit(source):
    import cv2
    import numpy as np
    body = np.zeros((TILE_HEIGHT - HEADER, TILE_WIDTH, 3), dtype=np.uint8)
    scale = min(body.shape[1] / source.shape[1], body.shape[0] / source.shape[0])
    width, height = max(1, round(source.shape[1] * scale)), max(1, round(source.shape[0] * scale))
    fitted = cv2.resize(source, (width, height), interpolation=cv2.INTER_AREA)
    x, y = (body.shape[1] - width) // 2, (body.shape[0] - height) // 2
    body[y:y + height, x:x + width] = fitted
    return body


def _frame_details(annotation, frame, observations, results):
    """Validate supplied identities and states without recomputing either."""
    _require(set(observations) == set(ARMS) and set(results) == set(ARMS),
             "Exactly saved RF top-one and new corroborated panels required")
    index = frame.frame_index
    _require(annotation.frame_index == index and all(
        observations[a]["frame_index"] == results[a]["frame_index"] == index for a in ARMS),
        "Review panels are not synchronized")
    candidates = {c.candidate_index: c for c in frame.detections}
    _require(len(candidates) == len(frame.detections), "Duplicate RF candidate identities")
    expected_status = ("localization_eligible" if annotation.localization_eligible else
                       "not_visible_negative" if annotation.visibility == "not_visible" else "unscored")
    details = {}
    for arm in ARMS:
        observation, result = observations[arm], results[arm]
        emitted = observation["emitted_candidate_indices"]
        _require(isinstance(emitted, list) and len(emitted) <= 1 and
                 all(type(i) is int and i in candidates and candidates[i].confidence >= .01 for i in emitted),
                 "Unknown, multiple or below-floor emitted RF candidates")
        _require(result["accepted_detection_count"] == len(emitted) and
                 (result["matched_candidate_index"] is None or result["matched_candidate_index"] in emitted),
                 "Render report/emission mismatch")
        _require(result["scoring_status"] == expected_status and
                 result["visibility"] == annotation.visibility and
                 result["annotation_status"] == annotation.annotation_status,
                 "Render report/annotation mismatch")
        if arm == ARM:
            _require(observation["emitted_candidates"] == [candidates[i].to_dict() for i in emitted],
                     "New output changed original RF geometry or confidence")
        _require(isinstance(observation["decision_reason"], str) and bool(observation["decision_reason"]),
                 "Missing supplied decision reason")
        state = frame_state(result)
        candidate = candidates[emitted[0]] if emitted else None
        selection = ("MISSING: no accepted observation" if candidate is None else
                     f"RF candidate #{candidate.candidate_index} | original RF conf {candidate.confidence:.6f}")
        details[VIEW_NAMES[arm]] = {
            "frame_index": index, "emitted_candidate_indices": list(emitted), "state": state,
            "selection_text": selection,
            "missing_reason": observation["decision_reason"] if candidate is None else None,
            "original_rf_center_xy_px": list(candidate.center_xy_px) if candidate else None,
            "original_rf_bbox_xyxy_px": list(candidate.bbox_xyxy_px) if candidate else None,
            "original_rf_confidence": candidate.confidence if candidate else None,
            "semantic_identity": None,
        }
    old, new = (details[VIEW_NAMES[a]] for a in ARMS)
    before, after = old["emitted_candidate_indices"], new["emitted_candidate_indices"]
    choice = ("retained" if before == after and before else "both_missing" if before == after else
              "suppressed" if before and not after else "replacement" if before else "new_emission")
    return details, {"old_state": old["state"], "new_state": new["state"], "choice": choice,
                     "changed_emission": before != after,
                     "lost_correct_choice": old["state"] == "matched" and new["state"] != "matched",
                     "error_suppressed": old["state"] == "wrong_present" and new["state"] == "missing",
                     "match_recovered": old["state"] in ("wrong_present", "missing") and new["state"] == "matched",
                     "wrong_replacement": choice == "replacement" and new["state"] == "wrong_present"}


def render_frame(source, annotation, frame, observations_by_arm, results_by_arm):
    """Return source/top-one/corroborated composite and two native overlays.

    Source pixels are never changed. Display markers use the unchanged original
    RF box/center, rounding only when rasterizing. Corroboration is not an object
    identity or visibility claim, and no prior human judgment is inherited.
    """
    import cv2
    import numpy as np
    _require(isinstance(source, np.ndarray) and source.ndim == 3 and source.shape[2] == 3 and
             source.dtype == np.uint8 and min(source.shape[:2]) > 0, "Expected native BGR source image")
    details, _ = _frame_details(annotation, frame, observations_by_arm, results_by_arm)
    panels, native = [], {}
    source_panel = np.zeros((TILE_HEIGHT, TILE_WIDTH, 3), dtype=np.uint8)
    source_panel[HEADER:] = _fit(source)
    for y, text in ((25, f"UNMARKED SOURCE | source frame {frame.frame_index}"),
                    (53, "Same bound image in all panels; native overlays retain source scale"),
                    (81, "Review all 25 frames through the final frame | playback 5 fps"),
                    (109, "Agreement is not object identity; missing output is not a hidden label")):
        _line(source_panel, text, y, size=.57)
    panels.append(source_panel)
    for arm in ARMS:
        detail = details[VIEW_NAMES[arm]]
        overlay = source.copy()
        if annotation.geometry is not None:
            center = tuple(map(round, annotation.geometry.center_xy_px))
            cv2.drawMarker(overlay, center, (255, 255, 0), cv2.MARKER_CROSS, 18, 2)
            cv2.circle(overlay, center, 10, (255, 100, 0), 1)
            cv2.circle(overlay, center, round(annotation.geometry.uncertainty_radius_px), (0, 255, 255), 1)
        if detail["emitted_candidate_indices"]:
            color = ((0, 220, 0) if detail["state"] == "matched" else
                     (0, 100, 255) if detail["state"] == "alarm" else (0, 0, 255))
            point = tuple(map(round, detail["original_rf_center_xy_px"]))
            x1, y1, x2, y2 = map(round, detail["original_rf_bbox_xyxy_px"])
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 1)
            cv2.circle(overlay, point, 7, color, 2)
            cv2.drawMarker(overlay, point, color, cv2.MARKER_TILTED_CROSS, 11, 1)
            cv2.putText(overlay, f"RF #{detail['emitted_candidate_indices'][0]}",
                        (max(0, point[0] + 10), max(14, point[1] - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, .60, color, 1, cv2.LINE_AA)
        heading = f"{TITLES[arm]} | source frame {frame.frame_index} | {detail['state']}"
        settings = ("RF floor .01 | original highest confidence" if arm == TOP else
                    "RF/YOLO floors .01 | box IoU >= .50 | same frame only") + " | raw10"
        meaning = ("Original RF geometry/confidence unchanged; score is NOT probability" if detail["emitted_candidate_indices"] else
                   "No accepted observation; this is NOT an occlusion/visibility judgment")
        legend = "Cyan cross=reference; blue=raw10; yellow=uncertainty; box/ring/X=prediction"
        lines = ((23, heading), (47, settings), (71, detail["selection_text"]), (95, meaning), (122, legend))
        native_header = np.zeros((NATIVE_HEADER, source.shape[1], 3), dtype=np.uint8)
        for y, text in lines:
            _line(native_header, text, y, size=.60 if source.shape[1] >= 1000 else .28)
        native[VIEW_NAMES[arm]] = np.vstack((native_header, overlay))
        panel = np.zeros((TILE_HEIGHT, TILE_WIDTH, 3), dtype=np.uint8)
        panel[HEADER:] = _fit(overlay)
        for y, text in lines:
            _line(panel, text, y, size=.53)
        panels.append(panel)
    return np.hstack(panels), native, details


def _validate_window(window, run, labels, observations, reports):
    expected = list(range(window["start_frame_index"], window["end_frame_index"] + 1))
    _require(len(expected) == 25 and [f.frame_index for f in run.frames] == expected,
             "Review needs the complete 25-frame source window")
    _require(set(observations) == set(ARMS) and set(reports) == set(ARMS), "Incomplete fixed review arms")
    _require(isinstance(window["window_id"], str) and re.fullmatch(r"[A-Za-z0-9_-]+", window["window_id"]),
             "Unsafe review window id")
    _require(window["source_video"] == run.source_video.to_dict() == labels.source_video.to_dict() and
             window["possession_id"] == run.possession_id == labels.possession_id and
             window["purpose"] == labels.window.selection_purpose and
             labels.window.start_frame_index == expected[0] and labels.window.end_frame_index == expected[-1],
             "Review source, possession, label window or pool differs")
    truth = labels.annotation_by_frame()
    _require(list(truth) == expected, "Review label frames incomplete/reordered")
    candidate_digest, label_digest = canonical_sha256(run.to_dict()), canonical_sha256(labels.to_dict())
    for arm in ARMS:
        observation, report = observations[arm], reports[arm]
        _require(observation["config"]["arm"] == arm and observation["config"]["confidence_threshold"] == .01 and
                 report["config"] == observation["config"] and report["localization_radius_px"] == 10.0,
                 "Review settings differ from fixed arm")
        if arm == ARM:
            _require(observation["config"].get("iou_threshold") == .5, "Review IoU differs")
            rf_binding = observation["input_bindings"]["rfdetr"]
            _require(rf_binding["detector"] == "rfdetr" and rf_binding["content_sha256"] == candidate_digest and
                     rf_binding["detection_run_id"] == run.detection_run_id and
                     rf_binding["model_provenance"] == run.model_provenance.to_dict() and
                     report["input_bindings"] == observation["input_bindings"], "Review RF detector binding differs")
        for value in (observation, report):
            _require(value["source_video"] == run.source_video.to_dict() and
                     value["window"] == run.window.to_dict() and value["possession_id"] == run.possession_id and
                     value["input_candidate_content_sha256"] == candidate_digest, "Review candidate/source provenance differs")
            require_digest(value["ranking_code_commit"], "review selection commit", 40)
        require_digest(report["evaluator_code_commit"], "review evaluator commit", 40)
        _require(report["variant_id"] == observation["variant_id"] and
                 report["ranking_code_commit"] == observation["ranking_code_commit"] and
                 report["observations_content_sha256"] == canonical_sha256(observation) and
                 report["annotation_content_sha256"] == label_digest and
                 report["input_model_provenance"] == run.model_provenance.to_dict() and
                 report["selection_purpose"] == window["purpose"] and
                 report["matching_rule"] == "raw center distance; uncertainty diagnostic only",
                 "Review report provenance differs")
        _require([r["frame_index"] for r in observation["frames"]] == expected and
                 [r["frame_index"] for r in report["frame_results"]] == expected,
                 "Review input frames incomplete/reordered")
    for offset, frame in enumerate(run.frames):
        _frame_details(truth[frame.frame_index], frame,
                       {a: observations[a]["frames"][offset] for a in ARMS},
                       {a: reports[a]["frame_results"][offset] for a in ARMS})
    return expected, truth


def render_window(window, run, labels, observations_by_arm, reports_by_arm, *,
                  read_source, write_bytes, open_video, verify_video):
    """Render 25 bound image frames at 5 fps using only caller-owned I/O.

    read_source(index) supplies a verified BGR image. write_bytes(relative,
    bytes) must create a new output or refuse overwriting. open_video(relative,
    fps,size) owns the generated writer; verify_video(relative,count,fps,size)
    verifies the completed generated video. No callback may decode source video,
    rerun inference/selection/scoring, or follow an unapproved provenance path.
    """
    import cv2
    expected, truth = _validate_window(window, run, labels, observations_by_arm, reports_by_arm)
    prefix = f"review/{window['window_id']}"
    video_path, size = prefix + "/comparison.mp4", (TILE_WIDTH * 3, TILE_HEIGHT)
    assets, frame_rows, writer = [], [], None

    def png(relative, pixels):
        ok, encoded = cv2.imencode(".png", pixels)
        _require(ok, "Could not encode new review PNG")
        assets.append(write_bytes(relative, encoded.tobytes()))

    try:
        for offset, frame in enumerate(run.frames):
            source = read_source(frame.frame_index)
            _require(source.shape == (run.source_video.height_px, run.source_video.width_px, 3),
                     "Bound source image dimensions differ")
            obs = {a: observations_by_arm[a]["frames"][offset] for a in ARMS}
            results = {a: reports_by_arm[a]["frame_results"][offset] for a in ARMS}
            composite, native, details = render_frame(source, truth[frame.frame_index], frame, obs, results)
            _require(composite.shape == (size[1], size[0], 3) and set(native) == set(VIEW_NAMES.values()),
                     "Incomplete rendered panels")
            for name, pixels in native.items():
                _require(pixels.shape == (run.source_video.height_px + NATIVE_HEADER, run.source_video.width_px, 3),
                         "Native overlay lost source scale")
                png(f"{prefix}/native/{name}/frame_{frame.frame_index:06d}.png", pixels)
            if offset == 0:
                png(prefix + "/first.png", composite)
                writer = open_video(video_path, FPS, size)
                _require(writer is not None, "Could not open owned review writer")
            if offset == 24:
                png(prefix + "/last.png", composite)
            writer.write(composite)
            _, change = _frame_details(truth[frame.frame_index], frame, obs, results)
            frame_rows.append({"frame_index": frame.frame_index, "panels": details,
                               "comparison": change, "reference_geometry_present": truth[frame.frame_index].geometry is not None,
                               "annotation_visibility": truth[frame.frame_index].visibility})
    finally:
        if writer is not None:
            writer.release()
    _require(len(frame_rows) == 25 and frame_rows[-1]["frame_index"] == expected[-1], "Missing final review frame")
    assets.append(verify_video(video_path, 25, FPS, size))
    indexed = {key + "_frame_indices": [r["frame_index"] for r in frame_rows if r["comparison"][key]]
               for key in ("changed_emission", "lost_correct_choice", "error_suppressed", "match_recovered", "wrong_replacement")}
    index = {"schema_version": "ball_crop_cross_detector_corroboration_review/v0.1", "window_id": window["window_id"],
             "purpose": window["purpose"], "panels": list(PANELS), "fps": FPS, "frame_count": 25,
             "first_frame_index": expected[0], "final_frame_index": expected[-1], "frame_indices": expected,
             "source_video": run.source_video.to_dict(), "input_candidate_content_sha256": canonical_sha256(run.to_dict()),
             "input_observation_content_sha256": {a: canonical_sha256(observations_by_arm[a]) for a in ARMS},
             "input_report_content_sha256": {a: canonical_sha256(reports_by_arm[a]) for a in ARMS},
             "native_overlay_count": 50, "native_source_dimensions": [run.source_video.width_px, run.source_video.height_px],
             "native_header_height": NATIVE_HEADER, "first_last_composites": 2, "assets": assets, **indexed,
             "frames": frame_rows,
             "disclosures": ["Cyan cross is reference geometry; blue ring is raw10; yellow ring is annotation uncertainty.",
                             "Prediction box/ring/X uses unchanged original RF geometry; displayed coordinates are rasterized only.",
                             "Hidden frames have no invented reference center; missing output is not a visibility label.",
                             "Detector agreement does not certify physical identity; confidence is not a calibrated probability.",
                             "Lost baseline matches are explicitly indexed alongside improvements.",
                             "Prior human judgments are not transferred to replacements; old reviews remain closed.",
                             "Native overlay source area is unscaled; the header is additional."],
             "human_final_frame_review": "pending", "old_reviews_reopened": False,
             "source_video_decodes": 0, "inference_calls": 0, "selection_calls": 0, "evaluation_calls": 0,
             "selected_operating_point": None, "quality_gate": None}
    binding = write_bytes(prefix + "/review_index.json",
                          (json.dumps(index, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"))
    return {"index": index, "index_binding": binding}
