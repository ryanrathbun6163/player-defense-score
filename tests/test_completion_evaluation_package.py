"""CPU-only producer/consumer joins and protected-band regression checks."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from src.ball_tracking.completion_evaluation_package import (
    ROLE, _baseline, _png, bind_selected_result, normalize_block, validate_timeline,
    validate_component_selection)
from src.ball_tracking.completion_training_package import Evidence

ROOT = Path(__file__).resolve().parents[1]


class EvaluationPackageTests(unittest.TestCase):
    def block(self):
        # Fixture derives from the accepted annotation producer, not hand-built geometry.
        document = json.loads((ROOT / "configs/ball_tracking/annotations/possession_001_frames_0100_0124_training_expansion_v0_1.json").read_text())
        frames = []
        for row in document["annotations"][:3]:
            index = row["frame_index"]
            saved = {"frame_index": index, "state": "missing", "center_xy_px": None,
                     "native_score": None, "contribution_count": 1}
            frames.append({"source_frame_index": index, "source_pts_ticks": 512 + index * 512,
                "duration_ticks": 512, "state": "permitted", "block_id": "test:100-102",
                "png": None, "annotation": row, "reference_role": "historical_training",
                "baseline_observation": _baseline(saved)})
        return {"block_id": "test:100-102", "role": ROLE, "domain": "nfhs", "game_id": "possession_001",
                "source_video": document["source_video"], "time_base": "1/12800",
                "protected_ranges": [[275, 349]], "frames": frames}

    def test_accepted_roles_and_native_origin_preserved(self):
        block = self.block(); original = deepcopy(block["frames"])
        result = normalize_block(block)
        self.assertEqual(result["frames"], original)
        self.assertEqual(result["range_inclusive"], [100, 102])
        self.assertEqual(result["frames"][0]["source_pts_ticks"], 51712)

    def test_bad_role_annotation_pts_context_and_protected_rejected(self):
        mutations = [lambda b: b.update(role="training"),
            lambda b: b["frames"][1].update(source_pts_ticks=9),
            lambda b: b["frames"][0]["annotation"].update(frame_index=99),
            lambda b: b["frames"][0]["baseline_observation"].update(temporal_contributions=2),
            lambda b: b.update(protected_ranges=[[100, 100]])]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                block = self.block(); mutate(block)
                with self.assertRaises(ValueError): normalize_block(block)

    def test_unlabeled_nba_context_is_not_a_reference(self):
        block = self.block(); block["domain"] = "nba"; block["source_video"].pop("fps")
        for row in block["frames"]: row["annotation"] = None
        self.assertTrue(all(f["annotation"] is None for f in normalize_block(block)["frames"]))

    def test_withheld_slots_are_metadata_only(self):
        timeline = {"source_video": {"frame_count": 2}, "protected_ranges": [[1, 1]], "frames": [
            {"source_frame_index": 0, "state": "permitted", "block_id": "a"},
            {"source_frame_index": 1, "state": "withheld", "block_id": None}]}
        validate_timeline(timeline)
        for field in ("png", "annotation", "baseline_observation", "player_records"):
            changed = deepcopy(timeline); changed["frames"][1][field] = None
            with self.assertRaises(ValueError): validate_timeline(changed)

    def test_incomplete_selected_training_result_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); path = root / "result.json"
            path.write_text(json.dumps({"schema_version": "completion_training_result/v0.1", "status": "failed"}))
            with self.assertRaises(ValueError): bind_selected_result(Evidence(root), "result.json")
            self.assertIsNone(bind_selected_result(Evidence(root), None))

    def test_missing_png_is_reported_without_source_decode(self):
        with tempfile.TemporaryDirectory() as folder:
            evidence = Evidence(folder)
            self.assertIsNone(_png(evidence, None, "segment", 100, {}, True))
            self.assertEqual(evidence.missing[0]["source_frame_index"], 100)

    def test_actual_observation_producer_transport_and_corruption(self):
        import numpy as np
        from src.ball_tracking.nba_action_observation import select_observation
        frame = {"source_frame_index": 100, "source_pts_ticks": 51712, "png": {"path": "synthetic.png"}}
        manifest = {"source_video": {"width_px": 1920, "height_px": 1080}, "time_base": "1/12800"}
        segment = {"kind": "test", "source_frame_range_inclusive": [100, 102]}
        heatmap = np.zeros((288, 512), dtype=np.float32)
        missing = select_observation(frame, heatmap, 1, manifest, segment)
        validate_component_selection(missing)
        heatmap[100:104, 100:104] = .8
        row = select_observation(frame, heatmap, 1, manifest, segment)
        validate_component_selection(row)
        self.assertEqual(_baseline(row)["original_record"], row)
        row["center_xy_px"][0] += 1
        with self.assertRaises(ValueError): validate_component_selection(row)


if __name__ == "__main__":
    unittest.main()
