import argparse
import csv
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


DEFAULT_TRACKS_PATH = Path(
    "data/outputs/identity/possession_001_reconciled_tracks.csv"
)
DEFAULT_CALIBRATION_PATH = Path(
    "configs/possession_001_court_calibration_final.json"
)
DEFAULT_HOMOGRAPHIES_PATH = Path(
    "data/outputs/court/possession_001_motion_review/"
    "possession_001_camera_homographies.npz"
)
DEFAULT_MOTION_REPORT_PATH = Path(
    "data/outputs/court/possession_001_motion_review/"
    "possession_001_court_motion_review.json"
)
DEFAULT_OUTPUT_PATH = Path(
    "data/outputs/court/possession_001_player_court_coordinates.csv"
)
DEFAULT_REPORT_PATH = Path(
    "data/outputs/court/possession_001_player_court_coordinates.json"
)

REQUIRED_TRACK_FIELDS = {
    "frame_index",
    "timestamp_sec",
    "track_id",
    "confidence",
    "floor_x",
    "floor_y",
    "player_id",
    "reconciled_team",
    "identity_status",
}
OUTPUT_FIELDS = [
    "court_x_ft",
    "court_y_ft",
    "court_position_in_half_court",
    "camera_raw_transform_valid",
    "camera_raw_transform_accepted",
]
EXPECTED_TEAMS = {"white", "dark"}
HOMOGRAPHY_EPSILON = 1e-12
IDENTITY_TOLERANCE = 1e-8
TERMINAL_HOLD_TOLERANCE = 1e-8


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Project reviewed player floor points into the calibrated "
            "right-half-court coordinate system."
        )
    )
    parser.add_argument(
        "--tracks",
        type=Path,
        default=DEFAULT_TRACKS_PATH,
        help="Final reconciled identity CSV.",
    )
    parser.add_argument(
        "--calibration",
        type=Path,
        default=DEFAULT_CALIBRATION_PATH,
        help="Reviewed reference-frame court calibration JSON.",
    )
    parser.add_argument(
        "--homographies",
        type=Path,
        default=DEFAULT_HOMOGRAPHIES_PATH,
        help="Per-frame camera homography NPZ.",
    )
    parser.add_argument(
        "--motion-report",
        type=Path,
        default=DEFAULT_MOTION_REPORT_PATH,
        help="Camera-motion review report JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output player court-coordinate CSV.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Output validation report JSON.",
    )
    parser.add_argument(
        "--expected-player-count",
        type=int,
        default=10,
        help="Required number of reconciled player identities; 0 disables.",
    )
    parser.add_argument(
        "--expected-players-per-team",
        type=int,
        default=5,
        help="Required identities per team; 0 disables.",
    )
    parser.add_argument(
        "--bounds-tolerance-ft",
        type=float,
        default=0.0,
        help=(
            "Tolerance applied only to the in-bounds audit flag. "
            "Coordinates are never clipped."
        ),
    )
    parser.add_argument(
        "--precision",
        type=int,
        default=6,
        help="Decimal places written for court coordinates.",
    )
    args = parser.parse_args()

    if args.expected_player_count < 0:
        parser.error("--expected-player-count cannot be negative")

    if args.expected_players_per_team < 0:
        parser.error("--expected-players-per-team cannot be negative")

    if args.bounds_tolerance_ft < 0:
        parser.error("--bounds-tolerance-ft cannot be negative")

    if not 0 <= args.precision <= 12:
        parser.error("--precision must be between 0 and 12")

    if args.output.resolve() == args.report.resolve():
        parser.error("--output and --report must be different paths")

    return args


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"Required JSON not found: {path}")

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


def load_tracks(path):
    if not path.exists():
        raise FileNotFoundError(f"Reconciled tracks not found: {path}")

    with path.open("r", newline="", encoding="utf-8") as input_file:
        reader = csv.DictReader(input_file)
        fieldnames = list(reader.fieldnames or [])
        missing_fields = sorted(REQUIRED_TRACK_FIELDS - set(fieldnames))
        duplicate_output_fields = sorted(set(OUTPUT_FIELDS) & set(fieldnames))

        if missing_fields:
            raise ValueError(
                "Reconciled CSV is missing required fields: "
                f"{missing_fields}"
            )

        if duplicate_output_fields:
            raise ValueError(
                "Input CSV already contains exporter output fields: "
                f"{duplicate_output_fields}"
            )

        rows = []

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
                "floor_x",
                "floor_y",
            ):
                row[field_name] = parse_float(
                    raw_row[field_name], field_name, row_number
                )

            row["player_id"] = raw_row["player_id"].strip()
            row["reconciled_team"] = raw_row["reconciled_team"].strip()
            row["identity_status"] = raw_row["identity_status"].strip()

            if not row["player_id"]:
                raise ValueError(f"Blank player_id at CSV row {row_number}")

            if row["reconciled_team"] not in EXPECTED_TEAMS:
                raise ValueError(
                    f"Unexpected reconciled_team at CSV row {row_number}: "
                    f"{row['reconciled_team']!r}"
                )

            if row["identity_status"] != "active":
                raise ValueError(
                    "The reconciled CSV must contain active identities only; "
                    f"row {row_number} has {row['identity_status']!r}."
                )

            rows.append(row)

    if not rows:
        raise ValueError(f"Reconciled tracks CSV is empty: {path}")

    duplicate_keys = [
        key
        for key, count in Counter(
            (row["frame_index"], row["player_id"]) for row in rows
        ).items()
        if count > 1
    ]

    if duplicate_keys:
        raise ValueError(
            "Reconciled CSV contains duplicate frame/player rows: "
            f"{duplicate_keys[:10]}"
        )

    return fieldnames, rows


def normalize_homography(matrix, label):
    homography = np.asarray(matrix, dtype=np.float64)

    if homography.shape != (3, 3):
        raise ValueError(f"{label} must have shape (3, 3), not {homography.shape}")

    if not np.isfinite(homography).all():
        raise ValueError(f"{label} contains non-finite values")

    scale = float(homography[2, 2])

    if abs(scale) <= HOMOGRAPHY_EPSILON:
        scale = float(np.linalg.norm(homography))

    if not math.isfinite(scale) or abs(scale) <= HOMOGRAPHY_EPSILON:
        raise ValueError(f"{label} cannot be normalized")

    normalized = homography / scale

    if abs(float(np.linalg.det(normalized))) <= HOMOGRAPHY_EPSILON:
        raise ValueError(f"{label} is singular")

    return normalized


def load_homographies(path):
    if not path.exists():
        raise FileNotFoundError(f"Camera homographies not found: {path}")

    with np.load(path, allow_pickle=False) as artifact:
        required_keys = {
            "smoothed_frame_to_reference",
            "raw_valid_mask",
            "robust_accepted_mask",
            "reference_frame_index",
        }
        missing_keys = sorted(required_keys - set(artifact.files))

        if missing_keys:
            raise ValueError(
                f"Homography artifact is missing keys: {missing_keys}"
            )

        transforms = np.asarray(
            artifact["smoothed_frame_to_reference"], dtype=np.float64
        )
        raw_valid_mask = np.asarray(artifact["raw_valid_mask"], dtype=bool)
        robust_accepted_mask = np.asarray(
            artifact["robust_accepted_mask"], dtype=bool
        )
        reference_values = np.asarray(
            artifact["reference_frame_index"]
        ).reshape(-1)

    if transforms.ndim != 3 or transforms.shape[1:] != (3, 3):
        raise ValueError(
            "smoothed_frame_to_reference must have shape "
            f"(frame_count, 3, 3), not {transforms.shape}"
        )

    frame_count = transforms.shape[0]

    if raw_valid_mask.shape != (frame_count,):
        raise ValueError(
            f"raw_valid_mask must have shape ({frame_count},), "
            f"not {raw_valid_mask.shape}"
        )

    if robust_accepted_mask.shape != (frame_count,):
        raise ValueError(
            f"robust_accepted_mask must have shape ({frame_count},), "
            f"not {robust_accepted_mask.shape}"
        )

    if reference_values.size != 1:
        raise ValueError("reference_frame_index must contain one value")

    reference_frame_index = int(reference_values[0])
    normalized_transforms = np.stack(
        [
            normalize_homography(transform, f"frame {frame_index} homography")
            for frame_index, transform in enumerate(transforms)
        ]
    )

    if not 0 <= reference_frame_index < frame_count:
        raise ValueError(
            f"Reference frame {reference_frame_index} is outside "
            f"0-{frame_count - 1}"
        )

    if not np.allclose(
        normalized_transforms[reference_frame_index],
        np.eye(3),
        rtol=0.0,
        atol=IDENTITY_TOLERANCE,
    ):
        raise ValueError(
            f"Reference frame {reference_frame_index} is not identity"
        )

    return (
        normalized_transforms,
        raw_valid_mask,
        robust_accepted_mask,
        reference_frame_index,
    )


def validate_contract(
    calibration,
    motion_report,
    transforms,
    reference_frame_index,
    rows,
    expected_player_count,
    expected_players_per_team,
):
    frame_count = transforms.shape[0]
    calibration_metadata = calibration.get("video_metadata", {})
    motion_metadata = motion_report.get("video_metadata", {})
    calibration_frame_count = int(calibration_metadata.get("frame_count", -1))
    motion_frame_count = int(motion_metadata.get("frame_count", -1))

    if calibration_frame_count != frame_count:
        raise ValueError(
            "Calibration frame count does not match homographies: "
            f"{calibration_frame_count} != {frame_count}"
        )

    if motion_frame_count != frame_count:
        raise ValueError(
            "Motion-report frame count does not match homographies: "
            f"{motion_frame_count} != {frame_count}"
        )

    calibration_reference = int(calibration.get("reference_frame_index", -1))
    motion_reference = int(motion_report.get("reference_frame_index", -1))

    if calibration_reference != reference_frame_index:
        raise ValueError(
            "Calibration reference frame does not match homographies: "
            f"{calibration_reference} != {reference_frame_index}"
        )

    if motion_reference != reference_frame_index:
        raise ValueError(
            "Motion-report reference frame does not match homographies: "
            f"{motion_reference} != {reference_frame_index}"
        )

    geometry_validation = (
        motion_report.get("tracking_summary", {})
        .get("smoothing", {})
        .get("geometry_validation", {})
    )

    if geometry_validation.get("status") != "passed":
        raise ValueError(
            "Motion report does not contain a passed smoothed-camera "
            "geometry validation. Rerun camera_motion with the current "
            "propagation code before exporting player coordinates."
        )

    invalid_frames = sorted(
        {
            row["frame_index"]
            for row in rows
            if not 0 <= row["frame_index"] < frame_count
        }
    )

    if invalid_frames:
        raise ValueError(
            "Track rows reference frames outside the homography artifact: "
            f"{invalid_frames[:20]}"
        )

    team_by_player = {}

    for row in rows:
        previous_team = team_by_player.setdefault(
            row["player_id"], row["reconciled_team"]
        )

        if previous_team != row["reconciled_team"]:
            raise ValueError(
                f"Player {row['player_id']} changes team from "
                f"{previous_team} to {row['reconciled_team']}"
            )

    if expected_player_count and len(team_by_player) != expected_player_count:
        raise ValueError(
            f"Expected {expected_player_count} player identities, found "
            f"{len(team_by_player)}"
        )

    players_by_team = Counter(team_by_player.values())

    if expected_players_per_team:
        expected_counts = {
            team: expected_players_per_team for team in EXPECTED_TEAMS
        }

        if dict(players_by_team) != expected_counts:
            raise ValueError(
                f"Expected {expected_counts} players by team, found "
                f"{dict(players_by_team)}"
            )

    terminal = (
        motion_report.get("tracking_summary", {})
        .get("smoothing", {})
        .get("terminal_stabilization", {})
    )

    if terminal.get("applied"):
        start_frame = int(terminal["start_frame"])
        end_frame = int(terminal["end_frame"])
        anchor_frame = int(terminal["anchor_frame"])

        if not (
            0 <= anchor_frame < start_frame <= end_frame < frame_count
        ):
            raise ValueError(
                "Motion report has invalid terminal stabilization bounds: "
                f"anchor={anchor_frame}, start={start_frame}, end={end_frame}"
            )

        if not np.allclose(
            transforms[start_frame : end_frame + 1],
            transforms[anchor_frame],
            rtol=0.0,
            atol=TERMINAL_HOLD_TOLERANCE,
        ):
            raise ValueError(
                "Terminal stabilization metadata does not match the "
                "homography artifact"
            )

    return team_by_player, players_by_team, terminal


def project_floor_point(frame_to_court, floor_x, floor_y, frame_index, player_id):
    projected = frame_to_court @ np.asarray(
        [floor_x, floor_y, 1.0], dtype=np.float64
    )
    denominator = float(projected[2])

    if not math.isfinite(denominator) or abs(denominator) <= HOMOGRAPHY_EPSILON:
        raise ValueError(
            "Court projection is undefined for "
            f"{player_id} at frame {frame_index}"
        )

    court_x = float(projected[0] / denominator)
    court_y = float(projected[1] / denominator)

    if not math.isfinite(court_x) or not math.isfinite(court_y):
        raise ValueError(
            "Court projection is non-finite for "
            f"{player_id} at frame {frame_index}"
        )

    return court_x, court_y


def export_rows(
    rows,
    transforms,
    raw_valid_mask,
    robust_accepted_mask,
    reference_to_court,
    half_court_length,
    court_width,
    bounds_tolerance,
    precision,
):
    output_rows = []
    coordinate_records = []
    format_string = f".{{precision}}f".format(precision=precision)

    for row in rows:
        frame_index = row["frame_index"]
        frame_to_court = normalize_homography(
            reference_to_court @ transforms[frame_index],
            f"composed frame {frame_index} homography",
        )
        court_x, court_y = project_floor_point(
            frame_to_court,
            row["floor_x"],
            row["floor_y"],
            frame_index,
            row["player_id"],
        )
        in_half_court = (
            -bounds_tolerance <= court_x <= half_court_length + bounds_tolerance
            and -bounds_tolerance <= court_y <= court_width + bounds_tolerance
        )
        output_row = dict(row)

        for field_name in (
            "frame_index",
            "track_id",
            "timestamp_sec",
            "confidence",
            "floor_x",
            "floor_y",
        ):
            output_row[field_name] = str(output_row[field_name])

        output_row["court_x_ft"] = format(court_x, format_string)
        output_row["court_y_ft"] = format(court_y, format_string)
        output_row["court_position_in_half_court"] = str(in_half_court).lower()
        output_row["camera_raw_transform_valid"] = str(
            bool(raw_valid_mask[frame_index])
        ).lower()
        output_row["camera_raw_transform_accepted"] = str(
            bool(robust_accepted_mask[frame_index])
        ).lower()
        output_rows.append(output_row)
        coordinate_records.append(
            {
                "frame_index": frame_index,
                "player_id": row["player_id"],
                "team": row["reconciled_team"],
                "court_x_ft": court_x,
                "court_y_ft": court_y,
                "in_half_court": in_half_court,
            }
        )

    return output_rows, coordinate_records


def summarize_coordinates(records):
    records_by_player = defaultdict(list)

    for record in records:
        records_by_player[record["player_id"]].append(record)

    per_player = {}

    for player_id, player_records in sorted(records_by_player.items()):
        x_values = [record["court_x_ft"] for record in player_records]
        y_values = [record["court_y_ft"] for record in player_records]
        outside_count = sum(
            not record["in_half_court"] for record in player_records
        )
        per_player[player_id] = {
            "team": player_records[0]["team"],
            "row_count": len(player_records),
            "first_frame": min(
                record["frame_index"] for record in player_records
            ),
            "last_frame": max(
                record["frame_index"] for record in player_records
            ),
            "court_x_range_ft": [
                round(min(x_values), 6),
                round(max(x_values), 6),
            ],
            "court_y_range_ft": [
                round(min(y_values), 6),
                round(max(y_values), 6),
            ],
            "outside_half_court_row_count": outside_count,
        }

    outside_count = sum(not record["in_half_court"] for record in records)

    return {
        "inside_half_court_row_count": len(records) - outside_count,
        "outside_half_court_row_count": outside_count,
        "inside_half_court_fraction": round(
            (len(records) - outside_count) / len(records), 6
        ),
        "per_player": per_player,
    }


def write_csv_atomic(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(path.name + ".tmp")

    try:
        with temporary_path.open(
            "w", newline="", encoding="utf-8"
        ) as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


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


def main():
    args = parse_args()
    calibration = load_json(args.calibration)
    motion_report = load_json(args.motion_report)
    input_fieldnames, rows = load_tracks(args.tracks)
    (
        transforms,
        raw_valid_mask,
        robust_accepted_mask,
        reference_frame_index,
    ) = load_homographies(args.homographies)
    (
        team_by_player,
        players_by_team,
        terminal_stabilization,
    ) = validate_contract(
        calibration,
        motion_report,
        transforms,
        reference_frame_index,
        rows,
        args.expected_player_count,
        args.expected_players_per_team,
    )
    reference_to_court = normalize_homography(
        calibration.get("image_to_court_homography"),
        "reviewed image_to_court_homography",
    )
    court_model = calibration.get("court_model", {})

    try:
        half_court_length = float(court_model["half_court_length_ft"])
        court_width = float(court_model["court_width_ft"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(
            "Calibration court model is missing numeric half-court bounds"
        ) from error

    if half_court_length <= 0 or court_width <= 0:
        raise ValueError("Calibration court dimensions must be positive")

    output_rows, coordinate_records = export_rows(
        rows,
        transforms,
        raw_valid_mask,
        robust_accepted_mask,
        reference_to_court,
        half_court_length,
        court_width,
        args.bounds_tolerance_ft,
        args.precision,
    )
    output_fieldnames = input_fieldnames + OUTPUT_FIELDS
    coordinate_summary = summarize_coordinates(coordinate_records)
    frame_indices = [row["frame_index"] for row in rows]
    frames_with_tracks = len(set(frame_indices))
    report = {
        "status": "validated_player_court_coordinates_exported",
        "source_tracks": str(args.tracks),
        "source_calibration": str(args.calibration),
        "source_homographies": str(args.homographies),
        "source_motion_report": str(args.motion_report),
        "output_csv": str(args.output),
        "coordinate_system": {
            "units": "feet",
            "scope": court_model.get("coordinate_scope"),
            "x_bounds_ft": [0.0, half_court_length],
            "y_bounds_ft": [0.0, court_width],
            "convention": court_model.get("coordinate_convention"),
            "coordinates_clipped": False,
            "bounds_audit_tolerance_ft": args.bounds_tolerance_ft,
        },
        "validation": {
            "row_count": len(rows),
            "frame_count_in_homography_artifact": transforms.shape[0],
            "frames_with_track_rows": frames_with_tracks,
            "first_track_frame": min(frame_indices),
            "last_track_frame": max(frame_indices),
            "reference_frame_index": reference_frame_index,
            "reference_frame_is_identity": True,
            "unique_player_count": len(team_by_player),
            "players_by_team": dict(sorted(players_by_team.items())),
            "raw_valid_transform_frame_count": int(
                np.count_nonzero(raw_valid_mask)
            ),
            "robust_accepted_transform_frame_count": int(
                np.count_nonzero(robust_accepted_mask)
            ),
            "terminal_stabilization": terminal_stabilization,
        },
        "court_position_audit": coordinate_summary,
        "output_columns": output_fieldnames,
    }

    write_csv_atomic(args.output, output_fieldnames, output_rows)
    write_json_atomic(args.report, report)

    outside_count = coordinate_summary["outside_half_court_row_count"]
    print("\nPlayer court-coordinate export complete.")
    print(f"Validated input rows: {len(rows)}")
    print(
        f"Validated player identities: {len(team_by_player)} "
        f"({dict(sorted(players_by_team.items()))})"
    )
    print(
        f"Validated homographies: {transforms.shape[0]} | "
        f"reference frame {reference_frame_index} is identity"
    )

    if terminal_stabilization.get("applied"):
        print(
            "Validated terminal hold: frames "
            f"{terminal_stabilization['start_frame']} -> "
            f"{terminal_stabilization['end_frame']} hold frame "
            f"{terminal_stabilization['anchor_frame']}"
        )

    print(
        "Court-bound audit: "
        f"{len(rows) - outside_count} inside / {outside_count} outside "
        "(coordinates preserved; not clipped)"
    )
    print(f"Court-coordinate CSV saved to: {args.output}")
    print(f"Validation report saved to: {args.report}")


if __name__ == "__main__":
    main()
