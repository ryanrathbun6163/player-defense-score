"""Run the frozen CPU acceptance analysis after independently audited new fits.

Imports and --check are metadata-only. All output paths are exclusive and old
experiments are read-only. No model call, threshold selection or adoption occurs.
"""
from __future__ import annotations

import argparse
from collections import Counter
from importlib import metadata
import json
from pathlib import Path
import time
import traceback

from . import candidate_acceptance_data as data
from . import candidate_acceptance_evaluation as evaluation
from . import candidate_acceptance_neural as neural

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = neural.BASE + "/attempt_001/analysis"
AUDIT = neural.BASE + "/implementation_review/neural_output_audit.json"
TENSOR_AUDIT = neural.BASE + "/postrun_tensor_audit/attempt_001.json"
GATES = ("outer_CHI", "outer_DEN", "outer_SAC", "final_all_NBA")
REQUIRED = {
    "src/ball_tracking/candidate_acceptance_data.py",
    "src/ball_tracking/candidate_acceptance_evaluation.py",
    "src/ball_tracking/candidate_acceptance_features.py",
    "src/ball_tracking/candidate_acceptance_experiment.py",
    "tests/test_candidate_acceptance_data.py",
    "tests/test_candidate_acceptance_evaluation.py",
    "tests/test_candidate_acceptance_features.py",
    "tests/test_candidate_acceptance_experiment.py",
}


def write_lines(path, iterable):
    count = 0
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        for item in iterable:
            stream.write(json.dumps(item, allow_nan=False, separators=(",", ":")) + "\n")
            count += 1
    return count


def check_frozen(root):
    root = Path(root)
    spec = neural.read(root / neural.CONFIG)
    specification = neural.binding(root, root / neural.CONFIG)
    data.require(specification["sha256"] == neural.SPEC_SHA256, "Specification changed")
    path = root / neural.LAUNCH_BASE / "execution_freeze.json"
    freeze = neural.read(path)
    data.require(freeze.get("status") == "frozen_for_authorized_execution"
                 and freeze.get("specification") == specification, "Execution freeze differs")
    data.require(REQUIRED <= {r["path"] for r in freeze["implementation"]}, "CPU implementation bindings missing")
    inputs = {r["path"]: r for r in freeze["inputs"]}
    data.require(len(inputs) == len(freeze["inputs"]) and
                 all(inputs.get(r["path"]) == r for r in spec["input_bindings"]), "Original input binding missing")
    data.require(freeze.get("review"), "Independent implementation review missing")
    for link in [spec["protocol"], *freeze["implementation"], *freeze["inputs"],
                 freeze["focused_tests"], *freeze["review"]]:
        neural.bound(root, link)
    data.require(metadata.version("numpy") == "2.4.6" and metadata.version("scipy") == "1.17.1",
                 "Frozen CPU package versions changed")
    auth = neural.read(root / neural.LAUNCH_BASE / "execution_authorization.json")
    neural.validate_authorization(auth, neural.binding(root, path), specification)
    return spec, freeze


def checked_new_scores(root):
    """Bind every completed fit, its scores, accounting and independent audit."""
    root = Path(root)
    completion = neural.read(root / neural.NEURAL_OUTPUT / "completed.json")
    data.require(completion["status"] == "completed_three_single_game_quality_fits_no_adoption",
                 "New fits incomplete")
    data.require(completion["execution_freeze"] == neural.binding(root, root / neural.LAUNCH_BASE / "execution_freeze.json"),
                 "New fits used another implementation freeze")
    neural.validate_counters(completion["counters"])
    data.require(completion["counts"] == neural.COUNTS, "Neural workload differs")
    launch = neural.read(root / neural.LAUNCH_BASE / "launcher_finished.json")
    data.require(launch["returncode"] == 0 and launch["failure"] is None
                 and launch["event_remaining_owned_processes"] == 0, "Unclean supervised execution")
    audit = neural.read(root / AUDIT)
    data.require(audit["status"] == "passed_independent_neural_transport_accounting_and_supervision_audit",
                 "Independent neural audit did not pass")
    for link in audit["bindings"]:
        neural.bound(root, link)
    completed_binding = neural.binding(root, root / neural.NEURAL_OUTPUT / "completed.json")
    data.require(completed_binding in audit["bindings"], "Transport audit omitted current neural completion")
    tensor_audit = neural.read(root / TENSOR_AUDIT)
    data.require(tensor_audit["status"] == "passed_independent_cpu_checkpoint_tensor_optimizer_audit",
                 "Independent tensor audit did not pass")
    data.require(completed_binding in tensor_audit["source_bindings"], "Tensor audit omitted current neural completion")
    for link in [tensor_audit["helper"], *tensor_audit["source_bindings"]]:
        neural.bound(root, link)
    data.require({r["fit"] for r in completion["fits"]} == set(neural.FIT_NAMES)
                 and len(completion["fits"]) == 3, "New fit identities differ")
    result = []
    for fit in completion["fits"]:
        for link in [fit["checkpoint"], fit["fit_manifest"], *fit["recovery_checkpoints"], *fit["health"], *fit["scores"]]:
            neural.bound(root, link)
        data.require(len(fit["scores"]) == 2 and fit["frozen_tensors_unchanged"] is True, "Fit contract differs")
        for link in fit["scores"]:
            current = list(data.rows(root / link["path"]))
            data.require(all(r["fit"] == fit["fit"] for r in current), "Score file fit transport differs")
            result.extend(current)
    data.require(len(result) == 37626, "Cross-score inventory differs")
    return result


def features_for(candidates, pools, builder):
    result = []
    for row in candidates:
        if row["cohort"] == "historical":
            pool = None
        else:
            # Empty HOU pools are observed empty, not unavailable historical pools.
            pool = pools.get(row["frame_key"], [])
        feature = builder(data.observable(row), pool)
        feature["out_of_fitting_schema"] = row.get("out_of_fitting_schema", False)
        result.append(feature)
    data.unique(result, "row_key", "Features")
    return result


def attach_gate_predictions(candidates, feature_index, models, predictor):
    for row in candidates:
        feature = feature_index[row["row_key"]]
        row["scores"] = {"Q": feature["Q"], "M": feature["M"], "S": None, "J": None}
        row["gate_fit"] = data.gate_for_evaluation(row)
        reason = feature["M_fallback_reason"]
        row["M_no_rival_fallback"] = None if reason == "missing_image" else reason is not None
    for gate in GATES:
        members = [r for r in candidates if r["gate_fit"] == gate]
        vectors = [feature_index[r["row_key"]] for r in members]
        for arm in ("S", "J"):
            values = predictor(models[(gate, arm)], vectors)
            data.require(len(values) == len(members), "Predictions dropped rows")
            for row, value in zip(members, values):
                data.require((value is None) == (row["logit"] is None), "Prediction missingness changed")
                row["scores"][arm] = value
    for row in candidates:
        data.require(row["scores"]["Q"] == row["logit"], "Original quality score changed")
        for arm in evaluation.ARMS:
            evaluation.score(row, arm)


def analyze(root=ROOT):
    root = Path(root).resolve()
    output = root / OUTPUT
    data.require(not output.exists(), "Preserve existing analysis; no automatic retry")
    spec, freeze = check_frozen(root)
    scores = checked_new_scores(root)
    output.mkdir(parents=True, exist_ok=False)
    began = time.monotonic()
    neural.write_once(output / "started.json", {"at_utc": neural.stamp(),
        "execution_freeze": neural.binding(root, root / neural.LAUNCH_BASE / "execution_freeze.json"),
        "neural_completion": neural.binding(root, root / neural.NEURAL_OUTPUT / "completed.json"),
        "neural_audit": neural.binding(root, root / AUDIT),
        "neural_tensor_audit": neural.binding(root, root / TENSOR_AUDIT), "new_model_calls": 0})
    try:
        from . import candidate_acceptance_features as features
        saved = data.load_saved(root, spec)
        candidates = saved["candidates"]
        cross = data.attach_cross_scores(saved["nba_candidates"], scores)
        data.require(len(cross) == 37626, "Cross-score rows changed")
        print("Building fixed observable features for cross-scores and evaluation", flush=True)
        cross_features = features_for(cross, data.pool_index(cross), features.build_feature_row)
        eval_features = features_for(candidates, saved["pools"], features.build_feature_row)
        cross_index = data.unique(cross_features, "row_key", "Cross features")
        eval_index = data.unique(eval_features, "row_key", "Evaluation features")
        write_lines(output / "cross_training_features.jsonl", cross_features)
        write_lines(output / "evaluation_features.jsonl", eval_features)
        write_lines(output / "final_training_features.jsonl", (eval_index[r["row_key"]] for r in saved["nba_candidates"]))
        models = {}
        fit_dir = output / "fits"
        fit_dir.mkdir()
        memberships = []
        for gate in GATES:
            selected, fitting = data.gate_training_rows(gate, saved, cross)
            own_index = eval_index if gate == "final_all_NBA" else cross_index
            vectors = [own_index[r["row_key"]] for r in fitting]
            weights = [saved["weights"][gate][r["candidate_id"]]["objective_weight"] for r in fitting]
            targets = [r["target"] for r in fitting]
            weight_map = saved["weights"][gate]
            memberships.extend({"gate_fit": gate, "row_key": r["row_key"], "candidate_id": r["candidate_id"],
                                "game_id": r["game_id"], "base_fit": r["fit"], "target": r["target"],
                                "included_in_fitting": r["candidate_id"] in weight_map,
                                "objective_weight": weight_map.get(r["candidate_id"], {}).get("objective_weight")}
                               for r in selected)
            for arm in ("S", "J"):
                try:
                    model = features.fit_gate(vectors, targets, weights, arm=arm, fit_id=gate)
                except features.GateFitError as error:
                    neural.write_once(fit_dir / (gate + "_" + arm + "_failed.json"), error.fit_record)
                    raise
                models[(gate, arm)] = model
                neural.write_once(fit_dir / (gate + "_" + arm + ".json"), model)
                print(json.dumps({"gate": gate, "arm": arm, "rows": len(fitting), "solver": model["solver"]}), flush=True)
        write_lines(output / "fit_membership.jsonl", memberships)
        attach_gate_predictions(candidates, eval_index, models, features.score_gate)
        policies = evaluation.policy_rows(saved["frames"], candidates)
        choices, contrasts = evaluation.old_case_views(saved, candidates)
        decision = evaluation.decide(policies, candidates, saved["controls"]["case_views"])
        counts = {}
        for name, iterable in (
            ("candidate_scores", candidates), ("frame_registry", saved["frames"]),
            ("fixed_policy_rows", policies), ("paired_policy_rows", evaluation.paired_policy_rows(policies)),
            ("source_choices", choices), ("contrast_views", contrasts),
            ("candidate_zero_tables", evaluation.zero_tables(candidates)),
            ("policy_zero_tables", evaluation.zero_tables(policies, policy=True)),
            ("candidate_curves", evaluation.curves(candidates)),
            ("policy_curves", evaluation.curves(policies, policy=True)),
            ("historical_rows", (r for r in candidates if r["cohort"] == "historical")),
        ):
            counts[name] = write_lines(output / (name + ".jsonl"), iterable)
        neural.write_once(output / "decision.json", decision)
        neural.write_once(output / "missingness.json", evaluation.missingness(candidates, eval_features))
        neural.write_once(output / "preserved_controls_and_cases.json", saved["controls"])
        neural.write_once(output / "summary.json", {
            "counts": counts, "CPU_gate_fits": len(models), "cross_training_rows": len(cross),
            "final_training_all_rows": len(saved["nba_candidates"]),
            "evaluation_cohorts": dict(Counter(r["cohort"] for r in candidates)),
            "missing_scores_each_arm": {a: sum(r["scores"][a] is None for r in candidates) for a in evaluation.ARMS},
            "at_zero_by_context_and_policy": [
                {"context": context, "policy": policy, "arm": arm, **evaluation.aggregate(
                    [r for r in policies if r["context"] == context and r["policy"] == policy], arm)}
                for context in sorted({r["context"] for r in policies})
                for policy in ("native", "quality_top") for arm in evaluation.ARMS],
            "fixed_reference_component_criterion_passed": decision["fixed_reference_component_criterion_passed"],
            "chosen_threshold": None, "adoption": False})
        data.require(counts["candidate_scores"] == 31430 and counts["frame_registry"] == 4289
                     and counts["fixed_policy_rows"] == 8578 and counts["historical_rows"] == 60,
                     "Final population counts differ")
        result = {"status": "completed_candidate_acceptance_analysis_no_adoption", "at_utc": neural.stamp(),
                  "elapsed_seconds": time.monotonic() - began, "counts": counts, "CPU_gate_fits": len(models),
                  "new_neural_calls": 0, "old_experiments_rerun": False, "automatic_retry": False,
                  "outputs": [neural.binding(root, path) for path in sorted(output.rglob("*")) if path.is_file()],
                  "execution_freeze": neural.binding(root, root / neural.LAUNCH_BASE / "execution_freeze.json")}
        neural.write_once(output / "completed.json", result)
        print(json.dumps({k: v for k, v in result.items() if k != "outputs"}), flush=True)
        return result
    except BaseException as error:
        neural.write_once(output / "failed.json", {"at_utc": neural.stamp(), "error": type(error).__name__,
            "message": str(error), "traceback": traceback.format_exc(), "automatic_retry": False,
            "elapsed_seconds": time.monotonic() - began})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data.require(args.analyze != args.check, "Choose exactly --analyze or --check")
    if args.analyze:
        analyze()
    else:
        check_frozen(ROOT)
        print("Metadata bindings and CPU implementation check passed; no analysis run")


if __name__ == "__main__":
    main()
