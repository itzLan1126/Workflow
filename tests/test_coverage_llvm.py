import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/workflow/scripts'))
from coverage_llvm import read, line_hits


class LLVMCoverageTests(unittest.TestCase):
    def test_line_and_region_counts_from_export(self):
        with tempfile.TemporaryDirectory() as directory:
            source = (Path(directory) / 'sample.swift').resolve()
            report = Path(directory) / 'coverage.json'
            data = {'type': 'llvm.coverage.json.export', 'data': [{'files': [
                {'filename': str(source), 'segments': [[1, 1, 2, True, True, False], [3, 1, 0, False, False, False]]}],
                'functions': [{'name': 'example', 'filenames': [str(source)],
                               'regions': [[1, 1, 3, 1, 2, 0, 0, 0, 'extension'], [2, 1, 2, 5, 0, 0, 0, 0], [2, 1, 2, 2, 5, 0, 0, 1]]}]}]}
            report.write_text(json.dumps(data))
            hits = read(report, {source: 'func example() {\n return 1\n}\n'})[source]
            self.assertEqual(hits['lines'], {1: 2, 2: 2})
            self.assertEqual(list(hits['branches'].values()), [2, 0])
            self.assertEqual(hits['branchKind'], 'region')
            from shared_crap import calculate, collect
            source.write_text('func example() {\n return 1\n}\n')
            measurements = collect({source: hits}, [str(source)])
            result = calculate(measurements)
            self.assertEqual(result['coverage']['region'], {'covered': 1, 'total': 2, 'coverage': 0.5, 'meetsStandard': False})
            self.assertNotIn('branch', result['coverage'])
            self.assertEqual(result['findings'], 1)
            with self.assertRaisesRegex(ValueError, '^Missing exact-path LLVM coverage$'):
                read(report, {Path('/missing.swift'): 'x'})
            data['type'] = 'other'
            report.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, '^Require llvm-cov export JSON$'):
                read(report, {})

    def test_segments_preserve_zero_hits_overlaps_and_last_source_line(self):
        self.assertEqual(line_hits([[1, 1, 0, True, True, False], [4, 1, 0, False, False, False]], 2), {1: 0, 2: 0})
        self.assertEqual(line_hits([[2, 1, 0, True, True, False]], 2), {2: 0})
        self.assertEqual(line_hits([[1, 1, 3, True, True, False], [1, 3, 0, True, True, False],
                                    [2, 1, 0, False, False, False]], 2), {1: 3})
        self.assertEqual(line_hits([[1, 1, 0, True, True, False, 'extension']], 1), {1: 0})

    def test_invalid_region_ranges_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            source = (Path(directory) / 'sample.swift').resolve()
            report = Path(directory) / 'coverage.json'
            for region, message in (([0, 1, 2, 1, 1, 0, 0, 0], 'Invalid LLVM region range'),
                                    ([1, 1, 3, 1, 1, 0, 0, 0], 'Invalid LLVM region outside source'),
                                    ([2, 1, 1, 1, 1, 0, 0, 0], 'Invalid LLVM region range'),
                                    ([1, 1, 2, 1, 1, -1, 0, 0], 'Invalid LLVM region file index')):
                data = {'type': 'llvm.coverage.json.export', 'data': [{'files': [{'filename': str(source), 'segments': []}],
                        'functions': [{'name': 'a', 'filenames': [str(source)], 'regions': [region]}]}]}
                report.write_text(json.dumps(data))
                with self.subTest(region=region), self.assertRaises(ValueError) as raised:
                    read(report, {source: 'func a() {\n}\n'})
                self.assertEqual(str(raised.exception), message)

    def test_invalid_segments_fail_closed(self):
        for segment in (None, [], [0, 1, 1, True, True, False], [1, 1, -1, True, True, False], [True, 1, 0, True, True, False]):
            with self.subTest(segment=segment), self.assertRaises(ValueError):
                line_hits([segment], 2)
        self.assertEqual(line_hits([[1, 1, 0, False, False, True], [2, 1, 1, True, True, False]], 1), {})
