import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AppConfig:
    discord_webhook_url: str
    discord_token: str
    target_channel_id: int
    guild_id: Optional[int]
    network_interface: str
    in_game_char_name: str
    bot_name: str
    bpf_filter: str
    queue_maxsize: int = 1000
    delay_seconds: float = 0.02


def load_config() -> AppConfig:
    """Load configuration from environment variables."""
    required = {
        "DISCORD_WEB_HOOK": "Discord webhook URL for sending messages",
        "DISCORD_TOKEN": "Discord bot token",
        "TARGET_CHANNEL_ID": "Target Discord channel ID",
    }
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return AppConfig(
        discord_webhook_url=os.environ["DISCORD_WEB_HOOK"],
        discord_token=os.environ["DISCORD_TOKEN"],
        target_channel_id=int(os.environ["TARGET_CHANNEL_ID"]),
        guild_id=int(os.getenv("GUILD_ID", "0")) or None,
        network_interface=os.getenv("NETWORK_INTERFACE", "Ethernet"),
        in_game_char_name=os.getenv("IN_GAME_CHAR_NAME", "DefaultChar"),
        bot_name=os.getenv("BOT_NAME", "DefaultBot"),
        bpf_filter=os.getenv("BPF_FILTER", "src host 54.214.176.167"),
        queue_maxsize=1000,
        delay_seconds=0.02,
    )


def create_sniffer_config(config: AppConfig):
    from packet_sniffer import PacketSnifferConfig
    return PacketSnifferConfig(
        discord_webhook_url=config.discord_webhook_url,
        network_interface=config.network_interface,
        in_game_char_name=config.in_game_char_name,
        bot_name=config.bot_name,
        queue_maxsize=config.queue_maxsize,
        bpf_filter=config.bpf_filter,
    )


def create_typer_config(config: AppConfig):
    from discord_client import ToClientConfig
    return ToClientConfig(
        discord_token=config.discord_token,
        target_channel_id=config.target_channel_id,
        guild_id=config.guild_id,
        delay_seconds=config.delay_seconds,
    )