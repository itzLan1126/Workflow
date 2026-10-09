"""Bounded checks of process ownership and deadline propagation."""

import io
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/workflow/scripts"
sys.path.insert(0, str(SCRIPTS))
import run_report


class CommandRunnerTests(unittest.TestCase):
    def test_requested_deadline_reaches_tool(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config.json"
            config.write_text('{"cwd":".","report":"report.json","command":["tool"],"timeoutMs":1234}')

            def run(command, cwd, timeout):
                self.assertEqual(command, ["tool"])
                self.assertEqual(cwd, root.resolve())
                self.assertEqual(timeout, 1234)
                (root / "report.json").write_text('{}')
                return 0

            with mock.patch.object(run_report, "run_command", side_effect=run):
                self.assertEqual(run_report.run_report(config)["report"], {})

    @unittest.skipUnless(os.name == "posix", "POSIX process groups")
    def test_kill_group_precedes_reaping(self):
        events = []
        child = mock.Mock(pid=12345)
        child.wait.side_effect = lambda: events.append("reaped")

        def kill(pid, sig):
            self.assertEqual((pid, sig), (12345, signal.SIGKILL))
            events.append("killed")

        with mock.patch.object(run_report.os, "killpg", side_effect=kill):
            run_report.stop(child)
        self.assertEqual(events, ["killed", "reaped"])
        child.wait.assert_called_once_with()

    @unittest.skipUnless(os.name == "posix", "POSIX process groups")
    def test_command_owns_group_and_converts_milliseconds(self):
        process = mock.MagicMock()
        child = process.__enter__.return_value
        child.wait.return_value = 17
        command = ["tool", "argument with spaces", "$(literal)"]
        with mock.patch.object(run_report.subprocess, "Popen", return_value=process) as start:
            self.assertEqual(run_report.run_command(command, "analysis-directory", 1234), 17)
        self.assertEqual(start.call_count, 1)
        self.assertEqual(start.call_args.args, (command,))
        options = dict(start.call_args.kwargs)
        self.assertFalse(options.pop("shell", False))
        self.assertEqual(options, dict(cwd="analysis-directory", stdin=subprocess.DEVNULL,
                                       stdout=sys.stderr, stderr=sys.stderr, start_new_session=True))
        child.wait.assert_called_once_with(timeout=1.234)

    @unittest.skipUnless(os.name == "posix", "POSIX process groups")
    def test_timeout_terminates_owned_group_before_returning(self):
        process = mock.MagicMock()
        child = process.__enter__.return_value
        child.pid = 12345
        timeout = subprocess.TimeoutExpired("tool", 1.234)
        child.wait.side_effect = [timeout, 0]
        with mock.patch.object(run_report.subprocess, "Popen", return_value=process), \
                mock.patch.object(run_report.os, "killpg") as kill, \
                self.assertRaises(ValueError) as raised:
            run_report.run_command(["tool"], ".", 1234)
        self.assertIs(raised.exception.__cause__, timeout)
        kill.assert_called_once_with(12345, signal.SIGKILL)
        self.assertEqual(child.wait.call_args_list, [mock.call(timeout=1.234), mock.call()])

    def test_json_encoding_is_independent_of_locale(self):
        encoded = '{"中文":"😀"}'.encode("utf-8")

        def read(path, *, encoding=None):
            return io.TextIOWrapper(io.BytesIO(encoded), encoding=encoding or "ascii").read()

        with mock.patch.object(Path, "read_text", autospec=True, side_effect=read):
            self.assertEqual(run_report.read_json("report.json"), {"中文": "😀"})


if __name__ == "__main__":
    unittest.main()
