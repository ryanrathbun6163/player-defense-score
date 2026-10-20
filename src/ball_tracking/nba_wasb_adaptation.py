"""One approved SAC/NFHS continuation fit, with native inputs and preserved history."""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import shutil
import sys
import time
import traceback
import uuid

import cv2
import numpy as np
from PIL import Image
import torch

from . import nba_annotations as nba
from . import wasb_training as training
from .annotations import FrameAnnotation
from .prepare_nba_assisted_review import read_json as parse_json, require
from .wasb_adapted_adapter import AdaptedWasbAdapter
from .wasb_adapter import preprocess_triplet
from .wasb_experiment import bound_path, canonical, digest_file, repository_path, write_once

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "nba_wasb_adaptation/v0.1"
INITIAL_SHA = "09da1214e94fc2eb8f36dbf46089eb117d9bbde4d5cb85d3a1d127c3fb61de98"
SAC_GAME = "0022500829"
EXCLUDED_GAMES = {"0022500828", "0022500843"}
RECIPE = {
    "updates": 200, "batch_size": 2, "seed": 1234, "optimizer": "Adam", "learning_rate": .0001,
    "betas": [.9, .999], "epsilon": 1e-8, "weight_decay": 0.0, "precision": "float32", "device": "cuda",
    "parameters": "all_trainable", "batch_norm": "affine_trainable_running_buffers_frozen",
    "target_disk_radius": 2.5, "target_center_conversion": "official_affine_then_astype_int32_truncate_toward_zero",
    "loss": "gamma2_weighted_binary_cross_entropy", "sigmoid_clamp": .0001,
    "masked_denominator": "valid_output_channels_times_height_times_width",
    "checkpoint_interval_updates": 25, "augmentation": False, "mining": False,
    "checkpoint_selection": "final_update200_only", "sampling": "shuffle_all_usable_triplets_seed1234_take400",
    "initialization": "expanded_checkpoint_fresh_adam", "exclude_all_masked_triplets": True,
}


def read_json(path):
    return parse_json(Path(path).read_bytes())


def binding(root, path):
    path = Path(path).resolve()
    require(path.is_relative_to(Path(root).resolve()), "Binding escapes repository")
    return {"path": path.relative_to(Path(root).resolve()).as_posix(),
            "sha256": digest_file(path), "bytes": path.stat().st_size}


def bound(root, value):
    path = bound_path(root, value)
    require("bytes" not in value or value["bytes"] == path.stat().st_size, "Bound file size differs")
    return path


def same_binding(a, b):
    return all(a.get(key) == b.get(key) for key in ("path", "sha256"))


def load_config(root, path):
    config = read_json(path)
    require(config.get("schema_version") == SCHEMA, "Unsupported NBA adaptation config")
    require(config.get("training") == RECIPE, "Training recipe differs from approved continuation")
    require(set(config.get("excluded_nba_game_ids", [])) == EXCLUDED_GAMES, "DET/TOR exclusions differ")
    repository_path(root, config["output_root"], "data/outputs")
    approval = read_json(bound(root, config["approval"]))
    require(approval.get("schema_version") == "nba_wasb_adaptation_approval/v0.1"
            and approval.get("status") == "approved" and approval.get("reviewer_id") == "Ryan"
            and isinstance(approval.get("user_statement"), str) and bool(approval["user_statement"].strip()),
            "New NBA training requires explicit Ryan approval")
    require(approval.get("experiment_contract") == {k: v for k, v in config.items() if k != "approval"},
            "Approved experiment contract differs")
    initialization = config["initialization"]
    require(initialization["checkpoint"]["sha256"] == INITIAL_SHA, "Continuation must start from frozen expanded checkpoint")
    prior = read_json(bound(root, initialization["training_completion"]))
    require(prior.get("status") == "completed" and prior.get("completed_updates") == 200
            and same_binding(prior["checkpoint"], initialization["checkpoint"])
            and same_binding(prior["config"], config["nfhs_training_config"]),
            "Initialization checkpoint/completed NFHS lineage differs")
    windows = config["nba_training_windows"]
    require(isinstance(windows, list) and windows and len({w["window_id"] for w in windows}) == len(windows),
            "NBA training window IDs must be distinct")
    require(all(w["game_id"] == SAC_GAME and w["candidate_id"] == "sac_mem_q1_c01"
                and w["reference_kind"] in {"pilot", "hard_example"} for w in windows),
            "Only approved SAC references may enter fitting")
    return config


def native_block(reference, specification):
    """Compose one accepted native block without crossing an unlabeled gap."""
    require(reference["game_id"] == specification["game_id"] == SAC_GAME
            and reference["candidate_id"] == specification["candidate_id"]
            and reference["approved_role"] == "future_training_candidate_pool",
            "Excluded game or wrong training role")
    require(reference["human_review"]["status"] == "accepted"
            and reference["human_review"]["independent_human_annotation"] is False
            and reference["origin"]["kind"] == "assistant_visual_proposal", "Accepted AI origin is required")
    frames, rows = reference["frames"], reference["annotations"]
    indices = [f["source_frame_index"] for f in frames]
    ticks = [f["source_pts_ticks"] for f in frames]
    require(len(frames) == len(rows) and len(frames) >= 3
            and indices == list(range(indices[0], indices[-1] + 1))
            and [indices[0], indices[-1]] == specification["source_frame_range_inclusive"]
            and all(b - a in {1440, 1530} for a, b in zip(ticks, ticks[1:]))
            and reference["time_base"] == "1/90000",
            "Native training window inventory/timing differs")
    source = reference["source_video"]
    bounds = type("PixelBounds", (), {key: source[key] for key in ("width_px", "height_px")})()
    labels = [FrameAnnotation.from_mapping(row, offset, bounds) for offset, row in enumerate(rows)]
    require([a.frame_index for a in labels] == indices and all(a.annotation_status == "labeled" for a in labels),
            "Native training annotations are incomplete or misaligned")
    kinds = [training.annotation_kind(a) for a in labels]
    records = [{"frame_index": frame["source_frame_index"], "source_pts_ticks": frame["source_pts_ticks"],
                "png": frame["png"], "kind": kind, "valid_output_channel": kind != "masked"}
               for frame, kind in zip(frames, kinds)]
    block = {"domain": "nba", "window_id": specification["window_id"], "game_id": reference["game_id"],
             "candidate_id": reference["candidate_id"], "source_video": source, "time_base": reference["time_base"],
             "source_frame_range_inclusive": specification["source_frame_range_inclusive"], "frames": records,
             "annotation_origin": reference["origin"], "human_review": reference["human_review"],
             "reference_bindings": reference["bindings"]}
    return block, {a.frame_index: a for a in labels}


def _selected_reference(root, document, specification):
    require(document.get("schema_version") == "nba_reviewed_reference/v0.1"
            and document.get("status") == "human_accepted_assisted_reference", "NBA reference is not accepted")
    matches = [r for r in document["references"] if r["candidate_id"] == specification["candidate_id"]
               and (specification["reference_kind"] == "pilot" or r.get("window_id") == specification["window_id"])]
    require(len(matches) == 1, "Expected exactly one accepted training reference")
    reference = matches[0]
    original = read_json(bound(root, reference["bindings"]["original_annotations"]))
    nba.validate_annotations(original)
    nba.verify_annotation_assets(original, root, verify_images=False)
    proposal = read_json(bound(root, reference["bindings"]["proposal"]))
    acceptance = read_json(bound(root, reference["bindings"]["acceptance"]))
    require(same_binding(document["acceptance"], reference["bindings"]["acceptance"])
            and acceptance["status"] == "accepted" and acceptance["reviewer_id"] == "Ryan",
            "Reference acceptance lineage differs")
    for key in ("status", "reviewer_id", "reviewed_at_utc", "review_method", "user_statement", "scope"):
        require(reference["human_review"][key] == acceptance[key], "Reference human acceptance differs")
    require(reference["frames"] == original["frames"] and reference["annotations"] == proposal["annotations"]
            and reference["origin"] == proposal["origin"], "Published native reference differs from unchanged reviewed proposal")
    for key in ("candidate_id", "game_id", "approved_role", "source_video", "time_base"):
        require(reference[key] == original[key], f"Native reference {key} differs from source authority")
    return reference


def compose_triplets(blocks):
    triplets, excluded, counts, seen = [], [], Counter(), set()
    for block in blocks:
        frames = block["frames"]
        for frame in frames:
            key = (block["source_video"]["sha256"], frame["frame_index"])
            require(key not in seen, "Training blocks duplicate or overlap source frames")
            seen.add(key)
            counts[frame["kind"] + "_frames"] += 1
            counts[block["domain"] + "_frames"] += 1
        indices = [f["frame_index"] for f in frames]
        require(indices == list(range(indices[0], indices[-1] + 1)), "Training block has a context gap")
        for offset in range(len(frames) - 2):
            selected = frames[offset:offset + 3]
            row = {"triplet_id": f"{block['window_id']}/frame_{selected[0]['frame_index']:06d}",
                   "window_id": block["window_id"], "domain": block["domain"],
                   "frame_indices": [f["frame_index"] for f in selected],
                   "valid_output_channels": [f["valid_output_channel"] for f in selected]}
            (triplets if any(row["valid_output_channels"]) else excluded).append(row)
    require(len({row["triplet_id"] for row in triplets + excluded}) == len(triplets) + len(excluded),
            "Duplicate training triplet IDs")
    counts = {**{key: counts[key] for key in ("positive_frames", "hidden_frames", "masked_frames", "nba_frames", "nfhs_frames")},
              "reviewed_frames": len(seen), "all_triplets": len(triplets) + len(excluded),
              "excluded_all_masked_triplets": len(excluded), "usable_triplets": len(triplets)}
    return triplets, excluded, counts


def exposure_report(blocks, triplets, schedule):
    lookup = {t["triplet_id"]: t for t in triplets}
    frequency = Counter(schedule["sampled_ids"])
    require(set(frequency) <= set(lookup), "Schedule includes unapproved or fully masked context")
    inputs, supervised, by_domain = Counter(), Counter(), Counter()
    samples = []
    for position, identity in enumerate(schedule["sampled_ids"]):
        triplet = lookup[identity]
        by_domain[triplet["domain"]] += 1
        for index, valid in zip(triplet["frame_indices"], triplet["valid_output_channels"]):
            inputs[triplet["window_id"], index] += 1
            supervised[triplet["window_id"], index] += int(valid)
        samples.append({"sample_index": position, "update": position // 2 + 1, "batch_slot": position % 2,
                        **triplet})
    return {"samples": samples, "sample_count": len(samples), "samples_by_domain": dict(by_domain),
            "unique_sampled_triplets": len(frequency), "unused_usable_triplets": sorted(set(lookup) - set(frequency)),
            "triplet_exposure": [{"triplet_id": t["triplet_id"], "count": frequency[t["triplet_id"]]} for t in triplets],
            "frame_exposure": [{"domain": block["domain"], "window_id": block["window_id"],
                                "frame_index": frame["frame_index"], "kind": frame["kind"],
                                "input_count": inputs[block["window_id"], frame["frame_index"]],
                                "supervised_output_count": supervised[block["window_id"], frame["frame_index"]]}
                               for block in blocks for frame in block["frames"]]}


def _prepare(root, config_path):
    config = load_config(root, config_path)
    nfhs_path = bound(root, config["nfhs_training_config"])
    nfhs_config = training.load_config(root, nfhs_path)
    nfhs_manifest, nfhs_labels = training.build_training_manifest(root, nfhs_config)
    require(nfhs_manifest["counts"]["reviewed_frames"] == 150, "Expected the existing 150 NFHS training frames")
    blocks, labels = [], {}
    for old, source in zip(nfhs_manifest["training_blocks"], nfhs_config["training_blocks"]):
        block = {"domain": "nfhs", "window_id": old["window_id"], "possession_id": source["possession_id"],
                 "source_video": source["source_video"], "frames": old["frames"],
                 "annotation_segments": old["annotation_segments"], "cadence": "source_25fps_unchanged"}
        blocks.append(block)
        labels[block["window_id"]] = nfhs_labels[block["window_id"]].annotation_by_frame()
    documents = {key: read_json(bound(root, value)) for key, value in config["nba_references"].items()}
    native_references = {}
    for specification in config["nba_training_windows"]:
        reference = _selected_reference(root, documents[specification["reference_kind"]], specification)
        block, frame_labels = native_block(reference, specification)
        require(block["window_id"] not in labels, "NBA/NFHS window IDs collide")
        blocks.append(block)
        labels[block["window_id"]] = frame_labels
        native_references[block["window_id"]] = reference
    triplets, excluded, counts = compose_triplets(blocks)
    require(counts == config["expected_split"], f"Approved mixed training counts differ: {counts}")
    schedule = training.sample_schedule(triplets)
    manifest = {"schema_version": "nba_wasb_training_manifest/v0.1", "counts": counts, "training_blocks": blocks,
                "triplets": triplets, "excluded_all_masked_triplets": excluded,
                "nfhs_manifest": nfhs_manifest, "nfhs_training_config": config["nfhs_training_config"],
                "nba_reference_bindings": config["nba_references"],
                "excluded_nba_game_ids": config["excluded_nba_game_ids"],
                "nba_mixed_reference_containers_parsed": True, "excluded_nba_annotation_rows_used": 0,
                "nfhs_evaluation_label_bodies_read": False, "holdout_label_bodies_read": False,
                "nba_source_video_reads_or_decodes": 0, "outside_training_block_context": False,
                "native_cadence_preserved": True, "human_accepted_ai_authorship_preserved": True}
    exposure = exposure_report(blocks, triplets, schedule)
    return config, manifest, schedule, exposure, nfhs_config, nfhs_labels, native_references, labels


def prepare(root, config_path):
    """Read approved metadata/labels only; no weights, image decode or output write."""
    root = Path(root).resolve()
    path = (root / config_path).resolve()
    config, manifest, schedule, exposure, *_ = _prepare(root, path)
    return {"schema_version": "nba_wasb_adaptation_preflight/v0.1", "status": "ready",
            "config": binding(root, path), "manifest": manifest, "schedule": schedule, "exposure": exposure,
            "work": {"model_loads": 0, "optimizer_updates": 0, "image_decodes": 0, "video_decodes": 0}}


def prepare_examples(root, manifest, nfhs_config, nfhs_labels, native_references, labels):
    examples, source_checks = training.prepare_examples(root, nfhs_config, manifest["nfhs_manifest"], nfhs_labels)
    for window_id, reference in native_references.items():
        frames = {}
        for frame in reference["frames"]:
            raw = nba.read_verified_png(frame, reference["source_video"], root)
            with Image.open(io.BytesIO(raw)) as image:
                frames[frame["source_frame_index"]] = np.asarray(image.convert("RGB")).copy()
        source = reference["source_video"]
        for triplet in [t for t in manifest["triplets"] if t["window_id"] == window_id]:
            ids = triplet["frame_indices"]
            inputs, _ = preprocess_triplet([frames[i] for i in ids])
            targets = [training.annotation_target(labels[window_id][i], source["width_px"], source["height_px"]) for i in ids]
            examples[triplet["triplet_id"]] = (inputs[0], torch.from_numpy(np.stack([t[0] for t in targets])),
                                               torch.tensor([t[1] for t in targets], dtype=torch.bool))
        source_checks.append({"window_id": window_id, "domain": "nba", "native_pngs_verified": len(frames),
                              "source_video_reads": 0, "source_video_decodes": 0,
                              "source_verification": reference["bindings"]["source_verification"]})
    require(set(examples) == {t["triplet_id"] for t in manifest["triplets"]}, "Prepared sample inventory differs")
    return examples, source_checks


def initialize(root, config, nfhs_config):
    require(torch.cuda.is_available(), "Approved real training device is CUDA")
    training.seed_runtime(training.SEED)
    parent = read_json(bound(root, config["initialization"]["training_completion"]))
    adapter = AdaptedWasbAdapter(repository_path(root, nfhs_config["upstream_source"]),
                                 bound(root, nfhs_config["pretrained_checkpoint"]),
                                 bound(root, config["initialization"]["checkpoint"]), INITIAL_SHA,
                                 parent["training_provenance"], device="cuda")
    model, device = adapter.model, adapter.device
    reference = training.freeze_batch_norm(model)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4, betas=(.9, .999), eps=1e-8, weight_decay=0)
    require(not optimizer.state, "Continuation optimizer must start fresh")
    return model, device, optimizer, reference


def publish_final(root, output, config_binding, state_path, state, attempts):
    require(state["completed_updates"] == 200, "Only final update200 may be published")
    checkpoint = output / "checkpoint.pth"
    payload = {"model_state_dict": state["model_state_dict"]}
    if checkpoint.exists():
        saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
        require(set(saved) == {"model_state_dict"} and set(saved["model_state_dict"]) == set(payload["model_state_dict"])
                and all(torch.equal(saved["model_state_dict"][key], value.cpu()) for key, value in payload["model_state_dict"].items()),
                "Existing final weights differ from preserved update200")
    else:
        training.save_checkpoint_once(checkpoint, payload)
    write_once(output / "losses.json", state["losses"])
    losses = [row["loss"] for row in state["losses"]]
    completion = {"schema_version": "wasb_adaptation_training_completion/v0.1", "status": "completed",
                  "completed_updates": 200, "config": config_binding, "checkpoint": binding(root, checkpoint),
                  "training_provenance": state["identity"], "training_state": binding(root, state_path),
                  "training_manifest": binding(root, output / "training_manifest.json"),
                  "sampling_schedule": binding(root, output / "sampling_schedule.json"),
                  "sample_exposure": binding(root, output / "sample_exposure.json"),
                  "losses": binding(root, output / "losses.json"),
                  "loss_summary": {"first": losses[0], "last": losses[-1], "minimum": min(losses),
                                   "maximum": max(losses), "mean": sum(losses) / len(losses)},
                  "resources": state["resources"], "attempt_records": attempts,
                  "batch_norm_running_buffers_unchanged": True, "all_parameters_trainable": True,
                  "initial_optimizer": "fresh_Adam_no_parent_optimizer_state", "checkpoint_selection": "final_update200_only",
                  "evaluation_used_for_training_or_selection": False, "quality_gate": None, "selected_operating_point": None}
    write_once(output / "completion.json", completion)
    return completion


def run(root, config_path, *, resume=False):
    root = Path(root).resolve()
    path = (root / config_path).resolve()
    config = load_config(root, path)
    output = repository_path(root, config["output_root"], "data/outputs") / "training"
    output.mkdir(parents=True, exist_ok=True)
    with training.training_lock(output / "training.lock"):
        return _run_locked(root, path, config, output, resume)


def _run_locked(root, path, config, output, resume):
    config_binding = binding(root, path)
    if (output / "completion.json").exists():
        completed_result = read_json(output / "completion.json")
        require(completed_result["config"] == config_binding and completed_result["completed_updates"] == 200,
                "Completed fit belongs to another experiment")
        bound(root, completed_result["checkpoint"])
        return completed_result
    attempt_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + uuid.uuid4().hex
    attempts_folder = output / "attempts"
    attempts_folder.mkdir(exist_ok=True)
    previous_attempts = list(attempts_folder.glob("*.json"))
    attempt_path = attempts_folder / (attempt_id + ".json")
    attempt = {"attempt_id": attempt_id, "config": config_binding, "resume_requested": resume,
               "status": "started", "started_at_utc": datetime.now(timezone.utc).isoformat()}
    write_once(attempts_folder / (attempt_id + ".started.json"), attempt)
    began, completed, latest_state = time.perf_counter(), 0, None
    try:
        require(not previous_attempts or resume, "Prior attempt preserved; inspect and use --resume, never restart")
        _, manifest, schedule, exposure, nfhs_config, nfhs_labels, native_refs, labels = _prepare(root, path)
        for name, value in (("experiment.json", config), ("training_manifest.json", manifest),
                            ("sampling_schedule.json", schedule), ("sample_exposure.json", exposure)):
            write_once(output / name, value)
        sources = [Path(__file__), *[Path(__file__).with_name(name) for name in
                   ("wasb_training.py", "wasb_adapter.py", "wasb_adapted_adapter.py", "nba_annotations.py",
                    "annotations.py", "wasb_experiment.py", "prepare_nba_assisted_review.py")]]
        identity = {"config": config_binding, "manifest_sha256": canonical(manifest), "schedule_sha256": canonical(schedule),
                    "initialization": config["initialization"], "source_bindings": [binding(ROOT, p) for p in sources],
                    "fresh_optimizer": True, "native_cadence_preserved": True, "excluded_nba_game_ids": sorted(EXCLUDED_GAMES),
                    "python": sys.version, "torch": str(torch.__version__), "numpy": np.__version__, "opencv": cv2.__version__}
        identity_path = output / "training_identity.json"
        saved_identity = read_json(identity_path) if identity_path.exists() else identity
        states = sorted((output / "states").glob("update_*.pth")) if (output / "states").exists() else []
        final_present = bool(states and states[-1].name == "update_000200.pth")
        if final_present:
            require(all(saved_identity.get(k) == identity[k] for k in ("config", "manifest_sha256", "schedule_sha256", "initialization")),
                    "Final-state publication cannot change the experiment")
        else:
            require(saved_identity == identity, "Resume source/config/runtime identity differs")
        write_once(identity_path, saved_identity)
        prior = training.load_training_state(states[-1], saved_identity, schedule) if states else None
        if prior:
            completed, latest_state = prior["completed_updates"], states[-1]
        prior_logs = [json.loads(line) for log in attempts_folder.glob("*.losses.jsonl")
                      for line in log.read_text().splitlines() if line.strip()]
        attempt.update(restored_update=completed, prior_logged_optimizer_updates=len(prior_logs),
                       prior_updates_beyond_restored_state=sum(r["update"] > completed for r in prior_logs))
        if prior and completed == 200:
            attempt.update(status="completed_existing_update200_publication", elapsed_seconds=time.perf_counter() - began,
                           completed_updates=completed, publication_source_bindings=identity["source_bindings"])
            write_once(attempt_path, attempt)
            history = [binding(root, p) for p in sorted(attempts_folder.glob("*.json")) if not p.name.endswith(".started.json")]
            return publish_final(root, output, config_binding, latest_state, prior, history)
        model, device, optimizer, bn_reference = initialize(root, config, nfhs_config)
        losses = []
        if prior:
            model.load_state_dict(prior["model_state_dict"], strict=True)
            optimizer.load_state_dict(prior["optimizer_state_dict"])
            bn_reference = {name: tensor.to(device) for name, tensor in prior["batch_norm_reference"].items()}
            losses = prior["losses"]
            training.restore_rng(prior["rng_state"])
        training.assert_batch_norm_unchanged(model, bn_reference)
        examples, source_checks = prepare_examples(root, manifest, nfhs_config, nfhs_labels, native_refs, labels)
        write_once(output / "source_checks.json", source_checks)
        torch.cuda.reset_peak_memory_stats(device)
        resources = {"device": str(device), "device_name": torch.cuda.get_device_name(device),
                     "parameter_count": sum(p.numel() for p in model.parameters()),
                     "preprocessed_cpu_tensor_bytes": sum(t.numel() * t.element_size() for e in examples.values() for t in e),
                     "disk_free_bytes_before_updates": shutil.disk_usage(output).free,
                     "cudnn_benchmark": False, "cudnn_deterministic": True, "bitwise_reproducibility_across_hardware_claimed": False}
        with (attempts_folder / (attempt_id + ".losses.jsonl")).open("x", encoding="utf-8") as log:
            for update in range(completed + 1, 201):
                ids = schedule["batches"][update - 1]
                inputs, targets, masks = [torch.stack([examples[i][j] for i in ids]).to(device) for j in range(3)]
                started_update = time.perf_counter()
                loss, parameter_count = training.training_step(model, optimizer, inputs, targets, masks)
                completed = update
                row = {"update": update, "triplet_ids": ids, "loss": loss, "valid_channels": int(masks.sum()),
                       "gradient_parameter_count": parameter_count, "elapsed_seconds": time.perf_counter() - started_update,
                       "attempt_id": attempt_id}
                losses.append(row)
                log.write(json.dumps(row, allow_nan=False) + "\n")
                log.flush()
                if update % 25 == 0:
                    training.assert_batch_norm_unchanged(model, bn_reference)
                    resources.update(cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated(device),
                                     cuda_peak_reserved_bytes=torch.cuda.max_memory_reserved(device),
                                     elapsed_seconds_this_attempt=time.perf_counter() - began,
                                     disk_free_bytes_at_checkpoint=shutil.disk_usage(output).free)
                    state = training._training_state(model, optimizer, identity, schedule, update, losses, bn_reference, resources)
                    latest_state = training.save_checkpoint_once(output / "states" / f"update_{update:06d}.pth", state)
                    print(f"Completed NBA continuation update {update}/200; loss={loss:.8f}", flush=True)
        state = training.load_training_state(latest_state, identity, schedule)
        attempt.update(status="completed_training", completed_updates=200, elapsed_seconds=time.perf_counter() - began,
                       training_state=binding(root, latest_state))
        write_once(attempt_path, attempt)
        history = [binding(root, p) for p in sorted(attempts_folder.glob("*.json")) if not p.name.endswith(".started.json")]
        return publish_final(root, output, config_binding, latest_state, state, history)
    except BaseException as error:
        failure = {**attempt, "status": "failed", "completed_updates_in_memory": completed,
                   "last_saved_state": None if latest_state is None else binding(root, latest_state),
                   "elapsed_seconds": time.perf_counter() - began, "failure": f"{type(error).__name__}: {error}",
                   "traceback": traceback.format_exc()}
        destination = attempt_path if not attempt_path.exists() else attempts_folder / (attempt_id + ".publication_failure.json")
        write_once(destination, failure)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--preflight", action="store_true")
    action.add_argument("--run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    require(not args.resume or args.run, "--resume requires --run")
    result = prepare(args.root, args.config) if args.preflight else run(args.root, args.config, resume=args.resume)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
