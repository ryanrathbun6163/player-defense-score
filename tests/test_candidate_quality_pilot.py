"""Metadata and actual producer/consumer checks; never run a neural model."""
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

from src.ball_tracking import candidate_quality_model as model
from src.ball_tracking import candidate_quality_pilot as pilot
from src.ball_tracking.nba_appearance_feature_screen import crop_and_preprocess

ROOT = Path(__file__).resolve().parents[1]


class CandidateQualityPilotTests(unittest.TestCase):
    def test_import_does_not_initialize_ml_runtime(self):
        code = "import sys; from src.ball_tracking import candidate_quality_pilot; assert 'torch' not in sys.modules"
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_exact_current_weight_transport_and_fixed_budget(self):
        base = ROOT / pilot.OUTPUT / "preparation"
        if not (base / "prepared.json").exists():
            self.skipTest("Requires the authorized captured training preparation")
        candidates = {r["candidate_id"]: r for r in pilot.rows(base / "candidates.jsonl")}
        steps = exposures = 0
        all_members = []
        for name in pilot.FIT_NAMES:
            manifest = pilot.read(base / "fits" / name / "manifest.json")
            weights = pilot.rows(base / "fits" / name / "weights.jsonl")
            fitting = pilot.validate_weights(candidates, weights)
            self.assertEqual({r["game_id"] for r in fitting}, set(manifest["fit_game_ids"]))
            self.assertFalse({r["game_id"] for r in fitting} & set(manifest["held_out_game_ids"]))
            self.assertTrue(all(r["domain"] == "nba" and r["target"] is not None for r in fitting))
            self.assertEqual(len(fitting), manifest["fitting_candidates"])
            self.assertEqual(sum(len(b) for b in pilot.batches(fitting, 32)), len(fitting))
            steps += math.ceil(len(fitting)/32) * 6
            exposures += len(fitting)*6
            all_members.extend(r["candidate_id"] for r in fitting)
        self.assertEqual(steps, 9870)
        self.assertEqual(exposures, 315432)
        # Two other-game fits plus the all-game fit, never the own-game fit.
        from collections import Counter
        self.assertEqual(set(Counter(all_members).values()), {3})

    def test_unknown_secondary_bad_weight_and_duplicate_rejected(self):
        for invalid in ({"domain": "nfhs", "target": 1}, {"domain": "nba", "target": None}):
            with self.assertRaises(ValueError):
                pilot.validate_weights({"c": invalid}, [{"candidate_id": "c", "objective_weight": 1., "training_multiplier": 1.}])
        candidate = {"c": {"domain": "nba", "target": 1}}
        for weight in (0., -1., math.nan, math.inf, .5):
            with self.assertRaises(ValueError):
                pilot.validate_weights(candidate, [{"candidate_id": "c", "objective_weight": weight, "training_multiplier": weight}])
        weight = {"candidate_id": "c", "objective_weight": 1., "training_multiplier": 1.}
        with self.assertRaises(ValueError):
            pilot.validate_weights(candidate, [weight, weight])

    def test_native_crop_cache_matches_original_pixel_producer(self):
        # Cache transport is distinct from the model's preprocessing helper.
        yy, xx = np.indices((83, 97))
        image = Image.fromarray(np.stack((xx*2, yy*3, (xx+yy) % 256), axis=-1).astype(np.uint8))
        centers = [[0., 0.], [48.25, 42.75], [96.999, 82.999]]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "source.png"
            image.save(path)
            link = pilot.binding(root, path)
            items = [{"query_id": str(i), "source_png": link, "center_xy_px": center}
                     for i, center in enumerate(centers)]
            cache, weights, index = pilot.make_crop_cache(root, items, "query_id", root / "crops.npy", model)
            try:
                for item in items:
                    i = index[item["query_id"]]
                    original_crop, _, original_input = crop_and_preprocess(image, item["center_xy_px"])
                    self.assertTrue(np.array_equal(cache[i], original_crop))
                    cached_input = crop_and_preprocess(Image.fromarray(np.asarray(cache[i])), [32., 32.])[2]
                    self.assertTrue(np.array_equal(cached_input, original_input))
                    self.assertTrue(np.array_equal(weights[i], model.preprocess(image, item["center_xy_px"])[1]))
            finally:
                cache._mmap.close()

    def test_changed_image_binding_rejected_before_cache_use(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "data"
            path.write_bytes(b"original")
            link = pilot.binding(root, path)
            path.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                pilot.bound(root, link)

    def test_preflight_needs_specific_new_approval(self):
        if not (ROOT / pilot.OUTPUT / "execution_freeze.json").exists():
            self.skipTest("Final freeze not yet written")
        # Emulate an absent new approval without modifying any real approval.
        code = ("import sys; from unittest.mock import patch; from src.ball_tracking import candidate_quality_pilot as p; "
                "original=p.read\n"
                "def read(path):\n"
                " if path.name == 'execution_approval.json': raise FileNotFoundError('test missing approval')\n"
                " return original(path)\n"
                "with patch.object(p, 'read', read):\n"
                " try: p.preflight(require_approval=True)\n"
                " except FileNotFoundError as e: assert str(e) == 'test missing approval'\n"
                " else: raise AssertionError('missing approval accepted')\n"
                "assert 'torch' not in sys.modules\n")
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
