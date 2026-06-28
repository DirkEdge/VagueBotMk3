## 2024-06-28 - Actionable Error Messages and Interaction Feedback
**Learning:** In a Discord-bot interface without a traditional UI, users can easily become trapped in hidden state errors (like exhausted context bounds or agent loops) without clear recovery paths. Additionally, lack of latency feedback makes the bot feel unresponsive.
**Action:** Always provide actionable recovery suggestions (like `!clear` or prompt breakdown) directly in error messages, formatted with clear visual hierarchy (emojis, bolding). Provide concrete latency metrics on heartbeat interactions like `!ping`.
