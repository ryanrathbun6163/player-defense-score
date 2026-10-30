"""Actual-producer fixtures and native scoring/render transport; CPU only."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

from src.ball_tracking import weak_response_review as review
from src.ball_tracking.nba_action_observation import select_observation, stream_means


ROOT = Path(__file__).resolve().parents[1]
REAL_INPUT = ROOT / "data/outputs/ball_tracking/wasb_continuation_v0_1/paired_review_inputs_v0_1.json"


def fixture():
    frames, pts = [], 90000
    for offset, duration in enumerate((1440, 1530, 1440, 1530)):
        category = ("eligible", "eligible", "unlabeled", "probable_hidden")[offset]
        label = None if category == "unlabeled" else {
            "frame_index": 100 + offset, "annotation_status": "labeled",
            "visibility": "fully_visible" if category == "eligible" else "not_visible",
            "absence_reason": None if category == "eligible" else "occluded",
            "game_ball_identity_certainty": "certain" if category == "eligible" else "probable",
            "geometry": {"center_xy_px": [20, 12], "source": "observed_complete_ball_center",
                         "uncertainty_radius_px": 2} if category == "eligible" else None,
            "localization_eligible": category == "eligible", "difficulty_tags": [], "notes": "Synthetic producer fixture."}
        frames.append({"source_frame_index": 100 + offset, "source_pts_ticks": pts,
            "duration_ticks": duration, "png": {"path": f"synthetic/{offset}.png", "sha256": "a" * 64},
            "annotation": label, "reference_role": "checkpoint_validation", "state": "permitted"})
        pts += duration
    block = {"block_id": "synthetic", "domain": "nba", "game_id": "synthetic", "role": "checkpoint_validation",
             "time_base": "1/90000", "source_video": {"width_px": 64, "height_px": 36, "frame_count": 200}, "frames": frames}
    def provider(_):
        heatmaps = np.zeros((3, 288, 512), np.float32)
        heatmaps[:, 96, 160] = .5  # observed ball at (20,12)
        heatmaps[:, 160, 320] = .9  # stronger wrong object at (40,20)
        return heatmaps
    rows = [select_observation(f, mean, count, block, {"kind": "synthetic"})
            for f, mean, count in stream_means(frames, provider)]
    return block, rows


def choose(row, index):
    result = deepcopy(row)
    candidate = None if index is None else row["candidates"][index]
    result.update(selected_candidate_index=index, state="missing" if candidate is None else "observed",
        center_xy_px=None if candidate is None else [candidate["center_x"], candidate["center_y"]],
        native_score=None if candidate is None else candidate["native_score"])
    return result


class WeakResponseReviewTests(unittest.TestCase):
    def test_nonmaximum_selection_and_nonempty_abstention_keep_original_pool(self):
        block, original = fixture()
        selected = [choose(row, 0 if position == 0 else None) for position, row in enumerate(original)]
        before = deepcopy((block, original, selected))
        report = review.score_block(block, selected, baseline=original,
                                    expected_pools=[r["candidates"] for r in original])
        self.assertEqual((report["summary"]["matched"], report["summary"]["missing"]), (1, 1))
        self.assertEqual(len(selected[1]["candidates"]), 2)
        self.assertEqual((block, original, selected), before)
        self.assertIsNone(report["human_visual_acceptance"])

    def test_provenance_point_pool_and_failed_record_rejections(self):
        block, original = fixture()
        for field, value in (("source_pts_ticks", 1), ("source_png", {"path": "wrong"}),
                             ("mean_heatmap_sha256", "b" * 64), ("temporal_contributions", 1),
                             ("center_xy_px", [1, 1]), ("inference_status", "failed"),
                             ("point_origin", "inferred"), ("selected_candidate_index", True)):
            changed = deepcopy(original)
            changed[1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                review.validate_observations(block, changed, baseline=original)
        changed = deepcopy(original)
        changed[0]["candidates"][0]["native_score"] = float("nan")
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            review.validate_observations(block, changed)
        changed = deepcopy(original)
        changed[0]["candidates"][0]["native_score"] = .6
        with self.assertRaisesRegex(ValueError, "extracted"):
            review.validate_observations(block, changed, expected_pools=[r["candidates"] for r in original])

    def test_protected_state_and_range_rejected(self):
        block, original = fixture()
        for mode in ("state", "range", "authorized"):
            changed = deepcopy(block)
            if mode == "state":
                changed["frames"][1]["state"] = "withheld"
            elif mode == "range":
                changed["protected_ranges"] = [[101, 101]]
            else:
                changed["protected_evaluation_authorized"] = True
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                review.score_block(changed, original)

    def test_nonpositive_response_and_selected_outside_source_are_rejected(self):
        block, original = fixture()
        for value in (0, -0.1):
            changed = deepcopy(original)
            changed[0]["candidates"][0]["native_score"] = value
            with self.subTest(mass=value), self.assertRaisesRegex(ValueError, "positive"):
                review.validate_observations(block, changed)
        for x, y, flag in ((64, 12, True), (20, 36, True), (-1, 12, True), (20, 12, False)):
            changed = deepcopy(original)
            changed[0]["candidates"][0].update(center_x=x, center_y=y, in_source_bounds=flag)
            changed[0] = choose(changed[0], 0)
            with self.subTest(point=(x, y, flag)), self.assertRaisesRegex(ValueError, "outside source"):
                review.validate_observations(block, changed)

    def test_unknown_references_censoring_and_native_intervals_preserved(self):
        block, original = fixture()
        report = review.score_block(block, original)
        self.assertEqual(report["summary"]["unscored"], 2)
        self.assertEqual(report["summary"]["certain_hidden_emitted_points"], 0)
        self.assertEqual(report["summary"]["uncertain_hidden_emitted_points"], 1)
        self.assertEqual(report["frame_results"][0]["boundary_before"], "exposure_subset_boundary")
        self.assertEqual(report["frame_results"][-1]["boundary_after"], "exposure_subset_boundary")
        self.assertEqual([r["duration_ticks"] for r in report["frame_results"]], [1440, 1530, 1440, 1530])
        self.assertEqual(report["summary"]["wrong_objects"]["gate"]["status"], "inconclusive")

    @unittest.skipUnless(REAL_INPUT.exists(), "Captured permitted cosine-nine records unavailable")
    def test_all_actual_native_scores_equal_saved_producer_scores(self):
        inputs = json.loads(REAL_INPUT.read_text())
        self.assertEqual(len(inputs["blocks"]), 8)
        self.assertEqual(sum(len(e["block"]["frames"]) for e in inputs["blocks"]), 3662)
        for entry in inputs["blocks"]:
            link = entry["provenance"]["candidate_records"]
            path = ROOT / link["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), link["sha256"])
            produced = json.loads(path.read_text())
            self.assertEqual(entry["candidate_observations"], produced["observations"])
            actual = review.score_block(entry["block"], produced["observations"], baseline=produced["observations"])
            with self.subTest(block=entry["block"]["block_id"]):
                self.assertEqual(actual, produced["score"])

    def test_module_does_not_import_model_runtime(self):
        result = subprocess.run([sys.executable, "-B", "-c",
            "import sys; from src.ball_tracking import weak_response_review; assert 'torch' not in sys.modules"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_compact_choices_require_same_full_pool_and_preserve_original_indices(self):
        _, original = fixture()
        for index in (None, 0, 1):
            row = choose(original[0], index)
            compact = review.compact_observation(row)
            self.assertNotIn("candidates", compact)
            self.assertEqual(compact["selected_candidate_index"], index)
            self.assertEqual(review.restore_observation(compact, row["candidates"]), row)
            wrong_pool = deepcopy(row["candidates"])
            wrong_pool[0]["native_score"] += .01
            with self.assertRaisesRegex(ValueError, "binding"):
                review.restore_observation(compact, wrong_pool)
            changed = deepcopy(compact)
            changed["center_xy_px"] = [0, 0]
            with self.assertRaises(ValueError):
                review.restore_observation(changed, row["candidates"])

    def test_source_verification_permits_only_exact_declared_projection(self):
        block, original = fixture()
        for row in original:
            for index, candidate in enumerate(row["candidates"]):
                candidate["original_index"] = index if index == 0 else None
                candidate["diagnostic_only_extra"] = "retained in source"
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "pools.jsonl"
            records = [{"block_id": block["block_id"], "width_px": 64, "height_px": 36,
                **{key: row[key] for key in ("source_frame_index", "source_pts_ticks", "time_base", "mean_heatmap_sha256", "candidates")}}
                for row in original]
            path.write_text("".join(json.dumps(row) + "\n" for row in records))
            projected = deepcopy(original)
            for row in projected:
                row["candidates"] = [{key: row["candidates"][0][key] for key in review.SELECTOR_FIELDS}]
            entry = {"block": block, "candidate_observations": projected,
                     "candidate_pool_source": review.binding(root, path), "candidate_pool_policy": "native_only",
                     "candidate_pool_projection": list(review.SELECTOR_FIELDS)}
            review.verify_pool_source(root, entry)
            bad = deepcopy(entry)
            bad["candidate_pool_projection"] = ["center_x", "center_y"]
            with self.assertRaisesRegex(ValueError, "projection"):
                review.verify_pool_source(root, bad)
            bad = deepcopy(entry)
            bad["candidate_observations"][0]["candidates"][0]["center_x"] += 1
            with self.assertRaisesRegex(ValueError, "Materialized"):
                review.verify_pool_source(root, bad)

    @unittest.skipUnless(shutil.which("ffprobe"), "Native encoded review requires ffprobe")
    def test_actual_native_render_preserves_nonmaximum_choice_null_and_final(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            block, original = fixture()
            for offset, (frame, row) in enumerate(zip(block["frames"], original, strict=True)):
                rgb = np.full((36, 64, 3), [20 + offset * 30, 80, 160], np.uint8)
                path = root / f"frame_{offset}.png"
                Image.fromarray(rgb).save(path)
                frame["png"] = {**review.binding(root, path), "rgb_sha256": hashlib.sha256(rgb.tobytes()).hexdigest()}
                row["source_png"] = frame["png"]
            selected = [choose(row, 0 if i != 1 else None) for i, row in enumerate(original)]
            pool_path = root / "pools.jsonl"
            pool_rows = [{"block_id": block["block_id"], "width_px": 64, "height_px": 36,
                **{key: row[key] for key in ("source_frame_index", "source_pts_ticks", "time_base", "mean_heatmap_sha256", "candidates")}}
                for row in selected]
            pool_path.write_text("".join(json.dumps(row) + "\n" for row in pool_rows))
            entries = [{"block": block, "baseline_observations": original, "candidate_observations": selected,
                        "expected_pools": [r["candidates"] for r in original],
                        "candidate_pool_source": review.binding(root, pool_path)}]
            result = review.render_review(root, entries, "data/outputs/review", provenance={"synthetic": True})
            self.assertEqual(result["native_frames"], 4)
            saved = result["blocks"][0]
            self.assertEqual((saved["actual_final_native_frame"], saved["actual_final_duration_ticks"]), (103, 1530))
            self.assertEqual(saved["total_duration_ticks"], 5940)
            self.assertEqual(saved["added_final_hold_ticks"], 0)
            self.assertTrue(saved["all_decoded_native_keys_verified"])
            records = json.loads((root / saved["frame_records"]["path"]).read_text())["frames"]
            self.assertTrue(saved["candidate_pools_duplicated_in_review"] is False)
            self.assertTrue(all("candidates" not in r["candidate_observation"] for r in records))
            self.assertEqual([review.restore_observation(r["candidate_observation"], row["candidates"])
                              for r, row in zip(records, selected, strict=True)], selected)
            self.assertEqual([r["encoded_pts_ticks"] for r in records], [0, 1440, 2970, 4410])
            with self.assertRaisesRegex(ValueError, "fresh"):
                review.render_review(root, entries, "data/outputs/review")


if __name__ == "__main__":
    unittest.main()
