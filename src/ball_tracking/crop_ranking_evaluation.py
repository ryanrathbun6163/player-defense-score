"""Separate scoring for ranked crops, with saved-control parity and loss audits."""
from __future__ import annotations

from dataclasses import replace

from .annotations import load_annotations
from .crop_ranking import ARMS, experiment_grid, validate_observations
from .crop_ranking_experiment import OUTPUT_ROOT, load_observations, preflight, unchanged
from .development_experiments import bound_file, canonical_sha256, read_json, safe_path
from .evaluation import evaluate_detections
from .temporal_association import RADII
from .temporal_evaluation import _runs
from .temporal_experiment import file_binding, persist_once, spec_digest
from .tiled_evaluation import METRICS, COUNTS


def selected_frame(frame, observation):
    emitted = set(observation["emitted_candidate_indices"])
    return replace(frame, detections=tuple(c for c in frame.detections if c.candidate_index in emitted))


def _evaluate_validated(labels, run, observations, radius, commit):
    view = replace(run, frames=tuple(selected_frame(f,o) for f,o in zip(run.frames,observations["frames"])))
    score = evaluate_detections(labels,view,confidence_threshold=observations["config"]["confidence_threshold"],
                                localization_radius_px=radius)
    missed = _runs([f["false_negative_count"] == 1 for f in score["frame_results"]])
    correct = _runs([f["matched_candidate_index"] is not None for f in score["frame_results"]])
    emitted = sum(bool(f["emitted_candidate_indices"]) for f in observations["frames"])
    return {"schema_version":"ball_crop_ranking_evaluation/v0.1","variant_id":observations["variant_id"],
            "config":observations["config"],"localization_radius_px":radius,
            "selection_purpose":labels.window.selection_purpose,"possession_id":run.possession_id,
            "source_video":run.source_video.to_dict(),"window":run.window.to_dict(),
            "input_model_provenance":run.model_provenance.to_dict(),
            "ranking_code_commit":observations["ranking_code_commit"],"evaluator_code_commit":commit,
            "observations_content_sha256":canonical_sha256(observations),
            "input_candidate_content_sha256":observations["input_candidate_content_sha256"],
            "annotation_content_sha256":score["annotation_content_sha256"],
            "matching_rule":"raw center distance; uncertainty diagnostic only",
            "metrics":{k:score[k] for k in METRICS},"frame_results":score["frame_results"],
            "temporal_metrics":{"emitted_frame_count":emitted,"missing_frame_count":len(run.frames)-emitted,
                                "frame_count":len(run.frames),"emitted_frame_coverage":emitted/len(run.frames),
                                "longest_consecutive_missed_eligible_run":max(missed,default=0),
                                "correct_match_run_lengths":correct},
            "selected_operating_point":None,"quality_gate":None}


def evaluate_observations(labels, run, observations, radius, commit):
    from .development_experiments import require_digest
    require_digest(commit,"evaluator commit",40)
    if radius not in RADII or isinstance(radius,bool):
        raise ValueError("Undeclared ranking evaluation radius")
    validate_observations(observations,run)
    return _evaluate_validated(labels,run,observations,radius,commit)


def aggregate(reports):
    if not reports:
        raise ValueError("Empty ranking scoring pool")
    first = reports[0]
    keys = ("variant_id","config","localization_radius_px","selection_purpose","input_model_provenance",
            "ranking_code_commit","evaluator_code_commit")
    if any(any(r[k] != first[k] for k in keys) for r in reports):
        raise ValueError("Mixed ranking settings, pools, or provenance")
    if len({r["possession_id"] for r in reports}) != len(reports):
        raise ValueError("Duplicate possession in ranking pool")
    metrics = {k:sum(r["metrics"][k] for r in reports) for k in COUNTS}
    tp,fp,fn = (metrics[k] for k in ("true_positive_count","false_positive_count","false_negative_count"))
    metrics.update(precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None)
    return {**{k:first[k] for k in keys},"metrics":metrics,"window_count":len(reports),
            "per_window":[{"possession_id":r["possession_id"],"window":r["window"],"metrics":r["metrics"],
                           "temporal_metrics":r["temporal_metrics"]} for r in reports],
            "selected_operating_point":None,"quality_gate":None}


def verify_control_parity(report, saved):
    excluded = {"input_detection_count","below_threshold_detection_count"}
    if ({k:v for k,v in report["metrics"].items() if k not in excluded}
            != {k:v for k,v in saved["metrics"].items() if k not in excluded}
            or [{k:v for k,v in f.items() if k not in excluded} for f in report["frame_results"]]
            != [{k:v for k,v in f.items() if k not in excluded} for f in saved["frame_results"]]):
        raise ValueError("Saved crop control scoring outcomes differ")


def paired_differences(reports):
    index = {(r["possession_id"],r["config"]["arm"],r["config"]["confidence_threshold"],r["localization_radius_px"]):r for r in reports}
    correct = lambda r: {f["frame_index"] for f in r["frame_results"] if f["matched_candidate_index"] is not None}
    differences, decomposition = [], []
    for report in reports:
        c = report["config"]
        if c["arm"] not in ARMS[3:]:
            continue
        raw, top_one, capped = (index[(report["possession_id"],arm,c["confidence_threshold"],report["localization_radius_px"])] for arm in ARMS[:3])
        new = correct(report)
        for baseline in (raw,top_one,capped):
            old = correct(baseline)
            differences.append({"possession_id":report["possession_id"],"config":c,
                                "radius_px":report["localization_radius_px"],"control":baseline["config"]["arm"],
                                "newly_recovered_frames":sorted(new-old),"newly_lost_frames":sorted(old-new),
                                "false_positive_delta":report["metrics"]["false_positive_count"]-baseline["metrics"]["false_positive_count"]})
        uncapped,limited = correct(raw),correct(capped)
        if not new <= limited or not limited <= uncapped:
            raise ValueError("Ranked matches must reference qualifying capped raw candidates")
        decomposition.append({"possession_id":report["possession_id"],"config":c,"radius_px":report["localization_radius_px"],
                              "raw_no_qualifying_candidate_frames":[f["frame_index"] for f in raw["frame_results"] if f["false_negative_count"]],
                              "cap_lost_frames":sorted(uncapped-limited),"additional_ranking_lost_frames":sorted(limited-new)})
    return differences,decomposition


def score_experiment(root,path):
    m,p,inputs,commit = preflight(root,path)
    saved = {purpose:read_json(bound_file(root,item,"data/outputs/ball_tracking/tiled_development"))
             for purpose,item in zip(p["pool_separation"],p["saved_crop_scoring_reports"])}
    pools = {purpose:[] for purpose in p["pool_separation"]}
    parity = 0
    for window,(_,run,digest),label in zip(p["windows"],inputs,p["scoring_labels"]):
        labels = load_annotations(bound_file(root,label["annotation"],"configs/ball_tracking/annotations"))
        if labels.window.selection_purpose != window["purpose"]:
            raise ValueError("Ranking scoring label pool mismatch")
        old = {(r["config"]["selector"],r["config"]["confidence_threshold"],r["config"]["localization_radius_px"]):r
               for r in saved[window["purpose"]]["evaluation_reports"]
               if r["possession_id"] == run.possession_id and r["config"]["image_arm"] == "four_crop_union"}
        for config in experiment_grid():
            observations = load_observations(root,m,window,run,digest,config,commit)
            for radius in RADII:
                report = _evaluate_validated(labels,run,observations,radius,commit)
                if config.arm in ARMS[:2]:
                    verify_control_parity(report,old[("raw" if config.arm == ARMS[0] else "top_one",config.confidence_threshold,radius)])
                    parity += 1
                pools[window["purpose"]].append(report)
    if parity != 540:
        raise ValueError("Incomplete saved-control parity audit")
    bindings = []
    for purpose,reports in pools.items():
        aggregates = [aggregate([r for r in reports if r["variant_id"] == c.variant_id and r["localization_radius_px"] == radius])
                      for c in experiment_grid() for radius in RADII]
        if len(reports) != 675 or any(a["window_count"] != 3 for a in aggregates):
            raise ValueError("Incomplete ranking scoring pool")
        differences,decomposition = paired_differences(reports)
        payload = {"schema_version":"ball_crop_ranking_pool/v0.1","purpose":purpose,"experiment_spec_sha256":spec_digest(m),
                   "code_commit":commit,"annotation_bindings":p["scoring_labels"],"crop_input_bindings":[w["crop_candidates"] for w in p["windows"]],
                   "evaluation_reports":reports,"aggregate_results":aggregates,"paired_differences":differences,
                   "loss_decomposition":decomposition,"saved_control_parity_cells":parity,
                   "parity_excluded_bookkeeping":["input_detection_count","below_threshold_detection_count"],
                   "selected_operating_point":None,"quality_gate":None}
        target = safe_path(root,f"{OUTPUT_ROOT}/evaluation/{purpose}.json",OUTPUT_ROOT)
        persist_once(target,payload)
        bindings.append(file_binding(root,target))
    unchanged(root,path,m,commit)
    for item in p["scoring_labels"]:
        bound_file(root,item["annotation"],"configs/ball_tracking/annotations")
    return {"reports":bindings,"per_window_reports":1350,"aggregate_cells_per_pool":225,"saved_control_parity_cells":parity}
