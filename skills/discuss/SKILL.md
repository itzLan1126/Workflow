---
name: discuss
description: Resolve product intent, scope, constraints, and high-level direction before design or implementation.
disable-model-invocation: true
---

# Discuss

Build a shared understanding of **what** to build before deciding exactly **how** to build it. This phase is read-only and ends after the user explicitly confirms the result.

## Decision tree

1. Read the request and investigate the available context: repository instructions, relevant code, tests, configuration, documentation, history, and current worktree state.
2. Internally scan the relevant coverage areas: functional scope and behavior, users and roles, data and lifecycle, primary/alternate/error/recovery flows, non-functional requirements, external dependencies, constraints, trade-offs, terminology, and success conditions. Mark each area `clear`, `partial`, `missing`, or `not relevant`. Use this only to find gaps; never turn it into a fixed questionnaire.
3. Classify each unresolved item:
   - Investigate a **fact** when the environment can establish it.
   - Use a **discovery question** only when the user is the source of otherwise unavailable information about their problem, experience, or desired outcome. Ask neutrally without a recommendation, and prefer a recent concrete example over a hypothetical preference.
   - Add a **decision** to the decision tree when it can change the goal, scope, behavior, constraints, compatibility, high-level direction, or success condition.
   - For a fact that the environment cannot establish, determine whether the user must provide it.
   - Keep an **assumption** labeled until it is confirmed or verified.
4. Select the most upstream candidate with the greatest combination of impact and uncertainty. Use downstream rework cost to break close calls. Remove a candidate if its answer would not materially change later design or implementation.
5. For an item with a material effect, ask one specific question. For a discovery question, stay neutral. For a decision, state your recommendation or current best guess and, when useful, offer a small set of real choices with evidence and trade-offs. For ambiguous behavior, use one ordinary example and one relevant alternate, error, or recovery example without designing tests. Wait for the answer before asking another question.
6. After each answer, update the decision tree and remove branches that the answer makes irrelevant. Check the facts, decisions, constraints, dependencies, assumptions, contradictions, and trade-offs.
7. Repeat from step 4 only while an unresolved item could materially change later design or implementation.
8. Otherwise, summarize the shared understanding and ask the user to confirm it. Incorporate corrections and repeat this confirmation until the user explicitly agrees.

## Boundaries

- Discuss goals, expected behavior, in-scope and out-of-scope work, important constraints, compatibility, success conditions, and high-level technical direction.
- Route file-level changes, symbols, data structures, API details, implementation steps, and concrete test design to `/design`.
- Use the fewest questions that resolve material uncertainty.
- Do not ask discovery questions when project evidence or tools can establish the answer.
- Translate vague words such as “fast,” “scalable,” or “simple” into a measurable behavior or decision only when they affect the work.
- Keep the workspace unchanged: use read-only inspection and non-mutating checks. If a needed fact requires a state-changing experiment, explain the limitation instead of creating a prototype here.
- Split an oversized request at the scope boundary before exploring its subproblems.

## Completion criterion

Discussion is complete only when the goal, scope, expected behavior, important constraints, key decisions, high-level direction, and any non-blocking unknowns are explicit; no material decision remains unresolved; and the user has confirmed the summary. Stop after confirmation. The user chooses whether to invoke `/design` or another phase.
