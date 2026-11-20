import argparse
import logging
import os
import sys
import time

from agents_deck.collector import Collector
from agents_deck.constants.app_constants import AppConstants
from agents_deck.diagnostics.once_logger import OnceLogger
from agents_deck.tablet.snapshot_codec import SnapshotCodec


def dumpSnapshot() -> int:
    tErrors = OnceLogger(logging.getLogger(AppConstants.LOGGER_NAME))
    tCollector = Collector.forHome(os.path.expanduser("~"), time.time(), tErrors)
    print(SnapshotCodec().encode(tCollector.collectOnce(time.time()), []))
    return 0


def runGui() -> int:
    # Imported here so --dump-snapshot works without a display.
    from agents_deck.ui.agents_deck_app import runApplication

    return runApplication()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    tParser = argparse.ArgumentParser(prog=AppConstants.APP_NAME, description="Animated status of the agent sessions running in Warp.")
    tParser.add_argument("--dump-snapshot", action="store_true", help="print one snapshot as JSON and exit")
    tArgs = tParser.parse_args()
    if tArgs.dump_snapshot:
        return dumpSnapshot()
    return runGui()


if __name__ == "__main__":
    sys.exit(main())
