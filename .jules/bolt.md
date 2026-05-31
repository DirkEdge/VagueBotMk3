## 2026-05-30 - Offload Blocking I/O to ThreadPool
**Learning:** Synchronous file I/O operations (like `json.dump` in `save_histories`) block the main Discord `asyncio` event loop on every message, which causes latency spikes and delays in processing other events.
**Action:** Use a single-worker `concurrent.futures.ThreadPoolExecutor` to offload file writing to a background thread while preparing the data in the main thread to avoid race conditions. This guarantees FIFO ordering for sequential state saving without requiring external dependencies like `aiofiles`.
