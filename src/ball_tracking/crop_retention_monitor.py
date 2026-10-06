"""Owned asynchronous metadata accounting with independent, sampled safety checks.

Disk totals remain observations, not filesystem quotas. Windows job limits bound
committed allocations; the separate combined-RSS limit is sampled. No scientific
file body is read by the accounting helper. Legacy journal limits and elapsed
charging are retained; final accounting has separately reported wall time.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time
import uuid

from src.ball_tracking import crop_retention_resources as resources

ResourceLimitError = resources.ResourceLimitError
GIB = 1024 ** 3
MIB = 1024 ** 2
RECORD_LIMIT = 8192
WORKER_RECEIPT_LIMIT = MIB
FINAL_RESERVE = 65536
POLICY_VERSION = "crop_retention_monitor/v1"
REQUEST_VERSION = "crop_retention_scan_request/v1"
RESPONSE_VERSION = "crop_retention_scan_response/v1"


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _bytes(value):
    return type(value) is int and value >= 0


def monitoring_policy(limits, poll_seconds=.25):
    """Fixed production policy; original limits are neither changed nor rehashed."""
    if not _number(poll_seconds) or not 0 < poll_seconds <= .25:
        raise ValueError("Fast polling must be positive and at most 0.25 seconds")
    for key in ("maximum_worker_memory_bytes", "maximum_total_new_output_bytes",
                "minimum_free_disk_bytes"):
        if not _bytes(limits[key]):
            raise ValueError("Resource byte limits must be nonnegative integers")
    return {
        "schema_version": POLICY_VERSION,
        "scan_timeout_seconds": 10.0,
        "next_scan_seconds": 5.0,
        "maximum_scan_age_seconds": 30.0,
        "maximum_fast_interval_seconds": 1.0,
        "poll_seconds": float(poll_seconds),
        "maximum_combined_rss_bytes": min(limits["maximum_worker_memory_bytes"], 8 * GIB),
        "worker_job_commit_bytes": min(limits["maximum_worker_memory_bytes"], 8 * GIB),
        "scanner_job_commit_bytes": 512 * MIB,
        "maximum_output_bytes": min(limits["maximum_total_new_output_bytes"], 32 * GIB),
        "effective_minimum_free_disk_bytes": max(limits["minimum_free_disk_bytes"], 50 * GIB),
        "final_publication_reserve_bytes": FINAL_RESERVE,
        "record_limit_bytes": RECORD_LIMIT,
        "age_basis": "requested_at of latest accepted complete scan",
        "commit_limit_semantics": "Windows job-wide committed allocation; not RSS",
        "disk_limit_semantics": "sampled whole-root logical bytes; overshoot is possible",
        "elapsed_semantics": "charge through writer shutdown; final accounting reported separately",
    }


def _check_deadline(deadline):
    if time.monotonic() >= deadline:
        raise ResourceLimitError("Output tree did not stabilize for complete byte accounting")


def _checked(path, directory):
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ResourceLimitError("Reparse points and symbolic links are not permitted")
    if directory and not stat.S_ISDIR(info.st_mode):
        raise ResourceLimitError("Expected an ordinary directory")
    if not directory and not stat.S_ISREG(info.st_mode):
        raise ResourceLimitError("Expected an ordinary file")
    return info


def _root_path(root, *, create=False):
    raw = os.fspath(root)
    if not isinstance(raw, str) or "\x00" in raw or ".." in Path(raw).parts:
        raise ValueError("Output root must be an unambiguous Unicode path")
    path = Path(os.path.abspath(raw))  # Deliberately do not resolve indirection.
    if os.name == "nt" and (len(path.drive) != 2 or path.drive[1] != ":"):
        raise ResourceLimitError("Only local drive roots are supported")
    for ancestor in reversed(path.parents):
        _checked(ancestor, True)
    if create:
        path.mkdir(exist_ok=True)
    _checked(path, True)
    return path


def output_bytes(root, *, deadline=None):
    """Two fresh complete inventories, preserving identity/link/maximum semantics.

    The deadline covers root guards, all retries and the final accepted sum.
    The helper's supervisor independently enforces the request's wall deadline.
    """
    deadline = time.monotonic() + 10.0 if deadline is None else deadline
    if not _number(deadline):
        raise ValueError("A finite deadline is required")
    previous = None
    while True:
        _check_deadline(deadline)
        try:
            target = _root_path(root)
            _check_deadline(deadline)
            current = {}

            def fail(error):
                raise error

            for folder, directories, files in os.walk(target, onerror=fail, followlinks=False):
                _check_deadline(deadline)
                _checked(folder, True)
                _check_deadline(deadline)
                for name in directories:
                    _check_deadline(deadline)
                    _checked(Path(folder) / name, True)
                    _check_deadline(deadline)
                for name in files:
                    _check_deadline(deadline)
                    # Fresh lstat is no-follow metadata, never DirEntry's cache.
                    info = _checked(Path(folder) / name, False)
                    _check_deadline(deadline)
                    if info.st_size < 0:
                        raise ResourceLimitError("Negative logical file size")
                    identity = (info.st_dev, info.st_ino)
                    count, maximum = current.get(identity, (0, 0))
                    current[identity] = (count + 1, max(maximum, info.st_size))
            _root_path(target)  # Recheck root/ancestor indirection after traversal.
            _check_deadline(deadline)
            if (previous is not None and previous.keys() <= current.keys()
                    and all(current[key][0] >= count for key, (count, _) in previous.items())):
                measured = sum(count * max(size, previous.get(key, (0, 0))[1])
                               for key, (count, size) in current.items())
                _check_deadline(deadline)
                return measured
            previous = current
        except FileNotFoundError:
            previous = None
        _check_deadline(deadline)


def _record_bytes(value, limit=RECORD_LIMIT):
    # Match the legacy atomic writer's serialization before publishing anything.
    payload = (json.dumps(value, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if len(payload) > limit:
        raise ResourceLimitError("Metadata protocol record exceeds its byte bound")
    return payload


def _write_record(path, value):
    _record_bytes(value)
    # The legacy writer publishes a complete file using a create-only hard link.
    resources._write_new(Path(path), value)
    if Path(path).stat().st_size > RECORD_LIMIT:
        raise ResourceLimitError("Published metadata record exceeds its byte bound")


def _read_record(path, *, with_sha256=False, limit=RECORD_LIMIT):
    before = _checked(path, False)
    if before.st_size > limit:
        raise ResourceLimitError("Metadata protocol record exceeds its byte bound")
    with Path(path).open("rb") as stream:
        payload = stream.read(limit + 1)
    after = _checked(path, False)
    if (len(payload) > limit or
            (before.st_dev, before.st_ino, before.st_size) !=
            (after.st_dev, after.st_ino, after.st_size)):
        raise ResourceLimitError("Metadata protocol record changed during read")
    value = json.loads(payload)
    if type(value) is not dict:
        raise ResourceLimitError("Metadata protocol record must be an object")
    return (value, hashlib.sha256(payload).hexdigest()) if with_sha256 else value


class _JobBasic(ctypes.Structure):
    _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                ("flags", ctypes.c_uint32), ("min_ws", ctypes.c_size_t),
                ("max_ws", ctypes.c_size_t), ("active_limit", ctypes.c_uint32),
                ("affinity", ctypes.c_size_t), ("priority", ctypes.c_uint32),
                ("scheduling", ctypes.c_uint32)]


class _JobIO(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint64) for name in ("ro", "wo", "oo", "rb", "wb", "ob")]


class _JobExtended(ctypes.Structure):
    _fields_ = [("basic", _JobBasic), ("io", _JobIO),
                ("process_memory", ctypes.c_size_t), ("job_memory", ctypes.c_size_t),
                ("peak_process", ctypes.c_size_t), ("peak_job", ctypes.c_size_t)]


def _job_limit_record(commit_limit_bytes):
    if not _bytes(commit_limit_bytes) or not 0 < commit_limit_bytes < 2 ** (8 * ctypes.sizeof(ctypes.c_size_t)):
        raise ValueError("Job committed-memory limit must be a positive SIZE_T")
    info = _JobExtended()
    info.basic.flags = 0x2000 | 0x200  # KILL_ON_JOB_CLOSE | JOB_MEMORY.
    info.job_memory = commit_limit_bytes
    return info


class _WindowsJob(resources._WindowsJob):
    """An owned, kill-on-close tree with an enforced committed-allocation cap."""

    def __init__(self, process, commit_limit_bytes):
        info = _job_limit_record(commit_limit_bytes)
        super().__init__(process)
        # Both worker and helper wait for their gates until this succeeds.
        if not self.kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            error = ctypes.get_last_error()
            self.close()
            raise OSError(error, "Cannot enforce job committed-memory limit")


def _resume_initial_thread(process):
    """Resume only the unique primary thread of a still-suspended owned process."""
    from ctypes import wintypes as w
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)

    class ThreadEntry(ctypes.Structure):
        _fields_ = [("size", w.DWORD), ("usage", w.DWORD), ("thread_id", w.DWORD),
                    ("owner_pid", w.DWORD), ("base_priority", ctypes.c_int32),
                    ("delta_priority", ctypes.c_int32), ("flags", w.DWORD)]

    for name, arguments, result in (
        ("CreateToolhelp32Snapshot", [w.DWORD, w.DWORD], w.HANDLE),
        ("Thread32First", [w.HANDLE, ctypes.POINTER(ThreadEntry)], w.BOOL),
        ("Thread32Next", [w.HANDLE, ctypes.POINTER(ThreadEntry)], w.BOOL),
        ("OpenThread", [w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
        ("GetProcessIdOfThread", [w.HANDLE], w.DWORD),
        ("ResumeThread", [w.HANDLE], w.DWORD),
        ("CloseHandle", [w.HANDLE], w.BOOL),
    ):
        getattr(kernel, name).argtypes, getattr(kernel, name).restype = arguments, result
    snapshot = kernel.CreateToolhelp32Snapshot(0x4, 0)  # TH32CS_SNAPTHREAD.
    if snapshot == ctypes.c_void_p(-1).value:
        raise OSError(ctypes.get_last_error(), "Cannot identify suspended primary thread")
    matches = []
    try:
        entry = ThreadEntry()
        entry.size = ctypes.sizeof(entry)
        ok = kernel.Thread32First(snapshot, ctypes.byref(entry))
        while ok:
            if entry.size < 16:
                raise ResourceLimitError("Truncated Windows thread entry")
            if entry.owner_pid == process.pid:
                matches.append(entry.thread_id)
            entry.size = ctypes.sizeof(entry)
            ok = kernel.Thread32Next(snapshot, ctypes.byref(entry))
        if ctypes.get_last_error() != 18:  # ERROR_NO_MORE_FILES.
            raise OSError(ctypes.get_last_error(), "Cannot enumerate suspended primary thread")
    finally:
        kernel.CloseHandle(snapshot)
    if process.poll() is not None or len(matches) != 1:
        raise ResourceLimitError("Suspended process must have exactly one initial thread")
    # THREAD_SUSPEND_RESUME | THREAD_QUERY_LIMITED_INFORMATION.
    thread = kernel.OpenThread(0x2 | 0x800, False, matches[0])
    if not thread:
        raise OSError(ctypes.get_last_error(), "Cannot open suspended primary thread")
    try:
        owner_pid = kernel.GetProcessIdOfThread(thread)
        if owner_pid != process.pid or process.poll() is not None:
            raise ResourceLimitError("Opened primary-thread handle lost its owned process identity")
        previous = kernel.ResumeThread(thread)
        if previous != 1:
            raise ResourceLimitError("Unexpected initial thread suspend count")
    finally:
        kernel.CloseHandle(thread)


def _spawn_owned(command, *, commit_limit_bytes, cwd, env=None,
                 stdin=None, stdout=None, stderr=None):
    """Assign the job and allocation limit before the first instruction runs.

    This also owns descendants of Windows virtual-environment redirectors.
    No primary thread can spawn a child before job assignment.
    """
    if os.name != "nt":
        raise ResourceLimitError("Owned suspended startup requires Windows")
    process = subprocess.Popen(command, cwd=cwd, env=env, stdin=stdin, stdout=stdout,
                               stderr=stderr,
                               creationflags=subprocess.CREATE_NO_WINDOW | 0x4)  # CREATE_SUSPENDED.
    job = None
    try:
        job = _WindowsJob(process, commit_limit_bytes)
        _resume_initial_thread(process)
        return process, job
    except BaseException:
        _terminate(process, job)
        raise


def _terminate(process, job):
    """Bounded cleanup; a surviving owned process is a failure, never success."""
    try:
        if job is not None:
            job.kill()
        elif process is not None and process.poll() is None:
            process.kill()
        deadline = time.monotonic() + 1.0
        while ((process is not None and process.poll() is None) or
               (job is not None and job.pids())):
            if time.monotonic() >= deadline:
                raise ResourceLimitError("Owned processes did not stop within cleanup allowance")
            time.sleep(.025)
    finally:
        if job is not None:
            job.close()


class _MonitorState:
    """Pure policy/state boundary used by the nonblocking supervisor tick."""

    def __init__(self, limits, started, seconds, policy):
        self.limits, self.started, self.seconds, self.policy = dict(limits), started, seconds, dict(policy)
        self.policy_sha256 = resources._digest(self.policy)
        self.active = self.latest = None
        self.last_tick = None
        self.maximum_interval = self.peak_memory = self.maximum_bytes = 0
        self.minimum_free = None
        self.scan_count = 0

    def request_started(self, now, request_id):
        if self.active is not None:
            raise ResourceLimitError("Overlapping accounting requests are forbidden")
        if not _number(now) or type(request_id) is not str or not request_id:
            raise ResourceLimitError("Invalid accounting request identity/time")
        self.active = {"request_id": request_id, "requested_at": now}

    def accept_scan(self, receipt, now):
        fields = {"schema_version", "request_id", "requested_at", "scan_started_at",
                  "completed_at", "output_bytes", "success", "error", "policy_sha256"}
        if type(receipt) is not dict or set(receipt) != fields or self.active is None:
            raise ResourceLimitError("Unsolicited or malformed accounting response")
        if (receipt["schema_version"] != RESPONSE_VERSION or
                receipt["policy_sha256"] != self.policy_sha256 or
                receipt["request_id"] != self.active["request_id"] or
                receipt["requested_at"] != self.active["requested_at"]):
            raise ResourceLimitError("Accounting response is not bound to the current request")
        stamps = [receipt[key] for key in ("requested_at", "scan_started_at", "completed_at")]
        if (not all(_number(stamp) for stamp in stamps) or not _number(now) or
                not stamps[0] <= stamps[1] <= stamps[2] <= now or
                now - stamps[0] >= self.policy["scan_timeout_seconds"]):
            raise ResourceLimitError("Accounting response is late or has invalid timestamps")
        if receipt["success"] is not True or receipt["error"] is not None or not _bytes(receipt["output_bytes"]):
            raise ResourceLimitError("Accounting helper failed: " + str(receipt.get("error"))[:1024])
        self.latest, self.active = dict(receipt), None
        self.maximum_bytes = max(self.maximum_bytes, receipt["output_bytes"])
        self.scan_count += 1
        if receipt["output_bytes"] > self.policy["maximum_output_bytes"]:
            raise ResourceLimitError("Sampled whole-root output limit exceeded")

    def scan_due(self, now):
        return self.active is None and (self.latest is None or
            now >= self.latest["completed_at"] + self.policy["next_scan_seconds"] - self.policy["poll_seconds"])

    def check(self, now, worker_rss, scanner_rss, free_bytes, *, final=False):
        if (not _number(now) or now < self.started or
                any(not _bytes(value) for value in (worker_rss, scanner_rss, free_bytes))):
            raise ResourceLimitError("Invalid safety measurement")
        if self.last_tick is not None:
            gap = now - self.last_tick
            if gap < 0:
                raise ResourceLimitError("Safety clock moved backwards")
            self.maximum_interval = max(self.maximum_interval, gap)
        self.last_tick = now
        combined = worker_rss + scanner_rss
        self.peak_memory = max(self.peak_memory, combined)
        self.minimum_free = free_bytes if self.minimum_free is None else min(self.minimum_free, free_bytes)
        failures = []
        if self.maximum_interval > self.policy["maximum_fast_interval_seconds"]:
            failures.append("fast_monitor_interval")
        if not final and now - self.started > self.seconds:
            failures.append("time")
        if combined > self.policy["maximum_combined_rss_bytes"]:
            failures.append("combined_worker_scanner_rss")
        if free_bytes < self.policy["effective_minimum_free_disk_bytes"]:
            failures.append("free_disk")
        if self.active is not None and now - self.active["requested_at"] >= self.policy["scan_timeout_seconds"]:
            failures.append("scan_timeout")
        if self.latest is not None and now - self.latest["requested_at"] > self.policy["maximum_scan_age_seconds"]:
            failures.append("stale_accounting")
        if failures:
            raise ResourceLimitError("Resource budget exceeded: " + ", ".join(failures))


class _Scanner:
    """One persistent owned helper, with bounded atomically published file IPC."""

    def __init__(self, root, folder, policy, *, cwd):
        self.root, self.folder, self.cwd = Path(root), Path(folder), cwd
        self.policy = dict(policy)
        self.policy_sha256 = resources._digest(policy)
        self.process = self.job = self.pending = None
        self.index = 0
        self.folder.mkdir(exist_ok=False)
        self.gate = self.folder / "owned.start"

    def request(self, now, request_id):
        if self.pending is not None:
            raise ResourceLimitError("Accounting helper already has a request")
        request = {"schema_version": REQUEST_VERSION, "request_id": request_id,
                   "requested_at": now, "deadline": now + self.policy["scan_timeout_seconds"],
                   "policy_sha256": self.policy_sha256}
        self.pending = self.folder / f"{self.index:06d}.response.json"
        _write_record(self.folder / f"{self.index:06d}.request.json", request)
        self.index += 1
        if self.process is None:
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                   "BALL_RETENTION_START_GATE": str(self.gate)}
            command = [sys.executable, "-B", "-m", "src.ball_tracking.crop_retention_monitor",
                       "--scanner", str(self.root), str(self.folder), self.policy_sha256]
            try:
                self.process, self.job = _spawn_owned(
                    command, commit_limit_bytes=self.policy["scanner_job_commit_bytes"],
                    cwd=str(Path(__file__).absolute().parents[2]), env=env,
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.gate.touch(exist_ok=False)
            except BaseException:
                _terminate(self.process, self.job)
                raise

    def poll(self):
        if self.process is None:
            return None
        if self.process.poll() is not None:
            raise ResourceLimitError("Accounting helper exited unexpectedly")
        if self.pending is not None and self.pending.exists():
            value = _read_record(self.pending)
            self.pending = None
            return value
        return None

    def rss(self):
        return sum(resources._rss(pid) for pid in self.job.pids()) if self.job is not None else 0

    def close(self):
        _terminate(self.process, self.job)
        self.job = None


def _scanner_main(root, folder, policy_sha256):
    resources.wait_for_supervisor()
    root, folder = _root_path(root), _root_path(folder)
    if not folder.is_relative_to(root):
        raise ResourceLimitError("Accounting protocol must be inside the counted root")
    index = 0
    while True:
        path = folder / f"{index:06d}.request.json"
        if not path.exists():
            time.sleep(.025)
            continue
        request = _read_record(path)
        fields = {"schema_version", "request_id", "requested_at", "deadline", "policy_sha256"}
        if (set(request) != fields or request["schema_version"] != REQUEST_VERSION or
                request["policy_sha256"] != policy_sha256 or
                type(request["request_id"]) is not str or not request["request_id"] or
                not _number(request["requested_at"]) or not _number(request["deadline"]) or
                not 0 < request["deadline"] - request["requested_at"] <= 10):
            raise ResourceLimitError("Malformed accounting request")
        scan_started = time.monotonic()
        total, error = None, None
        try:
            total = output_bytes(root, deadline=request["deadline"])
        except Exception as failure:
            error = f"{type(failure).__name__}: {failure}"[:1024]
        response = {"schema_version": RESPONSE_VERSION, "request_id": request["request_id"],
                    "requested_at": request["requested_at"], "scan_started_at": scan_started,
                    "completed_at": time.monotonic(), "output_bytes": total,
                    "success": error is None, "error": error, "policy_sha256": policy_sha256}
        _write_record(folder / f"{index:06d}.response.json", response)
        index += 1


def _append(journal, kind, **details):
    # Legacy journal envelope adds only fixed-size timestamps and SHA256 strings.
    # Bound details to16KiB, leaving a generous32KiB complete-event allowance.
    _record_bytes(details, 16384)
    return journal.append(kind, **details)


def _run_supervised(output_root, unit_key, command, limits, *, cwd, selection_unit=False,
                    env=None, poll_seconds=.25, require_result=False, journal_factory=None):
    if os.name != "nt":
        raise ResourceLimitError("This monitor requires Windows owned jobs")
    policy = monitoring_policy(limits, poll_seconds)
    target = _root_path(output_root, create=True)
    journal = (resources.BudgetJournal if journal_factory is None else journal_factory)(target, limits)
    attempt_id, seconds = journal.reserve(unit_key, selection_unit)
    started = time.monotonic()
    state = _MonitorState(limits, started, seconds, policy)
    attempts = target / "attempts"
    attempts.mkdir(exist_ok=True)
    log_path = attempts / (attempt_id + ".log")
    gate = attempts / (attempt_id + ".start")
    result_path = attempts / (attempt_id + ".result.json")
    policy_path = attempts / (attempt_id + ".monitoring_policy.json")
    worker = job = scanner = log = None
    failure = accounting_error = result_binding = None
    result_code = None
    samples = 0
    last_sample = -1.0
    charged = None
    final_scan = None
    cleanup_errors = []

    def request_scan():
        now = time.monotonic()
        request_id = uuid.uuid4().hex
        state.request_started(now, request_id)
        scanner.request(now, request_id)

    def tick(*, final=False):
        nonlocal samples, last_sample
        now = time.monotonic()  # Tick-start cadence includes all work below.
        worker_rss = sum(resources._rss(pid) for pid in job.pids()) if job is not None else 0
        scanner_rss = scanner.rss() if scanner is not None else 0
        free = shutil.disk_usage(target).free
        state.check(now, worker_rss, scanner_rss, free, final=final)
        response = scanner.poll() if scanner is not None else None
        if response is not None:
            state.accept_scan(response, time.monotonic())
        elapsed = charged if final else time.monotonic() - started
        # Final scans run after all writers stop. Do not publish periodic journal
        # files during that phase: the final64KiB reserve then covers only the
        # <=8KiB response, <=32KiB finished event and tiny completion seal.
        if not final and (now - last_sample >= .95 or response is not None):
            _append(journal, "sample", attempt_id=attempt_id, elapsed_seconds=elapsed,
                    monitoring_policy_sha256=state.policy_sha256,
                    memory_bytes=worker_rss + scanner_rss, scanner_memory_bytes=scanner_rss,
                    output_bytes=state.latest["output_bytes"] if state.latest else None,
                    free_disk_bytes=free, scan=state.latest,
                    wall_elapsed_seconds=now - started, final_accounting_phase=final)
            last_sample = now
            samples += 1
        completed = time.monotonic()
        duration = completed - now
        if duration > policy["maximum_fast_interval_seconds"]:
            state.maximum_interval = max(state.maximum_interval, duration)
            raise ResourceLimitError("Fast safety tick itself exceeded its interval limit")
        if not final and completed - started > seconds:
            raise ResourceLimitError("Resource budget exceeded: time")
        return completed

    def await_scan(*, final=False):
        while state.active is not None:
            tick(final=final)
            if state.active is not None:
                time.sleep(policy["poll_seconds"])

    try:
        _write_record(policy_path, {"policy": policy, "sha256": state.policy_sha256})
        scanner = _Scanner(target, attempts / (attempt_id + ".monitor"), policy, cwd=cwd)
        tick()  # Check cheap constraints before starting even the helper.
        request_scan()
        await_scan()  # Complete whole-root preflight before creating/releasing worker.
        temporary = attempts / (attempt_id + ".temp")
        temporary.mkdir()
        child_env = {**os.environ, **(env or {}), "PYTHONDONTWRITEBYTECODE": "1",
                     "TMP": str(temporary), "TEMP": str(temporary), "TMPDIR": str(temporary),
                     "BALL_RETENTION_START_GATE": str(gate), "BALL_RETENTION_PARENT_PID": str(os.getpid()),
                     "BALL_RETENTION_ATTEMPT_ID": attempt_id, "BALL_RETENTION_RESULT_PATH": str(result_path)}
        log = log_path.open("xb")
        worker, job = _spawn_owned(command, commit_limit_bytes=policy["worker_job_commit_bytes"],
                                   cwd=cwd, env=child_env, stdout=log, stderr=subprocess.STDOUT)
        tick()
        gate.touch(exist_ok=False)
        while worker.poll() is None:
            now = tick()
            if state.scan_due(now):
                if state.latest is not None and now - state.latest["completed_at"] > policy["next_scan_seconds"]:
                    raise ResourceLimitError("Next accounting dispatch missed its deadline")
                request_scan()
            time.sleep(policy["poll_seconds"])
        result_code = worker.returncode
        tick()
        if job.pids():
            raise ResourceLimitError("Worker exited with owned descendants still active")
        if result_code:
            raise ResourceLimitError(f"Worker failed with exit code {result_code}; see {log_path}")
        if require_result and not result_path.is_file():
            raise ResourceLimitError("Worker exited without a completion receipt")
        if result_path.is_file():
            receipt, receipt_hash = _read_record(result_path, with_sha256=True,
                                                 limit=WORKER_RECEIPT_LIMIT)
            result_binding = {"path": result_path.relative_to(target).as_posix(),
                              "sha256": receipt_hash}
            del receipt
    except BaseException as error:
        failure = f"{type(error).__name__}: {error}"[:2048]
    finally:
        try:
            _terminate(worker, job)
        except BaseException as error:
            cleanup_errors.append(f"worker: {type(error).__name__}: {error}"[:1024])
            failure = failure or cleanup_errors[-1]
        job = None
        if worker is not None:
            result_code = worker.returncode
        if log is not None:
            log.close()
        charged = time.monotonic() - started
        try:
            if scanner is None:
                raise ResourceLimitError("Accounting helper was not established")
            # A pre-shutdown in-flight measurement cannot certify final state.
            await_scan(final=True)
            request_scan()
            await_scan(final=True)
            final_scan = state.latest
        except BaseException as error:
            accounting_error = f"{type(error).__name__}: {error}"[:2048]
            failure = failure or accounting_error
        try:
            if scanner is not None:
                scanner.close()
        except BaseException as error:
            cleanup_errors.append(f"scanner: {type(error).__name__}: {error}"[:1024])
            failure = failure or cleanup_errors[-1]
        try:
            final_free = shutil.disk_usage(target).free
        except BaseException as error:
            final_free = 0
            failure = failure or f"Final free-space check failed: {type(error).__name__}: {error}"[:2048]
        bound = state.maximum_bytes + FINAL_RESERVE
        if (charged > seconds or bound > policy["maximum_output_bytes"] or
                final_free - FINAL_RESERVE < policy["effective_minimum_free_disk_bytes"]):
            failure = failure or "ResourceLimitError: final time/output/free-disk bound exceeded"
        total_wall = time.monotonic() - started
        _append(journal, "finished", attempt_id=attempt_id, elapsed_seconds=charged,
                charged_elapsed_seconds=charged, total_wall_seconds_before_publication=total_wall,
                success=failure is None, exit_code=result_code, failure=failure,
                monitoring_policy_sha256=state.policy_sha256,
                monitoring_policy_path=policy_path.relative_to(target).as_posix(),
                peak_worker_memory_bytes=state.peak_memory, maximum_output_bytes=state.maximum_bytes,
                time_budget_seconds=seconds, time_overshoot_seconds=max(0, charged - seconds),
                memory_overshoot_bytes=max(0, state.peak_memory - policy["maximum_combined_rss_bytes"]),
                output_overshoot_bytes=max(0, state.maximum_bytes - policy["maximum_output_bytes"]),
                final_accounting_output_bound_bytes=bound, final_accounting_error=accounting_error,
                final_scan=final_scan, maximum_monitor_interval_seconds=state.maximum_interval,
                minimum_free_disk_bytes=min(state.minimum_free if state.minimum_free is not None else final_free,
                                            final_free),
                monitor_samples=samples, completed_scans=state.scan_count, cleanup_errors=cleanup_errors,
                owned_cleanup_verified=not cleanup_errors,
                log_path=log_path.relative_to(target).as_posix(), worker_result=result_binding)
    if failure:
        raise ResourceLimitError(failure)
    return journal.events[-1]


def run_supervised(output_root, unit_key, command, limits, *, cwd, selection_unit=False,
                   env=None, poll_seconds=.25, require_result=False, journal_factory=None):
    """Run one gated worker using the fixed policy and one owned metadata helper.

    journal_factory only supports a stricter provenance-aware journal; it does
    not supply scanners, clocks, safety measurements or policy overrides.
    Workers must call the existing resources.wait_for_supervisor() before work.
    """
    target = _root_path(output_root, create=True)
    lock = target / "supervisor.lock"
    if lock.exists():
        owner = _read_record(lock)
        if resources._alive(owner["pid"]):
            raise ResourceLimitError("Another supervisor owns this output root")
        lock.unlink()
    token = uuid.uuid4().hex
    try:
        _write_record(lock, {"pid": os.getpid(), "token": token})
    except FileExistsError as error:
        raise ResourceLimitError("Concurrent supervisor acquired the output root") from error
    try:
        return _run_supervised(target, unit_key, command, limits, cwd=cwd,
                               selection_unit=selection_unit, env=env,
                               poll_seconds=poll_seconds, require_result=require_result,
                               journal_factory=journal_factory)
    finally:
        owner = _read_record(lock)
        if owner.get("token") != token or owner.get("pid") != os.getpid():
            raise ResourceLimitError("Supervisor lock ownership changed")
        lock.unlink()


if __name__ == "__main__":
    if len(sys.argv) != 5 or sys.argv[1] != "--scanner":
        raise SystemExit("Only the owned accounting-helper entry point is supported")
    _scanner_main(sys.argv[2], sys.argv[3], sys.argv[4])
