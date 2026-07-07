## 2024-07-08 - Fast Path Traversal with os.walk pruning
**Learning:** Using `Path.rglob()` and post-filtering results with `.parts` on a large file system is slow (O(N) for all files in ignored directories) because it still visits every file.
**Action:** When filtering out directories during file system traversal, prefer using `os.walk()` and pruning the `dirs` list in-place (e.g., `dirs[:] = [d for d in dirs if d not in excluded]`) to completely skip traversing ignored subtrees, resulting in massive performance gains (e.g. 100x).
