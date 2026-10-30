"""Synthetic-only consumer and diagnostic semantics; no local study outcomes."""
from copy import deepcopy
import hashlib
import unittest

import numpy as np

from src.ball_tracking import candidate_response_analysis as analysis
from src.ball_tracking.candidate_response_study import describe_frame
from src.ball_tracking.weak_response_followup import narrow_pool
from src.ball_tracking.weak_response_candidates import components


def candidate(score, *, match=True, native=True, selected=False, mass=None):
    return {"id":0,"native":native,"mass":score if mass is None else mass,"in_bounds":True,"match":match,
            "is_native_selected":selected,"features":{name:score for name in analysis.FEATURE_NAMES}}


def frame(candidates, *, category="eligible", native_correct=False, index=1, stress_score=None):
    return {"block_id":"synthetic","frame":index,"reference_category":category,"native_correct":native_correct,
            "candidates":candidates,"stress":{"emitted":stress_score is not None,
                "features":{name:stress_score for name in analysis.FEATURE_NAMES},"tags":["all_emitted","known_gain"]}}


class ResponseAnalysisTests(unittest.TestCase):
    def test_exact_ties_and_unknown_competitors_remain_explicit(self):
        row=frame([candidate(2),candidate(3,match=False),candidate(2,match=False),candidate(None,match=False,mass=1)])
        result=analysis.rank_frame(row,"peak")
        self.assertEqual(result["localization_misses_strictly_above"],1)
        self.assertEqual(result["localization_misses_tied"],1)
        self.assertEqual(result["best_rank_among_available_features"],2)
        self.assertEqual(result["worst_rank_after_miss_ties"],3)
        self.assertEqual(result["unknown_miss_candidates"],1)
        self.assertFalse(result["complete_feature_ranking"])

    def test_unknown_miss_cannot_manufacture_paired_gain(self):
        row=frame([candidate(2),candidate(3,match=False)])
        baseline=analysis.rank_frame(row,"peak")
        row["candidates"][1]["features"]["isotropy"]=None
        apparent=analysis.rank_frame(row,"isotropy")
        self.assertEqual(apparent["status_among_available_features"],"strict_first")
        self.assertEqual(analysis.compare_ranks([apparent],[baseline]),{"not_comparable_incomplete_features":1})

    def test_mass_baseline_never_compares_other_threshold_components(self):
        row=frame([candidate(2,selected=True),candidate(3,match=False,native=False,mass=999)])
        self.assertEqual(analysis.rank_frame(row,"native_mass")["candidate_count"],1)
        self.assertEqual(analysis.rank_frame(row,"peak")["status_among_available_features"],"beaten")
        self.assertEqual(analysis.rank_frame(row,"peak",native_only=True)["status_among_available_features"],"strict_first")

    def test_shared_bounds_strict_inclusive_unknown_and_stress(self):
        rows=[frame([candidate(2,selected=True),candidate(None,native=False,mass=.1)],native_correct=True,stress_score=2),
              frame([candidate(1,selected=True)],native_correct=True,index=2,stress_score=.5),
              frame([candidate(1,match=False),candidate(None,match=False,native=False,mass=.1)],category="certain_hidden",index=3)]
        thresholds=analysis.thresholds(rows,"peak")
        self.assertEqual(thresholds["maximum_observed_certain_hidden"],1)
        self.assertEqual(thresholds["minimum_observed_native_correct"],1)
        self.assertEqual(thresholds["hidden_feature_unknown"],1)
        self.assertFalse(thresholds["zero_hidden_claim_possible_from_available_features"])
        strict=analysis.evaluate_bound(rows,"peak",1,strict=True)
        self.assertEqual(strict["original_native_correct_points"],{"retained":1,"rejected":1})
        self.assertEqual(strict["certain_hidden"]["candidates_unknown"],1)
        self.assertEqual(strict["certain_hidden"]["candidates_rejected"],1)
        inclusive=analysis.evaluate_bound(rows,"peak",1,strict=False)
        self.assertEqual(inclusive["original_native_correct_points"],{"retained":2})
        self.assertEqual(inclusive["certain_hidden"]["candidates_retained"],1)
        self.assertEqual(inclusive["original_expanded_weak_stress"]["known_gain:rejected"],1)

    def test_unscored_contexts_never_enter_visibility_thresholds(self):
        rows=[frame([candidate(1,selected=True)],native_correct=True),
              frame([candidate(1000,match=False)],category="uncertain_hidden"),
              frame([candidate(3,match=False)],category="certain_hidden")]
        self.assertEqual(analysis.thresholds(rows,"peak")["maximum_observed_certain_hidden"],3)
        unknown=[frame([candidate(None,selected=True,mass=1)],native_correct=True)]
        self.assertIsNone(analysis.thresholds(unknown,"peak")["minimum_observed_native_correct"])
        self.assertFalse(analysis.thresholds(unknown,"peak")["all_native_correct_retention_claim_possible"])

    def test_actual_synthetic_producer_join_and_independent_geometry(self):
        mean=np.zeros((36,64),np.float32); mean[18,32]=.8
        old=[{"candidate_index":i,**c} for i,c in enumerate(components(mean,64,36,.3))]
        pool,_=narrow_pool(mean,old,64,36)
        native={"source_frame_index":10,"source_pts_ticks":1000,"time_base":"1/60000",
            "mean_heatmap_sha256":hashlib.sha256(mean.tobytes()).hexdigest(),"source_png":{"path":"synthetic.png","sha256":"a"*64},
            "temporal_contributions":3,"selected_candidate_index":0,"center_xy_px":[old[0]["center_x"],old[0]["center_y"]],
            "native_score":old[0]["native_score"],"candidates":old,"state":"observed"}
        stress={k:deepcopy(v) for k,v in native.items() if k!="candidates"}; stress["candidate_pool_count"]=len(pool)
        producer={"block_id":"synthetic",**{k:native[k] for k in analysis.PROVENANCE_FIELDS},
                  "width_px":64,"height_px":36,"candidates":pool}
        emitted=describe_frame(mean,native,producer,stress)
        annotation={"frame_index":10,"annotation_status":"labeled","visibility":"fully_visible","absence_reason":None,
            "game_ball_identity_certainty":"certain","geometry":{"center_xy_px":[42,18],"source":"observed_complete_ball_center",
            "uncertainty_radius_px":2},"localization_eligible":True,"difficulty_tags":[],"notes":"Synthetic only."}
        frm={"source_frame_index":10,"source_pts_ticks":1000,"png":native["source_png"],"annotation":annotation,"state":"permitted"}
        block={"block_id":"synthetic","time_base":"1/60000","source_video":{"width_px":64,"height_px":36}}
        joined=analysis.join_frame(emitted,frm,native,block,stress)
        self.assertTrue(joined["native_correct"])
        self.assertTrue(joined["candidates"][0]["match"])
        frm["annotation"]["geometry"]["center_xy_px"][0]=42.0001
        self.assertFalse(analysis.join_frame(emitted,frm,native,block,stress)["candidates"][0]["match"])
        changed=deepcopy(emitted); changed["source_pts_ticks"]+=1
        with self.assertRaises(ValueError): analysis.join_frame(changed,frm,native,block,stress)
        changed=deepcopy(emitted); changed["expanded_weak_selection"]["observation"]["native_score"]+=1
        with self.assertRaises(ValueError): analysis.join_frame(changed,frm,native,block,stress)


if __name__=="__main__":
    unittest.main()
