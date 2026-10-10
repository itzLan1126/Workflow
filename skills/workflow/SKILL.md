---
name: workflow
description: Coordinate delegated development through a concise brief, user feedback, independent quality checks, and hands-on acceptance.
disable-model-invocation: true
---

# Workflow

Own the outcome; delegate the work. Discuss the need, hand off a short brief, iterate until the user is happy, then check quality and personally verify the user experience.

## Right-size the run

Match depth to the request before starting, and state the chosen depth so the user can change it:

- **Trivial** (typo, rename, single obvious fix): Skip discovery; confirm a one-paragraph brief inline. Review the change; skip CRAP and mutation testing (say so explicitly). Personally verify the result.
- **Logic-free** (docs, copy, configuration, styling): Full discussion only if direction is unclear. Conventional review only; report CRAP and mutation testing as not applicable.
- **Standard / Complex**: Follow the full 5-step workflow below.

When in doubt, propose a depth and let the user choose. Escalate if the work turns out larger than expected.

## Keep context focused

- **Coordinate directly**: Hold the discussion yourself; you need that context for final acceptance.
- **Delegate work**: Assign implementation and quality checks to subagents so details do not crowd your context.
- **Start clean**: Use fresh subagent contexts when supported. Provide only the role reference, brief, repository location, and authorization boundaries—not the entire chat history.
- **No recipes**: Give subagents direction and responsibility, not rigid implementation recipes. Do not load every role reference at once.
- **Host fallback**: If your host cannot delegate to subagents, read [references/host-compatibility.md](references/host-compatibility.md) before choosing a fallback.

## Coordinate the work

1. **Discuss and hand off** ([references/discuss.md](references/discuss.md))
   - Clarify needs, evaluate options, and obtain the user's agreement to the brief and to proceed.
   - If a valid brief already exists, skip discovery and proceed directly to implementation.

2. **Implement and iterate** ([references/implement.md](references/implement.md))
   - Scale execution: use a single implementer for small tasks, or parallel subagents with clear write boundaries for independent slices.
   - Deliver an integrated testable version early, relay user feedback, and reuse relevant implementers for revisions.
   - Keep basic verification (tests, linting, typechecks) active throughout.
   - Update the brief when feedback changes goals or constraints.
   - **Rule**: Explicit user satisfaction is required before deep quality checks; silence or passing tests do not count as acceptance.

3. **Lock in acceptance**
   - Have the implementer turn user-tested scenarios into automated acceptance or regression tests where practical, and list remaining manual scenarios.
   - Record the accepted baseline: a saved patch (including untracked files) or a commit if authorized by the user. Add both to the brief's evidence.

4. **Check and repair** ([references/quality.md](references/quality.md))
   - Delegate to an independent quality agent using the brief and a precise change scope.
   - Run conventional code review first; resolve material issues before running deterministic tools (CRAP and mutation testing).
   - The implementer fixes substantiated issues; the quality agent verifies repairs against the accepted baseline to prevent regressions.
   - If required checks are blocked or repairs repeatedly make no progress, report evidence and wait for the user's decision; any accepted gap remains unverified. Changes to accepted behavior or scope require the user's decision.

5. **Personally accept**
   - Run automated acceptance tests, then personally exercise remaining manual scenarios through the real UI, CLI, or API (including error and recovery paths).
   - Delegate fixes and ask the quality agent to recheck affected evidence before repeating affected scenarios.
   - Completion requires actual verification evidence for each key user outcome. Report outcomes, evidence, and gaps separately; unavailable execution or a user-accepted gap does not count as verified completion.

## Operating guardrails

- Keep agent reports short: outcome, actual checks and results, unresolved issues, and paths to supporting evidence.
- Prevent file write conflicts: never allow concurrent agents to edit the same files.
- Protect the environment: workflow invocation permits local edits and repairs once authorized, but never authorizes commits, pushes, publication, or destructive actions without explicit user permission. Preserve unrelated work.
