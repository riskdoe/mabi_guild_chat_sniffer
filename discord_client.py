import asyncio
import logging
import threading
from dataclasses import dataclass
from typing import Optional

import discord

from message_normalizer import normalize_discord_message, normalize_message_chunks
from stats import stats
from to_client_worker import ToClientWorker


logger = logging.getLogger(__name__)


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
        logger.info(f"to_game logged on as {self.user}!")
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
    
        logger.info(f"Outgoing: {formatted_message}")

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
        client = self._client  # Local variable for type narrowing
        loop = getattr(client, "loop", None)
        if loop is None or loop.is_closed():
            return
        try:
            loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(client.close())
            )
        except Exception:
            pass

    def run(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True

        worker = ToClientWorker(delay_seconds=self._config.delay_seconds)
        client = DiscordClient(config=self._config, worker=worker, intents=intents)
        self._client = client

        logger.info("Starting to_game Discord bot...")
        client.run(self._config.discord_token, log_handler=None)