#!/usr/bin/env python3
"""Run mutmut 3 in a fresh analysis copy and export per-mutant results in the normalized format."""

import ast
import json
from pathlib import Path
import subprocess
import sys

from shared_mutation import ACTIONABLE
from shared_languages import Crap, Mutation
from shared_runner import read_json, read_utf8


def coverage_commands(project, evidence, args):
    rcfile = evidence / 'coveragerc'
    rcfile.write_bytes(('[run]\nbranch = true\nsource = ' + str(project) + '\npatch = subprocess\ndata_file = ' + str(evidence / '.coverage') + '\n').encode())
    return [[sys.executable, '-m', 'coverage', step[0], f'--rcfile={rcfile}', *step[1:]]
            for step in (['run', *(args or ['-m', 'pytest'])], ['combine'],
                         ['lcov', '-o', str(evidence / 'coverage.lcov')])]


def mutation_command(project, evidence, args):
    return args or [sys.executable, str(Path(__file__).resolve()), str(evidence / 'mutation.json')]


def report_path(project, evidence):
    return evidence / 'mutation.json'


CRAP = Crap('lcov', coverage_commands, 'coverage.lcov')
MUTATION = Mutation('normalized', mutation_command, report_path)

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
        exit_codes = read_json(meta).get("exit_code_by_key")
        if not isinstance(exit_codes, dict):
            raise ValueError(f"Unrecognized mutmut metadata: {meta}")
        mutants.extend({"id": key, "status": classify(code, status_by_exit_code)}
                       for key, code in exit_codes.items())
    return mutants


def named_node(nodes, kind, name):
    return next(node for node in nodes if isinstance(node, kind) and node.name == name)


def function_position(path, name, class_name):
    nodes = ast.parse(read_utf8(path)).body
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
                          diff=get_diff_for_mutant(mutant["id"]))
        except (OSError, ValueError, StopIteration, SyntaxError, KeyError) as error:
            mutant["detailGap"] = f"Cannot extract mutation diff: {error}"
    return mutants


# Python-only reduction of dryer astnorm/extract at 66ff6d2; see dryer-LICENSE.txt.
DUPLICATION_OPERATORS = {
    '+', '-', '*', '/', '//', '%', '**', '==', '!=', '<', '>', '<=', '>=',
    '&', '|', '^', '<<', '>>', '+=', '-=', '*=', '/=', '//=', '%=', '**=',
    '&=', '|=', '^=', '<<=', '>>=', '~', 'and', 'or', 'not', 'in', 'is', 'not in', 'is not', '=', ':=',
}
DUPLICATION_LITERALS = {'integer', 'float', 'true', 'false', 'none', 'string'}


def duplication_leaf(node, head):
    if node.type == 'identifier':
        return [':symbol', node.text.decode()] if head == 'callee' else ':symbol'
    if duplication_literal(node):
        return ':literal'
    if node.type in DUPLICATION_OPERATORS:
        return [':symbol', node.type]
    return None


def duplication_literal(node):
    return node.type in DUPLICATION_LITERALS and not any(c.type == 'interpolation' for c in node.children)


def duplication_children(node, head):
    if node.type == 'attribute':
        return [(node.child_by_field_name('object'), None),
                (node.child_by_field_name('attribute'), head)]
    if node.type == 'call':
        return [(node.child_by_field_name('function'), 'callee'),
                (node.child_by_field_name('arguments'), None)]
    if node.type == 'parenthesized_expression':
        return [(duplication_expression(node), head)]
    return [(child, None) for child in node.children if duplication_keep(child)]


def duplication_expression(node):
    return next(child for child in node.named_children if child.type != 'comment')


def duplication_keep(node):
    return node.type != 'comment' and (node.is_named or node.type in DUPLICATION_OPERATORS)


def duplication_normalize(root):
    cache = {}
    stack = [(root, None)]
    pending = []
    while stack:
        node, head = stack.pop()
        leaf = duplication_leaf(node, head)
        if leaf is not None:
            cache[node.id] = leaf
            continue
        children = duplication_children(node, head)
        pending.append((node, children))
        stack.extend(children)
    for node, children in reversed(pending):
        cache[node.id] = duplication_assemble(node, children, cache)
    return cache[root.id]


def duplication_assemble(node, children, cache):
    values = [cache[child.id] for child, _ in children]
    if node.type == 'parenthesized_expression':
        return values[0]
    return [':' + node.type, *values]


def duplication_nested(node):
    parent = node.parent
    while parent is not None:
        if parent.type == 'class_definition':
            return False
        if parent.type == 'function_definition':
            return True
        parent = parent.parent
    return False


def duplication_entries(path, file):
    import tree_sitter
    from tree_sitter_language_pack import get_parser
    from shared_duplication import fingerprint_tree

    tree = get_parser('python').parse(read_utf8(path).encode())
    if tree.root_node.has_error:
        raise ValueError(f'Unparseable Python source: {path}')
    entries = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        stack.extend(reversed(node.children))
        if node.type == 'function_definition' and not duplication_nested(node):
            count, fingerprints = fingerprint_tree(duplication_normalize(node))
            entries.append({'language': 'python', 'file': file,
                            'startLine': node.start_point.row + 1,
                            'endLine': node.end_point.row + bool(node.end_point.column),
                            'nodes': count, 'fingerprints': fingerprints})
    return entries


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
        Path(args[0]).write_bytes(json.dumps(report).encode())
        return 0
    except (OSError, ValueError, ImportError, subprocess.CalledProcessError) as error:
        print(f"mutmut_export: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
