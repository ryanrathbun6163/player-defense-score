"""Execute the frozen saved-score diagnosis using JSON records and CPU arithmetic."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback


DEFAULT_SPEC = "configs/ball_tracking/proposals/saved_score_failure_study_v0_1.json"
OUTPUT_BASE = "data/outputs/ball_tracking/saved_score_failure_study_v0_1"
ROW_OUTPUTS = {
    "paired_candidates", "paired_frames", "contrast_views", "historical_appendix",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def repository_path(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Path outside repository: " + str(relative))
    return path


def binding(root, path):
    root = Path(root).resolve()
    path = repository_path(root, path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def verify_binding(root, expected):
    actual = binding(root, expected["path"])
    if any(actual[key] != expected[key] for key in actual):
        raise ValueError("Frozen binding differs: " + expected["path"])
    return actual


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def write_rows(path, rows):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False,
                                    separators=(",", ":")) + "\n")


def verify_execution(root, spec_path, freeze_path):
    spec_path = repository_path(root, spec_path)
    freeze_path = repository_path(root, freeze_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    freeze = json.loads(freeze_path.read_text(encoding="utf-8-sig"))
    if freeze.get("status") != "frozen_for_authorized_CPU_execution":
        raise ValueError("Missing concrete CPU execution freeze")
    if binding(root, spec_path) != freeze["specification"]:
        raise ValueError("Specification differs from execution freeze")
    for row in [freeze["authorization"], freeze["focused_tests"],
                *freeze["implementation"], *freeze.get("review", [])]:
        verify_binding(root, row)
    source_paths = {row["path"] for row in freeze["implementation"]}
    for filename in ("saved_score_failure_study.py", "saved_score_failure_data.py",
                     "saved_score_failure_analysis.py"):
        if "src/ball_tracking/" + filename not in source_paths:
            raise ValueError("Unbound implementation: " + filename)
    inputs = spec["input_bindings"]
    if len({row["path"] for row in inputs}) != len(inputs):
        raise ValueError("Duplicate input path in specification")
    for row in [spec["protocol"], spec["preparation_helper"],
                spec["preparation_receipt"], *inputs]:
        verify_binding(root, row)
    return spec, freeze


def require_record_only_process():
    forbidden = {"torch", "torchvision", "transformers", "cv2", "PIL"}
    loaded = forbidden.intersection(sys.modules)
    if loaded:
        raise RuntimeError("Neural/image dependency loaded: " + ",".join(sorted(loaded)))


def run(root, spec_path, freeze_path, output):
    root = Path(root).resolve()
    output = repository_path(root, output)
    allowed = repository_path(root, OUTPUT_BASE)
    if not output.is_relative_to(allowed) or output == allowed:
        raise ValueError("Output must be a new attempt inside the study directory")
    if output.exists():
        raise FileExistsError("Preserve existing attempt: " + str(output))
    started = time.perf_counter()
    spec, freeze = verify_execution(root, spec_path, freeze_path)
    require_record_only_process()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "started.json", {
        "status": "started", "at_utc": now(),
        "specification": binding(root, spec_path),
        "execution_freeze": binding(root, freeze_path),
        "scope": "Saved JSON/JSONL source/support diagnosis; original producers reused",
    })
    try:
        from .saved_score_failure_data import load_study
        from .saved_score_failure_analysis import analyze

        study = load_study(root, spec)
        require_record_only_process()
        result = analyze(study)
        require_record_only_process()
        required = {"frame_tables", "candidate_tables", "paired_candidates",
                    "paired_frames", "paired_tables", "support_tables",
                    "support_associations", "missingness", "contrast_views",
                    "contrast_tables", "historical_appendix", "case_views",
                    "candidate_numeric_support_tables", "controls", "summary"}
        if not required.issubset(result):
            raise ValueError("Incomplete endpoint outputs: " + str(required - result.keys()))
        paths = []
        for name, rows in (("joined_frames", study["frames"]),
                           ("joined_candidate_contexts", study["candidates"]),
                           ("source_choices", study["source_choices"])):
            path = output / (name + ".jsonl")
            write_rows(path, rows)
            paths.append(path)
        for name, value in result.items():
            if name not in required:
                raise ValueError("Undeclared result output: " + name)
            path = output / (name + (".jsonl" if name in ROW_OUTPUTS else ".json"))
            (write_rows if name in ROW_OUTPUTS else write_json)(path, value)
            paths.append(path)
        write_json(output / "join_validation.json", study.get("validation", {}))
        paths.append(output / "join_validation.json")
        completed = {
            "status": "completed_CPU_saved_score_failure_study",
            "at_utc": now(), "elapsed_seconds": time.perf_counter() - started,
            "specification": binding(root, spec_path),
            "execution_freeze": binding(root, freeze_path),
            "counts": {"frames": len(study["frames"]),
                       "candidate_contexts": len(study["candidates"]),
                       "paired_candidates": len(result["paired_candidates"]),
                       "paired_frames": len(result["paired_frames"]),
                       "contrasts": len(result["contrast_views"]),
                       "historical": len(result["historical_appendix"])},
            "outputs": [binding(root, path) for path in paths],
            "new_model_calls": 0, "GPU_queries": 0, "new_labels": 0,
            "new_choices": 0, "selected_threshold": None, "adopted_model": None,
            "protected_access": False, "old_consumers_reexecuted": False,
            "limits": ["Descriptive exposed-data diagnosis, not independent validation",
                       "Fitting-game composition and training amount are confounded",
                       "Zero is the original diagnostic reference, not a calibrated probability",
                       "Support fields do not establish physical ball size or semantic identity"],
        }
        write_json(output / "completed.json", completed)
        return completed
    except Exception as error:
        write_json(output / "failed.json", {
            "status": "failed_preserved_attempt", "at_utc": now(),
            "elapsed_seconds": time.perf_counter() - started,
            "error_type": type(error).__name__, "error": str(error),
            "traceback": traceback.format_exc(),
            "partial_outputs_preserved": True,
        })
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--specification", default=DEFAULT_SPEC)
    parser.add_argument("--execution-freeze", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    completed = run(args.repository_root, args.specification, args.execution_freeze, args.output)
    print(json.dumps({key: completed[key] for key in ("status", "elapsed_seconds", "counts")}, indent=2))


if __name__ == "__main__":
    main()
