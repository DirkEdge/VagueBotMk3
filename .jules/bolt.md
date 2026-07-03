## 2026-07-03 - Optimized file saving to disk
**Learning:** In an asynchronous application like Discord bots, performing synchronous file writing tasks on the main thread causes event loop blocking and increases lag/disconnection risks.
**Action:** We implemented a concurrent thread executor to handle offloading file IO while parsing and serializing state using `json.dumps()` securely occurs within the main thread.
