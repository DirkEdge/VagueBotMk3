import os
import json
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import json5

from qwen_agent.tools.base import BaseTool, register_tool

# Load environment variables
load_dotenv()

VAULT_PATH = os.getenv("VAULT_PATH")
if not VAULT_PATH:
    raise ValueError("VAULT_PATH is not set in environment variables.")

VAULT_ROOT = Path(VAULT_PATH).resolve()

DISCORD_BOT = None  # Set dynamically by the Discord bot on startup

def find_channel(bot, channel_name_or_id: str):
    """Find a Discord channel by ID or case-insensitive name matching."""
    try:
        c_id = int(channel_name_or_id)
        channel = bot.get_channel(c_id)
        if channel:
            return channel
    except ValueError:
        pass
    
    name_clean = channel_name_or_id.strip("# ").lower()
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.name.lower() == name_clean:
                return channel
    return None

def run_async_on_bot(coro):
    """Execute an async coroutine on the Discord bot's main loop and block for the result."""
    global DISCORD_BOT
    if not DISCORD_BOT:
        raise ValueError("Discord bot is not initialized in obsidian_tools.")
    import asyncio
    future = asyncio.run_coroutine_threadsafe(coro, DISCORD_BOT.loop)
    return future.result()


def get_absolute_path(relative_path: str) -> Path:
    """Resolve a relative path against the vault root, ensuring it doesn't traverse outside."""
    target_path = Path(os.path.join(VAULT_ROOT, relative_path.strip("/\\"))).resolve()
    if not target_path.is_relative_to(VAULT_ROOT):
        raise PermissionError(f"Access denied: path {relative_path} is outside the vault.")
    return target_path

def validate_ai_first(content: str, rel_path: str) -> list[str]:
    """Validate that the note content complies with the AI-first vault rules."""
    errors = []
    
    # Skip validation for system metadata, log, and kanban board files
    filename = os.path.basename(rel_path)
    if filename in ("_CLAUDE.md", "log.md", "index.md", "SOUL.md", "CORE_VALUES.md") or rel_path.startswith("Logs/"):
        return errors
    
    # Check if this is a Kanban board
    if "kanban-plugin: board" in content:
        return errors

    # 1. Frontmatter delimiters
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        errors.append("Missing YAML frontmatter block starting at line 1 enclosed by '---' delimiters.")
        return errors
    
    fm_text = fm_match.group(1)
    
    # 2. Key checks
    if "ai-first: true" not in fm_text:
        errors.append("Frontmatter must contain 'ai-first: true'.")
    if "type:" not in fm_text:
        errors.append("Frontmatter must contain a 'type:' field (e.g., type: project, type: daily, type: person).")
    if "date:" not in fm_text:
        errors.append("Frontmatter must contain a 'date:' field in YYYY-MM-DD format.")
    else:
        # Check date format
        date_match = re.search(r"date:\s*([\d\-]+)", fm_text)
        if date_match:
            date_str = date_match.group(1)
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                errors.append(f"Date '{date_str}' is not in YYYY-MM-DD format.")
        else:
            errors.append("Date field must specify a value in YYYY-MM-DD format.")
            
    if "tags:" not in fm_text:
        errors.append("Frontmatter must contain a 'tags:' field.")
        
    # 3. Preamble check
    preamble_match = re.search(r"^## For future Claude\b", content, re.MULTILINE)
    if not preamble_match:
        errors.append("Note must contain a '## For future Claude' preamble header immediately after the frontmatter.")
        
    return errors


@register_tool('vault_read_file')
class VaultReader(BaseTool):
    description = 'Read the contents of a markdown note in the Obsidian vault.'
    parameters = [{
        'name': 'file_path',
        'type': 'string',
        'description': 'The relative path of the file to read inside the vault (e.g., "Projects/Tide.md")',
        'required': True,
    }]

    def call(self, params: str, **kwargs) -> str:
        try:
            args = json5.loads(params)
            file_path = args.get('file_path')
            abs_path = get_absolute_path(file_path)
            
            if not abs_path.exists():
                return json.dumps({"status": "error", "message": f"File '{file_path}' does not exist."}, ensure_ascii=False)
            
            content = abs_path.read_text(encoding="utf-8")
            return json.dumps({"status": "success", "content": content}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


@register_tool('vault_write_file')
class VaultWriter(BaseTool):
    description = 'Write or overwrite a markdown note in the Obsidian vault. Validates that the note follows AI-first vault rules.'
    parameters = [{
        'name': 'file_path',
        'type': 'string',
        'description': 'The relative path of the file to write inside the vault (e.g., "Projects/Tide.md")',
        'required': True,
    }, {
        'name': 'content',
        'type': 'string',
        'description': 'The full markdown content of the note, including YAML frontmatter and future-Claude preamble.',
        'required': True,
    }]

    def call(self, params: str, **kwargs) -> str:
        try:
            args = json5.loads(params)
            file_path = args.get('file_path')
            content = args.get('content')
            
            # Enforce validation
            validation_errors = validate_ai_first(content, file_path)
            if validation_errors:
                return json.dumps({
                    "status": "error",
                    "message": "AI-First Vault Validation Failed:\n" + "\n".join(f"- {err}" for err in validation_errors) + "\nPlease ensure the note content includes: YAML frontmatter with 'ai-first: true', 'type', 'date' (YYYY-MM-DD), 'tags', and a '## For future Claude' preamble at the top."
                }, ensure_ascii=False)
            
            abs_path = get_absolute_path(file_path)
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(content.strip() + "\n", encoding="utf-8")
            
            # Automatically log the update to Logs/YYYY-MM-DD.md if the Logs directory exists
            try:
                today_str = datetime.now().strftime("%Y-%m-%d")
                logs_dir = VAULT_ROOT / "Logs"
                if logs_dir.exists():
                    log_file = logs_dir / f"{today_str}.md"
                    time_str = datetime.now().strftime("%H:%M")
                    log_entry = f"**{time_str}** - write_file | Updated {file_path}\n"
                    if log_file.exists():
                        current_log = log_file.read_text(encoding="utf-8")
                        log_file.write_text(current_log.strip() + "\n" + log_entry, encoding="utf-8")
                    else:
                        log_file.write_text(f"---\ndate: {today_str}\ntype: log\ntags: [log]\nai-first: true\n---\n## For future Claude\nOperation log for {today_str}.\n\n" + log_entry, encoding="utf-8")
            except Exception as log_error:
                print(f"Error logging vault write operation: {log_error}")

            return json.dumps({"status": "success", "message": f"Successfully wrote to '{file_path}'."}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


@register_tool('vault_search')
class VaultSearcher(BaseTool):
    description = 'Search the Obsidian vault for markdown notes containing a specific query or matching a filename.'
    parameters = [{
        'name': 'query',
        'type': 'string',
        'description': 'The query to search for inside note titles or contents.',
        'required': True,
    }]

    def call(self, params: str, **kwargs) -> str:
        try:
            args = json5.loads(params)
            query = args.get('query').lower()
            results = []
            
            # Simple content and title search
            EXCLUDED_DIRS = {".obsidian", ".trash", "_trash", ".git", "Templates"}
            for root, dirs, filenames in os.walk(VAULT_ROOT):
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
                for filename in filenames:
                    if not filename.endswith(".md"):
                        continue
                    md = Path(root) / filename

                    rel = str(md.relative_to(VAULT_ROOT)).replace("\\", "/")
                    content = md.read_text(encoding="utf-8", errors="replace")

                    matched = False
                    excerpt = ""
                    if query in md.stem.lower():
                        matched = True
                        # Grab start of content as excerpt
                        lines = content.split("\n")
                        # skip frontmatter
                        non_fm_lines = [l for l in lines if not l.startswith("---")][:5]
                        excerpt = "Title match: " + " ".join(non_fm_lines)[:100]
                    elif query in content.lower():
                        matched = True
                        # Find a matching line
                        for line in content.split("\n"):
                            if query in line.lower():
                                excerpt = line.strip()[:150]
                                break

                    if matched:
                        results.append({
                            "file_path": rel,
                            "title": md.stem,
                            "excerpt": excerpt
                        })
                        if len(results) >= 20:  # Cap results
                            break
                if len(results) >= 20:  # Cap results out of outer loop too
                    break
            
            return json.dumps({"status": "success", "results": results}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


@register_tool('vault_list_files')
class VaultLister(BaseTool):
    description = 'List all markdown notes in a directory or the entire vault.'
    parameters = [{
        'name': 'directory',
        'type': 'string',
        'description': 'Optional relative directory path to list files from (e.g., "Projects", "Daily"). Defaults to the entire vault.',
        'required': False,
    }]

    def call(self, params: str, **kwargs) -> str:
        try:
            args = json5.loads(params)
            directory = args.get('directory', '').strip("/\\")
            
            target_dir = VAULT_ROOT
            if directory:
                target_dir = get_absolute_path(directory)
                if not target_dir.is_dir():
                    return json.dumps({"status": "error", "message": f"Directory '{directory}' does not exist."}, ensure_ascii=False)
            
            files = []
            EXCLUDED_DIRS = {".obsidian", ".trash", "_trash", ".git", "Templates"}
            for root, dirs, filenames in os.walk(target_dir):
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
                for filename in filenames:
                    if not filename.endswith(".md"):
                        continue
                    md = Path(root) / filename

                    rel = str(md.relative_to(VAULT_ROOT)).replace("\\", "/")
                    files.append(rel)
                
            return json.dumps({"status": "success", "files": files}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


@register_tool('vault_health_check')
class VaultHealthChecker(BaseTool):
    description = 'Run a vault health check to detect duplicates, orphans, stale tasks, missing frontmatter, and broken links.'
    parameters = []

    def call(self, params: str, **kwargs) -> str:
        try:
            # We import and call the vault_health run_health_check function
            # Since vault_health.py is in obsidian-second-brain-main/scripts/vault_health.py,
            # we can run it dynamically.
            import sys
            scripts_path = str(VAULT_ROOT.parent / "obsidian-second-brain-main" / "scripts")
            if scripts_path not in sys.path:
                sys.path.append(scripts_path)
            
            import vault_health
            result = vault_health.run_health_check(VAULT_ROOT)
            return json.dumps({"status": "success", "report": result}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


@register_tool('discord_list_channels')
class DiscordChannelLister(BaseTool):
    description = 'List all text channels available in the Discord server.'
    parameters = []

    def call(self, params: str, **kwargs) -> str:
        try:
            global DISCORD_BOT
            if not DISCORD_BOT:
                return json.dumps({"status": "error", "message": "Discord bot is not initialized."}, ensure_ascii=False)
            
            channels = []
            for guild in DISCORD_BOT.guilds:
                for channel in guild.text_channels:
                    channels.append({
                        "guild_name": guild.name,
                        "channel_name": channel.name,
                        "channel_id": str(channel.id)
                    })
            return json.dumps({"status": "success", "channels": channels}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


@register_tool('discord_read_channel_history')
class DiscordChannelReader(BaseTool):
    description = 'Read recent message history from a specific Discord channel to import conversation or context into the vault.'
    parameters = [{
        'name': 'channel_name',
        'type': 'string',
        'description': 'The name or ID of the channel to read (e.g., "dev-log" or "1234567890").',
        'required': True,
    }, {
        'name': 'limit',
        'type': 'integer',
        'description': 'Optional number of recent messages to fetch (default: 50).',
        'required': False,
    }]

    def call(self, params: str, **kwargs) -> str:
        try:
            global DISCORD_BOT
            if not DISCORD_BOT:
                return json.dumps({"status": "error", "message": "Discord bot is not initialized."}, ensure_ascii=False)
            
            args = json5.loads(params)
            channel_name = args.get('channel_name')
            limit = int(args.get('limit', 50))
            
            channel = find_channel(DISCORD_BOT, channel_name)
            if not channel:
                return json.dumps({"status": "error", "message": f"Channel '{channel_name}' not found."}, ensure_ascii=False)
            
            async def get_history(chan, lim):
                msgs = []
                async for msg in chan.history(limit=lim):
                    msgs.append({
                        "author": msg.author.display_name,
                        "content": msg.content,
                        "timestamp": msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    })
                # Reverse to keep chronological order
                msgs.reverse()
                return msgs
                
            history = run_async_on_bot(get_history(channel, limit))
            return json.dumps({"status": "success", "channel": channel.name, "history": history}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


@register_tool('discord_send_message')
class DiscordMessageSender(BaseTool):
    description = 'Send a message or notification to a specific Discord channel.'
    parameters = [{
        'name': 'channel_name',
        'type': 'string',
        'description': 'The name or ID of the channel to send the message to (e.g., "vault-logs" or "9876543210").',
        'required': True,
    }, {
        'name': 'content',
        'type': 'string',
        'description': 'The message content to send.',
        'required': True,
    }]

    def call(self, params: str, **kwargs) -> str:
        try:
            global DISCORD_BOT
            if not DISCORD_BOT:
                return json.dumps({"status": "error", "message": "Discord bot is not initialized."}, ensure_ascii=False)
            
            args = json5.loads(params)
            channel_name = args.get('channel_name')
            content = args.get('content')
            
            channel = find_channel(DISCORD_BOT, channel_name)
            if not channel:
                return json.dumps({"status": "error", "message": f"Channel '{channel_name}' not found."}, ensure_ascii=False)
            
            async def send_msg(chan, text):
                m = await chan.send(text)
                return m.id
                
            msg_id = run_async_on_bot(send_msg(channel, content))
            return json.dumps({"status": "success", "message_id": str(msg_id)}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

