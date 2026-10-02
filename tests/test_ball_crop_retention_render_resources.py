"""Synthetic rendering regressions for complete inventories with new files."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.ball_tracking import crop_retention_resources as resources


ROOT = Path(__file__).resolve().parents[1]
CREATE_WORKER = r'''
import json, os, sys, time
from pathlib import Path
from src.ball_tracking.crop_retention_resources import wait_for_supervisor
wait_for_supervisor()
root = Path(os.environ["SYNTHETIC_RESOURCE_ROOT"])
mode = sys.argv[1]
(root / "started.json").write_text(json.dumps({"pid": os.getpid()}))
started, index = time.monotonic(), 0
while time.monotonic() - started < float(os.environ["SYNTHETIC_WRITE_SECONDS"]):
    target = root / ("f" + str(index))
    size = 256 if mode == "under_cap" else 32768
    if mode == "hardlink":
        if index == 0:
            (root / "original").write_bytes(b"x" * size)
        os.link(root / "original", target)
    elif mode == "move":
        pending = root / ("p" + str(index))
        pending.mkdir()
        (pending / "payload").write_bytes(b"x" * size)
        pending.rename(target)
    elif mode == "replace":
        target.write_bytes(b"old")
        pending = root / ("p" + str(index))
        pending.write_bytes(b"x" * size)
        pending.replace(target)
    elif mode == "delete":
        discarded = root / ("d" + str(index))
        discarded.write_bytes(b"transient")
        discarded.unlink()
        target.write_bytes(b"x" * size)
    else:
        target.write_bytes(b"x" * size)
    index += 1
    time.sleep(.004)
Path(os.environ["BALL_RETENTION_RESULT_PATH"]).write_text(json.dumps(
    {"synthetic": True, "duration_seconds": time.monotonic()-started, "files_created": index}))
'''


def limits(**changes):
    return {"maximum_worker_memory_bytes": 256 * 1024 * 1024,
            "maximum_total_new_output_bytes": 8 * 1024 * 1024,
            "minimum_free_disk_bytes": 0, "maximum_seconds_per_unit": 5.0,
            "maximum_cumulative_seconds": 20.0, **changes}


def run_creator(root, mode, contract, duration=1.1):
    return resources.run_supervised(root, "synthetic_creation_" + mode,
        [sys.executable, "-B", "-c", CREATE_WORKER, mode], contract, cwd=ROOT,
        selection_unit=True, require_result=True, poll_seconds=.05,
        env={"SYNTHETIC_RESOURCE_ROOT": str(root), "SYNTHETIC_WRITE_SECONDS": str(duration)})


def scripted_measurement(states):
    """Supply independently specified observations, not generated measurements."""
    scans = [[("synthetic", [], [str(i) for i in range(len(state))])] for state in states]
    observations = [SimpleNamespace(st_dev=device, st_ino=inode, st_size=size)
                    for state in states for device, inode, size in state]
    with patch.object(resources.os, "walk", side_effect=scans) as walk, \
            patch.object(Path, "stat", side_effect=observations), \
            patch.object(resources.time, "monotonic", return_value=0):
        measured = resources.output_bytes("synthetic")
    return measured, walk.call_count


class RenderInventoryTests(unittest.TestCase):
    def test_added_files_and_links_charge_all_second_entries_and_largest_observed_sizes(self):
        # First identity shrinks from 90 to 40 but acquires a second link.
        # Distinct devices prevent the two other inode-7 files being merged.
        states = [[(1, 7, 90)], [(1, 7, 40), (1, 7, 35), (2, 7, 12), (3, 7, 8)]]
        self.assertEqual(scripted_measurement(states), (200, 2))

    def test_lost_identity_is_rejected_even_if_other_new_bytes_replace_it(self):
        states = [[(1, 7, 23), (1, 8, 31)], [(1, 7, 23), (1, 9, 100)],
                  [(1, 7, 23), (1, 9, 110)]]
        self.assertEqual(scripted_measurement(states), (133, 3))

    def test_reduced_multiplicity_is_rejected_even_with_an_added_identity(self):
        states = [[(1, 7, 23), (1, 7, 23)], [(1, 7, 23), (1, 9, 100)],
                  [(1, 7, 23), (1, 9, 100)]]
        self.assertEqual(scripted_measurement(states), (123, 3))

    def test_continuous_replacement_cannot_be_accepted_as_membership_growth(self):
        clock = SimpleNamespace(now=0, inode=0)
        def stat():
            clock.now += .1
            clock.inode += 1
            return SimpleNamespace(st_dev=1, st_ino=clock.inode, st_size=23)
        with patch.object(resources.os, "walk", return_value=[("synthetic", [], ["same_name"])]), \
                patch.object(Path, "stat", side_effect=stat), \
                patch.object(resources.time, "monotonic", side_effect=lambda: clock.now):
            with self.assertRaisesRegex(resources.ResourceLimitError, "did not stabilize"):
                resources.output_bytes("synthetic")

    def test_incomplete_walk_discards_pair_and_requires_two_fresh_complete_scans(self):
        calls = []
        def walk(*args, **kwargs):
            calls.append(True)
            yield ("synthetic", [], ["visible"])
            if len(calls) == 2:
                kwargs["onerror"](FileNotFoundError("subdirectory disappeared"))
        observations = [SimpleNamespace(st_dev=1, st_ino=i, st_size=size)
                        for i, size in ((7, 23), (7, 999), (8, 31), (8, 35))]
        with patch.object(resources.os, "walk", side_effect=walk), \
                patch.object(Path, "stat", side_effect=observations), \
                patch.object(resources.time, "monotonic", return_value=0):
            self.assertEqual(resources.output_bytes("synthetic"), 35)
        self.assertEqual(len(calls), 4)

    def test_unreadable_subtree_never_becomes_partial_success(self):
        def walk(*args, **kwargs):
            yield ("synthetic", [], ["visible"])
            kwargs["onerror"](PermissionError("synthetic access failure"))
        info = SimpleNamespace(st_dev=1, st_ino=7, st_size=23)
        with patch.object(resources.os, "walk", side_effect=walk), \
                patch.object(Path, "stat", return_value=info):
            with self.assertRaisesRegex(PermissionError, "synthetic access failure"):
                resources.output_bytes("synthetic")

    def test_monotone_additions_cannot_bypass_deadline_during_or_after_walk(self):
        for expiration in ("new_stat", "end_walk"):
            with self.subTest(expiration=expiration):
                clock = SimpleNamespace(now=0, scans=0)
                def walk(*args, **kwargs):
                    clock.scans += 1
                    yield ("synthetic", [], ["original"] if clock.scans == 1 else ["original", "new"])
                    if clock.scans == 2 and expiration == "end_walk":
                        clock.now = .5
                def stat(path):
                    if path.name == "new" and expiration == "new_stat":
                        clock.now = .5
                    return SimpleNamespace(st_dev=1, st_ino=7 if path.name == "original" else 8, st_size=23)
                with patch.object(resources.os, "walk", side_effect=walk), \
                        patch.object(Path, "stat", new=stat), \
                        patch.object(resources.time, "monotonic", side_effect=lambda: clock.now):
                    with self.assertRaisesRegex(resources.ResourceLimitError, "did not stabilize"):
                        resources.output_bytes("synthetic")

    def test_actual_directory_publication_with_new_file_and_link_keeps_all_observed_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pending = root / "pending"
            pending.mkdir()
            (pending / "original").write_bytes(b"x" * 90)
            walk, scans = resources.os.walk, []
            def publishing_walk(*args, **kwargs):
                yield from walk(*args, **kwargs)
                scans.append(True)
                if len(scans) == 1:
                    pending.rename(root / "published")
                    original = root / "published/original"
                    original.write_bytes(b"s" * 40)
                    os.link(original, root / "second_link")
                    (root / "new").write_bytes(b"n" * 12)
            with patch.object(resources.os, "walk", side_effect=publishing_walk):
                self.assertEqual(resources.output_bytes(root), 192)
            self.assertEqual(len(scans), 2)
            self.assertEqual(resources.output_bytes(root), 92)

    def test_actual_deleted_link_and_atomic_replacement_require_fresh_pair(self):
        for action in ("delete_link", "replace"):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                original = root / "original"
                original.write_bytes(b"x" * 90)
                if action == "delete_link":
                    os.link(original, root / "link")
                walk, scans = resources.os.walk, []
                def changing_walk(*args, **kwargs):
                    yield from walk(*args, **kwargs)
                    scans.append(True)
                    if len(scans) == 1:
                        if action == "delete_link":
                            (root / "link").unlink()
                        else:
                            new = root / "replacement"
                            new.write_bytes(b"y" * 110)
                            new.replace(original)
                with patch.object(resources.os, "walk", side_effect=changing_walk):
                    self.assertEqual(resources.output_bytes(root), 90 if action == "delete_link" else 110)
                self.assertEqual(len(scans), 3)


class RenderCreationTests(unittest.TestCase):
    def test_continuous_creation_with_two_thousand_existing_files_exceeds_half_second_without_false_abort(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(2000):
                (root / ("p" + str(index))).write_bytes(b"p" * 10)
            stopped, started = threading.Event(), threading.Event()
            created, errors, duration = [], [], []
            def writer():
                began = time.monotonic()
                try:
                    while not stopped.is_set() and time.monotonic() - began < 1.1:
                        (root / ("n" + str(len(created)))).write_bytes(b"n" * 10)
                        created.append(True)
                        started.set()
                        stopped.wait(.005)
                except BaseException as error:
                    errors.append(error)
                finally:
                    duration.append(time.monotonic() - began)
            thread = threading.Thread(target=writer)
            thread.start()
            measurements = []
            try:
                self.assertTrue(started.wait(2))
                while thread.is_alive():
                    before = len(created)
                    measured = resources.output_bytes(root)
                    measurements.append(measured)
                    self.assertGreaterEqual(measured, 20000 + before * 10)
                    stopped.wait(.01)
            finally:
                stopped.set()
                thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])
            self.assertGreater(duration[0], .5)
            self.assertGreater(len(created), 20)
            self.assertGreater(len(measurements), 2)
            self.assertEqual(resources.output_bytes(root), 20000 + len(created) * 10)

    def test_supervised_continuous_creation_succeeds_with_all_resource_contracts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            preserved = root / "old_partial"
            preserved.write_bytes(b"preserve")
            contract = limits()
            receipt = run_creator(root, "under_cap", contract)
            result = json.loads((root / receipt["worker_result"]["path"]).read_text())
            self.assertTrue(receipt["success"])
            self.assertGreater(result["duration_seconds"], .5)
            self.assertGreater(result["files_created"], 20)
            self.assertLessEqual(receipt["maximum_monitor_interval_seconds"], 1)
            self.assertEqual(receipt["output_overshoot_bytes"], 0)
            self.assertIsNone(receipt["final_accounting_error"])
            self.assertEqual(preserved.read_bytes(), b"preserve")
            self.assertEqual(resources.BudgetJournal(root, contract).consumed(), receipt["elapsed_seconds"])

    def test_new_files_links_moves_replacements_and_deletions_cannot_hide_over_cap_bytes(self):
        for mode in ("create", "hardlink", "move", "replace", "delete"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                preserved = root / "old_partial"
                preserved.write_bytes(b"preserve")
                contract = limits(maximum_total_new_output_bytes=128 * 1024)
                with self.assertRaisesRegex(resources.ResourceLimitError, "exceeded: output_bytes"):
                    run_creator(root, mode, contract, duration=30)
                journal = resources.BudgetJournal(root, contract)
                receipt = journal.events[-1]
                self.assertFalse(receipt["success"])
                self.assertIsNone(receipt["worker_result"])
                self.assertGreater(receipt["output_overshoot_bytes"], 0)
                self.assertGreater(receipt["maximum_output_bytes"], contract["maximum_total_new_output_bytes"])
                self.assertEqual(preserved.read_bytes(), b"preserve")
                self.assertFalse(resources._alive(json.loads((root / "started.json").read_text())["pid"]))
                self.assertEqual(journal.consumed(), receipt["elapsed_seconds"])
                actual = sum(path.stat().st_size for path in root.rglob("*") if path.is_file())
                self.assertEqual(resources.output_bytes(root), actual)


if __name__ == "__main__":
    unittest.main()
