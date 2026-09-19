"""Causal candidate association. No labels, source pixels, or model execution.

Outputs refer to immutable raw candidate indices; they are not raw detections.
Each call resets state, and an unmatched frame always has no emitted position.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from .detections import BallDetectionRun
from .development_experiments import canonical_sha256, closed, require_digest

SCHEMA = "ball_temporal_observations/v0.1"
THRESHOLDS = (0.01, 0.03, 0.05, 0.1, 0.15, 0.2, 0.25, 0.35, 0.5)
RADII = (5.0, 10.0, 15.0, 20.0, 30.0)


@dataclass(frozen=True)
class AssociationConfig:
    arm: str
    confidence_threshold: float
    step_limit: float | None = None
    max_missing_frames: int | None = None

    def __post_init__(self):
        if self.arm not in {"raw", "top_one", "tracklets"}:
            raise ValueError("Unknown association arm")
        threshold = self.confidence_threshold
        if (isinstance(threshold, bool) or not isinstance(threshold, (float, int))
                or not math.isfinite(threshold) or not 0 <= threshold <= 1):
            raise ValueError("Confidence must be finite and in [0, 1]")
        if self.arm == "tracklets":
            if (isinstance(self.step_limit, bool)
                    or not isinstance(self.step_limit, (float, int))
                    or not math.isfinite(self.step_limit) or not 0 < self.step_limit <= 1):
                raise ValueError("step_limit must be finite and in (0, 1]")
            if type(self.max_missing_frames) is not int or self.max_missing_frames < 0:
                raise ValueError("max_missing_frames must be a nonnegative integer")
        elif self.step_limit is not None or self.max_missing_frames is not None:
            raise ValueError("Control arms cannot have association parameters")

    @classmethod
    def from_mapping(cls, value):
        return cls(**closed(value, set(cls.__dataclass_fields__), "association config"))

    @property
    def variant_id(self):
        return self.arm + "_" + canonical_sha256(asdict(self))[:16]


def experiment_grid():
    """54 variants: 9 raw controls, 9 top-one controls, 36 tracklet variants."""
    return tuple(
        config
        for threshold in THRESHOLDS
        for config in (
            AssociationConfig("raw", threshold),
            AssociationConfig("top_one", threshold),
            *(AssociationConfig("tracklets", threshold, step, gap)
              for step in (0.01, 0.03) for gap in (0, 2)),
        )
    )


def associate(run: BallDetectionRun, config: AssociationConfig, code_commit: str):
    """Pure, deterministic selection; provisional observations never backfill."""
    require_digest(code_commit, "association commit", 40)
    # Validate manually constructed instances as strictly as persisted raw runs.
    run = BallDetectionRun.from_mapping(run.to_dict())
    config = AssociationConfig.from_mapping(asdict(config))
    if config.confidence_threshold < run.model_provenance.export_confidence_floor:
        raise ValueError("Threshold below input export floor")
    if any(frame.inference_status != "completed" for frame in run.frames):
        raise ValueError("Association requires complete input frames")
    diagonal = math.hypot(run.source_video.width_px, run.source_video.height_px)
    tracks, frames, next_id = {}, [], 0
    for frame in run.frames:
        t = frame.frame_index
        candidates = {d.candidate_index: d for d in frame.detections}
        accepted = {i: d for i, d in candidates.items()
                    if d.confidence >= config.confidence_threshold}
        decisions = {i: {"candidate_index": i, "disposition": "below_threshold",
                         "tracklet_id": None} for i in candidates}
        emitted, associations, expired, confirmed = [], [], [], []
        if config.arm != "tracklets":
            selected = set(accepted)
            if config.arm == "top_one" and accepted:
                selected = {min(accepted, key=lambda i: (-accepted[i].confidence, i))}
            for i in accepted:
                decisions[i]["disposition"] = "emitted" if i in selected else "control_suppressed"
            emitted = sorted(selected)
        else:
            for track_id, state in list(tracks.items()):
                age = t - state["frame_index"]
                allowed = config.max_missing_frames if state["confirmed"] else 0
                if age - 1 > allowed:
                    expired.append(track_id)
                    del tracks[track_id]
            edges = []
            for track_id, state in tracks.items():
                delta = t - state["frame_index"]
                for i, candidate in accepted.items():
                    distance = math.dist(state["center"], candidate.center_xy_px)
                    if distance <= config.step_limit * diagonal * delta:
                        edges.append((distance / delta, track_id, i, distance, delta))
            used_tracks, used_candidates = set(), set()
            for _, track_id, i, distance, delta in sorted(edges):
                if track_id in used_tracks or i in used_candidates:
                    continue
                used_tracks.add(track_id)
                used_candidates.add(i)
                old = tracks[track_id]
                associations.append({"tracklet_id": track_id, "candidate_index": i,
                                     "from_frame_index": old["frame_index"],
                                     "from_candidate_index": old["candidate_index"],
                                     "distance_px": distance, "elapsed_frames": delta})
                if not old["confirmed"]:
                    confirmed.append(track_id)
                tracks[track_id] = {"frame_index": t, "candidate_index": i,
                                    "center": accepted[i].center_xy_px, "confirmed": True}
                decisions[i] = {"candidate_index": i, "disposition": "emitted",
                                "tracklet_id": track_id}
                emitted.append(i)
            for i in sorted(set(accepted) - used_candidates):
                tracks[next_id] = {"frame_index": t, "candidate_index": i,
                                   "center": accepted[i].center_xy_px, "confirmed": False}
                decisions[i] = {"candidate_index": i, "disposition": "provisional",
                                "tracklet_id": next_id}
                next_id += 1
        frames.append({
            "frame_index": t, "emitted_candidate_indices": sorted(emitted),
            "candidate_decisions": [decisions[i] for i in sorted(decisions)],
            "associations": associations, "confirmed_tracklet_ids": confirmed,
            "expired_tracklet_ids": expired,
            "active_tracklets": [{"tracklet_id": i, "last_observed_frame": s["frame_index"],
                                  "confirmed": s["confirmed"]} for i, s in sorted(tracks.items())],
            "output_state": "observations" if emitted else "no_accepted_observation",
        })
    return {
        "schema_version": SCHEMA, "variant_id": config.variant_id,
        "config": asdict(config), "association_code_commit": code_commit,
        "raw_detection_content_sha256": canonical_sha256(run.to_dict()),
        "raw_detection_run_id": run.detection_run_id,
        "raw_detector_code_commit": run.model_provenance.code_commit,
        "source_video": run.source_video.to_dict(), "window": run.window.to_dict(),
        "possession_id": run.possession_id, "frames": frames,
        "boundary_expired_tracklet_ids": sorted(tracks),
        "selected_operating_point": None, "quality_gate": None,
    }


def validate_observations(value, raw_run):
    """Re-derive every decision, reference, gap, and provenance field."""
    config = AssociationConfig.from_mapping(value.get("config"))
    expected = associate(raw_run, config, value.get("association_code_commit"))
    # Canonical comparison also rejects booleans substituted for integer IDs.
    if canonical_sha256(value) != canonical_sha256(expected):
        raise ValueError("Temporal observation content/provenance mismatch")
    return config
