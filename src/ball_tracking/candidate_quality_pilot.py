"""Bounded candidate-quality pilot. Import/preflight never imports Torch.

Execution requires a separate approval bound to the frozen design and inputs,
and the existing owned GPU supervisor. It produces scores, never a trajectory.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
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
OUTPUT = "data/outputs/ball_tracking/candidate_quality_pilot_v0_1"
CONFIG = "configs/ball_tracking/proposals/candidate_quality_pilot_v0_1.json"
MODULE = "src.ball_tracking.candidate_quality_pilot"
FIT_NAMES = ("leave_chi_out", "leave_den_out", "leave_sac_out", "all_nba")
FIT_GAMES = {
    "leave_chi_out": ("0022400866", "0022500829"),
    "leave_den_out": ("0022400868", "0022500829"),
    "leave_sac_out": ("0022400868", "0022400866"),
    "all_nba": ("0022400868", "0022400866", "0022500829"),
}


def check(value, message):
    if not value:
        raise ValueError(message)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def rows(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def binding(root, path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {"path": path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path),
            "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def bound(root, link):
    path = root / link["path"]
    actual = binding(root, path)
    check(actual["bytes"] == link["bytes"] and actual["sha256"] == link["sha256"],
          "Binding differs: " + link["path"])
    return path


def write_once(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def append(path, value):
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, allow_nan=False) + "\n")
        stream.flush()


def batches(sequence, size):
    check(size > 0, "Positive batch size required")
    for first in range(0, len(sequence), size):
        yield sequence[first:first + size]


def validate_weights(candidates, weights):
    """Check transport independently of the producer's weighting implementation."""
    check(len({r["candidate_id"] for r in weights}) == len(weights) > 0, "Duplicate/empty fit weights")
    result = []
    for item in weights:
        row = candidates[item["candidate_id"]]
        check(row["domain"] == "nba" and row["target"] in (0, 1), "Unpermitted fitting row")
        w = item["objective_weight"]
        check(isinstance(w, (int, float)) and math.isfinite(w) and w > 0, "Invalid fit weight")
        check(math.isclose(item["training_multiplier"], w * len(weights), rel_tol=1e-12),
              "Objective/batch weight scale differs")
        result.append(row)
    check(math.isclose(sum(w["objective_weight"] for w in weights), 1.0, abs_tol=1e-10),
          "Fit weights do not sum to one")
    return result


def validate_fit_membership(candidates, weights, manifest, fit_name):
    """Independently require every known candidate from the exact declared games."""
    check(fit_name in FIT_GAMES and manifest["fit_id"] == fit_name, "Unexpected fit identity")
    declared = set(FIT_GAMES[fit_name])
    all_games = set(FIT_GAMES["all_nba"])
    check(len(manifest["fit_game_ids"]) == len(declared)
          and set(manifest["fit_game_ids"]) == declared, "Fit manifest games differ")
    check(len(manifest["held_out_game_ids"]) == len(all_games-declared)
          and set(manifest["held_out_game_ids"]) == all_games-declared,
          "Held-out manifest games differ")
    expected = {key for key, row in candidates.items()
                if row["domain"] == "nba" and row["game_id"] in declared and row["target"] in (0, 1)}
    actual = [item["candidate_id"] for item in weights]
    check(len(actual) == len(set(actual)) and set(actual) == expected
          and len(actual) == manifest["fitting_candidates"], "Fit candidate membership differs")
    check({candidates[key]["game_id"] for key in actual} == declared, "Actual fit games differ")
    check({candidates[key]["frame_id"] for key in actual} <= set(manifest["fit_frame_ids"]),
          "Fit candidates leave declared frame membership")
    check(not ({candidates[key]["frame_id"] for key in actual} & set(manifest["held_out_frame_ids"])),
          "Held-out frame entered fit")
    return declared


def trainable_group_fingerprints(model):
    """Exact before/after group hashes, separate from frozen-tensor preservation."""
    digests = {"backbone": hashlib.sha256(), "head": hashlib.sha256()}
    for name, parameter in sorted(model.named_parameters()):
        if parameter.requires_grad:
            group = name.split(".", 1)[0]
            check(group in digests, "Unexpected trainable group")
            digests[group].update(json.dumps([name, list(parameter.shape), str(parameter.dtype)],
                                             separators=(",", ":")).encode()+b"\n")
            digests[group].update(parameter.detach().cpu().contiguous().numpy().tobytes())
    return {name: digest.hexdigest() for name, digest in digests.items()}


def check_first_gradients(model):
    """Runtime-only aggregate nonzero gradients; each parameter must be finite."""
    import torch
    squared_norms = {"backbone": 0.0, "head": 0.0}
    tensors = {"backbone": 0, "head": 0}
    for name, parameter in model.named_parameters():
        if not parameter.requires_grad:
            check(parameter.grad is None, "Frozen gradient appeared")
            continue
        check(parameter.grad is not None and bool(torch.isfinite(parameter.grad).all()),
              "Missing or nonfinite trainable gradient: "+name)
        group = name.split(".", 1)[0]
        norm = float(torch.linalg.vector_norm(parameter.grad.detach()).cpu())
        squared_norms[group] += norm * norm
        tensors[group] += 1
    result = {name: {"norm": math.sqrt(value), "tensors": tensors[name]}
              for name, value in squared_norms.items()}
    check(all(math.isfinite(item["norm"]) and item["norm"] > 0 and item["tensors"] > 0
              for item in result.values()), "Head/backbone gradient must each be finite and nonzero")
    return result


def first_batch_parity(model, pixels, point_weights, manual_features):
    """One standard producer forward checked against the actual manual fit pass."""
    import numpy as np
    import torch
    from .point_feature_inference import point_readout, TOKEN_INDICES
    with torch.no_grad():
        output = model.backbone(pixel_values=pixels, return_dict=True)
        sequence = output.last_hidden_state
        check(tuple(sequence.shape) == (pixels.shape[0], 257, 384)
              and sequence.dtype == torch.float32 and bool(torch.isfinite(sequence).all()),
              "Standard DINO producer output differs")
        check(torch.equal(sequence[:, 0, :], output.pooler_output), "Same-pass CLS contract differs")
        tokens = sequence[:, TOKEN_INDICES.tolist(), :].detach().cpu().numpy()
    weights = point_weights.detach().cpu().numpy()
    actual = manual_features.detach().cpu().numpy()
    check(actual.shape == (pixels.shape[0], 384) and actual.dtype == np.float64,
          "Manual point readout contract differs")
    expected = []
    for sample, query_weights in zip(tokens, weights):
        geometry = {"tokens": [{"sequence_index": int(index), "weight": float(weight)}
                                for index, weight in zip(TOKEN_INDICES, query_weights)]}
        _, unit, reason = point_readout(sample, geometry)
        check(reason is None, "Original point consumer rejected producer output")
        expected.append(unit)
    expected = np.stack(expected)
    difference = float(np.max(np.abs(actual-expected)))
    check(np.allclose(actual, expected, atol=1e-10, rtol=1e-10), "Manual/standard producer point parity failed")
    return {"samples": len(expected), "max_absolute_difference": difference,
            "atol": 1e-10, "rtol": 1e-10,
            "producer": "pinned Dinov2Model.forward plus original float64 point_readout",
            "consumer": "actual first training forward_with_features"}


def preflight(root=ROOT, require_approval=False):
    root = Path(root).resolve()
    out = root / OUTPUT
    config = read(root / CONFIG)
    freeze = read(out / "execution_freeze.json")
    check(config["schema_version"] == "candidate_quality_pilot/v0.1", "Unexpected proposal")
    check(freeze["proposal"] == binding(root, root / CONFIG), "Proposal changed after freeze")
    for link in freeze["bindings"]:
        bound(root, link)
    check(subprocess.check_output(["git", "branch", "--show-current"], cwd=root, text=True).strip()
          == config["branch"], "Branch differs")
    check(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
          == config["head"], "HEAD differs")
    check(not subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=root).strip(),
          "Index must remain empty")
    for name, version in config["runtime"].items():
        check(metadata.version(name) == version, "Runtime metadata differs: " + name)
    if require_approval:
        approval = read(out / "execution_approval.json")
        check(approval.get("training_and_scoring_approved") is True
              and approval.get("execution_freeze") == binding(root, out / "execution_freeze.json")
              and isinstance(approval.get("user_statement"), str) and approval["user_statement"].strip(),
              "Explicit approval for this frozen training/scoring pilot required")
        check(all(approval.get(key) is False for key in
                  ("selector_approved", "protected_access_approved", "new_labels_approved")),
              "Execution scope differs")
    check("torch" not in sys.modules, "Metadata preflight imported Torch")
    return config, freeze


def make_crop_cache(root, items, id_field, destination, model_api):
    """One grouped image decode; uint8 native crops avoid caching ~12GB floats."""
    import numpy as np
    from PIL import Image
    groups = defaultdict(list)
    for index, item in enumerate(items):
        groups[item["source_png"]["path"]].append((index, item))
    cache = np.lib.format.open_memmap(destination, mode="w+", dtype=np.uint8,
                                     shape=(len(items), 64, 64, 3))
    point_weights = np.empty((len(items), 4), dtype=np.float64)
    indices = {}
    for members in groups.values():
        link = members[0][1]["source_png"]
        path = bound(root, link)
        check(all(item["source_png"] == link for _, item in members), "Conflicting source image bindings")
        with Image.open(path) as source:
            image = source.convert("RGB")
            for index, item in members:
                geometry = model_api.point_geometry(item["center_xy_px"], image.width, image.height)
                cache[index] = np.asarray(image.crop(tuple(geometry["crop_box"])), dtype=np.uint8)
                point_weights[index] = geometry["weights"]
                check(item[id_field] not in indices, "Duplicate image query")
                indices[item[id_field]] = index
    cache.flush()
    return cache, point_weights, indices


def input_batch(items, cache, point_weights, indices, id_field):
    import numpy as np
    import torch
    from PIL import Image
    from .nba_appearance_feature_screen import crop_and_preprocess
    positions = [indices[item[id_field]] for item in items]
    pixels = [crop_and_preprocess(Image.fromarray(np.asarray(cache[i])), [32., 32.])[2] for i in positions]
    return (torch.from_numpy(np.stack(pixels)).to("cuda"),
            torch.from_numpy(point_weights[positions].copy()).to("cuda"))


def run(root, monitor, arguments):
    root = Path(root).resolve()
    config, freeze = preflight(root, require_approval=True)
    check(monitor, "Owned supervisor directory required")
    from .continuation_owned_guard import verify_owned_worker
    ownership = verify_owned_worker(root, root / monitor, MODULE, arguments)
    out = root / OUTPUT
    destination = out / "attempt_001"
    destination.mkdir(exist_ok=False)
    began = time.monotonic()
    counters = {"training_forwards_attempted": 0, "training_forwards_returned": 0,
                "optimizer_updates": 0, "training_candidate_presentations": 0,
                "scoring_forwards_attempted": 0, "scoring_forwards_returned": 0,
                "scoring_candidate_presentations": 0, "parity_forwards_attempted": 0,
                "parity_forwards_returned": 0, "parity_candidate_presentations": 0}
    write_once(destination / "started.json", {"at_utc": stamp(), "ownership": ownership,
               "approval": binding(root, out / "execution_approval.json"),
               "execution_freeze": binding(root, out / "execution_freeze.json")})
    # A wall stop requests termination through the already-owned supervisor.
    done = threading.Event()
    def deadline():
        if not done.wait(config["execution"]["wall_stop_seconds"]):
            (root / monitor / "STOP").touch(exist_ok=True)
    threading.Thread(target=deadline, daemon=True).start()
    caches = []
    try:
        # Must precede the first Torch/CUDA import in this owned process.
        check("torch" not in sys.modules, "Torch imported before approved deterministic runtime setup")
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
        candidates = rows(out / "preparation/candidates.jsonl")
        by_id = {r["candidate_id"]: r for r in candidates}
        check(len(candidates) == len(by_id) == config["counts"]["training_package_candidates"],
              "Candidate transport differs")
        _, queries, _, _, _ = evaluation.load_prepared(root)
        emitted = [q for q in queries if q["input_id"] is not None]
        train_cache = make_crop_cache(root, candidates, "candidate_id", destination / "training_crops.npy", model_api)
        caches.append(train_cache[0])
        eval_cache = make_crop_cache(root, emitted, "query_id", destination / "evaluation_crops.npy", model_api)
        caches.append(eval_cache[0])
        journal = destination / "journal.jsonl"
        results = []
        for fit_name in FIT_NAMES:
            fit_dir = destination / fit_name
            fit_dir.mkdir()
            weights = rows(out / f"preparation/fits/{fit_name}/weights.jsonl")
            fit_manifest = read(out / f"preparation/fits/{fit_name}/manifest.json")
            fitting = validate_weights(by_id, weights)
            multipliers = {w["candidate_id"]: w["training_multiplier"] for w in weights}
            fit_games = validate_fit_membership(by_id, weights, fit_manifest, fit_name)
            random.seed(config["training"]["seed"])
            np.random.seed(config["training"]["seed"])
            torch.manual_seed(config["training"]["seed"])
            torch.cuda.manual_seed_all(config["training"]["seed"])
            model = model_api.build_model(root, device="cuda", execution_authorized=True,
                                          seed=config["training"]["seed"])
            frozen_before = model_api.frozen_fingerprint(model)
            trainable_before = trainable_group_fingerprints(model)
            write_once(fit_dir / "initial_tensor_fingerprints.json",
                       {"frozen": frozen_before, "trainable_groups": trainable_before})
            manifest = model_api.trainable_manifest(model)
            write_once(fit_dir / "trainable_parameters.json", manifest)
            optimizer = torch.optim.AdamW(model_api.optimizer_parameter_groups(model),
                                          betas=(0.9, 0.999), eps=1e-8)
            fit_steps = 0
            for epoch in range(1, config["training"]["epochs"] + 1):
                order = list(fitting)
                random.Random(config["training"]["seed"] + epoch).shuffle(order)
                model.train()
                epoch_loss = 0.0
                group_losses = defaultdict(lambda: [0.0, 0.0, 0])
                for batch in batches(order, config["training"]["batch_size"]):
                    pixels, point_weights = input_batch(batch, *train_cache, "candidate_id")
                    targets = torch.tensor([r["target"] for r in batch], device="cuda", dtype=torch.float32)
                    scale = torch.tensor([multipliers[r["candidate_id"]] for r in batch], device="cuda", dtype=torch.float32)
                    optimizer.zero_grad(set_to_none=True)
                    counters["training_forwards_attempted"] += 1
                    append(journal, {"event": "train_start", "fit": fit_name, "epoch": epoch,
                                     "step": fit_steps, "batch_count": len(batch)})
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
                        parity = first_batch_parity(model, pixels, point_weights, actual_features)
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
                        write_once(fit_dir / "first_gradient_checks.json", check_first_gradients(model))
                    grad_norm = torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad],
                                                               max_norm=1.0, error_if_nonfinite=True)
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
                        totals = group_losses[row["target_group"]]
                        totals[0] += contribution; totals[1] += objective_weight; totals[2] += 1
                    append(journal, {"event": "train_return", "fit": fit_name, "epoch": epoch,
                                     "step": fit_steps, "weighted_batch_loss": float(loss.detach().cpu()),
                                     "gradient_norm_before_clip": float(grad_norm.detach().cpu())})
                    del pixels, point_weights, targets, scale, logits, losses, loss, grad_norm
                append(destination / "epochs.jsonl", {"fit": fit_name, "epoch": epoch,
                       "weighted_online_loss": epoch_loss, "group_loss_mass_weight_count": dict(group_losses),
                       "note": "Online changing-model loss, not a held-out validation score"})
                # Retain each epoch for a separately authorized continuation if
                # interrupted. Intermediate checkpoints never enter selection.
                recovery = fit_dir / f"recovery_epoch_{epoch:02d}.pth"
                check(not recovery.exists(), "Recovery checkpoint already exists")
                torch.save({"trainable_state": {n: p.detach().cpu() for n, p in model.named_parameters() if p.requires_grad},
                            "optimizer_state": optimizer.state_dict(), "epoch": epoch, "fit": fit_name,
                            "fit_steps": fit_steps, "counters": dict(counters),
                            "python_rng": random.getstate(), "numpy_rng": np.random.get_state(),
                            "torch_rng": torch.get_rng_state(), "cuda_rng": torch.cuda.get_rng_state_all(),
                            "freeze_sha256": binding(root, out / "execution_freeze.json")["sha256"],
                            "purpose": "Recovery only; fixed epoch6 remains the comparison checkpoint"}, recovery)
                append(destination / "recovery_checkpoints.jsonl", binding(root, recovery))
                print(json.dumps({"fit": fit_name, "epoch": epoch, "steps": fit_steps,
                                  "weighted_online_loss": epoch_loss}), flush=True)
            check(fit_steps == math.ceil(len(fitting) / config["training"]["batch_size"]) * config["training"]["epochs"],
                  "Training step count differs")
            check(model_api.frozen_fingerprint(model) == frozen_before, "Frozen backbone tensors changed")
            trainable_after = trainable_group_fingerprints(model)
            check(all(trainable_after[group] != trainable_before[group] for group in trainable_before),
                  "Trainable backbone and head must each actually change")
            write_once(fit_dir / "final_tensor_fingerprints.json",
                       {"frozen": frozen_before, "trainable_groups": trainable_after,
                        "frozen_unchanged": True, "backbone_and_head_changed": True})
            checkpoint = fit_dir / "final_trainable.pth"
            torch.save({"trainable_state": {n: p.detach().cpu() for n, p in model.named_parameters() if p.requires_grad},
                        "epoch": config["training"]["epochs"], "fit": fit_name,
                        "freeze_sha256": binding(root, out / "execution_freeze.json")["sha256"]}, checkpoint)
            model.eval()
            score_groups = [("package_scores.jsonl", [r for r in candidates if fit_name == "all_nba"
                             or (r["domain"] == "nba" and r["game_id"] in set(fit_manifest["held_out_game_ids"]))],
                             train_cache, "candidate_id")]
            expected_score_ids = (set(by_id) if fit_name == "all_nba" else
                                  {key for key, row in by_id.items() if row["domain"] == "nba"
                                   and row["game_id"] in set(FIT_GAMES["all_nba"])-fit_games})
            check({row["candidate_id"] for row in score_groups[0][1]} == expected_score_ids
                  and len(score_groups[0][1]) == len(expected_score_ids), "Held-game score membership differs")
            if fit_name == "all_nba":
                score_groups.append(("development_scores.jsonl", emitted, eval_cache, "query_id"))
            with torch.inference_mode():
                for filename, scoring, cache, id_field in score_groups:
                    for batch in batches(scoring, config["training"]["batch_size"]):
                        pixels, point_weights = input_batch(batch, *cache, id_field)
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
            result = {"fit": fit_name, "steps": fit_steps, "checkpoint": binding(root, checkpoint),
                      "frozen_tensors_unchanged": True, "fit_manifest": binding(root, out / f"preparation/fits/{fit_name}/manifest.json"),
                      "scores": [binding(root, fit_dir / group[0]) for group in score_groups]}
            write_once(fit_dir / "completed.json", result)
            results.append(result)
            del optimizer, model
            torch.cuda.empty_cache()
        check(counters["optimizer_updates"] == config["counts"]["optimizer_updates"], "Total training budget differs")
        check(counters["training_candidate_presentations"] == config["counts"]["training_candidate_presentations"], "Training presentations differ")
        check(counters["scoring_candidate_presentations"] == config["counts"]["scoring_candidate_presentations"], "Score presentations differ")
        check(counters["training_forwards_attempted"] == counters["training_forwards_returned"] == counters["optimizer_updates"], "Unreturned training call")
        check(counters["scoring_forwards_attempted"] == counters["scoring_forwards_returned"], "Unreturned scoring call")
        check(counters["scoring_forwards_returned"] == config["counts"]["scoring_forwards"], "Scoring call budget differs")
        check(counters["parity_forwards_attempted"] == counters["parity_forwards_returned"] == 4
              and counters["parity_candidate_presentations"] == 128, "Producer parity budget differs")
        result = {"status": "completed_fixed_pilot_no_selector_no_adoption", "at_utc": stamp(),
                  "elapsed_seconds": time.monotonic() - began, "counters": counters, "fits": results,
                  "model_adopted": False, "protected_access": False, "new_labels": 0, "new_selector_runs": 0}
        write_once(destination / "completed.json", result)
        return result
    except BaseException as error:
        write_once(destination / "failed.json", {"at_utc": stamp(), "elapsed_seconds": time.monotonic() - began,
                   "error": type(error).__name__, "message": str(error), "traceback": traceback.format_exc(),
                   "counters": counters, "automatic_retry": False})
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
        config, freeze = preflight()
        print(json.dumps({"status": "metadata_preflight_passed_no_model_import", "bindings": len(freeze["bindings"])}))
    else:
        print(json.dumps(run(ROOT, args.monitor, sys.argv[1:])))


if __name__ == "__main__":
    main()
