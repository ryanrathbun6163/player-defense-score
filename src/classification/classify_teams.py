import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_MIN_TRACK_DETECTIONS = 35
DEFAULT_MIN_FEATURE_SAMPLES = 5
DEFAULT_MIN_TEXTURE_STD = 35.0
DEFAULT_WHITE_MIN_BRIGHT_FRACTION = 0.55
DEFAULT_WHITE_MAX_DARK_FRACTION = 0.20
DEFAULT_WHITE_MIN_VALUE = 170.0
DEFAULT_DARK_MIN_DARK_FRACTION = 0.22
DEFAULT_DARK_MAX_BRIGHT_FRACTION = 0.50
DEFAULT_DARK_MAX_VALUE = 150.0

TEAM_COLORS = {
    "white": (255, 255, 0),
    "dark": (0, 140, 255),
    "unknown": (160, 160, 160),
}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Classify tracked players as white, dark, or unknown from "
            "aggregate jersey features."
        )
    )
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--tracks", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--court-config", type=Path)
    parser.add_argument("--output-tracks", type=Path, required=True)
    parser.add_argument("--output-video", type=Path, required=True)
    parser.add_argument(
        "--min-track-detections",
        type=int,
        default=DEFAULT_MIN_TRACK_DETECTIONS,
    )
    parser.add_argument(
        "--min-feature-samples",
        type=int,
        default=DEFAULT_MIN_FEATURE_SAMPLES,
    )
    parser.add_argument(
        "--min-texture-std",
        type=float,
        default=DEFAULT_MIN_TEXTURE_STD,
    )
    parser.add_argument(
        "--white-min-bright-fraction",
        type=float,
        default=DEFAULT_WHITE_MIN_BRIGHT_FRACTION,
    )
    parser.add_argument(
        "--white-max-dark-fraction",
        type=float,
        default=DEFAULT_WHITE_MAX_DARK_FRACTION,
    )
    parser.add_argument(
        "--white-min-value",
        type=float,
        default=DEFAULT_WHITE_MIN_VALUE,
    )
    parser.add_argument(
        "--dark-min-dark-fraction",
        type=float,
        default=DEFAULT_DARK_MIN_DARK_FRACTION,
    )
    parser.add_argument(
        "--dark-max-bright-fraction",
        type=float,
        default=DEFAULT_DARK_MAX_BRIGHT_FRACTION,
    )
    parser.add_argument(
        "--dark-max-value",
        type=float,
        default=DEFAULT_DARK_MAX_VALUE,
    )
    args = parser.parse_args(argv)

    if args.min_track_detections < 1 or args.min_feature_samples < 1:
        parser.error("Minimum evidence counts must be positive")

    if args.min_texture_std < 0:
        parser.error("--min-texture-std cannot be negative")

    for field in (
        "white_min_bright_fraction",
        "white_max_dark_fraction",
        "dark_min_dark_fraction",
        "dark_max_bright_fraction",
    ):
        if not 0.0 <= getattr(args, field) <= 1.0:
            parser.error(f"--{field.replace('_', '-')} must be in [0, 1]")

    for field in ("white_min_value", "dark_max_value"):
        if not 0.0 <= getattr(args, field) <= 255.0:
            parser.error(f"--{field.replace('_', '-')} must be in [0, 255]")

    return args


def classify_feature_row(row, args):
    has_enough_evidence = (
        row["track_detections"] >= args.min_track_detections
        and row["feature_samples"] >= args.min_feature_samples
        and row["texture_std"] >= args.min_texture_std
    )

    if not has_enough_evidence:
        return "unknown"

    is_white = (
        row["bright_fraction"] >= args.white_min_bright_fraction
        and row["dark_fraction"] <= args.white_max_dark_fraction
        and row["median_value"] >= args.white_min_value
    )
    is_dark = (
        row["dark_fraction"] >= args.dark_min_dark_fraction
        and row["bright_fraction"] <= args.dark_max_bright_fraction
        and row["median_value"] <= args.dark_max_value
    )

    if is_white:
        return "white"

    if is_dark:
        return "dark"

    return "unknown"


def load_team_labels(path, args):
    if not path.exists():
        raise FileNotFoundError(f"Uniform features not found: {path}")

    required_fields = {
        "track_id",
        "track_detections",
        "feature_samples",
        "median_bright_fraction",
        "median_dark_fraction",
        "median_grayscale_std",
        "median_value",
    }
    team_by_track = {}
    feature_rows_by_track = {}

    with path.open("r", newline="", encoding="utf-8") as feature_file:
        reader = csv.DictReader(feature_file)
        missing_fields = sorted(required_fields - set(reader.fieldnames or []))

        if missing_fields:
            raise ValueError(
                f"Uniform-feature CSV is missing fields: {missing_fields}"
            )

        for row in reader:
            track_id = int(row["track_id"])
            parsed = {
                "track_detections": int(row["track_detections"]),
                "feature_samples": int(row["feature_samples"]),
                "bright_fraction": float(row["median_bright_fraction"]),
                "dark_fraction": float(row["median_dark_fraction"]),
                "texture_std": float(row["median_grayscale_std"]),
                "median_value": float(row["median_value"]),
            }
            team_by_track[track_id] = classify_feature_row(parsed, args)
            feature_rows_by_track[track_id] = parsed

    return team_by_track, feature_rows_by_track


def classify_tracking_rows(path, team_by_track):
    if not path.exists():
        raise FileNotFoundError(f"Tracking CSV not found: {path}")

    rows_by_frame = defaultdict(list)
    track_rows = []

    with path.open("r", newline="", encoding="utf-8") as input_file:
        reader = csv.DictReader(input_file)

        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")

        if "team_label" in reader.fieldnames:
            raise ValueError(f"Tracking CSV is already classified: {path}")

        output_fieldnames = list(reader.fieldnames) + ["team_label"]

        for row in reader:
            track_id = int(row["track_id"])
            frame_index = int(row["frame_index"])
            classified_row = dict(row)
            classified_row["team_label"] = team_by_track.get(
                track_id,
                "unknown",
            )
            track_rows.append(classified_row)
            rows_by_frame[frame_index].append(classified_row)

    if not track_rows:
        raise ValueError(f"Tracking CSV contains no rows: {path}")

    return output_fieldnames, track_rows, dict(rows_by_frame)


def write_classified_tracks(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_court_polygon(path):
    if path is None:
        return None

    import numpy as np

    if not path.exists():
        raise FileNotFoundError(f"Court configuration not found: {path}")

    with path.open("r", encoding="utf-8") as config_file:
        court_config = json.load(config_file)

    polygon = np.array(
        [
            [point["x"], point["y"]]
            for point in court_config["polygon"]
        ],
        dtype=np.int32,
    )

    if len(polygon) < 3:
        raise ValueError("Court polygon must contain at least three points")

    return polygon


def render_classified_video(args, rows_by_frame, court_polygon):
    import cv2
    from tqdm import tqdm

    capture = cv2.VideoCapture(str(args.video))

    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {args.video}")

    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
        capture.release()
        raise ValueError(
            "Invalid source-video metadata: "
            f"fps={fps}, frames={frame_count}, resolution={width}x{height}"
        )

    args.output_video.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(args.output_video),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    if not writer.isOpened():
        capture.release()
        raise RuntimeError(
            f"Could not create classified output video: {args.output_video}"
        )

    try:
        for frame_index in tqdm(
            range(frame_count),
            desc="Rendering team classifications",
        ):
            success, frame = capture.read()

            if not success:
                break

            if court_polygon is not None:
                cv2.polylines(
                    frame,
                    [court_polygon],
                    isClosed=True,
                    color=(0, 255, 255),
                    thickness=2,
                )

            frame_team_counts = Counter()

            for row in rows_by_frame.get(frame_index, []):
                track_id = int(row["track_id"])
                team_label = row["team_label"]
                color = TEAM_COLORS[team_label]
                x1 = int(round(float(row["x1"])))
                y1 = int(round(float(row["y1"])))
                x2 = int(round(float(row["x2"])))
                y2 = int(round(float(row["y2"])))
                floor_x = int(round(float(row["floor_x"])))
                floor_y = int(round(float(row["floor_y"])))
                frame_team_counts[team_label] += 1
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                cv2.putText(
                    frame,
                    f"ID {track_id} {team_label.upper()}",
                    (x1, max(y1 - 8, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    color,
                    2,
                )
                cv2.circle(frame, (floor_x, floor_y), 4, color, -1)

            summary_label = (
                f"White: {frame_team_counts['white']} | "
                f"Dark: {frame_team_counts['dark']} | "
                f"Unknown: {frame_team_counts['unknown']}"
            )
            cv2.rectangle(frame, (15, 15), (520, 58), (0, 0, 0), -1)
            cv2.putText(
                frame,
                summary_label,
                (25, 45),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.70,
                (255, 255, 255),
                2,
            )
            writer.write(frame)
    finally:
        capture.release()
        writer.release()


def print_summary(args, team_by_track):
    track_label_counts = Counter(team_by_track.values())
    print("\nTeam classification complete.")
    print(f"White tracks: {track_label_counts['white']}")
    print(f"Dark tracks: {track_label_counts['dark']}")
    print(f"Unknown tracks: {track_label_counts['unknown']}")

    for team_label in ("white", "dark", "unknown"):
        track_ids = sorted(
            track_id
            for track_id, label in team_by_track.items()
            if label == team_label
        )
        print(f"{team_label.capitalize()} IDs: {track_ids}")

    print(f"Classified CSV saved to: {args.output_tracks}")
    print(f"Classified video saved to: {args.output_video}")


def main(argv=None):
    args = parse_args(argv)
    team_by_track, _feature_rows_by_track = load_team_labels(
        args.features,
        args,
    )
    fieldnames, track_rows, rows_by_frame = classify_tracking_rows(
        args.tracks,
        team_by_track,
    )
    write_classified_tracks(args.output_tracks, fieldnames, track_rows)
    court_polygon = load_court_polygon(args.court_config)
    render_classified_video(args, rows_by_frame, court_polygon)
    print_summary(args, team_by_track)


if __name__ == "__main__":
    main()
