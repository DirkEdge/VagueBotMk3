## 2024-06-14 - Text-Based Discord Bot UX Pattern
**Learning:** In purely text-based conversational interfaces without visual state management, context limits or looping agent errors often manifest as hidden or confusing generic exceptions. Users cannot intuitively 'refresh' the page.
**Action:** Always append an actionable escape-hatch tip (like suggesting `!clear` or `!reset`) directly inside the error message string to empower the user to reset the invisible conversational state. Include clear telemetry where possible (e.g. latency).
