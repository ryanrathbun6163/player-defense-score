"""Read the accepted saved-score joins and enforce nested base/gate identities."""
from collections import Counter, defaultdict
import json
import math
from pathlib import Path

STUDY = "data/outputs/ball_tracking/saved_score_failure_study_v0_1/attempt_003"
PILOT = "data/outputs/ball_tracking/candidate_quality_pilot_v0_1"
GAMES = {"CHI": "0022400868", "DEN": "0022400866", "SAC": "0022500829"}
OLD_FITS = {"CHI": "leave_chi_out", "DEN": "leave_den_out", "SAC": "leave_sac_out"}
COUNTS = {"CHI": 5935, "DEN": 5790, "SAC": 7088}
MAIN_COHORTS = {"package", "HOU_main"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def rows(path):
    with Path(path).open(encoding="utf-8-sig") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def unique(items, key, name):
    result = {}
    for row in items:
        ident = row[key]
        require(ident not in result, name + ": duplicate " + str(ident))
        result[ident] = row
    return result


def observable(row):
    """Whitelist: references and annotation metadata cannot enter features."""
    names = ("row_key", "frame_key", "fit", "cohort", "logit", "center_xy_px",
             "native_score", "component_pixels", "padding_pixels", "native_or_weak")
    return {key: row.get(key) for key in names}


def pool_index(candidates):
    pools = defaultdict(list)
    for row in candidates:
        if row["cohort"] in MAIN_COHORTS:
            require(row["logit"] is not None, "Main-pool score unavailable")
            pools[row["frame_key"]].append(observable(row))
    return dict(pools)


def load_saved(root, spec):
    """Caller verifies frozen bindings before this record-only adapter."""
    root = Path(root)
    base = root / STUDY
    all_frames = list(rows(base / "joined_frames.jsonl"))
    require(len(all_frames) == 7468, "Old complete frame inventory changed")
    frames = [dict(r) for r in all_frames if r["context"] != "nba_in_sample"]
    for row in frames:
        row.pop("source", None)
    require(len(frames) == 4289, "Evaluation frame count differs")
    candidates = []
    old_count = 0
    for original in rows(base / "joined_candidate_contexts.jsonl"):
        old_count += 1
        if original["context"] == "nba_in_sample":
            continue
        row = {key: value for key, value in original.items() if key != "source"}
        source = original["source"]
        coordinate_source = source["candidate"] if row["cohort"] == "package" else source["query"]
        row["center_xy_px"] = coordinate_source["center_xy_px"]
        row["original_row_key"] = row["row_key"]
        row["source_record"] = {"path": STUDY + "/joined_candidate_contexts.jsonl",
                                "row_key": row["row_key"]}
        if row["cohort"] == "historical":
            row["historical_role"] = source["query"]["source_role"]
            row["original_semantic_target"] = source["target"].get("quality_target")
            row["historical_source"] = source.get("historical")
        else:
            row["historical_role"] = None
        row["out_of_fitting_schema"] = row["cohort"] in ("historical", "HOU_stress")
        candidates.append(row)
    require(old_count == 50243 and len(candidates) == 31430, "Candidate slots changed")
    require(sum(r["logit"] is None for r in candidates) == 11, "Missing-score slots changed")
    require(Counter(r["cohort"] for r in candidates) == {
        "package": 19632, "HOU_main": 10778, "HOU_stress": 960, "historical": 60}, "Cohort loss")
    by_key = unique(candidates, "row_key", "Saved evaluation candidates")
    frame_index = unique(frames, "frame_key", "Saved evaluation frames")
    for row in candidates:
        if row["frame_key"] is not None:
            require(row["frame_key"] in frame_index, "Candidate parent frame absent")
        require(row["logit"] is None or
                (isinstance(row["logit"], (int, float)) and math.isfinite(row["logit"])), "Bad saved score")
    nba = [r for r in candidates if r["context"] == "nba_out_of_fold"]
    require(len(nba) == 18813, "NBA population changed")
    weights = {}
    for gate in ("outer_CHI", "outer_DEN", "outer_SAC", "final_all_NBA"):
        fit = OLD_FITS[gate.removeprefix("outer_")] if gate.startswith("outer_") else "all_nba"
        path = root / PILOT / "preparation/fits" / fit / "weights.jsonl"
        weights[gate] = unique(list(rows(path)), "candidate_id", "Gate weights")
        included = set(GAMES.values()) - ({GAMES[gate.removeprefix("outer_")]} if gate.startswith("outer_") else set())
        expected = {r["candidate_id"] for r in nba if r["game_id"] in included and r["target"] is not None}
        require(set(weights[gate]) == expected, "Gate fitting membership differs: " + gate)
        require(math.isclose(math.fsum(r["objective_weight"] for r in weights[gate].values()), 1.0, abs_tol=1e-12),
                "Gate objective mass differs")
    controls = {}
    for name in ("controls", "case_views", "summary", "missingness"):
        controls[name] = json.loads((base / (name + ".json")).read_text(encoding="utf-8"))
    source_choices = list(rows(base / "source_choices.jsonl"))
    contrasts = list(rows(base / "contrast_views.jsonl"))
    require(len(source_choices) == 6720 and len(contrasts) == 6720, "Old case/control rows lost")
    return {"frames": frames, "candidates": candidates, "nba_candidates": nba, "weights": weights,
            "pools": pool_index(candidates), "by_key": by_key, "controls": controls,
            "source_choices": source_choices, "contrasts": contrasts}


def attach_cross_scores(nba_candidates, scores):
    """Attach NEW single-game scores, rejecting any source-game leakage."""
    metadata = unique(nba_candidates, "candidate_id", "NBA metadata")
    indexed = {}
    for score in scores:
        fit, cid = score["fit"], score["candidate_id"]
        require(fit in {name + "_only" for name in GAMES}, "Unknown new base fit")
        require(cid in metadata, "Unknown scored candidate")
        old = metadata[cid]
        source_name = fit.removesuffix("_only")
        require(old["game_id"] != GAMES[source_name], "Single-game score includes its fitting game")
        logit = score["quality_logit"]
        require(isinstance(logit, (int, float)) and not isinstance(logit, bool) and math.isfinite(logit),
                "Nonfinite/missing new score")
        if "game_id" in score:
            require(score["game_id"] == old["game_id"], "Cross-score game transport differs")
        if "frame_id" in score:
            require(score["frame_id"] == old["frame_id"], "Cross-score frame transport differs")
        key = fit + "|" + cid
        require(key not in indexed, "Duplicate cross-score key")
        indexed[key] = {**old, "fit": fit, "row_key": key,
                        "frame_key": fit + "|" + old["frame_id"], "logit": logit,
                        "source_record": {"new_fit": fit, "candidate_id": cid},
                        "old_metadata_row_key": old["row_key"]}
    expected = {fit + "_only|" + cid for fit, gid in GAMES.items()
                for cid, row in metadata.items() if row["game_id"] != gid}
    require(set(indexed) == expected, "New cross-score population is incomplete")
    return list(indexed.values())


def gate_training_rows(gate, saved, cross):
    if gate == "final_all_NBA":
        selected = saved["nba_candidates"]
    else:
        held = gate.removeprefix("outer_")
        require(held in GAMES, "Unknown outer gate")
        selected = [r for r in cross if r["game_id"] != GAMES[held]
                    and r["fit"].removesuffix("_only") != held]
        for row in selected:
            require(row["game_id"] != GAMES[row["fit"].removesuffix("_only")], "Training score is in-sample")
        require({r["game_id"] for r in selected} == set(GAMES.values()) - {GAMES[held]},
                "Outer training sources differ")
    ids = [r["candidate_id"] for r in selected]
    require(len(ids) == len(set(ids)), "Candidate has multiple base sources in gate fit")
    fitting = [r for r in selected if r["candidate_id"] in saved["weights"][gate]]
    require({r["candidate_id"] for r in fitting} == set(saved["weights"][gate]), "Fit membership lost")
    require(all(r["target"] in (0, 1) for r in fitting), "Unknown fitting target")
    return selected, fitting


def gate_for_evaluation(row):
    if row["context"] == "nba_out_of_fold":
        return "outer_" + next(name for name, gid in GAMES.items() if gid == row["game_id"])
    return "final_all_NBA"
