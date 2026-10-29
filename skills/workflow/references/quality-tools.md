# Deterministic quality checks

The bundled scripts require Python 3.10+. Missing pinned project-independent tools are installed into skill-owned environments outside the project. System toolchains and project test dependencies must already be available. See the selected language guide: [Python](languages/python.md), [JavaScript and TypeScript](languages/js.md), [Rust](languages/rust.md), or [Swift](languages/swift.md).

## Entry points

```sh
python /path/to/workflow/scripts/crap.py LANGUAGE PROJECT SOURCE... [--timeout-ms N] [-- tool args]
python /path/to/workflow/scripts/mutation.py [--json] LANGUAGE PROJECT [--overlay] [--previous-evidence DIRECTORY] [--no-install] [--timeout-ms N] [-- tool args]
python /path/to/workflow/scripts/duplication.py LANGUAGE PROJECT SOURCE... [--no-install]
python /path/to/workflow/scripts/crap.py CONFIG.json
python /path/to/workflow/scripts/mutation.py [--json] CONFIG.json
python /path/to/workflow/scripts/crap.py collect COVERAGE.lcov OUTPUT.json SOURCE...
```

A registered language name selects its language module; any other argument is a config path. Arguments after `--` go to the external tool unchanged. Language runs create a fresh evidence directory and print its path to stderr. Record scope, tool versions, and exclusions with the result.

Coverage commands receive `WORKFLOW_COVERAGE_FILE`, the absolute path of the fresh report expected by the selected language module. Configure replacement tools or their exporters to write that path; it is recorded in the evidence directory's `config.json`. Arguments remain literal and are not expanded by a shell.

Mutation commands and config-mode commands receive `WORKFLOW_REPORT_FILE`, the absolute expected report path derived from `cwd` and `report`. Replacement commands or their exporters must write to that path; read it from the environment rather than using a shell placeholder in the argument array.

Tool output goes to stderr; the result goes to stdout. Exit 0 means pass, exit 1 means review needed, and exit 2 means run failure. Missing tools, invalid or incomplete evidence, crashed commands, and no assessed mutants never count as a pass. Commands run as argument arrays without implicit shell evaluation. Timeouts default to 3,600,000 milliseconds; valid values are 1 through 2,147,483,647.

Run mutation checks in a fresh isolated copy containing the accepted changes and test resources, or pass `--overlay` to create and clean up a disposable copy automatically. The overlay copies every file except `.git` into a disposable parent directory, so Swift's sibling mutated directory stays inside it. Links between project files are redirected into the copy, preserving executable resolution such as npm `.bin` shims; targets outside the project are copied as private files. Nothing links back to the original project. Engines retain their own parallelism. Preserve evidence; never alter reports to obtain a pass.

All three language entry points accept `--no-install`. Python tools use one `pip install --target` directory per tool and interpreter version, Stryker a private npm prefix, and Cargo tools a private install root, all under `~/.cache/workflow/tools` (override with `WORKFLOW_TOOL_HOME`, outside the project). While a check runs, owned Python tools come first on `PYTHONPATH` and owned engine binaries first on `PATH`; both are restored afterwards, and test commands still run under the interpreter that runs the bundled scripts. Exact tools, versions and locations appear in `config.json`. Environments have a completion marker and their exact versions are checked on reuse; for example 10.1.10 does not satisfy a 10.1.1 pin. Failed installs, incomplete environments and version mismatches are run failures. Python, Node, Rust toolchains and Xcode/Swift are never installed; Muter requires manual installation.

`--previous-evidence` opts into incremental mutation. `snapshot.json` preserves source/function hashes, tests, configuration, engine identity and language module identity; `outcomes.json` preserves every outcome bound to its source file (and, for Python, its function). The snapshot is sealed with SHA-256 hashes of its own content and of `outcomes.json`; missing, edited, truncated or older-schema evidence is a run failure, and the engine is not started. Deleted source files, test, engine, configuration or language-module changes, or outcomes that cannot be bound to one source file, force a full run. Actionable outcomes always run again. Python selects mutmut functions (module-level code, signatures and class structure changes select the whole file); other engines select complete changed files. `incrementalScope` in the result names the files, functions and any fallback. Engine identity ignores the disposable overlay path, and freshly run mutants replace their earlier outcomes. Reused outcomes retain their statuses, appear with `reused: true`, and contribute to the normal gate. Replacement commands have no selection protocol, so they rerun in full when anything changed.

The duplication standard is fixed at similarity 0.8 with minimum 4 lines and 20 normalized nodes. Python, JS/TS and Rust compare functions within the same language. Swift returns `unverified: language not supported` and exit 1. Unparseable or unsupported selected sources fail with exit 2. Threshold and size overrides are rejected.

## Config mode

Configs require `cwd`, `report`, and a nonempty `command` argument array. `timeoutMs` is optional. `cwd` is relative to the config file; `report` is relative to `cwd`. Reports must not already exist, including symlinks. Inspect executable configs before running them. Use absolute executable paths for virtual environments.

Mutation configs also require `format`: `normalized`, `stryker`, `cargo-mutants`, or `muter`. Accepted external exit codes belong to the format adapter. A nonzero command exit normally produces a run failure; adapters may accept documented finding exits, but a nonzero exit with no reported findings is inconsistent evidence.

## CRAP standard and measurements

Every function must have CRAP at most 6, aggregate line coverage at least 95%, and aggregate branch coverage at least 90%. These requirements are fixed. `maxCrap` configs are rejected. Swift substitutes explicitly labeled region coverage because its compiler produces no branch records.

The formula is `C² × (1 − covered / total)³ + C`. Comparison uses exact rational arithmetic. Complexity at 6 requires full function coverage.

The collector joins Lizard complexity to freshly generated coverage for the same source snapshot. Pass source files explicitly. Coverage paths must resolve to those exact files from the project's working directory. Each covered line belongs to its innermost function; ambiguous shared-line function ranges cause a run failure. A language module may exclude test-code line ranges. LCOV checksums, when present, must match source lines and agree across sections.

LLVM JSON must contain each selected source file once, including across `data` objects. Duplicate source entries cause a run failure; combine coverage with LLVM before exporting rather than concatenating independent exports.

Config-mode exporters produce this measurement schema:

```json
{
  "functions": [{"file":"src/example.rs","name":"choose","line":1,"complexity":4,"covered":1,"total":2,"coverageKind":"line"}],
  "coverage": {"line":{"covered":95,"total":100},"branch":{"covered":9,"total":10}}
}
```

Counts are nonnegative integers, `covered <= total`, and each total is positive. Function `coverageKind` is `line`, `branch`, `statement`, or `basis-path`. Line, branch, and statement measurements are proxies for the original basis-path formula. Lizard is a source analyzer, not a compiler; valid arithmetic alone does not prove complete coverage mapping.

## Normalized mutation reports

Other engines can use executable exporters to produce:

```json
{"baselinePassed":true,"mutants":[{"id":"example-1","status":"killed"}]}
```

Allowed statuses are `killed`, `survived`, `noCoverage`, `timeout`, `unviable`, `ignored`, and `error`. Only failing tests count as killed. Assessed mutants have status killed, survived, noCoverage, or timeout. Unviable and ignored mutants are excluded. Survived, noCoverage, and timeout require review; errors or no assessed mutants produce a run failure.

Optional details include `file`, `function`, `line` (declaration line), `diff` (unified diff), and `diffOffset` (default 0). `detailGap` and `evidence` identify unavailable details and preserved evidence. Status-only reports remain valid. Details are read only for actionable mutants. Equivalent survivors require an evidence-backed disposition and retain their nonzero result.
