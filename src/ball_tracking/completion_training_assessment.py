"""One frozen epoch-five training-context assessment; no fitting or selection.

The default CLI is metadata-only preflight. --run performs each complete native
training triplet once, including all-masked contexts needed for exact streaming
observations. Only supervised channels contribute to the reported focal loss.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import traceback
import uuid

import numpy as np
import torch

from . import completion_training as runner
from . import completion_training_runtime as runtime
from . import wasb_training as training
from .nba_action_observation import stream_means, select_observation
from .wasb_experiment import bound_path, canonical, read_json

RECIPE = "configs/ball_tracking/completion_campaign/primary_recipe_v0_1.json"
RESULT = "data/outputs/ball_tracking/completion_campaign_v0_1/primary_fit_v0_1/completed.json"
OUTPUT = "data/outputs/ball_tracking/completion_next_step_v0_1/training_assessment_epoch005"
CATEGORIES = ("positive_foreground", "visible_background", "certain_hidden")
check = runtime.check
write_once = runtime.atomic_write_once


def stamp():
    return datetime.now(timezone.utc).isoformat()


def training_view(package):
    """Validate roles/joins before any pixels; retain only training blocks."""
    blocks = package["training_blocks"]
    check(len({b["block_id"] for b in blocks}) == len(blocks), "Duplicate training block")
    identities = set()
    for block in blocks:
        check(block["role"] == "training", "Only training roles may enter assessment")
        check(block["domain"] in {"nba", "nfhs"}, "Unknown training domain")
        indices = [f["source_frame_index"] for f in block["frames"]]
        check(len(indices) >= 3 and indices == list(range(indices[0], indices[-1] + 1)),
              "Training context must contain consecutive native frames")
        for frame in block["frames"]:
            index = frame["source_frame_index"]
            check(frame["annotation"]["frame_index"] == index, "Annotation/native frame mismatch")
            check(not any(lo <= index <= hi for lo, hi in package["protected_ranges"].get(block["game_id"], [])),
                  "Protected frame cannot enter training assessment")
            key = (block["source_video"]["sha256"], index)
            check(key not in identities, "Duplicate source frame across training blocks")
            identities.add(key)
    expected = {}
    for block in blocks:
        for offset in range(len(block["frames"]) - 2):
            frames = block["frames"][offset:offset + 3]
            mask = [f["valid_output_channel"] for f in frames]
            if any(mask):
                expected[(block["block_id"], tuple(f["source_frame_index"] for f in frames))] = mask
    actual = {}
    for triplet in package["training_triplets"]:
        key = (triplet["block_id"], tuple(triplet["frame_indices"]))
        check(key not in actual, "Duplicate supervised triplet")
        actual[key] = triplet["valid_output_channels"]
    check(actual == expected, "Usable training triplets differ from actual frame producer")
    return {"training_blocks": blocks, "validation_blocks": []}


def preflight(root, recipe_path=RECIPE, result_path=RESULT):
    root = Path(root).resolve()
    recipe, package, _, nfhs, frozen_identity = runner.preflight(root, recipe_path)
    check(len(recipe["code_bindings"]) == 25, "Frozen dependency census differs")
    result = read_json(root / result_path)
    check(result["schema_version"] == "completion_training_result/v0.1"
          and result["status"] == "completed" and result["identity"] == frozen_identity
          and result["completed_epochs"] == 5 and result["completed_updates"] == 7760,
          "Expected actual completed five-epoch primary result")
    check(result.get("ball_phase_accepted") is False, "Fit cannot accept the phase")
    checkpoint = result["final_checkpoint"]
    bound_path(root, checkpoint)
    reports = [read_json(bound_path(root, item)) for item in result["validation_reports"]]
    check([r["epoch"] for r in reports] == list(range(6)), "Epoch report census differs")
    check(all(r["identity"] == frozen_identity for r in reports), "Epoch identity differs")
    check(reports[-1]["checkpoint"] == checkpoint, "Final checkpoint differs from epoch-five producer")
    check(runner.policy.choose_checkpoint(reports)["selected_epoch"]
          == result["selection"]["selected_epoch"], "Completed checkpoint selection differs")
    view = training_view(package)
    check(sum(len(b["frames"]) for b in view["training_blocks"]) == 3329
          and len(package["training_triplets"]) == 3103, "Frozen training census differs")
    identity = {"schema_version": "completion_training_assessment_identity/v0.1",
        "recipe": runtime.binding(root, root / recipe_path), "package": recipe["package"],
        "training_result": runtime.binding(root, root / result_path), "checkpoint": checkpoint,
        "frozen_code_bindings": recipe["code_bindings"], "runtime": recipe["runtime"],
        "implementation": runtime.binding(root, Path(__file__)),
        "policy": {"training_only": True, "epoch": 5, "threshold": .3,
            "aggregation": "ascending_float32_aligned_contributor_mean", "triplet_stride": 1,
            "loss": "frozen_clamped_gamma2_wbce", "optimizer_updates": 0,
            "selection_or_phase_acceptance": False, "protected_evaluation_authorized": False}}
    counts = {"training_frames": 3329, "training_blocks": len(view["training_blocks"]),
        "supervised_triplets": 3103,
        "inference_triplets": sum(len(b["frames"]) - 2 for b in view["training_blocks"])}
    counts["all_masked_triplets_excluded_from_loss"] = counts["inference_triplets"] - counts["supervised_triplets"]
    return recipe, package, nfhs, identity, counts


def empty_loss():
    return {"categories": {k: {"term_sum": 0.0, "pixels": 0} for k in CATEGORIES},
        "supervised_channel_occurrences": 0, "masked_channel_occurrences": 0,
        "supervised_triplets": 0, "all_masked_triplets": 0,
        "sum_triplet_objectives": 0.0, "max_decomposition_roundoff": 0.0}


def loss_breakdown(logits, targets, valid, kinds):
    """Exact frozen float32 terms; float64 reduction makes category sums stable."""
    check(logits.dtype == targets.dtype == torch.float32 and logits.shape == targets.shape
          and logits.ndim == 4 and logits.shape[:2] == (1, 3)
          and valid.dtype == torch.bool and valid.shape == (1, 3), "Loss tensor contract differs")
    check(bool(torch.isfinite(logits).all()) and bool(torch.isfinite(targets).all()), "Nonfinite loss input")
    check(len(kinds) == 3 and all(k in {"positive", "hidden", "masked"} for k in kinds), "Invalid supervision kinds")
    check(valid.tolist()[0] == [k != "masked" for k in kinds], "Kind/mask differs")
    check(bool(((targets == 0) | (targets == 1)).all()), "Frozen targets must remain binary")
    result = empty_loss()
    result["supervised_channel_occurrences"] = int(valid.sum())
    result["masked_channel_occurrences"] = 3 - int(valid.sum())
    if not bool(valid.any()):
        result["all_masked_triplets"] = 1
        return result
    p = logits.sigmoid().clamp(1e-4, 1 - 1e-4)
    terms = -((1 - p) ** 2 * targets * torch.log(p) + p ** 2 * (1 - targets) * torch.log(1 - p))
    for channel, kind in enumerate(kinds):
        if kind == "masked":
            continue
        truth, values = targets[0, channel], terms[0, channel]
        if kind == "hidden":
            check(not bool(truth.any()), "Certain-hidden target must be zero")
            masks = {"certain_hidden": torch.ones_like(truth, dtype=torch.bool)}
        else:
            check(bool(truth.any()), "Positive target has no foreground")
            masks = {"positive_foreground": truth == 1, "visible_background": truth == 0}
        for name, mask in masks.items():
            result["categories"][name]["term_sum"] += float(values[mask].sum(dtype=torch.float64))
            result["categories"][name]["pixels"] += int(mask.sum())
    exact = float(training.masked_wbce(logits, targets, valid))
    count = sum(c["pixels"] for c in result["categories"].values())
    derived = sum(c["term_sum"] for c in result["categories"].values()) / count
    error = abs(derived - exact)
    check(error <= max(1e-10, abs(exact) * 2e-6), "Loss decomposition differs from frozen producer")
    result.update(supervised_triplets=1, sum_triplet_objectives=exact, max_decomposition_roundoff=error)
    return result


def merge_loss(total, part):
    for name in CATEGORIES:
        for field in ("term_sum", "pixels"):
            total["categories"][name][field] += part["categories"][name][field]
    for name in ("supervised_channel_occurrences", "masked_channel_occurrences", "supervised_triplets",
                 "all_masked_triplets", "sum_triplet_objectives"):
        total[name] += part[name]
    total["max_decomposition_roundoff"] = max(total["max_decomposition_roundoff"], part["max_decomposition_roundoff"])


def summarize_loss(loss):
    result = json.loads(json.dumps(loss))
    denominator = sum(c["pixels"] for c in loss["categories"].values())
    result["valid_pixel_denominator"] = denominator
    result["global_valid_pixel_mean"] = sum(c["term_sum"] for c in loss["categories"].values()) / denominator if denominator else None
    result["mean_supervised_triplet_objective"] = loss["sum_triplet_objectives"] / loss["supervised_triplets"] if loss["supervised_triplets"] else None
    for value in result["categories"].values():
        value["category_pixel_mean"] = value["term_sum"] / value["pixels"] if value["pixels"] else None
        value["contribution_to_global_mean"] = value["term_sum"] / denominator if denominator else None
    result["interpretation"] = "One exhaustive native-context pass, repeated temporal output channels; not the sampled batch-two training loss or unique-frame loss. Masked pixels excluded."
    return result


def model_digest(model):
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        value = tensor.detach().cpu().contiguous()
        digest.update(name.encode())
        digest.update(str((value.dtype, tuple(value.shape))).encode())
        digest.update(value.numpy().tobytes())
    return digest.hexdigest()


def assess_block(model, device, store, block, event=lambda row: None):
    check(block["role"] == "training", "Assessment cannot read a validation block")
    model.eval()
    frames = [{"source_frame_index": f["source_frame_index"], "source_pts_ticks": f["source_pts_ticks"],
               "png": f["png"]} for f in block["frames"]]
    indexed = {f["source_frame_index"]: f for f in block["frames"]}
    source = block["source_video"]
    manifest = {"source_video": source, "time_base": block["time_base"]}
    segment = {"kind": "training_only_assessment", "source_frame_range_inclusive":
               [frames[0]["source_frame_index"], frames[-1]["source_frame_index"]]}
    totals, calls = empty_loss(), 0
    def provide(selected):
        nonlocal calls
        indices = [f["source_frame_index"] for f in selected]
        event({"event": "started", "block_id": block["block_id"], "frame_indices": indices})
        target_rows = [training.annotation_target(store.labels[block["block_id"]][i],
                       source["width_px"], source["height_px"]) for i in indices]
        kinds = [r[2]["kind"] for r in target_rows]
        check(kinds == [indexed[i]["kind"] for i in indices], "Parsed training kind differs from package")
        with torch.inference_mode():
            inputs = store.inputs(block["block_id"], indices).unsqueeze(0).to(device)
            logits = model(inputs)[0]
            check(logits.shape == (1, 3, 288, 512) and bool(torch.isfinite(logits).all()), "Invalid assessment logits")
            targets = torch.from_numpy(np.stack([r[0] for r in target_rows])).unsqueeze(0).to(device)
            valid = torch.tensor([[r[1] for r in target_rows]], dtype=torch.bool, device=device)
            part = loss_breakdown(logits, targets, valid, kinds)
            heatmaps = logits.sigmoid()[0].cpu().numpy().astype(np.float32, copy=False)
        merge_loss(totals, part)
        calls += 1
        event({"event": "completed", "block_id": block["block_id"], "frame_indices": indices,
               "supervised_channels": part["supervised_channel_occurrences"]})
        return heatmaps
    observations = [select_observation(frame, mean, count, manifest, segment)
                    for frame, mean, count in stream_means(frames, provide)]
    score = runtime.scored_block(block, observations)
    unique = dict(Counter(f["kind"] for f in block["frames"]))
    return {**score, "source_video": source, "unique_frame_supervision": unique,
            "loss": totals, "observations": observations,
            "resources": {"model_calls": calls, "source_video_decodes": 0,
                "validation_png_reads": 0, "protected_png_reads": 0, "optimizer_updates": 0}}


def make_adapter(root, nfhs, identity):
    from .wasb_adapted_adapter import AdaptedWasbAdapter
    return AdaptedWasbAdapter(Path(root) / nfhs["upstream_source"],
        bound_path(root, nfhs["pretrained_checkpoint"]), bound_path(root, identity["checkpoint"]),
        identity["checkpoint"]["sha256"], {"training_only_assessment": identity}, device="cuda")


def aggregate(records):
    sources, total = {}, empty_loss()
    metrics = ("matched", "wrong", "missing", "eligible_frames", "certain_hidden_emissions", "all_hidden_emissions")
    for row in records:
        key = row["game_id"]
        source = sources.setdefault(key, {"domain": row["domain"], "blocks": 0, "frames": 0,
            **{m: 0 for m in metrics}, "loss": empty_loss(), "unique_frame_supervision": Counter()})
        source["blocks"] += 1
        source["frames"] += len(row["observations"])
        for name in metrics:
            source[name] += row[name]
        source["unique_frame_supervision"].update(row["unique_frame_supervision"])
        merge_loss(source["loss"], row["loss"])
        merge_loss(total, row["loss"])
    for source in sources.values():
        source["loss"] = summarize_loss(source["loss"])
        source["unique_frame_supervision"] = dict(source["unique_frame_supervision"])
    unique = Counter()
    for row in records:
        unique.update(row["unique_frame_supervision"])
    return {"sources": sources, "loss": summarize_loss(total),
            "supervision_accounting": {"unique_frames": dict(unique),
                "supervised_channel_occurrences": total["supervised_channel_occurrences"],
                "repeated_supervised_channel_occurrences": total["supervised_channel_occurrences"] - unique["positive"] - unique["hidden"],
                "masked_channel_occurrences_excluded": total["masked_channel_occurrences"]},
            "totals": {name: sum(r[name] for r in records) for name in metrics},
            "model_calls": sum(r["resources"]["model_calls"] for r in records)}


def execute(root, *, output_folder=OUTPUT, resume=False):
    root = Path(root).resolve()
    recipe, package, nfhs, identity, counts = preflight(root)
    output = runner.output_path(root, output_folder)
    output.mkdir(parents=True, exist_ok=True)
    with training.training_lock(output / "assessment.lock"):
        identity_path = output / "identity.json"
        if identity_path.exists():
            check(resume and read_json(identity_path) == identity, "Existing assessment requires --resume and identical method")
        else:
            check(not resume, "No assessment exists to resume")
            write_once(identity_path, identity)
        completed_path = output / "completed.json"
        if completed_path.exists():
            complete = read_json(completed_path)
            check(complete["identity"] == identity, "Completed identity differs")
            saved = read_json(bound_path(root, complete["assessment"]))
            for entry in saved["block_receipts"]:
                receipt = read_json(bound_path(root, entry))
                check(receipt["identity"] == identity, "Completed block identity differs")
                bound_path(root, receipt["record"])
            return complete
        attempt = output / "attempts" / uuid.uuid4().hex
        attempt.mkdir(parents=True)
        began, store, adapter = time.perf_counter(), None, None
        write_once(attempt / "started.json", {"identity": identity, "counts": counts, "started_at_utc": stamp()})
        try:
            records, receipts, model_before = [], [], None
            view = training_view(package)
            for block in view["training_blocks"]:
                key = hashlib.sha256(block["block_id"].encode()).hexdigest()[:24]
                receipt_path = output / "blocks" / key / "receipt.json"
                if receipt_path.exists():
                    receipt = read_json(receipt_path)
                    check(receipt["identity"] == identity and receipt["block_sha256"] == canonical(block), "Block receipt changed")
                    record = read_json(bound_path(root, receipt["record"]))
                    check(record["block_id"] == block["block_id"], "Block record mismatch")
                else:
                    if store is None:
                        check(torch.cuda.is_available(), "Assessment requires CUDA; no silent CPU fallback")
                        # Keep original cache identity to reuse verified training arrays, but
                        # remove validation blocks before any prepare/pixel/cache access.
                        store = runtime.FrameStore(root, package, root / recipe["cache_root"])
                        store.blocks = {b["block_id"]: b for b in view["training_blocks"]}
                        write_once(attempt / "training_cache.json", store.prepare())
                        adapter = make_adapter(root, nfhs, identity)
                        adapter.model.eval().requires_grad_(False)
                        model_before = model_digest(adapter.model)
                    def event(row):
                        with (attempt / "triplets.jsonl").open("a", encoding="utf-8") as stream:
                            stream.write(json.dumps({**row, "recorded_at_utc": stamp()}) + "\n")
                            stream.flush()
                    record = assess_block(adapter.model, adapter.device, store, block, event)
                    check(model_digest(adapter.model) == model_before, "Model tensors changed during assessment")
                    record_path = attempt / (key + ".json")
                    write_once(record_path, record)
                    receipt = {"identity": identity, "block_sha256": canonical(block),
                        "record": runtime.binding(root, record_path), "model_tensors_unchanged": True}
                    write_once(receipt_path, receipt)
                records.append(record)
                receipts.append(runtime.binding(root, receipt_path))
                print(f"Assessed training block {block['block_id']}: {record['matched']}/{record['eligible_frames']} matched", flush=True)
            summary = aggregate(records)
            check(summary["model_calls"] == counts["inference_triplets"]
                  and summary["loss"]["supervised_triplets"] == counts["supervised_triplets"]
                  and summary["loss"]["all_masked_triplets"] == counts["all_masked_triplets_excluded_from_loss"], "Assessment census differs")
            assessment = {"schema_version": "completion_training_assessment/v0.1", "identity": identity,
                "status": "completed_training_only", "counts": counts, **summary, "block_receipts": receipts,
                "source_video_decodes": 0, "validation_png_reads": 0, "protected_png_reads": 0,
                "optimizer_updates": 0, "model_tensors_unchanged": True,
                "checkpoint_selection_changed": False, "ball_phase_accepted": False,
                "interpretation": "Descriptive training fit only; no validation, transfer or phase acceptance claim."}
            write_once(output / "assessment.json", assessment)
            complete = {"identity": identity, "status": "completed", "assessment": runtime.binding(root, output / "assessment.json"),
                        "elapsed_seconds": time.perf_counter() - began}
            write_once(completed_path, complete)
            write_once(attempt / "completed.json", {"completion": runtime.binding(root, completed_path)})
            return complete
        except BaseException as error:
            write_once(attempt / "failed.json", {"identity": identity, "error_type": type(error).__name__,
                "error": str(error), "traceback": traceback.format_exc(), "elapsed_seconds": time.perf_counter() - began,
                "failed_inference_is_not_missing": True})
            raise
        finally:
            if store is not None:
                store.close()
            del adapter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--output-root", default=OUTPUT)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.run:
        result = execute(args.root, output_folder=args.output_root, resume=args.resume)
    else:
        _, _, _, identity, counts = preflight(args.root)
        result = {"status": "preflight_only_no_model_or_pixels", "identity": identity, "counts": counts}
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
