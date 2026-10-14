"""Bounded checks of process ownership and deadline propagation."""

import io
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/workflow/scripts"
sys.path.insert(0, str(SCRIPTS))
import shared_runner as run_report


class CommandRunnerTests(unittest.TestCase):
    def test_runner_accepts_configuration_already_read_by_caller(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = {"cwd": ".", "report": "report.json",
                      "command": [sys.executable, "-c", "from pathlib import Path; Path('report.json').write_text('{}')"]}
            self.assertEqual(run_report.run_report(root / "config.json", config=config)["report"], {})

    def test_requested_deadline_reaches_tool(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config.json"
            config.write_text('{"cwd":".","report":"report.json","command":["tool"],"timeoutMs":1234}')

            def run(command, cwd, timeout, *, env):
                self.assertEqual(command, ["tool"])
                self.assertEqual(cwd, root.resolve())
                self.assertEqual(timeout, 1234)
                self.assertEqual(env, {**os.environ, "WORKFLOW_REPORT_FILE": str((root / "report.json").resolve())})
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
        child.pid = 12345
        child.wait.return_value = 17
        command = ["tool", "argument with spaces", "$(literal)"]
        with mock.patch.object(run_report.subprocess, "Popen", return_value=process) as start, \
                mock.patch.object(run_report.os, "killpg") as kill:
            self.assertEqual(run_report.run_command(command, "analysis-directory", 1234), 17)
        self.assertEqual(start.call_count, 1)
        self.assertEqual(start.call_args.args, (command,))
        options = dict(start.call_args.kwargs)
        self.assertFalse(options.pop("shell", False))
        self.assertEqual(options, dict(cwd="analysis-directory", stdin=subprocess.DEVNULL,
                                       stdout=sys.stderr, stderr=sys.stderr, start_new_session=True, env=None))
        self.assertEqual(child.wait.call_args_list, [mock.call(timeout=1.234), mock.call()])
        kill.assert_called_once_with(12345, signal.SIGKILL)

    @unittest.skipUnless(os.name == "posix", "POSIX process groups")
    def test_normal_root_exit_stops_background_report_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            writer = ('import time; from pathlib import Path; Path("ready").touch(); '
                      'time.sleep(0.4); Path("report.json").write_text("{\\"late\\":true}")')
            tool = ('import subprocess,sys,time; from pathlib import Path; '
                    'Path("report.json").write_text("{}"); '
                    f'subprocess.Popen([sys.executable,"-c",{writer!r}]); '
                    '\nwhile not Path("ready").exists(): time.sleep(0.01)')
            config = {'cwd': '.', 'report': 'report.json', 'timeoutMs': 2000,
                      'command': [sys.executable, '-c', tool]}
            result = run_report.run_report(root / 'config.json', config=config)
            self.assertEqual(result['report'], {})
            self.assertTrue((root / 'ready').exists())
            time.sleep(0.5)
            self.assertEqual(run_report.read_json(root / 'report.json'), {})

    @unittest.skipUnless(os.name == "posix", "POSIX process groups")
    def test_cleanup_failure_preserves_timeout_classification(self):
        process = mock.MagicMock()
        child = process.__enter__.return_value
        timeout = subprocess.TimeoutExpired('tool', 1)
        child.wait.side_effect = timeout
        cleanup = OSError('cleanup failed')
        with mock.patch.object(run_report.subprocess, 'Popen', return_value=process), \
                mock.patch.object(run_report, 'stop', side_effect=cleanup), \
                self.assertRaisesRegex(ValueError, '^Tool exceeded timeoutMs$') as raised:
            run_report.run_command(['tool'], '.', 1000)
        self.assertIs(raised.exception.__cause__, timeout)
        self.assertIs(timeout.__cause__, cleanup)

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
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.json'
            path.write_bytes(encoded)
            with mock.patch.object(io, 'text_encoding', side_effect=lambda encoding, *args: encoding or 'ascii'):
                self.assertEqual(run_report.read_json(path), {"中文": "😀"})

    def test_json_rejects_duplicate_object_keys_at_every_depth(self):
        cases = ((b'{"value":1,"value":2}', 'value'),
                 (b'{"value":1,"value":1}', 'value'),
                 (b'{"outer":{"status":"survived","status":"killed"}}', 'status'),
                 (b'{"outer":[{"id":"unapproved","id":"approved"}]}', 'id'),
                 (b'{"a":1,"\\u0061":2}', 'a'))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.json'
            for encoded, key in cases:
                with self.subTest(encoded=encoded):
                    path.write_bytes(encoded)
                    with self.assertRaises(ValueError) as raised:
                        run_report.read_json(path)
                    self.assertEqual(str(raised.exception), f'Duplicate JSON object key: {key}')
                    self.assertEqual(path.read_bytes(), encoded)

    def test_json_allows_same_key_in_separate_objects_and_preserves_values(self):
        encoded = '{"objects":[{"id":"one"},{"id":"two"}],"values":[null,true,false,1,1.5,"中文😀",{}]}'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.json'
            path.write_bytes(encoded.encode())
            self.assertEqual(run_report.read_json(path), {
                'objects': [{'id': 'one'}, {'id': 'two'}],
                'values': [None, True, False, 1, 1.5, '中文😀', {}]})


if __name__ == "__main__":
    unittest.main()
