from dataclasses import dataclass

from agents_deck.discovery.process_info import ProcessInfo
from agents_deck.model.agent_kind import AgentKind


@dataclass(frozen=True)
class PaneAgent:
    """The agent process found under one Warp pane shell."""

    mPaneUuid: str
    mAgent: AgentKind
    mProcess: ProcessInfo
    mCwd: str
