## 2024-07-06 - [Offload Blocking I/O to Prevent Asyncio Event Loop Stalls]
**Learning:** In a Python `asyncio` Discord bot environment, performing synchronous disk I/O (like file writes) on the main event loop thread causes the loop to block, increasing latency and risking timeout disconnections.
**Action:** Always offload blocking file operations to a background thread or executor (e.g., `ThreadPoolExecutor`) and serialize state snapshots in the main thread to ensure thread safety without blocking.
