## 2024-06-24 - Actionable Chatbot Error States
**Learning:** Users lack visibility into internal agent state failures (e.g., context windows being exceeded) and often repeatedly try the same query without knowing they need to clear the session.
**Action:** Always provide explicit, actionable recovery steps (like suggesting `!clear`) in generic error messages for stateful text interfaces to improve failure recovery UX.
