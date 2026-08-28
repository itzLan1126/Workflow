# Agent Skills Collection

A small, portable collection of [Agent Skills](https://agentskills.io/) for compatible AI agents.

## Repository layout

```text
.
├── .github/workflows/validate.yml
├── scripts/validate_skills.py
├── skills/
│   └── markdown-outline/
│       └── SKILL.md
├── LICENSE
└── README.md
```

Each skill lives in its own directory under `skills/`. A skill requires only a `SKILL.md` file with `name` and `description` frontmatter. Add `scripts/`, `references/`, or `assets/` inside a skill only when the workflow needs them.

## Try the example

For a user-level Codex installation:

```sh
cp -R skills/markdown-outline ~/.agents/skills/
```

For a repository-scoped installation, copy it to `.agents/skills/` in that repository instead.

Then ask the agent to create an outline from a Markdown document, or invoke `$markdown-outline` explicitly.

## License

Licensed under the [MIT License](LICENSE).
