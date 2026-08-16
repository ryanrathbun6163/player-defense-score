import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


CLASSIFIED_TRACKS_PATH: Path
SEGMENTS_REPORT_PATH: Path
MATCH_REPORT_PATH: Path
IDENTITY_REVIEW_CONFIG_PATH: Path
SEQUENTIAL_IDENTITY_REVIEW_CONFIG_PATH: Path
OUTPUT_DIR: Path
MAPPING_OUTPUT_PATH: Path
ANNOTATED_OUTPUT_PATH: Path
RECONCILED_OUTPUT_PATH: Path


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Build reviewed player identities from classified tracks and "
            "resolved ReID decisions."
        )
    )
    parser.add_argument("--classified-tracks", type=Path, required=True)
    parser.add_argument("--segments", type=Path, required=True)
    parser.add_argument("--matches", type=Path, required=True)
    parser.add_argument("--identity-review-config", type=Path, required=True)
    parser.add_argument(
        "--sequential-review-config", type=Path, required=True
    )
    parser.add_argument("--output-mapping", type=Path, required=True)
    parser.add_argument(
        "--output-annotated-tracks", type=Path, required=True
    )
    parser.add_argument(
        "--output-reconciled-tracks", type=Path, required=True
    )
    parser.add_argument(
        "--expected-player-count", type=int, required=True
    )
    return parser


def parse_args(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.expected_player_count < 1:
        parser.error("--expected-player-count must be positive")

    return args


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


def apply_identity_review(
    baseline_identities,
    baseline_player_id_by_segment,
    segment_by_id,
    assignment_bounds,
    segment_row_counts,
    review_config,
):
    baseline_by_id = {
        identity["player_id"]: identity
        for identity in baseline_identities
    }
    baseline_player_ids = set(baseline_by_id)
    expected_count = review_config.get(
        "expected_baseline_identity_cluster_count"
    )

    if (
        expected_count is not None
        and int(expected_count) != len(baseline_identities)
    ):
        raise ValueError(
            "Identity review config expects "
            f"{expected_count} baseline clusters, but "
            f"the builder produced {len(baseline_identities)}."
        )

    expected_player_ids = set(
        review_config.get(
            "expected_baseline_player_ids",
            baseline_player_ids,
        )
    )

    if expected_player_ids != baseline_player_ids:
        raise ValueError(
            "Identity review config does not match the "
            "current baseline player IDs. Missing from "
            "config: "
            f"{sorted(baseline_player_ids - expected_player_ids)}; "
            "unexpected in config: "
            f"{sorted(expected_player_ids - baseline_player_ids)}"
        )

    excluded_records = review_config.get(
        "excluded_identities",
        [],
    )
    excluded_reason_by_player_id = {}

    for record in excluded_records:
        player_id = record["player_id"]

        if player_id not in baseline_by_id:
            raise ValueError(
                f"Unknown excluded baseline identity: {player_id}"
            )

        if player_id in excluded_reason_by_player_id:
            raise ValueError(
                f"Duplicate excluded identity: {player_id}"
            )

        excluded_reason_by_player_id[player_id] = record[
            "reason"
        ]

    accepted_merges = review_config.get(
        "accepted_identity_merges",
        [],
    )
    rejected_merges = review_config.get(
        "rejected_identity_merges",
        [],
    )
    disjoint_set = DisjointSet(baseline_player_ids)

    for record in accepted_merges:
        first_player_id = record["first_player_id"]
        second_player_id = record["second_player_id"]

        for player_id in (
            first_player_id,
            second_player_id,
        ):
            if player_id not in baseline_by_id:
                raise ValueError(
                    "Unknown reviewed merge identity: "
                    f"{player_id}"
                )

            if player_id in excluded_reason_by_player_id:
                raise ValueError(
                    "An excluded identity cannot also be "
                    f"merged: {player_id}"
                )

        disjoint_set.union(
            first_player_id,
            second_player_id,
        )

    for record in rejected_merges:
        first_player_id = record["first_player_id"]
        second_player_id = record["second_player_id"]

        for player_id in (
            first_player_id,
            second_player_id,
        ):
            if player_id not in baseline_by_id:
                raise ValueError(
                    "Unknown rejected merge identity: "
                    f"{player_id}"
                )

        if (
            disjoint_set.find(first_player_id)
            == disjoint_set.find(second_player_id)
        ):
            raise ValueError(
                "A rejected identity pair was reconnected "
                "transitively: "
                f"{first_player_id} -> {second_player_id}"
            )

    team_overrides = review_config.get(
        "team_overrides",
        {},
    )

    for player_id, team_label in team_overrides.items():
        if player_id not in baseline_by_id:
            raise ValueError(
                f"Unknown team-override identity: {player_id}"
            )

        if team_label not in TEAM_ORDER:
            raise ValueError(
                "Invalid reviewed team label for "
                f"{player_id}: {team_label}"
            )

    active_groups = defaultdict(list)

    for player_id in baseline_player_ids:
        if player_id in excluded_reason_by_player_id:
            continue

        active_groups[
            disjoint_set.find(player_id)
        ].append(player_id)

    reviewed_components = []

    for source_player_ids in active_groups.values():
        source_player_ids = sorted(source_player_ids)
        segment_ids = sorted(
            {
                segment_id
                for player_id in source_player_ids
                for segment_id in baseline_by_id[player_id][
                    "segment_ids"
                ]
            }
        )
        reviewed_teams = {
            team_overrides.get(
                player_id,
                baseline_by_id[player_id]["team_label"],
            )
            for player_id in source_player_ids
            if team_overrides.get(
                player_id,
                baseline_by_id[player_id]["team_label"],
            )
            in {"white", "dark"}
        }

        if len(reviewed_teams) > 1:
            raise ValueError(
                "Reviewed identity merges joined opposing "
                "teams without a resolving override: "
                f"{source_player_ids} -> "
                f"{sorted(reviewed_teams)}"
            )

        team_label = (
            next(iter(reviewed_teams))
            if reviewed_teams
            else "unknown"
        )
        raw_track_ids = sorted(
            {
                int(segment_by_id[segment_id]["track_id"])
                for segment_id in segment_ids
            }
        )
        first_frame = min(
            assignment_bounds[segment_id][0]
            for segment_id in segment_ids
        )
        last_frame = max(
            assignment_bounds[segment_id][1]
            for segment_id in segment_ids
        )
        row_count = sum(
            segment_row_counts[segment_id]
            for segment_id in segment_ids
        )

        reviewed_components.append(
            {
                "team_label": team_label,
                "source_player_ids": source_player_ids,
                "segment_ids": segment_ids,
                "raw_track_ids": raw_track_ids,
                "first_frame": first_frame,
                "last_frame": last_frame,
                "row_count": row_count,
            }
        )

    reviewed_components.sort(
        key=lambda component: (
            TEAM_ORDER[component["team_label"]],
            component["first_frame"],
            component["raw_track_ids"],
            component["segment_ids"],
        )
    )
    team_counters = Counter()
    player_id_by_segment = {}

    for component in reviewed_components:
        team_label = component["team_label"]
        team_counters[team_label] += 1
        player_id = (
            f"{team_label}_p"
            f"{team_counters[team_label]}"
        )
        component["player_id"] = player_id

        for segment_id in component["segment_ids"]:
            player_id_by_segment[segment_id] = player_id

    excluded_identities = []
    excluded_reason_by_segment = {}

    for player_id in sorted(excluded_reason_by_player_id):
        baseline_identity = baseline_by_id[player_id]
        reason = excluded_reason_by_player_id[player_id]
        excluded_identity = dict(baseline_identity)
        excluded_identity["baseline_player_id"] = player_id
        excluded_identity["exclusion_reason"] = reason
        excluded_identities.append(excluded_identity)

        for segment_id in baseline_identity["segment_ids"]:
            excluded_reason_by_segment[segment_id] = reason

    return (
        reviewed_components,
        player_id_by_segment,
        excluded_identities,
        excluded_reason_by_segment,
        {
            "accepted_identity_merge_count": len(
                accepted_merges
            ),
            "rejected_identity_merge_count": len(
                rejected_merges
            ),
            "excluded_identity_count": len(
                excluded_identities
            ),
            "team_override_count": len(team_overrides),
        },
    )


def apply_sequential_identity_review(
    identities,
    player_id_by_segment,
    segment_by_id,
    assignment_bounds,
    segment_row_counts,
    raw_rows,
    row_segment_ids,
    review_config,
):
    identity_by_id = {
        identity["player_id"]: identity
        for identity in identities
    }
    player_ids = set(identity_by_id)
    expected_count = review_config.get(
        "expected_presequential_identity_cluster_count"
    )

    if (
        expected_count is not None
        and int(expected_count) != len(identities)
    ):
        raise ValueError(
            "Sequential review config expects "
            f"{expected_count} pre-sequential clusters, but "
            f"the builder produced {len(identities)}."
        )

    expected_player_ids = set(
        review_config.get(
            "expected_presequential_player_ids",
            player_ids,
        )
    )

    if expected_player_ids != player_ids:
        raise ValueError(
            "Sequential review config does not match the "
            "current pre-sequential player IDs. Missing from "
            "config: "
            f"{sorted(player_ids - expected_player_ids)}; "
            "unexpected in config: "
            f"{sorted(expected_player_ids - player_ids)}"
        )

    frames_by_player_id = defaultdict(set)

    for row, segment_id in zip(raw_rows, row_segment_ids):
        player_id = player_id_by_segment.get(segment_id)

        if player_id is not None:
            frames_by_player_id[player_id].add(
                int(row["frame_index"])
            )

    accepted_merges = review_config.get(
        "accepted_identity_merges",
        [],
    )
    rejected_merges = review_config.get(
        "rejected_identity_merges",
        [],
    )
    accepted_pairs = set()
    rejected_pairs = set()

    def validate_pair(record, decision):
        first_player_id = record["first_player_id"]
        second_player_id = record["second_player_id"]

        for player_id in (first_player_id, second_player_id):
            if player_id not in identity_by_id:
                raise ValueError(
                    f"Unknown {decision} sequential identity: "
                    f"{player_id}"
                )

        if first_player_id == second_player_id:
            raise ValueError(
                "A sequential review pair cannot contain the "
                f"same identity twice: {first_player_id}"
            )

        return tuple(sorted((first_player_id, second_player_id)))

    for record in accepted_merges:
        pair = validate_pair(record, "accepted")

        if pair in accepted_pairs:
            raise ValueError(
                f"Duplicate accepted sequential pair: {pair}"
            )

        accepted_pairs.add(pair)

    for record in rejected_merges:
        pair = validate_pair(record, "rejected")

        if pair in rejected_pairs:
            raise ValueError(
                f"Duplicate rejected sequential pair: {pair}"
            )

        if pair in accepted_pairs:
            raise ValueError(
                "A sequential pair cannot be both accepted and "
                f"rejected: {pair}"
            )

        rejected_pairs.add(pair)

    disjoint_set = DisjointSet(player_ids)

    for first_player_id, second_player_id in accepted_pairs:
        if (
            frames_by_player_id[first_player_id]
            & frames_by_player_id[second_player_id]
        ):
            raise ValueError(
                "Sequential merge identities co-occur in at "
                "least one frame: "
                f"{first_player_id} -> {second_player_id}"
            )

        disjoint_set.union(first_player_id, second_player_id)

    groups = defaultdict(list)

    for player_id in player_ids:
        groups[disjoint_set.find(player_id)].append(player_id)

    for group_player_ids in groups.values():
        for first_player_id in group_player_ids:
            for second_player_id in group_player_ids:
                if first_player_id >= second_player_id:
                    continue

                pair = (first_player_id, second_player_id)

                if pair in rejected_pairs:
                    raise ValueError(
                        "A rejected sequential pair was "
                        "reconnected transitively: "
                        f"{first_player_id} -> {second_player_id}"
                    )

                if (
                    frames_by_player_id[first_player_id]
                    & frames_by_player_id[second_player_id]
                ):
                    raise ValueError(
                        "Sequential merges transitively joined "
                        "identities that co-occur: "
                        f"{first_player_id} -> {second_player_id}"
                    )

    sequential_components = []

    for presequential_player_ids in groups.values():
        presequential_player_ids = sorted(
            presequential_player_ids
        )
        source_player_ids = sorted(
            {
                source_player_id
                for player_id in presequential_player_ids
                for source_player_id in identity_by_id[player_id][
                    "source_player_ids"
                ]
            }
        )
        segment_ids = sorted(
            {
                segment_id
                for player_id in presequential_player_ids
                for segment_id in identity_by_id[player_id][
                    "segment_ids"
                ]
            }
        )
        known_teams = {
            identity_by_id[player_id]["team_label"]
            for player_id in presequential_player_ids
            if identity_by_id[player_id]["team_label"]
            in {"white", "dark"}
        }

        if len(known_teams) > 1:
            raise ValueError(
                "Sequential identity merges joined opposing "
                f"teams: {presequential_player_ids} -> "
                f"{sorted(known_teams)}"
            )

        team_label = (
            next(iter(known_teams))
            if known_teams
            else "unknown"
        )
        raw_track_ids = sorted(
            {
                int(segment_by_id[segment_id]["track_id"])
                for segment_id in segment_ids
            }
        )
        sequential_components.append(
            {
                "team_label": team_label,
                "source_player_ids": source_player_ids,
                "presequential_player_ids": (
                    presequential_player_ids
                ),
                "segment_ids": segment_ids,
                "raw_track_ids": raw_track_ids,
                "first_frame": min(
                    assignment_bounds[segment_id][0]
                    for segment_id in segment_ids
                ),
                "last_frame": max(
                    assignment_bounds[segment_id][1]
                    for segment_id in segment_ids
                ),
                "row_count": sum(
                    segment_row_counts[segment_id]
                    for segment_id in segment_ids
                ),
            }
        )

    sequential_components.sort(
        key=lambda component: (
            TEAM_ORDER[component["team_label"]],
            component["first_frame"],
            component["raw_track_ids"],
            component["segment_ids"],
        )
    )
    team_counters = Counter()
    final_player_id_by_segment = {}

    for component in sequential_components:
        team_label = component["team_label"]
        team_counters[team_label] += 1
        component["player_id"] = (
            f"{team_label}_p{team_counters[team_label]}"
        )

        for segment_id in component["segment_ids"]:
            final_player_id_by_segment[segment_id] = component[
                "player_id"
            ]

    return (
        sequential_components,
        final_player_id_by_segment,
        {
            "accepted_sequential_identity_merge_count": len(
                accepted_merges
            ),
            "rejected_sequential_identity_merge_count": len(
                rejected_merges
            ),
        },
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
        if row["identity_status"] != "active":
            continue

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


def run(args):
    global CLASSIFIED_TRACKS_PATH
    global SEGMENTS_REPORT_PATH
    global MATCH_REPORT_PATH
    global IDENTITY_REVIEW_CONFIG_PATH
    global SEQUENTIAL_IDENTITY_REVIEW_CONFIG_PATH
    global OUTPUT_DIR
    global MAPPING_OUTPUT_PATH
    global ANNOTATED_OUTPUT_PATH
    global RECONCILED_OUTPUT_PATH

    CLASSIFIED_TRACKS_PATH = args.classified_tracks
    SEGMENTS_REPORT_PATH = args.segments
    MATCH_REPORT_PATH = args.matches
    IDENTITY_REVIEW_CONFIG_PATH = args.identity_review_config
    SEQUENTIAL_IDENTITY_REVIEW_CONFIG_PATH = (
        args.sequential_review_config
    )
    MAPPING_OUTPUT_PATH = args.output_mapping
    ANNOTATED_OUTPUT_PATH = args.output_annotated_tracks
    RECONCILED_OUTPUT_PATH = args.output_reconciled_tracks
    OUTPUT_DIR = MAPPING_OUTPUT_PATH.parent
    required_paths = [
        CLASSIFIED_TRACKS_PATH,
        SEGMENTS_REPORT_PATH,
        MATCH_REPORT_PATH,
        IDENTITY_REVIEW_CONFIG_PATH,
        SEQUENTIAL_IDENTITY_REVIEW_CONFIG_PATH,
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
    identity_review_config = load_json(
        IDENTITY_REVIEW_CONFIG_PATH
    )
    sequential_identity_review_config = load_json(
        SEQUENTIAL_IDENTITY_REVIEW_CONFIG_PATH
    )

    configured_player_count = int(
        identity_review_config.get(
            "expected_active_player_count",
            args.expected_player_count,
        )
    )

    if configured_player_count != args.expected_player_count:
        raise ValueError(
            "Identity review config expected_active_player_count "
            f"({configured_player_count}) does not match the pipeline "
            f"manifest ({args.expected_player_count})."
        )

    identity_review_config.setdefault(
        "expected_active_player_count",
        args.expected_player_count,
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
        baseline_identities,
        baseline_player_id_by_segment,
    ) = assign_player_ids(
        components,
        segment_by_id,
        assignment_bounds,
        segment_row_counts,
    )

    (
        reviewed_identities,
        reviewed_player_id_by_segment,
        excluded_identities,
        excluded_reason_by_segment,
        identity_review_summary,
    ) = apply_identity_review(
        baseline_identities,
        baseline_player_id_by_segment,
        segment_by_id,
        assignment_bounds,
        segment_row_counts,
        identity_review_config,
    )

    (
        identities,
        player_id_by_segment,
        sequential_identity_review_summary,
    ) = apply_sequential_identity_review(
        reviewed_identities,
        reviewed_player_id_by_segment,
        segment_by_id,
        assignment_bounds,
        segment_row_counts,
        raw_rows,
        row_segment_ids,
        sequential_identity_review_config,
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
        baseline_player_id = (
            baseline_player_id_by_segment[
                segment_id
            ]
        )
        annotated_row = dict(row)
        annotated_row["segment_id"] = segment_id
        annotated_row[
            "baseline_player_id"
        ] = baseline_player_id

        if segment_id in excluded_reason_by_segment:
            annotated_row["player_id"] = ""
            annotated_row["reconciled_team"] = "excluded"
            annotated_row[
                "identity_status"
            ] = "excluded_non_player"
            annotated_row[
                "identity_review_reason"
            ] = excluded_reason_by_segment[segment_id]
        else:
            player_id = player_id_by_segment[segment_id]
            annotated_row["player_id"] = player_id
            annotated_row["reconciled_team"] = (
                team_by_player_id[player_id]
            )
            annotated_row[
                "identity_status"
            ] = "active"
            annotated_row[
                "identity_review_reason"
            ] = ""

        annotated_rows.append(annotated_row)

    reconciled_rows = build_reconciled_rows(
        annotated_rows
    )

    annotated_fieldnames = (
        input_fieldnames
        + [
            "segment_id",
            "baseline_player_id",
            "player_id",
            "reconciled_team",
            "identity_status",
            "identity_review_reason",
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
    excluded_annotated_row_count = sum(
        row["identity_status"] != "active"
        for row in annotated_rows
    )
    active_annotated_row_count = (
        len(annotated_rows)
        - excluded_annotated_row_count
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
    expected_active_player_count = int(
        identity_review_config.get(
            "expected_active_player_count",
            10,
        )
    )
    frames_above_expected_count = sum(
        count > expected_active_player_count
        for count in identities_per_frame.values()
    )
    frames_at_expected_count = sum(
        count == expected_active_player_count
        for count in identities_per_frame.values()
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
        baseline_player_id = (
            baseline_player_id_by_segment[
                segment_id
            ]
        )
        is_excluded = (
            segment_id
            in excluded_reason_by_segment
        )
        player_id = (
            None
            if is_excluded
            else player_id_by_segment[segment_id]
        )

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
                "baseline_player_id": (
                    baseline_player_id
                ),
                "player_id": player_id,
                "reconciled_team": (
                    None
                    if is_excluded
                    else team_by_player_id[player_id]
                ),
                "identity_status": (
                    "excluded_non_player"
                    if is_excluded
                    else "active"
                ),
                "identity_review_reason": (
                    excluded_reason_by_segment.get(
                        segment_id
                    )
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
        "identity_review_config": str(
            IDENTITY_REVIEW_CONFIG_PATH
        ),
        "sequential_identity_review_config": str(
            SEQUENTIAL_IDENTITY_REVIEW_CONFIG_PATH
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
            "baseline_identity_cluster_count": len(
                baseline_identities
            ),
            "residual_reviewed_identity_cluster_count": len(
                reviewed_identities
            ),
            "identity_cluster_count": len(
                identities
            ),
            "active_identity_cluster_count": len(
                identities
            ),
            "excluded_identity_cluster_count": len(
                excluded_identities
            ),
            **identity_review_summary,
            **sequential_identity_review_summary,
            "identity_counts_by_team": dict(
                identity_counts_by_team
            ),
            "identity_annotated_row_count": len(
                annotated_rows
            ),
            "active_annotated_row_count": (
                active_annotated_row_count
            ),
            "excluded_annotated_row_count": (
                excluded_annotated_row_count
            ),
            "reconciled_row_count": len(
                reconciled_rows
            ),
            "duplicate_rows_removed": (
                active_annotated_row_count
                - len(reconciled_rows)
            ),
            "frame_identity_count_distribution": (
                frame_identity_count_distribution
            ),
            "expected_active_player_count": (
                expected_active_player_count
            ),
            "frames_at_expected_count": (
                frames_at_expected_count
            ),
            "frames_above_expected_count": (
                frames_above_expected_count
            ),
        },
        "baseline_identities": baseline_identities,
        "residual_reviewed_identities": reviewed_identities,
        "identities": identities,
        "excluded_identities": excluded_identities,
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
        f"Baseline identity clusters: "
        f"{len(baseline_identities)}"
    )
    print(
        f"Residual-reviewed active identity clusters: "
        f"{len(reviewed_identities)}"
    )
    print(
        "Sequential identity merges applied: "
        f"{sequential_identity_review_summary['accepted_sequential_identity_merge_count']}"
    )
    print(
        "Sequential identity merges rejected: "
        f"{sequential_identity_review_summary['rejected_sequential_identity_merge_count']}"
    )
    print(
        f"Final active identity clusters: "
        f"{len(identities)}"
    )
    print(
        f"Excluded non-player identity clusters: "
        f"{len(excluded_identities)}"
    )
    print(
        "Reviewed identity merges applied: "
        f"{identity_review_summary['accepted_identity_merge_count']}"
    )
    print(
        "Identity clusters by team: "
        f"{dict(identity_counts_by_team)}"
    )
    print(
        f"Original rows: {len(annotated_rows)}"
    )
    print(
        "Excluded non-player rows: "
        f"{excluded_annotated_row_count}"
    )
    print(
        f"Reconciled rows: {len(reconciled_rows)}"
    )
    print(
        "Duplicate rows removed: "
        f"{active_annotated_row_count - len(reconciled_rows)}"
    )
    print(
        "Frame identity-count distribution: "
        f"{frame_identity_count_distribution}"
    )
    print(
        f"Frames at {expected_active_player_count} active players: "
        f"{frames_at_expected_count}"
    )
    print(
        f"Frames above {expected_active_player_count} active players: "
        f"{frames_above_expected_count}"
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


def main():
    run(parse_args())


if __name__ == "__main__":
    main()
