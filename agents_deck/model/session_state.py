from dataclasses import dataclass

from agents_deck.model.agent_kind import AgentKind
from agents_deck.model.agent_observation import AgentObservation


@dataclass(frozen=True)
class SessionState:
    """One tile: a Warp pane running an agent, as of one poll.

    Built only by the collector thread; read-only everywhere else.
    mPhaseSince is when mObservation.mPhase last changed.
    """

    mPaneUuid: str
    mAgent: AgentKind
    mPid: int
    mStartTicks: int
    mTitle: str
    mObservation: AgentObservation
    mPhaseSince: float
