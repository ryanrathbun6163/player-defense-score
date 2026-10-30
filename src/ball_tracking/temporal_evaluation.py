"""Evaluate derived observations with the existing raw-distance matching rule.

An in-memory candidate view adapts to the established evaluator; it is never
persisted as a raw detector run/report. Persisted reports use a separate schema
and retain association provenance and the original candidate indices.
"""
from __future__ import annotations

from dataclasses import replace

from .development_experiments import canonical_sha256
from .evaluation import evaluate_detections
from .temporal_association import validate_observations


def selected_frame(raw_frame, temporal_frame):
    emitted = set(temporal_frame["emitted_candidate_indices"])
    return replace(raw_frame, detections=tuple(d for d in raw_frame.detections
                                             if d.candidate_index in emitted))


def _runs(values):
    lengths, current = [], 0
    for value in [*values, False]:
        if value:
            current += 1
        elif current:
            lengths.append(current)
            current = 0
    return lengths


def evaluate_observations(labels, raw_run, observations, radius, evaluator_commit):
    from .development_experiments import require_digest
    require_digest(evaluator_commit, "evaluator commit", 40)
    config = validate_observations(observations, raw_run)
    view = replace(raw_run, frames=tuple(selected_frame(raw, selected)
                                        for raw, selected in zip(raw_run.frames, observations["frames"])))
    scored = evaluate_detections(labels, view, confidence_threshold=config.confidence_threshold,
                                localization_radius_px=radius)
    metric_keys = {
        "eligible_frame_count", "not_visible_frame_count", "unscored_frame_count",
        "input_detection_count", "below_threshold_detection_count", "true_positive_count",
        "false_positive_count", "false_negative_count", "duplicate_false_positive_count",
        "non_visible_false_alarm_count", "non_visible_false_alarm_frame_count",
        "non_visible_false_alarm_rate", "non_visible_false_alarms_per_100_frames",
        "unscored_prediction_count", "precision", "recall", "matched_center_error_px",
        "matched_effective_center_error_px",
    }
    frames = scored["frame_results"]
    correct_runs = _runs([f["matched_candidate_index"] is not None for f in frames])
    missed_runs = _runs([f["false_negative_count"] == 1 for f in frames])
    matched_ids = []
    for frame, temporal in zip(frames, observations["frames"]):
        index = frame["matched_candidate_index"]
        matched_ids.append(next((d["tracklet_id"] for d in temporal["candidate_decisions"]
                                 if d["candidate_index"] == index), None))
    fragments = None
    if config.arm == "tracklets":
        fragments = sum(track is not None and (i == 0 or matched_ids[i - 1] != track)
                        for i, track in enumerate(matched_ids))
    return {
        "schema_version": "ball_temporal_evaluation/v0.1",
        "variant_id": config.variant_id, "config": observations["config"],
        "observations_content_sha256": canonical_sha256(observations),
        "raw_detection_content_sha256": observations["raw_detection_content_sha256"],
        "annotation_content_sha256": scored["annotation_content_sha256"],
        "source_video": raw_run.source_video.to_dict(), "window": raw_run.window.to_dict(),
        "possession_id": raw_run.possession_id, "selection_purpose": labels.window.selection_purpose,
        "association_code_commit": observations["association_code_commit"],
        "raw_detector_code_commit": raw_run.model_provenance.code_commit,
        "evaluator_code_commit": evaluator_commit, "localization_radius_px": radius,
        "matching_rule": "raw_center_distance; uncertainty-adjusted error is diagnostic only",
        "metrics": {key: scored[key] for key in sorted(metric_keys)},
        "temporal_metrics": {
            "emitted_frame_count": sum(bool(f["emitted_candidate_indices"]) for f in observations["frames"]),
            "frame_count": len(frames),
            "emitted_frame_coverage": sum(bool(f["emitted_candidate_indices"]) for f in observations["frames"]) / len(frames),
            "longest_consecutive_missed_eligible_run": max(missed_runs, default=0),
            "correct_match_run_lengths": correct_runs,
            "correct_tracklet_fragment_count": fragments,
            "fragment_definition": "Consecutive correct matches with one tracklet ID; missing/unscored frames break a fragment. Null for control arms.",
        },
        "frame_results": frames, "selected_operating_point": None, "quality_gate": None,
    }


def aggregate_temporal_reports(reports):
    """Separate-pool, same-variant/radius micro counts with explicit denominators."""
    if not reports:
        raise ValueError("No reports to aggregate")
    first = reports[0]
    keys = ("variant_id", "config", "localization_radius_px", "selection_purpose",
            "association_code_commit", "evaluator_code_commit", "raw_detector_code_commit")
    if any(any(report[k] != first[k] for k in keys) for report in reports):
        raise ValueError("Cannot mix pools, settings, or provenance")
    identities = [(r["possession_id"], r["window"]["start_frame_index"], r["window"]["end_frame_index"]) for r in reports]
    if len(set(identities)) != len(identities):
        raise ValueError("Duplicate window in aggregate")
    count_keys = ("true_positive_count", "false_positive_count", "false_negative_count",
                  "duplicate_false_positive_count", "non_visible_false_alarm_count",
                  "non_visible_false_alarm_frame_count", "eligible_frame_count", "not_visible_frame_count")
    totals = {k: sum(r["metrics"][k] for r in reports) for k in count_keys}
    tp, fp, fn = (totals[k] for k in count_keys[:3])
    totals.update(precision=tp / (tp + fp) if tp + fp else None,
                  recall=tp / (tp + fn) if tp + fn else None)
    return {**{k: first[k] for k in keys}, "metrics": totals,
            "window_count": len(reports),
            "per_window": [{"possession_id": r["possession_id"], "window": r["window"],
                            "metrics": r["metrics"], "temporal_metrics": r["temporal_metrics"]} for r in reports],
            "selected_operating_point": None, "quality_gate": None}
