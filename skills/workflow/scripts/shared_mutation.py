"""Score and render mutation evidence independently of programming language."""

from difflib import unified_diff
import re
from importlib import import_module

ACTIONABLE = ("survived", "noCoverage", "timeout", "error")
STATUSES = ("killed", "survived", "noCoverage", "timeout", "unviable", "ignored", "error")
FORMATS = {"normalized": "report_normalized", "stryker": "report_stryker", "cargo-mutants": "report_cargo", "muter": "report_muter"}

def object_value(value):
    if not isinstance(value, dict):
        raise ValueError("Expected an object in mutation report")
    return value


def array(value):
    if not isinstance(value, list):
        raise ValueError("Expected an array in mutation report")
    return value


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


def safe_detail(factory, *args):
    try:
        return factory(*args)
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        return {"detailGap": f"Cannot extract mutation details: {error}"}


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


def adapter(format):
    if not isinstance(format, str) or format not in FORMATS:
        raise ValueError(f"Unsupported mutation format: {format}")
    return import_module(FORMATS[format])


def mutant_status(reader, engine_status):
    if not isinstance(engine_status, str):
        raise ValueError(f"Invalid mutation status: {engine_status}")
    status = reader.STATUSES.get(engine_status)
    if status not in STATUSES:
        raise ValueError(f"Unknown mutation status: {engine_status}")
    return status


def assess(report, format, report_path):
    reader = adapter(format)
    counts = dict.fromkeys(STATUSES, 0)
    details = []
    for engine_status, describe in reader.mutants(object_value(report), report_path):
        status = mutant_status(reader, engine_status)
        counts[status] += 1
        if status in ACTIONABLE:
            details.append({**validate_detail(describe()), "status": status})
    if not sum(counts.values()):
        raise ValueError("No mutations reported")
    assessed = sum(counts[s] for s in ("killed", "survived", "noCoverage", "timeout"))
    return {"format": format, "counts": counts, "assessed": assessed,
            "exitCode": exit_code(counts, assessed), "mutants": details}


def summarize(report, format):
    result = assess(report, format, None)
    result.pop("mutants")
    return result


def report_details(report, format, report_path, maps=None):
    return assess(report, format, report_path)["mutants"]
def exit_code(counts, assessed):
    if counts["error"] or not assessed:
        return 2
    return 1 if counts["survived"] + counts["noCoverage"] + counts["timeout"] else 0


