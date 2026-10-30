"""Focused acceptance-contract checks; only synthetic or bounded captured rows."""
import copy
import json
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from src.ball_tracking import candidate_acceptance_features as gate


def point(key, xy, score, *, origin="native", mass=3, pixels=4, padding=0, **extra):
    return {"row_key": key, "frame_key": "frame", "fit": "base", "cohort": "package",
            "center_xy_px": xy, "logit": score, "native_or_weak": origin,
            "native_score": mass, "component_pixels": pixels, "padding_pixels": padding,
            **extra}


def feature(key, score, **kwargs):
    row = point(key, [0, 0], score, **kwargs)
    return gate.build_feature_row(row, [row])


class CandidateAcceptanceFeatureTests(unittest.TestCase):
    def test_exact_coordinate_self_group_and_near_far_boundary(self):
        probe = point("probe", [4, 0], 5)
        duplicate = point("duplicate", [4.0, 0.0], 99)
        near = point("near", [24, 0], 2)
        same_near = point("near_duplicate", [24.0, 0.0], 3)
        far = point("far", [24.00001, 0], 1)
        row = gate.build_feature_row(probe, [probe, duplicate, near, same_near, far])
        f = row["raw_features"]
        self.assertEqual(f["quality_minus_near_max"], 2)
        self.assertEqual(f["quality_minus_far_max"], 4)
        self.assertEqual(f["log1p_near_count"], math.log(2))
        self.assertEqual(f["log1p_far_count"], math.log(2))
        self.assertEqual(row["pool_provenance"]["excluded_self_row_keys"], ["duplicate", "probe"])
        self.assertEqual(row["pool_provenance"]["distinct_center_count"], 3)
        self.assertEqual(row["M"], 4)
        self.assertIsNone(row["M_fallback_reason"])

    def test_features_are_label_blind_and_unknown_neighbors_remain(self):
        probe = point("p", [0, 0], 3, annotation={"geometry": {"center_xy_px": [900, 900]}},
                      target=1, target_group="positive", game_id="forbidden")
        neighbor = point("u", [50, 0], 8, target=None, target_group="masked_unknown")
        before = gate.build_feature_row(probe, [probe, neighbor])
        changed = copy.deepcopy([probe, neighbor])
        for row in changed:
            row.update(target=0, target_group="certain_hidden", game_id="different",
                       visibility="not_visible", distance_px=99999, rank_margin=-99999)
            row["annotation"] = {"geometry": {"center_xy_px": [0, 0]}}
        after = gate.build_feature_row(changed[0], changed)
        self.assertEqual(before, after)
        self.assertEqual(before["raw_features"]["quality_minus_far_max"], -5)

    def test_stress_is_external_and_does_not_add_itself_to_pool(self):
        main = [point("a", [0, 0], 2), point("b", [40, 0], -1)]
        probe = point("stress", [15, 0], 20, cohort="HOU_stress", pixels=None)
        result = gate.build_feature_row(probe, main)
        self.assertEqual(result["pool_provenance"]["original_candidate_count"], 2)
        self.assertEqual(result["raw_features"]["quality_minus_near_max"], 18)
        self.assertEqual(result["raw_features"]["quality_minus_far_max"], 21)
        self.assertIsNone(result["raw_features"]["log1p_component_pixels"])
        self.assertEqual(result["raw_features"]["component_missing"], 1)
        with self.assertRaisesRegex(gate.FeatureIntegrityError, "external probes"):
            gate.build_feature_row(probe, main + [probe])

    def test_historical_unavailable_differs_from_observed_empty_pool(self):
        row = point("h", [0, 0], -3, cohort="historical", origin="inapplicable_historical",
                    mass=None, pixels=None, padding=64)
        historical = gate.build_feature_row(row, None)
        f = historical["raw_features"]
        self.assertIsNone(f["log1p_near_count"])
        self.assertEqual(f["pool_unavailable"], 1)
        self.assertEqual(f["padding_fraction"], 64/4096)
        self.assertTrue(historical["out_of_fitting_schema"])
        self.assertEqual(historical["M"], -3)
        self.assertEqual(historical["M_fallback_reason"], "pool_unavailable")
        observed = gate.build_feature_row(point("s", [0, 0], -3, cohort="HOU_stress"), [])
        self.assertEqual(observed["raw_features"]["log1p_near_count"], 0)
        self.assertEqual(observed["raw_features"]["pool_unavailable"], 0)
        self.assertEqual(observed["M_fallback_reason"], "no_far_rival")
        with self.assertRaisesRegex(gate.FeatureIntegrityError, "historical"):
            gate.build_feature_row(row, [])

    def test_missing_image_is_no_vector_or_zero_reference(self):
        missing = point("missing", None, None, cohort="HOU_stress", origin="inapplicable_missing",
                        mass=None, pixels=None, padding=None)
        row = gate.build_feature_row(missing, [])
        self.assertEqual(row["status"], "missing_image")
        self.assertIsNone(row["raw_features"])
        self.assertIsNone(row["values"])
        self.assertIsNone(row["Q"])
        self.assertIsNone(row["M"])
        zero = feature("zero", 0)
        self.assertEqual(zero["Q"], 0)
        self.assertEqual(zero["status"], "observed")

    def test_observable_fields_and_same_frame_scorer_are_checked(self):
        row = point("p", [0, 0], 1)
        for override in ({"logit": float("nan")}, {"native_score": -1}, {"component_pixels": True},
                         {"padding_pixels": 4097}, {"center_xy_px": None}, {"native_or_weak": "mystery"}):
            with self.subTest(override=override), self.assertRaises(gate.FeatureIntegrityError):
                gate.build_feature_row({**row, **override}, [])
        for key in ("fit", "frame_key"):
            with self.assertRaisesRegex(gate.FeatureIntegrityError, "differs"):
                gate.build_feature_row(row, [{**row, "row_key": "other", key: "wrong"}])
        with self.assertRaisesRegex(gate.FeatureIntegrityError, "duplicate"):
            gate.build_feature_row(row, [row, row])
        with self.assertRaisesRegex(gate.FeatureIntegrityError, "missing declared"):
            gate.build_feature_rows([row], {})

    def test_actual_captured_producer_schema_uses_source_not_annotation(self):
        path = Path(__file__).parent / "fixtures/saved_score_failure_data.json"
        fixture = json.loads(path.read_text(encoding="utf-8"))
        candidate = fixture["package_candidates"][0]
        producer = candidate["producer_candidate"]
        probe = point("captured", candidate["center_xy_px"], 1,
                      origin=candidate["native_or_weak"], mass=producer["native_score"],
                      pixels=producer["component_pixels"])
        del probe["center_xy_px"]
        probe["source"] = {"candidate": candidate}
        probe["annotation"] = {"geometry": {"center_xy_px": [-999, -999]}}
        result = gate.build_feature_row(probe, [probe])
        self.assertEqual(result["raw_features"]["log1p_response_mass"], math.log1p(producer["native_score"]))
        self.assertEqual(result["pool_provenance"]["excluded_self_row_keys"], ["captured"])
        query_probe = {**probe, "source": {"query": {"center_xy_px": candidate["center_xy_px"]}}}
        self.assertEqual(gate.source_center(probe), gate.source_center(query_probe))

    def test_weighted_scaler_missingness_flags_and_degeneracies(self):
        rows = [feature("a", -2, mass=0, pixels=None, padding=64),
                feature("b", 2, mass=3, pixels=None, padding=64),
                feature("c", 4, mass=None, pixels=None, padding=64)]
        scaler = gate.fit_standardizer(rows, [.2, .3, .5])
        names = scaler["feature_names"]
        self.assertAlmostEqual(scaler["means"][names.index("quality_logit")], 2.2)
        self.assertAlmostEqual(scaler["means"][names.index("log1p_response_mass")], .6 * math.log(4))
        details = {d["feature"]: d for d in scaler["details"]}
        self.assertEqual(details["log1p_component_pixels"]["degeneracy"], "all_missing")
        self.assertEqual(details["padding_fraction"]["degeneracy"], "zero_variance")
        matrix = gate.transform_features(rows, scaler)
        self.assertEqual(matrix[2, names.index("log1p_response_mass")], 0)
        self.assertEqual(matrix[2, names.index("response_missing")], 1)
        self.assertEqual(matrix[0, names.index("response_missing")], 0)
        self.assertTrue(np.all(matrix[:, names.index("log1p_component_pixels")] == 0))
        self.assertTrue(np.all(matrix[:, names.index("component_missing")] == 1))
        self.assertTrue(np.all(matrix[:, names.index("padding_fraction")] == 0))

    def test_evaluation_transform_cannot_refit_or_change_standardizer(self):
        rows = [feature("a", -1), feature("b", 1)]
        scaler = gate.fit_standardizer(rows, [.5, .5], ["quality_logit"])
        saved = copy.deepcopy(scaler)
        prediction = gate.transform_features([feature("held", 1000)], scaler)
        self.assertEqual(prediction[0, 0], 1000)
        self.assertEqual(scaler, saved)
        self.assertEqual(scaler["means"], [0.0])
        with self.assertRaises(gate.FeatureIntegrityError):
            gate.fit_standardizer(rows, [.5, .4])

    def test_analytic_gradient_and_unpenalized_intercept(self):
        matrix = np.array([[-2, 1], [1, -3], [2, 2]], dtype=np.float64)
        target = np.array([0, 1, 1], dtype=np.float64)
        weights = np.array([.2, .3, .5], dtype=np.float64)
        theta = np.array([.7, -.3, .2], dtype=np.float64)
        loss, gradient = gate._objective(theta, matrix, target, weights)
        numerical = []
        for i in range(3):
            delta = np.zeros(3); delta[i] = 1e-6
            numerical.append((gate._objective(theta+delta, matrix, target, weights)[0]
                              - gate._objective(theta-delta, matrix, target, weights)[0]) / 2e-6)
        np.testing.assert_allclose(gradient, numerical, rtol=1e-7, atol=1e-9)
        self.assertTrue(math.isfinite(loss))
        extreme_loss, extreme_grad = gate._objective(np.array([1000.0, 0, 0]), matrix, target, weights)
        self.assertTrue(math.isfinite(extreme_loss))
        self.assertTrue(np.all(np.isfinite(extreme_grad)))

    def test_score_only_nonnegative_constraint_and_constant_degeneracy(self):
        rows = [feature(str(i), q) for i, q in enumerate((-2, -1, 1, 2))]
        model = gate.fit_gate(rows, [1, 1, 0, 0], [.25]*4, arm="S", fit_id="synthetic_inverse")
        self.assertEqual(model["coefficients"], [0.0])
        self.assertTrue(model["constant_score_degeneracy"])
        scores = gate.score_gate(model, rows)
        self.assertEqual(len(set(scores)), 1)
        self.assertEqual(model["solver"]["projected_gradient_inf_norm"], 0)
        forward = gate.fit_gate(rows, [0, 0, 1, 1], [.25]*4, arm="S", fit_id="synthetic_forward")
        self.assertGreater(forward["coefficients"][0], 0)
        self.assertEqual(gate.score_gate(forward, rows), sorted(gate.score_gate(forward, rows)))

    def test_joint_fit_roundtrips_and_preserves_missing_prediction_slots(self):
        rows = [feature("a", -2, mass=0), feature("b", -1, mass=1),
                feature("c", 1, mass=5, origin="weak"), feature("d", 2, mass=7, origin="weak")]
        model = gate.fit_gate(rows, [0, 0, 1, 1], [.25]*4, arm="J", fit_id="synthetic_joint")
        restored = json.loads(json.dumps(model, allow_nan=False))
        self.assertEqual(restored["feature_names"], list(gate.FEATURE_NAMES))
        self.assertEqual(restored["training_arrays"]["features"]["shape"], [4, 16])
        missing = gate.build_feature_row(point("m", None, None, mass=None, pixels=None, padding=None), [])
        scores = gate.score_gate(restored, [rows[0], missing, rows[-1]])
        self.assertLess(scores[0], 0)
        self.assertIsNone(scores[1])
        self.assertGreater(scores[2], 0)
        self.assertEqual(gate.score_gate(restored, []), [])

    def test_unknown_targets_duplicates_or_solver_failure_are_not_accepted(self):
        rows = [feature("a", -1), feature("b", 1)]
        with self.assertRaises(gate.FeatureIntegrityError):
            gate.fit_gate(rows, [None, 1], [.5, .5], arm="S", fit_id="bad")
        with self.assertRaises(gate.FeatureIntegrityError):
            gate.fit_gate([rows[0], rows[0]], [0, 1], [.5, .5], arm="S", fit_id="bad")
        failed = SimpleNamespace(x=np.array([0.0, 0.0]), fun=math.log(2), jac=np.array([0.0, -.5]),
                                 success=False, status=1, message="synthetic failure", nit=1, nfev=2)
        with patch.object(gate, "minimize", return_value=failed):
            with self.assertRaises(gate.GateFitError) as error:
                gate.fit_gate(rows, [0, 1], [.5, .5], arm="S", fit_id="failed_attempt")
        self.assertEqual(error.exception.fit_record["status"], "failed")
        self.assertEqual(error.exception.fit_record["solver"]["message"], "synthetic failure")
        with self.assertRaises(gate.FeatureIntegrityError):
            gate.score_gate(error.exception.fit_record, rows)


if __name__ == "__main__":
    unittest.main()
