import tempfile
import unittest
from pathlib import Path

from scripts.validation import validate_repository


SKILL = """---
name: demo
description: Demonstrate validation. Use when testing the validator.
disable-model-invocation: true
---

# Demo

Read [the guide](references/guide.md).
"""

OPENAI_METADATA = """interface:
  display_name: Demo
  short_description: Demonstrate validation

policy:
  allow_implicit_invocation: false
"""


class ValidatorTests(unittest.TestCase):
    def repository(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary_directory = tempfile.TemporaryDirectory()
        root = Path(temporary_directory.name)
        skill = root / "skills" / "demo"
        (skill / "references").mkdir(parents=True)
        (skill / "agents").mkdir()
        (skill / "SKILL.md").write_text(SKILL, encoding="utf-8")
        (skill / "references" / "guide.md").write_text("# Guide\n", encoding="utf-8")
        (skill / "agents" / "openai.yaml").write_text(OPENAI_METADATA, encoding="utf-8")
        (root / "README.md").write_text("[demo](skills/demo/SKILL.md)\n", encoding="utf-8")
        return temporary_directory, root

    def test_valid_repository(self):
        temporary_directory, root = self.repository()
        self.addCleanup(temporary_directory.cleanup)
        self.assertEqual(([], 1), validate_repository(root))

    def test_allows_exactly_500_lines(self):
        temporary_directory, root = self.repository()
        self.addCleanup(temporary_directory.cleanup)
        skill_file = root / "skills/demo/SKILL.md"
        line_count = len(SKILL.splitlines())
        skill_file.write_text(SKILL + ("line\n" * (500 - line_count)), encoding="utf-8")
        self.assertEqual(([], 1), validate_repository(root))

    def test_rejects_invalid_project_contracts(self):
        cases = {
            "invalid YAML": (
                "invalid YAML frontmatter",
                lambda root: (root / "skills/demo/SKILL.md").write_text(
                    SKILL.replace("description: Demonstrate", "description: [Demonstrate"),
                    encoding="utf-8",
                ),
            ),
            "unknown frontmatter": (
                "unknown frontmatter field(s): unknown-field",
                lambda root: (root / "skills/demo/SKILL.md").write_text(
                    SKILL.replace(
                        "disable-model-invocation",
                        "unknown-field: value\ndisable-model-invocation",
                    ),
                    encoding="utf-8",
                ),
            ),
            "unsupported directory": (
                "unsupported direct subdirectory(s): templates",
                lambda root: (root / "skills/demo/templates").mkdir(),
            ),
            "too many lines": (
                "SKILL.md exceeds 500 lines",
                lambda root: (root / "skills/demo/SKILL.md").write_text(
                    SKILL + ("line\n" * 500), encoding="utf-8"
                ),
            ),
            "missing resource": (
                "missing referenced resource: references/guide.md",
                lambda root: (root / "skills/demo/references/guide.md").unlink(),
            ),
            "README mismatch": (
                "README.md: missing skill(s): demo",
                lambda root: (root / "README.md").write_text("# Skills\n", encoding="utf-8"),
            ),
            "Claude policy": (
                "disable-model-invocation must be true",
                lambda root: (root / "skills/demo/SKILL.md").write_text(
                    SKILL.replace("disable-model-invocation: true\n", ""), encoding="utf-8"
                ),
            ),
            "Codex policy": (
                "policy.allow_implicit_invocation to false",
                lambda root: (root / "skills/demo/agents/openai.yaml").write_text(
                    OPENAI_METADATA.replace("false", "true"), encoding="utf-8"
                ),
            ),
        }

        for label, (expected, break_contract) in cases.items():
            with self.subTest(label=label):
                temporary_directory, root = self.repository()
                try:
                    break_contract(root)
                    problems, _ = validate_repository(root)
                    self.assertTrue(any(expected in problem for problem in problems), problems)
                finally:
                    temporary_directory.cleanup()


if __name__ == "__main__":
    unittest.main()
