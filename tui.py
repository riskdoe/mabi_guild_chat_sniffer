import curses
import logging
import queue
import threading
import time
from typing import Optional

from stats import Stats, stats


class QueueHandler(logging.Handler):
    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue
        self.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            datefmt="%H:%M:%S"
        ))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.log_queue.put_nowait(self.format(record))
        except queue.Full:
            pass


class TUI:
    def __init__(
        self,
        log_queue: queue.Queue,
        max_log_lines: int = 100,
        stats_update_interval: float = 1.0,
    ):
        self.log_queue = log_queue
        self.max_log_lines = max_log_lines
        self.stats_update_interval = stats_update_interval
        self.log_lines: list[str] = []
        self.last_stats_update = 0.0
        self._shutdown = threading.Event()
        self._stdscr: Optional[curses.window] = None

    def run(self, stdscr: curses.window) -> None:
        self._stdscr = stdscr
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.timeout(100)

        self._draw_static()
        self._main_loop()

    def _draw_static(self) -> None:
        assert self._stdscr is not None
        self._stdscr.clear()
        self._draw_header()
        self._draw_separator(5)
        self._draw_log_header(7)
        self._stdscr.refresh()

    def _draw_header(self) -> None:
        assert self._stdscr is not None
        header = " Mabinogi Chat Sniffer - TUI "
        cols = curses.COLS
        if len(header) > cols - 1:
            header = header[:cols - 1]
        self._stdscr.attron(curses.A_BOLD)
        self._stdscr.addstr(0, 0, header.ljust(min(len(header), cols - 1), "="))
        self._stdscr.attroff(curses.A_BOLD)

    def _draw_separator(self, y: int) -> None:
        assert self._stdscr is not None
        if y < curses.LINES:
            sep = "=" * min(50, curses.COLS - 1)
            self._stdscr.addstr(y, 0, sep[:curses.COLS - 1])

    def _draw_log_header(self, y: int) -> None:
        assert self._stdscr is not None
        if y < curses.LINES:
            header = " Logs (most recent at bottom): "
            if len(header) > curses.COLS - 1:
                header = header[:curses.COLS - 1]
            self._stdscr.addstr(y, 0, header.ljust(min(len(header), curses.COLS - 1), "-"))

    def _main_loop(self) -> None:
        assert self._stdscr is not None
        while not self._shutdown.is_set():
            key = self._stdscr.getch()
            if key in (ord('q'), ord('Q')):
                self._shutdown.set()
                break

            self._process_logs()
            self._draw_stats()
            self._draw_logs()
            self._stdscr.refresh()
            time.sleep(0.05)

    def _process_logs(self) -> None:
        while True:
            try:
                record = self.log_queue.get_nowait()
                self.log_lines.append(record)
                if len(self.log_lines) > self.max_log_lines:
                    self.log_lines = self.log_lines[-self.max_log_lines:]
            except queue.Empty:
                break

    def _draw_stats(self) -> None:
        assert self._stdscr is not None
        current_time = time.time()
        if current_time - self.last_stats_update < self.stats_update_interval:
            return
        self.last_stats_update = current_time

        snap = stats.snapshot()
        uptime = stats.get_uptime_str()

        self._stdscr.addstr(2, 0, f"Uptime: {uptime}".ljust(curses.COLS - 1))
        self._stdscr.addstr(3, 0, f"Packets processed: {snap['packets_processed']}".ljust(curses.COLS - 1))
        self._stdscr.addstr(4, 0, f"Messages to Discord: {snap['messages_to_discord']}".ljust(curses.COLS - 1))
        self._stdscr.addstr(5, 0, f"Messages to game: {snap['messages_to_game']}".ljust(curses.COLS - 1))
        self._stdscr.addstr(6, 0, f"Errors: {snap['errors']}".ljust(curses.COLS - 1))

    def _draw_logs(self) -> None:
        assert self._stdscr is not None
        log_start_y = 8
        available = max(0, curses.LINES - log_start_y - 1)
        if available <= 0 or not self.log_lines:
            return

        displayed = self.log_lines[-available:]
        for i, line in enumerate(displayed):
            y = log_start_y + i
            if y >= curses.LINES - 1:
                break
            self._draw_wrapped_line(y, line)

    def _draw_wrapped_line(self, y: int, line: str) -> None:
        assert self._stdscr is not None
        cols = curses.COLS
        max_wraps = curses.LINES - y - 1
        if max_wraps <= 0:
            return

        remaining = line
        wrap_count = 0
        while remaining and wrap_count < max_wraps:
            if len(remaining) <= cols - 1:
                self._safe_addstr(y + wrap_count, 0, remaining)
                break
            wrap_at = cols - 1
            space_pos = remaining.rfind(' ', 0, wrap_at)
            if space_pos > wrap_at * 0.7:
                wrap_at = space_pos
            self._safe_addstr(y + wrap_count, 0, remaining[:wrap_at])
            remaining = remaining[wrap_at:].lstrip()
            wrap_count += 1

    def _safe_addstr(self, y: int, x: int, text: str) -> None:
        assert self._stdscr is not None
        if y < curses.LINES and x < curses.COLS:
            try:
                self._stdscr.addstr(y, x, text[:curses.COLS - x - 1])
            except curses.error:
                pass

    def shutdown(self) -> None:
        self._shutdown.set()


def create_queue_handler(log_queue: queue.Queue) -> QueueHandler:
    return QueueHandler(log_queue)