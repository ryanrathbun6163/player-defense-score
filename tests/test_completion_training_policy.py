"""Pure policy checks: no model calls, source decoding or scientific scoring."""
from collections import Counter, defaultdict
import copy
import math
import unittest

from src.ball_tracking.completion_training_policy import (
    COHORTS, choose_checkpoint, make_schedule, should_stop,
)


def triplets():
    # Unequal game/episode sizes, including retained SAC replay and new episodes.
    specification = [("nfhs", "school", "nfhs_replay", 5),
                     ("nba", "sac", "sac_old_1", 2),
                     ("nba", "sac", "sac_old_2", 3),
                     ("nba", "sac", "sac_new", 7),
                     ("nba", "chi", "chi_short", 2),
                     ("nba", "chi", "chi_long", 6),
                     ("nba", "den", "den_episode", 4)]
    return [{"triplet_id": f"{block}/{i}", "domain": domain, "game_id": game,
             "block_id": block, "source_id": f"source-{block}",
             "frame_indices": [i, i + 1, i + 2],
             "valid_output_channels": [True, False, True]}
            for domain, game, block, count in specification for i in range(count)]


def report(epoch=0, matched=10, wrong=1, hidden=0, gap=.4):
    return {"epoch": epoch, "cohorts": {c: {"matched": matched, "wrong": wrong,
            "certain_hidden_emissions": hidden, "worst_missing_seconds": gap}
            for c in COHORTS}}


class ScheduleTests(unittest.TestCase):
    def test_deterministic_canonical_input_order_and_schedule_prefix(self):
        rows = triplets()
        before = copy.deepcopy(rows)
        short = make_schedule(rows, max_epochs=3)
        long = make_schedule(list(reversed(rows)), max_epochs=5)
        self.assertEqual(short["epochs"], long["epochs"][:3])
        self.assertEqual(rows, before)
        self.assertNotEqual(short["epochs"], make_schedule(rows, 3, seed=1235)["epochs"])

    def test_exact_draws_singleton_batch_and_prefix_domain_quota(self):
        rows = triplets()
        by_id = {r["triplet_id"]: r for r in rows}
        schedule = make_schedule(rows)
        self.assertEqual(len(rows), 29)
        nfhs, total = 0, 0
        for epoch in schedule["epochs"]:
            self.assertEqual(len(epoch["sampled_ids"]), 29)
            self.assertEqual([x for b in epoch["batches"] for x in b], epoch["sampled_ids"])
            self.assertEqual([len(b) for b in epoch["batches"]], [2] * 14 + [1])
            for item in epoch["sampled_ids"]:
                total += 1
                nfhs += by_id[item]["domain"] == "nfhs"
                self.assertEqual(nfhs, (total + 2) // 4)
            self.assertEqual(epoch["cumulative_exposure"]["domain_draws"]["nfhs"], nfhs)
        self.assertEqual(total, schedule["total_draw_count"])
        self.assertEqual(nfhs / total, .25)

    def test_games_and_episodes_balanced_despite_unequal_populations(self):
        rows = triplets()
        by_id = {r["triplet_id"]: r for r in rows}
        games = Counter({g: 0 for g in ("sac", "chi", "den")})
        blocks = {g: Counter({r["block_id"]: 0 for r in rows if r["game_id"] == g}) for g in games}
        for epoch in make_schedule(rows)["epochs"]:
            for item in epoch["sampled_ids"]:
                row = by_id[item]
                if row["domain"] == "nba":
                    game = row["game_id"]
                    games[game] += 1
                    blocks[game][row["block_id"]] += 1
                    self.assertLessEqual(max(games.values()) - min(games.values()), 1)
                    self.assertLessEqual(max(blocks[game].values()) - min(blocks[game].values()), 1)

    def test_persistent_queues_complete_cycles_across_epoch_boundaries(self):
        rows = triplets()
        by_id = {r["triplet_id"]: r for r in rows}
        expected, actual = defaultdict(set), defaultdict(list)
        for row in rows:
            queue = "nfhs_pool" if row["domain"] == "nfhs" else row["block_id"]
            expected[queue].add(row["triplet_id"])
        schedule = make_schedule(rows)
        for epoch in schedule["epochs"]:
            for item in epoch["sampled_ids"]:
                row = by_id[item]
                actual["nfhs_pool" if row["domain"] == "nfhs" else row["block_id"]].append(item)
        for queue, sequence in actual.items():
            width = len(expected[queue])
            self.assertGreater(len(sequence), width)
            for start in range(0, len(sequence), width):
                chunk = sequence[start:start + width]
                self.assertEqual(len(chunk), len(set(chunk)))
                if len(chunk) == width:
                    self.assertEqual(set(chunk), expected[queue])
        self.assertEqual(schedule["epochs"][-1]["cumulative_exposure"]["distinct_triplets"], len(rows))
        self.assertGreater(schedule["epochs"][-1]["queue_state"]["nfhs"]["cycles_started"], 1)

    def test_exposure_reports_repeats_masks_and_actual_source_frame_deduplication(self):
        rows = triplets()
        # Two blocks from one source can share context frames without double counting.
        for r in rows:
            if r["game_id"] == "sac":
                r["source_id"] = "same-sac-source"
        by_id = {r["triplet_id"]: r for r in rows}
        schedule = make_schedule(rows, max_epochs=1)
        epoch = schedule["epochs"][0]
        drawn = Counter(epoch["sampled_ids"])
        contexts, supervised = set(), set()
        for item in drawn:
            row = by_id[item]
            for f, valid in zip(row["frame_indices"], row["valid_output_channels"]):
                key = (row["domain"], row["game_id"], row["source_id"], f)
                contexts.add(key)
                if valid:
                    supervised.add(key)
        exposure = epoch["exposure"]
        self.assertEqual(exposure["repeated_draws"], len(rows) - len(drawn))
        self.assertEqual(exposure["distinct_context_frames"], len(contexts))
        self.assertEqual(exposure["distinct_supervised_frames"], len(supervised))
        self.assertEqual(exposure["valid_output_channel_draws"], 2 * len(rows))
        self.assertEqual(exposure["triplet_counts"], {key: drawn[key] for key in sorted(by_id)})

    def test_rejects_masked_non_native_duplicate_and_role_shape_errors(self):
        cases = []
        rows = triplets(); rows[0]["valid_output_channels"] = [0, 0, 0]; cases.append(rows)
        rows = triplets(); rows[0]["frame_indices"] = [0, 2, 4]; cases.append(rows)
        rows = triplets(); rows.append(copy.deepcopy(rows[0])); cases.append(rows)
        rows = triplets(); rows[0]["domain"] = "checkpoint_validation"; cases.append(rows)
        rows = triplets(); rows[0]["valid_output_channels"] = [1, .5, 1]; cases.append(rows)
        rows = [r for r in triplets() if r["game_id"] != "den"]; cases.append(rows)
        rows = triplets(); rows[-1]["block_id"] = rows[0]["block_id"]; cases.append(rows)
        for rows in cases:
            with self.subTest(rows=rows[0]), self.assertRaises(ValueError):
                make_schedule(rows)
        with self.assertRaises(ValueError):
            make_schedule(triplets(), max_epochs=21)


class SelectionTests(unittest.TestCase):
    def test_epoch_zero_wins_ties_and_rejects_all_regressions(self):
        baseline = report()
        tied = report(1)
        regressed = report(2, matched=100)
        regressed["cohorts"]["possession_002"]["matched"] = 9
        selected = choose_checkpoint([regressed, tied, baseline])
        self.assertEqual(selected["selected_epoch"], 0)
        self.assertEqual(selected["eligible_epochs"], [0, 1])
        self.assertIn("possession_002: matched below epoch zero", selected["rejected"][0]["reasons"])

    def test_each_cohort_and_each_nonregression_metric_is_enforced(self):
        for cohort in COHORTS:
            for key, value in (("matched", 9), ("wrong", 2), ("certain_hidden_emissions", 1)):
                candidate = report(1, matched=100)
                candidate["cohorts"][cohort][key] = value
                with self.subTest(cohort=cohort, metric=key):
                    self.assertEqual(choose_checkpoint([report(), candidate])["selected_epoch"], 0)

    def test_lexicographic_rank_prefers_nfhs_then_nba_then_gap_then_earlier(self):
        first = report(1)
        first["cohorts"]["possession_001"]["matched"] = 11
        nba_only = report(2)
        nba_only["cohorts"]["nba_validation"]["matched"] = 1000
        self.assertEqual(choose_checkpoint([report(), first, nba_only])["selected_epoch"], 1)
        more_nba = copy.deepcopy(first); more_nba["epoch"] = 3
        more_nba["cohorts"]["nba_validation"]["matched"] = 11
        shorter = copy.deepcopy(more_nba); shorter["epoch"] = 4
        for c in COHORTS[:3]:
            shorter["cohorts"][c]["worst_missing_seconds"] = .2
        tied = copy.deepcopy(shorter); tied["epoch"] = 5
        self.assertEqual(choose_checkpoint([report(), first, more_nba])["selected_epoch"], 3)
        self.assertEqual(choose_checkpoint([report(), first, more_nba, shorter, tied])["selected_epoch"], 4)

    def test_missing_run_can_improve_ranking_but_is_not_a_new_eligibility_gate(self):
        shorter = report(1, gap=.2)
        self.assertEqual(choose_checkpoint([report(), shorter])["selected_epoch"], 1)
        more_matches = report(2, matched=11, gap=10)
        self.assertEqual(choose_checkpoint([report(), more_matches])["selected_epoch"], 2)
        nba_gap_only = report(3)
        nba_gap_only["cohorts"]["nba_validation"]["worst_missing_seconds"] = 0
        self.assertEqual(choose_checkpoint([report(), nba_gap_only])["selected_epoch"], 0)

    def test_report_validation_and_input_preservation(self):
        original = [report(), report(1, matched=11)]
        snapshot = copy.deepcopy(original)
        selected = choose_checkpoint(original)
        selected["selected_report"]["cohorts"]["nba_validation"]["matched"] = 999
        self.assertEqual(original, snapshot)
        invalid = [report()]; invalid[0]["cohorts"]["possession_001"]["worst_missing_seconds"] = math.nan
        missing = report(); del missing["cohorts"]["nba_validation"]
        bad_count = report(); bad_count["cohorts"]["nba_validation"]["matched"] = True
        for rows in ([report(1)], [report(), report()], invalid, [missing], [bad_count]):
            with self.assertRaises(ValueError):
                choose_checkpoint(rows)

    def test_stopping_requires_five_epochs_and_five_since_strict_improvement(self):
        self.assertFalse(should_stop(4, 0))
        self.assertTrue(should_stop(5, 0))
        self.assertFalse(should_stop(8, 4))
        self.assertTrue(should_stop(9, 4))
        reports = [report()] + [report(i) for i in range(1, 6)]
        selected = choose_checkpoint(reports)
        self.assertTrue(should_stop(5, selected["selected_epoch"]))
        with self.assertRaises(ValueError):
            should_stop(5, 6)


if __name__ == "__main__":
    unittest.main()
