"""Finite synthetic CPU tests; never load a scientific model or fit."""
import copy
import hashlib
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from src.ball_tracking import candidate_producer_transfer_data as data
from src.ball_tracking import candidate_quality_data as original
from src.ball_tracking.candidate_quality_model import preprocess


def candidate(cid, xy=(50.2, 45.7), game=original.NBA_GAMES[0], target=1):
    return {"candidate_id": cid, "frame_id": "frame", "block_id": "block", "source_frame_index": 5,
            "source_video_sha256": "video", "source_png": {"path": "image.png", "bytes": 0,
                "sha256": "png", "rgb_sha256": "rgb"}, "center_xy_px": list(xy),
            "width_px": 100, "height_px": 90, "domain": "nba", "game_id": game,
            "target": target, "target_group": "positive" if target == 1 else "certain_hidden",
            "native_or_weak": "native"}


def augmented(old, additions):
    return [{**r, "producer_population": pop, "training_row_key": pop + "|" + r["candidate_id"]}
            for pop, items in (("cosine_current", old), ("alternate_added", additions)) for r in items]


def fitting_fixture(add=True):
    old, additions = [], []
    for gi, game in enumerate(original.NBA_GAMES):
        for index in range(12):
            row = candidate(f"old{gi}-{index}", game=game, target=1 if index % 3 == 0 else 0)
            row.update(frame_id=f"f{gi}-{index}", block_id=f"b{gi}")
            row["target_group"] = ("positive", "eligible_distant_miss", "certain_hidden")[index % 3]
            old.append(row)
        unknown = candidate(f"unknown{gi}", game=game, target=None)
        unknown["target_group"] = "boundary_unknown"
        old.append(unknown)
        if add:
            additions.append(candidate(f"new{gi}", game=game, target=0))
    union = augmented(old, additions)
    fit = "leave_chi_out"
    games = original.FIT_GAMES[fit]
    weights, _ = original.fit_weights(union, games)
    mapping = {r["candidate_id"]: r for r in union}
    weights = [{**r, "training_row_key": mapping[r["candidate_id"]]["training_row_key"]} for r in weights]
    keys = [r["training_row_key"] for r in weights]
    quota = sum(r["game_id"] in games and r["target"] is not None for r in old)
    sizes = [min(32, quota - start) for start in range(0, quota, 32)]
    schedules = []
    for cycle in range(1, 7):
        order = keys.copy()
        random.Random(data.SEED + cycle).shuffle(order)
        schedules.append({"fit": fit, "round": cycle, "seed": data.SEED + cycle,
                          "population": len(keys), "quota": quota, "batch_sizes": sizes,
                          "training_row_keys": order[:quota]})
    plan = {"fit": fit, "fit_games": list(games), "augmented_known_candidates": len(keys),
            "original_known_candidates": quota, "draws_per_round": quota,
            "batch_sizes_per_round": sizes, "optimizer_updates": 6 * len(sizes),
            "training_presentations": 6 * quota}
    return union, plan, weights, schedules


class TransferDataTests(unittest.TestCase):
    def test_same_crop_shares_pixels_without_conflating_point_or_labels(self):
        old = candidate("old", (50.2, 45.7))
        added = candidate("new", (50.8, 45.3), target=0)
        routes, new, counts = data.make_routes([old], [], [added])
        self.assertEqual(new, [])
        self.assertEqual(counts["reused_old_crops"], 1)
        self.assertEqual((routes[1]["cache"], routes[1]["index"]), ("old_training", 0))
        self.assertNotEqual(routes[0]["point_weights"], routes[1]["point_weights"])
        changed = copy.deepcopy(added)
        changed.update(target=1, target_group="positive", native_or_weak="weak", producer_candidate={"score": 999})
        self.assertEqual(routes, data.make_routes([old], [], [changed])[0])
        self.assertFalse(any("target" in r or "producer_candidate" in r for r in routes))

    def test_source_identity_and_floor_change_prevent_unsafe_reuse(self):
        old = candidate("old")
        shifted = candidate("shifted", (51.0, 45.7))
        other = candidate("other")
        other["source_video_sha256"] = "different_video"
        another = candidate("another")
        another["source_png"]["rgb_sha256"] = "different_rgb"
        routes, new, counts = data.make_routes([old], [], [shifted, other, another])
        self.assertEqual(counts["new_unique_crops"], 3)
        self.assertEqual([r["candidate_id"] for r in new], ["shifted", "other", "another"])
        self.assertTrue(all(r["cache"] == "added" for r in routes[1:]))

    def test_new_crops_deduplicate_pixels_only_and_reject_duplicate_raw_ids(self):
        a, b = candidate("a"), candidate("b", (50.9, 45.1))
        routes, new, counts = data.make_routes([], [], [a, b])
        self.assertEqual(len(new), 1)
        self.assertEqual(counts["reused_within_added_crops"], 1)
        self.assertEqual(routes[0]["index"], routes[1]["index"])
        self.assertNotEqual(routes[0]["point_weights"], routes[1]["point_weights"])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            data.make_routes([a], [], [a])

    def test_population_preserves_unknown_and_rejects_target_source_role_changes(self):
        old = [candidate("old", target=None)]
        added = [candidate("new")]
        novelty = [{"candidate_id": "new", "role_screen_eligible": True, "new_exact_point_vs_current_and_history": True}]
        union = augmented(old, added)
        data.validate_population(old, union, added, novelty)
        for field, value in (("target", 0), ("domain", "nfhs"), ("training_row_key", "wrong")):
            bad = copy.deepcopy(union)
            bad[0][field] = value
            with self.assertRaises(ValueError):
                data.validate_population(old, bad, added, novelty)
        novelty[0]["role_screen_eligible"] = False
        with self.assertRaisesRegex(ValueError, "role"):
            data.validate_population(old, union, added, novelty)

    def test_known_fits_exact_schedule_weight_scale_source_holdout_and_no_addition_parity(self):
        for additions in (False, True):
            union, plan, weights, schedules = fitting_fixture(additions)
            result = data.validate_fit(union, plan, weights, schedules)
            self.assertEqual(result["updates"], 6)
            self.assertEqual(result["presentations"], 144)
            self.assertTrue(all("unknown" not in key for s in schedules for key in s["training_row_keys"]))
            self.assertTrue(all("old0" not in key for s in schedules for key in s["training_row_keys"]))
            if not additions:
                self.assertTrue(all(len(s["training_row_keys"]) == len(weights) for s in schedules))
            bad = copy.deepcopy(weights)
            bad[0]["training_multiplier"] *= .99
            with self.assertRaisesRegex(ValueError, "scale"):
                data.validate_fit(union, plan, bad, schedules)
            bad = copy.deepcopy(schedules)
            bad[0]["training_row_keys"][0] = "cosine_current|old0-0"
            with self.assertRaisesRegex(ValueError, "schedule"):
                data.validate_fit(union, plan, weights, bad)
            bad = copy.deepcopy(schedules)
            bad[0]["batch_sizes"] = [23, 1]
            with self.assertRaisesRegex(ValueError, "schedule"):
                data.validate_fit(union, plan, weights, bad)

    def test_pixel_cache_exact_original_preprocessing_black_padding_and_exclusive_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pixels = np.arange(100 * 90 * 3, dtype=np.uint32).reshape(90, 100, 3).astype(np.uint8)
            image = Image.fromarray(pixels)
            image.save(root / "image.png")
            first, second = candidate("a", (0.2, 0.8)), candidate("b", (75.6, 67.1))
            link = {**data.binding(root, root / "image.png"), "rgb_sha256": hashlib.sha256(image.tobytes()).hexdigest()}
            first["source_png"] = second["source_png"] = link
            receipt = data.materialize_added_crops(root, [first, second], root / "added.npy")
            self.assertEqual(receipt["decoded_source_pngs"], 1)
            cache = np.load(root / "added.npy", mmap_mode="r")
            self.assertTrue(np.all(cache[0, :32] == 0))
            routes, _, _ = data.make_routes([], [], [first, second])
            loaded = {"routes": {r["input_key"]: r for r in routes}}
            x, point = data.batch_arrays(["b", "a"], loaded, {"added": cache})
            for index, row in enumerate((second, first)):
                expected_x, expected_point = preprocess(image, row["center_xy_px"])
                np.testing.assert_array_equal(x[index], expected_x)
                np.testing.assert_array_equal(point[index], expected_point)
            self.assertEqual(point.dtype, np.float64)
            with self.assertRaisesRegex(ValueError, "replace"):
                data.materialize_added_crops(root, [first], root / "added.npy")
            data.close_caches({"added": cache})

    def test_bad_source_bytes_dimensions_and_rgb_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image = Image.new("RGB", (100, 90), (20, 40, 60))
            image.save(root / "image.png")
            row = candidate("a")
            row["source_png"] = {**data.binding(root, root / "image.png"), "rgb_sha256": "wrong"}
            with self.assertRaisesRegex(ValueError, "RGB"):
                data.materialize_added_crops(root, [row], root / "bad.npy")
            self.assertFalse((root / "bad.npy").exists())
            row["source_png"]["rgb_sha256"] = hashlib.sha256(image.tobytes()).hexdigest()
            row["width_px"] = 99
            with self.assertRaisesRegex(ValueError, "dimensions"):
                data.materialize_added_crops(root, [row], root / "bad.npy")

    def test_missing_and_malformed_queries_never_fall_back(self):
        row = candidate("a")
        missing = {**row, "query_id": "missing", "input_id": None, "center_xy_px": None}
        routes, _, _ = data.make_routes([row], [missing], [])
        loaded = {"routes": {r["input_key"]: r for r in routes}}
        cache = {"old_training": np.zeros((1, 64, 64, 3), dtype=np.uint8)}
        for ids in (["missing"], ["unknown"], [], ["a"] * 33):
            with self.assertRaises(ValueError):
                data.batch_arrays(ids, loaded, cache)
        loaded["routes"]["a"]["point_weights"] = [float("nan"), 0, 0, 1]
        with self.assertRaisesRegex(ValueError, "point weights"):
            data.batch_arrays(["a"], loaded, cache)

    def test_scoring_plan_rejects_source_leak_reorder_and_missing_scoring(self):
        old = [candidate("c" + str(i), game=g) for i, g in enumerate(original.NBA_GAMES)]
        nfhs = candidate("n", game="possession_001")
        nfhs["domain"] = "nfhs"
        old.append(nfhs)
        added = [candidate("a" + str(i), game=g) for i, g in enumerate(original.NBA_GAMES)]
        queries = [{"query_id": "yes", "input_id": "i"}, {"query_id": "no", "input_id": None}]
        scoring = []
        for i, (fit, game) in enumerate(zip(tuple(original.FIT_GAMES)[:3], original.NBA_GAMES)):
            for owner, pop, ids in (("new_treatment", "original_held_NBA", ["c" + str(i)]),
                                    ("new_treatment", "added_held_challenge", ["a" + str(i)]),
                                    ("saved_Q_control", "added_held_challenge", ["a" + str(i)])):
                scoring.append({"fit": fit, "owner": owner, "population": pop, "game_id": game,
                                "id_field": "candidate_id", "ids": ids, "forwards": 1})
        for pop, field, ids in (("NFHS_secondary", "candidate_id", ["n"]), ("original_external_registry", "query_id", ["yes"])):
            scoring.append({"fit": "all_nba", "owner": "new_treatment", "population": pop,
                            "id_field": field, "ids": ids, "forwards": 1})
        self.assertEqual(data.validate_scoring_plan(old, queries, added, scoring)["presentations"], 11)
        for change in ("source", "order", "missing"):
            bad = copy.deepcopy(scoring)
            if change == "source":
                bad[0]["fit"] = "all_nba"
            elif change == "order":
                bad[:2] = list(reversed(bad[:2]))
            else:
                bad[-1]["ids"].append("no")
            with self.assertRaisesRegex(ValueError, "Scoring"):
                data.validate_scoring_plan(old, queries, added, bad)

    def test_failed_preparation_is_preserved_and_no_retry_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "attempt"
            with patch.object(data, "_read_design", side_effect=ValueError("broken binding")):
                with self.assertRaisesRegex(ValueError, "broken"):
                    data.prepare(root, destination)
            failed = (destination / "failed.json").read_bytes()
            self.assertIn("broken binding", json.loads(failed)["error"])
            with self.assertRaises(FileExistsError):
                data.prepare(root, destination)
            self.assertEqual((destination / "failed.json").read_bytes(), failed)


if __name__ == "__main__":
    unittest.main()
