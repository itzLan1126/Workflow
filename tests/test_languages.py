import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/workflow/scripts'))


class LanguageArgumentsTests(unittest.TestCase):
    def test_timeout_and_literal_tool_arguments(self):
        from shared_languages import arguments
        project, sources, timeout, tool = arguments(['.', 'source.py', '--timeout-ms', '1234', '--', '-m', 'unittest'])
        self.assertEqual((project, sources, timeout, tool), (Path('.').resolve(), ['source.py'], 1234, ['-m', 'unittest']))

    def test_typescript_alias_loads_same_language_module(self):
        from shared_languages import LANGUAGES
        self.assertEqual(LANGUAGES['ts'], LANGUAGES['js'])

    def test_python_override_replaces_pytest(self):
        from lang_python import coverage_commands
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory)
            command = coverage_commands(Path('.'), evidence, ['-m', 'unittest'])[0]
            self.assertEqual(command[-2:], ['-m', 'unittest'])
            self.assertNotIn('pytest', command)

    def test_invalid_timeout_is_run_failure(self):
        from shared_languages import arguments
        for timeout in ('0', '-1', 'no', '2147483648'):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                arguments(['.', '--timeout-ms', timeout])
