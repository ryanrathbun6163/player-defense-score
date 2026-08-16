"""Safe resumable execution for the config-driven player-coordinate plan."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from .possession import PipelineManifest, PipelinePaths


STATE_SCHEMA_VERSION = 1
APPROVED_CALIBRATION_STATUSES = {
    "approved",
    "approved_with_corrections",
}
IDENTITY_COMPLETION_OUTPUTS = {
    "segment_player_mapping",
    "identity_annotated_tracks",
    "reconciled_tracks",
}


class PipelineExecutionError(RuntimeError):
    """Raised when a planned stage cannot execute or validate safely."""


@dataclass
class ExecutionResult:
    status: str
    executed_stages: list[str] = field(default_factory=list)
    skipped_stages: list[str] = field(default_factory=list)
    stage_name: str | None = None
    reasons: list[str] = field(default_factory=list)
    review_commands: list[list[str]] = field(default_factory=list)


CommandRunner = Callable[[list[str], Path], int]


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _directory_fingerprint(path: Path) -> dict[str, Any]:
    entries = []

    for child in sorted(path.rglob("*")):
        relative = child.relative_to(path).as_posix()
        stat = child.stat()
        entries.append(
            {
                "path": relative,
                "kind": "directory" if child.is_dir() else "file",
                "size": 0 if child.is_dir() else stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
        )

    return {
        "kind": "directory",
        "entry_count": len(entries),
        "digest": _stable_digest(entries),
    }


def fingerprint_path(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"kind": "missing"}

    if path.is_dir():
        return _directory_fingerprint(path)

    stat = path.stat()
    return {
        "kind": "file",
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _stage_signature(
    stage: Mapping[str, Any],
    manifest: PipelineManifest,
    paths: PipelinePaths,
) -> str:
    inputs = {
        item["key"]: fingerprint_path(paths[item["key"]])
        for item in stage["inputs"]
    }
    return _stable_digest(
        {
            "manifest": manifest.to_dict(),
            "stage_name": stage["name"],
            "command": stage["command"],
            "review_commands": stage.get("review_commands", []),
            "inputs": inputs,
        }
    )


def _empty_state(manifest: PipelineManifest) -> dict[str, Any]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "possession_id": manifest.possession_id,
        "updated_at": _utc_timestamp(),
        "stages": {},
    }


def load_execution_state(
    state_path: Path,
    manifest: PipelineManifest,
) -> dict[str, Any]:
    if not state_path.exists():
        return _empty_state(manifest)

    try:
        with state_path.open("r", encoding="utf-8") as input_file:
            state = json.load(input_file)
    except json.JSONDecodeError as error:
        raise PipelineExecutionError(
            f"Invalid pipeline state JSON: {state_path}: {error}"
        ) from error

    if not isinstance(state, dict):
        raise PipelineExecutionError("Pipeline state must be a JSON object")

    if state.get("schema_version") != STATE_SCHEMA_VERSION:
        raise PipelineExecutionError(
            "Unsupported pipeline state schema version: "
            f"{state.get('schema_version')!r}"
        )

    if state.get("possession_id") != manifest.possession_id:
        raise PipelineExecutionError(
            "Pipeline state possession does not match the manifest: "
            f"{state.get('possession_id')!r}"
        )

    if not isinstance(state.get("stages"), dict):
        raise PipelineExecutionError("Pipeline state stages must be an object")

    return state


def save_execution_state(state_path: Path, state: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _utc_timestamp()
    temporary_path = state_path.with_suffix(state_path.suffix + ".tmp")

    with temporary_path.open("w", encoding="utf-8") as output_file:
        json.dump(state, output_file, indent=2)
        output_file.write("\n")

    os.replace(temporary_path, state_path)


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> bool:
    if path.exists():
        return False

    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with path.open("x", encoding="utf-8") as output_file:
            json.dump(payload, output_file, indent=2)
            output_file.write("\n")
    except FileExistsError:
        return False

    return True


def ensure_review_templates(
    manifest: PipelineManifest,
    paths: PipelinePaths,
) -> list[Path]:
    created = []
    templates = {
        "reid_review_config": {
            "manual_split_after_frames": {},
            "manual_segment_team_overrides": {},
            "reviewed_false_positive_boundaries": [],
            "manual_match_decisions": {
                "accept": [],
                "reject": [],
            },
        },
        "identity_review_config": {
            "review_source": paths.relative("residual_identity_candidates"),
            "expected_active_player_count": manifest.expected_player_count,
            "accepted_identity_merges": [],
            "rejected_identity_merges": [],
            "excluded_identities": [],
            "team_overrides": {},
            "retained_for_sequential_review": [],
            "candidate_decisions": [],
            "review_conclusion": "Pending human identity review.",
        },
        "sequential_identity_review_config": {
            "review_source": paths.relative(
                "sequential_identity_candidates"
            ),
            "accepted_identity_merges": [],
            "rejected_identity_merges": [],
            "confirmed_blocked_controls": [],
            "review_conclusion": "Pending human sequential review.",
        },
    }

    for key, payload in templates.items():
        path = paths[key]

        if _write_new_json(path, payload):
            created.append(path)

    return created


def _default_command_runner(command: list[str], repo_root: Path) -> int:
    actual_command = [sys.executable, *command[1:]]
    completed = subprocess.run(actual_command, cwd=repo_root, check=False)
    return completed.returncode


def _required_output_keys(stage: Mapping[str, Any]) -> list[str]:
    keys = [item["key"] for item in stage["outputs"]]

    if stage["name"] == "identity_review_cycle":
        return [key for key in keys if key in IDENTITY_COMPLETION_OUTPUTS]

    return keys


def _missing_stage_inputs(
    stage: Mapping[str, Any],
    paths: PipelinePaths,
) -> list[str]:
    return [
        item["key"]
        for item in stage["inputs"]
        if not paths[item["key"]].exists()
    ]


def _missing_stage_outputs(
    stage: Mapping[str, Any],
    paths: PipelinePaths,
) -> list[str]:
    return [
        key
        for key in _required_output_keys(stage)
        if not paths[key].exists()
    ]


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as input_file:
            payload = json.load(input_file)
    except json.JSONDecodeError as error:
        raise PipelineExecutionError(
            f"Invalid {label} JSON: {path}: {error}"
        ) from error

    if not isinstance(payload, dict):
        raise PipelineExecutionError(f"{label} must be a JSON object: {path}")

    return payload


def _identity_preconditions(paths: PipelinePaths) -> list[str]:
    reasons = []

    if not paths["reid_segments"].is_file():
        reasons.append("ReID segment report is missing.")
    else:
        segments = _load_json_object(paths["reid_segments"], "segment report")
        unresolved = segments.get(
            "unresolved_appearance_candidate_count",
            0,
        )

        if unresolved != 0:
            reasons.append(
                f"{unresolved} appearance boundary decision(s) remain."
            )

    if not paths["segment_match_candidates"].is_file():
        reasons.append("Segment-match report is missing.")
    else:
        matches = _load_json_object(
            paths["segment_match_candidates"],
            "segment-match report",
        )
        unresolved = matches.get("unresolved_review_candidate_count", 0)

        if unresolved != 0:
            reasons.append(f"{unresolved} segment match decision(s) remain.")

    for key, label in (
        ("identity_review_config", "Identity review config"),
        ("sequential_identity_review_config", "Sequential review config"),
    ):
        if not paths[key].is_file():
            reasons.append(f"{label} is missing: {paths.relative(key)}")

    return reasons


def _identity_output_reasons(
    manifest: PipelineManifest,
    paths: PipelinePaths,
) -> list[str]:
    mapping = _load_json_object(
        paths["segment_player_mapping"],
        "identity mapping",
    )
    summary = mapping.get("summary")

    if not isinstance(summary, dict):
        return ["Identity mapping summary is missing."]

    reasons = []
    active_count = summary.get("active_identity_cluster_count")

    if active_count != manifest.expected_player_count:
        reasons.append(
            "Active identity count is "
            f"{active_count!r}; expected {manifest.expected_player_count}."
        )

    actual_team_counts = summary.get("identity_counts_by_team")
    expected_team_counts = dict(manifest.expected_team_counts)

    if actual_team_counts != expected_team_counts:
        reasons.append(
            "Identity team counts are "
            f"{actual_team_counts!r}; expected {expected_team_counts!r}."
        )

    frames_above = summary.get("frames_above_expected_count")

    if frames_above != 0:
        reasons.append(
            f"{frames_above!r} frame(s) exceed the expected player count."
        )

    return reasons


def _calibration_review_reasons(paths: PipelinePaths) -> list[str]:
    review_path = paths["court_calibration_review"]

    if not review_path.is_file():
        return [
            "Calibration review is missing: "
            f"{paths.relative('court_calibration_review')}"
        ]

    review = _load_json_object(review_path, "calibration review")
    status = review.get("review_status")

    if status not in APPROVED_CALIBRATION_STATUSES:
        return [
            "Calibration review_status must be one of "
            f"{sorted(APPROVED_CALIBRATION_STATUSES)}; found {status!r}."
        ]

    return []


def _record_stage(
    state: dict[str, Any],
    stage_name: str,
    status: str,
    signature: str,
    **extra: Any,
) -> None:
    state["stages"][stage_name] = {
        "status": status,
        "signature": signature,
        "updated_at": _utc_timestamp(),
        **extra,
    }


def execute_plan(
    plan: Mapping[str, Any],
    manifest: PipelineManifest,
    paths: PipelinePaths,
    *,
    rerun_from: str | None = None,
    command_runner: CommandRunner | None = None,
) -> ExecutionResult:
    if not plan["generalization_gate"]["structural"]["passed"]:
        raise PipelineExecutionError(
            "The structural generalization gate must pass before execution."
        )

    stages = list(plan["stages"])
    stage_names = [stage["name"] for stage in stages]

    if rerun_from is not None and rerun_from not in stage_names:
        raise PipelineExecutionError(
            f"Unknown --rerun-from stage {rerun_from!r}; "
            f"choose one of {stage_names}"
        )

    state_path = paths["pipeline_state"]
    state = load_execution_state(state_path, manifest)

    if rerun_from is not None:
        rerun_index = stage_names.index(rerun_from)

        for name in stage_names[rerun_index:]:
            state["stages"].pop(name, None)

        save_execution_state(state_path, state)

    runner = command_runner or _default_command_runner
    result = ExecutionResult(status="completed")

    for stage in stages:
        name = stage["name"]
        signature = _stage_signature(stage, manifest, paths)
        prior = state["stages"].get(name, {})
        outputs_missing = _missing_stage_outputs(stage, paths)

        if name == "calibration_review_gate":
            reasons = _calibration_review_reasons(paths)

            if reasons:
                _record_stage(
                    state,
                    name,
                    "awaiting_review",
                    signature,
                    reasons=reasons,
                )
                save_execution_state(state_path, state)
                result.status = "paused_for_review"
                result.stage_name = name
                result.reasons = reasons
                return result

            if (
                prior.get("status") == "completed"
                and prior.get("signature") == signature
                and not outputs_missing
            ):
                result.skipped_stages.append(name)
                continue

            _record_stage(state, name, "completed", signature)
            save_execution_state(state_path, state)
            result.executed_stages.append(name)
            continue

        if name == "identity_review_cycle":
            reasons = _identity_preconditions(paths)

            if reasons:
                _record_stage(
                    state,
                    name,
                    "awaiting_review",
                    signature,
                    reasons=reasons,
                )
                save_execution_state(state_path, state)
                result.status = "paused_for_review"
                result.stage_name = name
                result.reasons = reasons
                result.review_commands = list(stage["review_commands"][:1])
                return result

            if (
                prior.get("status") == "completed"
                and prior.get("signature") == signature
                and not outputs_missing
            ):
                reasons = _identity_output_reasons(manifest, paths)

                if not reasons:
                    result.skipped_stages.append(name)
                    continue

        if (
            prior.get("status") == "completed"
            and prior.get("signature") == signature
            and not outputs_missing
        ):
            result.skipped_stages.append(name)
            continue

        missing_inputs = _missing_stage_inputs(stage, paths)

        if missing_inputs:
            reasons = [
                "Missing required inputs: " + ", ".join(missing_inputs)
            ]
            _record_stage(
                state,
                name,
                "failed",
                signature,
                reasons=reasons,
            )
            save_execution_state(state_path, state)
            return ExecutionResult(
                status="failed",
                executed_stages=result.executed_stages,
                skipped_stages=result.skipped_stages,
                stage_name=name,
                reasons=reasons,
            )

        command = stage["command"]

        if command is None:
            raise PipelineExecutionError(
                f"Executable stage {name!r} has no command"
            )

        print(f"\nRunning stage {stage['index']:02d}: {name}", flush=True)
        print("Command: " + " ".join(command), flush=True)

        try:
            return_code = runner(list(command), paths.repo_root)
        except KeyboardInterrupt:
            _record_stage(state, name, "interrupted", signature)
            save_execution_state(state_path, state)
            raise

        if return_code != 0:
            reasons = [f"Stage command exited with code {return_code}."]
            _record_stage(
                state,
                name,
                "failed",
                signature,
                command=command,
                return_code=return_code,
                reasons=reasons,
            )
            save_execution_state(state_path, state)
            return ExecutionResult(
                status="failed",
                executed_stages=result.executed_stages,
                skipped_stages=result.skipped_stages,
                stage_name=name,
                reasons=reasons,
            )

        outputs_missing = _missing_stage_outputs(stage, paths)

        if outputs_missing:
            reasons = [
                "Command succeeded but required outputs are missing: "
                + ", ".join(outputs_missing)
            ]
            _record_stage(
                state,
                name,
                "failed",
                signature,
                command=command,
                reasons=reasons,
            )
            save_execution_state(state_path, state)
            return ExecutionResult(
                status="failed",
                executed_stages=result.executed_stages,
                skipped_stages=result.skipped_stages,
                stage_name=name,
                reasons=reasons,
            )

        if name == "identity_review_cycle":
            reasons = _identity_output_reasons(manifest, paths)

            if reasons:
                _record_stage(
                    state,
                    name,
                    "awaiting_review",
                    signature,
                    command=command,
                    reasons=reasons,
                )
                save_execution_state(state_path, state)
                result.executed_stages.append(name)
                result.status = "paused_for_review"
                result.stage_name = name
                result.reasons = reasons
                result.review_commands = list(stage["review_commands"])
                return result

        _record_stage(
            state,
            name,
            "completed",
            signature,
            command=command,
        )
        save_execution_state(state_path, state)
        result.executed_stages.append(name)

    return result
