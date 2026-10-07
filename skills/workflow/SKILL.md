---
name: workflow
description: Coordinate delegated development through a concise brief, user feedback, independent quality checks, and hands-on acceptance.
disable-model-invocation: true
---

# Workflow

Own the outcome; delegate the work. Discuss the need, hand off a short brief, iterate until the user is happy, then check quality and personally verify the user experience.

## Keep context focused

Use separate subagents for discussion, implementation, and quality. Start with fresh contexts where supported; pass the relevant role reference, task context, repository location, and authorization boundaries rather than the full conversation. Read the brief and concise results, retrieving code or detailed evidence only when needed. Give agents direction and responsibility, not implementation recipes. Do not load every role reference into the coordinator.

A discussion agent can talk directly to the user only if the host supports that interaction. Otherwise use a separate discussion chat and its brief for an isolated handoff, or relay questions and answers while explaining that the main chat retains them. Never claim a summary removes existing context. Follow host authorization rules for creating or messaging chats. If delegation is unavailable, disclose it and offer a sequential fallback without claiming independence.

## Coordinate the work

1. **Discuss and hand off.** Delegate with [references/discuss.md](references/discuss.md). Obtain the user's agreement to the brief and to proceed. An already agreed brief is enough; do not restart discovery.
2. **Implement and iterate.** Delegate with [references/implement.md](references/implement.md). Scale implementation to the brief: small work stays with one implementer; large work uses dependency-aware parallel subagents. Let the user try the integrated version, relay feedback, and reuse relevant implementers for revisions. Keep basic verification active. Update the brief when feedback changes goals or constraints. Wait for explicit user satisfaction before commissioning deeper quality checks; silence is not acceptance.
3. **Check and repair.** Dispatch an independent quality agent with [references/quality.md](references/quality.md), the current brief, and a precise change scope. Run conventional code review first and resolve its findings, then execute the bundled CRAP and mutation scripts with the project's tools. Send substantiated findings to the implementer, then recheck affected behavior and the updated change. No findings is a valid result. End when material issues are resolved; report blockers or repeated attempts without progress instead of looping indefinitely. Changes to accepted behavior or scope require the user's decision.
4. **Personally accept.** Exercise representative user scenarios, including relevant failure and recovery paths, through the real UI, CLI, or API against the latest brief and feedback. Delegate fixes, recheck affected quality evidence, and repeat the affected scenarios. Report outcomes, evidence, and remaining gaps. Unavailable execution is unverified, not a pass.

Keep agent reports short: outcome, actual checks and results, unresolved issues, and paths to supporting evidence. Preserve unrelated user work and avoid concurrent writers touching the same files. Workflow invocation does not authorize commits, pushes, publication, or other external actions beyond the user's request.
