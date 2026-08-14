import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

import cv2
import numpy as np


VIDEO_PATH = Path(
    "data/clips/possession_001.mp4"
)

TRACKS_CSV_PATH = Path(
    "data/outputs/tracking/"
    "possession_001_court_filtered_tracks.csv"
)

OUTPUT_DIR = Path(
    "data/outputs/classification"
)

FEATURES_OUTPUT_PATH = (
    OUTPUT_DIR / "possession_001_uniform_features.csv"
)

MONTAGE_OUTPUT_PATH = (
    OUTPUT_DIR / "possession_001_uniform_crops.jpg"
)

SAMPLE_EVERY_N_FRAMES = 5
MIN_TRACK_DETECTIONS = 20

CROP_WIDTH = 160
CROP_HEIGHT = 200
MONTAGE_COLUMNS = 5


# ---------------------------------------------------------
# Load tracking data
# ---------------------------------------------------------

if not TRACKS_CSV_PATH.exists():
    raise FileNotFoundError(
        f"Tracking CSV not found: {TRACKS_CSV_PATH}"
    )

rows_by_frame = defaultdict(list)
rows_by_track = defaultdict(list)

with TRACKS_CSV_PATH.open(
    "r",
    newline="",
    encoding="utf-8",
) as csv_file:
    reader = csv.DictReader(csv_file)

    for row in reader:
        parsed_row = {
            "frame_index": int(row["frame_index"]),
            "track_id": int(row["track_id"]),
            "confidence": float(row["confidence"]),
            "x1": float(row["x1"]),
            "y1": float(row["y1"]),
            "x2": float(row["x2"]),
            "y2": float(row["y2"]),
        }

        rows_by_frame[
            parsed_row["frame_index"]
        ].append(parsed_row)

        rows_by_track[
            parsed_row["track_id"]
        ].append(parsed_row)


eligible_track_ids = {
    track_id
    for track_id, track_rows
    in rows_by_track.items()
    if len(track_rows) >= MIN_TRACK_DETECTIONS
}

print(
    f"Eligible tracks: {len(eligible_track_ids)} "
    f"with at least {MIN_TRACK_DETECTIONS} detections"
)


# ---------------------------------------------------------
# Open video
# ---------------------------------------------------------

cap = cv2.VideoCapture(str(VIDEO_PATH))

if not cap.isOpened():
    raise RuntimeError(f"Could not open video: {VIDEO_PATH}")

frame_count = int(
    cap.get(cv2.CAP_PROP_FRAME_COUNT)
)

video_width = int(
    cap.get(cv2.CAP_PROP_FRAME_WIDTH)
)

video_height = int(
    cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
)


# ---------------------------------------------------------
# Accumulate uniform features
# ---------------------------------------------------------

features_by_track = defaultdict(list)
best_crop_by_track = {}
best_crop_score_by_track = defaultdict(
    lambda: -1.0
)

for frame_index in range(frame_count):
    success, frame = cap.read()

    if not success:
        break

    if frame_index % SAMPLE_EVERY_N_FRAMES != 0:
        continue

    for row in rows_by_frame.get(frame_index, []):
        track_id = row["track_id"]

        if track_id not in eligible_track_ids:
            continue

        x1 = max(0, int(round(row["x1"])))
        y1 = max(0, int(round(row["y1"])))
        x2 = min(
            video_width - 1,
            int(round(row["x2"])),
        )
        y2 = min(
            video_height - 1,
            int(round(row["y2"])),
        )

        box_width = x2 - x1
        box_height = y2 - y1

        if box_width < 10 or box_height < 20:
            continue

        # Central upper-body region. This avoids most of the
        # background, legs, shoes, and head.
        crop_x1 = int(
            x1 + box_width * 0.20
        )
        crop_x2 = int(
            x1 + box_width * 0.80
        )
        crop_y1 = int(
            y1 + box_height * 0.18
        )
        crop_y2 = int(
            y1 + box_height * 0.58
        )

        crop_x1 = max(0, crop_x1)
        crop_y1 = max(0, crop_y1)
        crop_x2 = min(video_width, crop_x2)
        crop_y2 = min(video_height, crop_y2)

        jersey_crop = frame[
            crop_y1:crop_y2,
            crop_x1:crop_x2,
        ]

        if jersey_crop.size == 0:
            continue

        hsv_crop = cv2.cvtColor(
            jersey_crop,
            cv2.COLOR_BGR2HSV,
        )

        gray_crop = cv2.cvtColor(
            jersey_crop,
            cv2.COLOR_BGR2GRAY,
        )

        saturation = hsv_crop[:, :, 1]
        value = hsv_crop[:, :, 2]

        bright_neutral_mask = (
            (value >= 160)
            & (saturation <= 110)
        )

        dark_mask = value <= 90

        bright_fraction = float(
            np.mean(bright_neutral_mask)
        )

        dark_fraction = float(
            np.mean(dark_mask)
        )

        grayscale_std = float(
            np.std(gray_crop)
        )

        mean_saturation = float(
            np.mean(saturation)
        )

        mean_value = float(
            np.mean(value)
        )

        features_by_track[track_id].append(
            {
                "frame_index": frame_index,
                "bright_fraction": bright_fraction,
                "dark_fraction": dark_fraction,
                "grayscale_std": grayscale_std,
                "mean_saturation": mean_saturation,
                "mean_value": mean_value,
            }
        )

        # Prefer a large, confident crop for the montage.
        crop_score = (
            row["confidence"]
            * math.sqrt(box_width * box_height)
        )

        if (
            crop_score
            > best_crop_score_by_track[track_id]
        ):
            best_crop_score_by_track[
                track_id
            ] = crop_score

            best_crop_by_track[
                track_id
            ] = jersey_crop.copy()

cap.release()


# ---------------------------------------------------------
# Aggregate track-level features
# ---------------------------------------------------------

track_feature_rows = []

for track_id in sorted(features_by_track):
    samples = features_by_track[track_id]

    track_feature_rows.append(
        {
            "track_id": track_id,
            "track_detections": len(
                rows_by_track[track_id]
            ),
            "feature_samples": len(samples),
            "median_bright_fraction": median(
                sample["bright_fraction"]
                for sample in samples
            ),
            "median_dark_fraction": median(
                sample["dark_fraction"]
                for sample in samples
            ),
            "median_grayscale_std": median(
                sample["grayscale_std"]
                for sample in samples
            ),
            "median_saturation": median(
                sample["mean_saturation"]
                for sample in samples
            ),
            "median_value": median(
                sample["mean_value"]
                for sample in samples
            ),
            "average_bright_fraction": mean(
                sample["bright_fraction"]
                for sample in samples
            ),
            "average_dark_fraction": mean(
                sample["dark_fraction"]
                for sample in samples
            ),
        }
    )

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

with FEATURES_OUTPUT_PATH.open(
    "w",
    newline="",
    encoding="utf-8",
) as output_file:
    fieldnames = [
        "track_id",
        "track_detections",
        "feature_samples",
        "median_bright_fraction",
        "median_dark_fraction",
        "median_grayscale_std",
        "median_saturation",
        "median_value",
        "average_bright_fraction",
        "average_dark_fraction",
    ]

    writer = csv.DictWriter(
        output_file,
        fieldnames=fieldnames,
    )

    writer.writeheader()
    writer.writerows(track_feature_rows)


# ---------------------------------------------------------
# Build representative jersey-crop montage
# ---------------------------------------------------------

montage_tiles = []

for feature_row in track_feature_rows:
    track_id = feature_row["track_id"]

    crop = best_crop_by_track.get(track_id)

    if crop is None:
        continue

    tile = cv2.resize(
        crop,
        (CROP_WIDTH, CROP_HEIGHT),
        interpolation=cv2.INTER_CUBIC,
    )

    label_height = 42

    labeled_tile = cv2.copyMakeBorder(
        tile,
        label_height,
        0,
        0,
        0,
        cv2.BORDER_CONSTANT,
        value=(0, 0, 0),
    )

    cv2.putText(
        labeled_tile,
        f"ID {track_id}",
        (8, 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.50,
        (255, 255, 255),
        1,
    )

    cv2.putText(
        labeled_tile,
        (
            f"B {feature_row['median_bright_fraction']:.2f} "
            f"D {feature_row['median_dark_fraction']:.2f}"
        ),
        (8, 36),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (255, 255, 255),
        1,
    )

    montage_tiles.append(labeled_tile)

if montage_tiles:
    tile_height = montage_tiles[0].shape[0]
    tile_width = montage_tiles[0].shape[1]

    montage_rows = math.ceil(
        len(montage_tiles) / MONTAGE_COLUMNS
    )

    montage = np.zeros(
        (
            montage_rows * tile_height,
            MONTAGE_COLUMNS * tile_width,
            3,
        ),
        dtype=np.uint8,
    )

    for index, tile in enumerate(montage_tiles):
        row_index = index // MONTAGE_COLUMNS
        column_index = index % MONTAGE_COLUMNS

        y_start = row_index * tile_height
        x_start = column_index * tile_width

        montage[
            y_start:y_start + tile_height,
            x_start:x_start + tile_width,
        ] = tile

    cv2.imwrite(
        str(MONTAGE_OUTPUT_PATH),
        montage,
    )


# ---------------------------------------------------------
# Print summary
# ---------------------------------------------------------

print("\nUniform feature extraction complete.")
print(f"Tracks analyzed: {len(track_feature_rows)}")
print(f"Features saved to: {FEATURES_OUTPUT_PATH}")
print(f"Crop montage saved to: {MONTAGE_OUTPUT_PATH}")