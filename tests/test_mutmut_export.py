from contextlib import redirect_stderr
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/workflow/scripts"
sys.path.insert(0, str(SCRIPTS))
from mutmut_export import collect, main
from mutation import summarize

# A subset of mutmut 3's status table; collect() receives the installed table at runtime.
TABLE = {1: "killed", 0: "survived", 33: "no tests", 36: "timeout", 34: "skipped",
         37: "caught by type check", 35: "suspicious", None: "not checked"}
HAS_MUTMUT = importlib.util.find_spec("mutmut") is not None and importlib.util.find_spec("pytest") is not None


def meta(root, path, exit_codes):
    file = root / "mutants" / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps({"exit_code_by_key": exit_codes}))


class MutmutExportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="workflow-mutmut-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_maps_mutmut_statuses_and_treats_unfinished_as_error(self):
        meta(self.root, "src/a.py.meta", {"a.x_f__mutmut_1": 1, "a.x_f__mutmut_2": 0, "a.x_f__mutmut_3": 33})
        meta(self.root, "src/pkg/b.py.meta", {"b.x_g__mutmut_1": 36, "b.x_g__mutmut_2": 34,
                                              "b.x_g__mutmut_3": 37, "b.x_g__mutmut_4": 35,
                                              "b.x_g__mutmut_5": None})
        statuses = {m["id"]: m["status"] for m in collect(self.root / "mutants", TABLE)}
        self.assertEqual(statuses, {
            "a.x_f__mutmut_1": "killed", "a.x_f__mutmut_2": "survived", "a.x_f__mutmut_3": "noCoverage",
            "b.x_g__mutmut_1": "timeout", "b.x_g__mutmut_2": "ignored", "b.x_g__mutmut_3": "unviable",
            "b.x_g__mutmut_4": "error", "b.x_g__mutmut_5": "error"})

    def test_rejects_missing_or_unrecognized_metadata(self):
        with self.assertRaisesRegex(ValueError, "^No mutmut results found under mutants/$"):
            collect(self.root / "mutants", TABLE)
        (self.root / "mutants").mkdir()
        (self.root / "mutants/a.py.meta").write_text(json.dumps({"exit_code_by_key": []}))
        with self.assertRaisesRegex(ValueError, "^Unrecognized mutmut metadata: .*a.py.meta$"):
            collect(self.root / "mutants", TABLE)

    def test_pytest_internal_error_cannot_pass_mutation_gate(self):
        meta(self.root, "src/a.py.meta", {"a.x_f__mutmut_1": 3})
        # mutmut 3.8 calls pytest's internal-error exit a kill; it is not a failing assertion.
        mutants = collect(self.root / "mutants", {**TABLE, 3: "killed"})
        self.assertEqual(mutants, [{"id": "a.x_f__mutmut_1", "status": "error"}])
        self.assertEqual(summarize({"baselinePassed": True, "mutants": mutants}, "normalized")["exitCode"], 2)

    def run_main(self, argv=None):
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.root)
        with redirect_stderr(io.StringIO()) as stderr, mock.patch.object(sys, "argv", ["mutmut_export.py", "report.json"]):
            code = main(argv)
        return code, stderr.getvalue()

    def test_usage(self):
        self.assertEqual(self.run_main([]), (2, "mutmut_export: Usage: python mutmut_export.py REPORT.json\n"))

    @unittest.skipUnless(HAS_MUTMUT, "mutmut is not installed")
    def test_main_runs_mutmut_then_exports_its_results(self):
        (self.root / "pyproject.toml").write_text('[tool.mutmut]\nsource_paths = ["src/"]\n')

        def fake_run(command, check):
            meta(self.root, "src/a.py.meta", {"a.x_f__mutmut_1": 1, "a.x_f__mutmut_2": 0})

        with mock.patch("mutmut_export.subprocess.run", side_effect=fake_run) as run:
            self.assertEqual(self.run_main(), (0, ""))
        run.assert_called_once_with([sys.executable, "-m", "mutmut", "run"], check=True)
        self.assertEqual(json.loads((self.root / "report.json").read_text(encoding="utf-8")), {
            "baselinePassed": True,
            "mutants": [{"id": "a.x_f__mutmut_1", "status": "killed"}, {"id": "a.x_f__mutmut_2", "status": "survived"}]})

    def test_main_writes_no_report_when_mutmut_fails(self):
        failure = subprocess.CalledProcessError(1, ["mutmut", "run"])
        with mock.patch("mutmut_export.subprocess.run", side_effect=failure):
            code, stderr = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("returned non-zero exit status 1", stderr)
        self.assertFalse((self.root / "report.json").exists())

    def test_refuses_stale_mutants_directory(self):
        (self.root / "mutants").mkdir()
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.root)
        with redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(main(["report.json"]), 2)
        self.assertEqual(stderr.getvalue(), "mutmut_export: mutants/ already exists; mutmut would reuse "
                         "stale results. Use a fresh analysis copy\n")
        self.assertFalse((self.root / "report.json").exists())

    @unittest.skipUnless(HAS_MUTMUT, "mutmut and pytest are not installed")
    def test_real_mutmut_run_through_mutation_runner(self):
        (self.root / "src/calc").mkdir(parents=True)
        (self.root / "tests").mkdir()
        (self.root / "src/calc/__init__.py").write_text(
            "def choose(a, b):\n    if a > b:\n        return a\n    return b\n\n\n"
            "def untested(x):\n    return x + 1\n")
        test = self.root / "tests/test_calc.py"
        test.write_text("from calc import choose\n\n\ndef test_choose():\n    assert choose(2, 1) == 2\n")
        (self.root / "pyproject.toml").write_text(
            '[tool.mutmut]\npaths_to_mutate = ["src/"]\npytest_add_cli_args_test_selection = ["tests/"]\n')
        config = self.root / "mutation-config.json"
        config.write_text(json.dumps({"cwd": ".", "report": "mutation.json", "format": "normalized",
                                      "command": [sys.executable, str(SCRIPTS / "mutmut_export.py"),
                                                  "mutation.json"]}))

        def run():
            return subprocess.run([sys.executable, str(SCRIPTS / "mutation.py"), str(config)],
                                  cwd=self.root, text=True, capture_output=True, timeout=600,
                                  env={"PATH": "/usr/bin:/bin", "PYTHONPATH": "src"})

        result = run()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["counts"]["survived"], 1)
        self.assertEqual(json.loads(result.stdout)["counts"]["noCoverage"], 2)

        test.write_text("from calc import choose\n\n\ndef test_choose():\n    assert choose(2, 1) == 1\n")
        for path in ("mutants", "mutation.json"):
            subprocess.run(["rm", "-rf", path], cwd=self.root, check=True)
        result = run()
        self.assertEqual(result.returncode, 2, "a failing baseline must not produce a report")
        self.assertIn("Tool failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
