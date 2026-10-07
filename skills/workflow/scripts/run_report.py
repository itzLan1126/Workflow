"""Run a trusted project's command and read its newly created JSON report."""

import json
import math
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys


def read_json(path):
    def invalid_constant(value):
        raise ValueError(f"Non-finite JSON number: {value}")

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            invalid_constant(value)
        return number

    return json.loads(Path(path).read_text(encoding="utf-8"),
                      parse_constant=invalid_constant, parse_float=finite_float)


def run_report(config_path, accepted_exit_codes=(0,)):
    config = read_json(config_path)
    if not isinstance(config, dict):
        raise ValueError("Configuration must be an object")
    command = config.get("command")
    timeout = config.get("timeoutMs", 3600000)
    if (not isinstance(command, list) or not command
            or any(not isinstance(arg, str) or not arg for arg in command)
            or not isinstance(config.get("cwd"), str) or not config["cwd"]
            or not isinstance(config.get("report"), str) or not config["report"]
            or type(timeout) is not int or not 0 < timeout <= 2147483647):
        raise ValueError("Require cwd, report, nonempty command argv and positive timeoutMs (max 2147483647)")
    cwd = (Path(config_path).resolve().parent / config["cwd"]).resolve()
    if not cwd.is_dir():
        raise ValueError("cwd must be a directory")
    report_path = cwd / config["report"]
    try:
        report_path.lstat()
    except FileNotFoundError:
        pass
    else:
        raise ValueError("Report already exists; select a fresh report path to avoid stale results")
    # The caller supplies an isolated copy; this runner does not sandbox commands.
    with subprocess.Popen(command, cwd=cwd, shell=False, stdin=subprocess.DEVNULL,
                          stdout=sys.stderr, stderr=sys.stderr,
                          start_new_session=os.name == "posix") as child:
        try:
            exit_code = child.wait(timeout=timeout / 1000)
        except BaseException as error:
            try:
                if os.name == "posix":
                    os.killpg(child.pid, signal.SIGKILL)
                else:
                    child.kill()
            except ProcessLookupError:
                pass
            child.wait()
            if isinstance(error, subprocess.TimeoutExpired):
                raise ValueError("Tool exceeded timeoutMs") from error
            raise
    if exit_code < 0 or exit_code not in accepted_exit_codes:
        raise ValueError(f"Tool failed: exit {exit_code}")
    if not stat.S_ISREG(report_path.lstat().st_mode):
        raise ValueError("Report must be a regular file")
    return {"config": config, "report": read_json(report_path), "exitCode": exit_code}
