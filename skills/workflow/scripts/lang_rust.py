"""Rust uses nightly branch coverage and cargo-mutants."""
import codecs
import re
from pathlib import Path
import subprocess
import sys
from shared_languages import Crap, Mutation


def coverage_commands(project, evidence, args):
    return [[sys.executable, str(Path(__file__).resolve())],
            args or ['cargo', '+nightly', 'llvm-cov', '--branch', '--lcov', '--output-path', str(evidence / 'coverage.lcov')]]


RUST_PREREQUISITES = {
    'crap': [(['cargo', '--version'], 'Rust with rustup', ''),
             (['rustc', '+nightly', '--version'], 'nightly Rust: rustup toolchain install nightly', 'nightly'),
             (['rustup', 'component', 'list', '--installed', '--toolchain', 'nightly'],
              'nightly LLVM tools: rustup component add llvm-tools-preview --toolchain nightly', 'llvm-tools')],
    'mutation': [(['cargo', '--version'], 'Rust with rustup', '')]}
RUST_TOOLS = {'crap': ('cargo-llvm-cov', '0.9.1'), 'mutation': ('cargo-mutants', '27.1.0')}


def prepare_tools(project, check, install):
    from shared_tools import require_system, native_tool
    for command, hint, contains in RUST_PREREQUISITES[check]:
        require_system(command, hint, contains)
    directory, record = native_tool(*RUST_TOOLS[check], project, install, 'cargo')
    return directory, [record]


def require_nightly():
    probe = subprocess.run(['rustc', '+nightly', '--version'], capture_output=True, text=True)
    if probe.returncode or 'nightly' not in probe.stdout:
        raise ValueError('Rust CRAP check requires a nightly toolchain for branch coverage')


def mutation_command(project, evidence, args):
    return args or ['cargo', 'mutants', '--output', str(evidence)]


def incremental_command(command, files, functions):
    return [*command, *(argument for file in files for argument in ('--file', file))]


def report_path(project, evidence):
    return evidence / 'mutants.out/outcomes.json'


def exclude_tests(source, code):
    test_attribute = r'#\s*\[\s*cfg\s*\(\s*test\s*\)\s*\]'
    tokens = rust_tokens(source, code.removeprefix(codecs.BOM_UTF8.decode()))
    ranges, line, had_code, boundary = [], 1, False, None
    for token in tokens:
        if re.fullmatch(test_attribute, token):
            require_test_boundary(had_code)
            start = line
            line += token.count('\n')
            line = test_declaration_end(tokens, line)
            ranges.append((start, line))
            boundary = line
        elif re.fullmatch(r'#\s*\[', token):
            end = test_block_end(tokens, line + token.count('\n'), '[', ']')
            had_code = had_code and end == line
            line = end
        else:
            had_code = outside_test_token(token, had_code, line == boundary)
            line += token.count('\n')
    return ranges


def rust_tokens(source, code):
    # Extend Lizard before its string rules for raw literals, lifetimes, and attributes.
    from lizard_languages import get_reader_for
    test_attribute = r'#\s*\[\s*cfg\s*\(\s*test\s*\)\s*\]'
    addition = (r'|\b(?:br|cr|r)(?P<rust_raw_hashes>\#*)".*?"(?P=rust_raw_hashes)'
                r'|\br\#[^\W\d]\w*'
                r"|'[^\W\d]\w*(?![\w'])|" + test_attribute + r'|#\s*\[')
    reader, position = get_reader_for(str(source)), 0
    while True:
        for token in reader.generate_tokens(code[position:], addition=addition):
            if code.startswith('/*', position):
                end = block_comment_end(code, position)
                comment, position = code[position:end], end
                yield comment
                if len(comment) != len(token):
                    break
            else:
                position += len(token)
                yield token
        else:
            return


def block_comment_end(code, start):
    depth = 1
    for marker in re.compile(r'/\*|\*/').finditer(code, start + 2):
        depth += 1 if marker.group() == '/*' else -1
        if not depth:
            return marker.end()
    raise ValueError('Unclosed Rust block comment')


def require_test_boundary(ambiguous):
    if ambiguous:
        raise ValueError('Ambiguous Rust test boundary: production and tests share a line')


def outside_test_token(token, had_code, at_boundary):
    if token.isspace() or token.startswith(('//', '/*')):
        return had_code and '\n' not in token
    require_test_boundary(at_boundary)
    return True


def test_declaration_end(tokens, line):
    prefix = ''
    for token in tokens:
        line += token.count('\n')
        if re.fullmatch(r'#\s*\[', token):
            line = test_block_end(tokens, line, '[', ']')
            continue
        if token.startswith(('#[', '//', '/*')):
            prefix += ' '
            continue
        if token in ('fn', 'mod'):
            # The compiler validates modifiers; other declarations introduce punctuation.
            if not re.fullmatch(r'\s*(?:pub(?:\s*\([^()]*\))?\s*)?'
                                r'(?:(?:(?!r\#*")\w+\b|(?:r\#*)?"[^"]*"\#*)\s*)*', prefix):
                raise ValueError('Unsupported Rust test declaration: require a module or function')
            break
        prefix += token
    else:
        raise ValueError('Unsupported Rust test declaration: require a module or function')
    return test_signature_end(tokens, line)


def test_signature_end(tokens, line):
    nesting = []
    for token in tokens:
        line += token.count('\n')
        if token == ';' and not nesting:
            return line
        if token == '{' and not nesting:
            return test_block_end(tokens, line)
        update_signature_nesting(nesting, token)
    raise ValueError('Unclosed Rust test declaration')


def update_signature_nesting(nesting, token):
    token = re.sub(r'^#\s*(?=\[)', '', token)
    if token in ('<', '>') and any(delimiter != '<' for delimiter in nesting):
        return
    closing = {')': '(', ']': '[', '}': '{', '>': '<'}
    if token in closing.values():
        nesting.append(token)
    elif token in closing:
        close_signature_delimiter(nesting, closing[token])


def close_signature_delimiter(nesting, opening):
    if not nesting or nesting.pop() != opening:
        raise ValueError('Unbalanced Rust test declaration')


def test_block_end(tokens, line, opening='{', closing='}'):
    depth = 1
    for token in tokens:
        line += token.count('\n')
        token = re.sub(r'^#\s*(?=\[)', '', token)
        if token == opening:
            depth += 1
        if token == closing:
            depth -= 1
        if not depth:
            return line
    raise ValueError('Unclosed Rust test declaration')


# Ported from dryer 66ff6d2; see references/dryer-LICENSE.txt.
from shared_syntax import Syntax, entries

DUPLICATION_SYNTAX = Syntax(
    identifiers={'identifier', 'type_identifier', 'field_identifier'},
    literals={'integer_literal', 'float_literal', 'string_literal', 'raw_string_literal', 'char_literal',
              'boolean_literal'},
    calls={'call_expression'}, attributes={'field_expression'},
    paths={'scoped_identifier', 'scoped_type_identifier', 'generic_type'})


def duplication_candidate(node):
    if node.type != 'function_item' or node.child_by_field_name('body') is None:
        return False
    # Closures and functions nested in a body belong to their enclosing function.
    return node.parent.type != 'block' and not duplication_in_tests(node)


def duplication_in_tests(node):
    parent = node.parent
    while parent is not None:
        if parent.type == 'mod_item' and parent.child_by_field_name('name').text == b'tests':
            return True
        parent = parent.parent
    return False


def duplication_entries(path, file):
    return entries(path, file, 'rust', 'rust', duplication_candidate, DUPLICATION_SYNTAX)


CRAP = Crap('lcov', coverage_commands, 'coverage.lcov', exclude_tests)
MUTATION = Mutation('cargo-mutants', mutation_command, report_path)

if __name__ == '__main__':
    try:
        require_nightly()
    except (OSError, ValueError) as error:
        print(f'Rust coverage: {error}', file=sys.stderr)
        raise SystemExit(2)
