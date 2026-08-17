import argparse
import csv
import itertools
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

try:
    import cv2
except ModuleNotFoundError:
    cv2 = None


VIDEO_PATH: Path
RECONCILED_TRACKS_PATH: Path
MAPPING_PATH: Path
PROTOTYPES_PATH: Path
OUTPUT_DIR: Path
REPORT_PATH: Path
CANDIDATE_MONTAGE_DIR: Path
EPISODE_MONTAGE_DIR: Path


EXPECTED_PLAYER_COUNT = 10
MAX_REVIEW_FRAMES = 4

MIN_MULTI_FRAME_COUNT = 2
MIN_MEDIAN_IOU = 0.15
MIN_UPPER_QUARTILE_IOU = 0.30
MIN_DISTANCE_SUPPORTED_IOU = 0.15
MAX_DISTANCE_SUPPORTED_MEDIAN_FLOOR_DISTANCE = 100.0

MIN_SINGLE_FRAME_IOU = 0.30
MAX_SINGLE_FRAME_FLOOR_DISTANCE = 100.0


FULL_TILE_SIZE = (520, 292)
ZOOM_TILE_SIZE = (520, 390)
ZOOM_PADDING_X = 150
ZOOM_PADDING_Y = 120

FIRST_COLOR = (0, 215, 255)
SECOND_COLOR = (255, 80, 220)
OTHER_COLOR = (115, 115, 115)
TEXT_COLOR = (255, 255, 255)
TEAM_COLORS = {
    "white": (255, 220, 40),
    "dark": (255, 80, 220),
    "unknown": (170, 170, 170),
}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Generate residual player-identity candidates and "
            "visual review montages."
        )
    )
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--reconciled-tracks", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--prototypes", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--expected-player-count",
        type=int,
        default=EXPECTED_PLAYER_COUNT,
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help=(
            "Write the JSON candidate report without reading "
            "the source video or creating images."
        ),
    )
    args = parser.parse_args(argv)

    if args.expected_player_count < 1:
        parser.error("--expected-player-count must be positive")

    return args


def load_json(path):
    with path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def load_reconciled_rows(path):
    rows_by_frame = defaultdict(list)

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as input_file:
        reader = csv.DictReader(input_file)

        for row in reader:
            parsed = dict(row)
            parsed["frame_index"] = int(row["frame_index"])
            parsed["track_id"] = int(row["track_id"])
            parsed["confidence"] = float(row["confidence"])

            for field in (
                "x1",
                "y1",
                "x2",
                "y2",
                "floor_x",
                "floor_y",
            ):
                parsed[field] = float(row[field])

            rows_by_frame[
                parsed["frame_index"]
            ].append(parsed)

    for rows in rows_by_frame.values():
        rows.sort(key=lambda row: row["player_id"])

    return dict(rows_by_frame)


def load_prototypes(path):
    with np.load(path) as archive:
        return {
            str(segment_id): prototype.astype(
                np.float32,
                copy=True,
            )
            for segment_id, prototype in zip(
                archive["segment_ids"],
                archive["prototypes"],
            )
        }


def bounding_box_iou(first, second):
    intersection_x1 = max(first["x1"], second["x1"])
    intersection_y1 = max(first["y1"], second["y1"])
    intersection_x2 = min(first["x2"], second["x2"])
    intersection_y2 = min(first["y2"], second["y2"])

    intersection_width = max(
        0.0,
        intersection_x2 - intersection_x1,
    )
    intersection_height = max(
        0.0,
        intersection_y2 - intersection_y1,
    )
    intersection_area = (
        intersection_width * intersection_height
    )

    first_area = max(
        0.0,
        first["x2"] - first["x1"],
    ) * max(
        0.0,
        first["y2"] - first["y1"],
    )
    second_area = max(
        0.0,
        second["x2"] - second["x1"],
    ) * max(
        0.0,
        second["y2"] - second["y1"],
    )

    union_area = first_area + second_area - intersection_area

    if union_area <= 0:
        return 0.0

    return intersection_area / union_area


def floor_distance(first, second):
    return math.hypot(
        first["floor_x"] - second["floor_x"],
        first["floor_y"] - second["floor_y"],
    )


def teams_are_compatible(first, second):
    return (
        first == "unknown"
        or second == "unknown"
        or first == second
    )


def cosine_distance(first, second):
    return 1.0 - float(np.dot(first, second))


def quantile(values, amount):
    return float(np.quantile(values, amount))


def ordered_rows(first, second):
    if first["player_id"] <= second["player_id"]:
        return first, second

    return second, first


def candidate_passes_thresholds(record):
    frame_count = record["cooccurrence_frame_count"]

    if frame_count == 1:
        return (
            record["maximum_iou"] >= MIN_SINGLE_FRAME_IOU
            and record["minimum_floor_distance"]
            <= MAX_SINGLE_FRAME_FLOOR_DISTANCE
        )

    if frame_count < MIN_MULTI_FRAME_COUNT:
        return False

    if record["median_iou"] >= MIN_MEDIAN_IOU:
        return True

    if (
        record["upper_quartile_iou"]
        >= MIN_UPPER_QUARTILE_IOU
    ):
        return True

    return (
        record["upper_quartile_iou"]
        >= MIN_DISTANCE_SUPPORTED_IOU
        and record["median_floor_distance"]
        <= MAX_DISTANCE_SUPPORTED_MEDIAN_FLOOR_DISTANCE
    )


def candidate_priority(record):
    frame_support = min(
        record["cooccurrence_frame_count"],
        12,
    ) / 12.0
    distance_penalty = max(
        0.0,
        record["median_floor_distance"] - 60.0,
    ) / 300.0

    return (
        2.0 * record["median_iou"]
        + record["upper_quartile_iou"]
        + record["maximum_iou"]
        + frame_support
        - distance_penalty
    )


def choose_review_frames(frame_metrics):
    if len(frame_metrics) <= MAX_REVIEW_FRAMES:
        return sorted(
            metric["frame_index"]
            for metric in frame_metrics
        )

    ordered_by_frame = sorted(
        frame_metrics,
        key=lambda metric: metric["frame_index"],
    )
    ordered_by_iou = sorted(
        frame_metrics,
        key=lambda metric: (
            -metric["iou"],
            metric["floor_distance"],
            metric["frame_index"],
        ),
    )
    ordered_by_distance = sorted(
        frame_metrics,
        key=lambda metric: (
            metric["floor_distance"],
            -metric["iou"],
            metric["frame_index"],
        ),
    )

    chosen = []

    def add_frame(frame_index):
        if (
            frame_index not in chosen
            and len(chosen) < MAX_REVIEW_FRAMES
        ):
            chosen.append(frame_index)

    add_frame(ordered_by_iou[0]["frame_index"])
    add_frame(ordered_by_distance[0]["frame_index"])
    add_frame(ordered_by_frame[0]["frame_index"])
    add_frame(ordered_by_frame[-1]["frame_index"])

    if len(chosen) < MAX_REVIEW_FRAMES:
        middle = ordered_by_frame[
            len(ordered_by_frame) // 2
        ]
        add_frame(middle["frame_index"])

    return sorted(chosen)


def build_pair_candidates(
    rows_by_frame,
    prototypes,
):
    pair_metrics = defaultdict(list)
    pair_segment_pairs = defaultdict(set)
    pair_teams = {}
    frame_identity_counts = {
        frame_index: len(rows)
        for frame_index, rows in rows_by_frame.items()
    }

    for frame_index, rows in rows_by_frame.items():
        for first, second in itertools.combinations(rows, 2):
            first, second = ordered_rows(first, second)
            first_team = first["reconciled_team"]
            second_team = second["reconciled_team"]

            if not teams_are_compatible(
                first_team,
                second_team,
            ):
                continue

            pair = (
                first["player_id"],
                second["player_id"],
            )
            pair_teams[pair] = (
                first_team,
                second_team,
            )
            pair_segment_pairs[pair].add(
                tuple(
                    sorted(
                        (
                            first["segment_id"],
                            second["segment_id"],
                        )
                    )
                )
            )
            pair_metrics[pair].append(
                {
                    "frame_index": frame_index,
                    "iou": bounding_box_iou(first, second),
                    "floor_distance": floor_distance(
                        first,
                        second,
                    ),
                }
            )

    candidates = []

    for pair, metrics in pair_metrics.items():
        ious = [metric["iou"] for metric in metrics]
        distances = [
            metric["floor_distance"]
            for metric in metrics
        ]
        overloaded_frames = [
            metric["frame_index"]
            for metric in metrics
            if frame_identity_counts[
                metric["frame_index"]
            ]
            > EXPECTED_PLAYER_COUNT
        ]
        segment_pairs = sorted(pair_segment_pairs[pair])
        appearance_distances = []

        for first_segment, second_segment in segment_pairs:
            if (
                first_segment in prototypes
                and second_segment in prototypes
            ):
                appearance_distances.append(
                    cosine_distance(
                        prototypes[first_segment],
                        prototypes[second_segment],
                    )
                )

        record = {
            "first_player_id": pair[0],
            "second_player_id": pair[1],
            "first_team": pair_teams[pair][0],
            "second_team": pair_teams[pair][1],
            "cooccurrence_frame_count": len(metrics),
            "first_cooccurrence_frame": min(
                metric["frame_index"]
                for metric in metrics
            ),
            "last_cooccurrence_frame": max(
                metric["frame_index"]
                for metric in metrics
            ),
            "overloaded_frame_count": len(overloaded_frames),
            "median_iou": float(np.median(ious)),
            "upper_quartile_iou": quantile(ious, 0.75),
            "maximum_iou": max(ious),
            "strong_overlap_frame_count": sum(
                iou >= MIN_SINGLE_FRAME_IOU
                for iou in ious
            ),
            "minimum_floor_distance": min(distances),
            "median_floor_distance": float(
                np.median(distances)
            ),
            "minimum_appearance_distance": (
                min(appearance_distances)
                if appearance_distances
                else None
            ),
            "median_appearance_distance": (
                float(np.median(appearance_distances))
                if appearance_distances
                else None
            ),
            "segment_pairs": [
                {
                    "first_segment_id": first_segment,
                    "second_segment_id": second_segment,
                }
                for first_segment, second_segment in segment_pairs
            ],
            "review_frames": choose_review_frames(metrics),
        }

        if not candidate_passes_thresholds(record):
            continue

        record["priority_score"] = candidate_priority(record)
        candidates.append(record)

    candidates.sort(
        key=lambda record: (
            -record["priority_score"],
            -record["overloaded_frame_count"],
            record["first_player_id"],
            record["second_player_id"],
        )
    )

    for index, candidate in enumerate(candidates, 1):
        candidate["candidate_id"] = f"residual_{index:03d}"

    return candidates


def choose_episode_review_frames(frame_indices, rows_by_frame):
    if len(frame_indices) <= MAX_REVIEW_FRAMES:
        return list(frame_indices)

    maximum_count = max(
        len(rows_by_frame[frame_index])
        for frame_index in frame_indices
    )
    maximum_frames = [
        frame_index
        for frame_index in frame_indices
        if len(rows_by_frame[frame_index]) == maximum_count
    ]
    chosen = []

    def add_frame(frame_index):
        if (
            frame_index not in chosen
            and len(chosen) < MAX_REVIEW_FRAMES
        ):
            chosen.append(frame_index)

    add_frame(maximum_frames[len(maximum_frames) // 2])
    add_frame(frame_indices[0])
    add_frame(frame_indices[len(frame_indices) // 2])
    add_frame(frame_indices[-1])

    return sorted(chosen)


def build_overcount_episodes(rows_by_frame):
    overloaded_frames = sorted(
        frame_index
        for frame_index, rows in rows_by_frame.items()
        if len(rows) > EXPECTED_PLAYER_COUNT
    )
    frame_groups = []

    for frame_index in overloaded_frames:
        if (
            not frame_groups
            or frame_index > frame_groups[-1][-1] + 1
        ):
            frame_groups.append([frame_index])
        else:
            frame_groups[-1].append(frame_index)

    episodes = []

    for index, frame_indices in enumerate(frame_groups, 1):
        identity_counts = [
            len(rows_by_frame[frame_index])
            for frame_index in frame_indices
        ]
        player_ids = sorted(
            {
                row["player_id"]
                for frame_index in frame_indices
                for row in rows_by_frame[frame_index]
            }
        )
        count_distribution = Counter(identity_counts)

        episodes.append(
            {
                "episode_id": f"overcount_{index:03d}",
                "start_frame": frame_indices[0],
                "end_frame": frame_indices[-1],
                "frame_count": len(frame_indices),
                "maximum_identity_count": max(identity_counts),
                "identity_count_distribution": dict(
                    sorted(count_distribution.items())
                ),
                "player_ids": player_ids,
                "review_frames": choose_episode_review_frames(
                    frame_indices,
                    rows_by_frame,
                ),
            }
        )

    return episodes


def build_report(
    rows_by_frame,
    mapping_report,
    candidates,
    episodes,
):
    identity_count_distribution = Counter(
        len(rows)
        for rows in rows_by_frame.values()
    )
    overloaded_frame_count = sum(
        len(rows) > EXPECTED_PLAYER_COUNT
        for rows in rows_by_frame.values()
    )

    return {
        "reconciled_tracks": str(RECONCILED_TRACKS_PATH),
        "identity_mapping": str(MAPPING_PATH),
        "segment_prototypes": str(PROTOTYPES_PATH),
        "settings": {
            "expected_player_count": EXPECTED_PLAYER_COUNT,
            "minimum_multi_frame_count": MIN_MULTI_FRAME_COUNT,
            "minimum_median_iou": MIN_MEDIAN_IOU,
            "minimum_upper_quartile_iou": (
                MIN_UPPER_QUARTILE_IOU
            ),
            "minimum_distance_supported_iou": (
                MIN_DISTANCE_SUPPORTED_IOU
            ),
            "maximum_distance_supported_median_floor_distance": (
                MAX_DISTANCE_SUPPORTED_MEDIAN_FLOOR_DISTANCE
            ),
            "minimum_single_frame_iou": MIN_SINGLE_FRAME_IOU,
            "maximum_single_frame_floor_distance": (
                MAX_SINGLE_FRAME_FLOOR_DISTANCE
            ),
        },
        "summary": {
            "frame_count": len(rows_by_frame),
            "current_identity_cluster_count": mapping_report[
                "summary"
            ]["identity_cluster_count"],
            "identity_count_distribution": dict(
                sorted(identity_count_distribution.items())
            ),
            "overloaded_frame_count": overloaded_frame_count,
            "overcount_episode_count": len(episodes),
            "residual_candidate_count": len(candidates),
        },
        "decision_guide": {
            "same_identity": (
                "Both labels refer to the same player; merge them."
            ),
            "different_identity": (
                "The labels are different people; preserve a cannot-link."
            ),
            "exclude_first": (
                "The first label is an official, false detection, or "
                "other non-player."
            ),
            "exclude_second": (
                "The second label is an official, false detection, or "
                "other non-player."
            ),
            "uncertain": (
                "Evidence is insufficient; leave the pair unresolved."
            ),
        },
        "candidates": candidates,
        "overcount_episodes": episodes,
    }


def read_frames(frame_indices):
    capture = cv2.VideoCapture(str(VIDEO_PATH))

    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {VIDEO_PATH}")

    frames = {}

    try:
        for frame_index in sorted(frame_indices):
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            success, frame = capture.read()

            if not success:
                raise RuntimeError(
                    f"Could not read frame {frame_index} "
                    f"from {VIDEO_PATH}"
                )

            frames[frame_index] = frame
    finally:
        capture.release()

    return frames


def fit_to_tile(image, tile_size):
    tile_width, tile_height = tile_size
    image_height, image_width = image.shape[:2]
    scale = min(
        tile_width / image_width,
        tile_height / image_height,
    )
    resized_width = max(1, int(round(image_width * scale)))
    resized_height = max(1, int(round(image_height * scale)))
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


def add_header(tile, text, color=TEXT_COLOR):
    result = tile.copy()
    cv2.rectangle(
        result,
        (0, 0),
        (result.shape[1], 38),
        (0, 0, 0),
        -1,
    )
    cv2.putText(
        result,
        text,
        (10, 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        color,
        2,
        cv2.LINE_AA,
    )
    return result


def draw_label(image, row, color, thickness):
    x1 = int(round(row["x1"]))
    y1 = int(round(row["y1"]))
    x2 = int(round(row["x2"]))
    y2 = int(round(row["y2"]))
    cv2.rectangle(
        image,
        (x1, y1),
        (x2, y2),
        color,
        thickness,
    )
    label = (
        f"{row['player_id']} | "
        f"T{row['track_id']} | "
        f"{row['reconciled_team']}"
    )
    text_y = max(24, y1 - 8)
    (text_width, text_height), _ = cv2.getTextSize(
        label,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        2,
    )
    cv2.rectangle(
        image,
        (x1, max(0, text_y - text_height - 6)),
        (x1 + text_width + 6, text_y + 4),
        (0, 0, 0),
        -1,
    )
    cv2.putText(
        image,
        label,
        (x1 + 3, text_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        color,
        2,
        cv2.LINE_AA,
    )


def annotate_pair_frame(
    frame,
    rows,
    first_player_id,
    second_player_id,
):
    annotated = frame.copy()

    for row in rows:
        if row["player_id"] == first_player_id:
            color = FIRST_COLOR
            thickness = 5
        elif row["player_id"] == second_player_id:
            color = SECOND_COLOR
            thickness = 5
        else:
            color = OTHER_COLOR
            thickness = 1

        draw_label(annotated, row, color, thickness)

    return annotated


def annotate_episode_frame(frame, rows):
    annotated = frame.copy()

    for row in rows:
        color = TEAM_COLORS.get(
            row["reconciled_team"],
            TEAM_COLORS["unknown"],
        )
        draw_label(annotated, row, color, 3)

    return annotated


def find_player_row(rows, player_id):
    return next(
        (
            row
            for row in rows
            if row["player_id"] == player_id
        ),
        None,
    )


def pair_zoom(frame, first_row, second_row):
    frame_height, frame_width = frame.shape[:2]
    x1 = max(
        0,
        int(
            math.floor(
                min(first_row["x1"], second_row["x1"])
                - ZOOM_PADDING_X
            )
        ),
    )
    y1 = max(
        0,
        int(
            math.floor(
                min(first_row["y1"], second_row["y1"])
                - ZOOM_PADDING_Y
            )
        ),
    )
    x2 = min(
        frame_width,
        int(
            math.ceil(
                max(first_row["x2"], second_row["x2"])
                + ZOOM_PADDING_X
            )
        ),
    )
    y2 = min(
        frame_height,
        int(
            math.ceil(
                max(first_row["y2"], second_row["y2"])
                + ZOOM_PADDING_Y
            )
        ),
    )
    return frame[y1:y2, x1:x2]


def title_panel(width, lines, color):
    panel_height = 42 + 34 * len(lines)
    panel = np.zeros(
        (panel_height, width, 3),
        dtype=np.uint8,
    )

    for index, line in enumerate(lines):
        cv2.putText(
            panel,
            line,
            (16, 34 + index * 34),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.78 if index == 0 else 0.62,
            color if index == 0 else TEXT_COLOR,
            2,
            cv2.LINE_AA,
        )

    return panel


def create_pair_montage(
    candidate,
    frames,
    rows_by_frame,
):
    first_player_id = candidate["first_player_id"]
    second_player_id = candidate["second_player_id"]
    full_tiles = []
    zoom_tiles = []

    for frame_index in candidate["review_frames"]:
        rows = rows_by_frame[frame_index]
        annotated = annotate_pair_frame(
            frames[frame_index],
            rows,
            first_player_id,
            second_player_id,
        )
        first_row = find_player_row(rows, first_player_id)
        second_row = find_player_row(rows, second_player_id)

        if first_row is None or second_row is None:
            raise RuntimeError(
                "Candidate review frame is missing one of its "
                f"identities: {candidate['candidate_id']} "
                f"frame {frame_index}"
            )

        frame_iou = bounding_box_iou(first_row, second_row)
        frame_distance = floor_distance(first_row, second_row)
        header = (
            f"frame {frame_index} | "
            f"IoU={frame_iou:.3f} | "
            f"dist={frame_distance:.1f}px"
        )
        full_tiles.append(
            add_header(
                fit_to_tile(annotated, FULL_TILE_SIZE),
                header,
            )
        )
        zoom = pair_zoom(
            annotated,
            first_row,
            second_row,
        )
        zoom_tiles.append(
            add_header(
                fit_to_tile(zoom, ZOOM_TILE_SIZE),
                f"ZOOM | {header}",
            )
        )

    full_row = np.hstack(full_tiles)
    zoom_row = np.hstack(zoom_tiles)
    appearance_distance = candidate[
        "minimum_appearance_distance"
    ]
    appearance_text = (
        f"{appearance_distance:.3f}"
        if appearance_distance is not None
        else "n/a"
    )
    title = title_panel(
        full_row.shape[1],
        [
            (
                f"{candidate['candidate_id']} | "
                f"YELLOW {first_player_id} vs "
                f"MAGENTA {second_player_id}"
            ),
            (
                "coframes="
                f"{candidate['cooccurrence_frame_count']} | "
                "overloaded="
                f"{candidate['overloaded_frame_count']} | "
                "median IoU="
                f"{candidate['median_iou']:.3f} | "
                "median distance="
                f"{candidate['median_floor_distance']:.1f}px | "
                f"appearance={appearance_text}"
            ),
            (
                "Decision: same_identity / different_identity / "
                "exclude_first / exclude_second / uncertain"
            ),
        ],
        FIRST_COLOR,
    )
    return np.vstack([title, full_row, zoom_row])


def create_episode_montage(
    episode,
    frames,
    rows_by_frame,
):
    tiles = []

    for frame_index in episode["review_frames"]:
        rows = rows_by_frame[frame_index]
        annotated = annotate_episode_frame(
            frames[frame_index],
            rows,
        )
        header = (
            f"frame {frame_index} | "
            f"identities={len(rows)}"
        )
        tiles.append(
            add_header(
                fit_to_tile(annotated, FULL_TILE_SIZE),
                header,
            )
        )

    tile_row = np.hstack(tiles)
    title = title_panel(
        tile_row.shape[1],
        [
            (
                f"{episode['episode_id']} | frames "
                f"{episode['start_frame']}-"
                f"{episode['end_frame']} | "
                f"max identities={episode['maximum_identity_count']}"
            ),
            (
                "Colors show team classification: "
                "cyan=white, magenta=dark, gray=unknown"
            ),
        ],
        TEXT_COLOR,
    )
    return np.vstack([title, tile_row])


def write_montage(path, montage):
    path.parent.mkdir(parents=True, exist_ok=True)
    success = cv2.imwrite(
        str(path),
        montage,
        [cv2.IMWRITE_JPEG_QUALITY, 95],
    )

    if not success:
        raise RuntimeError(f"Could not write: {path}")


def generate_montages(
    candidates,
    episodes,
    rows_by_frame,
):
    requested_frames = {
        frame_index
        for candidate in candidates
        for frame_index in candidate["review_frames"]
    }
    requested_frames.update(
        frame_index
        for episode in episodes
        for frame_index in episode["review_frames"]
    )
    frames = read_frames(requested_frames)

    print("\nGenerating residual identity review montages...")

    for candidate in candidates:
        montage = create_pair_montage(
            candidate,
            frames,
            rows_by_frame,
        )
        filename = (
            f"{candidate['candidate_id']}_"
            f"{candidate['first_player_id']}__"
            f"{candidate['second_player_id']}.jpg"
        )
        output_path = CANDIDATE_MONTAGE_DIR / filename
        write_montage(output_path, montage)
        print(f"  Saved candidate: {output_path}")

    for episode in episodes:
        montage = create_episode_montage(
            episode,
            frames,
            rows_by_frame,
        )
        filename = (
            f"{episode['episode_id']}_"
            f"frames_{episode['start_frame']}_"
            f"{episode['end_frame']}.jpg"
        )
        output_path = EPISODE_MONTAGE_DIR / filename
        write_montage(output_path, montage)
        print(f"  Saved episode: {output_path}")


def main():
    global VIDEO_PATH
    global RECONCILED_TRACKS_PATH
    global MAPPING_PATH
    global PROTOTYPES_PATH
    global OUTPUT_DIR
    global REPORT_PATH
    global CANDIDATE_MONTAGE_DIR
    global EPISODE_MONTAGE_DIR
    global EXPECTED_PLAYER_COUNT

    args = parse_args()
    VIDEO_PATH = args.video
    RECONCILED_TRACKS_PATH = args.reconciled_tracks
    MAPPING_PATH = args.mapping
    PROTOTYPES_PATH = args.prototypes
    OUTPUT_DIR = args.output_dir
    REPORT_PATH = args.report
    CANDIDATE_MONTAGE_DIR = OUTPUT_DIR / "candidate_pairs"
    EPISODE_MONTAGE_DIR = OUTPUT_DIR / "overcount_episodes"
    EXPECTED_PLAYER_COUNT = args.expected_player_count
    required_paths = [
        RECONCILED_TRACKS_PATH,
        MAPPING_PATH,
        PROTOTYPES_PATH,
    ]

    for path in required_paths:
        if not path.exists():
            raise FileNotFoundError(f"Required input not found: {path}")

    if not args.report_only and not VIDEO_PATH.exists():
        raise FileNotFoundError(f"Video not found: {VIDEO_PATH}")

    if not args.report_only and cv2 is None:
        raise ModuleNotFoundError(
            "OpenCV is required to generate review montages. "
            "Install opencv-python or run with --report-only."
        )

    rows_by_frame = load_reconciled_rows(RECONCILED_TRACKS_PATH)
    mapping_report = load_json(MAPPING_PATH)
    prototypes = load_prototypes(PROTOTYPES_PATH)
    candidates = build_pair_candidates(
        rows_by_frame,
        prototypes,
    )
    episodes = build_overcount_episodes(rows_by_frame)
    report = build_report(
        rows_by_frame,
        mapping_report,
        candidates,
        episodes,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with REPORT_PATH.open("w", encoding="utf-8") as output_file:
        json.dump(report, output_file, indent=2)
        output_file.write("\n")

    if not args.report_only:
        generate_montages(
            candidates,
            episodes,
            rows_by_frame,
        )

    print("\nResidual identity review preparation complete.")
    print(f"Frames analyzed: {len(rows_by_frame)}")
    print(
        "Current identity clusters: "
        f"{mapping_report['summary']['identity_cluster_count']}"
    )
    print(
        "Frames above ten identities: "
        f"{report['summary']['overloaded_frame_count']}"
    )
    print(f"Overcount episodes: {len(episodes)}")
    print(f"Residual pair candidates: {len(candidates)}")

    print("\nResidual pair candidates:")

    for candidate in candidates:
        appearance_distance = candidate[
            "minimum_appearance_distance"
        ]
        appearance_text = (
            f"{appearance_distance:.3f}"
            if appearance_distance is not None
            else "n/a"
        )
        print(
            f"  {candidate['candidate_id']}: "
            f"{candidate['first_player_id']} <-> "
            f"{candidate['second_player_id']} | "
            "coframes="
            f"{candidate['cooccurrence_frame_count']} | "
            "overloaded="
            f"{candidate['overloaded_frame_count']} | "
            "median IoU="
            f"{candidate['median_iou']:.3f} | "
            "median floor distance="
            f"{candidate['median_floor_distance']:.1f}px | "
            f"appearance={appearance_text}"
        )

    print(f"Candidate report saved to: {REPORT_PATH}")

    if args.report_only:
        print("Montages skipped because --report-only was supplied.")
    else:
        print(f"Review montages saved under: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
