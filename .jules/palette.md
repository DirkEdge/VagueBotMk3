## 2024-05-14 - Actionable Error States for Context Limits
**Learning:** Discord bots using LLMs often fail opaquely when context limits are reached or state is corrupted. Users don't know how to recover.
**Action:** Always provide an actionable recovery step (like `!clear`) in generic error messages to empower users to unblock themselves without debugging.
