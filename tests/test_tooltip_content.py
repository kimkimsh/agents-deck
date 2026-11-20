import unittest

from agents_deck.model.background_kind import BackgroundKind
from agents_deck.model.background_task import BackgroundTask
from agents_deck.model.phase import Phase
from agents_deck.model.tool_activity import ToolActivity
from agents_deck.model.tool_category import ToolCategory
from agents_deck.ui.tooltip_content import TooltipContent
from tests.session_factory import makeSession


class TooltipContentTest(unittest.TestCase):
    NOW = 5000.0

    def lines(self, session, stale: bool):
        return TooltipContent().forSession(session, self.NOW, stale).mLines

    def testMcpToolNameIsReadable(self):
        tSession = makeSession(Phase.TOOL, self.NOW, ToolActivity("mcp__github__create_issue", ToolCategory.OTHER), None, (), True)
        self.assertEqual(self.lines(tSession, False)[0], "Claude Code · Running create_issue (github)")

    def testBackgroundSummaryCountsKindsAndListsOnlyProcessNames(self):
        tTasks = (BackgroundTask(mId="b1", mKind=BackgroundKind.SHELL, mProcessName=None), BackgroundTask(mId="a1", mKind=BackgroundKind.AGENT, mProcessName=None))
        tTasks += tuple(BackgroundTask(mId=str(tIndex), mKind=BackgroundKind.PROCESS, mProcessName="proc%d" % tIndex) for tIndex in range(6))
        tLines = self.lines(makeSession(Phase.IDLE, self.NOW, None, None, tTasks, True), False)
        self.assertEqual(tLines[1], "Background: 1 shell, 1 agent, 6 processes")
        self.assertEqual(tLines[2:6], ("· proc0", "· proc1", "· proc2", "· proc3"))
        self.assertEqual(tLines[6], "+2 more")

    def testUnknownBackgroundIsNotReportedAsNone(self):
        tLines = self.lines(makeSession(Phase.THINKING, self.NOW, None, None, (), False), False)
        self.assertIn("Background work not visible", tLines)
        self.assertNotIn("No background tasks", tLines)

    def testIdleDurationAndSleep(self):
        self.assertEqual(self.lines(makeSession(Phase.IDLE, self.NOW - 125, None, None, (), True), False)[0], "Claude Code · Idle for 2 min")
        self.assertEqual(self.lines(makeSession(Phase.IDLE, self.NOW - 3900, None, None, (), True), False)[0], "Claude Code · Asleep, idle for 1 h 5 min")

    def testStaleNoteIsShown(self):
        self.assertIn(TooltipContent.STALE_NOTE, self.lines(makeSession(Phase.IDLE, self.NOW, None, None, (), True), True))
