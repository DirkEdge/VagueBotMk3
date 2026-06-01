## 2025-02-23 - Improve Tool Parameters Output UX in Discord Bot
**Learning:** Raw string dictionaries passed to Discord messages are difficult to read and parse, causing a poor developer and user experience, particularly for deep JSON parameter objects.
**Action:** Always format object structures or dictionary parameters passing to Discord tools using `json.dumps(obj, indent=2, ensure_ascii=False)` enclosed within Markdown code blocks (e.g., ` ```json `). Include a basic exception handler with string fallback logic for objects that are strictly not JSON serializable.
