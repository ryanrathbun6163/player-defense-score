from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


REQUIRED_REVIEW_GATES = {
    "identity_review_cycle",
    "calibration_review_gate",
}
MIN_COORDINATE_COVERAGE_RATIO = 0.95
MIN_COMPLETE_PLAYER_FRAME_RATIO = 0.85
REQUIRED_EVIDENCE_FIELDS = {
    "possession_id",
    "source_edits_required",
    "all_stages_completed",
    "review_gates_completed",
    "homography_coverage_ratio",
    "coordinate_coverage_ratio",
    "complete_player_frame_ratio",
    "unresolved_review_count",
    "coordinate_key_violation_count",
    "outside_court_positions_audited",
    "visual_review_through_final_frame",
    "generated_outputs_uncommitted",
}


class GateEvidenceError(ValueError):
    """Raised when empirical gate evidence is not a JSON object."""


def load_empirical_evidence(path: Path) -> Mapping[str, Any]:
    evidence_path = path.resolve()

    if not evidence_path.is_file():
        raise FileNotFoundError(
            f"Generalization gate evidence not found: {evidence_path}"
        )

    try:
        with evidence_path.open("r", encoding="utf-8") as input_file:
            evidence = json.load(input_file)
    except json.JSONDecodeError as error:
        raise GateEvidenceError(
            f"Invalid JSON in gate evidence {evidence_path}: {error}"
        ) from error

    if not isinstance(evidence, Mapping):
        raise GateEvidenceError("Generalization gate evidence must be an object")

    return evidence


def _ratio_at_least(value: Any, minimum: float) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and minimum <= float(value) <= 1.0
    )


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "detail": detail,
    }


def evaluate_structural_gate(plan: Mapping[str, Any]) -> dict[str, Any]:
    stages = list(plan["stages"])
    blocker_names = [
        stage["name"]
        for stage in stages
        if stage["generalization_status"] == "needs_cli_refactor"
    ]
    missing_commands = [
        stage["name"]
        for stage in stages
        if (
            stage["generalization_status"] == "cli_ready"
            and stage["command"] is None
        )
    ]
    review_gates = {
        stage["name"]
        for stage in stages
        if stage["generalization_status"] == "review_gate"
    }
    identity_review_stage = next(
        (
            stage
            for stage in stages
            if stage["name"] == "identity_review_cycle"
        ),
        None,
    )
    identity_review_commands = (
        []
        if identity_review_stage is None
        else identity_review_stage.get("review_commands", [])
    )
    output_paths = [
        output["path"]
        for stage in stages
        for output in stage["outputs"]
    ]
    duplicate_outputs = sorted(
        {
            path
            for path in output_paths
            if output_paths.count(path) > 1
        }
    )
    possession_id = plan["manifest"]["possession_id"]
    scoped_output_paths = [
        path
        for path in output_paths
        if path.startswith(("configs/", "data/outputs/"))
    ]
    unscoped_outputs = [
        path
        for path in scoped_output_paths
        if possession_id not in path
    ]

    checks = [
        _check(
            "no_source_refactor_blockers",
            not blocker_names,
            (
                "All planned stages are CLI-ready or explicit review gates."
                if not blocker_names
                else f"Still blocked: {blocker_names}"
            ),
        ),
        _check(
            "all_automatic_stages_have_commands",
            not missing_commands,
            (
                "Every CLI-ready stage has a manifest-derived command."
                if not missing_commands
                else f"Missing commands: {missing_commands}"
            ),
        ),
        _check(
            "review_gates_are_explicit",
            review_gates == REQUIRED_REVIEW_GATES,
            (
                "Identity and calibration are the only human review gates."
                if review_gates == REQUIRED_REVIEW_GATES
                else (
                    f"Expected {sorted(REQUIRED_REVIEW_GATES)}, "
                    f"found {sorted(review_gates)}"
                )
            ),
        ),
        _check(
            "identity_review_tools_are_config_driven",
            len(identity_review_commands) == 5,
            (
                "Five manifest-derived identity review helpers are available."
                if len(identity_review_commands) == 5
                else (
                    "Expected five identity review helper commands, found "
                    f"{len(identity_review_commands)}."
                )
            ),
        ),
        _check(
            "stage_outputs_are_unique",
            not duplicate_outputs,
            (
                "No two stages claim the same output path."
                if not duplicate_outputs
                else f"Duplicate outputs: {duplicate_outputs}"
            ),
        ),
        _check(
            "outputs_are_possession_scoped",
            not unscoped_outputs,
            (
                f"All generated outputs are scoped to {possession_id}."
                if not unscoped_outputs
                else f"Unscoped outputs: {unscoped_outputs}"
            ),
        ),
        _check(
            "candidate_execution_is_guarded",
            (
                plan.get("execution_enabled") is True
                and plan.get("execution_guardrails", {}).get(
                    "reviewed_baseline_protected"
                )
                is True
                and plan.get("execution_guardrails", {}).get(
                    "review_gates_pause_execution"
                )
                is True
                and bool(
                    plan.get("execution_guardrails", {}).get(
                        "resumable_state"
                    )
                )
            ),
            (
                "Candidate execution protects the reviewed baseline, pauses "
                "at both review gates, and records resumable state."
            ),
        ),
    ]
    passed = all(check["passed"] for check in checks)

    return {
        "status": "passed" if passed else "failed",
        "passed": passed,
        "checks": checks,
    }


def evaluate_empirical_gate(
    baseline_possession_id: str,
    evidence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if evidence is None:
        return {
            "status": "pending_second_possession",
            "passed": False,
            "checks": [],
            "requirements": {
                "different_possession": True,
                "source_edits_required": False,
                "all_stages_completed": True,
                "review_gates_completed": True,
                "homography_coverage_ratio": 1.0,
                "coordinate_coverage_ratio_minimum": (
                    MIN_COORDINATE_COVERAGE_RATIO
                ),
                "complete_player_frame_ratio_minimum": (
                    MIN_COMPLETE_PLAYER_FRAME_RATIO
                ),
                "unresolved_review_count": 0,
                "coordinate_key_violation_count": 0,
                "outside_court_positions_audited": True,
                "visual_review_through_final_frame": True,
                "generated_outputs_uncommitted": True,
            },
        }

    candidate_id = evidence.get("possession_id")
    evidence_fields = set(evidence)
    missing_fields = sorted(REQUIRED_EVIDENCE_FIELDS - evidence_fields)
    unknown_fields = sorted(evidence_fields - REQUIRED_EVIDENCE_FIELDS)
    checks = [
        _check(
            "evidence_schema",
            not missing_fields and not unknown_fields,
            (
                "Evidence has exactly the required fields."
                if not missing_fields and not unknown_fields
                else (
                    f"Missing fields: {missing_fields}; "
                    f"unknown fields: {unknown_fields}"
                )
            ),
        ),
        _check(
            "different_possession",
            isinstance(candidate_id, str)
            and bool(candidate_id)
            and candidate_id != baseline_possession_id,
            f"Candidate possession: {candidate_id!r}",
        ),
        _check(
            "no_source_edits",
            evidence.get("source_edits_required") is False,
            "The candidate must run through configuration only.",
        ),
        _check(
            "all_stages_completed",
            evidence.get("all_stages_completed") is True,
            "All automatic, interactive, and review stages must finish.",
        ),
        _check(
            "review_gates_completed",
            evidence.get("review_gates_completed") is True,
            "Identity and calibration review decisions must be recorded.",
        ),
        _check(
            "one_homography_per_frame",
            _ratio_at_least(
                evidence.get("homography_coverage_ratio"),
                1.0,
            ),
            "Every decoded frame must have one camera homography.",
        ),
        _check(
            "coordinate_coverage",
            _ratio_at_least(
                evidence.get("coordinate_coverage_ratio"),
                MIN_COORDINATE_COVERAGE_RATIO,
            ),
            (
                "Coordinate coverage must be at least "
                f"{MIN_COORDINATE_COVERAGE_RATIO:.0%}."
            ),
        ),
        _check(
            "complete_player_frames",
            _ratio_at_least(
                evidence.get("complete_player_frame_ratio"),
                MIN_COMPLETE_PLAYER_FRAME_RATIO,
            ),
            (
                "Complete expected-player frames must be at least "
                f"{MIN_COMPLETE_PLAYER_FRAME_RATIO:.0%}."
            ),
        ),
        _check(
            "no_unresolved_reviews",
            evidence.get("unresolved_review_count") == 0,
            "No ReID, identity, calibration, or trajectory review remains.",
        ),
        _check(
            "coordinate_keys_are_unique",
            evidence.get("coordinate_key_violation_count") == 0,
            "Player/frame coordinate keys must be unique and valid.",
        ),
        _check(
            "outside_positions_audited",
            evidence.get("outside_court_positions_audited") is True,
            "Outside-court observations may remain only after audit.",
        ),
        _check(
            "visual_review_complete",
            evidence.get("visual_review_through_final_frame") is True,
            "Synchronized court and trajectory review must reach the final frame.",
        ),
        _check(
            "generated_outputs_uncommitted",
            evidence.get("generated_outputs_uncommitted") is True,
            "Generated media and data outputs must remain uncommitted.",
        ),
    ]
    passed = all(check["passed"] for check in checks)

    return {
        "status": "passed" if passed else "failed",
        "passed": passed,
        "checks": checks,
    }


def build_generalization_gate(
    plan: Mapping[str, Any],
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    structural = evaluate_structural_gate(plan)
    empirical = evaluate_empirical_gate(
        plan["manifest"]["possession_id"],
        evidence,
    )
    unlocked = structural["passed"] and empirical["passed"]

    return {
        "structural": structural,
        "empirical": empirical,
        "multi_possession_gate_passed": unlocked,
        "ball_tracking_unlocked": unlocked,
    }
