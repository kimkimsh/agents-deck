import json
import os
import tempfile
import unittest

from agents_deck.adapters.claude_adapter import ClaudeAdapter
from agents_deck.adapters.label_sanitizer import LabelSanitizer
from agents_deck.adapters.tool_classifier import ToolClassifier
from agents_deck.discovery.pane_agent import PaneAgent
from agents_deck.discovery.process_info import ProcessInfo
from agents_deck.model.agent_kind import AgentKind
from agents_deck.model.phase import Phase

PID = 4242
START_TICKS = 777
SESSION = "5f0c9a52-1111-4222-8333-944455556666"


class ClaudeAdapterTest(unittest.TestCase):
    def setUp(self):
        self.mDir = tempfile.TemporaryDirectory()
        self.mSessions = os.path.join(self.mDir.name, "sessions")
        self.mProjects = os.path.join(self.mDir.name, "projects")
        os.makedirs(self.mSessions)
        os.makedirs(os.path.join(self.mProjects, "-work"))
        self.mTranscript = os.path.join(self.mProjects, "-work", SESSION + ".jsonl")
        self.mAdapter = ClaudeAdapter(self.mSessions, self.mProjects, ToolClassifier(), LabelSanitizer())
        self.mPane = PaneAgent(mPaneUuid="a" * 32, mAgent=AgentKind.CLAUDE, mProcess=ProcessInfo(mPid=PID, mPpid=1, mComm="claude", mPgrp=PID, mTtyNr=1, mTpgid=PID, mStartTicks=START_TICKS), mCwd="/work")

    def tearDown(self):
        self.mDir.cleanup()

    def writeRegistry(self, status: str):
        with open(os.path.join(self.mSessions, "%d.json" % PID), "w", encoding="utf-8") as tFile:
            json.dump({"pid": PID, "procStart": str(START_TICKS), "sessionId": SESSION, "status": status, "cwd": "/work"}, tFile)

    def writeTranscript(self, records):
        with open(self.mTranscript, "a", encoding="utf-8") as tFile:
            for tRecord in records:
                tFile.write(json.dumps(tRecord, separators=(",", ":")) + "\n")

    def testUnreadableTranscriptDropsEarlierTranscriptState(self):
        self.writeRegistry("busy")
        self.writeTranscript([
            {"type": "assistant", "message": {"stop_reason": "tool_use", "content": [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1"}]}, "toolUseResult": {"backgroundTaskId": "b1"}},
            {"type": "assistant", "message": {"stop_reason": "tool_use", "content": [{"type": "tool_use", "id": "t2", "name": "Edit", "input": {}}]}},
        ])
        tSeen = self.mAdapter.observe(self.mPane)
        self.assertEqual(tSeen.mPhase, Phase.TOOL)
        self.assertEqual(len(tSeen.mBackground), 1)
        os.unlink(self.mTranscript)
        tBlind = self.mAdapter.observe(self.mPane)
        self.assertEqual(tBlind.mPhase, Phase.THINKING)
        self.assertIsNone(tBlind.mTool)
        self.assertEqual(tBlind.mBackground, ())
        self.assertFalse(tBlind.mBackgroundKnown)


if __name__ == "__main__":
    unittest.main()
