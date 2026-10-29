"""Evidence remains portable when the host defaults to a legacy encoding."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/workflow/scripts'))


class EvidenceEncodingTests(unittest.TestCase):
    def test_mutation_config_preserves_plus_signs_under_utf7_default(self):
        import mutation
        write_text = Path.write_text
        def write(path, text, *args, encoding=None, **kwargs):
            return write_text(path, text, *args, encoding=encoding or 'utf-7', **kwargs)
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / 'project+plus'
            project.mkdir()
            writer = ('import os,pathlib; pathlib.Path(os.environ["WORKFLOW_REPORT_FILE"]).write_text('
                      '\'{"baselinePassed":true,"mutants":[{"status":"killed"}]}\', encoding="utf-8")')
            with patch.object(Path, 'write_text', write), \
                    tempfile.TemporaryFile(mode='w+') as stderr, redirect_stderr(stderr):
                result = mutation.language_result('python', [str(project), '--', sys.executable, '-c', writer])
            self.assertEqual(result['exitCode'], 0)
            config = Path(result['reportPath']).parent / 'config.json'
            self.assertEqual(json.loads(config.read_text(encoding='utf-8'))['cwd'], str(project.resolve()))

    def test_python_export_preserves_diff_plus_signs_under_utf7_default(self):
        import lang_python
        from shared_runner import read_json
        write_text = Path.write_text
        def write(path, text, *args, encoding=None, **kwargs):
            return write_text(path, text, *args, encoding=encoding or 'utf-7', **kwargs)
        mutants = [{'id': 'module.x_choose__mutmut_1', 'status': 'survived',
                    'diff': '--- before\n+++ after\n@@ -1 +1 @@\n-return 1\n+return 2'}]
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                with patch.object(Path, 'write_text', write), patch('lang_python.subprocess.run'), \
                        patch('lang_python.collect', return_value=mutants), \
                        patch.dict(sys.modules, {'mutmut.__main__': SimpleNamespace(status_by_exit_code={})}), \
                        patch('lang_python.add_details', side_effect=lambda value, **kwargs: value):
                    self.assertEqual(lang_python.main(['report.json']), 0)
                self.assertEqual(read_json('report.json'), {'baselinePassed': True, 'mutants': mutants})
            finally:
                os.chdir(previous)

    def test_evidence_writers_work_with_encoding_warnings_as_errors(self):
        import lang_python
        code = '''import json, os, pathlib, sys
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
import lang_python, mutation
root = pathlib.Path(sys.argv[2])
if os.environ.get('MUTANT_UNDER_TEST') == 'stats':
    from mutmut.configuration import config
    config()  # Cache the analysis configuration before entering the writer fixture.
os.chdir(root)
with patch.dict(sys.modules, {'mutmut.__main__': SimpleNamespace(status_by_exit_code={})}), \\
     patch('lang_python.subprocess.run'), \\
     patch('lang_python.collect', return_value=[{'id': 'm+1', 'status': 'killed'}]), \\
     patch('lang_python.add_details', side_effect=lambda value, **kwargs: value):
    assert lang_python.main([str(root / 'export.json')]) == 0
assert json.loads((root / 'export.json').read_text(encoding='utf-8'))['mutants'][0]['id'] == 'm+1'
project = root / 'project+plus'
project.mkdir()
writer = "import json,os,pathlib;pathlib.Path(os.environ['WORKFLOW_REPORT_FILE']).write_text(json.dumps({'baselinePassed':True,'mutants':[{'status':'killed'}]}),encoding='utf-8')"
assert mutation.language_result('python', [str(project), '--', sys.executable, '-c', writer])['exitCode'] == 0
'''
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-X', 'warn_default_encoding', '-W',
                                     'error::EncodingWarning', '-c', code,
                                     str(Path(lang_python.__file__).resolve().parent), directory],
                                    capture_output=True, text=True, encoding='utf-8', timeout=8)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_python_config_and_source_use_utf8_under_legacy_locale(self):
        from lang_python import coverage_commands
        from shared_crap import analyze
        read_text, write_text = Path.read_text, Path.write_text
        def read(path, *args, encoding=None, **kwargs):
            return read_text(path, *args, encoding=encoding or 'ascii', **kwargs)
        def write(path, text, *args, encoding=None, **kwargs):
            return write_text(path, text, *args, encoding=encoding or 'ascii', **kwargs)
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / '项目'
            project.mkdir()
            source = project / 'sample.py'
            source.write_text('def example():\n    return "你好"\n', encoding='utf-8')
            with patch.object(Path, 'read_text', read), patch.object(Path, 'write_text', write):
                coverage_commands(project, Path(directory), [])
                self.assertIn('你好', analyze(source)[0])

    def test_language_entry_point_reads_unicode_source_under_legacy_locale(self):
        import crap
        import lang_js
        from shared_languages import Crap
        read_text = Path.read_text
        def read(path, *args, encoding=None, **kwargs):
            return read_text(path, *args, encoding=encoding or 'ascii', **kwargs)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'sample.js'
            source.write_text('function a() {\n return "你好";\n}\n', encoding='utf-8')
            def commands(project, evidence, args):
                (evidence / 'coverage.lcov').write_text(f'SF:{source}\nDA:2,1\nBRDA:2,0,0,1\nend_of_record\n', encoding='utf-8')
                return []
            with patch.object(lang_js, 'CRAP', Crap('lcov', commands, 'coverage.lcov')), patch.object(Path, 'read_text', read), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(crap.dispatch(['js', directory, 'sample.js']), 0)
