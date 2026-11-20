from dataclasses import dataclass
from typing import Tuple

from agents_deck.model.session_state import SessionState


@dataclass(frozen=True)
class Snapshot:
    """Every live session at one instant; handed from the collector thread to the UI."""

    mGeneratedAt: float
    mWarpRunning: bool
    mSessions: Tuple[SessionState, ...]
