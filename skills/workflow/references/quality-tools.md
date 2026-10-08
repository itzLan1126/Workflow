# Deterministic quality tools

Use these after conventional review findings are resolved. Requires Python 3.10+; CRAP's bundled multi-language collector also requires `lizard==1.17.31` in the analysis environment. The bundled runners use only the Python standard library; external mutation engines retain their own runtime requirements. Install tools only under the project's permissions. The scripts never install tools automatically.

## Execution contract

Run from any directory, using the installed skill's absolute script paths:

```sh
python /path/to/workflow/scripts/crap.py /path/to/crap-config.json
python /path/to/workflow/scripts/mutation.py /path/to/mutation-config.json
```

Both execute a trusted project's `command` argument array without implicit shell evaluation, then validate the newly generated JSON `report`. Command output goes to stderr; the calculated result goes to stdout. Config `cwd` is relative to the config file; `report` is relative to `cwd`. Commands resolve as they normally do in that working directory. Use absolute tool paths for virtual environments.

- Exit **0**: measured scope meets the CRAP standard, or assessed mutants are killed.
- Exit **1**: CRAP standard not met, or mutation survivors, uncovered mutants, or timeouts require review.
- Exit **2**: invalid/missing/empty report, missing tool, command failure, incomplete run, or no assessable mutants. This is not a quality pass.

Reports must not exist before execution, including symlinks. Choose a new run directory/report path; preserve old evidence rather than overwriting it. `timeoutMs` is optional (default one hour). A command's nonzero exit fails except cargo-mutants finding exits handled by the adapter. Stryker exit 1 is ambiguous (threshold failure or operational error), so it produces exit 2 for inspection; do not silently lower its configured thresholds. These are executable configs: inspect them before running. The scripts do not sandbox commands or prove that a supplied report describes all relevant code.

Use an isolated project copy for mutation execution, including the accepted uncommitted changes and necessary test resources. Exclude credentials and production access. Run baseline tests there. The runner does not create that copy or verify its isolation; do not point mutation commands at the user's working checkout.

On Windows, the [job helper](../scripts/windows_job.py) holds a bootstrap behind a pipe until it is assigned to a kill-on-close Job Object. The tool and its descendants then inherit that job. Cleanup owns the job rather than looking up a potentially exited root PID; timeout failures retain their timeout classification even if cleanup also reports an error.

## CRAP

Every CRAP run in this skill uses one fixed standard, which configs cannot change:

- each function's CRAP ≤ 6;
- aggregate line coverage ≥ 95%;
- aggregate branch coverage ≥ 90%.

The script computes `C² × (1 − covered / total)³ + C` for each function and compares it to 6 using exact rational arithmetic before converting scores to JSON numbers. Because CRAP is at least `C`, this also caps each function's cyclomatic complexity at 6, and a function at 6 needs full coverage. Aggregate coverage is compared exactly over the measured scope. A config containing `maxCrap` is rejected so that an old per-project limit cannot apply silently.

The bundled [collector](../scripts/lizard_metrics.py) measures complexity with Lizard and joins it to LCOV coverage for the same source snapshot: per-function **line** coverage from `DA` records, and aggregate line and branch coverage over the source files in scope from `DA` and `BRDA` records. Lizard supports Python, JavaScript/TypeScript, Rust, Swift, and other languages. Use a real project coverage command that emits LCOV with unexecuted lines and branch records included (for example, coverage.py with `branch = true`); do not handwrite metrics or let an agent estimate them. A report without branch records fails with exit 2 rather than passing.

```sh
python /path/to/workflow/scripts/lizard_metrics.py coverage.lcov measurements.json src/example.rs
```

Pass the source files in scope explicitly. Coverage `SF` paths must resolve to those exact files from the command's working directory; basenames are never guessed. The collector rejects missing coverage, no detected functions, and nested/overlapping/shared-line function ranges. For those cases use an existing language-aware metrics exporter, rather than silently dropping functions. Record selected files and exclusions.

A project-owned Python script can run its coverage command and then the collector with `subprocess.run(..., check=True)`. Configure that script as the command below so coverage and metrics are regenerated together. `measurements.json` must be written at the configured report path.

```json
{
  "cwd": "/absolute/isolated-project-copy",
  "command": ["python", "/absolute/project-analysis/collect-crap.py"],
  "report": "measurements.json"
}
```

Alternative tool-backed exporters must emit:

```json
{"functions":[{"file":"src/example.rs","name":"choose","line":1,"complexity":4,"covered":1,"total":2,"coverageKind":"line"}],
 "coverage":{"line":{"covered":95,"total":100},"branch":{"covered":9,"total":10}}}
```

`coverage.line` and `coverage.branch` are aggregate counts for the whole measured scope; each needs `1 <= total` and `covered <= total`. `coverageKind` must be `line`, `branch`, `statement`, or `basis-path`. The original CRAP1 formula used basis-path coverage; line/branch/statement variants are proxies and must be labeled when comparing scores. Lizard is a lightweight source analyzer, not a compiler. A valid report proves its arithmetic, not complete coverage mapping or correct behavior.

## Mutation testing

Configure a real installed mutation engine and a new output path. Set engine test commands and mutation scope in the target project before running. Supported report adapters:

| Format | Engine and report | Example command argv |
| --- | --- | --- |
| `cargo-mutants` | Rust cargo-mutants `mutants.out/outcomes.json` | `["cargo", "mutants"]` |
| `stryker` | JS/TS Stryker JSON reporter | `["./node_modules/.bin/stryker", "run", "--reporters", "json"]` |
| `muter` | Swift Muter JSON report | `["muter", "run", "--format", "json", "--output", "mutation.json", "--skip-update-check"]` |
| `normalized` | Python mutmut 3 through the bundled [exporter](../scripts/mutmut_export.py) | `["/absolute/venv/bin/python", "/path/to/workflow/scripts/mutmut_export.py", "mutation.json"]` |
| `normalized` | Other engines through a project-owned exporter | `["python", "/absolute/project-analysis/run-mutation.py"]` |

For example, in a fresh Rust analysis copy with cargo-mutants already installed:

```json
{
  "cwd": "/absolute/isolated-project-copy",
  "command": ["cargo", "mutants"],
  "report": "mutants.out/outcomes.json",
  "format": "cargo-mutants",
  "timeoutMs": 3600000
}
```

### Scope to the change

Mutate the changed code by default; whole-project runs can take hours. Widen the scope only with a stated reason, and record the scope with the result.

| Engine | Changed-code scope |
| --- | --- |
| cargo-mutants | `--in-diff changes.diff`, using a diff of the accepted change |
| Stryker | `--mutate "src/a.ts:10-40"` file and line ranges; do not use `--incremental`, which reuses earlier results |
| Muter | `--files-to-mutate` with the changed files |
| mutmut | `only_mutate` globs in the analysis copy's `[tool.mutmut]` configuration |

Do not use cargo-mutants `--check` or skip its baseline. Stryker and Muter must run their normal baseline/test flow. Use Stryker's completed JSON reporter output, never its incremental cache or a partial report. Configure their JSON output to match `report`; do not enable network dashboard upload as part of this workflow.

The normalized adapter requires real engine output converted by executable code, not a prompt-generated summary:

```json
{"baselinePassed":true,"mutants":[{"id":"example","status":"killed"}]}
```

Allowed statuses are `killed`, `survived`, `noCoverage`, `timeout`, `unviable`, `ignored`, and `error`. Only actual failing tests count as kills; compile failures and ignored mutants are excluded. Runtime errors and unfinished runs produce exit 2. Timeouts require investigation instead of being counted as kills. Equivalent survivors require an evidence-backed disposition; do not rewrite the report to get exit 0. Preserve a nonzero result and explain any justified exception.

The mutmut exporter runs `mutmut run` with the interpreter that runs the exporter, so use the analysis environment's Python. It refuses an existing `mutants/` directory because mutmut would reuse stale results, writes no report when mutmut's clean baseline fails, and maps abnormal or unfinished mutants (suspicious, segfault, interrupted, not checked) to `error`. mutmut derives module names from file paths relative to the project root (dropping a leading `src/`), so tests must import the code under those names; code started as a subprocess from another directory is not associated with tests. Other languages are supported through this explicit adapter contract, not automatic engine discovery. Native adapters are covered by report fixtures and subprocess tests; validate the installed engine version and its report format on each target project.

## Sources

- [Original CRAP1 formula](https://testing.googleblog.com/2011/02/this-code-is-crap.html)
- [Lizard languages and analysis](https://github.com/terryyin/lizard)
- [cargo-mutants reports](https://mutants.rs/mutants-out.html)
- [Stryker usage](https://stryker-mutator.io/docs/stryker-js/usage/) and [mutant states](https://stryker-mutator.io/docs/mutation-testing-elements/mutant-states-and-metrics/)
- [Muter](https://github.com/muter-mutation-testing/muter)
