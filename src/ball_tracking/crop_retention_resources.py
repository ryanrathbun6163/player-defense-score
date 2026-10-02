"""Persistent resource accounting and monitored, owned worker processes."""
from __future__ import annotations

import ctypes
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import uuid


class ResourceLimitError(RuntimeError):
    pass


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def _write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / (".pending_" + path.name + "_" + uuid.uuid4().hex)
    with temporary.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    # A worker can read the journal while its supervisor appends samples.
    # Hard-link publication is atomic and refuses an existing destination.
    os.link(temporary, path)
    temporary.unlink()


def output_bytes(root):
    # Writers may grow or rewrite a file while publishing an output. Compare
    # membership, including hard-link multiplicity, across two complete scans.
    # New identities/links may appear, but none observed in the first complete
    # scan may disappear or lose entries in the second accepted scan.
    # The larger observed size is conservative for those scans, not an upper
    # bound on future growth between monitor samples.
    deadline = time.monotonic() + .5

    def check_deadline():
        if time.monotonic() >= deadline:
            raise ResourceLimitError("Output tree did not stabilize for complete byte accounting")

    previous = None
    while True:
        check_deadline()
        try:
            current = {}
            def fail(error):
                raise error
            for folder, _, files in os.walk(root, onerror=fail):
                check_deadline()
                for name in files:
                    check_deadline()
                    info = (Path(folder)/name).stat()
                    check_deadline()
                    identity = (info.st_dev, info.st_ino)
                    count, size = current.get(identity, (0, 0))
                    current[identity] = (count + 1, max(size, info.st_size))
            check_deadline()
            if (previous is not None and previous.keys() <= current.keys()
                    and all(current[key][0] >= count for key, (count, _) in previous.items())):
                measured = sum(count * max(size, previous.get(key, (0, 0))[1])
                               for key, (count, size) in current.items())
                check_deadline()
                return measured
            previous = current
        except FileNotFoundError:
            previous = None
        check_deadline()


class BudgetJournal:
    """Append-only hash chain. Unclosed attempts retain their whole reservation."""

    def __init__(self, output_root, limits):
        self.root = Path(output_root)
        self.folder = self.root / "resource_events"
        self.limits = dict(limits)
        self.events = []
        previous = None
        if self.folder.exists():
            for index, path in enumerate(sorted(self.folder.glob("*.json"))):
                if path.name != f"{index:08d}.json":
                    raise ResourceLimitError("Missing/reordered resource journal event")
                value = json.loads(path.read_text(encoding="utf-8"))
                claimed = value.pop("sha256")
                if (value.get("previous_sha256") != previous or _digest(value) != claimed
                        or value.get("limits_sha256") != _digest(self.limits)):
                    raise ResourceLimitError("Resource journal or approved limits changed")
                value["sha256"] = claimed
                self.events.append(value)
                previous = claimed
        attempts = self._attempts()
        for path in (self.root / "attempts").glob("*"):
            if path.name.startswith(".pending_"):
                continue  # Incomplete publication still counts toward byte limits.
            attempt = attempts.get(path.name.split(".")[0])
            if attempt is None:
                raise ResourceLimitError("Orphan attempt evidence; resource history cannot be reset")
            if path.name.endswith(".completion.json"):
                seal = json.loads(path.read_text(encoding="utf-8"))
                if attempt["finished"] is None or seal["event_sha256"] != attempt["finished"]["sha256"]:
                    raise ResourceLimitError("Truncated or changed completed resource history")
            if path.name.endswith(".reservation.json"):
                if json.loads(path.read_text(encoding="utf-8"))["event_sha256"] != attempt["start"]["sha256"]:
                    raise ResourceLimitError("Changed resource reservation")

    def append(self, kind, **details):
        value = {"kind": kind, "recorded_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 "previous_sha256": self.events[-1]["sha256"] if self.events else None,
                 "limits_sha256": _digest(self.limits), **details}
        value["sha256"] = _digest(value)
        _write_new(self.folder / f"{len(self.events):08d}.json", value)
        self.events.append(value)
        if kind == "finished":
            _write_new(self.root / "attempts" / (details["attempt_id"] + ".completion.json"),
                       {"event_sha256": value["sha256"]})
        return value

    def _attempts(self):
        attempts = {}
        for event in self.events:
            kind = event["kind"]
            if kind == "started":
                key = event["attempt_id"]
                reserve = event["reserved_seconds"]
                if (key in attempts or isinstance(reserve, bool) or not isinstance(reserve, (int, float))
                        or not math.isfinite(reserve) or reserve <= 0):
                    raise ResourceLimitError("Invalid resource reservation")
                attempts[key] = {"start": event, "finished": None, "last_elapsed": 0.0}
            elif kind in ("sample", "finished"):
                item = attempts.get(event.get("attempt_id"))
                elapsed = event.get("elapsed_seconds")
                if (item is None or item["finished"] is not None or isinstance(elapsed, bool)
                        or not isinstance(elapsed, (int, float)) or not math.isfinite(elapsed)
                        or elapsed < item["last_elapsed"]):
                    raise ResourceLimitError("Invalid/nonmonotone resource accounting")
                item["last_elapsed"] = elapsed
                if kind == "finished":
                    item["finished"] = event
            else:
                raise ResourceLimitError("Unknown resource event")
        return attempts

    def consumed(self, unit_key=None):
        total = 0.0
        for item in self._attempts().values():
            if unit_key is None or item["start"]["unit_key"] == unit_key:
                # After abrupt interruption, never reset time to the last tick.
                total += (item["finished"]["elapsed_seconds"] if item["finished"]
                          else max(item["start"]["reserved_seconds"], item["last_elapsed"]))
        return total

    def reserve(self, unit_key, selection_unit):
        remaining = self.limits["maximum_cumulative_seconds"] - self.consumed()
        if selection_unit:
            remaining = min(remaining, self.limits["maximum_seconds_per_unit"] - self.consumed(unit_key))
        if remaining <= 0:
            raise ResourceLimitError("Approved cumulative or unit execution budget exhausted")
        attempt_id = uuid.uuid4().hex
        self.append("started", attempt_id=attempt_id, unit_key=unit_key,
                    selection_unit=selection_unit, reserved_seconds=remaining)
        _write_new(self.root / "attempts" / (attempt_id + ".reservation.json"),
                   {"event_sha256": self.events[-1]["sha256"]})
        return attempt_id, remaining


class _WindowsJob:
    """Kill-on-close prevents orphaned workers if the supervisor exits."""

    def __init__(self, process):
        from ctypes import wintypes as w
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel = k
        for name, arguments, result in (
            ("CreateJobObjectW", [ctypes.c_void_p, w.LPCWSTR], w.HANDLE),
            ("SetInformationJobObject", [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD], w.BOOL),
            ("AssignProcessToJobObject", [w.HANDLE, w.HANDLE], w.BOOL),
            ("QueryInformationJobObject", [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p], w.BOOL),
            ("TerminateJobObject", [w.HANDLE, w.UINT], w.BOOL),
            ("CloseHandle", [w.HANDLE], w.BOOL),
        ):
            getattr(k, name).argtypes, getattr(k, name).restype = arguments, result

        class Basic(ctypes.Structure):
            _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                        ("flags", w.DWORD), ("min_ws", ctypes.c_size_t), ("max_ws", ctypes.c_size_t),
                        ("active_limit", w.DWORD), ("affinity", ctypes.c_size_t),
                        ("priority", w.DWORD), ("scheduling", w.DWORD)]

        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in ("ro", "wo", "oo", "rb", "wb", "ob")]

        class Extended(ctypes.Structure):
            _fields_ = [("basic", Basic), ("io", IO), ("process_memory", ctypes.c_size_t),
                        ("job_memory", ctypes.c_size_t), ("peak_process", ctypes.c_size_t),
                        ("peak_job", ctypes.c_size_t)]

        self.handle = k.CreateJobObjectW(None, None)
        if not self.handle:
            raise OSError(ctypes.get_last_error(), "Cannot create worker job")
        info = Extended()
        info.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE.
        if (not k.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info))
                or not k.AssignProcessToJobObject(self.handle, w.HANDLE(process._handle))):
            error = ctypes.get_last_error()
            self.close()
            raise OSError(error, "Cannot supervise entire worker process tree")

    def pids(self):
        # Job membership is inherited by descendants; PID identity remains job-scoped.
        capacity = 64
        while capacity <= 65536:
            buffer = ctypes.create_string_buffer(8 + capacity * ctypes.sizeof(ctypes.c_size_t))
            ok = self.kernel.QueryInformationJobObject(self.handle, 3, buffer, len(buffer), None)
            assigned, count = (ctypes.c_uint32 * 2).from_buffer(buffer)
            if ok:
                return list((ctypes.c_size_t * count).from_buffer(buffer, 8))
            if ctypes.get_last_error() != 234:
                raise OSError(ctypes.get_last_error(), "Cannot enumerate worker job")
            capacity = max(capacity * 2, assigned)
        raise ResourceLimitError("Unbounded worker process tree")

    def kill(self):
        if self.handle:
            self.kernel.TerminateJobObject(self.handle, 1)

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def _rss(pid):
    if os.name != "nt":
        try:
            for line in Path(f"/proc/{pid}/status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
            return 0
        except FileNotFoundError:
            return 0
    from ctypes import wintypes as w
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.OpenProcess.argtypes, kernel.OpenProcess.restype = [w.DWORD, w.BOOL, w.DWORD], w.HANDLE
    kernel.CloseHandle.argtypes, kernel.CloseHandle.restype = [w.HANDLE], w.BOOL

    class Counters(ctypes.Structure):
        _fields_ = [("cb", w.DWORD), ("faults", w.DWORD)] + [(name, ctypes.c_size_t) for name in
                      ("peak_ws", "ws", "peak_paged", "paged", "peak_nonpaged", "nonpaged", "pagefile", "peak_pagefile")]

    psapi.GetProcessMemoryInfo.argtypes = [w.HANDLE, ctypes.POINTER(Counters), w.DWORD]
    psapi.GetProcessMemoryInfo.restype = w.BOOL
    handle = kernel.OpenProcess(0x0400 | 0x0010, False, pid)
    if not handle:
        # A process may exit between job enumeration and OpenProcess.
        if ctypes.get_last_error() == 87:
            return 0
        raise OSError(ctypes.get_last_error(), "Cannot account worker memory")
    try:
        value = Counters()
        value.cb = ctypes.sizeof(value)
        if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(value), value.cb):
            raise OSError(ctypes.get_last_error(), "Cannot read worker memory")
        return value.ws
    finally:
        kernel.CloseHandle(handle)


def _posix_pids(parent):
    parents = {}
    for path in Path("/proc").glob("[0-9]*/status"):
        try:
            lines = path.read_text().splitlines()
            parents[int(path.parent.name)] = int(next(v.split()[1] for v in lines if v.startswith("PPid:")))
        except (FileNotFoundError, ProcessLookupError, StopIteration):
            continue
    found = {parent}
    while True:
        more = {pid for pid, ppid in parents.items() if ppid in found}
        if more <= found:
            return found
        found |= more


def _run_supervised(output_root, unit_key, command, limits, *, cwd, selection_unit=False,
                    env=None, poll_seconds=.25, require_result=False):
    """Run an owned command; persist budgets, logs, failure and overshoot receipts."""
    if not 0 < poll_seconds <= 1:
        raise ValueError("Resource monitor must sample at least once per second")
    target = Path(output_root).resolve()
    target.mkdir(parents=True, exist_ok=True)
    journal = BudgetJournal(target, limits)
    attempt_id, seconds = journal.reserve(unit_key, selection_unit)
    started = time.monotonic()
    attempts = target / "attempts"
    attempts.mkdir(exist_ok=True)
    log_path = attempts / f"{attempt_id}.log"
    gate = attempts / f"{attempt_id}.start"
    result_path = attempts / f"{attempt_id}.result.json"
    worker = job = None
    peak = maximum_bytes = 0
    failure = None
    result_code = None
    samples = 0
    last_sample = -1.0
    result_binding = None
    last_tick = None
    maximum_interval = 0.0
    minimum_free = None

    def snapshot():
        nonlocal peak, maximum_bytes, samples, last_sample, last_tick, maximum_interval, minimum_free
        elapsed = time.monotonic() - started
        # Descendants can outlive the root worker; keep accounting the owned job.
        pids = job.pids() if job else (_posix_pids(worker.pid) if worker and worker.poll() is None else [])
        memory = sum(_rss(pid) for pid in pids)
        size = output_bytes(target)
        free = shutil.disk_usage(target).free
        now = time.monotonic()
        if last_tick is not None:
            maximum_interval = max(maximum_interval, now-last_tick)
        last_tick = now
        elapsed = now-started
        minimum_free = free if minimum_free is None else min(minimum_free, free)
        peak, maximum_bytes = max(peak, memory), max(maximum_bytes, size)
        if elapsed - last_sample >= .95 or worker is None or worker.poll() is not None:
            journal.append("sample", attempt_id=attempt_id, elapsed_seconds=elapsed,
                           memory_bytes=memory, output_bytes=size, free_disk_bytes=free)
            samples += 1
            last_sample = elapsed
        exceeded = []
        if elapsed > seconds:
            exceeded.append("time")
        if memory > limits["maximum_worker_memory_bytes"]:
            exceeded.append("worker_memory")
        if size > limits["maximum_total_new_output_bytes"]:
            exceeded.append("output_bytes")
        if free < limits["minimum_free_disk_bytes"]:
            exceeded.append("free_disk")
        if maximum_interval > 1:
            exceeded.append("monitor_interval")
        if exceeded:
            raise ResourceLimitError("Resource budget exceeded: " + ", ".join(exceeded))

    try:
        snapshot()
        with log_path.open("xb") as log:
            temporary_dir = attempts / (attempt_id + ".temp")
            temporary_dir.mkdir()
            child_env = {**os.environ, **(env or {}), "PYTHONDONTWRITEBYTECODE": "1",
                         "TMP": str(temporary_dir), "TEMP": str(temporary_dir), "TMPDIR": str(temporary_dir),
                         "BALL_RETENTION_START_GATE": str(gate), "BALL_RETENTION_PARENT_PID": str(os.getpid()),
                         "BALL_RETENTION_ATTEMPT_ID": attempt_id, "BALL_RETENTION_RESULT_PATH": str(result_path)}
            worker = subprocess.Popen(command, cwd=cwd, env=child_env, stdout=log, stderr=subprocess.STDOUT,
                                      creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                                      start_new_session=os.name != "nt")
            if os.name == "nt":
                job = _WindowsJob(worker)
            gate.touch(exist_ok=False)
            while worker.poll() is None:
                snapshot()
                time.sleep(poll_seconds)
            result_code = worker.returncode
            snapshot()
            if job and job.pids():
                raise ResourceLimitError("Worker exited while owned descendants were still active")
            if result_code:
                raise ResourceLimitError(f"Worker failed with exit code {result_code}; see {log_path}")
            if require_result and not result_path.is_file():
                raise ResourceLimitError("Worker exited without a completion receipt")
            if result_path.is_file():
                result_binding = {"path": result_path.relative_to(target).as_posix(),
                                  "sha256": hashlib.sha256(result_path.read_bytes()).hexdigest()}
            snapshot()
    except BaseException as error:
        failure = f"{type(error).__name__}: {error}"
        if job:
            job.kill()
        if worker and worker.poll() is None:
            if not job and os.name == "nt":
                worker.kill()
            elif not job:
                os.killpg(worker.pid, signal.SIGKILL)
            worker.wait(timeout=30)
        result_code = worker.returncode if worker else None
    finally:
        if job:
            job.close()
        elapsed = time.monotonic() - started
        accounting_error = None
        try:
            maximum_bytes = max(maximum_bytes, output_bytes(target))
            final_free = shutil.disk_usage(target).free
        except (OSError, ResourceLimitError) as error:
            accounting_error = f"{type(error).__name__}: {error}"
            failure = failure or accounting_error
            final_free = 0
        # Reserve room for the immutable final event and its completion seal.
        # This is a conservative accounting bound, not a data-truncation policy.
        accounting_bound = maximum_bytes + 16384
        minimum_free = final_free if minimum_free is None else min(minimum_free, final_free)
        if failure is None and (elapsed > seconds or accounting_bound > limits["maximum_total_new_output_bytes"]
                                or final_free-16384 < limits["minimum_free_disk_bytes"]):
            failure = "ResourceLimitError: final time/output/free-disk accounting would exceed the approved budget"
        journal.append("finished", attempt_id=attempt_id, elapsed_seconds=elapsed,
                       success=failure is None, exit_code=result_code, failure=failure,
                       peak_worker_memory_bytes=peak, maximum_output_bytes=maximum_bytes,
                       time_budget_seconds=seconds, time_overshoot_seconds=max(0, elapsed-seconds),
                       memory_overshoot_bytes=max(0, peak-limits["maximum_worker_memory_bytes"]),
                       output_overshoot_bytes=max(0, maximum_bytes-limits["maximum_total_new_output_bytes"]),
                       final_accounting_output_bound_bytes=accounting_bound,
                       final_accounting_error=accounting_error,
                       maximum_monitor_interval_seconds=maximum_interval, minimum_free_disk_bytes=minimum_free,
                       monitor_samples=samples, log_path=log_path.relative_to(target).as_posix(),
                       worker_result=result_binding)
    if failure:
        raise ResourceLimitError(failure)
    return journal.events[-1]


def _alive(pid):
    if os.name != "nt":
        return Path(f"/proc/{pid}").exists()
    from ctypes import wintypes as w
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes, kernel.OpenProcess.restype = [w.DWORD, w.BOOL, w.DWORD], w.HANDLE
    kernel.GetExitCodeProcess.argtypes, kernel.GetExitCodeProcess.restype = [w.HANDLE, ctypes.POINTER(w.DWORD)], w.BOOL
    kernel.CloseHandle.argtypes = [w.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return ctypes.get_last_error() != 87  # Denied means unknown/live, never remove its lock.
    try:
        code = w.DWORD()
        return not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value == 259
    finally:
        kernel.CloseHandle(handle)


def run_supervised(output_root, unit_key, command, limits, **kwargs):
    target = Path(output_root).resolve()
    target.mkdir(parents=True, exist_ok=True)
    lock = target / "supervisor.lock"
    if lock.exists():
        owner = json.loads(lock.read_text(encoding="utf-8"))
        if _alive(owner["pid"]):
            raise ResourceLimitError("Another supervisor owns this output root")
        lock.unlink()  # Only this validated, stale lock; never remove run evidence.
    try:
        _write_new(lock, {"pid": os.getpid(), "token": uuid.uuid4().hex})
    except FileExistsError as error:
        raise ResourceLimitError("Concurrent supervisor acquired the output root") from error
    try:
        return _run_supervised(target, unit_key, command, limits, **kwargs)
    finally:
        lock.unlink()


def wait_for_supervisor():
    """Workers wait until job ownership exists, before touching experiment data."""
    value = os.environ.get("BALL_RETENTION_START_GATE")
    if not value:
        raise ResourceLimitError("Worker must be started by the resource supervisor")
    start = time.monotonic()
    while not Path(value).is_file():
        if time.monotonic() - start > 30:
            raise ResourceLimitError("Supervisor did not release worker start gate")
        time.sleep(.05)
