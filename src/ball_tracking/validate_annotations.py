"""Command-line validation for ball annotation schema version 0.1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .annotations import (
    AnnotationValidationError,
    load_annotations,
    verify_source_video,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate an auditable ball-center annotation JSON document "
            "against schema version 0.1."
        )
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        required=True,
        help="Ball annotation JSON to validate.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the validation summary as JSON.",
    )
    parser.add_argument(
        "--verify-source",
        action="store_true",
        help="Hash and probe the declared source clip.",
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path("."),
        help="Repository root used to resolve the source-video path.",
    )
    return parser.parse_args(argv)


def print_text_summary(summary: dict) -> None:
    print("Ball annotation validation passed.")
    print(f"Annotation set: {summary['annotation_set_id']}")
    print(f"Possession: {summary['possession_id']}")
    print(
        "Window: "
        f"{summary['start_frame_index']}-"
        f"{summary['end_frame_index']} "
        f"({summary['frame_count']} frames)"
    )
    print(
        "Localization-eligible frames: "
        f"{summary['localization_eligible_count']}"
    )
    print(f"Review status: {summary['review_status']}")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    try:
        annotation_set = load_annotations(args.annotations)

        if annotation_set.review.status == "reviewed" and not args.verify_source:
            raise AnnotationValidationError(
                "Reviewed annotations require --verify-source"
            )

        source_verification = (
            verify_source_video(annotation_set, args.repository_root)
            if args.verify_source
            else None
        )
    except (AnnotationValidationError, FileNotFoundError) as error:
        raise SystemExit(f"Ball annotation validation error: {error}") from error

    summary = annotation_set.validation_summary()

    if source_verification is not None:
        summary["source_verification"] = source_verification

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print_text_summary(summary)


if __name__ == "__main__":
    main()
