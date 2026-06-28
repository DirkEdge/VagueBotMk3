## 2024-06-28 - [Non-blocking file saving]
**Learning:** Synchronous disk I/O (like json.dump) on the main thread blocks the asyncio event loop, causing bot latency and potential timeout disconnects when multiple messages are processed.
**Action:** Serialize data to a string in the main thread (to avoid dictionary mutation errors) and use a ThreadPoolExecutor for offloading the actual file writing to disk. Also, use atomic writes (.tmp file + os.replace) to avoid data corruption.
