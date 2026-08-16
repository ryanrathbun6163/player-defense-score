import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median


DEFAULT_EXPECTED_PLAYER_COUNT = 10
DEFAULT_TRACK_COUNT_TOLERANCE = 1
DEFAULT_SHORT_TRACK_MAX_FRAMES = 30
DEFAULT_MAX_HANDOFF_OVERLAP_FRAMES = 10
DEFAULT_MAX_HANDOFF_GAP_FRAMES = 30
DEFAULT_MAX_HANDOFF_DISTANCE_PIXELS = 150.0
DEFAULT_MIN_HANDOFF_TRACK_LENGTH = 20


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Audit court-filtered tracking coverage, short tracks, and "
            "possible ID handoffs."
        )
    )
    parser.add_argument(
        "--tracks",
        type=Path,
        required=True,
        help="Court-filtered tracking CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Destination tracking-audit JSON.",
    )
    frame_source = parser.add_mutually_exclusive_group(required=True)
    frame_source.add_argument(
        "--video",
        type=Path,
        help="Source video from which to read the exact frame count.",
    )
    frame_source.add_argument(
        "--frame-count",
        type=int,
        help="Exact frame count when video probing is not desired.",
    )
    parser.add_argument(
        "--expected-player-count",
        type=int,
        default=DEFAULT_EXPECTED_PLAYER_COUNT,
        help="Expected players in a complete frame.",
    )
    parser.add_argument(
        "--track-count-tolerance",
        type=int,
        default=DEFAULT_TRACK_COUNT_TOLERANCE,
        help="Accepted plus/minus range around the expected player count.",
    )
    parser.add_argument(
        "--short-track-max-frames",
        type=int,
        default=DEFAULT_SHORT_TRACK_MAX_FRAMES,
        help="Maximum detections for a track to be considered short.",
    )
    parser.add_argument(
        "--max-handoff-overlap-frames",
        type=int,
        default=DEFAULT_MAX_HANDOFF_OVERLAP_FRAMES,
    )
    parser.add_argument(
        "--max-handoff-gap-frames",
        type=int,
        default=DEFAULT_MAX_HANDOFF_GAP_FRAMES,
    )
    parser.add_argument(
        "--max-handoff-distance-pixels",
        type=float,
        default=DEFAULT_MAX_HANDOFF_DISTANCE_PIXELS,
    )
    parser.add_argument(
        "--min-handoff-track-length",
        type=int,
        default=DEFAULT_MIN_HANDOFF_TRACK_LENGTH,
    )
    args = parser.parse_args(argv)

    positive_fields = (
        "expected_player_count",
        "short_track_max_frames",
        "max_handoff_gap_frames",
        "min_handoff_track_length",
    )

    for field in positive_fields:
        if getattr(args, field) < 1:
            parser.error(f"--{field.replace('_', '-')} must be positive")

    if args.frame_count is not None and args.frame_count < 1:
        parser.error("--frame-count must be positive")

    if args.track_count_tolerance < 0:
        parser.error("--track-count-tolerance cannot be negative")

    if args.max_handoff_overlap_frames < 0:
        parser.error("--max-handoff-overlap-frames cannot be negative")

    if args.max_handoff_distance_pixels <= 0:
        parser.error("--max-handoff-distance-pixels must be positive")

    return args


def probe_frame_count(video_path):
    import cv2

    capture = cv2.VideoCapture(str(video_path))

    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    capture.release()

    if frame_count <= 0:
        raise ValueError(f"Invalid video frame count: {frame_count}")

    return frame_count


def load_rows(path):
    if not path.exists():
        raise FileNotFoundError(f"Tracking CSV not found: {path}")

    rows = []

    with path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        required_columns = {
            "frame_index",
            "track_id",
            "confidence",
            "floor_x",
            "floor_y",
        }
        missing_columns = required_columns.difference(reader.fieldnames or [])

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
        raise ValueError(f"Tracking CSV contains no detections: {path}")

    return rows


def euclidean_distance(point_a, point_b):
    return math.hypot(
        point_a[0] - point_b[0],
        point_a[1] - point_b[1],
    )


def build_audit(rows, frame_count, args):
    rows_by_track = defaultdict(list)
    track_count_by_frame = Counter()

    for row in rows:
        frame_index = row["frame_index"]

        if frame_index < 0 or frame_index >= frame_count:
            raise ValueError(
                f"Tracking row frame {frame_index} is outside "
                f"the configured {frame_count}-frame video"
            )

        rows_by_track[row["track_id"]].append(row)
        track_count_by_frame[frame_index] += 1

    for track_rows in rows_by_track.values():
        track_rows.sort(key=lambda row: row["frame_index"])

    frame_counts = [
        track_count_by_frame.get(frame_index, 0)
        for frame_index in range(frame_count)
    ]
    frame_count_distribution = dict(sorted(Counter(frame_counts).items()))
    frames_with_expected_count = sum(
        count == args.expected_player_count
        for count in frame_counts
    )
    lower_count = max(
        0,
        args.expected_player_count - args.track_count_tolerance,
    )
    upper_count = args.expected_player_count + args.track_count_tolerance
    frames_within_tolerance = sum(
        lower_count <= count <= upper_count
        for count in frame_counts
    )
    track_summaries = []

    for track_id, track_rows in rows_by_track.items():
        frames = [row["frame_index"] for row in track_rows]
        first_frame = frames[0]
        last_frame = frames[-1]
        track_span = last_frame - first_frame + 1
        gaps = [
            current_frame - previous_frame - 1
            for previous_frame, current_frame in zip(frames, frames[1:])
            if current_frame - previous_frame > 1
        ]
        first_row = track_rows[0]
        last_row = track_rows[-1]
        track_summaries.append(
            {
                "track_id": track_id,
                "first_frame": first_frame,
                "last_frame": last_frame,
                "detections": len(track_rows),
                "span_frames": track_span,
                "coverage_ratio": len(track_rows) / track_span,
                "missing_frames_inside_span": sum(gaps),
                "maximum_gap_frames": max(gaps, default=0),
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
        key=lambda summary: (-summary["detections"], summary["track_id"])
    )
    summary_by_track_id = {
        summary["track_id"]: summary
        for summary in track_summaries
    }
    short_tracks = [
        summary
        for summary in track_summaries
        if summary["detections"] <= args.short_track_max_frames
    ]
    handoff_candidates = []

    for source_id, source_rows in rows_by_track.items():
        source_summary = summary_by_track_id[source_id]

        if source_summary["detections"] < args.min_handoff_track_length:
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

            if target_summary["detections"] < args.min_handoff_track_length:
                continue

            target_first = target_rows[0]
            target_start_frame = target_first["frame_index"]
            frame_delta = target_start_frame - source_end_frame

            if not (
                -args.max_handoff_overlap_frames
                <= frame_delta
                <= args.max_handoff_gap_frames
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

            if distance > args.max_handoff_distance_pixels:
                continue

            handoff_candidates.append(
                {
                    "source_track_id": source_id,
                    "target_track_id": target_id,
                    "source_last_frame": source_end_frame,
                    "target_first_frame": target_start_frame,
                    "frame_delta": frame_delta,
                    "distance_pixels": distance,
                    "handoff_score": distance + abs(frame_delta) * 4,
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

    handoff_candidates.sort(key=lambda candidate: candidate["handoff_score"])
    return {
        "frame_counts": frame_counts,
        "frame_count_distribution": frame_count_distribution,
        "frames_with_expected_count": frames_with_expected_count,
        "frames_within_tolerance": frames_within_tolerance,
        "tolerance_range": (lower_count, upper_count),
        "rows_by_track": dict(rows_by_track),
        "track_summaries": track_summaries,
        "short_tracks": short_tracks,
        "handoff_candidates": handoff_candidates,
    }


def write_report(args, rows, frame_count, audit):
    frame_counts = audit["frame_counts"]
    lower_count, upper_count = audit["tolerance_range"]
    report = {
        "source_csv": str(args.tracks),
        "source_video": None if args.video is None else str(args.video),
        "expected_frame_count": frame_count,
        "expected_player_count": args.expected_player_count,
        "track_count_tolerance": args.track_count_tolerance,
        "total_tracked_detections": len(rows),
        "unique_track_ids": len(audit["rows_by_track"]),
        "per_frame_summary": {
            "minimum_tracks": min(frame_counts),
            "maximum_tracks": max(frame_counts),
            "average_tracks": mean(frame_counts),
            "median_tracks": median(frame_counts),
            "frames_with_exactly_10": audit["frames_with_expected_count"],
            "frames_with_exactly_10_ratio": (
                audit["frames_with_expected_count"] / frame_count
            ),
            "frames_with_9_to_11": audit["frames_within_tolerance"],
            "frames_with_9_to_11_ratio": (
                audit["frames_within_tolerance"] / frame_count
            ),
            "expected_count_label": args.expected_player_count,
            "tolerance_range": [lower_count, upper_count],
            "count_distribution": {
                str(track_count): frame_total
                for track_count, frame_total in (
                    audit["frame_count_distribution"].items()
                )
            },
        },
        "short_track_threshold_frames": args.short_track_max_frames,
        "short_track_count": len(audit["short_tracks"]),
        "short_tracks": audit["short_tracks"],
        "track_summaries": audit["track_summaries"],
        "handoff_candidate_count": len(audit["handoff_candidates"]),
        "handoff_candidates": audit["handoff_candidates"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w", encoding="utf-8") as output_file:
        json.dump(report, output_file, indent=2)
        output_file.write("\n")

    return report


def print_summary(args, frame_count, report):
    per_frame = report["per_frame_summary"]
    print("\nTracking audit complete.")
    print(f"Source: {args.tracks}")
    print(f"Tracked detections: {report['total_tracked_detections']}")
    print(f"Unique track IDs: {report['unique_track_ids']}")
    print(
        "Tracks per frame: "
        f"min={per_frame['minimum_tracks']}, "
        f"max={per_frame['maximum_tracks']}, "
        f"average={per_frame['average_tracks']:.2f}, "
        f"median={per_frame['median_tracks']:.1f}"
    )
    print(
        f"Frames with exactly {args.expected_player_count} tracks: "
        f"{per_frame['frames_with_exactly_10']}/{frame_count} "
        f"({per_frame['frames_with_exactly_10_ratio']:.1%})"
    )
    lower_count, upper_count = per_frame["tolerance_range"]
    print(
        f"Frames with {lower_count}-{upper_count} tracks: "
        f"{per_frame['frames_with_9_to_11']}/{frame_count} "
        f"({per_frame['frames_with_9_to_11_ratio']:.1%})"
    )
    print(
        f"Short tracks (<= {args.short_track_max_frames} frames): "
        f"{report['short_track_count']}"
    )
    print(f"Possible ID handoffs: {report['handoff_candidate_count']}")

    if report["handoff_candidates"]:
        print("\nTop possible ID handoffs:")

        for candidate in report["handoff_candidates"][:10]:
            print(
                "  "
                f"ID {candidate['source_track_id']} -> "
                f"ID {candidate['target_track_id']} | "
                f"frames {candidate['source_last_frame']} -> "
                f"{candidate['target_first_frame']} | "
                f"delta={candidate['frame_delta']} | "
                f"distance={candidate['distance_pixels']:.1f}px | "
                f"score={candidate['handoff_score']:.1f}"
            )

    print(f"\nAudit saved to: {args.output}")


def main(argv=None):
    args = parse_args(argv)
    frame_count = (
        args.frame_count
        if args.frame_count is not None
        else probe_frame_count(args.video)
    )
    rows = load_rows(args.tracks)
    audit = build_audit(rows, frame_count, args)
    report = write_report(args, rows, frame_count, audit)
    print_summary(args, frame_count, report)


if __name__ == "__main__":
    main()
