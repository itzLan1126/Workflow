---
name: design
description: Turn clear requirements into a confirmed, implementation-ready design grounded in the real project.
disable-model-invocation: true
---

# Design

Resolve implementation-level uncertainty and save a design that another agent can implement without redoing architectural work.

## Entry gate

Read the request and prior decisions. If a missing choice would change the goal, scope, user-visible behavior, compatibility, important constraint, or high-level direction, identify that choice and stop with a request to return to `/discuss`. `/design` may run without a prior discussion when requirements are already clear.

## Build the design

1. Inspect repository instructions, the current branch and HEAD, related uncommitted work, relevant code, callers, types, schemas, configuration, tests, documentation, history, and nearby patterns. Treat verified project state as the source of truth and preserve user work.
2. Separate project facts, ordinary technical decisions, major technical decisions, requirement decisions, and assumptions.
   - Investigate facts.
   - Make low-risk, reversible technical choices from project evidence.
   - For a choice that changes a long-term architecture, core subsystem, important dependency, compatibility contract, data model, or difficult-to-reverse direction, present options, trade-offs, and a recommendation; wait for the user's decision.
   - Send requirement decisions back to `/discuss`.
3. Challenge a confirmed high-level direction only when new project evidence shows a conflict, infeasibility, or serious risk. Present the evidence and wait for the user before changing direction.
4. Use a prototype only when static investigation cannot resolve an uncertainty that would materially change the design. Run the smallest experiment in an isolated worktree, clone, or temporary directory based on the current HEAD; include only relevant uncommitted changes; remove the entire prototype and verify the user's worktree is unchanged before proceeding.
5. Produce the simplest final approach that satisfies the confirmed requirements and fits existing ownership and patterns. Specify architecture and file responsibilities, important data/control flow, contracts, compatibility, error behavior, dependencies, edge cases, and test goals only where relevant. Leave local names and line-by-line code to `/implement`.

## Design document

Read the template that matches the design document language: [templates/design.zh-CN.md](templates/design.zh-CN.md) for Simplified Chinese, or [templates/design.md](templates/design.md) otherwise. Then:

1. Use the repository's existing design directory; otherwise use `docs/designs/`.
2. Create `YYYY-MM-DD-<short-name>.md`. For an existing same-day path, append `-2`, `-3`, and so on. Each independent `/design` creates a new document; never overwrite an older design.
3. Write the draft directly at its final path with `status: draft`.
4. Include `Goal`, `Requirements`, `Implementation Approach`, `File Changes`, and `Testing`. Add optional sections only when they carry real design information; remove empty or `N/A` sections.
5. In `File Changes`, name real investigated paths and each path's responsibility. Mark genuinely new paths as new files.
6. Record the final approach, not the brainstorming transcript or rejected alternatives.

## Confirmation and completion

Validate every path and material fact, requirement coverage, affected ownership, dependencies, compatibility, testing goals, contradictions, and prototype cleanup. Summarize the draft and ask for confirmation. Apply design-level feedback to the same file and ask again; route requirement changes to `/discuss`.

Only after explicit user confirmation, change the document to `status: confirmed`. The phase is complete when the design is implementation-ready, all blocking technical decisions are resolved, all experiments are cleaned up, the worktree is safe, and the file is confirmed. Stop; the user decides whether to invoke `/improve` or `/implement`.
