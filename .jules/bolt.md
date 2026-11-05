## 2024-03-24 - [Vault Search Performance]
**Learning:** Found an O(N) traversal bottleneck where `Path.rglob()` searches the entire vault, including `.git` and `.obsidian` directories, before filtering.
**Action:** Replaced `Path.rglob()` with `os.walk()` using in-place directory pruning to optimize search times, drastically reducing unnecessary I/O on large vaults.
