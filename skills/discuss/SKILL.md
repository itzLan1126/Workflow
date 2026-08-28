---
name: discuss
description: Resolve product intent, scope, constraints, and high-level direction before design or implementation.
disable-model-invocation: true
---

# Discuss

Build a shared understanding of **what** to build before deciding exactly **how** to build it. This phase is read-only and ends after the user explicitly confirms the result.

## Decision tree

1. Read the request and investigate available context: repository instructions, relevant code, tests, configuration, documentation, history, and current worktree state.
2. Separate:
   - **Facts** the environment can establish. Investigate these yourself.
   - **Decisions** that change the goal, scope, behavior, constraints, compatibility, high-level direction, or success condition. Leave these to the user.
   - **Assumptions** inferred from context. Keep them labeled until confirmed or verified.
3. Build a dynamic decision tree. Resolve the highest-impact upstream decision first and prune branches made irrelevant by each answer.
4. Ask exactly one material decision question per turn. When useful, offer a small set of real choices, state your recommendation or best guess, and give the evidence and trade-off behind it. Wait for the answer.
5. After each answer, update the facts, decisions, constraints, dependencies, assumptions, and contradictions. Continue only while an unresolved decision could materially change later design or implementation.
6. Summarize the resulting shared understanding and ask the user to confirm it. Incorporate corrections and repeat this confirmation until the user explicitly agrees.

## Boundaries

- Discuss goals, expected behavior, in-scope and out-of-scope work, important constraints, compatibility, success conditions, and high-level technical direction.
- Route file-level changes, symbols, data structures, API details, implementation steps, and concrete test design to `/design`.
- Use the fewest questions that resolve material uncertainty. Translate vague words such as “fast,” “scalable,” or “simple” into a measurable behavior or decision only when they affect the work.
- Keep the workspace unchanged: use read-only inspection and non-mutating checks. If a needed fact requires a state-changing experiment, explain the limitation instead of creating a prototype here.
- Split an oversized request at the scope boundary before exploring its subproblems.

## Completion criterion

Discussion is complete only when the goal, scope, expected behavior, important constraints, key decisions, high-level direction, and any non-blocking unknowns are explicit; no material decision remains unresolved; and the user has confirmed the summary. Stop after confirmation. The user chooses whether to invoke `/design` or another phase.
