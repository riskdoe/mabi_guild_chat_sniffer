import asyncio
import binascii
import logging
import pyshark
import queue
import threading
from dataclasses import dataclass
from typing import Optional

import Mabipacket.guildparser as parser
from discord_webhook import DiscordWebhook
from Guildmessage import Guild_message


from stats import stats, stats_lock


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PacketSnifferConfig:
    """Configuration for the packet sniffer and Discord webhook."""
    discord_webhook_url: str
    network_interface: str
    in_game_char_name: str
    bot_name: str = "DefaultBot"
    queue_maxsize: int = 1000
    bpf_filter: str = "src host 54.214.176.167"


class PacketWorker:
    def __init__(self, config: PacketSnifferConfig):
        self._config = config
        self._queue = queue.Queue(maxsize=config.queue_maxsize)
        self._worker_thread = None
        logger.info(f"PacketWorker initialized with queue max size: {config.queue_maxsize}")

    def _loop(self):
        logger.info("PacketWorker thread started.")
        while True:
            packet = self._queue.get()
            if packet is None:
                logger.info("PacketWorker received shutdown signal. Exiting.")
                self._queue.task_done()
                break

            try:
                if not hasattr(packet, "tcp"):
                    continue

                # Try reassembled TCP stream data first (for fragmented long messages)
                tcp = packet.tcp
                reassembled = getattr(tcp, "reassembled_data", None)
                if reassembled and isinstance(reassembled, str):
                    payload_hex = reassembled.replace(":", "")
                else:
                    payload = getattr(tcp, "payload", None)
                    if payload and isinstance(payload, str):
                        payload_hex = payload.replace(":", "")
                    else:
                        continue
                    
                if not payload_hex:
                    continue

                payload_bytes = binascii.unhexlify(payload_hex)
                parsed_packet = parser.parse(data=payload_bytes, debug=False)

                if isinstance(parsed_packet, bool):
                    logger.debug(f"Parser returned False for payload (len={len(payload_bytes)}): {payload_hex[:100]}...")
                    continue

                if parsed_packet.paramCount == 0:
                    logger.debug(f"Parser returned 0 params for payload (len={len(payload_bytes)}): {payload_hex[:100]}...")
                    continue

                # Build the message to send to Discord webhook
                message: Guild_message = Guild_message(
                    name=parsed_packet.parameters[0].value,
                    content=parsed_packet.parameters[1].value
                )

                # Clean up the message
                message.cleanmessage()
                message.replace_mentions()

                if self._config.in_game_char_name not in message.name:
                    # Discord has 2000 char limit per message - chunk if needed
                    max_chunk = 1900
                    content = message.content
                    for i in range(0, len(content), max_chunk):
                        chunk = content[i:i + max_chunk]
                        webhook = DiscordWebhook(
                            url=self._config.discord_webhook_url,
                            username=message.name[:80] if i == 0 else "",  # Discord username limit 80
                            content=chunk
                        )
                        message.add_emotes(webhook)
                        logger.info(f"{message.name}: {chunk}")
                        try:
                            response = webhook.execute()
                            logger.debug(f"Webhook response: {response.status_code}")
                        except Exception as webhook_err:
                            logger.exception(f"Webhook execute failed for '{chunk[:50]}...': {webhook_err}")
                            raise
                        stats.increment('messages_to_discord')
                    
            except Exception as e:
                logger.exception(f"Error in worker packet processing: {e}")
                # Increment error stats
                stats.increment('errors')
            finally:
                self._queue.task_done()
                # Increment packets processed stat
                stats.increment('packets_processed')

    def start(self):
        """Starts the worker thread."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._worker_thread = threading.Thread(
                target=self._loop, daemon=True
            )
            self._worker_thread.start()
            logger.info("PacketWorker thread requested to start.")
        else:
            logger.info("PacketWorker thread is already running.")

    def stop(self):
        """Sends a shutdown signal (poison pill) to the worker thread and waits for it to finish."""
        if self._worker_thread and self._worker_thread.is_alive():
            logger.info("Sending shutdown signal to PacketWorker thread...")
            self._queue.put(None)  # Poison pill
            self._worker_thread.join()
            logger.info("PacketWorker thread stopped.")
        else:
            logger.info("PacketWorker thread is not running or not initialized.")

    def add_packet(self, packet):
        """Adds a packet to the internal queue for processing by the worker thread."""
        try:
            self._queue.put_nowait(packet)
        except queue.Full:
            logger.warning("PacketWorker queue full, dropping packet.")

    @property
    def queue_size(self):
        """Returns the current size of the worker queue."""
        return self._queue.qsize()

    @property
    def queue_maxsize(self):
        """Returns the maximum size of the worker queue."""
        return self._queue.maxsize


class PacketSniffer(threading.Thread):
    def __init__(self, config: PacketSnifferConfig, worker_instance: PacketWorker):
        super().__init__(daemon=True)
        self._config = config
        self.worker_instance = worker_instance
        self.running = True
        self.capture: Optional[pyshark.LiveCapture] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        logger.info(f"Starting packet sniffer on interface: {self._config.network_interface}")
        try:
            self.capture = pyshark.LiveCapture(
                interface=self._config.network_interface,
                bpf_filter=self._config.bpf_filter,
                override_prefs={"tcp.desegment_tcp_streams": "TRUE"}
            )
            for packet in self.capture.sniff_continuously():
                if not self.running:
                    logger.info("Sniffing stopped by stop() call.")
                    break

                if 'TCP' not in packet:
                    continue

                # Accept packets with either payload or reassembled_data (must be strings)
                tcp = packet.tcp
                has_payload = hasattr(tcp, "payload") and isinstance(getattr(tcp, "payload", None), str)
                has_reassembled = hasattr(tcp, "reassembled_data") and isinstance(getattr(tcp, "reassembled_data", None), str)
                
                if not (has_payload or has_reassembled):
                    continue

                self.worker_instance.add_packet(packet)

        except Exception as e:
            logger.exception(f"Packet sniffer error: {e}")
        finally:
            if self.capture:
                self.capture.close()
            if self.loop and self.loop.is_running():
                self.loop.stop()
            if self.loop and not self.loop.is_closed():
                self.loop.close()
            logger.info("PacketSniffer stopped.")

    def stop(self):
        """Stops the packet sniffing thread."""
        self.running = False
        logger.info("Stopping PacketSniffer...")
        if self.capture:
            self.capture.close()
