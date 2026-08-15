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

# Statistics tracking
stats = {
    'packets_processed': 0,
    'messages_to_discord': 0,
    'messages_to_game': 0,
    'errors': 0,
    'start_time': time.time()
}
stats_lock = threading.Lock()
# ponytail: global lock for stats, use per-counter locks or atomic ops if throughput matters

# Log queue for TUI
log_queue = queue.Queue()


class QueueHandler(logging.Handler):
    """Logging handler that sends records to a queue for TUI display."""
    def emit(self, record):
        log_queue.put(self.format(record))


def setup_queue_handler():
    """Set up the queue handler for logging."""
    queue_handler = QueueHandler()
    queue_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    ))
    logger.addHandler(queue_handler)
    # Also add to root logger to catch all logs
    logging.getLogger().addHandler(queue_handler)


def display_stats(stdscr):
    """Display statistics in the TUI."""
    with stats_lock:
        uptime = time.time() - stats['start_time']
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        
        # Clear and redraw stats window
        stdscr.attron(curses.A_BOLD)
        stdscr.addstr(0, 0, " Mabinogi Chat Sniffer - TUI ".ljust(50, "="))
        stdscr.attroff(curses.A_BOLD)
        
        stdscr.addstr(2, 0, f"Uptime: {uptime_str}")
        stdscr.addstr(3, 0, f"Packets processed: {stats['packets_processed']}")
        stdscr.addstr(4, 0, f"Messages to Discord: {stats['messages_to_discord']}")
        stdscr.addstr(5, 0, f"Messages to game: {stats['messages_to_game']}")
        stdscr.addstr(6, 0, f"Errors: {stats['errors']}")
        stdscr.addstr(7, 0, "=" * 50)


def run_tui(stdscr):
    """Run the TUI interface."""
    # Load environment variables
    load_dotenv(".env")
    
    # Validate required environment variables
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
    
    # Initialize curses
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(1)   # Non-blocking input
    stdscr.timeout(100) # Refresh every 100ms
    
    # Set up logging to queue
    setup_queue_handler()
    
    # Start background tasks
    bpf_filter = os.getenv("BPF_FILTER", "src host 54.214.176.167")
    sniffer_config = PacketSnifferConfig(
        discord_webhook_url=os.environ["DISCORD_WEB_HOOK"],  # type: ignore
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
    
    # TUI state
    last_stats_update = 0
    stats_update_interval = 1.0  # Update stats every second
    log_lines = []  # Store log lines for display
    max_log_lines = 100  # Maximum lines to keep in log view
    
    def shutdown(signum, frame):
        logger.info("Shutting down...")
        packet_sniffer.stop()
        packet_worker.stop()
        typer.stop()
        packet_sniffer.join(timeout=3)
        typer.join(timeout=5)
    
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    # Main TUI loop
    while typer.is_alive():
        # Check for input (q to quit)
        key = stdscr.getch()
        if key == ord('q') or key == ord('Q'):
            break
        
        current_time = time.time()
        
        # Update stats periodically
        if current_time - last_stats_update >= stats_update_interval:
            display_stats(stdscr)
            last_stats_update = current_time
        
        # Process log messages from queue
        try:
            while True:
                record = log_queue.get_nowait()
                log_lines.append(record)
                # Keep only the most recent lines
                if len(log_lines) > max_log_lines:
                    log_lines = log_lines[-max_log_lines:]
        except queue.Empty:
            pass
        
        # Display logs
        stdscr.addstr(9, 0, " Logs (most recent at bottom): ".ljust(50, "-"))
        for i, line in enumerate(log_lines[-20:]):  # Show last 20 lines
            if 10 + i < curses.LINES - 1:  # Avoid writing beyond screen
                stdscr.addstr(10 + i, 0, line[:curses.COLS-1])  # Truncate to fit width
        
        stdscr.refresh()
        typer.join(timeout=0.1)  # Small sleep to prevent busy loop
    
    # Final shutdown
    shutdown(None, None)


def run_console():
    """Run the original console interface."""
    load_dotenv(".env")
    
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
    # Use TUI if we're in a TTY and curses is available
    if sys.stdout.isatty() and CURSES_AVAILABLE:
        curses.wrapper(run_tui)
    else:
        run_console()


if __name__ == "__main__":
    main()