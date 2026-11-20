import logging
import threading
import traceback
from typing import Set


class OnceLogger:
    """Logs an exception's traceback the first time it is raised from a given
    code location, and a warning the first time its context reports one, so a
    failure repeated every poll is reported once.

    Shared by the collector thread and the UI thread.
    """

    mLogger: logging.Logger
    mSeen: Set[str]
    mLock: threading.Lock

    def __init__(self, logger: logging.Logger):
        self.mLogger = logger
        self.mSeen = set()
        self.mLock = threading.Lock()

    def exception(self, context: str, error: BaseException):
        tFrames = traceback.extract_tb(error.__traceback__)
        tWhere = "%s:%d" % (tFrames[-1].filename, tFrames[-1].lineno) if tFrames else "?"
        tKey = "%s|%s|%s" % (context, type(error).__name__, tWhere)
        with self.mLock:
            if tKey in self.mSeen:
                return
            self.mSeen.add(tKey)
        self.mLogger.error("%s failed; further identical failures are not logged", context, exc_info=error)

    def warning(self, context: str, message: str):
        with self.mLock:
            if context in self.mSeen:
                return
            self.mSeen.add(context)
        self.mLogger.warning("%s: %s", context, message)
