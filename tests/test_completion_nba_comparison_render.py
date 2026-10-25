"""Synthetic CPU encoding and actual observation/receipt transport checks."""
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

from src.ball_tracking import completion_nba_comparison_render as render
from src.ball_tracking.annotations import FrameAnnotation
from src.ball_tracking.completion_training_runtime import atomic_write_once, binding
from src.ball_tracking.nba_action_observation import select_observation, stream_means
from src.ball_tracking.wasb_experiment import canonical


class NbaComparisonRenderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.block = {"block_id": "synthetic_nba:100-103", "candidate_id": "synthetic_nba", "domain": "nba",
            "game_id": "synthetic", "role": "post_selection_evaluation_only", "time_base": "1/90000",
            "source_video": {"width_px": 64, "height_px": 36,
                             "sha256": hashlib.sha256(b"synthetic-source-no-video").hexdigest()}, "frames": []}
        pts = 900000
        bounds = type("Bounds", (), self.block["source_video"])()
        for offset, duration in enumerate((1440, 1530, 1530, 1440)):
            index = 100 + offset
            rgb = np.full((36, 64, 3), [30 + 30 * offset, 100, 180 - 20 * offset], np.uint8)
            rgb[5:20, 5 + offset:20 + offset] = [180, 80 + offset * 20, 30]
            path = self.root / f"source_{index}.png"
            Image.fromarray(rgb).save(path)
            label = {"frame_index": index, "annotation_status": "labeled",
                "visibility": "fully_visible" if offset == 0 else "not_visible" if offset == 3 else "indeterminate",
                "absence_reason": "occluded" if offset == 3 else None,
                "game_ball_identity_certainty": "certain" if offset in {0, 3} else "ambiguous",
                "geometry": {"center_xy_px": [20, 12], "source": "observed_complete_ball_center", "uncertainty_radius_px": 2}
                            if offset == 0 else None,
                "localization_eligible": offset == 0, "difficulty_tags": [], "notes": "Synthetic test reference."}
            frame = {"source_frame_index": index, "source_pts_ticks": pts, "duration_ticks": duration,
                "state": "permitted", "block_id": self.block["block_id"], "reference_role": "excluded_development",
                "png": {**binding(self.root, path), "rgb_sha256": hashlib.sha256(rgb.tobytes()).hexdigest()},
                "annotation": None if offset == 2 else FrameAnnotation.from_mapping(label, offset, bounds).to_dict()}
            self.block["frames"].append(frame)
            pts += duration
        self.baseline = self.produce([(20, 12), None, (30, 14), None])
        self.selected = self.produce([(32, 12), None, (34, 14), None])
        for frame, original in zip(self.block["frames"], self.baseline):
            frame["baseline_observation"] = {k: original[k] for k in
                ("source_frame_index", "center_xy_px", "native_score", "temporal_contributions", "state")}
            frame["baseline_observation"]["original_record"] = copy.deepcopy(original)
        self.folder = self.root / "data/outputs/nba_review"

    def produce(self, points):
        def provider(frames):
            values = []
            for frame in frames:
                mean = np.zeros((288, 512), np.float32)
                point = points[frame["source_frame_index"] - 100]
                if point is not None:
                    mean[point[1] * 8, point[0] * 8] = .75
                values.append(mean)
            return np.stack(values)
        return [select_observation(frame, mean, count, self.block, {"kind": "synthetic"})
                for frame, mean, count in stream_means(self.block["frames"], provider)]

    @unittest.skipUnless(shutil.which("ffprobe"), "ffprobe required for encoded transport verification")
    def test_vfr_packets_decoded_frames_and_actual_final_are_exact(self):
        original = copy.deepcopy(self.block)
        result = render.render_block(self.root, self.block, self.selected, self.folder, {"synthetic": True})
        self.assertEqual(result["decoded_frames"], 4)
        self.assertEqual(result["native_pts_packet_frame_duration_checks"], 4)
        self.assertEqual(result["actual_final_native_frame"], 103)
        self.assertEqual(result["actual_final_duration_ticks"], 1440)
        self.assertEqual(result["total_duration_ticks"], 5940)
        self.assertEqual(result["added_final_hold_ticks"], 0)
        self.assertTrue(result["all_decoded_native_keys_verified"])
        records = json.loads((self.root / result["frame_records"]["path"]).read_text())["frames"]
        self.assertEqual([r["encoded_pts_ticks"] for r in records], [0, 1440, 2970, 4500])
        self.assertEqual([r["encoded_duration_ticks"] for r in records], [1440, 1530, 1530, 1440])
        self.assertEqual([r["selected_observation"] for r in records], self.selected)
        self.assertIsNone(records[1]["annotation"]["geometry"])
        self.assertIsNone(records[2]["annotation"])
        self.assertEqual([r["baseline_observation"]["original_baseline_record"] for r in records], self.baseline)
        final = cv2.imread(str(self.root / result["actual_final_frame"]["path"]))
        self.assertEqual(final.shape, (720, 1280, 3))
        # normalize_block only fills its deterministic source/range metadata.
        self.assertEqual(self.block["frames"], original["frames"])
        probe = json.loads((self.root / result["encoded_probe"]["path"]).read_text())
        wrong_final = render.timing_schedule(self.block)
        wrong_final[-1] = (4500, 1500)
        with self.assertRaisesRegex(ValueError, "total interval differs"):
            render.validate_encoded_timing(probe, wrong_final, self.block["time_base"], "bt709", "bt709")
        with self.assertRaises(FileExistsError):
            render.render_block(self.root, self.block, self.selected, self.folder, {})

    def test_stale_native_binding_and_inference_failure_rejected_before_render(self):
        for field, value, message in (("source_pts_ticks", 1, "native source"),
                                      ("inference_status", "failed", "Failed or filled"),
                                      ("temporal_contributions", 3, "temporal contexts")):
            changed = copy.deepcopy(self.selected)
            changed[0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, message):
                render.render_block(self.root, self.block, changed, self.folder, {})
            self.assertFalse(self.folder.exists())
        changed = copy.deepcopy(self.selected)
        changed[0]["source_png"]["sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "native source"):
            render.render_block(self.root, self.block, changed, self.folder, {})

    def test_protected_index_and_rgb_tampering_rejected(self):
        frame = copy.deepcopy(self.block["frames"][0])
        frame["state"] = "withheld"
        with patch.object(render, "bound_path", side_effect=AssertionError("No protected read")):
            with self.assertRaisesRegex(ValueError, "Protected source"):
                render.source_rgb(self.root, self.block, frame)
            block = {**self.block, "protected_ranges": [[100, 100]]}
            with self.assertRaisesRegex(ValueError, "Protected index"):
                render.source_rgb(self.root, block, self.block["frames"][0])
        frame["state"] = "permitted"
        frame["png"]["rgb_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "RGB hash"):
            render.source_rgb(self.root, self.block, frame)

    def test_encoder_failure_preserves_started_and_failed_records(self):
        with patch.object(render, "encode_review_video", side_effect=RuntimeError("synthetic encoder failure")):
            with self.assertRaisesRegex(RuntimeError, "synthetic encoder"):
                render.render_block(self.root, self.block, self.selected, self.folder, {"synthetic": True})
        self.assertTrue((self.folder / "started.json").is_file())
        failed = json.loads((self.folder / "failed.json").read_text())
        self.assertEqual(failed["error_type"], "RuntimeError")
        self.assertFalse((self.folder / "render_receipt.json").exists())

    def record_fixture(self):
        render.timing_schedule(self.block)
        folder = self.root / "data/outputs/evaluation"
        record = {"block_id": self.block["block_id"], "block_sha256": canonical(self.block), "observations": self.selected}
        atomic_write_once(folder / "observations.json", record)
        identity = {"synthetic_actual_producer_records": True}
        receipt = {"identity": identity, "block_sha256": canonical(self.block), "record": binding(self.root, folder / "observations.json")}
        atomic_write_once(folder / "block.json", receipt)
        package = {"inference_blocks": [self.block]}
        evaluation = {"block_receipts": [binding(self.root, folder / "block.json")]}
        return package, evaluation, identity, folder

    def test_actual_block_receipt_record_and_native_observation_transport(self):
        package, evaluation, identity, folder = self.record_fixture()
        result = render.read_block_records(self.root, package, evaluation, identity)
        self.assertEqual(result[self.block["block_id"]]["observations"], self.selected)
        changed = copy.deepcopy(package)
        changed["inference_blocks"][0]["frames"][0]["duration_ticks"] += 1
        with self.assertRaisesRegex(ValueError, "Stale or duplicate"):
            render.read_block_records(self.root, changed, evaluation, identity)
        with self.assertRaisesRegex(ValueError, "method identity"):
            render.read_block_records(self.root, package, evaluation, {})
        (folder / "observations.json").write_text("{}")
        with self.assertRaises(ValueError):
            render.read_block_records(self.root, package, evaluation, identity)

    def test_failed_evaluation_never_supplies_render_inputs(self):
        path = self.root / "failed_completion.json"
        atomic_write_once(path, {"status": "failed", "protected_evaluation_authorized": False})
        with self.assertRaisesRegex(ValueError, "Completed permitted"):
            render.load_inputs(self.root, binding(self.root, path))

    def test_completed_review_rejects_stale_nested_video(self):
        render.timing_schedule(self.block)
        folder = self.root / "data/outputs/review_closure"
        folder.mkdir(parents=True)
        identity = {"synthetic_completed_review": True}
        block_result = {"candidate_id": self.block["candidate_id"], "block_id": self.block["block_id"],
            "block_sha256": canonical(self.block), "decoded_frames": 4, "native_pts_packet_frame_duration_checks": 4,
            "actual_final_native_frame": 103, "actual_final_duration_ticks": 1440, "time_base": "1/90000"}
        for name in ("video", "actual_final_frame", "frame_records", "encoded_probe", "index"):
            path = folder / name
            path.write_bytes(("synthetic artifact " + name).encode())
            block_result[name] = binding(self.root, path)
        atomic_write_once(folder / "summary.json", {"schema_version": "completion_nba_comparison_render/v0.1",
            "status": "completed", "identity": identity, "blocks": [block_result], "native_frames": 4})
        completed = {"status": "completed", "identity": identity, "summary": binding(self.root, folder / "summary.json"),
                     "index": block_result["index"]}
        self.assertEqual(render.validate_completed(self.root, completed, identity, [self.block]), completed)
        (folder / "video").write_bytes(b"changed video bytes")
        with self.assertRaises(ValueError):
            render.validate_completed(self.root, completed, identity, [self.block])


if __name__ == "__main__":
    unittest.main()
