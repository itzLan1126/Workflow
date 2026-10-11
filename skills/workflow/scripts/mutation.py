#!/usr/bin/env python3
"""Execute a mutation engine and classify its fresh report conservatively."""

import json
import sys
from pathlib import Path
import shutil
from shared_languages import LANGUAGES, language, arguments, evidence_directory

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


def language_result(name, args):
    project, sources, timeout, tool = arguments(args)
    if sources:
        raise ValueError('Mutation check accepts one project path')
    spec = language(name).MUTATION
    evidence = evidence_directory()
    report = Path(spec.report(project, evidence))
    config = {'cwd': str(project), 'report': str(report), 'format': spec.format,
              'command': spec.command(project, evidence, tool), 'timeoutMs': timeout}
    path = evidence / 'config.json'
    path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    result = run_mutation(path)
    if not report.resolve().is_relative_to(evidence.resolve()):
        shutil.copy2(report, evidence / report.name)
        result['reportPath'] = str(evidence / report.name)
    return result


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        as_json = "--json" in args
        args = list(args)
        if as_json:
            args.remove("--json")
        if args and args[0] in LANGUAGES:
            result = language_result(args[0], args[1:])
        elif len(args) == 1:
            result = run_mutation(args[0])
        else:
            raise ValueError("Usage: python mutation.py [--json] CONFIG.json")
        print(json.dumps(result, indent=2, allow_nan=False) if as_json else render_report(result))
        return result["exitCode"]
    except (OSError, ValueError) as error:
        print(f"mutation: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
