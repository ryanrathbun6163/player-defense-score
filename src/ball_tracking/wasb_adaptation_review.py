"""Clearly labeled review of the final adapted WASB checkpoint at fixed 0.5."""
from __future__ import annotations

import subprocess
from pathlib import Path

import cv2

from .wasb_experiment import decode_window, digest_file, read_json, write_once
from .wasb_review import player_rows, render_image, verify_video


def render_window(root, window, labels, methods, evaluation, folder):
    points = methods["wasb_top_one"]
    provenance = points["model_provenance"]
    checkpoint = provenance["weights"]["sha256"]
    if provenance["inference"]["heatmap_threshold"] != .5 or not provenance.get("training_completion"):
        raise ValueError("Adapted review expects the bound trained checkpoint at fixed 0.5")
    identity = {"renderer_sha256": digest_file(Path(__file__)),
        "base_renderer_sha256": digest_file(Path(__file__).with_name("wasb_review.py")),
        "points_sha256": digest_file(folder / "points.json"),
        "evaluation_sha256": digest_file(folder / "evaluation.json"),
        "checkpoint_sha256": checkpoint, "heatmap_threshold": .5, "window_id": window["window_id"]}
    target, receipt = folder / "adapted_review.mp4", folder / "adapted_review.json"
    if receipt.exists():
        old = read_json(receipt)
        if old["identity"] != identity or digest_file(target) != old["video_sha256"]:
            raise ValueError("Completed adapted review differs from its recorded inputs")
        return
    if target.exists():
        raise ValueError("Preserve an unreceipted adapted review before replacing it")
    intermediate = folder / "adapted_review_intermediate.mp4"
    if intermediate.exists():
        raise ValueError("Preserve the partial adapted review before retrying")
    frames = decode_window(root, window)
    players, player_binding = player_rows(root, window)
    contributions = provenance["temporal_contributions_per_frame"]
    source = window["source_video"]
    writer = cv2.VideoWriter(str(intermediate), cv2.VideoWriter_fourcc(*"mp4v"), 5,
                            (source["width_px"], source["height_px"] + 150))
    if not writer.isOpened():
        raise ValueError("Adapted review video writer failed")
    try:
        for offset, (annotation, wasb, rf) in enumerate(zip(
                labels.annotations, points["frames"], methods["rf_top_one"]["frames"], strict=True)):
            if annotation.frame_index != wasb["frame_index"] or annotation.frame_index != rf["frame_index"]:
                raise ValueError("Review frames are not synchronized")
            canvas = render_image(frames[annotation.frame_index], annotation, wasb, rf,
                                  players.get(annotation.frame_index, []), contributions[offset])
            canvas[0:43] = 0
            title = (f"ADAPTED WASB | checkpoint {checkpoint[:12]} | threshold >0.5 | "
                     f"FRAME {annotation.frame_index} | {annotation.visibility} | playback 5 fps")
            cv2.putText(canvas, title, (18, 31), cv2.FONT_HERSHEY_SIMPLEX,
                        .66, (255, 255, 255), 2, cv2.LINE_AA)
            writer.write(canvas)
            if offset in {0, len(frames) - 1}:
                if not cv2.imwrite(str(folder / f"adapted_review_frame_{annotation.frame_index:06d}.png"), canvas):
                    raise ValueError("Could not write adapted review endpoint")
    finally:
        writer.release()
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-n", "-i", str(intermediate),
        "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(target)], check=True)
    verification = verify_video(target, len(frames), canvas.shape)
    write_once(receipt, {"identity": identity, "video_sha256": digest_file(target),
        "source_frame_indices": list(frames), "final_source_frame": max(frames), "playback_fps": 5,
        "verification": verification, "player_display_input": player_binding,
        "human_visual_review": "pending", "selected_operating_point": None})
    intermediate.unlink()
