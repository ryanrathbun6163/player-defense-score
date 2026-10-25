"""Single frozen completion-campaign fit, with immutable epoch evidence and resume.

The CLI only executes model work with --run. Validation never changes the training
RNG, and a durable epoch checkpoint precedes its report. Completed reports are
consumed on resume rather than evaluated again.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import time
import traceback
import uuid

import torch

from . import completion_training_policy as policy
from . import completion_training_runtime as runtime
from . import nba_wasb_adaptation as adaptation
from . import wasb_training as training
from .wasb_experiment import bound_path, canonical, read_json, runtime_versions
from .completion_training_runtime import atomic_write_once as write_once


TRAINING = {"width": 512, "height": 288, "batch_size": 2, "seed": 1234,
            "optimizer": "Adam", "learning_rate": .0001, "max_epochs": 20,
            "min_epochs": 5, "patience": 5, "checkpoint_interval_updates": 25,
            "loss": "gamma2_weighted_binary_cross_entropy", "target_radius": 2.5,
            "batch_norm": "affine_trainable_running_buffers_frozen",
            "augmentation": False, "mining": False}
MIN_FREE_BYTES = 10 * 1024 ** 3
INFERENCE = {"heatmap_threshold": .3, "strict_threshold": True,
             "selection": "largest_component_mass_then_stable_candidate_index",
             "aggregation": "mean_aligned_complete_triplets", "triplet_stride": 1,
             "dtype": "float32", "device": "cuda", "padding": False,
             "resampling": False, "interpolation": False, "motion_selector": False,
             "threshold_search": False}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def output_path(root, value):
    path = (root / value).resolve()
    check(path.is_relative_to(root / "data/outputs") and path != root / "data/outputs",
          "Campaign output must remain inside data/outputs")
    return path


def preflight(root, recipe_path):
    """Read-only identities/roles/schedule checks, before pixels or model loads."""
    root = Path(root).resolve()
    path = (root / recipe_path).resolve()
    recipe = read_json(path)
    check(recipe["schema_version"] == "ball_completion_primary_recipe/v0.1"
          and recipe["status"] == "frozen_before_model_execution", "Recipe must be frozen")
    check(recipe["training"] == TRAINING, "Frozen primary hyperparameters differ")
    check(recipe["runtime"] == runtime_versions(), "Frozen runtime library versions differ")
    check(recipe.get("protected_evaluation_authorized") is False, "Protected evaluation must remain closed")
    bound_path(root, recipe["campaign_approval"])
    code = {b["path"]: bound_path(root, b) for b in recipe["code_bindings"]}
    for module in (runtime, policy, training, adaptation):
        check(Path(module.__file__).resolve().relative_to(root).as_posix() in code,
              "Recipe omits required implementation binding")
    check(Path(__file__).resolve().relative_to(root).as_posix() in code,
          "Recipe omits runner binding")
    for name in ("nba_action_observation", "nba_wasb_diagnostic", "wasb_adapter",
                 "wasb_adapted_adapter", "annotations", "wasb_experiment"):
        check(f"src/ball_tracking/{name}.py" in code, "Recipe omits inference/scoring dependency")
    check(recipe["inference"] == INFERENCE, "Frozen inference policy differs from runtime")
    package = read_json(bound_path(root, recipe["package"]))
    check(package["schema_version"] == "completion_training_package/v0.1"
          and package["status"] == "accepted_references_prepared_for_freeze", "Package status differs")
    train, valid = package["training_blocks"], package["validation_blocks"]
    check(sum(len(b["frames"]) for b in train) == 3329
          and sum(len(b["frames"]) for b in valid) == 1110, "Frozen frame census differs")
    check(all(b["role"] == "training" for b in train)
          and all(b["role"] == "checkpoint_validation" for b in valid), "Package role leakage")
    blocks = {b["block_id"]: b for b in train + valid}
    check(len(blocks) == len(train) + len(valid), "Block identities collide")
    for t in package["training_triplets"]:
        check(t["block_id"] in blocks and blocks[t["block_id"]]["role"] == "training",
              "Training triplet references a nontraining block")
        b = blocks[t["block_id"]]
        check((t["domain"], t["game_id"]) == (b["domain"], b["game_id"]), "Triplet cohort differs")
        check(set(t["frame_indices"]).issubset({f["source_frame_index"] for f in b["frames"]}),
              "Triplet leaves its native block")
    schedule = read_json(bound_path(root, recipe["sampling_schedule"]))
    check(schedule == policy.make_schedule(package["training_triplets"], max_epochs=20, seed=1234),
          "Frozen schedule differs from actual package producer")
    nfhs = read_json(bound_path(root, recipe["nfhs_training_config"]))
    for key in ("checkpoint", "training_completion"):
        bound_path(root, recipe["initialization"][key])
    check(recipe["initialization"]["checkpoint"]["sha256"] == adaptation.INITIAL_SHA,
          "Initialization differs from approved retained checkpoint")
    identity = {"recipe": runtime.binding(root, path), "package_sha256": canonical(package),
                "schedule_sha256": canonical(schedule)}
    output_path(root, recipe["output_root"])
    output_path(root, recipe["cache_root"])
    return recipe, package, schedule, nfhs, identity


def resources(output):
    check(torch.cuda.is_available(), "Approved model execution requires CUDA; no fallback")
    ancestor = output
    while not ancestor.exists():
        ancestor = ancestor.parent
    check(shutil.disk_usage(ancestor).free >= MIN_FREE_BYTES, "Fewer than 10GiB free for campaign outputs")
    return {"gpu_name": torch.cuda.get_device_name(), "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "peak_reserved_bytes": torch.cuda.max_memory_reserved(), "disk_free_bytes": shutil.disk_usage(ancestor).free}


def state_payload(model, optimizer, identity, epoch, batch_index, losses, bn_reference):
    return {"schema_version": "completion_training_state/v0.1", "identity": identity,
            "epoch": epoch, "batch_index": batch_index, "completed_updates": len(losses),
            "model_state_dict": model.state_dict(), "optimizer_state_dict": optimizer.state_dict(),
            "rng_state": training.rng_state(), "losses": losses,
            "batch_norm_reference": bn_reference}


def load_state(path, identity, schedule):
    saved = torch.load(path, map_location="cpu", weights_only=True)
    check(saved.get("schema_version") == "completion_training_state/v0.1"
          and saved.get("identity") == identity, "Resume state frozen identity differs")
    epoch, position = saved["epoch"], saved["batch_index"]
    check(type(epoch) is int and 0 <= epoch <= 20 and type(position) is int,
          "Resume progress has invalid types")
    expected = []
    for e in schedule["epochs"][:epoch]:
        batches = e["batches"] if e["epoch"] < epoch else e["batches"][:position]
        expected.extend((e["epoch"], i + 1, ids) for i, ids in enumerate(batches))
    check((epoch == 0 and position == 0) or
          (epoch > 0 and 0 <= position <= len(schedule["epochs"][epoch - 1]["batches"])),
          "Resume batch position invalid")
    check(saved["completed_updates"] == len(saved["losses"]) == len(expected), "Resume loss/progress census differs")
    check(path.name == f"update_{len(expected):06d}.pth", "Resume filename/progress differs")
    check(all((r["epoch"], r["batch_index"], r["triplet_ids"]) == e
              and r["update"] == i + 1 for i, (r, e) in enumerate(zip(saved["losses"], expected))),
          "Saved losses differ from frozen schedule")
    model = saved["model_state_dict"]
    names = {n for n in model if n.endswith(("running_mean", "running_var", "num_batches_tracked"))}
    check(set(saved["batch_norm_reference"]) == names and
          all(torch.equal(model[n], saved["batch_norm_reference"][n]) for n in names),
          "Resume BatchNorm reference differs")
    training.validate_finite_tensors(saved)
    return saved


def retain_resume_states(root, output, latest):
    """Retain latest optimizer state and any state cited by a failed attempt."""
    keep = {latest.resolve()}
    check((output / "states").resolve().is_relative_to(output.resolve()), "Resume directory escaped this run")
    for failure in (output / "attempts").glob("*/failed.json"):
        old = read_json(failure).get("resume_checkpoint")
        if old:
            keep.add((root / old["path"]).resolve())
    for old in sorted((output / "states").glob("update_*.pth")):
        check(old.resolve().parent == (output / "states").resolve(), "Resume cleanup escaped this run")
        if old.resolve() not in keep:
            receipt = output / "retention" / (old.stem + ".json")
            if receipt.exists():
                record = read_json(receipt)
                check(record["removed_state"] == runtime.binding(root, old), "Interrupted cleanup state changed")
                bound_path(root, record["replacement"])
            else:
                record = {"status": "superseded_optimizer_state_removed", "removed_state": runtime.binding(root, old),
                          "replacement": runtime.binding(root, latest), "epoch_model_checkpoints_retained": True}
                write_once(receipt, record)
            old.unlink()


def checkpoint_epoch(root, output, identity, model, epoch, updates):
    path = output / "checkpoints" / f"epoch_{epoch:03d}.pth"
    if path.exists():
        saved = torch.load(path, map_location="cpu", weights_only=True)
        check(set(saved) == {"model_state_dict"}, "Epoch checkpoint must match adapter weight format")
        check(set(saved["model_state_dict"]) == set(model.state_dict()) and
              all(torch.equal(t.cpu(), saved["model_state_dict"][k]) for k, t in model.state_dict().items()),
              "Existing epoch checkpoint weights differ")
    else:
        training.save_checkpoint_once(path, {"model_state_dict": model.state_dict()})
    write_once(path.with_suffix(".json"), {"identity": identity, "epoch": epoch,
               "completed_updates": updates, "checkpoint": runtime.binding(root, path)})
    return runtime.binding(root, path)


def validation(root, output, identity, model, device, store, package, epoch, checkpoint):
    path = output / "validation" / f"epoch_{epoch:03d}.json"
    if path.exists():
        result = read_json(path)
        check(result["identity"] == identity and result["epoch"] == epoch and result["checkpoint"] == checkpoint,
              "Completed validation identity differs")
        bound_path(root, result["checkpoint"])
        return result
    rng = training.rng_state()
    try:
        result = runtime.validate_epoch(model, device, store, package, epoch, checkpoint)
    finally:
        training.restore_rng(rng)
    check(result["epoch"] == epoch and result["checkpoint"] == checkpoint, "Validation producer identity differs")
    result["identity"] = identity
    write_once(path, result)
    return result


def execute(root, recipe_path, *, resume=False):
    root = Path(root).resolve()
    recipe, package, schedule, nfhs, identity = preflight(root, recipe_path)
    output = output_path(root, recipe["output_root"])
    output.mkdir(parents=True, exist_ok=True)
    with training.training_lock(output / "training.lock"):
        return _execute_locked(root, recipe, package, schedule, nfhs, identity, output, resume)


def _execute_locked(root, recipe, package, schedule, nfhs, identity, output, resume):
    identity_path = output / "identity.json"
    if identity_path.exists():
        check(resume, "Campaign already started; use --resume, never an independent restart")
        check(read_json(identity_path) == identity, "Frozen campaign identity changed")
    else:
        check(not resume, "Cannot resume a campaign that has not started")
        write_once(identity_path, identity)
    completion_path = output / "completed.json"
    if completion_path.exists():
        result = read_json(completion_path)
        check(result["identity"] == identity, "Completed campaign identity differs")
        for key in ("selected_checkpoint", "final_checkpoint"):
            bound_path(root, result[key])
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
        write_once(attempt / "initial_resources.json", resources(output))
        states = sorted((output / "states").glob("update_*.pth"))
        prior = load_state(states[-1], identity, schedule) if states else None
        latest = states[-1] if states else None
        restored = prior["completed_updates"] if prior else 0
        replayed = []
        for log in sorted((output / "attempts").glob("*/updates.jsonl")):
            for line in log.read_text(encoding="utf-8").splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue  # A trailing power-loss fragment remains preserved in its original log.
                if event.get("event") == "completed" and event["update"] > restored:
                    replayed.append({"attempt_log": log.relative_to(root).as_posix(), "update": event["update"],
                                     "epoch": event["epoch"], "batch_index": event["batch_index"]})
        write_once(attempt / "restored.json", {"restored_updates": restored, "previous_unsaved_completed_updates": replayed,
                   "previous_unsaved_completed_count": len(replayed), "identity": identity})
        store = runtime.FrameStore(root, package, output_path(root, recipe["cache_root"]))
        cache = store.prepare()
        cache_path = output / "cache_preparation.json"
        if cache_path.exists():
            old = read_json(cache_path)
            check({k: v for k, v in old.items() if k != "elapsed_seconds"} ==
                  {k: v for k, v in cache.items() if k != "elapsed_seconds"}, "Verified cache changed")
        else:
            write_once(cache_path, cache)
        model, device, optimizer, initial_bn = adaptation.initialize(root, recipe, nfhs)
        epoch, position, losses, bn_reference = 0, 0, [], initial_bn
        if prior:
            check(set(initial_bn) == set(prior["batch_norm_reference"]) and
                  all(torch.equal(v.cpu(), prior["batch_norm_reference"][k]) for k, v in initial_bn.items()),
                  "Resume BN reference differs from initialization")
            model.load_state_dict(prior["model_state_dict"], strict=True)
            optimizer.load_state_dict(prior["optimizer_state_dict"])
            training.restore_rng(prior["rng_state"])
            epoch, position, losses = prior["epoch"], prior["batch_index"], prior["losses"]
            bn_reference = prior["batch_norm_reference"]
        training.freeze_batch_norm(model)
        training.assert_batch_norm_unchanged(model, bn_reference)

        def save_state(e, p):
            nonlocal latest
            measured = resources(output)
            training.assert_batch_norm_unchanged(model, bn_reference)
            path = output / "states" / f"update_{len(losses):06d}.pth"
            if path.exists():
                saved = load_state(path, identity, schedule)
                check(saved["epoch"] == e and saved["batch_index"] == p, "Existing resume position differs")
            else:
                training.save_checkpoint_once(path, state_payload(model, optimizer, identity, e, p, losses, bn_reference))
            latest = path
            measured_path = output / "resources" / (path.stem + ".json")
            if not measured_path.exists():
                write_once(measured_path, measured)
            retain_resume_states(root, output, latest)

        reports = []
        for path in sorted((output / "validation").glob("epoch_*.json")):
            r = read_json(path)
            check(r["identity"] == identity and r["epoch"] == len(reports), "Validation history has a gap or changed identity")
            check(r["epoch"] <= epoch, "Validation report is ahead of resume checkpoint")
            bound_path(root, r["checkpoint"])
            reports.append(r)
        if epoch == 0:
            save_state(0, 0)
            cp = recipe["initialization"]["checkpoint"]
            baseline = validation(root, output, identity, model, device, store, package, 0, cp)
            reports = [baseline]
        else:
            check(reports, "Trained state is missing retained epoch-zero report")
        selected = policy.choose_checkpoint(reports)
        for epoch_spec in schedule["epochs"]:
            e, batches = epoch_spec["epoch"], epoch_spec["batches"]
            if e < epoch:
                continue
            if e == epoch and position < len(batches):
                check(reports[-1]["epoch"] == e - 1, "Partial epoch has an existing validation report")
            if reports[-1]["epoch"] >= e:
                if policy.should_stop(e, selected["selected_epoch"], min_epochs=5, patience=5):
                    break
                continue
            start_batch = position if e == epoch else 0
            epoch_began = time.perf_counter()
            training.freeze_batch_norm(model)  # Discard returned buffers; keep initial reference.
            training.assert_batch_norm_unchanged(model, bn_reference)
            triplets = {t["triplet_id"]: t for t in package["training_triplets"]}
            for i in range(start_batch, len(batches)):
                attempted_update = len(losses) + 1
                log_event({"event": "started", "update": attempted_update, "epoch": e,
                           "batch_index": i + 1, "triplet_ids": batches[i]})
                examples = [store.example(triplets[key]) for key in batches[i]]
                inputs, targets, masks = (torch.stack([sample[j] for sample in examples]).to(device) for j in range(3))
                loss, gradients = training.training_step(model, optimizer, inputs, targets, masks)
                losses.append({"update": len(losses) + 1, "epoch": e, "batch_index": i + 1,
                               "triplet_ids": batches[i], "loss": loss, "gradient_parameter_count": gradients})
                log_event({"event": "completed", **losses[-1]})
                del inputs, targets, masks, examples
                if len(losses) % 25 == 0 or i + 1 == len(batches):
                    save_state(e, i + 1)
                    print(f"epoch {e} batch {i+1}/{len(batches)} update {len(losses)} loss {loss:.6f} elapsed {time.perf_counter()-epoch_began:.1f}s", flush=True)
            cp = checkpoint_epoch(root, output, identity, model, e, len(losses))
            report = validation(root, output, identity, model, device, store, package, e, cp)
            training.assert_batch_norm_unchanged(model, bn_reference)
            reports.append(report)
            selected = policy.choose_checkpoint(reports)
            print(f"epoch {e} validated; selected {selected['selected_epoch']}; elapsed {time.perf_counter()-epoch_began:.1f}s", flush=True)
            epoch, position = e, len(batches)
            if policy.should_stop(e, selected["selected_epoch"], min_epochs=5, patience=5):
                break
        final = reports[-1]
        result = {"schema_version": "completion_training_result/v0.1", "status": "completed",
                  "identity": identity, "completed_epochs": final["epoch"], "completed_updates": len(losses),
                  "selection": {k: v for k, v in selected.items() if k != "selected_report"},
                  "selected_checkpoint": selected["selected_report"]["checkpoint"],
                  "final_checkpoint": final["checkpoint"],
                  "validation_reports": [runtime.binding(root, output / "validation" / f"epoch_{r['epoch']:03d}.json") for r in reports],
                  "resume_checkpoint": runtime.binding(root, latest),
                  "stop_reason": "max_epochs" if final["epoch"] == 20 else "five_epochs_without_rank_improvement",
                  "attempt_elapsed_seconds": time.perf_counter() - began,
                  "resources": resources(output),
                  "protected_evaluation_authorized": False, "post_selection_references_used": False,
                  "heatmaps_retained": False, "ball_phase_accepted": False}
        write_once(completion_path, result)
        write_once(attempt / "completed.json", {"completion": runtime.binding(root, completion_path)})
        return result
    except BaseException as error:
        write_once(attempt / "failed.json", {"identity": identity, "error_type": type(error).__name__,
            "error": str(error), "traceback": traceback.format_exc(), "elapsed_seconds": time.perf_counter() - began,
            "resume_checkpoint": runtime.binding(root, latest) if latest else None,
            "completed_updates_in_memory": len(losses), "last_attempted_update": attempted_update,
            "attempt_update_log": runtime.binding(root, log_path) if log_path.exists() else None,
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
    root = Path(__file__).resolve().parents[2]
    check(not args.resume or args.run, "--resume requires --run")
    if args.run:
        result = execute(root, args.recipe, resume=args.resume)
        print(json.dumps({k: result[k] for k in ("status", "completed_epochs", "completed_updates", "selected_checkpoint")}))
    else:
        _, package, schedule, _, identity = preflight(root, args.recipe)
        print(json.dumps({"status": "preflight_only_no_model_execution", "identity": identity,
                          "training_triplets": len(package["training_triplets"]), "schedule_epochs": len(schedule["epochs"])}))


if __name__ == "__main__":
    main()
