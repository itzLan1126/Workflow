"""Rust uses nightly branch coverage and cargo-mutants."""
import re
from pathlib import Path
import subprocess
import sys
from shared_languages import Crap, Mutation


def coverage_commands(project, evidence, args):
    return [[sys.executable, str(Path(__file__).resolve())],
            args or ['cargo', '+nightly', 'llvm-cov', '--branch', '--lcov', '--output-path', str(evidence / 'coverage.lcov')]]


def require_nightly():
    probe = subprocess.run(['rustc', '+nightly', '--version'], capture_output=True, text=True)
    if probe.returncode or 'nightly' not in probe.stdout:
        raise ValueError('Rust CRAP check requires a nightly toolchain for branch coverage')


def mutation_command(project, evidence, args):
    return args or ['cargo', 'mutants', '--output', str(evidence)]


def report_path(project, evidence):
    return evidence / 'mutants.out/outcomes.json'


def exclude_tests(source, code):
    # Lizard's tokenizer removes braces in comments and string literals.
    from lizard_languages import get_reader_for
    tokens = get_reader_for(str(source)).generate_tokens(code)
    ranges, pending, depth, start, line, target = [], False, 0, None, 1, None
    for token in tokens:
        line += token.count('\n')
        if starts_test_range(token, start):
            pending, start = True, line
        pending, start = close_test_declaration(ranges, start, line, pending, token)
        if token == '{':
            depth += 1
            if pending:
                pending, target = False, depth
        if token == '}':
            start = close_test_range(ranges, start, line, depth, target)
            depth -= 1
    return ranges


def starts_test_range(token, start):
    return start is None and re.fullmatch(r'#\s*\[\s*cfg\s*\(\s*test\s*\)\s*\]', token)


def close_test_declaration(ranges, start, line, pending, token):
    if token == ';' and pending:
        ranges.append((start, line))
        return False, None
    return pending, start


def close_test_range(ranges, start, line, depth, target):
    if start is not None and depth == target:
        ranges.append((start, line))
        return None
    return start


CRAP = Crap('lcov', coverage_commands, 'coverage.lcov', exclude_tests)
MUTATION = Mutation('cargo-mutants', mutation_command, report_path)

if __name__ == '__main__':
    try:
        require_nightly()
    except (OSError, ValueError) as error:
        print(f'Rust coverage: {error}', file=sys.stderr)
        raise SystemExit(2)
