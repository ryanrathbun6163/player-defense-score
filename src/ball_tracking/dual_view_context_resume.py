"""Additive exact-checkpoint continuation after the recorded launcher deadline bug.

All attempt_001 outputs and source files remain immutable. A distinct owned run
performs only SAC/LC epochs4-6 and the two all-NBA fits, with explicit physical
accounting for the67 discarded updates replayed from the epoch3 checkpoint.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from importlib import metadata
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

from . import dual_view_context_experiment as prior

ROOT, BASE, CONFIG = prior.ROOT, prior.BASE, prior.CONFIG
SPEC_SHA256, PROTOCOL, PROTOCOL_SHA256 = prior.SPEC_SHA256, prior.PROTOCOL, prior.PROTOCOL_SHA256
LAUNCH_BASE = BASE+"/launch_v0_2"
NEURAL_OUTPUT = BASE+"/attempt_002"
MONITOR = LAUNCH_BASE+"/monitoring/attempt_002"
MODULE = "src.ball_tracking.dual_view_context_resume"
PREPARATION = prior.PREPARATION
PRIOR_OUTPUT = prior.NEURAL_OUTPUT
PRIOR_FREEZE = prior.LAUNCH_BASE+"/execution_freeze.json"
PRIOR_FREEZE_SHA256 = "a0fbcf9343665b81bdaf6e92cf179a79c24a41a35dfc2ea6743299118248aaff"
CHECKPOINT = PRIOR_OUTPUT+"/fits/leave_sac_out/LC/recovery_epoch_03.pth"
CHECKPOINT_SHA256 = "73f441cb6509694beac40f227739e52ce456e7872e82e025394a43a772e0dbdf"
CHECKPOINT_BYTES = 45434731
PRIOR_FAILED = PRIOR_OUTPUT+"/failed.json"
PRIOR_LAUNCH_FINISHED = prior.LAUNCH_BASE+"/launcher_finished.json"
CAPTURE_MANIFEST = PRIOR_OUTPUT+"/all_local_capture_verified_before_fitting.json"
SHARED_INITIAL = PRIOR_OUTPUT+"/shared_initial_trainable.pth"
FIT_NAMES, ARMS, BATCH_SIZE, EPOCHS, SEED = prior.FIT_NAMES, prior.ARMS, prior.BATCH_SIZE, prior.EPOCHS, prior.SEED
GPU = prior.GPU
MAX_TOTAL_SECONDS, CLEANUP_RESERVE_SECONDS, PRIOR_CHARGED_SECONDS = 3611, 30, 1789
COMPLETED_FITS = (("leave_chi_out", "LL"), ("leave_chi_out", "LC"), ("leave_den_out", "LL"),
                  ("leave_den_out", "LC"), ("leave_sac_out", "LL"))
NEW_FITS = (("leave_sac_out", "LC"), ("all_nba", "LL"), ("all_nba", "LC"))
CALL_BUDGETS = {"local_capture": (0, 0), "training": (7626, 243834), "scoring": (2754, 88032),
                "local_parity": (0, 0), "auxiliary_parity": (2, 64)}
COUNTER_EXPECTED = {key: value for kind, (calls, presentations) in CALL_BUDGETS.items()
                    for key, value in ((kind+"_forwards_attempted", calls), (kind+"_forwards_returned", calls),
                                       (kind+"_candidate_presentations", presentations))}
COUNTER_EXPECTED["optimizer_updates"] = 7626
PHYSICAL_EXPECTED = dict(prior.COUNTER_EXPECTED)
for _key in ("training_forwards_attempted", "training_forwards_returned", "optimizer_updates"):
    PHYSICAL_EXPECTED[_key] += 67
PHYSICAL_EXPECTED["training_candidate_presentations"] += 2144
REQUIRED_IMPLEMENTATION = prior.REQUIRED_IMPLEMENTATION | {
    "src/ball_tracking/dual_view_context_resume.py", "tests/test_dual_view_context_resume.py",
    "src/ball_tracking/dual_view_context_recovery_deadline.py",
}
REQUIRED_INPUTS = {PRIOR_FREEZE, CHECKPOINT, PRIOR_FAILED, PRIOR_LAUNCH_FINISHED, CAPTURE_MANIFEST, SHARED_INITIAL,
                   PRIOR_OUTPUT+"/journal.jsonl", PRIOR_OUTPUT+"/recovery_checkpoints.jsonl"}
REQUIRED_INPUTS |= {PRIOR_OUTPUT+f"/fits/{fit}/{arm}/completed.json" for fit, arm in COMPLETED_FITS}
io = prior.io
check, read, rows, binding, bound = prior.check, prior.read, prior.rows, prior.binding, prior.bound
write_once, append, stamp = prior.write_once, prior.append, prior.stamp


def validate_recovery_checkpoint(checkpoint, weights, freeze_sha256=PRIOR_FREEZE_SHA256):
    """Inspect actual CPU-loaded tensors/optimizer/RNG without a model forward."""
    import numpy as np
    import torch
    check(checkpoint["fit"] == "leave_sac_out" and checkpoint["arm"] == "LC" and checkpoint["epoch"] == 3
          and checkpoint["fit_steps"] == 1050 and checkpoint["freeze_sha256"] == freeze_sha256,
          "Recovery checkpoint identity/endpoint differs")
    check(checkpoint["actual_exposures"] == {w["row_key"]: 3 for w in weights}
          and len(weights) == 11182, "Recovery checkpoint original three-epoch exposures differ")
    state = checkpoint["trainable_state"]
    check(sum(value.numel() for value in state.values()) == 3698945, "Recovery trainable parameter count differs")
    for name, value in state.items():
        check(isinstance(value, torch.Tensor) and value.device.type == "cpu" and value.dtype == torch.float32
              and bool(torch.isfinite(value).all()), "Invalid recovered trainable tensor: "+name)
    names = [[n for n in state if n.startswith(prefix)] for prefix in ("backbone.", "head.")]
    check(set(sum(names, [])) == set(state) and all(names), "Recovery tensor groups differ")
    optimizer = checkpoint["optimizer_state"]
    check(len(optimizer["param_groups"]) == 2, "Recovery optimizer group count differs")
    ids = []
    for group, group_names, lr in zip(optimizer["param_groups"], names, (1e-5, 1e-3), strict=True):
        check(group["lr"] == lr and group["weight_decay"] == .01 and tuple(group["betas"]) == (.9, .999)
              and group["eps"] == 1e-8 and group["amsgrad"] is False and group["maximize"] is False
              and group["capturable"] is False and group["differentiable"] is False
              and len(group["params"]) == len(group_names), "Recovery optimizer recipe/group membership differs")
        ids.extend(group["params"])
        for parameter_id, name in zip(group["params"], group_names, strict=True):
            item = optimizer["state"][parameter_id]
            check(set(item) == {"step", "exp_avg", "exp_avg_sq"}, "Unexpected AdamW state fields")
            check(item["step"].device.type == "cpu" and float(item["step"]) == 1050., "AdamW per-parameter step differs")
            for field in ("exp_avg", "exp_avg_sq"):
                tensor = item[field]
                check(tensor.device.type == "cpu" and tensor.dtype == torch.float32 and tensor.shape == state[name].shape
                      and bool(torch.isfinite(tensor).all()), "Invalid recovered optimizer moment")
            check(bool((item["exp_avg_sq"] >= 0).all()), "Negative Adam second moment")
    check(len(ids) == len(set(ids)) == len(state) and set(ids) == set(optimizer["state"]), "AdamW parameter mapping differs")
    python_rng = random.Random()
    python_rng.setstate(checkpoint["python_rng"])
    numpy_rng = np.random.RandomState()
    numpy_rng.set_state(checkpoint["numpy_rng"])
    cpu_rng = checkpoint["torch_rng"]
    check(cpu_rng.device.type == "cpu" and cpu_rng.dtype == torch.uint8 and cpu_rng.ndim == 1 and cpu_rng.numel() > 0,
          "Invalid recovered CPU Torch RNG")
    check(len(checkpoint["cuda_rng"]) == 1 and all(t.device.type == "cpu" and t.dtype == torch.uint8
          and t.ndim == 1 and t.numel() > 0 for t in checkpoint["cuda_rng"]), "Invalid recovered CUDA RNG payload")
    check(checkpoint["counters"]["optimizer_updates"] == 12114
          and checkpoint["counters"]["training_forwards_returned"] == 12114
          and checkpoint["counters"]["training_candidate_presentations"] == 387030,
          "Checkpoint cumulative execution endpoint differs")
    return {"fit": "leave_sac_out", "arm": "LC", "epoch": 3, "fit_steps": 1050,
            "trainable_parameters": 3698945, "optimizer_parameters": len(ids), "known_rows": len(weights),
            "visits_each": 3, "optimizer_moments_finite": True, "RNG_payloads_present": True,
            "CPU_Torch_rng_bytes": cpu_rng.numel(), "CUDA_rng_bytes": [t.numel() for t in checkpoint["cuda_rng"]]}


def restore_recovery(model, optimizer, checkpoint, weights, *, restore_rng):
    """Restore tensors then AdamW, then RNG; optimizer group order is verified."""
    import numpy as np
    import torch
    result = validate_recovery_checkpoint(checkpoint, weights)
    parameters = {n: p for n, p in model.named_parameters() if p.requires_grad}
    check(list(parameters) == list(checkpoint["trainable_state"]), "Runtime recovery parameter order differs")
    with torch.no_grad():
        for name, parameter in parameters.items():
            value = checkpoint["trainable_state"][name]
            check(parameter.shape == value.shape and parameter.dtype == value.dtype, "Runtime recovery tensor shape/dtype differs")
            parameter.copy_(value.to(parameter.device))
    optimizer.load_state_dict(checkpoint["optimizer_state"])
    recovered = optimizer.state_dict()
    check(recovered["param_groups"] == checkpoint["optimizer_state"]["param_groups"], "Restored optimizer recipe/order differs")
    for pid, state in recovered["state"].items():
        for field, value in state.items():
            check(torch.equal(value.detach().cpu(), checkpoint["optimizer_state"]["state"][pid][field]),
                  "Restored optimizer state changed: "+field)
    check(all(torch.equal(p.detach().cpu(), checkpoint["trainable_state"][n]) for n, p in parameters.items()),
          "Recovered trainable values differ")
    if restore_rng:
        check(torch.cuda.is_initialized(), "CUDA RNG restoration requires owned initialized runtime")
        random.setstate(checkpoint["python_rng"])
        np.random.set_state(checkpoint["numpy_rng"])
        torch.set_rng_state(checkpoint["torch_rng"])
        torch.cuda.set_rng_state_all(checkpoint["cuda_rng"])
        check(torch.equal(torch.get_rng_state(), checkpoint["torch_rng"])
              and all(torch.equal(a, b) for a, b in zip(torch.cuda.get_rng_state_all(), checkpoint["cuda_rng"], strict=True)),
              "Restored Torch RNG state differs")
    return {**result, "trainable_and_optimizer_roundtrip_exact": True, "RNG_restored_to_runtime": restore_rng}


def replay_records(root, weights):
    """Identify only the already recorded, discarded epoch4 prefix."""
    records = []
    with (Path(root)/PRIOR_OUTPUT/"journal.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["event"] == "optimizer_update" and row.get("fit") == "leave_sac_out" and row.get("arm") == "LC" and row["epoch"] == 4:
                records.append(row)
    expected = list(prior.batches(prior.epoch_order(weights, 4)))[:67]
    check(len(records) == len(expected) == 67, "Discarded epoch4 prefix length differs")
    for number, (row, keys) in enumerate(zip(records, expected, strict=True), 1051):
        check(row["step"] == number and row["row_keys"] == keys and row["batch_count"] == 32,
              "Discarded updates are not the exact first67 full epoch4 batches")
    check(sum(r["batch_count"] for r in records) == 2144, "Replay presentation count differs")
    return {row["step"]: row for row in records}


def preflight(root=ROOT, require_authorization=True, *, require_approval=None):
    if require_approval is not None:
        require_authorization = require_approval
    root = Path(root).resolve()
    check("torch" not in sys.modules, "Torch imported before recovery preflight")
    spec, specification = read(root/CONFIG), binding(root, root/CONFIG)
    check(specification["sha256"] == SPEC_SHA256, "Original scientific proposal changed")
    options = {"cwd": root, "text": True, "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    check(subprocess.check_output(["git", "branch", "--show-current"], **options).strip() == prior.EXPECTED_BRANCH
          and subprocess.check_output(["git", "rev-parse", "HEAD"], **options).strip() == prior.EXPECTED_HEAD
          and not subprocess.check_output(["git", "diff", "--cached", "--name-only"], **options).strip(), "Frozen Git state differs")
    for name, version in io.RUNTIME.items():
        check(metadata.version(name) == version, "Pinned runtime differs: "+name)
    from . import dual_view_context_model as model_api
    model_api.local_contract(root)
    old_freeze = read(root/PRIOR_FREEZE)
    check(binding(root, root/PRIOR_FREEZE)["sha256"] == PRIOR_FREEZE_SHA256, "Original freeze changed")
    for link in [old_freeze["specification"], old_freeze["protocol"], *old_freeze["implementation"], *old_freeze["inputs"],
                 old_freeze["focused_tests"], *old_freeze["review"]]:
        bound(root, link)
    frozen_path = root/LAUNCH_BASE/"execution_freeze.json"
    freeze = read(frozen_path)
    check(freeze.get("status") == "frozen_for_authorized_execution" and freeze.get("specification") == specification
          and freeze.get("protocol") == spec["protocol"] and freeze.get("launch_base") == LAUNCH_BASE
          and freeze.get("neural_output") == NEURAL_OUTPUT and freeze.get("prior_execution_freeze") == binding(root, root/PRIOR_FREEZE)
          and freeze.get("consumed_wall_seconds") == PRIOR_CHARGED_SECONDS and freeze.get("max_total_seconds") == MAX_TOTAL_SECONDS,
          "Recovery freeze identity or charged budget differs")
    check(not (root/NEURAL_OUTPUT).exists(), "Continuation output already exists; no additional attempt authorized")
    implementation, inputs = freeze["implementation"], freeze["inputs"]
    check(REQUIRED_IMPLEMENTATION <= {r["path"] for r in implementation}, "Missing continuation implementation binding")
    input_index = {r["path"]: r for r in inputs}
    check(len(input_index) == len(inputs) and REQUIRED_INPUTS <= set(input_index)
          and input_index[CHECKPOINT] == {"path": CHECKPOINT, "bytes": CHECKPOINT_BYTES, "sha256": CHECKPOINT_SHA256}
          and input_index.get(PREPARATION) == freeze["prepared"], "Missing/changed recovery source binding")
    check(freeze["review"] and freeze.get("prior_partial_audit"), "Recovery independent reviews missing")
    for link in [*implementation, *inputs, freeze["focused_tests"], *freeze["review"], freeze["prior_partial_audit"]]:
        bound(root, link)
    audit = read(root/freeze["prior_partial_audit"]["path"])
    check(audit.get("status", "").startswith("passed"), "Partial-output audit did not pass")
    failed, launcher = read(root/PRIOR_FAILED), read(root/PRIOR_LAUNCH_FINISHED)
    check(failed["message"] == "Owned supervisor requested STOP" and launcher["event_remaining_owned_processes"] == 0
          and launcher["supervisor_result"]["remaining_owned_processes_before_close"] == 0
          and launcher["supervisor_result"]["job_cleanup_error"] is None
          and math.ceil(launcher["charged_elapsed_seconds"]) == PRIOR_CHARGED_SECONDS,
          "Prior failure/cleanup/charged wall record differs")
    check({k: failed["counters"][k]+COUNTER_EXPECTED[k] for k in COUNTER_EXPECTED} == PHYSICAL_EXPECTED,
          "Prior+continuation physical budget differs")
    from . import dual_view_context_data as data
    loaded = data.load_prepared(root, verify=True)
    prior.validate_loaded(loaded, spec)
    replay_records(root, loaded["fits"]["leave_sac_out"]["weights"])
    if require_authorization:
        freeze_binding = binding(root, frozen_path)
        auth_file = root/LAUNCH_BASE/"execution_authorization.json"
        authorization = read(auth_file)
        check(authorization.get("execution_approved") is True and authorization.get("execution_freeze") == freeze_binding
              and authorization.get("specification") == specification and authorization.get("scope") == COUNTER_EXPECTED
              and authorization.get("max_total_seconds") == MAX_TOTAL_SECONDS and authorization.get("user_statement"),
              "Continuation authorization differs from bound routine correction")
        check(all(authorization.get(k) is False for k in ("automatic_retry", "automatic_extension", "protected_access_approved", "new_labels_approved", "selector_approved")),
              "Continuation authorization expands scientific scope")
        readiness = read(root/LAUNCH_BASE/"launch_readiness.json")
        io.validate_readiness(readiness, freeze_binding, binding(root, auth_file))
        for link in readiness["sources"]:
            bound(root, link)
    check("torch" not in sys.modules, "Recovery preflight imported Torch")
    return spec, freeze


def validate_policy(policy):
    from . import dual_view_context_recovery_deadline as deadline
    deadline.validate_contract(policy)
    check(policy.get("module") == MODULE and policy.get("arguments") == ["--run", "--monitor", MONITOR]
          and policy.get("sample_seconds") == 2 and policy.get("temperature_stop_C") == 80
          and policy.get("telemetry_timeout_seconds") == 5 and policy.get("grace_seconds") == 10
          and policy.get("automatic_retry") is False and policy.get("max_total_seconds") == MAX_TOTAL_SECONDS
          and policy.get("soft_stop_seconds") == MAX_TOTAL_SECONDS-CLEANUP_RESERVE_SECONDS
          and policy.get("gpu_uuid") == GPU, "Owned continuation supervisor policy differs")


def remaining_wall_seconds(policy):
    from . import dual_view_context_recovery_deadline as deadline
    remaining = deadline.remaining_wall_seconds(policy)
    check(remaining > CLEANUP_RESERVE_SECONDS, "Charged continuation wall deadline reached")
    return remaining


def call_started(counters, kind, journal, details):
    key = kind+"_forwards_attempted"
    check(kind in CALL_BUDGETS and counters[key] < COUNTER_EXPECTED[key], "Continuation forward budget exhausted")
    counters[key] += 1
    append(journal, {"event": kind+"_start", **details, "counters": dict(counters)})


def call_returned(counters, kind, journal, details):
    returned, presentations = kind+"_forwards_returned", kind+"_candidate_presentations"
    check(counters[returned] < counters[kind+"_forwards_attempted"]
          and counters[presentations]+details["batch_count"] <= COUNTER_EXPECTED[presentations], "Continuation return/presentation budget differs")
    counters[returned] += 1
    counters[presentations] += details["batch_count"]
    append(journal, {"event": kind+"_return", **details, "counters": dict(counters)})


def run(root, monitor, arguments):
    root = Path(root).resolve()
    check(monitor == MONITOR and list(arguments) == ["--run", "--monitor", MONITOR], "Only declared owned continuation is allowed")
    spec, freeze = preflight(root, require_authorization=True)
    from .continuation_owned_guard import verify_owned_worker
    ownership = verify_owned_worker(root, root/monitor, MODULE, arguments)
    policy = read(root/monitor/"policy.json")
    validate_policy(policy)
    remaining = remaining_wall_seconds(policy)
    from .candidate_quality_native_cable_resume import verify_runtime_driver
    driver = verify_runtime_driver(policy["gpu_uuid"])
    out = root/NEURAL_OUTPUT
    out.mkdir(parents=True, exist_ok=False)
    began, done, caches, feature_caches = time.monotonic(), threading.Event(), {}, {}
    counters = dict.fromkeys(COUNTER_EXPECTED, 0)
    previous_counters = read(root/PRIOR_FAILED)["counters"]
    freeze_binding = binding(root, root/LAUNCH_BASE/"execution_freeze.json")
    write_once(out/"started.json", {"at_utc": stamp(), "ownership": ownership, "driver": driver,
               "execution_freeze": freeze_binding, "prior_execution_freeze": freeze["prior_execution_freeze"],
               "prepared": freeze["prepared"], "prior_failed": binding(root, root/PRIOR_FAILED),
               "recovery_checkpoint": binding(root, root/CHECKPOINT), "previous_physical_counters": previous_counters,
               "execution_authorization": binding(root, root/LAUNCH_BASE/"execution_authorization.json"),
               "launch_readiness": binding(root, root/LAUNCH_BASE/"launch_readiness.json"),
               "consumed_wall_seconds": PRIOR_CHARGED_SECONDS, "max_continuation_seconds": MAX_TOTAL_SECONDS,
               "settings_changed_by_worker": False, "prior_results_preserved": True})

    def deadline():
        if not done.wait(max(0., remaining-CLEANUP_RESERVE_SECONDS)):
            (root/monitor/"STOP").touch(exist_ok=True)

    def continuation_check():
        check(not (root/monitor/"STOP").exists(), "Owned supervisor requested STOP")
        remaining_wall_seconds(policy)

    threading.Thread(target=deadline, daemon=True).start()
    try:
        continuation_check()
        check("torch" not in sys.modules, "Torch imported before owned continuation runtime")
        os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
        import numpy as np
        import torch
        from . import candidate_quality_pilot as pilot
        from . import dual_view_context_model as model_api
        from . import dual_view_context_data as data
        torch.set_num_threads(4)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.use_deterministic_algorithms(True)
        loaded = data.load_prepared(root, verify=True)
        prior.validate_loaded(loaded, spec)
        caches = prior.open_caches(root, loaded)
        capture_manifest = read(root/CAPTURE_MANIFEST)
        local_artifacts = capture_manifest["local_captures"]
        check(len(local_artifacts) == 6, "Original local capture inventory differs")
        locations = {fit: {} for fit in FIT_NAMES}
        for artifact in local_artifacts:
            fit, group = artifact["fit"], artifact["group"]
            expected_keys = next(g["row_keys"] for g in loaded["fits"][fit]["capture_groups"] if g["name"] == group)
            records = rows(bound(root, prior.basic_binding(artifact)))
            check([r["row_key"] for r in records] == expected_keys, "Imported local feature identity/order differs")
            path = bound(root, artifact["features"])
            cache = np.load(path, mmap_mode="r", allow_pickle=False)
            check(cache.shape == (len(records), 384) and cache.dtype == np.float64, "Imported local feature matrix differs")
            feature_caches[artifact["features"]["path"]] = cache
            for number, row in enumerate(records):
                check(row["feature_index"] == number and row["fit"] == fit and row["group"] == group
                      and row["row_key"] not in locations[fit], "Imported local feature index differs")
                locations[fit][row["row_key"]] = artifact["features"]["path"], number
        results = [read(root/PRIOR_OUTPUT/f"fits/{fit}/{arm}/completed.json") for fit, arm in COMPLETED_FITS]
        check([(r["fit"], r["arm"]) for r in results] == list(COMPLETED_FITS), "Preserved five-fit order differs")
        all_scores = [score for result in results for score in result["scores"]]
        for result in results:
            for link in [result["checkpoint"], result["fit_manifest"], result["actual_exposure"],
                         *result["health"], *result["recovery_checkpoints"]]:
                bound(root, link)
            for score in result["scores"]:
                for link in [prior.basic_binding(score), score["point_features"], score["CLS_features"]]:
                    bound(root, link)
        initial_record = torch.load(root/SHARED_INITIAL, map_location="cpu", weights_only=True)
        initial_trainable, initial_reference = initial_record["trainable_state"], initial_record["fingerprints"]
        check(initial_record["freeze_sha256"] == PRIOR_FREEZE_SHA256 and initial_record["seed"] == SEED,
              "Shared original initialization changed")
        discarded = replay_records(root, loaded["fits"]["leave_sac_out"]["weights"])
        replay_comparisons = []
        journal = out/"journal.jsonl"
        write_once(out/"reused_results.json", {"local_captures": local_artifacts,
                   "completed_fits": [binding(root, root/PRIOR_OUTPUT/f"fits/{fit}/{arm}/completed.json") for fit, arm in COMPLETED_FITS],
                   "shared_initial_trainable": binding(root, root/SHARED_INITIAL),
                   "prior_partial_audit": freeze["prior_partial_audit"], "additional_capture_or_completed_fit_calls": 0})

        def inputs(keys, fit, arm):
            pixels, points = prior.input_arrays(loaded, caches, keys, arm)
            local = np.stack([feature_caches[locations[fit][key][0]][locations[fit][key][1]] for key in keys])
            return (torch.from_numpy(local).to("cuda"), torch.from_numpy(pixels).to("cuda"), torch.from_numpy(points).to("cuda"))

        def score_group(model, fit, arm, group, fit_dir):
            name, keys = group["name"], group["row_keys"]
            score_dir = fit_dir/"scores"
            score_dir.mkdir(exist_ok=True)
            score_path, point_path, cls_path = (score_dir/(name+suffix) for suffix in (".jsonl", "_point.npy", "_cls.npy"))
            check(not point_path.exists() and not cls_path.exists(), "Continuation feature outputs already exist")
            point_array = np.lib.format.open_memmap(point_path, mode="w+", dtype=np.float64, shape=(len(keys), 384))
            cls_array = np.lib.format.open_memmap(cls_path, mode="w+", dtype=np.float64, shape=(len(keys), 384))
            try:
                with score_path.open("x", encoding="utf-8", newline="\n") as stream, torch.inference_mode():
                    offset = 0
                    for batch in prior.batches(keys):
                        continuation_check()
                        local, pixels, points = inputs(batch, fit, arm)
                        details = {"fit": fit, "arm": arm, "group": name, "row_keys": batch, "batch_count": len(batch)}
                        call_started(counters, "scoring", journal, details)
                        logits, point, cls = model.forward_with_features(local, pixels, points)
                        call_returned(counters, "scoring", journal, details)
                        point_array[offset:offset+len(batch)] = point.detach().cpu().numpy()
                        cls_array[offset:offset+len(batch)] = cls.detach().cpu().numpy()
                        for row in prior.score_rows(batch, logits.detach().cpu().tolist(), fit, arm, name, offset):
                            stream.write(json.dumps(row, allow_nan=False)+"\n")
                        stream.flush()
                        os.fsync(stream.fileno())
                        offset += len(batch)
                        del local, pixels, points, logits, point, cls
                    check(offset == len(keys), "Continuation score identity count differs")
                point_array.flush()
                cls_array.flush()
            finally:
                point_array._mmap.close()
                cls_array._mmap.close()
            return {**binding(root, score_path), "fit": fit, "arm": arm, "group": name, "role": group["role"],
                    "rows": len(keys), "point_features": binding(root, point_path), "CLS_features": binding(root, cls_path)}

        for fit, arm in NEW_FITS:
            continuation_check()
            item, resumed = loaded["fits"][fit], fit == "leave_sac_out"
            weights = item["weights"]
            by_key = {w["row_key"]: w for w in weights}
            fit_dir = out/"fits"/fit/arm
            fit_dir.mkdir(parents=True, exist_ok=False)
            write_once(fit_dir/"fit_manifest.json", {"fit": fit, "arm": arm, "weights": weights,
                       "score_groups": item["score_groups"], "shuffle_seed_base": prior.SHUFFLE_SEED, "epochs": EPOCHS,
                       "prepared": freeze["prepared"], "execution_freeze": freeze_binding,
                       "start_epoch": 4 if resumed else 1, "recovered_original_checkpoint": binding(root, root/CHECKPOINT) if resumed else None})
            random.seed(SEED)
            np.random.seed(SEED)
            torch.manual_seed(SEED)
            torch.cuda.manual_seed_all(SEED)
            model = model_api.build_model(root, device="cuda", execution_authorized=True)
            frozen_before = model_api.frozen_fingerprint(model)
            trainable_before = pilot.trainable_group_fingerprints(model)
            check({"frozen": frozen_before, "trainable_groups": trainable_before} == initial_reference,
                  "Continuation generic auxiliary/head initial tensors differ")
            optimizer = torch.optim.AdamW(model_api.optimizer_parameter_groups(model), betas=(.9, .999), eps=1e-8)
            write_once(fit_dir/"trainable_parameters.json", model_api.trainable_manifest(model))
            if resumed:
                recovery = torch.load(root/CHECKPOINT, map_location="cpu", weights_only=False)
                restore_receipt = restore_recovery(model, optimizer, recovery, weights, restore_rng=True)
                check(model_api.frozen_fingerprint(model) == frozen_before, "Recovery changed frozen generic prefix")
                write_once(fit_dir/"checkpoint_restoration.json", {**restore_receipt, "checkpoint": binding(root, root/CHECKPOINT),
                           "restored_trainable_fingerprints": pilot.trainable_group_fingerprints(model), "frozen_prefix_unchanged": True})
                fit_steps, visits, start_epoch = 1050, Counter(recovery["actual_exposures"]), 4
                recoveries = [binding(root, root/PRIOR_OUTPUT/f"fits/{fit}/{arm}/recovery_epoch_{e:02d}.pth") for e in (1, 2, 3)]
                imported_health = [binding(root, root/PRIOR_OUTPUT/f"fits/{fit}/{arm}/{name}") for name in
                                   ("initial_tensor_fingerprints.json", "first_gradient_checks.json", "initial_producer_parity.json")]
                write_once(fit_dir/"imported_initial_health.json", {"original_receipts": imported_health,
                           "new_first_batch_parity_calls": 0, "reason": "Original six-fit parity and exact checkpoint restoration retained"})
                del recovery
            else:
                fit_steps, visits, start_epoch, recoveries, imported_health = 0, Counter(), 1, [], []
                write_once(fit_dir/"initial_tensor_fingerprints.json", initial_reference)
            start_steps = fit_steps
            for epoch in range(start_epoch, EPOCHS+1):
                model.train()
                epoch_loss, group_losses, epoch_steps = 0., defaultdict(lambda: [0., 0., 0]), 0
                for keys in prior.batches(prior.epoch_order(weights, epoch)):
                    continuation_check()
                    local, pixels, points = inputs(keys, fit, arm)
                    targets = torch.tensor([by_key[k]["target"] for k in keys], device="cuda", dtype=torch.float32)
                    scale = torch.tensor([by_key[k]["training_multiplier"] for k in keys], device="cuda", dtype=torch.float32)
                    optimizer.zero_grad(set_to_none=True)
                    replayed = resumed and epoch == 4 and fit_steps+1 in discarded
                    details = {"fit": fit, "arm": arm, "epoch": epoch, "step": fit_steps,
                               "row_keys": keys, "batch_count": len(keys), "replayed_discarded_update": replayed}
                    call_started(counters, "training", journal, details)
                    logits, point, cls = model.forward_with_features(local, pixels, points)
                    call_returned(counters, "training", journal, details)
                    first = fit_steps == 0
                    if first:
                        continuation_check()
                        call_started(counters, "auxiliary_parity", journal, details)
                        parity = model_api.first_batch_parity(model, pixels, points, point, cls)
                        call_returned(counters, "auxiliary_parity", journal, details)
                        write_once(fit_dir/"initial_producer_parity.json", parity)
                    losses = torch.nn.functional.binary_cross_entropy_with_logits(logits, targets, reduction="none")
                    loss = (losses*scale).mean()
                    check(bool(torch.isfinite(loss)), "Nonfinite continuation training loss")
                    loss.backward()
                    if first:
                        write_once(fit_dir/"first_gradient_checks.json", pilot.check_first_gradients(model))
                    elif resumed and fit_steps == start_steps:
                        write_once(fit_dir/"first_resumed_gradient_checks.json", pilot.check_first_gradients(model))
                    norm = torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], max_norm=1., error_if_nonfinite=True)
                    check(all(p.grad is None for p in model.parameters() if not p.requires_grad)
                          and local.grad is None and not local.requires_grad, "Frozen/local gradient appeared")
                    optimizer.step()
                    fit_steps += 1
                    epoch_steps += 1
                    counters["optimizer_updates"] += 1
                    check(counters["optimizer_updates"] <= COUNTER_EXPECTED["optimizer_updates"], "Continuation update budget exceeded")
                    visits.update(keys)
                    loss_value, norm_value = float(loss.detach().cpu()), float(norm.detach().cpu())
                    if replayed:
                        original_event = discarded[fit_steps]
                        check(keys == original_event["row_keys"], "Required replay batch identity differs")
                        replay_comparisons.append({"fit_step": fit_steps, "rows": len(keys),
                            "original_weighted_batch_loss": original_event["weighted_batch_loss"], "replayed_weighted_batch_loss": loss_value,
                            "original_gradient_norm": original_event["gradient_norm_before_clip"], "replayed_gradient_norm": norm_value,
                            "loss_identical": loss_value == original_event["weighted_batch_loss"],
                            "gradient_norm_identical": norm_value == original_event["gradient_norm_before_clip"]})
                    for key, value in zip(keys, (losses*scale).detach().cpu().tolist(), strict=True):
                        weight = by_key[key]
                        group = loaded["rows"][key].get("target_group", str(weight["target"]))
                        contribution = value/len(weights)
                        epoch_loss += contribution
                        bucket = group_losses[group]
                        bucket[0] += contribution
                        bucket[1] += weight["objective_weight"]
                        bucket[2] += 1
                    append(journal, {"event": "optimizer_update", **details, "step": fit_steps,
                                     "weighted_batch_loss": loss_value, "gradient_norm_before_clip": norm_value, "counters": dict(counters)})
                    del local, pixels, points, targets, scale, logits, point, cls, losses, loss, norm
                check(epoch_steps == math.ceil(len(weights)/BATCH_SIZE) and all(visits[k] == epoch for k in by_key),
                      "Continuation epoch exact exposures differ")
                append(out/"epochs.jsonl", {"fit": fit, "arm": arm, "epoch": epoch, "online_weighted_BCE": epoch_loss,
                       "group_loss_objective_mass_count": dict(group_losses), "note": "Full logical epoch; discarded prefix replay separately charged"})
                continuation_check()
                recovery_path = fit_dir/f"recovery_epoch_{epoch:02d}.pth"
                io.save_checkpoint_once(recovery_path, {"trainable_state": {n: p.detach().cpu() for n, p in model.named_parameters() if p.requires_grad},
                    "optimizer_state": optimizer.state_dict(), "epoch": epoch, "fit": fit, "arm": arm, "fit_steps": fit_steps,
                    "continuation_counters": dict(counters), "physical_counters": {k: previous_counters[k]+counters[k] for k in counters},
                    "actual_exposures": dict(visits), "python_rng": random.getstate(), "numpy_rng": np.random.get_state(),
                    "torch_rng": torch.get_rng_state(), "cuda_rng": torch.cuda.get_rng_state_all(), "freeze_sha256": freeze_binding["sha256"],
                    "purpose": "Preserved recovery only; no automatic additional attempt"})
                recoveries.append(binding(root, recovery_path))
                append(out/"recovery_checkpoints.jsonl", recoveries[-1])
                print(json.dumps({"fit": fit, "arm": arm, "epoch": epoch, "logical_fit_steps": fit_steps,
                                  "continuation_updates": counters["optimizer_updates"], "online_weighted_BCE": epoch_loss}), flush=True)
            check(fit_steps == EPOCHS*math.ceil(len(weights)/BATCH_SIZE) and set(visits) == set(by_key)
                  and all(v == 6 for v in visits.values()), "Logical final fit endpoint differs")
            write_once(fit_dir/"actual_exposure.json", [{"row_key": k, "visits": visits[k]} for k in by_key])
            check(model_api.frozen_fingerprint(model) == frozen_before, "Continuation changed frozen tensors")
            trainable_after = pilot.trainable_group_fingerprints(model)
            check(all(trainable_after[g] != initial_reference["trainable_groups"][g] for g in trainable_after), "Trainable groups did not change")
            write_once(fit_dir/"final_tensor_fingerprints.json", {"frozen": frozen_before, "trainable_groups": trainable_after,
                       "frozen_unchanged": True, "backbone_and_head_changed": True})
            write_once(fit_dir/"parameter_deltas.json", prior.parameter_deltas(model, initial_trainable))
            checkpoint_path = fit_dir/"final_trainable.pth"
            io.save_checkpoint_once(checkpoint_path, {"trainable_state": {n: p.detach().cpu() for n, p in model.named_parameters() if p.requires_grad},
                                    "epoch": 6, "fit": fit, "arm": arm, "fit_steps": fit_steps, "freeze_sha256": freeze_binding["sha256"]})
            model.eval()
            score_bindings = [score_group(model, fit, arm, group, fit_dir) for group in item["score_groups"]]
            all_scores.extend(score_bindings)
            health_names = ["final_tensor_fingerprints.json", "parameter_deltas.json"]
            health_names += ["checkpoint_restoration.json", "first_resumed_gradient_checks.json", "imported_initial_health.json"] if resumed else [
                "initial_tensor_fingerprints.json", "first_gradient_checks.json", "initial_producer_parity.json"]
            result = {"fit": fit, "arm": arm, "steps": fit_steps, "continuation_optimizer_updates": fit_steps-start_steps,
                      "checkpoint": binding(root, checkpoint_path), "recovery_checkpoints": recoveries, "scores": score_bindings,
                      "fit_manifest": binding(root, fit_dir/"fit_manifest.json"), "actual_exposure": binding(root, fit_dir/"actual_exposure.json"),
                      "health": imported_health+[binding(root, fit_dir/name) for name in health_names],
                      "frozen_tensors_unchanged": True, "continuation_counters": dict(counters),
                      "resumed_checkpoint": binding(root, root/CHECKPOINT) if resumed else None}
            write_once(fit_dir/"completed.json", result)
            results.append(result)
            del model, optimizer
            torch.cuda.empty_cache()
        continuation_check()
        check(counters == COUNTER_EXPECTED, "Exact continuation physical workload differs")
        physical = {k: previous_counters[k]+counters[k] for k in counters}
        check(physical == PHYSICAL_EXPECTED and len(results) == 8 and len(replay_comparisons) == 67, "Combined physical accounting differs")
        replay_result = {"rows": replay_comparisons, "replayed_discarded_updates": 67, "replayed_presentations": 2144,
                         "all_loss_and_gradient_norm_values_identical": all(r["loss_identical"] and r["gradient_norm_identical"] for r in replay_comparisons),
                         "max_absolute_loss_difference": max(abs(r["original_weighted_batch_loss"]-r["replayed_weighted_batch_loss"]) for r in replay_comparisons),
                         "max_absolute_gradient_norm_difference": max(abs(r["original_gradient_norm"]-r["replayed_gradient_norm"]) for r in replay_comparisons),
                         "comparison_is_diagnostic": True, "extra_forward_calls_for_comparison": 0}
        write_once(out/"required_replay_diagnostic.json", replay_result)
        result = {"status": "completed_exact_recovered_logical_workload", "at_utc": stamp(), "elapsed_seconds": time.monotonic()-began,
                  "execution_freeze": freeze_binding, "prior_execution_freeze": freeze["prior_execution_freeze"], "prepared": freeze["prepared"],
                  "counters": physical, "physical_counters": physical, "logical_counters": dict(prior.COUNTER_EXPECTED),
                  "continuation_counters": dict(counters), "prior_physical_counters": previous_counters,
                  "prior_failure": binding(root, root/PRIOR_FAILED), "prior_partial_audit": freeze["prior_partial_audit"],
                  "fits": results, "all_scores": all_scores, "local_captures": local_artifacts,
                  "shared_initial_trainable": binding(root, root/SHARED_INITIAL), "initial_tensors_identical_all_eight": initial_reference,
                  "local_capture_checks": capture_manifest["checks"], "replayed_discarded_updates": 67, "replayed_presentations": 2144,
                  "replay_diagnostic": binding(root, out/"required_replay_diagnostic.json"), "prior_consumed_wall_seconds": PRIOR_CHARGED_SECONDS,
                  "automatic_retry": False, "automatic_extension": False, "selector_changed": False,
                  "independent_CPU_audit_required": True, "original_failed_attempt_preserved_as_failed": True}
        write_once(out/"completed.json", result)
        return result
    except BaseException as error:
        write_once(out/"failed.json", {"at_utc": stamp(), "elapsed_seconds": time.monotonic()-began,
                   "error": type(error).__name__, "message": str(error), "traceback": traceback.format_exc(),
                   "continuation_counters": dict(counters), "physical_counters": {k: previous_counters[k]+counters[k] for k in counters},
                   "automatic_retry": False})
        raise
    finally:
        done.set()
        prior.close_caches(caches)
        prior.close_caches(feature_caches)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--monitor")
    args = parser.parse_args()
    if args.run:
        print(json.dumps(run(ROOT, args.monitor, sys.argv[1:])), flush=True)
    else:
        preflight(ROOT, require_authorization=False)
        print(json.dumps({"status": "metadata_continuation_preflight_passed", "continuation_counters": COUNTER_EXPECTED}), flush=True)


if __name__ == "__main__":
    main()
