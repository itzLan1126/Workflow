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
            with redirect_stdout(io.StringIO()) as stdout, redirect_stderr(tempfile.TemporaryFile(mode="w+")):
                code = crap.language_result('python', [str(project), 'sample.py'])
            self.assertEqual(code, 0, stdout.getvalue())
            self.assertEqual(json.loads(stdout.getvalue())['findings'], 0)
            engine = [sys.executable, '-c', "import json,pathlib; d=pathlib.Path(__import__('sys').argv[1]); (d/'reports/mutation').mkdir(parents=True); (d/'reports/mutation/mutation.json').write_text(json.dumps({'files':{'sample.js':{'mutants':[{'status':'Killed'}]}}}))", str(project)]
            with redirect_stderr(tempfile.TemporaryFile(mode="w+")):
                result = mutation.language_result('js', [str(project), '--', *engine])
            self.assertEqual(result['exitCode'], 0)
            self.assertTrue(Path(result['reportPath']).is_file())
            self.assertNotEqual(Path(result['reportPath']).parent, project / 'reports/mutation')

    def test_invalid_language_arguments_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'at least one source'):
                crap.language_result('python', [directory])
            with self.assertRaisesRegex(ValueError, 'one project'):
                mutation.language_result('python', [directory, 'extra'])
            with redirect_stdout(io.StringIO()), redirect_stderr(tempfile.TemporaryFile(mode="w+")):
                self.assertEqual(mutation.main(['--json', 'swift', directory, '--', 'nonexistent']), 2)

    def test_failed_coverage_command_is_run_failure(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stderr(tempfile.TemporaryFile(mode="w+")):
            with self.assertRaisesRegex(ValueError, 'Coverage command failed'):
                crap.language_result('js', [directory, 'sample.js', '--', sys.executable, '-c', 'raise SystemExit(1)'])
