import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

import review_cross_track_switches as cross
import review_residual_identities as residual


VIDEO_PATH = Path("data/clips/possession_001.mp4")
CLASSIFIED_TRACKS_PATH = Path(
    "data/outputs/classification/"
    "possession_001_team_classified_tracks.csv"
)
OUTPUT_DIR = Path(
    "data/outputs/identity/track_phase_review"
)
REPORT_PATH = (
    OUTPUT_DIR
    / "possession_001_track_phase_candidates.json"
)
MONTAGE_DIR = OUTPUT_DIR / "track_phases"

PHASES = [
    {
        "phase_id": "pre_270",
        "label": "PRE 270",
        "first_frame": 1,
        "last_frame": 270,
    },
    {
        "phase_id": "frames_271_312",
        "label": "FRAMES 271-312",
        "first_frame": 271,
        "last_frame": 312,
    },
    {
        "phase_id": "middle_313_452",
        "label": "MIDDLE 313-452",
        "first_frame": 313,
        "last_frame": 452,
    },
    {
        "phase_id": "post_452",
        "label": "POST 452",
        "first_frame": 453,
        "last_frame": 498,
    },
]

LINEAGES = [
    {
        "lineage_id": "t7_t29",
        "label": "T7 / T29 lineage",
        "phase_track_ids": {
            "pre_270": [7],
            "frames_271_312": [7],
            "middle_313_452": [7],
            "post_452": [7, 29],
        },
    },
    {
        "lineage_id": "t8",
        "label": "T8 lineage",
        "phase_track_ids": {
            "pre_270": [8],
            "frames_271_312": [8],
            "middle_313_452": [8],
            "post_452": [8],
        },
    },
    {
        "lineage_id": "t19_t33",
        "label": "T19 / T33 lineage",
        "phase_track_ids": {
            "pre_270": [19],
            "frames_271_312": [19],
            "middle_313_452": [19],
            "post_452": [19, 33],
        },
        "phase_window_overrides": {
            "pre_270": [223, 270]
        },
    },
]

TILE_SIZE = (390, 340)
PHASE_COLORS = {
    "pre_270": (255, 210, 60),
    "frames_271_312": (80, 220, 80),
    "middle_313_452": (0, 215, 255),
    "post_452": (255, 80, 220),
}
TEXT_COLOR = (255, 255, 255)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Generate clean raw-track crops for the three "
            "identity phases around frames 270, 312, and 452."
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


def load_rows():
    rows_by_frame = defaultdict(list)
    rows_by_track = defaultdict(list)

    with CLASSIFIED_TRACKS_PATH.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as input_file:
        for raw_row in csv.DictReader(input_file):
            row = dict(raw_row)
            row["frame_index"] = int(raw_row["frame_index"])
            row["track_id"] = int(raw_row["track_id"])
            row["confidence"] = float(raw_row["confidence"])

            for field in (
                "x1",
                "y1",
                "x2",
                "y2",
                "floor_x",
                "floor_y",
            ):
                row[field] = float(raw_row[field])

            row["player_id"] = f"raw_T{row['track_id']}"
            row["reconciled_team"] = row["team_label"]
            rows_by_frame[row["frame_index"]].append(row)
            rows_by_track[row["track_id"]].append(row)

    for rows in rows_by_frame.values():
        rows.sort(key=lambda row: row["track_id"])

    for rows in rows_by_track.values():
        rows.sort(key=lambda row: row["frame_index"])

    return dict(rows_by_frame), dict(rows_by_track)


def box_area(row):
    return max(0.0, row["x2"] - row["x1"]) * max(
        0.0,
        row["y2"] - row["y1"],
    )


def maximum_other_iou(row, rows_by_frame, family_track_ids):
    return max(
        (
            residual.bounding_box_iou(row, other)
            for other in rows_by_frame[row["frame_index"]]
            if other["track_id"] not in family_track_ids
        ),
        default=0.0,
    )


def clean_score(row, rows_by_frame, family_track_ids):
    overlap = maximum_other_iou(
        row,
        rows_by_frame,
        family_track_ids,
    )
    area_bonus = min(box_area(row) / 40000.0, 1.0)
    return row["confidence"] - 2.0 * overlap + 0.15 * area_bonus


def choose_phase_rows(
    track_ids,
    first_frame,
    last_frame,
    rows_by_frame,
    rows_by_track,
):
    candidates = sorted(
        (
            row
            for track_id in track_ids
            for row in rows_by_track.get(track_id, [])
            if first_frame <= row["frame_index"] <= last_frame
        ),
        key=lambda row: (row["frame_index"], row["track_id"]),
    )

    if not candidates:
        raise ValueError(
            f"No rows for tracks {track_ids} in "
            f"{first_frame}-{last_frame}."
        )

    actual_first = candidates[0]["frame_index"]
    actual_last = candidates[-1]["frame_index"]
    selected = []

    for bucket_index in range(3):
        bucket_start = (
            actual_first
            + (actual_last - actual_first + 1)
            * bucket_index
            // 3
        )
        bucket_end = (
            actual_first
            + (actual_last - actual_first + 1)
            * (bucket_index + 1)
            // 3
            - 1
        )
        bucket_rows = [
            row
            for row in candidates
            if bucket_start <= row["frame_index"] <= bucket_end
        ]

        if not bucket_rows:
            continue

        row = max(
            bucket_rows,
            key=lambda candidate: (
                clean_score(
                    candidate,
                    rows_by_frame,
                    set(track_ids),
                ),
                candidate["confidence"],
                box_area(candidate),
                -candidate["frame_index"],
            ),
        )
        selected.append(
            {
                "frame_index": row["frame_index"],
                "track_id": row["track_id"],
                "classified_team": row["team_label"],
                "confidence": row["confidence"],
                "maximum_other_iou": maximum_other_iou(
                    row,
                    rows_by_frame,
                    set(track_ids),
                ),
                "clean_score": clean_score(
                    row,
                    rows_by_frame,
                    set(track_ids),
                ),
            }
        )

    if len(selected) != 3:
        raise ValueError(
            "Expected three phase samples for tracks "
            f"{track_ids} in {first_frame}-{last_frame}, "
            f"got {len(selected)}."
        )

    return selected


def build_report(rows_by_frame, rows_by_track):
    lineages = []

    for lineage in LINEAGES:
        phase_records = []

        for phase in PHASES:
            phase_id = phase["phase_id"]
            track_ids = lineage["phase_track_ids"][phase_id]
            window = lineage.get(
                "phase_window_overrides",
                {},
            ).get(
                phase_id,
                [phase["first_frame"], phase["last_frame"]],
            )
            phase_records.append(
                {
                    "phase_id": phase_id,
                    "phase_label": phase["label"],
                    "review_window": window,
                    "track_ids": track_ids,
                    "clean_review_frames": choose_phase_rows(
                        track_ids,
                        window[0],
                        window[1],
                        rows_by_frame,
                        rows_by_track,
                    ),
                }
            )

        lineages.append(
            {
                "lineage_id": lineage["lineage_id"],
                "label": lineage["label"],
                "phases": phase_records,
            }
        )

    return {
        "classified_tracks": str(CLASSIFIED_TRACKS_PATH),
        "reviewed_boundaries": [270, 312, 452],
        "lineage_count": len(lineages),
        "lineages": lineages,
        "review_requirement": (
            "Compare actual uniform color, jersey number, build, "
            "and hair across the four phases. The stored team "
            "classification is shown only as historical metadata."
        ),
    }


def find_row(rows_by_frame, frame_index, track_id):
    return next(
        row
        for row in rows_by_frame[frame_index]
        if row["track_id"] == track_id
    )


def phase_tile(
    phase,
    review_frame,
    frames,
    rows_by_frame,
):
    frame_index = review_frame["frame_index"]
    track_id = review_frame["track_id"]
    row = find_row(rows_by_frame, frame_index, track_id)
    color = PHASE_COLORS[phase["phase_id"]]
    annotated = frames[frame_index].copy()
    residual.draw_label(annotated, row, color, 5)
    zoom = cross.player_zoom(annotated, row)
    return residual.add_header(
        residual.fit_to_tile(zoom, TILE_SIZE),
        (
            f"{phase['phase_label']} | T{track_id} | "
            f"f{frame_index} | stored={row['team_label']} | "
            f"IoU={review_frame['maximum_other_iou']:.2f}"
        ),
        color,
    )


def create_lineage_montage(
    lineage,
    frames,
    rows_by_frame,
):
    montage_rows = []

    for phase in lineage["phases"]:
        tiles = [
            phase_tile(
                phase,
                review_frame,
                frames,
                rows_by_frame,
            )
            for review_frame in phase["clean_review_frames"]
        ]
        montage_rows.append(np.hstack(tiles))

    width = montage_rows[0].shape[1]
    title = residual.title_panel(
        width,
        [
            f"RAW TRACK PHASE REVIEW | {lineage['label']}",
            (
                "Rows are pre-270, 271-312, 313-452, and post-452; "
                "compare uniform and jersey cues across rows."
            ),
        ],
        TEXT_COLOR,
    )
    return np.vstack([title] + montage_rows)


def generate_montages(report, rows_by_frame):
    requested_frames = {
        review_frame["frame_index"]
        for lineage in report["lineages"]
        for phase in lineage["phases"]
        for review_frame in phase["clean_review_frames"]
    }
    frames = cross.read_frames(requested_frames)

    print("\nGenerating raw-track phase montages...")

    for lineage in report["lineages"]:
        path = MONTAGE_DIR / f"{lineage['lineage_id']}_phases.jpg"
        cross.write_montage(
            path,
            create_lineage_montage(
                lineage,
                frames,
                rows_by_frame,
            ),
        )
        print(f"  Saved: {path}")


def main():
    args = parse_args()

    if not CLASSIFIED_TRACKS_PATH.exists():
        raise FileNotFoundError(
            f"Classified tracks not found: {CLASSIFIED_TRACKS_PATH}"
        )

    if not args.report_only and not VIDEO_PATH.exists():
        raise FileNotFoundError(f"Video not found: {VIDEO_PATH}")

    if not args.report_only and residual.cv2 is None:
        raise ModuleNotFoundError(
            "OpenCV is required to generate review montages. "
            "Install opencv-python or run with --report-only."
        )

    rows_by_frame, rows_by_track = load_rows()
    report = build_report(rows_by_frame, rows_by_track)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with REPORT_PATH.open("w", encoding="utf-8") as output_file:
        json.dump(report, output_file, indent=2)
        output_file.write("\n")

    print("\nRaw-track phase review preparation complete.")
    print(f"Lineages reviewed: {report['lineage_count']}")

    for lineage in report["lineages"]:
        print(f"\n{lineage['label']}:")

        for phase in lineage["phases"]:
            samples = ", ".join(
                (
                    f"T{sample['track_id']}@"
                    f"{sample['frame_index']}"
                )
                for sample in phase["clean_review_frames"]
            )
            print(f"  {phase['phase_label']}: {samples}")

    if not args.report_only:
        generate_montages(report, rows_by_frame)

    print(f"\nCandidate report saved to: {REPORT_PATH}")

    if args.report_only:
        print("Montages skipped because --report-only was supplied.")
    else:
        print(f"Review montages saved under: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
