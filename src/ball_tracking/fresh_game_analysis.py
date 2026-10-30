"""CPU-only fixed-choice diagnostic on accepted fresh-game references.

No fitting, inference, threshold search, fallback, temporal fill, or J selector.
The pure record consumer is also the small-fixture test interface.
"""
from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json
import math

POLICIES = ("native", "quality_top")
VIEWS = ("before", "Q", "J")
DEFAULT_REFERENCE = "data/outputs/ball_tracking/fresh_game_diagnostic_v0_1/accepted/reference.json"
FIXED_POPULATION = {"frames": 360, "eligible": 310, "certain_hidden": 32, "unknown": 18}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value, label):
    require(type(value) in (int, float) and math.isfinite(value), f"Invalid finite {label}")
    return float(value)


def unique(rows, key, label):
    result = {}
    for row in rows:
        value = row.get(key)
        require(isinstance(value, str) and value and value not in result, f"Duplicate/missing {label}")
        result[value] = row
    return result


def _reference(frame, dimensions):
    annotation = frame["annotation"]
    require(annotation["frame_index"] == frame["source_frame_index"], "Reference frame index mismatch")
    require(annotation["annotation_status"] == "labeled", "Incomplete accepted annotation")
    visibility = annotation["visibility"]
    require(visibility in ("fully_visible", "partially_visible", "not_visible", "indeterminate"),
            "Invalid accepted visibility")
    geometry = annotation["geometry"]
    if annotation["localization_eligible"]:
        require(visibility in ("fully_visible", "partially_visible") and geometry is not None,
                "Eligible reference lacks visible geometry")
        require(annotation["game_ball_identity_certainty"] in ("certain", "probable"), "Ambiguous eligible reference")
        x, y = geometry["center_xy_px"]
        x, y = number(x, "reference x"), number(y, "reference y")
        require(0 <= x < dimensions[0] and 0 <= y < dimensions[1], "Reference outside source")
        require(number(geometry["uncertainty_radius_px"], "reference uncertainty") > 0,
                "Invalid reference uncertainty")
        return "eligible", (x, y)
    require(geometry is None, "Ineligible reference unexpectedly supplies geometry")
    if visibility == "not_visible" and annotation["game_ball_identity_certainty"] == "certain":
        require(annotation["absence_reason"] in ("occluded", "out_of_frame", "unknown"), "Missing absence reason")
        return "certain_hidden", None
    return "unknown", None


def _category(reference_category, center, in_bounds, reference_center):
    distance = math.dist(center, reference_center) if reference_center is not None else None
    if reference_category == "eligible":
        # An out-of-bounds emission cannot be a valid source-image localization,
        # including when it happens to lie within ten pixels of an edge reference.
        return ("eligible_match" if in_bounds and distance <= 10.0 else "eligible_miss"), distance
    return reference_category, distance


def _choice(point, reference_category):
    if point is None:
        return {"candidate_id": None, "center_xy_px": None, "in_source_bounds": None,
                "native_or_weak": None, "evaluation_category": "missing_choice",
                "distance_to_reference_px": None, "scores": {"Q": None, "J": None},
                "accepted": {v: False for v in VIEWS}, "score_status": "missing_choice"}
    return {k: point[k] for k in ("candidate_id", "center_xy_px", "in_source_bounds", "native_or_weak",
                                  "evaluation_category", "distance_to_reference_px", "scores",
                                  "accepted", "score_status")}


def _counts(members, policy, view):
    counts = Counter({k: 0 for k in ("frames", "eligible", "certain_hidden", "unknown", "emitted",
                     "correct", "wrong_eligible", "hidden_emissions", "unknown_emissions", "missing_choices",
                     "out_of_bounds_choices", "out_of_bounds_emissions", "correct_rejected", "wrong_rejected",
                     "hidden_rejected", "unknown_rejected", "no_emission")})
    for frame in members:
        counts["frames"] += 1
        counts[frame["reference_category"]] += 1
        choice = frame["choices"][policy]
        category, accepted = choice["evaluation_category"], choice["accepted"][view]
        if choice["candidate_id"] is None:
            counts["missing_choices"] += 1
        elif choice["in_source_bounds"] is False:
            counts["out_of_bounds_choices"] += 1
        if accepted:
            counts["emitted"] += 1
            counts[{"eligible_match": "correct", "eligible_miss": "wrong_eligible",
                    "certain_hidden": "hidden_emissions", "unknown": "unknown_emissions"}[category]] += 1
            counts["out_of_bounds_emissions"] += int(choice["in_source_bounds"] is False)
        else:
            counts["no_emission"] += 1
            if category != "missing_choice":
                counts[{"eligible_match": "correct_rejected", "eligible_miss": "wrong_rejected",
                        "certain_hidden": "hidden_rejected", "unknown": "unknown_rejected"}[category]] += 1
    require(counts["correct"] + counts["wrong_eligible"] <= counts["eligible"], "Eligible partition failure")
    require(counts["emitted"] + counts["no_emission"] == counts["frames"], "Emission partition failure")
    return dict(counts)


def _groups(frames):
    groups = defaultdict(list)
    for row in frames:
        fields = {"clip_id": row["clip_id"], "visibility": row["visibility"],
                  "native_success_group": row["native_success_group"]}
        keys = [("all", {}), ("clip", {"clip_id": fields["clip_id"]}),
                ("visibility", {"visibility": fields["visibility"]}),
                ("native_success", {"native_success_group": fields["native_success_group"]}),
                ("clip_visibility_native_success", fields)]
        for scope, identity in keys:
            groups[json.dumps({"scope": scope, **identity}, sort_keys=True)].append(row)
    return [(json.loads(key), members) for key, members in sorted(groups.items())]


def _coverage(members):
    eligible = [f for f in members if f["reference_category"] == "eligible"]
    return {"frames": len(members), "eligible_frames": len(eligible),
            "frames_with_any_candidate": sum(bool(f["pool"]["candidate_ids"]) for f in members),
            "empty_pool_frames": sum(not f["pool"]["candidate_ids"] for f in members),
            "eligible_with_matching_candidate": sum(bool(f["pool"]["matching_candidate_ids"]) for f in eligible),
            "eligible_without_matching_candidate": sum(not f["pool"]["matching_candidate_ids"] for f in eligible),
            "eligible_with_matching_native_candidate": sum(bool(f["pool"]["matching_native_ids"]) for f in eligible),
            "eligible_with_matching_weak_candidate": sum(bool(f["pool"]["matching_weak_ids"]) for f in eligible),
            "eligible_weak_only_matching_pool": sum(bool(f["pool"]["matching_weak_ids"]) and not f["pool"]["matching_native_ids"] for f in eligible),
            "weak_match_available_on_native_failure": sum(f["native_success_group"] == "failure" and bool(f["pool"]["matching_weak_ids"]) for f in eligible),
            "matching_candidate_survives_Q": sum(bool(f["pool"]["matching_Q_positive_ids"]) for f in eligible),
            "matching_candidate_survives_J": sum(bool(f["pool"]["matching_J_positive_ids"]) for f in eligible)}


def _transitions(members, policy, left, right):
    names = ("correct_gained", "correct_lost", "wrong_newly_rejected", "wrong_newly_accepted",
             "hidden_newly_rejected", "hidden_newly_accepted", "unknown_newly_rejected", "unknown_newly_accepted")
    ids = {key: [] for key in names}
    unchanged = 0
    for frame in members:
        choice = frame["choices"][policy]
        a, b = choice["accepted"][left], choice["accepted"][right]
        if a == b:
            unchanged += 1
            continue
        category = choice["evaluation_category"]
        if category == "eligible_match":
            key = "correct_gained" if b else "correct_lost"
        else:
            prefix = {"eligible_miss": "wrong", "certain_hidden": "hidden", "unknown": "unknown"}[category]
            key = prefix + ("_newly_accepted" if b else "_newly_rejected")
        ids[key].append({"frame_key": frame["frame_key"], "candidate_id": choice["candidate_id"]})
    return {"policy": policy, "from": left, "to": right, "frames": len(members),
            "unchanged_acceptance_frames": unchanged, "counts": {k: len(v) for k, v in ids.items()},
            "exact_cases": ids, "candidate_choice_changed": False}


def analyze_records(reference, frames, candidates, scores, expected_population=None):
    """Validate joins and return complete, JSON-serializable diagnostic records."""
    require(reference.get("status") == "human_accepted_AI_reference", "References lack human acceptance")
    require(reference.get("role") == "diagnostic_development" and reference.get("training_eligible") is False
            and reference.get("checkpoint_selection_eligible") is False, "Reference role/eligibility changed")
    accepted_frames = reference["frames"]
    accepted = unique(accepted_frames, "frame_key", "accepted frame")
    observed = unique(frames, "frame_key", "inference frame")
    require(list(accepted) == list(observed), "Complete ordered accepted frame census differs")
    clips = unique(reference["clips"], "clip_id", "reference clip")
    points = unique(candidates, "candidate_id", "candidate")
    scored = unique(scores, "candidate_id", "candidate score")
    require(list(points) == list(scored), "Complete ordered candidate/score census differs")
    dimensions = {k: (v["source_metadata"]["width"], v["source_metadata"]["height"]) for k, v in clips.items()}
    references = {k: _reference(f, dimensions[f["clip_id"]]) for k, f in accepted.items()}
    population = Counter({"frames": len(frames), "eligible": 0, "certain_hidden": 0, "unknown": 0})
    population.update(category for category, _ in references.values())
    if expected_population is not None:
        require(dict(population) == expected_population, "Frozen accepted-reference population differs")
    pools = defaultdict(list)
    enriched = []
    for point in candidates:
        key = point["frame_key"]
        require(key in accepted, "Candidate refers to unknown frame")
        frame, score = accepted[key], scored[point["candidate_id"]]
        require(score["frame_key"] == key, "Candidate score joins another frame")
        require(point["clip_id"] == frame["clip_id"] and point["source_frame_index"] == frame["source_frame_index"],
                "Candidate source identity differs")
        require(point["game_id"] == reference["game_id"] and point["frame_id"] == observed[key]["frame_id"]
                and point["block_id"] == observed[key]["block_id"], "Candidate game/frame/block identity differs")
        require(point["source_pts_ticks"] == frame["native_pts_ticks"] and point["time_base"] == frame["native_time_base"]
                and point["source_png"] == frame["source_png"]
                and point["source_video_sha256"] == clips[frame["clip_id"]]["source_video"]["sha256"],
                "Candidate source timing/pixel identity differs")
        width, height = dimensions[frame["clip_id"]]
        require((point["width_px"], point["height_px"]) == (width, height), "Candidate source dimensions differ")
        require(point["native_or_weak"] in ("native", "weak"), "Unknown candidate origin")
        require(type(point["selected_native"]) is bool, "Malformed native selection flag")
        require(not point["selected_native"] or point["native_or_weak"] == "native", "Weak candidate marked native choice")
        x, y = point["center_xy_px"]
        x, y = number(x, "candidate x"), number(y, "candidate y")
        in_bounds = 0 <= x < width and 0 <= y < height
        require(type(point["in_source_bounds"]) is bool and point["in_source_bounds"] == in_bounds,
                "Candidate source-bounds flag differs")
        if in_bounds:
            require(score["status"] == "observed", "In-bounds candidate lacks observed scores")
            values = {arm: number(score[arm], arm + " score") for arm in ("Q", "J")}
        else:
            require(score["status"] == "out_of_source_bounds" and score["Q"] is None and score["J"] is None,
                    "Out-of-bounds score must remain explicitly null")
            values = {"Q": None, "J": None}
        category, distance = _category(references[key][0], (x, y), in_bounds, references[key][1])
        uncertainty = frame["annotation"]["geometry"]["uncertainty_radius_px"] if references[key][1] else None
        item = {**point, "evaluation_category": category, "reference_category": references[key][0],
                "distance_to_reference_px": distance, "scores": values, "score_status": score["status"],
                "accepted": {"before": True, **{arm: values[arm] is not None and values[arm] > 0.0 for arm in ("Q", "J")}},
                "exact_match_boundary": distance == 10.0 if distance is not None else False,
                "within_recorded_uncertainty_of_match_boundary": abs(distance - 10.0) <= uncertainty if distance is not None else False,
                "score_zero": {arm: values[arm] == 0.0 if values[arm] is not None else False for arm in ("Q", "J")}}
        enriched.append(item)
        pools[key].append(item)
    result_frames, policies, case_index = [], [], []
    for key, original in accepted.items():
        produced, pool = observed[key], pools[key]
        require(produced["clip_id"] == original["clip_id"] and produced["source_frame_index"] == original["source_frame_index"],
                "Inference frame source identity differs")
        require(produced["source_pts_ticks"] == original["native_pts_ticks"] and produced["time_base"] == original["native_time_base"]
                and produced["duration_ticks"] == original["native_duration_ticks"], "Inference frame native timing differs")
        require(produced["source_png"] == original["source_png"], "Inference source PNG binding differs")
        require(produced["source_video_sha256"] == clips[original["clip_id"]]["source_video"]["sha256"], "Inference source video differs")
        ids = [p["candidate_id"] for p in pool]
        require([p["candidate_index"] for p in pool] == list(range(len(pool))), "Candidate index/order differs")
        require(produced["candidate_ids"] == ids, "Frame candidate census/order differs")
        require(produced["game_id"] == reference["game_id"], "Inference game identity differs")
        require(produced.get("point_chosen_before_acceptance") is True and produced.get("fallback_allowed") is False,
                "Inference fixed-choice/no-fallback contract differs")
        native = [p for p in pool if p["selected_native"]]
        require(len(native) <= 1, "Multiple native choices")
        require(produced["native_selected_candidate_id"] == (native[0]["candidate_id"] if native else None), "Frozen native identity differs")
        ranked = sorted((p for p in pool if p["in_source_bounds"]), key=lambda p: (-p["scores"]["Q"], p["candidate_id"]))
        ties = [p["candidate_id"] for p in ranked if p["scores"]["Q"] == ranked[0]["scores"]["Q"]] if ranked else []
        require(produced["quality_top_candidate_id"] == (ranked[0]["candidate_id"] if ranked else None), "Frozen Q-top identity differs")
        require(produced["quality_top_tied_candidate_ids"] == ties, "Frozen Q-top tie inventory differs")
        category, reference_center = references[key]
        choices = {"native": _choice(native[0] if native else None, category),
                   "quality_top": _choice(ranked[0] if ranked else None, category)}
        native_success = ("correct" if choices["native"]["evaluation_category"] == "eligible_match" else "failure") if category == "eligible" else "not_eligible"
        matched = [p for p in pool if p["evaluation_category"] == "eligible_match"]
        inventory = {"candidate_ids": ids, "native_ids": [p["candidate_id"] for p in pool if p["native_or_weak"] == "native"],
                     "weak_ids": [p["candidate_id"] for p in pool if p["native_or_weak"] == "weak"],
                     "out_of_bounds_ids": [p["candidate_id"] for p in pool if not p["in_source_bounds"]],
                     "matching_candidate_ids": [p["candidate_id"] for p in matched],
                     "matching_native_ids": [p["candidate_id"] for p in matched if p["native_or_weak"] == "native"],
                     "matching_weak_ids": [p["candidate_id"] for p in matched if p["native_or_weak"] == "weak"],
                     **{f"matching_{arm}_positive_ids": [p["candidate_id"] for p in matched if p["accepted"][arm]] for arm in ("Q", "J")}}
        flags = []
        if category == "eligible" and not matched:
            flags.append("no_matching_candidate")
        if native_success == "failure" and inventory["matching_weak_ids"]:
            flags.append("weak_match_available_on_native_failure")
        if inventory["out_of_bounds_ids"]:
            flags.append("out_of_bounds_candidate_present")
        if category == "unknown":
            flags.append("unknown_reference_not_scored_as_error")
        for policy, choice in choices.items():
            outcome = choice["evaluation_category"]
            if outcome == "missing_choice":
                flags.append(policy + ":missing_choice")
            elif outcome == "eligible_miss":
                flags.append(policy + (":wrong_choice_match_available" if matched else ":wrong_choice_no_match"))
            for arm in ("Q", "J"):
                if outcome == "eligible_match":
                    flags.append(f"{policy}:{arm}:" + ("preserved_correct" if choice["accepted"][arm] else "rejected_correct"))
                elif choice["accepted"][arm] and outcome in ("eligible_miss", "certain_hidden"):
                    flags.append(f"{policy}:{arm}:" + ("accepted_wrong" if outcome == "eligible_miss" else "hidden_emission"))
        row = {**original, "frame_id": produced["frame_id"], "block_id": produced["block_id"], "game_id": reference["game_id"],
               "visibility": original["annotation"]["visibility"], "reference_category": category,
               "reference_center_xy_px": list(reference_center) if reference_center else None,
               "native_success_group": native_success, "original_native_outcome": choices["native"]["evaluation_category"],
               "pool": inventory, "choices": choices, "quality_top_tied_candidate_ids": ties,
               "diagnostic_flags": flags, "source_video_sha256": produced["source_video_sha256"]}
        result_frames.append(row)
        for policy in POLICIES:
            policies.append({"row_key": policy + "|" + key, "frame_key": key, "clip_id": row["clip_id"],
                             "source_frame_index": row["source_frame_index"], "visibility": row["visibility"],
                             "reference_category": category, "native_success_group": native_success,
                             "policy": policy, **choices[policy], "point_chosen_before_acceptance": True,
                             "fallback_allowed": False})
        case_index.append({"frame_key": key, "clip_id": row["clip_id"], "source_frame_index": row["source_frame_index"],
                           "source_png": row["source_png"], "reference_category": category,
                           "visibility": row["visibility"], "native_success_group": native_success,
                           "diagnostic_flags": flags, "native_candidate_id": choices["native"]["candidate_id"],
                           "quality_top_candidate_id": choices["quality_top"]["candidate_id"],
                           "all_candidate_ids": ids, "matching_candidate_ids": inventory["matching_candidate_ids"]})
    tables, paired = [], []
    for scope, members in _groups(result_frames):
        tables.append({**scope, "kind": "pool_coverage", "counts": _coverage(members)})
        for policy in POLICIES:
            for view in VIEWS:
                tables.append({**scope, "kind": "fixed_policy", "policy": policy, "view": view,
                               "counts": _counts(members, policy, view)})
            for left, right in (("before", "Q"), ("before", "J"), ("Q", "J")):
                paired.append({**scope, **_transitions(members, policy, left, right)})
    summary = {"status": "completed_fixed_fresh_game_diagnostic_no_adoption", "population": dict(population),
               "candidate_count": len(enriched), "in_bounds_candidates": sum(p["in_source_bounds"] for p in enriched),
               "out_of_bounds_candidates": sum(not p["in_source_bounds"] for p in enriched),
               "pool_coverage": _coverage(result_frames),
               "fixed_policy_counts": {p: {v: _counts(result_frames, p, v) for v in VIEWS} for p in POLICIES},
               "acceptance_threshold": 0.0, "acceptance_rule": "strictly_greater", "match_radius_source_px": 10.0,
               "match_rule": "in_source_bounds_and_distance_less_than_or_equal", "unknown_counted_as_errors": False,
               "out_of_bounds_raw_emissions_count_as_eligible_wrong_or_hidden_by_reference": True,
               "selected_threshold": None, "new_selector": False, "temporal_recovery_measurement": "not_measured",
               "training_eligible": False, "checkpoint_selection_eligible": False,
               "limits": ["Three fixed event-clipped starts from one diagnostic-development game; no cross-game accuracy claim.",
                          "AI-authored human-accepted references retain placement uncertainty; boundary flags do not change correctness.",
                          "Overlapping scopes/candidate matches are not independent plays or additive evidence.",
                          "No automatic fit, adoption, threshold rescue, or recovery claim."]}
    return {"frames": result_frames, "candidates": enriched, "policies": policies, "tables": tables,
            "paired": paired, "case_index": case_index, "summary": summary}


def binding(root, path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return {"path": path.relative_to(Path(root).resolve()).as_posix(), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def _read_json(path):
    def invalid(value):
        raise ValueError("Invalid JSON numeric constant: " + value)
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=invalid)


def _bound_path(root, value):
    path = (root / value["path"]).resolve()
    require(path.is_relative_to(root), "Bound path escapes repository")
    require(binding(root, path) == {k: value[k] for k in ("path", "bytes", "sha256")}, "Input binding changed: " + value["path"])
    return path


def analyze(root, inference_dir, output_dir, accepted_path=DEFAULT_REFERENCE, expected_population=FIXED_POPULATION):
    """Consume a completed, independently gated inference attempt once."""
    root = Path(root).resolve()
    inference_dir = (root / inference_dir).resolve()
    output = (root / output_dir).resolve()
    require(inference_dir.is_relative_to(root) and output.is_relative_to(root), "Analysis paths escape repository")
    require(not output.exists(), "Analysis output exists; overwrite/retry refused")
    output.mkdir(parents=True)
    try:
        completion_path = inference_dir / "completed.json"
        completion = _read_json(completion_path)
        require(completion["status"] == "completed_fresh_game_inference_no_fitting", "Incomplete inference attempt")
        accepted_path = (root / accepted_path).resolve()
        require(_bound_path(root, completion["accepted_reference"]) == accepted_path, "Accepted reference binding differs")
        reference = _read_json(accepted_path)
        inputs, loaded = [binding(root, completion_path), binding(root, accepted_path)], {}
        for name in ("frames", "candidates", "scores"):
            path = _bound_path(root, completion[name])
            require(path.is_relative_to(inference_dir), "Inference record file lies outside attempt")
            loaded[name] = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
            inputs.append(binding(root, path))
        result = analyze_records(reference, **loaded, expected_population=expected_population)
        artifacts = {}
        for name, value in result.items():
            path = output / (name + (".json" if name == "summary" else ".jsonl"))
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                if name == "summary":
                    json.dump(value, stream, indent=2, allow_nan=False)
                    stream.write("\n")
                else:
                    for row in value:
                        stream.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
            artifacts[name] = binding(root, path)
        receipt = {"status": "completed_fresh_game_analysis_no_fitting", "inputs": inputs, "outputs": artifacts,
                   "population": result["summary"]["population"], "scientific_model_calls": 0,
                   "new_threshold_or_selector": False}
        with (output / "completed.json").open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(receipt, stream, indent=2, allow_nan=False)
            stream.write("\n")
        return receipt
    except Exception as error:
        with (output / "failed.json").open("x", encoding="utf-8", newline="\n") as stream:
            json.dump({"status": "failed_fresh_game_analysis_preserved", "error_type": type(error).__name__,
                       "error": str(error)}, stream, indent=2)
            stream.write("\n")
        raise
