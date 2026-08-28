---
name: improve
description: Independently challenge and strengthen a confirmed implementation design before coding begins.
disable-model-invocation: true
---

# Improve

Adversarially review a confirmed implementation design, validate worthwhile improvements against the real project, and integrate them into the same authoritative file.

## Entry gate

Identify the design from the user's path or current task context. If several files are plausible, ask the user to choose. Continue only with a design whose frontmatter says `status: confirmed`; a draft returns to `/design`.

Read the complete design before judging it: goal, requirements, approach, file changes, testing, optional sections, important technical decisions, trade-offs, and evidence.

## Independent challenge

When subagents are available, dispatch three by default, or the user-requested count from one through five. If fewer are available, use the available count; if none are available, perform the same review yourself.

Give every subagent the same complete problem: independently review the whole confirmed design, inspect the real project where useful, and return only material improvements. Keep agents isolated from one another and avoid fixed review roles.

Each review should challenge correctness, completeness, simplicity, feasibility, ownership, project assumptions, affected modules, flows, contracts, compatibility, error paths, dependencies, testing, and likely rework only where relevant. A valid improvement materially increases reliability, clarity, maintainability, testability, security, performance, compatibility, or simplicity. “No substantive improvement” is valid.

## Decide and validate

1. Inspect only the project areas needed to verify the design and candidate improvements, including relevant uncommitted work. Preserve the user's worktree.
2. Merge duplicate suggestions, separate facts from opinions and assumptions, and validate each candidate. Repetition raises priority for verification; it is not a vote.
3. Prefer removing needless files, layers, abstractions, dependencies, configuration, or speculative flexibility when the confirmed requirements do not need them.
4. Apply ordinary, reversible implementation-level improvements yourself.
5. For a substantive conflict among agents or a major technical decision, present the competing directions, evidence, trade-offs, and recommendation; wait for the user.
6. If a proposal changes confirmed requirements or high-level direction, leave the design unchanged and stop with a request to return to `/discuss`.
7. Use a prototype only when static evidence cannot resolve a material candidate. Isolate it from the user's worktree, base it on current HEAD, include only necessary related uncommitted changes, and remove it completely after validation.

## Integrate and confirm

If no material improvement survives validation, leave the file and `status: confirmed` unchanged, report that result, and finish.

If changes are needed:

1. Change the original design to `status: draft` immediately before the first content edit.
2. Update only the affected parts of that same file. Preserve its style, required sections, final-solution focus, and implementation-ready detail. Do not create a versioned or “improved” copy or record the review transcript.
3. Recheck all confirmed requirements, scope, architecture, real paths, dependencies, compatibility, testing, assumptions, conflicts, experiment cleanup, and worktree integrity.
4. Summarize the substantive changes and ask the user to confirm them. Apply further design-level feedback to the same draft.
5. Set `status: confirmed` only after explicit user confirmation.

Completion requires every material candidate to be resolved or rejected with evidence, every major decision or substantive conflict to be resolved, all experiments to be cleaned up, and the resulting design to be confirmed. Stop; the user decides whether to invoke `/implement`.
