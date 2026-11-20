import unittest

from agents_deck.discovery.pane_scanner import PaneScanner
from agents_deck.discovery.process_info import ProcessInfo
from agents_deck.model.agent_kind import AgentKind
from tests.fakes.fake_process_table import FakeProcessTable

PANE = "0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f"
OTHER = "1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e"
TTY = 34817
SERVER = 10
SHELL = 20
PANE_VAR = "WARP_TERMINAL_SESSION_UUID"


def proc(pid: int, ppid: int, comm: str, pgrp: int, tpgid: int, tty: int = TTY) -> ProcessInfo:
    return ProcessInfo(mPid=pid, mPpid=ppid, mComm=comm, mPgrp=pgrp, mTtyNr=tty, mTpgid=tpgid, mStartTicks=pid)


class PaneScannerTest(unittest.TestCase):
    def setUp(self):
        self.mTable = FakeProcessTable()
        self.mTable.add(proc(SERVER, 1, "warp", SERVER, -1, tty=0), ["warp", "terminal-server"], {}, "/")
        self.mScanner = PaneScanner()

    def shell(self, environ, foreground: int):
        self.mTable.add(proc(SHELL, SERVER, "bash", SHELL, foreground), ["bash"], environ, "/home")

    def scan(self):
        return self.mScanner.scan(self.mTable, self.mScanner.warpServers(self.mTable))

    def testForegroundAgentWinsOverASuspendedOne(self):
        self.shell({PANE_VAR: PANE}, 40)
        self.mTable.add(proc(30, SHELL, "claude", 30, 40), ["claude"], {}, "/old")
        self.mTable.add(proc(40, SHELL, "codex", 40, 40), ["codex"], {}, "/new")
        tPanes = self.scan()
        self.assertEqual([(tPane.mAgent, tPane.mProcess.mPid) for tPane in tPanes], [(AgentKind.CODEX, 40)])

    def testPaneIdComesFromTheShellNotTheAgent(self):
        self.shell({PANE_VAR: PANE.upper()}, 30)
        self.mTable.add(proc(30, SHELL, "claude", 30, 30), ["claude"], {PANE_VAR: OTHER}, "/w")
        self.assertEqual([tPane.mPaneUuid for tPane in self.scan()], [PANE])

    def testMalformedPaneIdIsNotAPane(self):
        self.shell({PANE_VAR: "../../../x"}, 30)
        self.mTable.add(proc(30, SHELL, "claude", 30, 30), ["claude"], {}, "/w")
        self.assertEqual(self.scan(), [])

    def testCodexNonTuiModesAreNotPanes(self):
        self.shell({PANE_VAR: PANE}, 30)
        self.mTable.add(proc(30, SHELL, "codex", 30, 30), ["codex", "-c", "k=v", "review"], {}, "/w")
        self.assertEqual(self.scan(), [])

    def testCodexInAFolderNamedExecIsAPane(self):
        self.shell({PANE_VAR: PANE}, 30)
        self.mTable.add(proc(30, SHELL, "codex", 30, 30), ["codex", "-C", "exec"], {}, "/w")
        self.assertEqual([tPane.mAgent for tPane in self.scan()], [AgentKind.CODEX])

    def testAgentsUnderAnAgentAreItsWork(self):
        self.shell({PANE_VAR: PANE}, 30)
        self.mTable.add(proc(30, SHELL, "claude", 30, 31), ["claude"], {}, "/w")
        self.mTable.add(proc(31, 30, "codex", 31, 31), ["codex"], {}, "/w")
        self.assertEqual([tPane.mProcess.mPid for tPane in self.scan()], [30])

    def testAgentWhosePidWasReusedDuringTheScanIsNotAPane(self):
        self.mTable = ReusingProcessTable(30)
        self.mTable.add(proc(SERVER, 1, "warp", SERVER, -1, tty=0), ["warp", "terminal-server"], {}, "/")
        self.shell({PANE_VAR: PANE}, 30)
        self.mTable.add(proc(30, SHELL, "claude", 30, 30), ["claude"], {}, "/w")
        self.assertEqual(self.scan(), [])

    def testExecReplacedShellIsThePanesAgent(self):
        self.mTable.add(proc(SHELL, SERVER, "claude", SHELL, SHELL), ["claude"], {PANE_VAR: PANE}, "/w")
        self.assertEqual([(tPane.mAgent, tPane.mProcess.mPid) for tPane in self.scan()], [(AgentKind.CLAUDE, SHELL)])


class ReusingProcessTable(FakeProcessTable):
    """Reports one pid as a different process once metadata has been read,
    as when it exits and its pid is reused between refresh() and the reads."""

    mReusedPid: int

    def __init__(self, reusedPid: int):
        super().__init__()
        self.mReusedPid = reusedPid

    def isRunning(self, pid: int, startTicks: int) -> bool:
        return pid != self.mReusedPid and super().isRunning(pid, startTicks)


if __name__ == "__main__":
    unittest.main()
