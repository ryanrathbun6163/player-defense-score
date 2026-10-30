"""One frozen DINOv2 crop/reference screen; no training or trajectory changes."""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
from importlib import metadata, util
import io
import json
import math
import os
from pathlib import Path
import time
import uuid

import numpy as np
from PIL import Image

from . import nba_wasb_diagnostic as d

SCHEMA = "nba_appearance_feature_screen/v0.1"
FEATURE_SCHEMA = "nba_appearance_feature/v0.1"
ROLES = {"reference_bank", "resolved_check", "unresolved_audit", "exposed_regression"}


def _path(root, value):
    path = (root / value).resolve()
    d.require(path.is_relative_to(root), "Path leaves repository")
    return path


def _read(root, binding):
    return d.read_json(d.bound(root, binding))


def _hash_array(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def crop_and_preprocess(image, saved_center):
    """Fixed floor-centered black-padded64 -> bicubic256 -> centered224 RGB."""
    center = np.asarray(saved_center, dtype=np.float64)
    d.require(center.shape == (2,) and np.isfinite(center).all(), "Invalid saved crop center")
    x, y = (math.floor(float(v)) - 32 for v in center)
    native = image.convert("RGB").crop((x, y, x + 64, y + 64))
    model_input = native.resize((256, 256), Image.Resampling.BICUBIC).crop((16, 16, 240, 240))
    pixels = np.asarray(model_input, dtype=np.float32) / np.float32(255)
    pixels = (pixels - np.asarray([.485, .456, .406], dtype=np.float32)) / np.asarray([.229, .224, .225], dtype=np.float32)
    return native, model_input, np.ascontiguousarray(pixels.transpose(2, 0, 1))


def extract_cls(output):
    """Accept only the final-normalized CLS exposed by Dinov2Model."""
    value = getattr(output, "pooler_output", None)
    d.require(value is not None, "Dinov2 pooler_output is required")
    if hasattr(value, "detach"):
        d.require(str(value.dtype) == "torch.float32", "CLS must be CPU float32")
        d.require(str(value.device) == "cpu", "CLS must be on CPU")
        value = value.detach().numpy()
    value = np.asarray(value)
    d.require(value.shape == (1, 384) and value.dtype == np.float32 and np.isfinite(value).all(),
              "Expected one finite float32 384-dimensional pooler_output")
    result = np.ascontiguousarray(value[0]).copy()
    normalize_feature(result)
    return result


def normalize_feature(feature):
    value = np.asarray(feature, dtype=np.float64)
    d.require(value.shape == (384,) and np.isfinite(value).all(), "Invalid 384-dimensional feature")
    norm = np.linalg.norm(value)
    d.require(np.isfinite(norm) and norm > 0, "Feature norm must be finite and nonzero")
    return np.ascontiguousarray(value / norm)


def validate_registry(root, registry, proposal, accepted):
    """Join the exact existing JSON authorities without opening source pixels."""
    d.require(registry["schema_version"] == "nba_appearance_feature_screen_scope/v0.1"
              and registry["status"] == "proposed_not_approved"
              and registry["accepted_reference"] == proposal["accepted_reference"]
              and registry["totals"] == proposal["totals"]
              and accepted["status"] == "human_accepted_assisted_reference", "Registry authority differs")
    regression = _read(root, registry["regression_preparation"])
    selection = _read(root, registry["saved_selection"])
    prior = _read(root, registry["prior_ai_assessment"])
    key = lambda row: (row["continuous_source_id"], row["source_frame_index"])
    candidates = {r["candidate_key"]: r for r in accepted["candidates"]}
    labels = {r["candidate_key"]: r for r in accepted["rows"]}
    af = {key(r): r for r in accepted["frames"]}; rf = {key(r): r for r in regression["frames"]}
    decisions = {(r["candidate_id"], r["source_frame_index"]): r for r in selection["frames"]}
    judgments = {key(r): r for r in prior["rows"]}
    sources = {r["candidate_id"]: r["source_video"] for r in accepted["sources"] + regression["sources"]}
    items = registry["items"]; ids = [r["case_id"] for r in items]
    totals = registry["totals"]; roles = Counter(r["screen_role"] for r in items)
    d.require(len(ids) == len(set(ids)) == totals["crop_inputs"] == 60
              and set(roles) == ROLES and all(roles[k] == totals[k] for k in ROLES)
              and len({key(r) for r in items}) == totals["unique_cached_source_frames"] == 49,
              "Fixed60 case census or49 source-frame census differs")
    for item in items:
        pair = key(item); role = item["screen_role"]
        x, y = item["saved_center_xy_px"]
        d.require(math.isfinite(x) and math.isfinite(y)
                  and item["native_crop_box_xyxy_exclusive"] == [math.floor(x)-32, math.floor(y)-32, math.floor(x)+32, math.floor(y)+32]
                  and item["source_video"] == sources[pair[0]], "Saved crop/source identity differs")
        if role == "exposed_regression":
            decision = decisions[pair]; frame = rf[pair]
            d.require(item["saved_center_xy_px"] == decision["selected_center_xy_px"]
                      and item["saved_provenance_id"] == decision["selected_provenance_id"]
                      and item["saved_decision"] == decision["decision"]
                      and item["prior_ai_assessment"] == judgments[pair]
                      and item["semantic_label_status"] == "prior_ai_assessment_not_new_human_appearance_acceptance"
                      and "accepted_appearance" not in item, "Prior selected point or qualitative judgment differs")
        else:
            candidate = candidates[item["candidate_key"]]; label = labels[item["candidate_key"]]; frame = af[pair]
            expected_role = "unresolved_audit" if label["classification"] == "unresolved" else (
                "reference_bank" if candidate["role"] == "fit_eligible" else "resolved_check")
            d.require(item["saved_center_xy_px"] == candidate["center_xy_px"]
                      and item["saved_provenance_id"] == candidate["provenance_id"]
                      and item["accepted_appearance"] == label and item["original_source_role"] == candidate["role"]
                      and role == expected_role
                      and item["semantic_label_status"] == "human_accepted_assisted_appearance",
                      "Accepted candidate, label or source role differs")
            if role == "reference_bank":
                d.require(pair[0] == "sac_mem_q1_c01", "Only resolved SAC records enter the bank")
        d.require(item["raw_png"] == frame["raw_png"] and item["source_pts_ticks"] == frame["source_pts_ticks"],
                  "Cached source image or native clock differs")
    d.require({r["candidate_key"] for r in items if r["screen_role"] != "exposed_regression"} == set(candidates)
              and {key(r) for r in items if r["screen_role"] == "exposed_regression"} == set(judgments),
              "Accepted/prior case census differs")
    for role, field in (("reference_bank", "reference_bank_case_ids"), ("resolved_check", "resolved_check_case_ids")):
        d.require([r["case_id"] for r in items if r["screen_role"] == role] == proposal[field], "Frozen role order differs")
    return copy.deepcopy(items)


def _runtime():
    versions = {name: metadata.version(name) for name in ("torch", "transformers", "safetensors", "numpy", "Pillow")}
    location = Path(util.find_spec("transformers").origin).parent / "models/dinov2/modeling_dinov2.py"
    return {"versions": versions, "modeling_dinov2": {"path": str(location), "sha256": d.digest(location),
            "bytes": location.stat().st_size}, "device": "cpu", "dtype": "float32", "batch_size": 1,
            "torch_threads": 4, "attention": "eager", "eval": True, "inference_mode": True}


def load_inputs(root, approval_path, weights_path):
    """Verify protocol and all49 encoded PNG byte identities before inference."""
    root = Path(root).resolve(); approval_path = _path(root, approval_path); weights_path = _path(root, weights_path)
    approval = d.read_json(approval_path)
    d.require(approval["schema_version"] == "nba_appearance_feature_screen_approval/v0.1"
              and approval["status"] == "approved" and approval["execution_approved"] is True
              and isinstance(approval["user_statement"], str) and approval["user_statement"].strip(),
              "Explicit feature-screen execution approval required")
    proposal = _read(root, approval["proposal"])
    d.require(proposal["schema_version"] == "nba_appearance_feature_screen_proposal/v0.1"
              and all(approval[k] == proposal[k] for k in ("plan", "case_registry", "accepted_reference")),
              "Approved frozen proposal bindings differ")
    d.bound(root, proposal["plan"])
    accepted = _read(root, proposal["accepted_reference"])
    registry = _read(root, proposal["case_registry"])
    items = validate_registry(root, registry, proposal, accepted)
    encoder = proposal["encoder"]
    weights = d.binding(root, weights_path)
    d.require(weights["sha256"] == encoder["expected_sha256"] and weights["bytes"] == encoder["expected_bytes"],
              "Pinned local weight bytes differ")
    config = _read(root, encoder["config_metadata"]); processor = _read(root, encoder["processor_metadata"])
    d.require(config["model_type"] == "dinov2" and config["hidden_size"] == 384 and config["patch_size"] == 14
              and config["num_hidden_layers"] == 12 and config["num_attention_heads"] == 6
              and processor["image_mean"] == [.485, .456, .406] and processor["image_std"] == [.229, .224, .225]
              and processor["size"] == {"shortest_edge": 256} and processor["crop_size"] == {"height": 224, "width": 224}
              and processor["resample"] == 3 and processor["rescale_factor"] == 1/255,
              "Frozen model or processor contract differs")
    pngs = {}
    for item in items:
        png = item["raw_png"]
        d.require(png["path"] not in pngs or pngs[png["path"]] == png, "Conflicting source PNG binding")
        pngs[png["path"]] = png
    d.require(len(pngs) == 49, "Expected49 distinct cached source PNGs")
    for png in pngs.values():
        d.bound(root, png)
    protocol = {"schema_version": SCHEMA, "approval": d.binding(root, approval_path),
        "proposal": approval["proposal"], "case_registry": proposal["case_registry"],
        "accepted_reference": proposal["accepted_reference"], "weights": weights,
        "config": encoder["config_metadata"], "processor": encoder["processor_metadata"],
        "implementation": [d.binding(root, root / "src/ball_tracking" / name) for name in
                           ("nba_appearance_feature_screen.py", "nba_wasb_diagnostic.py")],
        "runtime": _runtime(), "source_pngs": list(pngs.values()), "totals": registry["totals"],
        "output_root": approval["output_root"], "input": proposal["input"], "execution": proposal["execution"],
        "decision": proposal["decision"], "encoder_repository": encoder["repository"], "encoder_revision": encoder["revision"]}
    return protocol, items


def load_model(config_path, weights_path):
    import torch
    from safetensors.torch import load_file
    from transformers import Dinov2Config, Dinov2Model
    torch.set_num_threads(4)
    config = Dinov2Config.from_json_file(str(config_path))
    config._attn_implementation = "eager"
    model = Dinov2Model(config)
    model.load_state_dict(load_file(str(weights_path), device="cpu"), strict=True)
    model.to(device="cpu", dtype=torch.float32)
    model.eval()
    d.require(not model.training and model.config._attn_implementation == "eager", "Model execution mode differs")
    return model


def encode(model, chw):
    import torch
    d.require(chw.shape == (3, 224, 224) and chw.dtype == np.float32, "Model input must be float32 CHW224")
    with torch.inference_mode():
        return extract_cls(model(pixel_values=torch.from_numpy(chw).unsqueeze(0), return_dict=True))


def retrieve(features, items):
    """Fixed float64 cosine class maxima; unknowns and exposed judgments stay separate."""
    ids = [r["case_id"] for r in items]
    d.require(len(ids) == len(set(ids)) and set(features) == set(ids), "Feature/case census differs")
    unit = {key: normalize_feature(value) for key, value in features.items()}
    bank = [r for r in items if r["screen_role"] == "reference_bank"]
    classes = {"ball", "other_object"}
    d.require({r["accepted_appearance"]["classification"] for r in bank} == classes,
              "Bank must contain only resolved ball and other-object references")
    rows = []
    for item in items:
        if item["screen_role"] == "reference_bank":
            continue
        similarities = [{"reference_case_id": ref["case_id"], "classification": ref["accepted_appearance"]["classification"],
                         "cosine_similarity": float(np.dot(unit[item["case_id"]], unit[ref["case_id"]]))} for ref in bank]
        maxima = {cls: max(r["cosine_similarity"] for r in similarities if r["classification"] == cls) for cls in classes}
        margin = maxima["ball"] - maxima["other_object"]
        preference = "ball_preferred" if margin > 0 else "other_preferred" if margin < 0 else "abstain_tie"
        outcome = None; disagreement = None; qualitative_tie = None
        if item["screen_role"] == "resolved_check":
            expected = "ball_preferred" if item["accepted_appearance"]["classification"] == "ball" else "other_preferred"
            outcome = "tie" if margin == 0 else "correct" if preference == expected else "incorrect"
        if item["screen_role"] == "exposed_regression":
            assessment = item["prior_ai_assessment"]["assessment"]
            qualitative_tie = margin == 0
            if assessment in classes:
                expected = "ball_preferred" if assessment == "ball" else "other_preferred"
                disagreement = preference != expected
        rows.append({**copy.deepcopy(item), "similarities": similarities, "s_ball": maxima["ball"],
            "s_other": maxima["other_object"], "margin": margin, "preference": preference,
            "nearest_ball_case_ids": [r["reference_case_id"] for r in similarities if r["classification"] == "ball" and r["cosine_similarity"] == maxima["ball"]],
            "nearest_other_case_ids": [r["reference_case_id"] for r in similarities if r["classification"] == "other_object" and r["cosine_similarity"] == maxima["other_object"]],
            "accepted_check_outcome": outcome, "qualitative_disagreement": disagreement, "qualitative_tie": qualitative_tie})
    checks = [r for r in rows if r["screen_role"] == "resolved_check"]
    by_class = {cls: dict(Counter(r["accepted_check_outcome"] for r in checks if r["accepted_appearance"]["classification"] == cls)) for cls in sorted(classes)}
    outcomes = Counter(r["accepted_check_outcome"] for r in checks)
    main = len(checks) == 10 and by_class["ball"] == {"correct": 6} and by_class["other_object"] == {"correct": 4}
    old = [r for r in rows if r["screen_role"] == "exposed_regression"]
    challenges = {}
    for name, cid, indices, desired in (("sac_wrong_head", "sac_mem_q1_c01", [1419, 1420, 1421], "other_preferred"),
                                       ("det_near_head_ball", "sas_det_q1_c02", [11722, 11723, 11724, 11725], "ball_preferred")):
        selected = [r for r in old if r["continuous_source_id"] == cid and r["source_frame_index"] in indices]
        missing = [i for i in indices if i not in {r["source_frame_index"] for r in selected}]
        adverse = [r["case_id"] for r in selected if r["preference"] != desired]
        challenges[name] = {"expected_source_frames": indices, "case_ids": [r["case_id"] for r in selected],
            "missing_source_frames": missing, "adverse_case_ids": adverse, "flagged": bool(missing or adverse),
            "qualitative_previously_exposed": True, "episodes": 1}
    summary = {"query_count": len(rows), "similarity_count": sum(len(r["similarities"]) for r in rows),
        "accepted_checks": {"total": len(checks), "correct": outcomes["correct"], "incorrect": outcomes["incorrect"],
                            "ties": outcomes["tie"], "by_class": by_class},
        "main_gate": {"passed": main, "required_balls": 6, "required_other_objects": 4},
        "unknowns_unscored": sum(r["screen_role"] == "unresolved_audit" for r in rows),
        "qualitative_regression": {"total": len(old), "disagreements": sum(r["qualitative_disagreement"] is True for r in old),
            "ties": sum(r["qualitative_tie"] is True for r in old),
            "unresolved_unscored": sum(r["prior_ai_assessment"]["assessment"] == "unresolved" for r in old),
            "provenance_populations": dict(Counter(r["saved_provenance_id"][3] for r in old))},
        "challenges": challenges, "clean_screen": main and not any(c["flagged"] for c in challenges.values())}
    return {"schema_version": SCHEMA, "reference_bank_case_ids": [r["case_id"] for r in bank],
        "queries": rows, "summary": summary, "limits": {"unseen_validation": False, "probabilities": False,
            "unknowns_scored": False, "prior_ai_judgments_newly_accepted": False, "automatic_policy_adoption": False,
            "candidate_populations": "Mean-component bank; mixed mean/contributor exposed regression supplement",
            "coverage": "Small correlated SAC bank; no resolved NFHS bank or excluded head/clothing negatives; no independent head-error episode"}}


def _png(root, path, image):
    buffer = io.BytesIO(); image.save(buffer, format="PNG"); raw = buffer.getvalue()
    if path.exists():
        d.require(path.read_bytes() == raw, "Existing crop/input PNG differs")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".partial")
        with temporary.open("xb") as handle:
            handle.write(raw); handle.flush(); os.fsync(handle.fileno())
        d.require(not path.exists(), "Concurrent crop creation")
        temporary.replace(path)
    return {**d.binding(root, path), "rgb_sha256": hashlib.sha256(image.tobytes()).hexdigest()}


def _cached(root, path, protocol, item, index):
    row = d.read_json(path)
    d.require(row["schema_version"] == FEATURE_SCHEMA and row["protocol"] == protocol
              and row["case_index"] == index and row["case"] == item, "Cached feature identity differs")
    raw = np.asarray(row["raw_cls_float32"], dtype=np.float32)
    d.require(raw.shape == (384,) and raw.tolist() == row["raw_cls_float32"]
              and _hash_array(raw) == row["raw_cls_sha256"]
              and _hash_array(normalize_feature(raw)) == row["normalized_float64_sha256"], "Cached descriptor differs")
    for name in ("crop64", "input224"):
        d.bound(root, row[name])
    return row, raw


def _source_image(root, item, resources, cache):
    png = item["raw_png"]
    if cache.get("binding") != png:
        raw = d.bound(root, png).read_bytes()
        d.require(hashlib.sha256(raw).hexdigest() == png["sha256"], "Source changed during read")
        with Image.open(io.BytesIO(raw)) as opened:
            d.require(opened.format == "PNG" and opened.mode == "RGB", "Source must be native RGB PNG")
            image = opened.copy()
        d.require(image.size == (item["source_video"]["width_px"], item["source_video"]["height_px"])
                  and hashlib.sha256(image.tobytes()).hexdigest() == png["rgb_sha256"], "Source RGB or dimensions differ")
        resources["source_png_decodes"] += 1
        cache.update(binding=png, image=image)
    return cache["image"]


def run(root, approval_path, output_dir, weights_path):
    """Encode missing fixed cases once, resume exact cached features, and report every gate."""
    root = Path(root).resolve(); output = _path(root, output_dir)
    d.require(output.is_relative_to(root / "data/outputs"), "Screen artifacts must remain ignored")
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".run.lock"
    with lock.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps({"pid": os.getpid(), "created_at_utc": d.stamp()}))
    attempt = output / "attempts" / uuid.uuid4().hex
    resources = {"model_load_attempts": 0, "model_loads": 0, "model_calls": 0, "source_png_decodes": 0, "source_video_decodes": 0,
                 "candidate_array_reads": 0, "training_updates": 0, "cached_features_reused": 0}
    started = time.monotonic()
    try:
        d.write_once(attempt / "started.json", {"created_at_utc": d.stamp(), "approval": d.binding(root, _path(root, approval_path))})
        protocol, items = load_inputs(root, approval_path, weights_path)
        d.require(output == _path(root, protocol["output_root"]), "Approved output directory differs")
        d.write_once(output / "protocol.json", protocol)
        binding = d.binding(root, output / "protocol.json")
        resources["source_pngs_byte_verified_before_inference"] = len(protocol["source_pngs"])
        model = None; features = {}; records = []; image_cache = {}
        for index, item in enumerate(items):
            feature_path = output / "features" / f"case_{index:03d}.json"
            if feature_path.exists():
                row, raw = _cached(root, feature_path, binding, item, index)
                resources["cached_features_reused"] += 1
            else:
                image = _source_image(root, item, resources, image_cache)
                crop, model_input, chw = crop_and_preprocess(image, item["saved_center_xy_px"])
                crop_binding = _png(root, feature_path.with_name(f"case_{index:03d}_crop64.png"), crop)
                input_binding = _png(root, feature_path.with_name(f"case_{index:03d}_input224.png"), model_input)
                if model is None:
                    resources["model_load_attempts"] += 1
                    model = load_model(d.bound(root, protocol["config"]), d.bound(root, protocol["weights"]))
                    resources["model_loads"] += 1
                resources["model_calls"] += 1
                raw = encode(model, chw)
                d.require(isinstance(raw, np.ndarray) and raw.shape == (384,) and raw.dtype == np.float32,
                          "Encoder must return one raw384 float32 descriptor")
                unit = normalize_feature(raw)
                row = {"schema_version": FEATURE_SCHEMA, "protocol": binding, "case_index": index,
                    "case": copy.deepcopy(item), "crop64": crop_binding, "input224": input_binding,
                    "input_chw_float32_sha256": _hash_array(chw), "raw_cls_float32": raw.tolist(),
                    "raw_cls_sha256": _hash_array(raw), "normalized_float64_sha256": _hash_array(unit)}
                d.write_once(feature_path, row)
            features[item["case_id"]] = raw
            records.append({"case_id": item["case_id"], "feature": d.binding(root, feature_path),
                            "crop64": row["crop64"], "input224": row["input224"]})
        report = retrieve(features, items)
        report.update(protocol=binding, features=records)
        d.write_once(output / "report.json", report)
        completion_path = output / "completion.json"
        if completion_path.exists():
            completion = d.read_json(completion_path)
            d.require(completion["status"] == "completed" and completion["protocol"] == binding
                      and completion["features"] == records and completion["report"] == d.binding(root, output / "report.json"),
                      "Existing completed screen differs")
            d.write_once(attempt / "completed.json", {"status": "resumed_verified", "completion": d.binding(root, completion_path),
                "resources": resources, "elapsed_seconds": time.monotonic() - started})
            return completion
        completion = {"status": "completed", "protocol": binding, "features": records,
            "report": d.binding(root, output / "report.json"), "summary": report["summary"], "resources": resources,
            "attempt": attempt.relative_to(root).as_posix(), "elapsed_seconds": time.monotonic() - started,
            "completed_at_utc": d.stamp(), "saved_encodings": len(records), "retrieval_review_status": "pending",
            "label_or_trajectory_changes": False}
        d.write_once(attempt / "completed.json", completion)
        d.write_once(completion_path, completion)
        return completion
    except BaseException as error:
        d.write_once(attempt / "failed.json", {"status": "failed_preserved", "error_type": type(error).__name__,
            "error": str(error), "resources": resources, "elapsed_seconds": time.monotonic() - started})
        raise
    finally:
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval", required=True); parser.add_argument("--output", required=True)
    parser.add_argument("--weights", required=True)
    args = parser.parse_args(); root = Path(__file__).resolve().parents[2]
    result = run(root, args.approval, args.output, args.weights)
    print(json.dumps({"status": result["status"], "report": result["report"], "summary": result["summary"], "resources": result["resources"]}))


if __name__ == "__main__":
    main()
