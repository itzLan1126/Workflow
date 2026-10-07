---
name: workflow
description: Coordinate delegated development through a concise brief, user feedback, independent quality checks, and hands-on acceptance.
disable-model-invocation: true
---

# Workflow

Own the outcome; delegate the work. Discuss the need, hand off a short brief, iterate until the user is happy, then check quality and personally verify the user experience.

## Keep context focused

Use separate subagents for discussion, implementation, and quality. Start with fresh contexts where supported; pass the relevant role reference, task context, repository location, and authorization boundaries rather than the full conversation. Read the brief and concise results, retrieving code or detailed evidence only when needed. Give agents direction and responsibility, not implementation recipes. Do not load every role reference into the coordinator.

Use an independent discussion context. If the host lacks direct user interaction with subagents or delegation, read [host compatibility](references/host-compatibility.md) before choosing a fallback.

## Coordinate the work

1. **Discuss and hand off.** Delegate with [references/discuss.md](references/discuss.md). Obtain the user's agreement to the brief and to proceed. An already agreed brief is enough; do not restart discovery.
2. **Implement and iterate.** Delegate with [references/implement.md](references/implement.md). Scale implementation to the brief: small work stays with one implementer; large work uses dependency-aware parallel subagents. Let the user try the integrated version, relay feedback, and reuse relevant implementers for revisions. Keep basic verification active. Update the brief when feedback changes goals or constraints. Wait for explicit user satisfaction before commissioning deeper quality checks; silence is not acceptance.
3. **Check and repair.** Delegate review and deterministic checks to an independent quality agent using [references/quality.md](references/quality.md), the current brief, and a precise change scope. Coordinate substantiated fixes with the implementer and have the quality agent verify them. Advance when required checks are complete and material issues are resolved. If required checks are blocked or repairs repeatedly make no progress, report the evidence and wait for the user's decision; any accepted gap remains unverified. Changes to accepted behavior or scope also require the user's decision.
4. **Personally accept.** Exercise the latest brief's key user outcomes through the real UI, CLI, or API, including relevant failure and recovery paths. Delegate fixes and ask the quality agent to recheck affected evidence before repeating affected scenarios. Completion requires actual verification evidence for each key user outcome. Report outcomes, evidence, and gaps separately; unavailable execution or a user-accepted gap does not count as verified completion.

Keep agent reports short: outcome, actual checks and results, unresolved issues, and paths to supporting evidence. Preserve unrelated user work and avoid concurrent writers touching the same files. Workflow invocation does not authorize commits, pushes, publication, or other external actions beyond the user's request.
