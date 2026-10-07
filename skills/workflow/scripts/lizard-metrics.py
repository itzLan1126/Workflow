#!/usr/bin/env python3
"""Join Lizard function complexity with fresh LCOV line and branch coverage, without guessing."""

import json
from pathlib import Path
import re
import sys


def parse_line(record):
    fields = record[3:].split(",")
    if (len(fields) not in (2, 3) or not re.fullmatch(r"[1-9][0-9]*", fields[0])
            or not re.fullmatch(r"[0-9]+", fields[1])):
        raise ValueError(f"Invalid LCOV line record: {record}")
    return int(fields[0]), int(fields[1])


def parse_branch(record):
    # BRDA:<line>,<block>,<branch>,<taken>; taken is "-" when the branch's line never ran.
    match = re.fullmatch(r"BRDA:([1-9][0-9]*),([^,]+),(.+),(-|[0-9]+)", record)
    if not match:
        raise ValueError(f"Invalid LCOV branch record: {record}")
    line, block, branch, taken = match.groups()
    return (int(line), block, branch), 0 if taken == "-" else int(taken)


def open_section(current, record):
    if current is not None or not record[3:]:
        raise ValueError("LCOV has nested or empty SF records")
    return Path(record[3:]).resolve(), {"lines": {}, "branches": {}}


def add_record(current, record):
    if current is None:
        raise ValueError(f"LCOV record outside SF: {record}")
    source, records = current
    kind, parse = ("lines", parse_line) if record.startswith("DA:") else ("branches", parse_branch)
    key, count = parse(record)
    if key in records[kind]:
        raise ValueError(f"Duplicate LCOV {kind} record in {source}: {record}")
    records[kind][key] = count


def close_section(files, current):
    if current is None:
        raise ValueError("LCOV end_of_record without SF")
    source, records = current
    merged = files.setdefault(source, {"lines": {}, "branches": {}})
    for kind, counts in records.items():
        for key, count in counts.items():
            merged[kind][key] = merged[kind].get(key, 0) + count


def read_record(files, current, record):
    """Apply one LCOV record; current is (source, records) inside an SF section, otherwise None."""
    if record.startswith("SF:"):
        return open_section(current, record)
    if record.startswith(("DA:", "BRDA:")):
        add_record(current, record)
    elif record == "end_of_record":
        close_section(files, current)
        return None
    return current


def read_lcov(path):
    files, current = {}, None
    for record in Path(path).read_text(encoding="utf-8").splitlines():
        current = read_record(files, current, record)
    if current is not None or not files:
        raise ValueError("Incomplete or empty LCOV report")
    return files


def summarize(counts):
    return {"covered": sum(count > 0 for count in counts), "total": len(counts)}


def analyze(source):
    import lizard
    from lizard_languages import get_reader_for

    if get_reader_for(str(source)) is None:
        raise ValueError(f"Unsupported source: {source}")
    code = source.read_text(encoding="utf-8")
    functions = sorted(lizard.analyze_file.analyze_source_code(
        str(source), code).function_list, key=lambda function: function.start_line)
    if not functions:
        raise ValueError(f"No functions found: {source}")
    return code, functions


def source_coverage(coverage, source, code):
    if source not in coverage:
        raise ValueError(f"Missing exact-path LCOV coverage: {source}")
    hits = coverage[source]
    recorded = [*hits["lines"], *(key[0] for key in hits["branches"])]
    if any(line > len(code.splitlines()) for line in recorded):
        raise ValueError(f"LCOV line outside source: {source}")
    return hits


def measure_function(source, function, hits):
    counts = [count for line, count in hits.items()
              if function.start_line <= line <= function.end_line]
    if not counts:
        raise ValueError(f"Missing line coverage: {source}:{function.name}")
    return {"file": str(source), "name": function.name, "line": function.start_line,
            "complexity": function.cyclomatic_complexity,
            "covered": sum(count > 0 for count in counts),
            "total": len(counts), "coverageKind": "line"}


def measure_functions(source, functions, hits):
    result, previous_end = [], 0
    for function in functions:
        # ponytail: reject nested/shared-line ranges; use a language-aware adapter if needed.
        if function.start_line <= previous_end:
            raise ValueError(f"Overlapping function ranges: {source}:{function.start_line}")
        previous_end = function.end_line
        result.append(measure_function(source, function, hits))
    return result


def collect(coverage, sources):
    result, seen, lines, branches = [], set(), [], []
    for argument in sources:
        source = Path(argument).resolve(strict=True)
        if source in seen:
            raise ValueError(f"Duplicate source: {source}")
        seen.add(source)
        code, functions = analyze(source)
        hits = source_coverage(coverage, source, code)
        lines.extend(hits["lines"].values())
        branches.extend(hits["branches"].values())
        result.extend(measure_functions(source, functions, hits["lines"]))
    return {"functions": result, "coverage": {"line": summarize(lines), "branch": summarize(branches)}}


def main():
    if len(sys.argv) < 4:
        print("Usage: lizard-metrics.py COVERAGE.lcov OUTPUT.json SOURCE_FILE...", file=sys.stderr)
        return 2
    try:
        metrics = collect(read_lcov(sys.argv[1]), sys.argv[3:])
        with Path(sys.argv[2]).open("x", encoding="utf-8") as output:
            output.write(json.dumps(metrics, indent=2) + "\n")
    except (OSError, ValueError, ImportError) as error:
        print(f"lizard-metrics: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
