from typing import Any, Dict, Optional

from agents_deck.constants.codex_constants import CodexConstants
from agents_deck.model.background_kind import BackgroundKind
from agents_deck.model.background_task import BackgroundTask


class CodexRolloutState:
    """Turn and subagent state of one Codex thread, fed rollout record by record.

    Keeps call ids, tool names and subagent thread ids; message text,
    reasoning, tool arguments, agent names and command output never enter
    this object.
    """

    mTurnActive: bool
    mTurnError: bool
    mOpenCalls: Dict[str, str]
    mSubagents: Dict[str, BackgroundTask]
    mRecognized: int

    def __init__(self):
        self.reset()

    def reset(self):
        self.mTurnActive = False
        self.mTurnError = False
        self.mOpenCalls = {}
        self.mSubagents = {}
        self.mRecognized = 0

    def openCallName(self) -> Optional[str]:
        if not self.mOpenCalls:
            return None
        return next(reversed(self.mOpenCalls.values()))

    def hasOpenCall(self, name: str) -> bool:
        return name in self.mOpenCalls.values()

    def openCallIds(self):
        return self.mOpenCalls.keys()

    def apply(self, record: Dict[str, Any]):
        tPayload = record.get("payload")
        if not isinstance(tPayload, dict):
            return
        tKind = tPayload.get("type")
        tRecordType = record.get("type")
        if tRecordType == CodexConstants.RECORD_EVENT:
            self._applyEvent(tKind, tPayload)
        elif tRecordType == CodexConstants.RECORD_RESPONSE:
            self._applyResponse(tKind, tPayload)

    def _applyEvent(self, kind, payload: Dict[str, Any]):
        if kind == CodexConstants.EVENT_TASK_STARTED:
            self.mRecognized += 1
            self.mTurnActive = True
            self.mTurnError = False
            self.mOpenCalls.clear()
        elif kind == CodexConstants.EVENT_TASK_COMPLETE:
            self.mRecognized += 1
            self.mTurnActive = False
            self.mTurnError = bool(payload.get("error"))
            # Calls still open when the turn ends are background processes;
            # those are observed as live processes, not as calls.
            self.mOpenCalls.clear()
        elif kind == CodexConstants.EVENT_TURN_ABORTED:
            self.mRecognized += 1
            self.mTurnActive = False
            self.mTurnError = bool(payload.get("error"))
            self.mOpenCalls.clear()
        elif kind == CodexConstants.EVENT_SUBAGENT_ACTIVITY:
            # Legacy history persists every kind but `completed` as this event.
            self.mRecognized += 1
            self._applySubagent(payload)
        elif kind == CodexConstants.EVENT_ITEM_COMPLETED:
            # ...and `completed` only as this nested item.
            tItem = payload.get("item")
            if isinstance(tItem, dict) and tItem.get("type") == CodexConstants.ITEM_SUBAGENT_ACTIVITY:
                self.mRecognized += 1
                self._applySubagent(tItem)

    def _applyResponse(self, kind, payload: Dict[str, Any]):
        tCallId = payload.get("call_id")
        if not isinstance(tCallId, str):
            return
        if kind in CodexConstants.CALL_TYPES:
            self.mRecognized += 1
            tName = payload.get("name")
            self.mOpenCalls[tCallId] = tName if isinstance(tName, str) else ""
        elif kind in CodexConstants.CALL_OUTPUT_TYPES:
            self.mRecognized += 1
            self.mOpenCalls.pop(tCallId, None)

    def _applySubagent(self, item: Dict[str, Any]):
        tThreadId = item.get("agent_thread_id")
        if not isinstance(tThreadId, str):
            return
        tKind = item.get("kind")
        if tKind == CodexConstants.SUBAGENT_STARTED:
            self.mSubagents[tThreadId] = BackgroundTask(mId=tThreadId, mKind=BackgroundKind.AGENT, mProcessName=None)
        elif tKind in CodexConstants.SUBAGENT_FINISHED_KINDS:
            self.mSubagents.pop(tThreadId, None)
