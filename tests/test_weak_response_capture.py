"""Producer-derived transport checks for the bounded HOU raw-map capture."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from src.ball_tracking import weak_response_capture as capture


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="weak_capture_")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def test_metadata_import_has_no_ml_runtime(self):
        code = ("import sys; from src.ball_tracking import weak_response_capture; "
                "assert not {'torch','cv2','numpy'} & set(sys.modules)")
        result = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_actual_producer_stream_and_row_transport(self):
        from src.ball_tracking import wasb_resolution as producer
        block = {"block_id": "synthetic", "time_base": "1/90000",
                 "source_video": {"width_px": 1920, "height_px": 1080}, "frames": []}
        pts = 90000
        for i, duration in enumerate([1440, 1530, 1440, 1530, 1530]):
            block["frames"].append({"source_frame_index": 20 + i, "source_pts_ticks": pts,
                                   "duration_ticks": duration, "png": {"path": f"frame{i}.png"}})
            pts += duration
        values = []
        for start in range(3):
            array = np.zeros((3, 432, 768), dtype=np.float32)
            for channel in range(3):
                array[channel, 100, 100 + start + channel] = np.float32(.6 + start / 10)
            values.append(array)
        segment = {"kind": "fixed_checkpoint_validation", "source_frame_range_inclusive": [20, 24]}
        # Independent original producer: explicit ascending additions, no capture helper.
        expected, means = [], []
        for offset, frame in enumerate(block["frames"]):
            terms = [values[start][offset - start] for start in range(3) if start <= offset < start + 3]
            total = np.zeros((432, 768), dtype=np.float32)
            for term in terms:
                total += term
            mean = total / np.float32(len(terms))
            means.append(mean)
            expected.append(producer.select_observation(frame, mean, len(terms), block, segment))
        calls = []

        def provide(frames):
            calls.append([f["source_frame_index"] for f in frames])
            return values[frames[0]["source_frame_index"] - 20]

        rows, count = capture.capture_block(block, expected, self.folder / "means.npy", provide)
        self.assertEqual(count, 3)
        self.assertEqual(calls, [[20, 21, 22], [21, 22, 23], [22, 23, 24]])
        self.assertEqual(rows, expected)
        np.testing.assert_array_equal(np.load(self.folder / "means.npy"), means)
        bad = deepcopy(expected)
        bad[2]["mean_heatmap_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Regenerated"):
            capture.capture_block(block, bad, self.folder / "bad.npy", provide)
        self.assertTrue((self.folder / "bad.npy").exists())

    def test_observation_transport_drift_rejected(self):
        paired_path = capture.ROOT / capture.PAIRED
        if not paired_path.exists():
            self.skipTest("Authorized captured control not available")
        entry = next(e for e in capture.read(paired_path)["blocks"] if e["block"]["block_id"] == capture.HOU[0])
        capture.validate_context(entry)
        for field, value in [("source_pts_ticks", -1), ("source_frame_index", -1), ("inference_status", "failed")]:
            bad = deepcopy(entry)
            bad["candidate_observations"][0][field] = value
            with self.assertRaises(ValueError):
                capture.validate_context(bad)

    def test_protected_or_changed_role_rejected(self):
        paired_path = capture.ROOT / capture.PAIRED
        if not paired_path.exists():
            self.skipTest("Authorized captured control not available")
        entry = next(e for e in capture.read(paired_path)["blocks"] if e["block"]["block_id"] == capture.HOU[0])
        for change in ("protected", "role"):
            bad = deepcopy(entry)
            if change == "protected":
                bad["block"]["frames"][0]["state"] = "protected"
            else:
                bad["block"]["role"] = "training"
            with self.assertRaises(ValueError):
                capture.validate_context(bad)

    def test_binding_detects_changed_bytes_and_escape(self):
        path = self.folder / "bound.txt"
        path.write_bytes(b"original")
        link = capture.bind(self.folder, path)
        self.assertEqual(capture.bound(self.folder, link), path)
        path.write_bytes(b"modified")
        with self.assertRaises(ValueError):
            capture.bound(self.folder, link)
        with self.assertRaises(ValueError):
            capture.bound(self.folder, {**link, "path": "../outside.txt"})

    def test_write_once_preserves_existing_record(self):
        path = self.folder / "record.json"
        capture.write_once(path, {"first": True})
        with self.assertRaises(FileExistsError):
            capture.write_once(path, {"first": False})
        self.assertEqual(json.loads(path.read_text()), {"first": True})

    def test_capture_rejects_missing_supervisor_before_ml_import(self):
        from src.ball_tracking import continuation_owned_guard
        with patch.object(continuation_owned_guard, "verify_owned_worker", side_effect=ValueError("No owned job")):
            with self.assertRaisesRegex(ValueError, "No owned job"):
                capture.capture(self.folder, "missing.json", "monitor", ["--run"])


if __name__ == "__main__":
    unittest.main()
