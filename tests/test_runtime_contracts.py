"""Runtime boundaries that temporary names and DLL lookup must preserve."""

from contextlib import redirect_stderr
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/workflow/scripts'))
import shared_languages
import shared_runner


class RuntimeContractTests(unittest.TestCase):
    def test_evidence_directory_preserves_text_paths_with_bytes_tempdir(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(tempfile, 'tempdir', os.fsencode(directory)), \
                redirect_stderr(io.StringIO()) as stderr:
            evidence = shared_languages.evidence_directory()
            self.assertIsInstance(evidence, Path)
            self.assertTrue(evidence.is_dir())
            self.assertEqual(stderr.getvalue(), f'Evidence: {evidence}\n')

    def test_evidence_directory_respects_audit_policy_for_owned_directory_names(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(tempfile, 'tempdir', directory), redirect_stderr(io.StringIO()):
            self.assertTrue(shared_languages.evidence_directory().is_dir())
            code = (f'import sys; sys.path.insert(0, {str(Path(shared_languages.__file__).resolve().parent)!r})\n'
                    'import os, tempfile, shared_languages\n'
                    f'tempfile.tempdir = {directory!r}\n'
                    'def owner_policy(event, args):\n'
                    '    if event == "tempfile.mkdtemp" and not os.fsdecode(os.path.basename(args[0])).startswith("workflow-evidence-"):\n'
                    '        raise PermissionError("unrecognized evidence-directory owner")\n'
                    'sys.addaudithook(owner_policy)\n'
                    'assert shared_languages.evidence_directory().is_dir()\n')
            result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_kernel32_lookup_respects_literal_dll_audit_allowlist(self):
        with patch.object(shared_runner.ctypes, 'WinDLL', return_value=Mock(), create=True):
            shared_runner.kernel32()
        code = (f'import sys; sys.path.insert(0, {str(Path(shared_runner.__file__).resolve().parent)!r})\n'
                'import ctypes, shared_runner\n'
                'from unittest.mock import Mock\n'
                'if not hasattr(ctypes, "WinDLL"):\n'
                '    api = Mock()\n'
                '    def loader(name, **options):\n'
                '        try:\n'
                '            ctypes.CDLL(name, **options)\n'
                '        except OSError as error:\n'
                '            if type(error) is not OSError:\n'
                '                raise\n'
                '        return api\n'
                '    ctypes.WinDLL = loader\n'
                'def dll_policy(event, args):\n'
                '    if event == "ctypes.dlopen" and isinstance(args[0], str) and args[0].casefold() == "kernel32" and args[0] != "kernel32":\n'
                '        raise PermissionError("DLL name is outside the literal allowlist")\n'
                'sys.addaudithook(dll_policy)\n'
                'shared_runner.kernel32()\n')
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
