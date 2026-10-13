#!/usr/bin/env python3
"""Mutation-test every production Python script in a fresh analysis copy."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/workflow/scripts"
# mutmut names mutants by path from the project root, while the tests import the scripts
# as top-level modules, so the analysis copy places them under src/. The script-entrypoint
# smoke tests run scripts by repository path, which does not exist in the copy, and the
# nested real-mutmut test would rerun mutmut for every mutant.
MUTMUT_CONFIG = """[tool.mutmut]
source_paths = ["src/", "scripts/"]
pytest_add_cli_args_test_selection = ["tests/", "-k", "not script_entrypoint and not real_mutmut"]
"""


def main():
    copy = Path(tempfile.mkdtemp(prefix="workflow-self-mutation-"))
    snapshot = {}
    for original, target in ((SCRIPTS, 'src'), (ROOT / 'scripts', 'scripts'), (ROOT / 'tests', 'tests')):
        (copy / target).mkdir()
        for path in sorted(original.glob('*.py')):
            shutil.copy2(path, copy / target / path.name)
            snapshot[str(path.relative_to(ROOT))] = hashlib.sha256((copy / target / path.name).read_bytes()).hexdigest()
    (copy / "pyproject.toml").write_text(MUTMUT_CONFIG, encoding="utf-8")
    (copy / 'source-snapshot.json').write_text(json.dumps({'python': sys.version, 'sha256': snapshot}, indent=2), encoding='utf-8')
    print(f"Isolated copy: {copy}", file=sys.stderr, flush=True)
    return subprocess.run([sys.executable, str(SCRIPTS / "mutation.py"),
                           *sys.argv[1:], 'python', str(copy)]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
