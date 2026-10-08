"""Fixed, pure same-frame RF/YOLO box corroboration; no files or models.

Support is geometric agreement, never an object identity verdict. Input content
digests bind the in-memory typed views; the later execution inventory must bind
their original files separately. A self digest detects corruption, not forgery.
"""
from __future__ import annotations

import copy
import math

from .detections import BallDetectionRun
from .development_experiments import canonical_sha256, closed, require_digest

ARM = "rfdetr_yolo_box_corroborated_top_one"
SCHEMA = "ball_crop_cross_detector_corroboration_observations/v0.1"
THRESHOLD, IOU_THRESHOLD = .01, .5
PAIR_CHECK_INTERVAL = 256
SCORE_SEMANTICS = (
    "Unchanged original RF confidence, not calibrated probability; same-frame "
    "box agreement is correlated evidence, not semantic ball identity; missing "
    "output is no accepted observation, not a visibility label."
)
CONFIG = {"arm": ARM, "confidence_threshold": THRESHOLD, "iou_threshold": IOU_THRESHOLD}
FRAME_FIELDS = {"frame_index", "horizon_start", "horizon_end", "emitted_candidate_indices",
                "supported_candidate_indices", "emitted_candidates", "candidate_decisions",
                "decision_reason", "output_state"}
DECISION_FIELDS = {"candidate_index", "reference", "inclusion", "maximum_iou",
                   "witness_yolo_original_index", "supporter_count", "supported", "disposition"}


def _tick(progress):
    if progress is not None:
        progress()


def _box(box):
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        raise ValueError("A source-pixel xyxy rectangle is required")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in box):
        raise ValueError("Rectangle coordinates must be finite numbers")
    try:
        x1, y1, x2, y2 = (float(v) for v in box)
    except (OverflowError, ValueError) as error:
        raise ValueError("Rectangle cannot be represented in binary64") from error
    if (not all(math.isfinite(v) for v in (x1, y1, x2, y2))
            or x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1):
        raise ValueError("Invalid source rectangle")
    area = (x2 - x1) * (y2 - y1)
    if not math.isfinite(area) or area <= 0:
        raise ValueError("Rectangle area must be finite and positive in binary64")
    return (x1, y1, x2, y2), area


def box_iou(rf_box, yolo_box):
    """Declared binary64 operation order; no +1 convention or tolerance."""
    r, area_r = _box(rf_box)
    y, area_y = _box(yolo_box)
    intersection = max(0.0, min(r[2], y[2]) - max(r[0], y[0])) * max(
        0.0, min(r[3], y[3]) - max(r[1], y[1]))
    union = (area_r + area_y) - intersection
    if not math.isfinite(union) or union <= 0:
        raise ValueError("Pair union must be finite and positive")
    value = intersection / union
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Invalid binary64 box IoU")
    return value


def _validated_inputs(rf_run, yolo_run, progress=None):
    """Check the entire inventory before any frame can be emitted."""
    _tick(progress)
    checked = []
    for detector, run, model_name, package in (
            ("rfdetr", rf_run, "RF-DETR Medium COCO", "rfdetr"),
            ("yolo", yolo_run, "Ultralytics YOLO11x Detect COCO", "ultralytics")):
        if not isinstance(run, BallDetectionRun):
            raise ValueError("Corroboration requires two typed BallDetectionRun inputs")
        original = run.to_dict()
        parsed = BallDetectionRun.from_mapping(original)
        if original != parsed.to_dict():
            raise ValueError("Input provenance must not require normalization")
        model = parsed.model_provenance
        if (model.model_name != model_name or model.package_name != package
                or model.target_class_id != 37 or model.target_class_name != "sports ball"
                or model.tiling_enabled is not True or model.export_confidence_floor > THRESHOLD):
            raise ValueError(f"Wrong {detector} crop detector namespace or export contract")
        count = 0
        for frame in parsed.frames:
            _tick(progress)
            if frame.inference_status != "completed" or frame.detections is None:
                raise ValueError("Every detector frame must have completed successfully")
            previous = math.inf
            for candidate in frame.detections:
                if candidate.confidence > previous:
                    raise ValueError("Original crop confidence ordering changed")
                previous = candidate.confidence
                _box(candidate.bbox_xyxy_px)
                count += 1
                if count % PAIR_CHECK_INTERVAL == 0:
                    _tick(progress)
        checked.append(parsed)
    rf, yolo = checked
    if (rf.source_video != yolo.source_video or rf.window != yolo.window
            or rf.possession_id != yolo.possession_id or rf.annotation_set_id != yolo.annotation_set_id
            or tuple(f.frame_index for f in rf.frames) != tuple(f.frame_index for f in yolo.frames)):
        raise ValueError("Detector source metadata, window, possession or exact frames differ")
    # Finite positive areas plus a finite maximum sum guarantee valid pair unions.
    # This also validates excluded candidates before any streamed output exists.
    for r, y in zip(rf.frames, yolo.frames):
        largest_r = max((_box(c.bbox_xyxy_px)[1] for c in r.detections), default=0.0)
        largest_y = max((_box(c.bbox_xyxy_px)[1] for c in y.detections), default=0.0)
        if not math.isfinite(largest_r + largest_y):
            raise ValueError("Source frame contains an overflowing pair-area sum")
        _tick(progress)
    return rf, yolo


def _bindings(rf, yolo):
    return {name: {"detector": name, "detection_run_id": run.detection_run_id,
                   "content_sha256": canonical_sha256(run.to_dict()),
                   "model_provenance": run.model_provenance.to_dict()}
            for name, run in (("rfdetr", rf), ("yolo", yolo))}


def _reference(binding, frame_index, candidate_index):
    return {"detector": "rfdetr", "input_binding": binding["rfdetr"]["content_sha256"],
            "source_frame": frame_index, "original_candidate_index": candidate_index}


def _iter_frames(rf, yolo, binding, progress):
    pair_count = 0
    for r_frame, y_frame in zip(rf.frames, yolo.frames):
        _tick(progress)
        qualifying_yolo = tuple(c for c in y_frame.detections if c.confidence >= THRESHOLD)
        decisions = []
        for candidate in r_frame.detections:
            maximum, witness, supporters = None, None, 0
            included = candidate.confidence >= THRESHOLD
            if included:
                for y in qualifying_yolo:
                    value = box_iou(candidate.bbox_xyxy_px, y.bbox_xyxy_px)
                    if (maximum is None or value > maximum
                            or (value == maximum and y.candidate_index < witness)):
                        maximum, witness = value, y.candidate_index
                    if value >= IOU_THRESHOLD:
                        supporters += 1
                    pair_count += 1
                    if pair_count % PAIR_CHECK_INTERVAL == 0:
                        _tick(progress)
            decisions.append({"candidate_index": candidate.candidate_index,
                              "reference": _reference(binding, r_frame.frame_index, candidate.candidate_index),
                              "inclusion": included, "maximum_iou": maximum,
                              "witness_yolo_original_index": witness, "supporter_count": supporters,
                              "supported": supporters > 0, "disposition": "pending"})
        supported = [d["candidate_index"] for d in decisions if d["supported"]]
        winner = min((r_frame.detections[i] for i in supported),
                     key=lambda c: (-c.confidence, c.candidate_index), default=None)
        emitted = [] if winner is None else [winner.candidate_index]
        for decision in decisions:
            decision["disposition"] = (
                "below_threshold" if not decision["inclusion"] else
                "no_yolo_box_support" if not decision["supported"] else
                "emitted" if decision["candidate_index"] in emitted else "supported_not_emitted")
        yield {"frame_index": r_frame.frame_index, "horizon_start": r_frame.frame_index,
               "horizon_end": r_frame.frame_index, "emitted_candidate_indices": emitted,
               "supported_candidate_indices": supported,
               "emitted_candidates": [] if winner is None else [winner.to_dict()],
               "candidate_decisions": decisions,
               "decision_reason": "supported_rf_candidate" if emitted else "no_supported_rf_candidate",
               "output_state": "tentative_observation" if emitted else "no_accepted_observation"}


def iter_selected_frames(rf_run, yolo_run, progress=None):
    """Yield linear-size traces, with at most 256 pair calculations between checks.

    All inputs are checked before the first yield. A consumer must still seal the
    complete window and externally bind it before treating shards as evidence.
    Callback exceptions propagate; no failed partial package is returned.
    """
    rf, yolo = _validated_inputs(rf_run, yolo_run, progress)
    yield from _iter_frames(rf, yolo, _bindings(rf, yolo), progress)


def _header(rf, yolo, code_commit, binding):
    require_digest(code_commit, "corroboration selector commit", 40)
    return {"schema_version": SCHEMA, "variant_id": ARM + "_" + canonical_sha256(CONFIG)[:16],
            "config": dict(CONFIG), "ranking_code_commit": code_commit,
            "input_bindings": binding,
            "input_candidate_content_sha256": binding["rfdetr"]["content_sha256"],
            "source_video": rf.source_video.to_dict(), "window": rf.window.to_dict(),
            "possession_id": rf.possession_id, "annotation_set_id": rf.annotation_set_id,
            "score_semantics": SCORE_SEMANTICS, "selected_operating_point": None, "quality_gate": None}


def select_candidates(rf_run, yolo_run, code_commit, progress=None):
    """Return the one frozen arm with complete, original-geometry audit records."""
    require_digest(code_commit, "corroboration selector commit", 40)
    rf, yolo = _validated_inputs(rf_run, yolo_run, progress)
    binding = _bindings(rf, yolo)
    result = {**_header(rf, yolo, code_commit, binding),
              "frames": list(_iter_frames(rf, yolo, binding, progress))}
    _tick(progress)
    result["content_sha256"] = canonical_sha256(result)
    return result


def _indices(value, label):
    if (not isinstance(value, list) or any(type(i) is not int or i < 0 for i in value)
            or value != sorted(set(value))):
        raise ValueError(f"Invalid {label} original indices")
    return value


def validate_observations(value, rf_run, yolo_run):
    """Validate saved structure/bindings without rerunning selection or IoU pairs.

    Maximum/witness/support count are structurally reconciled, not independently
    recomputed mathematical certificates. Later real evaluation must additionally
    verify the externally sealed byte/content binding; this self digest is not
    authentication. This function never invokes any historic selector validator.
    """
    rf, yolo = _validated_inputs(rf_run, yolo_run)
    if not isinstance(value, dict):
        raise ValueError("Corroboration observations must be an object")
    header = _header(rf, yolo, value.get("ranking_code_commit"), _bindings(rf, yolo))
    closed(value, set(header) | {"frames", "content_sha256"}, "corroboration observations")
    for key, expected in header.items():
        if canonical_sha256(value[key]) != canonical_sha256(expected):
            raise ValueError(f"Corroboration binding or fixed header differs: {key}")
    require_digest(value["content_sha256"], "corroboration content")
    if value["content_sha256"] != canonical_sha256({k: v for k, v in value.items() if k != "content_sha256"}):
        raise ValueError("Corroboration self digest changed")
    if not isinstance(value["frames"], list) or len(value["frames"]) != len(rf.frames):
        raise ValueError("Incomplete corroboration frame window")
    for saved, r_frame, y_frame in zip(value["frames"], rf.frames, yolo.frames):
        closed(saved, FRAME_FIELDS, "corroboration frame")
        if any(type(saved[key]) is not int or saved[key] != r_frame.frame_index
               for key in ("frame_index", "horizon_start", "horizon_end")):
            raise ValueError("Corroboration must retain exact same-frame references")
        emitted = _indices(saved["emitted_candidate_indices"], "emitted")
        supported = _indices(saved["supported_candidate_indices"], "supported")
        qualifying_yolo = {c.candidate_index for c in y_frame.detections if c.confidence >= THRESHOLD}
        decisions = saved["candidate_decisions"]
        if not isinstance(decisions, list) or len(decisions) != len(r_frame.detections):
            raise ValueError("Decisions must cover every original RF candidate")
        derived_supported = []
        for decision, candidate in zip(decisions, r_frame.detections):
            closed(decision, DECISION_FIELDS, "RF corroboration decision")
            included = candidate.confidence >= THRESHOLD
            if (type(decision["candidate_index"]) is not int
                    or decision["candidate_index"] != candidate.candidate_index
                    or canonical_sha256(decision["reference"]) != canonical_sha256(
                        _reference(header["input_bindings"], r_frame.frame_index, candidate.candidate_index))
                    or type(decision["inclusion"]) is not bool or decision["inclusion"] != included
                    or type(decision["supported"]) is not bool):
                raise ValueError("Corroboration candidate namespace, index or inclusion changed")
            count, maximum, witness = (decision[k] for k in
                                       ("supporter_count", "maximum_iou", "witness_yolo_original_index"))
            if type(count) is not int or not 0 <= count <= len(qualifying_yolo):
                raise ValueError("Invalid supporting YOLO count")
            if not included or not qualifying_yolo:
                if maximum is not None or witness is not None or count != 0:
                    raise ValueError("Excluded/empty pairs require null maximum and witness")
            elif (isinstance(maximum, bool) or not isinstance(maximum, (int, float))
                  or not math.isfinite(maximum) or not 0 <= maximum <= 1
                  or type(witness) is not int or witness not in qualifying_yolo
                  or (maximum >= IOU_THRESHOLD) != (count > 0)):
                raise ValueError("Inconsistent maximum, witness or support count")
            is_supported = included and count > 0
            if decision["supported"] != is_supported:
                raise ValueError("Support decision differs from witness/count")
            if is_supported:
                derived_supported.append(candidate.candidate_index)
            disposition = ("below_threshold" if not included else "no_yolo_box_support" if not is_supported
                           else "emitted" if candidate.candidate_index in emitted else "supported_not_emitted")
            if decision["disposition"] != disposition:
                raise ValueError("Incorrect candidate emission/rejection reason")
        if supported != derived_supported:
            raise ValueError("Supported candidate list differs from complete audit")
        winner = min((r_frame.detections[i] for i in supported),
                     key=lambda c: (-c.confidence, c.candidate_index), default=None)
        expected_emitted = [] if winner is None else [winner.candidate_index]
        if (emitted != expected_emitted
                or canonical_sha256(saved["emitted_candidates"]) != canonical_sha256(
                    [] if winner is None else [winner.to_dict()])
                or saved["decision_reason"] != ("supported_rf_candidate" if emitted else "no_supported_rf_candidate")
                or saved["output_state"] != ("tentative_observation" if emitted else "no_accepted_observation")):
            raise ValueError("Saved corroboration output differs from supported RF confidence order")
    return copy.deepcopy(CONFIG)
