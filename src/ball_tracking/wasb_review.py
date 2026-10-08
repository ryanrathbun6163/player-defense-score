"""Synchronized source/player/ball review for the WASB development comparison."""
from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np

from .wasb_experiment import decode_window, digest_file, repository_path, write_once

COLORS = {"truth": (70, 230, 70), "wasb": (240, 80, 240), "rf": (0, 215, 255)}


def player_rows(root, window):
    path = repository_path(root, f"data/outputs/identity/{window['possession_id']}_reconciled_tracks.csv")
    result = {}
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            frame = int(row["frame_index"])
            if window["start_frame_index"] <= frame <= window["end_frame_index"]:
                result.setdefault(frame, []).append(row)
    return result, {"path": path.relative_to(root).as_posix(), "sha256": digest_file(path),
                    "role": "display_only_existing_reviewed_player_identity; not a WASB input"}


def marker(image, center, color, kind):
    x, y = map(round, center)
    if not 0 <= x < image.shape[1] or not 0 <= y < image.shape[0]:
        return
    if kind == "wasb":
        cv2.drawMarker(image, (x, y), color, cv2.MARKER_CROSS, 23, 2, cv2.LINE_AA)
    else:
        cv2.circle(image, (x, y), 10 if kind == "truth" else 15, color, 2, cv2.LINE_AA)


def render_image(source, annotation, wasb_frame, rf_frame, players, contribution_count):
    canvas = np.zeros((source.shape[0] + 150, source.shape[1], 3), dtype=np.uint8)
    overlay = source.copy()
    for row in players:
        x, y = round(float(row["floor_x"])), round(float(row["floor_y"]))
        cv2.circle(overlay, (x, y), 4, (230, 230, 230), -1)
        cv2.putText(overlay, row["player_id"], (x + 5, y + 12), cv2.FONT_HERSHEY_SIMPLEX,
                    .44, (245, 245, 245), 1, cv2.LINE_AA)
    if annotation.geometry is not None:
        marker(overlay, annotation.geometry.center_xy_px, COLORS["truth"], "truth")
    for name, frame in (("wasb", wasb_frame), ("rf", rf_frame)):
        for candidate in frame["candidates"]:
            marker(overlay, candidate["center_xy_px"], COLORS[name], name)
    canvas[150:] = overlay
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(canvas, f"SOURCE FRAME {annotation.frame_index} | {annotation.visibility} | slow playback 5 fps (source 25 fps)",
                (18, 31), font, .75, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(canvas, "Green circle: reviewed center | Magenta cross: WASB | Yellow circle: saved RF top-one",
                (18, 64), font, .65, (235, 235, 235), 1, cv2.LINE_AA)
    wasb_text = "MISSING" if not wasb_frame["candidates"] else f"heatmap mass {wasb_frame['candidates'][0]['native_score']:.3f}"
    rf_text = "MISSING" if not rf_frame["candidates"] else f"confidence {rf_frame['candidates'][0]['native_score']:.3f}"
    cv2.putText(canvas, f"WASB: {wasb_text} | RF: {rf_text} | aligned temporal contributions: {contribution_count}",
                (18, 99), font, .65, (235, 235, 235), 1, cv2.LINE_AA)
    cv2.putText(canvas, "WASB heatmap mass is not a probability. White labels reuse reviewed player identities. Human review pending.",
                (18, 132), font, .58, (190, 190, 190), 1, cv2.LINE_AA)
    return canvas


def verify_video(path, expected_count, expected_shape):
    capture = cv2.VideoCapture(str(path))
    count = 0
    last = None
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame.shape != expected_shape:
                raise ValueError("Review video dimensions differ")
            count += 1
            last = frame
    finally:
        capture.release()
    if count != expected_count or last is None:
        raise ValueError("Review video omitted frames or failed final-frame decoding")
    return {"decoded_frames": count, "final_frame_decoded": True}


def render_window(root, window, labels, methods, evaluation, folder):
    target = folder / "review.mp4"
    receipt = folder / "review.json"
    identity = {"renderer_sha256": digest_file(Path(__file__)),
                "wasb_points_sha256": digest_file(folder / "points.json"),
                "evaluation_sha256": digest_file(folder / "evaluation.json"),
                "window_id": window["window_id"]}
    if receipt.exists():
        previous = json.loads(receipt.read_text(encoding="utf-8"))
        if previous["identity"] != identity or digest_file(target) != previous["video_sha256"]:
            raise ValueError("Existing review provenance/content differs; preserve before rerendering")
        return
    if target.exists():
        raise ValueError("Unreceipted review exists; preserve and inspect before replacing")
    images = decode_window(root, window)
    players, player_binding = player_rows(root, window)
    indices = list(images)
    contributions = methods["wasb_top_one"]["model_provenance"]["temporal_contributions_per_frame"]
    raw_path = folder / "review_intermediate.mp4"
    if raw_path.exists():
        raise ValueError("Partial intermediate review exists; preserve before retry")
    writer = cv2.VideoWriter(str(raw_path), cv2.VideoWriter_fourcc(*"mp4v"), 5,
                            (window["source_video"]["width_px"], window["source_video"]["height_px"] + 150))
    if not writer.isOpened():
        raise ValueError("Review video writer failed")
    try:
        for offset, (annotation, wasb, rf) in enumerate(zip(labels.annotations, methods["wasb_top_one"]["frames"],
                                                       methods["rf_top_one"]["frames"], strict=True)):
            if annotation.frame_index != wasb["frame_index"] or annotation.frame_index != rf["frame_index"]:
                raise ValueError("Review inputs are not synchronized")
            frame = render_image(images[annotation.frame_index], annotation, wasb, rf,
                                 players.get(annotation.frame_index, []), contributions[offset])
            writer.write(frame)
            if offset in {0, len(indices) - 1}:
                if not cv2.imwrite(str(folder / f"review_frame_{annotation.frame_index:06d}.png"), frame):
                    raise ValueError("Review endpoint image write failed")
    finally:
        writer.release()
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-n", "-i", str(raw_path),
                    "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    str(target)], check=True)
    verified = verify_video(target, len(indices), frame.shape)
    write_once(receipt, {"identity": identity, "video_sha256": digest_file(target),
                        "source_frame_indices": indices, "playback_fps": 5,
                        "final_source_frame": indices[-1], "verification": verified,
                        "player_display_input": player_binding, "human_visual_review": "pending"})
    # The intermediate is owned by this call and the completed video is verified.
    raw_path.unlink()
