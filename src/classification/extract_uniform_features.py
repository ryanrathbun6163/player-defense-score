import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median


DEFAULT_SAMPLE_EVERY_N_FRAMES = 5
DEFAULT_MIN_TRACK_DETECTIONS = 20
DEFAULT_MIN_BOX_WIDTH = 10
DEFAULT_MIN_BOX_HEIGHT = 20
DEFAULT_BRIGHT_VALUE_THRESHOLD = 160
DEFAULT_BRIGHT_SATURATION_MAX = 110
DEFAULT_DARK_VALUE_THRESHOLD = 90
DEFAULT_CROP_WIDTH = 160
DEFAULT_CROP_HEIGHT = 200
DEFAULT_MONTAGE_COLUMNS = 5


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Extract aggregate upper-body jersey features from tracked "
            "players."
        )
    )
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--tracks", type=Path, required=True)
    parser.add_argument("--output-features", type=Path, required=True)
    parser.add_argument("--output-montage", type=Path, required=True)
    parser.add_argument(
        "--sample-every-n-frames",
        type=int,
        default=DEFAULT_SAMPLE_EVERY_N_FRAMES,
    )
    parser.add_argument(
        "--min-track-detections",
        type=int,
        default=DEFAULT_MIN_TRACK_DETECTIONS,
    )
    parser.add_argument(
        "--min-box-width",
        type=int,
        default=DEFAULT_MIN_BOX_WIDTH,
    )
    parser.add_argument(
        "--min-box-height",
        type=int,
        default=DEFAULT_MIN_BOX_HEIGHT,
    )
    parser.add_argument(
        "--bright-value-threshold",
        type=int,
        default=DEFAULT_BRIGHT_VALUE_THRESHOLD,
    )
    parser.add_argument(
        "--bright-saturation-max",
        type=int,
        default=DEFAULT_BRIGHT_SATURATION_MAX,
    )
    parser.add_argument(
        "--dark-value-threshold",
        type=int,
        default=DEFAULT_DARK_VALUE_THRESHOLD,
    )
    parser.add_argument(
        "--crop-width",
        type=int,
        default=DEFAULT_CROP_WIDTH,
    )
    parser.add_argument(
        "--crop-height",
        type=int,
        default=DEFAULT_CROP_HEIGHT,
    )
    parser.add_argument(
        "--montage-columns",
        type=int,
        default=DEFAULT_MONTAGE_COLUMNS,
    )
    args = parser.parse_args(argv)

    for field in (
        "sample_every_n_frames",
        "min_track_detections",
        "min_box_width",
        "min_box_height",
        "crop_width",
        "crop_height",
        "montage_columns",
    ):
        if getattr(args, field) < 1:
            parser.error(f"--{field.replace('_', '-')} must be positive")

    for field in (
        "bright_value_threshold",
        "bright_saturation_max",
        "dark_value_threshold",
    ):
        if not 0 <= getattr(args, field) <= 255:
            parser.error(f"--{field.replace('_', '-')} must be in [0, 255]")

    return args


def load_tracking_rows(path):
    if not path.exists():
        raise FileNotFoundError(f"Tracking CSV not found: {path}")

    rows_by_frame = defaultdict(list)
    rows_by_track = defaultdict(list)
    required_fields = {
        "frame_index",
        "track_id",
        "confidence",
        "x1",
        "y1",
        "x2",
        "y2",
    }

    with path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        missing_fields = sorted(required_fields - set(reader.fieldnames or []))

        if missing_fields:
            raise ValueError(
                f"Tracking CSV is missing required fields: {missing_fields}"
            )

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
            rows_by_frame[parsed_row["frame_index"]].append(parsed_row)
            rows_by_track[parsed_row["track_id"]].append(parsed_row)

    if not rows_by_track:
        raise ValueError(f"Tracking CSV contains no rows: {path}")

    return dict(rows_by_frame), dict(rows_by_track)


def collect_features(args, rows_by_frame, rows_by_track):
    import cv2
    import numpy as np

    eligible_track_ids = {
        track_id
        for track_id, track_rows in rows_by_track.items()
        if len(track_rows) >= args.min_track_detections
    }
    print(
        f"Eligible tracks: {len(eligible_track_ids)} "
        f"with at least {args.min_track_detections} detections"
    )
    capture = cv2.VideoCapture(str(args.video))

    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {args.video}")

    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    video_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if frame_count <= 0 or video_width <= 0 or video_height <= 0:
        capture.release()
        raise ValueError(
            "Invalid source-video metadata: "
            f"frames={frame_count}, resolution={video_width}x{video_height}"
        )

    features_by_track = defaultdict(list)
    best_crop_by_track = {}
    best_crop_score_by_track = defaultdict(lambda: -1.0)

    try:
        for frame_index in range(frame_count):
            success, frame = capture.read()

            if not success:
                break

            if frame_index % args.sample_every_n_frames != 0:
                continue

            for row in rows_by_frame.get(frame_index, []):
                track_id = row["track_id"]

                if track_id not in eligible_track_ids:
                    continue

                x1 = max(0, int(round(row["x1"])))
                y1 = max(0, int(round(row["y1"])))
                x2 = min(video_width - 1, int(round(row["x2"])))
                y2 = min(video_height - 1, int(round(row["y2"])))
                box_width = x2 - x1
                box_height = y2 - y1

                if (
                    box_width < args.min_box_width
                    or box_height < args.min_box_height
                ):
                    continue

                crop_x1 = max(0, int(x1 + box_width * 0.20))
                crop_x2 = min(video_width, int(x1 + box_width * 0.80))
                crop_y1 = max(0, int(y1 + box_height * 0.18))
                crop_y2 = min(video_height, int(y1 + box_height * 0.58))
                jersey_crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]

                if jersey_crop.size == 0:
                    continue

                hsv_crop = cv2.cvtColor(jersey_crop, cv2.COLOR_BGR2HSV)
                gray_crop = cv2.cvtColor(jersey_crop, cv2.COLOR_BGR2GRAY)
                saturation = hsv_crop[:, :, 1]
                value = hsv_crop[:, :, 2]
                bright_neutral_mask = (
                    (value >= args.bright_value_threshold)
                    & (saturation <= args.bright_saturation_max)
                )
                dark_mask = value <= args.dark_value_threshold
                features_by_track[track_id].append(
                    {
                        "frame_index": frame_index,
                        "bright_fraction": float(np.mean(bright_neutral_mask)),
                        "dark_fraction": float(np.mean(dark_mask)),
                        "grayscale_std": float(np.std(gray_crop)),
                        "mean_saturation": float(np.mean(saturation)),
                        "mean_value": float(np.mean(value)),
                    }
                )
                crop_score = row["confidence"] * math.sqrt(
                    box_width * box_height
                )

                if crop_score > best_crop_score_by_track[track_id]:
                    best_crop_score_by_track[track_id] = crop_score
                    best_crop_by_track[track_id] = jersey_crop.copy()
    finally:
        capture.release()

    return dict(features_by_track), best_crop_by_track


def aggregate_features(features_by_track, rows_by_track):
    track_feature_rows = []

    for track_id in sorted(features_by_track):
        samples = features_by_track[track_id]
        track_feature_rows.append(
            {
                "track_id": track_id,
                "track_detections": len(rows_by_track[track_id]),
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

    return track_feature_rows


def write_features(path, track_feature_rows):
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
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(track_feature_rows)


def write_montage(args, track_feature_rows, best_crop_by_track):
    import cv2
    import numpy as np

    montage_tiles = []

    for feature_row in track_feature_rows:
        track_id = feature_row["track_id"]
        crop = best_crop_by_track.get(track_id)

        if crop is None:
            continue

        tile = cv2.resize(
            crop,
            (args.crop_width, args.crop_height),
            interpolation=cv2.INTER_CUBIC,
        )
        labeled_tile = cv2.copyMakeBorder(
            tile,
            42,
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

    if not montage_tiles:
        return False

    tile_height, tile_width = montage_tiles[0].shape[:2]
    montage_rows = math.ceil(len(montage_tiles) / args.montage_columns)
    montage = np.zeros(
        (
            montage_rows * tile_height,
            args.montage_columns * tile_width,
            3,
        ),
        dtype=np.uint8,
    )

    for index, tile in enumerate(montage_tiles):
        row_index = index // args.montage_columns
        column_index = index % args.montage_columns
        y_start = row_index * tile_height
        x_start = column_index * tile_width
        montage[
            y_start:y_start + tile_height,
            x_start:x_start + tile_width,
        ] = tile

    args.output_montage.parent.mkdir(parents=True, exist_ok=True)

    if not cv2.imwrite(str(args.output_montage), montage):
        raise RuntimeError(f"Could not write montage: {args.output_montage}")

    return True


def main(argv=None):
    args = parse_args(argv)
    rows_by_frame, rows_by_track = load_tracking_rows(args.tracks)
    features_by_track, best_crop_by_track = collect_features(
        args,
        rows_by_frame,
        rows_by_track,
    )
    track_feature_rows = aggregate_features(
        features_by_track,
        rows_by_track,
    )
    write_features(args.output_features, track_feature_rows)
    montage_written = write_montage(
        args,
        track_feature_rows,
        best_crop_by_track,
    )
    print("\nUniform feature extraction complete.")
    print(f"Tracks analyzed: {len(track_feature_rows)}")
    print(f"Features saved to: {args.output_features}")

    if montage_written:
        print(f"Crop montage saved to: {args.output_montage}")
    else:
        print("Crop montage not written because no representative crops exist.")


if __name__ == "__main__":
    main()
