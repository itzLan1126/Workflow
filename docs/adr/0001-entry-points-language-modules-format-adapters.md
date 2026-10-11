---
status: accepted
---

# Split quality checks into entry points, language modules, format adapters, and a shared core

Each check (CRAP and mutation) has one entry point. Everything specific to one programming language lives in its own language module. Report reading lives in format adapters, one per report format rather than one per language, because several languages share one format (LCOV for coverage, the Stryker schema for JS, C#, and Scala mutation). The shared core contains no language-specific code. A language whose tools write a format we already read needs only a new language module. Multi-language tools such as crapkit, crapper, and the Stryker family split the same way.

## Considered Options

- **One script per check, with all languages inside it**: rejected, because language details mix with scoring and every new language changes the gate.
- **One module per language, including report parsing**: rejected, because languages that share a report format would duplicate its parser.
