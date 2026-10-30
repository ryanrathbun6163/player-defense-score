"""Synthetic-only checks for removing exactly two origin input dimensions."""
import copy
import json
import math
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from src.ball_tracking import candidate_acceptance_features as original
from src.ball_tracking import candidate_acceptance_origin_model as ablation


def row(key, quality, *, origin="native", mass=3, pixels=4, padding=0):
    probe = {"row_key": key, "frame_key": key + "_frame", "fit": "synthetic", "cohort": "package",
             "logit": quality, "center_xy_px": None if quality is None else [0, 0],
             "native_or_weak": origin, "native_score": mass, "component_pixels": pixels, "padding_pixels": padding}
    return original.build_feature_row(probe, [] if quality is None else [probe])


def fixture():
    features = [row(str(i), q, origin="native" if i % 2 else "weak",
                    mass=2 + i, pixels=None if i == 3 else i + 1, padding=i * 7)
                for i, q in enumerate((-4, -2, -1, -.5, .5, 1, 2, 4))]
    return features, [0, 0, 0, 1, 0, 1, 1, 1], [.125] * 8


def set_value(feature, name, value):
    feature["raw_features"][name] = value
    feature["values"][original.FEATURE_NAMES.index(name)] = value


class CandidateAcceptanceOriginModelTests(unittest.TestCase):
    def test_removed_indicators_cannot_change_fitting_arrays_model_or_predictions(self):
        features, targets, weights = fixture()
        unchanged = copy.deepcopy(features)
        changed = copy.deepcopy(features)
        for i, feature in enumerate(changed):
            set_value(feature, "native_indicator", 1 - i % 2)
            set_value(feature, "origin_unavailable", i % 2)
        before = ablation.fit_origin_gate(features, targets, weights, fit_id="synthetic")
        after = ablation.fit_origin_gate(changed, targets, weights, fit_id="synthetic")
        self.assertEqual(before, after)
        self.assertEqual(ablation.score_origin_gate(before, features), ablation.score_origin_gate(before, changed))
        self.assertEqual(features, unchanged)
        self.assertEqual(before["arm"], "A")
        self.assertEqual(before["feature_names"], [name for name in original.FEATURE_NAMES
                                                 if name not in ("native_indicator", "origin_unavailable")])
        self.assertEqual(len(before["coefficients"]), 14)
        self.assertEqual(before["training_arrays"]["features"]["shape"], [8, 14])
        self.assertEqual(before["training_row_keys"], [r["row_key"] for r in features])
        self.assertFalse(before["calibrated_probability_claim"])
        restored = json.loads(json.dumps(before, allow_nan=False))
        self.assertEqual(ablation.score_origin_gate(restored, features), ablation.score_origin_gate(before, features))

    def test_same_scaling_and_exact_frozen_objective_solver_recipe_as_joint_gate(self):
        features, targets, _ = fixture()
        weights = [.05, .1, .1, .15, .2, .1, .1, .2]
        fake = SimpleNamespace(success=True, status=0, message="synthetic contract", nit=1, nfev=1,
                               x=np.zeros(15), fun=math.log(2), jac=np.zeros(15))
        with patch.object(ablation, "minimize", return_value=fake) as solver:
            model = ablation.fit_origin_gate(features, targets, weights, fit_id="contract")
        objective, initial = solver.call_args.args
        self.assertIs(objective, original._objective)
        np.testing.assert_array_equal(initial, np.zeros(15, dtype=np.float64))
        kwargs = solver.call_args.kwargs
        self.assertEqual(kwargs["method"], "L-BFGS-B")
        self.assertTrue(kwargs["jac"])
        self.assertIsNone(kwargs["bounds"])
        self.assertEqual(kwargs["options"], {"maxiter": 10000, "ftol": 1e-12, "gtol": 1e-9})
        matrix, y, w = kwargs["args"]
        self.assertEqual(matrix.dtype, np.float64)
        np.testing.assert_array_equal(y, targets)
        np.testing.assert_array_equal(w, weights)
        scaler = original.fit_standardizer(features, weights, list(ablation.FEATURE_NAMES))
        self.assertEqual(model["scaler"], scaler)
        np.testing.assert_array_equal(matrix, original.transform_features(features, scaler))
        all_scaler = original.fit_standardizer(features, weights)
        for i, name in enumerate(ablation.FEATURE_NAMES):
            old_i = original.FEATURE_NAMES.index(name)
            self.assertEqual(scaler["means"][i], all_scaler["means"][old_i])
            self.assertEqual(scaler["scales"][i], all_scaler["scales"][old_i])
        theta = np.arange(15, dtype=np.float64) / 10
        logits = theta[0] + matrix @ theta[1:]
        manual_loss = np.dot(w, np.logaddexp(0, logits) - y * logits) + .01 / 2 * np.dot(theta[1:], theta[1:])
        self.assertAlmostEqual(objective(theta, matrix, y, w)[0], manual_loss, places=14)
        self.assertEqual(model["training_arrays"]["features"], original._array_binding(matrix))
        self.assertEqual(model["training_arrays"]["targets"], original._array_binding(y))
        self.assertEqual(model["training_arrays"]["weights"], original._array_binding(w))
        self.assertEqual(model["solver"]["ridge"], .01)
        self.assertAlmostEqual(model["solver"]["initial_loss"], math.log(2), places=14)

    def test_full_sixteen_feature_input_is_validated_even_for_removed_values(self):
        features, targets, weights = fixture()
        model = ablation.fit_origin_gate(features, targets, weights, fit_id="validation")
        for name in original.FEATURE_NAMES:
            for value in (True, float("nan"), float("inf"), "1"):
                with self.subTest(name=name, value=value):
                    changed = copy.deepcopy(features)
                    set_value(changed[0], name, value)
                    with self.assertRaises(original.FeatureIntegrityError):
                        ablation.fit_origin_gate(changed, targets, weights, fit_id="bad")
                    with self.assertRaises(original.FeatureIntegrityError):
                        ablation.score_origin_gate(model, changed)
        for name in ablation.REMOVED_FEATURES:
            for value in (None, 2):
                with self.subTest(name=name, value=value):
                    changed = copy.deepcopy(features)
                    set_value(changed[0], name, value)
                    with self.assertRaises(original.FeatureIntegrityError):
                        ablation.score_origin_gate(model, changed)
        for mutate in (
            lambda r: r.update(feature_names=list(ablation.FEATURE_NAMES)),
            lambda r: r["raw_features"].pop("native_indicator"),
            lambda r: r["values"].pop(),
            lambda r: r.update(Q=999),
        ):
            changed = copy.deepcopy(features)
            mutate(changed[0])
            with self.assertRaises(original.FeatureIntegrityError):
                ablation.score_origin_gate(model, changed)

    def test_observed_zero_missing_slots_and_held_scaling_remain_distinct(self):
        features, targets, weights = fixture()
        model = ablation.fit_origin_gate(features, targets, weights, fit_id="missing")
        scaler_before = copy.deepcopy(model["scaler"])
        held = [row("zero", 0), row("missing", None), row("held", 999, mass=None, pixels=None)]
        scored = ablation.score_origin_gate(model, held)
        self.assertIsInstance(scored[0], float)
        self.assertIsNone(scored[1])
        self.assertIsInstance(scored[2], float)
        self.assertEqual(model["scaler"], scaler_before)
        self.assertEqual(ablation.score_origin_gate(model, []), [])
        self.assertEqual(ablation.score_origin_gate(model, [held[1]]), [None])
        with self.assertRaisesRegex(original.FeatureIntegrityError, "missing-image"):
            ablation.fit_origin_gate([*features[:-1], held[1]], targets, weights, fit_id="bad")
        for field, value in (("Q", 0), ("values", [0] * 16), ("raw_features", {}),
                             ("feature_names", list(ablation.FEATURE_NAMES)), ("status", "unknown")):
            changed = copy.deepcopy(held[1])
            changed[field] = value
            with self.assertRaisesRegex(original.FeatureIntegrityError, "missing score state"):
                ablation.score_origin_gate(model, [changed])

    def test_solver_failure_and_nonfinite_parameters_produce_persistable_failed_record(self):
        features, targets, weights = fixture()
        for success, value in ((False, 0.0), (True, float("nan")), (True, float("inf"))):
            with self.subTest(success=success, value=value):
                parameters = np.zeros(15)
                parameters[0] = value
                fake = SimpleNamespace(success=success, status=2, message="synthetic failure", nit=1, nfev=2,
                                       x=parameters, fun=math.log(2), jac=np.zeros(15))
                with patch.object(ablation, "minimize", return_value=fake):
                    with self.assertRaises(ablation.GateFitError) as raised:
                        ablation.fit_origin_gate(features, targets, weights, fit_id="failed")
                record = raised.exception.fit_record
                self.assertEqual(record["status"], "failed")
                self.assertEqual(record["arm"], "A")
                self.assertEqual(record["training_arrays"]["features"]["shape"], [8, 14])
                json.dumps(record, allow_nan=False)
                with self.assertRaisesRegex(original.FeatureIntegrityError, "unaccepted"):
                    ablation.score_origin_gate(record, features)

    def test_invalid_targets_weights_identity_and_model_dimensions_are_rejected(self):
        features, targets, weights = fixture()
        for bad_targets in ([0] * 8, [1] * 8, targets[:-1], [None, *targets[1:]], [True, *targets[1:]]):
            with self.subTest(targets=bad_targets):
                with self.assertRaises(original.FeatureIntegrityError):
                    ablation.fit_origin_gate(features, bad_targets, weights, fit_id="bad")
        for bad_weights in ([.25] * 8, [0, *weights[1:]], weights[:-1], [float("nan"), *weights[1:]]):
            with self.assertRaises(original.FeatureIntegrityError):
                ablation.fit_origin_gate(features, targets, bad_weights, fit_id="bad")
        with self.assertRaisesRegex(original.FeatureIntegrityError, "duplicate"):
            ablation.fit_origin_gate([features[0], *features[:-1]], targets, weights, fit_id="bad")
        with self.assertRaisesRegex(original.FeatureIntegrityError, "fit id"):
            ablation.fit_origin_gate(features, targets, weights, fit_id="")
        model = ablation.fit_origin_gate(features, targets, weights, fit_id="valid")
        for field, value in (("arm", "J"), ("feature_names", list(original.FEATURE_NAMES)),
                             ("removed_feature_names", ["native_indicator"]), ("coefficients", [0] * 16),
                             ("intercept", float("inf"))):
            changed = copy.deepcopy(model)
            changed[field] = value
            with self.assertRaises(original.FeatureIntegrityError):
                ablation.score_origin_gate(changed, features)


if __name__ == "__main__":
    unittest.main()
