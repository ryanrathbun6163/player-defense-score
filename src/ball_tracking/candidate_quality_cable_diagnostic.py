"""One prepared native-cable diagnostic replay; metadata stays CPU-only.

This preserves the historical recovery worker and recipe. Only leave_chi_out
runs, from the audited epoch-two state through epoch six, without scoring.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import random
import sys
import threading
import time
import traceback

from . import candidate_quality_pilot as original
from . import candidate_quality_post_driver_resume as recovery

ROOT = original.ROOT
MODULE = "src.ball_tracking.candidate_quality_cable_diagnostic"
OUTPUT = "data/outputs/t/native_cable_diagnostic_2026-10-29_v0_1"
MONITOR = OUTPUT + "/monitoring/attempt_001"
FIT = "leave_chi_out"
MAX_TOTAL_SECONDS = 600
CLEANUP_RESERVE_SECONDS = 30
REMAINING_PILOT_SECONDS = 2287
START_STEP = 748
END_STEP = 2244
MAX_UPDATES = 1496
PRIOR_RETURNED_OVERLAP = 1015

check = original.check
read = original.read
rows = original.rows
binding = original.binding
bound = original.bound
stamp = original.stamp
write_once = recovery.write_once
append = recovery.append


def validate_execution_approval(approval, freeze_binding):
    check(approval.get("run_approved") is True
          and approval.get("execution_freeze") == freeze_binding
          and approval.get("max_total_seconds") == MAX_TOTAL_SECONDS
          and approval.get("automatic_retry") is False
          and approval.get("diagnostic_intervention") == "previously_user_changed_native_Corsair_cable_path"
          and approval.get("debug_mode_enabled") is False
          and approval.get("settings_change_authorized") is False
          and isinstance(approval.get("approval_text"), str) and approval["approval_text"].strip(),
          "This prepared cable-path diagnostic needs a separate explicit execution approval")


def validate_freeze(freeze):
    expected = {"schema_version": "candidate_quality_cable_diagnostic/v0.1",
                "max_total_seconds": MAX_TOTAL_SECONDS,
                "cleanup_reserve_seconds": CLEANUP_RESERVE_SECONDS,
                "remaining_pilot_seconds": REMAINING_PILOT_SECONDS,
                "first_fit_only": FIT, "start_step": START_STEP, "end_step": END_STEP,
                "max_updates": MAX_UPDATES, "scoring": False,
                "debug_mode_enabled": False, "agent_settings_change": False,
                "diagnostic_intervention": "previously_user_changed_native_Corsair_cable_path"}
    check(all(freeze.get(key) == value for key, value in expected.items()), "Diagnostic scope or budget differs")


def preflight(root=ROOT, require_approval=False):
    root = Path(root).resolve()
    config, historical, audit = recovery.preflight(root, require_approval=True)
    folder = root / OUTPUT
    freeze = read(folder / "execution_freeze.json")
    validate_freeze(freeze)
    check(freeze["source_recovery_freeze"] == binding(root, root / recovery.OUTPUT / recovery.PREPARATION / "execution_freeze.json"),
          "Historical recovery binding differs")
    check(freeze["checkpoint"] == historical["checkpoint"] and freeze["checkpoint_audit"] == historical["checkpoint_audit"],
          "Only the already audited epoch-two checkpoint is permitted")
    for key in ("source_recovery_freeze", "checkpoint", "checkpoint_audit", "proposal", "intervention_record",
                "latest_interruption", "latest_launcher_receipt", "prior_budget_receipt"):
        bound(root, freeze[key])
    for link in freeze["bindings"]:
        bound(root, link)
    check(binding(root, Path(__file__).resolve()) in freeze["bindings"], "Diagnostic worker must be bound")
    validate_intervention_record(read(root / freeze["intervention_record"]["path"]))
    validate_previous_accounting(read(root / freeze["latest_interruption"]["path"]),
        read(root / freeze["latest_launcher_receipt"]["path"]),
        read(root / freeze["prior_budget_receipt"]["path"]))
    check(config["training"]["epochs"] == 6 and config["training"]["batch_size"] == 32,
          "Historical training recipe differs")
    if require_approval:
        validate_execution_approval(read(folder / "execution_approval.json"), binding(root, folder / "execution_freeze.json"))
        validate_launch_readiness(read(folder / "launch_readiness.json"))
    check("torch" not in sys.modules, "Diagnostic metadata preflight imported Torch")
    return config, freeze, historical, audit


def validate_intervention_record(record):
    check(record.get("cable_change_user_reported") is True
          and record.get("current_debug_mode_enabled") is False
          and record.get("debug_mode_state_basis") == "user_reported"
          and record.get("debug_mode_setting_changed_by_agent") is False,
          "Prepared intervention must preserve reported native cable and unchanged Debug Mode off")


def validate_launch_readiness(readiness, now_utc=None):
    # This receipt is produced only at a separately authorized launch. A user
    # report in the preparation handoff does not replace the fresh launch check.
    created_text = readiness.get("at_utc")
    check(isinstance(created_text, str), "Launch readiness requires an explicit UTC timestamp")
    created = datetime.fromisoformat(created_text)
    now = now_utc or datetime.now(timezone.utc)
    check(created.tzinfo is not None and created.utcoffset() == timedelta(0)
          and now.tzinfo is not None and now.utcoffset() == timedelta(0),
          "Launch readiness and comparison timestamps must be UTC")
    age_seconds = (now - created).total_seconds()
    check(math.isfinite(age_seconds) and -2 <= age_seconds <= 120,
          "Launch readiness is stale or dated in the future")
    check(readiness.get("driver_version") == "617.42"
          and readiness.get("gpu_uuid") == "GPU-f26f32f8-e85b-0d38-651e-d5c54097525b"
          and readiness.get("ram_configured_mt_s") == [5200, 5200]
          and readiness.get("isolation_conflicts") == []
          and readiness.get("existing_gpu_workers") == []
          and readiness.get("debug_mode_enabled") is False
          and readiness.get("debug_mode_state_basis") in ("user_reported", "ui_observed")
          and readiness.get("settings_changed") is False
          and readiness.get("fresh_launch_checks_passed") is True,
          "Fresh launch readiness requires the verified device, driver, memory, isolation and unchanged Debug Mode off")


def validate_previous_accounting(failed, launcher, prior_budget):
    saved = failed["accounting"]
    local = saved["new_attempt"]
    physical = saved["cumulative_physical_lower_bound"]
    check(local["training_forwards_attempted"] == local["training_forwards_returned"] == 83
          and local["optimizer_updates"] == 82 and local["training_candidate_presentations"] == 2624,
          "Preserved attempt004 partial-forward accounting differs")
    check(physical["training_forwards_attempted"] == 2588
          and physical["training_forwards_returned"] == 2587
          and physical["optimizer_updates"] == 2586
          and physical["training_candidate_presentations"] == 82682,
          "Prior physical lower bounds differ")
    check(launcher["returncode"] == 1 and launcher["supervisor_result"]["remaining_owned_processes_before_close"] == 0
          and launcher["supervisor_result"]["job_cleanup_error"] is None
          and launcher["event_remaining_owned_processes"] == 0 and launcher["automatic_retry"] is False,
          "Prior stopped-run cleanup evidence differs")
    debit = math.ceil(launcher["charged_elapsed_seconds"])
    check(debit == 150 and prior_budget["remaining_original_pilot_seconds"] == 2437
          and prior_budget["remaining_original_pilot_seconds"] - debit == REMAINING_PILOT_SECONDS,
          "Diagnostic may not refund or reset prior exposure")


def validate_policy(policy):
    """Consume actual gpu_supervision.py fields; ownership guard validates the bootstrap."""
    check(policy["module"] == MODULE and policy["arguments"] == ["--run", "--monitor", MONITOR]
          and policy["sample_seconds"] == 2 and policy["temperature_stop_C"] == 80
          and policy["telemetry_timeout_seconds"] == 5 and policy["grace_seconds"] == 10
          and policy["automatic_retry"] is False, "Diagnostic supervisor policy differs")


def remaining_wall_seconds(policy, now_utc=None):
    created = datetime.fromisoformat(policy["created_at_utc"])
    now = now_utc or datetime.now(timezone.utc)
    check(created.tzinfo is not None and now.tzinfo is not None, "Budget times must be timezone-aware")
    elapsed = (now-created).total_seconds()
    check(math.isfinite(elapsed) and elapsed >= -2, "Invalid supervisor start time")
    elapsed = max(0., elapsed)
    remaining = MAX_TOTAL_SECONDS-elapsed
    check(remaining > CLEANUP_RESERVE_SECONDS, "Diagnostic startup/runtime budget exhausted")
    return {"elapsed_seconds": elapsed, "remaining_seconds": remaining,
            "stop_wait_seconds": remaining-CLEANUP_RESERVE_SECONDS,
            "maximum_total_seconds": MAX_TOTAL_SECONDS,
            "remaining_original_pilot_seconds_before_diagnostic": REMAINING_PILOT_SECONDS,
            "cleanup_reserve_seconds": CLEANUP_RESERVE_SECONDS,
            "start_basis": created.isoformat(),
            "soft_stop_at_utc": (created+timedelta(seconds=570)).isoformat(),
            "absolute_budget_deadline_utc": (created+timedelta(seconds=600)).isoformat()}


def accounting(counters):
    check(set(counters) == set(recovery.RECOVERED_COUNTERS)
          and all(type(value) is int and value >= 0 for value in counters.values()), "Invalid diagnostic counters")
    updates = counters["optimizer_updates"]
    check(updates <= MAX_UPDATES, "Diagnostic update cap exceeded")
    check(all(counters[key] == 0 for key in counters if key.startswith(("scoring_", "parity_"))),
          "Diagnostic must not score or repeat parity inference")
    return {"diagnostic_attempt": dict(counters),
            "logical_replay_branch": {key: recovery.RECOVERED_COUNTERS[key]+counters[key] for key in counters},
            "prior_durable_physical_lower_bound": {"optimizer_updates": 2586, "training_candidate_presentations": 82682,
                "training_forwards_attempted": 2588, "training_forwards_returned": 2587},
            "cumulative_physical_lower_bound": {"optimizer_updates": 2586+updates,
                "training_candidate_presentations": 82682+counters["training_candidate_presentations"],
                "training_forwards_attempted": 2588+counters["training_forwards_attempted"],
                "training_forwards_returned": 2587+counters["training_forwards_returned"]},
            "updates_replaying_attempt003": min(updates, PRIOR_RETURNED_OVERLAP),
            "updates_beyond_attempt003_last_returned": max(0, updates-PRIOR_RETURNED_OVERLAP),
            "preserved_latest_scientific_checkpoint_step": 1496,
            "preserved_attempt003_unsaved_updates": 267,
            "prior_scientific_unsaved_updates_by_attempt": {"attempt_001": 87, "attempt_002": 213,
                "attempt_003": 267, "attempt_004": 82},
            "prior_reference_clock_diagnostic_returned_updates": 441,
            "prior_reference_clock_diagnostic_updates_after_checkpoint": 67,
            "prior_reference_clock_diagnostic_debug_mode": "observed_on",
            "current_debug_mode": "off_keep_unchanged",
            "attempt004_returned_forward_without_optimizer_update": 1,
            "prior_replay_overhead_updates": 300,
            "diagnostic_is_not_scientific_completion": True,
            "limit": "Counts are durable lower bounds; unjournaled work remains unknown."}


def make_attempt_directory(root):
    destination = Path(root) / OUTPUT / "attempt_001"
    destination.mkdir(exist_ok=False)
    return destination


def run(root, monitor, arguments):
    root = Path(root).resolve()
    check(monitor == MONITOR and list(arguments) == ["--run", "--monitor", MONITOR], "Only the declared diagnostic attempt is permitted")
    from .continuation_owned_guard import verify_owned_worker
    ownership = verify_owned_worker(root, root / monitor, MODULE, arguments)
    policy = read(root / monitor / "policy.json")
    validate_policy(policy)
    budget = remaining_wall_seconds(policy)
    stop_file = root / monitor / "STOP"
    done = threading.Event()
    def deadline():
        try:
            delay = remaining_wall_seconds(policy)["stop_wait_seconds"]
        except ValueError:
            delay = 0
        if not done.wait(delay):
            stop_file.touch(exist_ok=True)
    threading.Thread(target=deadline, daemon=True).start()
    def require_running():
        if stop_file.exists():
            raise KeyboardInterrupt("Diagnostic supervisor requested STOP")
        remaining_wall_seconds(policy)
    began = time.monotonic()
    destination = None
    caches = []
    counters = dict.fromkeys(recovery.RECOVERED_COUNTERS, 0)
    try:
        config, freeze, historical, audit = preflight(root, require_approval=True)
        require_running()
        driver = recovery.verify_runtime_driver(policy["gpu_uuid"])
        destination = make_attempt_directory(root)
        write_once(destination / "started.json", {"at_utc": stamp(), "ownership": ownership,
            "execution_freeze": binding(root, root / OUTPUT / "execution_freeze.json"),
            "execution_approval": binding(root, root / OUTPUT / "execution_approval.json"),
            "source_recovery_freeze": freeze["source_recovery_freeze"], "recovered_checkpoint": freeze["checkpoint"],
            "budget": budget, "runtime_driver": driver, "accounting": accounting(counters),
            "first_fit_only": FIT, "scoring": False, "model_adopted": False,
            "prior_failures_preserved": ["attempt_001", "attempt_002", "attempt_003", "reference_clock_diagnostic", "attempt_004"],
            "intervention_record": freeze["intervention_record"],
            "debug_mode_enabled": False, "settings_changed": False})
        check("torch" not in sys.modules, "Torch imported before owned diagnostic execution")
        os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
        import numpy as np
        import torch
        from . import candidate_quality_model as model_api
        torch.set_num_threads(4)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.use_deterministic_algorithms(True)
        checkpoint = torch.load(bound(root, freeze["checkpoint"]), map_location="cpu", weights_only=False)
        expected_shapes = model_api.local_contract(root)["trainable_shapes"]
        recovery.validate_checkpoint_payload(checkpoint, historical["original_execution_freeze"]["sha256"], expected_shapes)
        source_out = root / original.OUTPUT
        candidates = rows(source_out / "preparation/candidates.jsonl")
        by_id = {row["candidate_id"]: row for row in candidates}
        check(len(candidates) == len(by_id) == config["counts"]["training_package_candidates"], "Candidate transport differs")
        train_cache = original.make_crop_cache(root, candidates, "candidate_id", destination / "training_crops.npy", model_api)
        caches.append(train_cache[0])
        require_running()
        journal = destination / "journal.jsonl"
        fit_name = FIT
        fit_dir = destination / fit_name
        fit_dir.mkdir()
        weights = rows(source_out / f"preparation/fits/{fit_name}/weights.jsonl")
        fit_manifest = read(source_out / f"preparation/fits/{fit_name}/manifest.json")
        fitting = original.validate_weights(by_id, weights)
        multipliers = {w["candidate_id"]: w["training_multiplier"] for w in weights}
        original.validate_fit_membership(by_id, weights, fit_manifest, fit_name)
        check(len(fitting) == 11954 and math.ceil(len(fitting)/32) == 374, "First-fit endpoint differs")
        random.seed(config["training"]["seed"])
        np.random.seed(config["training"]["seed"])
        torch.manual_seed(config["training"]["seed"])
        torch.cuda.manual_seed_all(config["training"]["seed"])
        require_running()
        model = model_api.build_model(root, device="cuda", execution_authorized=True, seed=config["training"]["seed"])
        frozen_before = model_api.frozen_fingerprint(model)
        trainable_before = original.trainable_group_fingerprints(model)
        write_once(fit_dir / "initial_tensor_fingerprints.json", {"frozen": frozen_before, "trainable_groups": trainable_before})
        write_once(fit_dir / "trainable_parameters.json", model_api.trainable_manifest(model))
        optimizer = torch.optim.AdamW(model_api.optimizer_parameter_groups(model), betas=(.9, .999), eps=1e-8)
        prior_initial = read(root / historical["prior_initial_fingerprints"]["path"])
        check(frozen_before == prior_initial["frozen"] and trainable_before == prior_initial["trainable_groups"],
              "Rebuilt original initialization differs before restore")
        restored = recovery.restore_checkpoint(model, optimizer, checkpoint,
            historical["original_execution_freeze"]["sha256"], expected_shapes)
        actual_cuda_rng = torch.cuda.get_rng_state_all()
        check(len(actual_cuda_rng) == len(checkpoint["cuda_rng"])
              and all(torch.equal(actual.cpu(), saved) for actual, saved in zip(actual_cuda_rng, checkpoint["cuda_rng"])),
              "CUDA RNG restoration differs")
        restored["cuda_rng_restore_verified"] = True
        check(model_api.frozen_fingerprint(model) == frozen_before, "Restore changed frozen prefix")
        check(original.trainable_group_fingerprints(model) == audit["group_fingerprints"],
              "Restored trainable group hashes differ from independent audit")
        write_once(fit_dir / "restored_checkpoint.json", dict(restored, checkpoint=freeze["checkpoint"],
            inherited_initial=historical["prior_initial_fingerprints"], inherited_parity=historical["prior_producer_parity"],
            inherited_first_gradients=historical["prior_gradient_checks"], next_epoch=3,
            diagnostic_replay=True, runtime_driver=driver))
        del checkpoint
        fit_steps = START_STEP
        for epoch in range(3, 7):
            order = list(fitting)
            random.Random(config["training"]["seed"]+epoch).shuffle(order)
            model.train()
            epoch_loss = 0.0
            group_losses = defaultdict(lambda: [0.0, 0.0, 0])
            for batch in original.batches(order, config["training"]["batch_size"]):
                require_running()
                check(counters["optimizer_updates"] < MAX_UPDATES and fit_steps < END_STEP, "Diagnostic update cap reached")
                pixels, point_weights = original.input_batch(batch, *train_cache, "candidate_id")
                targets = torch.tensor([r["target"] for r in batch], device="cuda", dtype=torch.float32)
                scale = torch.tensor([multipliers[r["candidate_id"]] for r in batch], device="cuda", dtype=torch.float32)
                optimizer.zero_grad(set_to_none=True)
                counters["training_forwards_attempted"] += 1
                append(journal, {"event": "train_start", "fit": fit_name, "epoch": epoch, "step": fit_steps,
                    "batch_count": len(batch), "diagnostic_replay_of_attempt003": fit_steps < 1763})
                logits = model(pixels, point_weights)
                check(logits.shape == targets.shape and bool(torch.isfinite(logits).all()), "Invalid training logits")
                counters["training_forwards_returned"] += 1
                losses = torch.nn.functional.binary_cross_entropy_with_logits(logits, targets, reduction="none")
                loss = (losses*scale).mean()
                check(bool(torch.isfinite(loss)), "Nonfinite training loss")
                loss.backward()
                grad_norm = torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad],
                                                           max_norm=1.0, error_if_nonfinite=True)
                check(all(p.grad is None for p in model.parameters() if not p.requires_grad), "Frozen gradient appeared")
                optimizer.step()
                fit_steps += 1
                counters["optimizer_updates"] += 1
                counters["training_candidate_presentations"] += len(batch)
                weighted = (losses*scale).detach().cpu().tolist()
                for row, value in zip(batch, weighted):
                    objective_weight = multipliers[row["candidate_id"]]/len(fitting)
                    contribution = value/len(fitting)
                    epoch_loss += contribution
                    totals = group_losses[row["target_group"]]
                    totals[0] += contribution; totals[1] += objective_weight; totals[2] += 1
                append(journal, {"event": "train_return", "fit": fit_name, "epoch": epoch, "step": fit_steps,
                    "weighted_batch_loss": float(loss.detach().cpu()), "gradient_norm_before_clip": float(grad_norm.detach().cpu())})
                del pixels, point_weights, targets, scale, logits, losses, loss, grad_norm
            require_running()
            append(destination / "epochs.jsonl", {"fit": fit_name, "epoch": epoch, "weighted_online_loss": epoch_loss,
                "group_loss_mass_weight_count": dict(group_losses), "note": "Diagnostic replay; online loss is not evaluation"})
            checkpoint_path = fit_dir / f"diagnostic_epoch_{epoch:02d}.pth"
            recovery.save_checkpoint_once(checkpoint_path, {"trainable_state": {n: p.detach().cpu() for n, p in model.named_parameters() if p.requires_grad},
                "optimizer_state": optimizer.state_dict(), "epoch": epoch, "fit": fit_name, "fit_steps": fit_steps,
                "counters": accounting(counters)["logical_replay_branch"], "diagnostic_counters": dict(counters),
                "accounting": accounting(counters), "python_rng": random.getstate(), "numpy_rng": np.random.get_state(),
                "torch_rng": torch.get_rng_state(), "cuda_rng": torch.cuda.get_rng_state_all(),
                "original_execution_freeze": historical["original_execution_freeze"],
                "diagnostic_freeze": binding(root, root / OUTPUT / "execution_freeze.json"),
                "purpose": "Separate stability diagnostic only; no scientific adoption or automatic continuation"})
            append(destination / "diagnostic_checkpoints.jsonl", binding(root, checkpoint_path))
            print(json.dumps({"fit": fit_name, "epoch": epoch, "logical_replay_steps": fit_steps,
                "diagnostic_updates": counters["optimizer_updates"], "weighted_online_loss": epoch_loss}), flush=True)
        check(fit_steps == END_STEP and counters["optimizer_updates"] == MAX_UPDATES
              and counters["training_candidate_presentations"] == 47816, "Diagnostic first-fit endpoint differs")
        check(counters["training_forwards_attempted"] == counters["training_forwards_returned"] == MAX_UPDATES,
              "Unreturned diagnostic training call")
        check(model_api.frozen_fingerprint(model) == frozen_before, "Frozen backbone tensors changed")
        trainable_after = original.trainable_group_fingerprints(model)
        check(all(trainable_after[group] != trainable_before[group] for group in trainable_before), "Trainable groups must change")
        write_once(fit_dir / "final_tensor_fingerprints.json", {"frozen": frozen_before, "trainable_groups": trainable_after,
            "frozen_unchanged": True, "backbone_and_head_changed": True})
        del optimizer, model
        torch.cuda.empty_cache()
        require_running()
        result = {"status": "completed_bounded_native_cable_first_fit_no_scoring", "at_utc": stamp(),
            "elapsed_worker_seconds": time.monotonic()-began, "budget": budget, "accounting": accounting(counters),
            "fit": FIT, "final_replay_step": fit_steps, "epochs": [3, 4, 5, 6], "runtime_driver": driver,
            "model_adopted": False, "protected_access": False, "new_labels": 0, "scoring": False,
            "automatic_retry": False, "interpretation": "A completed short diagnostic is not proof of long-term stability or root cause."}
        write_once(destination / "completed.json", result)
        return result
    except BaseException as error:
        if destination is not None:
            write_once(destination / "failed.json", {"at_utc": stamp(), "elapsed_worker_seconds": time.monotonic()-began,
                "error": type(error).__name__, "message": str(error), "traceback": traceback.format_exc(),
                "accounting": accounting(counters), "automatic_retry": False})
        raise
    finally:
        done.set()
        for cache in caches:
            cache.flush()
            cache._mmap.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight", action="store_true")
    group.add_argument("--run", action="store_true")
    parser.add_argument("--monitor")
    parser.add_argument("--require-approval", action="store_true")
    args = parser.parse_args()
    if args.preflight:
        _, freeze, _, _ = preflight(require_approval=args.require_approval)
        print(json.dumps({"status": "CPU_metadata_cable_diagnostic_preflight_passed", "bindings": len(freeze["bindings"]),
            "max_total_seconds": MAX_TOTAL_SECONDS, "max_updates": MAX_UPDATES, "torch_imported": False}))
    else:
        print(json.dumps(run(ROOT, args.monitor, sys.argv[1:])))


if __name__ == "__main__":
    main()
