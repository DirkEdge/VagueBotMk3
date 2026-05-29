## 2024-05-30 - [Asynchronous State Saving in Discord Bot]
**Learning:** Synchronous file writes (like `json.dump`) inside the Discord bot event loop can block the thread, leading to increased latency and potential websocket drops during concurrent usage.
**Action:** Use a single-worker `ThreadPoolExecutor` to offload disk writes to a background thread. This maintains a lean deployment environment without adding external dependencies like `aiofiles`, while guaranteeing sequential, thread-safe file writes for state saving.
