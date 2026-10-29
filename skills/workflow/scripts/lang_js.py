"""JavaScript and TypeScript coverage and mutation commands."""
import os
from shared_languages import Crap, Mutation

STRYKER = ('stryker', '10.1.1')
NODE_HINT = 'Node.js'


def coverage_commands(project, evidence, args):
    return [args or ['node', '--experimental-strip-types', '--test', '--experimental-test-coverage',
                     '--test-reporter=lcov', f'--test-reporter-destination={evidence / "coverage.lcov"}']]


def mutation_command(project, evidence, args):
    executable = 'stryker.cmd' if os.name == 'nt' else 'stryker'
    return args or [executable, 'run', '--testRunner', 'command', '--reporters', 'json']


def prepare_tools(project, check, install):
    from shared_tools import require_system, native_tool
    require_system(['node', '--version'], NODE_HINT)
    if check != 'mutation':
        return None, []
    directory, record = native_tool(*STRYKER, project, install, 'npm')
    return directory, [record]


def incremental_command(command, files, functions):
    return [*command, '--mutate', ','.join(files)]


def report_path(project, evidence):
    return project / 'reports/mutation/mutation.json'


# Ported from dryer 66ff6d2; see references/dryer-LICENSE.txt.
from shared_syntax import Syntax, entries, inside

DUPLICATION_FUNCTIONS = {'function_declaration', 'method_definition', 'arrow_function', 'function_expression'}
DUPLICATION_DECLARATIONS = {'function_declaration', 'method_definition'}
DUPLICATION_DEFINITIONS = {'variable_declarator', 'public_field_definition', 'property_definition'}
DUPLICATION_VALUES = {'arrow_function', 'function_expression'}
DUPLICATION_SYNTAX = Syntax(
    identifiers={'identifier', 'type_identifier', 'property_identifier', 'shorthand_property_identifier',
                 'shorthand_property_identifier_pattern'},
    literals={'number', 'string', 'true', 'false', 'null', 'undefined', 'regex'},
    calls={'call_expression', 'new_expression'}, attributes={'member_expression'}, paths=set())
DUPLICATION_GRAMMARS = {'.tsx': 'tsx', '.jsx': 'tsx'}


def duplication_candidate(node):
    if inside(node, DUPLICATION_FUNCTIONS):
        return False
    if node.type in DUPLICATION_DECLARATIONS:
        return node.child_by_field_name('body') is not None
    return node.type in DUPLICATION_DEFINITIONS and any(c.type in DUPLICATION_VALUES for c in node.named_children)


def duplication_entries(path, file):
    grammar = DUPLICATION_GRAMMARS.get(path.suffix, 'typescript')
    return entries(path, file, grammar, 'typescript', duplication_candidate, DUPLICATION_SYNTAX)


CRAP = Crap('lcov', coverage_commands, 'coverage.lcov')
MUTATION = Mutation('stryker', mutation_command, report_path)
