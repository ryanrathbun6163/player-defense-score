"""Compare all five 768x432 epochs with fixed NBA contexts and saved controls.

Only --run prepares permitted native PNGs or loads a model. Fresh 768-resolution
HOU validation observations are reused verbatim apart from optional PNG-size
transport; SAC/DET are inferred from a separate native-image cache. Every block
has immutable attempted/completed evidence, so rerunning --run resumes receipts.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
import traceback
import uuid

import cv2
import numpy as np
import torch

from . import completion_resolution_training as training
from . import completion_training_runtime as runtime
from . import nba_first_evaluation as nba
from . import wasb_resolution as resolution
from .nba_first_validation import AUTOMATIC_GATES, aggregate_blocks, score_block
from .wasb_experiment import bound_path, canonical, read_json
from .wasb_training import training_lock

SCHEMA = "nba_resolution_comparison/v0.1"
OUTPUT_ROOT = "data/outputs/ball_tracking/wasb_resolution_v0_1/nba_comparison_v0_1"
CONTROLS = ("retained_baseline", "augmentation_epoch5")
RESOLUTION = {"width": 768, "height": 432, "target_radius": 3.75}
write_once, binding, check = runtime.atomic_write_once, runtime.binding, runtime.check


def reuse_validation(root, block, report, identity, checkpoint):
    """Consume the actual new-resolution validator; reject old-resolution reuse."""
    training.validate_report(report, identity)
    check(report["checkpoint"] == checkpoint, "Validation checkpoint differs from comparison model")
    bound_path(root, checkpoint)
    matching = [b for b in report["blocks"] if b["block_id"] == block["block_id"]]
    check(len(matching) == 1 and matching[0]["domain"] == "nba", "Unique NBA validation block required")
    observations = deepcopy(matching[0]["observations"])
    check(len(observations) == len(block["frames"]), "Validation native census differs")
    for frame, row in zip(block["frames"], observations, strict=True):
        check({"path", "sha256", "rgb_sha256"} <= row["source_png"].keys()
              and all(frame["png"].get(k) == v for k, v in row["source_png"].items()), "Saved validation PNG differs")
        row["source_png"] = deepcopy(frame["png"])
    nba.validate_records(block, observations)
    return observations


def read_controls(root, blocks, parent, evaluation_binding):
    """Bind original emitted control records; never relabel their fitted exposure."""
    result = read_json(bound_path(root, evaluation_binding))
    check(result["schema_version"] == nba.SCHEMA and result["status"] == "completed_evaluation"
          and result["identity"]["config"] == parent
          and result["protected_evaluation_authorized"] is False
          and result["model_adopted"] is False, "Original NBA control evaluation differs")
    controls = {}
    for name in CONTROLS:
        matches = [m for m in result["models"] if m["name"] == name]
        check(len(matches) == 1, "Control model is not unique")
        model = matches[0]
        bound_path(root, model["checkpoint"])
        check([r["block_id"] for r in model["records"]] == [b["block_id"] for b in blocks], "Control context scope differs")
        records = {}
        for block, link, episode in zip(blocks, model["records"], model["episodes"], strict=True):
            receipt = read_json(bound_path(root, link["receipt"]))
            check(receipt["identity"] == {"config": parent, "checkpoint": model["checkpoint"],
                                         "block_sha256": canonical(block)}, "Control receipt identity differs")
            body = read_json(bound_path(root, receipt["records"]))
            check(body["checkpoint"] == model["checkpoint"] and body["block_id"] == block["block_id"]
                  and episode == {"block_id": block["block_id"], "summary": body["score"]["summary"]}, "Control producer/publication differs")
            nba.validate_records(block, body["observations"])
            records[block["block_id"]] = {"records": receipt["records"], "receipt": link["receipt"], "score": body["score"]}
        controls[name] = {"checkpoint": model["checkpoint"], "training_exposure": model["training_exposure"], "blocks": records}
    return controls


def gains_losses(candidate, control):
    """Point-bound changes on identical accepted references; geometry is not identity."""
    new, old = candidate["frame_results"], control["frame_results"]
    check(len(new) == len(old), "Comparison frame census differs")
    fields = ("source_frame_index", "source_pts_ticks", "duration_ticks", "time_base",
              "reference_category", "localization_eligible", "exposure_role")
    changes = {key: [] for key in ("gained_matches", "lost_matches", "new_wrong", "resolved_wrong",
                                  "new_certain_hidden_emissions", "removed_certain_hidden_emissions",
                                  "new_uncertain_hidden_emissions", "removed_uncertain_hidden_emissions")}
    for after, before in zip(new, old, strict=True):
        check(all(after[key] == before[key] for key in fields), "Comparison reference/native transport differs")
        index = after["source_frame_index"]
        for key, is_new, was_old in (
            ("gained_matches", after["outcome"] == "matched", before["outcome"] == "matched"),
            ("new_wrong", after["outcome"] == "wrong", before["outcome"] == "wrong"),
            ("new_certain_hidden_emissions", after["certain_hidden_emissions"] > 0, before["certain_hidden_emissions"] > 0),
            ("new_uncertain_hidden_emissions", after["reference_category"] == "uncertain_hidden" and bool(after["published_points"]),
             before["reference_category"] == "uncertain_hidden" and bool(before["published_points"]))):
            reverse = {"gained_matches": "lost_matches", "new_wrong": "resolved_wrong",
                       "new_certain_hidden_emissions": "removed_certain_hidden_emissions",
                       "new_uncertain_hidden_emissions": "removed_uncertain_hidden_emissions"}[key]
            if is_new and not was_old:
                changes[key].append(index)
            if was_old and not is_new:
                changes[reverse].append(index)
    return {"frame_indices": changes, "counts": {key: len(value) for key, value in changes.items()},
            "control_summary": control["summary"], "candidate_summary": candidate["summary"],
            "semantic_wrong_object_inferred": False}


def qualifying_epoch(models):
    """Only explicit computable passes qualify for review; never adopt a model."""
    for model in sorted(models, key=lambda m: m["epoch"]):
        check(len(model["episodes"]) == 8, "Qualification needs all eight contexts")
        statuses = [episode["summary"].get("gates", {}).get(gate, {}).get("status")
                    for episode in model["episodes"] for gate in AUTOMATIC_GATES]
        if "pass" in statuses and all(value in {"pass", "not_applicable"} for value in statuses):
            return model["epoch"]
    return None


def preflight(root, recipe_path):
    """Hash/native-record checks only; require an actual completed five-epoch fit."""
    root = Path(root).resolve()
    recipe = read_json(root / recipe_path)
    completed, transport = training.audit_completed_result(root, recipe_path)
    check(recipe["evaluation_output_root"] == OUTPUT_ROOT and recipe["resolution"] == RESOLUTION, "Comparison scope differs")
    required = Path(__file__).resolve().relative_to(root).as_posix()
    check(required in {entry["path"] for entry in recipe["code_bindings"]}, "Recipe omits comparison implementation")
    bound_path(root, recipe["nba_first_config"])
    _, blocks, _ = nba.preflight(root, recipe["nba_first_config"]["path"])
    controls = read_controls(root, blocks, recipe["nba_first_config"], recipe["nba_control_evaluation"])
    reports = [read_json(bound_path(root, entry)) for entry in completed["validation_reports"]]
    check([r["epoch"] for r in reports] == list(range(6)) and completed["checkpoints"] == [r["checkpoint"] for r in reports[1:]],
          "Actual five-epoch checkpoint/report census differs")
    for report in reports[1:]:
        check([b["block_id"] for b in report["blocks"] if b["domain"] == "nba"] == [b["block_id"] for b in blocks[:6]],
              "New validation must have exactly the same six HOU contexts")
        for block in blocks[:6]:
            reuse_validation(root, block, report, completed["identity"], report["checkpoint"])
    audit = {"status": "passed", "training_transport": transport, "models": 5, "contexts_per_model": 8,
             "native_frames_per_model": 3662, "total_output_frames": 18310, "new_model_calls": 13490,
             "reused_HOU_observation_frames": 4800, "protected_reads": 0, "optimizer_updates": 0}
    return recipe, blocks, completed, reports[1:], controls, audit


class InputCache:
    """Image-only native-to-768 cache; sparse references never become fake labels."""
    def __init__(self, root, blocks, folder):
        self.root, self.blocks, self.folder = Path(root), blocks, Path(folder)
        self.arrays, self.positions = {}, {}

    def prepare(self):
        receipts = []
        for block in self.blocks:
            check(block["domain"] == "nba" and not block.get("protected_ranges")
                  and all(f["state"] == "permitted" for f in block["frames"]), "Only permitted NBA cache frames")
            folder = self.folder / nba.key(block)
            folder.mkdir(parents=True, exist_ok=True)
            expected = {"block_sha256": canonical(block), "representation": "affine_RGB_uint8_432x768",
                        "resolution": RESOLUTION, "implementation": binding(self.root, Path(__file__)),
                        "primitives": binding(self.root, Path(resolution.__file__)),
                        "normalization": binding(self.root, Path(runtime.__file__))}
            receipt_path = folder / "receipt.json"
            if receipt_path.exists():
                receipt = read_json(receipt_path)
                check(receipt["identity"] == expected, "Input-cache identity changed")
                path = bound_path(self.root, receipt["array"])
            else:
                attempt = folder / "attempts" / uuid.uuid4().hex
                attempt.mkdir(parents=True, exist_ok=False)
                write_once(attempt / "started.json", expected)
                path = attempt / "frames.npy"
                array = np.lib.format.open_memmap(path, mode="w+", dtype=np.uint8,
                                                shape=(len(block["frames"]), resolution.HEIGHT, resolution.WIDTH, 3))
                images = nba.evaluation.NativeImages(self.root, block)
                source = block["source_video"]
                forward, _ = resolution.affine_matrices(source["width_px"], source["height_px"])
                try:
                    for offset, frame in enumerate(block["frames"]):
                        array[offset] = cv2.warpAffine(images.get(frame), forward, (resolution.WIDTH, resolution.HEIGHT), flags=cv2.INTER_LINEAR)
                    array.flush()
                finally:
                    array._mmap.close()
                receipt = {"identity": expected, "array": binding(self.root, path), "native_png_decodes": images.decoded,
                           "source_video_decodes": 0, "protected_reads": 0, "annotation_targets_created": 0}
                write_once(receipt_path, receipt)
            array = np.load(path, mmap_mode="r", allow_pickle=False)
            self.arrays[block["block_id"]] = array
            check(array.dtype == np.uint8 and array.shape == (len(block["frames"]), resolution.HEIGHT, resolution.WIDTH, 3),
                  "Input-cache shape or dtype differs")
            self.positions[block["block_id"]] = {f["source_frame_index"]: i for i, f in enumerate(block["frames"])}
            verified = []
            images = nba.evaluation.NativeImages(self.root, block)
            for offset in sorted({0, (len(block["frames"]) - 3) // 2, len(block["frames"]) - 3}):
                frames = block["frames"][offset:offset + 3]
                expected_tensor, _ = resolution.preprocess_triplet([images.get(f) for f in frames])
                indices = [f["source_frame_index"] for f in frames]
                check(torch.equal(self.inputs(block["block_id"], indices).unsqueeze(0), expected_tensor), "Actual preprocessing/cache differs")
                verified.append(indices)
            receipts.append({"receipt": binding(self.root, receipt_path), "exact_preprocessing_triplets": verified})
            print(json.dumps({"event": "cache_verified", "block": block["block_id"], "frames": len(block["frames"])}), flush=True)
        return receipts

    def inputs(self, block_id, indices):
        return torch.cat([runtime.normalized_tensor(self.arrays[block_id][self.positions[block_id][index]]) for index in indices])

    def close(self):
        for array in self.arrays.values():
            array._mmap.close()
        self.arrays.clear()


def execute(root, recipe_path):
    root = Path(root).resolve()
    recipe, blocks, training_result, reports, controls, audit = preflight(root, recipe_path)
    output = root / OUTPUT_ROOT
    output.mkdir(parents=True, exist_ok=True)
    identity = {"recipe": binding(root, root / recipe_path), "training_result": audit["training_transport"]["training_result"],
                "original_controls": recipe["nba_control_evaluation"], "resolution": RESOLUTION, "preflight": audit}
    with training_lock(output / "comparison.lock"):
        if (output / "completed.json").exists():
            completed = read_json(output / "completed.json")
            check(completed["identity"] == identity, "Completed comparison identity differs")
            published = read_json(bound_path(root, completed["evaluation"]))
            for model in published["models"]:
                for link in model["records"]:
                    receipt = read_json(bound_path(root, link["receipt"]))
                    bound_path(root, receipt["records"])
                    if receipt["mean_heatmaps"]:
                        bound_path(root, receipt["mean_heatmaps"])
            return completed
        attempt = output / "attempts" / uuid.uuid4().hex
        attempt.mkdir(parents=True, exist_ok=False)
        write_once(attempt / "started.json", {"identity": identity, "started_at_utc": nba.stamp()})
        began = time.perf_counter()
        cache = InputCache(root, blocks[6:], output / "input_cache")
        calls_this_attempt, adapter = 0, None
        try:
            torch.set_num_threads(2)
            torch.backends.cudnn.benchmark = False
            torch.backends.cudnn.deterministic = True
            cv2.setNumThreads(1)
            write_once(attempt / "cache_verification.json", cache.prepare())
            models, total_calls, total_reused = [], 0, 0
            for report in reports:
                name = f"resolution_epoch{report['epoch']}"
                report_binding = training_result["validation_reports"][report["epoch"]]
                scored, links, comparisons = [], [], {name: [] for name in CONTROLS}
                adapter = None
                for offset, block in enumerate(blocks):
                    folder = output / "models" / name / nba.key(block)
                    folder.mkdir(parents=True, exist_ok=True)
                    receipt_path = folder / "receipt.json"
                    source = report_binding if offset < 6 else None
                    block_identity = {"comparison": identity, "checkpoint": report["checkpoint"],
                                      "block_sha256": canonical(block), "validation_source": source}
                    if receipt_path.exists():
                        receipt = read_json(receipt_path)
                        check(receipt["identity"] == block_identity, "Resumed block identity differs")
                        body = read_json(bound_path(root, receipt["records"]))
                        if receipt["mean_heatmaps"]:
                            bound_path(root, receipt["mean_heatmaps"])
                        nba.validate_records(block, body["observations"])
                        score = score_block(block, body["observations"])
                        check(body["block_id"] == block["block_id"] and body["checkpoint"] == report["checkpoint"]
                              and body["score"] == score and body["validation_source"] == source, "Resumed emitted record differs")
                    else:
                        block_attempt = folder / "attempts" / uuid.uuid4().hex
                        block_attempt.mkdir(parents=True, exist_ok=False)
                        write_once(block_attempt / "started.json", {"identity": block_identity, "started_at_utc": nba.stamp()})
                        heatmaps, calls = None, 0
                        if source is not None:
                            observations = reuse_validation(root, block, report, training_result["identity"], report["checkpoint"])
                        else:
                            if adapter is None:
                                adapter = nba.evaluation.make_adapter(root, {"selected_method": {
                                    "checkpoint": report["checkpoint"], "provenance": audit["training_transport"]["training_result"]}})
                            mean_path = block_attempt / "mean_heatmaps.npy"
                            observations, calls = resolution.infer(block, adapter.model, adapter.device, cache, mean_path, name)
                            heatmaps = binding(root, mean_path)
                        calls_this_attempt += calls
                        score = score_block(block, observations)
                        body_path = block_attempt / "records.json"
                        write_once(body_path, {"block_id": block["block_id"], "checkpoint": report["checkpoint"],
                            "resolution": RESOLUTION, "observations": observations, "score": score, "validation_source": source})
                        receipt = {"identity": block_identity, "records": binding(root, body_path), "mean_heatmaps": heatmaps,
                                   "new_model_calls": calls, "reused_observation_frames": len(observations) if source else 0}
                        write_once(receipt_path, receipt)
                    expected_calls = 0 if source else len(block["frames"]) - 2
                    check(receipt["new_model_calls"] == expected_calls
                          and receipt["reused_observation_frames"] == (len(block["frames"]) if source else 0)
                          and bool(receipt["mean_heatmaps"]) == (source is None), "Completed block work census differs")
                    total_calls += receipt["new_model_calls"]
                    total_reused += receipt["reused_observation_frames"]
                    scored.append(score)
                    links.append({"block_id": block["block_id"], "receipt": binding(root, receipt_path)})
                    for control_name in CONTROLS:
                        control = controls[control_name]["blocks"][block["block_id"]]
                        comparisons[control_name].append({"block_id": block["block_id"], "control_records": control["records"],
                                                         **gains_losses(score, control["score"])})
                    print(json.dumps({"event": "block_completed", "model": name, "block": block["block_id"],
                        "matched": score["summary"]["matched"], "wrong": score["summary"]["wrong"],
                        "certain_hidden": score["summary"]["certain_hidden_emitted_points"], "reused_validation": source is not None}), flush=True)
                models.append({"name": name, "epoch": report["epoch"], "checkpoint": report["checkpoint"],
                    "training_exposure": deepcopy(controls["augmentation_epoch5"]["training_exposure"]), "records": links,
                    "episodes": [{"block_id": s["block_id"], "summary": s["summary"]} for s in scored],
                    "HOU_validation_summary": aggregate_blocks(scored[:6]), "comparisons": comparisons})
                if adapter is not None:
                    del adapter
                    adapter = None
                    torch.cuda.empty_cache()
            check(total_calls == audit["new_model_calls"] and total_reused == audit["reused_HOU_observation_frames"]
                  and len(models) == audit["models"], "Full comparison census differs")
            candidate = qualifying_epoch(models)
            published = {"schema_version": SCHEMA, "status": "completed_evaluation", "identity": identity,
                "models": models, "controls": {name: {k: v for k, v in control.items() if k != "blocks"} for name, control in controls.items()},
                "blocks": [{k: v for k, v in b.items() if k != "frames"} for b in blocks],
                "new_model_calls": total_calls, "reused_validation_frames": total_reused,
                "earliest_epoch_for_human_review": candidate, "model_adopted": False, "ball_phase_accepted": False,
                "human_trajectory_acceptance": None, "protected_evaluation_authorized": False, "optimizer_updates": 0, "new_labels": 0,
                "limits": ["HOU is repeatedly used validation; DET is inspected development; SAC is training-exposed.",
                           "Unknown/inconclusive computable gates cannot qualify an epoch; not_applicable is not a pooled pass.",
                           "Human object-identity/trajectory review remains required; geometry does not establish identity.",
                           "Historical rejection decisions and high-school evidence remain unchanged."]}
            write_once(output / "evaluation.json", published)
            completed = {"schema_version": SCHEMA, "status": "completed", "identity": identity,
                "evaluation": binding(root, output / "evaluation.json"), "attempt": binding(root, attempt / "started.json"),
                "completed_block_calls_this_attempt": calls_this_attempt, "total_receipted_model_calls": total_calls,
                "optimizer_updates": 0, "protected_reads": 0, "elapsed_seconds_this_attempt": time.perf_counter() - began}
            write_once(output / "completed.json", completed)
            return completed
        except BaseException as error:
            write_once(attempt / "failed.json", {"status": "failed_preserved", "error": str(error), "traceback": traceback.format_exc(),
                "completed_block_calls_this_attempt": calls_this_attempt, "partial_block_calls_not_in_this_count": True,
                "elapsed_seconds_this_attempt": time.perf_counter() - began})
            raise
        finally:
            cache.close()
            if adapter is not None:
                del adapter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--recipe", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    result = execute(args.root, args.recipe) if args.run else preflight(args.root, args.recipe)[-1]
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
