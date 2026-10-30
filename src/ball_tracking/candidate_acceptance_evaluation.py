"""Fixed-policy acceptance diagnostics; never rerank after rejection."""
from collections import Counter, defaultdict
import json
import math

ARMS = ("Q", "S", "J", "M")
MEASURES = ("accepted", "correct_kept", "wrong_eligible_kept", "hidden_candidates",
            "hidden_emission_frames", "match_survival_frames", "unknown_kept", "historical_kept")


def token(value):
    def canonical(x):
        if isinstance(x, float) and math.isfinite(x) and x.is_integer():
            return int(x)
        if isinstance(x, dict):
            return {k: canonical(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [canonical(v) for v in x]
        return x
    return json.dumps(canonical(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def score(row, arm):
    value = row["scores"].get(arm)
    require(value is None or (isinstance(value, (int, float)) and not isinstance(value, bool)
                             and math.isfinite(value)), "Nonfinite/malformed acceptance score")
    return value


def policy_rows(frames, candidates):
    pools = defaultdict(list)
    for row in candidates:
        if row["cohort"] in ("package", "HOU_main"):
            pools[row["frame_key"]].append(row)
    result = []
    for frame in frames:
        pool = pools[frame["frame_key"]]
        natives = [r for r in pool if r["selected_native"]]
        require(len(natives) <= 1, "Multiple original native selections")
        top = sorted(pool, key=lambda r: (-r["scores"]["Q"], r["candidate_id"] or r["query_id"]))
        tied = [r["row_key"] for r in top if r["scores"]["Q"] == top[0]["scores"]["Q"]] if top else []
        for policy, point in (("native", natives[0] if natives else None), ("quality_top", top[0] if top else None)):
            category = point["evaluation_category"] if point else "missing_choice"
            result.append({
                "row_key": policy + "|" + frame["frame_key"], "policy": policy,
                **{k: frame.get(k) for k in ("frame_key", "context", "fit", "game_id", "block_id", "source_frame_index",
                   "eligible", "reference_category", "visibility", "difficulty_tags", "recorded_uncertainty_radius_px",
                   "selection_category", "ranking_normalized", "native_outcome")},
                "cohort": "fixed_policy", "chosen_row_key": point["row_key"] if point else None,
                "evaluation_category": category, "target_group": point["target_group"] if point else "missing_choice",
                "native_or_weak": point["native_or_weak"] if point else None,
                "scores": dict(point["scores"]) if point else {arm: None for arm in ARMS},
                "quality_top_tied_row_keys": tied, "point_chosen_before_acceptance": True,
                "fallback_allowed": False, "original_pool_count": len(pool),
                "M_no_rival_fallback": point.get("M_no_rival_fallback") if point else None,
            })
    require(len(result) == 2 * len(frames), "Policy frame inventory loss")
    return result


def aggregate(rows, arm, threshold=0.0):
    counts = Counter({name: 0 for name in MEASURES})
    hidden_frames, match_frames = set(), set()
    categories, zeros = Counter(), Counter()
    for row in rows:
        category = row["evaluation_category"]
        categories[category] += 1
        value = score(row, arm)
        zeros["missing" if value is None else "positive" if value > 0 else "negative" if value < 0 else "zero"] += 1
        if value is None or value <= threshold:
            continue
        counts["accepted"] += 1
        if category == "eligible_match":
            counts["correct_kept"] += 1
            match_frames.add(row["frame_key"])
        elif category == "eligible_miss":
            counts["wrong_eligible_kept"] += 1
        elif category == "certain_hidden":
            counts["hidden_candidates"] += 1
            hidden_frames.add(row["frame_key"])
        elif category == "historical":
            counts["historical_kept"] += 1
        else:
            counts["unknown_kept"] += 1
    counts["hidden_emission_frames"] = len(hidden_frames)
    counts["match_survival_frames"] = len(match_frames)
    return {"denominator": len(rows), "distinct_context_frames": len({r["frame_key"] for r in rows if r.get("frame_key")}),
            "original_categories": dict(categories), "score_states": dict(zeros),
            "correct_rejected": categories["eligible_match"] - counts["correct_kept"],
            "counts": dict(counts), "threshold": threshold, "acceptance_rule": "strictly_greater",
            "unknown_not_counted_as_errors": True}


def scopes(row, policy=False):
    base = {"context": row["context"], "cohort": row.get("cohort"),
            "policy": row.get("policy") if policy else None}
    for level in ("context", "game", "block"):
        yield {**base, "scope": level, "game_id": row.get("game_id") if level != "context" else None,
               "block_id": row.get("block_id") if level == "block" else None}


def family_values(row, family):
    if family == "all":
        return ["all"]
    if family == "difficulty_tag":
        return sorted(set(row.get("difficulty_tags") or [])) or ["no_tag"]
    if family == "uncertainty_radius":
        return [row.get("recorded_uncertainty_radius_px")]
    return [row.get(family)]


def grouped(rows, policy=False, detailed=True):
    families = ("all", "native_or_weak", "evaluation_category", "target_group", "visibility",
                "difficulty_tag", "uncertainty_radius") if detailed else ("all",)
    groups = defaultdict(list)
    for row in rows:
        for scope in scopes(row, policy):
            for family in families:
                for value in family_values(row, family):
                    key = {**scope, "family": family, "value": value}
                    groups[token(key)].append(row)
    return groups


def zero_tables(rows, policy=False):
    for key, members in sorted(grouped(rows, policy).items()):
        for arm in ARMS:
            yield {**json.loads(key), "arm": arm, "unit": "fixed_policy_context_frame" if policy else "candidate_context_slot",
                   **aggregate(members, arm), "families_tags_and_distinct_frames_not_additive": True}


def curve(rows, arm):
    """Exact strict-threshold steps; equal scores always move together."""
    score_groups = defaultdict(list)
    for row in rows:
        value = score(row, arm)
        if value is not None:
            score_groups[value].append(row)
    counts = Counter({name: 0 for name in MEASURES})
    hidden, matches = set(), set()
    points = [{"kind": "reject_all", "threshold": None, "counts": [0] * len(MEASURES)}]
    for threshold, tied in sorted(score_groups.items(), reverse=True):
        points.append({"kind": "threshold", "threshold": threshold, "tied_candidates": len(tied),
                       "counts": [counts[name] for name in MEASURES]})
        for row in tied:
            counts["accepted"] += 1
            category = row["evaluation_category"]
            if category == "eligible_match":
                counts["correct_kept"] += 1
                matches.add(row["frame_key"])
            elif category == "eligible_miss":
                counts["wrong_eligible_kept"] += 1
            elif category == "certain_hidden":
                counts["hidden_candidates"] += 1
                hidden.add(row["frame_key"])
            elif category == "historical":
                counts["historical_kept"] += 1
            else:
                counts["unknown_kept"] += 1
        counts["hidden_emission_frames"] = len(hidden)
        counts["match_survival_frames"] = len(matches)
    points.append({"kind": "accept_all_observed", "threshold": None, "counts": [counts[name] for name in MEASURES]})
    return {"denominator": len(rows), "observed_scores": sum(len(r) for r in score_groups.values()),
            "missing_scores": sum(score(r, arm) is None for r in rows),
            "measure_columns": list(MEASURES), "points": points,
            "threshold_chosen": None, "descriptive_only": True, "strict_acceptance": ">"}


def curves(rows, policy=False):
    for key, members in sorted(grouped(rows, policy, detailed=False).items()):
        for arm in ARMS:
            yield {**json.loads(key), "arm": arm, "unit": "fixed_policy_context_frame" if policy else "candidate_context_slot",
                   **curve(members, arm)}
    # Explicit M fallback populations keep the composite control interpretable.
    for fallback in (False, True, None):
        members = [r for r in rows if r.get("M_no_rival_fallback") is fallback]
        if members:
            yield {"scope": "M_fallback_inventory", "fallback": fallback, "arm": "M",
                   "unit": "fixed_policy_context_frame" if policy else "candidate_context_slot",
                   **curve(members, "M")}


def paired_policy_rows(policies):
    for row in policies:
        accepted = {arm: score(row, arm) is not None and score(row, arm) > 0 for arm in ARMS}
        yield {**row, "accepted_at_zero": accepted,
               "J_vs_Q": "agreement" if accepted["J"] == accepted["Q"] else "new_accept" if accepted["J"] else "new_reject",
               "J_vs_S": "agreement" if accepted["J"] == accepted["S"] else "new_accept" if accepted["J"] else "new_reject"}


def old_case_views(saved, candidates):
    queries = {r["query_id"]: r for r in candidates if r.get("query_id")}
    choices = []
    for old in saved["source_choices"]:
        point = queries.get(old["query_id"]) if old.get("query_id") else None
        require((point is not None) == (old["state"] == "observed"), "Old choice query lost")
        if point:
            require(point["scores"]["Q"] == old["logit"], "Old choice Q changed")
        choices.append({**old, "scores": dict(point["scores"]) if point else {a: None for a in ARMS},
                        "accepted_at_zero": {a: score(point, a) is not None and score(point, a) > 0 for a in ARMS}
                        if point else {a: False for a in ARMS},
                        "new_choice_created": False})
    contrasts = []
    for old in saved["contrasts"]:
        side_data = {}
        for side in ("source", "target"):
            choice = old["source_comparison"][side + "_choice"]
            point = queries.get(choice.get("query_id"))
            scores = dict(point["scores"]) if point else {a: None for a in ARMS}
            require(scores["Q"] == old[side + "_quality"]["image_quality_logit"], "Contrast Q changed")
            side_data[side] = {"query_id": choice.get("query_id"), "state": choice["state"],
                               "original_outcome": choice.get("outcome"), "scores": scores,
                               "accepted_at_zero": {a: scores[a] is not None and scores[a] > 0 for a in ARMS}}
        contrasts.append({**{k: old.get(k) for k in ("row_id", "contrast", "role", "block_id", "frame", "frame_key",
                          "tags", "choice_state", "coordinate_agreement", "candidate_identity_agreement",
                          "reference_category", "outcome_transition", "correct_side_status")},
                          **side_data, "new_choice_created": False,
                          "delta_target_minus_source": {a: side_data["target"]["scores"][a] - side_data["source"]["scores"][a]
                               if side_data["target"]["scores"][a] is not None and side_data["source"]["scores"][a] is not None else None
                               for a in ARMS}})
    return choices, contrasts


def decide(policies, candidates, case_views):
    checks, strict = [], []
    games = sorted({r["game_id"] for r in policies if r["context"] == "nba_out_of_fold"})
    for game in games:
        for policy in ("native", "quality_top"):
            members = [r for r in policies if r["context"] == "nba_out_of_fold" and r["game_id"] == game and r["policy"] == policy]
            counts = {a: aggregate(members, a)["counts"] for a in ("Q", "S", "J")}
            for comparator in ("Q", "S"):
                for metric, direction in (("correct_kept", "higher"), ("wrong_eligible_kept", "lower"), ("hidden_emission_frames", "lower")):
                    a, b = counts["J"][metric], counts[comparator][metric]
                    passed = a >= b if direction == "higher" else a <= b
                    improvement = a > b if direction == "higher" else a < b
                    row = {"game_id": game, "policy": policy, "comparator": comparator, "metric": metric,
                           "J": a, "baseline": b, "passed": passed, "strict_improvement": improvement}
                    checks.append(row)
                    if improvement:
                        strict.append(row)
    protected_frames = {key for group in case_views["named_groups"].values() for key in group.get("frame_keys", [])}
    policy_losses = [r["row_key"] for r in policies if r["context"] == "HOU_development"
                     and r["frame_key"] in protected_frames and r["evaluation_category"] == "eligible_match"
                     and score(r, "Q") is not None and score(r, "Q") > 0
                     and (score(r, "J") is None or score(r, "J") <= 0)]
    probes = [r for r in candidates if r["cohort"] == "HOU_stress" and r["frame_key"] in protected_frames
              and r["evaluation_category"] == "eligible_match" and score(r, "Q") is not None and score(r, "Q") > 0]
    probe_losses = [r["row_key"] for r in probes if score(r, "J") is None or score(r, "J") <= 0]
    hidden_checks = []
    for policy in ("native", "quality_top"):
        members = [r for r in policies if r["context"] == "HOU_development" and r["policy"] == policy]
        counts = {a: aggregate(members, a)["counts"]["hidden_emission_frames"] for a in ("Q", "S", "J")}
        for arm in ("Q", "S"):
            hidden_checks.append({"policy": policy, "comparator": arm, "J": counts["J"], "baseline": counts[arm],
                                  "passed": counts["J"] <= counts[arm]})
    passed = (all(r["passed"] for r in checks) and bool(strict) and not policy_losses and not probe_losses
              and all(r["passed"] for r in hidden_checks))
    return {"fixed_reference_component_criterion_passed": passed, "NBA_checks": checks,
            "strict_improvements": strict, "HOU_protected_policy_losses": policy_losses,
            "HOU_protected_stress_count": len(probes), "HOU_protected_stress_losses": probe_losses,
            "HOU_hidden_checks": hidden_checks, "curve_interpretation": "Requires descriptive per-source review; no automated curve pass",
            "selected_threshold": None, "model_adopted": False, "tracker_complete": False,
            "limits": ["Fixed ranking ceiling unchanged", "Exposed HOU veto is not independent validation",
                       "Base training size changes across nesting", "No semantic crop-presence target"]}


def missingness(candidates, feature_rows):
    feature_index = {r["row_key"]: r for r in feature_rows}
    result = []
    groups = defaultdict(list)
    for row in candidates:
        groups[(row["context"], row["cohort"])].append(row)
    for key, members in sorted(groups.items()):
        result.append({"context": key[0], "cohort": key[1], "denominator": len(members),
                       "scores_missing": {arm: sum(score(r, arm) is None for r in members) for arm in ARMS},
                       "source_fields_missing": {name: sum(r.get(name) is None for r in members)
                           for name in ("native_score", "component_pixels", "padding_pixels", "center_xy_px")},
                       "feature_records": sum(r["row_key"] in feature_index for r in members),
                       "out_of_fitting_schema": sum(r.get("out_of_fitting_schema", False) for r in members)})
    return result
