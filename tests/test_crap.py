from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/workflow/scripts'
sys.path.insert(0, str(SCRIPTS))
from crap import calculate, main

MEASURED = dict(file='src/a.ts', name='choose', line=1, complexity=4,
                covered=1, total=2, coverageKind='line')
COVERAGE = {'line': {'covered': 95, 'total': 100}, 'branch': {'covered': 9, 'total': 10}}
INVALID = '^Invalid function measurement: require file, name, line, complexity, covered, total, coverageKind$'


def report(*functions, **coverage):
    return {'functions': list(functions), 'coverage': {**COVERAGE, **coverage}}


class CrapTests(unittest.TestCase):
    def test_formula_and_crap_standard(self):
        result = calculate(report(MEASURED, {**MEASURED, 'name': 'uncovered', 'covered': 0}))
        self.assertEqual([f['crap'] for f in result['functions']], [20, 6])
        self.assertEqual([f['coverage'] for f in result['functions']], [0, 0.5])
        self.assertEqual([f['exceedsThreshold'] for f in result['functions']], [True, False])
        self.assertEqual(result['findings'], 1)
        self.assertEqual(result['standard'], {'maxCrap': 6, 'minCoveragePercent': {'line': 95, 'branch': 90}})
        self.assertEqual(calculate(report({**MEASURED, 'covered': 2}))['findings'], 0)
        self.assertEqual(calculate(report({**MEASURED, 'complexity': 6, 'covered': 2}))['findings'], 0)
        self.assertEqual(calculate(report({**MEASURED, 'complexity': 7, 'covered': 2}))['findings'], 1)
        self.assertEqual(calculate(report({**MEASURED, 'complexity': 6, 'covered': 99, 'total': 100}))['findings'], 1)
        self.assertEqual(calculate(report({**MEASURED, 'complexity': 5, 'covered': 19, 'total': 20}))['findings'], 0)

    def test_aggregate_coverage_standard(self):
        covered = {**MEASURED, 'covered': 2}
        passing = calculate(report(covered))['coverage']
        self.assertEqual(passing, {'line': {'covered': 95, 'total': 100, 'coverage': 0.95, 'meetsStandard': True},
                                   'branch': {'covered': 9, 'total': 10, 'coverage': 0.9, 'meetsStandard': True}})
        for kind, counts in [('line', {'covered': 94, 'total': 100}), ('line', {'covered': 18, 'total': 19}),
                             ('branch', {'covered': 89, 'total': 100})]:
            with self.subTest(kind=kind, counts=counts):
                result = calculate(report(covered, **{kind: counts}))
                self.assertFalse(result['coverage'][kind]['meetsStandard'])
                self.assertEqual(result['findings'], 1)
        self.assertEqual(calculate(report(MEASURED, line={'covered': 0, 'total': 1}))['findings'], 1)

    def test_crap_threshold_uses_exact_counts(self):
        for total in (1000000, 2**53 - 1):
            for covered, exceeds in ((total - 1, True), (total, False)):
                with self.subTest(total=total, covered=covered):
                    measured = {**MEASURED, 'complexity': 6, 'covered': covered, 'total': total}
                    self.assertEqual(calculate(report(measured))['functions'][0]['exceedsThreshold'], exceeds)
        # Complexity 4 reaches exactly 6 at half coverage; one count either way matters.
        for covered, exceeds in ((499999, True), (500000, False), (500001, False)):
            measured = {**MEASURED, 'covered': covered, 'total': 1000000}
            self.assertEqual(calculate(report(measured))['functions'][0]['exceedsThreshold'], exceeds)

    def test_accepts_boundary_values_and_every_coverage_kind(self):
        largest = 2**53 - 1
        for kind in ['line', 'branch', 'statement', 'basis-path']:
            measured = {**MEASURED, 'line': largest, 'coverageKind': kind}
            with self.subTest(kind=kind):
                self.assertEqual(calculate(report(measured))['functions'][0]['line'], largest)
        counts = {'covered': largest, 'total': largest}
        self.assertTrue(calculate(report(MEASURED, line=counts))['coverage']['line']['meetsStandard'])

    def test_invalid_measurements(self):
        changes = [dict(complexity=-1), dict(complexity=0), dict(complexity='4'), dict(covered=3), dict(covered=-1),
                   dict(total=0), dict(covered=0, total=0), dict(line=0), dict(coverageKind=None), dict(file=''),
                   dict(total=1.5), dict(covered=True), dict(complexity=2**53)]
        for functions in [[None], *[[{**MEASURED, **c}] for c in changes]]:
            with self.subTest(functions=functions), self.assertRaisesRegex(ValueError, INVALID):
                calculate(report(*functions))
        for measured in [{'functions': []}, {}, []]:
            with self.subTest(report=measured), self.assertRaisesRegex(ValueError, '^No function measurements$'):
                calculate(measured)
        with self.assertRaisesRegex(ValueError, r"^Duplicate function measurement: \('src/a.ts', 1, 'choose'\)$"):
            calculate(report(MEASURED, MEASURED))

    def test_invalid_aggregate_coverage(self):
        for coverage in [None, [], 'line']:
            with self.subTest(coverage=coverage), self.assertRaisesRegex(
                    ValueError, '^Missing aggregate coverage: require line and branch counts$'):
                calculate({'functions': [MEASURED], 'coverage': coverage})
        invalid = [None, [], {}, {'covered': 1}, {'total': 1}, {'covered': 0, 'total': 0},
                   {'covered': 2, 'total': 1}, {'covered': -1, 'total': 1}, {'covered': True, 'total': 1},
                   {'covered': 1, 'total': 1.0}, {'covered': 1, 'total': 2**53}]
        for kind in ['line', 'branch']:
            for counts in invalid:
                with self.subTest(kind=kind, counts=counts), self.assertRaisesRegex(
                        ValueError, f'^Invalid {kind} coverage: require covered and total counts, '
                                    '1 <= total, covered <= total$'):
                    calculate(report(MEASURED, **{kind: counts}))
        coverage = {'line': COVERAGE['line']}
        with self.assertRaisesRegex(ValueError, '^Invalid branch coverage'):
            calculate({'functions': [MEASURED], 'coverage': coverage})

    def run_main(self, measured, **extra):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code = f"from pathlib import Path; Path('report.json').write_text({json.dumps(measured)!r})"
            config = dict(cwd='.', command=[sys.executable, '-c', code], report='report.json', **extra)
            path = root / 'config.json'
            path.write_text(json.dumps(config))
            # The runner hands tool output to the stderr file descriptor, so stderr must be a real file.
            with tempfile.TemporaryFile('w+') as stderr, redirect_stderr(stderr), \
                    redirect_stdout(io.StringIO()) as stdout, \
                    mock.patch.object(sys, 'argv', ['crap.py', str(path)]):
                exit_code = main()
                stderr.seek(0)
                return exit_code, stdout.getvalue(), stderr.read()

    def test_cli_exit_codes_and_json_output(self):
        for measured, expected, crap in [(report({**MEASURED, 'covered': 2}), 0, 4), (report({**MEASURED, 'covered': 0}), 1, 20)]:
            with self.subTest(expected=expected):
                exit_code, stdout, stderr = self.run_main(measured)
                self.assertEqual(exit_code, expected, stderr)
                self.assertEqual(json.loads(stdout)['functions'][0]['crap'], crap)
        self.assertEqual(self.run_main(report({**MEASURED, 'covered': 2}), maxCrap=30),
                         (2, '', 'CRAP: maxCrap is not configurable; the skill standard is CRAP <= 6\n'))
        self.assertEqual(self.run_main({'functions': [MEASURED]}),
                         (2, '', 'CRAP: Missing aggregate coverage: require line and branch counts\n'))
        with redirect_stderr(io.StringIO()) as stderr, mock.patch.object(sys, 'argv', ['crap.py']):
            self.assertEqual(main(), 2)
        self.assertEqual(stderr.getvalue(), 'CRAP: Usage: python crap.py CONFIG.json\n')

    def test_script_entrypoint(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / 'crap.py')], capture_output=True, text=True)
        self.assertEqual((result.returncode, result.stderr), (2, 'CRAP: Usage: python crap.py CONFIG.json\n'))

    def test_forbidden_option_is_rejected_before_command_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = [sys.executable, '-c', "from pathlib import Path; Path('started').touch()"]
            path = root / 'config.json'
            path.write_text(json.dumps(dict(cwd='.', command=command, report='report.json', maxCrap=6)))
            with mock.patch.object(sys, 'argv', ['crap.py', str(path)]), redirect_stderr(io.StringIO()) as stderr:
                self.assertEqual(main(), 2)
            self.assertIn('maxCrap is not configurable', stderr.getvalue())
            self.assertFalse((root / 'started').exists())


if __name__ == '__main__':
    unittest.main()
