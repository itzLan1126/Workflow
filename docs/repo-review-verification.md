# Repository review repairs and survivor verification

Verified on 2026-10-13 on macOS in the uncommitted `fix/repo-review` worktree, based on `7bcf36d`. No commits or pushes were made. Standards, mutation exclusions, and platform skips were not relaxed.

## UTF-16 correction

The 16 PiB counterexample is now classified as **non-equivalent**, without a host-memory exception. The earlier conditional classification is withdrawn.

The pure integer predicate `valid_utf16_column(encoded_byte_length, column)` now contains the exact column-bound calculation. `valid_position` still checks the line range first and passes the length of the real UTF-16LE encoded line. Source-offset type validation, EOF handling, surrogate decoding, and actual source extraction are unchanged.

The new behavioral test uses twelve fixed input/expected-result cases, including empty lines, zero and out-of-range columns, and counts around the binary64 precision limit. For `encoded_byte_length = 2**54` and `column = 2**53 + 1`, integer arithmetic accepts while the actual floating-division mutation rejects. It also distinguishes the neighboring case `2**54 + 2` / `2**53 + 2`. No 16 PiB allocation, custom `__len__`, fake source string, precision cap, or source-size exclusion is used.

The old `report_stryker.x_valid_position__mutmut_9` ID is no longer generated after extraction. Its absence is **not** counted as a kill. The corresponding newly generated `report_stryker.x_valid_utf16_column__mutmut_5` contains the same `// 2` to `/ 2` arithmetic change. Its exact diff was independently matched to both full analysis copies, and both raw engine reports classify it as **killed**. Direct actual-trampoline checks also produced unittest assertion failures, not timeouts or tool errors.

[repo-review-survivor-audit.json](repo-review-survivor-audit.json) retains the old and new identities, original counterexample, source/test/helper/diff hashes, direct failure logs, proof program, and complete raw-run bindings. Original proof programs and the old Stryker source remain archived explicitly as historical evidence; they must be replayed in an isolated snapshot, not restored into the working tree.

## Disposition of the original 93 survivors

| Classification | Count | Evidence |
| --- | --- | --- |
| Non-equivalent | 22 | The earlier 21 remain killed; the UTF-16 correction's newly generated corresponding mutation is also killed |
| Value-equivalent under the stated current call and dependency contracts | 44 | Survived, with logical proofs and executed checks |
| JSON-semantic presentation equivalence; serialized bytes differ | 27 | Survived, without any claim of byte equivalence |

There is no remaining memory-conditional item. The 71 remaining IDs and diffs match the previously reviewed set after removing the UTF-16 finding. The source-offset function bodies and their two codec-alias diffs are unchanged, even though their containing file now has a new SHA-256. The current ledger binds them to that new file hash.

[repo-review-equivalents.json](repo-review-equivalents.json) contains only the 71 remaining survivors and lists all 22 withdrawn claims. Neither artifact is an exclusion list or automatic approval mechanism. The earlier counterexamples for omitted UTF-8, bytes temporary directories, directory ownership audit policies, and literal DLL audit policies remain preserved.

## Final complete checks

Both Python versions used pinned dependencies and normal repository commands. The fresh mutation copies match all 35 current source/test hashes: 19 production scripts and 16 Python test resources. Raw per-ID statuses and counters were checked independently against the summaries.

| Check | Python 3.14.3 | Python 3.10.18 |
| --- | --- | --- |
| `python -m unittest discover -s tests -v` | 209 total: 205 passed, 4 native Windows skips | Same |
| `python scripts/self_crap.py` | Exit 0; 170 functions; 0 findings; maximum CRAP 6 | Same |
| Line coverage | 1,295 / 1,307 = 99.0819% | 1,301 / 1,313 = 99.0861% |
| Branch coverage | 452 / 462 = 97.8355% | Same |
| `python scripts/self_mutation.py --json` | 3,719 generated: 3,648 killed, 71 survived | Same IDs and statuses |
| Mutation noCoverage / timeout / error / ignored / unviable | 0 / 0 / 0 / 0 / 0 | Same |
| Corresponding UTF-16 floating-division mutant | **Killed**, actual test failure | Same |
| Raw mutation exit | **1** | **1** |

Extraction changes the generated mutant set from 3,715 to 3,719; the difference in total kills is not attributed solely to the original disappearing ID. The generated corresponding arithmetic mutation is verified directly.

Repository validation, both dependency checks (`pip check`), Python syntax, workflow YAML, Bash syntax, and `git diff --check` passed. No threshold, status mapping, exclusion, or platform skip changed. The existing `not script_entrypoint and not real_mutmut` inner selection remains; those tests still execute in the full unit and CRAP suites.

## Real external-tool checks and limits

All four language samples were rerun with the actual entry points and engines:

| Language | CRAP | Mutation |
| --- | --- | --- |
| JS / Stryker | Full measured coverage, exit 0 | 2 / 2 killed, exit 0 |
| TS / Stryker | Full measured coverage, exit 0 | 2 / 2 killed, exit 0 |
| Rust / cargo-mutants | Full measured coverage, exit 0 | 6 / 6 killed, exit 0 |
| Swift / Muter | Full measured coverage, exit 0; region measure explicitly labeled | 1 / 1 killed, exit 0 |

The initial JS/TS repeat attempts correctly refused the existing report files. Fresh source/config projects were then used for their successful mutation runs; no stale report was accepted. Swift retained the restricted-host `--disable-sandbox` test setting, with coverage instrumentation enabled. These are small integration samples, not broad compatibility or performance benchmarks.

The five independent initial review skills and subsequent per-survivor reviews remain recorded. This UTF-16 follow-up received an independent read-only review of the pure integer seam, numeric test, unchanged source path, and actual mutant identity mapping.

Final logs, raw reports, source snapshots, narrow checks, and intermediate integration refusals are in `/private/tmp/workflow-utf16-repair-20261013-js3y6zxh/`. Durable evidence and the correction proof program are embedded in the audit JSON. CI and release remain blocked by raw mutation exit 1; this document does not call it a pass.

Native Windows behavior, remote GitHub workflows, and a complete real agent-host workflow were not executed on this macOS host. Windows CI still targets the existing Job Object tests. No commits or pushes were made.
