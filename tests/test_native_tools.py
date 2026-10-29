"""JS/TS, Rust and Swift prerequisites, pinned engines, overlays and incremental scoping at the entry points."""
from contextlib import redirect_stdout, redirect_stderr
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
import mutation

# One fake for every external command: behaviour comes from its file name and FAKE_* variables.
FAKE = r'''import json, os, pathlib, shutil, subprocess, sys
me = pathlib.Path(sys.argv[0])
name, args = me.name, sys.argv[1:]
with open(os.environ['FAKE_LOG'], 'a', encoding='utf-8') as log:
    log.write(json.dumps([name, *args]) + '\n')
# Marker files beside one copy of a tool change only that copy.
broken = name in os.environ['FAKE_BROKEN'].split() or me.with_name(name + '.broken').exists()
versions = {'node': 'v22.21.0', 'cargo': 'cargo 1.93.0', 'rustc': os.environ.get('FAKE_RUSTC', 'rustc 1.93.0-nightly'),
            'stryker': 'stryker 10.1.1', 'cargo-mutants': 'cargo-mutants 27.1.0',
            'cargo-llvm-cov': 'cargo-llvm-cov 0.9.1', 'muter': '16.0.0', 'xcrun': 'Swift version 6.4'}
override = me.with_name(name + '.version')
# Like the real binaries, cargo subcommands invoked directly expect their subcommand name first.
if name.startswith('cargo-') and args[:1] != [name.removeprefix('cargo-')]:
    raise SystemExit(2)
if args[-1:] == ['--version']:
    print(override.read_text() if override.exists() else versions[name])
    raise SystemExit(int(broken))
if broken or name == 'xcrun':
    raise SystemExit(1)
elif name == 'rustup':
    print(os.environ.get('FAKE_COMPONENTS', 'llvm-tools-aarch64-apple-darwin'))
elif name in ('npm', 'cargo') and 'install' in args:
    root = pathlib.Path(args[args.index('--prefix' if name == 'npm' else '--root') + 1])
    tool = 'stryker' if name == 'npm' else args[args.index('install') + 1]
    target = root / ('node_modules/.bin' if name == 'npm' else 'bin') / tool
    target.parent.mkdir(parents=True)
    shutil.copy(sys.argv[0], target)
    (root / 'installed-from').write_text(os.getcwd())
    if os.environ.get('FAKE_INSTALLED_VERSION'):
        target.with_name(tool + '.version').write_text(os.environ['FAKE_INSTALLED_VERSION'])
    raise SystemExit(int(os.environ.get('FAKE_INSTALL_EXIT', '0')))
elif name == 'cargo':
    subcommand = [a for a in args if a != '+nightly']
    raise SystemExit(subprocess.call([shutil.which('cargo-' + subcommand[0]), *subcommand]))
elif name == 'node':
    pathlib.Path(os.environ['WORKFLOW_COVERAGE_FILE']).write_text(os.environ['FAKE_LCOV'])
elif name == 'cargo-llvm-cov':
    pathlib.Path(args[args.index('--output-path') + 1]).write_text(os.environ['FAKE_LCOV'])
else:
    cwd = pathlib.Path.cwd()
    pathlib.Path(os.environ['FAKE_SOURCES']).write_text(json.dumps({'path': os.environ['PATH'], 'files': sorted(
        str(p.relative_to(cwd)) for p in cwd.rglob('*') if p.is_file())}))
    if name == 'muter':
        (cwd.parent / (cwd.name + '_mutated')).mkdir()
    (cwd / 'written-by-engine').write_text('engine output')
    report = pathlib.Path(os.environ['WORKFLOW_REPORT_FILE'])
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(os.environ['FAKE_REPORT'])
    if name == 'cargo-mutants':
        (report.parent / 'diff').mkdir()
        (report.parent / 'diff/m.diff').write_text('--- a\n+++ b\n')
'''
COMMANDS = ['node', 'npm', 'cargo', 'rustc', 'rustup', 'xcrun', 'muter']
STRYKER = {'files': {'a.js': {'mutants': [{'id': '1', 'status': 'Killed'}]}}}
CARGO = {'total_mutants': 1, 'outcomes': [
    {'scenario': 'Baseline', 'summary': 'Success', 'phase_results': [{'phase': 'Test'}]},
    {'scenario': {'Mutant': {'name': 'src/lib.rs: replace +', 'file': 'src/lib.rs'}}, 'summary': 'CaughtMutant',
     'diff_path': 'diff/m.diff', 'phase_results': [{'phase': 'Test'}]}]}
# Muter names only the file and the operator, so identity also needs the line and the snippet.
MUTER = {'fileReports': [{'fileName': 'A.swift', 'appliedOperators': [
    {'mutationPoint': {'mutationOperatorId': 'RelationalOperatorReplacement', 'position': {'line': line}},
     'mutationSnapshot': {'before': '<', 'after': '>'}, 'testSuiteOutcome': 'failed'} for line in (2, 3)]}]}
SOURCES = {'js': {'a.js': 'function f(x) {\n  return x ? 1 : 0;\n}\n', 'b.js': 'const b = 1;\n',
                  'package.json': '{}', 'package-lock.json': '{}'},
           'rust': {'src/lib.rs': 'pub fn f(x: i32) -> i32 {\n    if x > 0 { 1 } else { 0 }\n}\n',
                    'src/b.rs': 'pub const B: i32 = 1;\n', 'Cargo.toml': '[package]\nname = "a"\n'},
           'swift': {'Sources/A/A.swift': 'func f(x: Int) -> Bool {\n    x < 1\n    && x < 2\n}\n',
                     'Sources/A/B.swift': 'let b = 1\n'}}


@unittest.skipIf(os.name == 'nt', 'POSIX executable fixtures')
class NativeToolTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.bin, self.tools = self.root / 'bin', self.root / 'tools'
        self.bin.mkdir()
        for command in COMMANDS:
            self.fake(self.bin / command)
        self.log, self.seen = self.root / 'log.jsonl', self.root / 'seen.json'
        self.env = {'PATH': str(self.bin), 'FAKE_INSTALLED_VERSION': '', 'WORKFLOW_TOOL_HOME': str(self.tools), 'FAKE_LOG': str(self.log),
                    'FAKE_SOURCES': str(self.seen), 'FAKE_BROKEN': '', 'FAKE_REPORT': ''}

    def fake(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#!' + sys.executable + '\n' + FAKE, encoding='utf-8')
        path.chmod(0o755)

    def project(self, language):
        project = self.root / language
        for name, text in SOURCES[language].items():
            (project / name).parent.mkdir(parents=True, exist_ok=True)
            (project / name).write_text(text)
        return project

    def snapshot(self, directory):
        return {str(p.relative_to(directory)): p.read_bytes() for p in directory.rglob('*') if p.is_file()}

    def calls(self, name, probes=False):
        lines = self.log.read_text().splitlines() if self.log.exists() else []
        return [call for call in map(json.loads, lines) if call[0] == name and (probes or call[-1] != '--version')]

    def run_check(self, module, args, env=()):
        with patch.dict(os.environ, {**self.env, **dict(env)}), patch('lang_swift.sys.platform', 'darwin'), \
                redirect_stdout(io.StringIO()) as out, tempfile.TemporaryFile(mode='w+') as err, redirect_stderr(err):
            with patch.object(sys, 'argv', ['check.py', *args]):
                code = module.main()
            err.seek(0)
            error = err.read()
        evidence = next((Path(line[10:]) for line in error.splitlines() if line.startswith('Evidence: ')), None)
        return code, error, evidence, out.getvalue()

    def engine_path(self):
        return json.loads(self.seen.read_text())['path']

    def mutate(self, language, project, report, *options, env=()):
        code, error, evidence, out = self.run_check(
            mutation, ['--json', language, str(project), '--overlay', *options], {'FAKE_REPORT': json.dumps(report), **dict(env)})
        return code, error, evidence, json.loads(out) if out else None

    def test_js_installs_stryker_outside_the_project_reuses_it_and_respects_no_install(self):
        project = self.project('js')
        before = self.snapshot(project)
        code, error, _, _ = self.mutate('js', project, STRYKER, '--no-install')
        self.assertEqual(code, 2)
        self.assertIn('mutation: Missing pinned stryker 10.1.1; omit --no-install to install', error)
        code, error, evidence, result = self.mutate('js', project, STRYKER)
        self.assertEqual(code, 0, error)
        installed = self.tools / 'stryker-10.1.1'
        self.assertEqual(self.calls('npm')[-1], ['npm', 'install', '--prefix', str(installed), '--no-package-lock',
                                                 '--no-save', '@stryker-mutator/core@10.1.1'])
        self.assertEqual(self.calls('stryker')[-1], ['stryker', 'run', '--testRunner', 'command', '--reporters', 'json'])
        self.assertEqual((installed / 'installed-from').read_text(), str(installed))
        self.assertEqual(self.engine_path(), os.pathsep.join([str(installed / 'node_modules/.bin'), str(self.bin)]))
        config = json.loads((evidence / 'config.json').read_bytes())
        self.assertEqual(config['tools'][1:], [{'name': 'stryker', 'version': '10.1.1', 'location': str(installed)}])
        self.assertEqual(result['counts']['killed'], 1)
        self.assertTrue(Path(result['reportPath']).resolve().is_relative_to(evidence.resolve()))
        self.assertFalse(Path(config['cwd']).exists())
        self.assertEqual(self.mutate('js', project, STRYKER, '--no-install')[0], 0)
        self.assertEqual(len(self.calls('npm')), 1)
        self.assertEqual(self.snapshot(project), before)

    def test_js_prefers_a_pinned_project_or_path_stryker_and_replaces_wrong_or_broken_ones(self):
        project = self.project('js')
        self.fake(project / 'node_modules/.bin/stryker')

        def location():
            code, error, evidence, _ = self.mutate('js', project, STRYKER)
            self.assertEqual(code, 0, error)
            return json.loads((evidence / 'config.json').read_bytes())['tools'][1]['location']
        local = location()
        self.assertTrue(local.endswith('/node_modules/.bin/stryker'), local)
        self.assertNotIn(str(project), local)
        self.assertEqual(self.engine_path(), os.pathsep.join([str(Path(local).parent), str(self.bin)]))
        (project / 'node_modules/.bin/stryker').unlink()
        self.fake(self.bin / 'stryker')
        code, error, evidence, _ = self.mutate('js', project, STRYKER)
        self.assertEqual(json.loads((evidence / 'config.json').read_bytes())['tools'][1],
                         {'name': 'stryker', 'version': '10.1.1', 'location': str(self.bin / 'stryker')})
        self.assertEqual(self.engine_path(), str(self.bin))
        self.assertEqual(self.calls('npm'), [])
        (self.bin / 'stryker.version').write_text('stryker 9.0.0')
        self.assertEqual(location(), str(self.tools / 'stryker-10.1.1'))
        (self.bin / 'stryker.version').unlink()
        (self.bin / 'stryker.broken').write_text('')
        self.assertEqual(location(), str(self.tools / 'stryker-10.1.1'))
        self.assertEqual(len(self.calls('npm')), 1)

    def test_failed_installs_and_missing_node_are_run_failures_without_partial_environments(self):
        project = self.project('js')
        code, error, _, _ = self.mutate('js', project, STRYKER, env={'FAKE_INSTALL_EXIT': '1'})
        self.assertEqual(code, 2)
        self.assertIn('mutation: Tool install failed: npm (see installer output)', error)
        self.assertEqual(list(self.tools.iterdir()), [])
        code, error, _, _ = self.mutate('js', project, STRYKER, env={'FAKE_INSTALLED_VERSION': 'stryker 10.1.0'})
        self.assertEqual(code, 2)
        self.assertIn(f"mutation: Tool check failed: {self.tools / 'stryker-10.1.1/node_modules/.bin/stryker'} --version: "
                      'stryker 10.1.0', error)
        self.assertEqual(list(self.tools.iterdir()), [])
        code, error, _, _ = self.mutate('js', project, STRYKER, env={'FAKE_BROKEN': 'node'})
        self.assertEqual(code, 2)
        self.assertIn('mutation: Tool check failed: node --version: v22.21.0. Install Node.js; '
                      'system toolchains are never installed automatically', error)
        self.assertEqual(len(self.calls('npm')), 2)
        writer = [sys.executable, '-c', 'import os, pathlib; pathlib.Path(os.environ["WORKFLOW_REPORT_FILE"]).parent.mkdir('
                  'parents=True); pathlib.Path(os.environ["WORKFLOW_REPORT_FILE"]).write_text(os.environ["FAKE_REPORT"])']
        code, error, _, _ = self.mutate('js', project, STRYKER, '--', *writer, env={'FAKE_BROKEN': 'node'})
        self.assertEqual(code, 0, error)
        lcov = f'SF:{project / "a.js"}\nDA:1,1\nDA:2,1\nBRDA:2,0,0,1\nBRDA:2,0,1,1\nend_of_record\n'
        coverage = [sys.executable, '-c', 'import os, pathlib; pathlib.Path(os.environ["WORKFLOW_COVERAGE_FILE"]).write_text('
                    'os.environ["FAKE_LCOV"])']
        code, error, _, _ = self.run_check(crap, ['js', str(project), 'a.js', '--', *coverage],
                                           {'FAKE_BROKEN': 'node', 'FAKE_LCOV': lcov})
        self.assertEqual(code, 0, error)

    def test_js_crap_needs_node_but_not_stryker(self):
        project = self.project('js')
        lcov = f'SF:{project / "a.js"}\nDA:1,1\nDA:2,1\nBRDA:2,0,0,1\nBRDA:2,0,1,1\nend_of_record\n'
        code, error, evidence, _ = self.run_check(crap, ['js', str(project), 'a.js'], {'FAKE_LCOV': lcov})
        self.assertEqual(code, 0, error)
        self.assertEqual([t['name'] for t in json.loads((evidence / 'config.json').read_bytes())['tools']], ['lizard'])
        self.assertEqual(self.calls('npm'), [])

    def test_rust_crap_requires_nightly_and_llvm_tools_then_runs_pinned_cargo_llvm_cov(self):
        project = self.project('rust')
        hint = '; system toolchains are never installed automatically'
        cases = [({'FAKE_BROKEN': 'cargo'}, 'CRAP: Tool check failed: cargo --version: cargo 1.93.0. Install Rust with rustup' + hint),
                 ({'FAKE_RUSTC': 'rustc 1.93.0'}, 'CRAP: Tool check failed: rustc +nightly --version: rustc 1.93.0. '
                  'Install nightly Rust: rustup toolchain install nightly' + hint),
                 ({'FAKE_COMPONENTS': 'rust-src'}, 'CRAP: Tool check failed: rustup component list --installed '
                  '--toolchain nightly: rust-src. Install nightly LLVM tools: rustup component add '
                  'llvm-tools-preview --toolchain nightly' + hint)]
        for env, message in cases:
            with self.subTest(env=env):
                code, error, _, _ = self.run_check(crap, ['rust', str(project), 'src/lib.rs'], env)
                self.assertEqual((code, error.strip().splitlines()[-1]), (2, message))
        self.assertEqual(self.calls('cargo-llvm-cov'), [])
        lcov = (f'SF:{project / "src/lib.rs"}\nDA:1,1\nDA:2,1\nDA:3,1\n'
                'BRDA:2,0,0,1\nBRDA:2,0,1,1\nend_of_record\n')
        code, error, evidence, _ = self.run_check(crap, ['rust', str(project), 'src/lib.rs'], {'FAKE_LCOV': lcov})
        self.assertEqual(code, 0, error)
        installed = self.tools / 'cargo-llvm-cov-0.9.1'
        self.assertEqual(self.calls('cargo')[-1][1:], ['+nightly', 'llvm-cov', '--branch', '--lcov', '--output-path',
                                                       str(evidence / 'coverage.lcov')])
        self.assertIn(['cargo', 'install', 'cargo-llvm-cov', '--version', '0.9.1', '--locked', '--root', str(installed)],
                      self.calls('cargo'))
        self.assertEqual(json.loads((evidence / 'config.json').read_bytes())['tools'][1:],
                         [{'name': 'cargo-llvm-cov', 'version': '0.9.1', 'location': str(installed)}])

    def test_rust_mutation_installs_cargo_mutants_and_keeps_output_in_evidence(self):
        project = self.project('rust')
        before = self.snapshot(project)
        code, error, evidence, result = self.mutate('rust', project, CARGO)
        self.assertEqual(code, 0, error)
        self.assertEqual(self.calls('cargo-mutants')[-1], ['cargo-mutants', 'mutants', '--output', str(evidence)])
        self.assertEqual(json.loads((evidence / 'config.json').read_bytes())['tools'][1]['location'],
                         str(self.tools / 'cargo-mutants-27.1.0'))
        self.assertTrue(Path(result['reportPath']).resolve().is_relative_to(evidence.resolve()))
        self.assertEqual(self.calls('rustc'), [])
        self.assertEqual(result['outcomes'][0]['diff'], '--- a\n+++ b\n')
        self.assertEqual(self.snapshot(project), before)
        self.fake(self.bin / 'cargo-mutants')
        code, error, evidence, _ = self.mutate('rust', project, CARGO, '--no-install')
        self.assertEqual(code, 0, error)
        self.assertEqual(json.loads((evidence / 'config.json').read_bytes())['tools'][1]['location'],
                         str(self.bin / 'cargo-mutants'))

    def test_swift_needs_xcode_and_muter_installs_nothing_and_keeps_muter_siblings_disposable(self):
        project = self.project('swift')
        code, error, _, _ = self.mutate('swift', project, MUTER, env={'FAKE_BROKEN': 'xcrun'})
        self.assertEqual(code, 2)
        self.assertIn('Install Xcode command line tools: xcode-select --install; system toolchains', error)
        code, error, _, _ = self.mutate('swift', project, MUTER, env={'FAKE_BROKEN': 'muter'})
        self.assertEqual(code, 2)
        self.assertIn('Install Muter from https://github.com/muter-mutation-testing/muter; system toolchains', error)
        code, error, _, _ = self.run_check(crap, ['swift', str(project), 'Sources/A/A.swift'], {'FAKE_BROKEN': 'muter'})
        self.assertEqual((code, error.strip().splitlines()[-1]), (2, 'CRAP: Coverage command failed'))
        code, error, evidence, result = self.mutate('swift', project, MUTER)
        self.assertEqual(code, 0, error)
        self.assertEqual(json.loads((evidence / 'config.json').read_bytes())['tools'][1:],
                         [{'name': 'muter', 'version': '16.0.0', 'location': 'PATH'}])
        self.assertEqual(self.calls('muter')[-1][1:], ['run', '--format', 'json', '--output',
                                                       str(evidence / 'mutation.json'), '--skip-update-check'])
        self.assertEqual(result['counts']['killed'], 2)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['bin', 'log.jsonl', 'seen.json', 'swift'])
        self.assertFalse(self.tools.exists())

    def test_incremental_runs_reuse_unchanged_files_and_scope_changed_files_per_engine(self):
        cases = [('js', STRYKER, ['a.js', 'b.js'], ['--mutate', 'a.js,b.js']),
                 ('rust', CARGO, ['src/b.rs', 'src/lib.rs'], ['--file', 'src/b.rs', '--file', 'src/lib.rs']),
                 ('swift', MUTER, ['Sources/A/A.swift', 'Sources/A/B.swift'],
                  ['--files-to-mutate', 'Sources/A/A.swift,Sources/A/B.swift'])]
        for language, report, sources, scope in cases:
            with self.subTest(language=language):
                project = self.project(language)
                engine = {'js': 'stryker', 'rust': 'cargo-mutants', 'swift': 'muter'}[language]
                code, error, first, result = self.mutate(language, project, report)
                self.assertEqual(code, 0, error)
                runs = len(self.calls(engine))
                code, error, second, result = self.mutate(language, project, report, '--previous-evidence', str(first))
                self.assertEqual(code, 0, error)
                self.assertEqual(len(self.calls(engine)), runs)
                self.assertEqual(result['reusedCount'], result['counts']['killed'])
                self.assertTrue(all(item['reused'] for item in result['outcomes']))
                self.assertEqual(result['incrementalScope'], {'files': [], 'functions': None, 'fallback': 'full file'})
                for source in sources:
                    (project / source).write_text((project / source).read_text() + '\n')
                code, error, third, result = self.mutate(language, project, report, '--previous-evidence', str(second))
                self.assertEqual(code, 0, error)
                self.assertEqual(self.calls(engine)[-1][-len(scope):], scope)
                self.assertEqual(result['incrementalScope'], {'files': sources, 'functions': None, 'fallback': 'full file'})
                self.assertEqual(result['format'], {'js': 'stryker', 'rust': 'cargo-mutants', 'swift': 'muter'}[language])
                self.assertEqual(json.loads((third / 'config.json').read_bytes())['selectedFiles'], sources)


if __name__ == '__main__':
    unittest.main()
