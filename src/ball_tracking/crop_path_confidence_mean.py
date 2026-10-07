"""Pure fixed-terminal-length binary64 DP for the approved mean-confidence arm.

No file, label, image or control loading occurs here. Each horizon is rebuilt from
the original candidate records. This is the declared deterministic DP, not an
exact-real or exhaustive floating-point optimizer: extension can round distinct
prefix scores to equality after one of them has already been pruned.
"""
from __future__ import annotations

import copy
import math
from dataclasses import asdict, dataclass

from .detections import BallDetection, BallDetectionRun, DetectionFrame
from .development_experiments import canonical_sha256, closed

ARM = "history_mean_edge_tight_cost_tight"
SCHEMA = "ball_crop_path_confidence_mean_observations/v0.1"
HISTORY, CAP, GAP, PENALTY = 5, 20, 2, .25
THRESHOLD, EDGE_STEP, COST_STEP = .01, .01, .01


@dataclass(frozen=True)
class RankingConfig:
    arm: str = ARM
    confidence_threshold: float = THRESHOLD
    candidate_cap: int = CAP
    edge_step: float = EDGE_STEP
    cost_step: float = COST_STEP

    def __post_init__(self):
        if (self.arm != ARM or type(self.candidate_cap) is not int
                or self.candidate_cap != CAP):
            raise ValueError("Only the approved fixed mean-confidence arm is allowed")
        for key, expected in (("confidence_threshold", THRESHOLD),
                              ("edge_step", EDGE_STEP), ("cost_step", COST_STEP)):
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value != expected:
                raise ValueError("Mean-confidence settings differ from the approved arm")

    @property
    def variant_id(self):
        return self.arm + "_" + canonical_sha256(asdict(self))[:16]

    @classmethod
    def from_mapping(cls, value):
        return cls(**closed(value, set(cls.__dataclass_fields__), "mean ranking config"))


def _path(value):
    return tuple(tuple(pair) for pair in value["path"])


def _state_key(value):
    # Deliberately no tolerance. The stored binary64 value determines the tie.
    return -value["score"], _path(value)


def _endpoint_key(value):
    ref = value["endpoint"]
    return (-value["score"], 0 if ref is None else 1,
            -ref[0] if ref is not None else 0,
            -value["endpoint_confidence"] if ref is not None else 0,
            ref[1] if ref is not None else 0, _path(value))


def _reconcile(value, *, completed=False):
    """Check arithmetic only; this tolerance is never used to pick a path."""
    denominator = value["terminal_n"]
    expected = (value["confidence_sum"] / denominator
                - PENALTY * value["internal_skipped_frames"]
                - PENALTY * value["normalized_step_squared_sum"])
    if completed:
        expected -= PENALTY * value["trailing_skipped_frames"]
    if not math.isclose(value["score"], expected, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError("Mean-path stored score failed arithmetic reconciliation")


def _check_horizon(frames, diagonal):
    if not frames or len(frames) > HISTORY:
        raise ValueError("A one-to-five-frame horizon is required")
    if (isinstance(diagonal, bool) or not isinstance(diagonal, (int, float))
            or not math.isfinite(diagonal) or diagonal <= 0):
        raise ValueError("Source diagonal must be finite and positive")
    for frame in frames:
        if (not isinstance(frame, DetectionFrame) or type(frame.frame_index) is not int
                or frame.frame_index < 0 or frame.inference_status != "completed"
                or frame.failure_reason is not None or frame.detections is None):
            raise ValueError("Mean ranking requires completed valid frames")
        previous = math.inf
        for position, candidate in enumerate(frame.detections):
            if not isinstance(candidate, BallDetection):
                raise ValueError("History candidates must be original BallDetection records")
            if (type(candidate.candidate_index) is not int or candidate.candidate_index != position
                    or isinstance(candidate.confidence, bool)
                    or not isinstance(candidate.confidence, (int, float))
                    or not math.isfinite(candidate.confidence)
                    or not 0 <= candidate.confidence <= 1
                    or candidate.confidence > previous
                    or len(candidate.center_xy_px) != 2
                    or any(isinstance(v, bool) or not isinstance(v, (int, float))
                           or not math.isfinite(v) for v in candidate.center_xy_px)):
                raise ValueError("Candidates must preserve valid original indices and descending confidence")
            previous = candidate.confidence
    if any(b.frame_index != a.frame_index + 1 for a, b in zip(frames, frames[1:])):
        raise ValueError("History must be contiguous, increasing and causal")


def rank_history(frames, diagonal, progress=None):
    """Return a complete audit for one current-and-past horizon.

    State keys are (terminal_n, endpoint, actual_node_count). Only states whose
    actual count equals terminal_n compete as completed endpoint paths.
    """
    frames = tuple(frames)
    _check_horizon(frames, diagonal)
    if progress is not None:
        progress()
    nodes, edges, incoming = {}, [], {}
    for frame in frames:
        retained = [d for d in frame.detections if d.confidence >= THRESHOLD][:CAP]
        for candidate in retained:
            ref = (frame.frame_index, candidate.candidate_index)
            incoming[ref] = []
            for prior, old in nodes.items():
                delta = ref[0] - prior[0]
                if not 1 <= delta <= GAP + 1:
                    continue
                distance = math.dist(old.center_xy_px, candidate.center_xy_px)
                limit = EDGE_STEP * diagonal * delta
                if distance > limit:
                    continue
                normalized = distance / (COST_STEP * diagonal * delta)
                edge = {"from": list(prior), "to": list(ref), "elapsed_frames": delta,
                        "distance_px": distance, "normalized_step": normalized,
                        "skipped_frame_penalty": PENALTY * (delta - 1),
                        "motion_penalty": PENALTY * normalized ** 2}
                edges.append(edge)
                incoming[ref].append(edge)
            nodes[ref] = candidate

    surviving, completed, best = [], [], {}
    for terminal_n in range(1, len(frames) + 1):
        if progress is not None:
            progress()
        states = {}
        for ref, candidate in nodes.items():
            singleton = {"terminal_n": terminal_n, "actual_node_count": 1,
                         "endpoint": list(ref), "predecessor": None,
                         "score": candidate.confidence / terminal_n,
                         "path": [list(ref)], "confidence_sum": candidate.confidence,
                         "node_count": 1, "internal_skipped_frames": 0,
                         "normalized_step_squared_sum": 0.0}
            at_endpoint = {1: singleton}
            for edge in incoming[ref]:
                prior = tuple(edge["from"])
                for actual, parent in states[prior].items():
                    count = actual + 1
                    if count > terminal_n:
                        continue
                    value = {"terminal_n": terminal_n, "actual_node_count": count,
                             "endpoint": list(ref),
                             "predecessor": {"terminal_n": terminal_n,
                                             "endpoint": list(prior), "actual_node_count": actual},
                             # Keep every binary64 operation in the approved legacy order.
                             "score": ((parent["score"] + candidate.confidence / terminal_n)
                                       - edge["skipped_frame_penalty"]) - edge["motion_penalty"],
                             "path": [*parent["path"], list(ref)],
                             "confidence_sum": parent["confidence_sum"] + candidate.confidence,
                             "node_count": count,
                             "internal_skipped_frames": (parent["internal_skipped_frames"]
                                                         + edge["elapsed_frames"] - 1),
                             "normalized_step_squared_sum": (parent["normalized_step_squared_sum"]
                                                             + edge["normalized_step"] ** 2)}
                    old = at_endpoint.get(count)
                    if old is None or _state_key(value) < _state_key(old):
                        at_endpoint[count] = value
            states[ref] = {count: at_endpoint[count] for count in sorted(at_endpoint)}
            for value in states[ref].values():
                _reconcile(value)
                surviving.append(value)
            value = at_endpoint.get(terminal_n)
            if value is not None:
                completed.append(value)
                if ref not in best or _state_key(value) < _state_key(best[ref]):
                    best[ref] = value

    now = frames[-1].frame_index
    endpoints = [{"endpoint": None, "score": 0.0, "path": [], "endpoint_confidence": None,
                  "trailing_skipped_frames": None, "terminal_n": None, "actual_node_count": 0,
                  "predecessor": None, "confidence_sum": 0.0, "node_count": 0,
                  "internal_skipped_frames": 0, "normalized_step_squared_sum": 0.0}]
    for ref in nodes:
        value = best[ref]
        trailing = now - ref[0]
        if trailing <= GAP:
            endpoint = {**value, "score": value["score"] - PENALTY * trailing,
                        "endpoint_confidence": nodes[ref].confidence,
                        "trailing_skipped_frames": trailing}
            _reconcile(endpoint, completed=True)
            endpoints.append(endpoint)
    endpoints.sort(key=_endpoint_key)
    return {"retained_candidates": [{"reference": list(ref), **candidate.to_dict()}
                                     for ref, candidate in nodes.items()],
            "eligible_edges": edges, "surviving_states": surviving, "completed_states": completed,
            "best_path_per_endpoint": [best[ref] for ref in nodes],
            "competing_endpoints": endpoints, "winner": endpoints[0],
            "score_margin": endpoints[0]["score"] - endpoints[1]["score"] if len(endpoints) > 1 else None}


def iter_ranked_frames(run: BallDetectionRun, progress=None):
    """Yield original-order audit frames without retaining previous audit shards."""
    if not isinstance(run, BallDetectionRun):
        raise ValueError("Mean ranking requires a BallDetectionRun")
    run = BallDetectionRun.from_mapping(run.to_dict())
    if (THRESHOLD < run.model_provenance.export_confidence_floor
            or any(frame.inference_status != "completed" for frame in run.frames)):
        raise ValueError("Mean ranking requires complete input at or above export floor")
    # Validate all ordering before publishing any selection frame.
    for frame in run.frames:
        if any(b.confidence > a.confidence for a, b in zip(frame.detections, frame.detections[1:])):
            raise ValueError("Input must preserve descending crop global order")
    diagonal = math.hypot(run.source_video.width_px, run.source_video.height_px)
    for offset, frame in enumerate(run.frames):
        horizon = run.frames[max(0, offset - HISTORY + 1):offset + 1]
        ranking = rank_history(horizon, diagonal, progress)
        endpoint = ranking["winner"]["endpoint"]
        emitted = [endpoint[1]] if endpoint is not None and endpoint[0] == frame.frame_index else []
        accepted = {d.candidate_index for d in frame.detections if d.confidence >= THRESHOLD}
        eligible = set([d.candidate_index for d in frame.detections if d.confidence >= THRESHOLD][:CAP])
        yield {"frame_index": frame.frame_index, "horizon_start": horizon[0].frame_index,
               "horizon_end": frame.frame_index, "emitted_candidate_indices": emitted,
               "candidate_decisions": [{"candidate_index": d.candidate_index,
                   "disposition": "below_threshold" if d.candidate_index not in accepted else
                   "outside_top_twenty" if d.candidate_index not in eligible else
                   "emitted" if d.candidate_index in emitted else "eligible_not_emitted"}
                   for d in frame.detections],
               "ranking": ranking,
               "decision_reason": "current_endpoint" if emitted else "empty_hypothesis"
                                  if endpoint is None else "earlier_endpoint_no_current_observation",
               "output_state": "tentative_observation" if emitted else "no_accepted_observation"}


def summarize_frame(frame):
    """Return an independent compact frame; the full trace belongs in its shard."""
    return copy.deepcopy({**frame, "ranking": {key: frame["ranking"][key]
                                               for key in ("winner", "score_margin")}})
