from typing import Any

from .possession import PipelineManifest, PipelinePaths


def _setting(
    manifest: PipelineManifest,
    section: str,
    key: str,
    default: Any,
) -> Any:
    return manifest.overrides.get(section, {}).get(key, default)


def _base(module: str) -> list[str]:
    return ["python", "-m", module]


def build_stage_review_commands(
    stage_name: str,
    manifest: PipelineManifest,
    paths: PipelinePaths,
) -> list[list[str]]:
    if stage_name != "identity_review_cycle":
        return []

    expected_team_count = manifest.expected_team_counts["white"]

    if expected_team_count != manifest.expected_team_counts["dark"]:
        raise ValueError("Identity review requires equal expected team counts")

    return [
        _base("src.reid.review_identity_boundaries")
        + [
            "--video",
            paths.relative("video"),
            "--tracks",
            paths.relative("classified_tracks"),
            "--segments-report",
            paths.relative("reid_segments"),
            "--review-config",
            paths.relative("reid_review_config"),
            "--output-dir",
            paths.relative("identity_boundary_review_dir"),
            "--context-frames",
            "2",
        ],
        _base("src.identity.review_residual_identities")
        + [
            "--video",
            paths.relative("video"),
            "--reconciled-tracks",
            paths.relative("reconciled_tracks"),
            "--mapping",
            paths.relative("segment_player_mapping"),
            "--prototypes",
            paths.relative("reid_segment_prototypes"),
            "--output-dir",
            paths.relative("residual_identity_review_dir"),
            "--report",
            paths.relative("residual_identity_candidates"),
            "--expected-player-count",
            str(manifest.expected_player_count),
        ],
        _base("src.identity.review_sequential_identities")
        + [
            "--video",
            paths.relative("video"),
            "--reconciled-tracks",
            paths.relative("reconciled_tracks"),
            "--mapping",
            paths.relative("segment_player_mapping"),
            "--prototypes",
            paths.relative("reid_segment_prototypes"),
            "--reid-review",
            paths.relative("reid_review_config"),
            "--output-dir",
            paths.relative("sequential_identity_review_dir"),
            "--report",
            paths.relative("sequential_identity_candidates"),
        ],
        _base("src.identity.review_cross_track_switches")
        + [
            "--video",
            paths.relative("video"),
            "--reconciled-tracks",
            paths.relative("reconciled_tracks"),
            "--mapping",
            paths.relative("segment_player_mapping"),
            "--embeddings",
            paths.relative("osnet_embeddings"),
            "--reid-review",
            paths.relative("reid_review_config"),
            "--sequential-review",
            paths.relative("sequential_identity_review_config"),
            "--output-dir",
            paths.relative("cross_track_switch_review_dir"),
            "--report",
            paths.relative("cross_track_switch_candidates"),
            "--team-label",
            str(_setting(manifest, "identity", "cross_track_team", "dark")),
        ],
        _base("src.identity.review_team_balance")
        + [
            "--video",
            paths.relative("video"),
            "--reconciled-tracks",
            paths.relative("reconciled_tracks"),
            "--mapping",
            paths.relative("segment_player_mapping"),
            "--output-dir",
            paths.relative("team_balance_review_dir"),
            "--report",
            paths.relative("team_balance_candidates"),
            "--expected-team-count",
            str(expected_team_count),
            "--expected-active-count",
            str(manifest.expected_player_count),
        ],
    ]


def build_stage_command(
    stage_name: str,
    manifest: PipelineManifest,
    paths: PipelinePaths,
) -> list[str] | None:
    if stage_name == "court_polygon":
        return _base("src.court.select_court_polygon") + [
            "--video",
            paths.relative("video"),
            "--output",
            paths.relative("court_polygon_config"),
            "--reference-frame",
            str(manifest.reference_frame_value),
        ]

    if stage_name == "tracking":
        return _base("src.tracking.track_video") + [
            "--video",
            paths.relative("video"),
            "--court-config",
            paths.relative("court_polygon_config"),
            "--output-video",
            paths.relative("tracking_video"),
            "--output-tracks",
            paths.relative("tracking_tracks"),
            "--detector-threshold",
            str(_setting(manifest, "tracking", "detector_threshold", 0.15)),
            "--track-activation-threshold",
            str(
                _setting(
                    manifest,
                    "tracking",
                    "track_activation_threshold",
                    0.35,
                )
            ),
            "--high-confidence-threshold",
            str(
                _setting(
                    manifest,
                    "tracking",
                    "high_confidence_threshold",
                    0.35,
                )
            ),
            "--lost-track-buffer",
            str(_setting(manifest, "tracking", "lost_track_buffer", 30)),
            "--minimum-consecutive-frames",
            str(
                _setting(
                    manifest,
                    "tracking",
                    "minimum_consecutive_frames",
                    2,
                )
            ),
            "--minimum-iou-threshold",
            str(
                _setting(
                    manifest,
                    "tracking",
                    "minimum_iou_threshold",
                    0.1,
                )
            ),
        ]

    if stage_name == "tracking_audit":
        return _base("src.tracking.audit_tracks") + [
            "--tracks",
            paths.relative("tracking_tracks"),
            "--output",
            paths.relative("tracking_audit"),
            "--video",
            paths.relative("video"),
            "--expected-player-count",
            str(manifest.expected_player_count),
            "--track-count-tolerance",
            str(
                _setting(
                    manifest,
                    "tracking_audit",
                    "track_count_tolerance",
                    1,
                )
            ),
            "--short-track-max-frames",
            str(
                _setting(
                    manifest,
                    "tracking_audit",
                    "short_track_max_frames",
                    30,
                )
            ),
            "--max-handoff-overlap-frames",
            str(
                _setting(
                    manifest,
                    "tracking_audit",
                    "max_handoff_overlap_frames",
                    10,
                )
            ),
            "--max-handoff-gap-frames",
            str(
                _setting(
                    manifest,
                    "tracking_audit",
                    "max_handoff_gap_frames",
                    30,
                )
            ),
            "--max-handoff-distance-pixels",
            str(
                _setting(
                    manifest,
                    "tracking_audit",
                    "max_handoff_distance_pixels",
                    150.0,
                )
            ),
            "--min-handoff-track-length",
            str(
                _setting(
                    manifest,
                    "tracking_audit",
                    "min_handoff_track_length",
                    20,
                )
            ),
        ]

    if stage_name == "uniform_features":
        return _base("src.classification.extract_uniform_features") + [
            "--video",
            paths.relative("video"),
            "--tracks",
            paths.relative("tracking_tracks"),
            "--output-features",
            paths.relative("uniform_features"),
            "--output-montage",
            paths.relative("uniform_crops"),
            "--sample-every-n-frames",
            str(
                _setting(
                    manifest,
                    "classification",
                    "sample_every_n_frames",
                    5,
                )
            ),
            "--min-track-detections",
            str(
                _setting(
                    manifest,
                    "classification",
                    "feature_min_track_detections",
                    20,
                )
            ),
            "--bright-value-threshold",
            str(
                _setting(
                    manifest,
                    "classification",
                    "bright_value_threshold",
                    160,
                )
            ),
            "--bright-saturation-max",
            str(
                _setting(
                    manifest,
                    "classification",
                    "bright_saturation_max",
                    110,
                )
            ),
            "--dark-value-threshold",
            str(
                _setting(
                    manifest,
                    "classification",
                    "dark_value_threshold",
                    90,
                )
            ),
        ]

    if stage_name == "team_classification":
        return _base("src.classification.classify_teams") + [
            "--video",
            paths.relative("video"),
            "--tracks",
            paths.relative("tracking_tracks"),
            "--features",
            paths.relative("uniform_features"),
            "--court-config",
            paths.relative("court_polygon_config"),
            "--output-tracks",
            paths.relative("classified_tracks"),
            "--output-video",
            paths.relative("classified_video"),
            "--min-track-detections",
            str(
                _setting(
                    manifest,
                    "classification",
                    "classifier_min_track_detections",
                    35,
                )
            ),
            "--min-feature-samples",
            str(
                _setting(
                    manifest,
                    "classification",
                    "min_feature_samples",
                    5,
                )
            ),
            "--min-texture-std",
            str(
                _setting(
                    manifest,
                    "classification",
                    "min_texture_std",
                    35.0,
                )
            ),
            "--white-min-bright-fraction",
            str(
                _setting(
                    manifest,
                    "classification",
                    "white_min_bright_fraction",
                    0.55,
                )
            ),
            "--white-max-dark-fraction",
            str(
                _setting(
                    manifest,
                    "classification",
                    "white_max_dark_fraction",
                    0.20,
                )
            ),
            "--white-min-value",
            str(
                _setting(
                    manifest,
                    "classification",
                    "white_min_value",
                    170.0,
                )
            ),
            "--dark-min-dark-fraction",
            str(
                _setting(
                    manifest,
                    "classification",
                    "dark_min_dark_fraction",
                    0.22,
                )
            ),
            "--dark-max-bright-fraction",
            str(
                _setting(
                    manifest,
                    "classification",
                    "dark_max_bright_fraction",
                    0.50,
                )
            ),
            "--dark-max-value",
            str(
                _setting(
                    manifest,
                    "classification",
                    "dark_max_value",
                    150.0,
                )
            ),
        ]

    if stage_name == "reid_embeddings":
        return _base("src.reid.extract_track_embeddings") + [
            "--video",
            paths.relative("video"),
            "--classified-tracks",
            paths.relative("classified_tracks"),
            "--output-embeddings",
            paths.relative("osnet_embeddings"),
            "--output-metadata",
            paths.relative("osnet_metadata"),
            "--sample-every-n-frames",
            str(_setting(manifest, "reid", "sample_every_n_frames", 5)),
            "--min-confidence",
            str(_setting(manifest, "reid", "minimum_confidence", 0.20)),
            "--min-box-width",
            str(_setting(manifest, "reid", "minimum_box_width", 20)),
            "--min-box-height",
            str(_setting(manifest, "reid", "minimum_box_height", 50)),
            "--extractor-batch-size",
            str(_setting(manifest, "reid", "extractor_batch_size", 64)),
        ]

    if stage_name == "reid_segmentation":
        return _base("src.reid.segment_track_embeddings") + [
            "--embeddings",
            paths.relative("osnet_embeddings"),
            "--review-config",
            paths.relative("reid_review_config"),
            "--output-segments",
            paths.relative("reid_segments"),
            "--output-prototypes",
            paths.relative("reid_segment_prototypes"),
            "--max-sample-frame-gap",
            str(_setting(manifest, "reid", "max_sample_frame_gap", 15)),
            "--appearance-window-size",
            str(_setting(manifest, "reid", "appearance_window_size", 3)),
            "--appearance-change-threshold",
            str(
                _setting(
                    manifest,
                    "reid",
                    "appearance_change_threshold",
                    0.25,
                )
            ),
            "--min-candidate-separation-samples",
            str(
                _setting(
                    manifest,
                    "reid",
                    "min_candidate_separation_samples",
                    3,
                )
            ),
        ]

    if stage_name == "segment_matching":
        return _base("src.tracking.reconcile_track_ids") + [
            "--classified-tracks",
            paths.relative("classified_tracks"),
            "--segments",
            paths.relative("reid_segments"),
            "--prototypes",
            paths.relative("reid_segment_prototypes"),
            "--review-config",
            paths.relative("reid_review_config"),
            "--output",
            paths.relative("segment_match_candidates"),
            "--max-segment-overlap-frames",
            str(
                _setting(
                    manifest,
                    "reid",
                    "max_segment_overlap_frames",
                    30,
                )
            ),
            "--max-segment-gap-frames",
            str(_setting(manifest, "reid", "max_segment_gap_frames", 30)),
            "--max-appearance-distance",
            str(_setting(manifest, "reid", "max_appearance_distance", 0.18)),
            "--max-endpoint-floor-distance",
            str(
                _setting(
                    manifest,
                    "reid",
                    "max_endpoint_floor_distance",
                    120.0,
                )
            ),
            "--min-endpoint-box-iou",
            str(_setting(manifest, "reid", "min_endpoint_box_iou", 0.15)),
            "--min-duplicate-median-iou",
            str(
                _setting(
                    manifest,
                    "reid",
                    "min_duplicate_median_iou",
                    0.45,
                )
            ),
            "--max-duplicate-median-distance",
            str(
                _setting(
                    manifest,
                    "reid",
                    "max_duplicate_median_distance",
                    45.0,
                )
            ),
            "--strict-max-appearance-distance",
            str(
                _setting(
                    manifest,
                    "reid",
                    "strict_max_appearance_distance",
                    0.14,
                )
            ),
            "--strict-max-frame-gap",
            str(_setting(manifest, "reid", "strict_max_frame_gap", 10)),
            "--strict-max-floor-distance",
            str(
                _setting(
                    manifest,
                    "reid",
                    "strict_max_floor_distance",
                    90.0,
                )
            ),
            "--strict-min-box-iou",
            str(_setting(manifest, "reid", "strict_min_box_iou", 0.20)),
        ]

    if stage_name == "identity_review_cycle":
        return _base("src.identity.build_player_identities") + [
            "--classified-tracks",
            paths.relative("classified_tracks"),
            "--segments",
            paths.relative("reid_segments"),
            "--matches",
            paths.relative("segment_match_candidates"),
            "--identity-review-config",
            paths.relative("identity_review_config"),
            "--sequential-review-config",
            paths.relative("sequential_identity_review_config"),
            "--output-mapping",
            paths.relative("segment_player_mapping"),
            "--output-annotated-tracks",
            paths.relative("identity_annotated_tracks"),
            "--output-reconciled-tracks",
            paths.relative("reconciled_tracks"),
            "--expected-player-count",
            str(manifest.expected_player_count),
        ]

    if stage_name == "identity_visualization":
        command = _base("src.visualization.render_identity_tracks") + [
            "--video",
            paths.relative("video"),
            "--tracks",
            paths.relative("reconciled_tracks"),
            "--output",
            paths.relative("identity_review_video"),
            "--report",
            paths.relative("identity_review_report"),
            "--trail-length",
            str(_setting(manifest, "identity", "trail_length", 12)),
            "--boundary-window",
            str(_setting(manifest, "identity", "boundary_window", 3)),
            "--expected-player-count",
            str(manifest.expected_player_count),
            "--expected-white-count",
            str(manifest.expected_team_counts["white"]),
            "--expected-dark-count",
            str(manifest.expected_team_counts["dark"]),
            "--review-boundaries",
        ]
        command.extend(
            str(frame)
            for frame in _setting(
                manifest,
                "identity",
                "review_boundaries",
                [],
            )
        )
        return command

    if stage_name == "calibration_preparation":
        return _base("src.court.prepare_calibration_review") + [
            "--video",
            paths.relative("video"),
            "--court-config",
            paths.relative("court_polygon_config"),
            "--output-dir",
            paths.relative("calibration_review_dir"),
            "--report",
            paths.relative("calibration_preparation_report"),
            "--sample-count",
            "7",
            "--max-features",
            "5000",
        ]

    if stage_name == "court_landmarks":
        command = _base("src.court.select_court_landmarks") + [
            "--video",
            paths.relative("video"),
            "--court-config",
            paths.relative("court_polygon_config"),
            "--output-config",
            paths.relative("court_calibration_pending"),
            "--review-dir",
            paths.relative("landmark_review_dir"),
        ]

        if manifest.reference_frame_index is not None:
            command.extend(
                ["--reference-frame", str(manifest.reference_frame_index)]
            )

        return command

    if stage_name == "calibration_finalize":
        return _base("src.court.finalize_court_calibration") + [
            "--video",
            paths.relative("video"),
            "--input",
            paths.relative("court_calibration_pending"),
            "--review",
            paths.relative("court_calibration_review"),
            "--output",
            paths.relative("court_calibration_final"),
            "--review-dir",
            paths.relative("calibration_final_review_dir"),
        ]

    if stage_name == "boundary_refinement":
        return _base("src.court.refine_court_boundary") + [
            "--video",
            paths.relative("video"),
            "--input",
            paths.relative("court_calibration_final"),
            "--output",
            paths.relative("court_calibration_refined"),
            "--review-dir",
            paths.relative("boundary_refinement_dir"),
        ]

    if stage_name == "camera_motion":
        command = _base("src.court.propagate_court_calibration") + [
            "--video",
            paths.relative("video"),
            "--calibration",
            paths.relative("court_calibration_refined"),
            "--court-config",
            paths.relative("court_polygon_config"),
            "--output-dir",
            paths.relative("motion_review_dir"),
            "--output-video",
            paths.relative("court_motion_video"),
            "--output-homographies",
            paths.relative("camera_homographies"),
            "--report",
            paths.relative("court_motion_report"),
            "--sample-count",
            str(_setting(manifest, "camera_motion", "sample_count", 7)),
            "--max-features",
            str(_setting(manifest, "camera_motion", "max_features", 6000)),
            "--review-width",
            str(_setting(manifest, "camera_motion", "review_width", 1280)),
            "--smoothing-window",
            str(
                _setting(
                    manifest,
                    "camera_motion",
                    "smoothing_window",
                    11,
                )
            ),
            "--extra-checkpoint-frames",
        ]
        command.extend(
            str(frame)
            for frame in _setting(
                manifest,
                "camera_motion",
                "extra_checkpoint_frames",
                [],
            )
        )
        return command

    if stage_name == "coordinate_export":
        team_counts = manifest.expected_team_counts

        if team_counts["white"] != team_counts["dark"]:
            raise ValueError(
                "Coordinate export requires equal expected team counts"
            )

        return _base("src.court.export_player_court_coordinates") + [
            "--tracks",
            paths.relative("reconciled_tracks"),
            "--calibration",
            paths.relative("court_calibration_refined"),
            "--homographies",
            paths.relative("camera_homographies"),
            "--motion-report",
            paths.relative("court_motion_report"),
            "--output",
            paths.relative("player_coordinates"),
            "--report",
            paths.relative("player_coordinates_report"),
            "--expected-player-count",
            str(manifest.expected_player_count),
            "--expected-players-per-team",
            str(team_counts["white"]),
            "--bounds-tolerance-ft",
            "0.0",
            "--precision",
            "6",
        ]

    if stage_name in {"coordinate_review", "final_coordinate_review"}:
        final_review = stage_name == "final_coordinate_review"
        command = _base(
            "src.visualization.render_player_court_coordinates"
        ) + [
            "--video",
            paths.relative("video"),
            "--coordinates",
            paths.relative(
                "gap_filled_coordinates" if final_review else "player_coordinates"
            ),
            "--coordinate-report",
            paths.relative("player_coordinates_report"),
            "--calibration",
            paths.relative("court_calibration_refined"),
        ]

        if final_review:
            command.extend(
                [
                    "--refinement-report",
                    paths.relative("trajectory_refinement_report"),
                    "--gap-report",
                    paths.relative("gap_interpolation_report"),
                ]
            )

        command.extend(
            [
                "--output",
                paths.relative(
                    "gap_filled_review_video"
                    if final_review
                    else "player_coordinates_review_video"
                ),
                "--report",
                paths.relative(
                    "gap_filled_review_report"
                    if final_review
                    else "player_coordinates_review_report"
                ),
                "--checkpoints-dir",
                paths.relative(
                    "gap_filled_checkpoints"
                    if final_review
                    else "player_coordinates_checkpoints"
                ),
                "--review-height",
                str(_setting(manifest, "visualization", "review_height", 720)),
                "--source-width",
                str(_setting(manifest, "visualization", "source_width", 1280)),
                "--court-panel-width",
                str(
                    _setting(
                        manifest,
                        "visualization",
                        "court_panel_width",
                        560,
                    )
                ),
                "--trail-length",
                str(_setting(manifest, "visualization", "trail_length", 20)),
                "--jump-speed-threshold-ft-sec",
                str(
                    _setting(
                        manifest,
                        "visualization",
                        "jump_speed_threshold_ft_sec",
                        45.0,
                    )
                ),
                "--sample-count",
                str(_setting(manifest, "visualization", "sample_count", 12)),
                "--maximum-event-checkpoints",
                str(
                    _setting(
                        manifest,
                        "visualization",
                        "maximum_event_checkpoints",
                        8,
                    )
                ),
            ]
        )
        return command

    if stage_name == "trajectory_refinement":
        return _base("src.court.refine_player_court_trajectories") + [
            "--coordinates",
            paths.relative("player_coordinates"),
            "--review-report",
            paths.relative("player_coordinates_review_report"),
            "--output",
            paths.relative("refined_coordinates"),
            "--audit",
            paths.relative("trajectory_refinement_audit"),
            "--report",
            paths.relative("trajectory_refinement_report"),
            "--maximum-speed-ft-sec",
            str(
                _setting(
                    manifest,
                    "trajectory_refinement",
                    "maximum_speed_ft_sec",
                    45.0,
                )
            ),
            "--maximum-extrapolation-observations",
            str(
                _setting(
                    manifest,
                    "trajectory_refinement",
                    "maximum_extrapolation_observations",
                    2,
                )
            ),
            "--extrapolation-anchor-count",
            str(
                _setting(
                    manifest,
                    "trajectory_refinement",
                    "extrapolation_anchor_count",
                    5,
                )
            ),
            "--half-court-length-ft",
            str(manifest.court.half_court_length_ft),
            "--court-width-ft",
            str(manifest.court.court_width_ft),
        ]

    if stage_name == "gap_interpolation":
        return _base("src.court.fill_player_court_trajectory_gaps") + [
            "--coordinates",
            paths.relative("refined_coordinates"),
            "--refinement-report",
            paths.relative("trajectory_refinement_report"),
            "--output",
            paths.relative("gap_filled_coordinates"),
            "--audit",
            paths.relative("gap_interpolation_audit"),
            "--report",
            paths.relative("gap_interpolation_report"),
            "--maximum-gap-observations",
            str(
                _setting(
                    manifest,
                    "gap_interpolation",
                    "maximum_gap_observations",
                    10,
                )
            ),
            "--maximum-endpoint-speed-ft-sec",
            str(
                _setting(
                    manifest,
                    "gap_interpolation",
                    "maximum_endpoint_speed_ft_sec",
                    45.0,
                )
            ),
            "--half-court-length-ft",
            str(manifest.court.half_court_length_ft),
            "--court-width-ft",
            str(manifest.court.court_width_ft),
        ]

    return None
