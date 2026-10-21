"""Fixed head math, actual reference transport, alias weights and failure semantics."""
import copy
import json
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import warnings

import numpy as np

from src.ball_tracking import nba_ball_distractor_classifier as classifier

REPOSITORY = Path(__file__).resolve().parents[1]
CAPTURED = REPOSITORY/"data/outputs/ball_tracking/nba/ball_distractor_verifier_v0_1/reference"


def row(rid, frame, classification, block, *, obj=None, center=None, origin="saved_detector_candidate", role="fit"):
    return {"row_id":rid,"continuous_source_id":"source", "source_frame_index":frame,"center_xy_px":center or [10.2,20.4],
        "classification":classification,"subtype":"head" if classification == "other_object" else None,
        "block_id":block,"physical_object_instance_id":obj or rid,"episode_id":block+":episode",
        "origin":origin,"role":role,"duplicate_of_row_id":None}


def weight_rows():
    rows = [row("a0",1,"ball","pA",obj="a"),row("a1",1,"ball","pA",obj="a",center=[10.8,20.9]),
        row("a2",1,"ball","pA",obj="a",center=[12.2,20.4]),row("b",2,"ball","pA"),row("c",3,"ball","pB"),
        row("d",4,"other_object","nA"),row("e",5,"other_object","nB"),row("f",6,"other_object","nB"),
        row("g",7,"other_object","aA",origin="source_authored_contrast"),row("h",8,"other_object","aB",origin="source_authored_contrast")]
    duplicate = row("duplicate",4,"other_object","nA",obj="d",center=[30.,30.],origin="source_authored_contrast")
    duplicate["duplicate_of_row_id"] = "d"; rows.append(duplicate)
    rows.append(row("unknown",9,"unresolved","nA"))
    # No class/center required for an excluded row: those labels cannot influence weights.
    rows.append({"row_id":"check","role":"check"})
    return rows


def synthetic_arrays():
    x = np.zeros((4,384),np.float64); x[:2,0] = 1.; x[2:,0] = -1.
    return x,np.array([1.,1.,0.,0.]),np.full(4,.25)


class BallDistractorClassifierTests(unittest.TestCase):
    def test_three_pool_weights_equal_blocks_objects_and_distinct_crops(self):
        result = classifier.build_weights(weight_rows())
        self.assertEqual(result["pool_group_counts"],{"ball":3,"authored_other":2,"detector_other":3})
        self.assertEqual(result["pool_masses"],{"ball":.5,"authored_other":.2,"detector_other":.3})
        samples = {s["representative_row_id"]:s for s in result["samples"]}
        self.assertEqual(len(samples),9)
        self.assertEqual(samples["a0"]["row_ids"],["a0","a1"])
        self.assertAlmostEqual(samples["a0"]["weight"],.0625)
        self.assertAlmostEqual(samples["a0"]["alias_weight_each"],.03125)
        for rid,expected in {"a2":.0625,"b":.125,"c":.25,"d":.15,"e":.075,"f":.075,"g":.1,"h":.1}.items():
            self.assertAlmostEqual(samples[rid]["weight"],expected)
        self.assertEqual({r["row_id"]:r["reason"] for r in result["excluded_rows"]},
            {"unknown":"unresolved","check":"excluded_check","duplicate":"supplemental_same_object_duplicate"})
        self.assertAlmostEqual(math.fsum(s["weight"] for s in result["samples"]),1.)
        more_alias = weight_rows(); more_alias.append({**more_alias[0],"row_id":"a3"})
        augmented = classifier.build_weights(more_alias)
        self.assertEqual([s["weight"] for s in augmented["samples"]],[s["weight"] for s in result["samples"]])
        self.assertEqual(augmented["pool_group_counts"],result["pool_group_counts"])
        self.assertAlmostEqual(augmented["samples"][0]["alias_weight_each"],.0625/3)
        no_authored = [r for r in weight_rows() if r.get("origin") != "source_authored_contrast"]
        self.assertEqual(classifier.build_weights(no_authored)["pool_masses"],{"ball":.5,"authored_other":0.,"detector_other":.5})
        many_authored = weight_rows()+[row(f"authored{i}",20+i,"other_object","aA",origin="source_authored_contrast") for i in range(5)]
        self.assertEqual(classifier.build_weights(many_authored)["pool_masses"]["authored_other"],.25)

    def test_bad_grouping_duplicate_and_missing_real_negative_pool_rejected(self):
        for case in ("class","episode","crop","duplicate","missing_detector"):
            rows = weight_rows()
            if case == "class": rows[1].update(classification="other_object",subtype="head")
            elif case == "episode": rows[1]["episode_id"] = "different"
            elif case == "crop": rows[1]["physical_object_instance_id"] = "different"
            elif case == "duplicate": rows[10]["duplicate_of_row_id"] = "e"
            else: rows = [r for r in rows if r.get("classification") != "other_object" or r.get("origin") == "source_authored_contrast" and r["row_id"] != "duplicate"]
            with self.subTest(case=case),self.assertRaises(ValueError):
                classifier.build_weights(rows)

    @unittest.skipUnless((CAPTURED/"preparation.json").is_file() and (CAPTURED/"annotations/proposal.json").is_file(),"Ignored authorized captured reference unavailable")
    def test_actual_producer_reference_transport_old_labels_aliases_and_group_census(self):
        prep = json.loads((CAPTURED/"preparation.json").read_text())
        proposal = json.loads((CAPTURED/"annotations/proposal.json").read_text())
        rows = classifier.reference_rows(prep,proposal)
        self.assertEqual(rows[:len(proposal["rows"])],proposal["rows"])
        for row_,control in zip(rows[len(proposal["rows"]):],prep["reused_controls"],strict=True):
            self.assertEqual(row_["classification"],control["accepted_row"]["classification"])
            self.assertEqual(row_["center_xy_px"],control["accepted_candidate"]["center_xy_px"])
            self.assertEqual(row_["block_id"],control["historical_block"]["block_id"])
        weights = classifier.build_weights(rows)
        expected = {(g["continuous_source_id"],g["source_frame_index"],g["physical_object_instance_id"]) for g in proposal["physical_groups"] if g["role"] == "fit"}
        self.assertEqual({tuple(g["group_key"]) for g in weights["groups"]},expected)
        used = {rid for s in weights["samples"] for rid in s["row_ids"]}
        for source_row in rows:
            if source_row["role"] != "fit" or source_row["classification"] == "unresolved":
                self.assertNotIn(source_row["row_id"],used)
        self.assertAlmostEqual(weights["weight_sum"],1.)

    def test_every_analytic_gradient_coordinate_matches_finite_difference(self):
        rng = np.random.default_rng(193)
        x = rng.normal(size=(8,384)); x /= np.linalg.norm(x,axis=1)[:,None]
        y = np.array([1,1,1,1,0,0,0,0],np.float64)
        q = np.array([.05,.1,.15,.2,.125,.125,.125,.125])
        theta = rng.normal(scale=.13,size=385)
        value,gradient = classifier.objective(theta,x,y,q)
        numerical = np.empty(385); step = 1e-6
        for j in range(385):
            left,right = theta.copy(),theta.copy(); left[j] -= step; right[j] += step
            numerical[j] = (classifier.objective(right,x,y,q)[0]-classifier.objective(left,x,y,q)[0])/(2*step)
        np.testing.assert_allclose(gradient,numerical,rtol=0.,atol=2e-9)
        self.assertTrue(math.isfinite(value))
        zero = np.zeros(385)
        self.assertAlmostEqual(classifier.objective(zero,x,y,q)[0],math.log(2.))
        zero[-1] = 1000.
        extreme,grad = classifier.objective(zero,x,y,q)
        self.assertAlmostEqual(extreme,500.)  # bias has no quadratic penalty
        self.assertAlmostEqual(grad[-1],.5)

    def test_one_fixed_synthetic_fit_and_prediction_zero_boundary(self):
        # This is a four-vector numerical unit fixture, never project descriptors.
        x,y,q = synthetic_arrays()
        fitted = classifier.fit_matrix(x,y,q)
        self.assertEqual(fitted["status"],"converged_fit")
        self.assertEqual(fitted["optimizer_calls"],1)
        self.assertEqual(fitted["options"],{"maxiter":500,"maxfun":2000,"maxcor":10,"maxls":40,"ftol":1e-12,"gtol":1e-8})
        self.assertLess(fitted["objective"],math.log(2.))
        self.assertAlmostEqual(fitted["parameters"][-1],0.,places=12)
        np.testing.assert_allclose(fitted["parameters"][1:-1],0.,rtol=0.,atol=0.)
        scores = classifier.score({"positive":x[0].astype(np.float32)*7,"negative":x[-1]},fitted)
        self.assertEqual(classifier.decision(scores["positive"]),"ball_supported")
        self.assertEqual(classifier.decision(scores["negative"]),"other_supported")
        self.assertEqual(classifier.decision(0.),"abstain")
        self.assertEqual(classifier.decision(-0.),"abstain")
        self.assertEqual(classifier.decision(np.nextafter(0.,1.)),"ball_supported")
        self.assertEqual(classifier.score_feature(np.zeros(385),x[0]),0.)
        for bad in (float("nan"),float("inf"),-float("inf")):
            with self.assertRaises(ValueError): classifier.decision(bad)
        with self.assertRaises(ValueError): classifier.normalize_feature(np.zeros(384))

    def test_optimizer_warnings_failures_and_nonfinite_input_are_preserved_without_retry(self):
        x,y,q = synthetic_arrays()
        def failed(fun,initial,**kwargs):
            self.assertEqual(initial.dtype,np.float64); self.assertFalse(initial.any())
            self.assertIs(kwargs["jac"],True); self.assertEqual(kwargs["method"],"L-BFGS-B")
            self.assertEqual(kwargs["options"],classifier.OPTIONS)
            warnings.warn("synthetic convergence warning",RuntimeWarning)
            return SimpleNamespace(x=initial,success=False,status=1,message="iteration limit",nit=500,nfev=501,njev=501,fun=math.log(2.))
        with patch.object(classifier,"minimize",side_effect=failed) as optimizer:
            result = classifier.fit_matrix(x,y,q)
            self.assertEqual(optimizer.call_count,1)
        self.assertEqual(result["reason"],"optimizer_nonconvergence")
        self.assertIsNone(result["parameters"])
        self.assertEqual(len(result["final_parameters"]),385)
        self.assertEqual(result["optimizer_warnings"],[{"category":"RuntimeWarning","message":"synthetic convergence warning"}])
        with self.assertRaisesRegex(ValueError,"invalid fit"):
            classifier.score({"any":x[0]},result)
        with patch.object(classifier,"minimize",side_effect=AssertionError("must not optimize")) as optimizer:
            x[0,0] = np.nan
            invalid = classifier.fit_matrix(x,y,q)
            optimizer.assert_not_called()
        self.assertEqual((invalid["status"],invalid["reason"],invalid["optimizer_calls"]),("invalid_fit","invalid_input",0))

    def test_fit_reads_only_distinct_fit_crops_and_rejects_inconsistent_alias_features(self):
        weights = classifier.build_weights(weight_rows())
        feature = np.zeros(384,np.float32); feature[0] = 2.
        features = {s["representative_row_id"]:feature.copy() for s in weights["samples"]}
        features.update({"check":np.full(384,np.nan),"unknown":np.full(384,np.nan),"duplicate":np.full(384,np.nan)})
        with patch.object(classifier,"fit_matrix",return_value={"status":"test-only"}) as fitting:
            self.assertEqual(classifier.fit(features,weights),{"status":"test-only"})
            matrix,y,q = fitting.call_args.args
            self.assertEqual(len(matrix),9)
            self.assertTrue(all(v.dtype == np.float64 and np.linalg.norm(v) == 1 for v in matrix))
            self.assertAlmostEqual(math.fsum(q),1.)
        features["a1"] = -feature
        with patch.object(classifier,"fit_matrix") as fitting:
            result = classifier.fit(features,weights)
            fitting.assert_not_called()
        self.assertEqual(result["reason"],"invalid_input")
        self.assertIn("alias features",result["error"])


if __name__ == "__main__":
    unittest.main()
