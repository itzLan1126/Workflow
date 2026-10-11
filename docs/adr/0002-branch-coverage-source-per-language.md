---
status: accepted
---

# Keep the CRAP standard; use region coverage only where no branch records exist

The CRAP standard requires branch coverage, but not every toolchain produces branch records. Rust produces them only on the nightly compiler (`-Zcoverage-options=branch`; verified with nightly 2026-10-10 and cargo-llvm-cov 0.9.1), so the Rust language module requires nightly and reports a run failure without it. Swift produces no branch records at all (verified on Swift 6.4: `BRF:0`, and no branch data in the `llvm-cov export` JSON), so the Swift language module uses region coverage in place of branch coverage, and the result labels it as region coverage. We chose this over removing the branch requirement for Swift, because that would lower the standard, and over not supporting the CRAP check for Swift at all.

## Consequences

- Region coverage is weaker than branch coverage: for example, it does not count the false path of an `if` without an `else`. A Swift pass is therefore not directly comparable with a pass in another language.
- Rust projects that cannot use nightly cannot pass the CRAP check through the Rust language module. Region coverage on stable Rust was rejected to keep real branch records where a toolchain can produce them.
