## 2026-06-19 - Actionable Error Recovery and Latency Feedback
**Learning:** Discord users lack visibility into the bot's hidden state bounds or network latency, which can cause confusion when an agent silent-fails or seems unresponsive.
**Action:** Always provide actionable recovery hints (like suggesting `!clear` when loops fail) and explicit latency feedback to reassure users that the system is functioning.
