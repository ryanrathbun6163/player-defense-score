"""CPU-only native-cadence NBA comparisons from completed evaluation evidence.

Every canvas corresponds to one permitted prepared PNG. Source PTS and display
intervals are retained exactly, including the actual final frame. No nominal
frame rate, raw-video decode, inference, scoring or protected access is used.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import html
import io
import json
from pathlib import Path
import time
import traceback
import uuid

import cv2
import numpy as np
from PIL import Image

from . import completion_evaluation as evaluation_tools
from .completion_comparison_render import validate_evaluation
from .completion_evaluation_package import normalize_block
from .completion_sac_references import encode_review_video, probe_encoded_video, validate_encoded_timing
from .completion_training_runtime import atomic_write_once as write_once, binding
from .wasb_experiment import bound_path, canonical, read_json

WIDTH, HEIGHT, PANEL_W, PANEL_H, TOP, KEY_TOP = 1280, 720, 640, 360, 105, 704
COMPLETION = "data/outputs/ball_tracking/completion_campaign_v0_1/selected_comparison_v0_1/completed.json"
OUTPUT = "data/outputs/ball_tracking/completion_campaign_v0_1/selected_nba_comparison_review_v0_1"


def check(value, message):
    if not value:
        raise ValueError(message)


def timing_schedule(block):
    normalize_block(block)
    check(block["domain"] == "nba", "Only permitted NBA blocks may be rendered")
    frames = block["frames"]
    origin = frames[0]["source_pts_ticks"]
    return [(r["source_pts_ticks"] - origin, r["duration_ticks"]) for r in frames]


def read_block_records(root, package, evaluation, identity):
    """Check the actual immutable receipt -> record -> prepared-block transport."""
    by_hash = {canonical(b): b for b in package["inference_blocks"]}
    check(len(by_hash) == len(package["inference_blocks"]), "Duplicate inference blocks")
    records = {}
    check(len(evaluation["block_receipts"]) == len(by_hash), "Block receipt census differs")
    for entry in evaluation["block_receipts"]:
        receipt = read_json(bound_path(root, entry))
        check(receipt["identity"] == identity, "Block receipt method identity differs")
        block = by_hash.get(receipt["block_sha256"])
        check(block is not None and block["block_id"] not in records, "Stale or duplicate block receipt")
        record = read_json(bound_path(root, receipt["record"]))
        check(record["block_id"] == block["block_id"] and record["block_sha256"] == canonical(block),
              "Observation record block binding differs")
        evaluation_tools.validate_observations(block, record["observations"])
        records[block["block_id"]] = {"observations": record["observations"],
                                      "receipt": entry, "record": receipt["record"]}
    return records


def load_inputs(root, completion_binding):
    root = Path(root).resolve()
    completed = read_json(bound_path(root, completion_binding))
    check(completed.get("status") == "completed" and completed.get("protected_evaluation_authorized") is False,
          "Completed permitted evaluation required")
    identity = completed["identity"]
    for entry in identity["comparison_dependencies"] + identity["frozen_dependencies"]:
        bound_path(root, entry)
    evaluation = read_json(bound_path(root, completed["evaluation"]))
    package = read_json(bound_path(root, evaluation["package"]))
    validate_evaluation(package, evaluation, evaluation["package"])
    evaluation_tools.validate_package(package)
    check(evaluation["implementation"] == identity["implementation"]
          and identity["selected_package_sha256"] == canonical(package), "Evaluation identity/package differs")
    records = read_block_records(root, package, evaluation, identity)
    blocks = [b for b in package["inference_blocks"] if b["domain"] == "nba"]
    check(len(blocks) == 2 and {b["candidate_id"] for b in blocks} == {"sac_mem_q1_c01", "sas_det_q1_c02"}
          and sum(len(b["frames"]) for b in blocks) == 2702, "Fixed NBA action contexts differ")
    for block in blocks:
        timing_schedule(block)
    return blocks, records, {"completion": completion_binding, "evaluation": completed["evaluation"],
        "package": evaluation["package"], "selected_checkpoint": evaluation["selected_checkpoint"]}


def source_rgb(root, block, frame):
    check(block["domain"] == "nba" and frame["state"] == "permitted", "Protected source access prohibited")
    index = frame["source_frame_index"]
    check(not any(a <= index <= b for a, b in block.get("protected_ranges", [])), "Protected index prohibited")
    raw = bound_path(root, frame["png"]).read_bytes()
    with Image.open(io.BytesIO(raw)) as image:
        check(image.mode == "RGB", "Prepared source must be RGB")
        rgb = np.asarray(image).copy()
    source = block["source_video"]
    check(rgb.shape == (source["height_px"], source["width_px"], 3), "Native source dimensions differ")
    check(hashlib.sha256(rgb.tobytes()).hexdigest() == frame["png"]["rgb_sha256"], "Native RGB hash differs")
    return rgb


def frame_key(offset, frame):
    values = (offset, frame["source_frame_index"], frame["source_pts_ticks"])
    check(all(type(v) is int and 0 <= v < 2 ** bits for v, bits in zip(values, (32, 32, 64))),
          "Native frame identity exceeds encoded key")
    return f"{values[0]:032b}{values[1]:032b}{values[2]:064b}"


def canvas(rgb, block, frame, baseline, selected, offset):
    """Full source on both sides; one shared crop anchor does not alter labels."""
    source = block["source_video"]
    sw, sh = source["width_px"], source["height_px"]
    image = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    def text(value, x, y, color=(235, 235, 235), scale=.52):
        cv2.putText(image, value, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)
    def inside(point):
        return point is not None and 0 <= point[0] < sw and 0 <= point[1] < sh
    annotation = frame.get("annotation")
    geometry = None if annotation is None else annotation["geometry"]
    reference = None if geometry is None else geometry["center_xy_px"]
    anchor = next((p for p in (reference, selected["center_xy_px"], baseline["center_xy_px"]) if inside(p)), None)
    crop_size = min(128, sw, sh)
    ax, ay = anchor if anchor is not None else (sw / 2, sh / 2)
    left = min(max(0, int(ax - crop_size / 2)), sw - crop_size)
    top = min(max(0, int(ay - crop_size / 2)), sh - crop_size)
    text(f"{block['candidate_id']} | complete native action context | same frame on both sides", 12, 25, scale=.62)
    text(f"Native frame {frame['source_frame_index']} | PTS {frame['source_pts_ticks']} x {block['time_base']} | interval {frame['duration_ticks']} ticks", 12, 52)
    source_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    for column, observation in enumerate((baseline, selected)):
        x0 = column * PANEL_W
        color = (30, 150, 255) if column == 0 else (255, 210, 0)
        text("RETAINED BASELINE" if column == 0 else "SELECTED MODEL", x0 + 12, 90, color, .65)
        panel = cv2.resize(source_bgr, (PANEL_W, PANEL_H))
        crop = cv2.resize(source_bgr[top:top + crop_size, left:left + crop_size], (220, 220), interpolation=cv2.INTER_NEAREST)
        for point, point_color, marker in ((reference, (80, 255, 80), cv2.MARKER_TILTED_CROSS),
                                           (observation["center_xy_px"], color, cv2.MARKER_CROSS)):
            if inside(point):
                cv2.drawMarker(panel, (round(point[0] * PANEL_W / sw), round(point[1] * PANEL_H / sh)),
                               point_color, marker, 15, 2)
                if left <= point[0] < left + crop_size and top <= point[1] < top + crop_size:
                    cv2.drawMarker(crop, (round((point[0] - left) * 220 / crop_size), round((point[1] - top) * 220 / crop_size)),
                                   point_color, marker, 20, 2)
        image[TOP:TOP + PANEL_H, x0:x0 + PANEL_W] = panel
        image[480:700, x0 + 10:x0 + 230] = crop
        point = observation["center_xy_px"]
        text("MISSING" if point is None else f"Point ({point[0]:.1f}, {point[1]:.1f}) px", x0 + 245, 500, color)
        text(f"Native contributions: {observation['temporal_contributions']}", x0 + 245, 529)
        text("Reference: unlabeled" if annotation is None else f"Reference: {annotation['visibility']}", x0 + 245, 558)
        text("Reference center: unknown" if reference is None else f"Reference ({reference[0]:.1f}, {reference[1]:.1f})", x0 + 245, 587)
        text("Common crop: reference" if inside(reference) else "Common crop: model location" if anchor is not None else "Common crop: source center", x0 + 245, 616)
        text("Green: accepted reference", x0 + 245, 645, (80, 255, 80))
        text("Missing/unknown stay explicit", x0 + 245, 674)
    for i, bit in enumerate(frame_key(offset, frame)):
        image[KEY_TOP:HEIGHT, i * 10:(i + 1) * 10] = 255 if bit == "1" else 0
    return image


def render_block(root, block, selected, folder, provenance):
    root, folder = Path(root).resolve(), Path(folder).resolve()
    check(folder.is_relative_to(root / "data/outputs"), "Review output escaped data/outputs")
    schedule = timing_schedule(block)
    baseline = evaluation_tools.baseline_observations(block)
    evaluation_tools.validate_observations(block, selected)
    folder.mkdir(parents=True, exist_ok=False)
    began = time.perf_counter()
    implementation = binding(root, Path(__file__)) if Path(__file__).resolve().is_relative_to(root) else None
    write_once(folder / "started.json", {"block_sha256": canonical(block), "provenance": provenance,
                                         "implementation": implementation, "started_at_utc": evaluation_tools.stamp()})
    try:
        video = folder / "comparison.mp4"
        rows = block["frames"]
        def canvases():
            for offset, (frame, old, new) in enumerate(zip(rows, baseline, selected, strict=True)):
                yield canvas(source_rgb(root, block, frame), block, frame, old, new, offset)
        encoding = encode_review_video(video, canvases(), schedule, block["time_base"], "bt709", "bt709")
        probe = probe_encoded_video(video)
        checked = validate_encoded_timing(probe, schedule, block["time_base"], "bt709", "bt709")
        write_once(folder / "ffprobe.json", probe)
        capture = cv2.VideoCapture(str(video))
        errors, final = [], None
        try:
            for offset, (frame, old, new) in enumerate(zip(rows, baseline, selected, strict=True)):
                ok, final = capture.read()
                check(ok and final.shape == (HEIGHT, WIDTH, 3), "Encoded comparison ended before actual final frame")
                decoded_key = "".join("1" if float(final[KEY_TOP + 8, i * 10 + 5].mean()) > 127 else "0" for i in range(128))
                check(decoded_key == frame_key(offset, frame), "Decoded native frame key differs")
                expected = canvas(source_rgb(root, block, frame), block, frame, old, new, offset)
                error = float(np.abs(final.astype(np.int16) - expected.astype(np.int16)).mean())
                check(error < 8, "Decoded source/observation overlay differs")
                errors.append(error)
            check(not capture.read()[0], "Encoded comparison has unexpected extra frames")
        finally:
            capture.release()
        final_path = folder / "actual_final_frame.png"
        check(cv2.imwrite(str(final_path), final), "Actual final frame could not be saved")
        records = [{"source_frame_index": row["source_frame_index"], "source_pts_ticks": row["source_pts_ticks"],
            "duration_ticks": row["duration_ticks"], "time_base": block["time_base"], "source_png": row["png"],
            "annotation": row["annotation"], "reference_role": row["reference_role"], "baseline_observation": old,
            "selected_observation": new, **timing} for row, old, new, timing in zip(rows, baseline, selected, checked, strict=True)]
        write_once(folder / "frame_records.json", {"block_id": block["block_id"], "provenance": provenance, "frames": records})
        transported = read_json(folder / "frame_records.json")
        check(transported["frames"] == records, "Emitted frame record JSON differs")
        evaluation_tools.validate_observations(block, [r["baseline_observation"] for r in transported["frames"]])
        evaluation_tools.validate_observations(block, [r["selected_observation"] for r in transported["frames"]])
        result = {"candidate_id": block["candidate_id"], "block_id": block["block_id"], "block_sha256": canonical(block),
            "video": binding(root, video), "actual_final_frame": binding(root, final_path),
            "frame_records": binding(root, folder / "frame_records.json"), "encoded_probe": binding(root, folder / "ffprobe.json"),
            "provenance": provenance, "implementation": implementation, "encoding": encoding,
            "review_color_policy": "Prepared RGB unchanged; existing BT.601 limited-range review conversion and BT.709 output tags. Not a new source-transfer-metadata certification.",
            "decoded_frames": len(errors), "actual_final_native_frame": rows[-1]["source_frame_index"],
            "actual_final_source_pts_ticks": rows[-1]["source_pts_ticks"], "actual_final_duration_ticks": rows[-1]["duration_ticks"],
            "time_base": block["time_base"], "native_pts_packet_frame_duration_checks": len(checked),
            "total_duration_ticks": schedule[-1][0] + schedule[-1][1], "added_final_hold_ticks": 0,
            "all_frame_mean_absolute_errors": errors, "all_decoded_native_keys_verified": True,
            "elapsed_seconds": time.perf_counter() - began, "human_visual_acceptance": None,
            "model_calls": 0, "scoring_calls": 0, "source_video_decodes": 0, "protected_png_reads": 0}
        write_once(folder / "render_receipt.json", result)
        return result
    except BaseException as error:
        write_once(folder / "failed.json", {"error_type": type(error).__name__, "error": str(error),
            "traceback": traceback.format_exc(), "elapsed_seconds": time.perf_counter() - began})
        raise


def validate_completed(root, result, identity, blocks):
    """A saved completion remains reusable only while its nested media survive."""
    check(result["identity"] == identity and result["status"] == "completed", "Completed review identity changed")
    summary = read_json(bound_path(root, result["summary"]))
    bound_path(root, result["index"])
    check(summary["schema_version"] == "completion_nba_comparison_render/v0.1"
          and summary["status"] == "completed" and summary["identity"] == identity,
          "Review summary identity differs")
    expected = {b["candidate_id"]: b for b in blocks}
    rendered = {b["candidate_id"]: b for b in summary["blocks"]}
    check(len(rendered) == len(summary["blocks"]) == len(expected) and set(rendered) == set(expected)
          and summary["native_frames"] == sum(len(b["frames"]) for b in blocks), "Review context census differs")
    for candidate, block in expected.items():
        saved, final = rendered[candidate], block["frames"][-1]
        check(saved["block_id"] == block["block_id"] and saved["block_sha256"] == canonical(block)
              and saved["decoded_frames"] == saved["native_pts_packet_frame_duration_checks"] == len(block["frames"])
              and saved["actual_final_native_frame"] == final["source_frame_index"]
              and saved["actual_final_duration_ticks"] == final["duration_ticks"]
              and Fraction(saved["time_base"]) == Fraction(block["time_base"]), "Review native/final identity differs")
        for key in ("video", "actual_final_frame", "frame_records", "encoded_probe"):
            bound_path(root, saved[key])
    return result


def render_comparison(root, completion_binding, output_folder=OUTPUT, *, resume=False):
    root = Path(root).resolve()
    blocks, records, provenance = load_inputs(root, completion_binding)
    output = (root / output_folder).resolve()
    check(output.is_relative_to(root / "data/outputs") and output != root / "data/outputs", "Output escaped data/outputs")
    check(not output.exists() or resume, "Existing review requires explicit --resume; preserve old attempts")
    identity = {**provenance, "implementations": [binding(root, root / f"src/ball_tracking/{name}.py") for name in
        ("completion_nba_comparison_render", "completion_evaluation", "completion_evaluation_package", "completion_sac_references")],
        "native_presentation_timing": True, "protected_evaluation_authorized": False}
    output.mkdir(parents=True, exist_ok=True)
    from .wasb_training import training_lock
    with training_lock(output / "review.lock"):
        write_once(output / "identity.json", identity)
        if (output / "completed.json").exists():
            result = read_json(output / "completed.json")
            return validate_completed(root, result, identity, blocks)
        attempt = output / "attempts" / uuid.uuid4().hex
        attempt.mkdir(parents=True)
        began = time.perf_counter()
        write_once(attempt / "started.json", {"identity": identity, "started_at_utc": evaluation_tools.stamp()})
        try:
            results = []
            for block in blocks:
                record = records[block["block_id"]]
                results.append(render_block(root, block, record["observations"], attempt / block["candidate_id"],
                    {**provenance, "block_receipt": record["receipt"], "observation_record": record["record"]}))
                print(f"Verified native NBA review {block['candidate_id']}: {len(block['frames'])} frames", flush=True)
            summary = {"schema_version": "completion_nba_comparison_render/v0.1", "status": "completed",
                "identity": identity, "blocks": results, "native_frames": sum(r["decoded_frames"] for r in results),
                "human_visual_acceptance": None, "protected_evaluation_authorized": False}
            write_once(attempt / "summary.json", summary)
            sections = []
            for result in results:
                cid = html.escape(result["candidate_id"], quote=True)
                sections.append(f'<section><h2>{cid}</h2><video controls preload="metadata" src="{cid}/comparison.mp4"></video>'
                    f'<p>Final native frame {result["actual_final_native_frame"]} · <a href="{cid}/actual_final_frame.png">Actual final</a> · '
                    f'<a href="{cid}/frame_records.json">Every frame and timestamp</a></p></section>')
            (attempt / "index.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>NBA model comparison</title>'
                '<style>body{font:17px/1.5 system-ui;max-width:1400px;margin:32px auto;padding:0 20px}video{width:100%;background:black}section{margin:32px 0}</style>'
                '<h1>NBA retained baseline and selected model</h1><p>Two complete existing action contexts at exact native presentation timing, including the actual final interval. '
                'Orange: retained baseline; cyan: selected model; green: accepted reference where available. Unlabeled frames are not accuracy evidence. '
                'No points are filled. The same crop anchor is used on both sides. Human trajectory review is pending.</p>' + ''.join(sections) + '</html>', encoding="utf-8")
            result = {"identity": identity, "status": "completed", "summary": binding(root, attempt / "summary.json"),
                "index": binding(root, attempt / "index.html"), "elapsed_seconds": time.perf_counter() - began,
                "human_visual_acceptance": None}
            validate_completed(root, result, identity, blocks)
            write_once(output / "completed.json", result)
            write_once(attempt / "completed.json", {"completion": binding(root, output / "completed.json")})
            return result
        except BaseException as error:
            write_once(attempt / "failed.json", {"identity": identity, "error_type": type(error).__name__, "error": str(error),
                "traceback": traceback.format_exc(), "elapsed_seconds": time.perf_counter() - began, "retry_requires_resume": True})
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--completion", default=COMPLETION)
    parser.add_argument("--output-root", default=OUTPUT)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    completion = binding(root, root / args.completion)
    if args.run:
        print(json.dumps(render_comparison(root, completion, args.output_root, resume=args.resume)))
    else:
        blocks, _, provenance = load_inputs(root, completion)
        print(json.dumps({"status": "preflight_only_no_pixels", "blocks": [b["block_id"] for b in blocks], "provenance": provenance}))


if __name__ == "__main__":
    main()
