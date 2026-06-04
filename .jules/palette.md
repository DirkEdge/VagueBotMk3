## 2024-06-04 - [Improve tool parameter formatting in Discord]
**Learning:** Raw dictionary string representation of tool parameters in Discord messages is hard to read and disrupts the UX, especially when the tool passes nested objects or multiline text (like markdown content).
**Action:** Use `json.dumps(kwargs, indent=2, ensure_ascii=False)` enclosed in Markdown JSON code blocks for tool parameter outputs. Always include a fallback to `str()` for non-serializable objects and properly truncate large strings without breaking the Markdown block.
