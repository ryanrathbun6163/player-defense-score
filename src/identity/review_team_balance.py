import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

import review_cross_track_switches as cross
import review_residual_identities as residual
import review_sequential_identities as sequential


VIDEO_PATH = Path("data/clips/possession_001.mp4")
RECONCILED_TRACKS_PATH = Path(
    "data/outputs/identity/"
    "possession_001_reconciled_tracks.csv"
)
MAPPING_PATH = Path(
    "data/outputs/identity/"
    "possession_001_segment_player_mapping.json"
)
OUTPUT_DIR = Path(
    "data/outputs/identity/team_balance_review"
)
REPORT_PATH = (
    OUTPUT_DIR
    / "possession_001_team_balance_candidates.json"
)
CONTEXT_PATH = OUTPUT_DIR / "team_balance_context.jpg"
IDENTITY_GRID_PATH = OUTPUT_DIR / "team_balance_identities.jpg"

EXPECTED_TEAM_COUNT = 5
EXPECTED_ACTIVE_COUNT = 10
CONTEXT_TILE_SIZE = (560, 315)
IDENTITY_TILE_SIZE = (360, 320)
TEXT_COLOR = (255, 255, 255)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Generate clean identity evidence for frames whose "
            "reviewed team counts are not five versus five."
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


def team_counts(rows):
    return Counter(row["reconciled_team"] for row in rows)


def choose_context_frames(imbalanced_frames):
    if not imbalanced_frames:
        return []

    indices = sorted(
        {
            0,
            len(imbalanced_frames) // 2,
            len(imbalanced_frames) - 1,
        }
    )
    return [imbalanced_frames[index] for index in indices]


def choose_identity_rows(
    player_id,
    rows_by_identity,
    rows_by_frame,
    first_frame,
    last_frame,
):
    rows = [
        row
        for row in rows_by_identity.get(player_id, [])
        if first_frame <= row["frame_index"] <= last_frame
    ]

    if not rows:
        return []

    return cross.choose_clean_review_rows(
        player_id,
        rows_by_identity,
        rows_by_frame,
        rows[0]["frame_index"],
        rows[-1]["frame_index"],
        "CLEAN",
    )


def build_report(rows_by_frame, rows_by_identity, mapping_report):
    ten_player_frames = [
        frame_index
        for frame_index, rows in sorted(rows_by_frame.items())
        if len(rows) == EXPECTED_ACTIVE_COUNT
    ]
    imbalanced_frames = [
        frame_index
        for frame_index in ten_player_frames
        if (
            team_counts(rows_by_frame[frame_index]).get("white", 0)
            > EXPECTED_TEAM_COUNT
            or team_counts(rows_by_frame[frame_index]).get("dark", 0)
            > EXPECTED_TEAM_COUNT
        )
    ]

    if not imbalanced_frames:
        return {
            "reconciled_tracks": str(RECONCILED_TRACKS_PATH),
            "identity_mapping": str(MAPPING_PATH),
            "summary": {
                "ten_player_frame_count": len(ten_player_frames),
                "imbalanced_ten_player_frame_count": 0,
                "review_identity_count": 0,
            },
            "context_frames": [],
            "team_count_distribution": {},
            "review_identities": [],
            "review_conclusion": (
                "All ten-player frames have five reviewed white "
                "and five reviewed dark identities."
            ),
        }

    first_frame = min(imbalanced_frames)
    last_frame = max(imbalanced_frames)
    review_player_ids = sorted(
        {
            row["player_id"]
            for frame_index in imbalanced_frames
            for row in rows_by_frame[frame_index]
        }
    )
    identity_by_id = {
        identity["player_id"]: identity
        for identity in mapping_report["identities"]
    }
    review_identities = []

    for player_id in review_player_ids:
        identity = identity_by_id[player_id]
        review_identities.append(
            {
                "player_id": player_id,
                "reviewed_team": identity["team_label"],
                "segment_ids": identity["segment_ids"],
                "raw_track_ids": identity["raw_track_ids"],
                "clean_review_frames": choose_identity_rows(
                    player_id,
                    rows_by_identity,
                    rows_by_frame,
                    first_frame,
                    last_frame,
                ),
            }
        )

    count_distribution = Counter(
        (
            team_counts(rows_by_frame[frame_index]).get("white", 0),
            team_counts(rows_by_frame[frame_index]).get("dark", 0),
            team_counts(rows_by_frame[frame_index]).get("unknown", 0),
        )
        for frame_index in ten_player_frames
    )

    return {
        "reconciled_tracks": str(RECONCILED_TRACKS_PATH),
        "identity_mapping": str(MAPPING_PATH),
        "summary": {
            "ten_player_frame_count": len(ten_player_frames),
            "imbalanced_ten_player_frame_count": len(
                imbalanced_frames
            ),
            "first_imbalanced_frame": first_frame,
            "last_imbalanced_frame": last_frame,
            "review_identity_count": len(review_identities),
        },
        "context_frames": choose_context_frames(
            imbalanced_frames
        ),
        "team_count_distribution": {
            f"white_{white}_dark_{dark}_unknown_{unknown}": count
            for (white, dark, unknown), count in sorted(
                count_distribution.items()
            )
        },
        "review_identities": review_identities,
        "review_requirement": (
            "Compare uniform color, jersey number, body, and "
            "trajectory. A team-count mismatch is diagnostic "
            "evidence, not permission to force a relabel."
        ),
    }


def identity_color(player_id, player_ids):
    return cross.identity_color(player_id, player_ids)


def context_montage(report, frames, rows_by_frame, player_ids):
    tiles = []

    for frame_index in report["context_frames"]:
        annotated = frames[frame_index].copy()

        for row in rows_by_frame[frame_index]:
            residual.draw_label(
                annotated,
                row,
                identity_color(row["player_id"], player_ids),
                4,
            )

        counts = team_counts(rows_by_frame[frame_index])
        header = (
            f"frame {frame_index} | white={counts.get('white', 0)} "
            f"dark={counts.get('dark', 0)} "
            f"unknown={counts.get('unknown', 0)}"
        )
        tiles.append(
            residual.add_header(
                residual.fit_to_tile(
                    annotated,
                    CONTEXT_TILE_SIZE,
                ),
                header,
                TEXT_COLOR,
            )
        )

    row = np.hstack(tiles)
    title = residual.title_panel(
        row.shape[1],
        [
            "TEAM BALANCE REVIEW | representative ten-player frames",
            (
                "Colors identify current player IDs; verify the "
                "actual uniform color for every labeled identity."
            ),
        ],
        TEXT_COLOR,
    )
    return np.vstack([title, row])


def identity_tile(
    review_frame,
    frames,
    rows_by_frame,
    player_ids,
):
    frame_index = review_frame["frame_index"]
    player_id = review_frame["player_id"]
    row = cross.find_player_row(
        rows_by_frame[frame_index],
        player_id,
    )
    color = identity_color(player_id, player_ids)
    annotated = frames[frame_index].copy()
    residual.draw_label(annotated, row, color, 5)
    zoom = cross.player_zoom(annotated, row)
    return residual.add_header(
        residual.fit_to_tile(zoom, IDENTITY_TILE_SIZE),
        (
            f"{player_id} | f{frame_index} | "
            f"conf={row['confidence']:.2f} | "
            f"max IoU={review_frame['maximum_other_iou']:.2f}"
        ),
        color,
    )


def identity_grid(report, frames, rows_by_frame, player_ids):
    rows = []

    for identity in report["review_identities"]:
        review_frames = identity["clean_review_frames"]

        if len(review_frames) != 3:
            raise ValueError(
                "Expected three clean review frames for "
                f"{identity['player_id']}, got {len(review_frames)}."
            )

        tiles = [
            identity_tile(
                review_frame,
                frames,
                rows_by_frame,
                player_ids,
            )
            for review_frame in review_frames
        ]
        tile_row = np.hstack(tiles)
        color = identity_color(
            identity["player_id"],
            player_ids,
        )
        row_title = residual.title_panel(
            tile_row.shape[1],
            [
                (
                    f"{identity['player_id']} | reviewed team="
                    f"{identity['reviewed_team']} | segments="
                    f"{','.join(identity['segment_ids'])}"
                )
            ],
            color,
        )
        rows.extend([row_title, tile_row])

    width = rows[0].shape[1]
    title = residual.title_panel(
        width,
        [
            "TEAM BALANCE REVIEW | clean identity samples",
            (
                "Three low-overlap crops per identity; compare "
                "uniform color before considering any override."
            ),
        ],
        TEXT_COLOR,
    )
    return np.vstack([title] + rows)


def generate_montages(report, rows_by_frame):
    requested_frames = set(report["context_frames"])
    requested_frames.update(
        review_frame["frame_index"]
        for identity in report["review_identities"]
        for review_frame in identity["clean_review_frames"]
    )
    frames = cross.read_frames(requested_frames)
    player_ids = sorted(
        identity["player_id"]
        for identity in report["review_identities"]
    )
    cross.write_montage(
        CONTEXT_PATH,
        context_montage(
            report,
            frames,
            rows_by_frame,
            player_ids,
        ),
    )
    cross.write_montage(
        IDENTITY_GRID_PATH,
        identity_grid(
            report,
            frames,
            rows_by_frame,
            player_ids,
        ),
    )
    print(f"  Saved context: {CONTEXT_PATH}")
    print(f"  Saved identities: {IDENTITY_GRID_PATH}")


def main():
    args = parse_args()
    required_paths = [RECONCILED_TRACKS_PATH, MAPPING_PATH]

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
    report = build_report(
        rows_by_frame,
        rows_by_identity,
        mapping_report,
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with REPORT_PATH.open("w", encoding="utf-8") as output_file:
        json.dump(report, output_file, indent=2)
        output_file.write("\n")

    summary = report["summary"]
    print("\nTeam-balance review preparation complete.")
    print(
        "Ten-player frames: "
        f"{summary['ten_player_frame_count']}"
    )
    print(
        "Imbalanced ten-player frames: "
        f"{summary['imbalanced_ten_player_frame_count']}"
    )
    print(
        "Identities included for review: "
        f"{summary['review_identity_count']}"
    )

    if not args.report_only and report["review_identities"]:
        print("\nGenerating team-balance review montages...")
        generate_montages(report, rows_by_frame)

    print(f"\nCandidate report saved to: {REPORT_PATH}")

    if args.report_only:
        print("Montages skipped because --report-only was supplied.")
    elif report["review_identities"]:
        print(f"Review montages saved under: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
