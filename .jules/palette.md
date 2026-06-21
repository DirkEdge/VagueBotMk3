## 2026-06-21 - Actionable Error States in Discord Bots
**Learning:** Raw exception strings in Discord bot responses are a UX dead-end. When agent context bounds fail (hidden state), users lack UI indicators to debug, leading to friction.
**Action:** Always pair generic error outputs with explicit, actionable resolution commands (like `!clear`) to guide users out of broken states.
