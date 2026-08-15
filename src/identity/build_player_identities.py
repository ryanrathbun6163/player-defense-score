import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


CLASSIFIED_TRACKS_PATH = Path(
    "data/outputs/classification/"
    "possession_001_team_classified_tracks.csv"
)

SEGMENTS_REPORT_PATH = Path(
    "data/outputs/reid/"
    "possession_001_reid_segments.json"
)

MATCH_REPORT_PATH = Path(
    "data/outputs/reid/"
    "possession_001_segment_match_candidates.json"
)

OUTPUT_DIR = Path(
    "data/outputs/identity"
)

MAPPING_OUTPUT_PATH = (
    OUTPUT_DIR
    / "possession_001_segment_player_mapping.json"
)

ANNOTATED_OUTPUT_PATH = (
    OUTPUT_DIR
    / "possession_001_identity_annotated_tracks.csv"
)

RECONCILED_OUTPUT_PATH = (
    OUTPUT_DIR
    / "possession_001_reconciled_tracks.csv"
)


TEAM_ORDER = {
    "white": 0,
    "dark": 1,
    "unknown": 2,
}


class DisjointSet:
    def __init__(self, items):
        self.parent = {
            item: item
            for item in items
        }

    def find(self, item):
        parent = self.parent[item]

        if parent != item:
            self.parent[item] = self.find(
                parent
            )

        return self.parent[item]

    def union(self, first, second):
        first_root = self.find(first)
        second_root = self.find(second)

        if first_root == second_root:
            return

        canonical_root = min(
            first_root,
            second_root,
        )
        other_root = (
            second_root
            if canonical_root == first_root
            else first_root
        )

        self.parent[other_root] = (
            canonical_root
        )


def load_csv_rows(path):
    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as input_file:
        reader = csv.DictReader(input_file)

        if reader.fieldnames is None:
            raise ValueError(
                f"CSV has no header: {path}"
            )

        return (
            list(reader.fieldnames),
            [dict(row) for row in reader],
        )


def load_json(path):
    with path.open(
        "r",
        encoding="utf-8",
    ) as input_file:
        return json.load(input_file)


def segment_boundary(
    first_segment,
    second_segment,
):
    first_end_override = first_segment.get(
        "raw_end_frame_override"
    )
    second_start_override = second_segment.get(
        "raw_start_frame_override"
    )

    if (
        first_end_override is not None
        and second_start_override is not None
        and int(second_start_override)
        != int(first_end_override) + 1
    ):
        raise ValueError(
            "Conflicting raw-frame overrides: "
            f"{first_segment['segment_id']} -> "
            f"{second_segment['segment_id']}"
        )

    if first_end_override is not None:
        return int(first_end_override)

    if second_start_override is not None:
        return int(second_start_override) - 1

    return (
        int(first_segment["end_frame"])
        + int(second_segment["start_frame"])
    ) // 2


def infer_track_team(rows):
    team_counts = Counter(
        row.get("team_label", "unknown")
        for row in rows
    )

    known_counts = {
        team: count
        for team, count in team_counts.items()
        if team in {"white", "dark"}
    }

    if known_counts:
        return max(
            known_counts,
            key=lambda team: (
                known_counts[team],
                -TEAM_ORDER[team],
            ),
        )

    return "unknown"


def build_segment_assignments(
    raw_rows,
    sampled_segments,
):
    rows_by_track = defaultdict(list)

    for row in raw_rows:
        rows_by_track[
            int(row["track_id"])
        ].append(row)

    for track_rows in rows_by_track.values():
        track_rows.sort(
            key=lambda row: int(
                row["frame_index"]
            )
        )

    segments_by_track = defaultdict(list)

    for segment in sampled_segments:
        segments_by_track[
            int(segment["track_id"])
        ].append(dict(segment))

    for track_segments in (
        segments_by_track.values()
    ):
        track_segments.sort(
            key=lambda segment: (
                int(segment["start_frame"])
            )
        )

    all_segments = []
    assignment_bounds = {}

    for track_id, track_rows in sorted(
        rows_by_track.items()
    ):
        first_raw_frame = int(
            track_rows[0]["frame_index"]
        )
        last_raw_frame = int(
            track_rows[-1]["frame_index"]
        )

        track_segments = segments_by_track.get(
            track_id,
            [],
        )

        if not track_segments:
            fallback_segment_id = (
                f"t{track_id}_fallback"
            )

            fallback_segment = {
                "segment_id": fallback_segment_id,
                "track_id": track_id,
                "team_label": infer_track_team(
                    track_rows
                ),
                "start_frame": first_raw_frame,
                "end_frame": last_raw_frame,
                "sample_count": 0,
                "average_confidence": None,
                "raw_start_frame_override": (
                    first_raw_frame
                ),
                "raw_end_frame_override": (
                    last_raw_frame
                ),
                "segment_source": (
                    "fallback_no_reid_samples"
                ),
            }

            all_segments.append(
                fallback_segment
            )
            assignment_bounds[
                fallback_segment_id
            ] = (
                first_raw_frame,
                last_raw_frame,
            )
            continue

        boundaries = [
            segment_boundary(first, second)
            for first, second in zip(
                track_segments,
                track_segments[1:],
            )
        ]

        for index, segment in enumerate(
            track_segments
        ):
            lower_frame = (
                first_raw_frame
                if index == 0
                else boundaries[index - 1] + 1
            )
            upper_frame = (
                last_raw_frame
                if index
                == len(track_segments) - 1
                else boundaries[index]
            )

            if lower_frame > upper_frame:
                raise ValueError(
                    "Invalid raw-frame assignment for "
                    f"{segment['segment_id']}: "
                    f"{lower_frame} > {upper_frame}"
                )

            segment["segment_source"] = (
                "sampled_reid_segment"
            )
            all_segments.append(segment)
            assignment_bounds[
                segment["segment_id"]
            ] = (
                lower_frame,
                upper_frame,
            )

    segment_ids_by_track = defaultdict(list)

    for segment in all_segments:
        segment_ids_by_track[
            int(segment["track_id"])
        ].append(segment["segment_id"])

    row_segment_ids = []
    segment_row_counts = Counter()

    for row in raw_rows:
        track_id = int(row["track_id"])
        frame_index = int(row["frame_index"])

        matching_segment_ids = [
            segment_id
            for segment_id in (
                segment_ids_by_track[track_id]
            )
            if (
                assignment_bounds[segment_id][0]
                <= frame_index
                <= assignment_bounds[segment_id][1]
            )
        ]

        if len(matching_segment_ids) != 1:
            raise ValueError(
                "Each raw row must map to exactly "
                "one segment: "
                f"T{track_id} frame {frame_index} -> "
                f"{matching_segment_ids}"
            )

        segment_id = matching_segment_ids[0]
        row_segment_ids.append(segment_id)
        segment_row_counts[segment_id] += 1

    return (
        all_segments,
        assignment_bounds,
        row_segment_ids,
        segment_row_counts,
    )


def reconcile_segments(
    all_segments,
    match_report,
):
    segment_by_id = {
        segment["segment_id"]: segment
        for segment in all_segments
    }

    disjoint_set = DisjointSet(
        segment_by_id
    )

    accepted_candidates = match_report.get(
        "accepted_candidates",
        [],
    )

    for candidate in accepted_candidates:
        source_id = candidate[
            "source_segment_id"
        ]
        target_id = candidate[
            "target_segment_id"
        ]

        if source_id not in segment_by_id:
            raise ValueError(
                f"Unknown accepted segment: {source_id}"
            )

        if target_id not in segment_by_id:
            raise ValueError(
                f"Unknown accepted segment: {target_id}"
            )

        disjoint_set.union(
            source_id,
            target_id,
        )

    for candidate in match_report.get(
        "manually_rejected_candidates",
        [],
    ):
        source_id = candidate[
            "source_segment_id"
        ]
        target_id = candidate[
            "target_segment_id"
        ]

        if (
            disjoint_set.find(source_id)
            == disjoint_set.find(target_id)
        ):
            raise ValueError(
                "A manually rejected pair was "
                "reconnected transitively: "
                f"{source_id} -> {target_id}"
            )

    components = defaultdict(list)

    for segment_id in segment_by_id:
        components[
            disjoint_set.find(segment_id)
        ].append(segment_id)

    return (
        segment_by_id,
        list(components.values()),
    )


def resolve_component_team(
    segment_ids,
    segment_by_id,
):
    known_teams = {
        segment_by_id[segment_id][
            "team_label"
        ]
        for segment_id in segment_ids
        if segment_by_id[segment_id][
            "team_label"
        ]
        in {"white", "dark"}
    }

    if len(known_teams) > 1:
        raise ValueError(
            "Accepted matches joined opposing "
            "teams: "
            f"{sorted(segment_ids)} -> "
            f"{sorted(known_teams)}"
        )

    if known_teams:
        return next(iter(known_teams))

    return "unknown"


def assign_player_ids(
    components,
    segment_by_id,
    assignment_bounds,
    segment_row_counts,
):
    component_records = []

    for segment_ids in components:
        sorted_segment_ids = sorted(
            segment_ids
        )
        team_label = resolve_component_team(
            sorted_segment_ids,
            segment_by_id,
        )

        raw_track_ids = sorted(
            {
                int(
                    segment_by_id[segment_id][
                        "track_id"
                    ]
                )
                for segment_id
                in sorted_segment_ids
            }
        )

        first_frame = min(
            assignment_bounds[segment_id][0]
            for segment_id in sorted_segment_ids
        )
        last_frame = max(
            assignment_bounds[segment_id][1]
            for segment_id in sorted_segment_ids
        )
        row_count = sum(
            segment_row_counts[segment_id]
            for segment_id in sorted_segment_ids
        )

        component_records.append(
            {
                "team_label": team_label,
                "segment_ids": sorted_segment_ids,
                "raw_track_ids": raw_track_ids,
                "first_frame": first_frame,
                "last_frame": last_frame,
                "row_count": row_count,
            }
        )

    component_records.sort(
        key=lambda component: (
            TEAM_ORDER[component["team_label"]],
            component["first_frame"],
            component["raw_track_ids"],
            component["segment_ids"],
        )
    )

    team_counters = Counter()
    player_id_by_segment = {}

    for component in component_records:
        team_label = component["team_label"]
        team_counters[team_label] += 1

        player_id = (
            f"{team_label}_p"
            f"{team_counters[team_label]}"
        )

        component["player_id"] = player_id

        for segment_id in component[
            "segment_ids"
        ]:
            player_id_by_segment[
                segment_id
            ] = player_id

    return (
        component_records,
        player_id_by_segment,
    )


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


def row_box_area(row):
    width = max(
        0.0,
        float(row["x2"])
        - float(row["x1"]),
    )
    height = max(
        0.0,
        float(row["y2"])
        - float(row["y1"]),
    )

    return width * height


def build_reconciled_rows(annotated_rows):
    rows_by_player_frame = defaultdict(list)

    for row in annotated_rows:
        key = (
            int(row["frame_index"]),
            row["player_id"],
        )
        rows_by_player_frame[key].append(row)

    reconciled_rows = []

    for (
        frame_index,
        player_id,
    ), group_rows in sorted(
        rows_by_player_frame.items(),
        key=lambda item: (
            item[0][0],
            item[0][1],
        ),
    ):
        selected_row = max(
            group_rows,
            key=lambda row: (
                float(row["confidence"]),
                row_box_area(row),
                -int(row["track_id"]),
            ),
        )

        reconciled_row = dict(selected_row)
        reconciled_row[
            "duplicate_detection_count"
        ] = len(group_rows)
        reconciled_row[
            "source_track_ids"
        ] = ";".join(
            str(track_id)
            for track_id in sorted(
                {
                    int(row["track_id"])
                    for row in group_rows
                }
            )
        )
        reconciled_row[
            "source_segment_ids"
        ] = ";".join(
            sorted(
                {
                    row["segment_id"]
                    for row in group_rows
                }
            )
        )

        reconciled_rows.append(
            reconciled_row
        )

    return reconciled_rows


def main():
    required_paths = [
        CLASSIFIED_TRACKS_PATH,
        SEGMENTS_REPORT_PATH,
        MATCH_REPORT_PATH,
    ]

    for path in required_paths:
        if not path.exists():
            raise FileNotFoundError(
                f"Required input not found: {path}"
            )

    input_fieldnames, raw_rows = (
        load_csv_rows(
            CLASSIFIED_TRACKS_PATH
        )
    )
    segment_report = load_json(
        SEGMENTS_REPORT_PATH
    )
    match_report = load_json(
        MATCH_REPORT_PATH
    )

    if match_report.get(
        "unresolved_review_candidate_count",
        0,
    ) != 0:
        raise ValueError(
            "Cannot build identities while match "
            "candidates remain unresolved."
        )

    if segment_report.get(
        "unresolved_appearance_candidate_count",
        0,
    ) != 0:
        raise ValueError(
            "Cannot build identities while "
            "appearance boundaries remain unresolved."
        )

    (
        all_segments,
        assignment_bounds,
        row_segment_ids,
        segment_row_counts,
    ) = build_segment_assignments(
        raw_rows,
        segment_report["segments"],
    )

    (
        segment_by_id,
        components,
    ) = reconcile_segments(
        all_segments,
        match_report,
    )

    (
        identities,
        player_id_by_segment,
    ) = assign_player_ids(
        components,
        segment_by_id,
        assignment_bounds,
        segment_row_counts,
    )

    team_by_player_id = {
        identity["player_id"]: (
            identity["team_label"]
        )
        for identity in identities
    }

    annotated_rows = []

    for row, segment_id in zip(
        raw_rows,
        row_segment_ids,
    ):
        player_id = (
            player_id_by_segment[segment_id]
        )

        annotated_row = dict(row)
        annotated_row["segment_id"] = (
            segment_id
        )
        annotated_row["player_id"] = player_id
        annotated_row["reconciled_team"] = (
            team_by_player_id[player_id]
        )

        annotated_rows.append(annotated_row)

    reconciled_rows = build_reconciled_rows(
        annotated_rows
    )

    annotated_fieldnames = (
        input_fieldnames
        + [
            "segment_id",
            "player_id",
            "reconciled_team",
        ]
    )
    reconciled_fieldnames = (
        annotated_fieldnames
        + [
            "duplicate_detection_count",
            "source_track_ids",
            "source_segment_ids",
        ]
    )

    write_csv(
        ANNOTATED_OUTPUT_PATH,
        annotated_fieldnames,
        annotated_rows,
    )
    write_csv(
        RECONCILED_OUTPUT_PATH,
        reconciled_fieldnames,
        reconciled_rows,
    )

    identity_counts_by_team = Counter(
        identity["team_label"]
        for identity in identities
    )
    identities_per_frame = Counter()

    for row in reconciled_rows:
        identities_per_frame[
            int(row["frame_index"])
        ] += 1

    frame_identity_count_distribution = dict(
        sorted(
            Counter(
                identities_per_frame.values()
            ).items()
        )
    )

    fallback_segments = [
        segment
        for segment in all_segments
        if segment["segment_source"]
        == "fallback_no_reid_samples"
    ]

    mapping_records = []

    for segment in sorted(
        all_segments,
        key=lambda item: (
            int(item["track_id"]),
            assignment_bounds[
                item["segment_id"]
            ][0],
            item["segment_id"],
        ),
    ):
        segment_id = segment["segment_id"]

        mapping_records.append(
            {
                "segment_id": segment_id,
                "track_id": int(
                    segment["track_id"]
                ),
                "segment_source": segment[
                    "segment_source"
                ],
                "segment_team": segment[
                    "team_label"
                ],
                "raw_start_frame": (
                    assignment_bounds[
                        segment_id
                    ][0]
                ),
                "raw_end_frame": (
                    assignment_bounds[
                        segment_id
                    ][1]
                ),
                "row_count": (
                    segment_row_counts[
                        segment_id
                    ]
                ),
                "player_id": (
                    player_id_by_segment[
                        segment_id
                    ]
                ),
                "reconciled_team": (
                    team_by_player_id[
                        player_id_by_segment[
                            segment_id
                        ]
                    ]
                ),
            }
        )

    mapping_report = {
        "classified_tracks": str(
            CLASSIFIED_TRACKS_PATH
        ),
        "segments_report": str(
            SEGMENTS_REPORT_PATH
        ),
        "match_report": str(
            MATCH_REPORT_PATH
        ),
        "summary": {
            "raw_row_count": len(raw_rows),
            "sampled_segment_count": len(
                segment_report["segments"]
            ),
            "fallback_segment_count": len(
                fallback_segments
            ),
            "total_segment_count": len(
                all_segments
            ),
            "accepted_match_count": len(
                match_report.get(
                    "accepted_candidates",
                    [],
                )
            ),
            "identity_cluster_count": len(
                identities
            ),
            "identity_counts_by_team": dict(
                identity_counts_by_team
            ),
            "identity_annotated_row_count": len(
                annotated_rows
            ),
            "reconciled_row_count": len(
                reconciled_rows
            ),
            "duplicate_rows_removed": (
                len(annotated_rows)
                - len(reconciled_rows)
            ),
            "frame_identity_count_distribution": (
                frame_identity_count_distribution
            ),
        },
        "identities": identities,
        "segment_mapping": mapping_records,
    }

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with MAPPING_OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            mapping_report,
            output_file,
            indent=2,
        )

        output_file.write("\n")

    print("\nPlayer identity construction complete.")
    print(
        f"Sampled segments: "
        f"{len(segment_report['segments'])}"
    )
    print(
        f"Fallback segments: "
        f"{len(fallback_segments)}"
    )
    print(
        f"Accepted matches applied: "
        f"{len(match_report.get('accepted_candidates', []))}"
    )
    print(
        f"Identity clusters: "
        f"{len(identities)}"
    )
    print(
        "Identity clusters by team: "
        f"{dict(identity_counts_by_team)}"
    )
    print(
        f"Original rows: {len(annotated_rows)}"
    )
    print(
        f"Reconciled rows: {len(reconciled_rows)}"
    )
    print(
        "Duplicate rows removed: "
        f"{len(annotated_rows) - len(reconciled_rows)}"
    )
    print(
        "Frame identity-count distribution: "
        f"{frame_identity_count_distribution}"
    )
    print(
        f"\nMapping saved to: "
        f"{MAPPING_OUTPUT_PATH}"
    )
    print(
        f"Annotated tracks saved to: "
        f"{ANNOTATED_OUTPUT_PATH}"
    )
    print(
        f"Reconciled tracks saved to: "
        f"{RECONCILED_OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
