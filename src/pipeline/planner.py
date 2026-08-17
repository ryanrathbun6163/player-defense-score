from collections import Counter
from dataclasses import dataclass
from typing import Any, Mapping

from .commands import build_stage_command, build_stage_review_commands
from .generalization_gate import build_generalization_gate
from .possession import PipelineManifest, PipelinePaths


@dataclass(frozen=True)
class StageSpec:
    name: str
    modules: tuple[str, ...]
    mode: str
    generalization_status: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    description: str


STAGE_SPECS = (
    StageSpec(
        name="court_polygon",
        modules=("src.court.select_court_polygon",),
        mode="interactive",
        generalization_status="cli_ready",
        inputs=("video",),
        outputs=("court_polygon_config",),
        description="Select the playable-court polygon on a reference frame.",
    ),
    StageSpec(
        name="tracking",
        modules=("src.tracking.track_video",),
        mode="automatic",
        generalization_status="cli_ready",
        inputs=("video", "court_polygon_config"),
        outputs=("tracking_tracks", "tracking_video"),
        description="Detect and track court-filtered people.",
    ),
    StageSpec(
        name="tracking_audit",
        modules=("src.tracking.audit_tracks",),
        mode="automatic",
        generalization_status="cli_ready",
        inputs=("tracking_tracks", "video"),
        outputs=("tracking_audit",),
        description="Audit track counts, continuity, and handoff candidates.",
    ),
    StageSpec(
        name="uniform_features",
        modules=("src.classification.extract_uniform_features",),
        mode="automatic",
        generalization_status="cli_ready",
        inputs=("video", "tracking_tracks"),
        outputs=("uniform_features", "uniform_crops"),
        description="Extract aggregate jersey-color features by track.",
    ),
    StageSpec(
        name="team_classification",
        modules=("src.classification.classify_teams",),
        mode="automatic",
        generalization_status="cli_ready",
        inputs=(
            "video",
            "tracking_tracks",
            "uniform_features",
            "court_polygon_config",
        ),
        outputs=("classified_tracks", "classified_video"),
        description="Assign white, dark, or unknown team labels.",
    ),
    StageSpec(
        name="reid_embeddings",
        modules=("src.reid.extract_track_embeddings",),
        mode="automatic_gpu",
        generalization_status="cli_ready",
        inputs=("video", "classified_tracks"),
        outputs=("osnet_embeddings", "osnet_metadata"),
        description="Extract sampled OSNet-AIN player embeddings.",
    ),
    StageSpec(
        name="reid_segmentation",
        modules=("src.reid.segment_track_embeddings",),
        mode="automatic_with_review_overrides",
        generalization_status="cli_ready",
        inputs=("osnet_embeddings", "reid_review_config"),
        outputs=("reid_segments", "reid_segment_prototypes"),
        description="Split raw tracks into temporal appearance segments.",
    ),
    StageSpec(
        name="segment_matching",
        modules=("src.tracking.reconcile_track_ids",),
        mode="automatic_with_review_overrides",
        generalization_status="cli_ready",
        inputs=(
            "classified_tracks",
            "reid_segments",
            "reid_segment_prototypes",
            "reid_review_config",
        ),
        outputs=("segment_match_candidates",),
        description="Generate strict and reviewable ReID segment matches.",
    ),
    StageSpec(
        name="identity_review_cycle",
        modules=(
            "src.identity.build_player_identities",
            "src.identity.review_cross_track_switches",
            "src.identity.review_residual_identities",
            "src.identity.review_sequential_identities",
            "src.identity.review_team_balance",
            "src.reid.review_identity_boundaries",
        ),
        mode="iterative_human_review",
        generalization_status="review_gate",
        inputs=(
            "video",
            "classified_tracks",
            "reid_segments",
            "reid_segment_prototypes",
            "segment_match_candidates",
            "reid_review_config",
            "identity_review_config",
            "sequential_identity_review_config",
        ),
        outputs=(
            "segment_player_mapping",
            "identity_annotated_tracks",
            "reconciled_tracks",
            "cross_track_switch_candidates",
            "residual_identity_candidates",
            "sequential_identity_candidates",
            "team_balance_candidates",
            "cross_track_switch_review_config",
            "team_balance_review_config",
        ),
        description=(
            "Iterate possession-specific reviewed identity decisions and "
            "rerun the manifest-derived identity build until the expected "
            "active-player and team counts are satisfied."
        ),
    ),
    StageSpec(
        name="identity_visualization",
        modules=("src.visualization.render_identity_tracks",),
        mode="automatic_review_output",
        generalization_status="cli_ready",
        inputs=("video", "reconciled_tracks"),
        outputs=("identity_review_video", "identity_review_report"),
        description="Render and validate the consolidated player identities.",
    ),
    StageSpec(
        name="calibration_preparation",
        modules=("src.court.prepare_calibration_review",),
        mode="automatic_review_output",
        generalization_status="cli_ready",
        inputs=("video", "court_polygon_config"),
        outputs=("calibration_review_dir", "calibration_preparation_report"),
        description="Prepare candidate frames for reference calibration.",
    ),
    StageSpec(
        name="court_landmarks",
        modules=("src.court.select_court_landmarks",),
        mode="interactive",
        generalization_status="cli_ready",
        inputs=("video", "court_polygon_config"),
        outputs=("court_calibration_pending", "landmark_review_dir"),
        description="Select image-to-court reference correspondences.",
    ),
    StageSpec(
        name="calibration_review_gate",
        modules=(),
        mode="human_review",
        generalization_status="review_gate",
        inputs=("court_calibration_pending", "landmark_review_dir"),
        outputs=("court_calibration_review",),
        description="Record reviewed landmark corrections and fit choices.",
    ),
    StageSpec(
        name="calibration_finalize",
        modules=("src.court.finalize_court_calibration",),
        mode="automatic_review_output",
        generalization_status="cli_ready",
        inputs=(
            "video",
            "court_calibration_pending",
            "court_calibration_review",
        ),
        outputs=("court_calibration_final", "calibration_final_review_dir"),
        description="Apply reviewed landmark decisions to the reference fit.",
    ),
    StageSpec(
        name="boundary_refinement",
        modules=("src.court.refine_court_boundary",),
        mode="interactive",
        generalization_status="cli_ready",
        inputs=("video", "court_calibration_final"),
        outputs=("court_calibration_refined", "boundary_refinement_dir"),
        description="Constrain the visible camera-side court boundary.",
    ),
    StageSpec(
        name="camera_motion",
        modules=("src.court.propagate_court_calibration",),
        mode="automatic_review_output",
        generalization_status="cli_ready",
        inputs=(
            "video",
            "court_polygon_config",
            "court_calibration_refined",
        ),
        outputs=(
            "camera_homographies",
            "court_motion_video",
            "court_motion_report",
            "motion_review_dir",
        ),
        description="Propagate and audit one camera homography per frame.",
    ),
    StageSpec(
        name="coordinate_export",
        modules=("src.court.export_player_court_coordinates",),
        mode="automatic",
        generalization_status="cli_ready",
        inputs=(
            "reconciled_tracks",
            "court_calibration_refined",
            "camera_homographies",
            "court_motion_report",
        ),
        outputs=("player_coordinates", "player_coordinates_report"),
        description="Project observed player floor points into court space.",
    ),
    StageSpec(
        name="coordinate_review",
        modules=("src.visualization.render_player_court_coordinates",),
        mode="automatic_review_output",
        generalization_status="cli_ready",
        inputs=(
            "video",
            "player_coordinates",
            "player_coordinates_report",
            "court_calibration_refined",
        ),
        outputs=(
            "player_coordinates_review_video",
            "player_coordinates_review_report",
            "player_coordinates_checkpoints",
        ),
        description="Render synchronized observed player coordinates.",
    ),
    StageSpec(
        name="trajectory_refinement",
        modules=("src.court.refine_player_court_trajectories",),
        mode="automatic_audited_correction",
        generalization_status="cli_ready",
        inputs=(
            "player_coordinates",
            "player_coordinates_review_report",
        ),
        outputs=(
            "refined_coordinates",
            "trajectory_refinement_audit",
            "trajectory_refinement_report",
        ),
        description="Apply conservative audited trajectory corrections.",
    ),
    StageSpec(
        name="gap_interpolation",
        modules=("src.court.fill_player_court_trajectory_gaps",),
        mode="automatic_audited_interpolation",
        generalization_status="cli_ready",
        inputs=("refined_coordinates", "trajectory_refinement_report"),
        outputs=(
            "gap_filled_coordinates",
            "gap_interpolation_audit",
            "gap_interpolation_report",
        ),
        description="Fill only conservative bracketed internal gaps.",
    ),
    StageSpec(
        name="final_coordinate_review",
        modules=("src.visualization.render_player_court_coordinates",),
        mode="automatic_review_output",
        generalization_status="cli_ready",
        inputs=(
            "video",
            "gap_filled_coordinates",
            "player_coordinates_report",
            "court_calibration_refined",
            "trajectory_refinement_report",
            "gap_interpolation_report",
        ),
        outputs=(
            "gap_filled_review_video",
            "gap_filled_review_report",
            "gap_filled_checkpoints",
        ),
        description="Render the final synchronized coordinate foundation.",
    ),
)


def _path_records(
    paths: PipelinePaths,
    keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "key": key,
            "path": paths.relative(key),
            "exists": paths[key].exists(),
        }
        for key in keys
    ]


def validate_stage_contract(paths: PipelinePaths) -> None:
    stage_names = [stage.name for stage in STAGE_SPECS]

    if len(stage_names) != len(set(stage_names)):
        raise ValueError("Pipeline stage names must be unique")

    missing_path_keys = sorted(
        {
            key
            for stage in STAGE_SPECS
            for key in stage.inputs + stage.outputs
            if key not in paths.values
        }
    )

    if missing_path_keys:
        raise ValueError(
            f"Pipeline stages reference unknown path keys: {missing_path_keys}"
        )


def build_plan(
    manifest: PipelineManifest,
    paths: PipelinePaths,
    gate_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    validate_stage_contract(paths)
    statuses = Counter(
        stage.generalization_status
        for stage in STAGE_SPECS
    )
    stages = []

    for index, stage in enumerate(STAGE_SPECS, 1):
        stages.append(
            {
                "index": index,
                "name": stage.name,
                "modules": list(stage.modules),
                "mode": stage.mode,
                "generalization_status": stage.generalization_status,
                "description": stage.description,
                "command": build_stage_command(
                    stage.name,
                    manifest,
                    paths,
                ),
                "review_commands": build_stage_review_commands(
                    stage.name,
                    manifest,
                    paths,
                ),
                "inputs": _path_records(paths, stage.inputs),
                "outputs": _path_records(paths, stage.outputs),
            }
        )

    plan = {
        "status": "pipeline_generalization_ready",
        "execution_enabled": True,
        "execution_guardrails": {
            "reviewed_baseline_protected": True,
            "review_gates_pause_execution": True,
            "resumable_state": paths.relative("pipeline_state"),
        },
        "manifest": manifest.to_dict(),
        "path_contract": paths.as_dict(relative=True),
        "summary": {
            "stage_count": len(STAGE_SPECS),
            "generalization_status_counts": dict(sorted(statuses.items())),
        },
        "stages": stages,
    }
    plan["generalization_gate"] = build_generalization_gate(
        plan,
        evidence=gate_evidence,
    )

    return plan
