import os
import sys
import json
import asyncio
import datetime
import logging
import time
from dotenv import load_dotenv

import discord
from discord.ext import tasks, commands

# Add Qwen-Agent to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'Qwen-Agent-main'))

from qwen_agent.agents import Assistant  # type: ignore
import obsidian_tools
from obsidian_tools import (
    VaultReader,
    VaultWriter,
    VaultSearcher,
    VaultLister,
    VaultHealthChecker,
    VAULT_ROOT
)


# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('DiscordSecondBrain')

# Load environment variables
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
LOG_CHANNEL_ID_STR = os.getenv("DISCORD_LOG_CHANNEL_ID")
LOG_CHANNEL_ID = int(LOG_CHANNEL_ID_STR) if LOG_CHANNEL_ID_STR else None

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "dashscope")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_BASE = os.getenv("LLM_API_BASE")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-max")
LLM_USE_RAW_API = os.getenv("LLM_USE_RAW_API", "False").lower() in ("true", "1", "yes")

# Validate configuration
if not DISCORD_TOKEN:
    logger.error("DISCORD_TOKEN is missing in the environment variables.")
    sys.exit(1)

# Build Qwen-Agent LLM Config
llm_cfg = {
    'model': LLM_MODEL,
    'generate_cfg': {
        'max_input_tokens': 15000
    }
}
if LLM_API_KEY:
    llm_cfg['api_key'] = LLM_API_KEY
if LLM_API_BASE:
    llm_cfg['base_url'] = LLM_API_BASE
    llm_cfg['model_server'] = LLM_API_BASE  # Qwen-Agent uses 'model_server' for OpenAI compatible API
if LLM_PROVIDER == "openai" or (LLM_API_BASE and "http" in LLM_API_BASE):
    llm_cfg['model_type'] = 'oai'
if LLM_USE_RAW_API:
    llm_cfg['use_raw_api'] = True

logger.info(f"LLM Configuration: provider={LLM_PROVIDER}, model={LLM_MODEL}, base_url={LLM_API_BASE}, use_raw_api={LLM_USE_RAW_API}")

# Define the central system prompt for Qwen-Agent
SYSTEM_MESSAGE = """# STRICT CODER EXECUTION MANDATES

1. Core Identity & Immutable Posture:
You are an expert autonomous software architect operating in a zero-assumption environment. Prioritize deterministic verification, minimal file mutation, and rigorous state management. Never hallucinate context or rely on unsupported parametric memory.

2. The Fetch-First Mandate:
You are strictly PROHIBITED from formulating plans, generating code, or summarizing progress until you have explicitly read (fetched) every core file relevant to the task using vault_read_file.

3. Evidence-Based Reporting & Truth Receipts:
You cannot claim a task is completed, fixed, or added without providing verifiable proof. Summaries of actions MUST cite the specific file name and lines changed. After executing a file write, you MUST fetch the updated file content via vault_read_file and print a Truth Receipt—a direct, verbatim copy of the lines just modified, proving the write was successful.

4. The CHANGELOG Save State & Changelog Receipts:
The CHANGELOG.md file is the official Save State of the project architecture. If vault architecture, state logic, or templates are altered, you MUST update CHANGELOG.md using vault_write_file in the exact same turn and print a Changelog Receipt—a verbatim copy of the exact lines appended to the CHANGELOG.md file.

5. AI-First Vault Writing Rules:
Every note you create or update MUST follow these principles:
- YAML Frontmatter: Enclosed by '---' delimiters containing:
  - date: YYYY-MM-DD
  - type: <note-type> (e.g. project, daily, person, task, devlog)
  - tags: [tag1, tag2] (must include the note type as a tag)
  - ai-first: true
- '## For future Claude' Preamble: A 2-3 sentence summary immediately following the frontmatter.
- Mandatory Wikilinks: Link every person, project, idea, or decision using [[wikilinks]] (e.g., [[Projects/MyProject]], [[People/John Doe]]).
- Source URLs: Preserve verbatim source URLs inline.
- Recency Markers: Inline dates (e.g., as of YYYY-MM) for all external factual claims.
- Confidence levels: Use 'stated | high | medium | speculation' where applicable.
"""

# Initialize Discord Bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
obsidian_tools.DISCORD_BOT = bot  # Set the reference in tools

@bot.command()
async def ping(ctx):
    logger.info("Ping command triggered.")
    await ctx.send("pong")

@bot.command()
async def clear(ctx):
    channel_id = ctx.channel.id
    if channel_id in channel_histories:
        channel_histories[channel_id] = []
        save_histories()
        logger.info(f"Cleared chat history for channel {channel_id}.")
        await ctx.send("🧹 **Chat history cleared successfully.**")
    else:
        await ctx.send("🧹 **No chat history found for this channel.**")

# File path for persistent chat histories
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "chat_history.json")

# Map of channel_id -> list of conversational messages (excluding system messages)
channel_histories = {}

# Active conversation session tracking (channel_id -> (last_user_id, last_timestamp))
active_sessions = {}
SESSION_TIMEOUT_SECONDS = 300  # 5 minutes

def load_histories():
    global channel_histories
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # Convert keys back to integers (JSON keys are always strings)
                channel_histories = {int(k): v for k, v in loaded.items()}
                logger.info(f"Loaded persistent chat history for {len(channel_histories)} channels.")
        except Exception as e:
            logger.error(f"Error loading chat histories: {e}")
            channel_histories = {}
    else:
        channel_histories = {}

def save_histories():
    try:
        # Convert keys to strings for JSON serialization
        to_save = {str(k): v for k, v in channel_histories.items()}
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving chat histories: {e}")

def get_history_with_system_context(channel_id):
    """Rebuild conversation history by prepending the latest vault metadata from _CLAUDE.md."""
    history = list(channel_histories.get(channel_id, []))
    claude_md_path = VAULT_ROOT / "_CLAUDE.md"
    if claude_md_path.exists():
        try:
            claude_content = claude_md_path.read_text(encoding="utf-8")
            system_content = f"Obsidian Vault Configuration (_CLAUDE.md):\n```markdown\n{claude_content}\n```"
            history.insert(0, {'role': 'system', 'content': system_content})
        except Exception as e:
            logger.error(f"Error loading _CLAUDE.md: {e}")
    return history

def sync_agent_run(agent_instance, messages_list, placeholder=None, bot_loop=None) -> str:
    """Synchronous function to consume the agent's runner generator. Runs safely in a background thread."""
    logger.info(f"sync_agent_run: starting execution. Messages payload count: {len(messages_list)}")
    bot_response_content = "I encountered an issue processing your request."
    last_status = ""
    last_update_time = 0.0
    response = []
    
    try:
        for response in agent_instance.run(messages=messages_list):
            if not response:
                continue
                
            curr_msg = response[-1]
            content = curr_msg.get('content', '') if isinstance(curr_msg, dict) else getattr(curr_msg, 'content', '')
            fn_call = curr_msg.get('function_call', None) if isinstance(curr_msg, dict) else getattr(curr_msg, 'function_call', None)
            
            status_text = ""
            is_tool_call = False
            if fn_call:
                is_tool_call = True
                tool_name = ""
                if isinstance(fn_call, dict):
                    tool_name = fn_call.get('name', '')
                else:
                    tool_name = getattr(fn_call, 'name', '')
                status_text = f"⚙️ *Calling vault tool: `{tool_name}`...*"
            elif content:
                # Strip Markdown block formatting from status messages for readability
                snippet = content.strip().replace("*", "").replace("_", "").split('\n')[-1]
                if len(snippet) > 80:
                    snippet = snippet[:80] + "..."
                status_text = f"🧠 *Thinking: {snippet}*"
            else:
                status_text = "🧠 *Parsing vault context...*"
                
            if status_text != last_status:
                now = time.time()
                # Bypass throttle for tool calls or first update, otherwise throttle to 4.0 seconds
                if is_tool_call or (now - last_update_time >= 4.0) or not last_status:
                    logger.info(f"Agent Status (Updating Discord): {status_text}")
                    last_status = status_text
                    last_update_time = now
                    
                    # Update placeholder in Discord thread-safely
                    if placeholder and bot_loop:
                        asyncio.run_coroutine_threadsafe(placeholder.edit(content=status_text), bot_loop)
                else:
                    # Log internally but do not edit Discord placeholder to avoid rate limits
                    logger.debug(f"Agent Status (Throttled): {status_text}")
                    
            bot_response_content = content
            
        # Extract successful file writes to append as a footer
        vault_actions = []
        if response:
            for msg in response:
                role = msg.get('role') if isinstance(msg, dict) else getattr(msg, 'role', '')
                if role == 'function':
                    name = msg.get('name') if isinstance(msg, dict) else getattr(msg, 'name', '')
                    content = msg.get('content') if isinstance(msg, dict) else getattr(msg, 'content', '')
                    try:
                        parsed = json.loads(content)
                        if parsed.get('status') == 'success':
                            msg_text = parsed.get('message', '')
                            if name == 'vault_write_file':
                                if "'" in msg_text:
                                    path_extracted = msg_text.split("'")[1]
                                    vault_actions.append(f"Saved to `{path_extracted}`")
                                else:
                                    vault_actions.append(msg_text)
                    except Exception:
                        pass
        if vault_actions:
            unique_actions = list(dict.fromkeys(vault_actions))
            actions_str = "\n".join(f"- {action}" for action in unique_actions)
            bot_response_content += f"\n\n---\n📁 **Vault Updates:**\n{actions_str}"
            
    except Exception as e:
        logger.error(f"Error in sync_agent_run: {e}")
        bot_response_content = f"Error in agent processing: {e}"
    return bot_response_content



agent_instances = {}

def get_agent_for_channel(channel_id):
    """Instantiate a new Assistant agent with the custom Obsidian and Discord tools registered."""
    # ⚡ Bolt Optimization: Cache the Assistant instance per channel.
    # Qwen Assistant instantiation takes ~21ms per call. Caching it reduces to ~0.2ms,
    # preventing blocking thread overhead across all background jobs and user messages.
    if channel_id in agent_instances:
        return agent_instances[channel_id]

    tools = [
        'vault_read_file',
        'vault_write_file',
        'vault_search',
        'vault_list_files',
        'vault_health_check',
        'discord_list_channels',
        'discord_read_channel_history',
        'discord_send_message'
    ]
    agent = Assistant(
        llm=llm_cfg,
        name='ObsidianBrain',
        description='Obsidian Second Brain Assistant',
        system_message=SYSTEM_MESSAGE,
        function_list=tools
    )
    agent_instances[channel_id] = agent
    return agent


async def post_to_log_channel(message: str):
    """Utility to post status updates to the #vault-logs channel."""
    if LOG_CHANNEL_ID:
        try:
            channel = bot.get_channel(LOG_CHANNEL_ID)
            if not channel:
                channel = await bot.fetch_channel(LOG_CHANNEL_ID)
            if channel:
                await channel.send(message)
        except Exception as e:
            logger.error(f"Failed to post to log channel: {e}")

# Define datetime.time targets for scheduled events in local time
# Current local time zone offset is -07:00 (Pacific Time)
timezone_offset = datetime.timezone(datetime.timedelta(hours=-7))

time_morning = datetime.time(hour=8, minute=0, tzinfo=timezone_offset)
time_nightly = datetime.time(hour=22, minute=0, tzinfo=timezone_offset)
time_weekly = datetime.time(hour=18, minute=0, tzinfo=timezone_offset)   # 6 PM Friday
time_health = datetime.time(hour=21, minute=0, tzinfo=timezone_offset)   # 9 PM Sunday

# Scheduled Agents Loops
@tasks.loop(time=time_morning)
async def morning_job():
    logger.info("Executing Morning Agent job...")
    agent = get_agent_for_channel(0)
    
    prompt = (
        "Morning Agent initialization (8:00 AM). Please check the vault state and:\n"
        "1. Create today's daily note using the Daily Note template if it does not exist.\n"
        "2. Retrieve due-today or overdue tasks from the boards and list them.\n"
        "3. List active projects that have had no activity for over 7 days.\n"
        "Save all modifications in the vault following the AI-first vault rules. "
        "Return a clear, bulleted summary of today's focus, overdue tasks, and stale projects."
    )
    
    messages = [{'role': 'user', 'content': prompt}]
    try:
        result_text = await asyncio.to_thread(sync_agent_run, agent, messages)
        await post_to_log_channel(
            f"☀️ **Morning Vault Sweep Complete** ({datetime.date.today().isoformat()})\n\n{result_text}"
        )
    except Exception as e:
        logger.error(f"Error in morning_job: {e}")
        await post_to_log_channel(f"❌ **Morning Vault Sweep Failed**: {e}")

@tasks.loop(time=time_nightly)
async def nightly_job():
    logger.info("Executing Nightly Agent job...")
    agent = get_agent_for_channel(0)
    
    prompt = (
        "Nightly Agent closing (10:00 PM). Please run the nightly maintenance:\n"
        "1. Read today's daily note.\n"
        "2. Scan today's dev logs and tasks to compile a 3-5 bullet End of Day summary.\n"
        "3. Append this End of Day summary to today's daily note.\n"
        "4. Move completed tasks on kanban boards to the Done column.\n"
        "Ensure all edits adhere strictly to AI-first vault rules. "
        "Return a summary of the accomplishments logged and tasks updated."
    )
    
    messages = [{'role': 'user', 'content': prompt}]
    try:
        result_text = await asyncio.to_thread(sync_agent_run, agent, messages)
        await post_to_log_channel(
            f"🌙 **Nightly Vault Close Complete**\n\n{result_text}"
        )
    except Exception as e:
        logger.error(f"Error in nightly_job: {e}")
        await post_to_log_channel(f"❌ **Nightly Vault Close Failed**: {e}")

@tasks.loop(time=time_weekly)
async def weekly_job():
    # Only run on Fridays (weekday == 4)
    if datetime.datetime.now(timezone_offset).weekday() != 4:
        return
        
    logger.info("Executing Weekly Review Agent job...")
    agent = get_agent_for_channel(0)
    
    prompt = (
        "Weekly Review Agent (Friday 6:00 PM). Please run the weekly review:\n"
        "1. Scan the daily notes and dev logs from the last 7 days.\n"
        "2. Extract completed tasks, decisions, major achievements, and learnings.\n"
        "3. Draft and save a weekly review note at 'Reviews/YYYY-MM-DD — Weekly Review.md'.\n"
        "4. Update the last daily note of the week to link to this review note.\n"
        "Adhere to the AI-first rules (frontmatter, preamble, wikilinks). "
        "Return a high-level summary of the weekly achievements."
    )
    
    messages = [{'role': 'user', 'content': prompt}]
    try:
        result_text = await asyncio.to_thread(sync_agent_run, agent, messages)
        await post_to_log_channel(
            f"📅 **Weekly Review Completed**\n\n{result_text}"
        )
    except Exception as e:
        logger.error(f"Error in weekly_job: {e}")
        await post_to_log_channel(f"❌ **Weekly Review Failed**: {e}")

@tasks.loop(time=time_health)
async def health_job():
    # Only run on Sundays (weekday == 6)
    if datetime.datetime.now(timezone_offset).weekday() != 6:
        return
        
    logger.info("Executing Health Check / Contradiction Sweep job...")
    agent = get_agent_for_channel(0)
    
    prompt = (
        "Vault Health & Contradiction Sweep (Sunday 9:00 PM). Run the audit:\n"
        "1. Execute a vault health check to detect broken links, duplicates, or missing metadata.\n"
        "2. Scan key concept pages and decisions to flag any direct contradictions or superseded facts.\n"
        "3. Format and save a report note at 'Knowledge/Health Report — YYYY-MM-DD.md'.\n"
        "Adhere strictly to AI-first rules. Do not auto-fix. "
        "Return the counts of critical, warning, and info level items."
    )
    
    messages = [{'role': 'user', 'content': prompt}]
    try:
        result_text = await asyncio.to_thread(sync_agent_run, agent, messages)
        await post_to_log_channel(
            f"🔍 **Sunday Health & Contradiction Sweep Complete**\n\n{result_text}"
        )
    except Exception as e:
        logger.error(f"Error in health_job: {e}")
        await post_to_log_channel(f"❌ **Vault Health Sweep Failed**: {e}")



@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    
    # Start background scheduled jobs
    if not morning_job.is_running():
        morning_job.start()
    if not nightly_job.is_running():
        nightly_job.start()
    if not weekly_job.is_running():
        weekly_job.start()
    if not health_job.is_running():
        health_job.start()
        
    logger.info("Scheduled background task loops started.")
    await post_to_log_channel("🤖 **Discord Second Brain Agent is Online and Always On**")

@bot.event
async def on_message(message: discord.Message):
    # Ignore messages sent by the bot itself
    if message.author.id == bot.user.id:
        return
        
    # Ignore commands prefix (like command commands if any)
    if message.content.startswith("!"):
        logger.info(f"Command prefix detected. Processing command: {message.content!r}")
        await bot.process_commands(message)
        return

    # Check routing conditions
    is_dm = message.guild is None
    is_mentioned = bot.user.mentioned_in(message)
    is_log_channel = LOG_CHANNEL_ID and message.channel.id == LOG_CHANNEL_ID

    # Check if this is a reply to the bot
    is_reply_to_bot = False
    if message.reference and message.reference.resolved:
        resolved = message.reference.resolved
        if isinstance(resolved, discord.Message) and resolved.author.id == bot.user.id:
            is_reply_to_bot = True

    # Check if the channel is a dedicated chat channel
    is_chat_channel = False
    if hasattr(message.channel, 'name'):
        channel_name = message.channel.name.lower()
        if channel_name in ('second-brain', 'vague-bot', 'chat-with-ai', 'obsidian-bot'):
            is_chat_channel = True

    # Check active conversation session continuation
    is_session_continuation = False
    now = datetime.datetime.now()
    if message.channel.id in active_sessions:
        last_user_id, last_time = active_sessions[message.channel.id]
        if last_user_id == message.author.id and (now - last_time).total_seconds() < SESSION_TIMEOUT_SECONDS:
            is_session_continuation = True

    should_respond = is_dm or is_mentioned or is_log_channel or is_reply_to_bot or is_chat_channel or is_session_continuation

    logger.info(f"Received message from {message.author} in {message.channel} (ID: {message.channel.id}): {message.content!r} "
                f"[is_dm={is_dm}, is_mentioned={is_mentioned}, is_log_channel={is_log_channel}, "
                f"is_reply_to={is_reply_to_bot}, is_chat_channel={is_chat_channel}, is_session={is_session_continuation}] -> should_respond={should_respond}")

    # Process conversational message in the agentic loop
    channel_id = message.channel.id
    
    # If the bot was mentioned in a server channel, strip the mention to get clean prompt
    user_prompt = message.content
    if is_mentioned:
        # Remove the mention from the content (e.g. <@123456789>)
        mention_str = f"<@{bot.user.id}>"
        mention_nick_str = f"<@!{bot.user.id}>"
        user_prompt = user_prompt.replace(mention_str, "").replace(mention_nick_str, "").strip()
        if not user_prompt:
            user_prompt = "Hello"  # Default prompt if it was just a raw mention

    # --- 1. Passive Listening (For EVERY message) ---
    # Append the formatted message to the channel history so the bot knows what is being discussed
    if channel_id not in channel_histories:
        channel_histories[channel_id] = []
        
    channel_histories[channel_id].append({'role': 'user', 'content': f"{message.author.name}: {user_prompt}"})
    
    # Prune conversational history to the last 30 messages to avoid context window overflow
    if len(channel_histories[channel_id]) > 30:
        channel_histories[channel_id] = channel_histories[channel_id][-30:]
        
    # Save the updated history to disk
    save_histories()

    # --- 2. Active Execution (Only if called) ---
    if not should_respond:
        return

    # Update active session timestamp
    active_sessions[message.channel.id] = (message.author.id, datetime.datetime.now())

    logger.info(f"Acknowledge message from {message.author}: sending placeholder in channel {channel_id}")
    # 1. Immediate Acknowledge: Send a tentative placeholder message
    try:
        placeholder = await message.channel.send("🧠 *Thinking... parsing your vault context...*")
    except Exception as e:
        logger.error(f"Failed to send placeholder message: {e}")
        return
    
    # 2. Push processing to background task to keep WebSocket connection active
    logger.info(f"Dispatching run_agent_loop as background task for channel {channel_id}")
    asyncio.create_task(run_agent_loop(message, placeholder, channel_id))

async def run_agent_loop(message: discord.Message, placeholder: discord.Message, channel_id: int):
    # Use context manager to trigger typing across both DMs and Guild text channels safely
    async with message.channel.typing():
        try:
            # Rebuild history list by prepending the latest vault system context
            history_to_send = get_history_with_system_context(channel_id)
            
            # Instantiate agent
            agent = get_agent_for_channel(channel_id)
            
            # Run Qwen-Agent generator in a separate worker thread to prevent event loop deadlocks with our async channel tools
            start_time = asyncio.get_event_loop().time()
            logger.info(f"run_agent_loop: starting agent for channel {channel_id} with history size {len(history_to_send)}")
            bot_response_content = await asyncio.to_thread(sync_agent_run, agent, history_to_send, placeholder, bot.loop)
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.info(f"run_agent_loop: finished agent for channel {channel_id} in {elapsed:.3f}s. Response size: {len(bot_response_content)}")
                
            # Update history with bot response
            channel_histories[channel_id].append({'role': 'assistant', 'content': bot_response_content})
            
            # Prune again (after adding assistant response) and save
            if len(channel_histories[channel_id]) > 30:
                channel_histories[channel_id] = channel_histories[channel_id][-30:]
            save_histories()
            
            # 3. Post synthesized response back to channel
            # If response is too long for Discord (2000 character limit), split it
            if len(bot_response_content) > 1900:
                chunks = [bot_response_content[i:i+1900] for i in range(0, len(bot_response_content), 1900)]
                await placeholder.edit(content=chunks[0])
                for chunk in chunks[1:]:
                    await message.channel.send(chunk)
            else:
                await placeholder.edit(content=bot_response_content)
                
        except Exception as e:
            logger.error(f"Error running agent loop: {e}")
            await placeholder.edit(content=f"❌ **An error occurred**: {e}")


if __name__ == "__main__":
    load_histories()
    bot.run(DISCORD_TOKEN)
