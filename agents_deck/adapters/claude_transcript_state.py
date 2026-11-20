import re
from typing import Any, Dict, Optional, Set

from agents_deck.constants.claude_constants import ClaudeConstants
from agents_deck.model.background_kind import BackgroundKind
from agents_deck.model.background_task import BackgroundTask


class ClaudeTranscriptState:
    """Activity derived from one Claude Code transcript, fed record by record.

    Keeps only identifiers, tool names and flags; message text, tool input
    and output, and agent-written descriptions never enter this object.
    """

    TASK_ID_PATTERN = re.compile(r"<task-id>([^<]*)</task-id>")
    STATUS_PATTERN = re.compile(r"<status>([^<]*)</status>")

    mOpenToolUses: Dict[str, str]
    mBackground: Dict[str, BackgroundTask]
    mClosedTasks: Set[str]
    mTurnEnded: bool
    mLastError: bool

    def __init__(self):
        self.reset()

    def reset(self):
        self.mOpenToolUses = {}
        self.mBackground = {}
        self.mClosedTasks = set()
        self.mTurnEnded = False
        self.mLastError = False

    def endPrefix(self):
        """Ends a prefix scan: foreground state from out-of-window records is meaningless."""
        self.mOpenToolUses.clear()
        self.mTurnEnded = False
        self.mLastError = False

    def openToolName(self) -> Optional[str]:
        if not self.mOpenToolUses:
            return None
        return next(reversed(self.mOpenToolUses.values()))

    def apply(self, record: Dict[str, Any]):
        if record.get("isSidechain") or record.get("isMeta"):
            return
        tType = record.get("type")
        if tType == ClaudeConstants.RECORD_ASSISTANT:
            self._applyAssistant(record)
        elif tType == ClaudeConstants.RECORD_USER:
            self._applyUser(record)
        elif tType == ClaudeConstants.RECORD_QUEUE_OPERATION:
            self._applyQueueOperation(record)

    def _applyAssistant(self, record: Dict[str, Any]):
        tMessage = record.get("message")
        if not isinstance(tMessage, dict):
            return
        self.mLastError = bool(record.get("isApiErrorMessage"))
        for tBlock in self._blocks(tMessage):
            if tBlock.get("type") != ClaudeConstants.BLOCK_TOOL_USE:
                continue
            tId = tBlock.get("id")
            tName = tBlock.get("name")
            if not isinstance(tId, str) or not isinstance(tName, str):
                continue
            self.mOpenToolUses[tId] = tName
        self.mTurnEnded = tMessage.get("stop_reason") == ClaudeConstants.STOP_END_TURN

    def _applyUser(self, record: Dict[str, Any]):
        tMessage = record.get("message")
        if not isinstance(tMessage, dict):
            return
        tContent = tMessage.get("content")
        tResults = [tBlock for tBlock in self._blocks(tMessage) if tBlock.get("type") == ClaudeConstants.BLOCK_TOOL_RESULT]
        if not tResults:
            if isinstance(tContent, str) or self._blocks(tMessage):
                self._startTurn()
            return
        tToolResult = record.get("toolUseResult")
        for tBlock in tResults:
            tToolUseId = tBlock.get("tool_use_id")
            if not isinstance(tToolUseId, str):
                continue
            tToolName = self.mOpenToolUses.pop(tToolUseId, None)
            if isinstance(tToolResult, dict):
                self._registerBackground(tToolResult, tToolName)

    def _registerBackground(self, toolResult: Dict[str, Any], toolName: Optional[str]):
        if toolName in ClaudeConstants.STOP_TOOL_NAMES:
            # TaskStop ends a task without a later <task-notification>.
            tStoppedId = toolResult.get(ClaudeConstants.STOP_RESULT_TASK_ID)
            if isinstance(tStoppedId, str) and tStoppedId:
                self._closeTask(tStoppedId)
            return
        tTaskId = toolResult.get("backgroundTaskId")
        if isinstance(tTaskId, str) and tTaskId:
            self._addTask(tTaskId, self.kindForTaskId(tTaskId))
            return
        if toolResult.get("isAsync") and toolResult.get("status") == ClaudeConstants.ASYNC_LAUNCHED:
            # Agent ids are random hex, so their first letter is no kind prefix.
            tAgentId = toolResult.get("agentId")
            if isinstance(tAgentId, str) and tAgentId:
                self._addTask(tAgentId, BackgroundKind.AGENT)

    def _addTask(self, taskId: str, kind: BackgroundKind):
        if taskId in self.mClosedTasks:
            return
        self.mBackground[taskId] = BackgroundTask(mId=taskId, mKind=kind, mProcessName=None)

    def _applyQueueOperation(self, record: Dict[str, Any]):
        if record.get("operation") != ClaudeConstants.QUEUE_ENQUEUE:
            return
        tContent = record.get("content")
        if not isinstance(tContent, str) or ClaudeConstants.TASK_NOTIFICATION_TAG not in tContent:
            return
        tTaskId = self.TASK_ID_PATTERN.search(tContent)
        tStatus = self.STATUS_PATTERN.search(tContent)
        if tTaskId is None or tStatus is None:
            return
        if tStatus.group(1).strip() not in ClaudeConstants.TASK_TERMINAL_STATUSES:
            return
        self._closeTask(tTaskId.group(1).strip())

    def _closeTask(self, taskId: str):
        self.mBackground.pop(taskId, None)
        self.mClosedTasks.add(taskId)

    def _startTurn(self):
        # A new prompt ends the previous turn; tool calls left open by an
        # interrupt never receive a result and must not stay "running".
        self.mOpenToolUses.clear()
        self.mTurnEnded = False
        self.mLastError = False

    @staticmethod
    def kindForTaskId(taskId: str) -> BackgroundKind:
        tPrefix = taskId[:1]
        if tPrefix == ClaudeConstants.TASK_PREFIX_SHELL:
            return BackgroundKind.SHELL
        if tPrefix in (ClaudeConstants.TASK_PREFIX_AGENT, ClaudeConstants.TASK_PREFIX_TEAMMATE):
            return BackgroundKind.AGENT
        if tPrefix == ClaudeConstants.TASK_PREFIX_REMOTE:
            return BackgroundKind.REMOTE
        if tPrefix == ClaudeConstants.TASK_PREFIX_WORKFLOW:
            return BackgroundKind.WORKFLOW
        if tPrefix in ClaudeConstants.TASK_PREFIXES_MONITOR:
            return BackgroundKind.MONITOR
        return BackgroundKind.PROCESS

    @staticmethod
    def _blocks(message: Dict[str, Any]):
        tContent = message.get("content")
        if not isinstance(tContent, list):
            return []
        return [tBlock for tBlock in tContent if isinstance(tBlock, dict)]
