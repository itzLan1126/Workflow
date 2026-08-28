#!/usr/bin/env python3
"""Validate the required structure of every skill in this repository."""

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)


def scalar(frontmatter: str, field: str) -> str | None:
    match = re.search(rf"^{field}:\s*(.+?)\s*$", frontmatter, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip("\"'")


def validate(skill_dir: Path) -> list[str]:
    problems = []
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        return [f"{skill_dir.name}: missing SKILL.md"]

    content = skill_file.read_text(encoding="utf-8")
    frontmatter_match = FRONTMATTER_PATTERN.match(content)
    if not frontmatter_match:
        return [f"{skill_dir.name}: SKILL.md must start with YAML frontmatter"]

    frontmatter = frontmatter_match.group(1)
    name = scalar(frontmatter, "name")
    description = scalar(frontmatter, "description")

    if not name:
        problems.append(f"{skill_dir.name}: missing name")
    elif len(name) > 64 or not NAME_PATTERN.fullmatch(name):
        problems.append(f"{skill_dir.name}: invalid name")
    elif name != skill_dir.name:
        problems.append(f"{skill_dir.name}: name must match its directory")

    if not description:
        problems.append(f"{skill_dir.name}: missing description")
    elif len(description) > 1024:
        problems.append(f"{skill_dir.name}: description exceeds 1,024 characters")

    if not content[frontmatter_match.end() :].strip():
        problems.append(f"{skill_dir.name}: SKILL.md has no instructions")

    return problems


def main() -> int:
    skill_dirs = sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir()) if SKILLS_DIR.is_dir() else []
    if not skill_dirs:
        print("No skills found in skills/", file=sys.stderr)
        return 1

    problems = [problem for skill_dir in skill_dirs for problem in validate(skill_dir)]
    if problems:
        print("\n".join(f"ERROR: {problem}" for problem in problems), file=sys.stderr)
        return 1

    print(f"Validated {len(skill_dirs)} skill(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
