import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

try:
    import cv2
except ModuleNotFoundError:
    cv2 = None


VIDEO_PATH: Path
TRACKS_PATH: Path
OUTPUT_DIR: Path
REVIEW_CASES: list[dict]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Render player crops around generated ReID appearance-change "
            "boundaries."
        )
    )
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--tracks", type=Path, required=True)
    parser.add_argument("--segments-report", type=Path, required=True)
    parser.add_argument("--review-config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--context-frames",
        type=int,
        default=2,
        help="Frames sampled on either side of each boundary.",
    )
    args = parser.parse_args(argv)

    if args.context_frames < 1:
        parser.error("--context-frames must be positive")

    return args


def load_json(path, required):
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Required JSON not found: {path}")

        return {}

    with path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def build_review_cases(segment_report, review_config, context_frames):
    cases = {}

    for candidate in segment_report.get(
        "appearance_change_candidates",
        [],
    ):
        track_id = int(candidate["track_id"])
        before = int(candidate["before_last_frame"])
        after = int(candidate["after_first_frame"])
        key = (track_id, before, after)
        distance = float(candidate["appearance_distance"])
        cases[key] = {
            "name": f"t{track_id}_boundary_{before}_{after}",
            "track_id": track_id,
            "frames": sorted(
                {
                    max(0, before - context_frames),
                    before,
                    after,
                    after + context_frames,
                }
            ),
            "description": (
                f"T{track_id}: ReID change {distance:.3f} | "
                f"{candidate.get('review_decision', 'review_required')}"
            ),
        }

    for raw_track_id, boundaries in review_config.get(
        "manual_split_after_frames",
        {},
    ).items():
        track_id = int(raw_track_id)

        for raw_boundary in boundaries:
            boundary = int(raw_boundary)
            key = (track_id, boundary, boundary + 1)
            cases.setdefault(
                key,
                {
                    "name": f"t{track_id}_manual_{boundary}_{boundary + 1}",
                    "track_id": track_id,
                    "frames": sorted(
                        {
                            max(0, boundary - context_frames),
                            boundary,
                            boundary + 1,
                            boundary + 1 + context_frames,
                        }
                    ),
                    "description": (
                        f"T{track_id}: reviewed split after frame {boundary}"
                    ),
                },
            )

    return [cases[key] for key in sorted(cases)]


FULL_TILE_SIZE = (460, 270)
ZOOM_TILE_SIZE = (460, 360)
ZOOM_PADDING_X = 170
ZOOM_PADDING_Y = 140

TARGET_COLOR = (0, 255, 255)
TEAM_COLORS = {
    "white": (255, 220, 40),
    "dark": (255, 80, 220),
    "unknown": (170, 170, 170),
}


def load_tracks():
    rows_by_frame = defaultdict(list)

    with TRACKS_PATH.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as input_file:
        reader = csv.DictReader(input_file)

        for row in reader:
            parsed = {
                "frame_index": int(row["frame_index"]),
                "track_id": int(row["track_id"]),
                "confidence": float(row["confidence"]),
                "x1": int(round(float(row["x1"]))),
                "y1": int(round(float(row["y1"]))),
                "x2": int(round(float(row["x2"]))),
                "y2": int(round(float(row["y2"]))),
                "team_label": row["team_label"],
            }

            rows_by_frame[
                parsed["frame_index"]
            ].append(parsed)

    return rows_by_frame


def read_frames(frame_indices):
    cap = cv2.VideoCapture(str(VIDEO_PATH))

    if not cap.isOpened():
        raise RuntimeError(
            f"Could not open video: {VIDEO_PATH}"
        )

    frames = {}

    try:
        for frame_index in sorted(frame_indices):
            cap.set(
                cv2.CAP_PROP_POS_FRAMES,
                frame_index,
            )

            success, frame = cap.read()

            if not success:
                raise RuntimeError(
                    "Could not read frame "
                    f"{frame_index} from {VIDEO_PATH}"
                )

            frames[frame_index] = frame
    finally:
        cap.release()

    return frames


def annotate_frame(
    frame,
    rows,
    target_track_id,
):
    annotated = frame.copy()

    for row in rows:
        track_id = row["track_id"]
        is_target = track_id == target_track_id

        color = (
            TARGET_COLOR
            if is_target
            else TEAM_COLORS.get(
                row["team_label"],
                TEAM_COLORS["unknown"],
            )
        )

        thickness = 5 if is_target else 2

        cv2.rectangle(
            annotated,
            (row["x1"], row["y1"]),
            (row["x2"], row["y2"]),
            color,
            thickness,
        )

        label = (
            f"T{track_id} "
            f"{row['team_label']} "
            f"{row['confidence']:.2f}"
        )

        text_origin = (
            row["x1"],
            max(24, row["y1"] - 8),
        )

        cv2.putText(
            annotated,
            label,
            text_origin,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            color,
            2,
            cv2.LINE_AA,
        )

    return annotated


def fit_to_tile(image, tile_size):
    tile_width, tile_height = tile_size
    image_height, image_width = image.shape[:2]

    scale = min(
        tile_width / image_width,
        tile_height / image_height,
    )

    resized_width = max(
        1,
        int(round(image_width * scale)),
    )
    resized_height = max(
        1,
        int(round(image_height * scale)),
    )

    resized = cv2.resize(
        image,
        (resized_width, resized_height),
        interpolation=cv2.INTER_AREA,
    )

    tile = np.zeros(
        (tile_height, tile_width, 3),
        dtype=np.uint8,
    )

    x_offset = (tile_width - resized_width) // 2
    y_offset = (tile_height - resized_height) // 2

    tile[
        y_offset:y_offset + resized_height,
        x_offset:x_offset + resized_width,
    ] = resized

    return tile


def add_tile_header(tile, text):
    result = tile.copy()

    cv2.rectangle(
        result,
        (0, 0),
        (result.shape[1], 34),
        (0, 0, 0),
        -1,
    )

    cv2.putText(
        result,
        text,
        (10, 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )

    return result


def get_target_row(
    rows_by_frame,
    frame_index,
    target_track_id,
):
    return next(
        (
            row
            for row in rows_by_frame.get(
                frame_index,
                [],
            )
            if row["track_id"]
            == target_track_id
        ),
        None,
    )


def build_zoom_bounds(
    rows_by_frame,
    frame_indices,
    target_track_id,
    frame_width,
    frame_height,
):
    target_rows = [
        row
        for frame_index in frame_indices
        if (
            row := get_target_row(
                rows_by_frame,
                frame_index,
                target_track_id,
            )
        )
        is not None
    ]

    if not target_rows:
        raise RuntimeError(
            "No rows found for target track "
            f"T{target_track_id} in frames "
            f"{frame_indices}"
        )

    x1 = max(
        0,
        min(row["x1"] for row in target_rows)
        - ZOOM_PADDING_X,
    )
    y1 = max(
        0,
        min(row["y1"] for row in target_rows)
        - ZOOM_PADDING_Y,
    )
    x2 = min(
        frame_width,
        max(row["x2"] for row in target_rows)
        + ZOOM_PADDING_X,
    )
    y2 = min(
        frame_height,
        max(row["y2"] for row in target_rows)
        + ZOOM_PADDING_Y,
    )

    return x1, y1, x2, y2


def create_montage(
    review_case,
    frames,
    rows_by_frame,
):
    frame_indices = review_case["frames"]
    target_track_id = review_case["track_id"]

    first_frame = frames[frame_indices[0]]
    frame_height, frame_width = (
        first_frame.shape[:2]
    )

    zoom_bounds = build_zoom_bounds(
        rows_by_frame,
        frame_indices,
        target_track_id,
        frame_width,
        frame_height,
    )

    x1, y1, x2, y2 = zoom_bounds

    full_tiles = []
    zoom_tiles = []

    for frame_index in frame_indices:
        annotated = annotate_frame(
            frames[frame_index],
            rows_by_frame.get(frame_index, []),
            target_track_id,
        )

        target_row = get_target_row(
            rows_by_frame,
            frame_index,
            target_track_id,
        )

        target_status = (
            f"T{target_track_id} "
            f"conf={target_row['confidence']:.2f}"
            if target_row
            else f"T{target_track_id} missing"
        )

        header = (
            f"frame {frame_index} | "
            f"{target_status}"
        )

        full_tile = fit_to_tile(
            annotated,
            FULL_TILE_SIZE,
        )
        full_tiles.append(
            add_tile_header(full_tile, header)
        )

        zoom = annotated[y1:y2, x1:x2]
        zoom_tile = fit_to_tile(
            zoom,
            ZOOM_TILE_SIZE,
        )
        zoom_tiles.append(
            add_tile_header(
                zoom_tile,
                f"ZOOM | {header}",
            )
        )

    full_row = np.hstack(full_tiles)
    zoom_row = np.hstack(zoom_tiles)

    title_height = 64
    title = np.zeros(
        (
            title_height,
            full_row.shape[1],
            3,
        ),
        dtype=np.uint8,
    )

    cv2.putText(
        title,
        review_case["description"],
        (16, 42),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        TARGET_COLOR,
        2,
        cv2.LINE_AA,
    )

    return np.vstack(
        [title, full_row, zoom_row]
    )


def main():
    global VIDEO_PATH
    global TRACKS_PATH
    global OUTPUT_DIR
    global REVIEW_CASES

    args = parse_args()
    VIDEO_PATH = args.video
    TRACKS_PATH = args.tracks
    OUTPUT_DIR = args.output_dir
    REVIEW_CASES = build_review_cases(
        load_json(args.segments_report, required=True),
        load_json(args.review_config, required=False),
        args.context_frames,
    )

    if cv2 is None:
        raise ModuleNotFoundError(
            "OpenCV is required to render identity-boundary montages."
        )

    if not VIDEO_PATH.exists():
        raise FileNotFoundError(
            f"Video not found: {VIDEO_PATH}"
        )

    if not TRACKS_PATH.exists():
        raise FileNotFoundError(
            f"Tracks not found: {TRACKS_PATH}"
        )

    rows_by_frame = load_tracks()

    if not REVIEW_CASES:
        print("No ReID appearance boundaries require visual review.")
        return

    requested_frames = {
        frame_index
        for review_case in REVIEW_CASES
        for frame_index in review_case["frames"]
    }

    frames = read_frames(requested_frames)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("\nGenerating identity-boundary review montages...")

    for review_case in REVIEW_CASES:
        montage = create_montage(
            review_case,
            frames,
            rows_by_frame,
        )

        output_path = (
            OUTPUT_DIR
            / f"{review_case['name']}.jpg"
        )

        success = cv2.imwrite(
            str(output_path),
            montage,
            [cv2.IMWRITE_JPEG_QUALITY, 95],
        )

        if not success:
            raise RuntimeError(
                f"Could not write: {output_path}"
            )

        print(f"  Saved: {output_path}")

    print("\nReview montage generation complete.")


if __name__ == "__main__":
    main()
