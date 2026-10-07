from contextlib import redirect_stderr
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "skills/workflow/scripts/lizard_metrics.py"
sys.path.insert(0, str(SCRIPT.parent))
import lizard_metrics


class LizardMetricsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.coverage = self.root / "coverage.lcov"
        self.output = self.root / "metrics.json"

    def run_metrics(self, *sources):
        # Exercise the imported module so mutmut can associate these tests with its mutants.
        argv = [str(SCRIPT), str(self.coverage), str(self.output), *sources]
        previous = Path.cwd()
        try:
            os.chdir(self.root)
            with mock.patch.object(sys, "argv", argv), redirect_stderr(io.StringIO()) as stderr:
                code = lizard_metrics.main()
            return subprocess.CompletedProcess(argv, code, "", stderr.getvalue())
        finally:
            os.chdir(previous)

    def test_script_entrypoint(self):
        result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage:", result.stderr)

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
        self.assertEqual(json.loads(self.output.read_text())["coverage"],
                         {"line": {"covered": 4, "total": 8}, "branch": {"covered": 0, "total": 0}})
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
            "BRDA:2,0,jump,1\n",
            "SF:sample.py\nDA:2,1\nBRDA:3,0,jump,1\nend_of_record\n",
            "SF:sample.py\nDA:2,1\nBRDA:2,0,jump,1\nBRDA:2,0,jump,0\nend_of_record\n",
            *(f"SF:sample.py\nDA:2,1\n{record}\nend_of_record\n" for record in [
                "BRDA:0,0,jump,1", "BRDA:2,0,jump,-1", "BRDA:2,0,jump,x", "BRDA:2,,jump,1", "BRDA:2,0,1"]),
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

    def test_aggregates_line_and_branch_coverage_in_scope(self):
        (self.root / "sample.py").write_text("def choice(x):\n    if x:\n        return 1\n    return 0\n")
        (self.root / "other.py").write_text("def other():\n    return 1\n")
        self.coverage.write_text(
            "SF:sample.py\nDA:2,1\nDA:3,0\nDA:4,1\n"
            "BRDA:2,0,jump to line 3,0\nBRDA:2,0,jump to line 4,1\nBRDA:2,e1,raise, with comma,-\nend_of_record\n"
            "SF:sample.py\nDA:3,1\nBRDA:2,0,jump to line 3,2\nend_of_record\n"
            "SF:other.py\nDA:2,0\nBRDA:2,0,out of scope,0\nend_of_record\n")
        result = self.run_metrics("sample.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        metrics = json.loads(self.output.read_text())
        self.assertEqual(metrics["coverage"], {"line": {"covered": 3, "total": 3}, "branch": {"covered": 2, "total": 3}})
        self.assertEqual([(f["covered"], f["total"]) for f in metrics["functions"]], [(3, 3)])


if __name__ == "__main__":
    unittest.main()
