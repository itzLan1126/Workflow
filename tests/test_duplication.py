"""Duplication behaviour through its entry point, with the real Python parser."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/workflow/scripts'))
import duplication


class DuplicationTests(unittest.TestCase):
    def run_check(self, files, options=()):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            for name, text in files.items():
                (project / name).write_bytes(text.encode())
            with redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as stderr:
                code = duplication.main(['python', directory, *files, *options])
            evidence_lines = stderr.getvalue().splitlines()
            evidence = Path(evidence_lines[0].removeprefix('Evidence: '))
            config = json.loads((evidence / 'config.json').read_bytes())
            self.assertEqual(config['cwd'], str(project.resolve()))
            self.assertEqual({p.name for p in evidence.iterdir()} - {'result.json', 'measurements.json'}, {'config.json'})
            result = json.loads(stdout.getvalue()) if stdout.getvalue() else None
            if result is not None:
                self.assertEqual(json.loads((evidence / 'result.json').read_bytes()), result)
            return code, result, config, stderr.getvalue(), evidence

    def test_renamed_copies_report_score_language_spans_and_fresh_evidence(self):
        first = 'def first(items):\n    total = 0\n    for item in items:\n        total += item.price\n    return round(total)\n'
        second = first.replace('first', 'second').replace('items', 'values').replace('item', 'value').replace('total', 'sum_').replace('price', 'cost').replace('0', '100')
        code, result, config, _, evidence = self.run_check({'a.py': first, 'b.py': second})
        self.assertEqual(code, 1)
        self.assertEqual(result['findings'], 1)
        self.assertEqual(result['pairs'], [{'language': 'python', 'score': 1.0,
                                          'left': {'file': 'a.py', 'startLine': 1, 'endLine': 5},
                                          'right': {'file': 'b.py', 'startLine': 1, 'endLine': 5}}])
        self.assertEqual(config['sources'], ['a.py', 'b.py'])
        self.assertEqual(result['sources'], config['sources'])
        self.assertEqual(result['parserVersions'], {'tree-sitter': '0.25.2', 'tree-sitter-language-pack': '0.9.0'})
        self.assertEqual(config['parserVersions'], result['parserVersions'])
        self.assertNotEqual(self.run_check({'a.py': first})[-1], evidence)

    def test_distinct_structure_and_small_functions_pass(self):
        text = ('def total(items):\n    result = 0\n    for item in items:\n        result += item.price\n    return round(result)\n\n'
                'def handle(value):\n    try:\n        return open(value).read()\n    except OSError:\n        raise ValueError(value)\n\n'
                'def small(a):\n    return a + 1\n\n'
                'def tiny(b):\n    return b + 2\n\n'
                'def few_nodes():\n    pass\n    pass\n    pass\n\n'
                'def also_few():\n    pass\n    pass\n    pass\n')
        code, result, _, _, _ = self.run_check({'a.py': text})
        self.assertEqual(code, 0)
        self.assertEqual(result['pairs'], [])
        self.assertEqual(result['findings'], 0)

    def test_invalid_source_and_unsupported_extension_fail_closed(self):
        for name, text in [('a.py', 'def broken(:\n'), ('a.py', 'def f():\n    x =\n'),
                           ('a.js', 'function f() {}'), ('a.py', '\x00')]:
            with self.subTest(text=text):
                code, result, _, error, _ = self.run_check({name: text})
                self.assertEqual(code, 2, error)
                self.assertIsNone(result)
                expected = f'Unsupported source file: {name}' if name.endswith('.js') else 'Unparseable Python source: '
                self.assertIn('Duplication: ' + expected, error)

    def test_policy_flags_configs_and_tool_override_are_rejected(self):
        for option in ['--threshold', '--min-lines', '--min-nodes']:
            with self.subTest(option=option):
                with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
                    self.assertEqual(duplication.main(['python', '.', 'a.py', option, '0']), 2)
                self.assertEqual(out.getvalue(), '')
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'config.json'
            for policy in ['threshold', 'minLines', 'minNodes']:
                config.write_text(json.dumps({'cwd': directory, 'sources': ['a.py'], policy: 0}))
                with redirect_stderr(io.StringIO()) as error:
                    self.assertEqual(duplication.main([str(config)]), 2)
                self.assertEqual(error.getvalue(), 'Duplication: Usage: duplication.py python PROJECT SOURCE_FILE...; only Python is supported\n')
        cases = [(['python', '.', 'a.py', '--', 'anything'], 'Require source files; tool overrides are not supported'),
                 (['python', '.'], 'Require source files; tool overrides are not supported'),
                 (['python', '.', 'a.py', '--timeout-ms', '100'], 'Duplication check does not accept timeout overrides'),
                 ([], 'Usage: duplication.py python PROJECT SOURCE_FILE...; only Python is supported'),
                 (['swift', '.', 'a.swift'], 'Usage: duplication.py python PROJECT SOURCE_FILE...; only Python is supported')]
        for args, message in cases:
            with redirect_stderr(io.StringIO()) as error:
                self.assertEqual(duplication.main(args), 2)
            self.assertEqual(error.getvalue(), 'Duplication: ' + message + '\n')

    def test_missing_parser_packages_fail_closed(self):
        from unittest.mock import patch
        for name in ['tree_sitter', 'tree_sitter_language_pack']:
            with self.subTest(package=name), patch.dict(sys.modules, {name: None}):
                code, result, _, error, _ = self.run_check({'a.py': 'def f():\n    pass\n'})
                self.assertEqual(code, 2, error)
                self.assertIsNone(result)

    def test_calls_and_operators_keep_their_names(self):
        template = ('def f(items):\n    output = []\n    for item in items:\n'
                    '        output.append(CALL(item) OP 1)\n    return output\n')
        for original, changed in [('abs', 'str'), ('append', 'extend'), ('+', '*'), ('abs', 'obj.abs')]:
            text = template.replace('CALL', 'abs').replace('OP', '+')
            other = text.replace('def f', 'def g').replace(original, changed)
            code, result, _, _, _ = self.run_check({'a.py': text, 'b.py': other})
            # Small structural edits may still clear 0.8, but never become exact copies.
            self.assertIn(code, (0, 1))
            for finding in result['pairs']:
                self.assertLess(finding['score'], 1.0)

    def test_nested_functions_are_excluded_and_class_methods_kept(self):
        text = ('def outer(items):\n    def nested(values):\n        result = 0\n'
                '        for value in values:\n            result += value\n        return result\n'
                '    return nested(items)\n\n'
                'class C:\n    def method(self, values):\n        result = 0\n'
                '        for value in values:\n            result += value\n        return result\n')
        code, result, _, _, _ = self.run_check({'a.py': text})
        self.assertEqual(code, 0)
        method = text[text.index('    def method'):]
        code, result, _, _, _ = self.run_check({'a.py': text, 'b.py': 'class D:\n' + method})
        self.assertEqual(code, 1)
        self.assertEqual(len(result['pairs']), 1)
        self.assertEqual(result['pairs'][0]['left']['startLine'], 10)

    def test_similarity_at_point_eight_is_a_finding(self):
        first = 'def f(a):\n    for b in a:\n        print(b)\n    a = (b, 1)\n    b = abs(a)\n    a += 1\n'
        second = 'def g(a):\n    for b in a:\n        print(b)\n    a += 1\n    b = abs(a)\n'
        code, result, _, _, _ = self.run_check({'a.py': first, 'b.py': second})
        self.assertEqual(code, 1)
        self.assertEqual(result['pairs'][0]['score'], 0.8)

    def test_minimum_lines_and_nodes_include_the_boundaries(self):
        for text, expected in [
            ('def f(a):\n    b = abs(a)\n    return b\n', 0),
            ('def f(a):\n    b = abs(a)\n    c = b\n    return c\n', 1),
            ('def f():\n    a\n    a\n    a.b\n', 0),
            ('def f():\n    pass\n    pass\n    a = 1\n', 1),
        ]:
            with self.subTest(text=text):
                code, result, _, _, _ = self.run_check({'a.py': text, 'b.py': text.replace('def f', 'def g')})
                self.assertEqual(code, expected)
                self.assertEqual(result['findings'], expected)

    def test_nested_class_methods_remain_candidates(self):
        method = '    def f(a):\n        b = 0\n        for c in a:\n            b += c\n        return b\n'
        text = 'def outer():\n    class C:\n' + ''.join('    ' + line + '\n' for line in method.splitlines()) + '    return C\n'
        code, result, _, _, _ = self.run_check({'a.py': text, 'b.py': 'class D:\n' + method})
        self.assertEqual(code, 1)
        self.assertTrue(any(p['left']['startLine'] == 3 for p in result['pairs']))

    def test_measurements_preserve_auditable_normalization_and_fingerprints(self):
        text = 'def f(a):\n    b = abs(a) + 1\n    return b\n'
        _, _, _, _, evidence = self.run_check({'a.py': text})
        measurements = json.loads((evidence / 'measurements.json').read_bytes())
        self.assertEqual(len(measurements), 1)
        entry = measurements[0]
        self.assertEqual(entry['file'], 'a.py')
        self.assertEqual(entry['language'], 'python')
        self.assertEqual(entry['startLine'], 1)
        self.assertEqual(entry['endLine'], 3)
        self.assertEqual(entry['nodes'], 33)
        self.assertEqual(entry['fingerprints'], sorted([
            '\":symbol\"', '\":literal\"', '\":function_definition\"', '\":parameters\"',
            '\":block\"', '\":expression_statement\"', '\":assignment\"', '\":binary_operator\"',
            '\":call\"', '\":argument_list\"', '\":return_statement\"', '\"abs\"', '\"+\"', '\"=\"',
            '[\":symbol\" \"abs\"]', '[\":symbol\" \"+\"]', '[\":symbol\" \"=\"]',
            '[\":parameters\" \":symbol\"]', '[\":argument_list\" \":symbol\"]',
            '[\":call\" [\":symbol\" \"abs\"] [\":argument_list\" \":symbol\"]]',
            '[\":binary_operator\" [\":call\" [\":symbol\" \"abs\"] [\":argument_list\" \":symbol\"]] [\":symbol\" \"+\"] \":literal\"]',
            '[\":assignment\" \":symbol\" [\":symbol\" \"=\"] [\":binary_operator\" [\":call\" [\":symbol\" \"abs\"] [\":argument_list\" \":symbol\"]] [\":symbol\" \"+\"] \":literal\"]]',
            '[\":expression_statement\" [\":assignment\" \":symbol\" [\":symbol\" \"=\"] [\":binary_operator\" [\":call\" [\":symbol\" \"abs\"] [\":argument_list\" \":symbol\"]] [\":symbol\" \"+\"] \":literal\"]]]',
            '[\":return_statement\" \":symbol\"]',
            '[\":block\" [\":expression_statement\" [\":assignment\" \":symbol\" [\":symbol\" \"=\"] [\":binary_operator\" [\":call\" [\":symbol\" \"abs\"] [\":argument_list\" \":symbol\"]] [\":symbol\" \"+\"] \":literal\"]]] [\":return_statement\" \":symbol\"]]',
            '[\":function_definition\" \":symbol\" [\":parameters\" \":symbol\"] [\":block\" [\":expression_statement\" [\":assignment\" \":symbol\" [\":symbol\" \"=\"] [\":binary_operator\" [\":call\" [\":symbol\" \"abs\"] [\":argument_list\" \":symbol\"]] [\":symbol\" \"+\"] \":literal\"]]] [\":return_statement\" \":symbol\"]]]',
        ]))

    def test_default_argv_and_missing_files(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'a.py').write_text('pass\n')
            with patch.object(sys, 'argv', ['duplication.py', 'python', directory, 'a.py']), redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
                self.assertEqual(duplication.main(), 0)
            self.assertEqual(json.loads(out.getvalue())['findings'], 0)
            with redirect_stderr(io.StringIO()):
                self.assertEqual(duplication.main(['python', directory, 'missing.py']), 2)

    def test_parentheses_comments_and_interpolated_strings(self):
        text = ('def f(items):\n    total = 0  # ignored\n    for item in items:\n'
                '        total += abs(item)\n    return total\n')
        other = text.replace('def f', 'def g').replace('abs(item)', '(abs(item))').replace('# ignored', '# changed')
        code, result, _, _, _ = self.run_check({'a.py': text, 'b.py': other})
        self.assertEqual(code, 1)
        self.assertEqual(result['pairs'][0]['score'], 1.0)
        other = text.replace('def f', 'def g').replace('abs(item)', 'f"value {item}"')
        _, result, _, _, _ = self.run_check({'a.py': text, 'b.py': other})
        for finding in result['pairs']:
            self.assertLess(finding['score'], 1.0)

    def test_literals_interpolation_comments_and_parenthesized_callees(self):
        first = 'def f(a):\n    b = "hello"\n    c = abs(a)\n    return b, c\n'
        second = first.replace('def f', 'def g').replace('"hello"', '99').replace('abs(a)', '(abs)(a)') + '# trailing\n'
        code, result, _, _, _ = self.run_check({'a.py': first, 'b.py': second})
        self.assertEqual(code, 1)
        self.assertEqual(result['pairs'][0]['score'], 1.0)
        interpolated = first.replace('"hello"', 'f"hello {abs(a)}"')
        _, _, _, _, evidence = self.run_check({'a.py': interpolated})
        fingerprints = json.loads((evidence / 'measurements.json').read_bytes())[0]['fingerprints']
        self.assertIn('\":interpolation\"', fingerprints)
        self.assertIn('\":call\"', fingerprints)
        commented = first.replace('    c =', '    # extra comment\n    c =')
        _, result, _, _, _ = self.run_check({'a.py': first, 'b.py': commented})
        self.assertEqual(result['pairs'][0]['score'], 1.0)

    def test_compound_comparison_operators_remain_distinct(self):
        template = 'def f(a, b):\n    c = 0\n    if a OP b:\n        c = abs(a)\n    return c\n'
        _, result, _, _, evidence = self.run_check({
            'a.py': template.replace('OP', 'not in'),
            'b.py': template.replace('OP', 'is not'),
        })
        for finding in result['pairs']:
            self.assertLess(finding['score'], 1.0)
        measurements = json.loads((evidence / 'measurements.json').read_bytes())
        self.assertIn('[\":symbol\" \"not in\"]', measurements[0]['fingerprints'])
        self.assertIn('[\":symbol\" \"is not\"]', measurements[1]['fingerprints'])

    def test_comments_inside_parentheses_preserve_expression_and_callee(self):
        for expression in ['abs(a) + 1', 'abs']:
            with self.subTest(expression=expression):
                plain = f'def f(a):\n    b = (\n        {expression}\n    )\n    return b\n'
                commented = plain.replace('        ' + expression, '        # note\n        ' + expression)
                code, result, _, _, evidence = self.run_check({'a.py': plain, 'b.py': commented})
                self.assertEqual(code, 1)
                self.assertEqual(result['pairs'][0]['score'], 1.0)
                measurements = json.loads((evidence / 'measurements.json').read_bytes())
                self.assertEqual(measurements[0]['nodes'], measurements[1]['nodes'])
                self.assertEqual(measurements[0]['fingerprints'], measurements[1]['fingerprints'])
        plain = 'def f(a):\n    b = (abs)(a)\n    c = b + 1\n    return c\n'
        commented = plain.replace('(abs)', '(\n        # note\n        abs\n    )')
        _, result, _, _, _ = self.run_check({'a.py': plain, 'b.py': commented})
        self.assertEqual(result['pairs'][0]['score'], 1.0)

    def test_enclosing_function_pairs_are_excluded_but_separate_methods_are_compared(self):
        method = '        def m(self, a):\n            b = 0\n            for c in a:\n                b += abs(c)\n            return b\n'
        factory = 'def factory():\n    class C:\n' + method + '    return C\n'
        code, result, _, _, _ = self.run_check({'a.py': factory})
        self.assertEqual(code, 0)
        self.assertEqual(result['pairs'], [])
        code, result, _, _, _ = self.run_check({'a.py': factory.removesuffix('    return C\n')})
        self.assertEqual(code, 0)
        self.assertEqual(result['pairs'], [])
        separate = 'class D:\n' + '\n'.join(line[4:] for line in method.splitlines()) + '\n'
        code, result, _, _, _ = self.run_check({'a.py': factory + '\n' + separate})
        self.assertEqual(code, 1)
        self.assertEqual([(p['left']['startLine'], p['right']['startLine']) for p in result['pairs']],
                         [(1, 11), (3, 11)])

    def test_duplicate_source_paths_do_not_pair_a_function_with_itself(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'a.py'
            path.write_text('def f(a):\n    b = 0\n    for c in a:\n        b += c\n    return b\n')
            (Path(directory) / 'b.py').write_bytes(path.read_bytes())
            with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
                self.assertEqual(duplication.main(['python', directory, 'a.py', str(path), 'b.py']), 1)
            self.assertEqual(len(json.loads(out.getvalue())['pairs']), 1)


if __name__ == '__main__':
    unittest.main()
