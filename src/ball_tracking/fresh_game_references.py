"""Validate and render pending source-only fresh-game reference proposals.

No labels are generated or accepted. No predictions, model imports, fitting,
checkpoint selection, or source-video decoding occur. Native PNGs and the
preparer's bound presentation timeline are authoritative for this review.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import html
import json
import math
from pathlib import Path
import subprocess

import cv2
import numpy as np

from .annotations import FrameAnnotation, SourceVideo, _reject_duplicate_json_keys
from .completion_references import binding, write_new
from .completion_nba_references import render_frame, review_encoding_command


BASE = "data/outputs/ball_tracking/fresh_game_diagnostic_v0_1"
SELECTION = BASE + "/source_selection/selection.json"
ROLE = "diagnostic_development"
STATUS = "assistant_proposal_pending_human_acceptance"
PROPOSAL_FIELDS = frozenset(("schema_version", "clip_id", "game_id", "role",
    "annotation_origin", "annotator_id", "status", "human_acceptance",
    "training_eligible", "checkpoint_selection_eligible", "annotations", "inspection_evidence"))


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_json_keys)


def path_in(root, name):
    root = Path(root).resolve()
    path = (root / name).resolve()
    require(path.is_relative_to(root), "Path leaves the repository")
    return path


def checked(root, expected, label):
    require(isinstance(expected, dict) and {"path", "bytes", "sha256"} <= expected.keys(), label + " binding missing")
    actual = binding(root, path_in(root, expected["path"]))
    require(all(expected[k] == actual[k] for k in actual), label + " binding changed")
    return actual


def positive_fraction(value, label):
    try:
        result = Fraction(str(value))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError("Invalid " + label) from exc
    require(result > 0, "Invalid " + label)
    return result


def validate_proposal(proposal, selection):
    require(selection.get("schema_version") == "fresh_game_source_selection/v0.1"
            and selection.get("status") == "frozen_before_new_pixels_labels_and_predictions"
            and selection.get("training_eligible") is False
            and selection.get("checkpoint_selection_eligible") is False
            and selection.get("prediction_blind_labels") is True,
            "Fixed source selection schema/status or diagnostic eligibility differs")
    require(isinstance(proposal, dict) and set(proposal) == PROPOSAL_FIELDS, "Unexpected proposal fields")
    require(proposal["schema_version"] == "fresh_game_reference_proposal/v0.1", "Unexpected proposal schema")
    require(proposal["role"] == selection.get("role") == ROLE, "Fresh references require diagnostic_development role")
    require(proposal["game_id"] == selection["game_id"], "Proposal game differs from selected game")
    require(isinstance(proposal["clip_id"], str) and proposal["clip_id"]
            and len([c for c in selection["selected_clips"] if str(c["clip_id"]) == proposal["clip_id"]]) == 1,
            "Proposal clip absent or duplicated in source selection")
    selected = next(c for c in selection["selected_clips"] if str(c["clip_id"]) == proposal["clip_id"])
    require(selected.get("window_seconds_half_open") == [0, 2], "Fixed source window differs from this renderer")
    require(proposal["status"] == STATUS and proposal["annotation_origin"] == "assistant_visual_proposal"
            and proposal["human_acceptance"] is None and proposal["training_eligible"] is False
            and proposal["checkpoint_selection_eligible"] is False,
            "Proposal must remain pending and ineligible for training/checkpoint selection")
    require(isinstance(proposal["annotator_id"], str) and proposal["annotator_id"].strip(), "Annotator identity missing")
    require(isinstance(proposal["annotations"], list) and isinstance(proposal["inspection_evidence"], list)
            and proposal["inspection_evidence"], "Annotations and visual inspection evidence required")


def join_frames(preparation, frame_map, source_frames):
    """Derive the complete [0,2) second window from actual saved native PTS.

    Duration is the next native PTS difference. The selected window must have a
    following frame in the full source map, including for its final image.
    Average frame rate is checked, never used to invent selected timestamps.
    """
    rate = positive_fraction(preparation["average_rate"], "native frame rate")
    unit = positive_fraction(preparation["time_base"], "native time base")
    require(rate == 60, "This review recipe requires actual constant 60 fps")
    require(isinstance(frame_map, list) and len(frame_map) == preparation["decoded_frame_count"], "Full decoded frame census differs")
    require([r["source_frame_index"] for r in frame_map] == list(range(len(frame_map))), "Source frame map has a gap or duplicate")
    for row in frame_map:
        require(type(row["source_frame_index"]) is int and type(row["native_pts_ticks"]) is int,
                "Native frame indices and PTS must be integers")
        require(positive_fraction(row["native_time_base"], "frame time base") == unit, "Native frame time base differs")
        require(type(row["seconds"]) in (int, float) and math.isfinite(row["seconds"])
                and abs(row["seconds"] - float(row["native_pts_ticks"] * unit)) <= 1e-9,
                "Recorded seconds differ from native PTS")
    require(all(b["native_pts_ticks"] > a["native_pts_ticks"] for a, b in zip(frame_map, frame_map[1:])),
            "Source PTS are not strictly increasing")
    selected = [r for r in frame_map if 0 <= r["native_pts_ticks"] * unit < 2]
    require(selected and selected[0]["native_pts_ticks"] == 0 and selected[0]["source_frame_index"] == 0,
            "Selected source window does not begin at native time zero")
    require(len(selected) == preparation["selected_frame_count"] == len(source_frames), "Selected frame census differs")
    require(preparation["first_selected_frame"] == selected[0]["source_frame_index"]
            and preparation["last_selected_frame"] == selected[-1]["source_frame_index"], "Selected range differs")
    result = []
    for native, saved in zip(selected, source_frames, strict=True):
        require(all(saved.get(k) == native[k] and type(saved.get(k)) is type(native[k]) for k in native),
                "Source PNG lineage/PTS differs from full source timeline")
        index = native["source_frame_index"]
        require(index + 1 < len(frame_map), "Actual next-frame PTS needed for selected final duration")
        duration = frame_map[index + 1]["native_pts_ticks"] - native["native_pts_ticks"]
        require(duration * unit == 1 / rate, "Variable cadence cannot be silently resampled")
        result.append({**saved, "native_duration_ticks": duration,
                       "duration_authority": "next_native_frame_PTS_difference"})
    require((result[-1]["native_pts_ticks"] + result[-1]["native_duration_ticks"]) * unit == 2,
            "Selected display intervals do not exactly cover [0,2) seconds")
    require(len(result) == 120, "Native two-second 60 fps window has unexpected census")
    return result


def review_exceptions(frames):
    result = []
    for position, item in enumerate(frames):
        row, reasons = item["annotation"], []
        if row["geometry"] is None:
            reasons.append("unknown_center")
        else:
            # Every nonzero spatial uncertainty is disclosed, without choosing
            # a new numerical threshold for which references deserve review.
            reasons.append("spatial_uncertainty")
        if row["visibility"] != "fully_visible":
            reasons.append("visibility_" + row["visibility"])
        if row["game_ball_identity_certainty"] != "certain":
            reasons.append("identity_" + row["game_ball_identity_certainty"])
        if not row["localization_eligible"]:
            reasons.append("not_localization_eligible")
        if position == len(frames) - 1:
            reasons.append("actual_selected_final_frame")
        result.append({"source_frame_index": item["source_frame_index"], "reasons": reasons,
                       "annotation": row})
    return result


def validate(root, proposal_path, selection_path=SELECTION):
    root = Path(root).resolve()
    proposal_path, selection_path = path_in(root, proposal_path), path_in(root, selection_path)
    proposal, selection = read(proposal_path), read(selection_path)
    validate_proposal(proposal, selection)
    clip = proposal["clip_id"]
    folder = path_in(root, BASE + "/sources/" + clip)
    require(folder.parent == path_in(root, BASE + "/sources"), "Invalid clip path")
    preparation_path = folder / "preparation.json"
    preparation = read(preparation_path)
    selection_binding = binding(root, selection_path)
    require(preparation.get("status") == "source_only_extraction_complete" and preparation.get("model_calls") == 0,
            "Complete source-only preparation required")
    require(preparation.get("selection") == selection_binding and preparation.get("clip_id") == clip
            and preparation.get("game_id") == proposal["game_id"] and preparation.get("role") == ROLE,
            "Source preparation selection/role/clip lineage differs")
    clip_selection = next(c for c in selection["selected_clips"] if str(c["clip_id"]) == clip)
    expected_source = "data/raw/nba/fresh_game_diagnostic_v0_1/" + clip_selection["catalog_path"]
    require(preparation["source"]["path"] == expected_source, "Prepared video differs from fixed catalog selection")
    source_binding = checked(root, preparation["source"], "Source video")
    require(preparation["frames"]["path"] == (folder / "source_frames.json").relative_to(root).as_posix()
            and preparation["frame_map"]["path"] == (folder / "frame_map.json").relative_to(root).as_posix(),
            "Source timeline/PNG registry path differs")
    frames_binding = checked(root, preparation["frames"], "Source PNG registry")
    timing_binding = checked(root, preparation["frame_map"], "Source timeline")
    frames = join_frames(preparation, read(root / timing_binding["path"]), read(root / frames_binding["path"]))
    annotations = proposal["annotations"]
    require([r["frame_index"] for r in annotations] == [r["source_frame_index"] for r in frames],
            "Annotation order/census differs from full source window")
    bounds = SourceVideo.from_mapping({"path": source_binding["path"], "sha256": source_binding["sha256"],
        "width_px": preparation["width"], "height_px": preparation["height"], "fps": 60.0,
        "frame_count": preparation["decoded_frame_count"]})
    require(min(bounds.width_px, bounds.height_px) >= 120, "Source too small for unchanged detail renderer")
    evidence = [checked(root, b, "Visual inspection evidence") for b in proposal["inspection_evidence"]]
    require(len({b["path"] for b in evidence}) == len(evidence), "Duplicate inspection evidence")
    png_paths = set()
    for position, (frame, row) in enumerate(zip(frames, annotations, strict=True)):
        parsed = FrameAnnotation.from_mapping(row, position, bounds)
        require(parsed.annotation_status == "labeled", "All frames need explicit visual judgments, including unknowns")
        png = frame["source_png"]
        checked(root, png, "Source PNG")
        path = path_in(root, png["path"])
        require(path.parent == folder / "frames" and path.name == f"{frame['source_frame_index']:06d}.png"
                and path not in png_paths, "Source PNG identity/path duplicated or changed")
        png_paths.add(path)
        image = cv2.imread(str(path))
        require(image is not None and image.shape == (bounds.height_px, bounds.width_px, 3), "Native PNG dimensions differ")
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        require(hashlib.sha256(rgb.tobytes()).hexdigest() == png["rgb_sha256"], "Native PNG RGB hash differs")
        frame["annotation"] = row
    return {"schema_version": "fresh_game_reference_review/v0.1", "status": STATUS,
        "clip_id": clip, "game_id": proposal["game_id"], "role": ROLE,
        "annotation_origin": proposal["annotation_origin"], "annotator_id": proposal["annotator_id"],
        "human_acceptance": None, "training_eligible": False, "checkpoint_selection_eligible": False,
        "proposal": binding(root, proposal_path), "selection": selection_binding,
        "source_preparation": binding(root, preparation_path), "source_video": source_binding,
        "source_metadata": {k: preparation[k] for k in ("width", "height", "average_rate", "time_base", "decoded_frame_count")},
        "source_frames": frames_binding, "source_timeline": timing_binding, "inspection_evidence": evidence,
        "frames": frames, "frame_count": len(frames), "counts": dict(Counter(r["visibility"] for r in annotations)),
        "eligible_centers": sum(r["localization_eligible"] for r in annotations),
        "null_centers": sum(r["geometry"] is None for r in annotations), "exceptions": review_exceptions(frames),
        "validation": {"all_source_PNG_byte_and_RGB_hashes_checked": True,
            "all_native_PTS_joins_checked": True, "actual_emitted_frames_checked": 0,
            "independent_video_decode_pixel_audit_performed": False,
            "timing_authority": "bound source-preparer full native PTS map; actual next PTS for every selected duration"},
        "model_calls": 0, "new_labels": 0, "accepted_labels": 0, "training_updates": 0}


def canvas(root, item, manifest):
    image = cv2.imread(str(path_in(root, item["source_png"]["path"])))
    require(image is not None, "Source PNG cannot be read")
    final = manifest["frames"][-1]["source_frame_index"]
    result = render_frame(image, item, manifest["frame_count"], "Clip " + manifest["clip_id"], ROLE,
                          final, manifest["source_metadata"]["decoded_frame_count"] - 1)
    result[540:, :] = 0
    row = item["annotation"]
    geometry = row["geometry"]
    state = row["visibility"].replace("_", " ")
    center = "Center unknown" if geometry is None else f"Marked center; uncertainty {geometry['uncertainty_radius_px']:g} pixels"
    seconds = float(item["native_pts_ticks"] * Fraction(item["native_time_base"]))
    lines = [f"Clip {manifest['clip_id']} | Frame {item['source_frame_index']} of {final} | {seconds:.3f} seconds",
             f"{state.capitalize()} | {center}",
             "AI reference proposal - awaiting your review",
             "Review every frame, including unknown centers and the final frame."]
    for index, line in enumerate(lines):
        cv2.putText(result, line, (20, 576 + 34 * index), cv2.FONT_HERSHEY_SIMPLEX, .65,
                    (235, 235, 235), 1, cv2.LINE_AA)
    return result


def source_color(root, manifest):
    command = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
        "stream=width,height,avg_frame_rate,time_base,color_primaries,color_transfer", "-of", "json",
        str(path_in(root, manifest["source_video"]["path"]))]
    probe = json.loads(subprocess.run(command, check=True, capture_output=True, text=True).stdout)
    require(len(probe.get("streams", [])) == 1, "Exactly one source video stream required")
    stream, meta = probe["streams"][0], manifest["source_metadata"]
    require((stream["width"], stream["height"]) == (meta["width"], meta["height"])
            and Fraction(stream["avg_frame_rate"]) == 60 and Fraction(stream["time_base"]) == Fraction(meta["time_base"]),
            "Actual source metadata differs from preparation")
    primaries, transfer = stream.get("color_primaries"), stream.get("color_transfer")
    require(primaries not in (None, "unknown", "unspecified") and transfer not in (None, "unknown", "unspecified"),
            "Known actual source color primaries/transfer needed for review encoding")
    return probe, primaries, transfer


def encode_review(root, manifest, destination, name, rate, primaries, transfer):
    path = destination / name
    command = review_encoding_command(path, rate, primaries, transfer)
    with (destination / (name + ".log")).open("xb") as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
        try:
            for item in manifest["frames"]:
                process.stdin.write(canvas(root, item, manifest).tobytes())
            process.stdin.close()
            require(process.wait() == 0, "Review encoding failed; partial video/log preserved")
        finally:
            if process.stdin and not process.stdin.closed:
                try:
                    process.stdin.close()
                except BrokenPipeError:
                    pass
            if process.poll() is None:
                process.kill(); process.wait()
    probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
        "stream=width,height,nb_frames,avg_frame_rate,color_range,color_space,color_transfer,color_primaries",
        "-of", "json", str(path)], check=True, capture_output=True, text=True).stdout)
    stream = probe["streams"][0]
    require(len(probe["streams"]) == 1 and (stream["width"], stream["height"]) == (1280, 720)
            and int(stream["nb_frames"]) == manifest["frame_count"] and Fraction(stream["avg_frame_rate"]) == rate
            and stream.get("color_space") == "smpte170m" and stream.get("color_range") == "tv"
            and stream.get("color_primaries") == primaries and stream.get("color_transfer") == transfer,
            "Encoded frame count, rate, dimensions or color tags differ")
    capture = cv2.VideoCapture(str(path))
    checks = []
    try:
        for item in manifest["frames"]:
            ok, actual = capture.read()
            require(ok and actual.shape == (720, 1280, 3), "Encoded frame missing or wrong dimensions")
            expected = canvas(root, item, manifest)
            error = float(np.abs(actual.astype(np.int16) - expected.astype(np.int16)).mean())
            require(error <= 8, "Encoded review frame differs from its source/annotation")
            marker_error = None
            if item["annotation"]["geometry"] is not None:
                expected_crop, actual_crop = expected[40:340, 970:1270], actual[40:340, 970:1270]
                marker = np.all(expected_crop == (0, 255, 255), axis=2)
                require(int(marker.sum()) >= 20, "Expected annotation marker missing")
                marker_error = float(np.abs(actual_crop.astype(np.int16)[marker] - expected_crop.astype(np.int16)[marker]).mean())
                require(marker_error <= 65, "Encoded annotation marker differs")
            checks.append({"source_frame_index": item["source_frame_index"], "mean_absolute_pixel_error": error,
                           "marker_pixel_error": marker_error})
        require(not capture.read()[0], "Extra encoded frame")
        require(abs(capture.get(cv2.CAP_PROP_FPS) - rate) <= .01, "Decoded playback cadence differs")
        final = destination / name.replace(".mp4", "_actual_final.png")
        require(cv2.imwrite(str(final), actual), "Cannot save actual encoded final frame")
    finally:
        capture.release()
    probe_path = destination / name.replace(".mp4", "_probe.json")
    write_new(probe_path, probe)
    return {**binding(root, path), "fps": rate, "frame_count": len(checks), "duration_seconds": len(checks) / rate,
        "encoding_command": command, "encoded_probe": binding(root, probe_path),
        "actual_final": binding(root, final), "emitted_frame_checks": checks}


def write_viewer(destination, manifest):
    entries = [{"frame": f["source_frame_index"], "image": f"overlays/{f['source_frame_index']:06d}.png",
                "description": f["annotation"]["visibility"].replace("_", " "),
                "notes": f["annotation"]["notes"] or ""} for f in manifest["frames"]]
    safe_data = json.dumps(entries).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    title = html.escape("Clip " + manifest["clip_id"] + " - reference review")
    links = "".join(f'<li><a href="overlays/{r["source_frame_index"]:06d}.png">Frame {r["source_frame_index"]}</a>: '
                    + html.escape(", ".join(r["reasons"]).replace("_", " ")) + "</li>" for r in manifest["exceptions"])
    content = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title}</title><style>body{{font:17px system-ui;background:#171a1e;color:#eee;max-width:1280px;margin:24px auto;padding:0 16px}}a{{color:#8bc4ff}}img,video{{width:100%}}button,input{{font:inherit;margin:8px}}p{{line-height:1.5}}</style>
<h1>{title}</h1><p>These are AI reference proposals awaiting your review. Every source frame is included. An unknown center stays unmarked; no hidden ball position has been invented.</p>
<p><a href="review_native.mp4">Normal speed (60 fps)</a> · <a href="review_slow.mp4">Slow playback (10 fps)</a> · <a href="exceptions.json">All uncertainty and final-frame details</a></p>
<video controls preload="metadata" src="review_slow.mp4"></video><p><button id="previous">Previous</button><input id="index" type="range" min="0" max="{len(entries)-1}" value="0"><button id="next">Next</button><span id="label"></span></p>
<img id="frame" alt="Source frame with proposed reference marker"><p id="notes"></p><details><summary>Unknown centers, uncertainty, and the final frame</summary><p>Every nonzero spatial uncertainty is listed; this list does not set a new acceptance threshold.</p><ul>{links}</ul></details>
<script>const rows={safe_data};const slider=document.getElementById('index');function show(){{const r=rows[Number(slider.value)];document.getElementById('frame').src=r.image;document.getElementById('label').textContent='Frame '+r.frame+' — '+r.description;document.getElementById('notes').textContent=r.notes;}}slider.oninput=show;document.getElementById('previous').onclick=()=>{{slider.value=Math.max(0,Number(slider.value)-1);show();}};document.getElementById('next').onclick=()=>{{slider.value=Math.min(rows.length-1,Number(slider.value)+1);show();}};document.onkeydown=e=>{{if(e.key==='ArrowLeft')document.getElementById('previous').click();if(e.key==='ArrowRight')document.getElementById('next').click();}};show();</script></html>'''
    with (destination / "index.html").open("x", encoding="utf-8") as handle:
        handle.write(content)


def render(root, proposal_path, destination, selection_path=SELECTION):
    root = Path(root).resolve()
    manifest = validate(root, proposal_path, selection_path)
    probe, primaries, transfer = source_color(root, manifest)
    destination = path_in(root, destination)
    require(destination.is_relative_to(root / BASE), "Review output must stay in the new diagnostic study")
    destination.mkdir(parents=True, exist_ok=False)
    write_new(destination / "started.json", {"proposal": manifest["proposal"], "status": "rendering_pending_AI_proposal"})
    write_new(destination / "source_color_probe.json", probe)
    overlays = destination / "overlays"
    overlays.mkdir()
    for item in manifest["frames"]:
        path = overlays / f"{item['source_frame_index']:06d}.png"
        require(cv2.imwrite(str(path), canvas(root, item, manifest)), "Cannot save review overlay")
        item["review_overlay"] = binding(root, path)
    write_new(destination / "exceptions.json", {"status": STATUS, "all_nonzero_uncertainty_included": True,
        "source_final_frame_index": manifest["source_metadata"]["decoded_frame_count"] - 1,
        "selected_final_frame_index": manifest["frames"][-1]["source_frame_index"], "rows": manifest["exceptions"]})
    manifest["videos"] = [encode_review(root, manifest, destination, name, rate, primaries, transfer)
        for name, rate in (("review_native.mp4", 60), ("review_slow.mp4", 10))]
    manifest["validation"]["actual_emitted_frames_checked"] = 2 * len(manifest["frames"])
    manifest["review_color_conversion"] = {"source_pngs_changed": False, "primaries": primaries,
        "transfer": transfer, "encoded_matrix": "smpte170m", "encoded_range": "tv",
        "basis": "actual source tags preserved; shared tested RGB-to-video encoding helper"}
    write_viewer(destination, manifest)
    manifest["implementation"] = binding(root, Path(__file__))
    manifest["outputs"] = [binding(root, p) for p in sorted(destination.rglob("*")) if p.is_file()]
    write_new(destination / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--selection", default=SELECTION, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = (render(Path.cwd(), args.proposal, args.output, args.selection) if args.output
              else validate(Path.cwd(), args.proposal, args.selection))
    print(json.dumps({k: result[k] for k in ("status", "clip_id", "frame_count", "counts", "null_centers")}))


if __name__ == "__main__":
    main()
