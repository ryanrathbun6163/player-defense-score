"""Fixed temporal rule and transport checks using emitted component records."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from src.ball_tracking import nba_temporal_gap_selection as selector
from src.ball_tracking import nba_candidate_preservation as pools
from src.ball_tracking import nba_action_observation as producer
from src.ball_tracking import nba_wasb_diagnostic as scorer
from tests.test_nba_hard_example_diagnostic import label

ROOT = Path(__file__).resolve().parents[1]


def geometry(index, pts, center, candidates=(), window="test"):
    return {"window_id": window, "candidate_id": "synthetic", "source_frame_index": index,
        "source_pts_ticks": pts, "width_px": 300, "height_px": 400,
        "baseline_center_xy_px": center,
        "pool_records": [{"record_index": i, "center_xy_px": list(xy),
                          "provenance_id": ["old", "synthetic", index, "contributor", index-1, 1, i]}
                         for i, xy in enumerate(candidates)]}


def producer_report():
    """Candidates, original observations and original scores come from producers."""
    source = {"width_px": 512, "height_px": 288}
    frames = [{"source_frame_index": i, "source_pts_ticks": (i-1)*3600, "png": {"path": f"fixture_{i}.png"}}
              for i in (1, 2, 3)]
    manifest = {"candidate_id": "synthetic", "game_id": "fixture", "approved_role": "development",
                "source_video": source, "time_base": "1/90000", "frames": frames}
    rows = []
    for frame, point in zip(frames, ([50, 50], None, [52, 50])):
        mean = np.zeros((288, 512), np.float32)
        if point is not None: mean[point[1], point[0]] = .8
        observation = producer.select_observation(frame, mean, 3, manifest,
            {"kind": "development_window", "source_frame_range_inclusive": [1, 3]})
        candidate = mean.copy()
        if point is None: candidate[50, 51] = .8
        index = frame["source_frame_index"]
        pool = pools.build_pool("old", "synthetic", index, observation,
            [(index-2, 2, candidate), (index-1, 1, mean), (index, 0, mean)], (512, 288))
        annotation = label(index, (49+index, 50))
        score = scorer.score_reference({**manifest, "frames": [frame], "annotations": [annotation]},
                                       {"frames": [observation]})["frame_results"][0]
        rows.append({"window_id": "test", "candidate_id": "synthetic", "source_frame_index": index,
            "source_frame": frame, "source_video": source, "analysis_group": "sac_training_fit",
            "cohort": "synthetic", "is_control": False, "annotation": annotation, "eligibility": "eligible",
            "old": {"pool": pool, "original_score": score,
                    "original_selected": {k: observation[k] for k in ("state", "center_xy_px", "native_score", "selected_candidate_index")}}})
    return {"frames": rows}


class TemporalGapSelectionTests(unittest.TestCase):
    def test_actual_producer_pool_transport_and_original_scores_are_preserved(self):
        report = producer_report(); before = copy.deepcopy(report)
        selection = selector.attach_provenance(selector.select_all([[selector.projection(r) for r in report["frames"]]]), report)
        self.assertEqual([r["decision"] for r in selection["frames"]],
                         ["preserved_original", "filled_saved_candidate", "preserved_original"])
        self.assertEqual(selection["frames"][1]["selected_center_xy_px"], [51, 50])
        self.assertEqual(selection["frames"][1]["selected_pool_record_index"], 0)
        self.assertEqual(selection["frames"][1]["selected_provenance_id"], ["old", "synthetic", 2, "contributor", 0, 2, 0])
        for offset in (0, 2):
            row = selection["frames"][offset]
            self.assertEqual(row["original_selected"], before["frames"][offset]["old"]["original_selected"])
            self.assertEqual(row["selected_native_score"], row["original_selected"]["native_score"])
            self.assertEqual(row["selected_component"], before["frames"][offset]["old"]["pool"]["records"][0]["component"])
        scored = selector.score(report, selection)
        self.assertEqual([r["baseline"]["outcome"] for r in scored], ["matched", "missing", "matched"])
        self.assertEqual([r["selected"]["outcome"] for r in scored], ["matched"]*3)
        self.assertEqual(report, before)
        # Scorer parity is checked independently, rather than copied from old results.
        changed = copy.deepcopy(report); changed["frames"][0]["old"]["original_score"]["raw_center_error_px"] = 99
        with self.assertRaisesRegex(ValueError, "original outcomes/errors"): selector.score(changed, selection)

    def test_projection_excludes_labels_scores_new_arm_and_metadata(self):
        report = producer_report(); original = [selector.projection(r) for r in report["frames"]]
        changed = copy.deepcopy(report)
        for row in changed["frames"]:
            row["annotation"] = {"forbidden": "labels"}
            row["eligibility"] = "hidden"; row["is_control"] = True; row["cohort"] = "different"
            row["old"]["original_score"] = {"outcome": "wrong"}; row["new"] = {"center": [0, 0]}
        projected = [selector.projection(r) for r in changed["frames"]]
        self.assertEqual(projected, original)
        self.assertEqual(json.dumps(selector.select_all([projected]), sort_keys=True),
                         json.dumps(selector.select_all([original]), sort_keys=True))
        projected[0]["annotation"] = {}
        with self.assertRaisesRegex(ValueError, "whitelist"): selector.select_window(projected)

    def test_inclusive_native_span_and_speed_boundaries(self):
        rows = [geometry(1, 0, [100, 100]), geometry(2, 3600, None, [[120, 100]]),
                geometry(3, 7200, None, [[140, 100]]), geometry(4, 10800, [160, 100])]
        result = selector.select_window(rows)
        self.assertEqual(result["gaps"][0]["anchor_elapsed_seconds"], .12)
        self.assertEqual(result["gaps"][0]["anchor_speed_diagonals_per_second"], 1)
        self.assertEqual(result["gaps"][0]["status"], "filled")
        slow = copy.deepcopy(rows); slow[-1]["source_pts_ticks"] = 10801
        self.assertEqual(selector.select_window(slow)["gaps"][0]["reason"], "anchor_elapsed_exceeds_limit")
        fast = copy.deepcopy(rows); fast[-1]["baseline_center_xy_px"][0] += .000001
        self.assertEqual(selector.select_window(fast)["gaps"][0]["reason"], "anchor_speed_exceeds_limit")
        irregular = [geometry(1, 0, [100, 100]), geometry(2, 900, None, [[105, 100]]), geometry(3, 7200, [140, 100])]
        result = selector.select_window(irregular)
        self.assertEqual(result["gaps"][0]["frame_diagnostics"][0]["expected_center_xy_px"], [105, 100])
        self.assertEqual(result["frames"][1]["selected_center_xy_px"], [105, 100])

    def test_exact_duplicate_groups_distance_ties_and_spatial_boundaries(self):
        rows = [geometry(1, 0, [100, 100]), geometry(2, 3600, None, [[103, 100], [103, 100]]),
                geometry(3, 7200, [100, 100])]
        result = selector.select_window(rows)
        self.assertEqual(result["frames"][1]["selected_center_xy_px"], [103, 100])
        self.assertEqual(result["frames"][1]["selected_coordinate_group"]["record_indices"], [0, 1])
        tied = copy.deepcopy(rows); tied[1] = geometry(2, 3600, None, [[101.5, 100], [98.5, 100]])
        result = selector.select_window(tied)
        self.assertEqual(result["gaps"][0]["frame_diagnostics"][0]["plausible_pairwise_diameter_px"], 3)
        self.assertEqual(result["frames"][1]["selected_pool_record_index"], 0)
        separated = copy.deepcopy(tied); separated[1]["pool_records"][1]["center_xy_px"][0] -= .000001
        self.assertEqual(selector.select_window(separated)["gaps"][0]["status"], "abstained")
        too_far = copy.deepcopy(rows)
        for record in too_far[1]["pool_records"]: record["center_xy_px"][0] += .000001
        self.assertIsNone(selector.select_window(too_far)["frames"][1]["selected_center_xy_px"])

    def test_whole_gap_abstention_and_original_anchors_are_never_recursive(self):
        rows = [geometry(1, 0, [100, 100]), geometry(2, 3600, None, [[100, 100]]),
                geometry(3, 7200, None, []), geometry(4, 10800, [100, 100])]
        result = selector.select_window(rows)
        self.assertEqual([r["selected_center_xy_px"] for r in result["frames"][1:3]], [None, None])
        self.assertTrue(result["gaps"][0]["frame_diagnostics"][0]["acceptable"])
        # Good interior saved candidates cannot recursively shorten a maximal long gap.
        long = [geometry(1, 0, [100, 100])] + [geometry(i, (i-1)*3600, None, [[100, 100]]) for i in (2, 3, 4)] + [geometry(5, 14400, [100, 100])]
        result = selector.select_window(long)
        self.assertEqual(len(result["gaps"]), 1)
        self.assertEqual(result["gaps"][0]["reason"], "anchor_elapsed_exceeds_limit")
        self.assertTrue(all(r["selected_center_xy_px"] is None for r in result["frames"][1:4]))

    def test_edges_out_of_image_anchors_and_window_boundaries_preserve_points(self):
        rows = [geometry(1, 0, None, [[100, 100]]), geometry(2, 3600, [100, 100]),
                geometry(3, 7200, None, [[100, 100]])]
        result = selector.select_window(rows)
        self.assertEqual([g["reason"] for g in result["gaps"]], ["window_edge_gap"]*2)
        outside = [geometry(1, 0, [-1, 100], [[100, 100]]), geometry(2, 3600, None, [[100, 100]]),
                   geometry(3, 7200, [100, 100])]
        result = selector.select_window(outside)
        self.assertEqual(result["frames"][0]["selected_center_xy_px"], [-1, 100])
        self.assertEqual(result["gaps"][0]["reason"], "anchor_out_of_image")
        other = copy.deepcopy(rows); other[1]["window_id"] = "other"
        with self.assertRaisesRegex(ValueError, "crossed source/window"): selector.select_window(other)
        other = copy.deepcopy(rows); other[1]["source_frame_index"] += 1
        with self.assertRaisesRegex(ValueError, "not consecutive"): selector.select_window(other)

    def test_native_missing_intervals_do_not_invent_final_frame_duration(self):
        report = producer_report(); projected = [selector.projection(r) for r in report["frames"]]
        selection = selector.attach_provenance(selector.select_all([projected]), report)
        rows = selector.score(report, selection)
        interval = selector.missing_intervals(rows, "baseline")[0]
        self.assertEqual(interval["source_frame_range_inclusive"], [2, 2])
        self.assertEqual(interval["duration_seconds"], .04)
        rows[-1]["baseline"]["outcome"] = "missing"
        interval = selector.missing_intervals(rows, "baseline")[0]
        self.assertEqual(interval["source_frame_range_inclusive"], [2, 3])
        self.assertTrue(interval["right_censored_at_window_end"])
        self.assertIsNone(interval["duration_seconds"])

    def test_selection_is_immutable_before_scoring_failure_and_attempt_is_preserved(self):
        report = producer_report(); projected = [[selector.projection(r) for r in report["frames"]]]
        parent = ROOT/"data/outputs/t"; parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="temporal_selection_", dir=parent) as folder:
            output = Path(folder); scope = {"output_root": output.relative_to(ROOT).as_posix(),
                "input_report": {}, "pool_scope": {}, "pre_execution_design": {}}
            path = output/"scope.json"; scorer.write_once(path, scope)
            def fail_after_saved(*args):
                artifacts = list(output.glob("attempts/*/selection.json"))
                self.assertEqual(len(artifacts), 1)
                self.assertEqual(len(scorer.read_json(artifacts[0])["frames"]), 3)
                raise RuntimeError("synthetic scoring failure")
            with patch.object(selector, "load_context", return_value=(scope, report, projected)), patch.object(selector, "score", side_effect=fail_after_saved):
                with self.assertRaisesRegex(RuntimeError, "synthetic scoring failure"): selector.run(ROOT, path)
            failures = list(output.glob("attempts/*/failed.json"))
            self.assertEqual(len(failures), 1)
            self.assertEqual(scorer.read_json(failures[0])["resources"]["heatmap_array_reads"], 0)
            self.assertFalse((output/"completion.json").exists())


if __name__ == "__main__": unittest.main()
