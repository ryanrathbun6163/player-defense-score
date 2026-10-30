"""Bound, source-rate visual comparison of existing WASB candidate selections.

This renderer consumes selections, never labels or a model. Protected source
frames are not requested, player IDs are display-only, and gaps stay empty.
"""
from __future__ import annotations

import math
from pathlib import Path
import shutil
import subprocess
import time
import traceback
import uuid

import cv2
import numpy as np

from . import wasb_development_observation as observation
from .annotations import SourceVideo, verify_source_video_contract
from .wasb_experiment import bound_path, canonical, digest_file, read_json, repository_path, write_once


HEADER_HEIGHT = 160
KNOWN_CUES = {
    "possession_001": [246, 247, 248, 439, 440, 441, 442],
    "possession_002": [2, 3],
    "possession_003": [63, 64, 65],
}


def validate_timeline(possession, timeline):
    """Reject malformed or protected observations before opening a decoder."""
    source, rows = possession["source_video"], timeline["frames"]
    if timeline["source_video"] != source:
        raise ValueError("Comparison source metadata differs")
    if possession["visible_segments"] != observation.complement_ranges(
            source["frame_count"], possession["protected_ranges"]):
        raise ValueError("Visible segments do not complement protected ranges")
    for segment in possession["visible_segments"]:
        observation.guard_segment(possession, segment)
    if [row["frame_index"] for row in rows] != list(range(source["frame_count"])):
        raise ValueError("Comparison timeline must contain every source frame exactly once")
    for row in rows:
        protected = any(a <= row["frame_index"] <= b for a, b in possession["protected_ranges"])
        if (row["state"] == "withheld") != protected:
            raise ValueError("Comparison withheld state differs from protected bands")
        if row["state"] not in {"observed", "missing", "withheld"}:
            raise ValueError("Unknown comparison state")
        for center_key, index_key in (("center_xy_px", "selected_candidate_index"),
                                      ("baseline_center_xy_px", "baseline_candidate_index")):
            center, index = row[center_key], row[index_key]
            if (center is None) != (index is None):
                raise ValueError("Candidate index and center must both exist or both be missing")
            if protected and center is not None:
                raise ValueError("Withheld comparison must contain no ball selection")
            if center is not None:
                if (type(index) is not int or len(center) != 2
                        or any(isinstance(v, bool) or not isinstance(v, (int, float))
                               or not math.isfinite(v) for v in center)):
                    raise ValueError("Invalid comparison candidate center/index")
                if "candidates" in row:
                    matches = [c for c in row["candidates"] if c["candidate_index"] == index]
                    if len(matches) != 1 or center != [matches[0]["center_x"], matches[0]["center_y"]]:
                        raise ValueError("Comparison center differs from existing raw candidate")
        if protected and row.get("candidates"):
            raise ValueError("Withheld comparison must contain no raw candidates")
        if (row["state"] == "observed") != (row["center_xy_px"] is not None):
            raise ValueError("Motion observation state disagrees with selected center")


def render_frame(pixels, row, source, players):
    """Preserve each source pixel's scale and identical timing in both panels."""
    width, height = source["width_px"], source["height_px"]
    canvas = np.zeros((height + HEADER_HEIGHT, 2 * width, 3), dtype=np.uint8)
    withheld = row["state"] == "withheld"
    if withheld:
        if pixels is not None or row["center_xy_px"] is not None or row["baseline_center_xy_px"] is not None:
            raise ValueError("Withheld render must receive no source pixels or ball centers")
    else:
        if pixels is None or pixels.shape != (height, width, 3):
            raise ValueError("Visible comparison requires its synchronized source image")
        overlay = pixels.copy()
        for player in players:
            x, y = round(float(player["floor_x"])), round(float(player["floor_y"]))
            cv2.circle(overlay, (x, y), 4, (230, 230, 230), -1)
            cv2.putText(overlay, player["player_id"], (x + 5, y + 12), cv2.FONT_HERSHEY_SIMPLEX,
                        .44, (245, 245, 245), 1, cv2.LINE_AA)
        for panel, center in enumerate((row["baseline_center_xy_px"], row["center_xy_px"])):
            image = overlay.copy()
            if center is not None and 0 <= center[0] < width and 0 <= center[1] < height:
                cv2.drawMarker(image, tuple(map(round, center)), (240, 80, 240),
                               cv2.MARKER_CROSS, 23, 2, cv2.LINE_AA)
            canvas[HEADER_HEIGHT:, panel * width:(panel + 1) * width] = image
    changed = row["selected_candidate_index"] != row["baseline_candidate_index"]
    training = row.get("is_training_frame", row.get("training_frame", False))
    for panel, (title, center, selected) in enumerate((
            ("BASELINE / NATIVE MASS", row["baseline_center_xy_px"], row["baseline_candidate_index"]),
            ("MOTION / CACHED 0.3", row["center_xy_px"], row["selected_candidate_index"]))):
        state = "WITHHELD" if withheld else "OBSERVED" if center is not None else "MISSING"
        if center is not None and not (0 <= center[0] < width and 0 <= center[1] < height):
            state += " / OUTSIDE IMAGE"
        lines = [f"{title} | FRAME {row['frame_index']} | {state}",
                 f"Source time {row['frame_index'] / source['fps']:.2f}s | candidate {selected} | changed: {changed}",
                 ("SEALED HOLDOUT + BUFFER: source pixels omitted" if withheld else
                  f"Magenta: selected ball | White: player IDs (display only) | training frame: {training}"),
                 "Unlabeled visual comparison; missing is not proof of occlusion.",
                 "Human review pending | no interpolation or connecting trails"]
        for line_index, text in enumerate(lines):
            text_width = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, .66, 1)[0][0]
            scale = .66 * min(1.0, (width - 28) / max(1, text_width))
            cv2.putText(canvas, text, (panel * width + 14, 26 + line_index * 29),
                        cv2.FONT_HERSHEY_SIMPLEX, scale, (235, 235, 235), 1, cv2.LINE_AA)
    return canvas


def verify_video(path, rows, shape, fps, final_path):
    capture = cv2.VideoCapture(str(path))
    final = None
    try:
        if not capture.isOpened() or abs(capture.get(cv2.CAP_PROP_FPS) - fps) > .01:
            raise ValueError("Comparison playback rate differs from source")
        for row in rows:
            ok, image = capture.read()
            if not ok or image.shape != shape:
                raise ValueError("Comparison video frame count or dimensions differ")
            if row["state"] == "withheld" and int(image[HEADER_HEIGHT:].max()) > 3:
                raise ValueError("Protected comparison source areas are not black")
            final = image
        if capture.read()[0]:
            raise ValueError("Comparison video contains extra frames")
    finally:
        capture.release()
    if final is None or not cv2.imwrite(str(final_path), final):
        raise ValueError("Could not save decoded final comparison frame")
    return {"decoded_frames": len(rows), "final_frame_index": rows[-1]["frame_index"],
            "final_frame_decoded": True, "playback_fps": fps,
            "protected_frame_pairs_verified_black": sum(r["state"] == "withheld" for r in rows)}


def render_comparison(root, observation_config, possession, timeline, output_folder):
    """Render once; verify bound artifacts on resume and retain every attempt."""
    root, folder = Path(root).resolve(), Path(output_folder).resolve()
    repository_path(root, folder.relative_to(root).as_posix(), "data/outputs")
    validate_timeline(possession, timeline)
    source, settings = possession["source_video"], observation_config["rendering"]
    if settings["playback_fps"] != source["fps"] or not 0 <= settings["crf"] <= 51:
        raise ValueError("Comparison must use source-rate playback and a valid CRF")
    if source["height_px"] % 2 or source["width_px"] % 2:
        raise ValueError("H264 comparison requires even source dimensions")
    folder.mkdir(parents=True, exist_ok=True)
    write_once(folder / "review_timeline.json", timeline)
    identity = {"timeline": observation.binding(root, folder / "review_timeline.json"),
                "observation_config_sha256": canonical(observation_config), "possession": possession,
                "renderer_sha256": digest_file(Path(__file__)),
                "observation_helpers_sha256": digest_file(Path(observation.__file__)),
                "rendering": settings, "full_resolution_side_by_side": True}
    receipt_path = folder / "review.json"
    if receipt_path.exists():
        saved = read_json(receipt_path)
        if saved["identity"] != identity:
            raise ValueError("Completed comparison review identity differs")
        for artifact in [saved["video"], saved["decoded_final_frame"], *[s["image"] for s in saved["stills"]]]:
            bound_path(root, artifact)
        return saved
    attempt = folder / "render_attempts" / uuid.uuid4().hex
    attempt.mkdir(parents=True)
    write_once(attempt / "started.json", {"status": "started", "identity": identity})
    started = time.monotonic()
    outcome = {"status": "failed", "identity": identity}
    try:
        verify_source_video_contract(SourceVideo.from_mapping(source), root)
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            raise ValueError("ffmpeg is required for H264 comparison output")
        rows = timeline["frames"]
        changed = [r["frame_index"] for r in rows if r["selected_candidate_index"] != r["baseline_candidate_index"]]
        cues = [i for i in KNOWN_CUES.get(possession["possession_id"], [])
                if i < len(rows) and rows[i]["state"] != "withheld"]
        requested_stills = set(changed) | set(cues)
        target, final_path = attempt / "comparison.mp4", attempt / "final_frame.png"
        players = observation.load_player_display(root, possession)
        decoders = {a: [a, b] for a, b in possession["visible_segments"]}
        width, height = 2 * source["width_px"], source["height_px"] + HEADER_HEIGHT
        images, stills = None, []
        with (attempt / "ffmpeg.log").open("wb") as log:
            process = subprocess.Popen([ffmpeg, "-hide_banner", "-loglevel", "error", "-n", "-f", "rawvideo",
                "-pix_fmt", "bgr24", "-s", f"{width}x{height}", "-r", str(source["fps"]), "-i", "pipe:0",
                "-an", "-c:v", "libx264", "-threads", "2", "-crf", str(settings["crf"]),
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(target)], stdin=subprocess.PIPE, stderr=log)
            try:
                for row in rows:
                    index, pixels = row["frame_index"], None
                    if index in decoders:
                        if images is not None:
                            images.close()
                        images = iter(observation.decode_segment(root, possession, decoders[index]))
                    if row["state"] != "withheld":
                        if images is None:
                            raise ValueError("Visible comparison has no allowed source decoder")
                        actual, pixels = next(images)
                        if actual != index:
                            raise ValueError("Source/player/ball comparison is not synchronized")
                    elif images is not None:
                        images.close()
                        images = None
                    canvas = render_frame(pixels, row, source, players.get(index, []))
                    process.stdin.write(canvas.tobytes())
                    if index in requested_stills:
                        path = attempt / f"frame_{index:06d}.png"
                        if not cv2.imwrite(str(path), canvas):
                            raise ValueError("Could not save comparison still")
                        stills.append({"frame_index": index, "changed": index in changed,
                                       "known_cue": index in cues, "image": observation.binding(root, path)})
                process.stdin.close()
                if process.wait(timeout=60) != 0:
                    raise ValueError("Comparison encoding failed; attempt and log preserved")
            finally:
                if images is not None:
                    images.close()
                if process.stdin and not process.stdin.closed:
                    try:
                        process.stdin.close()
                    except OSError:
                        pass
                if process.poll() is None:
                    process.kill()
                    process.wait()
        verified = verify_video(target, rows, (height, width, 3), source["fps"], final_path)
        if [s["frame_index"] for s in stills] != sorted(requested_stills):
            raise ValueError("Comparison still inventory is incomplete")
        receipt = {"schema_version": "wasb_motion_visual_comparison/v0.1", "identity": identity,
                   "video": observation.binding(root, target),
                   "decoded_final_frame": observation.binding(root, final_path),
                   "stills": stills, "changed_frame_indices": changed, "known_cue_frame_indices": cues,
                   "verification": verified, "human_visual_review": "pending", "selected_operating_point": None}
        write_once(receipt_path, receipt)
        outcome.update(status="completed", review=observation.binding(root, receipt_path))
        return receipt
    except BaseException as error:
        outcome.update(error=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
        raise
    finally:
        outcome["wall_seconds"] = time.monotonic() - started
        write_once(attempt / "completed.json", outcome)
