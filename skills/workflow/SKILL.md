---
name: workflow
description: Coordinate delegated development through a concise brief, user feedback, independent quality checks, and hands-on acceptance.
disable-model-invocation: true
---

# Workflow

Own the outcome; delegate the work. Discuss the need, hand off a short brief, iterate until the user is happy, then check quality and personally verify the user experience.

## Right-size the run

Match depth to the request before starting, and state the chosen depth so the user can change it:

- **Trivial** (typo, rename, one obvious fix): skip discovery; confirm a one-paragraph brief inline. Review the change; skip CRAP and mutation testing and say so. Still verify the result yourself.
- **Logic-free** (docs, copy, configuration, styling): full discussion only if the direction is unclear. Conventional review only; report CRAP and mutation testing as not applicable.
- **Everything else**: the full workflow below.

When unsure, propose a depth and let the user choose. Escalate if the work turns out larger than expected.

## Keep context focused

Hold the discussion yourself: it is the context you need for final acceptance. Delegate implementation and quality work to subagents, whose detail would otherwise crowd your context. Start them with fresh contexts where supported; pass the relevant role reference, the brief, repository location, and authorization boundaries rather than the full conversation. Read concise results, retrieving code or detailed evidence only when needed. Give agents direction and responsibility, not implementation recipes. Do not load every role reference at once.

If the host cannot delegate, read [host compatibility](references/host-compatibility.md) before choosing a fallback.

## Coordinate the work

1. **Discuss and hand off.** Follow [references/discuss.md](references/discuss.md). Obtain the user's agreement to the brief and to proceed. An already agreed brief is enough; do not restart discovery.
2. **Implement and iterate.** Delegate with [references/implement.md](references/implement.md). Scale implementation to the brief: small work stays with one implementer; large work uses dependency-aware parallel subagents. Let the user try the integrated version, relay feedback, and reuse relevant implementers for revisions. Keep basic verification active. Update the brief when feedback changes goals or constraints. Wait for explicit user satisfaction before commissioning deeper quality checks; silence is not acceptance.
3. **Lock in acceptance.** When the user accepts, have the implementer turn the scenarios the user tried into automated acceptance or regression tests where practical, and list the scenarios that remain manual. Record the accepted baseline so later changes can be compared with it: a saved patch including new files, or a commit if the user authorizes one. Add both to the brief's evidence.
4. **Check and repair.** Delegate review and deterministic checks to an independent quality agent using [references/quality.md](references/quality.md), the current brief, and a precise change scope. Coordinate substantiated fixes with the implementer and have the quality agent verify them. Repairs must keep the acceptance tests passing; review any repair diff against the accepted baseline for behavior changes. Advance when required checks are complete and material issues are resolved. If required checks are blocked or repairs repeatedly make no progress, report the evidence and wait for the user's decision; any accepted gap remains unverified. Changes to accepted behavior or scope also require the user's decision.
5. **Personally accept.** Run the acceptance tests, then exercise the remaining manual scenarios through the real UI, CLI, or API, including relevant failure and recovery paths. Delegate fixes and ask the quality agent to recheck affected evidence before repeating affected scenarios. Completion requires actual verification evidence for each key user outcome. Report outcomes, evidence, and gaps separately; unavailable execution or a user-accepted gap does not count as verified completion.

Keep agent reports short: outcome, actual checks and results, unresolved issues, and paths to supporting evidence. Preserve unrelated user work and avoid concurrent writers touching the same files. Workflow invocation does not authorize commits, pushes, publication, or other external actions beyond the user's request.
