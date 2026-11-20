import threading
import time
from typing import Callable, Optional

from agents_deck.collector import Collector
from agents_deck.constants.app_constants import AppConstants
from agents_deck.diagnostics.once_logger import OnceLogger
from agents_deck.model.snapshot import Snapshot


class CollectorThread:
    """Runs Collector.collectOnce on a daemon thread once per interval.

    `publish` is called on the collector thread and must hand the Snapshot to
    the UI thread itself (the app passes a GLib.idle_add wrapper). A poll that
    raises is logged and skipped; the UI sees snapshots stop arriving and
    shows the paused state, so a failing collector is never silent.
    """

    mCollector: Collector
    mPublish: Callable[[Snapshot], None]
    mInterval: float
    mErrors: OnceLogger
    mStop: threading.Event
    mThread: Optional[threading.Thread]

    def __init__(self, collector: Collector, publish: Callable[[Snapshot], None], interval: float, errors: OnceLogger):
        self.mCollector = collector
        self.mPublish = publish
        self.mInterval = interval
        self.mErrors = errors
        self.mStop = threading.Event()
        self.mThread = None

    def start(self):
        self.mThread = threading.Thread(target=self._run, name=AppConstants.COLLECTOR_THREAD_NAME, daemon=True)
        self.mThread.start()

    def stop(self):
        self.mStop.set()

    def _run(self):
        while True:
            self._pollOnce()
            if self.mStop.wait(self.mInterval):
                return

    def _pollOnce(self):
        try:
            tSnapshot = self.mCollector.collectOnce(time.time())
        except Exception as tError:
            self.mErrors.exception("collector poll", tError)
            return
        self.mPublish(tSnapshot)
