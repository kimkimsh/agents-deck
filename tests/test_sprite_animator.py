import unittest

from agents_deck.constants.layout_constants import LayoutConstants
from agents_deck.model.background_kind import BackgroundKind
from agents_deck.model.background_task import BackgroundTask
from agents_deck.model.phase import Phase
from agents_deck.model.tool_activity import ToolActivity
from agents_deck.model.tool_category import ToolCategory
from agents_deck.model.wait_reason import WaitReason
from agents_deck.ui.sprite_animator import SpriteAnimator
from agents_deck.ui.sprite_art import SpriteArt
from tests.session_factory import makeSession


class SpriteAnimatorTest(unittest.TestCase):
    NOW = 10000.0

    def frameOf(self, phase: Phase, since: float, tool, waiting, reduced: bool):
        return SpriteAnimator().frame(makeSession(phase, since, tool, waiting, (), True), self.NOW, reduced)

    def testEveryStateUsesKnownFramesAndOverlays(self):
        tArt = SpriteArt()
        for tPhase in Phase:
            for tReduced in (False, True):
                for tNow in (self.NOW, self.NOW + 0.3, self.NOW + 0.7):
                    tFrame = SpriteAnimator().frame(makeSession(tPhase, self.NOW - 1, ToolActivity("Bash", ToolCategory.SHELL), WaitReason.INPUT, (), True), tNow, tReduced)
                    self.assertIn(tFrame.mFrame, SpriteArt.FRAMES)
                    for tOverlay in tFrame.mOverlays:
                        self.assertIn(tOverlay, SpriteArt.OVERLAYS)
                    tArt.composite(tFrame.mSpecies, tFrame.mFrame, tFrame.mOverlays)

    def testToolShowsItsCategoryProp(self):
        for tCategory in ToolCategory:
            tFrame = self.frameOf(Phase.TOOL, self.NOW, ToolActivity("x", tCategory), None, True)
            self.assertTrue(tFrame.mOverlays[0].startswith("prop." + tCategory.value))

    def testPermissionAndInputBubblesDiffer(self):
        self.assertEqual(self.frameOf(Phase.WAITING, self.NOW, None, WaitReason.PERMISSION, True).mOverlays, ("bang",))
        self.assertEqual(self.frameOf(Phase.WAITING, self.NOW, None, WaitReason.INPUT, True).mOverlays, ("ask",))

    def testErrorAnimatesThenHolds(self):
        tHeld = self.frameOf(Phase.ERROR, self.NOW - 60, None, None, False)
        self.assertEqual((tHeld.mFrame, tHeld.mOverlays), ("error0", ("smoke0",)))

    def testLongIdleSleeps(self):
        self.assertTrue(self.frameOf(Phase.IDLE, self.NOW - 3600, None, None, True).mFrame.startswith("sleep"))
        self.assertIn(self.frameOf(Phase.IDLE, self.NOW - 5, None, None, True).mFrame, ("idle", "blink"))

    def testReducedMotionIsStill(self):
        tFrames = {SpriteAnimator().frame(makeSession(Phase.THINKING, self.NOW, None, None, (), True), self.NOW + tStep / 10.0, True) for tStep in range(30)}
        self.assertEqual(len(tFrames), 1)

    def testUnknownIsDimmed(self):
        self.assertEqual(self.frameOf(Phase.UNKNOWN, self.NOW, None, None, False).mOpacity, LayoutConstants.UNKNOWN_OPACITY)

    def testBackgroundDoesNotChangeThePose(self):
        tTask = BackgroundTask(mId="b1", mKind=BackgroundKind.SHELL, mProcessName=None)
        tWith = SpriteAnimator().frame(makeSession(Phase.THINKING, self.NOW, None, None, (tTask,), True), self.NOW, True)
        self.assertEqual(tWith, self.frameOf(Phase.THINKING, self.NOW, None, None, True))
