#!/usr/bin/env python3
"""Compute CRAP scores and gate them, with aggregate coverage, against the skill's standard."""

import json
from fractions import Fraction
import sys

from run_report import run_report

# The skill's fixed standard: every function's CRAP <= 6, aggregate line coverage >= 95%,
# and aggregate branch coverage >= 90%. Coverage is compared exactly in integers.
MAX_CRAP = 6
MIN_COVERAGE_PERCENT = {'line': 95, 'branch': 90}
STANDARD = {'maxCrap': MAX_CRAP, 'minCoveragePercent': MIN_COVERAGE_PERCENT}


def is_count(value):
    return type(value) is int and 0 <= value <= 2**53 - 1


def is_text(value):
    return isinstance(value, str) and value.strip() != ''


def has_fields(f):
    return (all(is_text(f.get(key)) for key in ('file', 'name'))
            and all(is_count(f.get(key)) for key in ('line', 'complexity', 'total', 'covered')))


def is_measurement(f):
    return (isinstance(f, dict) and has_fields(f)
            and min(f['line'], f['complexity'], f['total']) >= 1
            and f['covered'] <= f['total']
            and f.get('coverageKind') in ('line', 'branch', 'statement', 'basis-path'))


def score_functions(measurements):
    if not isinstance(measurements, list) or not measurements:
        raise ValueError('No function measurements')
    seen, functions = set(), []
    for f in measurements:
        if not is_measurement(f):
            raise ValueError('Invalid function measurement: require file, name, line, complexity, covered, total, coverageKind')
        identity = (f['file'], f['line'], f['name'])
        if identity in seen:
            raise ValueError(f'Duplicate function measurement: {identity}')
        seen.add(identity)
        coverage = Fraction(f['covered'], f['total'])
        crap = f['complexity'] ** 2 * (1 - coverage) ** 3 + f['complexity']
        functions.append({**f, 'coverage': float(coverage), 'crap': float(crap),
                          'exceedsThreshold': crap > MAX_CRAP})
    functions.sort(key=lambda f: f['crap'], reverse=True)
    return functions


def gate_coverage(kind, counts):
    if (not isinstance(counts, dict) or not is_count(counts.get('covered'))
            or not is_count(counts.get('total')) or not counts['covered'] <= counts['total']
            or counts['total'] < 1):
        raise ValueError(f'Invalid {kind} coverage: require covered and total counts, 1 <= total, covered <= total')
    covered, total = counts['covered'], counts['total']
    return {'covered': covered, 'total': total, 'coverage': covered / total,
            'meetsStandard': covered * 100 >= MIN_COVERAGE_PERCENT[kind] * total}


def calculate(report):
    functions = score_functions(report.get('functions') if isinstance(report, dict) else None)
    measured = report.get('coverage')
    if not isinstance(measured, dict):
        raise ValueError('Missing aggregate coverage: require line and branch counts')
    coverage = {kind: gate_coverage(kind, measured.get(kind)) for kind in MIN_COVERAGE_PERCENT}
    findings = (sum(f['exceedsThreshold'] for f in functions)
                + sum(not c['meetsStandard'] for c in coverage.values()))
    return {'standard': STANDARD, 'functions': functions, 'coverage': coverage, 'findings': findings}


def main():
    try:
        if len(sys.argv) != 2:
            raise ValueError('Usage: python crap.py CONFIG.json')
        execution = run_report(sys.argv[1])
        if 'maxCrap' in execution['config']:
            raise ValueError('maxCrap is not configurable; the skill standard is CRAP <= 6')
        result = calculate(execution['report'])
        print(json.dumps(result, indent=2, allow_nan=False))
        return 1 if result['findings'] else 0
    except (OSError, ValueError) as error:
        print(f'CRAP: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
