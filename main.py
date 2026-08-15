import os
import logging
from dotenv import load_dotenv
from packet_sniffer import PacketSnifferConfig, PacketWorker, PacketSniffer
from message_typer import ToClientBotThread, ToClientConfig


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

def validate_env():
    """Validate required environment variables are set."""
    required = {
        "DISCORD_WEB_HOOK": "Discord webhook URL for sending messages",
        "DISCORD_TOKEN": "Discord bot token",
        "TARGET_CHANNEL_ID": "Target Discord channel ID",
    }
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        logger.error("Missing required environment variables:")
        for m in missing:
            logger.error(f"    {m} - {required[m]}")
        sys.exit(1)


def main():
    """Main entry point for the packet sniffer application."""
    load_dotenv(".env")
    validate_env()

    # start sniffer
    bpf_filter = os.getenv("BPF_FILTER", "src host 54.214.176.167")
    sniffer_config = PacketSnifferConfig(
        discord_webhook_url=os.getenv("DISCORD_WEB_HOOK"),
        network_interface=os.getenv("NETWORK_INTERFACE", "Ethernet"),
        in_game_char_name=os.getenv("IN_GAME_CHAR_NAME", "DefaultChar"),
        bot_name=os.getenv("BOT_NAME", "DefaultBot"),
        queue_maxsize=1000,
        bpf_filter=bpf_filter
    )
    packet_worker = PacketWorker(sniffer_config)
    packet_sniffer = PacketSniffer(sniffer_config, packet_worker)

    packet_worker.start()
    packet_sniffer.start()


    #start message handler for discord to client
    typer_config = ToClientConfig(
        discord_token=os.getenv("DISCORD_TOKEN"),
        target_channel_id=int(os.getenv("TARGET_CHANNEL_ID")),
        guild_id=int(os.getenv("GUILD_ID", "0")) or None,
        delay_seconds=0.02
    )

    typer = ToClientBotThread(typer_config)
    typer.start()

    try:
        while typer.is_alive():
            typer.join(timeout=1)
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
        packet_sniffer.stop()
        packet_worker.stop()
        typer.stop()
        packet_sniffer.join(timeout=3)
        typer.join(timeout=5)


if __name__ == "__main__":
    main()
