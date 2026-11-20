import unittest

from agents_deck.adapters.codex_tui_registry import CodexTuiRegistry
from agents_deck.discovery.process_info import ProcessInfo
from tests.fakes.fake_process_table import FakeProcessTable

TTY = 34817
TUI_PID = 30
APP_START = 0.0


class CodexTuiRegistryTest(unittest.TestCase):
    def setUp(self):
        self.mTable = FakeProcessTable()
        self.mTable.add(ProcessInfo(mPid=TUI_PID, mPpid=1, mComm="codex", mPgrp=TUI_PID, mTtyNr=TTY, mTpgid=TUI_PID, mStartTicks=TUI_PID), ["codex"], {}, "/w")
        self.mRegistry = CodexTuiRegistry(APP_START)

    def endTimes(self, now: float):
        return [tTui.mEndTime for tTui in self.mRegistry.update(self.mTable, now)]

    def testAMissedArgvReadDoesNotEndALiveTui(self):
        self.assertEqual(self.endTimes(1.0), [None])
        del self.mTable.mArgv[TUI_PID]
        self.assertEqual(self.endTimes(2.0), [None])

    def testAnExitedTuiIsEndedAndRemembered(self):
        self.endTimes(1.0)
        del self.mTable.mProcesses[TUI_PID]
        self.assertEqual(self.endTimes(2.0), [2.0])

    def testNonTuiModesAreNotRegistered(self):
        self.mTable.mArgv[TUI_PID] = ("codex", "exec", "x")
        self.assertEqual(self.endTimes(1.0), [])


if __name__ == "__main__":
    unittest.main()
