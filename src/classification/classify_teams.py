import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm


VIDEO_PATH = Path(
    "data/clips/possession_001.mp4"
)

TRACKS_CSV_PATH = Path(
    "data/outputs/tracking/"
    "possession_001_court_filtered_tracks.csv"
)

FEATURES_CSV_PATH = Path(
    "data/outputs/classification/"
    "possession_001_uniform_features.csv"
)

COURT_CONFIG_PATH = Path(
    "configs/possession_001_court.json"
)

OUTPUT_DIR = Path(
    "data/outputs/classification"
)

CLASSIFIED_CSV_PATH = (
    OUTPUT_DIR
    / "possession_001_team_classified_tracks.csv"
)

CLASSIFIED_VIDEO_PATH = (
    OUTPUT_DIR
    / "possession_001_team_classified.mp4"
)


# ---------------------------------------------------------
# Classification thresholds
# ---------------------------------------------------------

MIN_TRACK_DETECTIONS = 35
MIN_FEATURE_SAMPLES = 5
MIN_TEXTURE_STD = 35.0

WHITE_MIN_BRIGHT_FRACTION = 0.55
WHITE_MAX_DARK_FRACTION = 0.20
WHITE_MIN_VALUE = 170.0

DARK_MIN_DARK_FRACTION = 0.22
DARK_MAX_BRIGHT_FRACTION = 0.50
DARK_MAX_VALUE = 150.0


# OpenCV uses BGR colors.
TEAM_COLORS = {
    "white": (255, 255, 0),
    "dark": (0, 140, 255),
    "unknown": (160, 160, 160),
}


# ---------------------------------------------------------
# Classify each track from aggregate uniform features
# ---------------------------------------------------------

if not FEATURES_CSV_PATH.exists():
    raise FileNotFoundError(
        f"Uniform features not found: {FEATURES_CSV_PATH}"
    )

team_by_track = {}
feature_rows_by_track = {}

with FEATURES_CSV_PATH.open(
    "r",
    newline="",
    encoding="utf-8",
) as feature_file:
    reader = csv.DictReader(feature_file)

    for row in reader:
        track_id = int(row["track_id"])
        track_detections = int(
            row["track_detections"]
        )
        feature_samples = int(
            row["feature_samples"]
        )

        bright_fraction = float(
            row["median_bright_fraction"]
        )
        dark_fraction = float(
            row["median_dark_fraction"]
        )
        texture_std = float(
            row["median_grayscale_std"]
        )
        median_value = float(
            row["median_value"]
        )

        team_label = "unknown"

        has_enough_evidence = (
            track_detections
            >= MIN_TRACK_DETECTIONS
            and feature_samples
            >= MIN_FEATURE_SAMPLES
            and texture_std
            >= MIN_TEXTURE_STD
        )

        if has_enough_evidence:
            is_white = (
                bright_fraction
                >= WHITE_MIN_BRIGHT_FRACTION
                and dark_fraction
                <= WHITE_MAX_DARK_FRACTION
                and median_value
                >= WHITE_MIN_VALUE
            )

            is_dark = (
                dark_fraction
                >= DARK_MIN_DARK_FRACTION
                and bright_fraction
                <= DARK_MAX_BRIGHT_FRACTION
                and median_value
                <= DARK_MAX_VALUE
            )

            if is_white:
                team_label = "white"

            elif is_dark:
                team_label = "dark"

        team_by_track[track_id] = team_label

        feature_rows_by_track[track_id] = {
            "track_detections": track_detections,
            "feature_samples": feature_samples,
            "bright_fraction": bright_fraction,
            "dark_fraction": dark_fraction,
            "texture_std": texture_std,
            "median_value": median_value,
        }


# ---------------------------------------------------------
# Load tracking rows and write classified CSV
# ---------------------------------------------------------

if not TRACKS_CSV_PATH.exists():
    raise FileNotFoundError(
        f"Tracking CSV not found: {TRACKS_CSV_PATH}"
    )

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

rows_by_frame = defaultdict(list)
track_rows = []

with TRACKS_CSV_PATH.open(
    "r",
    newline="",
    encoding="utf-8",
) as input_file:
    reader = csv.DictReader(input_file)

    if reader.fieldnames is None:
        raise ValueError(
            f"CSV has no header: {TRACKS_CSV_PATH}"
        )

    output_fieldnames = (
        list(reader.fieldnames)
        + ["team_label"]
    )

    for row in reader:
        track_id = int(row["track_id"])
        frame_index = int(row["frame_index"])

        classified_row = dict(row)
        classified_row["team_label"] = (
            team_by_track.get(
                track_id,
                "unknown",
            )
        )

        track_rows.append(classified_row)
        rows_by_frame[frame_index].append(
            classified_row
        )

with CLASSIFIED_CSV_PATH.open(
    "w",
    newline="",
    encoding="utf-8",
) as output_file:
    writer = csv.DictWriter(
        output_file,
        fieldnames=output_fieldnames,
    )

    writer.writeheader()
    writer.writerows(track_rows)


# ---------------------------------------------------------
# Load court polygon for visualization
# ---------------------------------------------------------

court_polygon = None

if COURT_CONFIG_PATH.exists():
    with COURT_CONFIG_PATH.open(
        "r",
        encoding="utf-8",
    ) as config_file:
        court_config = json.load(config_file)

    court_polygon = np.array(
        [
            [point["x"], point["y"]]
            for point in court_config["polygon"]
        ],
        dtype=np.int32,
    )


# ---------------------------------------------------------
# Open video and create classified visualization
# ---------------------------------------------------------

cap = cv2.VideoCapture(str(VIDEO_PATH))

if not cap.isOpened():
    raise RuntimeError(f"Could not open video: {VIDEO_PATH}")

fps = cap.get(cv2.CAP_PROP_FPS)
frame_count = int(
    cap.get(cv2.CAP_PROP_FRAME_COUNT)
)
width = int(
    cap.get(cv2.CAP_PROP_FRAME_WIDTH)
)
height = int(
    cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
)

fourcc = cv2.VideoWriter_fourcc(*"mp4v")

writer = cv2.VideoWriter(
    str(CLASSIFIED_VIDEO_PATH),
    fourcc,
    fps,
    (width, height),
)

if not writer.isOpened():
    cap.release()
    raise RuntimeError(
        "Could not create classified output video"
    )


try:
    for frame_index in tqdm(
        range(frame_count),
        desc="Rendering team classifications",
    ):
        success, frame = cap.read()

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

        for row in rows_by_frame.get(
            frame_index,
            [],
        ):
            track_id = int(row["track_id"])
            team_label = row["team_label"]
            color = TEAM_COLORS[team_label]

            x1 = int(round(float(row["x1"])))
            y1 = int(round(float(row["y1"])))
            x2 = int(round(float(row["x2"])))
            y2 = int(round(float(row["y2"])))

            floor_x = int(
                round(float(row["floor_x"]))
            )
            floor_y = int(
                round(float(row["floor_y"]))
            )

            frame_team_counts[team_label] += 1

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                color,
                3,
            )

            label = (
                f"ID {track_id} "
                f"{team_label.upper()}"
            )

            cv2.putText(
                frame,
                label,
                (
                    x1,
                    max(y1 - 8, 20),
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
            )

            cv2.circle(
                frame,
                (floor_x, floor_y),
                4,
                color,
                -1,
            )

        summary_label = (
            f"White: {frame_team_counts['white']} | "
            f"Dark: {frame_team_counts['dark']} | "
            f"Unknown: {frame_team_counts['unknown']}"
        )

        cv2.rectangle(
            frame,
            (15, 15),
            (520, 58),
            (0, 0, 0),
            -1,
        )

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
    cap.release()
    writer.release()


# ---------------------------------------------------------
# Print classification summary
# ---------------------------------------------------------

track_label_counts = Counter(
    team_by_track.values()
)

print("\nTeam classification complete.")
print(
    f"White tracks: "
    f"{track_label_counts['white']}"
)
print(
    f"Dark tracks: "
    f"{track_label_counts['dark']}"
)
print(
    f"Unknown tracks: "
    f"{track_label_counts['unknown']}"
)

for team_label in (
    "white",
    "dark",
    "unknown",
):
    track_ids = sorted(
        track_id
        for track_id, label
        in team_by_track.items()
        if label == team_label
    )

    print(
        f"{team_label.capitalize()} IDs: "
        f"{track_ids}"
    )

print(
    f"Classified CSV saved to: "
    f"{CLASSIFIED_CSV_PATH}"
)
print(
    f"Classified video saved to: "
    f"{CLASSIFIED_VIDEO_PATH}"
)