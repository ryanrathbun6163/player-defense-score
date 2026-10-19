"""Render separate AI proposals from verified native PNGs; never edit human drafts."""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import math
import re
import shutil
import subprocess
import textwrap
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from PIL import Image, ImageDraw, ImageFont, ImageOps

from src.ball_tracking import nba_annotations as nba
from src.ball_tracking.annotations import FrameAnnotation

SCHEMA_VERSION = "nba_assisted_annotation_proposal/v0.1"
REQUIRED_FIELDS = {"schema_version", "candidate_id", "source_annotation_binding", "origin",
                   "annotations", "review_priority", "frame_inspections", "human_review"}
OPTIONAL_FIELDS = {"notes", "metadata"}
FRAME_SIZE = (1280, 720)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_json(raw: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError(f"Nonfinite JSON value: {value}")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def contained(root: Path, relative: str) -> Path:
    require(isinstance(relative, str) and bool(relative) and "\\" not in relative
            and ":" not in relative, "Expected portable relative path")
    value = PurePosixPath(relative)
    require(not value.is_absolute() and value.as_posix() == relative
            and all(part not in (".", "..") for part in value.parts), "Invalid relative path")
    result = (root / relative).resolve()
    require(result.is_relative_to(root.resolve()), "Path escapes repository")
    return result


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def binding(path: Path, root: Path) -> dict:
    raw = path.read_bytes()
    return {"path": path.relative_to(root).as_posix(), "bytes": len(raw), "sha256": digest(raw)}


def write_new(path: Path, data: dict) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), f"{label} must be nonempty text")


@dataclass(frozen=True)
class PixelBounds:
    width_px: int
    height_px: int


def validate_proposal(proposal: dict, original: dict, annotation_path: Path,
                      annotation_sha: str, root: Path) -> dict:
    require(isinstance(proposal, dict), "Proposal must be an object")
    require(REQUIRED_FIELDS <= set(proposal) <= REQUIRED_FIELDS | OPTIONAL_FIELDS,
            "Proposal has missing or unknown fields; put descriptive extras in metadata")
    require(proposal["schema_version"] == SCHEMA_VERSION, "Unsupported proposal schema")
    require(proposal["candidate_id"] == original["candidate_id"], "Candidate mismatch")
    source = proposal["source_annotation_binding"]
    require(isinstance(source, dict) and set(source) == {"path", "sha256"}, "Invalid source annotation binding")
    require(contained(root, source["path"]) == annotation_path.resolve()
            and source["sha256"] == annotation_sha, "Original annotation binding changed")
    origin = proposal["origin"]
    require(isinstance(origin, dict) and set(origin) == {
        "kind", "actor_id", "method", "detector_predictions_used", "interpolation_used", "created_at_utc"},
        "Invalid proposal origin fields")
    require(origin["kind"] == "assistant_visual_proposal"
            and origin["method"] == "direct_visual_inspection_of_native_rgb_pngs"
            and origin["detector_predictions_used"] is False
            and origin["interpolation_used"] is False, "Expected direct AI visual proposal without predictions/interpolation")
    text(origin["actor_id"], "origin.actor_id")
    text(origin["created_at_utc"], "origin.created_at_utc")
    stamp = datetime.fromisoformat(origin["created_at_utc"].replace("Z", "+00:00"))
    require(stamp.tzinfo is not None and stamp.utcoffset().total_seconds() == 0, "Origin timestamp must be UTC")
    require(proposal["human_review"] == {"status": "pending", "reviewer_id": None, "reviewed_at_utc": None},
            "Assisted proposals cannot assert human review")
    frames = original["frames"]
    indices = [frame["source_frame_index"] for frame in frames]
    raw_rows = proposal["annotations"]
    require(isinstance(raw_rows, list) and len(raw_rows) == len(frames), "Every source frame needs one proposal row")
    bounds = PixelBounds(original["source_video"]["width_px"], original["source_video"]["height_px"])
    rows = [FrameAnnotation.from_mapping(row, i, bounds).to_dict() for i, row in enumerate(raw_rows)]
    require([row["frame_index"] for row in rows] == indices, "Proposal must use exact ordered source frame inventory")
    inspections = proposal["frame_inspections"]
    require(isinstance(inspections, list) and len(inspections) == len(frames), "Every frame needs visual inspection provenance")
    evidence = {}
    for frame, inspection in zip(frames, inspections):
        require(isinstance(inspection, dict) and set(inspection) == {
            "frame_index", "source_png_sha256", "evidence_paths", "notes"}, "Invalid frame inspection fields")
        require(type(inspection["frame_index"]) is int
                and inspection["frame_index"] == frame["source_frame_index"]
                and inspection["source_png_sha256"] == frame["png"]["sha256"], "Inspection source frame/hash mismatch")
        text(inspection["notes"], "inspection.notes")
        paths = inspection["evidence_paths"]
        require(isinstance(paths, list) and bool(paths) and len(paths) == len(set(paths)), "Inspection needs distinct evidence paths")
        for name in paths:
            path = contained(root, name)
            require(path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".json"},
                    "Evidence must be an existing image or JSON; no source video reads")
            require(path.stat().st_size <= 64 * 1024 * 1024, "Evidence file exceeds bounded read")
            if name not in evidence:
                evidence[name] = binding(path, root)
    priorities = proposal["review_priority"]
    require(isinstance(priorities, list), "review_priority must be an array")
    priority_by_frame = {}
    for priority in priorities:
        require(isinstance(priority, dict) and set(priority) == {"frame_index", "reason"}, "Invalid review priority")
        index = priority["frame_index"]
        require(type(index) is int and index in indices and index not in priority_by_frame, "Invalid/duplicate priority frame")
        text(priority["reason"], "review priority reason")
        priority_by_frame[index] = priority["reason"]
    return {"rows": rows, "evidence": list(evidence.values()), "priority_by_frame": priority_by_frame}


def exceptions(row: dict, priority: str | None = None) -> list[str]:
    reasons = [priority] if priority else []
    if row["annotation_status"] != "labeled":
        reasons.append(row["annotation_status"])
    elif row["visibility"] != "fully_visible":
        reasons.append(row["visibility"])
    if row["game_ball_identity_certainty"] not in (None, "certain"):
        reasons.append("identity: " + row["game_ball_identity_certainty"])
    if row["geometry"] is None:
        reasons.append("no proposed point")
    if not row["localization_eligible"]:
        reasons.append("unscored proposal")
    return list(dict.fromkeys(reasons))


def font(size: int):
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def draw_point(draw, center, radius, color, scale=1.0):
    x, y = center
    length = max(5, 3 * scale)
    draw.line((x - length, y, x + length, y), fill=color, width=2)
    draw.line((x, y - length, x, y + length), fill=color, width=2)
    if radius > 0:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=color, width=2)


def render_frame(source: Image.Image, frame: dict, row: dict) -> tuple[Image.Image, dict]:
    canvas = Image.new("RGB", FRAME_SIZE, (15, 20, 29))
    draw = ImageDraw.Draw(canvas)
    small, normal, large = font(16), font(20), font(24)
    draw.text((16, 10), "AI PROPOSAL | HUMAN REVIEW PENDING", fill="#ffd380", font=large)
    ticks = frame["source_pts_ticks"]
    draw.text((16, 42), f"Source frame {frame['source_frame_index']} | PTS {ticks} x 1/90000 | {ticks / 90000:.9f}s", fill="white", font=normal)
    view = ImageOps.contain(source, (960, 540), Image.Resampling.LANCZOS)
    canvas.paste(view, (0, 78))
    sx, sy = view.width / source.width, view.height / source.height
    geometry = row["geometry"]
    crop_box = None
    color = "#00ffff"
    if geometry:
        x, y = geometry["center_xy_px"]
        radius = geometry["uncertainty_radius_px"]
        draw_point(draw, (x * sx, 78 + y * sy), radius * sx, color)
        crop_width = crop_height = min(128, source.width, source.height)
        left = min(max(0, math.floor(x - crop_width / 2)), source.width - crop_width)
        top = min(max(0, math.floor(y - crop_height / 2)), source.height - crop_height)
        crop_box = [left, top, left + crop_width, top + crop_height]
        zoom = source.crop(crop_box).resize((288, 288), Image.Resampling.NEAREST)
        canvas.paste(zoom, (976, 108))
        zx, zy = 288 / crop_width, 288 / crop_height
        # Crops are square for ordinary NBA source images, so uncertainty stays circular.
        draw_point(draw, (976 + (x - left) * zx, 108 + (y - top) * zy), radius * zx, color, zx)
        draw.text((976, 82), "Source crop + proposed point", fill="white", font=small)
        draw.text((976, 410), f"X {x:.3f}   Y {y:.3f}", fill="white", font=normal)
        draw.text((976, 438), f"Uncertainty {radius:.3f}px", fill="white", font=normal)
    else:
        draw.rectangle((976, 108, 1264, 396), outline="#e4b466", width=2)
        draw.text((1000, 225), "NO PROPOSED POINT", fill="#ffd380", font=normal)
    state = row["visibility"] or row["annotation_status"]
    eligibility = "ELIGIBLE PROPOSAL" if row["localization_eligible"] else "UNSCORED PROPOSAL"
    draw.text((16, 632), f"{state.upper()} | {eligibility} | identity: {row['game_ball_identity_certainty'] or 'unset'}", fill="#ffd380", font=normal)
    note = row["notes"] or "No extra notes. All labels remain AI proposals."
    for i, line in enumerate(textwrap.wrap(note, width=150)[:2]):
        draw.text((16, 665 + i * 21), line, fill="white", font=small)
    return canvas, {"source_view_rect": [0, 78, view.width, view.height], "source_crop_box": crop_box,
                    "point_source_pixels": geometry["center_xy_px"] if geometry else None,
                    "uncertainty_radius_source_pixels": geometry["uncertainty_radius_px"] if geometry else None}


def build_page(candidate: str, counts: dict, records: list[dict], fps: int) -> str:
    esc = html.escape
    priority = "".join(f"<tr><td>{r['source_frame_index']}</td><td>{esc('; '.join(r['exceptions']))}</td><td><a href='{esc(r['review_relative_path'])}'>Inspect frame</a></td></tr>"
                       for r in records if r["exceptions"])
    frames = "".join(f"<li><a href='{esc(r['review_relative_path'])}'>Frame {r['source_frame_index']} / {r['source_pts_ticks']} ticks</a></li>" for r in records)
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>{esc(candidate)} AI proposal</title>
<style>body{{background:#10151d;color:#edf2f8;font:16px system-ui;max-width:1100px;margin:auto;padding:24px}}a{{color:#85d8ff}}video{{width:100%}}table{{border-collapse:collapse;width:100%}}td,th{{text-align:left;padding:8px;border-bottom:1px solid #46556a}}.note{{color:#ffd380}}img{{max-width:48%}}</style>
<h1>{esc(candidate)} — AI proposal review</h1><p class="note">Human review pending. Original annotation drafts are unchanged.</p>
<p>{counts['frames']} source frames · {counts['with_point']} proposed points · {counts['eligible']} localization-eligible proposals · {counts['exception_frames']} frames flagged for attention.</p>
<video controls preload="metadata" src="review.mp4"></video><p>Slow review: {fps} source frames per second, then a one-second final-frame hold. Original source frame and PTS appear on every frame. Playback is not real-time timing evidence.</p>
<h2>Attention frames</h2><table><tr><th>Source frame</th><th>Reason</th><th>Evidence</th></tr>{priority or '<tr><td colspan="3">No exception flags. All frames still require human review.</td></tr>'}</table>
<p><a href="proposal.json">Separate AI proposal JSON</a> · <a href="review_manifest.json">Frame mapping and evidence manifest</a></p>
<p class="note">The inherited geometry token “human_amodal_estimate” describes a partial-ball center convention; this package's actual proposer is AI. No human label or review is claimed.</p>
<details><summary>Every source-frame overlay, including the final frame</summary><ol>{frames}</ol></details>
<h2>First and final source frames</h2><a href="{esc(records[0]['review_relative_path'])}"><img src="{esc(records[0]['review_relative_path'])}" alt="First source frame"></a> <a href="{esc(records[-1]['review_relative_path'])}"><img src="{esc(records[-1]['review_relative_path'])}" alt="Final source frame"></a></html>"""


def prepare_review(root: Path, annotation_path: Path, proposal_path: Path,
                   output_root: Path, ffmpeg: str, playback_fps: int = 6) -> dict:
    root, annotation_path, proposal_path = root.resolve(), annotation_path.resolve(), proposal_path.resolve()
    output_root = output_root.resolve()
    require(annotation_path.is_relative_to(root) and proposal_path.is_relative_to(root), "Inputs must be inside repository")
    require(output_root.is_relative_to(root / "data/outputs"), "Review output must be under data/outputs")
    require(type(playback_fps) is int and 1 <= playback_fps <= 30, "Playback fps must be 1..30")
    require(ffmpeg is not None and Path(ffmpeg).is_file(), "Pass the installed FFmpeg executable")
    original, annotation_sha = nba.load_annotation_snapshot(annotation_path, repo_root=root, verify_images=True)
    proposal_raw = proposal_path.read_bytes()
    proposal = read_json(proposal_raw)
    validated = validate_proposal(proposal, original, annotation_path, annotation_sha, root)
    candidate = original["candidate_id"]
    require(re.fullmatch(r"[a-z0-9][a-z0-9_-]*", candidate) is not None, "Invalid candidate ID")
    directory = output_root / candidate
    require(not directory.exists(), "Existing review preserved; choose a new output root")
    directory.mkdir(parents=True)
    (directory / "frames").mkdir()
    started = time.monotonic()
    write_new(directory / "started.json", {"status": "started", "source_annotation": binding(annotation_path, root),
              "proposal": binding(proposal_path, root),
              "code": {"path": "src/ball_tracking/prepare_nba_assisted_review.py",
                       "sha256": digest(Path(__file__).read_bytes())},
              "original_video_decodes": 0, "renderer_detector_model_calls": 0,
              "proposal_origin": "assistant_visual_proposal"})
    try:
        (directory / "proposal.json").write_bytes(proposal_raw)
        records = []
        for position, (frame, row) in enumerate(zip(original["frames"], validated["rows"])):
            raw = nba.read_verified_png(frame, original["source_video"], root)
            with Image.open(io.BytesIO(raw)) as image:
                composite, geometry = render_frame(image, frame, row)
            path = directory / "frames" / f"review_{position:06d}.png"
            composite.save(path)
            records.append({"review_index": position, "source_frame_index": frame["source_frame_index"],
                "source_pts_ticks": frame["source_pts_ticks"], "time_base": "1/90000",
                "source_png": frame["png"], "review_png": binding(path, root),
                "review_relative_path": path.relative_to(directory).as_posix(), "render_geometry": geometry,
                "exceptions": exceptions(row, validated["priority_by_frame"].get(row["frame_index"]))})
        command = [ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "warning", "-xerror", "-n",
                   "-framerate", str(playback_fps), "-start_number", "0", "-i", str(directory / "frames/review_%06d.png"),
                   "-an", "-vf", "tpad=stop_mode=clone:stop_duration=1", "-c:v", "libx264", "-threads", "2",
                   "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(directory / "review.mp4")]
        encode_start = time.monotonic()
        with (directory / "ffmpeg.stdout.txt").open("xb") as stdout, (directory / "ffmpeg.stderr.txt").open("xb") as stderr:
            result = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=120, check=False)
        require(result.returncode == 0, f"Review encode failed: {result.returncode}; retained logs")
        encode_seconds = round(time.monotonic() - encode_start, 6)
        counts = {"frames": len(records), "with_point": sum(r["geometry"] is not None for r in validated["rows"]),
                  "eligible": sum(r["localization_eligible"] for r in validated["rows"]),
                  "exception_frames": sum(bool(r["exceptions"]) for r in records),
                  "visibility": dict(Counter(r["visibility"] or r["annotation_status"] for r in validated["rows"]))}
        manifest = {"schema_version": "nba_assisted_review_manifest/v0.1", "candidate_id": candidate,
                    "origin": proposal["origin"], "human_review": proposal["human_review"],
                    "source_annotation_binding": proposal["source_annotation_binding"], "counts": counts,
                    "source_evidence": validated["evidence"], "frames": records,
                    "video": {"path": "review.mp4", "review_source_frames_per_second": playback_fps,
                              "final_frame_hold_seconds": 1, "expected_encoded_frames": len(records) + playback_fps,
                              "native_time_pacing": False, "interpolated_source_frames": 0,
                              "command": command, "encode_elapsed_seconds": encode_seconds},
                    "geometry_token_note": "human_amodal_estimate is inherited geometry terminology, not a human-origin claim."}
        write_new(directory / "review_manifest.json", manifest)
        (directory / "index.html").write_text(build_page(candidate, counts, records, playback_fps), encoding="utf-8")
        require(digest(annotation_path.read_bytes()) == annotation_sha, "Original draft changed during review preparation")
        require(proposal_path.read_bytes() == proposal_raw, "Input proposal changed during preparation")
        nba.verify_annotation_assets(original, root, verify_images=False)
        receipt = {"status": "prepared_pending_human_review", "candidate_id": candidate, "counts": counts,
                   "elapsed_seconds": round(time.monotonic() - started, 6), "human_labels_created": 0,
                   "original_annotations_modified": False, "original_video_decodes": 0,
                   "renderer_detector_model_calls": 0, "proposal_origin": "assistant_visual_proposal",
                   "final_source_frame_included": records[-1]["source_frame_index"],
                   "artifacts": [binding(directory / name, root) for name in
                                 ("proposal.json", "review_manifest.json", "review.mp4", "index.html", "ffmpeg.stderr.txt")]}
        write_new(directory / "preparation_receipt.json", receipt)
        return receipt
    except Exception as error:
        write_new(directory / "failed.json", {"status": "failed_preserved", "error_type": type(error).__name__,
                  "error": str(error), "elapsed_seconds": round(time.monotonic() - started, 6)})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", required=True, type=Path)
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--repository-root", default=Path.cwd(), type=Path)
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    parser.add_argument("--playback-fps", type=int, default=6)
    args = parser.parse_args()
    root = args.repository_root.resolve()
    print(json.dumps(prepare_review(root, root / args.annotations, root / args.proposal,
                                   root / args.output_root, args.ffmpeg, args.playback_fps)))


if __name__ == "__main__":
    main()
