import unittest

from agents_deck.constants.sprite_constants import SpriteConstants
from agents_deck.ui.sprite_art import SpriteArt
from agents_deck.ui.sprite_palette import SpritePalette

OUTLINE = "o"


class SpriteArtTest(unittest.TestCase):
    def setUp(self):
        self.mArt = SpriteArt()

    def testFramesAreFullCanvasWithKnownColours(self):
        tPalette = SpritePalette()
        for tSpecies, tFrames in self.mArt.frames().items():
            tKeys = set(tPalette.colors(tSpecies)) | {SpriteConstants.TRANSPARENT}
            self.assertEqual(set(tFrames), set(SpriteArt.FRAMES))
            for tName, tRows in tFrames.items():
                self.assertEqual(len(tRows), SpriteConstants.CANVAS, (tSpecies, tName))
                for tRow in tRows:
                    self.assertEqual(len(tRow), SpriteConstants.CANVAS)
                    self.assertLessEqual(set(tRow), tKeys, (tSpecies, tName))

    def testOverlaysUseFixedColoursAndFitTheCanvas(self):
        tKeys = set(SpritePalette().colors("")) | {SpriteConstants.TRANSPARENT}
        for tName, (tLeft, tTop, tRows) in SpriteArt.OVERLAYS.items():
            self.assertLessEqual(tLeft + max(len(tRow) for tRow in tRows), SpriteConstants.CANVAS, tName)
            self.assertLessEqual(tTop + len(tRows), SpriteConstants.CANVAS, tName)
            self.assertLessEqual(set("".join(tRows)), tKeys, tName)

    def assertGlyphClearOfOutline(self, rows, glyphKey: str):
        for tY, tRow in enumerate(rows):
            for tX, tKey in enumerate(tRow):
                if tKey != glyphKey:
                    continue
                for tNeighbourY in (tY - 1, tY + 1):
                    if 0 <= tNeighbourY < len(rows):
                        self.assertNotEqual(rows[tNeighbourY][tX], OUTLINE, "glyph touches outline at %d,%d" % (tX, tY))

    def testBadgeDigitsStayClearOfTheOutline(self):
        for tCount in (1, 2, 8, 9, 10, 99):
            self.assertGlyphClearOfOutline(self.mArt.badge(tCount), "e")

    def testBadgeCapsAtNinePlus(self):
        self.assertEqual(self.mArt.badge(42), self.mArt.badge(10))
        self.assertNotEqual(self.mArt.badge(9), self.mArt.badge(10))

    def testBubbleGlyphsStayClearOfTheOutline(self):
        for tName in ("bang", "ask"):
            self.assertGlyphClearOfOutline(SpriteArt.OVERLAYS[tName][2], "e")

    def testSilhouettesAreLeftRightSymmetricAtRest(self):
        # Ember's flame tuft above its body leans to one side on purpose.
        tFirstSymmetricRow = {SpriteArt.EMBER: 11, SpriteArt.CUBIT: 0, SpriteArt.FLOATY: 0}
        for tSpecies, tFrames in self.mArt.frames().items():
            tRows = tFrames["idle"][tFirstSymmetricRow[tSpecies]:]
            tSilhouette = ["".join("." if tKey == SpriteConstants.TRANSPARENT else "#" for tKey in tRow) for tRow in tRows]
            for tRow in tSilhouette:
                self.assertEqual(tRow, tRow[::-1], tSpecies)
