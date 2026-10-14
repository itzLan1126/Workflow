"""Check self-quality command scope, fresh copies, and exit propagation."""
from contextlib import redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import builtins

from scripts import self_crap, self_mutation
from test_mutation_review import DIFF, approved_source_bytes


class SelfQualityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.sources = {
            'skills/workflow/scripts/a.py': 'def a(): return 1\n',
            'skills/workflow/scripts/b.py': 'def b(): return 2\n',
            'scripts/validation.py': 'def validate(): return 3\n',
            'scripts/self_crap.py': 'def main(): return 0\n',
            'scripts/self_mutation.py': 'def main(): return 1\n',
            'tests/test_example.py': 'def test_example(): assert True\n',
            'tests/helpers.py': 'def fixture(): return 3\n',
        }
        for name, content in self.sources.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
        (self.root / 'scripts/ignored.md').write_text('not Python')
        (self.root / 'tests/ignored.txt').write_text('not Python')
        self.approval = {'id': 'coverage_lcov.x_validate_checksums__mutmut_3',
                         'file': 'src/coverage_lcov.py', 'function': 'validate_checksums',
                         'repositoryFile': 'skills/workflow/scripts/coverage_lcov.py',
                         'sourceSha256': '0' * 64, 'diffSha256': '0' * 64,
                         'reason': 'Test approval; no source matches by default.'}
        self.approval_path = self.root / 'docs/repo-review-md5-exclusion.json'
        self.approval_path.parent.mkdir()
        self.approval_path.write_bytes(json.dumps(self.approval).encode())
        self.stdout = io.StringIO()
        patcher = mock.patch.object(sys, 'stdout', self.stdout)
        patcher.start()
        self.addCleanup(patcher.stop)
        for module in (self_crap, self_mutation):
            for field, value in (('ROOT', self.root), ('SCRIPTS', self.root / 'skills/workflow/scripts')):
                patcher = mock.patch.object(module, field, value)
                patcher.start()
                self.addCleanup(patcher.stop)

    def engine(self, code, raw=None):
        def run(*args, **kwargs):
            counts = dict.fromkeys(('killed', 'survived', 'noCoverage', 'timeout',
                                    'unviable', 'ignored', 'error'), 0)
            counts['killed'] = 1
            mutants = []
            if code:
                status = 'survived' if code == 1 else 'error'
                counts[status] = 1
                mutants.append({'id': 'unapproved.mutant', 'status': status})
            result = {'format': 'normalized', 'counts': counts,
                      'assessed': counts['killed'] + counts['survived'],
                      'exitCode': code, 'toolExitCode': 0, 'mutants': mutants,
                      'reportPath': '/evidence/mutation.json'}
            kwargs['stdout'].write(json.dumps(result if raw is None else raw).encode())
            return mock.Mock(returncode=code)
        return run

    def test_crap_checks_every_production_file_and_propagates_result(self):
        sources = ['skills/workflow/scripts/a.py', 'skills/workflow/scripts/b.py',
                   'scripts/self_crap.py', 'scripts/self_mutation.py', 'scripts/validation.py']
        expected = [sys.executable, str(self.root / 'skills/workflow/scripts/crap.py'),
                    'python', str(self.root), *(str(self.root / name) for name in sources),
                    '--', '-m', 'unittest', 'discover', '-s', 'tests']
        for code in (0, 1, 2):
            with self.subTest(code=code), mock.patch.object(self_crap.subprocess, 'run') as run:
                run.return_value.returncode = code
                self.assertEqual(self_crap.main(), code)
                run.assert_called_once_with(expected, cwd=self.root)

    def test_mutation_copies_all_source_and_test_files_and_propagates_result(self):
        for code in (0, 1, 2):
            with self.subTest(code=code):
                copy = self.root / f'analysis-{code}'
                copy.mkdir()
                with mock.patch.object(self_mutation.tempfile, 'mkdtemp', return_value=str(copy)), \
                        mock.patch.object(sys, 'argv', ['self_mutation.py', '--json']), \
                        mock.patch.object(self_mutation.subprocess, 'run', side_effect=self.engine(code)) as run, \
                        redirect_stderr(io.StringIO()) as stderr:
                    self.assertEqual(self_mutation.main(), code)
                run.assert_called_once_with([sys.executable, str(self.root / 'skills/workflow/scripts/mutation.py'),
                                             '--json', 'python', str(copy)], stdout=mock.ANY)
                self.assertEqual(stderr.getvalue(), f'Isolated copy: {copy}\n')
                self.assertEqual({path.name for path in copy.iterdir()},
                                 {'src', 'scripts', 'tests', 'pyproject.toml', 'source-snapshot.json',
                                  'md5-exclusion.json', 'mutation-result.json', 'mutation-reviewed.json'})
                self.assertEqual((copy / 'md5-exclusion.json').read_bytes(), self.approval_path.read_bytes())
                raw = json.loads((copy / 'mutation-result.json').read_bytes())
                reviewed = json.loads((copy / 'mutation-reviewed.json').read_bytes())
                self.assertEqual(reviewed['exitCode'], code)
                self.assertEqual(reviewed['rawExitCode'], code)
                self.assertEqual(reviewed['reviewGate']['exitCode'], code)
                self.assertEqual({key: reviewed[key] for key in raw}, raw)
                self.assertEqual(reviewed['rawResultPath'], str(copy / 'mutation-result.json'))
                expected = {}
                for source, content in self.sources.items():
                    folder = 'src' if source.startswith('skills/') else source.split('/')[0]
                    target = copy / folder / Path(source).name
                    self.assertEqual(target.read_text(), content)
                    expected[source] = hashlib.sha256(content.encode('utf-8')).hexdigest()
                self.assertFalse((copy / 'scripts/ignored.md').exists())
                self.assertFalse((copy / 'tests/ignored.txt').exists())
                snapshot = json.loads((copy / 'source-snapshot.json').read_text())
                self.assertEqual(snapshot, {'python': sys.version, 'sha256': expected})
                self.assertEqual((copy / 'pyproject.toml').read_text(),
                                 '[tool.mutmut]\nsource_paths = ["src/", "scripts/"]\n'
                                 'pytest_add_cli_args_test_selection = ["tests/", "-k", '
                                 '"not script_entrypoint and not real_mutmut"]\n')

    def test_copy_failure_does_not_start_mutation_engine(self):
        copy = self.root / 'broken-copy'
        copy.mkdir()
        with mock.patch.object(self_mutation.tempfile, 'mkdtemp', return_value=str(copy)), \
                mock.patch.object(self_mutation.shutil, 'copy2', side_effect=OSError('copy failed')), \
                mock.patch.object(self_mutation.subprocess, 'run') as run, \
                self.assertRaisesRegex(OSError, '^copy failed$'):
            self_mutation.main()
        run.assert_not_called()

    def approved_case(self):
        source = self.root / 'skills/workflow/scripts/coverage_lcov.py'
        source.write_bytes(approved_source_bytes())
        diff = DIFF
        self.approval.update(sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                             diffSha256=hashlib.sha256(diff.encode()).hexdigest())
        self.approval_path.write_bytes(json.dumps(self.approval).encode())
        mutant = {key: self.approval[key] for key in ('id', 'file', 'function')}
        mutant.update(status='survived', diff=diff)
        counts = dict.fromkeys(('killed', 'survived', 'noCoverage', 'timeout',
                                'unviable', 'ignored', 'error'), 0)
        counts.update(killed=1, survived=1)
        return {'format': 'normalized', 'counts': counts, 'assessed': 2, 'exitCode': 1,
                'toolExitCode': 0, 'mutants': [mutant], 'reportPath': '/evidence/mutation.json'}

    def test_coordinated_proof_and_manifest_changes_preserve_raw_failure(self):
        for change_source, change_diff in ((True, False), (False, True), (True, True)):
            with self.subTest(source=change_source, diff=change_diff):
                raw = self.approved_case()
                source = self.root / 'skills/workflow/scripts/coverage_lcov.py'
                if change_source:
                    source.write_bytes(source.read_bytes() + b'\n# unapproved change\n')
                if change_diff:
                    raw['mutants'][0]['diff'] = DIFF.replace('usedforsecurity=None', 'usedforsecurity=True')
                self.approval.update(sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                                     diffSha256=hashlib.sha256(raw['mutants'][0]['diff'].encode()).hexdigest())
                approval_bytes = json.dumps(self.approval).encode()
                raw_bytes = json.dumps(raw).encode()
                copy = self.root / f'changed-{change_source}-{change_diff}'
                (copy / 'src').mkdir(parents=True)
                (copy / 'src/coverage_lcov.py').write_bytes(source.read_bytes())
                (copy / 'md5-exclusion.json').write_bytes(approval_bytes)
                (copy / 'mutation-result.json').write_bytes(raw_bytes)
                self.assertEqual(self_mutation.emit_review(copy, 1, True, approval_bytes), 1)
                reviewed = json.loads((copy / 'mutation-reviewed.json').read_bytes())
                self.assertEqual(reviewed['reviewGate'], {'exitCode': 1, 'approvedEquivalentExclusions': []})
                self.assertEqual({key: reviewed[key] for key in raw}, raw)
                self.assertEqual(reviewed['rawExitCode'], 1)
                self.assertEqual((copy / 'mutation-result.json').read_bytes(), raw_bytes)
                self.assertEqual((copy / 'md5-exclusion.json').read_bytes(), approval_bytes)

    def test_approved_gate_passes_without_rewriting_raw_status_or_exit(self):
        raw = self.approved_case()
        with mock.patch.object(self_mutation.subprocess, 'run', side_effect=self.engine(1, raw)) as run, \
                mock.patch.object(sys, 'argv', ['self_mutation.py', '--json']), redirect_stderr(io.StringIO()):
            self.assertEqual(self_mutation.main(), 0)
        copy = Path(run.call_args.args[0][-1])
        self.assertEqual((copy / 'mutation-result.json').read_bytes(), json.dumps(raw).encode())
        result = json.loads(self.stdout.getvalue())
        self.assertEqual({key: result[key] for key in raw}, raw)
        self.assertEqual(result['rawExitCode'], 1)
        self.assertEqual(result['reviewGate'], {'exitCode': 0,
                         'approvedEquivalentExclusions': [self.approval]})
        self.assertEqual(result['approvalSha256'], hashlib.sha256(self.approval_path.read_bytes()).hexdigest())
        self.assertEqual(json.loads((copy / 'mutation-reviewed.json').read_bytes()), result)

    def test_project_cannot_rewrite_approval_while_mutation_runs(self):
        raw = self.approved_case()
        def run(*args, **kwargs):
            copy = Path(args[0][-1])
            (copy / 'md5-exclusion.json').write_bytes(b'{}')
            return self.engine(1, raw)(*args, **kwargs)
        with mock.patch.object(self_mutation.subprocess, 'run', side_effect=run), \
                mock.patch.object(sys, 'argv', ['self_mutation.py', '--json']), redirect_stderr(io.StringIO()):
            self.assertEqual(self_mutation.main(), 2)
        result = json.loads(self.stdout.getvalue())
        self.assertEqual(result['reviewGate'], {'exitCode': 2,
                         'runFailure': 'MD5 approval changed during the mutation check'})

    def test_damaged_raw_json_is_preserved_and_never_passes_review(self):
        def run(*args, **kwargs):
            kwargs['stdout'].write(b'not a report')
            return mock.Mock(returncode=2)
        with mock.patch.object(self_mutation.subprocess, 'run', side_effect=run) as command, \
                mock.patch.object(sys, 'argv', ['self_mutation.py', '--json']), redirect_stderr(io.StringIO()):
            self.assertEqual(self_mutation.main(), 2)
        copy = Path(command.call_args.args[0][-1])
        self.assertEqual((copy / 'mutation-result.json').read_bytes(), b'not a report')
        result = json.loads(self.stdout.getvalue())
        self.assertEqual((result['rawExitCode'], result['reviewGate']['exitCode']), (2, 2))

    def test_default_output_keeps_raw_details_and_labels_reviewed_gate(self):
        with mock.patch.object(self_mutation.subprocess, 'run', side_effect=self.engine(1)), \
                mock.patch.object(sys, 'argv', ['self_mutation.py']), redirect_stderr(io.StringIO()):
            self.assertEqual(self_mutation.main(), 1)
        raw_text, gate_text = self.stdout.getvalue().split('Reviewed gate: ')
        self.assertIn('mutant unapproved.mutant [survived]', raw_text)
        self.assertIn('Summary: 1 killed, 1 survived', raw_text)
        self.assertEqual(json.loads(gate_text), {'exitCode': 1, 'approvedEquivalentExclusions': []})

    def test_nonfinite_raw_and_approval_json_never_pass_review(self):
        raw = self.approved_case()
        for value in ('NaN', 'Infinity', '-Infinity', '1e999'):
            for target in ('raw', 'approval'):
                with self.subTest(value=value, target=target):
                    copy = self.root / f'{target}-{value}'
                    copy.mkdir()
                    raw_bytes = json.dumps(raw).encode()
                    approval_bytes = json.dumps(self.approval).encode()
                    invalid = b', "extra":{"nested":[' + value.encode() + b']}}'
                    if target == 'raw':
                        raw_bytes = raw_bytes[:-1] + invalid
                    else:
                        approval_bytes = approval_bytes[:-1] + invalid
                    (copy / 'mutation-result.json').write_bytes(raw_bytes)
                    (copy / 'md5-exclusion.json').write_bytes(approval_bytes)
                    self.assertEqual(self_mutation.emit_review(copy, 1, True, approval_bytes), 2)
                    result = json.loads((copy / 'mutation-reviewed.json').read_bytes())
                    self.assertIn('Non-finite JSON number:', result['reviewGate']['runFailure'])
                    self.assertEqual((copy / 'mutation-result.json').read_bytes(), raw_bytes)

    def test_duplicate_raw_or_approval_keys_never_hide_survivors_or_pass_review(self):
        raw = self.approved_case()
        raw_bytes = json.dumps(raw).encode()
        approval_bytes = json.dumps(self.approval).encode()
        extra = {**raw['mutants'][0], 'id': 'unapproved.survivor'}
        bad_counts = {**raw['counts'], 'survived': 2}
        cases = (
            ('raw-mutants', b'{"mutants":' + json.dumps([raw['mutants'][0], extra]).encode() + b',' + raw_bytes[1:], approval_bytes, 'mutants'),
            ('raw-counts', b'{"counts":' + json.dumps(bad_counts).encode() + b',' + raw_bytes[1:], approval_bytes, 'counts'),
            ('raw-nested-object', raw_bytes[:-1] + b',"extra":{"status":"error","status":"killed"}}', approval_bytes, 'status'),
            ('raw-nested-array', raw_bytes[:-1] + b',"extra":[{"id":"unapproved","id":"approved"}]}', approval_bytes, 'id'),
            ('approval-source', raw_bytes, b'{"sourceSha256":"' + b'0' * 64 + b'",' + approval_bytes[1:], 'sourceSha256'),
            ('approval-id', raw_bytes, b'{"id":"unapproved.survivor",' + approval_bytes[1:], 'id'),
            ('approval-nested-object', raw_bytes, approval_bytes[:-1] + b',"extra":{"id":"unapproved","id":"approved"}}', 'id'),
            ('approval-nested-array', raw_bytes, approval_bytes[:-1] + b',"extra":[{"status":"error","status":"killed"}]}', 'status'),
        )
        for name, encoded_raw, encoded_approval, key in cases:
            with self.subTest(name=name):
                copy = self.root / name
                (copy / 'src').mkdir(parents=True)
                (copy / 'src/coverage_lcov.py').write_bytes((self.root / 'skills/workflow/scripts/coverage_lcov.py').read_bytes())
                (copy / 'mutation-result.json').write_bytes(encoded_raw)
                (copy / 'md5-exclusion.json').write_bytes(encoded_approval)
                self.assertEqual(self_mutation.emit_review(copy, 1, True, encoded_approval), 2)
                reviewed = json.loads((copy / 'mutation-reviewed.json').read_bytes())
                self.assertEqual(reviewed['reviewGate'], {'exitCode': 2,
                                 'runFailure': f'Duplicate JSON object key: {key}'})
                self.assertEqual(reviewed['rawExitCode'], 1)
                self.assertEqual(reviewed['approvalSha256'], hashlib.sha256(encoded_approval).hexdigest())
                self.assertEqual((copy / 'mutation-result.json').read_bytes(), encoded_raw)
                self.assertEqual((copy / 'md5-exclusion.json').read_bytes(), encoded_approval)

    def test_default_output_for_invalid_utf8_or_missing_raw_returns_recorded_gate(self):
        for data in (b'\xff', None):
            with self.subTest(data=data):
                copy = self.root / ('invalid-utf8' if data else 'missing-raw')
                copy.mkdir()
                if data is not None:
                    (copy / 'mutation-result.json').write_bytes(data)
                approval_bytes = self.approval_path.read_bytes()
                (copy / 'md5-exclusion.json').write_bytes(approval_bytes)
                self.stdout.seek(0)
                self.stdout.truncate()
                self.assertEqual(self_mutation.emit_review(copy, 2, False, approval_bytes), 2)
                self.assertIn(f'Raw result: {copy / "mutation-result.json"}', self.stdout.getvalue())
                result = json.loads((copy / 'mutation-reviewed.json').read_bytes())
                self.assertEqual((result['rawExitCode'], result['reviewGate']['exitCode']), (2, 2))
                if data is not None:
                    self.assertEqual((copy / 'mutation-result.json').read_bytes(), data)

    def test_analysis_files_work_with_case_sensitive_read_semantics(self):
        # Reproduce Linux file-name lookup even when the host filesystem ignores case.
        def case_sensitive(original):
            def open_file(path, mode='r', *args, **kwargs):
                if 'r' in mode and not isinstance(path, int):
                    path = Path(path)
                    if path.name not in {entry.name for entry in path.parent.iterdir()}:
                        raise FileNotFoundError(path)
                return original(path, mode, *args, **kwargs)
            return open_file
        with mock.patch.object(builtins, 'open', case_sensitive(builtins.open)), \
                mock.patch.object(Path, 'open', case_sensitive(Path.open)), \
                mock.patch.object(self_mutation.subprocess, 'run', side_effect=self.engine(0)), \
                mock.patch.object(sys, 'argv', ['self_mutation.py', '--json']), redirect_stderr(io.StringIO()):
            self.assertEqual(self_mutation.main(), 0)
        self.assertEqual(json.loads(self.stdout.getvalue())['reviewGate']['exitCode'], 0)

    def test_snapshot_hashes_the_assessed_copy_when_original_changes(self):
        copy = self.root / 'source-changed'
        copy.mkdir()
        copy_file = self_mutation.shutil.copy2

        def copy_then_save(source, target):
            result = copy_file(source, target)
            source.write_text('saved after copying\n')
            return result

        with mock.patch.object(self_mutation.tempfile, 'mkdtemp', return_value=str(copy)), \
                mock.patch.object(self_mutation.shutil, 'copy2', side_effect=copy_then_save), \
                mock.patch.object(self_mutation.subprocess, 'run', side_effect=self.engine(0)), \
                redirect_stderr(io.StringIO()):
            self.assertEqual(self_mutation.main(), 0)
        snapshot = json.loads((copy / 'source-snapshot.json').read_text())
        self.assertEqual(snapshot['sha256'], {
            source: hashlib.sha256(content.encode()).hexdigest() for source, content in self.sources.items()})

    def test_copy_path_is_flushed_before_engine_starts(self):
        copy = self.root / 'buffered-copy'
        copy.mkdir()
        buffer = io.BytesIO()
        stderr = io.TextIOWrapper(buffer, encoding='utf-8')
        self.addCleanup(stderr.close)

        def run(*args, **kwargs):
            self.assertEqual(buffer.getvalue(), f'Isolated copy: {copy}\n'.encode())
            return self.engine(0)(*args, **kwargs)

        with mock.patch.object(self_mutation.tempfile, 'mkdtemp', return_value=str(copy)), \
                mock.patch.object(self_mutation.subprocess, 'run', side_effect=run), redirect_stderr(stderr):
            self.assertEqual(self_mutation.main(), 0)

    def test_mutation_accepts_a_bytes_global_temp_directory(self):
        with mock.patch.object(tempfile, 'tempdir', bytes(self.root)), \
                mock.patch.object(self_mutation.subprocess, 'run', side_effect=self.engine(0)) as run, \
                redirect_stderr(io.StringIO()):
            self.assertEqual(self_mutation.main(), 0)
        copy = Path(run.call_args.args[0][-1])
        self.assertEqual(copy.parent, self.root)
        self.assertEqual(json.loads((copy / 'source-snapshot.json').read_text(encoding='utf-8'))['sha256'], {
            source: hashlib.sha256(content.encode('utf-8')).hexdigest() for source, content in self.sources.items()})

    def test_mutation_writes_utf8_under_strict_default_encoding_warnings(self):
        text_encoding = io.text_encoding

        def strict_encoding(encoding, stacklevel=2):
            if encoding is None:
                raise EncodingWarning("'encoding' argument not specified")
            return text_encoding(encoding, stacklevel)

        # Model strict encoding-warning mode in-process so mutation tests retain call association.
        with mock.patch.object(io, 'text_encoding', side_effect=strict_encoding), \
                mock.patch.object(tempfile, 'tempdir', str(self.root)), \
                mock.patch.object(self_mutation.subprocess, 'run', side_effect=self.engine(0)) as run, \
                redirect_stderr(io.StringIO()):
            self.assertEqual(self_mutation.main(), 0)
        copy = Path(run.call_args.args[0][-1])
        self.assertEqual((copy / 'pyproject.toml').read_bytes(), self_mutation.MUTMUT_CONFIG.encode('utf-8'))
        self.assertTrue(json.loads((copy / 'source-snapshot.json').read_bytes())['sha256'])

    def test_mutation_respects_audit_policy_for_analysis_directory_ownership(self):
        with mock.patch.object(tempfile, 'tempdir', str(self.root)), \
                mock.patch.object(self_mutation.subprocess, 'run', side_effect=self.engine(0)), \
                redirect_stderr(io.StringIO()):
            self.assertEqual(self_mutation.main(), 0)
        code = '''
import importlib.util
import os
from pathlib import Path
import sys
from unittest import mock
spec = importlib.util.spec_from_file_location(sys.argv[3], sys.argv[1])
sys.path.insert(0, sys.argv[4])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.ROOT = Path(sys.argv[2])
module.SCRIPTS = module.ROOT / 'skills/workflow/scripts'
module.tempfile.tempdir = sys.argv[2]
def owner_policy(event, args):
    if event == 'tempfile.mkdtemp' and not os.path.basename(args[0]).startswith('workflow-self-mutation-'):
        raise PermissionError('unrecognized analysis-directory owner')
sys.addaudithook(owner_policy)
def run(*args, **kwargs):
    import json
    counts = dict.fromkeys(('killed', 'survived', 'noCoverage', 'timeout', 'unviable', 'ignored', 'error'), 0)
    counts['killed'] = 1
    kwargs['stdout'].write(json.dumps({'format':'normalized','counts':counts,'assessed':1,
        'exitCode':0,'toolExitCode':0,'mutants':[],'reportPath':'/evidence/mutation.json'}).encode())
    return mock.Mock(returncode=0)
with mock.patch.object(module.subprocess, 'run', side_effect=run):
    assert module.main() == 0
'''
        result = subprocess.run([sys.executable, '-c', code, str(Path(self_mutation.__file__).resolve()),
                                 str(self.root), self_mutation.__name__,
                                 str(Path(sys.modules['shared_runner'].__file__).resolve().parent)],
                                capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', errors='replace'))
