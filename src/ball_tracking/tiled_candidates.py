"""Fixed-view geometry and auditable tiled candidates; no labels or inference."""
from __future__ import annotations

import math
from dataclasses import replace

from .detections import BallDetection, BallDetectionRun, DetectionFrame, ModelProvenance
from .development_experiments import canonical_sha256, closed

VIEWS = (
    ("tl", (0, 0, 1152, 648)), ("tr", (768, 0, 1920, 648)),
    ("bl", (0, 432, 1152, 1080)), ("br", (768, 432, 1920, 1080)),
)
SCHEMA = "ball_tiled_candidates/v0.1"
VIEW_FIELDS = {"view", "candidates", "elapsed_seconds", "cuda_peak_allocated_bytes"}


def crop_views():
    return [{"view_id": name, "ordinal": i, "xyxy_half_open_px": list(rect)}
            for i, (name, rect) in enumerate(VIEWS)]


def finite_nonnegative(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"Invalid {label}")
    return value


def validate_local(candidates, view, source, model):
    if not isinstance(candidates, list):
        raise ValueError("Crop candidates must be an array")
    x0, y0, x1, y1 = view["xyxy_half_open_px"]
    crop_source = replace(source, width_px=x1 - x0, height_px=y1 - y0)
    return [BallDetection.from_mapping(c, label="crop candidate", expected_candidate_index=i,
                                      source_video=crop_source, model_provenance=model)
            for i, c in enumerate(candidates)]


def combine_views(records, source, model):
    """Translate every candidate, preserving duplicates and deterministic ties."""
    if (source.width_px, source.height_px) != (1920, 1080):
        raise ValueError("Approved crops require 1920x1080 source frames")
    if not isinstance(records, list) or len(records) != 4:
        raise ValueError("Exactly four declared crop views required")
    mapped = []
    for record, view in zip(records, crop_views()):
        r = closed(record, VIEW_FIELDS, "crop result")
        if canonical_sha256(r["view"]) != canonical_sha256(view):
            raise ValueError("Crop identity/order differs from fixed grid")
        finite_nonnegative(r["elapsed_seconds"], "inference duration")
        if type(r["cuda_peak_allocated_bytes"]) is not int or r["cuda_peak_allocated_bytes"] < 0:
            raise ValueError("Invalid CUDA peak allocation")
        x0, y0, _, _ = view["xyxy_half_open_px"]
        for candidate in validate_local(r["candidates"], view, source, model):
            x1, y1, x2, y2 = candidate.bbox_xyxy_px
            global_candidate = replace(candidate, bbox_xyxy_px=(x1+x0, y1+y0, x2+x0, y2+y0),
                                       center_xy_px=(candidate.center_xy_px[0]+x0, candidate.center_xy_px[1]+y0))
            mapped.append((global_candidate, view["ordinal"], candidate.candidate_index))
    mapped.sort(key=lambda item: (-item[0].confidence, item[0].bbox_xyxy_px, item[1], item[2]))
    result = []
    for i, (candidate, ordinal, local_index) in enumerate(mapped):
        candidate = replace(candidate, candidate_index=i)
        checked = BallDetection.from_mapping(candidate.to_dict(), label="global candidate", expected_candidate_index=i,
                                             source_video=source, model_provenance=model)
        result.append({"detection": checked.to_dict(), "view_ordinal": ordinal, "local_candidate_index": local_index})
    return result


def make_frame(index, records, source, model):
    if type(index) is not int or not 0 <= index < source.frame_count:
        raise ValueError("Invalid source frame index")
    return {"frame_index": index, "views": records, "candidates": combine_views(records, source, model),
            "model_calls": 4, "elapsed_seconds": sum(r["elapsed_seconds"] for r in records)}


def validate_output(value, expected_header, raw):
    record = closed(value, {"schema_version", "header", "frames", "content_sha256"}, "tiled output")
    if record["schema_version"] != SCHEMA or record["header"] != expected_header:
        raise ValueError("Tiled output provenance mismatch")
    if record["content_sha256"] != canonical_sha256({"header": record["header"], "frames": record["frames"]}):
        raise ValueError("Tiled output content digest mismatch")
    model = ModelProvenance.from_mapping(expected_header["per_view_model_provenance"])
    if not isinstance(record["frames"], list) or len(record["frames"]) != len(raw.frames):
        raise ValueError("Incomplete tiled output")
    for frame, source_frame in zip(record["frames"], raw.frames):
        f = closed(frame, {"frame_index", "views", "candidates", "model_calls", "elapsed_seconds"}, "tiled frame")
        if (type(f["frame_index"]) is not int or f["frame_index"] != source_frame.frame_index
                or canonical_sha256(f) != canonical_sha256(make_frame(f["frame_index"], f["views"], raw.source_video, model))):
            raise ValueError("Tiled frame geometry/order/completeness mismatch")
    return record


def make_output(header, frames):
    return {"schema_version": SCHEMA, "header": header, "frames": frames,
            "content_sha256": canonical_sha256({"header": header, "frames": frames})}


def candidate_run(raw, output):
    """Evaluator-only typed view, never serialized as a raw image-only run."""
    model = ModelProvenance.from_mapping(output["header"]["per_view_model_provenance"])
    model = replace(model, tiling_enabled=True,
                    postprocessing_description="Four fixed overlapping crop union; global coordinate translation; all duplicates retained; no temporal filtering")
    frames = tuple(DetectionFrame(frame["frame_index"], "completed", None,
                                  tuple(BallDetection.from_mapping(c["detection"], label="global candidate",
                                        expected_candidate_index=i, source_video=raw.source_video, model_provenance=model)
                                        for i, c in enumerate(frame["candidates"]))) for frame in output["frames"])
    return BallDetectionRun.from_mapping(replace(raw, model_provenance=model, frames=frames).to_dict())


def select_run(run, selector, threshold):
    if selector not in {"raw", "top_one"}:
        raise ValueError("Unknown selector")
    if selector == "raw":
        return run
    frames = []
    for frame in run.frames:
        accepted = [d for d in frame.detections if d.confidence >= threshold]
        selected = min(accepted, key=lambda d: (-d.confidence, d.candidate_index)) if accepted else None
        # Keep original candidate indices for score/review audit; evaluator accepts sparse selected indices.
        frames.append(replace(frame, detections=() if selected is None else (selected,)))
    return replace(run, frames=tuple(frames))
