import signal
import sys
import logging
import threading
import queue

from dotenv import load_dotenv

from packet_sniffer import PacketWorker, PacketSniffer
from discord_client import ToClientBotThread
from tui import TUI, create_queue_handler
from stats import stats
from config import load_config, create_sniffer_config, create_typer_config


# Try to import curses for TUI
try:
    import curses
    CURSES_AVAILABLE = True
except ImportError:
    CURSES_AVAILABLE = False

# Log queue for TUI
log_queue = queue.Queue(maxsize=1000)

logger = logging.getLogger(__name__)


def setup_logging_for_tui():
    """Configure logging for TUI mode - only queue handler, no stdout."""
    # Remove any existing handlers from root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set up queue handler for root logger (catches all logs)
    queue_handler = create_queue_handler(log_queue)
    root_logger.addHandler(queue_handler)
    root_logger.setLevel(logging.INFO)

    # Also add to module logger
    logger.addHandler(queue_handler)
    logger.setLevel(logging.INFO)


def setup_logging_for_console():
    """Configure logging for console mode - standard stdout output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )


def run_tui(stdscr):
    """Run the TUI interface."""
    setup_logging_for_tui()
    load_dotenv(".env")
    
    config = load_config()

    sniffer_config = create_sniffer_config(config)
    packet_worker = PacketWorker(sniffer_config)
    packet_sniffer = PacketSniffer(sniffer_config, packet_worker)

    packet_worker.start()
    packet_sniffer.start()

    typer_config = create_typer_config(config)

    typer = ToClientBotThread(typer_config)
    typer.start()

    # Logging already set up by setup_logging_for_tui() at start of run_tui

    def do_shutdown():
        logger.info("Shutting down...")
        packet_sniffer.stop()
        packet_worker.stop()
        typer.stop()

    signal.signal(signal.SIGINT, lambda s, f: do_shutdown())
    signal.signal(signal.SIGTERM, lambda s, f: do_shutdown())

    tui = TUI(
        log_queue,
        on_shutdown=do_shutdown,
        threads_to_join=[packet_sniffer, typer],
    )
    tui.run(stdscr)


def run_console():
    """Run the original console interface."""
    setup_logging_for_console()
    load_dotenv(".env")

    config = load_config()

    sniffer_config = create_sniffer_config(config)
    packet_worker = PacketWorker(sniffer_config)
    packet_sniffer = PacketSniffer(sniffer_config, packet_worker)

    packet_worker.start()
    packet_sniffer.start()

    typer_config = create_typer_config(config)

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