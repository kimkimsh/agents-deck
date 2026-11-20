import json
import unittest

from agents_deck.model.background_kind import BackgroundKind
from agents_deck.model.background_task import BackgroundTask
from agents_deck.model.phase import Phase
from agents_deck.model.snapshot import Snapshot
from agents_deck.model.tool_activity import ToolActivity
from agents_deck.model.tool_category import ToolCategory
from agents_deck.model.wait_reason import WaitReason
from agents_deck.tablet.snapshot_codec import SnapshotCodec
from tests.session_factory import PANE, makeSession


class SnapshotCodecTest(unittest.TestCase):
    def testNoFreeTextLeavesTheMachine(self):
        tTask = BackgroundTask(mId="b1", mKind=BackgroundKind.PROCESS, mProcessName="secretproc")
        tSession = makeSession(Phase.WAITING, 10.0, ToolActivity(mName="mcp__secret-server__query", mCategory=ToolCategory.OTHER), WaitReason.PERMISSION, (tTask,), True)
        tText = SnapshotCodec().encode(Snapshot(mGeneratedAt=11.0, mWarpRunning=True, mSessions=(tSession,)), [])
        self.assertNotIn("secret", tText)
        tSessionJson = json.loads(tText)["sessions"][0]
        self.assertEqual(tSessionJson["pane"], PANE)
        self.assertEqual(tSessionJson["phase"], "waiting")
        self.assertEqual(tSessionJson["waitingFor"], "permission")
        self.assertEqual(tSessionJson["background"], {"known": True, "count": 1, "kinds": ["process"]})
        self.assertEqual(tSessionJson["toolCategory"], "other")
        self.assertNotIn("tool", tSessionJson)

    def testHiddenBackgroundSendsNoCount(self):
        tTask = BackgroundTask(mId="b1", mKind=BackgroundKind.SHELL, mProcessName=None)
        tSession = makeSession(Phase.THINKING, 10.0, None, None, (tTask,), False)
        tSessionJson = json.loads(SnapshotCodec().encode(Snapshot(mGeneratedAt=11.0, mWarpRunning=True, mSessions=(tSession,)), []))["sessions"][0]
        self.assertEqual(tSessionJson["background"], {"known": False, "count": None, "kinds": None})
