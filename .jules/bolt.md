
## 2026-06-13 - Thread-safe state serialization for Async Applications
**Learning:** When offloading state persistence to a background thread using ThreadPoolExecutor in an asynchronous environment (to avoid event loop blocking from file I/O), passing live memory dictionaries directly via standard submission can lead to `RuntimeError: dictionary changed size during iteration` due to concurrent state mutations in the main loop. Copying the state with `copy.deepcopy()` is slow and inefficient.
**Action:** Always serialize the dictionary/state structure to a JSON string in the main thread (synchronously) and pass the resulting string to the background thread for atomic file writing. This guarantees thread safety and provides immediate atomic capture of the current state.
