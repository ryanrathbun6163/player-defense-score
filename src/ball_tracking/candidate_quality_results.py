"""CPU-only reporting for future frozen candidate-quality package scores.

This consumes score files, not a model. Evaluation uses the unchanged inclusive
ten-pixel criterion even for candidates masked from fitting by the uncertainty
band. Strictly positive logits survive the fixed zero reference; equality is
reported as a tie. Diagnostic frontiers select no policy.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timezone
import math
from pathlib import Path

from .candidate_quality_data import (
    FIT_GAMES, NBA_GAMES, OUTPUT as PREPARATION, ROOT, binding, read_json,
    require, verify_binding, write_json, write_jsonl,
)
import json


PILOT = Path("data/outputs/ball_tracking/candidate_quality_pilot_v0_1")
ATTEMPT = PILOT / "attempt_001"
RESULTS = ATTEMPT / "package_analysis"
HELD_FIT = {game: name for name, games in FIT_GAMES.items() if name != "all_nba"
            for game in NBA_GAMES if game not in games}


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]


def validate_scores(candidates: list[dict], fit_scores: dict[str, list[dict]]) -> dict[str, dict[str, float]]:
    require(set(fit_scores) == set(FIT_GAMES), "Exactly four frozen score populations required")
    require(len({c["candidate_id"] for c in candidates}) == len(candidates), "Duplicate candidate IDs")
    result = {}
    for name, rows in fit_scores.items():
        expected = {c["candidate_id"] for c in candidates
                    if name == "all_nba" or (c["domain"] == "nba" and c["game_id"] not in FIT_GAMES[name])}
        scored = {}
        for row in rows:
            identity, value = row["candidate_id"], row["quality_logit"]
            require(identity not in scored, "Duplicate score identity")
            require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value),
                    "Non-finite or nonnumeric quality logit")
            scored[identity] = float(value)
        require(set(scored) == expected, "Missing, extra or wrong-game scores: " + name)
        result[name] = scored
    return result


def evaluation_category(frame: dict, candidate: dict) -> str:
    """Recompute evaluation labels independently of the training target/mask."""
    kind = frame["kind"]
    if kind == "hidden":
        return "certain_hidden"
    if kind == "masked":
        return "masked_unknown"
    require(kind == "positive", "Unexpected frame kind")
    center = frame["annotation"]["geometry"]["center_xy_px"]
    x, y = candidate["center_xy_px"]
    source = frame["source_video"]
    inside = 0 <= x < source["width_px"] and 0 <= y < source["height_px"]
    return "eligible_match" if inside and math.hypot(x - center[0], y - center[1]) <= 10 else "eligible_miss"


def frame_metrics(frame: dict, candidates: list[dict], scores: dict[str, float]) -> tuple[dict, dict]:
    """Counts retain every frame, including empty hidden and masked frames."""
    counters = Counter(frames=1)
    counters["frames:" + frame["kind"]] += 1
    counters["frames:empty_pool"] += not candidates
    counters["candidates"] += len(candidates)
    evaluated = [(c, evaluation_category(frame, c), scores[c["candidate_id"]]) for c in candidates]
    for candidate, category, score in evaluated:
        counters["candidates:" + category] += 1
        for relation, condition in (("retained_zero", score > 0), ("below_zero", score < 0), ("tie_zero", score == 0)):
            counters["candidates:" + relation] += condition
            counters["candidates:" + category + ":" + relation] += condition
        if candidate["target"] is None:
            counters["candidates:fitting_unknown"] += 1
            counters["candidates:fitting_unknown:retained_zero"] += score > 0
            counters["candidates:fitting_unknown:below_zero"] += score < 0
            counters["candidates:fitting_unknown:tie_zero"] += score == 0
    counters["frames:any_survivor_zero"] += any(score > 0 for _, _, score in evaluated)
    counters["frames:any_tie_zero"] += any(score == 0 for _, _, score in evaluated)
    matches = [(c, value) for c, category, value in evaluated if category == "eligible_match"]
    misses = [(c, value) for c, category, value in evaluated if category == "eligible_miss"]
    weak_matches = [(c, value) for c, value in matches if c["native_or_weak"] == "weak"]
    counters["frames:any_pool_match"] += bool(matches)
    counters["frames:any_match_retained_zero"] += any(value > 0 for _, value in matches)
    counters["frames:any_match_tie_zero"] += any(value == 0 for _, value in matches)
    counters["frames:weak_match"] += bool(weak_matches)
    counters["frames:weak_match_retained_zero"] += any(value > 0 for _, value in weak_matches)
    counters["frames:weak_match_tie_zero"] += any(value == 0 for _, value in weak_matches)
    counters["candidates:weak_match"] += len(weak_matches)
    counters["candidates:weak_match_retained_zero"] += sum(value > 0 for _, value in weak_matches)
    counters["candidates:weak_match_tie_zero"] += sum(value == 0 for _, value in weak_matches)
    if frame["kind"] == "positive":
        if not matches:
            ordering = "no_pool_match"
        elif not misses or max(value for _, value in matches) > max(value for _, value in misses):
            ordering = "match_strictly_first"
        elif max(value for _, value in matches) == max(value for _, value in misses):
            ordering = "match_miss_top_tie"
        else:
            ordering = "miss_strictly_first"
        counters["frames:ranking:" + ordering] += 1
    else:
        ordering = "unscored_reference"
    selected_index = frame["native_selected_candidate_index"]
    selected = next(((c, category, value) for c, category, value in evaluated
                     if c["native_or_weak"] == "native" and c["candidate_index"] == selected_index), None)
    require((selected is None) == (frame["native_center_xy_px"] is None), "Native selection transport mismatch")
    if frame["kind"] == "positive":
        native = "missing" if selected is None else "correct" if selected[1] == "eligible_match" else "wrong"
        counters["frames:native_" + native] += 1
        if selected is not None:
            counters["frames:native_" + native + ":retained_zero"] += selected[2] > 0
            counters["frames:native_" + native + ":rejected_zero"] += selected[2] < 0
            counters["frames:native_" + native + ":tie_zero"] += selected[2] == 0
        if weak_matches:
            counters["frames:weak_match:native_" + native] += 1
            counters["frames:weak_match_retained_zero:native_" + native] += any(v > 0 for _, v in weak_matches)
            counters["frames:weak_match_tie_zero:native_" + native] += any(v == 0 for _, v in weak_matches)
    else:
        native = "emitted" if selected is not None else "missing"
        counters["frames:" + frame["kind"] + ":native_" + native] += 1
        if frame["kind"] == "hidden":
            counters["frames:hidden:any_survivor_zero"] += any(value > 0 for _, _, value in evaluated)
            counters["frames:hidden:any_tie_zero"] += any(value == 0 for _, _, value in evaluated)
            counters["frames:hidden:native_survivor_zero"] += selected is not None and selected[2] > 0
            counters["frames:hidden:native_tie_zero"] += selected is not None and selected[2] == 0
    extrema = {
        "native_correct_logit": selected[2] if frame["kind"] == "positive" and native == "correct" else None,
        "hidden_max_logit": max((v for _, _, v in evaluated), default=None) if frame["kind"] == "hidden" else None,
        "weak_match_max_logit": max((v for _, v in weak_matches), default=None),
        "any_match_max_logit": max((v for _, v in matches), default=None),
    }
    return dict(counters), {"ranking": ordering, "native_outcome": native,
                            "native_selected_logit": selected[2] if selected is not None else None, **extrema}


def origin_metrics(frame: dict, candidates: list[dict], scores: dict[str, float], origin: str) -> dict:
    subset = [c for c in candidates if c["native_or_weak"] == origin]
    counters = Counter(frames=1, candidates=len(subset))
    counters["frames:" + frame["kind"]] += 1
    counters["frames:with_candidates"] += bool(subset)
    counters["frames:any_survivor_zero"] += any(scores[c["candidate_id"]] > 0 for c in subset)
    counters["frames:any_tie_zero"] += any(scores[c["candidate_id"]] == 0 for c in subset)
    categories = [(c, evaluation_category(frame, c)) for c in subset]
    counters["frames:with_match"] += any(category == "eligible_match" for _, category in categories)
    counters["frames:match_survivor_zero"] += any(category == "eligible_match" and scores[c["candidate_id"]] > 0
                                                for c, category in categories)
    counters["frames:match_tie_zero"] += any(category == "eligible_match" and scores[c["candidate_id"]] == 0
                                           for c, category in categories)
    if frame["kind"] == "hidden":
        counters["frames:hidden:survivor_zero"] += any(scores[c["candidate_id"]] > 0 for c in subset)
        counters["frames:hidden:tie_zero"] += any(scores[c["candidate_id"]] == 0 for c in subset)
    for candidate, category in categories:
        counters["candidates:" + category] += 1
        score = scores[candidate["candidate_id"]]
        for relation, condition in (("retained_zero", score > 0), ("below_zero", score < 0), ("tie_zero", score == 0)):
            counters["candidates:" + relation] += condition
            counters["candidates:" + category + ":" + relation] += condition
    return dict(counters)


def diagnostic_frontier(extrema: list[dict], hidden_frames: int) -> dict:
    """Exact frame-level tradeoff breakpoints; no threshold is chosen or fitted."""
    names = ("native_correct_logit", "hidden_max_logit", "weak_match_max_logit", "any_match_max_logit")
    series = {name: sorted(row[name] for row in extrema if row[name] is not None) for name in names}
    cuts = sorted(set(value for values in series.values() for value in values) | {0.0})
    labels = {"native_correct_logit": "native_correct_retained", "hidden_max_logit": "hidden_frames_with_survivor",
              "weak_match_max_logit": "weak_match_frames_retained", "any_match_max_logit": "any_match_frames_retained"}
    curve = [{"cutoff": None, "comparison": "accept_all", **{labels[n]: len(s) for n, s in series.items()}}]
    for cut in cuts:
        curve.append({"cutoff": cut, "comparison": "quality_logit > cutoff",
                      "boundary_kind": "fixed_zero_reference" if cut == 0 else "observed_score",
                      **{labels[n]: len(s) - bisect_right(s, cut) for n, s in series.items()}})
    return {"certain_hidden_frame_denominator": hidden_frames,
            "hidden_empty_pool_frames": hidden_frames - len(series["hidden_max_logit"]),
            "native_correct_denominator": len(series["native_correct_logit"]),
            "weak_match_frame_denominator": len(series["weak_match_max_logit"]),
            "diagnostic_only_no_selected_threshold": True, "rows": curve}


def analyze_scores(frames: list[dict], candidates: list[dict], fit_scores: dict[str, list[dict]]) -> tuple[list[dict], dict]:
    """Pure CPU result assembly; usable with declared synthetic scores in tests."""
    scores = validate_scores(candidates, fit_scores)
    by_id = {c["candidate_id"]: c for c in candidates}
    require(len({f["frame_id"] for f in frames}) == len(frames), "Duplicate frame IDs")
    require([i for f in frames for i in f["candidate_ids"]] == [c["candidate_id"] for c in candidates],
            "Complete candidate/frame ordering differs")
    summaries = {}
    extrema = defaultdict(list)
    for name in ("nba_in_sample", "nba_out_of_fold", "nfhs_secondary"):
        summaries[name] = {"counts": Counter(), "groups": {key: defaultdict(Counter) for key in
                          ("game", "block", "visibility", "kind", "uncertainty", "origin")}}
    frame_rows = []
    for frame in frames:
        members = [by_id[i] for i in frame["candidate_ids"]]
        require(all(c["frame_id"] == frame["frame_id"] and c["game_id"] == frame["game_id"]
                    and c["domain"] == frame["domain"] for c in members), "Candidate source/frame join mismatch")
        is_nba = frame["domain"] == "nba"
        require(is_nba or frame["domain"] == "nfhs", "Unexpected source domain")
        contexts = {"nba_in_sample" if is_nba else "nfhs_secondary": "all_nba"}
        if is_nba:
            require(frame["game_id"] in HELD_FIT, "NBA source lacks held fit")
            contexts["nba_out_of_fold"] = HELD_FIT[frame["game_id"]]
        detail = {}
        geometry = frame["annotation"].get("geometry")
        uncertainty = None if geometry is None else geometry.get("uncertainty_radius_px")
        groups = {"game": frame["game_id"], "block": frame["block_id"],
                  "visibility": frame["annotation"]["visibility"], "kind": frame["kind"],
                  "uncertainty": "unknown" if uncertainty is None else str(uncertainty)}
        for context, fit in contexts.items():
            counts, diagnostics = frame_metrics(frame, members, scores[fit])
            detail[context] = {"fit": fit, "counts": counts, **diagnostics}
            summaries[context]["counts"].update(counts)
            extrema[context].append(diagnostics)
            for key, value in groups.items():
                summaries[context]["groups"][key][value].update(counts)
            for origin in ("native", "weak"):
                summaries[context]["groups"]["origin"][origin].update(origin_metrics(frame, members, scores[fit], origin))
        frame_rows.append({"frame": frame, "scoring_contexts": detail,
                           "candidate_scores": [{"candidate_id": c["candidate_id"], "candidate_index": c["candidate_index"],
                                                 "native_or_weak": c["native_or_weak"], "center_xy_px": c["center_xy_px"],
                                                 "fitting_target": c["target"], "fitting_target_group": c["target_group"],
                                                 "distance_px": c["distance_px"],
                                                 "evaluation_category": evaluation_category(frame, c),
                                                 "all_nba_logit": scores["all_nba"][c["candidate_id"]],
                                                 "held_out_logit": scores[HELD_FIT[frame["game_id"]]][c["candidate_id"]] if is_nba else None}
                                                for c in members]})
    for context, result in summaries.items():
        result["counts"] = dict(result["counts"])
        result["groups"] = {key: {group: dict(counts) for group, counts in values.items()}
                            for key, values in result["groups"].items()}
        result["frontier"] = diagnostic_frontier(extrema[context], result["counts"].get("frames:hidden", 0))
    gaps = {}
    for game in NBA_GAMES:
        inside = summaries["nba_in_sample"]["groups"]["game"].get(game, {})
        outside = summaries["nba_out_of_fold"]["groups"]["game"].get(game, {})
        gaps[game] = {"in_sample": inside, "out_of_fold": outside,
                      "out_of_fold_minus_in_sample": {k: outside.get(k, 0) - inside.get(k, 0)
                                                       for k in set(inside) | set(outside)}}
    summary = {"schema_version": "candidate_quality_package_results/v0.1", "frames": len(frames),
               "candidates": len(candidates), "contexts": summaries, "paired_game_comparisons": gaps,
               "fixed_reject_reference": "quality_logit >0 survives; =0 is a separately reported tie; <0 is below the reject reference. No learned threshold.",
               "evaluation": "original eligibility, source bounds and inclusive10; boundary fitting masks remain misses",
               "limitations": ["OOF means scorer-held game only; cosine-nine backbone saw all NBA training games.",
                               "NBA in-sample and OOF share the same source frames, not independent samples.",
                               "NFHS is secondary and excluded from this scorer's fitting, but was seen by cosine nine.",
                               "Empty frames remain denominators; masked rows have no correctness target.",
                               "Curves are descriptive, not a selected policy, calibration guarantee or new trajectory."]}
    return frame_rows, summary


def analyze(root: Path = ROOT) -> dict:
    root = root.resolve()
    destination = root / RESULTS
    require(not destination.exists(), "Existing result must be preserved")
    prepared_path = root / PREPARATION / "prepared.json"
    prepared = read_json(prepared_path)
    frames = read_rows(verify_binding(root, prepared["common"]["frames"]))
    candidates = read_rows(verify_binding(root, prepared["common"]["candidates"]))
    completed_path = root / ATTEMPT / "completed.json"
    completed = read_json(completed_path)
    require(completed["status"] == "completed_fixed_pilot_no_selector_no_adoption"
            and completed["protected_access"] is False and completed["new_labels"] == 0
            and completed["new_selector_runs"] == 0 and completed["model_adopted"] is False,
            "Pilot not a complete permitted score producer")
    require(not (root / ATTEMPT / "failed.json").exists(), "Failed attempt cannot be analyzed as complete")
    fit_results = {r["fit"]: r for r in completed["fits"]}
    require(len(completed["fits"]) == len(fit_results) == len(FIT_GAMES) and set(fit_results) == set(FIT_GAMES),
            "Fit completion population differs")
    score_rows, score_bindings = {}, {}
    for name in FIT_GAMES:
        result = fit_results[name]
        require(result["frozen_tensors_unchanged"] is True, "Frozen tensors changed")
        require(result["fit_manifest"] == prepared["fit_manifests"][name], "Fit source membership binding differs")
        manifest = read_json(verify_binding(root, result["fit_manifest"]))
        require(manifest["fit_game_ids"] == list(FIT_GAMES[name]), "Fit game membership differs")
        require(result["steps"] == manifest["total_training_steps"], "Fit incomplete")
        matches = [link for link in result["scores"] if link["path"] == (ATTEMPT / name / "package_scores.jsonl").as_posix()]
        require(len(matches) == 1, "Exact package score binding required")
        score_rows[name] = read_rows(verify_binding(root, matches[0]))
        score_bindings[name] = matches[0]
    all_frames, summary = analyze_scores(frames, candidates, score_rows)
    require(len(all_frames) == 3329 and summary["candidates"] == 19632, "Full package population differs")
    summary["inputs"] = {"prepared": binding(root, prepared_path), "completed": binding(root, completed_path),
                         "common": prepared["common"], "scores": score_bindings,
                         "implementation": binding(root, Path(__file__))}
    summary["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    destination.mkdir(exist_ok=False)
    write_jsonl(destination / "frames.jsonl", all_frames)
    summary["frame_output"] = binding(root, destination / "frames.jsonl")
    write_json(destination / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analyze", action="store_true", required=True)
    parser.parse_args()
    result = analyze()
    print(json.dumps({"status": "package_scores_analyzed_no_new_model_calls", "frames": result["frames"],
                      "candidates": result["candidates"]}))


if __name__ == "__main__":
    main()
