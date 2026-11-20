from collections import deque
from typing import Deque, Dict, List, Optional, Set, Tuple

from agents_deck.adapters.codex_link import CodexLink
from agents_deck.adapters.codex_link_resolver import CodexLinkResolver
from agents_deck.adapters.codex_thread_index import CodexThreadIndex
from agents_deck.adapters.codex_thread_tracker import CodexThreadTracker
from agents_deck.adapters.codex_tui_registry import CodexTuiRegistry
from agents_deck.adapters.label_sanitizer import LabelSanitizer
from agents_deck.adapters.tool_classifier import ToolClassifier
from agents_deck.constants.codex_constants import CodexConstants
from agents_deck.constants.process_constants import ProcessConstants
from agents_deck.constants.timing_constants import TimingConstants
from agents_deck.discovery.pane_agent import PaneAgent
from agents_deck.discovery.process_table import ProcessTable
from agents_deck.model.agent_kind import AgentKind
from agents_deck.model.agent_observation import AgentObservation
from agents_deck.model.background_kind import BackgroundKind
from agents_deck.model.background_task import BackgroundTask
from agents_deck.model.link_confidence import LinkConfidence
from agents_deck.model.phase import Phase
from agents_deck.model.tool_activity import ToolActivity
from agents_deck.model.wait_reason import WaitReason


class CodexAdapter:
    """Codex state for a pane's TUI process.

    In daemon mode the TUI holds no file of its thread; the thread is guessed
    from TUI attach markers (CodexLinkResolver), then its rollout is tailed.
    Processes the thread started carry CODEX_THREAD_ID in their environment;
    those not tied to an open tool call are its background work. Owned by the
    collector thread; call beginPoll once per poll before observe.
    """

    THREAD_VARS = (ProcessConstants.CODEX_THREAD_ID_VAR, CodexConstants.TOOL_CALL_ID_VAR)

    mRegistry: CodexTuiRegistry
    mIndex: CodexThreadIndex
    mResolver: CodexLinkResolver
    mClassifier: ToolClassifier
    mSanitizer: LabelSanitizer
    mAppStartTime: float
    mLinks: Dict[Tuple[int, int], CodexLink]
    mTrackers: Dict[str, CodexThreadTracker]
    mThreadProcesses: Dict[str, List[Tuple[int, str, Optional[str]]]]

    def __init__(self, registry: CodexTuiRegistry, index: CodexThreadIndex, resolver: CodexLinkResolver, classifier: ToolClassifier, sanitizer: LabelSanitizer, appStartTime: float):
        self.mRegistry = registry
        self.mIndex = index
        self.mResolver = resolver
        self.mClassifier = classifier
        self.mSanitizer = sanitizer
        self.mAppStartTime = appStartTime
        self.mLinks = {}
        self.mTrackers = {}
        self.mThreadProcesses = {}

    def beginPoll(self, table: ProcessTable, now: float):
        tTuis = self.mRegistry.update(table, now)
        if not tTuis:
            self.mLinks = {}
            self.mThreadProcesses = {}
            return
        tSince = min(tTui.mStartTime for tTui in tTuis) - TimingConstants.CODEX_LINK_SLACK_SECONDS
        tMarkers = self.mIndex.markersSince(tSince)
        tThreadIds = {tThreadId for tThreadId, _ in tMarkers}
        self.mIndex.retain(tThreadIds)
        self.mIndex.refreshRows(tThreadIds)
        tMarkers = [tMarker for tMarker in tMarkers if not self.mIndex.isSubagent(tMarker[0])]
        self.mLinks = self.mResolver.update(tTuis, tMarkers, self.mIndex.cwds(), self.mAppStartTime)
        self.mThreadProcesses = self._threadProcesses(table)

    def observe(self, paneAgent: PaneAgent) -> AgentObservation:
        tKey = (paneAgent.mProcess.mPid, paneAgent.mProcess.mStartTicks)
        tLink = self.mLinks.get(tKey)
        if tLink is None or tLink.mThreadId is None:
            return AgentObservation.unknown()
        tThreadId = tLink.mThreadId
        tProcesses = self.mThreadProcesses.get(tThreadId, [])
        tTracker = self._tracker(tThreadId)
        if tTracker is None:
            if self.mIndex.hasRow(tThreadId):
                # The thread is persisted but its rollout cannot be found.
                return AgentObservation.unknown()
            # No row and no rollout: the thread has not persisted its first
            # turn, so it has neither a turn nor subagents yet.
            return self._observation(Phase.IDLE, None, None, self._processTasks(tProcesses, set()), [], tLink.mConfidence)
        if not tTracker.update() or tTracker.formatUnrecognized():
            return AgentObservation.unknown()
        tState = tTracker.state()
        tOpenCall = tState.openCallName()
        tOpenIds = set(tState.openCallIds())
        tBackground = self._processTasks(tProcesses, tOpenIds)
        tSubagents = list(tState.mSubagents.values())
        if tState.mTurnActive:
            if tState.hasOpenCall(CodexConstants.USER_INPUT_TOOL):
                return self._observation(Phase.WAITING, WaitReason.INPUT, None, tBackground, tSubagents, tLink.mConfidence)
            if tOpenCall is not None:
                tTool = ToolActivity(mName=tOpenCall, mCategory=self.mClassifier.classify(AgentKind.CODEX, tOpenCall))
                return self._observation(Phase.TOOL, None, tTool, tBackground, tSubagents, tLink.mConfidence)
            return self._observation(Phase.THINKING, None, None, tBackground, tSubagents, tLink.mConfidence)
        tPhase = Phase.ERROR if tState.mTurnError else Phase.IDLE
        return self._observation(tPhase, None, None, tBackground, tSubagents, tLink.mConfidence)

    def prune(self):
        tLinked = {tLink.mThreadId for tLink in self.mLinks.values() if tLink.mThreadId is not None}
        for tThreadId in list(self.mTrackers):
            if tThreadId not in tLinked:
                del self.mTrackers[tThreadId]

    def _tracker(self, threadId: str) -> Optional[CodexThreadTracker]:
        tTracker = self.mTrackers.get(threadId)
        if tTracker is not None:
            return tTracker
        tPath = self.mIndex.rolloutPath(threadId)
        if tPath is None:
            return None
        tTracker = CodexThreadTracker(tPath)
        self.mTrackers[threadId] = tTracker
        return tTracker

    def _threadProcesses(self, table: ProcessTable) -> Dict[str, List[Tuple[int, str, Optional[str]]]]:
        """Top-level processes per thread id, under any Codex process."""
        tResult: Dict[str, List[Tuple[int, str, Optional[str]]]] = {}
        tRoots = [tInfo for tInfo in table.all() if tInfo.mComm == ProcessConstants.CODEX_COMM]
        tQueue: Deque[Tuple[int, Optional[str], int]] = deque((tRoot.mPid, None, 0) for tRoot in tRoots)
        tVisited: Set[int] = set()
        while tQueue:
            tPid, tParentThread, tDepth = tQueue.popleft()
            if tPid in tVisited or tDepth > ProcessConstants.MAX_TREE_DEPTH:
                continue
            tVisited.add(tPid)
            for tChild in table.childrenOf(tPid):
                tEnviron = table.readEnviron(tChild.mPid, self.THREAD_VARS) or {}
                tThreadId = tEnviron.get(ProcessConstants.CODEX_THREAD_ID_VAR)
                if tThreadId and tThreadId != tParentThread and table.isRunning(tChild.mPid, tChild.mStartTicks):
                    tResult.setdefault(tThreadId, []).append((tChild.mPid, tChild.mComm, tEnviron.get(CodexConstants.TOOL_CALL_ID_VAR)))
                tQueue.append((tChild.mPid, tThreadId or tParentThread, tDepth + 1))
        return tResult

    def _processTasks(self, processes: List[Tuple[int, str, Optional[str]]], openCallIds: Set[str]) -> List[BackgroundTask]:
        tTasks = []
        for tPid, tComm, tCallId in processes:
            if tCallId is not None and tCallId in openCallIds:
                continue
            tTasks.append(BackgroundTask(mId=str(tPid), mKind=BackgroundKind.PROCESS, mProcessName=self.mSanitizer.processName(tComm)))
        return tTasks

    @staticmethod
    def _observation(phase: Phase, waitingFor: Optional[WaitReason], tool: Optional[ToolActivity], processes: List[BackgroundTask], subagents: List[BackgroundTask], confidence: LinkConfidence) -> AgentObservation:
        return AgentObservation(
            mPhase=phase,
            mWaitingFor=waitingFor,
            mTool=tool,
            mBackground=tuple(subagents + processes),
            mBackgroundKnown=True,
            mConfidence=confidence,
            mTitle=None,
        )
