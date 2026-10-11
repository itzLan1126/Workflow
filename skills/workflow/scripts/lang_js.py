"""JavaScript and TypeScript coverage and mutation commands."""
from shared_languages import Crap, Mutation


def coverage_commands(project, evidence, args):
    return [args or ['node', '--experimental-strip-types', '--test', '--experimental-test-coverage',
                     '--test-reporter=lcov', f'--test-reporter-destination={evidence / "coverage.lcov"}']]


def mutation_command(project, evidence, args):
    return args or [str(project / 'node_modules/.bin/stryker'), 'run', '--testRunner', 'command', '--reporters', 'json']


def report_path(project, evidence):
    return project / 'reports/mutation/mutation.json'


CRAP = Crap('lcov', coverage_commands, 'coverage.lcov')
MUTATION = Mutation('stryker', mutation_command, report_path)
