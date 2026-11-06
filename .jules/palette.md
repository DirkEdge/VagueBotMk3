## 2024-05-18 - Reply anchors context
**Learning:** In chat interfaces, using direct replies (`message.reply`) instead of channel sends (`message.channel.send`) drastically improves UX by anchoring the bot's response to the specific user message, especially in busy channels.
**Action:** Use `ctx.reply(..., mention_author=False)` or `message.reply(..., mention_author=False)` for bot responses to user commands/messages.
