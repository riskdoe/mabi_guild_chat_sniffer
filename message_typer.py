import asyncio
import os
import platform
import queue
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Optional

import discord

# ============================================================================
# AI GENERATED CODE
# ============================================================================
DISCORD_EMOTE_PATTERN = r"<a?:(\w+):(\d+)>"
UNICODE_EMOJI_PATTERN = (
    r"[\U0001F1E6-\U0001F1FF]"     # Regional Indicators (flags) 🇺🇸
    r"|[\U0001F300-\U0001F5FF]"    # Miscellaneous Symbols 🌍
    r"|[\U0001F600-\U0001F64F]"    # Emoticons 😀
    r"|[\U0001F680-\U0001F6FF]"    # Transport and Map 🚀
    r"|[\U0001F700-\U0001F77F]"    # Alchemical Symbols
    r"|[\U0001F780-\U0001F7FF]"    # Geometric Shapes Extended
    r"|[\U0001F800-\U0001F8FF]"    # Supplemental Arrows-C
    r"|[\U0001F900-\U0001F9FF]"    # Supplemental Symbols 🤷
    r"|[\U0001FA00-\U0001FA6F]"    # Chess Symbols ♟
    r"|[\U0001FA70-\U0001FAFF]"    # Symbols Extended-A 🫠
    r"|[\U00002600-\U000026FF]"    # Miscellaneous Symbols ☀
    r"|[\U00002700-\U000027BF]"    # Dingbats ✂
    r"|[\U0001F000-\U0001F02F]"    # Mahjong Tiles 🀄
    r"|[\U0001F0A0-\U0001F0FF]"    # Playing Cards 🃏
    r"|[\U00002B50]"               # Star ⭐
    r"|[\U00002934-\U00002935]"    # Arrows
)
UNICODE_EMOJI_PATTERN_WITH_MODIFIERS = (
    UNICODE_EMOJI_PATTERN +
    r"|[\U0001F3FB-\U0001F3FF]"    # Skin tone modifiers 👋🏻
    r"|[\U0000200D]"               # Zero-width joiner (for combo emojis)
    r"|[\U0000FE00-\U0000FE0F]"    # Variation selectors
)
INVISIBLE_CHAR_PATTERN = (
    r"[\u200B-\u200F]"             # Zero-width spaces and formatters
    r"|[\u202A-\u202E]"            # Bidirectional text formatting
    r"|[\u2060-\u206F]"            # Word joiners and invisible operators
    r"|[\uFEFF]"                   # Zero-width no-break space (BOM)
    r"|[\u180E]"                   # Mongolian vowel separator
    r"|[\u00AD]"                   # Soft hyphen
    r"|[\u034F]"                   # Combining grapheme joiner
    r"|[\u061C]"                   # Arabic letter mark
)
CODEPOINT_PATTERN = (
    r"[\u0300-\u036f\u0483-\u0489\u1AB0-\u1AFF\u1DC0-\u1DFF\u20D0-\u20FF\uFE20-\uFE2F]"
)
DISCORD_MENTION_PATTERN = r"<@!?(\d+)>|<@&(\d+)>"  # User and role mentions
DISCORD_CHANNEL_PATTERN = r"<#(\d+)>"              # Channel mentions
DISCORD_MARKDOWN_PATTERN = r"(\*\*|__|\*|_|~~|`|```|\|\|)"


# Compile for performance (re.compile is faster when used multiple times)
DISCORD_EMOTE_REGEX = re.compile(DISCORD_EMOTE_PATTERN)
UNICODE_EMOJI_REGEX = re.compile(UNICODE_EMOJI_PATTERN_WITH_MODIFIERS)
INVISIBLE_CHAR_REGEX = re.compile(INVISIBLE_CHAR_PATTERN)
DISCORD_MENTION_REGEX = re.compile(DISCORD_MENTION_PATTERN)
DISCORD_CHANNEL_REGEX = re.compile(DISCORD_CHANNEL_PATTERN)
DISCORD_MARKDOWN_REGEX = re.compile(DISCORD_MARKDOWN_PATTERN)
CODEPOINT_PATTERN_REGEX = re.compile(CODEPOINT_PATTERN)




def normalize_discord_message(
    message: str,
    emote_replacement: str = ":{name}:",
    emoji_replacement: str = "*",
    preserve_spacing: bool = True,
    remove_mentions: bool = True,
    remove_markdown: bool = False,
    max_length: Optional[int] = None
) -> str:
    # 1. Remove invisible/zero-width characters (do this first!)
    message = INVISIBLE_CHAR_REGEX.sub("", message)
    
    # 2. Replace Discord custom emotes with :name: format
    def emote_replacer(match):
        name, emote_id = match.groups()
        return emote_replacement.format(name=name, id=emote_id)
    
    message = DISCORD_EMOTE_REGEX.sub(emote_replacer, message)
    message = CODEPOINT_PATTERN_REGEX.sub("", message)
    
    # 3. Remove or replace Unicode emojis
    message = UNICODE_EMOJI_REGEX.sub(emoji_replacement, message)
    
    # 4. Optionally remove Discord mentions
    if remove_mentions:
        # Replace @user and @role mentions with [mention]
        message = DISCORD_MENTION_REGEX.sub("[mention]", message)
        message = DISCORD_CHANNEL_REGEX.sub("[channel]", message)
        # Remove @everyone and @here
        message = message.replace("@everyone", "").replace("@here", "")
    
    # 5. Optionally remove markdown formatting
    if remove_markdown:
        message = DISCORD_MARKDOWN_REGEX.sub("", message)
    
    # 6. Clean up whitespace
    if preserve_spacing:
        # Replace multiple spaces with single space
        message = re.sub(r'\s+', ' ', message)
        message = message.strip()
    
    # 7. Limit length if specified
    if max_length and len(message) > max_length:
        message = message[:max_length - 3] + "..."
    
    return message

def extract_discord_emotes(message: str) -> list[tuple[str, str]]:
    return DISCORD_EMOTE_REGEX.findall(message)    

def clean_username(username: str, max_length: int = 16) -> str:

    # Remove emojis
    username = UNICODE_EMOJI_REGEX.sub("", username)
    
    # Remove invisible characters
    username = INVISIBLE_CHAR_REGEX.sub("", username)
    
    # Remove Discord markdown
    username = DISCORD_MARKDOWN_REGEX.sub("", username)
    
    # Clean whitespace
    username = " ".join(username.split())
    
    # Limit length
    if len(username) > max_length:
        username = username[:max_length]
    
    return username.strip()

def normalize_message_chunks(
    message: str,
    chunk_size: int = 150,
    **kwargs
) -> list[str]:
    # First normalize the entire message
    normalized = normalize_discord_message(message, **kwargs)
    
    if len(normalized) <= chunk_size:
        return [normalized]
    
    chunks = []
    words = normalized.split()
    current_chunk = []
    current_length = 0
    
    for word in words:
        word_length = len(word) + 1  # +1 for space
        
        # If single word is too long, split it
        if len(word) > chunk_size:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0
            
            # Split the long word into chunks
            for i in range(0, len(word), chunk_size):
                chunks.append(word[i:i + chunk_size])
            continue
        
        # If adding this word would exceed limit, start new chunk
        if current_length + word_length > chunk_size:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = len(word)
        else:
            current_chunk.append(word)
            current_length += word_length
    
    # Add remaining chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks

# ============================================================================
# end of ai generated code
# ============================================================================


def type_message(message: str, delay_seconds: float) -> None:
        # Search for and activate the game window
    os.system(f'xdotool search --name "Mabinogi" windowactivate')
    time.sleep(delay_seconds)
        
    os.system("xdotool key Return")
    time.sleep(delay_seconds)
    subprocess.run(["xdotool", "type", message], check=False)
    time.sleep(delay_seconds)
    os.system("xdotool key Return")
    time.sleep(delay_seconds)
    os.system("xdotool key Return")
    time.sleep(delay_seconds)


class ToClientWorker:
    def __init__(self,
     queue_maxsize: int = 1000, 
     delay_seconds: float = 0.02):
        self._queue: queue.Queue[Optional[str]] = queue.Queue(maxsize=queue_maxsize)
        self._thread: Optional[threading.Thread] = None
        self._delay_seconds = delay_seconds
        print(f"[*] Typerworker initialized with queue max size: {queue_maxsize}")

    def _loop(self) -> None:
        print("[*] ToClientWorker thread started.")
        while True:
            item = self._queue.get()
            if item is None:
                print("[*] PacketWorker received shutdown signal. Exiting.")
                self._queue.task_done()
                break

            try:
                type_message(item, delay_seconds=self._delay_seconds)
            except Exception as e:
                print(f"[!] ToClientWorker error: {e}")
            finally:
                self._queue.task_done()

    def start(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        if self._thread and self._thread.is_alive():
            self._queue.put(None)
            self._thread.join(timeout=5)

    def enqueue(self, message: str) -> None:
        try:
            self._queue.put_nowait(message)
        except queue.Full:
            print("[!] ToClientWorker queue full, dropping message.")


@dataclass(frozen=True)
class ToClientConfig:
    discord_token: str
    target_channel_id: int
    guild_id: Optional[int] = None
    delay_seconds: float = 0.02


class DiscordClient(discord.Client):
    def __init__(self, *, config: ToClientConfig, worker: ToClientWorker, intents: discord.Intents):
        super().__init__(intents=intents)
        self._config = config
        self._worker = worker
        self.tree = discord.app_commands.CommandTree(self)
        self.scheduled_tasks: dict[int, dict[str, object]] = {}

    async def setup_hook(self) -> None:
        if self._config.guild_id is not None:
            self.tree.copy_global_to(guild=discord.Object(id=self._config.guild_id))
            await self.tree.sync(guild=discord.Object(id=self._config.guild_id))
        else:
            await self.tree.sync()

    async def on_ready(self) -> None:
        print(f"[*] to_game logged on as {self.user}!")
        self._worker.start()

    async def on_message(self, message: discord.Message) -> None:
        if message.webhook_id is not None:
            return
        if message.author.bot:
            return
        if message.channel.id != self._config.target_channel_id:
            return
        if (message.content or "").startswith("!"):
            return

        usrname = message.author.display_name
        message_content = message.content or " "
        cleaned = normalize_discord_message(message_content)
        formatted_message = f"[{usrname}] : {cleaned}".replace('"', "")
        chunks = normalize_message_chunks(formatted_message, chunk_size=80)
    
        print(f"[O] {formatted_message}")

        for chunk in chunks:
            chunk = chunk.replace("\0", "")
            if chunk:
                self._worker.enqueue(chunk)



class ToClientBotThread(threading.Thread):
    def __init__(self, config: ToClientConfig):
        super().__init__(daemon=True)
        self._config = config
        self._client: Optional[DiscordClient] = None

    def stop(self) -> None:
        """Close the Discord client so the bot thread can exit."""
        if self._client is None:
            return
        loop = getattr(self._client, "loop", None)
        if loop is None or loop.is_closed():
            return
        try:
            loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(self._client.close())
            )
        except Exception:
            pass

    def run(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True

        worker = ToClientWorker(delay_seconds=self._config.delay_seconds)
        client = DiscordClient(config=self._config, worker=worker, intents=intents)
        self._client = client

        print("[*] Starting to_game Discord bot...")
        client.run(self._config.discord_token, log_handler=None)
