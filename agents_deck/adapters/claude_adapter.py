import json
import os
from typing import Dict, Iterable, List, Optional, Tuple

from agents_deck.adapters.claude_session_tracker import ClaudeSessionTracker
from agents_deck.adapters.label_sanitizer import LabelSanitizer
from agents_deck.adapters.tool_classifier import ToolClassifier
from agents_deck.constants.claude_constants import ClaudeConstants
from agents_deck.constants.path_constants import PathConstants
from agents_deck.discovery.pane_agent import PaneAgent
from agents_deck.model.agent_kind import AgentKind
from agents_deck.model.agent_observation import AgentObservation
from agents_deck.model.background_kind import BackgroundKind
from agents_deck.model.background_task import BackgroundTask
from agents_deck.model.link_confidence import LinkConfidence
from agents_deck.model.phase import Phase
from agents_deck.model.tool_activity import ToolActivity
from agents_deck.model.wait_reason import WaitReason


class ClaudeAdapter:
    """Claude Code state from the session registry plus the transcript tail.

    The registry (`~/.claude/sessions/<pid>.json`) is authoritative for
    busy / waiting / idle; the transcript only adds which tool is running and
    which background tasks exist. Owned by the collector thread.
    """

    mSessionsDir: str
    mProjectsDir: str
    mClassifier: ToolClassifier
    mSanitizer: LabelSanitizer
    mTrackers: Dict[Tuple[int, int], ClaudeSessionTracker]

    def __init__(self, sessionsDir: str, projectsDir: str, classifier: ToolClassifier, sanitizer: LabelSanitizer):
        self.mSessionsDir = sessionsDir
        self.mProjectsDir = projectsDir
        self.mClassifier = classifier
        self.mSanitizer = sanitizer
        self.mTrackers = {}

    def observe(self, paneAgent: PaneAgent) -> AgentObservation:
        tProcess = paneAgent.mProcess
        tRegistry = self._readRegistry(tProcess.mPid, tProcess.mStartTicks)
        if tRegistry is None:
            return self._starting()
        tKey = (tProcess.mPid, tProcess.mStartTicks)
        tTracker = self.mTrackers.get(tKey)
        if tTracker is None:
            tTracker = ClaudeSessionTracker(self.mProjectsDir)
            self.mTrackers[tKey] = tTracker
        tSessionId = tRegistry.get("sessionId")
        tTranscriptOk = isinstance(tSessionId, str) and tTracker.update(tSessionId)
        tStatus = tRegistry.get("status")
        tBackground: List[BackgroundTask] = []
        tOpenTool: Optional[str] = None
        tTurnEnded = False
        tLastError = False
        if tTranscriptOk:
            # State from an unreadable transcript is from an earlier poll, or
            # an earlier session, and is not shown.
            tState = tTracker.state()
            tBackground = list(tState.mBackground.values())
            tOpenTool = tState.openToolName()
            tTurnEnded = tState.mTurnEnded
            tLastError = tState.mLastError
            if tStatus == ClaudeConstants.STATUS_SHELL and not any(tTask.mKind is BackgroundKind.SHELL for tTask in tBackground):
                tBackground.append(BackgroundTask(mId=ClaudeConstants.UNSEEN_SHELL_TASK_ID, mKind=BackgroundKind.SHELL, mProcessName=None))

        tPhase, tWaitingFor, tTool = self._phase(tStatus, tRegistry.get("waitingFor"), tOpenTool, tTurnEnded, tLastError)
        return AgentObservation(
            mPhase=tPhase,
            mWaitingFor=tWaitingFor,
            mTool=tTool,
            mBackground=tuple(tBackground),
            mBackgroundKnown=tTranscriptOk,
            mConfidence=LinkConfidence.EXACT,
            mTitle=self._title(tRegistry),
        )

    def prune(self, liveKeys: Iterable[Tuple[int, int]]):
        tLive = set(liveKeys)
        for tKey in list(self.mTrackers):
            if tKey not in tLive:
                del self.mTrackers[tKey]

    def _phase(self, status, waitingFor, openTool: Optional[str], turnEnded: bool, lastError: bool) -> Tuple[Phase, Optional[WaitReason], Optional[ToolActivity]]:
        if status == ClaudeConstants.STATUS_WAITING:
            return Phase.WAITING, self._waitingReason(waitingFor), None
        if status == ClaudeConstants.STATUS_BUSY:
            if openTool is not None:
                return Phase.TOOL, None, ToolActivity(mName=openTool, mCategory=self.mClassifier.classify(AgentKind.CLAUDE, openTool))
            if turnEnded:
                # busy with no turn in flight = delegated work only (async agents).
                return Phase.IDLE, None, None
            return Phase.THINKING, None, None
        if status == ClaudeConstants.STATUS_SHELL:
            return Phase.IDLE, None, None
        if status == ClaudeConstants.STATUS_IDLE:
            return (Phase.ERROR if lastError else Phase.IDLE), None, None
        return Phase.UNKNOWN, None, None

    @staticmethod
    def _waitingReason(waitingFor) -> WaitReason:
        if isinstance(waitingFor, str) and waitingFor in ClaudeConstants.WAITING_PERMISSION_REASONS:
            return WaitReason.PERMISSION
        if waitingFor is None:
            # The registry omits waitingFor for the default permission prompt.
            return WaitReason.PERMISSION
        return WaitReason.INPUT

    def _title(self, registry: dict) -> Optional[str]:
        if registry.get("nameSource") == ClaudeConstants.NAME_SOURCE_USER:
            tName = self.mSanitizer.title(registry.get("name"))
            if tName:
                return tName
        tCwd = registry.get("cwd")
        if isinstance(tCwd, str) and tCwd:
            return self.mSanitizer.title(os.path.basename(tCwd.rstrip(os.sep)))
        return None

    def _readRegistry(self, pid: int, startTicks: int) -> Optional[dict]:
        try:
            with open(os.path.join(self.mSessionsDir, PathConstants.CLAUDE_REGISTRY_FILE_FORMAT % pid), "r", encoding="utf-8") as tFile:
                tRegistry = json.load(tFile)
        except (OSError, ValueError):
            return None
        if not isinstance(tRegistry, dict):
            return None
        try:
            tProcStart = int(tRegistry.get("procStart", -1))
        except (TypeError, ValueError):
            return None
        if tProcStart != startTicks:
            return None
        return tRegistry

    @staticmethod
    def _starting() -> AgentObservation:
        return AgentObservation(
            mPhase=Phase.STARTING,
            mWaitingFor=None,
            mTool=None,
            mBackground=(),
            mBackgroundKnown=False,
            mConfidence=LinkConfidence.UNKNOWN,
            mTitle=None,
        )
