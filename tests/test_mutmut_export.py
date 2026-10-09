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
from mutmut_export import add_details, classify, collect, function_position, main
from mutation import summarize
from mutation_report import numbered_diff

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

    def test_only_pytest_test_failure_can_count_as_a_kill(self):
        # These semantics must not change even if a display table mislabels operational failures.
        table = {code: "killed" for code in (0, 1, 2, 3, 4, 5, 99)}
        for code, status, gate in ((0, "survived", 1), (1, "killed", 0), (2, "error", 2),
                                   (3, "error", 2), (4, "error", 2), (5, "noCoverage", 1), (99, "error", 2)):
            with self.subTest(code=code):
                meta(self.root, "src/a.py.meta", {"a.x_f__mutmut_1": code})
                mutants = collect(self.root / "mutants", table)
                self.assertEqual(mutants, [{"id": "a.x_f__mutmut_1", "status": status}])
                self.assertEqual(summarize({"baselinePassed": True, "mutants": mutants}, "normalized")["exitCode"], gate)
        for code in (True, False, 1.0, "1", None, []):
            with self.subTest(code=code):
                self.assertEqual(classify(code, table), "error")

    @unittest.skipUnless(HAS_MUTMUT, "mutmut is not installed")
    def test_installed_mutmut_table_preserves_pytest_errors(self):
        from mutmut.stats import status_by_exit_code
        self.assertEqual([classify(code, status_by_exit_code) for code in range(6)],
                         ["survived", "killed", "error", "error", "error", "noCoverage"])

    def run_main(self, argv=None):
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.root)
        with redirect_stderr(io.StringIO()) as stderr, mock.patch.object(sys, "argv", ["mutmut_export.py", "report.json"]):
            code = main(argv)
        return code, stderr.getvalue()

    def test_usage(self):
        self.assertEqual(self.run_main([]), (2, "mutmut_export: Usage: python mutmut_export.py REPORT.json\n"))

    def test_function_position_includes_decorators_and_distinguishes_methods(self):
        path = self.root / "example.py"
        path.write_text("def before():\n    pass\n\n@decorator\ndef choose():\n    pass\n\n"
                        "class Earlier:\n    pass\n\nclass Box:\n    def before(self):\n        pass\n\n"
                        "    @decorator\n    async def choose(self):\n        pass\n")
        self.assertEqual(function_position(path, "choose", None), (5, 3))
        self.assertEqual(function_position(path, "choose", "Box"), (16, 14))

    @unittest.skipUnless(HAS_MUTMUT, "mutmut is not installed")
    def test_detail_failure_preserves_outcome_and_killed_mutants_skip_extraction(self):
        mutants = [{"id": "calc.x_choose__mutmut_1", "status": "survived"},
                   {"id": "calc.x_choose__mutmut_2", "status": "killed"}]
        with mock.patch("mutmut.mutation.diff_apply.find_mutant", side_effect=FileNotFoundError("missing")) as find:
            result = add_details(mutants)
        self.assertEqual(result[0]["status"], "survived")
        self.assertIn("missing", result[0]["detailGap"])
        self.assertEqual(result[1], mutants[1])
        find.assert_called_once_with("calc.x_choose__mutmut_1")

    def generated_results(self):
        from mutmut.configuration import _load_config
        from mutmut.mutation.data import MutantLineSpans, SourceFileMutationData
        from mutmut.mutation.diff_apply import get_diff_for_mutant
        from mutmut.mutation.file_mutation import mutate_file_contents

        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.root)
        (self.root / "pyproject.toml").write_text('[tool.mutmut]\nsource_paths = ["src/"]\n')
        path = Path("src/calc.py")
        path.parent.mkdir()
        source = ("def before():\n    return 0\n\n@staticmethod\ndef choose(a, b):\n    return a + b\n\n"
                  "class Earlier:\n    def choose(self):\n        return 0\n\n"
                  "class Box:\n    @staticmethod\n    def choose(a, b):\n        return a + b\n")
        path.write_text(source, encoding="utf-8")
        # Keep the outer mutation runner's cached config for its instrumented trampolines.
        self.enterContext(mock.patch("mutmut.utils.file_utils.config", return_value=_load_config()))
        generated = mutate_file_contents(str(path), source)
        target = Path("mutants") / path
        target.parent.mkdir(parents=True)
        target.write_text(generated.code, encoding="utf-8")
        MutantLineSpans(path=path, span_by_function_name=generated.line_span_by_function_name).save()
        data = SourceFileMutationData(path=path)
        keys = ["calc." + key for key in generated.mutant_names]
        # Select an observable arithmetic change using the engine's actual generated functions.
        top, method = [key for key in keys if "return a - b" in get_diff_for_mutant(key, path=path)]
        data.exit_code_by_key = {keys[0]: 1, top: 0, method: 36}
        data.save()
        return keys[0], top, method

    @unittest.skipUnless(HAS_MUTMUT, "mutmut is not installed")
    def test_details_from_real_generated_functions_include_method_and_source_locations(self):
        from mutmut.stats import status_by_exit_code

        killed, top, method = self.generated_results()
        mutants = add_details(collect("mutants", status_by_exit_code))
        self.assertEqual(mutants[0], {"id": killed, "status": "killed"})
        for mutant, key, name, status, line, offset, changed_line in [
                (mutants[1], top, "choose", "survived", 5, 3, 6),
                (mutants[2], method, "Box.choose", "timeout", 14, 12, 15)]:
            with self.subTest(function=name):
                self.assertEqual({k: v for k, v in mutant.items() if k != "diff"}, {
                    "id": key, "status": status, "file": "src/calc.py", "function": name,
                    "line": line, "diffOffset": offset})
                self.assertEqual(numbered_diff(mutant["diff"], mutant["diffOffset"]),
                                 f"{changed_line} -     return a + b\n{changed_line} +     return a - b")

    @unittest.skipUnless(HAS_MUTMUT, "mutmut is not installed")
    def test_main_runs_mutmut_then_exports_its_results(self):
        generated = []

        def fake_run(command, check):
            generated.extend(self.generated_results())

        with mock.patch("mutmut_export.subprocess.run", side_effect=fake_run) as run:
            self.assertEqual(self.run_main(), (0, ""))
        run.assert_called_once_with([sys.executable, "-m", "mutmut", "run"], check=True)
        report = json.loads((self.root / "report.json").read_text(encoding="utf-8"))
        self.assertIs(report["baselinePassed"], True)
        self.assertEqual([(m["id"], m["status"]) for m in report["mutants"]],
                         list(zip(generated, ("killed", "survived", "timeout"))))
        self.assertEqual(report["mutants"][1]["function"], "choose")
        self.assertEqual(report["mutants"][2]["function"], "Box.choose")
        self.assertTrue(all(m.get("diff") for m in report["mutants"][1:]))

    @unittest.skipUnless(HAS_MUTMUT, "mutmut is not installed")
    def test_main_rejects_missing_metadata_and_report_write_failure(self):
        with mock.patch("mutmut_export.subprocess.run"):
            self.assertEqual(self.run_main()[0], 2)
        self.assertFalse((self.root / "report.json").exists())
        (self.root / "report.json").mkdir()
        with mock.patch("mutmut_export.subprocess.run", side_effect=lambda *a, **kw: self.generated_results()):
            self.assertEqual(self.run_main()[0], 2)
        self.assertTrue((self.root / "report.json").is_dir())

    def test_source_lookup_uses_utf8_even_when_default_encoding_cannot_read_it(self):
        path = self.root / "unicode.py"
        path.write_text("def 前置():\n    pass\n\ndef 目标():\n    pass\n", encoding="utf-8")
        meta_path = self.root / "mutants/unicode.py.meta"
        meta_path.parent.mkdir()
        meta_path.write_text(json.dumps({"exit_code_by_key": {"模块.x_目标__mutmut_1": 0}}, ensure_ascii=False),
                             encoding="utf-8")
        # Simulate an ASCII default without changing the process locale or explicit UTF-8 reads.
        with mock.patch("io.text_encoding", side_effect=lambda encoding, *a: encoding or "ascii"):
            self.assertEqual(function_position(path, "目标", None), (4, 3))
            self.assertEqual(collect(self.root / "mutants", TABLE),
                             [{"id": "模块.x_目标__mutmut_1", "status": "survived"}])

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
        (self.root / "src/unchanged.py").write_text("def unchanged(x):\n    return x + 1\n")
        test = self.root / "tests/test_calc.py"
        test.write_text("from calc import choose\n\n\ndef test_choose():\n    assert choose(2, 1) == 2\n")
        (self.root / "pyproject.toml").write_text(
            '[tool.mutmut]\nsource_paths = ["src/"]\nonly_mutate = ["src/calc/*.py"]\n'
            'pytest_add_cli_args_test_selection = ["tests/"]\n')
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
        self.assertIn('function "choose" (src/calc/__init__.py:1)', result.stdout)
        self.assertIn("has 1 surviving mutants:", result.stdout)
        self.assertIn("2 -     if a > b:", result.stdout)
        self.assertIn("2 +     if a >= b:", result.stdout)
        self.assertIn("2 noCoverage", result.stdout)
        mutants = json.loads((self.root / "mutation.json").read_text())["mutants"]
        self.assertTrue(mutants)
        self.assertTrue(all(m["id"].startswith("calc.") for m in mutants), mutants)
        actionable = [m for m in mutants if m["status"] in ("survived", "noCoverage")]
        self.assertTrue(all(m.get("diff") and m.get("function") and m.get("line") for m in actionable), actionable)

        test.write_text("from calc import choose\n\n\ndef test_choose():\n    assert choose(2, 1) == 1\n")
        for path in ("mutants", "mutation.json"):
            subprocess.run(["rm", "-rf", path], cwd=self.root, check=True)
        result = run()
        self.assertEqual(result.returncode, 2, "a failing baseline must not produce a report")
        self.assertIn("Tool failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
