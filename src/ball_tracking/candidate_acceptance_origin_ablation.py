"""Frozen CPU ablation: four new14-feature fits; all earlier work read-only."""
from __future__ import annotations

import argparse
from copy import deepcopy
from importlib import metadata
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

from . import candidate_acceptance_neural as io
from . import candidate_acceptance_evaluation as metrics
from . import candidate_acceptance_origin_data as data

ROOT = Path(__file__).resolve().parents[2]
BASE = "data/outputs/ball_tracking/candidate_acceptance_origin_ablation_v0_1"
OUTPUT = BASE + "/attempt_001"
CONFIG = "configs/ball_tracking/proposals/candidate_acceptance_origin_ablation_v0_1.json"
FREEZE = BASE + "/preparation/execution_freeze.json"
PROTECTION = BASE + "/preparation/protection.json"
SOURCE = data.SOURCE
ARMS = ("Q", "S", "J", "M", "A")
REMOVED = ("native_indicator", "origin_unavailable")
REQUIRED = {"src/ball_tracking/candidate_acceptance_origin_" + name + ".py" for name in ("model", "data", "ablation")}
REQUIRED |= {"tests/test_candidate_acceptance_origin_" + name + ".py" for name in ("model", "data", "ablation")}
COUNTS = {"CPU_fits": 4, "features": 14, "evaluation_slots": 31430, "observed_scores": 31419,
          "missing_scores": 11, "context_frames": 4289, "fixed_policy_rows": 8578,
          "cross_features_reused": 37626, "final_features_reused": 18813,
          "fit_membership_reused": 56439, "known_fit_row_presentations": 52572,
          "neural_calls": 0, "GPU_queries": 0}


def rows(path):
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def write_rows(path, items):
    count = 0
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        for item in items:
            stream.write(json.dumps(item, allow_nan=False, separators=(",", ":")) + "\n")
            count += 1
    return count


def accepted(row, arm):
    value = metrics.score(row, arm)
    return value is not None and value > 0


def protection_lists(policies, candidates, case_views):
    """Original Q/J labels and scores only, constructed before any A outcome."""
    named = {key for group in case_views["named_groups"].values() for key in group.get("frame_keys", [])}
    return {
        "NBA_J_kept_correct_policy_ids": sorted(r["row_key"] for r in policies
            if r["context"] == "nba_out_of_fold" and r["evaluation_category"] == "eligible_match" and accepted(r, "J")),
        "HOU_Q_or_J_kept_correct_named_policy_ids": sorted(r["row_key"] for r in policies
            if r["context"] == "HOU_development" and r["frame_key"] in named
            and r["evaluation_category"] == "eligible_match" and (accepted(r, "Q") or accepted(r, "J"))),
        "HOU_Q_or_J_kept_correct_named_stress_ids": sorted(r["row_key"] for r in candidates
            if r["cohort"] == "HOU_stress" and r["frame_key"] in named
            and r["evaluation_category"] == "eligible_match" and (accepted(r, "Q") or accepted(r, "J"))),
        "constructed_from": "accepted original Q/J scores and named-case identities before A fitting",
        "candidate_alternatives_are_not_extra_vetoes": True,
    }


def check_freeze(root):
    root = Path(root)
    spec = io.read(root / CONFIG)
    freeze = io.read(root / FREEZE)
    io.check(freeze["status"] == "frozen_for_authorized_CPU_origin_ablation"
             and freeze["specification"] == io.binding(root, root / CONFIG), "Freeze/specification differs")
    io.check(spec["counts"] == COUNTS and spec["removed_features"] == list(REMOVED), "Experiment scope changed")
    git_options = {"cwd": root, "text": True, "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    io.check(subprocess.check_output(["git", "branch", "--show-current"], **git_options).strip() == spec["branch"], "Branch changed")
    io.check(subprocess.check_output(["git", "rev-parse", "HEAD"], **git_options).strip() == spec["head"], "HEAD changed")
    io.check(not subprocess.check_output(["git", "diff", "--cached", "--name-only"], **git_options).strip(), "Index changed")
    io.check(freeze["user_statement"] == "Ok chat move forward" and freeze["counts"] == COUNTS,
             "Current direction/scope missing")
    io.check(REQUIRED <= {r["path"] for r in freeze["implementation"]}, "Implementation/test binding absent")
    io.check(freeze["review"] and io.read(root / freeze["focused_tests"]["path"])["status"] == "passed",
             "Focused checks or independent review missing")
    for link in [spec["protocol"], *spec["inputs"], *freeze["implementation"],
                 freeze["protection"], freeze["focused_tests"], *freeze["review"]]:
        io.bound(root, link)
    io.check(freeze["protection"]["path"] == PROTECTION and spec["protection"] == freeze["protection"], "Protection identity changed")
    old = io.read(root / SOURCE / "completed.json")
    audit = io.read(root / spec["accepted_output_audit"]["path"])
    io.bound(root, spec["accepted_output_audit"])
    io.check(old["status"] == "completed_candidate_acceptance_analysis_no_adoption"
             and audit["status"] == "passed_independent_acceptance_output_audit"
             and io.binding(root, root / SOURCE / "completed.json") in audit["bindings"], "Accepted source audit differs")
    input_map = {r["path"]: r for r in spec["inputs"]}
    io.check(len(input_map) == len(spec["inputs"]) and all(input_map.get(r["path"]) == r for r in old["outputs"]),
             "Complete accepted-output inputs missing")
    for name, version in (("numpy", "2.4.6"), ("scipy", "1.17.1")):
        io.check(metadata.version(name) == version, "CPU runtime changed: " + name)
    io.check("torch" not in sys.modules, "CPU-only runner must not import Torch")
    return spec, freeze


def verify_retained_scaler(model, old):
    names = [n for n in old["feature_names"] if n not in REMOVED]
    io.check(model["feature_names"] == names, "A feature projection differs")
    positions = [old["feature_names"].index(n) for n in names]
    for key in ("means", "scales", "details"):
        io.check(model["scaler"][key] == [old["scaler"][key][i] for i in positions], "Retained scaler differs: " + key)
    for key in ("targets", "weights"):
        io.check(model["training_arrays"][key] == old["training_arrays"][key], "Fit arrays changed: " + key)
    io.check(model["training_row_keys"] == old["training_row_keys"], "Fit order changed")


def add_predictions(loaded, models, predictor):
    candidates = deepcopy(loaded["candidates"])
    feature_index = loaded["feature_indices"]["evaluation"]
    for gate in data.GATES:
        members = [r for r in candidates if r["gate_fit"] == gate]
        values = predictor(models[gate], [feature_index[r["row_key"]] for r in members])
        io.check(len(values) == len(members), "A predictions lost rows")
        for row, value in zip(members, values):
            io.check((value is None) == (row["logit"] is None), "A missingness differs")
            row["scores"]["A"] = value
            metrics.score(row, "A")
    index = {r["row_key"]: r for r in candidates}
    policies = deepcopy(loaded["fixed_policies"])
    for row in policies:
        point = index.get(row["chosen_row_key"])
        io.check(point is not None or row["chosen_row_key"] is None, "Original fixed choice lost")
        row["scores"]["A"] = point["scores"]["A"] if point else None
    return candidates, policies


def zero_tables(items, policy=False):
    for key, members in sorted(metrics.grouped(items, policy).items()):
        yield {**json.loads(key), "arm": "A", "unit": "fixed_policy_context_frame" if policy else "candidate_context_slot",
               **metrics.aggregate(members, "A"), "families_tags_and_distinct_frames_not_additive": True}


def curves(items, policy=False):
    for key, members in sorted(metrics.grouped(items, policy, detailed=False).items()):
        yield {**json.loads(key), "arm": "A", "unit": "fixed_policy_context_frame" if policy else "candidate_context_slot",
               **metrics.curve(members, "A")}


def paired(items):
    for row in items:
        flags = {arm: accepted(row, arm) for arm in ARMS}
        changes = {"A_vs_" + arm: "agreement" if flags["A"] == flags[arm] else
                   "new_accept" if flags["A"] else "new_reject" for arm in ("Q", "S", "J", "M")}
        yield {**row, "accepted_at_zero": flags, **changes}


def extend_old_choices(old_choices, old_contrasts, candidates):
    query_index = {r["query_id"]: r for r in candidates if r.get("query_id")}
    choices, contrasts = deepcopy(old_choices), deepcopy(old_contrasts)
    for old in choices:
        point = query_index.get(old.get("query_id"))
        io.check((point is not None) == (old["state"] == "observed"), "Source choice identity changed")
        value = point["scores"]["A"] if point else None
        old["scores"]["A"] = value
        old["accepted_at_zero"]["A"] = value is not None and value > 0
    for old in contrasts:
        for side in ("source", "target"):
            point = query_index.get(old[side]["query_id"])
            value = point["scores"]["A"] if point else None
            old[side]["scores"]["A"] = value
            old[side]["accepted_at_zero"]["A"] = value is not None and value > 0
        a, b = old["source"]["scores"]["A"], old["target"]["scores"]["A"]
        old["delta_target_minus_source"]["A"] = b-a if a is not None and b is not None else None
    return choices, contrasts


def evaluate_decisions(policies, candidates, case_views, protection):
    checks = []
    for context in ("nba_out_of_fold", "HOU_development"):
        games = sorted({r["game_id"] for r in policies if r["context"] == context})
        for game in games:
            for policy in ("native", "quality_top"):
                members = [r for r in policies if r["context"] == context and r["game_id"] == game and r["policy"] == policy]
                counts = {arm: metrics.aggregate(members, arm)["counts"] for arm in ("J", "A")}
                for metric in ("correct_kept", "wrong_eligible_kept", "hidden_emission_frames"):
                    a, j = counts["A"][metric], counts["J"][metric]
                    higher = metric == "correct_kept"
                    checks.append({"context": context, "game_id": game, "policy": policy, "metric": metric,
                        "A": a, "J": j, "passed": a >= j if higher else a <= j,
                        "strict_improvement": a > j if higher else a < j})
    indexes = ({r["row_key"]: r for r in policies}, {r["row_key"]: r for r in candidates})
    losses = {}
    for key in ("NBA_J_kept_correct_policy_ids", "HOU_Q_or_J_kept_correct_named_policy_ids", "HOU_Q_or_J_kept_correct_named_stress_ids"):
        index = indexes[1 if "stress" in key else 0]
        io.check(all(ident in index for ident in protection[key]), "Protected identity lost")
        losses[key] = [ident for ident in protection[key] if not accepted(index[ident], "A")]
    strict = any(r["strict_improvement"] for r in checks if r["context"] == "nba_out_of_fold")
    passed = all(r["passed"] for r in checks) and strict and not any(losses.values())
    # Reuse the old criterion's arithmetic with isolated copies; original J stays untouched.
    substituted_policies, substituted_candidates = deepcopy(policies), deepcopy(candidates)
    for row in [*substituted_policies, *substituted_candidates]:
        row["scores"]["J"] = row["scores"]["A"]
    original = metrics.decide(substituted_policies, substituted_candidates, case_views)
    def relabel(value):
        if isinstance(value, dict):
            return {"A" if key == "J" else key: relabel(item) for key, item in value.items()}
        if isinstance(value, list):
            return [relabel(item) for item in value]
        return value
    return {"A_nonregression_vs_J_passed": passed, "A_vs_J_checks": checks,
        "strict_NBA_improvement": strict, "protected_losses": losses,
        "original_component_criterion_evaluated_arm": "A", "original_component_criterion": relabel(original),
        "selected_threshold": None, "model_adopted": False, "tracker_complete": False,
        "limits": ["Refitted feature-ablation evidence, not causal identification", "Origin-correlated proxies remain",
                   "Repeatedly inspected development games", "No repaired ranking or new candidate", "No semantic-presence claim"]}


def named_views(policies, candidates, case_views):
    result = {}
    for name, group in case_views["named_groups"].items():
        frames = set(group.get("frame_keys", []))
        groups = {policy: [r for r in policies if r["frame_key"] in frames and r["policy"] == policy]
                  for policy in ("native", "quality_top")}
        groups["exact_stress"] = [r for r in candidates if r["frame_key"] in frames and r["cohort"] == "HOU_stress"]
        result[name] = {"original_group": group, "views": {
            key: {"rows": [r["row_key"] for r in members],
                  "arms": {arm: metrics.aggregate(members, arm) for arm in ARMS}}
            for key, members in groups.items()}, "groups_overlap_not_additive": True}
    return result


def run(root=ROOT):
    root = Path(root).resolve()
    output = root / OUTPUT
    io.check(not output.exists(), "Preserve existing output; no silent retry")
    spec, freeze = check_freeze(root)
    loaded = data.load_inputs(root)
    source = root / SOURCE
    controls = io.read(source / "preserved_controls_and_cases.json")
    protection = protection_lists(loaded["fixed_policies"], loaded["candidates"], controls["case_views"])
    io.check(protection == io.read(root / PROTECTION), "Frozen prefit protection differs")
    output.mkdir(parents=True, exist_ok=False)
    began = time.monotonic()
    io.write_once(output / "started.json", {"at_utc": io.stamp(), "execution_freeze": io.binding(root, root / FREEZE),
        "counts": COUNTS, "new_neural_calls": 0, "GPU_queries": 0})
    try:
        from . import candidate_acceptance_origin_model as model_api
        (output / "fits").mkdir()
        models = {}
        for gate in data.GATES:
            features, targets, weights = data.fit_inputs(gate, loaded)
            try:
                model = model_api.fit_origin_gate(features, targets, weights, fit_id=gate)
            except model_api.GateFitError as error:
                io.write_once(output / "fits" / (gate + "_A_failed.json"), error.fit_record)
                raise
            verify_retained_scaler(model, loaded["original_J_models"][gate])
            io.write_once(output / "fits" / (gate + "_A.json"), model)
            models[gate] = model
            print(json.dumps({"gate": gate, "status": model["status"], "rows": model["training_row_count"],
                              "solver": model["solver"]}), flush=True)
        candidates, policies = add_predictions(loaded, models, model_api.score_origin_gate)
        choices, contrasts = extend_old_choices(list(rows(source / "source_choices.jsonl")),
                                               list(rows(source / "contrast_views.jsonl")), candidates)
        decisions = evaluate_decisions(policies, candidates, controls["case_views"], protection)
        counts = {}
        for name, items in (("candidate_scores", candidates), ("fixed_policy_rows", policies),
            ("paired_candidate_rows", paired(candidates)), ("paired_policy_rows", paired(policies)),
            ("candidate_zero_tables", zero_tables(candidates)), ("policy_zero_tables", zero_tables(policies, True)),
            ("candidate_curves", curves(candidates)), ("policy_curves", curves(policies, True)),
            ("source_choices", choices), ("contrast_views", contrasts),
            ("historical_rows", (r for r in candidates if r["cohort"] == "historical"))):
            counts[name] = write_rows(output / (name + ".jsonl"), items)
        io.write_once(output / "decision.json", decisions)
        io.write_once(output / "named_case_views.json", named_views(policies, candidates, controls["case_views"]))
        io.write_once(output / "summary.json", {"counts": counts, "CPU_fits": len(models),
            "transport_counts": loaded["transport_counts"],
            "missing_scores": {arm: sum(r["scores"][arm] is None for r in candidates) for arm in ARMS},
            "at_zero_by_context_and_policy": [{"context": context, "policy": policy, "arm": arm,
                **metrics.aggregate([r for r in policies if r["context"] == context and r["policy"] == policy], arm)}
                for context in sorted({r["context"] for r in policies}) for policy in ("native", "quality_top") for arm in ARMS],
            "A_nonregression_vs_J_passed": decisions["A_nonregression_vs_J_passed"],
            "original_component_criterion_for_A_passed": decisions["original_component_criterion"]["fixed_reference_component_criterion_passed"],
            "original_control_tables_and_curves": [r for r in spec["inputs"] if any(name in r["path"]
                for name in ("zero_tables.jsonl", "curves.jsonl", "missingness.json", "frame_registry.jsonl", "preserved_controls"))],
            "selected_threshold": None, "adoption": False})
        io.check(counts["candidate_scores"] == 31430 and counts["fixed_policy_rows"] == 8578
                 and counts["source_choices"] == counts["contrast_views"] == 6720
                 and counts["historical_rows"] == 60 and len(models) == 4, "Output inventory differs")
        io.check("torch" not in sys.modules, "CPU-only execution imported Torch")
        result = {"status": "completed_CPU_origin_ablation_no_adoption", "at_utc": io.stamp(),
            "elapsed_seconds": time.monotonic()-began, "counts": counts, "CPU_fits": 4,
            "new_neural_calls": 0, "GPU_queries": 0, "old_experiments_rerun": False,
            "outputs": [io.binding(root, path) for path in sorted(output.rglob("*")) if path.is_file()],
            "execution_freeze": io.binding(root, root / FREEZE)}
        io.write_once(output / "completed.json", result)
        print(json.dumps({key: value for key, value in result.items() if key != "outputs"}), flush=True)
        return result
    except BaseException as error:
        io.write_once(output / "failed.json", {"at_utc": io.stamp(), "error": type(error).__name__, "message": str(error),
            "traceback": traceback.format_exc(), "elapsed_seconds": time.monotonic()-began, "automatic_retry": False})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    io.check(args.run != args.check, "Choose --run or --check")
    if args.run:
        run()
    else:
        check_freeze(ROOT)
        print("Frozen metadata verified; no new fit run")


if __name__ == "__main__":
    main()
