## 2023-10-27 - Async Event Loop Blocking I/O
**Learning:** Synchronous file writes inside Discord bot event loops (like save_histories) can stall all concurrent message processing. Offloading state persistence to a single-worker ThreadPoolExecutor avoids this while maintaining sequential writes, but state must be serialized in the main thread to prevent 'RuntimeError: dictionary changed size' from concurrent modifications.
**Action:** Always serialize state objects (e.g., json.dumps) in the main async thread before passing them to background disk-writing threads.
