from agents_deck.adapters.codex_adapter import CodexAdapter
from agents_deck.discovery.pane_agent import PaneAgent
from agents_deck.discovery.process_table import ProcessTable
from agents_deck.model.agent_observation import AgentObservation


class FakeCodexAdapter(CodexAdapter):
    """Its link pass always fails, so observe() must never be reached."""

    def __init__(self):
        pass

    def beginPoll(self, table: ProcessTable, now: float):
        raise OSError("synthetic link pass failure")

    def observe(self, paneAgent: PaneAgent) -> AgentObservation:
        raise AssertionError("observe called after a failed link pass")

    def prune(self):
        pass
