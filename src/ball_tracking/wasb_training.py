"""One preset WASB adaptation on reviewed pilots, with resumable safe checkpoints.

Only pilot annotation bodies and pilot image frames enter training. Development
and holdout exclusions are checked from manifest metadata, never their labels.
Publication of an already trained final state never repeats optimizer updates.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import random
import shutil
import sys
import time
import traceback
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import torch
from torch import nn

from .annotations import load_annotations, verify_source_video_contract
from .wasb_adapter import WasbAdapter, affine_matrices, preprocess_triplet
from .wasb_experiment import bound_path, canonical, digest_file, read_json, repository_path, write_once

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = "configs/ball_tracking/wasb_experiments/wasb_basketball_adaptation_v0_1.json"
UPDATES, BATCH_SIZE, SEED = 200, 2, 1234
PILOT_RANGES = {"possession_001": (375, 399), "possession_002": (318, 342), "possession_003": (416, 440)}


def binding(root, path):
    return {"path": path.resolve().relative_to(root.resolve()).as_posix(), "sha256": digest_file(path)}


def annotation_kind(annotation):
    if (annotation.annotation_status == "labeled" and annotation.localization_eligible
            and annotation.game_ball_identity_certainty in {"certain", "probable"}):
        return "positive"
    if (annotation.annotation_status == "labeled" and annotation.visibility == "not_visible"
            and annotation.game_ball_identity_certainty == "certain"):
        return "hidden"
    return "masked"


def annotation_target(annotation, source_width, source_height):
    """Official affine float32 point, int32 truncation, binary radius2.5 disk."""
    target = np.zeros((288, 512), dtype=np.float32)
    kind = annotation_kind(annotation)
    center = None
    if kind == "positive":
        transform, _ = affine_matrices(source_width, source_height)
        x, y = annotation.geometry.center_xy_px
        center = (transform @ np.array([x, y, 1.0], dtype=np.float32)).astype(np.int32)
        # Upstream's negative-center convention produces an empty map.
        if center[0] >= 0 and center[1] >= 0:
            yy, xx = np.indices(target.shape)
            target[(xx - center[0]) ** 2 + (yy - center[1]) ** 2 <= 2.5 ** 2] = 1
    return target, kind != "masked", {"kind": kind, "integer_heatmap_center": None if center is None else center.tolist()}


def masked_wbce(logits, targets, valid_channels):
    if (logits.ndim != 4 or targets.shape != logits.shape
            or tuple(valid_channels.shape) != tuple(logits.shape[:2])
            or logits.dtype != torch.float32 or targets.dtype != torch.float32
            or valid_channels.dtype != torch.bool):
        raise ValueError("Expected float32 [batch,channels,height,width] and boolean channel mask")
    if not bool(valid_channels.any()):
        raise ValueError("A training batch must have supervised output pixels")
    prediction = logits[valid_channels].sigmoid().clamp(1e-4, 1 - 1e-4)
    truth = targets[valid_channels]
    if not bool(torch.isfinite(truth).all()) or not bool(((truth == 0) | (truth == 1)).all()):
        raise ValueError("Supervised target pixels must be binary and finite")
    terms = -((1 - prediction) ** 2 * truth * torch.log(prediction)
              + prediction ** 2 * (1 - truth) * torch.log(1 - prediction))
    # Boolean channel indexing removes masked channels from both numerator and denominator.
    return terms.mean()


def freeze_batch_norm(model):
    model.train()
    for parameter in model.parameters():
        parameter.requires_grad_(True)
    for module in model.modules():
        if isinstance(module, nn.modules.batchnorm._BatchNorm):
            module.eval()
    return {name: tensor.detach().clone() for name, tensor in model.named_buffers()
            if name.endswith(("running_mean", "running_var", "num_batches_tracked"))}


def assert_batch_norm_unchanged(model, reference):
    buffers = dict(model.named_buffers())
    if any(module.training for module in model.modules() if isinstance(module, nn.modules.batchnorm._BatchNorm)):
        raise ValueError("BatchNorm running-statistics updates were enabled")
    if set(reference) != {name for name in buffers if name.endswith(("running_mean", "running_var", "num_batches_tracked"))}:
        raise ValueError("BatchNorm buffer inventory changed")
    if reference and not bool(torch.stack([
            torch.eq(buffers[name], saved.to(buffers[name].device)).all() for name, saved in reference.items()]).all()):
        raise ValueError("BatchNorm running buffers changed")


def training_step(model, optimizer, inputs, targets, valid_channels):
    if any(module.training for module in model.modules() if isinstance(module, nn.modules.batchnorm._BatchNorm)):
        raise ValueError("BatchNorm must remain in evaluation mode")
    optimizer.zero_grad(set_to_none=True)
    outputs = model(inputs)
    if not isinstance(outputs, dict) or set(outputs) != {0} or outputs[0].shape != targets.shape:
        raise ValueError("Expected WASB scale0 logits aligned to the supervised triplet")
    if not bool(torch.isfinite(outputs[0]).all()):
        raise ValueError("Nonfinite model logits")
    loss = masked_wbce(outputs[0], targets, valid_channels)
    if not bool(torch.isfinite(loss)):
        raise ValueError("Nonfinite training loss")
    loss.backward()
    gradients = [p.grad for p in model.parameters() if p.grad is not None]
    if not gradients or not bool(torch.stack([torch.isfinite(g).all() for g in gradients]).all()):
        raise ValueError("Missing or nonfinite model gradients")
    optimizer.step()
    if not bool(torch.stack([torch.isfinite(p).all() for p in model.parameters()]).all()):
        raise ValueError("Nonfinite updated model parameters")
    return float(loss.detach()), len(gradients)


def sample_schedule(triplets, seed=SEED, sample_count=UPDATES * BATCH_SIZE):
    ids = sorted(t["triplet_id"] for t in triplets)
    if not ids or len(set(ids)) != len(ids) or type(sample_count) is not int or sample_count <= 0:
        raise ValueError("Sampling requires distinct triplet IDs and a positive sample count")
    rng, samples, cycles = random.Random(seed), [], []
    while len(samples) < sample_count:
        cycle = ids.copy()
        rng.shuffle(cycle)
        take = min(len(cycle), sample_count - len(samples))
        cycles.append({"shuffled_ids": cycle, "consumed_ids": cycle[:take]})
        samples.extend(cycle[:take])
    return {"seed": seed, "algorithm": "Python random.Random.shuffle concatenated cycles",
            "triplet_count": len(ids), "sample_count": sample_count, "sampled_ids": samples,
            "cycles": cycles, "batches": [samples[i:i + BATCH_SIZE] for i in range(0, sample_count, BATCH_SIZE)]}


def load_config(root, path):
    config = read_json(path)
    train = config["training"]
    required = {"updates": 200, "batch_size": 2, "seed": 1234, "optimizer": "Adam", "learning_rate": .0001,
        "betas": [.9, .999], "epsilon": 1e-8, "weight_decay": 0.0, "precision": "float32", "device": "cuda",
        "parameters": "all_trainable", "batch_norm": "affine_trainable_running_buffers_frozen",
        "target_disk_radius": 2.5, "target_center_conversion": "official_affine_then_astype_int32_truncate_toward_zero",
        "loss": "gamma2_weighted_binary_cross_entropy", "sigmoid_clamp": .0001,
        "masked_denominator": "valid_output_channels_times_height_times_width",
        "checkpoint_interval_updates": 25, "augmentation": False, "mining": False,
        "checkpoint_selection": "final_update200_only"}
    if config["schema_version"] != "wasb_adaptation_experiment/v0.1" or any(train.get(k) != v for k, v in required.items()):
        raise ValueError("Training preset differs from the approved200-update trial")
    repository_path(root, config["output_root"], "data/outputs")
    for key in ("approved_plan", "transfer_config", "original_calibration_config", "split_metadata"):
        bound_path(root, config[key])
    for source in config["upstream_training_sources"]:
        bound_path(root, source)
    return config


def build_training_manifest(root, config):
    """Read only three pilot label bodies; exclusions use bound metadata files."""
    metadata = read_json(bound_path(root, config["split_metadata"]))
    transfer = read_json(bound_path(root, config["transfer_config"]))
    development = metadata["windows"]
    holdouts = metadata["sealed_holdouts"]
    if len(development) != 6 or len(holdouts) != 3 or len(transfer["windows"]) != 6:
        raise ValueError("Development/holdout metadata inventory differs")
    for window in transfer["windows"]:
        matches = [d for d in development if d["window_id"] == window["window_id"]]
        if len(matches) != 1 or any(matches[0][key] != window[key] for key in (
                "possession_id", "source_video", "start_frame_index", "end_frame_index")):
            raise ValueError("Evaluation metadata differs from the split manifest")
    pilots = config["pilots"]
    if len(pilots) != 3 or {p["possession_id"] for p in pilots} != set(PILOT_RANGES):
        raise ValueError("Only the three approved pilot windows may train")
    counts = {"reviewed_frames": 0, "positive_frames": 0, "hidden_frames": 0, "masked_frames": 0,
              "fully_visible_positive": 0, "partially_visible_positive": 0, "triplets": 0,
              "masked_frame_ids": [], "hidden_frame_ids": []}
    labels_by_id, records, triplets = {}, [], []
    for pilot in pilots:
        low, high = PILOT_RANGES[pilot["possession_id"]]
        if (pilot["start_frame_index"], pilot["end_frame_index"]) != (low, high):
            raise ValueError("Pilot frame range changed")
        for excluded in [*development, *holdouts]:
            if (excluded["source_video"]["sha256"] == pilot["source_video"]["sha256"]
                    and max(low, excluded["start_frame_index"]) <= min(high, excluded["end_frame_index"])):
                raise ValueError("Training/context overlaps development or holdout metadata")
        labels = load_annotations(bound_path(root, pilot["annotation"]))
        if (labels.review.status != "reviewed" or labels.window.selection_purpose != "protocol_adjudication"
                or labels.source_video.to_dict() != pilot["source_video"]
                or labels.possession_id != pilot["possession_id"] or labels.annotation_set_id != pilot["window_id"]
                or (labels.window.start_frame_index, labels.window.end_frame_index) != (low, high)):
            raise ValueError("Pilot annotation identity/review/source differs")
        labels_by_id[pilot["window_id"]] = labels
        frame_records = []
        for annotation in labels.annotations:
            kind = annotation_kind(annotation)
            counts["reviewed_frames"] += 1
            counts[f"{kind}_frames"] += 1
            if kind == "positive":
                counts[f"{annotation.visibility}_positive"] += 1
            else:
                counts[f"{kind}_frame_ids"].append({"possession_id": labels.possession_id, "frame_index": annotation.frame_index})
            _, valid, target = annotation_target(annotation, labels.source_video.width_px, labels.source_video.height_px)
            frame_records.append({"frame_index": annotation.frame_index, "valid_output_channel": valid, **target})
        records.append({"window_id": pilot["window_id"], "annotation": pilot["annotation"], "frames": frame_records})
        for first in range(low, high - 1):
            triplets.append({"triplet_id": f"{pilot['window_id']}/frame_{first:06d}",
                             "window_id": pilot["window_id"], "frame_indices": [first, first + 1, first + 2]})
    counts["triplets"] = len(triplets)
    if counts != config["expected_split"]:
        raise ValueError(f"Pilot label accounting differs: {counts}")
    manifest = {"schema_version": "wasb_pilot_training_manifest/v0.1", "counts": counts,
                "pilot_windows": records, "triplets": triplets,
                "exclusion_metadata": config["split_metadata"], "evaluation_metadata": config["transfer_config"],
                "evaluation_label_bodies_read": False, "holdout_label_bodies_read": False,
                "outside_pilot_temporal_context": False}
    return manifest, labels_by_id


def prepare_examples(root, config, manifest, labels_by_id):
    examples, source_checks = {}, []
    for pilot in config["pilots"]:
        labels = labels_by_id[pilot["window_id"]]
        source_checks.append(verify_source_video_contract(labels.source_video, root))
        path = repository_path(root, labels.source_video.path.as_posix(), "data/clips")
        capture = cv2.VideoCapture(str(path))
        frames = {}
        try:
            if not capture.isOpened() or not capture.set(cv2.CAP_PROP_POS_FRAMES, pilot["start_frame_index"]):
                raise ValueError("Cannot seek the approved pilot window")
            for frame_index in range(pilot["start_frame_index"], pilot["end_frame_index"] + 1):
                ok, bgr = capture.read()
                if (not ok or bgr.shape != (labels.source_video.height_px, labels.source_video.width_px, 3)
                        or round(capture.get(cv2.CAP_PROP_POS_FRAMES)) != frame_index + 1):
                    raise ValueError(f"Pilot decode identity/dimensions failed at{frame_index}")
                frames[frame_index] = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        finally:
            capture.release()
        annotations = labels.annotation_by_frame()
        for triplet in [t for t in manifest["triplets"] if t["window_id"] == pilot["window_id"]]:
            ids = triplet["frame_indices"]
            inputs, _ = preprocess_triplet([frames[i] for i in ids])
            targets = [annotation_target(annotations[i], labels.source_video.width_px, labels.source_video.height_px) for i in ids]
            examples[triplet["triplet_id"]] = (inputs[0], torch.from_numpy(np.stack([t[0] for t in targets])),
                                               torch.tensor([t[1] for t in targets], dtype=torch.bool))
    return examples, source_checks


def seed_runtime(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def rng_state():
    numpy = np.random.get_state()
    return {"python": random.getstate(), "numpy": {
        "algorithm": numpy[0], "keys": torch.tensor(numpy[1].astype(np.int64)), "position": numpy[2],
        "has_gauss": numpy[3], "cached_gaussian": numpy[4]}, "torch_cpu": torch.get_rng_state(),
        "torch_cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else []}


def restore_rng(state):
    random.setstate(state["python"])
    numpy = state["numpy"]
    np.random.set_state((numpy["algorithm"], numpy["keys"].numpy().astype(np.uint32),
                         numpy["position"], numpy["has_gauss"], numpy["cached_gaussian"]))
    torch.set_rng_state(state["torch_cpu"])
    if state["torch_cuda"]:
        torch.cuda.set_rng_state_all(state["torch_cuda"])


def cpu_tree(value):
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {key: cpu_tree(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return type(value)(cpu_tree(item) for item in value)
    return value


def validate_finite_tensors(value):
    if isinstance(value, torch.Tensor):
        if not bool(torch.isfinite(value).all()):
            raise ValueError("Checkpoint contains nonfinite tensors")
    elif isinstance(value, dict):
        for item in value.values():
            validate_finite_tensors(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            validate_finite_tensors(item)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Checkpoint contains nonfinite scalar")


def save_checkpoint_once(path, payload):
    """Atomic new file; never replace a previous checkpoint or use unsafe pickle loading."""
    if path.exists():
        raise FileExistsError(f"Checkpoint already exists:{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    state = cpu_tree(payload)
    validate_finite_tensors(state)
    with temporary.open("xb") as stream:
        torch.save(state, stream)
        stream.flush()
        os.fsync(stream.fileno())
    torch.load(temporary, map_location="cpu", weights_only=True)
    # Single trainer owns this output; a second process is excluded by the run lock.
    if path.exists():
        raise FileExistsError(path)
    temporary.rename(path)
    return path


def load_training_state(path, identity, schedule):
    state = torch.load(path, map_location="cpu", weights_only=True)
    if (not isinstance(state, dict) or state.get("schema_version") != "wasb_training_state/v0.1"
            or state.get("identity") != identity or state.get("schedule") != schedule):
        raise ValueError("Saved training state identity/schedule differs")
    completed = state["completed_updates"]
    if type(completed) is not int or not 0 <= completed <= UPDATES or len(state["losses"]) != completed:
        raise ValueError("Saved training progress is invalid")
    if path.name.startswith("update_") and path.name != f"update_{completed:06d}.pth":
        raise ValueError("Saved checkpoint filename and completed progress differ")
    if any(row["update"] != i + 1 or row["triplet_ids"] != schedule["batches"][i]
           for i, row in enumerate(state["losses"])):
        raise ValueError("Saved losses do not follow the frozen sampling schedule")
    model_state, bn_reference = state["model_state_dict"], state["batch_norm_reference"]
    if (not isinstance(model_state, dict) or not model_state
            or any(not isinstance(name, str) or not isinstance(tensor, torch.Tensor) for name, tensor in model_state.items())):
        raise ValueError("Saved model state must contain named tensors only")
    bn_names = {name for name in model_state if name.endswith(("running_mean", "running_var", "num_batches_tracked"))}
    if (set(bn_reference) != bn_names
            or any(not torch.equal(model_state[name], bn_reference[name]) for name in bn_names)):
        raise ValueError("Saved BatchNorm buffers differ from frozen reference")
    validate_finite_tensors(state)
    return state


def _training_state(model, optimizer, identity, schedule, completed, losses, bn_reference, resources):
    return {"schema_version": "wasb_training_state/v0.1", "identity": identity,
        "completed_updates": completed, "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(), "rng_state": rng_state(),
        "schedule": schedule, "losses": losses, "batch_norm_reference": bn_reference, "resources": resources}


def publish_final(root, output, config_binding, state_path, state, attempts):
    if state["completed_updates"] != UPDATES:
        raise ValueError("Only final update200 may be published")
    checkpoint = output / "checkpoint.pth"
    payload = {"model_state_dict": state["model_state_dict"]}
    if checkpoint.exists():
        saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
        if (set(saved) != {"model_state_dict"} or set(saved["model_state_dict"]) != set(payload["model_state_dict"])
                or any(not torch.equal(saved["model_state_dict"][key], value.cpu())
                       for key, value in payload["model_state_dict"].items())):
            raise ValueError("Existing final weights differ from preserved update200 state")
    else:
        save_checkpoint_once(checkpoint, payload)
    write_once(output / "losses.json", state["losses"])
    losses = [row["loss"] for row in state["losses"]]
    attempt_times = {}
    for item in attempts:
        record = read_json(root / item["path"])
        attempt_times[record["attempt_id"]] = max(attempt_times.get(record["attempt_id"], 0), record.get("elapsed_seconds", 0))
    completion = {"schema_version": "wasb_adaptation_training_completion/v0.1", "status": "completed",
        "completed_updates": UPDATES, "config": config_binding, "checkpoint": binding(root, checkpoint),
        "training_provenance": state["identity"], "training_state": binding(root, state_path),
        "training_manifest": binding(root, output / "training_manifest.json"),
        "sampling_schedule": binding(root, output / "sampling_schedule.json"),
        "losses": binding(root, output / "losses.json"),
        "loss_summary": {"first": losses[0], "last": losses[-1], "minimum": min(losses),
                         "maximum": max(losses), "mean": sum(losses) / len(losses)},
        "resources": state["resources"], "attempt_records": attempts,
        "attempt_elapsed_seconds_total": sum(attempt_times.values()),
        "batch_norm_running_buffers_unchanged": True, "all_parameters_trainable": True,
        "checkpoint_selection": "final_update200_only", "evaluation_used_for_training_or_selection": False,
        "quality_gate": None, "selected_operating_point": None}
    write_once(output / "completion.json", completion)
    return completion


@contextmanager
def training_lock(path):
    """OS-owned lock releases on process exit, including a crash; no stale PID gate."""
    with path.open("a+b") as stream:
        if path.stat().st_size == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def execute(root, config_path, *, resume=False):
    config = load_config(root, config_path)
    output = repository_path(root, config["output_root"], "data/outputs") / "training"
    output.mkdir(parents=True, exist_ok=True)
    with training_lock(output / "training.lock"):
        return _execute_locked(root, config_path, config, output, resume)


def _execute_locked(root, config_path, config, output, resume):
    config_binding = binding(root, config_path)
    if (output / "completion.json").exists():
        completion = read_json(output / "completion.json")
        if completion["config"] != config_binding or completion["completed_updates"] != UPDATES:
            raise ValueError("Existing completed training belongs to a different trial")
        bound_path(root, completion["checkpoint"])
        return completion  # Delivery retries do not load a model or retrain.
    attempt_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + uuid.uuid4().hex
    attempts_folder = output / "attempts"
    attempts_folder.mkdir(exist_ok=True)
    attempt_path = attempts_folder / (attempt_id + ".json")
    started, completed, latest_state = time.perf_counter(), 0, None
    attempt = {"attempt_id": attempt_id, "config": config_binding, "resume_requested": resume,
               "status": "started", "started_at_utc": datetime.now(timezone.utc).isoformat()}
    write_once(attempts_folder / (attempt_id + ".started.json"), attempt)
    try:
        manifest, labels_by_id = build_training_manifest(root, config)
        schedule = sample_schedule(manifest["triplets"])
        write_once(output / "experiment.json", config)
        write_once(output / "training_manifest.json", manifest)
        write_once(output / "sampling_schedule.json", schedule)
        source_files = [Path(__file__), Path(__file__).with_name("wasb_adapter.py"),
                        Path(__file__).with_name("annotations.py")]
        identity = {"config": config_binding, "manifest_sha256": canonical(manifest), "schedule_sha256": canonical(schedule),
                    "pretrained_checkpoint": config["pretrained_checkpoint"], "upstream_commit": config["upstream_commit"],
                    "source_bindings": [binding(ROOT, path) for path in source_files],
                    "python": sys.version, "torch": str(torch.__version__), "numpy": np.__version__, "opencv": cv2.__version__}
        states = sorted((output / "states").glob("update_*.pth")) if (output / "states").exists() else []
        if states and not resume:
            raise ValueError("Existing training progress requires explicit --resume; it will not restart")
        if not states and list(attempts_folder.glob("*.json")) != [attempts_folder / (attempt_id + ".started.json")] and not resume:
            raise ValueError("A previous attempt exists; inspect it and use --resume explicitly")
        identity_path = output / "training_identity.json"
        saved_identity = read_json(identity_path) if identity_path.exists() else identity
        final_state_present = bool(states and states[-1].name == f"update_{UPDATES:06d}.pth")
        if saved_identity != identity and not final_state_present:
            raise ValueError("Resume source/config/runtime identity changed before completion")
        if final_state_present and any(saved_identity.get(key) != identity[key] for key in
                                       ("config", "manifest_sha256", "schedule_sha256", "pretrained_checkpoint", "upstream_commit")):
            raise ValueError("Final-state publication cannot change the training experiment")
        if not identity_path.exists():
            write_once(identity_path, identity)
        prior = load_training_state(states[-1], saved_identity, schedule) if states else None
        if prior:
            completed, latest_state = prior["completed_updates"], states[-1]
            attempt.update(restored_update=completed, restored_checkpoint=binding(root, latest_state))
        prior_logs = [json.loads(line) for path in attempts_folder.glob("*.losses.jsonl")
                      for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        attempt.update(prior_logged_optimizer_updates=len(prior_logs),
            restored_update=completed,
            prior_successful_updates_beyond_restored_state=sum(row["update"] > completed for row in prior_logs),
            continuation="Exact frozen schedule from restored state; prior failed/discarded work remains in attempt logs")
        if prior and completed == UPDATES:
            attempt.update(status="completed_existing_update200_publication", elapsed_seconds=time.perf_counter() - started,
                           completed_updates=completed, publication_source_bindings=identity["source_bindings"])
            write_once(attempt_path, attempt)
            history = [binding(root, p) for p in sorted(attempts_folder.glob("*.json")) if not p.name.endswith(".started.json")]
            return publish_final(root, output, config_binding, latest_state, prior, history)
        if not torch.cuda.is_available():
            raise ValueError("The approved training device is CUDA")
        seed_runtime(SEED)
        disk_before = shutil.disk_usage(output).free
        bound_path(root, config["pretrained_checkpoint"])
        adapter = WasbAdapter(repository_path(root, config["upstream_source"]),
                              root / config["pretrained_checkpoint"]["path"], device="cuda")
        model, device = adapter.model, adapter.device
        bn_reference = freeze_batch_norm(model)
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-4, betas=(.9, .999), eps=1e-8, weight_decay=0)
        losses = []
        if prior:
            model.load_state_dict(prior["model_state_dict"], strict=True)
            optimizer.load_state_dict(prior["optimizer_state_dict"])
            bn_reference = {name: tensor.to(device) for name, tensor in prior["batch_norm_reference"].items()}
            losses = prior["losses"]
            restore_rng(prior["rng_state"])
        assert_batch_norm_unchanged(model, bn_reference)
        examples, source_checks = prepare_examples(root, config, manifest, labels_by_id)
        write_once(output / "source_video_checks.json", source_checks)
        tensor_bytes = sum(t.numel() * t.element_size() for example in examples.values() for t in example)
        torch.cuda.reset_peak_memory_stats(device)
        resources = {"device": str(device), "device_name": torch.cuda.get_device_name(device),
            "parameter_count": sum(p.numel() for p in model.parameters()), "preprocessed_cpu_tensor_bytes": tensor_bytes,
            "disk_free_bytes_before_attempt": disk_before, "cudnn_benchmark": False, "cudnn_deterministic": True,
            "bitwise_reproducibility_across_hardware_claimed": False}
        with (attempts_folder / (attempt_id + ".losses.jsonl")).open("x", encoding="utf-8") as log:
            for update in range(completed + 1, UPDATES + 1):
                ids = schedule["batches"][update - 1]
                inputs, targets, masks = [torch.stack([examples[i][j] for i in ids]).to(device) for j in range(3)]
                began = time.perf_counter()
                loss, gradient_parameter_count = training_step(model, optimizer, inputs, targets, masks)
                completed = update
                row = {"update": update, "triplet_ids": ids, "loss": loss, "valid_channels": int(masks.sum()),
                       "gradient_parameter_count": gradient_parameter_count, "elapsed_seconds": time.perf_counter() - began,
                       "attempt_id": attempt_id}
                losses.append(row)
                log.write(json.dumps(row, allow_nan=False) + "\n")
                log.flush()
                if update % config["training"]["checkpoint_interval_updates"] == 0 or update == UPDATES:
                    assert_batch_norm_unchanged(model, bn_reference)
                    resources.update(cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated(device),
                        cuda_peak_reserved_bytes=torch.cuda.max_memory_reserved(device),
                        elapsed_seconds_this_attempt=time.perf_counter() - started,
                        disk_free_bytes_at_checkpoint=shutil.disk_usage(output).free)
                    state = _training_state(model, optimizer, identity, schedule, completed, losses, bn_reference, resources)
                    latest_state = save_checkpoint_once(output / "states" / f"update_{update:06d}.pth", state)
                    print(f"Completed training update{update}/{UPDATES}; loss={loss:.8f}", flush=True)
        state = load_training_state(latest_state, identity, schedule)
        attempt.update(status="completed_training", completed_updates=completed,
                       elapsed_seconds=time.perf_counter() - started, training_state=binding(root, latest_state))
        write_once(attempt_path, attempt)
        history = [binding(root, p) for p in sorted(attempts_folder.glob("*.json")) if not p.name.endswith(".started.json")]
        return publish_final(root, output, config_binding, latest_state, state, history)
    except BaseException as error:
        failure = {**attempt, "status": "failed", "completed_updates_in_memory": completed,
                   "last_saved_state": None if latest_state is None else binding(root, latest_state),
                   "elapsed_seconds": time.perf_counter() - started,
                   "failure": f"{type(error).__name__}: {error}", "traceback": traceback.format_exc()}
        # Publication failure after a completed training receipt is separate evidence.
        destination = attempt_path if not attempt_path.exists() else attempts_folder / (attempt_id + ".publication_failure.json")
        write_once(destination, failure)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--resume", action="store_true", help="Continue a preserved checkpoint after reviewing prior attempts")
    args = parser.parse_args()
    result = execute(ROOT, repository_path(ROOT, args.config), resume=args.resume)
    print(json.dumps({"status": result["status"], "completed_updates": result["completed_updates"],
                      "checkpoint": result["checkpoint"]}))


if __name__ == "__main__":
    main()
