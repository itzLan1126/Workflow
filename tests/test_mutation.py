import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/workflow/scripts"
sys.path.insert(0, str(SCRIPTS))
from mutation import run_mutation, summarize
from run_report import read_json, run_report


def normalized(*statuses):
    return {"baselinePassed": True, "mutants": [{"status": s} for s in statuses]}


def cargo(*summaries):
    return {"total_mutants": len(summaries), "outcomes": [
        {"scenario": "Baseline", "summary": "Success", "phase_results": [{"phase": "Test"}]},
        *[{"scenario": {"Mutant": {}}, "summary": s, "phase_results": [{"phase": "Test"}]} for s in summaries],
    ]}


class MutationTests(unittest.TestCase):
    def fixture(self, report, exit_code=0, **overrides):
        temporary = tempfile.TemporaryDirectory(prefix="workflow-mutation-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        code = f"from pathlib import Path; Path('report.json').write_text({json.dumps(report)!r}); raise SystemExit({exit_code})"
        config = {"cwd": ".", "command": [sys.executable, "-c", code], "report": "report.json",
                  "format": "normalized", "timeoutMs": 5000, **overrides}
        path = root / "config.json"
        path.write_text(json.dumps(config))
        return path

    def test_native_adapters_preserve_outcomes(self):
        self.assertEqual(summarize(cargo("CaughtMutant"), "cargo-mutants")["exitCode"], 0)
        self.assertEqual(summarize(cargo("MissedMutant", "Timeout", "Unviable"), "cargo-mutants")["exitCode"], 1)
        stryker = summarize({"files": {"a.ts": {"mutants": [{"status": s} for s in
                            ["Killed", "NoCoverage", "CompileError"]]}}}, "stryker")
        self.assertEqual([stryker["counts"][s] for s in ["killed", "noCoverage", "unviable"]], [1, 1, 1])
        self.assertEqual(stryker["exitCode"], 1)
        swift = summarize({"fileReports": [{"appliedOperators": [{"testSuiteOutcome": s} for s in
                          ["passed", "failed", "runtimeError", "timeout"]]}]}, "muter")
        self.assertEqual((swift["counts"]["killed"], swift["counts"]["error"], swift["exitCode"]), (1, 1, 2))

    def test_invalid_and_untested_reports_cannot_pass(self):
        for report in [None, [], normalized(), {"mutants": [{"status": "killed"}]},
                       normalized("unknown"), normalized([]), {"baselinePassed": 1, "mutants": []}]:
            with self.subTest(report=report), self.assertRaises(ValueError):
                summarize(report, "normalized")
        self.assertEqual(summarize(normalized("unviable", "ignored"), "normalized")["exitCode"], 2)
        self.assertEqual(summarize(normalized("timeout"), "normalized")["exitCode"], 1)
        for report in [{"files": {}}, {"files": {"a": None}}, {"files": {"a": {"mutants": [None]}}}]:
            with self.assertRaises(ValueError):
                summarize(report, "stryker")
        no_baseline = cargo("CaughtMutant")
        no_baseline["outcomes"].pop(0)
        check_only = cargo("CaughtMutant")
        check_only["outcomes"][1]["phase_results"] = [{"phase": "Check"}]
        for report in [no_baseline, check_only, {**cargo("CaughtMutant"), "total_mutants": 2},
                       {**cargo("CaughtMutant"), "total_mutants": True}]:
            with self.assertRaises(ValueError):
                summarize(report, "cargo-mutants")

    def test_runner_evaluates_fresh_report_and_rejects_existing_links(self):
        path = self.fixture(normalized("killed", "survived"))
        result = run_mutation(path)
        self.assertEqual((result["exitCode"], result["counts"]["killed"]), (1, 1))
        with self.assertRaisesRegex(ValueError, "already exists"):
            run_mutation(path)
        path = self.fixture(normalized("killed"))
        (path.parent / "report.json").symlink_to(path.parent / "absent.json")
        with self.assertRaisesRegex(ValueError, "already exists"):
            run_mutation(path)

    def test_engine_exits_do_not_mask_failures(self):
        self.assertEqual(run_mutation(self.fixture(cargo("MissedMutant"), 2, format="cargo-mutants"))["exitCode"], 1)
        with self.assertRaisesRegex(ValueError, "Tool failed"):
            run_mutation(self.fixture(normalized("killed"), 9))
        with self.assertRaisesRegex(ValueError, "without reported findings"):
            run_mutation(self.fixture(cargo("CaughtMutant"), 2, format="cargo-mutants"))
        report = {"files": {"a.ts": {"mutants": [{"status": "Survived"}]}}}
        self.assertEqual(run_mutation(self.fixture(report, format="stryker"))["exitCode"], 1)
        with self.assertRaisesRegex(ValueError, "Tool failed"):
            run_mutation(self.fixture(report, 1, format="stryker"))

    def test_runner_rejects_invalid_commands_timeouts_and_missing_reports(self):
        for overrides in [{"command": []}, {"timeoutMs": -1}, {"timeoutMs": True}, {"cwd": ""}]:
            with self.subTest(overrides=overrides), self.assertRaisesRegex(ValueError, "Require"):
                run_report(self.fixture(normalized("killed"), **overrides))
        with self.assertRaises(OSError):
            run_report(self.fixture({}, command=["workflow-nonexistent-mutation-tool"]))
        with self.assertRaisesRegex(ValueError, "timeoutMs"):
            run_report(self.fixture({}, command=[sys.executable, "-c", "import time; time.sleep(60)"], timeoutMs=100))
        with self.assertRaises(FileNotFoundError):
            run_report(self.fixture({}, command=[sys.executable, "-c", "pass"]))

    def test_json_rejects_nonfinite_numbers(self):
        path = self.fixture({})
        for raw in ['{"value":NaN}', '{"value":Infinity}', '{"value":-Infinity}', '{"value":1e999}']:
            path.write_text(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                read_json(path)

    def test_cli_exit_codes_and_json_output(self):
        for statuses, expected in [(('killed',), 0), (('survived',), 1), (('error',), 2)]:
            path = self.fixture(normalized(*statuses))
            result = subprocess.run([sys.executable, str(SCRIPTS / 'mutation.py'), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, expected, result.stderr)
            self.assertEqual(json.loads(result.stdout)["exitCode"], expected)
        for raw in ["null", "[]", '{"format":[]}', '{"baselinePassed":NaN}']:
            path = self.fixture({})
            path.write_text(raw)
            result = subprocess.run([sys.executable, str(SCRIPTS / 'mutation.py'), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("Traceback", result.stderr)
        result = subprocess.run([sys.executable, str(SCRIPTS / 'mutation.py')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage:", result.stderr)


if __name__ == "__main__":
    unittest.main()
