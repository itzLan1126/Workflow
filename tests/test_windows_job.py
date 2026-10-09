from contextlib import redirect_stderr
import ctypes
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/workflow/scripts"
sys.path.insert(0, str(SCRIPTS))
import windows_job


class WindowsJobTests(unittest.TestCase):
    def setUp(self):
        self.api = mock.Mock(spec=["CreateJobObjectW", "SetInformationJobObject", "AssignProcessToJobObject",
                                   "TerminateJobObject", "CloseHandle"])
        self.api.CreateJobObjectW.return_value = 123
        self.addCleanup(mock.patch.stopall)

        def load_library(name, *, use_last_error=False):
            self.assertEqual(name.lower(), "kernel32")
            self.assertIs(use_last_error, True)
            return self.api

        mock.patch.object(windows_job.ctypes, "WinDLL", side_effect=load_library, create=True).start()
        mock.patch.object(windows_job.ctypes, "WinError", side_effect=lambda code: OSError(code, "win32 failure"), create=True).start()
        mock.patch.object(windows_job.ctypes, "get_last_error", return_value=5, create=True).start()

    def test_job_sets_kill_on_close_and_tracks_handles(self):
        def set_limits(handle, kind, pointer, size):
            self.assertEqual((handle, kind, size), (123, 9, ctypes.sizeof(windows_job.ExtendedLimits)))
            limits = ctypes.cast(pointer, ctypes.POINTER(windows_job.ExtendedLimits)).contents
            self.assertEqual(limits.BasicLimitInformation.LimitFlags, 0x2000)
            return True

        self.api.SetInformationJobObject.side_effect = set_limits
        with windows_job.WindowsJob() as job:
            job.assign(mock.Mock(_handle=456))
            job.terminate()
        self.api.CreateJobObjectW.assert_called_once_with(None, None)
        self.api.AssignProcessToJobObject.assert_called_once_with(123, 456)
        self.api.TerminateJobObject.assert_called_once_with(123, 1)
        self.api.CloseHandle.assert_called_once_with(123)
        self.assertEqual(self.api.CreateJobObjectW.restype, ctypes.wintypes.HANDLE)

    def test_creation_and_setup_failure(self):
        self.api.CreateJobObjectW.return_value = 0
        with self.assertRaises(OSError):
            windows_job.WindowsJob()
        self.api.CloseHandle.assert_not_called()
        self.api.CreateJobObjectW.return_value = 123
        self.api.SetInformationJobObject.return_value = False
        with self.assertRaises(OSError):
            windows_job.WindowsJob()
        self.api.CloseHandle.assert_called_once_with(123)

    def test_win32_failure_preserves_cached_error_code(self):
        with self.assertRaises(OSError) as raised:
            windows_job.checked(False)
        self.assertEqual(raised.exception.errno, 5)
        self.assertEqual(windows_job.checked(123), 123)

    def test_close_failure_does_not_mask_original_error(self):
        self.api.CloseHandle.return_value = False
        with self.assertRaises(OSError):
            with windows_job.WindowsJob():
                pass
        with redirect_stderr(io.StringIO()) as stderr, self.assertRaisesRegex(ValueError, "original"):
            with windows_job.WindowsJob():
                raise ValueError("original")
        self.assertIn("cleanup failed", stderr.getvalue())

    def test_assignment_precedes_release_and_wait(self):
        events = mock.Mock()
        child, job = events.child, events.job
        child.wait.return_value = 17
        self.assertEqual(windows_job.start_and_wait(child, job, 1234), 17)
        self.assertEqual(events.mock_calls, [mock.call.job.assign(child), mock.call.child.stdin.write(b"1"),
                                           mock.call.child.stdin.close(), mock.call.child.wait(timeout=1.234)])

    def test_assignment_failure_never_releases_tool(self):
        child, job = mock.Mock(), mock.Mock()
        job.assign.side_effect = OSError("assignment failed")
        with self.assertRaisesRegex(OSError, "assignment failed"):
            windows_job.start_and_wait(child, job, 1000)
        child.stdin.write.assert_not_called()
        job.terminate.assert_called_once_with()
        child.wait.assert_called_once_with()

    def test_timeout_classification_survives_cleanup_failure(self):
        for cleanup_fails in (False, True):
            with self.subTest(cleanup_fails=cleanup_fails):
                child = mock.Mock(_handle=456)
                timeout = subprocess.TimeoutExpired("tool", 1)
                child.wait.side_effect = [timeout, 1]
                self.api.TerminateJobObject.return_value = not cleanup_fails
                process = mock.MagicMock()
                process.__enter__.return_value = child
                with mock.patch.object(windows_job.subprocess, "Popen", return_value=process), \
                        self.assertRaisesRegex(ValueError, "^Tool exceeded timeoutMs$") as raised:
                    windows_job.run(["tool"], ".", 1000)
                self.assertIs(raised.exception.__cause__, timeout)
                if cleanup_fails:
                    self.assertIsInstance(timeout.__cause__, OSError)
                child.kill.assert_called_once_with()
                self.assertEqual(child.wait.call_args_list, [mock.call(timeout=1.0), mock.call()])

    def test_assignment_failure_reaps_real_gated_bootstrap(self):
        # Portable subprocess test: no Win32 API is needed to verify the gated bootstrap cleanup.
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "started"
            command = [sys.executable, "-c", "from pathlib import Path; Path('started').touch()"]
            processes = []
            popen = subprocess.Popen

            def start(*args, **kwargs):
                child = popen(*args, **kwargs)
                processes.append(child)
                return child

            with mock.patch.object(windows_job.WindowsJob, "assign", side_effect=OSError("assignment failed")), \
                    mock.patch.object(windows_job.subprocess, "Popen", side_effect=start), \
                    self.assertRaisesRegex(OSError, "assignment failed"):
                windows_job.run(command, directory, 1000)
            self.assertEqual(len(processes), 1)
            self.assertIsNotNone(processes[0].poll())
            self.assertFalse(marker.exists())

    def test_normal_completion_closes_job_and_preserves_exit(self):
        process = mock.MagicMock()
        child = process.__enter__.return_value
        child._handle = 456
        child.wait.return_value = 17
        command = ["tool", "argument with spaces", "$(literal)"]
        with mock.patch.object(windows_job.subprocess, "Popen", return_value=process) as start:
            self.assertEqual(windows_job.run(command, "analysis-directory", 1000), 17)
        self.assertEqual(start.call_count, 1)
        self.assertEqual(start.call_args.args,
                         ([sys.executable, str(Path(windows_job.__file__).resolve()), *command],))
        options = dict(start.call_args.kwargs)
        self.assertFalse(options.pop("shell", False))
        self.assertEqual(options, dict(cwd="analysis-directory", stdin=subprocess.PIPE,
                                       stdout=sys.stderr, stderr=sys.stderr))
        self.api.CloseHandle.assert_called_once_with(123)

    def test_bootstrap_needs_release_and_disconnects_tool_stdin(self):
        for token, expected in ((b"", 2), (b"0", 2), (b"1", 17)):
            stdin = mock.Mock(buffer=io.BytesIO(token))
            with mock.patch.object(sys, "stdin", stdin), \
                    mock.patch.object(windows_job.subprocess, "call", return_value=17) as call:
                self.assertEqual(windows_job.bootstrap(["tool", "arg"]), expected)
            if token == b"1":
                call.assert_called_once_with(["tool", "arg"], stdin=subprocess.DEVNULL)
            else:
                call.assert_not_called()


@unittest.skipUnless(os.name == "nt", "requires native Windows job objects")
class NativeWindowsJobTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        self.api.OpenProcess.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.BOOL, ctypes.wintypes.DWORD]
        self.api.OpenProcess.restype = ctypes.wintypes.HANDLE
        self.api.WaitForSingleObject.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD]
        self.api.WaitForSingleObject.restype = ctypes.wintypes.DWORD
        self.api.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
        self.api.CloseHandle.restype = ctypes.wintypes.BOOL

    def command(self, wait):
        code = ("import subprocess,sys,time; from pathlib import Path; "
                "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
                "Path('descendant.pid').write_text(str(child.pid)); " + ("time.sleep(60)" if wait else "pass"))
        return [sys.executable, "-c", code]

    def descendant_handle(self):
        pid = int((self.root / "descendant.pid").read_text())
        handle = self.api.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
        if handle:
            self.addCleanup(self.api.CloseHandle, handle)
        return handle

    def test_native_timeout_terminates_descendants(self):
        with self.assertRaisesRegex(ValueError, "^Tool exceeded timeoutMs$"):
            windows_job.run(self.command(wait=True), self.root, 3000)
        handle = self.descendant_handle()
        if handle:
            self.assertEqual(self.api.WaitForSingleObject(handle, 5000), 0)
        else:
            self.assertEqual(ctypes.get_last_error(), 87)  # Already reaped, ERROR_INVALID_PARAMETER.

    def test_native_job_outlives_root_process(self):
        # Reproduce the taskkill race deterministically: the root exits while its child stays alive.
        with windows_job.WindowsJob() as job:
            argv = [sys.executable, str(Path(windows_job.__file__).resolve()), *self.command(wait=False)]
            with subprocess.Popen(argv, cwd=self.root, stdin=subprocess.PIPE) as child:
                self.assertEqual(windows_job.start_and_wait(child, job, 10000), 0)
            handle = self.descendant_handle()
            self.assertTrue(handle)
            self.assertEqual(self.api.WaitForSingleObject(handle, 0), 258)  # WAIT_TIMEOUT, still alive.
        self.assertEqual(self.api.WaitForSingleObject(handle, 5000), 0)  # Kill-on-close tracks it after root exit.


if __name__ == "__main__":
    unittest.main()
