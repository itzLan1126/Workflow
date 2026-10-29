"""Pinned tools owned by the skill, never installed into the project interpreter."""
from contextlib import contextmanager
from importlib import metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from shared_runner import run_command, read_json, DEFAULT_TIMEOUT_MS

PYTHON_TOOLS = {'lizard': '1.17.31', 'coverage': '7.16.2', 'mutmut': '3.8.0',
                'tree-sitter': '0.25.2', 'tree-sitter-language-pack': '0.9.0'}
DEFAULT_TOOL_HOME = '~/.cache/workflow/tools'
INTERPRETER = 'interpreter'
PYTHON_INSTALLER = [sys.executable, '-m', 'pip', 'install', '--no-input', '--target', '{root}', '{name}=={version}']
NATIVE_INSTALLERS = {
    'npm': ['npm', 'install', '--prefix', '{root}', '--no-package-lock', '--no-save', '@stryker-mutator/core@{version}'],
    'cargo': ['cargo', 'install', '{name}', '--version', '{version}', '--locked', '--root', '{root}'],
}
NATIVE_BIN = {'npm': 'node_modules/.bin', 'cargo': 'bin'}
NATIVE_FILES = {name: name + (suffix if os.name == 'nt' else '')
                for name, suffix in (('stryker', '.cmd'), ('cargo-mutants', '.exe'), ('cargo-llvm-cov', '.exe'))}
MARKER = 'complete.json'
# Cargo subcommand binaries expect their subcommand name as the first argument.
NATIVE_SUBCOMMANDS = {'cargo-mutants': ['mutants'], 'cargo-llvm-cov': ['llvm-cov']}
SYSTEM_NOTE = 'system toolchains are never installed automatically'


def options(args):
    args = list(args)
    boundary = args.index('--') if '--' in args else len(args)
    install = '--no-install' not in args[:boundary]
    if not install:
        args.remove('--no-install')
    return args, install


def tool_root(project):
    root = Path(os.environ.get('WORKFLOW_TOOL_HOME', DEFAULT_TOOL_HOME)).expanduser().resolve()
    if root.is_relative_to(project.resolve()):
        raise ValueError('Tool environment must be outside the project')
    root.mkdir(parents=True, exist_ok=True)
    return root


def probe(command, expected):
    result = subprocess.run(command, capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    if result.returncode or expected not in output:
        raise ValueError(f'Tool check failed: {" ".join(command)}: {output}')
    return output


def require_system(command, hint, contains=''):
    try:
        return probe(command, contains)
    except (OSError, ValueError) as error:
        raise ValueError(f'{error}. Install {hint}; {SYSTEM_NOTE}') from error


def owned_tool(directory, name, pinned, install, installer, check):
    """Install once into a skill-owned directory, then verify on every use."""
    if not directory.exists():
        if not install:
            raise ValueError(f'Missing pinned {name} {pinned}; omit --no-install to install')
        build(directory, name, pinned, installer, check)
    marker = directory / MARKER
    if not marker.is_file() or read_json(marker) != {'name': name, 'version': pinned}:
        raise ValueError(f'Incomplete tool environment: {directory}; remove it and retry')
    check()
    return {'name': name, 'version': pinned, 'location': str(directory)}


def build(directory, name, pinned, installer, check):
    directory.mkdir()
    try:
        command = [part.format(root=directory, name=name, version=pinned) for part in installer]
        if run_command(command, directory, DEFAULT_TIMEOUT_MS) != 0:
            raise ValueError(f'Tool install failed: {command[0]} (see installer output)')
        check()
        (directory / MARKER).write_bytes(json.dumps({'name': name, 'version': pinned}).encode())
    except BaseException:
        shutil.rmtree(directory)
        raise


def python_version(directory, name, pinned):
    versions = [d.version for d in metadata.distributions(name=name, path=[str(directory)])]
    if versions != [pinned]:
        raise ValueError(f'Tool check failed: {name} {pinned} in {directory}: found {versions}')


def python_package(name, project, install):
    pinned = PYTHON_TOOLS[name]
    try:
        if metadata.version(name) == pinned:
            return {'name': name, 'version': pinned, 'location': INTERPRETER}
    except metadata.PackageNotFoundError:
        pass
    directory = tool_root(project) / f'{name}-{pinned}-py{sys.version_info.major}.{sys.version_info.minor}'
    return owned_tool(directory, name, pinned, install, PYTHON_INSTALLER,
                      lambda: python_version(directory, name, pinned))


@contextmanager
def prepended(variable, entries):
    """Put owned tool locations first for child commands, then restore the variable."""
    previous = os.environ.get(variable)
    os.environ[variable] = os.pathsep.join([*entries, *filter(None, [previous])])
    try:
        yield
    finally:
        os.environ.pop(variable)
        if previous is not None:
            os.environ[variable] = previous


@contextmanager
def python_tools(names, project, install):
    """Expose owned packages to this process and to child commands, then restore both."""
    records = [python_package(name, project, install) for name in names]
    sites = [record['location'] for record in records if record['location'] != INTERPRETER]
    previous = list(sys.path)
    sys.path[:0] = sites
    try:
        with prepended('PYTHONPATH', sites):
            yield records
    finally:
        sys.path[:] = previous


@contextmanager
def native_tools(module, check, project, install, replaced):
    """Check system prerequisites and expose pinned engine binaries unless the command is replaced."""
    if replaced:
        yield []
        return
    directory, records = module.prepare_tools(project, check, install)
    with prepended('PATH', [directory] if directory else []):
        yield records


def native_version(binary, name, pinned):
    return probe([binary, *NATIVE_SUBCOMMANDS.get(name, []), '--version'], pinned)


def existing_native(name, pinned, project, kind):
    """Find a pinned engine in the project's own binaries or on PATH, with the directory to prepend."""
    local = project / NATIVE_BIN['npm'] / NATIVE_FILES[name]
    found, directory = (str(local), str(local.parent)) if kind == 'npm' and local.exists() else (shutil.which(name), None)
    if not found:
        return None, None
    try:
        native_version(found, name, pinned)
    except (OSError, ValueError):
        return None, None
    return found, directory


def native_tool(name, pinned, project, install, kind):
    """Return the directory to put on PATH (None when already on PATH) and the evidence record."""
    found, directory = existing_native(name, pinned, project, kind)
    if found:
        return directory, {'name': name, 'version': pinned, 'location': found}
    directory = tool_root(project) / f'{name}-{pinned}'
    binaries = directory / NATIVE_BIN[kind]
    binary = str(binaries / NATIVE_FILES[name])
    record = owned_tool(directory, name, pinned, install, NATIVE_INSTALLERS[kind],
                        lambda: native_version(binary, name, pinned))
    return str(binaries), record
