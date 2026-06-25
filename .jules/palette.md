## 2024-06-25 - Actionable Error Messages & Latency Feedback
**Learning:** In Discord bots, raw error messages leave users confused, especially when dealing with hidden context limits. Additionally, basic text replies lack feedback on bot performance.
**Action:** Always provide actionable steps (like suggesting `!clear` or breaking down prompts) in error catch-alls, and include latency metrics in basic health checks (like `!ping`) to give users immediate feedback.
