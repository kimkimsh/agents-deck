import os
import time
from typing import Any, Dict, Optional, Tuple

from agents_deck.adapters.json_record import JsonRecord
from agents_deck.adapters.line_tail import LineTail
from agents_deck.adapters.tool_classifier import ToolClassifier
from agents_deck.constants.agy_constants import AgyConstants
from agents_deck.constants.path_constants import PathConstants
from agents_deck.constants.tail_constants import TailConstants
from agents_deck.constants.timing_constants import TimingConstants
from agents_deck.discovery.pane_agent import PaneAgent
from agents_deck.model.agent_kind import AgentKind
from agents_deck.model.agent_observation import AgentObservation
from agents_deck.model.link_confidence import LinkConfidence
from agents_deck.model.phase import Phase
from agents_deck.model.tool_activity import ToolActivity


class AgyAdapter:
    """Antigravity CLI state from its per-process log and brain transcript.

    Each agy process writes `log/cli-<start time>.log` with its pid in every
    glog header; that log names the conversation, whose transcript holds the
    steps. The log also holds prompt text and the account email, so it is
    read incrementally, line by line, and only a line that is exactly a glog
    header from this pid followed by a conversation message yields anything:
    the conversation id. A prompt that quotes such a message sits after a
    different header text and does not match.

    transcript.jsonl is append-only: each step is written once, with the
    status it had at that moment. A tool step is written when it finishes, so
    while a tool runs the newest record is the planner step that called it. A
    RUN_COMMAND written as RUNNING went to the background and its end is never
    recorded, so background work and tool-confirmation waits are not
    observable here. Owned by the collector thread.
    """

    mLogDir: str
    mBrainDir: str
    mClassifier: ToolClassifier
    mLogs: Dict[Tuple[int, int], str]
    mLogTails: Dict[str, LineTail]
    mConversations: Dict[str, Optional[str]]
    mTranscripts: Dict[str, LineTail]
    mNewestSteps: Dict[str, Tuple[int, Dict[str, Any]]]

    def __init__(self, agyRoot: str, classifier: ToolClassifier):
        self.mLogDir = os.path.join(agyRoot, PathConstants.AGY_LOG_DIR)
        self.mBrainDir = os.path.join(agyRoot, PathConstants.AGY_BRAIN_DIR)
        self.mClassifier = classifier
        self.mLogs = {}
        self.mLogTails = {}
        self.mConversations = {}
        self.mTranscripts = {}
        self.mNewestSteps = {}

    def observe(self, paneAgent: PaneAgent, processStartTime: Optional[float]) -> AgentObservation:
        tPid = paneAgent.mProcess.mPid
        tKey = (tPid, paneAgent.mProcess.mStartTicks)
        tLogPath = self.mLogs.get(tKey)
        if tLogPath is None and processStartTime is not None:
            tLogPath = self._findLog(tPid, processStartTime)
        if tLogPath is None:
            return self._observation(Phase.UNKNOWN, None, LinkConfidence.UNKNOWN)
        self.mLogs[tKey] = tLogPath
        if not self._readLog(tLogPath, tPid):
            return self._observation(Phase.UNKNOWN, None, LinkConfidence.UNKNOWN)
        tConversation = self.mConversations.get(tLogPath)
        if tConversation is None:
            # The log is readable and has named no conversation: nothing typed yet.
            return self._observation(Phase.IDLE, None, LinkConfidence.EXACT)
        if not self._readSteps(tConversation):
            return self._observation(Phase.UNKNOWN, None, LinkConfidence.EXACT)
        tNewest = self.mNewestSteps.get(tConversation)
        if tNewest is None:
            return self._observation(Phase.IDLE, None, LinkConfidence.EXACT)
        return self._fromStep(tNewest[1])

    def prune(self, liveKeys):
        tLive = set(liveKeys)
        for tKey in list(self.mLogs):
            if tKey not in tLive:
                tLog = self.mLogs.pop(tKey)
                self.mLogTails.pop(tLog, None)
                self.mConversations.pop(tLog, None)
        tLiveConversations = {tConversation for tConversation in self.mConversations.values() if tConversation}
        for tConversation in list(self.mTranscripts):
            if tConversation not in tLiveConversations:
                del self.mTranscripts[tConversation]
                self.mNewestSteps.pop(tConversation, None)

    def _fromStep(self, step: Dict[str, Any]) -> AgentObservation:
        tType = step.get("type")
        tStatus = step.get("status")
        if tStatus == AgyConstants.STATUS_ERROR or tType == AgyConstants.STEP_ERROR_MESSAGE:
            return self._observation(Phase.ERROR, None, LinkConfidence.EXACT)
        if tType == AgyConstants.STEP_PLANNER:
            tCallName = self._firstToolCallName(step)
            if tCallName is None:
                return self._observation(Phase.IDLE, None, LinkConfidence.EXACT)
            return self._observation(Phase.TOOL, self._tool(tCallName), LinkConfidence.EXACT)
        # The user spoke, or a tool step finished: the planner responds next.
        return self._observation(Phase.THINKING, None, LinkConfidence.EXACT)

    def _tool(self, name: str) -> ToolActivity:
        return ToolActivity(mName=name, mCategory=self.mClassifier.classify(AgentKind.AGY, name))

    @staticmethod
    def _firstToolCallName(step: Dict[str, Any]) -> Optional[str]:
        tCalls = step.get("tool_calls")
        if not isinstance(tCalls, list) or not tCalls or not isinstance(tCalls[0], dict):
            return None
        tName = tCalls[0].get("name")
        return tName if isinstance(tName, str) else None

    def _findLog(self, pid: int, processStartTime: float) -> Optional[str]:
        try:
            tNames = sorted(tName for tName in os.listdir(self.mLogDir) if tName.endswith(AgyConstants.LOG_SUFFIX))
        except OSError:
            return None
        for tName in tNames:
            try:
                tCreated = time.mktime(time.strptime(tName, AgyConstants.LOG_NAME_TIME_FORMAT))
            except ValueError:
                continue
            # The log is opened as the process starts; a log from another
            # time with the same pid belongs to a process that reused it.
            if tCreated < processStartTime - TimingConstants.AGY_LOG_START_SLACK_SECONDS:
                continue
            if tCreated > processStartTime + TimingConstants.AGY_LOG_OPEN_WINDOW_SECONDS:
                continue
            tPath = os.path.join(self.mLogDir, tName)
            if self._logPid(tPath) == pid:
                return tPath
        return None

    @staticmethod
    def _logPid(path: str) -> Optional[int]:
        try:
            with open(path, "rb") as tFile:
                tFirst = tFile.readline()
        except OSError:
            return None
        tFields = tFirst.split()
        if len(tFields) <= AgyConstants.GLOG_PID_FIELD:
            return None
        try:
            return int(tFields[AgyConstants.GLOG_PID_FIELD])
        except ValueError:
            return None

    def _readLog(self, logPath: str, pid: int) -> bool:
        """Advances the log; False when it cannot be read."""
        tTail = self.mLogTails.get(logPath)
        if tTail is None:
            tTail = LineTail(logPath, TailConstants.INITIAL_WINDOW_BYTES, TailConstants.MAX_READ_BYTES_PER_POLL, AgyConstants.CONVERSATION_LINE_NEEDLES)
            self.mLogTails[logPath] = tTail
        tBatch = tTail.readNew()
        if tBatch is None:
            return False
        if tBatch.mWasReset:
            self.mConversations.pop(logPath, None)
        for tLine in tBatch.mPrefix + tBatch.mLines:
            tConversation = self._conversationLine(tLine, pid)
            if tConversation is not None:
                self.mConversations[logPath] = tConversation
        return True

    @staticmethod
    def _conversationLine(line: bytes, pid: int) -> Optional[str]:
        tMatch = AgyConstants.CONVERSATION_LINE.fullmatch(line)
        if tMatch is None or int(tMatch.group(AgyConstants.LINE_PID_GROUP)) != pid:
            return None
        # The id becomes a path component under brain/; the pattern admits only a UUID.
        return tMatch.group(AgyConstants.LINE_CONVERSATION_GROUP).decode("ascii")

    def _readSteps(self, conversationId: str) -> bool:
        """False when the transcript exists but cannot be read; a conversation
        whose transcript is not written yet has no steps."""
        tTail = self.mTranscripts.get(conversationId)
        if tTail is None:
            tPath = os.path.join(self.mBrainDir, conversationId, PathConstants.AGY_TRANSCRIPT)
            if not os.path.exists(tPath):
                return True
            tTail = LineTail(tPath, TailConstants.INITIAL_WINDOW_BYTES, TailConstants.MAX_READ_BYTES_PER_POLL, ())
            self.mTranscripts[conversationId] = tTail
        tBatch = tTail.readNew()
        if tBatch is None:
            return False
        if tBatch.mWasReset:
            self.mNewestSteps.pop(conversationId, None)
        for tRecord in JsonRecord.parseAll(tBatch.mLines):
            tIndex = tRecord.get(AgyConstants.STEP_INDEX)
            if not isinstance(tIndex, int) or tRecord.get("type") in AgyConstants.META_STEPS:
                continue
            tKnown = self.mNewestSteps.get(conversationId)
            if tKnown is None or tIndex >= tKnown[0]:
                self.mNewestSteps[conversationId] = (tIndex, self._allowlisted(tRecord))
        return True

    @staticmethod
    def _allowlisted(record: Dict[str, Any]) -> Dict[str, Any]:
        tCalls = record.get("tool_calls")
        tNames = [{"name": tCall.get("name")} for tCall in tCalls if isinstance(tCall, dict)] if isinstance(tCalls, list) else None
        return {"type": record.get("type"), "status": record.get("status"), "tool_calls": tNames}

    @staticmethod
    def _observation(phase: Phase, tool: Optional[ToolActivity], confidence: LinkConfidence) -> AgentObservation:
        return AgentObservation(
            mPhase=phase,
            mWaitingFor=None,
            mTool=tool,
            mBackground=(),
            mBackgroundKnown=False,
            mConfidence=confidence,
            mTitle=None,
        )
