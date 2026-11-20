import logging
import unittest

from agents_deck.adapters.agy_adapter import AgyAdapter
from agents_deck.adapters.label_sanitizer import LabelSanitizer
from agents_deck.adapters.tool_classifier import ToolClassifier
from agents_deck.collector import Collector
from agents_deck.diagnostics.once_logger import OnceLogger
from agents_deck.discovery.pane_agent import PaneAgent
from agents_deck.discovery.process_info import ProcessInfo
from agents_deck.model.agent_kind import AgentKind
from agents_deck.model.agent_observation import AgentObservation
from agents_deck.model.link_confidence import LinkConfidence
from agents_deck.model.phase import Phase
from tests.fakes.fake_claude_adapter import FakeClaudeAdapter
from tests.fakes.fake_codex_adapter import FakeCodexAdapter
from tests.fakes.fake_pane_scanner import FakePaneScanner
from tests.fakes.fake_process_table import FakeProcessTable

GOOD, BAD, CODEX = "1" * 32, "2" * 32, "3" * 32


def pane(paneUuid: str, agent: AgentKind, pid: int) -> PaneAgent:
    return PaneAgent(mPaneUuid=paneUuid, mAgent=agent, mProcess=ProcessInfo(mPid=pid, mPpid=1, mComm=agent.value, mPgrp=pid, mTtyNr=1, mTpgid=pid, mStartTicks=pid), mCwd="/work/" + agent.value + str(pid))


class CollectorFaultBoundaryTest(unittest.TestCase):
    def testOneFailingAdapterOnlyBlanksItsOwnSessions(self):
        tThinking = AgentObservation(mPhase=Phase.THINKING, mWaitingFor=None, mTool=None, mBackground=(), mBackgroundKnown=True, mConfidence=LinkConfidence.EXACT, mTitle=None)
        tLogger = logging.getLogger("agents_deck.test.collector")
        tCollector = Collector(
            FakeProcessTable(),
            FakePaneScanner([pane(GOOD, AgentKind.CLAUDE, 10), pane(BAD, AgentKind.CLAUDE, 11), pane(CODEX, AgentKind.CODEX, 12)]),
            FakeClaudeAdapter({BAD}, tThinking),
            FakeCodexAdapter(),
            AgyAdapter("/nonexistent", ToolClassifier()),
            LabelSanitizer(),
            OnceLogger(tLogger),
        )
        with self.assertLogs(tLogger, level="ERROR") as tCaptured:
            tSnapshot = tCollector.collectOnce(100.0)
        tPhases = {tSession.mPaneUuid: tSession.mObservation.mPhase for tSession in tSnapshot.mSessions}
        self.assertEqual(tPhases, {GOOD: Phase.THINKING, BAD: Phase.UNKNOWN, CODEX: Phase.UNKNOWN})
        self.assertEqual(len(tCaptured.records), 2)
        self.assertTrue(tSnapshot.mWarpRunning)
        self.assertEqual({tSession.mTitle for tSession in tSnapshot.mSessions}, {"claude10", "claude11", "codex12"})

    def testPhaseSinceSurvivesPollsUntilThePhaseChanges(self):
        tIdle = AgentObservation(mPhase=Phase.IDLE, mWaitingFor=None, mTool=None, mBackground=(), mBackgroundKnown=True, mConfidence=LinkConfidence.EXACT, mTitle=None)
        tClaude = FakeClaudeAdapter(set(), tIdle)
        tCollector = Collector(FakeProcessTable(), FakePaneScanner([pane(GOOD, AgentKind.CLAUDE, 10)]), tClaude, FakeCodexAdapter(), AgyAdapter("/nonexistent", ToolClassifier()), LabelSanitizer(), OnceLogger(logging.getLogger("agents_deck.test.since")))
        with self.assertLogs("agents_deck.test.since", level="ERROR"):
            self.assertEqual(tCollector.collectOnce(100.0).mSessions[0].mPhaseSince, 100.0)
            self.assertEqual(tCollector.collectOnce(105.0).mSessions[0].mPhaseSince, 100.0)
            tClaude.mObservation = AgentObservation.unknown()
            self.assertEqual(tCollector.collectOnce(110.0).mSessions[0].mPhaseSince, 110.0)
