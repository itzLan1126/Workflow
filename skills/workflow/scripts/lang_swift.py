"""macOS Swift coverage export and Muter commands."""
from pathlib import Path
import shutil
import subprocess
import sys
from shared_languages import Crap, Mutation


XCODE = (['xcrun', 'swift', '--version'], 'Xcode command line tools: xcode-select --install')
MUTER = (['muter', '--version'], 'Muter from https://github.com/muter-mutation-testing/muter')


def prepare_tools(project, check, install):
    from shared_tools import require_system
    require_macos()
    require_system(*XCODE)
    if check != 'mutation':
        return None, []
    # Muter is a system-level install, so the version is recorded rather than pinned.
    return None, [{'name': 'muter', 'version': require_system(*MUTER), 'location': 'PATH'}]


def require_macos():
    if sys.platform != 'darwin':
        raise ValueError('Swift quality checks require macOS')


def coverage_commands(project, evidence, args):
    require_macos()
    command = args or ['xcrun', 'swift', 'test', '--enable-code-coverage']
    if not swift_test_command(command):
        return [command]
    validate_test_command(command)
    return [command, [sys.executable, str(Path(__file__).resolve()), str(project),
                      str(evidence / 'coverage.json'), *args]]


def swift_test_command(command):
    words = [Path(argument).name for argument in command[:3]]
    return words[:2] == ['swift', 'test'] or words == ['xcrun', 'swift', 'test']


def validate_test_command(command):
    if '--enable-code-coverage' not in command or '--disable-code-coverage' in command:
        raise ValueError('Swift test overrides require --enable-code-coverage')
    if set(command) & {'--show-codecov-path', '--show-code-coverage-path', '--show-coverage-path'}:
        raise ValueError('Swift coverage requires a test run before querying the report path')


def export_coverage(project, output, args=()):
    command = args or ['xcrun', 'swift', 'test']
    probe = subprocess.run([*command, '--show-codecov-path'], cwd=project,
                           capture_output=True, text=True, check=True)
    with Path(probe.stdout.strip()).open('rb') as source, Path(output).open('xb') as report:
        shutil.copyfileobj(source, report)


def mutation_command(project, evidence, args):
    require_macos()
    return args or ['muter', 'run', '--format', 'json', '--output', str(evidence / 'mutation.json'), '--skip-update-check']


def incremental_command(command, files, functions):
    return [*command, '--files-to-mutate', ','.join(files)]


def report_path(project, evidence):
    return evidence / 'mutation.json'


CRAP = Crap('llvm-json', coverage_commands, 'coverage.json')
MUTATION = Mutation('muter', mutation_command, report_path)

if __name__ == '__main__':
    try:
        export_coverage(sys.argv[1], sys.argv[2], sys.argv[3:])
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'Swift coverage: {error}', file=sys.stderr)
        raise SystemExit(2)
