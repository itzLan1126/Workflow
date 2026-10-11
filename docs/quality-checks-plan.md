# Implementation Plan: Quality Checks by Language

This plan restructures the CRAP check and the mutation check so that each check has one entry point and each programming language has its own language module. Terms follow [GLOSSARY.md](../GLOSSARY.md). Decisions are recorded in [ADR 0001](adr/0001-entry-points-language-modules-format-adapters.md) and [ADR 0002](adr/0002-branch-coverage-source-per-language.md).

## Architecture

```
ENTRY POINTS (one per check)
         ┌─────────────────────────┐                 ┌─────────────────────────┐
         │ crap.py <language>      │                 │ mutation.py <language>  │
         │ CRAP check              │                 │ Mutation check          │
         └────────────┬────────────┘                 └────────────┬────────────┘
                      └─────────────────────┬─────────────────────┘
                                            ▼
LANGUAGE MODULES (one file per language)
┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ python        │ │ js / ts       │ │ rust          │ │ swift         │ │ new language  │
│ CRAP:         │ │ CRAP:         │ │ CRAP:         │ │ CRAP:         │ │ CRAP:         │
│  coverage.py  │ │  node / jest  │ │  llvm-cov     │ │  swift test   │ │  ...          │
│ Mutation:     │ │ Mutation:     │ │ Mutation:     │ │ Mutation:     │ │ Mutation:     │
│  mutmut       │ │  Stryker      │ │  cargo-mutants│ │  Muter        │ │  ...          │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        └─────────────────┴─────────────────┼─────────────────┴─────────────────┘
                                            ▼
FORMAT ADAPTERS (shared; one per report format)
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ Coverage formats:  lcov · llvm-json                                                   │
│ Mutation formats:  normalized · stryker · cargo-mutants · muter                       │
└───────────────────────────────────────────┬───────────────────────────────────────────┘
                                            ▼
SHARED CORE (no language-specific code)
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ Runner:            run command · timeout · process cleanup · fresh report             │
│ CRAP scoring:      Lizard complexity + coverage → CRAP ≤ 6, line ≥ 95%, branch ≥ 90%  │
│ Mutation scoring:  count statuses → gate → mutant report                              │
└───────────────────────────────────────────┬───────────────────────────────────────────┘
                                            ▼
                     RESULT: exit 0 pass · 1 review needed · 2 run failure
```

## File layout

All files stay in `skills/workflow/scripts/`, in one flat directory.

| New file | Role | Comes from |
|---|---|---|
| `crap.py` | Entry point of the CRAP check; `collect` subcommand | `crap.py` (argument parsing), `lizard_metrics.py` (`main`) |
| `mutation.py` | Entry point of the mutation check | `mutation.py` (argument parsing) |
| `shared_runner.py` | Runs commands; timeouts; process cleanup on Unix and Windows; fresh reports | `run_report.py`, `windows_job.py` |
| `shared_languages.py` | The explicit list of language names and their modules | New |
| `shared_crap.py` | Lizard join, innermost-function rule, test-code exclusion, CRAP formula, CRAP standard | `crap.py`, `lizard_metrics.py` |
| `shared_mutation.py` | Status counting, gate, mutant details, diff numbering, report rendering | `mutation.py`, `mutation_report.py` |
| `coverage_lcov.py` | Format adapter: LCOV, including checksum validation | `lizard_metrics.py` |
| `coverage_llvm.py` | Format adapter: `llvm-cov export` JSON, line and region coverage | New |
| `report_normalized.py` | Format adapter: normalized report | `mutation.py`, `mutation_report.py` |
| `report_stryker.py` | Format adapter: Stryker report | `mutation.py`, `mutation_report.py` |
| `report_cargo.py` | Format adapter: cargo-mutants `outcomes.json` | `mutation.py`, `mutation_report.py` |
| `report_muter.py` | Format adapter: Muter JSON report | `mutation.py`, `mutation_report.py` |
| `lang_python.py` | Language module; also runs as the mutmut exporter | `mutmut_export.py`, `scripts/self_crap.py` |
| `lang_js.py` | Language module for JS and TS | New |
| `lang_rust.py` | Language module | New |
| `lang_swift.py` | Language module | New |

Round 2 named one `shared_scoring.py`. This plan splits it into `shared_crap.py` and `shared_mutation.py`, so that neither check imports code of the other check.

## Interfaces

### Language registry (`shared_languages.py`)

```python
LANGUAGES = {"python": "lang_python", "js": "lang_js", "ts": "lang_js",
             "rust": "lang_rust", "swift": "lang_swift"}
```

The registry imports a module only when its language is selected. Because it imports lazily, language modules can import shared types from it without a circular import. `ts` maps to the same module as `js`.

### Language module

A language module defines `CRAP`, `MUTATION`, or both.

```python
CRAP = Crap(
    format="lcov",                       # name of the coverage format adapter
    commands=coverage_commands,          # (project, evidence, args) -> list of argv lists
    coverage="coverage.lcov",            # coverage file, relative to the evidence directory
    exclude=None,                        # optional (source, code) -> line ranges of test code
)
MUTATION = Mutation(
    format="cargo-mutants",              # name of the mutation format adapter
    command=mutation_command,            # (project, evidence, args) -> argv
    report=report_path,                  # (project, evidence) -> path where the engine writes its report
)
```

If the report path is outside the evidence directory, the shared core copies the report into the evidence directory after the run. This applies to Stryker.

### Format adapters

- **Coverage format adapter:** `read(path, source_text_by_path)` returns, for each source file, line hits, branch hits, and the branch kind (`branch` or `region`). The adapter validates evidence that is specific to its format, for example LCOV checksums.
- **Mutation format adapter:** defines `ACCEPTED_EXIT_CODES` and `STATUSES` (engine status → mutant status), and `mutants(report, report_path)`. `mutants` validates the report and yields `(engine_status, describe)` for each mutant. `describe()` returns mutant details, and the shared core calls it only for actionable mutants.

Exit codes belong to the format adapter, so config mode needs only the `format` field, as today.

### Command line

```
crap.py <language> <project> <source>... [--timeout-ms N] [-- tool args]
crap.py CONFIG.json
crap.py collect COVERAGE.lcov OUTPUT.json <source>...
mutation.py [--json] <language> <project> [--timeout-ms N] [-- tool args]
mutation.py [--json] CONFIG.json
```

- An argument that is a name in `LANGUAGES` selects a language module. Any other argument is a config path.
- Arguments after `--` go to the tool unchanged.
- A run with a language module writes a new evidence directory and prints its path to stderr.
- `--timeout-ms` defaults to 3,600,000.

## Language modules

| Language | Default CRAP command | Branch source | Default mutation command | Notes |
|---|---|---|---|---|
| python | `coverage run --branch -m pytest`, `coverage combine`, `coverage lcov` | Branch records | `lang_python.py <evidence>/mutation.json` (runs mutmut) | `--` replaces `-m pytest`. |
| js / ts | `node --experimental-strip-types --test --experimental-test-coverage --test-reporter=lcov --test-reporter-destination=<evidence>/coverage.lcov` | Branch records | `./node_modules/.bin/stryker run --testRunner command --reporters json` | Replace with `--` for Jest, Vitest, or c8, or for TS syntax that Node cannot strip. |
| rust | `cargo +nightly llvm-cov --branch --lcov --output-path <evidence>/coverage.lcov` | Branch records | `cargo mutants --output <evidence>` | Without nightly: run failure. Excludes `#[cfg(test)]` modules. |
| swift | `xcrun swift test --enable-code-coverage`, then `xcrun llvm-cov export` (JSON) | Region coverage | `muter run --format json --output <evidence>/mutation.json --skip-update-check` | macOS only. On other platforms: run failure. |

## Steps

Each step ends with its verification. A step is complete only when its verification passes.

0. **Record the baseline.** Run `python -m unittest discover -s tests`, `scripts/self_crap.py`, and `scripts/self_mutation.py`. Keep the evidence paths, CRAP scores, and mutant counts.
   → Verify: all three complete; results recorded.
1. **Shared runner.** Merge `run_report.py` and `windows_job.py` into `shared_runner.py`. `run_report` takes the configuration that the caller already read, so each config is read once. Update the Windows CI step to the new test file name.
   → Verify: unit tests pass, including the Windows job tests.
2. **Mutation format adapters.** Move each engine's status map, exit codes, and report walker into `report_*.py`. Each report is walked once. Move counting, gating, details, and rendering into `shared_mutation.py`. Delete `mutation_report.py`.
   → Verify: unit tests pass; `self_mutation.py` gives the same counts as the baseline.
3. **CRAP split.** Move LCOV parsing into `coverage_lcov.py`, and the Lizard join and gate into `shared_crap.py`. Add `crap.py collect`. Delete `lizard_metrics.py`.
   → Verify: unit tests pass; `self_crap.py` gives the same scores as the baseline.
4. **Registry and command line.** Add `shared_languages.py`; language-or-config argument handling; `--timeout-ms`; `--`; evidence directory.
   → Verify: new tests for argument handling pass; config-mode tests pass unchanged.
5. **Python language module.** Add `lang_python.py` and move `mutmut_export.py` into it. Change both self-checks to call the entry points with `python`, and to build their file lists from `*.py` in the scripts directory and `tests/test_*.py`.
   → Verify: `self_crap.py` and `self_mutation.py` give the same results as the baseline.
6. **Nested functions and test-code exclusion.** In `shared_crap.py`, count each line toward the innermost function that contains it, and apply the language module's exclusion rule.
   → Verify: new tests with nested JS functions pass; all earlier tests pass unchanged.
7. **JS language module.** Add `lang_js.py`.
   → Verify: a scratch JS project and a scratch TS project pass the CRAP check and the mutation check end to end.
8. **Rust language module.** Add `lang_rust.py`, including the nightly check and the `#[cfg(test)]` exclusion.
   → Verify: a scratch crate passes both checks end to end; without nightly, the CRAP check is a run failure with a clear message.
9. **Swift language module.** Add `coverage_llvm.py` and `lang_swift.py`. The result labels branch coverage as region coverage.
   → Verify: a scratch package passes both checks end to end on macOS; a non-macOS platform gives a run failure with a clear message.
10. **Docs.** Reduce `references/quality-tools.md` to the shared contract. Add `references/languages/{python,js,rust,swift}.md`. Delete `references/mutation-engines.md`. Update `quality.md` and `README.md`. The Swift doc states that Muter 16 writes no code snippets, and that Muter creates `<project>_mutated` next to the project, so the isolated copy must be inside its own parent directory.
    → Verify: `python scripts/validation.py` passes.
11. **Final check.**
    → Verify: unit tests, `validation.py`, `self_crap.py`, and `self_mutation.py` all pass. Every new function meets the CRAP standard, and no new mutant survives.

## Unchanged behavior

- Config mode: schema and behavior.
- The CRAP standard.
- The normalized report schema.
- Results: exit 0, 1, and 2 keep their meaning.
- Command output goes to stderr; the result goes to stdout.
- The scripts do not create the isolated copy and do not delete files outside the project.

## Not verified

- Rust branch coverage on generic or `async_trait` code. Published reports say `llvm-cov export` crashes on it with LLVM 21.1.1. A crash is a run failure, never a pass.
- Swift on Linux.
- Any language module on Windows.

## Verified tool versions

The toolchain probes ran on 2026-10-11, on macOS:

- Node 22.21.0
- Swift 6.4 (Xcode)
- rustc nightly 2026-10-10
- cargo-llvm-cov 0.9.1
- cargo-mutants 27.1.0
- Stryker 10.0.0
- Muter 16
- Lizard 1.17.31
