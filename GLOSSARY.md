# Deterministic Quality Checks

The CRAP check and the mutation check that the workflow skill's quality agent runs on an accepted change. They produce tool-measured results, not estimates.

## Checks and results

**CRAP check**:
The check that scores each function's change risk from its cyclomatic complexity and test coverage, and gates the scores against the CRAP standard.
_Avoid_: CRAP test, CRAP analysis

**CRAP standard**:
The fixed pass criteria of the CRAP check: every function's CRAP score is at most 6, aggregate line coverage is at least 95%, and aggregate branch coverage is at least 90%. No project can change it.
_Avoid_: threshold, maxCrap

**Mutation check**:
The check that injects faults into changed code and gates on whether the tests detect them.
_Avoid_: mutation run, mutation analysis

**Result**:
The outcome of one check: pass, review needed, or run failure.
_Avoid_: score, verdict

**Run failure**:
A result where the check could not produce trustworthy evidence, for example a missing tool, a crashed command, or an invalid report. It never counts as a pass.
_Avoid_: error (that is a mutant status)

**Evidence**:
The preserved files that support a result: reports, coverage data, and the configuration that produced them.
_Avoid_: artifacts, output

## Coverage

**Coverage kind**:
The type of per-function coverage that a CRAP score uses: line, branch, statement, or basis-path. Line, branch, and statement are proxies for the original basis-path coverage.

**Branch record**:
One measured outcome of a branch in a coverage report, with how often it ran.
_Avoid_: branch hit, branch data

**Region coverage**:
The share of compiler-reported code regions that ran during the tests. It replaces branch coverage only for a language whose compiler produces no branch records, and the result labels it as region coverage.
_Avoid_: block coverage, branch coverage (when meaning regions)

## Mutation

**Mutant**:
One injected fault in the source code.
_Avoid_: mutation (when meaning a single fault)

**Mutation engine**:
An external tool that creates and runs mutants for a language, such as mutmut, Stryker, cargo-mutants, or Muter.
_Avoid_: mutator, mutation tool

**Mutant status**:
The classification of a mutant after the tests ran against it: killed, survived, noCoverage, timeout, unviable, ignored, or error. Only a failing test makes a mutant killed.

**Assessed mutant**:
A mutant whose status is killed, survived, noCoverage, or timeout. Unviable and ignored mutants are not assessed.

**Actionable mutant**:
A mutant whose status is survived, noCoverage, timeout, or error. It requires review.
_Avoid_: surviving mutant (when meaning all four statuses)

**Isolated copy**:
A disposable copy of the project that contains the accepted changes and in which mutation commands run, supplied by the caller or created as an overlay.
_Avoid_: sandbox, checkout, working copy

**Overlay**:
An isolated copy that a mutation check creates itself inside a disposable parent directory and removes after the check, preserving its evidence.

**Reused outcome**:
A non-actionable mutant outcome carried from trustworthy previous evidence for unchanged source and labelled as reused.

**Tool environment**:
A skill-owned location outside the project containing a pinned tool and its dependencies.

**Duplication check**:
The check that identifies pairs of functions with similar normalized structure.

**Duplication standard**:
The fixed criteria of the duplication check: similarity at least 0.8 for functions with at least 4 lines and 20 normalized syntax nodes.

## Structure

**Entry point**:
The single command for one check. There is one each for the CRAP, mutation and duplication checks.
_Avoid_: CLI, wrapper, runner

**Language module**:
Everything that is specific to one programming language: the commands that produce coverage and run the mutation engine, and the report formats those commands write.
_Avoid_: preset, plugin, language adapter

**Config mode**:
Running a check from a configuration file that names the command, working directory, and report, instead of from a language module.
_Avoid_: custom mode, manual mode

**Report format**:
The structure of a file that a tool writes. Coverage formats include LCOV; mutation report formats include the normalized report, Stryker, cargo-mutants, and Muter.
_Avoid_: output format

**Format adapter**:
The reader for one report format. Several language modules can share one format adapter.
_Avoid_: parser, engine adapter

**Normalized report**:
This project's own mutation report format, for mutation engines that have no native format adapter.
_Avoid_: generic report, custom format

**Shared core**:
The language-independent part that runs commands, scores results, and gates them.
_Avoid_: framework, common code
