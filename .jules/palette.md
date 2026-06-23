## 2024-06-23 - JSON Markdown for Tool Parameters
**Learning:** Raw string conversion (`str()`) of Python dictionaries for Discord tool parameter prompts creates dense, unreadable text walls, making it difficult for users to evaluate actions in the `InteractiveToolGate` before approving them.
**Action:** Always format dictionary outputs for Discord bot messages using `json.dumps(..., indent=2)` wrapped in Markdown JSON code blocks, while preserving truncation limits to prevent message length errors.
