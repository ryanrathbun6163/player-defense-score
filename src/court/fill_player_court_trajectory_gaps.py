import argparse
import csv
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_COORDINATES_PATH = Path(
    "data/outputs/court/"
    "possession_001_player_court_coordinates_refined.csv"
)
DEFAULT_REFINEMENT_REPORT_PATH = Path(
    "data/outputs/court/"
    "possession_001_player_court_trajectory_refinement.json"
)
DEFAULT_OUTPUT_PATH = Path(
    "data/outputs/court/"
    "possession_001_player_court_coordinates_gap_filled.csv"
)
DEFAULT_AUDIT_PATH = Path(
    "data/outputs/court/"
    "possession_001_player_court_trajectory_gap_interpolation_audit.csv"
)
DEFAULT_REPORT_PATH = Path(
    "data/outputs/court/"
    "possession_001_player_court_trajectory_gap_interpolation.json"
)

EXPECTED_REFINEMENT_STATUS = (
    "refined_player_court_trajectories_pending_visual_review"
)
OUTPUT_STATUS = (
    "interpolated_internal_player_coordinate_gaps_pending_visual_review"
)
EXPECTED_PLAYER_COUNT = 10
EXPECTED_TEAM_COUNTS = {"white": 5, "dark": 5}

GAP_FIELDS = [
    "source_observation_available",
    "trajectory_observation_kind",
    "trajectory_gap_fill_applied",
    "trajectory_gap_fill_method",
    "trajectory_gap_fill_reason",
    "trajectory_gap_anchor_frames",
    "trajectory_gap_size_observations",
    "trajectory_gap_endpoint_speed_ft_sec",
]

AUDIT_FIELDS = [
    "player_id",
    "reconciled_team",
    "frame_index",
    "timestamp_sec",
    "court_x_ft",
    "court_y_ft",
    "court_position_in_half_court",
    "after_frame",
    "before_frame",
    "interpolation_fraction",
    "gap_size_observations",
    "endpoint_speed_ft_sec",
    "camera_raw_transform_valid",
    "camera_raw_transform_accepted",
    "source_observation_available",
    "trajectory_observation_kind",
    "trajectory_gap_fill_method",
    "trajectory_gap_fill_reason",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Linearly interpolate conservative bracketed internal gaps "
            "in refined player court-coordinate trajectories."
        )
    )
    parser.add_argument(
        "--coordinates",
        type=Path,
        default=DEFAULT_COORDINATES_PATH,
        help="Refined player court-coordinate CSV.",
    )
    parser.add_argument(
        "--refinement-report",
        type=Path,
        default=DEFAULT_REFINEMENT_REPORT_PATH,
        help="Trajectory-refinement validation report.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Gap-interpolated player court-coordinate CSV.",
    )
    parser.add_argument(
        "--audit",
        type=Path,
        default=DEFAULT_AUDIT_PATH,
        help="Row-level gap-interpolation audit CSV.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Gap-interpolation validation report.",
    )
    parser.add_argument(
        "--maximum-gap-observations",
        type=int,
        default=10,
        help="Maximum number of missing observations filled in one gap.",
    )
    parser.add_argument(
        "--maximum-endpoint-speed-ft-sec",
        type=float,
        default=45.0,
        help=(
            "Maximum motion speed allowed between interpolation anchors."
        ),
    )
    parser.add_argument(
        "--half-court-length-ft",
        type=float,
        default=42.0,
        help="Calibrated half-court length used for boundary validation.",
    )
    parser.add_argument(
        "--court-width-ft",
        type=float,
        default=50.0,
        help="Calibrated court width used for boundary validation.",
    )
    args = parser.parse_args()

    if args.maximum_gap_observations < 1:
        parser.error("--maximum-gap-observations must be positive")

    if args.maximum_endpoint_speed_ft_sec <= 0:
        parser.error("--maximum-endpoint-speed-ft-sec must be positive")

    if args.half_court_length_ft <= 0 or args.court_width_ft <= 0:
        parser.error("Court dimensions must be positive")

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


def bool_text(value):
    return "true" if value else "false"


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


def position_inside_half_court(x, y, half_length, court_width):
    return 0.0 <= x <= half_length and 0.0 <= y <= court_width


def load_coordinate_rows(path):
    if not path.exists():
        raise FileNotFoundError(f"Refined coordinate CSV not found: {path}")

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
    rows = []
    rows_by_player = defaultdict(list)
    rows_by_frame = defaultdict(list)

    with path.open("r", newline="", encoding="utf-8-sig") as input_file:
        reader = csv.DictReader(input_file)
        fieldnames = list(reader.fieldnames or [])
        missing_fields = sorted(required_fields - set(fieldnames))

        if missing_fields:
            raise ValueError(
                "Refined coordinate CSV is missing required fields: "
                f"{missing_fields}"
            )

        conflicting_fields = sorted(
            set(fieldnames).intersection(GAP_FIELDS)
        )

        if conflicting_fields:
            raise ValueError(
                "Input coordinates already contain gap-fill fields: "
                f"{conflicting_fields}"
            )

        for row_number, raw_row in enumerate(reader, 2):
            player_id = raw_row["player_id"].strip()
            team = raw_row["reconciled_team"].strip()
            record = {
                "input_index": len(rows),
                "row_number": row_number,
                "raw": dict(raw_row),
                "frame_index": parse_int(
                    raw_row["frame_index"], "frame_index", row_number
                ),
                "timestamp_sec": parse_float(
                    raw_row["timestamp_sec"],
                    "timestamp_sec",
                    row_number,
                ),
                "track_id": parse_int(
                    raw_row["track_id"], "track_id", row_number
                ),
                "confidence": parse_float(
                    raw_row["confidence"], "confidence", row_number
                ),
                "player_id": player_id,
                "reconciled_team": team,
                "court_x_ft": parse_float(
                    raw_row["court_x_ft"], "court_x_ft", row_number
                ),
                "court_y_ft": parse_float(
                    raw_row["court_y_ft"], "court_y_ft", row_number
                ),
                "inside": parse_bool(
                    raw_row["court_position_in_half_court"],
                    "court_position_in_half_court",
                    row_number,
                ),
                "camera_raw_transform_valid": parse_bool(
                    raw_row["camera_raw_transform_valid"],
                    "camera_raw_transform_valid",
                    row_number,
                ),
                "camera_raw_transform_accepted": parse_bool(
                    raw_row["camera_raw_transform_accepted"],
                    "camera_raw_transform_accepted",
                    row_number,
                ),
                "refinement_applied": parse_bool(
                    raw_row["trajectory_refinement_applied"],
                    "trajectory_refinement_applied",
                    row_number,
                ),
            }

            if record["frame_index"] < 0:
                raise ValueError(
                    f"Negative frame index at CSV row {row_number}"
                )

            if not player_id:
                raise ValueError(f"Blank player_id at CSV row {row_number}")

            if team not in EXPECTED_TEAM_COUNTS:
                raise ValueError(
                    f"Unexpected team at CSV row {row_number}: {team!r}"
                )

            if raw_row["identity_status"].strip() != "active":
                raise ValueError(
                    f"Non-active identity at CSV row {row_number}"
                )

            rows.append(record)
            rows_by_player[player_id].append(record)
            rows_by_frame[record["frame_index"]].append(record)

    if not rows:
        raise ValueError(f"No coordinate rows found in {path}")

    for player_rows in rows_by_player.values():
        player_rows.sort(key=lambda row: row["frame_index"])

        for first, second in zip(player_rows, player_rows[1:]):
            if second["frame_index"] <= first["frame_index"]:
                raise ValueError(
                    "Player observations are not strictly increasing: "
                    f"{first['player_id']} frame {first['frame_index']} "
                    f"to {second['frame_index']}"
                )

    for frame_index, frame_rows in rows_by_frame.items():
        player_ids = [row["player_id"] for row in frame_rows]

        if len(player_ids) != len(set(player_ids)):
            raise ValueError(
                f"Duplicate player rows in frame {frame_index}: "
                f"{player_ids}"
            )

        if len(frame_rows) > EXPECTED_PLAYER_COUNT:
            raise ValueError(
                f"Frame {frame_index} contains more than ten players"
            )

        frame_flags = {
            (
                row["camera_raw_transform_valid"],
                row["camera_raw_transform_accepted"],
            )
            for row in frame_rows
        }

        if len(frame_flags) != 1:
            raise ValueError(
                "Camera transform flags disagree within frame "
                f"{frame_index}: {sorted(frame_flags)}"
            )

    return (
        rows,
        dict(rows_by_player),
        dict(rows_by_frame),
        fieldnames,
    )


def validate_identity_and_boundary_contract(
    rows,
    rows_by_player,
    half_length,
    court_width,
):
    if len(rows_by_player) != EXPECTED_PLAYER_COUNT:
        raise ValueError(
            f"Expected ten players, found {len(rows_by_player)}"
        )

    team_by_player = {}

    for player_id, player_rows in rows_by_player.items():
        teams = {row["reconciled_team"] for row in player_rows}

        if len(teams) != 1:
            raise ValueError(
                f"Player {player_id} has inconsistent teams: {teams}"
            )

        team_by_player[player_id] = next(iter(teams))

    team_counts = Counter(team_by_player.values())

    if dict(team_counts) != EXPECTED_TEAM_COUNTS:
        raise ValueError(
            "Expected five white and five dark players, found "
            f"{dict(team_counts)}"
        )

    mismatches = []

    for row in rows:
        expected_inside = position_inside_half_court(
            row["court_x_ft"],
            row["court_y_ft"],
            half_length,
            court_width,
        )

        if expected_inside != row["inside"]:
            mismatches.append((row["frame_index"], row["player_id"]))

    if mismatches:
        raise ValueError(
            "Refined boundary flags disagree with coordinates: "
            f"{mismatches[:20]}"
        )

    return team_by_player, dict(sorted(team_counts.items()))


def validate_refinement_report_contract(
    refinement_report,
    rows,
    rows_by_player,
    rows_by_frame,
):
    if refinement_report.get("status") != EXPECTED_REFINEMENT_STATUS:
        raise ValueError(
            "Unexpected trajectory-refinement report status: "
            f"{refinement_report.get('status')!r}"
        )

    validation = refinement_report.get("validation", {})
    trusted = refinement_report.get("trusted_path_audit", {})
    boundary = refinement_report.get("boundary_audit", {})
    missing = refinement_report.get("missing_observation_audit", {})
    settings = refinement_report.get("settings", {})

    if int(validation.get("row_count", -1)) != len(rows):
        raise ValueError(
            "Trajectory-refinement report row count does not match CSV"
        )

    if int(validation.get("identity_count", -1)) != len(rows_by_player):
        raise ValueError(
            "Trajectory-refinement identity count does not match CSV"
        )

    frame_count = int(validation.get("frame_count", -1))
    fps = float(validation.get("fps", -1.0))

    if frame_count <= 0 or fps <= 0:
        raise ValueError(
            "Trajectory-refinement report has invalid video metadata"
        )

    if rows_by_frame and max(rows_by_frame) >= frame_count:
        raise ValueError("Coordinate rows exceed the reported frame count")

    corrected_count = sum(row["refinement_applied"] for row in rows)

    if int(trusted.get("corrected_observation_count", -1)) != int(
        corrected_count
    ):
        raise ValueError(
            "Trajectory-refinement corrected count does not match CSV"
        )

    outside_count = sum(not row["inside"] for row in rows)

    if int(boundary.get("refined_outside_observation_count", -1)) != int(
        outside_count
    ):
        raise ValueError(
            "Trajectory-refinement outside count does not match CSV"
        )

    total_missing = frame_count * len(rows_by_player) - len(rows)

    if int(missing.get("total_missing_observation_count", -1)) != int(
        total_missing
    ):
        raise ValueError(
            "Trajectory-refinement missing count does not match CSV"
        )

    reviewed_speed = float(settings.get("maximum_speed_ft_sec", -1.0))

    if reviewed_speed <= 0:
        raise ValueError(
            "Trajectory-refinement report has no valid speed threshold"
        )

    return fps, frame_count, reviewed_speed


def transition_metrics(first, second, fps):
    frame_gap = second["frame_index"] - first["frame_index"]

    if frame_gap <= 0:
        raise ValueError("Transition frame gap must be positive")

    distance = math.hypot(
        second["court_x_ft"] - first["court_x_ft"],
        second["court_y_ft"] - first["court_y_ft"],
    )
    speed = distance * fps / frame_gap
    return speed, distance, frame_gap


def interpolated_position(first, second, frame_index):
    frame_span = second["frame_index"] - first["frame_index"]
    fraction = (frame_index - first["frame_index"]) / frame_span
    court_x = first["court_x_ft"] + fraction * (
        second["court_x_ft"] - first["court_x_ft"]
    )
    court_y = first["court_y_ft"] + fraction * (
        second["court_y_ft"] - first["court_y_ft"]
    )
    return court_x, court_y, fraction


def analyze_internal_gaps(
    rows_by_player,
    fps,
    maximum_gap_observations,
    maximum_speed,
    half_length,
    court_width,
):
    gaps = []

    for player_id in sorted(rows_by_player, key=player_sort_key):
        player_rows = rows_by_player[player_id]

        for first, second in zip(player_rows, player_rows[1:]):
            missing_count = (
                second["frame_index"] - first["frame_index"] - 1
            )

            if missing_count <= 0:
                continue

            speed, distance, _ = transition_metrics(first, second, fps)
            boundary_state_stable = first["inside"] == second["inside"]
            interpolated_boundary_stable = boundary_state_stable

            if boundary_state_stable:
                for frame_index in range(
                    first["frame_index"] + 1,
                    second["frame_index"],
                ):
                    court_x, court_y, _ = interpolated_position(
                        first, second, frame_index
                    )
                    inside = position_inside_half_court(
                        court_x,
                        court_y,
                        half_length,
                        court_width,
                    )

                    if inside != first["inside"]:
                        interpolated_boundary_stable = False
                        break

            if missing_count > maximum_gap_observations:
                decision = "rejected_gap_too_long"
                fill = False
            elif speed > maximum_speed:
                decision = "rejected_endpoint_speed"
                fill = False
            elif not boundary_state_stable:
                decision = "rejected_boundary_state_transition"
                fill = False
            elif not interpolated_boundary_stable:
                decision = "rejected_interpolated_boundary_change"
                fill = False
            else:
                decision = "accepted_bracketed_internal_gap"
                fill = True

            gaps.append(
                {
                    "player_id": player_id,
                    "reconciled_team": first["reconciled_team"],
                    "after_frame": first["frame_index"],
                    "before_frame": second["frame_index"],
                    "missing_observation_count": missing_count,
                    "endpoint_distance_ft": distance,
                    "endpoint_speed_ft_sec": speed,
                    "left_inside": first["inside"],
                    "right_inside": second["inside"],
                    "interpolated_boundary_stable": (
                        interpolated_boundary_stable
                    ),
                    "fill": fill,
                    "decision": decision,
                    "first": first,
                    "second": second,
                }
            )

    return gaps


def frame_transform_flags(rows_by_frame):
    flags = {}

    for frame_index, rows in rows_by_frame.items():
        frame_flags = {
            (
                row["camera_raw_transform_valid"],
                row["camera_raw_transform_accepted"],
            )
            for row in rows
        }

        if len(frame_flags) != 1:
            raise ValueError(
                f"Camera flags disagree within frame {frame_index}"
            )

        flags[frame_index] = next(iter(frame_flags))

    return flags


def observed_gap_fields():
    return {
        "source_observation_available": "true",
        "trajectory_observation_kind": "observed",
        "trajectory_gap_fill_applied": "false",
        "trajectory_gap_fill_method": "not_applicable_observed",
        "trajectory_gap_fill_reason": "source_observation_preserved",
        "trajectory_gap_anchor_frames": "",
        "trajectory_gap_size_observations": "0",
        "trajectory_gap_endpoint_speed_ft_sec": "0.000000",
    }


def build_synthetic_row(
    gap,
    frame_index,
    fps,
    original_fields,
    transform_flags,
    half_length,
    court_width,
):
    first = gap["first"]
    second = gap["second"]
    court_x, court_y, fraction = interpolated_position(
        first, second, frame_index
    )
    inside = position_inside_half_court(
        court_x, court_y, half_length, court_width
    )

    if inside != first["inside"] or inside != second["inside"]:
        raise RuntimeError(
            "Synthetic coordinate changed boundary state for "
            f"{gap['player_id']} at frame {frame_index}"
        )

    valid, accepted = transform_flags[frame_index]
    row = {field_name: "" for field_name in original_fields}
    left_raw = first["raw"]
    player_id = gap["player_id"]
    team = gap["reconciled_team"]
    row.update(
        {
            "frame_index": str(frame_index),
            "timestamp_sec": f"{frame_index / fps:.6f}",
            "track_id": "-1",
            "confidence": "0.000000",
            "x1": "-1.000000",
            "y1": "-1.000000",
            "x2": "-1.000000",
            "y2": "-1.000000",
            "floor_x": "-1.000000",
            "floor_y": "-1.000000",
            "team_label": team,
            "segment_id": "-1",
            "baseline_player_id": left_raw.get(
                "baseline_player_id", player_id
            ),
            "player_id": player_id,
            "reconciled_team": team,
            "identity_status": "active",
            "identity_review_reason": "synthetic_gap_interpolation",
            "duplicate_detection_count": "0",
            "source_track_ids": "",
            "source_segment_ids": "",
            "court_x_ft": f"{court_x:.6f}",
            "court_y_ft": f"{court_y:.6f}",
            "court_position_in_half_court": bool_text(inside),
            "camera_raw_transform_valid": bool_text(valid),
            "camera_raw_transform_accepted": bool_text(accepted),
            "raw_court_x_ft": f"{court_x:.6f}",
            "raw_court_y_ft": f"{court_y:.6f}",
            "raw_court_position_in_half_court": bool_text(inside),
            "trajectory_refinement_applied": "false",
            "trajectory_refinement_method": (
                "not_applicable_synthetic_gap_observation"
            ),
            "trajectory_refinement_reason": (
                "no_raw_player_observation"
            ),
            "trajectory_correction_distance_ft": "0.000000",
            "trajectory_anchor_frames": "",
            "trajectory_trusted_path_observation": "false",
            "trajectory_raw_jump_candidate": "false",
            "source_observation_available": "false",
            "trajectory_observation_kind": (
                "interpolated_internal_gap"
            ),
            "trajectory_gap_fill_applied": "true",
            "trajectory_gap_fill_method": "linear_interpolation",
            "trajectory_gap_fill_reason": (
                "bracketed_internal_gap_within_motion_threshold"
            ),
            "trajectory_gap_anchor_frames": (
                f"{first['frame_index']}:{second['frame_index']}"
            ),
            "trajectory_gap_size_observations": str(
                gap["missing_observation_count"]
            ),
            "trajectory_gap_endpoint_speed_ft_sec": (
                f"{gap['endpoint_speed_ft_sec']:.6f}"
            ),
        }
    )
    audit = {
        "player_id": player_id,
        "reconciled_team": team,
        "frame_index": frame_index,
        "timestamp_sec": frame_index / fps,
        "court_x_ft": court_x,
        "court_y_ft": court_y,
        "court_position_in_half_court": inside,
        "after_frame": first["frame_index"],
        "before_frame": second["frame_index"],
        "interpolation_fraction": fraction,
        "gap_size_observations": gap["missing_observation_count"],
        "endpoint_speed_ft_sec": gap["endpoint_speed_ft_sec"],
        "camera_raw_transform_valid": valid,
        "camera_raw_transform_accepted": accepted,
        "source_observation_available": False,
        "trajectory_observation_kind": (
            "interpolated_internal_gap"
        ),
        "trajectory_gap_fill_method": "linear_interpolation",
        "trajectory_gap_fill_reason": (
            "bracketed_internal_gap_within_motion_threshold"
        ),
    }
    return row, audit


def build_output_rows(
    rows,
    gaps,
    rows_by_frame,
    original_fields,
    fps,
    half_length,
    court_width,
):
    output_rows = []
    audit_rows = []
    transform_flags = frame_transform_flags(rows_by_frame)

    for row in rows:
        output_row = dict(row["raw"])
        output_row.update(observed_gap_fields())
        output_rows.append(output_row)

    for gap in gaps:
        if not gap["fill"]:
            continue

        for frame_index in range(
            gap["after_frame"] + 1,
            gap["before_frame"],
        ):
            if frame_index not in transform_flags:
                raise RuntimeError(
                    "Cannot synthesize a player row without frame camera "
                    f"metadata: frame {frame_index}"
                )

            output_row, audit_row = build_synthetic_row(
                gap,
                frame_index,
                fps,
                original_fields,
                transform_flags,
                half_length,
                court_width,
            )
            output_rows.append(output_row)
            audit_rows.append(audit_row)

    output_rows.sort(
        key=lambda row: (
            int(row["frame_index"]),
            player_sort_key(row["player_id"]),
        )
    )
    audit_rows.sort(
        key=lambda row: (
            row["frame_index"],
            player_sort_key(row["player_id"]),
        )
    )
    return output_rows, audit_rows


def typed_output_rows(output_rows, half_length, court_width):
    typed_rows = []
    rows_by_player = defaultdict(list)
    rows_by_frame = defaultdict(list)

    for row_number, raw_row in enumerate(output_rows, 2):
        record = {
            "frame_index": parse_int(
                raw_row["frame_index"], "frame_index", row_number
            ),
            "player_id": raw_row["player_id"],
            "reconciled_team": raw_row["reconciled_team"],
            "court_x_ft": parse_float(
                raw_row["court_x_ft"], "court_x_ft", row_number
            ),
            "court_y_ft": parse_float(
                raw_row["court_y_ft"], "court_y_ft", row_number
            ),
            "inside": parse_bool(
                raw_row["court_position_in_half_court"],
                "court_position_in_half_court",
                row_number,
            ),
            "source_observation_available": parse_bool(
                raw_row["source_observation_available"],
                "source_observation_available",
                row_number,
            ),
            "gap_fill_applied": parse_bool(
                raw_row["trajectory_gap_fill_applied"],
                "trajectory_gap_fill_applied",
                row_number,
            ),
        }
        expected_inside = position_inside_half_court(
            record["court_x_ft"],
            record["court_y_ft"],
            half_length,
            court_width,
        )

        if record["inside"] != expected_inside:
            raise RuntimeError(
                "Output boundary flag disagrees at frame "
                f"{record['frame_index']} for {record['player_id']}"
            )

        if record["source_observation_available"] == record[
            "gap_fill_applied"
        ]:
            raise RuntimeError(
                "Output provenance flags disagree at frame "
                f"{record['frame_index']} for {record['player_id']}"
            )

        typed_rows.append(record)
        rows_by_player[record["player_id"]].append(record)
        rows_by_frame[record["frame_index"]].append(record)

    for player_rows in rows_by_player.values():
        player_rows.sort(key=lambda row: row["frame_index"])

    for frame_index, frame_rows in rows_by_frame.items():
        players = [row["player_id"] for row in frame_rows]

        if len(players) != len(set(players)):
            raise RuntimeError(
                f"Output has duplicate players in frame {frame_index}"
            )

        if len(players) > EXPECTED_PLAYER_COUNT:
            raise RuntimeError(
                f"Output has more than ten players in frame {frame_index}"
            )

    return typed_rows, dict(rows_by_player), dict(rows_by_frame)


def validate_output_provenance(
    input_rows,
    output_rows,
    audit_rows,
    original_fields,
):
    input_by_key = {
        (row["frame_index"], row["player_id"]): row["raw"]
        for row in input_rows
    }
    output_by_key = {
        (int(row["frame_index"]), row["player_id"]): row
        for row in output_rows
    }

    if len(output_by_key) != len(output_rows):
        raise RuntimeError("Output player-frame pairs are not unique")

    for key, input_raw in input_by_key.items():
        output_raw = output_by_key.get(key)

        if output_raw is None:
            raise RuntimeError(
                f"Observed coordinate was removed from output: {key}"
            )

        changed_fields = [
            field_name
            for field_name in original_fields
            if output_raw.get(field_name) != input_raw.get(field_name)
        ]

        if changed_fields:
            raise RuntimeError(
                "Observed coordinate changed during gap interpolation "
                f"at {key}: {changed_fields}"
            )

        if output_raw["source_observation_available"] != "true":
            raise RuntimeError(
                f"Observed coordinate lost provenance at {key}"
            )

    synthetic_rows = [
        row
        for row in output_rows
        if row["source_observation_available"] == "false"
    ]

    if len(synthetic_rows) != len(audit_rows):
        raise RuntimeError(
            "Synthetic output and row-audit counts disagree: "
            f"{len(synthetic_rows)} != {len(audit_rows)}"
        )

    synthetic_keys = {
        (int(row["frame_index"]), row["player_id"])
        for row in synthetic_rows
    }
    audit_keys = {
        (row["frame_index"], row["player_id"])
        for row in audit_rows
    }

    if synthetic_keys != audit_keys:
        raise RuntimeError(
            "Synthetic output coordinates do not match the row audit"
        )

    for row in synthetic_rows:
        key = (int(row["frame_index"]), row["player_id"])
        sentinel_fields = {
            "track_id": -1.0,
            "confidence": 0.0,
            "x1": -1.0,
            "y1": -1.0,
            "x2": -1.0,
            "y2": -1.0,
            "floor_x": -1.0,
            "floor_y": -1.0,
        }

        for field_name, expected in sentinel_fields.items():
            if not math.isclose(
                float(row[field_name]),
                expected,
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                raise RuntimeError(
                    "Synthetic coordinate fabricates detection data at "
                    f"{key}: {field_name}={row[field_name]!r}"
                )

        for field_name in (
            "source_track_ids",
            "source_segment_ids",
        ):
            if field_name in row and row[field_name].strip():
                raise RuntimeError(
                    "Synthetic coordinate fabricates source lineage at "
                    f"{key}: {field_name}={row[field_name]!r}"
                )


def analyze_motion(rows_by_player, fps, threshold):
    candidates = []
    maximum_speed = 0.0
    transition_count = 0

    for player_id in sorted(rows_by_player, key=player_sort_key):
        rows = rows_by_player[player_id]

        for first, second in zip(rows, rows[1:]):
            speed, distance, frame_gap = transition_metrics(
                first, second, fps
            )
            maximum_speed = max(maximum_speed, speed)
            transition_count += 1

            if speed > threshold:
                candidates.append(
                    {
                        "player_id": player_id,
                        "from_frame": first["frame_index"],
                        "to_frame": second["frame_index"],
                        "frame_gap": frame_gap,
                        "distance_ft": round(distance, 4),
                        "speed_ft_sec": round(speed, 4),
                        "touches_outside_coordinate": (
                            not first["inside"] or not second["inside"]
                        ),
                    }
                )

    candidates.sort(
        key=lambda candidate: (
            -candidate["speed_ft_sec"],
            candidate["to_frame"],
            candidate["player_id"],
        )
    )
    return {
        "transition_count": transition_count,
        "candidate_count": len(candidates),
        "maximum_speed_ft_sec": round(maximum_speed, 4),
        "candidates": candidates,
    }


def frame_count_distribution(rows_by_frame, frame_count):
    return dict(
        sorted(
            Counter(
                len(rows_by_frame.get(frame_index, []))
                for frame_index in range(frame_count)
            ).items()
        )
    )


def choose_checkpoint_frames(gaps, limit=16):
    candidates = sorted(
        (gap for gap in gaps if gap["fill"]),
        key=lambda gap: (
            -gap["missing_observation_count"],
            -gap["endpoint_speed_ft_sec"],
            gap["after_frame"],
            player_sort_key(gap["player_id"]),
        ),
    )
    selected = []

    for gap in candidates:
        midpoint = int(
            round((gap["after_frame"] + gap["before_frame"]) / 2)
        )

        if midpoint not in selected:
            selected.append(midpoint)

        if len(selected) >= limit:
            break

    return sorted(selected)


def summarize_gaps(gaps):
    records = []

    for gap in sorted(
        gaps,
        key=lambda item: (
            item["after_frame"],
            player_sort_key(item["player_id"]),
        ),
    ):
        records.append(
            {
                "player_id": gap["player_id"],
                "reconciled_team": gap["reconciled_team"],
                "after_frame": gap["after_frame"],
                "before_frame": gap["before_frame"],
                "missing_observation_count": gap[
                    "missing_observation_count"
                ],
                "endpoint_distance_ft": round(
                    gap["endpoint_distance_ft"], 6
                ),
                "endpoint_speed_ft_sec": round(
                    gap["endpoint_speed_ft_sec"], 6
                ),
                "left_inside": gap["left_inside"],
                "right_inside": gap["right_inside"],
                "interpolated_boundary_stable": gap[
                    "interpolated_boundary_stable"
                ],
                "filled": gap["fill"],
                "decision": gap["decision"],
            }
        )

    return records


def build_report(
    args,
    rows,
    input_rows_by_player,
    input_rows_by_frame,
    output_rows,
    output_rows_by_player,
    output_rows_by_frame,
    audit_rows,
    gaps,
    team_counts,
    fps,
    frame_count,
    input_motion,
    output_motion,
):
    filled_gaps = [gap for gap in gaps if gap["fill"]]
    rejected_gaps = [gap for gap in gaps if not gap["fill"]]
    observed_outside = sum(not row["inside"] for row in rows)
    synthetic_outside = sum(
        not row["inside"]
        for rows in output_rows_by_player.values()
        for row in rows
        if not row["source_observation_available"]
    )
    output_outside = sum(
        not row["inside"]
        for player_rows in output_rows_by_player.values()
        for row in player_rows
    )
    grid_size = frame_count * len(input_rows_by_player)
    leading_missing = sum(
        player_rows[0]["frame_index"]
        for player_rows in input_rows_by_player.values()
    )
    trailing_missing = sum(
        frame_count - 1 - player_rows[-1]["frame_index"]
        for player_rows in input_rows_by_player.values()
    )
    rejected_internal_missing = sum(
        gap["missing_observation_count"] for gap in rejected_gaps
    )
    remaining_missing = grid_size - len(output_rows)
    input_distribution = frame_count_distribution(
        input_rows_by_frame, frame_count
    )
    output_distribution = frame_count_distribution(
        output_rows_by_frame, frame_count
    )
    filled_by_player = Counter(
        row["player_id"] for row in audit_rows
    )
    per_player = {}

    for player_id in sorted(input_rows_by_player, key=player_sort_key):
        input_count = len(input_rows_by_player[player_id])
        output_count = len(output_rows_by_player[player_id])
        per_player[player_id] = {
            "reconciled_team": input_rows_by_player[player_id][0][
                "reconciled_team"
            ],
            "input_observation_count": input_count,
            "interpolated_observation_count": (
                filled_by_player.get(player_id, 0)
            ),
            "output_coordinate_count": output_count,
            "remaining_missing_observation_count": (
                frame_count - output_count
            ),
            "first_observed_frame": input_rows_by_player[player_id][0][
                "frame_index"
            ],
            "last_observed_frame": input_rows_by_player[player_id][-1][
                "frame_index"
            ],
        }

    if remaining_missing != (
        leading_missing + trailing_missing + rejected_internal_missing
    ):
        raise RuntimeError(
            "Remaining missing count does not match the audited policy"
        )

    if output_motion["candidate_count"] != input_motion[
        "candidate_count"
    ]:
        raise RuntimeError(
            "Gap interpolation changed the motion-candidate count"
        )

    non_boundary_candidates = [
        candidate
        for candidate in output_motion["candidates"]
        if not candidate["touches_outside_coordinate"]
    ]

    if non_boundary_candidates:
        raise RuntimeError(
            "Gap interpolation left non-boundary motion candidates: "
            f"{non_boundary_candidates[:20]}"
        )

    return {
        "status": OUTPUT_STATUS,
        "source_coordinates": str(args.coordinates),
        "source_refinement_report": str(args.refinement_report),
        "output_coordinates": str(args.output),
        "output_audit": str(args.audit),
        "settings": {
            "maximum_gap_observations": (
                args.maximum_gap_observations
            ),
            "maximum_endpoint_speed_ft_sec": (
                args.maximum_endpoint_speed_ft_sec
            ),
            "half_court_length_ft": args.half_court_length_ft,
            "court_width_ft": args.court_width_ft,
            "interpolation_method": "linear_interpolation",
            "leading_gap_policy": "preserve_unfilled_no_left_anchor",
            "trailing_gap_policy": "preserve_unfilled_no_right_anchor",
        },
        "validation": {
            "input_observed_row_count": len(rows),
            "output_coordinate_row_count": len(output_rows),
            "interpolated_row_count": len(audit_rows),
            "frame_count": frame_count,
            "fps": fps,
            "identity_count": len(input_rows_by_player),
            "identity_counts_by_team": team_counts,
            "source_refinement_contract_verified": True,
            "all_observed_rows_preserved_exactly": True,
            "no_source_detection_fields_fabricated": True,
            "output_player_frame_pairs_unique": True,
        },
        "coverage_audit": {
            "possible_player_frame_count": grid_size,
            "input_coverage_fraction": round(len(rows) / grid_size, 6),
            "output_coverage_fraction": round(
                len(output_rows) / grid_size, 6
            ),
            "input_frame_player_count_distribution": {
                str(key): value
                for key, value in input_distribution.items()
            },
            "output_frame_player_count_distribution": {
                str(key): value
                for key, value in output_distribution.items()
            },
            "input_frames_with_all_ten_players": (
                input_distribution.get(10, 0)
            ),
            "output_frames_with_all_ten_players": (
                output_distribution.get(10, 0)
            ),
            "remaining_missing_observation_count": remaining_missing,
            "remaining_leading_missing_observation_count": (
                leading_missing
            ),
            "remaining_trailing_missing_observation_count": (
                trailing_missing
            ),
            "remaining_rejected_internal_missing_observation_count": (
                rejected_internal_missing
            ),
        },
        "gap_audit": {
            "detected_internal_gap_count": len(gaps),
            "detected_internal_missing_observation_count": sum(
                gap["missing_observation_count"] for gap in gaps
            ),
            "filled_internal_gap_count": len(filled_gaps),
            "filled_observation_count": len(audit_rows),
            "rejected_internal_gap_count": len(rejected_gaps),
            "maximum_filled_gap_observations": max(
                (
                    gap["missing_observation_count"]
                    for gap in filled_gaps
                ),
                default=0,
            ),
            "maximum_filled_endpoint_speed_ft_sec": round(
                max(
                    (
                        gap["endpoint_speed_ft_sec"]
                        for gap in filled_gaps
                    ),
                    default=0.0,
                ),
                6,
            ),
            "filled_observations_by_player": dict(
                sorted(
                    filled_by_player.items(),
                    key=lambda item: player_sort_key(item[0]),
                )
            ),
            "recommended_checkpoint_frames": (
                choose_checkpoint_frames(gaps)
            ),
            "gaps": summarize_gaps(gaps),
        },
        "motion_audit": {
            "input_refined": input_motion,
            "gap_interpolated": output_motion,
            "candidate_count_preserved": True,
            "remaining_candidates_are_boundary_related": (
                not non_boundary_candidates
            ),
        },
        "boundary_audit": {
            "observed_outside_coordinate_count": observed_outside,
            "interpolated_outside_coordinate_count": synthetic_outside,
            "output_outside_coordinate_count": output_outside,
            "observed_outside_coordinates_preserved_exactly": True,
            "interpolated_boundary_states_stable": all(
                gap["interpolated_boundary_stable"]
                for gap in filled_gaps
            ),
        },
        "per_player": per_player,
        "review_guidance": [
            (
                "Inspect cyan diamond-ringed top-down markers as "
                "interpolated coordinates with no source detection."
            ),
            (
                "Confirm interpolated trails bridge each bracketed gap "
                "without changing identity or motion direction."
            ),
            (
                "Confirm all existing source boxes and observed court "
                "coordinates remain unchanged."
            ),
            (
                "Confirm red rings still identify physical outside-court "
                "coordinates, including interpolated outside positions."
            ),
            (
                "Leading missing observations remain absent because no "
                "left anchor exists; they are not extrapolated."
            ),
        ],
    }


def write_csv_atomic(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")

    try:
        with temporary_path.open(
            "w", newline="", encoding="utf-8"
        ) as output_file:
            writer = csv.DictWriter(
                output_file,
                fieldnames=fieldnames,
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(rows)

        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def write_audit_csv(path, audit_rows):
    rows = []

    for row in audit_rows:
        rows.append(
            {
                "player_id": row["player_id"],
                "reconciled_team": row["reconciled_team"],
                "frame_index": row["frame_index"],
                "timestamp_sec": f"{row['timestamp_sec']:.6f}",
                "court_x_ft": f"{row['court_x_ft']:.6f}",
                "court_y_ft": f"{row['court_y_ft']:.6f}",
                "court_position_in_half_court": bool_text(
                    row["court_position_in_half_court"]
                ),
                "after_frame": row["after_frame"],
                "before_frame": row["before_frame"],
                "interpolation_fraction": (
                    f"{row['interpolation_fraction']:.6f}"
                ),
                "gap_size_observations": row[
                    "gap_size_observations"
                ],
                "endpoint_speed_ft_sec": (
                    f"{row['endpoint_speed_ft_sec']:.6f}"
                ),
                "camera_raw_transform_valid": bool_text(
                    row["camera_raw_transform_valid"]
                ),
                "camera_raw_transform_accepted": bool_text(
                    row["camera_raw_transform_accepted"]
                ),
                "source_observation_available": bool_text(
                    row["source_observation_available"]
                ),
                "trajectory_observation_kind": row[
                    "trajectory_observation_kind"
                ],
                "trajectory_gap_fill_method": row[
                    "trajectory_gap_fill_method"
                ],
                "trajectory_gap_fill_reason": row[
                    "trajectory_gap_fill_reason"
                ],
            }
        )

    write_csv_atomic(path, AUDIT_FIELDS, rows)


def write_json_atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")

    try:
        with temporary_path.open("w", encoding="utf-8") as output_file:
            json.dump(payload, output_file, indent=2)
            output_file.write("\n")

        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def print_summary(report, output_path, audit_path, report_path):
    validation = report["validation"]
    coverage = report["coverage_audit"]
    gap_audit = report["gap_audit"]
    motion = report["motion_audit"]
    boundary = report["boundary_audit"]
    print("\nPlayer court-trajectory gap interpolation complete.")
    print(
        "Observed rows preserved: "
        f"{validation['input_observed_row_count']}"
    )
    print(
        "Internal gaps filled: "
        f"{gap_audit['filled_internal_gap_count']} gaps / "
        f"{gap_audit['filled_observation_count']} coordinates"
    )
    print(
        "Complete ten-player frames: "
        f"{coverage['input_frames_with_all_ten_players']} -> "
        f"{coverage['output_frames_with_all_ten_players']}"
    )
    print(
        "Remaining missing observations: "
        f"{coverage['remaining_missing_observation_count']} "
        "(all lack a left or right anchor)"
    )
    print(
        "Motion candidates above threshold preserved: "
        f"{motion['input_refined']['candidate_count']} -> "
        f"{motion['gap_interpolated']['candidate_count']}"
    )
    print(
        "Observed/interpolated outside coordinates: "
        f"{boundary['observed_outside_coordinate_count']} / "
        f"{boundary['interpolated_outside_coordinate_count']}"
    )
    print(f"Gap-interpolated coordinates saved to: {output_path}")
    print(f"Gap audit saved to: {audit_path}")
    print(f"Gap report saved to: {report_path}")
    print("Status: pending gap-interpolation visual review.")


def main():
    args = parse_args()
    refinement_report = load_json(
        args.refinement_report, "Trajectory-refinement report"
    )
    (
        rows,
        input_rows_by_player,
        input_rows_by_frame,
        original_fields,
    ) = load_coordinate_rows(args.coordinates)
    _, team_counts = validate_identity_and_boundary_contract(
        rows,
        input_rows_by_player,
        args.half_court_length_ft,
        args.court_width_ft,
    )
    fps, frame_count, reviewed_speed = (
        validate_refinement_report_contract(
            refinement_report,
            rows,
            input_rows_by_player,
            input_rows_by_frame,
        )
    )

    if not math.isclose(
        args.maximum_endpoint_speed_ft_sec,
        reviewed_speed,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError(
            "Gap endpoint speed threshold must match trajectory review: "
            f"{args.maximum_endpoint_speed_ft_sec} != {reviewed_speed}"
        )

    gaps = analyze_internal_gaps(
        input_rows_by_player,
        fps,
        args.maximum_gap_observations,
        args.maximum_endpoint_speed_ft_sec,
        args.half_court_length_ft,
        args.court_width_ft,
    )
    output_rows, audit_rows = build_output_rows(
        rows,
        gaps,
        input_rows_by_frame,
        original_fields,
        fps,
        args.half_court_length_ft,
        args.court_width_ft,
    )
    validate_output_provenance(
        rows,
        output_rows,
        audit_rows,
        original_fields,
    )
    (
        typed_rows,
        output_rows_by_player,
        output_rows_by_frame,
    ) = typed_output_rows(
        output_rows,
        args.half_court_length_ft,
        args.court_width_ft,
    )
    input_motion = analyze_motion(
        input_rows_by_player,
        fps,
        args.maximum_endpoint_speed_ft_sec,
    )
    output_motion = analyze_motion(
        output_rows_by_player,
        fps,
        args.maximum_endpoint_speed_ft_sec,
    )
    report = build_report(
        args,
        rows,
        input_rows_by_player,
        input_rows_by_frame,
        typed_rows,
        output_rows_by_player,
        output_rows_by_frame,
        audit_rows,
        gaps,
        team_counts,
        fps,
        frame_count,
        input_motion,
        output_motion,
    )
    write_csv_atomic(
        args.output,
        list(original_fields) + GAP_FIELDS,
        output_rows,
    )
    write_audit_csv(args.audit, audit_rows)
    write_json_atomic(args.report, report)
    print_summary(report, args.output, args.audit, args.report)


if __name__ == "__main__":
    main()
