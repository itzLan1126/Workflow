#!/usr/bin/env python3
"""Run mutmut 3 in a fresh analysis copy and export per-mutant results in the normalized format."""

import ast
import json
from pathlib import Path
import subprocess
import sys

from mutation_report import ACTIONABLE

# Keys are mutmut's own status names. Anything else (suspicious, segfault, interrupted,
# not checked) is abnormal or unfinished and must be investigated rather than scored.
STATUSES = {"survived": "survived", "no tests": "noCoverage",
            "timeout": "timeout", "skipped": "ignored", "caught by type check": "unviable"}
PYTEST_EXITS = {0: "survived", 1: "killed", 2: "error", 3: "error", 4: "error", 5: "noCoverage"}


def classify(code, status_by_exit_code):
    # Only pytest exit 1 proves a test failure, regardless of mutmut's display labels.
    if type(code) is not int:
        return "error"
    if code in PYTEST_EXITS:
        return PYTEST_EXITS[code]
    return STATUSES.get(status_by_exit_code.get(code), "error")


def collect(mutants_dir, status_by_exit_code):
    metas = sorted(Path(mutants_dir).rglob("*.meta"))
    if not metas:
        raise ValueError("No mutmut results found under mutants/")
    mutants = []
    for meta in metas:
        exit_codes = json.loads(meta.read_text(encoding="utf-8")).get("exit_code_by_key")
        if not isinstance(exit_codes, dict):
            raise ValueError(f"Unrecognized mutmut metadata: {meta}")
        mutants.extend({"id": key, "status": classify(code, status_by_exit_code)}
                       for key, code in exit_codes.items())
    return mutants


def named_node(nodes, kind, name):
    return next(node for node in nodes if isinstance(node, kind) and node.name == name)


def function_position(path, name, class_name):
    nodes = ast.parse(path.read_text(encoding="utf-8")).body
    if class_name:
        nodes = named_node(nodes, ast.ClassDef, class_name).body
    function = named_node(nodes, (ast.FunctionDef, ast.AsyncFunctionDef), name)
    first_line = min([function.lineno, *(d.lineno for d in function.decorator_list)])
    return function.lineno, first_line - 1


def add_details(mutants):
    from mutmut.mutation.diff_apply import find_mutant, get_diff_for_mutant
    from mutmut.utils.format_utils import orig_function_and_class_names_from_key

    for mutant in mutants:
        if mutant["status"] not in ACTIONABLE:
            continue
        try:
            path = find_mutant(mutant["id"]).path
            name, class_name = orig_function_and_class_names_from_key(mutant["id"])
            mutant.update(file=str(path), function=f"{class_name}.{name}" if class_name else name)
            line, offset = function_position(path, name, class_name)
            mutant.update(line=line, diffOffset=offset,
                          diff=get_diff_for_mutant(mutant["id"], path=path))
        except (OSError, ValueError, StopIteration, SyntaxError, KeyError) as error:
            mutant["detailGap"] = f"Cannot extract mutation diff: {error}"
    return mutants


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) != 1:
            raise ValueError("Usage: python mutmut_export.py REPORT.json")
        if Path("mutants").exists():
            raise ValueError("mutants/ already exists; mutmut would reuse stale results. Use a fresh analysis copy")
        # mutmut exits nonzero when the clean baseline fails, so no report is written.
        subprocess.run([sys.executable, "-m", "mutmut", "run"], check=True)
        from mutmut.__main__ import status_by_exit_code
        report = {"baselinePassed": True, "mutants": add_details(collect("mutants", status_by_exit_code))}
        Path(args[0]).write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 0
    except (OSError, ValueError, ImportError, subprocess.CalledProcessError) as error:
        print(f"mutmut_export: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
