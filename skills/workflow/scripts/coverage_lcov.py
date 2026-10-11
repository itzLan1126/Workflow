"""Read LCOV evidence and validate its source fingerprints."""

import base64
import hashlib
from pathlib import Path
import re

def parse_line(record):
    fields = record[3:].split(",")
    if (len(fields) not in (2, 3) or not re.fullmatch(r"[1-9][0-9]*", fields[0])
            or not re.fullmatch(r"[0-9]+", fields[1])):
        raise ValueError(f"Invalid LCOV line record: {record}")
    return int(fields[0]), int(fields[1]), fields[2] if len(fields) == 3 else None


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
    return Path(record[3:]).resolve(), {"lines": {}, "branches": {}, "checksums": {}}


def add_record(current, record):
    if current is None:
        raise ValueError(f"LCOV record outside SF: {record}")
    source, records = current
    if record.startswith("DA:"):
        kind = "lines"
        key, count, checksum = parse_line(record)
        if checksum is not None:
            records["checksums"][key] = checksum
    else:
        kind = "branches"
        key, count = parse_branch(record)
    if key in records[kind]:
        raise ValueError(f"Duplicate LCOV {kind} record in {source}: {record}")
    records[kind][key] = count


def merge_checksums(source, merged, checksums):
    for line, checksum in checksums.items():
        previous = merged.setdefault(line, checksum)
        if previous != checksum:
            raise ValueError(f"Conflicting LCOV checksums: {source}:{line}")


def close_section(files, current):
    if current is None:
        raise ValueError("LCOV end_of_record without SF")
    source, records = current
    merged = files.setdefault(source, {"lines": {}, "branches": {}, "checksums": {}})
    merge_checksums(source, merged["checksums"], records["checksums"])
    for kind in ("lines", "branches"):
        for key, count in records[kind].items():
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


def validate_checksums(source, lines, checksums):
    for line, checksum in checksums.items():
        # LCOV fingerprints UTF-8 source lines without their newline, with unpadded base64 MD5.
        digest = hashlib.md5(lines[line - 1].encode("utf-8"), usedforsecurity=False).digest()
        expected = base64.b64encode(digest).decode("ascii").rstrip("=")
        if checksum != expected:
            raise ValueError(f"LCOV checksum does not match source: {source}:{line}")


def source_coverage(coverage, source, code):
    if source not in coverage:
        raise ValueError(f"Missing exact-path LCOV coverage: {source}")
    hits = coverage[source]
    lines = code.splitlines()
    recorded = [*hits["lines"], *(key[0] for key in hits["branches"])]
    if any(line > len(lines) for line in recorded):
        raise ValueError(f"LCOV line outside source: {source}")
    validate_checksums(source, lines, hits["checksums"])
    return hits


def read(path, source_text_by_path):
    coverage = read_lcov(path)
    for source, code in source_text_by_path.items():
        source_coverage(coverage, source, code)
    for hits in coverage.values():
        hits["branchKind"] = "branch"
    return coverage
