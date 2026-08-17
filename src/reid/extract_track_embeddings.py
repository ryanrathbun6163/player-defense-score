import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_SAMPLE_EVERY_N_FRAMES = 5
DEFAULT_MIN_CONFIDENCE = 0.20
DEFAULT_MIN_BOX_WIDTH = 20
DEFAULT_MIN_BOX_HEIGHT = 50
DEFAULT_EXTRACTOR_BATCH_SIZE = 64


def build_parser():
    parser = argparse.ArgumentParser(
        description="Extract sampled OSNet-AIN embeddings for player tracks."
    )
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--classified-tracks", type=Path, required=True)
    parser.add_argument("--output-embeddings", type=Path, required=True)
    parser.add_argument("--output-metadata", type=Path, required=True)
    parser.add_argument(
        "--sample-every-n-frames",
        type=int,
        default=DEFAULT_SAMPLE_EVERY_N_FRAMES,
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=DEFAULT_MIN_CONFIDENCE,
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
        "--extractor-batch-size",
        type=int,
        default=DEFAULT_EXTRACTOR_BATCH_SIZE,
    )
    return parser


def parse_args(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    for name in (
        "sample_every_n_frames",
        "min_box_width",
        "min_box_height",
        "extractor_batch_size",
    ):
        if getattr(args, name) < 1:
            parser.error(f"--{name.replace('_', '-')} must be positive")

    if not 0.0 <= args.min_confidence <= 1.0:
        parser.error("--min-confidence must be in [0, 1]")

    return args


def run(args):
    import cv2
    import numpy as np
    from tqdm import tqdm

    from src.reid.osnet_extractor import (
        MODEL_FILENAME,
        MODEL_REPOSITORY,
        OSNetExtractor,
    )

    VIDEO_PATH = args.video
    CLASSIFIED_TRACKS_PATH = args.classified_tracks
    EMBEDDINGS_OUTPUT_PATH = args.output_embeddings
    METADATA_OUTPUT_PATH = args.output_metadata
    SAMPLE_EVERY_N_FRAMES = args.sample_every_n_frames
    MIN_CONFIDENCE = args.min_confidence
    MIN_BOX_WIDTH = args.min_box_width
    MIN_BOX_HEIGHT = args.min_box_height
    EXTRACTOR_BATCH_SIZE = args.extractor_batch_size

    if not CLASSIFIED_TRACKS_PATH.exists():
        raise FileNotFoundError(
            "Classified tracking CSV not found: "
            f"{CLASSIFIED_TRACKS_PATH}"
        )

    rows_by_frame = defaultdict(list)

    with CLASSIFIED_TRACKS_PATH.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as input_file:
        reader = csv.DictReader(input_file)

        for row in reader:
            parsed_row = {
                "frame_index": int(
                    row["frame_index"]
                ),
                "track_id": int(
                    row["track_id"]
                ),
                "confidence": float(
                    row["confidence"]
                ),
                "x1": float(row["x1"]),
                "y1": float(row["y1"]),
                "x2": float(row["x2"]),
                "y2": float(row["y2"]),
                "team_label": row["team_label"],
            }

            rows_by_frame[
                parsed_row["frame_index"]
            ].append(parsed_row)


    # ---------------------------------------------------------
    # Open video and collect sampled crops
    # ---------------------------------------------------------

    cap = cv2.VideoCapture(str(VIDEO_PATH))

    if not cap.isOpened():
        raise RuntimeError(
            f"Could not open video: {VIDEO_PATH}"
        )

    frame_count = int(
        cap.get(cv2.CAP_PROP_FRAME_COUNT)
    )
    video_width = int(
        cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    )
    video_height = int(
        cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    )

    crops = []
    sample_metadata = []
    skipped_low_confidence = 0
    skipped_small_boxes = 0
    skipped_empty_crops = 0

    try:
        for frame_index in tqdm(
            range(frame_count),
            desc="Collecting ReID crops",
        ):
            success, frame = cap.read()

            if not success:
                break

            if (
                frame_index
                % SAMPLE_EVERY_N_FRAMES
                != 0
            ):
                continue

            for row in rows_by_frame.get(
                frame_index,
                [],
            ):
                if (
                    row["confidence"]
                    < MIN_CONFIDENCE
                ):
                    skipped_low_confidence += 1
                    continue

                x1 = max(
                    0,
                    int(round(row["x1"])),
                )
                y1 = max(
                    0,
                    int(round(row["y1"])),
                )
                x2 = min(
                    video_width,
                    int(round(row["x2"])),
                )
                y2 = min(
                    video_height,
                    int(round(row["y2"])),
                )

                box_width = x2 - x1
                box_height = y2 - y1

                if (
                    box_width < MIN_BOX_WIDTH
                    or box_height < MIN_BOX_HEIGHT
                ):
                    skipped_small_boxes += 1
                    continue

                person_crop = frame[
                    y1:y2,
                    x1:x2,
                ]

                if person_crop.size == 0:
                    skipped_empty_crops += 1
                    continue

                crops.append(person_crop)

                sample_metadata.append(
                    {
                        "frame_index": (
                            frame_index
                        ),
                        "track_id": row["track_id"],
                        "confidence": (
                            row["confidence"]
                        ),
                        "team_label": (
                            row["team_label"]
                        ),
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                    }
                )

    finally:
        cap.release()


    if not crops:
        raise RuntimeError(
            "No valid player crops were collected"
        )

    print(
        f"\nCollected {len(crops)} "
        "player crops"
    )


    # ---------------------------------------------------------
    # Extract normalized OSNet embeddings
    # ---------------------------------------------------------

    extractor = OSNetExtractor(
        batch_size=EXTRACTOR_BATCH_SIZE,
    )

    embeddings = extractor.extract(crops)

    if len(embeddings) != len(sample_metadata):
        raise RuntimeError(
            "Embedding count does not match "
            "sample metadata count"
        )


    # ---------------------------------------------------------
    # Convert metadata to NumPy arrays
    # ---------------------------------------------------------

    frame_indices = np.array(
        [
            sample["frame_index"]
            for sample in sample_metadata
        ],
        dtype=np.int32,
    )

    track_ids = np.array(
        [
            sample["track_id"]
            for sample in sample_metadata
        ],
        dtype=np.int32,
    )

    confidences = np.array(
        [
            sample["confidence"]
            for sample in sample_metadata
        ],
        dtype=np.float32,
    )

    team_labels = np.array(
        [
            sample["team_label"]
            for sample in sample_metadata
        ],
        dtype=np.str_,
    )

    bounding_boxes = np.array(
        [
            [
                sample["x1"],
                sample["y1"],
                sample["x2"],
                sample["y2"],
            ]
            for sample in sample_metadata
        ],
        dtype=np.int32,
    )


    # ---------------------------------------------------------
    # Save embeddings and metadata
    # ---------------------------------------------------------

    EMBEDDINGS_OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    METADATA_OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    np.savez_compressed(
        EMBEDDINGS_OUTPUT_PATH,
        embeddings=embeddings,
        frame_indices=frame_indices,
        track_ids=track_ids,
        confidences=confidences,
        team_labels=team_labels,
        bounding_boxes=bounding_boxes,
    )

    sample_count_by_track = Counter(
        track_ids.tolist()
    )

    metadata_report = {
        "video": str(VIDEO_PATH),
        "classified_tracks": str(
            CLASSIFIED_TRACKS_PATH
        ),
        "model_repository": MODEL_REPOSITORY,
        "model_filename": MODEL_FILENAME,
        "embedding_dimension": int(
            embeddings.shape[1]
        ),
        "sample_every_n_frames": (
            SAMPLE_EVERY_N_FRAMES
        ),
        "minimum_confidence": (
            MIN_CONFIDENCE
        ),
        "minimum_box_width": MIN_BOX_WIDTH,
        "minimum_box_height": MIN_BOX_HEIGHT,
        "total_embeddings": int(
            len(embeddings)
        ),
        "unique_track_ids": int(
            len(sample_count_by_track)
        ),
        "samples_by_track": {
            str(track_id): sample_count
            for track_id, sample_count
            in sorted(
                sample_count_by_track.items()
            )
        },
        "skipped_low_confidence": (
            skipped_low_confidence
        ),
        "skipped_small_boxes": (
            skipped_small_boxes
        ),
        "skipped_empty_crops": (
            skipped_empty_crops
        ),
    }

    with METADATA_OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            metadata_report,
            output_file,
            indent=2,
        )

        output_file.write("\n")


    # ---------------------------------------------------------
    # Print summary
    # ---------------------------------------------------------

    embedding_norms = np.linalg.norm(
        embeddings,
        axis=1,
    )

    print("\nOSNet embedding extraction complete.")
    print(
        f"Embeddings: {embeddings.shape}"
    )
    print(
        "Embedding norm range: "
        f"{embedding_norms.min():.4f} "
        f"to {embedding_norms.max():.4f}"
    )
    print(
        f"Unique sampled tracks: "
        f"{len(sample_count_by_track)}"
    )
    print(
        f"Skipped low-confidence rows: "
        f"{skipped_low_confidence}"
    )
    print(
        f"Skipped small boxes: "
        f"{skipped_small_boxes}"
    )
    print(
        f"Skipped empty crops: "
        f"{skipped_empty_crops}"
    )
    print(
        f"Embeddings saved to: "
        f"{EMBEDDINGS_OUTPUT_PATH}"
    )
    print(
        f"Metadata saved to: "
        f"{METADATA_OUTPUT_PATH}"
    )


def main():
    run(parse_args())


if __name__ == "__main__":
    main()
