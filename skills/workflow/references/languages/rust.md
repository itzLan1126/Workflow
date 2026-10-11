# Rust

Use `crap.py rust PROJECT SOURCE...` and `mutation.py rust PROJECT` with a fresh isolated copy for mutation checks. Install Lizard, cargo-llvm-cov, cargo-mutants, and the nightly Rust toolchain with its LLVM tools component.

The CRAP check requires nightly to collect real branch records: `cargo +nightly llvm-cov --branch --lcov`. Without nightly it reports a run failure. `#[cfg(test)]` modules are excluded from function scores and aggregate coverage. Arguments after `--` replace the command; nightly is still required.

Mutation runs `cargo mutants --output EVIDENCE`, validates the baseline test, and reads `mutants.out/outcomes.json`. Arguments after `--` replace the command and must preserve that report location. `--timeout-ms` defaults to 3,600,000.

Generic and `async_trait` branch coverage remains unverified. Published reports describe LLVM 21.1.1 export crashes for those cases. A crash produces a run failure.
