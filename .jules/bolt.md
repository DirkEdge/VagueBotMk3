## 2024-10-25 - [Async Atomic Write Pattern]
**Learning:** Offloading synchronous file I/O using a `ThreadPoolExecutor` prevents blocking the main `discord.py` event loop, solving intermittent chat unresponsiveness. Atomic writes (writing to `.tmp` then replacing) prevent chat history corruption. Creating copies of mutable data before submitting to the thread pool is critical to prevent `RuntimeError: dictionary changed size during iteration`.
**Action:** Always use offloaded atomic file operations in background threads for recurring I/O operations in an async Discord application context.
