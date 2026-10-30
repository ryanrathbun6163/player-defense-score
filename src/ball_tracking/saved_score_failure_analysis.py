"""Descriptive, standard-library consumers of frozen saved-score study rows.

No model calls, image operations, fitted parameters or operating-point selection.
The data module owns source transport; this module retains full-pool frame states
and produces the prospectively specified marginal metadata/support tables.
"""
from collections import Counter, defaultdict
import json
import math


SUPPORT_FAMILIES = ("all", "visibility", "difficulty_tag", "uncertainty_radius",
                    "extraction_threshold", "padding_state")
FRAME_FAMILIES = ("all", "visibility", "identity_certainty", "difficulty_tag",
                  "uncertainty_radius", "geometry_source", "selection_category",
                  "candidate_count", "matching_candidate_count")
CANDIDATE_FAMILIES = ("all", "native_or_weak", "evaluation_category", "target_group",
                      "visibility", "difficulty_tag", "uncertainty_radius",
                      "extraction_threshold", "padding_state", "selection_category")


def token(value):
    """Stable keys: numerically equal measurements share a category.

    JSON may serialize the same recorded radius as 4 or 4.0. They are the same
    measurement, without rounding or binning any nonintegral value. Original
    source metadata remains untouched; null and string labels remain distinct.
    """
    def canonical(item):
        if isinstance(item, float) and math.isfinite(item) and item.is_integer():
            return int(item)
        if isinstance(item, dict):
            return {key: canonical(val) for key, val in item.items()}
        if isinstance(item, (list, tuple)):
            return [canonical(val) for val in item]
        return item

    return json.dumps(canonical(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def numeric_summary(values):
    vals = []
    missing = 0
    for value in values:
        if value is None:
            missing += 1
        elif isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("Nonfinite/non-numeric observed summary value")
        else:
            vals.append(float(value))
    vals.sort()

    def quantile(p):
        if not vals:
            return None
        idx = (len(vals) - 1) * p
        lo, hi = math.floor(idx), math.ceil(idx)
        return vals[lo] + (vals[hi] - vals[lo]) * (idx - lo)

    return {"observed_count": len(vals), "missing_count": missing,
            "min": vals[0] if vals else None, "median": quantile(.5),
            "max": vals[-1] if vals else None,
            "q25": quantile(.25) if len(vals) >= 4 else None,
            "q75": quantile(.75) if len(vals) >= 4 else None,
            "quartiles_reason": None if len(vals) >= 4 else "fewer_than_four_observed"}


def sign(value):
    if value is None:
        return "missing"
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Observed logit must be finite")
    return "positive" if value > 0 else "negative" if value < 0 else "zero"


def metadata(row, family):
    ann = row.get("annotation") or {}
    geometry = ann.get("geometry") or {}
    if family == "all":
        return ["all"]
    if family == "difficulty_tag":
        tags = row.get("difficulty_tags", ann.get("difficulty_tags"))
        if tags is None:
            return [None]
        return sorted(set(tags)) or ["no_tag"]
    if family == "extraction_threshold":
        return [[row.get("extraction"), row.get("threshold")]]
    fallbacks = {
        "visibility": ann.get("visibility"),
        "identity_certainty": row.get("game_ball_identity_certainty", ann.get("game_ball_identity_certainty")),
        "uncertainty_radius": row.get("recorded_uncertainty_radius_px", geometry.get("uncertainty_radius_px")),
        "geometry_source": geometry.get("source"),
    }
    return [row.get(family, fallbacks.get(family))]


def scopes(row, candidate=False):
    base = {"context": row["context"]}
    if candidate:
        base["cohort"] = row["cohort"]
    yield {**base, "scope": "context", "game_id": None, "block_id": None}
    yield {**base, "scope": "game", "game_id": row.get("game_id"), "block_id": None}
    yield {**base, "scope": "block", "game_id": row.get("game_id"), "block_id": row.get("block_id")}


def index_unique(rows, key, label):
    result = {}
    for row in rows:
        value = row[key]
        if value in result:
            raise ValueError(f"Duplicate {label}: {value}")
        result[value] = row
    return result


def frame_states(frames, candidates):
    main = defaultdict(list)
    for row in candidates:
        if row["cohort"] in ("package", "HOU_main"):
            main[row["frame_key"]].append(row)
    result = {}
    for row in frames:
        old = row["cross_tab"]
        points = main[row["frame_key"]]
        eligible = old["eligible"]
        native_correct = old.get("native_correct", row.get("native_correct", False))
        selected = [p for p in points if p.get("selected_native")]
        if len(selected) > 1:
            raise ValueError("Multiple selected native candidates")
        native_logit = row.get("native_selected_logit", selected[0]["logit"] if selected else old.get("native_correct_logit"))
        native_sign = sign(native_logit)
        weak = [p for p in points if p.get("native_or_weak") == "weak" and p["evaluation_category"] == "eligible_match"]
        hidden = old["reference_category"] in ("hidden", "certain_hidden")
        any_match_count = old["positive_matching_candidates"] if eligible else None
        matches = old["matching_candidates"] if eligible else None
        outcome = row.get("native_outcome", old.get("native_outcome"))
        result[row["frame_key"]] = {
            "eligible": eligible, "reference_category": old["reference_category"],
            "ranking": row["ranking_normalized"],
            "matching_candidate_count": matches,
            "empty_pool": len(points) == 0,
            "no_pool_match": eligible and matches == 0,
            "any_match_positive": (any_match_count > 0) if eligible else None,
            "matching_exact_zero_candidates": sum(p["evaluation_category"] == "eligible_match" and p["zero_state"] == "zero" for p in points) if eligible else None,
            "native_outcome": outcome, "native_correct": native_correct,
            "native_zero_state": native_sign,
            "native_correct_positive": native_correct and native_sign == "positive",
            "native_correct_rejected": native_correct and native_sign in ("negative", "zero"),
            "weak_matching_candidates": len(weak),
            "weak_match_frame": bool(weak),
            "weak_match_positive": any(p["zero_state"] == "positive" for p in weak),
            "certain_hidden": hidden,
            "hidden_survivor": any(p["zero_state"] == "positive" for p in points) if hidden else None,
            "hidden_surviving_candidates": sum(p["zero_state"] == "positive" for p in points) if hidden else None,
        }
    return result


def frame_counts(rows, states):
    counts = Counter()
    categories = Counter()
    ranks = Counter()
    joint = Counter()
    for row in rows:
        state = states[row["frame_key"]]
        counts["context_frames"] += 1
        for key in ("eligible", "empty_pool", "no_pool_match", "native_correct", "native_correct_positive",
                    "native_correct_rejected", "weak_match_frame", "weak_match_positive", "certain_hidden"):
            counts[key] += bool(state[key])
        if state["eligible"]:
            counts["eligible_any_match_positive"] += bool(state["any_match_positive"])
            counts["eligible_without_positive_match"] += not state["any_match_positive"]
        if state["certain_hidden"]:
            counts["hidden_survivor_frames"] += bool(state["hidden_survivor"])
            counts["hidden_surviving_candidates"] += state["hidden_surviving_candidates"]
        # Positive is already counted above; negative/zero/missing use separate
        # sign counters. Counting the positive suffix again doubles retention.
        if state["native_correct"] and state["native_zero_state"] != "positive":
            counts["native_correct_" + state["native_zero_state"]] += 1
        categories[state["reference_category"]] += 1
        ranks[state["ranking"]] += 1
        joint[token({k: state[k] for k in ("ranking", "any_match_positive", "native_outcome", "native_zero_state", "weak_match_frame", "weak_match_positive", "hidden_survivor")})] += 1
    return {"unit": "context_frame", "denominator": len(rows), "counts": dict(counts),
            "reference_categories": dict(categories), "full_pool_ranks": dict(ranks),
            "joint_states": [{"state": json.loads(k), "count": v} for k, v in sorted(joint.items())],
            "rank_margin": numeric_summary(r.get("rank_margin") for r in rows),
            "rank_margin_null_reasons": dict(Counter(r.get("rank_margin_null_reason") for r in rows if r.get("rank_margin") is None)),
            "native_correct_logit": numeric_summary((r["cross_tab"].get("native_correct_logit") if r["cross_tab"].get("native_correct") else None) for r in rows)}


def grouped_frames(frames, states):
    groups = defaultdict(list)
    for row in frames:
        for scope in scopes(row):
            for family in FRAME_FAMILIES:
                for value in metadata(row, family):
                    key = token({**scope, "family": family, "value": value})
                    groups[key].append(row)
    return [{**json.loads(key), **frame_counts(rows, states)} for key, rows in sorted(groups.items())]


def candidate_counts(rows, states):
    fkeys = {r["frame_key"] for r in rows if r.get("frame_key") is not None}
    categories = Counter(r["evaluation_category"] for r in rows)
    zeros = Counter(r["zero_state"] for r in rows)
    joint = Counter((r["evaluation_category"], r["zero_state"], bool(r.get("selected_native"))) for r in rows)
    parent = Counter()
    parent_frames = defaultdict(set)
    for row in rows:
        fkey = row.get("frame_key")
        if fkey in states:
            s = states[fkey]
            key = token({"ranking": s["ranking"], "any_match_positive": s["any_match_positive"],
                         "native_outcome": s["native_outcome"], "native_zero_state": s["native_zero_state"],
                         "weak_match_frame": s["weak_match_frame"], "weak_match_positive": s["weak_match_positive"],
                         "hidden_survivor": s["hidden_survivor"]})
            parent[key] += 1
            parent_frames[key].add(fkey)
    return {"unit": "candidate_context_slot", "denominator": len(rows),
            "observed_score_count": len(rows) - zeros.get("missing", 0),
            "missing_score_count": zeros.get("missing", 0), "distinct_context_frames": len(fkeys),
            "evaluation_categories": dict(categories), "zero_states": dict(zeros),
            "joint_candidate_states": [{"evaluation_category": k[0], "zero_state": k[1], "selected_native": k[2], "count": n} for k, n in sorted(joint.items())],
            "parent_full_pool_states": [{"state": json.loads(k), "candidate_count": n,
                                         "distinct_context_frames": len(parent_frames[k])} for k, n in sorted(parent.items())],
            "distinct_frames_not_additive_across_strata": True}


def grouped_candidates(candidates, states):
    groups = defaultdict(list)
    support = defaultdict(list)
    for row in candidates:
        for scope in scopes(row, candidate=True):
            for family in CANDIDATE_FAMILIES:
                for value in metadata(row, family):
                    groups[token({**scope, "family": family, "value": value})].append(row)
            # Continuous support is conditioned on compatible producer schema AND
            # extraction/threshold; success and rejection receive parallel cells.
            key = {**scope, "native_or_weak": row.get("native_or_weak"),
                   "evaluation_category": row["evaluation_category"],
                   "target_group": row["target_group"], "zero_state": row["zero_state"],
                   "extraction": row.get("extraction"), "threshold": row.get("threshold")}
            support[token(key)].append(row)
    tables = [{**json.loads(k), **candidate_counts(v, states)} for k, v in sorted(groups.items())]
    numeric = []
    for key, rows in sorted(support.items()):
        numeric.append({**json.loads(key), "unit": "candidate_context_slot", "denominator": len(rows),
                        "distinct_context_frames": len({r["frame_key"] for r in rows if r.get("frame_key")}),
                        "statistics": {name: numeric_summary(r.get(name) for r in rows)
                                       for name in ("logit", "native_score", "component_pixels", "padding_pixels", "distance_px", "recorded_uncertainty_radius_px")}})
    return tables, numeric


def paired_rows(frames, candidates, states):
    frame_index = index_unique(frames, "frame_key", "paired parent frame")
    fitted = index_unique([r for r in candidates if r["context"] == "nba_in_sample"], "candidate_id", "fitted candidate")
    held = index_unique([r for r in candidates if r["context"] == "nba_out_of_fold"], "candidate_id", "held candidate")
    if fitted.keys() != held.keys():
        raise ValueError("Fitted/held candidate populations differ")
    candidates_out = []
    for cid in sorted(fitted):
        a, b = fitted[cid], held[cid]
        for name in ("frame_id", "game_id", "block_id", "source_frame_index", "native_or_weak", "evaluation_category", "target_group", "selected_native"):
            if a.get(name) != b.get(name):
                raise ValueError(f"Paired candidate identity differs: {cid}: {name}")
        if a["logit"] is None or b["logit"] is None:
            raise ValueError("NBA pair has missing observed score")
        fa, fb = frame_index[a["frame_key"]], frame_index[b["frame_key"]]
        ma, mb = fa.get("rank_margin"), fb.get("rank_margin")
        candidates_out.append({"candidate_id": cid, "fitted_row_key": a["row_key"], "held_row_key": b["row_key"],
                               "game_id": a["game_id"], "block_id": a["block_id"], "source_frame_index": a["source_frame_index"],
                               "frame_id": a.get("frame_id"), "native_or_weak": a.get("native_or_weak"),
                               "evaluation_category": a["evaluation_category"], "target_group": a["target_group"],
                               "selected_native": a.get("selected_native"), "fitted_logit": a["logit"], "held_logit": b["logit"],
                               "held_minus_fitted": b["logit"] - a["logit"],
                               "sign_transition": a["zero_state"] + "->" + b["zero_state"],
                               "parent_rank_transition": fa["ranking_normalized"] + "->" + fb["ranking_normalized"],
                               "parent_fitted_rank_margin": ma, "parent_held_rank_margin": mb,
                               "parent_rank_margin_difference": mb - ma if ma is not None and mb is not None else None,
                               "parent_fitted_margin_null_reason": fa.get("rank_margin_null_reason"),
                               "parent_held_margin_null_reason": fb.get("rank_margin_null_reason"),
                               "native_score": a.get("native_score"), "component_pixels": a.get("component_pixels"),
                               "extraction": a.get("extraction"), "threshold": a.get("threshold"),
                               "visibility": a.get("visibility"), "difficulty_tags": a.get("difficulty_tags"),
                               "recorded_uncertainty_radius_px": a.get("recorded_uncertainty_radius_px"),
                               "padding_state": a.get("padding_state")})
    fit_f = index_unique([r for r in frames if r["context"] == "nba_in_sample"], "frame_id", "fitted frame")
    held_f = index_unique([r for r in frames if r["context"] == "nba_out_of_fold"], "frame_id", "held frame")
    if fit_f.keys() != held_f.keys():
        raise ValueError("Fitted/held frame populations differ")
    frames_out = []
    for fid in sorted(fit_f):
        a, b = fit_f[fid], held_f[fid]
        for name in ("game_id", "block_id", "source_frame_index", "candidate_count", "matching_candidate_count", "annotation"):
            if a.get(name) != b.get(name):
                raise ValueError(f"Paired frame identity differs: {fid}: {name}")
        ma, mb = a.get("rank_margin"), b.get("rank_margin")
        frames_out.append({"frame_id": fid, "fitted_frame_key": a["frame_key"], "held_frame_key": b["frame_key"],
                           "game_id": a["game_id"], "block_id": a["block_id"], "source_frame_index": a["source_frame_index"],
                           "rank_transition": a["ranking_normalized"] + "->" + b["ranking_normalized"],
                           "fitted_state": states[a["frame_key"]], "held_state": states[b["frame_key"]],
                           "fitted_rank_margin": ma, "held_rank_margin": mb,
                           "rank_margin_difference": mb - ma if ma is not None and mb is not None else None,
                           "fitted_margin_null_reason": a.get("rank_margin_null_reason"),
                           "held_margin_null_reason": b.get("rank_margin_null_reason"),
                           "annotation": a.get("annotation"), "selection_category": a.get("selection_category")})
    groups = defaultdict(list)
    for row in candidates_out:
        for level in ("all", "game", "block"):
            key = {"scope": level, "game_id": row["game_id"] if level != "all" else None,
                   "block_id": row["block_id"] if level == "block" else None,
                   "native_or_weak": row["native_or_weak"], "evaluation_category": row["evaluation_category"],
                   "target_group": row["target_group"], "sign_transition": row["sign_transition"],
                   "extraction": row["extraction"], "threshold": row["threshold"]}
            groups[token(key)].append(row)
    candidate_tables = [{**json.loads(k), "unit": "paired_NBA_candidate", "denominator": len(rows),
                         "distinct_frames": len({r["frame_id"] for r in rows}),
                         "parent_full_pool_margin_weighting": "one_parent_margin_per_candidate; not_reranked_within_origin_or_target",
                         "parent_rank_transitions": dict(Counter(r["parent_rank_transition"] for r in rows)),
                         "parent_fitted_margin_null_reasons": dict(Counter(r["parent_fitted_margin_null_reason"] for r in rows if r["parent_fitted_rank_margin"] is None)),
                         "parent_held_margin_null_reasons": dict(Counter(r["parent_held_margin_null_reason"] for r in rows if r["parent_held_rank_margin"] is None)),
                         "statistics": {n: numeric_summary(r.get(n) for r in rows) for n in
                                        ("held_minus_fitted", "fitted_logit", "held_logit", "native_score", "component_pixels",
                                         "parent_fitted_rank_margin", "parent_held_rank_margin", "parent_rank_margin_difference")}}
                        for k, rows in sorted(groups.items())]
    frame_groups = defaultdict(list)
    for row in frames_out:
        for level in ("all", "game", "block"):
            key = {"scope": level, "game_id": row["game_id"] if level != "all" else None,
                   "block_id": row["block_id"] if level == "block" else None,
                   "rank_transition": row["rank_transition"]}
            frame_groups[token(key)].append(row)
    frame_tables = [{**json.loads(k), "unit": "paired_NBA_frame", "denominator": len(rows),
                     "fitted_margin": numeric_summary(r["fitted_rank_margin"] for r in rows),
                     "held_margin": numeric_summary(r["held_rank_margin"] for r in rows),
                     "margin_difference": numeric_summary(r["rank_margin_difference"] for r in rows),
                     "fitted_margin_null_reasons": dict(Counter(r["fitted_margin_null_reason"] for r in rows if r["fitted_rank_margin"] is None)),
                     "held_margin_null_reasons": dict(Counter(r["held_margin_null_reason"] for r in rows if r["held_rank_margin"] is None))}
                    for k, rows in sorted(frame_groups.items())]
    return candidates_out, frames_out, {"candidates": candidate_tables, "frames": frame_tables}


def support_correspondence(candidates, weights, manifests, states):
    metadata_rows = index_unique([r for r in candidates if r["context"] in ("nba_in_sample", "nfhs_secondary") and r["cohort"] == "package"], "candidate_id", "support source")
    train_groups = defaultdict(list)
    keys = {}
    for fit, manifest in manifests.items():
        included = set(manifest["fit_game_ids"])
        for cid, row in metadata_rows.items():
            if row["game_id"] not in included:
                continue
            member = weights[fit].get(cid)
            if member is not None and row["target"] is None:
                raise ValueError("Unknown target included in fitting weights")
            for family in SUPPORT_FAMILIES:
                for value in metadata(row, family):
                    key = {"fit": fit, "target_group": row["target_group"], "native_or_weak": row.get("native_or_weak"),
                           "family": family, "value": value}
                    encoded = token(key)
                    keys[encoded] = key
                    train_groups[encoded].append((row, member))
    diagnostics = defaultdict(list)
    for row in candidates:
        if row["cohort"] == "historical":
            continue
        for family in SUPPORT_FAMILIES:
            for value in metadata(row, family):
                key = {"fit": row["fit"], "target_group": row["target_group"], "native_or_weak": row.get("native_or_weak"),
                       "family": family, "value": value}
                encoded = token(key)
                keys[encoded] = key
                for level in ("context", "game", "block"):
                    context = {"context": row["context"], "cohort": row["cohort"], "scope": level,
                               "game_id": row.get("game_id") if level != "context" else None,
                               "block_id": row.get("block_id") if level == "block" else None,
                               "support_key": encoded}
                    diagnostics[token(context)].append(row)
    tables = []
    for encoded, key in sorted(keys.items()):
        rows = train_groups.get(encoded, [])
        fitted = [(r, w) for r, w in rows if w is not None]
        excluded = [r for r, w in rows if w is None]
        known_target = key["target_group"] in ("positive", "eligible_distant_miss", "certain_hidden")
        usable_schema = key["native_or_weak"] in ("native", "weak") and key["target_group"] not in ("missing_selection", "historical")
        value, family = key["value"], key["family"]
        metadata_available = (all(v is not None for v in value) if family == "extraction_threshold"
                              else value is not None and value != "inapplicable_missing")
        status = ("excluded_target_or_inapplicable_metadata" if not known_target or not usable_schema
                  else "metadata_unavailable" if not metadata_available
                  else "available" if fitted else "zero_fitting_support")
        tables.append({"support_key": encoded, **key, "unit": "unique_fitting_candidate",
                       "status": status, "included_fit_games": manifests[key["fit"]]["fit_game_ids"],
                       "source_candidates_in_included_games": len(rows), "fitting_candidates": len(fitted),
                       "excluded_candidates": len(excluded),
                       "unique_fitting_frames": len({r["frame_id"] for r, _ in fitted}),
                       "unique_fitting_blocks": len({r["block_id"] for r, _ in fitted}),
                       "unique_fitting_games": len({r["game_id"] for r, _ in fitted}),
                       "fitting_game_ids": sorted({r["game_id"] for r, _ in fitted}),
                       "fitting_block_ids": sorted({r["block_id"] for r, _ in fitted}),
                       "objective_mass": math.fsum(w["objective_weight"] for _, w in fitted) if known_target and usable_schema and metadata_available else None,
                       "training_multiplier": numeric_summary(w["training_multiplier"] for _, w in fitted),
                       "families_and_overlapping_tags_not_additive": True})
    refs = {t["support_key"]: t for t in tables}
    associations = []
    for encoded, rows in sorted(diagnostics.items()):
        group = json.loads(encoded)
        support = refs[group["support_key"]]
        associations.append({**group, **candidate_counts(rows, states),
                             "support_status": support["status"], "fitting_candidates": support["fitting_candidates"],
                             "unique_fitting_frames": support["unique_fitting_frames"],
                             "objective_mass": support["objective_mass"]})
    return tables, associations


def missingness(frames, candidates):
    fields = ("logit", "native_score", "component_pixels", "extraction", "threshold", "padding_pixels",
              "in_bounds", "recorded_uncertainty_radius_px", "visibility", "game_ball_identity_certainty",
              "geometry_source", "selection_category", "distance_px")
    groups = defaultdict(list)
    for row in candidates:
        groups[(row["context"], row["cohort"])].append(row)
    return {"candidate_tables": [{"context": k[0], "cohort": k[1], "denominator": len(rows),
                                  "unit": "candidate_context_slot", "null_fields": {f: sum(r.get(f) is None for r in rows) for f in fields},
                                  "joint_null_patterns": [{"fields": list(p), "count": n} for p, n in sorted(Counter(tuple(f for f in fields if r.get(f) is None) for r in rows).items())],
                                  "zero_states": dict(Counter(r["zero_state"] for r in rows)),
                                  "target_groups": dict(Counter(r["target_group"] for r in rows))}
                                 for k, rows in sorted(groups.items())],
            "frame_margin_null_reasons": dict(Counter(r.get("rank_margin_null_reason") for r in frames if r.get("rank_margin") is None)),
            "null_is_not_zero": True,
            "historical_support": "inapplicable; semantic accepted labels are separate from geometric fitting targets",
            "missing_stress": "missing image and crop; reference comparison zero is not a logit"}


def case_views(frames, candidates, contrasts, controls):
    hou = [r for r in frames if r["context"] == "HOU_development"]
    frame_index = {r["frame_key"]: r for r in hou}
    source_index = {(r["block_id"], r["source_frame_index"]): r["frame_key"] for r in hou}
    named = {
        "e01_ten_recoveries": lambda r: r["block_id"].endswith("_e01") and 194 <= r["source_frame_index"] <= 203,
        "e05_six_below_001": lambda r: r["block_id"].endswith("_e05") and 14 <= r["source_frame_index"] <= 19,
        "e05_harmful_8_9": lambda r: r["block_id"].endswith("_e05") and r["source_frame_index"] in (8, 9),
        "e05_useful_206": lambda r: r["block_id"].endswith("_e05") and r["source_frame_index"] == 206,
        "all_HOU_native_correct": lambda r: bool(r["cross_tab"].get("native_correct")),
        "all_HOU_native_wrong_eligible": lambda r: r["cross_tab"]["eligible"] and r.get("native_outcome") in ("wrong", "localization_error"),
        "all_HOU_native_missing_eligible": lambda r: r["cross_tab"]["eligible"] and r.get("native_outcome") == "missing",
        "all_HOU_noneligible": lambda r: not r["cross_tab"]["eligible"],
    }
    views = {}

    def view(selected):
        return {"frame_count": len(selected), "frame_keys": sorted(selected),
                "candidate_row_keys": [r["row_key"] for r in candidates if r.get("frame_key") in selected],
                "contrast_row_ids": [r["row_id"] for r in contrasts if r.get("frame_key") in selected]}

    for name, pred in named.items():
        views[name] = view({r["frame_key"] for r in hou if pred(r)})
    tags = defaultdict(list)
    tag_frames = defaultdict(set)
    for row in contrasts:
        for tag in sorted(set(row.get("tags") or [])):
            tags[tag].append(row["row_id"])
            tag_frames[tag].add(row["frame_key"])
    prior = controls.get("paired_and_adverse_case_interpretation", {})
    regression_groups = defaultdict(set)
    for row in prior.get("regression_frame_details", []):
        regression_groups[row["feature"]].add(source_index[(row["block_id"], row["frame"])])
    for feature, selected in regression_groups.items():
        views[feature + "_complete_pair_regressions"] = view(selected)
    for name, rows in prior.get("hidden_original_choices", {}).items():
        views["hidden_original_choices_" + name] = view({source_index[(r["block_id"], r["frame"])] for r in rows})
    # Baseline completeness is an existing observation, not a new feature rank.
    incomplete_peak = {r["frame_key"] for r in candidates if r["cohort"] == "HOU_main"
                       and frame_index[r["frame_key"]]["cross_tab"]["eligible"]
                       and "baseline_features" in r.get("source", {}).get("target", {})
                       and r["source"]["target"]["baseline_features"].get("peak") is None}
    views["incomplete_original_peak_frames"] = view(incomplete_peak)
    return {"named_groups": views, "all_existing_contrast_tags": {k: v for k, v in sorted(tags.items())},
            "existing_contrast_tag_views": {k: view(v) for k, v in sorted(tag_frames.items())},
            "overlapping_tags_not_additive": True,
            "saved_controls_reused": sorted(controls)}


def contrast_tables(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["contrast"], "all")].append(row)
        groups[(row["contrast"], row["block_id"])].append(row)
    return [{"contrast": k[0], "block_id": k[1], "unit": "existing_directed_contrast", "denominator": len(rs),
             "choice_states": dict(Counter(r["choice_state"] for r in rs)),
             "outcome_transitions": dict(Counter(r["outcome_transition"] for r in rs)),
             "correct_side_states": dict(Counter(r["correct_side_status"] for r in rs)),
             "coordinate_agreements": sum(bool(r.get("coordinate_agreement")) for r in rs)}
            for k, rs in sorted(groups.items())]


def analyze(study):
    """Analyze once after external freeze; never reads or writes files itself."""
    frames, candidates = study["frames"], study["candidates"]
    index_unique(frames, "frame_key", "context frame")
    index_unique(candidates, "row_key", "candidate context")
    frame_index = {r["frame_key"]: r for r in frames}
    for row in candidates:
        if row.get("frame_key") is not None and row["frame_key"] not in frame_index:
            raise ValueError("Candidate frame lost")
        if sign(row["logit"]) != row["zero_state"]:
            raise ValueError("Candidate sign transport differs")
    states = frame_states(frames, candidates)
    ft = grouped_frames(frames, states)
    ct, numeric = grouped_candidates(candidates, states)
    pc, pf, pt = paired_rows(frames, candidates, states)
    st, sa = support_correspondence(candidates, study["weights"], study["manifests"], states)
    contrasts = study["contrasts"]
    for row in contrasts:
        if row.get("frame_key") not in frame_index:
            raise ValueError("Contrast frame lost")
    # These annotations add exact references to joined metadata without changing
    # the original comparison, score or label payload.
    contrast_views = [{**r, "frame_metadata": {k: frame_index[r["frame_key"]].get(k) for k in
                                               ("visibility", "difficulty_tags", "recorded_uncertainty_radius_px", "selection_category")},
                       "full_pool_state": states[r["frame_key"]]} for r in contrasts]
    summary = {"context_frames": len(frames), "candidate_context_slots": len(candidates),
               "observed_scores": sum(r["logit"] is not None for r in candidates),
               "missing_scores": sum(r["logit"] is None for r in candidates),
               "paired_NBA_candidates": len(pc), "paired_NBA_frames": len(pf),
               "paired_candidate_sign_transitions": dict(Counter(r["sign_transition"] for r in pc)),
               "paired_frame_rank_transitions": dict(Counter(r["rank_transition"] for r in pf)),
               "held_minus_fitted_logit": numeric_summary(r["held_minus_fitted"] for r in pc),
               "held_minus_fitted_margin": numeric_summary(r["rank_margin_difference"] for r in pf),
               "contrasts": len(contrasts), "historical_rows": len(study["historical"]),
               "contexts": {ctx: frame_counts([r for r in frames if r["context"] == ctx], states)
                            for ctx in sorted({r["context"] for r in frames})},
               "candidate_cohorts": dict(Counter(r["cohort"] for r in candidates)),
               "support_tables": len(st), "support_associations": len(sa),
               "new_choices": 0, "new_labels": 0, "model_calls": 0, "GPU_queries": 0,
               "selected_threshold": None, "causal_claim": False,
               "limits": ["Existing exposed correlated data, not independent validation.",
                          "Fitted and held model composition and training amount are confounded.",
                          "Marginal metadata support is not visual similarity or a causal explanation.",
                          "Objective weights are not population probabilities; zero is a diagnostic reference.",
                          "Full-pool ranking is not a new emitted trajectory or semantic identity acceptance."]}
    return {"summary": summary, "frame_tables": ft, "candidate_tables": ct,
            "candidate_numeric_support_tables": numeric,
            "paired_candidates": pc, "paired_frames": pf, "paired_tables": pt,
            "support_tables": st, "support_associations": sa,
            "missingness": missingness(frames, candidates), "contrast_views": contrast_views,
            "contrast_tables": contrast_tables(contrasts), "historical_appendix": study["historical"],
            "case_views": case_views(frames, candidates, contrasts, study.get("controls", {})),
            "controls": study.get("controls", {})}
