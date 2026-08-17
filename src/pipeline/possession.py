import json
import math
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Mapping


SCHEMA_VERSION = 1
POSSESSION_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

REQUIRED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "possession_id",
    "video_path",
    "reference_frame_index",
    "expected_player_count",
    "expected_team_counts",
    "court",
}
OPTIONAL_TOP_LEVEL_FIELDS = {"overrides"}

COURT_FIELDS = {
    "ruleset",
    "coordinate_scope",
    "ideal_full_court_length_ft",
    "half_court_length_ft",
    "court_width_ft",
    "lane_width_ft",
    "baseline_to_free_throw_line_ft",
    "basket_center_from_baseline_ft",
    "three_point_radius_ft",
}

ALLOWED_OVERRIDE_SECTIONS = {
    "tracking",
    "tracking_audit",
    "classification",
    "reid",
    "identity",
    "camera_motion",
    "trajectory_refinement",
    "gap_interpolation",
    "visualization",
}

TRACKING_OVERRIDE_FIELDS = {
    "detector_threshold",
    "track_activation_threshold",
    "high_confidence_threshold",
    "lost_track_buffer",
    "minimum_consecutive_frames",
    "minimum_iou_threshold",
}
TRACKING_AUDIT_OVERRIDE_FIELDS = {
    "track_count_tolerance",
    "short_track_max_frames",
    "max_handoff_overlap_frames",
    "max_handoff_gap_frames",
    "max_handoff_distance_pixels",
    "min_handoff_track_length",
}
CLASSIFICATION_OVERRIDE_FIELDS = {
    "sample_every_n_frames",
    "feature_min_track_detections",
    "bright_value_threshold",
    "bright_saturation_max",
    "dark_value_threshold",
    "classifier_min_track_detections",
    "min_feature_samples",
    "min_texture_std",
    "white_min_bright_fraction",
    "white_max_dark_fraction",
    "white_min_value",
    "dark_min_dark_fraction",
    "dark_max_bright_fraction",
    "dark_max_value",
}
REID_OVERRIDE_FIELDS = {
    "sample_every_n_frames",
    "minimum_confidence",
    "minimum_box_width",
    "minimum_box_height",
    "extractor_batch_size",
    "max_sample_frame_gap",
    "appearance_window_size",
    "appearance_change_threshold",
    "min_candidate_separation_samples",
    "max_segment_overlap_frames",
    "max_segment_gap_frames",
    "max_appearance_distance",
    "max_endpoint_floor_distance",
    "min_endpoint_box_iou",
    "min_duplicate_median_iou",
    "max_duplicate_median_distance",
    "strict_max_appearance_distance",
    "strict_max_frame_gap",
    "strict_max_floor_distance",
    "strict_min_box_iou",
}
IDENTITY_OVERRIDE_FIELDS = {
    "review_boundaries",
    "trail_length",
    "boundary_window",
    "cross_track_team",
}
CAMERA_MOTION_OVERRIDE_FIELDS = {
    "sample_count",
    "max_features",
    "review_width",
    "smoothing_window",
    "extra_checkpoint_frames",
}
TRAJECTORY_REFINEMENT_OVERRIDE_FIELDS = {
    "maximum_speed_ft_sec",
    "maximum_extrapolation_observations",
    "extrapolation_anchor_count",
}
GAP_INTERPOLATION_OVERRIDE_FIELDS = {
    "maximum_gap_observations",
    "maximum_endpoint_speed_ft_sec",
}
VISUALIZATION_OVERRIDE_FIELDS = {
    "review_height",
    "source_width",
    "court_panel_width",
    "trail_length",
    "jump_speed_threshold_ft_sec",
    "sample_count",
    "maximum_event_checkpoints",
}


class ConfigurationError(ValueError):
    """Raised when a possession manifest violates the pipeline contract."""


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{label} must be a JSON object")

    return value


def _require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{label} must be a non-empty string")

    return value.strip()


def _require_positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigurationError(f"{label} must be a positive integer")

    return value


def _require_positive_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{label} must be a positive number")

    result = float(value)

    if not math.isfinite(result) or result <= 0:
        raise ConfigurationError(f"{label} must be a positive number")

    return result


def _require_portable_relative_path(
    value: Any,
    label: str,
) -> PurePosixPath:
    raw_path = _require_nonempty_string(value, label)

    if "\\" in raw_path:
        raise ConfigurationError(
            f"{label} must use forward slashes for portability"
        )

    path = PurePosixPath(raw_path)

    if path.is_absolute() or ".." in path.parts or path == PurePosixPath("."):
        raise ConfigurationError(
            f"{label} must stay within the repository: {raw_path!r}"
        )

    return path


def _parse_reference_frame(value: Any) -> int | None:
    if value == "middle":
        return None

    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ConfigurationError(
            "reference_frame_index must be a non-negative integer or "
            'the string "middle"'
        )

    return value


def _validate_exact_fields(
    value: Mapping[str, Any],
    required: set[str],
    optional: set[str],
    label: str,
) -> None:
    keys = set(value)
    missing = sorted(required - keys)
    unknown = sorted(keys - required - optional)

    if missing:
        raise ConfigurationError(f"{label} is missing fields: {missing}")

    if unknown:
        raise ConfigurationError(f"{label} has unknown fields: {unknown}")


@dataclass(frozen=True)
class CourtModel:
    ruleset: str
    coordinate_scope: str
    ideal_full_court_length_ft: float
    half_court_length_ft: float
    court_width_ft: float
    lane_width_ft: float
    baseline_to_free_throw_line_ft: float
    basket_center_from_baseline_ft: float
    three_point_radius_ft: float

    @classmethod
    def from_mapping(cls, value: Any) -> "CourtModel":
        court = _require_mapping(value, "court")
        _validate_exact_fields(court, COURT_FIELDS, set(), "court")

        model = cls(
            ruleset=_require_nonempty_string(court["ruleset"], "court.ruleset"),
            coordinate_scope=_require_nonempty_string(
                court["coordinate_scope"],
                "court.coordinate_scope",
            ),
            ideal_full_court_length_ft=_require_positive_number(
                court["ideal_full_court_length_ft"],
                "court.ideal_full_court_length_ft",
            ),
            half_court_length_ft=_require_positive_number(
                court["half_court_length_ft"],
                "court.half_court_length_ft",
            ),
            court_width_ft=_require_positive_number(
                court["court_width_ft"],
                "court.court_width_ft",
            ),
            lane_width_ft=_require_positive_number(
                court["lane_width_ft"],
                "court.lane_width_ft",
            ),
            baseline_to_free_throw_line_ft=_require_positive_number(
                court["baseline_to_free_throw_line_ft"],
                "court.baseline_to_free_throw_line_ft",
            ),
            basket_center_from_baseline_ft=_require_positive_number(
                court["basket_center_from_baseline_ft"],
                "court.basket_center_from_baseline_ft",
            ),
            three_point_radius_ft=_require_positive_number(
                court["three_point_radius_ft"],
                "court.three_point_radius_ft",
            ),
        )

        if not math.isclose(
            model.ideal_full_court_length_ft,
            2.0 * model.half_court_length_ft,
            rel_tol=0.0,
            abs_tol=1e-6,
        ):
            raise ConfigurationError(
                "court.ideal_full_court_length_ft must equal twice "
                "court.half_court_length_ft"
            )

        return model

    def to_dict(self) -> dict[str, Any]:
        return {
            "ruleset": self.ruleset,
            "coordinate_scope": self.coordinate_scope,
            "ideal_full_court_length_ft": self.ideal_full_court_length_ft,
            "half_court_length_ft": self.half_court_length_ft,
            "court_width_ft": self.court_width_ft,
            "lane_width_ft": self.lane_width_ft,
            "baseline_to_free_throw_line_ft": (
                self.baseline_to_free_throw_line_ft
            ),
            "basket_center_from_baseline_ft": (
                self.basket_center_from_baseline_ft
            ),
            "three_point_radius_ft": self.three_point_radius_ft,
        }


@dataclass(frozen=True)
class PipelineManifest:
    schema_version: int
    possession_id: str
    video_path: PurePosixPath
    reference_frame_index: int | None
    expected_player_count: int
    expected_team_counts: Mapping[str, int]
    court: CourtModel
    overrides: Mapping[str, Mapping[str, Any]]

    @classmethod
    def from_mapping(cls, value: Any) -> "PipelineManifest":
        manifest = _require_mapping(value, "pipeline manifest")
        _validate_exact_fields(
            manifest,
            REQUIRED_TOP_LEVEL_FIELDS,
            OPTIONAL_TOP_LEVEL_FIELDS,
            "pipeline manifest",
        )

        schema_version = manifest["schema_version"]

        if schema_version != SCHEMA_VERSION:
            raise ConfigurationError(
                f"Unsupported schema_version {schema_version!r}; "
                f"expected {SCHEMA_VERSION}"
            )

        possession_id = _require_nonempty_string(
            manifest["possession_id"],
            "possession_id",
        )

        if not POSSESSION_ID_PATTERN.fullmatch(possession_id):
            raise ConfigurationError(
                "possession_id must match "
                f"{POSSESSION_ID_PATTERN.pattern!r}: {possession_id!r}"
            )

        expected_player_count = _require_positive_int(
            manifest["expected_player_count"],
            "expected_player_count",
        )
        raw_team_counts = _require_mapping(
            manifest["expected_team_counts"],
            "expected_team_counts",
        )

        if set(raw_team_counts) != {"white", "dark"}:
            raise ConfigurationError(
                "expected_team_counts must contain exactly white and dark"
            )

        team_counts = {
            team: _require_positive_int(
                count,
                f"expected_team_counts.{team}",
            )
            for team, count in raw_team_counts.items()
        }

        if sum(team_counts.values()) != expected_player_count:
            raise ConfigurationError(
                "expected_team_counts must sum to expected_player_count"
            )

        overrides = cls._parse_overrides(manifest.get("overrides", {}))

        return cls(
            schema_version=schema_version,
            possession_id=possession_id,
            video_path=_require_portable_relative_path(
                manifest["video_path"],
                "video_path",
            ),
            reference_frame_index=_parse_reference_frame(
                manifest["reference_frame_index"]
            ),
            expected_player_count=expected_player_count,
            expected_team_counts=MappingProxyType(team_counts),
            court=CourtModel.from_mapping(manifest["court"]),
            overrides=overrides,
        )

    @staticmethod
    def _parse_overrides(
        value: Any,
    ) -> Mapping[str, Mapping[str, Any]]:
        overrides = _require_mapping(value, "overrides")
        unknown = sorted(set(overrides) - ALLOWED_OVERRIDE_SECTIONS)

        if unknown:
            raise ConfigurationError(
                f"overrides has unknown sections: {unknown}"
            )

        parsed: dict[str, Mapping[str, Any]] = {}

        for section, raw_settings in overrides.items():
            settings = dict(
                _require_mapping(raw_settings, f"overrides.{section}")
            )

            if section == "tracking":
                PipelineManifest._validate_tracking(settings)
            elif section == "tracking_audit":
                PipelineManifest._validate_tracking_audit(settings)
            elif section == "classification":
                PipelineManifest._validate_classification(settings)
            elif section == "reid":
                PipelineManifest._validate_reid(settings)
            elif section == "identity":
                PipelineManifest._validate_identity(settings)
            elif section == "camera_motion":
                PipelineManifest._validate_camera_motion(settings)
            elif section == "trajectory_refinement":
                PipelineManifest._validate_trajectory_refinement(settings)
            elif section == "gap_interpolation":
                PipelineManifest._validate_gap_interpolation(settings)
            elif section == "visualization":
                PipelineManifest._validate_visualization(settings)

            parsed[section] = MappingProxyType(settings)

        return MappingProxyType(parsed)

    @staticmethod
    def _reject_unknown_settings(
        settings: Mapping[str, Any],
        allowed: set[str],
        label: str,
    ) -> None:
        unknown = sorted(set(settings) - allowed)

        if unknown:
            raise ConfigurationError(f"{label} has unknown fields: {unknown}")

    @staticmethod
    def _validate_integer_setting(
        settings: Mapping[str, Any],
        key: str,
        label: str,
        minimum: int = 1,
        maximum: int | None = None,
    ) -> None:
        if key not in settings:
            return

        value = settings[key]

        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigurationError(f"{label}.{key} must be an integer")

        if value < minimum or (maximum is not None and value > maximum):
            range_text = (
                f"[{minimum}, {maximum}]"
                if maximum is not None
                else f">= {minimum}"
            )
            raise ConfigurationError(
                f"{label}.{key} must be in {range_text}"
            )

    @staticmethod
    def _validate_number_setting(
        settings: Mapping[str, Any],
        key: str,
        label: str,
        minimum: float,
        maximum: float,
    ) -> None:
        if key not in settings:
            return

        value = settings[key]

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigurationError(f"{label}.{key} must be numeric")

        numeric = float(value)

        if not math.isfinite(numeric) or not minimum <= numeric <= maximum:
            raise ConfigurationError(
                f"{label}.{key} must be in [{minimum}, {maximum}]"
            )

    @staticmethod
    def _validate_tracking(settings: Mapping[str, Any]) -> None:
        label = "overrides.tracking"
        PipelineManifest._reject_unknown_settings(
            settings,
            TRACKING_OVERRIDE_FIELDS,
            label,
        )

        for key in (
            "detector_threshold",
            "track_activation_threshold",
            "high_confidence_threshold",
            "minimum_iou_threshold",
        ):
            PipelineManifest._validate_number_setting(
                settings,
                key,
                label,
                0.0,
                1.0,
            )

        for key in ("lost_track_buffer", "minimum_consecutive_frames"):
            PipelineManifest._validate_integer_setting(
                settings,
                key,
                label,
            )

    @staticmethod
    def _validate_tracking_audit(settings: Mapping[str, Any]) -> None:
        label = "overrides.tracking_audit"
        PipelineManifest._reject_unknown_settings(
            settings,
            TRACKING_AUDIT_OVERRIDE_FIELDS,
            label,
        )

        for key in (
            "short_track_max_frames",
            "max_handoff_gap_frames",
            "min_handoff_track_length",
        ):
            PipelineManifest._validate_integer_setting(
                settings,
                key,
                label,
            )

        PipelineManifest._validate_integer_setting(
            settings,
            "max_handoff_overlap_frames",
            label,
            minimum=0,
        )

        PipelineManifest._validate_integer_setting(
            settings,
            "track_count_tolerance",
            label,
            minimum=0,
        )
        PipelineManifest._validate_number_setting(
            settings,
            "max_handoff_distance_pixels",
            label,
            0.000001,
            float("inf"),
        )

    @staticmethod
    def _validate_classification(settings: Mapping[str, Any]) -> None:
        label = "overrides.classification"
        PipelineManifest._reject_unknown_settings(
            settings,
            CLASSIFICATION_OVERRIDE_FIELDS,
            label,
        )

        for key in (
            "sample_every_n_frames",
            "feature_min_track_detections",
            "classifier_min_track_detections",
            "min_feature_samples",
        ):
            PipelineManifest._validate_integer_setting(
                settings,
                key,
                label,
            )

        for key in (
            "bright_value_threshold",
            "bright_saturation_max",
            "dark_value_threshold",
        ):
            PipelineManifest._validate_integer_setting(
                settings,
                key,
                label,
                minimum=0,
                maximum=255,
            )

        PipelineManifest._validate_number_setting(
            settings,
            "min_texture_std",
            label,
            0.0,
            float("inf"),
        )

        for key in (
            "white_min_bright_fraction",
            "white_max_dark_fraction",
            "dark_min_dark_fraction",
            "dark_max_bright_fraction",
        ):
            PipelineManifest._validate_number_setting(
                settings,
                key,
                label,
                0.0,
                1.0,
            )

        for key in ("white_min_value", "dark_max_value"):
            PipelineManifest._validate_number_setting(
                settings,
                key,
                label,
                0.0,
                255.0,
            )

    @staticmethod
    def _validate_reid(settings: Mapping[str, Any]) -> None:
        label = "overrides.reid"
        PipelineManifest._reject_unknown_settings(
            settings,
            REID_OVERRIDE_FIELDS,
            label,
        )

        for key in (
            "sample_every_n_frames",
            "minimum_box_width",
            "minimum_box_height",
            "extractor_batch_size",
            "max_sample_frame_gap",
            "appearance_window_size",
            "min_candidate_separation_samples",
        ):
            PipelineManifest._validate_integer_setting(
                settings,
                key,
                label,
            )

        for key in (
            "max_segment_overlap_frames",
            "max_segment_gap_frames",
            "strict_max_frame_gap",
        ):
            PipelineManifest._validate_integer_setting(
                settings,
                key,
                label,
                minimum=0,
            )

        PipelineManifest._validate_number_setting(
            settings,
            "minimum_confidence",
            label,
            0.0,
            1.0,
        )

        for key in (
            "appearance_change_threshold",
            "max_appearance_distance",
            "strict_max_appearance_distance",
        ):
            PipelineManifest._validate_number_setting(
                settings,
                key,
                label,
                0.0,
                2.0,
            )

        for key in (
            "min_endpoint_box_iou",
            "min_duplicate_median_iou",
            "strict_min_box_iou",
        ):
            PipelineManifest._validate_number_setting(
                settings,
                key,
                label,
                0.0,
                1.0,
            )

        for key in (
            "max_endpoint_floor_distance",
            "max_duplicate_median_distance",
            "strict_max_floor_distance",
        ):
            PipelineManifest._validate_number_setting(
                settings,
                key,
                label,
                0.000001,
                float("inf"),
            )

        resolved = {
            "max_appearance_distance": 0.18,
            "strict_max_appearance_distance": 0.14,
            "max_segment_gap_frames": 30,
            "strict_max_frame_gap": 10,
            "max_endpoint_floor_distance": 120.0,
            "strict_max_floor_distance": 90.0,
            "min_endpoint_box_iou": 0.15,
            "strict_min_box_iou": 0.20,
            **settings,
        }

        if (
            resolved["strict_max_appearance_distance"]
            > resolved["max_appearance_distance"]
        ):
            raise ConfigurationError(
                "overrides.reid.strict_max_appearance_distance cannot "
                "exceed max_appearance_distance"
            )

        if (
            resolved["strict_max_frame_gap"]
            > resolved["max_segment_gap_frames"]
        ):
            raise ConfigurationError(
                "overrides.reid.strict_max_frame_gap cannot exceed "
                "max_segment_gap_frames"
            )

        if (
            resolved["strict_max_floor_distance"]
            > resolved["max_endpoint_floor_distance"]
        ):
            raise ConfigurationError(
                "overrides.reid.strict_max_floor_distance cannot exceed "
                "max_endpoint_floor_distance"
            )

        if (
            resolved["strict_min_box_iou"]
            < resolved["min_endpoint_box_iou"]
        ):
            raise ConfigurationError(
                "overrides.reid.strict_min_box_iou cannot be below "
                "min_endpoint_box_iou"
            )

    @staticmethod
    def _validate_camera_motion(settings: Mapping[str, Any]) -> None:
        PipelineManifest._reject_unknown_settings(
            settings,
            CAMERA_MOTION_OVERRIDE_FIELDS,
            "overrides.camera_motion",
        )

        for key, minimum in (
            ("sample_count", 3),
            ("max_features", 1000),
            ("review_width", 640),
        ):
            PipelineManifest._validate_integer_setting(
                settings,
                key,
                "overrides.camera_motion",
                minimum=minimum,
            )

        PipelineManifest._validate_integer_setting(
            settings,
            "smoothing_window",
            "overrides.camera_motion",
            minimum=3,
        )

        if (
            "smoothing_window" in settings
            and settings["smoothing_window"] % 2 == 0
        ):
            raise ConfigurationError(
                "overrides.camera_motion.smoothing_window must be odd"
            )

        if "extra_checkpoint_frames" not in settings:
            return

        raw_frames = settings["extra_checkpoint_frames"]

        if not isinstance(raw_frames, list):
            raise ConfigurationError(
                "overrides.camera_motion.extra_checkpoint_frames "
                "must be a JSON array"
            )

        frames = []

        for frame in raw_frames:
            if isinstance(frame, bool) or not isinstance(frame, int) or frame < 0:
                raise ConfigurationError(
                    "camera-motion checkpoint frames must be "
                    "non-negative integers"
                )

            frames.append(frame)

        if frames != sorted(set(frames)):
            raise ConfigurationError(
                "camera-motion checkpoint frames must be sorted and unique"
            )

    @staticmethod
    def _validate_identity(settings: Mapping[str, Any]) -> None:
        label = "overrides.identity"
        PipelineManifest._reject_unknown_settings(
            settings,
            IDENTITY_OVERRIDE_FIELDS,
            label,
        )
        PipelineManifest._validate_integer_setting(
            settings,
            "trail_length",
            label,
            minimum=0,
        )
        PipelineManifest._validate_integer_setting(
            settings,
            "boundary_window",
            label,
            minimum=0,
        )

        if (
            "cross_track_team" in settings
            and settings["cross_track_team"] not in {"white", "dark"}
        ):
            raise ConfigurationError(
                "overrides.identity.cross_track_team must be white or dark"
            )

        if "review_boundaries" not in settings:
            return

        boundaries = settings["review_boundaries"]

        if not isinstance(boundaries, list):
            raise ConfigurationError(
                "overrides.identity.review_boundaries must be a JSON array"
            )

        if any(
            isinstance(frame, bool) or not isinstance(frame, int) or frame < 0
            for frame in boundaries
        ):
            raise ConfigurationError(
                "identity review boundaries must be non-negative integers"
            )

        if boundaries != sorted(set(boundaries)):
            raise ConfigurationError(
                "identity review boundaries must be sorted and unique"
            )

    @staticmethod
    def _validate_trajectory_refinement(
        settings: Mapping[str, Any],
    ) -> None:
        label = "overrides.trajectory_refinement"
        PipelineManifest._reject_unknown_settings(
            settings,
            TRAJECTORY_REFINEMENT_OVERRIDE_FIELDS,
            label,
        )
        PipelineManifest._validate_number_setting(
            settings,
            "maximum_speed_ft_sec",
            label,
            0.000001,
            float("inf"),
        )
        PipelineManifest._validate_integer_setting(
            settings,
            "maximum_extrapolation_observations",
            label,
            minimum=0,
        )
        PipelineManifest._validate_integer_setting(
            settings,
            "extrapolation_anchor_count",
            label,
            minimum=3,
        )

    @staticmethod
    def _validate_gap_interpolation(settings: Mapping[str, Any]) -> None:
        label = "overrides.gap_interpolation"
        PipelineManifest._reject_unknown_settings(
            settings,
            GAP_INTERPOLATION_OVERRIDE_FIELDS,
            label,
        )
        PipelineManifest._validate_integer_setting(
            settings,
            "maximum_gap_observations",
            label,
        )
        PipelineManifest._validate_number_setting(
            settings,
            "maximum_endpoint_speed_ft_sec",
            label,
            0.000001,
            float("inf"),
        )

    @staticmethod
    def _validate_visualization(settings: Mapping[str, Any]) -> None:
        label = "overrides.visualization"
        PipelineManifest._reject_unknown_settings(
            settings,
            VISUALIZATION_OVERRIDE_FIELDS,
            label,
        )

        for key in ("review_height", "source_width", "court_panel_width"):
            PipelineManifest._validate_integer_setting(
                settings,
                key,
                label,
                minimum=200,
            )

            if key in settings and settings[key] % 2:
                raise ConfigurationError(f"{label}.{key} must be even")

        PipelineManifest._validate_integer_setting(
            settings,
            "trail_length",
            label,
            minimum=0,
        )
        PipelineManifest._validate_integer_setting(
            settings,
            "sample_count",
            label,
            minimum=2,
        )
        PipelineManifest._validate_integer_setting(
            settings,
            "maximum_event_checkpoints",
            label,
            minimum=0,
        )
        PipelineManifest._validate_number_setting(
            settings,
            "jump_speed_threshold_ft_sec",
            label,
            0.000001,
            float("inf"),
        )

    @property
    def reference_frame_value(self) -> int | str:
        if self.reference_frame_index is None:
            return "middle"

        return self.reference_frame_index

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "possession_id": self.possession_id,
            "video_path": self.video_path.as_posix(),
            "reference_frame_index": self.reference_frame_value,
            "expected_player_count": self.expected_player_count,
            "expected_team_counts": dict(self.expected_team_counts),
            "court": self.court.to_dict(),
            "overrides": {
                section: dict(settings)
                for section, settings in self.overrides.items()
            },
        }


def load_manifest(path: Path) -> PipelineManifest:
    config_path = path.resolve()

    if not config_path.exists():
        raise FileNotFoundError(f"Pipeline config not found: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as input_file:
            payload = json.load(input_file)
    except json.JSONDecodeError as error:
        raise ConfigurationError(
            f"Invalid JSON in pipeline config {config_path}: {error}"
        ) from error

    return PipelineManifest.from_mapping(payload)


@dataclass(frozen=True)
class PipelinePaths:
    repo_root: Path
    possession_id: str
    values: Mapping[str, Path]

    @classmethod
    def build(
        cls,
        repo_root: Path,
        manifest: PipelineManifest,
        config_path: Path | None = None,
    ) -> "PipelinePaths":
        root = repo_root.resolve()
        possession_id = manifest.possession_id
        configs = root / "configs"
        outputs = root / "data" / "outputs"
        tracking = outputs / "tracking"
        classification = outputs / "classification"
        reid = outputs / "reid"
        identity = outputs / "identity"
        court = outputs / "court"
        visualization = outputs / "visualization"
        pipeline = outputs / "pipeline"
        motion_review = court / f"{possession_id}_motion_review"

        if config_path is None:
            pipeline_config = configs / f"{possession_id}_pipeline.json"
        else:
            pipeline_config = config_path.resolve()

        values = {
            "pipeline_config": pipeline_config,
            "pipeline_state": (
                pipeline
                / f"{possession_id}_player_coordinate_pipeline_state.json"
            ),
            "video": root.joinpath(*manifest.video_path.parts),
            "court_polygon_config": configs / f"{possession_id}_court.json",
            "court_calibration_pending": (
                configs / f"{possession_id}_court_calibration.json"
            ),
            "court_calibration_review": (
                configs / f"{possession_id}_court_calibration_review.json"
            ),
            "court_calibration_final": (
                configs / f"{possession_id}_court_calibration_final.json"
            ),
            "court_calibration_refined": (
                configs / f"{possession_id}_court_calibration_refined.json"
            ),
            "reid_review_config": configs / f"{possession_id}_reid_review.json",
            "identity_review_config": (
                configs / f"{possession_id}_identity_review.json"
            ),
            "sequential_identity_review_config": (
                configs / f"{possession_id}_sequential_identity_review.json"
            ),
            "team_balance_review_config": (
                configs / f"{possession_id}_team_balance_review.json"
            ),
            "cross_track_switch_review_config": (
                configs / f"{possession_id}_cross_track_switch_review.json"
            ),
            "tracking_video": tracking / f"{possession_id}_court_filtered.mp4",
            "tracking_tracks": (
                tracking / f"{possession_id}_court_filtered_tracks.csv"
            ),
            "tracking_audit": tracking / f"{possession_id}_tracking_audit.json",
            "uniform_features": (
                classification / f"{possession_id}_uniform_features.csv"
            ),
            "uniform_crops": (
                classification / f"{possession_id}_uniform_crops.jpg"
            ),
            "classified_tracks": (
                classification / f"{possession_id}_team_classified_tracks.csv"
            ),
            "classified_video": (
                classification / f"{possession_id}_team_classified.mp4"
            ),
            "osnet_embeddings": reid / f"{possession_id}_osnet_embeddings.npz",
            "osnet_metadata": reid / f"{possession_id}_osnet_embeddings.json",
            "reid_segments": reid / f"{possession_id}_reid_segments.json",
            "reid_segment_prototypes": (
                reid / f"{possession_id}_reid_segment_prototypes.npz"
            ),
            "segment_match_candidates": (
                reid / f"{possession_id}_segment_match_candidates.json"
            ),
            "segment_player_mapping": (
                identity / f"{possession_id}_segment_player_mapping.json"
            ),
            "identity_annotated_tracks": (
                identity / f"{possession_id}_identity_annotated_tracks.csv"
            ),
            "reconciled_tracks": (
                identity / f"{possession_id}_reconciled_tracks.csv"
            ),
            "identity_review_video": (
                visualization / f"{possession_id}_identity_review.mp4"
            ),
            "identity_review_report": (
                visualization / f"{possession_id}_identity_review.json"
            ),
            "cross_track_switch_candidates": (
                identity
                / "cross_track_switch_review"
                / f"{possession_id}_cross_track_switch_candidates.json"
            ),
            "cross_track_switch_review_dir": (
                identity / "cross_track_switch_review" / possession_id
            ),
            "residual_identity_candidates": (
                identity
                / "residual_identity_review"
                / f"{possession_id}_residual_identity_candidates.json"
            ),
            "residual_identity_review_dir": (
                identity / "residual_identity_review" / possession_id
            ),
            "sequential_identity_candidates": (
                identity
                / "sequential_identity_review"
                / f"{possession_id}_sequential_identity_candidates.json"
            ),
            "sequential_identity_review_dir": (
                identity / "sequential_identity_review" / possession_id
            ),
            "team_balance_candidates": (
                identity
                / "team_balance_review"
                / f"{possession_id}_team_balance_candidates.json"
            ),
            "team_balance_review_dir": (
                identity / "team_balance_review" / possession_id
            ),
            "identity_boundary_review_dir": (
                reid / "identity_boundary_review" / possession_id
            ),
            "calibration_review_dir": (
                court / f"{possession_id}_calibration_review"
            ),
            "calibration_preparation_report": (
                court
                / f"{possession_id}_calibration_review"
                / f"{possession_id}_calibration_review.json"
            ),
            "landmark_review_dir": court / f"{possession_id}_landmark_review",
            "calibration_final_review_dir": (
                court / f"{possession_id}_calibration_final_review"
            ),
            "boundary_refinement_dir": (
                court / f"{possession_id}_boundary_refinement"
            ),
            "motion_review_dir": motion_review,
            "camera_homographies": (
                motion_review / f"{possession_id}_camera_homographies.npz"
            ),
            "court_motion_video": (
                motion_review / f"{possession_id}_court_motion_review.mp4"
            ),
            "court_motion_report": (
                motion_review / f"{possession_id}_court_motion_review.json"
            ),
            "player_coordinates": (
                court / f"{possession_id}_player_court_coordinates.csv"
            ),
            "player_coordinates_report": (
                court / f"{possession_id}_player_court_coordinates.json"
            ),
            "player_coordinates_review_video": (
                visualization
                / f"{possession_id}_player_court_coordinates_review.mp4"
            ),
            "player_coordinates_review_report": (
                visualization
                / f"{possession_id}_player_court_coordinates_review.json"
            ),
            "player_coordinates_checkpoints": (
                visualization
                / f"{possession_id}_player_court_coordinates_checkpoints"
            ),
            "refined_coordinates": (
                court / f"{possession_id}_player_court_coordinates_refined.csv"
            ),
            "trajectory_refinement_audit": (
                court
                / f"{possession_id}_player_court_trajectory_refinement_audit.csv"
            ),
            "trajectory_refinement_report": (
                court
                / f"{possession_id}_player_court_trajectory_refinement.json"
            ),
            "gap_filled_coordinates": (
                court
                / f"{possession_id}_player_court_coordinates_gap_filled.csv"
            ),
            "gap_interpolation_audit": (
                court
                / (
                    f"{possession_id}_player_court_trajectory_"
                    "gap_interpolation_audit.csv"
                )
            ),
            "gap_interpolation_report": (
                court
                / (
                    f"{possession_id}_player_court_trajectory_"
                    "gap_interpolation.json"
                )
            ),
            "gap_filled_review_video": (
                visualization
                / f"{possession_id}_player_court_coordinates_gap_filled_review.mp4"
            ),
            "gap_filled_review_report": (
                visualization
                / f"{possession_id}_player_court_coordinates_gap_filled_review.json"
            ),
            "gap_filled_checkpoints": (
                visualization
                / f"{possession_id}_player_court_coordinates_gap_filled_checkpoints"
            ),
        }

        return cls(
            repo_root=root,
            possession_id=possession_id,
            values=MappingProxyType(values),
        )

    def __getitem__(self, key: str) -> Path:
        try:
            return self.values[key]
        except KeyError as error:
            raise KeyError(f"Unknown pipeline path key: {key}") from error

    def relative(self, key: str) -> str:
        path = self[key].resolve()

        try:
            return path.relative_to(self.repo_root).as_posix()
        except ValueError as error:
            raise ConfigurationError(
                f"Pipeline path escapes repository root: {key}={path}"
            ) from error

    def as_dict(self, relative: bool = True) -> dict[str, str]:
        if relative:
            return {
                key: self.relative(key)
                for key in sorted(self.values)
            }

        return {
            key: str(path)
            for key, path in sorted(self.values.items())
        }
