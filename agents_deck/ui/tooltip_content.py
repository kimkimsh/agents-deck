from collections import Counter
from typing import Dict, List, Optional

from agents_deck.adapters.tool_classifier import ToolClassifier
from agents_deck.constants.animation_constants import AnimationConstants
from agents_deck.constants.app_constants import AppConstants
from agents_deck.constants.layout_constants import LayoutConstants
from agents_deck.model.agent_kind import AgentKind
from agents_deck.model.background_kind import BackgroundKind
from agents_deck.model.link_confidence import LinkConfidence
from agents_deck.model.phase import Phase
from agents_deck.model.session_state import SessionState
from agents_deck.model.wait_reason import WaitReason
from agents_deck.ui.tooltip_text import TooltipText


class TooltipContent:
    """Words shown when hovering a tile. Pure."""

    AGENT_NAMES: Dict[AgentKind, str] = {AgentKind.CLAUDE: "Claude Code", AgentKind.CODEX: "Codex", AgentKind.AGY: "Antigravity"}
    KIND_NAMES: Dict[BackgroundKind, tuple] = {
        BackgroundKind.SHELL: ("shell", "shells"),
        BackgroundKind.AGENT: ("agent", "agents"),
        BackgroundKind.MONITOR: ("monitor", "monitors"),
        BackgroundKind.WORKFLOW: ("workflow", "workflows"),
        BackgroundKind.REMOTE: ("remote task", "remote tasks"),
        BackgroundKind.PROCESS: ("process", "processes"),
    }
    PHASE_TEXT: Dict[Phase, str] = {
        Phase.STARTING: "Starting up",
        Phase.THINKING: "Thinking",
        Phase.ERROR: "Stopped on an error",
        Phase.UNKNOWN: "State not visible",
    }
    WAIT_TEXT: Dict[WaitReason, str] = {WaitReason.PERMISSION: "Needs your permission", WaitReason.INPUT: "Waiting for your answer"}
    MCP_SEPARATOR = "__"
    MCP_PARTS = 3
    SECONDS_PER_MINUTE = 60
    SECONDS_PER_HOUR = 3600
    SEPARATOR = " · "
    BULLET = "· "

    INFERRED_NOTE = "Thread matched by start time and folder; may be wrong"
    CODEX_UNLINKED_NOTE = "Can't tell which Codex thread this pane shows"
    STALE_NOTE = "Status paused: the collector stopped answering"
    NO_SESSIONS = "No agent sessions in Warp. Start claude, codex or agy in a pane."
    NO_WARP = "Warp is not running"
    ENDED = "Session ended"
    SETTINGS_TITLE = "Settings"
    SHELF_HINT = "Drag the shelf to move, the corner to resize"
    GRIP_TITLE = "Resize"
    GRIP_HINT = "Drag to change the size"

    def forSession(self, session: SessionState, nowSeconds: float, stale: bool) -> TooltipText:
        tObservation = session.mObservation
        tLines: List[str] = [self.AGENT_NAMES[session.mAgent] + self.SEPARATOR + self._phaseText(session, nowSeconds)]
        tLines += self._backgroundLines(session)
        if tObservation.mConfidence is LinkConfidence.INFERRED:
            tLines.append(self.INFERRED_NOTE)
        if tObservation.mPhase is Phase.UNKNOWN and session.mAgent is AgentKind.CODEX:
            tLines.append(self.CODEX_UNLINKED_NOTE)
        if stale:
            tLines.append(self.STALE_NOTE)
        return TooltipText(session.mTitle, tuple(tLines))

    def forGhost(self, warpRunning: bool, settingsNote: Optional[str]) -> TooltipText:
        tLines = [self.NO_SESSIONS if warpRunning else self.NO_WARP]
        if settingsNote:
            tLines.append(settingsNote)
        return TooltipText(AppConstants.APP_NAME, tuple(tLines))

    def forEnded(self, session: SessionState) -> TooltipText:
        return TooltipText(session.mTitle, (self.ENDED,))

    def forGear(self, settingsNote: Optional[str]) -> TooltipText:
        tLines = [self.SHELF_HINT]
        if settingsNote:
            tLines.append(settingsNote)
        return TooltipText(self.SETTINGS_TITLE, tuple(tLines))

    def forGrip(self) -> TooltipText:
        return TooltipText(self.GRIP_TITLE, (self.GRIP_HINT,))

    def _phaseText(self, session: SessionState, nowSeconds: float) -> str:
        tObservation = session.mObservation
        tPhase = tObservation.mPhase
        if tPhase is Phase.TOOL:
            return "Running " + self._toolName(tObservation.mTool.mName if tObservation.mTool else "a tool")
        if tPhase is Phase.WAITING:
            return self.WAIT_TEXT[tObservation.mWaitingFor or WaitReason.INPUT]
        if tPhase is Phase.IDLE:
            tIdle = nowSeconds - session.mPhaseSince
            if tIdle < self.SECONDS_PER_MINUTE:
                return "Idle"
            if tIdle >= AnimationConstants.IDLE_SLEEP_AFTER_SECONDS:
                return "Asleep, idle for " + self._duration(tIdle)
            return "Idle for " + self._duration(tIdle)
        return self.PHASE_TEXT[tPhase]

    def _backgroundLines(self, session: SessionState) -> List[str]:
        tObservation = session.mObservation
        if not tObservation.mBackgroundKnown:
            return ["Background work not visible"]
        if not tObservation.mBackground:
            return ["No background tasks"]
        tCounts = Counter(tTask.mKind for tTask in tObservation.mBackground)
        tSummary = ", ".join("%d %s" % (tCount, self.KIND_NAMES[tKind][0 if tCount == 1 else 1]) for tKind, tCount in tCounts.items())
        tLines = ["Background: " + tSummary]
        tNames = [tTask.mProcessName for tTask in tObservation.mBackground if tTask.mProcessName]
        tShown = tNames[: LayoutConstants.TOOLTIP_MAX_TASK_LINES]
        tLines += [self.BULLET + tName for tName in tShown]
        tHidden = len(tNames) - len(tShown)
        if tHidden > 0:
            tLines.append("+%d more" % tHidden)
        return tLines

    def _toolName(self, name: str) -> str:
        if name.startswith(ToolClassifier.MCP_PREFIX):
            tParts = name.split(self.MCP_SEPARATOR, self.MCP_PARTS - 1)
            if len(tParts) == self.MCP_PARTS:
                return "%s (%s)" % (tParts[2], tParts[1])
        return name

    def _duration(self, seconds: float) -> str:
        if seconds < self.SECONDS_PER_HOUR:
            return "%d min" % (seconds // self.SECONDS_PER_MINUTE)
        return "%d h %d min" % (seconds // self.SECONDS_PER_HOUR, (seconds % self.SECONDS_PER_HOUR) // self.SECONDS_PER_MINUTE)
