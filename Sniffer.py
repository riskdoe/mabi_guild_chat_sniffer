import asyncio
import binascii
import pyshark
import queue
import threading
from typing import Optional

import Mabipacket.guildparser as parser
from discord_webhook import DiscordWebhook
from Guildmessage import Guilde_message


class PacketWorker:
    def __init__(
        self,
        queue_maxsize: int = 1000,
        discord_webhook: Optional[str] = None,
        bot_name: str = "DefaultBot",
        in_game_char_name: str = "DefaultChar"
    ):
        self._packet_queue = queue.Queue(maxsize=queue_maxsize)
        self._worker_thread = None
        self.webhook = discord_webhook
        self.bot_name = bot_name
        self.in_game_char_name = in_game_char_name
        print(f"[*] PacketWorker initialized with queue max size: {queue_maxsize}")

    def _worker_loop(self):
        """Main worker loop for processing packets."""
        print("[*] PacketWorker thread started.")
        while True:
            packet = self._packet_queue.get()
            if packet is None:
                print("[*] PacketWorker received shutdown signal. Exiting.")
                self._packet_queue.task_done()
                break

            try:
                if not hasattr(packet, "tcp") or not hasattr(packet.tcp, "payload"):
                    self._packet_queue.task_done()
                    continue

                if self.webhook is None:
                    self._packet_queue.task_done()
                    continue

                payload_hex = packet.tcp.payload.replace(":", "")
                if not payload_hex:
                    self._packet_queue.task_done()
                    continue

                payload_bytes = binascii.unhexlify(payload_hex)
                parsed_packet = parser.parse(data=payload_bytes, debug=False)

                if isinstance(parsed_packet, bool):
                    self._packet_queue.task_done()
                    continue

                if parsed_packet.paramCount == 0:
                    self._packet_queue.task_done()
                    continue

                # Build the message to send to Discord webhook
                message: Guilde_message = Guilde_message(
                    name=parsed_packet.parameters[0].value,
                    content=parsed_packet.parameters[1].value
                )


                # Clean up the message
                message.cleanmessage()
                message.replace_mentions()

                if self.in_game_char_name not in message.name:
                    webhook = DiscordWebhook(
                        url=self.webhook,
                        username=message.name,
                        content=message.content
                    )
                    message.add_emotes(webhook)
                    print(f"{message.name}: {message.content}")
                    webhook.execute()

            except Exception as e:
                print(f"[!] Error in worker packet processing: {e}")

    def start(self):
        """
        Starts the worker thread.
        """
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._worker_thread = threading.Thread(
                target=self._worker_loop, daemon=True
            )
            self._worker_thread.start()
            print("[*] PacketWorker thread requested to start.")
        else:
            print("[*] PacketWorker thread is already running.")

    def stop(self):
        """
        Sends a shutdown signal (poison pill) to the worker thread and waits for it to finish.
        """
        if self._worker_thread and self._worker_thread.is_alive():
            print("[*] Sending shutdown signal to PacketWorker thread...")
            self._packet_queue.put(None)  # Poison pill
            self._worker_thread.join()
            print("[*] PacketWorker thread stopped.")
        else:
            print("[*] PacketWorker thread is not running or not initialized.")

    def add_packet(self, packet):
        """
        Adds a packet to the internal queue for processing by the worker thread.
        Drops packets if the queue is full.
        """
        try:
            self._packet_queue.put_nowait(packet)
        except queue.Full:
            print("[!] PacketWorker queue full, dropping packet.")

    @property
    def queue_size(self):
        """Returns the current size of the worker queue."""
        return self._packet_queue.qsize()

    @property
    def queue_maxsize(self):
        """Returns the maximum size of the worker queue."""
        return self._packet_queue.maxsize


class PacketSniffer(threading.Thread):
    def __init__(
        self,
        worker_instance: PacketWorker,
        network_interface: str = "Ethernet",
    ):
        super().__init__()
        self.worker_instance = worker_instance
        self.network_interface = network_interface
        self.running = True
        self.capture: Optional[pyshark.LiveCapture] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        print(f"Starting packet sniffer on interface: {self.network_interface}")
        try:
            self.capture = pyshark.LiveCapture(
                interface=self.network_interface,
                bpf_filter="src host 54.214.176.167"
            )
            for packet in self.capture.sniff_continuously():
                if not self.running:
                    print("Sniffing stopped by stop() call.")
                    break

                if 'TCP' not in packet:
                    continue

                if not hasattr(packet.tcp, "payload"):
                    continue
                self.worker_instance.add_packet(packet)

        except Exception as e:
            print(f"Packet sniffer error: {e}")
        finally:
            if self.capture:
                self.capture.close()
            if self.loop and self.loop.is_running():
                self.loop.stop()
            if self.loop and not self.loop.is_closed():
                self.loop.close()
            print("PacketSniffer stopped.")

    def stop(self):
        """Stops the packet sniffing thread."""
        self.running = False
        print("Stopping PacketSniffer...")
        if self.capture:
            self.capture.close()
