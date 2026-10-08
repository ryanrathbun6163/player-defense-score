"""Derived checkpoint checks use actual torch serialization and a tiny model."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import torch

from src.ball_tracking.wasb_adapter import WasbAdapter
from src.ball_tracking.wasb_adapted_adapter import AdaptedWasbAdapter


class WasbAdaptedAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.pretrained = self.root / "original.pth"
        self.pretrained.write_bytes(b"original boundary represented by the existing adapter")
        self.checkpoint = self.root / "adapted.pth"
        self.provenance = {"successful_updates": 200, "training_manifest": {"sha256": "a" * 64}}
        self.model = torch.nn.Linear(2, 3)
        with torch.no_grad():
            self.model.weight.zero_()
            self.model.bias.zero_()

        def original_boundary(instance, source_root, checkpoint_path, device="cuda"):
            self.assertEqual(source_root, self.root)
            self.assertEqual(checkpoint_path, self.pretrained)
            self.assertEqual(device, "cpu")
            instance.source_root = self.root
            instance.checkpoint_path = self.pretrained
            instance.device = torch.device(device)
            instance.model = self.model.eval()
            instance.provenance = {
                "source_revision": "pinned-original-source",
                "checkpoint_path": str(self.pretrained), "checkpoint_sha256": "b" * 64,
                "checkpoint_size_bytes": self.pretrained.stat().st_size,
                "native_tracker_used": False,
            }

        self.original = mock.patch.object(WasbAdapter, "__init__", autospec=True, side_effect=original_boundary).start()
        self.addCleanup(mock.patch.stopall)

    def save(self, content=None):
        if content is None:
            content = {"model_state_dict": {"weight": torch.ones(3, 2), "bias": torch.arange(3, dtype=torch.float32)}}
        torch.save(content, self.checkpoint)
        return hashlib.sha256(self.checkpoint.read_bytes()).hexdigest()

    def load(self, digest=None, provenance=None):
        return AdaptedWasbAdapter(
            self.root, self.pretrained, self.checkpoint,
            digest if digest is not None else self.save(),
            self.provenance if provenance is None else provenance,
            device="cpu",
        )

    def test_actual_tensor_checkpoint_loads_strictly_and_records_distinct_provenance(self):
        digest = self.save()
        actual_load = torch.load
        with mock.patch("torch.load", wraps=actual_load) as load:
            adapted = self.load(digest)
        self.original.assert_called_once()
        self.assertEqual(load.call_count, 1)
        self.assertIsInstance(load.call_args.args[0], io.BytesIO)
        self.assertEqual(load.call_args.kwargs, {"map_location": "cpu", "weights_only": True})
        torch.testing.assert_close(adapted.model.weight, torch.ones(3, 2), rtol=0, atol=0)
        torch.testing.assert_close(adapted.model.bias, torch.arange(3, dtype=torch.float32), rtol=0, atol=0)
        self.assertFalse(adapted.model.training)
        self.assertEqual(adapted.pretrained_path, self.pretrained)
        self.assertEqual(adapted.checkpoint_path, self.checkpoint)
        self.assertEqual(adapted.provenance["pretrained_checkpoint"]["sha256"], "b" * 64)
        self.assertEqual(adapted.provenance["checkpoint_sha256"], digest)
        self.assertEqual(adapted.provenance["checkpoint_path"], str(self.checkpoint))
        self.assertEqual(adapted.provenance["source_revision"], "pinned-original-source")
        self.assertEqual(adapted.provenance["training_provenance"], self.provenance)
        self.provenance["training_manifest"]["sha256"] = "c" * 64
        self.assertEqual(adapted.provenance["training_provenance"]["training_manifest"]["sha256"], "a" * 64)
        self.assertIs(AdaptedWasbAdapter.predict_triplet, WasbAdapter.predict_triplet)

    def test_digest_is_required_and_mismatch_prevents_deserialization(self):
        self.save()
        for digest in ("", "0" * 63, "A" * 64, True, "0" * 64):
            with self.subTest(digest=digest), mock.patch("torch.load") as load:
                with self.assertRaisesRegex(ValueError, "digest|SHA-256"):
                    self.load(digest)
                load.assert_not_called()

    def test_original_verification_failure_is_preserved_before_derived_load(self):
        self.original.side_effect = ValueError("Original source mismatch")
        with mock.patch("torch.load") as load:
            with self.assertRaisesRegex(ValueError, "Original source mismatch"):
                self.load()
            load.assert_not_called()

    def test_metadata_optimizer_objects_and_non_tensor_states_are_refused(self):
        cases = [
            {"model_state_dict": self.model.state_dict(), "optimizer": {}},
            self.model.state_dict(),
            {"model_state_dict": {}},
            {"model_state_dict": {"weight": "not a tensor"}},
            {"model_state_dict": {3: torch.zeros(1)}},
        ]
        for content in cases:
            with self.subTest(keys=list(content)), self.assertRaises(ValueError):
                self.load(self.save(content))

    def test_missing_extra_or_wrong_shape_tensors_are_strictly_refused(self):
        cases = [
            {"weight": torch.ones(3, 2)},
            {"weight": torch.ones(3, 2), "bias": torch.ones(3), "extra": torch.ones(1)},
            {"weight": torch.ones(3, 4), "bias": torch.ones(3)},
        ]
        for state in cases:
            with self.subTest(keys=list(state)), self.assertRaises(RuntimeError):
                self.load(self.save({"model_state_dict": state}))

    def test_nan_and_infinity_are_refused_before_model_load(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            state = {"weight": torch.full((3, 2), value), "bias": torch.zeros(3)}
            with self.subTest(value=value), mock.patch.object(self.model, "load_state_dict") as load:
                with self.assertRaisesRegex(ValueError, "non-finite"):
                    self.load(self.save({"model_state_dict": state}))
                load.assert_not_called()

    def test_unsafe_pickle_is_not_allowlisted_or_retried(self):
        # A real Python object in the file is rejected by the actual safe loader.
        digest = self.save({"model_state_dict": {"weight": torch.ones(3, 2), "bias": torch.ones(3)},
                            "unsafe_module": torch.nn.Linear(1, 1)})
        actual_load = torch.load
        with mock.patch("torch.load", wraps=actual_load) as load:
            with self.assertRaisesRegex(Exception, "Weights only load failed|Unsupported global"):
                self.load(digest)
            self.assertEqual(load.call_count, 1)
            self.assertTrue(load.call_args.kwargs["weights_only"])

    def test_training_provenance_must_be_nonempty_finite_json(self):
        digest = self.save()
        for provenance in ({}, [], {1: "integer key"}, {"loss": float("nan")}, {"tensor": torch.ones(1)}):
            with self.subTest(provenance=provenance), mock.patch("torch.load") as load:
                with self.assertRaisesRegex(ValueError, "provenance"):
                    self.load(digest, provenance)
                load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
