"""Protect the original-weight control from silently becoming another fitted arm."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from src.ball_tracking.nba_original_control import validate_config


class OriginalControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.config = json.loads((root / "configs/ball_tracking/proposals/nba_original_weight_control_v0_1.json").read_text())
        cls.previous = json.loads((root / "configs/ball_tracking/proposals/nba_first_saved_models_v0_1.json").read_text())

    def test_actual_manifest_and_budget(self):
        validate_config(self.config)
        self.assertEqual(len(self.config["block_ids"]), 8)
        self.assertEqual(self.config["block_ids"], self.previous["block_ids"])
        self.assertEqual(self.config["policy"], self.previous["inference_policy"])

    def test_existing_adapted_weights_cannot_masquerade_as_original(self):
        for model in self.previous["models"]:
            changed = deepcopy(self.config)
            changed["checkpoint"] = model["checkpoint"]
            with self.assertRaisesRegex(ValueError, "Original pinned"):
                validate_config(changed)

    def test_no_training_protected_or_call_budget_expansion(self):
        for field, value in (("training_authorized", True), ("protected_evaluation_authorized", True),
                             ("new_model_calls", 3647)):
            changed = deepcopy(self.config)
            changed[field] = value
            with self.assertRaises(ValueError):
                validate_config(changed)

    def test_threshold_or_interpolation_change_is_rejected(self):
        for field, value in (("threshold", .29), ("interpolation", True)):
            changed = deepcopy(self.config)
            changed["policy"][field] = value
            with self.assertRaisesRegex(ValueError, "policy"):
                validate_config(changed)


if __name__ == "__main__":
    unittest.main()
