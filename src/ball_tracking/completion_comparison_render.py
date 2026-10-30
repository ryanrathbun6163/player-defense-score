"""CPU-only synchronized comparison from prepared permitted PNGs and scored rows.

No inference, source-video access or filled ball positions. Protected rows receive
black image panels. Rendering publishes to a new folder and preserves failures.
"""
from __future__ import annotations

import csv
from fractions import Fraction
import hashlib
import html
import json
from pathlib import Path
import subprocess
import time
import traceback

import cv2
import numpy as np
from PIL import Image

from .wasb_experiment import bound_path, read_json, write_once


WIDTH, HEIGHT, PANEL_W, PANEL_H, TOP = 1920, 740, 960, 540, 120


def check(value, message):
    if not value:
        raise ValueError(message)


def binding(root, path):
    path = Path(path).resolve()
    return {"path": path.relative_to(Path(root).resolve()).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}


def validate_timeline(timeline, comparison):
    frames = timeline["frames"]
    check(comparison["possession_id"] == timeline["possession_id"], "Comparison possession differs")
    check([r["source_frame_index"] for r in frames] == list(range(timeline["source_video"]["frame_count"])),
          "Complete source timeline required")
    time_base = Fraction(timeline["time_base"])
    maps = {}
    permitted = {r["source_frame_index"] for r in frames if r["state"] == "permitted"}
    for label in ("baseline", "selected"):
        observations = comparison[label + "_observations"]
        mapped = {r["source_frame_index"]: r for r in observations}
        check(len(mapped) == len(observations) and permitted <= set(mapped) <= set(range(len(frames))),
              "Observation frame join is incomplete or duplicated")
        metrics = comparison[label + "_metrics"]["frame_results"]
        scored = {r["source_frame_index"]: r for r in metrics}
        check(len(scored) == len(metrics) == len(frames) and set(scored) == set(range(len(frames))),
              "Scored timeline must cover every native frame")
        maps[label] = (mapped, scored)
    for i, row in enumerate(frames):
        check(type(row["source_pts_ticks"]) is int and type(row["duration_ticks"]) is int
              and Fraction(row["duration_ticks"]) * time_base == Fraction(1, 25),
              "Only exact native 25fps timing is supported; no resampling")
        if i:
            check(row["source_pts_ticks"] == frames[i - 1]["source_pts_ticks"] + frames[i - 1]["duration_ticks"],
                  "Native PTS sequence has a gap")
        withheld = any(a <= i <= b for a, b in timeline["protected_ranges"])
        check(row["state"] == ("withheld" if withheld else "permitted"), "Protected complement differs")
        if withheld:
            check(not any(row.get(k) is not None for k in ("png", "annotation", "baseline_observation")),
                  "Protected row carries source or label data")
        else:
            check(row.get("png") and row.get("annotation") and row["annotation"]["frame_index"] == i,
                  "Permitted source/annotation join missing")
        for observations, metrics in maps.values():
            observation = observations.get(i)
            score = metrics[i]
            check(score["source_pts_ticks"] == row["source_pts_ticks"]
                  and score["duration_ticks"] == row["duration_ticks"]
                  and Fraction(score["time_base"]) == time_base, "Scoring native timing differs")
            if observation is not None:
                check(observation["source_pts_ticks"] == row["source_pts_ticks"]
                      and Fraction(observation["time_base"]) == time_base, "Observation native timing differs")
                check("source_png" not in observation or observation["source_png"] == row.get("png"),
                      "Observation source image binding differs")
            if withheld:
                check(score["outcome"] == "withheld" and score.get("automatic_center_xy_px") is None
                      and not score.get("published_points"), "Protected score carries observations")
                check(observation is None or (observation["state"] == "withheld"
                      and observation.get("center_xy_px") is None
                      and observation.get("inference_status") == "withheld"
                      and observation.get("temporal_contributions") == 0
                      and observation.get("candidates") == []
                      and observation.get("mean_heatmap_sha256") is None
                      and observation.get("selected_candidate_index") is None
                      and observation.get("native_score") is None), "Protected observation carries inference or geometry")
                continue
            center = observation.get("center_xy_px")
            check(observation.get("inference_status") == score.get("inference_status") == "completed",
                  "Only completed inference may render; failure is not a missing point")
            check(observation["state"] == ("observed" if center is not None else "missing"),
                  "Observation state/geometry differs; no unavailable inference or fills")
            check(observation.get("point_origin", "automatic") == "automatic", "Only automatic observations may render")
            check(center is None or (len(center) == 2 and all(np.isfinite(x) for x in center)), "Invalid model center")
            check(score.get("automatic_center_xy_px") == center, "Scored point differs from rendered point")
    return maps


def read_players(root, timeline):
    allowed = {r["source_frame_index"] for r in timeline["frames"] if r["state"] == "permitted"}
    result = {}
    with bound_path(root, timeline["player_context"]).open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            index = int(row["frame_index"])
            if index not in allowed:
                continue
            frame = timeline["frames"][index]
            seconds = float((frame["source_pts_ticks"] - timeline["frames"][0]["source_pts_ticks"]) * Fraction(timeline["time_base"]))
            check(abs(float(row["timestamp_sec"]) - seconds) <= 1e-6, "Player/native timing differs")
            point = [float(row["floor_x"]), float(row["floor_y"])]
            check(all(np.isfinite(x) for x in point), "Invalid reviewed player point")
            result.setdefault(index, []).append({"player_id": row["player_id"], "floor_xy_px": point})
    return result


def source_rgb(root, timeline, row):
    if row["state"] == "withheld":
        return None
    with Image.open(bound_path(root, row["png"])) as source:
        check(source.mode == "RGB", "Prepared native image must be RGB")
        rgb = np.array(source)
    metadata = timeline["source_video"]
    check(rgb.shape == (metadata["height_px"], metadata["width_px"], 3), "Source dimensions differ")
    check(hashlib.sha256(rgb.tobytes()).hexdigest() == row["png"]["rgb_sha256"], "Native RGB binding differs")
    return rgb


def canvas(rgb, timeline, row, maps, players):
    image = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    index = row["source_frame_index"]
    withheld = row["state"] == "withheld"
    check((rgb is None) == withheld, "Withheld panel must receive no source pixels")
    check(not withheld or not players, "Protected frame must receive no player display")
    source = timeline["source_video"]
    sx, sy = PANEL_W / source["width_px"], PANEL_H / source["height_px"]
    def text(value, x, y, color=(235, 235, 235), scale=.65):
        cv2.putText(image, value, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)
    text(f"{timeline['possession_id']} | native frame {index} | PTS {row['source_pts_ticks']} x {timeline['time_base']}", 20, 32)
    text("Protected frame withheld" if withheld else "Same source frame | white: reviewed player IDs | green: accepted reference", 20, 64)
    for column, label in enumerate(("baseline", "selected")):
        x0 = column * PANEL_W
        text("RETAINED BASELINE" if label == "baseline" else "SELECTED MODEL", x0 + 20, 100)
        if withheld:
            text("WITHHELD - no source pixels, players, labels or model points", x0 + 20, 700)
            continue
        panel = cv2.resize(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), (PANEL_W, PANEL_H))
        def at(point):
            return (round(point[0] * sx), round(point[1] * sy))
        def inside(point):
            return 0 <= point[0] < source["width_px"] and 0 <= point[1] < source["height_px"]
        for player in players:
            if not inside(player["floor_xy_px"]):
                continue
            x, y = at(player["floor_xy_px"])
            cv2.circle(panel, (x, y), 3, (240, 240, 240), -1)
            cv2.putText(panel, str(player["player_id"]), (x + 5, y + 10), cv2.FONT_HERSHEY_SIMPLEX,
                        .45, (235, 235, 235), 1, cv2.LINE_AA)
        reference = row["annotation"]["geometry"]
        if reference and inside(reference["center_xy_px"]):
            point = at(reference["center_xy_px"])
            cv2.drawMarker(panel, point, (80, 255, 80), cv2.MARKER_TILTED_CROSS, 14, 2)
            cv2.circle(panel, point, max(2, round(reference["uncertainty_radius_px"] * sx)), (80, 255, 80), 1)
        observation, scored = maps[label][0][index], maps[label][1][index]
        center = observation["center_xy_px"]
        if center is not None and inside(center):
            cv2.drawMarker(panel, at(center), (255, 210, 0) if column else (30, 150, 255), cv2.MARKER_CROSS, 22, 2)
        image[TOP:TOP + PANEL_H, x0:x0 + PANEL_W] = panel
        coords = "missing" if center is None else f"({center[0]:.1f}, {center[1]:.1f}) source px"
        text(f"{coords} | {scored['outcome']}", x0 + 20, 690)
        geometry = "unknown center" if reference is None else f"reference {reference['center_xy_px']} +/-{reference['uncertainty_radius_px']:g}px"
        text(f"{row['annotation']['visibility']} | {geometry}", x0 + 20, 720, scale=.55)
    return image


def render_possession(root, timeline, comparison, folder):
    """Render and decode only the newly encoded comparison; never open raw video."""
    root, folder = Path(root).resolve(), Path(folder).resolve()
    check(folder.is_relative_to(root / "data/outputs"), "Review output must remain under data/outputs")
    maps = validate_timeline(timeline, comparison)
    players = read_players(root, timeline)
    folder.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    process = None
    try:
        video = folder / "comparison.mp4"
        with (folder / "ffmpeg.stderr.txt").open("wb") as errors:
            process = subprocess.Popen(["ffmpeg", "-v", "error", "-nostdin", "-n", "-f", "rawvideo", "-pix_fmt", "bgr24",
                "-s", f"{WIDTH}x{HEIGHT}", "-r", "25", "-i", "pipe:0", "-an", "-c:v", "libx264", "-threads", "2",
                "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)], stdin=subprocess.PIPE, stderr=errors)
            for row in timeline["frames"]:
                image = canvas(source_rgb(root, timeline, row), timeline, row, maps, players.get(row["source_frame_index"], []))
                process.stdin.write(image.tobytes())
            process.stdin.close()
            check(process.wait() == 0, "Comparison encoder failed; attempt preserved")
        capture = cv2.VideoCapture(str(video))
        errors, final = [], None
        try:
            check(abs(capture.get(cv2.CAP_PROP_FPS) - 25) < .001, "Encoded playback rate differs")
            for row in timeline["frames"]:
                ok, final = capture.read()
                check(ok and final.shape == (HEIGHT, WIDTH, 3), "Encoded timeline incomplete")
                expected = canvas(source_rgb(root, timeline, row), timeline, row, maps, players.get(row["source_frame_index"], []))
                error = float(np.abs(final.astype(np.int16) - expected.astype(np.int16)).mean())
                check(error < 8, "Encoded source/point frame comparison differs")
                if row["state"] == "withheld":
                    check(int(final[TOP + 8:TOP + PANEL_H - 8].max()) <= 4, "Protected image panel is not black")
                errors.append(error)
            check(not capture.read()[0], "Encoded timeline has extra frames")
        finally:
            capture.release()
        final_path = folder / "actual_final_frame.png"
        check(cv2.imwrite(str(final_path), final), "Could not save decoded actual final")
        write_once(folder / "frame_records.json", {"timeline": timeline, "comparison": comparison,
                   "reviewed_players_display_only": players, "no_inferred_fills": True})
        result = {"possession_id": timeline["possession_id"], "video": binding(root, video),
                  "actual_final_frame": binding(root, final_path), "actual_final_native_frame": timeline["frames"][-1]["source_frame_index"],
                  "frame_records": binding(root, folder / "frame_records.json"), "decoded_frames": len(errors),
                  "all_frame_mean_absolute_errors": errors, "native_fps": 25,
                  "permitted_frames": sum(r["state"] == "permitted" for r in timeline["frames"]),
                  "protected_black_frames": sum(r["state"] == "withheld" for r in timeline["frames"]),
                  "elapsed_seconds": time.perf_counter() - started, "human_visual_acceptance": None,
                  "source_video_decodes": 0, "protected_png_reads": 0, "model_calls": 0}
        write_once(folder / "render_receipt.json", result)
        return result
    except BaseException as error:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        write_once(folder / "failed.json", {"error": str(error), "traceback": traceback.format_exc(),
                   "elapsed_seconds": time.perf_counter() - started})
        raise


def validate_evaluation(package, evaluation, package_binding):
    check(package["schema_version"] == "completion_evaluation_package/v0.1", "Unsupported evaluation package")
    check(package.get("execution_ready") is True and package.get("selected_method"), "Selected evaluation package is not ready")
    check(evaluation.get("schema_version") == "completion_evaluation/v0.1" and evaluation.get("status") == "completed",
          "Completed evaluation evidence required")
    check(evaluation.get("package") == package_binding and
          evaluation.get("selected_checkpoint") == package["selected_method"]["checkpoint"], "Evaluation method/package binding differs")
    check(evaluation.get("protected_evaluation_authorized") is False, "Protected evaluation must remain closed")


def render_comparison(root, package_binding, evaluation_binding, output_folder):
    root = Path(root).resolve()
    package, evaluation = read_json(bound_path(root, package_binding)), read_json(bound_path(root, evaluation_binding))
    validate_evaluation(package, evaluation, package_binding)
    timelines = package["curated_timelines"]
    comparisons = {r["possession_id"]: r for r in evaluation["curated_comparisons"]}
    check(len(comparisons) == len(evaluation["curated_comparisons"]) == len(timelines) == 3, "Possession census differs")
    check(set(comparisons) == {t["possession_id"] for t in timelines} ==
          {"possession_001", "possession_002", "possession_003"}, "Unexpected possession identity")
    check(sum(len(t["frames"]) for t in timelines) == 1498 and
          sum(r["state"] == "permitted" for t in timelines for r in t["frames"]) == 1273, "Complete curated census required")
    output = (root / output_folder).resolve()
    check(output.is_relative_to(root / "data/outputs"), "Output escaped data/outputs")
    check(not output.exists(), "Preserve previous comparison output")
    results = [render_possession(root, t, comparisons[t["possession_id"]], output / t["possession_id"]) for t in timelines]
    summary = {"schema_version": "completion_comparison_render/v0.1", "package": package_binding,
               "evaluation": evaluation_binding, "implementation": binding(root, Path(__file__)),
               "possessions": results, "timeline_frames": 1498, "permitted_frames": 1273,
               "protected_black_frames": 225, "human_visual_acceptance": None}
    write_once(output / "summary.json", summary)
    sections = []
    for result in results:
        pid = html.escape(result["possession_id"], quote=True)
        sections.append(f'<section><h2>{pid}</h2><video controls preload="metadata" src="{pid}/comparison.mp4"></video>'
                        f'<p>Final native frame {result["actual_final_native_frame"]} · <a href="{pid}/actual_final_frame.png">Actual final</a> · '
                        f'<a href="{pid}/frame_records.json">All frame records</a></p></section>')
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Ball model comparison</title><style>body{font:17px/1.5 system-ui;max-width:1400px;margin:32px auto;padding:0 20px}video{width:100%;background:black}section{margin:32px 0}</style><h1>Retained baseline and selected model</h1><p>Same native frames and reviewed player context. Orange: baseline; cyan: selected; green: accepted reference and uncertainty. Missing points stay missing. All 1,273 permitted frames are shown; 225 protected positions have black image panels. Review through all three actual finals. Human acceptance is pending.</p>' + ''.join(sections) + '</html>'
    (output / "index.html").write_text(page, encoding="utf-8")
    return {"summary": binding(root, output / "summary.json"), "index": binding(root, output / "index.html")}
