---
status: accepted
---

# Allow pinned tool environments and disposable mutation overlays

Entry points may install missing pinned project-independent tools into skill-owned locations outside the project: one `pip install --target` directory per Python tool and interpreter version, a private npm prefix for Stryker, and a private Cargo install root for cargo-llvm-cov and cargo-mutants. While a check runs, these come first on `PYTHONPATH` and `PATH`; both are restored afterwards. Versions and locations are evidence. Each location has a completion marker and its version is checked on every use. Failed installs, incomplete locations and version mismatches are run failures. System toolchains (Python, Node.js, rustup and nightly Rust with LLVM tools, Xcode/Swift) and Muter remain the user's responsibility, and `--no-install` supports offline and restricted hosts.

Mutation entry points may create an opt-in overlay: a full copy of the project (symlink targets copied as private files, `.git` omitted) inside a disposable parent, so Muter's sibling `<project>_mutated` directory lands inside it. Cleanup removes both while preserving evidence. Caller-supplied isolated copies remain supported. Engine parallelism stays with the engine.

## Considered options

- Installing into the project's interpreter or modifying dependency manifests: rejected because quality checks must not change project dependencies.
- Scoring failed coverage as zero percent: rejected because missing evidence is a run failure, never a measured score.
- A separate virtual environment per Python tool (the original spec's wording): replaced by `pip --target` directories, which are equally skill-owned and outside the project but avoid a second interpreter, per-platform executable paths and an extra site-packages probe.
- Linking unchanged files into the overlay (the original spec's wording): rejected because engines and tests can write through any link into the original project, which the overlay must leave byte-for-byte unchanged. Copying is slower for very large projects.
- Requiring a manually prepared full copy for every run: retained as an option, but insufficient for automatic isolation and cleanup.
