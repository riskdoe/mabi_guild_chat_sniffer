import os
import queue
import subprocess
import threading
import time
import logging
from dataclasses import dataclass
from typing import Optional

from stats import stats


logger = logging.getLogger(__name__)


def type_message(message: str, delay_seconds: float) -> None:
    # Search for and activate the game window
    os.system(f'xdotool search --name "Mabinogi" windowactivate')
    time.sleep(delay_seconds)
        
    os.system("xdotool key Return")
    time.sleep(delay_seconds)
    subprocess.run(["xdotool", "type", message], check=False)
    time.sleep(delay_seconds)
    os.system("xdotool key Return")
    time.sleep(delay_seconds)
    os.system("xdotool key Return")
    time.sleep(delay_seconds)


class ToClientWorker:
    def __init__(self,
     queue_maxsize: int = 1000,
     delay_seconds: float = 0.02):
        self._queue: queue.Queue[Optional[str]] = queue.Queue(maxsize=queue_maxsize)
        self._thread: Optional[threading.Thread] = None
        self._delay_seconds = delay_seconds
        logger.info(f"ToClientWorker initialized with queue max size: {queue_maxsize}")

    def _loop(self) -> None:
        logger.info("ToClientWorker thread started.")
        while True:
            item = self._queue.get()
            if item is None:
                logger.info("ToClientWorker received shutdown signal. Exiting.")
                self._queue.task_done()
                break

            try:
                type_message(item, delay_seconds=self._delay_seconds)
                # Increment stats for messages sent to game
                stats.increment('messages_to_game')
            except Exception as e:
                logger.exception(f"ToClientWorker error: {e}")
                # Increment error stats
                stats.increment('errors')
            finally:
                self._queue.task_done()

    def start(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        if self._thread and self._thread.is_alive():
            self._queue.put(None)
            self._thread.join(timeout=5)

    def enqueue(self, message: str) -> None:
        try:
            self._queue.put_nowait(message)
        except queue.Full:
            logger.warning("ToClientWorker queue full, dropping message.")