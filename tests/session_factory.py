from typing import Optional, Tuple

from agents_deck.model.agent_kind import AgentKind
from agents_deck.model.agent_observation import AgentObservation
from agents_deck.model.background_task import BackgroundTask
from agents_deck.model.link_confidence import LinkConfidence
from agents_deck.model.phase import Phase
from agents_deck.model.session_state import SessionState
from agents_deck.model.tool_activity import ToolActivity
from agents_deck.model.wait_reason import WaitReason

PANE = "0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f"


def makeSession(phase: Phase, phaseSince: float, tool: Optional[ToolActivity], waitingFor: Optional[WaitReason], background: Tuple[BackgroundTask, ...], backgroundKnown: bool) -> SessionState:
    """A session with a synthetic observation; title and pane are fixed test values."""
    tObservation = AgentObservation(
        mPhase=phase,
        mWaitingFor=waitingFor,
        mTool=tool,
        mBackground=background,
        mBackgroundKnown=backgroundKnown,
        mConfidence=LinkConfidence.EXACT,
        mTitle="secret-project-title",
    )
    return SessionState(mPaneUuid=PANE, mAgent=AgentKind.CLAUDE, mPid=100, mStartTicks=5, mTitle="secret-project-title", mObservation=tObservation, mPhaseSince=phaseSince)
