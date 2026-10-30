"""Meaningful tiny saved-record diagnostic checks; no images or neural calls."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from src.ball_tracking import fresh_game_analysis as analysis


def fixture():
    reference = {"status": "human_accepted_AI_reference", "role": "diagnostic_development",
                 "training_eligible": False, "checkpoint_selection_eligible": False, "game_id": "new_game",
                 "clips": [{"clip_id": "a", "source_video": {"sha256": "a" * 64},
                            "source_metadata": {"width": 100, "height": 100}},
                           {"clip_id": "b", "source_video": {"sha256": "b" * 64},
                            "source_metadata": {"width": 100, "height": 100}}], "frames": []}
    frames, candidates, scores = [], [], []
    specs = [
        [("0n", 80, 50, "native", True, 2, -1), ("0w", 50, 50, "weak", False, 1, 3)],
        [("1n", 50, 50, "native", True, -1, 1), ("1w", 80, 50, "weak", False, 2, 4)],
        [("2n", 60, 50, "native", True, 0, -1), ("2w", 60.0001, 50, "weak", False, -2, 0)],
        [("3n", 30, 40, "native", True, 1, -1)],
        [("4n", 45, 45, "native", True, -1, 1)],
        [],
        [("6n", -1, 50, "native", True, None, None), ("6w", 31, 50, "weak", False, -1, 1)],
        [("7n", -1, 50, "native", True, None, None)],
        [("8z", 50, 50, "native", True, 1, -1), ("8a", 51, 50, "weak", False, 1, 2)],
        [("9w", 50, 50, "weak", False, -1, 1)],
    ]
    for i, own in enumerate(specs):
        clip = "a" if i < 5 else "b"
        category = "hidden" if i in (3, 7) else "unknown" if i == 4 else "eligible"
        annotation = {"frame_index": i, "annotation_status": "labeled",
                      "visibility": "not_visible" if category == "hidden" else "partially_visible" if category == "unknown" else "fully_visible",
                      "absence_reason": "occluded" if category == "hidden" else None,
                      "game_ball_identity_certainty": "certain", "geometry": None,
                      "localization_eligible": category == "eligible", "difficulty_tags": [], "notes": "Synthetic reference."}
        if category == "eligible":
            annotation["geometry"] = {"center_xy_px": [1 if i == 6 else 50, 50],
                                      "uncertainty_radius_px": 3, "source": "observed_complete_ball_center"}
        png = {"path": f"synthetic/{i}.png", "bytes": i + 1, "sha256": str(i) * 64, "rgb_sha256": "0" * 64}
        ref = {"clip_id": clip, "frame_key": f"new_{clip}:{i}", "source_frame_index": i,
               "native_pts_ticks": i * 1000, "native_time_base": "1/60000", "native_duration_ticks": 1000,
               "source_png": png, "annotation": annotation}
        reference["frames"].append(ref)
        common = {"frame_key": ref["frame_key"], "frame_id": f"f{i}", "clip_id": clip, "block_id": clip,
                  "game_id": "new_game", "source_frame_index": i, "source_pts_ticks": i * 1000,
                  "time_base": "1/60000", "source_video_sha256": clip * 64, "source_png": png}
        for k, (identity, x, y, origin, selected, q, j) in enumerate(own):
            candidates.append({**common, "candidate_id": identity, "candidate_index": k,
                               "center_xy_px": [x, y], "width_px": 100, "height_px": 100,
                               "in_source_bounds": x >= 0, "native_or_weak": origin, "selected_native": selected})
            scores.append({"candidate_id": identity, "frame_key": ref["frame_key"], "Q": q, "J": j,
                           "status": "observed" if x >= 0 else "out_of_source_bounds"})
        ranked = sorted((s for s in own if s[5] is not None), key=lambda s: (-s[5], s[0]))
        frames.append({**common, "duration_ticks": 1000, "candidate_ids": [s[0] for s in own],
                       "native_selected_candidate_id": next((s[0] for s in own if s[4]), None),
                       "quality_top_candidate_id": ranked[0][0] if ranked else None,
                       "quality_top_tied_candidate_ids": [s[0] for s in ranked if s[5] == ranked[0][5]] if ranked else [],
                       "point_chosen_before_acceptance": True, "fallback_allowed": False})
    return reference, frames, candidates, scores


class FreshGameAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.data = fixture()

    def result(self):
        return analysis.analyze_records(*self.data)

    def test_manual_denominators_unknown_and_raw_oob_emissions(self):
        result = self.result()
        self.assertEqual(result["summary"]["population"], {"frames": 10, "eligible": 7, "certain_hidden": 2, "unknown": 1})
        counts = result["summary"]["fixed_policy_counts"]
        self.assertEqual([counts["native"]["before"][k] for k in ("correct", "wrong_eligible", "hidden_emissions", "unknown_emissions", "missing_choices")], [3, 2, 2, 1, 2])
        self.assertEqual([counts["quality_top"]["J"][k] for k in ("correct", "wrong_eligible", "hidden_emissions", "unknown_emissions")], [2, 2, 0, 1])
        self.assertEqual(counts["native"]["before"]["out_of_bounds_emissions"], 2)
        self.assertEqual(counts["native"]["Q"]["out_of_bounds_emissions"], 0)

    def test_pool_availability_is_separate_from_choice_and_no_fallback(self):
        result = self.result()
        coverage = result["summary"]["pool_coverage"]
        self.assertEqual(coverage["eligible_with_matching_candidate"], 5)
        self.assertEqual(coverage["eligible_without_matching_candidate"], 2)
        self.assertEqual(coverage["weak_match_available_on_native_failure"], 2)
        self.assertEqual(coverage["eligible_weak_only_matching_pool"], 2)
        row = result["frames"][0]
        self.assertEqual(row["pool"]["matching_candidate_ids"], ["0w"])
        self.assertEqual(row["choices"]["quality_top"]["candidate_id"], "0n")
        self.assertFalse(row["choices"]["quality_top"]["accepted"]["J"])
        self.assertIn("quality_top:wrong_choice_match_available", row["diagnostic_flags"])

    def test_exact_ten_pixel_match_and_strict_zero_not_training_boundary(self):
        result = self.result()
        points = {r["candidate_id"]: r for r in result["candidates"]}
        self.assertEqual(points["2n"]["evaluation_category"], "eligible_match")
        self.assertTrue(points["2n"]["exact_match_boundary"])
        self.assertFalse(points["2n"]["accepted"]["Q"])
        self.assertEqual(points["2w"]["evaluation_category"], "eligible_miss")
        self.assertTrue(points["2w"]["within_recorded_uncertainty_of_match_boundary"])
        self.assertFalse(points["2w"]["accepted"]["J"])

    def test_exact_gains_and_losses_do_not_hide_cancelling_regressions(self):
        paired = next(r for r in self.result()["paired"] if r["scope"] == "all" and r["policy"] == "native" and r["from"] == "Q" and r["to"] == "J")
        self.assertEqual(paired["counts"]["correct_gained"], 1)
        self.assertEqual(paired["counts"]["correct_lost"], 1)
        self.assertEqual(paired["exact_cases"]["correct_gained"], [{"frame_key": "new_a:1", "candidate_id": "1n"}])
        self.assertEqual(paired["exact_cases"]["correct_lost"], [{"frame_key": "new_b:8", "candidate_id": "8z"}])

    def test_tied_q_choice_uses_identity_before_j_and_keeps_negative_choices(self):
        result = self.result()
        tied = result["frames"][8]
        self.assertEqual(tied["quality_top_tied_candidate_ids"], ["8a", "8z"])
        self.assertEqual(tied["choices"]["quality_top"]["candidate_id"], "8a")
        self.assertEqual(result["frames"][9]["choices"]["quality_top"]["candidate_id"], "9w")
        self.assertFalse(result["frames"][9]["choices"]["quality_top"]["accepted"]["Q"])
        self.data[1][8]["quality_top_candidate_id"] = "8z"
        with self.assertRaisesRegex(ValueError, "Q-top identity"):
            self.result()

    def test_oob_near_reference_is_not_match_and_missing_stays_missing(self):
        result = self.result()
        self.assertEqual(result["frames"][6]["choices"]["native"]["distance_to_reference_px"], 2)
        self.assertEqual(result["frames"][6]["choices"]["native"]["evaluation_category"], "eligible_miss")
        self.assertEqual(result["frames"][7]["choices"]["native"]["evaluation_category"], "certain_hidden")
        self.assertEqual(result["frames"][5]["pool"]["candidate_ids"], [])
        self.assertEqual(result["frames"][5]["choices"]["native"]["accepted"], {"before": False, "Q": False, "J": False})

    def test_complete_id_order_duplicate_and_missing_score_validation(self):
        for mutation in (lambda d: d[3].pop(), lambda d: d[3].append(deepcopy(d[3][0])),
                         lambda d: d[3].reverse(), lambda d: d[1].pop(),
                         lambda d: d[3][0].update(frame_key="another_frame")):
            with self.subTest(mutation=mutation):
                data = deepcopy(self.data); mutation(data)
                with self.assertRaises(ValueError):
                    analysis.analyze_records(*data)

    def test_malformed_scores_and_bounds_cannot_become_abstentions(self):
        for value in (None, True, float("nan"), float("inf"), "1"):
            with self.subTest(value=value):
                data = deepcopy(self.data); data[3][0]["Q"] = value
                with self.assertRaises(ValueError):
                    analysis.analyze_records(*data)
        self.data[2][0]["in_source_bounds"] = False
        with self.assertRaisesRegex(ValueError, "bounds"):
            self.result()

    def test_source_dimensions_timing_game_and_native_flag_are_strict(self):
        mutations = [lambda d: d[2][0].update(width_px=200), lambda d: d[2][0].update(game_id="old_game"),
                     lambda d: d[1][0].update(source_pts_ticks=1), lambda d: d[2][0].update(source_video_sha256="wrong"),
                     lambda d: d[2][0].update(candidate_index=2), lambda d: d[1][0].update(fallback_allowed=True),
                     lambda d: d[2][1].update(selected_native=True)]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                data=deepcopy(self.data); mutation(data)
                with self.assertRaises(ValueError): analysis.analyze_records(*data)

    def test_reference_role_and_census_must_be_accepted_and_fixed(self):
        for field, value in (("status", "pending"), ("training_eligible", True), ("role", "training")):
            data=deepcopy(self.data); data[0][field]=value
            with self.assertRaises(ValueError): analysis.analyze_records(*data)
        with self.assertRaisesRegex(ValueError, "population"):
            analysis.analyze_records(*self.data, expected_population=analysis.FIXED_POPULATION)

    def test_full_case_inventory_scopes_and_inputs_preserved(self):
        old = deepcopy(self.data)
        result = self.result()
        self.assertEqual(old, self.data)
        self.assertEqual(len(result["frames"]), 10)
        self.assertEqual(len(result["policies"]), 20)
        self.assertEqual([r["frame_key"] for r in result["case_index"]], [r["frame_key"] for r in self.data[0]["frames"]])
        clips=[r for r in result["tables"] if r["scope"] == "clip" and r["kind"] == "fixed_policy" and r["policy"] == "native" and r["view"] == "before"]
        self.assertEqual(sum(r["counts"]["frames"] for r in clips), 10)
        self.assertEqual([r["native_success_group"] for r in result["frames"]], ["failure", "correct", "correct", "not_eligible", "not_eligible", "failure", "failure", "not_eligible", "correct", "failure"])

    def test_actual_inference_fixed_choice_helper_contract(self):
        from src.ball_tracking.fresh_game_inference import fixed_choices
        reference, frames, candidates, scores = self.data
        old=[{k:v for k,v in f.items() if k not in ("quality_top_candidate_id", "quality_top_tied_candidate_ids", "point_chosen_before_acceptance", "fallback_allowed")} for f in frames]
        actual=fixed_choices(old,candidates,{s["candidate_id"]:s["Q"] for s in scores if s["Q"] is not None})
        self.assertEqual(actual,frames)
        self.assertEqual(analysis.analyze_records(reference,actual,candidates,scores)["summary"]["candidate_count"],14)

    def test_actual_pool_row_transport_to_complete_consumer(self):
        from src.ball_tracking.fresh_game_inference import pool_rows, fixed_choices
        reference=deepcopy(self.data[0]);reference["frames"]=reference["frames"][:1];reference["clips"]=reference["clips"][:1]
        frame=reference["frames"][0]
        block={"block_id":"a","clip_id":"a","time_base":"1/60000",
               "source_video":{"sha256":"a"*64,"width_px":100,"height_px":100},
               "frames":[{"frame_key":frame["frame_key"],"source_frame_index":0,"source_pts_ticks":0,
                          "duration_ticks":1000,"png":frame["source_png"]}]}
        native={"center_x":80,"center_y":50,"native_score":0.8,"component_pixels":3}
        native_pool={**native,"candidate_index":0,"extraction":"native_component","threshold":0.3,"in_source_bounds":True}
        weak_pool={"center_x":50,"center_y":50,"native_score":0.02,"component_pixels":2,
                   "candidate_index":1,"extraction":"threshold_component","threshold":0.01,"in_source_bounds":True}
        observation={"source_frame_index":0,"source_pts_ticks":0,"mean_heatmap_sha256":"c"*64,
                     "source_png":frame["source_png"],"time_base":"1/60000","candidates":[native],
                     "selected_candidate_index":0,"state":"observed","temporal_contributions":1}
        record={"native_observations":[observation],"extraction":{"pools":{"path":"synthetic/pools.jsonl","bytes":1,"sha256":"d"*64}}}
        pool={"block_id":"a","source_frame_index":0,"source_pts_ticks":0,"time_base":"1/60000",
              "mean_heatmap_sha256":"c"*64,"diagnostic":{"native_parity":True,"labels_used":False,"native_count":1,"pool_count":2},
              "candidates":[native_pool,weak_pool]}
        produced,candidates=pool_rows(block,record,[pool])
        # The real producer's GAME constant must match its accepted game identity.
        reference["game_id"]=produced[0]["game_id"]
        native_id,weak_id=[c["candidate_id"] for c in candidates]
        produced=fixed_choices(produced,candidates,{native_id:2.0,weak_id:1.0})
        scores=[{"candidate_id":c["candidate_id"],"frame_key":c["frame_key"],"Q":q,"J":j,"status":"observed"}
                for c,q,j in zip(candidates,[2.0,1.0],[-1.0,3.0])]
        result=analysis.analyze_records(reference,produced,candidates,scores)
        self.assertEqual(result["frames"][0]["pool"]["matching_weak_ids"],[weak_id])
        self.assertEqual(result["frames"][0]["choices"]["quality_top"]["candidate_id"],native_id)
        self.assertFalse(result["frames"][0]["choices"]["quality_top"]["accepted"]["J"])
        self.assertEqual(result["summary"]["pool_coverage"]["weak_match_available_on_native_failure"],1)

    def _saved_fixture(self, root):
        attempt=root/"attempt";attempt.mkdir()
        reference, frames, candidates, scores=self.data
        ref=root/"accepted.json";ref.write_text(json.dumps(reference),encoding="utf8")
        completion={"status":"completed_fresh_game_inference_no_fitting", "accepted_reference":analysis.binding(root,ref)}
        for name,values in (("frames",frames),("candidates",candidates),("scores",scores)):
            p=attempt/(name+".jsonl");p.write_text("\n".join(json.dumps(r) for r in values)+"\n",encoding="utf8")
            completion[name]=analysis.binding(root,p)
        (attempt/"completed.json").write_text(json.dumps(completion),encoding="utf8")
        return ref,attempt

    def test_exclusive_outputs_bind_full_records_and_refuse_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();ref,attempt=self._saved_fixture(root)
            receipt=analysis.analyze(root,attempt,"analysis",ref,expected_population=None)
            self.assertEqual(receipt["population"]["frames"],10)
            self.assertEqual(set(receipt["outputs"]),{"frames","candidates","policies","tables","paired","case_index","summary"})
            saved=(root/"analysis/completed.json").read_bytes()
            with self.assertRaisesRegex(ValueError,"overwrite/retry"):
                analysis.analyze(root,attempt,"analysis",ref,expected_population=None)
            self.assertEqual((root/"analysis/completed.json").read_bytes(),saved)

    def test_changed_input_failure_is_preserved_without_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();ref,attempt=self._saved_fixture(root)
            with (attempt/"scores.jsonl").open("a",encoding="utf8") as stream:stream.write("{}\n")
            with self.assertRaisesRegex(ValueError,"binding changed"):
                analysis.analyze(root,attempt,"analysis",ref,expected_population=None)
            self.assertTrue((root/"analysis/failed.json").exists())
            self.assertFalse((root/"analysis/completed.json").exists())
            with self.assertRaisesRegex(ValueError,"overwrite/retry"):
                analysis.analyze(root,attempt,"analysis",ref,expected_population=None)


if __name__ == "__main__":
    unittest.main()
