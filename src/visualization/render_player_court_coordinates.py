import argparse
import csv
import json
import math
import os
from collections import Counter, defaultdict, deque
from pathlib import Path

try:
    import cv2
except ModuleNotFoundError:
    cv2 = None

import numpy as np


DEFAULT_VIDEO_PATH = Path("data/clips/possession_001.mp4")
DEFAULT_COORDINATES_PATH = Path(
    "data/outputs/court/possession_001_player_court_coordinates.csv"
)
DEFAULT_COORDINATE_REPORT_PATH = Path(
    "data/outputs/court/possession_001_player_court_coordinates.json"
)
DEFAULT_CALIBRATION_PATH = Path(
    "configs/possession_001_court_calibration_final.json"
)
DEFAULT_OUTPUT_PATH = Path(
    "data/outputs/visualization/"
    "possession_001_player_court_coordinates_review.mp4"
)
DEFAULT_REPORT_PATH = Path(
    "data/outputs/visualization/"
    "possession_001_player_court_coordinates_review.json"
)
DEFAULT_CHECKPOINTS_DIR = Path(
    "data/outputs/visualization/"
    "possession_001_player_court_coordinates_checkpoints"
)

EXPECTED_PLAYER_COUNT = 10
EXPECTED_TEAM_COUNTS = {"white": 5, "dark": 5}
EXPECTED_COORDINATE_STATUS = (
    "validated_player_court_coordinates_exported"
)
EXPECTED_REFINEMENT_STATUS = (
    "refined_player_court_trajectories_pending_visual_review"
)

OPTIONAL_REFINEMENT_FIELDS = {
    "raw_court_x_ft",
    "raw_court_y_ft",
    "raw_court_position_in_half_court",
    "trajectory_refinement_applied",
    "trajectory_refinement_method",
    "trajectory_refinement_reason",
    "trajectory_correction_distance_ft",
    "trajectory_anchor_frames",
    "trajectory_trusted_path_observation",
    "trajectory_raw_jump_candidate",
}

WHITE_PALETTE = [
    (255, 255, 0),
    (255, 190, 40),
    (170, 255, 40),
    (255, 130, 130),
    (190, 255, 130),
]
DARK_PALETTE = [
    (40, 90, 255),
    (20, 180, 255),
    (100, 70, 255),
    (210, 80, 255),
    (50, 220, 255),
]

BACKGROUND_COLOR = (18, 18, 18)
COURT_FILL_COLOR = (72, 142, 196)
COURT_LINE_COLOR = (235, 235, 235)
COURT_LABEL_COLOR = (210, 210, 210)
PANEL_COLOR = (15, 15, 15)
TEXT_COLOR = (245, 245, 245)
GOOD_COLOR = (90, 230, 90)
WARNING_COLOR = (0, 205, 255)
OUTSIDE_COLOR = (40, 40, 255)
REFINED_COLOR = (255, 255, 255)
RAW_GHOST_COLOR = (150, 150, 150)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Render synchronized source-video and top-down court views "
            "for validated player court coordinates."
        )
    )
    parser.add_argument(
        "--video",
        type=Path,
        default=DEFAULT_VIDEO_PATH,
        help="Source possession video.",
    )
    parser.add_argument(
        "--coordinates",
        type=Path,
        default=DEFAULT_COORDINATES_PATH,
        help="Validated player court-coordinate CSV.",
    )
    parser.add_argument(
        "--coordinate-report",
        type=Path,
        default=DEFAULT_COORDINATE_REPORT_PATH,
        help="Coordinate-export validation report.",
    )
    parser.add_argument(
        "--calibration",
        type=Path,
        default=DEFAULT_CALIBRATION_PATH,
        help="Reviewed court calibration JSON.",
    )
    parser.add_argument(
        "--refinement-report",
        type=Path,
        default=None,
        help=(
            "Optional trajectory-refinement report used to validate "
            "refined coordinates and select correction checkpoints."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Synchronized review MP4.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Review validation JSON.",
    )
    parser.add_argument(
        "--checkpoints-dir",
        type=Path,
        default=DEFAULT_CHECKPOINTS_DIR,
        help="Directory for selected synchronized review frames.",
    )
    parser.add_argument(
        "--review-height",
        type=int,
        default=720,
        help="Output video height in pixels.",
    )
    parser.add_argument(
        "--source-width",
        type=int,
        default=1280,
        help="Width of the resized source-video panel.",
    )
    parser.add_argument(
        "--court-panel-width",
        type=int,
        default=560,
        help="Width of the top-down court panel.",
    )
    parser.add_argument(
        "--trail-length",
        type=int,
        default=20,
        help="Consecutive positions retained in each player trail.",
    )
    parser.add_argument(
        "--jump-speed-threshold-ft-sec",
        type=float,
        default=45.0,
        help="Speed above which movement is listed for visual review.",
    )
    parser.add_argument(
        "--sample-count",
        type=int,
        default=12,
        help="Number of evenly spaced checkpoint frames.",
    )
    parser.add_argument(
        "--maximum-event-checkpoints",
        type=int,
        default=8,
        help="Maximum additional outside/jump checkpoint frames.",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Validate and write the report without rendering media.",
    )
    args = parser.parse_args()

    for name in (
        "review_height",
        "source_width",
        "court_panel_width",
    ):
        value = getattr(args, name)

        if value < 200 or value % 2:
            parser.error(
                f"--{name.replace('_', '-')} must be an even integer "
                "of at least 200"
            )

    if args.trail_length < 0:
        parser.error("--trail-length cannot be negative")

    if args.jump_speed_threshold_ft_sec <= 0:
        parser.error(
            "--jump-speed-threshold-ft-sec must be positive"
        )

    if args.sample_count < 2:
        parser.error("--sample-count must be at least 2")

    if args.maximum_event_checkpoints < 0:
        parser.error("--maximum-event-checkpoints cannot be negative")

    return args


def load_json(path, label):
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")

    with path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def parse_int(value, field_name, row_number):
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"Invalid integer in {field_name} at CSV row "
            f"{row_number}: {value!r}"
        ) from error


def parse_float(value, field_name, row_number):
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"Invalid number in {field_name} at CSV row "
            f"{row_number}: {value!r}"
        ) from error

    if not math.isfinite(parsed):
        raise ValueError(
            f"Non-finite number in {field_name} at CSV row "
            f"{row_number}: {value!r}"
        )

    return parsed


def parse_bool(value, field_name, row_number):
    normalized = str(value).strip().lower()

    if normalized == "true":
        return True

    if normalized == "false":
        return False

    raise ValueError(
        f"Invalid boolean in {field_name} at CSV row "
        f"{row_number}: {value!r}"
    )


def player_sort_key(player_id):
    team, _, suffix = player_id.partition("_p")

    try:
        number = int(suffix)
    except ValueError:
        number = 10_000

    return (
        {"white": 0, "dark": 1}.get(team, 2),
        number,
        player_id,
    )


def short_player_label(player_id):
    team, _, suffix = player_id.partition("_p")
    prefix = {"white": "W", "dark": "D"}.get(team, "?")
    return f"{prefix}{suffix}"


def load_coordinate_rows(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Player court-coordinate CSV not found: {path}"
        )

    required_fields = {
        "frame_index",
        "timestamp_sec",
        "track_id",
        "confidence",
        "x1",
        "y1",
        "x2",
        "y2",
        "floor_x",
        "floor_y",
        "player_id",
        "reconciled_team",
        "identity_status",
        "court_x_ft",
        "court_y_ft",
        "court_position_in_half_court",
        "camera_raw_transform_valid",
        "camera_raw_transform_accepted",
    }
    rows_by_frame = defaultdict(list)
    rows_by_player = defaultdict(list)
    team_by_player = {}
    row_count = 0

    with path.open("r", newline="", encoding="utf-8") as input_file:
        reader = csv.DictReader(input_file)
        fieldnames = set(reader.fieldnames or [])
        missing_fields = sorted(required_fields - fieldnames)

        if missing_fields:
            raise ValueError(
                "Court-coordinate CSV is missing required fields: "
                f"{missing_fields}"
            )

        present_refinement_fields = (
            fieldnames.intersection(OPTIONAL_REFINEMENT_FIELDS)
        )

        if present_refinement_fields and (
            present_refinement_fields != OPTIONAL_REFINEMENT_FIELDS
        ):
            missing_refinement_fields = sorted(
                OPTIONAL_REFINEMENT_FIELDS - present_refinement_fields
            )
            raise ValueError(
                "Refined coordinate CSV has an incomplete audit schema: "
                f"{missing_refinement_fields}"
            )

        has_refinement = bool(present_refinement_fields)

        for row_number, raw_row in enumerate(reader, 2):
            row = dict(raw_row)
            row["frame_index"] = parse_int(
                raw_row["frame_index"], "frame_index", row_number
            )
            row["track_id"] = parse_int(
                raw_row["track_id"], "track_id", row_number
            )

            for field_name in (
                "timestamp_sec",
                "confidence",
                "x1",
                "y1",
                "x2",
                "y2",
                "floor_x",
                "floor_y",
                "court_x_ft",
                "court_y_ft",
            ):
                row[field_name] = parse_float(
                    raw_row[field_name], field_name, row_number
                )

            for field_name in (
                "court_position_in_half_court",
                "camera_raw_transform_valid",
                "camera_raw_transform_accepted",
            ):
                row[field_name] = parse_bool(
                    raw_row[field_name], field_name, row_number
                )

            if has_refinement:
                for field_name in (
                    "raw_court_x_ft",
                    "raw_court_y_ft",
                    "trajectory_correction_distance_ft",
                ):
                    row[field_name] = parse_float(
                        raw_row[field_name], field_name, row_number
                    )

                for field_name in (
                    "raw_court_position_in_half_court",
                    "trajectory_refinement_applied",
                    "trajectory_trusted_path_observation",
                    "trajectory_raw_jump_candidate",
                ):
                    row[field_name] = parse_bool(
                        raw_row[field_name], field_name, row_number
                    )

                for field_name in (
                    "trajectory_refinement_method",
                    "trajectory_refinement_reason",
                    "trajectory_anchor_frames",
                ):
                    row[field_name] = raw_row[field_name].strip()
            else:
                row["raw_court_x_ft"] = row["court_x_ft"]
                row["raw_court_y_ft"] = row["court_y_ft"]
                row["raw_court_position_in_half_court"] = row[
                    "court_position_in_half_court"
                ]
                row["trajectory_refinement_applied"] = False
                row["trajectory_refinement_method"] = (
                    "unrefined_source_coordinate"
                )
                row["trajectory_refinement_reason"] = ""
                row["trajectory_correction_distance_ft"] = 0.0
                row["trajectory_anchor_frames"] = ""
                row["trajectory_trusted_path_observation"] = True
                row["trajectory_raw_jump_candidate"] = False

            row["player_id"] = raw_row["player_id"].strip()
            row["reconciled_team"] = raw_row[
                "reconciled_team"
            ].strip()
            row["identity_status"] = raw_row[
                "identity_status"
            ].strip()

            if row["frame_index"] < 0:
                raise ValueError(
                    f"Negative frame index at CSV row {row_number}"
                )

            if not row["player_id"]:
                raise ValueError(f"Blank player_id at CSV row {row_number}")

            if row["reconciled_team"] not in EXPECTED_TEAM_COUNTS:
                raise ValueError(
                    f"Unexpected team at CSV row {row_number}: "
                    f"{row['reconciled_team']!r}"
                )

            if row["identity_status"] != "active":
                raise ValueError(
                    f"Non-active identity at CSV row {row_number}: "
                    f"{row['identity_status']!r}"
                )

            if row["x2"] <= row["x1"] or row["y2"] <= row["y1"]:
                raise ValueError(
                    f"Invalid bounding box at CSV row {row_number}"
                )

            previous_team = team_by_player.setdefault(
                row["player_id"], row["reconciled_team"]
            )

            if previous_team != row["reconciled_team"]:
                raise ValueError(
                    f"Player {row['player_id']} changes team from "
                    f"{previous_team} to {row['reconciled_team']}"
                )

            rows_by_frame[row["frame_index"]].append(row)
            rows_by_player[row["player_id"]].append(row)
            row_count += 1

    if not row_count:
        raise ValueError(f"No coordinate rows found in {path}")

    for frame_index, rows in rows_by_frame.items():
        player_ids = [row["player_id"] for row in rows]

        if len(player_ids) != len(set(player_ids)):
            raise ValueError(
                "Duplicate player rows in frame "
                f"{frame_index}: {player_ids}"
            )

        transform_flags = {
            (
                row["camera_raw_transform_valid"],
                row["camera_raw_transform_accepted"],
            )
            for row in rows
        }

        if len(transform_flags) > 1:
            raise ValueError(
                "Camera transform flags disagree within frame "
                f"{frame_index}: {sorted(transform_flags)}"
            )

        rows.sort(key=lambda row: player_sort_key(row["player_id"]))

    for rows in rows_by_player.values():
        rows.sort(key=lambda row: row["frame_index"])

    return (
        dict(rows_by_frame),
        dict(rows_by_player),
        team_by_player,
        row_count,
    )


def validate_coordinate_contract(
    rows_by_frame,
    team_by_player,
    row_count,
    coordinate_report,
):
    if coordinate_report.get("status") != EXPECTED_COORDINATE_STATUS:
        raise ValueError(
            "Coordinate report does not have the validated export status: "
            f"{coordinate_report.get('status')!r}"
        )

    validation = coordinate_report.get("validation", {})

    if int(validation.get("row_count", -1)) != row_count:
        raise ValueError(
            "Coordinate report row count does not match the CSV: "
            f"{validation.get('row_count')} != {row_count}"
        )

    if int(validation.get("unique_player_count", -1)) != len(
        team_by_player
    ):
        raise ValueError(
            "Coordinate report player count does not match the CSV: "
            f"{validation.get('unique_player_count')} != "
            f"{len(team_by_player)}"
        )

    if len(team_by_player) != EXPECTED_PLAYER_COUNT:
        raise ValueError(
            f"Expected ten players, found {len(team_by_player)}: "
            f"{sorted(team_by_player, key=player_sort_key)}"
        )

    team_counts = Counter(team_by_player.values())

    if dict(team_counts) != EXPECTED_TEAM_COUNTS:
        raise ValueError(
            "Expected five white and five dark players, found "
            f"{dict(team_counts)}"
        )

    reported_team_counts = validation.get("players_by_team", {})

    if reported_team_counts != dict(sorted(team_counts.items())):
        raise ValueError(
            "Coordinate report team counts do not match the CSV: "
            f"{reported_team_counts} != "
            f"{dict(sorted(team_counts.items()))}"
        )

    outside_count = sum(
        not row["court_position_in_half_court"]
        for rows in rows_by_frame.values()
        for row in rows
    )
    reported_outside_count = int(
        coordinate_report.get("court_position_audit", {}).get(
            "outside_half_court_row_count", -1
        )
    )

    if reported_outside_count != outside_count:
        raise ValueError(
            "Coordinate report outside-row count does not match the CSV: "
            f"{reported_outside_count} != {outside_count}"
        )

    for frame_index, rows in rows_by_frame.items():
        if len(rows) > EXPECTED_PLAYER_COUNT:
            raise ValueError(
                f"Frame {frame_index} contains more than ten players"
            )

        if len(rows) == EXPECTED_PLAYER_COUNT:
            frame_team_counts = Counter(
                row["reconciled_team"] for row in rows
            )

            if dict(frame_team_counts) != EXPECTED_TEAM_COUNTS:
                raise ValueError(
                    f"Frame {frame_index} is not five-versus-five: "
                    f"{dict(frame_team_counts)}"
                )

    return dict(sorted(team_counts.items()))


def open_video(path):
    if cv2 is None:
        raise ModuleNotFoundError(
            "OpenCV is required for player-coordinate visualization"
        )

    if not path.exists():
        raise FileNotFoundError(f"Source video not found: {path}")

    capture = cv2.VideoCapture(str(path))

    if not capture.isOpened():
        raise RuntimeError(f"Could not open source video: {path}")

    metadata = {
        "fps": float(capture.get(cv2.CAP_PROP_FPS)),
        "frame_count": int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
        "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    }

    if (
        metadata["fps"] <= 0
        or metadata["frame_count"] <= 0
        or metadata["width"] <= 0
        or metadata["height"] <= 0
    ):
        capture.release()
        raise ValueError(f"Source video metadata is invalid: {metadata}")

    return capture, metadata


def validate_video_and_calibration(
    metadata,
    calibration,
    coordinate_report,
    rows_by_frame,
):
    calibration_metadata = calibration.get("video_metadata", {})
    coordinate_validation = coordinate_report.get("validation", {})

    for field_name in ("frame_count", "width", "height"):
        expected = int(calibration_metadata.get(field_name, -1))

        if metadata[field_name] != expected:
            raise ValueError(
                f"Video {field_name} does not match calibration: "
                f"{metadata[field_name]} != {expected}"
            )

    calibration_fps = float(calibration_metadata.get("fps", -1.0))

    if not math.isclose(
        metadata["fps"], calibration_fps, rel_tol=0.0, abs_tol=0.01
    ):
        raise ValueError(
            "Video FPS does not match calibration: "
            f"{metadata['fps']} != {calibration_fps}"
        )

    reported_frame_count = int(
        coordinate_validation.get(
            "frame_count_in_homography_artifact", -1
        )
    )

    if reported_frame_count != metadata["frame_count"]:
        raise ValueError(
            "Coordinate homography frame count does not match video: "
            f"{reported_frame_count} != {metadata['frame_count']}"
        )

    if max(rows_by_frame) >= metadata["frame_count"]:
        raise ValueError(
            "Coordinate CSV contains a frame outside the video: "
            f"{max(rows_by_frame)} >= {metadata['frame_count']}"
        )


def load_court_model(calibration):
    court_model = calibration.get("court_model", {})

    required_dimensions = {
        "half_court_length_ft",
        "court_width_ft",
        "lane_width_ft",
        "baseline_to_free_throw_line_ft",
        "basket_center_from_baseline_ft",
        "three_point_radius_ft",
    }
    missing = sorted(required_dimensions - set(court_model))

    if missing:
        raise ValueError(
            f"Calibration court model is missing dimensions: {missing}"
        )

    dimensions = {
        name: float(court_model[name]) for name in required_dimensions
    }

    if any(value <= 0 for value in dimensions.values()):
        raise ValueError("Court model dimensions must be positive")

    return court_model, dimensions


def validate_coordinate_bounds_flags(rows_by_frame, dimensions):
    half_length = dimensions["half_court_length_ft"]
    court_width = dimensions["court_width_ft"]
    mismatches = []

    for frame_index, rows in rows_by_frame.items():
        for row in rows:
            expected_inside = (
                0.0 <= row["court_x_ft"] <= half_length
                and 0.0 <= row["court_y_ft"] <= court_width
            )

            if expected_inside != row["court_position_in_half_court"]:
                mismatches.append((frame_index, row["player_id"]))

    if mismatches:
        raise ValueError(
            "Court-bound flags do not match exported coordinates: "
            f"{mismatches[:20]}"
        )


def validate_refined_coordinate_audit(rows_by_frame, dimensions):
    half_length = dimensions["half_court_length_ft"]
    court_width = dimensions["court_width_ft"]
    corrected_count = 0

    for rows in rows_by_frame.values():
        for row in rows:
            raw_inside = (
                0.0 <= row["raw_court_x_ft"] <= half_length
                and 0.0 <= row["raw_court_y_ft"] <= court_width
            )

            if raw_inside != row[
                "raw_court_position_in_half_court"
            ]:
                raise ValueError(
                    "Raw refinement boundary flag disagrees at frame "
                    f"{row['frame_index']} for {row['player_id']}"
                )

            expected_distance = math.hypot(
                row["court_x_ft"] - row["raw_court_x_ft"],
                row["court_y_ft"] - row["raw_court_y_ft"],
            )

            if not math.isclose(
                expected_distance,
                row["trajectory_correction_distance_ft"],
                rel_tol=0.0,
                abs_tol=2e-6,
            ):
                raise ValueError(
                    "Refinement correction distance disagrees at frame "
                    f"{row['frame_index']} for {row['player_id']}"
                )

            applied = row["trajectory_refinement_applied"]

            if applied != (expected_distance > 1e-9):
                raise ValueError(
                    "Refinement-applied flag disagrees at frame "
                    f"{row['frame_index']} for {row['player_id']}"
                )

            corrected_count += int(applied)

    return corrected_count


def validate_refinement_report_contract(
    refinement_report,
    row_count,
    frame_count,
    coordinate_analysis,
):
    if refinement_report.get("status") != EXPECTED_REFINEMENT_STATUS:
        raise ValueError(
            "Trajectory-refinement report has an unexpected status: "
            f"{refinement_report.get('status')!r}"
        )

    validation = refinement_report.get("validation", {})
    trusted = refinement_report.get("trusted_path_audit", {})
    motion = refinement_report.get("motion_audit", {})
    boundary = refinement_report.get("boundary_audit", {})
    refinement = coordinate_analysis["trajectory_refinement"]

    if int(validation.get("row_count", -1)) != row_count:
        raise ValueError(
            "Trajectory-refinement report row count does not match CSV"
        )

    if int(validation.get("frame_count", -1)) != frame_count:
        raise ValueError(
            "Trajectory-refinement report frame count does not match video"
        )

    if int(trusted.get("corrected_observation_count", -1)) != int(
        refinement["corrected_row_count"]
    ):
        raise ValueError(
            "Trajectory-refinement corrected count does not match CSV"
        )

    refined_motion = motion.get("refined", {})

    if int(refined_motion.get("candidate_count", -1)) != int(
        coordinate_analysis["jump_candidate_count"]
    ):
        raise ValueError(
            "Trajectory-refinement motion count does not match review"
        )

    if int(
        boundary.get("refined_outside_observation_count", -1)
    ) != int(coordinate_analysis["outside_row_count"]):
        raise ValueError(
            "Trajectory-refinement outside count does not match review"
        )

    checkpoint_frames = [
        int(frame_index)
        for frame_index in trusted.get(
            "recommended_checkpoint_frames", []
        )
    ]
    invalid_frames = [
        frame_index
        for frame_index in checkpoint_frames
        if not 0 <= frame_index < frame_count
    ]

    if invalid_frames:
        raise ValueError(
            "Trajectory-refinement report has invalid checkpoints: "
            f"{invalid_frames}"
        )

    return checkpoint_frames


def analyze_coordinates(
    rows_by_frame,
    rows_by_player,
    frame_count,
    fps,
    jump_speed_threshold,
    dimensions,
):
    frame_count_distribution = Counter(
        len(rows_by_frame.get(frame_index, []))
        for frame_index in range(frame_count)
    )
    outside_rows = [
        row
        for rows in rows_by_frame.values()
        for row in rows
        if not row["court_position_in_half_court"]
    ]
    outside_by_player = Counter(
        row["player_id"] for row in outside_rows
    )
    corrected_rows = [
        row
        for rows in rows_by_frame.values()
        for row in rows
        if row["trajectory_refinement_applied"]
    ]
    corrected_by_player = Counter(
        row["player_id"] for row in corrected_rows
    )
    corrected_by_method = Counter(
        row["trajectory_refinement_method"] for row in corrected_rows
    )
    jump_candidates = []
    per_player = {}

    for player_id, rows in sorted(
        rows_by_player.items(), key=lambda item: player_sort_key(item[0])
    ):
        speeds = []
        player_candidates = []

        for first, second in zip(rows, rows[1:]):
            frame_gap = second["frame_index"] - first["frame_index"]

            if frame_gap <= 0:
                raise ValueError(
                    f"Non-increasing frames for player {player_id}"
                )

            distance = math.hypot(
                second["court_x_ft"] - first["court_x_ft"],
                second["court_y_ft"] - first["court_y_ft"],
            )
            speed = distance * fps / frame_gap
            speeds.append(speed)

            if speed > jump_speed_threshold:
                candidate = {
                    "player_id": player_id,
                    "from_frame": first["frame_index"],
                    "to_frame": second["frame_index"],
                    "frame_gap": frame_gap,
                    "distance_ft": round(distance, 4),
                    "speed_ft_sec": round(speed, 4),
                }
                jump_candidates.append(candidate)
                player_candidates.append(candidate)

        per_player[player_id] = {
            "team": rows[0]["reconciled_team"],
            "row_count": len(rows),
            "first_frame": rows[0]["frame_index"],
            "last_frame": rows[-1]["frame_index"],
            "outside_row_count": outside_by_player.get(player_id, 0),
            "maximum_observed_speed_ft_sec": (
                None if not speeds else round(max(speeds), 4)
            ),
            "jump_candidate_count": len(player_candidates),
        }

    jump_candidates.sort(
        key=lambda candidate: (
            -candidate["speed_ft_sec"],
            candidate["to_frame"],
            candidate["player_id"],
        )
    )
    outside_records = []

    for row in sorted(
        outside_rows,
        key=lambda row: (row["frame_index"], row["player_id"]),
    ):
        court_x = row["court_x_ft"]
        court_y = row["court_y_ft"]
        half_length = dimensions["half_court_length_ft"]
        court_width = dimensions["court_width_ft"]

        if court_x < 0.0:
            boundary = "past_right_baseline"
            outside_distance = -court_x
        elif court_x > half_length:
            boundary = "past_midcourt"
            outside_distance = court_x - half_length
        elif court_y < 0.0:
            boundary = "past_far_sideline"
            outside_distance = -court_y
        else:
            boundary = "past_near_sideline"
            outside_distance = court_y - court_width

        outside_records.append(
            {
                "frame_index": row["frame_index"],
                "player_id": row["player_id"],
                "boundary": boundary,
                "outside_distance_ft": round(outside_distance, 4),
                "court_x_ft": round(court_x, 4),
                "court_y_ft": round(court_y, 4),
            }
        )

    corrected_records = []

    for row in sorted(
        corrected_rows,
        key=lambda item: (
            -item["trajectory_correction_distance_ft"],
            item["frame_index"],
            player_sort_key(item["player_id"]),
        ),
    ):
        corrected_records.append(
            {
                "frame_index": row["frame_index"],
                "player_id": row["player_id"],
                "raw_court_x_ft": round(
                    row["raw_court_x_ft"], 4
                ),
                "raw_court_y_ft": round(
                    row["raw_court_y_ft"], 4
                ),
                "refined_court_x_ft": round(row["court_x_ft"], 4),
                "refined_court_y_ft": round(row["court_y_ft"], 4),
                "correction_distance_ft": round(
                    row["trajectory_correction_distance_ft"], 4
                ),
                "method": row["trajectory_refinement_method"],
                "anchor_frames": row["trajectory_anchor_frames"],
            }
        )

    return {
        "frame_player_count_distribution": {
            str(count): frame_count_distribution[count]
            for count in sorted(frame_count_distribution)
        },
        "frames_with_all_ten_players": frame_count_distribution.get(10, 0),
        "outside_row_count": len(outside_rows),
        "outside_rows_by_player": dict(sorted(outside_by_player.items())),
        "outside_rows": outside_records,
        "jump_speed_threshold_ft_sec": jump_speed_threshold,
        "jump_candidate_count": len(jump_candidates),
        "jump_candidates": jump_candidates,
        "trajectory_refinement": {
            "present": bool(corrected_rows),
            "corrected_row_count": len(corrected_rows),
            "corrected_by_player": dict(
                sorted(
                    corrected_by_player.items(),
                    key=lambda item: player_sort_key(item[0]),
                )
            ),
            "corrected_by_method": dict(
                sorted(corrected_by_method.items())
            ),
            "corrected_rows": corrected_records,
        },
        "per_player": per_player,
    }


def build_identity_colors(team_by_player):
    colors = {}

    for team, palette in (
        ("white", WHITE_PALETTE),
        ("dark", DARK_PALETTE),
    ):
        players = sorted(
            (
                player_id
                for player_id, player_team in team_by_player.items()
                if player_team == team
            ),
            key=player_sort_key,
        )

        if len(players) != len(palette):
            raise ValueError(
                f"Expected five {team} players for the color palette, "
                f"found {len(players)}"
            )

        for player_id, color in zip(players, palette):
            colors[player_id] = color

    return colors


def blend_panel(frame, first_point, second_point, opacity=0.76):
    overlay = frame.copy()
    cv2.rectangle(
        overlay, first_point, second_point, PANEL_COLOR, -1
    )
    cv2.addWeighted(
        overlay, opacity, frame, 1.0 - opacity, 0, frame
    )


def draw_text(
    frame,
    text,
    origin,
    color=TEXT_COLOR,
    scale=0.55,
    thickness=1,
):
    cv2.putText(
        frame,
        text,
        origin,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        thickness,
        cv2.LINE_AA,
    )


def draw_source_annotations(frame, frame_index, fps, rows, colors):
    annotated = frame.copy()

    for row in rows:
        color = colors[row["player_id"]]
        x1 = max(0, int(round(row["x1"])))
        y1 = max(0, int(round(row["y1"])))
        x2 = min(
            annotated.shape[1] - 1, int(round(row["x2"]))
        )
        y2 = min(
            annotated.shape[0] - 1, int(round(row["y2"]))
        )
        floor_point = (
            min(
                annotated.shape[1] - 1,
                max(0, int(round(row["floor_x"]))),
            ),
            min(
                annotated.shape[0] - 1,
                max(0, int(round(row["floor_y"]))),
            ),
        )
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
        cv2.circle(
            annotated, floor_point, 7, (0, 0, 0), -1, cv2.LINE_AA
        )
        cv2.circle(
            annotated, floor_point, 5, color, -1, cv2.LINE_AA
        )

        if row["trajectory_refinement_applied"]:
            cv2.circle(
                annotated,
                floor_point,
                10,
                REFINED_COLOR,
                2,
                cv2.LINE_AA,
            )

        label = (
            f"{row['player_id']} | "
            f"({row['court_x_ft']:.1f}, {row['court_y_ft']:.1f})ft"
        )

        if row["trajectory_refinement_applied"]:
            label += (
                " | refined "
                f"{row['trajectory_correction_distance_ft']:.1f}ft"
            )

        label_size = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 2
        )[0]
        panel_x = min(
            max(0, x1),
            max(0, annotated.shape[1] - label_size[0] - 17),
        )
        panel_y = y1 - 29

        if panel_y < 0:
            panel_y = min(annotated.shape[0] - 30, y1 + 4)

        blend_panel(
            annotated,
            (panel_x, panel_y),
            (panel_x + label_size[0] + 16, panel_y + 28),
            opacity=0.8,
        )
        cv2.rectangle(
            annotated,
            (panel_x, panel_y),
            (panel_x + 5, panel_y + 28),
            color,
            -1,
        )
        draw_text(
            annotated,
            label,
            (panel_x + 10, panel_y + 20),
            scale=0.52,
            thickness=2,
        )

    team_counts = Counter(row["reconciled_team"] for row in rows)
    player_count = len(rows)
    refined_count = sum(
        row["trajectory_refinement_applied"] for row in rows
    )
    frame_flags = {
        row["camera_raw_transform_accepted"] for row in rows
    }
    raw_accepted = None if not frame_flags else next(iter(frame_flags))
    motion_label = (
        "no player rows"
        if raw_accepted is None
        else (
            "raw motion accepted"
            if raw_accepted
            else "robust motion replacement"
        )
    )
    status_color = (
        GOOD_COLOR if player_count == EXPECTED_PLAYER_COUNT else WARNING_COLOR
    )
    header_right = min(annotated.shape[1] - 15, 990)
    blend_panel(annotated, (15, 15), (header_right, 105))
    draw_text(
        annotated,
        (
            f"Frame {frame_index} | {frame_index / fps:.2f}s | "
            "PLAYER COURT COORDINATE REVIEW"
        ),
        (28, 47),
        scale=0.68,
        thickness=2,
    )
    draw_text(
        annotated,
        (
            f"Players {player_count}/10 | "
            f"white {team_counts.get('white', 0)}/5 | "
            f"dark {team_counts.get('dark', 0)}/5 | "
            f"refined {refined_count} | {motion_label}"
        ),
        (28, 82),
        color=status_color,
        scale=0.64,
        thickness=2,
    )
    return annotated


def court_layout(panel_width, panel_height, dimensions):
    header_height = 84
    footer_height = 112
    horizontal_margin = 58
    vertical_margin = 18
    half_length = dimensions["half_court_length_ft"]
    court_width = dimensions["court_width_ft"]
    scale = min(
        (panel_width - 2 * horizontal_margin) / half_length,
        (
            panel_height
            - header_height
            - footer_height
            - 2 * vertical_margin
        )
        / court_width,
    )
    rendered_width = half_length * scale
    rendered_height = court_width * scale
    left = int(round((panel_width - rendered_width) / 2))
    top = int(
        round(
            header_height
            + vertical_margin
            + (
                panel_height
                - header_height
                - footer_height
                - 2 * vertical_margin
                - rendered_height
            )
            / 2
        )
    )
    return {
        "left": left,
        "top": top,
        "scale": scale,
        "right": int(round(left + rendered_width)),
        "bottom": int(round(top + rendered_height)),
        "footer_top": panel_height - footer_height,
    }


def court_to_pixel(court_x, court_y, layout, dimensions):
    pixel_x = layout["left"] + (
        dimensions["half_court_length_ft"] - court_x
    ) * layout["scale"]
    pixel_y = layout["top"] + court_y * layout["scale"]
    return int(round(pixel_x)), int(round(pixel_y))


def clipped_arc_points(
    center_x,
    center_y,
    radius,
    layout,
    dimensions,
    minimum_x,
    maximum_x,
):
    point_groups = []
    current_group = []

    for angle in np.linspace(-math.pi, math.pi, 361):
        court_x = center_x + radius * math.cos(angle)
        court_y = center_y + radius * math.sin(angle)
        valid = (
            minimum_x <= court_x <= maximum_x
            and 0.0 <= court_y <= dimensions["court_width_ft"]
        )

        if valid:
            current_group.append(
                court_to_pixel(court_x, court_y, layout, dimensions)
            )
        elif len(current_group) >= 2:
            point_groups.append(current_group)
            current_group = []
        else:
            current_group = []

    if len(current_group) >= 2:
        point_groups.append(current_group)

    return point_groups


def draw_court_model(panel, layout, dimensions):
    cv2.rectangle(
        panel,
        (layout["left"], layout["top"]),
        (layout["right"], layout["bottom"]),
        COURT_FILL_COLOR,
        -1,
    )
    cv2.rectangle(
        panel,
        (layout["left"], layout["top"]),
        (layout["right"], layout["bottom"]),
        COURT_LINE_COLOR,
        3,
    )
    lane_near_y = (
        dimensions["court_width_ft"]
        + dimensions["lane_width_ft"]
    ) / 2.0
    lane_far_y = (
        dimensions["court_width_ft"]
        - dimensions["lane_width_ft"]
    ) / 2.0
    free_throw_x = dimensions["baseline_to_free_throw_line_ft"]
    lane_corners = [
        court_to_pixel(0.0, lane_far_y, layout, dimensions),
        court_to_pixel(free_throw_x, lane_far_y, layout, dimensions),
        court_to_pixel(free_throw_x, lane_near_y, layout, dimensions),
        court_to_pixel(0.0, lane_near_y, layout, dimensions),
    ]
    cv2.polylines(
        panel,
        [np.asarray(lane_corners, dtype=np.int32)],
        True,
        COURT_LINE_COLOR,
        2,
        cv2.LINE_AA,
    )
    free_throw_center = court_to_pixel(
        free_throw_x,
        dimensions["court_width_ft"] / 2.0,
        layout,
        dimensions,
    )
    free_throw_radius = int(round(6.0 * layout["scale"]))
    cv2.circle(
        panel,
        free_throw_center,
        free_throw_radius,
        COURT_LINE_COLOR,
        2,
        cv2.LINE_AA,
    )
    basket_x = dimensions["basket_center_from_baseline_ft"]
    basket_y = dimensions["court_width_ft"] / 2.0
    basket_center = court_to_pixel(
        basket_x, basket_y, layout, dimensions
    )
    cv2.circle(
        panel,
        basket_center,
        max(3, int(round(0.75 * layout["scale"]))),
        COURT_LINE_COLOR,
        2,
        cv2.LINE_AA,
    )
    backboard_first = court_to_pixel(
        4.0, basket_y - 3.0, layout, dimensions
    )
    backboard_second = court_to_pixel(
        4.0, basket_y + 3.0, layout, dimensions
    )
    cv2.line(
        panel,
        backboard_first,
        backboard_second,
        COURT_LINE_COLOR,
        3,
        cv2.LINE_AA,
    )

    for point_group in clipped_arc_points(
        basket_x,
        basket_y,
        dimensions["three_point_radius_ft"],
        layout,
        dimensions,
        0.0,
        dimensions["half_court_length_ft"],
    ):
        cv2.polylines(
            panel,
            [np.asarray(point_group, dtype=np.int32)],
            False,
            COURT_LINE_COLOR,
            2,
            cv2.LINE_AA,
        )

    for point_group in clipped_arc_points(
        dimensions["half_court_length_ft"],
        basket_y,
        6.0,
        layout,
        dimensions,
        0.0,
        dimensions["half_court_length_ft"],
    ):
        cv2.polylines(
            panel,
            [np.asarray(point_group, dtype=np.int32)],
            False,
            COURT_LINE_COLOR,
            2,
            cv2.LINE_AA,
        )

    draw_text(
        panel,
        "x=42 MIDCOURT",
        (layout["left"] + 8, layout["top"] + 18),
        color=COURT_LABEL_COLOR,
        scale=0.38,
    )
    draw_text(
        panel,
        "x=0 BASELINE",
        (layout["right"] - 92, layout["top"] + 18),
        color=COURT_LABEL_COLOR,
        scale=0.38,
    )
    draw_text(
        panel,
        "FAR SIDELINE (y=0)",
        (layout["left"], layout["top"] - 9),
        color=COURT_LABEL_COLOR,
        scale=0.38,
    )
    draw_text(
        panel,
        "NEAR SIDELINE (y=50)",
        (layout["left"], layout["bottom"] + 19),
        color=COURT_LABEL_COLOR,
        scale=0.38,
    )


def blended_trail_color(color, progress):
    return tuple(
        int(round(
            COURT_FILL_COLOR[index]
            + (color[index] - COURT_FILL_COLOR[index]) * progress
        ))
        for index in range(3)
    )


def draw_court_trail(panel, points, color, layout, dimensions):
    if len(points) < 2:
        return

    point_list = list(points)

    for index, (first, second) in enumerate(
        zip(point_list, point_list[1:]), 1
    ):
        progress = index / max(1, len(point_list) - 1)
        cv2.line(
            panel,
            court_to_pixel(first[0], first[1], layout, dimensions),
            court_to_pixel(second[0], second[1], layout, dimensions),
            blended_trail_color(color, 0.25 + 0.75 * progress),
            max(1, int(round(1 + 3 * progress))),
            cv2.LINE_AA,
        )


def draw_legend(panel, colors, team_by_player, footer_top):
    player_ids = sorted(colors, key=player_sort_key)
    column_width = panel.shape[1] // 2

    for index, player_id in enumerate(player_ids):
        column = 0 if index < 5 else 1
        row = index if index < 5 else index - 5
        x = 22 + column * column_width
        y = footer_top + 24 + row * 17
        color = colors[player_id]
        cv2.circle(panel, (x, y - 4), 6, color, -1, cv2.LINE_AA)
        cv2.circle(panel, (x, y - 4), 7, (0, 0, 0), 1, cv2.LINE_AA)
        draw_text(
            panel,
            f"{short_player_label(player_id)} = {player_id}",
            (x + 12, y),
            scale=0.38,
        )


def draw_top_down_panel(
    panel_width,
    panel_height,
    frame_index,
    fps,
    rows,
    colors,
    team_by_player,
    trails,
    dimensions,
):
    panel = np.full(
        (panel_height, panel_width, 3),
        BACKGROUND_COLOR,
        dtype=np.uint8,
    )
    layout = court_layout(panel_width, panel_height, dimensions)
    draw_court_model(panel, layout, dimensions)
    team_counts = Counter(row["reconciled_team"] for row in rows)
    player_count = len(rows)
    refined_count = sum(
        row["trajectory_refinement_applied"] for row in rows
    )
    status_color = (
        GOOD_COLOR if player_count == EXPECTED_PLAYER_COUNT else WARNING_COLOR
    )
    draw_text(
        panel,
        "TOP-DOWN RIGHT HALF COURT",
        (20, 29),
        scale=0.66,
        thickness=2,
    )
    draw_text(
        panel,
        f"Frame {frame_index} | {frame_index / fps:.2f}s",
        (20, 54),
        scale=0.50,
    )
    draw_text(
        panel,
        (
            f"Players {player_count}/10 | "
            f"W {team_counts.get('white', 0)}/5 | "
            f"D {team_counts.get('dark', 0)}/5 | "
            f"refined {refined_count}"
        ),
        (20, 76),
        color=status_color,
        scale=0.50,
        thickness=2,
    )

    for player_id, points in trails.items():
        draw_court_trail(
            panel,
            points,
            colors[player_id],
            layout,
            dimensions,
        )

    for row in rows:
        player_id = row["player_id"]
        color = colors[player_id]
        point = court_to_pixel(
            row["court_x_ft"],
            row["court_y_ft"],
            layout,
            dimensions,
        )

        if row["trajectory_refinement_applied"]:
            raw_point = court_to_pixel(
                row["raw_court_x_ft"],
                row["raw_court_y_ft"],
                layout,
                dimensions,
            )
            cv2.line(
                panel,
                raw_point,
                point,
                RAW_GHOST_COLOR,
                2,
                cv2.LINE_AA,
            )
            cv2.circle(
                panel,
                raw_point,
                7,
                RAW_GHOST_COLOR,
                2,
                cv2.LINE_AA,
            )

        cv2.circle(panel, point, 11, (0, 0, 0), -1, cv2.LINE_AA)
        cv2.circle(panel, point, 8, color, -1, cv2.LINE_AA)

        if row["trajectory_refinement_applied"]:
            cv2.circle(
                panel, point, 13, REFINED_COLOR, 2, cv2.LINE_AA
            )

        if not row["court_position_in_half_court"]:
            cv2.circle(
                panel, point, 14, OUTSIDE_COLOR, 3, cv2.LINE_AA
            )

        label = short_player_label(player_id)

        if row["trajectory_refinement_applied"]:
            label += "*"
        text_size = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1
        )[0]
        draw_text(
            panel,
            label,
            (point[0] - text_size[0] // 2, point[1] - 14),
            color=(0, 0, 0),
            scale=0.42,
            thickness=2,
        )

    draw_legend(panel, colors, team_by_player, layout["footer_top"])
    return panel


def build_sample_indices(frame_count, sample_count):
    return sorted(
        {
            int(round(index * (frame_count - 1) / (sample_count - 1)))
            for index in range(sample_count)
        }
    )


def build_checkpoint_indices(
    frame_count,
    sample_count,
    maximum_event_checkpoints,
    coordinate_analysis,
):
    indices = set(build_sample_indices(frame_count, sample_count))
    selected_event_frames = []

    def add_spaced_events(frame_indices, limit):
        if limit <= 0:
            return

        added = 0

        for frame_index in frame_indices:
            if frame_index in indices:
                continue

            if any(
                abs(frame_index - selected) <= 3
                for selected in selected_event_frames
            ):
                continue

            selected_event_frames.append(frame_index)
            added += 1

            if added >= limit:
                break

    refinement = coordinate_analysis["trajectory_refinement"]
    correction_frames = [
        record["frame_index"]
        for record in refinement["corrected_rows"]
    ]
    outside_frames = [
        record["frame_index"]
        for record in sorted(
            coordinate_analysis["outside_rows"],
            key=lambda record: (
                -record["outside_distance_ft"],
                record["frame_index"],
            ),
        )
    ]
    jump_frames = [
        candidate["to_frame"]
        for candidate in coordinate_analysis["jump_candidates"]
    ]

    if correction_frames:
        correction_limit = min(
            len(correction_frames),
            (maximum_event_checkpoints + 1) // 2,
        )
        remaining_limit = maximum_event_checkpoints - correction_limit
        outside_limit = min(
            len(outside_frames), (remaining_limit + 1) // 2
        )
        jump_limit = remaining_limit - outside_limit
        add_spaced_events(correction_frames, correction_limit)
        add_spaced_events(outside_frames, outside_limit)
        add_spaced_events(jump_frames, jump_limit)
    else:
        outside_limit = min(
            len(outside_frames),
            (maximum_event_checkpoints + 1) // 2,
        )
        jump_limit = maximum_event_checkpoints - outside_limit
        add_spaced_events(outside_frames, outside_limit)
        add_spaced_events(jump_frames, jump_limit)

    if len(selected_event_frames) < maximum_event_checkpoints:
        remaining_limit = (
            maximum_event_checkpoints - len(selected_event_frames)
        )
        add_spaced_events(
            correction_frames + outside_frames + jump_frames,
            remaining_limit,
        )

    indices.update(selected_event_frames)
    return sorted(indices)


def compose_review_frame(
    source_frame,
    frame_index,
    metadata,
    rows,
    colors,
    team_by_player,
    trails,
    dimensions,
    source_width,
    court_panel_width,
    review_height,
):
    annotated = draw_source_annotations(
        source_frame,
        frame_index,
        metadata["fps"],
        rows,
        colors,
    )
    source_height = int(
        round(metadata["height"] * source_width / metadata["width"])
    )

    if source_height % 2:
        source_height += 1

    if source_height > review_height:
        source_height = review_height
        source_width = int(
            round(metadata["width"] * review_height / metadata["height"])
        )

        if source_width % 2:
            source_width += 1

    resized_source = cv2.resize(
        annotated,
        (source_width, source_height),
        interpolation=cv2.INTER_AREA,
    )
    top_down = draw_top_down_panel(
        court_panel_width,
        review_height,
        frame_index,
        metadata["fps"],
        rows,
        colors,
        team_by_player,
        trails,
        dimensions,
    )
    composite = np.full(
        (review_height, source_width + court_panel_width, 3),
        BACKGROUND_COLOR,
        dtype=np.uint8,
    )
    source_y = (review_height - source_height) // 2
    composite[
        source_y : source_y + source_height,
        0:source_width,
    ] = resized_source
    composite[:, source_width:] = top_down
    cv2.line(
        composite,
        (source_width, 0),
        (source_width, review_height - 1),
        (90, 90, 90),
        2,
    )
    return composite


def calculate_source_display_size(metadata, source_width, review_height):
    source_height = int(
        round(metadata["height"] * source_width / metadata["width"])
    )

    if source_height > review_height:
        source_height = review_height
        source_width = int(
            round(metadata["width"] * review_height / metadata["height"])
        )

    if source_width % 2:
        source_width += 1

    if source_height % 2:
        source_height += 1

    return source_width, source_height


def render_review(
    capture,
    metadata,
    rows_by_frame,
    team_by_player,
    dimensions,
    output_path,
    checkpoints_dir,
    checkpoint_indices,
    source_width,
    court_panel_width,
    review_height,
    trail_length,
):
    colors = build_identity_colors(team_by_player)
    trails = defaultdict(lambda: deque(maxlen=max(1, trail_length)))
    last_seen_frame = {}
    source_width, _ = calculate_source_display_size(
        metadata, source_width, review_height
    )
    output_width = source_width + court_panel_width
    output_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    for stale_checkpoint in checkpoints_dir.glob(
        "frame_*_player_coordinates.jpg"
    ):
        stale_checkpoint.unlink()

    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        metadata["fps"],
        (output_width, review_height),
    )

    if not writer.isOpened():
        raise RuntimeError(f"Could not create review video: {output_path}")

    checkpoint_set = set(checkpoint_indices)
    checkpoint_paths = []
    processed_frames = 0

    try:
        for frame_index in range(metadata["frame_count"]):
            success, source_frame = capture.read()

            if not success:
                break

            rows = rows_by_frame.get(frame_index, [])

            if trail_length > 0:
                for row in rows:
                    player_id = row["player_id"]
                    previous_frame = last_seen_frame.get(player_id)

                    if (
                        previous_frame is not None
                        and frame_index - previous_frame > 1
                    ):
                        trails[player_id].clear()

                    trails[player_id].append(
                        (row["court_x_ft"], row["court_y_ft"])
                    )
                    last_seen_frame[player_id] = frame_index

            composite = compose_review_frame(
                source_frame,
                frame_index,
                metadata,
                rows,
                colors,
                team_by_player,
                trails,
                dimensions,
                source_width,
                court_panel_width,
                review_height,
            )
            writer.write(composite)
            processed_frames += 1

            if frame_index in checkpoint_set:
                checkpoint_path = (
                    checkpoints_dir
                    / f"frame_{frame_index:06d}_player_coordinates.jpg"
                )

                if not cv2.imwrite(str(checkpoint_path), composite):
                    raise RuntimeError(
                        f"Could not write checkpoint: {checkpoint_path}"
                    )

                checkpoint_paths.append(checkpoint_path)

            if processed_frames % 100 == 0:
                print(
                    f"  Rendered {processed_frames}/"
                    f"{metadata['frame_count']} frames"
                )
    finally:
        capture.release()
        writer.release()

    if processed_frames != metadata["frame_count"]:
        raise RuntimeError(
            "Decoded frame count does not match video metadata: "
            f"{processed_frames} != {metadata['frame_count']}"
        )

    return {
        "processed_frame_count": processed_frames,
        "output_width": output_width,
        "output_height": review_height,
        "output_fps": metadata["fps"],
        "output_size_bytes": output_path.stat().st_size,
        "checkpoint_count": len(checkpoint_paths),
        "checkpoint_paths": [str(path) for path in checkpoint_paths],
    }


def write_json_atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(path.name + ".tmp")

    try:
        with temporary_path.open("w", encoding="utf-8") as output_file:
            json.dump(payload, output_file, indent=2)
            output_file.write("\n")

        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def build_report(
    args,
    calibration,
    metadata,
    row_count,
    team_by_player,
    team_counts,
    coordinate_analysis,
    checkpoint_indices,
    render_metadata,
    refinement_report_verified,
):
    court_model = calibration["court_model"]
    return {
        "status": "pending_player_coordinate_visual_review",
        "source_video": str(args.video),
        "source_coordinates": str(args.coordinates),
        "source_coordinate_report": str(args.coordinate_report),
        "source_refinement_report": (
            None
            if args.refinement_report is None
            else str(args.refinement_report)
        ),
        "source_calibration": str(args.calibration),
        "review_video": None if args.report_only else str(args.output),
        "coordinate_system": {
            "units": "feet",
            "scope": court_model.get("coordinate_scope"),
            "convention": court_model.get("coordinate_convention"),
            "display_orientation": (
                "right baseline on the right; midcourt on the left; "
                "far sideline at the top; near sideline at the bottom"
            ),
        },
        "settings": {
            "expected_player_count": EXPECTED_PLAYER_COUNT,
            "expected_team_counts": EXPECTED_TEAM_COUNTS,
            "review_height": args.review_height,
            "source_width": args.source_width,
            "court_panel_width": args.court_panel_width,
            "trail_length": args.trail_length,
            "jump_speed_threshold_ft_sec": (
                args.jump_speed_threshold_ft_sec
            ),
            "sample_count": args.sample_count,
            "maximum_event_checkpoints": (
                args.maximum_event_checkpoints
            ),
        },
        "validation": {
            "coordinate_row_count": row_count,
            "video_metadata": metadata,
            "identity_count": len(team_by_player),
            "identities": sorted(team_by_player, key=player_sort_key),
            "identity_counts_by_team": team_counts,
            "coordinate_report_contract_verified": True,
            "video_calibration_contract_verified": True,
            "refined_coordinate_audit_verified": True,
            "refinement_report_contract_verified": (
                refinement_report_verified
            ),
        },
        "coordinate_analysis": coordinate_analysis,
        "checkpoint_indices": checkpoint_indices,
        "render": {
            "rendered": not args.report_only,
            "metadata": render_metadata,
        },
        "visual_review_guidance": [
            (
                "Confirm each colored source-video identity matches the "
                "same labeled top-down marker."
            ),
            (
                "Confirm player trails are locally continuous and do not "
                "teleport across the court."
            ),
            (
                "On corrected observations, compare each gray raw ghost "
                "and connector with the white-ringed refined marker."
            ),
            (
                "Inspect orange player-count warnings as missing "
                "detections rather than newly unresolved identities."
            ),
            (
                "Inspect red-ringed markers as preserved physical "
                "out-of-bounds positions; coordinates are not clipped."
            ),
            (
                "Use jump candidates as review prompts, not automatic "
                "failures; bounding-box foot points can jitter."
            ),
        ],
    }


def print_summary(
    row_count,
    team_by_player,
    team_counts,
    coordinate_analysis,
    output_path,
    report_path,
    render_metadata,
    report_only,
):
    print("\nPlayer court-coordinate visualization complete.")
    print(f"Validated coordinate rows: {row_count}")
    print(
        f"Validated player identities: {len(team_by_player)} "
        f"({team_counts})"
    )
    print(
        "Frame player-count distribution: "
        f"{coordinate_analysis['frame_player_count_distribution']}"
    )
    print(
        "Outside-court rows preserved: "
        f"{coordinate_analysis['outside_row_count']}"
    )
    print(
        "Motion jump review candidates: "
        f"{coordinate_analysis['jump_candidate_count']} "
        f"above {coordinate_analysis['jump_speed_threshold_ft_sec']:.1f} "
        "ft/s"
    )
    refinement = coordinate_analysis["trajectory_refinement"]

    if refinement["present"]:
        print(
            "Trajectory-refined observations: "
            f"{refinement['corrected_row_count']} "
            f"({refinement['corrected_by_method']})"
        )

    if report_only:
        print("Video rendering skipped because --report-only was supplied.")
    else:
        print(
            f"Rendered synchronized frames: "
            f"{render_metadata['processed_frame_count']}"
        )
        print(
            f"Checkpoint frames saved: "
            f"{render_metadata['checkpoint_count']}"
        )
        print(f"Review video saved to: {output_path}")

    print(f"Review report saved to: {report_path}")
    print("Status: pending complete visual review.")


def main():
    args = parse_args()

    if cv2 is None:
        raise ModuleNotFoundError(
            "OpenCV is required to validate the source video and render "
            "the player-coordinate review."
        )

    calibration = load_json(args.calibration, "Calibration JSON")
    coordinate_report = load_json(
        args.coordinate_report, "Coordinate report"
    )
    refinement_report = None

    if args.refinement_report is not None:
        refinement_report = load_json(
            args.refinement_report, "Trajectory-refinement report"
        )

    (
        rows_by_frame,
        rows_by_player,
        team_by_player,
        row_count,
    ) = load_coordinate_rows(args.coordinates)
    team_counts = validate_coordinate_contract(
        rows_by_frame,
        team_by_player,
        row_count,
        coordinate_report,
    )
    capture, metadata = open_video(args.video)

    try:
        validate_video_and_calibration(
            metadata,
            calibration,
            coordinate_report,
            rows_by_frame,
        )
        _, dimensions = load_court_model(calibration)
        validate_coordinate_bounds_flags(rows_by_frame, dimensions)
        validate_refined_coordinate_audit(rows_by_frame, dimensions)
        coordinate_analysis = analyze_coordinates(
            rows_by_frame,
            rows_by_player,
            metadata["frame_count"],
            metadata["fps"],
            args.jump_speed_threshold_ft_sec,
            dimensions,
        )
        recommended_checkpoint_frames = []

        if refinement_report is not None:
            recommended_checkpoint_frames = (
                validate_refinement_report_contract(
                    refinement_report,
                    row_count,
                    metadata["frame_count"],
                    coordinate_analysis,
                )
            )

        checkpoint_indices = build_checkpoint_indices(
            metadata["frame_count"],
            args.sample_count,
            args.maximum_event_checkpoints,
            coordinate_analysis,
        )
        checkpoint_indices = sorted(
            set(checkpoint_indices).union(
                recommended_checkpoint_frames
            )
        )
        render_metadata = None

        if args.report_only:
            capture.release()
        else:
            print("Rendering synchronized player court coordinates...")
            render_metadata = render_review(
                capture,
                metadata,
                rows_by_frame,
                team_by_player,
                dimensions,
                args.output,
                args.checkpoints_dir,
                checkpoint_indices,
                args.source_width,
                args.court_panel_width,
                args.review_height,
                args.trail_length,
            )
    except Exception:
        capture.release()
        raise

    report = build_report(
        args,
        calibration,
        metadata,
        row_count,
        team_by_player,
        team_counts,
        coordinate_analysis,
        checkpoint_indices,
        render_metadata,
        refinement_report is not None,
    )
    write_json_atomic(args.report, report)
    print_summary(
        row_count,
        team_by_player,
        team_counts,
        coordinate_analysis,
        args.output,
        args.report,
        render_metadata,
        args.report_only,
    )


if __name__ == "__main__":
    main()
