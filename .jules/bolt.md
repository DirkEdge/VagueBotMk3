## 2026-06-30 - Offload Disk I/O to ThreadPoolExecutor
**Learning:** Writing files to disk synchronously inside the asyncio event loop can cause blocking, leading to latency spikes and timeout disconnections.
**Action:** Offload file disk writes to a single-worker `concurrent.futures.ThreadPoolExecutor(max_workers=1)`. Use atomic writes (`os.replace`) in the worker function. Serialize the data string in the main thread before offloading, to avoid "dictionary changed size during iteration" errors.
