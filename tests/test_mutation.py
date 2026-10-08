from contextlib import contextmanager, redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/workflow/scripts"
sys.path.insert(0, str(SCRIPTS))
from mutation import main, run_mutation, summarize
from run_report import read_json, run_report, run_command

REQUIRE = r"^Require cwd, report, nonempty command argv and positive timeoutMs \(max 2147483647\)$"
NO_BASELINE = r"^cargo-mutants requires a successful baseline test \(do not use --check or --baseline skip\)$"


def normalized(*statuses):
    return {"baselinePassed": True, "mutants": [{"status": s} for s in statuses]}


def cargo(*summaries):
    return {"total_mutants": len(summaries), "outcomes": [
        {"scenario": "Baseline", "summary": "Success", "phase_results": [{"phase": "Test"}]},
        *[{"scenario": {"Mutant": {}}, "summary": s, "phase_results": [{"phase": "Test"}]} for s in summaries],
    ]}


def alive(pid):
    try:
        os.kill(pid, 0)
        if sys.platform == "linux":
            # An orphan can stay as a zombie when container PID 1 does not reap it.
            # The comm field may contain spaces or parentheses; state follows its last ')'.
            state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
            return state != "Z"
    except ProcessLookupError:
        return False
    except FileNotFoundError:
        return False  # Reaped between kill(0) and reading /proc.
    return True


@contextmanager
def descriptor(fd, file):
    """Point a process-level file descriptor at file, as child processes would inherit it."""
    sys.stdout.flush()
    saved = os.dup(fd)
    os.dup2(file.fileno(), fd)
    try:
        yield
    finally:
        os.dup2(saved, fd)
        os.close(saved)


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

    def test_summary_counts_every_mutant(self):
        result = summarize(normalized("killed", "killed", "survived", "unviable"), "normalized")
        self.assertEqual(result, {"format": "normalized", "assessed": 3, "exitCode": 1, "counts": {
            "killed": 2, "survived": 1, "noCoverage": 0, "timeout": 0, "unviable": 1, "ignored": 0, "error": 0}})
        self.assertEqual(summarize(normalized("survived", "noCoverage"), "normalized")["exitCode"], 1)

    def test_invalid_and_untested_reports_cannot_pass(self):
        cases = [(None, "^Expected an object in mutation report$"), ([], "^Expected an object in mutation report$"),
                 (normalized(), "^No mutations reported$"),
                 ({"mutants": [{"status": "killed"}]}, "^Normalized report must confirm baselinePassed: true$"),
                 ({"baselinePassed": 1, "mutants": []}, "^Normalized report must confirm baselinePassed: true$"),
                 (normalized("unknown"), "^Unknown mutation status: unknown$"),
                 (normalized([]), r"^Invalid mutation status: \[\]$")]
        for report, message in cases:
            with self.subTest(report=report), self.assertRaisesRegex(ValueError, message):
                summarize(report, "normalized")
        self.assertEqual(summarize(normalized("unviable", "ignored"), "normalized")["exitCode"], 2)
        self.assertEqual(summarize(normalized("timeout"), "normalized")["exitCode"], 1)
        for report, message in [({"files": {}}, "^No mutations reported$"),
                                ({"files": {"a": None}}, "^Expected an object in mutation report$"),
                                ({"files": {"a": {"mutants": [None]}}}, "^Expected an object in mutation report$"),
                                ({"files": {"a": {"mutants": None}}}, "^Expected an array in mutation report$")]:
            with self.subTest(report=report), self.assertRaisesRegex(ValueError, message):
                summarize(report, "stryker")
        no_baseline = cargo("CaughtMutant")
        no_baseline["outcomes"].pop(0)
        untested_baseline = cargo("CaughtMutant")
        untested_baseline["outcomes"][0]["phase_results"] = [{"phase": "Build"}]
        check_only = cargo("CaughtMutant")
        check_only["outcomes"][1]["phase_results"] = [{"phase": "Check"}]
        untested_miss = cargo("MissedMutant")
        untested_miss["outcomes"][1]["phase_results"] = [{"phase": "Check"}]
        for report, message in [(no_baseline, NO_BASELINE), (untested_baseline, NO_BASELINE),
                                (check_only, "^Missing mutation test phase$"),
                                (untested_miss, "^Missing mutation test phase$"),
                                ({**cargo("CaughtMutant"), "total_mutants": 2}, "^Inconsistent cargo-mutants count$"),
                                ({**cargo("CaughtMutant"), "total_mutants": True}, "^Inconsistent cargo-mutants count$")]:
            with self.subTest(report=report), self.assertRaisesRegex(ValueError, message):
                summarize(report, "cargo-mutants")
        with self.assertRaisesRegex(ValueError, "^Unsupported mutation format: bogus$"):
            summarize(normalized("killed"), "bogus")

    def test_runner_evaluates_fresh_report_and_rejects_existing_links(self):
        self.assertEqual(run_mutation(self.fixture(normalized("killed"))), {
            "format": "normalized", "assessed": 1, "exitCode": 0, "toolExitCode": 0, "counts": {
                "killed": 1, "survived": 0, "noCoverage": 0, "timeout": 0, "unviable": 0, "ignored": 0, "error": 0}})
        path = self.fixture(normalized("killed", "survived"))
        result = run_mutation(path)
        self.assertEqual((result["exitCode"], result["counts"]["killed"]), (1, 1))
        fresh = "^Report already exists; select a fresh report path to avoid stale results$"
        with self.assertRaisesRegex(ValueError, fresh):
            run_mutation(path)
        path = self.fixture(normalized("killed"))
        (path.parent / "report.json").symlink_to(path.parent / "absent.json")
        with self.assertRaisesRegex(ValueError, fresh):
            run_mutation(path)

    def test_engine_exits_do_not_mask_failures(self):
        self.assertEqual(run_mutation(self.fixture(cargo("MissedMutant"), 2, format="cargo-mutants"))["exitCode"], 1)
        with self.assertRaisesRegex(ValueError, "^Tool failed: exit 9$"):
            run_mutation(self.fixture(normalized("killed"), 9))
        with self.assertRaisesRegex(ValueError, "^Tool exited 2 without reported findings$"):
            run_mutation(self.fixture(cargo("CaughtMutant"), 2, format="cargo-mutants"))
        report = {"files": {"a.ts": {"mutants": [{"status": "Survived"}]}}}
        self.assertEqual(run_mutation(self.fixture(report, format="stryker"))["exitCode"], 1)
        with self.assertRaisesRegex(ValueError, "^Tool failed: exit 1$"):
            run_mutation(self.fixture(report, 1, format="stryker"))

    def test_unsupported_format_is_rejected_before_running_the_tool(self):
        path = self.fixture(normalized("killed"), format="bogus")
        with self.assertRaisesRegex(ValueError, "^Unsupported mutation format: bogus$"):
            run_mutation(path)
        self.assertFalse((path.parent / "report.json").exists())

    def test_runner_rejects_invalid_commands_timeouts_and_missing_reports(self):
        for overrides in [{"command": []}, {"command": [sys.executable, ""]}, {"timeoutMs": -1}, {"timeoutMs": 0},
                          {"timeoutMs": 2147483648}, {"timeoutMs": True}, {"cwd": ""}, {"cwd": 5},
                          {"report": ""}, {"report": 5}]:
            path = self.fixture(normalized("killed"))
            path.write_text(json.dumps({**json.loads(path.read_text()), **overrides}))
            with self.subTest(overrides=overrides), self.assertRaisesRegex(ValueError, REQUIRE):
                run_report(path)
        with self.assertRaisesRegex(ValueError, "^cwd must be a directory$"):
            run_report(self.fixture({}, cwd="missing"))
        path = self.fixture({})
        path.write_text("[]")
        with self.assertRaisesRegex(ValueError, "^Configuration must be an object$"):
            run_report(path)
        with self.assertRaises(OSError):
            run_report(self.fixture({}, command=["workflow-nonexistent-mutation-tool"]))
        sleep = [sys.executable, "-c", "import time; time.sleep(60)"]
        for timeout in [1, 100]:
            with self.subTest(timeout=timeout), self.assertRaisesRegex(ValueError, "^Tool exceeded timeoutMs$"):
                run_report(self.fixture({}, command=sleep, timeoutMs=timeout))
        with self.assertRaises(FileNotFoundError):
            run_report(self.fixture({}, command=[sys.executable, "-c", "pass"]))
        with self.assertRaisesRegex(ValueError, "^Report must be a regular file$"):
            run_report(self.fixture({}, command=[sys.executable, "-c", "import os; os.mkdir('report.json')"]))

    def test_runner_accepts_timeout_bounds_and_default(self):
        self.assertEqual(run_report(self.fixture({}, timeoutMs=2147483647))["report"], {})
        path = self.fixture({"done": True})
        config = json.loads(path.read_text())
        del config["timeoutMs"]
        path.write_text(json.dumps(config))
        self.assertEqual(run_report(path), {"config": config, "report": {"done": True}, "exitCode": 0})

    def test_tool_cannot_read_stdin_or_write_to_stdout(self):
        code = ("import os, sys; from pathlib import Path; print('tool noise', flush=True); "
                "print('tool error', file=sys.stderr, flush=True); "
                "Path('report.json').write_text(str(os.path.samestat(os.fstat(0), os.stat(os.devnull))).lower())")
        path = self.fixture({}, command=[sys.executable, "-c", code])
        read_end, write_end = os.pipe()
        self.addCleanup(os.close, write_end)
        with os.fdopen(read_end) as stdin, tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile("w+") as stderr, \
                descriptor(0, stdin), descriptor(1, stdout), redirect_stderr(stderr):
            result = run_report(path)
            stdout.seek(0)
            stderr.seek(0)
            self.assertEqual((stdout.read(), stderr.read()), (b"", "tool noise\ntool error\n"))
        self.assertIs(result["report"], True)

    @unittest.skipUnless(os.name == "posix", "process groups are POSIX-only")
    def test_timeout_kills_the_whole_process_group(self):
        code = ("import subprocess, sys, time; from pathlib import Path; "
                "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
                "Path('grandchild.pid').write_text(str(child.pid)); time.sleep(60)")
        path = self.fixture({}, command=[sys.executable, "-c", code], timeoutMs=2000)
        with self.assertRaisesRegex(ValueError, "^Tool exceeded timeoutMs$"):
            run_report(path)
        pid = int((path.parent / "grandchild.pid").read_text())
        self.addCleanup(lambda: alive(pid) and os.kill(pid, signal.SIGKILL))
        deadline = time.monotonic() + 5
        while alive(pid) and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertFalse(alive(pid), "a grandchild process outlived the timeout")

    def test_windows_commands_use_job_lifetime_tracking(self):
        with mock.patch("run_report.os.name", "nt"), mock.patch("run_report.run_windows", return_value=17) as run:
            self.assertEqual(run_command(["tool"], "directory", 1234), 17)
        run.assert_called_once_with(["tool"], "directory", 1234)

    def test_json_rejects_nonfinite_numbers(self):
        path = self.fixture({})
        for raw, token in [('{"value":NaN}', "NaN"), ('{"value":Infinity}', "Infinity"),
                           ('{"value":-Infinity}', "-Infinity"), ('{"value":1e999}', "1e999")]:
            path.write_text(raw)
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, f"^Non-finite JSON number: {re.escape(token)}$"):
                read_json(path)

    def run_main(self, argv):
        # The runner hands tool output to the stderr file descriptor, so stderr must be a real file.
        with tempfile.TemporaryFile("w+") as stderr, redirect_stderr(stderr), \
                redirect_stdout(io.StringIO()) as stdout:
            exit_code = main(argv)
            stderr.seek(0)
            return exit_code, stdout.getvalue(), stderr.read()

    def test_cli_exit_codes_and_json_output(self):
        for statuses, expected in [(("killed",), 0), (("survived",), 1), (("error",), 2)]:
            exit_code, stdout, stderr = self.run_main([str(self.fixture(normalized(*statuses)))])
            self.assertEqual(exit_code, expected, stderr)
            self.assertEqual(json.loads(stdout)["exitCode"], expected)
        for raw, message in [("null", "Expected an object in mutation report"),
                             ("[]", "Expected an object in mutation report"),
                             ('{"format":[]}', r"Unsupported mutation format: \[\]"),
                             ('{"baselinePassed":NaN}', "Non-finite JSON number: NaN")]:
            path = self.fixture({})
            path.write_text(raw)
            exit_code, stdout, stderr = self.run_main([str(path)])
            self.assertEqual((exit_code, stdout), (2, ""))
            self.assertRegex(stderr, f"^mutation: {message}\n$")
        with mock.patch.object(sys, "argv", ["mutation.py", str(self.fixture(normalized("killed")))]):
            self.assertEqual(self.run_main(None)[0], 0)
        self.assertEqual(self.run_main([]), (2, "", "mutation: Usage: python mutation.py CONFIG.json\n"))

    def test_script_entrypoint(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "mutation.py")], capture_output=True, text=True)
        self.assertEqual((result.returncode, result.stderr), (2, "mutation: Usage: python mutation.py CONFIG.json\n"))


if __name__ == "__main__":
    unittest.main()
