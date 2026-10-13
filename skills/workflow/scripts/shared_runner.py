"""Run a trusted project's command and read its newly created JSON report."""

import io
import json
import math
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys

import ctypes
from ctypes import wintypes


def invalid_constant(value):
    raise ValueError(f"Non-finite JSON number: {value}")


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        invalid_constant(value)
    return number


def read_utf8(path):
    return io.IncrementalNewlineDecoder(None, True).decode(Path(path).read_bytes().decode(), True)


def read_json(path):
    return json.loads(read_utf8(path),
                      parse_constant=invalid_constant, parse_float=finite_float)


DEFAULT_TIMEOUT_MS = 3600000


def is_text(value):
    return isinstance(value, str) and value != ""


def is_command(command):
    return isinstance(command, list) and command != [] and all(map(is_text, command))


def is_timeout(timeout):
    return type(timeout) is int and 0 < timeout <= 2147483647


def is_valid_config(config):
    return (is_command(config.get("command")) and is_text(config.get("cwd"))
            and is_text(config.get("report")) and is_timeout(config.get("timeoutMs", DEFAULT_TIMEOUT_MS)))


def read_config(config_path):
    config = read_json(config_path)
    if not isinstance(config, dict):
        raise ValueError("Configuration must be an object")
    if not is_valid_config(config):
        raise ValueError("Require cwd, report, nonempty command argv and positive timeoutMs (max 2147483647)")
    return config


def fresh_report_path(config_path, config):
    cwd = (Path(config_path).resolve().parent / config["cwd"]).resolve()
    if not cwd.is_dir():
        raise ValueError("cwd must be a directory")
    report_path = cwd / config["report"]
    try:
        report_path.lstat()
    except FileNotFoundError:
        return cwd, report_path
    raise ValueError("Report already exists; select a fresh report path to avoid stale results")


def stop(child):
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    child.wait()


def run_command(command, cwd, timeout, *, env=None):
    # The caller supplies an isolated copy; this runner does not sandbox commands.
    if os.name == "nt":
        return run_windows(command, cwd, timeout, env=env)
    with subprocess.Popen(command, cwd=cwd, stdin=subprocess.DEVNULL,
                          stdout=sys.stderr, stderr=sys.stderr,
                          start_new_session=True, env=env) as child:
        try:
            exit_code = child.wait(timeout=timeout / 1000)
        except BaseException as error:
            try:
                stop(child)
            except OSError as cleanup_error:
                error.__cause__ = cleanup_error
            if isinstance(error, subprocess.TimeoutExpired):
                raise ValueError("Tool exceeded timeoutMs") from error
            raise
        stop(child)
        return exit_code


def run_report(config_path, accepted_exit_codes=(0,), *, config=None):
    if config is None:
        config = read_config(config_path)
    cwd, report_path = fresh_report_path(config_path, config)
    exit_code = run_command(config["command"], cwd, config.get("timeoutMs", DEFAULT_TIMEOUT_MS),
                            env={**os.environ, "WORKFLOW_REPORT_FILE": str(report_path.resolve())})
    if exit_code < 0 or exit_code not in accepted_exit_codes:
        raise ValueError(f"Tool failed: exit {exit_code}")
    if not stat.S_ISREG(report_path.lstat().st_mode):
        raise ValueError("Report must be a regular file")
    return {"config": config, "report": read_json(report_path), "reportPath": report_path.resolve(),
            "exitCode": exit_code}


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


def stop_windows(child, job):
    try:
        job.terminate()
    finally:
        # Assignment may have failed: the gated bootstrap is then outside the job.
        child.kill()
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
            stop_windows(child, job)
        except OSError as cleanup_error:
            raise error from cleanup_error
        raise


def run_windows(command, cwd, timeout, *, env=None):
    bootstrap_command = [sys.executable, str(Path(__file__).resolve()), *command]
    try:
        with WindowsJob() as job:
            with subprocess.Popen(bootstrap_command, cwd=cwd, stdin=subprocess.PIPE,
                                  stdout=sys.stderr, stderr=sys.stderr, env=env) as child:
                return start_and_wait(child, job, timeout)
    except subprocess.TimeoutExpired as error:
        raise ValueError("Tool exceeded timeoutMs") from error


def bootstrap(command):
    if sys.stdin.buffer.read(1) != b"1":
        return 2
    return subprocess.call(command, stdin=subprocess.DEVNULL)


if __name__ == "__main__":
    sys.exit(bootstrap(sys.argv[1:]))
