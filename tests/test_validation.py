import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import validation

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

    def test_allows_percent_encoded_resource_links(self):
        temporary_directory, root = self.repository()
        self.addCleanup(temporary_directory.cleanup)
        skill_file = root / "skills/demo/SKILL.md"
        skill_file.write_text(
            SKILL.replace("references/guide.md", "references/my%20guide.md"),
            encoding="utf-8",
        )
        (root / "skills/demo/references/guide.md").rename(
            root / "skills/demo/references/my guide.md"
        )
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

    def test_frontmatter_parser_preserves_mapping_and_body(self):
        self.assertEqual(
            ({"name": "demo", "metadata": {"author": "测试"}}, "\n# Instructions", None),
            validation.parse_frontmatter(
                "---\r\nname: demo\r\nmetadata:\r\n  author: 测试\r\n---\r\n\r\n# Instructions"
            ),
        )
        for content, message in (
            ("", "SKILL.md must start with YAML frontmatter"),
            ("# Demo\n---\n", "SKILL.md must start with YAML frontmatter"),
            (" ---\nname: demo\n---", "SKILL.md must start with YAML frontmatter"),
            ("---\nname: demo", "SKILL.md frontmatter is not closed"),
            ("---\n- demo\n---", "SKILL.md frontmatter must be a mapping"),
            ("---\n\n---", "SKILL.md frontmatter must be a mapping"),
            ("---\n---", "SKILL.md frontmatter must be a mapping"),
        ):
            with self.subTest(content=content):
                self.assertEqual((None, "", message), validation.parse_frontmatter(content))
        metadata, body, problem = validation.parse_frontmatter("---\nname: [demo\n---")
        self.assertIsNone(metadata)
        self.assertEqual("", body)
        self.assertTrue(problem.startswith("invalid YAML frontmatter: "), problem)

    def test_frontmatter_field_contracts_and_boundaries(self):
        base = {"name": "demo", "description": "Demo", "disable-model-invocation": "true"}
        self.assertEqual([], validation.validate_frontmatter(Path("demo"), {
            **base, "license": "MIT", "allowed-tools": "Read", "compatibility": "x" * 500,
            "metadata": {"author": "测试", "version": "1"},
        }))
        self.assertEqual([], validation.validate_frontmatter(Path("a" * 64), {
            **base, "name": "a" * 64, "description": "x" * 1024,
            "compatibility": None, "metadata": {},
        }))
        self.assertEqual([], validation.validate_frontmatter(Path("demo"), {**base, "metadata": None}))
        cases = [
            ("name", None, "missing or invalid name"),
            ("name", 3, "missing or invalid name"),
            ("name", "", "missing or invalid name"),
            ("name", " \t", "missing or invalid name"),
            ("name", "Demo", "invalid name"),
            ("name", "demo_", "invalid name"),
            ("name", "-demo", "invalid name"),
            ("name", "demo-", "invalid name"),
            ("name", "demo--name", "invalid name"),
            ("name", "demo\n", "invalid name"),
            ("name", "a" * 65, "invalid name"),
            ("name", "other", "name must match its directory"),
            ("description", None, "missing or invalid description"),
            ("description", [], "missing or invalid description"),
            ("description", "", "missing or invalid description"),
            ("description", " \n\t", "missing or invalid description"),
            ("description", "x" * 1025, "description exceeds 1,024 characters"),
            ("license", "", "license must be a non-empty string"),
            ("license", 2, "license must be a non-empty string"),
            ("license", " \t", "license must be a non-empty string"),
            ("allowed-tools", None, "allowed-tools must be a non-empty string"),
            ("allowed-tools", " ", "allowed-tools must be a non-empty string"),
            ("compatibility", 5, "compatibility must be a non-empty string of at most 500 characters"),
            ("compatibility", "", "compatibility must be a non-empty string of at most 500 characters"),
            ("compatibility", " \t", "compatibility must be a non-empty string of at most 500 characters"),
            ("compatibility", "x" * 501, "compatibility must be a non-empty string of at most 500 characters"),
            ("metadata", "author", "metadata must map string keys to string values"),
            ("metadata", {1: "one"}, "metadata must map string keys to string values"),
            ("metadata", {"author": 1}, "metadata must map string keys to string values"),
            ("disable-model-invocation", True, "disable-model-invocation must be true"),
            ("disable-model-invocation", "false", "disable-model-invocation must be true"),
        ]
        for field, value, problem in cases:
            with self.subTest(field=field, value=value):
                self.assertEqual([problem], validation.validate_frontmatter(Path("demo"), {**base, field: value}))
        self.assertEqual([
            "unknown frontmatter field(s): a, z", "missing or invalid name",
            "missing or invalid description", "license must be a non-empty string",
            "allowed-tools must be a non-empty string",
            "compatibility must be a non-empty string of at most 500 characters",
            "metadata must map string keys to string values", "disable-model-invocation must be true",
        ], validation.validate_frontmatter(Path("demo"), {
            "z": "bad", "a": "bad", "license": "", "allowed-tools": "", "compatibility": "", "metadata": [],
        }))

    def test_local_resource_extraction(self):
        body = """[guide](./guide.md?view=1#section "Title")
![image](<assets/icon%20one.png>) [anchor](#section) [empty]()
[web](https://example.com/guide.md) [mail](mailto:a@example.com)
[remote](//example.com/guide.md) [wrapped remote](<//example.com/guide.md>)
`references/guide.md.` scripts/tool.py, assets/icon.svg: agents/openai.yaml;
[encoded](references/my%20guide.md)"""
        self.assertEqual({
            "./guide.md", "assets/icon one.png", "references/guide.md", "scripts/tool.py",
            "assets/icon.svg", "agents/openai.yaml", "references/my guide.md",
        }, validation.referenced_paths(body))
        self.assertEqual(set(), validation.referenced_paths("No references here."))
        self.assertEqual("", validation.local_link_path("<?query=1#anchor>"))
        self.assertEqual("guide.md", validation.local_link_path("<guide.md>"))
        self.assertEqual("Xguide.mdX", validation.local_link_path("<Xguide.mdX>"))
        self.assertEqual({"references/guide.mdX"}, validation.referenced_paths("references/guide.mdX."))

    def test_resource_boundaries_missing_files_and_symlinks(self):
        temporary_directory, root = self.repository()
        self.addCleanup(temporary_directory.cleanup)
        skill = root / "skills/demo"
        (skill / "references/escape.md").symlink_to(root / "README.md")
        body = "[a](../README.md) [b](%2E%2E/README.md) [c](references/escape.md) [d](missing.md)"
        self.assertEqual([
            "resource reference escapes the skill directory: ../README.md",
            "missing referenced resource: missing.md",
            "resource reference escapes the skill directory: references/escape.md",
        ], validation.validate_references(skill, body))
        self.assertEqual([
            f"resource reference escapes the skill directory: {root / 'README.md'}",
        ], validation.validate_references(skill, f"[absolute]({root / 'README.md'})"))
        self.assertEqual([], validation.validate_references(skill, "[here](.) [guide](references/guide.md)"))

    def test_openai_metadata_shape_policy_and_read_failures(self):
        self.assertEqual([], validation.parse_openai_metadata(OPENAI_METADATA))
        for content, problem in (
            ("- item\n", "agents/openai.yaml must be a mapping"),
            ("policy: false", "agents/openai.yaml must set policy.allow_implicit_invocation to false"),
            ("interface: Demo", "agents/openai.yaml must set policy.allow_implicit_invocation to false"),
            ("policy:\n  unrelated: false", "agents/openai.yaml must set policy.allow_implicit_invocation to false"),
            ("policy:\n  allow_implicit_invocation: true", "agents/openai.yaml must set policy.allow_implicit_invocation to false"),
        ):
            with self.subTest(content=content):
                self.assertEqual([problem], validation.parse_openai_metadata(content))
        problem = validation.parse_openai_metadata("policy: [broken")[0]
        self.assertTrue(problem.startswith("invalid agents/openai.yaml: "), problem)
        temporary_directory, root = self.repository()
        self.addCleanup(temporary_directory.cleanup)
        skill = root / "skills/demo"
        with patch.object(Path, "read_text", side_effect=OSError("denied")) as read:
            self.assertEqual(["cannot read agents/openai.yaml: denied"], validation.validate_openai_metadata(skill))
            read.assert_called_once_with(encoding="utf-8")
        (skill / "agents/openai.yaml").write_bytes(b"\xff")
        self.assertTrue(validation.validate_openai_metadata(skill)[0].startswith("cannot read agents/openai.yaml: "))
        (skill / "agents/openai.yaml").unlink()
        self.assertEqual(["missing agents/openai.yaml"], validation.validate_openai_metadata(skill))

    def test_skill_content_problems_are_accumulated(self):
        temporary_directory, root = self.repository()
        self.addCleanup(temporary_directory.cleanup)
        skill = root / "skills/demo"
        invalid = "---\nname: [broken\n---\n" + "line\n" * 498
        self.assertEqual("SKILL.md exceeds 500 lines", validation.validate_skill_content(skill, invalid)[0])
        self.assertTrue(validation.validate_skill_content(skill, invalid)[1].startswith("invalid YAML frontmatter: "))
        blank = SKILL.split("---", 2)[0] + "---" + SKILL.split("---", 2)[1] + "---\n \t\n"
        self.assertEqual(["SKILL.md has no instructions"], validation.validate_skill_content(skill, blank))
        (skill / "templates").mkdir()
        (skill / "z-extra").mkdir()
        (skill / "README.txt").write_text("allowed root file", encoding="utf-8")
        (skill / "scripts").mkdir()
        (skill / "assets").mkdir()
        self.assertEqual(["unsupported direct subdirectory(s): templates, z-extra"], validation.validate_directories(skill))
        (skill / "SKILL.md").write_text("Invalid frontmatter", encoding="utf-8")
        (skill / "agents/openai.yaml").unlink()
        self.assertEqual([
            "demo: unsupported direct subdirectory(s): templates, z-extra",
            "demo: SKILL.md must start with YAML frontmatter", "demo: missing agents/openai.yaml",
        ], validation.validate_skill(skill))
        with patch.object(Path, "read_text", side_effect=OSError("denied")) as read:
            self.assertEqual(["demo: cannot read SKILL.md: denied"], validation.validate_skill(skill))
            read.assert_called_once_with(encoding="utf-8")
        (skill / "SKILL.md").write_bytes(b"\xff")
        self.assertTrue(validation.validate_skill(skill)[0].startswith("demo: cannot read SKILL.md: "))
        (skill / "SKILL.md").unlink()
        self.assertEqual(["demo: missing SKILL.md"], validation.validate_skill(skill))

    def test_readme_exact_missing_and_unknown_skills(self):
        temporary_directory, root = self.repository()
        self.addCleanup(temporary_directory.cleanup)
        (root / "README.md").write_text("[x](skills/x/SKILL.md) [y](skills/y/SKILL.md)", encoding="utf-8")
        self.assertEqual([
            "README.md: missing skill(s): a, demo", "README.md: lists unknown skill(s): x, y",
        ], validation.validate_readme(root, {"demo", "a"}))
        with patch.object(Path, "read_text", side_effect=OSError("denied")) as read:
            self.assertEqual(["README.md: cannot read file: denied"], validation.validate_readme(root, {"demo"}))
            read.assert_called_once_with(encoding="utf-8")
        (root / "README.md").write_bytes(b"\xff")
        self.assertTrue(validation.validate_readme(root, {"demo"})[0].startswith("README.md: cannot read file: "))
        (root / "README.md").unlink()
        self.assertTrue(validation.validate_readme(root, {"demo"})[0].startswith("README.md: cannot read file: "))

    def test_skill_discovery_empty_missing_and_sorted_directories(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.assertEqual((["No skills found in skills/"], 0), validation.validate_repository(root))
            (root / "skills").mkdir()
            (root / "skills/ignored.txt").write_text("not a skill", encoding="utf-8")
            self.assertEqual((["No skills found in skills/"], 0), validation.validate_repository(root))
        temporary_directory, root = self.repository()
        self.addCleanup(temporary_directory.cleanup)
        original = root / "skills/demo"
        shutil.copytree(original, root / "skills/alpha")
        (root / "skills/alpha/SKILL.md").write_text(SKILL.replace("name: demo", "name: alpha"), encoding="utf-8")
        (root / "skills/ignored.txt").write_text("not a skill", encoding="utf-8")
        (root / "README.md").write_text("[demo](skills/demo/SKILL.md) [alpha](skills/alpha/SKILL.md)", encoding="utf-8")
        self.assertEqual([root / "skills/alpha", original], validation.skill_directories(root))
        self.assertEqual(([], 2), validation.validate_repository(root))
        (original / "references/guide.md").unlink()
        (root / "skills/alpha/agents/openai.yaml").unlink()
        self.assertEqual(([
            "alpha: missing agents/openai.yaml", "demo: missing referenced resource: references/guide.md",
        ], 2), validation.validate_repository(root))

    def test_uses_case_sensitive_document_paths(self):
        temporary_directory, root = self.repository()
        self.addCleanup(temporary_directory.cleanup)
        skill = root / "skills/demo"
        contents = {
            skill / "SKILL.md": SKILL,
            skill / "agents/openai.yaml": OPENAI_METADATA,
            root / "README.md": "[demo](skills/demo/SKILL.md)\n",
        }

        def read_document(path, *, encoding):
            self.assertEqual("utf-8", encoding)
            if path not in contents:
                raise FileNotFoundError(str(path))
            return contents[path]

        # Enforce the repository's exact names even on a case-insensitive filesystem.
        with patch.object(Path, "read_text", autospec=True, side_effect=read_document):
            self.assertEqual(([], 1), validation.validate_repository(root))

    def test_main_exit_codes_output_and_error_stream(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(validation, "validate_repository", return_value=([], 2)) as validate:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(0, validation.main())
            validate.assert_called_once_with()
        self.assertEqual(
            "Validated 2 skill(s): YAML frontmatter, project structure, resources, README, and manual invocation policies.\n",
            stdout.getvalue(),
        )
        self.assertEqual("", stderr.getvalue())
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(validation, "validate_repository", return_value=(["first", "second"], 2)):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(1, validation.main())
        self.assertEqual("", stdout.getvalue())
        self.assertEqual("ERROR: first\nERROR: second\n", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
