#!/usr/bin/env python3
"""Execute a mutation engine and classify its fresh report conservatively."""

import json
import sys

from run_report import read_json, run_report


STATUSES = ("killed", "survived", "noCoverage", "timeout", "unviable", "ignored", "error")
MAPS = {
    "stryker": {"Killed": "killed", "Survived": "survived", "NoCoverage": "noCoverage",
                "Timeout": "timeout", "CompileError": "unviable", "Ignored": "ignored",
                "RuntimeError": "error", "Pending": "error"},
    "cargo-mutants": {"CaughtMutant": "killed", "MissedMutant": "survived",
                      "Timeout": "timeout", "Unviable": "unviable"},
    "muter": {"failed": "killed", "passed": "survived", "noCoverage": "noCoverage",
              "timeout": "timeout", "buildError": "unviable", "runtimeError": "error"},
}
# Stryker exit 1 also means operational failure; a partial report cannot disambiguate it.
EXIT_CODES = {"stryker": (0,), "cargo-mutants": (0, 2, 3), "muter": (0,), "normalized": (0,)}


def object_value(value):
    if not isinstance(value, dict):
        raise ValueError("Expected an object in mutation report")
    return value


def array(value):
    if not isinstance(value, list):
        raise ValueError("Expected an array in mutation report")
    return value


def has_test(outcome):
    return any(object_value(phase).get("phase") == "Test"
               for phase in array(outcome.get("phase_results")))


def summarize(report, format):
    object_value(report)
    if format == "stryker":
        results = [object_value(m).get("status")
                   for file in object_value(report.get("files")).values()
                   for m in array(object_value(file).get("mutants"))]
    elif format == "cargo-mutants":
        outcomes = [object_value(o) for o in array(report.get("outcomes"))]
        baselines = [o for o in outcomes if o.get("scenario") == "Baseline"]
        if not baselines or any(o.get("summary") != "Success" or not has_test(o) for o in baselines):
            raise ValueError("cargo-mutants requires a successful baseline test (do not use --check or --baseline skip)")
        results = []
        for outcome in outcomes:
            if outcome.get("scenario") == "Baseline":
                continue
            object_value(object_value(outcome.get("scenario")).get("Mutant"))
            summary = outcome.get("summary")
            if summary in ("CaughtMutant", "MissedMutant") and not has_test(outcome):
                raise ValueError("Missing mutation test phase")
            results.append(summary)
        if type(report.get("total_mutants")) is not int or report["total_mutants"] != len(results):
            raise ValueError("Inconsistent cargo-mutants count")
    elif format == "muter":
        results = [object_value(m).get("testSuiteOutcome")
                   for file in array(report.get("fileReports"))
                   for m in array(object_value(file).get("appliedOperators"))]
    elif format == "normalized":
        if report.get("baselinePassed") is not True:
            raise ValueError("Normalized report must confirm baselinePassed: true")
        results = [object_value(m).get("status") for m in array(report.get("mutants"))]
    else:
        raise ValueError(f"Unsupported mutation format: {format}")
    if not results:
        raise ValueError("No mutations reported")
    counts = dict.fromkeys(STATUSES, 0)
    for result in results:
        if not isinstance(result, str):
            raise ValueError(f"Invalid mutation status: {result}")
        status = result if format == "normalized" else MAPS[format].get(result)
        if status not in STATUSES:
            raise ValueError(f"Unknown mutation status: {result}")
        counts[status] += 1
    assessed = sum(counts[status] for status in ("killed", "survived", "noCoverage", "timeout"))
    code = (2 if counts["error"] or not assessed else
            1 if counts["survived"] + counts["noCoverage"] + counts["timeout"] else 0)
    return {"format": format, "counts": counts, "assessed": assessed, "exitCode": code}


def run_mutation(config_path):
    format = object_value(read_json(config_path)).get("format")
    if not isinstance(format, str) or format not in EXIT_CODES:
        raise ValueError(f"Unsupported mutation format: {format}")
    run = run_report(config_path, EXIT_CODES[format])
    result = summarize(run["report"], format)
    if run["exitCode"] != 0 and result["exitCode"] == 0:
        raise ValueError(f"Tool exited {run['exitCode']} without reported findings")
    return {**result, "toolExitCode": run["exitCode"]}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) != 1:
            raise ValueError("Usage: python mutation.py CONFIG.json")
        result = run_mutation(args[0])
        print(json.dumps(result, indent=2, allow_nan=False))
        return result["exitCode"]
    except (OSError, ValueError) as error:
        print(f"mutation: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
