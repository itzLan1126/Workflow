#!/usr/bin/env python3
"""Validate the project contract for every skill in this repository."""

from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

from strictyaml import YAMLError, load


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_FRONTMATTER_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
    "disable-model-invocation",
}
ALLOWED_SKILL_DIRECTORIES = {"scripts", "references", "assets", "agents"}
NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
MARKDOWN_LINK_PATTERN = re.compile(r"!?\[[^]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")
RESOURCE_PATH_PATTERN = re.compile(
    r"(?<![\w./-])(?:scripts|references|assets|agents)/[A-Za-z0-9_.@+%/-]+"
)
README_SKILL_PATTERN = re.compile(r"\]\(skills/([a-z0-9]+(?:-[a-z0-9]+)*)/SKILL\.md\)")


def parse_frontmatter(content: str) -> tuple[dict | None, str, str | None]:
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        return None, "", "SKILL.md must start with YAML frontmatter"

    try:
        closing_line = lines.index("---", 1)
    except ValueError:
        return None, "", "SKILL.md frontmatter is not closed"

    try:
        metadata = load("\n".join(lines[1:closing_line])).data
    except YAMLError as error:
        return None, "", f"invalid YAML frontmatter: {error}"

    if not isinstance(metadata, dict):
        return None, "", "SKILL.md frontmatter must be a mapping"

    return metadata, "\n".join(lines[closing_line + 1 :]), None


def validate_frontmatter(skill_dir: Path, metadata: dict) -> list[str]:
    problems = []
    unknown_fields = sorted(set(metadata) - ALLOWED_FRONTMATTER_FIELDS)
    if unknown_fields:
        problems.append(f"unknown frontmatter field(s): {', '.join(unknown_fields)}")

    name = metadata.get("name")
    if not isinstance(name, str) or not name.strip():
        problems.append("missing or invalid name")
    elif len(name) > 64 or not NAME_PATTERN.fullmatch(name):
        problems.append("invalid name")
    elif name != skill_dir.name:
        problems.append("name must match its directory")

    description = metadata.get("description")
    if not isinstance(description, str) or not description.strip():
        problems.append("missing or invalid description")
    elif len(description) > 1024:
        problems.append("description exceeds 1,024 characters")

    for field in ("license", "allowed-tools"):
        if field in metadata and (
            not isinstance(metadata[field], str) or not metadata[field].strip()
        ):
            problems.append(f"{field} must be a non-empty string")

    compatibility = metadata.get("compatibility")
    if compatibility is not None and (
        not isinstance(compatibility, str)
        or not compatibility.strip()
        or len(compatibility) > 500
    ):
        problems.append("compatibility must be a non-empty string of at most 500 characters")

    additional_metadata = metadata.get("metadata")
    if additional_metadata is not None and (
        not isinstance(additional_metadata, dict)
        or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in additional_metadata.items()
        )
    ):
        problems.append("metadata must map string keys to string values")

    if metadata.get("disable-model-invocation") != "true":
        problems.append("disable-model-invocation must be true")

    return problems


def referenced_paths(body: str) -> set[str]:
    references = set()
    for match in MARKDOWN_LINK_PATTERN.finditer(body):
        target = match.group(1).strip("<>")
        parsed = urlsplit(target)
        if target.startswith("#") or parsed.scheme or target.startswith("//"):
            continue
        local_path = unquote(parsed.path)
        if local_path:
            references.add(local_path)

    references.update(
        match.group(0).rstrip(".,:;") for match in RESOURCE_PATH_PATTERN.finditer(body)
    )
    return references


def validate_references(skill_dir: Path, body: str) -> list[str]:
    problems = []
    skill_root = skill_dir.resolve()
    for reference in sorted(referenced_paths(body)):
        target = (skill_dir / reference).resolve()
        try:
            target.relative_to(skill_root)
        except ValueError:
            problems.append(f"resource reference escapes the skill directory: {reference}")
            continue
        if not target.exists():
            problems.append(f"missing referenced resource: {reference}")
    return problems


def validate_openai_metadata(skill_dir: Path) -> list[str]:
    metadata_file = skill_dir / "agents" / "openai.yaml"
    if not metadata_file.is_file():
        return ["missing agents/openai.yaml"]

    try:
        metadata = load(metadata_file.read_text(encoding="utf-8")).data
    except (OSError, UnicodeError) as error:
        return [f"cannot read agents/openai.yaml: {error}"]
    except YAMLError as error:
        return [f"invalid agents/openai.yaml: {error}"]

    if not isinstance(metadata, dict):
        return ["agents/openai.yaml must be a mapping"]
    policy = metadata.get("policy")
    if not isinstance(policy, dict) or policy.get("allow_implicit_invocation") != "false":
        return ["agents/openai.yaml must set policy.allow_implicit_invocation to false"]
    return []


def validate_skill(skill_dir: Path) -> list[str]:
    problems = []
    invalid_directories = sorted(
        path.name
        for path in skill_dir.iterdir()
        if path.is_dir() and path.name not in ALLOWED_SKILL_DIRECTORIES
    )
    if invalid_directories:
        problems.append(f"unsupported direct subdirectory(s): {', '.join(invalid_directories)}")

    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        return [f"{skill_dir.name}: missing SKILL.md"]

    try:
        content = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return [f"{skill_dir.name}: cannot read SKILL.md: {error}"]

    if len(content.splitlines()) > 500:
        problems.append("SKILL.md exceeds 500 lines")

    metadata, body, parse_problem = parse_frontmatter(content)
    if parse_problem:
        problems.append(parse_problem)
    else:
        problems.extend(validate_frontmatter(skill_dir, metadata or {}))
        if not body.strip():
            problems.append("SKILL.md has no instructions")
        problems.extend(validate_references(skill_dir, body))

    problems.extend(validate_openai_metadata(skill_dir))
    return [f"{skill_dir.name}: {problem}" for problem in problems]


def validate_readme(root: Path, skill_names: set[str]) -> list[str]:
    readme = root / "README.md"
    try:
        content = readme.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return [f"README.md: cannot read file: {error}"]

    listed_skills = set(README_SKILL_PATTERN.findall(content))
    problems = []
    missing = sorted(skill_names - listed_skills)
    unexpected = sorted(listed_skills - skill_names)
    if missing:
        problems.append(f"README.md: missing skill(s): {', '.join(missing)}")
    if unexpected:
        problems.append(f"README.md: lists unknown skill(s): {', '.join(unexpected)}")
    return problems


def validate_repository(root: Path = ROOT) -> tuple[list[str], int]:
    skills_dir = root / "skills"
    skill_dirs = (
        sorted(path for path in skills_dir.iterdir() if path.is_dir())
        if skills_dir.is_dir()
        else []
    )
    if not skill_dirs:
        return ["No skills found in skills/"], 0

    problems = [problem for skill_dir in skill_dirs for problem in validate_skill(skill_dir)]
    problems.extend(validate_readme(root, {skill_dir.name for skill_dir in skill_dirs}))
    return problems, len(skill_dirs)


def main() -> int:
    problems, skill_count = validate_repository()
    if problems:
        print("\n".join(f"ERROR: {problem}" for problem in problems), file=sys.stderr)
        return 1

    print(
        f"Validated {skill_count} skill(s): YAML frontmatter, project structure, "
        "resources, README, and manual invocation policies."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
