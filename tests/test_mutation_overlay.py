"""Overlay isolation through mutation's public entry point."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/workflow/scripts'))
import mutation


class OverlayTests(unittest.TestCase):
    def test_overlay_cleans_up_and_preserves_original_on_every_result(self):
        for status, expected in [('killed', 0), ('survived', 1), ('error', 2)]:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                (project / 'source.py').write_bytes(b'original\n')
                script = ('import os,pathlib,json; p=pathlib.Path.cwd(); '
                          '(p/"source.py").write_text("mutated"); '
                          'pathlib.Path(os.environ["WORKFLOW_REPORT_FILE"]).write_text(json.dumps('
                          '{"baselinePassed":True,"mutants":[{"id":"m","status":' + repr(status) + '}]}))')
                with redirect_stdout(io.StringIO()) as out, tempfile.TemporaryFile(mode='w+') as err, redirect_stderr(err):
                    code = mutation.main(['--json', 'python', directory, '--overlay', '--', sys.executable, '-c', script])
                    err.seek(0)
                    logs = err.read()
                self.assertEqual(code, expected, logs)
                self.assertEqual((project / 'source.py').read_bytes(), b'original\n')
                result = json.loads(out.getvalue())
                evidence = Path(result['reportPath']).parent
                config = json.loads((evidence / 'config.json').read_bytes())
                self.assertFalse(Path(config['cwd']).exists())
                self.assertTrue(Path(result['reportPath']).exists())

    def test_overlay_copies_symlink_targets_before_the_engine_can_write_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / 'project'
            project.mkdir()
            target = root / 'external.txt'
            target.write_bytes(b'original')
            (project / 'linked.txt').symlink_to(target)
            script = ('import os,pathlib; pathlib.Path("linked.txt").write_text("changed"); '
                      'pathlib.Path(os.environ["WORKFLOW_REPORT_FILE"]).write_text('
                      '\'{"baselinePassed":true,"mutants":[{"status":"killed"}]}\')')
            with redirect_stdout(io.StringIO()), tempfile.TemporaryFile(mode='w+') as err, redirect_stderr(err):
                code = mutation.main(['python', str(project), '--overlay', '--', sys.executable, '-c', script])
            self.assertEqual(code, 0)
            self.assertEqual(target.read_bytes(), b'original')

    def test_overlay_timeout_preserves_original_and_removes_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / 'a.py').write_bytes(b'original')
            with tempfile.TemporaryFile(mode='w+') as err, redirect_stderr(err):
                code = mutation.main(['python', directory, '--overlay', '--timeout-ms', '100', '--',
                                      sys.executable, '-c', 'import pathlib,time; pathlib.Path("a.py").write_text("changed"); time.sleep(10)'])
                err.seek(0)
                logs = err.read()
            self.assertEqual(code, 2, logs)
            self.assertEqual((project / 'a.py').read_bytes(), b'original')
            evidence = Path(next(l.removeprefix('Evidence: ') for l in logs.splitlines() if l.startswith('Evidence: ')))
            self.assertFalse(Path(json.loads((evidence / 'config.json').read_bytes())['cwd']).exists())
