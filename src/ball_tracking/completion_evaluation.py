"""Fixed post-selection comparison; additive to the frozen fitting implementation.

Only the hash-bound prepared permitted package enters inference.  Block receipts
are reusable after an interrupted attempt; failures never become missing points.
The retained baseline is reused when epoch zero wins.  This command cannot open
protected evaluation or authorize the conditional resolution fit.
"""
from __future__ import annotations

import argparse
from collections import Counter, OrderedDict
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import time
import traceback
import uuid

import numpy as np
from PIL import Image

from . import completion_comparison_render as rendering
from .completion_evaluation_package import (BASELINE_SHA, PRIMARY_RECIPE, ROLE,
    bind_selected_result, normalize_block, validate_component_selection, validate_timeline)
from .completion_scoring import score_timeline
from .completion_training_package import Evidence
from .completion_training_policy import should_stop
from .completion_training_runtime import atomic_write_once as write_once, binding
from .nba_action_observation import select_observation, stream_means
from .wasb_experiment import bound_path, canonical, read_json, runtime_versions


PREPARED = "data/outputs/ball_tracking/completion_campaign_v0_1/training_implementation/evaluation_package_prepared_inputs_v2.json"
PREPARED_SHA = "fd64df421c59ad2c1f535e5d530dd761d1040005cc2385154d1ef68267b26880"
RESULT = "data/outputs/ball_tracking/completion_campaign_v0_1/primary_fit_v0_1/completed.json"
OUTPUT = "data/outputs/ball_tracking/completion_campaign_v0_1/selected_comparison_v0_1"
POLICY = {"threshold": .3, "threshold_operator": ">", "resolution_wh": [512, 288],
          "aggregation": "ascending_float32_aligned_contributor_mean",
          "selection": "largest_component_mass_then_stable_index", "triplet_stride": 1,
          "padding": False, "resampling": False, "interpolation": False}


def check(value, message):
    if not value:
        raise ValueError(message)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def audit_completed_result(root, result_path=RESULT):
    """Consume the real frozen producer's record, without pixels or a model load."""
    root = Path(root).resolve()
    evidence = Evidence(root)
    selected = bind_selected_result(evidence, result_path)
    check(selected is not None, "A completed fit is required")
    result = read_json(root / result_path)
    reports = [read_json(bound_path(root, entry)) for entry in result["validation_reports"]]
    for report in reports:
        bound_path(root, report["checkpoint"])
    check(result["final_checkpoint"] == reports[-1]["checkpoint"], "Final checkpoint/report differs")
    bound_path(root, result["resume_checkpoint"])
    epoch = result["completed_epochs"]
    expected_stop = "max_epochs" if epoch == 20 else "five_epochs_without_rank_improvement"
    check(result["stop_reason"] == expected_stop, "Completed stop reason differs")
    if epoch < 20:
        check(should_stop(epoch, result["selection"]["selected_epoch"]), "Early-stop condition was not met")
    check(result.get("ball_phase_accepted") is False, "Training cannot accept the ball phase")
    return selected, {"status": "passed", "training_result": selected["training_result"],
        "completed_epochs": epoch, "completed_updates": result["completed_updates"],
        "validation_reports_checked": len(reports), "selected_epoch": result["selection"]["selected_epoch"],
        "final_checkpoint": result["final_checkpoint"], "resume_checkpoint": result["resume_checkpoint"],
        "model_loaded": False, "source_pixels_read": False, "protected_evaluation_authorized": False}


def validate_package(package):
    check(package["schema_version"] == "completion_evaluation_package/v0.1", "Evaluation package schema differs")
    check(package["protected_evaluation_authorized"] is False and package["png_assets_verified"] is True
          and not package["missing_png_assets"], "Prepared permitted inputs are not verified")
    check(package["inference_policy"] == POLICY and package["baseline_checkpoint_sha256"] == BASELINE_SHA,
          "Frozen evaluation policy differs")
    blocks, timelines = package["inference_blocks"], package["curated_timelines"]
    check(len(blocks) == 8 and len({b["block_id"] for b in blocks}) == 8
          and sum(len(b["frames"]) for b in blocks) == 3975, "Fixed inference census differs")
    check(len(package["regression_cohorts"]) == 16
          and len({c["cohort_id"] for c in package["regression_cohorts"]}) == 16, "Fixed cohort census differs")
    check(len(timelines) == 3 and {t["possession_id"] for t in timelines} ==
          {"possession_001", "possession_002", "possession_003"}, "Curated possession census differs")
    by_id = {}
    for block in blocks:
        normalize_block(block)
        by_id[block["block_id"]] = {f["source_frame_index"]: f for f in block["frames"]}
    for timeline in timelines:
        validate_timeline(timeline)
        for frame in timeline["frames"]:
            if frame["state"] == "permitted":
                check(by_id[frame["block_id"]][frame["source_frame_index"]] == frame,
                      "Curated timeline/block record transport differs")
    check(sum(len(t["frames"]) for t in timelines) == 1498
          and sum(f["state"] == "withheld" for t in timelines for f in t["frames"]) == 225,
          "Complete/protected timeline census differs")


def prepare_selected_package(root, result_path=RESULT):
    root = Path(root).resolve()
    prepared_binding = {"path": PREPARED, "sha256": PREPARED_SHA}
    package = read_json(bound_path(root, prepared_binding))
    validate_package(package)
    check(package["selected_method"] is None and package["execution_ready"] is False,
          "Prepared original must remain unselected")
    selected, audit = audit_completed_result(root, result_path)
    package.update(selected_method=selected, execution_ready=True, status="selected_method_inputs_prepared")
    package["prepared_package"] = binding(root, root / PREPARED)
    package["selected_result_transport_audit"] = audit
    return package


def baseline_observations(block):
    """Add native transport fields; never change an original saved prediction."""
    normalize_block(block)
    result = []
    for frame in block["frames"]:
        saved = frame["baseline_observation"]
        original = saved["original_record"]
        validate_component_selection(original)
        index = frame["source_frame_index"]
        check(original.get("source_frame_index", original.get("frame_index")) == index,
              "Original baseline frame differs")
        for key in ("center_xy_px", "native_score", "state"):
            check(saved[key] == original[key], "Baseline wrapper changed original prediction")
        count = original.get("temporal_contributions", original.get("contribution_count"))
        check(count == saved["temporal_contributions"] and count > 0, "Baseline contribution transport differs")
        check(original.get("inference_status", "completed") == "completed", "Baseline inference did not complete")
        check(original.get("source_pts_ticks", frame["source_pts_ticks"]) == frame["source_pts_ticks"], "Baseline PTS differs")
        check(Fraction(original.get("time_base", block["time_base"])) == Fraction(block["time_base"]), "Baseline time base differs")
        if "source_png" in original:
            check(all(frame["png"].get(k) == v for k, v in original["source_png"].items()),
                  "Baseline source image differs")
        row = deepcopy(original)
        row.update(source_frame_index=index, source_pts_ticks=frame["source_pts_ticks"], time_base=block["time_base"],
            source_png=frame["png"], inference_status="completed", point_origin="automatic",
            temporal_contributions=count, original_baseline_record=deepcopy(original))
        result.append(row)
    return result


def validate_observations(block, observations):
    check(len(observations) == len(block["frames"]), "Incomplete block output")
    for frame, row in zip(block["frames"], observations, strict=True):
        check(row["source_frame_index"] == frame["source_frame_index"]
              and row["source_pts_ticks"] == frame["source_pts_ticks"]
              and Fraction(row["time_base"]) == Fraction(block["time_base"])
              and row["source_png"] == frame["png"], "Observation/native source transport differs")
        check(row["inference_status"] == "completed" and row.get("point_origin", "automatic") == "automatic",
              "Failed or filled inference is not a model miss")
        check(row["temporal_contributions"] == frame["baseline_observation"]["temporal_contributions"],
              "Candidate and retained temporal contexts differ")
        validate_component_selection(row)


class NativeImages:
    """At most three verified RGB frames; protected rows are rejected before I/O."""
    def __init__(self, root, block):
        self.root, self.block = Path(root).resolve(), block
        self.cache = OrderedDict()
        self.decoded = 0
        self.peak_cached = 0

    def get(self, frame):
        check(frame["state"] == "permitted", "Protected image access prohibited")
        index = frame["source_frame_index"]
        check(not any(a <= index <= b for a, b in self.block.get("protected_ranges", [])),
              "Protected index prohibited")
        if index not in self.cache:
            while len(self.cache) >= 3:
                self.cache.popitem(last=False)
            raw = bound_path(self.root, frame["png"]).read_bytes()
            with Image.open(io.BytesIO(raw)) as image:
                check(image.mode == "RGB", "Prepared native PNG must be RGB")
                rgb = np.asarray(image).copy()
            source = self.block["source_video"]
            check(rgb.shape == (source["height_px"], source["width_px"], 3), "Native source dimensions differ")
            check(hashlib.sha256(rgb.tobytes()).hexdigest() == frame["png"]["rgb_sha256"], "Native RGB hash differs")
            self.cache[index] = rgb
            self.decoded += 1
            self.peak_cached = max(self.peak_cached, len(self.cache))
        self.cache.move_to_end(index)
        return self.cache[index]


def infer_block(root, block, adapter, heatmap_path, progress=None):
    normalize_block(block)
    images = NativeImages(root, block)
    calls = 0
    def provide(frames):
        nonlocal calls
        if progress is not None:
            progress({"event": "triplet_started", "frame_indices": [f["source_frame_index"] for f in frames]})
        values = adapter.predict_triplet([images.get(frame) for frame in frames])["heatmaps"]
        calls += 1
        if progress is not None:
            progress({"event": "triplet_completed", "frame_indices": [f["source_frame_index"] for f in frames],
                      "completed_model_calls": calls, "native_png_decodes": images.decoded})
        return values
    means = np.lib.format.open_memmap(heatmap_path, mode="w+", dtype=np.float32,
                                    shape=(len(block["frames"]), 288, 512))
    observations = []
    try:
        segment = {"kind": "fixed_post_selection", "source_frame_range_inclusive": block["range_inclusive"]}
        for offset, (frame, mean, count) in enumerate(stream_means(block["frames"], provide)):
            check(mean is not None and np.isfinite(mean).all(), "Inference failed to produce a finite mean")
            means[offset] = mean
            observations.append(select_observation(frame, mean, count, block, segment))
        means.flush()
    finally:
        means._mmap.close()
    validate_observations(block, observations)
    return observations, {"model_calls": calls, "native_png_decodes": images.decoded,
        "maximum_cached_native_images": images.peak_cached, "source_video_decodes": 0, "protected_png_reads": 0}


def comparison_changes(baseline, selected):
    check([r["source_frame_index"] for r in baseline] == [r["source_frame_index"] for r in selected], "Score rows differ")
    changed = []
    for old, new in zip(baseline, selected, strict=True):
        if old["automatic_center_xy_px"] != new["automatic_center_xy_px"] or old["outcome"] != new["outcome"]:
            changed.append({"source_frame_index": old["source_frame_index"], "source_pts_ticks": old["source_pts_ticks"],
                "time_base": old["time_base"], "baseline_outcome": old["outcome"], "selected_outcome": new["outcome"],
                "baseline_center_xy_px": old["automatic_center_xy_px"], "selected_center_xy_px": new["automatic_center_xy_px"],
                "gained_match": old["outcome"] != "matched" and new["outcome"] == "matched",
                "lost_match": old["outcome"] == "matched" and new["outcome"] != "matched"})
    return changed


def cohort_counts(rows):
    counts = Counter(r["outcome"] for r in rows)
    return {"frames": len(rows), "eligible": sum(counts[k] for k in ("matched", "wrong", "missing")),
        **{k: counts[k] for k in ("matched", "wrong", "missing", "unscored")},
        "certain_hidden_emissions": sum(r["certain_hidden_emissions"] for r in rows),
        "all_hidden_emissions": sum(len(r["published_points"]) for r in rows
                                    if r["reference_category"] in {"certain_hidden", "uncertain_hidden"})}


def score_package(package, block_records, package_binding):
    """Pure producer of the renderer envelope; no authority follows from a score."""
    blocks = package["inference_blocks"]
    check(set(block_records) == {b["block_id"] for b in blocks}, "Missing/extra inference blocks")
    rows_by_source, observations_by_source = {}, {}
    for block in blocks:
        record = block_records[block["block_id"]]
        check(record["block_sha256"] == canonical(block), "Saved inference block identity differs")
        baseline = baseline_observations(block)
        selected = record["observations"]
        validate_observations(block, selected)
        source_id = block.get("possession_id", block.get("candidate_id"))
        rows_by_source.setdefault(source_id, {"baseline": {}, "selected": {}})
        observations_by_source.setdefault(source_id, {"baseline": [], "selected": []})
        for label, observations in (("baseline", baseline), ("selected", selected)):
            score = score_timeline(block, observations)
            target = rows_by_source[source_id][label]
            check(not set(target).intersection(r["source_frame_index"] for r in score["frame_results"]), "Overlapping source blocks")
            target.update({r["source_frame_index"]: r for r in score["frame_results"]})
            observations_by_source[source_id][label].extend(observations)
    comparisons = []
    for timeline in package["curated_timelines"]:
        pid = timeline["possession_id"]
        result = {"possession_id": pid}
        for label in ("baseline", "selected"):
            observations = sorted(observations_by_source[pid][label], key=lambda r: r["source_frame_index"])
            result[label + "_observations"] = observations
            result[label + "_metrics"] = score_timeline(timeline, observations)
        result["changed_frames"] = comparison_changes(result["baseline_metrics"]["frame_results"],
                                                       result["selected_metrics"]["frame_results"])
        rendering.validate_timeline(timeline, result)
        comparisons.append(result)
    cohorts = []
    for cohort in package["regression_cohorts"]:
        ids = cohort["frame_indices"]
        check(len(ids) == len(set(ids)), "Duplicate cohort indices")
        source = rows_by_source[cohort["source_id"]]
        rows = {label: [source[label][i] for i in ids] for label in ("baseline", "selected")}
        counts = {label: cohort_counts(value) for label, value in rows.items()}
        old, new = counts["baseline"], counts["selected"]
        check(old["eligible"] == new["eligible"], "Comparison eligibility changed")
        conditions = {"matched_not_lower": new["matched"] >= old["matched"],
            "wrong_not_higher": new["wrong"] <= old["wrong"],
            "hidden_not_higher": new["all_hidden_emissions"] <= old["all_hidden_emissions"],
            "certain_hidden_not_higher": new["certain_hidden_emissions"] <= old["certain_hidden_emissions"]}
        if cohort.get("pilot_control"):
            check(old["matched"] == old["eligible"] == 60, "Retained pilot control no longer reproduces 60/60")
            conditions["pilot_60_of_60_retained"] = new["matched"] == new["eligible"] == 60
        cohorts.append({"cohort": cohort, **counts, "conditions": conditions,
            "status": ("pass" if all(conditions.values()) else "fail") if cohort["regression_screen"] else "descriptive_training_exposure",
            "changed_frames": comparison_changes(rows["baseline"], rows["selected"]),
            "baseline_frame_results": rows["baseline"], "selected_frame_results": rows["selected"]})
    selected = package["selected_method"]
    return {"schema_version": "completion_evaluation/v0.1", "status": "completed", "package": package_binding,
        "selected_checkpoint": selected["checkpoint"], "training_result": selected["training_result"],
        "selection": selected["selection"], "selection_outcome": "epoch_zero_retained_primary_not_adopted"
        if selected["selection"]["epoch_zero_selected"] else "trained_checkpoint_selected_pending_development_review",
        "curated_comparisons": comparisons, "regression_cohorts": cohorts,
        "prospective_regression_status": "fail" if any(c["status"] == "fail" for c in cohorts) else "pass",
        "permitted_development_screen": {c["possession_id"]: c["selected_metrics"]["summary"] for c in comparisons},
        "protected_evaluation_authorized": False, "human_trajectory_acceptance": None,
        "full_clip_pass_claimed": False, "conditional_resolution_fit_authorized_by_report": False,
        "wrong_object_review": "pending explicit point-bound evidence; geometry is not object identity",
        "tor": package.get("tor"), "bounded_gap_additions": package.get("bounded_gap_additions")}


def make_adapter(root, package):
    from .wasb_adapted_adapter import AdaptedWasbAdapter
    recipe = read_json(Path(root) / PRIMARY_RECIPE)
    nfhs = read_json(bound_path(root, recipe["nfhs_training_config"]))
    selected = package["selected_method"]
    return AdaptedWasbAdapter(Path(root) / nfhs["upstream_source"],
        bound_path(root, nfhs["pretrained_checkpoint"]), bound_path(root, selected["checkpoint"]),
        selected["checkpoint"]["sha256"], {"completed_selection": selected}, device="cuda")


def execution_identity(root, package):
    """Bind all frozen fitting dependencies and every additive comparison helper."""
    root = Path(root).resolve()
    recipe = read_json(root / PRIMARY_RECIPE)
    check(len(recipe["code_bindings"]) == 25, "Frozen dependency census differs")
    for entry in recipe["code_bindings"]:
        bound_path(root, entry)
    versions = runtime_versions()
    check(versions == recipe["runtime"], "Frozen runtime versions differ")
    dependencies = [binding(root, root / f"src/ball_tracking/{name}.py") for name in
                    ("completion_evaluation", "completion_evaluation_package", "completion_scoring", "completion_comparison_render")]
    return {"selected_package_sha256": canonical(package), "implementation": dependencies[0],
            "comparison_dependencies": dependencies, "frozen_dependencies": recipe["code_bindings"],
            "runtime": versions, "policy": POLICY, "protected_evaluation_authorized": False}


def ensure_review(root, output, completed):
    """Publish a later review separately; never overwrite an earlier completion."""
    root, output = Path(root).resolve(), Path(output).resolve()
    publication = output / "review_publication.json"
    if completed.get("review"):
        for entry in completed["review"].values():
            bound_path(root, entry)
        return completed
    if publication.exists():
        saved = read_json(publication)
        check(saved["evaluation"] == completed["evaluation"] and saved["identity"] == completed["identity"],
              "Review publication binding differs")
        review = saved["review"]
        for entry in review.values():
            bound_path(root, entry)
    else:
        attempt = output / "review_attempts" / uuid.uuid4().hex
        attempt.mkdir(parents=True)
        write_once(attempt / "started.json", {"evaluation": completed["evaluation"], "started_at_utc": stamp()})
        try:
            evaluation = read_json(bound_path(root, completed["evaluation"]))
            review = rendering.render_comparison(root, evaluation["package"], completed["evaluation"],
                                                 str((attempt / "review").relative_to(root)))
            write_once(publication, {"identity": completed["identity"], "evaluation": completed["evaluation"], "review": review})
        except BaseException as error:
            write_once(attempt / "failed.json", {"error_type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc()})
            raise
    return {**completed, "review": review, "review_publication": binding(root, publication)}


def execute(root, *, result_path=RESULT, output_folder=OUTPUT, resume=False, render=False):
    """Execute the authorized fixed comparison; call only after root grants GPU work."""
    from .wasb_training import training_lock
    root = Path(root).resolve()
    output = (root / output_folder).resolve()
    check(output.is_relative_to(root / "data/outputs") and output != root / "data/outputs", "Output escaped data/outputs")
    package = prepare_selected_package(root, result_path)
    identity = execution_identity(root, package)
    check(not output.exists() or resume, "Existing evaluation requires explicit --resume")
    output.mkdir(parents=True, exist_ok=True)
    with training_lock(output / "evaluation.lock"):
        if (output / "identity.json").exists():
            check(read_json(output / "identity.json") == identity, "Evaluation identity changed")
        else:
            check(not resume, "Cannot resume an evaluation that has not started")
            write_once(output / "identity.json", identity)
        write_once(output / "package.json", package)
        package_binding = binding(root, output / "package.json")
        if (output / "completed.json").exists():
            completed = read_json(output / "completed.json")
            check(completed["identity"] == identity, "Completed evaluation identity changed")
            bound_path(root, completed["evaluation"])
            return ensure_review(root, output, completed) if render else completed
        attempt = output / "attempts" / uuid.uuid4().hex
        attempt.mkdir(parents=True)
        began = time.perf_counter()
        write_once(attempt / "started.json", {"identity": identity, "started_at_utc": stamp(), "resume": resume})
        adapter = None
        try:
            records, receipts = {}, []
            for block in package["inference_blocks"]:
                key = hashlib.sha256(block["block_id"].encode()).hexdigest()[:24]
                block_folder = output / "blocks" / key
                block_folder.mkdir(parents=True, exist_ok=True)
                receipt_path = block_folder / "completed.json"
                if receipt_path.exists():
                    receipt = read_json(receipt_path)
                    check(receipt["identity"] == identity and receipt["block_sha256"] == canonical(block), "Saved block binding changed")
                    record = read_json(bound_path(root, receipt["record"]))
                    if receipt.get("mean_heatmaps"):
                        bound_path(root, receipt["mean_heatmaps"])
                    validate_observations(block, record["observations"])
                else:
                    work = block_folder / "attempts" / attempt.name
                    work.mkdir(parents=True)
                    write_once(work / "started.json", {"identity": identity, "block_sha256": canonical(block), "started_at_utc": stamp()})
                    heatmap_binding = None
                    if package["selected_method"]["selection"]["epoch_zero_selected"]:
                        check(package["selected_method"]["checkpoint"]["sha256"] == BASELINE_SHA, "Epoch-zero checkpoint differs")
                        observations = baseline_observations(block)
                        resources = {"model_calls": 0, "native_png_decodes": 0, "protected_png_reads": 0,
                                     "source_video_decodes": 0, "retained_baseline_reused": True}
                    else:
                        required_bytes = len(block["frames"]) * 288 * 512 * 4 + 1024 ** 3
                        check(shutil.disk_usage(work).free >= required_bytes,
                              "Insufficient space for this block's retained means and working reserve")
                        if adapter is None:
                            adapter = make_adapter(root, package)
                        def progress(event):
                            with (work / "triplets.jsonl").open("a", encoding="utf-8") as stream:
                                stream.write(json.dumps({**event, "recorded_at_utc": stamp()}) + "\n")
                                stream.flush()
                                os.fsync(stream.fileno())
                        observations, resources = infer_block(root, block, adapter, work / "mean_heatmaps.npy", progress)
                        heatmap_binding = binding(root, work / "mean_heatmaps.npy")
                    record = {"block_id": block["block_id"], "block_sha256": canonical(block),
                              "observations": observations, "resources": resources}
                    write_once(work / "observations.json", record)
                    receipt = {"identity": identity, "block_sha256": canonical(block), "record": binding(root, work / "observations.json"),
                               "mean_heatmaps": heatmap_binding, "resources": resources}
                    write_once(receipt_path, receipt)
                records[block["block_id"]] = record
                receipts.append(binding(root, receipt_path))
                print(f"Verified comparison block {block['block_id']}: {len(block['frames'])} frames", flush=True)
            evaluation = score_package(package, records, package_binding)
            evaluation["block_receipts"] = receipts
            evaluation["implementation"] = identity["implementation"]
            write_once(output / "evaluation.json", evaluation)
            evaluation_binding = binding(root, output / "evaluation.json")
            # Check the actual serialized producer output against the actual consumer.
            transported = read_json(bound_path(root, evaluation_binding))
            rendering.validate_evaluation(read_json(bound_path(root, package_binding)), transported, package_binding)
            for timeline, comparison in zip(package["curated_timelines"], transported["curated_comparisons"], strict=True):
                rendering.validate_timeline(timeline, comparison)
            review = rendering.render_comparison(root, package_binding, evaluation_binding,
                         str((attempt / "review").relative_to(root))) if render else None
            completed = {"identity": identity, "status": "completed", "evaluation": evaluation_binding,
                         "review": review, "elapsed_seconds": time.perf_counter() - began,
                         "human_trajectory_acceptance": None, "protected_evaluation_authorized": False}
            write_once(output / "completed.json", completed)
            write_once(attempt / "completed.json", {"completion": binding(root, output / "completed.json")})
            return completed
        except BaseException as error:
            write_once(attempt / "failed.json", {"identity": identity, "error_type": type(error).__name__,
                "error": str(error), "traceback": traceback.format_exc(), "elapsed_seconds": time.perf_counter() - began,
                "retry_requires_resume": True, "failed_inference_is_not_missing": True})
            raise
        finally:
            del adapter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--training-result", default=RESULT)
    parser.add_argument("--output-root", default=OUTPUT)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    if args.run:
        result = execute(args.root, result_path=args.training_result, output_folder=args.output_root,
                         resume=args.resume, render=args.render)
        print(json.dumps(result))
    else:
        package = prepare_selected_package(args.root, args.training_result)
        print(json.dumps({"status": "preflight_only_no_model_execution", "selected_method": package["selected_method"],
                          "selected_result_transport_audit": package["selected_result_transport_audit"], "counts": package["counts"]}))


if __name__ == "__main__":
    main()
