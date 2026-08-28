---
name: implement
description: Build and verify production code from clear requirements and any confirmed implementation design.
disable-model-invocation: true
---

# Implement

Write the simplest correct production implementation that satisfies the requirement, follows any confirmed design, and fits the real repository.

## Establish the contract

1. Read the request and locate any related design from its explicit path or reliable task context. A `status: confirmed` design is the implementation contract; a draft is context only.
2. `/implement` may proceed without a design for a clear, local change. If requirements are materially ambiguous, return to `/discuss`. If the work needs a new core subsystem, important dependency, public contract, persistence model, difficult-to-reverse architecture, or another major technical decision, return to `/design`.
3. If project evidence makes a confirmed design unsafe or infeasible, stop and report the exact design rule, conflicting fact, and affected work; return to `/design` or `/improve`. Keep low-level implementation choices that preserve the contract autonomous.

## Read before writing

Inspect repository instructions, branch and HEAD, tracked and untracked work, relevant code and callers, ownership boundaries, types, schemas, configuration, tests, documentation, verification commands, history, and nearby patterns. Preserve unrelated user work and merge safely with related edits.

Before adding a helper, service, component, hook, validator, type, wrapper, abstraction, or dependency, search for the existing owner or reusable capability. Extend the responsible module when possible. Use repository conventions first, then local patterns, language or framework conventions, and finally generic preference.

## Implement and verify

1. Define the minimum scope that implements the real behavior rather than a reported example or fixture.
2. For a bug, new behavior, complex logic, or important boundary, prefer a real behavioral test first and confirm the expected failure when practical. Use the lowest test level that proves observable behavior; static source matching is supplementary, not a runtime test.
3. Implement in coherent slices. After each slice, run the narrowest relevant existing check, fix failures caused by the change, and refactor only where the current work needs clearer ownership, less duplication, testability, or type safety.
4. Keep validation at trust boundaries, errors visible and correctly propagated, state and side effects owned, public contracts compatible, and security or performance work proportional to the actual requirement.
5. Reuse the standard library, native platform, installed dependencies, and project helpers before adding code or packages. Add no speculative extension points or one-use abstractions without a real invariant or ownership boundary.
6. Expand verification according to risk: targeted behavior, related tests, then applicable typecheck, lint, build, integration, or broader tests using commands defined by the project. Diagnose each failure before attributing it to the change.
7. Update generated artifacts or directly invalidated documentation only when the repository's normal workflow requires it.

## Final pass

Review the complete diff for requirement and confirmed-design compliance, missed callers, unintended API changes, scope creep, unrelated formatting, temporary code, debug output, hard-coded fixtures, stale generated files, and accidental user-work changes. Remove only artifacts created by this implementation.

Completion requires the requested behavior to be implemented, any confirmed design to be followed, relevant behavioral tests and proportionate checks to pass, change-caused failures to be resolved, no necessary scope to be missing, and no unexplained verification gap or user-work damage to remain.

Report what changed, the main affected areas, every test or check actually run and its result, and any unverified behavior with its residual risk. Do not commit, push, open a pull request, merge, or start `/review` unless the user separately asks. Stop after the implementation report.
