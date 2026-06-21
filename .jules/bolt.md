## 2026-06-21 - [Asynchronous State Saving]
**Learning:** In a Discord bot event loop, synchronous disk I/O and JSON serialization block the loop. However, offloading directly can cause 'dictionary changed size during iteration' errors.
**Action:** Serialize the state to a JSON string first in the main thread, and only offload the disk write (`os.replace`) to a single-worker `ThreadPoolExecutor`.
