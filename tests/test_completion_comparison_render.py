"""Synthetic CPU transport checks; no protected images or real model execution."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np
from PIL import Image

from src.ball_tracking import completion_comparison_render as render
from src.ball_tracking import completion_scoring as scoring
from src.ball_tracking.annotations import FrameAnnotation
from src.ball_tracking.nba_action_observation import select_observation


class ComparisonRenderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        csv = self.root / "players.csv"
        csv.write_text("frame_index,timestamp_sec,player_id,floor_x,floor_y\n0,0,p1,10,20\n2,0.08,PROTECTED,12,20\n")
        frames = []
        for f in range(3):
            row = {"source_frame_index": f, "source_pts_ticks": (f + 1) * 512,
                   "duration_ticks": 512, "state": "permitted" if f < 2 else "withheld"}
            if f < 2:
                rgb = np.full((36, 64, 3), [30 + f * 40, 100, 180], np.uint8)
                path = self.root / f"source{f}.png"
                Image.fromarray(rgb).save(path)
                annotation = {
                    "frame_index": f, "annotation_status": "labeled",
                    "visibility": "fully_visible" if f == 0 else "indeterminate",
                    "absence_reason": None,
                    "game_ball_identity_certainty": "certain" if f == 0 else "ambiguous",
                    "geometry": {"center_xy_px": [20, 12], "source": "observed_complete_ball_center",
                                 "uncertainty_radius_px": 2} if f == 0 else None,
                    "localization_eligible": f == 0, "difficulty_tags": [],
                    "notes": "Synthetic transport fixture; no real ball reference."}
                bounds = type("Bounds", (), {"width_px": 64, "height_px": 36})()
                row.update(png={**render.binding(self.root, path), "rgb_sha256": hashlib.sha256(rgb.tobytes()).hexdigest()},
                           annotation=FrameAnnotation.from_mapping(annotation, f, bounds).to_dict(),
                           block_id="synthetic_segment", reference_role="post_selection_evaluation_only")
            frames.append(row)
        self.timeline = {"possession_id": "possession_001", "source_video": {"frame_count": 3, "width_px": 64, "height_px": 36},
                         "time_base": "1/12800", "protected_ranges": [[2, 2]], "frames": frames,
                         "player_context": render.binding(self.root, csv)}
        self.comparison = {"possession_id": "possession_001"}
        for label in ("baseline", "selected"):
            self.set_observations(label, [None, None])

    def set_observations(self, label, points):
        # Use both actual producers, then serialize exactly as the renderer's
        # JSON inputs do. No manually copied scoring-row fixture is involved.
        observations = []
        for frame, point in zip(self.timeline["frames"][:2], points, strict=True):
            heatmap = np.zeros((288, 512), dtype=np.float32)
            if point is not None:
                heatmap[point[1] * 8, point[0] * 8] = .75
            observations.append(select_observation(frame, heatmap, 1, self.timeline, {"kind": "live_action"}))
        self.comparison[label + "_observations"] = json.loads(json.dumps(observations))
        self.comparison[label + "_metrics"] = json.loads(json.dumps(scoring.score_timeline(self.timeline, observations)))

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is required for emitted transport check")
    def test_emitted_all_frames_and_protected_actual_final_without_source_read(self):
        self.set_observations("baseline", [(20, 12), None])
        self.set_observations("selected", [(31, 12), None])
        self.assertEqual([row["outcome"] for row in self.comparison["baseline_metrics"]["frame_results"]],
                         ["matched", "unscored", "withheld"])
        self.assertEqual([row["outcome"] for row in self.comparison["selected_metrics"]["frame_results"]],
                         ["wrong", "unscored", "withheld"])
        opened = []
        original = render.source_rgb
        def guarded(root, timeline, row):
            if row["state"] == "withheld":
                self.assertNotIn("png", row)
            else:
                opened.append(row["source_frame_index"])
            return original(root, timeline, row)
        with patch.object(render, "source_rgb", side_effect=guarded):
            result = render.render_possession(self.root, self.timeline, self.comparison, self.root / "data/outputs/review")
        self.assertEqual(result["decoded_frames"], 3)
        self.assertEqual(result["actual_final_native_frame"], 2)
        self.assertEqual(result["protected_black_frames"], 1)
        self.assertEqual(opened, [0, 1, 0, 1])
        records = json.loads((self.root / result["frame_records"]["path"]).read_text())
        self.assertEqual(records["comparison"], self.comparison)
        self.assertEqual(records["comparison"]["selected_observations"][0]["center_xy_px"], [31, 12])
        final = cv2.imread(str(self.root / result["actual_final_frame"]["path"]))
        self.assertLessEqual(int(final[render.TOP + 8:render.TOP + render.PANEL_H - 8].max()), 4)
        self.assertNotIn(2, render.read_players(self.root, self.timeline))
        with self.assertRaises(FileExistsError):
            render.render_possession(self.root, self.timeline, self.comparison, self.root / "data/outputs/review")

    def test_native_timing_and_completed_selected_provenance_are_required(self):
        changed = copy.deepcopy(self.timeline)
        changed["frames"][1]["duration_ticks"] = 513
        with self.assertRaisesRegex(ValueError, "25fps"):
            render.validate_timeline(changed, self.comparison)
        changed = copy.deepcopy(self.comparison)
        changed["selected_observations"][0]["source_pts_ticks"] += 512
        with self.assertRaisesRegex(ValueError, "native timing"):
            render.validate_timeline(self.timeline, changed)
        changed = copy.deepcopy(self.comparison)
        changed["selected_metrics"]["frame_results"][0]["duration_ticks"] += 1
        with self.assertRaisesRegex(ValueError, "Scoring native timing"):
            render.validate_timeline(self.timeline, changed)
        changed = copy.deepcopy(self.comparison)
        changed["selected_observations"][0]["source_png"]["sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "source image binding"):
            render.validate_timeline(self.timeline, changed)
        package_binding = {"path": "package.json", "sha256": "package"}
        checkpoint = {"path": "selected.pth", "sha256": "selected"}
        package = {"schema_version": "completion_evaluation_package/v0.1", "execution_ready": True,
                   "selected_method": {"checkpoint": checkpoint}}
        evaluation = {"schema_version": "completion_evaluation/v0.1", "status": "completed", "package": package_binding,
                      "selected_checkpoint": checkpoint, "protected_evaluation_authorized": False}
        render.validate_evaluation(package, evaluation, package_binding)
        for field, value in [("status", "running"), ("package", {}), ("selected_checkpoint", {}), ("protected_evaluation_authorized", True)]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                render.validate_evaluation(package, {**evaluation, field: value}, package_binding)
        with self.assertRaisesRegex(ValueError, "not ready"):
            render.validate_evaluation({**package, "execution_ready": False}, evaluation, package_binding)

    def test_out_of_image_points_preserve_coordinates_without_cross_panel_drawings(self):
        row = self.timeline["frames"][0]
        rgb = render.source_rgb(self.root, self.timeline, row)
        maps = render.validate_timeline(self.timeline, self.comparison)
        original = render.canvas(rgb, self.timeline, row, maps, [])
        changed = copy.deepcopy(self.comparison)
        changed["baseline_observations"][0].update(state="observed", center_xy_px=[10000, -400])
        changed["baseline_metrics"] = scoring.score_timeline(self.timeline, changed["baseline_observations"])
        mapped = render.validate_timeline(self.timeline, changed)
        result = render.canvas(rgb, self.timeline, row, mapped, [{"player_id": "outside", "floor_xy_px": [-900, 200]}])
        self.assertTrue(np.array_equal(original[render.TOP:render.TOP + render.PANEL_H], result[render.TOP:render.TOP + render.PANEL_H]))
        self.assertEqual(mapped["baseline"][0][0]["center_xy_px"], [10000, -400])

    def test_protected_candidate_leak_and_failed_inference_are_rejected(self):
        frame = {**self.timeline["frames"][2], "png": None}
        withheld = select_observation(frame, None, 0, self.timeline, {"kind": "withheld"})
        changed = copy.deepcopy(self.comparison)
        changed["selected_observations"].append(withheld)
        render.validate_timeline(self.timeline, changed)
        withheld["candidates"] = [{"center_x": 10, "center_y": 20}]
        with self.assertRaisesRegex(ValueError, "Protected observation"):
            render.validate_timeline(self.timeline, changed)
        changed = copy.deepcopy(self.comparison)
        changed["selected_observations"][0]["inference_status"] = "failed"
        with self.assertRaisesRegex(ValueError, "Only completed inference"):
            render.validate_timeline(self.timeline, changed)


if __name__ == "__main__":
    unittest.main()
