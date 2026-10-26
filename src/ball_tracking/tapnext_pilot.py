"""Frozen, single-policy TAPNext++ pilot with separate compatibility execution.

No labels enter the adapter. All eight inference records are sealed before the
unchanged development contract is scored. Protected images cannot be decoded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time
import traceback
import uuid

from .completion_evaluation import (NativeImages, baseline_observations,
    validate_package, stamp)
from .completion_training_runtime import atomic_write_once as write_once, binding, check
from .tapnext_adapter import create_adapter, project_wasb_observation
from .wasb_experiment import bound_path, canonical, read_json, runtime_versions
from .wasb_training import training_lock

SCOPE = "configs/ball_tracking/proposals/ball_tracking_successor_v0_1.json"
ASSESSMENT = "data/outputs/ball_tracking/completion_next_step_v0_1/training_assessment_epoch005/assessment.json"
AUDIT = "data/outputs/t/successor_assessment_audit_20261025/audit.json"
ROOT_OUTPUT = "data/outputs/ball_tracking/successor_campaign_v0_1"
OUTPUT = ROOT_OUTPUT + "/tapnextpp512_pilot_v0_1"


def safe_output(root, folder):
    path = (root / folder).resolve()
    check(path.is_relative_to(root / "data/outputs") and path != root / "data/outputs",
          "Output must remain below data/outputs")
    return path


def prediction_input(block, frame, baseline):
    check(frame["state"] == "permitted", "Protected frames cannot reach prediction")
    return {"source_frame_index": frame["source_frame_index"],
        "source_pts_ticks": frame["source_pts_ticks"], "duration_ticks": frame["duration_ticks"],
        "time_base": block["time_base"], "source_png": frame["png"],
        "wasb_observation": project_wasb_observation(baseline)}


def inputs(root, assets_path):
    scope = read_json(root / SCOPE)
    for key in ("review", "accepted_quality_contract"):
        bound_path(root, scope[key])
    package = read_json(bound_path(root, scope["tap_pilot"]["prepared_package"]))
    validate_package(package)
    check([{ "block_id": b["block_id"], "frames": len(b["frames"])}
           for b in package["inference_blocks"]] == scope["tap_pilot"]["blocks"], "Pilot census differs")
    recipe = read_json(bound_path(root, scope["continuation"]["parent_recipe"]))
    for entry in recipe["code_bindings"]:
        bound_path(root, entry)
    check(len(recipe["code_bindings"]) == 25, "Frozen dependency census differs")
    check(runtime_versions() == recipe["runtime"], "Runtime differs from preserved environment")
    assets_path = (root / assets_path).resolve()
    check(assets_path.is_relative_to(root / "data/outputs"), "Assets must be local ignored evidence")
    assets = read_json(assets_path)
    bound_path(root, assets["checkpoint"])
    return scope, package, recipe, assets, binding(root, assets_path)


def record_skip(root):
    """Record the approved conditional resource decision, not a scientific proof."""
    decision = {"schema_version": "successor_continuation_decision/v0.1",
        "decision": "skip_epoch6_to10_duration_control",
        "authority": binding(root, root / SCOPE), "assessment": binding(root, root / ASSESSMENT),
        "independent_audit": binding(root, root / AUDIT),
        "observed_training_fit": {"matched": 2931, "eligible": 2941, "wrong": 10,
            "missing": 0, "certain_hidden_emissions": 3, "nfhs_matched": 130, "nfhs_eligible": 130},
        "reason": "Near-perfect training fit, including all NFHS positives, makes another five epochs a lower-priority use of resources than the approved temporal challenger.",
        "limits": "This is prioritization, not proof that more epochs cannot improve transfer or that overfitting is the only cause.",
        "optimizer_updates": 0, "parent_results_modified": False, "protected_evaluation_authorized": False}
    assessment = read_json(bound_path(root, decision["assessment"]))
    totals = assessment["totals"]
    check(totals["matched"] == 2931 and totals["eligible_frames"] == 2941
          and totals["wrong"] == 10 and totals["missing"] == 0
          and totals["certain_hidden_emissions"] == 3,
          "Actual training assessment no longer supports recorded decision")
    nfhs = [r for r in assessment["sources"].values() if r["domain"] == "nfhs"]
    check(sum(r["matched"] for r in nfhs) == sum(r["eligible_frames"] for r in nfhs) == 130,
          "Actual NFHS training fit differs from recorded decision")
    audit = read_json(bound_path(root, decision["independent_audit"]))
    check(audit["status"] == "passed" and not audit["discrepancies"], "Training assessment audit did not pass")
    path = root / ROOT_OUTPUT / "continuation_decision.json"
    write_once(path, decision)
    return binding(root, path)


def implementation(root, recipe):
    names = ("tapnext_pilot", "tapnext_adapter", "tapnext_evaluation", "gpu_supervision",
             "completion_evaluation", "completion_evaluation_package", "completion_scoring",
             "completion_comparison_render", "completion_nba_comparison_render")
    return {"implementation": [binding(root, root / f"src/ball_tracking/{n}.py") for n in names],
        "scope": binding(root, root / SCOPE),
        "plan": binding(root, root / "docs/ball_tracking_successor_execution_plan.md"),
        "frozen_dependencies": recipe["code_bindings"], "runtime": runtime_versions()}


def compatibility(root, assets_path, output_folder):
    """Four already permitted training images; results never enter pilot scoring."""
    root = Path(root).resolve()
    scope, package, recipe, assets, assets_binding = inputs(root, assets_path)
    output = safe_output(root, output_folder)
    check(not output.exists(), "Compatibility attempts must use a fresh directory")
    output.mkdir(parents=True)
    identity = {**implementation(root, recipe), "assets": assets_binding,
                "purpose": "four_training_frame_interface_memory_probe_no_selection"}
    write_once(output / "started.json", {"identity": identity, "started_at_utc": stamp()})
    start = time.perf_counter()
    try:
        train = read_json(bound_path(root, recipe["package"]))
        keys = {(b["source_video"]["sha256"], f["source_frame_index"])
                for b in train["training_blocks"] if b["role"] == "training" for f in b["frames"]}
        chosen = None
        for block in package["inference_blocks"]:
            baseline = baseline_observations(block)
            for offset in range(len(block["frames"]) - 3):
                frames = block["frames"][offset:offset + 4]
                if baseline[offset]["center_xy_px"] is not None and all(
                    (block["source_video"]["sha256"], f["source_frame_index"]) in keys for f in frames):
                    chosen = block, frames, baseline[offset:offset + 4]
                    break
            if chosen:
                break
        check(chosen is not None, "No four-frame permitted training probe available")
        block, frames, baseline = chosen
        adapter = create_adapter(root, assets)
        source = block["source_video"]
        adapter.begin_block("compatibility_only:" + block["block_id"], source["width_px"], source["height_px"], block["time_base"])
        images, observations, timings = NativeImages(root, block), [], []
        for frame, old in zip(frames, baseline, strict=True):
            began = time.perf_counter()
            observations.append(adapter.observe(images.get(frame), prediction_input(block, frame, old)))
            timings.append(time.perf_counter() - began)
            print(f"Compatibility frame {frame['source_frame_index']} completed in {timings[-1]:.3f}s", flush=True)
        check(adapter.calls == 4, "Probe did not exercise four actual recurrent model calls")
        write_once(output / "observations.json", observations)
        completed = {"status": "passed", "identity": identity, "assets": assets_binding,
            "observations": binding(root, output / "observations.json"), "frame_seconds": timings,
            "elapsed_seconds": time.perf_counter() - start, "model_calls": 4,
            "training_only": True, "protected_png_reads": 0, "scientific_pilot_outputs": False,
            "cpu_or_resolution_fallback": False}
        write_once(output / "completed.json", completed)
        return completed
    except BaseException as error:
        write_once(output / "failed.json", {"error_type": type(error).__name__, "error": str(error),
            "traceback": traceback.format_exc(), "elapsed_seconds": time.perf_counter() - start})
        raise


def infer_block(root, block, adapter, work):
    from .tapnext_evaluation import validate_observations
    source = block["source_video"]
    adapter.begin_block(block["block_id"], source["width_px"], source["height_px"], block["time_base"])
    images, observations = NativeImages(root, block), []
    started = time.perf_counter()
    with (work / "frames.jsonl").open("x", encoding="utf-8") as log:
        for frame, baseline in zip(block["frames"], baseline_observations(block), strict=True):
            row = adapter.observe(images.get(frame), prediction_input(block, frame, baseline))
            observations.append(row)
            log.write(json.dumps(row, allow_nan=False) + "\n")
            log.flush()
            if len(observations) % 100 == 0:
                print(f"{block['block_id']}: {len(observations)}/{len(block['frames'])} frames", flush=True)
    validate_observations(block, observations)
    return {"block_id": block["block_id"], "block_sha256": canonical(block), "observations": observations,
        "resources": {"model_calls": adapter.calls, "native_png_decodes": images.decoded,
            "maximum_cached_native_images": images.peak_cached, "protected_png_reads": 0,
            "elapsed_seconds": time.perf_counter() - started}}


def execute(root, assets_path, compatibility_path, *, output_folder=OUTPUT, resume=False):
    from . import tapnext_evaluation as evaluation
    root = Path(root).resolve()
    scope, package, recipe, assets, assets_binding = inputs(root, assets_path)
    probe = read_json(root / compatibility_path)
    check(probe["status"] == "passed" and probe["model_calls"] == 4
          and probe["assets"] == assets_binding and probe["training_only"] is True, "Compatibility receipt differs")
    code_identity = implementation(root, recipe)
    check(all(probe["identity"][k] == v for k, v in code_identity.items()), "Implementation changed after compatibility probe")
    decision = record_skip(root)
    identity = {"schema_version": "tapnext_pilot_identity/v0.1", **code_identity,
        "assets": assets_binding, "compatibility": binding(root, root / compatibility_path),
        "continuation_decision": decision, "policy": scope["tap_pilot"]["policy"],
        "prepared_package": scope["tap_pilot"]["prepared_package"], "protected_evaluation_authorized": False}
    package.update(selected_method={"method_kind": "tapnextpp512_single_seed",
        "checkpoint": assets["checkpoint"], "automatic_seed_checkpoint_sha256": scope["tap_pilot"]["seed_checkpoint_sha256"],
        "policy": scope["tap_pilot"]["policy"]}, execution_ready=True, status="fixed_tapnext_pilot")
    package["baseline_inference_policy"] = package["inference_policy"]
    package["inference_policy"] = scope["tap_pilot"]["policy"]
    if "selected_result_transport_audit" in package:
        package["retained_baseline_result_transport_audit"] = package.pop("selected_result_transport_audit")
    output = safe_output(root, output_folder)
    check(not output.exists() or resume, "Existing pilot requires --resume")
    output.mkdir(parents=True, exist_ok=True)
    check(shutil.disk_usage(output).free >= 3 * 1024**3, "Insufficient output reserve")
    with training_lock(output / "pilot.lock"):
        write_once(output / "identity.json", identity)
        write_once(output / "package.json", package)
        package_binding = binding(root, output / "package.json")
        if (output / "completed.json").exists():
            completed = read_json(output / "completed.json")
            check(completed["identity"] == identity, "Completed pilot identity differs")
            bound_path(root, completed["evaluation"])
            return completed
        attempt = output / "attempts" / uuid.uuid4().hex
        attempt.mkdir(parents=True)
        write_once(attempt / "started.json", {"identity": identity, "started_at_utc": stamp(), "resume": resume})
        adapter, records, receipts, began = None, {}, [], time.perf_counter()
        try:
            for block in package["inference_blocks"]:
                folder = output / "blocks" / hashlib.sha256(block["block_id"].encode()).hexdigest()[:24]
                receipt_path = folder / "completed.json"
                if receipt_path.exists():
                    receipt = read_json(receipt_path)
                    check(receipt["identity"] == identity and receipt["block_sha256"] == canonical(block), "Prior block identity differs")
                    record = read_json(bound_path(root, receipt["record"]))
                    check(record["block_sha256"] == canonical(block), "Prior record block differs")
                    evaluation.validate_observations(block, record["observations"])
                else:
                    work = folder / "attempts" / attempt.name
                    work.mkdir(parents=True)
                    write_once(work / "started.json", {"identity": identity, "block_sha256": canonical(block), "started_at_utc": stamp()})
                    if adapter is None:
                        adapter = create_adapter(root, assets)
                    record = infer_block(root, block, adapter, work)
                    write_once(work / "observations.json", record)
                    receipt = {"identity": identity, "block_sha256": canonical(block),
                        "record": binding(root, work / "observations.json"), "resources": record["resources"]}
                    write_once(receipt_path, receipt)
                records[block["block_id"]] = record
                receipts.append(binding(root, receipt_path))
                print(f"Sealed {block['block_id']}: {len(block['frames'])} native frames", flush=True)
            # This seal precedes every label-dependent calculation.
            write_once(output / "inference_sealed.json", {"identity": identity, "block_receipts": receipts,
                "frames": 3975, "protected_png_reads": 0})
            scored = evaluation.score_package(package, records, package_binding)
            scored["block_receipts"] = receipts
            scored["inference_seal"] = binding(root, output / "inference_sealed.json")
            write_once(output / "evaluation.json", scored)
            completed = {"status": "completed", "identity": identity,
                "evaluation": binding(root, output / "evaluation.json"), "elapsed_seconds": time.perf_counter() - began,
                "human_trajectory_acceptance": None, "protected_evaluation_authorized": False, "ball_phase_accepted": False}
            write_once(output / "completed.json", completed)
            write_once(attempt / "completed.json", {"completion": binding(root, output / "completed.json")})
            return completed
        except BaseException as error:
            write_once(attempt / "failed.json", {"identity": identity, "error_type": type(error).__name__,
                "error": str(error), "traceback": traceback.format_exc(), "elapsed_seconds": time.perf_counter() - began,
                "failed_inference_is_not_missing": True, "retry_requires_resume": True})
            raise
        finally:
            del adapter


def render(root, output_folder):
    from .tapnext_evaluation import render_all
    root = Path(root).resolve()
    output = safe_output(root, output_folder)
    complete = read_json(output / "completed.json")
    evaluation = read_json(bound_path(root, complete["evaluation"]))
    publication = output / "review_publication.json"
    if publication.exists():
        prior = read_json(publication)
        check(prior["evaluation"] == complete["evaluation"], "Prior review refers to another evaluation")
        return prior
    records = {}
    for entry in evaluation["block_receipts"]:
        receipt = read_json(bound_path(root, entry))
        record = read_json(bound_path(root, receipt["record"]))
        records[record["block_id"]] = record
    destination = output / "review_attempts" / uuid.uuid4().hex
    write_once(destination / "started.json", {"evaluation": complete["evaluation"], "started_at_utc": stamp()})
    try:
        review = render_all(root, evaluation["package"], complete["evaluation"], records,
                           (destination / "review").relative_to(root).as_posix())
        result = {"evaluation": complete["evaluation"], "review": review,
                  "human_trajectory_acceptance": None, "protected_evaluation_authorized": False}
        write_once(publication, result)
        return result
    except BaseException as error:
        write_once(destination / "failed.json", {"error_type": type(error).__name__, "error": str(error),
            "traceback": traceback.format_exc()})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--assets")
    parser.add_argument("--compatibility")
    parser.add_argument("--output-root", default=OUTPUT)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    if args.render:
        result = render(args.root, args.output_root)
    elif args.run and args.probe:
        result = compatibility(args.root, args.assets, args.output_root)
    elif args.run:
        check(bool(args.assets and args.compatibility), "Assets and compatibility receipt are required")
        result = execute(args.root, args.assets, args.compatibility, output_folder=args.output_root, resume=args.resume)
    else:
        root = Path(args.root).resolve()
        scope, package, recipe, assets, asset_binding = inputs(root, args.assets)
        result = {"status": "metadata_only", "assets": asset_binding, "blocks": len(package["inference_blocks"]),
                  "identity": implementation(root, recipe), "continuation_decision": record_skip(root)}
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
