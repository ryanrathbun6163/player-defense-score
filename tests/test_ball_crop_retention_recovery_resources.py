"""Synthetic recovery regressions for membership-stable live byte accounting."""
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.ball_tracking import crop_retention_resources as resources


ROOT = Path(__file__).resolve().parents[1]
STREAM_WORKER = r'''
import json, os, time
from pathlib import Path
from src.ball_tracking.crop_retention_resources import wait_for_supervisor
wait_for_supervisor()
root = Path(os.environ["SYNTHETIC_RESOURCE_ROOT"])
(root / "stream_started.json").write_text(json.dumps({"pid": os.getpid()}))
pending = root / "stream.json.incomplete"
started, chunks = time.monotonic(), 0
duration = float(os.environ["SYNTHETIC_WRITE_SECONDS"])
with pending.open("x", encoding="utf-8") as stream:
    stream.write('{"rows":[')
    while time.monotonic() - started < duration:
        if chunks:
            stream.write(",")
        json.dump({"i": chunks, "payload": "x" * 4096}, stream)
        stream.flush()
        if chunks % 32 == 0:
            print("synthetic streaming progress", flush=True)
        chunks += 1
        time.sleep(.002)
    stream.write("]}")
pending.rename(root / "stream.json")
Path(os.environ["BALL_RETENTION_RESULT_PATH"]).write_text(json.dumps(
    {"synthetic": True, "duration_seconds": time.monotonic()-started, "chunks": chunks}))
'''


def limits(**changes):
    return {"maximum_worker_memory_bytes": 256*1024*1024,
            "maximum_total_new_output_bytes": 8*1024*1024, "minimum_free_disk_bytes": 0,
            "maximum_seconds_per_unit": 5.0, "maximum_cumulative_seconds": 20.0, **changes}


def stream(root, contract, duration=1.1):
    return resources.run_supervised(root, "synthetic_stream", [sys.executable, "-B", "-c", STREAM_WORKER],
        contract, cwd=ROOT, selection_unit=False, require_result=True, poll_seconds=.05,
        env={"SYNTHETIC_RESOURCE_ROOT": str(root), "SYNTHETIC_WRITE_SECONDS": str(duration)})


class RecoveryInventoryTests(unittest.TestCase):
    def test_growth_shrink_and_modification_time_changes_keep_largest_observed_size(self):
        for sizes in ((23, 31), (31, 23), (31, 31)):
            with self.subTest(sizes=sizes):
                observations = [SimpleNamespace(st_dev=1, st_ino=7, st_size=size, st_mtime_ns=mtime)
                                for size, mtime in zip(sizes, (42, 99))]
                with patch.object(resources.os, "walk", return_value=[("synthetic_root", [], ["evidence.json"])]), \
                        patch.object(Path, "stat", side_effect=observations), \
                        patch.object(resources.time, "monotonic", return_value=0):
                    self.assertEqual(resources.output_bytes("synthetic_root"), max(sizes))

    def test_hard_link_multiplicity_and_largest_size_are_preserved(self):
        observations = [SimpleNamespace(st_dev=1, st_ino=7, st_size=size) for size in (10, 20, 30, 25)]
        with patch.object(resources.os, "walk", return_value=[("synthetic_root", [], ["first", "second"])]), \
                patch.object(Path, "stat", side_effect=observations), \
                patch.object(resources.time, "monotonic", return_value=0):
            self.assertEqual(resources.output_bytes("synthetic_root"), 60)

    def test_new_path_or_increased_multiplicity_is_charged_in_second_scan(self):
        for hard_link in (True, False):
            with self.subTest(hard_link=hard_link):
                scans = [[("synthetic_root", [], names)] for names in
                         (["first"], ["first", "second"])]
                identities = [7, 7, 7 if hard_link else 8]
                observations = [SimpleNamespace(st_dev=1, st_ino=i, st_size=23) for i in identities]
                with patch.object(resources.os, "walk", side_effect=scans) as walk, \
                        patch.object(Path, "stat", side_effect=observations), \
                        patch.object(resources.time, "monotonic", return_value=0):
                    self.assertEqual(resources.output_bytes("synthetic_root"), 46)
                self.assertEqual(walk.call_count, 2)

    def test_actual_file_and_subtree_renames_preserve_all_bytes(self):
        for rename_directory in (False, True):
            with self.subTest(rename_directory=rename_directory), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                pending = root / "pending"
                pending.mkdir()
                (pending / "first.bin").write_bytes(b"x" * 23)
                (pending / "second.bin").write_bytes(b"y" * 31)
                walk = resources.os.walk
                scans = []
                def publishing_walk(*args, **kwargs):
                    yield from walk(*args, **kwargs)
                    scans.append(True)
                    if len(scans) == 1:
                        if rename_directory:
                            pending.rename(root / "published")
                        else:
                            (pending / "first.bin").rename(pending / "published.bin")
                with patch.object(resources.os, "walk", side_effect=publishing_walk):
                    self.assertEqual(resources.output_bytes(root), 54)
                self.assertEqual(len(scans), 2)

    def test_actual_hard_links_keep_directory_entry_accounting(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "original"
            original.write_bytes(b"x" * 23)
            os.link(original, root / "second_link")
            self.assertEqual(resources.output_bytes(root), 46)

    def test_unresolved_missing_file_expires_without_accepting_partial_inventory(self):
        clock = SimpleNamespace(now=0)
        def missing_stat():
            clock.now += .2
            raise FileNotFoundError("synthetic publication race")
        with patch.object(resources.os, "walk", return_value=[("synthetic_root", [], ["missing"])]), \
                patch.object(Path, "stat", side_effect=missing_stat), \
                patch.object(resources.time, "monotonic", side_effect=lambda: clock.now):
            with self.assertRaisesRegex(resources.ResourceLimitError, "did not stabilize"):
                resources.output_bytes("synthetic_root")

    def test_deadline_is_enforced_during_stat_and_after_final_walk(self):
        for blocked_at in ("stat", "final_walk"):
            with self.subTest(blocked_at=blocked_at):
                clock = SimpleNamespace(now=0, scans=0)
                def scanned(*args, **kwargs):
                    clock.scans += 1
                    yield ("synthetic_root", [], ["evidence.json"])
                    if blocked_at == "final_walk" and clock.scans == 2:
                        clock.now = .5
                def stat():
                    if blocked_at == "stat":
                        clock.now = .5
                    return SimpleNamespace(st_dev=1, st_ino=7, st_size=23)
                with patch.object(resources.os, "walk", side_effect=scanned), \
                        patch.object(Path, "stat", side_effect=stat), \
                        patch.object(resources.time, "monotonic", side_effect=lambda: clock.now):
                    with self.assertRaisesRegex(resources.ResourceLimitError, "did not stabilize"):
                        resources.output_bytes("synthetic_root")


class RecoveryStreamingTests(unittest.TestCase):
    def test_continuous_json_writer_over_half_second_finishes_under_all_limits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract = limits()
            preserved = root / "prior_incomplete.json"
            preserved.write_bytes(b'{"historical_partial":')
            sampled_while_writing = []
            original = resources.output_bytes
            def measure(target):
                measured = original(target)
                if (root / "stream.json.incomplete").exists():
                    sampled_while_writing.append(measured)
                return measured
            with patch.object(resources, "output_bytes", side_effect=measure):
                receipt = stream(root, contract)
            completed = json.loads((root / receipt["worker_result"]["path"]).read_text())
            rows = json.loads((root / "stream.json").read_text())["rows"]
            self.assertGreater(completed["duration_seconds"], .5)
            self.assertEqual(len(rows), completed["chunks"])
            self.assertTrue(all(row["i"] == i and len(row["payload"]) == 4096 for i, row in enumerate(rows)))
            self.assertGreater(len(sampled_while_writing), 3)
            self.assertGreater(max(sampled_while_writing), min(sampled_while_writing))
            self.assertTrue(receipt["success"])
            self.assertLessEqual(receipt["maximum_monitor_interval_seconds"], 1)
            self.assertEqual(receipt["output_overshoot_bytes"], 0)
            self.assertEqual(receipt["final_accounting_error"], None)
            self.assertGreater((root / receipt["log_path"]).stat().st_size, 0)
            self.assertEqual(preserved.read_bytes(), b'{"historical_partial":')
            self.assertFalse((root / "stream.json.incomplete").exists())
            self.assertEqual(resources.output_bytes(root), sum(p.stat().st_size for p in root.rglob("*") if p.is_file()))

    def test_continuous_writer_crossing_byte_cap_is_killed_and_partial_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract = limits(maximum_total_new_output_bytes=128*1024)
            preserved = root / "previous_completed.json"
            preserved.write_bytes(b'{"completed":true}')
            with self.assertRaisesRegex(resources.ResourceLimitError, "exceeded: output_bytes"):
                stream(root, contract, duration=30)
            journal = resources.BudgetJournal(root, contract)
            receipt = journal.events[-1]
            self.assertEqual(receipt["kind"], "finished")
            self.assertFalse(receipt["success"])
            self.assertIsNone(receipt["worker_result"])
            self.assertGreater(receipt["output_overshoot_bytes"], 0)
            self.assertGreater(receipt["maximum_output_bytes"], contract["maximum_total_new_output_bytes"])
            self.assertTrue((root / "stream.json.incomplete").is_file())
            self.assertFalse((root / "stream.json").exists())
            pid = json.loads((root / "stream_started.json").read_text())["pid"]
            self.assertFalse(resources._alive(pid))
            self.assertEqual(preserved.read_bytes(), b'{"completed":true}')
            self.assertEqual(journal.consumed(), receipt["elapsed_seconds"])


if __name__ == "__main__":
    unittest.main()
