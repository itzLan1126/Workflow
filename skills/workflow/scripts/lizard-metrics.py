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


def read_lcov(path):
    files = {}
    source = None
    records = {}
    for record in Path(path).read_text(encoding="utf-8").splitlines():
        if record.startswith("SF:"):
            if source is not None or not record[3:]:
                raise ValueError("LCOV has nested or empty SF records")
            source, records = Path(record[3:]).resolve(), {"lines": {}, "branches": {}}
        elif record.startswith(("DA:", "BRDA:")):
            if source is None:
                raise ValueError(f"LCOV record outside SF: {record}")
            kind, parse = ("lines", parse_line) if record.startswith("DA:") else ("branches", parse_branch)
            key, count = parse(record)
            if key in records[kind]:
                raise ValueError(f"Duplicate LCOV {kind} record in {source}: {record}")
            records[kind][key] = count
        elif record == "end_of_record":
            if source is None:
                raise ValueError("LCOV end_of_record without SF")
            merged = files.setdefault(source, {"lines": {}, "branches": {}})
            for kind, counts in records.items():
                for key, count in counts.items():
                    merged[kind][key] = merged[kind].get(key, 0) + count
            source = None
    if source is not None or not files:
        raise ValueError("Incomplete or empty LCOV report")
    return files


def summarize(counts):
    return {"covered": sum(count > 0 for count in counts), "total": len(counts)}


def collect(coverage, sources):
    import lizard
    from lizard_languages import get_reader_for

    result, seen, lines, branches = [], set(), [], []
    for argument in sources:
        source = Path(argument).resolve(strict=True)
        if source in seen:
            raise ValueError(f"Duplicate source: {source}")
        seen.add(source)
        if get_reader_for(str(source)) is None:
            raise ValueError(f"Unsupported source: {source}")
        code = source.read_text(encoding="utf-8")
        functions = sorted(lizard.analyze_file.analyze_source_code(
            str(source), code).function_list, key=lambda function: function.start_line)
        if not functions:
            raise ValueError(f"No functions found: {source}")
        if source not in coverage:
            raise ValueError(f"Missing exact-path LCOV coverage: {source}")
        hits, branch_hits = coverage[source]["lines"], coverage[source]["branches"]
        if any(line > len(code.splitlines()) for line in [*hits, *(key[0] for key in branch_hits)]):
            raise ValueError(f"LCOV line outside source: {source}")
        lines.extend(hits.values())
        branches.extend(branch_hits.values())
        previous_end = 0
        for function in functions:
            # ponytail: reject nested/shared-line ranges; use a language-aware adapter if needed.
            if function.start_line <= previous_end:
                raise ValueError(f"Overlapping function ranges: {source}:{function.start_line}")
            previous_end = function.end_line
            counts = [count for line, count in hits.items()
                      if function.start_line <= line <= function.end_line]
            if not counts:
                raise ValueError(f"Missing line coverage: {source}:{function.name}")
            result.append({"file": str(source), "name": function.name,
                           "line": function.start_line,
                           "complexity": function.cyclomatic_complexity,
                           "covered": sum(count > 0 for count in counts),
                           "total": len(counts), "coverageKind": "line"})
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
