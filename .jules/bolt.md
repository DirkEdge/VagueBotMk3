## 2024-06-18 - Atomic Background File Saving
**Learning:** In async Python applications, synchronous file I/O blocks the main thread, degrading responsiveness. Modifying state in a background thread can cause `RuntimeError: dictionary changed size during iteration`.
**Action:** Use a single-worker `ThreadPoolExecutor` to offload file writing. Serialize the state to a JSON string in the main thread, then pass that string to the executor. Write to a `.tmp` file and use `os.replace` for atomic operations to prevent corruption.
