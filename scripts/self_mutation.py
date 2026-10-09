#!/usr/bin/env python3
"""Mutation-test the workflow skill's own scripts with its bundled runner and mutmut exporter."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/workflow/scripts"
SOURCES = ("crap.py", "lizard_metrics.py", "mutation.py", "mutation_report.py", "mutmut_export.py", "run_report.py", "windows_job.py")
TESTS = ("test_run_report.py", "test_crap.py", "test_lizard_metrics.py", "test_mutation.py", "test_mutmut_export.py", "test_windows_job.py")
# mutmut names mutants by path from the project root, while the tests import the scripts
# as top-level modules, so the analysis copy places them under src/. The script-entrypoint
# smoke tests run scripts by repository path, which does not exist in the copy, and the
# nested real-mutmut test would rerun mutmut for every mutant.
MUTMUT_CONFIG = """[tool.mutmut]
source_paths = ["src/"]
pytest_add_cli_args_test_selection = ["tests/", "-k", "not script_entrypoint and not real_mutmut"]
"""


def main():
    copy = Path(tempfile.mkdtemp(prefix="workflow-self-mutation-"))
    (copy / "src").mkdir()
    (copy / "tests").mkdir()
    for name in SOURCES:
        shutil.copy2(SCRIPTS / name, copy / "src" / name)
    for name in TESTS:
        shutil.copy2(ROOT / "tests" / name, copy / "tests" / name)
    (copy / "pyproject.toml").write_text(MUTMUT_CONFIG, encoding="utf-8")
    config = {"cwd": ".", "report": "mutation.json", "format": "normalized",
              "command": [sys.executable, str(copy / "src/mutmut_export.py"), "mutation.json"]}
    (copy / "mutation-config.json").write_text(json.dumps(config), encoding="utf-8")
    print(f"Evidence: {copy}", file=sys.stderr)
    return subprocess.run([sys.executable, str(SCRIPTS / "mutation.py"),
                           str(copy / "mutation-config.json"), *sys.argv[1:]]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
