import json
from typing import Any, Dict, List, Optional, Sequence

from agents_deck.model.session_state import SessionState
from agents_deck.model.snapshot import Snapshot


class SnapshotCodec:
    """JSON form of a Snapshot for clients off this screen (the future tablet
    deck, --dump-snapshot).

    It carries no text taken from an agent or its user: titles, tool names
    (MCP tools are named after their servers), process names and task labels
    stay on the machine's own overlay. Only pane ids validated at discovery,
    enum values, counts and times are encoded. Background counts are sent
    only while the agent's background work is visible.
    """

    def encode(self, snapshot: Snapshot, order: Sequence[str]) -> str:
        tSessions = sorted(snapshot.mSessions, key=_PaneRank(order))
        return json.dumps({"generatedAt": snapshot.mGeneratedAt, "warpRunning": snapshot.mWarpRunning, "sessions": [self._session(tSession) for tSession in tSessions]}, indent=2)

    @staticmethod
    def _session(session: SessionState) -> Dict[str, Any]:
        tObservation = session.mObservation
        return {
            "pane": session.mPaneUuid,
            "agent": session.mAgent.value,
            "phase": tObservation.mPhase.value,
            "phaseSince": session.mPhaseSince,
            "waitingFor": None if tObservation.mWaitingFor is None else tObservation.mWaitingFor.value,
            "toolCategory": None if tObservation.mTool is None else tObservation.mTool.mCategory.value,
            "background": SnapshotCodec._background(session),
            "confidence": tObservation.mConfidence.value,
        }

    @staticmethod
    def _background(session: SessionState) -> Dict[str, Any]:
        tObservation = session.mObservation
        if not tObservation.mBackgroundKnown:
            return {"known": False, "count": None, "kinds": None}
        tKinds: Optional[List[str]] = sorted({tTask.mKind.value for tTask in tObservation.mBackground})
        return {"known": True, "count": len(tObservation.mBackground), "kinds": tKinds}


class _PaneRank:
    """Sort key: a session's place in the saved tile order; unordered panes last."""

    def __init__(self, order: Sequence[str]):
        self.mRank = {tPane: tIndex for tIndex, tPane in enumerate(order)}

    def __call__(self, session: SessionState) -> int:
        return self.mRank.get(session.mPaneUuid, len(self.mRank))
