"""Public report boundaries retain useful diagnostics and review evidence."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/workflow/scripts'))
from coverage_lcov import read
from shared_mutation import assess, render_report


class ReportContractsTests(unittest.TestCase):
    def test_lcov_diagnostics_identify_invalid_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'coverage.lcov'
            source = (Path(directory) / 'sample.py').resolve()
            cases = [('', 'Incomplete or empty LCOV report'),
                     ('end_of_record\n', 'LCOV end_of_record without SF'),
                     ('SF:\n', 'LCOV has nested or empty SF records'),
                     ('DA:1,1\n', 'LCOV record outside SF: DA:1,1'),
                     (f'SF:{source}\nDA:0,1\n', 'Invalid LCOV line record: DA:0,1'),
                     (f'SF:{source}\nBRDA:0,0,0,1\n', 'Invalid LCOV branch record: BRDA:0,0,0,1'),
                     (f'SF:{source}\nDA:1,1\nDA:1,0\n', f'Duplicate LCOV lines record in {source}: DA:1,0'),
                     (f'SF:{source}\nDA:3,1\nend_of_record\n', f'LCOV line outside source: {source}'),
                     ('SF:other.py\nDA:1,1\nend_of_record\n', f'Missing exact-path LCOV coverage: {source}')]
            for text, message in cases:
                path.write_text(text)
                with self.subTest(text=text), self.assertRaises(ValueError) as raised:
                    read(path, {source: 'def a():\n return 1\n'})
                self.assertEqual(str(raised.exception), message)

    def test_shared_coverage_diagnostics_preserve_scope(self):
        from shared_crap import collect
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            unknown = root / 'a.unknown'
            unknown.write_text('x')
            empty = root / 'empty.py'
            empty.write_text('value = 1\n')
            source = root / 'a.py'
            source.write_text('def a():\n return 1\n')
            for path, coverage, message in ((unknown, {}, f'Unsupported source: {unknown}'),
                                            (empty, {}, f'No functions found: {empty}'),
                                            (source, {}, f'Missing exact-path LCOV coverage: {source}'),
                                            (source, {source: {'lines': {}, 'branches': {}}}, f'Missing line coverage: {source}:a')):
                with self.assertRaises(ValueError) as raised:
                    collect(coverage, [str(path)])
                self.assertEqual(str(raised.exception), message)
            coverage = {source: {'lines': {2: 1}, 'branches': {}}}
            self.assertEqual(collect(coverage, [str(source)])['coverage']['line'], {'covered': 1, 'total': 1})
            coverage[source]['branchKind'] = 'unknown'
            with self.assertRaisesRegex(ValueError, '^Invalid coverage kind$'):
                collect(coverage, [str(source)])
            other = root / 'b.py'
            other.write_text('def b():\n return 1\n')
            coverage = {source: {'lines': {2: 1}, 'branches': {}, 'branchKind': 'branch'},
                        other: {'lines': {2: 1}, 'branches': {}, 'branchKind': 'region'}}
            with self.assertRaises(ValueError) as raised:
                collect(coverage, [str(source), str(other)])
            self.assertEqual(str(raised.exception), 'Cannot combine branch and region coverage')

    def test_invalid_argument_diagnostics(self):
        from shared_languages import arguments
        import crap
        import mutation
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'file'
            source.touch()
            cases = (([], 'Require project and source paths, followed by -- tool args'),
                     ([str(source)], 'project must be a directory'),
                     ([directory, '--timeout-ms'], 'Require --timeout-ms N'),
                     ([directory, '--timeout-ms', '0'], 'Require positive timeoutMs (max 2147483647)'))
            for args, message in cases:
                with self.assertRaises(ValueError) as raised:
                    arguments(args)
                self.assertEqual(str(raised.exception), message)
            with self.assertRaises(ValueError) as raised:
                crap.dispatch(['unknown.json', 'extra'])
            self.assertEqual(str(raised.exception), 'Usage: python crap.py CONFIG.json')
            with self.assertRaises(ValueError) as raised:
                crap.collect_main([])
            self.assertEqual(str(raised.exception), 'Usage: crap.py collect COVERAGE.lcov OUTPUT.json SOURCE_FILE...')
            with self.assertRaises(ValueError) as raised:
                mutation.execute_config(source, {}, (0,))
            self.assertEqual(str(raised.exception), 'Require cwd, report, nonempty command argv and positive timeoutMs (max 2147483647)')

    def test_status_only_actionable_report_explicitly_shows_missing_details(self):
        result = assess({'baselinePassed': True, 'mutants': [{'status': 'survived'}]}, 'normalized', Path('report.json'))
        result['reportPath'] = 'report.json'
        self.assertEqual(render_report(result),
                         'function "function unavailable" (file unavailable:?)\nhas 1 surviving mutants:\n\n'
                         'mutant (ID unavailable) [survived]\nDiff unavailable; inspect the original engine report.\n\n'
                         'Summary: 0 killed, 1 survived, 0 noCoverage, 0 timeout, 0 unviable, 0 ignored, 0 error\n'
                         'Exit code: 1\nReport: report.json')

    def test_stryker_invalid_range_is_preserved_as_detail_gap(self):
        report = {'files': {'a.js': {'source': 'hello', 'mutants': [{'id': '1', 'status': 'Survived',
                  'location': {'start': {'line': 1, 'column': 4}, 'end': {'line': 1, 'column': 2}}}]}}}
        result = assess(report, 'stryker', Path('report.json'))
        self.assertEqual(result['mutants'][0]['detailGap'], 'Cannot extract mutation details: Invalid Stryker source range')

    def test_unified_diff_preserves_header_and_line_format(self):
        from shared_mutation import code_diff, numbered_diff
        self.assertEqual(code_diff('old\n', 'new\n'), '--- \n+++ \n@@ -1 +1 @@\n-old\n+new')
        self.assertEqual(numbered_diff('@@ -1,2 +1,2 @@\n-old\n\\ No newline at end of file\n-next\n+new'), '1 - old\n2 - next\n1 + new')

    def test_llvm_diagnostics_identify_invalid_segments(self):
        from coverage_llvm import line_hits
        for segment, message in (([], 'Invalid LLVM coverage segment'),
                                 ([0, 1, 1, True, True, False], 'Invalid LLVM coverage line'),
                                 ([1, 1, -1, True, True, False], 'Invalid LLVM coverage count')):
            with self.assertRaises(ValueError) as raised:
                line_hits([segment], 1)
            self.assertEqual(str(raised.exception), message)
