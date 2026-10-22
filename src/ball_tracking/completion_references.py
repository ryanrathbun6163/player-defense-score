"""Source-only review delivery for pending completion-campaign references.

This module validates and renders existing AI proposals. It neither generates
centers nor accepts labels, scores predictions, fits models or opens holdouts.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess

import cv2
import numpy as np

from .annotations import FrameAnnotation, SourceVideo


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def binding(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    with path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    return {"path": path.relative_to(root).as_posix(), "sha256": digest,
            "bytes": path.stat().st_size}


def write_new(path, data):
    with Path(path).open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def guard_range(config, possession, accepted):
    """Reject protected or already accepted frames before reading image pixels."""
    start, end = config["range_inclusive"]
    if (type(start) is not int or type(end) is not int or start < 0
            or end < start or end >= possession["source_video"]["frame_count"]):
        raise ValueError("Invalid proposal range")
    if any(max(start, lo) <= min(end, hi)
           for lo, hi in possession["protected_ranges"]):
        raise ValueError("Proposal intersects a protected range")
    if not any(lo <= start <= end <= hi for lo, hi in possession["visible_segments"]):
        raise ValueError("Proposal is not wholly inside one permitted segment")
    if any((config["possession_id"], index) in accepted for index in range(start, end + 1)):
        raise ValueError("Proposal would relabel an accepted reference")
    if (config["training_eligible"] is not False
            or config["checkpoint_selection_eligible"] is not False
            or config["human_acceptance"] != "pending"
            or config["role"] != "post_selection_evaluation_only"):
        raise ValueError("New curated references must remain pending evaluation-only proposals")
    return list(range(start, end + 1))


def presentation_timeline(probe, expected_count):
    """Packet decode order can differ from presentation order; preserve native ticks."""
    time_base = probe["streams"][0]["time_base"]
    unit = Fraction(time_base)
    packets = sorted(probe["packets"], key=lambda row: row["pts"])
    if len(packets) != expected_count or len({row["pts"] for row in packets}) != expected_count:
        raise ValueError("Packet presentation census is incomplete or duplicated")
    origin = packets[0]["pts"]
    result = []
    for index, packet in enumerate(packets):
        pts, duration = packet["pts"], packet["duration"]
        if type(pts) is not int or type(duration) is not int or duration <= 0:
            raise ValueError("Invalid native presentation timing")
        if index + 1 < len(packets) and pts + duration != packets[index + 1]["pts"]:
            raise ValueError("Non-contiguous native presentation timing")
        result.append({"source_frame_index": index, "native_pts_ticks": pts,
                       "native_duration_ticks": duration, "native_time_base": time_base,
                       "native_pts_seconds": float(pts * unit),
                       "clip_relative_seconds": float((pts - origin) * unit)})
    return result


def accepted_inventory(root, config):
    accepted = {}
    bindings = []
    for path in sorted((root / config["accepted_curated_directory"]).glob("*.json")):
        doc = read_json(path)
        if doc["review"]["status"] != "reviewed":
            continue
        bindings.append(binding(root, path))
        for row in doc["annotations"]:
            key = (doc["possession_id"], row["frame_index"])
            if key in accepted and accepted[key] != row:
                raise ValueError("Conflicting accepted rows")
            accepted[key] = row
    gap_path = root / config["accepted_gap_reference"]["path"]
    gap_binding = binding(root, gap_path)
    if gap_binding["sha256"] != config["accepted_gap_reference"]["sha256"]:
        raise ValueError("Accepted gap-reference hash changed")
    gap = read_json(gap_path)
    if gap["status"] != "human_accepted_assisted_reference":
        raise ValueError("Gap reference has not been accepted")
    bindings.append(gap_binding)
    for item in gap["new_annotations"]:
        if not item["continuous_source_id"].startswith("possession_"):
            continue
        key = (item["continuous_source_id"], item["source_frame_index"])
        if key in accepted and accepted[key] != item["annotation"]:
            raise ValueError("Conflicting accepted gap row")
        accepted[key] = item["annotation"]
    return accepted, bindings


def validate_batch(root, config_path, proposal_path):
    root = Path(root).resolve()
    config = read_json(config_path)
    source_contract = read_json(root / config["source_contract"])
    possession = next(p for p in source_contract["possessions"]
                      if p["possession_id"] == config["possession_id"])
    accepted, accepted_bindings = accepted_inventory(root, config)
    indices = guard_range(config, possession, accepted)
    source = possession["source_video"]
    source_binding = binding(root, root / source["path"])
    if source_binding["sha256"] != source["sha256"]:
        raise ValueError("Source video hash changed")
    folder = root / config["output_root"]
    probe = read_json(folder / "source_packet_timing.json")
    if (probe["streams"][0]["width"], probe["streams"][0]["height"]) != (source["width_px"], source["height_px"]):
        raise ValueError("Source timing dimensions differ")
    timeline = presentation_timeline(probe, source["frame_count"])
    source_frames = read_json(folder / "source_frames.json")
    if [row["frame_index"] for row in source_frames] != indices:
        raise ValueError("Source-frame census differs")
    proposal = read_json(proposal_path)
    if (proposal["status"] != "assistant_proposal_pending_human_acceptance"
            or proposal["annotation_origin"] != "assistant_visual_proposal"
            or proposal["human_acceptance"] is not None
            or proposal["training_eligible"] is not False
            or proposal["checkpoint_selection_eligible"] is not False
            or proposal["possession_id"] != config["possession_id"]
            or proposal["batch_id"] != config["batch_id"]):
        raise ValueError("Proposal identity, role, authorship or acceptance differs")
    rows = proposal["annotations"]
    if [row["frame_index"] for row in rows] != indices:
        raise ValueError("Annotation census differs")
    bounds = SourceVideo.from_mapping(source)
    for position, (frame, row) in enumerate(zip(source_frames, rows)):
        parsed = FrameAnnotation.from_mapping(row, position, bounds)
        if parsed.annotation_status != "labeled":
            raise ValueError("Reference batch contains incomplete labels")
        if binding(root, root / frame["path"])["sha256"] != frame["sha256"]:
            raise ValueError("Source PNG hash changed")
    frames = [{**timing, "source_png": png, "annotation": row}
              for timing, png, row in zip((timeline[i] for i in indices), source_frames, rows)]
    return config, {"schema_version": "completion_reference_review/v0.1",
                    "batch_id": config["batch_id"], "status": proposal["status"],
                    "config": binding(root, Path(config_path).resolve()),
                    "proposal": binding(root, Path(proposal_path).resolve()),
                    "source_video": source_binding, "source_metadata": source,
                    "source_timing": binding(root, folder / "source_packet_timing.json"),
                    "accepted_references_preserved": accepted_bindings,
                    "accepted_curated_rows": len(accepted),
                    "range_inclusive": config["range_inclusive"],
                    "protected_ranges": possession["protected_ranges"],
                    "annotation_origin": proposal["annotation_origin"],
                    "annotator_id": proposal["annotator_id"], "human_acceptance": None,
                    "training_eligible": False, "checkpoint_selection_eligible": False,
                    "counts": dict(Counter(row["visibility"] for row in rows)),
                    "frames": frames}


def render_frame(frame, item, count, possession_id, final_index):
    """Complete source context plus current-frame magnification; no track interpolation."""
    canvas = np.zeros((720, 1280, 3), dtype=np.uint8)
    canvas[:540, :960] = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)
    annotation = item["annotation"]
    geometry = annotation["geometry"]
    if geometry is not None:
        x, y = geometry["center_xy_px"]
        cv2.drawMarker(canvas, (round(x * 960 / frame.shape[1]), round(y * 540 / frame.shape[0])), (0, 255, 255),
                       cv2.MARKER_CROSS, 15, 1)
        cx, cy = round(x), round(y)
        x0 = min(max(0, cx - 60), frame.shape[1] - 120)
        y0 = min(max(0, cy - 60), frame.shape[0] - 120)
        crop = cv2.resize(frame[y0:y0 + 120, x0:x0 + 120], (300, 300), interpolation=cv2.INTER_NEAREST)
        point = (round((x - x0) * 2.5), round((y - y0) * 2.5))
        cv2.drawMarker(crop, point, (0, 255, 255), cv2.MARKER_CROSS, 22, 1)
        cv2.circle(crop, point, round(geometry["uncertainty_radius_px"] * 2.5), (0, 255, 255), 1)
        canvas[40:340, 970:1270] = crop
    lines = [f"{possession_id} - AI references, Ryan acceptance pending",
             f"Source frame {item['source_frame_index']} | native PTS {item['native_pts_ticks']} x {item['native_time_base']} sec",
             f"{annotation['visibility']} | complete-ball center {geometry['center_xy_px'] if geometry else 'UNKNOWN'}",
             f"Uncertainty: {geometry['uncertainty_radius_px'] if geometry else 'n/a'} source px | evaluation only; no fitting",
             f"Review EVERY frame (batch has {count}); final source frame is {final_index}."]
    for index, line in enumerate(lines):
        cv2.putText(canvas, line, (20, 572 + index * 29), cv2.FONT_HERSHEY_SIMPLEX,
                    .65, (235, 235, 235), 1, cv2.LINE_AA)
    return canvas


def render(root, config_path, proposal_path, destination):
    root = Path(root).resolve()
    config, manifest = validate_batch(root, config_path, proposal_path)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    frames = manifest["frames"]
    native_fps = config["review"]["native_playback_fps"]
    if any(Fraction(item["native_duration_ticks"]) * Fraction(item["native_time_base"])
           != Fraction(1, native_fps) for item in frames):
        raise ValueError("Configured playback would change native source timing")
    context = (len(frames), config["possession_id"], frames[-1]["source_frame_index"])
    videos = []
    for name, fps in (("review_native.mp4", config["review"]["native_playback_fps"]),
                      ("review_slow.mp4", config["review"]["slow_playback_fps"])):
        path = destination / name
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-n", "-f", "rawvideo",
                   "-pix_fmt", "bgr24", "-s", "1280x720", "-r", str(fps), "-i", "-",
                   "-an", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                   "-movflags", "+faststart", str(path)]
        with (destination / (name + ".log")).open("wb") as log:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
            try:
                for item in frames:
                    frame = cv2.imread(str(root / item["source_png"]["path"]))
                    canvas = render_frame(frame, item, *context)
                    process.stdin.write(canvas.tobytes())
                process.stdin.close()
                if process.wait() != 0:
                    raise ValueError("Reference video encoding failed")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
        capture = cv2.VideoCapture(str(path))
        errors = []
        marker_errors = []
        try:
            for item in frames:
                ok, actual = capture.read()
                if not ok or actual.shape != (720, 1280, 3):
                    raise ValueError("Reference video frame census/dimensions differ")
                expected = render_frame(cv2.imread(str(root / item["source_png"]["path"])), item, *context)
                # Full-image mean error verifies the actual emitted record/media join.
                error = float(np.abs(actual.astype(np.int16) - expected.astype(np.int16)).mean())
                errors.append(error)
                if error > 8:
                    raise ValueError("Reference video does not match its source/label record")
                # Whole-frame differences can hide a tiny shifted marker. Check
                # its yellow pixels separately in the magnified current-frame ROI.
                expected_crop, actual_crop = expected[40:340, 970:1270], actual[40:340, 970:1270]
                marker = np.all(expected_crop == (0, 255, 255), axis=2)
                if item["annotation"]["geometry"] is not None:
                    if int(marker.sum()) < 20:
                        raise ValueError("Expected label marker is absent")
                    marker_error = float(np.abs(actual_crop.astype(np.int16)[marker]
                                                - expected_crop.astype(np.int16)[marker]).mean())
                    marker_errors.append(marker_error)
                    if marker_error > 65:
                        raise ValueError("Encoded label marker does not match its record")
            if capture.read()[0]:
                raise ValueError("Unexpected additional reference video frame")
            if abs(capture.get(cv2.CAP_PROP_FPS) - fps) > .01:
                raise ValueError("Reference playback frame rate differs")
            final_path = destination / (name.replace(".mp4", "_actual_final.png"))
            cv2.imwrite(str(final_path), actual)
        finally:
            capture.release()
        videos.append({**binding(root, path), "frame_count": len(frames), "fps": fps,
                       "duration_seconds": len(frames) / fps, "actual_final": binding(root, final_path),
                       "all_frame_mean_absolute_pixel_errors": errors,
                       "all_frame_label_marker_pixel_errors": marker_errors})
    manifest["videos"] = videos
    manifest["validation"] = {"all_source_png_hashes_checked": True,
                              "actual_emitted_video_frames_checked": len(frames) * len(videos),
                              "human_visual_acceptance": "pending"}
    write_new(destination / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path.cwd()
    if args.output:
        result = render(root, args.config, args.proposal, args.output)
    else:
        _, result = validate_batch(root, args.config, args.proposal)
    print(json.dumps({"status": result["status"], "frame_count": len(result["frames"]),
                      "counts": result["counts"], "accepted_curated_rows": result["accepted_curated_rows"]}))


if __name__ == "__main__":
    main()
