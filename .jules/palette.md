## 2024-05-24 - Actionable Errors and Latency Feedback
**Learning:** In text-based interfaces like Discord bots, generic error messages without clear recovery paths can leave users stuck, especially when hitting invisible limits like LLM context bounds. Additionally, simple interactions like a `ping` command lack utility if they don't provide system feedback (latency).
**Action:** Always provide actionable suggestions (like resetting state via `!clear`) in error messages. Enhance standard bot commands to include measurable system feedback to improve user confidence and transparency.
