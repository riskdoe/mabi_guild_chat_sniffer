from __future__ import annotations
import json
from pathlib import Path
from typing import ClassVar

from discord_webhook import DiscordWebhook, DiscordEmbed


class Guild_message:
    _mentions_config: ClassVar[dict[str, dict[str, str]] | None] = None

    def __init__(self, name: str, content: str) -> None:
        super().__init__()
        self.name = name
        self.content = content

    @classmethod
    def _load_mentions_config(cls) -> dict[str, dict[str, str]]:
        if cls._mentions_config is None:
            config_path = Path(__file__).parent / "mentions_config.json"
            if config_path.exists():
                with config_path.open("r") as f:
                    cls._mentions_config = json.load(f)
            else:
                cls._mentions_config = {"role_mentions": {}, "user_mentions": {}}
        # _mentions_config is guaranteed to be set after the if/else above
        return cls._mentions_config  # type: ignore[return-value]

    def replace_mentions(self) -> None:
        config = self._load_mentions_config()
        out = self.content

        for keyword, role_id in config.get("role_mentions", {}).items():
            out = out.replace(f"@{keyword}", f"<@&{role_id}>")

        for keyword, user_id in config.get("user_mentions", {}).items():
            out = out.replace(f"@{keyword}", f"<@{user_id}>")

        self.content = out

    def cleanmessage(self) -> None:
        out = self.content
        out = out.replace("@everyone", "")
        out = out.replace("@here", "")
        out = out.replace("&", "")
        self.content = out

    def add_emotes(self, webhook: DiscordWebhook) -> None:
        if ":foxspinn:" in self.content.lower():
            embed = DiscordEmbed(title="spin")
            embed.set_image(
                url="https://raw.githubusercontent.com/riskdoe/mabi_guild_chat_sniffer/refs/heads/rewrite/emotes/spinn.webp"
            )
            webhook.add_embed(embed)
        if ":foxspin:" in self.content.lower():
            embed = DiscordEmbed(title="spin")
            embed.set_image(
                url="https://raw.githubusercontent.com/riskdoe/mabi_guild_chat_sniffer/refs/heads/rewrite/emotes/spin.webp"
            )
            webhook.add_embed(embed)