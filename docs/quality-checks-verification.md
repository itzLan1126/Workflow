# Issue #11 mutation exceptions and final verification

The user authorized exceptions on the condition that they are not real logic errors. The exceptions below preserve scoring, status classification, process ownership, or evidence semantics, or alter only presentation. Platform-limited exceptions are explicitly scoped to macOS; they are not assertions of equivalence on other filesystems.

The actual mutation gate remains **exit 1**. No reports, statuses, exclusions, or fixed standards were changed to obtain a pass. Acceptance is complete with the user-authorized exceptions, not a claim that the mutation tool returned exit 0. Exact historical counts are superseded by the verified current scope because splitting functions and adding language modules changes mutation generation.

## Verification

- The unit suite runs 142 tests: 138 pass and four native Windows tests are skipped on macOS.
- Repository validation passes.
- Full CRAP self-check passes; every function has CRAP <= 6.
- The initial JS, TS, Rust, and Swift scratch projects passed both entry points. Review repairs were additionally verified with a real Swift 6.4 release build in a custom scratch directory, combining two independent test bundles; line and region coverage were both 100%.
- Final mutation check: **2,933 killed, 103 survived, 0 uncovered, 0 timeouts, 0 errors**, out of 3,036 assessed. All 103 survivors are listed below.
- Evidence: `/private/tmp/workflow-review-repairs-mutation-3.log`, `/private/tmp/workflow-review-repairs-crap-final.log`, `/private/tmp/workflow-review-repairs-unit-final.log`; original report: `/private/var/folders/97/36py7_j14dv3mhytn6cgbgbw0000gn/T/workflow-evidence-uxvhi4ym/mutation.json`.

Repairs caught by this review: buffered evidence-path output; invalid LLVM region ranges and negative file indexes; unknown coverage kinds. Legacy-locale Unicode read/config tests were added rather than granting encoding exceptions for those behaviors.

Review repairs cover ambiguous shared-line attribution, nested Rust test exclusions, bounded nightly probes, Swift report lookup for the actual test command, and coverage-output environment propagation. Mutation verification exposed two Rust declaration-boundary test gaps and a Windows environment-forwarding test gap; the added regressions kill those variants. In particular, the previously accepted `lang_rust.x_exclude_tests__mutmut_6` is no longer equivalent after semicolon exclusions and is now killed.

The real blocked-probe script test runs in the full unit and CRAP suites. It follows the existing `script_entrypoint` exclusion in the mutation copy because an instrumented standalone subprocess lacks pytest's statistics context; direct nightly-validation tests still exercise the mutated function.

## Per-mutant dispositions

| Mutant ID | Accepted rationale and limit |
| --- | --- |
| `coverage_lcov.x_read_lcov__mutmut_5` | Equivalent codec alias; Python codec names are case-insensitive. |
| `coverage_lcov.x_validate_checksums__mutmut_3` | Equivalent false flag: None and False both disable security-use classification for this non-security checksum. |
| `coverage_lcov.x_validate_checksums__mutmut_10` | Equivalent codec alias; Python codec names are case-insensitive. |
| `coverage_lcov.x_validate_checksums__mutmut_18` | Equivalent codec alias; Python codec names are case-insensitive. |
| `coverage_lcov.x_validate_checksums__mutmut_19` | Equivalent for Base64 MD5: final unpadded character is one of A,Q,g,w, never X; extra stripping character cannot change a valid digest. |
| `crap.x_collect_main__mutmut_8` | Existence is checked by the following source read/analyze or project is_dir check; missing paths still fail closed. Error wording/timing may change. |
| `crap.x_collect_main__mutmut_10` | Existence is checked by the following source read/analyze or project is_dir check; missing paths still fail closed. Error wording/timing may change. |
| `crap.x_collect_main__mutmut_14` | Equivalent codec alias; Python codec names are case-insensitive. |
| `crap.x_collect_main__mutmut_28` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `crap.x_collect_main__mutmut_30` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `crap.x_collect_main__mutmut_36` | Equivalent codec alias; Python codec names are case-insensitive. |
| `crap.x_collect_main__mutmut_40` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `crap.x_collect_main__mutmut_42` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `crap.x_collect_main__mutmut_43` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `crap.x_config_result__mutmut_22` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `crap.x_config_result__mutmut_23` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `crap.x_config_result__mutmut_25` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `crap.x_config_result__mutmut_26` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `crap.x_config_result__mutmut_27` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `crap.x_config_result__mutmut_28` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `crap.x_read_measurements__mutmut_4` | Existence is checked by the following source read/analyze or project is_dir check; missing paths still fail closed. Error wording/timing may change. |
| `crap.x_read_measurements__mutmut_6` | Existence is checked by the following source read/analyze or project is_dir check; missing paths still fail closed. Error wording/timing may change. |
| `crap.x_read_measurements__mutmut_10` | Equivalent codec alias; Python codec names are case-insensitive. |
| `crap.x_language_result__mutmut_24` | Equivalent for generated evidence JSON: json.dumps escapes non-ASCII characters by default, so the written text is ASCII on supported locales. Explicit UTF-8 remains in the implementation. |
| `crap.x_language_result__mutmut_26` | Equivalent for generated evidence JSON: json.dumps escapes non-ASCII characters by default, so the written text is ASCII on supported locales. Explicit UTF-8 remains in the implementation. |
| `crap.x_language_result__mutmut_29` | Platform-limited exception: case-insensitive macOS resolves the same evidence file. Case-sensitive platforms still need verification; the original lowercase code is retained. |
| `crap.x_language_result__mutmut_31` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `crap.x_language_result__mutmut_33` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `crap.x_language_result__mutmut_46` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `crap.x_language_result__mutmut_48` | Equivalent codec alias; Python codec names are case-insensitive. |
| `crap.x_language_result__mutmut_73` | Equivalent for generated evidence JSON: json.dumps escapes non-ASCII characters by default, so the written text is ASCII on supported locales. Explicit UTF-8 remains in the implementation. |
| `crap.x_language_result__mutmut_75` | Equivalent for generated evidence JSON: json.dumps escapes non-ASCII characters by default, so the written text is ASCII on supported locales. Explicit UTF-8 remains in the implementation. |
| `crap.x_language_result__mutmut_78` | Platform-limited exception: case-insensitive macOS resolves the same evidence file. Case-sensitive platforms still need verification; the original lowercase code is retained. |
| `crap.x_language_result__mutmut_80` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `crap.x_language_result__mutmut_82` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `crap.x_language_result__mutmut_83` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `crap.x_language_result__mutmut_85` | Equivalent codec alias; Python codec names are case-insensitive. |
| `crap.x_language_result__mutmut_90` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `crap.x_language_result__mutmut_91` | Equivalent for calculated results: validated bounded integer measurements and exact rational scoring produce finite numeric fields, so allow_nan cannot change this output. |
| `crap.x_language_result__mutmut_93` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `crap.x_language_result__mutmut_94` | Equivalent for calculated results: validated bounded integer measurements and exact rational scoring produce finite numeric fields, so allow_nan cannot change this output. |
| `crap.x_language_result__mutmut_95` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `crap.x_language_result__mutmut_96` | Equivalent for calculated results: validated bounded integer measurements and exact rational scoring produce finite numeric fields, so allow_nan cannot change this output. |
| `lang_python.x_coverage_commands__mutmut_24` | Equivalent codec alias; Python codec names are case-insensitive. |
| `lang_python.x_collect__mutmut_18` | Equivalent codec alias; Python codec names are case-insensitive. |
| `lang_python.x_function_position__mutmut_5` | Equivalent codec alias; Python codec names are case-insensitive. |
| `lang_python.x_add_details__mutmut_34` | Equivalent mutmut API default: get_diff_for_mutant resolves find_mutant(id).path when path is absent, the same lookup already made by the caller. |
| `lang_python.x_add_details__mutmut_36` | Equivalent mutmut API default: get_diff_for_mutant resolves find_mutant(id).path when path is absent, the same lookup already made by the caller. |
| `lang_python.x_main__mutmut_14` | Platform-limited exception: case-insensitive macOS resolves the same file. Case-sensitive platforms still need verification; original lowercase code is retained. |
| `lang_python.x_main__mutmut_43` | Platform-limited exception: case-insensitive macOS resolves the same file. Case-sensitive platforms still need verification; original lowercase code is retained. |
| `lang_python.x_main__mutmut_45` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `lang_python.x_main__mutmut_47` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `lang_python.x_main__mutmut_51` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `lang_python.x_main__mutmut_53` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `lang_python.x_main__mutmut_54` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `lang_python.x_main__mutmut_56` | Equivalent codec alias; Python codec names are case-insensitive. |
| `lang_rust.x_exclude_tests__mutmut_7` | Equivalent scanner state: initial depth offset is added equally to nesting and target; initial pending flag affects target only before start exists and is overwritten at cfg(test). |
| `lang_swift.x_validate_test_command__mutmut_9` | Diagnostic only: the error-message prefix or capitalization changes; the validation predicate, ValueError type, and accepted/rejected inputs remain identical in a six-input comparison. |
| `lang_swift.x_validate_test_command__mutmut_10` | Diagnostic only: the error-message prefix or capitalization changes; the validation predicate, ValueError type, and accepted/rejected inputs remain identical in a six-input comparison. |
| `lang_swift.x_validate_test_command__mutmut_21` | Diagnostic only: the error-message prefix or capitalization changes; the validation predicate, ValueError type, and accepted/rejected inputs remain identical in a six-input comparison. |
| `lang_swift.x_validate_test_command__mutmut_22` | Diagnostic only: the error-message prefix or capitalization changes; the validation predicate, ValueError type, and accepted/rejected inputs remain identical in a six-input comparison. |
| `mutation.x_language_result__mutmut_39` | Platform-limited exception: case-insensitive macOS resolves the same file. Case-sensitive platforms still need verification; original lowercase code is retained. |
| `mutation.x_language_result__mutmut_41` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `mutation.x_language_result__mutmut_43` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `mutation.x_language_result__mutmut_45` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `mutation.x_language_result__mutmut_47` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `mutation.x_language_result__mutmut_48` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `mutation.x_language_result__mutmut_50` | Equivalent codec alias; Python codec names are case-insensitive. |
| `mutation.x_main__mutmut_29` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `mutation.x_main__mutmut_30` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `mutation.x_main__mutmut_32` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `mutation.x_main__mutmut_33` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `mutation.x_main__mutmut_34` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `mutation.x_main__mutmut_35` | Presentation only: JSON whitespace changes; parsed fields and gate are identical. |
| `report_cargo.x_read_cargo_diff__mutmut_6` | JSON writers emit ASCII via default ensure_ascii=True, so encoding omission preserves evidence on supported ASCII-compatible locales. Swift subprocess writes bytes to the descriptor; TextIO encoding is unused. |
| `report_cargo.x_read_cargo_diff__mutmut_7` | JSON writers emit ASCII via default ensure_ascii=True, so encoding omission preserves evidence on supported ASCII-compatible locales. Swift subprocess writes bytes to the descriptor; TextIO encoding is unused. |
| `report_cargo.x_read_cargo_diff__mutmut_18` | Equivalent codec alias; Python codec names are case-insensitive. |
| `report_muter.x_muter_detail__mutmut_24` | Redundant detail file field: adapter describe() supplies the canonical file independently. Extra mutated key is ignored by rendering; status, location, and gate are unchanged. |
| `report_muter.x_muter_detail__mutmut_25` | Redundant detail file field: adapter describe() supplies the canonical file independently. Extra mutated key is ignored by rendering; status, location, and gate are unchanged. |
| `report_muter.x_muter_detail__mutmut_55` | Presentation only: detail-gap wording changes; classification and preserved evidence are unchanged. |
| `report_muter.x_muter_detail__mutmut_56` | Presentation only: detail-gap wording changes; classification and preserved evidence are unchanged. |
| `report_stryker.x_valid_position__mutmut_9` | Equivalent UTF-16 length: encoded byte length is always even, so division and floor division produce the same column bound. |
| `report_stryker.x_source_offset__mutmut_15` | Presentation only: diagnostic wording changes; invalid paths/positions remain rejected. |
| `report_stryker.x_source_offset__mutmut_37` | Presentation only: diagnostic wording changes; invalid paths/positions remain rejected. |
| `report_stryker.x_source_offset__mutmut_46` | Equivalent codec alias; Python codec names are case-insensitive. |
| `report_stryker.x_source_offset__mutmut_52` | Equivalent codec alias; Python codec names are case-insensitive. |
| `report_stryker.x_stryker_detail__mutmut_2` | Redundant detail file field: adapter describe() supplies the canonical file independently. Extra mutated key is ignored by rendering; status, location, and gate are unchanged. |
| `report_stryker.x_stryker_detail__mutmut_3` | Redundant detail file field: adapter describe() supplies the canonical file independently. Extra mutated key is ignored by rendering; status, location, and gate are unchanged. |
| `shared_crap.x_analyze__mutmut_8` | Equivalent codec alias; Python codec names are case-insensitive. |
| `shared_crap.x_collect__mutmut_4` | Existence is checked by the following source read/analyze or project is_dir check; missing paths still fail closed. Error wording/timing may change. |
| `shared_crap.x_collect__mutmut_6` | Existence is checked by the following source read/analyze or project is_dir check; missing paths still fail closed. Error wording/timing may change. |
| `shared_languages.x_arguments__mutmut_16` | Existence is checked by the following source read/analyze or project is_dir check; missing paths still fail closed. Error wording/timing may change. |
| `shared_languages.x_arguments__mutmut_19` | Existence is checked by the following source read/analyze or project is_dir check; missing paths still fail closed. Error wording/timing may change. |
| `shared_languages.x_evidence_directory__mutmut_3` | Presentation only: tempfile prefix changes, while directory freshness and stderr path remain correct. |
| `shared_languages.x_evidence_directory__mutmut_4` | Presentation only: tempfile prefix changes, while directory freshness and stderr path remain correct. |
| `shared_languages.x_evidence_directory__mutmut_5` | Presentation only: tempfile prefix changes, while directory freshness and stderr path remain correct. |
| `shared_mutation.x_render_mutant__mutmut_20` | Equivalent fallback: unstructured XXXX contains no diff hunk, so numbered_diff returns empty and rendering uses the same unavailable-diff message. |
| `shared_runner.x_read_json__mutmut_10` | Equivalent codec alias; Python codec names are case-insensitive. |
| `shared_runner.x_run_command__mutmut_14` | Equivalent subprocess option: shell defaults to False, and None is false; Python uses the same launch mode. |
| `shared_runner.x_run_command__mutmut_22` | Equivalent subprocess option: shell defaults to False, and None is false; Python uses the same launch mode. |
| `shared_runner.x_kernel32__mutmut_7` | Equivalent Windows library name: DLL lookup is case-insensitive. |
| `shared_runner.x_run_windows__mutmut_6` | Equivalent subprocess option: shell defaults to False, and None is false; Python uses the same launch mode. |
| `shared_runner.x_run_windows__mutmut_13` | Equivalent subprocess option: shell defaults to False, and None is false; Python uses the same launch mode. |
