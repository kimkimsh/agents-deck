import unittest

from agents_deck.adapters.codex_link_resolver import CodexLinkResolver
from agents_deck.adapters.codex_tui import CodexTui
from agents_deck.model.link_confidence import LinkConfidence


def tui(pid: int, start: float, cwd: str, end=None, aliveAtStart=False) -> CodexTui:
    return CodexTui(mPid=pid, mStartTicks=pid * 10, mStartTime=start, mCwd=cwd, mEndTime=end, mAliveAtAppStart=aliveAtStart)


class CodexLinkResolverTest(unittest.TestCase):
    APP_START = 1000.0

    def setUp(self):
        self.mResolver = CodexLinkResolver()

    def update(self, tuis, markers, cwds):
        return self.mResolver.update(tuis, markers, cwds, self.APP_START)

    def testSingleLiveTuiIsInferredNeverExact(self):
        tLinks = self.update([tui(1, 1100.0, "/a")], [("t1", 1102.0)], {})
        self.assertEqual((tLinks[(1, 10)].mThreadId, tLinks[(1, 10)].mConfidence), ("t1", LinkConfidence.INFERRED))

    def testLaterAttachReplacesEarlierThread(self):
        tLinks = self.update([tui(1, 1100.0, "/a")], [("t2", 1300.0), ("t1", 1102.0)], {})
        self.assertEqual(tLinks[(1, 10)].mThreadId, "t2")

    def testTwoTuisSplitByCwd(self):
        tLinks = self.update([tui(1, 1100.0, "/a"), tui(2, 1100.0, "/b")], [("t1", 1200.0)], {"t1": "/b"})
        self.assertEqual((tLinks[(2, 20)].mThreadId, tLinks[(2, 20)].mConfidence), ("t1", LinkConfidence.INFERRED))
        self.assertIsNone(tLinks[(1, 10)].mThreadId)

    def testTwoTuisInOneFolderStayUnknown(self):
        tLinks = self.update([tui(1, 1100.0, "/a"), tui(2, 1100.0, "/a")], [("t1", 1200.0)], {"t1": "/a"})
        self.assertIsNone(tLinks[(1, 10)].mThreadId)
        self.assertIsNone(tLinks[(2, 20)].mThreadId)

    def testExitedTuiIsNotCreditedAfterItsEnd(self):
        tLinks = self.update([tui(1, 1100.0, "/a", end=1150.0), tui(2, 1100.0, "/b")], [("t1", 1200.0)], {})
        self.assertEqual(tLinks[(2, 20)].mThreadId, "t1")

    def testMarkerBeforeATuiStartedIsNotItsOwn(self):
        tLinks = self.update([tui(1, 1100.0, "/a")], [("t0", 1050.0)], {})
        self.assertIsNone(tLinks[(1, 10)].mThreadId)

    def testPreStartMarkerInsideStartupWindowIsCredited(self):
        tLinks = self.update([tui(1, 900.0, "/a", aliveAtStart=True)], [("t1", 905.0)], {})
        self.assertEqual(tLinks[(1, 10)].mThreadId, "t1")

    def testOldPreStartMarkerNeedsMatchingCwd(self):
        tTuis = [tui(1, 500.0, "/a", aliveAtStart=True)]
        self.assertIsNone(CodexLinkResolver().update(tTuis, [("t1", 900.0)], {"t1": "/b"}, self.APP_START)[(1, 10)].mThreadId)
        self.assertEqual(CodexLinkResolver().update(tTuis, [("t1", 900.0)], {"t1": "/a"}, self.APP_START)[(1, 10)].mThreadId, "t1")

    def testForgettingAnExitedTuiDoesNotHandItsMarkerToASurvivor(self):
        tX, tZ = tui(1, 1100.0, "/a"), tui(2, 1110.0, "/a")
        tMarkers = [("x", 1102.0), ("z", 1112.0), ("x2", 1200.0)]
        tBefore = self.update([tX, tZ], tMarkers, {})
        tAfter = self.update([tZ], tMarkers, {})
        self.assertEqual(tAfter[(2, 20)], tBefore[(2, 20)])
        self.assertNotIn((1, 10), tAfter)

    def testNewTuiTakesItsStartupMarkerWithoutARow(self):
        tOld = tui(1, 1100.0, "/a")
        self.update([tOld], [("x", 1102.0)], {})
        tLinks = self.update([tOld, tui(2, 1500.0, "/a")], [("x", 1102.0), ("z", 1502.0)], {})
        self.assertEqual(tLinks[(1, 10)].mThreadId, "x")
        self.assertEqual(tLinks[(2, 20)].mThreadId, "z")

    def testAStartedTuiDoesNotTakeASecondMarkerInItsWindow(self):
        tA, tB = tui(1, 1100.0, "/a"), tui(2, 1120.0, "/b")
        tLinks = self.update([tA, tB], [("a", 1102.0), ("b", 1122.0)], {})
        self.assertEqual(tLinks[(1, 10)].mThreadId, "a")
        self.assertEqual(tLinks[(2, 20)].mThreadId, "b")

    def testUnchangedMarkerIsNotDecidedAgain(self):
        tA = tui(1, 1100.0, "/a")
        self.update([tA], [("a", 1102.0), ("b", 1300.0)], {})
        tLinks = self.update([tA, tui(2, 1290.0, "/b")], [("a", 1102.0), ("b", 1300.0)], {"b": "/b"})
        self.assertEqual(tLinks[(1, 10)].mThreadId, "b")
        self.assertIsNone(tLinks[(2, 20)].mThreadId)


if __name__ == "__main__":
    unittest.main()
