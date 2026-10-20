"""Paired saved-source review of immutable temporal-gap trial decisions."""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path
import re
import subprocess
import time
import uuid

import numpy as np
from PIL import Image, ImageDraw

from . import nba_adaptation_comparison as paired
from . import nba_action_review as review
from . import nba_wasb_diagnostic as d
from . import wasb_experiment as wasb

SCHEMA = "nba_temporal_gap_review/v0.1"
GROUPS = {"sac_training_fit": (300, 3, 30), "det_development": (340, 3, 30),
          "nfhs_development": (150, 6, 6)}
TITLES = ("ORIGINAL mean selection", "TEMPORAL gap repair")


def join_entries(source_rows, decisions, scored_rows):
    """Bind display data to saved decisions without selecting or rescoring."""
    key = lambda row: (row["window_id"], row["source_frame_index"])
    indexed = {key(row): row for row in source_rows}
    selected = {key(row): row for row in decisions}
    scored = {key(row): row for row in scored_rows}
    d.require(len(indexed) == len(source_rows) == len(selected) == len(decisions)
              == len(scored) == len(scored_rows) and indexed.keys() == selected.keys() == scored.keys(),
              "Review frame coverage differs")
    result = []
    for row in source_rows:
        choice, score = selected[key(row)], scored[key(row)]
        frame, original = row["source_frame"], row["old"]["original_selected"]
        d.require(frame["source_frame_index"] == row["source_frame_index"]
                  and choice["candidate_id"] == row["candidate_id"]
                  and choice["source_pts_ticks"] == frame["source_pts_ticks"]
                  and choice["baseline_center_xy_px"] == original["center_xy_px"]
                  and choice["original_selected"] == original, "Review decision/source join differs")
        for field in ("candidate_id", "source_frame", "source_video", "annotation", "analysis_group", "cohort", "is_control"):
            d.require(score[field] == row[field], "Scored display source/reference differs")
        d.require(score["decision"] == choice, "Scored decision differs")
        center = choice["selected_center_xy_px"]
        changed = center != original["center_xy_px"]
        d.require(score["changed"] == changed, "Recorded change status differs")
        d.require(choice["decision"] in {"preserved_original", "abstained", "filled_saved_candidate"},
                  "Unknown selector decision")
        if choice["decision"] == "preserved_original":
            d.require(original["center_xy_px"] is not None and not changed, "Original prediction changed")
        elif choice["decision"] == "abstained":
            d.require(original["center_xy_px"] is None and center is None, "Abstention changed a prediction")
        else:
            d.require(original["center_xy_px"] is None and center is not None, "Gap fill replaced an original point")
        if center is not None:
            records = row["old"]["pool"]["records"]
            index = choice["selected_pool_record_index"]
            d.require(type(index) is int and 0 <= index < len(records), "Selected pool index differs")
            record = records[index]
            d.require(choice["selected_component"] == record["component"]
                      and choice["selected_native_score"] == record["component"]["native_score"]
                      and choice["selected_provenance_id"] == record["provenance_id"]
                      and center == [record["component"]["center_x"], record["component"]["center_y"]],
                      "Selected saved component differs")
        d.require(row["annotation"]["frame_index"] == frame["source_frame_index"], "Display annotation join differs")
        result.append({**{k: row[k] for k in ("window_id", "candidate_id", "analysis_group", "cohort", "is_control",
                                             "source_frame", "source_video", "annotation")},
            "original": original, "selected": {"state": "missing" if center is None else "observed", "center_xy_px": center},
            "decision_kind": "gap_fill" if changed else "unchanged", "decision": choice})
    return result


def load_inputs(root, scope_path, completion_path):
    root, scope_path, completion_path = Path(root).resolve(), Path(scope_path).resolve(), Path(completion_path).resolve()
    scope, completion = d.read_json(scope_path), d.read_json(completion_path)
    d.require(scope["schema_version"] == "nba_temporal_gap_selection_scope/v0.1"
              and scope["status"] == "approved" and scope["authorization"]["approved_by"] == "Ryan"
              and scope["policy"]["arm"] == "old",
              "Approved temporal-gap scope required")
    d.require(completion["schema_version"] == "nba_temporal_gap_selection/v0.1"
              and completion["status"] == "completed", "Completed selector trial required")
    bindings = completion["bindings"]
    d.require(paired.bound(root, bindings["scope"]) == scope_path, "Completion scope differs")
    for name in ("input_report", "pool_scope", "pre_execution_design"):
        d.require(bindings[name] == scope[name], "Completion input authority differs")
        paired.bound(root, bindings[name])
    for record in bindings["implementation"]: paired.bound(root, record)
    paired.bound(root, bindings["focused_tests"])
    original = d.read_json(paired.bound(root, scope["input_report"]))
    selection = d.read_json(paired.bound(root, completion["selection"]))
    report = d.read_json(paired.bound(root, completion["report"]))
    paired.bound(root, completion["summary"])
    d.require(selection["schema_version"] == report["schema_version"] == completion["schema_version"]
              and selection["bindings"] == report["bindings"] == bindings
              and report["selection"] == completion["selection"]
              and selection["labels_used"] is False, "Immutable selector artifact identity differs")
    entries = join_entries(original["frames"], selection["frames"], report["frames"])
    groups = {}
    expected = {(w["window_id"], index) for w in scope["windows"] for index in w["source_frame_indices"]}
    actual = {(r["window_id"], r["source_frame"]["source_frame_index"]) for r in entries}
    d.require(actual == expected and len(actual) == len(entries) == 790
              and len({(r["candidate_id"], r["source_frame"]["source_frame_index"]) for r in entries}) == 790,
              "Review must cover original 790 source frames exactly once")
    for group, (count, windows, fps) in GROUPS.items():
        order = {w["window_id"]: i for i, w in enumerate(scope["windows"]) if w["analysis_group"] == group}
        values = [r for r in entries if r["analysis_group"] == group]
        d.require(len(values) == count and {r["window_id"] for r in values} == order.keys()
                  and len(order) == windows, "Review group/window inventory differs")
        groups[group] = sorted(values, key=lambda r: (order[r["window_id"]], r["source_frame"]["source_frame_index"]))
        timeline(groups[group], fps)
    d.require(set(r["analysis_group"] for r in entries) == GROUPS.keys(), "Unknown review group")
    rendering = scope["rendering"]
    d.require(rendering["nba_fps"] == 30 and rendering["nfhs_fps"] == 6
              and rendering["final_hold_seconds"] == 1, "Frozen review pacing differs")
    output = d.contained(root, scope["output_root"])/"review"
    d.require(output.is_relative_to(root/"data/outputs"), "Review output must remain ignored")
    return {"groups": groups, "ffmpeg": rendering["ffmpeg"], "output": output,
            "bindings": {"scope": d.binding(root, scope_path), "selector_completion": d.binding(root, completion_path),
                         "input_report": scope["input_report"], "selection": completion["selection"], "report": completion["report"]}}


def header_text(item, record, fps):
    wid = item["window_id"]
    match = re.fullmatch(r"possession_(\d+)_frames_(\d+)_(\d+)_(representative|challenge)_evaluation_development_v0_2", wid)
    label = (f"P{match[1]} | {match[4]} | frames {int(match[2])}-{int(match[3])}"
             if match else wid.replace("_", " "))
    group = {"sac_training_fit": "SAC fitting", "det_development": "DET development",
             "nfhs_development": "NFHS development"}.get(item["analysis_group"], item["analysis_group"])
    reset = "NEW WINDOW / RESET" if record["window_start_reset"] else "within source window"
    frame = item["source_frame"]
    return (f"{group} | {label} | {reset}",
        f"Source frame {frame['source_frame_index']} | PTS {frame['source_pts_ticks']} / 90000"
        f" | {fps} fps review | Same retained checkpoint 09da1214e94f")


def timeline(entries, fps):
    """Each source appears once; every original window ends with an extra second."""
    d.require(fps in (6, 30) and entries, "Invalid review inventory")
    records, seen, previous, pts = [], set(), None, 0
    for index, item in enumerate(entries):
        wid, frame = item["window_id"], item["source_frame"]
        first = wid != previous
        if first:
            d.require(wid not in seen, "Review window must be contiguous")
            seen.add(wid)
        else:
            prior = entries[index-1]["source_frame"]
            d.require(frame["source_frame_index"] == prior["source_frame_index"]+1
                      and frame["source_pts_ticks"] > prior["source_pts_ticks"],
                      "Source discontinuity inside review window")
        last = index == len(entries)-1 or entries[index+1]["window_id"] != wid
        duration = 90000//fps + (90000 if last else 0)
        records.append({"review_index": index, "window_id": wid,
            "candidate_id": item["candidate_id"], "source_frame_index": frame["source_frame_index"],
            "source_pts_ticks": frame["source_pts_ticks"], "source_png": frame["png"],
            "review_pts_ticks": pts, "duration_ticks": duration,
            "window_start_reset": first, "window_final_hold": last,
            "decision_kind": item["decision_kind"]})
        previous, pts = wid, pts+duration
    return records


def overlay(root, item, record, fps):
    """Reuse source verification, point geometry and shared zoom; replace trial titles."""
    frame, original, selected = item["source_frame"], item["original"], item["selected"]
    manifest = {"candidate_id": item["candidate_id"], "source_video": item["source_video"]}
    label = item["annotation"]
    canvas = paired.paired_overlay(root, manifest, frame, original, selected,
        record["review_index"], {frame["source_frame_index"]: label}, fps)
    draw = ImageDraw.Draw(canvas)
    background = "#263c54" if record["window_start_reset"] else (15, 20, 29)
    draw.rectangle((0, 0, 1279, 83), fill=background)
    first_line, second_line = header_text(item, record, fps)
    d.require(draw.textlength(first_line, font=review.font(16)) <= 1256
              and draw.textlength(second_line, font=review.font(15)) <= 1256, "Review header clipped")
    draw.text((12, 3), first_line, fill="white", font=review.font(16))
    draw.text((12, 24), second_line, fill="white", font=review.font(15))
    statuses = ("MISSING" if original["center_xy_px"] is None else "OBSERVED",
                "GAP FILL" if item["decision_kind"] == "gap_fill" else
                "UNCHANGED MISSING" if selected["center_xy_px"] is None else "UNCHANGED OBSERVED")
    for panel, (title, status) in enumerate(zip(TITLES, statuses)):
        left = panel*640
        draw.text((left+12, 44), title, fill="#ffd380", font=review.font(20))
        draw.text((left+12, 68), status, fill="#ffd380", font=review.font(13))
        draw.rectangle((left, 447, left+639, 477), fill=(15, 20, 29))
        anchor = ("accepted label" if label.get("geometry") else "original point"
                  if original["center_xy_px"] else "gap-repair point"
                  if selected["center_xy_px"] else "image center")
        draw.text((left+12, 450), f"Shared zoom anchor: {anchor}", fill="#ffd380", font=review.font(16))
    draw.rectangle((0, 776, 1279, 807), fill=(15, 20, 29))
    ending = " | END WINDOW: +1s hold" if record["window_final_hold"] else ""
    draw.text((12, 782), "Pink: selected point | Cyan: accepted reference | Missing means unknown | No trails"
              + ending, fill="white", font=review.font(15))
    return canvas


def render_group(root, group, entries, fps, ffmpeg, output, bindings):
    """One video, external every-frame decode, per-window actual final screenshots."""
    import av
    records = timeline(entries, fps)
    identity = {"schema_version": SCHEMA, "group": group, "bindings": bindings,
        "entries_sha256": wasb.canonical(entries), "fps": fps, "window_hold_ticks": 90000,
        "panel_titles": list(TITLES), "renderer_sha256": d.digest(Path(__file__)),
        "shared_renderer_sha256": d.digest(Path(paired.__file__)),
        "source_reader_sha256": d.digest(Path(d.nba.__file__)),
        "key_and_font_sha256": d.digest(Path(review.__file__))}
    parent = output/group/"attempts"
    for path in sorted(parent.glob("*/completion.json")) if parent.exists() else []:
        saved = d.read_json(path)
        if saved["identity"] == identity:
            for record in saved["artifacts"].values(): paired.bound(root, record)
            for record in saved["window_final_frames"]: paired.bound(root, record["image"])
            return {**saved["artifacts"], "window_final_frames": saved["window_final_frames"],
                    "completion": d.binding(root, path)}
    folder = parent/uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=False)
    d.write_once(folder/"started.json", {"identity": identity, "at_utc": d.stamp()})
    began = time.monotonic()
    try:
        video = folder/"review.mp4"
        durations = {r["review_pts_ticks"]: r["duration_ticks"] for r in records}
        with av.open(str(video), "w", options={"movflags": "+faststart"}) as container:
            stream = container.add_stream("libx264", rate=fps,
                options={"crf": "18", "preset": "fast", "bf": "0"})
            stream.width, stream.height, stream.pix_fmt = 1280, 816, "yuv420p"
            stream.time_base = stream.codec_context.time_base = Fraction(1, 90000)
            stream.codec_context.thread_count = 2
            def mux(packets):
                for packet in packets:
                    d.require(packet.time_base == Fraction(1, 90000) and packet.pts in durations,
                              "Encoder PTS changed")
                    packet.duration = durations[packet.pts]
                    container.mux(packet)
            for item, record in zip(entries, records, strict=True):
                frame = av.VideoFrame.from_image(overlay(root, item, record, fps))
                frame.pts, frame.time_base = record["review_pts_ticks"], Fraction(1, 90000)
                mux(stream.encode(frame))
            mux(stream.encode())
        probe_binary = Path(ffmpeg).with_name("ffprobe.exe" if Path(ffmpeg).suffix.lower() == ".exe" else "ffprobe")
        probe_command = [str(probe_binary), "-v", "error", "-select_streams", "v:0", "-show_entries",
            "stream=time_base,duration_ts,nb_frames,width,height:frame=best_effort_timestamp,duration",
            "-of", "json", str(video)]
        probed = subprocess.run(probe_command, capture_output=True, check=False, timeout=180)
        (folder/"ffprobe.stderr.txt").write_bytes(probed.stderr)
        d.require(probed.returncode == 0, "Review probe failed")
        probe = json.loads(probed.stdout)
        d.write_once(folder/"ffprobe.json", probe)
        total = records[-1]["review_pts_ticks"]+records[-1]["duration_ticks"]
        d.require(len(probe["streams"]) == 1, "Unexpected video stream inventory")
        stream = probe["streams"][0]
        d.require(stream["time_base"] == "1/90000" and int(stream["duration_ts"]) == total
                  and (stream["width"], stream["height"]) == (1280, 816)
                  and int(stream["nb_frames"]) == len(records), "Encoded timeline differs")
        d.require([(int(r["best_effort_timestamp"]), int(r["duration"])) for r in probe["frames"]]
                  == [(r["review_pts_ticks"], r["duration_ticks"]) for r in records],
                  "Encoded frame timing differs")
        command = [str(ffmpeg), "-hide_banner", "-nostdin", "-loglevel", "error", "-xerror",
            "-threads", "2", "-i", str(video), "-map", "0:v:0", "-an", "-fps_mode", "passthrough",
            "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"]
        errors, finals = [], []
        with (folder/"decode.stderr.txt").open("xb") as stderr:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=stderr)
            try:
                for item, record in zip(entries, records, strict=True):
                    raw = bytearray()
                    while len(raw) < 1280*816*3:
                        chunk = process.stdout.read(1280*816*3-len(raw))
                        d.require(bool(chunk), "Missing decoded frame")
                        raw.extend(chunk)
                    decoded = np.frombuffer(raw, np.uint8).reshape(816, 1280, 3)
                    bits = "".join("1" if decoded[812, k*8+4].mean() > 127 else "0" for k in range(112))
                    d.require(bits == review.key_bits(record["review_index"], item["source_frame"]),
                              "Decoded source frame key differs")
                    expected = np.asarray(overlay(root, item, record, fps))
                    error = float(np.abs(decoded.astype(np.int16)-expected.astype(np.int16)).mean())
                    d.require(error < 8, "Decoded paired pixels differ")
                    errors.append(error)
                    if record["window_final_hold"]:
                        final = folder/f"window_final_{len(finals):02d}.png"
                        Image.fromarray(decoded).save(final)
                        finals.append({"window_id": item["window_id"], "review_index": record["review_index"],
                            "source_frame_index": record["source_frame_index"], "source_pts_ticks": record["source_pts_ticks"],
                            "overlay_mae": error, "image": d.binding(root, final)})
                d.require(process.stdout.read(1) == b"" and process.wait(timeout=60) == 0,
                          "Unexpected decoded frames or decoder failure")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)
                process.stdout.close()
        d.write_once(folder/"review_manifest.json", {"schema_version": SCHEMA, "identity": identity,
            "frames": records, "playback_fps": fps, "native_source_time_base": "1/90000",
            "review_time_base": "1/90000", "additional_window_final_hold_ticks": 90000,
            "source_frames_each_once": True, "continuity_between_windows_claimed": False,
            "human_review": "pending"})
        d.write_once(folder/"verification.json", {"status": "passed", "decoded_frames": len(errors),
            "all_source_keys_and_review_pts_verified": True, "all_source_png_and_rgb_hashes_verified": True,
            "all_paired_pixels_verified": True, "overlay_mae_max": max(errors),
            "actual_final_source_frame_index": records[-1]["source_frame_index"],
            "actual_final_frame_mae": errors[-1], "duration_ticks": total,
            "window_final_frames": finals, "probe_command": probe_command, "decode_command": command})
        artifacts = {key: d.binding(root, folder/name) for key, name in {
            "video": "review.mp4", "manifest": "review_manifest.json", "verification": "verification.json",
            "probe": "ffprobe.json", "final_frame": finals[-1]["image"]["path"].split("/")[-1]}.items()}
        d.write_once(folder/"completion.json", {"status": "completed", "identity": identity,
            "artifacts": artifacts, "window_final_frames": finals,
            "elapsed_seconds": time.monotonic()-began, "human_review": "pending"})
        return {**artifacts, "window_final_frames": finals, "completion": d.binding(root, folder/"completion.json")}
    except Exception as error:
        d.write_once(folder/"failed.json", {"status": "failed_preserved",
            "error_type": type(error).__name__, "error": str(error)})
        raise


def run(root, scope_path, completion_path):
    root = Path(root).resolve()
    context = load_inputs(root, scope_path, completion_path)
    output = context["output"]
    output.mkdir(parents=True, exist_ok=True)
    lock = d.acquire_run_lock(output/".run.lock")
    try:
        if (output/"completion.json").exists():
            saved = d.read_json(output/"completion.json")
            d.require(saved["bindings"] == context["bindings"]
                      and saved["renderer_sha256"] == d.digest(Path(__file__)), "Completed review identity differs")
            for group in saved["groups"].values():
                for name in ("video", "manifest", "verification", "probe", "final_frame", "completion"):
                    paired.bound(root, group[name])
                for final in group["window_final_frames"]: paired.bound(root, final["image"])
            return saved
        groups = {}
        for group, entries in context["groups"].items():
            print(f"Rendering {group}: {len(entries)} source frames", flush=True)
            groups[group] = render_group(root, group, entries, GROUPS[group][2],
                context["ffmpeg"], output, context["bindings"])
        result = {"schema_version": SCHEMA, "status": "completed", "bindings": context["bindings"],
            "renderer_sha256": d.digest(Path(__file__)), "groups": groups, "source_frames": 790,
            "windows": 12, "videos": 3, "new_model_calls": 0, "human_review": "pending",
            "player_ball_pipeline_milestone_claimed": False}
        d.write_once(output/"completion.json", result)
        return result
    finally:
        d.release_run_lock(lock)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--completion", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--check-inputs", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    if args.run:
        result = run(root, root/args.scope, root/args.completion)
    else:
        context = load_inputs(root, root/args.scope, root/args.completion)
        result = {"status": "verified_inputs", "frames_by_group": {k: len(v) for k, v in context["groups"].items()},
                  "bindings": context["bindings"], "pngs_decoded": 0, "model_calls": 0}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
