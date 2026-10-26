"""Matched 768px continuations of saved epoch five, preserving Adam and RNG.

The two arms use the same absolute epochs six through ten. Only their declared
per-update learning-rate function differs. No earlier experiment is modified.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import time
import traceback
import uuid

import torch

from . import completion_resolution_training as source_training
from . import completion_training as frozen
from . import wasb_resolution as resolution
from .completion_training_runtime import atomic_write_once as write_once, binding
from .wasb_experiment import bound_path, canonical, read_json

check = frozen.check
SCHEMA = "wasb_continuation_training_result/v0.1"
RECIPE_SCHEMA = "wasb_continuation_recipe/v0.1"
OUTPUT_ROOT = "data/outputs/ball_tracking/wasb_continuation_v0_1"
CACHE_ROOT = source_training.CACHE_ROOT
RESOLUTION = source_training.RESOLUTION
TRAINING = {**source_training.TRAINING, "learning_rate": "per_arm_schedule",
            "scheduler": "deterministic_continuation_step_function"}
ARMS = {"constant": {"kind": "constant", "initial": .0001, "final": .0001},
        "cosine": {"kind": "cosine", "initial": .0001, "final": .00001}}


def learning_rate(policy, update, total):
    """One-based continuation update; endpoints are exact and resume-independent."""
    check(type(update) is int and type(total) is int and total >= 2 and 1 <= update <= total,
          "Learning-rate update outside continuation budget")
    check(policy in ARMS.values(), "Unknown learning-rate policy")
    if update == 1 or policy["kind"] == "constant":
        return policy["initial"]
    if update == total:
        return policy["final"]
    return policy["final"] + (policy["initial"] - policy["final"]) * .5 * (1 + math.cos(math.pi * (update - 1) / (total - 1)))


def preflight(root, recipe_path, arm):
    """Check metadata/bytes only; never load a model or perform a forward call."""
    root = Path(root).resolve()
    path = (root / recipe_path).resolve()
    recipe = read_json(path)
    check(recipe["schema_version"] == RECIPE_SCHEMA and recipe["status"] == "frozen_before_model_execution",
          "Continuation recipe must be frozen")
    check(arm in ARMS and set(recipe["arms"]) == set(ARMS), "Unknown or missing continuation arm")
    source_recipe, parent, package, schedule, nfhs, source_identity = source_training.preflight(
        root, bound_path(root, recipe["source_recipe"]))
    source_path = bound_path(root, recipe["source_completed"])
    check(source_path == root / source_recipe["output_root"] / "completed.json", "Source completion location differs")
    source = read_json(source_path)
    reports = [read_json(bound_path(root, link)) for link in source["validation_reports"]]
    source_training.validate_completion(root, source_recipe, source_identity, source, reports)
    check(recipe["source_state"] == source["resume_checkpoint"], "Continuation must use complete parent optimizer state")
    bound_path(root, recipe["source_state"])
    check(recipe["runtime"] == source_recipe["runtime"] and recipe["training"] == TRAINING
          and recipe["resolution"] == RESOLUTION and recipe["augmentation"] == source_training.augmentation.POLICY,
          "Continuation scientific policy differs")
    check(recipe["start_epoch"] == 5 and recipe["end_epoch"] == 10 and recipe["initial_updates"] == 7760
          and recipe["additional_updates"] == 7760 and recipe["total_updates"] == 15520,
          "Continuation budget differs")
    check([e["epoch"] for e in schedule["epochs"][5:10]] == list(range(6, 11))
          and sum(len(e["batches"]) for e in schedule["epochs"][5:10]) == recipe["additional_updates"],
          "Continuation schedule differs")
    check(recipe["cache_root"] == CACHE_ROOT and recipe["protected_evaluation_authorized"] is False
          and recipe["new_labels"] == 0, "Cache, labels or protected boundary differs")
    bound_path(root, recipe["execution_plan"])
    check(bool(recipe["user_authority"]["approval"].strip()), "Missing continuation authority")
    code = {entry["path"]: bound_path(root, entry) for entry in recipe["code_bindings"]}
    check(Path(__file__).resolve().relative_to(root).as_posix() in code
          and "src/ball_tracking/gpu_supervision.py" in code, "Missing runner/supervisor binding")
    for name, policy in ARMS.items():
        expected = f"{OUTPUT_ROOT}/{name}/fit_v0_1"
        check(recipe["arms"][name]["learning_rate"] == policy and recipe["arms"][name]["output_root"] == expected,
              "Arm policy or output scope differs")
        frozen.output_path(root, expected)
    cache_path = bound_path(root, recipe["source_cache_preparation"])
    check(cache_path == root / source_recipe["output_root"] / "cache_preparation.json", "Source cache receipt differs")
    cache = read_json(cache_path)
    check(cache["resolution"] == RESOLUTION and len(cache["blocks"]) == 38 and cache["unique_block_frames"] == 4439,
          "Existing cache census differs")
    for link in cache["blocks"]:
        receipt_path = bound_path(root, link)
        check(receipt_path.is_relative_to(root / CACHE_ROOT), "Cache receipt escaped original cache")
        receipt = read_json(receipt_path)
        payload = root / receipt["warped_frames"]["path"]
        check(payload.is_file() and payload.stat().st_size == receipt["warped_frames"]["bytes"],
              "Existing cache payload absent; rebuilding is not authorized here")
    identity = {"recipe": binding(root, path), "arm": arm, "source_identity": source_identity,
        "source_completed": recipe["source_completed"], "source_state": recipe["source_state"],
        "source_checkpoint": source["final_checkpoint"], "source_validation_report": source["validation_reports"][-1],
        "package_sha256": canonical(package), "schedule_sha256": canonical(schedule),
        "executed_epochs_sha256": canonical(schedule["epochs"][5:10]),
        "learning_rate_policy": recipe["arms"][arm]["learning_rate"], "resolution": RESOLUTION}
    return recipe, parent, package, schedule, nfhs, identity, source


def source_report(root, identity):
    report = deepcopy(read_json(bound_path(root, identity["source_validation_report"])))
    source_training.validate_report(report, identity["source_identity"])
    check(report["epoch"] == 5 and report["checkpoint"] == identity["source_checkpoint"], "Source epoch-five report differs")
    report["identity"] = identity
    report["reused_validation"] = {"source_report": identity["source_validation_report"],
        "source_identity": identity["source_identity"], "new_model_calls": 0}
    return report


def validate_report(report, identity, *, allow_reused=False):
    if "reused_validation" in report:
        check(allow_reused and report["epoch"] == 5 and report["identity"] == identity
              and report["checkpoint"] == identity["source_checkpoint"]
              and report["reused_validation"] == {"source_report": identity["source_validation_report"],
                  "source_identity": identity["source_identity"], "new_model_calls": 0}, "Reused epoch-five report differs")
        original = {k: v for k, v in report.items() if k != "reused_validation"}
        original["identity"] = identity["source_identity"]
        source_training.validate_report(original, identity["source_identity"])
    else:
        check(6 <= report["epoch"] <= 10, "Fresh continuation epoch outside six through ten")
        source_training.validate_report(report, identity)


def validate_optimizer(optimizer, expected_lr, completed):
    check(isinstance(optimizer, torch.optim.Adam) and bool(optimizer.state), "Restored nonempty Adam history required")
    for group in optimizer.param_groups:
        check(group["lr"] == expected_lr and group["betas"] == (.9, .999) and group["eps"] == 1e-8
              and group["weight_decay"] == 0 and group.get("amsgrad", False) is False, "Continuation Adam settings differ")
    check(all(float(state["step"]) == completed for state in optimizer.state.values()), "Adam step history differs")


def trees_equal(left, right):
    if isinstance(left, torch.Tensor):
        return isinstance(right, torch.Tensor) and left.dtype == right.dtype and torch.equal(left.cpu(), right.cpu())
    if isinstance(left, dict):
        return isinstance(right, dict) and left.keys() == right.keys() and all(trees_equal(v, right[k]) for k, v in left.items())
    if isinstance(left, (tuple, list)):
        return type(left) is type(right) and len(left) == len(right) and all(trees_equal(a, b) for a, b in zip(left, right))
    return left == right


def validate_history(losses, recipe, identity, original_losses):
    initial = recipe["initial_updates"]
    check(losses[:initial] == original_losses and initial <= len(losses) <= recipe["total_updates"], "Parent history or budget differs")
    source_training.validate_augmentation_history(losses)
    for local, row in enumerate(losses[initial:], 1):
        check(row["continuation_update"] == local
              and row["learning_rate"] == learning_rate(identity["learning_rate_policy"], local, recipe["additional_updates"]),
              "Saved learning-rate/update history differs")


def load_source_state(root, recipe, identity, schedule):
    state = frozen.load_state(bound_path(root, recipe["source_state"]), identity["source_identity"], schedule)
    check(state["epoch"] == recipe["start_epoch"] and state["completed_updates"] == recipe["initial_updates"]
          and state["batch_index"] == len(schedule["epochs"][recipe["start_epoch"] - 1]["batches"]),
          "Parent state is not completed epoch five")
    checkpoint = torch.load(bound_path(root, identity["source_checkpoint"]), map_location="cpu", weights_only=True)
    check(set(checkpoint) == {"model_state_dict"} and trees_equal(checkpoint["model_state_dict"], state["model_state_dict"]),
          "Parent state and final model differ")
    source_training.validate_augmentation_history(state["losses"])
    return state


def validate_completion(root, recipe, identity, result, reports):
    initial, final = recipe["initial_updates"], recipe["total_updates"]
    check(result["schema_version"] == SCHEMA and result["status"] == "completed" and result["identity"] == identity
          and result["arm"] == identity["arm"] and result["completed_epochs"] == recipe["end_epoch"]
          and result["new_completed_epochs"] == 5 and result["completed_updates"] == final
          and result["initial_updates"] == initial and result["additional_updates"] == result["optimizer_updates"] == final - initial
          and result["new_validation_epochs"] == list(range(6, 11)) and result["epoch_five_reused"] is True
          and result["source_completed"] == identity["source_completed"] and result["source_state"] == identity["source_state"]
          and result["initial_optimizer"] == "continued_Adam_with_parent_moments_and_steps"
          and result["learning_rate_policy"] == identity["learning_rate_policy"] and result["training"] == TRAINING
          and result["resolution"] == RESOLUTION and result["augmentation"] == source_training.augmentation.POLICY
          and result["selection_applied"] is False and result["selected_checkpoint"] is None
          and result["model_adopted"] is False and result["ball_phase_accepted"] is False
          and result["protected_evaluation_authorized"] is False and result["post_selection_references_used"] is False
          and result["stop_reason"] == "fixed_five_additional_epochs", "Continuation completion contract differs")
    check([r["epoch"] for r in reports] == list(range(5, 11)) and reports[0] == source_report(root, identity),
          "Continuation validation/source transport differs")
    for report in reports:
        validate_report(report, identity, allow_reused=report["epoch"] == 5)
        bound_path(root, report["checkpoint"])
    check(result["checkpoints"] == [r["checkpoint"] for r in reports[1:]] and result["final_checkpoint"] == reports[-1]["checkpoint"],
          "Continuation checkpoint inventory differs")
    bound_path(root, result["resume_checkpoint"])
    initial_path = bound_path(root, result["initial_continuation_state"])
    check(initial_path == root / recipe["arms"][identity["arm"]]["output_root"] / "states" / f"update_{initial:06d}.pth",
          "Initial continuation handoff path differs")


def audit_completed_result(root, recipe_path, arm):
    root = Path(root).resolve()
    recipe, _, _, _, _, identity, _ = preflight(root, recipe_path, arm)
    path = frozen.output_path(root, recipe["arms"][arm]["output_root"]) / "completed.json"
    result = read_json(path)
    reports = [read_json(bound_path(root, link)) for link in result["validation_reports"]]
    validate_completion(root, recipe, identity, result, reports)
    return result, {"status": "passed", "training_result": binding(root, path), "arm": arm,
        "completed_epochs": 10, "new_completed_epochs": 5, "completed_updates": result["completed_updates"],
        "additional_updates": result["additional_updates"], "validation_reports_checked": 6,
        "epoch_five_reused": True, "resolution": RESOLUTION, "model_loaded": False,
        "source_pixels_read": False, "protected_evaluation_authorized": False}


def checkpoint_epoch(root, output, identity, model, epoch, updates):
    """Consume an already durable model/sidecar after an interrupted validation."""
    path = output / "checkpoints" / f"epoch_{epoch:03d}.pth"
    sidecar = path.with_suffix(".json")
    if sidecar.exists():
        expected = {"identity": identity, "epoch": epoch, "completed_updates": updates, "checkpoint": binding(root, path)}
        check(read_json(sidecar) == expected, "Existing checkpoint sidecar differs")
        saved = torch.load(path, map_location="cpu", weights_only=True)
        check(set(saved) == {"model_state_dict"} and trees_equal(saved["model_state_dict"], model.state_dict()),
              "Existing checkpoint weights differ")
        return expected["checkpoint"]
    return frozen.checkpoint_epoch(root, output, identity, model, epoch, updates)


def retain_resume_states(root, output, latest, initial_updates):
    """Preserve the arm's exact parent handoff, latest state and failure citations."""
    states = (output / "states").resolve()
    check(states.is_relative_to(output.resolve()), "Continuation state directory escaped run")
    keep = {latest.resolve(), (states / f"update_{initial_updates:06d}.pth").resolve()}
    for failure in (output / "attempts").glob("*/failed.json"):
        cited = read_json(failure).get("resume_checkpoint")
        if cited:
            keep.add((root / cited["path"]).resolve())
    for old in sorted(states.glob("update_*.pth")):
        check(old.resolve().parent == states, "Continuation state cleanup escaped run")
        if old.resolve() in keep:
            continue
        receipt = output / "retention" / (old.stem + ".json")
        if receipt.exists():
            record = read_json(receipt)
            check(record["removed_state"] == binding(root, old), "Interrupted state cleanup differs")
            bound_path(root, record["replacement"])
        else:
            write_once(receipt, {"status":"superseded_optimizer_state_removed", "removed_state":binding(root, old),
                "replacement":binding(root, latest), "epoch_model_checkpoints_retained":True,
                "initial_continuation_state_retained":True})
        old.unlink()


def execute(root, recipe_path, arm, *, resume=False):
    root = Path(root).resolve()
    context = preflight(root, recipe_path, arm)
    output = frozen.output_path(root, context[0]["arms"][arm]["output_root"])
    output.mkdir(parents=True, exist_ok=True)
    with frozen.training.training_lock(output / "training.lock"):
        return _execute_locked(root, *context, output, resume)


def _execute_locked(root, recipe, parent, package, schedule, nfhs, identity, source, output, resume):
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
    write_once(attempt / "started.json", {"identity": identity, "resume": resume, "started_at_utc": datetime.now(timezone.utc).isoformat()})
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
        validate_history(prior["losses"], recipe, identity, original_losses)
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
        expected_lr = learning_rate(identity["learning_rate_policy"], max(1, restored - recipe["initial_updates"]), recipe["additional_updates"])
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
                validate_history(saved["losses"], recipe, identity, original_losses)
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
                lr = learning_rate(identity["learning_rate_policy"], local, recipe["additional_updates"])
                for group in optimizer.param_groups:
                    group["lr"] = lr
                log_event({"event":"started", "update":attempted_update, "continuation_update":local,
                    "learning_rate":lr, "epoch":e, "batch_index":index + 1, "triplet_ids":batches[index]})
                augmented = [resolution.augment_example(store.example(triplets[key]), seed=1234, epoch=e,
                    batch_index=index + 1, sample_index=j, triplet_id=key) for j, key in enumerate(batches[index])]
                examples, audits = zip(*augmented)
                inputs, targets, masks = (torch.stack([x[j] for x in examples]).to(device) for j in range(3))
                loss, gradients = frozen.training.training_step(model, optimizer, inputs, targets, masks)
                losses.append({"update":len(losses) + 1, "continuation_update":local, "learning_rate":lr,
                    "epoch":e, "batch_index":index + 1, "triplet_ids":batches[index], "loss":loss,
                    "gradient_parameter_count":gradients, "augmentation":list(audits)})
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
            "completed_epochs":recipe["end_epoch"], "new_completed_epochs":5, "completed_updates":len(losses),
            "initial_updates":recipe["initial_updates"], "additional_updates":len(losses) - recipe["initial_updates"],
            "optimizer_updates":len(losses) - recipe["initial_updates"], "source_completed":identity["source_completed"],
            "source_state":identity["source_state"], "source_checkpoint":identity["source_checkpoint"],
            "initial_optimizer":"continued_Adam_with_parent_moments_and_steps", "learning_rate_policy":identity["learning_rate_policy"],
            "selection_applied":False, "selected_checkpoint":None, "model_adopted":False,
            "final_checkpoint":reports[-1]["checkpoint"], "checkpoints":[r["checkpoint"] for r in reports[1:]],
            "validation_reports":[binding(root, output / "validation" / f"epoch_{r['epoch']:03d}.json") for r in reports],
            "resume_checkpoint":binding(root, latest), "stop_reason":"fixed_five_additional_epochs",
            "initial_continuation_state":binding(root, output / "states" / f"update_{recipe['initial_updates']:06d}.pth"),
            "epoch_five_reused":True, "new_validation_epochs":list(range(6,11)), "training":TRAINING,
            "augmentation":source_training.augmentation.POLICY, "resolution":RESOLUTION,
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
    parser.add_argument("--arm", choices=tuple(ARMS), required=True)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    check(not args.resume or args.run, "--resume requires --run")
    root = Path(__file__).resolve().parents[2]
    if args.run:
        result = execute(root, args.recipe, args.arm, resume=args.resume)
        print(json.dumps({key:result[key] for key in ("status","arm","completed_epochs","completed_updates","additional_updates")}))
    else:
        *_, identity, _ = preflight(root, args.recipe, args.arm)
        print(json.dumps({"status":"preflight_only_no_model_execution", "identity":identity,
                          "new_epochs":list(range(6,11)), "new_updates":7760}))


if __name__ == "__main__":
    main()
