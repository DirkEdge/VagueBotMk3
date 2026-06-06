## 2024-06-06 - Conversational Bot UI State Recovery
**Learning:** In conversational bot interfaces without visual "refresh" buttons, users can easily get stuck due to hidden context window bounds or agent looping failures.
**Action:** When catching agent or LLM generation errors, the error message itself MUST provide explicit, actionable reset commands (e.g., suggesting `!clear`) so users can manually recover from invisible state issues.
