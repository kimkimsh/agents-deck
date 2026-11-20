from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessInfo:
    """One /proc entry. (mPid, mStartTicks) identifies a process across pid reuse.

    mTpgid is the foreground process group of the controlling terminal; the
    process is that terminal's foreground job when it equals mPgrp.
    """

    mPid: int
    mPpid: int
    mComm: str
    mPgrp: int
    mTtyNr: int
    mTpgid: int
    mStartTicks: int

    def isForeground(self) -> bool:
        return self.mPgrp == self.mTpgid
