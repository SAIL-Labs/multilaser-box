"""
Background polling of the power meters.

Each VISA query blocks until the meter answers (with averaging, or under a
slower driver, that can be tens to hundreds of ms). Polling from a QTimer
on the GUI thread therefore froze the window for most of every second.
:class:`MeterPoller` runs the reads on a worker thread and delivers them to
the GUI thread through a Qt signal.

It deliberately mimics the parts of QTimer the Power Meters tab used
(``start``, ``stop``, ``isActive``, ``setInterval``) so call sites stay
the same.

Results from before a ``stop()`` or ``invalidate()`` are dropped, so a
frozen display or a role change never receives a stale reading.
"""

import logging
import threading
import time
from typing import Callable, Optional, Tuple

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class MeterPoller(QObject):
    """Calls ``read_fn`` repeatedly on a worker thread.

    Signals:
        readings(tuple): the value returned by ``read_fn``
        timing(float, float): (seconds the read took, requested interval s)
    """

    readings = pyqtSignal(object)
    timing = pyqtSignal(float, float)
    _result = pyqtSignal(int, object, float)   # (generation, value, elapsed)

    def __init__(self, read_fn: Callable[[], Tuple], parent: Optional[QObject] = None):
        super().__init__(parent)
        self._read_fn = read_fn
        self._interval_s = 0.1
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._generation = 0
        self._active = False
        self._result.connect(self._deliver)

    # --- QTimer-like interface -------------------------------------------

    def setInterval(self, ms: int) -> None:
        self._interval_s = max(ms, 1) / 1000.0

    def interval(self) -> int:
        return int(self._interval_s * 1000)

    def isActive(self) -> bool:
        return self._active

    def start(self) -> None:
        if self._active:
            return
        self._generation += 1
        self._active = True
        self._stop = threading.Event()          # one per worker thread
        self._thread = threading.Thread(
            target=self._run, args=(self._stop,), name="meter-poller", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop polling and wait for any read in progress to finish.

        Waiting matters: callers go on to reconfigure or close the meters.
        """
        if not self._active:
            return
        self._active = False
        self._generation += 1      # drop anything still queued
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=5.0)
            if thread.is_alive():
                logger.warning("Power meter poll still running after 5 s")

    def invalidate(self) -> None:
        """Discard readings whose read began before now (e.g. role change).

        Doesn't block: the read in flight finishes but is dropped.
        """
        self._generation += 1

    # --- worker ------------------------------------------------------------

    def _run(self, stop: threading.Event) -> None:
        while not stop.is_set():
            generation = self._generation   # stamp at the start of the read
            start = time.monotonic()
            try:
                value = self._read_fn()
            except Exception as e:  # keep polling; report like the old timer did
                logger.error(f"Error reading power meters: {e}")
                value = None
            elapsed = time.monotonic() - start
            if stop.is_set():
                break
            if value is not None:
                self._result.emit(generation, value, elapsed)
            # Wait out the rest of the interval (at least a short breather
            # so the GUI thread can take the meter lock for settings changes)
            stop.wait(max(self._interval_s - elapsed, 0.005))

    def _deliver(self, generation: int, value, elapsed: float) -> None:
        if generation != self._generation or not self._active:
            return
        self.timing.emit(elapsed, self._interval_s)
        self.readings.emit(value)
