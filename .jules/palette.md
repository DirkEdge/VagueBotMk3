## 2024-06-20 - Readable Discord Tool Parameters
**Learning:** Raw string dictionaries in Discord tool prompts are difficult to read and can clutter the interface, but blindly truncating formatted JSON blocks can break Markdown rendering.
**Action:** Format tool parameters with JSON and Markdown blocks, but ensure that truncation logic explicitly appends closing backticks to maintain UI structure.
