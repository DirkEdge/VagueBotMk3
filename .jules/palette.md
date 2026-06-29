## 2024-06-29 - Actionable Bot Error Messages
**Learning:** Users lack visibility into hidden context bounds or stuck background agents when a standard text bot encounters an error. Standard generic exception messages leave users stranded.
**Action:** When bubbling up exceptions from background LLM worker threads in a chat interface, always include an explicit, actionable suggestion (like reminding them to use a `!clear` state reset command) to help them independently unblock themselves.
