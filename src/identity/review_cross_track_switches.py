import argparse
import itertools
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from . import review_residual_identities as residual
from . import review_sequential_identities as sequential


VIDEO_PATH: Path
RECONCILED_TRACKS_PATH: Path
MAPPING_PATH: Path
EMBEDDINGS_PATH: Path
REID_REVIEW_PATH: Path
SEQUENTIAL_REVIEW_PATH: Path
OUTPUT_DIR: Path
REPORT_PATH: Path
CONTEXT_DIR: Path
ASSIGNMENT_DIR: Path
CANDIDATE_DETAIL_DIR: Path


TEAM_LABEL = "dark"
WINDOW_FRAME_COUNT = 40
MAX_LOCAL_SAMPLE_FALLBACK_FRAME_GAP = 5
MAX_RANKED_ASSIGNMENTS = 5
GEOMETRY_COST_WEIGHT = 0.10
GEOMETRY_NORMALIZATION_DISTANCE = 250.0

STRONG_APPEARANCE_DISTANCE = 0.12
MODERATE_APPEARANCE_DISTANCE = 0.20

CONTEXT_TILE_SIZE = (560, 315)
ASSIGNMENT_TILE_SIZE = (330, 240)
CANDIDATE_DETAIL_TILE_SIZE = (440, 330)
ASSIGNMENT_ZOOM_PADDING_X = 105
ASSIGNMENT_ZOOM_PADDING_Y = 85

TEXT_COLOR = (255, 255, 255)
OTHER_COLOR = (90, 90, 90)
ANCHOR_COLOR = (120, 220, 120)
CROSS_LINK_COLOR = (0, 215, 255)
IDENTITY_COLORS = [
    (0, 215, 255),
    (255, 80, 220),
    (80, 220, 80),
    (255, 170, 50),
    (80, 180, 255),
    (200, 120, 255),
    (255, 255, 80),
]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Generate lineup-level evidence for cross-track "
            "identity switches around reviewed boundaries."
        )
    )
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--reconciled-tracks", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--embeddings", type=Path, required=True)
    parser.add_argument("--reid-review", type=Path, required=True)
    parser.add_argument("--sequential-review", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--team-label",
        choices=("white", "dark"),
        default=TEAM_LABEL,
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help=(
            "Write the JSON report without reading the source "
            "video or creating montages."
        ),
    )
    return parser.parse_args(argv)


def normalize(vector):
    norm = float(np.linalg.norm(vector))

    if norm <= 0:
        return vector.copy()

    return vector / norm


def cosine_distance(first, second):
    return 1.0 - float(np.dot(first, second))


def appearance_band(distance):
    if distance <= STRONG_APPEARANCE_DISTANCE:
        return "strong"

    if distance <= MODERATE_APPEARANCE_DISTANCE:
        return "moderate"

    return "weak"


def load_embedding_samples(mapping_report):
    active_segments_by_track = defaultdict(list)

    for segment in mapping_report["segment_mapping"]:
        if segment["identity_status"] != "active":
            continue

        active_segments_by_track[
            int(segment["track_id"])
        ].append(segment)

    for segments in active_segments_by_track.values():
        segments.sort(
            key=lambda segment: (
                int(segment["raw_start_frame"]),
                segment["segment_id"],
            )
        )

    def player_id_for_sample(track_id, frame_index):
        for segment in active_segments_by_track.get(
            track_id,
            [],
        ):
            if (
                int(segment["raw_start_frame"])
                <= frame_index
                <= int(segment["raw_end_frame"])
            ):
                return segment["player_id"]

        return None

    samples_by_identity = defaultdict(list)

    with np.load(EMBEDDINGS_PATH) as archive:
        embeddings = archive["embeddings"].astype(
            np.float32,
            copy=True,
        )
        frame_indices = archive["frame_indices"]
        track_ids = archive["track_ids"]
        confidences = archive["confidences"]

    embedding_norms = np.linalg.norm(
        embeddings,
        axis=1,
        keepdims=True,
    )
    embeddings = embeddings / np.maximum(
        embedding_norms,
        1e-12,
    )

    for embedding, frame_index, track_id, confidence in zip(
        embeddings,
        frame_indices,
        track_ids,
        confidences,
    ):
        frame_index = int(frame_index)
        track_id = int(track_id)
        player_id = player_id_for_sample(
            track_id,
            frame_index,
        )

        if player_id is None:
            continue

        samples_by_identity[player_id].append(
            {
                "frame_index": frame_index,
                "track_id": track_id,
                "confidence": float(confidence),
                "embedding": embedding,
            }
        )

    for samples in samples_by_identity.values():
        samples.sort(
            key=lambda sample: sample["frame_index"]
        )

    return dict(samples_by_identity)


def reviewed_boundaries(reid_review):
    boundaries = set()

    for split_frames in reid_review.get(
        "manual_split_after_frames",
        {},
    ).values():
        boundaries.update(
            int(frame_index)
            for frame_index in split_frames
        )

    return sorted(boundaries)


def local_rows(rows, first_frame, last_frame):
    return [
        row
        for row in rows
        if first_frame <= row["frame_index"] <= last_frame
    ]


def local_samples(samples, first_frame, last_frame):
    return [
        sample
        for sample in samples
        if first_frame
        <= sample["frame_index"]
        <= last_frame
    ]


def frame_gap_to_window(frame_index, first_frame, last_frame):
    if frame_index < first_frame:
        return first_frame - frame_index

    if frame_index > last_frame:
        return frame_index - last_frame

    return 0


def local_samples_with_continuity_fallback(
    samples,
    rows,
    first_frame,
    last_frame,
    excluded_track_ids,
):
    selected = local_samples(samples, first_frame, last_frame)

    if selected:
        return selected, None

    continuing_track_ids = {
        int(row["track_id"])
        for row in local_rows(rows, first_frame, last_frame)
        if int(row["track_id"]) not in excluded_track_ids
    }
    candidates = [
        sample
        for sample in samples
        if int(sample["track_id"]) in continuing_track_ids
    ]

    if not candidates:
        return [], None

    nearest = min(
        candidates,
        key=lambda sample: (
            frame_gap_to_window(
                int(sample["frame_index"]),
                first_frame,
                last_frame,
            ),
            -float(sample["confidence"]),
            int(sample["frame_index"]),
        ),
    )
    frame_gap = frame_gap_to_window(
        int(nearest["frame_index"]),
        first_frame,
        last_frame,
    )

    if frame_gap > MAX_LOCAL_SAMPLE_FALLBACK_FRAME_GAP:
        return [], None

    return [nearest], {
        "sample_frame_index": int(nearest["frame_index"]),
        "sample_track_id": int(nearest["track_id"]),
        "frame_gap": int(frame_gap),
        "requested_window": [first_frame, last_frame],
    }


def local_prototype(samples):
    if not samples:
        return None

    return normalize(
        np.mean(
            [sample["embedding"] for sample in samples],
            axis=0,
        )
    )


def endpoint_row(rows, before_boundary):
    if before_boundary:
        return max(
            rows,
            key=lambda row: row["frame_index"],
        )

    return min(
        rows,
        key=lambda row: row["frame_index"],
    )


def floor_distance(first, second):
    return math.hypot(
        first["floor_x"] - second["floor_x"],
        first["floor_y"] - second["floor_y"],
    )


def ranked_assignments(
    first_player_ids,
    second_player_ids,
    cost_matrix,
):
    if len(first_player_ids) != len(second_player_ids):
        raise ValueError(
            "Lineup assignment requires equal before/after "
            "identity counts; got "
            f"{len(first_player_ids)} and "
            f"{len(second_player_ids)}."
        )

    assignment_count = len(first_player_ids)
    ranked = []

    for permutation in itertools.permutations(
        range(assignment_count)
    ):
        total_cost = sum(
            cost_matrix[first_index][second_index]
            for first_index, second_index in enumerate(
                permutation
            )
        )
        ranked.append(
            {
                "total_cost": float(total_cost),
                "pairs": [
                    {
                        "first_player_id": first_player_ids[
                            first_index
                        ],
                        "second_player_id": second_player_ids[
                            second_index
                        ],
                    }
                    for first_index, second_index in enumerate(
                        permutation
                    )
                ],
            }
        )

    ranked.sort(
        key=lambda assignment: (
            assignment["total_cost"],
            [
                pair["second_player_id"]
                for pair in assignment["pairs"]
            ],
        )
    )
    return ranked[:MAX_RANKED_ASSIGNMENTS]


def assignment_pair_set(assignment):
    return {
        (
            pair["first_player_id"],
            pair["second_player_id"],
        )
        for pair in assignment["pairs"]
    }


def matrix_record(row_ids, column_ids, values):
    return {
        "row_player_ids": row_ids,
        "column_player_ids": column_ids,
        "values": [
            [float(value) for value in row]
            for row in values
        ],
    }


def context_frames(boundary, rows_by_frame):
    requested = [
        boundary - 7,
        boundary - 2,
        boundary,
        boundary + 1,
        boundary + 2,
        boundary + 7,
    ]
    available = sorted(rows_by_frame)

    return [
        min(
            available,
            key=lambda frame_index: (
                abs(frame_index - requested_frame),
                frame_index,
            ),
        )
        for requested_frame in requested
    ]


def review_rows_for_pair(
    first_player_id,
    second_player_id,
    rows_by_identity,
    before_start,
    boundary,
    after_end,
):
    first_rows = local_rows(
        rows_by_identity[first_player_id],
        before_start,
        boundary,
    )
    second_rows = local_rows(
        rows_by_identity[second_player_id],
        boundary + 1,
        after_end,
    )
    first_middle = (before_start + boundary) // 2
    second_middle = (boundary + 1 + after_end) // 2
    first_representative = sequential.best_row_near(
        first_rows,
        first_middle,
    )
    first_endpoint = endpoint_row(
        first_rows,
        before_boundary=True,
    )
    second_endpoint = endpoint_row(
        second_rows,
        before_boundary=False,
    )
    second_representative = sequential.best_row_near(
        second_rows,
        second_middle,
    )

    return [
        {
            "role": "PRE representative",
            "player_id": first_player_id,
            "frame_index": first_representative[
                "frame_index"
            ],
        },
        {
            "role": "PRE endpoint",
            "player_id": first_player_id,
            "frame_index": first_endpoint["frame_index"],
        },
        {
            "role": "POST endpoint",
            "player_id": second_player_id,
            "frame_index": second_endpoint["frame_index"],
        },
        {
            "role": "POST representative",
            "player_id": second_player_id,
            "frame_index": second_representative[
                "frame_index"
            ],
        },
    ]


def row_box_area(row):
    return max(0.0, row["x2"] - row["x1"]) * max(
        0.0,
        row["y2"] - row["y1"],
    )


def maximum_other_iou(row, rows_by_frame):
    return max(
        (
            residual.bounding_box_iou(row, other)
            for other in rows_by_frame[row["frame_index"]]
            if other["player_id"] != row["player_id"]
        ),
        default=0.0,
    )


def clean_row_score(row, rows_by_frame):
    overlap_penalty = maximum_other_iou(
        row,
        rows_by_frame,
    )
    area_bonus = min(
        row_box_area(row) / 40000.0,
        1.0,
    )
    return (
        row["confidence"]
        - 2.0 * overlap_penalty
        + 0.15 * area_bonus
    )


def choose_clean_review_rows(
    player_id,
    rows_by_identity,
    rows_by_frame,
    first_frame,
    last_frame,
    side,
):
    rows = local_rows(
        rows_by_identity[player_id],
        first_frame,
        last_frame,
    )

    if not rows:
        return []

    chosen = []

    for bucket_index in range(3):
        bucket_start = (
            first_frame
            + (last_frame - first_frame + 1)
            * bucket_index
            // 3
        )
        bucket_end = (
            first_frame
            + (last_frame - first_frame + 1)
            * (bucket_index + 1)
            // 3
            - 1
        )
        bucket_rows = [
            row
            for row in rows
            if bucket_start
            <= row["frame_index"]
            <= bucket_end
        ]

        if not bucket_rows:
            continue

        selected = max(
            bucket_rows,
            key=lambda row: (
                clean_row_score(row, rows_by_frame),
                row["confidence"],
                row_box_area(row),
                -row["frame_index"],
            ),
        )
        chosen.append(
            {
                "role": f"{side} clean {bucket_index + 1}",
                "player_id": player_id,
                "frame_index": selected["frame_index"],
                "confidence": selected["confidence"],
                "maximum_other_iou": maximum_other_iou(
                    selected,
                    rows_by_frame,
                ),
                "clean_row_score": clean_row_score(
                    selected,
                    rows_by_frame,
                ),
            }
        )

    return chosen


def build_boundary_record(
    boundary,
    team_player_ids,
    rows_by_frame,
    rows_by_identity,
    samples_by_identity,
    reid_review,
    stage_before_start,
    stage_after_end,
):
    before_start = boundary - WINDOW_FRAME_COUNT + 1
    after_end = boundary + WINDOW_FRAME_COUNT
    first_player_ids = sorted(
        player_id
        for player_id in team_player_ids
        if local_rows(
            rows_by_identity.get(player_id, []),
            before_start,
            boundary,
        )
    )
    second_player_ids = sorted(
        player_id
        for player_id in team_player_ids
        if local_rows(
            rows_by_identity.get(player_id, []),
            boundary + 1,
            after_end,
        )
    )
    split_tracks = [
        {
            "track_id": int(track_id),
            "split_after_frame": boundary,
        }
        for track_id, split_frames in reid_review.get(
            "manual_split_after_frames",
            {},
        ).items()
        if boundary in [int(frame) for frame in split_frames]
    ]
    split_track_ids = {
        split_track["track_id"] for split_track in split_tracks
    }

    if len(first_player_ids) != len(second_player_ids):
        return {
            "boundary_id": f"boundary_{boundary}_{boundary + 1}",
            "analysis_status": "skipped_unequal_lineup_counts",
            "analysis_reason": (
                "A one-to-one lineup assignment is undefined "
                "when the reviewed team has different identity "
                "counts on the two sides of the boundary."
            ),
            "split_after_frame": boundary,
            "before_window": [before_start, boundary],
            "after_window": [boundary + 1, after_end],
            "clean_review_before_window": [
                stage_before_start,
                boundary,
            ],
            "clean_review_after_window": [
                boundary + 1,
                stage_after_end,
            ],
            "reviewed_split_tracks": split_tracks,
            "first_player_ids": first_player_ids,
            "second_player_ids": second_player_ids,
            "first_identity_count": len(first_player_ids),
            "second_identity_count": len(second_player_ids),
            "first_sample_counts": {},
            "second_sample_counts": {},
            "first_sample_fallbacks": {},
            "second_sample_fallbacks": {},
            "missing_first_sample_player_ids": [],
            "missing_second_sample_player_ids": [],
            "appearance_matrix": None,
            "endpoint_floor_distance_matrix": None,
            "combined_cost_matrix": None,
            "appearance_ranked_assignments": [],
            "geometry_ranked_assignments": [],
            "combined_ranked_assignments": [],
            "appearance_geometry_consensus": False,
            "best_vs_second_combined_margin": None,
            "assignments": [],
            "cross_track_candidate_count": 0,
            "context_frames": context_frames(
                boundary,
                rows_by_frame,
            ),
        }

    first_samples = {}
    first_sample_fallbacks = {}

    for player_id in first_player_ids:
        samples, fallback = (
            local_samples_with_continuity_fallback(
                samples_by_identity.get(player_id, []),
                rows_by_identity.get(player_id, []),
                before_start,
                boundary,
                split_track_ids,
            )
        )
        first_samples[player_id] = samples

        if fallback is not None:
            first_sample_fallbacks[player_id] = fallback

    second_samples = {}
    second_sample_fallbacks = {}

    for player_id in second_player_ids:
        samples, fallback = (
            local_samples_with_continuity_fallback(
                samples_by_identity.get(player_id, []),
                rows_by_identity.get(player_id, []),
                boundary + 1,
                after_end,
                split_track_ids,
            )
        )
        second_samples[player_id] = samples

        if fallback is not None:
            second_sample_fallbacks[player_id] = fallback

    missing_first_samples = sorted(
        player_id
        for player_id, samples in first_samples.items()
        if not samples
    )
    missing_second_samples = sorted(
        player_id
        for player_id, samples in second_samples.items()
        if not samples
    )

    if missing_first_samples or missing_second_samples:
        return {
            "boundary_id": f"boundary_{boundary}_{boundary + 1}",
            "analysis_status": "skipped_missing_appearance_samples",
            "analysis_reason": (
                "A one-to-one appearance assignment is undefined "
                "when a lineup identity has no local sample or "
                "eligible same-track sample within the bounded "
                "fallback distance."
            ),
            "split_after_frame": boundary,
            "before_window": [before_start, boundary],
            "after_window": [boundary + 1, after_end],
            "clean_review_before_window": [
                stage_before_start,
                boundary,
            ],
            "clean_review_after_window": [
                boundary + 1,
                stage_after_end,
            ],
            "reviewed_split_tracks": split_tracks,
            "first_player_ids": first_player_ids,
            "second_player_ids": second_player_ids,
            "first_identity_count": len(first_player_ids),
            "second_identity_count": len(second_player_ids),
            "first_sample_counts": {
                player_id: len(samples)
                for player_id, samples in first_samples.items()
            },
            "second_sample_counts": {
                player_id: len(samples)
                for player_id, samples in second_samples.items()
            },
            "first_sample_fallbacks": first_sample_fallbacks,
            "second_sample_fallbacks": second_sample_fallbacks,
            "missing_first_sample_player_ids": (
                missing_first_samples
            ),
            "missing_second_sample_player_ids": (
                missing_second_samples
            ),
            "appearance_matrix": None,
            "endpoint_floor_distance_matrix": None,
            "combined_cost_matrix": None,
            "appearance_ranked_assignments": [],
            "geometry_ranked_assignments": [],
            "combined_ranked_assignments": [],
            "appearance_geometry_consensus": False,
            "best_vs_second_combined_margin": None,
            "assignments": [],
            "cross_track_candidate_count": 0,
            "context_frames": context_frames(
                boundary,
                rows_by_frame,
            ),
        }

    first_prototypes = {
        player_id: local_prototype(samples)
        for player_id, samples in first_samples.items()
    }
    second_prototypes = {
        player_id: local_prototype(samples)
        for player_id, samples in second_samples.items()
    }
    first_endpoints = {
        player_id: endpoint_row(
            local_rows(
                rows_by_identity[player_id],
                before_start,
                boundary,
            ),
            before_boundary=True,
        )
        for player_id in first_player_ids
    }
    second_endpoints = {
        player_id: endpoint_row(
            local_rows(
                rows_by_identity[player_id],
                boundary + 1,
                after_end,
            ),
            before_boundary=False,
        )
        for player_id in second_player_ids
    }
    appearance_matrix = [
        [
            cosine_distance(
                first_prototypes[first_player_id],
                second_prototypes[second_player_id],
            )
            for second_player_id in second_player_ids
        ]
        for first_player_id in first_player_ids
    ]
    geometry_matrix = [
        [
            floor_distance(
                first_endpoints[first_player_id],
                second_endpoints[second_player_id],
            )
            for second_player_id in second_player_ids
        ]
        for first_player_id in first_player_ids
    ]
    combined_matrix = [
        [
            appearance_matrix[first_index][second_index]
            + GEOMETRY_COST_WEIGHT
            * min(
                geometry_matrix[first_index][second_index]
                / GEOMETRY_NORMALIZATION_DISTANCE,
                1.0,
            )
            for second_index in range(len(second_player_ids))
        ]
        for first_index in range(len(first_player_ids))
    ]
    appearance_ranked = ranked_assignments(
        first_player_ids,
        second_player_ids,
        appearance_matrix,
    )
    geometry_ranked = ranked_assignments(
        first_player_ids,
        second_player_ids,
        geometry_matrix,
    )
    combined_ranked = ranked_assignments(
        first_player_ids,
        second_player_ids,
        combined_matrix,
    )
    best_assignment = combined_ranked[0]
    appearance_lookup = {
        (first_player_id, second_player_id): (
            appearance_matrix[first_index][second_index]
        )
        for first_index, first_player_id in enumerate(
            first_player_ids
        )
        for second_index, second_player_id in enumerate(
            second_player_ids
        )
    }
    geometry_lookup = {
        (first_player_id, second_player_id): (
            geometry_matrix[first_index][second_index]
        )
        for first_index, first_player_id in enumerate(
            first_player_ids
        )
        for second_index, second_player_id in enumerate(
            second_player_ids
        )
    }
    assignments = []

    for pair_index, pair in enumerate(
        best_assignment["pairs"],
        1,
    ):
        first_player_id = pair["first_player_id"]
        second_player_id = pair["second_player_id"]
        appearance_distance = appearance_lookup[
            (first_player_id, second_player_id)
        ]
        assignment = {
                "assignment_id": (
                    f"switch_{boundary}_{pair_index:02d}"
                ),
                "first_player_id": first_player_id,
                "second_player_id": second_player_id,
                "assignment_type": (
                    "same_label_anchor"
                    if first_player_id == second_player_id
                    else "cross_track_candidate"
                ),
                "appearance_distance": float(
                    appearance_distance
                ),
                "appearance_band": appearance_band(
                    appearance_distance
                ),
                "endpoint_floor_distance": float(
                    geometry_lookup[
                        (first_player_id, second_player_id)
                    ]
                ),
                "first_endpoint_frame": first_endpoints[
                    first_player_id
                ]["frame_index"],
                "second_endpoint_frame": second_endpoints[
                    second_player_id
                ]["frame_index"],
                "first_sample_count": len(
                    first_samples[first_player_id]
                ),
                "second_sample_count": len(
                    second_samples[second_player_id]
                ),
                "first_sample_fallback": (
                    first_sample_fallbacks.get(first_player_id)
                ),
                "second_sample_fallback": (
                    second_sample_fallbacks.get(second_player_id)
                ),
                "review_frames": review_rows_for_pair(
                    first_player_id,
                    second_player_id,
                    rows_by_identity,
                    before_start,
                    boundary,
                    after_end,
                ),
            }
        assignment["clean_review_frames"] = (
            choose_clean_review_rows(
                first_player_id,
                rows_by_identity,
                rows_by_frame,
                stage_before_start,
                boundary,
                "PRE",
            )
            + choose_clean_review_rows(
                second_player_id,
                rows_by_identity,
                rows_by_frame,
                boundary + 1,
                stage_after_end,
                "POST",
            )
        )
        pre_clean_frame_count = sum(
            review_frame["role"].startswith("PRE")
            for review_frame in assignment["clean_review_frames"]
        )
        post_clean_frame_count = sum(
            review_frame["role"].startswith("POST")
            for review_frame in assignment["clean_review_frames"]
        )
        assignment["clean_review_frame_counts"] = {
            "before": pre_clean_frame_count,
            "after": post_clean_frame_count,
        }
        assignment["clean_review_status"] = (
            "complete"
            if pre_clean_frame_count == 3
            and post_clean_frame_count == 3
            else "insufficient_rows"
        )
        assignments.append(assignment)

    return {
        "boundary_id": f"boundary_{boundary}_{boundary + 1}",
        "analysis_status": "analyzed",
        "analysis_reason": None,
        "split_after_frame": boundary,
        "before_window": [before_start, boundary],
        "after_window": [boundary + 1, after_end],
        "clean_review_before_window": [
            stage_before_start,
            boundary,
        ],
        "clean_review_after_window": [
            boundary + 1,
            stage_after_end,
        ],
        "reviewed_split_tracks": split_tracks,
        "first_player_ids": first_player_ids,
        "second_player_ids": second_player_ids,
        "first_sample_counts": {
            player_id: len(samples)
            for player_id, samples in first_samples.items()
        },
        "second_sample_counts": {
            player_id: len(samples)
            for player_id, samples in second_samples.items()
        },
        "first_sample_fallbacks": first_sample_fallbacks,
        "second_sample_fallbacks": second_sample_fallbacks,
        "missing_first_sample_player_ids": [],
        "missing_second_sample_player_ids": [],
        "appearance_matrix": matrix_record(
            first_player_ids,
            second_player_ids,
            appearance_matrix,
        ),
        "endpoint_floor_distance_matrix": matrix_record(
            first_player_ids,
            second_player_ids,
            geometry_matrix,
        ),
        "combined_cost_matrix": matrix_record(
            first_player_ids,
            second_player_ids,
            combined_matrix,
        ),
        "appearance_ranked_assignments": appearance_ranked,
        "geometry_ranked_assignments": geometry_ranked,
        "combined_ranked_assignments": combined_ranked,
        "appearance_geometry_consensus": (
            assignment_pair_set(appearance_ranked[0])
            == assignment_pair_set(geometry_ranked[0])
        ),
        "best_vs_second_combined_margin": (
            combined_ranked[1]["total_cost"]
            - combined_ranked[0]["total_cost"]
            if len(combined_ranked) > 1
            else None
        ),
        "assignments": assignments,
        "cross_track_candidate_count": sum(
            assignment["assignment_type"]
            == "cross_track_candidate"
            for assignment in assignments
        ),
        "context_frames": context_frames(
            boundary,
            rows_by_frame,
        ),
    }


def build_report(
    mapping_report,
    reid_review,
    sequential_review,
    boundary_records,
):
    return {
        "reconciled_tracks": str(RECONCILED_TRACKS_PATH),
        "identity_mapping": str(MAPPING_PATH),
        "source_embeddings": str(EMBEDDINGS_PATH),
        "reid_review_config": str(REID_REVIEW_PATH),
        "sequential_review_config": str(
            SEQUENTIAL_REVIEW_PATH
        ),
        "settings": {
            "team_label": TEAM_LABEL,
            "window_frame_count_per_side": WINDOW_FRAME_COUNT,
            "max_local_sample_fallback_frame_gap": (
                MAX_LOCAL_SAMPLE_FALLBACK_FRAME_GAP
            ),
            "geometry_cost_weight": GEOMETRY_COST_WEIGHT,
            "geometry_normalization_distance": (
                GEOMETRY_NORMALIZATION_DISTANCE
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
            "boundary_count": len(boundary_records),
            "cross_track_candidate_count": sum(
                record["cross_track_candidate_count"]
                for record in boundary_records
            ),
            "consensus_boundary_count": sum(
                record["appearance_geometry_consensus"]
                for record in boundary_records
            ),
            "sample_fallback_boundary_count": sum(
                bool(record["first_sample_fallbacks"])
                or bool(record["second_sample_fallbacks"])
                for record in boundary_records
            ),
            "skipped_boundary_count": sum(
                record["analysis_status"] != "analyzed"
                for record in boundary_records
            ),
        },
        "interpretation": {
            "lineup_assignment": (
                "A one-to-one permutation of the available team "
                "identities before and after a boundary."
            ),
            "cross_track_candidate": (
                "The best lineup assignment connects different "
                "current labels, suggesting a tracker ID swap."
            ),
            "same_label_anchor": (
                "The identity remains its own best lineup match "
                "and acts as an anchor for the permutation."
            ),
            "consensus": (
                "Appearance-only and court-position-only global "
                "assignments choose the same pairings."
            ),
            "review_requirement": (
                "A cross-track candidate must be confirmed from "
                "jersey, body, and motion cues before identities "
                "are changed."
            ),
            "bounded_sample_fallback": (
                "If one side lacks a sampled crop, the nearest "
                "sample may be reused only from the same raw track, "
                "within the configured frame gap, and never across "
                "that track's reviewed split boundary."
            ),
            "clean_detail_requirement": (
                "A six-tile clean-detail montage is generated only "
                "when three clean rows exist on each side. The "
                "lineup assignment and its standard four-frame "
                "review evidence remain available otherwise."
            ),
        },
        "prior_sequential_review_conclusion": (
            sequential_review.get("review_conclusion")
        ),
        "reviewed_boundaries": reviewed_boundaries(reid_review),
        "boundaries": boundary_records,
    }


def identity_color(player_id, player_ids):
    index = player_ids.index(player_id)
    return IDENTITY_COLORS[index % len(IDENTITY_COLORS)]


def annotate_context_frame(frame, rows, team_player_ids):
    annotated = frame.copy()

    for row in rows:
        player_id = row["player_id"]

        if player_id in team_player_ids:
            color = identity_color(
                player_id,
                team_player_ids,
            )
            thickness = 4
        else:
            color = OTHER_COLOR
            thickness = 1

        residual.draw_label(
            annotated,
            row,
            color,
            thickness,
        )

    return annotated


def create_context_montage(
    boundary_record,
    frames,
    rows_by_frame,
    team_player_ids,
):
    tiles = []
    boundary = boundary_record["split_after_frame"]

    for frame_index in boundary_record["context_frames"]:
        side = "PRE" if frame_index <= boundary else "POST"
        annotated = annotate_context_frame(
            frames[frame_index],
            rows_by_frame[frame_index],
            team_player_ids,
        )
        tiles.append(
            residual.add_header(
                residual.fit_to_tile(
                    annotated,
                    CONTEXT_TILE_SIZE,
                ),
                f"{side} | frame {frame_index}",
            )
        )

    first_row = np.hstack(tiles[:3])
    second_row = np.hstack(tiles[3:6])
    title = residual.title_panel(
        first_row.shape[1],
        [
            (
                f"{boundary_record['boundary_id']} | "
                f"full {TEAM_LABEL} lineup around reviewed switch"
            ),
            (
                "Colors identify current labels only; compare "
                "jersey number, body, and trajectory across sides."
            ),
        ],
        TEXT_COLOR,
    )
    return np.vstack([title, first_row, second_row])


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
        int(
            math.floor(
                row["x1"] - ASSIGNMENT_ZOOM_PADDING_X
            )
        ),
    )
    y1 = max(
        0,
        int(
            math.floor(
                row["y1"] - ASSIGNMENT_ZOOM_PADDING_Y
            )
        ),
    )
    x2 = min(
        image_width,
        int(
            math.ceil(
                row["x2"] + ASSIGNMENT_ZOOM_PADDING_X
            )
        ),
    )
    y2 = min(
        image_height,
        int(
            math.ceil(
                row["y2"] + ASSIGNMENT_ZOOM_PADDING_Y
            )
        ),
    )
    return image[y1:y2, x1:x2]


def assignment_tile(
    review_frame,
    frames,
    rows_by_frame,
    color,
):
    frame_index = review_frame["frame_index"]
    player_id = review_frame["player_id"]
    rows = rows_by_frame[frame_index]
    row = find_player_row(rows, player_id)
    annotated = frames[frame_index].copy()
    residual.draw_label(
        annotated,
        row,
        color,
        5,
    )
    zoom = player_zoom(annotated, row)
    header = (
        f"{review_frame['role']} | {player_id} | "
        f"f{frame_index}"
    )
    return residual.add_header(
        residual.fit_to_tile(
            zoom,
            ASSIGNMENT_TILE_SIZE,
        ),
        header,
        color,
    )


def create_assignment_grid(
    boundary_record,
    frames,
    rows_by_frame,
):
    assignment_rows = []

    for assignment in boundary_record["assignments"]:
        is_cross_link = (
            assignment["assignment_type"]
            == "cross_track_candidate"
        )
        color = (
            CROSS_LINK_COLOR
            if is_cross_link
            else ANCHOR_COLOR
        )
        tiles = [
            assignment_tile(
                review_frame,
                frames,
                rows_by_frame,
                color,
            )
            for review_frame in assignment["review_frames"]
        ]
        tile_row = np.hstack(tiles)
        row_title = residual.title_panel(
            tile_row.shape[1],
            [
                (
                    f"{assignment['assignment_id']} | "
                    f"{assignment['first_player_id']} -> "
                    f"{assignment['second_player_id']} | "
                    f"{assignment['assignment_type']}"
                ),
                (
                    "appearance="
                    f"{assignment['appearance_distance']:.3f} "
                    f"({assignment['appearance_band']}) | "
                    "endpoint distance="
                    f"{assignment['endpoint_floor_distance']:.1f}px"
                )
            ],
            color,
        )
        assignment_rows.extend([row_title, tile_row])

    width = assignment_rows[0].shape[1]
    margin = boundary_record[
        "best_vs_second_combined_margin"
    ]
    consensus_text = (
        "yes"
        if boundary_record["appearance_geometry_consensus"]
        else "no"
    )
    title = residual.title_panel(
        width,
        [
            (
                f"{boundary_record['boundary_id']} | "
                "best lineup assignment"
            ),
            (
                f"appearance/geometry consensus={consensus_text} | "
                f"best-vs-second margin={margin:.3f} | "
                "yellow=cross-track candidate, "
                "green=same-label anchor"
            ),
            (
                "This is evidence for visual review, not an "
                "automatic identity correction."
            ),
        ],
        TEXT_COLOR,
    )
    return np.vstack([title] + assignment_rows)


def candidate_detail_tile(
    review_frame,
    frames,
    rows_by_frame,
):
    frame_index = review_frame["frame_index"]
    player_id = review_frame["player_id"]
    row = find_player_row(
        rows_by_frame[frame_index],
        player_id,
    )
    annotated = frames[frame_index].copy()
    residual.draw_label(
        annotated,
        row,
        CROSS_LINK_COLOR,
        5,
    )
    zoom = player_zoom(annotated, row)
    header = (
        f"{review_frame['role']} | {player_id} | "
        f"f{frame_index} | conf={row['confidence']:.2f} | "
        "max IoU="
        f"{review_frame['maximum_other_iou']:.2f}"
    )
    return residual.add_header(
        residual.fit_to_tile(
            zoom,
            CANDIDATE_DETAIL_TILE_SIZE,
        ),
        header,
        CROSS_LINK_COLOR,
    )


def create_candidate_detail_montage(
    boundary_record,
    assignment,
    frames,
    rows_by_frame,
):
    review_frames = assignment["clean_review_frames"]
    pre_frames = [
        review_frame
        for review_frame in review_frames
        if review_frame["role"].startswith("PRE")
    ]
    post_frames = [
        review_frame
        for review_frame in review_frames
        if review_frame["role"].startswith("POST")
    ]

    if len(pre_frames) != 3 or len(post_frames) != 3:
        raise ValueError(
            "Candidate detail montage requires three clean "
            "frames on each side: "
            f"{assignment['assignment_id']}"
        )

    pre_row = np.hstack(
        [
            candidate_detail_tile(
                review_frame,
                frames,
                rows_by_frame,
            )
            for review_frame in pre_frames
        ]
    )
    post_row = np.hstack(
        [
            candidate_detail_tile(
                review_frame,
                frames,
                rows_by_frame,
            )
            for review_frame in post_frames
        ]
    )
    title = residual.title_panel(
        pre_row.shape[1],
        [
            (
                f"{assignment['assignment_id']} | CLEAN DETAIL | "
                f"{assignment['first_player_id']} -> "
                f"{assignment['second_player_id']}"
            ),
            (
                "appearance="
                f"{assignment['appearance_distance']:.3f} "
                f"({assignment['appearance_band']}) | "
                "endpoint distance="
                f"{assignment['endpoint_floor_distance']:.1f}px"
            ),
            (
                "Frames maximize confidence and box size while "
                "penalizing overlap with every other detection."
            ),
        ],
        CROSS_LINK_COLOR,
    )
    return np.vstack([title, pre_row, post_row])


def read_frames(frame_indices, video_path=None):
    source_video_path = (
        VIDEO_PATH
        if video_path is None
        else Path(video_path)
    )
    capture = residual.cv2.VideoCapture(str(source_video_path))

    if not capture.isOpened():
        raise RuntimeError(
            f"Could not open video: {source_video_path}"
        )

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
                    f"from {source_video_path}"
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
    boundary_records,
    rows_by_frame,
    team_player_ids,
):
    requested_frames = {
        frame_index
        for record in boundary_records
        for frame_index in record["context_frames"]
    }
    requested_frames.update(
        review_frame["frame_index"]
        for record in boundary_records
        for assignment in record["assignments"]
        for review_frame in assignment["review_frames"]
    )
    requested_frames.update(
        review_frame["frame_index"]
        for record in boundary_records
        for assignment in record["assignments"]
        if assignment["assignment_type"]
        == "cross_track_candidate"
        for review_frame in assignment["clean_review_frames"]
    )
    frames = read_frames(requested_frames)

    print("\nGenerating cross-track switch review montages...")

    for record in boundary_records:
        boundary = record["split_after_frame"]
        context_path = (
            CONTEXT_DIR
            / f"boundary_{boundary}_{boundary + 1}_context.jpg"
        )
        assignment_path = (
            ASSIGNMENT_DIR
            / f"boundary_{boundary}_{boundary + 1}_assignments.jpg"
        )
        write_montage(
            context_path,
            create_context_montage(
                record,
                frames,
                rows_by_frame,
                team_player_ids,
            ),
        )
        print(f"  Saved context: {context_path}")

        if record["analysis_status"] != "analyzed":
            print(
                "  Skipped assignment grid: "
                f"{record['analysis_reason']}"
            )
            continue

        write_montage(
            assignment_path,
            create_assignment_grid(
                record,
                frames,
                rows_by_frame,
            ),
        )
        print(f"  Saved assignments: {assignment_path}")

        for assignment in record["assignments"]:
            if (
                assignment["assignment_type"]
                != "cross_track_candidate"
            ):
                continue

            if assignment["clean_review_status"] != "complete":
                print(
                    "  Skipped clean detail: "
                    f"{assignment['assignment_id']} has "
                    "insufficient clean rows "
                    f"{assignment['clean_review_frame_counts']}"
                )
                continue

            detail_path = (
                CANDIDATE_DETAIL_DIR
                / f"{assignment['assignment_id']}_"
                f"{assignment['first_player_id']}__"
                f"{assignment['second_player_id']}_clean.jpg"
            )
            write_montage(
                detail_path,
                create_candidate_detail_montage(
                    record,
                    assignment,
                    frames,
                    rows_by_frame,
                ),
            )
            print(f"  Saved clean detail: {detail_path}")


def print_boundary(record):
    if record["analysis_status"] != "analyzed":
        print(
            f"\n{record['boundary_id']}: "
            f"{record['analysis_status']} | "
            "team identities="
            f"{record['first_identity_count']} before, "
            f"{record['second_identity_count']} after"
        )
        print(f"  {record['analysis_reason']}")
        return

    print(
        f"\n{record['boundary_id']}: "
        "appearance/geometry consensus="
        f"{record['appearance_geometry_consensus']} | "
        "cross-track candidates="
        f"{record['cross_track_candidate_count']}"
    )

    for assignment in record["assignments"]:
        marker = (
            "CROSS"
            if assignment["assignment_type"]
            == "cross_track_candidate"
            else "anchor"
        )
        print(
            f"  {marker:6s} | "
            f"{assignment['first_player_id']} -> "
            f"{assignment['second_player_id']} | "
            "appearance="
            f"{assignment['appearance_distance']:.3f} "
            f"({assignment['appearance_band']}) | "
            "endpoint distance="
            f"{assignment['endpoint_floor_distance']:.1f}px"
        )


def main():
    global VIDEO_PATH
    global RECONCILED_TRACKS_PATH
    global MAPPING_PATH
    global EMBEDDINGS_PATH
    global REID_REVIEW_PATH
    global SEQUENTIAL_REVIEW_PATH
    global OUTPUT_DIR
    global REPORT_PATH
    global CONTEXT_DIR
    global ASSIGNMENT_DIR
    global CANDIDATE_DETAIL_DIR
    global TEAM_LABEL

    args = parse_args()
    VIDEO_PATH = args.video
    RECONCILED_TRACKS_PATH = args.reconciled_tracks
    MAPPING_PATH = args.mapping
    EMBEDDINGS_PATH = args.embeddings
    REID_REVIEW_PATH = args.reid_review
    SEQUENTIAL_REVIEW_PATH = args.sequential_review
    OUTPUT_DIR = args.output_dir
    REPORT_PATH = args.report
    CONTEXT_DIR = OUTPUT_DIR / "boundary_context"
    ASSIGNMENT_DIR = OUTPUT_DIR / "assignment_grids"
    CANDIDATE_DETAIL_DIR = OUTPUT_DIR / "candidate_details"
    TEAM_LABEL = args.team_label
    required_paths = [
        RECONCILED_TRACKS_PATH,
        MAPPING_PATH,
        EMBEDDINGS_PATH,
        REID_REVIEW_PATH,
        SEQUENTIAL_REVIEW_PATH,
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

    rows_by_frame, rows_by_identity = sequential.load_rows(
        RECONCILED_TRACKS_PATH
    )
    mapping_report = sequential.load_json(MAPPING_PATH)
    reid_review = sequential.load_json(REID_REVIEW_PATH)
    sequential_review = sequential.load_json(
        SEQUENTIAL_REVIEW_PATH
    )
    samples_by_identity = load_embedding_samples(mapping_report)
    team_player_ids = sorted(
        identity["player_id"]
        for identity in mapping_report["identities"]
        if identity["team_label"] == TEAM_LABEL
    )
    boundaries = reviewed_boundaries(reid_review)
    minimum_frame = min(rows_by_frame)
    maximum_frame = max(rows_by_frame)
    boundary_records = []

    for boundary_index, boundary in enumerate(boundaries):
        stage_before_start = (
            minimum_frame
            if boundary_index == 0
            else boundaries[boundary_index - 1] + 1
        )
        stage_after_end = (
            maximum_frame
            if boundary_index == len(boundaries) - 1
            else boundaries[boundary_index + 1]
        )
        boundary_records.append(
            build_boundary_record(
                boundary,
                team_player_ids,
                rows_by_frame,
                rows_by_identity,
                samples_by_identity,
                reid_review,
                stage_before_start,
                stage_after_end,
            )
        )
    report = build_report(
        mapping_report,
        reid_review,
        sequential_review,
        boundary_records,
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with REPORT_PATH.open("w", encoding="utf-8") as output_file:
        json.dump(report, output_file, indent=2)
        output_file.write("\n")

    if not args.report_only:
        generate_montages(
            boundary_records,
            rows_by_frame,
            team_player_ids,
        )

    print("\nCross-track switch review preparation complete.")
    print(f"Boundaries analyzed: {len(boundary_records)}")
    print(
        "Cross-track candidates: "
        f"{report['summary']['cross_track_candidate_count']}"
    )

    for record in boundary_records:
        print_boundary(record)

    print(f"\nCandidate report saved to: {REPORT_PATH}")

    if args.report_only:
        print("Montages skipped because --report-only was supplied.")
    else:
        print(f"Review montages saved under: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
