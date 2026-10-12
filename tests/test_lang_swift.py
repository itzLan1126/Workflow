import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/workflow/scripts'))

from lang_swift import coverage_commands, export_coverage


class SwiftCoverageTests(unittest.TestCase):
    def test_override_uses_native_report_for_same_configuration_and_paths(self):
        options = (['-c', 'release', '--scratch-path', 'custom scratch', '--package-path', 'nested'],
                   ['-c=release', '--scratch-path=custom scratch', '--package-path=nested'],
                   ['--configuration', 'release'], ['--configuration=release'])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            current = root / 'custom scratch/Release/codecov/Package.json'
            current.parent.mkdir(parents=True)
            current.write_text(json.dumps({'data': [{'functions': [{'name': 'First', 'count': 1},
                                                                     {'name': 'Second', 'count': 1}]}]}))
            for index, flags in enumerate(options):
                command = ['xcrun', 'swift', 'test', '--enable-code-coverage', *flags]
                output = root / f'coverage-{index}.json'
                with self.subTest(flags=flags), patch('lang_swift.sys.platform', 'darwin'):
                    commands = coverage_commands(root, root, command)
                    self.assertEqual(commands[0], command)
                    self.assertEqual(commands[1][4:], command)
                def locate_report(argv, **kwargs):
                    self.assertEqual(argv, [*command, '--show-codecov-path'])
                    self.assertEqual(kwargs, {'cwd': root, 'capture_output': True,
                                              'text': True, 'check': True})
                    return subprocess.CompletedProcess(argv, 0, f'{current}\n', '')
                with patch('lang_swift.subprocess.run', side_effect=locate_report) as run:
                    export_coverage(root, output, command)
                run.assert_called_once()
                self.assertEqual(output.read_bytes(), current.read_bytes())

    def test_default_copies_complete_report_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'Package.json'
            source.write_text('{"type":"llvm.coverage.json.export","data":[{},{}]}')
            output = root / 'coverage.json'
            result = subprocess.CompletedProcess([], 0, str(source), '')
            with patch('lang_swift.subprocess.run', return_value=result) as run:
                export_coverage(root, output)
                self.assertEqual(run.call_args.args[0], ['xcrun', 'swift', 'test', '--show-codecov-path'])
                self.assertEqual(output.read_bytes(), source.read_bytes())
                source.write_text('new report')
                with self.assertRaises(FileExistsError):
                    export_coverage(root, output)
                self.assertEqual(output.read_text(), '{"type":"llvm.coverage.json.export","data":[{},{}]}')

    def test_missing_report_and_invalid_native_options_fail_without_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root, output = Path(directory), Path(directory) / 'coverage.json'
            result = subprocess.CompletedProcess([], 0, str(root / 'missing.json'), '')
            with patch('lang_swift.subprocess.run', return_value=result):
                with self.assertRaises(FileNotFoundError):
                    export_coverage(root, output)
            for flags in (['--configuration'], ['--configuration=invalid'], ['--scratch-path']):
                command = ['swift', 'test', '--enable-code-coverage', *flags]
                with self.subTest(flags=flags), patch('lang_swift.subprocess.run',
                        side_effect=subprocess.CalledProcessError(64, command)) as run:
                    with self.assertRaises(subprocess.CalledProcessError):
                        export_coverage(root, output, command)
                    self.assertEqual(run.call_args.args[0], [*command, '--show-codecov-path'])
                    self.assertFalse(output.exists())

    def test_direct_test_overrides_require_new_coverage_measurement(self):
        commands = (['swift', 'test'], ['xcrun', 'swift', 'test', '-c', 'release'],
                    ['swift', 'test', '--enable-code-coverage', '--disable-code-coverage'])
        with patch('lang_swift.sys.platform', 'darwin'):
            for command in commands:
                with self.subTest(command=command), self.assertRaisesRegex(ValueError, '--enable-code-coverage'):
                    coverage_commands(Path('/project'), Path('/evidence'), command)
            for option in ('--show-codecov-path', '--show-code-coverage-path', '--show-coverage-path'):
                with self.subTest(option=option), self.assertRaisesRegex(ValueError, 'requires a test run'):
                    coverage_commands(Path('/project'), Path('/evidence'),
                                      ['swift', 'test', '--enable-code-coverage', option])

    def test_direct_swift_and_wrapper_commands_preserve_arguments(self):
        with patch('lang_swift.sys.platform', 'darwin'):
            command = ['/toolchain/swift', 'test', '--enable-code-coverage', '--configuration=release']
            commands = coverage_commands(Path('/project'), Path('/evidence'), command)
            self.assertEqual(commands[0], command)
            self.assertEqual(commands[1][4:], command)
            for command in (['custom'], ['python', '-c', 'collect_coverage()'],
                            ['wrapper', 'swift', 'test', '-c', 'release']):
                with self.subTest(command=command):
                    self.assertEqual(coverage_commands(Path('/project'), Path('/evidence'), command), [command])


if __name__ == '__main__':
    unittest.main()
