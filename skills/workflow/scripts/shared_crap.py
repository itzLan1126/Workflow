"""Join complexity and coverage, then apply the fixed CRAP standard."""

from fractions import Fraction
from pathlib import Path


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


def summarize(counts):
    return {"covered": sum(count > 0 for count in counts), "total": len(counts)}


def analyze(source):
    import lizard
    from lizard_languages import get_reader_for

    if get_reader_for(str(source)) is None:
        raise ValueError(f"Unsupported source: {source}")
    code = source.read_text(encoding="utf-8")
    functions = sorted(lizard.analyze_file.analyze_source_code(
        str(source), code).function_list, key=lambda function: function.start_line)
    if not functions:
        raise ValueError(f"No functions found: {source}")
    return code, functions


def measure_function(source, function, hits):
    counts = [count for line, count in hits.items()
              if function.start_line <= line <= function.end_line]
    if not counts:
        raise ValueError(f"Missing line coverage: {source}:{function.name}")
    return {"file": str(source), "name": function.name, "line": function.start_line,
            "complexity": function.cyclomatic_complexity,
            "covered": sum(count > 0 for count in counts),
            "total": len(counts), "coverageKind": "line"}


def measure_functions(source, functions, hits):
    result, previous_end = [], 0
    for function in functions:
        # ponytail: reject nested/shared-line ranges; use a language-aware adapter if needed.
        if function.start_line <= previous_end:
            raise ValueError(f"Overlapping function ranges: {source}:{function.start_line}")
        previous_end = function.end_line
        result.append(measure_function(source, function, hits))
    return result


def collect(coverage, sources):
    result, seen, lines, branches = [], set(), [], []
    for argument in sources:
        source = Path(argument).resolve(strict=True)
        if source in seen:
            raise ValueError(f"Duplicate source: {source}")
        seen.add(source)
        code, functions = analyze(source)
        if source not in coverage:
            raise ValueError(f"Missing exact-path LCOV coverage: {source}")
        hits = coverage[source]
        lines.extend(hits["lines"].values())
        branches.extend(hits["branches"].values())
        result.extend(measure_functions(source, functions, hits["lines"]))
    return {"functions": result, "coverage": {"line": summarize(lines), "branch": summarize(branches)}}


