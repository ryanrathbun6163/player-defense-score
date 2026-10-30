"""Causal crop ranking with one bounded cost from frozen observed player boxes.

Detector confidence remains immutable. Context utility and path scores are
uncalibrated heuristics; minimizing rectangles do not identify a ball handler.
This module performs no file access and accepts no annotation payload.
"""
from __future__ import annotations

import copy
import math
from dataclasses import asdict, dataclass

from . import crop_motion_factorial as motion
from .detections import BallDetectionRun
from .development_experiments import canonical_sha256, closed, portable_path, require_digest
from .temporal_association import THRESHOLDS

ARMS = tuple(arm + "_player_context" for arm in motion.ARMS[3:])
STEPS = dict(zip(ARMS, ((.01, .01), (.01, .03), (.03, .01), (.03, .03))))
SCHEMA = "ball_crop_player_context_observations/v0.1"
CONTEXT_SCHEMA = "ball_observed_player_context_inputs/v0.1"
HISTORY, CAP, GAP, PENALTY, CONTEXT_COEFFICIENT = 5, 20, 2, .25, .25
INTEGER_FIELDS = ("frame_index", "track_id", "duplicate_detection_count")
FLOAT_FIELDS = ("timestamp_sec", "confidence", "x1", "y1", "x2", "y2", "floor_x", "floor_y")
COLUMNS = ("frame_index", "timestamp_sec", "track_id", "confidence", "x1", "y1", "x2", "y2",
           "floor_x", "floor_y", "team_label", "segment_id", "baseline_player_id", "player_id",
           "reconciled_team", "identity_status", "identity_review_reason", "duplicate_detection_count",
           "source_track_ids", "source_segment_ids")
WINDOW_FIELDS = {
    "window_id", "possession_id", "purpose", "start_frame_index", "end_frame_index", "source_video",
    "source_video_binding_status", "player_tracks", "columns", "per_frame_box_counts", "box_rows",
    "frames_with_any_box", "frames_with_ten_boxes", "missing_box_slots_relative_to_ten",
    "rows_collapsing_duplicate_detections", "raw_and_reconciled_team_disagreements",
    "selected_rows_sha256", "prior_feasibility_selected_rows_sha256", "rows",
    "original_csv_records", "original_csv_records_sha256",
}


@dataclass(frozen=True)
class RankingConfig:
    arm: str
    confidence_threshold: float
    candidate_cap: int = CAP
    edge_step: float | None = None
    cost_step: float | None = None
    context_coefficient: float = CONTEXT_COEFFICIENT

    def __post_init__(self):
        if self.arm not in ARMS:
            raise ValueError("Unknown player-context ranking arm")
        if (isinstance(self.confidence_threshold, bool)
                or not isinstance(self.confidence_threshold, (int, float))
                or self.confidence_threshold not in THRESHOLDS):
            raise ValueError("Undeclared confidence threshold")
        if (type(self.candidate_cap) is not int or self.candidate_cap != CAP
                or any(isinstance(v, bool) or not isinstance(v, (int, float))
                       for v in (self.edge_step, self.cost_step, self.context_coefficient))
                or (self.edge_step, self.cost_step) != STEPS[self.arm]
                or self.context_coefficient != CONTEXT_COEFFICIENT):
            raise ValueError("Settings differ from the approved context arm")

    def to_dict(self):
        return asdict(self)

    @property
    def variant_id(self):
        return self.arm + "_" + canonical_sha256(self.to_dict())[:16]

    @classmethod
    def from_mapping(cls, value):
        return cls(**closed(value, set(cls.__dataclass_fields__), "context ranking config"))


def experiment_grid():
    return tuple(RankingConfig(arm, threshold, CAP, *STEPS[arm])
                 for threshold in THRESHOLDS for arm in ARMS)


def paired_control_config(config):
    config = RankingConfig.from_mapping(config.to_dict())
    return motion.RankingConfig(config.arm.removesuffix("_player_context"), config.confidence_threshold,
                                config.candidate_cap, config.edge_step, config.cost_step)


def _finite(value, label):
    try:
        finite = not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError(f"Nonfinite or nonnumeric {label}")
    return value


def _rows(value, frame=None, fps=None):
    if not isinstance(value, (list, tuple)):
        raise ValueError("Observed player rows must be an explicit sequence")
    result, players = [], set()
    for source in value:
        row = closed(source, set(COLUMNS), "observed player row")
        for key in INTEGER_FIELDS:
            if type(row[key]) is not int or row[key] < (1 if key == "duplicate_detection_count" else 0):
                raise ValueError(f"Invalid player {key}")
        for key in FLOAT_FIELDS:
            _finite(row[key], key)
        for key in set(COLUMNS) - set(INTEGER_FIELDS) - set(FLOAT_FIELDS):
            if not isinstance(row[key], str):
                raise ValueError(f"Invalid player string {key}")
        width, height = row["x2"] - row["x1"], row["y2"] - row["y1"]
        if (not math.isfinite(width) or not math.isfinite(height) or width <= 0 or height <= 0
                or not 0 <= row["confidence"] <= 1 or row["timestamp_sec"] < 0
                or not row["player_id"].strip() or row["identity_status"] != "active"):
            raise ValueError("Malformed observed player geometry or identity")
        if frame is not None and row["frame_index"] != frame:
            raise ValueError("Player row belongs to another frame")
        if fps is not None and abs(row["timestamp_sec"] - row["frame_index"] / fps) >= 1e-8:
            raise ValueError("Player timestamp differs from source frame")
        if row["player_id"] in players:
            raise ValueError("Duplicate observed player ID in frame")
        players.add(row["player_id"])
        result.append(copy.deepcopy(row))
    return tuple(result)


def validate_context_window(snapshot_window, run):
    """Validate one unchanged snapshot window without selecting any candidate.

    Returns every inclusive frame key, including explicit empty row tuples.
    Snapshot-file/schema/hash verification belongs to the experiment wrapper.
    """
    w = closed(snapshot_window, WINDOW_FIELDS, "player context window")
    lo, hi = run.window.start_frame_index, run.window.end_frame_index
    if (type(w["start_frame_index"]) is not int or type(w["end_frame_index"]) is not int
            or (w["start_frame_index"], w["end_frame_index"]) != (lo, hi)
            or w["possession_id"] != run.possession_id
            or canonical_sha256(w["source_video"]) != canonical_sha256(run.source_video.to_dict())
            or w["purpose"] not in ("representative_evaluation", "challenge_evaluation")
            or not isinstance(w["window_id"], str) or not w["window_id"].strip()
            or not isinstance(w["source_video_binding_status"], str)
            or w["columns"] != list(COLUMNS)):
        raise ValueError("Player context source/window/column metadata differs")
    binding = closed(w["player_tracks"], {"path", "sha256"}, "player tracks binding")
    portable_path(binding["path"])
    require_digest(binding["sha256"], "player tracks")
    if not isinstance(w["rows"], list) or not isinstance(w["original_csv_records"], list):
        raise ValueError("Context rows must be arrays")
    if len(w["rows"]) != len(w["original_csv_records"]):
        raise ValueError("Original CSV and typed row counts differ")
    grouped = {f: [] for f in range(lo, hi + 1)}
    previous = lo
    for source, original in zip(w["rows"], w["original_csv_records"]):
        row = closed(source, set(COLUMNS), "observed player row")
        raw = closed(original, set(COLUMNS), "original CSV player row")
        if any(not isinstance(v, str) for v in raw.values()):
            raise ValueError("Original CSV fields must remain strings")
        rebuilt = dict(raw)
        try:
            for key in INTEGER_FIELDS:
                rebuilt[key] = int(raw[key])
            for key in FLOAT_FIELDS:
                rebuilt[key] = float(raw[key])
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("Malformed original CSV numeric field") from error
        if canonical_sha256(rebuilt) != canonical_sha256(row):
            raise ValueError("Typed row differs from original CSV fields")
        frame = row["frame_index"]
        if type(frame) is not int or frame not in grouped or frame < previous:
            raise ValueError("Out-of-window or unordered player frame")
        previous = frame
        grouped[frame].append(row)
    validated = {f: _rows(rows, f, run.source_video.fps) for f, rows in grouped.items()}
    counts = {str(f): len(rows) for f, rows in validated.items()}
    if (not isinstance(w["per_frame_box_counts"], dict)
            or any(type(n) is not int for n in w["per_frame_box_counts"].values())
            or w["per_frame_box_counts"] != counts):
        raise ValueError("Missing, extra or incorrect context frame counts")
    metrics = {"box_rows": len(w["rows"]), "frames_with_any_box": sum(n > 0 for n in counts.values()),
               "frames_with_ten_boxes": sum(n == 10 for n in counts.values()),
               "missing_box_slots_relative_to_ten": 10 * len(counts) - len(w["rows"]),
               "rows_collapsing_duplicate_detections": sum(r["duplicate_detection_count"] > 1 for r in w["rows"]),
               "raw_and_reconciled_team_disagreements": sum(r["team_label"] != r["reconciled_team"] for r in w["rows"])}
    if any(type(w[k]) is not int or w[k] != v for k, v in metrics.items()):
        raise ValueError("Player context coverage/provenance counts differ")
    for key, rows in (("selected_rows_sha256", w["rows"]),
                      ("original_csv_records_sha256", w["original_csv_records"])):
        require_digest(w[key], key)
        if w[key] != canonical_sha256(rows):
            raise ValueError("Player context row digest differs")
    if w["prior_feasibility_selected_rows_sha256"] != w["selected_rows_sha256"]:
        raise ValueError("Player context differs from frozen feasibility rows")
    return validated


def candidate_context(candidate, rows, context_coefficient=CONTEXT_COEFFICIENT):
    """Continuous per-node geometry; coefficient zero is a synthetic parity aid."""
    _finite(context_coefficient, "context coefficient")
    if context_coefficient not in (0., CONTEXT_COEFFICIENT):
        raise ValueError("Only the frozen coefficient or synthetic zero is supported")
    rows = _rows(rows)
    if len({r["frame_index"] for r in rows}) > 1:
        raise ValueError("Context must belong to one candidate frame")
    x, y = candidate.center_xy_px
    _finite(x, "candidate x"); _finite(y, "candidate y")
    if not 0 <= _finite(candidate.confidence, "original confidence") <= 1:
        raise ValueError("Original confidence outside [0,1]")
    values = []
    for row in rows:
        height = row["y2"] - row["y1"]
        distance = math.hypot(max(row["x1"] - x, 0., x - row["x2"]),
                              max(row["y1"] - y, 0., y - row["y2"]))
        normalized = distance / height
        if not math.isfinite(normalized):
            raise ValueError("Nonfinite normalized player distance")
        values.append({"player_id": row["player_id"], "track_id": row["track_id"],
                       "bbox_xyxy_px": [row[k] for k in ("x1", "y1", "x2", "y2")],
                       "distance_px": distance, "height_px": height, "normalized_distance": normalized,
                       "source_row": row})
    z = min((v["normalized_distance"] for v in values), default=None)
    minimizing = sorted((v for v in values if v["normalized_distance"] == z),
                        key=lambda v: (v["player_id"], v["track_id"]))
    fraction = 0. if z is None else z / (1. + z)
    cost = context_coefficient * fraction
    utility = candidate.confidence if cost == 0. else candidate.confidence - cost
    return {"original_confidence": candidate.confidence, "context_unavailable": not rows,
            "available_box_count": len(rows), "normalized_distance": z, "penalty_fraction": fraction,
            "context_cost": cost, "node_utility": utility, "minimizing_boxes": minimizing}


def rank_history(frames, config, diagonal, context_by_frame, context_coefficient=CONTEXT_COEFFICIENT):
    """Exact endpoint DP; own-frame context and current/past ball nodes only."""
    config = RankingConfig.from_mapping(config.to_dict())
    if not frames or len(frames) > HISTORY:
        raise ValueError("One-to-five history frames required")
    if (_finite(diagonal, "source diagonal") <= 0
            or config.edge_step * diagonal == 0 or config.cost_step * diagonal == 0):
        raise ValueError("Positive source diagonal required")
    _finite(context_coefficient, "context coefficient")
    if context_coefficient not in (0., CONTEXT_COEFFICIENT):
        raise ValueError("Only frozen context coefficient or synthetic zero allowed")
    indices = [f.frame_index for f in frames]
    if any(b != a + 1 for a, b in zip(indices, indices[1:])):
        raise ValueError("Noncontiguous history")
    if (not isinstance(context_by_frame, dict) or any(type(f) is not int for f in context_by_frame)
            or set(context_by_frame) != set(indices)):
        raise ValueError("Context keys must exactly match supplied history frames")
    context = {f: _rows(context_by_frame[f], f) for f in indices}
    t = indices[-1]
    nodes, best, edges, records, node_records = {}, {}, [], [], []
    for frame in frames:
        if frame.inference_status != "completed" or frame.detections is None:
            raise ValueError("Context ranking requires completed detector frames")
        if any(b.confidence > a.confidence for a, b in zip(frame.detections, frame.detections[1:])):
            raise ValueError("Candidate global confidence order differs")
        candidates = [c for c in frame.detections if c.confidence >= config.confidence_threshold][:CAP]
        for candidate in candidates:
            ref = (frame.frame_index, candidate.candidate_index)
            evidence = candidate_context(candidate, context[frame.frame_index], context_coefficient)
            node_records.append({"reference": list(ref), **evidence})
            utility, context_cost = evidence["node_utility"], evidence["context_cost"]
            choices = [{"score": utility, "path": [list(ref)], "confidence_sum": candidate.confidence,
                        "internal_skipped_frames": 0, "normalized_step_squared_sum": 0.,
                        "context_cost_sum": context_cost}]
            for prior, old in nodes.items():
                delta = ref[0] - prior[0]
                if not 1 <= delta <= GAP + 1:
                    continue
                distance = math.dist(old.center_xy_px, candidate.center_xy_px)
                if distance > config.edge_step * diagonal * delta:
                    continue
                normalized = distance / (config.cost_step * diagonal * delta)
                gap_cost, motion_cost = PENALTY * (delta - 1), PENALTY * normalized ** 2
                parent = best[prior]
                edges.append({"from": list(prior), "to": list(ref), "elapsed_frames": delta,
                              "distance_px": distance, "normalized_step": normalized,
                              "skipped_frame_penalty": gap_cost, "motion_penalty": motion_cost})
                choices.append({"score": ((parent["score"] + utility) - gap_cost) - motion_cost,
                                "path": [*parent["path"], list(ref)],
                                "confidence_sum": parent["confidence_sum"] + candidate.confidence,
                                "internal_skipped_frames": parent["internal_skipped_frames"] + delta - 1,
                                "normalized_step_squared_sum": parent["normalized_step_squared_sum"] + normalized ** 2,
                                "context_cost_sum": parent["context_cost_sum"] + context_cost})
            chosen = min(choices, key=lambda c: (-c["score"], tuple(map(tuple, c["path"]))))
            nodes[ref], best[ref] = candidate, chosen
            records.append({"endpoint": list(ref), **chosen})
    endpoints = [{"endpoint": None, "score": 0., "path": [], "endpoint_confidence": None,
                  "trailing_skipped_frames": None, "context_cost_sum": 0.}]
    for ref, value in best.items():
        trailing = t - ref[0]
        if trailing <= GAP:
            endpoints.append({"endpoint": list(ref), "score": value["score"] - PENALTY * trailing,
                              "path": value["path"], "endpoint_confidence": nodes[ref].confidence,
                              "trailing_skipped_frames": trailing, "context_cost_sum": value["context_cost_sum"]})
    def endpoint_key(value):
        ref = value["endpoint"]
        return (-value["score"], 0 if ref is None else 1, -ref[0] if ref is not None else 0,
                -value["endpoint_confidence"] if ref is not None else 0,
                ref[1] if ref is not None else 0, tuple(map(tuple, value["path"])))
    endpoints.sort(key=endpoint_key)
    winner = endpoints[0]
    return {"eligible_edges": edges, "best_path_per_endpoint": records, "competing_endpoints": endpoints,
            "winner": winner, "score_margin": winner["score"] - endpoints[1]["score"] if len(endpoints) > 1 else None,
            "node_context": node_records}


def project_zero_context_trace(ranking):
    """Synthetic-only comparison adapter: discard added audit fields at zero cost."""
    if any(n["context_cost"] != 0 for n in ranking["node_context"]):
        raise ValueError("Cannot project a nonzero-cost trace into a control")
    projected = copy.deepcopy(ranking)
    del projected["node_context"]
    for record in [*projected["best_path_per_endpoint"], *projected["competing_endpoints"], projected["winner"]]:
        if record.pop("context_cost_sum", 0.) != 0.:
            raise ValueError("Nonzero accumulated context cost")
    return projected


def rank_candidates(run: BallDetectionRun, config: RankingConfig, code_commit: str, context_window):
    require_digest(code_commit, "ranking code commit", 40)
    config = RankingConfig.from_mapping(config.to_dict())
    run = BallDetectionRun.from_mapping(run.to_dict())
    context = validate_context_window(context_window, run)
    if (config.confidence_threshold < run.model_provenance.export_confidence_floor
            or any(f.inference_status != "completed" for f in run.frames)):
        raise ValueError("Ranking requires complete input at or above export floor")
    diagonal = math.hypot(run.source_video.width_px, run.source_video.height_px)
    frames = []
    for offset, frame in enumerate(run.frames):
        accepted = [d.candidate_index for d in frame.detections if d.confidence >= config.confidence_threshold]
        eligible = accepted[:CAP]
        horizon = run.frames[max(0, offset - HISTORY + 1):offset + 1]
        ranking = rank_history(horizon, config, diagonal, {f.frame_index: context[f.frame_index] for f in horizon})
        endpoint = ranking["winner"]["endpoint"]
        emitted = [endpoint[1]] if endpoint is not None and endpoint[0] == frame.frame_index else []
        frames.append({"frame_index": frame.frame_index, "horizon_start": horizon[0].frame_index,
                       "horizon_end": frame.frame_index, "emitted_candidate_indices": emitted,
                       "candidate_decisions": [{"candidate_index": d.candidate_index,
                           "disposition": "below_threshold" if d.candidate_index not in accepted else
                           "outside_top_twenty" if d.candidate_index not in eligible else
                           "emitted" if d.candidate_index in emitted else "eligible_not_emitted"} for d in frame.detections],
                       "ranking": ranking,
                       "decision_reason": "current_endpoint" if emitted else "empty_hypothesis" if endpoint is None else "earlier_endpoint_no_current_observation",
                       "output_state": "tentative_observation" if emitted else "no_accepted_observation",
                       "context_available_box_count": len(context[frame.frame_index]),
                       "context_unavailable": not context[frame.frame_index]})
    return {"schema_version": SCHEMA, "variant_id": config.variant_id, "config": config.to_dict(),
            "ranking_code_commit": code_commit, "detector_code_commit": run.model_provenance.code_commit,
            "input_candidate_content_sha256": canonical_sha256(run.to_dict()),
            "input_context_content_sha256": canonical_sha256(context_window),
            "window_rows_sha256": context_window["selected_rows_sha256"],
            "source_video": run.source_video.to_dict(), "window": run.window.to_dict(),
            "possession_id": run.possession_id, "frames": frames,
            "score_semantics": "Uncalibrated heuristic; original detector confidence unchanged; signed node utility is not a probability; minimizing players are context, not inferred ball handlers.",
            "selected_operating_point": None, "quality_gate": None}


def validate_observations(value, run, context_window):
    config = RankingConfig.from_mapping(value.get("config"))
    expected = rank_candidates(run, config, value.get("ranking_code_commit"), context_window)
    if canonical_sha256(value) != canonical_sha256(expected):
        raise ValueError("Context observations or provenance differ from exact rederivation")
    return config
