---
name: discuss
description: Resolve product intent, scope, constraints, and high-level direction before design or implementation.
disable-model-invocation: true
---

# Discuss

Build a shared understanding of **what** to build before deciding exactly **how** to build it. This phase is read-only and ends after the user explicitly confirms the result.

## Decision tree

1. Read the request and investigate the available context: repository instructions, relevant code, tests, configuration, documentation, history, and current worktree state.
2. Classify each unresolved item:
   - Investigate a **fact** when the environment can establish it.
   - Add a **decision** to the decision tree when it can change the goal, scope, behavior, constraints, compatibility, high-level direction, or success condition.
   - For a fact that the environment cannot establish, determine whether the user must provide it.
   - Keep an **assumption** labeled until it is confirmed or verified.
3. Select the most upstream unresolved item. Determine what its answer can change. Remove the item if its answer has no material effect on later design or implementation.
4. For an item with a material effect, ask one specific question. State your recommendation or current best guess. When useful, offer a small set of real choices and explain the evidence and trade-offs. Wait for the answer before asking another question.
5. After each answer, update the decision tree and remove branches that the answer makes irrelevant. Check the facts, decisions, constraints, dependencies, assumptions, contradictions, and trade-offs.
6. Repeat from step 3 only while an unresolved item could materially change later design or implementation.
7. Otherwise, summarize the shared understanding and ask the user to confirm it. Incorporate corrections and repeat this confirmation until the user explicitly agrees.

## Boundaries

- Discuss goals, expected behavior, in-scope and out-of-scope work, important constraints, compatibility, success conditions, and high-level technical direction.
- Route file-level changes, symbols, data structures, API details, implementation steps, and concrete test design to `/design`.
- Use the fewest questions that resolve material uncertainty.
- Translate vague words such as “fast,” “scalable,” or “simple” into a measurable behavior or decision only when they affect the work.
- Keep the workspace unchanged: use read-only inspection and non-mutating checks. If a needed fact requires a state-changing experiment, explain the limitation instead of creating a prototype here.
- Split an oversized request at the scope boundary before exploring its subproblems.

## Completion criterion

Discussion is complete only when the goal, scope, expected behavior, important constraints, key decisions, high-level direction, and any non-blocking unknowns are explicit; no material decision remains unresolved; and the user has confirmed the summary. Stop after confirmation. The user chooses whether to invoke `/design` or another phase.
