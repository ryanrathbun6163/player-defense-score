"""Stream frozen selected points through the approved appearance encoder.

This module consumes saved selections; it never selects, fits, scores, or changes
coordinates. NFHS source pixels stay in memory and protected spans are skipped.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
from pathlib import Path
import time
import uuid

import numpy as np
from PIL import Image

from . import nba_annotations as nba
from . import nba_appearance_feature_screen as screen
from . import nba_temporal_gap_continuous_review as continuous
from . import nba_wasb_diagnostic as d
from . import wasb_development_observation as nfhs

SCHEMA = "nba_ball_distractor_emission_features/v0.1"
FEATURE_SCHEMA = "nba_ball_distractor_feature/v0.1"
EXPECTED_EMISSIONS = 3373


def crop_key(row):
    x, y = row["selected_center_xy_px"]
    return (row["candidate_id"], row["source_frame_index"], math.floor(x)-32, math.floor(y)-32)


def _sha(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def _same_video(left, right):
    return all(left.get(k) == right.get(k) for k in ("path", "sha256"))


def prepare_selection(root, selection):
    """Validate the actual producer transport and clocks before any pixels."""
    root = Path(root).resolve()
    if isinstance(selection, (str, Path)):
        path = screen._path(root, selection)
        binding = d.binding(root, path)
        selection = d.read_json(path)
    else:
        binding = {"canonical_sha256": hashlib.sha256(json.dumps(
            selection, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()}
    d.require(selection["schema_version"] == "nba_temporal_gap_continuous/v0.1", "Wrong selection producer")
    sources = selection["sources"]
    d.require(len({s["candidate_id"] for s in sources}) == len(sources), "Duplicate source")
    permitted = []
    for source in sources:
        continuous.validate_source(root, source)
        permitted.extend(r for r in source["frames"] if r["decision"] != "withheld")
    d.require(permitted == selection["frames"], "Global and per-source selections differ")
    rows = [r for r in permitted if r["selected_center_xy_px"] is not None]
    d.require(len(rows) == EXPECTED_EMISSIONS, "Frozen emitted-point census differs")
    d.require(len({(r["candidate_id"], r["source_frame_index"]) for r in rows}) == len(rows),
              "Duplicate emitted source frame")
    return sources, rows, binding


def _cached(root, entry, key, row, source):
    """Verify either a bound original screen feature or a new feature record."""
    d.require(_same_video(entry["source_video"], source["source_video"])
              and entry["source_pts_ticks"] == row["source_pts_ticks"], "Cached source/PTS differs")
    record = d.read_json(d.bound(root, entry["feature"]))
    for name in ("crop64", "input224"):
        d.require(record[name] == entry[name], "Cached image binding differs")
        d.bound(root, entry[name])
    case = record.get("case", {})
    cid = record.get("source_id", case.get("continuous_source_id"))
    index = record.get("source_frame_index", case.get("source_frame_index"))
    ticks = record.get("source_pts_ticks", case.get("source_pts_ticks"))
    video = record.get("source_video", case.get("source_video", {}))
    rgb = record.get("source_rgb_sha256", case.get("raw_png", {}).get("rgb_sha256"))
    center = record.get("center_xy_px", case.get("saved_center_xy_px"))
    d.require(cid == key[0] and index == key[1] and ticks == row["source_pts_ticks"]
              and _same_video(video, source["source_video"]) and rgb == entry["source_rgb_sha256"]
              and isinstance(rgb, str) and len(rgb) == 64, "Cached producer source identity differs")
    d.require(center is not None and (cid, index, math.floor(center[0])-32, math.floor(center[1])-32) == key,
              "Cached producer crop differs")
    if "crop_key" in record:
        d.require(record["crop_key"] == list(key), "Cached feature crop key differs")
    if source["kind"] == "nba":
        d.require(rgb == row["source_frame"]["png"]["rgb_sha256"], "Cached NBA source pixels differ")
    raw = np.asarray(record["raw_cls_float32"], dtype=np.float32)
    unit = screen.normalize_feature(raw)
    d.require(np.array_equal(raw, np.asarray(entry["raw_cls_float32"], dtype=np.float32))
              and _sha(raw) == record["raw_cls_sha256"]
              and _sha(unit) == record["normalized_float64_sha256"], "Cached raw/normalized feature differs")
    return record["raw_cls_float32"]


def _images(root, source, needed, resources):
    """Yield only needed images; release each permitted NFHS decoder promptly."""
    by_index = {r["source_frame_index"]: r for r in needed}
    if source["kind"] == "nba":
        for index, row in by_index.items():
            raw = nba.read_verified_png(row["source_frame"], source["source_video"], root)
            resources["nba_png_reads"] += 1
            with Image.open(io.BytesIO(raw)) as image:
                yield index, image.convert("RGB"), row["source_frame"]["png"]
        return
    possession = source["possession"]
    permitted = possession["visible_segments"]
    d.require(all(any(a <= i <= b for a, b in permitted)
                  and not any(a <= i <= b for a, b in source["protected_ranges"]) for i in by_index),
              "Requested NFHS frame is protected or outside permitted spans")
    for span in permitted:
        wanted = {i for i in by_index if span[0] <= i <= span[1]}
        if not wanted:
            continue
        resources["nfhs_requested_segments"].append({"source_id": source["candidate_id"], "range_inclusive": span})
        decoder = iter(nfhs.decode_segment(root, possession, span))
        observed = set()
        try:
            for index, pixels in decoder:
                resources["nfhs_decoded_frames"] += 1
                d.require(span[0] <= index <= span[1]
                          and not any(a <= index <= b for a, b in source["protected_ranges"]),
                          "NFHS decoder yielded outside permitted span")
                if index in wanted:
                    d.require(index not in observed, "Duplicate decoded source frame")
                    observed.add(index)
                    yield index, Image.fromarray(pixels[:, :, ::-1]), None
            d.require(observed == wanted, "Missing requested NFHS source frame")
        finally:
            decoder.close()


def extract(root, selection, model, cache, output_dir, context=None, progress=None):
    """Return raw features by ``source:frame``, updated exact-crop cache, manifest.

    ``model`` is the already approved/eval encoder used by screen.encode. Cache
    keys are (source, frame, floor(x)-32, floor(y)-32); cached evidence is checked
    before reuse. A protocol binding may be supplied as ``context``. Per-feature
    files survive interruptions; a later call verifies and resumes them.
    """
    root = Path(root).resolve(); output = screen._path(root, output_dir)
    sources, rows, selection_binding = prepare_selection(root, selection)
    if context is not None:
        d.bound(root, context)
    identity = {"schema_version": SCHEMA, "selection": selection_binding, "context": context,
                "implementation_sha256": d.digest(Path(__file__)), "emissions": len(rows)}
    d.write_once(output / "identity.json", identity)
    attempt = output / "attempts" / uuid.uuid4().hex
    resources = {"emissions_completed": 0, "cache_hits": 0, "resumed_features": 0,
                 "encoder_attempts": 0, "encoder_calls": 0, "nba_png_reads": 0, "nfhs_decoded_frames": 0,
                 "nfhs_requested_segments": []}
    d.write_once(attempt / "started.json", {"identity": identity, "started_at_utc": d.stamp()})
    began = time.monotonic(); values = {}; artifacts = {}

    def feature_path(key):
        token = hashlib.sha256(json.dumps(list(key), separators=(",", ":")).encode()).hexdigest()[:24]
        return output / "features" / (token + ".json")

    def finish(row, entry, source):
        key = crop_key(row); raw = _cached(root, entry, key, row, source)
        emission_id = f"{key[0]}:{key[1]}"
        values[emission_id] = raw
        artifacts[emission_id] = {"emission_id": emission_id, "source_id": key[0], "source_frame_index": key[1],
            "source_pts_ticks": row["source_pts_ticks"], "center_xy_px": row["selected_center_xy_px"],
            "selected_provenance_id": row["selected_provenance_id"], "decision": row["decision"],
            "crop_key": list(key), "feature": entry["feature"], "crop64": entry["crop64"], "input224": entry["input224"]}
        resources["emissions_completed"] += 1
        if resources["emissions_completed"] % 50 == 0 or resources["emissions_completed"] == len(rows):
            snapshot = {**resources, "elapsed_seconds": time.monotonic()-began}
            d.write_once(attempt / f"progress_{resources['emissions_completed']:04d}.json", snapshot)
            if progress is not None:
                progress(snapshot)

    try:
        for source in sources:
            pending = []
            for row in (r for r in rows if r["candidate_id"] == source["candidate_id"]):
                key = crop_key(row); path = feature_path(key)
                if key not in cache and path.exists():
                    record = d.read_json(path)
                    d.require(record["schema_version"] == FEATURE_SCHEMA and record["context"] == context,
                              "Resume feature context differs")
                    cache[key] = {k: record[k] for k in ("raw_cls_float32", "source_pts_ticks", "source_rgb_sha256",
                                                        "source_video", "crop64", "input224")}
                    cache[key]["feature"] = d.binding(root, path)
                    resources["resumed_features"] += 1
                if key in cache:
                    resources["cache_hits"] += 1; finish(row, cache[key], source)
                else:
                    pending.append(row)
            by_index = {r["source_frame_index"]: r for r in pending}
            for index, image, png in _images(root, source, pending, resources):
                row = by_index[index]; key = crop_key(row); path = feature_path(key)
                native, model_input, chw = screen.crop_and_preprocess(image, row["selected_center_xy_px"])
                resources["encoder_attempts"] += 1
                raw = screen.encode(model, chw); resources["encoder_calls"] += 1
                unit = screen.normalize_feature(raw)
                record = {"schema_version": FEATURE_SCHEMA, "context": context, "source_id": key[0],
                    "source_frame_index": index, "source_pts_ticks": row["source_pts_ticks"],
                    "source_video": source["source_video"], "source_png": png,
                    "source_rgb_sha256": hashlib.sha256(image.tobytes()).hexdigest(),
                    "center_xy_px": row["selected_center_xy_px"], "crop_key": list(key),
                    "raw_cls_float32": raw.tolist(), "raw_cls_sha256": _sha(raw),
                    "normalized_float64_sha256": _sha(unit), "input_chw_float32_sha256": _sha(chw),
                    "crop64": screen._png(root, path.with_name(path.stem+"_crop64.png"), native),
                    "input224": screen._png(root, path.with_name(path.stem+"_input224.png"), model_input)}
                d.write_once(path, record)
                cache[key] = {k: record[k] for k in ("raw_cls_float32", "source_pts_ticks", "source_rgb_sha256",
                                                    "source_video", "crop64", "input224")}
                cache[key]["feature"] = d.binding(root, path)
                finish(row, cache[key], source)
        ordered = [artifacts[f"{r['candidate_id']}:{r['source_frame_index']}"] for r in rows]
        manifest = {"schema_version": SCHEMA, "identity": identity, "emissions": ordered,
                    "emission_count": len(ordered), "tracking_outputs_changed": False, "fitting_performed": False}
        d.require(len(values) == len(rows), "Incomplete emitted feature census")
        d.write_once(output / "manifest.json", manifest)
        d.write_once(attempt / "completion.json", {"status": "completed", "resources": resources,
                     "elapsed_seconds": time.monotonic()-began, "manifest": d.binding(root, output / "manifest.json")})
        return {"features_by_emission_id": values, "cache": cache, "manifest": d.binding(root, output / "manifest.json"),
                "resources": resources, "attempt": str(attempt.relative_to(root)).replace("\\", "/")}
    except Exception as exc:
        d.write_once(attempt / "failure.json", {"status": "failed", "error_type": type(exc).__name__, "error": str(exc),
                     "resources": resources, "elapsed_seconds": time.monotonic()-began})
        raise
