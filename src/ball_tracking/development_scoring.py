"""Score the two development pools separately using the existing evaluator."""

from pathlib import Path, PurePosixPath

from .development_experiments import PURPOSES
from .development_release import validate_development_release
from . import score_detector_experiment as scoring


def pool_report_filename(purpose: str) -> str:
    if purpose not in PURPOSES:
        raise scoring.DetectorExperimentScoringError("Unknown development pool")
    return f"{purpose}_grid_v0_2.json"


def score_development_pools(experiment, manifest_path, manifest_relative,
                             manifest_bytes, root, head, deps):
    validate_development_release(experiment, root, head)
    if manifest_path.read_bytes() != manifest_bytes:
        raise scoring.DetectorExperimentScoringError("Manifest changed while loading")
    # This verifies common model provenance across all six, before splitting.
    windows = scoring._prepare_pilots(experiment, root, deps)
    deps.verify_commit_ancestor(
        root, windows[0].detections.model_provenance.code_commit, head, manifest_relative,
    )
    prepared = []
    for purpose in PURPOSES:
        pool = tuple(p for p in windows if p.window.selection_purpose == purpose)
        report = scoring.build_scoring_report(
            experiment, manifest_relative, manifest_bytes, head, pool,
            evaluate=deps.evaluate, aggregate=deps.aggregate, selection_purpose=purpose,
        )
        relative = PurePosixPath(*scoring.OUTPUT_ROOT_PARTS, experiment.experiment_id,
                                 pool_report_filename(purpose))
        path = scoring.reject_unsafe_repository_path(root, relative, label="Development report")
        if not deps.is_git_ignored(root, relative):
            raise scoring.DetectorExperimentScoringError("Development report must be ignored")
        content = scoring._serialized_report(report)
        reused = path.exists()
        if reused and (not path.is_file() or scoring.load_scoring_report(path) != report
                       or path.read_bytes() != content):
            raise scoring.DetectorExperimentScoringError("Existing development report conflicts; not overwritten")
        prepared.append((path, relative, report, reused))
    for window in windows:
        if (window.annotation_path.read_bytes() != window.annotation_bytes
            or window.detection_path.read_bytes() != window.detection_bytes):
            raise scoring.DetectorExperimentScoringError("Development scoring input changed")
        deps.verify_tracked_file(root, scoring._annotation_relative_path(window.window))
    if manifest_path.read_bytes() != manifest_bytes:
        raise scoring.DetectorExperimentScoringError("Manifest changed during scoring")
    scoring._verify_evaluator_sources(root, deps)
    closing = deps.inspect_git(root, manifest_relative)
    if scoring._validate_git_snapshot(closing, root, manifest_relative) != head:
        raise scoring.DetectorExperimentScoringError("HEAD changed during scoring")
    validate_development_release(experiment, root, head)
    for path, relative, report, reused in prepared:
        scoring.reject_unsafe_repository_path(root, relative, label="Development report")
        if not reused:
            deps.write_report(report, path)
    return scoring.ScoringSummary(
        head=head, output_path=prepared[0][0].parent,
        reused_existing=all(item[3] for item in prepared), pilot_window_count=6,
        grid_cell_count=sum(item[2]["grid_cell_count"] for item in prepared),
        evaluation_report_count=sum(item[2]["evaluation_report_count"] for item in prepared),
    )
