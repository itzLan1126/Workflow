---
name: review
description: Perform an independent, read-only, defect-first review of a specific code change.
disable-model-invocation: true
---

# Review

Review the actual change, prove each defect, and report only issues worth fixing. This phase is read-only and performs one review pass.

## Resolve the target

1. Use an explicitly named pull request, commit, range, branch, tag, patch, or working tree.
2. Without an explicit target, use the current working tree when it contains staged, unstaged, or relevant untracked changes. Otherwise determine the branch's actual integration base from its upstream, repository workflow, pull-request context, and merge-base; review the complete branch change.
3. Verify that the target is valid, non-empty, and has a reliable comparison base when needed. If several targets remain plausible, ask the user to choose. An empty or unresolved target blocks the review; it never expands into a repository-wide audit.

## Establish the basis

Read applicable repository instructions and determine the best available requirement from the request, discussion, issue or pull-request text, specifications, commits, tests, documentation, and established behavior. Find a related `status: confirmed` design when reliable; treat drafts only as non-authoritative context.

Review intended behavior against the implementation using this priority: explicit requirement, confirmed specification or design, repository rules, established behavior, then generic engineering expectations. Missing requirements or unavailable material checks are verification gaps, not permission to guess.

## Inspect the complete change

Read the entire diff before concluding. For every changed path, inspect enough surrounding code to understand ownership, contracts, state, errors, and tests. Follow affected callers and consumers, including unchanged ones. When relevant, inspect types, schemas, migrations, configuration, serialization, error and cleanup paths, concurrency, transactions, trust boundaries, fixtures, mocks, and public contracts.

Search for requirement or design violations, correctness defects, regressions, security or performance defects, concrete maintainability regressions, and material testing gaps. These are search prompts, not output quotas.

## Validate candidates

A reported finding must satisfy every condition:

- The reviewed change introduced or materially worsened it.
- It has meaningful correctness, regression, security, performance, maintainability, requirement, or design impact.
- Code evidence or focused non-mutating verification proves the affected scenario and behavior.
- It is discrete, actionable, and likely worth fixing.

Discard style preferences, generic suggestions, speculative future problems, unsupported alarms, unrelated repository debt, intentional required behavior changes, and failures not caused by the change. A missing test is a finding only when changed important behavior has real regression risk and repository practice expects that behavior to be tested.

Use the smallest existing check that can confirm or reject a candidate, then run repository-standard tests, typechecks, lint, builds, or integrations in proportion to change risk. Never install dependencies or modify source, tests, config, lockfiles, branch state, review threads, or user work. Analyze failed tooling before classifying it. Record unavailable material verification and the residual risk.

## Independent agents

Use one agent for an ordinary, narrow, well-understood change. Use three independent agents for high-risk, cross-module, security, authorization, persistence, migration, concurrency, public-contract, large-refactor, or materially uncertain changes. Honor a user-requested count from one through five; use fewer if the environment limits availability, and complete the review yourself if subagents are unavailable.

Every agent reviews the same complete change with the same defect criteria and without fixed roles or access to another agent's result. The main agent merges duplicates, rechecks evidence and causality, resolves conflicts through its own investigation, discards unsupported candidates, and assigns severity. Repetition prioritizes verification; it is not voting.

## Report

Continue after the first defect until the complete target and necessary affected paths are covered. Deduplicate by root cause and order findings by impact:

- `P0`: credible catastrophic security, widespread outage, or unrecoverable data loss.
- `P1`: serious defect on a common or critical path with significant impact.
- `P2`: definite localized defect or material regression.
- `P3`: concrete, low-impact issue still worth correcting.

Format each finding as:

```text
[P1] Imperative title: path/to/file.ext:line

One short paragraph explaining the affected scenario, incorrect behavior, and why this change causes it. Add a brief remedy direction only when it is not obvious.
```

Keep the location to the smallest useful range, preferably changed code. If no candidate meets the bar, write `No findings.`

Final output contains, in order:

1. `Findings`
2. `Overall Assessment` — finding count, requirement/design compliance actually established, and coverage completed.
3. `Verification Gaps` — only material gaps, each paired with residual risk; omit when none exist.

Do not add praise, generic advice, or a separate merge verdict. Confirm that the workspace and branch remain unchanged by the review. Stop after reporting; fixes require a separately invoked `/implement`, and a later `/review` reassesses the entire current change.
