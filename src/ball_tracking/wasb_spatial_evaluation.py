"""Evaluate one completed spatial pilot on the unchanged eight NBA contexts.

Fresh absolute epochs six and seven reuse their own HOU validation records.
SAC/DET use the existing verified 768 image cache and new inference. Existing
512, parent768 and constant-epoch6/7 controls remain immutable. NFHS validation
is secondary evidence. No checkpoint is adopted by this module.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import time
import traceback
import uuid

import cv2
import numpy as np
import torch

from . import completion_training_runtime as runtime
from . import nba_first_evaluation as nba
from . import nba_resolution_evaluation as prior
from . import wasb_spatial_training as training
from . import wasb_resolution as resolution
from . import wasb_continuation_evaluation as continuation
from .nba_first_validation import AUTOMATIC_GATES, aggregate_blocks, score_block
from .wasb_experiment import bound_path, canonical, read_json
from .wasb_training import training_lock

SCHEMA = "wasb_spatial_comparison/v0.1"
OUTPUT_ROOT = "data/outputs/ball_tracking/wasb_spatial_v0_1"
CACHE_ROOT = prior.OUTPUT_ROOT + "/input_cache"
ARM = "spatial"
EPOCHS = (6, 7)
CONTROLS = (*continuation.CONTROLS, "constant_epoch6", "constant_epoch7")
RESOLUTION = prior.RESOLUTION
write_once, binding, check = runtime.atomic_write_once, runtime.binding, runtime.check
gains_losses, qualifying_epoch = prior.gains_losses, prior.qualifying_epoch


def output_root():
    return f"{OUTPUT_ROOT}/nba_comparison_v0_1"


def reuse_validation(root, block, report, identity, checkpoint):
    """Only fresh spatial validation can supply a comparison observation."""
    training.validate_report(report, identity)
    check(report["epoch"] in EPOCHS and "reused_validation" not in report,
          "Comparison requires fresh absolute epochs six and seven")
    return prior.reuse_validation(root, block, report, identity, checkpoint)


def secondary_validation(report):
    """Transport actual NFHS validator counts without inventing an acceptance gate."""
    return [{k: deepcopy(v) for k, v in block.items() if k not in {"observations", "frame_results"}}
            for block in report["blocks"] if block["domain"] == "nfhs"]


def read_matched_controls(root, blocks, recipe):
    """Consume saved constant6/7 observations without reading mean arrays/pixels."""
    control_recipe = read_json(bound_path(root, recipe["matched_control_recipe"]))
    fit = read_json(bound_path(root, recipe["matched_control_completed"]))
    completed = read_json(bound_path(root, recipe["matched_control_comparison_completed"]))
    result = read_json(bound_path(root, recipe["matched_control_evaluation"]))
    check(control_recipe["source_recipe"] == recipe["source_recipe"]
          and control_recipe["source_completed"] == recipe["source_completed"]
          and control_recipe["source_state"] == recipe["source_state"], "Matched control parent state differs")
    check(fit["schema_version"] == continuation.training.SCHEMA and fit["status"] == "completed"
          and fit["arm"] == fit["identity"]["arm"] == "constant"
          and fit["identity"]["recipe"] == recipe["matched_control_recipe"]
          and fit["source_completed"] == recipe["source_completed"] and fit["source_state"] == recipe["source_state"]
          and fit["completed_epochs"] == 10 and fit["completed_updates"] == 15520
          and fit["learning_rate_policy"] == continuation.training.ARMS["constant"], "Matched constant fit differs")
    check(completed["schema_version"] == result["schema_version"] == continuation.SCHEMA
          and completed["status"] == "completed" and result["status"] == "completed_evaluation"
          and completed["evaluation"] == recipe["matched_control_evaluation"]
          and completed["identity"] == result["identity"] and result["arm"] == result["identity"]["arm"] == "constant"
          and result["identity"]["recipe"] == recipe["matched_control_recipe"]
          and result["identity"]["training_result"] == recipe["matched_control_completed"]
          and result["identity"]["training_identity"] == fit["identity"]
          and result["identity"]["source_evaluation"] == recipe["source_evaluation"]
          and result["identity"]["resolution"] == RESOLUTION
          and result["model_adopted"] is False and result["ball_phase_accepted"] is False
          and result["human_trajectory_acceptance"] is None and result["protected_evaluation_authorized"] is False
          and completed["optimizer_updates"] == completed["protected_reads"] == 0
          and result["optimizer_updates"] == result["new_labels"] == 0,
          "Matched constant comparison identity differs")
    report_links, reports = continuation.report_bindings(root, fit)
    by_epoch = {report["epoch"]: report for report in reports}
    check([m["epoch"] for m in result["models"]] == list(continuation.EPOCHS), "Saved constant model inventory differs")
    controls = {}
    for epoch in EPOCHS:
        model = next(m for m in result["models"] if m["epoch"] == epoch)
        report = by_epoch[epoch]
        name = f"continuation_constant_epoch{epoch}"
        check(model["name"] == name and model["arm"] == "constant"
              and model["checkpoint"] == report["checkpoint"] == fit["checkpoints"][epoch - 6]
              and [r["block_id"] for r in model["records"]] == [b["block_id"] for b in blocks],
              "Matched constant epoch/checkpoint/context differs")
        bound_path(root, model["checkpoint"])
        continuation.training.validate_report(report, fit["identity"])
        records = {}
        for offset, (block, link, episode) in enumerate(zip(blocks, model["records"], model["episodes"], strict=True)):
            source = report_links[epoch] if offset < 6 else None
            receipt = read_json(bound_path(root, link["receipt"]))
            check(receipt["identity"] == continuation.block_identity(result["identity"], block, report, source),
                  "Matched constant block identity differs")
            body = read_json(bound_path(root, receipt["records"]))
            check(body["block_id"] == block["block_id"] and body["model"] == name and body["arm"] == "constant"
                  and body["epoch"] == epoch and body["checkpoint"] == model["checkpoint"]
                  and body["resolution"] == RESOLUTION and body["validation_source"] == source,
                  "Matched constant emitted record differs")
            nba.validate_records(block, body["observations"])
            score = score_block(block, body["observations"])
            check(body["score"] == score and episode == {"block_id": block["block_id"], "summary": score["summary"]},
                  "Matched constant score differs")
            if source:
                check(body["observations"] == continuation.reuse_validation(root, block, report, fit["identity"], model["checkpoint"]),
                      "Matched constant HOU differs from validation producer")
            check(receipt["new_model_calls"] == (0 if source else len(block["frames"]) - 2)
                  and receipt["reused_observation_frames"] == (len(block["frames"]) if source else 0)
                  and bool(receipt["mean_heatmaps"]) == (source is None), "Matched control work census differs")
            records[block["block_id"]] = {"records": receipt["records"], "receipt": link["receipt"], "score": score}
        controls[f"constant_epoch{epoch}"] = {"checkpoint": model["checkpoint"], "absolute_epoch": epoch,
            "source_model": name, "source_evaluation": recipe["matched_control_evaluation"],
            "training_exposure": model["training_exposure"], "secondary_NFHS_validation": secondary_validation(report),
            "blocks": records}
    return controls


def read_controls(root, blocks, recipe, source_recipe):
    controls = continuation.read_controls(root, blocks, recipe, source_recipe)
    controls.update(read_matched_controls(root, blocks, recipe))
    check(all(controls[f"constant_epoch{epoch}"]["training_exposure"] == controls["resolution_epoch5"]["training_exposure"]
              for epoch in EPOCHS), "Matched control fitted exposure differs from parent")
    return controls


def report_bindings(root, result):
    pairs = [(read_json(bound_path(root, record)), record) for record in result["validation_reports"]]
    check([report["epoch"] for report, _ in pairs] == list(range(5, 8)),
          "Spatial validation epochs must be five through seven")
    return {report["epoch"]: record for report, record in pairs}, [report for report, _ in pairs[1:]]


def preflight(root, recipe_path):
    """Bind completed producer/control records without loading a model or pixels."""
    root = Path(root).resolve()
    arm = ARM
    recipe = read_json(root / recipe_path)
    completed, transport = training.audit_completed_result(root, recipe_path)
    check(completed["arm"] == arm and completed["identity"]["arm"] == arm,
          "Completed producer belongs to a different spatial pilot")
    check(recipe["evaluation_output_root"] == output_root()
          and recipe["evaluation_cache_root"] == CACHE_ROOT, "Spatial comparison paths differ")
    required = Path(__file__).resolve().relative_to(root).as_posix()
    check(required in {entry["path"] for entry in recipe["code_bindings"]}, "Recipe omits spatial evaluation")
    source_recipe = read_json(bound_path(root, recipe["source_recipe"]))
    _, blocks, _ = nba.preflight(root, source_recipe["nba_first_config"]["path"])
    controls = read_controls(root, blocks, recipe, source_recipe)
    bindings, reports = report_bindings(root, completed)
    check(completed["checkpoints"] == [r["checkpoint"] for r in reports]
          and len(reports) == 2, "Spatial checkpoint/report inventory differs")
    for report in reports:
        check([b["block_id"] for b in report["blocks"] if b["domain"] == "nba"] ==
              [b["block_id"] for b in blocks[:6]], "Spatial HOU scope differs")
        for block in blocks[:6]:
            reuse_validation(root, block, report, completed["identity"], report["checkpoint"])
    audit = {"status": "passed", "arm": arm, "training_transport": transport,
        "models": 2, "absolute_epochs": list(EPOCHS), "contexts_per_model": 8,
        "native_frames_per_model": 3662, "total_output_frames": 7324, "new_model_calls": 5396,
        "reused_HOU_observation_frames": 1920, "protected_reads": 0, "optimizer_updates": 0}
    return recipe, blocks, completed, reports, bindings, controls, audit


class ExistingInputCache(prior.InputCache):
    """Require existing receipts before invoking the unchanged cache verifier."""
    def prepare(self):
        check(all((self.folder / nba.key(block) / "receipt.json").is_file() for block in self.blocks),
              "Existing resolution input cache required; reconstruction is not authorized here")
        return super().prepare()


def block_identity(identity, block, report, validation_source):
    return {"comparison": identity, "checkpoint": report["checkpoint"], "epoch": report["epoch"],
            "block_sha256": canonical(block), "validation_source": validation_source}


def validate_block(root, block, report, identity, receipt, name, validation_source):
    check(receipt["identity"] == block_identity(identity, block, report, validation_source),
          "Spatial block identity differs")
    body = read_json(bound_path(root, receipt["records"]))
    check(body["block_id"] == block["block_id"] and body["checkpoint"] == report["checkpoint"]
          and body["epoch"] == report["epoch"] and body["arm"] == identity["arm"]
          and body["model"] == name and body["resolution"] == RESOLUTION
          and body["validation_source"] == validation_source, "Spatial emitted model record differs")
    nba.validate_records(block, body["observations"])
    score = score_block(block, body["observations"])
    check(body["score"] == score, "Spatial emitted score differs")
    expected_calls = 0 if validation_source else len(block["frames"]) - 2
    check(receipt["new_model_calls"] == expected_calls
          and receipt["reused_observation_frames"] == (len(block["frames"]) if validation_source else 0)
          and bool(receipt["mean_heatmaps"]) == (validation_source is None),
          "Spatial block work census differs")
    if receipt["mean_heatmaps"]:
        array = np.load(bound_path(root, receipt["mean_heatmaps"]), mmap_mode="r", allow_pickle=False)
        try:
            check(array.shape == (len(block["frames"]), 432, 768) and array.dtype == np.float32,
                  "Spatial mean-map shape/dtype differs")
        finally:
            array._mmap.close()
    return body, score


def validate_publication(root, completed, identity, reports, report_links, blocks, controls, audit):
    check(completed["schema_version"] == SCHEMA and completed["status"] == "completed"
          and completed["identity"] == identity and completed["optimizer_updates"] == 0
          and completed["protected_reads"] == 0, "Spatial completion identity differs")
    published = read_json(bound_path(root, completed["evaluation"]))
    check(published["schema_version"] == SCHEMA and published["status"] == "completed_evaluation"
          and published["identity"] == identity and published["arm"] == identity["arm"]
          and published["model_adopted"] is False and published["ball_phase_accepted"] is False
          and published["human_trajectory_acceptance"] is None and published["protected_evaluation_authorized"] is False
          and published["optimizer_updates"] == 0 and published["new_labels"] == 0,
          "Spatial publication status differs")
    check([model["epoch"] for model in published["models"]] == list(EPOCHS), "Published absolute epoch census differs")
    total_calls = total_reused = 0
    for model, report in zip(published["models"], reports, strict=True):
        name = f"spatial_epoch{report['epoch']}"
        check(model["name"] == name and model["arm"] == identity["arm"]
              and model["checkpoint"] == report["checkpoint"]
              and model["training_exposure"] == controls["resolution_epoch5"]["training_exposure"],
              "Published spatial model differs")
        check(model["matched_control"] == f"constant_epoch{report['epoch']}"
              and model["secondary_NFHS_validation"] == secondary_validation(report)
              and model["secondary_NFHS_matched_control"] == controls[model["matched_control"]]["secondary_NFHS_validation"],
              "Published matched epoch or secondary NFHS transport differs")
        check(len(model["records"]) == len(model["episodes"]) == 8 and set(model["comparisons"]) == set(CONTROLS),
              "Published spatial context/control inventory differs")
        scored = []
        for offset, (block, link, episode) in enumerate(zip(blocks, model["records"], model["episodes"], strict=True)):
            check(link["block_id"] == block["block_id"], "Published context order differs")
            source = report_links[report["epoch"]] if offset < 6 else None
            receipt = read_json(bound_path(root, link["receipt"]))
            body, score = validate_block(root, block, report, identity, receipt, name, source)
            if source:
                expected = reuse_validation(root, block, report, identity["training_identity"], report["checkpoint"])
                check(body["observations"] == expected, "Published HOU reuse differs from producing validation")
            check(episode == {"block_id": block["block_id"], "summary": score["summary"]},
                  "Published spatial episode score differs")
            for control_name in CONTROLS:
                old = controls[control_name]["blocks"][block["block_id"]]
                expected = {"block_id": block["block_id"], "control_records": old["records"], **gains_losses(score, old["score"])}
                check(model["comparisons"][control_name][offset] == expected, "Published spatial changes differ")
            total_calls += receipt["new_model_calls"]
            total_reused += receipt["reused_observation_frames"]
            scored.append(score)
        check(model["HOU_validation_summary"] == aggregate_blocks(scored[:6]), "Published HOU aggregate differs")
    check(published["new_model_calls"] == completed["total_receipted_model_calls"] == total_calls == audit["new_model_calls"]
          and published["reused_validation_frames"] == total_reused == audit["reused_HOU_observation_frames"],
          "Published spatial work census differs")
    check(published["earliest_epoch_for_human_review"] == qualifying_epoch(published["models"])
          and published["controls"] == {name: {k: v for k, v in control.items() if k != "blocks"}
                                       for name, control in controls.items()}, "Published spatial qualification/controls differ")
    return published


def execute(root, recipe_path):
    root = Path(root).resolve()
    arm = ARM
    recipe, blocks, result, reports, report_links, controls, audit = preflight(root, recipe_path)
    output = root / recipe["evaluation_output_root"]
    output.mkdir(parents=True, exist_ok=True)
    identity = {"recipe": binding(root, root / recipe_path), "arm": arm,
        "training_result": audit["training_transport"]["training_result"], "training_identity": result["identity"],
        "source_evaluation": recipe["source_evaluation"], "matched_control_evaluation": recipe["matched_control_evaluation"],
        "matched_control_comparison_completed": recipe["matched_control_comparison_completed"],
        "resolution": RESOLUTION, "preflight": audit}
    with training_lock(output / "comparison.lock"):
        if (output / "completed.json").exists():
            completed = read_json(output / "completed.json")
            validate_publication(root, completed, identity, reports, report_links, blocks, controls, audit)
            return completed
        attempt = output / "attempts" / uuid.uuid4().hex
        attempt.mkdir(parents=True, exist_ok=False)
        write_once(attempt / "started.json", {"identity": identity, "started_at_utc": nba.stamp()})
        began, calls_this_attempt, adapter = time.perf_counter(), 0, None
        cache = ExistingInputCache(root, blocks[6:], root / recipe["evaluation_cache_root"])
        try:
            torch.set_num_threads(2)
            torch.backends.cudnn.benchmark = False
            torch.backends.cudnn.deterministic = True
            cv2.setNumThreads(1)
            write_once(attempt / "cache_verification.json", cache.prepare())
            models, total_calls, total_reused = [], 0, 0
            for report in reports:
                name = f"spatial_epoch{report['epoch']}"
                scored, links, comparisons = [], [], {name: [] for name in CONTROLS}
                for offset, block in enumerate(blocks):
                    folder = output / "models" / name / nba.key(block)
                    folder.mkdir(parents=True, exist_ok=True)
                    source = report_links[report["epoch"]] if offset < 6 else None
                    receipt_path = folder / "receipt.json"
                    expected_identity = block_identity(identity, block, report, source)
                    if receipt_path.exists():
                        receipt = read_json(receipt_path)
                        body, score = validate_block(root, block, report, identity, receipt, name, source)
                        if source:
                            check(body["observations"] == reuse_validation(root, block, report, result["identity"], report["checkpoint"]),
                                  "Resumed HOU differs from producing validation")
                    else:
                        block_attempt = folder / "attempts" / uuid.uuid4().hex
                        block_attempt.mkdir(parents=True, exist_ok=False)
                        write_once(block_attempt / "started.json", {"identity": expected_identity, "started_at_utc": nba.stamp()})
                        heatmaps, calls = None, 0
                        if source:
                            observations = reuse_validation(root, block, report, result["identity"], report["checkpoint"])
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
                            "epoch": report["epoch"], "arm": arm, "model": name, "resolution": RESOLUTION,
                            "observations": observations, "score": score, "validation_source": source})
                        receipt = {"identity": expected_identity, "records": binding(root, body_path), "mean_heatmaps": heatmaps,
                                   "new_model_calls": calls, "reused_observation_frames": len(observations) if source else 0}
                        write_once(receipt_path, receipt)
                    total_calls += receipt["new_model_calls"]
                    total_reused += receipt["reused_observation_frames"]
                    scored.append(score)
                    links.append({"block_id": block["block_id"], "receipt": binding(root, receipt_path)})
                    for control_name in CONTROLS:
                        old = controls[control_name]["blocks"][block["block_id"]]
                        comparisons[control_name].append({"block_id": block["block_id"], "control_records": old["records"],
                                                         **gains_losses(score, old["score"])})
                    print(json.dumps({"event": "block_completed", "arm": arm, "model": name, "epoch": report["epoch"],
                        "block": block["block_id"], "matched": score["summary"]["matched"], "wrong": score["summary"]["wrong"],
                        "certain_hidden": score["summary"]["certain_hidden_emitted_points"], "reused_validation": source is not None}), flush=True)
                models.append({"name": name, "arm": arm, "epoch": report["epoch"], "checkpoint": report["checkpoint"],
                    "training_exposure": deepcopy(controls["resolution_epoch5"]["training_exposure"]), "records": links,
                    "episodes": [{"block_id": s["block_id"], "summary": s["summary"]} for s in scored],
                    "HOU_validation_summary": aggregate_blocks(scored[:6]), "comparisons": comparisons,
                    "matched_control": f"constant_epoch{report['epoch']}",
                    "secondary_NFHS_validation": secondary_validation(report),
                    "secondary_NFHS_matched_control": deepcopy(controls[f"constant_epoch{report['epoch']}"]["secondary_NFHS_validation"])})
                if adapter is not None:
                    del adapter
                    adapter = None
                    torch.cuda.empty_cache()
            check(total_calls == audit["new_model_calls"] and total_reused == audit["reused_HOU_observation_frames"]
                  and len(models) == audit["models"], "Full spatial comparison census differs")
            published = {"schema_version": SCHEMA, "status": "completed_evaluation", "identity": identity, "arm": arm,
                "models": models, "controls": {name: {k: v for k, v in control.items() if k != "blocks"} for name, control in controls.items()},
                "blocks": [{k: v for k, v in block.items() if k != "frames"} for block in blocks],
                "new_model_calls": total_calls, "reused_validation_frames": total_reused,
                "earliest_epoch_for_human_review": qualifying_epoch(models), "model_adopted": False, "ball_phase_accepted": False,
                "human_trajectory_acceptance": None, "protected_evaluation_authorized": False, "optimizer_updates": 0, "new_labels": 0,
                "limits": ["HOU is repeatedly used validation; DET is inspected development; SAC is training-exposed.",
                    "This spatial pilot and saved constant controls start from the same resolution epoch-five full state.",
                    "Constant controls are reused without inference; the matching control has the same absolute epoch.",
                    "NFHS counts are secondary evidence and do not establish a new NFHS acceptance decision.",
                    "Unknown/inconclusive gates cannot qualify an epoch; human trajectory/object-identity review remains required.",
                    "No cross-arm or historical checkpoint is adopted by this comparison."]}
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
