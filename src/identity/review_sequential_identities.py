import argparse
import csv
import itertools
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

import review_residual_identities as residual


VIDEO_PATH = Path("data/clips/possession_001.mp4")
RECONCILED_TRACKS_PATH = Path(
    "data/outputs/identity/"
    "possession_001_reconciled_tracks.csv"
)
MAPPING_PATH = Path(
    "data/outputs/identity/"
    "possession_001_segment_player_mapping.json"
)
PROTOTYPES_PATH = Path(
    "data/outputs/reid/"
    "possession_001_reid_segment_prototypes.npz"
)
REID_REVIEW_PATH = Path(
    "configs/possession_001_reid_review.json"
)
OUTPUT_DIR = Path(
    "data/outputs/identity/"
    "sequential_identity_review"
)
REPORT_PATH = (
    OUTPUT_DIR
    / "possession_001_sequential_identity_candidates.json"
)
CANDIDATE_MONTAGE_DIR = OUTPUT_DIR / "candidate_pairs"
BLOCKED_MONTAGE_DIR = OUTPUT_DIR / "blocked_controls"


MAX_REVIEW_APPEARANCE_DISTANCE = 0.30
STRONG_APPEARANCE_DISTANCE = 0.12
MODERATE_APPEARANCE_DISTANCE = 0.20
REPRESENTATIVE_WINDOW_FRAMES = 10

FULL_TILE_SIZE = (460, 259)
ZOOM_TILE_SIZE = (460, 360)
ZOOM_PADDING_X = 100
ZOOM_PADDING_Y = 80

EARLIER_COLOR = (0, 215, 255)
LATER_COLOR = (255, 80, 220)
OTHER_COLOR = (105, 105, 105)
BLOCKED_COLOR = (40, 40, 255)
TEXT_COLOR = (255, 255, 255)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Generate evidence for identity fragments that occur "
            "in separate time windows."
        )
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help=(
            "Write the JSON report without reading the source "
            "video or creating montages."
        ),
    )
    return parser.parse_args()


def load_json(path):
    with path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def load_rows(path):
    rows_by_frame = defaultdict(list)
    rows_by_identity = defaultdict(list)

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as input_file:
        for row in csv.DictReader(input_file):
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

            rows_by_frame[parsed["frame_index"]].append(parsed)
            rows_by_identity[parsed["player_id"]].append(parsed)

    for rows in rows_by_frame.values():
        rows.sort(key=lambda row: row["player_id"])

    for rows in rows_by_identity.values():
        rows.sort(key=lambda row: row["frame_index"])

    return dict(rows_by_frame), dict(rows_by_identity)


def load_prototypes(path):
    with np.load(path) as archive:
        prototypes = {}

        for segment_id, prototype, sample_count in zip(
            archive["segment_ids"],
            archive["prototypes"],
            archive["sample_counts"],
        ):
            normalized = normalize(prototype.astype(np.float32))
            prototypes[str(segment_id)] = {
                "prototype": normalized,
                "sample_count": int(sample_count),
            }

    return prototypes


def normalize(vector):
    norm = float(np.linalg.norm(vector))

    if norm <= 0:
        return vector.copy()

    return vector / norm


def cosine_distance(first, second):
    return 1.0 - float(np.dot(first, second))


def teams_are_compatible(first, second):
    return (
        first == "unknown"
        or second == "unknown"
        or first == second
    )


def aggregate_identity_prototype(identity, prototypes):
    weighted = []
    total_weight = 0

    for segment_id in identity["segment_ids"]:
        record = prototypes.get(segment_id)

        if record is None:
            continue

        weight = record["sample_count"]
        weighted.append(record["prototype"] * weight)
        total_weight += weight

    if not weighted or total_weight <= 0:
        return None

    return normalize(sum(weighted) / total_weight)


def segment_appearance_metrics(first, second, prototypes):
    distances = []

    for first_segment in first["segment_ids"]:
        first_record = prototypes.get(first_segment)

        if first_record is None:
            continue

        for second_segment in second["segment_ids"]:
            second_record = prototypes.get(second_segment)

            if second_record is None:
                continue

            distances.append(
                {
                    "first_segment_id": first_segment,
                    "second_segment_id": second_segment,
                    "appearance_distance": cosine_distance(
                        first_record["prototype"],
                        second_record["prototype"],
                    ),
                }
            )

    distances.sort(
        key=lambda record: (
            record["appearance_distance"],
            record["first_segment_id"],
            record["second_segment_id"],
        )
    )
    return distances


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


def appearance_band(distance):
    if distance is None:
        return "unavailable"

    if distance <= STRONG_APPEARANCE_DISTANCE:
        return "strong"

    if distance <= MODERATE_APPEARANCE_DISTANCE:
        return "moderate"

    if distance <= MAX_REVIEW_APPEARANCE_DISTANCE:
        return "weak"

    return "screened_out"


def identities_cooccur(first_player_id, second_player_id, frame_sets):
    return bool(
        frame_sets[first_player_id]
        & frame_sets[second_player_id]
    )


def chronological_order(first, second):
    if first["last_frame"] < second["first_frame"]:
        return first, second

    if second["last_frame"] < first["first_frame"]:
        return second, first

    return None


def manual_blockers(first, second, reid_review):
    blockers = []
    first_segments = set(first["segment_ids"])
    second_segments = set(second["segment_ids"])

    for rejection in reid_review.get(
        "manual_match_decisions",
        {},
    ).get("reject", []):
        source_segment = rejection["source_segment_id"]
        target_segment = rejection["target_segment_id"]

        if (
            source_segment in first_segments
            and target_segment in second_segments
        ) or (
            target_segment in first_segments
            and source_segment in second_segments
        ):
            blockers.append(
                {
                    "type": "rejected_segment_match",
                    "source_segment_id": source_segment,
                    "target_segment_id": target_segment,
                    "reason": rejection["reason"],
                }
            )

    shared_tracks = set(first["raw_track_ids"]) & set(
        second["raw_track_ids"]
    )
    manual_splits = reid_review.get(
        "manual_split_after_frames",
        {},
    )

    for track_id in sorted(shared_tracks):
        for split_after_frame in manual_splits.get(
            str(track_id),
            [],
        ):
            if (
                first["last_frame"] <= split_after_frame
                and second["first_frame"] > split_after_frame
            ):
                blockers.append(
                    {
                        "type": "reviewed_track_identity_switch",
                        "track_id": track_id,
                        "split_after_frame": split_after_frame,
                        "reason": (
                            "Visual review established that this raw "
                            "track ID changes players at the boundary."
                        ),
                    }
                )

    unique = []
    seen = set()

    for blocker in blockers:
        key = json.dumps(blocker, sort_keys=True)

        if key not in seen:
            seen.add(key)
            unique.append(blocker)

    return unique


def best_row_near(rows, target_frame):
    nearby = [
        row
        for row in rows
        if abs(row["frame_index"] - target_frame)
        <= REPRESENTATIVE_WINDOW_FRAMES
    ]

    if not nearby:
        nearby = rows

    return max(
        nearby,
        key=lambda row: (
            row["confidence"],
            -abs(row["frame_index"] - target_frame),
            row["frame_index"],
        ),
    )


def choose_review_rows(first_rows, second_rows):
    first_middle = (
        first_rows[0]["frame_index"]
        + first_rows[-1]["frame_index"]
    ) // 2
    second_middle = (
        second_rows[0]["frame_index"]
        + second_rows[-1]["frame_index"]
    ) // 2
    chosen = [
        ("EARLIER representative", best_row_near(
            first_rows,
            first_middle,
        )),
        ("EARLIER endpoint", first_rows[-1]),
        ("LATER endpoint", second_rows[0]),
        ("LATER representative", best_row_near(
            second_rows,
            second_middle,
        )),
    ]
    result = []
    seen = set()

    for role, row in chosen:
        key = (role.split()[0], row["frame_index"])

        if key in seen:
            continue

        seen.add(key)
        result.append(
            {
                "role": role,
                "player_id": row["player_id"],
                "frame_index": row["frame_index"],
                "confidence": row["confidence"],
            }
        )

    return result


def candidate_record(
    first,
    second,
    rows_by_identity,
    prototypes,
    reid_review,
):
    first_rows = rows_by_identity[first["player_id"]]
    second_rows = rows_by_identity[second["player_id"]]
    first_prototype = aggregate_identity_prototype(
        first,
        prototypes,
    )
    second_prototype = aggregate_identity_prototype(
        second,
        prototypes,
    )
    aggregate_distance = None

    if first_prototype is not None and second_prototype is not None:
        aggregate_distance = cosine_distance(
            first_prototype,
            second_prototype,
        )

    segment_distances = segment_appearance_metrics(
        first,
        second,
        prototypes,
    )
    first_endpoint = first_rows[-1]
    second_endpoint = second_rows[0]

    return {
        "first_player_id": first["player_id"],
        "second_player_id": second["player_id"],
        "first_team": first["team_label"],
        "second_team": second["team_label"],
        "first_start_frame": first_rows[0]["frame_index"],
        "first_end_frame": first_endpoint["frame_index"],
        "second_start_frame": second_endpoint["frame_index"],
        "second_end_frame": second_rows[-1]["frame_index"],
        "missing_frame_count": (
            second_endpoint["frame_index"]
            - first_endpoint["frame_index"]
            - 1
        ),
        "first_segment_ids": list(first["segment_ids"]),
        "second_segment_ids": list(second["segment_ids"]),
        "aggregate_appearance_distance": aggregate_distance,
        "appearance_band": appearance_band(aggregate_distance),
        "minimum_segment_appearance": (
            segment_distances[0]
            if segment_distances
            else None
        ),
        "segment_appearance_pairs": segment_distances,
        "endpoint_floor_distance": floor_distance(
            first_endpoint,
            second_endpoint,
        ),
        "endpoint_box_iou": bounding_box_iou(
            first_endpoint,
            second_endpoint,
        ),
        "manual_blockers": manual_blockers(
            first,
            second,
            reid_review,
        ),
        "review_frames": choose_review_rows(
            first_rows,
            second_rows,
        ),
    }


def build_candidates(
    mapping_report,
    rows_by_identity,
    prototypes,
    reid_review,
):
    identities = [
        identity
        for identity in mapping_report["identities"]
        if identity["player_id"] in rows_by_identity
    ]
    frame_sets = {
        player_id: {
            row["frame_index"]
            for row in rows
        }
        for player_id, rows in rows_by_identity.items()
    }
    possible = []

    for left, right in itertools.combinations(identities, 2):
        if not teams_are_compatible(
            left["team_label"],
            right["team_label"],
        ):
            continue

        if identities_cooccur(
            left["player_id"],
            right["player_id"],
            frame_sets,
        ):
            continue

        ordered = chronological_order(left, right)

        if ordered is None:
            continue

        possible.append(
            candidate_record(
                ordered[0],
                ordered[1],
                rows_by_identity,
                prototypes,
                reid_review,
            )
        )

    possible.sort(
        key=lambda record: (
            record["aggregate_appearance_distance"] is None,
            record["aggregate_appearance_distance"]
            if record["aggregate_appearance_distance"] is not None
            else float("inf"),
            record["missing_frame_count"],
            record["first_player_id"],
            record["second_player_id"],
        )
    )
    review_candidates = []
    blocked_controls = []
    screened_out = []

    for record in possible:
        distance = record["aggregate_appearance_distance"]

        if record["manual_blockers"]:
            blocked_controls.append(record)
        elif (
            distance is None
            or distance > MAX_REVIEW_APPEARANCE_DISTANCE
        ):
            screened_out.append(record)
        else:
            review_candidates.append(record)

    for index, record in enumerate(review_candidates, 1):
        record["candidate_id"] = f"sequential_{index:03d}"
        record["decision_status"] = "needs_visual_review"
        record["conflicts_with"] = []

    for index, record in enumerate(blocked_controls, 1):
        record["candidate_id"] = f"blocked_{index:03d}"
        record["decision_status"] = "blocked_by_prior_review"
        record["conflicts_with"] = []

    add_candidate_conflicts(
        review_candidates,
        frame_sets,
        reid_review,
        identities,
    )
    return review_candidates, blocked_controls, screened_out


def add_candidate_conflicts(
    candidates,
    frame_sets,
    reid_review,
    identities,
):
    identities_by_id = {
        identity["player_id"]: identity
        for identity in identities
    }

    for first, second in itertools.combinations(candidates, 2):
        first_members = {
            first["first_player_id"],
            first["second_player_id"],
        }
        second_members = {
            second["first_player_id"],
            second["second_player_id"],
        }

        if not first_members & second_members:
            continue

        combined = sorted(first_members | second_members)
        incompatible = False

        for left_id, right_id in itertools.combinations(combined, 2):
            if identities_cooccur(left_id, right_id, frame_sets):
                incompatible = True
                break

            ordered = chronological_order(
                identities_by_id[left_id],
                identities_by_id[right_id],
            )

            if ordered is not None and manual_blockers(
                ordered[0],
                ordered[1],
                reid_review,
            ):
                incompatible = True
                break

        if incompatible:
            first["conflicts_with"].append(second["candidate_id"])
            second["conflicts_with"].append(first["candidate_id"])


def build_report(
    mapping_report,
    review_candidates,
    blocked_controls,
    screened_out,
):
    return {
        "reconciled_tracks": str(RECONCILED_TRACKS_PATH),
        "identity_mapping": str(MAPPING_PATH),
        "segment_prototypes": str(PROTOTYPES_PATH),
        "reid_review_config": str(REID_REVIEW_PATH),
        "settings": {
            "maximum_review_appearance_distance": (
                MAX_REVIEW_APPEARANCE_DISTANCE
            ),
            "strong_appearance_distance": (
                STRONG_APPEARANCE_DISTANCE
            ),
            "moderate_appearance_distance": (
                MODERATE_APPEARANCE_DISTANCE
            ),
        },
        "summary": {
            "current_identity_cluster_count": mapping_report[
                "summary"
            ]["identity_cluster_count"],
            "review_candidate_count": len(review_candidates),
            "blocked_control_count": len(blocked_controls),
            "screened_out_pair_count": len(screened_out),
        },
        "interpretation": {
            "lower_appearance_distance": (
                "More similar clothing and visual appearance."
            ),
            "missing_frame_count": (
                "The number of frames with neither endpoint linking "
                "the two fragments; long gaps weaken motion evidence."
            ),
            "blocked_controls": (
                "Pairs retained for audit because their appearance "
                "looks similar, but a prior visual identity-switch "
                "decision prevents merging them."
            ),
            "conflicts_with": (
                "Both candidates cannot be accepted because doing so "
                "would join identities known to co-occur or differ."
            ),
        },
        "decision_guide": {
            "same_identity": (
                "The earlier and later fragments show the same player."
            ),
            "different_identity": (
                "The fragments show different players."
            ),
            "uncertain": (
                "The images do not support a safe decision."
            ),
        },
        "review_candidates": review_candidates,
        "blocked_controls": blocked_controls,
        "screened_out_pairs": screened_out,
    }


def annotate_frame(frame, rows, target_player_id, color):
    annotated = frame.copy()

    for row in rows:
        row_color = (
            color
            if row["player_id"] == target_player_id
            else OTHER_COLOR
        )
        thickness = 5 if row["player_id"] == target_player_id else 1
        residual.draw_label(
            annotated,
            row,
            row_color,
            thickness,
        )

    return annotated


def find_player_row(rows, player_id):
    return next(
        row
        for row in rows
        if row["player_id"] == player_id
    )


def player_zoom(image, row):
    image_height, image_width = image.shape[:2]
    x1 = max(
        0,
        int(math.floor(row["x1"] - ZOOM_PADDING_X)),
    )
    y1 = max(
        0,
        int(math.floor(row["y1"] - ZOOM_PADDING_Y)),
    )
    x2 = min(
        image_width,
        int(math.ceil(row["x2"] + ZOOM_PADDING_X)),
    )
    y2 = min(
        image_height,
        int(math.ceil(row["y2"] + ZOOM_PADDING_Y)),
    )
    return image[y1:y2, x1:x2]


def create_montage(candidate, frames, rows_by_frame):
    full_tiles = []
    zoom_tiles = []

    for review_frame in candidate["review_frames"]:
        frame_index = review_frame["frame_index"]
        player_id = review_frame["player_id"]
        rows = rows_by_frame[frame_index]
        is_earlier = review_frame["role"].startswith("EARLIER")
        color = EARLIER_COLOR if is_earlier else LATER_COLOR
        annotated = annotate_frame(
            frames[frame_index],
            rows,
            player_id,
            color,
        )
        row = find_player_row(rows, player_id)
        header = (
            f"{review_frame['role']} | {player_id} | "
            f"frame {frame_index} | conf={row['confidence']:.2f}"
        )
        full_tiles.append(
            residual.add_header(
                residual.fit_to_tile(
                    annotated,
                    FULL_TILE_SIZE,
                ),
                header,
                color,
            )
        )
        zoom_tiles.append(
            residual.add_header(
                residual.fit_to_tile(
                    player_zoom(annotated, row),
                    ZOOM_TILE_SIZE,
                ),
                f"ZOOM | {header}",
                color,
            )
        )

    full_row = np.hstack(full_tiles)
    zoom_row = np.hstack(zoom_tiles)
    distance = candidate["aggregate_appearance_distance"]
    distance_text = f"{distance:.3f}" if distance is not None else "n/a"
    conflict_text = (
        ", ".join(candidate["conflicts_with"])
        if candidate["conflicts_with"]
        else "none"
    )
    blocked = bool(candidate["manual_blockers"])
    title_color = BLOCKED_COLOR if blocked else EARLIER_COLOR
    status_line = (
        "BLOCKED CONTROL: prior visual review says do not merge"
        if blocked
        else (
            "Decision: same_identity / different_identity / "
            "uncertain"
        )
    )
    title = residual.title_panel(
        full_row.shape[1],
        [
            (
                f"{candidate['candidate_id']} | YELLOW earlier "
                f"{candidate['first_player_id']} -> MAGENTA later "
                f"{candidate['second_player_id']}"
            ),
            (
                f"appearance={distance_text} "
                f"({candidate['appearance_band']}) | "
                f"missing frames={candidate['missing_frame_count']} | "
                "endpoint floor distance="
                f"{candidate['endpoint_floor_distance']:.1f}px | "
                f"conflicts={conflict_text}"
            ),
            status_line,
        ],
        title_color,
    )
    return np.vstack([title, full_row, zoom_row])


def read_frames(frame_indices):
    capture = residual.cv2.VideoCapture(str(VIDEO_PATH))

    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {VIDEO_PATH}")

    frames = {}

    try:
        for frame_index in sorted(frame_indices):
            capture.set(
                residual.cv2.CAP_PROP_POS_FRAMES,
                frame_index,
            )
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


def write_montage(path, montage):
    path.parent.mkdir(parents=True, exist_ok=True)
    success = residual.cv2.imwrite(
        str(path),
        montage,
        [residual.cv2.IMWRITE_JPEG_QUALITY, 95],
    )

    if not success:
        raise RuntimeError(f"Could not write: {path}")


def generate_montages(
    review_candidates,
    blocked_controls,
    rows_by_frame,
):
    records = review_candidates + blocked_controls
    requested_frames = {
        review_frame["frame_index"]
        for record in records
        for review_frame in record["review_frames"]
    }
    frames = read_frames(requested_frames)

    print("\nGenerating sequential identity review montages...")

    for record in records:
        montage = create_montage(
            record,
            frames,
            rows_by_frame,
        )
        filename = (
            f"{record['candidate_id']}_"
            f"{record['first_player_id']}__"
            f"{record['second_player_id']}.jpg"
        )
        output_dir = (
            BLOCKED_MONTAGE_DIR
            if record["manual_blockers"]
            else CANDIDATE_MONTAGE_DIR
        )
        output_path = output_dir / filename
        write_montage(output_path, montage)
        print(f"  Saved: {output_path}")


def print_candidate(record):
    distance = record["aggregate_appearance_distance"]
    distance_text = f"{distance:.3f}" if distance is not None else "n/a"
    conflict_text = (
        ",".join(record["conflicts_with"])
        if record["conflicts_with"]
        else "none"
    )
    print(
        f"  {record['candidate_id']}: "
        f"{record['first_player_id']} -> "
        f"{record['second_player_id']} | "
        f"gap={record['missing_frame_count']} | "
        f"appearance={distance_text} "
        f"({record['appearance_band']}) | "
        f"conflicts={conflict_text}"
    )


def main():
    args = parse_args()
    required_paths = [
        RECONCILED_TRACKS_PATH,
        MAPPING_PATH,
        PROTOTYPES_PATH,
        REID_REVIEW_PATH,
    ]

    for path in required_paths:
        if not path.exists():
            raise FileNotFoundError(f"Required input not found: {path}")

    if not args.report_only and not VIDEO_PATH.exists():
        raise FileNotFoundError(f"Video not found: {VIDEO_PATH}")

    if not args.report_only and residual.cv2 is None:
        raise ModuleNotFoundError(
            "OpenCV is required to generate review montages. "
            "Install opencv-python or run with --report-only."
        )

    rows_by_frame, rows_by_identity = load_rows(
        RECONCILED_TRACKS_PATH
    )
    mapping_report = load_json(MAPPING_PATH)
    prototypes = load_prototypes(PROTOTYPES_PATH)
    reid_review = load_json(REID_REVIEW_PATH)
    review_candidates, blocked_controls, screened_out = (
        build_candidates(
            mapping_report,
            rows_by_identity,
            prototypes,
            reid_review,
        )
    )
    report = build_report(
        mapping_report,
        review_candidates,
        blocked_controls,
        screened_out,
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with REPORT_PATH.open("w", encoding="utf-8") as output_file:
        json.dump(report, output_file, indent=2)
        output_file.write("\n")

    if not args.report_only:
        generate_montages(
            review_candidates,
            blocked_controls,
            rows_by_frame,
        )

    print("\nSequential identity review preparation complete.")
    print(
        "Current identity clusters: "
        f"{mapping_report['summary']['identity_cluster_count']}"
    )
    print(f"Review candidates: {len(review_candidates)}")
    print(f"Blocked controls: {len(blocked_controls)}")
    print(f"Screened-out pairs: {len(screened_out)}")
    print("\nReview candidates:")

    for record in review_candidates:
        print_candidate(record)

    print("\nBlocked controls (do not merge):")

    for record in blocked_controls:
        print_candidate(record)

    print(f"\nCandidate report saved to: {REPORT_PATH}")

    if args.report_only:
        print("Montages skipped because --report-only was supplied.")
    else:
        print(f"Review montages saved under: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
