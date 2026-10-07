"""Run a trusted project's command and read its newly created JSON report."""

import json
import math
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys


def invalid_constant(value):
    raise ValueError(f"Non-finite JSON number: {value}")


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        invalid_constant(value)
    return number


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"),
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
        if os.name == "posix":
            os.killpg(child.pid, signal.SIGKILL)
        else:
            child.kill()
    except ProcessLookupError:
        pass
    child.wait()


def run_command(command, cwd, timeout):
    # The caller supplies an isolated copy; this runner does not sandbox commands.
    with subprocess.Popen(command, cwd=cwd, shell=False, stdin=subprocess.DEVNULL,
                          stdout=sys.stderr, stderr=sys.stderr,
                          start_new_session=os.name == "posix") as child:
        try:
            return child.wait(timeout=timeout / 1000)
        except BaseException as error:
            stop(child)
            if isinstance(error, subprocess.TimeoutExpired):
                raise ValueError("Tool exceeded timeoutMs") from error
            raise


def run_report(config_path, accepted_exit_codes=(0,)):
    config = read_config(config_path)
    cwd, report_path = fresh_report_path(config_path, config)
    exit_code = run_command(config["command"], cwd, config.get("timeoutMs", DEFAULT_TIMEOUT_MS))
    if exit_code < 0 or exit_code not in accepted_exit_codes:
        raise ValueError(f"Tool failed: exit {exit_code}")
    if not stat.S_ISREG(report_path.lstat().st_mode):
        raise ValueError("Report must be a regular file")
    return {"config": config, "report": read_json(report_path), "exitCode": exit_code}
