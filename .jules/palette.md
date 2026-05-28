## 2024-05-28 - Pretty-Print JSON Tool Parameters
**Learning:** Discord bots presenting complex tool execution arguments to users (like Markdown content or nested JSON) become unreadable when formatted as a raw string `str(kwargs)` inline, as newlines break and content wraps aggressively.
**Action:** Always format structured data (like JSON or dicts) using `json.dumps(..., indent=2)` and wrap it in a Discord multi-line code block (```json ... ```) with fallback exception handling.
