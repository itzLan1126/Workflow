#!/usr/bin/env python3
"""Mutation-test every production Python script in a fresh analysis copy."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

if __package__:
    from .mutation_review import review_result
else:
    from mutation_review import review_result


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/workflow/scripts"
sys.path.insert(0, str(SCRIPTS))
from shared_runner import read_json, parse_json
from shared_mutation import render_report
# mutmut names mutants by path from the project root, while the tests import the scripts
# as top-level modules, so the analysis copy places them under src/. The script-entrypoint
# smoke tests run scripts by repository path, which does not exist in the copy, and the
# nested real-mutmut test would rerun mutmut for every mutant.
MUTMUT_CONFIG = """[tool.mutmut]
source_paths = ["src/", "scripts/"]
pytest_add_cli_args_test_selection = ["tests/", "-k", "not script_entrypoint and not real_mutmut"]
"""


def display_review(result, as_json):
    if as_json:
        print(json.dumps(result))
    else:
        if 'counts' in result:
            print(render_report(result))
        else:
            print(f"Raw result: {result['rawResultPath']}")
        print('Reviewed gate: ' + json.dumps(result['reviewGate']))


def emit_review(copy, raw_exit_code, as_json, approval_bytes):
    raw_path = copy / 'mutation-result.json'
    result = {}
    try:
        if (copy / 'md5-exclusion.json').read_bytes() != approval_bytes:
            raise ValueError('MD5 approval changed during the mutation run')
        raw = read_json(raw_path)
        approval = parse_json(approval_bytes.decode())
        gate = review_result(raw, raw_exit_code, copy, approval)
        result.update(raw)
        result['reviewGate'] = gate
    except (OSError, ValueError, KeyError, TypeError) as error:
        result['reviewGate'] = {'exitCode': 2, 'error': str(error)}
    result['rawExitCode'] = raw_exit_code
    result['rawResultPath'] = str(raw_path)
    result['approvalSha256'] = hashlib.sha256(approval_bytes).hexdigest()
    (copy / 'mutation-reviewed.json').write_bytes(json.dumps(result).encode())
    display_review(result, as_json)
    return result['reviewGate']['exitCode']


def run_review(copy, args):
    as_json = '--json' in args
    args = [arg for arg in args if arg != '--json']
    # Capture the approved policy before running project code in the analysis copy.
    approval_bytes = (copy / 'md5-exclusion.json').read_bytes()
    with (copy / 'mutation-result.json').open('xb') as output:
        run = subprocess.run([sys.executable, str(SCRIPTS / 'mutation.py'),
                              '--json', *args, 'python', str(copy)], stdout=output)
    return emit_review(copy, run.returncode, as_json, approval_bytes)


def main():
    copy = Path(tempfile.mkdtemp(prefix="workflow-self-mutation-"))
    snapshot = {}
    for original, target in ((SCRIPTS, 'src'), (ROOT / 'scripts', 'scripts'), (ROOT / 'tests', 'tests')):
        (copy / target).mkdir()
        for path in sorted(original.glob('*.py')):
            shutil.copy2(path, copy / target / path.name)
            snapshot[str(path.relative_to(ROOT))] = hashlib.sha256((copy / target / path.name).read_bytes()).hexdigest()
    (copy / "pyproject.toml").write_bytes(MUTMUT_CONFIG.encode())
    shutil.copy2(ROOT / 'docs/repo-review-md5-exclusion.json', copy / 'md5-exclusion.json')
    (copy / 'source-snapshot.json').write_bytes(json.dumps({'python': sys.version, 'sha256': snapshot}).encode())
    print(f"Isolated copy: {copy}", file=sys.stderr, flush=True)
    return run_review(copy, sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
