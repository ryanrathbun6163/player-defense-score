"""Fixed veto and evaluation transport from actual synthetic-map producers.

No source pixels, neural inference, or production policy execution occurs here.
"""
import copy
from pathlib import Path
import tempfile
import unittest

import numpy as np

from src.ball_tracking import nba_ball_distractor_policy as policy
from src.ball_tracking import nba_temporal_gap_continuous as continuous
from src.ball_tracking import nba_action_observation as action
from src.ball_tracking import nba_wasb_diagnostic as d
from src.ball_tracking import wasb_development_observation as nfhs
from tests.test_nba_temporal_gap_continuous import produced_context, resources
from tests.test_nba_hard_example_diagnostic import label


def produced_selection(root):
    context, arrays, _, reader = produced_context(root, count=8)
    for values in arrays.values(): values.fill(0)
    anchors = {1,4,6}
    for index in range(1,7):
        starts = continuous.saved.needed_starts([index],[0,7])
        for start in starts:
            if index in anchors or start == starts[0]:
                arrays[start][index-start,50,49+index] = .8 if index in anchors else .6
    context["observations"] = []
    for frame in context["frames"]:
        index = frame["source_frame_index"]
        starts = continuous.saved.needed_starts([index],[0,7])
        mean = continuous.metrics.reconstruct_mean([(s,arrays[s][index-s]) for s in starts])
        context["observations"].append(action.select_observation(frame,mean,len(starts),context["manifest"],
            {"kind":"development","source_frame_range_inclusive":[0,7]}))
    segment = continuous.select_segment(root,context,resources(),cache_reader=reader)
    source = {**context["source"],"segments":[segment],"frames":segment["frames"]}
    return {"schema_version":continuous.SCHEMA,"sources":[source],"windows":[segment],"frames":segment["frames"]}


def positive_scores(selection):
    return {policy.emission_key(*policy.key(r)):1.0 for r in selection["frames"] if r["selected_center_xy_px"] is not None}


def reference(selection,index,*,gap=False,target=None,unknown=False,hidden=False,control=False):
    saved = selection["frames"][index]
    annotation = label(index,target or saved["selected_center_xy_px"] or [49+index,50],uncertainty=20)
    if unknown or hidden:
        annotation.update(visibility="not_visible" if hidden else "indeterminate",absence_reason="occluded" if hidden else None,
                          game_ball_identity_certainty="certain" if hidden else "ambiguous",geometry=None,localization_eligible=False)
    row = {"candidate_id":"synthetic","continuous_source_id":"synthetic","source_frame_index":index,
        "source_frame":saved["source_frame"],"source_video":saved["source_video"],"annotation":annotation,
        "cohort":"pilot_control" if control else "synthetic","is_control":control,
        "exact_saved_decision" if gap else "decision":copy.deepcopy(saved)}
    scoring = {**row,"old":{"pool":{"contributor_planes":[None]*saved["original_observation"]["temporal_contributions"]}}}
    components = [r["component"] for r in saved["candidate_pool"]["records"]]
    row["selected"] = policy.geometry.score_point(scoring,saved["selected_center_xy_px"],components)
    return row


def evaluation_inputs(selection):
    old = {"frames":[reference(selection,1,control=True),reference(selection,2),
        reference(selection,4,target=[63,50]),reference(selection,5,unknown=True),reference(selection,6,hidden=True)]}
    gap = {"metric":{"raw_match_radius_px":10,"boundary":"inclusive"},
           "new_frames":[reference(selection,2,gap=True),reference(selection,3,gap=True)],
           "reused_controls":[reference(selection,4,gap=True)]}
    gates = {"localization_radius_px_inclusive":10,"old790_exact_match_retention":{"synthetic":3},
        "new_eligible_match_retention":2,"prior_gains_exact":["synthetic:2"],"nba_easy_controls_match_each":1,
        "exposed_head_episode_suppress":["synthetic:6"],"exposed_near_head_ball_retain":["synthetic:1"]}
    return old,gap,gates


def produced_nfhs(root):
    (root/"source.mp4").write_bytes(b"synthetic-source-binding-only")
    source_binding = d.binding(root,root/"source.mp4")
    video = {"path":"source.mp4","sha256":source_binding["sha256"],"width_px":512,"height_px":288,"fps":25.0,"frame_count":7}
    possession = {"possession_id":"synthetic_nfhs","source_video":video,"visible_segments":[[0,2],[4,6]],"protected_ranges":[[3,3]]}
    identity = {"weights":{"sha256":d.EXPANDED_SHA},"source_video":video}
    produced,segments = [],[]
    for lo,hi in possession["visible_segments"]:
        means = np.zeros((3,288,512),np.float32)
        result = {"segment":[lo,hi],"identity":identity,"frames":nfhs.observed_frames(means,[1,1,1],lo,video,.3),
            "triplets":[{"input_frame_indices":[lo,lo+1,hi],"cache":{"path":"never-opened.npz"}}]}
        produced.append(result); path = root/f"segment_{lo}.json"; d.write_once(path,result)
        segments.append({"segment_id":f"synthetic_nfhs:{lo}-{hi}","range_inclusive":[lo,hi],"observations":d.binding(root,path)})
    d.write_once(root/"timeline.json",{"source_video":video,"protected_ranges":[[3,3]],"frames":nfhs.make_timeline(possession,produced,[])})
    d.write_once(root/"packets.json",{"streams":[{"width":512,"height":288,"nb_frames":"7","time_base":"1/12800"}],
                                    "packets":[{"pts":(i+1)*512,"duration":512} for i in range(7)]})
    timing = {"schema_version":"nfhs_container_native_timestamps/v0.1","status":"verified","candidate_id":"synthetic_nfhs",
        "actual_source_binding":source_binding,"packet_probe":d.binding(root,root/"packets.json"),"original_time_base":"1/12800",
        "source_end_exclusive_pts_ticks":7*3600,"container_end_exclusive_pts_ticks":8*3600,"time_base":"1/90000",
        "time_origin":"clip_first_frame","source_video":video,"container_time_origin_ticks":3600,
        "frames":[{"source_frame_index":i,"source_pts_ticks":i*3600,"container_pts_ticks":(i+1)*3600,"duration_ticks":3600} for i in range(7)]}
    d.write_once(root/"timing.json",timing)
    source = {"candidate_id":"synthetic_nfhs","kind":"nfhs","source_video":video,"possession":possession,
        "analysis_group":"nfhs_development","source_end_exclusive_pts_ticks":7*3600,"protected_ranges":[[3,3]],"segments":segments,
        "timeline_observations":d.binding(root,root/"timeline.json"),"native_timestamps":d.binding(root,root/"timing.json")}
    return continuous.select_sources(root,{"sources":[source],"totals":{"processed_frames":6,"segments":2,"timeline_frames":7}},resources())


class BallDistractorPolicyTests(unittest.TestCase):
    def test_actual_multi_fill_producer_whole_gap_veto_and_exact_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            selection = produced_selection(Path(folder)); before = copy.deepcopy(selection)
            self.assertEqual([r["decision"] for r in selection["frames"]],
                ["abstained","preserved_original","filled_saved_candidate","filled_saved_candidate","preserved_original","filled_saved_candidate","preserved_original","abstained"])
            scores = positive_scores(selection); scores["emission:synthetic:2"] = -1
            output = policy.apply(selection,scores)
            self.assertEqual([r["source_frame_index"] for r in output["frames"] if r["removed"]],[2,3])
            self.assertTrue(output["frames"][3]["removed_only_by_gap_dependency"])
            self.assertEqual(output["frames"][5]["selected_provenance_id"],selection["frames"][5]["selected_provenance_id"])
            scores = positive_scores(selection); scores["emission:synthetic:4"] = 0
            output = policy.apply(selection,scores)
            self.assertEqual(output["frames"][4]["policy_decision"],"retained_original")
            self.assertEqual([r["source_frame_index"] for r in output["frames"] if r["removed"]],[2,3,5])
            scores["emission:synthetic:4"] = -1
            output = policy.apply(selection,scores)
            self.assertEqual([r["source_frame_index"] for r in output["frames"] if r["removed"]],[2,3,4,5])
            self.assertEqual(output["new_fills"],0)
            self.assertEqual(selection,before)

    def test_score_census_nonfinite_and_record_transport_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            selection = produced_selection(Path(folder)); scores = positive_scores(selection)
            for changed in ({**scores,"emission:synthetic:0":1},{k:v for k,v in scores.items() if k != "emission:synthetic:2"},
                            {**scores,"emission:synthetic:2":float("nan")},{**scores,("synthetic",2):1},
                            {**scores,"emission:synthetic:2":True}):
                with self.subTest(scores=changed),self.assertRaises(ValueError): policy.apply(selection,changed)
            bad = copy.deepcopy(selection); bad["frames"] = copy.deepcopy(bad["frames"]); bad["frames"][1]["selected_center_xy_px"][0] += 1
            with self.assertRaisesRegex(ValueError,"Top-level frames"): policy.apply(bad,scores)
            bad = copy.deepcopy(selection); bad["sources"][0]["frames"][1]["selected_provenance_id"] = ["wrong"]
            with self.assertRaisesRegex(ValueError,"provenance"): policy.apply(bad,scores)

    def test_nfhs_protected_native_origin_and_segment_final_hold(self):
        with tempfile.TemporaryDirectory() as folder:
            selection = produced_nfhs(Path(folder)); output = policy.apply(selection,{})
            self.assertEqual(output["summary"]["protected_frames"],1)
            self.assertEqual(output["sources"][0]["frames"][3]["container_pts_ticks"],14400)
            intervals = [r for r in output["missing_intervals"] if r["arm"] == "policy"]
            self.assertEqual([r["intervals"][0]["source_frame_range_inclusive"] for r in intervals],[[0,2],[4,6]])
            self.assertEqual([r["intervals"][0]["duration_ticks"] for r in intervals],[10800,10800])
            self.assertEqual(intervals[-1]["intervals"][0]["end_exclusive_pts_ticks"],25200)
            policy._validate_policy(output,selection)
            with self.assertRaisesRegex(ValueError,"exactly saved emissions"):
                policy.apply(selection,{"emission:synthetic_nfhs:3":1})

    def test_frozen_scores_deduplicated_retention_and_unknown_removals(self):
        with tempfile.TemporaryDirectory() as folder:
            selection = produced_selection(Path(folder)); old,gap,gates = evaluation_inputs(selection)
            self.assertEqual(old["frames"][2]["selected"]["raw_center_error_px"],10)
            self.assertEqual(old["frames"][2]["selected"]["outcome"],"matched")
            scores = positive_scores(selection); scores["emission:synthetic:6"] = -1
            output = policy.apply(selection,scores)
            result = policy.evaluate(output,selection,old,gap,gates=gates,
                prior_object_assessment={"rows":[{"candidate_id":"synthetic","source_frame_index":5,"assessment":"unresolved"}]})
            self.assertEqual(result["protected_union_count"],4)
            self.assertEqual(result["protection_cohorts"]["prior_accepted_gains"]["retained_exact"],1)
            self.assertEqual(len(next(r for r in result["protected_union"] if r["source_frame_index"] == 2)["cohorts"]),3)
            self.assertTrue(result["checks"]["all_protected_points_exact"])
            self.assertEqual(result["old_790_frames"][-1]["after"]["outcome"],"hidden_quiet")
            unknown = next(r for r in result["removals"] if r["source_frame_index"] == 5)
            self.assertIn("geometric_reference_unscored",unknown["unscored_or_unknown_reasons"])
            self.assertIn("prior_qualitative_judgment_unresolved",unknown["unscored_or_unknown_reasons"])
            self.assertFalse(unknown["unknown_removal_counts_as_success"])
            self.assertFalse(result["checks"]["excluded_head_and_clothing_present"])
            scores["emission:synthetic:2"] = -1
            lost = policy.evaluate(policy.apply(selection,scores),selection,old,gap,gates=gates)
            self.assertFalse(lost["checks"]["all_protected_points_exact"])
            self.assertEqual(lost["protection_cohorts"]["additional_eligible_matches"]["retained_exact"],0)
            changed = copy.deepcopy(old); changed["frames"][0]["selected"]["raw_center_error_px"] = 99
            with self.assertRaisesRegex(ValueError,"reproduce exactly"): policy.evaluate(output,selection,changed,gap,gates=gates)

    def test_policy_native_transport_provenance_and_rule_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            selection = produced_selection(Path(folder)); output = policy.apply(selection,positive_scores(selection))
            old,gap,gates = evaluation_inputs(selection)
            for field in ("provenance","native_duration","timeline","rule"):
                bad = copy.deepcopy(output)
                if field == "provenance": bad["frames"][1]["selected_provenance_id"] = ["other"]
                elif field == "native_duration": bad["missing_intervals"][0]["intervals"][0]["duration_ticks"] += 1
                elif field == "timeline": bad["sources"][0]["source_end_exclusive_pts_ticks"] += 1
                else: bad["frames"][1]["logit"] = -1
                with self.subTest(field=field),self.assertRaises(ValueError): policy.evaluate(bad,selection,old,gap,gates=gates)

    def test_physical_object_groups_require_every_distinct_crop_not_alias_votes(self):
        with tempfile.TemporaryDirectory() as folder:
            selection = produced_selection(Path(folder)); output = policy.apply(selection,positive_scores(selection))
            _,indexed,_,_ = policy.index_selection(selection); applied = {policy.key(r):r for r in output["frames"]}
            def case(rid,index,point,classification="ball",subtype=None):
                return {"row_id":rid,"continuous_source_id":"synthetic","source_frame_index":index,"role":"check",
                    "center_xy_px":point,"classification":classification,"subtype":subtype,"origin":"saved_detector_candidate",
                    "block_id":"block","episode_id":"episode","physical_object_instance_id":"one_object"}
            rows = [case("a",1,[50,50]),case("alias",1,[50.5,50.5]),case("othercrop",1,[51,50]),
                    case("unknown",2,[51,50],"unresolved"),case("unselected_head",4,[300,200],"other_object","head")]
            scores = {"a":1,"alias":1,"othercrop":-1,"unknown":-1,"unselected_head":-1}
            result = policy._semantic_report(rows,scores,indexed,applied,"provisional_ai_human_review_pending")
            self.assertEqual(result["check_counts"],{"correct":3,"incorrect":1,"unscored":1})
            self.assertEqual(result["check_group_counts"],{"incorrect":1,"correct":1})
            self.assertEqual(len(result["physical_object_groups"][0]["distinct_crops"]),2)
            self.assertEqual(result["new_emitted_other_group_count"],0)
            self.assertFalse(result["checks"]["new_emitted_others_negative_and_removed"])
            self.assertFalse(result["checks"]["excluded_head_and_clothing_present"])
            self.assertEqual(result["unknown_rows_unscored"],["unknown"])
            scores["alias"] = 2
            with self.assertRaisesRegex(ValueError,"Same native crop"):
                policy._semantic_report(rows,scores,indexed,applied,"pending")


if __name__ == "__main__":
    unittest.main()
