from typing import Dict, Optional, Sequence, Tuple

from agents_deck.discovery.process_info import ProcessInfo
from agents_deck.discovery.process_table import ProcessTable


class FakeProcessTable(ProcessTable):
    """A process table that never reads /proc; tests add processes to it."""

    mArgv: Dict[int, Tuple[str, ...]]
    mEnviron: Dict[int, Dict[str, str]]
    mCwds: Dict[int, str]

    def __init__(self):
        self.mProcRoot = ""
        self.mProcesses = {}
        self.mChildren = {}
        self.mBootTime = 0.0
        self.mTicksPerSecond = 100
        self.mArgv = {}
        self.mEnviron = {}
        self.mCwds = {}

    def add(self, info: ProcessInfo, argv: Sequence[str], environ: Dict[str, str], cwd: str):
        self.mProcesses[info.mPid] = info
        self.mChildren.setdefault(info.mPpid, []).append(info.mPid)
        self.mArgv[info.mPid] = tuple(argv)
        self.mEnviron[info.mPid] = dict(environ)
        self.mCwds[info.mPid] = cwd

    def refresh(self):
        pass

    def isRunning(self, pid: int, startTicks: int) -> bool:
        tInfo = self.mProcesses.get(pid)
        return tInfo is not None and tInfo.mStartTicks == startTicks

    def startTimeSeconds(self, info: ProcessInfo) -> Optional[float]:
        return 0.0

    def readArgv(self, pid: int) -> Optional[Tuple[str, ...]]:
        return self.mArgv.get(pid)

    def readEnviron(self, pid: int, names: Sequence[str]) -> Optional[Dict[str, str]]:
        tEnviron = self.mEnviron.get(pid)
        if tEnviron is None:
            return None
        return {tName: tEnviron[tName] for tName in names if tName in tEnviron}

    def readCwd(self, pid: int) -> Optional[str]:
        return self.mCwds.get(pid)
