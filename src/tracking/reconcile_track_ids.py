import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np


CLASSIFIED_TRACKS_PATH = Path(
    "data/outputs/classification/"
    "possession_001_team_classified_tracks.csv"
)

SEGMENTS_REPORT_PATH = Path(
    "data/outputs/reid/"
    "possession_001_reid_segments.json"
)

SEGMENT_PROTOTYPES_PATH = Path(
    "data/outputs/reid/"
    "possession_001_reid_segment_prototypes.npz"
)

OUTPUT_PATH = Path(
    "data/outputs/reid/"
    "possession_001_segment_match_candidates.json"
)

REVIEW_CONFIG_PATH = Path(
    "configs/possession_001_reid_review.json"
)


MAX_SEGMENT_OVERLAP_FRAMES = 30
MAX_SEGMENT_GAP_FRAMES = 30
MAX_APPEARANCE_DISTANCE = 0.18
MAX_ENDPOINT_FLOOR_DISTANCE = 120.0
MIN_ENDPOINT_BOX_IOU = 0.15

MIN_DUPLICATE_MEDIAN_IOU = 0.45
MAX_DUPLICATE_MEDIAN_DISTANCE = 45.0

STRICT_MAX_APPEARANCE_DISTANCE = 0.14
STRICT_MAX_FRAME_GAP = 10
STRICT_MAX_FLOOR_DISTANCE = 90.0
STRICT_MIN_BOX_IOU = 0.20


def cosine_distance(first, second):
    return 1.0 - float(
        np.dot(first, second)
    )


def floor_distance(first, second):
    return math.hypot(
        first["floor_x"]
        - second["floor_x"],
        first["floor_y"]
        - second["floor_y"],
    )


def bounding_box_iou(first, second):
    intersection_x1 = max(
        first["x1"],
        second["x1"],
    )
    intersection_y1 = max(
        first["y1"],
        second["y1"],
    )
    intersection_x2 = min(
        first["x2"],
        second["x2"],
    )
    intersection_y2 = min(
        first["y2"],
        second["y2"],
    )

    intersection_width = max(
        0.0,
        intersection_x2 - intersection_x1,
    )
    intersection_height = max(
        0.0,
        intersection_y2 - intersection_y1,
    )

    intersection_area = (
        intersection_width
        * intersection_height
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

    union_area = (
        first_area
        + second_area
        - intersection_area
    )

    if union_area <= 0:
        return 0.0

    return intersection_area / union_area


def teams_are_compatible(first, second):
    if first == "unknown":
        return True

    if second == "unknown":
        return True

    return first == second


# ---------------------------------------------------------
# Load raw classified tracking rows
# ---------------------------------------------------------

if not CLASSIFIED_TRACKS_PATH.exists():
    raise FileNotFoundError(
        "Classified tracks not found: "
        f"{CLASSIFIED_TRACKS_PATH}"
    )

rows_by_track = defaultdict(list)

with CLASSIFIED_TRACKS_PATH.open(
    "r",
    newline="",
    encoding="utf-8",
) as input_file:
    reader = csv.DictReader(input_file)

    for row in reader:
        parsed = {
            "frame_index": int(
                row["frame_index"]
            ),
            "track_id": int(
                row["track_id"]
            ),
            "team_label": row[
                "team_label"
            ],
            "x1": float(row["x1"]),
            "y1": float(row["y1"]),
            "x2": float(row["x2"]),
            "y2": float(row["y2"]),
            "floor_x": float(
                row["floor_x"]
            ),
            "floor_y": float(
                row["floor_y"]
            ),
        }

        rows_by_track[
            parsed["track_id"]
        ].append(parsed)

for rows in rows_by_track.values():
    rows.sort(
        key=lambda row: row["frame_index"]
    )


# ---------------------------------------------------------
# Load temporal segment records
# ---------------------------------------------------------

if not SEGMENTS_REPORT_PATH.exists():
    raise FileNotFoundError(
        "Segment report not found: "
        f"{SEGMENTS_REPORT_PATH}"
    )

with SEGMENTS_REPORT_PATH.open(
    "r",
    encoding="utf-8",
) as input_file:
    segment_report = json.load(
        input_file
    )

segment_records = segment_report[
    "segments"
]


# ---------------------------------------------------------
# Load reviewed match decisions
# ---------------------------------------------------------

review_config = {}

if REVIEW_CONFIG_PATH.exists():
    with REVIEW_CONFIG_PATH.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        review_config = json.load(input_file)

match_decisions = review_config.get(
    "manual_match_decisions",
    {},
)

manual_accept_records_by_pair = {
    (
        item["source_segment_id"],
        item["target_segment_id"],
    ): item
    for item in match_decisions.get(
        "accept",
        [],
    )
}

manual_accept_pairs = set(
    manual_accept_records_by_pair
)

manual_reject_pairs = {
    (
        item["source_segment_id"],
        item["target_segment_id"],
    )
    for item in match_decisions.get(
        "reject",
        [],
    )
}

conflicting_decisions = (
    manual_accept_pairs
    & manual_reject_pairs
)

if conflicting_decisions:
    raise ValueError(
        "Match pairs cannot be both accepted "
        "and rejected: "
        f"{sorted(conflicting_decisions)}"
    )


# ---------------------------------------------------------
# Load matching segment prototypes
# ---------------------------------------------------------

if not SEGMENT_PROTOTYPES_PATH.exists():
    raise FileNotFoundError(
        "Segment prototypes not found: "
        f"{SEGMENT_PROTOTYPES_PATH}"
    )

prototype_data = np.load(
    SEGMENT_PROTOTYPES_PATH,
    allow_pickle=False,
)

prototype_by_segment = {
    str(segment_id): prototype
    for segment_id, prototype in zip(
        prototype_data["segment_ids"],
        prototype_data["prototypes"],
    )
}


# ---------------------------------------------------------
# Assign raw tracking rows to temporal segments
# ---------------------------------------------------------

segments_by_track = defaultdict(list)

for segment in segment_records:
    segments_by_track[
        int(segment["track_id"])
    ].append(segment)

for track_segments in (
    segments_by_track.values()
):
    track_segments.sort(
        key=lambda segment: (
            segment["start_frame"]
        )
    )

segment_rows = {}

for track_id, track_segments in (
    segments_by_track.items()
):
    raw_rows = rows_by_track.get(
        track_id,
        [],
    )

    if not raw_rows:
        continue

    track_first_frame = raw_rows[0][
        "frame_index"
    ]
    track_last_frame = raw_rows[-1][
        "frame_index"
    ]

    boundaries = []

    for first_segment, second_segment in zip(
        track_segments,
        track_segments[1:],
    ):
        first_end_override = (
            first_segment.get(
                "raw_end_frame_override"
            )
        )
        second_start_override = (
            second_segment.get(
                "raw_start_frame_override"
            )
        )

        if (
            first_end_override is not None
            and second_start_override is not None
            and int(second_start_override)
            != int(first_end_override) + 1
        ):
            raise ValueError(
                "Conflicting reviewed raw-frame "
                "segment boundaries: "
                f"{first_segment['segment_id']} -> "
                f"{second_segment['segment_id']}"
            )

        if first_end_override is not None:
            boundary = int(
                first_end_override
            )
        elif second_start_override is not None:
            boundary = (
                int(second_start_override) - 1
            )
        else:
            boundary = (
                int(first_segment["end_frame"])
                + int(
                    second_segment["start_frame"]
                )
            ) // 2

        boundaries.append(boundary)

    for index, segment in enumerate(
        track_segments
    ):
        if index == 0:
            lower_frame = track_first_frame
        else:
            lower_frame = (
                boundaries[index - 1] + 1
            )

        if index == len(track_segments) - 1:
            upper_frame = track_last_frame
        else:
            upper_frame = boundaries[index]

        assigned_rows = [
            row
            for row in raw_rows
            if (
                lower_frame
                <= row["frame_index"]
                <= upper_frame
            )
        ]

        segment_id = segment["segment_id"]

        segment_rows[segment_id] = (
            assigned_rows
        )

        segment["raw_start_frame"] = (
            assigned_rows[0]["frame_index"]
            if assigned_rows
            else lower_frame
        )

        segment["raw_end_frame"] = (
            assigned_rows[-1]["frame_index"]
            if assigned_rows
            else upper_frame
        )


# ---------------------------------------------------------
# Generate constrained segment-match candidates
# ---------------------------------------------------------

candidates = []
rejections = defaultdict(int)

for source in segment_records:
    source_id = source["segment_id"]
    source_rows = segment_rows.get(
        source_id,
        [],
    )

    if not source_rows:
        continue

    source_prototype = (
        prototype_by_segment[source_id]
    )

    for target in segment_records:
        target_id = target["segment_id"]

        if source_id == target_id:
            continue

        target_rows = segment_rows.get(
            target_id,
            [],
        )

        if not target_rows:
            continue

        # Preserve temporal direction.
        if (
            target["raw_start_frame"]
            < source["raw_start_frame"]
        ):
            continue

        source_team = source["team_label"]
        target_team = target["team_label"]

        if not teams_are_compatible(
            source_team,
            target_team,
        ):
            rejections[
                "opposing_team"
            ] += 1
            continue

        source_end = source_rows[-1]
        target_start = target_rows[0]

        frame_delta = (
            target_start["frame_index"]
            - source_end["frame_index"]
        )

        if (
            frame_delta
            < -MAX_SEGMENT_OVERLAP_FRAMES
            or frame_delta
            > MAX_SEGMENT_GAP_FRAMES
        ):
            rejections[
                "outside_time_window"
            ] += 1
            continue

        appearance_distance = (
            cosine_distance(
                source_prototype,
                prototype_by_segment[
                    target_id
                ],
            )
        )

        if (
            appearance_distance
            > MAX_APPEARANCE_DISTANCE
        ):
            rejections[
                "appearance_too_different"
            ] += 1
            continue

        endpoint_distance = floor_distance(
            source_end,
            target_start,
        )

        endpoint_iou = bounding_box_iou(
            source_end,
            target_start,
        )

        source_rows_by_frame = {
            row["frame_index"]: row
            for row in source_rows
        }

        target_rows_by_frame = {
            row["frame_index"]: row
            for row in target_rows
        }

        common_frames = sorted(
            set(source_rows_by_frame)
            & set(target_rows_by_frame)
        )

        duplicate_median_iou = None
        duplicate_median_distance = None
        duplicate_geometry = False

        if common_frames:
            overlap_ious = []
            overlap_distances = []

            for frame_index in common_frames:
                source_row = (
                    source_rows_by_frame[
                        frame_index
                    ]
                )
                target_row = (
                    target_rows_by_frame[
                        frame_index
                    ]
                )

                overlap_ious.append(
                    bounding_box_iou(
                        source_row,
                        target_row,
                    )
                )

                overlap_distances.append(
                    floor_distance(
                        source_row,
                        target_row,
                    )
                )

            duplicate_median_iou = float(
                np.median(overlap_ious)
            )

            duplicate_median_distance = float(
                np.median(
                    overlap_distances
                )
            )

            duplicate_geometry = (
                duplicate_median_iou
                >= MIN_DUPLICATE_MEDIAN_IOU
                or duplicate_median_distance
                <= MAX_DUPLICATE_MEDIAN_DISTANCE
            )

            if not duplicate_geometry:
                rejections[
                    "simultaneous_distinct_tracks"
                ] += 1
                continue

        else:
            if (
                endpoint_distance
                > MAX_ENDPOINT_FLOOR_DISTANCE
            ):
                rejections[
                    "endpoint_too_far"
                ] += 1
                continue

            if (
                endpoint_iou
                < MIN_ENDPOINT_BOX_IOU
            ):
                rejections[
                    "endpoint_iou_too_low"
                ] += 1
                continue

        if common_frames:
            matching_distance = (
                duplicate_median_distance
            )
            matching_iou = (
                duplicate_median_iou
            )

            score = (
                appearance_distance * 100.0
                + matching_distance
                - matching_iou * 40.0
            )
        else:
            matching_distance = (
                endpoint_distance
            )
            matching_iou = endpoint_iou

            score = (
                appearance_distance * 100.0
                + endpoint_distance
                + abs(frame_delta) * 3.0
                - endpoint_iou * 40.0
            )

        if common_frames:
            strict_accept = (
                appearance_distance
                <= STRICT_MAX_APPEARANCE_DISTANCE
                and duplicate_geometry
            )

            match_type = (
                "duplicate_overlap"
            )

        else:
            strict_accept = (
                appearance_distance
                <= STRICT_MAX_APPEARANCE_DISTANCE
                and 0 <= frame_delta
                <= STRICT_MAX_FRAME_GAP
                and endpoint_distance
                <= STRICT_MAX_FLOOR_DISTANCE
                and endpoint_iou
                >= STRICT_MIN_BOX_IOU
            )

            match_type = (
                "sequential_handoff"
            )

        candidates.append(
            {
                "source_segment_id": (
                    source_id
                ),
                "target_segment_id": (
                    target_id
                ),
                "source_track_id": int(
                    source["track_id"]
                ),
                "target_track_id": int(
                    target["track_id"]
                ),
                "source_team": source_team,
                "target_team": target_team,
                "match_type": match_type,
                "strict_accept": (
                    strict_accept
                ),
                "source_end_frame": (
                    source_end[
                        "frame_index"
                    ]
                ),
                "target_start_frame": (
                    target_start[
                        "frame_index"
                    ]
                ),
                "frame_delta": frame_delta,
                "appearance_distance": (
                    appearance_distance
                ),
                "endpoint_floor_distance": (
                    endpoint_distance
                ),
                "endpoint_box_iou": (
                    endpoint_iou
                ),
                "overlapping_frame_count": (
                    len(common_frames)
                ),
                "duplicate_median_iou": (
                    duplicate_median_iou
                ),
                "duplicate_median_distance": (
                    duplicate_median_distance
                ),
                "matching_floor_distance": (
                    matching_distance
                ),
                "matching_box_iou": (
                    matching_iou
                ),
                "score": score,
            }
        )


# ---------------------------------------------------------
# Add explicitly reviewed accepts outside auto thresholds
# ---------------------------------------------------------

segment_by_id = {
    segment["segment_id"]: segment
    for segment in segment_records
}
generated_candidate_pairs = {
    (
        candidate["source_segment_id"],
        candidate["target_segment_id"],
    )
    for candidate in candidates
}

for pair, decision_record in (
    manual_accept_records_by_pair.items()
):
    if pair in generated_candidate_pairs:
        continue

    if not decision_record.get(
        "allow_outside_candidate",
        False,
    ):
        continue

    source_id, target_id = pair

    if source_id not in segment_by_id:
        raise ValueError(
            "Reviewed outside-candidate accept refers to an "
            f"unknown source segment: {source_id}"
        )

    if target_id not in segment_by_id:
        raise ValueError(
            "Reviewed outside-candidate accept refers to an "
            f"unknown target segment: {target_id}"
        )

    source = segment_by_id[source_id]
    target = segment_by_id[target_id]
    source_rows = segment_rows.get(source_id, [])
    target_rows = segment_rows.get(target_id, [])

    if not source_rows or not target_rows:
        raise ValueError(
            "Reviewed outside-candidate accept has no assigned "
            f"rows: {source_id} -> {target_id}"
        )

    if not teams_are_compatible(
        source["team_label"],
        target["team_label"],
    ):
        raise ValueError(
            "Reviewed outside-candidate accepts require "
            "compatible corrected segment teams: "
            f"{source_id} ({source['team_label']}) -> "
            f"{target_id} ({target['team_label']})"
        )

    source_end = source_rows[-1]
    target_start = target_rows[0]
    frame_delta = (
        target_start["frame_index"]
        - source_end["frame_index"]
    )
    appearance_distance = cosine_distance(
        prototype_by_segment[source_id],
        prototype_by_segment[target_id],
    )
    endpoint_distance = floor_distance(
        source_end,
        target_start,
    )
    endpoint_iou = bounding_box_iou(
        source_end,
        target_start,
    )
    source_rows_by_frame = {
        row["frame_index"]: row
        for row in source_rows
    }
    target_rows_by_frame = {
        row["frame_index"]: row
        for row in target_rows
    }
    common_frames = sorted(
        set(source_rows_by_frame)
        & set(target_rows_by_frame)
    )
    duplicate_median_iou = None
    duplicate_median_distance = None

    if common_frames:
        duplicate_median_iou = float(
            np.median(
                [
                    bounding_box_iou(
                        source_rows_by_frame[frame_index],
                        target_rows_by_frame[frame_index],
                    )
                    for frame_index in common_frames
                ]
            )
        )
        duplicate_median_distance = float(
            np.median(
                [
                    floor_distance(
                        source_rows_by_frame[frame_index],
                        target_rows_by_frame[frame_index],
                    )
                    for frame_index in common_frames
                ]
            )
        )

        if (
            duplicate_median_iou
            < MIN_DUPLICATE_MEDIAN_IOU
            and duplicate_median_distance
            > MAX_DUPLICATE_MEDIAN_DISTANCE
        ):
            raise ValueError(
                "Reviewed outside-candidate duplicate lacks "
                "overlap evidence: "
                f"{source_id} -> {target_id}"
            )

        match_type = "reviewed_duplicate_overlap"
        matching_distance = duplicate_median_distance
        matching_iou = duplicate_median_iou
        score = (
            appearance_distance * 100.0
            + matching_distance
            - matching_iou * 40.0
        )
    else:
        if (
            frame_delta < 0
            or frame_delta > MAX_SEGMENT_GAP_FRAMES
        ):
            raise ValueError(
                "Reviewed outside-candidate handoff is not "
                "temporally adjacent: "
                f"{source_id} -> {target_id} "
                f"(frame delta {frame_delta})"
            )

        match_type = "reviewed_sequential_handoff"
        matching_distance = endpoint_distance
        matching_iou = endpoint_iou
        score = (
            appearance_distance * 100.0
            + endpoint_distance
            + abs(frame_delta) * 3.0
            - endpoint_iou * 40.0
        )

    candidates.append(
        {
            "source_segment_id": source_id,
            "target_segment_id": target_id,
            "source_track_id": int(source["track_id"]),
            "target_track_id": int(target["track_id"]),
            "source_team": source["team_label"],
            "target_team": target["team_label"],
            "match_type": match_type,
            "strict_accept": False,
            "forced_manual_accept": True,
            "manual_review_reason": decision_record["reason"],
            "source_end_frame": source_end["frame_index"],
            "target_start_frame": target_start["frame_index"],
            "frame_delta": frame_delta,
            "appearance_distance": appearance_distance,
            "endpoint_floor_distance": endpoint_distance,
            "endpoint_box_iou": endpoint_iou,
            "overlapping_frame_count": len(common_frames),
            "duplicate_median_iou": duplicate_median_iou,
            "duplicate_median_distance": (
                duplicate_median_distance
            ),
            "matching_floor_distance": matching_distance,
            "matching_box_iou": matching_iou,
            "score": score,
        }
    )

candidates.sort(
    key=lambda candidate: (
        not candidate["strict_accept"],
        candidate["score"],
    )
)

strict_candidates = [
    candidate
    for candidate in candidates
    if candidate["strict_accept"]
]

review_candidates = [
    candidate
    for candidate in candidates
    if not candidate["strict_accept"]
]

candidate_pairs = {
    (
        candidate["source_segment_id"],
        candidate["target_segment_id"],
    )
    for candidate in candidates
}

configured_decision_pairs = (
    manual_accept_pairs
    | manual_reject_pairs
)

missing_decision_pairs = (
    configured_decision_pairs
    - candidate_pairs
)

if missing_decision_pairs:
    raise ValueError(
        "Reviewed match decisions no longer "
        "correspond to generated candidates: "
        f"{sorted(missing_decision_pairs)}"
    )

accepted_candidates = []
manually_rejected_candidates = []
unresolved_review_candidates = []

for candidate in candidates:
    candidate_pair = (
        candidate["source_segment_id"],
        candidate["target_segment_id"],
    )

    if candidate_pair in manual_reject_pairs:
        candidate["review_decision"] = (
            "rejected_manual"
        )

        manually_rejected_candidates.append(
            candidate
        )
    elif candidate["strict_accept"]:
        candidate["review_decision"] = (
            "accepted_strict"
        )
        accepted_candidates.append(candidate)
    elif candidate_pair in manual_accept_pairs:
        candidate["review_decision"] = (
            "accepted_manual"
        )
        accepted_candidates.append(candidate)
    else:
        candidate["review_decision"] = (
            "review_required"
        )
        unresolved_review_candidates.append(
            candidate
        )


# ---------------------------------------------------------
# Save candidate report
# ---------------------------------------------------------

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

output_report = {
    "classified_tracks": str(
        CLASSIFIED_TRACKS_PATH
    ),
    "segments_report": str(
        SEGMENTS_REPORT_PATH
    ),
    "segment_prototypes": str(
        SEGMENT_PROTOTYPES_PATH
    ),
    "review_config": str(
        REVIEW_CONFIG_PATH
    ),
    "strict_candidate_count": len(
        strict_candidates
    ),
    "review_candidate_count": len(
        review_candidates
    ),
    "strict_candidates": (
        strict_candidates
    ),
    "review_candidates": (
        review_candidates
    ),
    "accepted_candidate_count": len(
        accepted_candidates
    ),
    "accepted_candidates": (
        accepted_candidates
    ),
    "manually_rejected_candidate_count": len(
        manually_rejected_candidates
    ),
    "manually_rejected_candidates": (
        manually_rejected_candidates
    ),
    "unresolved_review_candidate_count": len(
        unresolved_review_candidates
    ),
    "unresolved_review_candidates": (
        unresolved_review_candidates
    ),
    "rejection_counts": dict(
        rejections
    ),
}

with OUTPUT_PATH.open(
    "w",
    encoding="utf-8",
) as output_file:
    json.dump(
        output_report,
        output_file,
        indent=2,
    )

    output_file.write("\n")


# ---------------------------------------------------------
# Print concise results
# ---------------------------------------------------------

print(
    "\nSegment-level matching complete."
)
print(
    f"Segments evaluated: "
    f"{len(segment_records)}"
)
print(
    f"Strict candidates: "
    f"{len(strict_candidates)}"
)
print(
    f"Review candidates: "
    f"{len(review_candidates)}"
)
print(
    f"Accepted candidates: "
    f"{len(accepted_candidates)}"
)
print(
    f"Manually rejected candidates: "
    f"{len(manually_rejected_candidates)}"
)
print(
    f"Unresolved review candidates: "
    f"{len(unresolved_review_candidates)}"
)

print("\nStrict candidates:")

if not strict_candidates:
    print("  None")

for candidate in strict_candidates:
    print(
        "  "
        f"{candidate['source_segment_id']} -> "
        f"{candidate['target_segment_id']} | "
        f"{candidate['match_type']} | "
        f"appearance="
        f"{candidate['appearance_distance']:.3f} | "
        f"distance="
        f"{candidate['matching_floor_distance']:.1f}px | "
        f"IoU="
        f"{candidate['matching_box_iou']:.3f} | "
        f"decision="
        f"{candidate['review_decision']}"
    )

print("\nTop review candidates:")

if not review_candidates:
    print("  None")

for candidate in review_candidates[:10]:
    print(
        "  "
        f"{candidate['source_segment_id']} -> "
        f"{candidate['target_segment_id']} | "
        f"{candidate['match_type']} | "
        f"appearance="
        f"{candidate['appearance_distance']:.3f} | "
        f"distance="
        f"{candidate['matching_floor_distance']:.1f}px | "
        f"IoU="
        f"{candidate['matching_box_iou']:.3f} | "
        f"decision="
        f"{candidate['review_decision']}"
    )

print(
    f"\nCandidate report saved to: "
    f"{OUTPUT_PATH}"
)
