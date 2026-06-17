## 2024-06-17 - ThreadPoolExecutor for JSON State Sync
**Learning:** In async Discord applications, writing JSON state iteratively block the main event loop. Copying large state objects via `deepcopy()` is slow. Serializing to JSON first on the main thread and writing the pre-computed string to disk via a single-worker ThreadPoolExecutor provides optimal performance and thread safety.
**Action:** Always pre-serialize dictionaries on the main thread before dispatching to a ThreadPoolExecutor for disk writes to prevent iteration size change exceptions without the cost of deepcopy.
