#!/usr/bin/env python3
"""Compute CRAP scores and gate them, with aggregate coverage, against the skill's standard."""

import json
from pathlib import Path
from shared_crap import calculate, collect, score_functions, gate_coverage, STANDARD, MAX_CRAP, MIN_COVERAGE_PERCENT
from coverage_lcov import read
import sys

from shared_runner import read_config, read_utf8, run_report, run_command
from shared_languages import LANGUAGES, language, arguments, evidence_directory
from importlib import import_module
import os
from shared_tools import options, python_tools, native_tools

def collect_main(args):
    if len(args) < 3:
        raise ValueError('Usage: crap.py collect COVERAGE.lcov OUTPUT.json SOURCE_FILE...')
    sources = {Path(source).resolve(strict=True): read_utf8(source)
               for source in args[2:]}
    metrics = collect(read(args[0], sources), args[2:])
    with Path(args[1]).open('xb') as output:
        output.write((json.dumps(metrics) + '\n').encode())
    return 0


def config_result(path):
    config = read_config(path)
    if 'maxCrap' in config:
        raise ValueError('maxCrap is not configurable; the skill standard is CRAP <= 6')
    execution = run_report(path, config=config)
    result = calculate(execution['report'])
    print(json.dumps(result))
    return 1 if result['findings'] else 0


def read_measurements(project, sources, spec, evidence):
    previous = Path.cwd()
    try:
        os.chdir(project)
        texts = {Path(source).resolve(strict=True): read_utf8(source) for source in sources}
        coverage = import_module({'lcov': 'coverage_lcov', 'llvm-json': 'coverage_llvm'}[spec.format]).read(evidence / spec.coverage, texts)
        return collect(coverage, sources, exclude=spec.exclude)
    finally:
        os.chdir(previous)


CRAP_TOOLS = {'python': ['lizard', 'coverage']}


def language_result(name, args):
    args, install = options(args)
    project, sources, timeout, tool = arguments(args)
    with python_tools(CRAP_TOOLS.get(name, ['lizard']), project, install) as tools, \
            native_tools(language(name), 'crap', project, install, tool) as native:
        return prepared_result(name, project, sources, timeout, tool, tools + native)


def prepared_result(name, project, sources, timeout, tool, tools):
    if not sources:
        raise ValueError('Require at least one source file')
    spec = language(name).CRAP
    evidence = evidence_directory()
    commands = spec.commands(project, evidence, tool)
    environment = {'WORKFLOW_COVERAGE_FILE': str(evidence / spec.coverage)}
    (evidence / 'config.json').write_bytes(json.dumps({'cwd': str(project), 'commands': commands,
                                                     'sources': sources, 'timeoutMs': timeout,
                                                     'env': environment, 'tools': tools}).encode())
    for command in commands:
        if run_command(command, project, timeout, env={**os.environ, **environment}) != 0:
            raise ValueError('Coverage command failed')
    measurements = read_measurements(project, sources, spec, evidence)
    (evidence / 'measurements.json').write_bytes(json.dumps(measurements).encode())
    result = calculate(measurements)
    print(json.dumps(result))
    return 1 if result['findings'] else 0


def dispatch(args):
    if not args:
        raise ValueError('Usage: python crap.py CONFIG.json')
    if args[0] in LANGUAGES:
        return language_result(args[0], args[1:])
    if args[0] == 'collect':
        return collect_main(args[1:])
    if len(args) != 1:
        raise ValueError('Usage: python crap.py CONFIG.json')
    return config_result(args[0])


def main():
    try:
        return dispatch(sys.argv[1:])
    except (OSError, ValueError, ImportError, KeyError, TypeError, IndexError) as error:
        print(f'CRAP: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
