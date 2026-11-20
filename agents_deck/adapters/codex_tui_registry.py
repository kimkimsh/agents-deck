from typing import Dict, List, Tuple

from agents_deck.adapters.codex_tui import CodexTui
from agents_deck.constants.process_constants import ProcessConstants
from agents_deck.constants.timing_constants import TimingConstants
from agents_deck.discovery.codex_cli import CodexCli
from agents_deck.discovery.process_table import ProcessTable


class CodexTuiRegistry:
    """Lifetimes of every interactive Codex TUI on the machine, Warp or not.

    Attach markers are credited by "which TUIs were alive at that moment", so
    TUIs outside Warp count too, and a TUI that exited is remembered for
    TimingConstants.CODEX_TUI_MEMORY_SECONDS. Owned by the collector thread.
    """

    mAppStartTime: float
    mTuis: Dict[Tuple[int, int], CodexTui]

    def __init__(self, appStartTime: float):
        self.mAppStartTime = appStartTime
        self.mTuis = {}

    def update(self, table: ProcessTable, now: float) -> List[CodexTui]:
        tSeen = set()
        for tInfo in table.all():
            if tInfo.mComm != ProcessConstants.CODEX_COMM or tInfo.mTtyNr == ProcessConstants.NO_CONTROLLING_TTY:
                continue
            tKey = (tInfo.mPid, tInfo.mStartTicks)
            if tKey in self.mTuis:
                # Already classified; a process's mode never changes, and a
                # missed argv read must not end a lifetime.
                tSeen.add(tKey)
                continue
            tStart = table.startTimeSeconds(tInfo)
            if tStart is None:
                # Markers are credited by time; without a boot time no TUI can be placed.
                continue
            tArgv = table.readArgv(tInfo.mPid)
            if tArgv is None or not CodexCli.isTui(tArgv):
                continue
            tCwd = table.readCwd(tInfo.mPid)
            if not table.isRunning(tInfo.mPid, tInfo.mStartTicks):
                continue
            tSeen.add(tKey)
            self.mTuis[tKey] = CodexTui(
                mPid=tInfo.mPid,
                mStartTicks=tInfo.mStartTicks,
                mStartTime=tStart,
                mCwd=tCwd,
                mEndTime=None,
                mAliveAtAppStart=tStart <= self.mAppStartTime,
            )
        for tKey, tTui in list(self.mTuis.items()):
            if tKey in tSeen:
                continue
            if tTui.mEndTime is None:
                self.mTuis[tKey] = CodexTui(
                    mPid=tTui.mPid,
                    mStartTicks=tTui.mStartTicks,
                    mStartTime=tTui.mStartTime,
                    mCwd=tTui.mCwd,
                    mEndTime=now,
                    mAliveAtAppStart=tTui.mAliveAtAppStart,
                )
            elif now - tTui.mEndTime > TimingConstants.CODEX_TUI_MEMORY_SECONDS:
                del self.mTuis[tKey]
        return list(self.mTuis.values())
