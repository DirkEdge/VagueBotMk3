## 2026-06-09 - Non-blocking atomic chat history persistence
**Learning:** Main-thread JSON serialization with background atomic writes safely prevents main event loop blocking.
**Action:** Use single-worker ThreadPoolExecutor and os.replace() for I/O bound tasks.
