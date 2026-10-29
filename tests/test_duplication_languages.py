"""Multi-language duplication through the public entry point, with the real tree-sitter grammars."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/workflow/scripts'))
import duplication

JS = ('function first(items) {\n  let total = 0;\n  for (const item of items) {\n    total += item.price;\n'
      '  }\n  return Math.round(total);\n}\n')
RUST = ('fn first(items: Vec<i32>) -> i32 {\n    let mut total = 0;\n    for item in items {\n        total += item;\n'
        '    }\n    total.abs()\n}\n')


def renamed(source):
    return (source.replace('first', 'second').replace('items', 'values').replace('item', 'value')
            .replace('total', 'sum_').replace('price', 'cost').replace('0', '10'))


class LanguageDuplicationTests(unittest.TestCase):
    def check(self, language, files):
        with tempfile.TemporaryDirectory() as directory:
            for name, text in files.items():
                (Path(directory) / name).write_text(text, encoding='utf-8')
            with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()) as err:
                code = duplication.main([language, directory, *files])
            lines = err.getvalue().splitlines()
            evidence = Path(lines[0].removeprefix('Evidence: ')) if lines and lines[0].startswith('Evidence: ') else None
            measurements = json.loads((evidence / 'measurements.json').read_bytes()) if code != 2 and language != 'swift' else []
            config = json.loads((evidence / 'config.json').read_bytes()) if evidence else None
            stored = json.loads((evidence / 'result.json').read_bytes()) if code != 2 else None
            result = json.loads(out.getvalue()) if out.getvalue() else None
            self.assertEqual(stored, result)
            return code, result, err.getvalue(), measurements, config

    def test_renamed_copies_report_language_score_and_both_spans(self):
        for language, name, source, label in [('js', 'a.js', JS, 'typescript'), ('js', 'a.jsx', JS, 'typescript'),
                                              ('js', 'a.mjs', JS, 'typescript'), ('js', 'a.cjs', JS, 'typescript'),
                                              ('ts', 'a.ts', JS, 'typescript'), ('ts', 'a.tsx', JS, 'typescript'),
                                              ('rust', 'a.rs', RUST, 'rust')]:
            with self.subTest(name=name):
                code, result, error, _, _ = self.check(language, {name: source + renamed(source)})
                self.assertEqual(code, 1, error)
                self.assertEqual(result['pairs'], [{'language': label, 'score': 1.0,
                                                    'left': {'file': name, 'startLine': 1, 'endLine': 7},
                                                    'right': {'file': name, 'startLine': 8, 'endLine': 14}}])

    def test_structurally_different_functions_and_other_languages_are_not_paired(self):
        other = 'function other(a) {\n  try {\n    return JSON.parse(a);\n  } catch (e) {\n    throw new Error(e);\n  }\n}\n'
        code, result, _, _, _ = self.check('js', {'a.js': JS + other})
        self.assertEqual((code, result['pairs']), (0, []))

    def test_js_candidates_are_top_level_functions_methods_and_function_assignments(self):
        source = ('class K {\n  m(a) { return a; }\n  handler = (a) => { return a; };\n  value = 1;\n}\n'
                  'const g = function (a) { return a; };\n'
                  'const h = (a) => { return a; };\n'
                  'const n = 1;\n'
                  'function outer() {\n  const inner = () => { return 1; };\n  return [1].map(function (x) { return x; });\n}\n')
        _, _, error, measurements, _ = self.check('js', {'a.js': source})
        self.assertEqual([(m['startLine'], m['endLine']) for m in measurements], [(2, 2), (3, 3), (6, 6), (7, 7), (9, 12)], error)

    def test_tsx_uses_the_tsx_grammar_and_ts_keeps_type_assertions(self):
        self.assertEqual(self.check('ts', {'a.tsx': 'const C = () => { return <div>{1}</div>; };\n'})[0], 0)
        self.assertEqual(self.check('ts', {'a.ts': 'const f = (x) => { return <number>x; };\n'})[0], 0)
        code, _, error, _, _ = self.check('ts', {'a.tsx': 'const f = (x) => { return <number>x; };\n'})
        self.assertEqual(code, 2)
        self.assertIn('Duplication: Unparseable typescript source: ', error)

    def test_js_normalization_keeps_called_names_and_operators_but_drops_locals_fields_literals_and_comments(self):
        source = ('function f(items) {\n  // note\n  const seen = new Map();\n  let total = 0;\n'
                  '  for (const item of items) { total += item.price * 2; }\n'
                  "  return Math.round(total) + /x/.test('s') + seen.size + config?.load(1);\n}\n")
        _, _, _, (entry,), _ = self.check('js', {'a.js': source})
        prints = entry['fingerprints']
        for kept in ['[":symbol" "Map"]', '[":symbol" "round"]', '[":symbol" "test"]', '[":symbol" "+="]',
                     '[":symbol" "load"]',
                     '[":symbol" "*"]', '[":member_expression" ":symbol" [":symbol" "round"]]',
                     '[":member_expression" ":symbol" ":symbol"]', '":literal"']:
            self.assertIn(kept, prints)
        for dropped in ('"total"', '"items"', '"price"', '"note"', '"Math"', '"size"', 'comment', '"x"', '"s"'):
            self.assertFalse([p for p in prints if dropped in p], dropped)

    def test_rust_candidates_exclude_bodiless_nested_closure_and_test_module_functions(self):
        source = ('fn top(a: i32) -> i32 {\n    fn nested(b: i32) -> i32 { b }\n    let c = |x: i32| x + 1;\n'
                  '    nested(c(a))\n}\n'
                  'impl S {\n    fn method(&self) -> i32 { 1 }\n}\n'
                  'trait T {\n    fn required(&self);\n    fn provided(&self) -> i32 { 2 }\n}\n'
                  'mod tests {\n    fn t() {}\n}\n'
                  'mod other {\n    fn kept() {}\n}\n')
        _, _, error, measurements, _ = self.check('rust', {'a.rs': source})
        self.assertEqual([m['startLine'] for m in measurements], [1, 7, 11, 17], error)
        body = 'fn f(a: i32) -> i32 {\n    let b = a + 1;\n    let c = b.abs();\n    c\n}\n'
        code, _, _, _, _ = self.check('rust', {'a.rs': body + 'mod tests {\n' + body.replace('f(', 'g(') + '}\n'})
        self.assertEqual(code, 0)

    def test_rust_normalization_keeps_paths_and_methods_but_drops_locals_fields_and_literals(self):
        source = ('fn f(a: i32) -> i32 {\n    // c\n    let b = std::cmp::max(a, \'x\' as i32);\n'
                  '    let s = Point { x: 1.5, y: "s" };\n    let d: core::time::Duration = s.d;\n'
                  '    b.abs() + s.x as i32\n}\n')
        _, _, _, (entry,), _ = self.check('rust', {'a.rs': source})
        prints = entry['fingerprints']
        for kept in ['[":symbol" "std"]', '[":symbol" "cmp"]', '[":symbol" "max"]', '[":symbol" "abs"]',
                     '[":symbol" "+"]', '[":field_expression" ":symbol" ":symbol"]', '":literal"']:
            self.assertIn(kept, prints)
        for dropped in ('"b"', '"a"', '"Point"', '"x"', 'comment', '"i32"', '"core"', '"time"', '"Duration"'):
            self.assertFalse([p for p in prints if dropped in p], dropped)

    def test_swift_reports_an_unverified_gap_that_never_passes(self):
        code, result, error, _, config = self.check('swift', {'a.swift': 'func f() {}'})
        self.assertEqual(code, 1, error)
        self.assertEqual(result, {'findings': 0, 'pairs': [], 'sources': ['a.swift'], 'unverified': 'language not supported'})
        self.assertEqual([t['name'] for t in config['tools']], ['tree-sitter', 'tree-sitter-language-pack'])
        evidence = Path(error.splitlines()[0].removeprefix('Evidence: '))
        self.assertEqual({path.name for path in evidence.iterdir()}, {'config.json', 'result.json'})

    def test_unparseable_and_wrong_language_sources_are_run_failures(self):
        for language, name, message in [('js', 'a.js', 'Unparseable typescript source: '),
                                        ('rust', 'a.rs', 'Unparseable rust source: '),
                                        ('js', 'a.ts', 'Unsupported source file: a.ts'),
                                        ('rust', 'a.py', 'Unsupported source file: a.py')]:
            with self.subTest(name=name):
                code, result, error, _, _ = self.check(language, {name: 'fn function ((( {'})
                self.assertEqual((code, result), (2, None))
                self.assertIn('Duplication: ' + message, error)


if __name__ == '__main__':
    unittest.main()
