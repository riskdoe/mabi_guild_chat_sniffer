import os
from dotenv import load_dotenv
from worker import PacketWorker
from Sniffer import PacketSniffer
from to_game import ToClientBotThread, ToClientConfig


def main():
    """Main entry point for the packet sniffer application."""
    load_dotenv()
    
    # Configuration from .env
    discord_webhook = os.getenv("DISCORD_WEB_HOOK")
    if discord_webhook is None:
        print("Warning: DISCORD_WEB_HOOK environment variable not set.")
    
    bot_name = os.getenv("BOT_NAME", "DefaultBot")
    in_game_char_name = os.getenv("IN_GAME_CHAR_NAME", "DefaultChar")
    network_interface = os.getenv("NETWORK_INTERFACE", "Ethernet")
    
    # Initialize and start worker thread
    worker_thread = PacketWorker(
        discord_webhook=discord_webhook,
        bot_name=bot_name,
        in_game_char_name=in_game_char_name
    )
    worker_thread.start()
    
    # Initialize and start packet sniffer
    sniffer = PacketSniffer(
        worker_instance=worker_thread,
        network_interface=network_interface,
    )
    sniffer.start()
    sniffer.join()


if __name__ == "__main__":
    main()
