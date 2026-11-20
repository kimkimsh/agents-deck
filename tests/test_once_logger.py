import logging
import unittest

from agents_deck.diagnostics.once_logger import OnceLogger


def failAt(message: str):
    raise ValueError(message)


class OnceLoggerTest(unittest.TestCase):
    def testSameFailureIsLoggedOnce(self):
        tLogger = logging.getLogger("agents_deck.test.once")
        tOnce = OnceLogger(tLogger)
        with self.assertLogs(tLogger, level="ERROR") as tCaptured:
            for tAttempt in range(3):
                try:
                    failAt("poll %d" % tAttempt)
                except ValueError as tError:
                    tOnce.exception("claude adapter", tError)
            try:
                failAt("other context")
            except ValueError as tError:
                tOnce.exception("codex adapter", tError)
        self.assertEqual(len(tCaptured.records), 2)
