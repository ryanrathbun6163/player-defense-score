"""Approved fixed-crop experiment with immutable per-view checkpoints and no label reads."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

from .annotations import verify_source_video_contract
from .detections import ModelProvenance
from .detector_experiments import build_model_provenance, load_detector_experiment
from .development_experiments import bound_file, canonical_sha256, closed, read_json, safe_path, sha256_file
from .temporal_association import THRESHOLDS, RADII
from .temporal_experiment import (
    _tracked, clean_commit, file_binding, git, load_inputs, load_manifest as load_temporal,
    persist_once, spec_digest,
)
from .tiled_candidates import VIEW_FIELDS, crop_views, make_frame, make_output, validate_local, validate_output, finite_nonnegative

EXPERIMENT_ID = "rfdetr_medium_tiled_development_comparison_v0_1"
OUTPUT_ROOT = f"data/outputs/ball_tracking/tiled_development/{EXPERIMENT_ID}"
FIELDS = {"schema_version", "experiment_id", "proposal", "temporal_baseline", "output_root", "authorization", "selected_operating_point", "quality_gate"}


def prepare_manifest_payloads(root, proposal_path, temporal_path, approval_path, statement, recorded_at_utc):
    manifest = {"schema_version": "ball_tiled_experiment/v0.1", "experiment_id": EXPERIMENT_ID,
                "proposal": file_binding(root, proposal_path), "temporal_baseline": file_binding(root, temporal_path),
                "output_root": OUTPUT_ROOT, "authorization": None, "selected_operating_point": None, "quality_gate": None}
    approval = {"schema_version": "ball_tiled_experiment_approval/v0.1", "experiment_spec_sha256": spec_digest(manifest),
                "proposal": manifest["proposal"], "approved_by": "ryan", "statement": statement,
                "recorded_at_utc": recorded_at_utc,
                "timestamp_semantics": "Receipt creation time; authorization is the user's response to the linked fixed-crop proposal.",
                "scope": "six_development_windows_four_fixed_crops_all_declared_comparisons",
                "git_mutations_authorized": False}
    content = (json.dumps(approval, indent=2, allow_nan=False) + "\n").encode("utf-8")
    manifest["authorization"] = {"path": approval_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(content).hexdigest()}
    return manifest, approval


def load_manifest(root, path):
    safe_path(root, path.relative_to(root).as_posix(), "configs/ball_tracking/tiled_experiments")
    m = closed(read_json(path), FIELDS, "tiled manifest")
    if (m["schema_version"] != "ball_tiled_experiment/v0.1" or m["experiment_id"] != EXPERIMENT_ID
            or m["output_root"] != OUTPUT_ROOT or m["selected_operating_point"] is not None or m["quality_gate"] is not None):
        raise ValueError("Unsupported tiled experiment")
    proposal_path = bound_file(root, m["proposal"], "configs/ball_tracking/proposals")
    p = read_json(proposal_path)
    temporal = load_temporal(root, bound_file(root, m["temporal_baseline"], "configs/ball_tracking/temporal_experiments"))
    baseline = load_detector_experiment(bound_file(root, p["saved_control_manifest"], "configs/ball_tracking/experiments"))
    checks = {
        "schema_version": "ball_tiled_development_comparison_proposal/v0.1", "proposal_id": EXPERIMENT_ID,
        "status": "proposal_not_authorized_not_executable", "authorization": None,
        "windows": temporal["windows"], "scoring_labels": temporal["scoring_labels"],
        "saved_control_manifest": temporal["baseline"], "frozen_detector_contract_source": temporal["baseline"],
        "crop_views": crop_views(), "image_arms": ["saved_whole_frame", "four_crop_union"], "selectors": ["raw", "top_one"],
        "confidence_thresholds": list(THRESHOLDS), "localization_radii_px": list(RADII),
        "proposed_output_root": OUTPUT_ROOT, "selected_operating_point": None, "quality_gate": None,
        "inference_labels_access_allowed": False, "training_allowed": False, "window_expansion_allowed": False,
        "saved_control_rerun_allowed": False, "temporal_filtering_allowed": False, "holdout_release_authorized": False,
        "original_v0_1_embargoes_preserved": True, "duplicate_policy": "retain_all_no_nms_no_deduplication",
        "pool_separation": ["representative_evaluation", "challenge_evaluation"],
        "matching_rule": "raw center distance; uncertainty diagnostic only",
        "review": {"confidence_thresholds": [.2, .35], "radius_px": 10.0,
                   "panels": ["saved_whole_frame/raw", "saved_whole_frame/top_one", "four_crop_union/raw", "four_crop_union/top_one"],
                   "all_frames_and_final_frame_required": True, "clips": 12},
        "expected_counts": {"source_frames": 150, "new_model_calls": 600, "new_detection_files": 6,
                            "per_window_reports_saved_control": 540, "per_window_reports_new_crop": 540,
                            "total_per_window_reports": 1080, "aggregate_cells_per_pool": 180},
    }
    if any(canonical_sha256(p.get(k)) != canonical_sha256(v) for k, v in checks.items()):
        raise ValueError("Proposal differs from the supported fixed-crop comparison")
    if any(v != baseline.payload["detector"].get(k) for k, v in p["model"].items()):
        raise ValueError("Frozen per-view detector changed")
    for key in ("design", "rationale"):
        record = closed(p[key], {"path", "sha256"}, key)
        if sha256_file(safe_path(root, record["path"], "docs")) != record["sha256"]:
            raise ValueError("Approved design/rationale changed")
    receipt = read_json(bound_file(root, p["temporal_review_receipt"], "configs/ball_tracking/reviews"))
    if (receipt["human_visual_review"]["status"] != "completed" or receipt["human_visual_review"]["reviewer_id"] != "ryan"
            or receipt["bound_evidence"]["experiment_manifest"] != m["temporal_baseline"]):
        raise ValueError("Missing reviewed temporal evidence")
    approval = closed(read_json(bound_file(root, m["authorization"], "configs/ball_tracking/reviews")),
                      {"schema_version", "experiment_spec_sha256", "proposal", "approved_by", "statement", "recorded_at_utc",
                       "timestamp_semantics", "scope", "git_mutations_authorized"}, "tiled authorization")
    if (approval["schema_version"] != "ball_tiled_experiment_approval/v0.1" or approval["proposal"] != m["proposal"]
            or approval["experiment_spec_sha256"] != spec_digest(m) or approval["approved_by"] != "ryan"
            or not isinstance(approval["statement"], str) or not approval["statement"].strip()
            or approval["scope"] != "six_development_windows_four_fixed_crops_all_declared_comparisons"
            or approval["git_mutations_authorized"] is not False):
        raise ValueError("Missing exact-scope crop experiment approval")
    return m, p, temporal, baseline


def output_path(root, window):
    return safe_path(root, f"{OUTPUT_ROOT}/{window['window_id']}/candidates.json", OUTPUT_ROOT)


def checkpoint_path(root, window, frame, view):
    return safe_path(root, f"{OUTPUT_ROOT}/{window['window_id']}/views/frame_{frame:06d}_{view['view_id']}.json", OUTPUT_ROOT)


def preflight(root, manifest_path, *, require_clean=True, verify_sources=True):
    m, p, temporal, baseline = load_manifest(root, manifest_path)
    commit = clean_commit(root) if require_clean else git(root, "rev-parse", "HEAD")
    if require_clean:
        for path in [manifest_path, *(root / m[k]["path"] for k in ("proposal", "temporal_baseline", "authorization")),
                     *(root / p[k]["path"] for k in ("design", "rationale", "temporal_review_receipt")),
                     *(root / r["annotation"]["path"] for r in p["scoring_labels"]),
                     *Path(__file__).parent.glob("tiled_*.py")]:
            _tracked(root, path)
    runs = load_inputs(root, temporal)
    seen = set()
    for window, run in zip(p["windows"], runs):
        if (run.source_video.width_px, run.source_video.height_px, run.source_video.fps) != (1920, 1080, 25.0):
            raise ValueError("Source dimensions/timing differ from approved crop grid")
        if verify_sources and run.source_video.sha256 not in seen:
            verify_source_video_contract(run.source_video, root)
            seen.add(run.source_video.sha256)
        target = output_path(root, window)
        if subprocess.run(["git", "check-ignore", "-q", "--", target.relative_to(root).as_posix()], cwd=root).returncode:
            raise ValueError("Tiled outputs must remain ignored")
    return m, p, runs, baseline, commit


def inspect_runtime(baseline, commit):
    from .run_detector_experiment import default_dependencies, _validate_package_and_weights
    dependencies = default_dependencies()
    weights = _validate_package_and_weights(baseline, dependencies)
    device = dependencies.inspect_runtime_device()
    model = build_model_provenance(baseline.detector, code_commit=commit, runtime_device=device)
    return weights, model


def make_header(m, window, model):
    return {"experiment_spec_sha256": spec_digest(m), "window": window,
            "per_view_model_provenance": model.to_dict(), "crop_views": crop_views(),
            "tiling_enabled": True, "selected_operating_point": None, "quality_gate": None}


def read_checkpoint(path, header, frame, view, raw, model):
    value = closed(read_json(path), {"header", "frame_index", "result", "content_sha256"}, "crop checkpoint")
    if (value["header"] != header or type(value["frame_index"]) is not int or value["frame_index"] != frame
            or value["content_sha256"] != canonical_sha256({k: v for k, v in value.items() if k != "content_sha256"})):
        raise ValueError("Crop checkpoint provenance/content mismatch")
    result = closed(value["result"], VIEW_FIELDS, "crop result")
    if result["view"] != view:
        raise ValueError("Crop checkpoint view mismatch")
    validate_local(result["candidates"], view, raw.source_video, model)
    finite_nonnegative(result["elapsed_seconds"], "inference duration")
    if type(result["cuda_peak_allocated_bytes"]) is not int or result["cuda_peak_allocated_bytes"] < 0:
        raise ValueError("Invalid CUDA peak allocation")
    return result


def frames_from_video(root, raw, wanted):
    import cv2
    capture = cv2.VideoCapture(str(safe_path(root, raw.source_video.path.as_posix(), "data/clips")))
    try:
        if not capture.isOpened():
            raise ValueError("Source video cannot be opened")
        for frame in sorted(wanted):
            if not capture.set(cv2.CAP_PROP_POS_FRAMES, frame):
                raise ValueError("Could not seek source frame")
            ok, pixels = capture.read()
            if (not ok or pixels.shape != (1080, 1920, 3)
                    or round(capture.get(cv2.CAP_PROP_POS_FRAMES)) != frame + 1):
                raise ValueError("Source decode/frame-index mismatch")
            yield frame, cv2.cvtColor(pixels, cv2.COLOR_BGR2RGB)
    finally:
        capture.release()


def create_adapter(weights, floor):
    from .rfdetr_adapter import RFDETRBallAdapter
    return RFDETRBallAdapter(weights_path=weights, export_confidence_floor=floor)


def synchronize(*, reset_peak=False):
    import torch
    torch.cuda.synchronize()
    if reset_peak:
        torch.cuda.reset_peak_memory_stats()


def peak_memory():
    import torch
    return torch.cuda.max_memory_allocated()


def unchanged(root, path, manifest, commit):
    current = load_manifest(root, path)
    if clean_commit(root) != commit or current[0] != manifest:
        raise ValueError("Git or approved manifest changed during execution")
    load_inputs(root, current[2])


def run_experiment(root, manifest_path, *, dry_run=False):
    m, p, runs, baseline, commit = preflight(root, manifest_path, require_clean=not dry_run)
    weights, model = inspect_runtime(baseline, commit)
    if dry_run:
        return {"dry_run": True, "windows": 6, "source_frames": 150, "new_model_calls": 600,
                "runtime": model.device, "execution_requires_clean_commit": True}
    # Audit every existing final/checkpoint before making even one new model call.
    cached, headers = {}, {}
    for w, raw in zip(p["windows"], runs):
        header = headers[w["window_id"]] = make_header(m, w, model)
        for frame in raw.frames:
            for view in crop_views():
                path = checkpoint_path(root, w, frame.frame_index, view)
                if path.exists():
                    cached[(w["window_id"], frame.frame_index, view["ordinal"])] = read_checkpoint(path, header, frame.frame_index, view, raw, model)
        final = output_path(root, w)
        if final.exists():
            value = validate_output(read_json(final), header, raw)
            for f in value["frames"]:
                for result in f["views"]:
                    if cached.get((w["window_id"], f["frame_index"], result["view"]["ordinal"])) != result:
                        raise ValueError("Final output differs from its view checkpoints")
    adapter, calls = None, 0
    for w, raw in zip(p["windows"], runs):
        header = headers[w["window_id"]]
        wanted = {f.frame_index for f in raw.frames if any((w["window_id"], f.frame_index, v["ordinal"]) not in cached for v in crop_views())}
        decoded = set()
        for frame, pixels in frames_from_video(root, raw, wanted) if wanted else ():
            if frame not in wanted or frame in decoded or pixels.shape != (1080, 1920, 3):
                raise ValueError("Unexpected source decode")
            decoded.add(frame)
            for view in crop_views():
                key = (w["window_id"], frame, view["ordinal"])
                if key in cached:
                    continue
                if adapter is None:
                    adapter = create_adapter(weights, model.export_confidence_floor)
                x0, y0, x1, y1 = view["xyxy_half_open_px"]
                synchronize(reset_peak=True)
                start = time.perf_counter()
                candidates = adapter.predict_frame(pixels[y0:y1, x0:x1].copy())
                synchronize()
                result = {"view": view, "candidates": [c.to_dict() for c in candidates],
                          "elapsed_seconds": time.perf_counter() - start, "cuda_peak_allocated_bytes": peak_memory()}
                validate_local(result["candidates"], view, raw.source_video, model)
                value = {"header": header, "frame_index": frame, "result": result}
                value["content_sha256"] = canonical_sha256(value)
                persist_once(checkpoint_path(root, w, frame, view), value)
                cached[key] = result
                calls += 1
        if decoded != wanted:
            raise ValueError("Incomplete source frames; completed crop checkpoints preserved")
        frames = [make_frame(f.frame_index, [cached[(w["window_id"], f.frame_index, v["ordinal"])] for v in crop_views()], raw.source_video, model) for f in raw.frames]
        value = make_output(header, frames)
        validate_output(value, header, raw)
        persist_once(output_path(root, w), value)
    unchanged(root, manifest_path, m, commit)
    preflight(root, manifest_path)
    weights_after, model_after = inspect_runtime(baseline, commit)
    if weights_after != weights or model_after != model:
        raise ValueError("Runtime/weights changed during execution")
    return {"new_model_calls": calls, "total_completed_model_calls": len(cached), "windows": 6,
            "outputs": [file_binding(root, output_path(root, w)) for w in p["windows"]], "commit": commit}


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
