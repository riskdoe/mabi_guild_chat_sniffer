import os
from dotenv import load_dotenv
from worker import PacketWorker
from Sniffer import PacketSniffer

if __name__ == "__main__":
    load_dotenv()
    # --- Configuration from .env ---
    DISCORD_WEB_HOOK = os.getenv("DISCORD_WEB_HOOK")
    if DISCORD_WEB_HOOK is None:
        print("Warning: DISCORD_WEB_HOOK environment variable not set.")

    BOT_NAME = os.getenv("BOT_NAME", "DefaultBot")
    IN_GAME_CHAR_NAME = os.getenv("IN_GAME_CHAR_NAME", "DefaultChar")
    NETWORK_INTERFACE = os.getenv("NETWORK_INTERFACE", "Ethernet")

    worker_thread = PacketWorker(
        discord_webhook=DISCORD_WEB_HOOK,
        bot_name=BOT_NAME,
        in_game_char_name=IN_GAME_CHAR_NAME
    )

    worker_thread.start()

    sniffer = PacketSniffer(
        worker_instance=worker_thread,
        network_interface=NETWORK_INTERFACE,
    )
    sniffer.start()
    sniffer.join()
