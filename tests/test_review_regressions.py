"""Regressions from the PR #34 review, each driven through a public entry point."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/workflow/scripts'))
import duplication
import mutation
import test_incremental_mutation as incremental_tests
import test_native_tools as native_tests


class Fixtures(unittest.TestCase):
    def fixture(self, case):
        test = case()
        test.setUp()
        self.addCleanup(test.doCleanups)
        return test


class ReviewRegressionTests(Fixtures):
    def test_deleting_an_imported_module_forces_a_full_run(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / 'a.py').write_text('def a(): return 1\n')
            (project / 'b.py').write_text('def b(): return 2\n')
            report = {'baselinePassed': True, 'mutants': [{'id': 'a1', 'file': 'a.py', 'status': 'killed'},
                                                          {'id': 'b1', 'file': 'b.py', 'status': 'killed'}]}
            # The engine imports b, so deleting b breaks the baseline that reuse would skip.
            command = [sys.executable, '-c', 'import b, os; from pathlib import Path; '
                       f'Path(os.environ["WORKFLOW_REPORT_FILE"]).write_text({json.dumps(report)!r})']

            def run(*options):
                with redirect_stdout(io.StringIO()) as out, tempfile.TemporaryFile(mode='w+') as err, \
                        redirect_stderr(err):
                    code = mutation.main(['--json', 'python', directory, *options, '--', *command])
                return code, json.loads(out.getvalue()) if out.getvalue() else None
            code, first = run()
            self.assertEqual(code, 0)
            (project / 'b.py').unlink()
            code, result = run('--previous-evidence', str(Path(first['reportPath']).parent))
            self.assertEqual((code, result), (2, None))

    def test_same_named_methods_in_two_classes_are_counted_once(self):
        test = self.fixture(incremental_tests.IncrementalMutationTests)
        source = ('class A:\n    def size(self, x):\n        return x + 1\n\n'
                  'class B:\n    def size(self, x):\n        return x * 2\n')
        mutants = {'calc.xǁAǁsize__mutmut_1': ['src/calc.py', 1], 'calc.xǁBǁsize__mutmut_1': ['src/calc.py', 1]}
        test.write('src/calc.py', source)
        first = test.python(mutants=mutants, expected=0)
        test.write('src/calc.py', source.replace('x + 1', '1 + x'))
        second = test.python(test.evidence(first), mutants, expected=0)
        self.assertEqual(second['counts']['killed'], 2)
        self.assertEqual(sorted((m['id'], m['reused']) for m in second['outcomes']),
                         [('calc.xǁAǁsize__mutmut_1', False), ('calc.xǁBǁsize__mutmut_1', False)])

    def test_outcomes_of_a_removed_function_are_dropped(self):
        test = self.fixture(incremental_tests.IncrementalMutationTests)
        test.write('src/calc.py', incremental_tests.CALC)
        mutants = {key: [file, 1] for key, (file, _) in incremental_tests.MUTANTS.items() if file == 'src/calc.py'}
        first = test.python(mutants=mutants, expected=0)
        test.write('src/calc.py', incremental_tests.CALC.replace('def double(x):\n    return x * 2\n', ''))
        del mutants['calc.x_double__mutmut_1'], mutants['calc.x_double__mutmut_2']
        second = test.python(test.evidence(first), mutants, expected=0)
        self.assertEqual(sorted(o['id'] for o in second['outcomes']),
                         ['calc.x_choose__mutmut_1', 'calc.xǁBoxǁsize__mutmut_1'])

    def test_valid_jsx_is_parsed(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'a.jsx').write_text('function Component() { return <div />; }\n')
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as err:
                self.assertEqual(duplication.main(['js', directory, 'a.jsx']), 0, err.getvalue())


@unittest.skipIf(os.name == 'nt', 'POSIX executable and symlink fixtures')
class NativeReviewRegressionTests(Fixtures):
    def test_project_local_stryker_is_reused_across_overlays(self):
        test = self.fixture(native_tests.NativeToolTests)
        project = test.project('js')
        test.fake(project / 'node_modules/.bin/stryker')
        code, error, first, _ = test.mutate('js', project, native_tests.STRYKER)
        self.assertEqual(code, 0, error)
        code, error, _, result = test.mutate('js', project, native_tests.STRYKER, '--previous-evidence', str(first))
        self.assertEqual((code, result['reusedCount']), (0, 1), error)

    def test_a_rerun_mutant_replaces_only_the_outcome_from_its_own_file(self):
        test = self.fixture(native_tests.NativeToolTests)
        project = test.project('js')
        both = {'files': {name: {'mutants': [{'id': '1', 'status': 'Killed'}]} for name in ('a.js', 'b.js')}}
        code, error, first, _ = test.mutate('js', project, both)
        self.assertEqual(code, 0, error)
        (project / 'a.js').write_text((project / 'a.js').read_text() + '\n')
        rerun = {'files': {'a.js': {'mutants': [{'id': '1', 'status': 'Killed'}]}}}
        code, error, _, result = test.mutate('js', project, rerun, '--previous-evidence', str(first))
        self.assertEqual(code, 0, error)
        self.assertEqual(sorted((o['file'], o['reused']) for o in result['outcomes']), [('a.js', False), ('b.js', True)])

    def test_a_longer_version_does_not_satisfy_the_pin(self):
        test = self.fixture(native_tests.NativeToolTests)
        project = test.project('js')
        test.fake(test.bin / 'stryker')
        (test.bin / 'stryker.version').write_text('stryker 10.1.10')
        code, error, _, _ = test.mutate('js', project, native_tests.STRYKER, '--no-install')
        self.assertEqual(code, 2)
        self.assertIn('Missing pinned stryker 10.1.1', error)

    @unittest.skipUnless(shutil.which('node'), 'Node.js is not installed')
    def test_overlay_keeps_npm_executables_resolving_relative_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            package = project / 'node_modules/example'
            (package / 'bin').mkdir(parents=True)
            (package / 'lib').mkdir()
            (package / 'lib/main.js').write_text('module.exports = 42;\n')
            (package / 'bin/runner.js').write_text('if (require("../lib/main.js") !== 42) process.exit(1);\n')
            (project / 'node_modules/.bin').mkdir()
            (project / 'node_modules/.bin/runner').symlink_to('../example/bin/runner.js')
            command = [sys.executable, '-c', 'import os, subprocess; from pathlib import Path; '
                       'subprocess.run(["node", "node_modules/.bin/runner"], check=True); '
                       'Path(os.environ["WORKFLOW_REPORT_FILE"]).write_text('
                       '\'{"baselinePassed": true, "mutants": [{"status": "killed"}]}\')']
            with redirect_stdout(io.StringIO()), tempfile.TemporaryFile(mode='w+') as err, redirect_stderr(err):
                code = mutation.main(['python', directory, '--overlay', '--', *command])
                err.seek(0)
                logs = err.read()
            self.assertEqual(code, 0, logs)
            # The copy's link points inside the copy, never back into the original project.
            self.assertTrue((project / 'node_modules/.bin/runner').is_symlink())


if __name__ == '__main__':
    unittest.main()
