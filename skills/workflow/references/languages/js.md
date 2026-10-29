# JavaScript and TypeScript

`crap.py js PROJECT SOURCE...` and `mutation.py js PROJECT` select this language module. `ts` selects the same module. Run mutation checks in a fresh isolated copy or pass `--overlay` for automatic creation and cleanup.

The default CRAP command uses Node's built-in test runner with experimental type stripping and LCOV coverage. Node 22.21.0 was verified. Arguments after `--` replace the entire command for Jest, Vitest, c8, or TypeScript syntax Node cannot strip. Configure the replacement tool or exporter to write LCOV to the absolute path in `WORKFLOW_COVERAGE_FILE` (Node wrappers can read `process.env.WORKFLOW_COVERAGE_FILE`). A tool's default project-local report directory is not used.

The default mutation command runs `stryker` from `PATH`. A project-local or `PATH` Stryker 10.1.1 is used when present; otherwise the pinned version is installed into a skill-owned npm prefix without changing package.json or lock files. `--no-install` disables installation. Node.js is required and is never installed. Configure its command test runner, for example `testRunner: 'command', commandRunner: {command: 'node --test'}`. The default mutation command selects the JSON reporter. The report at `reports/mutation/mutation.json` must not already exist; it is copied into the evidence directory after the check. Arguments after `--` replace the full mutation command.

`duplication.py js PROJECT SOURCE...` (or `ts`) checks functions, methods and top-level arrow/function assignments; nested callbacks stay inside their enclosing function. Supported extensions are .js, .jsx, .mjs, .cjs, .ts and .tsx. Parser packages are pinned and installed automatically.

Mutation accepts `--previous-evidence DIRECTORY`; unchanged non-actionable outcomes are labelled as reused. Changed files are passed to Stryker's `--mutate` option, so every mutant in a changed file runs again; the result reports this `full file` fallback. Tests, engine/configuration or module changes force a full run; damaged evidence fails closed. Installed tool versions appear in config.json. See the [shared contract](../quality-tools.md).

Both checks accept `--timeout-ms N` (default 3,600,000). Tool output and evidence paths go to stderr; results go to stdout. Exit codes are 0 for pass, 1 for review needed, and 2 for run failure.
