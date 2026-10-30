"""Actual extraction/producer transport checks, without model or label changes."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from src.ball_tracking.weak_response_experiment import pool_rows, compact_choices, materialize_choices
from src.ball_tracking.weak_response_sequence import observation_rows

ROOT = Path(__file__).resolve().parents[1]
PAIRED = ROOT / "data/outputs/ball_tracking/wasb_continuation_v0_1/paired_review_inputs_v0_1.json"
POOLS = ROOT / "data/outputs/ball_tracking/weak_response_v0_1/feasibility_hou_v0_1/blocks/67eb4e0985d32a496946d9f2/pools.jsonl"


@unittest.skipUnless(PAIRED.is_file() and POOLS.is_file(), "Requires authorized saved development producer/extraction")
class WeakExperimentTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package = json.loads(PAIRED.read_text())
        cls.entry = next(e for e in package["blocks"] if e["block"]["block_id"] == "hou-vs-okc-0022400879_e01")
        with POOLS.open() as stream:
            cls.producer = json.loads(next(stream))

    def read_one(self, record):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pool.jsonl"
            path.write_text(json.dumps(record) + "\n")
            return pool_rows(ROOT, path, self.entry["block"], self.entry["candidate_observations"][:1])

    def test_actual_pool_projection_preserves_every_choice_and_native_candidate(self):
        pool = self.read_one(self.producer)[0]
        self.assertEqual(len(pool), len(self.producer["candidates"]))
        for projected, original in zip(pool, self.producer["candidates"], strict=True):
            self.assertTrue(all(original[k] == v for k, v in projected.items()))
        self.assertEqual(pool[0]["center_x"], self.entry["candidate_observations"][0]["candidates"][0]["center_x"])

    def test_actual_transport_rejects_changed_time_map_and_original_candidate(self):
        for key, value in (("source_pts_ticks", -1), ("mean_heatmap_sha256", "wrong")):
            changed = deepcopy(self.producer); changed[key] = value
            with self.assertRaises(ValueError):
                self.read_one(changed)
        changed = deepcopy(self.producer); changed["candidates"][0]["center_x"] += .01
        with self.assertRaises(ValueError):
            self.read_one(changed)

    def test_compact_choice_roundtrip_requires_full_original_pool_count(self):
        pools = self.read_one(self.producer)
        native = self.entry["candidate_observations"][:1]
        detail = {"frames": [{"selected_pool_position": 0}]}
        observed = observation_rows(native, pools, [0], detail, "sequence_weak", copy_pools=False)
        body = {"observations": compact_choices(observed)}
        self.assertNotIn("candidates", body["observations"][0])
        rebuilt = materialize_choices(body, pools)
        self.assertEqual(rebuilt[0]["candidates"], pools[0])
        self.assertEqual(rebuilt[0]["center_xy_px"], native[0]["center_xy_px"])
        with self.assertRaises(ValueError):
            materialize_choices(body, [pools[0][1:]])


if __name__ == "__main__":
    unittest.main()
