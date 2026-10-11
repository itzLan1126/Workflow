#!/usr/bin/env python3
"""Compute CRAP scores and gate them, with aggregate coverage, against the skill's standard."""

import json
from pathlib import Path
from shared_crap import calculate, collect, score_functions, gate_coverage, STANDARD, MAX_CRAP, MIN_COVERAGE_PERCENT
from coverage_lcov import read
import sys

from shared_runner import read_config, run_report, run_command
from shared_languages import LANGUAGES, language, arguments, evidence_directory
from importlib import import_module
import os

def collect_main(args):
    if len(args) < 3:
        raise ValueError('Usage: crap.py collect COVERAGE.lcov OUTPUT.json SOURCE_FILE...')
    sources = {Path(source).resolve(strict=True): Path(source).read_text(encoding='utf-8')
               for source in args[2:]}
    metrics = collect(read(args[0], sources), args[2:])
    with Path(args[1]).open('x', encoding='utf-8') as output:
        output.write(json.dumps(metrics, indent=2) + '\n')
    return 0


def config_result(path):
    config = read_config(path)
    if 'maxCrap' in config:
        raise ValueError('maxCrap is not configurable; the skill standard is CRAP <= 6')
    execution = run_report(path, config=config)
    result = calculate(execution['report'])
    print(json.dumps(result, indent=2, allow_nan=False))
    return 1 if result['findings'] else 0


def language_result(name, args):
    project, sources, timeout, tool = arguments(args)
    if not sources:
        raise ValueError('Require at least one source file')
    spec = language(name).CRAP
    evidence = evidence_directory()
    for command in spec.commands(project, evidence, tool):
        if run_command(command, project, timeout) != 0:
            raise ValueError('Coverage command failed')
    previous = Path.cwd()
    try:
        os.chdir(project)
        texts = {Path(source).resolve(strict=True): Path(source).read_text(encoding='utf-8') for source in sources}
        coverage = import_module({'lcov': 'coverage_lcov', 'llvm-json': 'coverage_llvm'}[spec.format]).read(evidence / spec.coverage, texts)
        measurements = collect(coverage, sources, exclude=spec.exclude)
    finally:
        os.chdir(previous)
    (evidence / 'measurements.json').write_text(json.dumps(measurements, indent=2), encoding='utf-8')
    result = calculate(measurements)
    print(json.dumps(result, indent=2, allow_nan=False))
    return 1 if result['findings'] else 0


def main():
    try:
        if len(sys.argv) > 1 and sys.argv[1] in LANGUAGES:
            return language_result(sys.argv[1], sys.argv[2:])
        if len(sys.argv) > 1 and sys.argv[1] == 'collect':
            return collect_main(sys.argv[2:])
        if len(sys.argv) != 2:
            raise ValueError('Usage: python crap.py CONFIG.json')
        return config_result(sys.argv[1])
    except (OSError, ValueError, ImportError) as error:
        print(f'CRAP: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
