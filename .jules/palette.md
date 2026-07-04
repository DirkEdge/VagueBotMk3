## 2024-07-04 - Actionable Error Messages for Hidden Context Bounds
**Learning:** Discord bot users lack visibility into background agent context limits. When the agent fails or loops due to context window exhaustion, generic exceptions leave users confused.
**Action:** Always provide actionable reset commands (like `!clear`) in agent exception messages to help users overcome hidden state boundaries without needing technical debugging.
