"""An exact MD5 proof never hides damaged reports or other mutant outcomes."""
from copy import deepcopy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/workflow/scripts'))
from scripts import mutation_review


STATUSES = ('killed', 'survived', 'noCoverage', 'timeout', 'unviable', 'ignored', 'error')
DIFF = '''--- src/coverage_lcov.py
+++ src/coverage_lcov.py
@@ -1,7 +1,7 @@
 def validate_checksums(source, lines, checksums):
     for line, checksum in checksums.items():
         # LCOV fingerprints UTF-8 source lines without their newline, with unpadded base64 MD5.
-        digest = hashlib.md5(lines[line - 1].encode(), usedforsecurity=False).digest()
+        digest = hashlib.md5(lines[line - 1].encode(), usedforsecurity=None).digest()
         # A 16-byte MD5 digest always has exactly two base64 padding characters.
         expected = base64.b64encode(digest)[:-2].decode()
         if checksum != expected:'''
UNSET = object()


def approved_source_bytes():
    root = Path(__file__).resolve().parents[1]
    if root.name == 'mutants':
        root = root.parent
    if (root / 'source-snapshot.json').is_file():
        return (root / 'src/coverage_lcov.py').read_bytes()
    return (root / 'skills/workflow/scripts/coverage_lcov.py').read_bytes()


class MutationReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / 'src' / 'coverage_lcov.py'
        self.source.parent.mkdir()
        self.source.write_bytes(approved_source_bytes())
        self.mutant = {'id': 'coverage_lcov.x_validate_checksums__mutmut_3',
                       'file': 'src/coverage_lcov.py', 'function': 'validate_checksums',
                       'status': 'survived', 'diff': DIFF}
        self.approval = {key: self.mutant[key] for key in ('id', 'file', 'function')}
        self.approval.update(repositoryFile='skills/workflow/scripts/coverage_lcov.py',
                             sourceSha256=hashlib.sha256(self.source.read_bytes()).hexdigest(),
                             diffSha256=hashlib.sha256(DIFF.encode()).hexdigest(),
                             reason='CPython reduces False and None to the same non-security flag.')
        self.raw = self.report([self.mutant])

    def report(self, mutants=(), **counts):
        total = dict.fromkeys(STATUSES, 0)
        total['killed'] = 8
        for mutant in mutants:
            total[mutant['status']] += 1
        total.update(counts)
        assessed = sum(total[status] for status in ('killed', 'survived', 'noCoverage', 'timeout'))
        code = 2 if total['error'] or not assessed else int(bool(total['survived'] + total['noCoverage'] + total['timeout']))
        return {'format': 'normalized', 'counts': total, 'assessed': assessed, 'exitCode': code,
                'toolExitCode': 0, 'mutants': list(mutants), 'reportPath': '/evidence/mutation.json'}

    def review(self, raw=UNSET, approval=UNSET, code=UNSET):
        raw = self.raw if raw is UNSET else raw
        if code is UNSET:
            code = raw.get('exitCode', 1) if isinstance(raw, dict) else 1
        return mutation_review.review_result(raw, code, self.root,
                                             self.approval if approval is UNSET else approval)

    def assert_invalid(self, raw, message='Invalid raw mutation evidence', **kwargs):
        with self.assertRaises(ValueError) as raised:
            self.review(raw, **kwargs)
        self.assertEqual(str(raised.exception), message)

    def assert_blocked(self, result, code=1):
        self.assertEqual(result, {'exitCode': code, 'approvedEquivalentExclusions': []})

    def test_exact_approval_passes_with_visible_exclusion_and_unchanged_raw(self):
        before = deepcopy(self.raw)
        result = self.review()
        self.assertEqual(result, {'exitCode': 0, 'approvedEquivalentExclusions': [self.approval]})
        self.assertEqual(self.raw, before)
        self.assertEqual(self.approval['sourceSha256'], hashlib.sha256(self.source.read_bytes()).hexdigest())

    def test_all_killed_passes_without_approval_or_source(self):
        self.source.unlink()
        self.assertEqual(mutation_review.review_result(self.report(), 0, self.root, None),
                         {'exitCode': 0, 'approvedEquivalentExclusions': []})

    def test_source_and_diff_hash_changes_keep_failure(self):
        for field in ('sourceSha256', 'diffSha256'):
            with self.subTest(field=field):
                self.assertEqual(self.review(approval={**self.approval, field: '0' * 64}),
                                 {'exitCode': 1, 'approvedEquivalentExclusions': []})
        self.source.write_bytes(b'changed source\n')
        self.assert_blocked(self.review())
        self.source.write_bytes(approved_source_bytes())
        self.assert_blocked(self.review(raw={**self.raw, 'mutants': [{**self.mutant, 'diff': DIFF + '\n'}]}))

    def test_coordinated_source_diff_and_manifest_changes_are_not_new_approvals(self):
        original = self.source.read_bytes()
        for change_source, change_diff in ((True, False), (False, True), (True, True)):
            with self.subTest(source=change_source, diff=change_diff):
                self.source.write_bytes(original + b'\n# unapproved change\n' if change_source else original)
                raw = deepcopy(self.raw)
                if change_diff:
                    raw['mutants'][0]['diff'] = DIFF.replace('usedforsecurity=None', 'usedforsecurity=True')
                approval = {**self.approval,
                            'sourceSha256': hashlib.sha256(self.source.read_bytes()).hexdigest(),
                            'diffSha256': hashlib.sha256(raw['mutants'][0]['diff'].encode()).hexdigest()}
                before = deepcopy(raw)
                self.assert_blocked(self.review(raw=raw, approval=approval))
                self.assertEqual(raw, before)
                self.assertEqual(approval['id'], self.approval['id'])
                self.assertEqual(approval['reason'], self.approval['reason'])

    def test_each_identity_is_fixed_in_manifest_and_mutant(self):
        for field in ('id', 'file', 'function', 'repositoryFile'):
            with self.subTest(manifest=field):
                self.assert_blocked(self.review(approval={**self.approval, field: 'wrong'}))
        for field in ('id', 'file', 'function'):
            with self.subTest(mutant=field):
                mutant = {**self.mutant, field: 'wrong'}
                self.assert_blocked(self.review(raw=self.report([mutant])))

    def test_missing_proof_fields_and_extra_survivor_never_pass(self):
        for field in ('file', 'function', 'diff'):
            with self.subTest(field=field):
                mutant = dict(self.mutant)
                del mutant[field]
                self.assert_blocked(self.review(raw=self.report([mutant])))
        extra = {**self.mutant, 'id': 'other.survivor'}
        self.assert_blocked(self.review(raw=self.report([self.mutant, extra])))

    def test_every_other_mutant_status_blocks_even_with_exact_approval(self):
        for status in ('noCoverage', 'timeout', 'error'):
            with self.subTest(status=status):
                other = {**self.mutant, 'id': 'other.status', 'status': status}
                raw = self.report([self.mutant, other])
                self.assert_blocked(self.review(raw), 2 if status == 'error' else 1)
        for status in ('unviable', 'ignored'):
            for raw in (self.report([self.mutant], **{status: 1}), self.report(**{status: 1})):
                with self.subTest(status=status, raw=raw):
                    self.assert_blocked(self.review(raw))

    def test_no_assessed_mutants_and_error_exit_never_pass(self):
        raw = self.report(killed=0)
        self.assertEqual(self.review(raw), {'exitCode': 2, 'approvedEquivalentExclusions': []})
        raw = self.report([{**self.mutant, 'status': 'error'}])
        self.assert_blocked(self.review(raw), 2)

    def test_counts_must_have_exact_statuses_and_nonnegative_integer_values(self):
        for value in (None, [], {}, {**self.raw['counts'], 'extra': 0}):
            with self.subTest(value=value):
                self.assert_invalid({**self.raw, 'counts': value})
        for value in (-1, 1.0, True, None, '1'):
            with self.subTest(value=value):
                self.assert_invalid({**self.raw, 'counts': {**self.raw['counts'], 'survived': value}})

    def test_assessed_and_exit_codes_must_match_exactly(self):
        for value in (None, False, 1.0, -1, 10):
            with self.subTest(assessed=value):
                self.assert_invalid({**self.raw, 'assessed': value})
        for field in ('exitCode', 'toolExitCode'):
            for value in (None, False, 0.0, -1, 3, '0'):
                with self.subTest(field=field, value=value):
                    self.assert_invalid({**self.raw, field: value})
        self.assert_invalid(self.raw, code=0)
        self.assert_invalid(self.raw, code=True)
        self.assert_invalid(self.raw, code=2)
        self.assert_invalid({**self.raw, 'toolExitCode': 1})

    def test_malformed_report_and_actionable_details_fail_closed(self):
        for raw in (None, [], {}, {**self.raw, 'format': 'stryker'},
                    {**self.raw, 'mutants': None}, {**self.raw, 'mutants': []},
                    {**self.raw, 'mutants': [None]}, {**self.raw, 'reportPath': None}):
            with self.subTest(raw=raw):
                self.assert_invalid(raw)
        for field, value in (('id', ''), ('id', ' '), ('id', 1), ('status', 'killed'),
                             ('status', 'unknown'), ('file', []), ('function', 1), ('diff', None)):
            with self.subTest(field=field, value=value):
                self.assert_invalid({**self.raw, 'mutants': [{**self.mutant, field: value}]})
        self.assert_invalid(self.report([self.mutant, self.mutant]))

    def test_approval_types_hash_formats_and_reason_fail_closed(self):
        for approval in ([], 'proof', {}, {**self.approval, 'reason': ''},
                         {**self.approval, 'reason': ' '}, {**self.approval, 'reason': None}):
            with self.subTest(approval=approval):
                self.assert_invalid(self.raw, 'Invalid MD5 equivalence approval', approval=approval)
        for field in ('sourceSha256', 'diffSha256'):
            for value in (None, 'g' * 64, 'A' * 64, '0' * 63, '0' * 65):
                with self.subTest(field=field, value=value):
                    self.assert_invalid(self.raw, 'Invalid MD5 equivalence approval',
                                        approval={**self.approval, field: value})
        for field in ('id', 'file', 'function', 'repositoryFile'):
            self.assert_invalid(self.raw, 'Invalid MD5 equivalence approval',
                                approval={**self.approval, field: None})

    def test_missing_approval_keeps_raw_failure(self):
        self.assertEqual(mutation_review.review_result(self.raw, 1, self.root, None),
                         {'exitCode': 1, 'approvedEquivalentExclusions': []})

    def test_missing_proof_source_is_an_io_failure(self):
        self.source.unlink()
        with self.assertRaises(FileNotFoundError):
            self.review()


if __name__ == '__main__':
    unittest.main()
