"""Reference-assisted comparison of sealed fixed DINO readouts; no new tracks."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path

import numpy as np

from . import candidate_response_analysis as response
from . import point_feature_inference as producer
from .weak_response_capture import bind, bound, read, write_once, HOU

ROOT = Path(__file__).resolve().parents[2]
READOUTS = ("cls", "point")
FEATURES = (*READOUTS, "peak", "native_mass")
STRATA = ("complete_source_crop", "padded_source_crop")
check = response.check


def reconstruct(record, item, queries, witness):
    """Consume a producer receipt and raw witnesses without loading any model."""
    check(record["status"] == "completed" and record["input"] == item,
          "Input receipt identity differs")
    check(record["same_pass_CLS_exact"] is True and record["sequence_shape"] == [1, 257, 384]
          and record["sequence_indices"] == [120, 121, 136, 137], "Sequence contract differs")
    cls, tokens, indices = (witness[k] for k in ("cls", "tokens", "sequence_indices"))
    check(cls.shape == (384,) and tokens.shape == (4, 384)
          and cls.dtype == tokens.dtype == np.float32 and indices.dtype == np.int64
          and np.array_equal(indices, producer.TOKEN_INDICES)
          and np.isfinite(cls).all() and np.isfinite(tokens).all(), "Witness schema differs")
    check(producer.sha(cls.tobytes()) == record["CLS_float32_sha256"], "CLS bytes differ")
    check(item["query_ids"] == [q["query_id"] for q in queries], "Input query membership differs")
    unit, reason = producer.normalize(cls)
    check(reason == record["CLS_unknown_reason"], "CLS unknown status differs")
    result, unknown = {}, {}
    for q in queries:
        check(q["input_id"] == item["input_id"] and q["geometry"]["status"] in STRATA,
              "Query input/geometry differs")
        _, point, why = producer.point_readout(tokens, q["geometry"])
        if why:
            unknown[q["query_id"]] = why
        result[q["query_id"]] = {"cls": unit, "point": point,
                                "unknown_reasons": {"cls": reason, "point": why}}
    check(unknown == record["point_unknown_reasons"], "Point unknown status differs")
    return result


def cosine_margin(unit, bank, labels, *, unknown_reason=None):
    """Never silently remove an unavailable bank member from either class."""
    unavailable = [identity for identity, vector in bank.items() if vector is None]
    if unavailable or unit is None:
        return {"margin": None, "status": "unavailable",
                "reason": "bank_descriptor_unavailable" if unavailable else unknown_reason or "query_descriptor_unavailable",
                "unknown_bank_ids": unavailable, "best_ball": None, "best_other_object": None,
                "best_ball_ids": [], "best_other_object_ids": []}
    check(set(bank) == set(labels) and set(labels.values()) == {"ball", "other_object"},
          "Bank class contract differs")
    scores = {identity: float(np.dot(unit, vector)) for identity, vector in bank.items()}
    check(all(math.isfinite(v) for v in scores.values()), "Nonfinite cosine")
    maxima = {kind: max(v for identity, v in scores.items() if labels[identity] == kind)
              for kind in ("ball", "other_object")}
    return {"margin": maxima["ball"] - maxima["other_object"], "status": "observed", "reason": None,
            "unknown_bank_ids": [], "best_ball": maxima["ball"], "best_other_object": maxima["other_object"],
            "best_ball_ids": [i for i, v in scores.items() if labels[i] == "ball" and v == maxima["ball"]],
            "best_other_object_ids": [i for i, v in scores.items() if labels[i] == "other_object" and v == maxima["other_object"]]}


def margins_for_queries(queries, vectors, bank_ids, labels):
    by_id = {q["query_id"]: q for q in queries}
    check(len(by_id) == len(queries) and set(bank_ids) == set(labels), "Bank/query IDs differ")
    for identity in bank_ids:
        q = by_id[identity]; case = q["historical_case"]
        check(q["cohort"] == "historical" and q["source_role"] == "reference_bank"
              and case["original_source_role"] == "fit_eligible"
              and case["semantic_label_status"] == "human_accepted_assisted_appearance"
              and case["accepted_appearance"]["classification"] == labels[identity], "Bank authority differs")
    banks = {name: {identity: vectors[identity][name] for identity in bank_ids} for name in READOUTS}
    rows = {}
    for q in queries:
        identity = q["query_id"]
        row = {"query_id": identity, "input_id": q["input_id"], "cohort": q["cohort"],
               "block_id": q["block_id"], "frame": q["source_frame_index"],
               "geometry_status": q["geometry"]["status"],
               "padded_native_pixels": q["geometry"].get("padded_native_pixels", 0), "readouts": {}}
        for name in READOUTS:
            if identity in bank_ids:
                result = {"margin": None, "status": "excluded_bank_query", "reason": "bank_vectors_serve_as_references_only"}
            elif q["input_id"] is None:
                result = {"margin": None, "status": "missing_selection", "reason": "missing_selection"}
            else:
                result = cosine_margin(vectors[identity][name], banks[name], labels,
                                       unknown_reason=vectors[identity]["unknown_reasons"][name])
            row["readouts"][name] = result
        rows[identity] = row
    return rows


def add_margins(frame, feature_row, main_queries, stress_query, scores, block):
    """Transport exact original candidate identities into the existing label join."""
    check(len(main_queries) == len(frame["candidates"]) == len(feature_row["main_candidates"]),
          "Main query count differs")
    for q in [*main_queries, stress_query]:
        check(q["block_id"] == frame["block_id"] and q["source_frame_index"] == frame["frame"]
              and q["source_pts_ticks"] == feature_row["source_pts_ticks"]
              and q["time_base"] == feature_row["time_base"]
              and q["source_png"] == feature_row["source_png"]
              and q["native_selected_candidate_index"] == feature_row["native_selected_candidate_index"]
              and q["source_video"] == block["source_video"] and q["source_role"] == "checkpoint_validation",
              "Point query/source join differs")
    reference = frame.pop("_reference")
    for c, item, q in zip(frame["candidates"], feature_row["main_candidates"], main_queries, strict=True):
        check(q["cohort"] == "HOU_main" and q["candidate"] == item["candidate"]
              and q["center_xy_px"] == [q["candidate"]["center_x"], q["candidate"]["center_y"]],
              "Point candidate identity changed")
        c.update(query_id=q["query_id"], geometry_status=q["geometry"]["status"],
                 localization_distance_px=None if reference is None else math.dist(q["center_xy_px"], reference))
        c["features"] = {"peak": c["features"]["peak"], **{n: scores[q["query_id"]]["readouts"][n]["margin"] for n in READOUTS}}
    check(stress_query["cohort"] == "HOU_stress"
          and stress_query["observation"] == feature_row["expanded_weak_selection"]["observation"]
          and stress_query["center_xy_px"] == stress_query["observation"]["center_xy_px"], "Stress identity changed")
    s = frame["stress"]
    s.update(query_id=stress_query["query_id"], geometry_status=stress_query["geometry"]["status"],
             localization_distance_px=None if reference is None or not s["emitted"] else math.dist(stress_query["center_xy_px"], reference))
    s["features"] = {"peak": s["features"]["peak"], **{n: scores[s["query_id"]]["readouts"][n]["margin"] for n in READOUTS}}
    return frame


def rank_summary(frames, feature, *, native_only=False):
    rows = [response.rank_frame(f, feature, native_only=native_only)
            for f in frames if f["reference_category"] == "eligible"]
    return {"frames": rows, "counts_among_available_features": dict(Counter(r["status_among_available_features"] for r in rows)),
            "complete_rankings": sum(r["complete_feature_ranking"] for r in rows),
            "incomplete_rankings": sum(not r["complete_feature_ranking"] for r in rows)}


def strata_summary(frames, feature, shared):
    """Strata describe coverage; they do not supply new cutoffs or exclusions."""
    result = {}
    for status in STRATA:
        subset = [{**f, "candidates": [c for c in f["candidates"] if c["geometry_status"] == status]} for f in frames]
        census = Counter(); bounds = {}
        for f in subset:
            for c in response.population(f, feature):
                census[f["reference_category"] + ":candidates"] += 1
                census[f["reference_category"] + ":unknown"] += response.value(c, feature) is None
        for label, key, strict in (("reject_all_observed_hidden", "maximum_observed_certain_hidden", True),
                                   ("retain_all_observed_native_correct", "minimum_observed_native_correct", False)):
            counts = Counter(); cutoff = shared[feature][key]
            for f in subset:
                candidates = response.population(f, feature)
                for c in candidates:
                    decision = response._decision(response.value(c, feature), cutoff, strict)
                    if f["reference_category"] == "certain_hidden": counts["hidden_candidates:" + decision] += 1
                    if f["native_correct"] and c["is_native_selected"]: counts["native_correct:" + decision] += 1
                if f["reference_category"] == "certain_hidden":
                    decisions = [response._decision(response.value(c, feature), cutoff, strict) for c in candidates]
                    counts["hidden_frames_with_survivor"] += "retained" in decisions
                    counts["hidden_frames_with_unknown"] += "unknown" in decisions
                s = f["stress"]
                if feature != "native_mass" and s["emitted"] and s["geometry_status"] == status:
                    decision = response._decision(s["features"][feature], cutoff, strict)
                    for tag in s["tags"]: counts["stress:" + tag + ":" + decision] += 1
            bounds[label] = {"same_shared_HOU_cutoff": cutoff, "comparison": ">" if strict else ">=", "counts": dict(counts)}
        result[status] = {"candidate_census": dict(census), "ranks_within_this_candidate_stratum_only": rank_summary(subset, feature),
                          "bounds": bounds, "stratum_is_not_semantic_or_absence_label": True}
    return result


def summarize(frames, shared):
    result = {"frames": len(frames), "reference_categories": dict(Counter(f["reference_category"] for f in frames)),
              "main_candidates": sum(len(f["candidates"]) for f in frames),
              "main_geometry_statuses": dict(Counter(c["geometry_status"] for f in frames for c in f["candidates"])),
              "stress_geometry_statuses": dict(Counter(f["stress"]["geometry_status"] for f in frames)),
              "out_of_source_candidates": sum(not c["in_bounds"] for f in frames for c in f["candidates"]),
              "stress_tags": dict(Counter(t for f in frames for t in f["stress"]["tags"])), "features": {}}
    for name in FEATURES:
        t = shared[name]
        result["features"][name] = {
            "scope": "native_only" if name == "native_mass" else "all_in_source_main_candidates",
            "ranks": rank_summary(frames, name), "native_only_ranks": rank_summary(frames, name, native_only=True),
            "reject_all_observed_hidden_bound": response.evaluate_bound(frames, name, t["maximum_observed_certain_hidden"], strict=True),
            "retain_all_observed_native_correct_bound": response.evaluate_bound(frames, name, t["minimum_observed_native_correct"], strict=False),
            "padding_strata": strata_summary(frames, name, shared)}
    for name in READOUTS:
        item = result["features"][name]
        for baseline in ("cls", "peak"):
            if baseline != name:
                item["paired_complete_ranks_vs_" + baseline] = response.compare_ranks(item["ranks"]["frames"], result["features"][baseline]["ranks"]["frames"])
        item["paired_complete_native_only_vs_mass"] = response.compare_ranks(item["native_only_ranks"]["frames"], result["features"]["native_mass"]["ranks"]["frames"])
    for status in STRATA:
        a = result["features"]["point"]["padding_strata"][status]["ranks_within_this_candidate_stratum_only"]["frames"]
        b = result["features"]["cls"]["padding_strata"][status]["ranks_within_this_candidate_stratum_only"]["frames"]
        result["features"]["point"]["padding_strata"][status]["paired_complete_ranks_vs_cls"] = response.compare_ranks(a, b)
    return result


def historical_summary(queries, scores, old_report):
    rows, pairs, groups = [], [], defaultdict(list)
    old = {r["case_id"]: r for r in old_report["queries"]}
    for q in queries:
        if q["cohort"] != "historical": continue
        case = q["historical_case"]; identity = q["query_id"]
        row = {**scores[identity], "case": case, "screen_role": q["source_role"],
               "accepted_classification": case.get("accepted_appearance", {}).get("classification"),
               "prior_AI_assessment_not_accepted": case.get("prior_ai_assessment", {}).get("assessment"),
               "old_nearest_bank_screen": old.get(identity), "old_fitted_veto": "Separate earlier fitted-logistic experiment; not rerun or conflated with nearest-bank scores."}
        rows.append(row); groups[q["source_id"], q["source_frame_index"], q["source_role"]].append(row)
    for (source, frame, role), group in groups.items():
        if role == "reference_bank": continue
        for ball in [r for r in group if r["accepted_classification"] == "ball"]:
            for other in [r for r in group if r["accepted_classification"] == "other_object"]:
                differences = {}
                for name in READOUTS:
                    a, b = ball["readouts"][name]["margin"], other["readouts"][name]["margin"]
                    differences[name] = {"ball_minus_other_margin": None if a is None or b is None else a-b,
                        "ordering": "unknown" if a is None or b is None else "ball_above" if a>b else "tie" if a==b else "other_above"}
                pairs.append({"source_id": source, "frame": frame, "screen_role": role,
                              "ball_id": ball["query_id"], "other_id": other["query_id"], "readouts": differences})
    roles = {}
    for role in dict.fromkeys(r["screen_role"] for r in rows):
        cohort = [r for r in rows if r["screen_role"] == role]; counts = {}
        for name in READOUTS:
            census = Counter()
            for r in cohort:
                margin = r["readouts"][name]["margin"]
                if role == "reference_bank": census["excluded_bank_query"] += 1
                elif role == "resolved_check":
                    label = r["accepted_classification"]
                    census["unknown" if margin is None else "exact_tie" if margin==0 else
                           "accepted_class_preferred" if (margin>0)==(label=="ball") else "other_class_preferred"] += 1
                else: census["unknown" if margin is None else "ball_preference" if margin>0 else "other_preference" if margin<0 else "exact_tie"] += 1
            counts[name] = dict(census)
        roles[role] = {"cases": len(cohort), "readouts": counts,
                       "semantic_accuracy_claim": role == "resolved_check", "independent_validation": False}
    return {"cases": rows, "roles": roles, "accepted_same_frame_pairs": pairs,
            "bank_query_metrics_excluded": True, "DET_parameter_or_model_choice": False,
            "exposed_AI_assessments_not_promoted_to_labels": True}


def strong_subsets(frames, shared):
    rows = []
    for f in frames:
        prior = f["prior_strong"]
        kind = ("six_prior_strong_gains" if prior["outcome"] == "matched" and f["native_outcome"] != "matched" else
                "27_prior_native_correct_losses" if f["native_correct"] and prior["outcome"] != "matched" else None)
        if kind is None: continue
        native = next((c for c in f["candidates"] if c["is_native_selected"]), None)
        strong = next((c for c in f["candidates"] if c["id"] == prior["candidate_index"]), None)
        detail = {}
        for name in FEATURES:
            a = None if strong is None else response.value(strong, name)
            b = None if native is None else response.value(native, name)
            detail[name] = {"native": b, "prior_strong": a,
                "ordering": "unavailable_or_missing" if a is None or b is None else "strong_above" if a>b else "tie" if a==b else "native_above",
                "native_at_reject_hidden_bound": response._decision(b, shared[name]["maximum_observed_certain_hidden"], True),
                "strong_at_retain_native_bound": response._decision(a, shared[name]["minimum_observed_native_correct"], False)}
        rows.append({"block_id": f["block_id"], "frame": f["frame"], "subset": kind,
                     "native_outcome": f["native_outcome"], "prior_strong": prior, "features": detail})
    check(Counter(r["subset"] for r in rows) == {"six_prior_strong_gains": 6, "27_prior_native_correct_losses": 27}, "Prior corrected-strong subset differs")
    return {"rows": rows, "counts": dict(Counter(r["subset"] for r in rows)),
            "subset_inputs_not_selected_for_new_inference": True}


def execute(root=ROOT):
    root = Path(root).resolve(); directory = root / producer.OUTPUT
    completed = read(directory / "completed.json")
    check(completed["status"] == "completed_all_descriptors_sealed"
          and completed["all_descriptors_sealed_before_outcome_analysis"] is True
          and completed["outcome_analysis_performed"] is False
          and completed["inputs"] == 10883 and completed["queries"] == 11798, "Complete sealed inference required")
    frozen = read(bound(root, completed["freeze"])); prepared = read(bound(root, completed["prepared"]))
    check(frozen["prepared"] == completed["prepared"] and frozen["config"] == completed["config"] == prepared["config"], "Inference freeze differs")
    check(bind(root, Path(__file__)) in frozen["source"], "Analysis source not frozen before inference")
    for link in frozen["source"]: bound(root, link)
    config = read(bound(root, completed["config"])); producer.validate_config(config)
    check(config["readouts"]["names"] == list(READOUTS) and config["quality_criteria_unchanged"]["radius_source_pixels_inclusive"] == 10,
          "Analysis scope differs")
    preparation = read(bound(root, prepared["preparation"])); geometry = read(bound(root, prepared["geometry_freeze"]))
    inputs, queries, by_input = producer.load_registries(root, preparation)
    check(completed["input_registry"] == preparation["input_registry"] and completed["query_registry"] == preparation["queries_registry"], "Sealed registries differ")
    records = [read(bound(root, link)) for link in completed["input_records"]]
    expected = {i["input_id"]: i for i in inputs}
    check(len(records) == len(expected) and {r["input"]["input_id"] for r in records} == set(expected), "Input receipt census differs")
    paths = [bound(root, r["witness"]) for r in records]  # All witness bytes checked before any outcome joins.
    vectors, parity = {}, []
    for record, path in zip(records, paths, strict=True):
        check(record["config"] == completed["config"] and record["outcome_analysis_performed"] is False, "Input scope differs")
        identity = record["input"]["input_id"]
        with np.load(path, allow_pickle=False) as data:
            check(set(data.files) == {"cls", "tokens", "sequence_indices"}, "Unexpected NPZ fields")
            vectors.update(reconstruct(record, expected[identity], by_input[identity], data))
        parity.extend(record["historical_CLS_parity"])
    check(parity == completed["historical_CLS_parity"] and len(parity) == 60
          and all(p["passed"] for p in parity)
          and {p["query_id"] for p in parity} == {q["query_id"] for q in queries if q["cohort"] == "historical"}, "Historical CLS parity differs")
    bank = config["reference_bank"]
    old_report = read(bound(root, geometry["old_report"]))
    check(bank["case_ids"] == old_report["reference_bank_case_ids"] and Counter(bank["classes"].values()) == {"ball": 4, "other_object": 6}, "Original bank differs")
    scores = margins_for_queries(queries, vectors, bank["case_ids"], bank["classes"])
    del vectors
    extraction = read(bound(root, geometry["study_extraction"])); package = read(bound(root, geometry["paired_inputs"]))
    check(extraction["paired_inputs"] == geometry["paired_inputs"], "Reference package differs")
    entries = {e["block"]["block_id"]: e for e in package["blocks"] if e["block"]["block_id"] in HOU}
    feature_paths = [bound(root, b["features"]) for b in extraction["blocks"]]
    followup = read(bound(root, geometry["followup_comparison"]))
    followup_rows = {r["block_id"]: r for r in followup["records"] if r["block_id"] in HOU}
    query_groups = defaultdict(list)
    for q in queries:
        if q["cohort"] != "historical": query_groups[q["block_id"], q["source_frame_index"], q["cohort"]].append(q)
    frames = []
    for spec, path in zip(extraction["blocks"], feature_paths, strict=True):
        bid = spec["block_id"]; check(bid in HOU, "Non-HOU feature block")
        entry = entries[bid]; block = entry["block"]
        stress = read(bound(root, spec["expanded_choices"]))["observations"]
        strong = read(bound(root, followup_rows[bid]["variants"]["motion_and_speed"]))["observations"]
        strong_scores = read(bound(root, followup_rows[bid]["scores"]["motion_and_speed"]))["frame_results"]
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        for row, frame, native, prior, corrected, prior_score in zip(rows, block["frames"], entry["candidate_observations"], stress, strong, strong_scores, strict=True):
            joined = response.join_frame(row, frame, native, block, prior)
            index = frame["source_frame_index"]
            reference = frame["annotation"]["geometry"]["center_xy_px"] if joined["reference_category"] == "eligible" else None
            joined["_reference"] = reference
            main = query_groups[bid, index, "HOU_main"]; sq = query_groups[bid, index, "HOU_stress"]
            check(len(sq) == 1 and all(q["main_pool"] == spec["main_pool"] and q["stress_choice_source"] == spec["expanded_choices"] for q in [*main, *sq]), "Query source binding differs")
            joined = add_margins(joined, row, main, sq[0], scores, block)
            check(corrected["source_frame_index"] == index and corrected["source_pts_ticks"] == row["source_pts_ticks"]
                  and corrected["time_base"] == row["time_base"] and prior_score["source_frame_index"] == index
                  and prior_score["source_pts_ticks"] == row["source_pts_ticks"] and prior_score["time_base"] == row["time_base"]
                  and prior_score["reference_category"] == joined["reference_category"], "Prior strong clock/category differs")
            selected = corrected["selected_candidate_index"]
            point = None if selected is None else [main[selected]["candidate"][k] for k in ("center_x", "center_y")]
            check(point == corrected["center_xy_px"], "Prior strong candidate identity differs")
            outcome = "unscored" if reference is None else response._outcome(point, reference, block["source_video"]["width_px"], block["source_video"]["height_px"])
            check(reference is None or outcome == prior_score["outcome"], "Prior strong outcome differs")
            joined["prior_strong"] = {"candidate_index": selected, "outcome": outcome}
            frames.append(joined)
    check(len(frames) == 960 and sum(len(f["candidates"]) for f in frames) == 10778
          and sum(f["native_correct"] for f in frames) == 842, "HOU reference census differs")
    shared = {name: response.thresholds(frames, name) for name in FEATURES}
    output = {"schema_version": "point_feature_analysis/v0.1", "status": "completed_reference_assisted_diagnosis",
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "inference": bind(root, directory / "completed.json"),
        "freeze": completed["freeze"], "config": completed["config"], "source": bind(root, Path(__file__)),
        "reused_frozen_math_and_category_helpers": [bind(root, root / "src/ball_tracking/candidate_response_analysis.py"),
            bind(root, root / "src/ball_tracking/completion_scoring.py"), bind(root, root / "src/ball_tracking/point_feature_inference.py")],
        "study_extraction": geometry["study_extraction"], "paired_inputs": geometry["paired_inputs"],
        "prior_corrected_strong_comparison": geometry["followup_comparison"], "old_nearest_bank_report": geometry["old_report"],
        "query_margin_rows": list(scores.values()), "joined_HOU_frame_diagnostics": frames, "shared_HOU_bounds": shared,
        "episodes": [{"block_id": bid, **summarize([f for f in frames if f["block_id"] == bid], shared)} for bid in HOU],
        "pooled_descriptive_only": summarize(frames, shared), "prior_corrected_strong_subsets": strong_subsets(frames, shared),
        "historical_separate": historical_summary(queries, scores, old_report),
        "winner_selected": False, "production_thresholds_selected": False, "new_model_calls": 0,
        "new_fits": 0, "new_selector_runs": 0, "new_tracking_outputs": 0, "protected_access": False,
        "limitations": ["Repeatedly inspected HOU development, not independent validation or frame-independent samples.",
            "Within10px is a localization criterion, not proof that the point lies on physical ball pixels; misses are not semantic negatives.",
            "Unknown bank members invalidate the representation margin; unknown queries never count as successful absence or retention.",
            "Padded crops remain scored and reported separately under identical HOU-wide bounds; padding is not absence evidence.",
            "Patch tokens mix global context through attention; this isolates spatial readout, not crop scale, backbone or supervision.",
            "Historical nearest-bank control and fitted-logistic veto have distinct failure provenance; no fitted head is applied here.",
            "All coordinates remain the prior observed candidates; no trajectory or operational threshold is produced."]}
    destination = directory / "analysis_v0_1/completed.json"
    write_once(destination, output)
    return {"status": output["status"], "analysis": bind(root, destination), "frames": len(frames)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", required=True)
    parser.parse_args()
    print(json.dumps(execute()))


if __name__ == "__main__":
    main()
