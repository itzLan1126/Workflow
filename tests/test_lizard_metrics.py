import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "skills/workflow/scripts/lizard-metrics.py"


class LizardMetricsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.coverage = self.root / "coverage.lcov"
        self.output = self.root / "metrics.json"

    def run_metrics(self, *sources):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.coverage),
                               str(self.output), *sources], cwd=self.root,
                              text=True, capture_output=True)

    def test_real_multilanguage_analysis(self):
        samples = {
            "sample.py": "def choice(x):\n    if x:\n        return 1\n    return 0\n",
            "sample.ts": "function choice(x: boolean): number {\n if (x) return 1;\n return 0;\n}\n",
            "sample.rs": "fn choice(x: bool) -> i32 {\n if x { return 1; }\n return 0;\n}\n",
            "sample.swift": "func choice(_ x: Bool) -> Int {\n if x { return 1 }\n return 0\n}\n",
        }
        for name, code in samples.items():
            (self.root / name).write_text(code)
        self.coverage.write_text("".join(
            f"SF:{name}\nDA:2,1\nDA:3,0\nend_of_record\n" for name in samples))
        result = self.run_metrics(*samples)
        self.assertEqual(result.returncode, 0, result.stderr)
        functions = json.loads(self.output.read_text())["functions"]
        self.assertEqual(len(functions), 4)
        for function in functions:
            self.assertEqual((function["complexity"], function["covered"], function["total"]), (2, 1, 2))
            self.assertEqual(function["coverageKind"], "line")
        result = self.run_metrics(*samples)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(self.output.read_text())["functions"], functions)

    def test_rejects_invalid_or_ambiguous_evidence(self):
        (self.root / "sample.py").write_text("def example():\n    return 1\n")
        cases = [
            "SF:other/sample.py\nDA:2,1\nend_of_record\n",
            "SF:sample.py\nDA:2,-1\nend_of_record\n",
            "SF:sample.py\nDA:0,1\nend_of_record\n",
            "SF:sample.py\nDA:2,nan\nend_of_record\n",
            "SF:sample.py\nDA:2,1,checksum,extra\nend_of_record\n",
            "SF:sample.py\nDA:3,1\nend_of_record\n",
            "SF:sample.py\nDA:2,1\nDA:2,0\nend_of_record\n",
            "SF:sample.py\nend_of_record\n",
            "SF:sample.py\nDA:2,1\n",
            "DA:2,1\n",
        ]
        for report in cases:
            with self.subTest(report=report):
                self.coverage.write_text(report)
                result = self.run_metrics("sample.py")
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(self.output.exists())

    def test_rejects_unsupported_empty_and_nested_functions(self):
        samples = {
            "sample.unknown": "def example():\n    return 1\n",
            "empty.py": "value = 1\n",
            "nested.py": "def outer():\n    def inner():\n        return 1\n    return inner()\n",
        }
        for name, code in samples.items():
            with self.subTest(name=name):
                (self.root / name).write_text(code)
                self.coverage.write_text(f"SF:{name}\nDA:1,1\nend_of_record\n")
                self.assertEqual(self.run_metrics(name).returncode, 2)
                self.assertFalse(self.output.exists())

    def test_merges_test_records_but_requires_each_function_coverage(self):
        source = self.root / "sample.py"
        source.write_text("def example():\n    return 1\n\ndef uncovered():\n    return 0\n")
        report = ("SF:sample.py\nDA:2,0\nend_of_record\n"
                  f"SF:{source}\nDA:2,1,checksum\nend_of_record\n")
        self.coverage.write_text(report)
        self.assertEqual(self.run_metrics("sample.py").returncode, 2)
        self.assertFalse(self.output.exists())
        self.coverage.write_text(report + "SF:sample.py\nDA:5,0\nend_of_record\n")
        result = self.run_metrics("sample.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        functions = json.loads(self.output.read_text())["functions"]
        self.assertEqual([(item["covered"], item["total"]) for item in functions], [(1, 1), (0, 1)])


if __name__ == "__main__":
    unittest.main()
