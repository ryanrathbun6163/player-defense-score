"""Approved, resumable observations on unlabeled native NBA action frames.

Preparation and source-continuity review precede inference. No annotation is
fabricated, no completed pilot triplet is reinferred, and no accuracy is scored.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
import uuid

import numpy as np
from PIL import Image

from . import nba_wasb_diagnostic as d
from .wasb_adapter import components_from_heatmap
from .wasb_experiment import canonical

SCHEMA = "nba_wasb_action_observation/v0.1"


def inference_identity():
    names = {"stream_means", "select_observation", "infer_action", "new_triplet"}
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    definitions = {node.name: ast.dump(node, include_attributes=False) for node in tree.body
                   if isinstance(node, ast.FunctionDef) and node.name in names}
    d.require(set(definitions) == names, "Inference implementation inventory differs")
    return {"action_inference_ast_sha256": canonical(definitions),
            "diagnostic_producer": d.inference_code_identity()}


def load_context(root, proposal_path, approval_path):
    root = Path(root).resolve()
    proposal = d.read_json(proposal_path)
    approval = d.read_json(approval_path)
    proposal_binding = d.binding(root, proposal_path)
    d.require(approval.get("schema_version") == "nba_wasb_action_observation_approval/v0.1"
              and approval.get("status") == "approved" and approval.get("approved_by") == "Ryan",
              "Action observation requires approval")
    d.require(approval.get("proposal") == proposal_binding, "Approval proposal bytes differ")
    scope = approval["scope"]
    d.require(scope.get("proposal_id") == proposal["proposal_id"]
              and all(scope.get(k) is True for k in ("implement", "validate", "execute_one_resumable_run")),
              "Approval lacks implementation and execution scope")
    window_fields = {"candidate_id", "game_id", "approved_role", "source_frame_range_inclusive",
                     "source_pts_ticks_inclusive", "source_end_exclusive_pts_ticks", "time_base",
                     "frames", "timeline_duration_seconds", "maximum_complete_triplets",
                     "planned_prior_triplet_imports", "maximum_new_model_calls"}
    d.require(len(scope["windows"]) == len(proposal["windows"]), "Approved window inventory differs")
    for approved, window in zip(scope["windows"],proposal["windows"]):
        d.require(set(approved) == window_fields and approved == {k:window[k] for k in window_fields},
                  "Approved windows differ")
    for key in ("totals", "model_recipe", "source_and_scene_policy", "cache_and_memory_policy",
                "outputs", "validation_before_real_run", "resource_estimate"):
        d.require(scope[key] == proposal[key], f"Approved {key} differs")
    recipe = proposal["model_recipe"]
    d.require(recipe == {"checkpoint_sha256": d.EXPANDED_SHA,
              "prior_diagnostic_config": proposal["model_recipe"]["prior_diagnostic_config"],
              "native_input_spacing_ms": [16,17], "strict_heatmap_threshold": .3,
              "selection": "largest_component_mass_then_stable_candidate_index",
              "aggregation": "mean_aligned_complete_triplets", "triplet_stride": 1,
              "dtype": "float32", **{k: False for k in ("training", "threshold_search", "motion_selector",
                  "interpolation", "padding", "resampling", "external_model_context")}}, "Unsupported recipe")
    result = d.read_json(d.bound(root, proposal["authority"]["completed_pilot_result"]))
    accepted = d.read_json(d.bound(root, proposal["authority"]["accepted_pilot_model_outputs"]))
    d.require(accepted["status"] == "accepted", "Pilot model output review is not accepted")
    config = d.read_json(d.bound(root, recipe["prior_diagnostic_config"]))
    d.require(config["inference"] == d.POLICY, "Original diagnostic policy changed")
    old_output = d.contained(root, config["output_root"])
    evidence = {x["path"]: x for x in result["evidence"]}
    def old_record(path):
        return d.read_json(d.bound(root, evidence[path.relative_to(root).as_posix()]))
    prior_identity = old_record(old_output / "run_identity.json")
    d.require(prior_identity["inference_code"] == d.inference_code_identity(),
              "Prior inference producer changed; investigate before importing")
    old_plan = {"checkpoint": prior_identity["checkpoint"], "inference_code": prior_identity["inference_code"]}
    training = d.read_json(d.bound(root, config["checkpoint_completion"]))
    d.require(training["checkpoint"] == old_plan["checkpoint"]
              and training["checkpoint"]["sha256"] == recipe["checkpoint_sha256"], "Checkpoint identity differs")
    references = d.read_json(d.bound(root, result["reference"]))["references"]
    old_observations = {r["candidate_id"]: old_record(old_output/r["candidate_id"]/"observations.json")
                        for r in references}
    d.require({r["candidate_id"] for r in references} == {w["candidate_id"] for w in proposal["windows"]},
              "Approved candidate inventory differs")
    return {"proposal": proposal, "proposal_binding": proposal_binding, "approval": d.binding(root, approval_path),
            "config": config, "references": references, "old_plan": old_plan, "training": training,
            "old_output": old_output, "old_observations": old_observations,
            "output": d.contained(root, proposal["outputs"]["root"])}


def validate_manifest(manifest, window, reference):
    d.require("annotations" not in manifest, "Unlabeled input must not fabricate annotations")
    for key in ("candidate_id", "game_id", "approved_role", "source_video", "time_base"):
        expected = reference[key] if key == "source_video" else window[key]
        d.require(manifest[key] == expected, f"Input manifest {key} differs")
    frames = manifest["frames"]
    first, last = window["source_frame_range_inclusive"]
    d.require([f["source_frame_index"] for f in frames] == list(range(first,last+1)), "Input range differs")
    ticks = [f["source_pts_ticks"] for f in frames]
    d.require([ticks[0], ticks[-1]] == window["source_pts_ticks_inclusive"]
              and all(b-a in (1440,1530) for a,b in zip(ticks,ticks[1:])), "Native timing differs")
    d.require(manifest["source_end_exclusive_pts_ticks"] == window["source_end_exclusive_pts_ticks"],
              "Final native display interval differs")
    indexed = {f["source_frame_index"]: f for f in frames}
    d.require(all(indexed[f["source_frame_index"]] == f for f in reference["frames"]),
              "Original pilot frame records changed")


def load_scenes(root, path, context, manifests):
    scene = d.read_json(path)
    d.require(scene.get("status") == "ai_source_continuity_reviewed"
              and scene.get("proposal") == context["proposal_binding"], "Missing approved-scope continuity review")
    d.require(len(scene["windows"]) == len(manifests), "Scene review inventory differs")
    result = {}
    for manifest in manifests:
        candidate = manifest["candidate_id"]
        matches = [x for x in scene["windows"] if x["candidate_id"] == candidate]
        d.require(len(matches) == 1, "Missing or duplicate scene review")
        item = matches[0]
        manifest_path = context["output"] / "inputs" / candidate / "manifest.json"
        d.require(item["input_manifest"] == d.binding(root,manifest_path), "Scene review input binding differs")
        frames = manifest["frames"]
        coverage = []
        for segment in item["segments"]:
            first,last = segment["source_frame_range_inclusive"]
            d.require(type(first) is int and type(last) is int and last >= first, "Invalid segment range")
            d.require(segment.get("kind") in ("live_action", "replay", "cutaway", "uncertain"), "Missing segment kind")
            coverage.extend(range(first,last+1))
        d.require(coverage == [f["source_frame_index"] for f in frames], "Segments must cover every frame exactly once")
        result[candidate] = item["segments"]
    return result


def load_prepared(root, context):
    """Use the completed preparation; each PNG is verified when actually consumed."""
    from .nba_action_inputs import _source_rows
    manifests = []
    for window in context["proposal"]["windows"]:
        _source_rows(root, window)  # Small audit/map bindings and unchanged source stat, no decode.
        reference = next(r for r in context["references"] if r["candidate_id"] == window["candidate_id"])
        path = context["output"]/"inputs"/window["candidate_id"]/"manifest.json"
        manifest = d.read_json(path)
        expected = {"schema_version":"nba_action_inputs/v0.1","proposal":context["proposal_binding"],
                    "approval":context["approval"],"window":window,"reused_frames":reference["frames"]}
        d.require(manifest["preparation"]["identity"] == expected, "Prepared input authority changed")
        for record in manifest["preparation"]["range_completions"]:
            d.bound(root,record)
        validate_manifest(manifest,window,reference)
        manifests.append(manifest)
    return manifests


def stream_means(frames, triplet_provider):
    """Same ascending float32 additions as merge_heatmaps, with at most 3 sums."""
    sums, counts = {}, {}
    if len(frames) < 3:
        for frame in frames:
            yield frame, None, 0
        return
    for offset in range(len(frames)-2):
        values = triplet_provider(frames[offset:offset+3])
        d.validate_heatmaps(values)
        for channel, frame in enumerate(frames[offset:offset+3]):
            index = frame["source_frame_index"]
            if index not in sums:
                sums[index] = np.zeros((288,512),np.float32)
                counts[index] = 0
            sums[index] += values[channel]
            counts[index] += 1
        frame = frames[offset]
        index = frame["source_frame_index"]
        count = counts.pop(index)
        yield frame, sums.pop(index)/np.float32(count), count
    for frame in frames[-2:]:
        index = frame["source_frame_index"]
        count = counts.pop(index)
        yield frame, sums.pop(index)/np.float32(count), count


def select_observation(frame, mean, count, manifest, segment):
    candidates = [] if mean is None else components_from_heatmap(
        mean, manifest["source_video"]["width_px"],manifest["source_video"]["height_px"],threshold=.3)
    candidates = [{"candidate_index": i, **c} for i,c in enumerate(candidates)]
    chosen = min(candidates,key=lambda c:(-c["native_score"],c["candidate_index"])) if candidates else None
    return {"source_frame_index": frame["source_frame_index"], "source_pts_ticks": frame["source_pts_ticks"],
            "time_base": manifest["time_base"], "source_png": frame["png"],
            "inference_status": "withheld" if mean is None else "completed",
            "state": "withheld" if mean is None else "observed" if chosen else "missing",
            "withheld_reason": "segment_has_fewer_than_three_frames" if mean is None else None,
            "segment_kind": segment["kind"],
            "segment_source_frame_range_inclusive": segment.get("source_frame_range_inclusive"),
            "temporal_contributions": count,
            "mean_heatmap_sha256": None if mean is None else hashlib.sha256(mean.tobytes()).hexdigest(),
            "candidates": candidates, "selected_candidate_index": None if chosen is None else chosen["candidate_index"],
            "center_xy_px": None if chosen is None else [chosen["center_x"],chosen["center_y"]],
            "native_score": None if chosen is None else chosen["native_score"]}


def new_triplet(root, manifest, frames, identity, folder, images, get_adapter):
    first = frames[0]["source_frame_index"]
    cache, receipt = folder/f"triplet_{first:06d}.npz", folder/f"triplet_{first:06d}.json"
    if cache.exists():
        return d.load_triplet(root,cache,receipt,identity)
    d.require(not receipt.exists(), "Completed receipt without cache; investigate, never reinfer")
    for frame in frames:
        index = frame["source_frame_index"]
        if index not in images:
            raw = d.nba.read_verified_png(frame,manifest["source_video"],root)
            with Image.open(io.BytesIO(raw)) as image:
                images[index] = np.asarray(image).copy()
    for index in list(images):
        if index not in {f["source_frame_index"] for f in frames}: del images[index]
    adapter = get_adapter()
    attempt_id = uuid.uuid4().hex
    start = folder/"attempts"/f"{first:06d}_{attempt_id}_started.json"
    d.write_once(start,{"attempt_id":attempt_id,"started_at_utc":d.stamp(),"identity_sha256":canonical(identity),
                        "source_frame_indices":[f["source_frame_index"] for f in frames],"status":"started"})
    began = time.monotonic()
    try:
        prediction = adapter.predict_triplet([images[f["source_frame_index"]] for f in frames])
        values = prediction["heatmaps"]
        d.validate_heatmaps(values)
        metadata = {"status":"completed","attempt_id":attempt_id,"identity":identity,
                    "started_record":d.binding(root,start),"elapsed_seconds":time.monotonic()-began}
        temporary = cache.with_name(cache.name+"."+attempt_id+".partial")
        with temporary.open("xb") as handle:
            np.savez_compressed(handle,heatmaps=values,
                                metadata_json=np.array(json.dumps(metadata,sort_keys=True,allow_nan=False)))
            handle.flush(); os.fsync(handle.fileno())
        d.require(not cache.exists(), "Concurrent triplet completion")
        temporary.replace(cache)
        return d.load_triplet(root,cache,receipt,identity)
    except Exception as error:
        d.write_once(folder/"attempts"/f"{first:06d}_{attempt_id}_failed.json",
                     {"attempt_id":attempt_id,"status":"failed_preserved","elapsed_seconds":time.monotonic()-began,
                      "error_type":type(error).__name__,"error":str(error)})
        raise


def infer_action(root, manifest, segments, context, get_adapter):
    candidate = manifest["candidate_id"]
    output = context["output"]/candidate
    folder = output/"triplets"
    folder.mkdir(parents=True,exist_ok=True)
    reference = next(r for r in context["references"] if r["candidate_id"] == candidate)
    original = {f["source_frame_index"]: f for f in reference["frames"]}
    old_starts = set(sorted(original)[:-2])
    old_observations = context["old_observations"][candidate]
    old_caches = {Path(b["path"]).stem: b for b in old_observations["triplet_caches"]}
    images, records = {}, []
    code_identity = inference_identity()
    def provide(frames):
        first = frames[0]["source_frame_index"]
        if first in old_starts:
            d.require(frames == [original[i] for i in range(first,first+3)], "Old input context differs")
            identity = d.input_identity(reference,frames,context["config"],context["old_plan"])
            cache = d.bound(root,old_caches[f"triplet_{first:06d}"])
            receipt = cache.with_suffix(".json")
            d.require(receipt.is_file(), "Prior completed receipt missing; investigate")
            values, record = d.load_triplet(root,cache,receipt,identity)
            origin = "prior_pilot_import"
        else:
            identity = {"candidate_id":candidate,"game_id":manifest["game_id"],
                        "source_video":manifest["source_video"],"time_base":manifest["time_base"],"frames":frames,
                        "model_checkpoint":context["old_plan"]["checkpoint"],
                        "pretrained_checkpoint":context["config"]["pretrained_checkpoint"],
                        "policy":d.POLICY,"inference_code":code_identity,
                        "proposal":context["proposal_binding"]}
            values, record = new_triplet(root,manifest,frames,identity,folder,images,get_adapter)
            origin = "action_observation"
        records.append({"first_source_frame_index":first,"origin":origin,"cache":record["cache"],
                        "original_identity_sha256":canonical(record["identity"]),
                        "original_started_record":record["started_record"],"attempt_id":record["attempt_id"]})
        if len(records)%100 == 0: print(f"{candidate}: {len(records)} triplets available",flush=True)
        return values
    indexed = {f["source_frame_index"]: f for f in manifest["frames"]}
    observations = []
    for segment in segments:
        first,last = segment["source_frame_range_inclusive"]
        frames = [indexed[i] for i in range(first,last+1)]
        for frame,mean,count in stream_means(frames,provide):
            observations.append(select_observation(frame,mean,count,manifest,segment))
    imported = {r["first_source_frame_index"] for r in records if r["origin"] == "prior_pilot_import"}
    old_frames = {f["source_frame_index"]: f for f in old_observations["frames"]}
    same_context, changed_context = [], []
    old_first, old_last = min(original), max(original)
    fields = ("state", "temporal_contributions", "candidates", "selected_candidate_index", "center_xy_px", "native_score")
    for row in observations:
        index = row["source_frame_index"]
        if index not in old_frames:
            continue
        segment = next(s for s in segments if s["source_frame_range_inclusive"][0] <= index <= s["source_frame_range_inclusive"][1])
        first,last = segment["source_frame_range_inclusive"]
        same = old_first+2 <= index <= old_last-2 and first+2 <= index <= last-2
        if same:
            d.require(all(row[k] == old_frames[index][k] for k in fields),
                      f"Unchanged pilot context produced different observation: {index}")
            same_context.append(index)
        else:
            changed_context.append({"source_frame_index":index,
                "prior_center_xy_px":old_frames[index]["center_xy_px"],"new_center_xy_px":row["center_xy_px"],
                "prior_contributions":old_frames[index]["temporal_contributions"],
                "new_contributions":row["temporal_contributions"]})
    payload = {"schema_version":SCHEMA,"candidate_id":candidate,"game_id":manifest["game_id"],
               "approved_role":manifest["approved_role"],"input_manifest":d.binding(root,context["output"]/"inputs"/candidate/"manifest.json"),
               "proposal":context["proposal_binding"],"approval":context["approval"],
               "source_continuity_review":context["scene_binding"],"inference":d.POLICY,
               "inference_code":code_identity,"checkpoint":context["old_plan"]["checkpoint"],
               "model_output_human_review":"pending","annotations_present":False,
               "native_score_semantics":"sum of sigmoid heatmap values in strict >0.3 component; not probability",
               "frames":observations,"triplet_caches":records,
               "excluded_prior_triplet_starts":sorted(old_starts-imported),
               "pilot_context_comparison":{"unchanged_context_frames_verified_identical":same_context,
                   "changed_context_frames":changed_context,"original_score_recomputed":False}}
    d.write_once(output/"observations.json",payload)
    return payload


def summarize(manifest, observations):
    frames = observations["frames"]
    counts = Counter(f["state"] for f in frames)
    intervals = []
    for frame in frames:
        if not intervals or (intervals[-1]["state"],intervals[-1]["segment_kind"],intervals[-1]["segment_source_frame_range_inclusive"]) != (
                frame["state"],frame["segment_kind"],frame["segment_source_frame_range_inclusive"]):
            intervals.append({"state":frame["state"],"segment_kind":frame["segment_kind"],
                              "segment_source_frame_range_inclusive":frame["segment_source_frame_range_inclusive"],
                              "first_source_frame_index":frame["source_frame_index"],
                              "first_source_pts_ticks":frame["source_pts_ticks"],"frames":0})
        intervals[-1]["frames"] += 1
        intervals[-1]["last_source_frame_index"] = frame["source_frame_index"]
    for index,item in enumerate(intervals):
        end = intervals[index+1]["first_source_pts_ticks"] if index+1 < len(intervals) else manifest["source_end_exclusive_pts_ticks"]
        item["end_exclusive_pts_ticks"] = end
        item["duration_seconds"] = (end-item["first_source_pts_ticks"])/90000
    return {"frames":len(frames),**{k:counts[k] for k in ("observed","missing","withheld")},
            "semantics":"unlabeled availability, not accuracy","state_intervals":intervals,
            "imported_prior_triplets":sum(r["origin"]=="prior_pilot_import" for r in observations["triplet_caches"]),
            "action_triplets":sum(r["origin"]=="action_observation" for r in observations["triplet_caches"])}


def run(root, proposal_path, approval_path, scene_path=None, *, prepare_only=False, adapter_factory=None, render=True):
    root = Path(root).resolve()
    context = load_context(root,proposal_path,approval_path)
    output = context["output"]
    d.require(output.is_relative_to(root/"data/outputs"), "Output outside ignored data tree")
    output.mkdir(parents=True,exist_ok=True)
    lock = d.acquire_run_lock(output/".run.lock")
    began = time.monotonic()
    attempt = output/"run_attempts"/uuid.uuid4().hex
    adapter = None
    try:
        d.write_once(attempt/"started.json",{"at_utc":d.stamp(),"pid":os.getpid(),"prepare_only":prepare_only,
                     "proposal":context["proposal_binding"],"approval":context["approval"],
                     "code_sha256":d.digest(Path(__file__))})
        if prepare_only:
            from .nba_action_inputs import prepare_inputs
            manifests = prepare_inputs(root,context["proposal"],context["approval"],context["references"],
                                       output/"inputs",context["config"]["rendering"]["ffmpeg"])
        else:
            manifests = load_prepared(root,context)
        d.require([m["candidate_id"] for m in manifests] == [w["candidate_id"] for w in context["proposal"]["windows"]],
                  "Prepared candidate inventory differs")
        for manifest,window in zip(manifests,context["proposal"]["windows"]):
            reference = next(r for r in context["references"] if r["candidate_id"] == window["candidate_id"])
            validate_manifest(manifest,window,reference)
        if prepare_only:
            result = {"status":"inputs_prepared_continuity_review_pending","manifests":[
                d.binding(root,output/"inputs"/m["candidate_id"]/"manifest.json") for m in manifests],"model_calls":0}
        else:
            d.require(scene_path is not None, "Inference requires completed source continuity inspection")
            segments = load_scenes(root,scene_path,context,manifests)
            context["scene_binding"] = d.binding(root,scene_path)
            d.write_once(output/"run_identity.json",{"proposal":context["proposal_binding"],
                "approval":context["approval"],"inference_code":inference_identity(),
                "scene_review":context["scene_binding"],"checkpoint":context["old_plan"]["checkpoint"]})
            def get_adapter():
                nonlocal adapter
                if adapter is None:
                    if adapter_factory is not None: adapter = adapter_factory()
                    else:
                        from .wasb_adapted_adapter import AdaptedWasbAdapter
                        config,training = context["config"],context["training"]
                        adapter = AdaptedWasbAdapter(d.contained(root,config["upstream_source"]["path"]),
                            d.bound(root,config["pretrained_checkpoint"]),d.bound(root,training["checkpoint"]),
                            training["checkpoint"]["sha256"],training["training_provenance"],device="cuda")
                    d.write_once(attempt/"model_loaded.json",{"at_utc":d.stamp(),"python":sys.version,
                        "numpy":np.__version__,"provenance":getattr(adapter,"provenance",{"kind":"injected_test_adapter"})})
                return adapter
            packages = []
            for manifest in manifests:
                candidate = manifest["candidate_id"]
                observations = infer_action(root,manifest,segments[candidate],context,get_adapter)
                summary = summarize(manifest,observations)
                d.write_once(output/candidate/"summary.json",summary)
                review = None
                if render:
                    from .nba_action_review import render_action
                    review = render_action(root,manifest,observations,context["config"]["rendering"]["ffmpeg"],output/candidate)
                    review = {k:v for k,v in review.items() if k != "reused"}
                packages.append({"candidate_id":candidate,"game_id":manifest["game_id"],"summary":summary,
                    "observations":d.binding(root,output/candidate/"observations.json"),"review":review})
            page = None
            if render:
                from .nba_action_review import build_review_page
                page = build_review_page(root,packages,output)
            result = {"schema_version":SCHEMA,"status":"completed","proposal":context["proposal_binding"],
                      "approval":context["approval"],"source_continuity_review":context["scene_binding"],
                      "packages":packages,"review_page":page,"call_accounting":d.call_accounting(output),
                      "training":False,"accuracy_scoring":False,"model_output_human_review":"pending"}
            d.write_once(output/"completion.json",result)
        d.write_once(attempt/"completed.json",{"status":"completed","elapsed_seconds":time.monotonic()-began,
                     "result_status":result["status"],"call_accounting":d.call_accounting(output)})
        return result
    except Exception as error:
        d.write_once(attempt/"failed.json",{"status":"failed_preserved","error":str(error),
                    "error_type":type(error).__name__,"elapsed_seconds":time.monotonic()-began,
                    "call_accounting":d.call_accounting(output)})
        raise
    finally:
        d.release_run_lock(lock)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root",type=Path,default=Path.cwd())
    parser.add_argument("--proposal",type=Path,required=True)
    parser.add_argument("--approval",type=Path,required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare",action="store_true")
    mode.add_argument("--run",action="store_true")
    parser.add_argument("--scene-review",type=Path)
    args = parser.parse_args()
    root = args.repository_root.resolve()
    result = run(root,root/args.proposal,root/args.approval,
                 None if args.scene_review is None else root/args.scene_review,prepare_only=args.prepare)
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__ == "__main__":
    main()
