"""One additive five-epoch augmentation experiment; frozen fitting helpers reused.

The old twenty-epoch recipe and completed control remain immutable.  Epoch zero
is a bound reuse of the actual old validation producer; epochs one through five
are new validations.  Only --run loads a model or reads permitted native PNGs.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import traceback
import uuid

import torch

from . import completion_training as frozen
from . import wasb_augmentation as augmentation
from .completion_training_runtime import atomic_write_once as write_once, binding
from .wasb_experiment import bound_path, canonical, read_json, runtime_versions

check = frozen.check
OUTPUT_ROOT = "data/outputs/ball_tracking/wasb_augmentation_v0_1/fit_v0_1"
SCHEMA = "completion_augmentation_training_result/v0.1"


def validate_report(report, identity):
    check(report["identity"] == identity and report["protected_frames"] == 0
          and report["post_selection_curated_labels_used"] is False
          and report["det_or_tor_used"] is False and report["threshold"] == .3
          and report["strict_threshold"] is True
          and report["selection"] == "largest_component_mass_then_stable_index"
          and report["aggregation"] == "ascending_float32_aligned_contributor_mean",
          "Validation policy or identity differs")


def read_control(root, parent, parent_identity, control_binding):
    """Check actual saved producer records, without importing/loading a model."""
    result = read_json(bound_path(root, control_binding))
    check(result["schema_version"] == "completion_training_result/v0.1"
          and result["status"] == "completed" and result["identity"] == parent_identity
          and result["completed_epochs"] == 5 and result["completed_updates"] == 7760
          and result["stop_reason"] == "five_epochs_without_rank_improvement"
          and result["protected_evaluation_authorized"] is False
          and result["post_selection_references_used"] is False
          and result["ball_phase_accepted"] is False, "Original control completion differs")
    reports = [read_json(bound_path(root, b)) for b in result["validation_reports"]]
    check([r["epoch"] for r in reports] == list(range(6)), "Control epoch census differs")
    for report in reports:
        validate_report(report, parent_identity)
        bound_path(root, report["checkpoint"])
    selected = frozen.policy.choose_checkpoint(reports)
    check(result["selection"] == {k: v for k, v in selected.items() if k != "selected_report"}
          and result["selected_checkpoint"] == selected["selected_report"]["checkpoint"]
          and frozen.policy.should_stop(5, selected["selected_epoch"]), "Control selection differs")
    check(reports[0]["checkpoint"] == parent["initialization"]["checkpoint"]
          and result["final_checkpoint"] == reports[-1]["checkpoint"], "Control checkpoints differ")
    bound_path(root, result["resume_checkpoint"])
    return result, reports


def preflight(root, recipe_path):
    """Metadata/hash checks only; return recipe,parent,package,schedule,nfhs,identity."""
    root = Path(root).resolve()
    path = (root / recipe_path).resolve()
    recipe = read_json(path)
    check(recipe["schema_version"] == "wasb_augmentation_recipe/v0.1"
          and recipe["status"] == "frozen_before_model_execution", "Augmentation recipe must be frozen")
    parent_path = bound_path(root, recipe["parent_recipe"])
    parent, package, schedule, nfhs, parent_identity = frozen.preflight(root, parent_path)
    check(recipe["runtime"] == parent["runtime"] == runtime_versions(), "Runtime differs from control")
    check(recipe["max_epochs"] == 5 and recipe["total_updates"] == 7760
          and recipe["augmentation"] == augmentation.POLICY, "Approved intervention/budget differs")
    check(recipe["protected_evaluation_authorized"] is False, "Protected evaluation remains closed")
    check(recipe["output_root"] == OUTPUT_ROOT and recipe["cache_root"] == parent["cache_root"],
          "Experiment output/cache differs")
    frozen.output_path(root, recipe["output_root"])
    bound_path(root, recipe["execution_plan"])
    check(isinstance(recipe["user_authority"].get("approval"), str)
          and bool(recipe["user_authority"]["approval"].strip()), "Missing user authority")
    code = {b["path"]: bound_path(root, b) for b in recipe["code_bindings"]}
    for module in (augmentation,):
        check(Path(module.__file__).resolve().relative_to(root).as_posix() in code,
              "Recipe omits augmentation implementation")
    check(Path(__file__).resolve().relative_to(root).as_posix() in code
          and "src/ball_tracking/gpu_supervision.py" in code, "Recipe omits runner/supervisor binding")
    check([e["epoch"] for e in schedule["epochs"][:5]] == list(range(1, 6))
          and sum(len(e["batches"]) for e in schedule["epochs"][:5]) == 7760
          and len(package["training_triplets"]) == 3103, "Control schedule prefix differs")
    read_control(root, parent, parent_identity, recipe["control_completed"])
    identity = {"recipe": binding(root, path), "parent_identity": parent_identity,
                "control_completed": recipe["control_completed"],
                "package_sha256": canonical(package), "schedule_sha256": canonical(schedule),
                "executed_epochs_sha256": canonical(schedule["epochs"][:5]),
                "augmentation_sha256": canonical(augmentation.POLICY)}
    return recipe, parent, package, schedule, nfhs, identity


def epoch_zero_record(root, recipe, parent, identity):
    """New envelope, original saved validation body retained verbatim otherwise."""
    control, reports = read_control(root, parent, identity["parent_identity"], recipe["control_completed"])
    result = deepcopy(reports[0])
    result["identity"] = identity
    result["reused_validation"] = {"source_report": control["validation_reports"][0],
        "source_identity": reports[0]["identity"], "source_completed": recipe["control_completed"],
        "new_model_calls": 0, "policy_and_checkpoint_unchanged": True}
    return result


def epoch_zero(root, output, recipe, parent, identity):
    result = epoch_zero_record(root, recipe, parent, identity)
    write_once(output / "validation/epoch_000.json", result)
    return result


def validate_augmentation_history(losses):
    """Check durable draws against the separate stateless producer on resume."""
    for row in losses:
        audits = row["augmentation"]
        check(len(audits) == len(row["triplet_ids"]), "Augmentation sample census differs")
        for index, (triplet, audit) in enumerate(zip(row["triplet_ids"], audits, strict=True)):
            expected = augmentation.parameters(seed=1234, epoch=row["epoch"],
                batch_index=row["batch_index"], sample_index=index)
            check(all(audit.get(k) == v for k, v in expected.items())
                  and audit.get("triplet_id") == triplet and audit.get("shared_frame_count") == 3
                  and audit.get("input_shape") == [9, 288, 512]
                  and audit.get("targets_mirrored_with_images") is True
                  and audit.get("channel_masks_unchanged") is True
                  and audit.get("source_uint8_recovery_verified") is True
                  and audit.get("original_inputs_mutated") is False, "Saved augmentation draw differs")


def completion_record(root, output, recipe, identity, reports, losses, latest, elapsed, resources):
    check([r["epoch"] for r in reports] == list(range(6)) and len(losses) == recipe["total_updates"],
          "Five-epoch experiment is incomplete")
    selected = frozen.policy.choose_checkpoint(reports)
    return {"schema_version": SCHEMA, "status": "completed", "identity": identity,
        "completed_epochs": 5, "completed_updates": len(losses),
        "selection": {k: v for k, v in selected.items() if k != "selected_report"},
        "selected_checkpoint": selected["selected_report"]["checkpoint"],
        "final_checkpoint": reports[-1]["checkpoint"],
        "validation_reports": [binding(root, output / "validation" / f"epoch_{r['epoch']:03d}.json") for r in reports],
        "resume_checkpoint": binding(root, latest), "stop_reason": "five_epoch_budget",
        "parent_recipe": recipe["parent_recipe"], "control_completed": recipe["control_completed"],
        "epoch_zero_reused": True, "new_validation_epochs": [1, 2, 3, 4, 5],
        "initial_optimizer": "fresh_Adam_no_parent_optimizer_state", "augmentation": augmentation.POLICY,
        "attempt_elapsed_seconds": elapsed, "resources": resources,
        "protected_evaluation_authorized": False, "post_selection_references_used": False,
        "heatmaps_retained": False, "ball_phase_accepted": False}


def validate_completion(root, recipe, identity, result, reports):
    check(result["schema_version"] == SCHEMA and result["status"] == "completed"
          and result["identity"] == identity and result["completed_epochs"] == 5
          and result["completed_updates"] == recipe["total_updates"] and result["stop_reason"] == "five_epoch_budget"
          and result["parent_recipe"] == recipe["parent_recipe"]
          and result["control_completed"] == recipe["control_completed"]
          and result["epoch_zero_reused"] is True and result["new_validation_epochs"] == [1, 2, 3, 4, 5]
          and result["augmentation"] == augmentation.POLICY
          and result["initial_optimizer"] == "fresh_Adam_no_parent_optimizer_state"
          and result["protected_evaluation_authorized"] is False
          and result["post_selection_references_used"] is False
          and result["ball_phase_accepted"] is False, "Augmentation completion contract differs")
    check([r["epoch"] for r in reports] == list(range(6)), "Experiment validation census differs")
    for r in reports:
        validate_report(r, identity)
        bound_path(root, r["checkpoint"])
        if r["epoch"] > 0:
            check("reused_validation" not in r, "Trained validation must be newly produced")
    check(result["final_checkpoint"] == reports[-1]["checkpoint"], "Final checkpoint differs")
    chosen = frozen.policy.choose_checkpoint(reports)
    check(result["selection"] == {k: v for k, v in chosen.items() if k != "selected_report"}
          and result["selected_checkpoint"] == chosen["selected_report"]["checkpoint"], "Selected checkpoint differs")
    bound_path(root, result["resume_checkpoint"])


def audit_completed_result(root, recipe_path):
    """New-schema consumer for the later conditional comparison, metadata only."""
    root = Path(root).resolve()
    recipe, parent, _, _, _, identity = preflight(root, recipe_path)
    output = frozen.output_path(root, recipe["output_root"])
    result_path = output / "completed.json"
    result = read_json(result_path)
    reports = [read_json(bound_path(root, b)) for b in result["validation_reports"]]
    validate_completion(root, recipe, identity, result, reports)
    check(reports[0] == epoch_zero_record(root, recipe, parent, identity), "Reused epoch-zero body differs")
    selected = {"training_result": binding(root, result_path), "checkpoint": result["selected_checkpoint"],
        "selection": result["selection"], "method_kind": "wasb_five_epoch_augmentation",
        "protected_evaluation_authorized": False}
    return selected, {"status": "passed", "training_result": selected["training_result"],
        "completed_epochs": 5, "completed_updates": result["completed_updates"], "selected_epoch": result["selection"]["selected_epoch"],
        "validation_reports_checked": 6, "epoch_zero_reuse_checked": True,
        "model_loaded": False, "source_pixels_read": False, "protected_evaluation_authorized": False}


def execute(root, recipe_path, *, resume=False):
    root = Path(root).resolve()
    context = preflight(root, recipe_path)
    output = frozen.output_path(root, context[0]["output_root"])
    output.mkdir(parents=True, exist_ok=True)
    with frozen.training.training_lock(output / "training.lock"):
        return _execute_locked(root, *context, output, resume)


def _execute_locked(root, recipe, parent, package, schedule, nfhs, identity, output, resume):
    identity_path = output / "identity.json"
    if identity_path.exists():
        check(resume and read_json(identity_path) == identity, "Existing experiment requires unchanged --resume")
    else:
        check(not resume, "Cannot resume an experiment that has not started")
        write_once(identity_path, identity)
    completion_path = output / "completed.json"
    if completion_path.exists():
        result = read_json(completion_path)
        reports = [read_json(bound_path(root, b)) for b in result["validation_reports"]]
        validate_completion(root, recipe, identity, result, reports)
        check(reports[0] == epoch_zero_record(root, recipe, parent, identity), "Epoch-zero reuse differs")
        return result
    attempt = output / "attempts" / uuid.uuid4().hex
    attempt.mkdir(parents=True)
    began = time.perf_counter()
    write_once(attempt / "started.json", {"identity": identity, "resume": resume,
        "started_at_utc": datetime.now(timezone.utc).isoformat()})
    store, latest, losses, attempted_update = None, None, [], None
    log_path = attempt / "updates.jsonl"

    def log_event(record):
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({**record, "recorded_at_utc": datetime.now(timezone.utc).isoformat()}, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    try:
        write_once(attempt / "initial_resources.json", frozen.resources(output))
        states = sorted((output / "states").glob("update_*.pth"))
        prior = frozen.load_state(states[-1], identity, schedule) if states else None
        latest = states[-1] if states else None
        if prior:
            check(prior["epoch"] <= 5 and prior["completed_updates"] <= recipe["total_updates"], "Resume exceeds experiment budget")
            validate_augmentation_history(prior["losses"])
        restored = prior["completed_updates"] if prior else 0
        replayed = []
        for log in sorted((output / "attempts").glob("*/updates.jsonl")):
            for line in log.read_text(encoding="utf-8").splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue  # Preserve original power-loss fragments.
                if event.get("event") == "completed" and event["update"] > restored:
                    replayed.append({"attempt_log": log.relative_to(root).as_posix(), "update": event["update"],
                        "epoch": event["epoch"], "batch_index": event["batch_index"]})
        write_once(attempt / "restored.json", {"restored_updates": restored, "previous_unsaved_completed_updates": replayed,
            "previous_unsaved_completed_count": len(replayed), "identity": identity})
        baseline = epoch_zero(root, output, recipe, parent, identity)
        store = frozen.runtime.FrameStore(root, package, frozen.output_path(root, recipe["cache_root"]))
        cache = store.prepare()
        cache_path = output / "cache_preparation.json"
        if cache_path.exists():
            check({k: v for k, v in read_json(cache_path).items() if k != "elapsed_seconds"} ==
                  {k: v for k, v in cache.items() if k != "elapsed_seconds"}, "Verified cache changed")
        else:
            write_once(cache_path, cache)
        model, device, optimizer, bn_reference = frozen.adaptation.initialize(root, parent, nfhs)
        epoch, position = 0, 0
        if prior:
            check(set(bn_reference) == set(prior["batch_norm_reference"]) and
                  all(torch.equal(v.cpu(), prior["batch_norm_reference"][k]) for k, v in bn_reference.items()),
                  "Resume BatchNorm reference differs")
            model.load_state_dict(prior["model_state_dict"], strict=True)
            optimizer.load_state_dict(prior["optimizer_state_dict"])
            frozen.training.restore_rng(prior["rng_state"])
            epoch, position, losses = prior["epoch"], prior["batch_index"], prior["losses"]
        frozen.training.freeze_batch_norm(model)
        frozen.training.assert_batch_norm_unchanged(model, bn_reference)

        def save_state(e, p):
            nonlocal latest
            measured = frozen.resources(output)
            frozen.training.assert_batch_norm_unchanged(model, bn_reference)
            path = output / "states" / f"update_{len(losses):06d}.pth"
            if path.exists():
                saved = frozen.load_state(path, identity, schedule)
                check(saved["epoch"] == e and saved["batch_index"] == p, "Existing resume position differs")
                validate_augmentation_history(saved["losses"])
            else:
                frozen.training.save_checkpoint_once(path, frozen.state_payload(model, optimizer, identity, e, p, losses, bn_reference))
            latest = path
            measured_path = output / "resources" / (path.stem + ".json")
            if not measured_path.exists():
                write_once(measured_path, measured)
            frozen.retain_resume_states(root, output, latest)

        reports = []
        for path in sorted((output / "validation").glob("epoch_*.json")):
            report = read_json(path)
            validate_report(report, identity)
            check(report["epoch"] == len(reports) and report["epoch"] <= epoch, "Validation history differs from resume progress")
            bound_path(root, report["checkpoint"])
            reports.append(report)
        check(reports and reports[0] == baseline, "Epoch-zero provenance differs")
        if epoch == 0:
            save_state(0, 0)
        triplets = {t["triplet_id"]: t for t in package["training_triplets"]}
        for spec in schedule["epochs"][:5]:
            e, batches = spec["epoch"], spec["batches"]
            if e < epoch or reports[-1]["epoch"] >= e:
                continue
            check(reports[-1]["epoch"] == e - 1, "Validation history has a gap")
            start = position if e == epoch else 0
            frozen.training.freeze_batch_norm(model)
            frozen.training.assert_batch_norm_unchanged(model, bn_reference)
            for index in range(start, len(batches)):
                attempted_update = len(losses) + 1
                log_event({"event": "started", "update": attempted_update, "epoch": e,
                    "batch_index": index + 1, "triplet_ids": batches[index]})
                augmented = [augmentation.augment_example(store.example(triplets[key]), seed=1234,
                    epoch=e, batch_index=index + 1, sample_index=j, triplet_id=key)
                    for j, key in enumerate(batches[index])]
                examples, audits = zip(*augmented)
                inputs, targets, masks = (torch.stack([x[j] for x in examples]).to(device) for j in range(3))
                loss, gradients = frozen.training.training_step(model, optimizer, inputs, targets, masks)
                losses.append({"update": len(losses) + 1, "epoch": e, "batch_index": index + 1,
                    "triplet_ids": batches[index], "loss": loss, "gradient_parameter_count": gradients,
                    "augmentation": list(audits)})
                log_event({"event": "completed", **losses[-1]})
                del inputs, targets, masks, examples, audits, augmented
                if len(losses) % 25 == 0 or index + 1 == len(batches):
                    save_state(e, index + 1)
                    print(f"epoch {e} batch {index+1}/{len(batches)} update {len(losses)} loss {loss:.6f}", flush=True)
            cp = frozen.checkpoint_epoch(root, output, identity, model, e, len(losses))
            reports.append(frozen.validation(root, output, identity, model, device, store, package, e, cp))
            frozen.training.assert_batch_norm_unchanged(model, bn_reference)
            selected = frozen.policy.choose_checkpoint(reports)
            print(f"epoch {e} validated; selected {selected['selected_epoch']}", flush=True)
            epoch, position = e, len(batches)
        result = completion_record(root, output, recipe, identity, reports, losses, latest,
                                   time.perf_counter() - began, frozen.resources(output))
        validate_completion(root, recipe, identity, result, reports)
        write_once(completion_path, result)
        write_once(attempt / "completed.json", {"completion": binding(root, completion_path)})
        return result
    except BaseException as error:
        write_once(attempt / "failed.json", {"identity": identity, "error_type": type(error).__name__,
            "error": str(error), "traceback": traceback.format_exc(), "elapsed_seconds": time.perf_counter() - began,
            "resume_checkpoint": binding(root, latest) if latest else None,
            "completed_updates_in_memory": len(losses), "last_attempted_update": attempted_update,
            "attempt_update_log": binding(root, log_path) if log_path.exists() else None,
            "retry_requires_resume": True})
        raise
    finally:
        if store is not None:
            store.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe", required=True)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    check(not args.resume or args.run, "--resume requires --run")
    root = Path(__file__).resolve().parents[2]
    if args.run:
        result = execute(root, args.recipe, resume=args.resume)
        print(json.dumps({k: result[k] for k in ("status", "completed_epochs", "completed_updates", "selected_checkpoint")}))
    else:
        *_, identity = preflight(root, args.recipe)
        print(json.dumps({"status": "preflight_only_no_model_execution", "identity": identity,
            "training_triplets": 3103, "schedule_epochs": 5, "total_updates": 7760}))


if __name__ == "__main__":
    main()
