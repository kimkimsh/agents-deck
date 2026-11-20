from dataclasses import dataclass
from typing import Optional, Tuple

from agents_deck.model.background_task import BackgroundTask
from agents_deck.model.link_confidence import LinkConfidence
from agents_deck.model.phase import Phase
from agents_deck.model.tool_activity import ToolActivity
from agents_deck.model.wait_reason import WaitReason


@dataclass(frozen=True)
class AgentObservation:
    """What one adapter could tell about one agent process in one poll.

    mBackgroundKnown False means the adapter could not see background work at
    all; an empty mBackground with mBackgroundKnown True means none is running.
    """

    mPhase: Phase
    mWaitingFor: Optional[WaitReason]
    mTool: Optional[ToolActivity]
    mBackground: Tuple[BackgroundTask, ...]
    mBackgroundKnown: bool
    mConfidence: LinkConfidence
    mTitle: Optional[str]

    @staticmethod
    def unknown() -> "AgentObservation":
        """Nothing could be observed: no phase, no background, no link."""
        return AgentObservation(
            mPhase=Phase.UNKNOWN,
            mWaitingFor=None,
            mTool=None,
            mBackground=(),
            mBackgroundKnown=False,
            mConfidence=LinkConfidence.UNKNOWN,
            mTitle=None,
        )
