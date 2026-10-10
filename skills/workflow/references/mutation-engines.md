# Mutation Engines

Per-engine scoping, adapter commands, and caveats. Read the entries and notes for the project's engine; the shared runner contract and normalized schema live in [the tool guide](quality-tools.md).

## Scope to Changed Code

| Engine                   | Scoping Flag & Instructions                                                                       |
| :----------------------- | :------------------------------------------------------------------------------------------------ |
| **cargo-mutants** (Rust) | `--in-diff changes.diff` using a diff of accepted changes. Do not use `--check` or skip baseline. |
| **Stryker** (JS/TS)      | `--mutate "src/a.ts:10-40"` file/line ranges. Do not use `--incremental` (reuses old cache).      |
| **Muter** (Swift)        | `--files-to-mutate <files>` with changed files. Must run normal baseline and test flow.           |
| **mutmut 3.8** (Python)  | In `[tool.mutmut]`: `source_paths = ["src/"]` and `only_mutate = ["src/changed.py"]`.             |

### Engine Warnings

- **mutmut 3.8**: `only_mutate` is a supported file-glob filter within `source_paths`; `paths_to_mutate` is the deprecated name for `source_paths`, not that filter. Check installed versions before applying to other releases.
- **Stryker**: Use Stryker's completed JSON reporter output, never its incremental cache or a partial report. Configure output path to match `report`; do not enable network dashboard upload.
- **Muter**: Provides positioned before/after snippets labeled as snippets; its report does not supply function names. Missing details are marked explicitly with IDs and evidence paths without inventing source or treating detail gaps as passes.

## Supported Adapters

| Format          | Engine and Report                                                   | Example Command argv                                                                           |
| :-------------- | :------------------------------------------------------------------ | :--------------------------------------------------------------------------------------------- |
| `cargo-mutants` | Rust `mutants.out/outcomes.json`                                    | `["cargo", "mutants"]`                                                                         |
| `stryker`       | JS/TS JSON reporter                                                 | `["./node_modules/.bin/stryker", "run", "--reporters", "json"]`                                |
| `muter`         | Swift JSON report                                                   | `["muter", "run", "--format", "json", "--output", "mutation.json", "--skip-update-check"]`     |
| `normalized`    | Python mutmut 3 via bundled [exporter](../scripts/mutmut_export.py) | `["/absolute/venv/bin/python", "/path/to/workflow/scripts/mutmut_export.py", "mutation.json"]` |
| `normalized`    | Custom project exporter                                             | `["python", "/absolute/project-analysis/run-mutation.py"]`                                     |

### Configuration Example (`cargo-mutants`)

```json
{
  "cwd": "/absolute/isolated-project-copy",
  "command": ["cargo", "mutants"],
  "report": "mutants.out/outcomes.json",
  "format": "cargo-mutants",
  "timeoutMs": 3600000
}
```

## Python mutmut 3 Details

- **Interpreter**: The bundled [mutmut exporter](../scripts/mutmut_export.py) runs `mutmut run` with the interpreter running the exporter; use the analysis environment's Python.
- **Stale Data Guard**: Refuses an existing `mutants/` directory because mutmut would reuse stale results.
- **Clean Baseline**: Writes no report when mutmut's clean baseline fails.
- **Status Mapping**: Maps abnormal or unfinished mutants (suspicious, segfault, interrupted, not checked) to `error`.
- **Module Names**: mutmut derives module names from file paths relative to project root (dropping a leading `src/`). Tests must import code under those names; code started as a subprocess from another directory is not associated with tests.
