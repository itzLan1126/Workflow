---
name: markdown-outline
description: Create concise outlines from Markdown documents while preserving heading hierarchy and important links. Use when the user asks to outline, condense, or map the structure of a Markdown file.
license: MIT
---

# Markdown Outline

1. Read the complete Markdown input before writing the outline.
2. Preserve the original heading hierarchy.
3. Under each heading, list only the key claims, decisions, or actions.
4. Keep links only when they are necessary to understand or follow the outline.
5. Do not add facts or conclusions that are absent from the source.

Return a Markdown bullet list unless the user requests another format.
