import json
import os
import tempfile
import time
import unittest

from agents_deck.adapters.agy_adapter import AgyAdapter
from agents_deck.adapters.tool_classifier import ToolClassifier
from agents_deck.discovery.pane_agent import PaneAgent
from agents_deck.discovery.process_info import ProcessInfo
from agents_deck.model.agent_kind import AgentKind
from agents_deck.model.phase import Phase
from agents_deck.model.tool_category import ToolCategory

CONVERSATION = "0d6a1f6e-3c2b-4a59-9e51-7b9f1c2d3e4f"


class AgyAdapterTest(unittest.TestCase):
    def setUp(self):
        self.mDir = tempfile.TemporaryDirectory()
        self.mRoot = self.mDir.name
        os.makedirs(os.path.join(self.mRoot, "log"))
        self.mAdapter = AgyAdapter(self.mRoot, ToolClassifier())

    def tearDown(self):
        self.mDir.cleanup()

    def writeLog(self, started: float, pid: int, body: str) -> str:
        tName = time.strftime("cli-%Y%m%d_%H%M%S.log", time.localtime(started))
        tPath = os.path.join(self.mRoot, "log", tName)
        with open(tPath, "w", encoding="utf-8") as tFile:
            tFile.write("I1120 21:00:00.000000 %d main.go:1] started\n" % pid)
            tFile.write(body)
        return tPath

    def testPlannerWithToolCallIsTool(self):
        tObservation = self.mAdapter._fromStep({"type": "PLANNER_RESPONSE", "status": "DONE", "tool_calls": [{"name": "run_command"}]})
        self.assertEqual(tObservation.mPhase, Phase.TOOL)
        assert tObservation.mTool is not None
        self.assertEqual(tObservation.mTool.mCategory, ToolCategory.SHELL)

    def testPlannerWithoutCallsIsIdle(self):
        self.assertEqual(self.mAdapter._fromStep({"type": "PLANNER_RESPONSE", "status": "DONE", "tool_calls": []}).mPhase, Phase.IDLE)

    def testErrorStatusIsError(self):
        self.assertEqual(self.mAdapter._fromStep({"type": "RUN_COMMAND", "status": "ERROR"}).mPhase, Phase.ERROR)

    def testUserInputIsThinking(self):
        tObservation = self.mAdapter._fromStep({"type": "USER_INPUT", "status": "DONE"})
        self.assertEqual(tObservation.mPhase, Phase.THINKING)
        self.assertFalse(tObservation.mBackgroundKnown)

    def testLogIsFoundByPidAndNotBeforeTheProcessStarted(self):
        tNow = time.time()
        self.writeLog(tNow - 3600, 4242, "")
        tOwn = self.writeLog(tNow - 10, 4242, "")
        self.assertEqual(self.mAdapter._findLog(4242, tNow - 10), tOwn)
        self.assertIsNone(self.mAdapter._findLog(4243, tNow - 10))

    def conversationOf(self, body: str, pid: int):
        # One log per pid: log names have one-second resolution.
        tPath = self.writeLog(time.time() + pid, pid, body)
        self.assertTrue(self.mAdapter._readLog(tPath, pid))
        return self.mAdapter.mConversations.get(tPath)

    def testConversationIdMustBeAUuid(self):
        tTraversal = "../../../../etc/passwd" + "x" * 14
        self.assertIsNone(self.conversationOf("I1120 21:00:01.000000 1 server.go:755] Streaming conversation %s\n" % tTraversal, 1))

    def testOnlyTheExactGlogLineFromThisPidNamesTheConversation(self):
        tSpoof = "I1120 21:00:01.000000 7 handler.go:12] User message: Streaming conversation %s\n" % CONVERSATION
        self.assertIsNone(self.conversationOf(tSpoof, 7))
        tOtherPid = "I1120 21:00:01.000000 8 server.go:755] Created conversation %s\n" % CONVERSATION
        self.assertIsNone(self.conversationOf(tOtherPid, 9))
        tReal = "I1120 21:00:01.000000 10 conversation_manager.go:378] Streaming conversation %s\n" % CONVERSATION
        self.assertEqual(self.conversationOf(tReal, 10), CONVERSATION)

    def testLaterConversationLineWins(self):
        tSecond = "1" + CONVERSATION[1:]
        tBody = "I1120 21:00:01.000000 3 server.go:755] Created conversation %s\nI1120 21:00:09.000000 3 server.go:755] Created conversation %s\n" % (CONVERSATION, tSecond)
        self.assertEqual(self.conversationOf(tBody, 3), tSecond)

    def testUnreadableLogIsUnknownNotIdle(self):
        tNow = time.time()
        tPath = self.writeLog(tNow, 4242, "")
        tPane = PaneAgent(mPaneUuid="a" * 32, mAgent=AgentKind.AGY, mProcess=ProcessInfo(mPid=4242, mPpid=1, mComm="agy", mPgrp=4242, mTtyNr=1, mTpgid=4242, mStartTicks=1), mCwd="/w")
        self.assertEqual(self.mAdapter.observe(tPane, tNow).mPhase, Phase.IDLE)
        os.chmod(tPath, 0)
        try:
            self.assertEqual(AgyAdapter(self.mRoot, ToolClassifier()).observe(tPane, tNow).mPhase, Phase.UNKNOWN)
        finally:
            os.chmod(tPath, 0o600)

    def testNewestStepWinsAndMetaStepsAreSkipped(self):
        tDir = os.path.join(self.mRoot, "brain", CONVERSATION, ".system_generated", "logs")
        os.makedirs(tDir)
        with open(os.path.join(tDir, "transcript.jsonl"), "w", encoding="utf-8") as tFile:
            for tRecord in ({"step_index": 0, "type": "USER_INPUT", "status": "DONE", "content": "secret prompt"},
                            {"step_index": 1, "type": "PLANNER_RESPONSE", "status": "DONE", "tool_calls": [{"name": "view_file", "args": {"path": "/x"}}]},
                            {"step_index": 2, "type": "CONVERSATION_HISTORY", "status": "DONE"}):
                tFile.write(json.dumps(tRecord) + "\n")
        self.assertTrue(self.mAdapter._readSteps(CONVERSATION))
        tIndex, tStep = self.mAdapter.mNewestSteps[CONVERSATION]
        self.assertEqual(tIndex, 1)
        self.assertEqual(tStep, {"type": "PLANNER_RESPONSE", "status": "DONE", "tool_calls": [{"name": "view_file"}]})
