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
from mutation import MAPS, main, run_mutation, summarize
from mutation_report import function_at, numbered_diff, report_details, source_offset
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
        path = self.fixture(normalized("killed"))
        self.assertEqual(run_mutation(path), {
            "format": "normalized", "assessed": 1, "exitCode": 0, "toolExitCode": 0, "counts": {
                "killed": 1, "survived": 0, "noCoverage": 0, "timeout": 0, "unviable": 0, "ignored": 0, "error": 0},
            "mutants": [], "reportPath": str((path.parent / "report.json").resolve())})
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
        self.assertEqual(run_report(path), {"config": config, "report": {"done": True},
                                            "reportPath": (path.parent / "report.json").resolve(), "exitCode": 0})

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

    def test_human_report_groups_survivors_and_numbers_each_diff(self):
        mutants = [{"id": str(index), "status": "survived", "file": "demo.js", "function": "power",
                    "line": 42, "diff": f"--- demo.js\n+++ demo.js\n@@ -43 +43 @@\n-    return x ** y\n+    return x {operator} y"}
                   for index, operator in enumerate(("+", "*"), 1)]
        report = {"baselinePassed": True, "mutants": [*mutants, {"id": "3", "status": "timeout",
                  "diffOffset": None, "detailGap": "Engine timed out", "evidence": "mutants/3.log"}]}
        code, stdout, stderr = self.run_main([str(self.fixture(report))])
        self.assertEqual(code, 1, stderr)
        self.assertIn('function "power" (demo.js:42)\nhas 2 surviving mutants:', stdout)
        self.assertIn("43 -     return x ** y\n43 +     return x + y", stdout)
        self.assertIn("43 +     return x * y", stdout)
        for identifier, status in (("1", "survived"), ("2", "survived"), ("3", "timeout")):
            self.assertIn(f"mutant {identifier} [{status}]", stdout)
        self.assertIn("has 1 timed-out mutants:", stdout)
        self.assertIn("Diff unavailable", stdout)
        self.assertIn("0 killed, 2 survived", stdout)
        self.assertIn("Report:", stdout)
        self.assertIn("Engine timed out\nEvidence: mutants/3.log", stdout)

    def test_numbered_diff_handles_context_multiple_hunks_and_offsets(self):
        diff = "--- a\n+++ a\n@@ -1,2 +1,3 @@\n same\n-old\n+new\n+extra\n@@ -9 +10 @@\n-last\n+final\n\\ No newline at end of file"
        self.assertEqual(numbered_diff(diff, 40), "42 - old\n42 + new\n43 + extra\n49 - last\n50 + final")
        self.assertEqual(numbered_diff("not a unified diff"), "")

    def test_stryker_details_use_report_source_and_utf16_positions(self):
        source = 'function power(x, y) {\n    return "😀" + x ** y;\n}\n'
        mutant = {"id": "1", "status": "Survived", "replacement": "+",
                  "location": {"start": {"line": 2, "column": 21}, "end": {"line": 2, "column": 23}}}
        report = {"files": {"missing/demo.js": {"source": source, "mutants": [mutant]}}}
        details = report_details(report, "stryker", Path("/tmp/report.json"), MAPS)
        self.assertEqual(details[0]["function"], "power")
        self.assertEqual((details[0]["id"], details[0]["file"], details[0]["line"], details[0]["status"]),
                         ("1", "missing/demo.js", 1, "survived"))
        self.assertIn('2 +     return "😀" + x + y;', numbered_diff(details[0]["diff"]))
        self.assertEqual(source_offset(source, {"line": 4, "column": 1}), len(source))
        for position in ({"line": 0, "column": 1}, {"line": 2, "column": 99},
                         {"line": True, "column": 1}, {"line": 2, "column": False}):
            with self.assertRaisesRegex(ValueError, "Invalid Stryker source position"):
                source_offset(source, position)
        mutant["location"] = {}
        self.assertIn("detailGap", report_details(report, "stryker", Path("/tmp/report.json"), MAPS)[0])
        with mock.patch.dict(sys.modules, {"lizard": None}):
            self.assertEqual(function_at("demo.js", source, 2), {})
        self.assertEqual(function_at("demo.js", "const x = 1;", 1), {})

    def test_invalid_optional_details_do_not_crash_or_pass(self):
        for field, value in (("file", []), ("function", []), ("diff", 42), ("diffOffset", True), ("line", "8"),
                             ("detailGap", []), ("evidence", {})):
            report = {"baselinePassed": True, "mutants": [{"status": "survived", field: value}]}
            code, stdout, stderr = self.run_main([str(self.fixture(report))])
            self.assertEqual((code, stdout), (2, ""))
            self.assertIn(f"Invalid mutation detail field: {field}", stderr)

    def test_cargo_and_muter_details_keep_native_evidence(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "change.diff").write_text("@@ -7 +7 @@\n-false\n+true")
        report = cargo("MissedMutant")
        outcome = report["outcomes"][1]
        outcome.update(diff_path="change.diff")
        outcome["scenario"]["Mutant"] = {"name": "replace bool", "file": "src/lib.rs",
            "function": {"function_name": "choose", "span": {"start": {"line": 6}}}}
        detail = report_details(report, "cargo-mutants", root / "outcomes.json", MAPS)[0]
        self.assertEqual((detail["function"], detail["line"]), ("choose", 6))
        self.assertEqual((detail["id"], detail["file"], detail["status"]),
                         ("replace bool", "src/lib.rs", "survived"))
        self.assertEqual(Path(detail["evidence"]), (root / "change.diff").resolve())
        self.assertEqual(numbered_diff(detail["diff"]), "7 - false\n7 + true")
        outcome["diff_path"] = "missing.diff"
        self.assertIn("Cannot read diff", report_details(report, "cargo-mutants", root / "outcomes.json", MAPS)[0]["detailGap"])
        outcome["diff_path"] = "../outside.diff"
        self.assertIn("inside the report directory", report_details(report, "cargo-mutants", root / "outcomes.json", MAPS)[0]["detailGap"])
        swift = {"fileReports": [{"fileName": "Demo.swift", "appliedOperators": [{
            "testSuiteOutcome": "passed", "mutationPoint": {"mutationOperatorId": "Swap", "position": {"line": 8}},
            "mutationSnapshot": {"before": "x > y", "after": "x < y"}}]}]}
        detail = report_details(swift, "muter", root / "swift.json", MAPS)[0]
        self.assertEqual(numbered_diff(detail["diff"], detail["diffOffset"]), "8 - x > y\n8 + x < y")
        self.assertIn("function name is unavailable", detail["detailGap"])
        self.assertEqual((detail["id"], detail["file"], detail["line"], detail["status"]),
                         ("Swap", "Demo.swift", 8, "survived"))

    def test_function_locations_include_boundaries_and_choose_innermost(self):
        source = ("function outer() {\n const a = 1;\n const b = 2;\n const c = 3;\n"
                  " function inner() {\n return 1;\n }\n return inner();\n}\n")
        for line, name, start in ((1, "outer", 1), (9, "outer", 1), (5, "inner", 5),
                                  (6, "inner", 5), (7, "inner", 5)):
            with self.subTest(line=line):
                self.assertEqual(function_at("nested.js", source, line), {"function": name, "line": start})

    def test_stryker_offsets_accept_utf16_boundaries_and_reject_past_end(self):
        source = "ab\r\n😀x"
        for line, column, offset in ((1, 1, 0), (1, 3, 2), (2, 1, 4), (2, 3, 5), (2, 4, 6)):
            with self.subTest(line=line, column=column):
                self.assertEqual(source_offset(source, {"line": line, "column": column}), offset)
        for line, column in ((1, 4), (2, 5), (3, 1)):
            with self.subTest(line=line, column=column), self.assertRaises(ValueError):
                source_offset(source, {"line": line, "column": column})

    def test_stryker_top_level_insertions_and_missing_source_keep_identity(self):
        location = {"start": {"line": 1, "column": 2}, "end": {"line": 1, "column": 2}}
        mutant = {"id": "insert-1", "status": "Survived", "replacement": "x", "location": location}
        for data in ({"source": "abc", "mutants": [mutant]}, {"mutants": [mutant]},
                     {"source": "abc", "mutants": [{"id": "insert-1", "status": "Survived"}]}):
            with self.subTest(data=data):
                detail = report_details({"files": {"top.js": data}}, "stryker", Path("report.json"), MAPS)[0]
                self.assertEqual((detail["id"], detail["file"], detail["status"]),
                                 ("insert-1", "top.js", "survived"))
                self.assertNotIn("detailGap", detail)
                if "source" in data and "location" in data["mutants"][0]:
                    self.assertEqual(detail["line"], 1)
                    self.assertIn("1 + axbc", numbered_diff(detail["diff"]))
                else:
                    self.assertNotIn("diff", detail)

    def test_native_detail_errors_preserve_file_and_available_identifier(self):
        stryker = {"files": {"demo.js": {"source": "abc", "mutants": [
            {"id": "S1", "status": "Survived", "location": {}}]}}}
        cargo_report = cargo("MissedMutant")
        cargo_report["outcomes"][1]["scenario"]["Mutant"] = {"name": "C1", "file": "a.rs", "function": 42}
        muter = {"fileReports": [{"fileName": "a.swift", "appliedOperators": [
            {"testSuiteOutcome": "passed", "mutationPoint": 42}]}]}
        for report, format, file, identifier in ((stryker, "stryker", "demo.js", "S1"),
                (cargo_report, "cargo-mutants", "a.rs", "C1"), (muter, "muter", "a.swift", None)):
            with self.subTest(format=format):
                detail = report_details(report, format, Path("report.json"), MAPS)[0]
                self.assertEqual((detail["file"], detail["status"]), (file, "survived"))
                if identifier is not None:
                    self.assertEqual(detail["id"], identifier)
                self.assertTrue(detail["detailGap"])
                self.assertNotIn("diff", detail)

    def test_cargo_span_fallback_and_missing_fields_preserve_metadata(self):
        for extras, expected_line in (({"span": {"start": {"line": 9}}}, 9), ({}, None),
                                     ({"span": {}}, None),
                                     ({"function": {"function_name": "choose", "span": {}}}, None)):
            report = cargo("MissedMutant")
            report["outcomes"][1]["scenario"]["Mutant"] = {"name": "C1", "file": "a.rs", **extras}
            with self.subTest(extras=extras):
                detail = report_details(report, "cargo-mutants", Path("report.json"), MAPS)[0]
                self.assertEqual((detail["id"], detail["file"], detail["status"], detail.get("line")),
                                 ("C1", "a.rs", "survived", expected_line))
                self.assertNotIn("detailGap", detail)
                if "function" in extras:
                    self.assertEqual(detail["function"], "choose")

    def test_muter_incomplete_snapshots_and_positions_preserve_metadata(self):
        for point, snapshot in (({"position": {"line": 20}}, {"before": 1, "after": "x"}),
                ({"position": {"line": 20}}, {"before": "x"}), ({}, {})):
            mutant = {"testSuiteOutcome": "passed", "mutationPoint": {"mutationOperatorId": "Swap", **point},
                      "mutationSnapshot": snapshot}
            report = {"fileReports": [{"fileName": "Demo.swift", "appliedOperators": [mutant]}]}
            with self.subTest(point=point, snapshot=snapshot):
                detail = report_details(report, "muter", Path("report.json"), MAPS)[0]
                self.assertEqual((detail["id"], detail["file"], detail["status"]),
                                 ("Swap", "Demo.swift", "survived"))
                self.assertEqual(detail.get("line"), point.get("position", {}).get("line"))
                self.assertNotIn("diff", detail)
                self.assertNotIn("detailGap", detail)

    def test_numbered_diff_tracks_consecutive_changes_and_no_newline_markers(self):
        diff = ("@@ -1,4 +1,4 @@\n-a\n-b\n+c\n+d\n same\n-e\n"
                "\\ No newline at end of file\n+f\n\\ No newline at end of file")
        self.assertEqual(numbered_diff(diff), "1 - a\n2 - b\n1 + c\n2 + d\n4 - e\n4 + f")

    def test_human_report_preserves_offsets_and_nonpassing_statuses(self):
        report = {"baselinePassed": True, "mutants": [{"id": status, "status": status,
                  "file": "snippet.swift", "line": 20, "diffOffset": 19,
                  "diff": "@@ -1 +1 @@\n-x\n+y"} for status in ("noCoverage", "error")]}
        code, stdout, stderr = self.run_main([str(self.fixture(report))])
        self.assertEqual(code, 2, stderr)
        for status in ("noCoverage", "error"):
            self.assertIn(f"mutant {status} [{status}]", stdout)
        self.assertIn("20 - x\n20 + y", stdout)
        self.assertIn("snippet.swift:20", stdout)
        self.assertIn("1 uncovered mutants", stdout)
        self.assertIn("1 error mutants", stdout)

    def test_cargo_unicode_diff_uses_utf8_even_when_default_encoding_is_ascii(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            diff = "@@ -7 +7 @@\n-中文\n+😀"
            (root / "change.diff").write_bytes(diff.encode("utf-8"))
            report = cargo("MissedMutant")
            report["outcomes"][1].update(diff_path="change.diff")
            report["outcomes"][1]["scenario"]["Mutant"] = {"name": "Unicode", "file": "a.rs"}
            with mock.patch("io.text_encoding", side_effect=lambda encoding, *args: encoding or "ascii"):
                with self.assertRaises(UnicodeDecodeError):
                    (root / "change.diff").read_text()
                detail = report_details(report, "cargo-mutants", root / "outcomes.json", MAPS)[0]
            self.assertEqual(detail["diff"], diff)
            self.assertEqual(Path(detail["evidence"]), (root / "change.diff").resolve())
            self.assertNotIn("detailGap", detail)

    def test_cargo_runner_resolves_and_reads_diff_from_configured_directory(self):
        report = cargo("MissedMutant")
        report["outcomes"][1].update(diff_path="change.diff")
        report["outcomes"][1]["scenario"]["Mutant"] = {"name": "C1", "file": "a.rs"}
        diff = "@@ -7 +7 @@\n-中文\n+😀"
        code = (f"from pathlib import Path; Path('change.diff').write_bytes({diff.encode('utf-8')!r}); "
                f"Path('report.json').write_text({json.dumps(report)!r})")
        path = self.fixture(report, format="cargo-mutants", cwd="execution",
                            command=[sys.executable, "-c", code])
        (path.parent / "execution").mkdir()
        result = run_mutation(path)
        detail = result["mutants"][0]
        self.assertEqual((result["exitCode"], detail["id"], detail["file"], detail["status"]),
                         (1, "C1", "a.rs", "survived"))
        self.assertEqual(detail["diff"], diff)
        self.assertEqual(Path(detail["evidence"]), (path.parent / "execution/change.diff").resolve())
        self.assertEqual(Path(result["reportPath"]), (path.parent / "execution/report.json").resolve())

    def test_cli_exit_codes_and_json_output(self):
        for statuses, expected in [(("killed",), 0), (("survived",), 1), (("error",), 2)]:
            exit_code, stdout, stderr = self.run_main(["--json", str(self.fixture(normalized(*statuses)))])
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
        self.assertEqual(self.run_main([]), (2, "", "mutation: Usage: python mutation.py [--json] CONFIG.json\n"))

    def test_script_entrypoint(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "mutation.py")], capture_output=True, text=True)
        self.assertEqual((result.returncode, result.stderr), (2, "mutation: Usage: python mutation.py [--json] CONFIG.json\n"))


if __name__ == "__main__":
    unittest.main()
