"""New synchronized mean-path review from caller-supplied bound source PNGs.

No source video is opened and no detection/selection/evaluation is executed.
The worker supplies all reads and create-only publication callbacks.
"""
from __future__ import annotations

import json

from .crop_path_confidence_mean_evaluation import ARMS, ARM, TT, TOP, frame_state

PANELS = ("unmarked_source", "saved_tt", "new_mean", "saved_top_one")
VIEW_NAMES = {TT: "saved_tt", ARM: "new_mean", TOP: "saved_top_one"}
TITLES = {TT: "SAVED TT: sum confidence", ARM: "NEW MEAN: mean confidence", TOP: "SAVED TOP ONE: current confidence"}
TILE_WIDTH, TILE_HEIGHT, HEADER = 960, 680, 140
NATIVE_HEADER = 140
FPS = 5.0


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _line(image, text, y, *, color=(235, 235, 235), size=.62):
    import cv2
    cv2.putText(image, text, (12, y), cv2.FONT_HERSHEY_SIMPLEX, size, color, 1, cv2.LINE_AA)


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


def _details(frame, observation, result):
    emitted = observation["emitted_candidate_indices"]
    candidates = {c.candidate_index: c for c in frame.detections}
    _require(len(emitted) <= 1 and all(i in candidates for i in emitted), "Unknown or multiple emitted candidates")
    state = frame_state(result)
    _require(result["accepted_detection_count"] == len(emitted)
             and (result["matched_candidate_index"] is None or result["matched_candidate_index"] in emitted),
             "Render report/emission mismatch")
    selection = "MISSING: no current output" if not emitted else f"candidate #{emitted[0]} | detector conf {candidates[emitted[0]].confidence:.6f}"
    ranking = observation["ranking"]
    if ranking is None:
        detail = "No history score | current highest-confidence candidate"
    else:
        winner = ranking["winner"]
        endpoint = winner["endpoint"]
        endpoint_text = "empty" if endpoint is None else f"frame {endpoint[0]} / #{endpoint[1]}"
        margin = ranking["score_margin"]
        detail = f"path n={len(winner['path'])} | score {winner['score']:.6f} | endpoint {endpoint_text}"
        detail += " | margin none" if margin is None else f" | margin {margin:.6f}"
    return selection, detail, state


def render_frame(source, annotation, frame, observations_by_arm, results_by_arm):
    """Return one four-panel composite and three source-scale overlays."""
    import cv2
    import numpy as np
    _require(set(observations_by_arm) == set(ARMS) and set(results_by_arm) == set(ARMS), "Exactly three fixed arm panels required")
    _require(source.ndim == 3 and source.shape[2] == 3 and source.dtype == np.uint8, "Expected native BGR source PNG")
    index = frame.frame_index
    _require(annotation.frame_index == index and all(observations_by_arm[a]["frame_index"] == results_by_arm[a]["frame_index"] == index for a in ARMS),
             "Review panels are not synchronized")
    panels, native, details = [], {}, {}
    source_panel = np.zeros((TILE_HEIGHT, TILE_WIDTH, 3), dtype=np.uint8)
    source_panel[HEADER:] = _fit(source)
    _line(source_panel, f"UNMARKED SOURCE | source frame {index}", 28, size=.78)
    _line(source_panel, "Same bound PNG in every panel; native overlays preserve source scale", 56)
    _line(source_panel, "Review all 25 frames through the final frame | playback 5 fps", 84)
    _line(source_panel, "Localization does not certify object identity", 112)
    panels.append(source_panel)
    for arm in ARMS:
        observation, result = observations_by_arm[arm], results_by_arm[arm]
        selection, detail, state = _details(frame, observation, result)
        overlay = source.copy()
        if annotation.geometry is not None:
            center = tuple(map(round, annotation.geometry.center_xy_px))
            cv2.drawMarker(overlay, center, (255, 255, 0), cv2.MARKER_CROSS, 18, 2)
            cv2.circle(overlay, center, 10, (255, 100, 0), 1)
            cv2.circle(overlay, center, round(annotation.geometry.uncertainty_radius_px), (0, 255, 255), 1)
        for candidate in frame.detections:
            if candidate.candidate_index not in observation["emitted_candidate_indices"]:
                continue
            color = (0, 220, 0) if state == "matched" else (0, 100, 255) if state == "alarm" else (0, 0, 255)
            point = tuple(map(round, candidate.center_xy_px))
            cv2.circle(overlay, point, 7, color, 2)
            cv2.drawMarker(overlay, point, color, cv2.MARKER_TILTED_CROSS, 11, 1)
            cv2.putText(overlay, f"#{candidate.candidate_index}", (max(0, point[0] + 10), max(14, point[1] - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, .65, color, 2, cv2.LINE_AA)
        native_header = np.zeros((NATIVE_HEADER, source.shape[1], 3), dtype=np.uint8)
        heading = f"{TITLES[arm]} | source frame {index} | {state}"
        settings = "floor .01 | " + ("top 1 current" if arm == TOP else "cap 20 | horizon 5 | edge/cost .01") + " | raw radius 10 px"
        legend = "Cyan cross=reference; blue ring=raw10; yellow=uncertainty; scores/margins are NOT probabilities"
        for y, text in ((24, heading), (49, settings), (74, selection), (99, detail), (126, legend)):
            _line(native_header, text, y, size=.65 if source.shape[1] >= 1000 else .29)
        native[VIEW_NAMES[arm]] = np.vstack((native_header, overlay))
        panel = np.zeros((TILE_HEIGHT, TILE_WIDTH, 3), dtype=np.uint8)
        panel[HEADER:] = _fit(overlay)
        for y, text, size in ((23, heading, .65), (47, settings, .53), (71, selection, .58),
                              (94, detail, .46), (117, "Cyan=reference; blue=raw10; yellow=uncertainty; scores NOT probabilities", .49)):
            _line(panel, text, y, size=size)
        panels.append(panel)
        details[VIEW_NAMES[arm]] = {"frame_index": index, "emitted_candidate_indices": list(observation["emitted_candidate_indices"]),
                                  "state": state, "selection_text": selection, "path_text": detail,
                                  "missing_reason": observation["decision_reason"] if not observation["emitted_candidate_indices"] else None}
    composite = np.vstack((np.hstack(panels[:2]), np.hstack(panels[2:])))
    return composite, native, details


def render_window(window, run, labels, observations_by_arm, reports_by_arm, *,
                  read_source, write_bytes, open_video, verify_video):
    """Render exactly 25 PNG-backed frames through explicit worker callbacks.

    read_source(frame_index) returns a verified BGR image. write_bytes(relative,
    payload) publishes create-only and returns its binding. open_video(relative,
    fps, size) returns an owned writer; verify_video(relative,count,fps,size)
    verifies the finished generated video and returns its binding. No callback
    may decode source video, rerun inference, or follow provenance pointers.
    """
    import cv2
    expected = list(range(window["start_frame_index"], window["end_frame_index"] + 1))
    _require(len(expected) == 25 and [f.frame_index for f in run.frames] == expected, "Review needs the complete 25-frame source window")
    _require(set(observations_by_arm) == set(ARMS) and set(reports_by_arm) == set(ARMS), "Incomplete fixed review arms")
    _require(window["source_video"] == run.source_video.to_dict(), "Review source metadata differs")
    for arm in ARMS:
        _require([r["frame_index"] for r in observations_by_arm[arm]["frames"]] == expected
                 and [r["frame_index"] for r in reports_by_arm[arm]["frame_results"]] == expected,
                 "Review input frames are incomplete/reordered")
    truth = labels.annotation_by_frame()
    prefix = f"review/{window['window_id']}"
    video_path, size = prefix + "/comparison.mp4", (TILE_WIDTH * 2, TILE_HEIGHT * 2)
    assets, frame_rows = [], []
    writer = None

    def publish_png(relative, pixels):
        ok, encoded = cv2.imencode(".png", pixels)
        _require(ok, "Could not encode new review PNG")
        assets.append(write_bytes(relative, encoded.tobytes()))

    try:
        for offset, frame in enumerate(run.frames):
            source = read_source(frame.frame_index)
            _require(source.shape == (run.source_video.height_px, run.source_video.width_px, 3), "Bound source PNG has incorrect dimensions")
            composite, native, details = render_frame(source, truth[frame.frame_index], frame,
                {a: observations_by_arm[a]["frames"][offset] for a in ARMS},
                {a: reports_by_arm[a]["frame_results"][offset] for a in ARMS})
            _require(composite.shape == (size[1], size[0], 3) and set(native) == set(VIEW_NAMES.values()), "Incomplete rendered panels")
            for name, pixels in native.items():
                _require(pixels.shape == (run.source_video.height_px + NATIVE_HEADER, run.source_video.width_px, 3), "Native overlay lost source scale")
                publish_png(f"{prefix}/native/{name}/frame_{frame.frame_index:06d}.png", pixels)
            if offset == 0:
                publish_png(prefix + "/first.png", composite)
                writer = open_video(video_path, FPS, size)
                _require(writer is not None, "Could not open owned review writer")
            if offset == 24:
                publish_png(prefix + "/last.png", composite)
            writer.write(composite)
            frame_rows.append({"frame_index": frame.frame_index, "panels": details,
                               "reference_geometry_present": truth[frame.frame_index].geometry is not None,
                               "annotation_visibility": truth[frame.frame_index].visibility})
    finally:
        if writer is not None:
            writer.release()
    _require(len(frame_rows) == 25 and frame_rows[-1]["frame_index"] == window["end_frame_index"], "Missing final review frame")
    assets.append(verify_video(video_path, 25, FPS, size))
    changes = {VIEW_NAMES[a]: [row["frame_index"] for row in frame_rows
               if row["panels"][VIEW_NAMES[a]]["emitted_candidate_indices"] != row["panels"]["new_mean"]["emitted_candidate_indices"]]
               for a in (TT, TOP)}
    index = {"schema_version": "ball_crop_path_confidence_mean_review/v0.1", "window_id": window["window_id"],
             "purpose": window["purpose"], "panels": list(PANELS), "fps": FPS, "frame_count": 25,
             "first_frame_index": expected[0], "final_frame_index": expected[-1], "frame_indices": expected,
             "native_overlay_count": 75, "native_source_dimensions": [run.source_video.width_px, run.source_video.height_px],
             "native_header_height": NATIVE_HEADER, "first_last_composites": 2, "assets": assets,
             "changed_emission_frame_indices": changes, "frames": frame_rows,
             "disclosures": ["Cyan cross is reviewed reference geometry; blue ring is raw10 matching radius; yellow ring is annotation uncertainty.",
                             "Hidden frames have no invented reference center.", "Heuristic path scores/margins are not probabilities.",
                             "Old human judgments were not transferred to new choices.", "Native overlay source area is unscaled; the header is additional."],
             "human_final_frame_review": "pending", "old_reviews_reopened": False,
             "source_video_decodes": 0, "inference_calls": 0, "selected_operating_point": None, "quality_gate": None}
    binding = write_bytes(prefix + "/review_index.json", (json.dumps(index, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"))
    return {"index": index, "index_binding": binding}
