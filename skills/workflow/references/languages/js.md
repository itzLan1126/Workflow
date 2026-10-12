# JavaScript and TypeScript

`crap.py js PROJECT SOURCE...` and `mutation.py js PROJECT` select this language module. `ts` selects the same module. Run mutation checks in a fresh isolated copy.

The default CRAP command uses Node's built-in test runner with experimental type stripping and LCOV coverage. Node 22.21.0 was verified. Arguments after `--` replace the entire command for Jest, Vitest, c8, or TypeScript syntax Node cannot strip. Configure the replacement tool or exporter to write LCOV to the absolute path in `WORKFLOW_COVERAGE_FILE` (Node wrappers can read `process.env.WORKFLOW_COVERAGE_FILE`). A tool's default project-local report directory is not used.

Install Stryker locally and configure its command test runner, for example `testRunner: 'command', commandRunner: {command: 'node --test'}`. The default mutation command selects the JSON reporter. The report at `reports/mutation/mutation.json` must not already exist; it is copied into the evidence directory after the check. Arguments after `--` replace the full mutation command.

Both checks accept `--timeout-ms N` (default 3,600,000). Tool output and evidence paths go to stderr; results go to stdout. Exit codes are 0 for pass, 1 for review needed, and 2 for run failure.
