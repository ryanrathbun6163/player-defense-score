"""Guarded manifest, authorization, and resumable runner for saved detections.

The association runner opens no annotation JSON, video, player, or court data.
Scoring and rendering are separate stages. No detector is constructed here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import asdict
from pathlib import Path

from .detections import load_detection_run
from .detector_experiments import load_detector_experiment
from .development_experiments import (
    bound_file, canonical_sha256, closed, read_json, safe_path, sha256_file,
)
from .temporal_association import RADII, associate, experiment_grid

SCHEMA = "ball_temporal_experiment/v0.1"
EXPERIMENT_ID = "rfdetr_medium_temporal_association_v0_1"
OUTPUT_ROOT = f"data/outputs/ball_tracking/temporal_association/{EXPERIMENT_ID}"
FIELDS = {"schema_version", "experiment_id", "design", "baseline", "visual_review",
          "windows", "scoring_labels", "variants", "localization_radii_px", "output_root",
          "authorization", "selected_operating_point", "quality_gate"}


def spec_digest(manifest):
    return canonical_sha256({k: v for k, v in manifest.items() if k != "authorization"})


def file_binding(root, path):
    path = Path(path)
    return {"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path)}


def prepare_manifest_payloads(root, baseline_path, review_path, design_path,
                              approval_path, statement, recorded_at_utc):
    """Prepare reviewable metadata; caller persists it without Git mutations.

    This preparation may hash reviewed labels. Runtime association never does.
    The caller supplies the actual user authorization statement and receipt time.
    """
    baseline = load_detector_experiment(baseline_path)
    reviewed = read_json(review_path)["bound_evidence"]["windows"]
    windows, labels = [], []
    for w in baseline.windows:
        r = next(item for item in reviewed if item["window_id"] == w.window_id)
        windows.append({"window_id": w.window_id, "purpose": w.selection_purpose,
                        "possession_id": w.possession_id, "source_video": w.source_video.to_dict(),
                        "start_frame_index": w.start_frame_index, "end_frame_index": w.end_frame_index,
                        "detection_run_id": w.detection_run_id, "annotation_set_id": w.annotation_set_id,
                        "detection": r["detection"]})
        labels.append({"window_id": w.window_id,
                       "annotation": file_binding(root, root / f"configs/ball_tracking/annotations/{w.annotation_set_id}.json")})
    m = {"schema_version": SCHEMA, "experiment_id": EXPERIMENT_ID,
         "design": file_binding(root, design_path), "baseline": file_binding(root, baseline_path),
         "visual_review": file_binding(root, review_path), "windows": windows, "scoring_labels": labels,
         "variants": [asdict(c) for c in experiment_grid()], "localization_radii_px": list(RADII),
         "output_root": OUTPUT_ROOT, "authorization": None,
         "selected_operating_point": None, "quality_gate": None}
    auth = {"schema_version": "ball_temporal_experiment_approval/v0.1",
            "experiment_spec_sha256": spec_digest(m), "design": m["design"],
            "approved_by": "ryan", "statement": statement, "recorded_at_utc": recorded_at_utc,
            "timestamp_semantics": "Receipt creation time; authorization is the user's response to the linked temporal experiment design.",
            "scope": "saved_six_development_windows_all_declared_variants", "git_mutations_authorized": False}
    auth_bytes = (json.dumps(auth, indent=2, allow_nan=False) + "\n").encode("utf-8")
    m["authorization"] = {"path": approval_path.relative_to(root).as_posix(),
                          "sha256": hashlib.sha256(auth_bytes).hexdigest()}
    return m, auth


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def clean_commit(root):
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root.resolve():
        raise ValueError("Wrong repository root")
    if git(root, "branch", "--show-current") == "main":
        raise ValueError("Experiment requires a feature branch")
    if git(root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Execution requires a clean committed checkpoint; preserve current work")
    return git(root, "rev-parse", "HEAD")


def _tracked(root, path):
    git(root, "ls-files", "--error-unmatch", "--", Path(path).relative_to(root).as_posix())


def load_manifest(root, path):
    """Read bindings, never label contents; exactly six inherited development windows."""
    root, path = root.resolve(), path.resolve()
    relative = path.relative_to(root).as_posix()
    safe_path(root, relative, "configs/ball_tracking/temporal_experiments")
    m = closed(read_json(path), FIELDS, "temporal manifest")
    if (m["schema_version"] != SCHEMA or m["experiment_id"] != EXPERIMENT_ID
            or m["output_root"] != OUTPUT_ROOT
            or canonical_sha256(m["variants"]) != canonical_sha256([asdict(c) for c in experiment_grid()])
            or m["localization_radii_px"] != list(RADII)
            or m["selected_operating_point"] is not None or m["quality_gate"] is not None):
        raise ValueError("Temporal experiment settings differ from the declared contract")
    design = closed(m["design"], {"path", "sha256"}, "design")
    design_path = safe_path(root, design["path"], "docs")
    if sha256_file(design_path) != design["sha256"]:
        raise ValueError("Design binding mismatch")
    baseline_path = bound_file(root, m["baseline"], "configs/ball_tracking/experiments")
    baseline = load_detector_experiment(baseline_path)
    if baseline.schema_version != "ball_detector_experiment/v0.2":
        raise ValueError("Expected approved versioned development baseline")
    review_path = bound_file(root, m["visual_review"], "configs/ball_tracking/reviews")
    review = read_json(review_path)
    if (review.get("schema_version") != "ball_detection_development_visual_review_record/v0.1"
            or review.get("experiment_id") != baseline.experiment_id
            or review.get("human_visual_approval", {}).get("status") != "approved"
            or review.get("human_visual_approval", {}).get("approved_by") != "ryan"
            or review["bound_evidence"]["experiment_manifest"] != m["baseline"]):
        raise ValueError("Missing bound human visual approval")
    reviewed = review["bound_evidence"]["windows"]
    expected = []
    for w in baseline.windows:
        matches = [r for r in reviewed if r["window_id"] == w.window_id]
        if len(matches) != 1:
            raise ValueError("Review window inventory mismatch")
        r = matches[0]
        if (r["purpose"] != w.selection_purpose or r["possession_id"] != w.possession_id
                or r["start_frame_index"] != w.start_frame_index
                or r["end_frame_index"] != w.end_frame_index
                or r["detection"]["path"] != w.output_path.as_posix()):
            raise ValueError("Review window identity mismatch")
        expected.append({"window_id": w.window_id, "purpose": w.selection_purpose,
                         "possession_id": w.possession_id, "source_video": w.source_video.to_dict(),
                         "start_frame_index": w.start_frame_index, "end_frame_index": w.end_frame_index,
                         "detection_run_id": w.detection_run_id, "annotation_set_id": w.annotation_set_id,
                         "detection": r["detection"]})
    if len(reviewed) != 6 or m["windows"] != expected:
        raise ValueError("Only the exact six reviewed development windows are allowed")
    # Label byte bindings are checked only during scoring, not association.
    labels = m["scoring_labels"]
    if not isinstance(labels, list) or len(labels) != 6:
        raise ValueError("Expected six scoring-label bindings")
    for item, window in zip(labels, expected):
        closed(item, {"window_id", "annotation"}, "scoring label")
        record = closed(item["annotation"], {"path", "sha256"}, "annotation binding")
        if (item["window_id"] != window["window_id"]
                or record["path"] != f"configs/ball_tracking/annotations/{window['annotation_set_id']}.json"):
            raise ValueError("Scoring annotation identity mismatch")
        from .development_experiments import require_digest
        require_digest(record["sha256"], "annotation")
    parent = read_json(bound_file(root, baseline.payload["parent_experiment"], "configs/ball_tracking/experiments"))
    embargoes = [w for w in parent["windows"] if w["execution_status"] == "annotation_pending_prediction_embargo"]
    if len(embargoes) != 9 or any(safe_path(root, w["output_path"]).exists() for w in embargoes):
        raise ValueError("Original prediction embargo paths must remain absent")
    auth_path = bound_file(root, m["authorization"], "configs/ball_tracking/reviews")
    auth = closed(read_json(auth_path), {"schema_version", "experiment_spec_sha256", "design",
                                      "approved_by", "statement", "recorded_at_utc",
                                      "timestamp_semantics", "scope", "git_mutations_authorized"}, "authorization")
    if (auth["schema_version"] != "ball_temporal_experiment_approval/v0.1"
            or auth["experiment_spec_sha256"] != spec_digest(m) or auth["design"] != m["design"]
            or auth["approved_by"] != "ryan" or not isinstance(auth["statement"], str)
            or not auth["statement"].strip() or auth["git_mutations_authorized"] is not False
            or auth["scope"] != "saved_six_development_windows_all_declared_variants"):
        raise ValueError("Missing exact-scope experiment authorization")
    return m


def load_inputs(root, manifest):
    runs = []
    for w in manifest["windows"]:
        path = bound_file(root, w["detection"], "data/outputs/ball_tracking/detections")
        run = load_detection_run(path)
        if (run.detection_run_id != w["detection_run_id"]
                or run.annotation_set_id != w["annotation_set_id"]
                or run.possession_id != w["possession_id"] or run.source_video.to_dict() != w["source_video"]
                or run.window.to_dict() != {k: w[k] for k in ("start_frame_index", "end_frame_index")}
                or any(f.inference_status != "completed" for f in run.frames)):
            raise ValueError("Detection input identity/completeness mismatch")
        runs.append(run)
    return runs


def persist_once(path, payload):
    """Atomic exclusive creation. Exact deterministic resume; never overwrite."""
    content = (json.dumps(payload, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"Refusing changed existing output: {path}")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".pending_")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)  # Fails if another writer already owns the output.
    finally:
        Path(temporary).unlink(missing_ok=True)
    return True


def output_path(root, manifest, window, config):
    return safe_path(root, f"{manifest['output_root']}/{window['window_id']}/{config.variant_id}.json", OUTPUT_ROOT)


def preflight(root, manifest_path, *, require_clean=True):
    manifest = load_manifest(root, manifest_path)
    if require_clean:
        commit = clean_commit(root)
        for name in [manifest_path, *(root / manifest[k]["path"] for k in ("design", "baseline", "visual_review", "authorization")),
                     *(root / l["annotation"]["path"] for l in manifest["scoring_labels"])]:
            _tracked(root, name)
        for path in Path(__file__).parent.glob("temporal_*.py"):
            _tracked(root, path)
    else:
        commit = git(root, "rev-parse", "HEAD")
    for w in manifest["windows"]:
        for config in experiment_grid():
            path = output_path(root, manifest, w, config)
            result = subprocess.run(["git", "check-ignore", "-q", "--", path.relative_to(root).as_posix()], cwd=root)
            if result.returncode != 0:
                raise ValueError("Generated observations must be Git-ignored")
    return manifest, load_inputs(root, manifest), commit


def run_experiment(root, manifest_path, *, dry_run=False):
    manifest, runs, commit = preflight(root, manifest_path, require_clean=not dry_run)
    if dry_run:
        return {"dry_run": True, "windows": len(runs), "variants": len(experiment_grid()),
                "frames": sum(len(r.frames) for r in runs), "execution_requires_clean_commit": True}
    created = 0
    for window, run in zip(manifest["windows"], runs):
        for config in experiment_grid():
            payload = associate(run, config, commit)
            envelope = {"experiment_spec_sha256": spec_digest(manifest),
                        "input_detection_file": window["detection"], "observations": payload}
            created += persist_once(output_path(root, manifest, window, config), envelope)
    if clean_commit(root) != commit:
        raise ValueError("Git changed during execution")
    if load_manifest(root, manifest_path) != manifest:
        raise ValueError("Manifest changed during execution")
    load_inputs(root, manifest)
    return {"created_outputs": created, "total_outputs": len(runs) * len(experiment_grid()), "commit": commit}


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
