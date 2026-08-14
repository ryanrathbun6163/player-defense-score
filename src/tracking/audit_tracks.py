import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median


TRACKS_CSV_PATH = Path(
    "data/outputs/tracking/"
    "possession_001_court_filtered_tracks.csv"
)

AUDIT_OUTPUT_PATH = Path(
    "data/outputs/tracking/"
    "possession_001_tracking_audit.json"
)

EXPECTED_FRAME_COUNT = 499
SHORT_TRACK_MAX_FRAMES = 30

# Candidate handoffs may overlap briefly because ByteTrack can
# temporarily assign two IDs to the same person.
MAX_HANDOFF_OVERLAP_FRAMES = 10
MAX_HANDOFF_GAP_FRAMES = 30
MAX_HANDOFF_DISTANCE_PIXELS = 150
MIN_HANDOFF_TRACK_LENGTH = 20


def euclidean_distance(point_a, point_b):
    return math.hypot(
        point_a[0] - point_b[0],
        point_a[1] - point_b[1],
    )


if not TRACKS_CSV_PATH.exists():
    raise FileNotFoundError(
        f"Tracking CSV not found: {TRACKS_CSV_PATH}"
    )


# ---------------------------------------------------------
# Read tracking rows
# ---------------------------------------------------------

rows = []

with TRACKS_CSV_PATH.open(
    "r",
    newline="",
    encoding="utf-8",
) as csv_file:
    reader = csv.DictReader(csv_file)

    required_columns = {
        "frame_index",
        "track_id",
        "confidence",
        "floor_x",
        "floor_y",
    }

    missing_columns = required_columns.difference(
        reader.fieldnames or []
    )

    if missing_columns:
        raise ValueError(
            "Tracking CSV is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    for row in reader:
        rows.append(
            {
                "frame_index": int(row["frame_index"]),
                "track_id": int(row["track_id"]),
                "confidence": float(row["confidence"]),
                "floor_x": float(row["floor_x"]),
                "floor_y": float(row["floor_y"]),
            }
        )

if not rows:
    raise ValueError(
        f"Tracking CSV contains no detections: {TRACKS_CSV_PATH}"
    )


# ---------------------------------------------------------
# Organize rows by frame and track
# ---------------------------------------------------------

rows_by_track = defaultdict(list)
track_count_by_frame = Counter()

for row in rows:
    rows_by_track[row["track_id"]].append(row)
    track_count_by_frame[row["frame_index"]] += 1

for track_rows in rows_by_track.values():
    track_rows.sort(
        key=lambda row: row["frame_index"]
    )


# ---------------------------------------------------------
# Calculate per-frame statistics
# ---------------------------------------------------------

frame_counts = [
    track_count_by_frame.get(frame_index, 0)
    for frame_index in range(EXPECTED_FRAME_COUNT)
]

frame_count_distribution = dict(
    sorted(Counter(frame_counts).items())
)

frames_with_exactly_10 = sum(
    count == 10
    for count in frame_counts
)

frames_with_9_to_11 = sum(
    9 <= count <= 11
    for count in frame_counts
)


# ---------------------------------------------------------
# Calculate per-track statistics
# ---------------------------------------------------------

track_summaries = []

for track_id, track_rows in rows_by_track.items():
    frames = [
        row["frame_index"]
        for row in track_rows
    ]

    first_frame = frames[0]
    last_frame = frames[-1]
    track_span = last_frame - first_frame + 1

    gaps = [
        current_frame - previous_frame - 1
        for previous_frame, current_frame in zip(
            frames,
            frames[1:],
        )
        if current_frame - previous_frame > 1
    ]

    missing_frames_inside_span = sum(gaps)
    maximum_gap = max(gaps, default=0)

    first_row = track_rows[0]
    last_row = track_rows[-1]

    track_summaries.append(
        {
            "track_id": track_id,
            "first_frame": first_frame,
            "last_frame": last_frame,
            "detections": len(track_rows),
            "span_frames": track_span,
            "coverage_ratio": (
                len(track_rows) / track_span
            ),
            "missing_frames_inside_span": (
                missing_frames_inside_span
            ),
            "maximum_gap_frames": maximum_gap,
            "average_confidence": mean(
                row["confidence"]
                for row in track_rows
            ),
            "start_position": {
                "x": first_row["floor_x"],
                "y": first_row["floor_y"],
            },
            "end_position": {
                "x": last_row["floor_x"],
                "y": last_row["floor_y"],
            },
        }
    )

track_summaries.sort(
    key=lambda summary: (
        -summary["detections"],
        summary["track_id"],
    )
)

summary_by_track_id = {
    summary["track_id"]: summary
    for summary in track_summaries
}

short_tracks = [
    summary
    for summary in track_summaries
    if summary["detections"] <= SHORT_TRACK_MAX_FRAMES
]


# ---------------------------------------------------------
# Find possible ID handoffs
# ---------------------------------------------------------

handoff_candidates = []

for source_id, source_rows in rows_by_track.items():
    source_summary = summary_by_track_id[source_id]

    if (
        source_summary["detections"]
        < MIN_HANDOFF_TRACK_LENGTH
    ):
        continue

    source_last = source_rows[-1]
    source_end_frame = source_last["frame_index"]
    source_end_position = (
        source_last["floor_x"],
        source_last["floor_y"],
    )

    for target_id, target_rows in rows_by_track.items():
        if source_id == target_id:
            continue

        target_summary = summary_by_track_id[target_id]

        if (
            target_summary["detections"]
            < MIN_HANDOFF_TRACK_LENGTH
        ):
            continue

        target_first = target_rows[0]
        target_start_frame = target_first["frame_index"]

        frame_delta = (
            target_start_frame - source_end_frame
        )

        if not (
            -MAX_HANDOFF_OVERLAP_FRAMES
            <= frame_delta
            <= MAX_HANDOFF_GAP_FRAMES
        ):
            continue

        target_start_position = (
            target_first["floor_x"],
            target_first["floor_y"],
        )

        distance = euclidean_distance(
            source_end_position,
            target_start_position,
        )

        if distance > MAX_HANDOFF_DISTANCE_PIXELS:
            continue

        # Lower scores represent more plausible handoffs.
        handoff_score = (
            distance
            + abs(frame_delta) * 4
        )

        handoff_candidates.append(
            {
                "source_track_id": source_id,
                "target_track_id": target_id,
                "source_last_frame": source_end_frame,
                "target_first_frame": (
                    target_start_frame
                ),
                "frame_delta": frame_delta,
                "distance_pixels": distance,
                "handoff_score": handoff_score,
                "source_end_position": {
                    "x": source_end_position[0],
                    "y": source_end_position[1],
                },
                "target_start_position": {
                    "x": target_start_position[0],
                    "y": target_start_position[1],
                },
            }
        )

handoff_candidates.sort(
    key=lambda candidate: candidate["handoff_score"]
)


# ---------------------------------------------------------
# Build and save audit report
# ---------------------------------------------------------

audit_report = {
    "source_csv": str(TRACKS_CSV_PATH),
    "expected_frame_count": EXPECTED_FRAME_COUNT,
    "total_tracked_detections": len(rows),
    "unique_track_ids": len(rows_by_track),
    "per_frame_summary": {
        "minimum_tracks": min(frame_counts),
        "maximum_tracks": max(frame_counts),
        "average_tracks": mean(frame_counts),
        "median_tracks": median(frame_counts),
        "frames_with_exactly_10": frames_with_exactly_10,
        "frames_with_exactly_10_ratio": (
            frames_with_exactly_10
            / EXPECTED_FRAME_COUNT
        ),
        "frames_with_9_to_11": frames_with_9_to_11,
        "frames_with_9_to_11_ratio": (
            frames_with_9_to_11
            / EXPECTED_FRAME_COUNT
        ),
        "count_distribution": {
            str(track_count): frame_total
            for track_count, frame_total
            in frame_count_distribution.items()
        },
    },
    "short_track_threshold_frames": (
        SHORT_TRACK_MAX_FRAMES
    ),
    "short_track_count": len(short_tracks),
    "short_tracks": short_tracks,
    "track_summaries": track_summaries,
    "handoff_candidate_count": len(
        handoff_candidates
    ),
    "handoff_candidates": handoff_candidates,
}

AUDIT_OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

with AUDIT_OUTPUT_PATH.open(
    "w",
    encoding="utf-8",
) as output_file:
    json.dump(
        audit_report,
        output_file,
        indent=2,
    )

    output_file.write("\n")


# ---------------------------------------------------------
# Print concise terminal report
# ---------------------------------------------------------

print("\nTracking audit complete.")
print(f"Source: {TRACKS_CSV_PATH}")
print(f"Tracked detections: {len(rows)}")
print(f"Unique track IDs: {len(rows_by_track)}")
print(
    "Tracks per frame: "
    f"min={min(frame_counts)}, "
    f"max={max(frame_counts)}, "
    f"average={mean(frame_counts):.2f}, "
    f"median={median(frame_counts):.1f}"
)
print(
    "Frames with exactly 10 tracks: "
    f"{frames_with_exactly_10}/"
    f"{EXPECTED_FRAME_COUNT} "
    f"({frames_with_exactly_10 / EXPECTED_FRAME_COUNT:.1%})"
)
print(
    "Frames with 9-11 tracks: "
    f"{frames_with_9_to_11}/"
    f"{EXPECTED_FRAME_COUNT} "
    f"({frames_with_9_to_11 / EXPECTED_FRAME_COUNT:.1%})"
)
print(
    f"Short tracks "
    f"(<= {SHORT_TRACK_MAX_FRAMES} frames): "
    f"{len(short_tracks)}"
)
print(
    "Possible ID handoffs: "
    f"{len(handoff_candidates)}"
)

if handoff_candidates:
    print("\nTop possible ID handoffs:")

    for candidate in handoff_candidates[:10]:
        print(
            "  "
            f"ID {candidate['source_track_id']} -> "
            f"ID {candidate['target_track_id']} | "
            f"frames "
            f"{candidate['source_last_frame']} -> "
            f"{candidate['target_first_frame']} | "
            f"delta={candidate['frame_delta']} | "
            f"distance="
            f"{candidate['distance_pixels']:.1f}px | "
            f"score="
            f"{candidate['handoff_score']:.1f}"
        )

print(f"\nAudit saved to: {AUDIT_OUTPUT_PATH}")