"""Separate, source-pixel scoring for saved whole-frame and new tiled inputs."""
from __future__ import annotations

from .annotations import load_annotations
from .development_experiments import bound_file, canonical_sha256, read_json, safe_path
from .evaluation import evaluate_detections
from .temporal_association import THRESHOLDS, RADII
from .temporal_experiment import file_binding, persist_once, spec_digest
from .tiled_candidates import candidate_run, select_run, validate_output
from .tiled_experiment import OUTPUT_ROOT, preflight, output_path, unchanged, make_header
from .detections import ModelProvenance

ARMS = ("saved_whole_frame", "four_crop_union")
SELECTORS = ("raw", "top_one")
METRICS = (
    "eligible_frame_count", "not_visible_frame_count", "unscored_frame_count", "input_detection_count",
    "below_threshold_detection_count", "true_positive_count", "false_positive_count", "false_negative_count",
    "duplicate_false_positive_count", "non_visible_false_alarm_count", "non_visible_false_alarm_frame_count",
    "non_visible_false_alarm_rate", "non_visible_false_alarms_per_100_frames", "unscored_prediction_count",
    "precision", "recall", "matched_center_error_px", "matched_effective_center_error_px",
)
COUNTS = ("eligible_frame_count", "not_visible_frame_count", "unscored_frame_count", "true_positive_count",
          "false_positive_count", "false_negative_count", "duplicate_false_positive_count",
          "non_visible_false_alarm_count", "non_visible_false_alarm_frame_count")


def configurations():
    return [(arm, selector, threshold, radius) for arm in ARMS for selector in SELECTORS for threshold in THRESHOLDS for radius in RADII]


def load_output(root, m, window, raw, baseline, commit):
    value = read_json(output_path(root, window))
    model = ModelProvenance.from_mapping(value["header"]["per_view_model_provenance"])
    from .detector_experiments import build_model_provenance
    expected_model = build_model_provenance(baseline.detector, code_commit=commit, runtime_device=model.device)
    if model != expected_model:
        raise ValueError("Tiled model provenance differs from frozen per-view detector")
    header = make_header(m, window, expected_model)
    return validate_output(value, header, raw)


def score_one(labels, run, arm, selector, threshold, radius, output_digest, commit):
    if (arm, selector, threshold, radius) not in configurations():
        raise ValueError("Undeclared comparison configuration")
    selected = select_run(run, selector, threshold)
    score = evaluate_detections(labels, selected, confidence_threshold=threshold, localization_radius_px=radius)
    return {
        "schema_version": "ball_tiled_comparison_evaluation/v0.1",
        "config": {"image_arm": arm, "selector": selector, "confidence_threshold": threshold, "localization_radius_px": radius},
        "possession_id": run.possession_id, "source_video": run.source_video.to_dict(), "window": run.window.to_dict(),
        "selection_purpose": labels.window.selection_purpose,
        "input_model_provenance": run.model_provenance.to_dict(), "evaluator_code_commit": commit,
        "tiled_output_content_sha256": output_digest,
        "evaluated_candidate_content_sha256": canonical_sha256(selected.to_dict()),
        "annotation_content_sha256": score["annotation_content_sha256"],
        "matching_rule": "raw center distance; uncertainty diagnostic only",
        "metrics": {key: score[key] for key in METRICS}, "frame_results": score["frame_results"],
        "selected_operating_point": None, "quality_gate": None,
    }


def aggregate(reports):
    if not reports:
        raise ValueError("Empty comparison pool")
    first = reports[0]
    identity = ("config", "selection_purpose", "evaluator_code_commit", "input_model_provenance")
    if any(any(r[k] != first[k] for k in identity) for r in reports):
        raise ValueError("Mixed settings/pools/provenance")
    if len({r["possession_id"] for r in reports}) != len(reports):
        raise ValueError("Duplicate possession in pool")
    totals = {k: sum(r["metrics"][k] for r in reports) for k in COUNTS}
    tp, fp, fn = (totals[k] for k in ("true_positive_count", "false_positive_count", "false_negative_count"))
    totals.update(precision=tp/(tp+fp) if tp+fp else None, recall=tp/(tp+fn) if tp+fn else None)
    return {**{k: first[k] for k in identity}, "metrics": totals, "window_count": len(reports),
            "per_window": [{"possession_id": r["possession_id"], "window": r["window"], "metrics": r["metrics"]} for r in reports],
            "selected_operating_point": None, "quality_gate": None}


def paired_differences(reports):
    indexed = {(r["possession_id"], *r["config"].values()): r for r in reports}
    result = []
    for r in reports:
        c = r["config"]
        if c["image_arm"] != "four_crop_union":
            continue
        baseline = indexed[(r["possession_id"], "saved_whole_frame", c["selector"], c["confidence_threshold"], c["localization_radius_px"])]
        correct = lambda report: {f["frame_index"] for f in report["frame_results"] if f["matched_candidate_index"] is not None}
        old, new = correct(baseline), correct(r)
        result.append({"possession_id": r["possession_id"], "config": c,
                       "newly_recovered_frames": sorted(new-old), "newly_lost_frames": sorted(old-new),
                       "false_positive_delta": r["metrics"]["false_positive_count"]-baseline["metrics"]["false_positive_count"]})
    return result


def score_experiment(root, manifest_path):
    m, p, raws, baseline, commit = preflight(root, manifest_path)
    pools = {purpose: [] for purpose in p["pool_separation"]}
    bindings, durations = [], []
    for w, raw, label in zip(p["windows"], raws, p["scoring_labels"]):
        output = load_output(root, m, w, raw, baseline, commit)
        tiled = candidate_run(raw, output)
        labels = load_annotations(bound_file(root, label["annotation"], "configs/ball_tracking/annotations"))
        if labels.window.selection_purpose != w["purpose"]:
            raise ValueError("Label pool mismatch")
        bindings.append(file_binding(root, output_path(root, w)))
        durations.append({"window_id": w["window_id"], "per_frame": [
            {"frame_index": f["frame_index"], "elapsed_seconds": f["elapsed_seconds"],
             "raw_candidate_count": len(f["candidates"]),
             "cuda_peak_allocated_bytes": max(v["cuda_peak_allocated_bytes"] for v in f["views"])} for f in output["frames"]],
             "timing_note": "Four sequential crop calls per frame, CUDA-synchronized; first model call includes lazy initialization. No saved-control timing is invented."})
        for arm, selector, threshold, radius in configurations():
            run = raw if arm == "saved_whole_frame" else tiled
            pools[w["purpose"]].append(score_one(labels, run, arm, selector, threshold, radius,
                                                 output["content_sha256"] if arm == "four_crop_union" else None, commit))
    results = []
    for purpose, reports in pools.items():
        aggregates = []
        for arm, selector, threshold, radius in configurations():
            group = [r for r in reports if list(r["config"].values()) == [arm, selector, threshold, radius]]
            if len(group) != 3:
                raise ValueError("Incomplete comparison pool")
            aggregates.append(aggregate(group))
        payload = {"schema_version": "ball_tiled_comparison_pool/v0.1", "purpose": purpose,
                   "experiment_spec_sha256": spec_digest(m), "code_commit": commit,
                   "tiled_output_bindings": bindings, "annotation_bindings": p["scoring_labels"],
                   "evaluation_reports": reports, "aggregate_results": aggregates,
                   "paired_differences": paired_differences(reports), "runtime_measurements": durations,
                   "selected_operating_point": None, "quality_gate": None}
        path = safe_path(root, f"{OUTPUT_ROOT}/evaluation/{purpose}.json", OUTPUT_ROOT)
        persist_once(path, payload)
        results.append(file_binding(root, path))
    unchanged(root, manifest_path, m, commit)
    for record in p["scoring_labels"]:
        bound_file(root, record["annotation"], "configs/ball_tracking/annotations")
    for record in bindings:
        bound_file(root, record, OUTPUT_ROOT)
    return {"reports": results, "per_window_reports": 1080, "aggregate_cells_per_pool": 180}
