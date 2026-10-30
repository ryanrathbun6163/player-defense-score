"""Exact, metadata-only joins for the frozen saved-score failure study.

The runner verifies the protocol bindings before calling ``load_study``. This
module reads only bound JSON/JSONL files, never images, models or raw maps. All
source rows are retained; reporting annotations do not change training targets.
"""

from __future__ import annotations

import json
import math
from pathlib import Path


PILOT = "data/outputs/ball_tracking/candidate_quality_pilot_v0_1"
QUERIES = "data/outputs/ball_tracking/candidate_identity_feasibility_v0_1/point_preparation_v0_1/attempt_003"
RUN = "data/outputs/t/native_cable_training_continuation_2026-10-29_v0_1"
AUDIT = RUN + "/postrun_analysis_audit"
CHANGES = "data/outputs/ball_tracking/candidate_change_comparison_v0_1/analysis_v0_1"
PACKAGE = "data/outputs/ball_tracking/completion_campaign_v0_1/frozen_primary_package_v0_1/package.json"
PAIRED = "data/outputs/ball_tracking/wasb_continuation_v0_1/paired_review_inputs_v0_1.json"
FITS = ("leave_chi_out", "leave_den_out", "leave_sac_out", "all_nba")
HOU_BLOCKS = {f"hou-vs-okc-0022400879_e{i:02d}" for i in range(1, 7)}
RANKING_NORMALIZATION = {
    "match_strictly_first": "match_first", "strict_first": "match_first",
    "miss_strictly_first": "miss_first", "beaten": "miss_first",
    "top_tie": "top_tie", "tie_at_top": "top_tie", "tied": "top_tie",
    "match_tied_first": "top_tie", "tied_first": "top_tie", "match_miss_top_tie": "top_tie",
    "no_pool_match": "no_pool_match", "no_matching_candidate_in_pool": "no_pool_match",
    "unscored_reference": "not_eligible", "not_localization_eligible": "not_eligible",
}


class IntegrityError(ValueError):
    """A frozen source identity, population or score contract was violated."""


def require(condition, message):
    if not condition:
        raise IntegrityError(message)


def index_unique(rows, key, label):
    result = {}
    for row in rows:
        value = key(row) if callable(key) else row[key]
        require(value not in result, f"{label}: duplicate key {value!r}")
        result[value] = row
    return result


def same_keys(left, right, label):
    require(set(left) == set(right), f"{label}: key loss or unexpected keys")


def finite_score(value, label, *, missing=False):
    if value is None and missing:
        return None
    require(isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value), f"{label}: missing or nonfinite observed score")
    return value


def zero_state(value):
    if value is None:
        return "missing"
    finite_score(value, "zero_state")
    return "positive" if value > 0 else "negative" if value < 0 else "zero"


def rank_margin(candidates, eligible):
    """Full-pool margin; a missing maximum is never replaced by zero."""
    if not eligible:
        return None, "not_localization_eligible"
    matches = [r["logit"] for r in candidates if r["evaluation_category"] == "eligible_match"]
    misses = [r["logit"] for r in candidates if r["evaluation_category"] == "eligible_miss"]
    if not matches:
        return None, "no_matching_candidate"
    if not misses:
        return None, "no_eligible_miss"
    return max(matches) - max(misses), None


def crop_padding(center, width, height):
    """Arithmetic for the existing 64px floor-centered source rectangle."""
    x, y = center
    require(all(math.isfinite(v) for v in (x, y)), "crop center nonfinite")
    left, top = math.floor(x) - 32, math.floor(y) - 32
    right, bottom = left + 64, top + 64
    overlap = max(0, min(right, width) - max(left, 0)) * max(0, min(bottom, height) - max(top, 0))
    padded = 4096 - overlap
    return {"crop_box": [left, top, right, bottom], "padding_pixels": padded,
            "padding_state": "padded" if padded else "complete",
            "padding_provenance": "64px_floor_centered_rectangle_arithmetic"}


def reporting_target(frame, center, width, height):
    """Original geometric target rules, for HOU reporting correspondence only."""
    annotation = frame["annotation"]
    geometry = annotation.get("geometry")
    radius = geometry.get("uncertainty_radius_px") if geometry else None
    if center is None:
        return {"target": None, "target_group": "missing_selection", "distance_px": None,
                "recorded_uncertainty_radius_px": radius, "in_bounds": None}
    x, y = center
    require(all(isinstance(v, (int, float)) and math.isfinite(v) for v in center), "nonfinite candidate center")
    inside = 0 <= x < width and 0 <= y < height
    result = {"target": None, "target_group": "masked_unknown", "distance_px": None,
              "recorded_uncertainty_radius_px": radius, "in_bounds": inside}
    if frame["kind"] == "masked":
        return result
    require(annotation["game_ball_identity_certainty"] == "certain", "nonmasked identity must be certain")
    if frame["kind"] == "hidden":
        require(annotation["visibility"] == "not_visible" and not annotation["localization_eligible"]
                and geometry is None, "hidden annotation contract")
        return {**result, "target": 0, "target_group": "certain_hidden"}
    require(frame["kind"] == "positive" and annotation["localization_eligible"], "positive annotation contract")
    require(isinstance(radius, (int, float)) and math.isfinite(radius) and radius >= 0, "invalid uncertainty radius")
    distance = math.hypot(x - geometry["center_xy_px"][0], y - geometry["center_xy_px"][1])
    result["distance_px"] = distance
    if inside and distance <= 10:
        result.update(target=1, target_group="positive")
    elif not inside or distance > 10 + radius:
        result.update(target=0, target_group="eligible_distant_miss")
    else:
        result["target_group"] = "boundary_unknown"
    return result


def _metadata(frame, block):
    annotation = frame["annotation"]
    geometry = annotation.get("geometry") or {}
    return {
        "annotation": annotation, "kind": frame["kind"],
        "visibility": annotation.get("visibility"),
        "game_ball_identity_certainty": annotation.get("game_ball_identity_certainty"),
        "difficulty_tags": annotation.get("difficulty_tags", []),
        "recorded_uncertainty_radius_px": geometry.get("uncertainty_radius_px"),
        "geometry_source": geometry.get("source"),
        "selection_category": block.get("selection_category"),
        "selection_category_missing_reason": None if block.get("selection_category") is not None else "not_recorded_in_original_block",
        "observed_source_content": block.get("observed_source_content"),
        "reference_bindings": block.get("reference_bindings"),
        "human_review": block.get("human_review"),
        "reference_origin": block.get("reference_origin"),
        "source_frame_index": frame["source_frame_index"],
        "source_pts_ticks": frame["source_pts_ticks"], "duration_ticks": frame["duration_ticks"],
        "source_video": block["source_video"], "source_png": frame.get("source_png", frame.get("png")),
        "time_base": block["time_base"], "source_role": block["role"],
    }


def _block_source(block):
    # Every block-level field is retained without copying the entire frame list per row.
    return {key: value for key, value in block.items() if key != "frames"}


def _check_transport(frame, block, source, *, package):
    for key in ("source_frame_index", "source_pts_ticks", "duration_ticks", "annotation", "kind", "valid_output_channel"):
        require(frame[key] == source[key], f"source-frame transport {block['block_id']} {key}")
    require(frame["source_png"] == source["png"], "source PNG transport")
    require(frame["time_base"] == block["time_base"], "source timebase transport")
    require(frame["source_video"] == block["source_video"], "source video transport")
    if package:
        require(frame["game_id"] == block["game_id"] and frame["domain"] == block["domain"], "source game/domain transport")
        require(frame["original_source_role"] == block["role"] == "training", "package role changed")


def _enrich_frame(row, candidates):
    selected = [c for c in candidates if c["selected_native"]]
    require(len(selected) <= 1, "multiple selected native candidates")
    row["native_logit"] = selected[0]["logit"] if selected else None
    row["native_selected_logit"] = row["native_logit"]
    row["native_zero_state"] = zero_state(row["native_logit"])
    row["native_correct_logit"] = row["native_logit"] if row["native_correct"] else None
    if row["native_correct"]:
        require(selected and selected[0]["evaluation_category"] == "eligible_match", "native-correct candidate transport")
    matches = [c for c in candidates if c["evaluation_category"] == "eligible_match"]
    hidden = [c for c in candidates if c["evaluation_category"] == "certain_hidden"]
    weak_matches = [c for c in matches if c["native_or_weak"] == "weak"]
    row.update(candidate_count=len(candidates), matching_candidate_count=len(matches),
               any_match_max_logit=max((c["logit"] for c in matches), default=None),
               weak_match_max_logit=max((c["logit"] for c in weak_matches), default=None),
               weak_matching_candidate_count=len(weak_matches),
               hidden_max_logit=max((c["logit"] for c in hidden), default=None),
               hidden_positive_count=sum(c["logit"] > 0 for c in hidden),
               positive_matching_candidate_count=sum(c["logit"] > 0 for c in matches))
    row["rank_margin"], row["rank_margin_null_reason"] = rank_margin(candidates, row["eligible"])
    cross = row["cross_tab"]
    for local, original in (("candidate_count", "candidate_count"), ("matching_candidate_count", "matching_candidates"),
                            ("positive_matching_candidate_count", "positive_matching_candidates"),
                            ("native_correct", "native_correct"), ("native_correct_logit", "native_correct_logit")):
        require(row[local] == cross[original], f"cross-tab transport {row['frame_key']} {local}")


def load_study(root, spec):
    """Load and join the exact frozen populations after runner binding checks."""
    root = Path(root)
    bound = {b["path"] for b in spec["input_bindings"]}

    def read(path):
        require(path in bound, f"unbound input: {path}")
        with (root / path).open(encoding="utf-8") as handle:
            if path.endswith(".jsonl"):
                return [json.loads(line) for line in handle if line.strip()]
            return json.load(handle)

    prep_frames = read(PILOT + "/preparation/frames.jsonl")
    prep_candidates = read(PILOT + "/preparation/candidates.jsonl")
    package_outcomes = read(PILOT + "/attempt_005/package_analysis/frames.jsonl")
    frame_index = index_unique(prep_frames, "frame_id", "package frames")
    candidate_index = index_unique(prep_candidates, "candidate_id", "package candidates")
    outcome_index = index_unique(package_outcomes, lambda x: x["frame"]["frame_id"], "package outcomes")
    same_keys(frame_index, outcome_index, "package frames/outcomes")
    require([r["frame"] for r in package_outcomes] == prep_frames, "package frame sequence/content transport")
    require([c["candidate_id"] for r in package_outcomes for c in r["candidate_scores"]]
            == [c["candidate_id"] for c in prep_candidates]
            == [cid for f in prep_frames for cid in f["candidate_ids"]], "candidate sequence transport")
    cross_rows = read(AUDIT + "/rank_zero_crosstab_rows.jsonl")
    cross_index = index_unique(cross_rows, lambda x: (x["context"], x["frame_id"]), "cross-tab")
    manifests, weights, fit_scores = {}, {}, {}
    for fit in FITS:
        manifest = read(PILOT + f"/preparation/fits/{fit}/manifest.json")
        weight = index_unique(read(PILOT + f"/preparation/fits/{fit}/weights.jsonl"), "candidate_id", fit + " weights")
        scores = index_unique(read(PILOT + f"/attempt_005/{fit}/package_scores.jsonl"), "candidate_id", fit + " scores")
        require(manifest["fit_id"] == fit, "fit ID transport")
        expected_weight = {c["candidate_id"] for c in prep_candidates if c["domain"] == "nba"
                           and c["game_id"] in manifest["fit_game_ids"] and c["target"] is not None}
        expected_score = {c["candidate_id"] for c in prep_candidates if fit == "all_nba"
                          or c["game_id"] in manifest["held_out_game_ids"]}
        same_keys(weight, expected_weight, fit + " fitting membership")
        same_keys(scores, expected_score, fit + " score membership")
        for w in weight.values():
            require(finite_score(w["objective_weight"], "objective weight") > 0, "nonpositive objective weight")
            require(finite_score(w["training_multiplier"], "training multiplier") > 0, "nonpositive training multiplier")
        for s in scores.values():
            finite_score(s["quality_logit"], "package score")
        manifests[fit], weights[fit], fit_scores[fit] = manifest, weight, scores
    package = read(PACKAGE)
    blocks = index_unique(package["training_blocks"], "block_id", "training blocks")
    block_frames = {bid: index_unique(b["frames"], "source_frame_index", bid + " source frames") for bid, b in blocks.items()}
    frames, candidates = [], []
    for frame in prep_frames:
        fid, bid = frame["frame_id"], frame["block_id"]
        block = blocks[bid]
        source_frame = block_frames[bid][frame["source_frame_index"]]
        _check_transport(frame, block, source_frame, package=True)
        outcome = outcome_index[fid]
        saved_candidates = index_unique(outcome["candidate_scores"], "candidate_id", fid + " scores")
        metadata = _metadata(frame, block)
        for context, saved in outcome["scoring_contexts"].items():
            fit = saved["fit"]
            cross = cross_index[(context, fid)]
            require(cross["population"] == "package" and cross["block_id"] == bid
                    and cross["game_id"] == frame["game_id"] and cross["rank"] == saved["ranking"], "package cross-tab identity")
            require(saved["ranking"] in RANKING_NORMALIZATION, "unknown package ranking")
            row = {**metadata, "frame_key": context + "|" + fid, "frame_id": fid,
                   "context": context, "fit": fit, "game_id": frame["game_id"], "block_id": bid,
                   "domain": frame["domain"], "cross_tab": cross, "eligible": cross["eligible"],
                   "reference_category": cross["reference_category"], "ranking": saved["ranking"],
                   "ranking_normalized": RANKING_NORMALIZATION[saved["ranking"]],
                   "native_outcome": saved["native_outcome"], "native_correct": cross["native_correct"],
                   "source": {"frame": frame, "outcome": saved, "block": _block_source(block), "source_frame": source_frame}}
            pool = []
            for cid in frame["candidate_ids"]:
                candidate, score = candidate_index[cid], saved_candidates[cid]
                for key in ("frame_id", "block_id", "game_id", "source_frame_index", "source_pts_ticks", "time_base", "source_video_sha256", "source_png"):
                    require(candidate[key] == frame[key], "package candidate transport " + key)
                require(candidate["candidate_index"] == score["candidate_index"]
                        and candidate["native_or_weak"] == score["native_or_weak"]
                        and candidate["center_xy_px"] == score["center_xy_px"]
                        and candidate["target"] == score["fitting_target"]
                        and candidate["target_group"] == score["fitting_target_group"], "candidate score identity/target")
                logit = score["held_out_logit"] if context == "nba_out_of_fold" else score["all_nba_logit"]
                require(finite_score(logit, "package saved score") == fit_scores[fit][cid]["quality_logit"], "package score transport")
                producer = candidate["producer_candidate"]
                weight = weights[fit].get(cid)
                padding = crop_padding(candidate["center_xy_px"], candidate["width_px"], candidate["height_px"])
                item = {**metadata, **padding, "row_key": context + "|" + cid, "candidate_id": cid,
                        "query_id": None, "frame_key": row["frame_key"], "frame_id": fid,
                        "context": context, "fit": fit, "game_id": frame["game_id"], "block_id": bid,
                        "domain": frame["domain"], "cohort": "package", "native_or_weak": candidate["native_or_weak"],
                        "selected_native": candidate["native_or_weak"] == "native" and candidate["candidate_index"] == frame["native_selected_candidate_index"],
                        "evaluation_category": score["evaluation_category"], "target_group": candidate["target_group"],
                        "target": candidate["target"], "logit": logit, "zero_state": zero_state(logit),
                        "native_score": producer.get("native_score"), "component_pixels": producer.get("component_pixels"),
                        "extraction": producer.get("extraction"), "threshold": producer.get("threshold"),
                        "in_bounds": candidate["in_source_bounds"], "distance_px": candidate["distance_px"],
                        "fitting_member": weight is not None, "objective_weight": weight["objective_weight"] if weight else None,
                        "training_multiplier": weight["training_multiplier"] if weight else None,
                        "fitting_exclusion_reason": None if weight else ("unknown_fitting_target" if candidate["target"] is None else "source_game_excluded_by_fit"),
                        "source": {"candidate": candidate, "score": score, "fit_score": fit_scores[fit][cid], "weight": weight}}
                pool.append(item)
            _enrich_frame(row, pool)
            for key in ("any_match_max_logit", "weak_match_max_logit", "hidden_max_logit", "native_selected_logit"):
                require(row[key] == saved[key], "saved frame score transport " + key)
            frames.append(row)
            candidates.extend(pool)

    queries = index_unique(read(QUERIES + "/queries.jsonl"), "query_id", "queries")
    inputs = index_unique(read(QUERIES + "/inputs.jsonl"), "input_id", "inputs")
    targets = index_unique(read(PILOT + "/evaluation/query_targets.jsonl"), "query_id", "query targets")
    development = index_unique(read(PILOT + "/attempt_005/all_nba/development_scores.jsonl"), "query_id", "development scores")
    same_keys(queries, targets, "query/target membership")
    same_keys(development, {qid for qid, q in queries.items() if q["input_id"] is not None}, "observed development membership")
    same_keys(inputs, {q["input_id"] for q in queries.values() if q["input_id"] is not None}, "crop input membership")
    hou_outcomes = read(PILOT + "/attempt_005/all_nba/quality_evaluation/frames.jsonl")
    hou_index = index_unique(hou_outcomes, lambda x: (x["block_id"], x["frame"]), "HOU outcomes")
    paired = read(PAIRED)
    hou_blocks = index_unique([x["block"] for x in paired["blocks"] if x["block"]["block_id"] in HOU_BLOCKS], "block_id", "HOU blocks")
    same_keys(hou_blocks, HOU_BLOCKS, "HOU block membership")
    hou_sources = {(bid, f["source_frame_index"]): (block, f) for bid, block in hou_blocks.items() for f in block["frames"]}
    require(len(hou_sources) == sum(len(b["frames"]) for b in hou_blocks.values()), "duplicate HOU source frames")
    same_keys(hou_sources, hou_index, "HOU source/outcome membership")
    hou_frames = {}
    for key, outcome in hou_index.items():
        bid, number = key
        block, sf = hou_sources[key]
        require(block["role"] == "checkpoint_validation", "HOU source role changed")
        fid, context = f"{bid}:{number}", "HOU_development"
        cross = cross_index[(context, fid)]
        require(cross["population"] == "HOU" and cross["block_id"] == bid
                and cross["frame"] == number and cross["game_id"] == block["game_id"], "HOU cross-tab source identity")
        rank = outcome["ranking"]["status"]
        require(cross["rank"] == rank and rank in RANKING_NORMALIZATION, "HOU ranking transport")
        metadata = _metadata(sf, block)
        row = {**metadata, "frame_key": context + "|" + fid, "frame_id": fid, "context": context,
               "fit": "all_nba", "game_id": block["game_id"], "block_id": bid, "domain": "nba",
               "cross_tab": cross, "eligible": cross["eligible"], "reference_category": outcome["reference_category"],
               "ranking": rank, "ranking_normalized": RANKING_NORMALIZATION[rank],
               "native_outcome": outcome["native_outcome"], "native_correct": outcome["native_correct"],
               "stress_tags": outcome["stress_tags"],
               "source": {"outcome": outcome, "source_frame": sf, "block": _block_source(block)}}
        hou_frames[key] = row
    historical_sources = index_unique(read(PILOT + "/attempt_005/all_nba/quality_evaluation/historical.jsonl"), "query_id", "historical outcomes")
    same_keys(historical_sources, {qid for qid, q in queries.items() if q["cohort"] == "historical"}, "historical membership")
    choices = index_unique(read(CHANGES + "/choices.jsonl"), lambda x: (x["block_id"], x["frame"]), "old choice frames")
    same_keys(choices, hou_index, "old choice frames")
    query_rows = {}
    for qid, query in queries.items():
        target = targets[qid]
        cohort = query["cohort"]
        require(target["cohort"] == cohort and not target["fit_eligible"] and not target["threshold_selection_eligible"], "development roles changed")
        require(target["block_id"] == query["block_id"] and target["frame"] == query["source_frame_index"], "query target identity")
        input_row = inputs.get(query["input_id"])
        missing = query["input_id"] is None
        require(target["missing"] == missing, "missing query transport")
        logit = None if missing else finite_score(development[qid]["quality_logit"], "development score")
        if input_row:
            require(qid in input_row["query_ids"], "crop input query membership")
            for key in ("source_png", "source_video", "source_pts_ticks", "time_base"):
                require(query[key] == input_row[key], "crop input transport " + key)
            identity = input_row["identity"]
            require(identity["source_video_sha256"] == query["source_video"]["sha256"]
                    and identity["source_frame_index"] == query["source_frame_index"]
                    and identity["source_rgb_sha256"] == query["source_png"]["rgb_sha256"]
                    and identity["crop_box"] == query["geometry"]["crop_box"], "crop identity transport")
        if cohort == "historical":
            parent, sf = None, None
            metadata = {"annotation": None, "kind": None, "visibility": None,
                        "game_ball_identity_certainty": None, "difficulty_tags": [],
                        "geometry_source": None, "selection_category": None,
                        "selection_category_missing_reason": "historical_semantic_schema",
                        "observed_source_content": None, "reference_bindings": None,
                        "human_review": None, "reference_origin": None,
                        "source_pts_ticks": query["source_pts_ticks"], "duration_ticks": query.get("duration_ticks"),
                        "source_video": query["source_video"], "source_png": query["source_png"],
                        "time_base": query["time_base"], "source_role": query["source_role"]}
            require(query["source_role"] == target["screen_role"] and query["source_role"] in
                    {"reference_bank", "resolved_check", "unresolved_audit", "exposed_regression"}, "historical source role changed")
            group = {"target": None, "target_group": "historical", "in_bounds": None, "distance_px": None,
                     "recorded_uncertainty_radius_px": None}
            evaluation = "historical"
        else:
            key = query["block_id"], query["source_frame_index"]
            parent = hou_frames[key]
            block, sf = hou_sources[key]
            metadata = _metadata(sf, block)
            for name in ("source_pts_ticks", "duration_ticks"):
                require(query[name] == sf[name], "HOU source timing transport")
            require(query["source_png"] == sf["png"] and query["source_video"] == block["source_video"]
                    and query["time_base"] == block["time_base"] and query["source_role"] == block["role"], "HOU query source transport")
            group = reporting_target(sf, query["center_xy_px"], block["source_video"]["width_px"], block["source_video"]["height_px"])
            if missing:
                evaluation = "missing"
            elif target["reference_category"] == "eligible":
                evaluation = "eligible_match" if target["quality_target"] == 1 else "eligible_miss"
            elif sf["kind"] == "hidden":
                evaluation = "certain_hidden"
            else:
                evaluation = "masked_unknown"
            if cohort == "HOU_main":
                require(group["in_bounds"] == target["in_bounds"], "HOU bounds transport")
            if cohort == "HOU_main" and target["reference_category"] == "eligible":
                require(math.isclose(group["distance_px"], target["localization_distance_px"], abs_tol=1e-9), "HOU distance transport")
        producer = query.get("candidate") or {}
        observation = query.get("observation") or {}
        geometry = query["geometry"]
        padded = geometry.get("padded_native_pixels")
        require(padded is None if missing else isinstance(padded, int) and 0 <= padded <= 4096, "query padding contract")
        stress_choice = None
        if cohort == "HOU_stress":
            stress_choice = choices[(query["block_id"], query["source_frame_index"])]["choices"]["sequence_weak"]
            require((stress_choice["state"] != "observed") == missing, "stress choice missingness transport")
            if missing:
                origin = "inapplicable_missing"
            else:
                require(stress_choice["query_id"] == qid and stress_choice["center_xy_px"] == query["center_xy_px"], "stress choice query transport")
                extraction = stress_choice["extraction"]
                require(extraction in {"native_component", "broad_weak_selected"}, "unknown saved stress extraction")
                origin = "native" if extraction == "native_component" else "weak"
        else:
            origin = ("native" if target["native"] else "weak") if cohort == "HOU_main" else "inapplicable_historical"
        row = {**metadata, **group, "row_key": ("HOU_development" if parent else "historical") + "|" + qid,
               "candidate_id": None, "query_id": qid, "frame_key": parent["frame_key"] if parent else None,
               "frame_id": parent["frame_id"] if parent else None, "context": "HOU_development" if parent else "historical",
               "fit": "all_nba", "game_id": parent["game_id"] if parent else None,
               "block_id": query["block_id"], "source_frame_index": query["source_frame_index"], "cohort": cohort,
               "native_or_weak": origin, "selected_native": bool(target.get("is_native_selected")) if cohort == "HOU_main" else False,
               "evaluation_category": evaluation, "logit": logit, "zero_state": zero_state(logit),
               "native_score": producer.get("native_score", observation.get("native_score")),
               "component_pixels": producer.get("component_pixels"),
               "extraction": stress_choice.get("extraction") if stress_choice else producer.get("extraction"),
               "threshold": producer.get("threshold"), "padding_pixels": padded,
               "padding_state": "inapplicable_missing" if missing else "padded" if padded else "complete",
               "crop_box": geometry.get("crop_box"), "padding_provenance": "saved_crop_geometry",
               "fitting_member": False, "objective_weight": None, "training_multiplier": None,
               "fitting_exclusion_reason": "development_excluded" if parent else "historical_semantic_audit",
               "target_derivation": "reporting_only_original_positive_hidden_distant_boundary_rules" if parent else "semantic_not_geometric",
               "original_evaluation_target": target["quality_target"],
               "stress_tags": parent.get("stress_tags", []) if parent else [],
               "source": {"query": query, "input": input_row, "target": target,
                          "score": development.get(qid), "historical": historical_sources.get(qid),
                          "stress_choice": stress_choice}}
        candidates.append(row)
        query_rows[qid] = row
    for key, row in hou_frames.items():
        saved = hou_index[key]
        pool = [query_rows[qid] for qid in saved["main_query_ids"]]
        require(all(c["cohort"] == "HOU_main" and c["frame_key"] == row["frame_key"] for c in pool), "HOU main membership")
        score_rows = index_unique(saved["main_scores"], "query_id", "HOU main scores")
        same_keys(score_rows, saved["main_query_ids"], "HOU main score membership")
        for candidate in pool:
            require(candidate["logit"] == score_rows[candidate["query_id"]]["quality_logit"], "HOU main logit transport")
        stress = query_rows[saved["stress_query_id"]]
        require(stress["cohort"] == "HOU_stress" and stress["frame_key"] == row["frame_key"]
                and stress["logit"] == saved["stress_image_logit"], "HOU stress transport")
        _enrich_frame(row, pool)
        frames.append(row)
    same_keys({qid for f in hou_outcomes for qid in f["main_query_ids"]}, {qid for qid, q in queries.items() if q["cohort"] == "HOU_main"}, "complete main population")
    same_keys({f["stress_query_id"] for f in hou_outcomes}, {qid for qid, q in queries.items() if q["cohort"] == "HOU_stress"}, "complete stress population")
    same_keys({(r["context"], r["frame_id"]) for r in frames}, cross_index, "complete context-frame population")
    historical = []
    for qid, saved in historical_sources.items():
        require(saved["quality_logit"] == query_rows[qid]["logit"], "historical score transport")
        historical.append({**saved, "joined_candidate": query_rows[qid], "source": saved})

    source_choices = []
    for key, source in choices.items():
        parent = hou_frames[key]
        require(len(source["choices"]) == 7, "seven old choice arms required")
        for name in ("source_video", "source_pts_ticks", "duration_ticks", "time_base"):
            require(source[name] == parent[name], "choice source transport")
        for arm, choice in source["choices"].items():
            observed = choice["state"] == "observed"
            qid = choice.get("query_id")
            logit = query_rows[qid]["logit"] if observed else None
            require(not observed or logit is not None, "observed choice missing score")
            if observed:
                query = queries[qid]
                require(query["block_id"] == key[0] and query["source_frame_index"] == key[1]
                        and query["source_png"] == choice["source_png"]
                        and query["center_xy_px"] == choice["center_xy_px"], "choice query transport")
            source_choices.append({**choice, "row_key": f"{arm}|{key[0]}:{key[1]}", "arm": arm,
                                   "frame_key": parent["frame_key"], "block_id": key[0], "frame": key[1],
                                   "logit": logit, "zero_state": zero_state(logit), "source": choice,
                                   "source_frame_metadata": {k: v for k, v in source.items() if k != "choices"}})
    comparisons = index_unique(read(CHANGES + "/comparisons.jsonl"), "row_id", "comparisons")
    saved_contrasts = read(PILOT + "/attempt_005/all_nba/quality_evaluation/contrasts.jsonl")
    same_keys(index_unique(saved_contrasts, "row_id", "quality contrasts"), comparisons, "contrast membership")
    contrasts = []
    for saved in saved_contrasts:
        comparison = comparisons[saved["row_id"]]
        key = saved["block_id"], saved["frame"]
        source = choices[key]
        for name in ("contrast", "role", "block_id", "frame", "tags", "choice_state", "coordinate_agreement", "candidate_identity_agreement", "reference_category", "outcome_transition"):
            require(saved[name] == comparison[name], "contrast transport " + name)
        for side in ("source", "target"):
            choice = comparison[side + "_choice"]
            require(choice == source["choices"][comparison[side + "_arm"]], "contrast choice transport")
            expected = query_rows[choice["query_id"]]["logit"] if choice["state"] == "observed" else None
            require(saved[side + "_quality"]["image_quality_logit"] == expected, "contrast observed/missing image logit transport")
        contrasts.append({**saved, "frame_key": hou_frames[key]["frame_key"],
                          "source_comparison": comparison, "source_choice_frame": {k: v for k, v in source.items() if k != "choices"}, "source": saved})
    controls_paths = {
        "prepared": PILOT + "/preparation/prepared.json",
        "evaluation_completed": PILOT + "/evaluation/completed.json",
        "pilot_completed": PILOT + "/attempt_005/completed.json",
        "package_summary": PILOT + "/attempt_005/package_analysis/summary.json",
        "hou_completed": PILOT + "/attempt_005/all_nba/quality_evaluation/completed.json",
        "rank_zero_crosstab": AUDIT + "/rank_zero_crosstab.json",
        "completed_score_audit": AUDIT + "/completed_score_audit.json",
        "source_roles": "configs/ball_tracking/completion_campaign/source_roles_v0_1.json",
        "completed_tables": RUN + "/postrun_report/completed_tables_001.json",
        "paired_and_adverse_case_interpretation": AUDIT + "/paired_and_adverse_case_interpretation.json",
        "complete_pilot_interpretation": AUDIT + "/complete_pilot_interpretation.json",
        "results_report_review_final_supplement": AUDIT + "/results_report_review_final_supplement.json",
    }
    counts = {
        "package_frames": len(prep_frames), "unique_package_candidates": len(prep_candidates),
        "nba_paired_frames": sum(f["domain"] == "nba" for f in prep_frames),
        "nba_paired_candidates": sum(c["domain"] == "nba" for c in prep_candidates),
        "nfhs_frames": sum(f["domain"] == "nfhs" for f in prep_frames),
        "nfhs_candidates": sum(c["domain"] == "nfhs" for c in prep_candidates),
        "HOU_frames": len(hou_frames), "context_frame_rows": len(frames),
        "package_context_score_slots": sum(c["cohort"] == "package" for c in candidates),
        "development_query_slots": len(queries), "all_context_score_slots": len(candidates),
        "observed_score_slots": sum(c["logit"] is not None for c in candidates),
        "missing_stress_image_slots": sum(c["cohort"] == "HOU_stress" and c["logit"] is None for c in candidates),
        "old_choice_slots": len(source_choices), "old_contrasts": len(contrasts), "historical_rows": len(historical),
    }
    require(counts == spec["units"], f"frozen population mismatch: {counts!r}")
    for row in candidates:
        reason = ("missing_image_selection" if row["logit"] is None else
                  "historical_semantic_schema" if row["cohort"] == "historical" else
                  "not_recorded_in_stress_selection_schema" if row["cohort"] == "HOU_stress" else
                  "not_recorded_or_inapplicable_in_original_schema")
        row["metadata_missing_reasons"] = {
            field: reason for field in ("native_score", "component_pixels", "extraction", "threshold",
                                       "padding_pixels", "geometry_source", "recorded_uncertainty_radius_px",
                                       "selection_category", "in_bounds", "distance_px") if row.get(field) is None}
    index_unique(frames, "frame_key", "joined frames")
    index_unique(candidates, "row_key", "joined candidates")
    return {"frames": frames, "candidates": candidates, "contrasts": contrasts,
            "historical": historical, "weights": weights, "manifests": manifests,
            "controls": {key: read(path) for key, path in controls_paths.items()},
            "source_choices": source_choices,
            "validation": {"counts": counts, "exact_transport_checks_passed": True,
                           "binding_verification": "runner_required_before_load", "ranking_normalization": RANKING_NORMALIZATION,
                           "no_pixels_models_or_raw_maps_read": True}}
