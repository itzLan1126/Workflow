#!/usr/bin/env python3
"""Execute a mutation engine and classify its fresh report conservatively."""

import json
import sys

from shared_runner import read_json, is_valid_config, run_report
from shared_mutation import adapter, assess, render_report, summarize, object_value
MAPS = {name: adapter(name).STATUSES for name in ("stryker", "cargo-mutants", "muter")}


def execute_config(path, config, codes):
    if not is_valid_config(config):
        raise ValueError("Require cwd, report, nonempty command argv and positive timeoutMs (max 2147483647)")
    return run_report(path, codes, config=config)


def run_mutation(config_path):
    config = object_value(read_json(config_path))
    format = config.get("format")
    reader = adapter(format)
    run = execute_config(config_path, config, reader.ACCEPTED_EXIT_CODES)
    result = assess(run["report"], format, run["reportPath"])
    if run["exitCode"] != 0 and result["exitCode"] == 0:
        raise ValueError(f"Tool exited {run['exitCode']} without reported findings")
    return {**result, "toolExitCode": run["exitCode"], "reportPath": str(run["reportPath"])}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        as_json = "--json" in args
        args = list(args)
        if as_json:
            args.remove("--json")
        if len(args) != 1:
            raise ValueError("Usage: python mutation.py [--json] CONFIG.json")
        result = run_mutation(args[0])
        print(json.dumps(result, indent=2, allow_nan=False) if as_json else render_report(result))
        return result["exitCode"]
    except (OSError, ValueError) as error:
        print(f"mutation: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
