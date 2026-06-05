## 2026-06-05 - [Optimize chat history saving with atomic async I/O]
**Learning:** Serializing state to a string in the main thread and passing it to a background thread for atomic file I/O is faster and more thread-safe than deep copying for saving chat histories.
**Action:** Use this atomic background execution pattern for similar file I/O operations.
