"""Prove a diagnostic worker belongs to the frozen supervisor's Windows job.

The venv executable can be a redirector; owned_process.pid is the assigned
launcher, not necessarily the Python worker. Query the supervisor's actual
outer job and the live parent chain instead of requiring equal PIDs.
"""
import ctypes
from ctypes import wintypes as wt
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sys

SUPERVISOR_SHA256 = 'dbc03099c088f6c5b96aa6d1691f5dd11d7abf7c600c97e563344a7541256cd0'


def check(value, message):
    if not value:
        raise ValueError(message)


def binding(root, path):
    raw = path.read_bytes()
    return {'path':path.relative_to(root).as_posix(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}


class Entry(ctypes.Structure):
    _fields_ = [('dwSize',wt.DWORD),('cntUsage',wt.DWORD),('th32ProcessID',wt.DWORD),
        ('th32DefaultHeapID',ctypes.c_size_t),('th32ModuleID',wt.DWORD),('cntThreads',wt.DWORD),
        ('th32ParentProcessID',wt.DWORD),('pcPriClassBase',wt.LONG),('dwFlags',wt.DWORD),('szExeFile',wt.WCHAR*260)]


class Limits(ctypes.Structure):
    _fields_ = [('PerProcessUserTimeLimit',ctypes.c_longlong),('PerJobUserTimeLimit',ctypes.c_longlong),
        ('LimitFlags',wt.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),('MaximumWorkingSetSize',ctypes.c_size_t),
        ('ActiveProcessLimit',wt.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',wt.DWORD),('SchedulingClass',wt.DWORD)]


class Io(ctypes.Structure):
    _fields_ = [(k,ctypes.c_ulonglong) for k in ('ReadOperationCount','WriteOperationCount',
        'OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]


class ExtendedLimits(ctypes.Structure):
    _fields_ = [('BasicLimitInformation',Limits),('IoInfo',Io),('ProcessMemoryLimit',ctypes.c_size_t),
        ('JobMemoryLimit',ctypes.c_size_t),('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]


def kernel():
    check(os.name == 'nt','Owned diagnostic requires Windows')
    k = ctypes.WinDLL('kernel32',use_last_error=True)
    declarations = {
        'CreateToolhelp32Snapshot':([wt.DWORD,wt.DWORD],wt.HANDLE),
        'Process32FirstW':([wt.HANDLE,ctypes.POINTER(Entry)],wt.BOOL),
        'Process32NextW':([wt.HANDLE,ctypes.POINTER(Entry)],wt.BOOL),
        'OpenProcess':([wt.DWORD,wt.BOOL,wt.DWORD],wt.HANDLE),
        'GetProcessTimes':([wt.HANDLE,*([ctypes.POINTER(wt.FILETIME)]*4)],wt.BOOL),
        'WaitForSingleObject':([wt.HANDLE,wt.DWORD],wt.DWORD),
        'QueryInformationJobObject':([wt.HANDLE,ctypes.c_int,ctypes.c_void_p,wt.DWORD,ctypes.c_void_p],wt.BOOL),
        'CreateJobObjectW':([ctypes.c_void_p,wt.LPCWSTR],wt.HANDLE),
        'GetCurrentProcess':([],wt.HANDLE),
        'DuplicateHandle':([wt.HANDLE,wt.HANDLE,wt.HANDLE,ctypes.POINTER(wt.HANDLE),wt.DWORD,wt.BOOL,wt.DWORD],wt.BOOL),
        'IsProcessInJob':([wt.HANDLE,wt.HANDLE,ctypes.POINTER(wt.BOOL)],wt.BOOL),
        'CloseHandle':([wt.HANDLE],wt.BOOL)}
    for name,(args,result) in declarations.items():
        fn = getattr(k,name)
        fn.argtypes,fn.restype = args,result
    return k


def ok(value):
    if not value:
        raise ctypes.WinError(ctypes.get_last_error())


def job_information(k, handle):
    extended = ExtendedLimits()
    ok(k.QueryInformationJobObject(handle,9,ctypes.byref(extended),ctypes.sizeof(extended),None))
    limits = extended.BasicLimitInformation
    members = None
    for capacity in (16,64,256,1024):
        class Pids(ctypes.Structure):
            _fields_ = [('assigned',wt.DWORD),('listed',wt.DWORD),('ids',ctypes.c_size_t*capacity)]
        value = Pids()
        success = k.QueryInformationJobObject(handle,3,ctypes.byref(value),ctypes.sizeof(value),None)
        if success and value.listed == value.assigned and value.listed <= capacity:
            members = {int(p) for p in value.ids[:value.listed]}
            break
        check(ctypes.get_last_error() == 234 or value.assigned > capacity,'Cannot query complete immediate job membership')
    check(members is not None,'Cannot enumerate complete job membership')
    return int(limits.LimitFlags),members


class HandleEntry(ctypes.Structure):
    _fields_ = [('Object',ctypes.c_void_p),('UniqueProcessId',ctypes.c_size_t),('HandleValue',ctypes.c_size_t),
        ('GrantedAccess',wt.ULONG),('CreatorBackTraceIndex',wt.USHORT),('ObjectTypeIndex',wt.USHORT),
        ('HandleAttributes',wt.ULONG),('Reserved',wt.ULONG)]


def supervisor_job(k, worker, launcher, supervisor, created):
    """Query-only duplicate of the actual outer job; venv may add an inner job.

    Native handle enumeration is read-only. A temporary unassigned job identifies
    this boot's Job object type; only supervisor-owned Job handles are duplicated,
    with JOB_OBJECT_QUERY access. No assign/set/terminate operation is used.
    """
    process = k.OpenProcess(0x40|0x1000|0x100000,False,supervisor)
    ok(process)
    temporary = None
    matches = []
    try:
        check(k.WaitForSingleObject(process,0) == 258,'Supervisor must remain live')
        times = [wt.FILETIME() for _ in range(4)]
        ok(k.GetProcessTimes(process,*[ctypes.byref(v) for v in times]))
        process_created = ((times[0].dwHighDateTime<<32)|times[0].dwLowDateTime)/10000000-11644473600
        check(process_created <= created,'Supervisor PID was reused after policy creation')
        temporary = k.CreateJobObjectW(None,None); ok(temporary)
        nt = ctypes.WinDLL('ntdll').NtQuerySystemInformation
        nt.argtypes = [wt.ULONG,ctypes.c_void_p,wt.ULONG,ctypes.POINTER(wt.ULONG)]
        nt.restype = wt.LONG
        needed = wt.ULONG(); size = 1024*1024
        while size <= 64*1024*1024:
            buffer = ctypes.create_string_buffer(size)
            status = nt(64,buffer,size,ctypes.byref(needed)) & 0xffffffff
            if status == 0: break
            check(status in {0xc0000004,0xc0000023},f'Cannot enumerate native handles: {status:#x}')
            size = max(size*2,int(needed.value)+65536)
        check(status == 0,'Native handle table exceeds bounded query size')
        count = ctypes.c_size_t.from_buffer(buffer).value
        offset = 2*ctypes.sizeof(ctypes.c_size_t)
        check(offset+count*ctypes.sizeof(HandleEntry) <= size,'Native handle table schema differs')
        entries = (HandleEntry*count).from_buffer(buffer,offset)
        types = {e.ObjectTypeIndex for e in entries if e.UniqueProcessId == worker and e.HandleValue == temporary}
        check(len(types) == 1,'Cannot identify actual Job handle type')
        job_type = next(iter(types))
        for entry in entries:
            if entry.UniqueProcessId != supervisor or entry.ObjectTypeIndex != job_type: continue
            duplicate = wt.HANDLE()
            ok(k.DuplicateHandle(process,entry.HandleValue,k.GetCurrentProcess(),ctypes.byref(duplicate),0x4,False,0))
            try:
                flags,pids = job_information(k,duplicate)
                if worker not in pids or launcher not in pids or supervisor in pids: continue
                check(flags & 0x2000 and not flags & (0x800|0x1000),'Actual supervisor-owned job limits differ')
                launcher_handle = k.OpenProcess(0x1000,False,launcher); ok(launcher_handle)
                try:
                    for member in (k.GetCurrentProcess(),launcher_handle):
                        contained = wt.BOOL()
                        ok(k.IsProcessInJob(member,duplicate,ctypes.byref(contained)))
                        check(bool(contained.value),'Exact supervisor job membership failed')
                finally:
                    k.CloseHandle(launcher_handle)
                matches.append({'members':pids,'flags':flags,'supervisor_handle_value':int(entry.HandleValue),
                    'duplicate_access':'JOB_OBJECT_QUERY only','native_handle_entries_examined':int(count)})
            finally:
                k.CloseHandle(duplicate)
        check(len(matches) == 1,'Require one unambiguous supervisor-owned outer job')
        check(k.WaitForSingleObject(process,0) == 258,'Supervisor exited during job verification')
        return matches[0]
    finally:
        if temporary: k.CloseHandle(temporary)
        k.CloseHandle(process)


def live_membership(worker, launcher, supervisor, created, started):
    k = kernel()
    evidence = supervisor_job(k,worker,launcher,supervisor,created)
    members = evidence['members']
    snapshot = k.CreateToolhelp32Snapshot(2,0)
    check(snapshot != ctypes.c_void_p(-1).value,'Cannot snapshot process ancestry')
    parents = {}
    try:
        entry = Entry(); entry.dwSize = ctypes.sizeof(entry)
        ok(k.Process32FirstW(snapshot,ctypes.byref(entry)))
        while True:
            parents[int(entry.th32ProcessID)] = int(entry.th32ParentProcessID)
            if not k.Process32NextW(snapshot,ctypes.byref(entry)):
                check(ctypes.get_last_error() == 18,'Process ancestry enumeration failed')
                break
    finally:
        k.CloseHandle(snapshot)
    chain = [worker]
    while chain[-1] != launcher and len(chain) <= 32:
        parent = parents.get(chain[-1])
        check(parent and parent in members and parent not in chain,'Worker is not a live descendant of recorded launcher')
        chain.append(parent)
    check(chain[-1] == launcher and parents.get(launcher) == supervisor,'Launcher must be direct child of recorded supervisor')
    handles, times = [], {}
    try:
        for pid in [*chain,supervisor]:
            handle = k.OpenProcess(0x1000|0x100000,False,pid)
            ok(handle); handles.append(handle)
            check(k.WaitForSingleObject(handle,0) == 258,'Required owned process is no longer live')
            values = [wt.FILETIME() for _ in range(4)]
            ok(k.GetProcessTimes(handle,*[ctypes.byref(v) for v in values]))
            times[pid] = ((values[0].dwHighDateTime<<32)|values[0].dwLowDateTime)/10000000-11644473600
        check(all(times[parent] <= times[child] for child,parent in zip(chain,chain[1:])), 'Reused PID in ancestry')
        check(times[supervisor] <= created and created-2 <= times[launcher] <= started+2
              and times[worker] >= times[launcher], 'Process creation times disagree with supervisor launch receipts')
        check(all(k.WaitForSingleObject(h,0) == 258 for h in handles),'Owned process exited during verification')
    finally:
        for handle in handles: k.CloseHandle(handle)
    return {'worker_pid':worker,'launcher_pid':launcher,'supervisor_pid':supervisor,
        'worker_to_launcher_chain':chain,'supervisor_job_process_ids':sorted(members),
        'supervisor_job_limit_flags':evidence['flags'],'process_creation_unix_seconds':times,
        'supervisor_job_handle_value':evidence['supervisor_handle_value'],'duplicate_access':evidence['duplicate_access'],
        'native_handle_entries_examined':evidence['native_handle_entries_examined'],
        'exact_supervisor_job_verified':True,'live_ancestry_verified':True}


def verify_owned_worker(root, monitor, module, arguments):
    root,monitor = Path(root).resolve(),Path(monitor).resolve()
    check(monitor.is_relative_to(root/'data/outputs'),'Supervisor directory escaped outputs')
    check(not (monitor/'finished.json').exists() and not (monitor/'STOP').exists(),'Supervisor is finished or stopping')
    policy_path,owned_path = monitor/'policy.json',monitor/'owned_process.json'
    policy_bytes,owned_bytes = policy_path.read_bytes(),owned_path.read_bytes()
    policy,owned = json.loads(policy_bytes),json.loads(owned_bytes)
    check(policy['module'] == module and policy['arguments'] == list(arguments) and '--run' in arguments,
          'Exact supervised module and arguments required')
    source = root/'src/ball_tracking/gpu_supervision.py'
    check(hashlib.sha256(source.read_bytes()).hexdigest() == policy['supervisor_sha256'] == SUPERVISOR_SHA256,
          'Frozen supervisor source differs')
    check(policy['assign_job_before_resume'] is policy['job_kill_on_supervisor_exit'] is owned['job_owns_descendants'] is True
          and policy['automatic_retry'] is policy['protected_evaluation_authorized'] is False,'Owned job policy differs')
    stop_file = monitor/'STOP'
    bootstrap = ('import os,sys,runpy,threading,time,_thread\n'
        f'stop_file={str(stop_file)!r}\n'
        'def watch():\n    while not os.path.exists(stop_file): time.sleep(.25)\n    _thread.interrupt_main()\n'
        'threading.Thread(target=watch,daemon=True).start()\n'
        f'sys.argv={[module,*arguments]!r}\n'
        f"runpy.run_module({module!r},run_name='__main__')\n")
    command = policy['command']
    check(len(command) == 5 and Path(command[0]).resolve() == Path(sys.executable).resolve()
          and command[1:] == ['-B','-u','-c',bootstrap],'Actual frozen bootstrap/module/arguments/STOP path differ')
    result = live_membership(os.getpid(),owned['pid'],owned['supervisor_pid'],
        datetime.fromisoformat(policy['created_at_utc']).timestamp(),datetime.fromisoformat(owned['started_at_utc']).timestamp())
    check(policy_path.read_bytes() == policy_bytes and owned_path.read_bytes() == owned_bytes
          and not (monitor/'finished.json').exists() and not (monitor/'STOP').exists(),'Supervisor evidence changed during verification')
    return {'status':'passed_active_owned_worker','module':module,**result,
        'policy':binding(root,policy_path),'owned_process':binding(root,owned_path),'guard':binding(root,Path(__file__).resolve())}
