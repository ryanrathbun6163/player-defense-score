"""Bounded synthetic checks for saved metadata and honest nested score joins."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from src.ball_tracking import candidate_acceptance_data as data


def nested_fixture():
    candidates, scores = [], []
    for name, game in data.GAMES.items():
        for suffix, target in (("match", 1), ("miss", 0), ("unknown", None)):
            cid = name + "_" + suffix
            candidates.append({
                "candidate_id": cid, "row_key": "old|" + cid,
                "frame_id": name + "_frame", "frame_key": "old|" + name + "_frame",
                "fit": data.OLD_FITS[name], "game_id": game, "context": "nba_out_of_fold",
                "cohort": "package", "target": target,
                "target_group": "masked_unknown" if target is None else "positive" if target else "negative",
                "center_xy_px": [10 * len(candidates), 2], "native_score": 7,
                "component_pixels": 3, "padding_pixels": 0, "native_or_weak": "native",
                "logit": -99, "visibility": "visible", "distance_px": 7,
            })
    for source in data.GAMES:
        for number, row in enumerate(candidates):
            if row["game_id"] != data.GAMES[source]:
                scores.append({"fit": source + "_only", "candidate_id": row["candidate_id"],
                               "game_id": row["game_id"], "frame_id": row["frame_id"],
                               "quality_logit": number + .125})
    weights = {}
    for gate in ("outer_CHI", "outer_DEN", "outer_SAC", "final_all_NBA"):
        held = data.GAMES.get(gate.removeprefix("outer_"))
        included = [r for r in candidates if r["target"] is not None and r["game_id"] != held]
        weights[gate] = {r["candidate_id"]: {"candidate_id": r["candidate_id"],
                                            "objective_weight": 1 / len(included)} for r in included}
    return {"nba_candidates": candidates, "weights": weights}, scores


class CandidateAcceptanceDataTests(unittest.TestCase):
    def test_cross_score_join_preserves_metadata_and_only_replaces_declared_fields(self):
        saved, scores = nested_fixture()
        original = copy.deepcopy(saved)
        scores[0].update(target=999, center_xy_px=[9999, 9999], native_score=9999)
        joined = data.attach_cross_scores(saved["nba_candidates"], scores)
        old = {r["candidate_id"]: r for r in saved["nba_candidates"]}
        self.assertEqual(len(joined), 18)
        self.assertEqual(saved, original)
        for row, supplied in zip(joined, scores):
            baseline = old[row["candidate_id"]]
            self.assertEqual(row["logit"], supplied["quality_logit"])
            self.assertEqual(row["row_key"], supplied["fit"] + "|" + row["candidate_id"])
            self.assertEqual(row["frame_key"], supplied["fit"] + "|" + baseline["frame_id"])
            self.assertEqual(row["old_metadata_row_key"], baseline["row_key"])
            for key in ("target", "target_group", "center_xy_px", "native_score", "distance_px", "visibility"):
                self.assertEqual(row[key], baseline[key])
            self.assertNotEqual(row["game_id"], data.GAMES[row["fit"].removesuffix("_only")])

    def test_each_outer_gate_excludes_held_game_from_both_sources_and_retains_unknown_pool(self):
        saved, scores = nested_fixture()
        cross = data.attach_cross_scores(saved["nba_candidates"], scores)
        for held, held_id in data.GAMES.items():
            with self.subTest(held=held):
                selected, fitting = data.gate_training_rows("outer_" + held, saved, cross)
                self.assertEqual(len(selected), 6)
                self.assertEqual(len(fitting), 4)
                self.assertEqual(sum(r["target"] is None for r in selected), 2)
                self.assertEqual({r["target"] for r in fitting}, {0, 1})
                expected = {(source + "_only", r["candidate_id"])
                            for source, source_id in data.GAMES.items() if source != held
                            for r in saved["nba_candidates"]
                            if r["game_id"] not in (source_id, held_id)}
                self.assertEqual({(r["fit"], r["candidate_id"]) for r in selected}, expected)
                pools = data.pool_index(selected)
                self.assertEqual(sum(len(pool) for pool in pools.values()), 6)
                self.assertEqual(len(pools), 2)
                self.assertTrue(all(len(pool) == 3 for pool in pools.values()))

    def test_final_gate_reuses_old_out_of_fold_rows_and_exact_weight_membership(self):
        saved, scores = nested_fixture()
        selected, fitting = data.gate_training_rows("final_all_NBA", saved, [])
        self.assertIs(selected, saved["nba_candidates"])
        self.assertEqual(len(selected), 9)
        self.assertEqual(len(fitting), 6)
        self.assertTrue(all(r["logit"] == -99 for r in selected))
        for row in selected:
            expected = "outer_" + next(name for name, gid in data.GAMES.items() if gid == row["game_id"])
            self.assertEqual(data.gate_for_evaluation(row), expected)
        for context in ("HOU_development", "nfhs_external", "historical"):
            self.assertEqual(data.gate_for_evaluation({"context": context}), "final_all_NBA")
        saved["weights"]["final_all_NBA"]["lost"] = {"candidate_id": "lost"}
        with self.assertRaisesRegex(ValueError, "membership lost"):
            data.gate_training_rows("final_all_NBA", saved, [])

    def test_cross_score_identity_malformed_duplicate_missing_and_leaking_rows_rejected(self):
        saved, scores = nested_fixture()
        scenarios = []
        changed = copy.deepcopy(scores); changed.pop(); scenarios.append(("incomplete", changed))
        scenarios.append(("Duplicate cross-score", scores + [scores[0]]))
        for field, value, reason in (("candidate_id", "absent", "Unknown scored"),
                                     ("fit", "all_nba", "Unknown new base"),
                                     ("game_id", "wrong", "game transport"),
                                     ("frame_id", "wrong", "frame transport"),
                                     ("quality_logit", None, "Nonfinite/missing"),
                                     ("quality_logit", True, "Nonfinite/missing"),
                                     ("quality_logit", float("inf"), "Nonfinite/missing"),
                                     ("quality_logit", float("nan"), "Nonfinite/missing")):
            changed = copy.deepcopy(scores); changed[0][field] = value
            scenarios.append((reason, changed))
        leaked = {"fit": "CHI_only", "candidate_id": "CHI_match", "quality_logit": 0}
        scenarios.append(("fitting game", scores + [leaked]))
        for reason, altered in scenarios:
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(ValueError, reason):
                    data.attach_cross_scores(saved["nba_candidates"], altered)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            data.attach_cross_scores(saved["nba_candidates"] + [saved["nba_candidates"][0]], scores)

    def test_gate_join_rejects_missing_fit_rows_duplicate_base_sources_and_unknown_targets(self):
        saved, scores = nested_fixture()
        cross = data.attach_cross_scores(saved["nba_candidates"], scores)
        selected, _ = data.gate_training_rows("outer_CHI", saved, cross)
        missing = [r for r in cross if r["row_key"] != selected[0]["row_key"]]
        with self.assertRaisesRegex(ValueError, "membership lost"):
            data.gate_training_rows("outer_CHI", saved, missing)
        with self.assertRaisesRegex(ValueError, "multiple base sources"):
            data.gate_training_rows("outer_CHI", saved, cross + [selected[0]])
        changed = copy.deepcopy(cross)
        next(r for r in changed if r["row_key"] == selected[0]["row_key"])["target"] = None
        with self.assertRaisesRegex(ValueError, "Unknown fitting target"):
            data.gate_training_rows("outer_CHI", saved, changed)
        with self.assertRaisesRegex(ValueError, "Unknown outer gate"):
            data.gate_training_rows("outer_INVALID", saved, cross)

    def test_observable_whitelist_independent_of_all_annotation_and_target_fields(self):
        saved, _ = nested_fixture()
        before = saved["nba_candidates"][0]
        after = {**before, "target": 0, "target_group": "certain_hidden", "game_id": "changed",
                 "visibility": "hidden", "distance_px": 1e9, "recorded_uncertainty_radius_px": 999,
                 "annotation": {"geometry": {"center_xy_px": [200, 200]}},
                 "reference_category": "masked", "rank_margin": 100, "difficulty_tags": ["changed"]}
        expected = {"row_key", "frame_key", "fit", "cohort", "logit", "center_xy_px", "native_score",
                    "component_pixels", "padding_pixels", "native_or_weak"}
        self.assertEqual(set(data.observable(before)), expected)
        self.assertEqual(data.observable(before), data.observable(after))
        self.assertEqual(data.observable({})["padding_pixels"], None)
        pools = data.pool_index([before, {**before, "cohort": "HOU_stress", "row_key": "external"},
                                 {**before, "cohort": "historical", "row_key": "historical"}])
        self.assertEqual(pools, {before["frame_key"]: [data.observable(before)]})
        with self.assertRaisesRegex(ValueError, "Main-pool score unavailable"):
            data.pool_index([{**before, "logit": None}])

    def test_jsonl_reader_bom_blank_lines_and_unique_key_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "small.jsonl"
            path.write_text(json.dumps({"id": "a", "score": None}) + "\n\n" + json.dumps({"id": "b", "score": 0}),
                            encoding="utf-8-sig")
            loaded = list(data.rows(path))
            self.assertEqual(loaded, [{"id": "a", "score": None}, {"id": "b", "score": 0}])
            self.assertEqual(set(data.unique(loaded, "id", "test")), {"a", "b"})
            with self.assertRaisesRegex(ValueError, "duplicate"):
                data.unique(loaded + [loaded[0]], "id", "test")


if __name__ == "__main__":
    unittest.main()
