"""CPU-only census of sealed alternate-producer candidates, never a model fit.

The original geometric target rules are reused after the label-blind capture is
sealed. Physical runs ignore administrative block boundaries. Historical semantic
roles are reported separately and never become localization targets.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import traceback

from . import candidate_quality_data as original

ROOT = Path(__file__).resolve().parents[2]
PREPARATION = "data/outputs/ball_tracking/candidate_quality_pilot_v0_1/preparation"
HISTORICAL = "data/outputs/ball_tracking/candidate_acceptance_gate_v0_1/attempt_001/analysis/historical_rows.jsonl"
OLD_SCORES = "data/outputs/ball_tracking/candidate_acceptance_gate_v0_1/attempt_001/analysis/candidate_scores.jsonl"
EXTERNAL = "data/outputs/ball_tracking/candidate_training_coverage_review_v0_1/support/external_stress_supplement.json"
CONDITIONS = ("chosen_native_known_distant", "chosen_native_certain_hidden", "weak_positive_native_wrong_or_missing")
require = original.require


def rows(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def source_key(row):
    source = row.get("source_video_sha256") or row["source_video"]["sha256"]
    return source, row["source_frame_index"]


def point_key(row):
    center = row["center_xy_px"]
    require(len(center) == 2 and all(type(v) in (int, float) and math.isfinite(v) for v in center),
            "Invalid canonical point")
    return (*source_key(row), *center)


def crop_key(row):
    return (*source_key(row), *(math.floor(v) for v in row["center_xy_px"]))


def point_metadata(row):
    """Geometry only; floor crop equality is distinct from point-readout equality."""
    x, y = row["center_xy_px"]
    width, height = row["width_px"], row["height_px"]
    left, top = math.floor(x) - 32, math.floor(y) - 32
    valid = max(0, min(width, left + 64) - max(0, left)) * max(0, min(height, top + 64) - max(0, top))
    inside = 0 <= x < width and 0 <= y < height
    return {"crop_box": [left, top, left + 64, top + 64], "padding_pixels": 4096 - valid,
            "point_model_input_eligible": inside,
            "point_input_xy": [4 * (x - left + .5) - .5 - 16, 4 * (y - top + .5) - .5 - 16] if inside else None,
            "point_model_input_missing_reason": None if inside else "original_point_model_rejects_out_of_source_center"}


def unique_index(items, key, message):
    result = {}
    for item in items:
        ident = key(item)
        require(ident not in result, message)
        result[ident] = item
    return result


def physical_runs(frame_rows):
    """Canonical video SHA + source index; a block edge does not split a run."""
    physical = {}
    for frame in frame_rows:
        key = source_key(frame)
        if key in physical:
            prior = physical[key]
            require((prior["game_id"], prior["source_pts_ticks"], prior["time_base"], prior["source_png"]["rgb_sha256"])
                    == (frame["game_id"], frame["source_pts_ticks"], frame["time_base"], frame["source_png"]["rgb_sha256"]),
                    "Conflicting duplicate physical frame")
        else:
            physical[key] = frame
    grouped = defaultdict(list)
    for frame in physical.values():
        grouped[(frame["game_id"], source_key(frame)[0])].append(frame)
    result = []
    for (game, video), items in sorted(grouped.items()):
        items.sort(key=lambda row: row["source_frame_index"])
        current = []

        def emit():
            if current:
                result.append({"game_id": game, "source_video_sha256": video,
                    "first_source_frame": current[0]["source_frame_index"],
                    "last_source_frame": current[-1]["source_frame_index"], "frames": len(current),
                    "block_ids": sorted({row["block_id"] for row in current}),
                    "frame_ids": [row["frame_id"] for row in current]})

        for frame in items:
            if current and frame["source_frame_index"] != current[-1]["source_frame_index"] + 1:
                emit()
                current = []
            if current:
                require(frame["time_base"] == current[-1]["time_base"], "Timebase changed within physical run")
                duration = current[-1].get("duration_ticks")
                if duration is not None:
                    require(frame["source_pts_ticks"] == current[-1]["source_pts_ticks"] + duration,
                            "Noncontiguous timing at consecutive source indices")
            current.append(frame)
        emit()
    return result


def frame_support(frame_rows):
    physical = {source_key(row) for row in frame_rows}
    runs = physical_runs(frame_rows)
    games = sorted({row["game_id"] for row in frame_rows})
    return {"frames": len(physical), "frame_ids": sorted({row["frame_id"] for row in frame_rows}),
            "games": len(games), "game_ids": games, "blocks": len({row["block_id"] for row in frame_rows}),
            "block_ids": sorted({row["block_id"] for row in frame_rows}),
            "source_videos": len({source_key(row)[0] for row in frame_rows}),
            "physical_index_runs": len(runs), "largest_run_frames": max((row["frames"] for row in runs), default=0),
            "run_length_histogram": dict(sorted(Counter(row["frames"] for row in runs).items())), "runs": runs,
            "by_game": {game: {"frames": len({source_key(row) for row in frame_rows if row["game_id"] == game}),
                "blocks": len({row["block_id"] for row in frame_rows if row["game_id"] == game}),
                "physical_index_runs": sum(row["game_id"] == game for row in runs)} for game in games}}


def support(items, frames):
    ids = {row["frame_id"] for row in items}
    result = frame_support([frames[key] for key in sorted(ids)])
    result.update(candidate_rows=len(items), candidate_ids=[row["candidate_id"] for row in items],
                  unique_exact_points=len({point_key(row) for row in items}),
                  unique_floor_crops=len({crop_key(row) for row in items}),
                  target_groups=dict(Counter(row["target_group"] for row in items)))
    for game, own in result["by_game"].items():
        own["candidate_rows"] = sum(row["game_id"] == game for row in items)
    return result


def validate_population(frame_rows, candidate_rows):
    frames = unique_index(frame_rows, lambda row: row["frame_id"], "Duplicate frame ID")
    unique_index(frame_rows, source_key, "Repeated physical frame context")
    candidates = unique_index(candidate_rows, lambda row: row["candidate_id"], "Duplicate candidate ID")
    pools = defaultdict(list)
    for row in candidate_rows:
        require(row["frame_id"] in frames, "Candidate has no frame")
        frame = frames[row["frame_id"]]
        for key in ("block_id", "game_id", "domain", "source_frame_index", "source_pts_ticks", "time_base", "source_video_sha256", "source_png"):
            require(row[key] == frame[key], "Candidate/frame transport differs: " + key)
        require(row["native_or_weak"] in ("native", "weak"), "Unknown origin")
        require(row["width_px"] == frame["source_video"]["width_px"] and row["height_px"] == frame["source_video"]["height_px"],
                "Candidate/source dimension mismatch")
        transport = {"center_x": row["center_xy_px"][0], "center_y": row["center_xy_px"][1],
                     "in_source_bounds": row["in_source_bounds"]}
        target = original.candidate_target(frame, transport, row["width_px"], row["height_px"])
        require(all(row[key] == value for key, value in target.items()), "Original target transport changed")
        pools[row["frame_id"]].append(row)
    views = {}
    for fid, frame in frames.items():
        require(frame["domain"] == "nba" and frame["game_id"] in original.NBA_GAMES
                and frame["original_source_role"] == "training", "Forbidden capture source")
        pool = pools[fid]
        require([row["candidate_id"] for row in pool] == frame["candidate_ids"], "Pool identity/order mismatch")
        require([row["candidate_index"] for row in pool] == list(range(len(pool))), "Candidate index mismatch")
        require(frame["candidate_count"] == len(pool), "Frame candidate count mismatch")
        selected = frame["native_selected_candidate_index"]
        require(selected is None or type(selected) is int and 0 <= selected < len(pool), "Invalid selected identity")
        choice = pool[selected] if selected is not None else None
        require(choice is None or choice["native_or_weak"] == "native", "Native choice is a weak candidate")
        require(frame["native_center_xy_px"] == (choice["center_xy_px"] if choice else None), "Selected center differs")
        if frame["kind"] == "positive":
            outcome = "missing" if choice is None else "correct" if choice["target"] == 1 else "wrong"
        elif frame["kind"] == "hidden":
            outcome = "hidden_emission" if choice else "hidden_abstention"
        else:
            require(frame["kind"] == "masked", "Unknown frame kind")
            outcome = "masked_observed" if choice else "masked_missing"
        views[fid] = {"native_outcome": outcome, "chosen_candidate_id": choice["candidate_id"] if choice else None,
                      "chosen_center_xy_px": choice["center_xy_px"] if choice else None,
                      "chosen_target_group": choice["target_group"] if choice else None,
                      "candidate_count": len(pool), "native_count": sum(row["native_or_weak"] == "native" for row in pool),
                      "known_positive_ids": [row["candidate_id"] for row in pool if row["target"] == 1],
                      "weak_positive_ids": [row["candidate_id"] for row in pool if row["target"] == 1 and row["native_or_weak"] == "weak"],
                      "target_counts": dict(Counter(row["target_group"] for row in pool))}
    return frames, candidates, pools, views


def category_rows(candidates, views, comparison_views=None):
    comparison_views = views if comparison_views is None else comparison_views
    groups = {name: [] for name in CONDITIONS}
    groups.update({name: [] for name in ("weak_positive_native_wrong", "weak_positive_native_missing",
                                        "weak_positive_native_already_correct", "chosen_native_boundary_unknown",
                                        "chosen_native_wrong_all", "all_known_positive", "all_boundary_unknown", "all_masked_unknown")})
    for origin in ("native", "weak"):
        for target in ("positive", "eligible_distant_miss", "certain_hidden", "boundary_unknown", "masked_unknown"):
            groups["all_" + origin + "_" + target] = []
    for row in candidates:
        own, comparison = views[row["frame_id"]], comparison_views[row["frame_id"]]
        chosen = own["chosen_candidate_id"] == row["candidate_id"]
        group = row["target_group"]
        groups["all_" + row["native_or_weak"] + "_" + group].append(row)
        if row["target"] == 1:
            groups["all_known_positive"].append(row)
        if group in ("boundary_unknown", "masked_unknown"):
            groups["all_" + group].append(row)
        if chosen and group == "eligible_distant_miss":
            groups[CONDITIONS[0]].append(row)
        if chosen and group == "certain_hidden":
            groups[CONDITIONS[1]].append(row)
        if chosen and group == "boundary_unknown":
            groups["chosen_native_boundary_unknown"].append(row)
        if chosen and own["native_outcome"] == "wrong":
            groups["chosen_native_wrong_all"].append(row)
        if row["native_or_weak"] == "weak" and row["target"] == 1:
            state = comparison["native_outcome"]
            if state in ("wrong", "missing"):
                groups[CONDITIONS[2]].append(row)
                groups["weak_positive_native_" + state].append(row)
            elif state == "correct":
                groups["weak_positive_native_already_correct"].append(row)
    return groups


def coverage_gate(groups):
    conditions = {}
    for name in CONDITIONS:
        items = groups[name]
        games = sorted({row["game_id"] for row in items})
        folds = {fit: {"candidate_rows": sum(row["game_id"] in fit_games for row in items),
                       "frames": len({source_key(row) for row in items if row["game_id"] in fit_games})}
                 for fit, fit_games in original.FIT_GAMES.items() if fit != "all_nba"}
        conditions[name] = {"game_ids": games, "at_least_two_games": len(games) >= 2,
                            "outer_training_folds": folds, "all_outer_folds_nonzero": all(row["candidate_rows"] > 0 for row in folds.values())}
        conditions[name]["passed"] = conditions[name]["at_least_two_games"] and conditions[name]["all_outer_folds_nonzero"]
    return {"passed": all(row["passed"] for row in conditions.values()), "conditions": conditions,
            "meaning": "Prospective engineering coverage screen, not power or generalization evidence."}


def novelty_rows(new_candidates, old_candidates, old_frames, historical):
    def index(items, key, id_field):
        result = defaultdict(list)
        for row in items:
            result[key(row)].append(row[id_field])
        return result
    old_exact, old_crop = index(old_candidates, point_key, "candidate_id"), index(old_candidates, crop_key, "candidate_id")
    hist_exact, hist_crop = index(historical, point_key, "row_key"), index(historical, crop_key, "row_key")
    hist_frames = index(historical, source_key, "row_key")
    hist_by_id = {row["row_key"]: row for row in historical}
    old_source = {source_key(row): row for row in old_frames}
    new_exact = index(new_candidates, point_key, "candidate_id")
    result = []
    for row in new_candidates:
        frame = old_source[source_key(row)]
        require(row["source_png"]["rgb_sha256"] == frame["source_png"]["rgb_sha256"], "Novelty source RGB identity differs")
        history_ids = hist_frames[source_key(row)]
        for hid in history_ids:
            require(hist_by_id[hid]["source_png"]["rgb_sha256"] == row["source_png"]["rgb_sha256"], "Historical source RGB identity differs")
        conflicts = [hid for hid in history_ids if hist_by_id[hid].get("historical_role", hist_by_id[hid].get("source_role")) != "training"]
        geometry = point_metadata(row)
        result.append({"candidate_id": row["candidate_id"], "frame_id": row["frame_id"],
            "exact_current_candidate_ids": old_exact[point_key(row)], "floor_crop_current_candidate_ids": old_crop[crop_key(row)],
            "current_training_source_frame_overlap": True, "exact_historical_row_keys": hist_exact[point_key(row)],
            "floor_crop_historical_row_keys": hist_crop[crop_key(row)], "historical_source_frame_row_keys": history_ids,
            "unresolved_historical_role_row_keys": conflicts,
            "historical_roles": sorted({str(hist_by_id[hid].get("historical_role", hist_by_id[hid].get("source_role"))) for hid in history_ids}),
            "within_new_exact_candidate_ids": new_exact[point_key(row)],
            "new_exact_point_vs_current_pool": not old_exact[point_key(row)],
            "new_floor_crop_vs_current_pool": not old_crop[crop_key(row)],
            "new_exact_point_vs_current_and_history": not old_exact[point_key(row)] and not hist_exact[point_key(row)],
            "role_screen_eligible": not conflicts and geometry["point_model_input_eligible"],
            **geometry})
    return result


def analyze_populations(new_frames, new_candidates, old_frames, old_candidates, historical):
    """Pure metadata analysis; production caller validates seal and frozen bindings."""
    new_f, new_c, new_p, new_views = validate_population(new_frames, new_candidates)
    old_f, old_c, old_p, old_views = validate_population(old_frames, old_candidates)
    require(set(new_f) == set(old_f), "Old/new frame census differs")
    for fid in new_f:
        for key in ("block_id", "game_id", "source_video", "source_frame_index", "source_pts_ticks", "duration_ticks", "time_base", "source_png", "annotation", "kind", "valid_output_channel"):
            require(new_f[fid][key] == old_f[fid][key], "Paired accepted reference differs: " + key)
    novelty = novelty_rows(new_candidates, old_candidates, old_frames, historical)
    novel_by_id = {row["candidate_id"]: row for row in novelty}
    groups = category_rows(new_candidates, new_views)
    old_groups = category_rows(old_candidates, old_views)
    current_relative = category_rows(new_candidates, new_views, old_views)
    screened = {name: [row for row in items if novel_by_id[row["candidate_id"]]["role_screen_eligible"]]
                for name, items in groups.items()}
    useful_ids = {row["candidate_id"] for name in CONDITIONS for row in groups[name]}
    useful = [row for row in new_candidates if row["candidate_id"] in useful_ids]
    useful_new = [row for row in useful if novel_by_id[row["candidate_id"]]["new_exact_point_vs_current_and_history"]
                  and novel_by_id[row["candidate_id"]]["role_screen_eligible"]]
    raw_gate, screened_gate = coverage_gate(groups), coverage_gate(screened)
    paired = []
    for fid in new_f:
        old, new = old_views[fid], new_views[fid]
        paired.append({"frame_id": fid, "game_id": new_f[fid]["game_id"], "block_id": new_f[fid]["block_id"],
            "source_video_sha256": source_key(new_f[fid])[0], "source_frame_index": new_f[fid]["source_frame_index"],
            "kind": new_f[fid]["kind"], "current_cosine": old, "alternate_producer": new,
            "current_native_correct_retained": old["native_outcome"] == "correct" and new["native_outcome"] == "correct",
            "current_native_correct_lost": old["native_outcome"] == "correct" and new["native_outcome"] != "correct",
            "lost_native_but_new_pool_has_positive": old["native_outcome"] == "correct" and new["native_outcome"] != "correct" and bool(new["known_positive_ids"]),
            "current_native_wrong_or_missing_recovered": old["native_outcome"] in ("wrong", "missing") and new["native_outcome"] == "correct",
            "current_pool_positive_lost": bool(old["known_positive_ids"]) and not new["known_positive_ids"],
            "new_pool_positive_added": not old["known_positive_ids"] and bool(new["known_positive_ids"]),
            "current_weak_positive_frame_retains_any_positive": bool(old["weak_positive_ids"]) and bool(new["known_positive_ids"]),
            "current_weak_positive_frame_retains_weak_positive": bool(old["weak_positive_ids"]) and bool(new["weak_positive_ids"]),
            "both_pools_empty": not old["candidate_count"] and not new["candidate_count"]})
    flags = [key for key, value in paired[0].items() if type(value) is bool] if paired else []
    candidate_retention = []
    new_exact = defaultdict(list)
    for row in new_candidates:
        new_exact[point_key(row)].append(row["candidate_id"])
    for row in old_candidates:
        if row["target"] != 1:
            continue
        view = new_views[row["frame_id"]]
        candidate_retention.append({"old_candidate_id": row["candidate_id"], "frame_id": row["frame_id"],
            "native_or_weak": row["native_or_weak"], "exact_new_candidate_ids": new_exact[point_key(row)],
            "new_frame_any_positive_ids": view["known_positive_ids"], "new_frame_weak_positive_ids": view["weak_positive_ids"],
            "new_native_correct": view["native_outcome"] == "correct"})
    frame_groups = {"all_frames": new_frames,
                    "empty_new_pool": [new_f[fid] for fid, view in new_views.items() if not view["candidate_count"]],
                    "empty_old_pool": [old_f[fid] for fid, view in old_views.items() if not view["candidate_count"]]}
    frame_groups.update({"new_" + outcome: [new_f[fid] for fid, view in new_views.items() if view["native_outcome"] == outcome]
                        for outcome in ("correct", "wrong", "missing", "hidden_emission", "hidden_abstention", "masked_observed", "masked_missing")})
    frame_groups.update({flag: [new_f[row["frame_id"]] for row in paired if row[flag]] for flag in flags})
    reasons = []
    if not raw_gate["passed"]:
        reasons.append("producer_relative_required_category_coverage_failed")
    if not screened_gate["passed"]:
        reasons.append("conservative_role_or_point_input_screen_blocks_required_category_coverage")
    if not useful_new:
        reasons.append("no_role_compatible_useful_new_exact_point")
    decision = {"joint_transfer_design_eligible": not reasons, "blocking_reasons": reasons,
        "raw_producer_relative_coverage": raw_gate, "conservative_role_screened_coverage": screened_gate,
        "useful_new_role_compatible_exact_points": len({point_key(row) for row in useful_new}),
        "role_screen_policy": "Conservatively unresolved if any non-training historical role occurs on the same canonical source frame; also require original point-model in-source input eligibility. This does not invalidate any original accepted fit or change any historical role. Report raw coverage independently.",
        "novelty_policy": "At least one useful canonical exact point absent from both current candidate and historical point registries, outside unresolved historical frames. Floor-crop overlap remains a distinct descriptive measure.",
        "next_step": "Only a separately specified producer-transfer design is eligible; no training/adoption authorized." if not reasons
                     else "Stop this joint augmentation branch; preserve narrower findings without a silent weaker gate or sweep.",
        "training_run": False, "model_adopted": False, "threshold_selected": False}
    summary = {"frames": len(new_frames), "new_candidates": len(new_candidates), "old_candidates": len(old_candidates),
        "new_target_counts": dict(Counter(row["target_group"] for row in new_candidates)),
        "old_target_counts": dict(Counter(row["target_group"] for row in old_candidates)),
        "new_origin_counts": dict(Counter(row["native_or_weak"] for row in new_candidates)),
        "frame_kind_counts": dict(Counter(row["kind"] for row in new_frames)),
        "new_native_outcomes": dict(Counter(view["native_outcome"] for view in new_views.values())),
        "old_native_outcomes": dict(Counter(view["native_outcome"] for view in old_views.values())),
        "paired_native_transitions": dict(Counter(old_views[fid]["native_outcome"] + " -> " + new_views[fid]["native_outcome"] for fid in new_f)),
        "paired_counts": {flag: sum(row[flag] for row in paired) for flag in flags},
        "per_game": {game: {"frames": sum(row["game_id"] == game for row in new_frames),
            "new_native_outcomes": dict(Counter(new_views[row["frame_id"]]["native_outcome"] for row in new_frames if row["game_id"] == game)),
            "old_native_outcomes": dict(Counter(old_views[row["frame_id"]]["native_outcome"] for row in old_frames if row["game_id"] == game)),
            "paired_counts": {flag: sum(row[flag] for row in paired if row["game_id"] == game) for flag in flags}}
            for game in original.NBA_GAMES},
        "novelty_counts": {key: sum(bool(row[key]) for row in novelty) for key in (
            "exact_current_candidate_ids", "floor_crop_current_candidate_ids", "exact_historical_row_keys", "floor_crop_historical_row_keys",
            "historical_source_frame_row_keys", "unresolved_historical_role_row_keys", "new_exact_point_vs_current_pool",
            "new_floor_crop_vs_current_pool", "role_screen_eligible")},
        "historical_rows_preserved": len(historical), "historical_targets_promoted": 0,
        "current_cosine_recovery_view": {"wrong_or_missing_frames": frame_support([old_f[fid] for fid, view in old_views.items() if view["native_outcome"] in ("wrong", "missing")]),
            "alternate_weak_positive_on_current_wrong_or_missing": support(current_relative[CONDITIONS[2]], new_f),
            "alternate_weak_positive_on_current_wrong": support(current_relative["weak_positive_native_wrong"], new_f),
            "alternate_weak_positive_on_current_missing": support(current_relative["weak_positive_native_missing"], new_f),
            "cross_game_gate_applied": False, "meaning": "Current-policy failures are fixed by saved cosine choices. Producer-relative recoveries elsewhere do not fill this current-policy coverage gap."}}
    return {"summary": summary, "decision": decision, "paired_frames": paired, "novelty": novelty,
            "positive_retention": candidate_retention,
            "support": {"alternate_producer": {name: support(items, new_f) for name, items in groups.items()},
                        "current_cosine": {name: support(items, old_f) for name, items in old_groups.items()},
                        "conservative_role_screened": {name: support(items, new_f) for name, items in screened.items()},
                        "useful_population": support(useful, new_f), "useful_new_compatible_points": support(useful_new, new_f),
                        "frame_populations": {name: frame_support(items) for name, items in frame_groups.items()}}}


def assert_label_blind(value):
    forbidden = {"annotation", "target", "target_group", "distance_px", "localization_eligible",
                 "game_ball_identity_certainty", "recorded_uncertainty_radius_px", "accepted_classification"}
    if isinstance(value, dict):
        require(not forbidden.intersection(value), "Label field in sealed observable capture")
        for key, item in value.items():
            if key == "labels_used":
                require(item is False, "Capture reports label use")
            assert_label_blind(item)
    elif isinstance(value, list):
        for item in value:
            assert_label_blind(item)


def load_sealed_capture(root, capture_dir):
    """Check all label-blind pool bytes before opening the accepted package."""
    completed_path = capture_dir / "completed.json"
    complete = original.read_json(completed_path)
    require(complete["status"] == "completed_capture_no_fitting"
            and complete["extraction_sealed_before_label_assisted_coverage"] is True, "Capture is not sealed")
    require(complete["new_training_updates"] == complete["new_labels"] == complete["new_selector_runs"] == 0
            and complete["protected_access"] is False and complete["model_tensors_unchanged"] is True,
            "Capture scope changed")
    require(complete["new_forward_calls_attempted"] == complete["new_forward_calls_returned"] == 3137
            and complete["frames"] == 3179 and complete["counts"] == {
                "blocks": 21, "frames": 3179, "forward_calls": 3137, "imported_frames": 0,
                "parity_calls": 0, "optimizer_updates": 0}, "Capture call/frame budget differs")
    records, links = [], [original.binding(root, completed_path)]
    for link in complete["records"]:
        record_path = original.verify_binding(root, link)
        require(record_path.resolve().is_relative_to(capture_dir.resolve()), "Capture record outside this attempt")
        record = original.read_json(record_path)
        extraction = record["extraction"]
        require(extraction["labels_used"] is False and extraction["all_native_candidates_exact"] is True
                and extraction["all_mean_hashes_exact"] is True, "Extraction seal/parity missing")
        pool_path = original.verify_binding(root, extraction["pools"])
        require(pool_path.resolve().is_relative_to(capture_dir.resolve()), "Pool outside this capture")
        pools = rows(pool_path)
        ledger_path = original.verify_binding(root, record["contributor_ledger"])
        require(ledger_path.resolve().is_relative_to(capture_dir.resolve()), "Ledger outside this capture")
        ledger = rows(ledger_path)
        assert_label_blind(record["native_observations"])
        assert_label_blind(pools)
        assert_label_blind(ledger)
        require(record.get("imports", {}) == {}, "Unapproved donor import")
        observations = record["native_observations"]
        require(record["calls"] == len(observations) - 2 and len(observations) == len(ledger) == len(pools),
                "Block forward/frame ledger differs")
        for offset, (observation, item) in enumerate(zip(observations, ledger, strict=True)):
            starts = list(range(max(0, offset - 2), min(offset, len(observations) - 3) + 1))
            require(item["offset"] == offset and item["block_id"] == record["block_id"]
                    and item["source_frame_index"] == observation["source_frame_index"]
                    and item["source_pts_ticks"] == observation["source_pts_ticks"]
                    and item["mean_heatmap_sha256"] == observation["mean_heatmap_sha256"]
                    and item["count"] == observation["temporal_contributions"] == len(starts),
                    "Frame contributor ledger transport differs")
            require(item["all_finite"] is True and 0 <= item["minimum"] <= item["maximum"] <= 1,
                    "Nonfinite/out-of-range saved mean metadata")
            require([entry["triplet_start_offset"] for entry in item["contributors"]] == starts,
                    "Contributor reduction order differs")
            for entry, start in zip(item["contributors"], starts, strict=True):
                require(entry["channel"] == offset - start and entry["triplet_source_frame_indices"]
                        == [row["source_frame_index"] for row in observations[start:start + 3]],
                        "Contributor triplet/channel alignment differs")
                require(isinstance(entry["channel_sha256"], str) and len(entry["channel_sha256"]) == 64,
                        "Missing raw channel digest")
        records.append((record, pools))
        links.extend((link, extraction["pools"], record["contributor_ledger"]))
    require(sum(record["calls"] for record, _ in records) == 3137, "Block calls do not sum to total")
    # The accepted references are opened only after every candidate pool has passed.
    package_link = complete["package"]
    package = original.read_json(original.verify_binding(root, package_link))
    require(package_link["sha256"] == original.PACKAGE_SHA256, "Accepted package changed")
    links.append(package_link)
    blocks = [block for block in package["training_blocks"] if block["domain"] == "nba"]
    require(len(blocks) == len(records) == 21, "Capture block inventory changed")
    expected = {block["block_id"]: block for block in blocks}
    require(len({record["block_id"] for record, _ in records}) == 21 and {record["block_id"] for record, _ in records} == set(expected),
            "Capture block identities changed")
    frame_rows, candidate_rows = [], []
    for record, pools in records:
        block = expected[record["block_id"]]
        original.validate_source_block(block)
        require(len(pools) == len(record["native_observations"]) == len(block["frames"]), "Capture frame count differs")
        for frame, observation, pool in zip(block["frames"], record["native_observations"], pools, strict=True):
            fr, cr = original.make_frame_rows(block, frame, observation, pool, record["extraction"]["pools"])
            frame_rows.append(fr)
            candidate_rows.extend(cr)
    require(len(frame_rows) == 3179, "Capture accepted frame census changed")
    for link in [package["source_roles"], package["accepted_nba_inventory"], *package["reference_bindings"]]:
        original.verify_binding(root, link)
        links.append(link)
    roles = original.read_json(root / package["source_roles"]["path"])
    require(all(next(row["role"] for row in roles["game_roles"] if row["game_id"] == game) == "training"
                for game in original.NBA_GAMES), "Capture source role changed")
    return frame_rows, candidate_rows, links


def analyze_capture(root=ROOT, capture_dir=None, output_dir=None):
    root = Path(root).resolve()
    require(capture_dir is not None and output_dir is not None, "Explicit capture and analysis output required")
    capture_dir, output_dir = Path(capture_dir).resolve(), Path(output_dir).resolve()
    require(capture_dir.is_relative_to(root) and output_dir.is_relative_to(root), "Paths outside project")
    require(not output_dir.exists(), "Preserve existing analysis output")
    output_dir.mkdir(parents=True, exist_ok=False)
    original.write_json(output_dir / "started.json", {"at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "CPU postcapture target/census only; no images, models, fits or label changes."})
    try:
        new_frames, new_candidates, source_links = load_sealed_capture(root, capture_dir)
        old_prepared = original.read_json(root / PREPARATION / "prepared.json")
        old_links = old_prepared["common"]
        old_frames = [row for row in rows(original.verify_binding(root, old_links["frames"])) if row["domain"] == "nba"]
        old_candidates = [row for row in rows(original.verify_binding(root, old_links["candidates"])) if row["domain"] == "nba"]
        require(len(old_frames) == 3179 and len(old_candidates) == 18813, "Original NBA census changed")
        historical = rows(root / HISTORICAL)
        require(len(historical) == 60 and all(row["cohort"] == "historical" and row["target"] is None for row in historical), "Historical role inventory changed")
        external = original.read_json(root / EXTERNAL)
        require(external["external_stress_weak_positive_native_missing"]["frames"] == 21, "Original external stress history changed")
        for path in (PREPARATION + "/prepared.json", HISTORICAL, OLD_SCORES, EXTERNAL):
            source_links.append(original.binding(root, root / path))
        source_links.extend(old_links.values())
        result = analyze_populations(new_frames, new_candidates, old_frames, old_candidates, historical)
        current = result["summary"]["current_cosine_recovery_view"]["wrong_or_missing_frames"]
        require(current["frames"] == 4 and current["game_ids"] == ["0022400868"], "Saved current-cosine failure ceiling differs")
        require(len(result["support"]["current_cosine"]["all_weak_positive"]["candidate_ids"]) == 610, "Original weak-positive inventory changed")
        original.write_jsonl(output_dir / "frames.jsonl", new_frames)
        original.write_jsonl(output_dir / "candidates.jsonl", new_candidates)
        for name in ("paired_frames", "novelty", "positive_retention"):
            original.write_jsonl(output_dir / (name + ".jsonl"), result[name])
        for name in ("summary", "decision", "support"):
            original.write_json(output_dir / (name + ".json"), result[name])
        original.write_json(output_dir / "external_history_references.json", {
            "status": "unchanged_referenced_history_no_new_HOU_evaluation", "supplement": original.binding(root, root / EXTERNAL),
            "external_protected_missing_recovery_frames": 21,
            "current_main_pool_recovery_frames": external["current_main_pool_weak_positive_native_missing"]["frames"],
            "below_pool_extra_recovery_frames": external["stress_match_frames_without_current_main_pool_match"],
            "historical_rows": original.binding(root, root / HISTORICAL), "semantic_targets_promoted": 0})
        for link in source_links:
            original.verify_binding(root, link)
        artifacts = {path.name: original.binding(root, path) for path in sorted(output_dir.iterdir()) if path.name != "started.json"}
        complete = {"schema_version": "candidate_proposal_coverage_analysis/v0.1", "status": "completed_cpu_census_no_fitting",
            "sources": source_links, "implementation": original.binding(root, Path(__file__)), "outputs": artifacts,
            "frames": len(new_frames), "candidates": len(new_candidates), "decision": result["decision"],
            "new_model_calls": 0, "new_training_updates": 0, "new_labels": 0, "new_image_reads": 0,
            "original_scores_and_populations_preserved": True, "historical_semantics_promoted": False,
            "at_utc": datetime.now(timezone.utc).isoformat()}
        original.write_json(output_dir / "completed.json", complete)
        return complete
    except BaseException as error:
        original.write_json(output_dir / "failed.json", {"status": "failed_preserved_no_retry", "error_type": type(error).__name__,
            "error": str(error), "traceback": traceback.format_exc(), "at_utc": datetime.now(timezone.utc).isoformat()})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(analyze_capture(capture_dir=args.capture, output_dir=args.output), indent=2))


if __name__ == "__main__":
    main()
