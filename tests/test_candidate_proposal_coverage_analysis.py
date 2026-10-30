import copy
import json
from pathlib import Path
from unittest import mock

import unittest
import tempfile

from src.ball_tracking import candidate_proposal_coverage_analysis as analysis
from src.ball_tracking import candidate_quality_data as original


CHI, DEN, SAC = original.NBA_GAMES


def frame(game=CHI, index=0, kind="positive", block="block", video=None, uncertainty=2):
    video = video or "video-" + game
    annotation = {"frame_index": index, "game_ball_identity_certainty": "certain",
                  "visibility": "visible" if kind == "positive" else "not_visible",
                  "localization_eligible": kind == "positive",
                  "geometry": {"center_xy_px": [50, 50], "uncertainty_radius_px": uncertainty} if kind == "positive" else None}
    return {"frame_id": f"{game}:{block}:{index}", "block_id": block, "game_id": game, "domain": "nba",
            "source_frame_index": index, "source_pts_ticks": index * 1000, "duration_ticks": 1000,
            "time_base": "1/60000", "source_video_sha256": video,
            "source_video": {"sha256": video, "path": video + ".mp4", "width_px": 100, "height_px": 100},
            "source_png": {"rgb_sha256": f"rgb-{video}-{index}", "sha256": f"png-{video}-{index}"},
            "annotation": annotation, "kind": kind, "valid_output_channel": kind != "masked",
            "original_source_role": "training", "candidate_ids": [], "candidate_count": 0,
            "native_selected_candidate_index": None, "native_center_xy_px": None}


def population(specs, prefix):
    frames, candidates = [], []
    for base, points, selected in specs:
        fr = copy.deepcopy(base)
        for index, (origin, x, y) in enumerate(points):
            candidate = {"center_x": x, "center_y": y, "in_source_bounds": 0 <= x < 100 and 0 <= y < 100}
            cid = f"{prefix}:{fr['frame_id']}:{index}"
            row = {key: fr[key] for key in ("frame_id", "block_id", "game_id", "domain", "source_frame_index",
                                           "source_pts_ticks", "time_base", "source_video_sha256", "source_png")}
            row.update(candidate_id=cid, candidate_index=index, native_or_weak=origin,
                       center_xy_px=[x, y], width_px=100, height_px=100, producer_candidate=candidate,
                       **original.candidate_target(fr, candidate, 100, 100))
            candidates.append(row)
            fr["candidate_ids"].append(cid)
        fr["candidate_count"] = len(points)
        fr["native_selected_candidate_index"] = selected
        fr["native_center_xy_px"] = list(points[selected][1:]) if selected is not None else None
        frames.append(fr)
    return frames, candidates


def covered_populations():
    old_specs, new_specs = [], []
    for game in (CHI, DEN):
        visible, hidden = frame(game, 0), frame(game, 1, "hidden")
        old_specs.extend([(visible, [("native", 50, 50)], 0), (hidden, [], None)])
        new_specs.extend([(visible, [("native", 80, 50), ("weak", 50, 50)], 0),
                          (hidden, [("native", 20, 20)], 0)])
    last = frame(SAC, 0)
    old_specs.append((last, [("native", 50, 50)], 0))
    new_specs.append((last, [("native", 50, 50)], 0))
    return (*population(new_specs, "new"), *population(old_specs, "old"))


def history_at(fr, center, role="diagnostic_only"):
    return {"row_key": "historical:" + fr["frame_id"], "source_video": fr["source_video"],
            "source_frame_index": fr["source_frame_index"], "source_png": fr["source_png"],
            "center_xy_px": list(center), "historical_role": role,
            "target": None, "original_semantic_target": 1}


class CandidateProposalCoverageAnalysisTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.tmp_path = Path(temporary.name)

    def test_exact_original_target_boundary_unknown_hidden_and_empty_frames(self):
        visible = frame(uncertainty=5)
        hidden = frame(index=1, kind="hidden")
        masked = frame(index=2, kind="masked")
        empty = frame(index=3)
        specs = [(visible, [("native", 65, 50), ("weak", 60, 50), ("weak", 65.01, 50), ("weak", -1, 50)], 0),
                 (hidden, [("native", 50, 50)], 0), (masked, [("native", 50, 50)], 0), (empty, [], None)]
        new_f, new_c = population(specs, "new")
        old_f, old_c = population(specs, "old")
        result = analysis.analyze_populations(new_f, new_c, old_f, old_c, [])
        assert [row["target_group"] for row in new_c] == ["boundary_unknown", "positive", "eligible_distant_miss",
                                                            "eligible_distant_miss", "certain_hidden", "masked_unknown"]
        groups = result["support"]["alternate_producer"]
        assert groups["chosen_native_known_distant"]["candidate_rows"] == 0
        assert groups["chosen_native_wrong_all"]["candidate_rows"] == 1
        assert groups["weak_positive_native_wrong"]["candidate_rows"] == 1
        assert groups["chosen_native_certain_hidden"]["candidate_rows"] == 1
        assert result["summary"]["frames"] == 4
        assert result["summary"]["new_native_outcomes"] == {"wrong": 1, "hidden_emission": 1, "masked_observed": 1, "missing": 1}
        assert result["support"]["frame_populations"]["empty_new_pool"]["frames"] == 1
        assert result["novelty"][3]["point_model_input_eligible"] is False


    def test_all_three_categories_two_games_all_outer_folds_and_novelty_required(self):
        populations = covered_populations()
        result = analysis.analyze_populations(*populations, [])
        decision = result["decision"]
        assert decision["joint_transfer_design_eligible"] is True
        assert decision["raw_producer_relative_coverage"]["passed"] is True
        for condition in decision["raw_producer_relative_coverage"]["conditions"].values():
            assert condition["game_ids"] == sorted([CHI, DEN])
            assert all(row["candidate_rows"] > 0 for row in condition["outer_training_folds"].values())
        assert decision["useful_new_role_compatible_exact_points"] == 4
        assert result["summary"]["paired_counts"]["current_native_correct_lost"] == 2
        assert result["summary"]["paired_counts"]["lost_native_but_new_pool_has_positive"] == 2
        assert result["summary"]["paired_counts"]["current_native_correct_retained"] == 1
        assert result["summary"]["current_cosine_recovery_view"]["wrong_or_missing_frames"]["frames"] == 0
        assert result["summary"]["current_cosine_recovery_view"]["alternate_weak_positive_on_current_wrong_or_missing"]["frames"] == 0


    def test_one_game_support_does_not_pass_and_held_source_fold_is_zero(self):
        new_f, new_c, old_f, old_c = covered_populations()
        keep = lambda row: row["game_id"] != DEN
        result = analysis.analyze_populations(*[list(filter(keep, values)) for values in (new_f, new_c, old_f, old_c)], [])
        conditions = result["decision"]["raw_producer_relative_coverage"]["conditions"]
        assert not result["decision"]["joint_transfer_design_eligible"]
        for condition in conditions.values():
            assert not condition["at_least_two_games"]
            assert condition["outer_training_folds"]["leave_chi_out"]["candidate_rows"] == 0


    def test_producer_relabeling_of_identical_points_cannot_satisfy_novelty(self):
        new_f, new_c, _, _ = covered_populations()
        old_f, old_c = copy.deepcopy(new_f), copy.deepcopy(new_c)
        for row in old_c:
            row["candidate_id"] = "old:" + row["candidate_id"]
        for fr in old_f:
            fr["candidate_ids"] = ["old:" + cid for cid in fr["candidate_ids"]]
        result = analysis.analyze_populations(new_f, new_c, old_f, old_c, [])
        assert result["decision"]["raw_producer_relative_coverage"]["passed"]
        assert result["decision"]["useful_new_role_compatible_exact_points"] == 0
        assert result["decision"]["blocking_reasons"] == ["no_role_compatible_useful_new_exact_point"]


    def test_historical_source_frame_screen_separate_from_raw_science_no_semantic_target_promotion(self):
        new_f, new_c, old_f, old_c = covered_populations()
        historical = [history_at(fr, (80, 50)) for fr in new_f if fr["game_id"] == CHI]
        prior_history = copy.deepcopy(historical)
        result = analysis.analyze_populations(new_f, new_c, old_f, old_c, historical)
        assert result["decision"]["raw_producer_relative_coverage"]["passed"]
        assert not result["decision"]["conservative_role_screened_coverage"]["passed"]
        assert result["decision"]["blocking_reasons"] == ["conservative_role_or_point_input_screen_blocks_required_category_coverage"]
        assert result["decision"]["useful_new_role_compatible_exact_points"] == 2
        assert historical == prior_history
        assert result["summary"]["historical_targets_promoted"] == 0
        assert new_c[0]["target"] == 0  # Historical semantic 1 did not replace geometric negative.
        assert result["novelty"][1]["unresolved_historical_role_row_keys"]  # Even another point on that source frame remains unresolved.
        assert result["novelty"][1]["exact_historical_row_keys"] == []


    def test_exact_point_and_floor_crop_overlap_are_distinct_and_use_numeric_identity(self):
        fr = frame()
        new_f, new_c = population([(fr, [("native", 50.9, 50.9)], 0)], "new")
        old_f, old_c = population([(fr, [("native", 50.1, 50.1)], 0)], "old")
        result = analysis.analyze_populations(new_f, new_c, old_f, old_c, [])
        novelty = result["novelty"][0]
        assert novelty["new_exact_point_vs_current_pool"]
        assert not novelty["new_floor_crop_vs_current_pool"]
        assert novelty["floor_crop_current_candidate_ids"] == [old_c[0]["candidate_id"]]
        assert analysis.point_metadata(new_c[0])["point_input_xy"] != analysis.point_metadata(old_c[0])["point_input_xy"]
        numeric = copy.deepcopy(old_c[0])
        numeric["center_xy_px"] = [50, 50]
        decimal = copy.deepcopy(numeric)
        decimal["center_xy_px"] = [50.0, 50.0]
        assert analysis.point_key(numeric) == analysis.point_key(decimal)


    def test_physical_runs_cross_block_edges_but_not_video_or_missing_index(self):
        items = [frame(index=10, block="a"), frame(index=11, block="b"), frame(index=13, block="b"),
                 frame(index=14, block="c", video="other")]
        runs = analysis.physical_runs(items)
        assert sorted(row["frames"] for row in runs) == [1, 1, 2]
        joined = next(row for row in runs if row["frames"] == 2)
        assert joined["block_ids"] == ["a", "b"]
        assert (joined["first_source_frame"], joined["last_source_frame"]) == (10, 11)
        assert analysis.physical_runs(items + [copy.deepcopy(items[0])]) == runs
        conflict = copy.deepcopy(items[0])
        conflict["source_png"]["rgb_sha256"] = "different"
        with self.assertRaisesRegex(ValueError, "Conflicting duplicate"):
            analysis.physical_runs(items + [conflict])


    def test_current_cosine_weak_recovery_wrong_missing_and_original_positive_losses_are_separate(self):
        wrong, missing, losing, hidden = frame(index=0), frame(index=1), frame(index=2), frame(index=3, kind="hidden")
        old_f, old_c = population([(wrong, [("native", 61, 50)], 0), (missing, [], None),
                                   (losing, [("native", 50, 50), ("weak", 49, 50)], 0), (hidden, [("native", 10, 10)], 0)], "old")
        new_f, new_c = population([(wrong, [("native", 50, 50), ("weak", 49, 50)], 0),
                                   (missing, [("weak", 50, 50)], None), (losing, [], None), (hidden, [], None)], "new")
        result = analysis.analyze_populations(new_f, new_c, old_f, old_c, [])
        current = result["summary"]["current_cosine_recovery_view"]
        assert current["wrong_or_missing_frames"]["frames"] == 2
        assert current["alternate_weak_positive_on_current_wrong"]["frames"] == 1
        assert current["alternate_weak_positive_on_current_missing"]["frames"] == 1
        assert not current["cross_game_gate_applied"]
        assert result["support"]["alternate_producer"]["weak_positive_native_wrong"]["frames"] == 0
        assert result["summary"]["paired_counts"]["current_pool_positive_lost"] == 1
        assert result["summary"]["paired_counts"]["current_native_correct_lost"] == 1
        assert len(result["positive_retention"]) == 2
        assert all(row["new_frame_any_positive_ids"] == [] for row in result["positive_retention"])
        assert result["summary"]["paired_native_transitions"]["hidden_emission -> hidden_abstention"] == 1


    def test_malformed_targets_missing_rows_and_native_fallback_rejected(self):
        populations = covered_populations()
        bad = copy.deepcopy(populations)
        bad[1][0]["target"] = 1
        with self.assertRaisesRegex(ValueError, "Original target"):
            analysis.analyze_populations(*bad, [])
        bad = copy.deepcopy(populations)
        bad[0][0]["native_selected_candidate_index"] = 1
        bad[0][0]["native_center_xy_px"] = [50, 50]
        with self.assertRaisesRegex(ValueError, "weak candidate"):
            analysis.analyze_populations(*bad, [])
        bad = copy.deepcopy(populations)
        bad[1].pop()
        with self.assertRaisesRegex(ValueError, "Pool identity"):
            analysis.analyze_populations(*bad, [])


    def test_label_blind_recursive_seal_validation(self):
        analysis.assert_label_blind({"diagnostic": {"labels_used": False}, "candidates": [{"center_x": 12, "threshold": .01}]})
        for value in ({"candidates": [{"target": None}]}, {"annotation": {}}, {"diagnostic": {"labels_used": True}}):
            with self.assertRaisesRegex(ValueError, "Label field|label use"):
                analysis.assert_label_blind(value)


    def test_unsealed_or_tampered_capture_fails_before_package_label_read(self):
        tmp_path = self.tmp_path
        cap = tmp_path / "capture"
        cap.mkdir()
        complete = {"status": "completed_capture_no_fitting", "extraction_sealed_before_label_assisted_coverage": False,
                    "package": {"path": "must-not-read-package.json"}}
        (cap / "completed.json").write_text(json.dumps(complete))
        with mock.patch.object(original, "verify_binding", side_effect=AssertionError("package read")):
            with self.assertRaisesRegex(ValueError, "not sealed"):
                analysis.load_sealed_capture(tmp_path, cap)
        complete.update(extraction_sealed_before_label_assisted_coverage=True, new_training_updates=0, new_labels=0,
                        new_selector_runs=0, protected_access=False, model_tensors_unchanged=True,
                        new_forward_calls_attempted=3137, new_forward_calls_returned=3137, frames=3179,
                        counts={"blocks": 21, "frames": 3179, "forward_calls": 3137, "imported_frames": 0,
                                "parity_calls": 0, "optimizer_updates": 0},
                        records=[{"path": "capture/changed-record.json", "sha256": "wrong", "bytes": 0}])
        (cap / "completed.json").write_text(json.dumps(complete))
        (cap / "changed-record.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "Changed binding"):
            analysis.load_sealed_capture(tmp_path, cap)


    def test_failure_receipt_preserved_and_output_retry_refused(self):
        tmp_path = self.tmp_path
        out = tmp_path / "analysis"
        with mock.patch.object(analysis, "load_sealed_capture", side_effect=ValueError("synthetic missing pool")):
            with self.assertRaisesRegex(ValueError, "synthetic missing pool"):
                analysis.analyze_capture(tmp_path, tmp_path / "capture", out)
        failure = json.loads((out / "failed.json").read_text())
        assert failure["status"] == "failed_preserved_no_retry"
        saved = (out / "failed.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "Preserve existing"):
            analysis.analyze_capture(tmp_path, tmp_path / "capture", out)
        assert (out / "failed.json").read_bytes() == saved
        assert not (out / "completed.json").exists()


if __name__ == "__main__":
    unittest.main()
