## 2026-06-01 - [Async Event Loop Unblocking]
**Learning:** Passive event listeners (like `on_message`) doing synchronous disk I/O will severely block the async main event loop for all users.
**Action:** Offload file I/O to a single-worker ThreadPoolExecutor (for FIFO ordering) and use `copy.deepcopy` to prevent 'dictionary changed size' runtime errors.
