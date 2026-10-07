#!/usr/bin/env python3
"""CRAP-test the workflow skill's own scripts with its bundled collector and gate."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/workflow/scripts"
SOURCES = ("crap.py", "lizard-metrics.py", "mutation.py", "mutmut_export.py", "run_report.py")
# Several tests run the scripts as subprocesses, so coverage patches subprocess to measure them.
COVERAGE_CONFIG = """[run]
branch = true
source = {source}
patch = subprocess
data_file = {data}
"""


def main():
    evidence = Path(tempfile.mkdtemp(prefix="workflow-self-crap-"))
    print(f"Evidence: {evidence}", file=sys.stderr)
    rcfile = evidence / "coveragerc"
    rcfile.write_text(COVERAGE_CONFIG.format(source=SCRIPTS, data=evidence / ".coverage"), encoding="utf-8")
    lcov = evidence / "coverage.lcov"
    for step in (["run", "-m", "unittest", "discover", "-s", "tests"], ["combine"], ["lcov", "-o", str(lcov)]):
        command = [sys.executable, "-m", "coverage", step[0], f"--rcfile={rcfile}", *step[1:]]
        if subprocess.run(command, cwd=ROOT, stdout=sys.stderr).returncode:
            print(f"self_crap: coverage {step[0]} failed", file=sys.stderr)
            return 2
    # LCOV paths are relative to the repository root, so the collector runs there and writes its
    # report into the evidence directory.
    config = {"cwd": str(ROOT), "report": str(evidence / "measurements.json"),
              "command": [sys.executable, str(SCRIPTS / "lizard-metrics.py"), str(lcov),
                          str(evidence / "measurements.json"), *(str(SCRIPTS / name) for name in SOURCES)]}
    (evidence / "crap-config.json").write_text(json.dumps(config), encoding="utf-8")
    return subprocess.run([sys.executable, str(SCRIPTS / "crap.py"), str(evidence / "crap-config.json")]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
