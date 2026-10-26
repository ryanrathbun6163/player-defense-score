"""Telemetry rejection and real owned-process-tree containment, with no GPU job."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import contextmanager

from src.ball_tracking.gpu_supervision import FIELDS, GPU, OwnedJob, parse_sample, stop_reason


class TelemetryTests(unittest.TestCase):
    def test_actual_shape_and_stop_conditions(self):
        # Same nvidia-smi fields as the actual local query; thermal flags are explicit.
        values = parse_sample(", ".join([GPU, "42", "43", "2", "1", "1802", "12227", "12.52", "250", "0", "Not Active", "Not Active", "Not Active"]))
        self.assertEqual(set(values), set(FIELDS))
        self.assertIsNone(stop_reason(values))
        self.assertEqual(stop_reason({**values, "temperature.gpu": "80"}), "operational_temperature_stop_at_80C")
        self.assertIn("thermal", stop_reason({**values, "clocks_event_reasons.hw_thermal_slowdown": "Active"}))

    def test_invalid_telemetry(self):
        for text in ("", "a,b", ",".join(["wrong"] * len(FIELDS))):
            with self.assertRaises(ValueError):
                parse_sample(text)


@unittest.skipUnless(os.name == "nt", "Windows job object integration")
class OwnedJobTests(unittest.TestCase):
    @contextmanager
    def evidence_folder(self):
        # Preserve process-test evidence. Job accounting can reach zero before
        # Windows finishes closing inherited file handles after termination.
        folder = Path(tempfile.mkdtemp(prefix="gpu_job_test_", dir="data/outputs/t")).resolve()
        self.assertTrue(folder.is_relative_to((Path.cwd() / "data/outputs/t").resolve()))
        yield folder

    def wait(self, job, seconds=10):
        end = time.monotonic() + seconds
        while job.active() and time.monotonic() < end:
            time.sleep(.05)
        self.assertEqual(job.active(), 0)

    def test_success_and_descendant_capture(self):
        with self.evidence_folder() as tmp:
            folder = Path(tmp).resolve()
            marker = folder / "child.json"
            child = "import os,json,pathlib; pathlib.Path(" + repr(str(marker)) + ").write_text(json.dumps({'pid':os.getpid()}))"
            code = "import subprocess,sys; subprocess.run([sys.executable,'-B','-c'," + repr(child) + "],check=True)"
            with (folder / "log").open("wb") as log:
                job = OwnedJob([sys.executable, "-B", "-c", code], Path.cwd(), log)
                try:
                    self.wait(job)
                    self.assertEqual(job.exit_code(), 0)
                    self.assertGreater(json.loads(marker.read_text())["pid"], 0)
                finally:
                    job.close()

    def test_terminate_owned_descendant_after_launcher_exits(self):
        with self.evidence_folder() as tmp:
            folder = Path(tmp).resolve()
            marker = folder / "started"
            child = "import pathlib,time; pathlib.Path(" + repr(str(marker)) + ").write_text('yes'); time.sleep(60)"
            code = "import subprocess,sys; subprocess.Popen([sys.executable,'-B','-c'," + repr(child) + "])"
            with (folder / "log").open("wb") as log:
                job = OwnedJob([sys.executable, "-B", "-c", code], Path.cwd(), log)
                try:
                    end = time.monotonic() + 10
                    while not marker.exists() and time.monotonic() < end:
                        time.sleep(.05)
                    self.assertTrue(marker.exists())
                    self.assertGreater(job.active(), 0)
                    job.terminate()
                    self.wait(job)
                finally:
                    job.close()


if __name__ == "__main__":
    unittest.main()
