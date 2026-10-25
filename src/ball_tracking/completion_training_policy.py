"""Deterministic sampling and checkpoint selection for the approved campaign.

This module reads no labels, pixels or weights and performs no model work. The
package builder owns acceptance and role checks. The runner freezes its package,
this policy and the remaining recipe before fitting.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import copy
import math
import random


NFHS_COHORTS = ("possession_001", "possession_002", "possession_003")
COHORTS = (*NFHS_COHORTS, "nba_validation")


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    return value


class _Queue:
    """Consume an entire shuffled cycle before reshuffling; never reset per epoch."""

    def __init__(self, values, rng):
        self.values = sorted(values)
        self.rng = rng
        self.pending = []
        self.position = 0
        self.cycles = 0
        self.draws = 0

    def pop(self):
        if self.position == len(self.pending):
            self.pending = self.values.copy()
            self.rng.shuffle(self.pending)
            self.position = 0
            self.cycles += 1
        result = self.pending[self.position]
        self.position += 1
        self.draws += 1
        return result

    def state(self):
        return {"population": len(self.values), "cycles_started": self.cycles,
                "draws": self.draws, "remaining_in_cycle": len(self.pending) - self.position}


def _triplet_records(triplets):
    records, block_metadata = {}, {}
    for item in triplets:
        if not isinstance(item, dict):
            raise ValueError("Each triplet must be a mapping")
        row = copy.deepcopy(item)
        for key in ("triplet_id", "block_id", "domain", "game_id"):
            _text(row.get(key), key)
        if row["triplet_id"] in records:
            raise ValueError("Triplet IDs must be distinct")
        if row["domain"] not in {"nfhs", "nba"}:
            raise ValueError("Only nfhs and nba training domains may be sampled")
        frames, mask = row.get("frame_indices"), row.get("valid_output_channels")
        if (not isinstance(frames, (list, tuple)) or len(frames) != 3
                or any(type(f) is not int or f < 0 for f in frames)
                or list(frames) != list(range(frames[0], frames[0] + 3))):
            raise ValueError("Each triplet needs three consecutive chronological native frames")
        if (not isinstance(mask, (list, tuple)) or len(mask) != 3
                or any(type(v) not in (bool, int) or v not in (0, 1) for v in mask)
                or not any(mask)):
            raise ValueError("Each usable triplet needs three binary channel flags and supervision")
        row["frame_indices"] = list(frames)
        row["valid_output_channels"] = [bool(v) for v in mask]
        row["source_id"] = _text(row.get("source_id", row["block_id"]), "source_id")
        metadata = (row["domain"], row["game_id"], row["source_id"])
        if block_metadata.setdefault(row["block_id"], metadata) != metadata:
            raise ValueError("A block ID cannot cross domain, game or source identity")
        records[row["triplet_id"]] = row
    if not records or not any(r["domain"] == "nfhs" for r in records.values()):
        raise ValueError("The schedule requires usable NFHS replay triplets")
    games = {r["game_id"] for r in records.values() if r["domain"] == "nba"}
    if len(games) != 3:
        raise ValueError("The campaign requires exactly three NBA training games")
    return dict(sorted(records.items()))


def _frame_keys(row, supervised=False):
    return {(row["domain"], row["game_id"], row["source_id"], frame)
            for frame, valid in zip(row["frame_indices"], row["valid_output_channels"])
            if valid or not supervised}


def _exposure(counts, records, all_context, all_supervised):
    domain, games, blocks = Counter(), Counter(), Counter()
    context, supervised = set(), set()
    valid_draws = 0
    for triplet_id, count in counts.items():
        row = records[triplet_id]
        domain[row["domain"]] += count
        if row["domain"] == "nba":
            games[row["game_id"]] += count
        blocks[row["block_id"]] += count
        context.update(_frame_keys(row))
        supervised.update(_frame_keys(row, True))
        valid_draws += count * sum(row["valid_output_channels"])
    draws = sum(counts.values())
    return {"draws": draws, "distinct_triplets": len(counts),
            "repeated_draws": draws - len(counts),
            "triplet_counts": {key: counts.get(key, 0) for key in records},
            "domain_draws": {key: domain[key] for key in ("nfhs", "nba")},
            "domain_fractions": {key: domain[key] / draws for key in ("nfhs", "nba")},
            "nba_game_draws": {key: games[key] for key in sorted({r["game_id"] for r in records.values() if r["domain"] == "nba"})},
            "block_draws": {key: blocks[key] for key in sorted({r["block_id"] for r in records.values()})},
            "distinct_context_frames": len(context),
            "distinct_supervised_frames": len(supervised),
            "valid_output_channel_draws": valid_draws,
            "context_frame_coverage_fraction": len(context) / len(all_context),
            "supervised_frame_coverage_fraction": len(supervised) / len(all_supervised)}


def make_schedule(triplets, max_epochs=20, seed=1234):
    """Materialize the fixed schedule without touching training data.

    Cumulative NFHS quota after ``d`` draws is floor((d + 2) / 4), i.e.
    half-up rounding of d/4. Its difference from the preceding quota chooses
    each domain. NBA games, their blocks and each block's triplets use persistent
    shuffled queues; NFHS uses one pooled triplet queue. All queues share a
    local seeded RNG and canonically sorted inputs. Each epoch has exactly N
    draws, including an actual final singleton batch when N is odd.

    Frame coverage uses (domain, game_id, source_id, native_frame_index), with
    source_id defaulting to block_id. A builder supplying a source hash as
    source_id obtains exact source-wide deduplication across its blocks.
    """
    _integer(max_epochs, "max_epochs", 1)
    if max_epochs > 20:
        raise ValueError("The approved campaign permits at most 20 epochs")
    _integer(seed, "seed")
    records = _triplet_records(triplets)
    rng = random.Random(seed)
    nfhs = _Queue([k for k, r in records.items() if r["domain"] == "nfhs"], rng)
    nba_blocks = defaultdict(list)
    for key, row in records.items():
        if row["domain"] == "nba":
            nba_blocks[(row["game_id"], row["block_id"])].append(key)
    games = _Queue({game for game, _ in nba_blocks}, rng)
    episodes = {game: _Queue([block for g, block in nba_blocks if g == game], rng)
                for game in games.values}
    queues = {key: _Queue(ids, rng) for key, ids in sorted(nba_blocks.items())}
    all_context = set().union(*(_frame_keys(r) for r in records.values()))
    all_supervised = set().union(*(_frame_keys(r, True) for r in records.values()))
    cumulative, epochs = Counter(), []
    n = len(records)
    for epoch in range(1, max_epochs + 1):
        sampled = []
        for offset in range(n):
            preceding = (epoch - 1) * n + offset
            if (preceding + 3) // 4 > (preceding + 2) // 4:
                triplet_id = nfhs.pop()
            else:
                game = games.pop()
                block = episodes[game].pop()
                triplet_id = queues[(game, block)].pop()
            sampled.append(triplet_id)
        counts = Counter(sampled)
        cumulative.update(counts)
        epochs.append({"epoch": epoch, "sampled_ids": sampled,
                       "batches": [sampled[i:i + 2] for i in range(0, n, 2)],
                       "exposure": _exposure(counts, records, all_context, all_supervised),
                       "cumulative_exposure": _exposure(cumulative, records, all_context, all_supervised),
                       "queue_state": {"nfhs": nfhs.state(), "nba_games": games.state(),
                                       "nba_episodes": {g: q.state() for g, q in episodes.items()},
                                       "nba_triplets": {g: {b: queues[(g, b)].state() for b in episodes[g].values}
                                                        for g in games.values}}})
    return {"schema_version": "completion_training_schedule/v0.1", "seed": seed,
            "algorithm": "cumulative_half_up_quarter_domain_quota_and_persistent_shuffled_queues",
            "batch_size": 2, "max_epochs": max_epochs, "triplet_count": n,
            "epoch_draw_count": n, "total_draw_count": n * max_epochs,
            "target_domain_fractions": {"nfhs": .25, "nba": .75},
            "frame_identity": ["domain", "game_id", "source_id_or_block_id", "native_frame_index"],
            "total_distinct_context_frames": len(all_context),
            "total_distinct_supervised_frames": len(all_supervised), "epochs": epochs}


def _validated_reports(reports):
    result = {}
    for report in reports:
        if not isinstance(report, dict):
            raise ValueError("Each checkpoint report must be a mapping")
        epoch = _integer(report.get("epoch"), "epoch")
        if epoch in result:
            raise ValueError("Checkpoint epochs must be distinct")
        cohorts = report.get("cohorts")
        if not isinstance(cohorts, dict) or set(cohorts) != set(COHORTS):
            raise ValueError("Selection requires exactly the three NFHS and fresh NBA validation cohorts")
        for name, metrics in cohorts.items():
            if not isinstance(metrics, dict):
                raise ValueError(f"{name} metrics must be a mapping")
            for key in ("matched", "wrong", "certain_hidden_emissions"):
                _integer(metrics.get(key), f"{name}.{key}")
            gap = metrics.get("worst_missing_seconds")
            if type(gap) not in (int, float) or not math.isfinite(gap) or gap < 0:
                raise ValueError(f"{name}.worst_missing_seconds must be finite and nonnegative")
        result[epoch] = copy.deepcopy(report)
    if 0 not in result:
        raise ValueError("The retained model at epoch zero is required")
    return dict(sorted(result.items()))


def _rank(report):
    cohorts = report["cohorts"]
    return (sum(cohorts[c]["matched"] for c in NFHS_COHORTS),
            cohorts["nba_validation"]["matched"],
            -max(cohorts[c]["worst_missing_seconds"] for c in NFHS_COHORTS),
            -report["epoch"])


def choose_checkpoint(reports):
    """Select against epoch zero; larger rank tuples are better.

    Each cohort separately forbids losing a match or gaining a wrong output or
    certain-hidden emission. Missing-run duration is a ranking term, not a new
    eligibility veto. Equal-quality later epochs cannot displace the baseline.
    """
    reports = _validated_reports(reports)
    baseline = reports[0]["cohorts"]
    eligible, rejected = [], []
    for epoch, report in reports.items():
        reasons = []
        for name in COHORTS:
            metrics = report["cohorts"][name]
            if metrics["matched"] < baseline[name]["matched"]:
                reasons.append(f"{name}: matched below epoch zero")
            for key in ("wrong", "certain_hidden_emissions"):
                if metrics[key] > baseline[name][key]:
                    reasons.append(f"{name}: {key} above epoch zero")
        if reasons:
            rejected.append({"epoch": epoch, "reasons": reasons})
        else:
            eligible.append(epoch)
    selected = max(eligible, key=lambda epoch: _rank(reports[epoch]))
    return {"selected_epoch": selected, "epoch_zero_selected": selected == 0,
            "eligible_epochs": eligible, "rejected": rejected,
            "rank": list(_rank(reports[selected])),
            "selected_report": reports[selected]}


def should_stop(epoch, best_epoch, min_epochs=5, patience=5):
    """Call after epoch validation, using choose_checkpoint's selected_epoch."""
    _integer(epoch, "epoch")
    _integer(best_epoch, "best_epoch")
    _integer(min_epochs, "min_epochs", 1)
    _integer(patience, "patience", 1)
    if best_epoch > epoch:
        raise ValueError("The best epoch cannot be in the future")
    return epoch >= min_epochs and epoch - best_epoch >= patience
