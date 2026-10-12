"""Explicit lazy language registry and the shared language command contract."""

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
import sys
import tempfile

from shared_runner import DEFAULT_TIMEOUT_MS, is_timeout

LANGUAGES = {'python': 'lang_python', 'js': 'lang_js', 'ts': 'lang_js',
             'rust': 'lang_rust', 'swift': 'lang_swift'}


@dataclass(frozen=True)
class Crap:
    format: str
    commands: object
    coverage: str
    exclude: object = None


@dataclass(frozen=True)
class Mutation:
    format: str
    command: object
    report: object


def language(name):
    return import_module(LANGUAGES[name])


def split_tool(args):
    if '--' in args:
        index = args.index('--')
        return args[:index], args[index + 1:]
    return args, []


def take_timeout(args):
    timeout = DEFAULT_TIMEOUT_MS
    if '--timeout-ms' in args:
        index = args.index('--timeout-ms')
        if index + 1 >= len(args):
            raise ValueError('Require --timeout-ms N')
        timeout = int(args[index + 1])
        del args[index:index + 2]
    if not is_timeout(timeout):
        raise ValueError('Require positive timeoutMs (max 2147483647)')
    return timeout


def arguments(args):
    args, tool = split_tool(list(args))
    timeout = take_timeout(args)
    if not args or any(arg.startswith('--') for arg in args):
        raise ValueError('Require project and source paths, followed by -- tool args')
    project = Path(args[0]).resolve(strict=True)
    if not project.is_dir():
        raise ValueError('project must be a directory')
    return project, args[1:], timeout, tool


def evidence_directory():
    evidence = Path(tempfile.mkdtemp(prefix='workflow-evidence-'))
    print(f'Evidence: {evidence}', file=sys.stderr, flush=True)
    return evidence
