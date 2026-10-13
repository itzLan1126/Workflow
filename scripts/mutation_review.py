"""Apply the approved, hash-bound MD5 equivalence without changing raw results."""
from collections import Counter
import hashlib
from pathlib import Path
import re


STATUSES = ('killed', 'survived', 'noCoverage', 'timeout', 'unviable', 'ignored', 'error')
ACTIONABLE = ('survived', 'noCoverage', 'timeout', 'error')
IDENTITY = {'id': 'coverage_lcov.x_validate_checksums__mutmut_3',
            'file': 'src/coverage_lcov.py', 'function': 'validate_checksums'}
REPOSITORY_FILE = 'skills/workflow/scripts/coverage_lcov.py'


def is_integer(value):
    return type(value) is int and value >= 0


def is_text(value):
    return isinstance(value, str) and bool(value.strip())


def raw_counts(raw):
    counts = raw.get('counts')
    if not isinstance(counts, dict) or set(counts) != set(STATUSES):
        raise ValueError('Invalid raw mutation evidence')
    if not all(is_integer(value) for value in counts.values()):
        raise ValueError('Invalid raw mutation evidence')
    return counts


def expected_exit(counts, assessed):
    if counts['error'] or not assessed:
        return 2
    return int(bool(counts['survived'] + counts['noCoverage'] + counts['timeout']))


def validate_totals(raw, code, counts):
    assessed = sum(counts[status] for status in ('killed', 'survived', 'noCoverage', 'timeout'))
    values = (code, raw.get('exitCode'), raw.get('toolExitCode'), raw.get('assessed'))
    if not all(is_integer(value) for value in values):
        raise ValueError('Invalid raw mutation evidence')
    expected = (expected_exit(counts, assessed), expected_exit(counts, assessed), 0, assessed)
    if values != expected:
        raise ValueError('Invalid raw mutation evidence')


def mutant_identity(mutant):
    if not isinstance(mutant, dict):
        raise ValueError('Invalid raw mutation evidence')
    if not is_text(mutant.get('id')) or mutant.get('status') not in ACTIONABLE:
        raise ValueError('Invalid raw mutation evidence')
    return mutant['id'], mutant['status']


def validate_proof_details(mutant):
    for field in ('file', 'function', 'diff'):
        if field in mutant and not isinstance(mutant[field], str):
            raise ValueError('Invalid raw mutation evidence')


def raw_mutants(raw, counts):
    mutants = raw.get('mutants')
    if not isinstance(mutants, list):
        raise ValueError('Invalid raw mutation evidence')
    seen, statuses = set(), Counter()
    for mutant in mutants:
        identity, status = mutant_identity(mutant)
        if identity in seen:
            raise ValueError('Invalid raw mutation evidence')
        validate_proof_details(mutant)
        seen.add(identity)
        statuses[status] += 1
    if any(statuses[status] != counts[status] for status in ACTIONABLE):
        raise ValueError('Invalid raw mutation evidence')
    return mutants


def validate_raw(raw, code):
    if not isinstance(raw, dict) or raw.get('format') != 'normalized':
        raise ValueError('Invalid raw mutation evidence')
    if not is_text(raw.get('reportPath')):
        raise ValueError('Invalid raw mutation evidence')
    counts = raw_counts(raw)
    validate_totals(raw, code, counts)
    return counts, raw_mutants(raw, counts)


def validate_approval(approval):
    if not isinstance(approval, dict):
        raise ValueError('Invalid MD5 equivalence approval')
    if not all(is_text(approval.get(field)) for field in (*IDENTITY, 'repositoryFile', 'reason')):
        raise ValueError('Invalid MD5 equivalence approval')
    validate_hashes(approval)


def validate_hashes(approval):
    if not all(isinstance(approval.get(field), str) and re.fullmatch('[0-9a-f]{64}', approval[field])
               for field in ('sourceSha256', 'diffSha256')):
        raise ValueError('Invalid MD5 equivalence approval')


def matches_identity(value):
    return all(value.get(field) == expected for field, expected in IDENTITY.items())


def approved_md5(mutants, copy_root, approval):
    if approval is None:
        return []
    validate_approval(approval)
    if len(mutants) != 1 or not matches_identity(approval):
        return []
    if approval['repositoryFile'] != REPOSITORY_FILE:
        return []
    return matched_proof(mutants[0], copy_root, approval)


def matched_proof(mutant, copy_root, approval):
    if not matches_identity(mutant) or 'diff' not in mutant:
        return []
    source = (Path(copy_root) / IDENTITY['file']).read_bytes()
    if hashlib.sha256(source).hexdigest() != approval['sourceSha256']:
        return []
    if hashlib.sha256(mutant['diff'].encode()).hexdigest() != approval['diffSha256']:
        return []
    return [dict(approval)]


def review_result(raw, raw_exit_code, copy_root, approval):
    counts, mutants = validate_raw(raw, raw_exit_code)
    if raw_exit_code == 2:
        return {'exitCode': 2, 'approvedEquivalentExclusions': []}
    if any(counts[status] for status in ('noCoverage', 'timeout', 'unviable', 'ignored')):
        return {'exitCode': 1, 'approvedEquivalentExclusions': []}
    if raw_exit_code == 0:
        return {'exitCode': 0, 'approvedEquivalentExclusions': []}
    approved = approved_md5(mutants, copy_root, approval)
    return {'exitCode': 0 if approved else 1, 'approvedEquivalentExclusions': approved}
