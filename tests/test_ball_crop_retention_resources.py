"""Owned synthetic workers exercise resource accounting and Windows job cleanup."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.ball_tracking import crop_retention_resources as resources
from src.ball_tracking.development_experiments import safe_path


ROOT = Path(__file__).resolve().parents[1]
WORKER = r'''
import json, os, subprocess, sys, time
from pathlib import Path
from src.ball_tracking.crop_retention_resources import wait_for_supervisor, _rss
wait_for_supervisor()
root = Path(os.environ["SYNTHETIC_RESOURCE_ROOT"])
mode = sys.argv[1]
if mode == "receipt":
    Path(os.environ["BALL_RETENTION_RESULT_PATH"]).write_text(json.dumps({"synthetic": True}), encoding="utf-8")
elif mode == "tree":
    child = subprocess.Popen([sys.executable, "-B", "-c", sys.argv[2]],
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    (root / "tree_parent.json").write_text(json.dumps({"pid": os.getpid(), "child_pid": child.pid}), encoding="utf-8")
    time.sleep(30)
elif mode == "bytes":
    (root / "synthetic_payload.bin").write_bytes(b"x" * 131072)
    time.sleep(30)
elif mode == "sleep":
    (root / "worker_started.json").write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
    time.sleep(30)
elif mode == "fail":
    print("synthetic worker failure", flush=True)
    raise SystemExit(9)
elif mode != "missing":
    raise RuntimeError("Unknown synthetic mode")
'''

CHILD = r'''
import json, os, time
from pathlib import Path
from src.ball_tracking.crop_retention_resources import wait_for_supervisor, _rss
wait_for_supervisor()
allocation = bytearray(16 * 1024 * 1024)
for offset in range(0, len(allocation), 4096):
    allocation[offset] = 1
root = Path(os.environ["SYNTHETIC_RESOURCE_ROOT"])
(root / "tree_child.json").write_text(json.dumps({"pid": os.getpid(), "rss_bytes": _rss(os.getpid())}), encoding="utf-8")
time.sleep(30)
'''


def limits(**changes):
    return {"maximum_worker_memory_bytes": 256 * 1024 * 1024,
            "maximum_total_new_output_bytes": 8 * 1024 * 1024,
            "minimum_free_disk_bytes": 0,
            "maximum_seconds_per_unit": 3.0,
            "maximum_cumulative_seconds": 20.0,
            **changes}


def run(root, mode="receipt", contract=None, **kwargs):
    return resources.run_supervised(root, "synthetic_" + mode,
        [sys.executable, "-B", "-c", WORKER, mode, CHILD], contract or limits(),
        cwd=ROOT, env={"SYNTHETIC_RESOURCE_ROOT": str(root)}, poll_seconds=.05, **kwargs)


def finished(root, contract):
    journal = resources.BudgetJournal(root, contract)
    return next(event for event in reversed(journal.events) if event["kind"] == "finished")


def wait_until(predicate, seconds=5.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(.02)
    return bool(predicate())


class BudgetJournalTests(unittest.TestCase):
    def test_interrupted_reservations_survive_resume_for_unit_and_cumulative_budgets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract = limits(maximum_seconds_per_unit=2.0, maximum_cumulative_seconds=5.0)
            journal = resources.BudgetJournal(root, contract)
            attempt, reserved = journal.reserve("unit_a", True)
            self.assertEqual(reserved, 2.0)
            journal.append("sample", attempt_id=attempt, elapsed_seconds=.1)
            resumed = resources.BudgetJournal(root, contract)
            self.assertEqual(resumed.consumed("unit_a"), 2.0)
            with self.assertRaisesRegex(resources.ResourceLimitError, "exhausted"):
                resumed.reserve("unit_a", True)
            resumed.reserve("unit_b", True)
            last = resources.BudgetJournal(root, contract)
            _, remaining = last.reserve("unit_c", True)
            self.assertEqual(remaining, 1.0)
            self.assertEqual(resources.BudgetJournal(root, contract).consumed(), 5.0)
            with self.assertRaises(resources.ResourceLimitError):
                resources.BudgetJournal(root, contract).reserve("unit_d", False)

    def test_finished_attempt_charges_actual_time_without_resetting_prior_consumption(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract = limits(maximum_seconds_per_unit=2.0, maximum_cumulative_seconds=5.0)
            journal = resources.BudgetJournal(root, contract)
            attempt, _ = journal.reserve("unit_a", True)
            journal.append("finished", attempt_id=attempt, elapsed_seconds=.75, success=False)
            resumed = resources.BudgetJournal(root, contract)
            _, remaining = resumed.reserve("unit_a", True)
            self.assertEqual(remaining, 1.25)
            self.assertEqual(resumed.consumed(), 2.0)

    def test_hash_chain_rejects_tampered_missing_or_reordered_events_and_changed_limits(self):
        for scenario in ("tamper", "missing", "rename", "limits"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                contract = limits()
                journal = resources.BudgetJournal(root, contract)
                attempt, _ = journal.reserve("unit", True)
                journal.append("finished", attempt_id=attempt, elapsed_seconds=.25, success=True)
                first = root / "resource_events/00000000.json"
                if scenario == "tamper":
                    value = json.loads(first.read_text())
                    value["reserved_seconds"] += 1
                    first.write_text(json.dumps(value), encoding="utf-8")
                elif scenario == "missing":
                    first.unlink()
                elif scenario == "rename":
                    first.rename(first.with_name("00000099.json"))
                else:
                    contract["maximum_cumulative_seconds"] += 1
                with self.assertRaises(resources.ResourceLimitError):
                    resources.BudgetJournal(root, contract)

    def test_valid_hashes_do_not_make_nonmonotone_or_finished_twice_events_valid(self):
        for scenario in ("nonmonotone", "finished_twice", "unknown_attempt"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                contract = limits()
                journal = resources.BudgetJournal(root, contract)
                attempt, _ = journal.reserve("unit", True)
                if scenario == "nonmonotone":
                    journal.append("sample", attempt_id=attempt, elapsed_seconds=.5)
                    journal.append("sample", attempt_id=attempt, elapsed_seconds=.25)
                elif scenario == "finished_twice":
                    journal.append("finished", attempt_id=attempt, elapsed_seconds=.5)
                    with self.assertRaises(FileExistsError):
                        journal.append("finished", attempt_id=attempt, elapsed_seconds=.6)
                else:
                    journal.append("sample", attempt_id="not_started", elapsed_seconds=.1)
                with self.assertRaises(resources.ResourceLimitError):
                    resources.BudgetJournal(root, contract)

    def test_completion_seal_rejects_valid_prefix_after_finished_tail_is_removed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract = limits()
            journal = resources.BudgetJournal(root, contract)
            attempt, _ = journal.reserve("unit", True)
            journal.append("sample", attempt_id=attempt, elapsed_seconds=.1)
            journal.append("finished", attempt_id=attempt, elapsed_seconds=.2, success=True)
            (root / "resource_events/00000002.json").unlink()
            with self.assertRaisesRegex(resources.ResourceLimitError, "Truncated|completed"):
                resources.BudgetJournal(root, contract)

    def test_reservation_seal_rejects_reset_history_even_before_worker_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract = limits()
            journal = resources.BudgetJournal(root, contract)
            journal.reserve("unit", True)
            (root / "resource_events/00000000.json").unlink()
            with self.assertRaisesRegex(resources.ResourceLimitError, "Orphan attempt"):
                resources.BudgetJournal(root, contract)


class OutputInventoryTests(unittest.TestCase):
    def test_directory_rename_preserves_identical_file_identity_inventory(self):
        info = SimpleNamespace(st_dev=1, st_ino=7, st_size=23, st_mtime_ns=42)
        scans = [[("pending", [], ["evidence.json"])], [("published", [], ["evidence.json"])]]
        with patch.object(resources.os, "walk", side_effect=scans) as walk, \
                patch.object(Path, "stat", return_value=info), \
                patch.object(resources.time, "monotonic", return_value=0):
            self.assertEqual(resources.output_bytes("synthetic_root"), 23)
        self.assertEqual(walk.call_count, 2)

    def test_transient_missing_file_requires_two_fresh_complete_inventories(self):
        before = SimpleNamespace(st_dev=1, st_ino=7, st_size=23, st_mtime_ns=42)
        after = SimpleNamespace(st_dev=1, st_ino=8, st_size=31, st_mtime_ns=43)
        with patch.object(resources.os, "walk", return_value=[("synthetic_root", [], ["evidence.json"])]) as walk, \
                patch.object(Path, "stat", side_effect=[before, FileNotFoundError(), after, after]), \
                patch.object(resources.time, "monotonic", return_value=0):
            self.assertEqual(resources.output_bytes("synthetic_root"), 31)
        self.assertEqual(walk.call_count, 4)

    def test_equal_byte_totals_with_changing_identity_fail_at_retry_deadline(self):
        clock = SimpleNamespace(now=0)
        def changing_stat():
            clock.now += .1
            return SimpleNamespace(st_dev=1, st_ino=round(clock.now * 10), st_size=23, st_mtime_ns=42)
        with patch.object(resources.os, "walk", return_value=[("synthetic_root", [], ["evidence.json"])]), \
                patch.object(Path, "stat", side_effect=changing_stat), \
                patch.object(resources.time, "monotonic", side_effect=lambda: clock.now):
            with self.assertRaisesRegex(resources.ResourceLimitError, "did not stabilize"):
                resources.output_bytes("synthetic_root")


class ResourceBoundaryTests(unittest.TestCase):
    def test_success_requires_and_binds_completion_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract = limits()
            receipt = run(root, contract=contract, require_result=True)
            self.assertTrue(receipt["success"])
            self.assertEqual(receipt["exit_code"], 0)
            self.assertGreater(receipt["monitor_samples"], 0)
            binding = receipt["worker_result"]
            self.assertNotIn("\\", binding["path"])
            self.assertNotIn("\\", receipt["log_path"])
            saved = safe_path(root, binding["path"]).read_bytes()
            self.assertTrue(safe_path(root, receipt["log_path"]).is_file())
            self.assertEqual(hashlib.sha256(saved).hexdigest(), binding["sha256"])
            self.assertEqual(json.loads(saved), {"synthetic": True})
            self.assertFalse((root / "supervisor.lock").exists())
            self.assertEqual(resources.BudgetJournal(root, contract).consumed(), receipt["elapsed_seconds"])

    def test_missing_receipt_or_nonzero_exit_cannot_claim_success(self):
        for mode, message in (("missing", "completion receipt"), ("fail", "exit code 9")):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                contract = limits()
                with self.assertRaisesRegex(resources.ResourceLimitError, message):
                    run(root, mode, contract, require_result=True)
                receipt = finished(root, contract)
                self.assertFalse(receipt["success"])
                self.assertIsNone(receipt["worker_result"])
                self.assertGreater(receipt["elapsed_seconds"], 0)

    def test_prelaunch_free_disk_and_existing_output_limits_stop_before_process_creation(self):
        for mode in ("disk", "bytes"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                contract = limits()
                if mode == "bytes":
                    (root / "preserved.bin").write_bytes(b"x" * 8192)
                    contract["maximum_total_new_output_bytes"] = 4096
                else:
                    contract["minimum_free_disk_bytes"] = 10
                disk = SimpleNamespace(free=4 if mode == "disk" else 1000000)
                with patch.object(resources.shutil, "disk_usage", return_value=disk), \
                        patch.object(resources.subprocess, "Popen", side_effect=AssertionError("Prelaunch guard bypassed")) as popen:
                    with self.assertRaisesRegex(resources.ResourceLimitError, "free_disk" if mode == "disk" else "output_bytes"):
                        run(root, contract=contract)
                popen.assert_not_called()
                self.assertFalse(finished(root, contract)["success"])
                if mode == "bytes":
                    self.assertEqual((root / "preserved.bin").stat().st_size, 8192)

    def test_actual_new_output_excess_stops_worker_and_records_overshoot(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract = limits(maximum_total_new_output_bytes=65536)
            with self.assertRaisesRegex(resources.ResourceLimitError, "output_bytes"):
                run(root, "bytes", contract, selection_unit=True)
            receipt = finished(root, contract)
            self.assertGreater(receipt["output_overshoot_bytes"], 0)
            self.assertGreaterEqual(receipt["maximum_output_bytes"], 131072)
            self.assertEqual((root / "synthetic_payload.bin").stat().st_size, 131072)

    def test_memory_limit_can_be_exercised_without_allocating_unsafe_memory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract = limits(maximum_worker_memory_bytes=4096)
            with patch.object(resources, "_rss", return_value=8192):
                with self.assertRaisesRegex(resources.ResourceLimitError, "worker_memory"):
                    run(root, "sleep", contract, selection_unit=True)
            receipt = finished(root, contract)
            self.assertGreater(receipt["memory_overshoot_bytes"], 0)
            self.assertGreaterEqual(receipt["peak_worker_memory_bytes"], 8192)

    def test_actual_time_abort_spends_unit_budget_and_resume_cannot_reset_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract = limits(maximum_seconds_per_unit=.4, maximum_cumulative_seconds=2.0)
            with self.assertRaisesRegex(resources.ResourceLimitError, "time"):
                run(root, "sleep", contract, selection_unit=True)
            receipt = finished(root, contract)
            self.assertGreater(receipt["elapsed_seconds"], .4)
            self.assertGreater(receipt["time_overshoot_seconds"], 0)
            with patch.object(resources.subprocess, "Popen", side_effect=AssertionError("Spent unit was restarted")):
                with self.assertRaisesRegex(resources.ResourceLimitError, "exhausted"):
                    run(root, "sleep", contract, selection_unit=True)

    def test_worker_cannot_start_without_supervisor_gate(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(resources.ResourceLimitError, "resource supervisor"):
                resources.wait_for_supervisor()

    def test_monitor_interval_never_exceeds_one_second(self):
        with tempfile.TemporaryDirectory() as temporary:
            for interval in (0, -1, 1.01):
                with self.subTest(interval=interval), self.assertRaises(ValueError):
                    resources.run_supervised(temporary, "unit", [sys.executable, "-B", "-c", "pass"], limits(),
                                             cwd=ROOT, poll_seconds=interval)

    def test_final_accounting_reserves_exactly_sixteen_kib_for_output_and_free_disk(self):
        measured_bytes = 1000
        reserve_bytes = 16384
        for boundary in ("output", "free_disk"):
            for shortage in (1, 0):
                with self.subTest(boundary=boundary, shortage=shortage), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    contract = limits(minimum_free_disk_bytes=1000)
                    free = 1000000
                    if boundary == "output":
                        contract["maximum_total_new_output_bytes"] = measured_bytes + reserve_bytes - shortage
                    else:
                        free = contract["minimum_free_disk_bytes"] + reserve_bytes - shortage
                    with patch.object(resources, "output_bytes", return_value=measured_bytes), \
                            patch.object(resources.shutil, "disk_usage", return_value=SimpleNamespace(free=free)):
                        if shortage:
                            with self.assertRaisesRegex(resources.ResourceLimitError, "final time/output/free-disk accounting"):
                                run(root, contract=contract, require_result=True)
                        else:
                            run(root, contract=contract, require_result=True)
                    receipt = finished(root, contract)
                    self.assertEqual(receipt["success"], not shortage)
                    self.assertEqual(receipt["exit_code"], 0)
                    self.assertIsNotNone(receipt["worker_result"])
                    self.assertEqual(receipt["maximum_output_bytes"], measured_bytes)
                    self.assertEqual(receipt["final_accounting_output_bound_bytes"], measured_bytes + reserve_bytes)
                    self.assertEqual(receipt["output_overshoot_bytes"], 0)

    def test_actual_snapshot_cadence_over_one_second_aborts_within_time_and_byte_budgets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract = limits()
            ticks = iter([0, 0, 0, 1.001, 1.001, 1.001])
            fake_clock = SimpleNamespace(monotonic=lambda: next(ticks), sleep=lambda _: None)
            with patch.object(resources, "time", fake_clock), \
                    patch.object(resources, "output_bytes", return_value=1000):
                with self.assertRaisesRegex(resources.ResourceLimitError, "exceeded: monitor_interval"):
                    run(root, "sleep", contract, selection_unit=True)
            receipt = finished(root, contract)
            self.assertFalse(receipt["success"])
            self.assertEqual(receipt["maximum_monitor_interval_seconds"], 1.001)
            self.assertLess(receipt["elapsed_seconds"], contract["maximum_seconds_per_unit"])
            self.assertEqual(receipt["time_overshoot_seconds"], 0)


class SupervisorLockTests(unittest.TestCase):
    def test_live_owner_lock_is_preserved_and_prevents_worker_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock = root / "supervisor.lock"
            original = json.dumps({"pid": os.getpid(), "token": "existing_owner"}).encode()
            lock.write_bytes(original)
            with patch.object(resources.subprocess, "Popen", side_effect=AssertionError("Second worker started")):
                with self.assertRaisesRegex(resources.ResourceLimitError, "Another supervisor"):
                    run(root)
            self.assertEqual(lock.read_bytes(), original)

    def test_proven_dead_owner_lock_can_be_replaced_without_deleting_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            child = subprocess.Popen([sys.executable, "-B", "-c", "pass"],
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            child.wait(timeout=5)
            self.assertFalse(resources._alive(child.pid))
            (root / "supervisor.lock").write_text(json.dumps({"pid": child.pid, "token": "dead_owner"}), encoding="utf-8")
            (root / "preserved_evidence.json").write_bytes(b'{"preserve":true}')
            receipt = run(root, require_result=True)
            self.assertTrue(receipt["success"])
            self.assertEqual((root / "preserved_evidence.json").read_bytes(), b'{"preserve":true}')
            self.assertFalse((root / "supervisor.lock").exists())


@unittest.skipUnless(os.name == "nt", "Windows Job Object behavior requires Windows")
class WindowsJobTreeTests(unittest.TestCase):
    def test_time_abort_accounts_parent_and_child_rss_and_kills_entire_owned_job(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract = limits(maximum_seconds_per_unit=1.5)
            observed_pids = set()
            original_rss = resources._rss
            def record_rss(pid):
                observed_pids.add(pid)
                return original_rss(pid)
            with patch.object(resources, "_rss", side_effect=record_rss):
                with self.assertRaisesRegex(resources.ResourceLimitError, "time"):
                    run(root, "tree", contract, selection_unit=True)
            parent = json.loads((root / "tree_parent.json").read_text())
            child = json.loads((root / "tree_child.json").read_text())
            # A Windows venv launcher may create another interpreter process.
            # Both the launcher and actual interpreter must stay in the job.
            self.assertTrue({parent["pid"], parent["child_pid"], child["pid"]} <= observed_pids)
            receipt = finished(root, contract)
            self.assertGreaterEqual(receipt["peak_worker_memory_bytes"], child["rss_bytes"])
            self.assertTrue(wait_until(lambda: all(not resources._alive(pid) for pid in
                                                  (parent["pid"], parent["child_pid"], child["pid"]))))
            self.assertFalse(receipt["success"])

    def test_job_close_terminates_descendants_even_without_explicit_kill(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            gate = root / "owned_job.start"
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "BALL_RETENTION_START_GATE": str(gate),
                   "SYNTHETIC_RESOURCE_ROOT": str(root)}
            worker = subprocess.Popen([sys.executable, "-B", "-c", WORKER, "tree", CHILD], cwd=ROOT,
                                      env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                      creationflags=subprocess.CREATE_NO_WINDOW)
            job = None
            try:
                job = resources._WindowsJob(worker)
                gate.touch()
                self.assertTrue(wait_until(lambda: (root / "tree_child.json").is_file()))
                child = json.loads((root / "tree_child.json").read_text())
                self.assertIn(worker.pid, job.pids())
                self.assertIn(child["pid"], job.pids())
                job.close()
                worker.wait(timeout=5)
                self.assertTrue(wait_until(lambda: not resources._alive(child["pid"])))
            finally:
                if job is not None:
                    job.close()
                if worker.poll() is None:
                    worker.kill()
                    worker.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
