from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from agents_deck.constants.process_constants import ProcessConstants
from agents_deck.constants.warp_constants import WarpConstants
from agents_deck.discovery.codex_cli import CodexCli
from agents_deck.discovery.pane_agent import PaneAgent
from agents_deck.discovery.process_info import ProcessInfo
from agents_deck.discovery.process_table import ProcessTable
from agents_deck.model.agent_kind import AgentKind


class PaneScanner:
    """Finds the agent running in each Warp pane.

    A pane is a child of the Warp `terminal-server` process; its agent is the
    shallowest descendant (the pane shell itself included, for `exec claude`)
    that is an agent and has a controlling terminal, preferring the
    terminal's foreground job over one suspended or sent to the background.
    Processes that merely inherited a Warp pane UUID (the Codex app-server
    daemon, VS Code extensions) are never reached because the walk only goes
    downward from pane shells. Deeper agents, such as `codex exec` run by a
    Claude Bash tool, are part of the outer agent's work and are not panes.

    The pane id comes from the pane shell, which Warp started; an agent's
    own environment can be rewritten by whatever launched it, and the id
    ends up in a `warp://` link.
    """

    AGENT_BY_COMM: Dict[str, AgentKind] = {
        ProcessConstants.CLAUDE_COMM: AgentKind.CLAUDE,
        ProcessConstants.CODEX_COMM: AgentKind.CODEX,
        ProcessConstants.AGY_COMM: AgentKind.AGY,
    }

    def scan(self, table: ProcessTable, warpServers: List[ProcessInfo]) -> List[PaneAgent]:
        tResult: List[PaneAgent] = []
        for tServer in warpServers:
            for tShell in table.childrenOf(tServer.mPid):
                tPaneAgent = self._scanPane(table, tShell)
                if tPaneAgent is not None:
                    tResult.append(tPaneAgent)
        return tResult

    def warpServers(self, table: ProcessTable) -> List[ProcessInfo]:
        tServers = []
        for tInfo in table.all():
            if tInfo.mComm != ProcessConstants.WARP_SERVER_COMM:
                continue
            tArgv = table.readArgv(tInfo.mPid)
            if tArgv is not None and ProcessConstants.WARP_SERVER_ARG in tArgv[1:2]:
                tServers.append(tInfo)
        return tServers

    def _scanPane(self, table: ProcessTable, shell: ProcessInfo) -> Optional[PaneAgent]:
        tPaneUuid = self._paneUuid(table, shell)
        if tPaneUuid is None:
            return None
        tAgent = self._paneAgent(table, shell)
        if tAgent is None:
            return None
        tKind, tProcess = tAgent
        tCwd = table.readCwd(tProcess.mPid)
        if not table.isRunning(shell.mPid, shell.mStartTicks) or not table.isRunning(tProcess.mPid, tProcess.mStartTicks):
            # A pid was reused while its files were read.
            return None
        return PaneAgent(mPaneUuid=tPaneUuid, mAgent=tKind, mProcess=tProcess, mCwd=tCwd or "")

    @staticmethod
    def _paneUuid(table: ProcessTable, shell: ProcessInfo) -> Optional[str]:
        tEnviron = table.readEnviron(shell.mPid, (ProcessConstants.WARP_PANE_UUID_VAR,))
        if tEnviron is None:
            return None
        tValue = tEnviron.get(ProcessConstants.WARP_PANE_UUID_VAR, "").lower()
        return tValue if WarpConstants.PANE_UUID_PATTERN.fullmatch(tValue) else None

    def _paneAgent(self, table: ProcessTable, shell: ProcessInfo) -> Optional[Tuple[AgentKind, ProcessInfo]]:
        """The shallowest foreground agent, else the shallowest agent."""
        tFirst: Optional[Tuple[AgentKind, ProcessInfo]] = None
        tQueue: Deque[Tuple[ProcessInfo, int]] = deque([(shell, 0)])
        while tQueue:
            tInfo, tDepth = tQueue.popleft()
            if tDepth > ProcessConstants.MAX_TREE_DEPTH:
                continue
            tKind = self._agentKindOf(table, tInfo)
            if tKind is not None and tInfo.mTtyNr != ProcessConstants.NO_CONTROLLING_TTY:
                if tInfo.isForeground():
                    return tKind, tInfo
                if tFirst is None:
                    tFirst = (tKind, tInfo)
                # An agent's own descendants are its work, not other panes' agents.
                continue
            for tChild in sorted(table.childrenOf(tInfo.mPid), key=self._startOrder):
                tQueue.append((tChild, tDepth + 1))
        return tFirst

    def _agentKindOf(self, table: ProcessTable, info: ProcessInfo) -> Optional[AgentKind]:
        tKind = self.AGENT_BY_COMM.get(info.mComm)
        if tKind is not AgentKind.CODEX:
            return tKind
        tArgv = table.readArgv(info.mPid)
        if tArgv is None or not CodexCli.isTui(tArgv):
            return None
        return tKind

    @staticmethod
    def _startOrder(info: ProcessInfo) -> int:
        return info.mStartTicks
