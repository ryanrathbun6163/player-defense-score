"""Saved-data-only paired review with explicit crop inference and assembly provenance."""
from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from . import yolo_crop_review as original
from .annotations import load_annotations
from .development_experiments import bound_file, canonical_sha256, closed, read_json, require_digest, safe_path, sha256_file
from .temporal_experiment import file_binding, persist_once, spec_digest
from .tiled_candidates import crop_views
from .yolo_crop_candidates import experiment_grid

OUTPUT_ROOT = original.OUTPUT_ROOT + "/recovery_v0_2"
ORIGINAL_COMMIT = "116e3ed9cb4113521fa8c93adf4a100fea4dc0ec"
ROLE = "assembly_view_only_not_actual_inference_commit_for_all_units"
PROVENANCE_FIELDS = ("inference_inventory_sha256", "actual_inference_commits", "assembly_code_commit", "model_code_commit_role")
UNIT_BINDINGS = ("checkpoint", "attempt_start", "attempt_result", "preparation_start", "preparation_result")
UNIT_FIELDS = {"window_id", "possession_id", "frame_index", "view_id", "view_ordinal", "actual_inference_commit", *UNIT_BINDINGS}
THRESHOLDS, CONTROL_ARMS, YOLO_ARMS = original.THRESHOLDS, original.CONTROL_ARMS, original.YOLO_ARMS
TILE_WIDTH, TILE_HEIGHT, NATIVE_HEADER = original.TILE_WIDTH, original.TILE_HEIGHT, 180


def _unit_key(unit):
    return unit["window_id"], unit["frame_index"], unit["view_id"], unit["view_ordinal"]


def _window_provenance(header, window, commit):
    """Check ordered identity and the explicit meaning of the typed model commit."""
    require_digest(commit, "assembly commit", 40)
    if (header["assembly_code_commit"] != commit or header["model_code_commit_role"] != ROLE
            or header["per_view_model_provenance"]["code_commit"] != commit):
        raise ValueError("Candidate assembly/model commit role differs")
    units = header["inference_units"]
    expected = [(window["window_id"], f, v["view_id"], v["ordinal"])
                for f in range(window["start_frame_index"], window["end_frame_index"]+1) for v in crop_views()]
    if (not isinstance(units, list) or [_unit_key(u) for u in units] != expected
            or header["inference_inventory_sha256"] != canonical_sha256(units)):
        raise ValueError("Candidate inference unit identity/order/digest differs")
    for u in units:
        closed(u, UNIT_FIELDS, "review inference unit")
        for key in UNIT_BINDINGS:
            if key == "attempt_result" and u[key] is None:
                continue
            closed(u[key], {"path", "sha256"}, "unit receipt binding")
            require_digest(u[key]["sha256"], "unit receipt")
        require_digest(u["actual_inference_commit"], "actual inference commit", 40)
        if (u["possession_id"] != window["possession_id"] or type(u["frame_index"]) is not int
                or type(u["view_ordinal"]) is not int or u["actual_inference_commit"] not in {ORIGINAL_COMMIT, commit}):
            raise ValueError("Inference unit possession/commit differs")
    if header["actual_inference_commits"] != sorted({u["actual_inference_commit"] for u in units}):
        raise ValueError("Actual inference commits differ from unit inventory")
    return {"window_id": window["window_id"], **{k: header[k] for k in PROVENANCE_FIELDS}, "inference_units": units}


def _check_partition(provenances, recovery, commit):
    units = [u for p in provenances for u in p["inference_units"]]
    old = {_unit_key(u): u for u in recovery["completed_crop_units_reuse_without_inference"]}
    missing = {_unit_key(u) for u in recovery["missing_crop_units_only_allowed_new_inference"]}
    if len(old) != 175 or len(missing) != 425 or set(old) & missing or len(units) != 600:
        raise ValueError("Recovery inference partition is not exactly 175 reused plus 425 new")
    if {_unit_key(u) for u in units} != set(old) | missing:
        raise ValueError("Review units differ from exact recovery scope")
    for u in units:
        if _unit_key(u) in old:
            if any(u[k] != v for k, v in old[_unit_key(u)].items() if k in UNIT_FIELDS):
                raise ValueError("A reused unit was relabeled or rebound")
        elif u["actual_inference_commit"] != commit:
            raise ValueError("New unit does not name its actual recovery commit")


def _report(pool, run, config, observations, provenance, candidate_binding, commit):
    r = original._report(pool, run, config, observations)
    if (r["schema_version"] != "ball_yolo_crop_evaluation/v0.2"
            or observations["schema_version"] != "ball_yolo_crop_observations/v0.2"
            or "detector_code_commit" in r or "detector_code_commit" in observations
            or any(r[k] != provenance[k] or observations[k] != provenance[k] for k in PROVENANCE_FIELDS)
            or r["input_candidate_file"] != candidate_binding or observations["input_candidate_file"] != candidate_binding
            or r["ranking_code_commit"] != commit or r["evaluator_code_commit"] != commit
            or observations["ranking_code_commit"] != commit
            or r["input_model_provenance"]["code_commit"] != provenance["assembly_code_commit"]
            or r["input_candidate_content_sha256"] != canonical_sha256(run.to_dict())):
        raise ValueError("Recovery score/observation inference or assembly provenance differs")
    return r


def _prepare_review(root, path):
    from .yolo_crop_recovery_evaluation import load_scoring_pools
    from .yolo_crop_recovery import (candidate_path, load_candidate_run, load_observations,
                                     load_saved_control, output_path, preflight, unchanged)
    manifest_binding = file_binding(root, path)
    m, p, inputs, commit = preflight(root, path)
    pool_bindings = [file_binding(root, root / OUTPUT_ROOT / "evaluation" / (purpose+".json")) for purpose in p["pool_separation"]]
    pools = load_scoring_pools(root, m, p, commit, inputs=inputs)
    reused = original.load_reused_assets(root, p)
    bindings = [manifest_binding, m["recovery_proposal"], m["original_experiment"], m["authorization"], m["runtime"],
                inputs[0]["original_manifest"]["proposal"], p["reused_native_review_manifest"],
                *p["saved_control_scoring_reports"], *pool_bindings]
    windows, provenances = [], []
    for w, label, item in zip(p["windows"], p["scoring_labels"], inputs, strict=True):
        if item["window"] != w:
            raise ValueError("Preflight recovery window order differs")
        candidate_binding = file_binding(root, candidate_path(root, w))
        bindings.append(candidate_binding)
        run, payload, digest = load_candidate_run(root, m, p, w, commit, model=item["model"])
        provenance = _window_provenance(payload["header"], w, commit)
        provenance["input_candidate_file"] = candidate_binding
        provenances.append(provenance)
        bindings.extend(u[k] for u in provenance["inference_units"] for k in UNIT_BINDINGS if u[k] is not None)
        if label["window_id"] != w["window_id"] or len(run.frames) != 25:
            raise ValueError("Recovery annotation/window mismatch")
        annotations = load_annotations(bound_file(root, label["annotation"], "configs/ball_tracking/annotations"))
        if (annotations.annotation_set_id != w["annotation_set_id"] or annotations.possession_id != run.possession_id
                or annotations.source_video != run.source_video or annotations.window.start_frame_index != run.window.start_frame_index
                or annotations.window.end_frame_index != run.window.end_frame_index or annotations.window.selection_purpose != w["purpose"]):
            raise ValueError("Frozen annotation identity differs from recovery window")
        bindings.append(label["annotation"])
        observations, reports = {}, {}
        for c in (c for c in original.control_grid() if c.arm in CONTROL_ARMS and c.confidence_threshold in THRESHOLDS):
            obs = load_saved_control(root, p, w, c)
            observations[c.arm, c.confidence_threshold] = obs
            reports[c.arm, c.confidence_threshold] = original._report(pools[w["purpose"]], run, c, obs)
            suffix = f"/{w['window_id']}/{c.variant_id}.json"
            matches = [b for b in p["saved_control_outputs"] if b["path"].endswith(suffix)]
            if len(matches) != 1:
                raise ValueError("Missing/duplicate saved RF-DETR output")
            bindings.append(matches[0])
        for c in (c for c in experiment_grid() if c.confidence_threshold in THRESHOLDS):
            bindings.append(file_binding(root, output_path(root, w, c)))
            obs = load_observations(root, m, p, w, run, digest, c, commit, rederive=False)
            observations[c.arm, c.confidence_threshold] = obs
            reports[c.arm, c.confidence_threshold] = _report(pools[w["purpose"]], run, c, obs, provenance, candidate_binding, commit)
        if any(r["annotation_content_sha256"] != canonical_sha256(annotations.to_dict()) for r in reports.values()):
            raise ValueError("Scored annotations differ from frozen review labels")
        windows.append({"window": w, "run": run, "truth": annotations.annotation_by_frame(), "observations": observations,
                        "reports": reports, "inference_provenance": provenance})
    _check_partition(provenances, inputs[0]["recovery"], commit)
    header = {"schema_version": "ball_yolo_crop_visual_review/v0.2", "experiment_spec_sha256": spec_digest(m),
        "renderer_code_commit": commit, "assembly_code_commit": commit, "model_code_commit_role": ROLE,
        "window_inference_provenance": provenances,
        "actual_inference_commit_counts": dict(sorted(Counter(u["actual_inference_commit"] for pv in provenances for u in pv["inference_units"]).items())),
        "windows": p["windows"], "confidence_views": list(THRESHOLDS), "radius_px": 10.0, "layout": original.LAYOUT,
        "view_configs": [asdict(c) for c in experiment_grid() if c.confidence_threshold in THRESHOLDS],
        "native_new_arms": list(YOLO_ARMS), "native_reused_arms": list(CONTROL_ARMS), "native_header_px": NATIVE_HEADER,
        "reused_native_header_px": original.NATIVE_HEADER, "reused_assets": reused, "input_bindings": bindings,
        "source_inventory_sha256": canonical_sha256(p["inference_source_frames"]),
        "source_pixels": "exact original full-size development PNG references; no source-video decode",
        "old_controls": "unchanged native PNGs and saved observations/reports; no old execution",
        "inference_semantics": "175 original units keep their inference commit; 425 recovery units keep theirs; assembly is separate",
        "confidence_semantics": "original model scores; equal numerical thresholds are not calibrated probabilities",
        "hidden_closeup_focus": "highest accepted YOLO candidate, otherwise frame center; not ball truth",
        "selected_method": None, "selected_operating_point": None, "quality_gate": None}

    def verify():
        for b in bindings+reused:
            original._verify_binding(root, b)
        unchanged(root, path, m, commit)
    verify()
    return original.PreparedReview(header, windows, verify)


def _frame_units(provenance, frame):
    return [u for u in provenance["inference_units"] if u["frame_index"] == frame]


def render_frame(source, annotation, frame, observations, reports, native_controls, threshold, *,
                 inference_units, assembly_commit, renderer_commit):
    import cv2
    import numpy as np
    require_digest(assembly_commit, "assembly commit", 40)
    require_digest(renderer_commit, "renderer commit", 40)
    if (len(inference_units) != 4 or [u["view_id"] for u in inference_units] != [v["view_id"] for v in crop_views()]
            or any(u["frame_index"] != frame.frame_index for u in inference_units)):
        raise ValueError("Frame inference units differ from synchronized four crops")
    for u in inference_units:
        require_digest(u["actual_inference_commit"], "actual inference commit", 40)
    comparison, natives, closeups, focus = original.render_frame(source, annotation, frame, observations, reports, native_controls, threshold)
    counts = Counter(u["actual_inference_commit"] for u in inference_units)
    actual = "; ".join(f"{commit[:12]} x{count}" for commit, count in sorted(counts.items()))
    exact_crops = ", ".join(f"{u['view_id']}={u['actual_inference_commit'][:12]}" for u in inference_units)
    comparison[:TILE_HEIGHT, 2*TILE_WIDTH:] = original._tile(source, (
        f"Unmarked source | frame {frame.frame_index}", "Actual crop inference: " + actual,
        f"Assembly {assembly_commit[:12]} | rendering {renderer_commit[:12]}", "Typed model code_commit names assembly only; unit receipts preserve inference"))
    from .prepare_detection_visual_review import _put_fitted_text
    updated = []
    for old_native, name in zip(natives, ("all exported", "top one", "top twenty"), strict=True):
        body = old_native[original.NATIVE_HEADER:]
        title = np.zeros((NATIVE_HEADER, body.shape[1], 3), np.uint8)
        lines = (f"YOLO11x {name} | frame {frame.frame_index} | conf {threshold:.2f}",
            "Postprocessed best class / NMS .7 / max_det300 per crop; exported >= .01; original confidence",
            "ACTUAL CROP INFERENCE: " + exact_crops,
            f"ASSEMBLY {assembly_commit} | RENDERER {renderer_commit}",
            "ModelProvenance.code_commit is assembly-view provenance only; full checkpoint bindings are in the manifest",
            "Original 175 units preserved; remaining 425 recovered separately. No method, operating point or quality gate selected")
        for i, line in enumerate(lines):
            _put_fitted_text(title, line, (10, 24+i*28), body.shape[1]-20, .58, (235, 235, 235))
        updated.append(np.vstack((title, body)))
    return comparison, updated, closeups, focus


def validate_review_bundle(root, bundle, header):
    value = original.validate_review_bundle(root, bundle, header)
    if (header["schema_version"] != "ball_yolo_crop_visual_review/v0.2" or header["model_code_commit_role"] != ROLE
            or header["native_header_px"] != NATIVE_HEADER or header["reused_native_header_px"] != original.NATIVE_HEADER):
        raise ValueError("Recovery review schema/model role differs")
    provenance = {p["window_id"]: p for p in header["window_inference_provenance"]}
    if len(provenance) != len(header["windows"]) or set(provenance) != {w["window_id"] for w in header["windows"]}:
        raise ValueError("Recovery review is missing window inference provenance")
    for row in value["frame_evidence"]:
        p = provenance[row["window_id"]]
        if (row["inference_units"] != _frame_units(p, row["frame_index"])
                or row["inference_inventory_sha256"] != p["inference_inventory_sha256"]
                or row["assembly_code_commit"] != p["assembly_code_commit"]
                or row["renderer_code_commit"] != header["renderer_code_commit"]):
            raise ValueError("Frame evidence inference/assembly provenance differs")
    return value


def _verify_video(path):
    import cv2
    capture, count = cv2.VideoCapture(str(path)), 0
    try:
        if not capture.isOpened():
            raise ValueError("Could not decode recovery review clip")
        while True:
            ok, pixels = capture.read()
            if not ok:
                break
            if pixels.shape != (TILE_HEIGHT*3, TILE_WIDTH*3, 3):
                raise ValueError("Incorrect recovery review video dimensions")
            count += 1
        if count != 25 or capture.get(cv2.CAP_PROP_FPS) != 5.0:
            raise ValueError("Recovery review did not decode all 25 frames at 5fps")
    finally:
        capture.release()


def render_experiment(root, path):
    import cv2
    root, path = Path(root).resolve(), Path(path).resolve()
    prepared = _prepare_review(root, path)
    header = prepared.header
    bundle = safe_path(root, f"{OUTPUT_ROOT}/review/{canonical_sha256(header)[:32]}", OUTPUT_ROOT)
    if bundle.exists():
        validate_review_bundle(root, bundle, header)
        prepared.verify()
        return {"bundle": str(bundle), "reused": True}
    bundle.parent.mkdir(parents=True, exist_ok=True)
    indexed = {(r["window_id"], r["confidence_threshold"], r["frame_index"], r["arm"]): r for r in header["reused_assets"]}
    if len(indexed) != len(header["reused_assets"]):
        raise ValueError("Duplicate saved native identity")
    with tempfile.TemporaryDirectory(prefix=".pending_review_", dir=bundle.parent) as temporary:
        staging = Path(temporary).resolve()
        assets, evidence = [], []

        def add(target):
            assets.append({"path": target.relative_to(staging).as_posix(), "sha256": sha256_file(target)})

        for item in prepared.windows:
            w, run, pv = item["window"], item["run"], item["inference_provenance"]
            writers = {}
            try:
                for offset, frame in enumerate(run.frames):
                    for c in THRESHOLDS:
                        records = {a: indexed[w["window_id"], c, frame.frame_index, a] for a in (*CONTROL_ARMS, "unmarked_source")}
                        source = original._read_png(root, records["unmarked_source"])
                        if source.shape != (run.source_video.height_px, run.source_video.width_px, 3):
                            raise ValueError("Saved source dimensions differ from recovery contract")
                        controls = {a: original._read_png(root, records[a]) for a in CONTROL_ARMS}
                        observations = {a: item["observations"][a, c]["frames"][offset] for a in (*CONTROL_ARMS, *YOLO_ARMS)}
                        reports = {a: item["reports"][a, c]["frame_results"][offset] for a in observations}
                        units = _frame_units(pv, frame.frame_index)
                        comparison, native, closeups, focus = render_frame(source, item["truth"][frame.frame_index], frame,
                            observations, reports, controls, c, inference_units=units, assembly_commit=pv["assembly_code_commit"],
                            renderer_commit=header["renderer_code_commit"])
                        folder = staging / w["window_id"] / f"confidence_{c}"
                        for name, pixels in [("comparison", comparison), ("closeups", closeups),
                                             *((f"yolo_view_{i}", v) for i, v in enumerate(native))]:
                            target = folder / name / f"frame_{frame.frame_index:06d}.png"
                            target.parent.mkdir(parents=True, exist_ok=True)
                            if not cv2.imwrite(str(target), pixels):
                                raise ValueError("Could not write recovery review PNG")
                            add(target)
                        evidence.append({"window_id": w["window_id"], "confidence_threshold": c, "frame_index": frame.frame_index,
                            "source_png": records["unmarked_source"], "closeup_regions": focus, "inference_units": units,
                            "inference_inventory_sha256": pv["inference_inventory_sha256"], "assembly_code_commit": pv["assembly_code_commit"],
                            "renderer_code_commit": header["renderer_code_commit"]})
                        if c not in writers:
                            target = folder / "comparison_slow.mp4"
                            writer = cv2.VideoWriter(str(target), cv2.VideoWriter_fourcc(*"mp4v"), 5.0, (comparison.shape[1], comparison.shape[0]))
                            if not writer.isOpened():
                                writer.release()
                                raise ValueError("Could not open recovery review writer")
                            writers[c] = writer, target
                        writers[c][0].write(comparison)
            finally:
                for writer, _ in writers.values():
                    writer.release()
            if len(writers) != 2:
                raise ValueError("Incomplete recovery confidence clips")
            for _, target in writers.values():
                _verify_video(target)
                add(target)
        persist_once(staging / "manifest.json", {"header": header, "assets": assets,
            "final_frames": [{"window_id": w["window_id"], "frame_index": w["end_frame_index"]} for w in header["windows"]],
            "frame_evidence": evidence, "human_visual_review": "pending"})
        validate_review_bundle(root, staging, header)
        prepared.verify()
        staging.rename(bundle)
    return {"bundle": str(bundle), "reused": False, "assets": len(assets),
            "reused_native_assets": len(header["reused_assets"]), "human_visual_review": "pending"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.repository_root.resolve()
    print(json.dumps(render_experiment(root, (root/args.manifest).resolve()), indent=2))


if __name__ == "__main__":
    main()
