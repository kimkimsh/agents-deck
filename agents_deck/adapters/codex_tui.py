from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CodexTui:
    """One interactive Codex TUI process as known to the linker.

    mEndTime is None while the process is alive; otherwise the poll time at
    which it was first seen gone (an upper bound on its exit).
    """

    mPid: int
    mStartTicks: int
    mStartTime: float
    mCwd: Optional[str]
    mEndTime: Optional[float]
    mAliveAtAppStart: bool
