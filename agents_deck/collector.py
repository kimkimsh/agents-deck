import os
from typing import Dict, List, Optional, Tuple

from agents_deck.adapters.agy_adapter import AgyAdapter
from agents_deck.adapters.claude_adapter import ClaudeAdapter
from agents_deck.adapters.codex_adapter import CodexAdapter
from agents_deck.adapters.codex_link_resolver import CodexLinkResolver
from agents_deck.adapters.codex_thread_index import CodexThreadIndex
from agents_deck.adapters.codex_tui_registry import CodexTuiRegistry
from agents_deck.adapters.label_sanitizer import LabelSanitizer
from agents_deck.adapters.tool_classifier import ToolClassifier
from agents_deck.constants.path_constants import PathConstants
from agents_deck.constants.process_constants import ProcessConstants
from agents_deck.diagnostics.once_logger import OnceLogger
from agents_deck.discovery.pane_agent import PaneAgent
from agents_deck.discovery.pane_scanner import PaneScanner
from agents_deck.discovery.process_table import ProcessTable
from agents_deck.model.agent_kind import AgentKind
from agents_deck.model.agent_observation import AgentObservation
from agents_deck.model.phase import Phase
from agents_deck.model.session_state import SessionState
from agents_deck.model.snapshot import Snapshot


class Collector:
    """Turns one /proc scan plus the agents' state files into a Snapshot.

    Each adapter call is a fault boundary: the files read here belong to
    third-party tools whose formats change without notice, so an exception
    while observing one pane makes that pane unknown, with its traceback
    logged once, instead of stopping every tile.

    Owned by whichever thread calls collectOnce: the collector thread in the
    GUI, the main thread for --dump-snapshot.
    """

    mTable: ProcessTable
    mScanner: PaneScanner
    mClaude: ClaudeAdapter
    mCodex: CodexAdapter
    mAgy: AgyAdapter
    mSanitizer: LabelSanitizer
    mErrors: OnceLogger
    mPhaseSince: Dict[Tuple[str, int, int], Tuple[Phase, float]]

    def __init__(self, table: ProcessTable, scanner: PaneScanner, claude: ClaudeAdapter, codex: CodexAdapter, agy: AgyAdapter, sanitizer: LabelSanitizer, errors: OnceLogger):
        self.mTable = table
        self.mScanner = scanner
        self.mClaude = claude
        self.mCodex = codex
        self.mAgy = agy
        self.mSanitizer = sanitizer
        self.mErrors = errors
        self.mPhaseSince = {}

    @staticmethod
    def forHome(home: str, appStartTime: float, errors: OnceLogger) -> "Collector":
        """The collector wired to the real agent state under `home`."""
        tClassifier = ToolClassifier()
        tSanitizer = LabelSanitizer()
        tCodex = CodexAdapter(
            CodexTuiRegistry(appStartTime),
            CodexThreadIndex(os.path.join(home, PathConstants.CODEX_TUI_MARKERS), os.path.join(home, PathConstants.CODEX_SESSIONS), os.path.join(home, PathConstants.CODEX_STATE_DB)),
            CodexLinkResolver(),
            tClassifier,
            tSanitizer,
            appStartTime,
        )
        tTable = ProcessTable(ProcessConstants.PROC_ROOT)
        if tTable.mBootTime is None:
            errors.warning("process table", "no boot time in /proc/stat; Codex and Antigravity sessions are shown without state")
        return Collector(
            tTable,
            PaneScanner(),
            ClaudeAdapter(os.path.join(home, PathConstants.CLAUDE_SESSIONS), os.path.join(home, PathConstants.CLAUDE_PROJECTS), tClassifier, tSanitizer),
            tCodex,
            AgyAdapter(os.path.join(home, PathConstants.AGY_ROOT), tClassifier),
            tSanitizer,
            errors,
        )

    def collectOnce(self, now: float) -> Snapshot:
        self.mTable.refresh()
        tWarpServers = self.mScanner.warpServers(self.mTable)
        tPanes = self.mScanner.scan(self.mTable, tWarpServers)
        tCodexReady = self._beginCodexPoll(now)
        tSessions: List[SessionState] = []
        for tPane in tPanes:
            tObservation = self._observe(tPane, tCodexReady)
            tSessions.append(self._session(tPane, tObservation, now))
        self._prune(tPanes)
        return Snapshot(mGeneratedAt=now, mWarpRunning=bool(tWarpServers), mSessions=tuple(tSessions))

    def _beginCodexPoll(self, now: float) -> bool:
        try:
            self.mCodex.beginPoll(self.mTable, now)
        except Exception as tError:
            self.mErrors.exception("codex link pass", tError)
            return False
        return True

    def _observe(self, pane: PaneAgent, codexReady: bool) -> AgentObservation:
        try:
            if pane.mAgent is AgentKind.CLAUDE:
                return self.mClaude.observe(pane)
            if pane.mAgent is AgentKind.CODEX:
                return self.mCodex.observe(pane) if codexReady else AgentObservation.unknown()
            return self.mAgy.observe(pane, self.mTable.startTimeSeconds(pane.mProcess))
        except Exception as tError:
            self.mErrors.exception("%s adapter" % pane.mAgent.value, tError)
            return AgentObservation.unknown()

    def _session(self, pane: PaneAgent, observation: AgentObservation, now: float) -> SessionState:
        tKey = (pane.mPaneUuid, pane.mProcess.mPid, pane.mProcess.mStartTicks)
        tPrevious = self.mPhaseSince.get(tKey)
        if tPrevious is None or tPrevious[0] is not observation.mPhase:
            tPrevious = (observation.mPhase, now)
            self.mPhaseSince[tKey] = tPrevious
        return SessionState(
            mPaneUuid=pane.mPaneUuid,
            mAgent=pane.mAgent,
            mPid=pane.mProcess.mPid,
            mStartTicks=pane.mProcess.mStartTicks,
            mTitle=observation.mTitle or self._folderTitle(pane) or pane.mAgent.value,
            mObservation=observation,
            mPhaseSince=tPrevious[1],
        )

    def _folderTitle(self, pane: PaneAgent) -> Optional[str]:
        return self.mSanitizer.title(os.path.basename(pane.mCwd.rstrip(os.sep))) if pane.mCwd else None

    def _prune(self, panes: List[PaneAgent]):
        tLiveProcesses = {(tPane.mProcess.mPid, tPane.mProcess.mStartTicks) for tPane in panes}
        tLiveKeys = {(tPane.mPaneUuid, tPane.mProcess.mPid, tPane.mProcess.mStartTicks) for tPane in panes}
        for tKey in list(self.mPhaseSince):
            if tKey not in tLiveKeys:
                del self.mPhaseSince[tKey]
        self.mClaude.prune(tLiveProcesses)
        self.mAgy.prune(tLiveProcesses)
        self.mCodex.prune()
