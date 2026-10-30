"""CPU scoring and native-timing review for an observed-candidate sequence choice.

The frozen native scorer/renderer validates largest-mass selection. This additive
adapter validates a chosen observed candidate or explicit abstention instead;
it preserves full candidate pools and reuses the unchanged numerical kernels.
No model library is imported, and no reference enters candidate selection here.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import html
import io
import math
from pathlib import Path
import time
import traceback

from . import completion_scoring as scoring
from .completion_references import binding
from .wasb_experiment import bound_path, canonical, read_json, write_once

AUTOMATIC_GATES = ("correct_fraction", "wrong_fraction", "certain_hidden_emissions", "missing_continuity", "recovery")
SCHEMA = "weak_response_sequence_review/v0.1"
WIDTH, HEIGHT, KEY_TOP = 1280, 720, 704
SELECTOR_FIELDS = ("candidate_index", "center_x", "center_y", "native_score", "in_source_bounds", "original_index")


def check(condition, message):
    if not condition:
        raise ValueError(message)


def validate_observations(block, observations, *, baseline=None, expected_pools=None):
    """Validate exact source transport and a real pool member (or missing state).

    ``baseline`` is the original cosine-nine producer series. ``expected_pools``
    can bind an independently retained extraction output, one list per frame.
    Neither scores nor candidate order may be rewritten to pretend a sequence
    choice was the original largest-mass choice.
    """
    check(block["domain"] == "nba" and not block.get("protected_evaluation_authorized", False),
          "Only permitted NBA contexts are supported")
    frames = block["frames"]
    indices = [f["source_frame_index"] for f in frames]
    check(len(frames) >= 3 and all(type(i) is int for i in indices)
          and indices == list(range(indices[0], indices[-1] + 1)), "Complete consecutive native context required")
    check(len(observations) == len(frames), "Observation census differs")
    check(baseline is None or len(baseline) == len(frames), "Baseline census differs")
    check(expected_pools is None or len(expected_pools) == len(frames), "Extraction census differs")
    base = Fraction(block["time_base"])
    check(base > 0 and 0 <= indices[0] <= indices[-1] < block["source_video"]["frame_count"],
          "Invalid native time base or source range")
    for position, (frame, row) in enumerate(zip(frames, observations, strict=True)):
        index = indices[position]
        check(frame.get("state", "permitted") == "permitted"
              and not any(lo <= index <= hi for lo, hi in block.get("protected_ranges", [])),
              "Protected frame prohibited")
        check(type(frame["source_pts_ticks"]) is int and type(frame["duration_ticks"]) is int
              and frame["duration_ticks"] > 0, "Invalid native timing")
        if position:
            prior = frames[position - 1]
            check(prior["source_pts_ticks"] + prior["duration_ticks"] == frame["source_pts_ticks"],
                  "Native interval discontinuity")
        check(row["source_frame_index"] == index and row["source_pts_ticks"] == frame["source_pts_ticks"]
              and row["source_png"] == frame["png"] and Fraction(row["time_base"]) == base,
              "Observation/native source transport differs")
        check(row["inference_status"] == "completed" and row.get("point_origin", "automatic") == "automatic",
              "Only completed automatic observed candidates are eligible")
        count = sum(start <= position <= start + 2
                    for start in range(max(0, position - 2), min(position, len(frames) - 3) + 1))
        check(row["temporal_contributions"] == count, "Saved temporal context differs")
        if baseline is not None:
            old = baseline[position]
            for field in ("source_frame_index", "source_pts_ticks", "time_base", "source_png",
                          "inference_status", "temporal_contributions", "mean_heatmap_sha256"):
                check(row[field] == old[field], f"Original producer provenance differs: {field}")
        candidates = row["candidates"]
        check([c["candidate_index"] for c in candidates] == list(range(len(candidates))), "Candidate order differs")
        check(all(type(c["candidate_index"]) is int and all(
            isinstance(c[k], (int, float)) and not isinstance(c[k], bool) and math.isfinite(c[k])
            for k in ("center_x", "center_y", "native_score")) for c in candidates), "Nonfinite candidate")
        check(all(c["native_score"] > 0 for c in candidates), "Observed candidate response mass must be positive")
        if expected_pools is not None:
            check(candidates == expected_pools[position], "Emitted pool differs from extracted candidates")
        chosen = row["selected_candidate_index"]
        if chosen is None:
            check(row["state"] == "missing" and row["center_xy_px"] is None and row["native_score"] is None,
                  "Abstention must be explicitly missing")
        else:
            check(type(chosen) is int and 0 <= chosen < len(candidates), "Chosen candidate is outside pool")
            candidate = candidates[chosen]
            check(row["state"] == "observed" and row["center_xy_px"] == [candidate["center_x"], candidate["center_y"]]
                  and row["native_score"] == candidate["native_score"], "Chosen point differs from observed candidate")
            check(candidate["in_source_bounds"] is True
                  and 0 <= candidate["center_x"] < block["source_video"]["width_px"]
                  and 0 <= candidate["center_y"] < block["source_video"]["height_px"],
                  "Selected observed candidate is outside source bounds")


def combine(statuses):
    values = set(statuses)
    return "fail" if "fail" in values else "inconclusive" if "inconclusive" in values else "pass" if "pass" in values else "not_applicable"


def compact_observation(row):
    """Keep the exact chosen index/point and a digest of every candidate.

    The pool lives once in a separately bound extraction file. These fields do
    not describe a one-candidate replacement pool or renumber the selection.
    """
    pool = row["candidates"]
    result = {k: deepcopy(v) for k, v in row.items() if k != "candidates"}
    chosen = row["selected_candidate_index"]
    result.update(candidate_pool_count=len(pool), candidate_pool_sha256=canonical(pool),
                  selected_candidate=None if chosen is None else deepcopy(pool[chosen]))
    return result


def restore_observation(compact, pool):
    """Verify compact transport against the actual extracted (or projected) pool."""
    check("candidates" not in compact and compact["candidate_pool_count"] == len(pool)
          and compact["candidate_pool_sha256"] == canonical(pool), "Compact candidate pool binding differs")
    chosen = compact["selected_candidate_index"]
    if chosen is None:
        check(compact["selected_candidate"] is None and compact["center_xy_px"] is None
              and compact["native_score"] is None and compact["state"] == "missing", "Compact abstention differs")
    else:
        check(type(chosen) is int and 0 <= chosen < len(pool), "Compact selected index is outside pool")
        selected = pool[chosen]
        check(compact["selected_candidate"] == selected
              and compact["center_xy_px"] == [selected["center_x"], selected["center_y"]]
              and compact["native_score"] == selected["native_score"] and compact["state"] == "observed",
              "Compact chosen observation differs from actual pool")
    row = {k: deepcopy(v) for k, v in compact.items()
           if k not in {"candidate_pool_count", "candidate_pool_sha256", "selected_candidate"}}
    row["candidates"] = pool
    return row


def verify_pool_source(root, entry):
    """Stream full extraction rows and verify only the declared lossless choice view.

    A six-field projection omits bulky extraction diagnostics, never candidates.
    The original complete source file remains hash-bound and unchanged.
    """
    source = entry.get("candidate_pool_source")
    if source is None:
        return
    policy = entry.get("candidate_pool_policy", "all")
    projection = entry.get("candidate_pool_projection")
    check(policy in {"all", "native_only"}, "Unknown candidate pool policy")
    check(projection is None or tuple(projection) == SELECTOR_FIELDS, "Unknown candidate pool projection")
    path = bound_path(root, source)
    check(binding(root, path) == source, "Candidate pool source size or digest differs")
    block = entry["block"]
    rows = entry["candidate_observations"]
    import json
    with path.open(encoding="utf-8") as handle:
        for row in rows:
            line = handle.readline()
            check(bool(line), "Candidate source ended early")
            record = json.loads(line)
            check(record["block_id"] == block["block_id"] and record["width_px"] == block["source_video"]["width_px"]
                  and record["height_px"] == block["source_video"]["height_px"], "Candidate source context differs")
            check(all(record[field] == row[field] for field in
                ("source_frame_index", "source_pts_ticks", "time_base", "mean_heatmap_sha256")), "Candidate source provenance differs")
            pool = record["candidates"]
            if policy == "native_only":
                pool = [candidate for candidate in pool if candidate.get("original_index") is not None]
            if projection is not None:
                pool = [{key: candidate[key] for key in projection} for candidate in pool]
            check(row["candidates"] == pool, "Materialized candidate pool differs from bound source/filter/projection")
        check(not handle.read().strip(), "Candidate source contains additional rows")


def _entry_identity(entry, compact):
    return {"block_id": entry["block"]["block_id"], "block_sha256": canonical(entry["block"]),
            "baseline_sha256": canonical(entry["baseline_observations"]),
            "compact_choices_sha256": canonical(compact),
            "candidate_pool_source": entry.get("candidate_pool_source"),
            "candidate_pool_policy": entry.get("candidate_pool_policy", "all"),
            "candidate_pool_projection": entry.get("candidate_pool_projection")}


def score_block(block, observations, *, baseline=None, expected_pools=None):
    """Same numerical and outer-boundary semantics as nba_first_validation.

    Only the observation selector contract differs. No label, quality threshold,
    recovery definition, uncertainty category or human-review status is changed.
    """
    validate_observations(block, observations, baseline=baseline, expected_pools=expected_pools)
    frames = block["frames"]
    timeline = {**block, "exposure_role": block.get("exposure_role", block.get("reference_role", block.get("role")))}
    report = scoring.score_timeline(timeline, observations)
    rows = report["frame_results"]
    left = frames[0]["source_frame_index"] > 0
    right = frames[-1]["source_frame_index"] < block["source_video"]["frame_count"] - 1
    if left:
        rows[0]["boundary_before"] = "exposure_subset_boundary"
    if right:
        rows[-1]["boundary_after"] = "exposure_subset_boundary"
    report["summary"] = scoring._metrics(rows)
    report["cohorts"] = {role: {"scope": "descriptive exposure subset; omitted intervals censored",
        **scoring._metrics(scoring._cohort_rows(rows, role))} for role in sorted({r["exposure_role"] for r in rows})}
    report.update(scope_censoring={"left_unobserved": left, "right_unobserved": right,
        "source_frame_range_inclusive": [frames[0]["source_frame_index"], frames[-1]["source_frame_index"]],
        "source_frame_count": block["source_video"]["frame_count"], "outside_context_inferred": False},
        source_video=block["source_video"],
        automatic_gate_status=combine(report["summary"]["gates"][key]["status"] for key in AUTOMATIC_GATES),
        human_visual_acceptance=None, full_possession_acceptance="not_assessed")
    return report


def source_rgb(root, block, frame):
    import numpy as np
    from PIL import Image
    check(frame.get("state", "permitted") == "permitted" and not any(
        lo <= frame["source_frame_index"] <= hi for lo, hi in block.get("protected_ranges", [])), "Protected image prohibited")
    raw = bound_path(root, frame["png"]).read_bytes()
    with Image.open(io.BytesIO(raw)) as image:
        check(image.mode == "RGB", "Prepared source must be RGB")
        rgb = np.asarray(image).copy()
    source = block["source_video"]
    check(rgb.shape == (source["height_px"], source["width_px"], 3)
          and hashlib.sha256(rgb.tobytes()).hexdigest() == frame["png"]["rgb_sha256"], "Native source RGB differs")
    return rgb


def frame_key(offset, frame):
    values = (offset, frame["source_frame_index"], frame["source_pts_ticks"])
    check(all(type(v) is int and 0 <= v < 2 ** bits for v, bits in zip(values, (32, 32, 64))), "Frame key exceeds limits")
    return f"{values[0]:032b}{values[1]:032b}{values[2]:064b}"


def canvas(rgb, block, frame, baseline, candidate, offset):
    """Shared reference-centered review crop is display-only, never selector input."""
    import cv2
    import numpy as np
    image = np.zeros((HEIGHT, WIDTH, 3), np.uint8)
    sw, sh = block["source_video"]["width_px"], block["source_video"]["height_px"]
    def text(value, x, y, color=(235, 235, 235), scale=.52):
        cv2.putText(image, value, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)
    def inside(point):
        return point is not None and 0 <= point[0] < sw and 0 <= point[1] < sh
    annotation = frame.get("annotation")
    geometry = None if annotation is None else annotation.get("geometry")
    reference = None if geometry is None else geometry["center_xy_px"]
    anchor = next((p for p in (reference, candidate["center_xy_px"], baseline["center_xy_px"]) if inside(p)), None)
    size = min(128, sw, sh)
    ax, ay = anchor if anchor is not None else (sw / 2, sh / 2)
    left, top = min(max(0, int(ax - size / 2)), sw - size), min(max(0, int(ay - size / 2)), sh - size)
    text(f"{block['block_id']} | same native frame | human review pending", 12, 25, scale=.60)
    text(f"Frame {frame['source_frame_index']} | PTS {frame['source_pts_ticks']} x {block['time_base']} | interval {frame['duration_ticks']} ticks", 12, 52)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    for column, observation in enumerate((baseline, candidate)):
        x0 = column * 640
        color = (30, 150, 255) if column == 0 else (255, 210, 0)
        text("COSINE NINE: NATIVE CONTROL" if column == 0 else "SEQUENCE RESEARCH CANDIDATE", x0 + 12, 90, color, .60)
        panel = cv2.resize(bgr, (640, 360))
        crop = cv2.resize(bgr[top:top + size, left:left + size], (220, 220), interpolation=cv2.INTER_NEAREST)
        for point, point_color, marker in ((reference, (80, 255, 80), cv2.MARKER_TILTED_CROSS),
                (observation["center_xy_px"], color, cv2.MARKER_CROSS)):
            if inside(point):
                cv2.drawMarker(panel, (round(point[0] * 640 / sw), round(point[1] * 360 / sh)), point_color, marker, 15, 2)
                if left <= point[0] < left + size and top <= point[1] < top + size:
                    cv2.drawMarker(crop, (round((point[0] - left) * 220 / size), round((point[1] - top) * 220 / size)), point_color, marker, 20, 2)
        image[105:465, x0:x0 + 640] = panel
        image[480:700, x0 + 10:x0 + 230] = crop
        point = observation["center_xy_px"]
        text("MISSING / ABSTAIN" if point is None else f"Observed ({point[0]:.1f}, {point[1]:.1f}) px", x0 + 245, 500, color)
        text(f"Pool: {len(observation['candidates'])} | selected: {observation['selected_candidate_index']}", x0 + 245, 529)
        text("Reference: unlabeled" if annotation is None else f"Reference: {annotation['visibility']}", x0 + 245, 558)
        text("Reference center: unknown" if reference is None else f"Reference ({reference[0]:.1f}, {reference[1]:.1f})", x0 + 245, 587)
        text("Common crop is display-only", x0 + 245, 616)
        text("Green: accepted reference", x0 + 245, 645, (80, 255, 80))
        text("Missing / uncertainty retained", x0 + 245, 674)
    for i, bit in enumerate(frame_key(offset, frame)):
        image[KEY_TOP:HEIGHT, i * 10:(i + 1) * 10] = 255 if bit == "1" else 0
    return image


def render_block(root, entry, folder, *, provenance=None, _compact_candidates=None):
    """Render and independently decode every frame, native PTS and final interval."""
    import cv2
    import numpy as np
    from .completion_sac_references import encode_review_video, probe_encoded_video, validate_encoded_timing
    root, folder = Path(root).resolve(), Path(folder).resolve()
    check(folder.is_relative_to(root / "data/outputs") and folder != root / "data/outputs", "Review output escaped data/outputs")
    block, old, new = entry["block"], entry["baseline_observations"], entry["candidate_observations"]
    validate_observations(block, old)
    validate_observations(block, new, baseline=old, expected_pools=entry.get("expected_pools"))
    check(entry.get("candidate_pool_source") is not None, "Compact review requires a bound complete candidate pool source")
    verify_pool_source(root, entry)
    compact = [compact_observation(row) for row in new] if _compact_candidates is None else _compact_candidates
    check(len(compact) == len(new), "Compact choice census differs")
    for row, reduced in zip(new, compact, strict=True):
        check(restore_observation(reduced, row["candidates"]) == row, "Compact choice preparation differs")
    input_identity = _entry_identity(entry, compact)
    folder.mkdir(parents=True, exist_ok=False)
    began = time.perf_counter()
    write_once(folder / "started.json", {"block_sha256": canonical(block), "provenance": provenance,
        "input_identity": input_identity, "implementation": binding(root, Path(__file__)) if Path(__file__).resolve().is_relative_to(root) else None})
    try:
        frames = block["frames"]
        origin = frames[0]["source_pts_ticks"]
        schedule = [(f["source_pts_ticks"] - origin, f["duration_ticks"]) for f in frames]
        video = folder / "comparison.mp4"
        def canvases():
            for offset, (frame, a, b) in enumerate(zip(frames, old, new, strict=True)):
                yield canvas(source_rgb(root, block, frame), block, frame, a, b, offset)
        encoding = encode_review_video(video, canvases(), schedule, block["time_base"], "bt709", "bt709")
        probe = probe_encoded_video(video)
        timing = validate_encoded_timing(probe, schedule, block["time_base"], "bt709", "bt709")
        write_once(folder / "ffprobe.json", probe)
        capture = cv2.VideoCapture(str(video))
        errors, final = [], None
        try:
            for offset, (frame, a, b) in enumerate(zip(frames, old, new, strict=True)):
                ok, final = capture.read()
                check(ok and final.shape == (HEIGHT, WIDTH, 3), "Encoded review ended before final frame")
                key = "".join("1" if float(final[KEY_TOP + 8, i * 10 + 5].mean()) > 127 else "0" for i in range(128))
                check(key == frame_key(offset, frame), "Decoded native frame key differs")
                expected = canvas(source_rgb(root, block, frame), block, frame, a, b, offset)
                error = float(np.abs(final.astype(np.int16) - expected.astype(np.int16)).mean())
                check(error < 8, "Decoded overlay differs")
                errors.append(error)
            check(not capture.read()[0], "Encoded review has extra frames")
        finally:
            capture.release()
        final_path = folder / "actual_final_frame.png"
        check(cv2.imwrite(str(final_path), final), "Could not save actual final frame")
        records = [{"source_frame_index": f["source_frame_index"], "source_pts_ticks": f["source_pts_ticks"],
            "duration_ticks": f["duration_ticks"], "time_base": block["time_base"], "source_png": f["png"],
            "annotation": f.get("annotation"), "reference_role": f.get("reference_role", block["role"]),
            "baseline_observation": a, "candidate_observation": b, **t}
            for f, a, b, t in zip(frames, old, compact, timing, strict=True)]
        write_once(folder / "frame_records.json", {"block_id": block["block_id"],
            "candidate_transport": "Exact selected index/geometry plus full pool count and digest; pools retained only in bound source.",
            "candidate_pool_source": entry.get("candidate_pool_source"),
            "candidate_pool_policy": entry.get("candidate_pool_policy", "all"),
            "candidate_pool_projection": entry.get("candidate_pool_projection"), "frames": records})
        loaded = read_json(folder / "frame_records.json")["frames"]
        check(loaded == records, "Emitted review records differ")
        for original, transported in zip(new, loaded, strict=True):
            check(restore_observation(transported["candidate_observation"], original["candidates"]) == original,
                  "Emitted compact choice differs from actual candidate source")
        result = {"block_id": block["block_id"], "block_sha256": canonical(block), "video": binding(root, video),
            "actual_final_frame": binding(root, final_path), "frame_records": binding(root, folder / "frame_records.json"),
            "encoded_probe": binding(root, folder / "ffprobe.json"), "encoding": encoding,
            "decoded_frames": len(errors), "native_pts_packet_frame_duration_checks": len(timing),
            "actual_final_native_frame": frames[-1]["source_frame_index"],
            "actual_final_source_pts_ticks": frames[-1]["source_pts_ticks"],
            "actual_final_duration_ticks": frames[-1]["duration_ticks"], "time_base": block["time_base"],
            "total_duration_ticks": schedule[-1][0] + schedule[-1][1], "added_final_hold_ticks": 0,
            "all_decoded_native_keys_verified": True, "all_frame_mean_absolute_errors": errors,
            "review_color_policy": "Existing BT.601 limited-range conversion with BT.709 output tags; no new source-metadata certification.",
            "elapsed_seconds": time.perf_counter() - began, "human_visual_acceptance": None,
            "model_calls": 0, "protected_png_reads": 0, "input_identity": input_identity,
            "candidate_pools_duplicated_in_review": False}
        write_once(folder / "render_receipt.json", result)
        return result
    except BaseException as error:
        write_once(folder / "failed.json", {"error": str(error), "traceback": traceback.format_exc(),
            "elapsed_seconds": time.perf_counter() - began})
        raise


def render_review(root, entries, output_folder, *, provenance=None):
    """Fresh complete comparison directory; immutable evidence, never acceptance."""
    root = Path(root).resolve()
    output = (root / output_folder).resolve()
    check(output.is_relative_to(root / "data/outputs") and output != root / "data/outputs" and not output.exists(),
          "Use a fresh comparison directory under data/outputs")
    check(entries and len({e["block"]["block_id"] for e in entries}) == len(entries), "Empty or duplicate review contexts")
    for entry in entries:
        validate_observations(entry["block"], entry["baseline_observations"])
        validate_observations(entry["block"], entry["candidate_observations"], baseline=entry["baseline_observations"],
                              expected_pools=entry.get("expected_pools"))
    compact_choices = [[compact_observation(row) for row in entry["candidate_observations"]] for entry in entries]
    input_identities = [_entry_identity(entry, compact) for entry, compact in zip(entries, compact_choices, strict=True)]
    output.mkdir(parents=True)
    write_once(output / "started.json", {"schema_version": SCHEMA, "input_sha256": canonical(input_identities),
        "provenance": provenance, "human_visual_acceptance": None})
    try:
        results, sections = [], []
        for offset, (entry, compact) in enumerate(zip(entries, compact_choices, strict=True), 1):
            name = f"block_{offset:02d}"
            result = render_block(root, entry, output / name, provenance=provenance, _compact_candidates=compact)
            results.append(result)
            sections.append(f'<section><h2>{html.escape(result["block_id"])}</h2>'
                f'<video controls preload="metadata" src="{name}/comparison.mp4"></video>'
                f'<p>Actual final native frame: {result["actual_final_native_frame"]}. '
                f'<a href="{name}/actual_final_frame.png">Final frame</a> | '
                f'<a href="{name}/frame_records.json">All frame records</a></p></section>')
            print(f"Verified weak-response comparison {result['block_id']}: {result['decoded_frames']} frames", flush=True)
        index = output / "index.html"
        index.write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>NBA sequence comparison</title>'
            '<style>body{font:17px/1.5 system-ui;max-width:1400px;margin:32px auto;padding:0 20px}video{width:100%}</style>'
            '<h1>NBA sequence comparison</h1><p>Orange/left: cosine-nine native research control. Cyan/right: '
            'sequence candidate. Green: existing accepted reference where available. Common crops use references '
            'only for display. Complete supplied native contexts and final intervals are included. Unknown references '
            'are unscored, and missing choices remain explicit. Human trajectory and object-identity review is pending. '
            'No model adoption or ball-phase pass is claimed.</p>' + ''.join(sections) + '</html>', encoding="utf-8")
        result = {"schema_version": SCHEMA, "status": "completed", "blocks": results,
            "native_frames": sum(r["decoded_frames"] for r in results), "index": binding(root, index),
            "input_sha256": canonical(input_identities), "input_identities": input_identities, "provenance": provenance,
            "human_visual_acceptance": None, "protected_evaluation_authorized": False, "model_adopted": False}
        write_once(output / "completed.json", result)
        return result
    except BaseException as error:
        write_once(output / "failed.json", {"error": str(error), "traceback": traceback.format_exc()})
        raise
