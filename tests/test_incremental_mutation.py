"""Incremental mutation through the entry point: sealed evidence, reuse, invalidation and scoping."""
from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/workflow/scripts'))
import mutation

# A stand-in for mutmut 3's command line and mutant lookup. Like mutmut, it records every generated
# mutant in .meta files but leaves unselected ones without an exit code. Every other mutmut module,
# including the trampoline that mutated copies of these scripts import, comes from the real package.
FAKE_MUTMUT = {
    '__init__.py': '''import os
__path__.append(os.environ['REAL_MUTMUT'])
exec(compile(open(os.path.join(os.environ['REAL_MUTMUT'], '__init__.py')).read(), __file__, 'exec'))
''',
    '__main__.py': '''import fnmatch, json, os, pathlib, sys
status_by_exit_code = {}
if __name__ == '__main__':
    mutants = json.loads(os.environ['FAKE_MUTANTS'])
    patterns = sys.argv[2:]
    with open(os.environ['FAKE_MUTMUT_LOG'], 'a', encoding='utf-8') as log:
        log.write(json.dumps(patterns) + '\\n')
    chosen = [key for key in mutants if not patterns or any(fnmatch.fnmatch(key, p) for p in patterns)]
    if not chosen:
        raise SystemExit('Filtered for specific mutants, but nothing matches')
    by_file = {}
    for key, (file, code) in mutants.items():
        by_file.setdefault(file, {})[key] = code if key in chosen else None
    for file, codes in by_file.items():
        meta = pathlib.Path('mutants', file + '.meta')
        meta.parent.mkdir(parents=True, exist_ok=True)
        meta.write_text(json.dumps({'exit_code_by_key': codes}))
''',
    'mutation/__init__.py': "import os\n__path__.append(os.path.join(os.environ['REAL_MUTMUT'], 'mutation'))\n",
    'mutation/diff_apply.py': '''import json, os, pathlib, types
def find_mutant(key):
    return types.SimpleNamespace(path=pathlib.Path(json.loads(os.environ['FAKE_MUTANTS'])[key][0]))
def get_diff_for_mutant(key):
    return '--- a\\n+++ b\\n@@ -1 +1 @@\\n-' + key + '\\n+changed'
''',
}
CALC = ('def choose(x):\n    if x:\n        return 1\n    return 0\n\n\n'
        'def double(x):\n    return x * 2\n\n\n'
        'class Box:\n    def size(self, x):\n        return x + 1\n')
MUTANTS = {'calc.x_choose__mutmut_1': ['src/calc.py', 1], 'calc.x_double__mutmut_1': ['src/calc.py', 1],
           'calc.x_double__mutmut_2': ['src/calc.py', 0], 'calc.xǁBoxǁsize__mutmut_1': ['src/calc.py', 1],
           'other.x_other__mutmut_1': ['src/other.py', 0]}
CHOOSE, DOUBLE, SIZE = 'src/calc.py:choose:1', 'src/calc.py:double:7', 'src/calc.py:size:12'
OTHER = 'src/other.py:other:1'
DOUBLE_PATTERNS = ['calc.x_double__mutmut_*', 'calc.xǁ*ǁdouble__mutmut_*']
SIZE_PATTERNS = ['calc.x_size__mutmut_*', 'calc.xǁ*ǁsize__mutmut_*']
OTHER_PATTERNS = ['other.x_other__mutmut_*', 'other.xǁ*ǁother__mutmut_*']
INVALIDATED = 'full run: tests, engine, configuration or language module changed'


class IncrementalMutationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.project = self.root / 'project'
        self.calls = self.root / 'calls.jsonl'

    def write(self, name, text):
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def run_check(self, args, env=()):
        with patch.dict(os.environ, dict(env)), redirect_stdout(io.StringIO()) as out, \
                tempfile.TemporaryFile(mode='w+') as err, redirect_stderr(err):
            code = mutation.main(['--json', *args])
            err.seek(0)
            error = err.read()
        result = json.loads(out.getvalue()) if out.getvalue() else None
        return code, result, error

    def evidence(self, result):
        return Path(result['reportPath']).resolve().parent

    def python(self, previous=None, mutants=MUTANTS, expected=1):
        fake = self.root / 'fake'
        for name, text in FAKE_MUTMUT.items():
            (fake / 'mutmut' / name).parent.mkdir(parents=True, exist_ok=True)
            (fake / 'mutmut' / name).write_text(text, encoding='utf-8')
        real = importlib.util.find_spec('mutmut').submodule_search_locations[0]
        env = {'PYTHONPATH': str(fake), 'REAL_MUTMUT': real, 'FAKE_MUTANTS': json.dumps(mutants),
               'FAKE_MUTMUT_LOG': str(self.calls)}
        options = ['--previous-evidence', str(previous)] if previous else []
        code, result, error = self.run_check(['python', str(self.project), '--overlay', *options], env)
        self.assertEqual(code, expected, error)
        return result

    def patterns(self):
        return [json.loads(line) for line in self.calls.read_text().splitlines()]

    def test_python_reuses_unchanged_functions_and_reruns_edited_and_actionable_ones(self):
        self.write('src/calc.py', CALC)
        self.write('src/other.py', 'def other(x):\n    return x - 1\n')
        self.write('tests/test_calc.py', 'from calc import choose\n')
        self.write('pyproject.toml', '[tool.mutmut]\nsource_paths = ["src/"]\n')
        first = self.python()
        self.assertEqual((first['counts']['killed'], first['counts']['survived'], first['reusedCount']), (3, 2, 0))
        self.assertNotIn('incrementalScope', first)
        config = json.loads((self.evidence(first) / 'config.json').read_bytes())
        self.assertEqual([tool['name'] for tool in config['tools']], ['lizard', 'mutmut'])
        snapshot = json.loads((self.evidence(first) / 'snapshot.json').read_bytes())
        self.assertEqual(snapshot['engine'], {'format': 'normalized', 'command': ['normalized'], 'tools': config['tools']})
        expected_source = ['def double(x):', '    return x * 2']
        self.assertEqual(snapshot['functions'][DOUBLE], hashlib.sha256(repr(expected_source).encode()).hexdigest())
        second = self.python(self.evidence(first))
        self.assertEqual(self.patterns()[-1], DOUBLE_PATTERNS + OTHER_PATTERNS)
        self.assertEqual(second['incrementalScope'], {'files': ['src/calc.py', 'src/other.py'],
                                                      'functions': [DOUBLE, OTHER], 'fallback': None})
        self.assertEqual(sorted((o['id'], o['reused']) for o in second['outcomes']), [
            ('calc.x_choose__mutmut_1', True), ('calc.x_double__mutmut_1', False),
            ('calc.x_double__mutmut_2', False), ('calc.xǁBoxǁsize__mutmut_1', True), ('other.x_other__mutmut_1', False)])
        self.assertEqual((second['counts']['killed'], second['counts']['survived'], second['exitCode']), (3, 2, 1))
        self.assertEqual(sorted(m['id'] for m in second['mutants']), ['calc.x_double__mutmut_2', 'other.x_other__mutmut_1'])
        self.assertEqual(json.loads((self.evidence(second) / 'result.json').read_bytes()), second)
        saved = json.loads((self.evidence(second) / 'outcomes.json').read_bytes())
        self.assertEqual(sorted((o['functionKey'], o['reused']) for o in saved),
                         [(CHOOSE, True), (DOUBLE, False), (DOUBLE, False), (SIZE, True), (OTHER, False)])
        self.write('src/calc.py', CALC.replace('x + 1', '1 + x'))
        third = self.python(self.evidence(second))
        self.assertEqual(self.patterns()[-1], DOUBLE_PATTERNS + SIZE_PATTERNS + OTHER_PATTERNS)
        self.assertEqual(third['reusedCount'], 1)
        # Line 6 is blank between functions: replacing it edits the file but no function.
        lines = CALC.replace('x + 1', '1 + x').splitlines(keepends=True)
        lines[5] = 'LIMIT = 3\n'
        self.write('src/calc.py', ''.join(lines))
        fourth = self.python(self.evidence(third))
        self.assertEqual(fourth['incrementalScope']['functions'], [CHOOSE, DOUBLE, SIZE, OTHER])
        self.assertEqual(fourth['reusedCount'], 0)
        evidence = self.evidence(fourth)
        for name, text in [('tests/test_calc.py', 'from calc import double\n'),
                           ('pyproject.toml', '[tool.mutmut]\nsource_paths = ["src/"]\n# changed\n')]:
            with self.subTest(changed=name):
                self.write(name, text)
                result = self.python(evidence)
                self.assertEqual(self.patterns()[-1], [])
                self.assertEqual(result['incrementalScope'], {'files': None, 'functions': None, 'fallback': INVALIDATED})
                self.assertEqual(result['reusedCount'], 0)
                evidence = self.evidence(result)

    def test_python_top_level_edit_invalidates_other_functions_even_when_a_function_changes_too(self):
        self.write('src/calc.py', 'LIMIT = 1\n' + CALC)
        mutants = {key: [file, 1] for key, (file, _) in MUTANTS.items() if file == 'src/calc.py'}
        first = self.python(mutants=mutants, expected=0)
        self.write('src/calc.py', 'LIMIT = 2\n' + CALC.replace('x + 1', '1 + x'))
        second = self.python(self.evidence(first), mutants, expected=0)
        self.assertEqual(second['reusedCount'], 0)
        self.assertEqual(second['counts']['killed'], 4)

    def test_python_outcomes_without_a_known_function_fall_back_to_whole_files(self):
        self.write('src/calc.py', CALC)
        mutants = {**MUTANTS, 'calc.x_ghost__mutmut_1': ['src/calc.py', 1]}
        del mutants['other.x_other__mutmut_1']
        first = self.python(mutants=mutants)
        self.assertNotIn('functionKey', [k for o in first['outcomes'] if o['id'] == 'calc.x_ghost__mutmut_1' for k in o])
        second = self.python(self.evidence(first), mutants=mutants)
        self.assertEqual(self.patterns()[-1], ['calc.*'])
        self.assertEqual(second['incrementalScope'], {'files': ['src/calc.py'], 'functions': None, 'fallback': 'full file'})

    def custom(self, previous=None, report=None, marker='a', status='killed', files=('a.py',)):
        report = report or {'baselinePassed': True, 'mutants': [
            {'id': f'{file}-1', 'file': file, 'status': status} for file in files]}
        # The command line stays identical across runs; the report comes from the environment.
        writer = ('import os, sys; from pathlib import Path; '
                  f'open({str(self.calls)!r}, "a").write(sys.argv[1] + "\\n"); '
                  'Path(os.environ["WORKFLOW_REPORT_FILE"]).write_text(os.environ["FAKE_REPORT"])')
        options = ['--previous-evidence', str(previous)] if previous else []
        return self.run_check(['python', str(self.project), *options, '--', sys.executable, '-c', writer, marker],
                              {'FAKE_REPORT': json.dumps(report)})

    def engine_runs(self):
        return len(self.calls.read_text().splitlines()) if self.calls.exists() else 0

    def test_replaced_commands_reuse_only_when_nothing_changed_and_name_every_fallback(self):
        for name in ('a.py', 'b.py'):
            self.write(name, 'def f(x):\n    return x\n')
        code, first, error = self.custom(files=('a.py', 'b.py'))
        self.assertEqual(code, 0, error)
        code, second, _ = self.custom(self.evidence(first), files=('a.py', 'b.py'))
        self.assertEqual((code, self.engine_runs(), second['reusedCount']), (0, 1, 2))
        self.assertEqual(json.loads(Path(second['reportPath']).read_bytes()),
                         {'baselinePassed': True, 'mutants': second['outcomes']})
        self.assertEqual(second['incrementalScope'], {'files': [], 'functions': None, 'fallback': 'full file'})
        self.assertEqual({k: second[k] for k in ('format', 'assessed', 'exitCode', 'toolExitCode', 'mutants')},
                         {'format': 'normalized', 'assessed': 2, 'exitCode': 0, 'toolExitCode': 0, 'mutants': []})
        self.assertEqual(json.loads(Path(second['reportPath']).read_bytes())['baselinePassed'], True)
        (self.project / 'b.py').unlink()
        code, third, _ = self.custom(self.evidence(second))
        self.assertEqual((code, self.engine_runs(), third['reusedCount']), (0, 1, 1))
        evidence = self.evidence(third)
        for name, text in [('README.md', 'notes'), ('node_modules/x/index.js', 'x'), ('docs/notes.txt', 'n')]:
            with self.subTest(ignored=name):
                self.write(name, text)
                code, result, _ = self.custom(evidence)
                self.assertEqual((code, self.engine_runs(), result['reusedCount']), (0, 1, 1))
        cases = [('a.py', 'def f(x):\n    return x + 0\n', 'full run: replaced command cannot be scoped'),
                 ('pkg/tests/helper.py', 'x = 1\n', INVALIDATED), ('test_a.py', 'x = 1\n', INVALIDATED),
                 ('web/a.spec.js', 'x\n', INVALIDATED), ('Sources/ATests.swift', 'x\n', INVALIDATED),
                 ('requirements-dev.txt', 'x\n', INVALIDATED), ('setup.cfg', '[x]\n', INVALIDATED)]
        for name, text, fallback in cases:
            with self.subTest(changed=name):
                self.write(name, text)
                runs = self.engine_runs()
                code, result, error = self.custom(evidence)
                self.assertEqual(code, 0, error)
                self.assertEqual(self.engine_runs(), runs + 1)
                self.assertEqual(result['incrementalScope'], {'files': None, 'functions': None, 'fallback': fallback})
                evidence = self.evidence(result)
        code, result, _ = self.custom(evidence, marker='b')
        self.assertEqual(result['incrementalScope']['fallback'], INVALIDATED)
        # Options after --previous-evidence DIRECTORY still apply.
        writer = 'import os; open(os.environ["WORKFLOW_REPORT_FILE"], "w").write(os.environ["FAKE_REPORT"])'
        report = {'baselinePassed': True, 'mutants': [{'id': 'a.py-1', 'file': 'a.py', 'status': 'killed'}]}
        code, result, error = self.run_check(['python', str(self.project), '--previous-evidence', str(evidence),
                                              '--timeout-ms', '9000', '--', sys.executable, '-c', writer],
                                             {'FAKE_REPORT': json.dumps(report)})
        self.assertEqual(code, 0, error)
        self.assertEqual(json.loads((self.evidence(result) / 'config.json').read_bytes())['timeoutMs'], 9000)

    def test_actionable_and_unbound_outcomes_are_always_run_again(self):
        self.write('a.py', 'def f(x):\n    return x\n')
        code, first, _ = self.custom(status='timeout')
        self.assertEqual((code, first['counts']['timeout'], first['counts']['killed']), (1, 1, 0))
        code, second, _ = self.custom(self.evidence(first), status='timeout')
        self.assertEqual((code, self.engine_runs(), second['reusedCount']), (1, 2, 0))
        self.assertEqual(second['incrementalScope']['fallback'], 'full run: replaced command cannot be scoped')
        code, third, _ = self.custom(report={'baselinePassed': True, 'mutants': [{'id': 'x', 'status': 'killed'}]})
        code, fourth, _ = self.custom(self.evidence(third))
        self.assertEqual((self.engine_runs(), fourth['reusedCount']), (4, 0))
        self.assertEqual(fourth['incrementalScope']['fallback'], 'full run: previous outcomes are not bound to source files')

    def test_missing_damaged_or_inconsistent_previous_evidence_never_starts_the_engine(self):
        self.write('a.py', 'def f(x):\n    return x\n')
        code, first, _ = self.custom()
        evidence = self.evidence(first)
        snapshot, outcomes = (evidence / 'snapshot.json').read_bytes(), (evidence / 'outcomes.json').read_bytes()
        edited = json.loads(snapshot)
        edited['files']['a.py'] = '0' * 64
        cases = [('outcomes.json', outcomes[:-1] + b',{"id":"x","status":"killed"}]', ': seal mismatch\n'),
                 ('snapshot.json', json.dumps(edited).encode(), ': seal mismatch\n'),
                 ('snapshot.json', snapshot.replace(b'"sha256"', b'"seal"'), "'sha256'"),
                 ('snapshot.json', b'[]', "'str' object cannot be interpreted as an integer"),
                 ('outcomes.json', None, 'No such file or directory')]
        for index, (name, data, reason) in enumerate(cases):
            with self.subTest(name=name, reason=reason):
                damaged = self.root / f'damaged-{index}'
                shutil.copytree(evidence, damaged)
                if data is None:
                    (damaged / name).unlink()
                else:
                    (damaged / name).write_bytes(data)
                code, result, error = self.custom(damaged)
                self.assertEqual((code, result, self.engine_runs()), (2, None, 1))
                self.assertTrue(error.startswith(f'mutation: Damaged previous mutation evidence in {damaged}: '), error)
                self.assertIn(reason, error)
        code, result, error = self.run_check(['python', str(self.project), '--previous-evidence'])
        self.assertEqual((code, error), (2, 'mutation: Require --previous-evidence DIRECTORY\n'))


if __name__ == '__main__':
    unittest.main()
