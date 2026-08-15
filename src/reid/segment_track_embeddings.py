import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


EMBEDDINGS_PATH = Path(
    "data/outputs/reid/"
    "possession_001_osnet_embeddings.npz"
)

SEGMENTS_OUTPUT_PATH = Path(
    "data/outputs/reid/"
    "possession_001_reid_segments.json"
)

PROTOTYPES_OUTPUT_PATH = Path(
    "data/outputs/reid/"
    "possession_001_reid_segment_prototypes.npz"
)

REVIEW_CONFIG_PATH = Path(
    "configs/possession_001_reid_review.json"
)


# Embeddings are normally sampled every five frames.
# A gap above 15 frames indicates unreliable continuity.
MAX_SAMPLE_FRAME_GAP = 15

# Compare the normalized average of three samples before a
# boundary against three samples after it.
APPEARANCE_WINDOW_SIZE = 3

# This threshold only flags a candidate. Appearance changes
# are not automatically used to split tracks.
APPEARANCE_CHANGE_THRESHOLD = 0.25

# Prevent several neighboring boundaries from reporting the
# same underlying appearance change.
MIN_CANDIDATE_SEPARATION_SAMPLES = 3


def normalized_mean(embeddings):
    prototype = np.mean(
        embeddings,
        axis=0,
    )

    norm = np.linalg.norm(prototype)

    if norm <= 0:
        raise ValueError(
            "Cannot normalize a zero prototype"
        )

    return prototype / norm


def cosine_distance(first, second):
    return 1.0 - float(
        np.dot(first, second)
    )


if not EMBEDDINGS_PATH.exists():
    raise FileNotFoundError(
        f"Embeddings not found: {EMBEDDINGS_PATH}"
    )


# ---------------------------------------------------------
# Load possession-specific reviewed split boundaries
# ---------------------------------------------------------

review_config = {}

if REVIEW_CONFIG_PATH.exists():
    with REVIEW_CONFIG_PATH.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        review_config = json.load(input_file)

manual_split_after_frames = {
    int(track_id): sorted(
        int(frame_index)
        for frame_index in split_frames
    )
    for track_id, split_frames in review_config.get(
        "manual_split_after_frames",
        {},
    ).items()
}


# ---------------------------------------------------------
# Load embeddings
# ---------------------------------------------------------

embedding_data = np.load(
    EMBEDDINGS_PATH,
    allow_pickle=False,
)

embeddings = embedding_data[
    "embeddings"
].astype(np.float32)

frame_indices = embedding_data[
    "frame_indices"
].astype(np.int32)

track_ids = embedding_data[
    "track_ids"
].astype(np.int32)

confidences = embedding_data[
    "confidences"
].astype(np.float32)

team_labels = embedding_data[
    "team_labels"
].astype(np.str_)

bounding_boxes = embedding_data[
    "bounding_boxes"
].astype(np.int32)


indices_by_track = defaultdict(list)

for embedding_index, track_id in enumerate(
    track_ids
):
    indices_by_track[
        int(track_id)
    ].append(embedding_index)

for embedding_indices in (
    indices_by_track.values()
):
    embedding_indices.sort(
        key=lambda index: int(
            frame_indices[index]
        )
    )


# ---------------------------------------------------------
# Split tracks at temporal gaps and reviewed boundaries
# ---------------------------------------------------------

temporal_segments = []
temporal_breaks = []
manual_breaks = []
used_manual_boundaries = set()

for track_id in sorted(indices_by_track):
    track_embedding_indices = (
        indices_by_track[track_id]
    )

    current_segment = [
        track_embedding_indices[0]
    ]
    current_raw_start_override = None

    for previous_index, current_index in zip(
        track_embedding_indices,
        track_embedding_indices[1:],
    ):
        previous_frame = int(
            frame_indices[previous_index]
        )
        current_frame = int(
            frame_indices[current_index]
        )

        frame_gap = (
            current_frame - previous_frame
        )

        matching_manual_boundaries = [
            boundary
            for boundary in (
                manual_split_after_frames.get(
                    track_id,
                    [],
                )
            )
            if (
                previous_frame
                <= boundary
                < current_frame
            )
        ]

        if len(matching_manual_boundaries) > 1:
            raise ValueError(
                "Multiple manual boundaries fall "
                "between the same embedding samples: "
                f"T{track_id} {previous_frame} -> "
                f"{current_frame}: "
                f"{matching_manual_boundaries}"
            )

        manual_boundary = (
            matching_manual_boundaries[0]
            if matching_manual_boundaries
            else None
        )

        temporal_gap = (
            frame_gap > MAX_SAMPLE_FRAME_GAP
        )

        if manual_boundary is not None or temporal_gap:
            temporal_segments.append(
                {
                    "track_id": track_id,
                    "embedding_indices": (
                        current_segment
                    ),
                    "raw_start_frame_override": (
                        current_raw_start_override
                    ),
                    "raw_end_frame_override": (
                        manual_boundary
                    ),
                }
            )

            if manual_boundary is not None:
                used_manual_boundaries.add(
                    (track_id, manual_boundary)
                )

                manual_breaks.append(
                    {
                        "track_id": track_id,
                        "split_after_frame": (
                            manual_boundary
                        ),
                        "before_sample_frame": (
                            previous_frame
                        ),
                        "after_sample_frame": (
                            current_frame
                        ),
                    }
                )

                next_raw_start_override = (
                    manual_boundary + 1
                )
            else:
                temporal_breaks.append(
                    {
                        "track_id": track_id,
                        "previous_frame": (
                            previous_frame
                        ),
                        "next_frame": (
                            current_frame
                        ),
                        "frame_gap": frame_gap,
                    }
                )

                next_raw_start_override = None

            current_segment = [
                current_index
            ]
            current_raw_start_override = (
                next_raw_start_override
            )

        else:
            current_segment.append(
                current_index
            )

    temporal_segments.append(
        {
            "track_id": track_id,
            "embedding_indices": (
                current_segment
            ),
            "raw_start_frame_override": (
                current_raw_start_override
            ),
            "raw_end_frame_override": None,
        }
    )


configured_manual_boundaries = {
    (track_id, boundary)
    for track_id, boundaries in (
        manual_split_after_frames.items()
    )
    for boundary in boundaries
}

unused_manual_boundaries = (
    configured_manual_boundaries
    - used_manual_boundaries
)

if unused_manual_boundaries:
    raise ValueError(
        "Manual split boundaries did not fall "
        "between sampled embeddings: "
        f"{sorted(unused_manual_boundaries)}"
    )


# ---------------------------------------------------------
# Find persistent appearance-change candidates
# ---------------------------------------------------------

appearance_candidates = []

for segment_index, segment in enumerate(
    temporal_segments
):
    embedding_indices = segment[
        "embedding_indices"
    ]

    minimum_samples = (
        APPEARANCE_WINDOW_SIZE * 2
    )

    if len(embedding_indices) < minimum_samples:
        continue

    raw_candidates = []

    for boundary_index in range(
        APPEARANCE_WINDOW_SIZE,
        len(embedding_indices)
        - APPEARANCE_WINDOW_SIZE
        + 1,
    ):
        before_indices = embedding_indices[
            boundary_index
            - APPEARANCE_WINDOW_SIZE:
            boundary_index
        ]

        after_indices = embedding_indices[
            boundary_index:
            boundary_index
            + APPEARANCE_WINDOW_SIZE
        ]

        before_prototype = normalized_mean(
            embeddings[before_indices]
        )

        after_prototype = normalized_mean(
            embeddings[after_indices]
        )

        distance = cosine_distance(
            before_prototype,
            after_prototype,
        )

        if (
            distance
            < APPEARANCE_CHANGE_THRESHOLD
        ):
            continue

        raw_candidates.append(
            {
                "segment_index": (
                    segment_index
                ),
                "track_id": (
                    segment["track_id"]
                ),
                "boundary_sample_index": (
                    boundary_index
                ),
                "before_last_frame": int(
                    frame_indices[
                        before_indices[-1]
                    ]
                ),
                "after_first_frame": int(
                    frame_indices[
                        after_indices[0]
                    ]
                ),
                "before_window_frames": [
                    int(frame_indices[index])
                    for index in before_indices
                ],
                "after_window_frames": [
                    int(frame_indices[index])
                    for index in after_indices
                ],
                "appearance_distance": (
                    distance
                ),
            }
        )

    # Keep strongest separated candidates first.
    selected_candidates = []

    for candidate in sorted(
        raw_candidates,
        key=lambda item: (
            -item["appearance_distance"]
        ),
    ):
        boundary_index = candidate[
            "boundary_sample_index"
        ]

        too_close = any(
            abs(
                boundary_index
                - selected[
                    "boundary_sample_index"
                ]
            )
            < MIN_CANDIDATE_SEPARATION_SAMPLES
            for selected in selected_candidates
        )

        if not too_close:
            selected_candidates.append(
                candidate
            )

    appearance_candidates.extend(
        selected_candidates
    )

appearance_candidates.sort(
    key=lambda item: (
        -item["appearance_distance"]
    )
)

reviewed_false_positive_keys = {
    (
        int(item["track_id"]),
        int(item["before_last_frame"]),
        int(item["after_first_frame"]),
    )
    for item in review_config.get(
        "reviewed_false_positive_boundaries",
        [],
    )
}

matched_false_positive_keys = set()

for candidate in appearance_candidates:
    candidate_key = (
        int(candidate["track_id"]),
        int(candidate["before_last_frame"]),
        int(candidate["after_first_frame"]),
    )

    if candidate_key in reviewed_false_positive_keys:
        candidate["review_decision"] = (
            "keep_continuous"
        )
        matched_false_positive_keys.add(
            candidate_key
        )
    else:
        candidate["review_decision"] = (
            "review_required"
        )

unused_false_positive_keys = (
    reviewed_false_positive_keys
    - matched_false_positive_keys
)

if unused_false_positive_keys:
    raise ValueError(
        "Reviewed false-positive boundaries "
        "were not generated as appearance "
        "candidates: "
        f"{sorted(unused_false_positive_keys)}"
    )

unresolved_appearance_candidates = [
    candidate
    for candidate in appearance_candidates
    if candidate["review_decision"]
    == "review_required"
]


# ---------------------------------------------------------
# Build segment prototypes and report records
# ---------------------------------------------------------

segment_records = []
segment_prototypes = []
segment_ids = []
segment_track_ids = []
segment_start_frames = []
segment_end_frames = []
segment_team_labels = []
segment_sample_counts = []

segment_number_by_track = Counter()

for segment in temporal_segments:
    track_id = segment["track_id"]
    embedding_indices = segment[
        "embedding_indices"
    ]

    segment_number_by_track[
        track_id
    ] += 1

    segment_number = (
        segment_number_by_track[track_id]
    )

    segment_id = (
        f"t{track_id}_s{segment_number}"
    )

    frames = [
        int(frame_indices[index])
        for index in embedding_indices
    ]

    team_votes = Counter(
        str(team_labels[index])
        for index in embedding_indices
    )

    team_label = (
        team_votes.most_common(1)[0][0]
    )

    prototype = normalized_mean(
        embeddings[embedding_indices]
    ).astype(np.float32)

    average_confidence = float(
        np.mean(
            confidences[
                embedding_indices
            ]
        )
    )

    matching_candidates = [
        candidate
        for candidate
        in appearance_candidates
        if candidate["segment_index"]
        == len(segment_records)
    ]

    segment_record = {
        "segment_id": segment_id,
        "track_id": track_id,
        "team_label": team_label,
        "start_frame": min(frames),
        "end_frame": max(frames),
        "sample_count": len(
            embedding_indices
        ),
        "average_confidence": (
            average_confidence
        ),
        "raw_start_frame_override": (
            segment.get(
                "raw_start_frame_override"
            )
        ),
        "raw_end_frame_override": (
            segment.get(
                "raw_end_frame_override"
            )
        ),
        "appearance_change_candidates": (
            matching_candidates
        ),
    }

    segment_records.append(
        segment_record
    )

    segment_prototypes.append(
        prototype
    )
    segment_ids.append(
        segment_id
    )
    segment_track_ids.append(
        track_id
    )
    segment_start_frames.append(
        min(frames)
    )
    segment_end_frames.append(
        max(frames)
    )
    segment_team_labels.append(
        team_label
    )
    segment_sample_counts.append(
        len(embedding_indices)
    )


# ---------------------------------------------------------
# Save segment prototype arrays
# ---------------------------------------------------------

PROTOTYPES_OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

np.savez_compressed(
    PROTOTYPES_OUTPUT_PATH,
    prototypes=np.stack(
        segment_prototypes
    ),
    segment_ids=np.array(
        segment_ids,
        dtype=np.str_,
    ),
    track_ids=np.array(
        segment_track_ids,
        dtype=np.int32,
    ),
    start_frames=np.array(
        segment_start_frames,
        dtype=np.int32,
    ),
    end_frames=np.array(
        segment_end_frames,
        dtype=np.int32,
    ),
    team_labels=np.array(
        segment_team_labels,
        dtype=np.str_,
    ),
    sample_counts=np.array(
        segment_sample_counts,
        dtype=np.int32,
    ),
)


# ---------------------------------------------------------
# Save readable audit report
# ---------------------------------------------------------

report = {
    "source_embeddings": str(
        EMBEDDINGS_PATH
    ),
    "settings": {
        "review_config": str(
            REVIEW_CONFIG_PATH
        ),
        "maximum_sample_frame_gap": (
            MAX_SAMPLE_FRAME_GAP
        ),
        "appearance_window_size": (
            APPEARANCE_WINDOW_SIZE
        ),
        "appearance_change_threshold": (
            APPEARANCE_CHANGE_THRESHOLD
        ),
        "minimum_candidate_separation_samples": (
            MIN_CANDIDATE_SEPARATION_SAMPLES
        ),
    },
    "raw_track_count": len(
        indices_by_track
    ),
    "temporal_segment_count": len(
        segment_records
    ),
    "temporal_break_count": len(
        temporal_breaks
    ),
    "temporal_breaks": temporal_breaks,
    "manual_break_count": len(
        manual_breaks
    ),
    "manual_breaks": manual_breaks,
    "appearance_candidate_count": len(
        appearance_candidates
    ),
    "reviewed_false_positive_count": (
        len(matched_false_positive_keys)
    ),
    "unresolved_appearance_candidate_count": (
        len(unresolved_appearance_candidates)
    ),
    "appearance_change_candidates": (
        appearance_candidates
    ),
    "segments": segment_records,
}

with SEGMENTS_OUTPUT_PATH.open(
    "w",
    encoding="utf-8",
) as output_file:
    json.dump(
        report,
        output_file,
        indent=2,
    )

    output_file.write("\n")


# ---------------------------------------------------------
# Print concise summary
# ---------------------------------------------------------

print("\nReID segment generation complete.")
print(
    f"Raw sampled tracks: "
    f"{len(indices_by_track)}"
)
print(
    f"Temporal segments: "
    f"{len(segment_records)}"
)
print(
    f"Temporal breaks: "
    f"{len(temporal_breaks)}"
)
print(
    f"Reviewed manual breaks: "
    f"{len(manual_breaks)}"
)
print(
    "Persistent appearance-change "
    f"candidates: "
    f"{len(appearance_candidates)}"
)
print(
    "Unresolved appearance-change "
    f"candidates: "
    f"{len(unresolved_appearance_candidates)}"
)

if temporal_breaks:
    print("\nTemporal breaks:")

    for item in temporal_breaks:
        print(
            "  "
            f"T{item['track_id']}: "
            f"{item['previous_frame']} -> "
            f"{item['next_frame']} "
            f"(gap {item['frame_gap']})"
        )

if manual_breaks:
    print("\nReviewed manual breaks:")

    for item in manual_breaks:
        print(
            "  "
            f"T{item['track_id']}: split after "
            f"frame {item['split_after_frame']} "
            f"(samples "
            f"{item['before_sample_frame']} -> "
            f"{item['after_sample_frame']})"
        )

if appearance_candidates:
    print(
        "\nAppearance-change candidates:"
    )

    for candidate in (
        appearance_candidates
    ):
        print(
            "  "
            f"T{candidate['track_id']}: "
            f"{candidate['before_last_frame']} -> "
            f"{candidate['after_first_frame']} | "
            f"distance="
            f"{candidate['appearance_distance']:.3f} | "
            f"decision="
            f"{candidate['review_decision']}"
        )

print(
    f"\nSegment report saved to: "
    f"{SEGMENTS_OUTPUT_PATH}"
)
print(
    f"Prototypes saved to: "
    f"{PROTOTYPES_OUTPUT_PATH}"
)
