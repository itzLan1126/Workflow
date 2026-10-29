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
        from shared_languages import language
        self.assertIs(language('ts'), language('js'))

    def test_js_commands_and_report_location(self):
        from lang_js import coverage_commands, mutation_command, report_path
        project, evidence = Path('/project'), Path('/evidence')
        self.assertEqual(coverage_commands(project, evidence, []), [['node', '--experimental-strip-types', '--test', '--experimental-test-coverage', '--test-reporter=lcov', '--test-reporter-destination=/evidence/coverage.lcov']])
        self.assertEqual(coverage_commands(project, evidence, ['custom']), [['custom']])
        self.assertEqual(mutation_command(project, evidence, []), ['stryker', 'run', '--testRunner', 'command', '--reporters', 'json'])
        self.assertEqual(mutation_command(project, evidence, ['custom']), ['custom'])
        self.assertEqual(report_path(project, evidence), project / 'reports/mutation/mutation.json')

    def test_js_mutation_uses_platform_shim_and_preserves_override(self):
        from lang_js import mutation_command
        from unittest.mock import patch
        project, evidence = Path('/project with spaces'), Path('/evidence')
        for platform, executable in (('posix', 'stryker'), ('nt', 'stryker.cmd')):
            with self.subTest(platform=platform), patch('os.name', platform):
                self.assertEqual(mutation_command(project, evidence, []),
                                 [executable, 'run',
                                  '--testRunner', 'command', '--reporters', 'json'])
                self.assertEqual(mutation_command(project, evidence, ['custom', 'literal argument']),
                                 ['custom', 'literal argument'])

    def test_python_mutation_command_and_report_location(self):
        import lang_python
        project, evidence = Path('/project'), Path('/evidence')
        self.assertEqual(lang_python.mutation_command(project, evidence, []),
                         [sys.executable, str(Path(lang_python.__file__).resolve()), '/evidence/mutation.json'])
        self.assertEqual(lang_python.mutation_command(project, evidence, ['custom']), ['custom'])
        self.assertEqual(lang_python.report_path(project, evidence), evidence / 'mutation.json')

    def test_rust_commands_and_report_location(self):
        from lang_rust import coverage_commands, mutation_command, report_path, require_nightly
        import lang_rust
        from unittest.mock import patch
        import subprocess
        project, evidence = Path('/project'), Path('/evidence')
        def probe(command, *, capture_output, text):
            self.assertEqual(command, ['rustc', '+nightly', '--version'])
            self.assertIs(capture_output, True)
            self.assertIs(text, True)
            return subprocess.CompletedProcess(command, 0, 'rustc nightly', '')
        with patch('lang_rust.subprocess.run', side_effect=probe):
            require_nightly()
        helper = [sys.executable, str(Path(lang_rust.__file__).resolve())]
        self.assertEqual(coverage_commands(project, evidence, []), [helper, ['cargo', '+nightly', 'llvm-cov', '--branch', '--lcov', '--output-path', '/evidence/coverage.lcov']])
        self.assertEqual(coverage_commands(project, evidence, ['custom']), [helper, ['custom']])
        self.assertEqual(mutation_command(project, evidence, []), ['cargo', 'mutants', '--output', '/evidence'])
        self.assertEqual(mutation_command(project, evidence, ['custom']), ['custom'])
        self.assertEqual(report_path(project, evidence), evidence / 'mutants.out/outcomes.json')

    def test_swift_commands_and_report_location(self):
        from lang_swift import coverage_commands, mutation_command, report_path
        from unittest.mock import patch
        project, evidence = Path('/project'), Path('/evidence')
        with patch('lang_swift.sys.platform', 'darwin'):
            self.assertEqual(coverage_commands(project, evidence, [])[0], ['xcrun', 'swift', 'test', '--enable-code-coverage'])
            self.assertEqual(coverage_commands(project, evidence, ['custom'])[0], ['custom'])
            import lang_swift
            self.assertEqual(coverage_commands(project, evidence, [])[1], [sys.executable, str(Path(lang_swift.__file__).resolve()), '/project', '/evidence/coverage.json'])
            self.assertEqual(mutation_command(project, evidence, []), ['muter', 'run', '--format', 'json', '--output', '/evidence/mutation.json', '--skip-update-check'])
            self.assertEqual(mutation_command(project, evidence, ['custom']), ['custom'])
            self.assertEqual(report_path(project, evidence), evidence / 'mutation.json')

    def test_python_override_replaces_pytest(self):
        from lang_python import coverage_commands
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory)
            command = coverage_commands(Path('.'), evidence, ['-m', 'unittest'])[0]
            self.assertEqual(command[-2:], ['-m', 'unittest'])
            self.assertNotIn('pytest', command)
            import configparser
            config = configparser.ConfigParser()
            config.read(evidence / 'coveragerc')
            self.assertEqual(dict(config['run']), {'branch': 'true', 'source': '.', 'patch': 'subprocess', 'data_file': str(evidence / '.coverage')})
            commands = coverage_commands(Path('.'), evidence, [])
            self.assertEqual(commands, [[sys.executable, '-m', 'coverage', 'run', f'--rcfile={evidence / "coveragerc"}', '-m', 'pytest'],
                                        [sys.executable, '-m', 'coverage', 'combine', f'--rcfile={evidence / "coveragerc"}'],
                                        [sys.executable, '-m', 'coverage', 'lcov', f'--rcfile={evidence / "coveragerc"}', '-o', str(evidence / 'coverage.lcov')]])

    def test_rust_requires_nightly(self):
        from lang_rust import require_nightly
        from unittest.mock import patch
        import subprocess
        for code, version in ((1, ''), (0, 'rustc stable'), (1, 'rustc nightly')):
            with patch('lang_rust.subprocess.run', return_value=subprocess.CompletedProcess([], code, version, 'missing')):
                with self.assertRaisesRegex(ValueError, '^Rust CRAP check requires a nightly toolchain for branch coverage$'):
                    require_nightly()

    def test_rust_test_module_excludes_braces_in_strings(self):
        from lang_rust import exclude_tests
        self.assertEqual(exclude_tests('lib.rs', 'fn a() {}\n#[cfg(test)]\nmod tests {\n fn t() { let text = "}"; }\n}\n'), [(2, 5)])

    def test_rust_external_test_module_preserves_production_measurements(self):
        from lang_rust import exclude_tests
        from shared_crap import collect
        import tempfile
        code = ('#[cfg(test)]\nmod tests;\n'
                'pub fn production(value: i32) -> i32 {\n'
                '    if value > 0 { 1 } else { 0 }\n}\n')
        with tempfile.TemporaryDirectory() as directory:
            source = (Path(directory) / 'lib.rs').resolve()
            source.write_text(code, encoding='utf-8')
            measured = collect({source: {'lines': {3: 1, 4: 1},
                                        'branches': {(4, '0', '0'): 1, (4, '0', '1'): 0}}},
                               [source], exclude_tests)
        self.assertEqual(exclude_tests(source, code), [(1, 2)])
        self.assertEqual([function['name'] for function in measured['functions']], ['production'])
        self.assertEqual(measured['coverage'], {'line': {'covered': 2, 'total': 2},
                                              'branch': {'covered': 1, 'total': 2}})

    def test_swift_rejects_other_platforms_for_both_checks(self):
        from lang_swift import coverage_commands, mutation_command
        from unittest.mock import patch
        with patch('lang_swift.sys.platform', 'linux'):
            for command in (coverage_commands, mutation_command):
                with self.assertRaisesRegex(ValueError, '^Swift quality checks require macOS$'):
                    command(Path('.'), Path('/tmp'), [])

    def test_timeout_before_source_preserves_source_and_default(self):
        from shared_languages import arguments
        self.assertEqual(arguments(['.', '--timeout-ms', '1234', 'file.py'])[1:], (['file.py'], 1234, []))
        self.assertEqual(arguments(['.'])[2], 3600000)
        with self.assertRaisesRegex(ValueError, 'Require --timeout-ms N'):
            arguments(['.', '--timeout-ms'])
        for args in ([], ['.', '--unknown']):
            with self.assertRaisesRegex(ValueError, 'Require project'):
                arguments(args)
        import tempfile
        with tempfile.NamedTemporaryFile() as file:
            with self.assertRaisesRegex(ValueError, 'project must be a directory'):
                arguments([file.name])

    def test_invalid_timeout_is_run_failure(self):
        from shared_languages import arguments
        for timeout in ('0', '-1', 'no', '2147483648'):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                arguments(['.', '--timeout-ms', timeout])

    def test_missing_project_reports_filesystem_failure_before_directory_validation(self):
        from shared_languages import arguments
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory).resolve() / 'missing'
            with self.assertRaises(FileNotFoundError) as raised:
                arguments([str(missing)])
            self.assertEqual(raised.exception.filename, str(missing))
