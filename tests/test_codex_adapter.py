import os
import tempfile
import unittest

from agents_deck.adapters.codex_adapter import CodexAdapter
from agents_deck.adapters.codex_link import CodexLink
from agents_deck.adapters.codex_link_resolver import CodexLinkResolver
from agents_deck.adapters.codex_thread_index import CodexThreadIndex
from agents_deck.adapters.codex_tui_registry import CodexTuiRegistry
from agents_deck.adapters.label_sanitizer import LabelSanitizer
from agents_deck.adapters.tool_classifier import ToolClassifier
from agents_deck.discovery.pane_agent import PaneAgent
from agents_deck.discovery.process_info import ProcessInfo
from agents_deck.model.agent_kind import AgentKind
from agents_deck.model.link_confidence import LinkConfidence
from agents_deck.model.phase import Phase

TUI_PID = 30
THREAD = "019a0000-0000-7000-8000-000000000001"
PANE = "0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f"
APP_START = 0.0


class CodexAdapterTest(unittest.TestCase):
    """observe() for a TUI whose link was already decided; no rollout exists on disk."""

    def setUp(self):
        self.mDir = tempfile.TemporaryDirectory()
        self.mIndex = CodexThreadIndex(os.path.join(self.mDir.name, "markers"), os.path.join(self.mDir.name, "sessions"), os.path.join(self.mDir.name, "state.sqlite"))
        self.mAdapter = CodexAdapter(CodexTuiRegistry(APP_START), self.mIndex, CodexLinkResolver(), ToolClassifier(), LabelSanitizer(), APP_START)
        self.mAdapter.mLinks = {(TUI_PID, TUI_PID): CodexLink(mThreadId=THREAD, mConfidence=LinkConfidence.INFERRED)}
        tProcess = ProcessInfo(mPid=TUI_PID, mPpid=1, mComm="codex", mPgrp=TUI_PID, mTtyNr=1, mTpgid=TUI_PID, mStartTicks=TUI_PID)
        self.mPane = PaneAgent(mPaneUuid=PANE, mAgent=AgentKind.CODEX, mProcess=tProcess, mCwd="/w")

    def tearDown(self):
        self.mDir.cleanup()

    def testPersistedThreadWithoutARolloutIsUnknown(self):
        self.mIndex.mCwds[THREAD] = "/w"
        tObservation = self.mAdapter.observe(self.mPane)
        self.assertIs(tObservation.mPhase, Phase.UNKNOWN)
        self.assertFalse(tObservation.mBackgroundKnown)

    def testThreadNotPersistedYetIsIdle(self):
        tObservation = self.mAdapter.observe(self.mPane)
        self.assertIs(tObservation.mPhase, Phase.IDLE)
        self.assertIs(tObservation.mConfidence, LinkConfidence.INFERRED)


if __name__ == "__main__":
    unittest.main()
