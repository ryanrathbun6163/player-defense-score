"""Approved YOLO inference on bound unmarked PNGs, with immutable crop retries."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .annotations import SourceVideo
from .crop_motion_factorial import RankingConfig as ControlConfig
from .development_experiments import bound_file, canonical_sha256, closed, read_json, require_digest, safe_path, sha256_file
from .temporal_experiment import _tracked, clean_commit, file_binding, git, persist_once, spec_digest
from .tiled_candidates import crop_views
from .yolo_crop_candidates import (ARMS, SCHEMA, SelectorConfig, candidate_run, experiment_grid,
                                   make_frame, make_output, select_candidates, validate_observations, validate_output)

EXPERIMENT_ID = "yolo11x_crop_development_comparison_v0_1"
OUTPUT_ROOT = "data/outputs/ball_tracking/detector_challenger/" + EXPERIMENT_ID
PRIOR_COMMIT = "2274ab6097cd841421e2b606f723b047cd7dc62b"
EXPECTED_PROPOSAL_SHA = "f891c04464422428dadbcfdf425436d3347464dbcab6d96ae23cac963dca5492"
FIELDS = {"schema_version", "experiment_id", "proposal", "authorization", "runtime", "output_root",
          "selected_operating_point", "quality_gate"}
APPROVED_WINDOWS = [("possession_001", 50, 74), ("possession_001", 200, 224),
                    ("possession_002", 250, 274), ("possession_002", 25, 49),
                    ("possession_003", 300, 324), ("possession_003", 150, 174)]
SEALED = [["possession_001", 300, 324], ["possession_002", 200, 224], ["possession_003", 250, 274]]
ENVELOPE_FIELDS = {"experiment_spec_sha256", "input_candidates", "candidate_content_sha256",
                   "observations_content_sha256", "observations"}


def bound_source_png(root, value):
    record = closed(value, {"path", "sha256"}, "source PNG binding")
    require_digest(record["sha256"], "source PNG")
    path = safe_path(Path(root), record["path"], "data/outputs/ball_tracking")
    if path.suffix != ".png" or not path.is_file() or sha256_file(path) != record["sha256"]:
        raise ValueError("Source PNG binding mismatch")
    return path


def load_manifest(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    safe_path(root, path.relative_to(root).as_posix(), "configs/ball_tracking/yolo_crop_experiments")
    m = closed(read_json(path), FIELDS, "YOLO experiment manifest")
    if (m["schema_version"] != "ball_yolo_crop_experiment/v0.1" or m["experiment_id"] != EXPERIMENT_ID
            or m["output_root"] != OUTPUT_ROOT or m["selected_operating_point"] is not None or m["quality_gate"] is not None
            or m["proposal"]["sha256"] != EXPECTED_PROPOSAL_SHA):
        raise ValueError("YOLO experiment differs from exact approved proposal")
    p = read_json(bound_file(root, m["proposal"], "configs/ball_tracking/proposals"))
    if (p["schema_version"] != "ball_detector_challenger_proposal/v0.1" or p["proposal_id"] != EXPERIMENT_ID
            or [(w["possession_id"], w["start_frame_index"], w["end_frame_index"]) for w in p["windows"]] != APPROVED_WINDOWS
            or p["crop_views"] != crop_views() or p["sealed_holdouts"] != SEALED
            or p["proposed_output_root"] != OUTPUT_ROOT):
        raise ValueError("Unsupported YOLO frame/crop scope")
    if len(p["original_embargo_paths"]) != 9 or any(safe_path(root, s).exists() for s in p["original_embargo_paths"]):
        raise ValueError("An original prediction embargo is not intact")
    # Labels, controls, review manifests, player records and source videos are
    # intentionally not opened here. Their metadata is frozen by proposal bytes.
    for key in ("design_document", "prior_results"):
        b = p[key]
        if sha256_file(safe_path(root, b["path"], "docs")) != b["sha256"]:
            raise ValueError("Approved YOLO design/results bytes changed")
    approval = closed(read_json(bound_file(root, m["authorization"], "configs/ball_tracking/reviews")),
        {"schema_version", "experiment_spec_sha256", "proposal", "approved_by", "statement", "recorded_at_utc",
         "timestamp_semantics", "scope", "git_mutations_authorized"}, "YOLO authorization")
    if (approval["schema_version"] != "ball_yolo_crop_experiment_approval/v0.1"
            or approval["experiment_spec_sha256"] != spec_digest(m) or approval["proposal"] != m["proposal"]
            or approval["approved_by"] != "ryan" or not isinstance(approval["statement"], str) or not approval["statement"].strip()
            or approval["scope"] != "six_development_windows_four_fixed_crops_three_selectors"
            or approval["git_mutations_authorized"] is not False):
        raise ValueError("Missing exact YOLO experiment authorization")
    return m, p


def inspect_runtime(root, runtime, commit):
    from .yolo11x_adapter import inspect_runtime as inspect
    weights = safe_path(root, runtime["weights"]["path"], "data/outputs/ball_tracking")
    return weights, inspect(weights, runtime, commit)


def preflight(root, path, *, require_clean=True):
    root, path = Path(root).resolve(), Path(path).resolve()
    m, p = load_manifest(root, path)
    commit = clean_commit(root) if require_clean else git(root, "rev-parse", "HEAD")
    if require_clean:
        for target in [path, *(root / m[k]["path"] for k in ("proposal", "authorization")),
                       *(root / p[k]["path"] for k in ("design_document", "prior_results", "prior_visual_review")),
                       *Path(__file__).parent.glob("yolo*.py")]:
            _tracked(root, target)
    runtime = read_json(bound_file(root, m["runtime"], "data/outputs/ball_tracking"))
    weights, model = inspect_runtime(root, runtime, commit)
    model_contract = p["model"]
    if (model.model_name != model_contract["model_name"] or model.package_name != "ultralytics"
            or model.package_version != model_contract["package_version"] or model.code_commit != commit
            or model.weights_sha256 != model_contract["publisher_expected_weights_sha256"]
            or model.target_class_id != 37 or model.target_class_name != "sports ball"
            or model.export_confidence_floor != .01 or model.tiling_enabled
            or model.precision != "float32" or (model.input_width_px, model.input_height_px) != (640, 640)):
        raise ValueError("Runtime model provenance differs from approved detector")
    inventory = p["inference_source_frames"]
    expected = [(w["window_id"], f) for w in p["windows"]
                for f in range(w["start_frame_index"], w["end_frame_index"] + 1)]
    if len(inventory) != 150 or [(r["window_id"], r["frame_index"]) for r in inventory] != expected:
        raise ValueError("Expected exactly 150 ordered approved source PNGs")
    for record in inventory:
        closed(record, {"window_id", "frame_index", "source_png"}, "inference source")
        png = bound_source_png(root, record["source_png"])
        if (png.suffix != ".png" or png.parent.name != "unmarked_source"
                or png.name != f"frame_{record['frame_index']:06d}.png"
                or record["window_id"] not in png.parts):
            raise ValueError("Inference inventory must contain exact unmarked source PNGs")
    inputs = []
    for w in p["windows"]:
        source = SourceVideo.from_mapping(w["source_video"])
        if (source.width_px, source.height_px, source.fps) != (1920, 1080, 25.0):
            raise ValueError("Unexpected source dimensions/timing")
        inputs.append({"window": w, "source_frames": [r for r in inventory if r["window_id"] == w["window_id"]],
                       "runtime_record": runtime, "model": model, "weights_path": weights})
    if subprocess.run(["git", "check-ignore", "-q", "--", OUTPUT_ROOT + "/ignore_check.json"], cwd=root).returncode:
        raise ValueError("YOLO generated outputs must be ignored")
    return m, p, inputs, commit


def unchanged(root, path, m, commit):
    if clean_commit(root) != commit:
        raise ValueError("Git changed during YOLO stage")
    loaded, _, _, current = preflight(root, path)
    if loaded != m or current != commit:
        raise ValueError("YOLO inputs changed during stage")


def output_path(root, window, config=None):
    suffix = "candidates.json" if config is None else config.variant_id + ".json"
    return safe_path(root, f"{OUTPUT_ROOT}/{window['window_id']}/{suffix}", OUTPUT_ROOT)


def candidate_path(root, window):
    return output_path(root, window)


def checkpoint_path(root, window, frame, view):
    return safe_path(root, f"{OUTPUT_ROOT}/{window['window_id']}/views/frame_{frame:06d}_{view['view_id']}.json", OUTPUT_ROOT)


def make_header(m, window, model, source_frames):
    return {"experiment_spec_sha256": spec_digest(m), "runtime": m["runtime"], "window": window,
            "per_view_model_provenance": model.to_dict(), "source_frames": source_frames,
            "crop_views": crop_views(), "candidate_semantics": "postprocessed/exported candidates; per-view NMS and cap; all cross-crop duplicates retained",
            "selected_operating_point": None, "quality_gate": None}


def read_checkpoint(path, header, frame, view, source_png, model):
    from .yolo11x_adapter import validate_prediction
    value = closed(read_json(path), {"schema_version", "header", "frame_index", "source_png", "result", "content_sha256"}, "YOLO crop checkpoint")
    if (value["schema_version"] != "ball_yolo_crop_checkpoint/v0.1" or value["header"] != header
            or type(value["frame_index"]) is not int or value["frame_index"] != frame or value["source_png"] != source_png
            or value["content_sha256"] != canonical_sha256({k: v for k, v in value.items() if k != "content_sha256"})):
        raise ValueError("YOLO checkpoint provenance/content differs")
    result = value["result"]
    if result["view"] != view:
        raise ValueError("YOLO checkpoint crop differs")
    validate_prediction(result["prediction"], model)
    # Validate every scalar and the complete local geometry through the pure
    # four-view combiner without assembling a source-frame output.
    from .yolo_crop_candidates import VIEW_FIELDS
    closed(result, VIEW_FIELDS, "YOLO crop result")
    from .tiled_candidates import finite_nonnegative, validate_local
    finite_nonnegative(result["elapsed_seconds"], "elapsed seconds")
    if type(result["cuda_peak_allocated_bytes"]) is not int or result["cuda_peak_allocated_bytes"] < 0:
        raise ValueError("Invalid checkpoint memory count")
    if not isinstance(result["attempt_id"], str) or not result["attempt_id"]:
        raise ValueError("Missing checkpoint attempt")
    validate_local(result["prediction"]["candidates"], view, SourceVideo.from_mapping(header["window"]["source_video"]), model)
    return result


def load_candidate_run(root, m, p, window, commit, *, model=None):
    if model is None:
        runtime = read_json(bound_file(root, m["runtime"], "data/outputs/ball_tracking"))
        _, model = inspect_runtime(root, runtime, commit)
    if model.code_commit != commit:
        raise ValueError("Preflight model commit differs")
    frames = [r for r in p["inference_source_frames"] if r["window_id"] == window["window_id"]]
    header = make_header(m, window, model, frames)
    payload = validate_output(read_json(output_path(root, window)), header)
    return candidate_run(payload), payload, payload["content_sha256"]


def load_observations(root, m, p, window, run, digest, config, commit, *, rederive=False):
    value = closed(read_json(output_path(root, window, config)), ENVELOPE_FIELDS, "YOLO selector envelope")
    obs = value["observations"]
    if (value["experiment_spec_sha256"] != spec_digest(m)
            or value["input_candidates"] != file_binding(root, output_path(root, window))
            or value["candidate_content_sha256"] != digest or value["observations_content_sha256"] != canonical_sha256(obs)
            or obs["schema_version"] != SCHEMA or obs["config"] != asdict(config) or obs["variant_id"] != config.variant_id
            or obs["ranking_code_commit"] != commit or obs["detector_code_commit"] != run.model_provenance.code_commit
            or obs["input_candidate_content_sha256"] != canonical_sha256(run.to_dict())
            or obs["source_video"] != run.source_video.to_dict() or obs["window"] != run.window.to_dict()
            or obs["possession_id"] != run.possession_id or obs["selected_operating_point"] is not None or obs["quality_gate"] is not None
            or [f["frame_index"] for f in obs["frames"]] != [f.frame_index for f in run.frames]):
        raise ValueError("YOLO selector observation provenance differs")
    from .yolo_crop_candidates import validate_saved_structure
    validate_saved_structure(obs, run)
    if rederive:
        validate_observations(obs, run)
    return obs


def load_saved_control(root, p, window, config):
    config = ControlConfig.from_mapping(asdict(config))
    if config.arm not in ("crop_raw", "crop_top_one", "crop_top_twenty"):
        raise ValueError("Only the three saved simple controls are in scope")
    suffix = f"/{window['window_id']}/{config.variant_id}.json"
    matches = [b for b in p["saved_control_outputs"] if b["path"].endswith(suffix)]
    if len(matches) != 1:
        raise ValueError("Missing/duplicate saved RF-DETR selector")
    value = read_json(bound_file(root, matches[0], "data/outputs/ball_tracking/crop_motion_factorial"))
    obs = value["observations"]
    if (obs["schema_version"] != "ball_crop_motion_observations/v0.1" or obs["config"] != asdict(config)
            or obs["variant_id"] != config.variant_id or obs["ranking_code_commit"] != PRIOR_COMMIT
            or obs["source_video"] != window["source_video"] or obs["possession_id"] != window["possession_id"]
            or obs["window"] != {k: window[k] for k in ("start_frame_index", "end_frame_index")}
            or [f["frame_index"] for f in obs["frames"]] != list(range(window["start_frame_index"], window["end_frame_index"] + 1))):
        raise ValueError("Saved RF-DETR control provenance differs")
    return obs


def create_adapter(weights, runtime, commit):
    from .yolo11x_adapter import YOLO11xAdapter
    return YOLO11xAdapter(weights, runtime, commit)


def read_source_png(root, record):
    import cv2
    import numpy as np
    binding = closed(record["source_png"], {"path", "sha256"}, "source PNG binding")
    require_digest(binding["sha256"], "source PNG")
    path = safe_path(Path(root), binding["path"], "data/outputs/ball_tracking")
    if path.suffix != ".png":
        raise ValueError("Source binding must name a PNG")
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != binding["sha256"]:
        raise ValueError("Source PNG bytes changed before decode")
    pixels = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if pixels is None or pixels.shape != (1080, 1920, 3):
        raise ValueError("Bound unmarked PNG dimensions/decoding differ")
    return cv2.cvtColor(pixels, cv2.COLOR_BGR2RGB)


def _accounting(value, *, prepared=False):
    fields = {"synthetic_forwards", "project_attempts", "project_forwards", "preparation_complete"}
    closed(value, fields, "adapter accounting")
    if (any(type(value[k]) is not int or value[k] < 0 for k in fields - {"preparation_complete"})
            or type(value["preparation_complete"]) is not bool or value["project_forwards"] > value["project_attempts"]
            or (prepared and (not value["preparation_complete"] or value["synthetic_forwards"] < 1))):
        raise ValueError("Invalid adapter forward accounting")
    return copy.deepcopy(value)


def _attempt_files(root):
    folder = safe_path(root, OUTPUT_ROOT + "/attempts", OUTPUT_ROOT)
    return folder


def _preparation_folder(root):
    return safe_path(root, OUTPUT_ROOT + "/preparations", OUTPUT_ROOT)


def _validate_preparations(root, manifest, commit):
    folder = _preparation_folder(root)
    starts, results = {}, {}
    for path in sorted(folder.glob("*.json")) if folder.exists() else []:
        value = read_json(path)
        identity = value.get("preparation_id")
        if path.name.endswith(".start.json"):
            closed(value, {"preparation_id", "experiment_spec_sha256", "runtime", "code_commit", "accounting_before", "started_at_utc"}, "preparation start")
            before = _accounting(value["accounting_before"])
            if (identity != path.name.removesuffix(".start.json") or value["experiment_spec_sha256"] != spec_digest(manifest)
                    or value["runtime"] != manifest["runtime"] or value["code_commit"] != commit
                    or before != {"synthetic_forwards": 0, "project_attempts": 0, "project_forwards": 0, "preparation_complete": False}):
                raise ValueError("Preparation start provenance/accounting differs")
            starts[identity] = value
        elif path.name.endswith(".result.json"):
            closed(value, {"preparation_id", "start_sha256", "status", "accounting_after", "error", "finished_at_utc"}, "preparation result")
            if identity != path.name.removesuffix(".result.json") or value["status"] not in ("prepared", "failed"):
                raise ValueError("Invalid preparation result")
            after = _accounting(value["accounting_after"], prepared=value["status"] == "prepared")
            if (after["project_attempts"] or after["project_forwards"]
                    or (value["status"] == "prepared" and value["error"] is not None)
                    or (value["status"] == "failed" and not isinstance(value["error"], str))):
                raise ValueError("Preparation consumed project work or has invalid status")
            results[identity] = value
        else:
            raise ValueError("Unexpected file in preparation ledger")
    for identity, value in results.items():
        if identity not in starts or value["start_sha256"] != sha256_file(folder / (identity + ".start.json")):
            raise ValueError("Preparation result lost its start binding")
    return starts, results


def _validate_attempts(root, headers, preparations):
    folder = _attempt_files(root)
    starts, results = {}, {}
    for path in sorted(folder.glob("*.json")) if folder.exists() else []:
        value = read_json(path)
        if path.name.endswith(".start.json"):
            closed(value, {"attempt_id", "preparation_id", "window_id", "frame_index", "view", "header_sha256", "source_png", "accounting_before", "started_at_utc"}, "attempt start")
            identity = value["window_id"]
            if identity not in headers or value["header_sha256"] != canonical_sha256(headers[identity]):
                raise ValueError("Saved attempt provenance differs")
            header = headers[identity]
            source = next((r["source_png"] for r in header["source_frames"] if r["frame_index"] == value["frame_index"]), None)
            if source is None or source != value["source_png"] or value["view"] not in crop_views() or value["attempt_id"] != path.name.removesuffix(".start.json"):
                raise ValueError("Saved attempt scope differs")
            before = _accounting(value["accounting_before"], prepared=True)
            prepared = preparations.get(value["preparation_id"])
            if (prepared is None or prepared["status"] != "prepared"
                    or before["synthetic_forwards"] != prepared["accounting_after"]["synthetic_forwards"]):
                raise ValueError("Project attempt has no matching completed synthetic preparation")
            starts[value["attempt_id"]] = value
        elif path.name.endswith(".result.json"):
            closed(value, {"attempt_id", "start_sha256", "status", "accounting_after", "checkpoint", "error", "finished_at_utc"}, "attempt result")
            if value["attempt_id"] != path.name.removesuffix(".result.json") or value["status"] not in ("completed", "failed"):
                raise ValueError("Invalid saved attempt result")
            _accounting(value["accounting_after"], prepared=True)
            results[value["attempt_id"]] = value
        else:
            raise ValueError("Unexpected file in attempt ledger")
    for identity, value in results.items():
        if identity not in starts or value["start_sha256"] != sha256_file(folder / (identity + ".start.json")):
            raise ValueError("Attempt result lost its start binding")
        if value["status"] == "completed":
            if value["error"] is not None or not value["checkpoint"]:
                raise ValueError("Invalid completed attempt")
            checkpoint = bound_file(root, value["checkpoint"], OUTPUT_ROOT)
            start = starts[identity]
            expected_path = checkpoint_path(root, headers[start["window_id"]]["window"], start["frame_index"], start["view"])
            if checkpoint != expected_path or read_json(checkpoint)["result"]["attempt_id"] != identity:
                raise ValueError("Completed attempt points at another crop checkpoint")
        elif value["checkpoint"] is not None or not isinstance(value["error"], str):
            raise ValueError("Failed attempt cannot certify a checkpoint")
        before, after = starts[identity]["accounting_before"], value["accounting_after"]
        delta_attempts = after["project_attempts"] - before["project_attempts"]
        delta_forwards = after["project_forwards"] - before["project_forwards"]
        if (after["synthetic_forwards"] != before["synthetic_forwards"] or not 0 <= delta_forwards <= delta_attempts <= 1
                or (value["status"] == "completed" and (delta_attempts, delta_forwards) != (1, 1))):
            raise ValueError("Attempt ledger forward accounting differs")
    return starts, results


def run_experiment(root, path, *, dry_run=False, adapter_factory=None, png_reader=None):
    root, path = Path(root).resolve(), Path(path).resolve()
    m, p, inputs, commit = preflight(root, path, require_clean=not dry_run)
    if dry_run:
        return {"dry_run": True, "source_frames": 150, "unique_project_crop_units": 600,
                "window_candidates": 6, "selector_outputs": 162, "model_constructed": False}
    headers = {item["window"]["window_id"]: make_header(m, item["window"], item["model"], item["source_frames"]) for item in inputs}
    # Validate every existing checkpoint and derived output before any adapter
    # construction, synthetic warmup, source PNG decode or project retry.
    preparation_starts, preparations = _validate_preparations(root, m, commit)
    starts, results = _validate_attempts(root, headers, preparations)
    cached, candidate_payloads = {}, {}
    for item in inputs:
        w, model = item["window"], item["model"]
        header = headers[w["window_id"]]
        for source in item["source_frames"]:
            f = source["frame_index"]
            for view in crop_views():
                target = checkpoint_path(root, w, f, view)
                if target.exists():
                    record = read_checkpoint(target, header, f, view, source["source_png"], model)
                    attempt = starts.get(record["attempt_id"])
                    if attempt is None or (attempt["window_id"], attempt["frame_index"], attempt["view"]) != (w["window_id"], f, view):
                        raise ValueError("Checkpoint has no matching started attempt")
                    final = results.get(record["attempt_id"])
                    after = {k: v for k, v in record["prediction"]["forward_accounting"].items() if k != "this_project_attempt_forwards"}
                    if (final is not None and (final["status"] != "completed" or final["accounting_after"] != after)):
                        raise ValueError("Checkpoint differs from its completed attempt accounting")
                    before = attempt["accounting_before"]
                    if (after["synthetic_forwards"] != before["synthetic_forwards"]
                            or after["project_attempts"] != before["project_attempts"] + 1
                            or after["project_forwards"] != before["project_forwards"] + 1):
                        raise ValueError("Cached checkpoint project forward differs")
                    cached[w["window_id"], f, view["view_id"]] = record
        target = output_path(root, w)
        if target.exists():
            candidate_payloads[w["window_id"]] = validate_output(read_json(target), header)
            run = candidate_run(candidate_payloads[w["window_id"]])
            for config in experiment_grid():
                if output_path(root, w, config).exists():
                    load_observations(root, m, p, w, run, candidate_payloads[w["window_id"]]["content_sha256"], config, commit, rederive=True)
        elif any(output_path(root, w, c).exists() for c in experiment_grid()):
            raise ValueError("Selector output without its candidate window")
        if target.exists() and any((w["window_id"], s["frame_index"], v["view_id"]) not in cached for s in item["source_frames"] for v in crop_views()):
            raise ValueError("Candidate file without all crop checkpoints")
        if target.exists():
            rebuilt = make_output(header, [make_frame(s["frame_index"], s["source_png"],
                [cached[w["window_id"], s["frame_index"], v["view_id"]] for v in crop_views()],
                SourceVideo.from_mapping(w["source_video"]), model) for s in item["source_frames"]])
            if rebuilt != candidate_payloads[w["window_id"]]:
                raise ValueError("Saved candidate file differs from checkpoints before model creation")
    missing = 600 - len(cached)
    adapter = None
    created, attempt_count = 0, 0
    if missing:
        first = inputs[0]
        adapter = (adapter_factory or create_adapter)(first["weights_path"], first["runtime_record"], commit)
        before = _accounting(adapter.accounting)
        if before != {"synthetic_forwards": 0, "project_attempts": 0, "project_forwards": 0, "preparation_complete": False}:
            raise ValueError("A fresh adapter is required for auditable invocation accounting")
        preparation_id = uuid.uuid4().hex
        preparation_path = _preparation_folder(root) / (preparation_id + ".start.json")
        persist_once(preparation_path, {"preparation_id": preparation_id, "experiment_spec_sha256": spec_digest(m),
            "runtime": m["runtime"], "code_commit": commit, "accounting_before": before,
            "started_at_utc": datetime.now(timezone.utc).isoformat()})
        try:
            adapter.prepare()
            prepared = _accounting(adapter.accounting, prepared=True)
            if prepared["project_attempts"] or prepared["project_forwards"]:
                raise ValueError("Warmup used project forwards")
        except Exception as error:
            persist_once(_preparation_folder(root) / (preparation_id + ".result.json"), {
                "preparation_id": preparation_id, "start_sha256": sha256_file(preparation_path), "status": "failed",
                "accounting_after": _accounting(adapter.accounting), "error": type(error).__name__ + ": " + str(error),
                "finished_at_utc": datetime.now(timezone.utc).isoformat()})
            raise
        persist_once(_preparation_folder(root) / (preparation_id + ".result.json"), {
            "preparation_id": preparation_id, "start_sha256": sha256_file(preparation_path), "status": "prepared",
            "accounting_after": prepared, "error": None, "finished_at_utc": datetime.now(timezone.utc).isoformat()})
    for item in inputs:
        w, model, header = item["window"], item["model"], headers[item["window"]["window_id"]]
        frames = []
        for source in item["source_frames"]:
            f, records = source["frame_index"], []
            needed = [v for v in crop_views() if (w["window_id"], f, v["view_id"]) not in cached]
            rgb = (png_reader or read_source_png)(root, source) if needed else None
            if needed and (rgb.shape != (1080, 1920, 3) or str(rgb.dtype) != "uint8"):
                raise ValueError("Source reader must return native uint8 RGB")
            for view in crop_views():
                key, target = (w["window_id"], f, view["view_id"]), checkpoint_path(root, w, f, view)
                if key not in cached:
                    attempt_id = uuid.uuid4().hex
                    folder = _attempt_files(root)
                    before = _accounting(adapter.accounting, prepared=True)
                    start = {"attempt_id": attempt_id, "preparation_id": preparation_id, "window_id": w["window_id"], "frame_index": f, "view": view,
                             "header_sha256": canonical_sha256(header), "source_png": source["source_png"],
                             "accounting_before": before, "started_at_utc": datetime.now(timezone.utc).isoformat()}
                    start_path = folder / (attempt_id + ".start.json")
                    persist_once(start_path, start)
                    began = time.perf_counter()
                    try:
                        x1, y1, x2, y2 = view["xyxy_half_open_px"]
                        prediction = adapter.predict_frame(rgb[y1:y2, x1:x2].copy())
                        after = _accounting(adapter.accounting, prepared=True)
                        if (after["synthetic_forwards"] != before["synthetic_forwards"]
                                or after["project_attempts"] != before["project_attempts"] + 1
                                or after["project_forwards"] != before["project_forwards"] + 1
                                or prediction["forward_accounting"] != {**after, "this_project_attempt_forwards": 1}):
                            raise ValueError("Exactly one project forward per successful attempt required")
                        peak = adapter.cuda_peak_allocated_bytes
                        if type(peak) is not int or peak < 0:
                            raise ValueError("A measured nonnegative per-crop CUDA peak is required")
                        result = {"view": view, "prediction": prediction, "elapsed_seconds": time.perf_counter() - began,
                                  "cuda_peak_allocated_bytes": peak, "attempt_id": attempt_id}
                        payload = {"schema_version": "ball_yolo_crop_checkpoint/v0.1", "header": header,
                                   "frame_index": f, "source_png": source["source_png"], "result": result}
                        payload["content_sha256"] = canonical_sha256(payload)
                        # Validate via the same pure candidate geometry before publication.
                        from .yolo11x_adapter import validate_prediction
                        validate_prediction(prediction, model)
                        persist_once(target, payload)
                        cached[key] = read_checkpoint(target, header, f, view, source["source_png"], model)
                        persist_once(folder / (attempt_id + ".result.json"), {"attempt_id": attempt_id,
                            "start_sha256": sha256_file(start_path), "status": "completed", "accounting_after": after,
                            "checkpoint": file_binding(root, target), "error": None,
                            "finished_at_utc": datetime.now(timezone.utc).isoformat()})
                        created += 1; attempt_count += 1
                    except Exception as error:
                        # A committed valid checkpoint survives an interruption between
                        # its atomic publication and the ledger completion record.
                        if not target.exists():
                            persist_once(folder / (attempt_id + ".result.json"), {"attempt_id": attempt_id,
                                "start_sha256": sha256_file(start_path), "status": "failed",
                                "accounting_after": _accounting(adapter.accounting, prepared=True), "checkpoint": None,
                                "error": type(error).__name__ + ": " + str(error),
                                "finished_at_utc": datetime.now(timezone.utc).isoformat()})
                        raise
                records.append(cached[key])
            frames.append(make_frame(f, source["source_png"], records, SourceVideo.from_mapping(w["source_video"]), model))
        payload = make_output(header, frames)
        if w["window_id"] in candidate_payloads and payload != candidate_payloads[w["window_id"]]:
            raise ValueError("Saved candidate file differs from completed crop checkpoints")
        persist_once(output_path(root, w), payload)
        run = candidate_run(payload)
        for config in experiment_grid():
            obs = select_candidates(run, config, commit)
            persist_once(output_path(root, w, config), {"experiment_spec_sha256": spec_digest(m),
                "input_candidates": file_binding(root, output_path(root, w)), "candidate_content_sha256": payload["content_sha256"],
                "observations_content_sha256": canonical_sha256(obs), "observations": obs})
    unchanged(root, path, m, commit)
    preparation_starts, preparations = _validate_preparations(root, m, commit)
    starts, results = _validate_attempts(root, headers, preparations)
    return {"unique_completed_crop_units": len(cached), "created_crop_checkpoints": created,
            "project_attempts_this_invocation": attempt_count, "total_recorded_project_attempts": len(starts),
            "failed_attempt_records": sum(r["status"] == "failed" for r in results.values()),
            "unfinished_attempt_records": len(set(starts) - set(results)),
            "recorded_synthetic_forwards": sum(r["accounting_after"]["synthetic_forwards"] for r in preparations.values()),
            "predictor_preparations": len(preparation_starts),
            "unfinished_preparation_records": len(set(preparation_starts) - set(preparations)),
            "unfinished_accounting_is_unknown": bool(set(starts) - set(results) or set(preparation_starts) - set(preparations)),
            "forward_accounting_this_invocation": adapter.accounting if adapter else None,
            "window_candidate_files": 6, "selector_outputs": 162, "reused_control_outputs": 162,
            "commit": commit, "selected_operating_point": None, "quality_gate": None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = args.repository_root.resolve()
    print(json.dumps(run_experiment(root, (root / args.manifest).resolve(), dry_run=args.dry_run), indent=2))


if __name__ == "__main__":
    main()
