"""Focused monitor checks using tiny invented files and controlled processes."""
from __future__ import annotations

import copy
from contextlib import ExitStack
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import Mock, patch

from src.ball_tracking import crop_retention_monitor as monitor
from src.ball_tracking import crop_retention_resources as resources


BASE = Path(__file__).resolve().parents[1]
GIB = 1024 ** 3
MIB = 1024 ** 2


def limits(**changes):
    value = {"maximum_cumulative_seconds": 120.0,
             "maximum_seconds_per_unit": 30.0,
             "maximum_worker_memory_bytes": 8 * GIB,
             "maximum_total_new_output_bytes": 32 * GIB,
             "minimum_free_disk_bytes": 50 * GIB}
    value.update(changes)
    return value


class ModuleProxy:
    """Replace one module-local dependency without patching the shared module."""
    def __init__(self, original, **changes):
        self.original = original
        self.changes = changes

    def __getattr__(self, name):
        return self.changes[name] if name in self.changes else getattr(self.original, name)


class TinyRoot(unittest.TestCase):
    def setUp(self):
        # The outer recorder binds TEMP/TMP/TMPDIR to its fresh counted root.
        parent = Path(tempfile.gettempdir())
        self.temporary = tempfile.TemporaryDirectory(prefix="monitor_unit_", dir=parent)
        self.root = Path(self.temporary.name)
        self.assertEqual(self.root.resolve().parent, parent.resolve())
        self.addCleanup(self.temporary.cleanup)

    def write(self, name, size):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * size)
        return path

    def reference(self):
        return sum(os.stat(Path(folder) / name, follow_symlinks=False).st_size
                   for folder, _, names in os.walk(self.root) for name in names)


class MetadataScanTests(TinyRoot):
    def test_empty_tree_and_unicode_hardlinks_match_reference(self):
        self.assertEqual(monitor.output_bytes(self.root), 0)
        original = self.write("\u7bee\u7403/caf\u00e9.bin", 17)
        os.link(original, self.root / "link.bin")
        self.write("nested/a/b.bin", 5)
        self.assertEqual(monitor.output_bytes(self.root), 39)
        self.assertEqual(monitor.output_bytes(self.root), self.reference())

    def test_growth_between_inventories_uses_fresh_size_and_link_multiplicity(self):
        original = self.write("growing.bin", 3)
        os.link(original, self.root / "link.bin")
        real_walk = os.walk
        calls = []

        def walk(*args, **kwargs):
            calls.append(None)
            if len(calls) == 2:
                original.write_bytes(b"y" * 9)
            return real_walk(*args, **kwargs)

        with patch.object(monitor, "os", ModuleProxy(os, walk=walk)):
            self.assertEqual(monitor.output_bytes(self.root), 18)
        self.assertEqual(len(calls), 2)

    def test_shrink_between_inventories_uses_larger_observed_size(self):
        original = self.write("shrinking.bin", 13)
        real_walk = os.walk
        calls = []

        def walk(*args, **kwargs):
            calls.append(None)
            if len(calls) == 2:
                original.write_bytes(b"z" * 2)
            return real_walk(*args, **kwargs)

        with patch.object(monitor, "os", ModuleProxy(os, walk=walk)):
            self.assertEqual(monitor.output_bytes(self.root), 13)

    def test_deletion_needs_another_complete_compatible_inventory(self):
        self.write("survivor.bin", 7)
        removed = self.write("removed.bin", 23)
        real_walk = os.walk
        calls = []

        def walk(*args, **kwargs):
            calls.append(None)
            if len(calls) == 2:
                removed.unlink()
            return real_walk(*args, **kwargs)

        with patch.object(monitor, "os", ModuleProxy(os, walk=walk)):
            self.assertEqual(monitor.output_bytes(self.root), 7)
        self.assertEqual(len(calls), 3)

    def test_disappearance_discards_partial_inventory(self):
        self.write("only.bin", 11)
        real_walk = os.walk
        calls = []

        def walk(*args, **kwargs):
            calls.append(None)
            yield from real_walk(*args, **kwargs)
            if len(calls) == 1:
                raise FileNotFoundError("injected disappearance after traversal")

        with patch.object(monitor, "os", ModuleProxy(os, walk=walk)):
            self.assertEqual(monitor.output_bytes(self.root), 11)
        self.assertEqual(len(calls), 3)

    def test_enumeration_permission_error_is_not_an_empty_inventory(self):
        selected = PermissionError("injected walk error")

        def walk(root, onerror, **kwargs):
            onerror(selected)
            raise AssertionError("walk error callback must raise")

        with patch.object(monitor, "os", ModuleProxy(os, walk=walk)):
            with self.assertRaises(PermissionError) as caught:
                monitor.output_bytes(self.root)
        self.assertIs(caught.exception, selected)

    def test_expired_deadline_fails_before_traversal(self):
        walk = Mock(side_effect=AssertionError("expired scan must not walk"))
        with patch.object(monitor, "time", ModuleProxy(time, monotonic=lambda: 1.0)), \
                patch.object(monitor, "os", ModuleProxy(os, walk=walk)):
            with self.assertRaises(resources.ResourceLimitError):
                monitor.output_bytes(self.root, deadline=1.0)
        walk.assert_not_called()


class MonitorStateTests(unittest.TestCase):
    def setUp(self):
        self.limits = limits()
        self.policy = monitor.monitoring_policy(self.limits, .25)

    def state(self, **changes):
        selected = limits(**changes)
        policy = monitor.monitoring_policy(selected, .25)
        return monitor._MonitorState(selected, 0.0, 90.0, policy)

    def receipt(self, requested=0.0, started=.1, completed=.2, total=10,
                request_id="scan1", **changes):
        value = {"schema_version": "crop_retention_scan_response/v1",
                 "request_id": request_id, "requested_at": requested,
                 "scan_started_at": started, "completed_at": completed,
                 "output_bytes": total, "success": True, "error": None,
                 "policy_sha256": resources._digest(self.policy)}
        value.update(changes)
        return value

    def healthy_tick(self, state, now):
        return state.check(now, 0, 0, 100 * GIB)

    def tick_through(self, state, end):
        now = .25 if state.last_tick is None else state.last_tick + .25
        while now < end:
            self.healthy_tick(state, now)
            now += .25

    def test_public_policy_values_and_immutable_source_limits(self):
        before = copy.deepcopy(self.limits)
        self.assertEqual(self.policy["scan_timeout_seconds"], 10.0)
        self.assertEqual(self.policy["next_scan_seconds"], 5.0)
        self.assertEqual(self.policy["maximum_scan_age_seconds"], 30.0)
        self.assertEqual(self.policy["maximum_fast_interval_seconds"], 1.0)
        self.assertEqual(self.policy["poll_seconds"], .25)
        self.assertEqual(monitor.monitoring_policy(limits(minimum_free_disk_bytes=1))[
            "effective_minimum_free_disk_bytes"], 50 * GIB)
        self.assertEqual(self.limits, before)

    def test_scanner_can_remain_pending_beyond_old_half_second(self):
        state = self.state()
        state.request_started(0.0, "scan1")
        for now in (.25, .5, .75, 1.0, 1.25):
            self.healthy_tick(state, now)
        state.accept_scan(self.receipt(started=.1, completed=1.25), 1.25)
        self.assertEqual(state.maximum_bytes, 10)
        self.assertIsNone(state.active)

    def test_combined_rss_limit_acts_while_scanner_is_pending(self):
        state = self.state(maximum_worker_memory_bytes=100)
        state.request_started(0.0, "scan1")
        with self.assertRaises(resources.ResourceLimitError):
            state.check(.25, 70, 31, 100 * GIB)
        self.assertEqual(state.peak_memory, 101)

    def test_scanner_alone_can_trigger_combined_memory_limit(self):
        state = self.state(maximum_worker_memory_bytes=100)
        state.request_started(0.0, "scan1")
        with self.assertRaises(resources.ResourceLimitError):
            state.check(.25, 0, 101, 100 * GIB)

    def test_low_free_disk_acts_while_scanner_is_pending(self):
        state = self.state()
        state.request_started(0.0, "scan1")
        with self.assertRaises(resources.ResourceLimitError):
            state.check(.25, 0, 0, 50 * GIB - 1)

    def test_unit_time_limit_acts_while_scanner_is_pending(self):
        state = monitor._MonitorState(self.limits, 0.0, .1, self.policy)
        state.request_started(0.0, "scan1")
        with self.assertRaises(resources.ResourceLimitError):
            self.healthy_tick(state, .25)

    def test_delayed_fast_poll_is_rejected_independently_of_scan(self):
        state = self.state()
        state.request_started(0.0, "scan1")
        self.healthy_tick(state, 0.0)
        with self.assertRaises(resources.ResourceLimitError):
            self.healthy_tick(state, 1.01)
        self.assertGreater(state.maximum_interval, 1.0)

    def test_scan_request_deadline_includes_startup_delay(self):
        state = self.state()
        state.request_started(0.0, "scan1")
        self.tick_through(state, 10.0)
        with self.assertRaises(resources.ResourceLimitError):
            self.healthy_tick(state, 10.0)

    def test_completed_at_deadline_is_not_a_successful_measurement(self):
        state = self.state()
        state.request_started(0.0, "scan1")
        with self.assertRaises(resources.ResourceLimitError):
            state.accept_scan(self.receipt(started=9.0, completed=10.0), 10.0)

    def test_only_one_scan_request_can_be_active(self):
        state = self.state()
        state.request_started(0.0, "scan1")
        with self.assertRaises(resources.ResourceLimitError):
            state.request_started(.1, "scan2")

    def test_next_dispatch_due_five_seconds_after_completion(self):
        state = self.state()
        state.request_started(0.0, "scan1")
        state.accept_scan(self.receipt(completed=2.0), 2.0)
        self.assertFalse(state.scan_due(2.01))
        self.assertTrue(state.scan_due(7.0))

    def test_age_uses_scan_request_start_not_completion(self):
        state = self.state()
        state.request_started(0.0, "scan1")
        state.accept_scan(self.receipt(started=.1, completed=9.0), 9.0)
        self.tick_through(state, 30.01)
        with self.assertRaises(resources.ResourceLimitError):
            self.healthy_tick(state, 30.01)

    def test_late_parent_observation_does_not_rejuvenate_measurement(self):
        state = self.state()
        state.request_started(0.0, "scan1")
        with self.assertRaises(resources.ResourceLimitError):
            state.accept_scan(self.receipt(completed=1.0), 30.0)

    def test_malformed_stale_and_failed_responses_are_rejected(self):
        changes = ({"request_id": "other"}, {"requested_at": .01},
                   {"policy_sha256": "0" * 64}, {"output_bytes": True},
                   {"output_bytes": -1}, {"output_bytes": 1.5},
                   {"success": 1}, {"success": False, "error": "injected failure"},
                   {"completed_at": float("nan")}, {"scan_started_at": -.1},
                   {"completed_at": .05}, {"completed_at": 1.1},
                   {"error": "unexpected error on success"},
                   {"schema_version": "other"}, {"extra": 1})
        for change in changes:
            with self.subTest(change=change):
                state = self.state()
                state.request_started(0.0, "scan1")
                with self.assertRaises(resources.ResourceLimitError):
                    state.accept_scan(self.receipt(**change), 1.0)
                self.assertIsNone(state.latest)

    def test_response_without_request_or_duplicate_response_is_rejected(self):
        state = self.state()
        response = self.receipt()
        with self.assertRaises(resources.ResourceLimitError):
            state.accept_scan(response, .2)
        state.request_started(0.0, "scan1")
        state.accept_scan(response, .2)
        with self.assertRaises(resources.ResourceLimitError):
            state.accept_scan(response, .3)

    def test_new_measurement_enforces_output_cap_and_keeps_high_water_mark(self):
        state = self.state(maximum_total_new_output_bytes=100)
        state.request_started(0.0, "scan1")
        with self.assertRaises(resources.ResourceLimitError):
            state.accept_scan(self.receipt(total=101, policy_sha256=state.policy_sha256), .2)
            self.healthy_tick(state, .25)
        self.assertEqual(state.maximum_bytes, 101)


class ProtocolTests(TinyRoot):
    def test_protocol_is_bounded_before_publication_and_create_only(self):
        path = self.root / "response.json"
        # Compact JSON fits but legacy indented serialization exceeds 8192 bytes.
        with self.assertRaises(resources.ResourceLimitError):
            monitor._write_record(path, {"items": [0] * 2000})
        self.assertFalse(path.exists())
        monitor._write_record(path, {"accepted": True})
        before = path.read_bytes()
        with self.assertRaises(FileExistsError):
            monitor._write_record(path, {"accepted": False})
        self.assertEqual(path.read_bytes(), before)

    def test_protocol_rejects_oversized_nonobject_and_malformed_records(self):
        path = self.root / "response.json"
        for data, errors in ((b" " * 8193, (resources.ResourceLimitError,)),
                             (b"[]", (resources.ResourceLimitError,)),
                             (b"{", (ValueError,))):
            with self.subTest(length=len(data)):
                path.write_bytes(data)
                with self.assertRaises(errors):
                    monitor._read_record(path)

    def test_worker_receipt_has_separate_one_mib_bound_and_same_read_hash(self):
        path = self.root / "worker.result.json"
        value = {"artificial_payload": "x" * 10000}
        payload = json.dumps(value).encode("utf-8")
        path.write_bytes(payload)
        with self.assertRaises(resources.ResourceLimitError):
            monitor._read_record(path)
        actual, digest = monitor._read_record(
            path, limit=monitor.WORKER_RECEIPT_LIMIT, with_sha256=True)
        self.assertEqual(actual, value)
        self.assertEqual(digest, hashlib.sha256(payload).hexdigest())
        self.assertEqual(monitor.WORKER_RECEIPT_LIMIT, MIB)
        path.write_bytes(b" " * (MIB + 1))
        with self.assertRaises(resources.ResourceLimitError):
            monitor._read_record(path, limit=monitor.WORKER_RECEIPT_LIMIT, with_sha256=True)


@unittest.skipUnless(os.name == "nt", "Windows monitor dispatch contract")
class SupervisorFlowTests(TinyRoot):
    """Exercise real journal/runner code; only processes, clock and metrics fake."""
    def simulate(self, *, fault=None, worker_seconds=7.0, approved=None):
        approved = limits() if approved is None else approved
        self.clock = 0.0
        self.scanners = []
        self.workers = []
        self.worker_progress_during_scan = False
        owner = self

        class Scanner:
            def __init__(self, root, folder, policy, *, cwd):
                self.policy = policy
                self.pending = None
                self.requests = []
                self.closed = False
                self.folder = Path(folder)
                self.folder.mkdir()
                owner.scanners.append(self)

            def request(self, now, request_id):
                if self.pending is not None:
                    raise AssertionError("overlapping request reached scanner")
                self.requests.append((now, request_id))
                self.pending = (now, request_id)
                monitor._write_record(self.folder / (request_id + ".request.json"),
                                      {"requested_at": now, "request_id": request_id})

            def poll(self):
                if self.pending is None:
                    return None
                requested, request_id = self.pending
                number = len(self.requests)
                if number == 2 and fault in ("memory", "disk", "time", "stall"):
                    return None
                delay = .75 if number == 2 and fault is None else .25
                if owner.clock < requested + delay:
                    return None
                self.pending = None
                failed = (fault == "pre" and number == 1) or (fault == "post" and number == 2)
                receipt = {"schema_version": monitor.RESPONSE_VERSION,
                           "request_id": request_id, "requested_at": requested,
                           "scan_started_at": requested, "completed_at": requested + delay,
                           "output_bytes": None if failed else 100,
                           "success": not failed, "error": "injected scan failure" if failed else None,
                           "policy_sha256": resources._digest(self.policy)}
                monitor._write_record(self.folder / (request_id + ".response.json"), receipt)
                return receipt

            def rss(self):
                if fault == "memory" and len(self.requests) >= 2 and not self.closed:
                    return 9 * GIB
                return 20 if self.requests and not self.closed else 0

            def close(self):
                self.closed = True

        class Process:
            def __init__(self, env):
                self.pid = 1234
                self.returncode = None
                self.started = owner.clock
                self.env = env
                self.killed = False

            def poll(self):
                if self.returncode is None:
                    scanner = owner.scanners[0]
                    if scanner.pending and owner.clock - scanner.pending[0] >= .5:
                        owner.worker_progress_during_scan = True
                    if owner.clock - self.started >= worker_seconds:
                        self.returncode = 0
                        Path(self.env["BALL_RETENTION_RESULT_PATH"]).write_text(
                            json.dumps({"artificial_worker": True}), encoding="utf-8")
                return self.returncode

            def kill(self):
                if self.returncode is None:
                    self.returncode = -9
                    self.killed = True

        class Job:
            def __init__(self, process):
                self.process = process
                self.closed = False

            def pids(self):
                return [self.process.pid] if self.process.poll() is None else []

            def kill(self):
                self.process.kill()

            def close(self):
                self.closed = True

        def spawn(command, *, env, **kwargs):
            self.assertEqual(len(self.scanners[0].requests), 1)
            self.assertIsNone(self.scanners[0].pending, "worker launched before completed preflight")
            process = Process(env)
            job = Job(process)
            self.workers.append((process, job))
            return process, job

        def sleep(seconds):
            self.clock += seconds

        def disk_usage(path):
            blocked = self.scanners and len(self.scanners[0].requests) >= 2
            return types.SimpleNamespace(free=1 if fault == "disk" and blocked else 100 * GIB)

        with ExitStack() as stack:
            stack.enter_context(patch.object(monitor, "_Scanner", Scanner))
            stack.enter_context(patch.object(monitor, "_spawn_owned", spawn))
            stack.enter_context(patch.object(monitor, "time", ModuleProxy(
                time, monotonic=lambda: self.clock, sleep=sleep)))
            stack.enter_context(patch.object(monitor, "shutil", ModuleProxy(shutil, disk_usage=disk_usage)))
            stack.enter_context(patch.object(monitor, "resources", ModuleProxy(resources, _rss=lambda pid: 40)))
            return monitor.run_supervised(self.root, "artificial:unit", ["artificial-command"],
                                          approved, cwd=BASE, selection_unit=True,
                                          require_result=True)

    def finished(self):
        paths = sorted((self.root / "resource_events").glob("*.json"))
        self.assertTrue(paths)
        value = json.loads(paths[-1].read_text())
        self.assertEqual(value["kind"], "finished")
        return value

    def assert_cleaned(self):
        self.assertFalse((self.root / "supervisor.lock").exists())
        self.assertTrue(all(scanner.closed for scanner in self.scanners))
        self.assertTrue(all(job.closed and process.poll() is not None
                            for process, job in self.workers))

    def test_worker_progresses_during_slow_scan_and_pre_post_scans_are_required(self):
        result = self.simulate()
        self.assertTrue(result["success"])
        self.assertTrue(self.worker_progress_during_scan)
        self.assertEqual(len(self.scanners), 1)
        self.assertGreaterEqual(len(self.scanners[0].requests), 3)
        self.assertGreaterEqual(result["final_scan"]["requested_at"], result["charged_elapsed_seconds"])
        self.assertGreater(result["total_wall_seconds_before_publication"], result["charged_elapsed_seconds"])
        self.assertEqual(result["peak_worker_memory_bytes"], 60)
        self.assertLessEqual(result["maximum_monitor_interval_seconds"], .25)
        self.assert_cleaned()

    def test_fast_memory_failure_does_not_wait_for_hung_scanner(self):
        with self.assertRaises(resources.ResourceLimitError):
            self.simulate(fault="memory", worker_seconds=100)
        result = self.finished()
        request_start = self.scanners[0].requests[1][0]
        self.assertLess(result["charged_elapsed_seconds"] - request_start, 1)
        self.assertGreater(result["memory_overshoot_bytes"], 0)
        self.assert_cleaned()

    def test_fast_disk_failure_does_not_wait_for_hung_scanner(self):
        with self.assertRaises(resources.ResourceLimitError):
            self.simulate(fault="disk", worker_seconds=100)
        result = self.finished()
        self.assertLess(result["charged_elapsed_seconds"] - self.scanners[0].requests[1][0], 1)
        self.assertIn("free_disk", result["failure"])
        self.assert_cleaned()

    def test_time_failure_does_not_wait_for_hung_scanner(self):
        with self.assertRaises(resources.ResourceLimitError):
            self.simulate(fault="time", worker_seconds=100,
                          approved=limits(maximum_seconds_per_unit=6.0))
        result = self.finished()
        self.assertLessEqual(result["charged_elapsed_seconds"], 6.5)
        self.assertGreater(result["time_overshoot_seconds"], 0)
        self.assert_cleaned()

    def test_hung_scanner_times_out_and_both_process_groups_are_cleaned(self):
        with self.assertRaises(resources.ResourceLimitError):
            self.simulate(fault="stall", worker_seconds=100)
        result = self.finished()
        self.assertIn("scan_timeout", result["failure"])
        self.assertFalse(result["success"])
        self.assert_cleaned()

    def test_failed_initial_scan_never_launches_worker(self):
        with self.assertRaises(resources.ResourceLimitError):
            self.simulate(fault="pre")
        self.assertEqual(self.workers, [])
        self.assertFalse(self.finished()["success"])
        self.assert_cleaned()

    def test_failed_final_scan_preserves_worker_result_as_unaccepted_evidence(self):
        with self.assertRaises(resources.ResourceLimitError):
            self.simulate(fault="post", worker_seconds=.5)
        result = self.finished()
        self.assertFalse(result["success"])
        self.assertIsNotNone(result["final_accounting_error"])
        self.assertTrue((self.root / result["worker_result"]["path"]).is_file())
        self.assertTrue((self.root / result["log_path"]).is_file())
        self.assert_cleaned()

    def test_existing_failure_and_limits_hash_survive_and_budget_is_deducted(self):
        approved = limits()
        journal = resources.BudgetJournal(self.root, approved)
        old_id, _ = journal.reserve("artificial:unit", True)
        journal.append("finished", attempt_id=old_id, elapsed_seconds=1.0,
                       success=False, failure="preserved artificial failure")
        before = {p: p.read_bytes() for p in self.root.rglob("*.json")}
        result = self.simulate(worker_seconds=.5, approved=approved)
        for path, payload in before.items():
            self.assertEqual(path.read_bytes(), payload)
        self.assertEqual(result["time_budget_seconds"], 29.0)
        reloaded = resources.BudgetJournal(self.root, approved)
        self.assertEqual(reloaded.consumed("artificial:unit"), 1.0 + result["elapsed_seconds"])
        self.assertTrue(all(event["limits_sha256"] == resources._digest(approved)
                            for event in reloaded.events))
        self.assert_cleaned()


@unittest.skipUnless(os.name == "nt", "Windows Job Object contract")
class WindowsOwnershipTests(TinyRoot):
    def test_job_record_has_exact_kill_on_close_and_commit_limit(self):
        record = monitor._job_limit_record(64 * MIB)
        raw = bytes(record)
        self.assertEqual(len(raw), 144)
        self.assertEqual(int.from_bytes(raw[16:20], "little"), 0x2000 | 0x200)
        self.assertEqual(int.from_bytes(raw[112:120], "little"), 0)
        self.assertEqual(int.from_bytes(raw[120:128], "little"), 64 * MIB)

    def launch(self, code, cap):
        gate = self.root / "child.start"
        result = self.root / "child.json"
        log = (self.root / "child.log").open("xb")
        self.addCleanup(log.close)
        # No payload or descendants are started until the test assigns the job.
        preamble = ("import os, sys, time, json\nfrom pathlib import Path\n"
                    "gate, result = map(Path, sys.argv[1:3])\n"
                    "end = time.monotonic() + 5\n"
                    "while not gate.exists():\n"
                    "    if time.monotonic() >= end: raise RuntimeError('gate timeout')\n"
                    "    time.sleep(.01)\n")
        process, job = monitor._spawn_owned(
            [sys.executable, "-B", "-c", preamble + code, str(gate), str(result)],
            commit_limit_bytes=cap, cwd=BASE, stdout=log, stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})

        def cleanup():
            if job is not None:
                job.kill()
                job.close()
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)

        self.addCleanup(cleanup)
        gate.touch(exist_ok=False)
        return process, job, result

    def test_small_job_rejects_large_commit_without_memory_pressure(self):
        # A single 128MiB reservation+commit must be denied by the 64MiB job.
        # No pages are touched; unexpected success is immediately freed.
        code = ("import ctypes\n"
                "k = ctypes.WinDLL('kernel32', use_last_error=True)\n"
                "k.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32]\n"
                "k.VirtualAlloc.restype = ctypes.c_void_p\n"
                "k.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32]\n"
                "k.VirtualFree.restype = ctypes.c_int\n"
                "p = k.VirtualAlloc(None, 128 * 1024 * 1024, 0x3000, 4)\n"
                "error = ctypes.get_last_error()\n"
                "if p: k.VirtualFree(p, 0, 0x8000)\n"
                "result.write_text(json.dumps({'denied': not bool(p), 'error': error, 'pid': os.getpid()}))\n")
        process, job, result = self.launch(code, 64 * MIB)
        self.assertEqual(process.wait(timeout=10), 0)
        value = json.loads(result.read_text())
        self.assertTrue(value["denied"])
        self.assertIn(value["error"], (8, 1455))
        deadline = time.monotonic() + 1
        while job.pids() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertEqual(job.pids(), [])

    def test_job_owns_and_cleans_up_worker_descendant(self):
        code = ("import subprocess\n"
                "child = subprocess.Popen([sys.executable, '-B', '-c', 'import time; time.sleep(8)'], creationflags=subprocess.CREATE_NO_WINDOW)\n"
                "result.write_text(json.dumps({'worker': os.getpid(), 'child': child.pid}))\n"
                "time.sleep(8)\n")
        process, job, result = self.launch(code, 128 * MIB)
        deadline = time.monotonic() + 5
        while not result.is_file() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(result.is_file(), "controlled worker did not publish child IDs")
        value = json.loads(result.read_text())
        owned = set(job.pids())
        self.assertIn(value["worker"], owned)
        self.assertIn(value["child"], owned)
        job.kill()
        process.wait(timeout=5)
        deadline = time.monotonic() + 5
        while job.pids() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertEqual(job.pids(), [])
        self.assertFalse(resources._alive(value["worker"]))
        self.assertFalse(resources._alive(value["child"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
