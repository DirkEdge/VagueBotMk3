
## 2024-05-25 - Expensive Qwen-Agent Instantiation
**Learning:** Instantiating the Qwen-Agent `Assistant` class is a surprisingly expensive operation (~21ms per call) because it processes tool arrays and sets up internal message templates on init. In a high-throughput environment or background scheduling (like `morning_job` or async channel listeners), recreating this repeatedly blocks threads unnecessarily.
**Action:** Always cache long-lived LLM Agent wrappers globally using a channel or session-based dictionary to avoid recreating them per invocation. This brings retrieval time down to ~0.2ms.
