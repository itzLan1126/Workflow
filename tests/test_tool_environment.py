"""Pinned Python tool environments through the check entry points, with a fake pip installer."""
from contextlib import redirect_stdout, redirect_stderr
from importlib import metadata
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/workflow/scripts'))
import crap
import duplication
import mutation

# Stands in for `python -m pip`: records its arguments and writes only distribution metadata,
# so the real packages already importable in this interpreter keep doing the analysis.
FAKE_PIP = '''import os, pathlib, sys
args = sys.argv[1:]
with open(os.environ['FAKE_PIP_LOG'], 'a', encoding='utf-8') as log:
    log.write(' '.join(args) + '\\n')
if os.environ.get('FAKE_PIP_FAIL'):
    raise SystemExit(1)
root = pathlib.Path(args[args.index('--target') + 1])
name, version = args[-1].split('==')
version = os.environ.get('FAKE_PIP_VERSION', version)
info = root / (name.replace('-', '_') + '-' + version + '.dist-info')
info.mkdir(parents=True)
(info / 'METADATA').write_text('Metadata-Version: 2.1\\nName: ' + name + '\\nVersion: ' + version + '\\n')
# Real installs bring dependencies, whose versions must not be mistaken for the tool's.
(root / 'dependency-1.0.dist-info').mkdir()
(root / 'dependency-1.0.dist-info/METADATA').write_text('Metadata-Version: 2.1\\nName: dependency\\nVersion: 1.0\\n')
'''
SUFFIX = f'py{sys.version_info.major}.{sys.version_info.minor}'


def missing_from_interpreter(*names):
    version = metadata.version

    def lookup(name):
        if name in names:
            raise metadata.PackageNotFoundError(name)
        return version(name)
    return patch('shared_tools.metadata.version', side_effect=lookup)


class ToolEnvironmentTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve()
        self.project, self.tools, fake = root / 'project', root / 'home/nested/tools', root / 'fake'
        (fake / 'pip').mkdir(parents=True)
        (fake / 'pip/__init__.py').write_text('')
        (fake / 'pip/__main__.py').write_text(FAKE_PIP)
        self.project.mkdir()
        (self.project / 'a.py').write_bytes(b'def f(a):\n    return a\n')
        (self.project / 'requirements.txt').write_bytes(b'example==1\n')
        self.log = root / 'pip.log'
        self.env = {'PYTHONPATH': str(fake), 'FAKE_PIP_LOG': str(self.log), 'WORKFLOW_TOOL_HOME': str(self.tools)}

    def duplication(self, *options, env=None):
        with patch.dict(os.environ, {**self.env, **(env or {})}), redirect_stdout(io.StringIO()), \
                tempfile.TemporaryFile(mode='w+') as stream, redirect_stderr(stream):
            code = duplication.main(['python', str(self.project), 'a.py', *options])
            stream.seek(0)
            error = stream.read()
        evidence = Path(error.splitlines()[0].removeprefix('Evidence: ')) if code != 2 else None
        return code, error, evidence

    def installs(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def project_bytes(self):
        return {p.relative_to(self.project): p.read_bytes() for p in self.project.rglob('*') if p.is_file()}

    def test_interpreter_packages_at_the_pinned_version_are_used_without_installing(self):
        code, error, evidence = self.duplication()
        self.assertEqual(code, 0, error)
        self.assertEqual(json.loads((evidence / 'config.json').read_bytes())['tools'], [
            {'name': 'tree-sitter', 'version': '0.25.2', 'location': 'interpreter'},
            {'name': 'tree-sitter-language-pack', 'version': '0.9.0', 'location': 'interpreter'}])
        self.assertEqual(self.installs(), [])

    def test_missing_or_mismatched_tools_install_once_outside_the_project_and_are_reused(self):
        before = self.project_bytes()
        # A different interpreter version counts as missing: the pinned version is installed alongside.
        with patch('shared_tools.metadata.version', return_value='0.0.1'):
            code, error, evidence = self.duplication()
            self.assertEqual(code, 0, error)
            location = self.tools / f'tree-sitter-0.25.2-{SUFFIX}'
            self.assertEqual(self.installs(), [
                f'install --no-input --target {location} tree-sitter==0.25.2',
                f'install --no-input --target {self.tools / f"tree-sitter-language-pack-0.9.0-{SUFFIX}"} '
                'tree-sitter-language-pack==0.9.0'])
            self.assertEqual(json.loads((evidence / 'config.json').read_bytes())['tools'][0],
                             {'name': 'tree-sitter', 'version': '0.25.2', 'location': str(location)})
            self.assertEqual(self.duplication()[0], 0)
            self.assertEqual(self.duplication('--no-install')[0], 0)
        self.assertEqual(len(self.installs()), 2)
        self.assertEqual(self.project_bytes(), before)
        self.assertEqual(sorted(p.name for p in self.tools.iterdir()),
                         [f'tree-sitter-0.25.2-{SUFFIX}', f'tree-sitter-language-pack-0.9.0-{SUFFIX}'])

    def test_install_failures_version_mismatches_and_partial_environments_are_run_failures(self):
        cases = [({'FAKE_PIP_FAIL': '1'}, 'Tool install failed: '),
                 ({'FAKE_PIP_VERSION': '0.25.1'}, "Tool check failed: tree-sitter 0.25.2 in ")]
        with missing_from_interpreter('tree-sitter', 'tree-sitter-language-pack'):
            for env, message in cases:
                with self.subTest(env=env):
                    code, error, _ = self.duplication(env=env)
                    self.assertEqual(code, 2)
                    self.assertIn(message, error)
                    self.assertEqual(list(self.tools.iterdir()), [])
            partial = self.tools / f'tree-sitter-0.25.2-{SUFFIX}'
            for marker in (None, {'name': 'tree-sitter', 'version': '0.25.1'}):
                with self.subTest(marker=marker):
                    partial.mkdir(exist_ok=True)
                    if marker:
                        (partial / 'complete.json').write_text(json.dumps(marker))
                    code, error, _ = self.duplication()
                    self.assertEqual(code, 2)
                    self.assertIn(f'Duplication: Incomplete tool environment: {partial}; remove it and retry', error)
            (partial / 'complete.json').write_text(json.dumps({'name': 'tree-sitter', 'version': '0.25.2'}))
            code, error, _ = self.duplication()
            self.assertEqual(code, 2)
            self.assertIn('Tool check failed: tree-sitter 0.25.2 in ', error)
        self.assertEqual(self.installs()[-1:], [f'install --no-input --target {partial} tree-sitter==0.25.2'])

    def test_python_crap_installs_lizard_and_coverage_for_the_project(self):
        (self.project / 'a.py').write_bytes(b'def f(a):\n    if a:\n        return 1\n    return 0\n')
        (self.project / 'test_a.py').write_bytes(b'from a import f\n\ndef test_f():\n    assert f(1) == 1\n    assert f(0) == 0\n')
        with missing_from_interpreter('lizard', 'coverage'), patch.dict(os.environ, self.env), \
                patch.object(sys, 'argv', ['crap.py', 'python', str(self.project), 'a.py']), \
                redirect_stdout(io.StringIO()), tempfile.TemporaryFile(mode='w+') as err, redirect_stderr(err):
            code = crap.main()
            err.seek(0)
            evidence = Path(err.readline().removeprefix('Evidence: ').strip())
        self.assertEqual(code, 0)
        self.assertEqual(json.loads((evidence / 'config.json').read_bytes())['tools'], [
            {'name': 'lizard', 'version': '1.17.31', 'location': str(self.tools / f'lizard-1.17.31-{SUFFIX}')},
            {'name': 'coverage', 'version': '7.16.2', 'location': str(self.tools / f'coverage-7.16.2-{SUFFIX}')}])
        with missing_from_interpreter('lizard'), patch.dict(os.environ, self.env), \
                patch.object(sys, 'argv', ['crap.py', 'python', str(self.project), 'a.py', '--no-install']), \
                redirect_stdout(io.StringIO()), tempfile.TemporaryFile(mode='w+') as err, redirect_stderr(err):
            self.assertEqual(crap.main(), 0)

    def test_no_install_with_a_missing_tool_never_creates_an_environment(self):
        with missing_from_interpreter('tree-sitter'):
            code, error, _ = self.duplication('--no-install')
        self.assertEqual(code, 2)
        self.assertEqual(error, 'Duplication: Missing pinned tree-sitter 0.25.2; omit --no-install to install\n')
        self.assertEqual(self.installs(), [])

    def test_tool_home_defaults_to_the_user_cache_and_must_be_outside_the_project(self):
        home = self.tools.parent
        del self.env['WORKFLOW_TOOL_HOME']
        with missing_from_interpreter('tree-sitter'), patch.dict(os.environ, {'HOME': str(home)}):
            os.environ.pop('WORKFLOW_TOOL_HOME', None)
            self.assertEqual(self.duplication()[0], 0)
            code, error, _ = self.duplication(env={'WORKFLOW_TOOL_HOME': str(self.project / 'tools')})
        self.assertTrue((home / f'.cache/workflow/tools/tree-sitter-0.25.2-{SUFFIX}/complete.json').is_file())
        self.assertEqual(code, 2)
        self.assertEqual(error, 'Duplication: Tool environment must be outside the project\n')
        self.assertFalse((self.project / 'tools').exists())

    def test_child_commands_see_owned_tools_first_and_the_environment_is_restored(self):
        seen = self.project.parent / 'seen.json'
        writer = ('import json, os, sys; from pathlib import Path; '
                  f'Path({str(seen)!r}).write_text(json.dumps([os.environ["PYTHONPATH"], sys.argv[1:]])); '
                  'Path(os.environ["WORKFLOW_REPORT_FILE"]).write_text(json.dumps('
                  '{"baselinePassed": True, "mutants": [{"id": "m", "status": "killed"}]}))')
        path = list(sys.path)
        with missing_from_interpreter('lizard'), patch.dict(os.environ, self.env), \
                redirect_stdout(io.StringIO()), tempfile.TemporaryFile(mode='w+') as err, redirect_stderr(err):
            code = mutation.main(['python', str(self.project), '--', sys.executable, '-c', writer, '--no-install'])
            self.assertEqual(os.environ['PYTHONPATH'], self.env['PYTHONPATH'])
        self.assertEqual(code, 0)
        self.assertEqual(sys.path, path)
        self.assertEqual(json.loads(seen.read_text()), [
            os.pathsep.join([str(self.tools / f'lizard-1.17.31-{SUFFIX}'), self.env['PYTHONPATH']]), ['--no-install']])
        with missing_from_interpreter('lizard'), patch.dict(os.environ, self.env):
            os.environ.pop('PYTHONPATH')
            with redirect_stdout(io.StringIO()), tempfile.TemporaryFile(mode='w+') as err, redirect_stderr(err):
                self.assertEqual(mutation.main(['python', str(self.project), '--', sys.executable, '-c', writer]), 0)
            self.assertNotIn('PYTHONPATH', os.environ)
        self.assertEqual(json.loads(seen.read_text())[0], str(self.tools / f'lizard-1.17.31-{SUFFIX}'))


if __name__ == '__main__':
    unittest.main()
