# Deterministic Quality Tools

Use these deterministic quality tools after conventional code review findings are resolved.

## Prerequisites

- **Python**: Requires Python 3.10+.
- **Lizard**: Multi-language CRAP metrics collection requires `lizard==1.17.31` in the analysis environment.
- **Standard Library**: Bundled runners use only the Python standard library, except that mutation reporting optionally uses Lizard (when installed) to name functions containing Stryker mutants.
- **External Tools**: External mutation engines retain their own runtime requirements. Install tools only under project permissions; scripts never install dependencies automatically.

---

## Execution Contract

Run from any directory using absolute paths to the installed skill scripts:

```sh
python /path/to/workflow/scripts/crap.py /path/to/crap-config.json
python /path/to/workflow/scripts/mutation.py /path/to/mutation-config.json
python /path/to/workflow/scripts/mutation.py --json /path/to/mutation-config.json
```

### Protocol & Exit Codes

- **Execution**: Runs a trusted project's `command` argument array directly without implicit shell evaluation.
- **Streams**: Command output streams to `stderr`; calculated result (CRAP JSON or mutation report) outputs to `stdout`.
- **Paths**: `cwd` is relative to the configuration file; `report` path is relative to `cwd`. Use absolute tool paths for virtual environments.
- **Timeout**: `timeoutMs` is optional (defaults to one hour / 3,600,000 ms).
- **Reports**: Reports must not exist prior to execution (including symlinks). Always specify a fresh run directory / report path to preserve historical evidence rather than overwriting it.
- **Config Inspection**: These are executable configurations; inspect them before running. Scripts do not sandbox commands or prove that a supplied report covers all relevant code.

| Exit Code | Meaning                                                                                                                                                                         |
| :-------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **0**     | **Pass**: Measured scope meets the CRAP standard, or all assessed mutants are killed.                                                                                           |
| **1**     | **Review Needed**: CRAP standard unmet, or surviving mutants, uncovered mutants, or timeouts require review.                                                                    |
| **2**     | **Tool / Run Failure**: Invalid/missing/empty report, missing tool, command crash, incomplete run, runtime error, or no assessable mutants. **Never counts as a quality pass.** |

#### Engine Exit Code Handling

- A command's nonzero exit fails the run with exit 2, except cargo-mutants finding exits handled by its adapter.
- Stryker exit 1 is ambiguous (threshold failure or operational error), so it produces exit 2 for manual inspection; do not silently lower its configured thresholds.

### Isolation & Platform Safety

- **Isolated Project Copy**: Always run mutation commands in an isolated disposable copy of the project containing the accepted uncommitted changes and necessary test resources. Exclude credentials and production access. Run baseline tests there. The runner does not create that copy or verify its isolation; never point mutation commands at the user's active checkout.
- **Windows Process Management**: On Windows, the [job helper](../scripts/windows_job.py) holds a bootstrap behind a pipe until assigned to a kill-on-close Job Object. The tool and all descendants inherit that job. Cleanup owns the job rather than looking up a potentially exited root PID; timeout failures retain their timeout classification even if cleanup reports an error.

---

## CRAP Metrics

### Fixed Quality Standard

Every CRAP run strictly enforces one fixed standard that configs cannot alter:

- **Per-function CRAP** ≤ 6
- **Aggregate line coverage** ≥ 95%
- **Aggregate branch coverage** ≥ 90%

> **Formula**: `CRAP = C² × (1 − covered / total)³ + C` (where `C` is cyclomatic complexity).  
> The script computes this using exact rational arithmetic before converting scores to JSON. Because CRAP is always ≥ `C`, cyclomatic complexity is capped at 6, and a function at 6 requires 100% coverage. Configurations containing `maxCrap` are rejected so old per-project limits cannot apply silently.

### Generating Metrics with Lizard & LCOV

Use the bundled [metrics collector](../scripts/lizard_metrics.py) to measure complexity with Lizard and join it to LCOV coverage for the exact same source snapshot:

```sh
python /path/to/workflow/scripts/lizard_metrics.py coverage.lcov measurements.json src/example.rs
```

- **Scope & Resolution**: Pass target source files explicitly. Coverage `SF` paths must resolve to those exact files from the command's working directory; basenames are never guessed.
- **Branch Records Required**: Coverage LCOV must include branch records (`BRDA`, e.g. coverage.py with `branch = true`). A report without branch records fails with exit 2 rather than passing. Do not handwrite metrics or let an agent estimate them.
- **Checksums**: Optional `DA` checksums must agree across sections and match analyzed UTF-8 source lines (LCOV's unpadded base64 MD5). Reports without checksums still require a fresh coverage run for the same source snapshot.
- **Function Ranges**: The collector rejects missing coverage, no detected functions, and nested/overlapping/shared-line function ranges. For those cases, use an existing language-aware metrics exporter rather than silently dropping functions. Record selected files and exclusions.

### CRAP Configuration Example

A project-owned script can run its coverage tool and then the collector with `subprocess.run(..., check=True)`:

```json
{
  "cwd": "/absolute/isolated-project-copy",
  "command": ["python", "/absolute/project-analysis/collect-crap.py"],
  "report": "measurements.json"
}
```

### Exporter Schema & Constraints

Alternative tool-backed exporters must output:

```json
{
  "functions": [
    {
      "file": "src/example.rs",
      "name": "choose",
      "line": 1,
      "complexity": 4,
      "covered": 1,
      "total": 2,
      "coverageKind": "line"
    }
  ],
  "coverage": {
    "line": { "covered": 95, "total": 100 },
    "branch": { "covered": 9, "total": 10 }
  }
}
```

- **Counts**: `coverage.line` and `coverage.branch` are aggregate counts for the whole measured scope; each requires `1 <= total` and `covered <= total`.
- **Kinds**: `coverageKind` must be `line`, `branch`, `statement`, or `basis-path`.
- **Proxies**: The original CRAP1 formula used basis-path coverage; line/branch/statement variants are proxies and must be labeled when comparing scores.
- **Analyzer Scope**: Lizard is a lightweight source analyzer, not a compiler. A valid report proves its arithmetic, not complete coverage mapping or correct behavior.

---

## Mutation Testing

Mutation testing validates test sensitivity by injecting real code faults.

### Report Presentation

- **Default Output**: Groups survivors, uncovered mutants, timeouts, and errors separately by function, displaying mutant IDs and numbered `-`/`+` code diffs. Ends with status counts, exit code, and original report path.
- **Machine Output**: Use `--json` to output summary fields plus actionable `mutants` and `reportPath`.
- **Integrity**: Presentation formatting does not alter the gate or classify timeouts as kills.

### Scope to Changed Code

Mutate only changed code by default; whole-project runs can take hours. Widen scope only with a stated reason, and record the scope with the result:

| Engine                   | Scoping Flag & Instructions                                                                       |
| :----------------------- | :------------------------------------------------------------------------------------------------ |
| **cargo-mutants** (Rust) | `--in-diff changes.diff` using a diff of accepted changes. Do not use `--check` or skip baseline. |
| **Stryker** (JS/TS)      | `--mutate "src/a.ts:10-40"` file/line ranges. Do not use `--incremental` (reuses old cache).      |
| **Muter** (Swift)        | `--files-to-mutate <files>` with changed files. Must run normal baseline and test flow.           |
| **mutmut 3.8** (Python)  | In `[tool.mutmut]`: `source_paths = ["src/"]` and `only_mutate = ["src/changed.py"]`.             |

#### Scoping & Engine Warnings

- **mutmut 3.8**: `only_mutate` is a supported file-glob filter within `source_paths`; `paths_to_mutate` is the deprecated name for `source_paths`, not that filter. Check installed versions before applying to other releases.
- **Stryker**: Use Stryker's completed JSON reporter output, never its incremental cache or a partial report. Configure output path to match `report`; do not enable network dashboard upload.
- **Muter**: Provides positioned before/after snippets labeled as snippets; its report does not supply function names. Missing details are marked explicitly with IDs and evidence paths without inventing source or treating detail gaps as passes.

### Supported Adapters

| Format          | Engine and Report                                                   | Example Command argv                                                                           |
| :-------------- | :------------------------------------------------------------------ | :--------------------------------------------------------------------------------------------- |
| `cargo-mutants` | Rust `mutants.out/outcomes.json`                                    | `["cargo", "mutants"]`                                                                         |
| `stryker`       | JS/TS JSON reporter                                                 | `["./node_modules/.bin/stryker", "run", "--reporters", "json"]`                                |
| `muter`         | Swift JSON report                                                   | `["muter", "run", "--format", "json", "--output", "mutation.json", "--skip-update-check"]`     |
| `normalized`    | Python mutmut 3 via bundled [exporter](../scripts/mutmut_export.py) | `["/absolute/venv/bin/python", "/path/to/workflow/scripts/mutmut_export.py", "mutation.json"]` |
| `normalized`    | Custom project exporter                                             | `["python", "/absolute/project-analysis/run-mutation.py"]`                                     |

#### Configuration Example (`cargo-mutants`)

```json
{
  "cwd": "/absolute/isolated-project-copy",
  "command": ["cargo", "mutants"],
  "report": "mutants.out/outcomes.json",
  "format": "cargo-mutants",
  "timeoutMs": 3600000
}
```

### Normalized Report Schema

The normalized adapter requires real engine output converted by executable code, not a prompt-generated summary:

```json
{
  "baselinePassed": true,
  "mutants": [{ "id": "example-1", "status": "killed" }]
}
```

- **Allowed Statuses**: `killed`, `survived`, `noCoverage`, `timeout`, `unviable`, `ignored`, `error`.
- **Kill Classification**: Only actual failing tests count as kills; compile failures and ignored mutants are excluded.
- **Errors & Timeouts**: Runtime errors and unfinished runs produce exit 2. Timeouts require investigation and never count as kills.
- **Equivalent Mutants**: Equivalent survivors require an evidence-backed disposition; do not rewrite reports to get exit 0. Preserve a nonzero result and explain justified exceptions.
- **Optional Metadata**: Exporters may include `file`, `function`, `line` (declaration line), `diff` (unified diff), and `diffOffset` (default 0). `detailGap` and `evidence` describe unavailable details and evidence paths. Existing status-only reports remain valid and display explicit unavailable-detail markers.

### Python mutmut 3 Details

- **Interpreter**: The bundled [mutmut exporter](../scripts/mutmut_export.py) runs `mutmut run` with the interpreter running the exporter; use the analysis environment's Python.
- **Stale Data Guard**: Refuses an existing `mutants/` directory because mutmut would reuse stale results.
- **Clean Baseline**: Writes no report when mutmut's clean baseline fails.
- **Status Mapping**: Maps abnormal or unfinished mutants (suspicious, segfault, interrupted, not checked) to `error`.
- **Module Names**: mutmut derives module names from file paths relative to project root (dropping a leading `src/`). Tests must import code under those names; code started as a subprocess from another directory is not associated with tests.
- **Adapter Contract**: Other languages are supported through this explicit adapter contract, not automatic engine discovery. Validate installed engine versions and report formats on target projects.
