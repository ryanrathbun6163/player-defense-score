"""Run one explicitly requested GPU module in an owned Windows job with telemetry.

The job is assigned before the process starts, includes its descendants, and is
killed if this supervisor exits. A STOP file first requests KeyboardInterrupt;
after ten seconds only the owned job is terminated. No settings are changed.
"""
from __future__ import annotations

import argparse
import csv
import ctypes
from ctypes import wintypes as wt
from datetime import datetime, timezone
import hashlib
import json
import msvcrt
import os
from pathlib import Path
import subprocess
import sys
import time


FIELDS = ["uuid", "temperature.gpu", "temperature.gpu.tlimit", "utilization.gpu",
          "utilization.memory", "memory.used", "memory.total", "power.draw",
          "power.limit", "fan.speed", "clocks_event_reasons.sw_thermal_slowdown",
          "clocks_event_reasons.hw_thermal_slowdown", "clocks_event_reasons.hw_power_brake_slowdown"]
GPU = "GPU-f26f32f8-e85b-0d38-651e-d5c54097525b"


def stamp():
    return datetime.now(timezone.utc).isoformat()


def write_once(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def parse_sample(stdout, expected_gpu=GPU):
    rows = list(csv.reader(stdout.strip().splitlines()))
    if len(rows) != 1 or len(rows[0]) != len(FIELDS):
        raise ValueError("Unexpected NVIDIA telemetry format")
    values = dict(zip(FIELDS, (v.strip() for v in rows[0])))
    if values["uuid"] != expected_gpu:
        raise ValueError("GPU identity changed")
    if not 0 <= float(values["temperature.gpu"]) < 150:
        raise ValueError("Invalid temperature telemetry")
    return values


def stop_reason(values):
    if float(values["temperature.gpu"]) >= 80:
        return "operational_temperature_stop_at_80C"
    for key in ("clocks_event_reasons.sw_thermal_slowdown", "clocks_event_reasons.hw_thermal_slowdown"):
        if values[key].lower() == "active":
            return key
    return None


def sample():
    result = subprocess.run(["nvidia-smi", "--query-gpu=" + ",".join(FIELDS),
        "--format=csv,noheader,nounits", "--id=" + GPU], capture_output=True,
        text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError("NVIDIA telemetry failed: " + result.stderr)
    return {"recorded_at_utc": stamp(), "values": parse_sample(result.stdout)}


class _Startup(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("lpReserved", wt.LPWSTR), ("lpDesktop", wt.LPWSTR),
        ("lpTitle", wt.LPWSTR), ("dwX", wt.DWORD), ("dwY", wt.DWORD),
        ("dwXSize", wt.DWORD), ("dwYSize", wt.DWORD), ("dwXCountChars", wt.DWORD),
        ("dwYCountChars", wt.DWORD), ("dwFillAttribute", wt.DWORD),
        ("dwFlags", wt.DWORD), ("wShowWindow", wt.WORD), ("cbReserved2", wt.WORD),
        ("lpReserved2", ctypes.POINTER(wt.BYTE)), ("hStdInput", wt.HANDLE),
        ("hStdOutput", wt.HANDLE), ("hStdError", wt.HANDLE)]


class _Process(ctypes.Structure):
    _fields_ = [("hProcess", wt.HANDLE), ("hThread", wt.HANDLE),
                ("dwProcessId", wt.DWORD), ("dwThreadId", wt.DWORD)]


class _BasicLimits(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wt.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wt.DWORD),
        ("Affinity", ctypes.c_size_t), ("PriorityClass", wt.DWORD), ("SchedulingClass", wt.DWORD)]


class _Io(ctypes.Structure):
    _fields_ = [(k, ctypes.c_ulonglong) for k in
        ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
         "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", _BasicLimits), ("IoInfo", _Io),
        ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]


class _Accounting(ctypes.Structure):
    _fields_ = [(k, ctypes.c_longlong) for k in ("TotalUserTime", "TotalKernelTime",
        "ThisPeriodTotalUserTime", "ThisPeriodTotalKernelTime")] + [(k, wt.DWORD) for k in
        ("TotalPageFaultCount", "TotalProcesses", "ActiveProcesses", "TotalTerminatedProcesses")]


class OwnedJob:
    """A handle-based process tree, assigned while the executable is suspended."""
    def __init__(self, command, cwd, log):
        if os.name != "nt":
            raise RuntimeError("This supervisor requires Windows")
        self.k = ctypes.WinDLL("kernel32", use_last_error=True)
        declarations = {
            "CreateJobObjectW": ([ctypes.c_void_p, wt.LPCWSTR], wt.HANDLE),
            "SetInformationJobObject": ([wt.HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD], wt.BOOL),
            "CreateProcessW": ([wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wt.BOOL,
                wt.DWORD, ctypes.c_void_p, wt.LPCWSTR, ctypes.POINTER(_Startup), ctypes.POINTER(_Process)], wt.BOOL),
            "AssignProcessToJobObject": ([wt.HANDLE, wt.HANDLE], wt.BOOL),
            "ResumeThread": ([wt.HANDLE], wt.DWORD),
            "GetExitCodeProcess": ([wt.HANDLE, ctypes.POINTER(wt.DWORD)], wt.BOOL),
            "WaitForSingleObject": ([wt.HANDLE, wt.DWORD], wt.DWORD),
            "QueryInformationJobObject": ([wt.HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD, ctypes.c_void_p], wt.BOOL),
            "TerminateJobObject": ([wt.HANDLE, wt.UINT], wt.BOOL),
            "TerminateProcess": ([wt.HANDLE, wt.UINT], wt.BOOL),
            "CloseHandle": ([wt.HANDLE], wt.BOOL),
        }
        for name, (args, result) in declarations.items():
            fn = getattr(self.k, name)
            fn.argtypes, fn.restype = args, result
        self.job = self.k.CreateJobObjectW(None, None)
        self.process = None
        if not self.job:
            raise ctypes.WinError(ctypes.get_last_error())
        pi = _Process()
        try:
            limits = _ExtendedLimits()
            limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
            self._ok(self.k.SetInformationJobObject(self.job, 9, ctypes.byref(limits), ctypes.sizeof(limits)))
            with open(os.devnull, "rb") as null:
                out_handle, in_handle = msvcrt.get_osfhandle(log.fileno()), msvcrt.get_osfhandle(null.fileno())
                os.set_handle_inheritable(out_handle, True)
                os.set_handle_inheritable(in_handle, True)
                si = _Startup()
                si.cb, si.dwFlags, si.wShowWindow = ctypes.sizeof(si), 0x101, 0
                si.hStdOutput = si.hStdError = out_handle
                si.hStdInput = in_handle
                try:
                    self._ok(self.k.CreateProcessW(str(command[0]), ctypes.create_unicode_buffer(subprocess.list2cmdline(command)),
                        None, None, True, 0x4 | 0x200 | 0x08000000, None, str(cwd), ctypes.byref(si), ctypes.byref(pi)))
                finally:
                    os.set_handle_inheritable(out_handle, False)
                    os.set_handle_inheritable(in_handle, False)
            self.process, self.pid = pi.hProcess, pi.dwProcessId
            self._ok(self.k.AssignProcessToJobObject(self.job, self.process))
            if self.k.ResumeThread(pi.hThread) == 0xFFFFFFFF:
                raise ctypes.WinError(ctypes.get_last_error())
        except BaseException:
            if pi.hProcess:
                self.k.TerminateProcess(pi.hProcess, 1)
            self.close()
            raise
        finally:
            if pi.hThread:
                self.k.CloseHandle(pi.hThread)

    @staticmethod
    def _ok(ok):
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())

    def active(self):
        info = _Accounting()
        self._ok(self.k.QueryInformationJobObject(self.job, 1, ctypes.byref(info), ctypes.sizeof(info), None))
        return info.ActiveProcesses

    def exit_code(self):
        code = wt.DWORD()
        self._ok(self.k.GetExitCodeProcess(self.process, ctypes.byref(code)))
        return None if code.value == 259 else code.value

    def terminate(self):
        self._ok(self.k.TerminateJobObject(self.job, 1))

    def wait_launcher(self, milliseconds=5000):
        if self.k.WaitForSingleObject(self.process, milliseconds) != 0:
            raise RuntimeError("Owned launcher did not signal exit")

    def close(self):
        if self.process:
            self.k.CloseHandle(self.process)
            self.process = None
        if self.job:
            self.k.CloseHandle(self.job)
            self.job = None


def supervise(root, directory, module, arguments, python):
    root, directory = Path(root).resolve(), Path(directory).resolve()
    if not directory.is_relative_to(root / "data/outputs"):
        raise ValueError("Monitor folder must be inside data/outputs")
    if not module.startswith("src.ball_tracking.") or "--run" not in arguments:
        raise ValueError("An explicitly executable ball module is required")
    directory.mkdir(parents=True, exist_ok=False)
    stop_file = directory / "STOP"
    bootstrap = ("import os,sys,runpy,threading,time,_thread\n"
        f"stop_file={str(stop_file)!r}\n"
        "def watch():\n"
        "    while not os.path.exists(stop_file): time.sleep(.25)\n"
        "    _thread.interrupt_main()\n"
        "threading.Thread(target=watch,daemon=True).start()\n"
        f"sys.argv={[module, *arguments]!r}\n"
        f"runpy.run_module({module!r},run_name='__main__')\n")
    command = [str(Path(python).resolve()), "-B", "-u", "-c", bootstrap]
    write_once(directory / "policy.json", {"created_at_utc": stamp(), "module": module,
        "arguments": arguments, "command": command, "gpu_uuid": GPU, "sample_seconds": 2,
        "telemetry_timeout_seconds": 5, "temperature_stop_C": 80, "grace_seconds": 10,
        "job_kill_on_supervisor_exit": True, "assign_job_before_resume": True,
        "supervisor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "authorization": "Thank you for this assessment chat. I like this, and I am cool to move forward with it",
        "gpu_monitoring_authorization": "Ok I lift the pause. Please monitor the GPU as we go, and lets move forward",
        "automatic_retry": False, "protected_evaluation_authorized": False})
    job, reason, code, forced = None, None, None, False
    began = time.monotonic()
    readings = []
    def event(row):
        with (directory / "telemetry.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    try:
        first = sample()
        event(first)
        readings.append(first)
        if stop_reason(first["values"]):
            raise RuntimeError("Prelaunch telemetry stop condition")
        with (directory / "console.log").open("xb") as log:
            job = OwnedJob(command, root, log)
            write_once(directory / "owned_process.json", {"pid": job.pid, "supervisor_pid": os.getpid(),
                "started_at_utc": stamp(), "job_owns_descendants": True})
            print(json.dumps({"status": "started_with_telemetry", "pid": job.pid, "monitor": str(directory)}), flush=True)
            last_print = 0
            while job.active():
                row = sample()
                event(row)
                readings.append(row)
                reason = stop_reason(row["values"])
                if stop_file.exists():
                    reason = "operator_stop_file"
                if reason:
                    break
                elapsed = time.monotonic() - began
                if elapsed - last_print >= 15:
                    print(json.dumps({"elapsed_seconds": round(elapsed, 1), "owned_processes": job.active(), **row["values"]}), flush=True)
                    last_print = elapsed
                time.sleep(2)
            if not job.active():
                job.wait_launcher()
            code = job.exit_code()
    except BaseException as error:
        reason = type(error).__name__ + ": " + str(error)
        event({"recorded_at_utc": stamp(), "supervisor_error": reason})
    finally:
        cleanup_error = None
        if job:
            remaining = None
            try:
                if job.active():
                    stop_file.touch(exist_ok=True)
                    deadline = time.monotonic() + 10
                    while job.active() and time.monotonic() < deadline:
                        time.sleep(.25)
                    if job.active():
                        job.terminate()
                        forced = True
                        deadline = time.monotonic() + 5
                        while job.active() and time.monotonic() < deadline:
                            time.sleep(.1)
                if not job.active():
                    job.wait_launcher()
                code = job.exit_code()
                remaining = job.active()
            except BaseException as error:
                cleanup_error = type(error).__name__ + ": " + str(error)
                reason = reason or "Owned-job cleanup: " + cleanup_error
                event({"recorded_at_utc": stamp(), "cleanup_error": cleanup_error})
            finally:
                job.close()
        else:
            remaining = 0
        values = [r["values"] for r in readings]
        result = {"finished_at_utc": stamp(), "elapsed_seconds": time.monotonic() - began,
            "returncode": code, "stop_reason": reason, "force_stopped_owned_job": forced,
            "job_cleanup_error": cleanup_error,
            "remaining_owned_processes_before_close": remaining, "samples": len(values),
            "maximum_temperature_C": max((float(v["temperature.gpu"]) for v in values), default=None),
            "maximum_power_W": max((float(v["power.draw"]) for v in values), default=None),
            "maximum_memory_MiB": max((float(v["memory.used"]) for v in values), default=None),
            "automatic_retry": False}
        write_once(directory / "finished.json", result)
        print(json.dumps(result), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--monitor", required=True)
    parser.add_argument("--module", required=True)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    arguments = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
    root = Path(__file__).resolve().parents[2]
    result = supervise(root, root / args.monitor, args.module, arguments, args.python)
    raise SystemExit(0 if result["returncode"] == 0 and result["stop_reason"] is None else 1)


if __name__ == "__main__":
    main()
