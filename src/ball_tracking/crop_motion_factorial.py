"""Independent edge allowance and motion cost on immutable saved crop candidates."""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from .detections import BallDetectionRun
from . import crop_ranking as legacy
from .development_experiments import canonical_sha256, closed, require_digest
from .temporal_association import THRESHOLDS

ARMS = ("crop_raw", "crop_top_one", "crop_top_twenty",
        "history_edge_tight_cost_tight", "history_edge_tight_cost_wide",
        "history_edge_wide_cost_tight", "history_edge_wide_cost_wide")
STEPS = dict(zip(ARMS[3:], ((.01, .01), (.01, .03), (.03, .01), (.03, .03))))
SCHEMA = "ball_crop_motion_observations/v0.1"
HISTORY, CAP, GAP, PENALTY = 5, 20, 2, 0.25


@dataclass(frozen=True)
class RankingConfig:
    arm: str
    confidence_threshold: float
    candidate_cap: int | None = None
    edge_step: float | None = None
    cost_step: float | None = None

    def __post_init__(self):
        if self.arm not in ARMS:
            raise ValueError("Unknown crop ranking arm")
        if (isinstance(self.confidence_threshold, bool)
                or not isinstance(self.confidence_threshold, (int, float))
                or self.confidence_threshold not in THRESHOLDS):
            raise ValueError("Undeclared ranking confidence")
        cap = CAP if self.arm in ARMS[2:] else None
        edge, cost = STEPS.get(self.arm, (None, None))
        if (self.candidate_cap != cap or (cap is not None and type(self.candidate_cap) is not int)
                or self.edge_step != edge or self.cost_step != cost
                or isinstance(self.edge_step, bool) or isinstance(self.cost_step, bool)):
            raise ValueError("Ranking settings differ from the approved arm")

    @property
    def variant_id(self):
        return self.arm + "_" + canonical_sha256(asdict(self))[:16]

    @classmethod
    def from_mapping(cls, value):
        return cls(**closed(value, set(cls.__dataclass_fields__), "ranking config"))


def experiment_grid():
    return tuple(RankingConfig(arm, threshold, CAP if arm in ARMS[2:] else None,
                              *STEPS.get(arm, (None, None)))
                 for threshold in THRESHOLDS for arm in ARMS)


def legacy_config(config):
    """Map the five controls to their immutable prior configurations."""
    config = RankingConfig.from_mapping(asdict(config))
    arm = {ARMS[3]: "recent_history_tight", ARMS[6]: "recent_history_wide"}.get(config.arm)
    if config.arm in ARMS[:3]:
        arm = config.arm
    if arm is None:
        return None
    return legacy.RankingConfig(arm, config.confidence_threshold,
                                config.candidate_cap, config.edge_step)


def verify_control_trace(observations, saved):
    """Exact behavioral parity, allowing only declared schema/config provenance changes."""
    config = RankingConfig.from_mapping(observations.get("config"))
    prior = legacy_config(config)
    if prior is None:
        raise ValueError("New crossed arm has no legacy control")
    if (observations.get("schema_version") != SCHEMA or saved.get("schema_version") != legacy.SCHEMA
            or observations.get("variant_id") != config.variant_id
            or saved.get("variant_id") != prior.variant_id or saved.get("config") != asdict(prior)):
        raise ValueError("Saved control configuration mapping differs")
    for value in (observations, saved):
        require_digest(value.get("ranking_code_commit"), "control code commit", 40)
    metadata = {"schema_version", "variant_id", "config", "ranking_code_commit"}
    if canonical_sha256({k: v for k, v in observations.items() if k not in metadata}) != canonical_sha256(
            {k: v for k, v in saved.items() if k not in metadata}):
        raise ValueError("Saved control observation traces differ")


def reference(frame, candidate):
    return (frame.frame_index, candidate.candidate_index)


def _path(value):
    return tuple(tuple(pair) for pair in value["path"])


def rank_history(frames, config, diagonal):
    """Exact endpoint DP on a supplied current-and-past horizon only."""
    if config.edge_step is None or not frames or len(frames) > HISTORY:
        raise ValueError("History arm and one-to-five frames required")
    t = frames[-1].frame_index
    if any(b.frame_index != a.frame_index + 1 for a, b in zip(frames, frames[1:])):
        raise ValueError("Noncontiguous history")
    nodes, best, edges, records = {}, {}, [], []
    for frame in frames:
        candidates = [c for c in frame.detections if c.confidence >= config.confidence_threshold][:CAP]
        for candidate in candidates:
            ref = reference(frame, candidate)
            choices = [{"score": candidate.confidence, "path": [list(ref)],
                        "confidence_sum": candidate.confidence, "internal_skipped_frames": 0,
                        "normalized_step_squared_sum": 0.0}]
            for prior, old in nodes.items():
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
                choices.append({"score": parent["score"] + candidate.confidence - gap_cost - motion_cost,
                                "path": [*parent["path"], list(ref)],
                                "confidence_sum": parent["confidence_sum"] + candidate.confidence,
                                "internal_skipped_frames": parent["internal_skipped_frames"] + delta - 1,
                                "normalized_step_squared_sum": parent["normalized_step_squared_sum"] + normalized ** 2})
            chosen = min(choices, key=lambda c: (-c["score"], _path(c)))
            nodes[ref], best[ref] = candidate, chosen
            records.append({"endpoint": list(ref), **chosen})
    endpoints = [{"endpoint": None, "score": 0.0, "path": [],
                  "endpoint_confidence": None, "trailing_skipped_frames": None}]
    for ref, value in best.items():
        trailing = t - ref[0]
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
    return {"eligible_edges": edges, "best_path_per_endpoint": records,
            "competing_endpoints": endpoints, "winner": winner,
            "score_margin": winner["score"] - endpoints[1]["score"] if len(endpoints) > 1 else None}


def rank_candidates(run: BallDetectionRun, config: RankingConfig, code_commit: str):
    require_digest(code_commit, "ranking code commit", 40)
    config = RankingConfig.from_mapping(asdict(config))
    run = BallDetectionRun.from_mapping(run.to_dict())
    if (config.confidence_threshold < run.model_provenance.export_confidence_floor
            or any(f.inference_status != "completed" for f in run.frames)):
        raise ValueError("Ranking requires complete input at or above export floor")
    for f in run.frames:
        if any(b.confidence > a.confidence for a, b in zip(f.detections, f.detections[1:])):
            raise ValueError("Input must preserve descending crop global order")
    frames = []
    diagonal = math.hypot(run.source_video.width_px, run.source_video.height_px)
    for offset, frame in enumerate(run.frames):
        accepted = [d.candidate_index for d in frame.detections if d.confidence >= config.confidence_threshold]
        eligible = accepted if config.candidate_cap is None else accepted[:config.candidate_cap]
        history = None
        if config.edge_step is not None:
            history = rank_history(run.frames[max(0, offset-HISTORY+1):offset+1], config, diagonal)
            endpoint = history["winner"]["endpoint"]
            emitted = [endpoint[1]] if endpoint is not None and endpoint[0] == frame.frame_index else []
            reason = "current_endpoint" if emitted else "empty_hypothesis" if endpoint is None else "earlier_endpoint_no_current_observation"
        else:
            emitted = accepted[:1] if config.arm == "crop_top_one" else eligible
            reason = "control_selection" if emitted else "no_threshold_qualified_candidate"
        frames.append({"frame_index": frame.frame_index,
                       "horizon_start": run.frames[max(0, offset-HISTORY+1)].frame_index if history is not None else frame.frame_index,
                       "horizon_end": frame.frame_index, "emitted_candidate_indices": emitted,
                       "candidate_decisions": [{"candidate_index": d.candidate_index,
                           "disposition": "below_threshold" if d.candidate_index not in accepted else
                           "outside_top_twenty" if d.candidate_index not in eligible else
                           "emitted" if d.candidate_index in emitted else "eligible_not_emitted"}
                           for d in frame.detections],
                       "ranking": history, "decision_reason": reason,
                       "output_state": "tentative_observation" if emitted else "no_accepted_observation"})
    return {"schema_version": SCHEMA, "variant_id": config.variant_id, "config": asdict(config),
            "ranking_code_commit": code_commit, "detector_code_commit": run.model_provenance.code_commit,
            "input_candidate_content_sha256": canonical_sha256(run.to_dict()),
            "source_video": run.source_video.to_dict(), "window": run.window.to_dict(),
            "possession_id": run.possession_id, "frames": frames,
            "score_semantics": "Uncalibrated heuristic; detector confidence unchanged; alternatives are hypotheses.",
            "selected_operating_point": None, "quality_gate": None}


def validate_observations(value, run):
    config = RankingConfig.from_mapping(value.get("config"))
    expected = rank_candidates(run, config, value.get("ranking_code_commit"))
    if canonical_sha256(value) != canonical_sha256(expected):
        raise ValueError("Ranking observations or provenance differ from exact rederivation")
    return config
