#!/usr/bin/env python3
"""Check every production Python script for structural duplication."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/workflow/scripts'


def main():
    return subprocess.run([sys.executable, str(SCRIPTS / 'duplication.py'), 'python', str(ROOT),
                           *(str(path) for directory in (SCRIPTS, ROOT / 'scripts')
                             for path in sorted(directory.glob('*.py')))], cwd=ROOT).returncode


if __name__ == '__main__':
    raise SystemExit(main())
