#!/usr/bin/env python3
"""Run the CRAP entry point against every production Python script."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/workflow/scripts'


def main():
    return subprocess.run([sys.executable, str(SCRIPTS / 'crap.py'), 'python', str(ROOT),
                           *(str(path) for directory in (SCRIPTS, ROOT / 'scripts')
                             for path in sorted(directory.glob('*.py'))),
                           '--', '-m', 'unittest', 'discover', '-s', 'tests'], cwd=ROOT).returncode


if __name__ == '__main__':
    raise SystemExit(main())
