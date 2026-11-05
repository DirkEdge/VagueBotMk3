## 2024-10-24 - Enhanced Discord Bot Error Handling and Ping Latency Feedback
**Learning:** Users lack visibility into network latency during basic commands like `!ping` and often encounter opaque errors without actionable next steps when context limits are exceeded in AI loops.
**Action:** Provide explicit latency metrics (bot response and API) on ping commands and always suggest state-reset commands (like `!clear`) in generic error messages to empower users to self-recover from hidden state issues.
