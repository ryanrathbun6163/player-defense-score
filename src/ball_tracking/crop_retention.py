"""Causal all-candidate retention using the frozen motion-path arithmetic.

This module accepts candidate objects and source metadata only. It does no
file access, annotation access, image work or inference. The real runner owns
authorization and restricts execution to the .01 uncapped units; cap20 and
higher thresholds here support synthetic parity and equivalence verification.
Full audit frames are yielded individually so the caller can persist each
lossless trace without accumulating a window's graphs in memory.
"""
from __future__ import annotations

from collections import deque
import copy
from dataclasses import asdict, dataclass
import hashlib
import json
import math


ARMS = ("history_edge_tight_cost_tight", "history_edge_tight_cost_wide",
        "history_edge_wide_cost_tight", "history_edge_wide_cost_wide")
STEPS = dict(zip(ARMS, ((.01, .01), (.01, .03), (.03, .01), (.03, .03))))
THRESHOLDS = (.01, .2, .35)
HISTORY, GAP, PENALTY = 5, 2, .25
PROGRESS_PAIR_INTERVAL = 4096


def _finite(value, label, *, positive=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or (positive and value <= 0)):
        raise ValueError(f"Invalid {label}")
    return value


@dataclass(frozen=True)
class RankingConfig:
    arm: str
    confidence_threshold: float = .01
    candidate_cap: int | None = None
    edge_step: float | None = None
    cost_step: float | None = None

    def __post_init__(self):
        if self.arm not in ARMS:
            raise ValueError("Unknown retention motion probe")
        if (_finite(self.confidence_threshold, "confidence threshold") not in THRESHOLDS
                or (self.candidate_cap is not None
                    and (type(self.candidate_cap) is not int or self.candidate_cap != 20))):
            raise ValueError("Only frozen thresholds and all/cap20 retention are supported")
        _finite(self.edge_step, "edge step", positive=True)
        _finite(self.cost_step, "cost step", positive=True)
        if (self.edge_step, self.cost_step) != STEPS[self.arm]:
            raise ValueError("Motion scales differ from the fixed probe")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_mapping(cls, value):
        if not isinstance(value, dict) or set(value) != set(cls.__dataclass_fields__):
            raise ValueError("Retention config requires exactly its five declared fields")
        return cls(**value)

    @property
    def variant_id(self):
        payload = json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False)
        return self.arm + "_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _validate_frame(frame):
    if type(frame.frame_index) is not int or frame.frame_index < 0:
        raise ValueError("Frame index must be a nonnegative integer")
    if frame.inference_status != "completed" or frame.detections is None:
        raise ValueError("Retention requires completed candidate frames")
    indices = set()
    previous_confidence = math.inf
    for candidate in frame.detections:
        index = candidate.candidate_index
        if type(index) is not int or index < 0 or index in indices:
            raise ValueError("Original candidate indices must be unique nonnegative integers")
        confidence = _finite(candidate.confidence, "candidate confidence")
        if not 0 <= confidence <= 1 or confidence > previous_confidence:
            raise ValueError("Candidates must retain descending original confidence order")
        center = candidate.center_xy_px
        if not isinstance(center, (list, tuple)) or len(center) != 2:
            raise ValueError("Candidate center must contain two coordinates")
        for value in center:
            _finite(value, "candidate center")
        previous_confidence = confidence
        indices.add(index)


def _retained(frame, config):
    qualified = [c for c in frame.detections if c.confidence >= config.confidence_threshold]
    return qualified if config.candidate_cap is None else qualified[:config.candidate_cap]


def _path(value):
    return tuple(tuple(pair) for pair in value["path"])


def rank_history(frames, config, diagonal, progress=None):
    """Exact legacy traversal with the declared cap applied to every frame.

    The complete graph audit is returned. A progress callback may raise to
    cancel work; exceptions propagate without a shortened or fallback result.
    """
    config = RankingConfig.from_mapping(config.to_dict())
    _finite(diagonal, "source diagonal", positive=True)
    if not frames or len(frames) > HISTORY:
        raise ValueError("One to five current/past frames required")
    for frame in frames:
        _validate_frame(frame)
    if any(b.frame_index != a.frame_index + 1 for a, b in zip(frames, frames[1:])):
        raise ValueError("History frames must be contiguous")
    current = frames[-1].frame_index
    nodes, best, edges, records = {}, {}, [], []
    pair_visits = 0

    def notify(phase, processed_frame_index):
        if progress is not None:
            progress({"phase": phase, "frame_index": current,
                      "processed_frame_index": processed_frame_index,
                      "node_count": len(nodes), "edge_count": len(edges),
                      "pair_visits": pair_visits})

    notify("horizon_start", frames[0].frame_index)
    for frame in frames:
        for candidate in _retained(frame, config):
            ref = (frame.frame_index, candidate.candidate_index)
            choices = [{"score": candidate.confidence, "path": [list(ref)],
                        "confidence_sum": candidate.confidence,
                        "internal_skipped_frames": 0, "normalized_step_squared_sum": 0.0}]
            for prior, old in nodes.items():
                pair_visits += 1
                if progress is not None and pair_visits % PROGRESS_PAIR_INTERVAL == 0:
                    notify("ranking", frame.frame_index)
                delta = ref[0] - prior[0]
                if not 1 <= delta <= GAP + 1:
                    continue
                distance = math.dist(old.center_xy_px, candidate.center_xy_px)
                limit = config.edge_step * diagonal * delta
                if distance > limit:
                    continue
                normalized = distance / (config.cost_step * diagonal * delta)
                gap_cost, motion_cost = PENALTY * (delta - 1), PENALTY * normalized ** 2
                parent = best[prior]
                edges.append({"from": list(prior), "to": list(ref), "elapsed_frames": delta,
                              "distance_px": distance, "normalized_step": normalized,
                              "skipped_frame_penalty": gap_cost, "motion_penalty": motion_cost})
                choices.append({"score": ((parent["score"] + candidate.confidence) - gap_cost) - motion_cost,
                                "path": [*parent["path"], list(ref)],
                                "confidence_sum": parent["confidence_sum"] + candidate.confidence,
                                "internal_skipped_frames": parent["internal_skipped_frames"] + delta - 1,
                                "normalized_step_squared_sum": parent["normalized_step_squared_sum"] + normalized ** 2})
            chosen = min(choices, key=lambda c: (-c["score"], _path(c)))
            nodes[ref], best[ref] = candidate, chosen
            records.append({"endpoint": list(ref), **chosen})
        notify("history_frame_complete", frame.frame_index)
    endpoints = [{"endpoint": None, "score": 0.0, "path": [],
                  "endpoint_confidence": None, "trailing_skipped_frames": None}]
    for ref, value in best.items():
        trailing = current - ref[0]
        if trailing <= GAP:
            endpoints.append({"endpoint": list(ref), "score": value["score"] - PENALTY * trailing,
                              "path": value["path"], "endpoint_confidence": nodes[ref].confidence,
                              "trailing_skipped_frames": trailing})

    def endpoint_key(value):
        ref = value["endpoint"]
        return (-value["score"], 0 if ref is None else 1,
                -ref[0] if ref is not None else 0,
                -value["endpoint_confidence"] if ref is not None else 0,
                ref[1] if ref is not None else 0, _path(value))

    endpoints.sort(key=endpoint_key)
    winner = endpoints[0]
    notify("horizon_complete", current)
    return {"eligible_edges": edges, "best_path_per_endpoint": records,
            "competing_endpoints": endpoints, "winner": winner,
            "score_margin": winner["score"] - endpoints[1]["score"] if len(endpoints) > 1 else None}


def iter_ranked_frames(run, config, progress=None):
    """Yield a full audit one frame at a time, with a fresh horizon per call.

    No candidate in a future frame is inspected to emit the current frame.
    Candidate objects, coordinates, confidence values and indices are unchanged.
    """
    config = RankingConfig.from_mapping(config.to_dict())
    floor = _finite(run.model_provenance.export_confidence_floor, "export floor")
    if not 0 <= floor <= config.confidence_threshold:
        raise ValueError("Confidence threshold is below the saved export floor")
    width = _finite(run.source_video.width_px, "source width", positive=True)
    height = _finite(run.source_video.height_px, "source height", positive=True)
    diagonal = math.hypot(width, height)
    history = deque(maxlen=HISTORY)
    previous = None
    for frame in run.frames:
        _validate_frame(frame)
        if previous is not None and frame.frame_index != previous + 1:
            raise ValueError("Window frames must be contiguous")
        previous = frame.frame_index
        history.append(frame)
        accepted = [c.candidate_index for c in frame.detections if c.confidence >= config.confidence_threshold]
        eligible = accepted if config.candidate_cap is None else accepted[:config.candidate_cap]
        ranking = rank_history(tuple(history), config, diagonal, progress)
        endpoint = ranking["winner"]["endpoint"]
        emitted = [endpoint[1]] if endpoint is not None and endpoint[0] == frame.frame_index else []
        reason = ("current_endpoint" if emitted else "empty_hypothesis" if endpoint is None
                  else "earlier_endpoint_no_current_observation")
        yield {"frame_index": frame.frame_index, "horizon_start": history[0].frame_index,
               "horizon_end": frame.frame_index, "emitted_candidate_indices": emitted,
               "candidate_decisions": [{"candidate_index": c.candidate_index,
                   "disposition": "below_threshold" if c.candidate_index not in accepted else
                   "outside_top_twenty" if c.candidate_index not in eligible else
                   "emitted" if c.candidate_index in emitted else "eligible_not_emitted"}
                   for c in frame.detections],
               "ranking": ranking, "decision_reason": reason,
               "output_state": "tentative_observation" if emitted else "no_accepted_observation"}
        # Do not keep the previous graph alive while constructing the next one.
        del ranking


def summarize_frame(frame):
    """Create the compact view; the caller separately persists the full audit.

    Competing-endpoint count includes the empty hypothesis. Alternatives are
    the three best current-frame endpoints that were not emitted, in the saved
    ranking order; no coordinate, confidence or ranking value is recomputed.
    """
    ranking = frame["ranking"]
    winner = ranking["winner"]
    best = next((r for r in ranking["best_path_per_endpoint"]
                 if r["endpoint"] == winner["endpoint"]), None)
    alternatives = [r for r in ranking["competing_endpoints"]
                    if r["endpoint"] is not None and r["endpoint"][0] == frame["frame_index"]
                    and r["endpoint"][1] not in frame["emitted_candidate_indices"]][:3]
    return {**copy.deepcopy({k: v for k, v in frame.items() if k != "ranking"}),
            "ranking": copy.deepcopy({"winner": winner, "score_margin": ranking["score_margin"],
                                      "best_path_for_winner": best, "current_alternatives": alternatives}),
            "audit_counts": {"node_count": len(ranking["best_path_per_endpoint"]),
                             "edge_count": len(ranking["eligible_edges"]),
                             "competing_endpoint_count": len(ranking["competing_endpoints"])}}
