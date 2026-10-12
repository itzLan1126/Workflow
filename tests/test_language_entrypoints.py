"""Exercise language entry points with real subprocess-produced evidence."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/workflow/scripts'))
import crap
import mutation


class LanguageEntryPointsTests(unittest.TestCase):
    def test_python_coverage_and_mutation_entry_points(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            source = project / 'sample.py'
            source.write_text('def choose(x):\n    if x:\n        return 1\n    return 0\n')
            (project / 'test_sample.py').write_text('from sample import choose\ndef test_choose():\n    assert choose(True) == 1\n    assert choose(False) == 0\n')
            with redirect_stdout(io.StringIO()) as stdout, tempfile.TemporaryFile(mode="w+") as stderr, redirect_stderr(stderr):
                code = crap.dispatch(['python', str(project), 'sample.py'])
                stderr.seek(0)
                evidence = Path(stderr.readline().removeprefix('Evidence: ').strip())
            config = json.loads((evidence / 'config.json').read_text())
            self.assertEqual(config['cwd'], str(project.resolve()))
            self.assertEqual(config['sources'], ['sample.py'])
            self.assertEqual(config['timeoutMs'], 3600000)
            self.assertEqual(len(config['commands']), 3)
            measurements = json.loads((evidence / 'measurements.json').read_text())
            self.assertEqual(measurements['coverage']['line'], {'covered': 4, 'total': 4})
            self.assertEqual(code, 0, stdout.getvalue())
            self.assertEqual(json.loads(stdout.getvalue())['findings'], 0)
            engine = [sys.executable, '-c', "import json,pathlib; d=pathlib.Path(__import__('sys').argv[1]); (d/'reports/mutation').mkdir(parents=True); (d/'reports/mutation/mutation.json').write_text(json.dumps({'files':{'sample.js':{'mutants':[{'status':'Killed'}]}}}))", str(project)]
            with tempfile.TemporaryFile(mode="w+") as stderr, redirect_stderr(stderr):
                result = mutation.dispatch(['js', str(project), '--timeout-ms', '1234', '--', *engine])
            self.assertEqual(result['exitCode'], 0)
            self.assertTrue(Path(result['reportPath']).is_file())
            self.assertNotEqual(Path(result['reportPath']).parent, project / 'reports/mutation')
            config = json.loads((Path(result['reportPath']).parent / 'config.json').read_text())
            self.assertEqual(config['timeoutMs'], 1234)
            self.assertEqual(config['command'], engine)

    def test_review_needed_exit_and_literal_json_tool_argument(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            source = project / 'sample.js'
            source.write_text('function sample(x) {\n if (x) return 1;\n return 0;\n}\n')
            writer = "import pathlib,sys; pathlib.Path(sys.argv[1]).write_text('SF:'+sys.argv[2]+'\\nDA:2,0\\nDA:3,1\\nBRDA:2,0,0,0\\nBRDA:2,0,1,1\\nend_of_record\\n')"
            from unittest.mock import patch
            import lang_js
            from shared_languages import Crap
            spec = Crap('lcov', lambda p, e, a: [[sys.executable, '-c', writer, str(e / 'coverage.lcov'), str(source)]], 'coverage.lcov')
            with patch.object(lang_js, 'CRAP', spec), redirect_stdout(io.StringIO()), tempfile.TemporaryFile(mode='w+') as stderr, redirect_stderr(stderr):
                self.assertEqual(crap.dispatch(['js', directory, 'sample.js']), 1)
            engine = [sys.executable, '-c', "import pathlib,json,sys; assert sys.argv[1]=='--json'; pathlib.Path(sys.argv[2]).write_text(json.dumps({'baselinePassed':True,'mutants':[{'status':'killed'}]}))", '--json']
            import lang_python
            from shared_languages import Mutation
            spec = Mutation('normalized', lambda p, e, a: [*a, str(e / 'mutation.json')], lambda p, e: e / 'mutation.json')
            with patch.object(lang_python, 'MUTATION', spec), redirect_stdout(io.StringIO()) as stdout, tempfile.TemporaryFile(mode='w+') as stderr, redirect_stderr(stderr):
                self.assertEqual(mutation.main(['--json', 'python', directory, '--', *engine]), 0)
            self.assertEqual(json.loads(stdout.getvalue())['counts']['killed'], 1)
            with patch.object(lang_python, 'MUTATION', spec), redirect_stdout(io.StringIO()) as stdout, tempfile.TemporaryFile(mode='w+') as stderr, redirect_stderr(stderr):
                self.assertEqual(mutation.main(['python', directory, '--', *engine]), 0)
            self.assertIn('Summary: 1 killed', stdout.getvalue())

    def test_llvm_coverage_and_exclusion_through_entry_point(self):
        from shared_languages import Crap
        import lang_js
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            source = project / 'sample.swift'
            source.write_text('func a() {\n return 1\n}\nfunc test() { return 0 }\n')
            def commands(p, e, args):
                report = {'type': 'llvm.coverage.json.export', 'data': [{'files': [{'filename': str(source),
                          'segments': [[1, 1, 1, True, True, False], [3, 1, 0, False, False, False], [4, 1, 0, True, True, False]]}],
                          'functions': [{'name': 'a', 'filenames': [str(source)], 'regions': [[1, 1, 3, 1, 1, 0, 0, 0]]}]}]}
                return [[sys.executable, '-c', 'import pathlib,sys;pathlib.Path(sys.argv[1]).write_text(sys.argv[2])', str(e / 'coverage.json'), json.dumps(report)]]
            def exclude(path, code):
                self.assertEqual(path, source.resolve())
                self.assertEqual(code, source.read_text())
                return [(4, 4)]
            spec = Crap('llvm-json', commands, 'coverage.json', exclude)
            with patch.object(lang_js, 'CRAP', spec), redirect_stdout(io.StringIO()) as stdout, tempfile.TemporaryFile(mode='w+') as stderr, redirect_stderr(stderr):
                self.assertEqual(crap.dispatch(['js', directory, 'sample.swift']), 0)
            result = json.loads(stdout.getvalue())
            self.assertEqual(result['coverage']['region']['coverage'], 1)
            self.assertEqual([f['name'] for f in result['functions']], ['a'])

    def test_config_is_read_once_even_if_command_replaces_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / 'config.json'
            report = {'functions': [{'file': 'a.py', 'name': 'a', 'line': 1, 'complexity': 1,
                       'covered': 1, 'total': 1, 'coverageKind': 'line'}],
                      'coverage': {'line': {'covered': 1, 'total': 1}, 'branch': {'covered': 1, 'total': 1}}}
            # Detect a second read at the filesystem boundary without mocking the runner.
            from unittest.mock import patch
            read_text = Path.read_text
            reads = []
            def read(path, *args, **kwargs):
                if path == config:
                    reads.append(path)
                    if len(reads) > 1:
                        raise OSError('config read twice')
                return read_text(path, *args, **kwargs)
            command = [sys.executable, '-c', 'import pathlib,sys;pathlib.Path("report.json").write_text(sys.argv[1])', json.dumps(report)]
            config.write_text(json.dumps({'cwd': '.', 'command': command, 'report': 'report.json'}))
            with patch.object(Path, 'read_text', read), redirect_stdout(io.StringIO()), tempfile.TemporaryFile(mode='w+') as stderr, redirect_stderr(stderr):
                self.assertEqual(crap.config_result(config), 0)
            self.assertEqual(len(reads), 1)
            (root / 'report.json').unlink()
            report = {'baselinePassed': True, 'mutants': [{'status': 'killed'}]}
            command[-1] = json.dumps(report)
            config.write_text(json.dumps({'cwd': '.', 'command': command, 'report': 'report.json', 'format': 'normalized'}))
            reads.clear()
            with patch.object(Path, 'read_text', read), tempfile.TemporaryFile(mode='w+') as stderr, redirect_stderr(stderr):
                self.assertEqual(mutation.run_mutation(config)['exitCode'], 0)
            self.assertEqual(len(reads), 1)

    def test_invalid_language_arguments_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'at least one source'):
                crap.language_result('python', [directory])
            with self.assertRaisesRegex(ValueError, 'one project'):
                mutation.language_result('python', [directory, 'extra'])
            with redirect_stdout(io.StringIO()), tempfile.TemporaryFile(mode="w+") as stderr, redirect_stderr(stderr):
                self.assertEqual(mutation.main(['--json', 'swift', directory, '--', 'nonexistent']), 2)

    def test_failed_coverage_command_is_run_failure(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryFile(mode="w+") as stderr, redirect_stderr(stderr):
            with self.assertRaisesRegex(ValueError, 'Coverage command failed'):
                crap.language_result('js', [directory, 'sample.js', '--', sys.executable, '-c', 'raise SystemExit(1)'])
