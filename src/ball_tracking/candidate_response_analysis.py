"""Reference-assisted diagnostics of sealed responses; no fit or new tracks."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from types import SimpleNamespace

from . import completion_scoring as scoring
from .annotations import FrameAnnotation
from .candidate_response_features import FEATURE_NAMES
from .candidate_response_study import OUTPUT, validate_config, PROVENANCE_FIELDS
from .weak_response_capture import bind, bound, read, write_once, HOU

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "native_mass"
FEATURES = (*FEATURE_NAMES, BASELINE)


def check(value, message):
    if not value:
        raise ValueError(message)


def value(candidate, feature):
    if feature == BASELINE:
        return candidate["mass"] if candidate["native"] else None
    score = candidate["features"][feature]
    check(score is None or (not isinstance(score, bool) and isinstance(score, (int, float))
                           and math.isfinite(score)), "Invalid feature value")
    return score


def population(frame, feature, native_only=False):
    return [c for c in frame["candidates"] if c["in_bounds"]
            and (not native_only and feature != BASELINE or c["native"])]


def rank_frame(frame, feature, *, native_only=False):
    """Best geometric match versus every geometric miss; exact ties stay ties."""
    check(frame["reference_category"] == "eligible", "Ranking requires an eligible reference")
    candidates = population(frame, feature, native_only)
    correct = [c for c in candidates if c["match"]]
    known_correct = [value(c, feature) for c in correct if value(c, feature) is not None]
    misses = [c for c in candidates if not c["match"]]
    known_misses = [value(c, feature) for c in misses if value(c, feature) is not None]
    best = max(known_correct) if known_correct else None
    above = None if best is None else sum(v > best for v in known_misses)
    tied = None if best is None else sum(v == best for v in known_misses)
    status = ("no_matching_candidate" if not correct else "matching_feature_unknown" if best is None
              else "beaten" if above else "tied_first" if tied else "strict_first")
    return {"frame": frame["frame"], "candidate_count": len(candidates), "matching_candidates": len(correct),
        "known_matching_candidates": len(known_correct), "unknown_matching_candidates": len(correct)-len(known_correct),
        "unknown_miss_candidates": len(misses)-len(known_misses), "best_matching_score": best,
        "localization_misses_strictly_above": above, "localization_misses_tied": tied,
        "best_rank_among_available_features": None if above is None else 1+above,
        "worst_rank_after_miss_ties": None if above is None else 1+above+tied,
        "status_among_available_features": status, "complete_feature_ranking": len(known_correct)+len(known_misses)==len(candidates)}


def thresholds(frames, feature):
    hidden = [c for f in frames if f["reference_category"] == "certain_hidden" for c in population(f, feature)]
    valid = [c for f in frames if f["native_correct"] for c in population(f, feature) if c["is_native_selected"]]
    h = [value(c, feature) for c in hidden if value(c, feature) is not None]
    v = [value(c, feature) for c in valid if value(c, feature) is not None]
    return {"scope": "one HOU-wide reference-assisted bound; per-episode evaluation uses the same cutoff",
        "maximum_observed_certain_hidden": max(h) if h else None,
        "minimum_observed_native_correct": min(v) if v else None,
        "hidden_candidates": len(hidden), "hidden_feature_unknown": len(hidden)-len(h),
        "native_correct_points": len(valid), "native_correct_feature_unknown": len(valid)-len(v),
        "zero_hidden_claim_possible_from_available_features": bool(h) and len(h)==len(hidden),
        "all_native_correct_retention_claim_possible": bool(v) and len(v)==len(valid),
        "production_threshold": False}


def _decision(score, cutoff, strict):
    if score is None or cutoff is None:
        return "unknown"
    return "retained" if (score > cutoff if strict else score >= cutoff) else "rejected"


def evaluate_bound(frames, feature, cutoff, *, strict):
    """Unknown evidence never counts as a successful rejection or retention."""
    coverage, native, hidden, stress = Counter(), Counter(), Counter(), Counter()
    for frame in frames:
        candidates = population(frame, feature)
        if frame["reference_category"] == "eligible":
            coverage["eligible_frames"] += 1
            good = [c for c in candidates if c["match"]]
            decisions = [_decision(value(c, feature), cutoff, strict) for c in good]
            coverage["geometric_candidate_available"] += bool(good)
            coverage["matching_candidate_survives"] += "retained" in decisions
            coverage["no_known_survivor_with_unknown_matching_feature"] += "retained" not in decisions and "unknown" in decisions
        if frame["native_correct"]:
            chosen = [c for c in candidates if c["is_native_selected"]]
            check(len(chosen)==1, "Native-correct selected candidate omitted")
            native[_decision(value(chosen[0], feature), cutoff, strict)] += 1
        if frame["reference_category"] == "certain_hidden":
            hidden["reference_frames"] += 1
            decisions = [_decision(value(c, feature), cutoff, strict) for c in candidates]
            hidden.update("candidates_"+d for d in decisions)
            hidden["frames_with_known_surviving_candidate"] += "retained" in decisions
            hidden["frames_with_unknown_candidate_feature"] += "unknown" in decisions
        choice = frame["stress"]
        # Broad-pool mass is incomparable across extraction thresholds.
        if feature == BASELINE:
            stress["excluded_mass_not_comparable_across_extractions"] += 1
        elif not choice["emitted"]:
            stress["missing_selection"] += 1
        else:
            decision = _decision(choice["features"][feature], cutoff, strict)
            for tag in choice["tags"]:
                stress[tag+":"+decision] += 1
    return {"cutoff": cutoff, "comparison": ">" if strict else ">=", "available_features_only": True,
        "matching_candidate_coverage": dict(coverage), "original_native_correct_points": dict(native),
        "certain_hidden": dict(hidden), "original_expanded_weak_stress": dict(stress),
        "complete_visibility_claim": False, "new_tracking_outputs": 0}


def _outcome(point, reference, width, height):
    if point is None:
        return "missing"
    return "matched" if 0<=point[0]<width and 0<=point[1]<height and math.dist(point,reference)<=10 else "wrong"


def compare_ranks(rows, baseline):
    """Incomplete competitor evidence cannot manufacture a paired improvement."""
    paired=Counter()
    for row,base in zip(rows,baseline,strict=True):
        a,b=row["localization_misses_strictly_above"],base["localization_misses_strictly_above"]
        if not row["complete_feature_ranking"] or not base["complete_feature_ranking"]:
            paired["not_comparable_incomplete_features"]+=1
            continue
        if a is None or b is None:
            paired["not_comparable_no_matching_candidate"]+=1
            continue
        paired["fewer_strictly_higher_misses" if a<b else "more_strictly_higher_misses" if a>b else "same_strictly_higher_misses"]+=1
        if row["status_among_available_features"]=="strict_first" and base["status_among_available_features"]!="strict_first": paired["strict_first_gain_over_baseline"]+=1
        if row["status_among_available_features"]!="strict_first" and base["status_among_available_features"]=="strict_first": paired["strict_first_loss_vs_baseline"]+=1
    return dict(paired)


def join_frame(feature_row, frame, native, block, stress_original):
    """Join labels only after sealing, reusing the frozen reference-category rule."""
    check(feature_row["block_id"]==block["block_id"] and feature_row["reference_inputs_used"] is False
          and feature_row["tracking_outputs_changed"] is False, "Feature scope differs")
    check(all(feature_row[k]==native[k] for k in PROVENANCE_FIELDS)
          and feature_row["source_frame_index"]==frame["source_frame_index"]
          and feature_row["source_pts_ticks"]==frame["source_pts_ticks"]
          and feature_row["time_base"]==block["time_base"]
          and feature_row["source_png"]==frame["png"]==native["source_png"]
          and feature_row["native_selected_candidate_index"]==native["selected_candidate_index"], "Native feature join differs")
    width,height=block["source_video"]["width_px"],block["source_video"]["height_px"]
    check(feature_row["width_px"]==width and feature_row["height_px"]==height
          and frame.get("state","permitted")=="permitted", "Permitted source dimensions differ")
    annotation=frame.get("annotation")
    parsed=None if annotation is None else FrameAnnotation.from_mapping(annotation,0,SimpleNamespace(width_px=width,height_px=height))
    check(parsed is None or parsed.frame_index==frame["source_frame_index"], "Reference frame differs")
    category=scoring._category(parsed)
    reference=None if category!="eligible" else list(parsed.geometry.center_xy_px)
    native_outcome="unscored" if reference is None else _outcome(native["center_xy_px"],reference,width,height)
    candidates=[]
    for position,item in enumerate(feature_row["main_candidates"]):
        c=item["candidate"]
        check(c["candidate_index"]==position and tuple(item["descriptor"]["features"])==FEATURE_NAMES, "Candidate/feature order differs")
        point=[c["center_x"],c["center_y"]]
        check(all(math.isfinite(v) for v in point) and math.isfinite(c["native_score"]) and c["native_score"]>0,
              "Invalid observed candidate")
        in_bounds=0<=point[0]<width and 0<=point[1]<height
        check(c["in_source_bounds"]==in_bounds, "Candidate bounds flag differs")
        is_native=c["original_index"] is not None
        check(is_native==(position<len(native["candidates"])), "Native prefix differs")
        if is_native:
            check(c["original_index"]==position and all(c.get(k)==v for k,v in native["candidates"][position].items()), "Original native candidate changed")
        candidates.append({"id":position,"native":is_native,"mass":c["native_score"],"in_bounds":in_bounds,
            "match":reference is not None and in_bounds and math.dist(point,reference)<=10,
            "is_native_selected":position==native["selected_candidate_index"],"features":item["descriptor"]["features"],
            "feature_unknown_reasons":item["descriptor"]["feature_unknown_reasons"]})
    check(len(candidates)>=len(native["candidates"]), "Native candidates omitted")
    stress=feature_row["expanded_weak_selection"]
    check(stress["observation"]==stress_original, "Original broad choice changed")
    point=stress_original["center_xy_px"]
    emitted=point is not None
    outcome="unscored" if reference is None else _outcome(point,reference,width,height)
    tags=["all_emitted" if emitted else "all_missing", "reference_"+category, "outcome_"+outcome]
    if category=="eligible":
        tags.append("native_"+native_outcome)
        if native_outcome=="missing" and outcome=="matched": tags.append("correct_gain_from_native_missing")
        if native_outcome=="wrong" and outcome=="matched": tags.append("correct_gain_from_native_wrong")
        if native_outcome=="matched" and outcome!="matched": tags.append("native_correct_regression")
    bid,index=block["block_id"],frame["source_frame_index"]
    if bid.endswith("_e01") and 194<=index<=203: tags.append("prior_e01_ten_gain_cohort")
    if bid.endswith("_e05") and 14<=index<=19: tags.append("prior_e05_six_below_001_gain_cohort")
    for feature in FEATURE_NAMES:
        value({"features":stress["descriptor"]["features"]},feature)
    return {"block_id":bid,"frame":index,"reference_category":category,"native_correct":native_outcome=="matched",
        "native_outcome":native_outcome,"candidates":candidates,
        "stress":{"emitted":emitted,"features":stress["descriptor"]["features"],"tags":tags,
                  "outcome":outcome,"source_support":stress_original.get("selection_diagnostic",{}).get("selected_support")}}


def summarize(frames, shared):
    result={"frames":len(frames),"reference_categories":dict(Counter(f["reference_category"] for f in frames)),
        "main_candidates":sum(len(f["candidates"]) for f in frames),
        "out_of_bounds_candidates":sum(not c["in_bounds"] for f in frames for c in f["candidates"]),
        "stress_tags":dict(Counter(tag for f in frames for tag in f["stress"]["tags"])),"features":{}}
    for feature in FEATURES:
        ranks=[rank_frame(f,feature) for f in frames if f["reference_category"]=="eligible"]
        native_ranks=[rank_frame(f,feature,native_only=True) for f in frames if f["reference_category"]=="eligible"]
        counts=Counter(r["status_among_available_features"] for r in ranks)
        unknown=Counter()
        for f in frames:
            for c in population(f,feature):
                if value(c,feature) is None: unknown[f["reference_category"]]+=1
        t=shared[feature]
        result["features"][feature]={"scope":"native_only" if feature==BASELINE else "all_in_source_main_candidates",
            "rank_counts_among_available_features":dict(counts),"rank_frames":ranks,"native_only_rank_frames":native_ranks,
            "complete_feature_rank_frames":sum(r["complete_feature_ranking"] for r in ranks),
            "incomplete_feature_rank_frames":sum(not r["complete_feature_ranking"] for r in ranks),
            "unknown_features_by_reference_category":dict(unknown),
            "reject_all_observed_hidden_bound":evaluate_bound(frames,feature,t["maximum_observed_certain_hidden"],strict=True),
            "retain_all_observed_native_correct_bound":evaluate_bound(frames,feature,t["minimum_observed_native_correct"],strict=False)}
    for feature in FEATURE_NAMES:
        for scope,baseline in (("rank_frames","peak"),("native_only_rank_frames",BASELINE)):
            result["features"][feature]["paired_"+scope+"_vs_"+baseline]=compare_ranks(
                result["features"][feature][scope],result["features"][baseline][scope])
    return result


def execute(root=ROOT):
    root=Path(root).resolve(); directory=root/OUTPUT
    extraction_path=directory/"extraction_complete.json"
    extraction=read(extraction_path)
    check(extraction["status"]=="completed" and extraction["frames"]==960 and extraction["main_candidates"]==10778
          and extraction["stress_rows"]==960 and extraction["all_feature_rows_sealed_before_reference_analysis"] is True
          and extraction["reference_analysis_performed"] is False, "Complete sealed six-context features required")
    frozen=read(bound(root,extraction["freeze"]))
    check(bind(root,Path(__file__)) in frozen["source"], "Analysis implementation was not frozen before extraction")
    for link in frozen["source"]: bound(root,link)
    prepared=read(bound(root,extraction["prepared"]))
    check(frozen["prepared"]==extraction["prepared"] and prepared["config"]==extraction["config"], "Extraction freeze differs")
    config=read(bound(root,extraction["config"])); validate_config(config)
    check(config["analysis"]["reference_radius_source_px_inclusive"]==10,"Reference radius changed")
    package=read(bound(root,extraction["paired_inputs"]))
    entries={e["block"]["block_id"]:e for e in package["blocks"] if e["block"]["block_id"] in HOU}
    check(tuple(b["block_id"] for b in extraction["blocks"])==HOU, "Feature contexts differ")
    # Verify every table binding before any reference join, not merely one table
    # before its own episode's analysis.
    tables=[bound(root,b["features"]) for b in extraction["blocks"]]
    frames=[]
    for spec,path in zip(extraction["blocks"],tables,strict=True):
        entry=entries[spec["block_id"]]
        stress=read(bound(root,spec["expanded_choices"]))["observations"]
        rows=[json.loads(line) for line in path.open(encoding="utf-8")]
        check(len(rows)==spec["frames"]==len(entry["block"]["frames"]),"Sealed frame census differs")
        for row,frame,native,prior in zip(rows,entry["block"]["frames"],entry["candidate_observations"],stress,strict=True):
            frames.append(join_frame(row,frame,native,entry["block"],prior))
    check(len(frames)==960 and sum(len(f["candidates"]) for f in frames)==10778,"Analysis census differs")
    shared={feature:thresholds(frames,feature) for feature in FEATURES}
    result={"schema_version":"candidate_response_analysis/v0.1","status":"completed_reference_assisted_diagnosis",
        "created_at_utc":datetime.now(timezone.utc).isoformat(),"extraction":bind(root,extraction_path),
        "freeze":extraction["freeze"],"config":extraction["config"],"source":bind(root,Path(__file__)),
        "reference_category_kernel":bind(root,root/"src/ball_tracking/completion_scoring.py"),
        "reference_category_kernel_reused":True,"distance_counts_independent":True,
        "shared_HOU_bounds":shared,"episodes":[{"block_id":bid,**summarize([f for f in frames if f["block_id"]==bid],shared)} for bid in HOU],
        "pooled_descriptive_only":summarize(frames,shared),"winner_selected":False,"production_thresholds_selected":False,
        "new_selector_runs":0,"new_model_calls":0,"new_training_updates":0,"new_tracking_outputs":0,
        "protected_evaluation_access":False,"human_visual_acceptance":None,
        "limitations":["Repeatedly inspected HOU development; no fresh validation or frame-independence claim.",
            "Geometric misses are not semantic non-ball labels; unknown reference categories remain separate.",
            "Feature rankings and two shared-cutoff bounds are diagnostic only; no new coordinates or tracks emitted.",
            "Unknown descriptors are counted, never successful rejections or retentions; shape descriptors are correlated.",
            "Native mass is evaluated only on native candidates; broad selected-output mass is excluded."]}
    destination=directory/"analysis_v0_1/completed.json"
    write_once(destination,result)
    return {"status":result["status"],"analysis":bind(root,destination),"frames":len(frames),"new_selector_runs":0}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",action="store_true",required=True)
    parser.parse_args()
    print(json.dumps(execute()))


if __name__=="__main__":
    main()
