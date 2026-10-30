"""Complete the original fixed pilot from a separately audited diagnostic endpoint.

Preparation imports no Torch. A new bound approval and fresh readiness are
required for execution. The original diagnostic purpose and failure history
remain unchanged; the first fixed fit receives no further training updates.
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
import subprocess
import sys
import threading
import time
import traceback

from . import candidate_quality_pilot as original
from . import candidate_quality_cable_reference_diagnostic as diagnostic

ROOT = original.ROOT
OUTPUT = original.OUTPUT
MODULE = "src.ball_tracking.candidate_quality_native_cable_resume"
PREPARATION = "data/outputs/t/native_cable_training_continuation_2026-10-29_v0_1"
MONITOR = PREPARATION + "/monitoring/attempt_001"
CHECKPOINT_PATH = diagnostic.OUTPUT + "/attempt_001/leave_chi_out/diagnostic_epoch_06.pth"
CHECKPOINT_SHA256 = "6976594931e696a4f9f5c3e624c1048a95d666f6503b10960a4360f5bb9b9cfc"
CHECKPOINT_BYTES = 43_272_491
DIAGNOSTIC_FREEZE = {"path": diagnostic.OUTPUT + "/execution_freeze.json",
    "bytes": 7412, "sha256": "7e7aa08968a707319dad3e501e87dfb3ed1ecea55348d34c22429de21e080de1"}
ORIGINAL_FREEZE = {"path": OUTPUT + "/execution_freeze.json", "bytes": 10543,
    "sha256": "b1aaaad44fb039d0814e26f0f94390b77ca8ffd119e672c0f88e7268daf9295b"}
MAX_TOTAL_SECONDS = 5400
CLEANUP_RESERVE_SECONDS = 30
HISTORICAL_EXPOSURE_SECONDS = 1574
RECOVERED_COUNTERS = {
    "training_forwards_attempted": 2244, "training_forwards_returned": 2244,
    "optimizer_updates": 2244, "training_candidate_presentations": 71724,
    "scoring_forwards_attempted": 0, "scoring_forwards_returned": 0,
    "scoring_candidate_presentations": 0, "parity_forwards_attempted": 1,
    "parity_forwards_returned": 1, "parity_candidate_presentations": 32,
}
PRIOR_PHYSICAL_COUNTERS = dict(RECOVERED_COUNTERS, training_forwards_attempted=4084,
    training_forwards_returned=4083, optimizer_updates=4082, training_candidate_presentations=130498)
CHECKPOINT_DIAGNOSTIC_COUNTERS = dict.fromkeys(RECOVERED_COUNTERS, 0)
CHECKPOINT_DIAGNOSTIC_COUNTERS.update(training_forwards_attempted=1496, training_forwards_returned=1496,
    optimizer_updates=1496, training_candidate_presentations=47816)

check = original.check
read = original.read
rows = original.rows
binding = original.binding
bound = original.bound
stamp = original.stamp


def write_once(path, value):
    """Never replace a receipt; flush its bytes before reporting completion."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def append(path, value):
    # Timestamp receipt creation, not CUDA kernel duration or completion latency.
    value = dict(value)
    value.setdefault("at_utc", stamp())
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def accounting(new_counters):
    check(set(new_counters) == set(RECOVERED_COUNTERS), "Counter fields differ")
    check(all(type(v) is int and v >= 0 for v in new_counters.values()), "Invalid new-work counter")
    return {
        "new_attempt": dict(new_counters),
        "logical": {k: RECOVERED_COUNTERS[k] + new_counters[k] for k in new_counters},
        "cumulative_physical_lower_bound": {k: PRIOR_PHYSICAL_COUNTERS[k] + new_counters[k]
                                            for k in new_counters},
        "source_endpoint_logical_updates": 2244,
        "prior_unsaved_updates_by_attempt_preserved": {
            "attempt_001": 87, "attempt_002": 213, "attempt_003": 267, "attempt_004": 82},
        "prior_reference_clock_diagnostic_updates": 441,
        "completed_native_cable_diagnostic_updates": 1496,
        "diagnostic_import_is_not_model_adoption": True,
        "limit": "Durably recorded lower bounds; prior unjournaled work and the partial returned forward remain distinct.",
    }


def remaining_wall_seconds(policy, now_utc=None):
    created = datetime.fromisoformat(policy["created_at_utc"])
    now = now_utc or datetime.now(timezone.utc)
    check(created.tzinfo is not None and now.tzinfo is not None, "Budget times require timezone")
    elapsed = (now-created).total_seconds()
    check(math.isfinite(elapsed) and elapsed >= -2, "Invalid supervisor start time")
    elapsed = max(0., elapsed)
    remaining = MAX_TOTAL_SECONDS-elapsed
    check(remaining > CLEANUP_RESERVE_SECONDS, "Operational supervised limit exhausted")
    return {"elapsed_seconds": elapsed, "remaining_seconds": remaining,
            "stop_wait_seconds": remaining-CLEANUP_RESERVE_SECONDS,
            "maximum_total_seconds": MAX_TOTAL_SECONDS, "cleanup_reserve_seconds": CLEANUP_RESERVE_SECONDS,
            "historical_exposure_seconds_preserved": HISTORICAL_EXPOSURE_SECONDS,
            "historical_hour_budget_is_active_limit": False,
            "start_basis": created.isoformat(),
            "soft_stop_at_utc": (created+timedelta(seconds=MAX_TOTAL_SECONDS-CLEANUP_RESERVE_SECONDS)).isoformat(),
            "absolute_budget_deadline_utc": (created+timedelta(seconds=MAX_TOTAL_SECONDS)).isoformat(),
            "outer_launcher_monotonic_deadline_includes_prepolicy_startup": True}


def make_attempt_directory(out):
    destination = Path(out) / "attempt_005"
    destination.mkdir(exist_ok=False)
    return destination


def fit_start(fit_name):
    check(fit_name in original.FIT_NAMES, "Unknown fixed fit")
    return (7, 2244) if fit_name == "leave_chi_out" else (1, 0)


def validate_policy(policy):
    check(policy["module"] == MODULE and policy["arguments"] == ["--run", "--monitor", MONITOR]
          and policy["sample_seconds"] == 2 and policy["temperature_stop_C"] == 80
          and policy["telemetry_timeout_seconds"] == 5 and policy["grace_seconds"] == 10
          and policy["automatic_retry"] is False and policy["max_total_seconds"] == MAX_TOTAL_SECONDS
          and policy["soft_stop_seconds"] == MAX_TOTAL_SECONDS-CLEANUP_RESERVE_SECONDS,
          "Continuation supervisor policy differs")


def preflight(root=ROOT, require_approval=False):
    root = Path(root).resolve()
    # Historical completion is checked below; never apply its stale launch-readiness lease.
    config, _, historical, _ = diagnostic.preflight(root, require_approval=False)
    folder = root / PREPARATION
    freeze = read(folder / "execution_freeze.json")
    check(freeze["schema_version"] == "candidate_quality_native_cable_resume/v0.1"
          and freeze["max_total_seconds"] == MAX_TOTAL_SECONDS
          and freeze["cleanup_reserve_seconds"] == CLEANUP_RESERVE_SECONDS
          and freeze["historical_hour_budget_is_active_limit"] is False
          and freeze["historical_exposure_seconds"] == HISTORICAL_EXPOSURE_SECONDS,
          "Continuation operational limit or historical exposure differs")
    check(freeze["new_attempt"] == "attempt_005" and freeze["first_fit_next_epoch"] == 7
          and freeze["new_updates_if_complete"] == 7626 and freeze["logical_updates_if_complete"] == 9870,
          "Fixed scientific endpoints differ")
    check(freeze["original_execution_freeze"] == ORIGINAL_FREEZE == historical["original_execution_freeze"]
          and freeze["original_execution_approval"] == historical["original_execution_approval"]
          and freeze["source_diagnostic_freeze"] == DIAGNOSTIC_FREEZE,
          "Original/diagnostic provenance differs")
    check(freeze["checkpoint"] == {"path": CHECKPOINT_PATH, "bytes": CHECKPOINT_BYTES, "sha256": CHECKPOINT_SHA256},
          "Only the audited fixed epoch-six endpoint may be imported")
    for key in ("original_execution_freeze", "original_execution_approval", "source_diagnostic_freeze",
                "source_diagnostic_approval", "source_diagnostic_completed", "source_launcher_finished",
                "source_events_finished", "checkpoint", "checkpoint_audit", "prior_initial_fingerprints",
                "prior_producer_parity", "prior_gradient_checks"):
        bound(root, freeze[key])
    for link in freeze["bindings"]:
        bound(root, link)
    check(binding(root, Path(__file__).resolve()) in freeze["bindings"], "New worker source must be frozen")
    diagnostic.validate_execution_approval(read(root / freeze["source_diagnostic_approval"]["path"]), DIAGNOSTIC_FREEZE)
    completed = read(root / freeze["source_diagnostic_completed"]["path"])
    check(completed["status"] == "completed_bounded_native_cable_reference_clock_first_fit_no_scoring"
          and completed["fit"] == "leave_chi_out" and completed["final_replay_step"] == 2244
          and completed["accounting"]["logical_replay_branch"] == RECOVERED_COUNTERS
          and completed["accounting"]["diagnostic_attempt"] == CHECKPOINT_DIAGNOSTIC_COUNTERS
          and completed["scoring"] is False and completed["model_adopted"] is False,
          "Source diagnostic endpoint did not complete as declared")
    launched = read(root / freeze["source_launcher_finished"]["path"])
    final = launched["supervisor_result"]
    check(launched["returncode"] == final["returncode"] == 0
          and launched["failure"] is None and final["stop_reason"] is None
          and final["job_cleanup_error"] is None and final["remaining_owned_processes_before_close"] == 0
          and launched["event_remaining_owned_processes"] == 0
          and read(root / freeze["source_events_finished"]["path"])["status"] == "supervisor_finished",
          "Source successful execution/cleanup evidence differs")
    check(math.ceil(launched["charged_elapsed_seconds"]) == 261
          and 474+180+285+224+150+261 == HISTORICAL_EXPOSURE_SECONDS,
          "Recorded historical exposure may not be refunded")
    audit = read(root / freeze["checkpoint_audit"]["path"])
    check(audit["status"] == "diagnostic_epoch_six_checkpoint_cpu_semantics_and_actual_model_restore_passed"
          and audit["checkpoint"] == freeze["checkpoint"] and audit["epoch"] == 6
          and audit["fit"] == "leave_chi_out" and audit["logical_fit_steps"] == 2244
          and audit["saved_logical_counters"] == RECOVERED_COUNTERS
          and audit["saved_diagnostic_local_counters"] == CHECKPOINT_DIAGNOSTIC_COUNTERS
          and audit["original_scientific_freeze"] == ORIGINAL_FREEZE
          and audit["diagnostic_freeze"] == DIAGNOSTIC_FREEZE
          and audit["all_trainable_and_optimizer_tensors_finite_cpu"] is True
          and audit["exact_cpu_parameter_and_AdamW_restore"] is True
          and audit["actual_pinned_CPU_model_constructed"] is True
          and audit["frozen_prefix_matches_original_executed_model"] is True
          and audit["restored_group_fingerprints_match_producer_final"] is True
          and audit["cuda_initialized"] is False and audit["model_forward_calls"] == 0,
          "Actual checkpoint semantic audit differs")
    for key in ("prior_initial_fingerprints", "prior_producer_parity", "prior_gradient_checks"):
        check(freeze[key] == historical[key], "Original first-fit runtime evidence differs")
    if require_approval:
        validate_execution_approval(read(folder / "execution_approval.json"), binding(root, folder / "execution_freeze.json"), freeze)
        diagnostic.validate_launch_readiness(read(folder / "launch_readiness.json"))
    check("torch" not in sys.modules, "Continuation metadata preflight imported Torch")
    return config, freeze, audit


def validate_execution_approval(approval, freeze_binding, freeze):
    check(approval.get("resume_approved") is True and approval.get("execution_freeze") == freeze_binding
          and approval.get("original_execution_approval") == freeze["original_execution_approval"]
          and approval.get("attempt") == "attempt_005" and approval.get("max_total_seconds") == MAX_TOTAL_SECONDS
          and approval.get("driver_version") == "617.42" and approval.get("debug_mode_enabled") is True
          and isinstance(approval.get("user_statement"), str) and approval["user_statement"].strip(),
          "New explicit approval for this exact scientific continuation is required")
    check(all(approval.get(key) is False for key in
              ("selector_approved", "protected_access_approved", "new_labels_approved", "automatic_retry")),
          "Scientific continuation scope differs")


def verify_runtime_driver(expected_gpu):
    """A launch-only read-only query; preparation never calls NVIDIA or Torch."""
    result = subprocess.run(["nvidia-smi", "--query-gpu=uuid,driver_version",
        "--format=csv,noheader,nounits", "--id=" + expected_gpu], capture_output=True,
        text=True, timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    check(result.returncode == 0, "NVIDIA driver verification failed: " + result.stderr)
    lines = result.stdout.strip().splitlines()
    check(len(lines) == 1, "Unexpected NVIDIA driver response")
    fields = [part.strip() for part in lines[0].split(",")]
    check(fields == [expected_gpu, "617.42"], "Expected GPU or post-install driver changed")
    return {"at_utc": stamp(), "gpu_uuid": fields[0], "driver_version": fields[1],
            "read_only_query": True, "settings_changed": False}


def validate_checkpoint_payload(payload, original_freeze_sha256, expected_shapes):
    """Validate the actual CPU-loaded producer payload, without a model forward."""
    import numpy as np
    import torch
    required = {"trainable_state", "optimizer_state", "epoch", "fit", "fit_steps", "counters",
                "python_rng", "numpy_rng", "torch_rng", "cuda_rng", "original_execution_freeze", "purpose",
                "diagnostic_counters", "accounting", "diagnostic_freeze"}
    check(set(payload) == required, "Checkpoint fields differ from actual diagnostic producer")
    check(payload["fit"] == "leave_chi_out" and payload["epoch"] == 6 and payload["fit_steps"] == 2244
          and payload["counters"] == RECOVERED_COUNTERS
          and all(type(value) is int for value in payload["counters"].values())
          and payload["original_execution_freeze"] == ORIGINAL_FREEZE
          and payload["original_execution_freeze"]["sha256"] == original_freeze_sha256
          and payload["diagnostic_freeze"] == DIAGNOSTIC_FREEZE
          and payload["purpose"] == "Separate stability diagnostic only; no scientific adoption or automatic continuation",
          "Diagnostic endpoint identity or unchanged historical purpose differs")
    check(payload["diagnostic_counters"] == CHECKPOINT_DIAGNOSTIC_COUNTERS
          and payload["accounting"] == diagnostic.accounting(payload["diagnostic_counters"])
          and payload["accounting"]["logical_replay_branch"] == payload["counters"],
          "Saved diagnostic/logical/physical accounting differs")
    state = payload["trainable_state"]
    check(len(state) == len(expected_shapes) == 42 and set(state) == set(expected_shapes), "Trainable name coverage differs")
    check(sum(math.prod(shape) for shape in expected_shapes.values()) == 3_600_641,
          "Trainable parameter count differs")
    for name, tensor in state.items():
        check(isinstance(tensor, torch.Tensor) and tensor.device.type == "cpu"
              and tensor.dtype == torch.float32 and tuple(tensor.shape) == tuple(expected_shapes[name])
              and bool(torch.isfinite(tensor).all()), "Invalid saved trainable tensor: " + name)
    optimizer = payload["optimizer_state"]
    check(set(optimizer) == {"state", "param_groups"} and len(optimizer["param_groups"]) == 2,
          "Unexpected AdamW state interface")
    parameter_ids = []
    for group, count, lr in zip(optimizer["param_groups"], (38, 4), (1e-5, 1e-3)):
        check(len(group["params"]) == count and group["lr"] == lr and group["weight_decay"] == .01
              and tuple(group["betas"]) == (.9, .999) and group["eps"] == 1e-8
              and group.get("amsgrad") is False and group.get("maximize") is False
              and group.get("capturable") is False and group.get("differentiable") is False,
              "Saved AdamW group or recipe differs")
        parameter_ids.extend(group["params"])
    check(len(set(parameter_ids)) == len(parameter_ids) == 42 and set(parameter_ids) == set(optimizer["state"]),
          "AdamW parameter state coverage differs")
    check(parameter_ids == list(range(42)), "Saved optimizer parameter order differs from producer")
    for parameter_id in parameter_ids:
        moment = optimizer["state"][parameter_id]
        check(set(moment) == {"step", "exp_avg", "exp_avg_sq"}, "Unexpected AdamW moment fields")
        check(all(isinstance(t, torch.Tensor) and t.device.type == "cpu" and bool(torch.isfinite(t).all())
                  for t in moment.values()), "AdamW moments must be finite CPU tensors")
        check(moment["step"].shape == torch.Size([]) and moment["step"].dtype == torch.float32
              and float(moment["step"]) == 2244,
              "Saved optimizer step differs")
        check(moment["exp_avg"].dtype == moment["exp_avg_sq"].dtype == torch.float32
              and moment["exp_avg"].shape == moment["exp_avg_sq"].shape,
              "Saved optimizer moment types/shapes differ")
    check(isinstance(payload["torch_rng"], torch.Tensor) and payload["torch_rng"].device.type == "cpu"
          and payload["torch_rng"].dtype == torch.uint8 and payload["torch_rng"].ndim == 1
          and payload["torch_rng"].numel() == torch.get_rng_state().numel(), "CPU RNG record differs")
    check(isinstance(payload["cuda_rng"], list) and len(payload["cuda_rng"]) == 1
          and all(isinstance(t, torch.Tensor) and t.device.type == "cpu" and t.dtype == torch.uint8
                  and t.ndim == 1 and t.numel() > 0 for t in payload["cuda_rng"]), "CUDA RNG record differs")
    probe = random.Random()
    probe.setstate(payload["python_rng"])
    np_probe = np.random.RandomState()
    np_probe.set_state(payload["numpy_rng"])
    return {"fit": payload["fit"], "epoch": 6, "steps": 2244, "trainable_tensors": 42,
            "trainable_parameters": 3600641, "all_saved_tensors_finite_on_cpu": True}


def restore_checkpoint(model, optimizer, payload, original_freeze_sha256, expected_shapes):
    """Restore weights/AdamW, then RNG last; never perform a neural forward."""
    import numpy as np
    import torch
    summary = validate_checkpoint_payload(payload, original_freeze_sha256, expected_shapes)
    named = {name: parameter for name, parameter in model.named_parameters() if parameter.requires_grad}
    check(set(named) == set(expected_shapes), "Live trainable names differ")
    live_groups = optimizer.state_dict()["param_groups"]
    saved_groups = payload["optimizer_state"]["param_groups"]
    check(len(live_groups) == len(saved_groups) == 2, "Live optimizer group count differs")
    named_by_identity = {id(parameter): name for name, parameter in named.items()}
    for live, saved, actual_group, prefix in zip(live_groups, saved_groups, optimizer.param_groups, ("backbone.", "head.")):
        check({k: v for k, v in live.items() if k != "params"}
              == {k: v for k, v in saved.items() if k != "params"}, "Live/saved AdamW settings differ")
        expected_names = [name for name in named if name.startswith(prefix)]
        actual_names = [named_by_identity.get(id(p)) for p in actual_group["params"]]
        check(actual_names == expected_names and len(saved["params"]) == len(actual_names),
              "Optimizer parameter ordering differs")
        for name, parameter_id in zip(actual_names, saved["params"]):
            moment = payload["optimizer_state"]["state"][parameter_id]
            check(tuple(moment["exp_avg"].shape) == tuple(named[name].shape) == tuple(expected_shapes[name]),
                  "AdamW moment/parameter mapping differs: " + name)
    with torch.no_grad():
        for name, parameter in named.items():
            check(parameter.dtype == torch.float32 and tuple(parameter.shape) == tuple(expected_shapes[name]),
                  "Live trainable dtype/shape differs")
            parameter.copy_(payload["trainable_state"][name].to(device=parameter.device))
    optimizer.load_state_dict(payload["optimizer_state"])
    for actual_group, saved_group in zip(optimizer.param_groups, saved_groups):
        for parameter, parameter_id in zip(actual_group["params"], saved_group["params"]):
            actual, saved = optimizer.state[parameter], payload["optimizer_state"]["state"][parameter_id]
            check(set(actual) == set(saved) and all(torch.equal(actual[k].detach().cpu(), saved[k]) for k in saved),
                  "AdamW state did not restore exactly")
    check(all(torch.equal(parameter.detach().cpu(), payload["trainable_state"][name])
              for name, parameter in named.items()), "Trainable state did not restore exactly")
    # Construction and loading may consume RNG. Restore only after all of them.
    random.setstate(payload["python_rng"])
    np.random.set_state(payload["numpy_rng"])
    torch.set_rng_state(payload["torch_rng"])
    torch.cuda.set_rng_state_all(payload["cuda_rng"])
    check(random.getstate() == payload["python_rng"] and torch.equal(torch.get_rng_state(), payload["torch_rng"]),
          "Python/Torch RNG restoration differs")
    actual_numpy = np.random.get_state()
    saved_numpy = payload["numpy_rng"]
    check(actual_numpy[0] == saved_numpy[0] and np.array_equal(actual_numpy[1], saved_numpy[1])
          and actual_numpy[2:] == saved_numpy[2:], "NumPy RNG restoration differs")
    return dict(summary, exact_trainable_restore=True, exact_AdamW_restore=True,
                python_numpy_torch_rng_restored=True, cuda_rng_restore_requested=len(payload["cuda_rng"]),
                rng_restored_after_model_and_optimizer=True)


def save_checkpoint_once(path, payload):
    """Publish only a fully flushed checkpoint; retain an incomplete file on error."""
    import torch
    check(not path.exists(), "Checkpoint already exists")
    temporary = path.with_name(path.name + ".incomplete")
    with temporary.open("xb") as stream:
        torch.save(payload, stream)
        stream.flush()
        os.fsync(stream.fileno())
    check(not path.exists(), "Checkpoint appeared before publication")
    temporary.rename(path)


def run(root, monitor, arguments):
    root = Path(root).resolve()
    config, freeze, audit = preflight(root, require_approval=True)
    check(monitor == MONITOR and list(arguments) == ["--run", "--monitor", MONITOR], "Only declared owned continuation is permitted")
    from .continuation_owned_guard import verify_owned_worker
    ownership = verify_owned_worker(root, root / monitor, MODULE, arguments)
    policy = read(root / monitor / "policy.json")
    validate_policy(policy)
    budget = remaining_wall_seconds(policy)
    driver = verify_runtime_driver(policy["gpu_uuid"])
    out = root / OUTPUT
    destination = make_attempt_directory(out)
    began = time.monotonic()
    counters = {key: 0 for key in RECOVERED_COUNTERS}
    write_once(destination / "started.json", {"at_utc": stamp(), "ownership": ownership,
        "recovery_approval": binding(root, root / PREPARATION / "execution_approval.json"),
        "recovery_freeze": binding(root, root / PREPARATION / "execution_freeze.json"),
        "original_execution_freeze": freeze["original_execution_freeze"], "budget": budget,
        "recovered_checkpoint": freeze["checkpoint"], "accounting": accounting(counters),
        "runtime_driver": driver, "source_diagnostic_completed": freeze["source_diagnostic_completed"],
        "settings_changed_by_worker": False, "launch_readiness": binding(root, root / PREPARATION / "launch_readiness.json"),
        "prior_failures_preserved": ["attempt_001", "attempt_002", "attempt_003", "reference_clock_diagnostic", "attempt_004"]})
    done = threading.Event()
    def deadline():
        # Recompute after receipt I/O so no worker startup cost is omitted.
        try:
            delay = remaining_wall_seconds(policy)["stop_wait_seconds"]
        except ValueError:
            delay = 0
        if not done.wait(delay):
            (root / monitor / "STOP").touch(exist_ok=True)
    threading.Thread(target=deadline, daemon=True).start()
    def require_running():
        if (root / monitor / "STOP").exists():
            raise KeyboardInterrupt("Supervised continuation requested STOP")
        remaining_wall_seconds(policy)
    caches = []
    try:
        require_running()
        check("torch" not in sys.modules, "Torch imported before owned recovery execution")
        os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
        import numpy as np
        import torch
        from . import candidate_quality_model as model_api
        from . import candidate_quality_evaluation as evaluation
        torch.set_num_threads(4)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.use_deterministic_algorithms(True)
        checkpoint = torch.load(bound(root, freeze["checkpoint"]), map_location="cpu", weights_only=False)
        expected_shapes = model_api.local_contract(root)["trainable_shapes"]
        validate_checkpoint_payload(checkpoint, freeze["original_execution_freeze"]["sha256"], expected_shapes)
        candidates = rows(out / "preparation/candidates.jsonl")
        by_id = {row["candidate_id"]: row for row in candidates}
        check(len(candidates) == len(by_id) == config["counts"]["training_package_candidates"], "Candidate transport differs")
        _, queries, _, _, _ = evaluation.load_prepared(root)
        emitted = [q for q in queries if q["input_id"] is not None]
        # Regenerate CPU pixels from bound original PNGs; do not trust unbound
        # cache files left by the unclean shutdown. This is not a model rerun.
        train_cache = original.make_crop_cache(root, candidates, "candidate_id", destination / "training_crops.npy", model_api)
        caches.append(train_cache[0])
        require_running()
        eval_cache = original.make_crop_cache(root, emitted, "query_id", destination / "evaluation_crops.npy", model_api)
        caches.append(eval_cache[0])
        journal = destination / "journal.jsonl"
        results = []
        for fit_name in original.FIT_NAMES:
            require_running()
            fit_dir = destination / fit_name
            fit_dir.mkdir()
            weights = rows(out / f"preparation/fits/{fit_name}/weights.jsonl")
            fit_manifest = read(out / f"preparation/fits/{fit_name}/manifest.json")
            fitting = original.validate_weights(by_id, weights)
            multipliers = {w["candidate_id"]: w["training_multiplier"] for w in weights}
            fit_games = original.validate_fit_membership(by_id, weights, fit_manifest, fit_name)
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
            first_epoch, fit_steps = fit_start(fit_name)
            if fit_name == "leave_chi_out":
                prior_initial = read(root / freeze["prior_initial_fingerprints"]["path"])
                check(frozen_before == prior_initial["frozen"] and trainable_before == prior_initial["trainable_groups"],
                      "Rebuilt original initialization differs before restore")
                restored = restore_checkpoint(model, optimizer, checkpoint,
                    freeze["original_execution_freeze"]["sha256"], expected_shapes)
                actual_cuda_rng = torch.cuda.get_rng_state_all()
                check(len(actual_cuda_rng) == len(checkpoint["cuda_rng"])
                      and all(torch.equal(actual.cpu(), saved) for actual, saved
                              in zip(actual_cuda_rng, checkpoint["cuda_rng"])),
                      "CUDA RNG restoration differs")
                restored["cuda_rng_restore_verified"] = True
                check(model_api.frozen_fingerprint(model) == frozen_before, "Restore changed frozen prefix")
                check(original.trainable_group_fingerprints(model) == audit["group_fingerprints"],
                      "Restored trainable group hashes differ from independent audit")
                write_once(fit_dir / "restored_checkpoint.json", dict(restored, checkpoint=freeze["checkpoint"],
                    inherited_initial=freeze["prior_initial_fingerprints"], inherited_parity=freeze["prior_producer_parity"],
                    inherited_first_gradients=freeze["prior_gradient_checks"], next_epoch=7,
                    source_diagnostic_freeze=freeze["source_diagnostic_freeze"], historical_purpose_preserved=True,
                    import_role="audited_fixed_first_fit_epoch_six_endpoint", additional_first_fit_training_updates=0,
                    recomputed_completed_epochs=False, runtime_driver=driver))
                write_once(fit_dir / "diagnostic_endpoint_import.json", {
                    "at_utc": stamp(), "source_checkpoint": freeze["checkpoint"],
                    "source_diagnostic_completed": freeze["source_diagnostic_completed"],
                    "source_diagnostic_freeze": freeze["source_diagnostic_freeze"],
                    "cpu_audit": freeze["checkpoint_audit"], "historical_purpose": checkpoint["purpose"],
                    "new_execution_approval": binding(root, root / PREPARATION / "execution_approval.json"),
                    "logical_fit_steps": 2244, "first_fit_training_updates_this_attempt": 0,
                    "scoring_still_required": True, "model_adopted": False,
                    "original_checkpoint_and_diagnostic_receipts_unchanged": True})
                del checkpoint
            for epoch in range(first_epoch, config["training"]["epochs"]+1):
                order = list(fitting)
                random.Random(config["training"]["seed"]+epoch).shuffle(order)
                model.train()
                epoch_loss = 0.0
                group_losses = defaultdict(lambda: [0.0, 0.0, 0])
                for batch in original.batches(order, config["training"]["batch_size"]):
                    require_running()
                    pixels, point_weights = original.input_batch(batch, *train_cache, "candidate_id")
                    targets = torch.tensor([r["target"] for r in batch], device="cuda", dtype=torch.float32)
                    scale = torch.tensor([multipliers[r["candidate_id"]] for r in batch], device="cuda", dtype=torch.float32)
                    optimizer.zero_grad(set_to_none=True)
                    counters["training_forwards_attempted"] += 1
                    append(journal, {"event": "train_start", "fit": fit_name, "epoch": epoch, "step": fit_steps,
                                     "batch_count": len(batch), "replays_known_lost_suffix": False})
                    first_batch = fit_steps == 0
                    if first_batch:
                        logits, actual_features = model.forward_with_features(pixels, point_weights)
                    else:
                        logits = model(pixels, point_weights)
                    check(logits.shape == targets.shape and bool(torch.isfinite(logits).all()), "Invalid training logits")
                    counters["training_forwards_returned"] += 1
                    if first_batch:
                        counters["parity_forwards_attempted"] += 1
                        append(journal, {"event": "parity_start", "fit": fit_name, "batch_count": len(batch)})
                        parity = original.first_batch_parity(model, pixels, point_weights, actual_features)
                        counters["parity_forwards_returned"] += 1
                        counters["parity_candidate_presentations"] += len(batch)
                        write_once(fit_dir / "initial_producer_point_parity.json", parity)
                        append(journal, {"event": "parity_return", "fit": fit_name, **parity})
                        del actual_features
                    losses = torch.nn.functional.binary_cross_entropy_with_logits(logits, targets, reduction="none")
                    loss = (losses*scale).mean()
                    check(bool(torch.isfinite(loss)), "Nonfinite training loss")
                    loss.backward()
                    if first_batch:
                        write_once(fit_dir / "first_gradient_checks.json", original.check_first_gradients(model))
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
                append(destination / "epochs.jsonl", {"fit": fit_name, "epoch": epoch, "weighted_online_loss": epoch_loss,
                    "group_loss_mass_weight_count": dict(group_losses), "note": "Online changing-model loss, not a held-out validation score"})
                recovery = fit_dir / f"recovery_epoch_{epoch:02d}.pth"
                save_checkpoint_once(recovery, {"trainable_state": {n: p.detach().cpu() for n, p in model.named_parameters() if p.requires_grad},
                    "optimizer_state": optimizer.state_dict(), "epoch": epoch, "fit": fit_name, "fit_steps": fit_steps,
                    "counters": accounting(counters)["logical"], "new_attempt_counters": dict(counters), "accounting": accounting(counters),
                    "python_rng": random.getstate(), "numpy_rng": np.random.get_state(), "torch_rng": torch.get_rng_state(),
                    "cuda_rng": torch.cuda.get_rng_state_all(), "freeze_sha256": freeze["original_execution_freeze"]["sha256"],
                    "recovery_freeze": binding(root, root / PREPARATION / "execution_freeze.json"),
                    "purpose": "Recovery only; fixed epoch6 remains the comparison checkpoint"})
                append(destination / "recovery_checkpoints.jsonl", binding(root, recovery))
                print(json.dumps({"fit": fit_name, "epoch": epoch, "logical_fit_steps": fit_steps,
                                  "new_updates": counters["optimizer_updates"], "weighted_online_loss": epoch_loss}), flush=True)
            check(fit_steps == math.ceil(len(fitting)/config["training"]["batch_size"])*config["training"]["epochs"], "Training step count differs")
            check(model_api.frozen_fingerprint(model) == frozen_before, "Frozen backbone tensors changed")
            trainable_after = original.trainable_group_fingerprints(model)
            check(all(trainable_after[group] != trainable_before[group] for group in trainable_before), "Trainable groups must change")
            write_once(fit_dir / "final_tensor_fingerprints.json", {"frozen": frozen_before, "trainable_groups": trainable_after,
                       "frozen_unchanged": True, "backbone_and_head_changed": True})
            final_checkpoint = fit_dir / "final_trainable.pth"
            save_checkpoint_once(final_checkpoint, {"trainable_state": {n: p.detach().cpu() for n, p in model.named_parameters() if p.requires_grad},
                "epoch": config["training"]["epochs"], "fit": fit_name, "freeze_sha256": freeze["original_execution_freeze"]["sha256"]})
            model.eval()
            score_groups = [("package_scores.jsonl", [r for r in candidates if fit_name == "all_nba"
                             or (r["domain"] == "nba" and r["game_id"] in set(fit_manifest["held_out_game_ids"]))], train_cache, "candidate_id")]
            expected_score_ids = (set(by_id) if fit_name == "all_nba" else {key for key, row in by_id.items()
                                  if row["domain"] == "nba" and row["game_id"] in set(original.FIT_GAMES["all_nba"])-fit_games})
            check({row["candidate_id"] for row in score_groups[0][1]} == expected_score_ids
                  and len(score_groups[0][1]) == len(expected_score_ids), "Held-game score membership differs")
            if fit_name == "all_nba":
                score_groups.append(("development_scores.jsonl", emitted, eval_cache, "query_id"))
            with torch.inference_mode():
                for filename, scoring, cache, id_field in score_groups:
                    for batch in original.batches(scoring, config["training"]["batch_size"]):
                        require_running()
                        pixels, point_weights = original.input_batch(batch, *cache, id_field)
                        counters["scoring_forwards_attempted"] += 1
                        append(journal, {"event": "score_start", "fit": fit_name, "file": filename, "count": len(batch)})
                        values = model(pixels, point_weights).detach().cpu().tolist()
                        check(len(values) == len(batch) and all(math.isfinite(v) for v in values), "Invalid score output")
                        counters["scoring_forwards_returned"] += 1
                        counters["scoring_candidate_presentations"] += len(batch)
                        for row, value in zip(batch, values):
                            append(fit_dir / filename, {id_field: row[id_field], "quality_logit": value})
                        append(journal, {"event": "score_return", "fit": fit_name, "file": filename, "count": len(batch)})
                        del pixels, point_weights
            result = {"fit": fit_name, "steps": fit_steps, "checkpoint": binding(root, final_checkpoint),
                      "frozen_tensors_unchanged": True, "fit_manifest": binding(root, out / f"preparation/fits/{fit_name}/manifest.json"),
                      "scores": [binding(root, fit_dir / group[0]) for group in score_groups],
                      "imported_diagnostic_epoch_six": fit_name == "leave_chi_out"}
            if fit_name == "leave_chi_out":
                result["diagnostic_endpoint_import"] = binding(root, fit_dir / "diagnostic_endpoint_import.json")
            write_once(fit_dir / "completed.json", result)
            results.append(result)
            del optimizer, model
            torch.cuda.empty_cache()
        totals = accounting(counters)
        logical = totals["logical"]
        check(logical["optimizer_updates"] == config["counts"]["optimizer_updates"] == 9870
              and counters["optimizer_updates"] == 7626, "Recovery update budget differs")
        check(logical["training_candidate_presentations"] == config["counts"]["training_candidate_presentations"] == 315432
              and counters["training_candidate_presentations"] == 243708, "Recovery presentations differ")
        check(logical["scoring_candidate_presentations"] == config["counts"]["scoring_candidate_presentations"], "Score presentations differ")
        check(counters["training_forwards_attempted"] == counters["training_forwards_returned"] == counters["optimizer_updates"], "Unreturned training call")
        check(counters["scoring_forwards_attempted"] == counters["scoring_forwards_returned"] == config["counts"]["scoring_forwards"], "Scoring calls differ")
        check(counters["parity_forwards_attempted"] == counters["parity_forwards_returned"] == 3
              and logical["parity_forwards_returned"] == 4 and logical["parity_candidate_presentations"] == 128,
              "Inherited/new parity budget differs")
        result = {"status": "completed_fixed_pilot_no_selector_no_adoption", "at_utc": stamp(),
            "elapsed_seconds": time.monotonic()-began, "budget": budget, "accounting": totals, "counters": logical,
            "fits": results, "recovery_completed": True, "original_failure_preserved": True,
            "prior_failures_preserved": ["attempt_001", "attempt_002", "attempt_003", "reference_clock_diagnostic", "attempt_004"], "runtime_driver": driver,
            "model_adopted": False, "protected_access": False,
            "new_labels": 0, "new_selector_runs": 0}
        write_once(destination / "completed.json", result)
        return result
    except BaseException as error:
        write_once(destination / "failed.json", {"at_utc": stamp(), "elapsed_seconds": time.monotonic()-began,
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
    args = parser.parse_args()
    if args.preflight:
        _, freeze, _ = preflight()
        print(json.dumps({"status": "CPU_metadata_recovery_preflight_passed_no_model_import",
                          "max_total_seconds": MAX_TOTAL_SECONDS, "historical_hour_budget_is_active_limit": False, "bindings": len(freeze["bindings"])}))
    else:
        print(json.dumps(run(ROOT, args.monitor, sys.argv[1:])))


if __name__ == "__main__":
    main()
