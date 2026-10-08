"""Keep Windows command descendants in a kill-on-close job, independent of root PID lifetime."""

import ctypes
from ctypes import wintypes
from pathlib import Path
import subprocess
import sys


class BasicLimits(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD)]


class IoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint64) for name in
                ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                 "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class ExtendedLimits(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", BasicLimits), ("IoInfo", IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]


def kernel32():
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    signatures = {
        "CreateJobObjectW": ([ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
        "SetInformationJobObject": ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
        "AssignProcessToJobObject": ([wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
        "TerminateJobObject": ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
        "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
    }
    for name, (args, result) in signatures.items():
        function = getattr(api, name)
        function.argtypes, function.restype = args, result
    return api


def checked(result):
    if not result:
        raise ctypes.WinError(ctypes.get_last_error())
    return result


class WindowsJob:
    def __init__(self):
        self.api = kernel32()
        self.handle = checked(self.api.CreateJobObjectW(None, None))
        limits = ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        try:
            checked(self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)))
        except BaseException:
            self.api.CloseHandle(self.handle)
            raise

    def __enter__(self):
        return self

    def assign(self, child):
        checked(self.api.AssignProcessToJobObject(self.handle, int(child._handle)))

    def terminate(self):
        checked(self.api.TerminateJobObject(self.handle, 1))

    def __exit__(self, kind, error, traceback):
        try:
            checked(self.api.CloseHandle(self.handle))
        except OSError as cleanup_error:
            if error is None:
                raise
            print(f"Windows job cleanup failed: {cleanup_error}", file=sys.stderr)


def stop(child, job):
    try:
        job.terminate()
    except OSError:
        child.kill()  # Reap the bootstrap even when job termination failed; never claim success.
        raise
    finally:
        child.wait()


def start_and_wait(child, job, timeout):
    try:
        job.assign(child)
        # The bootstrap cannot launch the tool until assignment has succeeded.
        child.stdin.write(b"1")
        child.stdin.close()
        return child.wait(timeout=timeout / 1000)
    except BaseException as error:
        try:
            stop(child, job)
        except OSError as cleanup_error:
            raise error from cleanup_error
        raise


def run(command, cwd, timeout):
    bootstrap_command = [sys.executable, str(Path(__file__).resolve()), *command]
    try:
        with WindowsJob() as job:
            with subprocess.Popen(bootstrap_command, cwd=cwd, shell=False, stdin=subprocess.PIPE,
                                  stdout=sys.stderr, stderr=sys.stderr) as child:
                return start_and_wait(child, job, timeout)
    except subprocess.TimeoutExpired as error:
        raise ValueError("Tool exceeded timeoutMs") from error


def bootstrap(command):
    if sys.stdin.buffer.read(1) != b"1":
        return 2
    return subprocess.call(command, stdin=subprocess.DEVNULL)


if __name__ == "__main__":
    sys.exit(bootstrap(sys.argv[1:]))
