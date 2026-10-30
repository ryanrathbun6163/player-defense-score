"""Read-only transport of accepted features for the focused origin ablation.

The caller verifies frozen input bindings before loading. This adapter does no
feature extraction, scaler fitting, model fitting or prediction. Saved feature
rows, labels, weights and pre-acceptance point identities remain unchanged.
"""
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import struct

SOURCE = "data/outputs/ball_tracking/candidate_acceptance_gate_v0_1/attempt_001/analysis"
GAMES = {"CHI": "0022400868", "DEN": "0022400866", "SAC": "0022500829"}
OLD_BASES = {"CHI": "leave_chi_out", "DEN": "leave_den_out", "SAC": "leave_sac_out"}
GATES = ("outer_CHI", "outer_DEN", "outer_SAC", "final_all_NBA")
FEATURE_NAMES = (
    "quality_logit", "log1p_response_mass", "log1p_component_pixels", "padding_fraction",
    "native_indicator", "origin_unavailable", "response_missing", "component_missing", "padding_missing",
    "quality_minus_far_max", "quality_minus_near_max", "log1p_near_count", "log1p_far_count",
    "far_max_missing", "near_max_missing", "pool_unavailable",
)
BINARY = {"native_indicator", "origin_unavailable", "response_missing", "component_missing", "padding_missing",
          "far_max_missing", "near_max_missing", "pool_unavailable"}
FILES = {
    "cross_features": "cross_training_features.jsonl", "final_features": "final_training_features.jsonl",
    "evaluation_features": "evaluation_features.jsonl", "candidates": "candidate_scores.jsonl",
    "frames": "frame_registry.jsonl", "fixed_policies": "fixed_policy_rows.jsonl", "fit_membership": "fit_membership.jsonl",
}
INPUT_PATHS = tuple(SOURCE + "/" + filename for filename in FILES.values()) + tuple(
    SOURCE + "/fits/" + gate + "_J.json" for gate in GATES)
EXPECTED_COUNTS = {"cross_features": 37626, "final_features": 18813, "evaluation_features": 31430,
                   "candidates": 31430, "frames": 4289, "fixed_policies": 8578, "fit_membership": 56439}
KNOWN_COUNTS = {"outer_CHI": 11954, "outer_DEN": 11912, "outer_SAC": 11182, "final_all_NBA": 17524}
STRATUM_MASSES = {"positive": .5, "eligible_distant_miss": .25, "certain_hidden": .25}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(rows, key, label):
    result = {}
    for row in rows:
        value = row[key]
        require(value not in result, "Duplicate " + label + ": " + str(value))
        result[value] = row
    return result


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_feature(row):
    require(tuple(row["feature_names"]) == FEATURE_NAMES, "Saved feature names/order differ")
    require(isinstance(row["row_key"], str) and row["row_key"], "Feature identity missing")
    if row["status"] == "missing_image":
        require(row["Q"] is None and row["M"] is None and row["values"] is None
                and row["raw_features"] is None, "Missing image acquired fabricated features")
        return
    require(row["status"] == "observed" and finite(row["Q"]) and finite(row["M"]), "Unknown/invalid observed feature state")
    raw = row["raw_features"]
    require(set(raw) == set(FEATURE_NAMES) and row["values"] == [raw[name] for name in FEATURE_NAMES],
            "Saved feature array/dictionary mismatch")
    require(raw["quality_logit"] == row["Q"], "Feature raw Q mismatch")
    for name, value in raw.items():
        require((value is None and name not in BINARY) or finite(value), "Nonfinite/malformed saved feature")
        if name in BINARY:
            require(value in (0, 1), "Invalid saved binary feature")


def float64_binding(values, shape):
    digest = hashlib.sha256()
    count = 0
    for value in values:
        require(finite(value), "Nonfinite numeric transport")
        digest.update(struct.pack("<d", float(value)))
        count += 1
    require(count == math.prod(shape), "Numeric transport shape differs")
    return {"dtype": "little_endian_float64", "shape": list(shape), "sha256": digest.hexdigest()}


def saved_matrix_binding(features, scaler):
    """Check old array bytes using the saved scaler only; never fit a scaler."""
    require(tuple(scaler["feature_names"]) == FEATURE_NAMES, "Old J scaler feature order differs")
    means, scales = scaler["means"], scaler["scales"]
    require(len(means) == len(scales) == len(FEATURE_NAMES), "Old J scaler shape differs")
    require(all(finite(m) and finite(s) and s > 0 for m, s in zip(means, scales)), "Invalid saved J scaler")
    require(set(scaler["binary_features"]) == BINARY, "Saved J binary feature inventory differs")
    for i, name in enumerate(FEATURE_NAMES):
        if name in BINARY:
            require(means[i] == 0 and scales[i] == 1, "Binary features were standardized")

    def transformed_values():
        for row in features:
            require(row["status"] == "observed", "Missing image entered old training matrix")
            for value, mean, scale in zip(row["values"], means, scales):
                yield ((mean if value is None else float(value)) - mean) / scale

    return float64_binding(transformed_values(), [len(features), len(FEATURE_NAMES)])


def validate_fixed_policies(frames, candidates, policies):
    """Check saved pre-acceptance choices; return original policies unchanged."""
    frame_index = unique(frames, "frame_key", "frame")
    candidate_index = unique(candidates, "row_key", "candidate row")
    policy_index = unique(policies, "row_key", "policy row")
    expected = {policy + "|" + frame_key for frame_key in frame_index for policy in ("native", "quality_top")}
    require(set(policy_index) == expected, "Fixed policy frame inventory differs")
    pools = defaultdict(list)
    for row in candidates:
        if row["cohort"] in ("package", "HOU_main"):
            pools[row["frame_key"]].append(row)
    for frame_key, frame in frame_index.items():
        pool = pools[frame_key]
        natives = [r for r in pool if r["selected_native"]]
        require(len(natives) <= 1, "Multiple original native identities")
        ordered = sorted(pool, key=lambda r: (-r["scores"]["Q"], r["candidate_id"] or r["query_id"]))
        tied = [r["row_key"] for r in ordered if r["scores"]["Q"] == ordered[0]["scores"]["Q"]] if ordered else []
        for policy, point in (("native", natives[0] if natives else None), ("quality_top", ordered[0] if ordered else None)):
            row = policy_index[policy + "|" + frame_key]
            require(row["policy"] == policy and row["frame_key"] == frame_key
                    and row["chosen_row_key"] == (point["row_key"] if point else None), "Saved fixed point identity changed")
            require(row["point_chosen_before_acceptance"] is True and row["fallback_allowed"] is False,
                    "Fixed policy permits reselection/fallback")
            require(row["quality_top_tied_row_keys"] == tied and row["original_pool_count"] == len(pool),
                    "Saved quality tie/pool transport differs")
            for field in ("context", "fit", "game_id", "block_id", "source_frame_index", "eligible", "reference_category"):
                require(row.get(field) == frame.get(field), "Fixed policy/frame provenance differs: " + field)
            if point is None:
                require(row["evaluation_category"] == row["target_group"] == "missing_choice"
                        and row["native_or_weak"] is None and all(v is None for v in row["scores"].values()),
                        "Missing fixed choice acquired an emitted point")
            else:
                require(row["scores"] == point["scores"] and all(row[field] == point[field] for field in
                        ("evaluation_category", "target_group", "native_or_weak")), "Fixed choice metadata/scores differ")
    return policies


def expected_source(gate, candidate):
    name = next((name for name, game in GAMES.items() if game == candidate["game_id"]), None)
    require(name is not None and candidate["domain"] == "nba", "Non-NBA source in fitting registry")
    if gate == "final_all_NBA":
        return OLD_BASES[name]
    require(gate in GATES, "Unknown gate")
    held = gate.removeprefix("outer_")
    require(name != held, "Outer-held game entered fitting registry")
    return next(other for other in GAMES if other not in (name, held)) + "_only"


def fit_inputs(gate, loaded):
    """Return unchanged rows, targets, weights in exact old J training order."""
    require(gate in GATES, "Unknown gate")
    model = loaded["original_J_models"][gate]
    require(model["status"] == "fitted" and model["arm"] == "J" and model["fit_id"] == gate
            and tuple(model["feature_names"]) == FEATURE_NAMES, "Old J model identity/schema differs")
    membership = loaded["membership_by_gate"][gate]
    feature_index = loaded["feature_indices"]["final" if gate == "final_all_NBA" else "cross"]
    keys = model["training_row_keys"]
    require(len(keys) == len(set(keys)) == model["training_row_count"], "Old J training order is duplicated/incomplete")
    known = {key for key, member in membership.items() if member["included_in_fitting"]}
    require(set(keys) == known, "Old J known membership changed")
    features, targets, weights = [], [], []
    mass = defaultdict(list)
    candidate_ids = set()
    for key in keys:
        member, feature = membership[key], feature_index[key]
        candidate = loaded["nba_by_id"][member["candidate_id"]]
        require(member["candidate_id"] not in candidate_ids, "Candidate repeated within gate fit")
        candidate_ids.add(member["candidate_id"])
        require(member["base_fit"] == feature["fit"] == expected_source(gate, candidate), "Gate/base source nesting differs")
        require(member["game_id"] == candidate["game_id"] and member["target"] == candidate["target"]
                and member["target"] in (0, 1) and candidate["target_group"] in STRATUM_MASSES,
                "Target/game membership transport differs")
        require(member["target"] == int(candidate["target_group"] == "positive"), "Target/stratum mismatch")
        require(feature["row_key"] == key and feature["status"] == "observed", "Fitting feature identity/state differs")
        weight = member["objective_weight"]
        require(finite(weight) and weight > 0, "Missing/invalid known objective weight")
        features.append(feature)
        targets.append(member["target"])
        weights.append(weight)
        mass[candidate["target_group"]].append(weight)
    require(set(mass) == set(STRATUM_MASSES) and all(math.isclose(math.fsum(mass[group]), expected,
            rel_tol=1e-12, abs_tol=1e-12) for group, expected in STRATUM_MASSES.items()), "Original target-stratum objective masses changed")
    require(math.isclose(math.fsum(weights), 1.0, rel_tol=1e-12, abs_tol=1e-12), "Objective weights do not sum to one")
    arrays = model["training_arrays"]
    require(float64_binding(targets, [len(targets)]) == arrays["targets"], "Old J target array binding differs")
    require(float64_binding(weights, [len(weights)]) == arrays["weights"], "Old J weight array binding differs")
    require(saved_matrix_binding(features, model["scaler"]) == arrays["features"], "Old J saved-normalizer feature array binding differs")
    return features, targets, weights


def validate_loaded(loaded, *, exact_counts=True):
    """Validate registry transport; synthetic tests may use a smaller population."""
    if exact_counts:
        require({key: len(loaded[key]) for key in EXPECTED_COUNTS} == EXPECTED_COUNTS, "Accepted registry counts changed")
    indices = {name: unique(loaded[key], "row_key", key) for name, key in
               (("cross", "cross_features"), ("final", "final_features"), ("evaluation", "evaluation_features"))}
    loaded["feature_indices"] = indices
    for index in indices.values():
        for row in index.values():
            validate_feature(row)
    candidate_index = unique(loaded["candidates"], "row_key", "evaluation candidate")
    frame_index = unique(loaded["frames"], "frame_key", "evaluation frame")
    require(set(indices["evaluation"]) == set(candidate_index), "Evaluation feature/candidate identities differ")
    nba = [r for r in loaded["candidates"] if r["context"] == "nba_out_of_fold"]
    loaded["nba_by_id"] = unique(nba, "candidate_id", "NBA candidate")
    loaded["candidates_by_key"], loaded["frames_by_key"] = candidate_index, frame_index
    require(set(indices["final"]) == {r["row_key"] for r in nba}, "Final training registry differs from full NBA OOF inventory")
    for key, feature in indices["final"].items():
        require(feature == indices["evaluation"][key], "Final training/evaluation features changed")
    missing = 0
    for key, candidate in candidate_index.items():
        feature = indices["evaluation"][key]
        require(feature["fit"] == candidate["fit"] and feature["frame_key"] == candidate["frame_key"], "Evaluation base/frame provenance differs")
        require(feature["Q"] == candidate["logit"] == candidate["scores"]["Q"]
                and feature["M"] == candidate["scores"]["M"], "Saved Q/M score transport differs")
        require(all(value is None or finite(value) for value in candidate["scores"].values()), "Invalid original acceptance score")
        if candidate["frame_key"] is not None:
            require(candidate["frame_key"] in frame_index, "Candidate frame absent")
        if candidate["logit"] is None:
            missing += 1
            require(candidate["cohort"] == "HOU_stress" and feature["status"] == "missing_image"
                    and all(value is None for value in candidate["scores"].values()), "Missing-image registry changed")
        else:
            require(feature["status"] == "observed", "Observed score lost features")
        if candidate["context"] == "nba_out_of_fold":
            name = next(name for name, game in GAMES.items() if game == candidate["game_id"])
            require(candidate["fit"] == OLD_BASES[name] and candidate["gate_fit"] == "outer_" + name,
                    "Outer evaluation scorer/gate differs")
        else:
            require(candidate["fit"] == "all_nba" and candidate["gate_fit"] == "final_all_NBA",
                    "Secondary/HOU/historical evaluation scorer differs")
    if exact_counts:
        require(missing == 11 and len(nba) == 18813, "Missing-image/NBA count differs")
        require(Counter(r["cohort"] for r in loaded["candidates"]) ==
                {"package": 19632, "HOU_main": 10778, "HOU_stress": 960, "historical": 60}, "Evaluation cohort inventory differs")
    expected_cross = {name + "_only|" + cid for name, gid in GAMES.items()
                      for cid, row in loaded["nba_by_id"].items() if row["game_id"] != gid}
    require(set(indices["cross"]) == expected_cross, "Complete cross-feature registry differs")
    for key, feature in indices["cross"].items():
        base, cid = key.split("|", 1)
        candidate = loaded["nba_by_id"][cid]
        require(feature["fit"] == base and feature["frame_key"] == base + "|" + candidate["frame_id"]
                and GAMES[base.removesuffix("_only")] != candidate["game_id"], "Cross-feature source leakage/identity mismatch")
        require(feature["status"] == "observed", "NBA cross feature lost image")
    for index in (indices["cross"], indices["evaluation"]):
        for key, feature in index.items():
            for other in feature.get("pool_provenance", {}).get("excluded_self_row_keys", []):
                require(other in index and index[other]["frame_key"] == feature["frame_key"]
                        and index[other]["fit"] == feature["fit"], "Saved pool provenance mixed base scorers/frames")
    grouped = {gate: [] for gate in GATES}
    for member in loaded["fit_membership"]:
        require(member["gate_fit"] in GATES, "Unknown membership gate")
        grouped[member["gate_fit"]].append(member)
    loaded["membership_by_gate"] = {}
    for gate, members in grouped.items():
        index = unique(members, "row_key", "gate membership")
        loaded["membership_by_gate"][gate] = index
        expected_candidates = {cid for cid, row in loaded["nba_by_id"].items()
                               if gate == "final_all_NBA" or row["game_id"] != GAMES[gate.removeprefix("outer_")]}
        require({r["candidate_id"] for r in members} == expected_candidates and len(members) == len(expected_candidates),
                "Gate full registry dropped/duplicated candidates")
        for key, member in index.items():
            candidate = loaded["nba_by_id"][member["candidate_id"]]
            base = expected_source(gate, candidate)
            expected_key = candidate["row_key"] if gate == "final_all_NBA" else base + "|" + member["candidate_id"]
            require(key == expected_key and member["base_fit"] == base and member["game_id"] == candidate["game_id"]
                    and member["target"] == candidate["target"], "Gate membership source/target mismatch")
            known = candidate["target"] is not None
            require(member["included_in_fitting"] is known, "Original known-target mask changed")
            require(known or member["objective_weight"] is None, "Unknown candidate acquired a fit weight")
        if exact_counts:
            require(sum(r["included_in_fitting"] for r in members) == KNOWN_COUNTS[gate], "Known fitting count differs")
        fit_inputs(gate, loaded)
    validate_fixed_policies(loaded["frames"], loaded["candidates"], loaded["fixed_policies"])
    loaded["transport_counts"] = {key: len(loaded[key]) for key in EXPECTED_COUNTS}
    return loaded


def load_inputs(root):
    """Load accepted saved artifacts after caller binding verification."""
    base = Path(root) / SOURCE
    loaded = {}
    for name, filename in FILES.items():
        with (base / filename).open(encoding="utf-8") as stream:
            loaded[name] = [json.loads(line) for line in stream if line.strip()]
    loaded["original_J_models"] = {
        gate: json.loads((base / "fits" / (gate + "_J.json")).read_text(encoding="utf-8")) for gate in GATES}
    loaded["input_paths"] = list(INPUT_PATHS)
    return validate_loaded(loaded)
