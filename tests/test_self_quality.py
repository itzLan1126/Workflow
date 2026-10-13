"""Check self-quality command scope, fresh copies, and exit propagation."""
from contextlib import redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from scripts import self_crap, self_mutation


class SelfQualityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.sources = {
            'skills/workflow/scripts/a.py': 'def a(): return 1\n',
            'skills/workflow/scripts/b.py': 'def b(): return 2\n',
            'scripts/validation.py': 'def validate(): return 3\n',
            'scripts/self_crap.py': 'def main(): return 0\n',
            'scripts/self_mutation.py': 'def main(): return 1\n',
            'tests/test_example.py': 'def test_example(): assert True\n',
            'tests/helpers.py': 'def fixture(): return 3\n',
        }
        for name, content in self.sources.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
        (self.root / 'scripts/ignored.md').write_text('not Python')
        (self.root / 'tests/ignored.txt').write_text('not Python')
        for module in (self_crap, self_mutation):
            for field, value in (('ROOT', self.root), ('SCRIPTS', self.root / 'skills/workflow/scripts')):
                patcher = mock.patch.object(module, field, value)
                patcher.start()
                self.addCleanup(patcher.stop)

    def test_crap_checks_every_production_file_and_propagates_result(self):
        sources = ['skills/workflow/scripts/a.py', 'skills/workflow/scripts/b.py',
                   'scripts/self_crap.py', 'scripts/self_mutation.py', 'scripts/validation.py']
        expected = [sys.executable, str(self.root / 'skills/workflow/scripts/crap.py'),
                    'python', str(self.root), *(str(self.root / name) for name in sources),
                    '--', '-m', 'unittest', 'discover', '-s', 'tests']
        for code in (0, 1, 2):
            with self.subTest(code=code), mock.patch.object(self_crap.subprocess, 'run') as run:
                run.return_value.returncode = code
                self.assertEqual(self_crap.main(), code)
                run.assert_called_once_with(expected, cwd=self.root)

    def test_mutation_copies_all_source_and_test_files_and_propagates_result(self):
        for code in (0, 1, 2):
            with self.subTest(code=code):
                copy = self.root / f'analysis-{code}'
                copy.mkdir()
                with mock.patch.object(self_mutation.tempfile, 'mkdtemp', return_value=str(copy)), \
                        mock.patch.object(sys, 'argv', ['self_mutation.py', '--json']), \
                        mock.patch.object(self_mutation.subprocess, 'run') as run, \
                        redirect_stderr(io.StringIO()) as stderr:
                    run.return_value.returncode = code
                    self.assertEqual(self_mutation.main(), code)
                run.assert_called_once_with([sys.executable, str(self.root / 'skills/workflow/scripts/mutation.py'),
                                             '--json', 'python', str(copy)])
                self.assertEqual(stderr.getvalue(), f'Isolated copy: {copy}\n')
                self.assertEqual({path.name for path in copy.iterdir()},
                                 {'src', 'scripts', 'tests', 'pyproject.toml', 'source-snapshot.json'})
                expected = {}
                for source, content in self.sources.items():
                    folder = 'src' if source.startswith('skills/') else source.split('/')[0]
                    target = copy / folder / Path(source).name
                    self.assertEqual(target.read_text(), content)
                    expected[source] = hashlib.sha256(content.encode('utf-8')).hexdigest()
                self.assertFalse((copy / 'scripts/ignored.md').exists())
                self.assertFalse((copy / 'tests/ignored.txt').exists())
                snapshot = json.loads((copy / 'source-snapshot.json').read_text())
                self.assertEqual(snapshot, {'python': sys.version, 'sha256': expected})
                self.assertEqual((copy / 'pyproject.toml').read_text(),
                                 '[tool.mutmut]\nsource_paths = ["src/", "scripts/"]\n'
                                 'pytest_add_cli_args_test_selection = ["tests/", "-k", '
                                 '"not script_entrypoint and not real_mutmut"]\n')

    def test_copy_failure_does_not_start_mutation_engine(self):
        copy = self.root / 'broken-copy'
        copy.mkdir()
        with mock.patch.object(self_mutation.tempfile, 'mkdtemp', return_value=str(copy)), \
                mock.patch.object(self_mutation.shutil, 'copy2', side_effect=OSError('copy failed')), \
                mock.patch.object(self_mutation.subprocess, 'run') as run, \
                self.assertRaisesRegex(OSError, '^copy failed$'):
            self_mutation.main()
        run.assert_not_called()

    def test_snapshot_hashes_the_assessed_copy_when_original_changes(self):
        copy = self.root / 'source-changed'
        copy.mkdir()
        copy_file = self_mutation.shutil.copy2

        def copy_then_save(source, target):
            result = copy_file(source, target)
            source.write_text('saved after copying\n')
            return result

        with mock.patch.object(self_mutation.tempfile, 'mkdtemp', return_value=str(copy)), \
                mock.patch.object(self_mutation.shutil, 'copy2', side_effect=copy_then_save), \
                mock.patch.object(self_mutation.subprocess, 'run', return_value=mock.Mock(returncode=0)), \
                redirect_stderr(io.StringIO()):
            self.assertEqual(self_mutation.main(), 0)
        snapshot = json.loads((copy / 'source-snapshot.json').read_text())
        self.assertEqual(snapshot['sha256'], {
            source: hashlib.sha256(content.encode()).hexdigest() for source, content in self.sources.items()})

    def test_copy_path_is_flushed_before_engine_starts(self):
        copy = self.root / 'buffered-copy'
        copy.mkdir()
        buffer = io.BytesIO()
        stderr = io.TextIOWrapper(buffer, encoding='utf-8')
        self.addCleanup(stderr.close)

        def run(*args):
            self.assertEqual(buffer.getvalue(), f'Isolated copy: {copy}\n'.encode())
            return mock.Mock(returncode=0)

        with mock.patch.object(self_mutation.tempfile, 'mkdtemp', return_value=str(copy)), \
                mock.patch.object(self_mutation.subprocess, 'run', side_effect=run), redirect_stderr(stderr):
            self.assertEqual(self_mutation.main(), 0)

    def test_mutation_accepts_a_bytes_global_temp_directory(self):
        with mock.patch.object(tempfile, 'tempdir', bytes(self.root)), \
                mock.patch.object(self_mutation.subprocess, 'run', return_value=mock.Mock(returncode=0)) as run, \
                redirect_stderr(io.StringIO()):
            self.assertEqual(self_mutation.main(), 0)
        copy = Path(run.call_args.args[0][-1])
        self.assertEqual(copy.parent, self.root)
        self.assertEqual(json.loads((copy / 'source-snapshot.json').read_text(encoding='utf-8'))['sha256'], {
            source: hashlib.sha256(content.encode('utf-8')).hexdigest() for source, content in self.sources.items()})

    def test_mutation_writes_utf8_under_strict_default_encoding_warnings(self):
        text_encoding = io.text_encoding

        def strict_encoding(encoding, stacklevel=2):
            if encoding is None:
                raise EncodingWarning("'encoding' argument not specified")
            return text_encoding(encoding, stacklevel)

        # Model strict encoding-warning mode in-process so mutation tests retain call association.
        with mock.patch.object(io, 'text_encoding', side_effect=strict_encoding), \
                mock.patch.object(tempfile, 'tempdir', str(self.root)), \
                mock.patch.object(self_mutation.subprocess, 'run', return_value=mock.Mock(returncode=0)) as run, \
                redirect_stderr(io.StringIO()):
            self.assertEqual(self_mutation.main(), 0)
        copy = Path(run.call_args.args[0][-1])
        self.assertEqual((copy / 'pyproject.toml').read_bytes(), self_mutation.MUTMUT_CONFIG.encode('utf-8'))
        self.assertTrue(json.loads((copy / 'source-snapshot.json').read_bytes())['sha256'])

    def test_mutation_respects_audit_policy_for_analysis_directory_ownership(self):
        with mock.patch.object(tempfile, 'tempdir', str(self.root)), \
                mock.patch.object(self_mutation.subprocess, 'run', return_value=mock.Mock(returncode=0)), \
                redirect_stderr(io.StringIO()):
            self.assertEqual(self_mutation.main(), 0)
        code = '''
import importlib.util
import os
from pathlib import Path
import sys
from unittest import mock
spec = importlib.util.spec_from_file_location(sys.argv[3], sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.ROOT = Path(sys.argv[2])
module.SCRIPTS = module.ROOT / 'skills/workflow/scripts'
module.tempfile.tempdir = sys.argv[2]
def owner_policy(event, args):
    if event == 'tempfile.mkdtemp' and not os.path.basename(args[0]).startswith('workflow-self-mutation-'):
        raise PermissionError('unrecognized analysis-directory owner')
sys.addaudithook(owner_policy)
with mock.patch.object(module.subprocess, 'run', return_value=mock.Mock(returncode=0)):
    assert module.main() == 0
'''
        result = subprocess.run([sys.executable, '-c', code, str(Path(self_mutation.__file__).resolve()),
                                 str(self.root), self_mutation.__name__], capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
