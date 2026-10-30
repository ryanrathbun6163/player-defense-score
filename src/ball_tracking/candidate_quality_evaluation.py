"""CPU-only preparation and diagnostics for the proposed quality scorer.

This module consumes frozen producer records. It never creates an observation,
chooses a candidate, fits a threshold, imports Torch or reads image pixels.
Missing choices have no image score; zero is a separately named reject reference.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = "data/outputs/ball_tracking/candidate_quality_pilot_v0_1/evaluation"
POINT_CONFIG = "configs/ball_tracking/proposals/point_feature_comparison_v0_1.json"
CHANGE_CONFIG = "configs/ball_tracking/proposals/candidate_change_comparison_v0_1.json"
CHANGE_RESULT = "data/outputs/ball_tracking/candidate_change_comparison_v0_1/analysis_v0_1/completed.json"


def check(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def lines(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def bind(path, root=ROOT):
    path = Path(path)
    content = path.read_bytes()
    return {"path": path.relative_to(root).as_posix(), "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest()}


def bound(root, binding):
    path = root / binding["path"]
    check(bind(path, root) == {k: binding[k] for k in ("path", "bytes", "sha256")},
          f"Changed input: {binding['path']}")
    return path


def write_once(path, value, *, jsonl=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        if jsonl:
            for row in value:
                stream.write(json.dumps(row, allow_nan=False, separators=(",", ":")) + "\n")
        else:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")


def query_targets(queries, analysis):
    """Join actual query and frame producers; preserve unknown semantic states."""
    by_id = {q["query_id"]: q for q in queries}
    check(len(by_id) == len(queries), "Duplicate query identity")
    scores = {q["query_id"]: q for q in analysis["query_margin_rows"]}
    check(set(scores) == set(by_id), "Old margin/query coverage differs")
    output = {}
    frames = []
    for frame in analysis["joined_HOU_frame_diagnostics"]:
        category = frame["reference_category"]
        key = (frame["block_id"], frame["frame"])
        main_ids = []
        for candidate in frame["candidates"]:
            identity = candidate["query_id"]
            q = by_id[identity]
            check((q["block_id"], q["source_frame_index"]) == key and q["cohort"] == "HOU_main",
                  "Main query/frame provenance differs")
            check(candidate["id"] == q["candidate"]["candidate_index"], "Candidate index differs")
            check(candidate["in_bounds"] == q["candidate"]["in_source_bounds"], "Bounds differ")
            target = int(candidate["match"]) if category == "eligible" else 0 if category == "certain_hidden" else None
            output[identity] = {"query_id": identity, "cohort": "HOU_main", "block_id": key[0],
                "frame": key[1], "reference_category": category, "quality_target": target,
                "quality_target_semantics": "inclusive_10px_localization" if category == "eligible" else
                    "certain_hidden_rejection" if category == "certain_hidden" else "unknown",
                "native": candidate["native"], "is_native_selected": candidate["is_native_selected"],
                "native_correct_frame": frame["native_correct"], "in_bounds": candidate["in_bounds"],
                "localization_distance_px": candidate["localization_distance_px"],
                "baseline_features": candidate["features"], "missing": False,
                "fit_eligible": False, "threshold_selection_eligible": False}
            main_ids.append(identity)
        stress = frame["stress"]
        identity = stress["query_id"]
        q = by_id[identity]
        check((q["block_id"], q["source_frame_index"]) == key and q["cohort"] == "HOU_stress",
              "Stress query/frame provenance differs")
        check(stress["emitted"] == (q["input_id"] is not None), "Stress missing state differs")
        target = (int(stress["outcome"] == "matched") if category == "eligible" else
                  0 if category == "certain_hidden" else None) if stress["emitted"] else None
        output[identity] = {"query_id": identity, "cohort": "HOU_stress", "block_id": key[0],
            "frame": key[1], "reference_category": category, "quality_target": target,
            "quality_target_semantics": "missing_no_image_target" if not stress["emitted"] else
                "inclusive_10px_localization" if category == "eligible" else
                "certain_hidden_rejection" if category == "certain_hidden" else "unknown",
            "outcome": stress["outcome"], "tags": stress["tags"],
            "baseline_features": stress["features"], "missing": not stress["emitted"],
            "fit_eligible": False, "threshold_selection_eligible": False}
        frames.append({"block_id": key[0], "frame": key[1], "reference_category": category,
                       "native_correct": frame["native_correct"], "native_outcome": frame["native_outcome"],
                       "main_query_ids": main_ids, "stress_query_id": identity,
                       "stress_tags": stress["tags"]})
    historical = {r["query_id"]: r for r in analysis["historical_separate"]["cases"]}
    for q in queries:
        if q["cohort"] != "historical":
            continue
        h = historical[q["query_id"]]
        output[q["query_id"]] = {"query_id": q["query_id"], "cohort": "historical",
            "block_id": q["block_id"], "frame": q["source_frame_index"], "source_id": q["source_id"],
            "reference_category": "separate_historical_semantic_audit", "quality_target": None,
            "quality_target_semantics": "semantic_labels_are_not_automatic_localization_labels",
            "screen_role": h["screen_role"], "accepted_classification": h["accepted_classification"],
            "prior_AI_assessment_not_accepted": h["prior_AI_assessment_not_accepted"],
            "baseline_readouts": scores[q["query_id"]]["readouts"], "missing": False,
            "fit_eligible": False, "threshold_selection_eligible": False,
            "DET_method_choice_eligible": False}
    check(set(output) == set(by_id), "Target/query coverage differs")
    return [output[q["query_id"]] for q in queries], frames


def validate_logits(queries, rows):
    """Require exact emitted QUERY coverage, not merely crop/input coverage."""
    expected = {q["query_id"] for q in queries if q["input_id"] is not None}
    result = {}
    for row in rows:
        identity = row["query_id"]
        score = row["quality_logit"]
        check(identity not in result, "Duplicate predicted query")
        check(type(score) in (int, float) and math.isfinite(score), "Finite numeric logit required")
        result[identity] = float(score)
    check(set(result) == expected, "Prediction coverage differs: missing, extra or image-less query")
    return result


def choice_score(choice, logits):
    if choice["state"] == "missing":
        check(choice["center_xy_px"] is None, "Missing choice has coordinates")
        return {"image_quality_logit": None, "comparison_value": 0.0,
                "value_kind": "fixed_reject_reference_not_an_image"}
    check(choice["state"] == "observed" and choice["center_xy_px"] is not None,
          "Unknown old choice state")
    score = logits[choice["query_id"]]
    return {"image_quality_logit": score, "comparison_value": score, "value_kind": "image_quality_logit"}


def successful_choice(choice):
    if choice["reference_category"] == "eligible":
        return choice["outcome"] == "matched"
    if choice["reference_category"] == "certain_hidden":
        return choice["state"] == "missing"
    return None


def score_contrasts(comparisons, logits):
    output = []
    for row in comparisons:
        source, target = row["source_choice"], row["target_choice"]
        a, b = choice_score(source, logits), choice_score(target, logits)
        delta = b["comparison_value"] - a["comparison_value"]
        preference = "target" if delta > 0 else "source" if delta < 0 else "tie"
        good_a, good_b = successful_choice(source), successful_choice(target)
        comparable = good_a is not None and good_b is not None and good_a != good_b
        status = ("tie" if delta == 0 else "correct_side" if ((delta > 0) == good_b) else "wrong_side") if comparable else "not_discrimination_pair"
        output.append({k: row[k] for k in ("row_id", "contrast", "role", "block_id", "frame", "tags",
            "choice_state", "coordinate_agreement", "candidate_identity_agreement", "reference_category", "outcome_transition")} |
            {"source_quality": a, "target_quality": b, "delta_target_minus_source": delta,
             "preference": preference, "exactly_one_successful_old_choice": comparable,
             "correct_side_status": status, "baseline_features": row["features"],
             "new_choice_created": False})
    return output


def diagnostic_curve(targets, logits):
    """All observed breakpoints; scores strictly greater than boundary survive.

    This is descriptive evidence, never threshold selection. Candidate counts
    and certain-hidden frame counts are distinct; unknowns remain unknown.
    """
    selected = [r for r in targets if not r["missing"] and r["query_id"] in logits]
    counts = Counter()
    frame_counts = Counter()
    buckets = defaultdict(list)
    for row in selected:
        category = row["reference_category"]
        tags = ["all_candidates"]
        if category == "eligible":
            tags.append("matching" if row["quality_target"] == 1 else "localization_miss")
            if row.get("native") is False and row["quality_target"] == 1:
                tags.append("weak_matching")
            if row.get("is_native_selected") and row["quality_target"] == 1:
                tags.append("native_correct")
        elif category == "certain_hidden":
            tags.append("certain_hidden")
        else:
            tags.append("unknown")
        counts.update(tags)
        key = (row["block_id"], row["frame"])
        if category == "certain_hidden":
            frame_counts[key] += 1
        buckets[logits[row["query_id"]]].append((tags, key))
    names = ["all_candidates", "matching", "localization_miss", "weak_matching", "native_correct", "certain_hidden", "unknown"]
    def snapshot(boundary, kind):
        return {"threshold": boundary, "boundary_kind": kind, "strictly_greater_survives": True,
                "retained_candidates": {k: counts[k] for k in names},
                "certain_hidden_frames_with_survivors": len(frame_counts)}
    output = [snapshot(None, "below_all_scores")]
    for threshold in sorted(set(buckets) | {0.0}):
        for tags, key in buckets.get(threshold, []):
            counts.subtract(tags)
            if "certain_hidden" in tags:
                frame_counts[key] -= 1
                if not frame_counts[key]:
                    del frame_counts[key]
        output.append(snapshot(threshold, "fixed_zero_reference" if threshold == 0 else "observed_score"))
    return output


def score_frames(frames, targets, logits):
    """Keep every frame, ranking evidence and empty/unknown states separately."""
    lookup = {t["query_id"]: t for t in targets}
    output = []
    for frame in frames:
        candidates = [lookup[q] for q in frame["main_query_ids"]]
        matches = [t for t in candidates if t["quality_target"] == 1]
        misses = [t for t in candidates if t["quality_target"] == 0]
        ranking = {"status": "not_localization_eligible", "best_matching_logit": None,
                   "misses_strictly_above": None, "misses_tied": None}
        if frame["reference_category"] == "eligible":
            if not matches:
                ranking["status"] = "no_matching_candidate_in_pool"
            else:
                best = max(logits[t["query_id"]] for t in matches)
                above = sum(logits[t["query_id"]] > best for t in misses)
                tied = sum(logits[t["query_id"]] == best for t in misses)
                ranking = {"status": "beaten" if above else "tied_first" if tied else "strict_first",
                           "best_matching_logit": best, "misses_strictly_above": above, "misses_tied": tied}
        stress = lookup[frame["stress_query_id"]]
        scores = [{"query_id": t["query_id"], "quality_logit": logits[t["query_id"]],
                   "target": t["quality_target"], "native": t["native"],
                   "is_native_selected": t["is_native_selected"]} for t in candidates]
        output.append(dict(frame, main_scores=scores, ranking=ranking,
            pool_empty=not candidates, zero_reference_survivors=sum(r["quality_logit"] > 0 for r in scores),
            stress_image_logit=None if stress["missing"] else logits[stress["query_id"]],
            stress_missing=stress["missing"], new_choice_created=False))
    return output


def prepare(root=ROOT):
    root = Path(root)
    point_config = read(root / POINT_CONFIG)
    point_prep = read(bound(root, point_config["preparation"]))
    change_config = read(root / CHANGE_CONFIG)
    analysis = read(bound(root, change_config["inputs"]["point_analysis"]))
    change = read(root / CHANGE_RESULT)
    queries = lines(bound(root, point_prep["queries_registry"]))
    inputs = lines(bound(root, point_prep["input_registry"]))
    choices = lines(bound(root, change["choices"]))
    comparisons = lines(bound(root, change["comparisons"]))
    check(len(queries) == 11798 and len(inputs) == 10883 and len(choices) == 960 and len(comparisons) == 6720,
          "Frozen population differs")
    check(Counter(q["cohort"] for q in queries) == {"HOU_main": 10778, "HOU_stress": 960, "historical": 60}, "Cohort census differs")
    check(sum(q["input_id"] is None for q in queries) == 11, "Missing census differs")
    check({q["input_id"] for q in queries if q["input_id"] is not None} == {i["input_id"] for i in inputs}, "Input coverage differs")
    targets, frames = query_targets(queries, analysis)
    check(len(frames) == len({(f["block_id"], f["frame"]) for f in frames}) == 960, "Frame census differs")
    frame_keys = {(f["block_id"], f["frame"]) for f in frames}
    check({(r["block_id"], r["frame"]) for r in choices} == frame_keys, "Choice frame coverage differs")
    query_ids = {q["query_id"] for q in queries}
    for row in choices:
        check(len(row["choices"]) == 7, "Old arm coverage differs")
        for c in row["choices"].values():
            if c["state"] == "observed":
                check(c["query_id"] in query_ids, "Observed old choice lacks exact query")
    directory = root / OUTPUT
    write_once(directory / "query_targets.jsonl", targets, jsonl=True)
    write_once(directory / "frames.jsonl", frames, jsonl=True)
    manifest = {"schema_version": "candidate_quality_evaluation/v0.1", "status": "prepared_CPU_metadata_only_no_scores",
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "queries": len(queries), "emitted_queries": 11787,
        "missing_queries": 11, "unique_inputs": len(inputs), "cohorts": dict(Counter(q["cohort"] for q in queries)),
        "frames": len(frames), "old_choice_slots": 6720, "contrast_rows": len(comparisons),
        "frame_categories": dict(Counter(f["reference_category"] for f in frames)),
        "historical_source_counts": dict(Counter(q["source_id"] for q in queries if q["cohort"] == "historical")),
        "queries_registry": point_prep["queries_registry"], "input_registry": point_prep["input_registry"],
        "source_png_registry": point_prep["source_png_registry"], "choices": change["choices"], "comparisons": change["comparisons"],
        "query_targets": bind(directory / "query_targets.jsonl", root), "frame_registry": bind(directory / "frames.jsonl", root),
        "point_baselines": change_config["inputs"]["point_analysis"], "change_baselines": bind(root / CHANGE_RESULT, root),
        "source": bind(root / "src/ball_tracking/candidate_quality_evaluation.py", root),
        "pixel_bindings": "Original immutable source PNG bytes/RGB bindings reused; no pixel read or fresh pixel verification here.",
        "future_prediction_contract": "Exactly11787 emitted query IDs with finite quality_logit; missing11 have no score; crop dedup cannot conflate point weights.",
        "reject_reference": {"value": 0.0, "semantics": "Fixed logit reference, not a missing image feature; >0 survives, =0 tie."},
        "historical_scope": "All60 separate after frozen fit;18DET diagnostic only, never method/checkpoint/threshold choice; no AI assessment promoted.",
        "fit_eligible": False, "threshold_selection_eligible": False, "new_model_calls": 0,
        "new_labels": 0, "new_selections": 0, "protected_access": False}
    write_once(directory / "completed.json", manifest)
    return manifest


def load_prepared(root=ROOT):
    root = Path(root)
    manifest = read(root / OUTPUT / "completed.json")
    return (manifest, lines(bound(root, manifest["queries_registry"])), lines(bound(root, manifest["query_targets"])),
            lines(bound(root, manifest["frame_registry"])), lines(bound(root, manifest["comparisons"])))


def analyze(root, prediction_path):
    root = Path(root)
    manifest, queries, targets, frames, comparisons = load_prepared(root)
    logits = validate_logits(queries, lines(prediction_path))
    contrasted = score_contrasts(comparisons, logits)
    output = Path(prediction_path).parent / "quality_evaluation"
    write_once(output / "contrasts.jsonl", contrasted, jsonl=True)
    frame_rows = score_frames(frames, targets, logits)
    write_once(output / "frames.jsonl", frame_rows, jsonl=True)
    curves = {}
    for cohort in ("HOU_main", "HOU_stress"):
        selected = [t for t in targets if t["cohort"] == cohort]
        curve = diagnostic_curve(selected, logits)
        write_once(output / (cohort + "_curve.jsonl"), curve, jsonl=True)
        curves[cohort] = {"all_breakpoints": bind(output / (cohort + "_curve.jsonl"), root),
                          "at_zero": next(r for r in curve if r["boundary_kind"] == "fixed_zero_reference")}
    episodes = {}
    for block in sorted({f["block_id"] for f in frames}):
        selected = [t for t in targets if t["cohort"] == "HOU_main" and t["block_id"] == block]
        curve = diagnostic_curve(selected, logits)
        episode_frames = [f for f in frame_rows if f["block_id"] == block]
        write_once(output / (block + "_curve.jsonl"), curve, jsonl=True)
        episodes[block] = {"frames": len(episode_frames),
            "reference_categories": dict(Counter(f["reference_category"] for f in episode_frames)),
            "ranking_status": dict(Counter(f["ranking"]["status"] for f in episode_frames)),
            "pool_empty_frames": sum(f["pool_empty"] for f in episode_frames),
            "all_breakpoints": bind(output / (block + "_curve.jsonl"), root),
            "at_zero": next(r for r in curve if r["boundary_kind"] == "fixed_zero_reference")}
    historical = [dict(t, quality_logit=logits[t["query_id"]]) for t in targets if t["cohort"] == "historical"]
    write_once(output / "historical.jsonl", historical, jsonl=True)
    summaries = {}
    for contrast in sorted({r["contrast"] for r in contrasted}):
        selected = [r for r in contrasted if r["contrast"] == contrast]
        summaries[contrast] = {"rows": len(selected), "choice_states": dict(Counter(r["choice_state"] for r in selected)),
            "correct_side_status": dict(Counter(r["correct_side_status"] for r in selected)),
            "reference_categories": dict(Counter(r["reference_category"] for r in selected)),
            "overlapping_tags": {tag: dict(Counter(r["correct_side_status"] for r in selected if tag in r["tags"]))
                                 for tag in sorted({t for r in selected for t in r["tags"]})}}
    result = {"status": "completed_offline_score_diagnostics_no_new_choices", "preparation": bind(root / OUTPUT / "completed.json", root),
        "predictions": bind(Path(prediction_path), root), "queries": len(queries), "scored_queries": len(logits),
        "missing_queries_without_image_score": 11, "frames": len(frames), "contrasts": summaries, "curves": curves,
        "episodes": episodes, "frame_rows": bind(output / "frames.jsonl", root),
        "contrast_rows": bind(output / "contrasts.jsonl", root), "historical": bind(output / "historical.jsonl", root),
        "new_selections": 0, "threshold_selected": False, "new_labels": 0, "protected_access": False}
    write_once(output / "completed.json", result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--predictions", type=Path)
    args = parser.parse_args()
    check(args.prepare != bool(args.predictions), "Choose --prepare or --predictions")
    result = prepare() if args.prepare else analyze(ROOT, args.predictions.resolve())
    print(json.dumps({k: result[k] for k in ("status", "queries", "frames")}))


if __name__ == "__main__":
    main()
