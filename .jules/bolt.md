## 2026-06-04 - Thread-safe state saving
**Learning:** When offloading state serialization and saving to a background thread to prevent blocking the main event loop, passing a `deepcopy` of large dictionaries like `channel_histories` can be expensive and lead to `RuntimeError: dictionary changed size during iteration` if modified concurrently.
**Action:** Always serialize state (e.g., `json.dumps()`) to a string synchronously in the main thread, then offload the actual file I/O to a background thread pool executor (max_workers=1 for FIFO ordering).
