"""Quality-target and transport checks from the authorized emitted capture.

No model, image or protected source is opened. Local producer records supply
the critical schema fixtures; their absence is an explicit test skip.
"""
from copy import deepcopy
import json
import math
from pathlib import Path
import unittest

from src.ball_tracking import candidate_quality_data as data


class CandidateQualityDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = data.ROOT / data.CAPTURE_BASE
        if not (base / "capture_attempt_001/completed.json").exists():
            raise unittest.SkipTest("Ignored authorized capture unavailable")
        prepared = data.read_json(base / "prepared.json")
        cls.package = data.read_json(data.ROOT / prepared["package"]["path"])
        complete = data.read_json(base / "capture_attempt_001/completed.json")
        cls.records = {}
        for link in complete["records"]:
            record = data.read_json(data.ROOT / link["path"])
            cls.records[record["block_id"]] = record

    def actual(self, block_id=None, offset=0):
        block = next(b for b in self.package["training_blocks"]
                     if b["block_id"] == block_id) if block_id else self.package["training_blocks"][0]
        record = self.records[block["block_id"]]
        link = record["extraction"]["pools"]
        with (data.ROOT / link["path"]).open(encoding="utf-8") as stream:
            pool = json.loads(next(line for i, line in enumerate(stream) if i == offset))
        return deepcopy((block, block["frames"][offset], record["native_observations"][offset], pool, link))

    def test_actual_emitted_candidate_transport_and_original_fields(self):
        block, frame, observation, pool, link = self.actual()
        frame_row, candidates = data.make_frame_rows(block, frame, observation, pool, link)
        self.assertEqual(len(candidates), 5)
        self.assertEqual([r["native_or_weak"] for r in candidates], ["native"] + ["weak"] * 4)
        self.assertEqual([r["target"] for r in candidates], [1, 0, 0, 0, 0])
        self.assertEqual([r["producer_candidate"] for r in candidates], pool["candidates"])
        self.assertEqual(frame_row["candidate_ids"], [r["candidate_id"] for r in candidates])
        self.assertEqual(frame_row["source_png"], frame["png"])
        self.assertAlmostEqual(candidates[0]["distance_px"], 1.6380846550504857)
        changed_link = dict(link, sha256="0" * 64)
        other_frame, other = data.make_frame_rows(block, frame, observation, pool, changed_link)
        self.assertEqual(other_frame["frame_id"], frame_row["frame_id"])
        self.assertNotEqual(other[0]["candidate_id"], candidates[0]["candidate_id"])

    def test_actual_transport_rejects_clock_native_and_origin_mutations(self):
        for mutation in ("clock", "native", "origin", "bounds", "index"):
            block, frame, observation, pool, link = self.actual()
            if mutation == "clock":
                pool["source_pts_ticks"] += 1
            elif mutation == "native":
                pool["candidates"][0]["native_score"] += 1
            elif mutation == "origin":
                pool["candidates"][1]["extraction"] = "native_component"
            elif mutation == "bounds":
                pool["candidates"][1]["in_source_bounds"] = False
            else:
                pool["candidates"][1]["candidate_index"] = 8
            with self.assertRaises(ValueError, msg=mutation):
                data.make_frame_rows(block, frame, observation, pool, link)

    def test_inclusive_ten_and_uncertainty_boundary_are_asymmetric(self):
        block, frame, _, pool, _ = self.actual()
        candidate = deepcopy(pool["candidates"][0])
        center = frame["annotation"]["geometry"]["center_xy_px"]
        uncertainty = frame["annotation"]["geometry"]["uncertainty_radius_px"]
        for distance, expected in ((10, 1), (10.5, None), (10 + uncertainty, None),
                                   (10 + uncertainty + 0.01, 0)):
            candidate["center_x"], candidate["center_y"] = center[0] + distance, center[1]
            row = data.candidate_target(frame, candidate, block["source_video"]["width_px"],
                                        block["source_video"]["height_px"])
            self.assertEqual(row["target"], expected)
        candidate["center_x"], candidate["in_source_bounds"] = -1, False
        self.assertEqual(data.candidate_target(frame, candidate, 1280, 720)["target"], 0)

    def test_masked_geometry_remains_unknown(self):
        block = next(b for b in self.package["training_blocks"] if b["game_id"] == "possession_002")
        offset = next(i for i, f in enumerate(block["frames"]) if f["kind"] == "masked")
        block, frame, observation, pool, link = self.actual(block["block_id"], offset)
        self.assertIsNotNone(frame["annotation"]["geometry"])
        _, rows = data.make_frame_rows(block, frame, observation, pool, link)
        self.assertTrue(rows)
        self.assertTrue(all(r["target"] is None and r["target_group"] == "masked_unknown" for r in rows))

    def test_empty_hidden_frame_is_preserved_and_hidden_candidates_are_negative(self):
        found_empty = found_nonempty = False
        for block in self.package["training_blocks"]:
            record = self.records[block["block_id"]]
            pools = [json.loads(s) for s in (data.ROOT / record["extraction"]["pools"]["path"]).read_text().splitlines()]
            for frame, observation, pool in zip(block["frames"], record["native_observations"], pools, strict=True):
                if frame["kind"] != "hidden":
                    continue
                row, candidates = data.make_frame_rows(block, frame, observation, pool, record["extraction"]["pools"])
                self.assertEqual(row["kind"], "hidden")
                if not candidates:
                    found_empty = True
                    self.assertEqual(row["candidate_ids"], [])
                else:
                    found_nonempty = True
                    self.assertTrue(all(c["target"] == 0 and c["target_group"] == "certain_hidden" for c in candidates))
            if found_empty and found_nonempty:
                break
        self.assertTrue(found_empty and found_nonempty)

    def test_actual_single_weak_only_recovery_keeps_its_positive(self):
        block, frame, observation, pool, link = self.actual("chi-vs-ind-0022400868_e02", 83)
        _, rows = data.make_frame_rows(block, frame, observation, pool, link)
        self.assertIsNone(observation["center_xy_px"])
        positives = [r for r in rows if r["target"] == 1]
        self.assertEqual(len(positives), 1)
        self.assertEqual(positives[0]["native_or_weak"], "weak")

    def test_source_role_gate_excludes_hou_det_tor_and_unknown_sources(self):
        block = deepcopy(self.package["training_blocks"][0])
        for game in ("0022400879", "0022500828", "0022500843", "protected_unknown"):
            block["game_id"] = game
            with self.assertRaises(ValueError):
                data.validate_source_block(block)
        block["game_id"] = data.NBA_GAMES[0]
        block["role"] = "checkpoint_validation"
        with self.assertRaises(ValueError):
            data.validate_source_block(block)

    def weighted_fixture(self):
        def row(identity, frame, origin, group, game=data.NBA_GAMES[0], domain="nba"):
            return {"candidate_id": identity, "frame_id": frame, "block_id": "b", "game_id": game,
                    "domain": domain, "native_or_weak": origin, "target_group": group,
                    "target": None if group == "masked_unknown" else int(group == "positive")}
        return [row("a", "f1", "native", "positive"), row("b", "f1", "native", "positive"),
                row("c", "f1", "weak", "positive"), row("d", "f2", "native", "positive"),
                row("e", "f3", "weak", "eligible_distant_miss"), row("f", "f4", "weak", "certain_hidden"),
                row("unknown", "f5", "weak", "masked_unknown"),
                row("nfhs", "f6", "weak", "positive", "possession_001", "nfhs"),
                row("held", "f7", "weak", "positive", data.NBA_GAMES[1])]

    def test_hierarchical_weighting_preserves_frame_origin_and_stratum_mass(self):
        weights, summary = data.fit_weights(self.weighted_fixture(), (data.NBA_GAMES[0],))
        actual = {r["candidate_id"]: r["objective_weight"] for r in weights}
        self.assertEqual(actual, {"a": 0.0625, "b": 0.0625, "c": 0.125, "d": 0.25, "e": 0.25, "f": 0.25})
        self.assertEqual(summary["fitting_candidates"], 6)
        self.assertEqual(summary["weight_sum"], 1)
        self.assertEqual(summary["total_training_steps"], 6)
        self.assertTrue(all(math.isclose(r["training_multiplier"], 6 * r["objective_weight"]) for r in weights))

    def test_missing_stratum_duplicates_and_forbidden_fit_games_fail(self):
        rows = self.weighted_fixture()
        with self.assertRaises(ValueError):
            data.fit_weights([r for r in rows if r["target_group"] != "certain_hidden"], (data.NBA_GAMES[0],))
        with self.assertRaises(ValueError):
            data.fit_weights(rows + [rows[0]], (data.NBA_GAMES[0],))
        with self.assertRaises(ValueError):
            data.fit_weights(rows, ("0022400879",))


if __name__ == "__main__":
    unittest.main()
