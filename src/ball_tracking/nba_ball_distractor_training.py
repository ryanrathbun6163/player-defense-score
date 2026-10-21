"""One provisional frozen-recipe fit, with immutable features and failure receipts."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time
import traceback
import uuid

import numpy as np

from . import nba_appearance_feature_screen as screen
from . import nba_ball_distractor_classifier as classifier
from . import nba_ball_distractor_reference_labels as labels
from . import nba_wasb_diagnostic as d

MODEL = "data/outputs/ball_tracking/nba/appearance_feature_screen_v0_1/model/model.safetensors"
CONFIG = "data/outputs/ball_tracking/nba/appearance_reference_v0_1/design_sources/config.json"
MODEL_SHA = "ae1e99fcefd534ed978cdeb8326f08030c96e28b7a81ffcbc98a857c84d14be1"
CONFIG_SHA = "1809f83e3bdb1609a501a610ad4a742f4fd8ae44d72ca4aa0df52d1f2ac8628d"


def crop_key(cid, index, center):
    return (cid, index, math.floor(center[0])-32, math.floor(center[1])-32)


def validate_raw(record):
    raw = np.asarray(record["raw_cls_float32"], dtype=np.float32)
    d.require(raw.shape == (384,) and raw.tolist() == record["raw_cls_float32"]
              and screen._hash_array(raw) == record["raw_cls_sha256"]
              and screen._hash_array(screen.normalize_feature(raw)) == record["normalized_float64_sha256"],
              "Saved raw feature or normalization differs")
    return raw


def old_cache(root, completion_binding):
    completion = d.read_json(d.bound(root, completion_binding))
    protocol = d.read_json(d.bound(root, completion["protocol"]))
    d.require(protocol["weights"]["sha256"] == MODEL_SHA and protocol["config"]["sha256"] == CONFIG_SHA,
              "Reused feature backbone differs")
    d.bound(root, protocol["weights"]); d.bound(root, protocol["config"])
    # Reuse only an identical extraction implementation and runtime, not a lookalike descriptor.
    for binding in protocol["implementation"]:
        d.bound(root, binding)
    d.require(protocol["runtime"] == screen._runtime(), "Reused feature runtime differs")
    cache, cases = {}, []
    registry = d.read_json(d.bound(root, protocol["case_registry"]))
    d.require(len(completion["features"]) == len(registry["items"]) == 60, "Old60 census differs")
    for index, (entry, item) in enumerate(zip(completion["features"], registry["items"], strict=True)):
        row, raw = screen._cached(root, d.bound(root, entry["feature"]), completion["protocol"], item, index)
        d.require(entry["case_id"] == item["case_id"] and entry["crop64"] == row["crop64"]
                  and entry["input224"] == row["input224"], "Old feature/case transport differs")
        key = crop_key(item["continuous_source_id"], item["source_frame_index"], item["saved_center_xy_px"])
        value = {"raw_cls_float32": raw.tolist(), "feature": entry["feature"],
                 "source_pts_ticks": item["source_pts_ticks"], "source_rgb_sha256": item["raw_png"]["rgb_sha256"],
                 "source_video": item["source_video"], "crop64": row["crop64"], "input224": row["input224"]}
        if key in cache:
            d.require(cache[key]["raw_cls_float32"] == value["raw_cls_float32"], "Conflicting old native crop features")
        else:
            cache[key] = value
        cases.append({"case": item, "feature": entry["feature"], "crop_key": list(key)})
    return cache, cases


def reference_summary(rows, scores):
    report = []
    for role in ("fit", "check"):
        for cls in ("ball", "other_object", "unresolved"):
            selected = [r for r in rows if r["role"] == role and r["classification"] == cls and r["row_id"] in scores]
            desired = "ball_supported" if cls == "ball" else "other_supported"
            report.append({"role": role, "classification": cls, "rows": len(selected),
                           "correct": None if cls == "unresolved" else sum(classifier.decision(scores[r["row_id"]]) == desired for r in selected),
                           "ties": sum(scores[r["row_id"]] == 0 for r in selected)})
    return report


def run(root, approval_path):
    root = Path(root).resolve(); approval_path = screen._path(root, approval_path)
    approval = d.read_json(approval_path)
    d.require(approval["schema_version"] == "nba_ball_distractor_execution_amendment/v0.1"
              and approval["status"] == "explicit_training_request_interpreted_for_provisional_experiment"
              and approval["human_new_label_acceptance"] == "pending", "Provisional execution authority differs")
    for binding in approval["bindings"].values():
        d.bound(root, binding)
    output = screen._path(root, approval["output_root"])
    d.require(output.is_relative_to(root / "data/outputs"), "Artifacts must remain ignored")
    output.mkdir(parents=True, exist_ok=True)
    d.require(not (output / "fit.json").exists() and not (output / "fit_started.json").exists(),
              "A fit has already been attempted; never refit this experiment")
    lock = output / ".run.lock"
    with lock.open("x", encoding="utf-8") as handle:
        json.dump({"pid": os.getpid(), "created_at_utc": d.stamp()}, handle)
    attempt = output / "attempts" / uuid.uuid4().hex
    resources = {"model_load_attempts": 0, "model_loads": 0, "model_calls": 0, "source_png_decodes": 0,
                 "source_video_decodes": 0, "cached_features_reused": 0, "optimizer_calls": 0}
    start = time.monotonic()
    try:
        d.write_once(attempt / "started.json", {"approval": d.binding(root, approval_path), "created_at_utc": d.stamp()})
        prep, proposed = labels.load_proposal(root, d.bound(root, approval["bindings"]["proposed_labels"]))
        rows = classifier.reference_rows(prep, proposed)
        weights = classifier.build_weights(rows)
        d.require(len(weights["samples"]) == approval["training_crops"] and len(weights["groups"]) == approval["training_groups"], "Training census differs")
        d.write_once(output / "training_weights.json", weights)
        d.write_once(output / "reference_rows.json", {"rows": rows, "human_new_label_acceptance": "pending"})
        cache, cases = old_cache(root, approval["bindings"]["old_feature_completion"])
        model_binding, config_binding = d.binding(root, root/MODEL), d.binding(root, root/CONFIG)
        d.require(model_binding["sha256"] == MODEL_SHA and config_binding["sha256"] == CONFIG_SHA, "Frozen encoder differs")
        protocol = {"schema_version": "nba_ball_distractor_training_protocol/v0.1", "approval": d.binding(root, approval_path),
                    "proposed_labels": approval["bindings"]["proposed_labels"], "weights": d.binding(root, output/"training_weights.json"),
                    "model": model_binding, "config": config_binding, "runtime": screen._runtime(),
                    "implementation": [d.binding(root, root/"src/ball_tracking"/name) for name in
                        ("nba_ball_distractor_training.py", "nba_ball_distractor_classifier.py", "nba_appearance_feature_screen.py")],
                    "labels": "AI proposals, human acceptance pending; old26 accepted classes unchanged",
                    "adoption": "not authorized by a provisional fit"}
        d.write_once(output / "protocol.json", protocol); binding = d.binding(root, output / "protocol.json")
        frames = {(f["continuous_source_id"],f["source_frame_index"]):f for f in prep["frames"]}
        sources = {s["candidate_id"]:s["source_video"] for s in prep["sources"]}
        old_by_key = {c["case"].get("candidate_key"):c for c in cases if "candidate_key" in c["case"]}
        features, records, model, image_cache = {}, [], None, {}
        for index, row in enumerate(rows):
            if row["center_xy_px"] is None:
                continue
            rid = row["row_id"]; cid = row["continuous_source_id"]; native_index = row["source_frame_index"]
            key = crop_key(cid,native_index,row["center_xy_px"])
            if row["origin"] == "existing_accepted_reference":
                item = old_by_key[rid]["case"]
                d.require(item["saved_center_xy_px"] == row["center_xy_px"]
                          and item["accepted_appearance"]["classification"] == row["classification"], "Old accepted row changed")
                frame = {"source_pts_ticks":item["source_pts_ticks"], "raw_png":item["raw_png"]}
            else:
                frame = frames[(cid,native_index)]
            path = output / "features" / f"reference_{index:03d}.json"
            if key not in cache and path.exists():
                saved = d.read_json(path); raw = validate_raw(saved)
                d.require(saved["protocol"] == binding and saved["crop_key"] == list(key)
                          and saved["center_xy_px"] == row["center_xy_px"]
                          and saved["source_video"] == sources[cid]
                          and saved["source_png"] == frame["raw_png"], "Resumed feature identity differs")
                for field in ("crop64","input224"):
                    d.bound(root,saved[field])
                cache[key] = {k:saved[k] for k in ("raw_cls_float32","source_pts_ticks","source_rgb_sha256","source_video","crop64","input224")}
                cache[key]["feature"] = d.binding(root,path)
            if key in cache:
                value = cache[key]
                d.require(value["source_pts_ticks"] == frame["source_pts_ticks"]
                          and value["source_rgb_sha256"] == frame["raw_png"]["rgb_sha256"]
                          and value["source_video"]["sha256"] == sources[cid]["sha256"], "Cached feature source identity differs")
                resources["cached_features_reused"] += 1
            else:
                image = screen._source_image(root,{"raw_png":frame["raw_png"],"source_video":sources[cid]},resources,image_cache)
                crop, model_input, chw = screen.crop_and_preprocess(image,row["center_xy_px"])
                crop_binding = screen._png(root,path.with_name(path.stem+"_crop64.png"),crop)
                input_binding = screen._png(root,path.with_name(path.stem+"_input224.png"),model_input)
                if model is None:
                    resources["model_load_attempts"] += 1
                    model = screen.load_model(root/CONFIG,root/MODEL); resources["model_loads"] += 1
                resources["model_calls"] += 1
                raw = screen.encode(model,chw)
                saved = {"schema_version":"nba_ball_distractor_feature/v0.1","protocol":binding,
                         "source_id":cid,"source_frame_index":native_index,"source_pts_ticks":frame["source_pts_ticks"],
                         "source_video":sources[cid],"source_png":frame["raw_png"],
                         "source_rgb_sha256":frame["raw_png"]["rgb_sha256"],"center_xy_px":row["center_xy_px"],"crop_key":list(key),
                         "crop64":crop_binding,"input224":input_binding,"input_chw_float32_sha256":screen._hash_array(chw),
                         "raw_cls_float32":raw.tolist(),"raw_cls_sha256":screen._hash_array(raw),
                         "normalized_float64_sha256":screen._hash_array(screen.normalize_feature(raw))}
                d.write_once(path,saved)
                value = {k:saved[k] for k in ("raw_cls_float32","source_pts_ticks","source_rgb_sha256","source_video","crop64","input224")}
                value["feature"] = d.binding(root,path); cache[key] = value
            features[rid] = value["raw_cls_float32"]
            records.append({"row_id":rid,"crop_key":list(key),"feature":value["feature"]})
            if len(records)%25 == 0:
                print(json.dumps({"stage":"reference_features","completed":len(records),"model_calls":resources["model_calls"],"elapsed_seconds":time.monotonic()-start}),flush=True)
        d.write_once(output/"feature_manifest.json",{"reference_features":records,"old_cases":cases,
                     "cache":[{"crop_key":list(k),**v} for k,v in cache.items()]})
        d.write_once(output/"fit_started.json",{"created_at_utc":d.stamp(),"protocol":binding,
                     "features":d.binding(root,output/"feature_manifest.json"),"optimizer_attempt_limit":1})
        fitted = classifier.fit(features,weights); resources["optimizer_calls"] = fitted["optimizer_calls"]
        d.write_once(output/"fit.json",fitted)
        result = {"status":fitted["status"],"fit":d.binding(root,output/"fit.json"),"protocol":binding,
                  "resources":resources,"elapsed_seconds":time.monotonic()-start,"completed_at_utc":d.stamp(),
                  "human_new_label_acceptance":"pending","adoption":"not_accepted"}
        if fitted["status"] == "converged_fit":
            scores = classifier.score(features,fitted)
            old_scores = [{**c,"logit":classifier.score_feature(fitted["parameters"],cache[tuple(c["crop_key"])]["raw_cls_float32"])} for c in cases]
            report = {"reference_scores":scores,"row_summary":reference_summary(rows,scores),"old_case_scores":old_scores,
                      "human_new_label_acceptance":"pending","original_coverage_requirements_passed":False}
            d.write_once(output/"reference_score_report.json",report)
            result.update(reference_report=d.binding(root,output/"reference_score_report.json"),row_summary=report["row_summary"])
        d.write_once(output/"completion.json",result)
        print(json.dumps(result),flush=True)
        return result
    except Exception as error:
        d.write_once(attempt/"failure.json",{"error_type":type(error).__name__,"error":str(error),"traceback":traceback.format_exc(),
                     "resources":resources,"elapsed_seconds":time.monotonic()-start,"recorded_at_utc":d.stamp()})
        raise
    finally:
        lock.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--approval",required=True)
    args = parser.parse_args(); run(Path(__file__).resolve().parents[2],args.approval)
