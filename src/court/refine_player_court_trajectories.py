import argparse
import csv
import json
import math
import os
import statistics
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_COORDINATES_PATH = Path(
    "data/outputs/court/possession_001_player_court_coordinates.csv"
)
DEFAULT_REVIEW_REPORT_PATH = Path(
    "data/outputs/visualization/"
    "possession_001_player_court_coordinates_review.json"
)
DEFAULT_OUTPUT_PATH = Path(
    "data/outputs/court/"
    "possession_001_player_court_coordinates_refined.csv"
)
DEFAULT_AUDIT_PATH = Path(
    "data/outputs/court/"
    "possession_001_player_court_trajectory_refinement_audit.csv"
)
DEFAULT_REPORT_PATH = Path(
    "data/outputs/court/"
    "possession_001_player_court_trajectory_refinement.json"
)

EXPECTED_REVIEW_STATUS = "pending_player_coordinate_visual_review"
OUTPUT_STATUS = "refined_player_court_trajectories_pending_visual_review"
EXPECTED_PLAYER_COUNT = 10
EXPECTED_TEAM_COUNTS = {"white": 5, "dark": 5}

REFINEMENT_FIELDS = [
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
]

AUDIT_FIELDS = [
    "player_id",
    "reconciled_team",
    "frame_index",
    "timestamp_sec",
    "track_id",
    "confidence",
    "raw_court_x_ft",
    "raw_court_y_ft",
    "refined_court_x_ft",
    "refined_court_y_ft",
    "raw_court_position_in_half_court",
    "trajectory_refinement_applied",
    "trajectory_refinement_method",
    "trajectory_refinement_reason",
    "trajectory_correction_distance_ft",
    "trajectory_anchor_frames",
    "trajectory_raw_jump_candidate",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Refine isolated impossible player court-coordinate motion "
            "while preserving raw observations and a complete audit trail."
        )
    )
    parser.add_argument(
        "--coordinates",
        type=Path,
        default=DEFAULT_COORDINATES_PATH,
        help="Raw validated player court-coordinate CSV.",
    )
    parser.add_argument(
        "--review-report",
        type=Path,
        default=DEFAULT_REVIEW_REPORT_PATH,
        help="Raw coordinate visualization review report.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Refined player court-coordinate CSV.",
    )
    parser.add_argument(
        "--audit",
        type=Path,
        default=DEFAULT_AUDIT_PATH,
        help="Row-level trajectory correction audit CSV.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Trajectory-refinement validation report.",
    )
    parser.add_argument(
        "--maximum-speed-ft-sec",
        type=float,
        default=45.0,
        help=(
            "Maximum non-boundary transition speed retained in the "
            "trusted observation path."
        ),
    )
    parser.add_argument(
        "--maximum-extrapolation-observations",
        type=int,
        default=2,
        help="Maximum leading or trailing observations extrapolated.",
    )
    parser.add_argument(
        "--extrapolation-anchor-count",
        type=int,
        default=5,
        help="Trusted observations used for robust endpoint extrapolation.",
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

    if args.maximum_speed_ft_sec <= 0:
        parser.error("--maximum-speed-ft-sec must be positive")

    if args.maximum_extrapolation_observations < 0:
        parser.error(
            "--maximum-extrapolation-observations cannot be negative"
        )

    if args.extrapolation_anchor_count < 3:
        parser.error("--extrapolation-anchor-count must be at least 3")

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


def load_coordinate_rows(path):
    if not path.exists():
        raise FileNotFoundError(f"Coordinate CSV not found: {path}")

    required_fields = {
        "frame_index",
        "timestamp_sec",
        "track_id",
        "confidence",
        "player_id",
        "reconciled_team",
        "court_x_ft",
        "court_y_ft",
        "court_position_in_half_court",
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
                "Coordinate CSV is missing required fields: "
                f"{missing_fields}"
            )

        conflicting_fields = sorted(
            set(fieldnames).intersection(REFINEMENT_FIELDS)
        )

        if conflicting_fields:
            raise ValueError(
                "Input coordinates already contain refinement fields: "
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
                "raw_x": parse_float(
                    raw_row["court_x_ft"], "court_x_ft", row_number
                ),
                "raw_y": parse_float(
                    raw_row["court_y_ft"], "court_y_ft", row_number
                ),
                "raw_inside": parse_bool(
                    raw_row["court_position_in_half_court"],
                    "court_position_in_half_court",
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

    return (
        rows,
        dict(rows_by_player),
        dict(rows_by_frame),
        fieldnames,
    )


def validate_identity_contract(rows_by_player):
    if len(rows_by_player) != EXPECTED_PLAYER_COUNT:
        raise ValueError(
            f"Expected ten players, found {len(rows_by_player)}"
        )

    team_by_player = {}

    for player_id, rows in rows_by_player.items():
        teams = {row["reconciled_team"] for row in rows}

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

    return team_by_player, dict(sorted(team_counts.items()))


def position_inside_half_court(x, y, half_length, court_width):
    return 0.0 <= x <= half_length and 0.0 <= y <= court_width


def validate_boundary_flags(rows, half_length, court_width):
    mismatches = []

    for row in rows:
        expected = position_inside_half_court(
            row["raw_x"], row["raw_y"], half_length, court_width
        )

        if expected != row["raw_inside"]:
            mismatches.append((row["frame_index"], row["player_id"]))

    if mismatches:
        raise ValueError(
            "Raw boundary flags disagree with coordinates: "
            f"{mismatches[:20]}"
        )


def transition_speed(first, second, fps, x_key, y_key):
    frame_gap = second["frame_index"] - first["frame_index"]

    if frame_gap <= 0:
        raise ValueError("Transition frame gap must be positive")

    distance = math.hypot(
        second[x_key] - first[x_key],
        second[y_key] - first[y_key],
    )
    return distance * fps / frame_gap, distance, frame_gap


def analyze_motion(rows_by_player, fps, threshold, x_key, y_key):
    candidates = []
    maximum_speed = 0.0
    transition_count = 0

    for player_id in sorted(rows_by_player, key=player_sort_key):
        rows = rows_by_player[player_id]

        for first, second in zip(rows, rows[1:]):
            speed, distance, frame_gap = transition_speed(
                first, second, fps, x_key, y_key
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
                        "touches_protected_outside_observation": (
                            not first["raw_inside"]
                            or not second["raw_inside"]
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


def validate_review_contract(
    review_report,
    rows,
    rows_by_player,
    rows_by_frame,
    raw_motion,
    maximum_speed,
):
    if review_report.get("status") != EXPECTED_REVIEW_STATUS:
        raise ValueError(
            "Review report status is not the expected pending status: "
            f"{review_report.get('status')!r}"
        )

    validation = review_report.get("validation", {})
    analysis = review_report.get("coordinate_analysis", {})
    video_metadata = validation.get("video_metadata", {})

    if int(validation.get("coordinate_row_count", -1)) != len(rows):
        raise ValueError("Review report row count does not match the CSV")

    if int(validation.get("identity_count", -1)) != len(rows_by_player):
        raise ValueError(
            "Review report identity count does not match the CSV"
        )

    frame_count = int(video_metadata.get("frame_count", -1))
    fps = float(video_metadata.get("fps", -1.0))

    if frame_count <= 0 or fps <= 0:
        raise ValueError(
            f"Review report video metadata is invalid: {video_metadata}"
        )

    if rows_by_frame and max(rows_by_frame) >= frame_count:
        raise ValueError("Coordinate rows exceed the source frame count")

    reported_threshold = float(
        analysis.get("jump_speed_threshold_ft_sec", -1.0)
    )

    if not math.isclose(
        reported_threshold, maximum_speed, rel_tol=0.0, abs_tol=1e-9
    ):
        raise ValueError(
            "Refinement speed threshold must match the reviewed source: "
            f"{maximum_speed} != {reported_threshold}"
        )

    reported_candidates = analysis.get("jump_candidates", [])

    if len(reported_candidates) != raw_motion["candidate_count"]:
        raise ValueError(
            "Recomputed raw jump count does not match the review report: "
            f"{raw_motion['candidate_count']} != "
            f"{len(reported_candidates)}"
        )

    reported_by_key = {
        (
            candidate["player_id"],
            int(candidate["from_frame"]),
            int(candidate["to_frame"]),
        ): candidate
        for candidate in reported_candidates
    }

    for candidate in raw_motion["candidates"]:
        key = (
            candidate["player_id"],
            candidate["from_frame"],
            candidate["to_frame"],
        )
        reported = reported_by_key.get(key)

        if reported is None:
            raise ValueError(
                f"Raw motion candidate missing from review report: {key}"
            )

        if not math.isclose(
            candidate["speed_ft_sec"],
            float(reported["speed_ft_sec"]),
            rel_tol=0.0,
            abs_tol=0.001,
        ):
            raise ValueError(
                f"Raw motion candidate speed changed for {key}: "
                f"{candidate['speed_ft_sec']} != "
                f"{reported['speed_ft_sec']}"
            )

    reported_outside = int(analysis.get("outside_row_count", -1))
    actual_outside = sum(not row["raw_inside"] for row in rows)

    if reported_outside != actual_outside:
        raise ValueError(
            "Review report outside count does not match the CSV: "
            f"{reported_outside} != {actual_outside}"
        )

    return fps, frame_count


def path_state_better(candidate, current):
    if candidate["count"] != current["count"]:
        return candidate["count"] > current["count"]

    if not math.isclose(
        candidate["motion_cost"],
        current["motion_cost"],
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        return candidate["motion_cost"] < current["motion_cost"]

    if not math.isclose(
        candidate["confidence_sum"],
        current["confidence_sum"],
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        return candidate["confidence_sum"] > current["confidence_sum"]

    return False


def select_trusted_path(rows, fps, maximum_speed):
    states = []

    for index, row in enumerate(rows):
        best = {
            "count": 1,
            "motion_cost": 0.0,
            "confidence_sum": row["confidence"],
            "previous": None,
        }

        for previous_index in range(index):
            previous_row = rows[previous_index]
            speed, _, _ = transition_speed(
                previous_row,
                row,
                fps,
                "raw_x",
                "raw_y",
            )
            if speed > maximum_speed:
                continue

            previous_state = states[previous_index]
            candidate = {
                "count": previous_state["count"] + 1,
                "motion_cost": (
                    previous_state["motion_cost"] + speed * speed
                ),
                "confidence_sum": (
                    previous_state["confidence_sum"] + row["confidence"]
                ),
                "previous": previous_index,
            }

            if path_state_better(candidate, best):
                best = candidate

        states.append(best)

    best_end = 0

    for index in range(1, len(rows)):
        if path_state_better(states[index], states[best_end]):
            best_end = index

    trusted_indices = set()
    current = best_end

    while current is not None:
        trusted_indices.add(current)
        current = states[current]["previous"]

    return trusted_indices


def contiguous_index_groups(indices):
    groups = []

    for index in sorted(indices):
        if not groups or index > groups[-1][-1] + 1:
            groups.append([])

        groups[-1].append(index)

    return groups


def robust_linear_prediction(anchor_rows, target_frame, axis_key):
    slopes = []

    for first_index, first in enumerate(anchor_rows):
        for second in anchor_rows[first_index + 1 :]:
            frame_gap = second["frame_index"] - first["frame_index"]

            if frame_gap > 0:
                slopes.append(
                    (second[axis_key] - first[axis_key]) / frame_gap
                )

    slope = statistics.median(slopes) if slopes else 0.0
    intercept = statistics.median(
        row[axis_key] - slope * row["frame_index"]
        for row in anchor_rows
    )
    return slope * target_frame + intercept


def mark_raw_jump_rows(raw_motion):
    candidate_rows = set()

    for candidate in raw_motion["candidates"]:
        candidate_rows.add(
            (candidate["player_id"], candidate["from_frame"])
        )
        candidate_rows.add(
            (candidate["player_id"], candidate["to_frame"])
        )

    return candidate_rows


def initialize_refinement_fields(rows, trusted_indices, raw_jump_rows):
    for index, row in enumerate(rows):
        trusted = index in trusted_indices
        row["refined_x"] = row["raw_x"]
        row["refined_y"] = row["raw_y"]
        row["refined_inside"] = row["raw_inside"]
        row["refinement_applied"] = False
        row["refinement_method"] = (
            "trusted_raw_boundary_observation"
            if trusted and not row["raw_inside"]
            else "trusted_raw_observation"
            if trusted
            else "unreviewed_path_outlier"
        )
        row["refinement_reason"] = (
            "maximum_speed_path_retained"
            if trusted
            else "pending_path_outlier_correction"
        )
        row["correction_distance"] = 0.0
        row["anchor_frames"] = ""
        row["trusted_path"] = trusted
        row["raw_jump_candidate"] = (
            row["player_id"], row["frame_index"]
        ) in raw_jump_rows


def apply_candidate_correction(
    row,
    refined_x,
    refined_y,
    method,
    reason,
    anchor_frames,
    half_length,
    court_width,
):
    row["refined_inside"] = position_inside_half_court(
        refined_x, refined_y, half_length, court_width
    )

    row["refined_x"] = refined_x
    row["refined_y"] = refined_y
    row["correction_distance"] = math.hypot(
        refined_x - row["raw_x"], refined_y - row["raw_y"]
    )
    row["refinement_applied"] = row["correction_distance"] > 1e-9
    row["refinement_method"] = method
    row["refinement_reason"] = reason
    row["anchor_frames"] = anchor_frames
    return row["refinement_applied"]


def refine_player_rows(
    rows,
    trusted_indices,
    maximum_extrapolation_observations,
    extrapolation_anchor_count,
    half_length,
    court_width,
):
    discarded_indices = set(range(len(rows))) - trusted_indices
    groups = contiguous_index_groups(discarded_indices)

    for group in groups:
        first_index = group[0]
        last_index = group[-1]
        left_index = first_index - 1
        right_index = last_index + 1
        has_left = left_index >= 0 and left_index in trusted_indices
        has_right = (
            right_index < len(rows) and right_index in trusted_indices
        )

        if has_left and has_right:
            left = rows[left_index]
            right = rows[right_index]
            frame_span = right["frame_index"] - left["frame_index"]

            for index in group:
                row = rows[index]
                fraction = (
                    (row["frame_index"] - left["frame_index"])
                    / frame_span
                )
                refined_x = left["raw_x"] + fraction * (
                    right["raw_x"] - left["raw_x"]
                )
                refined_y = left["raw_y"] + fraction * (
                    right["raw_y"] - left["raw_y"]
                )
                apply_candidate_correction(
                    row,
                    refined_x,
                    refined_y,
                    "linear_interpolation",
                    "maximum_speed_path_outlier",
                    (
                        f"{left['frame_index']}:"
                        f"{right['frame_index']}"
                    ),
                    half_length,
                    court_width,
                )

            continue

        can_extrapolate = (
            len(group) <= maximum_extrapolation_observations
            and (has_left or has_right)
        )

        if can_extrapolate:
            trusted_order = sorted(trusted_indices)

            if has_left:
                anchor_indices = [
                    index
                    for index in trusted_order
                    if index <= left_index
                ][-extrapolation_anchor_count:]
                method = "robust_forward_extrapolation"
            else:
                anchor_indices = [
                    index
                    for index in trusted_order
                    if index >= right_index
                ][:extrapolation_anchor_count]
                method = "robust_backward_extrapolation"

            if len(anchor_indices) >= 3:
                anchors = [rows[index] for index in anchor_indices]
                anchor_frames = ":".join(
                    str(row["frame_index"]) for row in anchors
                )

                for index in group:
                    row = rows[index]
                    refined_x = robust_linear_prediction(
                        anchors, row["frame_index"], "raw_x"
                    )
                    refined_y = robust_linear_prediction(
                        anchors, row["frame_index"], "raw_y"
                    )
                    apply_candidate_correction(
                        row,
                        refined_x,
                        refined_y,
                        method,
                        "maximum_speed_path_endpoint_outlier",
                        anchor_frames,
                        half_length,
                        court_width,
                    )

                continue

        for index in group:
            row = rows[index]
            row["refinement_method"] = "raw_observation_preserved"
            row["refinement_reason"] = "unresolved_unbracketed_run"


def refine_trajectories(
    rows_by_player,
    fps,
    maximum_speed,
    maximum_extrapolation_observations,
    extrapolation_anchor_count,
    half_length,
    court_width,
    raw_jump_rows,
):
    trusted_indices_by_player = {}

    for player_id in sorted(rows_by_player, key=player_sort_key):
        player_rows = rows_by_player[player_id]
        trusted_indices = select_trusted_path(
            player_rows, fps, maximum_speed
        )
        trusted_indices_by_player[player_id] = trusted_indices
        initialize_refinement_fields(
            player_rows, trusted_indices, raw_jump_rows
        )
        refine_player_rows(
            player_rows,
            trusted_indices,
            maximum_extrapolation_observations,
            extrapolation_anchor_count,
            half_length,
            court_width,
        )

    return trusted_indices_by_player


def validate_refined_boundaries(rows, half_length, court_width):
    mismatches = []

    for row in rows:
        refined_inside = position_inside_half_court(
            row["refined_x"],
            row["refined_y"],
            half_length,
            court_width,
        )

        if refined_inside != row["refined_inside"]:
            mismatches.append((row["frame_index"], row["player_id"]))

    if mismatches:
        raise RuntimeError(
            "Refined boundary flags disagree with refined coordinates: "
            f"{mismatches[:20]}"
        )


def percentile(values, fraction):
    if not values:
        return 0.0

    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    lower_index = int(math.floor(position))
    upper_index = int(math.ceil(position))

    if lower_index == upper_index:
        return ordered[lower_index]

    weight = position - lower_index
    return ordered[lower_index] * (1.0 - weight) + ordered[
        upper_index
    ] * weight


def build_gap_audit(rows_by_player, frame_count):
    per_player = {}
    total_missing_observations = 0
    internal_missing_observations = 0

    for player_id in sorted(rows_by_player, key=player_sort_key):
        rows = rows_by_player[player_id]
        frames = [row["frame_index"] for row in rows]
        internal_gaps = []

        for first, second in zip(frames, frames[1:]):
            missing_count = second - first - 1

            if missing_count > 0:
                internal_gaps.append(
                    {
                        "after_frame": first,
                        "before_frame": second,
                        "missing_observation_count": missing_count,
                    }
                )
                internal_missing_observations += missing_count

        leading_missing = frames[0]
        trailing_missing = frame_count - 1 - frames[-1]
        missing_count = frame_count - len(frames)
        total_missing_observations += missing_count
        per_player[player_id] = {
            "row_count": len(rows),
            "first_frame": frames[0],
            "last_frame": frames[-1],
            "missing_observation_count": missing_count,
            "leading_missing_observation_count": leading_missing,
            "trailing_missing_observation_count": trailing_missing,
            "internal_missing_observation_count": sum(
                gap["missing_observation_count"] for gap in internal_gaps
            ),
            "internal_gaps": internal_gaps,
        }

    return {
        "rows_synthesized": 0,
        "gaps_interpolated": 0,
        "total_missing_observation_count": total_missing_observations,
        "internal_missing_observation_count": (
            internal_missing_observations
        ),
        "policy": (
            "Missing observations are preserved for a separate gap-filling "
            "review; this pass refines only existing rows."
        ),
        "per_player": per_player,
    }


def choose_checkpoint_frames(rows, limit=12, spacing=3):
    corrected = sorted(
        (row for row in rows if row["refinement_applied"]),
        key=lambda row: (
            -row["correction_distance"],
            row["frame_index"],
            row["player_id"],
        ),
    )
    selected = []

    for row in corrected:
        frame_index = row["frame_index"]

        if any(abs(frame_index - frame) <= spacing for frame in selected):
            continue

        selected.append(frame_index)

        if len(selected) >= limit:
            break

    return sorted(selected)


def write_refined_csv(path, rows, original_fields):
    output_fields = list(original_fields) + REFINEMENT_FIELDS
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")

    with temporary_path.open(
        "w", newline="", encoding="utf-8"
    ) as output_file:
        writer = csv.DictWriter(
            output_file, fieldnames=output_fields, extrasaction="ignore"
        )
        writer.writeheader()

        for row in sorted(rows, key=lambda item: item["input_index"]):
            output_row = dict(row["raw"])
            output_row["court_x_ft"] = f"{row['refined_x']:.6f}"
            output_row["court_y_ft"] = f"{row['refined_y']:.6f}"
            output_row["court_position_in_half_court"] = bool_text(
                row["refined_inside"]
            )
            output_row["raw_court_x_ft"] = f"{row['raw_x']:.6f}"
            output_row["raw_court_y_ft"] = f"{row['raw_y']:.6f}"
            output_row[
                "raw_court_position_in_half_court"
            ] = bool_text(row["raw_inside"])
            output_row["trajectory_refinement_applied"] = bool_text(
                row["refinement_applied"]
            )
            output_row[
                "trajectory_refinement_method"
            ] = row["refinement_method"]
            output_row[
                "trajectory_refinement_reason"
            ] = row["refinement_reason"]
            output_row[
                "trajectory_correction_distance_ft"
            ] = f"{row['correction_distance']:.6f}"
            output_row[
                "trajectory_anchor_frames"
            ] = row["anchor_frames"]
            output_row[
                "trajectory_trusted_path_observation"
            ] = bool_text(row["trusted_path"])
            output_row["trajectory_raw_jump_candidate"] = bool_text(
                row["raw_jump_candidate"]
            )
            writer.writerow(output_row)

    os.replace(temporary_path, path)


def write_audit_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")

    with temporary_path.open(
        "w", newline="", encoding="utf-8"
    ) as output_file:
        writer = csv.DictWriter(output_file, fieldnames=AUDIT_FIELDS)
        writer.writeheader()

        for row in sorted(
            (
                item
                for item in rows
                if not item["trusted_path"]
                or item["refinement_applied"]
            ),
            key=lambda item: (
                item["frame_index"],
                player_sort_key(item["player_id"]),
            ),
        ):
            writer.writerow(
                {
                    "player_id": row["player_id"],
                    "reconciled_team": row["reconciled_team"],
                    "frame_index": row["frame_index"],
                    "timestamp_sec": f"{row['timestamp_sec']:.6f}",
                    "track_id": row["track_id"],
                    "confidence": f"{row['confidence']:.6f}",
                    "raw_court_x_ft": f"{row['raw_x']:.6f}",
                    "raw_court_y_ft": f"{row['raw_y']:.6f}",
                    "refined_court_x_ft": (
                        f"{row['refined_x']:.6f}"
                    ),
                    "refined_court_y_ft": (
                        f"{row['refined_y']:.6f}"
                    ),
                    "raw_court_position_in_half_court": bool_text(
                        row["raw_inside"]
                    ),
                    "trajectory_refinement_applied": bool_text(
                        row["refinement_applied"]
                    ),
                    "trajectory_refinement_method": (
                        row["refinement_method"]
                    ),
                    "trajectory_refinement_reason": (
                        row["refinement_reason"]
                    ),
                    "trajectory_correction_distance_ft": (
                        f"{row['correction_distance']:.6f}"
                    ),
                    "trajectory_anchor_frames": row["anchor_frames"],
                    "trajectory_raw_jump_candidate": bool_text(
                        row["raw_jump_candidate"]
                    ),
                }
            )

    os.replace(temporary_path, path)


def write_json_atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")

    with temporary_path.open("w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2)
        output_file.write("\n")

    os.replace(temporary_path, path)


def build_report(
    args,
    rows,
    rows_by_player,
    team_counts,
    fps,
    frame_count,
    raw_motion,
    refined_motion,
    gap_audit,
    trusted_indices_by_player,
):
    corrected_rows = [
        row for row in rows if row["refinement_applied"]
    ]
    discarded_rows = [row for row in rows if not row["trusted_path"]]
    correction_distances = [
        row["correction_distance"] for row in corrected_rows
    ]
    corrected_by_player = Counter(
        row["player_id"] for row in corrected_rows
    )
    corrected_by_method = Counter(
        row["refinement_method"] for row in corrected_rows
    )
    raw_outside_rows = [
        row for row in rows if not row["raw_inside"]
    ]
    refined_outside_rows = [
        row for row in rows if not row["refined_inside"]
    ]
    boundary_state_changed_rows = [
        row
        for row in rows
        if row["raw_inside"] != row["refined_inside"]
    ]
    unresolved_rows = [
        row
        for row in discarded_rows
        if not row["refinement_applied"]
    ]
    remaining_candidates = refined_motion["candidates"]

    if remaining_candidates:
        raise RuntimeError(
            "Refinement left speed candidates after correcting raw path "
            "outliers: "
            f"{remaining_candidates[:20]}"
        )

    corrected_records = []

    for row in sorted(
        corrected_rows,
        key=lambda item: (
            item["frame_index"],
            player_sort_key(item["player_id"]),
        ),
    ):
        corrected_records.append(
            {
                "player_id": row["player_id"],
                "frame_index": row["frame_index"],
                "raw_court_x_ft": round(row["raw_x"], 6),
                "raw_court_y_ft": round(row["raw_y"], 6),
                "refined_court_x_ft": round(row["refined_x"], 6),
                "refined_court_y_ft": round(row["refined_y"], 6),
                "correction_distance_ft": round(
                    row["correction_distance"], 6
                ),
                "method": row["refinement_method"],
                "anchor_frames": row["anchor_frames"],
            }
        )

    return {
        "status": OUTPUT_STATUS,
        "source_coordinates": str(args.coordinates),
        "source_review_report": str(args.review_report),
        "output_coordinates": str(args.output),
        "output_audit": str(args.audit),
        "settings": {
            "maximum_speed_ft_sec": args.maximum_speed_ft_sec,
            "maximum_extrapolation_observations": (
                args.maximum_extrapolation_observations
            ),
            "extrapolation_anchor_count": (
                args.extrapolation_anchor_count
            ),
            "protect_raw_outside_observations": False,
            "boundary_policy": (
                "Outside observations are retained when they belong to "
                "the maximum-speed trusted path; isolated implausible "
                "boundary samples may be corrected without clipping."
            ),
            "half_court_length_ft": args.half_court_length_ft,
            "court_width_ft": args.court_width_ft,
        },
        "validation": {
            "row_count": len(rows),
            "frame_count": frame_count,
            "fps": fps,
            "identity_count": len(rows_by_player),
            "identity_counts_by_team": team_counts,
            "source_review_contract_verified": True,
            "row_count_preserved": True,
            "identity_assignments_preserved": True,
            "source_bbox_and_track_fields_preserved": True,
        },
        "trusted_path_audit": {
            "trusted_raw_observation_count": sum(
                len(indices)
                for indices in trusted_indices_by_player.values()
            ),
            "discarded_path_observation_count": len(discarded_rows),
            "corrected_observation_count": len(corrected_rows),
            "unresolved_discarded_observation_count": len(
                unresolved_rows
            ),
            "corrected_fraction": round(
                len(corrected_rows) / len(rows), 6
            ),
            "corrected_by_player": dict(
                sorted(corrected_by_player.items(), key=lambda item: (
                    player_sort_key(item[0])
                ))
            ),
            "corrected_by_method": dict(
                sorted(corrected_by_method.items())
            ),
            "correction_distance_ft": {
                "median": round(
                    statistics.median(correction_distances), 6
                )
                if correction_distances
                else 0.0,
                "p95": round(
                    percentile(correction_distances, 0.95), 6
                ),
                "maximum": round(max(correction_distances), 6)
                if correction_distances
                else 0.0,
            },
            "recommended_checkpoint_frames": (
                choose_checkpoint_frames(rows)
            ),
            "corrected_observations": corrected_records,
        },
        "motion_audit": {
            "raw": raw_motion,
            "refined": refined_motion,
            "candidate_reduction_count": (
                raw_motion["candidate_count"]
                - refined_motion["candidate_count"]
            ),
            "candidate_reduction_fraction": round(
                (
                    raw_motion["candidate_count"]
                    - refined_motion["candidate_count"]
                )
                / raw_motion["candidate_count"],
                6,
            )
            if raw_motion["candidate_count"]
            else 0.0,
            "remaining_candidate_count": len(remaining_candidates),
            "remaining_candidates_are_boundary_protected": False,
        },
        "boundary_audit": {
            "raw_outside_observation_count": len(
                raw_outside_rows
            ),
            "refined_outside_observation_count": len(
                refined_outside_rows
            ),
            "boundary_state_changed_observation_count": len(
                boundary_state_changed_rows
            ),
            "raw_outside_corrected_to_inside_count": sum(
                not row["raw_inside"] and row["refined_inside"]
                for row in boundary_state_changed_rows
            ),
            "raw_inside_corrected_to_outside_count": sum(
                row["raw_inside"] and not row["refined_inside"]
                for row in boundary_state_changed_rows
            ),
            "outside_observation_count_preserved": (
                len(raw_outside_rows) == len(refined_outside_rows)
            ),
            "outside_coordinates_preserved_exactly": all(
                math.isclose(
                    row["raw_x"],
                    row["refined_x"],
                    rel_tol=0.0,
                    abs_tol=0.0,
                )
                and math.isclose(
                    row["raw_y"],
                    row["refined_y"],
                    rel_tol=0.0,
                    abs_tol=0.0,
                )
                for row in raw_outside_rows
            ),
        },
        "missing_observation_audit": gap_audit,
        "review_guidance": [
            (
                "Inspect the recommended correction checkpoints in the "
                "refined synchronized review."
            ),
            (
                "Confirm corrected top-down paths remove isolated "
                "teleports without changing player identities."
            ),
            (
                "Inspect raw-to-refined boundary-state corrections and "
                "confirm isolated false outside samples were removed "
                "without clipping credible physical outside positions."
            ),
            (
                "Confirm the refined motion audit contains no remaining "
                "speed candidates above the reviewed threshold."
            ),
            (
                "Missing player observations remain unfilled and require "
                "a separate explicit gap-review decision."
            ),
        ],
    }


def print_summary(report, output_path, audit_path, report_path):
    trusted = report["trusted_path_audit"]
    motion = report["motion_audit"]
    boundary = report["boundary_audit"]
    missing = report["missing_observation_audit"]
    print("\nPlayer court-trajectory refinement complete.")
    print(f"Validated input rows: {report['validation']['row_count']}")
    print(
        "Corrected existing observations: "
        f"{trusted['corrected_observation_count']} "
        f"({trusted['corrected_fraction']:.1%})"
    )
    print(
        "Motion candidates above threshold: "
        f"{motion['raw']['candidate_count']} raw -> "
        f"{motion['refined']['candidate_count']} refined"
    )
    print(
        "Remaining motion candidates: "
        f"{motion['remaining_candidate_count']}"
    )
    print(
        "Outside observations (raw -> refined): "
        f"{boundary['raw_outside_observation_count']} -> "
        f"{boundary['refined_outside_observation_count']}"
    )
    print(
        "Boundary-state corrections: "
        f"{boundary['boundary_state_changed_observation_count']}"
    )
    print(
        "Missing observations preserved/unfilled: "
        f"{missing['total_missing_observation_count']}"
    )
    print(f"Refined coordinates saved to: {output_path}")
    print(f"Correction audit saved to: {audit_path}")
    print(f"Refinement report saved to: {report_path}")
    print("Status: pending refined trajectory visual review.")


def main():
    args = parse_args()
    review_report = load_json(
        args.review_report, "Coordinate visualization review report"
    )
    (
        rows,
        rows_by_player,
        rows_by_frame,
        original_fields,
    ) = load_coordinate_rows(args.coordinates)
    _, team_counts = validate_identity_contract(rows_by_player)
    validate_boundary_flags(
        rows, args.half_court_length_ft, args.court_width_ft
    )
    review_validation = review_report.get("validation", {})
    review_metadata = review_validation.get("video_metadata", {})
    fps = float(review_metadata.get("fps", -1.0))

    if fps <= 0:
        raise ValueError("Review report does not contain a valid FPS")

    raw_motion = analyze_motion(
        rows_by_player,
        fps,
        args.maximum_speed_ft_sec,
        "raw_x",
        "raw_y",
    )
    fps, frame_count = validate_review_contract(
        review_report,
        rows,
        rows_by_player,
        rows_by_frame,
        raw_motion,
        args.maximum_speed_ft_sec,
    )
    raw_jump_rows = mark_raw_jump_rows(raw_motion)
    trusted_indices_by_player = refine_trajectories(
        rows_by_player,
        fps,
        args.maximum_speed_ft_sec,
        args.maximum_extrapolation_observations,
        args.extrapolation_anchor_count,
        args.half_court_length_ft,
        args.court_width_ft,
        raw_jump_rows,
    )
    validate_refined_boundaries(
        rows, args.half_court_length_ft, args.court_width_ft
    )
    refined_motion = analyze_motion(
        rows_by_player,
        fps,
        args.maximum_speed_ft_sec,
        "refined_x",
        "refined_y",
    )
    gap_audit = build_gap_audit(rows_by_player, frame_count)
    report = build_report(
        args,
        rows,
        rows_by_player,
        team_counts,
        fps,
        frame_count,
        raw_motion,
        refined_motion,
        gap_audit,
        trusted_indices_by_player,
    )
    write_refined_csv(args.output, rows, original_fields)
    write_audit_csv(args.audit, rows)
    write_json_atomic(args.report, report)
    print_summary(report, args.output, args.audit, args.report)


if __name__ == "__main__":
    main()
