## 2025-02-28 - Offload synchronous file I/O to avoid blocking asyncio
**Learning:** Using `json.dump` synchronously on the main thread causes latency spikes that block the Discord bot's async event loop.
**Action:** Use a single-worker `concurrent.futures.ThreadPoolExecutor` to offload sequential file I/O operations without relying on external async libraries (like `aiofiles`). Combine this with an atomic file write (`os.replace`) to maintain strict thread safety.
