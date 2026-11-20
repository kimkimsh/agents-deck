import zlib
from typing import Dict, Tuple

from agents_deck.constants.animation_constants import AnimationConstants
from agents_deck.constants.layout_constants import LayoutConstants
from agents_deck.constants.timing_constants import TimingConstants
from agents_deck.model.agent_kind import AgentKind
from agents_deck.model.phase import Phase
from agents_deck.model.session_state import SessionState
from agents_deck.model.tool_category import ToolCategory
from agents_deck.model.wait_reason import WaitReason
from agents_deck.ui.sprite_art import SpriteArt
from agents_deck.ui.sprite_frame import SpriteFrame


class SpriteAnimator:
    """Picks the frame a session shows at a given time. Pure.

    Each state has one pose and at most one prop or bubble, so every state is
    told apart by shape, not by colour alone. With reduced motion every state
    holds its first frame and the idle blink is off.
    """

    SPECIES: Dict[AgentKind, str] = {AgentKind.CLAUDE: SpriteArt.EMBER, AgentKind.CODEX: SpriteArt.CUBIT, AgentKind.AGY: SpriteArt.FLOATY}

    THINK_DOTS = ("think1", "think2", "think3")
    PROP_PREFIX = "prop."
    SHELL_PROP = ("prop.shell0", "prop.shell1")
    FULL_OPACITY = 1.0

    def frame(self, session: SessionState, nowSeconds: float, reducedMotion: bool) -> SpriteFrame:
        tSpecies = self.SPECIES[session.mAgent]
        tObservation = session.mObservation
        tPhase = tObservation.mPhase
        tNowMs = int(nowSeconds * TimingConstants.MS_PER_SECOND)
        tElapsed = nowSeconds - session.mPhaseSince

        if tPhase is Phase.STARTING:
            return SpriteFrame(tSpecies, "blink", (), self.FULL_OPACITY)
        if tPhase is Phase.UNKNOWN:
            return SpriteFrame(tSpecies, "idle", (), LayoutConstants.UNKNOWN_OPACITY)
        if tPhase is Phase.THINKING:
            tBody = "think0" if reducedMotion else self._alternate("think0", "think1", tNowMs, AnimationConstants.THINK_BODY_MS)
            tDots = self.THINK_DOTS[-1] if reducedMotion else self.THINK_DOTS[(tNowMs // AnimationConstants.THINK_DOTS_MS) % len(self.THINK_DOTS)]
            return SpriteFrame(tSpecies, tBody, (tDots,), self.FULL_OPACITY)
        if tPhase is Phase.TOOL:
            tBody = "work0" if reducedMotion else self._alternate("work0", "work1", tNowMs, AnimationConstants.WORK_FRAME_MS)
            return SpriteFrame(tSpecies, tBody, (self._prop(tObservation.mTool.mCategory if tObservation.mTool else ToolCategory.OTHER, tNowMs, reducedMotion),), self.FULL_OPACITY)
        if tPhase is Phase.WAITING:
            tBody = "raise0" if reducedMotion else self._alternate("raise0", "raise1", tNowMs, AnimationConstants.RAISE_FRAME_MS)
            tBubble = "bang" if tObservation.mWaitingFor is WaitReason.PERMISSION else "ask"
            return SpriteFrame(tSpecies, tBody, (tBubble,), self.FULL_OPACITY)
        if tPhase is Phase.ERROR:
            if reducedMotion or tElapsed * TimingConstants.MS_PER_SECOND >= AnimationConstants.ERROR_LOOP_MS:
                return SpriteFrame(tSpecies, "error0", ("smoke0",), self.FULL_OPACITY)
            tIndex = (tNowMs // AnimationConstants.ERROR_FRAME_MS) % 2
            return SpriteFrame(tSpecies, ("error0", "error1")[tIndex], (("smoke0", "smoke1")[tIndex],), self.FULL_OPACITY)
        if tElapsed >= AnimationConstants.IDLE_SLEEP_AFTER_SECONDS:
            if reducedMotion:
                return SpriteFrame(tSpecies, "sleep0", ("zzz1",), self.FULL_OPACITY)
            tIndex = (tNowMs // AnimationConstants.SLEEP_FRAME_MS) % 2
            return SpriteFrame(tSpecies, ("sleep0", "sleep1")[tIndex], (("zzz0", "zzz1")[tIndex],), self.FULL_OPACITY)
        if not reducedMotion and self._blinking(session.mPaneUuid, tNowMs):
            return SpriteFrame(tSpecies, "blink", (), self.FULL_OPACITY)
        return SpriteFrame(tSpecies, "idle", (), self.FULL_OPACITY)

    def _prop(self, category: ToolCategory, nowMs: int, reducedMotion: bool) -> str:
        if category is ToolCategory.SHELL:
            return self.SHELL_PROP[0] if reducedMotion else self._alternate(self.SHELL_PROP[0], self.SHELL_PROP[1], nowMs, AnimationConstants.CURSOR_BLINK_MS)
        return self.PROP_PREFIX + category.value

    @staticmethod
    def _alternate(first: str, second: str, nowMs: int, periodMs: int) -> str:
        return first if (nowMs // periodMs) % 2 == 0 else second

    @staticmethod
    def _blinking(paneUuid: str, nowMs: int) -> bool:
        tSeed = zlib.crc32(paneUuid.encode("ascii", "replace"))
        tPeriod = AnimationConstants.BLINK_PERIOD_MIN_MS + tSeed % AnimationConstants.BLINK_PERIOD_SPREAD_MS
        return (nowMs + tSeed) % tPeriod < AnimationConstants.BLINK_DURATION_MS

    @staticmethod
    def ghost() -> Tuple[str, str]:
        """Species and frame of the placeholder tile shown with no sessions."""
        return SpriteArt.EMBER, "idle"
