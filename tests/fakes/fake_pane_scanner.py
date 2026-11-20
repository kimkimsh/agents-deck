from typing import List

from agents_deck.discovery.pane_agent import PaneAgent
from agents_deck.discovery.pane_scanner import PaneScanner
from agents_deck.discovery.process_info import ProcessInfo
from agents_deck.discovery.process_table import ProcessTable


class FakePaneScanner(PaneScanner):
    """Reports a fixed list of panes under one pretend Warp server."""

    mPanes: List[PaneAgent]

    def __init__(self, panes: List[PaneAgent]):
        self.mPanes = panes

    def warpServers(self, table: ProcessTable) -> List[ProcessInfo]:
        return [ProcessInfo(mPid=1, mPpid=0, mComm="warp", mPgrp=1, mTtyNr=0, mTpgid=-1, mStartTicks=1)]

    def scan(self, table: ProcessTable, warpServers: List[ProcessInfo]) -> List[PaneAgent]:
        return list(self.mPanes)
