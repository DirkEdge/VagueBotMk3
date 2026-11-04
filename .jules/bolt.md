## 2024-05-30 - Optimize Obsidian file traversal with os.walk
**Learning:** Path.rglob() in Python is extremely slow for traversing large, heavily-nested vault directories because it searches all paths and only filters out ignored directories (like .git, .obsidian) after the fact.
**Action:** When performing deep directory traversal, use os.walk() and prune ignored directories in-place (e.g., `dirs[:] = [d for d in dirs if d not in excluded]`) to avoid wasting I/O on large hidden directories.
