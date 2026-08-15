import threading
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Stats:
    packets_processed: int = 0
    messages_to_discord: int = 0
    messages_to_game: int = 0
    errors: int = 0
    start_time: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def increment(self, key: str, value: int = 1) -> None:
        with self._lock:
            setattr(self, key, getattr(self, key) + value)

    def get_uptime_str(self) -> str:
        with self._lock:
            uptime = time.time() - self.start_time
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "packets_processed": self.packets_processed,
                "messages_to_discord": self.messages_to_discord,
                "messages_to_game": self.messages_to_game,
                "errors": self.errors,
                "start_time": self.start_time,
            }


stats = Stats()
stats_lock = stats._lock