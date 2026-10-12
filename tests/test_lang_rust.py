"""Rust exclusion boundaries and bounded nightly discovery."""
from contextlib import redirect_stderr
import io
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/workflow/scripts'
sys.path.insert(0, str(SCRIPTS))
import lang_rust
from shared_crap import collect
from shared_runner import run_command


class RustCoverageTests(unittest.TestCase):
    def test_production_declarations_before_and_after_external_test_module(self):
        code = ('use std::cmp;\n'
                '#[cfg(test)]\nmod tests;\n'
                'const LIMIT: i32 = 1;\n'
                'pub fn production(value: i32) -> i32 {\n'
                '    if value > LIMIT { cmp::min(value, 5) } else { 0 }\n}\n')
        with tempfile.TemporaryDirectory() as directory:
            source = (Path(directory) / 'lib.rs').resolve()
            source.write_text(code, encoding='utf-8')
            self.assertEqual(lang_rust.exclude_tests(source, code), [(2, 3)])
            measured = collect({source: {'lines': {5: 1, 6: 1},
                                        'branches': {(6, '0', '0'): 1, (6, '0', '1'): 0}}},
                               [source], lang_rust.exclude_tests)
        self.assertEqual([function['name'] for function in measured['functions']], ['production'])
        self.assertEqual(measured['coverage'], {'line': {'covered': 2, 'total': 2},
                                              'branch': {'covered': 1, 'total': 2}})

    def test_probe_entrypoint_preserves_nightly_diagnostic_and_failure_status(self):
        version = subprocess.CompletedProcess([], 0, 'rustc nightly', '')
        with patch('lang_rust.subprocess.run', return_value=version):
            runpy.run_module('lang_rust', run_name='__main__')
        for result in (subprocess.CompletedProcess([], 0, 'rustc stable', ''), OSError('missing compiler')):
            with self.subTest(result=result), patch('lang_rust.subprocess.run', side_effect=[result]), \
                    redirect_stderr(io.StringIO()) as stderr, self.assertRaises(SystemExit) as raised:
                runpy.run_module('lang_rust', run_name='__main__')
            self.assertEqual(raised.exception.code, 2)
            self.assertIn('Rust coverage:', stderr.getvalue())
            if isinstance(result, subprocess.CompletedProcess):
                self.assertIn('Rust CRAP check requires a nightly toolchain for branch coverage', stderr.getvalue())
            else:
                self.assertIn('missing compiler', stderr.getvalue())

    def test_nested_test_attributes_preserve_outer_aggregate_exclusion(self):
        code = ('pub fn production(value: bool) -> i32 {\n'
                '    if value { 1 } else { 0 }\n}\n'
                '#[cfg(test)]\nmod tests {\n'
                '    fn outer(value: bool) {\n'
                '        if value { assert!(true); }\n    }\n'
                '    #[cfg(test)]\n    mod inner {\n'
                '        fn nested() {}\n    }\n'
                '    #[cfg(test)]\n    mod external;\n'
                '    fn after() {}\n}\n'
                'pub fn last(value: bool) -> i32 {\n'
                '    if value { 1 } else { 0 }\n}\n')
        with tempfile.TemporaryDirectory() as directory:
            source = (Path(directory) / 'lib.rs').resolve()
            source.write_text(code, encoding='utf-8')
            hits = {'lines': {1: 1, 2: 1, 6: 0, 7: 0, 11: 0, 15: 0, 17: 1, 18: 1},
                    'branches': {(2, '0', '0'): 1, (2, '0', '1'): 1,
                                 (7, '0', '0'): 0, (7, '0', '1'): 0,
                                 (18, '0', '0'): 1, (18, '0', '1'): 1}}
            measured = collect({source: hits}, [source], lang_rust.exclude_tests)
        self.assertEqual(lang_rust.exclude_tests(source, code), [(4, 16)])
        self.assertEqual([function['name'] for function in measured['functions']], ['production', 'last'])
        self.assertEqual(measured['coverage'], {'line': {'covered': 4, 'total': 4},
                                              'branch': {'covered': 4, 'total': 4}})

    @unittest.skipUnless(os.name == 'posix', 'Executable probe and POSIX process group')
    def test_script_entrypoint_blocked_nightly_probe_times_out_and_stops_its_process(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            started = root / 'probe-entered'
            marker = root / 'probe-survived'
            rustc = root / 'rustc'
            rustc.write_text(f'#!{sys.executable}\n'
                             'import time\nfrom pathlib import Path\n'
                             f'Path({str(started)!r}).touch()\n'
                             'time.sleep(3)\n'
                             f'Path({str(marker)!r}).touch()\n'
                             'print("rustc nightly")\n', encoding='utf-8')
            rustc.chmod(0o755)
            with patch.dict(os.environ, {'PATH': str(root) + os.pathsep + os.environ['PATH']}), \
                    tempfile.TemporaryFile(mode='w+') as stderr, redirect_stderr(stderr):
                command = lang_rust.coverage_commands(root, root, [sys.executable, '-c', 'pass'])[0]
                with self.assertRaisesRegex(ValueError, '^Tool exceeded timeoutMs$'):
                    run_command(command, root, 1500)
            self.assertTrue(started.exists(), 'rustc probe did not start before the timeout')
            time.sleep(3)
            self.assertFalse(marker.exists(), 'Timed-out rustc probe kept running')
