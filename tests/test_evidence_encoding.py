"""Evidence remains portable when the host defaults to a legacy encoding."""
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/workflow/scripts'))


class EvidenceEncodingTests(unittest.TestCase):
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
