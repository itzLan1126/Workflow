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
from shared_crap import calculate, collect
from shared_runner import run_command


class RustCoverageTests(unittest.TestCase):
    def test_long_unsupported_declaration_is_rejected_without_parser_hang(self):
        code = ('#[cfg(test)]\ntype ' + 'A' * 64 + ' = fn();\n'
                'pub fn production() {}\n')
        probe = (f'import sys; sys.path.insert(0, {str(SCRIPTS)!r}); '
                 'import lang_rust\n'
                 'try:\n'
                 f'    lang_rust.exclude_tests("lib.rs", {code!r})\n'
                 'except ValueError as error:\n'
                 '    assert str(error).startswith("Unsupported Rust test declaration")\n'
                 'else:\n'
                 '    raise AssertionError("Unsupported declaration was accepted")\n')
        result = subprocess.run([sys.executable, '-c', probe], capture_output=True, text=True, timeout=3)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bom_and_raw_identifiers_and_c_strings_preserve_exclusion(self):
        declarations = ('#[cfg(test)]\nfn r#type() {}',
                        '#[cfg(test)]\nmod r#type { fn helper() {} }',
                        '#[cfg(test)]\nfn helper() { let _ = cr#"quoted } value"#; }')
        for declaration in declarations:
            with self.subTest(declaration=declaration), tempfile.TemporaryDirectory() as directory:
                code = '\ufeff' + declaration + '\npub fn production(flag: bool) -> i32 {\n if flag { 1 } else { 0 }\n}\n'
                source = (Path(directory) / 'lib.rs').resolve()
                source.write_text(code, encoding='utf-8')
                first = declaration.count('\n') + 2
                hits = {'lines': dict.fromkeys(range(first, first + 3), 1),
                        'branches': {(first + 1, '0', '0'): 1, (first + 1, '0', '1'): 1}}
                result = calculate(collect({source: hits}, [source], lang_rust.exclude_tests))
                self.assertEqual([function['name'] for function in result['functions']], ['production'])
                self.assertEqual(result['findings'], 0)
                self.assertEqual(''.join(lang_rust.rust_tokens(source, code)), code)

    def test_nested_block_comments_preserve_test_ranges_and_line_numbers(self):
        for comment in ('/* outer /* inner */ } "quoted" */',
                        '/* outer\n /* inner */\n } "quoted" */'):
            with self.subTest(comment=comment), tempfile.TemporaryDirectory() as directory:
                prefix = comment + '\n'
                test_code = ('#[cfg(test)]\nmod tests {\n'
                             f'    {comment}\n'
                             '    fn helper() {}\n} ' + comment + '\n')
                code = (prefix + test_code + 'pub fn production(flag: bool) -> i32 {\n'
                        '    if flag { 1 } else { 0 }\n}\n')
                source = (Path(directory) / 'lib.rs').resolve()
                source.write_text(code, encoding='utf-8')
                start = prefix.count('\n') + 1
                end = start + test_code[:test_code.index('} ' + comment)].count('\n')
                self.assertEqual(lang_rust.exclude_tests(source, code), [(start, end)])
                self.assertEqual(''.join(lang_rust.rust_tokens(source, code)), code)
                production = (prefix + test_code).count('\n') + 1
                hits = {'lines': {production: 1, production + 1: 1, production + 2: 1},
                        'branches': {(production + 1, '0', '0'): 1,
                                     (production + 1, '0', '1'): 1}}
                result = calculate(collect({source: hits}, [source], lang_rust.exclude_tests))
                self.assertEqual([function['name'] for function in result['functions']], ['production'])
                self.assertEqual(result['findings'], 0)

    def test_comment_delimiters_in_literals_do_not_open_comments(self):
        code = ('#[cfg(test)]\nmod tests {\n'
                '    fn helper() { let _ = ("/* outer /* inner */", r#"/* /*"#, br#"/*"#, \'/\'); }\n}\n'
                'pub fn production() {}\n')
        self.assertEqual(lang_rust.exclude_tests('lib.rs', code), [(1, 4)])
        self.assertEqual(''.join(lang_rust.rust_tokens('lib.rs', code)), code)

    def test_nested_comments_with_unmatched_quotes_do_not_swallow_code(self):
        code = ('/* outer /* inner */ } " */\n'
                '#[cfg(test)]\nmod tests { fn helper() {} } /* outer /* inner */ } " */\n'
                'pub fn production() {}\n')
        self.assertEqual(lang_rust.exclude_tests('lib.rs', code), [(2, 3)])
        self.assertEqual(''.join(lang_rust.rust_tokens('lib.rs', code)), code)

    def test_unclosed_block_comments_fail_closed_without_overlapping_delimiters(self):
        for comment in ('/* unclosed', '/* outer /* inner */', '/*/'):
            with self.subTest(comment=comment), self.assertRaisesRegex(ValueError, 'Unclosed Rust block comment'):
                lang_rust.exclude_tests('lib.rs', f'#[cfg(test)]\nmod tests {{ fn helper() {{}} }} {comment}')

    def test_nested_attribute_tokens_and_default_function_qualifier(self):
        declarations = ('#[cfg(test)]\n#[doc = stringify!(#[inner])]\nfn helper() {}',
                        '#[doc = stringify!(#[inner])] #[cfg(test)]\nfn helper() {}',
                        '#[cfg(test)]\ngen fn helper() -> i32 { yield 1; }',
                        '#[cfg(test)]\nasync gen fn helper() -> i32 { yield 1; }',
                        'trait Demo { fn value() {} }\nimpl<T> Demo for T {\n'
                        '    #[cfg(test)]\n    default fn value() {}\n}')
        for declaration in declarations:
            with self.subTest(declaration=declaration), tempfile.TemporaryDirectory() as directory:
                code = ('pub fn production(flag: bool) -> i32 {\n'
                        '    if flag { 1 } else { 0 }\n}\n' + declaration + '\n')
                source = (Path(directory) / 'lib.rs').resolve()
                source.write_text(code, encoding='utf-8')
                hits = {'lines': {1: 1, 2: 1, 3: 1, 4: 1},
                        'branches': {(2, '0', '0'): 1, (2, '0', '1'): 1}}
                result = calculate(collect({source: hits}, [source], lang_rust.exclude_tests))
                self.assertEqual(result['findings'], 0)
                self.assertIn('production', [function['name'] for function in result['functions']])

    def test_raw_abi_and_safe_extern_function_qualifiers_preserve_exclusion(self):
        declarations = ('#[cfg(test)]\nextern r"C" fn helper() {}',
                        '#[cfg(test)]\nextern r##"C"## fn helper() {}',
                        '#[cfg(test)]\nextern/**/r#"C"# fn helper() {}',
                        '#[cfg(test)]\nextern/* comment\n */r##"C"## fn helper() {}',
                        'unsafe extern "C" {\n    #[cfg(test)]\n    safe fn helper();\n}')
        for declaration in declarations:
            with self.subTest(declaration=declaration), tempfile.TemporaryDirectory() as directory:
                code = ('pub fn production(flag: bool) -> i32 {\n'
                        '    if flag { 1 } else { 0 }\n}\n' + declaration + '\n')
                source = (Path(directory) / 'lib.rs').resolve()
                source.write_text(code, encoding='utf-8')
                hits = {'lines': {1: 1, 2: 1, 3: 1},
                        'branches': {(2, '0', '0'): 1, (2, '0', '1'): 1}}
                result = calculate(collect({source: hits}, [source], lang_rust.exclude_tests))
                self.assertEqual([function['name'] for function in result['functions']], ['production'])
                self.assertEqual(result['findings'], 0)

    def test_attributes_before_cfg_and_on_generic_parameters_preserve_exclusion(self):
        declarations = (
            '#[allow(dead_code)] #[cfg(test)]\nfn helper() {}',
            '#[\n allow(dead_code)\n] #[cfg(test)]\nfn helper() {}',
            '#[cfg(test)]\nfn helper<#[allow(unused)] T>() {}',
            '#[cfg(test)] fn first() {} #[cfg(test)]\nfn helper() {}',
        )
        for declaration in declarations:
            with self.subTest(declaration=declaration), tempfile.TemporaryDirectory() as directory:
                code = ('pub fn production(flag: bool) -> i32 {\n'
                        '    if flag { 1 } else { 0 }\n}\n' + declaration + '\n')
                source = (Path(directory) / 'lib.rs').resolve()
                source.write_text(code, encoding='utf-8')
                hits = {'lines': {1: 1, 2: 1, 3: 1},
                        'branches': {(2, '0', '0'): 1, (2, '0', '1'): 1}}
                result = calculate(collect({source: hits}, [source], lang_rust.exclude_tests))
                self.assertEqual([function['name'] for function in result['functions']], ['production'])
                self.assertEqual(result['findings'], 0)

    def test_lifetimes_attributes_and_const_expressions_preserve_test_exclusion(self):
        declarations = ("fn helper<'a>(x: &'a str) -> &'a str { x }",
                        "fn helper(x: &'static str) -> &'static str { x }",
                        '#[\n    allow(dead_code)\n]\nfn helper() {}',
                        '#[allow(\n    dead_code\n)]\nfn helper() {}',
                        'fn helper() -> [u8; (1 << 3)] { [0; 8] }',
                        'fn helper() -> [u8; ((1 < 3) as usize)] { [0; 1] }',
                        'fn helper() -> [u8; (64 >> 3)] { [0; 8] }',
                        "fn helper() -> [u8; ('a' as usize)] { [0; 97] }")
        for declaration in declarations:
            with self.subTest(declaration=declaration), tempfile.TemporaryDirectory() as directory:
                code = ('pub fn production(flag: bool) -> i32 {\n'
                        '    if flag { 1 } else { 0 }\n}\n'
                        f'#[cfg(test)]\n{declaration}\n')
                source = (Path(directory) / 'lib.rs').resolve()
                source.write_text(code, encoding='utf-8')
                self.assertEqual(lang_rust.exclude_tests(source, code), [(4, len(code.splitlines()))])
                hits = {'lines': {1: 1, 2: 1, 3: 1},
                        'branches': {(2, '0', '0'): 1, (2, '0', '1'): 1}}
                report = calculate(collect({source: hits}, [source], lang_rust.exclude_tests))
                self.assertEqual([function['name'] for function in report['functions']], ['production'])
                self.assertEqual(report['findings'], 0)

    def test_char_literals_are_not_lifetimes(self):
        code = ('#[cfg(test)]\nmod tests {\n'
                '    fn helper() { let _ = (\'a\', \'é\', \'{\', \'}\', \'\\\'\'); }\n}\n'
                'pub fn production() {}\n')
        self.assertEqual(lang_rust.exclude_tests('lib.rs', code), [(1, 4)])

    def test_shared_test_boundary_lines_cannot_hide_complex_production(self):
        complex_body = ('if value == 0 { 0 } else if value == 1 { 1 } '
                        'else if value == 2 { 2 } else if value == 3 { 3 } '
                        'else if value == 4 { 4 } else if value == 5 { 5 } else { 6 }')
        complex_function = f'pub fn complex(value: i32) -> i32 {{ {complex_body} }}'
        for declarations in ('#[cfg(test)]\nmod tests {\n    fn t() {}\n} ' + complex_function,
                             '#[cfg(test)]\nmod tests; ' + complex_function,
                             complex_function + ' #[cfg(test)]\nmod tests { fn t() {} }'):
            with self.subTest(declarations=declarations), tempfile.TemporaryDirectory() as directory:
                code = ('pub fn covered(flag: bool) -> i32 {\n'
                        '    if flag { 1 } else { 0 }\n}\n' + declarations + '\n')
                source = (Path(directory) / 'lib.rs').resolve()
                source.write_text(code, encoding='utf-8')
                hits = {'lines': {line: 1 for line in range(1, len(code.splitlines()) + 1)},
                        'branches': {(2, '0', '0'): 1, (2, '0', '1'): 1}}
                self.assertGreater(calculate(collect({source: hits}, [source]))['findings'], 0)
                with self.assertRaisesRegex(ValueError, 'Ambiguous Rust test boundary'):
                    calculate(collect({source: hits}, [source], lang_rust.exclude_tests))

    def test_test_boundary_comments_are_allowed(self):
        code = ('/* before\n */ #[cfg(test)] /* attribute comment */\n'
                'mod tests { fn helper() {} } /* after\n */ // comment\n'
                'pub fn production() {}\n')
        self.assertEqual(lang_rust.exclude_tests('lib.rs', code), [(2, 3)])

    def test_raw_strings_preserve_test_range_and_production_complexity(self):
        for literal in ('r"}"', 'br"{"', 'r#"value"#', 'br##"internal \" quote }"##',
                        'r##"incomplete "# delimiter {"##',
                        'r#"{\n "value": "}",\n "more": "}"\n}"#'):
            with self.subTest(literal=literal), tempfile.TemporaryDirectory() as directory:
                test_code = ('#[cfg(test)]\nmod tests {\n    fn helper() {\n'
                             f'        let _ = {literal};\n'
                             '        let _ = "r#\\\"}\\\"#";\n'
                             '        // r#"{"#\n        /* br#"}"# */\n    }\n}\n')
                code = (test_code + 'pub fn production(value: i32) -> i32 {\n'
                        '    if value == 0 { 0 } else if value == 1 { 1 }\n'
                        '    else if value == 2 { 2 } else if value == 3 { 3 }\n'
                        '    else if value == 4 { 4 } else if value == 5 { 5 } else { 6 }\n}\n')
                source = (Path(directory) / 'lib.rs').resolve()
                source.write_text(code, encoding='utf-8')
                end = test_code.count('\n')
                self.assertEqual(lang_rust.exclude_tests(source, code), [(1, end)])
                hits = {'lines': {line: 1 for line in range(end + 1, end + 6)},
                        'branches': {(end + 2, '0', '0'): 1, (end + 2, '0', '1'): 1}}
                measured = collect({source: hits}, [source], lang_rust.exclude_tests)
                self.assertEqual([function['name'] for function in measured['functions']], ['production'])
                self.assertGreater(calculate(measured)['findings'], 0)

    def test_inline_test_function_raw_strings_preserve_closing_braces(self):
        code = ('#[cfg(test)]\nmod tests {\n'
                '    fn helper() { assert_eq!(r#"value"#, "value"); }\n}\n'
                'pub fn production() {}\n')
        self.assertEqual(lang_rust.exclude_tests('lib.rs', code), [(1, 4)])

    def test_unsupported_test_declarations_cannot_hide_production_coverage(self):
        for declaration in ('tracked: bool,', 'tracked: bool',
                            'tracked: Result<(bool, bool), Error>,',
                            'tracked: fn(bool, bool) -> bool,',
                            'tracked: [bool; { count(1, 2) }],'):
            with self.subTest(declaration=declaration), tempfile.TemporaryDirectory() as directory:
                code = ('pub fn first(value: bool) -> i32 {\n'
                        '    if value { 1 } else { 0 }\n}\n'
                        'struct State {\n    #[cfg(test)]\n'
                        f'    {declaration}\n}}\n'
                        'pub fn production(value: bool) -> i32 {\n'
                        '    if value { 1 } else { 0 }\n}\n')
                source = (Path(directory) / 'lib.rs').resolve()
                source.write_text(code, encoding='utf-8')
                hits = {'lines': {1: 1, 2: 1, 8: 0, 9: 0},
                        'branches': {(2, '0', '0'): 1, (2, '0', '1'): 1,
                                     (9, '0', '0'): 0, (9, '0', '1'): 0}}
                with self.assertRaisesRegex(ValueError, 'Unsupported Rust test declaration'):
                    calculate(collect({source: hits}, [source], lang_rust.exclude_tests))

    def test_test_functions_preserve_signature_delimiters_and_following_production(self):
        for signature in ('pub(crate) const fn test() -> [bool; { 1 + 2 }]',
                          'pub async unsafe extern "C" fn test()',
                          'fn test<T>() -> Wrapper<{ 2 > 1 }>'):
            with self.subTest(signature=signature):
                code = ('#[cfg(test)]\n#[allow(dead_code)]\n'
                        f'{signature} {{\n    todo!()\n}}\n'
                        'pub fn production(value: bool) -> i32 {\n'
                        '    if value { 1 } else { 0 }\n}\n')
                self.assertEqual(lang_rust.exclude_tests('lib.rs', code), [(1, 5)])

    def test_invalid_test_declarations_fail_closed(self):
        for declaration, message in (('struct Empty;', 'Unsupported Rust test declaration'),
                                     ('fn missing_body()', 'Unclosed Rust test declaration'),
                                     ('fn unclosed() {', 'Unclosed Rust test declaration'),
                                     ('fn mismatched(]', 'Unbalanced Rust test declaration'),
                                     ('fn unmatched)', 'Unbalanced Rust test declaration')):
            with self.subTest(declaration=declaration), self.assertRaisesRegex(ValueError, message):
                lang_rust.exclude_tests('lib.rs', f'#[cfg(test)]\n{declaration}')

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
