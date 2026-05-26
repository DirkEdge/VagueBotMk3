## 2024-06-25 - Avoid `Path.rglob` for selective tree traversal
**Learning:** `Path.rglob("*.md")` traverses the entire tree unconditionally before results can be filtered. In vault-like or repo-like structures with large ignored directories (e.g., `.git`, `.obsidian`), this causes significant O(N) overhead where N is total files.
**Action:** Use `os.walk` instead and modify the `dirs` list in-place (`dirs[:] = [d for d in dirs if d not in excludes]`) to prune the search tree. This changes the traversal time to depend only on the un-excluded directories, drastically reducing IO load.
