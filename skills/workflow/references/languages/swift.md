# Swift

Use `crap.py swift PROJECT SOURCE...` and `mutation.py swift PROJECT`. Both checks require macOS and report a run failure elsewhere. Install Xcode's Swift and LLVM tools, Lizard, and Muter.

The CRAP check runs `xcrun swift test --enable-code-coverage` and copies SwiftPM's LLVM JSON coverage report, which combines all test binaries. Swift has no branch records, so the result explicitly labels the measured proportion as **region coverage** and applies the same 90% requirement. Region coverage does not measure an absent `else` path and is weaker than branch coverage.

Mutation requires a configured `muter.conf.yml` (create it with `muter init`). Muter 16 writes no code snippets, so actionable mutants may have no diff or function name. Muter creates `<project>_mutated` next to the project: put the isolated copy inside its own disposable parent directory. The entry point does not create that copy or delete files outside it. A replacement mutation command receives the absolute expected report path in `WORKFLOW_REPORT_FILE`.

Arguments after `--` replace the test or mutation command. A direct `swift test` or `xcrun swift test` override must include `--enable-code-coverage`. After the test run, the same command with `--show-codecov-path` queries the report location without rerunning tests; this preserves release configurations, custom scratch paths, and all other SwiftPM settings. A wrapper command must write its LLVM JSON report to `WORKFLOW_COVERAGE_FILE`. Reports and evidence are preserved; `--timeout-ms` defaults to 3,600,000. Verified with Swift 6.4 and Muter 16 on macOS.
