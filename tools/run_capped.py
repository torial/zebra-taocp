"""Run a command under a hard MEMORY cap and a time limit, for the whole process tree.

Why this exists: on 2026-10-12 a mutation-test run of this repository left one mutant (an
Algorithm T that never drains its queue) looping and appending for its full 900-second
timeout. Measured afterwards: 8.8 GB working set and 16.7 GB committed within 60 seconds. It
slowed the machine for other work, and nothing in the harness noticed -- the run was
eventually scored "killed (timeout)", which is a PASS for a mutation test, so the cost was
invisible in the result.

On Windows the cap is a Job Object with JOB_OBJECT_LIMIT_JOB_MEMORY: every process the
command starts (zebra, then zig, then the built program) belongs to the job, allocations past
the cap fail (the Zebra runtime then stops with an out-of-memory panic), and closing the job
kills whatever is left. Elsewhere it falls back to a time limit only and SAYS so.

THE CAP IS NOT TIGHT -- measured, not documented by Windows as far as I found: the job's peak
went past the nominal cap by about one allocation. A list that keeps growing reached 436 MB
under a 256 MB cap, 1471 MB under 512 MB, and the hanging mutant 1533 MB under 1024 MB --
consistent with a doubled buffer being granted while the old one is still live. Read the cap
as "stops a runaway within seconds at a few times the cap", not "never exceeds N". That was
the point: the run it was written for reached 16.7 GB committed and ran for 900 s.

    from run_capped import run_capped
    r = run_capped(["zebra", "taocp_test.zbr"], cwd, mem_mb=2048, timeout_s=300)
    r.status   # "exit" | "timeout" | "memory-cap"
    r.code, r.output, r.peak_mb

usage (CLI): python tools/run_capped.py [--mem-mb N] [--timeout S] -- command args...
"""
import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes


class Result:
    def __init__(self, status, code, output, peak_mb, capped_by_os):
        self.status = status            # "exit", "timeout" or "memory-cap"
        self.code = code
        self.output = output
        self.peak_mb = peak_mb          # the job's peak committed memory, MB (None off Windows)
        self.capped_by_os = capped_by_os

    def __repr__(self):
        return f'Result(status={self.status}, code={self.code}, peak_mb={self.peak_mb})'


if os.name == 'nt':
    k32 = ctypes.WinDLL('kernel32', use_last_error=True)

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in (
            'ReadOperationCount', 'WriteOperationCount', 'OtherOperationCount',
            'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]

    class BASIC_LIMIT(ctypes.Structure):
        _fields_ = [('PerProcessUserTimeLimit', ctypes.c_longlong),
                    ('PerJobUserTimeLimit', ctypes.c_longlong),
                    ('LimitFlags', wintypes.DWORD),
                    ('MinimumWorkingSetSize', ctypes.c_size_t),
                    ('MaximumWorkingSetSize', ctypes.c_size_t),
                    ('ActiveProcessLimit', wintypes.DWORD),
                    ('Affinity', ctypes.c_size_t),
                    ('PriorityClass', wintypes.DWORD),
                    ('SchedulingClass', wintypes.DWORD)]

    class EXTENDED_LIMIT(ctypes.Structure):
        _fields_ = [('BasicLimitInformation', BASIC_LIMIT),
                    ('IoInfo', IO_COUNTERS),
                    ('ProcessMemoryLimit', ctypes.c_size_t),
                    ('JobMemoryLimit', ctypes.c_size_t),
                    ('PeakProcessMemoryUsed', ctypes.c_size_t),
                    ('PeakJobMemoryUsed', ctypes.c_size_t)]

    JobObjectExtendedLimitInformation = 9
    JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    PROCESS_ALL_ACCESS = 0x1F0FFF

    k32.CreateJobObjectW.restype = wintypes.HANDLE
    k32.OpenProcess.restype = wintypes.HANDLE

    def _job(mem_mb):
        h = k32.CreateJobObjectW(None, None)
        if not h:
            raise OSError(ctypes.get_last_error(), 'CreateJobObject failed')
        info = EXTENDED_LIMIT()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_JOB_MEMORY | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        info.JobMemoryLimit = mem_mb * 1024 * 1024
        if not k32.SetInformationJobObject(h, JobObjectExtendedLimitInformation,
                                           ctypes.byref(info), ctypes.sizeof(info)):
            raise OSError(ctypes.get_last_error(), 'SetInformationJobObject failed')
        return h

    def _peak_mb(job):
        info = EXTENDED_LIMIT()
        if k32.QueryInformationJobObject(job, JobObjectExtendedLimitInformation,
                                         ctypes.byref(info), ctypes.sizeof(info), None):
            return info.PeakJobMemoryUsed // (1024 * 1024)
        return None


def run_capped(cmd, cwd, mem_mb=2048, timeout_s=300, env=None):
    """Run cmd; return a Result. On Windows the tree is stopped soon after it passes mem_mb
    (see the module note: the overshoot is about one allocation, measured up to ~3x)."""
    if os.name != 'nt':
        try:
            r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout_s, env=env)
            return Result('exit', r.returncode, r.stdout + r.stderr, None, False)
        except subprocess.TimeoutExpired as e:
            out = (e.stdout or '') + (e.stderr or '') if isinstance(e.stdout, str) else ''
            return Result('timeout', None, out, None, False)
    job = _job(mem_mb)
    # Start suspended would be tighter; a fresh process has allocated nothing worth capping in
    # the few microseconds before it joins the job, and its children are all started later.
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, env=env, creationflags=0)
    hproc = k32.OpenProcess(PROCESS_ALL_ACCESS, False, p.pid)
    if not hproc or not k32.AssignProcessToJobObject(job, hproc):
        p.kill()
        raise OSError(ctypes.get_last_error(), 'AssignProcessToJobObject failed -- refusing to run uncapped')
    k32.CloseHandle(hproc)
    try:
        out, _ = p.communicate(timeout=timeout_s)
        status = 'exit'
    except subprocess.TimeoutExpired:
        k32.TerminateJobObject(job, 1)
        out, _ = p.communicate()
        status = 'timeout'
    peak = _peak_mb(job)
    k32.CloseHandle(job)                    # KILL_ON_JOB_CLOSE: nothing outlives this
    # An allocation refused by the cap shows up as the program's own out-of-memory failure; the
    # job's peak at (or within a page of) the cap is what says the CAP did it, not the program.
    if status == 'exit' and p.returncode != 0 and peak is not None and peak >= mem_mb * 0.95:
        status = 'memory-cap'
    return Result(status, p.returncode, out or '', peak, True)


if __name__ == '__main__':
    args = sys.argv[1:]
    mem, tmo = 2048, 300
    while args and args[0] != '--':
        if args[0] == '--mem-mb':
            mem = int(args[1]); args = args[2:]
        elif args[0] == '--timeout':
            tmo = int(args[1]); args = args[2:]
        else:
            raise SystemExit(f'unknown option {args[0]}')
    if not args or args[0] != '--' or len(args) < 2:
        raise SystemExit('usage: run_capped.py [--mem-mb N] [--timeout S] -- command args...')
    r = run_capped(args[1:], os.getcwd(), mem, tmo)
    sys.stdout.write(r.output)
    print(f'[run_capped] status={r.status} code={r.code} peak={r.peak_mb} MB (cap {mem} MB, limit {tmo} s)')
    sys.exit(0 if r.status == 'exit' and r.code == 0 else 1)
