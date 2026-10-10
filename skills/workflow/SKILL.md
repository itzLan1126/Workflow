---
name: workflow
description: Coordinate delegated development through a concise brief, user feedback, independent quality checks, and hands-on acceptance.
disable-model-invocation: true
---

# Workflow

Own the outcome; delegate the work. Discuss the need, hand off a short brief, iterate until the user signs off, then check quality and personally verify the user experience.

Every check _fails closed_: missing, blocked, or user-waived evidence is a gap, never a pass, and is reported as unverified.

## Right-size the run

Match depth to the request before starting, and state the chosen depth so the user can change it:

- **Trivial** (typo, rename, single obvious fix): Skip discovery; confirm a one-paragraph brief inline. Review the diff yourself rather than spawning a quality agent; skip CRAP and mutation testing (say so explicitly). Personally verify the result.
- **Logic-free** (docs, copy, configuration, styling): Full discussion only if direction is unclear. Conventional review only; report CRAP and mutation testing as not applicable.
- **Standard / Complex**: Follow the full 5-step workflow below.

When in doubt, propose a depth and let the user choose. Escalate if the work turns out larger than expected.

## Keep context focused

- **Coordinate directly**: Hold the discussion yourself; you need that context for final acceptance.
- **Delegate work**: Assign implementation and quality checks to subagents so details do not crowd your context.
- **Start clean**: Use fresh subagent contexts when supported. Provide only the role reference, brief, repository location, and authorization boundaries—not the entire chat history.
- **Direction, not recipes**: Give subagents outcomes and responsibility; leave implementation choices to them. Read only the discussion reference yourself; each other role reference goes to the subagent that plays that role.
- **Host fallback**: If your host cannot delegate to subagents, read [references/host-compatibility.md](references/host-compatibility.md) before choosing a fallback.

## Coordinate the work

1. **Discuss and hand off**: read [references/discuss.md](references/discuss.md).
   - Clarify needs, evaluate options, and obtain the user's agreement to the brief and to proceed.
   - If the user has already agreed to the brief and authorized implementation, skip discovery and proceed with that agreed scope.

2. **Implement and iterate**: spawn the implementer with [references/implement.md](references/implement.md) and the brief.
   - Scale execution: use a single implementer for small tasks, or parallel subagents with clear write boundaries for independent slices.
   - Deliver an integrated testable version early, relay user feedback, and reuse relevant implementers for revisions.
   - Keep basic verification (tests, linting, typechecks) active throughout.
   - Update the brief when feedback changes goals or constraints.
   - Done when the user gives explicit _sign-off_ on the behavior; silence and passing tests are not sign-off.

3. **Lock in acceptance**
   - Have the implementer automate the user-tested scenarios as its role reference describes.
   - Record the accepted baseline: a saved patch (including untracked files), or a commit if the user authorizes one. Add the patch path or commit hash, plus the remaining manual scenarios, to the brief's evidence.

4. **Check and repair**: spawn the quality agent with [references/quality.md](references/quality.md), the brief, and a precise change scope.
   - The implementer fixes substantiated issues; the quality agent verifies repairs against the accepted baseline to prevent regressions.
   - If required checks are blocked or repairs repeatedly make no progress, report evidence and wait for the user's decision. Changes to accepted behavior or scope require the user's decision.
   - Done when every required check exits 0 or has a user-decided disposition, and acceptance tests still pass against the baseline.

5. **Personally accept**
   - Run automated acceptance tests, then personally exercise remaining manual scenarios through the real UI, CLI, or API (including error and recovery paths).
   - Delegate fixes and ask the quality agent to recheck affected evidence before repeating affected scenarios.
   - Done when each key user outcome in the brief has actual verification evidence; quality scores and subagent claims are not that evidence. Report outcomes, evidence, and gaps separately.

## Operating guardrails

- Keep agent reports short: outcome, actual checks and results, unresolved issues, and paths to supporting evidence.
- Prevent file write conflicts: one writer per file at a time; sequence overlapping edits or use isolated worktrees.
- Protect the environment: workflow invocation permits local edits and repairs once authorized. Commits, external actions (including pushes, pull requests, publishing, and messages), production access, and destructive operations require explicit user permission. Preserve unrelated work.
