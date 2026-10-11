"""Rust uses nightly branch coverage and cargo-mutants."""
import re
import subprocess
from shared_languages import Crap, Mutation


def coverage_commands(project, evidence, args):
    probe = subprocess.run(['rustc', '+nightly', '--version'], capture_output=True, text=True)
    if probe.returncode or 'nightly' not in probe.stdout:
        raise ValueError('Rust CRAP check requires a nightly toolchain for branch coverage')
    return [args or ['cargo', '+nightly', 'llvm-cov', '--branch', '--lcov', '--output-path', str(evidence / 'coverage.lcov')]]


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
        if token == '\n':
            line += 1
        if re.fullmatch(r'#\s*\[\s*cfg\s*\(\s*test\s*\)\s*\]', token):
            pending = True
            start = line
        if token == '{':
            depth += 1
            if pending:
                pending = False
                target = depth
        if token == '}':
            if start is not None and depth == target:
                ranges.append((start, line))
                start = None
            depth -= 1
    return ranges


CRAP = Crap('lcov', coverage_commands, 'coverage.lcov', exclude_tests)
MUTATION = Mutation('cargo-mutants', mutation_command, report_path)
