import argparse
import json
from pathlib import Path

from .execution import (
    PipelineExecutionError,
    ensure_review_templates,
    execute_plan,
)
from .generalization_gate import (
    GateEvidenceError,
    load_empirical_evidence,
)
from .planner import build_plan
from .possession import (
    ConfigurationError,
    PipelinePaths,
    load_manifest,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a possession manifest and display the planned "
            "player-coordinate pipeline."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Possession pipeline JSON configuration.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="Repository root; normally discovered automatically.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and print the non-executing stage plan.",
    )
    mode.add_argument(
        "--run",
        action="store_true",
        help=(
            "Execute or resume a non-baseline possession until completion "
            "or the next explicit human review gate."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the dry-run plan as JSON.",
    )
    parser.add_argument(
        "--check-inputs",
        action="store_true",
        help="Fail if the configured source video does not exist.",
    )
    parser.add_argument(
        "--gate-evidence",
        type=Path,
        help=(
            "Optional reviewed evidence JSON for evaluating a different "
            "possession against the empirical generalization gate."
        ),
    )
    parser.add_argument(
        "--rerun-from",
        help=(
            "With --run, invalidate this stage and every downstream stage "
            "before resuming. Existing outputs are overwritten by their "
            "normal stage commands, not deleted."
        ),
    )
    parser.add_argument(
        "--allow-reviewed-baseline",
        action="store_true",
        help=(
            "Allow --run to overwrite possession_001 outputs. This is an "
            "explicit emergency override and is never needed for "
            "generalization testing."
        ),
    )
    args = parser.parse_args(argv)

    if args.json and not args.dry_run:
        parser.error("--json is available only with --dry-run")

    if args.gate_evidence is not None and not args.dry_run:
        parser.error("--gate-evidence is available only with --dry-run")

    if args.rerun_from is not None and not args.run:
        parser.error("--rerun-from requires --run")

    if args.allow_reviewed_baseline and not args.run:
        parser.error("--allow-reviewed-baseline requires --run")

    return args


def _looks_like_repo_root(path: Path) -> bool:
    return (
        (path / "src").is_dir()
        and (path / "configs").is_dir()
    )


def discover_repo_root(
    config_path: Path,
    explicit_root: Path | None,
) -> Path:
    if explicit_root is not None:
        candidate = explicit_root.resolve()

        if not _looks_like_repo_root(candidate):
            raise ConfigurationError(
                f"Not a player-defense-score repository root: {candidate}"
            )

        return candidate

    starts = [Path.cwd().resolve(), config_path.resolve().parent]
    checked = set()

    for start in starts:
        for candidate in (start, *start.parents):
            if candidate in checked:
                continue

            checked.add(candidate)

            if _looks_like_repo_root(candidate):
                return candidate

    raise ConfigurationError(
        "Could not discover repository root from the current directory "
        f"or config path: {config_path}"
    )


def print_text_plan(plan: dict) -> None:
    manifest = plan["manifest"]
    summary = plan["summary"]
    print("\nPlayer-coordinate pipeline dry run")
    print(f"Possession: {manifest['possession_id']}")
    print(f"Video: {manifest['video_path']}")
    print(
        "Reference frame: "
        f"{manifest['reference_frame_index']}"
    )
    print(f"Stages: {summary['stage_count']}")
    print(
        "Generalization status: "
        f"{summary['generalization_status_counts']}"
    )
    print("Candidate execution: resumable and review-gated")
    gate = plan["generalization_gate"]
    print(
        "Structural generalization gate: "
        f"{gate['structural']['status']}"
    )
    print(
        "Empirical multi-possession gate: "
        f"{gate['empirical']['status']}"
    )
    if gate["ball_tracking_unlocked"]:
        print("Ball tracking is unlocked by the reviewed gate evidence.")
    else:
        print("Ball tracking remains blocked until the empirical gate passes.")
    print()

    for stage in plan["stages"]:
        print(
            f"{stage['index']:02d}. {stage['name']} "
            f"[{stage['generalization_status']}]"
        )
        print(f"    {stage['description']}")

        if stage["command"] is not None:
            print(f"    Command: {' '.join(stage['command'])}")

        for review_index, command in enumerate(
            stage.get("review_commands", []),
            1,
        ):
            print(
                f"    Review command {review_index}: "
                f"{' '.join(command)}"
            )

    print()
    print("No pipeline stage was executed and no output was written.")


def print_execution_result(result, paths: PipelinePaths) -> None:
    print("\nPlayer-coordinate pipeline execution summary")
    print(f"Status: {result.status}")
    print(f"Executed stages: {len(result.executed_stages)}")
    print(f"Resumed/skipped stages: {len(result.skipped_stages)}")
    print(f"State: {paths.relative('pipeline_state')}")

    if result.stage_name is not None:
        print(f"Current stage: {result.stage_name}")

    for reason in result.reasons:
        print(f"  - {reason}")

    if result.review_commands:
        print("\nManifest-derived review commands:")

        for command in result.review_commands:
            print("  " + " ".join(command))

    if result.status == "paused_for_review":
        print(
            "\nReview the reported evidence/configuration, then rerun the "
            "same --run command to resume."
        )
    elif result.status == "completed":
        print("\nAll 21 player-coordinate stages completed.")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    config_path = args.config.resolve()

    try:
        repo_root = discover_repo_root(config_path, args.repo_root)
        manifest = load_manifest(config_path)
        gate_evidence = (
            None
            if args.gate_evidence is None
            else load_empirical_evidence(args.gate_evidence)
        )
        paths = PipelinePaths.build(
            repo_root,
            manifest,
            config_path=config_path,
        )

        if args.check_inputs and not paths["video"].is_file():
            raise FileNotFoundError(
                f"Configured source video not found: {paths['video']}"
            )

        plan = build_plan(
            manifest,
            paths,
            gate_evidence=gate_evidence,
        )
    except (
        ConfigurationError,
        FileNotFoundError,
        GateEvidenceError,
    ) as error:
        raise SystemExit(f"Pipeline configuration error: {error}") from error

    if args.dry_run and args.json:
        print(json.dumps(plan, indent=2, sort_keys=False))
    elif args.dry_run:
        print_text_plan(plan)
    else:
        if (
            manifest.possession_id == "possession_001"
            and not args.allow_reviewed_baseline
        ):
            raise SystemExit(
                "Pipeline execution blocked: possession_001 is the reviewed "
                "baseline. Use a different possession config."
            )

        if not paths["video"].is_file():
            raise SystemExit(
                "Pipeline execution blocked: configured source video not "
                f"found: {paths['video']}"
            )

        created_templates = ensure_review_templates(manifest, paths)

        for path in created_templates:
            print(
                "Created review template: "
                f"{path.relative_to(repo_root).as_posix()}"
            )

        try:
            result = execute_plan(
                plan,
                manifest,
                paths,
                rerun_from=args.rerun_from,
            )
        except PipelineExecutionError as error:
            raise SystemExit(f"Pipeline execution error: {error}") from error

        print_execution_result(result, paths)

        if result.status == "failed":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
