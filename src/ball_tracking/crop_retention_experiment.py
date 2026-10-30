"""Approved, immutable retention execution with saved-control reuse only."""
from __future__ import annotations

import argparse
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

from .crop_retention import RankingConfig, iter_ranked_frames, summarize_frame
from .crop_retention_resources import BudgetJournal, run_supervised, wait_for_supervisor
from .detections import BallDetectionRun
from .development_experiments import canonical_sha256, read_json, safe_path, sha256_file
from .tiled_candidates import combine_views

EXPERIMENT_ID = "rfdetr_medium_crop_candidate_retention_v0_1"
OUTPUT_ROOT = f"data/outputs/ball_tracking/crop_candidate_retention/{EXPERIMENT_ID}"
PROPOSAL_SHA256 = "7640784e2a64e81a2064ebb40cd4d1c77366076e5e78a2c19f8f5fc28e29fe1b"
APPROVAL_SHA256 = "dcc52439d7e08f17c45f10811b4eb39b34577c23a0a3291aa347246ef6f24219"
BASE_COMMIT = "9fe6a1ef86d23391c64b7d5b16198ad7bb005c25"
RF_COMMIT = "1a9479f83a1766d8979fad07c604bc686d3c52c6"
MOTION_COMMIT = "2274ab6097cd841421e2b606f723b047cd7dc62b"
MANIFEST_FIELDS = {"schema_version", "experiment_id", "proposal", "authorization", "output_root",
                   "implementation_validation", "selected_method", "selected_operating_point", "quality_gate"}


def _require(value, message):
    if not value:
        raise ValueError(message)


def _git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def verify_binding(root, value):
    path = safe_path(Path(root).resolve(), value["path"])
    _require(path.is_file() and sha256_file(path) == value["sha256"], "Changed bound file: " + value["path"])
    return path


def file_binding(root, path):
    path = Path(path).resolve()
    return {"path": path.relative_to(Path(root).resolve()).as_posix(), "sha256": sha256_file(path)}


def persist_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def _clean_checkpoint(root):
    _require(_git(root, "branch", "--show-current") == "codex/ball-detector-baseline", "Unexpected execution branch")
    _require(not _git(root, "status", "--porcelain=v1"), "Real retention stages require a clean committed checkpoint")
    _require(not _git(root, "diff", "--cached", "--name-only"), "Index must be empty")
    _require(subprocess.run(["git", "merge-base", "--is-ancestor", BASE_COMMIT, "HEAD"], cwd=root).returncode == 0,
             "Execution HEAD does not descend from the proposal checkpoint")
    return _git(root, "rev-parse", "HEAD")


def _metadata(root, path, require_clean):
    root, path = Path(root).resolve(), Path(path).resolve()
    safe_path(root, path.relative_to(root).as_posix(), "configs/ball_tracking/crop_retention_experiments")
    # Check this before any saved data or labels are opened.
    commit = _clean_checkpoint(root) if require_clean else _git(root, "rev-parse", "HEAD")
    m = read_json(path)
    _require(set(m) == MANIFEST_FIELDS and m["schema_version"] == "ball_crop_candidate_retention_experiment/v0.1"
             and m["experiment_id"] == EXPERIMENT_ID and m["output_root"] == OUTPUT_ROOT,
             "Unsupported retention manifest")
    _require(all(m[k] is None for k in ("selected_method", "selected_operating_point", "quality_gate")),
             "No method or quality selection is authorized")
    _require(m["proposal"]["sha256"] == PROPOSAL_SHA256 and m["authorization"]["sha256"] == APPROVAL_SHA256,
             "Manifest is not bound to Ryan's exact approved scope")
    p = read_json(verify_binding(root, m["proposal"]))
    a = read_json(verify_binding(root, m["authorization"]))
    verify_binding(root, p["design"])
    _require(a["proposal"] == m["proposal"] and a["design"] == p["design"] and a["approved_by"] == "ryan"
             and a["implementation_authorized"] is True and a["execution_authorized"] is True
             and a["git_mutations_authorized"] is False and a["training_authorized"] is False,
             "Missing exact retention authorization")
    _require(p["proposed_output_root"].rstrip("/") == OUTPUT_ROOT and len(p["new_selection_units"]) == 24,
             "Frozen retention scope mismatch")
    _embargoes(root, p)
    target = safe_path(root, OUTPUT_ROOT + "/ignore_check.json", OUTPUT_ROOT)
    _require(subprocess.run(["git", "check-ignore", "-q", "--", str(target.relative_to(root))], cwd=root).returncode == 0,
             "Retention outputs must be ignored by Git")
    if require_clean:
        _validate_implementation(root, m)
        required = [path, root/m["proposal"]["path"], root/m["authorization"]["path"], root/p["design"]["path"],
                    *Path(__file__).parent.glob("crop_retention*.py"), * (root/"tests").glob("test_ball_crop_retention*.py")]
        for file in required:
            _git(root, "ls-files", "--error-unmatch", "--", file.relative_to(root).as_posix())
    return {"root": root, "manifest_path": path, "manifest": m, "proposal": p, "approval": a,
            "commit": commit, "spec_sha256": canonical_sha256(m), "output_root": root/OUTPUT_ROOT}


def _embargoes(root, p):
    _require(len(p["original_embargo_paths"]) == 9 and len(p["sealed_holdouts_metadata_only"]) == 3,
             "Protected scope changed")
    for name in p["original_embargo_paths"]:
        _require(not safe_path(root, name).exists(), "Original prediction embargo violated")


def _validate_implementation(root, m):
    b = m["implementation_validation"]
    _require(isinstance(b, dict), "Implementation validation is not complete")
    evidence = read_json(verify_binding(root, b))
    _require(evidence["focused_tests_passed"] is True and evidence["full_suite_passed"] is True
             and evidence["synthetic_dense_400_by_25_passed"] is True
             and evidence["synthetic_sparse_400_by_25_passed"] is True
             and evidence["resource_abort_and_resume_tests_passed"] is True,
             "Required synthetic/full/resource validation is incomplete")
    _require(evidence["proposal_sha256"] == PROPOSAL_SHA256, "Validation is for another proposal")
    required = {p.relative_to(root).as_posix() for folder in ("src", "tests")
                for p in (root/folder).rglob("*.py")}
    required.add("requirements.txt")
    bindings = evidence["source_bindings"]
    _require(required <= {b["path"] for b in bindings}, "Validation omits production dependencies or test inputs")
    for binding in bindings + evidence["evidence_bindings"]:
        verify_binding(root, binding)


def _candidate_input(root, window):
    output = read_json(verify_binding(root, window["crop_candidates"]))
    _require(output["schema_version"] == "ball_tiled_candidates/v0.1"
             and output["content_sha256"] == canonical_sha256({"header": output["header"], "frames": output["frames"]}),
             "Crop candidate content contract mismatch")
    model = dict(output["header"]["per_view_model_provenance"])
    _require(model["code_commit"] == RF_COMMIT and model["export_confidence_floor"] == .01,
             "Crop inference provenance changed")
    model.update(tiling_enabled=True, postprocessing_description=
                 "Four fixed overlapping crop union; global coordinate translation; all duplicates retained; no temporal filtering")
    original = output["header"]["window"]
    _require(all(original[key] == value for key, value in window.items() if key != "crop_candidates"),
             "Crop header differs from the approved window/source")
    payload = {"schema_version": "0.1", "detection_run_id": original["detection_run_id"],
               "annotation_set_id": window["annotation_set_id"], "possession_id": window["possession_id"],
               "source_video": window["source_video"],
               "window": {k: window[k] for k in ("start_frame_index", "end_frame_index")},
               "model_provenance": model,
               "frames": [{"frame_index": f["frame_index"], "inference_status": "completed", "failure_reason": None,
                           "detections": [c["detection"] for c in f["candidates"]]} for f in output["frames"]]}
    run = BallDetectionRun.from_mapping(payload)
    _require(len(run.frames) == 25 and len(output["frames"]) == 25, "Expected complete 25-frame input")
    for stored, frame in zip(output["frames"], run.frames):
        _require(stored["model_calls"] == 4 and stored["frame_index"] == frame.frame_index
                 and combine_views(stored["views"], run.source_video, run.model_provenance) == stored["candidates"],
                 "Crop-local/global candidate mapping changed")
    return run, output["content_sha256"]


def load_saved_control(root, record, run=None):
    """Verify original bytes/content/provenance without rederiving selection."""
    wrapped = read_json(verify_binding(root, record["file"]))
    obs = wrapped["observations"]
    _require(canonical_sha256(obs) == record["observations_content_sha256"]
             and obs["config"] == record["config"] and obs["variant_id"] == record["variant_id"]
             and obs["ranking_code_commit"] == record["original_selection_commit"] == MOTION_COMMIT
             and obs["detector_code_commit"] == record["original_detector_commit"] == RF_COMMIT,
             "Saved control identity/provenance mismatch")
    if run is not None:
        _require(obs["input_candidate_content_sha256"] == canonical_sha256(run.to_dict())
                 and obs["source_video"] == run.source_video.to_dict()
                 and obs["window"] == run.window.to_dict() and obs["possession_id"] == run.possession_id
                 and [f["frame_index"] for f in obs["frames"]] == [f.frame_index for f in run.frames],
                 "Saved control differs from the frozen candidate input")
    return obs


def _resolve(root, binding, cache):
    key = binding["path"]
    if key not in cache:
        cache[key] = read_json(verify_binding(root, binding))
    value = cache[key]
    for token in binding["json_pointer"].split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def load_context(root, manifest_path, *, require_clean=True, verify_review_inputs=False, verify_scoring_inputs=False):
    context = _metadata(root, manifest_path, require_clean)
    root, p = context["root"], context["proposal"]
    inputs = {w["window_id"]: _candidate_input(root, w) for w in p["windows"]}
    context["inputs"] = inputs
    for record in p["saved_control_outputs"]:
        load_saved_control(root, record, inputs[record["window_id"]][0])
    for alias in p["higher_confidence_structural_equivalence"]:
        run = inputs[alias["window_id"]][0]
        proof = [{"frame_index": f.frame_index, "qualified_candidate_count":
                  sum(c.confidence >= alias["confidence_threshold"] for c in f.detections)} for f in run.frames]
        _require(proof == alias["per_frame_count_proof"] and max(r["qualified_candidate_count"] for r in proof) <= 20,
                 "Higher-confidence equivalence no longer holds")
    if verify_scoring_inputs:
        for item in p["scoring_labels"]:
            verify_binding(root, item["annotation"])
        cache = {}
        for key, digest in (("saved_report_references", "report_content_sha256"),
                            ("saved_aggregate_references", "aggregate_content_sha256")):
            for item in p[key]:
                _require(canonical_sha256(_resolve(root, item["source"], cache)) == item[digest],
                         "Saved scoring pointer/content changed")
    if verify_review_inputs:
        for item in p["saved_source_pngs"]:
            verify_binding(root, item["source_png"])
    return context


def _config(unit):
    value = unit["config"]
    _require(value["confidence_threshold"] == .01 and value["candidate_cap"] is None
             and value["retention_policy"] == "all_threshold_qualified_saved_candidates", "Undeclared real selection")
    return RankingConfig.from_mapping({k: v for k, v in value.items() if k != "retention_policy"})


def unit_directory(context, unit):
    _require(unit in context["proposal"]["new_selection_units"], "Unknown retention unit")
    return context["output_root"] / "observations" / unit["window_id"] / _config(unit).variant_id


def _completed_bindings(context):
    target = context["output_root"]
    journal = BudgetJournal(target, context["proposal"]["resource_limits"])
    result = {}
    for event in journal.events:
        if event["kind"] == "finished" and event["success"]:
            b = event.get("worker_result")
            if b is None:
                continue
            path = safe_path(target, b["path"])
            _require(sha256_file(path) == b["sha256"], "Completed worker receipt changed")
            value = read_json(path)
            _require(value["spec_sha256"] == context["spec_sha256"] and value["commit"] == context["commit"],
                     "Completed worker belongs to another source checkpoint")
            for binding in value["artifacts"]:
                old = result.setdefault(binding["path"], binding["sha256"])
                _require(old == binding["sha256"], "Conflicting completed artifact receipts")
                verify_binding(context["root"], binding)
    return result


def load_new_observations(root, context, unit):
    return _validate_new_observations(root, context, unit, require_completion=True)


def _validate_new_observations(root, context, unit, *, require_completion):
    folder = unit_directory(context, unit)
    path = folder / "manifest.json"
    if require_completion:
        completed = _completed_bindings(context)
        relative = path.relative_to(Path(root).resolve()).as_posix()
        _require(relative in completed and sha256_file(path) == completed[relative],
                 "Selection lacks a successful resource-bound completion receipt")
    value = read_json(path)
    obs = value["observations"]
    run, digest = context["inputs"][unit["window_id"]]
    _require(value["experiment_spec_sha256"] == context["spec_sha256"]
             and value["crop_content_sha256"] == digest
             and value["input_crop_file"] == next(w["crop_candidates"] for w in context["proposal"]["windows"] if w["window_id"] == unit["window_id"])
             and value["observations_content_sha256"] == canonical_sha256(obs)
             and obs["ranking_code_commit"] == context["commit"]
             and obs["detector_code_commit"] == RF_COMMIT
             and obs["config"] == unit["config"] and obs["variant_id"] == _config(unit).variant_id
             and obs["input_candidate_content_sha256"] == canonical_sha256(run.to_dict()),
             "New retention output provenance changed")
    _require([f["frame_index"] for f in obs["frames"]] == [f.frame_index for f in run.frames], "Incomplete selection")
    _require(obs["source_video"] == run.source_video.to_dict() and obs["window"] == run.window.to_dict()
             and obs["possession_id"] == run.possession_id, "New output source/window mismatch")
    expected_files = {"manifest.json"}
    for frame, original in zip(obs["frames"], run.frames):
        b = frame["trace_binding"]
        file = safe_path(Path(root).resolve(), b["path"], folder.relative_to(root).as_posix())
        _require(sha256_file(file) == b["sha256"], "Lossless selection trace changed")
        expected_files.add(file.relative_to(folder).as_posix())
        _require([d["candidate_index"] for d in frame["candidate_decisions"]] == [d.candidate_index for d in original.detections],
                 "Original candidate decision inventory changed")
        candidates = {d.candidate_index: d for d in original.detections}
        emitted = frame["emitted_candidate_indices"]
        winner = frame["ranking"]["winner"]["endpoint"]
        expected = [winner[1]] if winner is not None and winner[0] == original.frame_index else []
        _require(emitted == expected and len(emitted) <= 1 and all(i in candidates for i in emitted), "Invalid emission")
        _require(all(d["disposition"] == ("below_threshold" if candidates[d["candidate_index"]].confidence < .01
                                         else "emitted" if d["candidate_index"] in emitted else "eligible_not_emitted")
                     for d in frame["candidate_decisions"]), "Unexpected confidence/cap decision")
    _require({p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()} == expected_files,
             "Unexpected or incomplete selection files")
    return obs


def read_trace(root, frame):
    b = frame["trace_binding"]
    path = verify_binding(root, b)
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        full = json.load(stream)
    compact = summarize_frame(full)
    _require(compact == {k: v for k, v in frame.items() if k != "trace_binding"}, "Trace and compact observation disagree")
    return full


def write_selection(root, context, unit):
    target = unit_directory(context, unit)
    _require(not target.exists(), "Selection output already exists; verify and reuse it")
    run, digest = context["inputs"][unit["window_id"]]
    config = _config(unit)
    pending = context["output_root"] / ".pending_selection" / (config.variant_id + "_" + uuid.uuid4().hex)
    pending.mkdir(parents=True, exist_ok=False)
    frames = []
    iterator = iter_ranked_frames(run, config)
    for full in iterator:
        name = f"frame_{full['frame_index']:06d}.json.gz"
        # Full precision JSON and all edges are retained; compression is lossless.
        payload = json.dumps(full, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
        packed = gzip.compress(payload, compresslevel=1, mtime=0)
        del payload
        with (pending / name).open("xb") as stream:
            stream.write(packed)
        del packed
        compact = summarize_frame(full)
        compact["trace_binding"] = {"path": (target/name).relative_to(root).as_posix(),
                                    "sha256": sha256_file(pending/name)}
        frames.append(compact)
        del full
    obs = {"schema_version": "ball_crop_retention_observations/v0.1", "variant_id": config.variant_id,
           "config": unit["config"], "ranking_code_commit": context["commit"], "detector_code_commit": RF_COMMIT,
           "input_candidate_content_sha256": canonical_sha256(run.to_dict()),
           "source_video": run.source_video.to_dict(), "window": run.window.to_dict(),
           "possession_id": run.possession_id, "frames": frames, "selected_method": None,
           "selected_operating_point": None, "quality_gate": None,
           "score_semantics": "Uncalibrated original-confidence path score; no identity labels or coordinate correction"}
    value = {"schema_version": "ball_crop_retention_output/v0.1", "experiment_spec_sha256": context["spec_sha256"],
             "input_crop_file": next(w["crop_candidates"] for w in context["proposal"]["windows"] if w["window_id"] == unit["window_id"]),
             "crop_content_sha256": digest, "observations": obs, "observations_content_sha256": canonical_sha256(obs),
             "resource_attempt_id": os.environ.get("BALL_RETENTION_ATTEMPT_ID")}
    persist_new(pending/"manifest.json", value)
    _require(len(frames) == len(run.frames), "Incomplete selection trace")
    target.parent.mkdir(parents=True, exist_ok=True)
    pending.rename(target)
    checked = _validate_new_observations(root, context, unit, require_completion=False)
    for frame in checked["frames"]:
        # Decode each lossless shard once before publication is marked successful.
        # This verifies serialization, never rederives selection.
        read_trace(root, frame)
    return file_binding(root, target/"manifest.json")


def _unchanged(context):
    _require(_clean_checkpoint(context["root"]) == context["commit"], "Execution checkpoint changed during stage")
    _require(read_json(context["manifest_path"]) == context["manifest"], "Manifest changed during stage")
    verify_binding(context["root"], context["manifest"]["proposal"])
    verify_binding(context["root"], context["manifest"]["authorization"])
    p = context["proposal"]
    for window in p["windows"]:
        verify_binding(context["root"], window["crop_candidates"])
    for record in p["saved_control_outputs"]:
        verify_binding(context["root"], record["file"])
    _embargoes(context["root"], context["proposal"])


def _worker(root, manifest_path, stage, key):
    wait_for_supervisor()
    scope = key if stage == "preflight" else stage
    context = load_context(root, manifest_path, verify_review_inputs=scope in ("render", "review-final"),
                           verify_scoring_inputs=scope != "select")
    p, output = context["proposal"], context["output_root"]
    artifacts = []
    if stage == "preflight":
        completed = _completed_bindings(context)
        for unit in p["new_selection_units"]:
            if unit_directory(context, unit).exists():
                load_new_observations(root, context, unit)
        from .crop_retention_evaluation import load_window_score
        from .crop_retention_review import prepare_window, validate_review_bundle
        for window in p["windows"]:
            name = window["window_id"]
            score = output/"evaluation/windows"/f"{name}.json"
            if score.exists() and scope != "select":
                _require(score.relative_to(root).as_posix() in completed,
                         "Scoring output lacks successful resource-bound completion")
                load_window_score(root, context, name)
            review = output/"review/windows"/name
            if review.exists() and scope in ("render", "review-final"):
                _require((review/"manifest.json").relative_to(root).as_posix() in completed,
                         "Review output lacks successful resource-bound completion")
                validate_review_bundle(root, review, prepare_window(root, context, name).header)
    elif stage == "select":
        unit = next(u for u in p["new_selection_units"] if u["comparison_unit_id"] == key)
        if unit_directory(context, unit).exists():
            load_new_observations(root, context, unit)
            artifacts.append(file_binding(root, unit_directory(context, unit)/"manifest.json"))
        else:
            artifacts.append(write_selection(root, context, unit))
    elif stage == "score":
        from .crop_retention_evaluation import score_window
        target = output/"evaluation/windows"
        score_window(root, context, key, target)
        artifacts.append(file_binding(root, target/f"{key}.json"))
    elif stage == "score-final":
        from .crop_retention_evaluation import finalize
        windows = [output/"evaluation/windows"/f"{w['window_id']}.json" for w in p["windows"]]
        finalize(root, context, windows, output/"evaluation")
        artifacts.extend(file_binding(root, f) for f in sorted((output/"evaluation").glob("*.json")))
    elif stage == "render":
        from .crop_retention_review import render_window
        target = output/"review/windows"
        render_window(root, context, key, target/key)
        artifacts.append(file_binding(root, target/key/"manifest.json"))
    elif stage == "review-final":
        from .crop_retention_review import finalize_review
        finalize_review(root, context)
        artifacts.append(file_binding(root, output/"review/manifest.json"))
    else:
        raise ValueError("Unknown worker stage")
    _unchanged(context)
    result = {"stage": stage, "key": key, "spec_sha256": context["spec_sha256"],
              "commit": context["commit"], "artifacts": artifacts}
    target = safe_path(context["output_root"], Path(os.environ["BALL_RETENTION_RESULT_PATH"]).relative_to(context["output_root"]).as_posix())
    persist_new(target, result)
    return result


def run_experiment(root, manifest_path, *, stage="select", dry_run=False):
    root, manifest_path = Path(root).resolve(), Path(manifest_path).resolve()
    if dry_run:
        context = load_context(root, manifest_path, require_clean=False)
        return {"dry_run": True, "source_frames": 150, "new_units": 24, "saved_controls": 126,
                "equivalence_units": 48, "new_model_calls": 0, "selection_executed": False,
                "execution_requires_clean_tested_commit": True, "proposal_sha256": PROPOSAL_SHA256,
                "input_window_count": len(context["inputs"])}
    _require(stage in ("select", "score", "render"), "Unknown retention stage")
    context = _metadata(root, manifest_path, True)
    p, output = context["proposal"], context["output_root"]

    def dispatch(action, key=""):
        command = [sys.executable, "-B", "-m", "src.ball_tracking.crop_retention_experiment", "--manifest",
                   str(manifest_path), "--repository-root", str(root), "--worker-stage", action, "--unit-key", key]
        return run_supervised(output, action+":"+key, command, p["resource_limits"], cwd=root,
                              selection_unit=action == "select", require_result=True)

    receipts = [dispatch("preflight", stage)]
    if stage == "select":
        for unit in p["new_selection_units"]:
            # Even reused units are verified by a supervised read-only worker.
            receipts.append(dispatch("select", unit["comparison_unit_id"]))
    elif stage == "score":
        for window in p["windows"]:
            receipts.append(dispatch("score", window["window_id"]))
        receipts.append(dispatch("score-final"))
    else:
        for window in p["windows"]:
            receipts.append(dispatch("render", window["window_id"]))
        receipts.append(dispatch("review-final"))
    return {"stage": stage, "successful_workers": len(receipts), "commit": context["commit"],
            "new_model_calls": 0, "training_executed": False, "output_root": str(output)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--stage", choices=("select", "score", "render"), default="select")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--worker-stage", choices=("preflight", "select", "score", "score-final", "render", "review-final"), help=argparse.SUPPRESS)
    parser.add_argument("--unit-key", default="", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = args.repository_root.resolve()
    path = (root/args.manifest).resolve()
    result = (_worker(root, path, args.worker_stage, args.unit_key) if args.worker_stage
              else run_experiment(root, path, stage=args.stage, dry_run=args.dry_run))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
