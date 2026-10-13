"""Shared source and report reading preserves strict UTF-8 and universal newlines."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/workflow/scripts'))
from shared_runner import read_json, read_utf8


class Utf8ReadingTests(unittest.TestCase):
    def test_unicode_and_universal_newlines_preserve_source_text(self):
        cases = [(b'', ''), (b'a\nb\n', 'a\nb\n'), (b'a\r\nb\r\n', 'a\nb\n'),
                 (b'a\rb\r', 'a\nb\n'), (b'\r', '\n'),
                 ('\ufeff你好😀\r\nlast\r'.encode(), '\ufeff你好😀\nlast\n')]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source'
            for data, expected in cases:
                with self.subTest(data=data):
                    path.write_bytes(data)
                    self.assertEqual(read_utf8(path), expected)

    def test_invalid_utf8_never_uses_a_different_codec_or_replaces_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.json'
            for data in (b'\xff', b'\xed\xa0\x80', '{"x":"你好"}'.encode('utf-16'),
                         '{"x":"你好"}'.encode('utf-32'), b'\xe2\x82'):
                with self.subTest(data=data):
                    path.write_bytes(data)
                    with self.assertRaises(UnicodeDecodeError):
                        read_json(path)

    def test_json_bom_and_nonfinite_values_remain_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.json'
            for data in (b'\xef\xbb\xbf{}', b'{"nested":[NaN]}', b'{"nested":[Infinity]}',
                         b'{"nested":[-Infinity]}', b'{"nested":[1e999]}'):
                with self.subTest(data=data):
                    path.write_bytes(data)
                    with self.assertRaises(ValueError):
                        read_json(path)
            path.write_bytes(b'{\r\n"value":1e308\r\n}\r\n')
            self.assertEqual(read_json(path), {'value': 1e308})

    def test_invalid_json_diagnostic_positions_use_normalized_newlines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.json'
            for newline in (b'\n', b'\r\n', b'\r'):
                path.write_bytes(b'{' + newline + b'"x":}' + newline)
                with self.assertRaises(json.JSONDecodeError) as raised:
                    read_json(path)
                self.assertEqual((raised.exception.lineno, raised.exception.colno, raised.exception.pos), (2, 5, 6))
