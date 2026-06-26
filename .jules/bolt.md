## 2023-11-20 - [Offload Synchronous File Writes in Async Loops]
**Learning:** Synchronous file operations like `open()` and `json.dump()` within Discord bot event handlers silently block the main `asyncio` event loop. Attempting to offload a shared mutable state like a dictionary directly to a background thread causes `RuntimeError: dictionary changed size during iteration`.
**Action:** Serialize the state to a string (`json.dumps()`) on the main thread for thread-safety, then offload the blocking string-to-file write onto a single-worker `ThreadPoolExecutor`.
