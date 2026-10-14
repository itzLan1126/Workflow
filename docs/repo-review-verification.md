# Repository review repairs and survivor verification

## Latest review follow-up repairs (2026-10-14)

A two-axis review of `66d7cf9` against `origin/main` found that the shared duplicate-key hook also changed config mode, which `docs/quality-checks-plan.md` lists as unchanged behavior. Config files read by `read_config` and `mutation.py` again keep the last duplicate value; reports, captured approvals and mutmut metadata still reject duplicates through the shared `parse_json`. `mutation_review.py` now imports the statuses, assessed count and exit code from `shared_mutation.py` instead of copying them. A reviewed-gate run failure is reported as `reviewGate.runFailure`. CI now writes the reviewed stdout to `mutation-reviewed.json`, so it is no longer named like the raw report. The MD5 source, approval manifest and pinned hashes are unchanged.

| Local check (Python 3.14.3) | Result |
| --- | --- |
| Full unit suite (`unittest discover`) | 253 tests; 4 existing Windows skips; OK |
| Full-repository CRAP | 191 functions; maximum 6; 0 findings; exit 0 |
| Full-repository mutation | 4,060 generated; 4,059 killed; exactly 1 MD5 survivor |
| Raw strict exit / reviewed gate / process exit | **1 / 0 / 0** |

Both new config-mode tests fail against `66d7cf9` and pass with the repair. Repository validation and `git diff --check` passed. Python 3.10, remote CI and native Windows were not run for this snapshot.

## Codex review repairs at `66d7cf9` (2026-10-14)

GitHub Codex review of `e5a35e364f2a7595619ec414e7efb643548dcf93` completed with two findings, both independently reproduced and repaired. [P1](https://github.com/itzLan1126/Workflow/pull/22#discussion_r4265935611) showed that changing source/diff and matching editable manifest hashes could silently create a new approval. The reviewer now pins the original owner-approved `ef99126aed9617accb3f32190a56822f49684df14bb0dc2366acfa5ad47fea47` source hash and `97ecc3613d91c5e6170e02a10a2269070c5b70fd0f47f967476b29d2cfc5e798` diff hash before comparing the actual copied source and generated diff. Coordinated changes now return reviewed exit 1 with no approval; normal JSON formatting and legitimate reason changes do not expand those bindings.

[P2](https://github.com/itzLan1126/Workflow/pull/22#discussion_r4265935616) showed that duplicate JSON keys use the last value, hiding conflicting evidence. Independent checks also demonstrated a hidden extra survivor and a duplicate native metadata ID changing survived into killed. One shared object-pairs hook now rejects duplicate keys at every nesting depth in original reports, captured approvals and mutmut metadata. Ambiguous raw/approval documents return reviewed exit 2; metadata export fails without emitting a passable report. Original raw and approval bytes remain untouched. Normal objects, including the same key in distinct objects, retain their values.

The existing MD5 production source and approval manifest are byte-identical to `e5a35e3`. No exemption, generator filter, status mapping, CRAP standard, workflow or platform skip was added or relaxed. Positive approval fixtures use the actual approved source and canonical diff independently of the reviewer's constants, and read the original analysis-copy source rather than a mutation trampoline. Red/green tests cover all three coordinated source/diff change combinations, hidden survivors/counts, approval identity/hash keys, nested objects/arrays and duplicate mutmut metadata.

| Final local check | Python 3.14.3 | Python 3.10.18 |
| --- | --- | --- |
| Full unit suite | 251 total; 247 passed; 4 existing native Windows skips; exit 0 | Same |
| Full-repository CRAP | 190 functions; maximum 6; 0 findings; exit 0 | Same |
| Line coverage | 1,457 / 1,469 = 99.1831% | 1,463 / 1,475 = 99.1864% |
| Branch coverage | 519 / 528 = 98.2955% | Same |
| Full-repository mutation | 4,082 generated; 4,081 killed; exactly 1 MD5 survivor | Same IDs/statuses |
| Engine / raw strict exit | **0 / 1** | **0 / 1** |
| Reviewed gate / actual self-check process exit | **0 / 0**, original single approval | Same |
| Other mutant statuses | All zero | Same |

Both fresh mutation copies match all 38 current input hashes: 20 production scripts and 18 test resources. Every complete native ID/status was independently compared with its real per-mutant pytest exit metadata. The duplicate-key hook's four generated mutants, all 332 reviewer mutants and all 24 approval-check mutants are killed; ten actual approval-check diffs exercise the new hash-pin comparison. The seven other MD5-line mutants and the 16 PiB UTF-16 arithmetic mutant remain killed.

Fresh JS/TS/Rust/Swift checks all returned actual exit 0: mutation 2/2, 2/2, 6/6 and 1/1 killed, with complete measured CRAP coverage (Swift: region). Production hashes remained stable. Validation, both dependency checks, all 38 Python AST checks, both workflow YAML files, all 15 Bash-step syntax checks and `git diff --check` passed. Full unit and CRAP checks ran before heavy concurrent checks to avoid the previously documented 100 ms probe startup contention; no deadline or skip changed.

The initial local `codex review --base origin/main` returned exit 0 without finding the two subsequently confirmed flaws; that result does not override their concrete reproductions. A fresh official `codex review --uncommitted` of the eight repaired source/test files returned exit 0 with no confirmed defects. HEAD, the complete repair diff and all 38 input hashes stayed unchanged throughout that review. Its internal read-only sandbox limited some test execution; complete checks above were independently executed in the real workspace. A separate read-only acceptance audit verified the copies, native metadata, fixes, negative controls and real-language reports.

[repo-review-codex-followup.json](repo-review-codex-followup.json) records the review identities, complete source hashes, original/copy evidence bindings, red/green results, before/after counterexamples, fixed authority values and actual final checks. Raw files are preserved in `/private/tmp/workflow-pr22-codex-review-20261014-_kzww2sr/`. This was the pre-commit repair verification snapshot; after pushing, remote CI [run 38500034724](https://github.com/itzLan1126/Workflow/actions/runs/38500034724) passed all four jobs at `66d7cf9`, including native Windows. Raw mutation remains exit 1, and only the separately reviewed gate passes. No merge or release was performed. All sections below describe older snapshots.

## Historical approved MD5 reviewed gate (2026-10-14)

The current uncommitted snapshot remains based on `ea67dabf9b7b7767f8be10fb92ec997045a52540` on `fix/repo-review`. The repository owner approved exactly the MD5 `usedforsecurity=False` to `None` equivalent. The new reviewed gate passes on Python 3.14.3 and 3.10.18; **the original strict mutation result remains exit 1**, with its counts, statuses and bytes preserved. All sections after this update describe historical snapshots.

[repo-review-md5-exclusion.json](repo-review-md5-exclusion.json) binds the exact ID, file, function and repository path to the complete source-file SHA-256 `ef99126aed9617accb3f32190a56822f49684df14bb0dc2366acfa5ad47fea47` and actual generated diff SHA-256 `97ecc3613d91c5e6170e02a10a2269070c5b70fd0f47f967476b29d2cfc5e798`. The production MD5 call remains unchanged for restricted-policy compatibility. This is a reviewed-result exception, without a line exclusion or generator filter. All eight mutations on the digest line remain generated: only False-to-None survives and is approved; the other seven, including True and argument deletion, are killed. Other failures, stale hashes, changed identities, malformed evidence or approval changes during execution block the reviewed gate.

`scripts/mutation_review.py` validates the raw evidence and applies the single approval. `scripts/self_mutation.py` preserves separate raw `mutation-result.json` and overlaid `mutation-reviewed.json` files, with raw exit 1, review exit 0 and the captured manifest SHA clearly labeled. The original bundled strict mutation command retains its behavior. CI uses the existing self-check command and uploads both results, the approval and source snapshot; only the existing step name and three evidence paths changed, with no new jobs or altered exit handling.

The complete scope is **20 production scripts and 18 test resources**, including the new reviewer. Both full mutation checks match all 38 current source/test hashes to their snapshots and actual copied bytes. Every native ID/status was independently compared with its real per-mutant pytest exit metadata. All **326 mutations in the new reviewer are killed**, and the previously repaired 16 PiB UTF-16 arithmetic mutation remains killed.

| Final accepted check | Python 3.14.3 | Python 3.10.18 |
| --- | --- | --- |
| Full unit suite | 245 total; 241 passed; 4 existing native Windows skips; exit 0 | Same, serial full run |
| Full-repository CRAP | 189 functions; 0 findings; maximum 6; exit 0 | Same |
| Line coverage | 1,448 / 1,460 = 99.1781% | 1,454 / 1,466 = 99.1814% |
| Branch coverage | 515 / 524 = 98.2824% | Same |
| Full-repository mutation | 4,069 generated; 4,068 killed; 1 survived | Same IDs and raw statuses |
| Raw strict mutation exit | **1** | **1** |
| Reviewed gate and actual self-check process exit | **0**, exactly one hash-bound approval | Same |
| Mutation noCoverage / timeout / error / ignored / unviable | 0 / 0 / 0 / 0 / 0 | Same |

Eleven controls based on a real raw report confirm that only the exact approved item passes. Source/diff changes, an extra survivor, noCoverage, timeout, unviable, ignored, error and inconsistent counts are blocked. Raw objects remain unchanged. Strict JSON tests also reject NaN, infinity, overflow and invalid UTF-8 without hiding damaged raw output. A case-sensitive read fixture exercises Linux filename semantics on macOS and is applied through `Path.open` on both Python versions; subprocess tests load the helper from the actual isolated module location.

Fresh real JS/TS/Rust/Swift checks all returned exit 0: mutation 2/2, 2/2, 6/6 and 1/1 killed, with complete measured CRAP coverage (Swift retains its region label). Their 20 production-source hashes match this final snapshot. Repository validation, both dependency checks, AST syntax for all 38 Python inputs, both workflow YAML files, all 15 embedded Bash-step syntax checks and `git diff --check` passed. The CRAP standard, inner test selection, raw status mapping and platform skips are unchanged.

One Python 3.10 full-unit attempt under six concurrent heavy checks failed because an existing Rust probe had not started before its 100 ms deadline. Its failure log and exit 1 are retained. The complete suite then passed serially on the exact same source/test snapshot, without changing the timeout or adding a skip. This remains an observed startup timing limitation under heavy parallel load.

Fresh OpenSSL `default_properties=fips=yes` subprocess probes on both Python versions again reject True and accept False/None with the same checksum. This verifies the stated property-policy compatibility, without claiming FIPS module certification or behavior on every Python implementation. The exact CPython source evidence and original proof remain in [repo-review-survivor-remediation.json](repo-review-survivor-remediation.json).

[repo-review-reviewed-gate.json](repo-review-reviewed-gate.json) records the complete input hashes, original and preserved raw-report bindings, neighboring mutation diffs, native metadata checks, both full results, real-language reports, negative controls, policy replay and preserved failed attempt. Raw files and byte-identical archive copies are in `/private/tmp/workflow-reviewed-gate-20261014-jyqqqni9/`. The final code and raw evidence also received an independent read-only review.

No commits, pushes or merges were made. Remote CI for this snapshot and native Windows behavior were not run; both local executions of the same CI mutation command passed the reviewed gate. Earlier raw failure reports are historical evidence and remain unchanged.

## Historical survivor remediation (2026-10-13)

The latest uncommitted repair is based on `ea67dabf9b7b7767f8be10fb92ec997045a52540` on `fix/repo-review`. The sections below this update and the 71-item equivalent ledger are historical measurements of the earlier source snapshot. They are not the current survivor list.

The complete reruns now generate **3,601 mutants: 3,600 killed and 1 survived**, identically on Python 3.14.3 and 3.10.18. All other statuses are zero. The engine completed with exit 0, while the unchanged strict mutation gate returns **exit 1**. Mutation has **not passed**.

Of the previous 71 survivors, 68 redundant sites were removed or consolidated into standard/shared operations. JSON formatting/default arguments, repeated Rust opener scans, duplicate exhaustion checks and absent-diff processing were simplified. Strict UTF-8, universal newlines, surrogate errors, non-finite input rejection, exclusive report ownership and process cleanup remain covered. The two corresponding Rust comment-depth operator mutants now fail tests in both complete runs. A disappearing or reused historical ID is not counted as a kill. The 16 PiB UTF-16 arithmetic regression still kills the exact floating-division mutation.

[repo-review-survivor-remediation.json](repo-review-survivor-remediation.json) records each of the 71 dispositions, old/current source and diff hashes, the new corresponding mutant diffs, all 36 copied-input hashes, native per-ID/pytest-exit verification, complete check results and the remaining proof. The previous audit and equivalence evidence files retain their original source bindings. No CRAP standard, mutation selection, status mapping, workflow or platform skip changed.

The remaining mutation changes `hashlib.md5(..., usedforsecurity=False)` to `usedforsecurity=None`. In the verified CPython [3.10.18 parameter parser](https://github.com/python/cpython/blob/v3.10.18/Modules/clinic/_hashopenssl.c.h#L262) and [3.14.3 parameter parser](https://github.com/python/cpython/blob/v3.14.3/Modules/clinic/_hashopenssl.c.h#L408), both values become the same false C integer and select the same OpenSSL nonsecurity branch. Real subprocesses using `default_properties=fips=yes` reject the default/True call but accept False and None with the same checksum. Removing this parameter would therefore break restricted-policy compatibility. Tests that only assert a literal False, changing its spelling, hiding it outside mutation coverage or suppressing the survivor would not prove a behavioral repair. The flag and raw failure remain. The replayable probe, configuration, outputs and exact official-source excerpts are embedded in the remediation JSON; this property-policy check does not claim FIPS module certification.

| Latest check | Python 3.14.3 | Python 3.10.18 |
| --- | --- | --- |
| Full unit suite | 225 total; 221 passed; 4 existing native Windows skips | Same |
| Full-repository CRAP | 171 functions; 0 findings; maximum 6; exit 0 | Same |
| Line coverage | 1,306 / 1,317 = 99.1648% | 1,312 / 1,323 = 99.1686% |
| Branch coverage | 454 / 462 = 98.2684% | Same |
| Full-repository mutation | 3,601 generated; 3,600 killed; 1 survived; exit 1 | Same IDs and raw statuses |

Fresh real JS/TS/Rust/Swift CRAP and mutation checks all returned exit 0. Their mutation counts were 2/2, 2/2, 6/6 and 1/1 killed; measured line/branch coverage was complete (Swift retains the region label). Their production-source hashes match the final repair snapshot. Repository validation, both dependency checks, syntax for all 36 Python input files, both workflow YAML files, embedded Bash steps and `git diff --check` passed. A read-only review found and repaired one new test's mutmut initialization/order dependency; its selected Unicode tests and entire file passed separately on both Python versions before the final full reruns.

Raw logs, snapshots, reports and independent proof programs are in `/private/tmp/workflow-survivor-repair-20261013-hrvz2h2x/`. These repairs have not been committed, pushed or merged. Native Windows and remote CI were not run for this uncommitted snapshot. The retained exit 1 will still block strict CI/release gates.

## Earlier UTF-16 repair snapshot

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

[repo-review-equivalents.json](repo-review-equivalents.json) contains only the 71 remaining survivors and lists all 22 withdrawn claims. Neither evidence file is an exclusion list or automatic approval mechanism. The earlier counterexamples for omitted UTF-8, bytes temporary directories, directory ownership audit policies, and literal DLL audit policies remain preserved.

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

Repository validation, both dependency checks (`pip check`), Python syntax, workflow YAML, Bash syntax, and `git diff --check` passed. No CRAP standard, status mapping, exclusion, or platform skip changed. The existing `not script_entrypoint and not real_mutmut` inner selection remains; those tests still execute in the full unit and CRAP suites.

## Real external-tool checks and limits

All four language samples were rerun with the actual entry points and engines:

| Language | CRAP | Mutation |
| --- | --- | --- |
| JS / Stryker | Full measured coverage, exit 0 | 2 / 2 killed, exit 0 |
| TS / Stryker | Full measured coverage, exit 0 | 2 / 2 killed, exit 0 |
| Rust / cargo-mutants | Full measured coverage, exit 0 | 6 / 6 killed, exit 0 |
| Swift / Muter | Full measured coverage, exit 0; region measure explicitly labeled | 1 / 1 killed, exit 0 |

The initial JS/TS repeat attempts correctly refused the existing report files. Fresh source/config projects were then used for their successful mutation checks; no stale report was accepted. Swift retained the restricted-host `--disable-sandbox` test setting, with coverage instrumentation enabled. These are small integration samples, not broad compatibility or performance benchmarks.

The five independent initial review skills and subsequent per-survivor reviews remain recorded. This UTF-16 follow-up received an independent read-only review of the pure integer seam, numeric test, unchanged source path, and actual mutant identity mapping.

Final logs, raw reports, source snapshots, narrow checks, and intermediate integration refusals are in `/private/tmp/workflow-utf16-repair-20261013-js3y6zxh/`. Durable evidence and the correction proof program are embedded in the audit JSON. CI and release remain blocked by raw mutation exit 1; this document does not call it a pass.

Native Windows behavior, remote GitHub workflows, and a complete real agent-host workflow were not executed on this macOS host. Windows CI still targets the existing Job Object tests. No commits or pushes were made.
