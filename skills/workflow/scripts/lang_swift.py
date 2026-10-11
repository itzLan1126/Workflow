"""macOS Swift coverage export and Muter commands."""
import json
from pathlib import Path
import subprocess
import sys
from shared_languages import Crap, Mutation


def require_macos():
    if sys.platform != 'darwin':
        raise ValueError('Swift quality checks require macOS')


def coverage_commands(project, evidence, args):
    require_macos()
    return [args or ['xcrun', 'swift', 'test', '--enable-code-coverage'],
            [sys.executable, str(Path(__file__).resolve()), str(project), str(evidence / 'coverage.json')]]


def export_coverage(project, output):
    probe = subprocess.run(['xcrun', 'swift', 'build', '--show-bin-path'], cwd=project,
                           capture_output=True, text=True, check=True)
    directory = Path(probe.stdout.strip())
    binaries = sorted(directory.glob('*.xctest/Contents/MacOS/*'))
    if not binaries:
        raise ValueError('Swift test coverage binary not found')
    command = ['xcrun', 'llvm-cov', 'export', str(binaries[0]),
               f'-instr-profile={directory / "codecov/default.profdata"}',
               *(argument for binary in binaries[1:] for argument in ('-object', str(binary)))]
    with Path(output).open('x', encoding='utf-8') as report:
        subprocess.run(command, cwd=project, stdout=report, stderr=sys.stderr, check=True)


def mutation_command(project, evidence, args):
    require_macos()
    return args or ['muter', 'run', '--format', 'json', '--output', str(evidence / 'mutation.json'), '--skip-update-check']


def report_path(project, evidence):
    return evidence / 'mutation.json'


CRAP = Crap('llvm-json', coverage_commands, 'coverage.json')
MUTATION = Mutation('muter', mutation_command, report_path)

if __name__ == '__main__':
    try:
        export_coverage(sys.argv[1], sys.argv[2])
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'Swift coverage: {error}', file=sys.stderr)
        raise SystemExit(2)
