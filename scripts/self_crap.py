#!/usr/bin/env python3
"""Run the CRAP entry point against the workflow scripts."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/workflow/scripts'


def main():
    return subprocess.run([sys.executable, str(SCRIPTS / 'crap.py'), 'python', str(ROOT),
                           *(str(path) for path in sorted(SCRIPTS.glob('*.py'))),
                           '--', '-m', 'unittest', 'discover', '-s', 'tests'], cwd=ROOT).returncode


if __name__ == '__main__':
    raise SystemExit(main())
