## 2024-05-27 - JSON Formatting for Discord Bot Tool Payloads
**Learning:** Raw Python dictionary representations (`str(kwargs)`) render poorly in Discord embeds and messages, leading to a poor UX for reviewing tool actions (like `vault_write_file`).
**Action:** Use `json.dumps(kwargs, indent=2, ensure_ascii=False)` and enclose the payload in a Discord Markdown block (```json ... ```) when requesting user confirmation.
