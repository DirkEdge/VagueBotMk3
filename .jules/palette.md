## 2024-05-24 - Actionable Error States

**Learning:** Generic, single-line error messages without context or next steps are poor UX for bot users, who may feel stuck or blame the system. Presenting raw exceptions without code block formatting makes the message unreadable.
**Action:** When bubbling up exceptions or failures, always wrap raw error output in markdown code blocks to preserve readability, and provide a clear, actionable next step (like suggesting where to check logs or to try again).
