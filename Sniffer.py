import asyncio
import pyshark
import threading
from typing import Optional
from worker import PacketWorker


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