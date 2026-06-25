## 2024-06-25 - [Async State Serialization]
**Learning:** In a Python async application, using `copy.deepcopy()` to safely pass state to a background thread for synchronous I/O can be surprisingly slow for large dictionaries.
**Action:** Always serialize the dictionary directly to a JSON string (`json.dumps()`) in the main thread and pass the string to the ThreadPoolExecutor. This guarantees thread safety against 'dictionary changed size during iteration' errors and performs much faster than deep copying.

## 2024-06-25 - [Atomic Writes for File I/O]
**Learning:** Writing directly to a state file can corrupt it if the process crashes mid-write.
**Action:** Always write to a `.tmp` file first and use `os.replace()` for atomic file replacements.
