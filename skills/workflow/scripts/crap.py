#!/usr/bin/env python3
"""Compute and gate CRAP scores from tool-measured function coverage."""

import json
import sys

from run_report import run_report


def calculate(report, max_crap):
    if type(max_crap) not in (int, float) or not 0 < max_crap <= sys.float_info.max:
        raise ValueError('maxCrap must be a positive number chosen for this project')
    measurements = report.get('functions') if isinstance(report, dict) else None
    if not isinstance(measurements, list) or not measurements:
        raise ValueError('No function measurements')
    seen, functions = set(), []
    for f in measurements:
        if (not isinstance(f, dict)
                or any(not isinstance(f.get(key), str) or not f[key].strip() for key in ('file', 'name'))
                or any(type(f.get(key)) is not int or not 0 <= f[key] <= 2**53 - 1
                       for key in ('line', 'complexity', 'total', 'covered'))
                or min(f['line'], f['complexity'], f['total']) < 1
                or f['covered'] > f['total']
                or f.get('coverageKind') not in ('line', 'branch', 'statement', 'basis-path')):
            raise ValueError('Invalid function measurement: require file, name, line, complexity, covered, total, coverageKind')
        identity = (f['file'], f['line'], f['name'])
        if identity in seen:
            raise ValueError(f'Duplicate function measurement: {identity}')
        seen.add(identity)
        coverage = f['covered'] / f['total']
        crap = f['complexity'] ** 2 * (1 - coverage) ** 3 + f['complexity']
        functions.append({**f, 'coverage': coverage, 'crap': crap, 'exceedsThreshold': crap > max_crap})
    functions.sort(key=lambda f: f['crap'], reverse=True)
    return {'maxCrap': max_crap, 'functions': functions,
            'findings': sum(f['exceedsThreshold'] for f in functions)}


def main():
    try:
        if len(sys.argv) != 2:
            raise ValueError('Usage: python crap.py CONFIG.json')
        execution = run_report(sys.argv[1])
        result = calculate(execution['report'], execution['config'].get('maxCrap'))
        print(json.dumps(result, indent=2, allow_nan=False))
        return 1 if result['findings'] else 0
    except (OSError, ValueError) as error:
        print(f'CRAP: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
