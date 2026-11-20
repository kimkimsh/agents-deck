import os
from typing import Dict, List, Optional, Sequence, Tuple

from agents_deck.constants.process_constants import ProcessConstants
from agents_deck.discovery.process_info import ProcessInfo


class ProcessTable:
    """Point-in-time view of /proc.

    A process can exit between listing and reading; every reader returns
    None (or skips the entry) instead of raising for that race. A pid can
    also be reused in that gap, so a caller that acts on what it read
    confirms the identity afterwards with isRunning.

    mBootTime is None when /proc/stat has no boot time; process start times
    are then unknown, and nothing is attributed by time.
    """

    mProcRoot: str
    mProcesses: Dict[int, ProcessInfo]
    mChildren: Dict[int, List[int]]
    mBootTime: Optional[float]
    mTicksPerSecond: int

    def __init__(self, procRoot: str):
        self.mProcRoot = procRoot
        self.mProcesses = {}
        self.mChildren = {}
        self.mBootTime = self._readBootTime()
        self.mTicksPerSecond = os.sysconf("SC_CLK_TCK")

    def refresh(self):
        tProcesses: Dict[int, ProcessInfo] = {}
        tChildren: Dict[int, List[int]] = {}
        for tName in os.listdir(self.mProcRoot):
            if not tName.isdigit():
                continue
            tInfo = self._readStat(int(tName))
            if tInfo is None:
                continue
            tProcesses[tInfo.mPid] = tInfo
            tChildren.setdefault(tInfo.mPpid, []).append(tInfo.mPid)
        self.mProcesses = tProcesses
        self.mChildren = tChildren

    def all(self) -> List[ProcessInfo]:
        return list(self.mProcesses.values())

    def childrenOf(self, pid: int) -> List[ProcessInfo]:
        tResult = []
        for tChildPid in self.mChildren.get(pid, []):
            tInfo = self.mProcesses.get(tChildPid)
            if tInfo is not None:
                tResult.append(tInfo)
        return tResult

    def isRunning(self, pid: int, startTicks: int) -> bool:
        """Reads /proc now rather than the last refresh; touches no shared state."""
        tInfo = self._readStat(pid)
        return tInfo is not None and tInfo.mStartTicks == startTicks

    def startTimeSeconds(self, info: ProcessInfo) -> Optional[float]:
        if self.mBootTime is None:
            return None
        return self.mBootTime + info.mStartTicks / self.mTicksPerSecond

    def readArgv(self, pid: int) -> Optional[Tuple[str, ...]]:
        tRaw = self._readBytes(pid, "cmdline")
        if tRaw is None:
            return None
        return tuple(tPart.decode("utf-8", "replace") for tPart in tRaw.split(b"\0") if tPart)

    def readEnviron(self, pid: int, names: Sequence[str]) -> Optional[Dict[str, str]]:
        """The listed variables that are set, from one read; None if unreadable."""
        tRaw = self._readBytes(pid, "environ")
        if tRaw is None:
            return None
        tWanted = {tName.encode(): tName for tName in names}
        tResult: Dict[str, str] = {}
        for tEntry in tRaw.split(b"\0"):
            tKey, tSeparator, tValue = tEntry.partition(b"=")
            if tSeparator and tKey in tWanted:
                tResult[tWanted[tKey]] = tValue.decode("utf-8", "replace")
        return tResult

    def readCwd(self, pid: int) -> Optional[str]:
        try:
            return os.readlink(os.path.join(self.mProcRoot, str(pid), "cwd"))
        except OSError:
            return None

    def _readBytes(self, pid: int, entry: str) -> Optional[bytes]:
        try:
            with open(os.path.join(self.mProcRoot, str(pid), entry), "rb") as tFile:
                return tFile.read()
        except OSError:
            return None

    def _readStat(self, pid: int) -> Optional[ProcessInfo]:
        tRaw = self._readBytes(pid, "stat")
        if tRaw is None:
            return None
        tText = tRaw.decode("utf-8", "replace")
        # comm may itself contain spaces or ")", so split on the last ")".
        tOpen = tText.find("(")
        tClose = tText.rfind(")")
        if tOpen < 0 or tClose < tOpen:
            return None
        tFields = tText[tClose + 1:].split()
        if len(tFields) <= ProcessConstants.STAT_START_TICKS_INDEX:
            return None
        try:
            return ProcessInfo(
                mPid=pid,
                mPpid=int(tFields[ProcessConstants.STAT_PPID_INDEX]),
                mComm=tText[tOpen + 1:tClose],
                mPgrp=int(tFields[ProcessConstants.STAT_PGRP_INDEX]),
                mTtyNr=int(tFields[ProcessConstants.STAT_TTY_INDEX]),
                mTpgid=int(tFields[ProcessConstants.STAT_TPGID_INDEX]),
                mStartTicks=int(tFields[ProcessConstants.STAT_START_TICKS_INDEX]),
            )
        except ValueError:
            return None

    def _readBootTime(self) -> Optional[float]:
        try:
            with open(os.path.join(self.mProcRoot, "stat"), "r") as tFile:
                for tLine in tFile:
                    tFields = tLine.split()
                    if len(tFields) == 2 and tFields[0] == ProcessConstants.BOOT_TIME_KEY:
                        return float(tFields[1])
        except (OSError, ValueError):
            return None
        return None
