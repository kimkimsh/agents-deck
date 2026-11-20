from typing import Iterable, Set, Tuple

from agents_deck.adapters.claude_adapter import ClaudeAdapter
from agents_deck.discovery.pane_agent import PaneAgent
from agents_deck.model.agent_observation import AgentObservation


class FakeClaudeAdapter(ClaudeAdapter):
    """Raises for the panes named in `failing`; otherwise reports a fixed observation."""

    mFailing: Set[str]
    mObservation: AgentObservation

    def __init__(self, failing: Set[str], observation: AgentObservation):
        self.mFailing = failing
        self.mObservation = observation

    def observe(self, paneAgent: PaneAgent) -> AgentObservation:
        if paneAgent.mPaneUuid in self.mFailing:
            raise KeyError("synthetic adapter failure")
        return self.mObservation

    def prune(self, liveKeys: Iterable[Tuple[int, int]]):
        pass
