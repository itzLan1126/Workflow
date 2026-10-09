"""Preserve mutation evidence and render actionable mutants for human review."""

from difflib import unified_diff
from pathlib import Path
import re


ACTIONABLE = ("survived", "noCoverage", "timeout", "error")


def code_diff(before, after):
    return "\n".join(unified_diff(before.splitlines(), after.splitlines(), lineterm=""))


def function_at(file, source, line):
    try:
        import lizard
    except ImportError:
        return {}
    matches = [f for f in lizard.analyze_file.analyze_source_code(file, source).function_list
               if f.start_line <= line <= f.end_line]
    if not matches:
        return {}
    function = min(matches, key=lambda f: f.end_line - f.start_line)
    return {"function": function.name, "line": function.start_line}


def valid_position(lines, line, column):
    return (1 <= line <= len(lines)
            and 1 <= column <= len(lines[line - 1].rstrip("\r\n").encode("utf-16-le")) // 2 + 1)


def source_offset(source, position):
    lines = source.splitlines(keepends=True)
    line, column = position["line"], position["column"]
    if type(line) is not int or type(column) is not int:
        raise ValueError("Invalid Stryker source position")
    if position == {"line": len(lines) + 1, "column": 1} and source.endswith("\n"):
        return len(source)
    if not valid_position(lines, line, column):
        raise ValueError("Invalid Stryker source position")
    # Stryker columns count UTF-16 code units, including two units for astral characters.
    prefix = lines[line - 1].encode("utf-16-le")[:(column - 1) * 2].decode("utf-16-le")
    return sum(map(len, lines[:line - 1])) + len(prefix)


def stryker_detail(file, source, mutant):
    detail = {**mutant, "file": file}
    location = mutant.get("location")
    if not isinstance(source, str) or not isinstance(location, dict):
        return detail
    start, end = source_offset(source, location["start"]), source_offset(source, location["end"])
    if end < start:
        raise ValueError("Invalid Stryker source range")
    line = location["start"]["line"]
    detail.update({"line": line, **function_at(file, source, line)})
    replacement = mutant.get("replacement")
    if isinstance(replacement, str):
        detail["diff"] = code_diff(source, source[:start] + replacement + source[end:])
    return detail


def cargo_detail(outcome, report_path):
    mutant = outcome["scenario"]["Mutant"]
    function = mutant.get("function") or {}
    span = function.get("span", mutant.get("span", {}))
    detail = {"function": function.get("function_name"), "line": span.get("start", {}).get("line")}
    diff_path = outcome.get("diff_path")
    if diff_path:
        detail.update(read_cargo_diff(report_path, diff_path))
    return detail


def read_cargo_diff(report_path, diff_path):
    path = (report_path.parent / diff_path).resolve()
    if not path.is_relative_to(report_path.parent.resolve()):
        raise ValueError("Cargo diff path must stay inside the report directory")
    detail = {"evidence": str(path)}
    try:
        detail["diff"] = path.read_text(encoding="utf-8")
    except OSError as error:
        detail["detailGap"] = f"Cannot read diff: {error}"
    return detail


def muter_detail(file, mutant):
    point = mutant.get("mutationPoint") or {}
    line = point.get("position", {}).get("line")
    detail = {"id": point.get("mutationOperatorId"), "file": file, "line": line}
    snapshot = mutant.get("mutationSnapshot") or {}
    before, after = snapshot.get("before"), snapshot.get("after")
    if isinstance(before, str) and isinstance(after, str) and line:
        detail.update(diff=code_diff(before, after), diffOffset=line - 1,
                      detailGap="Muter provides a code snippet; function name is unavailable")
    return detail


def safe_detail(factory, *args):
    try:
        return factory(*args)
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        return {"detailGap": f"Cannot extract mutation details: {error}"}


def normalized_entries(report, report_path, statuses):
    return [(m, m["status"]) for m in report["mutants"]]


def stryker_entries(report, report_path, statuses):
    return [({"id": m.get("id"), "file": file,
              **safe_detail(stryker_detail, file, data.get("source"), m)}, statuses[m["status"]])
            for file, data in report["files"].items() for m in data["mutants"]
            if statuses[m["status"]] in ACTIONABLE]


def cargo_entries(report, report_path, statuses):
    return [({"id": o["scenario"]["Mutant"].get("name"), "file": o["scenario"]["Mutant"].get("file"),
              **safe_detail(cargo_detail, o, report_path)}, statuses[o["summary"]])
            for o in report["outcomes"] if o["scenario"] != "Baseline"
            and statuses[o["summary"]] in ACTIONABLE]


def muter_entries(report, report_path, statuses):
    return [({"file": f.get("fileName"), **safe_detail(muter_detail, f.get("fileName"), m)}, statuses[m["testSuiteOutcome"]])
            for f in report["fileReports"] for m in f["appliedOperators"]
            if statuses[m["testSuiteOutcome"]] in ACTIONABLE]


def report_details(report, format, report_path, maps):
    adapters = {"normalized": normalized_entries, "stryker": stryker_entries,
                "cargo-mutants": cargo_entries, "muter": muter_entries}
    entries = adapters[format](report, report_path, maps.get(format))
    return [{**validate_detail(detail), "status": status} for detail, status in entries if status in ACTIONABLE]


def validate_detail(detail):
    fields = {"file": str, "function": str, "line": int, "diff": str,
              "diffOffset": int, "detailGap": str, "evidence": str}
    for field, kind in fields.items():
        value = detail.get(field)
        if value is not None and type(value) is not kind:
            raise ValueError(f"Invalid mutation detail field: {field}")
    return {key: value for key, value in detail.items() if value is not None}


def number_diff_line(line, old, new, output):
    if old is None:
        return old, new
    prefix = line[:1]
    if prefix in ("-", "+"):
        number = {"-": old, "+": new}[prefix]
        output.append(f"{number} {prefix} {line[1:]}")
    old_step, new_step = {"-": (1, 0), "+": (0, 1), " ": (1, 1)}.get(prefix, (0, 0))
    return old + old_step, new + new_step


def numbered_diff(diff, offset=0):
    old = new = None
    output = []
    for line in diff.splitlines():
        hunk = re.match(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if hunk:
            old, new = (int(n) + offset for n in hunk.groups())
        else:
            old, new = number_diff_line(line, old, new, output)
    return "\n".join(output)


def group_mutants(mutants):
    groups = {}
    for mutant in mutants:
        key = (mutant.get("file") or "file unavailable", mutant.get("function") or "function unavailable",
               mutant.get("line") or "?", mutant["status"])
        groups.setdefault(key, []).append(mutant)
    return groups


def render_mutant(mutant):
    output = [f"mutant {mutant.get('id') or '(ID unavailable)'} [{mutant['status']}]"]
    diff = numbered_diff(mutant.get("diff") or "", mutant.get("diffOffset", 0))
    output.append(diff or "Diff unavailable; inspect the original engine report.")
    if mutant.get("detailGap"):
        output.append(mutant["detailGap"])
    if mutant.get("evidence"):
        output.append(f"Evidence: {mutant['evidence']}")
    return [*output, ""]


def render_report(result):
    output = []
    labels = {"survived": "surviving", "noCoverage": "uncovered", "timeout": "timed-out", "error": "error"}
    for (file, function, line, status), mutants in group_mutants(result["mutants"]).items():
        location = f"{file}:{line}"
        output.extend([f'function "{function}" ({location})',
                       f"has {len(mutants)} {labels[status]} mutants:", ""])
        for mutant in mutants:
            output.extend(render_mutant(mutant))
    output.append("Summary: " + ", ".join(f"{count} {status}" for status, count in result["counts"].items()))
    output.extend([f"Exit code: {result['exitCode']}", f"Report: {result['reportPath']}"])
    return "\n".join(output)
