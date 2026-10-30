"""Three fresh single-game quality fits for the frozen acceptance experiment.

Import, preparation and preflight are metadata-only. Runtime requires the new
bound authorization, fresh readiness and the existing owned-job supervisor.
Old checkpoints, scores and crop caches are never overwritten or regenerated.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
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

ROOT = Path(__file__).resolve().parents[2]
BASE = "data/outputs/ball_tracking/candidate_acceptance_gate_v0_1"
LAUNCH_BASE = BASE + "/launch_v0_1"
NEURAL_OUTPUT = BASE + "/attempt_001/neural"
PREPARATION = LAUNCH_BASE + "/neural_preparation/preparation.json"
MONITOR = LAUNCH_BASE + "/monitoring/attempt_001"
MODULE = "src.ball_tracking.candidate_acceptance_neural"
CONFIG = "configs/ball_tracking/proposals/candidate_acceptance_gate_v0_1.json"
SPEC_SHA256 = "42bf1ff4571dba80f9845852e54cacd0f9a6021e9e19b1490fee24883deafb15"
ORIGINAL = "data/outputs/ball_tracking/candidate_quality_pilot_v0_1"
CANDIDATES = ORIGINAL + "/preparation/candidates.jsonl"
FRAMES = ORIGINAL + "/preparation/frames.jsonl"
CACHE = ORIGINAL + "/attempt_005/training_crops.npy"
GAMES = {"CHI": "0022400868", "DEN": "0022400866", "SAC": "0022500829"}
FIT_NAMES = tuple(name + "_only" for name in GAMES)
SEED, EPOCHS, BATCH_SIZE = 20261028, 6, 32
MAX_TOTAL_SECONDS, CLEANUP_RESERVE_SECONDS = 5400, 30
GPU = "GPU-f26f32f8-e85b-0d38-651e-d5c54097525b"
RUNTIME = {"torch": "2.13.0+cu130", "transformers": "5.14.1", "safetensors": "0.8.0",
           "numpy": "2.4.6", "Pillow": "12.3.0"}
DINO_LIBRARY = ".venv/Lib/site-packages/transformers/models/dinov2/modeling_dinov2.py"
DINO_LIBRARY_SHA256 = "9c7e028bdadef16e4fe6c59833ac916fe0a7987d1ac968a6f19aca40359ea9f8"
COUNTS = {
    "quality_fits": 3, "epochs_each": 6, "batch_size": 32,
    "optimizer_updates": 3300, "training_presentations": 105144,
    "cross_game_score_presentations": 37626,
    "cross_game_score_forwards_game_batched": 1178,
    "parity_forwards": 3, "parity_presentations": 96,
    "total_neural_forwards": 4481, "total_neural_presentations": 142866,
    "CPU_gate_fits": 8,
}
COUNTER_EXPECTED = {
    "training_forwards_attempted": 3300, "training_forwards_returned": 3300,
    "optimizer_updates": 3300, "training_candidate_presentations": 105144,
    "scoring_forwards_attempted": 1178, "scoring_forwards_returned": 1178,
    "scoring_candidate_presentations": 37626, "parity_forwards_attempted": 3,
    "parity_forwards_returned": 3, "parity_candidate_presentations": 96,
}
REQUIRED_IMPLEMENTATION = {
    "src/ball_tracking/candidate_acceptance_neural.py",
    "tests/test_candidate_acceptance_neural.py",
    "src/ball_tracking/candidate_quality_data.py",
    "src/ball_tracking/candidate_quality_model.py",
    "src/ball_tracking/candidate_quality_pilot.py",
    "src/ball_tracking/candidate_quality_native_cable_resume.py",
    "src/ball_tracking/continuation_owned_guard.py",
    "src/ball_tracking/point_feature_inference.py",
    "src/ball_tracking/nba_appearance_feature_screen.py",
}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def rows(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def owned_path(root, relative):
    root = Path(root).resolve()
    check(isinstance(relative, str) and not Path(relative).is_absolute(), "Expected repository-relative path")
    path = (root / relative).resolve()
    check(path.is_relative_to(root) and path != root, "Path escapes repository")
    return path


def binding(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    check(path.is_relative_to(root), "Binding escapes repository")
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return {"path": path.relative_to(root).as_posix(), "bytes": size, "sha256": digest.hexdigest()}


def bound(root, link):
    check(set(link) == {"path", "bytes", "sha256"}, "Invalid binding fields")
    path = owned_path(root, link["path"])
    check(binding(root, path) == link, "Binding differs: " + link["path"])
    return path


def write_once(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def append(path, value):
    with Path(path).open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps({"at_utc": stamp(), **value}, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def make_fit_plan(candidates, fit_name):
    """Recompute the original hierarchy using only this single game's labels."""
    from .candidate_quality_data import fit_weights
    check(fit_name in FIT_NAMES, "Unexpected single-game fit")
    name = fit_name.removesuffix("_only")
    game = GAMES[name]
    weights, summary = fit_weights(candidates, (game,))
    by_id = {row["candidate_id"]: row for row in candidates}
    expected = [row["candidate_id"] for row in candidates
                if row["domain"] == "nba" and row["game_id"] == game and row["target"] is not None]
    check([w["candidate_id"] for w in weights] == expected, "Single-game fit membership differs")
    fitting_frames = sorted({by_id[key]["frame_id"] for key in expected})
    groups = []
    for other, other_game in GAMES.items():
        if other == name:
            continue
        selected = [row for row in candidates if row["domain"] == "nba" and row["game_id"] == other_game]
        check(selected and not (set(fitting_frames) & {r["frame_id"] for r in selected}), "Held frames overlap fitting")
        groups.append({"name": other, "game_id": other_game,
                       "filename": f"scores_{other}.jsonl",
                       "candidate_ids": [r["candidate_id"] for r in selected],
                       "candidates": len(selected), "forwards": math.ceil(len(selected) / BATCH_SIZE)})
    return {"fit": fit_name, "fit_game_id": game, "fit_frame_ids": fitting_frames,
            "weights": weights, "summary": summary, "score_groups": groups,
            "initialization": "fresh_pinned_pretrained_DINO_and_seeded_head",
            "checkpoint_epoch": EPOCHS}


def plan_counts(plans):
    updates = sum(p["summary"]["total_training_steps"] for p in plans)
    presentations = EPOCHS * sum(p["summary"]["fitting_candidates"] for p in plans)
    scores = sum(g["candidates"] for p in plans for g in p["score_groups"])
    score_forwards = sum(g["forwards"] for p in plans for g in p["score_groups"])
    parity_presentations = sum(min(BATCH_SIZE, p["summary"]["fitting_candidates"]) for p in plans)
    return {"quality_fits": len(plans), "epochs_each": EPOCHS, "batch_size": BATCH_SIZE,
            "optimizer_updates": updates, "training_presentations": presentations,
            "cross_game_score_presentations": scores, "cross_game_score_forwards_game_batched": score_forwards,
            "parity_forwards": len(plans), "parity_presentations": parity_presentations,
            "total_neural_forwards": updates + score_forwards + len(plans),
            "total_neural_presentations": presentations + scores + parity_presentations, "CPU_gate_fits": 8}


def prepare_neural(root=ROOT, output=None):
    """Hash metadata/cache and prepare membership/weights; never open an image or model."""
    root = Path(root).resolve()
    spec_binding = binding(root, root / CONFIG)
    check(spec_binding["sha256"] == SPEC_SHA256, "Frozen acceptance specification changed")
    spec = read(root / CONFIG)
    check(spec["counts"] == COUNTS, "Frozen neural scope changed")
    links = {link["path"]: link for link in spec["input_bindings"]}
    for path in (CANDIDATES, FRAMES, CACHE, "src/ball_tracking/candidate_quality_data.py"):
        bound(root, links[path])
    candidates, frames = rows(root / CANDIDATES), rows(root / FRAMES)
    check(len(candidates) == len({r["candidate_id"] for r in candidates}) == 19632, "Original candidate transport differs")
    frame_index = {r["frame_id"]: r for r in frames}
    check(len(frames) == len(frame_index) == 3329, "Original frame transport differs")
    for row in candidates:
        frame = frame_index[row["frame_id"]]
        check(row["game_id"] == frame["game_id"] and row["domain"] == frame["domain"]
              and row["candidate_id"] in frame["candidate_ids"], "Candidate/frame provenance differs")
    plans = [make_fit_plan(candidates, name) for name in FIT_NAMES]
    for name, plan in zip(GAMES, plans):
        expected = spec["single_game_counts"][name]
        summary = plan["summary"]
        check(summary["fitting_candidates"] == expected["fitting_candidates"]
              and summary["stratum_counts"] == expected["fitting_targets"]
              and summary["total_training_steps"] == expected["updates"], "Single-game counts differ")
        for group in plan["score_groups"]:
            target = spec["single_game_counts"][group["name"]]
            check(group["candidates"] == target["all_candidates"]
                  and group["forwards"] == target["score_batches_per_presentation_of_this_game"], "Scoring counts differ")
    counts = plan_counts(plans)
    check(counts == COUNTS, "Exact new neural workload differs")
    result = {"schema": "candidate_acceptance_neural_preparation/v0.1", "specification": spec_binding,
              "candidate_source": links[CANDIDATES], "frame_source": links[FRAMES], "cache": links[CACHE],
              "cache_contract": {"shape": [19632, 64, 64, 3], "dtype": "uint8",
                                 "mode": "r", "row_order": "unchanged candidates.jsonl order"},
              "counts": counts, "fits": plans}
    if output is not None:
        output = Path(output).resolve()
        check(output.is_relative_to(root / BASE), "Preparation must stay in the new study")
        output.mkdir(parents=True, exist_ok=False)
        write_once(output / "preparation.json", result)
    return result


def validate_authorization(authorization, freeze_binding, specification):
    check(authorization.get("execution_approved") is True
          and authorization.get("execution_freeze") == freeze_binding
          and authorization.get("specification") == specification
          and authorization.get("scope") == COUNTS
          and authorization.get("max_total_seconds") == MAX_TOTAL_SECONDS
          and isinstance(authorization.get("user_statement"), str) and authorization["user_statement"].strip(),
          "Authorization must bind this freeze, specification and exact workload")
    check(all(authorization.get(key) is False for key in
              ("automatic_retry", "automatic_extension", "protected_access_approved", "new_labels_approved", "selector_approved")),
          "Authorization exceeds fixed experiment scope")


def validate_readiness(readiness, freeze_binding, authorization_binding, now=None):
    created = datetime.fromisoformat(readiness["at_utc"])
    now = now or datetime.now(timezone.utc)
    check(created.tzinfo is not None and created.utcoffset() == timedelta(0)
          and now.tzinfo is not None and now.utcoffset() == timedelta(0), "Readiness requires UTC timestamps")
    age = (now - created).total_seconds()
    check(math.isfinite(age) and -2 <= age <= 120, "Readiness stale or future dated")
    check(readiness.get("execution_freeze") == freeze_binding
          and readiness.get("execution_authorization") == authorization_binding, "Readiness binding differs")
    check(readiness.get("driver_version") == "617.42" and readiness.get("gpu_uuid") == GPU
          and readiness.get("power_limit_W") == 250 and readiness.get("ram_configured_mt_s") == [5200, 5200]
          and readiness.get("isolation_conflicts") == [] and readiness.get("existing_gpu_workers") == []
          and readiness.get("debug_mode_enabled") is True and readiness.get("debug_mode_state_basis") == "ui_observed"
          and readiness.get("configuration_changes") == [] and readiness.get("unexpected_setting_changes") == []
          and readiness.get("settings_changed") is False and readiness.get("settings_changed_by_agent") is False
          and readiness.get("fresh_launch_checks_passed") is True, "Fresh device/isolation/observed Debug ON checks required")
    temperature = readiness.get("temperature_C")
    check(isinstance(temperature, (int, float)) and math.isfinite(temperature) and 0 < temperature < 80,
          "Invalid launch temperature")
    check(isinstance(readiness.get("sources"), list) and len(readiness["sources"]) >= 3, "Readiness evidence missing")


def preflight(root=ROOT, require_approval=False):
    """Validate immutable preparation before any Torch or hardware operation."""
    root = Path(root).resolve()
    spec = read(root / CONFIG)
    specification = binding(root, root / CONFIG)
    check(specification["sha256"] == SPEC_SHA256 and spec["counts"] == COUNTS, "Specification differs")
    for name, version in RUNTIME.items():
        check(metadata.version(name) == version, "Pinned runtime metadata differs: " + name)
    check(binding(root, root / DINO_LIBRARY)["sha256"] == DINO_LIBRARY_SHA256, "Pinned DINO implementation differs")
    git_options = {"cwd": root, "text": True, "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    check(subprocess.check_output(["git", "branch", "--show-current"], **git_options).strip() == spec["branch"], "Branch differs")
    check(subprocess.check_output(["git", "rev-parse", "HEAD"], **git_options).strip() == spec["head"], "HEAD differs")
    check(not subprocess.check_output(["git", "diff", "--cached", "--name-only"], **git_options).strip(), "Index must remain empty")
    freeze_file = root / LAUNCH_BASE / "execution_freeze.json"
    freeze = read(freeze_file)
    check(freeze.get("status") == "frozen_for_authorized_execution"
          and freeze.get("specification") == specification
          and freeze.get("launch_base") == LAUNCH_BASE and freeze.get("neural_output") == NEURAL_OUTPUT,
          "Freeze identity, destination or specification differs")
    check(not (root / NEURAL_OUTPUT).exists(), "Neural output already exists; retry/resume is not authorized")
    implementation = freeze.get("implementation", [])
    check(REQUIRED_IMPLEMENTATION <= {link["path"] for link in implementation}, "Runtime source/test bindings missing")
    inputs = freeze.get("inputs", [])
    input_index = {link["path"]: link for link in inputs}
    check(len(input_index) == len(inputs), "Duplicate frozen inputs")
    check(all(input_index.get(link["path"]) == link for link in spec["input_bindings"])
          and PREPARATION in input_index, "Frozen preparation/original input coverage differs")
    check(isinstance(freeze.get("review"), list) and freeze["review"], "Independent review missing")
    for link in [spec["protocol"], *implementation, *inputs, freeze["focused_tests"], *freeze["review"]]:
        bound(root, link)
    prepared = prepare_neural(root)
    check(read(root / PREPARATION) == prepared, "Persisted neural preparation differs from independently regenerated membership/weights")
    if require_approval:
        freeze_binding = binding(root, freeze_file)
        auth_file = root / LAUNCH_BASE / "execution_authorization.json"
        validate_authorization(read(auth_file), freeze_binding, specification)
        readiness = read(root / LAUNCH_BASE / "launch_readiness.json")
        validate_readiness(readiness, freeze_binding, binding(root, auth_file))
        for link in readiness["sources"]:
            bound(root, link)
    check("torch" not in sys.modules, "Torch imported before authorized runtime")
    return spec, freeze


def validate_policy(policy):
    check(policy.get("module") == MODULE and policy.get("arguments") == ["--run", "--monitor", MONITOR]
          and policy.get("sample_seconds") == 2 and policy.get("temperature_stop_C") == 80
          and policy.get("telemetry_timeout_seconds") == 5 and policy.get("grace_seconds") == 10
          and policy.get("automatic_retry") is False and policy.get("max_total_seconds") == MAX_TOTAL_SECONDS
          and policy.get("soft_stop_seconds") == MAX_TOTAL_SECONDS - CLEANUP_RESERVE_SECONDS
          and policy.get("gpu_uuid") == GPU, "Owned supervisor policy differs")


def remaining_wall_seconds(policy, now=None):
    created = datetime.fromisoformat(policy["created_at_utc"])
    now = now or datetime.now(timezone.utc)
    check(created.tzinfo is not None and created.utcoffset() == timedelta(0)
          and now.tzinfo is not None and now.utcoffset() == timedelta(0), "Owned deadline requires UTC")
    elapsed = (now - created).total_seconds()
    check(math.isfinite(elapsed) and elapsed >= -2, "Owned deadline future dated")
    remaining = MAX_TOTAL_SECONDS - elapsed
    check(remaining > CLEANUP_RESERVE_SECONDS, "Owned wall deadline reached")
    return remaining


def validate_counters(counters):
    check(counters == COUNTER_EXPECTED, "Exact neural forward/presentation/update accounting differs")


def save_checkpoint_once(path, payload):
    import torch
    check(not path.exists(), "Checkpoint already exists")
    temporary = path.with_name(path.name + ".incomplete")
    with temporary.open("xb") as stream:
        torch.save(payload, stream)
        stream.flush()
        os.fsync(stream.fileno())
    check(not path.exists(), "Checkpoint appeared during save")
    temporary.rename(path)


def run(root, monitor, arguments):
    root = Path(root).resolve()
    check(monitor == MONITOR and list(arguments) == ["--run", "--monitor", MONITOR], "Only declared owned launch is allowed")
    spec, freeze = preflight(root, require_approval=True)
    from .continuation_owned_guard import verify_owned_worker
    ownership = verify_owned_worker(root, root / monitor, MODULE, arguments)
    policy = read(root / monitor / "policy.json")
    validate_policy(policy)
    remaining = remaining_wall_seconds(policy)
    from . import candidate_quality_pilot as pilot
    from .candidate_quality_native_cable_resume import verify_runtime_driver
    driver = verify_runtime_driver(policy["gpu_uuid"])
    out = root / NEURAL_OUTPUT
    out.mkdir(parents=True, exist_ok=False)
    began, done, caches = time.monotonic(), threading.Event(), []
    counters = dict.fromkeys(COUNTER_EXPECTED, 0)
    freeze_binding = binding(root, root / LAUNCH_BASE / "execution_freeze.json")
    write_once(out / "started.json", {"at_utc": stamp(), "ownership": ownership, "driver": driver,
               "execution_freeze": freeze_binding,
               "execution_authorization": binding(root, root / LAUNCH_BASE / "execution_authorization.json"),
               "launch_readiness": binding(root, root / LAUNCH_BASE / "launch_readiness.json"),
               "settings_changed_by_worker": False, "new_work_only": True})

    def deadline():
        if not done.wait(max(0.0, remaining - CLEANUP_RESERVE_SECONDS)):
            (root / monitor / "STOP").touch(exist_ok=True)

    def continuation_check():
        check(not (root / monitor / "STOP").exists(), "Owned supervisor requested STOP")
        remaining_wall_seconds(policy)

    threading.Thread(target=deadline, daemon=True).start()
    try:
        continuation_check()
        check("torch" not in sys.modules, "Torch imported before authorized deterministic runtime")
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
        candidates = rows(root / CANDIDATES)
        by_id = {r["candidate_id"]: r for r in candidates}
        indices = {r["candidate_id"]: i for i, r in enumerate(candidates)}
        preparation = read(root / PREPARATION)
        cache = np.load(root / CACHE, mmap_mode="r", allow_pickle=False)
        caches.append(cache)
        check(cache.shape == (19632, 64, 64, 3) and cache.dtype == np.uint8 and not cache.flags.writeable,
              "Reused read-only crop cache contract differs")
        geometry = np.asarray([model_api.point_geometry(r["center_xy_px"], r["width_px"], r["height_px"])["weights"]
                               for r in candidates], dtype=np.float64)
        cache_args = (cache, geometry, indices)
        journal, results = out / "journal.jsonl", []
        for plan in preparation["fits"]:
            continuation_check()
            fit_name = plan["fit"]
            fit_dir = out / fit_name
            fit_dir.mkdir(exist_ok=False)
            write_once(fit_dir / "fit_manifest.json", plan)
            fitting = pilot.validate_weights(by_id, plan["weights"])
            multipliers = {w["candidate_id"]: w["training_multiplier"] for w in plan["weights"]}
            random.seed(SEED)
            np.random.seed(SEED)
            torch.manual_seed(SEED)
            torch.cuda.manual_seed_all(SEED)
            model = model_api.build_model(root, device="cuda", execution_authorized=True, seed=SEED)
            frozen_before = model_api.frozen_fingerprint(model)
            trainable_before = pilot.trainable_group_fingerprints(model)
            write_once(fit_dir / "initial_tensor_fingerprints.json", {"frozen": frozen_before, "trainable_groups": trainable_before})
            write_once(fit_dir / "trainable_parameters.json", model_api.trainable_manifest(model))
            optimizer = torch.optim.AdamW(model_api.optimizer_parameter_groups(model), betas=(0.9, 0.999), eps=1e-8)
            fit_steps, recoveries = 0, []
            for epoch in range(1, EPOCHS + 1):
                order = list(fitting)
                random.Random(SEED + epoch).shuffle(order)
                model.train()
                epoch_loss, group_losses = 0.0, defaultdict(lambda: [0.0, 0.0, 0])
                for batch in pilot.batches(order, BATCH_SIZE):
                    continuation_check()
                    pixels, point_weights = pilot.input_batch(batch, *cache_args, "candidate_id")
                    targets = torch.tensor([r["target"] for r in batch], device="cuda", dtype=torch.float32)
                    scale = torch.tensor([multipliers[r["candidate_id"]] for r in batch], device="cuda", dtype=torch.float32)
                    optimizer.zero_grad(set_to_none=True)
                    counters["training_forwards_attempted"] += 1
                    append(journal, {"event": "train_start", "fit": fit_name, "epoch": epoch, "step": fit_steps, "batch_count": len(batch)})
                    first_batch = fit_steps == 0
                    if first_batch:
                        logits, actual_features = model.forward_with_features(pixels, point_weights)
                    else:
                        logits = model(pixels, point_weights)
                    check(logits.shape == targets.shape and bool(torch.isfinite(logits).all()), "Invalid training logits")
                    counters["training_forwards_returned"] += 1
                    if first_batch:
                        continuation_check()
                        counters["parity_forwards_attempted"] += 1
                        append(journal, {"event": "parity_start", "fit": fit_name, "batch_count": len(batch)})
                        parity = pilot.first_batch_parity(model, pixels, point_weights, actual_features)
                        counters["parity_forwards_returned"] += 1
                        counters["parity_candidate_presentations"] += len(batch)
                        write_once(fit_dir / "initial_producer_point_parity.json", parity)
                        append(journal, {"event": "parity_return", "fit": fit_name, **parity})
                        del actual_features
                    losses = torch.nn.functional.binary_cross_entropy_with_logits(logits, targets, reduction="none")
                    loss = (losses * scale).mean()
                    check(bool(torch.isfinite(loss)), "Nonfinite training loss")
                    loss.backward()
                    if first_batch:
                        write_once(fit_dir / "first_gradient_checks.json", pilot.check_first_gradients(model))
                    grad_norm = torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], max_norm=1.0, error_if_nonfinite=True)
                    check(all(p.grad is None for p in model.parameters() if not p.requires_grad), "Frozen gradient appeared")
                    optimizer.step()
                    fit_steps += 1
                    counters["optimizer_updates"] += 1
                    counters["training_candidate_presentations"] += len(batch)
                    weighted = (losses * scale).detach().cpu().tolist()
                    for row, value in zip(batch, weighted):
                        objective_weight = multipliers[row["candidate_id"]] / len(fitting)
                        contribution = value / len(fitting)
                        epoch_loss += contribution
                        group = group_losses[row["target_group"]]
                        group[0] += contribution
                        group[1] += objective_weight
                        group[2] += 1
                    append(journal, {"event": "train_return", "fit": fit_name, "epoch": epoch, "step": fit_steps,
                                     "weighted_batch_loss": float(loss.detach().cpu()), "gradient_norm_before_clip": float(grad_norm.detach().cpu())})
                    del pixels, point_weights, targets, scale, logits, losses, loss, grad_norm
                check(fit_steps == epoch * plan["summary"]["steps_per_epoch"], "Epoch update count differs")
                append(out / "epochs.jsonl", {"fit": fit_name, "epoch": epoch, "weighted_online_loss": epoch_loss,
                       "group_loss_mass_weight_count": dict(group_losses), "note": "Online changing-model loss; not held-out validation"})
                continuation_check()
                recovery = fit_dir / f"recovery_epoch_{epoch:02d}.pth"
                save_checkpoint_once(recovery, {
                    "trainable_state": {n: p.detach().cpu() for n, p in model.named_parameters() if p.requires_grad},
                    "optimizer_state": optimizer.state_dict(), "epoch": epoch, "fit": fit_name,
                    "fit_steps": fit_steps, "counters": dict(counters), "python_rng": random.getstate(),
                    "numpy_rng": np.random.get_state(), "torch_rng": torch.get_rng_state(),
                    "cuda_rng": torch.cuda.get_rng_state_all(), "freeze_sha256": freeze_binding["sha256"],
                    "purpose": "Recovery only after separate authorization; fixed epoch6 remains the endpoint"})
                recoveries.append(binding(root, recovery))
                append(out / "recovery_checkpoints.jsonl", recoveries[-1])
                print(json.dumps({"fit": fit_name, "epoch": epoch, "steps": fit_steps, "weighted_online_loss": epoch_loss}), flush=True)
            check(fit_steps == plan["summary"]["total_training_steps"], "Fit update count differs")
            check(model_api.frozen_fingerprint(model) == frozen_before, "Frozen backbone tensors changed")
            trainable_after = pilot.trainable_group_fingerprints(model)
            check(all(trainable_after[group] != trainable_before[group] for group in trainable_before), "Head/backbone did not both change")
            write_once(fit_dir / "final_tensor_fingerprints.json", {"frozen": frozen_before, "trainable_groups": trainable_after,
                       "frozen_unchanged": True, "backbone_and_head_changed": True})
            checkpoint = fit_dir / "final_trainable.pth"
            save_checkpoint_once(checkpoint, {"trainable_state": {n: p.detach().cpu() for n, p in model.named_parameters() if p.requires_grad},
                                 "epoch": EPOCHS, "fit": fit_name, "freeze_sha256": freeze_binding["sha256"]})
            model.eval()
            score_bindings = []
            with torch.inference_mode():
                for group in plan["score_groups"]:
                    scoring = [by_id[key] for key in group["candidate_ids"]]
                    score_path = fit_dir / group["filename"]
                    scored_ids = []
                    # Each target game gets its own batches, preserving the frozen 1,178 forwards.
                    with score_path.open("x", encoding="utf-8", newline="\n") as stream:
                        for batch in pilot.batches(scoring, BATCH_SIZE):
                            continuation_check()
                            pixels, point_weights = pilot.input_batch(batch, *cache_args, "candidate_id")
                            counters["scoring_forwards_attempted"] += 1
                            append(journal, {"event": "score_start", "fit": fit_name, "game": group["name"], "count": len(batch)})
                            values = model(pixels, point_weights).detach().cpu().tolist()
                            check(len(values) == len(batch) and all(math.isfinite(v) for v in values), "Invalid score output")
                            counters["scoring_forwards_returned"] += 1
                            counters["scoring_candidate_presentations"] += len(batch)
                            for row, value in zip(batch, values):
                                scored_ids.append(row["candidate_id"])
                                stream.write(json.dumps({"candidate_id": row["candidate_id"], "quality_logit": value,
                                    "game_id": row["game_id"], "frame_id": row["frame_id"], "fit": fit_name,
                                    "source_index": indices[row["candidate_id"]]}, allow_nan=False) + "\n")
                            stream.flush()
                            os.fsync(stream.fileno())
                            append(journal, {"event": "score_return", "fit": fit_name, "game": group["name"], "count": len(batch)})
                            del pixels, point_weights
                    check(scored_ids == group["candidate_ids"], "Score identity/order transport differs")
                    score_bindings.append(binding(root, score_path))
            result = {"fit": fit_name, "steps": fit_steps, "checkpoint": binding(root, checkpoint),
                      "recovery_checkpoints": recoveries, "scores": score_bindings,
                      "fit_manifest": binding(root, fit_dir / "fit_manifest.json"),
                      "frozen_tensors_unchanged": True, "cumulative_counters": dict(counters),
                      "health": [binding(root, fit_dir / name) for name in
                                 ("initial_tensor_fingerprints.json", "final_tensor_fingerprints.json",
                                  "trainable_parameters.json", "initial_producer_point_parity.json", "first_gradient_checks.json")]}
            write_once(fit_dir / "completed.json", result)
            results.append(result)
            del optimizer, model
            torch.cuda.empty_cache()
        validate_counters(counters)
        result = {"status": "completed_three_single_game_quality_fits_no_adoption", "at_utc": stamp(),
                  "elapsed_seconds": time.monotonic() - began, "counters": counters, "counts": COUNTS,
                  "fits": results, "execution_freeze": freeze_binding, "model_adopted": False,
                  "old_studies_rerun": False, "protected_access": False, "new_labels": 0,
                  "settings_changed": False, "automatic_retry": False}
        write_once(out / "completed.json", result)
        return result
    except BaseException as error:
        write_once(out / "failed.json", {"at_utc": stamp(), "elapsed_seconds": time.monotonic() - began,
                   "error": type(error).__name__, "message": str(error), "traceback": traceback.format_exc(),
                   "counters": counters, "automatic_retry": False})
        raise
    finally:
        done.set()
        for cache in caches:
            cache._mmap.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--monitor")
    args = parser.parse_args()
    if args.run:
        print(json.dumps(run(ROOT, args.monitor, sys.argv[1:])), flush=True)
    else:
        spec, _ = preflight(ROOT)
        print(json.dumps({"status": "metadata_preflight_passed_no_runtime", "counts": spec["counts"]}), flush=True)


if __name__ == "__main__":
    main()
