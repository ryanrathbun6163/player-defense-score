"""Two matched 768px continuation epochs with coherent spatial augmentation.

The parent Adam/RNG/BatchNorm state, example schedule, mirror/brightness draws,
native validation and recovery helpers are retained from completed controls.
Only the separately keyed training spatial transform is new.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
import traceback
import uuid

import torch

from . import wasb_continuation_training as continuation
from . import wasb_spatial_augmentation as spatial
from .continuation_owned_guard import verify_owned_worker
from .completion_training_runtime import atomic_write_once as write_once, binding
from .wasb_experiment import bound_path, canonical, read_json

source_training = continuation.source_training
frozen = continuation.frozen
resolution = continuation.resolution
check = frozen.check
trees_equal = continuation.trees_equal
load_source_state = continuation.load_source_state
source_report = continuation.source_report
checkpoint_epoch = continuation.checkpoint_epoch
retain_resume_states = continuation.retain_resume_states
validate_optimizer = continuation.validate_optimizer

MODULE = "src.ball_tracking.wasb_spatial_training"
SCHEMA = "wasb_spatial_training_result/v0.1"
RECIPE_SCHEMA = "wasb_spatial_recipe/v0.1"
OUTPUT_ROOT = "data/outputs/ball_tracking/wasb_spatial_v0_1/fit_v0_1"
CACHE_ROOT = continuation.CACHE_ROOT
RESOLUTION = continuation.RESOLUTION
TRAINING = dict(source_training.TRAINING)
LEARNING_RATE_POLICY = continuation.ARMS["constant"]


def preflight(root, recipe_path):
    """Consume real frozen parent/control metadata; no model or image loads."""
    root = Path(root).resolve()
    path = (root / recipe_path).resolve()
    recipe = read_json(path)
    check(recipe["schema_version"] == RECIPE_SCHEMA and recipe["status"] == "frozen_before_model_execution",
          "Spatial recipe must be frozen")
    control_recipe, parent, package, schedule, nfhs, control_identity, source = continuation.preflight(
        root, bound_path(root, recipe["matched_control_recipe"]), "constant")
    control_path = bound_path(root, recipe["matched_control_completed"])
    check(control_path == root / control_recipe["arms"]["constant"]["output_root"] / "completed.json",
          "Matched constant control path differs")
    control = read_json(control_path)
    control_reports = [read_json(bound_path(root, link)) for link in control["validation_reports"]]
    continuation.validate_completion(root, control_recipe, control_identity, control, control_reports)
    for key in ("source_recipe", "source_completed", "source_state", "source_cache_preparation", "source_evaluation", "cache_root", "runtime", "resolution", "augmentation"):
        check(recipe[key] == control_recipe[key], "Spatial/control shared input differs: " + key)
    check(recipe["training"] == TRAINING and recipe["spatial_augmentation"] == spatial.POLICY,
          "Spatial training policy differs")
    check(recipe["start_epoch"] == 5 and recipe["end_epoch"] == 7 and recipe["initial_updates"] == 7760
          and recipe["additional_updates"] == 3104 and recipe["total_updates"] == 10864,
          "Spatial two-epoch budget differs")
    check([e["epoch"] for e in schedule["epochs"][5:7]] == [6,7]
          and sum(len(e["batches"]) for e in schedule["epochs"][5:7]) == recipe["additional_updates"],
          "Spatial schedule differs from matched control")
    check(recipe["output_root"] == OUTPUT_ROOT and recipe["protected_evaluation_authorized"] is False
          and recipe["new_labels"] == 0, "Spatial output/label/protected scope differs")
    frozen.output_path(root, recipe["output_root"])
    bound_path(root, recipe["execution_plan"])
    check(bool(recipe["user_authority"]["approval"].strip()), "Missing spatial experiment authority")
    code = {link["path"]: bound_path(root, link) for link in recipe["code_bindings"]}
    for required in (Path(__file__).resolve(), Path(spatial.__file__).resolve(),
                     root / "src/ball_tracking/continuation_owned_guard.py", root / "src/ball_tracking/gpu_supervision.py"):
        check(required.relative_to(root).as_posix() in code, "Missing spatial execution dependency")
    identity = {**control_identity, "recipe":binding(root, path), "arm":"spatial",
        "executed_epochs_sha256":canonical(schedule["epochs"][5:7]),
        "learning_rate_policy":LEARNING_RATE_POLICY,
        "matched_control_recipe":recipe["matched_control_recipe"],
        "matched_control_completed":recipe["matched_control_completed"],
        "spatial_augmentation_sha256":canonical(spatial.POLICY)}
    return recipe, parent, package, schedule, nfhs, identity, source


def validate_report(report, identity, *, allow_reused=False):
    if "reused_validation" in report:
        continuation.validate_report(report, identity, allow_reused=allow_reused)
    else:
        check(report["epoch"] in (6,7), "Fresh spatial epoch outside six and seven")
        source_training.validate_report(report, identity)


def validate_history(losses, recipe, identity, original_losses, package):
    continuation.validate_history(losses, recipe, identity, original_losses)
    triplets = {row["triplet_id"]:row for row in package["training_triplets"]}
    blocks = {row["block_id"]:row for row in package["training_blocks"]}
    for row in losses[recipe["initial_updates"]:]:
        audits = row.get("spatial_augmentation")
        check(isinstance(audits, list) and len(audits) == len(row["triplet_ids"]), "Spatial audit census differs")
        for sample_index, (key, audit) in enumerate(zip(row["triplet_ids"], audits, strict=True)):
            triplet = triplets[key]
            spatial.validate_audit(audit, triplet=triplet, block=blocks[triplet["block_id"]], seed=1234,
                epoch=row["epoch"], batch_index=row["batch_index"], sample_index=sample_index, triplet_id=key)


def validate_completion(root, recipe, identity, result, reports):
    initial, final = recipe["initial_updates"], recipe["total_updates"]
    check(result["schema_version"] == SCHEMA and result["status"] == "completed" and result["identity"] == identity
          and result["arm"] == "spatial" and result["completed_epochs"] == recipe["end_epoch"]
          and result["new_completed_epochs"] == 2 and result["completed_updates"] == final
          and result["initial_updates"] == initial and result["additional_updates"] == result["optimizer_updates"] == final-initial
          and result["new_validation_epochs"] == [6,7] and result["epoch_five_reused"] is True
          and result["source_completed"] == identity["source_completed"] and result["source_state"] == identity["source_state"]
          and result["source_checkpoint"] == identity["source_checkpoint"]
          and result["matched_control_completed"] == identity["matched_control_completed"]
          and result["initial_optimizer"] == "continued_Adam_with_parent_moments_and_steps"
          and result["learning_rate_policy"] == LEARNING_RATE_POLICY and result["training"] == TRAINING
          and result["resolution"] == RESOLUTION and result["augmentation"] == source_training.augmentation.POLICY
          and result["spatial_augmentation"] == spatial.POLICY
          and result["selection_applied"] is False and result["selected_checkpoint"] is None
          and result["model_adopted"] is False and result["ball_phase_accepted"] is False
          and result["protected_evaluation_authorized"] is False and result["post_selection_references_used"] is False
          and result["stop_reason"] == "fixed_two_additional_epochs", "Spatial completion contract differs")
    check([r["epoch"] for r in reports] == [5,6,7] and reports[0] == source_report(root, identity),
          "Spatial validation/source transport differs")
    for report in reports:
        validate_report(report, identity, allow_reused=report["epoch"] == 5)
        bound_path(root, report["checkpoint"])
    check(result["checkpoints"] == [r["checkpoint"] for r in reports[1:]] and result["final_checkpoint"] == reports[-1]["checkpoint"],
          "Spatial checkpoint inventory differs")
    bound_path(root, result["resume_checkpoint"])
    initial_path = bound_path(root, result["initial_continuation_state"])
    check(initial_path == root / recipe["output_root"] / "states" / f"update_{initial:06d}.pth",
          "Spatial initial handoff path differs")


def audit_completed_result(root, recipe_path):
    root = Path(root).resolve()
    recipe, _, _, _, _, identity, _ = preflight(root, recipe_path)
    path = frozen.output_path(root, recipe["output_root"]) / "completed.json"
    result = read_json(path)
    reports = [read_json(bound_path(root, link)) for link in result["validation_reports"]]
    validate_completion(root, recipe, identity, result, reports)
    return result, {"status":"passed", "training_result":binding(root, path), "arm":"spatial",
        "completed_epochs":7, "new_completed_epochs":2, "completed_updates":result["completed_updates"],
        "additional_updates":result["additional_updates"], "validation_reports_checked":3,
        "epoch_five_reused":True, "resolution":RESOLUTION, "model_loaded":False,
        "source_pixels_read":False, "protected_evaluation_authorized":False}


def execute(root, recipe_path, *, resume=False, monitor):
    root = Path(root).resolve()
    context = preflight(root, recipe_path)
    ownership = verify_owned_worker(root, root / monitor, MODULE, sys.argv[1:])
    output = frozen.output_path(root, context[0]["output_root"])
    output.mkdir(parents=True, exist_ok=True)
    with frozen.training.training_lock(output / "training.lock"):
        return _execute_locked(root, *context, output, resume, ownership)


def _execute_locked(root, recipe, parent, package, schedule, nfhs, identity, source, output, resume, ownership):
    identity_path, completion_path = output / "identity.json", output / "completed.json"
    if identity_path.exists():
        check(resume and read_json(identity_path) == identity, "Existing arm requires unchanged --resume")
    else:
        check(not resume, "Cannot resume an unstarted arm")
        write_once(identity_path, identity)
    if completion_path.exists():
        result = read_json(completion_path)
        validate_completion(root, recipe, identity, result, [read_json(bound_path(root, b)) for b in result["validation_reports"]])
        return result
    attempt = output / "attempts" / uuid.uuid4().hex
    attempt.mkdir(parents=True)
    began = time.perf_counter()
    write_once(attempt / "started.json", {"identity": identity, "resume": resume, "owned_worker_verification": ownership, "started_at_utc": datetime.now(timezone.utc).isoformat()})
    store, latest, losses, attempted_update = None, None, [], None
    log_path = attempt / "updates.jsonl"
    def log_event(record):
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({**record, "recorded_at_utc": datetime.now(timezone.utc).isoformat()}, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    try:
        source_state = load_source_state(root, recipe, identity, schedule)
        original_losses = deepcopy(source_state["losses"])
        states = sorted((output / "states").glob("update_*.pth"))
        latest = states[-1] if states else None
        prior = frozen.load_state(latest, identity, schedule) if latest else source_state
        check(recipe["start_epoch"] <= prior["epoch"] <= recipe["end_epoch"], "Resume epoch outside continuation budget")
        validate_history(prior["losses"], recipe, identity, original_losses, package)
        restored = prior["completed_updates"]
        replayed = []
        for log in sorted((output / "attempts").glob("*/updates.jsonl")):
            for line in log.read_text().splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("event") == "completed" and event["update"] > restored:
                    replayed.append({"attempt_log": log.relative_to(root).as_posix(), "update": event["update"],
                                     "epoch": event["epoch"], "batch_index": event["batch_index"]})
        write_once(attempt / "restored.json", {"restored_updates": restored, "source_state": recipe["source_state"],
            "restored_from": binding(root, latest) if latest else recipe["source_state"],
            "previous_unsaved_completed_updates": replayed, "previous_unsaved_completed_count": len(replayed), "identity": identity})
        store = resolution.FrameStore(root, package, frozen.output_path(root, recipe["cache_root"]))
        cache = store.prepare()
        original_cache = read_json(bound_path(root, recipe["source_cache_preparation"]))
        check({k:v for k,v in cache.items() if k != "elapsed_seconds"} ==
              {k:v for k,v in original_cache.items() if k != "elapsed_seconds"}, "Continuation cache differs from parent")
        if not (output / "cache_preparation.json").exists():
            write_once(output / "cache_preparation.json", cache)
        model, device, optimizer, bn_reference = frozen.adaptation.initialize(root, parent, nfhs)
        check(trees_equal(bn_reference, prior["batch_norm_reference"]), "Parent BatchNorm reference differs")
        model.load_state_dict(prior["model_state_dict"], strict=True)
        optimizer.load_state_dict(prior["optimizer_state_dict"])
        check(trees_equal(optimizer.state_dict(), prior["optimizer_state_dict"]), "Optimizer history did not restore exactly")
        expected_lr = TRAINING["learning_rate"]
        validate_optimizer(optimizer, expected_lr, restored)
        frozen.training.restore_rng(prior["rng_state"])
        check(trees_equal(frozen.training.rng_state(), prior["rng_state"]), "Training RNG did not restore exactly")
        epoch, position, losses = prior["epoch"], prior["batch_index"], deepcopy(prior["losses"])
        frozen.training.freeze_batch_norm(model)
        frozen.training.assert_batch_norm_unchanged(model, bn_reference)
        write_once(attempt / "initial_resources.json", frozen.resources(output))
        def save_state(e, p):
            nonlocal latest
            frozen.training.assert_batch_norm_unchanged(model, bn_reference)
            path = output / "states" / f"update_{len(losses):06d}.pth"
            if path.exists():
                saved = frozen.load_state(path, identity, schedule)
                check(saved["epoch"] == e and saved["batch_index"] == p, "Existing resume position differs")
                validate_history(saved["losses"], recipe, identity, original_losses, package)
            else:
                frozen.training.save_checkpoint_once(path, frozen.state_payload(model, optimizer, identity, e, p, losses, bn_reference))
            latest = path
            resource_path = output / "resources" / (path.stem + ".json")
            if not resource_path.exists():
                write_once(resource_path, frozen.resources(output))
            retain_resume_states(root, output, latest, recipe["initial_updates"])
        expected_source = source_report(root, identity)
        reused_path = output / "validation/epoch_005.json"
        if reused_path.exists():
            check(read_json(reused_path) == expected_source, "Reused source report changed")
        else:
            write_once(reused_path, expected_source)
        reports = [expected_source]
        for path in sorted((output / "validation").glob("epoch_*.json")):
            report = read_json(path)
            if report["epoch"] == 5:
                continue
            validate_report(report, identity)
            check(report["epoch"] == reports[-1]["epoch"] + 1 and report["epoch"] <= epoch,
                  "Validation history differs from durable continuation progress")
            bound_path(root, report["checkpoint"])
            reports.append(report)
        if latest is None:
            save_state(epoch, position)
        triplets = {row["triplet_id"]:row for row in package["training_triplets"]}
        for spec in schedule["epochs"][recipe["start_epoch"]:recipe["end_epoch"]]:
            e, batches = spec["epoch"], spec["batches"]
            if e < epoch or reports[-1]["epoch"] >= e:
                continue
            check(reports[-1]["epoch"] == e - 1, "Continuation validation history has a gap")
            start = position if e == epoch else 0
            frozen.training.freeze_batch_norm(model)
            for index in range(start, len(batches)):
                attempted_update = len(losses) + 1
                local = attempted_update - recipe["initial_updates"]
                lr = TRAINING["learning_rate"]
                for group in optimizer.param_groups:
                    group["lr"] = lr
                log_event({"event":"started", "update":attempted_update, "continuation_update":local,
                    "learning_rate":lr, "epoch":e, "batch_index":index + 1, "triplet_ids":batches[index]})
                augmented = [spatial.augment_example(store.example(triplets[key]), triplet=triplets[key],
                    block=store.blocks[triplets[key]["block_id"]], seed=1234, epoch=e,
                    batch_index=index + 1, sample_index=j, triplet_id=key) for j, key in enumerate(batches[index])]
                examples, audits = zip(*augmented)
                inputs, targets, masks = (torch.stack([x[j] for x in examples]).to(device) for j in range(3))
                loss, gradients = frozen.training.training_step(model, optimizer, inputs, targets, masks)
                losses.append({"update":len(losses) + 1, "continuation_update":local, "learning_rate":lr,
                    "epoch":e, "batch_index":index + 1, "triplet_ids":batches[index], "loss":loss,
                    "gradient_parameter_count":gradients, "augmentation":[a["augmentation"] for a in audits],
                    "spatial_augmentation":[a["spatial_augmentation"] for a in audits]})
                log_event({"event":"completed", **losses[-1]})
                del inputs, targets, masks, examples, audits, augmented
                if local % TRAINING["checkpoint_interval_updates"] == 0 or index + 1 == len(batches):
                    save_state(e, index + 1)
                    print(f"{identity['arm']} epoch {e} batch {index + 1}/{len(batches)} cumulative {len(losses)} new {local} lr {lr:.9g} loss {loss:.6g}", flush=True)
            cp = checkpoint_epoch(root, output, identity, model, e, len(losses))
            reports.append(source_training.validation(root, output, identity, model, device, store, package, e, cp))
            frozen.training.assert_batch_norm_unchanged(model, bn_reference)
            print(f"{identity['arm']} epoch {e} validated; fixed continuation budget continues", flush=True)
            epoch, position = e, len(batches)
        result = {"schema_version":SCHEMA, "status":"completed", "identity":identity, "arm":identity["arm"],
            "completed_epochs":recipe["end_epoch"], "new_completed_epochs":2, "completed_updates":len(losses),
            "initial_updates":recipe["initial_updates"], "additional_updates":len(losses) - recipe["initial_updates"],
            "optimizer_updates":len(losses) - recipe["initial_updates"], "source_completed":identity["source_completed"],
            "source_state":identity["source_state"], "source_checkpoint":identity["source_checkpoint"],
            "initial_optimizer":"continued_Adam_with_parent_moments_and_steps", "learning_rate_policy":identity["learning_rate_policy"],
            "selection_applied":False, "selected_checkpoint":None, "model_adopted":False,
            "final_checkpoint":reports[-1]["checkpoint"], "checkpoints":[r["checkpoint"] for r in reports[1:]],
            "validation_reports":[binding(root, output / "validation" / f"epoch_{r['epoch']:03d}.json") for r in reports],
            "resume_checkpoint":binding(root, latest), "stop_reason":"fixed_two_additional_epochs",
            "initial_continuation_state":binding(root, output / "states" / f"update_{recipe['initial_updates']:06d}.pth"),
            "epoch_five_reused":True, "new_validation_epochs":[6,7], "training":TRAINING,
            "augmentation":source_training.augmentation.POLICY, "spatial_augmentation":spatial.POLICY,
            "matched_control_completed":identity["matched_control_completed"], "resolution":RESOLUTION,
            "attempt_elapsed_seconds":time.perf_counter() - began, "resources":frozen.resources(output),
            "protected_evaluation_authorized":False, "post_selection_references_used":False,
            "heatmaps_retained":False, "ball_phase_accepted":False}
        validate_completion(root, recipe, identity, result, reports)
        write_once(completion_path, result)
        write_once(attempt / "completed.json", {"completion":binding(root, completion_path)})
        return result
    except BaseException as error:
        write_once(attempt / "failed.json", {"identity":identity, "error_type":type(error).__name__, "error":str(error),
            "traceback":traceback.format_exc(), "elapsed_seconds":time.perf_counter() - began,
            "resume_checkpoint":binding(root, latest) if latest else None, "source_state":recipe["source_state"],
            "completed_updates_in_memory":len(losses), "last_attempted_update":attempted_update,
            "attempt_update_log":binding(root, log_path) if log_path.exists() else None, "retry_requires_resume":True})
        raise
    finally:
        if store is not None:
            store.close()



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe", required=True)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--monitor")
    args = parser.parse_args()
    check(not args.resume or args.run, "--resume requires --run")
    check(bool(args.monitor) == bool(args.run), "--monitor is required only for --run")
    root = Path(__file__).resolve().parents[2]
    if args.run:
        result = execute(root, args.recipe, resume=args.resume, monitor=args.monitor)
        print(json.dumps({key:result[key] for key in ("status","arm","completed_epochs","completed_updates","additional_updates")}))
    else:
        *_, identity, _ = preflight(root, args.recipe)
        print(json.dumps({"status":"preflight_only_no_model_execution", "identity":identity,
                          "new_epochs":[6,7], "new_updates":3104}))


if __name__ == "__main__":
    main()
