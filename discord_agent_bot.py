import os
import sys
import asyncio
import datetime
import logging
from dotenv import load_dotenv

import discord
from discord.ext import tasks, commands

# Add Qwen-Agent to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'Qwen-Agent-main'))

from qwen_agent.agents import Assistant
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
}
if LLM_API_KEY:
    llm_cfg['api_key'] = LLM_API_KEY
if LLM_API_BASE:
    llm_cfg['base_url'] = LLM_API_BASE
if LLM_USE_RAW_API:
    llm_cfg['use_raw_api'] = True

logger.info(f"LLM Configuration: provider={LLM_PROVIDER}, model={LLM_MODEL}, base_url={LLM_API_BASE}, use_raw_api={LLM_USE_RAW_API}")

# Define the central system prompt for Qwen-Agent
SYSTEM_MESSAGE = """You are an advanced Obsidian Second Brain AI partner. You are proactive, "Always On", and manage a user's static knowledge vault via Discord.
You operate on the vault using your provided tools: vault_read_file, vault_write_file, vault_search, vault_list_files, and vault_health_check.

CORE RULES FOR VAULT WRITING (The AI-First Vault Principle):
Every note you create or update MUST follow the AI-first vault rules:
1. Self-contained context: each note explains itself, stating what, why, and when.
2. "For future Claude" preamble: Every note must start with a 2-3 sentence English summary under a '## For future Claude' header, placed immediately after the frontmatter block.
3. Rich, consistent YAML frontmatter: Every note must have delimiters (---) at the top, containing at least:
   ---
   date: YYYY-MM-DD
   type: <note-type> (e.g. daily, project, person, idea, task, decision, devlog, review, research, adr)
   tags: [tag1, tag2] (must include the note type as a tag)
   ai-first: true
   ---
4. Recency markers: Inline dates (as of YYYY-MM, source) for all external factual claims.
5. Verbatim source URLs preserved inline.
6. Mandatory wikilinks: Link every person, project, idea, or decision using [[wikilinks]] (e.g., [[Projects/MyProject]], [[People/John Doe]]).
7. Confidence levels: Use 'stated | high | medium | speculation' where applicable.

When writing or updating daily notes, projects, tasks, devlogs, or people, ensure you propagate changes (e.g., updating a project list or a task list when a task changes). Search before creating files to avoid duplication.
If your file writes fail validation, you will receive an error from the tool. Fix the content and write it again.
"""

# Initialize Discord Bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
obsidian_tools.DISCORD_BOT = bot  # Set the reference in tools

# Active user sessions / threads to maintain chat history
# Map of channel_id -> list of Qwen-Agent message history
channel_histories = {}

def sync_agent_run(agent_instance, messages_list) -> str:
    """Synchronous function to consume the agent's runner generator. Runs safely in a background thread."""
    bot_response_content = "I encountered an issue processing your request."
    try:
        for response in agent_instance.run(messages=messages_list):
            if response:
                bot_response_content = response[-1].get('content', '') if isinstance(response[-1], dict) else getattr(response[-1], 'content', '')
    except Exception as e:
        logger.error(f"Error in sync_agent_run: {e}")
        bot_response_content = f"Error in agent processing: {e}"
    return bot_response_content


def get_agent_for_channel(channel_id):
    """Instantiate a new Assistant agent with the custom Obsidian and Discord tools registered."""
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
    return Assistant(
        llm=llm_cfg,
        name='ObsidianBrain',
        description='Obsidian Second Brain Assistant',
        system_message=SYSTEM_MESSAGE,
        function_list=tools
    )


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
        await bot.process_commands(message)
        return

    # Check if the message is in a DM or if the bot is explicitly mentioned
    is_dm = isinstance(message.channel, discord.DMChannel)
    is_mentioned = bot.user.mentioned_in(message)
    
    # Also support logging if it's the dedicated log/vault logs channel
    is_log_channel = LOG_CHANNEL_ID and message.channel.id == LOG_CHANNEL_ID

    if not (is_dm or is_mentioned or is_log_channel):
        return

    # Process conversational message in the agentic loop
    channel_id = message.channel.id
    
    # If the bot was mentioned in a server channel, strip the mention to get clean prompt
    user_prompt = message.content
    if bot.user.mentioned_in(message):
        # Remove the mention from the content (e.g. <@123456789>)
        mention_str = f"<@{bot.user.id}>"
        mention_nick_str = f"<@!{bot.user.id}>"
        user_prompt = user_prompt.replace(mention_str, "").replace(mention_nick_str, "").strip()
        if not user_prompt:
            user_prompt = "Hello"  # Default prompt if it was just a raw mention

    # 1. Immediate Acknowledge: Send a typing indicator and a tentative placeholder message
    await message.channel.trigger_typing()
    placeholder = await message.channel.send("🧠 *Thinking... parsing your vault context...*")
    
    # 2. Push processing to background task to keep WebSocket connection active
    asyncio.create_task(run_agent_loop(message, placeholder, channel_id, user_prompt))

async def run_agent_loop(message: discord.Message, placeholder: discord.Message, channel_id: int, user_prompt: str):
    try:
        # Load or initialize chat history for this channel
        if channel_id not in channel_histories:
            channel_histories[channel_id] = []
            
        # Append user message to history
        channel_histories[channel_id].append({'role': 'user', 'content': user_prompt})
        
        # Instantiate agent
        agent = get_agent_for_channel(channel_id)
        
        # Initialize vault context if first time (e.g. read _CLAUDE.md)
        claude_md_path = VAULT_ROOT / "_CLAUDE.md"
        if len(channel_histories[channel_id]) == 1 and claude_md_path.exists():
            try:
                claude_content = claude_md_path.read_text(encoding="utf-8")
                # Feed the vault metadata as system context inside the history
                channel_histories[channel_id].insert(0, {
                    'role': 'system', 
                    'content': f"Obsidian Vault Configuration (_CLAUDE.md):\n```markdown\n{claude_content}\n```"
                })
            except Exception as e:
                logger.error(f"Error loading _CLAUDE.md: {e}")
                
        # Run Qwen-Agent generator in a separate worker thread to prevent event loop deadlocks with our async channel tools
        bot_response_content = await asyncio.to_thread(sync_agent_run, agent, channel_histories[channel_id])
            
        # Update history with bot response
        channel_histories[channel_id].append({'role': 'assistant', 'content': bot_response_content})
        
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
    bot.run(DISCORD_TOKEN)
