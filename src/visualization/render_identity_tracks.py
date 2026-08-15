import argparse
import csv
import json
from collections import Counter, defaultdict, deque
from pathlib import Path

try:
    import cv2
except ModuleNotFoundError:
    cv2 = None


DEFAULT_VIDEO_PATH = Path("data/clips/possession_001.mp4")
DEFAULT_TRACKS_PATH = Path(
    "data/outputs/identity/possession_001_reconciled_tracks.csv"
)
DEFAULT_OUTPUT_PATH = Path(
    "data/outputs/visualization/"
    "possession_001_identity_review.mp4"
)
DEFAULT_REPORT_PATH = Path(
    "data/outputs/visualization/"
    "possession_001_identity_review.json"
)

DEFAULT_REVIEW_BOUNDARIES = [270, 312, 452]
EXPECTED_PLAYER_COUNT = 10
EXPECTED_TEAM_COUNTS = {"white": 5, "dark": 5}

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

TEXT_COLOR = (255, 255, 255)
PANEL_COLOR = (15, 15, 15)
BOUNDARY_COLOR = (0, 235, 255)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Render the final reconciled player identities onto "
            "the source possession video."
        )
    )
    parser.add_argument(
        "--video",
        type=Path,
        default=DEFAULT_VIDEO_PATH,
        help="Source possession video.",
    )
    parser.add_argument(
        "--tracks",
        type=Path,
        default=DEFAULT_TRACKS_PATH,
        help="Final reconciled identity CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Annotated MP4 output path.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="JSON validation report path.",
    )
    parser.add_argument(
        "--trail-length",
        type=int,
        default=12,
        help="Number of recent floor points to draw per player.",
    )
    parser.add_argument(
        "--boundary-window",
        type=int,
        default=3,
        help=(
            "Frames before and after each reviewed boundary in "
            "which to display the boundary banner."
        ),
    )
    parser.add_argument(
        "--hide-raw-track-ids",
        action="store_true",
        help="Hide raw tracker IDs from player labels.",
    )
    parser.add_argument(
        "--hide-legend",
        action="store_true",
        help="Hide the ten-player color legend.",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help=(
            "Validate the reconciled CSV and write the JSON "
            "report without opening or rendering the video."
        ),
    )
    args = parser.parse_args()

    if args.trail_length < 0:
        parser.error("--trail-length cannot be negative")

    if args.boundary_window < 0:
        parser.error("--boundary-window cannot be negative")

    return args


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
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"Invalid number in {field_name} at CSV row "
            f"{row_number}: {value!r}"
        ) from error


def player_sort_key(player_id):
    team, _, suffix = player_id.partition("_p")

    try:
        player_number = int(suffix)
    except ValueError:
        player_number = 10_000

    team_order = {"white": 0, "dark": 1}
    return (
        team_order.get(team, 2),
        player_number,
        player_id,
    )


def load_reconciled_rows(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Reconciled identity tracks not found: {path}"
        )

    required_fields = {
        "frame_index",
        "track_id",
        "confidence",
        "x1",
        "y1",
        "x2",
        "y2",
        "floor_x",
        "floor_y",
        "segment_id",
        "player_id",
        "reconciled_team",
        "identity_status",
        "duplicate_detection_count",
        "source_track_ids",
        "source_segment_ids",
    }
    rows_by_frame = defaultdict(list)
    team_by_player = {}
    row_count = 0

    with path.open("r", newline="", encoding="utf-8") as input_file:
        reader = csv.DictReader(input_file)
        field_names = set(reader.fieldnames or [])
        missing_fields = sorted(required_fields - field_names)

        if missing_fields:
            raise ValueError(
                "Reconciled CSV is missing required fields: "
                f"{missing_fields}"
            )

        for row_number, raw_row in enumerate(reader, 2):
            row = dict(raw_row)
            row["frame_index"] = parse_int(
                raw_row["frame_index"],
                "frame_index",
                row_number,
            )
            row["track_id"] = parse_int(
                raw_row["track_id"],
                "track_id",
                row_number,
            )
            row["duplicate_detection_count"] = parse_int(
                raw_row["duplicate_detection_count"],
                "duplicate_detection_count",
                row_number,
            )

            for field_name in (
                "confidence",
                "x1",
                "y1",
                "x2",
                "y2",
                "floor_x",
                "floor_y",
            ):
                row[field_name] = parse_float(
                    raw_row[field_name],
                    field_name,
                    row_number,
                )

            player_id = row["player_id"].strip()
            team = row["reconciled_team"].strip()
            identity_status = row["identity_status"].strip()

            if not player_id:
                raise ValueError(
                    f"Blank player_id at CSV row {row_number}"
                )

            if team not in EXPECTED_TEAM_COUNTS:
                raise ValueError(
                    f"Unexpected reconciled team at CSV row "
                    f"{row_number}: {team!r}"
                )

            if identity_status != "active":
                raise ValueError(
                    "The reconciled CSV must contain active rows "
                    f"only; row {row_number} has status "
                    f"{identity_status!r}."
                )

            previous_team = team_by_player.setdefault(
                player_id,
                team,
            )

            if previous_team != team:
                raise ValueError(
                    f"Identity {player_id} changes teams: "
                    f"{previous_team} -> {team}"
                )

            if row["frame_index"] < 0:
                raise ValueError(
                    f"Negative frame index at CSV row {row_number}"
                )

            if row["x2"] <= row["x1"] or row["y2"] <= row["y1"]:
                raise ValueError(
                    f"Invalid bounding box at CSV row {row_number}"
                )

            rows_by_frame[row["frame_index"]].append(row)
            row_count += 1

    if not rows_by_frame:
        raise ValueError(f"No reconciled identity rows found in {path}")

    for frame_index, rows in rows_by_frame.items():
        player_ids = [row["player_id"] for row in rows]

        if len(player_ids) != len(set(player_ids)):
            duplicate_ids = sorted(
                player_id
                for player_id, count in Counter(player_ids).items()
                if count > 1
            )
            raise ValueError(
                "Reconciled CSV contains duplicate player rows "
                f"in frame {frame_index}: {duplicate_ids}"
            )

        rows.sort(key=lambda row: player_sort_key(row["player_id"]))

    return dict(rows_by_frame), team_by_player, row_count


def build_input_summary(rows_by_frame, team_by_player, row_count):
    player_ids = sorted(team_by_player, key=player_sort_key)
    identities_by_team = Counter(team_by_player.values())
    frame_identity_counts = Counter(
        len(rows) for rows in rows_by_frame.values()
    )
    ten_player_frames = [
        frame_index
        for frame_index, rows in rows_by_frame.items()
        if len(rows) == EXPECTED_PLAYER_COUNT
    ]
    imbalanced_ten_player_frames = []

    for frame_index in ten_player_frames:
        team_counts = Counter(
            row["reconciled_team"]
            for row in rows_by_frame[frame_index]
        )

        if dict(team_counts) != EXPECTED_TEAM_COUNTS:
            imbalanced_ten_player_frames.append(frame_index)

    summary = {
        "row_count": row_count,
        "first_tracked_frame": min(rows_by_frame),
        "last_tracked_frame": max(rows_by_frame),
        "tracked_frame_count": len(rows_by_frame),
        "identity_count": len(player_ids),
        "player_ids": player_ids,
        "identity_counts_by_team": {
            team: identities_by_team.get(team, 0)
            for team in EXPECTED_TEAM_COUNTS
        },
        "frame_identity_count_distribution": {
            str(count): frame_identity_counts[count]
            for count in sorted(frame_identity_counts)
        },
        "maximum_identities_in_one_frame": max(
            frame_identity_counts
        ),
        "ten_player_frame_count": len(ten_player_frames),
        "imbalanced_ten_player_frame_count": len(
            imbalanced_ten_player_frames
        ),
        "imbalanced_ten_player_frames": (
            imbalanced_ten_player_frames
        ),
    }
    return summary


def validate_input_summary(summary):
    if summary["identity_count"] != EXPECTED_PLAYER_COUNT:
        raise ValueError(
            "Expected exactly ten active identities, but found "
            f"{summary['identity_count']}: "
            f"{summary['player_ids']}"
        )

    if summary["identity_counts_by_team"] != EXPECTED_TEAM_COUNTS:
        raise ValueError(
            "Expected five white and five dark identities, but "
            f"found {summary['identity_counts_by_team']}"
        )

    if (
        summary["maximum_identities_in_one_frame"]
        > EXPECTED_PLAYER_COUNT
    ):
        raise ValueError(
            "At least one frame contains more than ten active "
            "identities."
        )

    if summary["imbalanced_ten_player_frame_count"]:
        raise ValueError(
            "At least one ten-player frame does not contain a "
            "five-versus-five team split."
        )


def build_identity_colors(team_by_player):
    colors = {}

    for team, palette in (
        ("white", WHITE_PALETTE),
        ("dark", DARK_PALETTE),
    ):
        player_ids = sorted(
            (
                player_id
                for player_id, player_team in team_by_player.items()
                if player_team == team
            ),
            key=player_sort_key,
        )

        if len(player_ids) > len(palette):
            raise ValueError(
                f"Not enough colors for {team} identities: "
                f"{len(player_ids)}"
            )

        for player_id, color in zip(player_ids, palette):
            colors[player_id] = color

    return colors


def blend_panel(frame, first_point, second_point, opacity=0.72):
    overlay = frame.copy()
    cv2.rectangle(
        overlay,
        first_point,
        second_point,
        PANEL_COLOR,
        -1,
    )
    cv2.addWeighted(
        overlay,
        opacity,
        frame,
        1.0 - opacity,
        0,
        frame,
    )


def draw_text(frame, text, origin, color=TEXT_COLOR, scale=0.62):
    cv2.putText(
        frame,
        text,
        origin,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        2,
        cv2.LINE_AA,
    )


def display_source_tracks(row):
    source_track_ids = [
        item.strip()
        for item in row["source_track_ids"].split(";")
        if item.strip()
    ]

    if not source_track_ids:
        return f"T{row['track_id']}"

    return "/".join(f"T{track_id}" for track_id in source_track_ids)


def draw_player_box(frame, row, color, show_raw_track_ids):
    x1 = max(0, int(round(row["x1"])))
    y1 = max(0, int(round(row["y1"])))
    x2 = min(frame.shape[1] - 1, int(round(row["x2"])))
    y2 = min(frame.shape[0] - 1, int(round(row["y2"])))
    floor_point = (
        min(frame.shape[1] - 1, max(0, int(round(row["floor_x"])))),
        min(frame.shape[0] - 1, max(0, int(round(row["floor_y"])))),
    )
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
    cv2.circle(frame, floor_point, 6, color, -1, cv2.LINE_AA)
    cv2.circle(frame, floor_point, 8, (0, 0, 0), 2, cv2.LINE_AA)

    primary_label = row["player_id"]

    if show_raw_track_ids:
        primary_label += f" | raw {display_source_tracks(row)}"

    secondary_label = (
        f"{row['segment_id']} | conf {row['confidence']:.2f}"
    )

    if row["duplicate_detection_count"] > 1:
        secondary_label += (
            f" | merged {row['duplicate_detection_count']} boxes"
        )

    font = cv2.FONT_HERSHEY_SIMPLEX
    primary_size = cv2.getTextSize(
        primary_label,
        font,
        0.55,
        2,
    )[0]
    secondary_size = cv2.getTextSize(
        secondary_label,
        font,
        0.43,
        1,
    )[0]
    panel_width = max(primary_size[0], secondary_size[0]) + 14
    panel_height = 47
    panel_x = min(
        max(0, x1),
        max(0, frame.shape[1] - panel_width - 1),
    )
    panel_y = y1 - panel_height - 3

    if panel_y < 0:
        panel_y = min(frame.shape[0] - panel_height - 1, y1 + 3)

    blend_panel(
        frame,
        (panel_x, panel_y),
        (panel_x + panel_width, panel_y + panel_height),
        opacity=0.78,
    )
    cv2.rectangle(
        frame,
        (panel_x, panel_y),
        (panel_x + 5, panel_y + panel_height),
        color,
        -1,
    )
    cv2.putText(
        frame,
        primary_label,
        (panel_x + 10, panel_y + 19),
        font,
        0.55,
        TEXT_COLOR,
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        secondary_label,
        (panel_x + 10, panel_y + 39),
        font,
        0.43,
        (220, 220, 220),
        1,
        cv2.LINE_AA,
    )
    return floor_point


def draw_trail(frame, points, color):
    if len(points) < 2:
        return

    point_list = list(points)

    for index, (first, second) in enumerate(
        zip(point_list, point_list[1:]),
        1,
    ):
        thickness = max(1, int(4 * index / len(point_list)))
        cv2.line(
            frame,
            first,
            second,
            color,
            thickness,
            cv2.LINE_AA,
        )


def draw_status_panel(frame, frame_index, fps, rows):
    team_counts = Counter(row["reconciled_team"] for row in rows)
    player_count = len(rows)
    status_color = (
        (80, 230, 80)
        if player_count == EXPECTED_PLAYER_COUNT
        else BOUNDARY_COLOR
    )
    blend_panel(frame, (15, 15), (715, 102))
    draw_text(
        frame,
        (
            f"Frame {frame_index} | {frame_index / fps:.2f}s | "
            "FINAL RECONCILED IDENTITIES"
        ),
        (28, 45),
        scale=0.65,
    )
    draw_text(
        frame,
        (
            f"Players {player_count}/10 | "
            f"white {team_counts.get('white', 0)}/5 | "
            f"dark {team_counts.get('dark', 0)}/5"
        ),
        (28, 78),
        color=status_color,
        scale=0.68,
    )


def draw_identity_legend(frame, colors, team_by_player):
    player_ids = sorted(colors, key=player_sort_key)
    panel_width = 245
    row_height = 25
    panel_height = 38 + len(player_ids) * row_height
    x1 = frame.shape[1] - panel_width - 15
    y1 = 15
    blend_panel(
        frame,
        (x1, y1),
        (frame.shape[1] - 15, y1 + panel_height),
    )
    draw_text(
        frame,
        "IDENTITY COLORS",
        (x1 + 15, y1 + 25),
        scale=0.55,
    )

    for index, player_id in enumerate(player_ids):
        row_y = y1 + 43 + index * row_height
        color = colors[player_id]
        cv2.rectangle(
            frame,
            (x1 + 15, row_y - 12),
            (x1 + 31, row_y + 4),
            color,
            -1,
        )
        cv2.rectangle(
            frame,
            (x1 + 15, row_y - 12),
            (x1 + 31, row_y + 4),
            (0, 0, 0),
            1,
        )
        draw_text(
            frame,
            f"{player_id}  [{team_by_player[player_id]}]",
            (x1 + 40, row_y + 2),
            scale=0.44,
        )


def nearest_review_boundary(frame_index, boundaries, window):
    matches = [
        boundary
        for boundary in boundaries
        if abs(frame_index - boundary) <= window
        or abs(frame_index - (boundary + 1)) <= window
    ]

    if not matches:
        return None

    return min(matches, key=lambda boundary: abs(frame_index - boundary))


def draw_boundary_banner(frame, frame_index, boundaries, window):
    boundary = nearest_review_boundary(
        frame_index,
        boundaries,
        window,
    )

    if boundary is None:
        return

    text = (
        f"REVIEWED ID SWITCH: frame {boundary} -> {boundary + 1}"
    )
    text_size = cv2.getTextSize(
        text,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        2,
    )[0]
    panel_width = text_size[0] + 32
    x1 = max(15, (frame.shape[1] - panel_width) // 2)
    y1 = 116
    blend_panel(
        frame,
        (x1, y1),
        (x1 + panel_width, y1 + 48),
        opacity=0.82,
    )
    cv2.rectangle(
        frame,
        (x1, y1),
        (x1 + panel_width, y1 + 48),
        BOUNDARY_COLOR,
        2,
    )
    draw_text(
        frame,
        text,
        (x1 + 16, y1 + 32),
        color=BOUNDARY_COLOR,
        scale=0.72,
    )


def annotate_frame(
    frame,
    frame_index,
    fps,
    rows,
    colors,
    team_by_player,
    trails,
    trail_length,
    boundaries,
    boundary_window,
    show_raw_track_ids,
    show_legend,
):
    annotated = frame.copy()
    current_points = {}

    for row in rows:
        player_id = row["player_id"]
        current_points[player_id] = (
            int(round(row["floor_x"])),
            int(round(row["floor_y"])),
        )

    if trail_length > 0:
        for player_id, floor_point in current_points.items():
            trails[player_id].append(floor_point)
            draw_trail(
                annotated,
                trails[player_id],
                colors[player_id],
            )

    for row in rows:
        draw_player_box(
            annotated,
            row,
            colors[row["player_id"]],
            show_raw_track_ids,
        )

    draw_status_panel(annotated, frame_index, fps, rows)
    draw_boundary_banner(
        annotated,
        frame_index,
        boundaries,
        boundary_window,
    )

    if show_legend:
        draw_identity_legend(
            annotated,
            colors,
            team_by_player,
        )

    return annotated


def open_video(path):
    if not path.exists():
        raise FileNotFoundError(f"Source video not found: {path}")

    capture = cv2.VideoCapture(str(path))

    if not capture.isOpened():
        raise RuntimeError(f"Could not open source video: {path}")

    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
        capture.release()
        raise ValueError(
            "Source video has invalid metadata: "
            f"fps={fps}, frames={frame_count}, "
            f"resolution={width}x{height}"
        )

    return capture, {
        "fps": fps,
        "frame_count": frame_count,
        "width": width,
        "height": height,
    }


def render_video(
    video_path,
    output_path,
    rows_by_frame,
    team_by_player,
    trail_length,
    boundaries,
    boundary_window,
    show_raw_track_ids,
    show_legend,
):
    capture, metadata = open_video(video_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        metadata["fps"],
        (metadata["width"], metadata["height"]),
    )

    if not writer.isOpened():
        capture.release()
        raise RuntimeError(
            f"Could not create annotated video: {output_path}"
        )

    colors = build_identity_colors(team_by_player)
    trails = defaultdict(lambda: deque(maxlen=max(1, trail_length)))
    last_seen_frame = {}
    processed_frames = 0

    try:
        for frame_index in range(metadata["frame_count"]):
            success, frame = capture.read()

            if not success:
                break

            rows = rows_by_frame.get(frame_index, [])

            for row in rows:
                player_id = row["player_id"]
                previous_frame = last_seen_frame.get(player_id)

                if (
                    previous_frame is not None
                    and frame_index - previous_frame > 1
                ):
                    trails[player_id].clear()

                last_seen_frame[player_id] = frame_index

            annotated = annotate_frame(
                frame,
                frame_index,
                metadata["fps"],
                rows,
                colors,
                team_by_player,
                trails,
                trail_length,
                boundaries,
                boundary_window,
                show_raw_track_ids,
                show_legend,
            )
            writer.write(annotated)
            processed_frames += 1

            if processed_frames % 100 == 0:
                print(
                    f"  Rendered {processed_frames}/"
                    f"{metadata['frame_count']} frames"
                )
    finally:
        capture.release()
        writer.release()

    if processed_frames == 0:
        raise RuntimeError("No video frames were rendered")

    if max(rows_by_frame) >= processed_frames:
        raise ValueError(
            "The reconciled CSV contains a frame outside the "
            "decoded source video: "
            f"CSV max={max(rows_by_frame)}, "
            f"decoded frames={processed_frames}"
        )

    metadata["processed_frame_count"] = processed_frames
    metadata["output_size_bytes"] = output_path.stat().st_size
    return metadata


def build_report(args, input_summary, render_metadata):
    return {
        "source_video": str(args.video),
        "reconciled_tracks": str(args.tracks),
        "annotated_video": (
            None if args.report_only else str(args.output)
        ),
        "settings": {
            "expected_player_count": EXPECTED_PLAYER_COUNT,
            "expected_team_counts": EXPECTED_TEAM_COUNTS,
            "review_boundaries": DEFAULT_REVIEW_BOUNDARIES,
            "boundary_window": args.boundary_window,
            "trail_length": args.trail_length,
            "show_raw_track_ids": not args.hide_raw_track_ids,
            "show_legend": not args.hide_legend,
        },
        "validation": input_summary,
        "render": {
            "rendered": not args.report_only,
            "video_metadata": render_metadata,
        },
        "interpretation": {
            "player_id": (
                "The final stable identity used by downstream "
                "court and matchup analysis."
            ),
            "raw_track_id": (
                "The original ByteTrack container. It may change "
                "while player_id remains stable."
            ),
            "segment_id": (
                "The time-bounded portion of a raw track used by "
                "the identity graph."
            ),
            "missing_players": (
                "Frames below ten represent missing detections, "
                "not additional unresolved identities."
            ),
        },
    }


def print_summary(input_summary, report_path, output_path, report_only):
    print("\nIdentity visualization validation complete.")
    print(f"Reconciled rows: {input_summary['row_count']}")
    print(f"Final identities: {input_summary['identity_count']}")
    print(
        "Identities by team: "
        f"{input_summary['identity_counts_by_team']}"
    )
    print(
        "Frame identity-count distribution: "
        f"{input_summary['frame_identity_count_distribution']}"
    )
    print(
        "Imbalanced ten-player frames: "
        f"{input_summary['imbalanced_ten_player_frame_count']}"
    )

    if report_only:
        print("Video rendering skipped because --report-only was supplied.")
    else:
        print(f"Annotated video saved to: {output_path}")

    print(f"Validation report saved to: {report_path}")


def main():
    args = parse_args()

    if not args.report_only and cv2 is None:
        raise ModuleNotFoundError(
            "OpenCV is required to render the identity video. "
            "Install opencv-python or run with --report-only."
        )

    rows_by_frame, team_by_player, row_count = (
        load_reconciled_rows(args.tracks)
    )
    input_summary = build_input_summary(
        rows_by_frame,
        team_by_player,
        row_count,
    )
    validate_input_summary(input_summary)
    render_metadata = None

    if not args.report_only:
        print("Rendering final reconciled identities...")
        render_metadata = render_video(
            args.video,
            args.output,
            rows_by_frame,
            team_by_player,
            args.trail_length,
            DEFAULT_REVIEW_BOUNDARIES,
            args.boundary_window,
            not args.hide_raw_track_ids,
            not args.hide_legend,
        )

    report = build_report(
        args,
        input_summary,
        render_metadata,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)

    with args.report.open("w", encoding="utf-8") as output_file:
        json.dump(report, output_file, indent=2)
        output_file.write("\n")

    print_summary(
        input_summary,
        args.report,
        args.output,
        args.report_only,
    )


if __name__ == "__main__":
    main()
