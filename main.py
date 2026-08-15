import os
import signal
import sys
import logging
import threading
import time
import queue
from dotenv import load_dotenv

from packet_sniffer import PacketSnifferConfig, PacketWorker, PacketSniffer
from message_typer import ToClientBotThread, ToClientConfig
from tui import TUI, create_queue_handler
from stats import stats

# Try to import curses for TUI
try:
    import curses
    CURSES_AVAILABLE = True
except ImportError:
    CURSES_AVAILABLE = False

# Configure logging with cleaner format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# Log queue for TUI
log_queue = queue.Queue(maxsize=1000)


def setup_queue_handler():
    """Set up the queue handler for logging."""
    queue_handler = create_queue_handler(log_queue)
    logger.addHandler(queue_handler)
    # Also add to root logger to catch all logs
    logging.getLogger().addHandler(queue_handler)


def run_tui(stdscr):
    """Run the TUI interface."""
    load_dotenv(".env")
    
    required = {
        "DISCORD_WEB_HOOK": "Discord webhook URL for sending messages",
        "DISCORD_TOKEN": "Discord bot token",
        "TARGET_CHANNEL_ID": "Target Discord channel ID",
    }
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        stdscr.clear()
        stdscr.addstr(0, 0, "ERROR: Missing required environment variables:")
        for i, m in enumerate(missing):
            stdscr.addstr(2 + i, 0, f"  {m} - {required[m]}")
        stdscr.addstr(len(required) + 3, 0, "Please set them in .env file or environment.")
        stdscr.addstr(len(required) + 5, 0, "Press any key to exit...")
        stdscr.refresh()
        stdscr.getch()
        return
    
    bpf_filter = os.getenv("BPF_FILTER", "src host 54.214.176.167")
    sniffer_config = PacketSnifferConfig(
        discord_webhook_url=os.environ["DISCORD_WEB_HOOK"],
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
    
    typer_config = ToClientConfig(
        discord_token=os.environ["DISCORD_TOKEN"],
        target_channel_id=int(os.environ["TARGET_CHANNEL_ID"]),
        guild_id=int(os.getenv("GUILD_ID", "0")) or None,
        delay_seconds=0.02
    )
    
    typer = ToClientBotThread(typer_config)
    typer.start()
    
    setup_queue_handler()
    
    def shutdown(signum, frame):
        logger.info("Shutting down...")
        packet_sniffer.stop()
        packet_worker.stop()
        typer.stop()
        packet_sniffer.join(timeout=3)
        typer.join(timeout=5)
    
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    tui = TUI(log_queue)
    tui.run(stdscr)
    
    shutdown(None, None)


def run_console():
    """Run the original console interface."""
    load_dotenv(".env")
    
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

    typer_config = ToClientConfig(
        discord_token=os.getenv("DISCORD_TOKEN"),
        target_channel_id=int(os.getenv("TARGET_CHANNEL_ID")),
        guild_id=int(os.getenv("GUILD_ID", "0")) or None,
        delay_seconds=0.02
    )

    typer = ToClientBotThread(typer_config)
    typer.start()

    def shutdown(signum, frame):
        logger.info("Shutting down...")
        packet_sniffer.stop()
        packet_worker.stop()
        typer.stop()
        packet_sniffer.join(timeout=3)
        typer.join(timeout=5)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while typer.is_alive():
            typer.join(timeout=1)
    except KeyboardInterrupt:
        shutdown(signal.SIGINT, None)


def main():
    """Main entry point - chooses between TUI and console."""
    if sys.stdout.isatty() and CURSES_AVAILABLE:
        curses.wrapper(run_tui)
    else:
        run_console()


if __name__ == "__main__":
    main()