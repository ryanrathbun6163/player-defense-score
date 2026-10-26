"""Strict TAP transport, unchanged completion scoring, and five native reviews.

NBA review layout/publication is adapted from completion_nba_comparison_render;
its native encoder, source guards and decoded frame-key helpers are reused.
TAP observations never acquire fabricated heatmaps or temporal contributions.
"""
from __future__ import annotations

from fractions import Fraction
import html
import math
from pathlib import Path
import time
import traceback

import cv2
import numpy as np

from . import completion_evaluation as original
from . import completion_comparison_render as curated
from . import completion_nba_comparison_render as nba
from .completion_scoring import score_timeline
from .completion_training_runtime import atomic_write_once as write_once, binding, check
from .tapnext_adapter import POLICY, project_wasb_observation, support_queries
from .wasb_experiment import bound_path, canonical, read_json

METHOD = "tapnextpp512_single_seed"


def finite_point(point):
    check(isinstance(point, list) and len(point) == 2
          and all(type(v) in (int, float) and math.isfinite(v) for v in point), "Invalid finite TAP point")
    return point


def validate_observations(block, observations):
    """Check actual SingleSeedAdapter records against the native baseline producer."""
    baseline = original.baseline_observations(block)
    check(len(observations) == len(block["frames"]), "Incomplete TAP native block")
    width, height = (block["source_video"][k] for k in ("width_px", "height_px"))
    def inside(point):
        return point is not None and 0 <= point[0] < width and 0 <= point[1] < height
    seed, calls, previous = None, 0, None
    for frame, old, row in zip(block["frames"], baseline, observations, strict=True):
        check(frame["state"] == "permitted" and not any(lo <= frame["source_frame_index"] <= hi
              for lo, hi in block.get("protected_ranges", [])), "Protected TAP inference prohibited")
        check(row.get("schema_version") == "tapnext_observation/v0.1" and row.get("method") == POLICY
              and row.get("block_id") == block["block_id"], "TAP method/block differs")
        check(not ({"candidates", "mean_heatmap_sha256", "selected_candidate_index", "temporal_contributions"} & row.keys()),
              "TAP must not fabricate WASB fields")
        check(row["source_frame_index"] == frame["source_frame_index"]
              and row["source_pts_ticks"] == frame["source_pts_ticks"]
              and row["duration_ticks"] == frame["duration_ticks"]
              and Fraction(row["time_base"]) == Fraction(block["time_base"])
              and row["source_png"] == frame["png"], "TAP native source transport differs")
        if previous is not None:
            check(row["source_frame_index"] == previous["source_frame_index"] + 1
                  and row["source_pts_ticks"] == previous["source_pts_ticks"] + previous["duration_ticks"],
                  "TAP native context has an undeclared discontinuity")
        previous = row
        check(row["inference_status"] == "completed" and row["point_origin"] == "automatic"
              and row["native_score"] is None, "Failed/manual inference or fabricated confidence")
        projected = project_wasb_observation(old)
        check(row["wasb_observation"] == projected, "TAP baseline projection differs from actual original record")
        newly_seeded = seed is None and inside(projected["center_xy_px"])
        if newly_seeded:
            seed = {"source_frame_index": frame["source_frame_index"], "source_pts_ticks": frame["source_pts_ticks"],
                "time_base": block["time_base"], "center_xy_px": projected["center_xy_px"],
                "wasb_record_sha256": projected["original_record_sha256"],
                "support_queries_xy": support_queries(projected["center_xy_px"], width, height).astype(float).tolist()}
        check(row["seeded_this_frame"] is newly_seeded and row["seed"] == seed, "First automatic seed/reseed policy differs")
        raw, expected, reason, disagreement = row["tracker_raw"], None, "before_first_valid_automatic_seed", None
        if seed is None:
            check(raw is None, "Unseeded frame contains tracker output")
        else:
            calls += 1
            check(isinstance(raw, dict), "Seeded frame lacks tracker output")
            point = finite_point(raw["center_xy_px"])
            model_yx = finite_point(raw["coordinates_model_yx"])
            expected_xy = (np.array(model_yx[::-1], np.float32)
                           * np.array([width / 256, height / 256], np.float32)).astype(float).tolist()
            check(point == expected_xy, "TAP source/model coordinate transform differs")
            logits = raw["coordinate_logits_model_yx"]
            check(isinstance(logits, list) and len(logits) == 512
                  and all(type(v) in (int, float) and math.isfinite(v) for v in logits), "Invalid coordinate logits")
            visibility = raw["visibility_logit"]
            check(type(visibility) in (int, float) and math.isfinite(visibility), "Invalid visibility logit")
            visible, in_image = visibility > 0, inside(point)
            check(raw["predicted_visible"] is visible and raw["in_source_bounds"] is in_image
                  and raw["support_count"] == 64 and raw["coordinate_resolution"] == 256, "Tracker flags/support policy differs")
            expected = point if visible and in_image else None
            reason = None if expected is not None else "tracker_predicted_hidden" if not visible else "tracker_out_of_image"
            if inside(projected["center_xy_px"]) and in_image:
                disagreement = math.dist(projected["center_xy_px"], point)
        check(type(row["tracker_calls_in_block"]) is int and row["tracker_calls_in_block"] == calls, "Tracker call census differs")
        check(row["center_xy_px"] == expected and row["missing_reason"] == reason
              and row["state"] == ("observed" if expected is not None else "missing"), "Public TAP point/visibility differs")
        check(row["wasb_tracker_distance_px"] == disagreement, "Diagnostic disagreement differs")
    return {"frames": len(observations), "model_calls": calls, "automatic_seed": seed}


def score_package(package, block_records, package_binding):
    """The original fixed cohorts and exact scorer; TAP replaces only predictions."""
    method = package["selected_method"]
    check(method["method_kind"] == METHOD and method.get("training_result") is None
          and method["policy"]["id"] == POLICY, "Expected fixed pretrained TAP method, not a fit")
    check(package["execution_ready"] is True and package.get("protected_evaluation_authorized", False) is False,
          "Permitted selected package required")
    inventory = package["regression_cohorts"]
    check(len(inventory) == len({c["cohort_id"] for c in inventory}) == 16
          and sum(c["regression_screen"] is True for c in inventory) == 13
          and sum(c.get("pilot_control", False) is True for c in inventory) == 2,
          "Fixed16-cohort/13-guard/two-pilot inventory differs")
    blocks = package["inference_blocks"]
    check(set(block_records) == {b["block_id"] for b in blocks}, "Missing/extra TAP blocks")
    rows_by_source, observations_by_source = {}, {}
    for block in blocks:
        record = block_records[block["block_id"]]
        check(record["block_sha256"] == canonical(block), "TAP block bytes differ")
        baseline, selected = original.baseline_observations(block), record["observations"]
        validate_observations(block, selected)
        source_id = block.get("possession_id", block.get("candidate_id"))
        rows_by_source.setdefault(source_id, {"baseline": {}, "selected": {}})
        observations_by_source.setdefault(source_id, {"baseline": [], "selected": []})
        for label, observations in (("baseline", baseline), ("selected", selected)):
            score = score_timeline(block, observations)
            target = rows_by_source[source_id][label]
            check(not set(target).intersection(r["source_frame_index"] for r in score["frame_results"]), "Overlapping source blocks")
            target.update({r["source_frame_index"]: r for r in score["frame_results"]})
            observations_by_source[source_id][label].extend(observations)
    comparisons = []
    for timeline in package["curated_timelines"]:
        pid = timeline["possession_id"]
        result = {"possession_id": pid}
        for label in ("baseline", "selected"):
            observations = sorted(observations_by_source[pid][label], key=lambda r: r["source_frame_index"])
            result[label + "_observations"] = observations
            result[label + "_metrics"] = score_timeline(timeline, observations)
        result["changed_frames"] = original.comparison_changes(result["baseline_metrics"]["frame_results"], result["selected_metrics"]["frame_results"])
        curated.validate_timeline(timeline, result)
        comparisons.append(result)
    cohorts = []
    for cohort in inventory:
        ids = cohort["frame_indices"]
        check(len(ids) == len(set(ids)), "Duplicate cohort indices")
        source = rows_by_source[cohort["source_id"]]
        rows = {label: [source[label][i] for i in ids] for label in ("baseline", "selected")}
        counts = {label: original.cohort_counts(value) for label, value in rows.items()}
        old, new = counts["baseline"], counts["selected"]
        check(old["eligible"] == new["eligible"], "Comparison eligibility changed")
        conditions = {"matched_not_lower": new["matched"] >= old["matched"],
            "wrong_not_higher": new["wrong"] <= old["wrong"],
            "hidden_not_higher": new["all_hidden_emissions"] <= old["all_hidden_emissions"],
            "certain_hidden_not_higher": new["certain_hidden_emissions"] <= old["certain_hidden_emissions"]}
        if cohort.get("pilot_control"):
            check(old["matched"] == old["eligible"] == 60, "Retained pilot control does not reproduce60/60")
            conditions["pilot_60_of_60_retained"] = new["matched"] == new["eligible"] == 60
        cohorts.append({"cohort": cohort, **counts, "conditions": conditions,
            "status": ("pass" if all(conditions.values()) else "fail") if cohort["regression_screen"] else "descriptive_training_exposure",
            "changed_frames": original.comparison_changes(rows["baseline"], rows["selected"]),
            "baseline_frame_results": rows["baseline"], "selected_frame_results": rows["selected"]})
    return {"schema_version": "completion_evaluation/v0.1", "status": "completed", "package": package_binding,
        "selected_checkpoint": method["checkpoint"], "method_kind": METHOD, "training_result": None,
        "selection": None, "selection_outcome": "fixed_pretrained_tracker_pilot_pending_development_and_human_review",
        "curated_comparisons": comparisons, "regression_cohorts": cohorts,
        "prospective_regression_status": "fail" if any(c["status"] == "fail" for c in cohorts) else "pass",
        "permitted_development_screen": {c["possession_id"]: c["selected_metrics"]["summary"] for c in comparisons},
        "protected_evaluation_authorized": False, "human_trajectory_acceptance": None,
        "full_clip_pass_claimed": False, "conditional_resolution_fit_authorized_by_report": False,
        "wrong_object_review": "pending explicit point-bound evidence; geometry is not object identity",
        "tor": package.get("tor"), "bounded_gap_additions": package.get("bounded_gap_additions")}


def nba_canvas(rgb, block, frame, baseline, selected, offset):
    """Existing NBA two-panel layout with truthful recurrent-tracker captions."""
    sw, sh = (block["source_video"][k] for k in ("width_px", "height_px"))
    image = np.zeros((nba.HEIGHT, nba.WIDTH, 3), dtype=np.uint8)
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
    left, top = min(max(0, int(ax-crop_size/2)), sw-crop_size), min(max(0, int(ay-crop_size/2)), sh-crop_size)
    text(f"{block['candidate_id']} | complete native action context | same frame on both sides", 12, 25, scale=.62)
    text(f"Native frame {frame['source_frame_index']} | PTS {frame['source_pts_ticks']} x {block['time_base']} | interval {frame['duration_ticks']} ticks", 12, 52)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    for column, observation in enumerate((baseline, selected)):
        x0, color = column * nba.PANEL_W, (30, 150, 255) if column == 0 else (255, 210, 0)
        text("RETAINED WASB" if column == 0 else "AUTOMATIC TAPNext++ PILOT", x0+12, 90, color, .65)
        panel = cv2.resize(bgr, (nba.PANEL_W, nba.PANEL_H))
        crop = cv2.resize(bgr[top:top+crop_size, left:left+crop_size], (220, 220), interpolation=cv2.INTER_NEAREST)
        for point, point_color, marker in ((reference, (80, 255, 80), cv2.MARKER_TILTED_CROSS),
                                           (observation["center_xy_px"], color, cv2.MARKER_CROSS)):
            if inside(point):
                cv2.drawMarker(panel, (round(point[0]*nba.PANEL_W/sw), round(point[1]*nba.PANEL_H/sh)), point_color, marker, 15, 2)
                if left <= point[0] < left+crop_size and top <= point[1] < top+crop_size:
                    cv2.drawMarker(crop, (round((point[0]-left)*220/crop_size), round((point[1]-top)*220/crop_size)), point_color, marker, 20, 2)
        image[nba.TOP:nba.TOP+nba.PANEL_H, x0:x0+nba.PANEL_W] = panel
        image[480:700, x0+10:x0+230] = crop
        point = observation["center_xy_px"]
        text("MISSING" if point is None else f"Point ({point[0]:.1f}, {point[1]:.1f}) px", x0+245, 500, color)
        text(f"WASB contributions: {observation['temporal_contributions']}" if column == 0 else
             f"TAP recurrent steps: {observation['tracker_calls_in_block']}", x0+245, 529)
        text("Reference: unlabeled" if annotation is None else f"Reference: {annotation['visibility']}", x0+245, 558)
        text("Reference center: unknown" if reference is None else f"Reference ({reference[0]:.1f}, {reference[1]:.1f})", x0+245, 587)
        text("Common crop: reference" if inside(reference) else "Common crop: model" if anchor is not None else "Common crop: source center", x0+245, 616)
        text("Green: accepted reference", x0+245, 645, (80, 255, 80))
        text("Hidden tracker coordinates not shown", x0+245, 674)
    for i, bit in enumerate(nba.frame_key(offset, frame)):
        image[nba.KEY_TOP:nba.HEIGHT, i*10:(i+1)*10] = 255 if bit == "1" else 0
    return image


def render_nba_block(root, block, selected, folder, provenance):
    """Adapted NBA renderer, preserving the original native encoder/verification."""
    root, folder = Path(root).resolve(), Path(folder).resolve()
    check(folder.is_relative_to(root / "data/outputs"), "Review output escaped data/outputs")
    schedule, baseline = nba.timing_schedule(block), original.baseline_observations(block)
    validate_observations(block, selected)
    folder.mkdir(parents=True, exist_ok=False)
    began = time.perf_counter()
    write_once(folder / "started.json", {"block_sha256": canonical(block), "provenance": provenance,
        "implementation": binding(root, Path(__file__)) if Path(__file__).resolve().is_relative_to(root) else None})
    try:
        video = folder / "comparison.mp4"
        rows = block["frames"]
        def canvases():
            for offset, (frame, old, new) in enumerate(zip(rows, baseline, selected, strict=True)):
                yield nba_canvas(nba.source_rgb(root, block, frame), block, frame, old, new, offset)
        encoding = nba.encode_review_video(video, canvases(), schedule, block["time_base"], "bt709", "bt709")
        probe = nba.probe_encoded_video(video)
        checked = nba.validate_encoded_timing(probe, schedule, block["time_base"], "bt709", "bt709")
        write_once(folder / "ffprobe.json", probe)
        capture = cv2.VideoCapture(str(video))
        errors, final = [], None
        try:
            for offset, (frame, old, new) in enumerate(zip(rows, baseline, selected, strict=True)):
                ok, final = capture.read()
                check(ok and final.shape == (nba.HEIGHT, nba.WIDTH, 3), "Encoded TAP comparison ended before actual final")
                key = "".join("1" if float(final[nba.KEY_TOP+8, i*10+5].mean()) > 127 else "0" for i in range(128))
                check(key == nba.frame_key(offset, frame), "Decoded native TAP frame key differs")
                expected = nba_canvas(nba.source_rgb(root, block, frame), block, frame, old, new, offset)
                error = float(np.abs(final.astype(np.int16)-expected.astype(np.int16)).mean())
                check(error < 8, "Decoded TAP overlay/source differs")
                errors.append(error)
            check(not capture.read()[0], "Encoded TAP comparison has extra frames")
        finally:
            capture.release()
        final_path = folder / "actual_final_frame.png"
        check(cv2.imwrite(str(final_path), final), "Could not save actual TAP final")
        records = [{"source_frame_index": row["source_frame_index"], "source_pts_ticks": row["source_pts_ticks"],
            "duration_ticks": row["duration_ticks"], "time_base": block["time_base"], "source_png": row["png"],
            "annotation": row["annotation"], "reference_role": row["reference_role"],
            "baseline_observation": old, "selected_observation": new, **timing}
            for row, old, new, timing in zip(rows, baseline, selected, checked, strict=True)]
        write_once(folder / "frame_records.json", {"block_id": block["block_id"], "provenance": provenance, "frames": records})
        transported = read_json(folder / "frame_records.json")
        validate_observations(block, [r["selected_observation"] for r in transported["frames"]])
        check(transported["frames"] == records, "Serialized TAP render records differ")
        result = {"candidate_id": block["candidate_id"], "block_id": block["block_id"], "block_sha256": canonical(block),
            "video": binding(root, video), "actual_final_frame": binding(root, final_path),
            "frame_records": binding(root, folder / "frame_records.json"), "encoded_probe": binding(root, folder / "ffprobe.json"),
            "provenance": provenance, "encoding": encoding, "decoded_frames": len(errors),
            "actual_final_native_frame": rows[-1]["source_frame_index"], "actual_final_source_pts_ticks": rows[-1]["source_pts_ticks"],
            "actual_final_duration_ticks": rows[-1]["duration_ticks"], "time_base": block["time_base"],
            "native_pts_packet_frame_duration_checks": len(checked), "total_duration_ticks": schedule[-1][0]+schedule[-1][1],
            "added_final_hold_ticks": 0, "all_decoded_native_keys_verified": True,
            "all_frame_mean_absolute_errors": errors, "elapsed_seconds": time.perf_counter()-began,
            "human_visual_acceptance": None, "model_calls": 0, "source_video_decodes": 0, "protected_png_reads": 0}
        write_once(folder / "render_receipt.json", result)
        return result
    except BaseException as error:
        write_once(folder / "failed.json", {"error": str(error), "traceback": traceback.format_exc()})
        raise


def validate_curated_timing(probe, timeline):
    """Verify CFR packet/frame times without inventing missing color metadata.

The existing curated encoder may use B frames, so packet decode order is not
presentation order. Compare both complete censuses sorted by presentation PTS.
"""
    streams = probe.get("streams", [])
    check(len(streams) == 1, "Curated video stream census differs")
    stream, rows = streams[0], timeline["frames"]
    check((stream["width"], stream["height"]) == (curated.WIDTH, curated.HEIGHT), "Curated video dimensions differ")
    encoded, source = Fraction(stream["time_base"]), Fraction(timeline["time_base"])
    origin = rows[0]["source_pts_ticks"]
    expected = [((r["source_pts_ticks"]-origin)*source, r["duration_ticks"]*source) for r in rows]
    check(int(stream["start_pts"]) == 0 and int(stream["nb_frames"]) == len(rows)
          and int(stream["duration_ts"])*encoded == expected[-1][0]+expected[-1][1], "Curated total/final interval differs")
    combined = probe.get("packets_and_frames", [])
    packets = probe.get("packets", [r for r in combined if r.get("type") == "packet"])
    frames = probe.get("frames", [r for r in combined if r.get("type") == "frame"])
    check(len(packets) == len(frames) == len(rows), "Curated packet/frame census differs")
    for records, decoded in ((packets, False), (frames, True)):
        ordered = sorted(records, key=lambda r: int(r["pts"]))
        for record, (pts, duration) in zip(ordered, expected, strict=True):
            check(int(record["pts"])*encoded == pts
                  and int(record.get("duration", record.get("pkt_duration", -1)))*encoded == duration,
                  "Curated native PTS/duration differs")
            if decoded:
                check(int(record["best_effort_timestamp"])*encoded == pts, "Curated decoded PTS differs")
    return len(rows)


def scorecard_html(evaluation):
    guarded = [c for c in evaluation["regression_cohorts"] if c["cohort"]["regression_screen"]]
    passed = sum(c["status"] == "pass" for c in guarded)
    rows = []
    for comparison in evaluation["curated_comparisons"]:
        for key, label in (("baseline", "Retained WASB"), ("selected", "Automatic TAPNext++")):
            m = comparison[key + "_metrics"]["summary"]
            rows.append(f'<tr><td>{html.escape(comparison["possession_id"])}</td><td>{label}</td>'
                f'<td>{m["matched"]}/{m["eligible_frames"]}</td><td>{m["wrong"]}</td><td>{m["missing"]}</td>'
                f'<td>{m["certain_hidden_emitted_points"]}</td><td>{html.escape(m["quantitative_status"])}</td></tr>')
    return (f'<h2>Fixed development comparison</h2><p>Guarded cohorts: <strong>{passed}/{len(guarded)} pass</strong>. '
        f'Prospective regression status: <strong>{html.escape(evaluation["prospective_regression_status"])}</strong>. '
        'Three training-exposure cohorts remain descriptive. Pending object judgments and human review are not passes.</p>'
        '<table><thead><tr><th>Possession</th><th>Method</th><th>Correct / eligible</th><th>Wrong</th><th>Missing</th>'
        '<th>Certain-hidden emissions</th><th>Automatic screen</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table>')


def render_all(root, package_binding, evaluation_binding, block_records, output_folder):
    """Publish three curated and two NBA reviews; all five native finals verified."""
    root = Path(root).resolve()
    package, evaluation = read_json(bound_path(root, package_binding)), read_json(bound_path(root, evaluation_binding))
    curated.validate_evaluation(package, evaluation, package_binding)
    check(evaluation["method_kind"] == METHOD and evaluation["training_result"] is None, "TAP render method differs")
    expected = score_package(package, block_records, package_binding)
    check(all(evaluation.get(k) == v for k, v in expected.items()), "Serialized evaluation differs from actual TAP records")
    output = (root / output_folder).resolve()
    check(output.is_relative_to(root / "data/outputs") and not output.exists(), "Preserve previous TAP review output")
    output.mkdir(parents=True)
    identity = {"package": package_binding, "evaluation": evaluation_binding,
        "implementation": binding(root, Path(__file__)), "method_kind": METHOD,
        "protected_evaluation_authorized": False}
    write_once(output / "started.json", identity)
    try:
        curated_result = curated.render_comparison(root, package_binding, evaluation_binding,
            str((output / "curated").relative_to(root)))
        curated_summary = read_json(bound_path(root, curated_result["summary"]))
        native = []
        for timeline, rendered in zip(package["curated_timelines"], curated_summary["possessions"], strict=True):
            expected_comparison = next(c for c in evaluation["curated_comparisons"]
                                       if c["possession_id"] == timeline["possession_id"])
            transported = read_json(bound_path(root, rendered["frame_records"]))
            check(rendered["possession_id"] == timeline["possession_id"]
                  and transported["timeline"] == timeline and transported["comparison"] == expected_comparison
                  and transported["no_inferred_fills"] is True, "Emitted curated TAP frame records differ")
            curated.validate_timeline(transported["timeline"], transported["comparison"])
            bound_path(root, rendered["actual_final_frame"])
            rows = timeline["frames"]
            probe = nba.probe_encoded_video(bound_path(root, rendered["video"]))
            checked = validate_curated_timing(probe, timeline)
            record = {"possession_id": timeline["possession_id"], "checks": checked,
                "actual_final_native_frame": rows[-1]["source_frame_index"],
                "actual_final_source_pts_ticks": rows[-1]["source_pts_ticks"], "actual_final_duration_ticks": rows[-1]["duration_ticks"],
                "time_base": timeline["time_base"], "added_final_hold_ticks": 0, "probe": probe}
            path = output / (timeline["possession_id"] + "_native_timing.json")
            write_once(path, record)
            native.append(binding(root, path))
        blocks = [b for b in package["inference_blocks"] if b["domain"] == "nba"]
        check(len(blocks) == 2 and sum(len(b["frames"]) for b in blocks) == 2702, "Fixed NBA review census differs")
        nba_results = [render_nba_block(root, block, block_records[block["block_id"]]["observations"],
            output / block["candidate_id"], identity) for block in blocks]
        videos = curated_summary["possessions"] + nba_results
        check(len(videos) == 5 and sum(r["decoded_frames"] for r in videos) == 4200
              and curated_summary["protected_black_frames"] == 225, "Five-video timeline census differs")
        summary = {"schema_version": "tapnext_comparison_render/v0.1", "status": "completed", "identity": identity,
            "curated": curated_result, "curated_native_timing": native, "nba": nba_results,
            "videos": 5, "timeline_slots": 4200, "permitted_frames": 3975, "protected_black_frames": 225,
            "all_native_final_intervals_verified": True, "human_visual_acceptance": None}
        write_once(output / "summary.json", summary)
        sections = []
        for result in videos:
            label = result.get("possession_id", result.get("candidate_id"))
            video = (root / result["video"]["path"]).relative_to(output).as_posix()
            final = (root / result["actual_final_frame"]["path"]).relative_to(output).as_posix()
            sections.append(f'<section><h2>{html.escape(label)}</h2><video controls preload="metadata" src="{html.escape(video, quote=True)}"></video><p>Final native frame {result["actual_final_native_frame"]}: <a href="{html.escape(final, quote=True)}">actual final</a></p></section>')
        (output / "index.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Automatic TAP pilot comparison</title><style>body{font:17px/1.5 system-ui;max-width:1400px;margin:32px auto;padding:0 16px}video{width:100%}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:9px;border-bottom:1px solid #aaa}section{margin:32px 0}</style><h1>Retained WASB and automatic TAPNext++ pilot</h1><p>Exact native timing; missing outputs remain absent. Protected panels stay black. All five actual finals are verified; human trajectory acceptance is pending.</p>'+scorecard_html(evaluation)+''.join(sections)+'</html>', encoding="utf-8")
        completed = {"status": "completed", "identity": identity, "summary": binding(root, output / "summary.json"),
            "index": binding(root, output / "index.html"), "human_visual_acceptance": None}
        write_once(output / "completed.json", completed)
        return completed
    except BaseException as error:
        write_once(output / "failed.json", {"identity": identity, "error": str(error), "traceback": traceback.format_exc()})
        raise
